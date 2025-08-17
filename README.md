# 💸 ExpenTrax - Telegram Expense Tracker Bot

A simple Telegram bot to track your expenses and income, view summaries, and export reports — all from your chat.

## ✅ Features

- Add expense and income entries
- Choose from preset categories
- View monthly/yearly summaries
- Export data as CSV
- Set budgets and preferences

---

## 🚀 Setup Instructions

### 1. Clone this repo
```bash
git clone https://github.com/DenHafiz69/expentrax.git
cd expentrax
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

---

## 🤖 Available Commands

| Command        | Function                     |
|----------------|------------------------------|
| /add_expense   | Add an expense               |
| /add_income    | Add an income                |
| /view_expenses | View recent expenses         |
| /summary       | Monthly/yearly summary       |
| /budget        | Set/view budget              |
| /search        | Search transactions          |
| /export        | Export data as CSV           |
<!-- | /settings      | Currency, timezone, etc.     | -->
| /help          | Get help info                |

---

## 📁 Project Structure

```
handlers/         # Logic for expense, income, etc.
helpers/          # Reusable helper functions
config.py         # Settings, categories, constants
main.py           # Bot setup and handler registration
.env              # Secret token
requirements.txt  # Python dependencies
```

---

## 📄 License

This project is licensed under the **GNU General Public License v3.0**.  
See the [LICENSE](LICENSE) file for details.

---
