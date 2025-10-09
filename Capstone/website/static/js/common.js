// --- PWA Service Worker Registration ---
// Must be outside DOMContentLoaded to ensure it runs as early as possible
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js')
            .then(registration => console.log('ServiceWorker registration successful.'))
            .catch(err => console.log('ServiceWorker registration failed: ', err));
    });
}

// ----------------------------------------------------------------------
// --- Custom Dialog (Alert/Confirm) Implementation ---
// Replaces all native alert() and confirm() calls with a non-blocking modal.
// This modal is dynamically created and appended to the body.
// ----------------------------------------------------------------------
function setupCustomDialog() {
    // Inject the modal structure into the body if it doesn't exist
    let modal = document.getElementById('custom-dialog-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'custom-dialog-modal';
        // Tailwind classes for fixed, full-screen overlay, centered content, and hidden state
        modal.className = 'hidden fixed inset-0 z-[9999] bg-gray-900 bg-opacity-75 flex items-center justify-center p-4 transition-opacity duration-300';
        modal.innerHTML = `
            <div class="bg-white rounded-xl shadow-2xl p-6 w-full max-w-sm transform transition-all scale-100">
                <p id="custom-dialog-message" class="text-gray-800 text-center mb-6 font-semibold"></p>
                <div id="custom-dialog-actions" class="flex justify-center space-x-4">
                    <button id="custom-dialog-ok" class="px-6 py-2 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition duration-150 shadow-md">OK</button>
                    <button id="custom-dialog-cancel" class="px-6 py-2 bg-gray-300 text-gray-800 font-medium rounded-lg hover:bg-gray-400 transition duration-150 shadow-md">Cancel</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }

    const messageEl = document.getElementById('custom-dialog-message');
    const okBtn = document.getElementById('custom-dialog-ok');
    const cancelBtn = document.getElementById('custom-dialog-cancel');
    const dialogModal = document.getElementById('custom-dialog-modal');

    // Hides the modal and cleans up event listeners
    const hideDialog = () => {
        dialogModal.classList.add('hidden');
        okBtn.onclick = null;
        cancelBtn.onclick = null;
    };

    /**
     * Shows a confirmation dialog (replaces window.confirm).
     */
    window.showCustomConfirm = (message, onConfirm, onCancel = () => {}) => {
        messageEl.textContent = message;
        cancelBtn.classList.remove('hidden');

        okBtn.onclick = () => {
            hideDialog();
            onConfirm();
        };

        cancelBtn.onclick = () => {
            hideDialog();
            onCancel();
        };

        dialogModal.classList.remove('hidden');
    };

    /**
     * Shows a simple alert dialog (replaces window.alert).
     */
    window.showCustomAlert = (message) => {
        messageEl.textContent = message;
        cancelBtn.classList.add('hidden');

        okBtn.onclick = hideDialog;

        dialogModal.classList.remove('hidden');
    };
}
// ----------------------------------------------------------------------


document.addEventListener('DOMContentLoaded', function() {
    // Setup the custom dialog functionality immediately
    setupCustomDialog();

    // --- Global CSRF Token Handling ---
    const getCsrfToken = () => {
        const csrfMeta = document.querySelector('meta[name="csrf-token"]');
        if (csrfMeta) {
            return csrfMeta.getAttribute('content');
        }
        console.warn('CSRF token meta tag not found.');
        return '';
    };
    window.getCsrfToken = getCsrfToken;

    // ----------------------------------------------------------------------
    // --- PWA & Notification Logic ---
    // ----------------------------------------------------------------------

    const PWA = {
        init: function() {
            this.handleNotifications();
            if ('serviceWorker' in navigator && 'PushManager' in window) {
                this.initPushNotifications();
            }
        },

        // --- In-App Bell Notifications ---
        handleNotifications: function() {
            const notificationBtn = document.getElementById('notification-btn');
            const notificationPanel = document.getElementById('notification-panel');
            const notificationList = document.getElementById('notification-list');
            const redDot = notificationBtn ? notificationBtn.querySelector('span') : null;

            if (!notificationBtn || !notificationPanel) return;

            // Function to fetch and render notifications
            const fetchNotifications = () => {
                fetch('/api/notifications')
                    .then(res => res.json())
                    .then(notifications => {
                        if (!notificationList) return;

                        if (notifications && notifications.length > 0) {
                            if (redDot) redDot.classList.remove('hidden');
                            notificationList.innerHTML = notifications.map(n => `
                                <a href="${n.url || '#'}" class="block p-3 rounded-lg hover:bg-gray-200 transition-colors">
                                    <p class="font-semibold text-sm text-custom-text-dark">${n.title || 'Notification'}</p>
                                    <p class="text-sm text-gray-600">${n.message}</p>
                                    <p class="text-xs text-gray-400 mt-1">${new Date(n.createdAt).toLocaleString()}</p>
                                </a>
                            `).join('');
                        } else {
                            if (redDot) redDot.classList.add('hidden');
                            notificationList.innerHTML = `<p class="text-sm text-gray-500 p-4 text-center">You have no new notifications.</p>`;
                        }
                    }).catch(err => {
                        console.error("Failed to fetch notifications:", err);
                        if (notificationList) {
                            notificationList.innerHTML = `<p class="text-sm text-red-500 p-4 text-center">Could not load notifications.</p>`;
                        }
                    // --- THIS IS THE FIX ---
                    // The incorrect closing parenthesis and semicolon have been removed.
                    });
            };

            // Fetch initial notifications on load
            fetchNotifications();

            // Event listener to toggle panel and mark as read
            notificationBtn.addEventListener('click', (event) => {
                event.stopPropagation();
                notificationPanel.classList.toggle('hidden');

                if (!notificationPanel.classList.contains('hidden') && (redDot && !redDot.classList.contains('hidden'))) {
                    fetch('/api/notifications/mark-read', {
                        method: 'POST',
                        headers: { 'X-CSRF-Token': window.getCsrfToken() }
                    }).then(res => {
                        if (res.ok) {
                            if (redDot) redDot.classList.add('hidden');
                        }
                    }).catch(err => {
                        console.error("Failed to mark notifications as read:", err);
                    });
                }
            });

            // Hide panel on outside click
            document.addEventListener('click', (event) => {
                if (!notificationPanel.contains(event.target) && !notificationBtn.contains(event.target) && !notificationPanel.classList.contains('hidden')) {
                    notificationPanel.classList.add('hidden');
                }
            });
        },

        // --- PWA Push Notifications ---
        initPushNotifications: function() {
            const pushButton = document.getElementById('enable-push-btn');
            if (!pushButton) return;

            navigator.serviceWorker.ready.then(swReg => {
                swReg.pushManager.getSubscription().then(subscription => {
                    if (subscription) {
                        pushButton.textContent = 'Disable Push Notifications';
                    } else {
                        pushButton.textContent = 'Enable Push Notifications';
                    }
                });
            });

            pushButton.addEventListener('click', () => {
                navigator.serviceWorker.ready.then(swReg => {
                    swReg.pushManager.getSubscription().then(subscription => {
                        if (subscription) {
                            window.showCustomAlert('Unsubscribe logic needs to be implemented on the server.');
                        } else {
                            this.subscribeUser(swReg);
                        }
                    });
                });
            });
        },

        subscribeUser: async function(swReg) {
            const vapidPublicKey = document.body.dataset.vapidPublicKey;
            if (!vapidPublicKey) {
                console.error('VAPID public key not found on body data attribute.');
                window.showCustomAlert('Push notification setup is incomplete. Contact support.');
                return;
            }

            try {
                const subscription = await swReg.pushManager.subscribe({
                    userVisibleOnly: true,
                    applicationServerKey: this.urlBase64ToUint8Array(vapidPublicKey)
                });

                const response = await fetch('/api/push/subscribe', {
                    method: 'POST',
                    body: JSON.stringify(subscription),
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRF-Token': window.getCsrfToken()
                    }
                });

                if (response.ok) {
                    window.showCustomAlert('Successfully subscribed to push notifications!');
                    const pushButton = document.getElementById('enable-push-btn');
                    if(pushButton) pushButton.textContent = 'Disable Push Notifications';
                } else {
                    throw new Error('Failed to save subscription on server.');
                }
            } catch (err) {
                console.error('Failed to subscribe the user: ', err);
                window.showCustomAlert('Failed to subscribe. Please ensure you have granted notification permissions in your browser.');
            }
        },

        // Helper function for VAPID key conversion
        urlBase64ToUint8Array: function(base64String) {
            const padding = '='.repeat((4 - base64String.length % 4) % 4);
            const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
            const rawData = window.atob(base64);
            const outputArray = new Uint8Array(rawData.length);
            for (let i = 0; i < rawData.length; ++i) {
                outputArray[i] = rawData.charCodeAt(i);
            }
            return outputArray;
        }
    };

    // Initialize the PWA/Notification features
    PWA.init();

    // ----------------------------------------------------------------------
    // --- Flash Message Auto-Fade Logic ---
    // ----------------------------------------------------------------------
    const flashMessagesContainer = document.getElementById('flash-messages-overlay-container');
    if (flashMessagesContainer) {
        setTimeout(() => {
            const messages = flashMessagesContainer.querySelectorAll('.flash-message-local');
            messages.forEach(msg => msg.classList.add('fade-out'));
            if (messages.length > 0) {
                messages[messages.length - 1].addEventListener('transitionend', () => {
                    flashMessagesContainer.remove();
                }, { once: true });
            }
        }, 5000);
    }

    // ----------------------------------------------------------------------
    // --- Transaction Deletion Logic ---
    // ----------------------------------------------------------------------
    const transactionTableForDelete = document.querySelector('.transaction-table');
    if (transactionTableForDelete) {
        transactionTableForDelete.addEventListener('click', async (event) => {
            const deleteButton = event.target.closest('.delete-btn');
            if (!deleteButton) return;

            const transactionId = deleteButton.dataset.id;
            if (!transactionId) return;

            window.showCustomConfirm('Are you sure you want to delete this transaction? This action cannot be undone.', async () => {
                try {
                    const response = await fetch(`/api/transactions/${transactionId}`, {
                        method: 'DELETE',
                        headers: { 'X-CSRF-Token': window.getCsrfToken() }
                    });
                    const result = await response.json();
                    if (response.ok) {
                        deleteButton.closest('.transaction-row').remove();
                        window.showCustomAlert('Transaction deleted successfully.');
                    } else {
                        window.showCustomAlert('Error: ' + (result.error || 'Could not delete transaction.'));
                    }
                } catch (error) {
                    console.error('Failed to delete transaction:', error);
                    window.showCustomAlert('An error occurred. Please try again.');
                }
            });
        });
    }

    // ----------------------------------------------------------------------
    // --- Transaction Details Modal Logic ---
    // ----------------------------------------------------------------------
    const modal = document.getElementById("transaction-details-modal");
    if (modal) {
        const closeBtn = document.getElementById("close-modal-btn");

        document.addEventListener("click", async (event) => {
            const link = event.target.closest(".view-details-link");
            if (!link) return;

            const id = link.getAttribute("data-id");
            try {
                const res = await fetch(`/api/transaction/${id}`);
                if (!res.ok) throw new Error("Failed to fetch details");
                const data = await res.json();

                document.getElementById("modal-status-text").textContent = `A payment was sent to ${data.name}`;
                document.getElementById("modal-amount-header").textContent = `₱ ${parseFloat(data.amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
                document.getElementById("modal-recipient").textContent = data.name;
                document.getElementById("modal-delivery-date").textContent = data.delivery_date_full;
                document.getElementById("modal-check-date").textContent = data.check_date_only;
                document.getElementById("modal-payment-method").textContent = data.method;
                document.getElementById("modal-amount-sent").textContent = `₱ ${parseFloat(data.amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
                document.getElementById("modal-notes").textContent = data.notes;

                modal.classList.remove("hidden");
            } catch (err) {
                console.error(err);
                window.showCustomAlert("Could not load transaction details.");
            }
        });

        closeBtn.addEventListener("click", () => {
            modal.classList.add("hidden");
        });
        modal.addEventListener("click", (e) => {
            if (e.target === modal) modal.classList.add("hidden");
        });
    }

});