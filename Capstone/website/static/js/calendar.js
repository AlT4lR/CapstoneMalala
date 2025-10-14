// static/js/calendar.js
document.addEventListener('DOMContentLoaded', function() {
    const calendarEl = document.getElementById('calendar');
    if (!calendarEl) return;

    const calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'timeGridWeek',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,timeGridDay'
        },
        events: '/api/schedules', // Fetch events from this endpoint
        editable: true,
        selectable: true,
        eventClick: function(info) {
            alert('Event: ' + info.event.title);
        },
        select: function(info) {
            var title = prompt('Enter Event Title:');
            if (title) {
                // Here you would make an API call to save the new event
                console.log('New event selected from ' + info.startStr + ' to ' + info.endStr);
            }
            calendar.unselect();
        }
    });

    calendar.render();
});