// Lightweight pass-through Service Worker for PWA Installability
// Never caches video streams, HLS segments, or api.php responses.
self.addEventListener('install', (event) => {
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', (event) => {
    // Pass all requests straight through to the network so NAS media & API stay fresh
    if (event.request.method !== 'GET') return;
    event.respondWith(fetch(event.request));
});
