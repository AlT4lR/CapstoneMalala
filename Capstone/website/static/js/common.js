// static/js/common.js

// --- PWA Service Worker Registration ---
// Must be outside DOMContentLoaded to ensure it runs as early as possible
if ('serviceWorker' in navigator) {
	window.addEventListener('load', () => {
		navigator.serviceWorker.register('/sw.js')
			.then(registration => console.log('ServiceWorker registration successful.'))
			.catch(err => console.log('ServiceWorker registration failed: ', err));
	});
}

document.addEventListener('DOMContentLoaded', function() {

	// --- CSRF Token Handling ---
	let csrfToken = null;
	const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
	if (csrfTokenMeta) {
		csrfToken = csrfTokenMeta.getAttribute('content');
	} else {
		const csrfCookie = document.cookie.split('; ').find(row => row.startsWith('csrf_access_token='));
		if (csrfCookie) {
			csrfToken = csrfCookie.split('=')[1];
		}
	}
	if (!csrfToken) console.warn("CSRF token not found.");
	window.getCsrfToken = () => csrfToken;

	// ----------------------------------------------------------------------
	// --- PWA & Notification Logic ---
	// ----------------------------------------------------------------------

	const PWA = {
		init: function() {
			this.handleNotifications();
			if ('serviceWorker' in navigator && 'PushManager' in window) {
				// Initialize Push Notifications (Assuming a button with id="enable-push-btn" exists, e.g., on a settings page)
				this.initPushNotifications(); 
			}
		},

		// --- In-App Bell Notifications ---
		handleNotifications: function() {
			const notificationBtn = document.getElementById('notification-btn');
			const notificationPanel = document.getElementById('notification-panel');
			const notificationList = document.getElementById('notification-list'); 
			// Red dot is the small indicator span inside the button
			const redDot = notificationBtn ? notificationBtn.querySelector('span') : null;

			if (!notificationBtn || !notificationPanel) return;

			// Function to fetch and render notifications
			const fetchNotifications = () => {
				fetch('/api/notifications')
					.then(res => res.json())
					.then(notifications => {
						// Only proceed if we have a list to render into
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
						if (notificationList) notificationList.innerHTML = `<p class="text-sm text-red-500 p-4 text-center">Could not load notifications.</p>`;
					});
			};
			
			// Fetch initial notifications on load
			fetchNotifications();

			// Event listener to toggle panel and mark as read
			notificationBtn.addEventListener('click', (event) => {
				event.stopPropagation();
				notificationPanel.classList.toggle('hidden');

				// Mark as read only if panel is opened and red dot is visible
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

			// Hide panel on outside click (consolidating previous redundant logic)
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

			// Check and update button state on load
			navigator.serviceWorker.ready.then(swReg => {
				swReg.pushManager.getSubscription().then(subscription => {
					if (subscription) {
						pushButton.textContent = 'Disable Push Notifications';
					} else {
						pushButton.textContent = 'Enable Push Notifications';
					}
				});
			});

			// Toggle subscribe/unsubscribe on button click
			pushButton.addEventListener('click', () => {
				navigator.serviceWorker.ready.then(swReg => {
					swReg.pushManager.getSubscription().then(subscription => {
						if (subscription) {
							// Implement unsubscribe logic here (server-side API call needed)
							alert('Unsubscribe logic needs to be implemented on the server.');
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
				alert('Push notification setup is incomplete. Contact support.');
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
					alert('Successfully subscribed to push notifications!');
					const pushButton = document.getElementById('enable-push-btn');
					if(pushButton) pushButton.textContent = 'Disable Push Notifications';
				} else {
					throw new Error('Failed to save subscription on server.');
				}
			} catch (err) {
				console.error('Failed to subscribe the user: ', err);
				alert('Failed to subscribe. Please ensure you have granted notification permissions in your browser.');
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
				// Only track transition end for the last message
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

			if (confirm('Are you sure you want to delete this transaction? This action cannot be undone.')) {
				try {
					const response = await fetch(`/api/transactions/${transactionId}`, {
						method: 'DELETE',
						headers: { 'X-CSRF-Token': window.getCsrfToken() }
					});
					const result = await response.json();
					if (response.ok) {
						// Remove row from UI
						deleteButton.closest('.transaction-row').remove();
						alert('Transaction deleted successfully.'); 
					} else {
						alert('Error: ' + (result.error || 'Could not delete transaction.'));
					}
				} catch (error) {
					console.error('Failed to delete transaction:', error);
					alert('An error occurred. Please try again.');
				}
			}
		});
	}

	// ----------------------------------------------------------------------
	// --- Transaction Details Modal Logic ---
	// ----------------------------------------------------------------------
	const modal = document.getElementById("transaction-details-modal");
	if (modal) {
		const closeBtn = document.getElementById("close-modal-btn");

		// Use event delegation on the document to handle clicks on any .view-details-link
		document.addEventListener("click", async (event) => {
			const link = event.target.closest(".view-details-link");
			if (!link) return;

			const id = link.getAttribute("data-id");
			try {
				const res = await fetch(`/api/transaction/${id}`);
				if (!res.ok) throw new Error("Failed to fetch details");
				const data = await res.json();

				// Populate modal fields
				document.getElementById("modal-status-text").textContent = `A payment was sent to ${data.name}`;
				// Note: Assumes `data` includes fields like `name`, `amount`, `delivery_date_full`, etc.
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
				alert("Could not load transaction details.");
			}
		});

		// Close modal logic
		closeBtn.addEventListener("click", () => {
			modal.classList.add("hidden");
		});
		modal.addEventListener("click", (e) => {
			if (e.target === modal) modal.classList.add("hidden");
		});
	}
	
	// --- Schedule Form Submission (if exists) ---
	// ... (schedule logic remains unchanged) ...
});