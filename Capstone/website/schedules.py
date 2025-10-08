from flask import Blueprint, jsonify

schedules_bp = Blueprint('schedules', __name__)

@schedules_bp.route("/api/schedules")
def get_schedules():
    # Example static events to verify the calendar displays correctly
    return jsonify([
        {"title": "Sample Meeting", "start": "2025-10-10T09:00:00", "end": "2025-10-10T10:00:00", "category": "Work"},
        {"title": "Team Lunch", "start": "2025-10-12T12:00:00", "end": "2025-10-12T13:00:00", "category": "Personal"}
    ])
