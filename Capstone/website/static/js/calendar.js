// static/js/calendar.js

document.addEventListener('DOMContentLoaded', function() {
    const calendarEl = document.getElementById('calendar');
    if (!calendarEl) return; // Exit if the calendar element isn't on the page

    // --- Modal Elements (assuming you create these modals) ---
    // const createModal = document.getElementById('create-schedule-modal');
    // const detailsModal = document.getElementById('schedule-details-modal');
    // const closeCreateBtn = document.getElementById('close-create-modal-btn');
    // const closeDetailsBtn = document.getElementById('close-details-modal-btn');

    const calendar = new FullCalendar.Calendar(calendarEl, {
        // --- PLUGIN INITIALIZATION ---
        initialView: 'timeGridWeek', // The default view (week, day, month)
        themeSystem: 'standard', // Use standard theme that's easy to override with Tailwind

        // --- HEADER TOOLBAR ---
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,timeGridDay' // Buttons to switch views
        },
        
        // --- DATE & TIME ---
        navLinks: true, // Can click day/week names to navigate views
        dayMaxEvents: true, // Allow "more" link when too many events
        
        // --- EVENT DATA ---
        // This is the core part: fetching events from your Flask API
        events: {
            url: '/api/schedules',
            method: 'GET',
            failure: function() {
                alert('There was an error while fetching events!');
            },
            // You can add extra parameters if needed, like the selected branch
            extraParams: function() {
                // This is a placeholder, as branch is stored in the session on the backend
                return {}; 
            }
        },

        // --- INTERACTIVITY ---
        editable: true,       // Allows dragging and resizing events
        selectable: true,       // Allows selecting a time range to create an event

        /**
         * Triggered when a user clicks on an existing event.
         * We can use this to open our details modal.
         */
        eventClick: function(info) {
            info.jsEvent.preventDefault(); // Don't let the browser navigate
            
            // Log for debugging, replace with modal logic
            console.log('Event Clicked:', info.event);
            const props = info.event.extendedProps;
            alert(
                `Event: ${info.event.title}\n` +
                `Category: ${props.category}\n` +
                `Starts: ${info.event.start.toLocaleString()}\n` +
                `Ends: ${info.event.end.toLocaleString()}\n` +
                `Notes: ${props.notes}`
            );
            // Example of how you would populate a details modal:
            // document.getElementById('details-title').textContent = info.event.title;
            // document.getElementById('details-category').textContent = props.category;
            // ...populate other fields...
            // detailsModal.classList.remove('hidden');
        },

        /**
         * Triggered when a user clicks and drags on an empty part of the calendar.
         * We can use this to open our creation modal with pre-filled dates.
         */
        select: function(info) {
            console.log('Date Selected:', info);
            // For now, we will just prompt the user. Replace this with your modal.
            var title = prompt('Enter Event Title:');
            if (title) {
                // This is where you would make an AJAX call to a new '/api/schedules/create' endpoint
                // and then refresh the calendar on success.
                alert(`Creating event "${title}" from ${info.startStr} to ${info.endStr}`);
                
                // Example of what a real AJAX call to create an event would look like:
                /*
                fetch('/api/schedules/create', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRF-Token': window.getCsrfToken() // From common.js
                    },
                    body: JSON.stringify({
                        title: title,
                        start_time: info.startStr,
                        end_time: info.endStr,
                        category: 'Office' // Get this from your create modal
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        calendar.refetchEvents(); // Reload events from the server
                    } else {
                        alert('Error: ' + (data.error || 'Could not create event.'));
                    }
                })
                .catch(error => {
                    console.error('Error creating event:', error);
                    alert('A network error occurred.');
                });
                */
            }
            calendar.unselect(); // Clear the selection
        },

        /**
         * Triggered after an event is dragged and dropped.
         */
        eventDrop: function(info) {
             // Here you would make an AJAX call to an '/api/schedules/update' endpoint
             // to save the new start/end times for info.event.id
            alert(info.event.title + " was dropped on " + info.event.start.toISOString() + ". In a real app, this change would be saved to the database!");

            if (!confirm("Are you sure about this change?")) {
                info.revert(); // Revert the change if the user cancels
            }
        }
    });

    calendar.render();

    // You can add a listener to refetch events if something global changes, like the branch
    // document.body.addEventListener('branchChanged', () => calendar.refetchEvents());
});