from telegram import Update
from telegram.ext import ContextTypes

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "👋 *Welcome to Expense Tracker Bot!*\n\n"
        "I can help you track your spending, set budgets, and generate reports.\n\n"
        "*Here are the commands you can use:*\n"
        "📥 `/add_expense` – Add a new expense\n"
        "📈 `/add_income` – Add a new income\n"
        "📊 `/summary` – View reports (monthly/yearly)\n"
        "💰 `/budget` – Set or view your monthly budget\n"
        "🔍 `/search` – Find specific transactions\n"
        "📤 `/export` – Export your data as CSV\n"
        "⚙️ `/settings` – Change currency, timezone, etc.\n"
        "❓ `/help` – Get help using the bot\n\n"
        "Let’s get started!"
    )

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message,
        parse_mode="Markdown"
    )
