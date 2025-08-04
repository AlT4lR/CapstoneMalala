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

        // DOM Elements for Mini Calendar
        const miniCalMonthYearEl = document.getElementById('mini-cal-month-year');
        const miniCalendarGridEl = document.getElementById('mini-calendar-grid');
        const miniCalPrevMonthBtn = document.getElementById('mini-cal-prev-month');
        const miniCalNextMonthBtn = document.getElementById('mini-cal-next-month');

        // DOM Elements for Main Calendar
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

        // Navigation & Modal Elements
        const viewButtons = document.querySelectorAll('.view-button');
        const createScheduleBtn = document.getElementById('create-schedule-btn');
        const createScheduleModal = document.getElementById('create-schedule-modal');
        const closeScheduleModalBtn = document.getElementById('close-schedule-modal');
        const createScheduleForm = document.getElementById('create-schedule-form'); // For AJAX submission
        const eventCategorySelect = document.getElementById('event-category');
        const categoryListEl = document.getElementById('category-list');
        const addCategoryBtn = document.getElementById('add-category-btn');

        const eventDetailsModal = document.getElementById('event-details-modal');
        const closeEventDetailsModalBtn = document.getElementById('close-event-details-modal');
        const detailsEventTitleEl = document.getElementById('details-event-title');
        const detailsEventCategoryEl = document.getElementById('details-event-category');
        const detailsEventTimeEl = document.getElementById('details-event-time');
        const detailsEventNotesEl = document.getElementById('details-event-notes');

        // Category Colors Mapping
        const categoryColors = {
            'Office': 'bg-category-office',
            'Meetings': 'bg-category-meetings',
            'Events': 'bg-category-events',
            'Personal': 'bg-category-personal',
            'Others': 'bg-category-others',
        };
        
        // --- Initial Date Setup (Uses global variable from schedules.html) ---
        // Ensure FLASK_INITIAL_DATE_ISO is available globally from Jinja2
        // Initialize currentMainDate as a UTC-aware date object
        currentMainDate = new Date(FLASK_INITIAL_DATE_ISO);
        if (isNaN(currentMainDate.getTime())) { // Check if parsing failed
            currentMainDate = new Date(Date.now()); // Fallback to current time
        }
        currentMainDate.setHours(0, 0, 0, 0); // Normalize to start of day (locally, but will be treated as UTC contextually)
        currentMainDate.setUTCHours(0, 0, 0, 0); // Ensure it's UTC-based for consistency

        let miniCalMonth = currentMainDate.getMonth(); // Month is 0-indexed locally
        let miniCalYear = currentMainDate.getFullYear();

        // --- Helper Functions ---
        // Function to get the start of the week (Sunday) for a given date
        function getWeekStartDate(date) {
            // Ensure date is UTC-aware
            const utcDate = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
            let dayOfWeek = utcDate.getDay(); // 0 = Sunday, 1 = Monday, ..., 6 = Saturday
            let diff = utcDate.getDate() - dayOfWeek; // Number of days to subtract to get to Sunday
            const sundayOfThatWeek = new Date(utcDate.setDate(diff));
            return sundayOfThatWeek;
        }

        // Formats a date string into a time (e.g., "10:30 AM")
        function formatTime(dateStringOrDate) {
            let date;
            if (typeof dateStringOrDate === 'string') {
                date = new Date(dateStringOrDate);
            } else if (dateStringOrDate instanceof Date) {
                date = dateStringOrDate;
            } else {
                return 'Invalid Time';
            }
            // Using toLocaleTimeString for user's local time, adjust if UTC display is needed
            return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        }

        // Formats a date for display (e.g., "Mon, Jan 1")
        function formatDateForDisplay(date) {
            // Assuming date is a Date object
            return date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
        }

        // Gets Tailwind CSS class for a given category
        function getCategoryColorClass(category) {
            const baseClass = 'px-2 py-1 rounded-full text-xs font-semibold';
            return `${baseClass} ${categoryColors[category] || 'bg-gray-500'}`; // Fallback to gray if category not mapped
        }

        // Fetches schedules from the API, ensuring proper date formatting and CSRF headers
        async function fetchSchedules(start, end) {
            try {
                // Use the globally available getCsrfToken from common.js
                const csrfToken = await window.getCsrfToken();
                if (!csrfToken) {
                    console.error("CSRF token not available for fetching schedules.");
                    return [];
                }

                // Ensure dates are correctly formatted for API query (ISO String)
                const startISO = start.toISOString();
                const endISO = end.toISOString();

                const response = await fetch(`/api/schedules?start=${startISO}&end=${endISO}`, {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRF-Token': csrfToken
                    }
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    console.error("Error fetching schedules:", errorData.error || response.statusText);
                    return []; // Return empty array on error
                }
                const schedules = await response.json();
                
                // Convert fetched date strings back to Date objects for easier manipulation in JS
                return schedules.map(s => ({
                    ...s,
                    start_time: new Date(s.start_time), // Parse ISO string back to Date object
                    end_time: new Date(s.end_time)
                }));
            } catch (error) {
                console.error("Network or parsing error fetching schedules:", error);
                return [];
            }
        }

        // Fetches categories (initially via JSON, potentially via API later)
        async function fetchCategories() {
            try {
                // Use the globally available getCsrfToken from common.js
                const csrfToken = await window.getCsrfToken();
                if (!csrfToken) {
                    console.warn("CSRF token not available for fetching categories.");
                    // Fallback if token is missing or not needed for GET (depends on your Flask route)
                    // If GET requests also require CSRF, handle accordingly.
                    // For now, assuming GET might not strictly need it, but it's safer if it does.
                }

                const response = await fetch('/api/categories', {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRF-Token': csrfToken // Include token if required for GET API
                    }
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    console.error("Error fetching categories:", errorData.error || response.statusText);
                    return ['Office', 'Meetings', 'Events', 'Personal', 'Others']; // Fallback on error
                }
                const categories = await response.json();
                
                // Ensure categories is an array and return defaults if empty
                if (Array.isArray(categories) && categories.length > 0) {
                    return categories;
                }
                return ['Office', 'Meetings', 'Events', 'Personal', 'Others']; // Fallback
            } catch (error) {
                console.error("Network or parsing error fetching categories:", error);
                return ['Office', 'Meetings', 'Events', 'Personal', 'Others']; // Fallback
            }
        }

        // Populates the <select> for the form and the radio buttons for the sidebar category list
        async function populateCategorySelectAndList(initialCategories = null) {
            const categories = initialCategories || await fetchCategories();
            
            eventCategorySelect.innerHTML = ''; // Clear existing options
            categoryListEl.innerHTML = ''; // Clear existing radio buttons

            categories.forEach(cat => {
                // Option for the <select> dropdown
                const option = document.createElement('option');
                option.value = cat;
                option.textContent = cat;
                eventCategorySelect.appendChild(option);

                // Radio button for the sidebar category list
                const label = document.createElement('label');
                label.className = 'flex items-center mb-1'; // Add margin-bottom for spacing
                label.innerHTML = `
                    <input type="radio" name="sidebar-category" value="${cat}" class="form-radio h-4 w-4 text-custom-green-active">
                    <span class="ml-2">${cat}</span>
                `;
                categoryListEl.appendChild(label);
            });
        }

        // --- Render Mini Calendar ---
        function renderMiniCalendar() {
            // Clear previous content (except day headers)
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

            // Get the first day of the month and its day of the week (0=Sunday)
            const firstDayOfMonth = new Date(miniCalYear, miniCalMonth, 1);
            let startingDay = firstDayOfMonth.getDay(); 

            // Get total days in the month
            const daysInMonth = new Date(miniCalYear, miniCalMonth + 1, 0).getDate();
            // Get days in the previous month (for padding)
            const daysInPrevMonth = new Date(miniCalYear, miniCalMonth, 0).getDate();

            // Add padding days from the previous month
            for (let i = 0; i < startingDay; i++) {
                const dayEl = document.createElement('div');
                dayEl.className = 'p-1 rounded-full flex items-center justify-center text-gray-400'; // Faded text for prev month days
                dayEl.textContent = daysInPrevMonth - startingDay + i + 1;
                miniCalendarGridEl.appendChild(dayEl);
            }

            // Add days of the current month
            for (let i = 1; i <= daysInMonth; i++) {
                const dayEl = document.createElement('div');
                dayEl.className = 'p-1 rounded-full flex items-center justify-center cursor-pointer';
                
                // Highlight the current day being displayed in the main calendar
                if (i === currentMainDate.getDate() && miniCalMonth === currentMainDate.getMonth() && miniCalYear === currentMainDate.getFullYear()) {
                    dayEl.classList.add('font-bold', 'bg-custom-green-active');
                } else {
                    dayEl.classList.add('hover:bg-gray-700'); // Light hover effect for non-active days
                }
                dayEl.textContent = i;
                // Store the full date for click handling
                dayEl.dataset.date = new Date(Date.UTC(miniCalYear, miniCalMonth, i)).toISOString(); 

                dayEl.addEventListener('click', (e) => {
                    const selectedDate = new Date(e.target.dataset.date);
                    currentMainDate = selectedDate; // Update the main calendar date
                    renderCalendar(); // Re-render main calendar
                    renderMiniCalendar(); // Re-render mini calendar to update active day
                });

                miniCalendarGridEl.appendChild(dayEl);
            }

            // Fill remaining cells to ensure 6 weeks (42 cells total) for consistent layout
            const totalCellsUsed = miniCalendarGridEl.children.length - 7; // Subtract day headers
            const totalGridCells = 42; // 6 weeks * 7 days
            const remainingCells = totalGridCells - totalCellsUsed;
            for (let i = 1; i <= remainingCells; i++) {
                const dayEl = document.createElement('div');
                dayEl.className = 'p-1 rounded-full flex items-center justify-center text-gray-400'; // Faded text for padding days
                dayEl.textContent = i;
                miniCalendarGridEl.appendChild(dayEl);
            }
        }

        // --- Render Main Calendar ---
        async function renderCalendar() {
            // Update main header with current month/year
            mainCalHeaderMonthYearEl.textContent = `${monthNames[currentMainDate.getMonth()]} ${currentMainDate.getFullYear()}`;
            
            // Hide all views initially
            monthViewEl.classList.add('hidden');
            weekViewEl.classList.add('hidden');
            dayViewEl.classList.add('hidden');
            yearViewEl.classList.add('hidden');

            // Update active view button styling
            viewButtons.forEach(btn => btn.classList.remove('active', 'bg-gray-600', 'text-white'));
            document.getElementById(`view-${currentView.toLowerCase()}-btn`).classList.add('active', 'bg-gray-600', 'text-white');

            let startDate, endDate;
            let events = [];

            if (currentView === 'Month') {
                monthViewEl.classList.remove('hidden');
                mainCalHeaderMonthYearEl.textContent = `${monthNames[currentMainDate.getMonth()]} ${currentMainDate.getFullYear()}`;

                let firstDayOfMonth = new Date(Date.UTC(currentMainDate.getFullYear(), currentMainDate.getMonth(), 1));
                startDate = getWeekStartDate(firstDayOfMonth); // Sunday of the first week
                endDate = new Date(startDate);
                endDate.setDate(startDate.getDate() + 41); // Display 6 full weeks (42 days)

                events = await fetchSchedules(startDate, endDate);
                renderMonthView(startDate, events);

            } else if (currentView === 'Week') {
                weekViewEl.classList.remove('hidden');
                startDate = getWeekStartDate(currentMainDate);
                endDate = new Date(startDate);
                endDate.setDate(startDate.getDate() + 6); // Saturday of the current week

                // Update week view headers with day numbers
                for (let i = 0; i < 7; i++) {
                    const date = new Date(startDate);
                    date.setDate(startDate.getDate() + i);
                    weekHeaderDayEls[i].textContent = date.getDate();
                    // Highlight today's date in the week header
                    if (date.toDateString() === new Date().toDateString()) { 
                        weekHeaderDayEls[i].parentElement.classList.add('text-custom-green-active');
                    } else {
                        weekHeaderDayEls[i].parentElement.classList.remove('text-custom-green-active');
                    }
                }
                // Update main header for the week range
                mainCalHeaderMonthYearEl.textContent = `${monthNames[startDate.getMonth()]} ${startDate.getDate()} - ${monthNames[endDate.getMonth()]} ${endDate.getDate()}, ${startDate.getFullYear()}`;

                events = await fetchSchedules(startDate, endDate);
                renderWeekView(startDate, events);

            } else if (currentView === 'Day') {
                dayViewEl.classList.remove('hidden');
                // Define start and end of the day for the query, ensuring UTC
                startDate = new Date(Date.UTC(currentMainDate.getFullYear(), currentMainDate.getMonth(), currentMainDate.getDate()));
                endDate = new Date(Date.UTC(currentMainDate.getFullYear(), currentMainDate.getMonth(), currentMainDate.getDate(), 23, 59, 59));

                // Update day header
                dayHeaderDateEl.textContent = `${dayNames[currentMainDate.getDay()]}, ${monthNames[currentMainDate.getMonth()]} ${currentMainDate.getDate()}, ${currentMainDate.getFullYear()}`;
                mainCalHeaderMonthYearEl.textContent = `Schedules for ${dayHeaderDateEl.textContent}`;

                events = await fetchSchedules(startDate, endDate);
                renderDayView(currentMainDate, events); // Pass the specific day for rendering

            } else if (currentView === 'Year') {
                yearViewEl.classList.remove('hidden');
                mainCalHeaderMonthYearEl.textContent = `Yearly Overview for ${currentMainDate.getFullYear()}`;
                // Placeholder for Year View
            }
        }

        // Renders events for the Month View
        function renderMonthView(startDate, events) {
            monthGridDaysEl.innerHTML = ''; // Clear previous days

            for (let i = 0; i < 42; i++) { // Render 6 weeks (42 days)
                const date = new Date(startDate);
                date.setDate(startDate.getDate() + i);

                const dayCell = document.createElement('div');
                // Base classes for day cells
                dayCell.className = 'p-1 relative border-b border-l border-r border-gray-700 h-28'; // Fixed height
                
                // Style days outside the current month
                if (date.getMonth() !== currentMainDate.getMonth()) {
                    dayCell.classList.add('text-gray-500'); 
                } else {
                     dayCell.classList.add('cursor-pointer', 'hover:bg-gray-700');
                     // Add click listener to switch to Day view for this date
                     dayCell.addEventListener('click', () => {
                         currentMainDate = date;
                         currentView = 'Day';
                         renderCalendar();
                         renderMiniCalendar();
                     });
                }
                
                // Display the day number
                dayCell.innerHTML = `<div class="text-right font-medium">${date.getDate()}</div>`;

                // Filter and sort events for this specific day
                const dailyEvents = events.filter(event => 
                    event.start_time.getFullYear() === date.getFullYear() &&
                    event.start_time.getMonth() === date.getMonth() &&
                    event.start_time.getDate() === date.getDate()
                ).sort((a, b) => a.start_time - b.start_time); // Sort by start time

                // Display up to 3 events on the day cell
                dailyEvents.slice(0, 3).forEach(event => { 
                    const eventEl = document.createElement('div');
                    eventEl.className = `event-box ${getCategoryColorClass(event.category)}`;
                    eventEl.textContent = event.title;
                    eventEl.title = `${event.title} (${formatTime(event.start_time)} - ${formatTime(event.end_time)})`;
                    eventEl.addEventListener('click', (e) => {
                        e.stopPropagation(); // Prevent day cell click propagation
                        showEventDetails(event);
                    });
                    dayCell.appendChild(eventEl);
                });

                // Show "+ X more" if there are more events than displayed
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

        // Renders events for the Week View
        function renderWeekView(startDate, events) {
            // Clear any previously rendered events in the week grid
            weekGridTimeSlotsEl.querySelectorAll('.day-cell').forEach(cell => cell.innerHTML = ''); 

            events.forEach(event => {
                const eventDay = event.start_time.getDay(); // Day of the week (0=Sun, 6=Sat)
                const eventHour = event.start_time.getHours();
                const eventMinute = event.start_time.getMinutes();
                // Calculate duration in hours for height calculation
                const durationHours = (event.end_time - event.start_time) / (1000 * 60 * 60);

                // Find the target cell for this event
                const targetCell = weekGridTimeSlotsEl.querySelector(`.day-cell.hour-${eventHour}.day-${eventDay}`);
                if (targetCell) {
                    const eventEl = document.createElement('div');
                    eventEl.className = `event-box ${getCategoryColorClass(event.category)}`;
                    // Event content: title, time, and notes if available
                    eventEl.innerHTML = `
                        <p class="font-semibold leading-tight">${event.title}</p>
                        <p class="text-xs opacity-80">${formatTime(event.start_time)} - ${formatTime(event.end_time)}</p>
                        ${event.notes ? `<p class="text-xs opacity-80 truncate">${event.notes}</p>` : ''}
                    `;
                    // Position the event vertically within its hour slot
                    eventEl.style.top = `${eventMinute / 60 * 60}px`; // 60px per hour slot
                    eventEl.style.height = `${durationHours * 60 - 8}px`; // Height based on duration, accounting for padding/margins
                    eventEl.title = `${event.title} (${formatTime(event.start_time)} - ${formatTime(event.end_time)}) - ${event.notes || ''}`;
                    
                    // Add click listener to show event details
                    eventEl.addEventListener('click', (e) => {
                        e.stopPropagation(); // Prevent triggering the day cell click
                        showEventDetails(event);
                    });
                    targetCell.appendChild(eventEl);
                }
            });
        }

        // Renders events for the Day View
        function renderDayView(date, events) {
            dayGridTimeSlotsEl.querySelectorAll('.day-cell').forEach(cell => cell.innerHTML = ''); // Clear previous events

            events.forEach(event => {
                const eventHour = event.start_time.getHours();
                const eventMinute = event.start_time.getMinutes();
                const durationHours = (event.end_time - event.start_time) / (1000 * 60 * 60);

                // Find the target cell for this event (day-0 for single day view)
                const targetCell = dayGridTimeSlotsEl.querySelector(`.day-cell.hour-${eventHour}.day-0`); 
                if (targetCell) {
                    const eventEl = document.createElement('div');
                    eventEl.className = `event-box ${getCategoryColorClass(event.category)}`;
                     eventEl.innerHTML = `
                        <p class="font-semibold leading-tight">${event.title}</p>
                        <p class="text-xs opacity-80">${formatTime(event.start_time)} - ${formatTime(event.end_time)}</p>
                        ${event.notes ? `<p class="text-xs opacity-80 truncate">${event.notes}</p>` : ''}
                    `;
                    eventEl.style.top = `${eventMinute / 60 * 60}px`; // Position vertically
                    eventEl.style.height = `${durationHours * 60 - 8}px`; // Height based on duration
                    eventEl.title = `${event.title} (${formatTime(event.start_time)} - ${formatTime(event.end_time)}) - ${event.notes || ''}`;
                    
                    eventEl.addEventListener('click', (e) => {
                        e.stopPropagation();
                        showEventDetails(event);
                    });
                    targetCell.appendChild(eventEl);
                }
            });
        }

        // Displays event details in a modal
        function showEventDetails(event) {
            detailsEventTitleEl.textContent = event.title;
            detailsEventCategoryEl.textContent = event.category;
            detailsEventCategoryEl.className = getCategoryColorClass(event.category); // Apply category color class
            detailsEventTimeEl.textContent = `${formatDateForDisplay(event.start_time)} ${formatTime(event.start_time)} - ${formatTime(event.end_time)}`;
            detailsEventNotesEl.textContent = event.notes || 'No notes.';
            eventDetailsModal.classList.remove('hidden');
        }

        // --- Event Listeners for Navigation ---
        // Previous month button for mini calendar
        miniCalPrevMonthBtn.addEventListener('click', () => {
            miniCalMonth--;
            if (miniCalMonth < 0) {
                miniCalMonth = 11; // December
                miniCalYear--;
            }
            // Update currentMainDate reference for calendar rendering
            currentMainDate = new Date(Date.UTC(miniCalYear, miniCalMonth, currentMainDate.getDate()));
            renderMiniCalendar();
            renderCalendar(); // Re-render main calendar
        });

        // Next month button for mini calendar
        miniCalNextMonthBtn.addEventListener('click', () => {
            miniCalMonth++;
            if (miniCalMonth > 11) {
                miniCalMonth = 0; // January
                miniCalYear++;
            }
            currentMainDate = new Date(Date.UTC(miniCalYear, miniCalMonth, currentMainDate.getDate()));
            renderMiniCalendar();
            renderCalendar();
        });

        // View buttons (Day, Week, Month, Year)
        viewButtons.forEach(button => {
            button.addEventListener('click', () => {
                currentView = button.textContent; // Set the current view based on button text
                renderCalendar(); // Re-render the calendar with the new view
            });
        });

        // --- Create Schedule Modal Logic ---
        createScheduleBtn.addEventListener('click', () => {
            createScheduleModal.classList.remove('hidden');
            populateCategorySelectAndList(); // Load categories into the select and radio list
        });

        closeScheduleModalBtn.addEventListener('click', () => {
            createScheduleModal.classList.add('hidden');
            createScheduleForm.reset(); // Clear form fields on close
        });

        // --- Add Category Logic ---
        addCategoryBtn.addEventListener('click', async () => {
            const newCategory = prompt("Enter new category name:");
            if (newCategory && newCategory.trim() !== "") {
                try {
                    // Use global getCsrfToken from common.js
                    const csrfToken = await window.getCsrfToken();
                    const response = await fetch('/api/categories', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
                        body: JSON.stringify({ category_name: newCategory.trim() }),
                    });
                    
                    if (response.ok) {
                        alert(`Category '${newCategory.trim()}' added!`);
                        // Dynamically add color class if not predefined
                        if (!categoryColors[newCategory.trim()]) {
                             const randomHue = Math.floor(Math.random() * 360);
                             const newCategoryColorClass = `bg-[hsl(${randomHue},_70%,_70%)]`; 
                             categoryColors[newCategory.trim()] = newCategoryColorClass;
                        }
                        await populateCategorySelectAndList(); // Re-populate select/radios
                        renderCalendar(); // Re-render calendar to potentially show new category usage
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
        // Ensure the initial date setup is correct and UTC-aware
        if (isNaN(currentMainDate.getTime())) { // Check if initial date was invalid
            currentMainDate = new Date(Date.now()); // Fallback to current time, make UTC-aware
            currentMainDate.setUTCHours(0,0,0,0);
        }
        
        // Update mini calendar month/year based on initial currentMainDate
        miniCalMonth = currentMainDate.getMonth();
        miniCalYear = currentMainDate.getFullYear();

        renderMiniCalendar();
        renderCalendar(); // Render main calendar initially (defaults to Week view)
    }
});

// Helper function to get CSRF token (if not already globally defined by common.js)
// This ensures that if this script were somehow loaded without common.js, it would still try.
// However, ideally, common.js should handle this exclusively.
if (typeof window.getCsrfToken !== 'function') {
    window.getCsrfToken = async function() {
        let csrfToken = null;
        const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
        if (csrfTokenMeta) {
            csrfToken = csrfTokenMeta.getAttribute('content');
        } else {
            const csrfCookie = document.cookie.split('; ').find(row => row.startsWith('csrf_access_token='));
            if (csrfCookie) {
                csrfToken = csrfCookie.split('=')[1];
            }
        }
        if (!csrfToken) {
            console.warn("CSRF token not found in calendar.js. AJAX requests may fail.");
        }
        return csrfToken;
    };
}