from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from database.database import get_summary_periods, get_summary_data
from datetime import datetime
from collections import defaultdict

# States
CHOOSE_PERIOD, CHOOSE_OPTION = [0, 1]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_markup = ReplyKeyboardMarkup(
        [["Yearly"], ["Monthly"], ["Weekly"]],
        one_time_keyboard=True,
        resize_keyboard=True
    )
    await update.message.reply_text("Please choose a summary period:", reply_markup=reply_markup)
    return CHOOSE_PERIOD

async def choose_period(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    context.user_data["period"] = update.message.text.lower()

    available = get_summary_periods(chat_id, context.user_data["period"])

    if not available:
        await update.message.reply_text("No data available for this period.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    # If only one option, send summary directly
    if len(available) == 1:
        context.user_data["option"] = available[0]
        return await send_summary(update, context)

    # Let user pick from available options
    markup = ReplyKeyboardMarkup(
        [[str(opt)] for opt in available],
        one_time_keyboard=True,
        resize_keyboard=True
    )
    await update.message.reply_text(f"Choose a {context.user_data['period']} option:", reply_markup=markup)
    return CHOOSE_OPTION

async def choose_option(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["option"] = update.message.text
    return await send_summary(update, context)

async def send_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    period = context.user_data["period"]
    option = context.user_data["option"]

    summary = get_summary_data(chat_id, period, option)
    print(f"Summary data: {summary}")
    if not summary:
        await update.message.reply_text("No transactions found.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    # Use defaultdict for efficient aggregation
    totals = defaultdict(float)
    for item in summary:
        if item.transaction_type == "income":
            totals["income"] += item.amount
        elif item.transaction_type == "expense":
            totals["expense"] += item.amount
    total_income = totals["income"]
    total_expense = totals["expense"]
    balance = total_income - total_expense
    days_count = len({transaction.timestamp.date() for transaction in summary}) or 1

    avg_income = total_income / days_count
    avg_expense = total_expense / days_count

    text = (
        f"📊 Summary ({period.title()} - {option}):\n\n"
        f"Income: RM {total_income:.2f}\n" # Ensure totals are not None before formatting

        f"Expense: RM {total_expense:.2f}\n"
        f"Balance: RM {balance:.2f}\n\n"
        f"Daily Avg Income: RM {avg_income:.2f}\n"
        f"Daily Avg Expense: RM {avg_expense:.2f}"
    )

    await update.message.reply_text(text, reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Summary cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END
