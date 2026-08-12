import { useEffect, useState } from 'react'
import { listReports, listAidPoints, listDangerZones, updateReport, createAidPoint, createDangerZone } from '../services/api'
import { useAuth } from '../hooks/useAuth'
import { useNavigate } from 'react-router-dom'
import MapView from '../components/MapView'
import toast from 'react-hot-toast'

const STATUS_LABELS = { pending: 'Sin atender', in_progress: 'En proceso', resolved: 'Resuelto' }
const STATUS_COLORS = {
  pending: 'bg-red-100 text-red-700',
  in_progress: 'bg-yellow-100 text-yellow-700',
  resolved: 'bg-green-100 text-green-700',
}
const NEED_LABELS = {
  rescue: 'Rescate', medical: 'Médico', food: 'Alimentos', shelter: 'Albergue',
  family: 'Familiar', psychological: 'Psicológico', other: 'Otro',
}

export default function Dashboard() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [tab, setTab] = useState('reports')
  const [reports, setReports] = useState([])
  const [aidPoints, setAidPoints] = useState([])
  const [dangerZones, setDangerZones] = useState([])
  const [showAddAid, setShowAddAid] = useState(false)
  const [showAddDanger, setShowAddDanger] = useState(false)
  const [clickedLatLng, setClickedLatLng] = useState(null)
  const [addForm, setAddForm] = useState({})

  useEffect(() => {
    if (!user || user.role === 'victim') { navigate('/'); return }
    refresh()
  }, [user])

  const refresh = async () => {
    const [r, a, d] = await Promise.all([listReports(), listAidPoints({ active_only: false }), listDangerZones()])
    setReports(r.data)
    setAidPoints(a.data)
    setDangerZones(d.data)
  }

  const changeStatus = async (id, status) => {
    await updateReport(id, { status })
    toast.success('Estado actualizado')
    refresh()
  }

  const handleMapClick = (latlng) => {
    setClickedLatLng(latlng)
    setAddForm((f) => ({ ...f, lat: latlng.lat, lng: latlng.lng }))
  }

  const submitAidPoint = async (e) => {
    e.preventDefault()
    try {
      await createAidPoint(addForm)
      toast.success('Punto de ayuda registrado')
      setShowAddAid(false); setAddForm({}); setClickedLatLng(null)
      refresh()
    } catch { toast.error('Error al crear punto de ayuda') }
  }

  const submitDangerZone = async (e) => {
    e.preventDefault()
    try {
      await createDangerZone({ ...addForm, radius_meters: Number(addForm.radius_meters || 200) })
      toast.success('Zona de peligro registrada')
      setShowAddDanger(false); setAddForm({}); setClickedLatLng(null)
      refresh()
    } catch { toast.error('Error al crear zona de peligro') }
  }

  const inputCls = 'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-400'
  const fc = (e) => setAddForm((f) => ({ ...f, [e.target.name]: e.target.value }))

  return (
    <div className="max-w-4xl mx-auto px-4 py-6">
      <h1 className="text-2xl font-bold text-gray-800 mb-1">Panel de coordinación</h1>
      <p className="text-sm text-gray-500 mb-5">Hola, {user?.full_name} · {user?.role}</p>

      {/* Tabs */}
      <div className="flex gap-3 mb-6 border-b">
        {[
          { key: 'reports', label: `🆘 Reportes (${reports.length})` },
          { key: 'aid', label: `🤝 Puntos de ayuda (${aidPoints.length})` },
          { key: 'danger', label: `⚠️ Zonas peligro (${dangerZones.length})` },
          { key: 'map', label: '🗺️ Mapa' },
        ].map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`pb-2 text-sm font-medium border-b-2 transition-colors ${
              tab === key ? 'border-red-500 text-red-600' : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Reportes */}
      {tab === 'reports' && (
        <div className="space-y-3">
          {reports.map((r) => (
            <div key={r.id} className="bg-white border border-gray-200 rounded-xl p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-semibold text-sm">{NEED_LABELS[r.need_type]}</span>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[r.status]}`}>
                      {STATUS_LABELS[r.status]}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500">{r.address}</p>
                  <p className="text-xs mt-1 text-gray-700">{r.description}</p>
                  <p className="text-xs text-gray-400 mt-1">
                    {r.reporter_name} · {r.people_count} persona(s)
                    {r.reporter_phone && ` · ${r.reporter_phone}`}
                  </p>
                </div>
                <div className="flex flex-col gap-1.5 flex-shrink-0">
                  {r.status === 'pending' && (
                    <button
                      onClick={() => changeStatus(r.id, 'in_progress')}
                      className="text-xs bg-yellow-500 text-white px-3 py-1 rounded-lg hover:bg-yellow-600"
                    >
                      Tomar caso
                    </button>
                  )}
                  {r.status === 'in_progress' && (
                    <button
                      onClick={() => changeStatus(r.id, 'resolved')}
                      className="text-xs bg-green-600 text-white px-3 py-1 rounded-lg hover:bg-green-700"
                    >
                      Marcar resuelto
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Puntos de ayuda */}
      {tab === 'aid' && (
        <div>
          <button
            onClick={() => { setShowAddAid(true); setShowAddDanger(false) }}
            className="mb-4 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700"
          >
            + Agregar punto de ayuda
          </button>

          {showAddAid && (
            <form onSubmit={submitAidPoint} className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-4 space-y-3">
              <p className="text-sm font-semibold text-blue-800">Nuevo punto de ayuda — haz clic en el mapa para ubicarlo</p>
              <div className="h-48 rounded-lg overflow-hidden border border-blue-200">
                <MapView reports={[]} aidPoints={[]} dangerZones={[]} onMapClick={handleMapClick} clickedLatLng={clickedLatLng} />
              </div>
              {addForm.lat && <p className="text-xs text-green-600">✓ Ubicación: {addForm.lat.toFixed(5)}, {addForm.lng.toFixed(5)}</p>}
              <input name="name" placeholder="Nombre del punto" required onChange={fc} className={inputCls} />
              <select name="aid_type" required onChange={fc} className={inputCls}>
                <option value="">Tipo de ayuda</option>
                {['shelter','food','medical','water','supplies','information'].map(t => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
              <input name="address" placeholder="Dirección" required onChange={fc} className={inputCls} />
              <input name="contact_phone" placeholder="Teléfono de contacto" onChange={fc} className={inputCls} />
              <input type="number" name="capacity" placeholder="Cupos disponibles" onChange={fc} className={inputCls} />
              <textarea name="description" placeholder="Descripción adicional" rows={2} onChange={fc} className={inputCls} />
              <div className="flex gap-2">
                <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium">Guardar</button>
                <button type="button" onClick={() => setShowAddAid(false)} className="text-gray-500 text-sm px-4 py-2">Cancelar</button>
              </div>
            </form>
          )}

          <div className="space-y-2">
            {aidPoints.map((a) => (
              <div key={a.id} className={`border rounded-xl p-3 text-sm flex justify-between items-center ${a.is_active ? 'bg-white border-gray-200' : 'bg-gray-50 border-gray-100 opacity-60'}`}>
                <div>
                  <span className="font-medium">{a.name}</span>
                  <span className="text-xs text-gray-500 ml-2">{a.aid_type}</span>
                  <p className="text-xs text-gray-400">{a.address}</p>
                </div>
                {a.capacity && <span className="text-xs text-gray-500">{a.capacity} cupos</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Zonas de peligro */}
      {tab === 'danger' && (
        <div>
          <button
            onClick={() => { setShowAddDanger(true); setShowAddAid(false) }}
            className="mb-4 bg-red-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-red-700"
          >
            + Definir zona de peligro
          </button>

          {showAddDanger && (
            <form onSubmit={submitDangerZone} className="bg-red-50 border border-red-200 rounded-xl p-4 mb-4 space-y-3">
              <p className="text-sm font-semibold text-red-800">Nueva zona de peligro — haz clic en el mapa para ubicarla</p>
              <div className="h-48 rounded-lg overflow-hidden border border-red-200">
                <MapView reports={[]} aidPoints={[]} dangerZones={[]} onMapClick={handleMapClick} clickedLatLng={clickedLatLng} />
              </div>
              {addForm.lat && <p className="text-xs text-green-600">✓ Centro: {addForm.lat.toFixed(5)}, {addForm.lng.toFixed(5)}</p>}
              <input name="name" placeholder="Nombre de la zona" required onChange={fc} className={inputCls} />
              <select name="danger_level" required onChange={fc} className={inputCls}>
                <option value="">Nivel de peligro</option>
                <option value="low">Precaución (bajo)</option>
                <option value="medium">Peligro moderado</option>
                <option value="high">Peligro alto</option>
                <option value="critical">Zona roja — evacuar</option>
              </select>
              <input type="number" name="radius_meters" placeholder="Radio en metros (ej: 300)" defaultValue={200} onChange={fc} className={inputCls} />
              <textarea name="description" placeholder="Descripción del peligro" required rows={2} onChange={fc} className={inputCls} />
              <div className="flex gap-2">
                <button type="submit" className="bg-red-600 text-white px-4 py-2 rounded-lg text-sm font-medium">Guardar</button>
                <button type="button" onClick={() => setShowAddDanger(false)} className="text-gray-500 text-sm px-4 py-2">Cancelar</button>
              </div>
            </form>
          )}

          <div className="space-y-2">
            {dangerZones.map((z) => (
              <div key={z.id} className="bg-white border border-gray-200 rounded-xl p-3 text-sm flex justify-between items-center">
                <div>
                  <span className="font-medium">{z.name}</span>
                  <span className={`text-xs ml-2 px-2 py-0.5 rounded-full ${
                    z.danger_level === 'critical' ? 'bg-red-900 text-white' :
                    z.danger_level === 'high' ? 'bg-red-100 text-red-700' :
                    z.danger_level === 'medium' ? 'bg-orange-100 text-orange-700' :
                    'bg-yellow-100 text-yellow-700'
                  }`}>{z.danger_level}</span>
                  <p className="text-xs text-gray-400">{z.description}</p>
                </div>
                <span className="text-xs text-gray-400">{z.radius_meters}m</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Mapa general */}
      {tab === 'map' && (
        <div className="h-[60vh] rounded-xl overflow-hidden border border-gray-200">
          <MapView reports={reports} aidPoints={aidPoints} dangerZones={dangerZones} />
        </div>
      )}
    </div>
  )
}
