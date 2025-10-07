// website/static/js/transactions.js
document.addEventListener('DOMContentLoaded', function() {
    const mainContent = document.querySelector('main[data-status]');
    if (!mainContent) return;

    const status = mainContent.dataset.status;
    const transactionList = document.getElementById('transaction-list');
    let networkDataReceived = false;

    function renderTransactions(data) {
        transactionList.innerHTML = ''; // Clear existing list
        if (!data || data.length === 0) {
            transactionList.innerHTML = `<div class="flex items-center justify-center h-full pt-16"><p class="text-gray-500">No ${status.toLowerCase()} transactions found.</p></div>`;
            return;
        }

        const statusColors = {
            'Paid': 'bg-[#3a4d39] text-white',
            'Pending': 'bg-yellow-500 text-white',
            'Declined': 'bg-red-500 text-white'
        };
        const statusClass = statusColors[status] || 'bg-gray-500 text-white';

        for (const trx of data) {
            const row = document.createElement('div');
            row.className = 'grid grid-cols-7 gap-4 items-center px-4 py-3 text-sm text-gray-700 bg-white rounded-lg border border-gray-200 shadow-sm transaction-row';
            row.innerHTML = `
                <span class="font-semibold view-details-link cursor-pointer hover:underline" data-id="${trx._id}">${trx.name}</span>
                <span class="text-gray-600">#${trx.check_no}</span>
                <span class="text-gray-600">${trx.check_date}</span>
                <span class="text-gray-600">${trx.countered}</span>
                <span class="font-semibold">₱ ${parseFloat(trx.amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                <span class="text-gray-600">${trx.ewt}</span>
                <div class="text-center">
                    <span class="px-4 py-1 rounded-full text-xs font-semibold ${statusClass}">${trx.status}</span>
                </div>
            `;
            transactionList.appendChild(row);
        }
    }

    // 1. Fetch from network
    const apiUrl = `/api/transactions/${status.toLowerCase()}`;
    fetch(apiUrl)
        .then(res => res.json())
        .then(data => {
            networkDataReceived = true;
            console.log('Received fresh data from network:', data);
            // Clear old data and write fresh data to IndexedDB
            window.db.clearAllData('transactions')
                .then(() => window.db.writeData('transactions', data))
                .then(() => renderTransactions(data));
        })
        .catch(err => console.error('Network fetch failed:', err));

    // 2. Load from IndexedDB immediately (if network is slow or offline)
    window.db.readAllData('transactions')
        .then(data => {
            // Only render from cache if network data hasn't arrived yet
            if (!networkDataReceived) {
                console.log('Rendering stale data from IndexedDB:', data);
                // Filter by status since the store contains all transactions
                const filteredData = data.filter(trx => trx.status === status);
                renderTransactions(filteredData);
            }
        });
});