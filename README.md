# Expentrax: Personal Finance Telegram Bot

I built Expentrax, a personal finance management tool, as a Telegram bot to offer a simple, fast, and highly accessible way for me to track my income and expenses. As my final project for CS50, the bot was born from my personal need to overcome the limitations of existing financial tracking methods. It represents a practical solution for anyone seeking a streamlined, no-frills approach to financial awareness, leveraging the convenience of a messaging platform that millions of people, including myself, already use daily. This project also served as a significant learning experience for me, enabling my transition from a background in Physics to a career in software development by building a full-featured application from the ground up.

## The Problem

For two years, I relied on Google Sheets for my personal financial tracking. While functional and accessible across my devices, this method was not without its drawbacks. My exploration of dedicated finance applications revealed a landscape of tools that were often ill-suited for my simple needs. These applications typically fell into three problematic categories. First, many of the most effective apps were platform-specific, available only on either Android or iOS, creating an inconvenient barrier. Second, powerful features in many applications were locked behind recurring subscription fees, making them a costly option for basic expense tracking. Finally, a significant number of apps suffered from feature bloat, overwhelming me with complex functionalities such as investment portfolio management, loan amortization calculators, and advanced financial charting. These superfluous features cluttered the interface and detracted from the core task of simple income and expense logging.

## The Solution

I identified a more elegant solution by looking at the tools I already used. In Malaysia, while WhatsApp is the dominant messaging app, my wife and I prefer Telegram for its robust features, including seamless multi-device synchronization, cloud storage, and a powerful bot API. I realized that my financial tool didn't need to be a standalone application. Instead, it could be integrated into an existing, widely-used platform.

A Telegram bot was the perfect answer. This approach eliminates the need for users to download, install, and manage yet another application on their phones. I can interact with my finance tracker directly within a chat interface I am already familiar with and likely have open throughout the day. For ease of access, I can pin the bot to the top of my chat list, making it instantly available. This design choice prioritizes user convenience and reduces friction, making the habit of tracking finances easier to maintain.

## Core Features: Focus on Simplicity and User Experience

I designed the minimum viable product (MVP) for Expentrax based on my own experience with manual tracking in Google Sheets, focusing on essential, high-impact features.

- **Transaction Logging:** The primary function is handled by the `/transactions` command, which initiates a guided conversation to log either income or an expense. The bot prompts for the amount and category, making the process quick and straightforward.
- **Modern User Interface:** A key design decision was my use of `InlineKeyboardButton` for user interactions, such as selecting a category. This presents clean, clickable buttons directly within the chat message, offering a superior user experience compared to the older `ReplyKeyboardMarkup`, which clutters the user's keyboard and makes the interaction feel clunky.
- **Financial History and Summaries:** With the `/history` command, I can review my recent transactions or request summaries of my financial activity, broken down by week, month, or year. This provides valuable insights into my spending habits over time.
- **User Customization:** The `/settings` command serves as a central hub for personalization. Here, I can add my own custom spending categories, change my preferred currency, or reset my data if I wish to start over.

## Technical Architecture and Design Decisions

I built Expentrax with a modular architecture to ensure a clean separation of concerns, making the codebase readable, maintainable, and scalable.

- **`main.py`**: This is the entry point of the application. It loads the bot token from an environment file, initializes the bot using the `python-telegram-bot` library, registers all the command handlers from the `/handlers` directory, and starts the bot's polling loop to listen for user messages.
- **`./handlers`**: This directory contains the logic for each user-facing command, with each file dedicated to a specific feature (e.g., `transaction.py`, `history.py`, `settings.py`). This separation keeps the main file clean and organized. The `transaction.py` handler is the most complex, utilizing `ConversationHandler` to manage the multi-step process of logging a transaction.
- **`./utils/database.py`**: To keep the handlers focused on user interaction, I abstracted all database logic into this utility file. It uses **SQLAlchemy**, an Object-Relational Mapper (ORM), which allows the application to interact with the database using Python objects instead of raw SQL queries. This improves code readability, security, and maintainability. The database schema includes tables for users, default and custom categories, transactions, budgets, and recurring transactions.
- **Database Choice**: I chose **SQLite** for this project because it is serverless and stores the entire database in a single file, making it incredibly easy for development and deployment in small-to-medium-scale applications. My use of SQLAlchemy means that if the bot's user base grows, the backend can be migrated to a more robust database like PostgreSQL with minimal changes to the application code.
- **Framework**: I chose the `python-telegram-bot` library for its active community support, comprehensive documentation, and powerful features like `ConversationHandler` and `JobQueue`, which are essential for creating a responsive and interactive bot.

## Future Plans

I have a clear roadmap for future improvements that will add more value for users:

- **Visual Reports:** I plan to integrate the `matplotlib` library to generate and send visual reports, such as pie charts illustrating spending by category.
- **Natural Language Parsing:** I intend to implement smarter input parsing so that users can log transactions more naturally (e.g., by typing "15 for lunch") instead of having to use a specific command.
