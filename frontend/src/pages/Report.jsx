import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import MapView from '../components/MapView'
import { createReport } from '../services/api'
import toast from 'react-hot-toast'

const NEED_OPTIONS = [
  { value: 'rescue', label: '🆘 Rescate — estoy atrapado/a' },
  { value: 'medical', label: '⚕️ Atención médica urgente' },
  { value: 'food', label: '🍲 Necesito alimentos / agua' },
  { value: 'shelter', label: '🏠 Necesito albergue' },
  { value: 'family', label: '👨‍👩‍👧 Busco un familiar' },
  { value: 'psychological', label: '🧠 Apoyo psicológico' },
  { value: 'other', label: '📌 Otro' },
]

const INITIAL = {
  reporter_name: '',
  reporter_phone: '',
  need_type: '',
  description: '',
  address: '',
  lat: null,
  lng: null,
  people_count: 1,
}

export default function Report() {
  const [form, setForm] = useState(INITIAL)
  const [clickedLatLng, setClickedLatLng] = useState(null)
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleMapClick = (latlng) => {
    setClickedLatLng(latlng)
    setForm((f) => ({ ...f, lat: latlng.lat, lng: latlng.lng }))
  }

  const handleChange = (e) => setForm((f) => ({ ...f, [e.target.name]: e.target.value }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.lat || !form.lng) {
      toast.error('Selecciona tu ubicación en el mapa')
      return
    }
    if (!form.need_type) {
      toast.error('Selecciona el tipo de ayuda')
      return
    }
    setLoading(true)
    try {
      await createReport({ ...form, people_count: Number(form.people_count) })
      toast.success('Solicitud enviada. Los voluntarios serán notificados.')
      navigate('/')
    } catch {
      toast.error('Error al enviar. Intenta de nuevo.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-lg mx-auto px-4 py-5">
      <h1 className="text-xl font-bold text-gray-900 mb-1">Pedir ayuda</h1>
      <p className="text-sm text-gray-500 mb-5 leading-relaxed">
        Sin necesidad de cuenta. Tu reporte aparece en el mapa de inmediato.
      </p>

      <form onSubmit={handleSubmit} className="flex flex-col gap-5">

        {/* Tipo de necesidad — columna única en mobile */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">¿Qué necesitas?</label>
          <div className="flex flex-col gap-2">
            {NEED_OPTIONS.map((o) => (
              <label
                key={o.value}
                className="flex items-center gap-3 border rounded-xl px-4 cursor-pointer transition-all"
                style={{
                  minHeight: 52,
                  borderColor: form.need_type === o.value ? '#dc2626' : '#e5e7eb',
                  background: form.need_type === o.value ? '#fff1f2' : 'white',
                  color: form.need_type === o.value ? '#991b1b' : '#374151',
                }}
              >
                <input
                  type="radio"
                  name="need_type"
                  value={o.value}
                  checked={form.need_type === o.value}
                  onChange={handleChange}
                  className="sr-only"
                />
                <span className="text-base">{o.label}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Descripción */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Describe la situación</label>
          <textarea
            name="description"
            value={form.description}
            onChange={handleChange}
            required
            rows={3}
            placeholder="Cuántas personas, condición de salud, acceso al lugar..."
            className="w-full border border-gray-300 rounded-xl px-4 py-3 focus:outline-none focus:border-red-400"
            style={{ resize: 'vertical', fontFamily: 'inherit' }}
          />
        </div>

        {/* Dirección */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Dirección o referencia</label>
          <input
            name="address"
            value={form.address}
            onChange={handleChange}
            required
            placeholder="Cra 7 #19-25, barrio Cuba, cerca de la iglesia..."
            className="w-full border border-gray-300 rounded-xl px-4 py-3 focus:outline-none focus:border-red-400"
          />
        </div>

        {/* Personas */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Número de personas afectadas</label>
          <input
            type="number"
            name="people_count"
            value={form.people_count}
            onChange={handleChange}
            min={1}
            max={500}
            className="border border-gray-300 rounded-xl px-4 py-3 focus:outline-none focus:border-red-400"
            style={{ width: 90 }}
          />
        </div>

        {/* Mapa */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Marca tu ubicación en el mapa{' '}
            {form.lat && <span className="text-green-600 text-xs font-normal">✓ seleccionada</span>}
          </label>
          <div
            className="rounded-xl overflow-hidden border"
            style={{
              height: 220,
              borderColor: form.lat ? '#16a34a' : '#d1d5db',
              borderWidth: form.lat ? 2 : 1,
            }}
          >
            <MapView
              reports={[]}
              aidPoints={[]}
              dangerZones={[]}
              onMapClick={handleMapClick}
              clickedLatLng={clickedLatLng}
            />
          </div>
          <p className="text-xs text-gray-400 mt-1.5">Toca el mapa para marcar el punto exacto</p>
        </div>

        {/* Contacto */}
        <div className="flex flex-col gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Tu nombre</label>
            <input
              name="reporter_name"
              value={form.reporter_name}
              onChange={handleChange}
              required
              placeholder="Juan Pérez"
              className="w-full border border-gray-300 rounded-xl px-4 py-3 focus:outline-none focus:border-red-400"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Teléfono (opcional)</label>
            <input
              name="reporter_phone"
              value={form.reporter_phone}
              onChange={handleChange}
              type="tel"
              placeholder="300 123 4567"
              className="w-full border border-gray-300 rounded-xl px-4 py-3 focus:outline-none focus:border-red-400"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-red-600 text-white rounded-xl font-bold text-base disabled:opacity-50 transition-opacity"
          style={{ minHeight: 56, fontSize: 16 }}
        >
          {loading ? 'Enviando...' : '🆘 Enviar solicitud de ayuda'}
        </button>
      </form>
    </div>
  )
}
