# website/models/analytics.py

import logging
from datetime import datetime, timedelta
import pytz
from calendar import month_name, monthrange
from flask import current_app

logger = logging.getLogger(__name__)

def get_analytics_data(username, branch, year, month):
    db = current_app.db
    if db is None: return {}

    try:
        year_start = datetime(year, 1, 1, tzinfo=pytz.utc)
        year_end = datetime(year + 1, 1, 1, tzinfo=pytz.utc)
        month_start = datetime(year, month, 1, tzinfo=pytz.utc)
        next_month_val = month + 1 if month < 12 else 1
        next_year_val = year if month < 12 else year + 1
        month_end = datetime(next_year_val, next_month_val, 1, tzinfo=pytz.utc)

        year_pipeline = [
            {'$match': {'username': username, 'branch': branch, 'status': 'Paid', 'parent_id': None, 'paidAt': {'$gte': year_start, '$lt': year_end}}},
            {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}
        ]
        year_result = list(db.transactions.aggregate(year_pipeline))
        total_year_earning = year_result[0]['total'] if year_result else 0.0

        month_pipeline = [
            {'$match': {'username': username, 'branch': branch, 'status': 'Paid', 'parent_id': None, 'paidAt': {'$gte': year_start, '$lt': year_end}}},
            {'$group': {'_id': {'$month': '$paidAt'}, 'total': {'$sum': '$amount'}}}
        ]
        monthly_totals_docs = list(db.transactions.aggregate(month_pipeline))
        monthly_totals = {doc['_id']: doc['total'] for doc in monthly_totals_docs}
        max_earning = max(monthly_totals.values()) if monthly_totals else 0

        chart_data = []
        for i in range(1, 13):
            total = monthly_totals.get(i, 0.0)
            percentage = (total / max_earning * 100) if max_earning > 0 else 0
            chart_data.append({
                'month_name': month_name[i][:3].upper(),
                'month_name_full': month_name[i],
                'total': total,
                'percentage': percentage,
                'is_current_month': i == datetime.now().month and year == datetime.now().year
            })

        # --- START OF MODIFICATION: More robust weekly breakdown logic ---
        weekly_pipeline = [
            {'$match': {'username': username, 'branch': branch, 'status': 'Paid', 'parent_id': None, 'paidAt': {'$gte': month_start, '$lt': month_end}}},
            {'$project': { 'amount': 1, 'weekOfMonth': {'$add': [{'$floor': {'$divide': [{'$subtract': [{'$dayOfMonth': '$paidAt'}, 1]}, 7]}}, 1]}}},
            {'$group': { '_id': '$weekOfMonth', 'total': {'$sum': '$amount'}}},
            {'$sort': {'_id': 1}}
        ]
        weekly_docs = list(db.transactions.aggregate(weekly_pipeline))
        weekly_totals_dict = {doc['_id']: doc['total'] for doc in weekly_docs}
        
        weekly_breakdown = []
        # A month can have up to 5 weeks with this logic (e.g., day 31 is in week 5). Loop to 6 for safety.
        for i in range(1, 7): 
            weekly_breakdown.append({
                'week': f"Week {i}",
                'total': weekly_totals_dict.get(i, 0.0)
            })
        # --- END OF MODIFICATION ---
        
        current_month_total = monthly_totals.get(month, 0.0)

        return {
            'year': year,
            'total_year_earning': total_year_earning,
            'current_month_name': month_name[month],
            'current_month_total': current_month_total,
            'chart_data': chart_data,
            'weekly_breakdown': weekly_breakdown,
        }
    except Exception as e:
        logger.error(f"Error getting analytics data for {username}: {e}", exc_info=True)
        return {}

def get_weekly_billing_summary(username, year, week):
    db = current_app.db
    if db is None: return {}
    try:
        start_of_week = datetime.fromisocalendar(year, week, 1).replace(tzinfo=pytz.utc)
        end_of_week = start_of_week + timedelta(days=7)
        
        parent_pipeline = [
            {'$match': {
                'username': username,
                'status': 'Paid',
                'parent_id': None, 
                'paidAt': {'$gte': start_of_week, '$lt': end_of_week}
            }},
            {'$group': {
                '_id': None,
                'total_check_amount': {'$sum': {'$ifNull': ['$amount', 0]}}
            }}
        ]
        parent_result = list(db.transactions.aggregate(parent_pipeline))

        child_pipeline = [
            {'$match': {
                'username': username,
                'status': 'Paid',
                'parent_id': {'$ne': None}, 
                'paidAt': {'$gte': start_of_week, '$lt': end_of_week}
            }},
            {'$group': {
                '_id': None,
                'total_ewt': {'$sum': {'$ifNull': ['$ewt', 0]}},
                'total_countered': {'$sum': {'$ifNull': ['$countered_check', 0]}}
            }}
        ]
        child_result = list(db.transactions.aggregate(child_pipeline))
        
        loans_pipeline = [
            {'$match': {
                'username': username,
                'date_paid': {'$gte': start_of_week, '$lt': end_of_week}
            }},
            {'$group': {
                '_id': None,
                'total_loans': {'$sum': '$amount'}
            }}
        ]
        loans_result = list(db.loans.aggregate(loans_pipeline))

        summary = {
            'check_amount': parent_result[0]['total_check_amount'] if parent_result else 0,
            'ewt_collected': child_result[0]['total_ewt'] if child_result else 0,
            'countered_check': child_result[0]['total_countered'] if child_result else 0,
            'other_loans': loans_result[0]['total_loans'] if loans_result else 0
        }
        return summary
    except Exception as e:
        logger.error(f"Error generating weekly billing summary for {username}: {e}", exc_info=True)
        return {}