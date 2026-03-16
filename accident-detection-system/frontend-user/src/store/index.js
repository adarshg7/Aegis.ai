import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useAuthStore = create(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      setTokens: (a, r) => set({ accessToken: a, refreshToken: r }),
      setUser: (u) => set({ user: u }),
      logout: () => set({ user: null, accessToken: null, refreshToken: null }),
    }),
    { name: 'auth-driver' }
  )
)

export const useAlertStore = create((set) => ({
  alerts: [],
  nearbyCount: 0,
  wsConnected: false,
  addAlert: (alert) => set((s) => ({
    alerts: [{ ...alert, _new: true }, ...s.alerts].slice(0, 100),
    nearbyCount: s.nearbyCount + 1,
  })),
  setAlerts: (alerts) => set({ alerts }),
  setWsConnected: (v) => set({ wsConnected: v }),
  clearNew: () => set((s) => ({ alerts: s.alerts.map(a => ({ ...a, _new: false })), nearbyCount: 0 })),
}))
