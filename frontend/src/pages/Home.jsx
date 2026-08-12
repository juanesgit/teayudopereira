import { useEffect, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { listReports, listAidPoints, listDangerZones } from '../services/api'
import MapView from '../components/MapView'
import toast from 'react-hot-toast'

const LEGEND = [
  { color: '#ef4444', emoji: '🆘', label: 'Emergencia' },
  { color: '#3b82f6', emoji: '🏠', label: 'Albergue' },
  { color: '#10b981', emoji: '⚕️', label: 'Médico' },
  { color: '#f59e0b', emoji: '🍲', label: 'Alimentos' },
  { color: '#06b6d4', emoji: '💧', label: 'Agua' },
]

export default function Home() {
  const [reports, setReports] = useState([])
  const [aidPoints, setAidPoints] = useState([])
  const [dangerZones, setDangerZones] = useState([])
  const [filters, setFilters] = useState({ reports: true, aidPoints: true, dangerZones: true })
  const [loading, setLoading] = useState(true)

  const fetchData = useCallback(async () => {
    try {
      const [r, a, d] = await Promise.all([
        listReports({ status: 'pending' }),
        listAidPoints({ active_only: true }),
        listDangerZones(),
      ])
      setReports(r.data)
      setAidPoints(a.data)
      setDangerZones(d.data)
    } catch {
      toast.error('Error cargando datos del mapa')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 30_000)
    return () => clearInterval(interval)
  }, [fetchData])

  return (
    /* Ocupa toda la altura disponible menos header y bottom nav */
    <div className="flex flex-col" style={{ height: 'calc(100vh - 56px - 60px)' }}>

      {/* Chips de filtro — scroll horizontal en mobile */}
      <div className="bg-white border-b border-gray-100 px-3 py-2 flex gap-2 overflow-x-auto hide-scrollbar flex-shrink-0">
        {[
          { key: 'reports', label: `🆘 ${reports.length}` },
          { key: 'aidPoints', label: `🤝 ${aidPoints.length}` },
          { key: 'dangerZones', label: `⚠️ ${dangerZones.length}` },
        ].map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setFilters((f) => ({ ...f, [key]: !f[key] }))}
            className="flex-shrink-0 px-4 rounded-full border text-sm font-medium transition-colors"
            style={{
              minHeight: 36,
              background: filters[key] ? '#1f2937' : 'white',
              color: filters[key] ? 'white' : '#6b7280',
              borderColor: filters[key] ? '#1f2937' : '#e5e7eb',
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Mapa — ocupa todo el espacio restante */}
      <div className="flex-1 relative">
        {loading && (
          <div className="absolute inset-0 z-10 bg-white/70 flex items-center justify-center">
            <p className="text-gray-400 text-sm">Cargando mapa...</p>
          </div>
        )}
        <MapView
          reports={filters.reports ? reports : []}
          aidPoints={filters.aidPoints ? aidPoints : []}
          dangerZones={filters.dangerZones ? dangerZones : []}
        />
      </div>

      {/* Leyenda — scroll horizontal */}
      <div className="bg-white border-t border-gray-100 px-3 py-2 flex gap-3 overflow-x-auto hide-scrollbar flex-shrink-0">
        {LEGEND.map(({ color, emoji, label }) => (
          <div key={label} className="flex items-center gap-1.5 text-xs text-gray-500 whitespace-nowrap">
            <span
              className="w-5 h-5 rounded-full flex items-center justify-center text-[10px] flex-shrink-0"
              style={{ background: color }}
            >
              {emoji}
            </span>
            {label}
          </div>
        ))}
      </div>

      {/* FAB — botón flotante de acción principal */}
      <Link
        to="/reportar"
        className="fixed right-4 text-white font-bold text-2xl rounded-full shadow-lg z-30 no-underline"
        style={{
          bottom: 76,
          width: 56,
          height: 56,
          background: '#dc2626',
          boxShadow: '0 4px 16px rgba(220,38,38,.5)',
          minHeight: 'unset',
        }}
        aria-label="Pedir ayuda"
      >
        🆘
      </Link>
    </div>
  )
}
