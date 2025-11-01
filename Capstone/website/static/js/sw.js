// website/static/js/sw.js
const STATIC_CACHE_NAME = 'decooffice-static-v8'; // Increment version number
const DYNAMIC_CACHE_NAME = 'decooffice-dynamic-v8'; // Increment version number

const urlsToCache = [
    '/',
    '/offline',
    '/splash',
    '/static/js/common.js',
    '/static/js/db.js',
    'https://cdn.jsdelivr.net/npm/idb@7/build/umd.js',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css',
    // --- START OF MODIFICATION: Add all app icon paths to the cache ---
    '/static/imgs/icons/logo192.png',
    '/static/imgs/icons/logo512.png',
    '/static/imgs/icons/icon-maskable-512.png'
    // --- END OF MODIFICATION ---
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

self.addEventListener('fetch', event => {
    event.respondWith(
        fetch(event.request)
            .then(response => {
                if (response && response.status === 200 && response.type === 'basic') {
                    const clonedResponse = response.clone();
                    caches.open(DYNAMIC_CACHE_NAME).then(cache => {
                        cache.put(event.request.url, clonedResponse);
                    });
                }
                
                return response;
            })
            .catch(() => {
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