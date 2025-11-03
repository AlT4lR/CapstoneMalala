// website/static/js/common.js

// --- PWA Service Worker Registration ---
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js')
            .then(registration => console.log('ServiceWorker registration successful.'))
            .catch(err => console.log('ServiceWorker registration failed: ', err));
    });
}

// --- Universal Modal Opening/Closing Functions ---
function openModal(modal) {
    if (!modal) return;
    modal.classList.remove('hidden');
    setTimeout(() => modal.classList.add('active'), 10);
}

function closeModal(modal) {
    if (!modal) return;
    modal.classList.remove('active');
    modal.addEventListener('transitionend', () => modal.classList.add('hidden'), { once: true });
}

// --- Universal Custom Confirmation Dialog ---
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
    const hideDialog = () => closeModal(dialogModal);
    window.showCustomConfirm = (message, onConfirm) => {
        messageEl.textContent = message;
        iconContainer.innerHTML = `<i class="fa-solid fa-trash-can text-5xl text-red-500"></i>`;
        okBtn.onclick = () => { hideDialog(); onConfirm(); };
        cancelBtn.onclick = hideDialog;
        openModal(dialogModal);
    };
}


document.addEventListener('DOMContentLoaded', function() {
    setupCustomDialog();
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    window.getCsrfToken = () => csrfToken;

    // --- Flash Message Auto-Hide ---
    const flashContainer = document.getElementById('flash-messages-overlay-container');
    if (flashContainer) {
        setTimeout(() => {
            flashContainer.style.opacity = '0';
            flashContainer.addEventListener('transitionend', () => flashContainer.remove());
        }, 5000);
    }

    // --- START OF NEW MODIFICATION: Centralized Event Listener ---
    document.body.addEventListener('click', async (event) => {
        const deleteButton = event.target.closest('.delete-btn');
        const editButton = event.target.closest('.edit-btn');
        const closeModalButton = event.target.closest('.close-modal-btn');

        // --- Global Delete Button Handler ---
        if (deleteButton) {
            const transactionId = deleteButton.dataset.id;
            const transactionName = deleteButton.dataset.name || 'this item';
            if (!transactionId) return;

            window.showCustomConfirm(`Are you sure you want to archive "${transactionName}"?`, async () => {
                try {
                    const response = await fetch(`/api/transactions/${transactionId}`, {
                        method: 'DELETE',
                        headers: { 'X-CSRF-Token': window.getCsrfToken() }
                    });
                    if (response.ok) {
                        window.location.reload();
                    } else {
                        alert('Failed to archive the item.');
                    }
                } catch (error) {
                    console.error("Deletion failed:", error);
                    alert('An error occurred during deletion.');
                }
            });
        }

        // --- Global Edit Button Handler ---
        if (editButton) {
            const transactionId = editButton.dataset.id;
            const modalTargetSelector = editButton.dataset.modalTarget;
            const modalElement = document.querySelector(modalTargetSelector);

            if (!transactionId || !modalElement) {
                console.error('Edit button is missing data-id or data-modal-target');
                return;
            }

            try {
                const response = await fetch(`/api/transactions/details/${transactionId}`);
                if (response.status === 401) {
                    alert('Your session has expired. Please log in again.');
                    window.location.href = "/auth/login";
                    return;
                }
                if (response.status === 404) {
                    alert('Item not found. It may have been deleted. Please refresh the page.');
                    return;
                }
                if (!response.ok) throw new Error(`Server error: ${response.status}`);
                
                const data = await response.json();

                // Populate common modal fields
                modalElement.querySelector('input[name="transaction_id"]').value = transactionId;
                if(modalElement.querySelector('input[name="name"]')) modalElement.querySelector('input[name="name"]').value = data.name || '';
                if(modalElement.querySelector('input[name="name_of_issued_check"]')) modalElement.querySelector('input[name="name_of_issued_check"]').value = data.name || '';
                if(modalElement.querySelector('input[name="check_no"]')) modalElement.querySelector('input[name="check_no"]').value = data.check_no || '';
                if(modalElement.querySelector('input[name="check_date"]')) flatpickr(modalElement.querySelector('input[name="check_date"]')).setDate(data.check_date);
                if(modalElement.querySelector('input[name="due_date"]')) flatpickr(modalElement.querySelector('input[name="due_date"]')).setDate(data.due_date);
                if(modalElement.querySelector('input[name="amount"]')) modalElement.querySelector('input[name="amount"]').value = data.amount || '0.00';
                if(modalElement.querySelector('input[name="check_amount"]')) modalElement.querySelector('input[name="check_amount"]').value = data.check_amount || '0.00';
                if(modalElement.querySelector('textarea[name="notes"]')) modalElement.querySelector('textarea[name="notes"]').value = data.notes || '';
                
                // --- START OF CHANGE: Handle EWT and other deductions separately ---
                if (modalElement.id === 'edit-check-modal') {
                    // Manually set the countered_check value
                    if(modalElement.querySelector('input[name="countered_check"]')) {
                        modalElement.querySelector('input[name="countered_check"]').value = data.countered_check || '0.00';
                    }

                    // Set the dedicated EWT field
                    if(modalElement.querySelector('input[name="ewt"]')) {
                        modalElement.querySelector('input[name="ewt"]').value = data.ewt || '0.00';
                    }
                    
                    const populateFuncName = 'populateDeductions_' + modalElement.id.replace(/-/g, '_');
                    if (window[populateFuncName]) {
                        // Pass the original deductions array to the populator function
                        window[populateFuncName](data.deductions || []);
                    }
                }
                // --- END OF CHANGE ---
                
                openModal(modalElement);

            } catch (error) {
                console.error('Error populating edit form:', error);
                alert('Could not load item details. Please check your network connection or try again later.');
            }
        }

        // --- Global Modal Close Button Handler ---
        if (closeModalButton) {
            const modalToClose = closeModalButton.closest('.modal-backdrop');
            if (modalToClose) {
                closeModal(modalToClose);
            }
        }
    });
    // --- END OF NEW MODIFICATION ---
});