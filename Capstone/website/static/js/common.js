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
        modal.className = 'hidden fixed inset-0 z-[9999] bg-gray-900 bg-opacity-75 flex items-center justify-center p-4';
        modal.innerHTML = `
            <div class="bg-[#fafaf5] rounded-xl shadow-2xl p-8 w-full max-w-sm text-center relative">
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

    const hideDialog = () => dialogModal.classList.add('hidden');

    window.showCustomConfirm = (message, onConfirm) => {
        messageEl.textContent = message;
        iconContainer.innerHTML = `<i class="fa-solid fa-trash-can text-5xl text-red-500"></i>`;
        
        okBtn.onclick = () => { hideDialog(); onConfirm(); };
        cancelBtn.onclick = hideDialog;

        dialogModal.classList.remove('hidden');
    };
}

document.addEventListener('DOMContentLoaded', function() {
    setupCustomDialog();

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    window.getCsrfToken = () => csrfToken;

    // --- START OF MODIFICATION ---
    // This block finds the flash message container and makes it fade out.
    const flashContainer = document.getElementById('flash-messages-overlay-container');
    if (flashContainer) {
        // Wait 5 seconds before starting the fade-out
        setTimeout(() => {
            flashContainer.style.opacity = '0';
            // After the CSS transition is complete, remove the element from the DOM
            flashContainer.addEventListener('transitionend', () => flashContainer.remove());
        }, 5000);
    }
    // --- END OF MODIFICATION ---

    document.body.addEventListener('click', async (event) => {
        const deleteButton = event.target.closest('.delete-btn');
        if (!deleteButton) return;
    
        const transactionId = deleteButton.dataset.id;
        const transactionName = deleteButton.dataset.name || 'this item';
        
        if (!transactionId) return;

        window.showCustomConfirm(`Are you sure you want to delete ${transactionName}?`, async () => {
            const response = await fetch(`/api/transactions/${transactionId}`, {
                method: 'DELETE',
                headers: { 'X-CSRF-Token': window.getCsrfToken() }
            });
            if (response.ok) {
                window.location.reload(); // Reload to show flash message and updated list
            } else {
                alert('Error: Could not delete the transaction.');
            }
        });
    });
});