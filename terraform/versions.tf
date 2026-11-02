terraform {
  required_version = ">= 1.6.0"

  backend "s3" {
    encrypt        = true
    key            = "log-analytics/terraform.tfstate"
    dynamodb_table = "log-analytics-terraform-lock"
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
