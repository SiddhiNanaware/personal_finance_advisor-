# Personal Finance Advisor Bot 🪙🤖

An AI-powered full-stack personal finance management web application built with **Python, Flask, SQLAlchemy, Bootstrap 5, Chart.js**, and an intelligent AI advisory layer (supporting **Google Gemini** and **OpenAI**, with an offline **Heuristic Advisor Engine** fallback).

---

## 🌟 Key Features

1. **User Authentication & Security**
   - Secure registration, login, logout, and protected routes.
   - Salted password hashing with `werkzeug.security`.
   - Form validations for emails, duplicate checks, and password match.

2. **Interactive Financial Dashboard**
   - Live metrics: Monthly Income, Monthly Expenses, Net Savings, Savings Rate (%), Financial Health Score.
   - Interactive **Chart.js** visualizations:
     - Donut Chart: Category-wise Expense distribution.
     - Bar Chart: 6-Month Income vs. Expense cashflow trend.
   - Real-time Category Budget Utilization progress bars with dynamic warning badges.
   - Recent transaction ledger with income/expense indicators.
   - 1-Click **"Load Demo Data"** to instantly test all charts, budget meters, and AI advice with realistic sample transactions.

3. **Income Management**
   - Add, Edit, Delete, and browse income history.
   - Categorize by source (*Salary, Freelancing, Allowance, Scholarship, Business, Other*).
   - Automated calculations: Total monthly income, total yearly income, and income-by-source distribution.

4. **Expense Management**
   - Add, Edit, Delete, and view daily/weekly expenses.
   - Real-time search by description.
   - Multi-criteria filtering by category, payment method (*Cash, UPI, Debit Card, Credit Card, Bank Transfer, Other*), and billing month.
   - Cumulative filtered spending totals.

5. **Budget Management & Threshold Alerts**
   - Set monthly category spending caps.
   - Real-time calculation of Amount Used, Amount Remaining, and Percentage Used.
   - Visual status indicators & progress bar color coding:
     - **Normal** (< 70%): Green
     - **Warning** (70% – 90%): Blue / Cyan
     - **Near Limit** (90% – 100%): Orange / Amber
     - **Overspending** (> 100%): Red with pulse animation

6. **Automatic Budget Generator (50/30/20 Rule)**
   - Analyzes monthly income, past category expenditure, and user's monthly savings target.
   - Allocates:
     - **Needs (50%)**: Rent, Food, Utilities, Bills, Transport, Healthcare, Education.
     - **Wants (30%)**: Shopping, Entertainment, Travel, Personal, Other.
     - **Savings (20%)**: User savings target.
   - Preview suggested limits and apply with one click to the active month.

7. **Financial Goals & Milestones**
   - Create milestone targets (e.g. *Emergency Fund, Vacation, Car*).
   - Track progress %, remaining balance, and target completion dates.
   - Quick deposit modal to log saved funds toward goals.

8. **Monthly Financial Reports & Audit Statement**
   - Audited monthly financial statement.
   - Income sources and category spending distribution tables.
   - Budget compliance & variance audit table.
   - AI-generated Executive Summary and recommendations.
   - One-click **Print / Export PDF** layout (`@media print` optimized).

9. **AI Personal Finance Advisor ("FinBot")**
   - Dual cloud AI engine: Google Gemini API (`GEMINI_API_KEY`) or OpenAI API (`OPENAI_API_KEY`).
   - Built-in **Heuristic Rule-Based Engine**: Works 100% offline with zero external API keys!
   - Real-time conversational chatbot with contextual financial memory.
   - Overspending detection and custom spending leak audits.

10. **User Profile & Multi-Currency Support**
    - Preferred currency configuration (Default: **INR ₹**, plus **USD $**, **EUR €**, **GBP £**, **JPY ¥**, **CAD C$**, **AUD A$**).
    - Customizable monthly savings target, baseline income, and primary financial goals.

---

## 🛠️ Technology Stack

- **Backend**: Python 3.11, Flask 3.1, Flask-Login, Flask-SQLAlchemy 3.1, Werkzeug, Jinja2, python-dotenv
- **Database**: SQLite (default, stored in `instance/finance_advisor.db`), easily switchable to PostgreSQL via `DATABASE_URL`
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5.3, Bootstrap Icons 1.11, Chart.js 4.4
- **Testing**: Pytest 9.1

---

## 🚀 Getting Started

### 1. Prerequisites
Ensure Python 3.10+ is installed on your system.

### 2. Installation
Navigate to the project directory:
```bash
cd C:\Users\Siddhi\.gemini\antigravity\scratch\personal_finance_advisor
```

Install the dependencies:
```bash
pip install -r requirements.txt
```

### 3. Environment Setup
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Configuration variables in `.env`:
```ini
# Flask Secret Key
SECRET_KEY=dev-secret-key-finance-advisor-2026

# Database Configuration (SQLite default, PostgreSQL ready)
DATABASE_URL=sqlite:///finance_advisor.db

# AI Provider: 'auto', 'gemini', or 'openai'
AI_PROVIDER=auto

# Optional Cloud AI API Keys (Leave blank to use the built-in heuristic offline advisor)
GEMINI_API_KEY=
OPENAI_API_KEY=
```

### 4. Run the Application
Start the Flask development server:
```bash
python run.py
```

Open your browser and visit:
[http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## 🧪 Running the Test Suite

Execute the automated pytest suite (14 test cases covering authentication, CRUD, budget math, auto-budget generator, and AI advisor):
```bash
pytest -v tests/
```

---

## 📂 Project Directory Structure

```
personal_finance_advisor/
│
├── app/
│   ├── __init__.py            # Flask application factory, Jinja filters, blueprints
│   ├── models.py              # SQLAlchemy models (User, Income, Expense, Budget, Goal, ChatMessage)
│   ├── services/
│   │   ├── analytics_service.py # Budget utilization, 50/30/20 algorithm, health score
│   │   └── ai_service.py        # Gemini, OpenAI & offline heuristic advisor engine
│   ├── routes/
│   │   ├── auth.py            # Registration, login, logout, password hashing
│   │   ├── dashboard.py       # Metrics, Chart.js API, sample data seeder
│   │   ├── income.py          # Income management & source analysis
│   │   ├── expense.py         # Expense management, filters, and search
│   │   ├── budget.py          # Budget limits & auto-generator (50/30/20)
│   │   ├── goals.py           # Financial goals milestone tracking
│   │   ├── reports.py         # Audited monthly statements & printable reports
│   │   ├── advisor.py         # AI advisor recommendations & conversational FinBot
│   │   └── profile.py         # User profile, savings targets, currency switcher
│   ├── templates/             # Jinja2 HTML templates
│   │   ├── base.html
│   │   ├── auth/
│   │   ├── dashboard/
│   │   ├── income/
│   │   ├── expense/
│   │   ├── budget/
│   │   ├── goals/
│   │   ├── reports/
│   │   ├── advisor/
│   │   └── profile/
│   └── static/
│       ├── css/custom.css     # Responsive dashboard styling, alert badges, print styles
│       └── js/
│           ├── dashboard.js   # Chart.js integration
│           └── advisor.js     # Live conversational chat controller
│
├── tests/
│   ├── __init__.py
│   └── test_app.py            # Comprehensive unit and integration test suite
│
├── config.py                  # Environment and database configuration
├── run.py                     # Application launcher
├── requirements.txt           # Python package dependencies
├── .env.example               # Environment variables template
├── .env                       # Local active environment settings
└── README.md                  # Project documentation
```
