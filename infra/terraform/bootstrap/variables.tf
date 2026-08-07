variable "aws_region" {
  description = "Region for the Terraform state bucket."
  type        = string
  default     = "us-east-1"

  validation {
    condition     = var.aws_region == "us-east-1"
    error_message = "ADR-0022 fixes the initial deployment Region to us-east-1."
  }
}

variable "github_repository" {
  description = "Repository recorded on the state bucket."
  type        = string
  default     = "jaydreyer/ChangeOps"
}
