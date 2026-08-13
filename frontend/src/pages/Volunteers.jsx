import { useEffect, useState } from 'react'
import { listVolunteers } from '../services/api'
import toast from 'react-hot-toast'

const SKILL_TAGS = ['médico', 'logística', 'psicología', 'rescate', 'comunicaciones', 'cocina']

export default function Volunteers() {
  const [volunteers, setVolunteers] = useState([])
  const [loading, setLoading] = useState(true)
  const [skillFilter, setSkillFilter] = useState('')

  useEffect(() => {
    listVolunteers(skillFilter || undefined)
      .then((r) => setVolunteers(r.data))
      .catch(() => toast.error('Error cargando voluntarios'))
      .finally(() => setLoading(false))
  }, [skillFilter])

  return (
    <div className="max-w-lg mx-auto px-4 py-5">
      <h1 className="text-xl font-bold text-gray-900 mb-1">Voluntarios</h1>
      <p className="text-sm text-gray-500 mb-4">Personas disponibles en Pereira y sus barrios.</p>

      {/* Filtros — scroll horizontal sin barra */}
      <div className="flex gap-2 overflow-x-auto hide-scrollbar pb-2 mb-4">
        {['', ...SKILL_TAGS].map((s) => (
          <button
            key={s || 'todos'}
            onClick={() => setSkillFilter(s)}
            className="flex-shrink-0 rounded-full border px-4 text-sm font-medium transition-colors"
            style={{
              minHeight: 40,
              background: skillFilter === s ? '#1f2937' : 'white',
              color: skillFilter === s ? 'white' : '#6b7280',
              borderColor: skillFilter === s ? '#1f2937' : '#e5e7eb',
            }}
          >
            {s || 'Todos'}
          </button>
        ))}
      </div>

      {loading ? (
        <p className="text-gray-400 text-sm text-center py-8">Cargando...</p>
      ) : volunteers.length === 0 ? (
        <p className="text-gray-400 text-sm text-center py-8">No hay voluntarios con ese perfil.</p>
      ) : (
        <div className="flex flex-col gap-3">
          {volunteers.map((v) => (
            <div
              key={v.id}
              className="bg-white border border-gray-200 rounded-2xl p-4 flex items-start gap-3"
            >
              {/* Avatar */}
              <div
                className="w-11 h-11 rounded-full bg-red-100 text-red-600 font-bold text-base flex items-center justify-center flex-shrink-0"
                style={{ minWidth: 44 }}
              >
                {v.full_name.charAt(0).toUpperCase()}
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-gray-900 text-base leading-tight truncate">{v.full_name}</p>
                {v.neighborhood && (
                  <p className="text-xs text-gray-500 mt-0.5">📍 {v.neighborhood}</p>
                )}
                {v.skills && (
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {v.skills.split(',').map((s) => (
                      <span
                        key={s}
                        className="text-xs px-2 py-0.5 rounded-full border"
                        style={{ background: '#eff6ff', color: '#1d4ed8', borderColor: '#bfdbfe' }}
                      >
                        {s.trim()}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Llamar */}
              {v.phone && (
                <a
                  href={`tel:${v.phone}`}
                  className="flex-shrink-0 bg-green-600 text-white rounded-xl px-3 font-semibold text-sm no-underline flex items-center"
                  style={{ minHeight: 44 }}
                >
                  📞 Llamar
                </a>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
