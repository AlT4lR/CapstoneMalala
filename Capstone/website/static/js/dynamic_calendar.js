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
    let currentView = 'week';
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

        modalBackdrop.classList.add('active');
    }
    
    function closeModal() {
        modalBackdrop.classList.remove('active');
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
        grid.className = 'calendar-grid';
        
        if (currentView === 'month') renderMonthView(grid);
        else if (currentView === 'week') renderWeekView(grid);
        else grid.innerHTML = `<div class="p-8 text-center col-span-full">${currentView.charAt(0).toUpperCase() + currentView.slice(1)} view is not implemented yet.</div>`;
        
        calendarContainer.appendChild(grid);

        document.getElementById('cal-prev').addEventListener('click', navigatePrev);
        document.getElementById('cal-next').addEventListener('click', navigateNext);
    }
    
    function renderMonthView(grid) {
        // ... (month view rendering) ...
        grid.innerHTML = '<div class="p-8 text-center col-span-7">Month view not fully implemented.</div>';
        document.getElementById('calendar-title').textContent = 'MONTH VIEW';
    }

    function renderWeekView(grid) {
        const year = currentDate.getFullYear();
        const month = currentDate.getMonth();
        document.getElementById('calendar-title').textContent = `${monthNames[month]} ${year}`;
        grid.className += ' week-view';

        const weekStart = new Date(currentDate);
        weekStart.setDate(weekStart.getDate() - weekStart.getDay());
        weekStart.setHours(0,0,0,0);

        const weekEnd = new Date(weekStart);
        weekEnd.setDate(weekEnd.getDate() + 7);

        grid.innerHTML += '<div class="corner-cell"></div>';
        for (let i = 0; i < 7; i++) {
            const dayDate = new Date(weekStart);
            dayDate.setDate(weekStart.getDate() + i);
            const headerCell = document.createElement('div');
            headerCell.className = 'day-header';
            headerCell.innerHTML = `<span>${dayNames[dayDate.getDay()]}</span> <span class="text-lg">${dayDate.getDate()}</span>`;
            grid.appendChild(headerCell);
        }

        const START_HOUR = 8, END_HOUR = 18;
        const totalRows = (END_HOUR - START_HOUR) + 1;
        grid.style.gridTemplateRows = `auto repeat(${totalRows}, 1fr)`;
        
        for (let hour = START_HOUR; hour <= END_HOUR; hour++) {
            const timeSlot = document.createElement('div');
            timeSlot.className = 'time-slot';
            timeSlot.textContent = `${hour > 12 ? hour - 12 : hour} ${hour >= 12 ? 'PM' : 'AM'}`;
            grid.appendChild(timeSlot);
            
            for (let day = 0; day < 7; day++) {
                const hourCell = document.createElement('div');
                hourCell.className = 'hour-cell';
                grid.appendChild(hourCell);
            }
        }
        
        const eventsForWeek = events.filter(ev => ev.start < weekEnd && ev.end > weekStart);
        
        eventsForWeek.forEach(event => {
            if (event.allDay) return; // All-day events would be handled separately
            
            const eventDay = event.start.getDay();
            const startHour = event.start.getHours();
            const startMinutes = event.start.getMinutes();
            const endHour = event.end.getHours();
            const endMinutes = event.end.getMinutes();

            // Calculate grid row positions
            const startRow = (startHour - START_HOUR) * 2 + (startMinutes >= 30 ? 2 : 1) + 1; // +1 for header row
            const endRow = (endHour - START_HOUR) * 2 + (endMinutes > 0 ? (endMinutes > 30 ? 2 : 1) : 0) + 1;

            const gridColumn = eventDay + 2; // +1 for time col, +1 for 1-based index
            
            const eventEl = document.createElement('div');
            eventEl.className = 'event';
            eventEl.style.gridColumn = `${gridColumn}`;
            eventEl.style.gridRow = `${startRow} / ${endRow}`;
            
            const topOffset = (startMinutes / 60) * 100;
            const bottomOffset = ( (60 - endMinutes) / 60) * 100;
            
            eventEl.style.top = `calc(${(startMinutes / 60) * 100}%)`;
            eventEl.style.bottom = `calc(${((60 - endMinutes) / 60) * 100}%)`;

            eventEl.innerHTML = `
                &bull; ${event.title}
                <div class="text-xs opacity-75">${event.start.toTimeString().slice(0,5)} - ${event.end.toTimeString().slice(0,5)}</div>
            `;
            eventEl.addEventListener('click', () => openModal(event));

            grid.appendChild(eventEl);
        });
    }

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
            viewSwitcher.querySelector('.active-view').classList.remove('active-view');
            e.target.classList.add('active-view');
            currentView = selectedView;
            currentDate = new Date();
            render();
        }
    });

    // --- INITIALIZATION ---
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