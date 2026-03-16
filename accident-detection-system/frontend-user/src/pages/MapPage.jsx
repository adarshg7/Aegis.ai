import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from 'react-leaflet'
import { useQuery } from '@tanstack/react-query'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import { useAlertStore } from '../store'
import { accidentApi } from '../services/api'

dayjs.extend(relativeTime)

const SEV_COLOR = { CRITICAL: '#ff1744', HIGH: '#ff6d00', MEDIUM: '#ffd600', LOW: '#00c853' }

function UserLocationMarker({ setUserPos }) {
  const map = useMap()
  useEffect(() => {
    if (!navigator.geolocation) return
    const id = navigator.geolocation.watchPosition(
      ({ coords }) => {
        setUserPos([coords.latitude, coords.longitude])
        map.setView([coords.latitude, coords.longitude], map.getZoom() < 12 ? 14 : map.getZoom())
      },
      () => {},
      { enableHighAccuracy: true }
    )
    return () => navigator.geolocation.clearWatch(id)
  }, [map, setUserPos])
  return null
}

function RecentAlertBanner({ alerts }) {
  const latest = alerts.find(a => a._new)
  if (!latest) return null
  return (
    <div className="alert-banner" style={{ position: 'absolute', top: 12, left: 12, right: 12, zIndex: 1000 }}>
      <div className="alert-dot" style={{ background: SEV_COLOR[latest.severity] || '#ff3b3b' }} />
      <div>
        <div style={{ fontWeight: 700, fontSize: '0.88rem' }}>⚠️ Accident Detected — {latest.severity}</div>
        <div style={{ fontSize: '0.75rem', opacity: 0.75, marginTop: 2 }}>
          {latest.address || `${latest.lat?.toFixed(4) || ''}, ${latest.lon?.toFixed(4) || ''}`}
        </div>
      </div>
    </div>
  )
}

export default function MapPage() {
  const [userPos, setUserPos] = useState([20.5937, 78.9629])
  const { alerts, setAlerts } = useAlertStore()

  const { data } = useQuery({
    queryKey: ['driver-accidents'],
    queryFn: () => accidentApi.list({ page_size: 50, page: 1 }).then(r => r.data),
    refetchInterval: 30_000,
    onSuccess: d => setAlerts(d.data || []),
  })

  useEffect(() => { if (data?.data) setAlerts(data.data) }, [data, setAlerts])

  // Merge API accidents with real-time WebSocket alerts
  const allMarkers = alerts

  return (
    <div className="map-page">
      <div className="map-fill">
        <MapContainer center={userPos} zoom={12} style={{ height: '100%', width: '100%' }} zoomControl={false}>
          <TileLayer url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png" attribution='&copy; CARTO' />
          <UserLocationMarker setUserPos={setUserPos} />

          {/* User position */}
          <CircleMarker
            center={userPos}
            radius={8}
            pathOptions={{ color: '#3875ff', fillColor: '#3875ff', fillOpacity: 1, weight: 3 }}
          >
            <Popup><strong>You are here</strong></Popup>
          </CircleMarker>

          {/* Accident markers */}
          {allMarkers.map(a => {
            const lat = a.latitude ?? a.lat
            const lon = a.longitude ?? a.lon
            if (!lat || !lon) return null
            return (
              <CircleMarker
                key={a.id}
                center={[lat, lon]}
                radius={a.severity === 'CRITICAL' ? 14 : 9}
                pathOptions={{
                  color: SEV_COLOR[a.severity] || '#888',
                  fillColor: SEV_COLOR[a.severity] || '#888',
                  fillOpacity: 0.75,
                  weight: a._new ? 3 : 1,
                }}
              >
                <Popup>
                  <div style={{ fontFamily: 'Inter,sans-serif', minWidth: 160 }}>
                    <strong style={{ color: SEV_COLOR[a.severity] }}>{a.severity}</strong>
                    <div style={{ fontSize: 12, marginTop: 4 }}>{a.address || `${lat.toFixed(4)}, ${lon.toFixed(4)}`}</div>
                    <div style={{ fontSize: 11, opacity: 0.6, marginTop: 2 }}>{dayjs(a.detected_at).fromNow()}</div>
                  </div>
                </Popup>
              </CircleMarker>
            )
          })}
        </MapContainer>
        <RecentAlertBanner alerts={allMarkers} />
      </div>
    </div>
  )
}
