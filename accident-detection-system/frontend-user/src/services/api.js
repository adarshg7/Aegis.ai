import axios from 'axios'
import { useAuthStore } from '../store'

const API = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1',
  timeout: 15_000,
})

API.interceptors.request.use((cfg) => {
  const tok = useAuthStore.getState().accessToken
  if (tok) cfg.headers.Authorization = `Bearer ${tok}`
  return cfg
})

API.interceptors.response.use(r => r, async (err) => {
  const orig = err.config
  if (err.response?.status === 401 && !orig._retry) {
    orig._retry = true
    try {
      const { refreshToken, setTokens } = useAuthStore.getState()
      const { data } = await axios.post(`http://localhost:8000/api/v1/auth/refresh`, { refresh_token: refreshToken })
      setTokens(data.access_token, data.refresh_token)
      orig.headers.Authorization = `Bearer ${data.access_token}`
      return API(orig)
    } catch { useAuthStore.getState().logout() }
  }
  return Promise.reject(err)
})

export default API

export const authApi = {
  login: (email, pw) => API.post('/auth/login', { email, password: pw }),
  register: (b) => API.post('/auth/register', b),
  me: () => API.get('/auth/me'),
}

export const accidentApi = {
  list: (p) => API.get('/accidents', { params: p }),
  report: (b) => API.post('/accidents', b),
}

export const locationApi = {
  update: (lat, lon) => API.post('/users/location', { latitude: lat, longitude: lon }),
}
