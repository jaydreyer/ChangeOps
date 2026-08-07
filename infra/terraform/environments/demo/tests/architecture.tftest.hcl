mock_provider "aws" {
  mock_data "aws_iam_policy_document" {
    defaults = {
      json = "{\"Version\":\"2012-10-17\",\"Statement\":[]}"
    }
  }

  mock_data "aws_caller_identity" {
    defaults = {
      account_id = "123456789012"
      arn        = "arn:aws:iam::123456789012:user/terraform-test"
      user_id    = "terraform-test"
    }
  }

  mock_data "aws_partition" {
    defaults = {
      partition  = "aws"
      dns_suffix = "amazonaws.com"
    }
  }

  mock_data "aws_region" {
    defaults = {
      name = "us-east-1"
    }
  }

  mock_data "aws_availability_zones" {
    defaults = {
      names = ["us-east-1a", "us-east-1b"]
    }
  }

}

override_resource {
  target = aws_acm_certificate.app
  values = {
    arn = "arn:aws:acm:us-east-1:123456789012:certificate/00000000-0000-0000-0000-000000000000"
    domain_validation_options = [{
      domain_name           = "changeops.example.com"
      resource_record_name  = "_validation.changeops.example.com"
      resource_record_type  = "CNAME"
      resource_record_value = "_validation.acm-validations.aws"
    }]
  }
}

override_resource {
  target          = aws_secretsmanager_secret.runtime_db
  override_during = plan
  values = {
    arn = "arn:aws:secretsmanager:us-east-1:123456789012:secret:runtime-db"
  }
}

override_resource {
  target          = aws_secretsmanager_secret.migration_db
  override_during = plan
  values = {
    arn = "arn:aws:secretsmanager:us-east-1:123456789012:secret:migration-db"
  }
}

override_resource {
  target          = aws_secretsmanager_secret.model_provider
  override_during = plan
  values = {
    arn = "arn:aws:secretsmanager:us-east-1:123456789012:secret:model-provider"
  }
}

override_resource {
  target          = aws_lb.app
  override_during = plan
  values = {
    arn = "arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/changeops-demo-alb/0000000000000000"
  }
}

variables {
  hosted_zone_name                       = "example.com"
  application_hostname                   = "changeops.example.com"
  alert_email                            = "operator@example.com"
  infrastructure_prerequisites_confirmed = true
}

run "adr_0022_off_state" {
  command = plan

  assert {
    condition     = aws_ecs_service.app.desired_count == 0
    error_message = "The normal off state must run zero ECS tasks."
  }

  assert {
    condition     = length(aws_lb.app) == 0
    error_message = "The normal off state must not retain the billable ALB."
  }

  assert {
    condition     = length(aws_route53_record.app_ipv4) == 0
    error_message = "The normal off state must not publish the application alias."
  }

  assert {
    condition     = aws_db_instance.main.publicly_accessible == false
    error_message = "RDS must never be publicly accessible."
  }

  assert {
    condition     = aws_db_instance.main.multi_az == false && aws_db_instance.main.instance_class == "db.t4g.micro"
    error_message = "The database must retain the ADR's low-cost Single-AZ baseline."
  }

  assert {
    condition     = aws_db_instance.main.deletion_protection == true
    error_message = "RDS deletion protection must be enabled by default."
  }

  assert {
    condition     = aws_ecs_task_definition.application.cpu == "1024" && aws_ecs_task_definition.application.memory == "2048"
    error_message = "The application task must retain the approved 1 vCPU / 2 GiB size."
  }

  assert {
    condition = alltrue([
      for secret in local.api_secrets :
      !strcontains(secret.valueFrom, aws_secretsmanager_secret.migration_db.arn)
    ])
    error_message = "The long-running application must never receive the migration credential."
  }

  assert {
    condition = alltrue([
      for secret in local.migration_secrets :
      strcontains(secret.valueFrom, aws_secretsmanager_secret.migration_db.arn)
    ])
    error_message = "The migration task must receive only the migration database secret."
  }

  assert {
    condition = length(local.bootstrap_secrets) == 2 && alltrue([
      for secret in local.bootstrap_secrets :
      strcontains(secret.valueFrom, aws_secretsmanager_secret.runtime_db.arn)
    ])
    error_message = "The fictional bootstrap must use only restricted runtime DB authority."
  }
}

run "declared_demo_window" {
  command = plan

  variables {
    demo_enabled = true
  }

  assert {
    condition     = aws_ecs_service.app.desired_count == 1
    error_message = "A declared demo window must run exactly one ECS task."
  }

  assert {
    condition     = length(aws_lb.app) == 1
    error_message = "A declared demo window must create exactly one public ALB."
  }

  assert {
    condition     = length(aws_route53_record.app_ipv4) == 1
    error_message = "A declared demo window must publish the application alias."
  }

  assert {
    condition     = aws_lb.app[0].idle_timeout == 180
    error_message = "The ALB idle timeout must exceed the bounded 120-second model timeout."
  }

  assert {
    condition = one([
      for item in local.web_environment :
      item.value if item.name == "ALB_EXPECTED_SIGNER_ARN"
    ]) == aws_lb.app[0].arn
    error_message = "Next.js must verify the signed OIDC signer against the load balancer ARN."
  }

  assert {
    condition = one([
      for item in local.web_environment :
      item.value if item.name == "CHANGEOPS_IDENTITY_MODE"
    ]) == "alb"
    error_message = "The deployed proxy must fail closed on verified ALB and Cognito identity."
  }

  assert {
    condition = sort(flatten([
      for listener_condition in aws_lb_listener_rule.public_health[0].condition : flatten([
        for pattern in listener_condition.path_pattern : pattern.values
      ])
    ])) == sort(["/healthz", "/readyz"])
    error_message = "Only the non-product health and readiness routes may bypass Cognito."
  }
}

run "rejects_wrong_region" {
  command = plan

  variables {
    aws_region = "us-west-2"
  }

  expect_failures = [var.aws_region]
}

run "rejects_unconfirmed_database_destruction" {
  command = plan

  variables {
    allow_database_destroy        = true
    database_destroy_confirmation = "wrong-environment"
  }

  expect_failures = [var.database_destroy_confirmation]
}

run "rejects_unconfirmed_infrastructure_prerequisites" {
  command = plan

  variables {
    infrastructure_prerequisites_confirmed = false
  }

  expect_failures = [var.infrastructure_prerequisites_confirmed]
}
