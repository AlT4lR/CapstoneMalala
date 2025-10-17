// website/static/sw.js
const STATIC_CACHE_NAME = 'decooffice-static-v1';
const DYNAMIC_CACHE_NAME = 'decooffice-dynamic-v1';

const urlsToCache = [
    '/',
    '/offline',
    '/static/js/common.js',
    '/static/js/db.js', // Cache the db helper
    'https://cdn.jsdelivr.net/npm/idb@7/build/umd.js', // Cache IndexedDB library
    'https://cdn.tailwindcss.com',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css'
];

// --- START OF MODIFICATION: Import IDB and add new event listeners ---
importScripts('https://cdn.jsdelivr.net/npm/idb@7/build/umd.js');

const dbPromise = idb.openDB('deco-office-db', 1);

self.addEventListener('sync', event => {
    if (event.tag === 'sync-deleted-items') {
        console.log('[Service Worker] Syncing deleted items...');
        event.waitUntil(syncOutbox());
    }
});

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
                await outboxStore.delete(req.id); // 'id' is the auto-incremented key
                console.log(`[SW] Synced and deleted request with id: ${req.id}`);
            } else {
                console.error(`[SW] Sync failed for id: ${req.id}, server responded with: ${response.status}`);
            }
        } catch (error) {
            console.error(`[SW] Sync failed for id: ${req.id}, error:`, error);
        }
    }
}

self.addEventListener('push', event => {
    let data = { title: 'New Notification', body: 'Something happened!', icon: '/static/imgs/icons/logo.ico' };
    if (event.data) {
        data = event.data.json();
    }

    const options = {
        body: data.body,
        icon: data.icon,
        badge: '/static/imgs/icons/logo.ico',
        data: {
            url: data.data.url // URL to open on click
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
// --- END OF MODIFICATION ---

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
        caches.match(event.request).then(response => {
            return response || fetch(event.request).then(fetchRes => {
                return caches.open(DYNAMIC_CACHE_NAME).then(cache => {
                    cache.put(event.request.url, fetchRes.clone());
                    return fetchRes;
                });
            });
        }).catch(() => {
            if (event.request.mode === 'navigate') {
                return caches.match('/offline');
            }
        })
    );
});