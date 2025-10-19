// static/js/calendar.js
document.addEventListener('DOMContentLoaded', function() {
    const calendarEl = document.getElementById('calendar');
    if (!calendarEl) return;

    // --- Modal Element Refs ---
    const modal = document.getElementById('create-schedule-modal');
    const form = document.getElementById('schedule-form');
    const scheduleIdInput = document.getElementById('schedule-id');
    const scheduleTitleInput = document.getElementById('schedule-title');
    const scheduleDateInput = document.getElementById('schedule-date');
    const startTimeInput = document.getElementById('schedule-start-time');
    const endTimeInput = document.getElementById('schedule-end-time');
    const allDayToggle = document.getElementById('all-day-toggle');
    const descriptionInput = document.getElementById('schedule-description');
    const locationInput = document.getElementById('schedule-location');
    const scheduleLabelInput = document.getElementById('schedule-label');

    // --- View Buttons ---
    const dayViewBtn = document.getElementById('day-view-btn');
    const weekViewBtn = document.getElementById('week-view-btn');
    const monthViewBtn = document.getElementById('month-view-btn');
    const yearViewBtn = document.getElementById('year-view-btn');

    // Helper to get CSRF token
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';

    // --- FullCalendar Setup ---
    const calendar = window.calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'timeGridWeek',
        headerToolbar: {
            // ✅ "Create Schedule" button removed from the toolbar
            left: 'prev,next today',
            center: 'title',
            right: '' 
        },
        // ✅ customButtons block fully removed
        selectable: true,
        editable: true,
        height: '100%',
        events: `/api/schedules`, // FullCalendar will auto-add start/end params

        select: function(info) {
            form.reset();
            scheduleIdInput.value = '';
            scheduleDateInput.value = info.startStr.slice(0, 10);
            if (!info.allDay) {
                startTimeInput.value = info.startStr.slice(11, 16);
                endTimeInput.value = info.endStr ? info.endStr.slice(11, 16) : '';
            }
            allDayToggle.checked = info.allDay;
            modal.classList.remove('hidden');
        },

        eventClick: function(info) {
            const event = info.event;
            form.reset();
            scheduleIdInput.value = event.id;
            scheduleTitleInput.value = event.title || '';
            scheduleDateInput.value = event.startStr.slice(0, 10);
            descriptionInput.value = event.extendedProps?.description || '';
            locationInput.value = event.extendedProps?.location || '';
            scheduleLabelInput.value = event.extendedProps?.label || 'Others';
            allDayToggle.checked = !!event.allDay;
            if (!event.allDay) {
                startTimeInput.value = event.startStr.slice(11, 16);
                endTimeInput.value = event.endStr ? event.endStr.slice(11, 16) : '';
            }
            modal.classList.remove('hidden');
        },

        eventDrop: (info) => handleEventUpdate(info.event),
        eventResize: (info) => handleEventUpdate(info.event),
    });

    calendar.render();

    // --- Event Handlers (Submit, Update, Delete) ---
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        const formData = new FormData(this);
        const id = scheduleIdInput.value;
        const url = id ? `/api/schedules/update/${id}` : '/api/schedules/add';
        const method = 'POST';

        try {
            const response = await fetch(url, {
                method: method,
                body: new URLSearchParams(formData),
                headers: { 'X-CSRF-Token': csrfToken }
            });
            const result = await response.json();
            if (result.success) {
                modal.classList.add('hidden');
                calendar.refetchEvents();
            } else {
                alert('Error: ' + (result.error || 'Could not save schedule.'));
            }
        } catch (error) {
            console.error('Save error:', error);
            alert('A network error occurred.');
        }
    });

    async function handleEventUpdate(event) {
        const payload = {
            start: event.start.toISOString(),
            end: event.end ? event.end.toISOString() : null,
            allDay: event.allDay
        };
        try {
            const response = await fetch(`/api/schedules/update/${event.id}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
                body: JSON.stringify(payload)
            });
            if (!response.ok) throw new Error('Update failed');
        } catch (error) {
            console.error('Update error:', error);
            alert('Could not save changes.');
            info.revert();
        }
    }

    window.deleteSchedule = async function(id) {
        if (!id || !confirm('Are you sure you want to delete this schedule?')) return;
        try {
            const response = await fetch(`/api/schedules/${id}`, {
                method: 'DELETE',
                headers: { 'X-CSRF-Token': csrfToken }
            });
            const result = await response.json();
            if (result.success) {
                modal.classList.add('hidden');
                calendar.refetchEvents();
            } else {
                alert('Error: ' + (result.error || 'Could not delete schedule.'));
            }
        } catch (error) {
            console.error('Delete error:', error);
            alert('A network error occurred.');
        }
    }

    // --- View Controls Logic ---
    function setActiveView(activeBtn) {
        [dayViewBtn, weekViewBtn, monthViewBtn, yearViewBtn].forEach(btn => {
            btn.classList.remove('bg-white', 'shadow');
            btn.classList.add('text-gray-600', 'hover:bg-white', 'hover:shadow');
        });
        activeBtn.classList.add('bg-white', 'shadow');
        activeBtn.classList.remove('text-gray-600');
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
        calendar.changeView('yearGrid'); // The plugin uses 'yearGrid'
        setActiveView(yearViewBtn);
    });
});