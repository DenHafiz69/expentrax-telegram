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

    user_record = read_user(user_id_to_check)
    
    # Check if user exists in db. If not, save them.
    if not user_record:
        save_user(
            # Using update.effective_user.id for consistency, which is generally 
            # the same as update.effective_user.id in a private chat.
            id=update.effective_user.id, 
            username=update.effective_user.username
        )
    
    # --- Welcome Message Content ---
    message = (
        "👋 **Welcome to ExpenTrax!**\n\n"
        "Hey there! I'm your personal finance manager, built to help you track "
        "your income and expenses quickly and easily, right here in Telegram.\n\n"
        "Ready to start managing your money? Here's a quick look at what I can do:\n\n"
        
        "### 🚀 **Main Commands**\n"
        "•  **/transaction** — **Log Finances.** Starts a conversation to record a new **Income** or **Expense**.\n"
        "•  **/history** — **View Reports.** Check your transactions, get recent history, or view summaries (yearly, monthly, or weekly).\n"
        "•  **/settings** — **Manage Categories.** View all available categories, and **add or remove your own custom categories**.\n\n"
        
        "### 🎯 **Ready to Start?**\n"
        "To log your first expense, just type or click the **/transaction** command below!\n\n"
        "If you have any questions, you can always check the full list of commands using the menu button. Happy tracking!"
    )

    await context.bot.send_message(
        chat_id=update.effective_user.id,
        text=message,
        parse_mode='Markdown' # Use Markdown for bolding, headings, and formatting
    )
