import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  return (
    <header className="bg-red-600 text-white px-4 flex items-center justify-between h-14 shadow-md flex-shrink-0 sticky top-0 z-40">
      <button
        onClick={() => navigate('/')}
        className="font-bold text-lg flex items-center gap-2 bg-transparent border-none text-white min-h-0"
        style={{ minHeight: 'unset' }}
      >
        🚨 Pereira Alerta
      </button>

      <div className="flex items-center gap-2">
        {/* Notificación */}
        <button className="w-10 h-10 rounded-full bg-white/20 text-white border-none text-lg">
          🔔
        </button>

        {user ? (
          <button
            onClick={() => { logout(); navigate('/') }}
            className="text-xs text-red-100 bg-white/20 rounded-full px-3 h-9 border-none"
          >
            {user.full_name.split(' ')[0]} · Salir
          </button>
        ) : (
          <button
            onClick={() => navigate('/login')}
            className="bg-white text-red-600 text-xs font-semibold rounded-full px-4 h-9 border-none"
          >
            Ingresar
          </button>
        )}
      </div>
    </header>
  )
}
