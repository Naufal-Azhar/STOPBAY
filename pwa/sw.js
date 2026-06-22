// STOPBAY PWA - Service Worker
// Background sync + push notification ready

const CACHE_NAME = 'stopbay-v2';
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/styles.css',
  '/app.js',
  '/manifest.json',
];

// Install: cache static assets
self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

// Activate: clean old caches
self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Fetch: network-first strategy for API, cache-first for static
self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);

  // API calls: network only (no cache for real-time data)
  if (url.pathname.startsWith('/api/')) {
    e.respondWith(fetch(e.request).catch(() =>
      new Response(JSON.stringify({ success: false, message: 'Offline' }),
                   { headers: { 'Content-Type': 'application/json' } })
    ));
    return;
  }

  // Static assets: cache-first, network fallback
  e.respondWith(
    caches.match(e.request).then((cached) =>
      cached || fetch(e.request).then((networkResp) => {
        const clone = networkResp.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(e.request, clone));
        return networkResp;
      })
    )
  );
});

// Push notification (ready for HTTPS)
self.addEventListener('push', (e) => {
  const data = e.data ? e.data.json() : {};
  const title = data.title || 'STOPBAY';
  const options = {
    body: data.body || 'Parking update available',
    icon: '/icon-192.png',
    badge: '/icon-192.png',
    vibrate: [200, 100, 200],
  };
  e.waitUntil(self.registration.showNotification(title, options));
});
