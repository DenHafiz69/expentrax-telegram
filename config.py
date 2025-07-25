import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required")

BOT_USERNAME = os.getenv('BOT_USERNAME', 'expentrax_bot')
# WEBHOOK_URL = os.getenv('WEBHOOK_URL')

# Database
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///expenses.db')

# Application Settings
DEFAULT_CURRENCY = os.getenv('DEFAULT_CURRENCY', 'RM')
DEFAULT_TIMEZONE = os.getenv('DEFAULT_TIMEZONE', 'Asia/Kuala_Lumpur')
MAX_TRANSACTION_AMOUNT = float(os.getenv('MAX_TRANSACTION_AMOUNT', '999999.99'))

# Categories
DEFAULT_EXPENSE_CATEGORIES = [
    'Rent', 'Food', 'Groceries', 'Health', 'Transportation', 
    'Personal', 'Pets', 'Utilities', 'Savings', 'Debt', 
    'Education', 'Syazni'
]

DEFAULT_INCOME_CATEGORIES = ['Savings', 'Paycheck', 'Bonus', 'Other']

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Environment
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
DEBUG_MODE = ENVIRONMENT == 'development'