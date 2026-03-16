import { motion, AnimatePresence } from 'framer-motion'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import { useAlertStore } from '../store'

dayjs.extend(relativeTime)

const SEV_COLOR = { CRITICAL: '#ff1744', HIGH: '#ff6d00', MEDIUM: '#ffd600', LOW: '#00c853' }
const SEV_CLS = { CRITICAL: 'critical', HIGH: 'high', MEDIUM: 'medium', LOW: 'low' }

export default function AlertsPage() {
  const { alerts, nearbyCount, clearNew } = useAlertStore()

  return (
    <div className="alerts-page" onClick={clearNew}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
        <h2 style={{ fontSize: '1rem', fontWeight: 700 }}>Nearby Accidents</h2>
        {nearbyCount > 0 && (
          <span style={{
            background: 'rgba(255,59,59,.15)', color: '#ff3b3b',
            border: '1px solid rgba(255,59,59,.4)',
            borderRadius: 20, fontSize: '0.7rem', padding: '2px 10px', fontWeight: 600
          }}>
            {nearbyCount} NEW
          </span>
        )}
      </div>

      <AnimatePresence initial={false}>
        {alerts.length === 0 && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }}
            style={{ textAlign: 'center', paddingTop: 60, color: 'var(--muted)' }}
          >
            <div style={{ fontSize: 40, marginBottom: 12 }}>✅</div>
            <div style={{ fontWeight: 600 }}>All Clear</div>
            <div style={{ fontSize: '0.8rem', marginTop: 6 }}>No accidents reported nearby</div>
          </motion.div>
        )}

        {alerts.map((a, i) => {
          const lat = a.latitude ?? a.lat
          const lon = a.longitude ?? a.lon
          return (
            <motion.div
              key={a.id}
              initial={{ opacity: 0, x: 30 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -30 }}
              transition={{ delay: i < 5 ? i * 0.04 : 0 }}
              className={`alert-card ${SEV_CLS[a.severity] || 'medium'}`}
            >
              <div className="alert-card-head">
                <span className={`sev-chip sev-${SEV_CLS[a.severity] || 'medium'}`}>{a.severity}</span>
                <span className="alert-time">{dayjs(a.detected_at).fromNow()}</span>
              </div>
              <div className="alert-addr">
                {a.address || (lat && lon ? `${lat.toFixed(4)}, ${lon.toFixed(4)}` : 'Location unknown')}
              </div>
              <div className="alert-meta">
                <span>📡 {a.source?.replace('_', ' ') || 'Unknown'}</span>
                {a.confidence_score && (
                  <span>🤖 {(a.confidence_score * 100).toFixed(1)}%</span>
                )}
                {a.status && <span style={{ color: a.status === 'RESOLVED' ? '#00e676' : 'inherit' }}>
                  {a.status === 'RESOLVED' ? '✅ Resolved' : '🔴 Active'}
                </span>}
              </div>
              {a.screenshot_url && (
                <a
                  href={a.screenshot_url}
                  target="_blank" rel="noreferrer"
                  style={{ display: 'block', marginTop: 10, fontSize: '0.75rem', color: 'var(--accent)' }}
                >
                  📷 View Screenshot
                </a>
              )}
              {a._new && (
                <div style={{
                  position: 'absolute', top: 10, right: 10,
                  background: '#ff3b3b', borderRadius: 20,
                  width: 8, height: 8,
                }} />
              )}
            </motion.div>
          )
        })}
      </AnimatePresence>
    </div>
  )
}
