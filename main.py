# Import necessary modules
from dotenv import load_dotenv
import os
import logging

from utils.database import init_db
from handlers.start import start_command
from handlers.transaction import start_transaction

from telegram.ext import filters, ApplicationBuilder, ContextTypes, CommandHandler, ConversationHandler

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Load environment variables from .env file
load_dotenv()

# Access environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Conversation states
TYPE, AMOUNT, DESCRIPTION, CATEGORY = range(4)

def main() -> None:
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Start the application
    application.add_handler(CommandHandler("start", start_command))
    
    # Conversation handler with states AMOUNT, DESCRIPTION, CATEGORY
    transaction_handler = ConversationHandler(
        entry_points=[CommandHandler("transaction", start_transaction)],
        states={
            TYPE: [],
            AMOUNT: [],
            DESCRIPTION: [],
            CATEGORY: []
        },
        fallbacks=[]
    )
    
    application.add_handler(transaction_handler)
    
    application.run_polling()


if __name__ == '__main__':
    init_db()
    main()
