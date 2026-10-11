variable "aws_region" {
  description = "AWS region that will hold the Terraform state bucket"
  type        = string
  default     = "us-east-1"
}

variable "state_bucket_name" {
  description = "Override for the Terraform state bucket name. Defaults to expentrax-tfstate-<account_id>-<region>."
  type        = string
  default     = ""
}
