import { Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import BottomNav from './components/BottomNav'
import Home from './pages/Home'
import Report from './pages/Report'
import Volunteers from './pages/Volunteers'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import { useAuth } from './hooks/useAuth'

export default function App() {
  const { user } = useAuth()

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      <Navbar />

      {/* Contenido: pb-16 para dejar espacio al bottom nav */}
      <main className="flex-1 overflow-auto pb-16">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/reportar" element={<Report />} />
          <Route path="/voluntarios" element={<Volunteers />} />
          <Route path="/login" element={<Login />} />
          <Route path="/panel" element={<Dashboard />} />
        </Routes>
      </main>

      <BottomNav user={user} />
    </div>
  )
}
