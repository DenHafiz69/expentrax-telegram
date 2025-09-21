from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from database.database import get_summary_periods, get_summary_data
from collections import defaultdict
import matplotlib.pyplot as plt
import io
import os
from datetime import datetime

# States
CHOOSE_PERIOD, CHOOSE_OPTION = [0, 1]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_markup = ReplyKeyboardMarkup(
        [["Yearly"], ["Monthly"], ["Weekly"]],
        one_time_keyboard=True,
        resize_keyboard=True
    )
    await update.message.reply_text("Please choose a summary period:", reply_markup=reply_markup)
    return CHOOSE_PERIOD

async def choose_period(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    context.user_data["period"] = update.message.text.lower()

    available = get_summary_periods(chat_id, context.user_data["period"])

    if not available:
        await update.message.reply_text("No data available for this period.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    # If only one option, send summary directly
    if len(available) == 1:
        context.user_data["option"] = available[0]
        return await send_summary(update, context)

    # Let user pick from available options
    markup = ReplyKeyboardMarkup(
        [[str(opt)] for opt in available],
        one_time_keyboard=True,
        resize_keyboard=True
    )
    await update.message.reply_text(f"Choose a {context.user_data['period']} option:", reply_markup=markup)
    return CHOOSE_OPTION

async def choose_option(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["option"] = update.message.text
    return await send_summary(update, context)

async def send_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    period = context.user_data["period"]
    option = context.user_data["option"]

    summary = get_summary_data(chat_id, period, option)
    print(f"Summary data: {summary}")
    if not summary:
        await update.message.reply_text("No transactions found.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    # Use defaultdict for efficient aggregation
    totals = defaultdict(float)
    expense_categories = defaultdict(float)
    
    for item in summary:
        if item.transaction_type == "income":
            totals["income"] += item.amount
        elif item.transaction_type == "expense":
            totals["expense"] += item.amount
            category = item.category if item.category else "Uncategorized"
            expense_categories[category] += item.amount
    
    total_income = totals["income"]
    total_expense = totals["expense"]
    balance = total_income - total_expense

    # Create basic summary text
    text = (
        f"📊 Summary ({period.title()} - {option}):\n\n"
        f"Income: RM {total_income:.2f}\n"
        f"Expense: RM {total_expense:.2f}\n"
        f"Balance: RM {balance:.2f}"
    )

    # Add expense breakdown by category if there are expenses
    if expense_categories:
        text += "\n\n💰 Expense Breakdown by Category:\n"
        for category, amount in sorted(expense_categories.items(), key=lambda x: x[1], reverse=True):
            percentage = (amount / total_expense) * 100 if total_expense > 0 else 0
            text += f"• {category}: RM {amount:.2f} ({percentage:.1f}%)\n"

    # Send the text summary first
    await update.message.reply_text(text, reply_markup=ReplyKeyboardRemove())

    # Generate and send pie chart if there are expenses
    if expense_categories:
        try:
            chart_path = create_expense_pie_chart(summary, period, option)
            if chart_path and os.path.exists(chart_path):
                with open(chart_path, 'rb') as photo:
                    await update.message.reply_photo(
                        photo=photo,
                        caption=f"📈 Expense Categories Pie Chart ({period.title()} - {option})"
                    )
                # Clean up the temporary file
                os.remove(chart_path)
            else:
                await update.message.reply_text("⚠️ Could not generate pie chart.")
        except Exception as e:
            print(f"Error generating pie chart: {e}")
            await update.message.reply_text("⚠️ Error generating pie chart.")

    return ConversationHandler.END

def create_expense_pie_chart(summary_data, period, option):
    """Create a pie chart for expense categories and return the file path."""
    # Filter only expenses and group by category
    expense_categories = defaultdict(float)
    
    for item in summary_data:
        if item.transaction_type == "expense":
            category = item.category if item.category else "Uncategorized"
            expense_categories[category] += item.amount
    
    if not expense_categories:
        return None
    
    # Create the pie chart
    plt.figure(figsize=(10, 8))
    categories = list(expense_categories.keys())
    amounts = list(expense_categories.values())
    
    # Create colors for the pie chart
    colors = plt.cm.Set3(range(len(categories)))
    
    # Create pie chart with percentage labels
    wedges, texts, autotexts = plt.pie(
        amounts, 
        labels=categories, 
        autopct='%1.1f%%',
        colors=colors,
        startangle=90,
        textprops={'fontsize': 10}
    )
    
    # Enhance the appearance
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')
    
    plt.title(f'Expense Categories ({period.title()} - {option})', fontsize=14, fontweight='bold', pad=20)
    
    # Add a legend with amounts
    legend_labels = [f'{cat}: RM {amt:.2f}' for cat, amt in expense_categories.items()]
    plt.legend(wedges, legend_labels, title="Categories", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))
    
    plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
    
    # Save the chart to a temporary file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"expense_chart_{timestamp}.png"
    filepath = os.path.join("/tmp", filename)
    
    plt.tight_layout()
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    plt.close()  # Close the figure to free memory
    
    return filepath

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Summary cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END
