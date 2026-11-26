// Lightweight pass-through Service Worker for PWA Installability
// Bypasses all media streams, Range requests, and API calls so video streaming
// and 206 Partial Content never pass through the Service Worker layer.
self.addEventListener('install', () => {
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', (event) => {
    const req = event.request;
    if (req.method !== 'GET') return;
    if (req.headers.has('range')) return;
    const url = new URL(req.url);
    if (url.pathname.startsWith('/media/') || url.pathname.endsWith('/api.php')) return;
    if (req.mode === 'navigate') {
        event.respondWith(fetch(req).catch(() => Response.error()));
    }
});
