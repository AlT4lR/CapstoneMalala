// website/static/js/sw.js
const STATIC_CACHE_NAME = 'decooffice-static-v4';
const DYNAMIC_CACHE_NAME = 'decooffice-dynamic-v4';

const urlsToCache = [
    '/',
    '/offline',
    '/splash',
    '/static/js/common.js',
    '/static/js/db.js',
    'https://cdn.jsdelivr.net/npm/idb@7/build/umd.js',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css'
];

importScripts('https://cdn.jsdelivr.net/npm/idb@7/build/umd.js');

const dbPromise = idb.openDB('deco-office-db', 1);

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
                const clonedResponse = response.clone();
                caches.open(DYNAMIC_CACHE_NAME).then(cache => {
                    cache.put(event.request.url, clonedResponse);
                });
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
                console.log(`[Service Worker] Synced and deleted request with id: ${req.id}`);
            } else {
                console.error(`[Service Worker] Sync failed for id: ${req.id}, server responded with: ${response.status}`);
            }
        } catch (error) {
            console.error(`[Service Worker] Sync failed for id: ${req.id}, error:`, error);
        }
    }
}

self.addEventListener('sync', event => {
    if (event.tag === 'sync-deleted-items') {
        console.log('[Service Worker] Syncing deleted items...');
        event.waitUntil(syncOutbox());
    }
});

// --- START OF PUSH NOTIFICATION LOGIC ---

// This listener handles incoming push messages from the server.
self.addEventListener('push', event => {
    // Default data in case the push message is empty.
    let data = { 
        title: 'New Notification', 
        body: 'Something important happened!', 
        icon: '/static/imgs/icons/logo.ico',
        data: { url: '/' } // Default URL to open
    };
    
    // If the push event has data, parse it as JSON.
    if (event.data) {
        data = event.data.json();
    }

    // Define the options for the notification that will be shown.
    const options = {
        body: data.body,
        icon: data.icon, // The main icon.
        badge: '/static/imgs/icons/logo.ico', // A smaller icon for Android status bars.
        data: {
            url: data.data.url // Pass the URL to the notification's data payload.
        }
    };

    // Tell the browser to keep the Service Worker alive until the notification is shown.
    event.waitUntil(
        self.registration.showNotification(data.title, options)
    );
});

// --- END OF PUSH NOTIFICATION LOGIC ---


// --- START OF NOTIFICATION CLICK LOGIC ---

// This listener handles what happens when a user clicks on a notification.
self.addEventListener('notificationclick', event => {
    const notification = event.notification;
    const urlToOpen = notification.data.url;

    // Close the notification immediately after it's clicked.
    event.notification.close();

    // This logic checks if a window/tab with the target URL is already open.
    // If it is, it focuses that window. If not, it opens a new one.
    event.waitUntil(
        clients.matchAll({ type: 'window' }).then(windowClients => {
            // Check if there is an already open tab with the same URL.
            for (let client of windowClients) {
                if (client.url === urlToOpen && 'focus' in client) {
                    return client.focus(); // If so, focus it.
                }
            }
            // If no tab is found, open a new one.
            if (clients.openWindow) {
                return clients.openWindow(urlToOpen);
            }
        })
    );
});

// --- END OF NOTIFICATION CLICK LOGIC ---