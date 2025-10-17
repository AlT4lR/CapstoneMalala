// static/js/dynamic_calendar.js
document.addEventListener('DOMContentLoaded', () => {
    const calendarContainer = document.getElementById('main-calendar-container');
    const viewSwitcher = document.getElementById('view-switcher');

    if (!calendarContainer || !viewSwitcher) return;

    let currentDate = new Date();
    let currentView = 'week'; // 'day', 'week', 'month', 'year'

    const monthNames = ["JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"];
    const dayNames = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"];

    function render() {
        calendarContainer.innerHTML = ''; // Clear previous content

        // 1. Render Header (Title & Navigation)
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
        
        // 2. Render Grid based on view
        const grid = document.createElement('div');
        grid.className = 'calendar-grid';
        
        if (currentView === 'month') {
            renderMonthView(grid);
        } else if (currentView === 'week' || currentView === 'day') {
            renderWeekView(grid);
        } else {
             grid.innerHTML = '<div class="p-8 text-center">Year view is not implemented yet.</div>';
        }
        
        calendarContainer.appendChild(grid);

        // 3. Add event listeners
        document.getElementById('cal-prev').addEventListener('click', navigatePrev);
        document.getElementById('cal-next').addEventListener('click', navigateNext);
    }

    function renderMonthView(grid) {
        const year = currentDate.getFullYear();
        const month = currentDate.getMonth();
        document.getElementById('calendar-title').textContent = `${monthNames[month]} ${year}`;
        grid.className += ' month-view';
        
        // Headers
        dayNames.forEach(day => {
            const headerCell = document.createElement('div');
            headerCell.className = 'day-header';
            headerCell.textContent = day;
            grid.appendChild(headerCell);
        });

        // Date cells
        const firstDay = new Date(year, month, 1).getDay();
        const daysInMonth = new Date(year, month + 1, 0).getDate();
        
        for (let i = 0; i < firstDay; i++) {
            grid.innerHTML += '<div class="date-cell empty"></div>';
        }

        for (let day = 1; day <= daysInMonth; day++) {
            const cell = document.createElement('div');
            cell.className = 'date-cell';
            const today = new Date();
            if (day === today.getDate() && month === today.getMonth() && year === today.getFullYear()) {
                cell.classList.add('is-today');
            }
            cell.innerHTML = `<span class="date-number">${day}</span>`;
            grid.appendChild(cell);
        }
    }

    function renderWeekView(grid) {
        const year = currentDate.getFullYear();
        const month = currentDate.getMonth();
        document.getElementById('calendar-title').textContent = `${monthNames[month]} ${year}`;
        grid.className += ' week-view';

        // Get start of the week (Sunday)
        const first = currentDate.getDate() - currentDate.getDay();
        const weekStart = new Date(currentDate.setDate(first));
        
        // Render headers
        grid.innerHTML += '<div class="corner-cell"></div>'; // Top-left empty
        for (let i = 0; i < 7; i++) {
            const dayDate = new Date(weekStart);
            dayDate.setDate(weekStart.getDate() + i);
            const headerCell = document.createElement('div');
            headerCell.className = 'day-header';
            headerCell.innerHTML = `<span>${dayNames[dayDate.getDay()]}</span> <span class="text-lg">${dayDate.getDate()}</span>`;
            grid.appendChild(headerCell);
        }

        // Render time slots and cells
        for (let hour = 8; hour <= 18; hour++) { // 8 AM to 6 PM
            const timeSlot = document.createElement('div');
            timeSlot.className = 'time-slot';
            timeSlot.textContent = `${hour > 12 ? hour - 12 : hour} ${hour >= 12 ? 'PM' : 'AM'}`;
            grid.appendChild(timeSlot);
            
            for (let i = 0; i < 7; i++) {
                const hourCell = document.createElement('div');
                hourCell.className = 'hour-cell';
                
                // Add example event placeholder for demonstration
                const dayDate = new Date(weekStart);
                dayDate.setDate(weekStart.getDate() + i);
                if (dayDate.getDate() === 20 && hour === 16) { // July 20th at 4 PM
                    hourCell.innerHTML = `
                        <div class="event-placeholder">
                            &bull; Delivery of Alcoholic Liquor
                            <div class="text-xs opacity-75">5:30 - 6:00 (work)</div>
                        </div>
                    `;
                }
                grid.appendChild(hourCell);
            }
        }
    }
    
    // --- Navigation ---
    function navigatePrev() {
        if (currentView === 'month') {
            currentDate.setMonth(currentDate.getMonth() - 1);
        } else { // Week or day view
            currentDate.setDate(currentDate.getDate() - 7);
        }
        render();
    }

    function navigateNext() {
        if (currentView === 'month') {
            currentDate.setMonth(currentDate.getMonth() + 1);
        } else { // Week or day view
            currentDate.setDate(currentDate.getDate() + 7);
        }
        render();
    }
    
    // --- View Switching ---
    viewSwitcher.addEventListener('click', (e) => {
        if (e.target.tagName === 'BUTTON') {
            const selectedView = e.target.dataset.view;
            if (selectedView === currentView) return;

            // Update active button style
            viewSwitcher.querySelector('.active-view').classList.remove('active-view');
            e.target.classList.add('active-view');

            currentView = selectedView;
            currentDate = new Date(); // Reset to today when switching views
            render();
        }
    });

    // Initial Render
    render();
});