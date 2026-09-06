# AWS Lambda Stateless Deployment Guide

This guide details the deployment of **Expentrax Telegram Bot** to **AWS Lambda** with **Amazon RDS PostgreSQL** (or Supabase/External PostgreSQL), fully stateless session persistence, and webhook integration.

---

## 🏛️ Stateless Infrastructure Architecture

```
                                      ┌────────────────────────────────────────────────┐
                                      │                   AWS VPC                      │
                                      │                                                │
[ Telegram Webhook ]                  │   ┌────────────────────────────────────────┐   │
        │                             │   │          Private App Subnet            │   │
        │ HTTPS POST                  │   │                                        │   │
        ▼                             │   │   ┌────────────────────────────────┐   │   │
[ API Gateway / HTTP API ] ───────────────┼──>│ AWS Lambda (main.handler)      │   │   │
  (or Lambda Function URL)            │   │   │  • Initializes Application     │   │   │
                                      │   │   │  • Uses SQLAlchemyPersistence  │   │   │
                                      │   │   └───────────────┬────────────────┘   │   │
                                      │   └───────────────────┼────────────────────┘   │
                                      │                       │                        │
                                      │   ┌───────────────────┼────────────────────┐   │
                                      │   │          Private DB Subnet             │   │
                                      │   │                   ▼                    │   │
                                      │   │   ┌────────────────────────────────┐   │   │
                                      │   │   │ RDS PostgreSQL (expentrax-db)  │   │   │
                                      │   │   │  • Transactions & Budgets      │   │   │
                                      │   │   │  • Bot Conversation States     │   │   │
                                      │   │   │  • Bot User Session Data       │   │   │
                                      │   │   └────────────────────────────────┘   │   │
                                      │   └────────────────────────────────────────┘   │
                                      └────────────────────────────────────────────────┘
```

---

## 🔑 How Stateless Execution Works

In AWS Lambda, instances scale up on demand, recycle, and do not share in-memory state across webhook invocations.

1. **Custom `SQLAlchemyPersistence`**: All multi-step `ConversationHandler` states (e.g. `/transaction`, `/budget`, `/settings`) and active user session data (`context.user_data`) are stored directly in PostgreSQL tables (`bot_persistence_conversations` and `bot_persistence_user_data`).
2. **Instant Reload**: When a user clicks an inline button or sends a message, whichever Lambda container processes the request instantly pulls the latest conversation state and user context from PostgreSQL.
3. **Resilient Connection Pooling**: SQLAlchemy is configured with `pool_pre_ping=True` and `pool_recycle=300` so dropped idle connections across warm Lambda invocations are transparently reconnected.
4. **Webhook Secret Validation**: If `SECRET_TOKEN` is configured, incoming requests are authenticated against the `X-Telegram-Bot-Api-Secret-Token` header.

---

## ⚙️ Environment Variables Reference

Configure these environment variables in your AWS Lambda function settings:

| Variable | Description | Example / Default |
| :--- | :--- | :--- |
| `BOT_TOKEN` | Telegram Bot token from @BotFather *(or use `TELEGRAM_SECRET_ARN`)* | `123456789:ABCdef...` |
| `TELEGRAM_SECRET_ARN` | AWS Secrets Manager ARN storing the Bot Token | `arn:aws:secretsmanager:...` |
| `DATABASE_URL` | Full PostgreSQL connection string *(optional if using DB_HOST)* | `postgresql://user:pass@host:5432/expentrax` |
| `DB_HOST` | RDS PostgreSQL Host endpoint | `expentrax-db.xxxx.us-east-1.rds.amazonaws.com` |
| `DB_PORT` | RDS PostgreSQL Port | `5432` |
| `DB_NAME` | Database name | `expentrax` |
| `DB_USER` | Database username *(optional if using `DB_SECRET_ARN`)* | `expentrax_admin` |
| `DB_PASSWORD` | Database password *(optional if using `DB_SECRET_ARN`)* | `supersecretpassword` |
| `DB_SECRET_ARN` | AWS Secrets Manager ARN containing JSON `{"username": "...", "password": "..."}` | `arn:aws:secretsmanager:...` |
| `SECRET_TOKEN` | Pre-shared webhook secret token configured in Telegram `setWebhook` | `random_uuid_string` |

---

## 📦 Packaging & Deployment

### Option A: Zip Archive Deployment

1. Install dependencies into a build directory:
   ```bash
   mkdir -p build/package
   pip install --platform manylinux2014_x86_64 --target=build/package --implementation cp --python-version 3.13 --only-binary=:all: -r requirements.txt
   ```
2. Copy application source files:
   ```bash
   cp -r handlers utils main.py build/package/
   ```
3. Zip package:
   ```bash
   cd build/package
   zip -r ../bot_package.zip .
   cd ../..
   ```
4. Deploy the zip file to Lambda with handler set to `main.handler`.

### Option B: Docker Container Image Deployment

Build and push the Lambda container image to AWS ECR:

```dockerfile
FROM public.ecr.aws/lambda/python:3.13

COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r requirements.txt

COPY handlers/ ${LAMBDA_TASK_ROOT}/handlers/
COPY utils/ ${LAMBDA_TASK_ROOT}/utils/
COPY main.py ${LAMBDA_TASK_ROOT}/

CMD [ "main.handler" ]
```

Build and push:
```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <YOUR_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com
docker build -t expentrax-bot .
docker tag expentrax-bot:latest <YOUR_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/expentrax-bot:latest
docker push <YOUR_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/expentrax-bot:latest
```

---

## 🔗 Configuring Telegram Webhook

Once your API Gateway or Lambda Function URL is active, register your webhook with Telegram:

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://<your-api-gateway-id>.execute-api.us-east-1.amazonaws.com/webhook",
       "secret_token": "<YOUR_SECRET_TOKEN>",
       "allowed_updates": ["message", "callback_query"]
     }'
```

Verify webhook status:
```bash
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```
