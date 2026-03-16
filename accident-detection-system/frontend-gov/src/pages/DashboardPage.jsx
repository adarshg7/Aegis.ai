import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from 'react-leaflet'
import { motion, AnimatePresence } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import toast from 'react-hot-toast'
import { useAccidentStore, useAuthStore } from '../store'
import { accidentApi } from '../services/api'
import 'leaflet/dist/leaflet.css'

dayjs.extend(relativeTime)

const SEVERITY_COLOR = {
  CRITICAL: '#ff1744', HIGH: '#ff6d00', MEDIUM: '#ffd600', LOW: '#00c853',
}

function MapMarkers({ accidents, onSelect }) {
  return accidents.map((a) => (
    <CircleMarker
      key={a.id}
      center={[a.latitude ?? a.lat ?? 28.6, a.longitude ?? a.lon ?? 77.2]}
      radius={a.severity === 'CRITICAL' ? 12 : a.severity === 'HIGH' ? 9 : 7}
      pathOptions={{
        color: SEVERITY_COLOR[a.severity] || '#888',
        fillColor: SEVERITY_COLOR[a.severity] || '#888',
        fillOpacity: 0.8,
        weight: a._isNew ? 3 : 1,
      }}
      eventHandlers={{ click: () => onSelect(a) }}
    >
      <Popup>
        <div style={{ fontFamily: 'Inter,sans-serif', minWidth: 180 }}>
          <strong style={{ color: SEVERITY_COLOR[a.severity] }}>{a.severity}</strong>
          <div style={{ fontSize: 12, marginTop: 4 }}>{a.address || 'Location unavailable'}</div>
          <div style={{ fontSize: 11, opacity: 0.7, marginTop: 2 }}>
            {dayjs(a.detected_at).fromNow()}
            {a.confidence_score ? ` · ${(a.confidence_score * 100).toFixed(1)}% conf` : ''}
          </div>
        </div>
      </Popup>
    </CircleMarker>
  ))
}

function FlyToSelected({ selected }) {
  const map = useMap()
  useEffect(() => {
    if (selected) {
      map.flyTo(
        [selected.latitude ?? selected.lat, selected.longitude ?? selected.lon],
        15, { duration: 1 }
      )
    }
  }, [selected, map])
  return null
}

function Topbar({ wsConnected }) {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()
  return (
    <div className="topbar">
      <div className="topbar-logo">
        <div className="topbar-logo-icon">🚨</div>
        <div>
          <div style={{ fontWeight: 700 }}>AI Accident Detection</div>
          <div className="topbar-title">Government Command Center</div>
        </div>
      </div>
      <div className="topbar-spacer" />
      <div className="conn-status">
        <div className={`conn-dot ${wsConnected ? 'connected' : 'disconnected'}`} />
        {wsConnected ? 'Live' : 'Reconnecting…'}
      </div>
      <div className="live-badge">
        <div className="live-dot" /> LIVE
      </div>
      <nav style={{ display: 'flex', gap: 4 }}>
        {[['/', '🗺️ Map'], ['/incidents', '📋 Incidents'], ['/analytics', '📊 Analytics']].map(([to, label]) => (
          <button key={to} className="btn btn-ghost" style={{ fontSize: '0.75rem', padding: '6px 12px' }}
            onClick={() => navigate(to)}>{label}</button>
        ))}
      </nav>
      <button className="btn btn-ghost" style={{ fontSize: '0.75rem' }} onClick={logout}>
        Sign Out
      </button>
    </div>
  )
}

function StatCards({ accidents }) {
  const counts = accidents.reduce((acc, a) => {
    acc[a.severity] = (acc[a.severity] || 0) + 1; return acc
  }, {})
  const active = accidents.filter(a => a.status !== 'RESOLVED').length

  return (
    <div className="stats-grid" style={{ padding: '12px 16px 0', gridTemplateColumns: 'repeat(4,1fr)', gap: 10 }}>
      {[
        { label: 'Total Detected', value: accidents.length, color: '#3875ff' },
        { label: 'Active Incidents', value: active, color: '#ff3b3b' },
        { label: 'Critical', value: counts.CRITICAL || 0, color: '#ff1744' },
        { label: 'High', value: counts.HIGH || 0, color: '#ff6d00' },
      ].map(({ label, value, color }) => (
        <div className="stat-card" key={label} style={{ '--accent-color': color }}>
          <div className="stat-value" style={{ color }}>{value}</div>
          <div className="stat-label">{label}</div>
        </div>
      ))}
    </div>
  )
}

function IncidentPanel({ accidents, selectedId, onSelect, onResolve }) {
  return (
    <div className="incident-panel">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
        <div className="card-title">Live Incidents</div>
        <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{accidents.length} events</span>
      </div>
      <AnimatePresence initial={false}>
        {accidents.map((a) => (
          <motion.div
            key={a.id}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.25 }}
            className={`incident-item ${a.severity?.toLowerCase()} ${selectedId === a.id ? 'active' : ''}`}
            onClick={() => onSelect(a)}
            style={{ marginBottom: 8, borderColor: selectedId === a.id ? 'var(--accent-blue)' : undefined }}
          >
            <div className="incident-header">
              <span className={`severity-badge ${a.severity?.toLowerCase()}`}>{a.severity}</span>
              <span className="incident-time">{dayjs(a.detected_at).fromNow()}</span>
            </div>
            <div className="incident-address">{a.address || `${(a.latitude ?? a.lat)?.toFixed(4)}, ${(a.longitude ?? a.lon)?.toFixed(4)}`}</div>
            <div className="incident-meta">
              <span>📍 {a.source?.replace('_', ' ')}</span>
              {a.confidence_score && (
                <span className="incident-confidence">🤖 {(a.confidence_score * 100).toFixed(1)}%</span>
              )}
              {a.status === 'RESOLVED'
                ? <span style={{ color: 'var(--accent-green)' }}>✅ Resolved</span>
                : (
                  <button
                    className="btn btn-ghost"
                    style={{ fontSize: '0.65rem', padding: '2px 8px' }}
                    onClick={(e) => { e.stopPropagation(); onResolve(a.id) }}
                  >Resolve</button>
                )}
            </div>
          </motion.div>
        ))}
      </AnimatePresence>
      {accidents.length === 0 && (
        <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.82rem', paddingTop: 40 }}>
          No incidents detected
        </div>
      )}
    </div>
  )
}

export default function DashboardPage() {
  const { accidents, selectedId, wsConnected, setAccidents, selectAccident } = useAccidentStore()
  const [mapCenter] = useState([20.5937, 78.9629]) // India center
  const selectedAccident = accidents.find(a => a.id === selectedId) || null

  const { data } = useQuery({
    queryKey: ['accidents'],
    queryFn: () => accidentApi.list({ page_size: 100, page: 1 }).then(r => r.data),
    refetchInterval: 30_000,
    onSuccess: (d) => setAccidents(d.data || []),
  })

  useEffect(() => {
    if (data?.data) setAccidents(data.data)
  }, [data, setAccidents])

  async function handleResolve(id) {
    try {
      await accidentApi.resolve(id)
      toast.success('Incident resolved')
      useAccidentStore.getState().updateAccident(id, { status: 'RESOLVED' })
    } catch {
      toast.error('Failed to resolve')
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      <Topbar wsConnected={wsConnected} />
      <StatCards accidents={accidents} />
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden', padding: '12px 16px 16px' }}>
        {/* Map */}
        <div style={{ flex: 1, borderRadius: 12, overflow: 'hidden', border: '1px solid var(--border)', position: 'relative' }}>
          <MapContainer
            center={mapCenter}
            zoom={5}
            style={{ height: '100%', width: '100%' }}
            zoomControl={true}
          >
            <TileLayer
              url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
              attribution='&copy; <a href="https://carto.com">CARTO</a>'
            />
            <MapMarkers accidents={accidents} onSelect={selectAccident} />
            <FlyToSelected selected={selectedAccident} />
          </MapContainer>

          {/* Legend */}
          <div className="map-legend">
            <div style={{ fontWeight: 600, marginBottom: 6, fontSize: '0.7rem', color: 'var(--text-secondary)' }}>SEVERITY</div>
            {Object.entries(SEVERITY_COLOR).map(([s, c]) => (
              <div className="legend-item" key={s}>
                <div className="legend-dot" style={{ background: c }} />
                <span style={{ color: 'var(--text-secondary)' }}>{s}</span>
              </div>
            ))}
          </div>
        </div>
        {/* Incident sidebar */}
        <IncidentPanel
          accidents={accidents}
          selectedId={selectedId}
          onSelect={(a) => selectAccident(a.id)}
          onResolve={handleResolve}
        />
      </div>
    </div>
  )
}
