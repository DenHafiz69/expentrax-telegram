from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

from datetime import datetime, timedelta

from handlers import start
from utils.database import get_recent_transactions, get_summary_periods, read_user

import logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# set higher logging level for httpx to avoid all GET and POST requests being logged

logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Conversation states
CHOICE, SUMMARY = range(2)

# Start the history conversation
async def start_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_keyboard = [["Recent", "Summary"]]
    
    logger.info("History conversation started, User: %s", update.message.from_user.first_name)
    
    await update.message.reply_text(
        "What would you like to do?",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, 
            resize_keyboard=True, 
            one_time_keyboard=True, 
            input_field_placeholder="Add 'Recent', 'Weekly' or 'Monthly'"
        ),
    )
    
    return CHOICE


async def history_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the user's selection for history type"""
    user = update.message.from_user
    choice = update.message.text
    
    logger.info("User choice: %s, User: %s", choice, user.first_name)
    
    if choice == "Recent":
        return await recent_handler(update, context)
    
    elif choice == "Summary":
        reply_keyboard = [["Weekly", "Monthly"]]
        
        await update.message.reply_text(
            "Please specify a summary period either 'Weekly' or 'Monthly'.",
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard,
                resize_keyboard=True,
                one_time_keyboard=True,
                input_field_placeholder="Add 'Weekly' or 'Monthly'"
            )
        )
        
        return SUMMARY
    
    else:
        await update.message.reply_text(
            "Invalid choice. Please select 'Recent' or 'Summary'.\n"
            "Weekly and Monthly would be summaries instead of individual transaction."
            )
        return CHOICE
      
async def recent_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show recent transactions by the user"""
    user = update.message.from_user
    
    # Read the transactions from database
    user_id = read_user(update.effective_chat.id).id
    transactions = get_recent_transactions(user_id)
    logger.info("Recent transactions: %s, User: %s", transactions, user.first_name)
    
    if not transactions:
        await update.message.reply_text(
            "No recent transactions found.",
            reply_markup=ReplyKeyboardRemove()
            )
        
        return ConversationHandler.END
    
    message = "Here are your recent transactions:\n\n"
    for transaction in transactions:
        # Determine the prefix (color and type) based on transaction.type
        # Google Gemini help with this part
        # Learned about ternary operator (conditional expression)
        type_prefix = "🟩 Income" if transaction.type_of_transaction == "income" else "🟥 Expense" 

        message += (
            f"{transaction.timestamp.strftime('%Y-%m-%d')} | "  # Date
            f"{type_prefix} | "                            # Income/Expense with emoji
            f"RM {transaction.amount:.2f} | "              # Amount (formatted)
            f"*{transaction.category}* | "                 # Category (bold for Markdown)
            f"{transaction.description}\n"                 # Description
        )
        
    await update.message.reply_text(
        message.strip(), 
        reply_markup=ReplyKeyboardRemove(), 
        parse_mode='Markdown')
    
    return ConversationHandler.END

async def summary_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show monthly transactions by the user"""
    user = update.message.from_user
    summary_choice = update.message.text
    
    logger.info("Summary period: %s, User: %s", summary_choice, user.first_name)
    
    # Read the transactions from database
    user_id = read_user(update.effective_chat.id).id
    periods = get_summary_periods(user_id, summary_choice.lower())
    
    if not periods:
        await update.message.reply_text(
            f"No {summary_choice} summary found.",
            reply_markup=ReplyKeyboardRemove()
        )
        
        return ConversationHandler.END

    elif summary_choice == "Weekly":
        weekly_handler(update, context, periods, user)
    elif summary_choice == "Monthly":
        monthly_handler(update, context, periods, user)
    else:
        yearly_handler(update, context, periods, user)
        
    return ConversationHandler.END

def weekly_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, periods, user):
    pass

def monthly_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, periods, user):
    pass

def yearly_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, periods, user):
    pass
   
async def cancel_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)

    await update.message.reply_text(
        "Transaction cancelled.",
        reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END