import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

// Adjuntar token JWT automáticamente
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// ── Auth ──────────────────────────────────────────────────────────────
export const register = (data) => api.post('/auth/register', data)
export const login = (data) => api.post('/auth/login', data)
export const getMe = () => api.get('/users/me')

// ── Reportes ──────────────────────────────────────────────────────────
export const createReport = (data) => api.post('/reports/', data)
export const listReports = (params) => api.get('/reports/', { params })
export const updateReport = (id, data) => api.patch(`/reports/${id}`, data)

// ── Puntos de ayuda ───────────────────────────────────────────────────
export const listAidPoints = (params) => api.get('/aid-points/', { params })
export const createAidPoint = (data) => api.post('/aid-points/', data)
export const updateAidPoint = (id, data) => api.patch(`/aid-points/${id}`, data)

// ── Zonas de peligro ──────────────────────────────────────────────────
export const listDangerZones = () => api.get('/danger-zones/')
export const createDangerZone = (data) => api.post('/danger-zones/', data)
export const updateDangerZone = (id, data) => api.patch(`/danger-zones/${id}`, data)

// ── Voluntarios ───────────────────────────────────────────────────────
export const listVolunteers = (skill) => api.get('/users/volunteers', { params: { skill } })
