from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from utils.database import add_custom_category, get_categories_name

import logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# set higher logging level for httpx to avoid all GET and POST requests being logged

logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

CHOICE, ADD_CATEGORY, VIEW_CATEGORIES = range(3)

async def start_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_keyboard = [['Add Category', 'View Categories']]
    
    await update.message.reply_text(
        "What would you like to do?",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, 
            resize_keyboard=True, 
            one_time_keyboard=True, 
            input_field_placeholder="Choose 'Add Category' or 'View Categories'"
        ),
    )
    
    return CHOICE
    

async def categories_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    
    choice = update.message.text
    reply_keyboard = [['Expense', 'Income']]
    keyboard_markup = ReplyKeyboardMarkup(
        reply_keyboard,
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Choose 'Expense' or 'Income'"
    )
    
    if choice == "Add Category":
        await update.message.reply_text(
            "What is the category you want to add?",
            reply_markup=keyboard_markup
        )
        return ADD_CATEGORY
    
    elif choice == "View Categories":
        await update.message.reply_text(
            "What would you like to view?",
            reply_markup=keyboard_markup
        )
        return VIEW_CATEGORIES
    
    else:
        await update.message.reply_text(
            "Invalid choice. Please select 'Add Category' or 'View Categories'.\n"
        )
        
        return CHOICE
    

async def add_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user

    category_name = update.message.text
    
    logger.info("Category name: %s, User: %s", category_name, user.first_name)
    
    add_custom_category(
        user_id=user.id,
        name=category_name,
        type_of_transaction="expense"
    )
    
    await update.message.reply_text(
        f"Category {category_name} added!",
        reply_markup=ReplyKeyboardRemove()
    )
    
    return ConversationHandler.END
    
async def view_categories(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    
    # Show the default categories + custom categories
    # Ask the user if he want to edit the custom categories
    
    logger.info("User: %s", user.first_name)
    
    expense_categories = get_categories_name("expense")
    income_categories = get_categories_name("income")
    
    choice = update.message.text
    
    if choice == "Expense":
        message = "Here are the expense categories:\n\n"
        for category in expense_categories:
            message += f"{category}\n"
    elif choice == "Income":
        message = "Here are the income categories:\n\n"
        for category in income_categories:
            message += f"{category}\n"
    
    await update.message.reply_text(
        f"{message}",
        reply_markup=ReplyKeyboardRemove()
    )
    
    return ConversationHandler.END
    
    
async def cancel_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user
    
    logger.info("User %s canceled the conversation.", user.first_name)


    await update.message.reply_text(
        "Transaction cancelled.", reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END