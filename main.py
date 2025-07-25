from importlib.metadata import entry_points
import os
import logging
from telegram import Update
from telegram.ext import filters, MessageHandler, ApplicationBuilder, ContextTypes, CommandHandler, ConversationHandler

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Import from config.py
from config import BOT_TOKEN

# Initialize database connection

# Import commands from handlers
from handlers.start_handler import start_command
# from handlers.help_handler import help_command

# from handlers import expense_handler as expense
# from handlers import income_handler as income

from handlers import transaction_handler as transaction

# from handlers.summary_handler import summary_command

def get_transaction_handler(command: str):
    return ConversationHandler(
        entry_points=[CommandHandler(command, transaction.add)],
        states={
            0: [MessageHandler(filters.TEXT & ~filters.COMMAND, transaction.get_description)],
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, transaction.get_amount)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, transaction.get_category)],
        },
        fallbacks=[CommandHandler("cancel", transaction.cancel)]
    )

# Function to register all handler
def register_handler(application):

    # Basic commands
    application.add_handler(CommandHandler("start", start_command))
    # application.add_handler(CommandHandler("help", help_command))
    
    application.add_handler(get_transaction_handler("add_expense"))
    application.add_handler(get_transaction_handler("add_income"))
    
    # application.add_handler(CommandHandler("add_income", income.add))
    # application.add_handler(CommandHandler("summary", summary_command))

def main() -> None:
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    register_handler(application)
    
    application.run_polling()

if __name__ == '__main__':
    main()