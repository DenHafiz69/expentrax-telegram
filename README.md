# Expentrax - Den Hafiz's Final Project for CS50

### Your personal, fast, and simple finance manager. Track income and expenses instantly right in Telegram.

## The Problem

For the past two years, I've relied on Google Sheets to track personal income and expenses, aiming to understand spending patterns and maintain financial awareness. It's accessible on laptop and phone with seamless sync. However, dedicated finance apps often fall short: many are platform-specific (Android/iOS only), subscription-based with locked features, or bloated with unnecessary complexities like investment tracking or advanced charting that clutter the interface and aren't needed for basic tracking.

## The Solution

In Malaysia, WhatsApp dominates communication, but my wife and I prefer Telegram for its features. With Telegram already installed by millions, its multi-device sync, cloud storage, and powerful bot API make it ideal. A Telegram bot eliminates the need for another app; users interact via an existing chat. I chose a bot over a web app for instant access by clicking a chat, allowing pinning for quick use.

## Personal Motivation

As a Physics graduate transitioning to software development, this project offered hands-on learning in practical skills: interacting with third-party APIs (Telegram Bot API), database design and management, asynchronous programming for responsiveness, full-stack bot development, and writing clean, modular code.

## Core Features

Drawing from Google Sheets usage, I identified essential MVP features:

- **Transaction Logging:** Use `/transactions` to log expenses or income. The bot guides through amount and category selection via a simple process.
- **User-Friendly Interface:** Employ `InlineKeyboardButton` for modern, clickable category selection, avoiding cluttered keyboards and messy messaging.
- **History & Summaries:** `/history` provides recent transactions or summaries by week, month, or year.
- **User Settings:** `/settings` centralizes management of custom categories, currency preferences, and data resets.

## Technical Architecture

The project uses modular structure for separation of concerns, enhancing readability, debugging, and expansion.

### `main.py`
This entry point handles:
1. Loading `BOT_TOKEN` from `.env` via `dotenv`.
2. Initializing `ApplicationBuilder` from `python-telegram-bot`.
3. Registering handlers from `/handlers` for commands like `/start`.
4. Starting the event loop with `application.run_polling()` to listen for messages.

### `./handlers`
Contains command logic, keeping `main.py` organized. Each file handles a feature:

- **`start.py`**: Manages `/start` and `/help`, sending welcome messages and command lists.
- **`transaction.py`**: Core handler for `/transactions`, using `ConversationHandler` for multi-step income/expense logging, including amount, category (default/custom), and optional descriptions.
- **`history.py`**: Powers `/history`, offering options like "Recent Transactions" or "Monthly Summary," fetching data from `utils/database.py` and formatting responses.
- **`settings.py`**: Drives `/settings` with inline menus for "Manage Custom Categories," "Change Currency," or "Reset All Data," routing to sub-functions.
- **`budget.py`**: Handles budget commands like `/set_budget`, `/view_budgets`, and `/delete_budget`, storing/retrieving data and comparing against transactions.
- **`recurring.py`**: Manages recurring transactions (e.g., rent), with commands like `/add_recurring` and `/list_recurring`, potentially using `JobQueue` for automatic logging.

### `./utils`
Abstracts complex logic, especially database interactions.

- **`database.py`**: Manages SQLite via SQLAlchemy ORM for readable, secure operations. Schema includes:
  - `users`: Telegram ID and settings (e.g., currency).
  - `default_categories`: Global categories like "Food," "Transport."
  - `custom_categories`: User-specific categories linked by `user_id`.
  - `transactions`: Core table with amount, type (income/expense), and foreign keys to user and category.
  - `budget`: User/category budget data.
  - `recurring_transactions`: Recurring transaction details.

### `requirements.txt`
Lists dependencies: `python-telegram-bot` for bot framework, `SQLAlchemy` for ORM, `python-dotenv` for environment variables.

## Design Decisions

- **Database: SQLite vs. PostgreSQL/MySQL**  
  SQLite's simplicity (single-file, serverless) suits development and small apps. SQLAlchemy abstracts backend, enabling easy migration to PostgreSQL if needed.

- **Framework: `python-telegram-bot`**  
  Chosen for active support, documentation, and features like `ConversationHandler` and `JobQueue`, with strong async support.

- **Interface: `InlineKeyboardButton` vs. `ReplyKeyboardMarkup`**  
  Opted for inline buttons for cleaner, faster UX within chat messages, avoiding keyboard replacement and extra messages.

## Future Improvements

- **Visual Reports:** Integrate `matplotlib` for pie charts of spending by category.
- **Google Sheets Integration:** Enable data export or two-way sync for spreadsheet power with bot convenience.
- **Smarter Parsing:** Add natural language processing for inputs like "15 for lunch" without commands.