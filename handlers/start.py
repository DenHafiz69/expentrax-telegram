from telegram import Update
from telegram.ext import ContextTypes

from utils.database import save_user, read_user

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not read_user(update.effective_chat.id): # Check if user exist in db
        save_user(
            chat_id=update.effective_chat.id,
            username=update.effective_chat.username
        )
    
    message = (
        "Hi"
    )

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message
    )