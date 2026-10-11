terraform {
  # S3-native state locking (use_lockfile) requires Terraform >= 1.10.
  required_version = ">= 1.10.0"

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

  # Remote state with S3-native locking. No DynamoDB table is required:
  # `use_lockfile = true` stores the lock as an object in the same bucket.
  #
  # The bucket is created by the bootstrap configuration in ./bootstrap.
  # If you deploy to a different account or region, re-run the bootstrap and
  # update `bucket`/`region` below to match its `backend_config` output.
  backend "s3" {
    bucket       = "expentrax-tfstate-259924044633-us-east-1"
    key          = "expentrax/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}
