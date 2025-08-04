// static/js/common.js

document.addEventListener('DOMContentLoaded', function() {

    // --- CSRF Token Handling ---
    let csrfToken = null;
    // Try to get CSRF token from meta tag
    const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
    if (csrfTokenMeta) {
        csrfToken = csrfTokenMeta.getAttribute('content');
    } else {
        // Fallback: Try to get CSRF token from cookie (adjust cookie name if needed)
        const csrfCookie = document.cookie.split('; ').find(row => row.startsWith('csrf_access_token='));
        if (csrfCookie) {
            csrfToken = csrfCookie.split('=')[1];
        }
    }

    if (!csrfToken) {
        console.warn("CSRF token not found. AJAX requests may fail CSRF protection.");
    }

    // Override fetch to inject CSRF token and set headers automatically
    const originalFetch = window.fetch;
    window.fetch = async function(url, options = {}) {
        // Only add CSRF token for API calls and non-GET/HEAD methods
        // Adjust URL prefix check if your API routes differ (e.g., '/api/v1/')
        if (url.startsWith('/api/') && options.method && !['GET', 'HEAD'].includes(options.method.toUpperCase())) {
            if (csrfToken) {
                options.headers = {
                    ...options.headers,
                    'X-CSRF-Token': csrfToken,
                    // Ensure Content-Type is set, defaulting to JSON for API calls
                    'Content-Type': options.headers?.['Content-Type'] || 'application/json'
                };
            }
        }
        return originalFetch(url, options);
    };
    
    // Make getCsrfToken globally available if needed by other specific scripts
    window.getCsrfToken = () => csrfToken;


    // --- Notification Panel Logic ---
    const notificationBtn = document.getElementById('notification-btn');
    const notificationPanel = document.getElementById('notification-panel');

    if (notificationBtn && notificationPanel) {
        notificationBtn.addEventListener('click', (event) => {
            event.stopPropagation(); // Prevent document click from immediately closing it
            notificationPanel.classList.toggle('hidden');
        });

        document.addEventListener('click', (event) => {
            // Close notification panel if clicked outside of it or its button
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
            // Remove the element from the DOM after the fade-out transition completes
            flashMessagesContainer.addEventListener('transitionend', () => {
                if (flashMessagesContainer.parentNode) {
                    flashMessagesContainer.remove();
                }
            });
        }, 5000); // Fades out after 5 seconds (5000 milliseconds)
    }

    // --- Generic Form Submission with Fetch and CSRF ---
    // This part is a generic handler. If specific forms need custom logic,
    // they should add their own event listeners, but this ensures basic
    // CSRF and fetch handling for forms submitted via JS.

    // Example: Submit the create schedule form via AJAX
    const createScheduleForm = document.getElementById('create-schedule-form');
    if (createScheduleForm) {
        createScheduleForm.addEventListener('submit', async (e) => {
            e.preventDefault(); // Prevent default form submission

            const formData = new FormData(createScheduleForm);
            const data = Object.fromEntries(formData.entries());

            const csrfToken = await window.getCsrfToken(); // Use the globally available function

            try {
                const response = await fetch('/api/schedules', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRF-Token': csrfToken
                    },
                    body: JSON.stringify(data),
                });

                if (response.ok) {
                    alert('Schedule created successfully!'); // Use alert or a better notification system
                    createScheduleModal.classList.add('hidden');
                    createScheduleForm.reset();
                    // Ideally, trigger a refresh of the main calendar data
                    // For now, a simple page reload or re-rendering is assumed.
                    // If calendar.js is loaded separately, it might need to be triggered.
                    window.location.reload(); // Simple way to refresh, or call a dedicated refresh function
                } else {
                    const errorData = await response.json();
                    alert('Failed to create schedule: ' + (errorData.error || response.statusText));
                }
            } catch (error) {
                console.error('Error submitting schedule:', error);
                alert('An error occurred while creating the schedule.');
            }
        });
    }
    // Add similar handlers for other forms submitting via AJAX if necessary.
});