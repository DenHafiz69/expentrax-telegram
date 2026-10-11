output "db_endpoint" {
  description = "RDS PostgreSQL connection endpoint"
  value       = aws_db_instance.main.address
}

output "lambda_function_name" {
  description = "Name of the deployed Lambda function"
  value       = aws_lambda_function.main.function_name
}

output "webhook_url" {
  description = "Webhook URL to register with Telegram"
  value       = "${aws_apigatewayv2_stage.default.invoke_url}webhook"
}
