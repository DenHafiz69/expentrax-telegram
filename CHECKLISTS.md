# Expentrax - A Telegram Expense Tracking Bot

This project is a complete rewrite of my previous Telegram bot, Expentrax. The goal is to build it from scratch without the use of any AI tools, demonstrating a deeper understanding of the underlying concepts and code. This project is for CS50's final project.

> [!NOTE]  
> This README is generated using Google Gemini and ChatGPT

---

## 🚧 Core Functionalities

This checklist outlines the essential features required for a minimum viable product.

- [x] **User Management**: The bot can uniquely identify and manage individual users.

    - [x] Implemented a database schema to store user information.

    - [x] Handled user authentication and data persistence.

- [x] **Transaction Logging**: The bot can parse and record expense messages.
    
    - [x] Implemented custom keyboards for quick access to commands.

    - [x] Added inline buttons for more dynamic interactions.

    - [x] Integrated with a database to save transaction data.

- [x] **Data Retrieval**: The bot can provide basic expense summaries.

    - [x] Implemented a command to list recent transactions.

    - [x] Implemented a command to show total expenses for a specific period (e.g., this month).

- [ ] **Balance Checking**: Check your current balance (income-expense)

    - [ ] Need a way to reset your balance

    - [ ] Can also check the balance for each category 

---

## ✨ "Wow" Factors

This checklist covers additional features to enhance the bot's functionality and demonstrate advanced skills.

- [x] Custom Category Management: Users can manage their own expense categories.

    - [x] Created a dedicated database table for user-defined categories.

    - [x] Developed commands to add, edit, and delete categories.

- [x] Budgeting: Users can set and track budgets for different categories.

    - [x] Created a dedicated database table for budgets, linked to users and categories.

    - [x] Implemented a command for users to set a budget via /budget.

    - [ ] The bot provides a summary of spending against the budget.

    - [ ] The bot can alert the user when they are nearing their budget limit.

- [ ] Visual Reporting: The bot provides visual summaries of spending.

    - [ ] Integrated a plotting library (e.g., Matplotlib) to create charts.

    - [ ] The bot can send a visual report (e.g., a pie chart) of expenses by category.

- [x] Recurring Transactions: The bot can handle recurring expenses.

    - [x] Implemented a command to set up repeating transactions.

    - [x] Developed a scheduling mechanism to automatically add recurring expenses to the database.

This checklist will serve as a clear roadmap for my development process and provide a great overview for anyone looking at this project.

---

## 🚀 Setup Instructions

### 1. Clone this repo
```bash
git clone https://github.com/DenHafiz69/expentrax.git
cd expentrax
git checkout no-ai-rewrite
```

### 2. Create virtual environment
```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Create `.env` file
Create a `.env` file in the project root with your bot token:
```
BOT_TOKEN=your_telegram_bot_token
```

---

## ▶️ Run the bot
```bash
python main.py
```
