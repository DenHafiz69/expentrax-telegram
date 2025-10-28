from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from datetime import datetime

from utils.database import save_recurring_transaction, get_category_id, get_categories_name, get_category_type
from utils.misc import is_valid_currency, list_chunker

import logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Conversation states
TYPE, AMOUNT, DESCRIPTION, CATEGORY, FREQUENCY, START_DATE, END_DATE = range(7)

# Categories
EXPENSE_CATEGORIES = list_chunker(
    categories=get_categories_name("expense"), chunk_size=3)
INCOME_CATEGORIES = list_chunker(
    categories=get_categories_name("income"), chunk_size=3)


async def start_recurring_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation and ask for transaction type."""
    keyboard = [
        [
            InlineKeyboardButton("💸 Expense", callback_data="Expense"),
            InlineKeyboardButton("💰 Income", callback_data="Income"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Let's set up a recurring transaction. Is it an income or an expense? 💰", reply_markup=reply_markup
    )
    return TYPE


async def type_handler_recurring(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Take the state and ask for amount of transaction"""
    query = update.callback_query
    await query.answer()
    context.user_data['type'] = query.data
    logger.info("Recurring transaction type: %s, User: %s",
                context.user_data['type'], query.from_user.first_name)
    await query.edit_message_text(
        text="Got it! How much is this recurring transaction?\n_Please enter a number, e.g., `100` or `50.50`._",
        parse_mode='Markdown',
    )
    return AMOUNT


async def amount_handler_recurring(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Take the amount of transaction and ask for description"""
    user = update.message.from_user
    context.user_data['amount'] = update.message.text
    if not is_valid_currency(context.user_data['amount']):
        await update.message.reply_text("❌ Invalid amount. Please provide a valid currency.")
        return AMOUNT
    logger.info("Recurring transaction amount: %s, User: %s",
                context.user_data['amount'], user.first_name)
    await update.message.reply_text(
        f"Perfect! Now, give me a short description for this recurring {context.user_data['type'].lower()}.\n_E.g., 'Netflix Subscription', 'Monthly Salary'._",
        parse_mode='Markdown'
    )
    return DESCRIPTION


async def description_handler_recurring(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Take the description of transaction and ask for category"""
    user = update.message.from_user
    context.user_data['description'] = update.message.text
    logger.info("Recurring transaction description: %s, User: %s",
                context.user_data['description'], user.first_name)
    categories = INCOME_CATEGORIES if context.user_data['type'] == "Income" else EXPENSE_CATEGORIES
    keyboard = [[InlineKeyboardButton(
        category, callback_data=category) for category in row] for row in categories]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"Great! Which category best describes this recurring {context.user_data['type'].lower()}? 👇",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return CATEGORY


async def category_handler_recurring(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Take the category of transaction and ask for frequency"""
    query = update.callback_query
    await query.answer()
    context.user_data['category_name'] = query.data
    logger.info("Recurring transaction category: %s, User: %s",
                context.user_data['category_name'], query.from_user.first_name)
    keyboard = [
        [
            InlineKeyboardButton("Daily", callback_data="daily"),
            InlineKeyboardButton("Weekly", callback_data="weekly"),
            InlineKeyboardButton("Monthly", callback_data="monthly"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text="How often should this transaction repeat?", reply_markup=reply_markup
    )
    return FREQUENCY


async def frequency_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Take the frequency and ask for the start date."""
    query = update.callback_query
    await query.answer()
    context.user_data['frequency'] = query.data
    logger.info("Recurring transaction frequency: %s, User: %s",
                context.user_data['frequency'], query.from_user.first_name)
    await query.edit_message_text(
        text="When should this recurring transaction start?\n_Please use YYYY-MM-DD format._",
        parse_mode='Markdown'
    )
    return START_DATE


async def start_date_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Take the start date and ask for the end date."""
    user = update.message.from_user
    try:
        context.user_data['start_date'] = datetime.strptime(
            update.message.text, '%Y-%m-%d')
    except ValueError:
        await update.message.reply_text("❌ Invalid date format. Please use YYYY-MM-DD.")
        return START_DATE
    logger.info("Recurring transaction start date: %s, User: %s",
                context.user_data['start_date'], user.first_name)
    await update.message.reply_text(
        text="Got it. When should this transaction end?\n_Please use YYYY-MM-DD format, or type 'None' if it should not expire._",
        parse_mode='Markdown'
    )
    return END_DATE


async def end_date_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Take the end date and save the recurring transaction."""
    user = update.message.from_user
    end_date_text = update.message.text
    end_date = None
    if end_date_text.lower() != 'none':
        try:
            end_date = datetime.strptime(end_date_text, '%Y-%m-%d')
        except ValueError:
            await update.message.reply_text("❌ Invalid date format. Please use YYYY-MM-DD or 'None'.")
            return END_DATE

    context.user_data['end_date'] = end_date
    logger.info("Recurring transaction end date: %s, User: %s",
                context.user_data['end_date'], user.first_name)

    category_name = context.user_data['category_name']
    category_id = get_category_id(category_name)
    category_type = get_category_type(category_id)

    save_recurring_transaction(
        user_id=update.effective_chat.id,
        type_of_transaction=context.user_data['type'].lower(),
        amount=float(context.user_data['amount']),
        description=context.user_data['description'],
        category_id=category_id,
        category_type=category_type,
        frequency=context.user_data['frequency'],
        start_date=context.user_data['start_date'],
        end_date=context.user_data.get('end_date')
    )

    await update.message.reply_text(
        f"✅ Recurring {context.user_data['type']} has been set up successfully!\n\n"
        f"Description: {context.user_data['description']}\n"
        f"Amount: RM {float(context.user_data['amount']):.2f}\n"
        f"Category: {category_name}\n"
        f"Frequency: {context.user_data['frequency'].capitalize()}\n"
        f"Start Date: {context.user_data['start_date'].strftime('%Y-%m-%d')}\n"
        f"End Date: {context.user_data['end_date'].strftime('%Y-%m-%d') if context.user_data['end_date'] else 'None'}"
    )
    return ConversationHandler.END


async def cancel_recurring_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user
    logger.info("User %s canceled the recurring transaction setup.",
                user.first_name)
    await update.message.reply_text("❌ Recurring transaction setup cancelled.")
    return ConversationHandler.END
