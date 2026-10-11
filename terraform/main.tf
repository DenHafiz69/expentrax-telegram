# ==============================================================================
# 1. NETWORKING (VPC, SUBNETS, ROUTING, NAT)
# ==============================================================================

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(local.common_tags, {
    Name = "expentrax-vpc"
  })
}

# Public subnets (NAT gateway and public egress)
resource "aws_subnet" "public_a" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "${var.aws_region}a"
  map_public_ip_on_launch = true

  tags = merge(local.common_tags, {
    Name = "expentrax-public-a"
  })
}

resource "aws_subnet" "public_b" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.2.0/24"
  availability_zone       = "${var.aws_region}b"
  map_public_ip_on_launch = true

  tags = merge(local.common_tags, {
    Name = "expentrax-public-b"
  })
}

# Private subnets (Lambda and RDS PostgreSQL)
resource "aws_subnet" "private_a" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.10.0/24"
  availability_zone = "${var.aws_region}a"

  tags = merge(local.common_tags, {
    Name = "expentrax-private-a"
  })
}

resource "aws_subnet" "private_b" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.11.0/24"
  availability_zone = "${var.aws_region}b"

  tags = merge(local.common_tags, {
    Name = "expentrax-private-b"
  })
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = merge(local.common_tags, {
    Name = "expentrax-igw"
  })
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = merge(local.common_tags, {
    Name = "expentrax-public-rt"
  })
}

resource "aws_route_table_association" "public_a" {
  subnet_id      = aws_subnet.public_a.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "public_b" {
  subnet_id      = aws_subnet.public_b.id
  route_table_id = aws_route_table.public.id
}

# NAT gateway so the private Lambda subnet can reach Telegram and Secrets Manager
resource "aws_eip" "nat" {
  domain = "vpc"

  tags = merge(local.common_tags, {
    Name = "expentrax-nat-eip"
  })

  depends_on = [aws_internet_gateway.main]
}

resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public_a.id

  tags = merge(local.common_tags, {
    Name = "expentrax-nat-gw"
  })

  depends_on = [aws_internet_gateway.main]
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main.id
  }

  tags = merge(local.common_tags, {
    Name = "expentrax-private-rt"
  })
}

resource "aws_route_table_association" "private_a" {
  subnet_id      = aws_subnet.private_a.id
  route_table_id = aws_route_table.private.id
}

resource "aws_route_table_association" "private_b" {
  subnet_id      = aws_subnet.private_b.id
  route_table_id = aws_route_table.private.id
}

# ==============================================================================
# 2. SECURITY GROUPS
# ==============================================================================

resource "aws_security_group" "lambda" {
  name        = "expentrax-lambda-sg"
  description = "Security group for the Lambda bot function"
  vpc_id      = aws_vpc.main.id

  egress {
    description = "Allow all outbound traffic through the NAT gateway"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "expentrax-lambda-sg"
  })
}

resource "aws_security_group" "rds" {
  name        = "expentrax-rds-sg"
  description = "Security group for RDS PostgreSQL"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "PostgreSQL access from Lambda"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda.id]
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "expentrax-rds-sg"
  })
}

# ==============================================================================
# 3. SECRETS MANAGER (TELEGRAM TOKEN, DB PASSWORD, WEBHOOK SECRET)
# ==============================================================================

resource "random_password" "db_password" {
  length           = 16
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# Telegram only accepts [A-Za-z0-9_-] in the webhook secret token, so keep the
# special characters within that URL-safe subset.
resource "random_password" "webhook_secret" {
  length           = 32
  special          = true
  override_special = "_-"
}

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

resource "aws_secretsmanager_secret" "db_credentials" {
  name                    = "expentrax/db_credentials"
  recovery_window_in_days = 0

  tags = merge(local.common_tags, {
    Name = "expentrax-db-credentials"
  })
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    username = "expentrax_admin"
    password = random_password.db_password.result
  })
}

# ==============================================================================
# 4. RDS POSTGRESQL
# ==============================================================================

resource "aws_db_subnet_group" "main" {
  name       = "expentrax-db-subnets"
  subnet_ids = [aws_subnet.private_a.id, aws_subnet.private_b.id]

  tags = merge(local.common_tags, {
    Name = "expentrax-db-subnets"
  })
}

resource "aws_db_instance" "main" {
  identifier                 = "expentrax-db"
  engine                     = "postgres"
  engine_version             = "15"
  auto_minor_version_upgrade = true
  instance_class             = "db.t4g.micro"
  allocated_storage          = 20
  max_allocated_storage      = 20
  storage_type               = "gp3"
  storage_encrypted          = true
  db_name                    = "expentrax"
  username                   = "expentrax_admin"
  password                   = random_password.db_password.result
  db_subnet_group_name       = aws_db_subnet_group.main.name
  vpc_security_group_ids     = [aws_security_group.rds.id]
  publicly_accessible        = false
  skip_final_snapshot        = true

  tags = merge(local.common_tags, {
    Name = "expentrax-db"
  })
}

# ==============================================================================
# 5. IAM ROLES AND POLICIES FOR LAMBDA
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

# VPC/ENI management access
resource "aws_iam_role_policy_attachment" "lambda_vpc_access" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_iam_policy" "lambda_secrets" {
  name        = "expentrax-lambda-secrets-policy"
  description = "Allow the Lambda function to read its application secrets"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["secretsmanager:GetSecretValue"]
      Resource = [
        aws_secretsmanager_secret.telegram_token.arn,
        aws_secretsmanager_secret.db_credentials.arn,
      ]
    }]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "lambda_secrets" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.lambda_secrets.arn
}

# ==============================================================================
# 6. AWS LAMBDA FUNCTION
# ==============================================================================

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

  vpc_config {
    subnet_ids         = [aws_subnet.private_a.id, aws_subnet.private_b.id]
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      DB_HOST             = aws_db_instance.main.address
      DB_PORT             = "5432"
      DB_NAME             = aws_db_instance.main.db_name
      DB_SECRET_ARN       = aws_secretsmanager_secret.db_credentials.arn
      TELEGRAM_SECRET_ARN = aws_secretsmanager_secret.telegram_token.arn
      SECRET_TOKEN        = random_password.webhook_secret.result
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic_execution,
    aws_iam_role_policy_attachment.lambda_vpc_access,
    aws_iam_role_policy_attachment.lambda_secrets,
  ]
}

# ==============================================================================
# 7. API GATEWAY HTTP API (INGRESS AND ROUTING)
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
# 8. TELEGRAM WEBHOOK REGISTRATION
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
