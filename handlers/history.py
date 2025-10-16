from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

from utils.database import get_period_total, get_recent_transactions, get_summary_periods, read_user, get_category_name_by_id
from datetime import datetime

import logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# set higher logging level for httpx to avoid all GET and POST requests being logged

logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Conversation states
CHOICE, SUMMARY, WEEKLY, MONTHLY, YEARLY = range(5)

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
        reply_keyboard = [["Weekly", "Monthly", "Yearly"]]
        
        await update.message.reply_text(
            "Please specify a summary period either 'Weekly', 'Monthly', or 'Yearly'.",
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard,
                resize_keyboard=True,
                one_time_keyboard=True,
                input_field_placeholder="Add 'Weekly', 'Monthly', or 'Yearly'"
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
    user_id = update.effective_chat.id
    
    # Read the transactions from database
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
            f"*{get_category_name_by_id(transaction.category_id)}* | "                 # Category (bold for Markdown)
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
    user_id = update.effective_chat.id
    periods = get_summary_periods(user_id, summary_choice.lower())
    context.user_data['periods'] = periods
    
    # Specifying the keyboard markup for weekly, monthly, and yearly
    row_size = 3
    
    reply_keyboard = [
        periods[i:i + row_size]
        for i in range(0, len(periods), row_size)
    ]
    
    if not periods:
        await update.message.reply_text(
            f"No {summary_choice} summary found.",
            reply_markup=ReplyKeyboardRemove()
        )
        
        return ConversationHandler.END

    elif summary_choice == "Weekly":
        
        await update.message.reply_text(
            "Please choose the week that you want:",
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard,
                one_time_keyboard=True,
                resize_keyboard=True,
                input_field_placeholder="Choose a week for the summary."
            )
        )
        
        return WEEKLY
    
    elif summary_choice == "Monthly":
        
        await update.message.reply_text(
            "Please choose the month that you want:",
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard,
                one_time_keyboard=True,
                resize_keyboard=True,
                input_field_placeholder="Choose a month for the summary."
            )
        )
        
        return MONTHLY
    
    else:
        
        await update.message.reply_text(
            "Please choose the year that you want:",
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard,
                one_time_keyboard=True,
                resize_keyboard=True,
                input_field_placeholder="Choose a year for the summary."
            )
        )
        
        return YEARLY

async def weekly_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = update.effective_chat.id
    
    user_choice = update.message.text.split(' ')
    
    year_choice, week_choice = user_choice[2], user_choice[1]
    
    week_total = get_period_total(
        user_id,
        period_type='week',
        target_year=int(year_choice),
        target_week=int(week_choice)
    )
    
    logger.info("Weekly total: %s, User: %s", week_total, user.first_name)
    
    await update.message.reply_text(
        f"Total income: RM {week_total.total_income:.2f}\n"
        f"Total expense: RM {week_total.total_expense:.2f}",
        reply_markup=ReplyKeyboardRemove(),
    )
    
    return ConversationHandler.END


async def monthly_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = update.effective_chat.id
    
    user_choice = update.message.text.split(' ')
    
    month_choice, year_choice = user_choice[0], user_choice[1]
    
    month_total = get_period_total(
        user_id,
        period_type='month',
        target_year=int(year_choice),
        target_month=datetime.strptime(month_choice, "%b").month
    )
    
    logger.info("Monthly total: %s, User: %s", month_total, user.first_name)
    
    await update.message.reply_text(
        f"Total income: RM {month_total.total_income:.2f}\n"
        f"Total expense: RM {month_total.total_expense:.2f}",
        reply_markup=ReplyKeyboardRemove()
    )
    
    return ConversationHandler.END
    

async def yearly_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = update.effective_chat.id
    
    year_choice = update.message.text
    
    year_total = get_period_total(
        user_id,
        period_type='year',
        target_year=int(year_choice)
    )
    
    logger.info("Year total: %s, User: %s", year_total, user.first_name)
    
    await update.message.reply_text(
        f"Total income: RM {year_total.total_income:.2f}\n"
        f"Total expense: RM {year_total.total_expense:.2f}",
        reply_markup=ReplyKeyboardRemove()
    )
    
    return ConversationHandler.END

   
async def cancel_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)

    await update.message.reply_text(
        "Transaction cancelled.",
        reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END
