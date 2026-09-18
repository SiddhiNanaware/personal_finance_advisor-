from datetime import datetime, date
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import db, Goal

goals_bp = Blueprint('goals', __name__, url_prefix='/goals')

@goals_bp.route('/')
@login_required
def index():
    goals = Goal.query.filter_by(user_id=current_user.id).order_by(Goal.status.asc(), Goal.created_at.desc()).all()
    
    total_target = sum(g.target_amount for g in goals)
    total_saved = sum(g.current_amount for g in goals)
    overall_progress = (total_saved / total_target * 100) if total_target > 0 else 0.0

    return render_template(
        'goals/index.html',
        goals=goals,
        total_target=total_target,
        total_saved=total_saved,
        overall_progress=round(overall_progress, 1),
        today_date=date.today().strftime('%Y-%m-%d')
    )


@goals_bp.route('/add', methods=['POST'])
@login_required
def add():
    title = request.form.get('title', '').strip()
    target_amount_raw = request.form.get('target_amount', '').strip()
    current_amount_raw = request.form.get('current_amount', '0').strip()
    target_date_raw = request.form.get('target_date', '').strip()

    if not title or not target_amount_raw:
        flash("Title and target amount are required.", "danger")
        return redirect(url_for('goals.index'))

    try:
        target = float(target_amount_raw)
        curr = float(current_amount_raw) if current_amount_raw else 0.0
        if target <= 0:
            flash("Target amount must be greater than zero.", "danger")
            return redirect(url_for('goals.index'))
    except ValueError:
        flash("Invalid target amount.", "danger")
        return redirect(url_for('goals.index'))

    t_date = None
    if target_date_raw:
        try:
            t_date = datetime.strptime(target_date_raw, '%Y-%m-%d').date()
        except ValueError:
            pass

    status = 'Completed' if curr >= target else 'In Progress'

    new_goal = Goal(
        user_id=current_user.id,
        title=title,
        target_amount=target,
        current_amount=curr,
        target_date=t_date,
        status=status
    )
    db.session.add(new_goal)
    db.session.commit()

    flash(f"Financial goal '{title}' added successfully!", "success")
    return redirect(url_for('goals.index'))


@goals_bp.route('/update-progress/<int:goal_id>', methods=['POST'])
@login_required
def update_progress(goal_id):
    goal = Goal.query.filter_by(id=goal_id, user_id=current_user.id).first_or_404()
    add_amount_raw = request.form.get('add_amount', '').strip()
    new_status = request.form.get('status', '').strip()
    if new_status and new_status != goal.status:
        goal.status = new_status

    if add_amount_raw:
        try:
            add_amt = float(add_amount_raw)
            goal.current_amount = max(0.0, goal.current_amount + add_amt)
            if goal.current_amount >= goal.target_amount:
                goal.status = 'Completed'
            elif goal.status == 'Completed':
                goal.status = 'In Progress'
        except ValueError:
            flash("Invalid deposit amount.", "danger")
            return redirect(url_for('goals.index'))

    db.session.commit()
    flash(f"Goal '{goal.title}' progress updated!", "success")
    return redirect(url_for('goals.index'))


@goals_bp.route('/delete/<int:goal_id>', methods=['POST'])
@login_required
def delete(goal_id):
    goal = Goal.query.filter_by(id=goal_id, user_id=current_user.id).first_or_404()
    title = goal.title
    db.session.delete(goal)
    db.session.commit()
    flash(f"Goal '{title}' deleted.", "info")
    return redirect(url_for('goals.index'))
