// static/js/calendar.js
document.addEventListener('DOMContentLoaded', function() {
    const calendarEl = document.getElementById('calendar');
    if (!calendarEl) return;

    // --- Modal Element Refs ---
    const modal = document.getElementById('create-schedule-modal');
    const form = document.getElementById('schedule-form');
    const discardBtn = document.getElementById('discard-schedule-btn');
    const scheduleIdInput = document.getElementById('schedule-id');
    const scheduleTitleInput = document.getElementById('schedule-title');
    const scheduleDateInput = document.getElementById('schedule-date');
    const startTimeInput = document.getElementById('schedule-start-time');
    const endTimeInput = document.getElementById('schedule-end-time');
    const allDayToggle = document.getElementById('all-day-toggle');
    const descriptionInput = document.getElementById('schedule-description');
    const locationInput = document.getElementById('schedule-location');

    // Buttons
    const dayViewBtn = document.getElementById('day-view-btn');
    const weekViewBtn = document.getElementById('week-view-btn');
    const monthViewBtn = document.getElementById('month-view-btn');
    const yearViewBtn = document.getElementById('year-view-btn');

    // Helper: get CSRF token from meta
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';

    // MODIFICATION: Expose the calendar instance to the window object
    // 'const calendar' is changed to 'const calendar = window.calendar ='
    const calendar = window.calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'timeGridWeek',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: '' // Right is empty because we use custom buttons
        },
        selectable: true,
        editable: true,
        eventResizableFromStart: true,
        height: '100%',
        
        events: function(fetchInfo, successCallback, failureCallback) {
            const params = new URLSearchParams({
                start: fetchInfo.startStr,
                end: fetchInfo.endStr
            });
            fetch(`/api/schedules?${params.toString()}`, {
                method: 'GET',
                credentials: 'same-origin',
                headers: { 'Accept': 'application/json' }
            })
            .then(r => {
                if (!r.ok) throw new Error('Failed to load events');
                return r.json();
            })
            .then(data => successCallback(data))
            .catch(err => {
                console.error('Error fetching events:', err);
                failureCallback(err);
            });
        },

        eventContent: function(arg) {
            const title = arg.event.title.toLowerCase();
            let dotColor = '#6b7280'; // Default to 'Others'
            if (title.includes('office')) dotColor = '#3b82f6';
            else if (title.includes('meeting')) dotColor = '#8b5cf6';
            else if (title.includes('event')) dotColor = '#ec4899';
            else if (title.includes('personal')) dotColor = '#f59e0b';
            
            const eventHtml = `
                <div class="flex items-center">
                    <span class="event-label-dot" style="background-color: ${dotColor};"></span>
                    <div class="fc-event-title">${arg.event.title}</div>
                </div>
            `;
            return { html: eventHtml };
        },

        select: function(info) {
            form.reset();
            scheduleIdInput.value = '';
            scheduleTitleInput.value = '';
            descriptionInput.value = '';
            locationInput.value = '';
            allDayToggle.checked = info.allDay || false;

            scheduleDateInput.value = info.startStr.slice(0,10);
            if (!info.allDay) {
                startTimeInput.value = info.startStr.slice(11,16);
                endTimeInput.value = info.endStr ? info.endStr.slice(11,16) : '';
            } else {
                startTimeInput.value = '';
                endTimeInput.value = '';
            }
            modal.classList.remove('hidden');
        },

        eventClick: function(info) {
            const event = info.event;
            form.reset();
            scheduleIdInput.value = event.id;
            scheduleTitleInput.value = event.title || '';
            scheduleDateInput.value = event.startStr.slice(0,10);
            descriptionInput.value = event.extendedProps?.description || '';
            locationInput.value = event.extendedProps?.location || '';
            allDayToggle.checked = !!event.allDay;

            if (!event.allDay) {
                startTimeInput.value = event.startStr.slice(11,16);
                endTimeInput.value = event.endStr ? event.endStr.slice(11,16) : '';
            } else {
                startTimeInput.value = '';
                endTimeInput.value = '';
            }
            modal.classList.remove('hidden');
        },

        eventDrop: function(info) {
            const e = info.event;
            const payload = {
                start: e.start.toISOString(),
                end: e.end ? e.end.toISOString() : null,
                allDay: !!e.allDay
            };
            fetch(`/api/schedules/update/${e.id}`, {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': csrfToken
                },
                body: JSON.stringify(payload)
            })
            .then(r => r.json())
            .then(j => {
                if (!j.success) {
                    console.error('Failed to update event on drop:', j);
                    info.revert();
                }
            })
            .catch(err => {
                console.error('Error updating event on drop:', err);
                info.revert();
            });
        },

        eventResize: function(info) {
            const e = info.event;
            const payload = {
                start: e.start.toISOString(),
                end: e.end ? e.end.toISOString() : null,
                allDay: !!e.allDay
            };
            fetch(`/api/schedules/update/${e.id}`, {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': csrfToken
                },
                body: JSON.stringify(payload)
            })
            .then(r => r.json())
            .then(j => {
                if (!j.success) {
                    console.error('Failed to update event on resize:', j);
                    info.revert();
                }
            })
            .catch(err => {
                console.error('Error updating event on resize:', err);
                info.revert();
            });
        }
    });

    calendar.render();

    // Modal controls
    const closeModal = () => modal.classList.add('hidden');
    discardBtn.addEventListener('click', closeModal);
    document.getElementById('create-schedule-btn').addEventListener('click', () => {
        form.reset();
        scheduleIdInput.value = '';
        scheduleDateInput.valueAsDate = new Date();
        startTimeInput.value = '';
        endTimeInput.value = '';
        modal.classList.remove('hidden');
    });

    // Submit form - handles both create and update
    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        const data = new FormData(this);
        const id = scheduleIdInput.value;
        if (allDayToggle.checked) data.set('all_day', 'on');
        else data.delete('all_day');

        try {
            if (!id) {
                const body = new URLSearchParams(data).toString();
                const resp = await fetch('/api/schedules/add', {
                    method: 'POST',
                    credentials: 'same-origin',
                    body,
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'X-CSRF-Token': csrfToken
                    }
                });
                const result = await resp.json();
                if (result.success) {
                    closeModal();
                    calendar.refetchEvents();
                } else {
                    alert('Failed to create schedule: ' + (result.error || 'Unknown error'));
                }
            } else {
                const date = data.get('date');
                const isAllDay = data.get('all_day') === 'on';
                let startIso = null, endIso = null;

                if (isAllDay) {
                    const s = new Date(date + 'T00:00:00Z');
                    const e = new Date(s.getTime() + 24 * 60 * 60 * 1000);
                    startIso = s.toISOString();
                    endIso = e.toISOString();
                } else {
                    const sTime = data.get('start_time') || '00:00';
                    const eTime = data.get('end_time') || '23:59';
                    startIso = new Date(date + 'T' + sTime + ':00').toISOString();
                    endIso = new Date(date + 'T' + eTime + ':00').toISOString();
                }

                const payload = {
                    title: data.get('title'),
                    description: data.get('description'),
                    location: data.get('location'),
                    start: startIso,
                    end: endIso,
                    allDay: isAllDay
                };

                const resp = await fetch(`/api/schedules/update/${id}`, {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRF-Token': csrfToken
                    },
                    body: JSON.stringify(payload)
                });
                const result = await resp.json();
                if (result.success) {
                    closeModal();
                    calendar.refetchEvents();
                } else {
                    alert('Failed to update schedule: ' + (result.error || 'Unknown'));
                }
            }
        } catch (err) {
            console.error('Network error while saving schedule:', err);
            alert('Network error — could not save schedule.');
        }
    });

    function deleteSchedule(id) {
        if (!id) return;
        if (!confirm('Are you sure you want to delete this schedule?')) return;
        fetch(`/api/schedules/${id}`, {
            method: 'DELETE',
            credentials: 'same-origin',
            headers: { 'X-CSRF-Token': csrfToken }
        })
        .then(r => r.json())
        .then(j => {
            if (j.success) {
                calendar.refetchEvents();
                closeModal();
            } else {
                alert('Failed to delete schedule: ' + (j.error || 'Unknown'));
            }
        })
        .catch(err => {
            console.error('Error deleting schedule:', err);
            alert('Network error while deleting schedule.');
        });
    }

    window.deleteSchedule = deleteSchedule;

    function setActiveView(activeBtn) {
        [dayViewBtn, weekViewBtn, monthViewBtn, yearViewBtn].forEach(btn => {
            btn.classList.remove('bg-white', 'shadow');
        });
        activeBtn.classList.add('bg-white', 'shadow');
    }

    dayViewBtn.addEventListener('click', () => { calendar.changeView('timeGridDay'); setActiveView(dayViewBtn); });
    weekViewBtn.addEventListener('click', () => { calendar.changeView('timeGridWeek'); setActiveView(weekViewBtn); });
    monthViewBtn.addEventListener('click', () => { calendar.changeView('dayGridMonth'); setActiveView(monthViewBtn); });
    yearViewBtn.addEventListener('click', () => {
        calendar.changeView('dayGridMonth');
        setActiveView(yearViewBtn);
    });
});