from telegram import Update, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database.database import get_search_results, get_user_settings
import math

# States
GET_QUERY, PAGINATE = 0, 1
PAGE_SIZE = 5  # Number of results per page

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts the search conversation and asks for a search term."""
    await update.message.reply_text("What transaction are you looking for? Please type a keyword to search.")
    return GET_QUERY

def _build_search_message_and_keyboard(results, query, current_page, total_count, currency_symbol: str):
    """Helper function to build the message and keyboard for search results."""
    if not results:
        return "No transactions found.", None

    message = f"🔎 Search Results for '{query}' (Page {current_page} of {math.ceil(total_count / PAGE_SIZE)}):\n\n"
    for tx in results:
        date_str = tx.timestamp.strftime("%Y-%m-%d")
        icon = "📈" if tx.transaction_type == "income" else "📥"
        message += (
            f"{icon} *{tx.transaction_type.title()}*\n"
            f"📅 {date_str}\n"
            f"💬 {tx.description}\n"
            f"💸 {currency_symbol} {tx.amount:.2f}  |  🏷️ {tx.category}\n\n"
        )

    # --- Pagination Keyboard ---
    keyboard = []
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

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancels the search operation."""
    await update.message.reply_text("Search cancelled.", reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    return ConversationHandler.END