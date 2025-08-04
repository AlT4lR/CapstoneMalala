// static/js/common.js

document.addEventListener('DOMContentLoaded', function() {

    // --- CSRF Token Handling ---
    // Make CSRF token globally accessible and ensure it's injected into AJAX requests.
    let csrfToken = null;
    const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
    if (csrfTokenMeta) {
        csrfToken = csrfTokenMeta.getAttribute('content');
    } else {
        // Fallback to cookie if meta tag isn't present (adjust cookie name if needed)
        const csrfCookie = document.cookie.split('; ').find(row => row.startsWith('csrf_access_token='));
        if (csrfCookie) {
            csrfToken = csrfCookie.split('=')[1];
        }
    }

    if (!csrfToken) {
        console.warn("CSRF token not found. AJAX requests may fail CSRF protection.");
    }

    // Intercept all fetch calls to inject the CSRF token for relevant requests
    const originalFetch = window.fetch;
    window.fetch = async function(url, options = {}) {
        // Only add CSRF token for API calls and non-GET/HEAD methods
        if (url.startsWith('/api/') && options.method && !['GET', 'HEAD'].includes(options.method.toUpperCase())) {
            if (csrfToken) {
                options.headers = {
                    ...options.headers,
                    'X-CSRF-Token': csrfToken,
                    'Content-Type': options.headers?.['Content-Type'] || 'application/json'
                };
            }
        }
        return originalFetch(url, options);
    };

    // --- Notification Panel Logic ---
    const notificationBtn = document.getElementById('notification-btn');
    const notificationPanel = document.getElementById('notification-panel');

    if (notificationBtn && notificationPanel) {
        notificationBtn.addEventListener('click', (event) => {
            event.stopPropagation(); // Prevent document click from immediately closing it
            notificationPanel.classList.toggle('hidden');
        });

        document.addEventListener('click', (event) => {
            // Close notification panel if clicked outside
            if (!notificationPanel.contains(event.target) && !notificationBtn.contains(event.target) && !notificationPanel.classList.contains('hidden')) {
                notificationPanel.classList.add('hidden');
            }
        });
    }

    // --- Flash Message Auto-Fade Logic ---
    const flashMessagesContainer = document.getElementById('flash-messages-container');
    if (flashMessagesContainer) {
        setTimeout(() => {
            flashMessagesContainer.classList.add('fade-out');
            flashMessagesContainer.addEventListener('transitionend', () => {
                // Remove the element from the DOM after the fade-out transition completes
                if (flashMessagesContainer.parentNode) {
                    flashMessagesContainer.remove();
                }
            });
        }, 5000); // Fades out after 5 seconds (5000 milliseconds)
    }
});