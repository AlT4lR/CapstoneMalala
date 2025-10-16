// static/js/invoice.js
document.addEventListener("DOMContentLoaded", () => {
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");
    const fileList = document.getElementById("file-list");
    // --- START OF MODIFICATION: Added form and button elements ---
    const invoiceForm = document.getElementById("invoice-form");
    const uploadBtn = document.getElementById("upload-btn");
    let filesToUpload = []; // Array to store the actual File objects
    // --- END OF MODIFICATION ---

    if (!dropZone || !fileInput || !fileList) {
        console.error("Uploader elements not found.");
        return;
    }

    // --- Event Listeners ---
    dropZone.addEventListener("click", () => fileInput.click());
    dropZone.addEventListener("dragover", e => {
        e.preventDefault();
        dropZone.classList.add("border-[#3a4d39]", "bg-green-50");
    });
    dropZone.addEventListener("dragleave", () => {
        dropZone.classList.remove("border-[#3a4d39]", "bg-green-50");
    });
    dropZone.addEventListener("drop", e => {
        e.preventDefault();
        dropZone.classList.remove("border-[#3a4d39]", "bg-green-50");
        handleFiles(e.dataTransfer.files);
    });
    fileInput.addEventListener("change", e => handleFiles(e.target.files));


    // --- START OF MODIFICATION: Simplified handleFiles and added remove functionality ---
    const handleFiles = (newFiles) => {
        [...newFiles].forEach(file => {
            // Prevent duplicates
            if (filesToUpload.some(f => f.name === file.name && f.size === file.size)) {
                return;
            }
            filesToUpload.push(file); // Add the actual file object to our array
            const fileId = `file-${Date.now()}-${Math.random()}`;
            const fileItemHTML = createFileItemHTML(file, fileId);
            fileList.insertAdjacentHTML('beforeend', fileItemHTML);

            // Add event listener to the new remove button
            document.getElementById(fileId).querySelector('.remove-btn').addEventListener('click', () => {
                removeFile(file, fileId);
            });
        });
    };

    const createFileItemHTML = (file, fileId) => {
        const fileSize = (file.size / 1024).toFixed(1); // in KB
        return `
            <div id="${fileId}" class="flex items-center gap-4 p-3 bg-white border border-gray-200 rounded-lg">
                <div class="flex-shrink-0">
                    <i class="fa-solid fa-image text-2xl text-gray-400"></i>
                </div>
                <div class="flex-1 min-w-0">
                    <p class="text-sm font-semibold truncate">${file.name}</p>
                    <p class="text-xs text-gray-500 mt-1">${fileSize} KB</p>
                </div>
                <div>
                    <button class="remove-btn text-gray-400 hover:text-red-600 text-xl">&times;</button>
                </div>
            </div>
        `;
    };
    
    const removeFile = (file, fileId) => {
        // Remove from the array
        filesToUpload = filesToUpload.filter(f => !(f.name === file.name && f.size === file.size));
        // Remove from the DOM
        document.getElementById(fileId).remove();
    };
    // --- END OF MODIFICATION ---

    // --- START OF MODIFICATION: Real form submission logic ---
    if (invoiceForm && uploadBtn) {
        invoiceForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            if (filesToUpload.length === 0) {
                alert('Please select at least one file to upload.');
                return;
            }

            uploadBtn.disabled = true;
            uploadBtn.textContent = 'Uploading...';

            const formData = new FormData();
            // Append form fields
            formData.append('folder-name', document.getElementById('folder-name').value);
            formData.append('categories', document.getElementById('categories').value);
            formData.append('date', document.getElementById('date').value);

            // Append files
            filesToUpload.forEach(file => {
                formData.append('files', file);
            });

            try {
                const response = await fetch('/api/invoices/upload', {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-CSRF-Token': window.getCSRFToken ? window.getCSRFToken() : ''
                    }
                });

                if (!response.ok) {
                    throw new Error(`Server responded with status: ${response.status}`);
                }
                
                const result = await response.json();
                
                if (result.success && result.redirect_url) {
                    window.location.href = result.redirect_url;
                } else {
                    alert(result.error || 'An unknown error occurred during upload.');
                    uploadBtn.disabled = false;
                    uploadBtn.textContent = 'Upload';
                }

            } catch (error) {
                console.error("Upload failed:", error);
                alert("An error occurred while uploading the files. Please check the console and try again.");
                uploadBtn.disabled = false;
                uploadBtn.textContent = 'Upload';
            }
        });
    }
    // --- END OF MODIFICATION ---

});