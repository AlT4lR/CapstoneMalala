import logging
from datetime import datetime, timedelta
import pytz
from calendar import month_name
from flask import current_app

logger = logging.getLogger(__name__)

# --- Configuration Constant: Defines the 100% scale for the monthly chart ---
# Setting the 100% mark at 2,000,000.0 for consistent chart scaling.
FIXED_MAX_EARNING_SCALE = 2000000.0

def get_analytics_data(username, branch, year, month):
    """
    Generates data for the main analytics chart.
    The percentage is calculated against a fixed maximum earnings scale.
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

        # --- Year Total Calculation ---
        year_pipeline = [
            {'$match': {**base_match, 'paidAt': {'$gte': year_start, '$lt': year_end}}},
            {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}
        ]
        year_result = list(db.transactions.aggregate(year_pipeline))
        total_year_earning = year_result[0]['total'] if year_result else 0.0

        # --- Monthly Totals for Chart ---
        month_pipeline = [
            {'$match': {**base_match, 'paidAt': {'$gte': year_start, '$lt': year_end}}},
            {'$group': {'_id': {'$month': '$paidAt'}, 'total': {'$sum': '$amount'}}}
        ]
        monthly_totals_docs = list(db.transactions.aggregate(month_pipeline))
        monthly_totals = {doc['_id']: doc['total'] for doc in monthly_totals_docs}
        
        # --- Generate Chart Data using FIXED_MAX_EARNING_SCALE ---
        chart_data = []
        for i in range(1, 13):
            total = monthly_totals.get(i, 0.0)
            
            # Calculate percentage against the fixed scale
            percentage = (total / FIXED_MAX_EARNING_SCALE) * 100
            
            chart_data.append({
                'month_name': month_name[i][:3].upper(),
                'month_name_full': month_name[i],
                'total': total,
                'percentage': min(100, percentage), # Cap at 100%
                'is_current_month': i == datetime.now().month and year == datetime.now().year
            })

        # --- Weekly Breakdown for Selected Month (Capped at 4 Weeks) ---
        weekly_pipeline = [
            {'$match': {**base_match, 'paidAt': {'$gte': month_start, '$lt': month_end}}},
            {'$project': { 
                'amount': 1, 
                'weekOfMonth': {
                    '$min': [ 
                        4, 
                        {'$add': [{'$floor': {'$divide': [{'$subtract': [{'$dayOfMonth': '$paidAt'}, 1]}, 7]}}, 1]}
                    ]
                }
            }},
            {'$group': { '_id': '$weekOfMonth', 'total': {'$sum': '$amount'}}},
            {'$sort': {'_id': 1}}
        ]
        weekly_docs = list(db.transactions.aggregate(weekly_pipeline))
        weekly_totals_dict = {doc['_id']: doc['total'] for doc in weekly_docs}
        weekly_breakdown = [{'week': f"Week {i}", 'total': weekly_totals_dict.get(i, 0.0)} for i in range(1, 5)]
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


def get_weekly_billing_summary(username, branch, year, week):
    db = current_app.db
    if db is None: return {}
    try:
        start_of_week = datetime.fromisocalendar(year, week, 1).replace(tzinfo=pytz.utc)
        end_of_week = start_of_week + timedelta(days=7)
        parent_folders = list(db.transactions.find({
            'username': username, 'branch': branch, 'status': 'Paid', 'parent_id': None, 
            'paidAt': {'$gte': start_of_week, '$lt': end_of_week},
            '$or': [{'isArchived': {'$exists': False}}, {'isArchived': False}]
        }))
        total_check_amount = sum(folder.get('amount', 0) for folder in parent_folders)
        parent_ids = [folder['_id'] for folder in parent_folders]
        total_ewt, total_countered = 0, 0
        if parent_ids:
            child_pipeline = [
                {'$match': {'parent_id': {'$in': parent_ids}}},
                {'$group': {'_id': None, 'total_ewt': {'$sum': {'$ifNull': ['$ewt', 0]}}, 'total_countered': {'$sum': {'$ifNull': ['$countered_check', 0]}}}}
            ]
            child_result = list(db.transactions.aggregate(child_pipeline))
            if child_result:
                total_ewt = child_result[0].get('total_ewt', 0)
                total_countered = child_result[0].get('total_countered', 0)
        loans_pipeline = [
            {'$match': {
                'username': username, 'branch': branch,
                'date_paid': {'$gte': start_of_week, '$lt': end_of_week},
                '$or': [{'isArchived': {'$exists': False}}, {'isArchived': False}]
            }},
            {'$group': {'_id': None, 'total_loans': {'$sum': '$amount'}}}
        ]
        loans_result = list(db.loans.aggregate(loans_pipeline))
        total_loans = loans_result[0]['total_loans'] if loans_result else 0
        return {
            'check_amount': total_check_amount, 'ewt_collected': total_ewt,
            'countered_check': total_countered, 'other_loans': total_loans
        }
    except Exception as e:
        logger.error(f"Error generating weekly billing summary for {username}: {e}", exc_info=True)
        return {}