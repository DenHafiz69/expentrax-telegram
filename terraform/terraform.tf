terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }

  # Remote state is strongly recommended for shared or CI-driven deployments.
  # Uncomment and provide the bucket/table before running `terraform init`.
  #
  # backend "s3" {
  #   bucket         = "your-terraform-state-bucket"
  #   key            = "expentrax/terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "terraform-locks"
  #   encrypt        = true
  # }
}
