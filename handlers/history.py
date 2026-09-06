import asyncio
import logging
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from utils.database import (
    get_category_name_by_id,
    get_currency,
    get_period_total,
    get_recent_transactions,
    get_summary_periods,
)

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
    keyboard = [
        [
            InlineKeyboardButton("Recent ✅", callback_data="recent"),
            InlineKeyboardButton("Summary 📊", callback_data="summary"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    logger.info(
        "History conversation started, User: %s", update.message.from_user.first_name
    )

    await update.message.reply_text(
        "📋 Welcome to the transaction history! What would you like to do?",
        reply_markup=reply_markup,
    )

    return CHOICE


async def history_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the user's selection for history type"""
    query = update.callback_query
    await query.answer()
    choice = query.data

    logger.info("User choice: %s, User: %s", choice, query.from_user.first_name)

    if choice == "recent":
        return await recent_handler(update, context)

    elif choice == "summary":
        keyboard = [
            [
                InlineKeyboardButton("Weekly", callback_data="weekly"),
                InlineKeyboardButton("Monthly", callback_data="monthly"),
                InlineKeyboardButton("Yearly", callback_data="yearly"),
            ],
            [InlineKeyboardButton("Back", callback_data="start_history")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text="📅 Please specify a summary period:", reply_markup=reply_markup
        )

        return SUMMARY

    else:
        await query.edit_message_text(
            text="❓ Oops! Please select 'Recent' or 'Summary'.\n"
            "📝 Note: Weekly, Monthly, and Yearly options show summaries instead of individual transactions."
        )
        return CHOICE


async def recent_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show recent transactions by the user"""
    query = update.callback_query
    await query.answer()
    user = query.from_user
    user_id = update.effective_chat.id
    currency = await asyncio.to_thread(get_currency, update.effective_chat.id)

    # Read the transactions from database
    transactions = await asyncio.to_thread(get_recent_transactions, user_id)
    logger.info("Recent transactions: %s, User: %s", transactions, user.first_name)

    if not transactions:
        await query.edit_message_text(
            text="🔍 No recent transactions found. Try adding some transactions first!"
        )

        return ConversationHandler.END

    message = "📄 *Here are your recent transactions:*\n\n"
    for transaction in transactions:
        type_prefix = (
            "💰 Income" if transaction.type_of_transaction == "income" else "💸 Expense"
        )
        category_name = await asyncio.to_thread(
            get_category_name_by_id, transaction.category_id
        )

        message += (
            f"📅 {transaction.timestamp.strftime('%Y-%m-%d')} | "
            f"{type_prefix} | "
            f"💵 {currency} {transaction.amount:.2f} | "
            f"🏷️ *{category_name}* | "
            f"{transaction.description}\n"
        )

    await query.edit_message_text(text=message.strip(), parse_mode="Markdown")

    return ConversationHandler.END


async def summary_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show summary transactions by the user"""
    query = update.callback_query
    await query.answer()
    summary_choice = query.data

    logger.info(
        "Summary period: %s, User: %s", summary_choice, query.from_user.first_name
    )

    # Read the transactions from database
    user_id = update.effective_chat.id
    periods = await asyncio.to_thread(
        get_summary_periods, user_id, summary_choice.lower()
    )
    context.user_data["periods"] = periods

    row_size = 3

    keyboard = [
        [
            InlineKeyboardButton(period, callback_data=period)
            for period in periods[i : i + row_size]
        ]
        for i in range(0, len(periods), row_size)
    ]
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back_to_summary")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    if not periods:
        await query.edit_message_text(
            text=f"🔍 No {summary_choice} summary found. Try adding transactions first!"
        )

        return ConversationHandler.END

    elif summary_choice == "weekly":
        await query.edit_message_text(
            text="📅 Please choose the week you want to view:",
            reply_markup=reply_markup,
        )

        return WEEKLY

    elif summary_choice == "monthly":
        await query.edit_message_text(
            text="📅 Please choose the month you want to view:",
            reply_markup=reply_markup,
        )

        return MONTHLY

    else:
        await query.edit_message_text(
            text="📅 Please choose the year you want to view:",
            reply_markup=reply_markup,
        )

        return YEARLY


async def weekly_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    user_id = update.effective_chat.id

    user_choice = query.data.split(" ")

    year_choice, week_choice = user_choice[2], user_choice[1]

    week_total = await asyncio.to_thread(
        get_period_total,
        user_id,
        period_type="week",
        target_year=int(year_choice),
        target_week=int(week_choice),
    )

    logger.info("Weekly total: %s, User: %s", week_total, user.first_name)

    net_amount = week_total.total_income - week_total.total_expense
    emoji = "📈" if net_amount >= 0 else "📉"
    currency = await asyncio.to_thread(get_currency, update.effective_chat.id)

    await query.edit_message_text(
        text=f"📊 *Weekly Summary ({year_choice} Week {week_choice})*\n\n"
        f"💰 Total Income: *{currency} {week_total.total_income:.2f}*\n"
        f"💸 Total Expense: *{currency} {week_total.total_expense:.2f}*\n"
        f"💡 Net: *{currency} {net_amount:.2f}* {emoji}",
        parse_mode="Markdown",
    )

    return ConversationHandler.END


async def monthly_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    user_id = update.effective_chat.id

    user_choice = query.data.split(" ")

    month_choice, year_choice = user_choice[0], user_choice[1]

    month_total = await asyncio.to_thread(
        get_period_total,
        user_id,
        period_type="month",
        target_year=int(year_choice),
        target_month=datetime.strptime(month_choice, "%b").month,
    )

    logger.info("Monthly total: %s, User: %s", month_total, user.first_name)

    net_amount = month_total.total_income - month_total.total_expense
    emoji = "📈" if net_amount >= 0 else "📉"
    currency = await asyncio.to_thread(get_currency, update.effective_chat.id)

    await query.edit_message_text(
        text=f"📊 *Monthly Summary ({month_choice} {year_choice})*\n\n"
        f"💰 Total Income: *{currency} {month_total.total_income:.2f}*\n"
        f"💸 Total Expense: *{currency} {month_total.total_expense:.2f}*\n"
        f"💡 Net: *{currency} {net_amount:.2f}* {emoji}",
        parse_mode="Markdown",
    )

    return ConversationHandler.END


async def yearly_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    user_id = update.effective_chat.id

    year_choice = query.data

    year_total = await asyncio.to_thread(
        get_period_total, user_id, period_type="year", target_year=int(year_choice)
    )

    logger.info("Year total: %s, User: %s", year_total, user.first_name)

    net_amount = year_total.total_income - year_total.total_expense
    emoji = "📈" if net_amount >= 0 else "📉"
    currency = await asyncio.to_thread(get_currency, update.effective_chat.id)

    await query.edit_message_text(
        text=f"📊 *Yearly Summary ({year_choice})*\n\n"
        f"💰 Total Income: *{currency} {year_total.total_income:.2f}*\n"
        f"💸 Total Expense: *{currency} {year_total.total_expense:.2f}*\n"
        f"💡 Net: *{currency} {net_amount:.2f}* {emoji}",
        parse_mode="Markdown",
    )

    return ConversationHandler.END


async def back_history_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handles the back button in the history conversation."""
    query = update.callback_query
    await query.answer()

    if query.data == "start_history":
        return await start_history(update, context)
    elif query.data == "back_to_summary":
        keyboard = [
            [
                InlineKeyboardButton("Weekly 📅", callback_data="weekly"),
                InlineKeyboardButton("Monthly 📅", callback_data="monthly"),
                InlineKeyboardButton("Yearly 📅", callback_data="yearly"),
            ],
            [InlineKeyboardButton("⬅️ Back", callback_data="start_history")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text="📅 Please specify a summary period:", reply_markup=reply_markup
        )

        return SUMMARY


async def cancel_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)

    await update.message.reply_text("❌ History operation cancelled.")

    return ConversationHandler.END
