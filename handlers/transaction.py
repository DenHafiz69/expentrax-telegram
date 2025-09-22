from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove

from utils.database import save_transaction
from utils.validators import is_valid_currency

EXPENSE_CATEGORIES = [
    'Food',
    'Groceries',
    'Utilities',
    'Health/Medical',
    'Transport',
    'Savings',
    'Debt',
    'Personal',
    'Other'
]

INCOME_CATEGORIES = [
    'Paycheck',
    'Savings',
    'Investment',
    'Other'
]

