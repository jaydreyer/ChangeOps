terraform {
  required_version = ">= 1.10.0, < 2.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.33"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Application  = "ChangeOps"
      ManagedBy    = "Terraform"
      Repository   = var.github_repository
      Architecture = "ADR-0022"
    }
  }
}

data "aws_caller_identity" "current" {}
