import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Circle, useMapEvents } from 'react-leaflet'
import L from 'leaflet'

// Coordenadas centro de Pereira
const PEREIRA_CENTER = [4.8133, -75.6961]

// Iconos SVG inline para cada tipo de marcador
const makeIcon = (color, emoji) =>
  L.divIcon({
    html: `<div style="background:${color};width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:16px;border:2px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.3)">${emoji}</div>`,
    className: '',
    iconSize: [32, 32],
    iconAnchor: [16, 16],
    popupAnchor: [0, -18],
  })

const REPORT_ICON = makeIcon('#ef4444', '🆘')
const AID_ICONS = {
  shelter: makeIcon('#3b82f6', '🏠'),
  food: makeIcon('#f59e0b', '🍲'),
  medical: makeIcon('#10b981', '⚕️'),
  water: makeIcon('#06b6d4', '💧'),
  supplies: makeIcon('#8b5cf6', '📦'),
  information: makeIcon('#6b7280', 'ℹ️'),
}

const DANGER_COLORS = {
  low: '#fbbf24',
  medium: '#f97316',
  high: '#ef4444',
  critical: '#7f1d1d',
}

const DANGER_LABELS = {
  low: 'Precaución',
  medium: 'Peligro moderado',
  high: 'Peligro alto',
  critical: 'Zona roja — evacuar',
}

const NEED_LABELS = {
  rescue: 'Rescate',
  medical: 'Atención médica',
  food: 'Alimentos / agua',
  shelter: 'Albergue',
  family: 'Búsqueda familiar',
  psychological: 'Apoyo psicológico',
  other: 'Otro',
}

const STATUS_LABELS = {
  pending: { label: 'Sin atender', color: 'bg-red-100 text-red-700' },
  in_progress: { label: 'En proceso', color: 'bg-yellow-100 text-yellow-700' },
  resolved: { label: 'Resuelto', color: 'bg-green-100 text-green-700' },
}

function ClickHandler({ onMapClick }) {
  useMapEvents({ click: (e) => onMapClick(e.latlng) })
  return null
}

export default function MapView({ reports, aidPoints, dangerZones, onMapClick, clickedLatLng }) {
  return (
    <MapContainer center={PEREIRA_CENTER} zoom={13} style={{ height: '100%', width: '100%' }}>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {onMapClick && <ClickHandler onMapClick={onMapClick} />}

      {/* Marcador de click activo */}
      {clickedLatLng && (
        <Marker position={[clickedLatLng.lat, clickedLatLng.lng]} icon={makeIcon('#6366f1', '📍')}>
          <Popup>Ubicación seleccionada</Popup>
        </Marker>
      )}

      {/* Zonas de peligro */}
      {dangerZones.map((zone) => (
        <Circle
          key={zone.id}
          center={[zone.lat, zone.lng]}
          radius={zone.radius_meters}
          pathOptions={{
            color: DANGER_COLORS[zone.danger_level],
            fillColor: DANGER_COLORS[zone.danger_level],
            fillOpacity: 0.25,
            weight: 2,
          }}
        >
          <Popup>
            <div className="min-w-[180px]">
              <p className="font-semibold text-sm">{zone.name}</p>
              <p className="text-xs text-gray-500 mt-1">{DANGER_LABELS[zone.danger_level]}</p>
              <p className="text-xs mt-1">{zone.description}</p>
            </div>
          </Popup>
        </Circle>
      ))}

      {/* Puntos de ayuda */}
      {aidPoints.map((ap) => (
        <Marker key={ap.id} position={[ap.lat, ap.lng]} icon={AID_ICONS[ap.aid_type] || AID_ICONS.information}>
          <Popup>
            <div className="min-w-[180px]">
              <p className="font-semibold text-sm">{ap.name}</p>
              <p className="text-xs text-gray-500 mt-0.5">{ap.address}</p>
              {ap.capacity && (
                <p className="text-xs mt-1">Cupos: <span className="font-medium">{ap.capacity}</span></p>
              )}
              {ap.contact_phone && (
                <p className="text-xs mt-0.5">Tel: <a href={`tel:${ap.contact_phone}`} className="text-blue-600">{ap.contact_phone}</a></p>
              )}
              {ap.description && <p className="text-xs mt-1 text-gray-600">{ap.description}</p>}
            </div>
          </Popup>
        </Marker>
      ))}

      {/* Reportes de emergencia */}
      {reports.map((r) => (
        <Marker key={r.id} position={[r.lat, r.lng]} icon={REPORT_ICON}>
          <Popup>
            <div className="min-w-[200px]">
              <div className="flex items-center justify-between mb-1">
                <span className="font-semibold text-sm">{NEED_LABELS[r.need_type]}</span>
                <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${STATUS_LABELS[r.status]?.color}`}>
                  {STATUS_LABELS[r.status]?.label}
                </span>
              </div>
              <p className="text-xs text-gray-500">{r.address}</p>
              <p className="text-xs mt-1">{r.description}</p>
              <p className="text-xs text-gray-400 mt-1">
                {r.people_count} persona(s) · {r.reporter_name}
              </p>
              {r.reporter_phone && (
                <a href={`tel:${r.reporter_phone}`} className="text-xs text-blue-600 mt-0.5 block">{r.reporter_phone}</a>
              )}
            </div>
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  )
}
