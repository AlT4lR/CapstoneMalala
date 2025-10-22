// website/static/js/sw.js
const STATIC_CACHE_NAME = 'decooffice-static-v2'; // Increment version to force update
const DYNAMIC_CACHE_NAME = 'decooffice-dynamic-v2';

// --- MODIFICATION: Removed the problematic Tailwind CDN script ---
// We only cache essential files for the core app shell to work.
const urlsToCache = [
    '/',
    '/offline',
    '/static/js/common.js',
    '/static/js/db.js',
    'https://cdn.jsdelivr.net/npm/idb@7/build/umd.js',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css'
];

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
                await outboxStore.delete(req.id);
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


// --- START OF MODIFICATION: A more robust fetch strategy ---
self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);

    // Strategy 1: For API calls, try network first, then cache.
    // This ensures data is fresh but provides a fallback if offline.
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(
            fetch(event.request)
            .then(response => {
                // If successful, clone the response and cache it
                const clonedResponse = response.clone();
                caches.open(DYNAMIC_CACHE_NAME).then(cache => {
                    cache.put(event.request.url, clonedResponse);
                });
                return response;
            })
            .catch(() => {
                // If network fails, try to get the data from the cache
                return caches.match(event.request);
            })
        );
    // Strategy 2: For all other requests (pages, CSS, JS, images), use Cache-first.
    } else {
        event.respondWith(
            caches.match(event.request).then(response => {
                // If found in cache, return it.
                if (response) {
                    return response;
                }
                // Otherwise, go to the network.
                return fetch(event.request)
                    .then(fetchRes => {
                        // And cache the new resource for next time.
                        return caches.open(DYNAMIC_CACHE_NAME).then(cache => {
                            cache.put(event.request.url, fetchRes.clone());
                            return fetchRes;
                        });
                    })
                    .catch(() => {
                        // If the network fails for a page navigation, show the offline page.
                        if (event.request.mode === 'navigate') {
                            return caches.match('/offline');
                        }
                        // For other assets (like images), you could return a placeholder,
                        // but for now, we'll let them fail gracefully.
                    });
            })
        );
    }
});