const TSRA_CACHE_VERSION = 'tsra-field-cache-v46';
const CORE_ASSETS = [
  '/',
  '/seismic_report.html',
  '/manifest.webmanifest',
  '/tsra-version.json',
  '/duality-logo.png',
  '/duality-logo-light.png',
  '/duality-icon-64.png',
  '/duality-icon-192.png',
  '/duality-icon-512.png',
  '/seismic_pattern_analysis.svg',
  '/seismic_pattern_analysis.png'
];
const FIELD_MEMORY_ASSETS = [
  ...CORE_ASSETS,
  '/safety/80124894-56EA-42FF-BDF0-2F6C37B6453B.png',
  '/safety/Cotabato_Trench_Rhythm.mp4',
  '/safety/Twin_Tectonic_Giants.mp4'
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
  if (data.type === 'TSRA_VERSION_REQUEST') {
    if (event.source) event.source.postMessage({ type: 'TSRA_VERSION_RESPONSE', cacheVersion: TSRA_CACHE_VERSION });
    return;
  }
  if (data.type === 'TSRA_SKIP_WAITING') {
    self.skipWaiting();
    return;
  }
  if (data.type === 'TSRA_CACHE_CORE') {
    event.waitUntil(cacheUrls(CORE_ASSETS, 'core cached'));
    return;
  }
  if (data.type === 'TSRA_CACHE_FIELD_MEMORY') {
    event.waitUntil(cacheUrls(FIELD_MEMORY_ASSETS, 'field memory saved'));
    return;
  }
  if (data.type === 'TSRA_CACHE_URLS') {
    const urls = Array.isArray(data.urls) ? data.urls : [];
    event.waitUntil(cacheUrls(urls, 'interaction cached'));
    return;
  }
  if (data.type === 'TSRA_CLEAR_FIELD_MEMORY') {
    event.waitUntil(
      caches.delete(TSRA_CACHE_VERSION)
        .then(() => caches.open(TSRA_CACHE_VERSION))
        .then(cache => cache.addAll(CORE_ASSETS))
        .then(() => notifyClients('local memory cleared'))
        .catch(() => notifyClients('clear failed'))
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
  if (pathname === '/tsra-version.json') {
    event.respondWith(networkFirst(request, '/tsra-version.json'));
    return;
  }
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
  const cache = await caches.open(TSRA_CACHE_VERSION);
  if (request.headers.has('range')) {
    const cached = await cache.match(request.url);
    if (cached) return buildRangeResponse(request, cached);
    return fetch(request);
  }
  const cached = await cache.match(request.url);
  if (cached) return cached;
  if (lowDataMode) return fetch(request);
  const response = await fetch(request);
  if (response.ok && response.status !== 206) await cache.put(request.url, response.clone());
  return response;
}

async function buildRangeResponse(request, cachedResponse) {
  const rangeHeader = request.headers.get('range') || '';
  const match = rangeHeader.match(/bytes=(\d*)-(\d*)/);
  if (!match) return cachedResponse;
  const blob = await cachedResponse.blob();
  const size = blob.size;
  const start = match[1] ? Number(match[1]) : 0;
  const end = match[2] ? Number(match[2]) : size - 1;
  if (!Number.isFinite(start) || !Number.isFinite(end) || start > end || start >= size) {
    return new Response(null, {
      status: 416,
      headers: {
        'Content-Range': `bytes */${size}`,
        'Accept-Ranges': 'bytes'
      }
    });
  }
  const boundedEnd = Math.min(end, size - 1);
  const chunk = blob.slice(start, boundedEnd + 1, cachedResponse.headers.get('Content-Type') || 'application/octet-stream');
  return new Response(chunk, {
    status: 206,
    statusText: 'Partial Content',
    headers: {
      'Content-Type': cachedResponse.headers.get('Content-Type') || 'application/octet-stream',
      'Content-Length': String(chunk.size),
      'Content-Range': `bytes ${start}-${boundedEnd}/${size}`,
      'Accept-Ranges': 'bytes'
    }
  });
}

async function cacheUrls(urls, status) {
  const cache = await caches.open(TSRA_CACHE_VERSION);
  let cachedCount = 0;
  const safeUrls = urls
    .map(url => {
      try { return new URL(url, self.location.origin); } catch (_) { return null; }
    })
    .filter(url => url && url.origin === self.location.origin)
    .map(url => url.pathname + url.search);

  for (const url of [...new Set(safeUrls)]) {
    try {
      const response = await fetch(url, { credentials: 'same-origin' });
      if (response.ok && response.status !== 206) {
        await cache.put(url, response.clone());
        cachedCount += 1;
      }
    } catch (_) { }
  }
  await notifyClients(`${status} · ${cachedCount}/${safeUrls.length}`);
}

async function notifyClients(status) {
  const clients = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
  for (const client of clients) client.postMessage({ type: 'TSRA_CACHE_STATUS', status });
}
