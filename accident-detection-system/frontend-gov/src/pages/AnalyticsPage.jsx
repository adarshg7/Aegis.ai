import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { BarChart, Bar, XAxis, YAxis, Tooltip, PieChart, Pie, Cell, ResponsiveContainer, LineChart, Line, CartesianGrid } from 'recharts'
import { accidentApi } from '../services/api'

const COLORS = { CRITICAL: '#ff1744', HIGH: '#ff6d00', MEDIUM: '#ffd600', LOW: '#00c853' }

const CHART_STYLE = {
  background: 'var(--bg-card)',
  border: '1px solid var(--border)',
  borderRadius: 12,
  padding: 20,
}

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: 8, padding: '8px 12px', fontSize: '0.78rem' }}>
      <div style={{ color: 'var(--text-secondary)', marginBottom: 4 }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.fill || p.color || 'var(--accent-blue)' }}>
          {p.name}: <strong>{p.value}</strong>
        </div>
      ))}
    </div>
  )
}

export default function AnalyticsPage() {
  const navigate = useNavigate()

  const { data, isLoading } = useQuery({
    queryKey: ['analytics'],
    queryFn: () => accidentApi.analytics().then(r => r.data),
    refetchInterval: 60_000,
  })

  const bySeverity = Object.entries(data?.accidents_by_severity || {}).map(([name, value]) => ({ name, value }))
  const byHour = (data?.accidents_by_hour || []).map(r => ({
    hour: r.hour ? new Date(r.hour).getHours() + ':00' : '',
    count: r.count,
  }))

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      <div className="topbar">
        <button className="btn btn-ghost" onClick={() => navigate('/')}>← Map</button>
        <div style={{ fontWeight: 700, marginLeft: 12 }}>Analytics & Intelligence</div>
      </div>

      {isLoading ? (
        <div style={{ textAlign: 'center', paddingTop: 80, color: 'var(--text-muted)' }}>Computing analytics…</div>
      ) : (
        <div style={{ flex: 1, overflow: 'auto', display: 'grid', gridTemplateColumns: '1fr 1fr', gridTemplateRows: 'auto 1fr', gap: 16, padding: 20 }}>

          {/* KPI row */}
          <div style={{ gridColumn: '1 / -1', display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 12 }}>
            {[
              { label: 'Total Accidents', value: data?.total_accidents ?? 0, color: '#3875ff' },
              { label: 'Avg Response Time', value: data?.avg_response_time_minutes ? `${data.avg_response_time_minutes.toFixed(1)} min` : 'N/A', color: '#00d4ff' },
              { label: 'Hotspots', value: data?.hotspots?.length ?? 0, color: '#ff8c00' },
            ].map(({ label, value, color }) => (
              <div key={label} className="stat-card" style={{ '--accent-color': color }}>
                <div className="stat-value" style={{ color }}>{value}</div>
                <div className="stat-label">{label}</div>
              </div>
            ))}
          </div>

          {/* Severity Pie */}
          <div style={CHART_STYLE}>
            <div className="card-title" style={{ marginBottom: 16 }}>Accidents by Severity</div>
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie data={bySeverity} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                  {bySeverity.map((entry) => (
                    <Cell key={entry.name} fill={COLORS[entry.name] || '#888'} />
                  ))}
                </Pie>
                <Tooltip content={<ChartTooltip />} />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Hourly bar */}
          <div style={CHART_STYLE}>
            <div className="card-title" style={{ marginBottom: 16 }}>Accidents Last 24 Hours</div>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={byHour}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="hour" tick={{ fill: '#8a9bbf', fontSize: 10 }} />
                <YAxis tick={{ fill: '#8a9bbf', fontSize: 10 }} />
                <Tooltip content={<ChartTooltip />} />
                <Bar dataKey="count" fill="#3875ff" name="Accidents" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  )
}
