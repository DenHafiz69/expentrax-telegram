import csv
import io
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

from database.database import get_summary_periods, get_summary_data

# States for conversation
CHOOSE_MONTH = 0

async def export_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the export conversation and asks the user to choose a month."""
    chat_id = update.effective_chat.id

    # Fetch available months from the database
    available_months = get_summary_periods(chat_id, "monthly")

    if not available_months:
        await update.message.reply_text("You have no transaction data to export.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    # Create a keyboard with the available months
    markup = ReplyKeyboardMarkup(
        [[month] for month in available_months],
        one_time_keyboard=True,
        resize_keyboard=True
    )

    await update.message.reply_text(
        "Please choose a month to export as a CSV file:",
        reply_markup=markup
    )

    return CHOOSE_MONTH

async def generate_csv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Fetches data for the selected month, generates a CSV, and sends it."""
    chat_id = update.effective_chat.id
    selected_month = update.message.text  # e.g., "2025-07"

    # Fetch transactions for the selected month
    transactions = get_summary_data(chat_id, "monthly", selected_month)

    if not transactions:
        await update.message.reply_text("No transactions found for the selected month.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    # Create CSV in-memory using io.StringIO
    output = io.StringIO()
    writer = csv.writer(output)

    # Write the header row
    writer.writerow(['Timestamp', 'Type', 'Description', 'Amount', 'Category'])

    # Write transaction data
    for tx in transactions:
        writer.writerow([
            tx.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            tx.transaction_type,
            tx.description,
            tx.amount,
            tx.category
        ])

    # Go to the beginning of the StringIO object to read its content
    output.seek(0)

    await update.message.reply_text(f"Here is your transaction report for {selected_month}.", reply_markup=ReplyKeyboardRemove())

    # Send the CSV file as a document
    await context.bot.send_document(chat_id=chat_id, document=io.BytesIO(output.getvalue().encode('utf-8')), filename=f"transactions_{selected_month}.csv")

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the export operation."""
    await update.message.reply_text("Export cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END