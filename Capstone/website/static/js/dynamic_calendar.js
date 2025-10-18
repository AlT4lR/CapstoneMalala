// static/js/dynamic_calendar.js
document.addEventListener('DOMContentLoaded', () => {
    // --- DOM ELEMENT REFERENCES ---
    const calendarContainer = document.getElementById('main-calendar-container');
    const viewSwitcher = document.getElementById('view-switcher');
    
    // Updated Modal References
    const modalBackdrop = document.getElementById('schedule-modal-backdrop');
    const form = document.getElementById('schedule-form');
    const scheduleIdInput = document.getElementById('schedule-id');
    const scheduleTitleInput = document.getElementById('schedule-title');
    const scheduleDateInput = document.getElementById('schedule-date');
    const startTimeInput = document.getElementById('schedule-start-time');
    const endTimeInput = document.getElementById('schedule-end-time');
    const allDayToggle = document.getElementById('all-day-toggle');
    const descriptionInput = document.getElementById('schedule-description');
    const locationInput = document.getElementById('schedule-location');
    const createScheduleBtn = document.getElementById('create-schedule-btn');
    const deleteBtn = document.getElementById('delete-schedule-btn');

    if (!calendarContainer || !viewSwitcher || !modalBackdrop) return;

    // --- STATE MANAGEMENT ---
    let currentDate = new Date();
    // --- START OF MODIFICATION: Default view is now week ---
    let currentView = 'week';
    // --- END OF MODIFICATION ---
    let events = [ // Sample data
        {
            id: 1,
            title: 'Delivery of Alcoholic Liquor',
            start: new Date(2025, 9, 22, 15, 30), // Oct 22, 2025, 3:30 PM
            end: new Date(2025, 9, 22, 18, 0),   // Oct 22, 2025, 6:00 PM
            description: '(notes)',
            location: 'Main Warehouse',
            allDay: false
        },
        {
            id: 2,
            title: 'Team Meeting',
            start: new Date(2025, 9, 24, 10, 0), // Oct 24, 2025, 10:00 AM
            end: new Date(2025, 9, 24, 11, 0),   // Oct 24, 2025, 11:00 AM
            description: 'Weekly sync up',
            location: 'Conference Room 1',
            allDay: false
        },
        {
            id: 3,
            title: 'Project Deadline',
            start: new Date(2025, 9, 15),
            end: new Date(2025, 9, 15),
            description: 'Final submission for Q3 report',
            location: 'Online',
            allDay: true
        }
    ];

    const monthNames = ["JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"];
    const dayNames = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"];

    // --- MODAL & FORM LOGIC ---
    function openModal(data = {}) {
        form.reset();
        scheduleIdInput.value = data.id || '';
        scheduleTitleInput.value = data.title || '';
        descriptionInput.value = data.description || '';
        locationInput.value = data.location || '';
        allDayToggle.checked = data.allDay || false;

        const startDate = data.start ? new Date(data.start) : new Date();
        scheduleDateInput.valueAsDate = startDate;

        if (!data.allDay) {
            startTimeInput.value = data.start ? startDate.toTimeString().slice(0, 5) : '';
            endTimeInput.value = data.end ? new Date(data.end).toTimeString().slice(0, 5) : '';
        }

        // Show/hide delete button
        deleteBtn.classList.toggle('hidden', !data.id);

        modalBackdrop.classList.remove('hidden');
        setTimeout(() => modalBackdrop.classList.add('active'), 10);
    }
    
    function closeModal() {
        modalBackdrop.classList.remove('active');
        modalBackdrop.addEventListener('transitionend', () => {
            modalBackdrop.classList.add('hidden');
        }, { once: true });
    }
    
    function saveEvent(e) {
        e.preventDefault();
        const id = scheduleIdInput.value ? Number(scheduleIdInput.value) : null;
        const date = scheduleDateInput.value;
        const start = `${date}T${startTimeInput.value || '00:00'}`;
        const end = `${date}T${endTimeInput.value || '23:59'}`;

        const eventData = {
            id: id || Date.now(),
            title: scheduleTitleInput.value,
            start: new Date(start),
            end: new Date(end),
            allDay: allDayToggle.checked,
            description: descriptionInput.value,
            location: locationInput.value,
        };

        if (id) {
            events = events.map(ev => ev.id === id ? eventData : ev);
        } else {
            events.push(eventData);
        }

        closeModal();
        render();
    }
    
    // --- RENDERING LOGIC ---
    function render() {
        calendarContainer.innerHTML = '';

        const header = document.createElement('div');
        header.className = 'calendar-header';
        header.innerHTML = `
            <h2 id="calendar-title" class="calendar-title"></h2>
            <div class="calendar-nav">
                <button id="cal-prev">&lt;</button>
                <button id="cal-next">&gt;</button>
            </div>
        `;
        calendarContainer.appendChild(header);
        
        const grid = document.createElement('div');
        
        if (currentView === 'month') renderMonthView(grid);
        else if (currentView === 'week') renderWeekView(grid);
        else grid.innerHTML = `<div class="p-8 text-center col-span-full">${currentView.charAt(0).toUpperCase() + currentView.slice(1)} view is not implemented yet.</div>`;
        
        calendarContainer.appendChild(grid);

        document.getElementById('cal-prev').addEventListener('click', navigatePrev);
        document.getElementById('cal-next').addEventListener('click', navigateNext);
    }
    
    function renderMonthView(grid) {
        const year = currentDate.getFullYear();
        const month = currentDate.getMonth();
        document.getElementById('calendar-title').textContent = `${monthNames[month]} ${year}`;
        grid.className = 'calendar-grid month-view';

        // 1. Add day headers
        dayNames.forEach(day => {
            const headerCell = document.createElement('div');
            headerCell.className = 'day-header';
            headerCell.textContent = day;
            grid.appendChild(headerCell);
        });

        // 2. Calculate dates
        const firstDayOfMonth = new Date(year, month, 1).getDay();
        const daysInMonth = new Date(year, month + 1, 0).getDate();
        const today = new Date();

        // 3. Add padding cells for days before the 1st
        for (let i = 0; i < firstDayOfMonth; i++) {
            grid.appendChild(document.createElement('div'));
        }

        // 4. Add a cell for each day of the month
        for (let day = 1; day <= daysInMonth; day++) {
            const isToday = day === today.getDate() && month === today.getMonth() && year === today.getFullYear();
            const cell = document.createElement('div');
            cell.className = 'date-cell';
            if (isToday) cell.classList.add('is-today');
            
            // Store date for easy event placement
            cell.dataset.date = new Date(year, month, day).toISOString().slice(0, 10);

            cell.innerHTML = `
                <div class="date-number">${day}</div>
                <div class="events-container custom-scrollbar"></div>
            `;
            grid.appendChild(cell);
        }

        // 5. Render events for the current month
        const monthStart = new Date(year, month, 1, 0, 0, 0);
        const monthEnd = new Date(year, month, daysInMonth, 23, 59, 59);

        const eventsForMonth = events.filter(ev => {
            const evStart = new Date(ev.start);
            return evStart >= monthStart && evStart <= monthEnd;
        });

        eventsForMonth.forEach(event => {
            const eventDateStr = new Date(event.start).toISOString().slice(0, 10);
            const cell = grid.querySelector(`.date-cell[data-date="${eventDateStr}"]`);
            if (cell) {
                const eventsContainer = cell.querySelector('.events-container');
                const eventEl = document.createElement('div');
                eventEl.className = 'event';
                eventEl.textContent = event.title;
                eventEl.addEventListener('click', (e) => {
                    e.stopPropagation(); // Prevent opening a new event modal
                    openModal(event);
                });
                eventsContainer.appendChild(eventEl);
            }
        });
    }

    // --- START OF MODIFICATION: Implemented Week View ---
    function renderWeekView(grid) {
        const year = currentDate.getFullYear();
        const month = currentDate.getMonth();
        document.getElementById('calendar-title').textContent = `${monthNames[month]} ${year}`;
        grid.className = 'calendar-grid week-view';

        const HOUR_HEIGHT_REM = 4; // Height of one hour slot in rem
        const START_HOUR = 8;
        const END_HOUR = 18; // 6 PM

        // 1. Calculate week dates
        const weekStart = new Date(currentDate);
        weekStart.setDate(weekStart.getDate() - weekStart.getDay());
        weekStart.setHours(0, 0, 0, 0);
        const weekEnd = new Date(weekStart);
        weekEnd.setDate(weekEnd.getDate() + 7);

        // 2. Set grid row structure
        grid.style.gridTemplateRows = `auto repeat(${END_HOUR - START_HOUR + 1}, ${HOUR_HEIGHT_REM}rem)`;

        // 3. Create headers and grid cells
        grid.appendChild(document.createElement('div')).className = 'corner-cell'; // Top-left corner
        for (let i = 0; i < 7; i++) {
            const dayDate = new Date(weekStart);
            dayDate.setDate(weekStart.getDate() + i);
            const headerCell = document.createElement('div');
            headerCell.className = 'day-header';
            headerCell.innerHTML = `<div>${dayNames[dayDate.getDay()]}</div><div class="text-lg">${dayDate.getDate()}</div>`;
            grid.appendChild(headerCell);
        }

        // 4. Create time slots and the background grid cells
        for (let hour = START_HOUR; hour <= END_HOUR; hour++) {
            const timeSlot = document.createElement('div');
            timeSlot.className = 'time-slot';
            timeSlot.textContent = `${hour > 12 ? hour - 12 : hour} ${hour >= 12 ? 'PM' : 'AM'}`;
            grid.appendChild(timeSlot);
            for (let day = 0; day < 7; day++) {
                grid.appendChild(document.createElement('div')); // These are the empty cells for grid lines
            }
        }

        // 5. Filter and render events
        const eventsForWeek = events.filter(ev => ev.start < weekEnd && ev.end > weekStart && !ev.allDay);
        
        eventsForWeek.forEach(event => {
            const start = new Date(event.start);
            const end = new Date(event.end);

            // Skip events outside the displayed time range
            if (start.getHours() > END_HOUR || end.getHours() < START_HOUR) return;
            
            const eventDay = start.getDay();
            const startMinutes = (start.getHours() * 60) + start.getMinutes();
            const endMinutes = (end.getHours() * 60) + end.getMinutes();
            const durationMinutes = endMinutes - startMinutes;

            const topOffsetMinutes = startMinutes - (START_HOUR * 60);
            
            const top = (topOffsetMinutes / 60) * HOUR_HEIGHT_REM;
            const height = (durationMinutes / 60) * HOUR_HEIGHT_REM;

            const eventEl = document.createElement('div');
            eventEl.className = 'event';
            eventEl.style.gridColumn = `${eventDay + 2}`;
            // --- START OF FIX: Removed the conflicting gridRow style ---
            eventEl.style.top = `${top}rem`;
            eventEl.style.height = `${height}rem`;
            // --- END OF FIX ---

            const formatTime = (date) => date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });

            eventEl.innerHTML = `
                <div class="font-bold">&bull; ${event.title}</div>
                <div class="text-xs opacity-75">${formatTime(start)} - ${formatTime(end)}</div>
                <div class="text-xs opacity-75">${event.description || ''}</div>
            `;
            eventEl.addEventListener('click', () => openModal(event));

            grid.appendChild(eventEl);
        });
    }
    // --- END OF MODIFICATION ---

    // --- NAVIGATION & EVENT LISTENERS ---
    function navigatePrev() {
        if (currentView === 'month') currentDate.setMonth(currentDate.getMonth() - 1);
        else currentDate.setDate(currentDate.getDate() - 7);
        render();
    }

    function navigateNext() {
        if (currentView === 'month') currentDate.setMonth(currentDate.getMonth() + 1);
        else currentDate.setDate(currentDate.getDate() + 7);
        render();
    }
    
    viewSwitcher.addEventListener('click', (e) => {
        if (e.target.tagName === 'BUTTON') {
            const selectedView = e.target.dataset.view;
            if (selectedView === currentView) return;
            const currentActive = viewSwitcher.querySelector('.active-view');
            if (currentActive) currentActive.classList.remove('active-view');
            e.target.classList.add('active-view');
            currentView = selectedView;
            currentDate = new Date(); // Reset to today when switching view
            render();
        }
    });

    // --- INITIALIZATION ---
    // Set default active view button
    const defaultActiveButton = viewSwitcher.querySelector(`[data-view="${currentView}"]`);
    if(defaultActiveButton) defaultActiveButton.classList.add('active-view');

    form.addEventListener('submit', saveEvent);
    createScheduleBtn.addEventListener('click', () => openModal());
    document.getElementById('discard-schedule-btn').addEventListener('click', closeModal);
    document.getElementById('cancel-schedule-btn').addEventListener('click', closeModal);
    deleteBtn.addEventListener('click', () => {
        const id = scheduleIdInput.value;
        if(confirm('Are you sure you want to delete this schedule?')) {
            events = events.filter(ev => ev.id !== Number(id));
            closeModal();
            render();
        }
    });
    
    window.mainCalendar = {
        goToDate: (date) => {
            currentDate = new Date(date);
            render();
        }
    };

    render();
});