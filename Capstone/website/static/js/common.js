// website/static/js/common.js

if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js')
            .then(registration => console.log('ServiceWorker registration successful.'))
            .catch(err => console.log('ServiceWorker registration failed: ', err));
    });
}

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

    const flashContainer = document.getElementById('flash-messages-overlay-container');
    if (flashContainer) {
        setTimeout(() => {
            flashContainer.style.opacity = '0';
            flashContainer.addEventListener('transitionend', () => flashContainer.remove());
        }, 5000);
    }

    document.body.addEventListener('click', async (event) => {
        const deleteButton = event.target.closest('.delete-btn');
        const editButton = event.target.closest('.edit-btn');
        const closeModalButton = event.target.closest('.close-modal-btn');

        if (deleteButton) {
            const itemId = deleteButton.dataset.id;
            const itemName = deleteButton.dataset.name || 'this item';
            if (!itemId) return;

            window.showCustomConfirm(`Are you sure you want to archive "${itemName}"?`, async () => {
                try {
                    const response = await fetch(`/api/transactions/${itemId}`, {
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
                if (!response.ok) throw new Error(`Server error: ${response.status}`);
                
                const data = await response.json();

                modalElement.querySelector('input[name="transaction_id"]').value = transactionId;
                if(modalElement.querySelector('input[name="name"]')) modalElement.querySelector('input[name="name"]').value = data.name || '';
                if(modalElement.querySelector('input[name="name_of_issued_check"]')) modalElement.querySelector('input[name="name_of_issued_check"]').value = data.name || '';
                if(modalElement.querySelector('input[name="check_no"]')) modalElement.querySelector('input[name="check_no"]').value = data.check_no || '';
                if(modalElement.querySelector('input[name="check_amount"]')) modalElement.querySelector('input[name="check_amount"]').value = data.check_amount || '0.00';
                if(modalElement.querySelector('textarea[name="notes"]')) modalElement.querySelector('textarea[name="notes"]').value = data.notes || '';
                if(modalElement.querySelector('input[name="ewt"]')) modalElement.querySelector('input[name="ewt"]').value = data.ewt || '0.00';
                
                // --- START OF FIX: Added population for the countered_check field ---
                if(modalElement.querySelector('input[name="countered_check"]')) {
                    modalElement.querySelector('input[name="countered_check"]').value = data.countered_check || '0.00';
                }
                // --- END OF FIX ---

                const checkDateInput = modalElement.querySelector('input[name="check_date"]');
                if (checkDateInput) flatpickr(checkDateInput).setDate(data.check_date);
                
                const dueDateInput = modalElement.querySelector('input[name="due_date"]');
                if (dueDateInput) flatpickr(dueDateInput).setDate(data.due_date);
                
                if (modalElement.id === 'edit-check-modal') {
                    const populateFuncName = 'populateDeductions_edit_check';
                    if (window[populateFuncName]) {
                        window[populateFuncName](data.deductions || []);
                    }
                }
                
                openModal(modalElement);

            } catch (error) {
                console.error('Error populating edit form:', error);
                alert('Could not load item details. Please try again.');
            }
        }

        if (closeModalButton) {
            const modalToClose = closeModalButton.closest('.modal-backdrop');
            if (modalToClose) {
                closeModal(modalToClose);
            }
        }
    });
});