// website/static/js/sw.js
const STATIC_CACHE_NAME = 'decooffice-static-v3'; // Incremented version
const DYNAMIC_CACHE_NAME = 'decooffice-dynamic-v3';

const urlsToCache = [
    '/',
    '/offline',
    '/static/js/common.js',
    '/static/js/db.js',
    'https://cdn.jsdelivr.net/npm/idb@7/build/umd.js',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css'
];

importScripts('https://cdn.jsdelivr.net/npm/idb@7/build/umd.js');

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(STATIC_CACHE_NAME).then(cache => cache.addAll(urlsToCache))
    );
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys => Promise.all(
            keys.filter(key => key !== STATIC_CACHE_NAME && key !== DYNAMIC_CACHE_NAME)
                .map(key => caches.delete(key))
        ))
    );
});

// --- START OF MODIFICATION: Network-first fetch strategy ---
self.addEventListener('fetch', event => {
    event.respondWith(
        fetch(event.request)
            .then(response => {
                // If the network request is successful, cache it and return it.
                const clonedResponse = response.clone();
                caches.open(DYNAMIC_CACHE_NAME).then(cache => {
                    cache.put(event.request.url, clonedResponse);
                });
                return response;
            })
            .catch(() => {
                // If the network fails, try to serve from the cache as a fallback.
                return caches.match(event.request).then(cachedResponse => {
                    if (cachedResponse) {
                        return cachedResponse;
                    }
                    if (event.request.mode === 'navigate') {
                        return caches.match('/offline');
                    }
                });
            })
    );
});
// --- END OF MODIFICATION ---


// --- Other Service Worker logic (Push, Sync) goes below ---
self.addEventListener('push', event => { /* ... your push logic ... */ });
self.addEventListener('notificationclick', event => { /* ... your notification click logic ... */ });
self.addEventListener('sync', event => { /* ... your sync logic ... */ });