from datetime import datetime, date
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy import or_, extract, func
from app.models import db, Expense, EXPENSE_CATEGORIES, PAYMENT_METHODS
from app.services.analytics_service import get_current_month, get_category_expenses

expense_bp = Blueprint('expense', __name__, url_prefix='/expenses')

@expense_bp.route('/')
@login_required
def index():
    # Filter parameters
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()
    payment_method = request.args.get('payment_method', '').strip()
    month = request.args.get('month', '').strip()
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()

    query = Expense.query.filter_by(user_id=current_user.id)

    if search:
        query = query.filter(Expense.description.ilike(f'%{search}%'))
    
    if category and category != 'All':
        query = query.filter(Expense.category == category)

    if payment_method and payment_method != 'All':
        query = query.filter(Expense.payment_method == payment_method)

    if month:
        try:
            y, m = map(int, month.split('-'))
            query = query.filter(
                extract('year', Expense.date) == y,
                extract('month', Expense.date) == m
            )
        except ValueError:
            pass

    if start_date:
        try:
            s_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(Expense.date >= s_date)
        except ValueError:
            pass

    if end_date:
        try:
            e_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(Expense.date <= e_date)
        except ValueError:
            pass

    expenses = query.order_by(Expense.date.desc(), Expense.id.desc()).all()
    total_filtered = sum(e.amount for e in expenses)

    # Category summary for the current view
    curr_month = month or get_current_month()
    category_breakdown = get_category_expenses(current_user.id, curr_month)

    return render_template(
        'expense/index.html',
        expenses=expenses,
        total_filtered=total_filtered,
        categories=EXPENSE_CATEGORIES,
        payment_methods=PAYMENT_METHODS,
        search=search,
        selected_category=category,
        selected_pm=payment_method,
        selected_month=month,
        start_date=start_date,
        end_date=end_date,
        category_breakdown=category_breakdown,
        today_date=date.today().strftime('%Y-%m-%d')
    )


@expense_bp.route('/add', methods=['POST'])
@login_required
def add():
    amount_raw = request.form.get('amount', '').strip()
    category = request.form.get('category', 'Other').strip()
    date_raw = request.form.get('date', '').strip()
    description = request.form.get('description', '').strip()
    payment_method = request.form.get('payment_method', 'UPI').strip()

    if not amount_raw or not category or not date_raw:
        flash("Amount, category, and date are required.", "danger")
        return redirect(url_for('expense.index'))

    try:
        amount = float(amount_raw)
        if amount <= 0:
            flash("Expense amount must be positive.", "danger")
            return redirect(url_for('expense.index'))
    except ValueError:
        flash("Invalid expense amount.", "danger")
        return redirect(url_for('expense.index'))

    try:
        exp_date = datetime.strptime(date_raw, '%Y-%m-%d').date()
    except ValueError:
        exp_date = date.today()

    new_expense = Expense(
        user_id=current_user.id,
        amount=amount,
        category=category,
        date=exp_date,
        description=description,
        payment_method=payment_method
    )
    db.session.add(new_expense)
    db.session.commit()

    flash(f"Expense of {current_user.preferred_currency} {amount:,.2f} recorded under {category}!", "success")
    return redirect(url_for('expense.index', month=exp_date.strftime('%Y-%m')))


@expense_bp.route('/edit/<int:expense_id>', methods=['POST'])
@login_required
def edit(expense_id):
    expense = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first_or_404()

    amount_raw = request.form.get('amount', '').strip()
    category = request.form.get('category', expense.category).strip()
    date_raw = request.form.get('date', '').strip()
    description = request.form.get('description', '').strip()
    payment_method = request.form.get('payment_method', expense.payment_method).strip()

    try:
        amount = float(amount_raw)
        if amount <= 0:
            flash("Amount must be positive.", "danger")
            return redirect(url_for('expense.index'))
    except ValueError:
        flash("Invalid amount.", "danger")
        return redirect(url_for('expense.index'))

    try:
        exp_date = datetime.strptime(date_raw, '%Y-%m-%d').date()
    except ValueError:
        exp_date = expense.date

    expense.amount = amount
    expense.category = category
    expense.date = exp_date
    expense.description = description
    expense.payment_method = payment_method

    db.session.commit()
    flash("Expense updated successfully!", "success")
    return redirect(url_for('expense.index', month=exp_date.strftime('%Y-%m')))


@expense_bp.route('/delete/<int:expense_id>', methods=['POST'])
@login_required
def delete(expense_id):
    expense = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first_or_404()
    month_str = expense.date.strftime('%Y-%m')
    db.session.delete(expense)
    db.session.commit()
    flash("Expense entry removed.", "info")
    return redirect(url_for('expense.index', month=month_str))
