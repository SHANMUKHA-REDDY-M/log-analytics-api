output "cluster_name" {
  value = module.eks.cluster_name
}

output "archive_bucket_name" {
  value = aws_s3_bucket.archive.bucket
}

output "vpc_id" {
  value = module.vpc.vpc_id
}
