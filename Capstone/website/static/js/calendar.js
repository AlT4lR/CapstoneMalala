// static/js/calendar.js
document.addEventListener('DOMContentLoaded', function() {
    const calendarEl = document.getElementById('calendar');
    if (!calendarEl) return;

    // --- Modal & Form Element Refs ---
    const modal = document.getElementById('create-schedule-modal');
    const modalTitle = document.getElementById('modal-title');
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
    const deleteBtn = document.getElementById('delete-schedule-btn');
    const cancelBtn = document.getElementById('cancel-schedule-btn');
    const discardBtn = document.getElementById('discard-schedule-btn');

    // --- View Buttons ---
    const dayViewBtn = document.getElementById('day-view-btn');
    const weekViewBtn = document.getElementById('week-view-btn');
    const monthViewBtn = document.getElementById('month-view-btn');
    const yearViewBtn = document.getElementById('year-view-btn');

    // --- Mobile Sidebar Refs ---
    const mobileControlsBtn = document.getElementById('mobile-controls-btn');
    const sidebar = document.getElementById('schedule-controls');
    const overlay = document.getElementById('sidebar-overlay');
    const closeSidebarBtn = document.getElementById('close-sidebar-btn');

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';

    const labelColors = {
        'Office': '#3b82f6', 'Meetings': '#8b5cf6', 'Events': '#ec4899',
        'Personal': '#f59e0b', 'Others': '#6b7280'
    };
    
    const isMobile = window.innerWidth < 768;

    const openModal = (data = {}) => {
        form.reset();
        
        scheduleIdInput.value = data.id || '';
        scheduleTitleInput.value = data.title || '';
        scheduleDateInput.value = data.date || new Date().toISOString().slice(0, 10);
        startTimeInput.value = data.startTime || '';
        endTimeInput.value = data.endTime || '';
        allDayToggle.checked = data.allDay || false;
        descriptionInput.value = data.description || '';
        locationInput.value = data.location || '';
        scheduleLabelInput.value = data.label || 'Others';

        if (data.id) {
            modalTitle.textContent = 'Edit Schedule';
            deleteBtn.classList.remove('hidden');
        } else {
            modalTitle.textContent = 'Create Schedule';
            deleteBtn.classList.add('hidden');
        }

        modal.classList.remove('hidden');
        setTimeout(() => modal.classList.add('active'), 10);
    };

    const closeModal = () => {
        modal.classList.remove('active');
        modal.addEventListener('transitionend', () => modal.classList.add('hidden'), { once: true });
    };

    if (cancelBtn) cancelBtn.addEventListener('click', closeModal);
    if (discardBtn) discardBtn.addEventListener('click', closeModal);
    if (modal) modal.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });


    // --- FullCalendar Setup ---
    const calendar = window.calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: isMobile ? 'timeGridDay' : 'timeGridWeek',
        headerToolbar: isMobile ? 
            { left: 'prev,next', center: 'title', right: 'today' } : 
            { left: 'prev,next today', center: 'title', right: '' },
        selectable: true,
        editable: true,
        
        // --- START OF FIX: Make calendar height responsive to content ---
        height: 'auto',
        // --- END OF FIX ---

        events: `/api/schedules`,
        eventTimeFormat: {
            hour: 'numeric',
            minute: '2-digit',
            meridiem: 'short'
        },

        eventDidMount: function(info) {
            const label = info.event.extendedProps.label || 'Others';
            const color = labelColors[label] || labelColors['Others'];
            if (color) {
                info.el.style.backgroundColor = color;
                info.el.style.borderColor = color;
            }
        },

        select: function(info) {
            openModal({
                date: info.startStr.slice(0, 10),
                startTime: info.allDay ? '' : info.startStr.slice(11, 16),
                endTime: info.allDay ? '' : (info.endStr ? info.endStr.slice(11, 16) : ''),
                allDay: info.allDay
            });
        },

        eventClick: function(info) {
            const event = info.event;
            openModal({
                id: event.id,
                title: event.title,
                date: event.startStr.slice(0, 10),
                startTime: event.allDay ? '' : event.startStr.slice(11, 16),
                endTime: event.allDay ? '' : (event.endStr ? event.endStr.slice(11, 16) : ''),
                allDay: event.allDay,
                description: event.extendedProps.description,
                location: event.extendedProps.location,
                label: event.extendedProps.label
            });
        },

        eventDrop: (info) => handleEventUpdate(info.event),
        eventResize: (info) => handleEventUpdate(info.event),
    });

    calendar.render();

    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        const id = scheduleIdInput.value;
        const isUpdate = !!id;
        const allDay = allDayToggle.checked;
        const date = scheduleDateInput.value;
        const startTime = startTimeInput.value || '00:00';
        const endTime = endTimeInput.value;

        const payload = {
            title: scheduleTitleInput.value,
            description: descriptionInput.value,
            location: locationInput.value,
            label: scheduleLabelInput.value,
            allDay: allDay,
            date: date,
            notification_method: 'none',
            start: allDay ? `${date}T00:00:00Z` : `${date}T${startTime}:00Z`
        };
        
        if (endTime && !allDay) {
            payload.end = `${date}T${endTime}:00Z`;
        }

        const url = isUpdate ? `/api/schedules/update/${id}` : '/api/schedules/add';

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
                body: JSON.stringify(payload)
            });
            if (!response.ok) throw new Error('Server error');
            const result = await response.json();
            if (result.success) {
                closeModal();
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
                    closeModal();
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

    // --- View Controls & Mobile Sidebar Logic ---
    function setActiveView(activeBtn) {
        [dayViewBtn, weekViewBtn, monthViewBtn, yearViewBtn].forEach(btn => {
            btn.classList.remove('bg-white', 'shadow');
            btn.classList.add('text-gray-600', 'hover:bg-white', 'hover:shadow');
        });
        activeBtn.classList.add('bg-white', 'shadow');
        activeBtn.classList.remove('text-gray-600');
    }

    dayViewBtn.addEventListener('click', () => { calendar.changeView('timeGridDay'); setActiveView(dayViewBtn); });
    weekViewBtn.addEventListener('click', () => { calendar.changeView('timeGridWeek'); setActiveView(weekViewBtn); });
    monthViewBtn.addEventListener('click', () => { calendar.changeView('dayGridMonth'); setActiveView(monthViewBtn); });
    yearViewBtn.addEventListener('click', () => { calendar.changeView('listYear'); setActiveView(yearViewBtn); });

    function openSidebar() { if(sidebar && overlay) { sidebar.classList.remove('-translate-x-full'); overlay.classList.remove('hidden'); } }
    function closeSidebar() { if(sidebar && overlay) { sidebar.classList.add('-translate-x-full'); overlay.classList.add('hidden'); } }
    if(mobileControlsBtn) mobileControlsBtn.addEventListener('click', openSidebar);
    if(closeSidebarBtn) closeSidebarBtn.addEventListener('click', closeSidebar);
    if(overlay) overlay.addEventListener('click', closeSidebar);
});