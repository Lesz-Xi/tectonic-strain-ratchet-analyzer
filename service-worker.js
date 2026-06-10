const TSRA_CACHE_VERSION = 'tsra-field-cache-v4';
const CORE_ASSETS = [
  '/',
  '/seismic_report.html',
  '/manifest.webmanifest',
  '/seismic_pattern_analysis.svg',
  '/seismic_pattern_analysis.png'
];
const MEDIA_EXTENSIONS = ['.mp4', '.webm', '.m4a', '.mp3', '.mov'];
let lowDataMode = false;

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(TSRA_CACHE_VERSION)
      .then(cache => cache.addAll(CORE_ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys
        .filter(key => key !== TSRA_CACHE_VERSION)
        .map(key => caches.delete(key))))
      .then(() => self.clients.claim())
      .then(() => self.clients.matchAll({ type: 'window', includeUncontrolled: true }))
      .then(clients => Promise.all(clients.map(client => client.navigate(client.url))))
  );
});

self.addEventListener('message', event => {
  const data = event.data || {};
  if (data.type === 'TSRA_LOW_DATA') {
    lowDataMode = Boolean(data.enabled);
    return;
  }
  if (data.type === 'TSRA_CACHE_CORE') {
    event.waitUntil(
      caches.open(TSRA_CACHE_VERSION)
        .then(cache => cache.addAll(CORE_ASSETS))
        .then(() => notifyClients('core cached'))
        .catch(() => notifyClients('cache failed'))
    );
  }
});

self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (request.mode === 'navigate') {
    event.respondWith(networkFirst(request, '/seismic_report.html'));
    return;
  }

  const pathname = url.pathname;
  if (MEDIA_EXTENSIONS.some(ext => pathname.endsWith(ext))) {
    event.respondWith(mediaCacheStrategy(request));
    return;
  }

  event.respondWith(staleWhileRevalidate(request));
});

async function networkFirst(request, fallbackPath) {
  const cache = await caches.open(TSRA_CACHE_VERSION);
  try {
    const response = await fetch(request);
    if (response.ok) await cache.put(request, response.clone());
    return response;
  } catch (_) {
    return (await cache.match(request)) || (await cache.match(fallbackPath));
  }
}

async function staleWhileRevalidate(request) {
  const cache = await caches.open(TSRA_CACHE_VERSION);
  const cached = await cache.match(request);
  const network = fetch(request)
    .then(response => {
      if (response.ok) cache.put(request, response.clone());
      return response;
    })
    .catch(() => cached);
  return cached || network;
}

async function mediaCacheStrategy(request) {
  if (request.headers.has('range')) return fetch(request);
  const cache = await caches.open(TSRA_CACHE_VERSION);
  const cached = await cache.match(request);
  if (cached) return cached;
  if (lowDataMode) return fetch(request);
  const response = await fetch(request);
  if (response.ok && response.status !== 206) await cache.put(request, response.clone());
  return response;
}

async function notifyClients(status) {
  const clients = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
  for (const client of clients) client.postMessage({ type: 'TSRA_CACHE_STATUS', status });
}
