import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import dayjs from 'dayjs'
import toast from 'react-hot-toast'
import { accidentApi } from '../services/api'
import { useAccidentStore } from '../store'

const SEVERITIES = ['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW']
const SOURCES = ['ALL', 'AI_CAMERA', 'USER_REPORT', 'EXTERNAL']
const STATUSES = ['ALL', 'DETECTED', 'NOTIFIED', 'RESOLVED']

const SEVERITY_COLOR = { CRITICAL: '#ff1744', HIGH: '#ff6d00', MEDIUM: '#ffd600', LOW: '#00c853' }

export default function IncidentsPage() {
  const navigate = useNavigate()
  const [severity, setSeverity] = useState('ALL')
  const [source, setSource] = useState('ALL')
  const [status, setStatus] = useState('ALL')
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState(null)

  const { data, isLoading } = useQuery({
    queryKey: ['incidents', severity, source, status, page],
    queryFn: () => accidentApi.list({
      page, page_size: 25,
      ...(severity !== 'ALL' && { severity }),
      ...(source !== 'ALL' && { source }),
      ...(status !== 'ALL' && { status }),
    }).then(r => r.data),
    keepPreviousData: true,
  })

  async function handleResolve(id) {
    try {
      await accidentApi.resolve(id)
      useAccidentStore.getState().updateAccident(id, { status: 'RESOLVED' })
      toast.success('Incident resolved')
    } catch { toast.error('Failed') }
  }

  async function handleSimulate() {
    try {
      await accidentApi.simulate({ severity: 'HIGH', confidence_score: 0.91 })
      toast.success('Simulated accident created')
    } catch (e) { toast.error(e.response?.data?.detail || 'Simulation failed') }
  }

  const incidents = data?.data || []
  const total = data?.total || 0

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      {/* Topbar */}
      <div className="topbar">
        <button className="btn btn-ghost" onClick={() => navigate('/')}>← Map</button>
        <div style={{ fontWeight: 700, marginLeft: 12 }}>Incident Management</div>
        <div className="topbar-spacer" />
        <button className="btn btn-danger" onClick={handleSimulate}>🚨 Simulate Accident</button>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: 10, padding: '12px 20px', background: 'var(--bg-secondary)', borderBottom: '1px solid var(--border)' }}>
        {[
          { label: 'Severity', value: severity, set: setSeverity, opts: SEVERITIES },
          { label: 'Source', value: source, set: setSource, opts: SOURCES },
          { label: 'Status', value: status, set: setStatus, opts: STATUSES },
        ].map(({ label, value, set, opts }) => (
          <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>{label}</span>
            <select
              value={value} onChange={e => { set(e.target.value); setPage(1) }}
              style={{ background: 'var(--bg-input)', border: '1px solid var(--border)', color: 'var(--text-primary)', borderRadius: 6, padding: '4px 10px', fontSize: '0.78rem' }}
            >
              {opts.map(o => <option key={o}>{o}</option>)}
            </select>
          </div>
        ))}
        <div style={{ marginLeft: 'auto', fontSize: '0.75rem', color: 'var(--text-muted)', alignSelf: 'center' }}>
          {total} incidents
        </div>
      </div>

      {/* Table */}
      <div style={{ flex: 1, overflow: 'auto', padding: '16px 20px' }}>
        {isLoading ? (
          <div style={{ textAlign: 'center', paddingTop: 80, color: 'var(--text-muted)' }}>Loading…</div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                {['Time', 'Severity', 'Source', 'Location', 'Confidence', 'Status', 'Actions'].map(h => (
                  <th key={h} style={{ padding: '8px 12px', textAlign: 'left', borderBottom: '1px solid var(--border)' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {incidents.map((inc, i) => (
                <motion.tr
                  key={inc.id}
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.02 }}
                  style={{ borderBottom: '1px solid var(--border)', cursor: 'pointer', transition: 'background 0.15s' }}
                  onClick={() => setSelected(inc === selected ? null : inc)}
                  onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-card-hover)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                >
                  <td style={{ padding: '10px 12px', fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                    {dayjs(inc.detected_at).format('DD/MM HH:mm:ss')}
                  </td>
                  <td style={{ padding: '10px 12px' }}>
                    <span className={`severity-badge ${inc.severity?.toLowerCase()}`}>{inc.severity}</span>
                  </td>
                  <td style={{ padding: '10px 12px', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{inc.source}</td>
                  <td style={{ padding: '10px 12px', fontSize: '0.75rem', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {inc.address || `${inc.latitude?.toFixed(4)}, ${inc.longitude?.toFixed(4)}`}
                  </td>
                  <td style={{ padding: '10px 12px', fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: inc.confidence_score > 0.85 ? 'var(--accent-red)' : 'var(--text-secondary)' }}>
                    {inc.confidence_score ? `${(inc.confidence_score * 100).toFixed(1)}%` : '—'}
                  </td>
                  <td style={{ padding: '10px 12px', fontSize: '0.72rem', color: inc.status === 'RESOLVED' ? 'var(--accent-green)' : 'var(--text-primary)' }}>
                    {inc.status}
                  </td>
                  <td style={{ padding: '10px 12px' }}>
                    {inc.status !== 'RESOLVED' && (
                      <button className="btn btn-ghost" style={{ fontSize: '0.65rem', padding: '3px 10px' }}
                        onClick={(e) => { e.stopPropagation(); handleResolve(inc.id) }}>
                        Resolve
                      </button>
                    )}
                    {inc.screenshot_url && (
                      <a href={inc.screenshot_url} target="_blank" rel="noreferrer"
                        style={{ fontSize: '0.65rem', color: 'var(--accent-blue)', marginLeft: 8 }} onClick={e => e.stopPropagation()}>
                        📷
                      </a>
                    )}
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        )}

        {/* Pagination */}
        <div style={{ display: 'flex', justifyContent: 'center', gap: 12, paddingTop: 20 }}>
          <button className="btn btn-ghost" disabled={page === 1} onClick={() => setPage(p => p - 1)}>← Prev</button>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', alignSelf: 'center' }}>
            Page {page} · {total} total
          </span>
          <button className="btn btn-ghost" disabled={incidents.length < 25} onClick={() => setPage(p => p + 1)}>Next →</button>
        </div>
      </div>
    </div>
  )
}
