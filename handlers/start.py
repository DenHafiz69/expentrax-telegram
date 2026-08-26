import asyncio
from telegram import Update
from telegram.ext import ContextTypes

# Assuming these are correct imports for your database helper functions
from utils.database import save_user, read_user


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles the /start command, registers new users, and sends a welcome message 
    detailing the main commands.
    """

    user_id_to_check = update.effective_user.id
    print(f"DEBUG: Checking database for user ID: {user_id_to_check}")

    user_record = await asyncio.to_thread(read_user, user_id_to_check)

    # Check if user exists in db. If not, save them.
    if not user_record:
        await asyncio.to_thread(
            save_user,
            id=update.effective_user.id,
            username=update.effective_user.username
        )

    # --- Welcome Message Content ---
    message = (
        "👋 <b>Welcome to Expentrax!</b>\n\n"
        "Hey there! I'm your personal finance manager, built to help you track "
        "your income and expenses quickly and easily, right here in Telegram.\n\n"
        "Ready to start managing your money? Here's a quick look at what I can do:\n\n"

        "🚀 <b>Main Commands</b>\n"
        "- /transaction — <b>Log Finances.</b> Starts a conversation to record a new <b>Income</b> or <b>Expense</b>.\n"
        "- /budget - <b>Budgeting.</b> Set/Change or Check your budgets.\n"
        "- /history — <b>View Reports.</b> Check your transactions, get recent history, or view summaries (yearly, monthly, or weekly).\n"
        "- /settings — <b>Manage Categories.</b> View all available categories, and <b>add or remove your own custom categories</b>.\n\n"

        "🎯 <b>Ready to Start?</b>\n"
        "To log your first expense, just type or click the /transaction command below!\n\n"
        "If you have any questions, you can always check the full list of commands using the menu button. Happy tracking!"
    )

    await context.bot.send_message(
        chat_id=update.effective_user.id,
        text=message,
        parse_mode='HTML'  # Use HTML for bolding, headings, and formatting
    )
