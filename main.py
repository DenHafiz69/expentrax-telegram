# Import necessary modules
from dotenv import load_dotenv
import os
import logging
import asyncio
import json

from telegram import Update
from telegram.ext import (
    filters,
    ApplicationBuilder,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from utils.database import init_db
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
from utils.scheduler import check_recurring_transactions

# --- Bot Setup ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file for local development
load_dotenv()

# Access environment variables - fetch from Secrets Manager in Lambda, .env locally


def get_bot_token():
    secret_arn = os.getenv("TELEGRAM_SECRET_ARN")
    if secret_arn:
        import boto3

        client = boto3.client("secretsmanager")
        response = client.get_secret_value(SecretId=secret_arn)
        return response["SecretString"]
    return os.getenv("BOT_TOKEN")


BOT_TOKEN = get_bot_token()
if not BOT_TOKEN:
    raise ValueError("No BOT_TOKEN found in environment variables or Secrets Manager")

# State definitions
TYPE, AMOUNT, DESCRIPTION, CATEGORY = range(4)
(
    RECURRING_TYPE,
    RECURRING_AMOUNT,
    RECURRING_DESCRIPTION,
    RECURRING_CATEGORY,
    RECURRING_FREQUENCY,
    RECURRING_START_DATE,
    RECURRING_END_DATE,
) = range(7)
CHOICE, SUMMARY, WEEKLY, MONTHLY, YEARLY = range(5)
(
    SETTINGS_CHOICE,
    ADD_CATEGORY,
    DATABASE_ACTION,
    VIEW_CATEGORIES,
    DELETE_CATEGORIES,
    SET_CURRENCY,
    RESET_DATA,
    RESET_DATA_CONFIRM,
) = range(8)
(
    BUDGET_CHOICE,
    MONTH_SELECTION,
    CATEGORY_SELECTION,
    AMOUNT_INPUT,
    CHANGE_CATEGORY,
    CHANGE_AMOUNT,
) = range(6)

# Initialize the database
init_db()

# Build the application and add handlers once
application = ApplicationBuilder().token(BOT_TOKEN).build()

# Add handlers
transaction_handler = ConversationHandler(
    entry_points=[CommandHandler("transaction", start_transaction)],
    states={
        TYPE: [CallbackQueryHandler(type_handler)],
        AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, amount_handler)],
        DESCRIPTION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, description_handler)
        ],
        CATEGORY: [
            CallbackQueryHandler(
                category_handler, pattern="^(?!back_to_description).*$"
            ),
            CallbackQueryHandler(back_handler, pattern="^back_to_description.*$"),
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel_transaction)],
    per_message=False,
)

recurring_transaction_handler = ConversationHandler(
    entry_points=[CommandHandler("recurring", start_recurring_transaction)],
    states={
        RECURRING_TYPE: [CallbackQueryHandler(type_handler_recurring)],
        RECURRING_AMOUNT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, amount_handler_recurring)
        ],
        RECURRING_DESCRIPTION: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND, description_handler_recurring
            )
        ],
        RECURRING_CATEGORY: [CallbackQueryHandler(category_handler_recurring)],
        RECURRING_FREQUENCY: [CallbackQueryHandler(frequency_handler)],
        RECURRING_START_DATE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, start_date_handler)
        ],
        RECURRING_END_DATE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, end_date_handler)
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel_recurring_transaction)],
    per_message=False,
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
    per_message=False,
)

settings_handler = ConversationHandler(
    entry_points=[CommandHandler("settings", start_settings)],
    states={
        SETTINGS_CHOICE: [CallbackQueryHandler(categories_handler)],
        ADD_CATEGORY: [CallbackQueryHandler(add_category)],
        DATABASE_ACTION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, database_action),
            CallbackQueryHandler(database_action),
        ],
        VIEW_CATEGORIES: [CallbackQueryHandler(view_categories)],
        DELETE_CATEGORIES: [CallbackQueryHandler(delete_categories)],
        SET_CURRENCY: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, set_currency_handler)
        ],
        RESET_DATA_CONFIRM: [CallbackQueryHandler(reset_data_confirm_handler)],
    },
    fallbacks=[CommandHandler("cancel", cancel_settings)],
    per_message=False,
)

budget_handler = ConversationHandler(
    entry_points=[CommandHandler("budget", start_budget)],
    states={
        BUDGET_CHOICE: [CallbackQueryHandler(choice_handler)],
        MONTH_SELECTION: [CallbackQueryHandler(month_selection_handler)],
        CATEGORY_SELECTION: [CallbackQueryHandler(category_selection_handler)],
        AMOUNT_INPUT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, amount_input_handler)
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel_budget)],
    per_message=False,
)

application.add_handler(CommandHandler("start", start_command))
application.add_handler(transaction_handler)
application.add_handler(recurring_transaction_handler)
application.add_handler(history_handler)
application.add_handler(settings_handler)
application.add_handler(budget_handler)


async def run_scheduler(context: ContextTypes.DEFAULT_TYPE):
    """Run the recurring transactions check."""
    logger.info("Starting recurring transaction check via JobQueue...")
    await asyncio.to_thread(check_recurring_transactions)
    logger.info("Recurring transaction check finished.")


def handler(event, context):
    """AWS Lambda handler for processing Telegram webhook updates."""
    body = json.loads(event.get("body") or "{}")
    update = Update.de_json(body, application.bot)
    if update:
        asyncio.run(application.process_update(update))
    return {
        "statusCode": 200,
        "body": json.dumps({"status": "ok"}),
    }


if __name__ == "__main__":
    logger.info("Starting bot...")
    # Run recurring check once per hour to ensure it's picked up daily
    application.job_queue.run_repeating(run_scheduler, interval=3600, first=10)

    WEBHOOK_URL = os.getenv("WEBHOOK_URL")
    PORT = int(os.getenv("PORT", "8000"))
    LISTEN_ADDRESS = os.getenv("LISTEN_ADDRESS", "0.0.0.0")
    SECRET_TOKEN = os.getenv("SECRET_TOKEN")

    if WEBHOOK_URL:
        logger.info(f"Starting bot via webhook on {LISTEN_ADDRESS}:{PORT}...")
        application.run_webhook(
            listen=LISTEN_ADDRESS,
            port=PORT,
            url_path=f"webhook/{BOT_TOKEN}",
            webhook_url=f"{WEBHOOK_URL}/webhook/{BOT_TOKEN}",
            secret_token=SECRET_TOKEN,
            allowed_updates=Update.ALL_TYPES,
        )
    else:
        logger.info("Starting bot via polling...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
