/**
 * useWebSocket — connects to /ws/gov, dispatches incoming accident events
 * to the global Zustand store, and shows toast notifications.
 */
import { useEffect, useRef, useCallback } from 'react'
import toast from 'react-hot-toast'
import { useAuthStore, useAccidentStore } from '../store'

const WS_BASE = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'
const RECONNECT_INTERVAL = 3000
const PING_INTERVAL = 25000

export function useGovWebSocket() {
  const { accessToken } = useAuthStore()
  const { prependAccident, updateAccident, setWsConnected } = useAccidentStore()
  const ws = useRef(null)
  const pingTimer = useRef(null)
  const reconnectTimer = useRef(null)

  const handleMessage = useCallback((raw) => {
    try {
      const msg = JSON.parse(raw)
      switch (msg.type) {
        case 'accident.new':
          prependAccident(msg.payload)
          toast.custom(
            <div className="accident-toast" style={{ padding: '12px 16px', minWidth: 280 }}>
              <div style={{ fontWeight: 700, color: '#ff3b3b', marginBottom: 4 }}>
                🚨 NEW ACCIDENT — {msg.payload.severity}
              </div>
              <div style={{ fontSize: '0.82rem', opacity: 0.85 }}>
                {msg.payload.address || `${msg.payload.lat?.toFixed(4)}, ${msg.payload.lon?.toFixed(4)}`}
              </div>
              <div style={{ fontSize: '0.72rem', opacity: 0.6, marginTop: 4 }}>
                Confidence: {((msg.payload.confidence_score || 0) * 100).toFixed(1)}%
              </div>
            </div>,
            { duration: 8000 }
          )
          break
        case 'accident.resolved':
          updateAccident(msg.payload.id, { status: 'RESOLVED' })
          break
        case 'connected':
          setWsConnected(true)
          break
        default:
          break
      }
    } catch (e) {
      console.warn('WS parse error', e)
    }
  }, [prependAccident, updateAccident, setWsConnected])

  const connect = useCallback(() => {
    if (!accessToken) return
    if (ws.current?.readyState === WebSocket.OPEN) return

    const socket = new WebSocket(`${WS_BASE}/ws/gov?token=${accessToken}`)
    ws.current = socket

    socket.onopen = () => {
      setWsConnected(true)
      // Start pinging
      pingTimer.current = setInterval(() => {
        if (socket.readyState === WebSocket.OPEN) {
          socket.send(JSON.stringify({ type: 'ping' }))
        }
      }, PING_INTERVAL)
    }

    socket.onmessage = (e) => handleMessage(e.data)

    socket.onclose = () => {
      setWsConnected(false)
      clearInterval(pingTimer.current)
      // Auto-reconnect
      reconnectTimer.current = setTimeout(connect, RECONNECT_INTERVAL)
    }

    socket.onerror = () => socket.close()
  }, [accessToken, handleMessage, setWsConnected])

  useEffect(() => {
    connect()
    return () => {
      clearInterval(pingTimer.current)
      clearTimeout(reconnectTimer.current)
      ws.current?.close()
    }
  }, [connect])
}
