# Expentrax - Den Hafiz's Final Project for CS50

### Your personal, fast, and simple finance manager. Track income and expenses instantly right in Telegram.

## The Problem

For the past two years, I have diligently used Google Sheets to track my personal income and expenses. The primary motivation has always been to understand where my money goes and maintain financial awareness. Google Sheets was my tool of choice because it is accessible from both my laptop and my phone, and it syncs data seamlessly across devices.

However, this solution is not perfect. As I explored dedicated finance-tracking applications, I found they generally fell into three categories that didn't fit my needs:

* **Platform-Specific:** Many of the best apps are (Android or iOS only), which is inconvenient.
* **Subscription-Based:** Most powerful apps lock essential features behind a monthly or annual subscription.
* **Bloated:** Many apps are overloaded with complex functionalities like investment tracking, loan management, or advanced charting, which I don't use and which clutter the interface.

## The Solution

In Malaysia, WhatsApp is the dominant platform for communication. However, my wife and I use Telegram as our primary messaging app, and I've come to appreciate its features. I already have Telegram installed, as do millions of other users. It supports multi-device sync, offers cloud storage, and has a powerful bot API.

To solve my tracking problem, I realized a Telegram bot would be the perfect solution. A user doesn't need to install *another* app; they can simply interact with a bot in an app they already have open.

I considered two options: a web app or a Telegram bot. I chose to build a Telegram bot because I wanted users to access the tool just by clicking a chat, rather than remembering or bookmarking a URL. For frequent users, they can simply pin the bot to the top of their chat list for instant access.

## Personal Motivation

I am a Physics graduate who wants to transition into a career as a software developer. This project was the perfect opportunity to self-teach a wide range of practical skills. By building this bot from scratch, I was able to gain hands-on experience with:
* Interacting with third-party APIs (the Telegram Bot API).
* Database design, implementation, and management.
* Asynchronous programming, which is essential for a responsive bot.
* Full-stack bot development, from user-facing commands to the database backend.
* Writing clean, modular, and maintainable code.

## Core Features

Based on my personal use of Google Sheets, I drafted the "must-have" features for a minimum viable product (MVP).

* **Transaction Logging:** A user can send `/transactions` to log either an expense or income. The bot guides them through a simple, clean process, asking for the amount and category.
* **User-Friendly Interface:** Where possible, I use `InlineKeyboardButton` for a more modern and user-friendly experience (e.g., selecting a category). This is a major improvement over the older `ReplyKeyboardMarkup`, which clutters the user's keyboard and requires a lot of messy back-and-forth messaging.
* **History & Summaries:** Users can send `/history` to check their recent transactions or get summaries of their financial activity by week, month, or year.
* **User Settings:** The `/settings` command provides a central hub for users to manage their experience, including adding their own custom spending categories, changing their preferred currency, or resetting their data.

## Technical Architecture

The project is structured in a modular way to ensure separation of concerns, making the code easier to read, debug, and expand.

### `main.py`
As the name suggests, this is the main entry point for the bot. Its primary responsibilities are:
1.  Loading the `BOT_TOKEN` from the `.env` file using `dotenv`.
2.  Initializing the `ApplicationBuilder` from `python-telegram-bot` to build the bot instance.
3.  Registering all the command and message handlers. It imports functions and handlers from the `/handlers` directory and maps them to specific user commands (e.g., mapping the `/start` command to the `start` function in `start.py`).
4.  Starting the bot's asynchronous event loop by calling `application.run_polling()`, which continuously listens for new messages from Telegram.

### `./handlers`
This directory contains all the logic for handling user commands. This separation keeps `main.py` clean and organized. Each file corresponds to a specific feature of the bot.

* **`start.py`**: Handles the very first commands a user interacts with: `/start` and `/help`. It's responsible for sending a welcome message, explaining the bot's purpose, and listing the available commands. This is the user's first impression of the bot.
* **`transaction.py`**: This is the most critical and frequently used handler. It manages the logic for logging income and expenses (e.g., the `/transactions` command). It uses `ConversationHandler` to guide the user through the multi-step process of providing an amount, selecting a category (from default or custom lists), and optionally adding a description.
* **`history.py`**: Contains the logic for the `/history` command. It presents the user with options (e.g., "Recent Transactions," "Monthly Summary," "Yearly Summary") and then fetches the relevant data from the database via `utils/database.py`. Finally, it formats this data into a clear, human-readable message to send back to the user.
* **`settings.py`**: This file powers the `/settings` command. It typically presents an inline keyboard menu with several options, such as "Manage Custom Categories," "Change Currency," or "Reset All Data." It acts as a router, directing the user to other functions based on their selection.
* **`budget.py`**: This file (or a similar one) would contain the logic for managing budgets. It would handle commands like `/set_budget`, `/view_budgets`, and `/delete_budget`. It would interact heavily with the database to store and retrieve budget information and compare it against the user's transactions.
* **`recurring.py`**: This file would handle the logic for recurring transactions (e.g., rent, subscriptions). It would manage commands like `/add_recurring` and `/list_recurring`. It might also integrate with the `python-telegram-bot` `JobQueue` to automatically log these transactions at set intervals (e.g., on the 1st of every month).

### `./utils`
This directory is used to abstract away complex logic, especially database interactions, so the handlers remain clean and focused on user interaction.

* **`database.py`**: This is a critical file that manages all communication with the SQLite database. It uses **SQLAlchemy**, which allows me to interact with the database using Python objects (an Object-Relational Mapper or ORM) instead of writing raw SQL. This makes the code more readable, maintainable, and secure.
    * **Schema:** This file defines the database schema, which includes several tables:
        * `users`: Stores user-specific information, like their Telegram ID and settings (e.g., currency).
        * `default_categories`: A global table of categories (e.g., "Food," "Transport").
        * `custom_categories`: Stores categories created by a specific user, linked by their `user_id`.
        * `transactions`: The main table, storing each transaction with its amount, type (income/expense), and foreign keys linking to the `user_id` and `category_id`.
        * `budget`: Stores budget information, linked to a user and a category.
        * `recurring_transactions`: Stores the data for recurring transactions.

### `requirements.txt`
This file lists all the Python libraries required for the project and their specific versions, ensuring that the project can be reliably installed in any environment. The major dependencies are:
* `python-telegram-bot`: The core framework for building the bot.
* `SQLAlchemy`: The ORM for all database operations.
* `python-dotenv`: For managing environment variables securely.

## Design Decisions

* **Database: SQLite vs. PostgreSQL/MySQL**
    * I chose to use SQLite for now because it is incredibly easy to set up, as it saves the entire database to a single file. It's serverless and perfect for development and small-to-medium applications. My use of SQLAlchemy means the database backend is abstracted. If the user base grows significantly, I can easily migrate to a more robust database like PostgreSQL with minimal code changes.
* **Framework: `python-telegram-bot`**
    * After some research, I found this to be the most actively supported, well-documented, and most-used framework for building Telegram bots with Python. Its robust support for asynchronous programming (`asyncio`) and its rich feature set (like `ConversationHandler` and `JobQueue`) made it the clear choice.
* **Interface: `InlineKeyboardButton` vs. `ReplyKeyboardMarkup`**
    * I initially considered `ReplyKeyboardMarkup` to get user input for categories. However, this method is clunky; it replaces the user's keyboard and requires them to send a separate message. I made a conscious design choice to use `InlineKeyboardButton` instead. This presents clean, clickable buttons *within* the chat message, leading to a much faster and more modern user experience.

## Future Improvements

* **Visual Reports:** I would like to integrate `matplotlib` to generate and send visual reports (like pie charts of spending by category) to the user.
* **Google Sheets Integration:** To bring the project full circle, I want to add a feature for users to export their data or even set up a two-way sync with a Google Sheet, giving them the power of a spreadsheet with the convenience of a bot.
* **Smarter Parsing:** Implement more natural language parsing so a user could just type "15 for lunch" instead of using a specific command.
