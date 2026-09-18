from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import db, ChatMessage
from app.services.analytics_service import get_current_month, get_financial_health_score
from app.services.ai_service import generate_ai_financial_recommendations, generate_chat_response

advisor_bp = Blueprint('advisor', __name__, url_prefix='/advisor')

@advisor_bp.route('/')
@login_required
def index():
    month = request.args.get('month', get_current_month())
    ai_data = generate_ai_financial_recommendations(current_user, month)
    health = get_financial_health_score(current_user, month)
    chat_history = ChatMessage.query.filter_by(user_id=current_user.id).order_by(ChatMessage.created_at.asc()).limit(50).all()

    return render_template(
        'advisor/index.html',
        context=ai_data['context'],
        recommendations=ai_data['recommendations'],
        ai_analysis=ai_data['ai_analysis'],
        health=health,
        chat_history=chat_history,
        month=month
    )


@advisor_bp.route('/chat', methods=['POST'])
@login_required
def chat():
    data = request.get_json(silent=True) or {}
    user_message = data.get('message', '').strip()

    if not user_message:
        return jsonify({'error': 'Message cannot be empty'}), 400

    # Save user message
    user_msg_record = ChatMessage(
        user_id=current_user.id,
        role='user',
        content=user_message
    )
    db.session.add(user_msg_record)

    # Generate response (Live AI or Heuristic Fallback)
    reply_text = generate_chat_response(current_user, user_message)

    # Save bot message
    bot_msg_record = ChatMessage(
        user_id=current_user.id,
        role='assistant',
        content=reply_text
    )
    db.session.add(bot_msg_record)
    db.session.commit()

    return jsonify({
        'reply': reply_text,
        'user_message': user_message
    })


@advisor_bp.route('/clear-chat', methods=['POST'])
@login_required
def clear_chat():
    ChatMessage.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    flash("Advisor chat history cleared.", "info")
    return redirect(url_for('advisor.index'))
