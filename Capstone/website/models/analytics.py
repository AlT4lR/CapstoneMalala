# website/models/analytics.py

import logging
from datetime import datetime, timedelta
import pytz
from calendar import month_name
from flask import current_app

logger = logging.getLogger(__name__)

def get_analytics_data(username, branch, year, month):
    """
    Generates data for the main analytics chart with a dynamic scale based on the year's max earning.
    The total amount is correctly calculated from the 'amount' field of 'Paid' parent folders.
    """
    db = current_app.db
    if db is None: return {}

    try:
        # Date calculations for the year and current month
        # Timezone-aware datetimes for MongoDB queries
        year_start = pytz.utc.localize(datetime(year, 1, 1))
        year_end = pytz.utc.localize(datetime(year + 1, 1, 1))
        month_start = pytz.utc.localize(datetime(year, month, 1))
        
        # Calculate the start of the next month for a clean boundary
        next_month_val = month + 1 if month < 12 else 1
        next_year_val = year if month < 12 else year + 1
        month_end = pytz.utc.localize(datetime(next_year_val, next_month_val, 1))

        # Base filter for all analytics queries
        base_match = {
            'username': username, 
            'branch': branch, 
            'status': 'Paid', 
            'parent_id': None,
            'paidAt': {'$exists': True, '$type': "date"},
            '$or': [{'isArchived': {'$exists': False}}, {'isArchived': False}]
        }

        # 1. Monthly Breakdowns for Chart Data
        month_pipeline = [
            {'$match': {**base_match, 'paidAt': {'$gte': year_start, '$lt': year_end}}},
            {'$group': {'_id': {'$month': '$paidAt'}, 'total': {'$sum': '$amount'}}},
            {'$sort': {'_id': 1}}
        ]
        monthly_totals_docs = list(db.transactions.aggregate(month_pipeline))
        monthly_totals = {doc['_id']: doc['total'] for doc in monthly_totals_docs}
        
        # Determine the maximum monthly earning for dynamic chart scaling
        max_earning_for_year = max(monthly_totals.values(), default=0)

        chart_data = []
        for i in range(1, 13):
            total = monthly_totals.get(i, 0.0)
            # Calculate each bar's height relative to the year's highest earning month.
            percentage = (total / max_earning_for_year * 100) if max_earning_for_year > 0 else 0
            chart_data.append({
                'month_name': month_name[i][:3].upper(),
                'month_name_full': month_name[i],
                'total': total,
                'percentage': percentage,
                'is_current_month': i == datetime.now().month and year == datetime.now().year
            })
            
        # 2. Total Earning for the Year (Sum of all monthly totals)
        total_year_earning = sum(monthly_totals.values())

        # 3. Weekly Breakdown for Current Month
        weekly_pipeline = [
            {'$match': {**base_match, 'paidAt': {'$gte': month_start, '$lt': month_end}}},
            {'$project': { 
                'amount': 1, 
                # $dayOfMonth - 1 / 7, floor it, and add 1 gives the week number
                # We use a $min to cap the week at 4 for display purposes in a standard 4-week breakdown
                'weekOfMonth': {'$min': [ 4, {'$add': [{'$floor': {'$divide': [{'$subtract': [{'$dayOfMonth': '$paidAt'}, 1]}, 7]}}, 1]}]}
            }},
            {'$group': { '_id': '$weekOfMonth', 'total': {'$sum': '$amount'}}},
            {'$sort': {'_id': 1}}
        ]
        weekly_docs = list(db.transactions.aggregate(weekly_pipeline))
        weekly_totals_dict = {doc['_id']: doc['total'] for doc in weekly_docs}
        
        # Populate the final 4-week structure
        weekly_breakdown = [{'week': f"Week {i}", 'total': weekly_totals_dict.get(i, 0.0)} for i in range(1, 5)]
        current_month_total = monthly_totals.get(month, 0.0)

        return {
            'year': year,
            'total_year_earning': total_year_earning,
            'max_earning_for_year': max_earning_for_year, 
            'current_month_name': month_name[month],
            'current_month_total': current_month_total,
            'chart_data': chart_data,
            'weekly_breakdown': weekly_breakdown,
        }
    except Exception as e:
        logger.error(f"Error getting analytics data for {username}: {e}", exc_info=True)
        # Fallback chart data to prevent client-side JS errors on rendering
        fallback_chart_data = []
        for i in range(1, 13):
            fallback_chart_data.append({
                'month_name': month_name[i][:3].upper(),
                'month_name_full': month_name[i],
                'total': 0.0,
                'percentage': 0,
                'is_current_month': i == datetime.now().month and year == datetime.now().year
            })

        return {
            'year': year, 'total_year_earning': 0, 'max_earning_for_year': 0,
            'current_month_name': month_name[month], 'current_month_total': 0,
            'chart_data': fallback_chart_data, 'weekly_breakdown': []
        }

def get_weekly_billing_summary(username, branch, year, week):
    """
    Generates a summary of billing for a specific week, including transactions, EWT, countered checks, and loans.
    """
    db = current_app.db
    if db is None: return {}
    try:
        # Calculate start and end of the specified ISO week
        start_of_week = datetime.fromisocalendar(year, week, 1).replace(tzinfo=pytz.utc)
        end_of_week = start_of_week + timedelta(days=7)
        
        # Find parent transactions (the checks/billing folders) for the week
        parent_folders = list(db.transactions.find({
            'username': username, 'branch': branch, 'status': 'Paid', 'parent_id': None, 
            'paidAt': {'$gte': start_of_week, '$lt': end_of_week},
            '$or': [{'isArchived': {'$exists': False}}, {'isArchived': False}]
        }))
        total_check_amount = sum(folder.get('amount', 0) for folder in parent_folders)
        parent_ids = [folder['_id'] for folder in parent_folders]
        
        # Aggregate child transactions (EWT and Countered Checks)
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

        # Aggregate loans paid within the week
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