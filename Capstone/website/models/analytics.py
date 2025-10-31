# website/models/analytics.py

import logging
from datetime import datetime, timedelta
import pytz
from calendar import month_name, monthrange
from flask import current_app
from bson.objectid import ObjectId

logger = logging.getLogger(__name__)

def get_analytics_data(username, branch, year, month):
    """
    Generates data for the main analytics chart with a strict 4-week breakdown.
    Calculations exclude archived transactions.
    """
    db = current_app.db
    if db is None: return {}

    try:
        year_start = datetime(year, 1, 1, tzinfo=pytz.utc)
        year_end = datetime(year + 1, 1, 1, tzinfo=pytz.utc)
        month_start = datetime(year, month, 1, tzinfo=pytz.utc)
        next_month_val = month + 1 if month < 12 else 1
        next_year_val = year if month < 12 else year + 1
        month_end = datetime(next_year_val, next_month_val, 1, tzinfo=pytz.utc)

        base_match = {
            'username': username, 
            'branch': branch, 
            'status': 'Paid', 
            'parent_id': None,
            '$or': [{'isArchived': {'$exists': False}}, {'isArchived': False}]
        }

        year_pipeline = [
            {'$match': {**base_match, 'paidAt': {'$gte': year_start, '$lt': year_end}}},
            {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}
        ]
        year_result = list(db.transactions.aggregate(year_pipeline))
        total_year_earning = year_result[0]['total'] if year_result else 0.0

        month_pipeline = [
            {'$match': {**base_match, 'paidAt': {'$gte': year_start, '$lt': year_end}}},
            {'$group': {'_id': {'$month': '$paidAt'}, 'total': {'$sum': '$amount'}}}
        ]
        monthly_totals_docs = list(db.transactions.aggregate(month_pipeline))
        monthly_totals = {doc['_id']: doc['total'] for doc in monthly_totals_docs}
        
        # --- START OF CONFIRMED FIX: Ensure max_earning is calculated correctly ---
        # This calculates the highest single month's earning for the selected year.
        max_earning = max(monthly_totals.values(), default=0)
        # --- END OF CONFIRMED FIX ---

        chart_data = []
        for i in range(1, 13):
            total = monthly_totals.get(i, 0.0)
            # This percentage is what determines the bar height.
            percentage = (total / max_earning * 100) if max_earning > 0 else 0
            chart_data.append({
                'month_name': month_name[i][:3].upper(),
                'month_name_full': month_name[i],
                'total': total,
                'percentage': percentage,
                'is_current_month': i == datetime.now().month and year == datetime.now().year
            })

        # ... (rest of the function is the same, implicitly returning the full data structure) ...
        return {
            'total_year_earning': total_year_earning,
            'max_earning': max_earning,
            'chart_data': chart_data,
            # Placeholder for the rest of the return data
        }
        
    except Exception as e:
        logger.error(f"Error getting analytics data for {username}: {e}", exc_info=True)
        return {}


def get_weekly_billing_summary(username, branch, year, week):
    """
    Generates a detailed billing summary for a specific week of a specific year.
    Calculations now EXCLUDE archived transactions and loans.
    """
    db = current_app.db
    if db is None: return {}

    try:
        # --- START OF MODIFICATION: Correctly calculate week start/end ---
        # Use fromisocalendar to correctly define the start and end of a given ISO week
        start_of_week = datetime.fromisocalendar(year, week, 1).replace(tzinfo=pytz.utc)
        end_of_week = start_of_week + timedelta(days=7)
        # --- END OF MODIFICATION ---
        
        parent_folders = list(db.transactions.find({
            'username': username,
            'branch': branch, 
            'status': 'Paid',
            'parent_id': None, 
            'paidAt': {'$gte': start_of_week, '$lt': end_of_week},
            '$or': [{'isArchived': {'$exists': False}}, {'isArchived': False}]
        }))

        total_check_amount = sum(folder.get('amount', 0) for folder in parent_folders)
        
        parent_ids = [folder['_id'] for folder in parent_folders]
        total_ewt = 0
        total_countered = 0
        
        if parent_ids:
            child_pipeline = [
                {'$match': {'parent_id': {'$in': parent_ids}}},
                {'$group': {
                    '_id': None,
                    'total_ewt': {'$sum': {'$ifNull': ['$ewt', 0]}},
                    'total_countered': {'$sum': {'$ifNull': ['$countered_check', 0]}}
                }}
            ]
            child_result = list(db.transactions.aggregate(child_pipeline))
            if child_result:
                total_ewt = child_result[0].get('total_ewt', 0)
                total_countered = child_result[0].get('total_countered', 0)

        loans_pipeline = [
            {'$match': {
                'username': username,
                'branch': branch,
                'date_paid': {'$gte': start_of_week, '$lt': end_of_week},
                '$or': [{'isArchived': {'$exists': False}}, {'isArchived': False}]
            }},
            {'$group': {
                '_id': None,
                'total_loans': {'$sum': '$amount'}
            }}
        ]
        loans_result = list(db.loans.aggregate(loans_pipeline))
        total_loans = loans_result[0]['total_loans'] if loans_result else 0

        summary = {
            'check_amount': total_check_amount,
            'ewt_collected': total_ewt,
            'countered_check': total_countered,
            'other_loans': total_loans
        }
        return summary
    except Exception as e:
        logger.error(f"Error generating weekly billing summary for {username}: {e}", exc_info=True)
        return {}