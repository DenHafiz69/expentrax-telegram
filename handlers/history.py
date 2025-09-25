from httpx import get
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
CHOICE, RECENT, WEEKLY, MONTHLY = range(4)

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
    
    return CHOICE


async def history_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the user's selection for history type"""
    user = update.message.from_user
    choice = update.message.text
    
    if choice == "Recent":
        return RECENT
    elif choice == "Weekly":
        return WEEKLY
    elif choice == "Monthly":
        return MONTHLY
    else:
        await update.message.reply_text("Invalid choice. Please select 'Recent', 'Weekly', or 'Monthly'.")
        return CHOICE
    
async def recent_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show recent transactions by the user"""
    user = update.message.from_user
    
    print("test")
    
    # Read the transactions from database
    transactions = get_recent_transactions(user.id)
    logger.info("Recent transactions: %s, User: %s", transactions, user.first_name)
    
    if not transactions:
        await update.message.reply_text("No recent transactions found.")
        return ConversationHandler.END
    
    message = "Here are your recent transactions:\n\n"
    for transaction in transactions:
        # Determine the prefix (color and type) based on transaction.type
        # Google Gemini help with this part
        # Learned about ternary operator (conditional expression)
        type_prefix = "🟩 Income" if transaction.type_of_transaction == "income" else "🟥 Expense" 

        message += (
            f"{transaction.date.strftime('%Y-%m-%d')} | "  # Date
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