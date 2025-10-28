from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
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
    keyboard = [
        [
            InlineKeyboardButton(
                "➕ Add Category", callback_data="add_category"),
            InlineKeyboardButton(
                "👁️ View Categories", callback_data="view_categories"),
            InlineKeyboardButton("🗑️ Delete Categories",
                                 callback_data="delete_categories"),
        ],
        [
            InlineKeyboardButton(
                "💵 Set Currency", callback_data="set_currency"),
            InlineKeyboardButton("🔄 Reset Data", callback_data="reset_data"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "⚙️ Welcome to Settings! What would you like to do?",
        reply_markup=reply_markup,
    )

    return CHOICE


async def categories_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    choice = query.data

    keyboard = [
        [
            InlineKeyboardButton("💸 Expense", callback_data="expense"),
            InlineKeyboardButton("💰 Income", callback_data="income"),
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="start_settings")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if choice == "add_category":
        await query.edit_message_text(
            text="What type of category you want to add?",
            reply_markup=reply_markup
        )
        return ADD_CATEGORY

    elif choice == "view_categories":
        await query.edit_message_text(
            text="What would you like to view?",
            reply_markup=reply_markup
        )
        return VIEW_CATEGORIES

    elif choice == "delete_categories":
        await query.edit_message_text(
            text="Which would you like to delete?",
            reply_markup=reply_markup
        )
        return DELETE_CATEGORIES

    elif choice == "set_currency":
        await query.edit_message_text(
            text="💱 Please enter the currency symbol you would like to use (e.g., $, €, £, ¥, RM)."
        )
        return SET_CURRENCY

    elif choice == "reset_data":
        keyboard = [
            [
                InlineKeyboardButton("✅ Yes, reset my data",
                                     callback_data="confirm_reset"),
                InlineKeyboardButton(
                    "❌ No, cancel", callback_data="cancel_reset"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="⚠️ Are you sure you want to reset all your data? This action cannot be undone.",
            reply_markup=reply_markup
        )
        return RESET_DATA_CONFIRM

    else:
        await query.edit_message_text(
            text="❌ Invalid choice. Please select an option from the menu."
        )
        return CHOICE


async def add_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    type_of_transaction = query.data
    context.user_data['action'] = 'add_category'
    context.user_data['type_of_transaction'] = type_of_transaction

    await query.edit_message_text(
        text=f"🆕 Adding a new {type_of_transaction} category!\n\n"
        "What name would you like to give it? 💡"
    )

    return DATABASE_ACTION


async def delete_categories(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = update.effective_chat.id
    type_of_transaction = query.data.lower()
    context.user_data['action'] = 'delete_category'

    categories = get_custom_categories_name_and_id(
        user_id, type_of_transaction)

    keyboard = [
        [InlineKeyboardButton(name, callback_data=name) for name, id in row]
        for row in list_chunker(categories, 3)
    ]
    keyboard.append([InlineKeyboardButton(
        "🔙 Back", callback_data="back_to_delete_choice")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text="Which category would you like to delete?",
        reply_markup=reply_markup
    )

    return DATABASE_ACTION


async def database_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_chat.id
    action = context.user_data.get('action')

    if action == "add_category":
        category_name = update.message.text
        type_of_transaction = context.user_data.get('type_of_transaction')

        if category_name in get_categories_name(type_of_transaction.lower(), user_id):
            await update.message.reply_text(
                f"⛔️ Category '{category_name}' already exists for {type_of_transaction}. Please choose another name.",
            )
            return DATABASE_ACTION

        try:
            add_custom_category(
                user_id=user_id,
                name=category_name,
                type_of_transaction=type_of_transaction.lower()
            )
            await update.message.reply_text(
                f"✅ Category '{category_name}' has been successfully added!"
            )
        except:
            pass

    elif action == "delete_category":
        query = update.callback_query
        await query.answer()
        category_name = query.data
        category_id = get_category_id(category_name)
        delete_category(user_id, category_id)
        await query.edit_message_text(
            text=f"⛔️ Category '{category_name}' has been successfully deleted!"
        )

    return ConversationHandler.END


async def view_categories(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    choice = query.data
    categories = get_categories_name(choice.lower())

    message = f"📋 Here are your {choice.lower()} categories:\n\n"
    for category in categories:
        message += f"• {category}\n"

    await query.edit_message_text(
        text=f"{message}"
    )

    return ConversationHandler.END


async def set_currency_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_chat.id
    currency_symbol = update.message.text

    if len(currency_symbol) > 5 or len(currency_symbol) < 1:
        await update.message.reply_text(
            "❌ Invalid currency symbol. Please enter a symbol between 1 and 5 characters."
        )
        return SET_CURRENCY

    set_currency(user_id, currency_symbol)

    await update.message.reply_text(
        f"✅ Your currency has been set to {currency_symbol}."
    )
    return ConversationHandler.END


async def reset_data_confirm_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    choice = query.data
    user_id = update.effective_chat.id

    if choice == 'confirm_reset':
        delete_user_data(user_id)
        await query.edit_message_text(
            text="🗑️ All your data has been successfully reset."
        )
        return ConversationHandler.END
    else:
        await query.edit_message_text(
            text="❌ Data reset cancelled."
        )
        return ConversationHandler.END


async def back_settings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the back button in the settings conversation."""
    query = update.callback_query
    await query.answer()

    if query.data == "start_settings":
        return await start_settings(update, context)
    elif query.data == "back_to_delete_choice":
        keyboard = [
            [
                InlineKeyboardButton("💸 Expense", callback_data="expense"),
                InlineKeyboardButton("💰 Income", callback_data="income"),
            ],
            [InlineKeyboardButton("🔙 Back", callback_data="start_settings")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="🗑️ Which category would you like to delete?",
            reply_markup=reply_markup
        )
        return DELETE_CATEGORIES


async def cancel_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user

    logger.info("User %s canceled the conversation.", user.first_name)

    await update.message.reply_text(
        "❌ Settings operation cancelled."
    )

    return ConversationHandler.END
