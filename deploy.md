Switching from DynamoDB to **RDS PostgreSQL** introduces networking components to your infrastructure. Unlike DynamoDB (which sits directly on AWS's public API network and relies on IAM), RDS instances must run inside a **Virtual Private Cloud (VPC)** and require structured relational schemas and secret storage for database credentials.

---

## Updated Infrastructure Architecture

Your Lambda function needs to communicate with a PostgreSQL instance inside a private subnet:

```
[ Telegram Webhook ] ──> [ API Gateway (HTTP) ] ──> [ Lambda (in VPC Subnet) ]
                                                          │
                                         ┌────────────────┴────────────────┐
                                         ▼                                 ▼
                             [ Security Group ]                 [ Secrets Manager ]
                                     │                        (DB Host, User, Pass)
                                     ▼
                        [ RDS PostgreSQL (Private) ]

```

---

## Updated Terraform Blueprint (`rds.tf` & `network.tf`)

### 1. `network.tf` (VPC & Subnets)

* **Purpose:** Defines an isolated networking layer. RDS must sit in private subnets across at least two Availability Zones.
* **Pseudocode Structure:**
```hcl
resource "aws_vpc" "expentrax_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
}

# Two private subnets in different AZs for RDS multi-AZ requirements
resource "aws_subnet" "private_a" { ... }
resource "aws_subnet" "private_b" { ... }

# Subnet group telling RDS where it is allowed to launch instances
resource "aws_db_subnet_group" "rds_subnet_group" {
  name       = "expentrax-db-subnet-group"
  subnet_ids = [aws_subnet.private_a.id, aws_subnet.private_b.id]
}

```



### 2. `security.tf` (Firewall Rules)

* **Purpose:** Controls network access. Lambda must be granted explicit outbound access to talk to RDS on port `5432`.
* **Pseudocode Structure:**
```hcl
# Security group for Lambda
resource "aws_security_group" "lambda_sg" {
  name   = "expentrax-lambda-sg"
  vpc_id = aws_vpc.expentrax_vpc.id
}

# Security group for RDS (Only allows inbound port 5432 from lambda_sg)
resource "aws_security_group" "rds_sg" {
  name   = "expentrax-rds-sg"
  vpc_id = aws_vpc.expentrax_vpc.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda_sg.id]
  }
}

```



### 3. `rds.tf` (PostgreSQL Database)

* **Purpose:** Provisions a low-cost, single-AZ PostgreSQL instance suitable for a small application.
* **Pseudocode Structure:**
```hcl
resource "aws_db_instance" "expentrax_postgres" {
  identifier             = "expentrax-db"
  allocated_storage      = 20
  engine                 = "postgres"
  engine_version         = "15" # Or latest stable version
  instance_class         = "db.t4g.micro" # Cost-effective instance type
  db_name                = "expentrax"
  username               = "expentrax_admin"
  password               = var.db_password # Sourced securely from TF variables or Random Password resource

  db_subnet_group_name   = aws_db_subnet_group.rds_subnet_group.name
  vpc_security_group_ids = [aws_security_group.rds_sg.id]
  skip_final_snapshot    = true # Set false for production data retention
  publicly_accessible    = false
}

```



### 4. Updated `lambda.tf` (VPC Configuration & Secrets)

* **Purpose:** Lambda must now be attached to the VPC to reach PostgreSQL and given database connection details via environment variables.
* **Pseudocode Changes:**
```hcl
resource "aws_lambda_function" "expentrax_bot" {
  # ... previous Lambda configs ...

  # Attach Lambda to your VPC
  vpc_config {
    subnet_ids         = [aws_subnet.private_a.id, aws_subnet.private_b.id]
    security_group_ids = [aws_security_group.lambda_sg.id]
  }

  environment {
    variables = {
      DB_HOST             = aws_db_instance.expentrax_postgres.address
      DB_PORT             = "5432"
      DB_NAME             = aws_db_instance.expentrax_postgres.db_name
      TELEGRAM_SECRET_ARN = aws_secretsmanager_secret.telegram_bot_token.arn
      DB_SECRET_ARN       = aws_secretsmanager_secret.db_credentials.arn
    }
  }
}

# Requires the AWS Managed Policy for Lambda VPC Access attached to execution role:
# AWSLambdaVPCAccessExecutionRole (allows Lambda to create ENIs in the VPC)

```



---

## Database Schema Design (PostgreSQL)

Unlike DynamoDB's single-table or document approach, PostgreSQL uses structured tables connected with foreign keys.

```sql
-- Users table
CREATE TABLE users (
    user_id BIGINT PRIMARY KEY, -- Telegram Chat/User ID
    username VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Categories table
CREATE TABLE categories (
    category_id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);

-- Expenses table
CREATE TABLE expenses (
    expense_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    category_id INT REFERENCES categories(category_id),
    amount NUMERIC(12, 2) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

```

---

## Critical Resume & Interview Considerations

1. **VPC Cold Start Overhead:** When Lambda runs inside a VPC to talk to RDS, AWS creates Elastic Network Interfaces (ENIs). While AWS Hyperplane has largely reduced VPC cold starts, it is still a key architectural point to discuss in interviews.
2. **Connection Pooling:** PostgreSQL has hard connection limits. Lambdas scale up instantly by opening new instances, which can easily exhaust database connections. In production, an **RDS Proxy** (`aws_db_proxy`) sits between Lambda and RDS to pool connections efficiently.
3. **Cost Factor:** DynamoDB has a generous perpetual free tier for small projects ($0/month idle). RDS instances (e.g., `db.t4g.micro`) run 24/7 and cost around **$12–$15/month** after the 12-month AWS Free Tier expires.

---

## Official Documentation References

* [Terraform `aws_db_instance` Resource Documentation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/db_instance)
* [Terraform `aws_vpc` Resource Documentation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc)
* [AWS Documentation: Configuring a Lambda Function to Access Resources in a VPC](https://docs.aws.amazon.com/lambda/latest/dg/configuration-vpc.html)
