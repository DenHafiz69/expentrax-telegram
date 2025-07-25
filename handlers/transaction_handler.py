from ctypes import resize
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from config import DEFAULT_EXPENSE_CATEGORIES, DEFAULT_INCOME_CATEGORIES
from utils.helpers import is_valid_currency

# States
DESCRIPTION, AMOUNT, CATEGORY = [0, 1, 2]

# Categories
def get_category_markup(transaction_type):
    if transaction_type == "/add_expense":
        return ReplyKeyboardMarkup(
            [[cat] for cat in DEFAULT_EXPENSE_CATEGORIES],
            one_time_keyboard=True,
            resize_keyboard=True
        )
    elif transaction_type == "/add_income":
        return ReplyKeyboardMarkup(
            [[cat] for cat in DEFAULT_INCOME_CATEGORIES],
            one_time_keyboard=True,
            resize_keyboard=True
        )

# User command "/add_income"
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    # Get the type of transaction from the function call in main
    context.user_data["transaction_type"] = update.message.text.split()[0]
    
    args = context.args
    if len(args) >= 2:
        # Case 1: /add_income Salary 5928
        description = " ".join(args[:-1])
        amount = args[-1]

        context.user_data['description'] = description
        
        if not is_valid_currency(amount):
            await update.message.reply_text(
                "❌ Invalid amount. Please enter a valid number for the amount (e.g. 12.50):"
            )
            return AMOUNT
        else:
            context.user_data['amount'] = float(amount)

        await update.message.reply_text(
            f"Description: {description}\nAmount: RM {context.user_data['amount']:.2f}\nNow choose a category:",
            reply_markup=get_category_markup(context.user_data["transaction_type"])
        )

        return CATEGORY
    else:
        # Case 2: interactive flow
        print(f"This is the command {context.user_data["transaction_type"]}")
        await update.message.reply_text("Please enter the description:")
        return DESCRIPTION

# --- Step 1: Description ---
async def get_description(update:Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['description'] = update.message.text
    await update.message.reply_text("Enter the amount:")
    return AMOUNT

# --- Step 2: Amount ---
async def get_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    amount = update.message.text.strip()
    
    if not is_valid_currency(amount):
        await update.message.reply_text(
            "❌ Invalid amount. Please enter a valid number (e.g. 12.50):"
        )
        return AMOUNT
    
    context.user_data['amount'] = float(amount)
    await update.message.reply_text("Choose a category:", reply_markup=get_category_markup(context.user_data["transaction_type"]))
    return CATEGORY

# --- Step 3: Category ---
async def get_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['category'] = update.message.text

    # Finalize
    desc = context.user_data['description']
    amount = context.user_data['amount']
    cat = context.user_data['category']

    await update.message.reply_text(
        f"✅ Income added:\n\n"
        f"Description: {desc}\n"
        f"Amount: RM {amount:.2f}\n"
        f"Category: {cat}",
        reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END

# --- Cancel Handler ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Expense entry cancelled.")
    return ConversationHandler.END