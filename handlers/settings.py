from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from utils.database import (
    add_custom_category,
    get_categories_name,
    get_custom_categories_name_and_id,
    get_category_id,
    delete_category,
    set_currency,
    delete_user_data,
)
from utils.misc import list_chunker

import logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# set higher logging level for httpx to avoid all GET and POST requests being logged

logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

CHOICE, ADD_CATEGORY, DATABASE_ACTION, VIEW_CATEGORIES, DELETE_CATEGORIES, SET_CURRENCY, RESET_DATA, RESET_DATA_CONFIRM = range(
    8)


async def start_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_keyboard = [
        ['Add Category', 'View Categories', 'Delete Categories'],
        ['Set Currency', 'Reset Data']
    ]

    await update.message.reply_text(
        "What would you like to do?",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard,
            resize_keyboard=True,
            one_time_keyboard=True,
            input_field_placeholder="Choose an option"
        ),
    )

    return CHOICE


async def categories_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user

    choice = update.message.text
    reply_keyboard = [['Expense', 'Income']]
    keyboard_markup = ReplyKeyboardMarkup(
        reply_keyboard,
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Choose 'Expense' or 'Income'"
    )

    if choice == "Add Category":
        await update.message.reply_text(
            "What type of category you want to add?",
            reply_markup=keyboard_markup
        )
        return ADD_CATEGORY

    elif choice == "View Categories":
        await update.message.reply_text(
            "What would you like to view?",
            reply_markup=keyboard_markup
        )
        return VIEW_CATEGORIES

    elif choice == "Delete Categories":
        await update.message.reply_text(
            "Which would you like to delete?",
            reply_markup=keyboard_markup
        )
        return DELETE_CATEGORIES

    elif choice == "Set Currency":
        await update.message.reply_text(
            "Please enter the currency symbol you would like to use (e.g., $, €, £, ¥, RM).",
            reply_markup=ReplyKeyboardRemove()
        )
        return SET_CURRENCY

    elif choice == "Reset Data":
        reply_keyboard = [['Yes, reset my data'], ['No, cancel']]
        await update.message.reply_text(
            "⚠️ Are you sure you want to reset all your data? This action cannot be undone.",
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard,
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )
        return RESET_DATA_CONFIRM

    else:
        await update.message.reply_text(
            "Invalid choice. Please select an option from the menu.\n"
        )
        return CHOICE


async def add_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:

    type_of_transaction = update.message.text
    context.user_data['action'] = 'add_category'
    # Save the transaction type temporarily
    context.user_data['type_of_transaction'] = type_of_transaction

    await update.message.reply_text(
        f"Okay, you're adding an '{type_of_transaction}' category.\n\n"
        "What name would you like to give it?",
        reply_markup=ReplyKeyboardRemove()
    )

    return DATABASE_ACTION


async def delete_categories(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:

    user = update.message.from_user
    user_id = update.effective_chat.id
    type_of_transaction = update.message.text.lower()
    context.user_data['action'] = 'delete_category'

    categories = list_chunker(get_custom_categories_name_and_id(
        user_id, type_of_transaction), 3)
    # Display a list of custom category that can be deleted
    reply_keyboard = ReplyKeyboardMarkup(
        categories,
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    await update.message.reply_text(
        "Which category would you like to delete?",
        reply_markup=ReplyKeyboardMarkup(
            categories,
            resize_keyboard=True,
            one_time_keyboard=True,
            input_field_placeholder="Choose the category that you want to delete."
        )
    )

    return DATABASE_ACTION


async def database_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    user_id = update.effective_chat.id
    action = context.user_data.get('action')

    category_name = update.message.text
    type_of_transaction = context.user_data.get('type_of_transaction')

    # Check if the user want to add or delete category
    if action == "add_category":
        # Check if the category is already in database
        if category_name in get_categories_name(type_of_transaction.lower(), user_id):
            await update.message.reply_text(
                f"Categry {category_name} already exists. Please choose another name.",
            )

            return DATABASE_ACTION

        try:
            # Call your database function with all the required data
            add_custom_category(
                user_id=user_id,
                name=category_name,
                type_of_transaction=type_of_transaction.lower()  # e.g., 'expense'
            )

            await update.message.reply_text(
                f"✅ Category '{category_name}' has been successfully added!",
                reply_markup=ReplyKeyboardRemove()
            )
        except:
            pass

    elif action == "delete_category":

        category_id = get_category_id(category_name)

        delete_category(user_id, category_id)

        await update.message.reply_text(
            f"⛔️ Category '{category_name}' has been successfully deleted!",
            reply_markup=ReplyKeyboardRemove()
        )

    return ConversationHandler.END


async def view_categories(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user

    # Show the categories that the user want to see i.e "expense" or "income"
    choice = update.message.text
    categories = get_categories_name(choice.lower())

    message = "Here are the expense categories:\n\n"
    for category in categories:
        message += f"{category}\n"

    await update.message.reply_text(
        f"{message}",
        reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


async def set_currency_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_chat.id
    currency_symbol = update.message.text

    # Basic validation for currency symbol (you can make this more robust)
    if len(currency_symbol) > 5 or len(currency_symbol) < 1:
        await update.message.reply_text(
            "Invalid currency symbol. Please enter a symbol between 1 and 5 characters."
        )
        return SET_CURRENCY

    set_currency(user_id, currency_symbol)

    await update.message.reply_text(
        f"✅ Your currency has been set to {currency_symbol}."
    )
    return ConversationHandler.END


async def reset_data_confirm_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text
    user_id = update.effective_chat.id

    if choice == 'Yes, reset my data':
        delete_user_data(user_id)
        await update.message.reply_text(
            "🗑️ All your data has been successfully reset.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            "Data reset cancelled.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END


async def cancel_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user

    logger.info("User %s canceled the conversation.", user.first_name)

    await update.message.reply_text(
        "Transaction cancelled.", reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END
