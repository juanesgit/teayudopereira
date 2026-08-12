import { create } from 'zustand'

export const useAuth = create((set) => ({
  user: null,
  token: localStorage.getItem('token'),

  setAuth: (token, user) => {
    localStorage.setItem('token', token)
    set({ token, user })
  },

  logout: () => {
    localStorage.removeItem('token')
    set({ token: null, user: null })
  },
}))
