from telegram import Update, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database.database import get_search_results, get_user_settings, get_transaction_by_id, update_transaction, delete_transaction
from config import DEFAULT_EXPENSE_CATEGORIES, DEFAULT_INCOME_CATEGORIES
from utils.validators import is_valid_currency
import math

# States
GET_QUERY, PAGINATE, EDIT_CHOICE, EDIT_DESCRIPTION, EDIT_AMOUNT, EDIT_CATEGORY = 0, 1, 2, 3, 4, 5
PAGE_SIZE = 4  # Number of results per page

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts the search conversation and asks for a search term."""
    await update.message.reply_text("What transaction are you looking for? Please type a keyword to search.")
    return GET_QUERY

def _build_search_message_and_keyboard(results, query, current_page, total_count, currency_symbol: str):
    """Helper function to build the message and keyboard for search results."""
    if not results:
        return "No transactions found.", None

    message = f"🔎 Search Results for '{query}' (Page {current_page} of {math.ceil(total_count / PAGE_SIZE)}):\n\n"
    keyboard = []
    
    for i, tx in enumerate(results):
        date_str = tx.timestamp.strftime("%Y-%m-%d")
        icon = "📈" if tx.transaction_type == "income" else "📥"
        message += (
            f"{i+1}. {icon} *{tx.transaction_type.title()}*\n"
            f"📅 {date_str}\n"
            f"💬 {tx.description}\n"
            f"💸 {currency_symbol} {tx.amount:.2f}  |  🏷️ {tx.category}\n\n"
        )
        
        # Add edit button for each transaction
        keyboard.append([InlineKeyboardButton(f"✏️ Edit #{i+1}", callback_data=f"edit_{tx.id}")])

    # --- Pagination Keyboard ---
    total_pages = math.ceil(total_count / PAGE_SIZE)

    nav_row = []
    if current_page > 1:
        nav_row.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"search_page_{current_page - 1}"))

    if current_page < total_pages:
        nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"search_page_{current_page + 1}"))

    if nav_row:
        keyboard.append(nav_row)

    keyboard.append([InlineKeyboardButton("❌ Close", callback_data="search_close")])

    return message.strip(), InlineKeyboardMarkup(keyboard)

async def process_search_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes the user's initial search query and displays the first page of results."""
    chat_id = update.effective_chat.id
    query = update.message.text
    context.user_data['search_query'] = query
    context.user_data['search_page'] = 1

    settings = get_user_settings(chat_id)
    results, total_count = get_search_results(chat_id, query, page=1, page_size=PAGE_SIZE)

    if total_count == 0:
        await update.message.reply_text(f"No transactions found matching '{query}'.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    message, keyboard = _build_search_message_and_keyboard(results, query, 1, total_count, settings.currency)

    await update.message.reply_text(message, reply_markup=keyboard, parse_mode="Markdown")
    return PAGINATE

async def paginate_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles pagination for search results via inline keyboard."""
    await update.callback_query.answer()
    callback_data = update.callback_query.data

    # callback_data is like "search_page_2"
    try:
        page = int(callback_data.split('_')[-1])
    except (ValueError, IndexError):
        await update.callback_query.edit_message_text("An error occurred. Please try the search again.")
        context.user_data.clear()
        return ConversationHandler.END

    chat_id = update.effective_chat.id
    query = context.user_data.get('search_query')
    
    if not query:
        await update.callback_query.edit_message_text("Your search session has expired. Please start a new search.")
        return ConversationHandler.END

    settings = get_user_settings(chat_id)
    context.user_data['search_page'] = page
    results, total_count = get_search_results(chat_id, query, page=page, page_size=PAGE_SIZE)
    message, keyboard = _build_search_message_and_keyboard(results, query, page, total_count, settings.currency)

    await update.callback_query.edit_message_text(text=message, reply_markup=keyboard, parse_mode="Markdown")
    return PAGINATE

async def close_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Closes the search results message."""
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("Search closed.")
    context.user_data.clear()
    return ConversationHandler.END

async def start_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts editing a transaction."""
    await update.callback_query.answer()
    callback_data = update.callback_query.data
    
    # Extract transaction ID from callback_data like "edit_123"
    try:
        transaction_id = int(callback_data.split('_')[1])
    except (ValueError, IndexError):
        await update.callback_query.edit_message_text("An error occurred. Please try the search again.")
        return ConversationHandler.END

    chat_id = update.effective_chat.id
    transaction = get_transaction_by_id(transaction_id, chat_id)
    
    if not transaction:
        await update.callback_query.edit_message_text("Transaction not found or you don't have permission to edit it.")
        return ConversationHandler.END

    # Store transaction info in context
    context.user_data['edit_transaction_id'] = transaction_id
    context.user_data['edit_transaction'] = {
        'description': transaction.description,
        'amount': transaction.amount,
        'category': transaction.category,
        'transaction_type': transaction.transaction_type
    }

    # Show current transaction details and edit options
    settings = get_user_settings(chat_id)
    date_str = transaction.timestamp.strftime("%Y-%m-%d")
    icon = "📈" if transaction.transaction_type == "income" else "📥"
    
    message = (
        f"✏️ *Editing Transaction*\n\n"
        f"{icon} *{transaction.transaction_type.title()}*\n"
        f"📅 {date_str}\n"
        f"💬 {transaction.description}\n"
        f"💸 {settings.currency} {transaction.amount:.2f}\n"
        f"🏷️ {transaction.category}\n\n"
        f"What would you like to edit?"
    )

    keyboard = [
        [InlineKeyboardButton("📝 Description", callback_data="edit_field_description")],
        [InlineKeyboardButton("💰 Amount", callback_data="edit_field_amount")],
        [InlineKeyboardButton("🏷️ Category", callback_data="edit_field_category")],
        [InlineKeyboardButton("🗑️ Delete Transaction", callback_data="edit_field_delete")],
        [InlineKeyboardButton("💾 Save Changes", callback_data="edit_save")],
        [InlineKeyboardButton("❌ Cancel", callback_data="edit_cancel")]
    ]

    await update.callback_query.edit_message_text(
        text=message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return EDIT_CHOICE

async def handle_edit_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the user's choice of what to edit."""
    await update.callback_query.answer()
    callback_data = update.callback_query.data

    if callback_data == "edit_field_description":
        await update.callback_query.edit_message_text("Enter the new description:")
        return EDIT_DESCRIPTION
    elif callback_data == "edit_field_amount":
        await update.callback_query.edit_message_text("Enter the new amount:")
        return EDIT_AMOUNT
    elif callback_data == "edit_field_category":
        transaction_type = context.user_data['edit_transaction']['transaction_type']
        categories = DEFAULT_EXPENSE_CATEGORIES if transaction_type == "expense" else DEFAULT_INCOME_CATEGORIES
        
        keyboard = ReplyKeyboardMarkup(
            [[cat] for cat in categories],
            one_time_keyboard=True,
            resize_keyboard=True
        )
        
        await update.callback_query.edit_message_text("Choose a new category:")
        # Send a new message with the keyboard since we can't edit inline keyboard to reply keyboard
        await update.callback_query.message.reply_text("Select a category:", reply_markup=keyboard)
        return EDIT_CATEGORY
    elif callback_data == "edit_field_delete":
        transaction_id = context.user_data['edit_transaction_id']
        chat_id = update.effective_chat.id
        
        if delete_transaction(transaction_id, chat_id):
            await update.callback_query.edit_message_text("✅ Transaction deleted successfully.")
        else:
            await update.callback_query.edit_message_text("❌ Failed to delete transaction.")
        
        context.user_data.clear()
        return ConversationHandler.END
    elif callback_data == "edit_save":
        # Save all changes
        transaction_id = context.user_data['edit_transaction_id']
        chat_id = update.effective_chat.id
        edit_data = context.user_data['edit_transaction']
        
        success = update_transaction(
            transaction_id, 
            chat_id,
            description=edit_data['description'],
            amount=edit_data['amount'],
            category=edit_data['category']
        )
        
        if success:
            settings = get_user_settings(chat_id)
            message = (
                f"✅ *Transaction Updated Successfully*\n\n"
                f"💬 {edit_data['description']}\n"
                f"💸 {settings.currency} {edit_data['amount']:.2f}\n"
                f"🏷️ {edit_data['category']}"
            )
            await update.callback_query.edit_message_text(message, parse_mode="Markdown")
        else:
            await update.callback_query.edit_message_text("❌ Failed to update transaction.")
        
        context.user_data.clear()
        return ConversationHandler.END
    elif callback_data == "edit_cancel":
        await update.callback_query.edit_message_text("Edit cancelled.")
        context.user_data.clear()
        return ConversationHandler.END

async def edit_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles editing the transaction description."""
    new_description = update.message.text.strip()
    context.user_data['edit_transaction']['description'] = new_description
    
    await update.message.reply_text(
        f"✅ Description updated to: {new_description}\n\n"
        "You can continue editing other fields or save your changes.",
        reply_markup=ReplyKeyboardRemove()
    )
    
    # Return to edit choice menu
    return await show_edit_menu(update, context)

async def edit_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles editing the transaction amount."""
    amount_text = update.message.text.strip()
    
    if not is_valid_currency(amount_text):
        await update.message.reply_text(
            "❌ Invalid amount. Please enter a valid number (e.g. 12.50):"
        )
        return EDIT_AMOUNT
    
    new_amount = float(amount_text)
    context.user_data['edit_transaction']['amount'] = new_amount
    
    await update.message.reply_text(
        f"✅ Amount updated to: {new_amount:.2f}\n\n"
        "You can continue editing other fields or save your changes."
    )
    
    # Return to edit choice menu
    return await show_edit_menu(update, context)

async def edit_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles editing the transaction category."""
    new_category = update.message.text.strip()
    context.user_data['edit_transaction']['category'] = new_category
    
    await update.message.reply_text(
        f"✅ Category updated to: {new_category}\n\n"
        "You can continue editing other fields or save your changes.",
        reply_markup=ReplyKeyboardRemove()
    )
    
    # Return to edit choice menu
    return await show_edit_menu(update, context)

async def show_edit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows the edit menu with current transaction details."""
    edit_data = context.user_data['edit_transaction']
    chat_id = update.effective_chat.id
    settings = get_user_settings(chat_id)
    
    message = (
        f"✏️ *Current Transaction Details*\n\n"
        f"💬 {edit_data['description']}\n"
        f"💸 {settings.currency} {edit_data['amount']:.2f}\n"
        f"🏷️ {edit_data['category']}\n\n"
        f"What would you like to edit next?"
    )

    keyboard = [
        [InlineKeyboardButton("📝 Description", callback_data="edit_field_description")],
        [InlineKeyboardButton("💰 Amount", callback_data="edit_field_amount")],
        [InlineKeyboardButton("🏷️ Category", callback_data="edit_field_category")],
        [InlineKeyboardButton("🗑️ Delete Transaction", callback_data="edit_field_delete")],
        [InlineKeyboardButton("💾 Save Changes", callback_data="edit_save")],
        [InlineKeyboardButton("❌ Cancel", callback_data="edit_cancel")]
    ]

    await update.message.reply_text(
        text=message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return EDIT_CHOICE

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancels the search operation."""
    await update.message.reply_text("Search cancelled.", reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    return ConversationHandler.END
