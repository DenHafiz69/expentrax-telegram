import logging
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database.database import get_all_user_chat_ids, get_budget_for_month

async def check_monthly_budget_prompt(context: ContextTypes.DEFAULT_TYPE):
    """
    A daily job that checks if it's the start of the month and prompts users
    who haven't set a budget yet.
    """
    today = datetime.now()
    # Run this check for the first 3 days of the month
    if today.day > 3:
        return

    current_month_period = today.strftime("%Y-%m")
    chat_ids = get_all_user_chat_ids()
    logging.info(f"Running budget check for {len(chat_ids)} users for period {current_month_period}.")

    for chat_id in chat_ids:
        budget = get_budget_for_month(chat_id, current_month_period)
        if not budget:
            logging.info(f"Prompting user {chat_id} to set a budget.")
            keyboard = [[InlineKeyboardButton("Set Budget Now", callback_data="prompt_set_budget")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            try:
                await context.bot.send_message(chat_id, "👋 It's a new month! Time to set your budget.", reply_markup=reply_markup)
            except Exception as e:
                logging.error(f"Failed to send budget prompt to {chat_id}: {e}")
