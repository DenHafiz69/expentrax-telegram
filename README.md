# Expentrax: Personal Finance Telegram Bot

Expentrax is a personal finance tracker bot for **Telegram**. It allows you to log daily income and expenses, set and monitor category-based monthly budgets, customize categories and currency, and view financial summaries (weekly, monthly, yearly) through interactive Telegram inline menus.

The application is built to run both **locally** (via polling or local webhook) and **serverlessly on AWS Lambda** (stateless architecture with PostgreSQL).

---

## 🏛️ System Architecture & How It Works

```
                                 ┌────────────────────────────────────────────────────────┐
                                 │                   Telegram Platform                    │
                                 └───────────────────────────┬────────────────────────────┘
                                                             │ HTTPS Webhook / Updates
                                                             ▼
                                 ┌────────────────────────────────────────────────────────┐
                                 │           API Gateway / Lambda Function URL            │
                                 └───────────────────────────┬────────────────────────────┘
                                                             │
                                                             ▼
                                 ┌────────────────────────────────────────────────────────┐
                                 │                 main.py (AWS Lambda)                   │
                                 │  • Validates Secret Token                              │
                                 │  • Deserializes Update                                 │
                                 │  • Lazy-initializes Application                        │
                                 └─────────────┬───────────────────────────┬──────────────┘
                                               │                           │
                                               ▼                           ▼
                    ┌──────────────────────────────────┐   ┌──────────────────────────────────┐
                    │    Conversation State Machines   │   │     utils/persistence.py         │
                    │        (./handlers/*.py)         │   │   (SQLAlchemyPersistence)        │
                    │  • /transaction                  │   │  • Loads user_data & conv state  │
                    │  • /budget                       │   │  • Saves state updates back to DB│
                    │  • /history                      │   │  • Makes Lambda 100% stateless   │
                    │  • /settings                     │   └───────────────┬──────────────────┘
                    └──────────────────┬───────────────┘                   │
                                       │                                   │
                                       └─────────────────┬─────────────────┘
                                                         │
                                                         ▼
                                       ┌──────────────────────────────────┐
                                       │        utils/database.py         │
                                       │   (SQLAlchemy 2.0 + Engine Pool) │
                                       │  • pool_pre_ping / pool_recycle  │
                                       │  • RDS PostgreSQL / Local SQLite │
                                       └──────────────────────────────────┘
```

### Core Concepts

1. **Stateless Conversational UX (`handlers/` + `utils/persistence.py`)**:
   - Multi-step flows (`/transaction`, `/budget`, `/settings`) use `telegram.ext.ConversationHandler`.
   - In serverless environments (AWS Lambda), instances are ephemeral and do not share in-memory state.
   - We implemented a custom `SQLAlchemyPersistence` that automatically stores active conversation steps and `context.user_data` (temporary inputs like amount, selected category, etc.) into the database (`bot_persistence_conversations` and `bot_persistence_user_data`).
   - Any Lambda instance can handle any step of a user's multi-step interaction seamlessly.

2. **Non-Blocking Async Database Access (`utils/database.py`)**:
   - Telegram handlers are asynchronous (`async def`).
   - Synchronous SQLAlchemy queries are offloaded using `asyncio.to_thread(...)` to ensure database I/O never blocks the event loop.

3. **Resilient Connection Pooling for Lambda**:
   - Configured with `pool_pre_ping=True` and `pool_recycle=300` so dropped idle connections across warm Lambda invocations are transparently re-established without errors.
   - Supports AWS Secrets Manager, direct PostgreSQL environment variables (`DATABASE_URL` or `DB_HOST`/`DB_USER`/`DB_PASSWORD`), and local SQLite fallback.

---

## 📂 Project Structure

```bash
├── handlers/                    # Command logic & conversation state machines
│   ├── start.py                 # /start command & user registration
│   ├── transaction.py           # /transaction: Log income or expense
│   ├── budget.py                # /budget: Set monthly category budget & check status
│   ├── history.py               # /history: Recent transactions & weekly/monthly/yearly reports
│   └── settings.py              # /settings: Add/delete categories, change currency, reset data
├── utils/                       # Shared utility modules
│   ├── database.py              # SQLAlchemy 2.0 ORM models, connection pool & CRUD queries
│   ├── persistence.py           # SQLAlchemyPersistence provider for stateless PTB operation
│   └── misc.py                  # Currency validation regex & list chunking helper
├── tests/                       # Automated test suite & data seeders
│   ├── test_stateless_lambda.py # Unit tests for persistence and Lambda webhook handling
│   ├── populate_db.py           # Seed script for default categories and sample records
│   └── *.csv                    # Sample seed data
├── terraform/                   # Infrastructure as Code for AWS deployment
│   ├── main.tf                  # VPC, Subnets, RDS PostgreSQL, Secrets Manager, Lambda config
│   ├── variables.tf             # Input variables
│   └── outputs.tf               # Webhook URL, DB endpoint, function name
├── deploy.md                    # Detailed AWS Lambda & RDS deployment guide
├── main.py                      # Application entrypoint (Local Polling/Webhook & Lambda handler)
├── build.sh                     # Builds build/bot_package.zip for Lambda
├── requirements.txt             # Full dependency set (development + runtime)
└── requirements-lambda.txt      # Runtime-only dependencies for the Lambda artifact
```

---

## 🤖 Features & Command Reference

### 1. `/start` ([`handlers/start.py`](file:///home/denhafiz/Coding/expentrax-telegram/handlers/start.py))
- Checks if the user exists in the database; creates a new `User` record if not.
- Sends an introductory menu explaining available commands.

### 2. `/transaction` ([`handlers/transaction.py`](file:///home/denhafiz/Coding/expentrax-telegram/handlers/transaction.py))
- Guides the user through a 4-step logging wizard:
  1. **Type**: Choose `💸 Expense` or `💰 Income` via inline buttons.
  2. **Amount**: Type a number (e.g. `25` or `12.50`, validated via regex).
  3. **Description**: Text description (e.g., "Grocery shopping").
  4. **Category**: Dynamic keyboard displaying default + user's custom categories.
- Saves the transaction to the database with the current timestamp and user's preferred currency symbol.

### 3. `/budget` ([`handlers/budget.py`](file:///home/denhafiz/Coding/expentrax-telegram/handlers/budget.py))
- **Set/Change Budget**: Pick the month (current or next month), choose an expense category, and enter the budgeted target amount.
- **Check Budget**: Calculates total spent vs. budgeted amount per category for the current month and generates a clean summary with visual indicators (`✅` or `❌`).

### 4. `/history` ([`handlers/history.py`](file:///home/denhafiz/Coding/expentrax-telegram/handlers/history.py))
- **Recent (`Recent ✅`)**: Displays the last 3 logged transactions with category, description, and amount.
- **Summary (`Summary 📊`)**: Aggregates total income, total expenses, and net balance over **Weekly**, **Monthly**, or **Yearly** periods.

### 5. `/settings` ([`handlers/settings.py`](file:///home/denhafiz/Coding/expentrax-telegram/handlers/settings.py))
- **Add Category**: Create custom income or expense categories.
- **View Categories**: List all active categories.
- **Delete Categories**: Remove user-created custom categories.
- **Set Currency**: Set personal currency notation (e.g., `RM`, `$`, `€`, `£`, `¥`).
- **Reset Data**: Confirmation dialog to wipe all transactions, custom categories, and budgets for the user.

---

## ⚙️ Environment Variables

Create a `.env` file in the root directory (based on `.env-example`):

```env
# Required for running the bot
BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ

# Optional: Webhook configuration (if not using Polling)
WEBHOOK_URL=https://your-domain-or-ngrok.dev
SECRET_TOKEN=your_secure_random_secret_token

# Optional: Database configuration (defaults to SQLite if omitted)
# DATABASE_URL=postgresql://user:password@localhost:5432/expentrax
# DB_HOST=localhost
# DB_PORT=5432
# DB_NAME=expentrax
# DB_USER=postgres
# DB_PASSWORD=yourpassword
```

---

## 🚀 Local Development

### 1. Setup Virtual Environment
```bash
# Using uv (fastest)
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt

# Or using standard python venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Run Database Migrations / Seed Data (Optional)
```bash
python -c "from utils.database import init_db; init_db()"
# Seed default categories and sample records
python tests/populate_db.py
```

### 3. Start the Bot (Polling Mode)
```bash
python main.py
```

---

## 📊 Local Observability Stack (Docker Compose)

You can run the entire Expentrax stack locally with PostgreSQL, Prometheus, Grafana, and cAdvisor:

```bash
# Start bot, database, and monitoring stack
docker compose up -d
```

### Services & URLs:
- **Telegram Bot Metrics**: `http://localhost:9090/metrics`
- **Prometheus UI**: `http://localhost:9091`
- **Grafana Dashboards**: `http://localhost:3000` (Default credentials: `admin` / `admin`)
- **cAdvisor Container Monitor**: `http://localhost:8080`
- **PostgreSQL Exporter**: `http://localhost:9187/metrics`

Pre-provisioned Grafana dashboards are located under the **Expentrax** folder:
- **Expentrax Bot Overview**: Real-time update rates, handler execution latencies (P50/P95), error counts, income vs expense breakdowns, and process memory/CPU.
- **Container & Host Metrics**: Real-time CPU %, memory working set, and network I/O per container.

---

## 🧪 Running Automated Tests

Run the test suite to verify stateless persistence, conversation transitions, and the Lambda webhook handler:

```bash
python -m unittest tests/test_stateless_lambda.py -v
```

---

## ☁️ Deploying to AWS Lambda

The stack is defined with Terraform and deployed as a zip artifact. From the
repository root:

```bash
./build.sh          # builds build/bot_package.zip (runtime deps + app code)

cd terraform
terraform init
terraform plan      # needs TF_VAR_telegram_bot_token or terraform.tfvars
terraform apply
```

See [`deploy.md`](file:///home/denhafiz/Coding/expentrax-telegram/deploy.md) for full instructions on deploying via AWS Lambda and configuring Telegram Webhooks with Amazon RDS PostgreSQL.
