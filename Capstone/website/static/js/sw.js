// static/js/sw.js

// --- IMPORT LIBRARIES ---
// Import the idb library for easier IndexedDB usage
importScripts('https://cdn.jsdelivr.net/npm/idb@7/build/iife/index-min.js');

// --- CACHE NAMES & IndexedDB CONSTANTS (Using V3 names) ---
const STATIC_CACHE_NAME = 'decooffice-static-v3';    // For app shell, CSS, JS
const DYNAMIC_CACHE_NAME = 'decooffice-dynamic-v3';  // For API calls and dynamic content

// Constants for the original invoice queue (V2 logic)
const INVOICE_DB = 'invoice-queue-db';
const OUTBOX_STORE = 'outbox-invoices';

// Constants for the new transaction queue (V3 logic)
const TRANSACTION_DB_NAME = 'deco-office-db';
const TRANSACTION_DB_VERSION = 1;
const TRANSACTION_OUTBOX_STORE = 'transaction-outbox';

// IndexedDB Helper (Using idb library for V3 transaction sync)
// This promise will be used by the V3 transaction sync logic.
const dbPromise = idb.openDB(TRANSACTION_DB_NAME, TRANSACTION_DB_VERSION, {
    upgrade(db) {
        if (!db.objectStoreNames.contains(TRANSACTION_OUTBOX_STORE)) {
            db.createObjectStore(TRANSACTION_OUTBOX_STORE, { keyPath: 'id', autoIncrement: true });
        }
    }
});


// --- V2 INVOICE IndexedDB Helper Functions (for syncInvoicesToServer) ---

/**
 * Opens and returns the IndexedDB database instance for V2 invoice logic.
 * Note: This uses the older indexedDB API, distinct from the 'idb' library promise above.
 */
function openInvoiceDatabase() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(INVOICE_DB, 1);

        request.onupgradeneeded = event => {
            const db = event.target.result;
            if (!db.objectStoreNames.contains(OUTBOX_STORE)) {
                db.createObjectStore(OUTBOX_STORE, { keyPath: 'id' });
            }
        };

        request.onsuccess = event => {
            resolve(event.target.result);
        };

        request.onerror = event => {
            console.error('IndexedDB error (Invoice DB):', event.target.error);
            reject(event.target.error);
        };
    });
}

/**
 * Retrieves all items from the invoice outbox store.
 */
function getOutboxItems() {
    return openInvoiceDatabase().then(db => {
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
 * Deletes an item from the invoice outbox store after successful sync.
 */
function deleteOutboxItem(id) {
    return openInvoiceDatabase().then(db => {
        return new Promise((resolve, reject) => {
            const transaction = db.transaction([OUTBOX_STORE], 'readwrite');
            const store = transaction.objectStore(OUTBOX_STORE);
            const request = store.delete(id);

            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
        });
    });
}


// --- Background Sync Implementation (Invoice V2) ---

/**
 * Attempts to sync all queued invoices from IndexedDB to the server.
 */
function syncInvoicesToServer() {
    return getOutboxItems()
        .then(invoices => {
            if (invoices.length === 0) {
                console.log('No queued invoices to sync.');
                return Promise.resolve();
            }

            console.log(`Attempting to sync ${invoices.length} invoices...`);

            const syncPromises = invoices.map(invoice => {
                const formData = new FormData();
                // We create a dummy file blob because we didn't store the actual file in this version.
                // In a real app, you would store the blob in IndexedDB and retrieve it here.
                const dummyFileBlob = new Blob(["Invoice Content"], { type: invoice.fileMimeType || 'application/pdf' });
                
                formData.append("invoice_file", dummyFileBlob, invoice.filename);
                formData.append("folder_name", invoice.folder_name);
                formData.append("category", invoice.category);
                formData.append("invoice_date", invoice.invoice_date);
                
                return fetch('/api/invoice/upload', {
                    method: 'POST',
                    body: formData
                })
                .then(response => {
                    if (response.ok) {
                        console.log(`Successfully synced invoice ID ${invoice.id}: ${invoice.filename}`);
                        return deleteOutboxItem(invoice.id);
                    } else {
                        console.error(`Failed to sync invoice ID ${invoice.id}. Status: ${response.status}`);
                        return Promise.resolve(); // Keep in outbox if server returns an error
                    }
                })
                .catch(error => {
                    console.error(`Network error while syncing invoice ID ${invoice.id}:`, error);
                    return Promise.resolve(); // Keep in outbox on network failure
                });
            });

            return Promise.all(syncPromises);
        })
        .catch(error => {
            console.error('Error during invoice background sync operation:', error);
            return Promise.reject(error); // Reject to let the sync manager know it failed
        });
}


// --- Background Sync Implementation (Transaction V3) ---

function syncNewTransactions() {
    console.log('Service Worker: Starting transaction sync...');
    return dbPromise.then(db => {
        const tx = db.transaction(TRANSACTION_OUTBOX_STORE, 'readonly');
        return tx.store.getAll();
    }).then(outboxItems => {
        if (outboxItems.length === 0) {
            console.log('No queued transactions to sync.');
            return Promise.resolve();
        }

        const syncPromises = outboxItems.map(item => {
            return fetch('/api/transactions/add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(item)
            })
            .then(response => {
                if (response.ok) {
                    console.log(`Successfully synced outbox item ID: ${item.id}`);
                    // Delete the item from the outbox after successful sync
                    return dbPromise.then(db => {
                        const deleteTx = db.transaction(TRANSACTION_OUTBOX_STORE, 'readwrite');
                        return deleteTx.store.delete(item.id);
                    });
                } else {
                    console.error(`Failed to sync transaction ID ${item.id}. Status: ${response.status}`);
                    return Promise.resolve(); // Keep in outbox if server returns a bad status
                }
            })
            .catch(err => {
                console.error(`Network failure while syncing transaction ID ${item.id}:`, err);
                return Promise.resolve(); // Keep in outbox if network fails
            });
        });
        return Promise.all(syncPromises);
    })
    .catch(error => {
        console.error('Error during transaction background sync operation:', error);
        return Promise.reject(error); 
    });
}


// --- FILES TO CACHE ON INSTALL (App Shell) ---
const urlsToCache = [
    '/',
    '/offline',
    'https://cdn.jsdelivr.net/npm/idb@7/build/iife/index-min.js', // Cache the idb library
    '/static/js/common.js',
    '/static/js/db.js',
    '/static/js/transactions.js',
    '/static/js/add_transaction.js',
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
    // Strategy: Stale-While-Revalidate for API calls
    if (event.request.url.includes('/api/')) {
        // Skip caching for POST/PUT/DELETE requests (like /api/invoice/upload or /api/transactions/add)
        if (event.request.method !== 'GET') {
            return; 
        }

        event.respondWith(
            caches.open(DYNAMIC_CACHE_NAME).then(cache => {
                // Try network first, then cache
                return fetch(event.request)
                    .then(networkResponse => {
                        // Only cache successful GET responses
                        if (networkResponse.ok) {
                           cache.put(event.request, networkResponse.clone());
                        }
                        return networkResponse;
                    })
                    .catch(() => cache.match(event.request)); // Fallback to cache on network failure
            })
        );
        return;
    }

    // Strategy: Cache First for all other requests (App Shell, HTML pages, etc.)
    event.respondWith(
        caches.match(event.request)
            .then(response => {
                // Return cached response if found, otherwise fetch from network
                return response || fetch(event.request).catch(() => {
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
        event.waitUntil(syncInvoicesToServer());
    }
    
    if (event.tag === 'sync-new-transactions') {
        console.log('Service Worker: Background sync triggered for transactions. 💾');
        event.waitUntil(syncNewTransactions());
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