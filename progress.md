Project: ExpenTrax - Telegram Expense Tracker Bot
Version: 1.0
Last Updated: 2025-08-18

This document tracks the development progress of the ExpenTrax bot.

---

### ✅ Completed Features

The core functionality of the bot is in place.

- **Core Bot Infrastructure**:
  - [x] Bot initialization and startup (`main.py`).
  - [x] Database setup and table creation (`database.py`).
  - [x] Configuration management for bot token (`config.py`).

- **Transaction Management**:
  - [x] Add new income (`/add_income`).
  - [x] Add new expenses (`/add_expense`).
  - [x] View a list of recent expenses (`/view_expenses`).

- **Data Summaries**:
  - [x] Full conversation flow for generating summaries (`/summary`).
  - [x] Yearly, Monthly, and Weekly summary period options.
  - [x] Database logic to fetch and filter data for all summary types.

<!-- - **Testing**:
  - [x] Basic unit tests for `save_transaction` and `get_recent_expenses`. -->

---

### 🚧 To-Do & In-Progress Features

These features are planned (as seen in `README.md` or `start_handler.py`) but not yet implemented.
- **New Commands**:
  - [x] `/budget`: Handler for setting and viewing monthly budgets.
  - [x] `/search`: Handler for finding specific transactions.
  - [x] `/export`: Handler to export user data to a CSV file.
  - [x] `/help`: A dedicated help command handler.

<!-- - **Testing**:
  - [ ] Write unit tests for summary functions (`get_summary_periods`, `get_summary_data`).
  - [ ] Write unit tests for the conversation handlers to simulate user interaction. -->

---