variable "aws_region" {
  description = "AWS region to deploy the Expentrax stack into"
  type        = string
  default     = "us-east-1"
}

variable "db_token" {
  description = "Turso database authentication token (passed to the Lambda as DB_TOKEN)"
  type        = string
  sensitive   = true
}

variable "db_url" {
  description = "Turso database URL, e.g. libsql://<database>-<org>.turso.io (passed to the Lambda as DB_URL)"
  type        = string
}

variable "lambda_zip_path" {
  description = "Path to the Lambda deployment artifact, relative to the terraform directory. Build it with ../build.sh."
  type        = string
  default     = "../build/bot_package.zip"
}

variable "telegram_bot_token" {
  description = "Telegram Bot Token issued by BotFather"
  type        = string
  sensitive   = true
}
