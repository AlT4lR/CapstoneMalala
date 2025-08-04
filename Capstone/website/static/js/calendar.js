// static/js/calendar.js

document.addEventListener('DOMContentLoaded', function() {
    // --- Calendar Logic Initialization ---
    // Check if the necessary calendar elements exist before proceeding
    if (document.getElementById('create-schedule-btn') && 
        document.getElementById('mini-cal-month-year') &&
        document.getElementById('main-cal-header-month-year')) {
        
        let currentMainDate; // Tracks the date currently displayed in the main calendar header
        let currentView = 'Week'; // Default view: 'Week', 'Month', 'Day', 'Year'

        const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
        const dayNames = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"];

        const miniCalMonthYearEl = document.getElementById('mini-cal-month-year');
        const miniCalendarGridEl = document.getElementById('mini-calendar-grid');
        const miniCalPrevMonthBtn = document.getElementById('mini-cal-prev-month');
        const miniCalNextMonthBtn = document.getElementById('mini-cal-next-month');

        const mainCalHeaderMonthYearEl = document.getElementById('main-cal-header-month-year');
        const monthViewEl = document.getElementById('month-view');
        const monthGridDaysEl = document.getElementById('month-grid-days');
        const weekViewEl = document.getElementById('week-view');
        const weekHeaderDayEls = Array.from({length: 7}, (_, i) => document.getElementById(`week-header-day-${i}`));
        const weekGridTimeSlotsEl = document.getElementById('week-grid-time-slots');
        const dayViewEl = document.getElementById('day-view');
        const dayHeaderDateEl = document.getElementById('day-header-date');
        const dayGridTimeSlotsEl = document.getElementById('day-grid-time-slots');
        const yearViewEl = document.getElementById('year-view');

        const viewButtons = document.querySelectorAll('.view-button');
        const createScheduleBtn = document.getElementById('create-schedule-btn');
        const createScheduleModal = document.getElementById('create-schedule-modal');
        const closeScheduleModalBtn = document.getElementById('close-schedule-modal');
        const eventCategorySelect = document.getElementById('event-category');
        const categoryListEl = document.getElementById('category-list');
        const addCategoryBtn = document.getElementById('add-category-btn');

        const eventDetailsModal = document.getElementById('event-details-modal');
        const closeEventDetailsModalBtn = document.getElementById('close-event-details-modal');
        const detailsEventTitleEl = document.getElementById('details-event-title');
        const detailsEventCategoryEl = document.getElementById('details-event-category');
        const detailsEventTimeEl = document.getElementById('details-event-time');
        const detailsEventNotesEl = document.getElementById('details-event-notes');

        const categoryColors = {
            'Office': 'bg-category-office',
            'Meetings': 'bg-category-meetings',
            'Events': 'bg-category-events',
            'Personal': 'bg-category-personal',
            'Others': 'bg-category-others',
        };
        
        // --- Initial Date Setup (Uses global variable from schedules.html) ---
        // Ensure FLASK_INITIAL_DATE_ISO is available globally
        currentMainDate = new Date(FLASK_INITIAL_DATE_ISO);
        currentMainDate.setHours(0, 0, 0, 0); // Normalize to start of day

        let miniCalMonth = currentMainDate.getMonth();
        let miniCalYear = currentMainDate.getFullYear();

        // --- Helper Functions ---
        function getWeekStartDate(date) {
            let day = date.getDay(); // 0 = Sunday, 1 = Monday, etc.
            let diff = date.getDate() - day; // Adjust date to Sunday
            return new Date(date.getFullYear(), date.getMonth(), diff);
        }

        function formatTime(dateString) {
            const date = new Date(dateString);
            return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        }

        function formatDateForDisplay(date) {
            return date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
        }

        function getCategoryColorClass(category) {
            const baseClass = 'px-2 py-1 rounded-full text-xs font-semibold';
            return `${baseClass} ${categoryColors[category] || 'bg-gray-500'}`;
        }

        async function fetchSchedules(start, end) {
            try {
                // Use the overridden fetch which includes CSRF token and Content-Type
                const response = await fetch(`/api/schedules?start=${start.toISOString()}&end=${end.toISOString()}`); 
                if (!response.ok) {
                    const errorData = await response.json();
                    console.error("Error fetching schedules:", errorData.error);
                    return [];
                }
                const schedules = await response.json();
                return schedules.map(s => ({
                    ...s,
                    start_time: new Date(s.start_time),
                    end_time: new Date(s.end_time)
                }));
            } catch (error) {
                console.error("Network or parsing error fetching schedules:", error);
                return [];
            }
        }

        async function fetchCategories() {
            try {
                // Ensure FLASK_INITIAL_CATEGORIES_JSON is correctly parsed
                const categories = JSON.parse(FLASK_INITIAL_CATEGORIES_JSON); 
                if (categories && categories.length > 0) {
                    return categories;
                }
                return ['Office', 'Meetings', 'Events', 'Personal', 'Others']; // Fallback
            } catch (error) {
                console.error("Error parsing initial categories JSON:", error);
                return ['Office', 'Meetings', 'Events', 'Personal', 'Others']; // Fallback
            }
        }

        async function populateCategorySelectAndList(initialCategories = null) {
            const categories = initialCategories || await fetchCategories();
            
            eventCategorySelect.innerHTML = '';
            categoryListEl.innerHTML = '';

            categories.forEach(cat => {
                const option = document.createElement('option');
                option.value = cat;
                option.textContent = cat;
                eventCategorySelect.appendChild(option);

                const label = document.createElement('label');
                label.className = 'flex items-center';
                label.innerHTML = `
                    <input type="radio" name="sidebar-category" value="${cat}" class="form-radio h-4 w-4 text-custom-green-active">
                    <span class="ml-2">${cat}</span>
                `;
                categoryListEl.appendChild(label);
            });
        }

        // --- Render Mini Calendar ---
        function renderMiniCalendar() {
            miniCalendarGridEl.innerHTML = `
                <div class="text-gray-300 font-medium">S</div>
                <div class="text-gray-300 font-medium">M</div>
                <div class="text-gray-300 font-medium">T</div>
                <div class="text-gray-300 font-medium">W</div>
                <div class="text-gray-300 font-medium">T</div>
                <div class="text-gray-300 font-medium">F</div>
                <div class="text-gray-300 font-medium">S</div>
            `;
            miniCalMonthYearEl.textContent = `${monthNames[miniCalMonth]} ${miniCalYear}`;

            let firstDayOfMonth = new Date(miniCalYear, miniCalMonth, 1);
            let startingDay = firstDayOfMonth.getDay(); // 0 for Sunday, 1 for Monday...

            let daysInMonth = new Date(miniCalYear, miniCalMonth + 1, 0).getDate();
            let daysInPrevMonth = new Date(miniCalYear, miniCalMonth, 0).getDate();

            // Add padding days from previous month
            for (let i = 0; i < startingDay; i++) {
                const dayEl = document.createElement('div');
                dayEl.className = 'p-1 rounded-full flex items-center justify-center text-gray-400';
                dayEl.textContent = daysInPrevMonth - startingDay + i + 1;
                miniCalendarGridEl.appendChild(dayEl);
            }

            // Add days of current month
            for (let i = 1; i <= daysInMonth; i++) {
                const dayEl = document.createElement('div');
                dayEl.className = 'p-1 rounded-full flex items-center justify-center cursor-pointer';
                if (i === currentMainDate.getDate() && miniCalMonth === currentMainDate.getMonth() && miniCalYear === currentMainDate.getFullYear()) {
                    dayEl.classList.add('font-bold', 'bg-custom-green-active');
                } else {
                    dayEl.classList.add('hover:bg-gray-700'); // Light hover effect for non-active days
                }
                dayEl.textContent = i;
                dayEl.dataset.date = new Date(miniCalYear, miniCalMonth, i).toISOString(); // Store full date

                dayEl.addEventListener('click', (e) => {
                    const selectedDate = new Date(e.target.dataset.date);
                    currentMainDate = selectedDate;
                    renderCalendar(); // Re-render main calendar based on selected day
                    renderMiniCalendar(); // Re-render mini calendar to update active day
                });

                miniCalendarGridEl.appendChild(dayEl);
            }

            // Add padding days from next month (fill up to 6 weeks for consistency)
            const totalCells = miniCalendarGridEl.children.length - 7; // Subtract initial day headers
            const remainingCells = 42 - totalCells; // 6 rows * 7 days = 42 cells
            for (let i = 1; i <= remainingCells; i++) {
                const dayEl = document.createElement('div');
                dayEl.className = 'p-1 rounded-full flex items-center justify-center text-gray-400';
                dayEl.textContent = i;
                miniCalendarGridEl.appendChild(dayEl);
            }
        }

        // --- Render Main Calendar ---
        async function renderCalendar() {
            mainCalHeaderMonthYearEl.textContent = `${monthNames[currentMainDate.getMonth()]} ${currentMainDate.getFullYear()}`;
            
            // Hide all views first
            monthViewEl.classList.add('hidden');
            weekViewEl.classList.add('hidden');
            dayViewEl.classList.add('hidden');
            yearViewEl.classList.add('hidden');

            // Set active view button
            viewButtons.forEach(btn => btn.classList.remove('active', 'bg-gray-600', 'text-white'));
            document.getElementById(`view-${currentView.toLowerCase()}-btn`).classList.add('active', 'bg-gray-600', 'text-white');

            let startDate, endDate;
            let events = [];

            if (currentView === 'Month') {
                monthViewEl.classList.remove('hidden');
                mainCalHeaderMonthYearEl.textContent = `${monthNames[currentMainDate.getMonth()]} ${currentMainDate.getFullYear()}`;

                let firstDayOfMonth = new Date(currentMainDate.getFullYear(), currentMainDate.getMonth(), 1);
                startDate = getWeekStartDate(firstDayOfMonth); // Get Sunday of the first week of the month
                endDate = new Date(startDate);
                endDate.setDate(startDate.getDate() + 41); // Display 6 weeks (42 days)

                events = await fetchSchedules(startDate, endDate);
                renderMonthView(startDate, events);

            } else if (currentView === 'Week') {
                weekViewEl.classList.remove('hidden');
                startDate = getWeekStartDate(currentMainDate);
                endDate = new Date(startDate);
                endDate.setDate(startDate.getDate() + 6); // End of the week (Saturday)

                // Update week view headers
                for (let i = 0; i < 7; i++) {
                    const date = new Date(startDate);
                    date.setDate(startDate.getDate() + i);
                    weekHeaderDayEls[i].textContent = date.getDate();
                    if (date.toDateString() === new Date().toDateString()) { // Highlight today
                        weekHeaderDayEls[i].parentElement.classList.add('text-custom-green-active');
                    } else {
                        weekHeaderDayEls[i].parentElement.classList.remove('text-custom-green-active');
                    }
                }
                mainCalHeaderMonthYearEl.textContent = `${monthNames[startDate.getMonth()]} ${startDate.getDate()} - ${monthNames[endDate.getMonth()]} ${endDate.getDate()}, ${startDate.getFullYear()}`;


                events = await fetchSchedules(startDate, endDate);
                renderWeekView(startDate, events);

            } else if (currentView === 'Day') {
                dayViewEl.classList.remove('hidden');
                startDate = new Date(currentMainDate.getFullYear(), currentMainDate.getMonth(), currentMainDate.getDate());
                endDate = new Date(currentMainDate.getFullYear(), currentMainDate.getMonth(), currentMainDate.getDate(), 23, 59, 59);

                dayHeaderDateEl.textContent = `${dayNames[currentMainDate.getDay()]}, ${monthNames[currentMainDate.getMonth()]} ${currentMainDate.getDate()}, ${currentMainDate.getFullYear()}`;
                mainCalHeaderMonthYearEl.textContent = `Schedules for ${dayHeaderDateEl.textContent}`;

                events = await fetchSchedules(startDate, endDate);
                renderDayView(startDate, events);

            } else if (currentView === 'Year') {
                yearViewEl.classList.remove('hidden');
                mainCalHeaderMonthYearEl.textContent = `Yearly Overview for ${currentMainDate.getFullYear()}`;
                // No specific rendering for Year view beyond placeholder.
            }
        }

        function renderMonthView(startDate, events) {
            monthGridDaysEl.innerHTML = ''; // Clear previous days

            for (let i = 0; i < 42; i++) { // 6 weeks * 7 days
                const date = new Date(startDate);
                date.setDate(startDate.getDate() + i);

                const dayCell = document.createElement('div');
                dayCell.className = 'p-1 relative border-b border-l border-r border-gray-700 h-28'; // Fixed height for month cells
                if (date.getMonth() !== currentMainDate.getMonth()) {
                    dayCell.classList.add('text-gray-500'); // Faded for prev/next month days
                } else {
                     dayCell.classList.add('cursor-pointer', 'hover:bg-gray-700');
                     dayCell.addEventListener('click', () => {
                         currentMainDate = date;
                         currentView = 'Day';
                         renderCalendar();
                         renderMiniCalendar();
                     });
                }
                
                dayCell.innerHTML = `<div class="text-right font-medium">${date.getDate()}</div>`;

                const dailyEvents = events.filter(event => 
                    event.start_time.getFullYear() === date.getFullYear() &&
                    event.start_time.getMonth() === date.getMonth() &&
                    event.start_time.getDate() === date.getDate()
                ).sort((a, b) => a.start_time - b.start_time); // Sort events by time

                dailyEvents.slice(0, 3).forEach(event => { // Display max 3 events
                    const eventEl = document.createElement('div');
                    eventEl.className = `event-box ${getCategoryColorClass(event.category)}`;
                    eventEl.textContent = event.title;
                    eventEl.title = `${event.title} (${formatTime(event.start_time)} - ${formatTime(event.end_time)})`;
                    eventEl.addEventListener('click', (e) => {
                        e.stopPropagation(); // Prevent day cell click
                        showEventDetails(event);
                    });
                    dayCell.appendChild(eventEl);
                });

                if (dailyEvents.length > 3) {
                    const moreEl = document.createElement('div');
                    moreEl.className = 'text-xs text-gray-400 mt-1 cursor-pointer hover:underline';
                    moreEl.textContent = `+${dailyEvents.length - 3} more`;
                     moreEl.addEventListener('click', (e) => {
                         e.stopPropagation();
                         currentMainDate = date;
                         currentView = 'Day';
                         renderCalendar();
                         renderMiniCalendar();
                     });
                    dayCell.appendChild(moreEl);
                }

                monthGridDaysEl.appendChild(dayCell);
            }
        }

        function renderWeekView(startDate, events) {
            weekGridTimeSlotsEl.querySelectorAll('.day-cell').forEach(cell => cell.innerHTML = ''); // Clear previous events

            events.forEach(event => {
                const eventDay = event.start_time.getDay(); // 0-6 (Sunday-Saturday)
                const eventHour = event.start_time.getHours();
                const eventMinute = event.start_time.getMinutes();
                const durationHours = (event.end_time - event.start_time) / (1000 * 60 * 60);

                const targetCell = weekGridTimeSlotsEl.querySelector(`.day-cell.hour-${eventHour}.day-${eventDay}`);
                if (targetCell) {
                    const eventEl = document.createElement('div');
                    eventEl.className = `event-box ${getCategoryColorClass(event.category)}`;
                    eventEl.innerHTML = `
                        <p class="font-semibold leading-tight">${event.title}</p>
                        <p class="text-xs opacity-80">${formatTime(event.start_time)} - ${formatTime(event.end_time)}</p>
                        ${event.notes ? `<p class="text-xs opacity-80 truncate">${event.notes}</p>` : ''}
                    `;
                    eventEl.style.top = `${eventMinute / 60 * 60}px`; // Position vertically within the hour slot
                    eventEl.style.height = `${durationHours * 60 - 8}px`; // Height based on duration, minus padding
                    eventEl.title = `${event.title} (${formatTime(event.start_time)} - ${formatTime(event.end_time)}) - ${event.notes || ''}`;
                    eventEl.addEventListener('click', (e) => {
                        e.stopPropagation();
                        showEventDetails(event);
                    });
                    targetCell.appendChild(eventEl);
                }
            });
        }

        function renderDayView(date, events) {
            dayGridTimeSlotsEl.querySelectorAll('.day-cell').forEach(cell => cell.innerHTML = ''); // Clear previous events

            events.forEach(event => {
                const eventHour = event.start_time.getHours();
                const eventMinute = event.start_time.getMinutes();
                const durationHours = (event.end_time - event.start_time) / (1000 * 60 * 60);

                const targetCell = dayGridTimeSlotsEl.querySelector(`.day-cell.hour-${eventHour}.day-0`); // day-0 for the single day
                if (targetCell) {
                    const eventEl = document.createElement('div');
                    eventEl.className = `event-box ${getCategoryColorClass(event.category)}`;
                     eventEl.innerHTML = `
                        <p class="font-semibold leading-tight">${event.title}</p>
                        <p class="text-xs opacity-80">${formatTime(event.start_time)} - ${formatTime(event.end_time)}</p>
                        ${event.notes ? `<p class="text-xs opacity-80 truncate">${event.notes}</p>` : ''}
                    `;
                    eventEl.style.top = `${eventMinute / 60 * 60}px`;
                    eventEl.style.height = `${durationHours * 60 - 8}px`;
                    eventEl.title = `${event.title} (${formatTime(event.start_time)} - ${formatTime(event.end_time)}) - ${event.notes || ''}`;
                    eventEl.addEventListener('click', (e) => {
                        e.stopPropagation();
                        showEventDetails(event);
                    });
                    targetCell.appendChild(eventEl);
                }
            });
        }

        function showEventDetails(event) {
            detailsEventTitleEl.textContent = event.title;
            detailsEventCategoryEl.textContent = event.category;
            detailsEventCategoryEl.className = getCategoryColorClass(event.category); // Apply category color class
            detailsEventTimeEl.textContent = `${formatDateForDisplay(event.start_time)} ${formatTime(event.start_time)} - ${formatTime(event.end_time)}`;
            detailsEventNotesEl.textContent = event.notes || 'No notes.';
            eventDetailsModal.classList.remove('hidden');
        }

        // --- Event Listeners for Navigation ---
        miniCalPrevMonthBtn.addEventListener('click', () => {
            miniCalMonth--;
            if (miniCalMonth < 0) {
                miniCalMonth = 11;
                miniCalYear--;
            }
            currentMainDate = new Date(miniCalYear, miniCalMonth, currentMainDate.getDate()); // Keep current date as reference
            renderMiniCalendar();
            renderCalendar();
        });

        miniCalNextMonthBtn.addEventListener('click', () => {
            miniCalMonth++;
            if (miniCalMonth > 11) {
                miniCalMonth = 0;
                miniCalYear++;
            }
            currentMainDate = new Date(miniCalYear, miniCalMonth, currentMainDate.getDate());
            renderMiniCalendar();
            renderCalendar();
        });

        viewButtons.forEach(button => {
            button.addEventListener('click', () => {
                currentView = button.textContent; // Or button.dataset.view if you use that
                renderCalendar();
            });
        });

        // --- Create Schedule Modal Logic ---
        createScheduleBtn.addEventListener('click', () => {
            createScheduleModal.classList.remove('hidden');
            populateCategorySelectAndList(); // Ensure categories are up-to-date
        });

        closeScheduleModalBtn.addEventListener('click', () => {
            createScheduleModal.classList.add('hidden');
            createScheduleForm.reset(); // Clear form on close
        });

        // --- Add Category Logic ---
        addCategoryBtn.addEventListener('click', async () => {
            const newCategory = prompt("Enter new category name:");
            if (newCategory && newCategory.trim() !== "") {
                try {
                    const csrfToken = await getCsrfToken(); // Get token for API call
                    const response = await fetch('/api/categories', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
                        body: JSON.stringify({ category_name: newCategory.trim() }),
                    });
                    if (response.ok) {
                        alert(`Category '${newCategory.trim()}' added!`);
                        if (!categoryColors[newCategory.trim()]) {
                             const randomHue = Math.floor(Math.random() * 360);
                             const newCategoryColorClass = `bg-[hsl(${randomHue},_70%,_70%)]`; 
                             categoryColors[newCategory.trim()] = newCategoryColorClass;
                        }
                        populateCategorySelectAndList(); // Re-populate to show new category
                        renderCalendar(); // Re-render to ensure new category is available in event displays
                    } else {
                        const errorData = await response.json();
                        alert('Failed to add category: ' + (errorData.error || response.statusText));
                    }
                } catch (error) {
                    console.error('Error adding category:', error);
                    alert('An error occurred while adding the category.');
                }
            }
        });

        // --- Event Details Modal Logic ---
        closeEventDetailsModalBtn.addEventListener('click', () => {
            eventDetailsModal.classList.add('hidden');
        });

        // --- Initial Render ---
        renderMiniCalendar();
        renderCalendar(); // Render main calendar initially (defaults to Week view)
    }
});