from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler

from utils.database import get_category_id, save_transaction, get_categories_name, get_category_type
from utils.misc import is_valid_currency, list_chunker

import logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# set higher logging level for httpx to avoid all GET and POST requests being logged

logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


# Set the categories for income and expense

EXPENSE_CATEGORIES = list_chunker(
    categories=get_categories_name("expense"), chunk_size=3)
INCOME_CATEGORIES = list_chunker(
    categories=get_categories_name("income"), chunk_size=3)

# Conversation states
TYPE, AMOUNT, DESCRIPTION, CATEGORY = range(4)

# Start the transaction conversation


async def start_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation and ask for transaction type."""
    keyboard = [
        [
            InlineKeyboardButton("Expense", callback_data="Expense"),
            InlineKeyboardButton("Income", callback_data="Income"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "What kind of transaction are we tracking today? 💰", reply_markup=reply_markup
    )
    return TYPE


async def type_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Take the state and ask for amount of transaction"""
    query = update.callback_query
    await query.answer()

    # Store transaction type in temporary dictionary
    context.user_data['type'] = query.data
    logger.info("Transaction type: %s, User: %s",
                context.user_data['type'], query.from_user.first_name)

    await query.edit_message_text(
        text="Got it! How much was this transaction?\n"
        "_Please enter a number, e.g., `100` or `50.50`._",
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

    logger.info("Transaction amount: %s, User: %s",
                context.user_data['amount'], user.first_name)

    await update.message.reply_text(
        f"Perfect! Now, give me a short description for this {context.user_data['type'].lower()}.\n"
        "_E.g., 'Dinner with friends', 'Monthly internet bill'._",
        parse_mode='Markdown'
    )

    return DESCRIPTION


async def description_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Take the description of transaction and ask for category"""
    user = update.message.from_user

    # Store transaction description in temporary dictionary
    context.user_data['description'] = update.message.text
    logger.info("Transaction description: %s, User: %s",
                context.user_data['description'], user.first_name)

    if context.user_data['type'] == "Income":
        categories = INCOME_CATEGORIES
    else:
        categories = EXPENSE_CATEGORIES

    keyboard = [
        [InlineKeyboardButton(category, callback_data=category)
         for category in row]
        for row in categories
    ]
    keyboard.append([InlineKeyboardButton(
        "Back", callback_data="back_to_description")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"Great! Which category best describes this {context.user_data['type'].lower()}? 👇",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

    return CATEGORY


async def category_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Take the category of transaction and save the transaction"""
    query = update.callback_query
    await query.answer()
    user = query.from_user

    # Store transaction category in temporary dictionary
    category_name = query.data
    category_id = get_category_id(category_name)
    category_type = get_category_type(category_id)

    # Save transaction to database
    save_transaction(
        user_id=update.effective_chat.id,
        type_of_transaction=context.user_data['type'].lower(),
        amount=float(context.user_data['amount']),
        description=context.user_data['description'],
        timestamp=update.callback_query.message.date,
        category_id=category_id,
        category_type=category_type
    )

    logger.info("Transaction category: %s, User: %s",
                category_name, user.first_name)
    await query.edit_message_text(
        text=f"✅ {context.user_data['type']} added:\n\n"
        f"Description: {context.user_data['description']}\n"
        f"Amount: RM {float(context.user_data['amount']):.2f}\n"
        f"Category: {category_name}\n"
    )

    logger.info("Transaction saved to database: %s, User: %s",
                context.user_data, user.first_name)

    # End the conversation
    return ConversationHandler.END


async def back_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Go back to the previous state."""
    query = update.callback_query
    await query.answer()

    # Get the previous state from the callback data
    previous_state = query.data.split('_')[-1]

    if previous_state == "description":
        await query.edit_message_text(
            text=f"Perfect! Now, give me a short description for this {context.user_data['type'].lower()}.\n"
            "_E.g., 'Dinner with friends', 'Monthly internet bill'._",
            parse_mode='Markdown'
        )
        return DESCRIPTION

    return ConversationHandler.END


async def cancel_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)

    await update.message.reply_text(
        "Transaction cancelled."
    )

    return ConversationHandler.END
