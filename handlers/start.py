from telegram import Update
from telegram.ext import ContextTypes

from utils.database import save_user

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    message = (
        "Hi"
    )
    
    save_user(
        chat_id=update.effective_chat.id,
        username=update.effective_chat.username
    )
    
    # If new user, record the telegram id and username into the user table

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message
    )