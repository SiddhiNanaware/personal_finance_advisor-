import pytest
from datetime import date, datetime
from app import create_app
from app.models import db, User, Income, Expense, Budget, Goal, ChatMessage
from config import TestConfig
from app.services.analytics_service import (
    get_monthly_summary,
    get_category_expenses,
    get_income_sources,
    get_budget_utilization,
    generate_suggested_budget,
    get_financial_health_score
)
from app.services.ai_service import generate_ai_financial_recommendations, generate_chat_response

@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def test_user(app):
    with app.app_context():
        user = User(
            full_name='Test User',
            email='test@example.com',
            monthly_income=50000.0,
            monthly_savings_target=10000.0,
            preferred_currency='INR',
            financial_goal='Buy a Laptop'
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        return user

def login(client, email='test@example.com', password='password123'):
    return client.post('/login', data={
        'email': email,
        'password': password
    }, follow_redirects=True)

# 1. User Authentication Tests
def test_registration_success(client, app):
    response = client.post('/register', data={
        'full_name': 'Alice Smith',
        'email': 'alice@example.com',
        'password': 'secret123',
        'confirm_password': 'secret123',
        'monthly_income': '45000',
        'preferred_currency': 'INR'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Account created successfully" in response.data

    with app.app_context():
        u = User.query.filter_by(email='alice@example.com').first()
        assert u is not None
        assert u.check_password('secret123')
        assert not u.check_password('wrongpassword')
        assert u.password_hash != 'secret123'  # Werkzeug salted hashing

def test_registration_validation(client):
    # Passwords do not match
    response = client.post('/register', data={
        'full_name': 'Bob',
        'email': 'bob@example.com',
        'password': 'password1',
        'confirm_password': 'different_pass',
        'monthly_income': '0'
    }, follow_redirects=True)
    assert b"Passwords do not match" in response.data

    # Password too short (<6 chars)
    response = client.post('/register', data={
        'full_name': 'Bob',
        'email': 'bob@example.com',
        'password': '123',
        'confirm_password': '123'
    }, follow_redirects=True)
    assert b"at least 6 characters" in response.data

def test_login_and_logout(client, test_user):
    # Invalid password
    resp = login(client, 'test@example.com', 'wrongpassword')
    assert b"Invalid email or password" in resp.data

    # Valid login
    resp = login(client, 'test@example.com', 'password123')
    assert b"Welcome back, Test User" in resp.data

    # Logout
    resp = client.get('/logout', follow_redirects=True)
    assert b"logged out successfully" in resp.data

def test_login_required_protection(client):
    resp = client.get('/dashboard', follow_redirects=False)
    assert resp.status_code == 302
    assert '/login' in resp.headers['Location']

# 2. Income Management Tests
def test_income_crud_and_calculation(client, test_user, app):
    login(client)

    today_str = date.today().strftime('%Y-%m-%d')
    month_str = date.today().strftime('%Y-%m')

    # Add Income 1
    resp = client.post('/income/add', data={
        'amount': '40000',
        'source': 'Salary',
        'date': today_str,
        'description': 'Main salary'
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"added successfully" in resp.data

    # Add Income 2
    client.post('/income/add', data={
        'amount': '15000',
        'source': 'Freelancing',
        'date': today_str,
        'description': 'Side gig'
    }, follow_redirects=True)

    with app.app_context():
        u = User.query.filter_by(email='test@example.com').first()
        summary = get_monthly_summary(u.id, month_str)
        assert summary['monthly_income'] == 55000.0
        assert summary['yearly_income'] == 55000.0

        sources = get_income_sources(u.id, month_str)
        assert len(sources) == 2
        sources_dict = {s['source']: s['amount'] for s in sources}
        assert sources_dict['Salary'] == 40000.0
        assert sources_dict['Freelancing'] == 15000.0

# 3. Expense Management & Filtering Tests
def test_expense_crud_and_filtering(client, test_user, app):
    login(client)
    today = date.today()
    today_str = today.strftime('%Y-%m-%d')
    month_str = today.strftime('%Y-%m')

    # Add Expense 1: Food
    client.post('/expenses/add', data={
        'amount': '3500',
        'category': 'Food',
        'date': today_str,
        'description': 'Organic groceries',
        'payment_method': 'UPI'
    }, follow_redirects=True)

    # Add Expense 2: Entertainment
    client.post('/expenses/add', data={
        'amount': '1500',
        'category': 'Entertainment',
        'date': today_str,
        'description': 'Cinema tickets',
        'payment_method': 'Credit Card'
    }, follow_redirects=True)

    with app.app_context():
        u = User.query.filter_by(email='test@example.com').first()
        categories = get_category_expenses(u.id, month_str)
        assert len(categories) == 2
        cat_dict = {c['category']: c['amount'] for c in categories}
        assert cat_dict['Food'] == 3500.0
        assert cat_dict['Entertainment'] == 1500.0

    # Test filtering by category
    resp = client.get('/expenses/?category=Food')
    assert b"Organic groceries" in resp.data
    assert b"Cinema tickets" not in resp.data

    # Test search by description
    resp = client.get('/expenses/?search=Cinema')
    assert b"Cinema tickets" in resp.data
    assert b"Organic groceries" not in resp.data

# 4. Budget Thresholds & Warnings Tests
def test_budget_utilization_thresholds(app, test_user):
    with app.app_context():
        u = User.query.filter_by(email='test@example.com').first()
        today = date.today()
        month_str = today.strftime('%Y-%m')

        # 1. Normal: Under 70% (spent 3000 out of 5000 -> 60%)
        db.session.add(Budget(user_id=u.id, month=month_str, category='Education', amount_limit=5000.0))
        db.session.add(Expense(user_id=u.id, amount=3000.0, category='Education', date=today))

        # 2. Warning: 70-90% (spent 800 out of 1000 -> 80%)
        db.session.add(Budget(user_id=u.id, month=month_str, category='Transport', amount_limit=1000.0))
        db.session.add(Expense(user_id=u.id, amount=800.0, category='Transport', date=today))

        # 3. Near Limit: 90-100% (spent 950 out of 1000 -> 95%)
        db.session.add(Budget(user_id=u.id, month=month_str, category='Utilities', amount_limit=1000.0))
        db.session.add(Expense(user_id=u.id, amount=950.0, category='Utilities', date=today))

        # 4. Overspending: > 100% (spent 6500 out of 5000 -> 130%)
        db.session.add(Budget(user_id=u.id, month=month_str, category='Food', amount_limit=5000.0))
        db.session.add(Expense(user_id=u.id, amount=6500.0, category='Food', date=today))

        db.session.commit()

        utilization = get_budget_utilization(u.id, month_str)
        items_by_cat = {i['category']: i for i in utilization['items']}

        assert items_by_cat['Education']['status'] == 'Normal'
        assert items_by_cat['Transport']['status'] == 'Warning'
        assert items_by_cat['Utilities']['status'] == 'Near Limit'
        assert items_by_cat['Food']['status'] == 'Overspending'
        assert items_by_cat['Food']['percentage'] == 130.0

# 5. Automatic Budget Generator (50/30/20) Tests
def test_auto_budget_generator(app, test_user):
    with app.app_context():
        u = User.query.filter_by(email='test@example.com').first()
        suggestion = generate_suggested_budget(u)

        assert suggestion['effective_income'] == 50000.0
        assert suggestion['savings_target'] == 10000.0  # matches user's target
        assert len(suggestion['categories']) > 0

        # Check that Needs and Wants categories are both present
        types = {c['type'] for c in suggestion['categories']}
        assert 'Needs (50%)' in types
        assert 'Wants (30%)' in types

# 6. AI Advisor Heuristic Fallback & Chat Tests
def test_ai_advisor_offline_heuristics_and_chat(app, test_user):
    with app.app_context():
        u = User.query.filter_by(email='test@example.com').first()
        today = date.today()

        # Add income and overspent expense
        db.session.add(Income(user_id=u.id, amount=60000.0, source='Salary', date=today))
        db.session.add(Budget(user_id=u.id, month=today.strftime('%Y-%m'), category='Shopping', amount_limit=4000.0))
        db.session.add(Expense(user_id=u.id, amount=5500.0, category='Shopping', date=today))
        db.session.commit()

        # Call AI recommendations (offline heuristic engine)
        ai_res = generate_ai_financial_recommendations(u)
        assert 'context' in ai_res
        assert len(ai_res['recommendations']) > 0
        
        # Check overspending detected
        titles = [r['title'] for r in ai_res['recommendations']]
        assert any('Overspending' in t for t in titles)

        # Call FinBot chat response
        reply_budget = generate_chat_response(u, "Am I overspending on my budget?")
        assert "over budget in: **Shopping**" in reply_budget

        reply_savings = generate_chat_response(u, "How can I improve my savings?")
        assert "savings rate" in reply_savings.lower()

# 7. Interactive Chat API & Clear Endpoint Tests
def test_advisor_chat_endpoint(client, test_user):
    login(client)

    # Post chat message
    resp = client.post('/advisor/chat', json={'message': 'How is my spending looking?'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'reply' in data
    assert len(data['reply']) > 0

    # Clear chat
    clear_resp = client.post('/advisor/clear-chat', follow_redirects=True)
    assert clear_resp.status_code == 200
    assert b"chat history cleared" in clear_resp.data

# 8. Goals CRUD & Progress Tests
def test_goals_lifecycle(client, test_user, app):
    login(client)

    # Add Goal
    resp = client.post('/goals/add', data={
        'title': 'Emergency Cushion',
        'target_amount': '50000',
        'current_amount': '10000',
        'target_date': '2026-12-31'
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Emergency Cushion" in resp.data

    with app.app_context():
        g = Goal.query.filter_by(title='Emergency Cushion').first()
        assert g is not None
        assert g.percentage == 20.0
        goal_id = g.id

    # Add funds to goal
    client.post(f'/goals/update-progress/{goal_id}', data={
        'add_amount': '40000',
        'status': 'In Progress'
    }, follow_redirects=True)

    with app.app_context():
        g = db.session.get(Goal, goal_id)
        assert g.current_amount == 50000.0
        assert g.status == 'Completed'
        assert g.percentage == 100.0

    # Delete goal
    del_resp = client.post(f'/goals/delete/{goal_id}', follow_redirects=True)
    assert del_resp.status_code == 200
    assert b"deleted" in del_resp.data

# 9. Profile Settings & Currency Switcher Tests
def test_profile_update(client, test_user, app):
    login(client)

    resp = client.post('/profile/', data={
        'full_name': 'Test User Updated',
        'email': 'test@example.com',
        'monthly_income': '75000',
        'monthly_savings_target': '20000',
        'financial_goal': 'Retirement Nest Egg',
        'preferred_currency': 'USD'
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Profile updated successfully" in resp.data

    with app.app_context():
        u = User.query.filter_by(email='test@example.com').first()
        assert u.full_name == 'Test User Updated'
        assert u.monthly_income == 75000.0
        assert u.preferred_currency == 'USD'
        assert u.financial_goal == 'Retirement Nest Egg'

# 10. Auto-Budget Apply Route & Dashboard Charts API Tests
def test_auto_budget_apply_and_charts_api(client, test_user, app):
    login(client)
    curr_month = date.today().strftime('%Y-%m')

    # Apply auto-generated 50/30/20 budget
    resp = client.post('/budget/apply-auto-budget', data={
        'month': curr_month
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Successfully applied AI-optimized 50/30/20 budget" in resp.data

    with app.app_context():
        u = User.query.filter_by(email='test@example.com').first()
        budgets = Budget.query.filter_by(user_id=u.id, month=curr_month).all()
        assert len(budgets) > 5

    # Test Charts JSON API
    chart_resp = client.get(f'/api/dashboard-charts?month={curr_month}')
    assert chart_resp.status_code == 200
    chart_data = chart_resp.get_json()
    assert 'categories' in chart_data
    assert 'trend' in chart_data
    assert 'payment_methods' in chart_data

# 11. Seed Demo Data & Reports Route Tests
def test_seed_demo_data_and_reports(client, test_user):
    login(client)

    # Seed demo data
    seed_resp = client.post('/seed-demo-data', follow_redirects=True)
    assert seed_resp.status_code == 200
    assert b"Sample data successfully loaded" in seed_resp.data

    # Verify reports view loads successfully
    rep_resp = client.get('/reports/')
    assert rep_resp.status_code == 200
    assert b"Monthly Financial Report" in rep_resp.data
    assert b"Budget Adherence &amp; Compliance Audit" in rep_resp.data

