from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, jsonify, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy import desc, extract, func
from app.models import (
    db, Income, Expense, Budget, Goal,
    EXPENSE_CATEGORIES, INCOME_SOURCES, PAYMENT_METHODS
)
from app.services.analytics_service import (
    get_current_month,
    get_monthly_summary,
    get_category_expenses,
    get_budget_utilization,
    get_monthly_trend,
    get_financial_health_score
)
from app.services.ai_service import generate_ai_financial_recommendations

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    current_month = get_current_month()
    summary = get_monthly_summary(current_user.id, current_month)
    utilization = get_budget_utilization(current_user.id, current_month)
    health = get_financial_health_score(current_user, current_month)
    ai_data = generate_ai_financial_recommendations(current_user, current_month)

    # Fetch recent transactions (Incomes + Expenses combined, sorted by date desc)
    recent_incomes = Income.query.filter_by(user_id=current_user.id).order_by(Income.date.desc(), Income.id.desc()).limit(5).all()
    recent_expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.date.desc(), Expense.id.desc()).limit(5).all()

    transactions = []
    for inc in recent_incomes:
        transactions.append({
            'type': 'income',
            'title': inc.source,
            'description': inc.description or 'Income deposit',
            'amount': inc.amount,
            'date': inc.date,
            'category': inc.source,
            'badge_class': 'success'
        })
    for exp in recent_expenses:
        transactions.append({
            'type': 'expense',
            'title': exp.category,
            'description': exp.description or f"Payment via {exp.payment_method}",
            'amount': exp.amount,
            'date': exp.date,
            'category': exp.category,
            'badge_class': 'danger'
        })

    transactions.sort(key=lambda x: x['date'], reverse=True)
    recent_transactions = transactions[:7]

    # Active goals
    goals = Goal.query.filter_by(user_id=current_user.id).all()

    return render_template(
        'dashboard/index.html',
        summary=summary,
        utilization=utilization,
        health=health,
        recommendations=ai_data['recommendations'],
        ai_analysis=ai_data['ai_analysis'],
        recent_transactions=recent_transactions,
        goals=goals,
        current_month=current_month,
        expense_categories=EXPENSE_CATEGORIES,
        income_sources=INCOME_SOURCES,
        payment_methods=PAYMENT_METHODS
    )


@dashboard_bp.route('/api/dashboard-charts')
@login_required
def dashboard_charts():
    month = request.args.get('month', get_current_month())
    
    # Category expenses
    cat_expenses = get_category_expenses(current_user.id, month)
    category_labels = [c['category'] for c in cat_expenses]
    category_data = [c['amount'] for c in cat_expenses]

    # Monthly 6-month trend
    trend = get_monthly_trend(current_user.id, months_count=6)
    trend_labels = [t['label'] for t in trend]
    trend_income = [t['income'] for t in trend]
    trend_expense = [t['expense'] for t in trend]
    trend_savings = [t['savings'] for t in trend]

    # Payment methods breakdown
    year, m = map(int, month.split('-'))
    pm_query = db.session.query(
        Expense.payment_method,
        func.coalesce(func.sum(Expense.amount), 0.0)
    ).filter(
        Expense.user_id == current_user.id,
        extract('year', Expense.date) == year,
        extract('month', Expense.date) == m
    ).group_by(Expense.payment_method).all()

    pm_labels = [pm[0] for pm in pm_query]
    pm_data = [round(pm[1], 2) for pm in pm_query]

    return jsonify({
        'categories': {
            'labels': category_labels,
            'data': category_data
        },
        'trend': {
            'labels': trend_labels,
            'income': trend_income,
            'expense': trend_expense,
            'savings': trend_savings
        },
        'payment_methods': {
            'labels': pm_labels,
            'data': pm_data
        }
    })


@dashboard_bp.route('/seed-demo-data', methods=['POST'])
@login_required
def seed_demo_data():
    """
    Seeds a realistic sample dataset for the logged-in user so they can immediately
    explore charts, overspending warnings, reports, and AI advice.
    """
    today = date.today()
    curr_month_str = today.strftime('%Y-%m')

    # Update profile defaults if 0
    if current_user.monthly_income <= 0:
        current_user.monthly_income = 65000.0
    if current_user.monthly_savings_target <= 0:
        current_user.monthly_savings_target = 15000.0
    current_user.financial_goal = 'Emergency Fund & Home Down Payment'

    # Sample Incomes for current month & past month
    incomes_data = [
        {'amount': 55000.0, 'source': 'Salary', 'date': today.replace(day=1), 'desc': 'Primary Monthly Salary'},
        {'amount': 10000.0, 'source': 'Freelancing', 'date': today.replace(day=5), 'desc': 'UI Design Freelance Project'},
        {'amount': 2500.0, 'source': 'Other', 'date': today.replace(day=12), 'desc': 'Dividend Payout'}
    ]
    for inc in incomes_data:
        db.session.add(Income(
            user_id=current_user.id,
            amount=inc['amount'],
            source=inc['source'],
            date=inc['date'],
            description=inc['desc']
        ))

    # Sample Expenses for current month demonstrating various categories and budget thresholds
    sample_expenses = [
        {'amount': 18000.0, 'category': 'Rent', 'day': 2, 'desc': 'Monthly Apartment Rent', 'pm': 'Bank Transfer'},
        {'amount': 6500.0, 'category': 'Food', 'day': 4, 'desc': 'Supermarket Groceries', 'pm': 'UPI'},
        {'amount': 2200.0, 'category': 'Food', 'day': 9, 'desc': 'Dinner at Italian Restaurant', 'pm': 'Credit Card'},
        {'amount': 2800.0, 'category': 'Utilities', 'day': 6, 'desc': 'Electricity & Water Bill', 'pm': 'UPI'},
        {'amount': 1499.0, 'category': 'Bills', 'day': 7, 'desc': 'Fiber Broadband & Mobile Recharge', 'pm': 'UPI'},
        {'amount': 3200.0, 'category': 'Transport', 'day': 10, 'desc': 'Metro Pass & Fuel', 'pm': 'Debit Card'},
        {'amount': 4500.0, 'category': 'Entertainment', 'day': 11, 'desc': 'Concert Tickets & Movies', 'pm': 'Credit Card'},
        {'amount': 7200.0, 'category': 'Shopping', 'day': 13, 'desc': 'Clothing & Footwear Sale', 'pm': 'Credit Card'},
        {'amount': 1500.0, 'category': 'Healthcare', 'day': 14, 'desc': 'Pharmacy & Health Vitamins', 'pm': 'UPI'},
        {'amount': 2000.0, 'category': 'Education', 'day': 8, 'desc': 'Online Coding Certification Course', 'pm': 'Debit Card'}
    ]

    for exp in sample_expenses:
        try:
            exp_date = today.replace(day=min(exp['day'], 28))
        except ValueError:
            exp_date = today
        db.session.add(Expense(
            user_id=current_user.id,
            amount=exp['amount'],
            category=exp['category'],
            date=exp_date,
            description=exp['desc'],
            payment_method=exp['pm']
        ))

    # Sample Budgets for current month to demonstrate Under 70%, 70-90%, and Over 100%
    sample_budgets = [
        {'cat': 'Rent', 'limit': 18000.0},          # 100% (Near Limit / Exact)
        {'cat': 'Food', 'limit': 9000.0},           # 8700 / 9000 = 96.6% (Near Limit)
        {'cat': 'Transport', 'limit': 4000.0},      # 3200 / 4000 = 80.0% (Warning)
        {'cat': 'Utilities', 'limit': 3500.0},      # 2800 / 3500 = 80.0% (Warning)
        {'cat': 'Entertainment', 'limit': 3500.0},  # 4500 / 3500 = 128.5% (Overspending!)
        {'cat': 'Shopping', 'limit': 6000.0},       # 7200 / 6000 = 120.0% (Overspending!)
        {'cat': 'Education', 'limit': 5000.0},      # 2000 / 5000 = 40.0% (Normal)
        {'cat': 'Healthcare', 'limit': 4000.0}      # 1500 / 4000 = 37.5% (Normal)
    ]

    for b in sample_budgets:
        existing = Budget.query.filter_by(
            user_id=current_user.id,
            month=curr_month_str,
            category=b['cat']
        ).first()
        if existing:
            existing.amount_limit = b['limit']
        else:
            db.session.add(Budget(
                user_id=current_user.id,
                month=curr_month_str,
                category=b['cat'],
                amount_limit=b['limit']
            ))

    # Sample Goals
    sample_goals = [
        {
            'title': 'Emergency Fund (6 Months Expenses)',
            'target': 150000.0,
            'current': 95000.0,
            'target_date': date(today.year, 12, 31),
            'status': 'In Progress'
        },
        {
            'title': 'MacBook Pro Upgrade',
            'target': 120000.0,
            'current': 120000.0,
            'target_date': date(today.year, today.month, 15),
            'status': 'Completed'
        },
        {
            'title': 'Annual Vacation Trip',
            'target': 40000.0,
            'current': 16000.0,
            'target_date': date(today.year + 1, 3, 31),
            'status': 'In Progress'
        }
    ]

    for g in sample_goals:
        existing_g = Goal.query.filter_by(user_id=current_user.id, title=g['title']).first()
        if not existing_g:
            db.session.add(Goal(
                user_id=current_user.id,
                title=g['title'],
                target_amount=g['target'],
                current_amount=g['current'],
                target_date=g['target_date'],
                status=g['status']
            ))

    db.session.commit()
    flash("Sample data successfully loaded! Explore your charts, budget meters, and AI advisor.", "success")
    return redirect(url_for('dashboard.index'))
