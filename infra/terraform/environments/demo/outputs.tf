output "aws_account_id" {
  description = "AWS account receiving the ChangeOps resources."
  value       = data.aws_caller_identity.current.account_id
}

output "aws_region" {
  description = "AWS Region selected by ADR-0022."
  value       = var.aws_region
}

output "hosted_zone_id" {
  description = "Public Route 53 hosted zone containing certificate and application records."
  value       = local.hosted_zone_id
}

output "hosted_zone_name_servers" {
  description = "Delegate these name servers at the registrar when Terraform created the hosted zone."
  value       = var.existing_hosted_zone_id == null ? aws_route53_zone.app[0].name_servers : []
}

output "application_url" {
  description = "Public URL only when the declared demo window is enabled."
  value       = var.demo_enabled ? "https://${var.application_hostname}" : null
}

output "application_hostname" {
  description = "Stable public hostname used by ACM, Cognito callbacks, and the demo alias."
  value       = var.application_hostname
}

output "certificate_arn" {
  description = "Validated regional ACM certificate."
  value       = aws_acm_certificate_validation.app.certificate_arn
}

output "vpc_id" {
  description = "ChangeOps VPC."
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "Two public subnets used by the ALB and outbound-only public Fargate task."
  value       = aws_subnet.public[*].id
}

output "database_subnet_ids" {
  description = "Two isolated subnets used only by the private RDS subnet group."
  value       = aws_subnet.database[*].id
}

output "task_security_group_id" {
  description = "Security group used by application, migration, and bootstrap Fargate tasks."
  value       = aws_security_group.task.id
}

output "database_security_group_id" {
  description = "Private RDS security group accepting PostgreSQL only from the task group."
  value       = aws_security_group.database.id
}

output "database_subnet_group_name" {
  description = "Named isolated subnet group required for controlled snapshot restore."
  value       = aws_db_subnet_group.main.name
}

output "api_repository_url" {
  description = "Immutable backend ECR repository URL."
  value       = aws_ecr_repository.api.repository_url
}

output "web_repository_url" {
  description = "Immutable frontend ECR repository URL."
  value       = aws_ecr_repository.web.repository_url
}

output "ecs_cluster_name" {
  description = "Named ECS cluster used by application and one-off tasks."
  value       = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  description = "Named one-task application ECS service."
  value       = aws_ecs_service.app.name
}

output "application_task_definition_arn" {
  description = "Reviewed two-container application task definition."
  value       = aws_ecs_task_definition.application.arn
}

output "migration_task_definition_arn" {
  description = "Separate one-off Alembic task definition."
  value       = aws_ecs_task_definition.migration.arn
}

output "bootstrap_task_definition_arn" {
  description = "Separate one-off fictional-data bootstrap task using only runtime DB authority."
  value       = aws_ecs_task_definition.bootstrap.arn
}

output "database_identifier" {
  description = "Private RDS instance identifier."
  value       = aws_db_instance.main.identifier
}

output "database_endpoint" {
  description = "Non-secret private RDS hostname."
  value       = aws_db_instance.main.address
}

output "database_port" {
  description = "Private PostgreSQL port."
  value       = aws_db_instance.main.port
}

output "database_admin_secret_arn" {
  description = "AWS-managed break-glass RDS master secret; never injected into ECS."
  value       = aws_db_instance.main.master_user_secret[0].secret_arn
}

output "secret_arns" {
  description = "Named empty secret containers whose values are populated outside Terraform."
  value       = local.secret_arns
}

output "cognito_user_pool_id" {
  description = "Closed Cognito user pool."
  value       = aws_cognito_user_pool.app.id
}

output "cognito_user_pool_arn" {
  description = "Closed Cognito user pool ARN used by authenticated ALB listeners."
  value       = aws_cognito_user_pool.app.arn
}

output "cognito_user_pool_client_id" {
  description = "Non-secret Cognito client ID used by ALB and Next.js claim validation."
  value       = aws_cognito_user_pool_client.alb.id
}

output "cognito_user_pool_domain" {
  description = "Cognito managed sign-in prefix used by ALB authentication."
  value       = aws_cognito_user_pool_domain.app.domain
}

output "cognito_reviewer_group" {
  description = "Closed reviewer group name."
  value       = aws_cognito_user_group.reviewer.name
}

output "cognito_admin_group" {
  description = "Closed admin group name."
  value       = aws_cognito_user_group.admin.name
}

output "github_deploy_role_arn" {
  description = "GitHub OIDC role scoped to image push, migration, and ECS deployment."
  value       = aws_iam_role.github_deploy.arn
}

output "github_lifecycle_role_arn" {
  description = "Separate GitHub OIDC role for explicitly approved startup and teardown."
  value       = aws_iam_role.github_lifecycle.arn
}

output "operations_topic_arn" {
  description = "SNS topic for operational alarms."
  value       = aws_sns_topic.operations.arn
}

output "target_group_arn" {
  description = "Retained Next.js target group used when authenticated ingress is enabled."
  value       = aws_lb_target_group.web.arn
}

output "https_listener_arn" {
  description = "HTTPS listener ARN used by the declared demo ingress."
  value       = var.demo_enabled ? aws_lb_listener.https[0].arn : null
}

output "alb_signer_arn" {
  description = "Load balancer ARN expected in the signed x-amzn-oidc-data signer claim."
  value       = var.demo_enabled ? aws_lb.app[0].arn : null
}

output "cloudwatch_dashboard_name" {
  description = "CloudWatch operations dashboard."
  value       = aws_cloudwatch_dashboard.main.dashboard_name
}
