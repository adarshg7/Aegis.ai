/**
 * Zustand global store — shared state for auth, accidents, WebSocket status.
 */
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useAuthStore = create(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      setTokens: (access, refresh) => set({ accessToken: access, refreshToken: refresh }),
      setUser: (user) => set({ user }),
      logout: () => set({ user: null, accessToken: null, refreshToken: null }),
    }),
    { name: 'auth-gov' }
  )
)

export const useAccidentStore = create((set, get) => ({
  accidents: [],
  selectedId: null,
  totalCount: 0,
  wsConnected: false,

  setAccidents: (accidents) => set({ accidents }),
  prependAccident: (accident) =>
    set((s) => ({
      accidents: [{ ...accident, _isNew: true }, ...s.accidents].slice(0, 200),
      totalCount: s.totalCount + 1,
    })),
  updateAccident: (id, patch) =>
    set((s) => ({
      accidents: s.accidents.map((a) => (a.id === id ? { ...a, ...patch } : a)),
    })),
  selectAccident: (id) => set({ selectedId: id }),
  setWsConnected: (v) => set({ wsConnected: v }),
}))
