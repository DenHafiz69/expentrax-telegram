from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler

from utils.database import (
    get_categories_name,
    get_category_id,
    get_category_type,
    get_currency,
    set_budget,
    get_budget_by_month,
    get_spend_by_month,
    get_category_name_by_id,
)
from utils.misc import list_chunker, is_valid_currency

import logging
from datetime import datetime, timedelta

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Conversation states
CHOICE, MONTH_SELECTION, CATEGORY_SELECTION, AMOUNT_INPUT, CHANGE_CATEGORY, CHANGE_AMOUNT = range(
    6)

# Keyboards
EXPENSE_CATEGORIES = list_chunker(
    categories=get_categories_name("expense"), chunk_size=3)


async def start_budget(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the budget conversation."""
    keyboard = [
        [
            InlineKeyboardButton(
                "Set/Change", callback_data="set_change_budget"),
            InlineKeyboardButton("Check", callback_data="check_budget"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Welcome to the budget manager! What would you like to do?",
        reply_markup=reply_markup,
    )

    return CHOICE


async def choice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the user's main choice."""
    query = update.callback_query
    await query.answer()
    choice = query.data

    context.user_data['budget_choice'] = choice

    if choice == "set_change_budget":
        today = datetime.now()
        next_month = today + timedelta(days=31)

        keyboard = [
            [
                InlineKeyboardButton(today.strftime(
                    "%B %Y"), callback_data=today.strftime("%B %Y")),
                InlineKeyboardButton(next_month.strftime(
                    "%B %Y"), callback_data=next_month.strftime("%B %Y")),
            ],
            [InlineKeyboardButton("Back", callback_data="start_budget")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text="Which month are you setting or changing the budget for?",
            reply_markup=reply_markup,
        )
        return MONTH_SELECTION

    elif choice == "check_budget":
        await check_budget_handler(update, context)
        return ConversationHandler.END


async def month_selection_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles month selection for setting/changing budget."""
    query = update.callback_query
    await query.answer()
    selected_month_str = query.data
    month, year = selected_month_str.split()

    month_number = datetime.strptime(month, "%B").month

    context.user_data['budget_month'] = month_number
    context.user_data['budget_year'] = int(year)

    keyboard = [
        [InlineKeyboardButton(category, callback_data=category)
         for category in row]
        for row in EXPENSE_CATEGORIES
    ]
    keyboard.append([InlineKeyboardButton(
        "Back", callback_data="back_to_month_selection")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text="Please select a category to set or change the budget for.",
        reply_markup=reply_markup,
    )
    return CATEGORY_SELECTION


async def category_selection_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles category selection and asks for the amount."""
    query = update.callback_query
    await query.answer()
    category_name = query.data
    context.user_data['budget_category_name'] = category_name

    await query.edit_message_text(
        text=f"What is the budget amount for *{category_name}*?",
        parse_mode='Markdown'
    )
    return AMOUNT_INPUT


async def amount_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the budget amount input and saves it."""
    user = update.message.from_user
    amount = update.message.text

    if not is_valid_currency(amount):
        await update.message.reply_text("Invalid amount. Please provide a valid number.")
        return AMOUNT_INPUT

    context.user_data['budget_amount'] = float(amount)

    category_name = context.user_data['budget_category_name']
    category_id = get_category_id(category_name)
    category_type = get_category_type(category_id)
    currency = get_currency(update.effective_chat.id)

    set_budget(
        user_id=user.id,
        budgeted_amount=context.user_data['budget_amount'],
        category_id=category_id,
        category_type=category_type,
        month=context.user_data['budget_month'],
        year=context.user_data['budget_year']
    )

    await update.message.reply_text(
        f"✅ Budget for *{category_name}* in "
        f"*{datetime(context.user_data['budget_year'], context.user_data['budget_month'], 1).strftime('%B %Y')}* "
        f"has been set to *{currency} {context.user_data['budget_amount']:.2f}*.",
        parse_mode='Markdown'
    )

    logger.info("Budget set for %s by %s", category_name, user.first_name)
    return ConversationHandler.END


async def check_budget_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the budget status for the current month."""
    user_id = update.effective_chat.id
    today = datetime.now()

    budgets = get_budget_by_month(user_id, today.month, today.year)
    spends = get_spend_by_month(user_id, today.month, today.year)
    currency = get_currency(update.effective_chat.id)

    if not budgets:
        await update.callback_query.edit_message_text(text="You have not set any budgets for this month.")
        return

    message = f"📊 *Budget Status for {today.strftime('%B %Y')}*\n\n"
    total_budgeted = 0
    total_spent = 0

    spend_dict = {spend.category_id: spend.total_spent for spend in spends}

    for budget in budgets:
        category_name = get_category_name_by_id(budget.category_id)
        budgeted = budget.budgeted_amount
        spent = spend_dict.get(budget.category_id, 0)
        remaining = budgeted - spent

        total_budgeted += budgeted
        total_spent += spent

        emoji = "✅" if remaining >= 0 else "❌"
        message += f"*{category_name}*:\n"
        message += f"  - Budgeted: {currency} {budgeted:.2f}\n"
        message += f"  - Spent: {currency} {spent:.2f}\n"
        message += f"  - Remaining: {currency} {remaining:.2f} {emoji}\n\n"

    total_remaining = total_budgeted - total_spent
    message += f"*Overall Summary*:\n"
    message += f"  - Total Budgeted: {currency} {total_budgeted:.2f}\n"
    message += f"  - Total Spent: {currency} {total_spent:.2f}\n"
    message += f"  - Total Remaining: {currency} {total_remaining:.2f}\n"

    await update.callback_query.edit_message_text(text=message, parse_mode='Markdown')


async def back_budget_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the back button in the budget conversation."""
    query = update.callback_query
    await query.answer()

    if query.data == "start_budget":
        return await start_budget(update, context)
    elif query.data == "back_to_month_selection":
        today = datetime.now()
        next_month = today + timedelta(days=31)

        keyboard = [
            [
                InlineKeyboardButton(today.strftime(
                    "%B %Y"), callback_data=today.strftime("%B %Y")),
                InlineKeyboardButton(next_month.strftime(
                    "%B %Y"), callback_data=next_month.strftime("%B %Y")),
            ],
            [InlineKeyboardButton("Back", callback_data="start_budget")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text="Which month are you setting or changing the budget for?",
            reply_markup=reply_markup,
        )
        return MONTH_SELECTION


async def cancel_budget(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user
    logger.info("User %s canceled the budget conversation.", user.first_name)

    await update.message.reply_text(
        "Budget operation cancelled."
    )

    return ConversationHandler.END
