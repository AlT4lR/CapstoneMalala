// static/js/calendar.js
document.addEventListener('DOMContentLoaded', function() {
    const calendarEl = document.getElementById('calendar');
    if (!calendarEl) return;

    const createModal = document.getElementById('create-schedule-modal');
    const modalContent = document.getElementById('modal-content');
    const createScheduleBtn = document.getElementById('create-schedule-btn');
    const discardBtn = document.getElementById('discard-btn');
    const scheduleForm = document.getElementById('create-schedule-form');

    const showCreateModal = (info = {}) => {
        scheduleForm.reset();
        if (info.startStr) {
            const start = new Date(info.startStr);
            document.getElementById('schedule-start-date').value = start.toISOString().slice(0, 10);
            document.getElementById('schedule-start-time').value = start.toTimeString().slice(0, 5);
        }
        if (info.endStr) {
            const end = new Date(info.endStr);
            document.getElementById('schedule-end-time').value = end.toTimeString().slice(0, 5);
        }
        createModal.classList.remove('hidden');
        setTimeout(() => modalContent.classList.remove('scale-95'), 10);
    };

    const hideCreateModal = () => {
        modalContent.classList.add('scale-95');
        setTimeout(() => createModal.classList.add('hidden'), 200);
    };

    createScheduleBtn.addEventListener('click', () => showCreateModal());
    discardBtn.addEventListener('click', hideCreateModal);
    createModal.addEventListener('click', (e) => {
        if (e.target === createModal) hideCreateModal();
    });

    const calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridMonth',
        headerToolbar: false,
        height: '100%',
        selectable: true,
        editable: true,
        dayMaxEvents: true,
        navLinks: true,

        events: {
            url: '/api/schedules',
            failure: () => alert('There was an error while fetching events!'),
        },

        eventClick(info) {
            info.jsEvent.preventDefault();
            alert(
                `Event: ${info.event.title}\n` +
                `Category: ${info.event.extendedProps.category}\n` +
                `Notes: ${info.event.extendedProps.notes || 'None'}`
            );
        },

        select(info) {
            showCreateModal(info);
            calendar.unselect();
        },

        eventDrop(info) {
            if (!confirm(`Move ${info.event.title}?`)) {
                info.revert();
            } else {
                alert(`${info.event.title} moved to ${info.event.start.toISOString()}`);
            }
        }
    });

    calendar.render();

    scheduleForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(scheduleForm);
        const title = formData.get('title');
        const startDate = formData.get('start_date');
        const startTime = formData.get('start_time');
        const endTime = formData.get('end_time');
        const category = formData.get('category');
        const notes = formData.get('notes');

        const startDateTime = new Date(`${startDate}T${startTime}`).toISOString();
        const endDateTime = new Date(`${startDate}T${endTime}`).toISOString();

        try {
            const response = await fetch('/api/schedules/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    // --- THIS IS THE FIX ---
                    'X-CSRF-Token': window.getCsrfToken() 
                },
                body: JSON.stringify({
                    title,
                    start: startDateTime,
                    end: endDateTime,
                    category,
                    notes
                })
            });

            const result = await response.json();
            if (response.ok) {
                hideCreateModal();
                calendar.refetchEvents();
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