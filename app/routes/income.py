from datetime import datetime, date
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import db, Income, INCOME_SOURCES
from app.services.analytics_service import (
    get_current_month,
    get_monthly_summary,
    get_income_sources
)

income_bp = Blueprint('income', __name__, url_prefix='/income')

@income_bp.route('/')
@login_required
def index():
    month = request.args.get('month', get_current_month())
    year = int(month.split('-')[0])

    summary = get_monthly_summary(current_user.id, month)
    sources = get_income_sources(current_user.id, month)

    # Incomes list ordered by date desc
    incomes = Income.query.filter_by(user_id=current_user.id).order_by(Income.date.desc()).all()

    return render_template(
        'income/index.html',
        incomes=incomes,
        summary=summary,
        sources=sources,
        selected_month=month,
        income_sources=INCOME_SOURCES
    )


@income_bp.route('/add', methods=['POST'])
@login_required
def add():
    amount_raw = request.form.get('amount', '').strip()
    source = request.form.get('source', 'Salary').strip()
    date_raw = request.form.get('date', '').strip()
    description = request.form.get('description', '').strip()

    if not amount_raw or not source or not date_raw:
        flash("Amount, source, and date are required.", "danger")
        return redirect(url_for('income.index'))

    try:
        amount = float(amount_raw)
        if amount <= 0:
            flash("Income amount must be greater than zero.", "danger")
            return redirect(url_for('income.index'))
    except ValueError:
        flash("Invalid amount entered.", "danger")
        return redirect(url_for('income.index'))

    try:
        inc_date = datetime.strptime(date_raw, '%Y-%m-%d').date()
    except ValueError:
        inc_date = date.today()

    new_income = Income(
        user_id=current_user.id,
        amount=amount,
        source=source,
        date=inc_date,
        description=description
    )
    db.session.add(new_income)
    db.session.commit()

    flash(f"Income of {current_user.preferred_currency} {amount:,.2f} added successfully!", "success")
    return redirect(url_for('income.index', month=inc_date.strftime('%Y-%m')))


@income_bp.route('/edit/<int:income_id>', methods=['POST'])
@login_required
def edit(income_id):
    income = Income.query.filter_by(id=income_id, user_id=current_user.id).first_or_404()

    amount_raw = request.form.get('amount', '').strip()
    source = request.form.get('source', income.source).strip()
    date_raw = request.form.get('date', '').strip()
    description = request.form.get('description', '').strip()

    try:
        amount = float(amount_raw)
        if amount <= 0:
            flash("Amount must be positive.", "danger")
            return redirect(url_for('income.index'))
    except ValueError:
        flash("Invalid amount.", "danger")
        return redirect(url_for('income.index'))

    try:
        inc_date = datetime.strptime(date_raw, '%Y-%m-%d').date()
    except ValueError:
        inc_date = income.date

    income.amount = amount
    income.source = source
    income.date = inc_date
    income.description = description

    db.session.commit()
    flash("Income record updated successfully!", "success")
    return redirect(url_for('income.index', month=inc_date.strftime('%Y-%m')))


@income_bp.route('/delete/<int:income_id>', methods=['POST'])
@login_required
def delete(income_id):
    income = Income.query.filter_by(id=income_id, user_id=current_user.id).first_or_404()
    month_str = income.date.strftime('%Y-%m')
    db.session.delete(income)
    db.session.commit()
    flash("Income entry deleted.", "info")
    return redirect(url_for('income.index', month=month_str))
