import { useState } from 'react'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { authApi } from '../services/api'
import { useAuthStore } from '../store'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const { setTokens, setUser } = useAuthStore()

  async function handleLogin(e) {
    e.preventDefault()
    setLoading(true)
    try {
      const { data } = await authApi.login(email, password)
      setTokens(data.access_token, data.refresh_token)
      const { data: user } = await authApi.me()
      setUser(user)
      toast.success('Access granted')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Access denied')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <motion.div
        className="login-card"
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <div className="login-logo">
          <div style={{ fontSize: 40, marginBottom: 12 }}>🛡️</div>
          <h1>Command Center</h1>
          <p>AI Accident Detection — Government Access</p>
        </div>

        <form onSubmit={handleLogin}>
          <div className="form-group">
            <label className="form-label">Government Email</label>
            <input
              id="gov-email"
              type="email"
              className="form-input"
              placeholder="officer@gov.in"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="username"
            />
          </div>
          <div className="form-group">
            <label className="form-label">Secure Password</label>
            <input
              id="gov-password"
              type="password"
              className="form-input"
              placeholder="••••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
          </div>
          <button className="login-submit" type="submit" disabled={loading}>
            {loading ? 'Authenticating…' : 'Access System →'}
          </button>
        </form>

        <div style={{ marginTop: 24, textAlign: 'center', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
          Unauthorized access will be prosecuted. All sessions are logged.
        </div>
      </motion.div>
    </div>
  )
}
