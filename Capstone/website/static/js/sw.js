// website/static/js/sw.js
const STATIC_CACHE_NAME = 'decooffice-static-v8';
const DYNAMIC_CACHE_NAME = 'decooffice-dynamic-v8';

const urlsToCache = [
    '/',
    '/offline',
    '/splash',
    '/static/js/common.js',
    '/static/js/db.js',
    'https://cdn.jsdelivr.net/npm/idb@7/build/umd.js',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css',
    '/static/imgs/icons/logo192.png',
    '/static/imgs/icons/logo512.png',
    '/static/imgs/icons/icon-maskable-512.png'
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

// --- START OF MODIFICATION: Updated Fetch Event Listener ---
self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);

    // --- Special Strategy for Calendar API ---
    if (url.pathname.startsWith('/api/schedules')) {
        event.respondWith(
            // 1. Try to fetch from the network first
            fetch(event.request).then(networkResponse => {
                // If successful, cache the response and return it
                return caches.open(DYNAMIC_CACHE_NAME).then(cache => {
                    cache.put(event.request.url, networkResponse.clone());
                    return networkResponse;
                });
            }).catch(() => {
                // If the network request fails (offline), get the data from the cache
                return caches.match(event.request);
            })
        );
    } 
    // --- General Strategy for other requests ---
    else {
        event.respondWith(
            caches.match(event.request)
                .then(cachedResponse => {
                    // Return from cache if found
                    if (cachedResponse) {
                        return cachedResponse;
                    }
                    // Otherwise, fetch from network
                    return fetch(event.request)
                        .then(networkResponse => {
                            // If we get a valid response, cache it for future offline use
                            if (networkResponse && networkResponse.status === 200) {
                                return caches.open(DYNAMIC_CACHE_NAME).then(cache => {
                                    cache.put(event.request.url, networkResponse.clone());
                                    return networkResponse;
                                });
                            }
                            return networkResponse;
                        })
                        .catch(() => {
                            // If both cache and network fail, show the offline page for navigation requests
                            if (event.request.mode === 'navigate') {
                                return caches.match('/offline');
                            }
                        });
                })
        );
    }
});
// --- END OF MODIFICATION ---


// --- Other Service Worker logic (Push, Sync) ---
const dbPromise = idb.openDB('deco-office-db', 1);

async function syncOutbox() {
    const db = await dbPromise;
    const outboxStore = db.transaction('transaction-outbox', 'readwrite').store;
    let requests = await outboxStore.getAll();
    if (!requests.length) return;

    for (const req of requests) {
        try {
            const response = await fetch(req.url, {
                method: req.method,
                headers: req.headers,
            });
            if (response.ok) {
                await outboxStore.delete(req.id);
            }
        } catch (error) {
            console.error('Sync failed for request:', req.id, error);
        }
    }
}

self.addEventListener('sync', event => {
    if (event.tag === 'sync-deleted-items') {
        event.waitUntil(syncOutbox());
    }
});

self.addEventListener('push', event => {
    let data = { title: 'New Notification', body: 'Something happened!', icon: '/static/imgs/icons/logo.ico', data: { url: '/' } };
    if (event.data) {
        data = event.data.json();
    }
    const options = {
        body: data.body,
        icon: data.icon,
        badge: '/static/imgs/icons/logo.ico',
        data: {
            url: data.data.url
        }
    };
    event.waitUntil(
        self.registration.showNotification(data.title, options)
    );
});

self.addEventListener('notificationclick', event => {
    const notification = event.notification;
    const urlToOpen = notification.data.url;
    event.notification.close();
    event.waitUntil(
        clients.matchAll({ type: 'window' }).then(windowClients => {
            for (let client of windowClients) {
                if (client.url === urlToOpen && 'focus' in client) {
                    return client.focus();
                }
            }
            if (clients.openWindow) {
                return clients.openWindow(urlToOpen);
            }
        })
    );
});