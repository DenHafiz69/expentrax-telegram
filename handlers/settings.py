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

CHOICE, ADD_CATEGORY, GET_CATEGORY_NAME, VIEW_CATEGORIES = range(4)

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
            "What type of category you want to add?",
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

    type_of_transaction = update.message.text
    context.user_data['type_of_transaction'] = type_of_transaction # Save the transaction type temporarily
    
    await update.message.reply_text(
        f"Okay, you're adding an '{type_of_transaction}' category.\n\n"
        "What name would you like to give it?",
        reply_markup=ReplyKeyboardRemove()
    )
    
    return GET_CATEGORY_NAME
    
async def get_category_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    
    category_name = update.message.text
    type_of_transaction = context.user_data.get('type_of_transaction')
    
    if not type_of_transaction:
        # Safety check in case something goes wrong
        await update.message.reply_text("Something went wrong. Please start over.")
        return ConversationHandler.END
    
    try:
        # Call your database function with all the required data
        add_custom_category(
            user_id=user.id,
            name=category_name,
            type_of_transaction=type_of_transaction.lower() # e.g., 'expense'
        )
        
        await update.message.reply_text(
            f"✅ Category '{category_name}' has been successfully added!",
            reply_markup=ReplyKeyboardRemove()
        )
    except ValueError as e:
        # Handle cases where the category might already exist
        await update.message.reply_text(f"⚠️ Error: {e}")
    finally:
        # Clean up the temporary storage
        context.user_data.clear()

    return ConversationHandler.END
    
async def view_categories(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    
    # Show the categories that the user want to see i.e "expense" or "income"
    choice = update.message.text
    categories = get_categories_name(choice.lower())
    
    message = "Here are the expense categories:\n\n"
    for category in categories:
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