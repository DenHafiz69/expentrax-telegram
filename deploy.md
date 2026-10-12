# Deploying Expentrax to AWS Lambda

This guide walks through deploying the Expentrax Telegram bot to AWS Lambda with
the Terraform configuration in [`terraform/`](terraform/). The stack provisions
an IAM role, Secrets Manager, the Lambda function, an API Gateway HTTP API, and
registers the Telegram webhook.

The database is [Turso](https://turso.tech) (libSQL). There is **no VPC, NAT
gateway, or RDS instance** — the function runs outside a VPC and reaches Turso
and the Telegram API directly over HTTPS.

## Prerequisites

- [Terraform](https://developer.hashicorp.com/terraform/install) `>= 1.10.0`
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
  configured with credentials that can manage IAM, Lambda, API Gateway, and
  Secrets Manager
- Python 3.13 and `pip` (for building the artifact)
- `zip`
- a Telegram bot token from [@BotFather](https://t.me/BotFather)
- a Turso database URL and auth token (`turso db show <db> --url` and
  `turso db tokens create <db>`)

## 0. Bootstrap the remote state backend (one-time)

State is stored in S3 with S3-native locking (`use_lockfile = true`); **no
DynamoDB table is required**. Create the bucket once with the self-contained
bootstrap configuration:

```bash
cd terraform/bootstrap
terraform init
terraform apply
```

This provisions a versioned, encrypted, private bucket named
`expentrax-tfstate-<account_id>-<region>` and prints the `backend_config`
values. Those are already wired into the `backend "s3"` block in
`terraform/terraform.tf` for account `259924044633` / `us-east-1`. If you deploy
to a different account or region, update `bucket`/`region` there to match the
bootstrap output, then re-run `terraform init -reconfigure`.

Terraform stores state at `expentrax/terraform.tfstate` in that bucket and locks
concurrent runs by writing a `.tflock` object alongside it. The bootstrap is only
needed until the bucket exists; if you already have a versioned, private S3
bucket, skip this step and point the backend `bucket` at it instead.

## 1. Build the Lambda artifact

The Lambda deployment package is not checked in. Build it for the Linux x86_64
runtime that Lambda uses:

```bash
./build.sh
```

This installs only `requirements-lambda.txt` into `build/package/`, adds the
application code (`main.py`, `handlers/`, `utils/`) to the archive root, and
writes `build/bot_package.zip`. The script prints the final size; keep it below
50 MB to use Terraform's direct `filename` upload.

> The build targets Python 3.13 (`cp313`, `manylinux2014_x86_64`). If you change
> the `runtime` in `terraform/main.tf`, rebuild with a matching version, e.g.
> `PYTHON_VERSION=3.12 ./build.sh`.

## 2. Provide credentials

Create `terraform/terraform.tfvars` (git-ignored):

```hcl
telegram_bot_token = "123456789:REPLACE_WITH_BOTFATHER_TOKEN"
db_url             = "libsql://your-database-your-org.turso.io"
db_token           = "REPLACE_WITH_TURSO_AUTH_TOKEN"
```

or export them for the session:

```bash
export TF_VAR_telegram_bot_token="123456789:REPLACE_WITH_BOTFATHER_TOKEN"
export TF_VAR_db_url="libsql://your-database-your-org.turso.io"
export TF_VAR_db_token="REPLACE_WITH_TURSO_AUTH_TOKEN"
```

See [`terraform/terraform.tfvars.example`](terraform/terraform.tfvars.example)
for all options. `telegram_bot_token` and `db_token` are marked sensitive.

> `db_token` is injected into the Lambda as a plain environment variable, so it
> is visible to anyone who can read the function configuration. If that is a
> concern, move it into Secrets Manager and read it at runtime.

## 3. Deploy

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

Terraform creates everything and, as a final step, calls Telegram's `setWebhook`
with the generated API Gateway URL and a random `secret_token`. The database
schema is created and seeded automatically on the first request.

## 4. Verify

```bash
terraform output webhook_url
curl -s "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getWebhookInfo"
```

The `getWebhookInfo` response should show the `url` from `terraform output` and
an empty `last_error_message`. Then send `/start` to your bot.

## 5. Logs

Lambda logs are written to CloudWatch Logs (the basic execution role is
attached). Tail them with:

```bash
aws logs tail "/aws/lambda/expentrax-telegram-bot" --follow
```

## 6. Teardown

```bash
cd terraform
terraform destroy
```

This removes the Lambda function, API Gateway, and IAM role. The Telegram token
secret is configured with `recovery_window_in_days = 0` so it is removed
immediately. The Turso database is external and is **not** affected.

## Configuration reference

| Variable | Default | Description |
| --- | --- | --- |
| `aws_region` | `us-east-1` | Deployment region |
| `db_url` | *(required)* | Turso/libSQL URL (`libsql://…`) |
| `db_token` | *(required)* | Turso auth token (sensitive) |
| `lambda_zip_path` | `../build/bot_package.zip` | Path to the built artifact |
| `telegram_bot_token` | *(required)* | BotFather token (sensitive) |

## Cost

Without NAT gateway or RDS, the recurring AWS cost is limited to Lambda
invocations, API Gateway requests, CloudWatch Logs, and one Secrets Manager
secret — typically a few cents per month at personal-bot traffic. Turso has a
free tier.

## Troubleshooting

- **`no such file or directory: ../build/bot_package.zip`** — run `./build.sh`
  from the repository root before `terraform plan`.
- **Artifact is 50 MB or larger** — Lambda's direct zip upload is capped at
  50 MB. Upload the zip to S3 and switch `aws_lambda_function.main` from
  `filename` to `s3_bucket` + `s3_key`.
- **`ModuleNotFoundError` / native import errors after deploy** — the artifact
  was built for a different Python version than the Lambda `runtime`. Rebuild
  with the matching `PYTHON_VERSION`.
- **Database errors in the logs** — check that `DB_URL` and `DB_TOKEN` are valid
  and that the token has not expired (`turso db tokens create <db>`).
- **`403 Forbidden` in the Lambda logs** — the webhook `secret_token` stored in
  Telegram does not match the `SECRET_TOKEN` environment variable. Re-run
  `terraform apply` so the webhook is re-registered.
