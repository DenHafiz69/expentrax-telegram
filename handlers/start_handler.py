from telegram import Update
from telegram.ext import ContextTypes

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return a start message to the user"""
    message = (
        "👋 *Welcome to Expense Tracker Bot!*\n\n"
        "I can help you track your spending, set budgets, and generate reports.\n\n"
        "*Here are the commands you can use:*\n"
        "📥  /add\_expense – Add a new expense\n"
        "📈  /add\_income – Add a new income\n"
        "👀  /view\_expenses – See your recent expenses\n\n"
        "📊  /summary – View reports (monthly/yearly)\n"
        "💰  /budget – Set or view your monthly budget\n"
        "🔍  /search – Find specific transactions\n\n"
        "📤  /export – Export your data as a CSV file\n"
        "❓  /help – Show this help message\n\n"
        "Let’s get started!"
    )

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message,
        parse_mode="Markdown"
    )
