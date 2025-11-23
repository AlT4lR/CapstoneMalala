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
        // --- MODIFICATION 1: Use Flatpickr instance to set date ---
        flatpickr(scheduleDateInput).setDate(data.date || new Date());
        // --- END MODIFICATION 1 ---
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

    // --- MODIFICATION 2: Debounce Helper Function ---
    const debounce = (callback, delay) => {
        let timeoutId;
        return (...args) => {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => {
                callback(...args);
            }, delay);
        };
    };
    // --- END MODIFICATION 2 ---

    // --- MODIFICATION 3: Raw Event Update Function with Robust Error Handling ---
    async function rawHandleEventUpdate(event) {
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
            
            if (!response.ok) {
                // Attempt to read server-side error message
                const errorResult = await response.json();
                throw new Error(errorResult.error || `Server responded with status ${response.status}`);
            }
            
            calendar.refetchEvents(); 
        } catch (error) {
            console.error('Event Update/Drag Error:', error);
            // Display a more specific error message if available
            alert('Error saving schedule changes: ' + (error.message || 'Network request failed.')); 
            // Revert the event's position/size if update failed
            event.revert(); 
        }
    }
    // --- END MODIFICATION 3 ---
    
    // Create the debounced version of the update function
    const debouncedHandleEventUpdate = debounce(rawHandleEventUpdate, 500); 

    // --- FullCalendar Setup ---
    const calendar = window.calendar = new FullCalendar.Calendar(calendarEl, {
        // --- MODIFICATION 4: Change initial mobile view ---
        initialView: isMobile ? 'dayGridMonth' : 'timeGridWeek',
        // --- END MODIFICATION 4 ---
        headerToolbar: isMobile ? 
            { left: 'prev,next', center: 'title', right: 'today' } : 
            { left: 'prev,next today', center: 'title', right: '' },
        selectable: true,
        editable: true,
        
        // --- START OF FIX: Set height back to 100% to fill the container ---
        height: '100%',
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

        eventDrop: (info) => debouncedHandleEventUpdate(info.event),
        eventResize: (info) => debouncedHandleEventUpdate(info.event),
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
            start: allDay ? `${date}T00:00:00Z` : `${date}T${startTime}:00Z`
        };
        
        // Only include 'end' if it's explicitly set and not an all-day event
        if (endTime && !allDay) {
            payload.end = `${date}T${endTime}:00Z`;
        } else if (isUpdate) {
             // For update, if it was edited to be allDay or if end time was removed, explicitly set end to null
             payload.end = null;
        }

        const url = isUpdate ? `/api/schedules/update/${id}` : '/api/schedules/add';

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
                body: JSON.stringify(payload)
            });
            
            // --- MODIFICATION 5: Robust Error Handling for submit/save ---
            const result = await response.json();
            
            if (response.ok) {
                closeModal();
                calendar.refetchEvents();
            } else {
                alert('Error: ' + (result.error || 'Could not save schedule.'));
            }
            // --- END MODIFICATION 5 ---

        } catch (error) {
            console.error('Save error:', error);
            alert('A network error occurred. Please check console for details.');
        }
    });

    
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
                
                if (response.ok) {
                    closeModal();
                    calendar.refetchEvents();
                } else {
                    alert('Error: ' + (result.error || 'The schedule could not be deleted.'));
                }
            } catch (error) {
                console.error('Delete error:', error);
                alert('A network error occurred. Please check your connection or server logs.');
            }
        });
    };

    // --- MODIFICATION 6: Ensure listener is attached for delete button ---
    if (deleteBtn) {
        deleteBtn.addEventListener('click', () => {
            const id = scheduleIdInput.value;
            if (id) {
                window.deleteSchedule(id);
            }
        });
    }
    // --- END MODIFICATION 6 ---

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