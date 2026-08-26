# AWS Lambda & RDS PostgreSQL Deployment Guide

This guide walks you through deploying **Expentrax Telegram Bot** using the Terraform configuration located in [`terraform/main.tf`](file:///home/denhafiz/Coding/expentrax-telegram/terraform/main.tf).

---

## 🏛️ Infrastructure Architecture Overview

The Terraform template provisions a secure, stateless AWS architecture:

```
[ Telegram App / User ]
         │
         │ HTTPS Webhook Update
         ▼
[ API Gateway HTTP API ($default) ]
         │
         │ POST /webhook (Payload Format 2.0)
         ▼
[ AWS Lambda (main.handler) ]  <── [ AWS Secrets Manager ]
  • Attached to Private VPC Subnets  • expentrax/telegram_bot_token
  • 256 MB / 15s Timeout             • expentrax/db_credentials
  • Stateless SQLAlchemyPersistence
         │
         ├─── Egress via NAT Gateway ───> [ Telegram Bot API (api.telegram.org) ]
         │
         └─── Port 5432 (Internal) ─────> [ RDS PostgreSQL (expentrax-db) ]
                                            • db.t4g.micro (gp3 20GB)
                                            • Isolated in Private DB Subnet
```

### Components Provisioned by `terraform/main.tf`
1. **VPC & Subnets**:
   - `10.0.0.0/16` VPC across 2 Availability Zones (`us-east-1a`, `us-east-1b`).
   - **2 Public Subnets** (`10.0.1.0/24`, `10.0.2.0/24`) hosting the Internet Gateway and NAT Gateway.
   - **2 Private Subnets** (`10.0.10.0/24`, `10.0.11.0/24`) hosting the Lambda function ENIs and RDS PostgreSQL instance.
2. **NAT Gateway & EIP**:
   - Allows Lambda in the private subnets to make outbound HTTPS calls to `api.telegram.org` to send replies.
3. **Security Groups**:
   - `expentrax-lambda-sg`: Full outbound egress (via NAT Gateway and to RDS).
   - `expentrax-rds-sg`: Inbound TCP port `5432` strictly restricted to `expentrax-lambda-sg`.
4. **Secrets Manager & Random Password**:
   - Automatically generates a 16-character secure database password.
   - Stores Telegram Bot Token in `expentrax/telegram_bot_token`.
   - Stores DB credentials in `expentrax/db_credentials`.
5. **Amazon RDS PostgreSQL**:
   - PostgreSQL 15.7 (`db.t4g.micro`, 20GB gp3 storage) in a multi-AZ private DB subnet group.
6. **AWS Lambda**:
   - `expentrax-telegram-bot` (`main.handler`, 256MB memory, 15s timeout).
   - Attached to private subnets with IAM permissions for VPC access (`AWSLambdaVPCAccessExecutionRole`) and Secrets Manager read permissions.
   - Injected with environment variables: `DB_HOST`, `DB_PORT`, `DB_NAME`, `TELEGRAM_SECRET_ARN`, `DB_SECRET_ARN`.
7. **API Gateway (HTTP API v2)**:
   - Route `POST /webhook` forwarding requests to the Lambda function.
8. **Automated Webhook Registration**:
   - Terraform automatically executes `null_resource.set_telegram_webhook` to register the generated API Gateway URL with Telegram via `curl`.

---

## 📋 Prerequisites

1. **AWS CLI** installed and configured (`aws configure` with Administrator / deployment credentials).
2. **Terraform** (>= 1.5.0).
3. **Python 3.11 / 3.13** and `pip` (or `uv`) for bundling the Lambda package.
4. **Telegram Bot Token** obtained from [@BotFather](https://t.me/BotFather).

---

## 🚀 Step-by-Step Deployment

### Step 1: Package the Lambda Function

Lambda requires application source files and all runtime dependencies zipped together.

From the workspace root directory:

```bash
# 1. Clean previous build artifacts
rm -rf build package
mkdir -p build/package

# 2. Install dependencies targeting Linux x86_64
pip install \
  --platform manylinux2014_x86_64 \
  --target=build/package \
  --implementation cp \
  --python-version 3.11 \
  --only-binary=:all: \
  -r requirements.txt

# 3. Copy handlers, utils, and main.py into the package directory
cp -r handlers utils main.py build/package/

# 4. Create the build zip archive
cd build/package
zip -r ../bot_package.zip .
cd ../..
```

This creates `build/bot_package.zip`, which is the default artifact path expected by [`terraform/main.tf`](file:///home/denhafiz/Coding/expentrax-telegram/terraform/main.tf#L47-L51).

---

### Step 2: Initialize and Apply Terraform

Navigate to the `terraform/` directory:

```bash
cd terraform
```

#### 1. Initialize Terraform
```bash
terraform init
```

#### 2. Create `terraform.tfvars` (or pass via CLI)
Create `terraform/terraform.tfvars`:
```hcl
aws_region         = "us-east-1"
telegram_bot_token = "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ"
lambda_zip_path    = "../build/bot_package.zip"
```

#### 3. Preview Plan
```bash
terraform plan
```

#### 4. Apply Infrastructure
```bash
terraform apply
```
Type `yes` when prompted. 

Terraform will:
1. Create the VPC, subnets, routing tables, and NAT Gateway.
2. Generate the RDS PostgreSQL database and store secrets in Secrets Manager.
3. Deploy the Lambda function with VPC ENI bindings.
4. Set up the API Gateway HTTP API.
5. Automatically invoke `setWebhook` to connect Telegram to your newly deployed API Gateway endpoint.

---

### Step 3: Verify Webhook & Status

Once deployment completes, check the outputs from Terraform:

```bash
terraform output webhook_url
terraform output db_endpoint
```

Check the Telegram webhook status:

```bash
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

You should see:
```json
{
  "ok": true,
  "result": {
    "url": "https://<api-id>.execute-api.us-east-1.amazonaws.com/webhook",
    "has_custom_certificate": false,
    "pending_update_count": 0
  }
}
```

Open your Telegram app, send `/start` or `/transaction` to your bot, and verify that responses are processed.

---

## 🔍 Monitoring & Logs

To inspect execution logs and diagnose any issues:

```bash
# Stream real-time logs from CloudWatch
aws logs tail "/aws/lambda/expentrax-telegram-bot" --follow
```

---

## 🔄 Updating Code After Changes

When you make changes to handlers, database queries, or `main.py`:

```bash
# 1. Rebuild the zip package
rm -f build/bot_package.zip
cd build/package
cp -r ../../handlers ../../utils ../../main.py .
zip -r ../bot_package.zip .
cd ../..

# 2. Deploy updated code via Terraform (or AWS CLI)
cd terraform
terraform apply -target=aws_lambda_function.expentrax_bot
```

Or instantly via AWS CLI without re-running Terraform:
```bash
aws lambda update-function-code \
  --function-name expentrax-telegram-bot \
  --zip-file fileb://build/bot_package.zip
```

---

## 🧹 Teardown / Destroy Infrastructure

To delete all AWS resources when no longer needed:

```bash
cd terraform
terraform destroy
```
Type `yes` when prompted.
