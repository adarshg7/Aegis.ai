import { useState } from 'react'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { authApi } from '../services/api'
import { useAuthStore } from '../store'

export default function LoginPage() {
  const [mode, setMode] = useState('login')   // 'login' | 'register'
  const [form, setForm] = useState({ email: '', password: '', full_name: '', phone: '' })
  const [loading, setLoading] = useState(false)
  const { setTokens, setUser } = useAuthStore()

  const set = (k) => (e) => setForm(f => ({ ...f, [k]: e.target.value }))

  async function submit(e) {
    e.preventDefault()
    setLoading(true)
    try {
      if (mode === 'register') {
        await authApi.register({ email: form.email, password: form.password, full_name: form.full_name, phone: form.phone })
        toast.success('Account created! Please sign in.')
        setMode('login')
      } else {
        const { data } = await authApi.login(form.email, form.password)
        setTokens(data.access_token, data.refresh_token)
        const { data: user } = await authApi.me()
        setUser(user)
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-pwa">
      <motion.div className="login-pwa-card" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <div style={{ fontSize: 44 }}>🚗</div>
          <h1 style={{ fontSize: '1.4rem', fontWeight: 800, marginTop: 8 }}>Road Alert</h1>
          <p style={{ color: 'var(--muted)', fontSize: '0.82rem', marginTop: 4 }}>AI-Powered Accident Detection</p>
        </div>

        <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
          {['login', 'register'].map(m => (
            <button key={m} onClick={() => setMode(m)} style={{
              flex: 1, padding: '8px', borderRadius: 8, border: 'none', cursor: 'pointer',
              background: mode === m ? 'var(--accent)' : 'var(--bg)',
              color: mode === m ? 'white' : 'var(--muted)', fontWeight: 600, fontSize: '0.85rem',
              fontFamily: 'var(--font)', transition: 'var(--t)',
            }}>
              {m === 'login' ? 'Sign In' : 'Register'}
            </button>
          ))}
        </div>

        <form onSubmit={submit}>
          {mode === 'register' && (
            <>
              <input className="pwa-form-input" placeholder="Full name" required value={form.full_name} onChange={set('full_name')} />
              <input className="pwa-form-input" placeholder="Phone (+91...)" value={form.phone} onChange={set('phone')} />
            </>
          )}
          <input className="pwa-form-input" type="email" placeholder="Email" required value={form.email} onChange={set('email')} autoComplete="username" />
          <input className="pwa-form-input" type="password" placeholder="Password" required value={form.password} onChange={set('password')} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} />
          <button className="pwa-submit" type="submit" disabled={loading}>
            {loading ? '…' : mode === 'login' ? 'Sign In →' : 'Create Account →'}
          </button>
        </form>
      </motion.div>
    </div>
  )
}
