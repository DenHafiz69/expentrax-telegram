# Import necessary modules
from dotenv import load_dotenv
import os
import logging

from utils.database import init_db
from handlers.start import start_command
from handlers.transaction import (
    start_transaction,
    type_handler,
    amount_handler,
    description_handler,
    category_handler,
    cancel_transaction,
)
from handlers.history import (
    summary_handler,
    start_history,
    history_choice,
    cancel_history,
)
from handlers.history import weekly_handler, monthly_handler, yearly_handler
from handlers.settings import (
    start_settings,
    categories_handler,
    add_category,
    database_action,
    view_categories,
    delete_categories,
    cancel_settings,
)
from handlers.budget import (
    start_budget,
    choice_handler,
    month_selection_handler,
    category_selection_handler,
    amount_input_handler,
    cancel_budget,
)


from telegram.ext import (
    filters,
    ApplicationBuilder,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# Load environment variables from .env file
load_dotenv()

# Access environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Transaction states
TYPE, AMOUNT, DESCRIPTION, CATEGORY = range(4)

# History states
CHOICE, SUMMARY, WEEKLY, MONTHLY, YEARLY = range(5)

# Settings states
CHOICE, ADD_CATEGORY, DATABASE_ACTION, VIEW_CATEGORIES, DELETE_CATEGORIES = range(
    5)

# Budget states
CHOICE, MONTH_SELECTION, CATEGORY_SELECTION, AMOUNT_INPUT, CHANGE_CATEGORY, CHANGE_AMOUNT = range(
    6)


def main() -> None:
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Start the application
    application.add_handler(CommandHandler("start", start_command))

    transaction_handler = ConversationHandler(
        entry_points=[CommandHandler("transaction", start_transaction)],
        states={
            TYPE: [MessageHandler(filters.TEXT, type_handler)],
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, amount_handler)],
            DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND,
                               description_handler)
            ],
            CATEGORY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND,
                               category_handler)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_transaction)],
    )

    history_handler = ConversationHandler(
        entry_points=[CommandHandler("history", start_history)],
        states={
            CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, history_choice)],
            SUMMARY: [MessageHandler(filters.TEXT & ~filters.COMMAND, summary_handler)],
            WEEKLY: [MessageHandler(filters.TEXT & ~filters.COMMAND, weekly_handler)],
            MONTHLY: [MessageHandler(filters.TEXT & ~filters.COMMAND, monthly_handler)],
            YEARLY: [MessageHandler(filters.TEXT & ~filters.COMMAND, yearly_handler)],
        },
        fallbacks=[CommandHandler("cancel", cancel_history)],
    )

    settings_handler = ConversationHandler(
        entry_points=[CommandHandler("settings", start_settings)],
        states={
            CHOICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND,
                               categories_handler)
            ],
            ADD_CATEGORY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_category)
            ],
            DATABASE_ACTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND,
                               database_action)
            ],
            VIEW_CATEGORIES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND,
                               view_categories)
            ],
            DELETE_CATEGORIES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND,
                               delete_categories)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel_settings)],
    )

    budget_handler = ConversationHandler(
        entry_points=[CommandHandler("budget", start_budget)],
        states={
            CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choice_handler)],
            MONTH_SELECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, month_selection_handler)],
            CATEGORY_SELECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, category_selection_handler)],
            AMOUNT_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, amount_input_handler)],
        },
        fallbacks=[CommandHandler("cancel", cancel_budget)],
    )

    application.add_handler(transaction_handler)
    application.add_handler(history_handler)
    application.add_handler(settings_handler)
    application.add_handler(budget_handler)

    application.run_polling()


if __name__ == "__main__":
    init_db()
    main()
