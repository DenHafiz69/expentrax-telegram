# Deploying Expentrax to AWS Lambda

This guide walks through deploying the Expentrax Telegram bot to AWS Lambda with
the Terraform configuration in [`terraform/`](terraform/). The stack provisions a
VPC, RDS PostgreSQL, Secrets Manager, IAM, the Lambda function, an API Gateway
HTTP API, and registers the Telegram webhook.

## Prerequisites

- [Terraform](https://developer.hashicorp.com/terraform/install) `>= 1.5.0`
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
  configured with credentials that can manage VPC, RDS, IAM, Lambda, API Gateway,
  and Secrets Manager
- Python 3.13 and `pip` (for building the artifact)
- `zip`
- a Telegram bot token from [@BotFather](https://t.me/BotFather)

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

## 2. Provide the bot token

The token is a sensitive Terraform variable and is never committed. Create
`terraform/terraform.tfvars` (git-ignored):

```hcl
telegram_bot_token = "123456789:REPLACE_WITH_BOTFATHER_TOKEN"
```

or export it for the session:

```bash
export TF_VAR_telegram_bot_token="123456789:REPLACE_WITH_BOTFATHER_TOKEN"
```

See [`terraform/terraform.tfvars.example`](terraform/terraform.tfvars.example)
for all options.

## 3. Deploy

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

Terraform creates everything and, as a final step, calls Telegram's `setWebhook`
with the generated API Gateway URL and a random `secret_token`.

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

This deletes the RDS instance and its data. Secrets are configured with
`recovery_window_in_days = 0` so they are removed immediately.

## Configuration reference

| Variable | Default | Description |
| --- | --- | --- |
| `aws_region` | `us-east-1` | Deployment region |
| `telegram_bot_token` | *(required)* | BotFather token (sensitive) |
| `lambda_zip_path` | `../build/bot_package.zip` | Path to the built artifact |

## Remote state (recommended for teams/CI)

State is local by default. To share it, uncomment the `backend "s3"` block in
`terraform/terraform.tf`, create the bucket and a DynamoDB lock table, then run
`terraform init -migrate-state`.

## Troubleshooting

- **`no such file or directory: ../build/bot_package.zip`** — run `./build.sh`
  from the repository root before `terraform plan`.
- **Artifact is 50 MB or larger** — Lambda's direct zip upload is capped at
  50 MB. Upload the zip to S3 and switch `aws_lambda_function.main` from
  `filename` to `s3_bucket` + `s3_key`.
- **`ModuleNotFoundError` / native import errors after deploy** — the artifact
  was built for a different Python version than the Lambda `runtime`. Rebuild
  with the matching `PYTHON_VERSION`.
- **`403 Forbidden` in the Lambda logs** — the webhook `secret_token` stored in
  Telegram does not match the `SECRET_TOKEN` environment variable. Re-run
  `terraform apply` so the webhook is re-registered.
- **Lambda timeouts reaching the internet** — confirm the NAT gateway and
  private route table were created; the Lambda runs in private subnets.
