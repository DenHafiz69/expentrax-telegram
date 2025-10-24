from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from utils.database import add_custom_category, get_categories_name, get_custom_categories_name_and_id, get_category_id, delete_category
from utils.misc import list_chunker
from datetime  import date
import calendar

import logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# set higher logging level for httpx to avoid all GET and POST requests being logged

logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

CHOICE, SET, CHANGE, CHECK = range(4)

async def start_budget(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_keyboard = [["Set", "Change", "Check Balance"]]
    
    await update.message.reply_text(
        "What would you like to do today?",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, 
            resize_keyboard=True, 
            one_time_keyboard=True, 
            input_field_placeholder="Choose 'Set', 'Change', or 'Check Balanance'"
        )
    )
    
    return CHOICE
 
async def choice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:

    user_id = update.effective_chat.id
    choice = update.message.text

    if choice == "Set":
        # Query database to get this and next month name
        today = date.today()
        current_month = calendar.month_name[today.month]

        if today.month == 12:
            next_month = calendar.month_name[1]
        else:
            next_month = calendar.month_namep[today.month + 1]

        keyboard_markup = [[current_month, next_month]]

        # Ask the user which month he want to set for
        await update.message.reply_text(
            "Which month do you want to set the budget for?",
            
        ) 
        # Query database and ask user which category and the budget amount
        # Maybe can create function to copy from last month too
        #
    elif choice == "Change":
        # Same process as Set
        # Except for the copy from last month

    elif choice == "Check Balance":

        # Call the function to print the balance for all category for current month
