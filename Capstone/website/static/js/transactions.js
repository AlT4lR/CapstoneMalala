document.addEventListener('DOMContentLoaded', function() {
    const mainContent = document.querySelector('main[data-status]');
    if (!mainContent) {
        console.error('Main content with data-status attribute not found.');
        return;
    }

    const status = mainContent.dataset.status;
    const transactionList = document.getElementById('transaction-list');
    let networkDataReceived = false;

    function renderTransactions(data) {
        transactionList.innerHTML = ''; // Clear the list first
        if (!data || data.length === 0) {
            transactionList.innerHTML = `<div class="flex items-center justify-center h-full pt-16"><p class="text-gray-500">No ${status.toLowerCase()} transactions found.</p></div>`;
            return;
        }

        const statusColors = {
            'Paid': 'bg-[#3a4d39] text-white',
            'Pending': 'bg-yellow-500 text-white',
            'Declined': 'bg-red-500 text-white'
        };

        for (const trx of data) {
            const row = document.createElement('div');
            // This is now dynamically set inside the 'if' block
            let gridClass = ''; 
            const statusClass = statusColors[trx.status] || 'bg-gray-500 text-white';

            let rowHTML = `
                <span class="font-semibold view-details-link cursor-pointer hover:underline" data-id="${trx._id}">${trx.name}</span>
                <span class="text-gray-600">#${trx.check_no}</span>
                <span class="text-gray-600">${trx.check_date}</span>
                <span class="text-gray-600">${trx.countered}</span>
                <span class="font-semibold">₱ ${parseFloat(trx.amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                <span class="text-gray-600">${trx.ewt}</span>
            `;

            // Dynamically adjust grid and content based on the status
            if (status === 'Declined') {
                gridClass = 'grid grid-cols-8 gap-4 items-center px-4 py-3 text-sm text-gray-700 bg-white rounded-lg border border-gray-200 shadow-sm transaction-row';
                rowHTML += `
                    <div class="text-center">
                        <span class="px-4 py-1 rounded-full text-xs font-semibold ${statusClass}">${trx.status}</span>
                    </div>
                    <div class="text-center">
                        <button class="text-gray-400 hover:text-red-600 delete-btn" data-id="${trx._id}" title="Delete">
                            <i class="fas fa-trash-alt"></i>
                        </button>
                    </div>
                `;
            } else { // For Paid and Pending
                gridClass = 'grid grid-cols-7 gap-4 items-center px-4 py-3 text-sm text-gray-700 bg-white rounded-lg border border-gray-200 shadow-sm transaction-row';
                rowHTML += `
                    <div class="text-center">
                        <span class="px-4 py-1 rounded-full text-xs font-semibold ${statusClass}">${trx.status}</span>
                    </div>
                `;
            }

            row.className = gridClass;
            row.innerHTML = rowHTML;
            transactionList.appendChild(row);
        }
    }

    // --- Data Fetching Logic (Network-First, Cache-Fallback) ---
    const apiUrl = `/api/transactions/${status.toLowerCase()}`;
    fetch(apiUrl)
        .then(res => {
            if (!res.ok) {
                throw new Error(`Network response was not ok: ${res.statusText}`);
            }
            return res.json();
        })
        .then(data => {
            networkDataReceived = true;
            console.log(`Received fresh data from network for status: ${status}`, data);
            
            // --- START OF FIXED CACHING LOGIC ---
            // 1. Read all existing data from the cache.
            window.db.readAllData('transactions')
                .then(existingData => {
                    // 2. Filter out items that match the current status, preserving the cache for other statuses.
                    const otherStatusData = existingData.filter(trx => trx.status !== status);
                    
                    // 3. Combine the preserved data with the fresh data from the network.
                    const combinedData = [...otherStatusData, ...data];

                    // 4. Clear the entire store and rewrite the updated, combined dataset.
                    return window.db.clearAllData('transactions')
                        .then(() => window.db.writeData('transactions', combinedData))
                        .then(() => renderTransactions(data)); // Render the fresh data to the page.
                });
            // --- END OF FIXED CACHING LOGIC ---
        })
        .catch(err => {
            console.error('Network fetch failed:', err);
             // If network fails, try to load from IndexedDB as a fallback.
            window.db.readAllData('transactions')
                .then(data => {
                    if (!networkDataReceived) {
                        console.log('Rendering stale data from IndexedDB due to network failure:', data);
                        const filteredData = data.filter(trx => trx.status === status);
                        renderTransactions(filteredData);
                    }
                });
        });

    // Load from IndexedDB immediately for a faster initial load if starting offline.
    if (!navigator.onLine) {
        window.db.readAllData('transactions')
            .then(data => {
                if (!networkDataReceived) {
                    console.log('Offline: Rendering stale data from IndexedDB:', data);
                    const filteredData = data.filter(trx => trx.status === status);
                    renderTransactions(filteredData);
                }
            });
    }
});