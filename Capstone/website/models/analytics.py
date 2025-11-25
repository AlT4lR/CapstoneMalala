# website/models/analytics.py

import logging
from datetime import datetime, timedelta
import pytz
from calendar import month_name, month_abbr
from flask import current_app

logger = logging.getLogger(__name__)


def get_analytics_data(username, branch, year, month):
    """
    Generates data for the main analytics chart. Bars reflect the total COVERED/COUNTERED amount.
    """
    db = current_app.db
    if db is None:
        return {}

    # Initialize variables to satisfy the linter/ensure proper scope within the try block
    year_start = None
    year_end = None
    month_start = None
    month_end = None
    base_match = {}

    try:
        # Date calculations for the year and current month
        year_start = pytz.utc.localize(datetime(year, 1, 1))
        year_end = pytz.utc.localize(datetime(year + 1, 1, 1))
        month_start = pytz.utc.localize(datetime(year, month, 1))

        next_month_val = month + 1 if month < 12 else 1
        next_year_val = year if month < 12 else year + 1
        month_end = pytz.utc.localize(datetime(next_year_val, next_month_val, 1))

        # Base filter (Paid parent folders only)
        base_match = {
            "username": username,
            "branch": branch,
            "status": "Paid",
            "parent_id": None,
            "paidAt": {"$exists": True, "$type": "date"},
            "$or": [
                {"isArchived": {"$exists": False}},
                {"isArchived": False},
            ],
        }

        # ---------------------------------------------------------
        # 1. Monthly Breakdown — COUNTERED CHECK (Covered Debt)
        # ---------------------------------------------------------
        month_pipeline = [
            {"$match": {**base_match, "paidAt": {"$gte": year_start, "$lt": year_end}}},
            {
                "$group": {
                    "_id": {"$month": "$paidAt"},
                    "total": {"$sum": "$countered_check"},  # Sums Parent's Covered Debt
                }
            },
            {"$sort": {"_id": 1}},
        ]

        monthly_totals_docs = list(db.transactions.aggregate(month_pipeline))
        monthly_totals = {doc["_id"]: doc["total"] for doc in monthly_totals_docs}

        # Determine the maximum monthly earning for dynamic chart scaling
        actual_max_earning = max(monthly_totals.values(), default=0)

        # Ensure a minimum scale for the chart, as the JS relies on this
        max_earning_for_chart_scale = max(actual_max_earning, 1000) 

        # Build chart data
        chart_data = []
        now = datetime.now()

        for i in range(1, 13):
            total = monthly_totals.get(i, 0.0)
            
            # Use the calculated scale for the percentage (this fixes the full bar issue)
            percentage = (total / max_earning_for_chart_scale * 100) if max_earning_for_chart_scale else 0

            chart_data.append({
                "month_name": month_abbr[i].upper(),
                "month_name_full": month_name[i],
                "total": total,
                "percentage": percentage,
                "is_current_month": (i == now.month and year == now.year),
            })

        # ---------------------------------------------------------
        # 2. Total for the Year
        # ---------------------------------------------------------
        total_year_earning = sum(monthly_totals.values())

        # ---------------------------------------------------------
        # 3. Weekly Breakdown for Selected Month
        # ---------------------------------------------------------
        weekly_pipeline = [
            {"$match": {**base_match, "paidAt": {"$gte": month_start, "$lt": month_end}}},
            {
                "$project": {
                    "amount": "$countered_check",  # parent covered debt
                    "weekOfMonth": {
                        "$min": [
                            4,
                            {
                                "$add": [
                                    {
                                        "$floor": {
                                            "$divide": [
                                                {"$subtract": [{"$dayOfMonth": "$paidAt"}, 1]},
                                                7
                                            ]
                                        }
                                    },
                                    1,
                                ]
                            },
                        ]
                    },
                }
            },
            {"$group": {"_id": "$weekOfMonth", "total": {"$sum": "$amount"}}},
            {"$sort": {"_id": 1}},
        ]

        weekly_docs = list(db.transactions.aggregate(weekly_pipeline))
        weekly_totals_dict = {doc["_id"]: doc["total"] for doc in weekly_docs}

        weekly_breakdown = [
            {"week": f"Week {i}", "total": weekly_totals_dict.get(i, 0.0)}
            for i in range(1, 5)
        ]

        current_month_total = monthly_totals.get(month, 0.0)

        return {
            "year": year,
            "max_earning_for_year": max_earning_for_chart_scale,
            "total_year_earning": total_year_earning,
            "current_month_name": month_name[month],
            "current_month_total": current_month_total,
            "chart_data": chart_data,
            "weekly_breakdown": weekly_breakdown,
        }

    except Exception as e:
        logger.error(f"Error getting analytics data for {username}: {e}", exc_info=True)

        # fallback chart (prevent frontend crash)
        fallback_chart_data = []
        now = datetime.now()

        for i in range(1, 13):
            fallback_chart_data.append({
                "month_name": month_abbr[i].upper(),
                "month_name_full": month_name[i],
                "total": 0.0,
                "percentage": 0,
                "is_current_month": (i == now.month and year == now.year),
            })

        return {
            "year": year,
            "total_year_earning": 0,
            "max_earning_for_year": 1000,
            "current_month_name": month_name[month],
            "current_month_total": 0,
            "chart_data": fallback_chart_data,
            "weekly_breakdown": [],
        }


def get_weekly_billing_summary(username, branch, year, week):
    """
    Generates a summary of billing for a specific week:
    - Total Check Amount (Target Debt)
    - EWT
    - Countered Checks (Covered Debt)
    - Loans
    """
    db = current_app.db
    if db is None:
        return {}

    try:
        # ISO week start/end
        start_of_week = datetime.fromisocalendar(year, week, 1).replace(tzinfo=pytz.utc)
        end_of_week = start_of_week + timedelta(days=7)

        # Parent folders (Paid)
        parent_folders = list(db.transactions.find({
            "username": username,
            "branch": branch,
            "status": "Paid",
            "parent_id": None,
            "paidAt": {"$gte": start_of_week, "$lt": end_of_week},
            "$or": [
                {"isArchived": {"$exists": False}},
                {"isArchived": False},
            ],
        }))

        # Sum correct fields from parent folder
        total_check_amount = sum(folder.get("amount", 0) for folder in parent_folders) # Target Debt
        total_countered_check = sum(folder.get("countered_check", 0) for folder in parent_folders) # Covered Debt
        total_ewt_collected = sum(folder.get("ewt", 0) for folder in parent_folders) # EWT

        # Loans
        loans_pipeline = [
            {"$match": {
                "username": username,
                "branch": branch,
                "date_paid": {"$gte": start_of_week, "$lt": end_of_week},
                "$or": [
                    {"isArchived": {"$exists": False}},
                    {"isArchived": False},
                ],
            }},
            {"$group": {"_id": None, "total_loans": {"$sum": "$amount"}}},
        ]

        loans_result = list(db.loans.aggregate(loans_pipeline))
        total_loans = loans_result[0]["total_loans"] if loans_result else 0

        return {
            "check_amount": total_check_amount, 
            "ewt_collected": total_ewt_collected,
            "countered_check": total_countered_check, 
            "other_loans": total_loans,
        }

    except Exception as e:
        logger.error(f"Error generating weekly billing summary for {username}: {e}", exc_info=True)
        return {}