import os
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-finance-advisor-2026')
    
    # Database Configuration: SQLite default, PostgreSQL ready
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'finance_advisor.db')}"
    elif db_url.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = db_url.replace('postgres://', 'postgresql://', 1)
    else:
        SQLALCHEMY_DATABASE_URI = db_url
        
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # AI Configuration
    AI_PROVIDER = os.getenv('AI_PROVIDER', 'auto')
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '').strip()
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '').strip()

    # Currency configurations
    DEFAULT_CURRENCY = 'INR'
    CURRENCY_SYMBOLS = {
        'INR': '₹',
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'JPY': '¥',
        'CAD': 'C$',
        'AUD': 'A$'
    }

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
