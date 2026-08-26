terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = "Expentrax"
      ManagedBy = "Terraform"
    }
  }
}

# ==============================================================================
# VARIABLES
# ==============================================================================

variable "aws_region" {
  type        = string
  default     = "us-east-1"
  description = "AWS deployment region"
}

variable "telegram_bot_token" {
  type        = string
  sensitive   = true
  description = "Telegram Bot Token from BotFather"
}

variable "lambda_zip_path" {
  type        = string
  default     = "build/bot_package.zip"
  description = "Path to the Lambda build artifact zip file"
}

# ==============================================================================
# 1. NETWORKING (VPC, SUBNETS, ROUTING, NAT)
# ==============================================================================

resource "aws_vpc" "expentrax_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = { Name = "expentrax-vpc" }
}

# Public Subnets (For NAT Gateway & Public Egress)
resource "aws_subnet" "public_a" {
  vpc_id                  = aws_vpc.expentrax_vpc.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "${var.aws_region}a"
  map_public_ip_on_launch = true

  tags = { Name = "expentrax-public-a" }
}

resource "aws_subnet" "public_b" {
  vpc_id                  = aws_vpc.expentrax_vpc.id
  cidr_block              = "10.0.2.0/24"
  availability_zone       = "${var.aws_region}b"
  map_public_ip_on_launch = true

  tags = { Name = "expentrax-public-b" }
}

# Private Subnets (For Lambda and RDS PostgreSQL)
resource "aws_subnet" "private_a" {
  vpc_id            = aws_vpc.expentrax_vpc.id
  cidr_block        = "10.0.10.0/24"
  availability_zone = "${var.aws_region}a"

  tags = { Name = "expentrax-private-a" }
}

resource "aws_subnet" "private_b" {
  vpc_id            = aws_vpc.expentrax_vpc.id
  cidr_block        = "10.0.11.0/24"
  availability_zone = "${var.aws_region}b"

  tags = { Name = "expentrax-private-b" }
}

# Internet Gateway (Allows Public Subnet out to Internet)
resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.expentrax_vpc.id
  tags   = { Name = "expentrax-igw" }
}

# Public Route Table
resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.expentrax_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }

  tags = { Name = "expentrax-public-rt" }
}

resource "aws_route_table_association" "pub_a" {
  subnet_id      = aws_subnet.public_a.id
  route_table_id = aws_route_table.public_rt.id
}

resource "aws_route_table_association" "pub_b" {
  subnet_id      = aws_subnet.public_b.id
  route_table_id = aws_route_table.public_rt.id
}

# Elastic IP & NAT Gateway (Allows Lambda in Private Subnet to reach Telegram API)
resource "aws_eip" "nat_eip" {
  domain     = "vpc"
  depends_on = [aws_internet_gateway.igw]
  tags       = { Name = "expentrax-nat-eip" }
}

resource "aws_nat_gateway" "nat_gw" {
  allocation_id = aws_eip.nat_eip.id
  subnet_id     = aws_subnet.public_a.id
  tags          = { Name = "expentrax-nat-gw" }

  depends_on = [aws_internet_gateway.igw]
}

# Private Route Table
resource "aws_route_table" "private_rt" {
  vpc_id = aws_vpc.expentrax_vpc.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.nat_gw.id
  }

  tags = { Name = "expentrax-private-rt" }
}

resource "aws_route_table_association" "priv_a" {
  subnet_id      = aws_subnet.private_a.id
  route_table_id = aws_route_table.private_rt.id
}

resource "aws_route_table_association" "priv_b" {
  subnet_id      = aws_subnet.private_b.id
  route_table_id = aws_route_table.private_rt.id
}

# ==============================================================================
# 2. SECURITY GROUPS
# ==============================================================================

# Lambda Security Group (Can make egress anywhere through NAT)
resource "aws_security_group" "lambda_sg" {
  name        = "expentrax-lambda-sg"
  description = "Security Group for Lambda Bot Function"
  vpc_id      = aws_vpc.expentrax_vpc.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "expentrax-lambda-sg" }
}

# RDS Security Group (Only accepts inbound 5432 from Lambda)
resource "aws_security_group" "rds_sg" {
  name        = "expentrax-rds-sg"
  description = "Security Group for RDS PostgreSQL"
  vpc_id      = aws_vpc.expentrax_vpc.id

  ingress {
    description     = "PostgreSQL access from Lambda"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "expentrax-rds-sg" }
}

# ==============================================================================
# 3. SECRETS MANAGER (TELEGRAM TOKEN & DB PASSWORD)
# ==============================================================================

resource "random_password" "db_password" {
  length           = 16
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

resource "aws_secretsmanager_secret" "telegram_token" {
  name                    = "expentrax/telegram_bot_token"
  recovery_window_in_days = 0 # Immediate deletion on destroy for dev testing
}

resource "aws_secretsmanager_secret_version" "telegram_token_val" {
  secret_id     = aws_secretsmanager_secret.telegram_token.id
  secret_string = var.telegram_bot_token
}

resource "aws_secretsmanager_secret" "db_credentials" {
  name                    = "expentrax/db_credentials"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "db_credentials_val" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    username = "expentrax_admin"
    password = random_password.db_password.result
  })
}

# ==============================================================================
# 4. RDS POSTGRESQL
# ==============================================================================

resource "aws_db_subnet_group" "rds_subnet_group" {
  name       = "expentrax-db-subnets"
  subnet_ids = [aws_subnet.private_a.id, aws_subnet.private_b.id]
}

resource "aws_db_instance" "expentrax_postgres" {
  identifier             = "expentrax-db"
  engine                 = "postgres"
  engine_version         = "15.7"
  instance_class         = "db.t4g.micro"
  allocated_storage      = 20
  max_allocated_storage  = 20
  storage_type           = "gp3"
  db_name                = "expentrax"
  username               = "expentrax_admin"
  password               = random_password.db_password.result
  db_subnet_group_name   = aws_db_subnet_group.rds_subnet_group.name
  vpc_security_group_ids = [aws_security_group.rds_sg.id]
  skip_final_snapshot    = true
  publicly_accessible    = false
}

# ==============================================================================
# 5. IAM ROLES & POLICIES FOR LAMBDA
# ==============================================================================

resource "aws_iam_role" "lambda_exec_role" {
  name = "expentrax-lambda-exec-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

# Attach AWS managed VPC Execution Policy (enables ENI management)
resource "aws_iam_role_policy_attachment" "lambda_vpc_access" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# Policy allowing Lambda to retrieve secrets from Secrets Manager
resource "aws_iam_policy" "lambda_secrets_policy" {
  name = "expentrax-lambda-secrets-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["secretsmanager:GetSecretValue"]
      Resource = [
        aws_secretsmanager_secret.telegram_token.arn,
        aws_secretsmanager_secret.db_credentials.arn
      ]
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_secrets_attach" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = aws_iam_policy.lambda_secrets_policy.arn
}

# ==============================================================================
# 6. AWS LAMBDA FUNCTION
# ==============================================================================

resource "aws_lambda_function" "expentrax_bot" {
  function_name    = "expentrax-telegram-bot"
  role             = aws_iam_role.lambda_exec_role.arn
  runtime          = "python3.11" # Adjust to "nodejs20.x" or other runtime if needed
  handler          = "main.handler"
  filename         = var.lambda_zip_path
  source_code_hash = fileexists(var.lambda_zip_path) ? filebase64sha256(var.lambda_zip_path) : null
  timeout          = 15
  memory_size      = 256

  vpc_config {
    subnet_ids         = [aws_subnet.private_a.id, aws_subnet.private_b.id]
    security_group_ids = [aws_security_group.lambda_sg.id]
  }

  environment {
    variables = {
      DB_HOST             = aws_db_instance.expentrax_postgres.address
      DB_PORT             = "5432"
      DB_NAME             = aws_db_instance.expentrax_postgres.db_name
      TELEGRAM_SECRET_ARN = aws_secretsmanager_secret.telegram_token.arn
      DB_SECRET_ARN       = aws_secretsmanager_secret.db_credentials.arn
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_vpc_access,
    aws_iam_role_policy_attachment.lambda_secrets_attach
  ]
}

# ==============================================================================
# 7. API GATEWAY HTTP API (INGRESS & ROUTING)
# ==============================================================================

resource "aws_apigatewayv2_api" "telegram_api" {
  name          = "expentrax-http-api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_stage" "default_stage" {
  api_id      = aws_apigatewayv2_api.telegram_api.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id                 = aws_apigatewayv2_api.telegram_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.expentrax_bot.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "webhook_route" {
  api_id    = aws_apigatewayv2_api.telegram_api.id
  route_key = "POST /webhook"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

# Permission allowing API Gateway to invoke Lambda
resource "aws_lambda_permission" "apigw_invoke" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.expentrax_bot.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.telegram_api.execution_arn}/*/*"
}

# ==============================================================================
# OUTPUTS
# ==============================================================================

output "webhook_url" {
  description = "The complete Webhook URL to register with Telegram"
  value       = "${aws_apigatewayv2_stage.default_stage.invoke_url}webhook"
}

output "db_endpoint" {
  description = "RDS PostgreSQL connection endpoint"
  value       = aws_db_instance.expentrax_postgres.address
}
