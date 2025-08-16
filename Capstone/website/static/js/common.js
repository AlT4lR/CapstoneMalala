// static/js/common.js

document.addEventListener('DOMContentLoaded', function() {

    // --- CSRF Token Handling ---
    let csrfToken = null;
    const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
    if (csrfTokenMeta) {
        csrfToken = csrfTokenMeta.getAttribute('content');
    } else {
        const csrfCookie = document.cookie.split('; ').find(row => row.startsWith('csrf_access_token='));
        if (csrfCookie) {
            csrfToken = csrfCookie.split('=')[1];
        }
    }

    if (!csrfToken) {
        console.warn("CSRF token not found. AJAX requests may fail CSRF protection.");
    }

    window.fetch = async function(url, options = {}) {
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
    
    window.getCsrfToken = () => csrfToken;

    // --- Notification Panel Logic ---
    const notificationBtn = document.getElementById('notification-btn');
    const notificationPanel = document.getElementById('notification-panel');

    if (notificationBtn && notificationPanel) {
        notificationBtn.addEventListener('click', (event) => {
            event.stopPropagation();
            notificationPanel.classList.toggle('hidden');
        });

        document.addEventListener('click', (event) => {
            if (!notificationPanel.contains(event.target) && !notificationBtn.contains(event.target) && !notificationPanel.classList.contains('hidden')) {
                notificationPanel.classList.add('hidden');
            }
        });
    }

    // --- Flash Message Auto-Fade Logic (for the new overlay) ---
    const flashMessagesOverlayContainer = document.getElementById('flash-messages-overlay-container');
    if (flashMessagesOverlayContainer && flashMessagesOverlayContainer.classList.contains('fade-in-animation')) {
        // If it has the fade-in class, remove it after a short delay to allow it to show
        setTimeout(() => {
            flashMessagesOverlayContainer.classList.remove('fade-in-animation');
            
            // Then set up the fade-out after a longer delay
            setTimeout(() => {
                flashMessagesOverlayContainer.classList.add('fade-out');
                flashMessagesOverlayContainer.addEventListener('transitionend', () => {
                    if (flashMessagesOverlayContainer.parentNode) {
                        flashMessagesOverlayContainer.remove();
                    }
                }, { once: true }); // Ensure listener is removed after firing
            }, 5000); // Fade out after 5 seconds
        }, 100); // Small delay to ensure initial rendering before fade-in
    }

    // --- Generic Form Submission with Fetch and CSRF ---
    const createScheduleForm = document.getElementById('create-schedule-form');
    if (createScheduleForm) {
        createScheduleForm.addEventListener('submit', async (e) => {
            e.preventDefault(); 

            const formData = new FormData(createScheduleForm);
            const data = Object.fromEntries(formData.entries());

            const csrfToken = await window.getCsrfToken(); 

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
                    alert('Schedule created successfully!'); 
                    createScheduleModal.classList.add('hidden');
                    createScheduleForm.reset();
                    window.location.reload(); 
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
});