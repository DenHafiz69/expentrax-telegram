data "aws_caller_identity" "current" {}

locals {
  common_tags = {
    ManagedBy = "Terraform"
    Project   = "Expentrax"
    Purpose   = "Terraform remote state"
  }

  state_bucket_name = (
    var.state_bucket_name != ""
    ? var.state_bucket_name
    : "expentrax-tfstate-${data.aws_caller_identity.current.account_id}-${var.aws_region}"
  )
}
