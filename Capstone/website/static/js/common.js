// static/js/common.js

if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js')
            .then(registration => console.log('ServiceWorker registration successful.'))
            .catch(err => console.log('ServiceWorker registration failed: ', err));
    });
}

function setupCustomDialog() {
    let modal = document.getElementById('custom-dialog-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'custom-dialog-modal';
        modal.className = 'modal-backdrop hidden fixed inset-0 z-[9999] bg-gray-900 bg-opacity-75 flex items-center justify-center p-4';
        modal.innerHTML = `
            <div class="modal-content bg-[#fafaf5] rounded-xl shadow-2xl p-8 w-full max-w-sm text-center relative">
                <div id="custom-dialog-icon-container" class="mb-4"></div>
                <p id="custom-dialog-message" class="text-gray-800 text-lg mb-8 font-semibold"></p>
                <div id="custom-dialog-actions" class="flex justify-center space-x-4">
                    <button id="custom-dialog-cancel" class="px-8 py-3 bg-[#6f8a6e] text-white font-bold rounded-lg">NO</button>
                    <button id="custom-dialog-ok" class="px-8 py-3 bg-[#6f8a6e] text-white font-bold rounded-lg">YES</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }

    const okBtn = document.getElementById('custom-dialog-ok');
    const cancelBtn = document.getElementById('custom-dialog-cancel');
    const messageEl = document.getElementById('custom-dialog-message');
    const iconContainer = document.getElementById('custom-dialog-icon-container');
    const dialogModal = document.getElementById('custom-dialog-modal');

    const hideDialog = () => {
        dialogModal.classList.remove('active');
        dialogModal.addEventListener('transitionend', () => {
            dialogModal.classList.add('hidden');
        }, { once: true });
    };

    window.showCustomConfirm = (message, onConfirm) => {
        messageEl.textContent = message;
        iconContainer.innerHTML = `<i class="fa-solid fa-trash-can text-5xl text-red-500"></i>`;
        
        okBtn.onclick = () => { hideDialog(); onConfirm(); };
        cancelBtn.onclick = hideDialog;

        dialogModal.classList.remove('hidden');
        setTimeout(() => dialogModal.classList.add('active'), 10);
    };
}

// --- PWA Enhancements (Install Prompt & Notifications) ---
let deferredPrompt;
const installButton = document.getElementById('custom-install-button');
const notificationButton = document.getElementById('enable-notifications-btn');

window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    if (installButton) {
        installButton.style.display = 'block';
        installButton.disabled = false;
    }
});

// --- START OF MODIFICATION ---
if (installButton) {
    installButton.addEventListener('click', async () => {
        if (!deferredPrompt) return;
        
        // Disable the button while the prompt is open
        installButton.disabled = true;
        
        // Show the browser's install prompt
        deferredPrompt.prompt();
        
        // Wait for the user to respond to the prompt
        const { outcome } = await deferredPrompt.userChoice;
        
        // Check the outcome
        if (outcome === 'accepted') {
            console.log('User accepted the install prompt');
            // The prompt can't be used again, so clear it
            deferredPrompt = null;
            // Hide the button permanently
            installButton.style.display = 'none';
        } else {
            console.log('User dismissed the install prompt');
            // Re-enable the button so the user can try again
            installButton.disabled = false;
        }
    });
}
// --- END OF MODIFICATION ---

window.addEventListener('appinstalled', () => {
    if (installButton) installButton.style.display = 'none';
    deferredPrompt = null;
    console.log('PWA was installed');
});

async function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}

async function subscribeToPushNotifications() {
    try {
        const sw = await navigator.serviceWorker.ready;
        const vapidPublicKey = document.body.dataset.vapidPublicKey;

        if (!vapidPublicKey) {
            return console.error('VAPID public key not found on body data attribute.');
        }

        const subscription = await sw.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: await urlBase64ToUint8Array(vapidPublicKey)
        });

        await fetch('/api/save-subscription', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': window.getCsrfToken()
            },
            body: JSON.stringify(subscription)
        });
        alert('Successfully subscribed to push notifications!');
    } catch (err) {
        console.error('Failed to subscribe to push notifications:', err);
        alert('Failed to subscribe. Please ensure notifications are not blocked for this site.');
    }
}

function askForNotificationPermission() {
    Notification.requestPermission().then(result => {
        if (result === 'granted') {
            subscribeToPushNotifications();
        } else {
            console.log('User did not grant notification permission.');
        }
    });
}

if (notificationButton) {
    notificationButton.addEventListener('click', askForNotificationPermission);
}


document.addEventListener('DOMContentLoaded', function() {
    setupCustomDialog();

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    window.getCsrfToken = () => csrfToken;

    // --- Auto-hiding logic for flash messages ---
    const flashContainer = document.getElementById('flash-messages-overlay-container');
    if (flashContainer) {
        setTimeout(() => {
            flashContainer.style.opacity = '0';
            flashContainer.addEventListener('transitionend', () => flashContainer.remove());
        }, 5000);
    }

    document.body.addEventListener('click', async (event) => {
        const deleteButton = event.target.closest('.delete-btn');
        if (!deleteButton) return;
    
        const transactionId = deleteButton.dataset.id;
        const transactionName = deleteButton.dataset.name || 'this item';
        
        if (!transactionId) return;

        window.showCustomConfirm(`Are you sure you want to delete ${transactionName}?`, async () => {
            const deleteUrl = `/api/transactions/${transactionId}`;
            const csrfToken = window.getCsrfToken();

            if ('serviceWorker' in navigator && 'SyncManager' in window && !navigator.onLine) {
                try {
                    await window.db.writeData('transaction-outbox', {
                        url: deleteUrl,
                        method: 'DELETE',
                        headers: { 'X-CSRF-Token': csrfToken },
                        timestamp: new Date().toISOString()
                    });

                    const swRegistration = await navigator.serviceWorker.ready;
                    await swRegistration.sync.register('sync-deleted-items');
                    
                    alert("You're offline. This item will be deleted when you reconnect.");
                    const itemElement = deleteButton.closest('.transaction-row, .transaction-item');
                    if(itemElement) itemElement.remove();

                } catch (error) {
                    console.error('Failed to schedule sync for deletion:', error);
                    alert('Could not schedule deletion. Please try again when online.');
                }
            } else {
                try {
                    const response = await fetch(deleteUrl, {
                        method: 'DELETE',
                        headers: { 'X-CSRF-Token': csrfToken }
                    });
                    window.location.reload(); 
                } catch (error) {
                    console.error("Deletion failed:", error);
                    window.location.reload();
                }
            }
        });
    });

    // --- Notification Panel Logic (Integrated) ---
    const notificationBtn = document.getElementById('notification-btn');
    const notificationPanel = document.getElementById('notification-panel');
    const notificationIndicator = document.getElementById('notification-indicator');
    const notificationList = document.getElementById('notification-list');
    const notificationLoader = document.getElementById('notification-loader');

    const checkNotificationStatus = async () => {
        try {
            const response = await fetch('/api/notifications/status');
            if (!response.ok) return;
            const data = await response.json();
            if (data.unread_count > 0) {
                notificationIndicator.classList.remove('hidden');
            } else {
                notificationIndicator.classList.add('hidden');
            }
        } catch (error) {
            console.error('Error checking notification status:', error);
        }
    };

    const createNotificationHTML = (notification) => {
        let iconClass = 'fa-solid fa-info-circle';
        if (notification.title.toLowerCase().includes('transaction')) {
            iconClass = 'fa-solid fa-truck-fast';
        } else if (notification.title.toLowerCase().includes('meeting')) {
            iconClass = 'fa-solid fa-calendar-days';
        }
        
        const unreadIndicator = '<span class="absolute -top-1 -left-1 block h-3 w-3 rounded-full bg-red-500 ring-2 ring-white"></span>';

        return `
            <a href="${notification.url}" class="flex items-start gap-4 p-4 border-b hover:bg-gray-50 transition-colors">
                <div class="relative">
                    <div class="w-10 h-10 flex items-center justify-center bg-gray-100 rounded-full">
                        <i class="${iconClass} text-gray-500"></i>
                    </div>
                    ${unreadIndicator}
                </div>
                <div class="flex-1">
                    <div class="flex justify-between items-center mb-1">
                        <p class="font-bold text-gray-800">${notification.title}</p>
                        <p class="text-xs text-gray-500">${notification.relative_time}</p>
                    </div>
                    <p class="text-sm text-gray-600">${notification.message}</p>
                </div>
            </a>
        `;
    };

    const fetchAndDisplayNotifications = async () => {
        notificationLoader.textContent = 'Loading...';
        notificationLoader.style.display = 'block';
        notificationList.innerHTML = '';

        try {
            const response = await fetch('/api/notifications');
            if (!response.ok) throw new Error('Failed to fetch');
            const notifications = await response.json();
            
            notificationLoader.style.display = 'none';

            if (notifications.length === 0) {
                notificationList.innerHTML = '<p class="text-center text-gray-500 p-8">No new notifications.</p>';
            } else {
                notifications.forEach(n => {
                    notificationList.innerHTML += createNotificationHTML(n);
                });
            }
            
            await fetch('/api/notifications/read', { 
                method: 'POST',
                headers: { 'X-CSRF-Token': window.getCsrfToken() } 
            });
            notificationIndicator.classList.add('hidden');

        } catch (error) {
            console.error('Error fetching notifications:', error);
            notificationLoader.textContent = 'Failed to load notifications.';
        }
    };

    if (notificationBtn && notificationPanel) {
        notificationBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            const isHidden = notificationPanel.classList.toggle('hidden');
            if (!isHidden) {
                fetchAndDisplayNotifications();
            }
        });

        document.addEventListener('click', (e) => {
            if (!notificationPanel.contains(e.target) && !notificationBtn.contains(e.target)) {
                notificationPanel.classList.add('hidden');
            }
        });
    }

    checkNotificationStatus();
});