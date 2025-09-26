from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

from utils.database import save_transaction
from utils.validators import is_valid_currency

import logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# set higher logging level for httpx to avoid all GET and POST requests being logged

logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


# Set the default categories for income and expense

EXPENSE_CATEGORIES = [
    ['Food', 'Groceries', 'Utilities'],
    ['Health/Medical', 'Transport', 'Savings'],
    ['Debt', 'Personal', 'Other']
]

INCOME_CATEGORIES = [
    ['Paycheck', 'Savings', 'Freelance'],
    ['Investment', 'Other']
]

# Conversation states
TYPE, AMOUNT, DESCRIPTION, CATEGORY = range(4)

# Start the transaction conversation
async def start_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_keyboard = [["Income", "Expense"]]
    
    await update.message.reply_text(
        "What kind of transaction are we tracking today? 💰", # From Google Gemini
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
    context.user_data['type'] = update.message.text
    logger.info("Transaction type: %s, User: %s", context.user_data['type'], user.first_name)
    
    await update.message.reply_text(
        "Got it! How much was this transaction?\n" # From Google Gemini
        "_Please enter a number, e.g., `100` or `50.50`._",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode='Markdown',
    )
    
    return AMOUNT

async def amount_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Take the amount of transaction and ask for description"""
    user = update.message.from_user
    
    # Store transaction amount in temporary dictionary
    context.user_data['amount'] = update.message.text
    
    # Check if the currency is valid
    if not is_valid_currency(context.user_data['amount']):
        await update.message.reply_text(
            "Invalid amount. Please provide a valid currency."
        )
        return AMOUNT
    
    logger.info("Transaction amount: %s, User: %s", context.user_data['amount'], user.first_name)
    
    await update.message.reply_text(
        f"Perfect! Now, give me a short description for this {context.user_data['type'].lower()}.\n" # From Google Gemini
        "_E.g., 'Dinner with friends', 'Monthly internet bill'._",
        parse_mode='Markdown'
    )
    
    return DESCRIPTION

async def description_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Take the description of transaction and ask for category"""
    user = update.message.from_user
    
    # Store transaction description in temporary dictionary
    context.user_data['description'] = update.message.text        
    logger.info("Transaction description: %s, User: %s", context.user_data['description'], user.first_name)
    
    if context.user_data['type'] == "Income":
        reply_keyboard = INCOME_CATEGORIES
    else:
        reply_keyboard = EXPENSE_CATEGORIES
    
    await update.message.reply_text(
        f"Great! Which category best describes this {context.user_data['type'].lower()}? 👇",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, 
            resize_keyboard=True, 
            one_time_keyboard=True
        ),
        parse_mode='Markdown'
    )
    
    return CATEGORY

async def category_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Take the category of transaction and save the transaction"""
    user = update.message.from_user
    
    # Store transaction category in temporary dictionary
    context.user_data['category'] = update.message.text
    
    # Save transaction to database
    save_transaction(
        user_id=user.id,
        type_of_transaction=context.user_data['type'].lower(),
        amount=context.user_data['amount'],
        category=context.user_data['category'],
        description=context.user_data['description'],
        timestamp=update.message.date
    )
    
    logger.info("Transaction category: %s, User: %s", context.user_data['category'], user.first_name)
    await update.message.reply_text(
        f"✅ {context.user_data['type']} added:\n\n"
        f"Description: {context.user_data['description']}\n"
        f"Amount: RM {context.user_data['amount']:.2f}\n"
        f"Category: {context.user_data['category']}\n",
        reply_markup=ReplyKeyboardRemove()
    )
    
    logger.info("Transaction saved to database: %s, User: %s", context.user_data, user.first_name)
    
    # End the conversation
    return ConversationHandler.END

async def cancel_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)

    await update.message.reply_text(
        "Transaction cancelled.", reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END