from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="I'm a bot, please talk to me!"
    )