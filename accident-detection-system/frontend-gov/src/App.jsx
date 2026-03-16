import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store'
import { useGovWebSocket } from './hooks/useWebSocket'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import IncidentsPage from './pages/IncidentsPage'
import AnalyticsPage from './pages/AnalyticsPage'

function ProtectedApp() {
  useGovWebSocket()
  return (
    <Routes>
      <Route path="/" element={<DashboardPage />} />
      <Route path="/incidents" element={<IncidentsPage />} />
      <Route path="/analytics" element={<AnalyticsPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default function App() {
  const { accessToken } = useAuthStore()
  if (!accessToken) return <LoginPage />
  return <ProtectedApp />
}
