output "state_bucket_arn" {
  description = "ARN of the S3 bucket holding Terraform state"
  value       = aws_s3_bucket.state.arn
}

output "state_bucket_name" {
  description = "Name of the S3 bucket holding Terraform state"
  value       = aws_s3_bucket.state.bucket
}

output "backend_config" {
  description = "Values for the main configuration's S3 backend block"
  value = {
    bucket = aws_s3_bucket.state.bucket
    key    = "expentrax/terraform.tfstate"
    region = var.aws_region
  }
}
