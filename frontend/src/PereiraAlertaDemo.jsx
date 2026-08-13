/**
 * Pereira Alerta — Demo self-contained (un solo archivo)
 * Funciona como artifact de Claude o como componente standalone.
 * Para conectar con el backend real cambia DEMO_MODE = false y
 * asegúrate de que FastAPI corre en http://localhost:8000
 */

import { useState, useEffect, useRef, useCallback } from "react"

const DEMO_MODE = true
const API = "http://localhost:8000"
const PEREIRA = [4.8133, -75.6961]

// ── Datos de demostración ────────────────────────────────────────────────────
const DEMO = {
  reports: [
    { id: 1, reporter_name: "María López", need_type: "rescue", description: "Edificio colapsado, 3 personas atrapadas en el 2do piso.", address: "Cra 7 # 19-25, Cuba", lat: 4.8050, lng: -75.7100, people_count: 3, status: "pending", reporter_phone: "3001234567" },
    { id: 2, reporter_name: "Carlos Ruiz", need_type: "medical", description: "Persona mayor con herida en la cabeza, necesita atención urgente.", address: "Av. 30 de Agosto, Álamos", lat: 4.8200, lng: -75.6900, people_count: 1, status: "in_progress", reporter_phone: "3109876543" },
    { id: 3, reporter_name: "Ana Gómez", need_type: "food", description: "Familia de 5 sin agua ni alimentos desde ayer.", address: "Barrio Boston", lat: 4.8100, lng: -75.7000, people_count: 5, status: "pending", reporter_phone: null },
  ],
  aidPoints: [
    { id: 1, name: "Albergue Coliseo Mayor", aid_type: "shelter", address: "Cl. 19 # 6-52, Centro", lat: 4.8133, lng: -75.6961, capacity: 150, contact_phone: "3204567890", description: "Habilitado por la alcaldía. Cupos disponibles.", is_active: true },
    { id: 2, name: "Brigada Médica Cruz Roja", aid_type: "medical", address: "Parque Olaya, Centro", lat: 4.8180, lng: -75.6940, capacity: null, contact_phone: "3157891234", description: "Atención médica gratuita 24h.", is_active: true },
    { id: 3, name: "Punto de Agua Potable", aid_type: "water", address: "Cra 10 # 25-40, Pinares", lat: 4.8090, lng: -75.6800, capacity: null, contact_phone: null, description: "Agua disponible 24h.", is_active: true },
    { id: 4, name: "Comedor Comunitario San José", aid_type: "food", address: "Iglesia San José, Cuba", lat: 4.8040, lng: -75.7120, capacity: 80, contact_phone: "3003456789", description: "Desayuno, almuerzo y cena.", is_active: true },
  ],
  dangerZones: [
    { id: 1, name: "Deslizamiento Nororiental", danger_level: "critical", description: "Deslizamiento activo — evacuación inmediata, no acercarse.", lat: 4.8300, lng: -75.6950, radius_meters: 400, is_active: true },
    { id: 2, name: "Riesgo Eléctrico Cuba", danger_level: "high", description: "Cables caídos y postes inestables. Peligro de electrocución.", lat: 4.8060, lng: -75.7080, radius_meters: 250, is_active: true },
    { id: 3, name: "Edificios Dañados Centro", danger_level: "medium", description: "Varios edificios con daños estructurales — no ingresar.", lat: 4.8150, lng: -75.6970, radius_meters: 300, is_active: true },
  ],
  volunteers: [
    { id: 1, full_name: "Dr. Roberto Silva", skills: "médico,urgencias", neighborhood: "Centro", phone: "3001112233" },
    { id: 2, full_name: "Luisa Fernández", skills: "psicología,primeros auxilios", neighborhood: "Álamos", phone: "3109998877" },
    { id: 3, full_name: "Equipo Rescate Bomberos", skills: "rescate,logística", neighborhood: "Cuba", phone: "119" },
    { id: 4, full_name: "Sandra Ríos", skills: "logística,cocina,suministros", neighborhood: "Pinares", phone: "3204445566" },
  ],
}

// ── Constantes ───────────────────────────────────────────────────────────────
const NEED_LABELS = { rescue: "Rescate", medical: "Médico", food: "Alimentos", shelter: "Albergue", family: "Busca familiar", psychological: "Psicológico", other: "Otro" }
const NEED_OPTIONS = [
  { value: "rescue", label: "🆘 Rescate — estoy atrapado/a" },
  { value: "medical", label: "⚕️ Atención médica urgente" },
  { value: "food", label: "🍲 Necesito alimentos / agua" },
  { value: "shelter", label: "🏠 Necesito albergue" },
  { value: "family", label: "👨‍👩‍👧 Busco un familiar" },
  { value: "psychological", label: "🧠 Apoyo psicológico" },
  { value: "other", label: "📌 Otro" },
]
const STATUS_META = {
  pending: { label: "Sin atender", bg: "#fee2e2", color: "#b91c1c" },
  in_progress: { label: "En proceso", bg: "#fef9c3", color: "#854d0e" },
  resolved: { label: "Resuelto", bg: "#dcfce7", color: "#15803d" },
}
const DANGER_COLOR = { low: "#fbbf24", medium: "#f97316", high: "#ef4444", critical: "#7f1d1d" }
const DANGER_LABEL = { low: "Precaución", medium: "Peligro moderado", high: "Peligro alto", critical: "Zona roja — evacuar" }
const AID_EMOJI = { shelter: "🏠", food: "🍲", medical: "⚕️", water: "💧", supplies: "📦", information: "ℹ️" }
const AID_COLOR = { shelter: "#3b82f6", food: "#f59e0b", medical: "#10b981", water: "#06b6d4", supplies: "#8b5cf6", information: "#6b7280" }

// ── API helper ───────────────────────────────────────────────────────────────
async function api(method, path, body, token) {
  const res = await fetch(API + path, {
    method,
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  })
  const data = await res.json()
  if (!res.ok) throw data
  return data
}

// ── Leaflet map component ─────────────────────────────────────────────────────
function makeIcon(color, emoji) {
  return window.L?.divIcon({
    html: `<div style="background:${color};width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:15px;border:2px solid white;box-shadow:0 2px 6px rgba(0,0,0,.3)">${emoji}</div>`,
    className: "",
    iconSize: [32, 32],
    iconAnchor: [16, 16],
    popupAnchor: [0, -18],
  })
}

function MapView({ reports = [], aidPoints = [], dangerZones = [], onMapClick, clickedLatLng }) {
  const containerRef = useRef(null)
  const mapRef = useRef(null)
  const layersRef = useRef([])
  const [ready, setReady] = useState(!!window.L)

  // Load Leaflet from CDN
  useEffect(() => {
    if (window.L) { setReady(true); return }
    const link = document.createElement("link")
    link.rel = "stylesheet"
    link.href = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css"
    document.head.appendChild(link)
    const script = document.createElement("script")
    script.src = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"
    script.onload = () => setReady(true)
    document.body.appendChild(script)
  }, [])

  // Init map
  useEffect(() => {
    if (!ready || !containerRef.current || mapRef.current) return
    const L = window.L
    const map = L.map(containerRef.current).setView(PEREIRA, 13)
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "© OpenStreetMap",
    }).addTo(map)
    if (onMapClick) map.on("click", (e) => onMapClick(e.latlng))
    mapRef.current = map
  }, [ready])

  // Update layers
  useEffect(() => {
    const map = mapRef.current
    if (!map || !window.L) return
    const L = window.L

    layersRef.current.forEach((l) => map.removeLayer(l))
    layersRef.current = []

    const add = (layer) => { layer.addTo(map); layersRef.current.push(layer) }

    dangerZones.forEach((z) => {
      add(L.circle([z.lat, z.lng], {
        radius: z.radius_meters,
        color: DANGER_COLOR[z.danger_level],
        fillColor: DANGER_COLOR[z.danger_level],
        fillOpacity: 0.25,
        weight: 2,
      }).bindPopup(`<b>${z.name}</b><br><span style="color:${DANGER_COLOR[z.danger_level]}">${DANGER_LABEL[z.danger_level]}</span><br><small>${z.description}</small>`))
    })

    aidPoints.forEach((ap) => {
      add(L.marker([ap.lat, ap.lng], { icon: makeIcon(AID_COLOR[ap.aid_type] || "#6b7280", AID_EMOJI[ap.aid_type] || "ℹ️") })
        .bindPopup(`<b>${ap.name}</b><br><small>${ap.address}</small>${ap.capacity ? `<br>Cupos: ${ap.capacity}` : ""}${ap.contact_phone ? `<br>📞 ${ap.contact_phone}` : ""}`))
    })

    reports.forEach((r) => {
      add(L.marker([r.lat, r.lng], { icon: makeIcon("#ef4444", "🆘") })
        .bindPopup(`<b>${NEED_LABELS[r.need_type]}</b> · ${r.people_count} persona(s)<br><small>${r.address}</small><br>${r.description}${r.reporter_phone ? `<br>📞 ${r.reporter_phone}` : ""}`))
    })

    if (clickedLatLng) {
      add(L.marker([clickedLatLng.lat, clickedLatLng.lng], { icon: makeIcon("#6366f1", "📍") })
        .bindPopup("Ubicación seleccionada"))
    }
  }, [ready, reports, aidPoints, dangerZones, clickedLatLng])

  // Cleanup
  useEffect(() => () => { if (mapRef.current) { mapRef.current.remove(); mapRef.current = null } }, [])

  if (!ready) return <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center", background: "#f9fafb", color: "#9ca3af", fontSize: 14 }}>Cargando mapa...</div>
  return <div ref={containerRef} style={{ height: "100%", width: "100%" }} />
}

// ── Estilos reutilizables ────────────────────────────────────────────────────
const S = {
  btn: (color = "#dc2626", outline = false) => ({
    background: outline ? "white" : color,
    color: outline ? color : "white",
    border: `1.5px solid ${color}`,
    borderRadius: 8,
    padding: "8px 16px",
    cursor: "pointer",
    fontSize: 13,
    fontWeight: 600,
    transition: "opacity .15s",
  }),
  card: { background: "white", border: "1px solid #e5e7eb", borderRadius: 12, padding: "14px 18px" },
  input: { width: "100%", border: "1px solid #d1d5db", borderRadius: 8, padding: "8px 12px", fontSize: 14, boxSizing: "border-box", outline: "none" },
  badge: (bg, color) => ({ background: bg, color, borderRadius: 20, padding: "2px 10px", fontSize: 11, fontWeight: 600 }),
  label: { display: "block", fontSize: 13, fontWeight: 500, color: "#374151", marginBottom: 4 },
  section: { maxWidth: 680, margin: "0 auto", padding: "24px 16px" },
}

// ── Navbar ───────────────────────────────────────────────────────────────────
function Navbar({ page, setPage, user, setUser }) {
  return (
    <nav style={{ background: "#dc2626", color: "white", padding: "0 16px", display: "flex", alignItems: "center", justifyContent: "space-between", minHeight: 52, flexShrink: 0, boxShadow: "0 2px 8px rgba(0,0,0,.2)" }}>
      <button onClick={() => setPage("home")} style={{ background: "none", border: "none", color: "white", fontWeight: 700, fontSize: 17, cursor: "pointer", display: "flex", alignItems: "center", gap: 6 }}>
        🚨 Pereira Alerta
      </button>
      <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        {[["home", "Mapa"], ["report", "Pedir ayuda"], ["volunteers", "Voluntarios"]].map(([p, label]) => (
          <button key={p} onClick={() => setPage(p)} style={{ background: "none", border: "none", color: page === p ? "white" : "rgba(255,255,255,.75)", cursor: "pointer", fontSize: 13, fontWeight: page === p ? 700 : 400, borderBottom: page === p ? "2px solid white" : "2px solid transparent", paddingBottom: 2 }}>
            {label}
          </button>
        ))}
        {user ? (
          <>
            {(user.role === "coordinator" || user.role === "volunteer") && (
              <button onClick={() => setPage("dashboard")} style={{ ...S.btn("white", false), color: "#dc2626", fontSize: 12, padding: "5px 12px" }}>Panel</button>
            )}
            <button onClick={() => { setUser(null); setPage("home") }} style={{ background: "none", border: "none", color: "rgba(255,255,255,.75)", cursor: "pointer", fontSize: 12 }}>
              {user.full_name.split(" ")[0]} · Salir
            </button>
          </>
        ) : (
          <button onClick={() => setPage("login")} style={{ ...S.btn("white", false), color: "#dc2626", fontSize: 12, padding: "5px 12px" }}>Ingresar</button>
        )}
      </div>
    </nav>
  )
}

// ── Página inicio / mapa ─────────────────────────────────────────────────────
function HomePage({ reports, aidPoints, dangerZones, setPage }) {
  const [filters, setFilters] = useState({ reports: true, aidPoints: true, dangerZones: true })
  const toggle = (k) => setFilters((f) => ({ ...f, [k]: !f[k] }))

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {DEMO_MODE && (
        <div style={{ background: "#fef9c3", borderBottom: "1px solid #fcd34d", padding: "6px 16px", fontSize: 12, color: "#854d0e", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span>⚠️ Modo demo — datos de ejemplo. Inicia el backend en localhost:8000 para datos reales.</span>
        </div>
      )}
      <div style={{ background: "white", borderBottom: "1px solid #e5e7eb", padding: "8px 16px", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8, flexWrap: "wrap", flexShrink: 0 }}>
        <div style={{ display: "flex", gap: 8 }}>
          {[
            { k: "reports", label: `🆘 Emergencias (${reports.length})` },
            { k: "aidPoints", label: `🤝 Ayudas (${aidPoints.length})` },
            { k: "dangerZones", label: `⚠️ Peligro (${dangerZones.length})` },
          ].map(({ k, label }) => (
            <button key={k} onClick={() => toggle(k)} style={{ ...S.badge(filters[k] ? "#1f2937" : "#f3f4f6", filters[k] ? "white" : "#6b7280"), cursor: "pointer", border: "none", padding: "6px 12px", fontSize: 12 }}>
              {label}
            </button>
          ))}
        </div>
        <button onClick={() => setPage("report")} style={{ ...S.btn(), fontSize: 13, padding: "7px 16px" }}>+ Pedir ayuda</button>
      </div>

      <div style={{ flex: 1, minHeight: 0 }}>
        <MapView
          reports={filters.reports ? reports : []}
          aidPoints={filters.aidPoints ? aidPoints : []}
          dangerZones={filters.dangerZones ? dangerZones : []}
        />
      </div>

      <div style={{ background: "white", borderTop: "1px solid #e5e7eb", padding: "8px 16px", display: "flex", gap: 16, flexShrink: 0, overflowX: "auto" }}>
        {[["#ef4444", "🆘", "Emergencia"], ["#3b82f6", "🏠", "Albergue"], ["#10b981", "⚕️", "Médico"], ["#f59e0b", "🍲", "Alimentos"], ["#06b6d4", "💧", "Agua"]].map(([c, e, l]) => (
          <div key={l} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "#6b7280", whiteSpace: "nowrap" }}>
            <span style={{ width: 20, height: 20, background: c, borderRadius: "50%", display: "inline-flex", alignItems: "center", justifyContent: "center", fontSize: 11 }}>{e}</span>
            {l}
          </div>
        ))}
        <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "#6b7280" }}>
          <span style={{ width: 20, height: 20, background: "rgba(239,68,68,.25)", border: "2px solid #ef4444", borderRadius: "50%" }} />
          Zona peligro
        </div>
      </div>
    </div>
  )
}

// ── Formulario de reporte ────────────────────────────────────────────────────
function ReportPage({ reports, setReports, setPage, token }) {
  const [form, setForm] = useState({ reporter_name: "", reporter_phone: "", need_type: "", description: "", address: "", people_count: 1, lat: null, lng: null })
  const [clicked, setClicked] = useState(null)
  const [loading, setLoading] = useState(false)
  const [sent, setSent] = useState(false)

  const fc = (e) => setForm((f) => ({ ...f, [e.target.name]: e.target.value }))
  const handleMapClick = (latlng) => { setClicked(latlng); setForm((f) => ({ ...f, lat: latlng.lat, lng: latlng.lng })) }

  const submit = async (e) => {
    e.preventDefault()
    if (!form.need_type) return alert("Selecciona el tipo de ayuda que necesitas")
    if (!form.lat) return alert("Marca tu ubicación en el mapa")
    setLoading(true)
    try {
      if (DEMO_MODE) {
        const newReport = { ...form, id: Date.now(), status: "pending", people_count: Number(form.people_count) }
        setReports((prev) => [newReport, ...prev])
      } else {
        await api("POST", "/reports/", { ...form, people_count: Number(form.people_count) }, token)
      }
      setSent(true)
    } catch { alert("Error al enviar el reporte") }
    finally { setLoading(false) }
  }

  if (sent) return (
    <div style={{ ...S.section, textAlign: "center", paddingTop: 60 }}>
      <div style={{ fontSize: 48, marginBottom: 16 }}>✅</div>
      <h2 style={{ color: "#15803d", margin: "0 0 8px" }}>Solicitud enviada</h2>
      <p style={{ color: "#6b7280", fontSize: 14, marginBottom: 24 }}>Los voluntarios serán notificados de tu ubicación.</p>
      <button onClick={() => setPage("home")} style={S.btn()}>Ver mapa</button>
    </div>
  )

  return (
    <div style={S.section}>
      <h1 style={{ margin: "0 0 4px", fontSize: 22, color: "#111827" }}>Pedir ayuda</h1>
      <p style={{ margin: "0 0 24px", fontSize: 13, color: "#6b7280" }}>Sin necesidad de crear una cuenta. Tu reporte aparecerá en el mapa.</p>

      <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        <div>
          <label style={S.label}>¿Qué necesitas?</label>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            {NEED_OPTIONS.map((o) => (
              <label key={o.value} style={{ display: "flex", alignItems: "center", gap: 8, border: `1.5px solid ${form.need_type === o.value ? "#dc2626" : "#e5e7eb"}`, borderRadius: 8, padding: "10px 12px", cursor: "pointer", background: form.need_type === o.value ? "#fff1f2" : "white", fontSize: 13, transition: "all .1s" }}>
                <input type="radio" name="need_type" value={o.value} checked={form.need_type === o.value} onChange={fc} style={{ accentColor: "#dc2626" }} />
                {o.label}
              </label>
            ))}
          </div>
        </div>

        <div>
          <label style={S.label}>Describe la situación</label>
          <textarea name="description" value={form.description} onChange={fc} required rows={3} placeholder="Cuántas personas, condición de salud, acceso al lugar..." style={{ ...S.input, resize: "vertical", fontFamily: "inherit" }} />
        </div>

        <div>
          <label style={S.label}>Dirección o referencia en Pereira</label>
          <input name="address" value={form.address} onChange={fc} required placeholder="Cra 7 # 19-25, barrio Cuba, cerca de la iglesia..." style={S.input} />
        </div>

        <div>
          <label style={S.label}>Personas que necesitan ayuda</label>
          <input type="number" name="people_count" value={form.people_count} onChange={fc} min={1} max={500} style={{ ...S.input, width: 80 }} />
        </div>

        <div>
          <label style={S.label}>
            Marca tu ubicación en el mapa {form.lat && <span style={{ color: "#15803d", fontWeight: 400 }}>✓ seleccionada</span>}
          </label>
          <div style={{ height: 240, border: "1px solid #d1d5db", borderRadius: 8, overflow: "hidden" }}>
            <MapView reports={[]} aidPoints={[]} dangerZones={[]} onMapClick={handleMapClick} clickedLatLng={clicked} />
          </div>
          <p style={{ margin: "4px 0 0", fontSize: 12, color: "#9ca3af" }}>Toca el mapa para marcar el punto exacto</p>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <div>
            <label style={S.label}>Tu nombre</label>
            <input name="reporter_name" value={form.reporter_name} onChange={fc} required placeholder="Juan Pérez" style={S.input} />
          </div>
          <div>
            <label style={S.label}>Teléfono (opcional)</label>
            <input name="reporter_phone" value={form.reporter_phone} onChange={fc} placeholder="300 123 4567" style={S.input} />
          </div>
        </div>

        <button type="submit" disabled={loading} style={{ ...S.btn(), padding: "12px", fontSize: 15, borderRadius: 12, opacity: loading ? .6 : 1 }}>
          {loading ? "Enviando..." : "🆘 Enviar solicitud de ayuda"}
        </button>
      </form>
    </div>
  )
}

// ── Lista de voluntarios ─────────────────────────────────────────────────────
function VolunteersPage({ token }) {
  const [volunteers, setVolunteers] = useState(DEMO.volunteers)
  const [skill, setSkill] = useState("")
  const SKILLS = ["médico", "logística", "psicología", "rescate", "cocina", "primeros auxilios"]

  const filtered = skill ? volunteers.filter((v) => v.skills?.toLowerCase().includes(skill)) : volunteers

  return (
    <div style={S.section}>
      <h1 style={{ margin: "0 0 4px", fontSize: 22, color: "#111827" }}>Voluntarios disponibles</h1>
      <p style={{ margin: "0 0 20px", fontSize: 13, color: "#6b7280" }}>Personas que pueden apoyar en Pereira y sus barrios.</p>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 20 }}>
        {["", ...SKILLS].map((s) => (
          <button key={s || "todos"} onClick={() => setSkill(s)} style={{ ...S.badge(skill === s ? "#1f2937" : "#f3f4f6", skill === s ? "white" : "#6b7280"), cursor: "pointer", border: "none", padding: "6px 14px", fontSize: 12 }}>
            {s || "Todos"}
          </button>
        ))}
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {filtered.map((v) => (
          <div key={v.id} style={{ ...S.card, display: "flex", alignItems: "flex-start", gap: 12 }}>
            <div style={{ width: 40, height: 40, borderRadius: "50%", background: "#fee2e2", color: "#dc2626", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700, fontSize: 14, flexShrink: 0 }}>
              {v.full_name.charAt(0).toUpperCase()}
            </div>
            <div style={{ flex: 1 }}>
              <p style={{ margin: 0, fontWeight: 600, fontSize: 14 }}>{v.full_name}</p>
              {v.neighborhood && <p style={{ margin: "2px 0 0", fontSize: 12, color: "#6b7280" }}>📍 {v.neighborhood}</p>}
              <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 6 }}>
                {v.skills?.split(",").map((s) => (
                  <span key={s} style={{ ...S.badge("#eff6ff", "#1d4ed8"), border: "1px solid #bfdbfe", padding: "2px 8px" }}>{s.trim()}</span>
                ))}
              </div>
            </div>
            {v.phone && (
              <a href={`tel:${v.phone}`} style={{ ...S.btn("#16a34a"), textDecoration: "none", fontSize: 12, padding: "6px 12px" }}>📞 Llamar</a>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Login / Registro ─────────────────────────────────────────────────────────
function LoginPage({ setUser, setPage }) {
  const [mode, setMode] = useState("login")
  const [form, setForm] = useState({ phone: "", password: "", full_name: "", role: "volunteer", skills: "", neighborhood: "" })
  const [loading, setLoading] = useState(false)
  const fc = (e) => setForm((f) => ({ ...f, [e.target.name]: e.target.value }))

  const submit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      if (DEMO_MODE) {
        // Demo: simula login
        const demoUser = { id: 1, full_name: form.full_name || "Coordinador Demo", phone: form.phone, role: form.role || "coordinator", skills: form.skills, neighborhood: form.neighborhood }
        setUser(demoUser)
        setPage("home")
      } else {
        const data = await api("POST", mode === "login" ? "/auth/login" : "/auth/register", form)
        setUser(data.user)
        setPage("home")
      }
    } catch (err) {
      alert(err?.detail || "Error al ingresar")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ minHeight: "calc(100vh - 52px)", display: "flex", alignItems: "center", justifyContent: "center", background: "#f9fafb", padding: 16 }}>
      <div style={{ ...S.card, width: "100%", maxWidth: 420, boxShadow: "0 4px 24px rgba(0,0,0,.08)" }}>
        <h1 style={{ margin: "0 0 4px", fontSize: 20 }}>{mode === "login" ? "Ingresar" : "Crear cuenta"}</h1>
        <p style={{ margin: "0 0 24px", fontSize: 13, color: "#6b7280" }}>
          {DEMO_MODE ? "⚠️ Modo demo: cualquier datos funciona" : mode === "login" ? "Para gestionar reportes y puntos de ayuda" : "Las víctimas pueden reportar sin cuenta"}
        </p>

        <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {mode === "register" && (
            <>
              <div>
                <label style={S.label}>Nombre completo</label>
                <input name="full_name" value={form.full_name} onChange={fc} required style={S.input} placeholder="Ana García" />
              </div>
              <div>
                <label style={S.label}>Rol</label>
                <div style={{ display: "flex", gap: 8 }}>
                  {[["volunteer", "🤝 Voluntario/a"], ["coordinator", "📋 Coordinador/a"]].map(([v, l]) => (
                    <label key={v} style={{ flex: 1, textAlign: "center", border: `1.5px solid ${form.role === v ? "#dc2626" : "#e5e7eb"}`, borderRadius: 8, padding: "8px 4px", cursor: "pointer", background: form.role === v ? "#fff1f2" : "white", fontSize: 13 }}>
                      <input type="radio" name="role" value={v} checked={form.role === v} onChange={fc} style={{ marginRight: 4 }} />{l}
                    </label>
                  ))}
                </div>
              </div>
              <div>
                <label style={S.label}>Habilidades (separadas por coma)</label>
                <input name="skills" value={form.skills} onChange={fc} placeholder="médico, logística, psicología" style={S.input} />
              </div>
              <div>
                <label style={S.label}>Barrio en Pereira</label>
                <input name="neighborhood" value={form.neighborhood} onChange={fc} placeholder="Cuba, Álamos, Centro..." style={S.input} />
              </div>
            </>
          )}
          <div>
            <label style={S.label}>Teléfono (usuario)</label>
            <input name="phone" value={form.phone} onChange={fc} required placeholder="3001234567" style={S.input} />
          </div>
          <div>
            <label style={S.label}>Contraseña</label>
            <input type="password" name="password" value={form.password} onChange={fc} required style={S.input} placeholder="••••••••" />
          </div>
          <button type="submit" disabled={loading} style={{ ...S.btn(), padding: "10px", fontSize: 14, borderRadius: 10, opacity: loading ? .6 : 1, marginTop: 4 }}>
            {loading ? "..." : mode === "login" ? "Ingresar" : "Registrarse"}
          </button>
        </form>

        <p style={{ textAlign: "center", fontSize: 13, color: "#6b7280", marginTop: 16 }}>
          {mode === "login" ? <>¿Sin cuenta? <button onClick={() => setMode("register")} style={{ background: "none", border: "none", color: "#dc2626", cursor: "pointer", fontWeight: 600 }}>Regístrate</button></> : <>¿Ya tienes cuenta? <button onClick={() => setMode("login")} style={{ background: "none", border: "none", color: "#dc2626", cursor: "pointer", fontWeight: 600 }}>Ingresar</button></>}
        </p>
      </div>
    </div>
  )
}

// ── Panel coordinador ────────────────────────────────────────────────────────
function DashboardPage({ reports, setReports, aidPoints, setAidPoints, dangerZones, setDangerZones, user, token }) {
  const [tab, setTab] = useState("reports")
  const [addMode, setAddMode] = useState(null) // 'aid' | 'danger' | null
  const [clicked, setClicked] = useState(null)
  const [addForm, setAddForm] = useState({})
  const fc = (e) => setAddForm((f) => ({ ...f, [e.target.name]: e.target.value }))

  const changeStatus = (id, status) => setReports((prev) => prev.map((r) => r.id === id ? { ...r, status } : r))

  const submitAid = (e) => {
    e.preventDefault()
    if (!addForm.lat) return alert("Marca la ubicación en el mapa")
    setAidPoints((prev) => [...prev, { ...addForm, id: Date.now(), is_active: true, capacity: addForm.capacity ? Number(addForm.capacity) : null }])
    setAddMode(null); setAddForm({}); setClicked(null)
  }

  const submitDanger = (e) => {
    e.preventDefault()
    if (!addForm.lat) return alert("Marca el centro de la zona en el mapa")
    setDangerZones((prev) => [...prev, { ...addForm, id: Date.now(), is_active: true, radius_meters: Number(addForm.radius_meters || 200) }])
    setAddMode(null); setAddForm({}); setClicked(null)
  }

  const inpt = { ...S.input, marginBottom: 0 }

  const TABS = [
    ["reports", `🆘 Reportes (${reports.length})`],
    ["aid", `🤝 Puntos de ayuda (${aidPoints.length})`],
    ["danger", `⚠️ Peligro (${dangerZones.length})`],
    ["map", "🗺️ Mapa"],
  ]

  return (
    <div style={S.section}>
      <h1 style={{ margin: "0 0 4px", fontSize: 22, color: "#111827" }}>Panel de coordinación</h1>
      <p style={{ margin: "0 0 20px", fontSize: 13, color: "#6b7280" }}>Hola, {user?.full_name} · {user?.role}</p>

      <div style={{ display: "flex", gap: 0, borderBottom: "1px solid #e5e7eb", marginBottom: 20, overflowX: "auto" }}>
        {TABS.map(([k, label]) => (
          <button key={k} onClick={() => setTab(k)} style={{ background: "none", border: "none", borderBottom: `2px solid ${tab === k ? "#dc2626" : "transparent"}`, color: tab === k ? "#dc2626" : "#6b7280", padding: "8px 14px", cursor: "pointer", fontSize: 13, fontWeight: tab === k ? 600 : 400, whiteSpace: "nowrap" }}>
            {label}
          </button>
        ))}
      </div>

      {/* Reportes */}
      {tab === "reports" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {reports.map((r) => {
            const st = STATUS_META[r.status]
            return (
              <div key={r.id} style={{ ...S.card, display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 14 }}>{NEED_LABELS[r.need_type]}</span>
                    <span style={S.badge(st.bg, st.color)}>{st.label}</span>
                  </div>
                  <p style={{ margin: "2px 0", fontSize: 12, color: "#6b7280" }}>{r.address}</p>
                  <p style={{ margin: "4px 0", fontSize: 13 }}>{r.description}</p>
                  <p style={{ margin: 0, fontSize: 12, color: "#9ca3af" }}>{r.reporter_name} · {r.people_count} persona(s){r.reporter_phone ? ` · ${r.reporter_phone}` : ""}</p>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 6, flexShrink: 0 }}>
                  {r.status === "pending" && <button onClick={() => changeStatus(r.id, "in_progress")} style={{ ...S.btn("#d97706"), fontSize: 12, padding: "5px 12px" }}>Tomar caso</button>}
                  {r.status === "in_progress" && <button onClick={() => changeStatus(r.id, "resolved")} style={{ ...S.btn("#16a34a"), fontSize: 12, padding: "5px 12px" }}>Marcar resuelto</button>}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Puntos de ayuda */}
      {tab === "aid" && (
        <div>
          <button onClick={() => { setAddMode("aid"); setClicked(null); setAddForm({}) }} style={{ ...S.btn("#2563eb"), marginBottom: 16 }}>+ Agregar punto de ayuda</button>
          {addMode === "aid" && (
            <form onSubmit={submitAid} style={{ background: "#eff6ff", border: "1px solid #bfdbfe", borderRadius: 12, padding: 16, marginBottom: 16, display: "flex", flexDirection: "column", gap: 10 }}>
              <p style={{ margin: 0, fontWeight: 600, color: "#1d4ed8", fontSize: 13 }}>Nuevo punto de ayuda — haz clic en el mapa para ubicarlo</p>
              <div style={{ height: 200, borderRadius: 8, overflow: "hidden", border: "1px solid #bfdbfe" }}>
                <MapView reports={[]} aidPoints={[]} dangerZones={[]} onMapClick={(ll) => { setClicked(ll); setAddForm((f) => ({ ...f, lat: ll.lat, lng: ll.lng })) }} clickedLatLng={clicked} />
              </div>
              {addForm.lat && <p style={{ margin: 0, fontSize: 12, color: "#15803d" }}>✓ {addForm.lat.toFixed(5)}, {addForm.lng.toFixed(5)}</p>}
              <input name="name" placeholder="Nombre del punto" required onChange={fc} style={inpt} />
              <select name="aid_type" required onChange={fc} style={inpt}>
                <option value="">Tipo de ayuda...</option>
                {Object.entries(AID_EMOJI).map(([k, v]) => <option key={k} value={k}>{v} {k}</option>)}
              </select>
              <input name="address" placeholder="Dirección" required onChange={fc} style={inpt} />
              <input name="contact_phone" placeholder="Teléfono de contacto" onChange={fc} style={inpt} />
              <input type="number" name="capacity" placeholder="Cupos disponibles" onChange={fc} style={inpt} />
              <div style={{ display: "flex", gap: 8 }}>
                <button type="submit" style={S.btn("#2563eb")}>Guardar</button>
                <button type="button" onClick={() => setAddMode(null)} style={{ background: "none", border: "none", cursor: "pointer", color: "#6b7280", fontSize: 13 }}>Cancelar</button>
              </div>
            </form>
          )}
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {aidPoints.map((a) => (
              <div key={a.id} style={{ ...S.card, display: "flex", justifyContent: "space-between", alignItems: "center", opacity: a.is_active ? 1 : .5 }}>
                <div>
                  <span style={{ fontWeight: 600, fontSize: 14 }}>{AID_EMOJI[a.aid_type]} {a.name}</span>
                  <p style={{ margin: "2px 0 0", fontSize: 12, color: "#6b7280" }}>{a.address}</p>
                </div>
                {a.capacity && <span style={{ fontSize: 12, color: "#6b7280" }}>{a.capacity} cupos</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Zonas de peligro */}
      {tab === "danger" && (
        <div>
          <button onClick={() => { setAddMode("danger"); setClicked(null); setAddForm({}) }} style={{ ...S.btn(), marginBottom: 16 }}>+ Definir zona de peligro</button>
          {addMode === "danger" && (
            <form onSubmit={submitDanger} style={{ background: "#fff1f2", border: "1px solid #fecdd3", borderRadius: 12, padding: 16, marginBottom: 16, display: "flex", flexDirection: "column", gap: 10 }}>
              <p style={{ margin: 0, fontWeight: 600, color: "#b91c1c", fontSize: 13 }}>Nueva zona — haz clic en el mapa para marcar el centro</p>
              <div style={{ height: 200, borderRadius: 8, overflow: "hidden", border: "1px solid #fecdd3" }}>
                <MapView reports={[]} aidPoints={[]} dangerZones={[]} onMapClick={(ll) => { setClicked(ll); setAddForm((f) => ({ ...f, lat: ll.lat, lng: ll.lng })) }} clickedLatLng={clicked} />
              </div>
              {addForm.lat && <p style={{ margin: 0, fontSize: 12, color: "#15803d" }}>✓ {addForm.lat.toFixed(5)}, {addForm.lng.toFixed(5)}</p>}
              <input name="name" placeholder="Nombre de la zona" required onChange={fc} style={inpt} />
              <select name="danger_level" required onChange={fc} style={inpt}>
                <option value="">Nivel de peligro...</option>
                <option value="low">Precaución (bajo)</option>
                <option value="medium">Peligro moderado</option>
                <option value="high">Peligro alto</option>
                <option value="critical">Zona roja — evacuar</option>
              </select>
              <input type="number" name="radius_meters" placeholder="Radio en metros (ej: 300)" defaultValue={200} onChange={fc} style={inpt} />
              <textarea name="description" placeholder="Descripción del peligro" required rows={2} onChange={fc} style={{ ...inpt, resize: "vertical", fontFamily: "inherit" }} />
              <div style={{ display: "flex", gap: 8 }}>
                <button type="submit" style={S.btn()}>Guardar</button>
                <button type="button" onClick={() => setAddMode(null)} style={{ background: "none", border: "none", cursor: "pointer", color: "#6b7280", fontSize: 13 }}>Cancelar</button>
              </div>
            </form>
          )}
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {dangerZones.map((z) => (
              <div key={z.id} style={{ ...S.card, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <span style={{ fontWeight: 600, fontSize: 14 }}>{z.name}</span>
                  <span style={{ ...S.badge(DANGER_COLOR[z.danger_level] + "22", DANGER_COLOR[z.danger_level]), marginLeft: 8, border: `1px solid ${DANGER_COLOR[z.danger_level]}44` }}>{DANGER_LABEL[z.danger_level]}</span>
                  <p style={{ margin: "3px 0 0", fontSize: 12, color: "#6b7280" }}>{z.description}</p>
                </div>
                <span style={{ fontSize: 12, color: "#9ca3af" }}>{z.radius_meters}m</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Mapa general */}
      {tab === "map" && (
        <div style={{ height: "60vh", borderRadius: 12, overflow: "hidden", border: "1px solid #e5e7eb" }}>
          <MapView reports={reports} aidPoints={aidPoints} dangerZones={dangerZones} />
        </div>
      )}
    </div>
  )
}

// ── App principal ─────────────────────────────────────────────────────────────
export default function App() {
  const [page, setPage] = useState("home")
  const [user, setUser] = useState(null)
  const [reports, setReports] = useState(DEMO.reports)
  const [aidPoints, setAidPoints] = useState(DEMO.aidPoints)
  const [dangerZones, setDangerZones] = useState(DEMO.dangerZones)

  const pages = { home: HomePage, report: ReportPage, volunteers: VolunteersPage, login: LoginPage, dashboard: DashboardPage }
  const Page = pages[page] || HomePage

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column", fontFamily: "system-ui, -apple-system, sans-serif", background: "#f9fafb" }}>
      <Navbar page={page} setPage={setPage} user={user} setUser={setUser} />
      <div style={{ flex: 1, overflow: "auto", display: "flex", flexDirection: "column" }}>
        <Page
          page={page} setPage={setPage}
          user={user} setUser={setUser}
          reports={reports} setReports={setReports}
          aidPoints={aidPoints} setAidPoints={setAidPoints}
          dangerZones={dangerZones} setDangerZones={setDangerZones}
        />
      </div>
    </div>
  )
}
