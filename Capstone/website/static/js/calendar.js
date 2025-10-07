// static/js/calendar.js

document.addEventListener('DOMContentLoaded', function() {
    const calendarEl = document.getElementById('calendar');
    if (!calendarEl) return;

    // --- Modal Elements ---
    const createModal = document.getElementById('create-schedule-modal');
    const modalContent = document.getElementById('modal-content');
    const createScheduleBtn = document.getElementById('create-schedule-btn');
    const discardBtn = document.getElementById('discard-btn');
    const scheduleForm = document.getElementById('create-schedule-form');

    // --- Helper function to show/hide the modal ---
    const showCreateModal = (info = {}) => {
        scheduleForm.reset();
        // Pre-fill dates if provided by FullCalendar's 'select' callback
        if (info.startStr) {
            const start = new Date(info.startStr);
            // Format to YYYY-MM-DD for the date input
            document.getElementById('schedule-start-date').value = start.toISOString().slice(0, 10);
            // Format to HH:mm for the time input
            document.getElementById('schedule-start-time').value = start.toTimeString().slice(0, 5);
        }
        if (info.endStr) {
             const end = new Date(info.endStr);
             document.getElementById('schedule-end-time').value = end.toTimeString().slice(0, 5);
        }
        createModal.classList.remove('hidden');
        setTimeout(() => modalContent.classList.remove('scale-95'), 10); // Entrance animation
    };

    const hideCreateModal = () => {
        modalContent.classList.add('scale-95');
        setTimeout(() => createModal.classList.add('hidden'), 200); // Wait for animation
    };

    // --- Event Listeners for Modal ---
    createScheduleBtn.addEventListener('click', () => showCreateModal());
    discardBtn.addEventListener('click', hideCreateModal);
    createModal.addEventListener('click', (e) => {
        if (e.target === createModal) hideCreateModal();
    });

    const calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridMonth',
        themeSystem: 'standard',

        // --- THIS IS THE FIX ---
        // The header toolbar is removed to match the new design.
        headerToolbar: false, 
        height: '100%', // Make calendar fill its container height
        
        navLinks: true,
        dayMaxEvents: true,
        editable: true,
        selectable: true,

        events: {
            url: '/api/schedules',
            failure: () => alert('There was an error while fetching events!'),
        },

        eventClick: function(info) {
            info.jsEvent.preventDefault();
            alert(
                `Event: ${info.event.title}\n` +
                `Category: ${info.event.extendedProps.category}\n` +
                `Notes: ${info.event.extendedProps.notes || 'None'}`
            );
        },

        select: function(info) {
            showCreateModal(info);
            calendar.unselect();
        },

        eventDrop: function(info) {
            alert(info.event.title + " was dropped on " + info.event.start.toISOString() + ".\nThis change should be saved to the database.");
            if (!confirm("Are you sure about this change?")) {
                info.revert();
            }
        }
    });

    calendar.render();

    // Handle Form Submission
    scheduleForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const formData = new FormData(scheduleForm);
        const title = formData.get('title');
        const startDate = formData.get('start_date');
        const startTime = formData.get('start_time');
        const endTime = formData.get('end_time');
        const category = formData.get('category');
        const notes = formData.get('notes');

        // Combine date and time to create full ISO strings
        const startDateTime = new Date(`${startDate}T${startTime}`).toISOString();
        const endDateTime = new Date(`${startDate}T${endTime}`).toISOString();

        try {
            const response = await fetch('/api/schedules/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': window.getCsrfToken() // From common.js
                },
                body: JSON.stringify({
                    title: title,
                    start: startDateTime,
                    end: endDateTime,
                    category: category,
                    notes: notes
                })
            });

            const result = await response.json();

            if (response.ok) {
                hideCreateModal();
                calendar.refetchEvents(); // Reload events from the server
                alert('Schedule created successfully!');
            } else {
                throw new Error(result.error || 'Failed to create schedule.');
            }
        } catch (error) {
            console.error('Error creating schedule:', error);
            alert(`Error: ${error.message}`);
        }
    });
});