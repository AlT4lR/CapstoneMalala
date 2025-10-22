from flask import render_template, request, jsonify, redirect, url_for, session
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime

from . import main # Import the blueprint
from ..models import get_analytics_data

@main.route('/analytics')
@jwt_required()
def analytics():
    username = get_jwt_identity()
    selected_branch = session.get('selected_branch')
    if not selected_branch:
        return redirect(url_for('main.branches'))
    
    initial_data = get_analytics_data(username, selected_branch, datetime.now().year, datetime.now().month)
    return render_template('analytics.html', analytics_data=initial_data, show_sidebar=True)

# --- Analytics API Routes ---
@main.route('/api/analytics/summary', methods=['GET'])
@jwt_required()
def get_analytics_summary():
    username = get_jwt_identity()
    selected_branch = session.get('selected_branch')
    if not selected_branch:
        return jsonify({'error': 'Branch not selected'}), 400
        
    try:
        year = int(request.args.get('year', datetime.now().year))
        month = int(request.args.get('month', datetime.now().month))
        if not (1 <= month <= 12):
            raise ValueError("Month is out of range")
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid year or month parameter'}), 400

    summary_data = get_analytics_data(username, selected_branch, year, month)
    return jsonify(summary_data)