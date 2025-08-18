from telegram import Update, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from datetime import datetime

from database.database import set_or_update_budget, get_budget_for_month, get_summary_data, get_user_settings
from utils.validators import is_valid_currency

# States for conversation
GET_BUDGET_AMOUNT = 0

async def set_budget_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation to set a budget for the current month."""
    current_month = datetime.now().strftime("%Y-%m")
    context.user_data['budget_period'] = current_month

    await update.message.reply_text(f"What is your budget for {current_month}?")
    return GET_BUDGET_AMOUNT

async def prompt_set_budget(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the callback from the monthly prompt to set a budget."""
    query = update.callback_query
    await query.answer()
    
    current_month = datetime.now().strftime("%Y-%m")
    context.user_data['budget_period'] = current_month

    await query.edit_message_text(text=f"Great! What is your budget for {current_month}?")
    return GET_BUDGET_AMOUNT

async def receive_budget_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives and saves the budget amount."""
    chat_id = update.effective_chat.id
    amount_text = update.message.text

    if not is_valid_currency(amount_text):
        await update.message.reply_text("❌ Invalid amount. Please enter a valid number (e.g., 1500.50).")
        return GET_BUDGET_AMOUNT

    amount = float(amount_text)
    period = context.user_data['budget_period']
    
    set_or_update_budget(chat_id, period, amount)
    
    settings = get_user_settings(chat_id)
    await update.message.reply_text(
        f"✅ Budget set successfully for {period} at {settings.currency} {amount:.2f}.",
        reply_markup=ReplyKeyboardRemove()
    )
    
    context.user_data.clear()
    return ConversationHandler.END

async def view_budget(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the current month's budget, spending, and remaining amount."""
    chat_id = update.effective_chat.id
    current_month = datetime.now().strftime("%Y-%m")
    
    budget = get_budget_for_month(chat_id, current_month)
    if not budget:
        await update.message.reply_text(
            f"You have not set a budget for {current_month}. "
            "Use /set_budget to create one."
        )
        return

    # Get expenses for the current month
    transactions = get_summary_data(chat_id, "monthly", current_month)
    total_expenses = sum(tx.amount for tx in transactions if tx.transaction_type == 'expense')
    
    remaining = budget.amount - total_expenses
    percentage_spent = (total_expenses / budget.amount) * 100 if budget.amount > 0 else 0
    
    # Create a simple progress bar
    progress_bar = ""
    filled_blocks = int(percentage_spent / 10)
    progress_bar += "▓" * filled_blocks
    progress_bar += "░" * (10 - filled_blocks)

    settings = get_user_settings(chat_id)
    currency = settings.currency

    message = (
        f"💰 *Budget Status for {current_month}*\n\n"
        f"Budget: {currency} {budget.amount:.2f}\n"
        f"Spent: {currency} {total_expenses:.2f}\n"
        f"Remaining: {currency} {remaining:.2f}\n\n"
        f"*{percentage_spent:.1f}% Spent*\n"
        f"`{progress_bar}`"
    )

    await update.message.reply_text(message, parse_mode="Markdown")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the budget setting operation."""
    await update.message.reply_text("Budget setup cancelled.", reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    return ConversationHandler.END