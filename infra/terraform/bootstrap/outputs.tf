output "state_bucket_name" {
  description = "Bucket passed to the demo root's partial S3 backend configuration."
  value       = aws_s3_bucket.terraform_state.id
}
