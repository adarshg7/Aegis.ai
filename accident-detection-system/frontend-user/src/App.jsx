import { Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore, useAlertStore } from './store'
import { useEffect, useRef, useCallback } from 'react'
import toast from 'react-hot-toast'
import LoginPage from './pages/LoginPage'
import MapPage from './pages/MapPage'
import AlertsPage from './pages/AlertsPage'
import SOSPage from './pages/SOSPage'
import 'leaflet/dist/leaflet.css'

const WS_BASE = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'

function DriverWebSocket() {
  const { accessToken } = useAuthStore()
  const { addAlert, setWsConnected } = useAlertStore()
  const ws = useRef(null)
  const timer = useRef(null)

  const connect = useCallback(() => {
    if (!accessToken) return
    const socket = new WebSocket(`${WS_BASE}/ws/drivers?token=${accessToken}`)
    ws.current = socket
    socket.onopen = () => {
      setWsConnected(true)
      timer.current = setInterval(() => socket.readyState === 1 && socket.send(JSON.stringify({ type: 'ping' })), 25000)
    }
    socket.onmessage = ({ data }) => {
      try {
        const msg = JSON.parse(data)
        if (msg.type === 'accident.new') {
          addAlert(msg.payload)
          toast.custom(() => (
            <div style={{
              background: '#111827', border: '1px solid #ff3b3b', borderRadius: 12,
              padding: '12px 16px', color: '#e8edf5', minWidth: 260,
            }}>
              <div style={{ fontWeight: 700, color: '#ff3b3b', marginBottom: 4 }}>⚠️ Accident Nearby!</div>
              <div style={{ fontSize: '0.82rem' }}>{msg.payload.address || 'Near your location'}</div>
              <div style={{ fontSize: '0.72rem', opacity: 0.6, marginTop: 2 }}>{msg.payload.severity} severity</div>
            </div>
          ), { duration: 8000 })
        }
      } catch {}
    }
    socket.onclose = () => {
      setWsConnected(false)
      clearInterval(timer.current)
      setTimeout(connect, 3000)
    }
    socket.onerror = () => socket.close()
  }, [accessToken, addAlert, setWsConnected])

  useEffect(() => {
    connect()
    return () => { clearInterval(timer.current); ws.current?.close() }
  }, [connect])

  return null
}

function BottomNav() {
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const { nearbyCount } = useAlertStore()
  const tabs = [
    { path: '/', icon: '🗺️', label: 'Map' },
    { path: '/alerts', icon: '🔔', label: `Alerts${nearbyCount ? ` (${nearbyCount})` : ''}` },
    { path: '/sos', icon: '🚨', label: 'SOS' },
  ]
  return (
    <nav className="bottom-nav">
      {tabs.map(({ path, icon, label }) => (
        <button
          key={path}
          className={`nav-tab ${pathname === path ? 'active' : ''}`}
          onClick={() => navigate(path)}
        >
          <span className="icon">{icon}</span>
          <span>{label}</span>
        </button>
      ))}
    </nav>
  )
}

function ProtectedDriver() {
  return (
    <>
      <DriverWebSocket />
      <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <Routes>
          <Route path="/" element={<MapPage />} />
          <Route path="/alerts" element={<AlertsPage />} />
          <Route path="/sos" element={<SOSPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
      <BottomNav />
    </>
  )
}

export default function App() {
  const { accessToken } = useAuthStore()
  if (!accessToken) return <LoginPage />
  return <ProtectedDriver />
}
