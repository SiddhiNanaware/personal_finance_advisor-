import os
from flask import Flask
from flask_login import LoginManager, current_user
from config import Config
from app.models import db, User

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure instance directory exists for SQLite
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    # Custom Jinja filters & context processors
    @app.template_filter('currency')
    def currency_filter(amount, currency_code=None):
        if amount is None:
            amount = 0.0
        try:
            val = float(amount)
        except (ValueError, TypeError):
            val = 0.0

        if not currency_code:
            if current_user and current_user.is_authenticated and current_user.preferred_currency:
                currency_code = current_user.preferred_currency
            else:
                currency_code = 'INR'

        symbols = app.config.get('CURRENCY_SYMBOLS', {})
        sym = symbols.get(currency_code, currency_code + ' ')
        return f"{sym} {val:,.2f}"

    @app.context_processor
    def inject_globals():
        symbols = app.config.get('CURRENCY_SYMBOLS', {})
        user_curr = 'INR'
        if current_user and current_user.is_authenticated and current_user.preferred_currency:
            user_curr = current_user.preferred_currency
        return {
            'user_currency_symbol': symbols.get(user_curr, '₹'),
            'user_currency_code': user_curr,
            'currency_symbols': symbols
        }

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.income import income_bp
    from app.routes.expense import expense_bp
    from app.routes.budget import budget_bp
    from app.routes.goals import goals_bp
    from app.routes.reports import reports_bp
    from app.routes.advisor import advisor_bp
    from app.routes.profile import profile_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(income_bp)
    app.register_blueprint(expense_bp)
    app.register_blueprint(budget_bp)
    app.register_blueprint(goals_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(advisor_bp)
    app.register_blueprint(profile_bp)

    # Create tables automatically
    with app.app_context():
        db.create_all()

    return app
