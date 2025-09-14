// static/js/common.js

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
    
    // --- Notification Panel Logic ---
    const notificationBtn = document.getElementById('notification-btn');
    const notificationPanel = document.getElementById('notification-panel');
    if (notificationBtn && notificationPanel) {
        notificationBtn.addEventListener('click', (event) => {
            event.stopPropagation();
            notificationPanel.classList.toggle('hidden');
        });
        document.addEventListener('click', (event) => {
            if (!notificationPanel.contains(event.target) && !notificationBtn.contains(event.target) && !notificationPanel.classList.contains('hidden')) {
                notificationPanel.classList.add('hidden');
            }
        });
    }

    // --- Flash Message Auto-Fade Logic ---
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

    // --- Transaction Deletion Logic ---
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

    // --- Transaction Details Modal Logic ---
    const transactionTableForModal = document.querySelector('.transaction-table');
    const modal = document.getElementById('transaction-details-modal');

    if (transactionTableForModal && modal) {
        const closeModalBtn = document.getElementById('close-modal-btn');
        const statusBox = document.getElementById('modal-status-box');
        const statusIcon = document.getElementById('modal-status-icon');
        const statusText = document.getElementById('modal-status-text');
        const amountHeader = document.getElementById('modal-amount-header');
        const recipient = document.getElementById('modal-recipient');
        const deliveryDate = document.getElementById('modal-delivery-date');
        const checkDate = document.getElementById('modal-check-date');
        const paymentMethod = document.getElementById('modal-payment-method');
        const amountSent = document.getElementById('modal-amount-sent');
        const notes = document.getElementById('modal-notes');

        const openModal = async (transactionId) => {
            try {
                const response = await fetch(`/api/transaction/${transactionId}`);
                if (!response.ok) throw new Error('Transaction not found.');
                
                const data = await response.json();
                const formattedAmount = `₱ ${parseFloat(data.amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

                // Populate modal
                recipient.textContent = data.name;
                deliveryDate.textContent = data.id; 
                checkDate.textContent = data.delivery_date; 
                paymentMethod.textContent = data.method;
                amountHeader.textContent = formattedAmount;
                amountSent.textContent = formattedAmount;
                notes.textContent = data.notes;

                // Update status display
                statusText.textContent = data.status;
                statusBox.className = 'flex justify-between items-center border rounded-lg px-4 py-3 mb-4';
                statusIcon.className = 'fas';
                if (data.status === 'Paid') {
                    statusBox.classList.add('border-green-400', 'text-green-700');
                    statusIcon.classList.add('fa-check-circle');
                } else if (data.status === 'Pending') {
                    statusBox.classList.add('border-yellow-400', 'text-yellow-700');
                    statusIcon.classList.add('fa-clock');
                } else { // Declined
                    statusBox.classList.add('border-red-400', 'text-red-700');
                    statusIcon.classList.add('fa-times-circle');
                }
                
                modal.classList.remove('hidden');

            } catch (error) {
                console.error("Failed to fetch transaction details:", error);
                alert("Could not load transaction details. Please try again.");
            }
        };

        const closeModal = () => {
            modal.classList.add('hidden');
        };

        transactionTableForModal.addEventListener('click', (event) => {
            const link = event.target.closest('.view-details-link');
            if (link) {
                openModal(link.dataset.id);
            }
        });

        closeModalBtn.addEventListener('click', closeModal);
        modal.addEventListener('click', (event) => {
            if (event.target === modal) {
                closeModal();
            }
        });
    }
    
    // --- Schedule Form Submission (if exists) ---
    // ... (schedule logic remains unchanged) ...
});
// --- PWA Service Worker Registration ---
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js')
      .then(registration => console.log('ServiceWorker registration successful.'))
      .catch(err => console.log('ServiceWorker registration failed: ', err));
  });
}