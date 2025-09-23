from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes

from utils.database import save_transaction
from utils.validators import is_valid_currency

import logging

# Enable logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# set higher logging level for httpx to avoid all GET and POST requests being logged

logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


# Set the default categories for income and expense

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

# Conversation states
TYPE, AMOUNT, DESCRIPTION, CATEGORY = range(4)

# Start the transaction conversation
async def start_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_keyboard = [["Income", "Expense"]]
    
    await update.message.reply_text(
        "What would you like to do?",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, 
            resize_keyboard=True, 
            one_time_keyboard=True, 
            input_field_placeholder="Add 'Income' or 'Expense'"
        ),
    )
    
    return TYPE
    
    
async def type_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Take the state and ask for amount of transaction"""
    user = update.message.from_user
    
    # Store transaction type in temporary dictionary
    context.user_data['transaction_type'] = update.message.text
    
    logger.info("Transaction type: %s, User: %s", context.user_data['transaction_type'], user.first_name)
    await update.message.reply_text(
        "I see! Please provide the amount of the transaction.",
        reply_markup=ReplyKeyboardRemove()
    )
    
    return AMOUNT

# async def amount_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     """Take the amount of transaction and ask for description"""
    

    