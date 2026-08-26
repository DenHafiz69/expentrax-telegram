# Expentrax: Personal Finance Telegram Bot

[![Python Version](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/)
[![Telegram Bot API](https://img.shields.io/badge/Telegram%20Bot%20API-v22.4-blue)](https://core.telegram.org/bots/api)
[![Database](https://img.shields.io/badge/Database-SQLite%20%7C%20PostgreSQL-green)](https://www.postgresql.org/)
[![ORM](https://img.shields.io/badge/ORM-SQLAlchemy%202.0-red)](https://www.sqlalchemy.org/)
[![Deployment](https://img.shields.io/badge/Deployment-Docker%20%2F%20Docker%20Compose-orange)](https://www.docker.com/)

Expentrax is a personal financial tracker built on top of the **Telegram Bot API**. It provides a lightweight, frictionless, and zero-installation approach to managing daily income, expenses, custom categories, budgets, and recurring transactions. 

This project was built from scratch to replace manual tracking methods (such as Google Sheets) and overcome the limitations of proprietary finance tracking apps (which are often platform-restricted, feature-bloated, or paid). Expentrax serves as a capstone portfolio project demonstrating a deep dive into asynchronous programming, database optimization, background scheduling, and containerized deployment in a transition from a Physics background into professional software development.

---

## 🏗️ System Architecture

Expentrax is designed with a modular architecture that cleanly separates routing, business logic, background scheduling, and database access.

```mermaid
graph TD
    User([User in Telegram App]) <-->|HTTPS Update / Webhook| TelegramAPI[Telegram Bot API Gateway]
    TelegramAPI <-->|Webhook / AWS Lambda| AppContainer[Expentrax Application]
    
    subgraph AppContainer [Python Application Layer]
        main[main.py: Entrypoint & Lambda Router] <--> handlers[Handlers: Conversation State Machines]
        handlers <--> database[database.py: SQLAlchemy 2.0 ORM]
        main <--> persistence[persistence.py: Stateless SQLAlchemyPersistence]
        persistence <--> database
    end
    
    database <--> SQLite[(SQLite Database - Local)]
    database <--> Postgres[(PostgreSQL / RDS / Supabase - Production)]
```

- **Client Gateway**: Telegram acts as the user interface, routing messages to our application via HTTPS Webhooks (Production / AWS Lambda) or Polling (Development).
- **Application Core**: `main.py` parses webhook payloads and AWS Lambda events, delegating to state-driven conversational flow systems.
- **Stateless Persistence Layer**: `utils/persistence.py` automatically persists and restores multi-step conversation states and user session data across ephemeral Lambda instances.
- **Feature Handlers**: Each feature is modularized in `./handlers` to isolate code complexity. Large multi-step interactions use `ConversationHandler` backed by database persistence.
- **Data Access Layer**: Database queries are abstracted inside `utils/database.py` utilizing modern SQLAlchemy 2.0 ORM with connection pooling optimized for AWS Lambda.

---

## ⚡ Technical Design Decisions & Lessons Learned

### 1. Conversational UX & State Machines
Instead of forcing users to navigate complex forms or type error-prone command sequences, the logging process relies on a state machine pattern implemented via `ConversationHandler`.
- **Interactive Buttons**: The bot uses `InlineKeyboardButton` and `CallbackQueryHandler` instead of plain text options or rigid keyboard menus. Clickable prompts provide a modern, app-like UI that automatically updates the active message text to eliminate conversation clutter.
- **Dynamic Keyboards**: Keyboard actions dynamically query the database (e.g., custom categories defined by the specific user) in real-time, displaying immediate, contextual options.

### 2. Multi-Threading & Async Event Loop Optimization
One of the key bottlenecks when running an asynchronous bot with a SQL backend is that standard database transactions are synchronous (blocking).
- **The Problem**: If a database query takes 500ms to execute, running it directly on the main event loop blocks all incoming messages for other concurrent users, causing lag.
- **The Solution**: Every database CRUD helper inside our handlers is offloaded using `asyncio.to_thread`. This runs database interactions in a separate worker thread, keeping the async event loop entirely free to handle incoming network packets and webhook requests.

### 3. Indexed User Lookup for Scale
To ensure lookups remain extremely fast as the database size increases:
- Query-level index optimizations (`index=True`) are defined on the `user_id` foreign key columns across the `Transaction`, `Budget`, `RecurringTransaction`, and `CustomCategory` SQLAlchemy tables.
- This creates structured index trees that reduce search complexity from \(O(N)\) table scans to \(O(\log N)\) lookups.

### 4. Database Engine Agnosticism (SQLite & PostgreSQL)
To keep the application developer-friendly yet production-ready, the connection pooling layer adapts to its environment:
- **Local Dev**: Defaults to a single-file, zero-config **SQLite** database.
- **Production**: Seamlessly connects to a high-concurrency **PostgreSQL** instance (e.g., Supabase) by injecting the `DATABASE_URL` environment variable. 
- Thanks to SQLAlchemy, no raw SQL scripts or table structures need modification when shifting between engines.

### 5. Production Webhook Architecture
- **Latency Optimization**: In development, Polling queries Telegram repeatedly. For production deployment, the bot switches to Webhook mode, exposing an internal port via a Tornado-backed HTTP server. 
- **Security Check**: Every incoming webhook payload is validated against a pre-shared `SECRET_TOKEN` to ensure requests originate strictly from Telegram's secure gateway.

---

## 🛠️ Tech Stack & Packages

- **Core Runtime**: Python 3.13
- **Bot Framework**: `python-telegram-bot[webhooks,job-queue]` (v22.4)
- **Database Engine**: SQLAlchemy 2.0 ORM, PostgreSQL (via Supabase driver integration), SQLite
- **Static Typing & Lints**: mypy, black, flake8
- **Process Orchestration**: Docker & Docker Compose
- **Scheduling**: APScheduler (embedded via JobQueue)

---

## ✨ Features Checklist

- [x] **State-Guided Transaction Logging** (`/transaction`): Prompt-driven flow for income/expense details (type, amount, description, category).
- [x] **Dynamic Categories Settings** (`/settings`): Create and delete custom transaction categories instantly.
- [x] **Budgeting Suite** (`/budget`): Set monthly budgets for specific categories and audit progress.
- [x] **Currency Personalization**: Swap currency notations (e.g., RM, USD, EUR) to customize interface outputs.
- [x] **Granular Financial History** (`/history`): Instantly query past logs, grouped and aggregated by week, month, or year.
- [x] **Stateless AWS Lambda & Serverless Readiness**: Database-persisted conversational states and webhook handler ready for AWS Lambda & API Gateway.
- [x] **Dockerized Setup**: Multi-stage Docker integration and environment variable routing.

---

## 📂 Project Structure

```bash
├── data/                    # Local database storage directory (SQLite)
├── handlers/                # Business logic command handlers
│   ├── start.py             # Entrypoint message /start
│   ├── transaction.py       # State machine flow for transactions
│   ├── history.py           # Financial reporting and search commands
│   ├── settings.py          # Dashboard for preferences and custom categories
│   └── budget.py            # Budget limit set and management handlers
├── utils/                   # Shared utility modules
│   ├── database.py          # SQLAlchemy models, initialization and CRUD tasks
│   ├── persistence.py       # Custom SQLAlchemyPersistence for stateless Lambda execution
│   └── misc.py              # Parsing and formatting utilities
├── tests/                   # Automated test suite
│   └── test_stateless_lambda.py # Persistence and Lambda webhook unit tests
├── deploy.md                # AWS Lambda & RDS PostgreSQL deployment guide
├── Dockerfile               # Production multi-stage docker configurations
├── docker-compose.yml       # Production deployment docker configuration
├── main.py                  # Main entrypoint; registers routing tables and AWS Lambda handler
├── requirements.txt         # Project dependencies
└── pyproject.toml           # Build configurations and package manager targets
```

---

## 🚀 Setup & Local Execution

### 1. Clone the Repository
```bash
git clone https://github.com/DenHafiz69/expentrax-telegram.git
cd expentrax-telegram
```

### 2. Configure Virtual Environment (uv / pip)
Using standard `venv`:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Setup Environment Configuration
Create a `.env` file in the root of the workspace:
```env
BOT_TOKEN=your_telegram_bot_token_from_botfather

# Optional (Local defaults to SQLite):
# DATABASE_URL=postgresql://user:password@host:port/dbname
```

### 4. Run Locally (Polling Mode)
```bash
python main.py
```

---

## 🐳 Containerized Deployment (Docker)

To run the containerized application stack locally or on a VPS:

### 1. Setup Docker Environment Variables
Ensure the following variables are present in your production environment or `.env` file:
```env
BOT_TOKEN=your_telegram_bot_token
WEBHOOK_URL=https://your-public-domain.com
SECRET_TOKEN=your_custom_secure_webhook_secret_token
DATABASE_URL=your_postgres_database_url
```

### 2. Launch the Application Stack
```bash
docker-compose up --build -d
```
The application will listen on port `8000`. Set up your reverse proxy (e.g., Nginx, Traefik, Cloudflare Tunnels) to direct traffic from `https://your-public-domain.com` to `localhost:8000`.

---

## 🏆 Key Achievements & Portfolio Highlights
- Built a **non-blocking asynchronous backend** that handles database queries in worker threads to prevent bot lag.
- Achieved **engine flexibility** that swaps storage from offline SQLite to scale-ready PostgreSQL using SQLAlchemy.
- Implemented **state machine conversations** using `ConversationHandler` along with dynamic inline keyboards.
- Integrated an **automated background task scheduler** to process recurring user payments and items.
