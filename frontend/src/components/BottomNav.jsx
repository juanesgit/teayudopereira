import { Link, useLocation } from 'react-router-dom'

const ITEMS = [
  { to: '/', icon: '🗺️', label: 'Mapa' },
  { to: '/reportar', icon: '🆘', label: 'Pedir ayuda' },
  { to: '/voluntarios', icon: '🤝', label: 'Voluntarios' },
  { to: '/panel', icon: '📋', label: 'Panel' },
]

export default function BottomNav({ user }) {
  const { pathname } = useLocation()

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 z-50"
      style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
    >
      <div className="flex">
        {ITEMS.filter(item => item.to !== '/panel' || (user && user.role !== 'victim')).map(({ to, icon, label }) => {
          const active = pathname === to
          return (
            <Link
              key={to}
              to={to}
              className="flex-1 flex flex-col items-center justify-center py-2 gap-0.5 min-h-[60px]"
              style={{ textDecoration: 'none' }}
            >
              <span className="text-xl leading-none">{icon}</span>
              <span
                className="text-[10px] font-medium"
                style={{ color: active ? '#dc2626' : '#9ca3af' }}
              >
                {label}
              </span>
              {active && (
                <span className="w-1 h-1 rounded-full bg-red-600 mt-0.5" />
              )}
            </Link>
          )
        })}
      </div>
    </nav>
  )
}
