/**
 * Axios API client — auto-attaches JWT, handles 401 token refresh.
 */
import axios from 'axios'
import { useAuthStore } from '../store'

const API = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1',
  timeout: 15_000,
})

// Attach access token
API.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Auto-refresh on 401
API.interceptors.response.use(
  (r) => r,
  async (error) => {
    const orig = error.config
    if (error.response?.status === 401 && !orig._retry) {
      orig._retry = true
      try {
        const { refreshToken, setTokens } = useAuthStore.getState()
        const { data } = await axios.post(
          `${orig.baseURL || 'http://localhost:8000/api/v1'}/auth/refresh`,
          { refresh_token: refreshToken }
        )
        setTokens(data.access_token, data.refresh_token)
        orig.headers.Authorization = `Bearer ${data.access_token}`
        return API(orig)
      } catch {
        useAuthStore.getState().logout()
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default API

// ── Endpoint helpers ──────────────────────────────────────────────
export const authApi = {
  login: (email, password) => API.post('/auth/login', { email, password }),
  me: () => API.get('/auth/me'),
}

export const accidentApi = {
  list: (params) => API.get('/accidents', { params }),
  get: (id) => API.get(`/accidents/${id}`),
  simulate: (body) => API.post('/accidents/simulate', body),
  resolve: (id) => API.patch(`/accidents/${id}/resolve`),
  analytics: () => API.get('/accidents/analytics/summary'),
}
