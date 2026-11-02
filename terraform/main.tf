module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${var.project_name}-vpc"
  cidr = var.vpc_cidr
  azs  = var.availability_zones

  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

  enable_nat_gateway = true
  single_nat_gateway = false
  enable_dns_hostnames = true
  enable_dns_support   = true

  public_subnet_tags = {
    "kubernetes.io/role/elb" = "1"
  }
  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = "1"
  }
}

resource "aws_vpc_endpoint" "s3" {
  vpc_id            = module.vpc.vpc_id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = module.vpc.private_route_table_ids
}

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name                   = "${var.project_name}-${var.environment}"
  cluster_version                = var.cluster_version
  cluster_endpoint_public_access = false
  cluster_endpoint_private_access = true
  enable_irsa                   = true
  vpc_id                        = module.vpc.vpc_id
  subnet_ids                    = module.vpc.private_subnets

  eks_managed_node_groups = {
    api = {
      capacity_type  = "ON_DEMAND"
      instance_types = ["t3.medium"]
      min_size       = 2
      max_size       = 6
      desired_size   = 3
    }
    workers = {
      capacity_type  = "SPOT"
      instance_types = ["t3.medium", "t3a.medium"]
      min_size       = 2
      max_size       = 8
      desired_size   = 3
      taints = [{
        key    = "lifecycle"
        value  = "Ec2Spot"
        effect = "NO_SCHEDULE"
      }]
    }
  }
}

resource "aws_s3_bucket" "archive" {
  bucket_prefix = "${var.project_name}-${var.environment}-archives-"
}

resource "aws_s3_bucket_public_access_block" "archive" {
  bucket                  = aws_s3_bucket.archive.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "archive" {
  bucket = aws_s3_bucket.archive.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_versioning" "archive" {
  bucket = aws_s3_bucket.archive.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "archive" {
  bucket = aws_s3_bucket.archive.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "archive" {
  bucket = aws_s3_bucket.archive.id
  rule {
    id     = "archive-log-data"
    status = "Enabled"
    filter {}
    transition {
      days          = 30
      storage_class = "GLACIER"
    }
    transition {
      days          = 180
      storage_class = "DEEP_ARCHIVE"
    }
    noncurrent_version_expiration {
      noncurrent_days = 365
    }
  }
}
