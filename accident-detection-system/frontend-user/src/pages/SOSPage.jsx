import { useState } from 'react'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { accidentApi } from '../services/api'

export default function SOSPage() {
  const [status, setStatus] = useState('idle')  // idle | sending | sent
  const [pos, setPos] = useState(null)

  async function handleSOS() {
    if (status !== 'idle') return
    setStatus('sending')

    // Get GPS position
    let lat, lon
    try {
      const coords = await new Promise((res, rej) =>
        navigator.geolocation.getCurrentPosition(res, rej, { enableHighAccuracy: true, timeout: 5000 })
      )
      lat = coords.coords.latitude
      lon = coords.coords.longitude
      setPos([lat, lon])
    } catch {
      lat = 28.6139; lon = 77.2090   // Delhi fallback
    }

    try {
      await accidentApi.report({
        latitude: lat, longitude: lon,
        severity: 'CRITICAL',
        source: 'USER_REPORT',
        confidence_score: 1.0,
        metadata: { sos: true, reported_via: 'driver_app' },
      })
      setStatus('sent')
      toast.success('SOS sent! Emergency services notified.')
    } catch (e) {
      toast.error('SOS failed. Call 112 immediately.')
      setStatus('idle')
    }
  }

  function reset() {
    setStatus('idle')
    setPos(null)
  }

  return (
    <div className="sos-page">
      <div style={{ textAlign: 'center' }}>
        <h1 style={{ fontSize: '1.3rem', fontWeight: 800 }}>Emergency SOS</h1>
        <p style={{ color: 'var(--muted)', fontSize: '0.82rem', marginTop: 4 }}>
          Tap to alert emergency services + notify nearby people
        </p>
      </div>

      <motion.button
        className={`sos-btn ${status === 'sent' ? 'sent' : ''}`}
        onClick={handleSOS}
        disabled={status === 'sending'}
        whileTap={{ scale: 0.92 }}
        animate={status === 'sending' ? { scale: [1, 1.05, 1], transition: { repeat: Infinity, duration: 0.6 } } : {}}
      >
        <span className="sos-icon">
          {status === 'idle' ? '🚨' : status === 'sending' ? '📡' : '✅'}
        </span>
        <span>
          {status === 'idle' ? 'SOS' : status === 'sending' ? 'Sending…' : 'Sent!'}
        </span>
      </motion.button>

      <div className="sos-info">
        {status === 'idle' && (
          <>
            <div className="sos-status" style={{ color: 'var(--muted)' }}>Ready</div>
            <p style={{ marginTop: 8 }}>
              Press SOS to instantly alert ambulance, police,<br />
              and up to 500 nearby drivers and local businesses.
            </p>
          </>
        )}
        {status === 'sending' && (
          <div className="sos-status" style={{ color: 'var(--warning)' }}>
            📍 Getting your location & alerting emergency services…
          </div>
        )}
        {status === 'sent' && (
          <>
            <div className="sos-status" style={{ color: '#00e676' }}>✅ Emergency services notified</div>
            {pos && (
              <p style={{ marginTop: 6, fontSize: '0.78rem', color: 'var(--muted)' }}>
                GPS: {pos[0].toFixed(5)}, {pos[1].toFixed(5)}
              </p>
            )}
            <p style={{ marginTop: 8 }}>Ambulance + Police alerted. Nearby users notified.</p>
            <button
              onClick={reset}
              style={{
                marginTop: 16, background: 'transparent', border: '1px solid var(--border)',
                color: 'var(--muted)', borderRadius: 8, padding: '8px 20px',
                cursor: 'pointer', fontSize: '0.82rem', fontFamily: 'var(--font)',
              }}
            >
              Reset
            </button>
          </>
        )}
      </div>

      {/* Emergency numbers */}
      <div style={{ width: '100%', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        {[['🚑 Ambulance', '108'], ['🚔 Police', '100'],['🔥 Fire', '101'], ['📞 Emergency', '112']].map(([label, num]) => (
          <a
            key={num}
            href={`tel:${num}`}
            style={{
              display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
              background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12,
              padding: '12px', textDecoration: 'none', color: 'var(--text)', transition: 'var(--t)',
            }}
            onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--accent)'}
            onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--border)'}
          >
            <span style={{ fontSize: '1.3rem' }}>{label.split(' ')[0]}</span>
            <span style={{ fontWeight: 700, fontSize: '1.1rem' }}>{num}</span>
            <span style={{ fontSize: '0.68rem', color: 'var(--muted)' }}>{label.split(' ')[1]}</span>
          </a>
        ))}
      </div>
    </div>
  )
}
