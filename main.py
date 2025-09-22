# Import necessary modules
from dotenv import load_dotenv
import os
import logging

from database import init_db, save_user, save_transaction

from telegram import Update
from telegram.ext import filters, ApplicationBuilder, ContextTypes, CommandHandler

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Load environment variables from .env file
load_dotenv()

# Access environment variables
BOT_TOKEN = os.getenv('TELEGRAM_API')

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

def main() -> None:
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.run_polling()


if __name__ == '__main__':
    init_db()
    main()
