import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { login, register } from '../services/api'
import { useAuth } from '../hooks/useAuth'
import toast from 'react-hot-toast'

const ROLE_OPTIONS = [
  { value: 'victim', label: '🆘 Soy afectado/a' },
  { value: 'volunteer', label: '🤝 Soy voluntario/a' },
  { value: 'coordinator', label: '📋 Soy coordinador/a' },
]

export default function Login() {
  const [mode, setMode] = useState('login') // 'login' | 'register'
  const [form, setForm] = useState({ phone: '', password: '', full_name: '', role: 'volunteer', skills: '', neighborhood: '' })
  const [loading, setLoading] = useState(false)
  const { setAuth } = useAuth()
  const navigate = useNavigate()

  const handleChange = (e) => setForm((f) => ({ ...f, [e.target.name]: e.target.value }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      const fn = mode === 'login' ? login : register
      const { data } = await fn(form)
      setAuth(data.access_token, data.user)
      toast.success(`Bienvenido/a, ${data.user.full_name}`)
      navigate('/')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al ingresar')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-[calc(100vh-56px)] flex items-center justify-center bg-gray-50 px-4">
      <div className="bg-white border border-gray-200 rounded-2xl p-8 w-full max-w-md shadow-sm">
        <h1 className="text-2xl font-bold text-gray-800 mb-1">
          {mode === 'login' ? 'Ingresar' : 'Registrarse como voluntario/coordinador'}
        </h1>
        <p className="text-sm text-gray-500 mb-6">
          {mode === 'login'
            ? 'Para gestionar reportes y puntos de ayuda'
            : 'Las víctimas pueden reportar sin cuenta desde el mapa'}
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          {mode === 'register' && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nombre completo</label>
                <input
                  name="full_name"
                  value={form.full_name}
                  onChange={handleChange}
                  required
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-400"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Rol</label>
                <div className="grid grid-cols-3 gap-2">
                  {ROLE_OPTIONS.filter((r) => r.value !== 'victim').map((o) => (
                    <label
                      key={o.value}
                      className={`flex flex-col items-center border rounded-lg px-2 py-2 cursor-pointer text-xs text-center transition-colors ${
                        form.role === o.value
                          ? 'border-red-500 bg-red-50 text-red-700 font-medium'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <input
                        type="radio"
                        name="role"
                        value={o.value}
                        checked={form.role === o.value}
                        onChange={handleChange}
                        className="sr-only"
                      />
                      {o.label}
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Habilidades (separadas por coma)
                </label>
                <input
                  name="skills"
                  value={form.skills}
                  onChange={handleChange}
                  placeholder="médico, logística, psicología"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-400"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Barrio en Pereira</label>
                <input
                  name="neighborhood"
                  value={form.neighborhood}
                  onChange={handleChange}
                  placeholder="Cuba, Álamos, Centro..."
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-400"
                />
              </div>
            </>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Teléfono (sirve como usuario)</label>
            <input
              name="phone"
              value={form.phone}
              onChange={handleChange}
              required
              placeholder="3001234567"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-400"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Contraseña</label>
            <input
              type="password"
              name="password"
              value={form.password}
              onChange={handleChange}
              required
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-400"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-red-600 text-white py-2.5 rounded-xl font-semibold hover:bg-red-700 disabled:opacity-50 transition-colors"
          >
            {loading ? 'Cargando...' : mode === 'login' ? 'Ingresar' : 'Registrarse'}
          </button>
        </form>

        <p className="text-sm text-center text-gray-500 mt-4">
          {mode === 'login' ? (
            <>
              ¿Sin cuenta?{' '}
              <button onClick={() => setMode('register')} className="text-red-600 font-medium hover:underline">
                Regístrate
              </button>
            </>
          ) : (
            <>
              ¿Ya tienes cuenta?{' '}
              <button onClick={() => setMode('login')} className="text-red-600 font-medium hover:underline">
                Ingresar
              </button>
            </>
          )}
        </p>
      </div>
    </div>
  )
}
