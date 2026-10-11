variable "aws_region" {
  description = "AWS region to deploy the Expentrax stack into"
  type        = string
  default     = "us-east-1"
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
