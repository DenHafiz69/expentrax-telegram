# ==============================================================================
# 1. SECRETS MANAGER (TELEGRAM TOKEN AND WEBHOOK SECRET)
# ==============================================================================

resource "aws_secretsmanager_secret" "telegram_token" {
  name                    = "expentrax/telegram_bot_token"
  recovery_window_in_days = 0

  tags = merge(local.common_tags, {
    Name = "expentrax-telegram-bot-token"
  })
}

resource "aws_secretsmanager_secret_version" "telegram_token" {
  secret_id     = aws_secretsmanager_secret.telegram_token.id
  secret_string = var.telegram_bot_token
}

# Telegram only accepts [A-Za-z0-9_-] in the webhook secret token, so keep the
# special characters within that URL-safe subset.
resource "random_password" "webhook_secret" {
  length           = 32
  special          = true
  override_special = "_-"
}

# ==============================================================================
# 2. IAM ROLE AND POLICIES FOR LAMBDA
# ==============================================================================

resource "aws_iam_role" "lambda_exec" {
  name = "expentrax-lambda-exec-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })

  tags = local.common_tags
}

# CloudWatch Logs write access
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_policy" "lambda_secrets" {
  name        = "expentrax-lambda-secrets-policy"
  description = "Allow the Lambda function to read its application secrets"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = [aws_secretsmanager_secret.telegram_token.arn]
    }]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "lambda_secrets" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.lambda_secrets.arn
}

# ==============================================================================
# 3. AWS LAMBDA FUNCTION
# ==============================================================================
#
# The function runs outside a VPC so it can reach Turso and the Telegram API
# over the public internet without a NAT gateway. There is no RDS instance.

resource "aws_lambda_function" "main" {
  function_name    = "expentrax-telegram-bot"
  role             = aws_iam_role.lambda_exec.arn
  runtime          = "python3.13"
  handler          = "main.handler"
  architectures    = ["x86_64"]
  filename         = var.lambda_zip_path
  source_code_hash = filebase64sha256(var.lambda_zip_path)
  timeout          = 30
  memory_size      = 256

  environment {
    variables = {
      DB_URL              = var.db_url
      DB_TOKEN            = var.db_token
      TELEGRAM_SECRET_ARN = aws_secretsmanager_secret.telegram_token.arn
      SECRET_TOKEN        = random_password.webhook_secret.result
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic_execution,
    aws_iam_role_policy_attachment.lambda_secrets,
  ]
}

# ==============================================================================
# 4. API GATEWAY HTTP API (INGRESS AND ROUTING)
# ==============================================================================

resource "aws_apigatewayv2_api" "main" {
  name          = "expentrax-http-api"
  protocol_type = "HTTP"

  tags = local.common_tags
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = "$default"
  auto_deploy = true

  tags = local.common_tags
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.main.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "webhook" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /webhook"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_lambda_permission" "apigw_invoke" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.main.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

# ==============================================================================
# 5. TELEGRAM WEBHOOK REGISTRATION
# ==============================================================================

resource "null_resource" "telegram_webhook" {
  triggers = {
    webhook_url  = aws_apigatewayv2_stage.default.invoke_url
    secret_token = random_password.webhook_secret.result
  }

  provisioner "local-exec" {
    command = "curl -sSf -X POST 'https://api.telegram.org/bot${var.telegram_bot_token}/setWebhook?url=${aws_apigatewayv2_stage.default.invoke_url}webhook&secret_token=${random_password.webhook_secret.result}'"
  }

  depends_on = [
    aws_apigatewayv2_stage.default,
    aws_apigatewayv2_route.webhook,
    aws_lambda_permission.apigw_invoke,
  ]
}
