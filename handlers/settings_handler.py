from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database.database import get_user_settings, update_user_setting

# States for the conversation
SHOW_SETTINGS, GET_NEW_VALUE = 0, 1

async def settings_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Displays the current settings and options to change them.
    This is the entry point for the /settings command.
    """
    chat_id = update.effective_chat.id
    settings = get_user_settings(chat_id)

    text = (
        "⚙️ *Settings*\n\n"
        "Here are your current settings. You can change them using the buttons below.\n\n"
        f"🔹 *Currency:* {settings.currency}\n"
        f"🔸 *Timezone:* {settings.timezone}"
    )

    keyboard = [
        [InlineKeyboardButton("Change Currency", callback_data="settings_change_currency")],
        [InlineKeyboardButton("Change Timezone", callback_data="settings_change_timezone")],
        [InlineKeyboardButton("❌ Close", callback_data="settings_close")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # If the command was triggered by a button press, edit the existing message
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    return SHOW_SETTINGS

async def choose_setting_to_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Asks the user for a new value for the selected setting."""
    query = update.callback_query
    await query.answer()
    
    # 'currency' or 'timezone'
    setting_to_change = query.data.split('_')[-1]
    context.user_data['setting_to_change'] = setting_to_change

    await query.edit_message_text(text=f"Please enter your new {setting_to_change.title()}:")
    return GET_NEW_VALUE

async def get_new_setting_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Updates the setting with the new value from the user."""
    chat_id = update.effective_chat.id
    new_value = update.message.text.strip()
    setting_to_change = context.user_data.get('setting_to_change')

    if not setting_to_change:
        await update.message.reply_text("Something went wrong. Please start over with /settings.")
        return ConversationHandler.END

    # --- Input Validation ---
    if setting_to_change == 'currency':
        if not (1 <= len(new_value) <= 5):
            await update.message.reply_text(
                "❌ Invalid currency symbol. Please enter a symbol between 1 and 5 characters (e.g., $, €, RM)."
            )
            return GET_NEW_VALUE  # Ask again

    if setting_to_change == 'timezone':
        # Basic validation for IANA timezone format (e.g., "Area/City").
        # For more robust validation, a library like `pytz` could be used.
        if '/' not in new_value or ' ' in new_value or len(new_value) > 32:
            await update.message.reply_text(
                "❌ Invalid timezone format. Please use the 'Area/City' format (e.g., America/New_York, Asia/Singapore)."
            )
            return GET_NEW_VALUE  # Ask again

    update_user_setting(chat_id, setting_to_change, new_value)
    await update.message.reply_text(f"✅ Your {setting_to_change.title()} has been updated to *{new_value}*.", parse_mode="Markdown")
    
    context.user_data.clear()
    return await settings_start(update, context)

async def close_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Closes the settings menu."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Settings menu closed.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancels the settings operation."""
    await update.message.reply_text("Settings update cancelled.")
    context.user_data.clear()
    return ConversationHandler.END
