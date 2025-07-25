from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from config import DEFAULT_EXPENSE_CATEGORIES as CATEGORIES
from utils.helpers import is_valid_currency

# States
DESCRIPTION, PRICE, CATEGORY = range(3)

# Categories
CATEGORY_MARKUP = ReplyKeyboardMarkup(
    [[cat] for cat in CATEGORIES], one_time_keyboard=True, resize_keyboard=True
)

# User command "/add_expense"
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) >= 2:
        # Case 1: /add_expense Nasi Lemak 11.50
        description = " ".join(args[:-1])
        price = args[-1]

        context.user_data['description'] = description
        
        if not is_valid_currency(price):
            await update.message.reply_text(
                "❌ Invalid amount. Please enter a valid number for the price (e.g. 12.50):"
            )
            return PRICE
        else:
            context.user_data['price'] = float(price)

        await update.message.reply_text(
            f"Description: {description}\nPrice: {price}\nNow choose a category:",
            reply_markup=CATEGORY_MARKUP
        )

        return CATEGORY
    else:
        # Case 2: interactive flow
        await update.message.reply_text("Please enter the expense description:")
        return DESCRIPTION

# --- Step 1: Description ---
async def get_description(update:Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['description'] = update.message.text
    await update.message.reply_text("Enter the price:")
    return PRICE

# --- Step 2: Price ---
async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    price = update.message.text.strip()
    
    if not is_valid_currency(price):
        await update.message.reply_text(
            "❌ Invalid amount. Please enter a valid number (e.g. 12.50):"
        )
        return PRICE
    
    context.user_data['price'] = float(price)
    await update.message.reply_text("Choose a category:", reply_markup=CATEGORY_MARKUP)
    return CATEGORY

# --- Step 3: Category ---
async def get_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['category'] = update.message.text

    # Finalize
    desc = context.user_data['description']
    price = context.user_data['price']
    cat = context.user_data['category']

    await update.message.reply_text(
        f"✅ Expense added:\n\n"
        f"Description: {desc}\n"
        f"Price: {price:.2f}\n"
        f"Category: {cat}",
        reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END

# --- Cancel Handler ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Expense entry cancelled.")
    return ConversationHandler.END