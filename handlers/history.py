from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

from utils.database import get_recent_transactions

import logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# set higher logging level for httpx to avoid all GET and POST requests being logged

logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Conversation states
RECENT, WEEKLY, MONTHLY = range(3)

# Start the history conversation
async def start_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_keyboard = [["Recent", "Weekly", "Monthly"]]
    
    await update.message.reply_text(
        "What would you like to do?",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, 
            resize_keyboard=True, 
            one_time_keyboard=True, 
            input_field_placeholder="Add 'Recent', 'Weekly' or 'Monthly'"
        ),
    )
    
    if update.message.text == "Recent":
        return RECENT
    elif update.message.text == "Weekly":
        return WEEKLY
    elif update.message.text == "Monthly":
        return MONTHLY
    else:
        # 
        return ConversationHandler.END
    
async def recent_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show recent transactions by the user"""
    user = update.message.from_user
    
    # Read the transactions from database
    get_recent_transactions(user.id)
    
    # Send recent transactions to the user
    

async def weekly_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show weekly transactions by the user"""
    user = update.message.from_user
    
    reply_keyboard = [["This week", "Last week", "Last two weeks"]]
    
    await update.message.reply_text(
        "Which week would you like to see?",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, 
            resize_keyboard=True, 
            one_time_keyboard=True
        ),
    )
    
    # Read the transactions needed from the database
    
    
async def monthly_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show monthly transactions by the user"""
    user = update.message.from_user
    
    # reply_keyboard = show last three months but in spelling eg. September, August, July
    
async def cancel_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)

    await update.message.reply_text(
        "Transaction cancelled.", reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END