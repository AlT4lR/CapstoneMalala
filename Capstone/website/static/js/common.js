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

if (installButton) {
    installButton.addEventListener('click', async () => {
        if (!deferredPrompt) return;
        
        installButton.disabled = true;
        deferredPrompt.prompt();
        const { outcome } = await deferredPrompt.userChoice;
        
        if (outcome === 'accepted') {
            deferredPrompt = null;
            installButton.style.display = 'none';
        } else {
            installButton.disabled = false;
        }
    });
}

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
                // ... (offline logic remains the same)
            } else {
                try {
                    await fetch(deleteUrl, {
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

    // --- REVISED NOTIFICATION PANEL LOGIC ---
    const notificationBtns = document.querySelectorAll('.notification-btn');
    const notificationPanel = document.getElementById('notification-panel');
    const notificationList = document.getElementById('notification-list');
    const notificationLoader = document.getElementById('notification-loader');
    
    // State management
    let currentPage = 1;
    let isLoading = false;
    let hasMoreNotifications = true;
    const NOTIFICATIONS_PER_PAGE = 25;

    const checkNotificationStatus = async () => {
        // --- START OF FIX: Use querySelectorAll to find ALL indicators ---
        const notificationIndicators = document.querySelectorAll('.notification-indicator');
        if (notificationIndicators.length === 0) return;
        // --- END OF FIX ---

        try {
            const response = await fetch('/api/notifications/status');
            if (!response.ok) return;
            const data = await response.json();

            // --- START OF FIX: Loop through each indicator and update it ---
            notificationIndicators.forEach(indicator => {
                if (data.unread_count > 0) {
                    indicator.classList.remove('hidden');
                } else {
                    indicator.classList.add('hidden');
                }
            });
            // --- END OF FIX ---
        } catch (error) {
            console.error('Error checking notification status:', error);
        }
    };

    const createNotificationHTML = (notification) => {
        let iconClass = 'fa-solid fa-info-circle';
        if (notification.title.toLowerCase().includes('transaction')) {
            iconClass = 'fa-solid fa-truck-fast';
        } else if (notification.title.toLowerCase().includes('event')) {
            iconClass = 'fa-solid fa-calendar-days';
        }
        
        const unreadIndicator = !notification.isRead ? '<span class="unread-dot absolute -top-1 -left-1 block h-3 w-3 rounded-full bg-red-500 ring-2 ring-white"></span>' : '';

        return `
            <a href="${notification.url}" class="notification-item flex items-start gap-4 p-4 border-b hover:bg-gray-50 transition-colors" data-notification-id="${notification.id}">
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

    const fetchAndDisplayNotifications = async (page = 1) => {
        if (isLoading || !hasMoreNotifications) return;
        isLoading = true;
        if (notificationLoader) notificationLoader.style.display = 'block';

        try {
            const response = await fetch(`/api/notifications?page=${page}&limit=${NOTIFICATIONS_PER_PAGE}`);
            if (!response.ok) throw new Error('Failed to fetch');
            const notifications = await response.json();
            
            if (page === 1) {
                notificationList.innerHTML = ''; // Clear only on the first page load
            }
            
            if (notifications.length === 0 && page === 1) {
                notificationList.innerHTML = '<p class="text-center text-gray-500 p-8">No notifications found.</p>';
            } else {
                notifications.forEach(n => {
                    notificationList.insertAdjacentHTML('beforeend', createNotificationHTML(n));
                });
            }

            if (notifications.length < NOTIFICATIONS_PER_PAGE) {
                hasMoreNotifications = false;
            } else {
                currentPage++;
            }

        } catch (error) {
            console.error('Error fetching notifications:', error);
            const errorMsg = '<p class="text-center text-red-500 p-8">Failed to load notifications.</p>';
            if (page === 1) notificationList.innerHTML = errorMsg;
        } finally {
            isLoading = false;
            if (notificationLoader) notificationLoader.style.display = 'none';
        }
    };

    if (notificationBtns.length > 0 && notificationPanel) {
        notificationBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const isHidden = notificationPanel.classList.toggle('hidden');
                // Always reset and fetch when opening the panel for fresh data
                if (!isHidden) {
                    currentPage = 1;
                    hasMoreNotifications = true;
                    fetchAndDisplayNotifications(currentPage);
                }
            });
        });

        // Close panel when clicking outside
        document.addEventListener('click', (e) => {
            let clickedOnButton = Array.from(notificationBtns).some(btn => btn.contains(e.target));
            if (!notificationPanel.contains(e.target) && !clickedOnButton) {
                notificationPanel.classList.add('hidden');
            }
        });

        // Infinite scroll listener
        notificationList.addEventListener('scroll', () => {
            const { scrollTop, scrollHeight, clientHeight } = notificationList;
            if (scrollTop + clientHeight >= scrollHeight - 100) { // 100px threshold
                fetchAndDisplayNotifications(currentPage);
            }
        });

        // Event delegation for marking as read
        notificationList.addEventListener('click', async function(event) {
            const notificationItem = event.target.closest('.notification-item');
            if (!notificationItem) return;
            
            event.preventDefault();
            
            const notificationId = notificationItem.dataset.notificationId;
            const unreadDot = notificationItem.querySelector('.unread-dot');

            if (unreadDot) {
                unreadDot.remove();
                try {
                    await fetch(`/api/notifications/read/${notificationId}`, {
                        method: 'POST',
                        headers: { 'X-CSRF-Token': window.getCsrfToken() }
                    });
                    checkNotificationStatus();
                } catch (error) {
                    console.error('Failed to mark notification as read:', error);
                }
            }
            window.location.href = notificationItem.href;
        });
    }

    checkNotificationStatus();
});