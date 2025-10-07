// website/static/js/add_transaction.js
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('add-transaction-form');
    if (!form) return;

    form.addEventListener('submit', function(event) {
        event.preventDefault();

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

        if ('serviceWorker' in navigator && 'SyncManager' in window) {
            navigator.serviceWorker.ready.then(sw => {
                // Save the data to IndexedDB's outbox
                window.db.writeData('transaction-outbox', transactionData)
                    .then(() => {
                        // Register the background sync
                        return sw.sync.register('sync-new-transactions');
                    })
                    .then(() => {
                        console.log('Transaction saved to outbox and sync registered.');
                        // Provide immediate feedback and redirect
                        alert('Transaction saved and will be uploaded automatically when you are back online.');
                        window.location.href = '/transactions/pending';
                    })
                    .catch(err => {
                        console.error('Error saving transaction for sync:', err);
                        // Fallback to trying a direct network request
                        sendToServer(transactionData);
                    });
            });
        } else {
            // Fallback for browsers that don't support background sync
            sendToServer(transactionData);
        }
    });

    function sendToServer(data) {
        fetch('/api/transactions/add', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': window.getCsrfToken()
            },
            body: JSON.stringify(data)
        })
        .then(response => {
            if (response.ok) {
                alert('Transaction added successfully!');
                const statusMap = {
                    'Paid': '/transactions/paid',
                    'Pending': '/transactions/pending',
                    'Declined': '/transactions/declined'
                };
                window.location.href = statusMap[data.status] || '/dashboard';
            } else {
                return response.json().then(err => { throw new Error(err.error) });
            }
        })
        .catch(error => {
            alert(`Could not add transaction: ${error.message}`);
        });
    }
});