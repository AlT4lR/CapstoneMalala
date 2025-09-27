// static/js/sw.js

// --- CACHE NAMES & IndexedDB CONSTANTS ---
const STATIC_CACHE_NAME = 'decooffice-static-v2';  // For app shell, CSS, JS
const DYNAMIC_CACHE_NAME = 'decooffice-dynamic-v2'; // For API calls and dynamic content
const INVOICE_DB = 'invoice-queue-db';
const OUTBOX_STORE = 'outbox-invoices';

// --- IndexedDB Helper Functions for Service Worker ---

/**
 * Opens and returns the IndexedDB database instance.
 */
function openDatabase() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(INVOICE_DB, 1);

        request.onupgradeneeded = event => {
            const db = event.target.result;
            // Create the object store if it doesn't exist
            if (!db.objectStoreNames.contains(OUTBOX_STORE)) {
                db.createObjectStore(OUTBOX_STORE, { keyPath: 'id' });
            }
        };

        request.onsuccess = event => {
            resolve(event.target.result);
        };

        request.onerror = event => {
            console.error('IndexedDB error:', event.target.error);
            reject(event.target.error);
        };
    });
}

/**
 * Retrieves all items from the outbox store.
 */
function getOutboxItems() {
    return openDatabase().then(db => {
        return new Promise((resolve, reject) => {
            const transaction = db.transaction([OUTBOX_STORE], 'readonly');
            const store = transaction.objectStore(OUTBOX_STORE);
            const request = store.getAll();

            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    });
}

/**
 * Deletes an item from the outbox store after successful sync.
 */
function deleteOutboxItem(id) {
    return openDatabase().then(db => {
        return new Promise((resolve, reject) => {
            const transaction = db.transaction([OUTBOX_STORE], 'readwrite');
            const store = transaction.objectStore(OUTBOX_STORE);
            const request = store.delete(id);

            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
        });
    });
}

// --- Background Sync Implementation ---

/**
 * Attempts to sync all queued invoices from IndexedDB to the server.
 */
function syncInvoicesToServer() {
    // 1. Get all queued items from IndexedDB
    return getOutboxItems()
        .then(invoices => {
            if (invoices.length === 0) {
                console.log('No queued invoices to sync.');
                return Promise.resolve();
            }

            console.log(`Attempting to sync ${invoices.length} invoices...`);

            // 2. Process each queued invoice
            const syncPromises = invoices.map(invoice => {
                // NOTE: In a real app, file/blob reconstruction from IndexedDB would happen here.
                const formData = new FormData();
                const dummyFileBlob = new Blob(["Invoice Content"], { type: invoice.fileMimeType || 'application/pdf' });
                
                formData.append("invoice_file", dummyFileBlob, invoice.filename);
                formData.append("folder_name", invoice.folder_name);
                formData.append("category", invoice.category);
                formData.append("invoice_date", invoice.invoice_date);
                
                // 3. Send the request to the server
                return fetch('/api/invoice/upload', {
                    method: 'POST',
                    body: formData
                    // Authentication Headers (e.g., JWT) would be needed here.
                })
                .then(response => {
                    if (response.ok) {
                        console.log(`Successfully synced invoice ID ${invoice.id}: ${invoice.filename}`);
                        // 4. Delete successfully synced item from the outbox
                        return deleteOutboxItem(invoice.id);
                    } else {
                        // Keep item in outbox for next sync attempt
                        console.error(`Failed to sync invoice ID ${invoice.id}. Status: ${response.status}`);
                        return Promise.resolve(); 
                    }
                })
                .catch(error => {
                    // Keep item in outbox for next sync attempt (e.g., network timeout)
                    console.error(`Network error while syncing invoice ID ${invoice.id}:`, error);
                    return Promise.resolve(); 
                });
            });

            return Promise.all(syncPromises);
        })
        .catch(error => {
            console.error('Error during background sync operation:', error);
            return Promise.reject(error); 
        });
}


// --- FILES TO CACHE ON INSTALL (App Shell) ---
const urlsToCache = [
    '/',
    '/offline',
    '/static/js/common.js',
    '/static/js/calendar.js',
    '/static/js/invoice.js',
    'https://cdn.jsdelivr.net/npm/fullcalendar@6.1.11/main.min.css',
    'https://cdn.jsdelivr.net/npm/fullcalendar@6.1.11/main.min.js',
    'https://cdn.tailwindcss.com',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css'
];

// --- INSTALL EVENT (Caches the App Shell) ---
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(STATIC_CACHE_NAME)
            .then(cache => {
                console.log('Opened static cache and caching app shell');
                return cache.addAll(urlsToCache);
            })
    );
});

// --- ACTIVATE EVENT (Cleans up old caches) ---
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys => {
            return Promise.all(keys
                .filter(key => key !== STATIC_CACHE_NAME && key !== DYNAMIC_CACHE_NAME)
                .map(key => caches.delete(key))
            );
        })
    );
});

// --- FETCH EVENT (Caching Strategies) ---
self.addEventListener('fetch', event => {
    const requestUrl = new URL(event.request.url);

    // Strategy 1: Cache, then Network for API calls (Stale-While-Revalidate pattern)
    if (requestUrl.pathname.startsWith('/api/')) {
        event.respondWith(
            caches.open(DYNAMIC_CACHE_NAME).then(cache => {
                return cache.match(event.request).then(response => {
                    const fetchPromise = fetch(event.request).then(networkResponse => {
                        // Cache the fresh response for next time
                        if (networkResponse.ok) {
                            cache.put(event.request, networkResponse.clone());
                        }
                        return networkResponse;
                    }).catch(error => {
                        // Handle network failure for API calls if no cache is available
                        console.error('API network failure:', error);
                        // The existing `response` (if any) is returned outside this chain
                        throw error;
                    });
                    // Return cached response immediately if available, otherwise wait for network
                    return response || fetchPromise;
                });
            })
        );
        return;
    }

    // Strategy 2: Cache First for static assets and HTML pages
    event.respondWith(
        caches.match(event.request)
            .then(response => {
                if (response) {
                    return response;
                }
                // Fetch from the network and handle failure
                return fetch(event.request).catch(() => {
                    // Fallback to the offline page for navigation requests when network fails
                    if (event.request.mode === 'navigate') {
                        return caches.match('/offline');
                    }
                });
            })
    );
});

// --- SYNC EVENT (Background Data Synchronization) ---
self.addEventListener('sync', event => {
    if (event.tag === 'sync-new-invoices') {
        console.log('Service Worker: Background sync triggered for invoices. 💾');
        // Ensure the Service Worker stays alive until the sync process is complete
        event.waitUntil(syncInvoicesToServer());
    }
});

// --- PUSH EVENT LISTENER (Receiving Push Notifications) ---
self.addEventListener('push', event => {
    console.log('[Service Worker] Push Received.');
    
    let pushData = {
        title: 'DecoOffice',
        body: 'You have a new notification.',
        url: '/'
    };

    if (event.data) {
        try {
            pushData = event.data.json();
        } catch (e) {
            console.error('Error parsing push data:', e);
        }
    }

    const options = {
        body: pushData.body,
        icon: '/static/imgs/icons/dashboard/tempicon.ico', 
        badge: '/static/imgs/icons/dashboard/tempicon.ico', 
        data: {
            url: pushData.url // URL to open when the notification is clicked
        }
    };

    // Show the notification to the user
    event.waitUntil(
        self.registration.showNotification(pushData.title, options)
    );
});

// --- NOTIFICATION CLICK EVENT LISTENER (Handling User Interaction) ---
self.addEventListener('notificationclick', event => {
    console.log('[Service Worker] Notification click Received.');

    event.notification.close(); // Close the notification immediately

    const urlToOpen = event.notification.data.url || '/';
    
    event.waitUntil(
        clients.matchAll({
            type: "window"
        }).then(clientList => {
            // Check if the app's window is already open
            for (const client of clientList) {
                // Focus the existing window if its URL is the target URL or a base URL
                if (client.url.includes(urlToOpen.split('?')[0]) && 'focus' in client) {
                    return client.focus();
                }
            }
            // If the window is not open, open a new one
            if (clients.openWindow) {
                return clients.openWindow(urlToOpen);
            }
        })
    );
});