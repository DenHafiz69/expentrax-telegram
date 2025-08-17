from telegram import Update
from telegram.ext import ContextTypes

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays a help message with all available commands."""
    help_text = (
        "❓ *How can I help you?*\n\n"
        "Here is a list of commands you can use to manage your finances:\n\n"
        "*Available Commands:*\n"
        "📥 /add\_expense – Add a new expense\n"
        "📈 /add\_income – Add a new income\n"
        "🧾 /view\_expenses – See your last 3 expense entries\n"
        "📊 /summary – Get a financial summary\n"
        "🔍 /search – Find specific transactions\n\n"
        "*Upcoming Features:*\n"
        "💰 /budget, /export\n\n"
        "You can type /cancel at any time to stop an ongoing operation."
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")