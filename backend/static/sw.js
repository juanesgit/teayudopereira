/* ================================================================
   Te Ayudo Pereira — Service Worker
   Estrategias de caché para funcionamiento offline
   ================================================================ */

const CACHE_APP   = 'tap-app-v5'
const CACHE_API   = 'tap-api-v1'
const CACHE_TILES = 'tap-tiles-v1'

const APP_SHELL = [
  'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css',
  'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js',
  'https://cdnjs.cloudflare.com/ajax/libs/alpinejs/3.14.1/cdn.min.js',
]

// ── Install: pre-cachear app shell ──────────────────────────────
self.addEventListener('install', event => {
  self.skipWaiting()
  event.waitUntil(
    caches.open(CACHE_APP).then(cache =>
      Promise.allSettled(APP_SHELL.map(url => cache.add(url)))
    )
  )
})

// ── Activate: limpiar cachés viejos ────────────────────────────
self.addEventListener('activate', event => {
  const valid = [CACHE_APP, CACHE_API, CACHE_TILES]
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => !valid.includes(k)).map(k => caches.delete(k))))
      .then(() => clients.claim())
  )
})

// ── Helpers ────────────────────────────────────────────────────

async function networkFirst(request, cacheName) {
  try {
    const response = await fetch(request.clone())
    if (response.ok) {
      const cache = await caches.open(cacheName)
      cache.put(request, response.clone())
    }
    return response
  } catch {
    const cached = await caches.match(request)
    return cached ?? new Response(JSON.stringify([]), {
      headers: { 'Content-Type': 'application/json', 'X-From-Cache': 'true' }
    })
  }
}

async function cacheFirst(request, cacheName) {
  const cached = await caches.match(request)
  if (cached) return cached
  try {
    const response = await fetch(request.clone())
    if (response.ok) {
      const cache = await caches.open(cacheName)
      cache.put(request, response.clone())
    }
    return response
  } catch {
    return Response.error()
  }
}

async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName)
  const cached = await cache.match(request)
  const fetchPromise = fetch(request.clone()).then(res => {
    if (res.ok) cache.put(request, res.clone())
    return res
  }).catch(() => null)
  return cached ?? (await fetchPromise) ?? Response.error()
}

// ── Fetch: enrutamiento de estrategias ─────────────────────────
self.addEventListener('fetch', event => {
  const { request } = event
  if (request.method !== 'GET') return   // POST/PATCH los maneja la app

  const url = new URL(request.url)

  // Tiles de OpenStreetMap → cache-first (ahorra datos, funciona offline)
  if (url.hostname.includes('tile.openstreetmap.org')) {
    event.respondWith(cacheFirst(request, CACHE_TILES))
    return
  }

  // CDN (Leaflet, Alpine) → stale-while-revalidate
  // Nota: cdn.tailwindcss.com excluido — bloquea CORS en fetch cross-origin
  if (
    url.hostname === 'cdnjs.cloudflare.com' ||
    url.hostname === 'cdn.jsdelivr.net'
  ) {
    event.respondWith(staleWhileRevalidate(request, CACHE_APP))
    return
  }

  // API datos del mapa → network-first con fallback a caché
  if (url.pathname.match(/^\/(reports|aid-points|danger-zones)\//)) {
    event.respondWith(networkFirst(request, CACHE_API))
    return
  }

  // HTML principal → siempre network-first (garantiza HTML actualizado)
  if (url.pathname === '/') {
    event.respondWith(networkFirst(request, CACHE_APP))
    return
  }

  // Estáticos → stale-while-revalidate
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(staleWhileRevalidate(request, CACHE_APP))
    return
  }
})

// ── Background sync: notificar clientes al volver la red ───────
self.addEventListener('sync', event => {
  if (event.tag === 'sync-reports') {
    event.waitUntil(
      self.clients.matchAll().then(cls =>
        cls.forEach(c => c.postMessage({ type: 'SYNC_REPORTS' }))
      )
    )
  }
})

// ── Web Push: mostrar notificación ─────────────────────────────
self.addEventListener('push', event => {
  let data = { title: 'Te Ayudo Pereira', body: 'Tienes un mensaje nuevo', url: '/' }
  try {
    if (event.data) data = { ...data, ...JSON.parse(event.data.text()) }
  } catch {}

  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: '/static/icons/icon-192.png',
      badge: '/static/icons/icon-192.png',
      data: { url: data.url },
      vibrate: [200, 100, 200],
      requireInteraction: false,
    })
  )
})

// ── Click en notificación: abrir/enfocar la app ────────────────
self.addEventListener('notificationclick', event => {
  event.notification.close()
  const url = event.notification.data?.url || '/'
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(cls => {
      // Si ya hay una ventana abierta, enfocarla
      const existing = cls.find(c => c.url.includes(self.location.origin))
      if (existing) return existing.focus()
      // Si no, abrir una nueva
      return clients.openWindow(url)
    })
  )
})
