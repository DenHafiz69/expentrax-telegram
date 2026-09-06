# Import necessary modules
import os
import json
import base64
import logging
import asyncio
from typing import Any, Optional
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import (
    filters,
    ApplicationBuilder,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
)

from utils.database import init_db, engine
from utils.persistence import SQLAlchemyPersistence
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

# --- Logging Setup ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file for local development
load_dotenv()


def get_bot_token() -> str:
    secret_arn = os.getenv("TELEGRAM_SECRET_ARN")
    if secret_arn:
        import boto3

        client = boto3.client("secretsmanager")
        response = client.get_secret_value(SecretId=secret_arn)
        return response["SecretString"]
    return os.getenv("BOT_TOKEN", "")


BOT_TOKEN = get_bot_token()
if not BOT_TOKEN and not (
    os.getenv("AWS_LAMBDA_FUNCTION_NAME") or os.getenv("AWS_EXECUTION_ENV")
):
    logger.warning("BOT_TOKEN is not configured.")

# State definitions
TYPE, AMOUNT, DESCRIPTION, CATEGORY = range(4)
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

# Initialize database schema
init_db()

# Initialize database-backed persistence for stateless execution
persistence = SQLAlchemyPersistence(db_engine=engine)

# Build the application with persistence attached
application = (
    ApplicationBuilder()
    .token(BOT_TOKEN or "TOKEN_PLACEHOLDER")
    .persistence(persistence)
    .build()
)

# --- Add Handlers with Persistence ---

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
    name="transaction_handler",
    persistent=True,
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
    name="history_handler",
    persistent=True,
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
    name="settings_handler",
    persistent=True,
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
    name="budget_handler",
    persistent=True,
    per_message=False,
)

application.add_handler(CommandHandler("start", start_command))
application.add_handler(transaction_handler)
application.add_handler(history_handler)
application.add_handler(settings_handler)
application.add_handler(budget_handler)


# --- Lambda Webhook Processor ---


async def _process_lambda_update(update_data: dict) -> None:
    """Initialize application if needed and process the incoming update."""
    if not application._initialized:
        await application.initialize()
    update = Update.de_json(update_data, application.bot)
    if update:
        await application.process_update(update)


def handler(event: dict, context: Any = None) -> dict:
    """
    AWS Lambda entrypoint for processing incoming Telegram webhook requests
    from API Gateway (HTTP/REST) or Lambda Function URL.
    """
    headers = event.get("headers") or {}
    # Lowercase headers for case-insensitive lookup
    normalized_headers = {k.lower(): v for k, v in headers.items()}

    # Verify secret token if configured
    secret_token = os.getenv("SECRET_TOKEN")
    if secret_token:
        received_token = normalized_headers.get("x-telegram-bot-api-secret-token")
        if received_token != secret_token:
            logger.warning("Unauthorized webhook request: secret token mismatch.")
            return {
                "statusCode": 403,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Forbidden: invalid secret token"}),
            }

    # Extract and decode request body
    body_raw = event.get("body")
    if not body_raw:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Missing body"}),
        }

    if event.get("isBase64Encoded"):
        body_str = base64.b64decode(body_raw).decode("utf-8")
    elif isinstance(body_raw, dict):
        body_str = json.dumps(body_raw)
    else:
        body_str = body_raw

    try:
        update_data = json.loads(body_str)
    except json.JSONDecodeError as err:
        logger.error("Failed to parse request JSON: %s", err)
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Invalid JSON"}),
        }

    try:
        asyncio.run(_process_lambda_update(update_data))
    except Exception as exc:
        logger.error("Error processing update: %s", exc, exc_info=True)
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Internal server error"}),
        }

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"status": "ok"}),
    }


# --- Local Development Entrypoint ---

if __name__ == "__main__":
    logger.info("Starting Expentrax bot locally...")

    WEBHOOK_URL = os.getenv("WEBHOOK_URL")
    PORT = int(os.getenv("PORT", "8000"))
    LISTEN_ADDRESS = os.getenv("LISTEN_ADDRESS", "0.0.0.0")
    SECRET_TOKEN = os.getenv("SECRET_TOKEN")

    if WEBHOOK_URL:
        logger.info("Starting bot via webhook on %s:%s...", LISTEN_ADDRESS, PORT)
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
