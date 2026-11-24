const CACHE_NAME = 'shoi-cache-v4';
const ASSETS = [
  '/',
  '/pwa/index.html',
  '/pwa/style.css',
  '/pwa/app.js',
  '/pwa/manifest.json',
  '/pwa/icon.svg',
  '/pwa/icon-192.png',
  '/pwa/icon-512.png'
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((k) => {
          if (k !== CACHE_NAME) return caches.delete(k);
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (e) => {
  // Network first with cache fallback
  e.respondWith(
    fetch(e.request).catch(() => caches.match(e.request))
  );
});
