document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('add-transaction-form');
    if (!form) {
        console.error('Add transaction form not found!');
        return;
    }

    // --- THIS IS THE FIX ---
    // The getCsrfToken helper function is now removed from this file.
    // We will use the global `window.getCsrfToken()` from `common.js`.

    /**
     * This function saves the transaction to the local database (IndexedDB)
     * for background synchronization. It is ONLY called when the user is offline.
     */
    function saveTransactionForSync(transactionData) {
        // Check if the necessary PWA features are available
        if ('serviceWorker' in navigator && 'SyncManager' in window && window.db) {
            console.log('Attempting to save transaction for background sync.');
            navigator.serviceWorker.ready
                .then(sw => {
                    // Save the data to the 'transaction-outbox' store in IndexedDB
                    return window.db.writeData('transaction-outbox', transactionData);
                })
                .then(() => {
                    // After saving, register a sync event with the service worker
                    return navigator.serviceWorker.ready.then(sw => sw.sync.register('sync-new-transactions'));
                })
                .then(() => {
                    // Inform the user that the data is saved and will be synced later
                    alert('You are offline. Transaction has been saved and will be uploaded automatically when you reconnect.');
                    // Redirect to the pending page to give the user a sense of completion
                    window.location.href = '/transactions/pending';
                })
                .catch(err => {
                    console.error('Could not save transaction for sync:', err);
                    alert('An error occurred while trying to save your transaction for offline use.');
                });
        } else {
            // This alert shows if PWA features are not supported AND the user is offline.
            alert('You appear to be offline, and your browser does not support background saving. Please reconnect to add the transaction.');
        }
    }

    /**
     * This is now the MAIN function. It tries to send the data directly to the server.
     * If it fails due to a network error, it calls the offline saving function as a fallback.
     */
    function sendToServer(transactionData) {
        fetch('/api/transactions/add', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                // --- THIS IS THE FIX ---
                // The CSRF token is added to the request headers.
                'X-CSRF-Token': window.getCsrfToken() 
            },
            body: JSON.stringify(transactionData)
        })
        .then(response => {
            // If the server responds with an error (e.g., 400, 500), handle it.
            if (!response.ok) {
                return response.json().then(err => {
                    // Create a new error to be caught by the .catch() block
                    throw new Error(err.error || 'The server returned an error.');
                });
            }
            return response.json();
        })
        .then(data => {
            // This part runs ONLY if the fetch was successful
            if (data.success) {
                alert('Transaction added successfully!');
                // Redirect to the correct page based on the status selected in the form
                const statusMap = {
                    'Paid': '/transactions/paid',
                    'Pending': '/transactions/pending',
                    'Declined': '/transactions/declined'
                };
                window.location.href = statusMap[transactionData.status] || '/dashboard';
            }
        })
        .catch(error => {
            // This .catch() block will run for two reasons:
            // 1. A network error (the user is offline).
            // 2. An error thrown from the .then() block above (server error).
            
            console.warn('Could not send transaction to server:', error.message);

            // Check if it's a network error by checking the error type
            if (error instanceof TypeError && error.message === 'Failed to fetch') {
                 // This is a network error, so we try to save for offline sync.
                saveTransactionForSync(transactionData);
            } else {
                // This was a server-side error, so we show it to the user.
                alert(`Could not add transaction: ${error.message}`);
            }
        });
    }

    // The main event listener for the form submission
    form.addEventListener('submit', function(event) {
        // ALWAYS prevent the default browser submission
        event.preventDefault();

        // Gather all the data from the form into a simple object
        const formData = new FormData(form);
        const transactionData = {
            name_of_issued_check: formData.get('name_of_issued_check'),
            check_no: formData.get('check_no'),
            check_date: formData.get('check_date'),
            countered_check: formData.get('countered_check') || 0,
            check_amount: formData.get('check_amount'),
            ewt: formData.get('ewt') || 0,
            payment_method: formData.get('payment_method'),
            status: formData.get('status'),
        };

        // The ONLY action is to call the primary function, sendToServer.
        // This makes the logic simple and reliable.
        sendToServer(transactionData);
    });
});