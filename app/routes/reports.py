from datetime import datetime, date
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from app.services.analytics_service import (
    get_current_month,
    get_monthly_summary,
    get_category_expenses,
    get_income_sources,
    get_budget_utilization,
    get_financial_health_score
)
from app.services.ai_service import generate_ai_financial_recommendations

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

@reports_bp.route('/')
@login_required
def index():
    selected_month = request.args.get('month', get_current_month())

    summary = get_monthly_summary(current_user.id, selected_month)
    category_expenses = get_category_expenses(current_user.id, selected_month)
    income_sources = get_income_sources(current_user.id, selected_month)
    utilization = get_budget_utilization(current_user.id, selected_month)
    health = get_financial_health_score(current_user, selected_month)
    ai_insights = generate_ai_financial_recommendations(current_user, selected_month)

    # Human-readable month title
    y, m = map(int, selected_month.split('-'))
    month_title = datetime(y, m, 1).strftime('%B %Y')

    return render_template(
        'reports/index.html',
        selected_month=selected_month,
        month_title=month_title,
        summary=summary,
        category_expenses=category_expenses,
        income_sources=income_sources,
        utilization=utilization,
        health=health,
        recommendations=ai_insights['recommendations'],
        ai_analysis=ai_insights['ai_analysis']
    )
