// static/js/invoice.js
document.addEventListener("DOMContentLoaded", () => {
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");
    const fileList = document.getElementById("file-list");
    // --- START OF MODIFICATION ---
    const MAX_FILES = 10; // Define the upload limit
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


    // --- Core Functions ---
    const handleFiles = (files) => {
        // --- START OF MODIFICATION: File limit logic ---
        const existingFilesCount = fileList.children.length;
        const allowedNewFilesCount = MAX_FILES - existingFilesCount;

        if (files.length > allowedNewFilesCount) {
            alert(`You can only upload a maximum of 10 files in total. Please select ${allowedNewFilesCount > 0 ? `up to ${allowedNewFilesCount} more files.` : 'no more files.'}`);
            if (allowedNewFilesCount <= 0) return; // Stop if the list is already full
        }
        
        // Take only the number of files that are allowed
        const filesToProcess = Array.from(files).slice(0, allowedNewFilesCount);

        filesToProcess.forEach(file => {
        // --- END OF MODIFICATION ---
            const fileId = `file-${Date.now()}-${Math.random()}`;
            const fileItemHTML = createFileItemHTML(file, fileId);
            fileList.insertAdjacentHTML('beforeend', fileItemHTML);
            simulateUpload(fileId);
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
                    <div class="status-container text-xs text-gray-500 mt-1">
                        <div class="progress-bar-container w-full bg-gray-200 rounded-full h-1.5 hidden">
                           <div class="progress-bar bg-[#3a4d39] h-1.5 rounded-full" style="width: 0%"></div>
                        </div>
                        <span class="status-text">${fileSize} KB</span>
                    </div>
                </div>
                <div class="action-container">
                    <button class="remove-btn text-gray-400 hover:text-red-600">&times;</button>
                </div>
            </div>
        `;
    };

    const simulateUpload = (fileId) => {
        const fileItem = document.getElementById(fileId);
        const progressBarContainer = fileItem.querySelector('.progress-bar-container');
        const progressBar = fileItem.querySelector('.progress-bar');
        const statusText = fileItem.querySelector('.status-text');
        const actionContainer = fileItem.querySelector('.action-container');
        
        progressBarContainer.classList.remove('hidden');
        statusText.textContent = '0% Done';
        
        let progress = 0;
        const interval = setInterval(() => {
            progress += Math.random() * 10;
            if (progress >= 100) {
                clearInterval(interval);
                Math.random() > 0.3 ? setSuccessState(fileItem) : setErrorState(fileItem);
            } else {
                progressBar.style.width = `${progress}%`;
                statusText.textContent = `${Math.round(progress)}% Done`;
            }
        }, 200);

        actionContainer.querySelector('.remove-btn').addEventListener('click', () => {
            clearInterval(interval);
            fileItem.remove();
        });
    };

    const setSuccessState = (fileItem) => {
        const progressBarContainer = fileItem.querySelector('.progress-bar-container');
        const statusText = fileItem.querySelector('.status-text');
        const actionContainer = fileItem.querySelector('.action-container');

        progressBarContainer.classList.add('hidden');
        statusText.innerHTML = '<i class="fa-solid fa-check text-green-600"></i> Done';
        
        // Replace the simple 'X' button with the red trash can icon.
        actionContainer.innerHTML = `<button class="remove-btn text-red-500 hover:text-red-700 transition-colors"><i class="fa-solid fa-trash-can"></i></button>`;
        
        actionContainer.querySelector('.remove-btn').addEventListener('click', () => fileItem.remove());
    };

    const setErrorState = (fileItem) => {
        const progressBarContainer = fileItem.querySelector('.progress-bar-container');
        const statusText = fileItem.querySelector('.status-text');
        const actionContainer = fileItem.querySelector('.action-container');

        progressBarContainer.classList.add('hidden');
        statusText.innerHTML = '<i class="fa-solid fa-triangle-exclamation text-red-600"></i> Error';
        actionContainer.innerHTML = `<button class="retry-btn text-xs bg-gray-200 px-2 py-1 rounded hover:bg-gray-300">Retry</button>`;
        
        actionContainer.querySelector('.retry-btn').addEventListener('click', (e) => {
             e.stopPropagation();
             simulateUpload(fileItem.id);
        });
    };

});