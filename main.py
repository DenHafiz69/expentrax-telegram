# Import necessary modules
from dotenv import load_dotenv
import os
import logging

from utils.database import init_db
from utils.scheduler import start_scheduler
from handlers.start import start_command
from handlers.transaction import (
    start_transaction,
    type_handler,
    amount_handler,
    description_handler,
    category_handler,
    cancel_transaction,
    back_handler,
)
from handlers.recurring import (
    start_recurring_transaction,
    type_handler_recurring,
    amount_handler_recurring,
    description_handler_recurring,
    category_handler_recurring,
    frequency_handler,
    start_date_handler,
    end_date_handler,
    cancel_recurring_transaction,
)
from handlers.history import (
    summary_handler,
    start_history,
    history_choice,
    cancel_history,
    weekly_handler,
    monthly_handler,
    yearly_handler,
    back_history_handler,
)
from handlers.settings import (
    start_settings,
    categories_handler,
    add_category,
    database_action,
    view_categories,
    delete_categories,
    cancel_settings,
    set_currency_handler,
    reset_data_confirm_handler,
    back_settings_handler,
)
from handlers.budget import (
    start_budget,
    choice_handler,
    month_selection_handler,
    category_selection_handler,
    amount_input_handler,
    cancel_budget,
    back_budget_handler,
)


from telegram.ext import (
    filters,
    ApplicationBuilder,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
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

# Recurring Transaction states
RECURRING_TYPE, RECURRING_AMOUNT, RECURRING_DESCRIPTION, RECURRING_CATEGORY, RECURRING_FREQUENCY, RECURRING_START_DATE, RECURRING_END_DATE = range(
    7)

# History states
CHOICE, SUMMARY, WEEKLY, MONTHLY, YEARLY = range(5)

# Settings states
CHOICE, ADD_CATEGORY, DATABASE_ACTION, VIEW_CATEGORIES, DELETE_CATEGORIES, SET_CURRENCY, RESET_DATA, RESET_DATA_CONFIRM = range(
    8)

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
            TYPE: [CallbackQueryHandler(type_handler)],
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, amount_handler)],
            DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND,
                               description_handler)
            ],
            CATEGORY: [
                CallbackQueryHandler(
                    category_handler, pattern="^(?!back_to_description).*$"),
                CallbackQueryHandler(
                    back_handler, pattern="^back_to_description.*$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_transaction)],
    )

    recurring_transaction_handler = ConversationHandler(
        entry_points=[CommandHandler(
            "recurring", start_recurring_transaction)],
        states={
            RECURRING_TYPE: [CallbackQueryHandler(type_handler_recurring)],
            RECURRING_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, amount_handler_recurring)],
            RECURRING_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, description_handler_recurring)],
            RECURRING_CATEGORY: [CallbackQueryHandler(category_handler_recurring)],
            RECURRING_FREQUENCY: [CallbackQueryHandler(frequency_handler)],
            RECURRING_START_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, start_date_handler)],
            RECURRING_END_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, end_date_handler)],
        },
        fallbacks=[CommandHandler("cancel", cancel_recurring_transaction)],
    )

    history_handler = ConversationHandler(
        entry_points=[CommandHandler("history", start_history)],
        states={
            CHOICE: [CallbackQueryHandler(history_choice)],
            SUMMARY: [CallbackQueryHandler(summary_handler)],
            WEEKLY: [CallbackQueryHandler(weekly_handler)],
            MONTHLY: [CallbackQueryHandler(monthly_handler)],
            YEARLY: [CallbackQueryHandler(yearly_handler)],
        },
        fallbacks=[CommandHandler("cancel", cancel_history)],
    )

    settings_handler = ConversationHandler(
        entry_points=[CommandHandler("settings", start_settings)],
        states={
            CHOICE: [
                CallbackQueryHandler(categories_handler)
            ],
            ADD_CATEGORY: [
                CallbackQueryHandler(add_category)
            ],
            DATABASE_ACTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND,
                               database_action),
                CallbackQueryHandler(database_action)
            ],
            VIEW_CATEGORIES: [
                CallbackQueryHandler(view_categories)
            ],
            DELETE_CATEGORIES: [
                CallbackQueryHandler(delete_categories)
            ],
            SET_CURRENCY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND,
                               set_currency_handler)
            ],
            RESET_DATA_CONFIRM: [
                CallbackQueryHandler(reset_data_confirm_handler)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel_settings)],
    )

    budget_handler = ConversationHandler(
        entry_points=[CommandHandler("budget", start_budget)],
        states={
            CHOICE: [CallbackQueryHandler(choice_handler)],
            MONTH_SELECTION: [CallbackQueryHandler(month_selection_handler)],
            CATEGORY_SELECTION: [CallbackQueryHandler(category_selection_handler)],
            AMOUNT_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, amount_input_handler)],
        },
        fallbacks=[CommandHandler("cancel", cancel_budget)],
    )

    application.add_handler(transaction_handler)
    application.add_handler(recurring_transaction_handler)
    application.add_handler(history_handler)
    application.add_handler(settings_handler)
    application.add_handler(budget_handler)

    application.run_polling()


if __name__ == "__main__":
    init_db()
    start_scheduler()
    main()
