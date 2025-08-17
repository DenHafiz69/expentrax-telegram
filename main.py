import logging
from telegram import Update
from telegram.ext import filters, MessageHandler, ApplicationBuilder, CommandHandler, ConversationHandler, CallbackQueryHandler
from database.database import init_db

# Import from config.py
from config import BOT_TOKEN, LOG_LEVEL, LOG_FORMAT

# Configure logging
logging.basicConfig(
    format=LOG_FORMAT,
    level=LOG_LEVEL
)

# Import commands from handlers
from handlers.start_handler import start_command
from handlers.help_handler import help_command

from handlers import transaction_handler as transaction
from handlers.view_handler import view_expenses
from handlers import summary_handler as summary, search_handler as search

def get_transaction_handler(command: str):
    return ConversationHandler(
        entry_points=[CommandHandler(command, transaction.add)],
        states={
            0: [MessageHandler(filters.TEXT & ~filters.COMMAND, transaction.get_description)],
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, transaction.get_amount)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, transaction.get_category)],
        },
        fallbacks=[CommandHandler("cancel", transaction.cancel)],
        allow_reentry=True
    )

# Function to register all handler
def register_handler(application):

    # Basic commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    
    application.add_handler(get_transaction_handler("add_expense"))
    application.add_handler(get_transaction_handler("add_income"))
    
    application.add_handler(CommandHandler("view_expenses", view_expenses))
    
    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler("summary", summary.start)],
        states={
            0: [MessageHandler(filters.TEXT & ~filters.COMMAND, summary.choose_period)],
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, summary.choose_option)]
        },
        fallbacks=[CommandHandler("cancel", summary.cancel)],
        allow_reentry=True
    ))
    
    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler("search", search.search)],
        states={
            search.GET_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, search.process_search_query)],
            search.PAGINATE: [
                CallbackQueryHandler(search.paginate_search, pattern="^search_page_"),
                CallbackQueryHandler(search.close_search, pattern="^search_close$")
            ]
        },
        fallbacks=[CommandHandler("cancel", search.cancel)],
        allow_reentry=True
    ))

def main() -> None:
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    register_handler(application)
    
    application.run_polling()

if __name__ == '__main__':
    init_db()
    main()