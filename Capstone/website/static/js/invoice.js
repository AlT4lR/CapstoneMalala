// static/js/invoice.js
document.addEventListener("DOMContentLoaded", () => {
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");
    const fileList = document.getElementById("file-list");

    if (!dropZone) return;

    dropZone.addEventListener("click", () => fileInput.click());
    dropZone.addEventListener("dragover", e => { e.preventDefault(); dropZone.classList.add("bg-green-50"); });
    dropZone.addEventListener("dragleave", () => dropZone.classList.remove("bg-green-50"));
    dropZone.addEventListener("drop", e => {
        e.preventDefault();
        dropZone.classList.remove("bg-green-50");
        handleFiles(e.dataTransfer.files);
    });
    fileInput.addEventListener("change", e => handleFiles(e.target.files));

    function handleFiles(files) {
        [...files].forEach(file => {
            const item = document.createElement("div");
            item.className = "flex items-center gap-3 p-3 border rounded-lg bg-white";
            item.innerHTML = `
                <i class="fas fa-file-invoice text-gray-500 fa-2x"></i>
                <div class="flex-1"><p class="font-medium truncate">${file.name}</p><p class="text-xs text-gray-500">${(file.size / 1024).toFixed(1)} KB</p></div>
                <button class="remove text-red-500 hover:text-red-700 font-bold">&times;</button>
            `;
            item.querySelector(".remove").addEventListener("click", () => item.remove());
            fileList.appendChild(item);
        });
    }
});