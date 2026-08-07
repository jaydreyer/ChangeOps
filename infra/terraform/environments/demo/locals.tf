locals {
  name_prefix = "changeops-${var.environment}"

  common_tags = {
    Application  = "ChangeOps"
    Environment  = var.environment
    ManagedBy    = "Terraform"
    Repository   = var.github_repository
    Architecture = "ADR-0022"
  }

  public_subnet_cidrs   = [cidrsubnet(var.vpc_cidr, 8, 0), cidrsubnet(var.vpc_cidr, 8, 1)]
  database_subnet_cidrs = [cidrsubnet(var.vpc_cidr, 8, 10), cidrsubnet(var.vpc_cidr, 8, 11)]
  vpc_dns_resolver_cidr = "${cidrhost(var.vpc_cidr, 2)}/32"

  hosted_zone_id = var.existing_hosted_zone_id != null ? var.existing_hosted_zone_id : aws_route53_zone.app[0].zone_id

  github_oidc_subject = "repo:${var.github_repository}:environment:${var.github_environment}"

  ecs_cluster_name    = "${local.name_prefix}-cluster"
  ecs_service_name    = "${local.name_prefix}-service"
  ecs_service_arn     = "arn:${data.aws_partition.current.partition}:ecs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:service/${local.ecs_cluster_name}/${local.ecs_service_name}"
  application_family  = "${local.name_prefix}-application"
  migration_family    = "${local.name_prefix}-migration"
  database_identifier = "${local.name_prefix}-postgres"

  secret_arns = {
    runtime_db     = aws_secretsmanager_secret.runtime_db.arn
    migration_db   = aws_secretsmanager_secret.migration_db.arn
    model_provider = aws_secretsmanager_secret.model_provider.arn
    jira           = aws_secretsmanager_secret.jira.arn
    confluence     = aws_secretsmanager_secret.confluence.arn
  }
}
