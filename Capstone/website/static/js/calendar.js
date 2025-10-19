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

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';

    const labelColors = {
        'Office': '#3b82f6',
        'Meetings': '#8b5cf6',
        'Events': '#ec4899',
        'Personal': '#f59e0b',
        'Others': '#6b7280'
    };

    // ✅ START OF MODIFICATION: Animation Helper Functions
    const openModal = () => {
        modal.classList.remove('hidden');
        // Slight delay to allow the browser to register the removal of 'hidden' before adding 'active'
        setTimeout(() => modal.classList.add('active'), 10);
    };

    const closeModal = () => {
        modal.classList.remove('active');
        // Wait for the CSS transition to finish before hiding the element completely
        modal.addEventListener('transitionend', () => {
            modal.classList.add('hidden');
        }, { once: true });
    };
    // ✅ END OF MODIFICATION

    // --- FullCalendar Setup ---
    const calendar = window.calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'timeGridWeek',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: ''
        },
        selectable: true,
        editable: true,
        height: '100%',
        events: `/api/schedules`,

        eventDidMount: function(info) {
            const label = info.event.extendedProps.label || 'Others';
            const color = labelColors[label] || labelColors['Others'];
            if (color) {
                info.el.style.backgroundColor = color;
                info.el.style.borderColor = color;
            }
        },

        select: function(info) {
            form.reset();
            scheduleIdInput.value = '';
            scheduleDateInput.value = info.startStr.slice(0, 10);
            if (!info.allDay) {
                startTimeInput.value = info.startStr.slice(11, 16);
                endTimeInput.value = info.endStr ? info.endStr.slice(11, 16) : '';
            }
            allDayToggle.checked = info.allDay;
            scheduleLabelInput.value = 'Others';
            openModal(); // ✅ Use helper
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
            openModal(); // ✅ Use helper
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

        try {
            let response;

            if (id) {
                // UPDATE (send as JSON)
                const url = `/api/schedules/update/${id}`;
                const payload = {
                    title: formData.get('title'),
                    description: formData.get('description'),
                    location: formData.get('location'),
                    label: formData.get('label'),
                    allDay: formData.has('all_day')
                };

                const date = formData.get('date');
                if (payload.allDay) {
                    payload.start = new Date(date + 'T00:00:00Z').toISOString();
                } else {
                    const startTime = formData.get('start_time') || '00:00';
                    const endTime = formData.get('end_time');
                    payload.start = new Date(`${date}T${startTime}:00Z`).toISOString();
                    if (endTime) {
                        payload.end = new Date(`${date}T${endTime}:00Z`).toISOString();
                    }
                }

                response = await fetch(url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
                    body: JSON.stringify(payload)
                });
            } else {
                // CREATE (send as form-data)
                const url = '/api/schedules/add';
                response = await fetch(url, {
                    method: 'POST',
                    body: new URLSearchParams(formData),
                    headers: { 'X-CSRF-Token': csrfToken }
                });
            }

            const result = await response.json();
            if (result.success) {
                closeModal(); // ✅ Use helper
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
            allDay: event.allDay,
            title: event.title,
            description: event.extendedProps.description,
            location: event.extendedProps.location,
            label: event.extendedProps.label
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
        if (!id) return;
        const event = calendar.getEventById(id);
        const eventTitle = event ? event.title : 'this schedule';
        
        window.showCustomConfirm(`Are you sure you want to delete "${eventTitle}"?`, async () => {
            try {
                const response = await fetch(`/api/schedules/${id}`, {
                    method: 'DELETE',
                    headers: { 'X-CSRF-Token': csrfToken }
                });
                const result = await response.json();
                if (result.success) {
                    closeModal(); // ✅ Use helper
                    calendar.refetchEvents();
                } else {
                    alert('Error: ' + (result.error || 'Could not delete schedule.'));
                }
            } catch (error) {
                console.error('Delete error:', error);
                alert('A network error occurred.');
            }
        });
    };

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
        calendar.changeView('yearGrid');
        setActiveView(yearViewBtn);
    });
});