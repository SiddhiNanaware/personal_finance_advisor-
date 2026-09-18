from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.models import db, Budget, EXPENSE_CATEGORIES
from app.services.analytics_service import (
    get_current_month,
    get_budget_utilization,
    generate_suggested_budget
)

budget_bp = Blueprint('budget', __name__, url_prefix='/budget')

@budget_bp.route('/')
@login_required
def index():
    month = request.args.get('month', get_current_month())
    utilization = get_budget_utilization(current_user.id, month)
    auto_budget = generate_suggested_budget(current_user, month)

    # Categories that do not yet have a budget for this month
    configured_cats = {item['category'] for item in utilization['items']}
    available_cats = [c for c in EXPENSE_CATEGORIES if c not in configured_cats]

    return render_template(
        'budget/index.html',
        month=month,
        utilization=utilization,
        auto_budget=auto_budget,
        available_categories=available_cats,
        all_categories=EXPENSE_CATEGORIES
    )


@budget_bp.route('/set', methods=['POST'])
@login_required
def set_budget():
    category = request.form.get('category', '').strip()
    month = request.form.get('month', get_current_month()).strip()
    limit_raw = request.form.get('amount_limit', '').strip()

    if not category or not limit_raw:
        flash("Category and amount limit are required.", "danger")
        return redirect(url_for('budget.index', month=month))

    try:
        limit = float(limit_raw)
        if limit <= 0:
            flash("Budget limit must be greater than zero.", "danger")
            return redirect(url_for('budget.index', month=month))
    except ValueError:
        flash("Invalid limit entered.", "danger")
        return redirect(url_for('budget.index', month=month))

    existing = Budget.query.filter_by(
        user_id=current_user.id,
        month=month,
        category=category
    ).first()

    if existing:
        existing.amount_limit = limit
        flash(f"Budget for {category} updated to {current_user.preferred_currency} {limit:,.2f}.", "success")
    else:
        new_b = Budget(
            user_id=current_user.id,
            month=month,
            category=category,
            amount_limit=limit
        )
        db.session.add(new_b)
        flash(f"Budget limit set for {category}: {current_user.preferred_currency} {limit:,.2f}.", "success")

    db.session.commit()
    return redirect(url_for('budget.index', month=month))


@budget_bp.route('/delete/<int:budget_id>', methods=['POST'])
@login_required
def delete(budget_id):
    budget = Budget.query.filter_by(id=budget_id, user_id=current_user.id).first_or_404()
    month = budget.month
    db.session.delete(budget)
    db.session.commit()
    flash(f"Budget for {budget.category} removed.", "info")
    return redirect(url_for('budget.index', month=month))


@budget_bp.route('/auto-generate-preview')
@login_required
def auto_generate_preview():
    month = request.args.get('month', get_current_month())
    suggestion = generate_suggested_budget(current_user, month)
    return jsonify(suggestion)


@budget_bp.route('/apply-auto-budget', methods=['POST'])
@login_required
def apply_auto_budget():
    month = request.form.get('month', get_current_month()).strip()
    suggestion = generate_suggested_budget(current_user, month)

    # Save or update budgets for each recommended category
    count = 0
    for cat_data in suggestion['categories']:
        cat = cat_data['category']
        limit = cat_data['suggested_limit']

        existing = Budget.query.filter_by(
            user_id=current_user.id,
            month=month,
            category=cat
        ).first()

        if existing:
            existing.amount_limit = limit
        else:
            db.session.add(Budget(
                user_id=current_user.id,
                month=month,
                category=cat,
                amount_limit=limit
            ))
        count += 1

    db.session.commit()
    flash(f"Successfully applied AI-optimized 50/30/20 budget for {month} across {count} categories!", "success")
    return redirect(url_for('budget.index', month=month))
