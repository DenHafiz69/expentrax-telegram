from telegram import Update
from telegram.ext import ContextTypes
from database.database import get_recent_expenses
from datetime import datetime

async def view_expenses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    expenses = get_recent_expenses(chat_id)

    if not expenses:
        await update.message.reply_text("You don't have any expenses recorded yet.")
        return

    message = "🧾 Your Recent Expenses:\n\n"
    for tx in expenses:
        date_str = tx.timestamp.strftime("%Y-%m-%d")
        message += (
            f"📅 {date_str}\n"
            f"💬 {tx.description}\n"
            f"💸 RM {tx.amount:.2f}  |  🏷️ {tx.category}\n\n"
        )

    await update.message.reply_text(message.strip())
