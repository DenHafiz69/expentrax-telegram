# Import necessary modules
from dotenv import load_dotenv
import os
import logging

from utils.database import init_db
from handlers.start import start_command

from telegram import Update
from telegram.ext import filters, ApplicationBuilder, ContextTypes, CommandHandler

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Load environment variables from .env file
load_dotenv()

# Access environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN')

def main() -> None:
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.run_polling()


if __name__ == '__main__':
    init_db()
    main()
