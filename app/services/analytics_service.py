from datetime import datetime, date
from calendar import monthrange
from sqlalchemy import func, extract
from app.models import db, Income, Expense, Budget, Goal, EXPENSE_CATEGORIES

NEEDS_CATEGORIES = {'Rent', 'Food', 'Utilities', 'Bills', 'Healthcare', 'Transport', 'Education'}
WANTS_CATEGORIES = {'Shopping', 'Entertainment', 'Travel', 'Personal', 'Other'}

def get_current_month():
    return datetime.now().strftime('%Y-%m')

def get_monthly_summary(user_id, month_str=None):
    if not month_str:
        month_str = get_current_month()

    year, month = map(int, month_str.split('-'))

    # Total income for this month
    monthly_income = db.session.query(func.coalesce(func.sum(Income.amount), 0.0)).filter(
        Income.user_id == user_id,
        extract('year', Income.date) == year,
        extract('month', Income.date) == month
    ).scalar()

    # Total expenses for this month
    monthly_expense = db.session.query(func.coalesce(func.sum(Expense.amount), 0.0)).filter(
        Expense.user_id == user_id,
        extract('year', Expense.date) == year,
        extract('month', Expense.date) == month
    ).scalar()

    # Yearly totals
    yearly_income = db.session.query(func.coalesce(func.sum(Income.amount), 0.0)).filter(
        Income.user_id == user_id,
        extract('year', Income.date) == year
    ).scalar()

    yearly_expense = db.session.query(func.coalesce(func.sum(Expense.amount), 0.0)).filter(
        Expense.user_id == user_id,
        extract('year', Expense.date) == year
    ).scalar()

    savings = monthly_income - monthly_expense
    savings_rate = (savings / monthly_income * 100) if monthly_income > 0 else 0.0

    return {
        'month': month_str,
        'year': year,
        'monthly_income': round(monthly_income, 2),
        'monthly_expense': round(monthly_expense, 2),
        'monthly_savings': round(savings, 2),
        'savings_rate': round(savings_rate, 1),
        'yearly_income': round(yearly_income, 2),
        'yearly_expense': round(yearly_expense, 2),
        'yearly_savings': round(yearly_income - yearly_expense, 2)
    }

def get_category_expenses(user_id, month_str=None):
    if not month_str:
        month_str = get_current_month()
    year, month = map(int, month_str.split('-'))

    results = db.session.query(
        Expense.category,
        func.coalesce(func.sum(Expense.amount), 0.0).label('total')
    ).filter(
        Expense.user_id == user_id,
        extract('year', Expense.date) == year,
        extract('month', Expense.date) == month
    ).group_by(Expense.category).order_by(func.sum(Expense.amount).desc()).all()

    total_expense = sum(r[1] for r in results) or 1.0

    breakdown = []
    for cat, amt in results:
        breakdown.append({
            'category': cat,
            'amount': round(amt, 2),
            'percentage': round((amt / total_expense) * 100, 1)
        })

    return breakdown

def get_income_sources(user_id, month_str=None):
    if not month_str:
        month_str = get_current_month()
    year, month = map(int, month_str.split('-'))

    results = db.session.query(
        Income.source,
        func.coalesce(func.sum(Income.amount), 0.0).label('total')
    ).filter(
        Income.user_id == user_id,
        extract('year', Income.date) == year,
        extract('month', Income.date) == month
    ).group_by(Income.source).order_by(func.sum(Income.amount).desc()).all()

    total_income = sum(r[1] for r in results) or 1.0
    breakdown = []
    for src, amt in results:
        breakdown.append({
            'source': src,
            'amount': round(amt, 2),
            'percentage': round((amt / total_income) * 100, 1)
        })

    return breakdown

def get_budget_utilization(user_id, month_str=None):
    if not month_str:
        month_str = get_current_month()
    year, month = map(int, month_str.split('-'))

    budgets = Budget.query.filter_by(user_id=user_id, month=month_str).all()
    
    # Calculate actual expenses per category for this month
    expense_query = db.session.query(
        Expense.category,
        func.coalesce(func.sum(Expense.amount), 0.0).label('spent')
    ).filter(
        Expense.user_id == user_id,
        extract('year', Expense.date) == year,
        extract('month', Expense.date) == month
    ).group_by(Expense.category).all()

    spent_dict = {cat: amt for cat, amt in expense_query}

    utilization_list = []
    total_budgeted = 0.0
    total_spent_budgeted = 0.0

    for b in budgets:
        spent = spent_dict.get(b.category, 0.0)
        remaining = b.amount_limit - spent
        pct = (spent / b.amount_limit * 100) if b.amount_limit > 0 else 0.0

        # Warning thresholds:
        # Under 70% -> Normal
        # 70-90% -> Warning
        # Above 90% -> Near Limit
        # Above 100% -> Overspending
        if pct > 100.0:
            status = 'Overspending'
            badge_class = 'danger'
            bar_color = 'bg-danger'
        elif pct >= 90.0:
            status = 'Near Limit'
            badge_class = 'warning text-dark'
            bar_color = 'bg-warning'
        elif pct >= 70.0:
            status = 'Warning'
            badge_class = 'info text-dark'
            bar_color = 'bg-info'
        else:
            status = 'Normal'
            badge_class = 'success'
            bar_color = 'bg-success'

        total_budgeted += b.amount_limit
        total_spent_budgeted += spent

        utilization_list.append({
            'id': b.id,
            'category': b.category,
            'amount_limit': round(b.amount_limit, 2),
            'spent': round(spent, 2),
            'remaining': round(remaining, 2),
            'percentage': round(pct, 1),
            'status': status,
            'badge_class': badge_class,
            'bar_color': bar_color
        })

    # Sort so overspending and near-limit appear first
    utilization_list.sort(key=lambda x: x['percentage'], reverse=True)

    overall_pct = (total_spent_budgeted / total_budgeted * 100) if total_budgeted > 0 else 0.0
    return {
        'category_budgets': utilization_list,
        'items': utilization_list,
        'total_budgeted': round(total_budgeted, 2),
        'total_spent': round(total_spent_budgeted, 2),
        'total_remaining': round(total_budgeted - total_spent_budgeted, 2),
        'overall_percentage': round(overall_pct, 1)
    }

def generate_suggested_budget(user, month_str=None):
    """
    Intelligent Auto Budget Generator:
    Applies the 50/30/20 financial rule (Needs 50%, Wants 30%, Savings 20%),
    customized by user's savings target and historical spending habits.
    """
    if not month_str:
        month_str = get_current_month()
    year, month = map(int, month_str.split('-'))

    # Determine baseline income: monthly income from recorded income this month, or user profile monthly_income
    summary = get_monthly_summary(user.id, month_str)
    effective_income = summary['monthly_income']
    if effective_income <= 0 and user.monthly_income and user.monthly_income > 0:
        effective_income = user.monthly_income

    if effective_income <= 0:
        effective_income = 50000.0  # Reasonable fallback baseline if user has 0 entered yet

    # Savings target: either user's defined target or 20% standard
    if user.monthly_savings_target and user.monthly_savings_target > 0:
        savings_target = min(user.monthly_savings_target, effective_income * 0.4)
    else:
        savings_target = effective_income * 0.20

    spendable_income = max(effective_income - savings_target, effective_income * 0.6)
    
    # 50/30 split of total income or 62.5% / 37.5% of spendable income:
    needs_budget = effective_income * 0.50
    wants_budget = effective_income * 0.30

    # Ensure total allocated equals spendable_income
    total_allocated = needs_budget + wants_budget
    if total_allocated > 0:
        factor = spendable_income / total_allocated
        needs_budget *= factor
        wants_budget *= factor

    # Get user's past 3 months expense history to weight categories
    past_expenses = db.session.query(
        Expense.category,
        func.coalesce(func.sum(Expense.amount), 0.0)
    ).filter(Expense.user_id == user.id).group_by(Expense.category).all()
    past_dict = {cat: amt for cat, amt in past_expenses}

    # Standard distribution weights within Needs
    default_needs_weights = {
        'Rent': 0.35,
        'Food': 0.25,
        'Utilities': 0.10,
        'Bills': 0.10,
        'Transport': 0.10,
        'Healthcare': 0.05,
        'Education': 0.05
    }

    # Standard distribution weights within Wants
    default_wants_weights = {
        'Entertainment': 0.25,
        'Shopping': 0.30,
        'Travel': 0.15,
        'Personal': 0.20,
        'Other': 0.10
    }

    suggested_categories = []

    # Allocate Needs
    needs_total_past = sum(past_dict.get(c, 0.0) for c in NEEDS_CATEGORIES)
    for cat in sorted(NEEDS_CATEGORIES):
        if needs_total_past > 0 and cat in past_dict:
            weight = 0.5 * default_needs_weights.get(cat, 0.1) + 0.5 * (past_dict[cat] / needs_total_past)
        else:
            weight = default_needs_weights.get(cat, 0.1)
        allocated = round(needs_budget * weight, -1)  # round to nearest 10
        suggested_categories.append({
            'category': cat,
            'type': 'Needs (50%)',
            'suggested_limit': max(allocated, 500.0)
        })

    # Allocate Wants
    wants_total_past = sum(past_dict.get(c, 0.0) for c in WANTS_CATEGORIES)
    for cat in sorted(WANTS_CATEGORIES):
        if wants_total_past > 0 and cat in past_dict:
            weight = 0.5 * default_wants_weights.get(cat, 0.1) + 0.5 * (past_dict[cat] / wants_total_past)
        else:
            weight = default_wants_weights.get(cat, 0.1)
        allocated = round(wants_budget * weight, -1)
        suggested_categories.append({
            'category': cat,
            'type': 'Wants (30%)',
            'suggested_limit': max(allocated, 300.0)
        })

    total_suggested = sum(c['suggested_limit'] for c in suggested_categories)

    return {
        'month': month_str,
        'effective_income': round(effective_income, 2),
        'needs_budget': round(needs_budget, 2),
        'wants_budget': round(wants_budget, 2),
        'savings_target': round(savings_target, 2),
        'total_suggested_budget': round(total_suggested, 2),
        'categories': suggested_categories
    }

def get_monthly_trend(user_id, months_count=6):
    """
    Returns monthly income, expense, and savings for the last N months.
    """
    today = date.today()
    trend = []
    
    for i in range(months_count - 1, -1, -1):
        # Calculate year and month offset
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        m_str = f"{y:04d}-{m:02d}"
        summary = get_monthly_summary(user_id, m_str)
        month_label = datetime(y, m, 1).strftime('%b %Y')
        trend.append({
            'month_key': m_str,
            'label': month_label,
            'income': summary['monthly_income'],
            'expense': summary['monthly_expense'],
            'savings': summary['monthly_savings']
        })

    return trend

def get_financial_health_score(user, month_str=None):
    """
    Calculates Financial Health Score (0-100) based on:
    - Savings Rate (0-35 points)
    - Budget Compliance (0-35 points)
    - Needs vs Wants balance (0-20 points)
    - Goals progress (0-10 points)
    """
    summary = get_monthly_summary(user.id, month_str)
    utilization = get_budget_utilization(user.id, month_str)
    
    score = 0
    feedback = []

    # 1. Savings Rate Evaluation (0-35 pts)
    savings_rate = summary['savings_rate']
    if savings_rate >= 25.0:
        score += 35
        feedback.append("Superb savings rate (>25%).")
    elif savings_rate >= 15.0:
        score += 25
        feedback.append("Healthy savings rate (15-25%).")
    elif savings_rate > 0.0:
        score += 15
        feedback.append("Positive savings, but try to reach at least 20%.")
    else:
        score += 5
        feedback.append("Negative or zero savings this month.")

    # 2. Budget Adherence (0-35 pts)
    items = utilization['items']
    if not items:
        score += 20
        feedback.append("No active budget limits set. Setting category budgets helps control spending.")
    else:
        overspent_count = sum(1 for item in items if item['percentage'] > 100.0)
        near_limit_count = sum(1 for item in items if 90.0 <= item['percentage'] <= 100.0)
        if overspent_count == 0 and near_limit_count == 0:
            score += 35
            feedback.append("Excellent budget discipline! All categories within limits.")
        elif overspent_count == 0:
            score += 25
            feedback.append("Good budget management with a few categories nearing limits.")
        elif overspent_count <= 2:
            score += 15
            feedback.append(f"Attention needed: {overspent_count} categories have exceeded budget limits.")
        else:
            score += 5
            feedback.append(f"High risk: {overspent_count} categories have overspent significantly.")

    # 3. Expense to Income Ratio (0-20 pts)
    if summary['monthly_income'] > 0:
        ratio = summary['monthly_expense'] / summary['monthly_income']
        if ratio <= 0.60:
            score += 20
        elif ratio <= 0.80:
            score += 15
        elif ratio <= 1.0:
            score += 8
        else:
            score += 0
            feedback.append("Expenses exceed monthly income!")
    else:
        score += 10

    # 4. Goals Progress (0-10 pts)
    goals = Goal.query.filter_by(user_id=user.id).all()
    if goals:
        completed = sum(1 for g in goals if g.status == 'Completed' or g.percentage >= 100.0)
        if completed > 0:
            score += 10
            feedback.append("Great progress on financial goals!")
        else:
            score += 7
    else:
        score += 5

    score = min(max(int(score), 0), 100)

    if score >= 85:
        rating = 'Excellent'
        badge_class = 'success'
    elif score >= 70:
        rating = 'Good'
        badge_class = 'primary'
    elif score >= 50:
        rating = 'Fair'
        badge_class = 'warning text-dark'
    else:
        rating = 'Needs Attention'
        badge_class = 'danger'

    return {
        'score': score,
        'rating': rating,
        'badge_class': badge_class,
        'feedback': feedback
    }
