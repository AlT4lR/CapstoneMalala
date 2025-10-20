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

    // --- START OF MODIFICATION: Mobile Sidebar Refs ---
    const mobileControlsBtn = document.getElementById('mobile-controls-btn');
    const sidebar = document.getElementById('schedule-controls');
    const overlay = document.getElementById('sidebar-overlay');
    const closeSidebarBtn = document.getElementById('close-sidebar-btn');
    // --- END OF MODIFICATION ---

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';

    const labelColors = {
        'Office': '#3b82f6',
        'Meetings': '#8b5cf6',
        'Events': '#ec4899',
        'Personal': '#f59e0b',
        'Others': '#6b7280'
    };
    
    // --- START OF MODIFICATION: Responsive Calendar Config ---
    const isMobile = window.innerWidth < 768;

    // --- FullCalendar Setup ---
    const calendar = window.calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: isMobile ? 'timeGridDay' : 'timeGridWeek',
        headerToolbar: isMobile ? 
            { left: 'prev,next', center: 'title', right: 'today' } : 
            { left: 'prev,next today', center: 'title', right: '' },
        selectable: true,
        editable: true,
        height: '100%',
        events: `/api/schedules`,
    // --- END OF MODIFICATION ---

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
        const isUpdate = !!id;

        const date = formData.get('date');
        const allDay = formData.has('all_day');
        const startTime = formData.get('start_time') || '00:00';
        const endTime = formData.get('end_time');

        const payload = {
            title: formData.get('title'),
            description: formData.get('description'),
            location: formData.get('location'),
            label: formData.get('label'),
            allDay: allDay,
            start: allDay ? new Date(`${date}T00:00:00`).toISOString() : new Date(`${date}T${startTime}:00`).toISOString(),
            end: allDay ? null : (endTime ? new Date(`${date}T${endTime}:00`).toISOString() : null)
        };

        const url = isUpdate ? `/api/schedules/update/${id}` : '/api/schedules/add';

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
                body: JSON.stringify(payload)
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
                    modal.classList.add('hidden');
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
        calendar.changeView('listYear'); 
        setActiveView(yearViewBtn);
    });

    // --- START OF MODIFICATION: Mobile Sidebar Logic ---
    function openSidebar() {
        if(sidebar && overlay) {
            sidebar.classList.remove('-translate-x-full');
            overlay.classList.remove('hidden');
        }
    }
    function closeSidebar() {
        if(sidebar && overlay) {
            sidebar.classList.add('-translate-x-full');
            overlay.classList.add('hidden');
        }
    }

    if(mobileControlsBtn) mobileControlsBtn.addEventListener('click', openSidebar);
    if(closeSidebarBtn) closeSidebarBtn.addEventListener('click', closeSidebar);
    if(overlay) overlay.addEventListener('click', closeSidebar);
    // --- END OF MODIFICATION ---
});