import re
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import db, User
from app.routes.auth import EMAIL_REGEX

profile_bp = Blueprint('profile', __name__, url_prefix='/profile')

AVAILABLE_CURRENCIES = [
    ('INR', 'INR (₹) - Indian Rupee'),
    ('USD', 'USD ($) - US Dollar'),
    ('EUR', 'EUR (€) - Euro'),
    ('GBP', 'GBP (£) - British Pound'),
    ('JPY', 'JPY (¥) - Japanese Yen'),
    ('CAD', 'CAD (C$) - Canadian Dollar'),
    ('AUD', 'AUD (A$) - Australian Dollar')
]

@profile_bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        monthly_income_raw = request.form.get('monthly_income', '0').strip()
        monthly_savings_target_raw = request.form.get('monthly_savings_target', '0').strip()
        financial_goal = request.form.get('financial_goal', '').strip()
        preferred_currency = request.form.get('preferred_currency', 'INR').strip()

        errors = []
        if not full_name:
            errors.append("Full name is required.")
        if not email or not re.match(EMAIL_REGEX, email):
            errors.append("Valid email is required.")

        # Check duplicate email if changed
        if email != current_user.email:
            existing = User.query.filter_by(email=email).first()
            if existing:
                errors.append("This email is already in use by another account.")

        try:
            monthly_income = float(monthly_income_raw) if monthly_income_raw else 0.0
            if monthly_income < 0:
                errors.append("Monthly income cannot be negative.")
        except ValueError:
            errors.append("Invalid monthly income value.")

        try:
            savings_target = float(monthly_savings_target_raw) if monthly_savings_target_raw else 0.0
            if savings_target < 0:
                errors.append("Savings target cannot be negative.")
        except ValueError:
            errors.append("Invalid savings target value.")

        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template(
                'profile/index.html',
                currencies=AVAILABLE_CURRENCIES
            )

        # Update fields
        current_user.full_name = full_name
        current_user.email = email
        current_user.monthly_income = monthly_income
        current_user.monthly_savings_target = savings_target
        current_user.financial_goal = financial_goal
        current_user.preferred_currency = preferred_currency

        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for('profile.index'))

    return render_template(
        'profile/index.html',
        currencies=AVAILABLE_CURRENCIES
    )
