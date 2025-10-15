// static/js/calendar.js
document.addEventListener('DOMContentLoaded', function() {
    const calendarEl = document.getElementById('calendar');
    if (!calendarEl) return;

    // --- Modal Element Refs ---
    const modal = document.getElementById('create-schedule-modal');
    const form = document.getElementById('schedule-form');
    const discardBtn = document.getElementById('discard-schedule-btn');
    const scheduleIdInput = document.getElementById('schedule-id');
    const scheduleTitleInput = document.getElementById('schedule-title');
    const scheduleDateInput = document.getElementById('schedule-date');
    const startTimeInput = document.getElementById('schedule-start-time');
    const endTimeInput = document.getElementById('schedule-end-time');

    // --- Calendar View Buttons ---
    const dayViewBtn = document.getElementById('day-view-btn');
    const weekViewBtn = document.getElementById('week-view-btn');
    const monthViewBtn = document.getElementById('month-view-btn');
    const yearViewBtn = document.getElementById('year-view-btn');

    const calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'timeGridWeek', // The default view
        headerToolbar: {
            left: 'prev',
            center: 'title',
            right: 'next'
        },
        events: '/api/schedules', // URL to fetch events
        editable: true,       // Allows dragging and resizing
        selectable: true,       // Allows clicking and dragging on empty slots

        // --- Event Handlers ---

        // Triggered when clicking an empty date/time
        select: function(info) {
            form.reset();
            scheduleIdInput.value = ''; // Ensure it's a new event
            
            // Pre-fill date and time
            scheduleDateInput.value = info.startStr.slice(0, 10);
            if (!info.allDay) {
                startTimeInput.value = info.startStr.slice(11, 16);
                endTimeInput.value = info.endStr.slice(11, 16);
            }
            
            modal.classList.remove('hidden');
        },

        // Triggered when clicking an existing event
        eventClick: function(info) {
            // Populate form with existing event data for editing
            form.reset();
            const event = info.event;
            scheduleIdInput.value = event.id;
            scheduleTitleInput.value = event.title;
            scheduleDateInput.value = event.startStr.slice(0, 10);
            
            // Handle description, location etc. from extendedProps
            document.getElementById('schedule-description').value = event.extendedProps.description || '';
            document.getElementById('schedule-location').value = event.extendedProps.location || '';
            
            if (!event.allDay) {
                startTimeInput.value = event.startStr.slice(11, 16);
                endTimeInput.value = event.endStr.slice(11, 16);
            }
            document.getElementById('all-day-toggle').checked = event.allDay;

            modal.classList.remove('hidden');
        },

        // Triggered when an event is dragged and dropped
        eventDrop: function(info) {
            // Here you would make an API call to update the event's date
            console.log(info.event.title + " was dropped on " + info.event.start.toISOString());
            // Example: fetch(`/api/schedules/update/${info.event.id}`, { method: 'PUT', ... })
        }
    });

    calendar.render();

    // --- Modal and Button Logic ---
    const closeModal = () => modal.classList.add('hidden');
    discardBtn.addEventListener('click', closeModal);
    document.getElementById('create-schedule-btn').addEventListener('click', () => {
        form.reset();
        scheduleIdInput.value = '';
        modal.classList.remove('hidden');
    });

    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        const formData = new FormData(this);
        const url = '/api/schedules/add'; // For now, only handles adding
        
        try {
            const response = await fetch(url, {
                method: 'POST',
                body: new URLSearchParams(formData).toString(),
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || ''
                }
            });
            const result = await response.json();
            if (result.success) {
                closeModal();
                calendar.refetchEvents(); // Refresh the calendar to show the new event
            } else {
                alert('Error: ' + (result.error || 'Could not save schedule.'));
            }
        } catch (error) {
            console.error('Failed to submit schedule:', error);
            alert('A network error occurred.');
        }
    });

    // --- View Switching Logic ---
    function setActiveView(activeBtn) {
        [dayViewBtn, weekViewBtn, monthViewBtn, yearViewBtn].forEach(btn => {
            btn.classList.remove('bg-white', 'shadow');
        });
        activeBtn.classList.add('bg-white', 'shadow');
    }

    dayViewBtn.addEventListener('click', () => {
        calendar.changeView('timeGridDay');
        setActiveView(dayViewBtn);
    });
    weekViewBtn.addEventListener('click', () => {
        calendar.changeView('timeGridWeek');
        setActiveView(weekViewBtn);
    });
    monthViewBtn.addEventListener('click', () => {
        calendar.changeView('dayGridMonth');
        setActiveView(monthViewBtn);
    });
    yearViewBtn.addEventListener('click', () => {
        calendar.changeView('dayGridYear');
        setActiveView(yearViewBtn);
    });
});