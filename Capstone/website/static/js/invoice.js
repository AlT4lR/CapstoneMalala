// static/js/invoice.js
document.addEventListener("DOMContentLoaded", () => {
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");
    const fileList = document.getElementById("file-list");
    const invoiceForm = document.getElementById("invoice-form");

    // A Map to keep track of files and their associated UI elements
    const fileMap = new Map();

    // --- PWA: Background Sync Logic ---

    /**
     * Registers a one-time background sync event.
     */
    function registerBackgroundSync() {
        if ('serviceWorker' in navigator && 'SyncManager' in window) {
            navigator.serviceWorker.ready.then(swRegistration => {
                // The tag 'sync-new-invoices' will be handled in the service worker
                return swRegistration.sync.register('sync-new-invoices');
            }).then(() => {
                console.log('Background sync for invoices registered.');
            }).catch(err => {
                console.error('Background sync registration failed:', err);
            });
        }
    }

    /**
     * CONCEPTUAL: Saves the invoice request data locally to a store like IndexedDB.
     * In a real application, you'd also save the file itself (e.g., using the Cache API or Filesystem API).
     * @param {FormData} formData The form data to be saved.
     * @param {File} file The actual file object.
     * @param {string} tempId A temporary ID for the transaction.
     */
    function saveInvoiceForSync(formData, file, tempId) {
        // --- NOTE: This is a conceptual implementation. Real IndexedDB logic is required here. ---
        
        // Convert FormData to a storable object
        const dataToStore = {
            id: tempId,
            filename: file.name,
            fileMimeType: file.type,
            folder_name: formData.get("folder_name"),
            category: formData.get("category"),
            invoice_date: formData.get("invoice_date"),
            // In a real app, you'd save the file data itself using a more robust mechanism
            // For now, we'll just log that it was prepared for sync.
        };
        
        console.log("Invoice queued for sync. Data:", dataToStore);
        // IndexedDB: db.add('outbox', dataToStore);
        
        // For demonstration, we'll store a placeholder in sessionStorage
        // In reality, this data would be stored persistently in IndexedDB.
        let outbox = JSON.parse(sessionStorage.getItem('sync-outbox-invoices') || '[]');
        outbox.push(dataToStore);
        sessionStorage.setItem('sync-outbox-invoices', JSON.stringify(outbox));

        // We assume the service worker will handle fetching the file from a temporary local store 
        // or re-uploading the saved data when the sync event fires.
    }
    
    // --- End PWA Logic ---

    /**
     * Handles the actual file upload to the backend.
     * @param {File} file The file to upload.
     * @param {HTMLElement} itemEl The UI element for this file.
     */
    function uploadFile(file, itemEl) {
        const xhr = new XMLHttpRequest();
        const formData = new FormData();
        const csrfToken = window.getCsrfToken(); // Assumes getCsrfToken is globally available from common.js

        // Use a unique ID to track this transaction across offline queue and eventual upload
        const tempId = Date.now().toString(36) + Math.random().toString(36).substr(2);

        // Append file and form data
        formData.append("invoice_file", file);
        formData.append("folder_name", document.getElementById("folder-name").value);
        formData.append("category", document.getElementById("categories").value);
        formData.append("invoice_date", document.getElementById("invoice-date").value);

        const progressBar = itemEl.querySelector(".progress-bar");
        const statusText = itemEl.querySelector(".status-text");
        const retryBtn = itemEl.querySelector(".retry");
        const removeBtn = itemEl.querySelector(".remove");

        // UI update for upload start
        statusText.textContent = "Uploading...";
        statusText.className = "status-text text-gray-500";
        retryBtn.classList.add("hidden");
        progressBar.style.width = "0%";

        xhr.open("POST", "/api/invoice/upload", true);
        xhr.setRequestHeader("X-CSRF-Token", csrfToken);

        // Progress event
        xhr.upload.onprogress = (event) => {
            if (event.lengthComputable) {
                const percentComplete = (event.loaded / event.total) * 100;
                progressBar.style.width = `${percentComplete}%`;
            }
        };

        // Upload finished (successfully or not)
        xhr.onload = () => {
            if (xhr.status >= 200 && xhr.status < 300) {
                // Success
                statusText.textContent = "Done";
                statusText.className = "status-text text-green-600 font-semibold";
                progressBar.style.width = "100%";
                removeBtn.classList.add("hidden"); // Prevent removal of successful uploads
            } else {
                // Server Error (e.g., 400, 500)
                const response = JSON.parse(xhr.responseText || "{}");
                statusText.textContent = `Error: ${response.error || 'Upload failed'}`;
                statusText.className = "status-text text-red-600 font-semibold";
                retryBtn.classList.remove("hidden");
            }
        };
        
        // --- PWA: Background Sync Integration FIX ---
        // Network error (i.e., we are offline)
        xhr.onerror = () => {
            statusText.textContent = "Offline. Queued for sync.";
            statusText.className = "status-text text-blue-600 font-semibold";
            retryBtn.classList.add("hidden"); // Cannot retry immediately if offline

            // Save the form data locally and register for sync
            saveInvoiceForSync(formData, file, tempId);
            registerBackgroundSync();
        };
        // --- End FIX ---

        xhr.send(formData);
    }

    /**
     * Creates the UI element for a newly added file.
     * @param {File} file The file object.
     */
    function createFileItem(file) {
        const item = document.createElement("div");
        item.className = "flex items-center gap-3 p-3 border rounded-lg text-sm relative bg-white shadow-sm";
        
        // Check if file is already in the map by object reference to prevent duplicates
        // Note: For files dropped at different times, two identical files might be added
        // if we don't check by name/size. For simplicity, we stick to object reference for now.
        if (fileMap.has(file)) return;
        fileMap.set(file, item); // Associate file with its element

        item.innerHTML = `
            <div class="w-10 h-10 flex items-center justify-center border rounded bg-gray-100">
                <i class="fas fa-file-invoice text-gray-500"></i>
            </div>
            <div class="flex-1">
                <p class="font-medium truncate">${file.name}</p>
                <p class="text-xs text-gray-500">${(file.size / 1024).toFixed(1)} KB</p>
                <div class="h-1.5 bg-gray-200 rounded mt-1.5 overflow-hidden">
                    <div class="progress-bar h-full bg-[#6f8a6e] w-0 transition-width duration-300"></div>
                </div>
            </div>
            <div class="text-xs text-gray-500 flex items-center gap-2">
                <span class="status-text font-medium">Queued</span>
                <button class="retry hidden text-blue-600 hover:underline">Retry</button>
                <button class="remove text-red-500 hover:text-red-700 font-bold">✕</button>
            </div>
        `;
        
        item.querySelector(".remove").addEventListener("click", () => {
            fileMap.delete(file);
            item.remove();
        });

        item.querySelector(".retry").addEventListener("click", () => {
            if (!validateForm()) return;
            uploadFile(file, item);
        });

        fileList.appendChild(item);
    }

    function handleFiles(files) {
        [...files].forEach(file => {
            createFileItem(file); // createFileItem now handles the fileMap check
        });
    }

    function validateForm() {
        if (!document.getElementById("folder-name").value ||
            !document.getElementById("categories").value ||
            !document.getElementById("invoice-date").value) {
            alert("Please fill in Folder Name, Category, and Date before uploading.");
            return false;
        }
        return true;
    }

    // Event Listeners
    dropZone.addEventListener("click", () => fileInput.click());
    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.classList.add("bg-green-50", "border-green-400");
    });
    dropZone.addEventListener("dragleave", () => {
        dropZone.classList.remove("bg-green-50", "border-green-400");
    });
    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.classList.remove("bg-green-50", "border-green-400");
        handleFiles(e.dataTransfer.files);
    });

    fileInput.addEventListener("change", (e) => {
        handleFiles(e.target.files);
        fileInput.value = ""; // Reset for next selection
    });
    
    document.getElementById("upload-btn").addEventListener("click", () => {
        if (!validateForm()) return;
        if (fileMap.size === 0) {
            alert("Please add files to upload.");
            return;
        }
        // Upload all queued or error files
        for (const [file, itemEl] of fileMap.entries()) {
            const status = itemEl.querySelector(".status-text").textContent;
            if (status === "Queued" || status.startsWith("Error")) {
                uploadFile(file, itemEl);
            }
        }
    });

    document.getElementById("save-draft").addEventListener("click", () => {
        alert("Draft functionality is not yet implemented.");
    });
});