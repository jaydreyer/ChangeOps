resource "aws_cloudwatch_log_group" "api" {
  name              = "/changeops/${var.environment}/api"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "web" {
  name              = "/changeops/${var.environment}/web"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "migration" {
  name              = "/changeops/${var.environment}/migration"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "bootstrap" {
  name              = "/changeops/${var.environment}/bootstrap"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "rds_postgresql" {
  name              = "/aws/rds/instance/${local.database_identifier}/postgresql"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "rds_upgrade" {
  name              = "/aws/rds/instance/${local.database_identifier}/upgrade"
  retention_in_days = 30
}

resource "aws_ecs_cluster" "main" {
  name = local.ecs_cluster_name

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

locals {
  api_environment = [
    {
      name  = "APP_NAME"
      value = "ChangeOps"
    },
    {
      name  = "AWS_REGION"
      value = var.aws_region
    },
    {
      name  = "DB_HOST"
      value = aws_db_instance.main.address
    },
    {
      name  = "DB_PORT"
      value = tostring(aws_db_instance.main.port)
    },
    {
      name  = "DB_NAME"
      value = var.database_name
    },
    {
      name  = "DB_SSLMODE"
      value = "require"
    },
    {
      name  = "EXTRACTION_MODEL_PROVIDER"
      value = "openai"
    },
    {
      name  = "EXTRACTION_MODEL"
      value = "gpt-5.6-luna"
    },
    {
      name  = "EXTRACTION_MODEL_TIMEOUT_SECONDS"
      value = "120"
    },
    {
      name  = "EXTRACTION_MODEL_MAX_RETRIES"
      value = "0"
    },
    {
      name  = "INTERPRETATION_MODEL_PROVIDER"
      value = "openai"
    },
    {
      name  = "INTERPRETATION_MODEL"
      value = "gpt-5.6-luna"
    },
    {
      name  = "INTERPRETATION_MODEL_TIMEOUT_SECONDS"
      value = "120"
    },
    {
      name  = "INTERPRETATION_MODEL_MAX_RETRIES"
      value = "0"
    },
    {
      name  = "JIRA_BASE_URL"
      value = var.enable_jira ? var.jira_base_url : ""
    },
    {
      name  = "JIRA_PROJECT_ID_OR_KEY"
      value = var.enable_jira ? var.jira_project_id_or_key : ""
    },
    {
      name  = "JIRA_ISSUE_TYPE_ID"
      value = var.enable_jira ? var.jira_issue_type_id : ""
    },
    {
      name  = "CONFLUENCE_BASE_URL"
      value = var.enable_confluence ? var.confluence_base_url : ""
    },
    {
      name  = "CONFLUENCE_MANAGER_TRAVEL_APPROVAL_GUIDE_PAGE_ID"
      value = var.enable_confluence ? var.confluence_manager_guide_page_id : ""
    },
  ]

  api_secrets = concat(
    [
      {
        name      = "DB_USERNAME"
        valueFrom = "${aws_secretsmanager_secret.runtime_db.arn}:username::"
      },
      {
        name      = "DB_PASSWORD"
        valueFrom = "${aws_secretsmanager_secret.runtime_db.arn}:password::"
      },
      {
        name      = "OPENAI_API_KEY"
        valueFrom = "${aws_secretsmanager_secret.model_provider.arn}:api_key::"
      },
    ],
    var.enable_jira ? [
      {
        name      = "JIRA_EMAIL"
        valueFrom = "${aws_secretsmanager_secret.jira.arn}:email::"
      },
      {
        name      = "JIRA_API_TOKEN"
        valueFrom = "${aws_secretsmanager_secret.jira.arn}:api_token::"
      },
    ] : [],
    var.enable_confluence ? [
      {
        name      = "CONFLUENCE_EMAIL"
        valueFrom = "${aws_secretsmanager_secret.confluence.arn}:email::"
      },
      {
        name      = "CONFLUENCE_API_TOKEN"
        valueFrom = "${aws_secretsmanager_secret.confluence.arn}:api_token::"
      },
    ] : [],
  )

  web_environment = [
    {
      name  = "CHANGEOPS_API_BASE_URL"
      value = "http://127.0.0.1:8000"
    },
    {
      name  = "CHANGEOPS_IDENTITY_MODE"
      value = "alb"
    },
    {
      name  = "AWS_REGION"
      value = var.aws_region
    },
    {
      name  = "ALB_EXPECTED_SIGNER_ARN"
      value = try(aws_lb.app[0].arn, "disabled")
    },
    {
      name  = "COGNITO_USER_POOL_ID"
      value = aws_cognito_user_pool.app.id
    },
    {
      name  = "COGNITO_CLIENT_ID"
      value = aws_cognito_user_pool_client.alb.id
    },
  ]

  migration_secrets = [
    {
      name      = "DB_USERNAME"
      valueFrom = "${aws_secretsmanager_secret.migration_db.arn}:username::"
    },
    {
      name      = "DB_PASSWORD"
      valueFrom = "${aws_secretsmanager_secret.migration_db.arn}:password::"
    },
  ]

  bootstrap_environment = [
    for item in local.api_environment : item
    if contains(["APP_NAME", "AWS_REGION", "DB_HOST", "DB_PORT", "DB_NAME", "DB_SSLMODE"], item.name)
  ]

  bootstrap_secrets = [
    for item in local.api_secrets : item
    if contains(["DB_USERNAME", "DB_PASSWORD"], item.name)
  ]
}

resource "aws_ecs_task_definition" "application" {
  family                   = local.application_family
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 1024
  memory                   = 2048
  execution_role_arn       = aws_iam_role.application_execution.arn
  task_role_arn            = aws_iam_role.application_task.arn

  container_definitions = jsonencode([
    {
      name              = "api"
      image             = "${aws_ecr_repository.api.repository_url}:${var.container_image_tag}"
      essential         = true
      cpu               = 768
      memoryReservation = 1280
      portMappings = [{
        name          = "api"
        containerPort = 8000
        hostPort      = 8000
        protocol      = "tcp"
        appProtocol   = "http"
      }]
      environment = local.api_environment
      secrets     = local.api_secrets
      healthCheck = {
        command     = ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz')"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 30
      }
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.api.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "api"
        }
      }
    },
    {
      name              = "web"
      image             = "${aws_ecr_repository.web.repository_url}:${var.container_image_tag}"
      essential         = true
      cpu               = 256
      memoryReservation = 512
      portMappings = [{
        name          = "web"
        containerPort = 3000
        hostPort      = 3000
        protocol      = "tcp"
        appProtocol   = "http"
      }]
      dependsOn = [{
        containerName = "api"
        condition     = "HEALTHY"
      }]
      environment = local.web_environment
      healthCheck = {
        command     = ["CMD-SHELL", "wget -q -O /dev/null http://127.0.0.1:3000${var.web_health_check_path} || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 30
      }
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.web.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "web"
        }
      }
    },
  ])

  runtime_platform {
    cpu_architecture        = "X86_64"
    operating_system_family = "LINUX"
  }

  tags = {
    Name = local.application_family
  }
}

resource "aws_ecs_task_definition" "migration" {
  family                   = local.migration_family
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.migration_execution.arn
  task_role_arn            = aws_iam_role.migration_task.arn

  container_definitions = jsonencode([
    {
      name      = "migration"
      image     = "${aws_ecr_repository.api.repository_url}:${var.container_image_tag}"
      essential = true
      command   = ["alembic", "upgrade", "head"]
      environment = [
        {
          name  = "DB_HOST"
          value = aws_db_instance.main.address
        },
        {
          name  = "DB_PORT"
          value = tostring(aws_db_instance.main.port)
        },
        {
          name  = "DB_NAME"
          value = var.database_name
        },
        {
          name  = "DB_SSLMODE"
          value = "require"
        },
      ]
      secrets = local.migration_secrets
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.migration.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "migration"
        }
      }
    },
  ])

  runtime_platform {
    cpu_architecture        = "X86_64"
    operating_system_family = "LINUX"
  }

  tags = {
    Name = local.migration_family
  }
}

resource "aws_ecs_task_definition" "bootstrap" {
  family                   = local.bootstrap_family
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.application_execution.arn
  task_role_arn            = aws_iam_role.application_task.arn

  container_definitions = jsonencode([
    {
      name        = "bootstrap"
      image       = "${aws_ecr_repository.api.repository_url}:${var.container_image_tag}"
      essential   = true
      command     = ["python", "-m", "changeops.deployment_bootstrap"]
      environment = local.bootstrap_environment
      secrets     = local.bootstrap_secrets
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.bootstrap.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "bootstrap"
        }
      }
    },
  ])

  runtime_platform {
    cpu_architecture        = "X86_64"
    operating_system_family = "LINUX"
  }

  tags = {
    Name = local.bootstrap_family
  }
}

resource "aws_ecs_service" "app" {
  name            = local.ecs_service_name
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.application.arn
  desired_count   = var.demo_enabled ? 1 : 0
  launch_type     = "FARGATE"

  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200
  health_check_grace_period_seconds  = var.demo_enabled ? 60 : null
  enable_execute_command             = false

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.task.id]
    assign_public_ip = true
  }

  dynamic "load_balancer" {
    for_each = var.demo_enabled ? [1] : []

    content {
      target_group_arn = aws_lb_target_group.web.arn
      container_name   = "web"
      container_port   = 3000
    }
  }

  depends_on = [aws_lb_listener.https]

  tags = {
    Name = local.ecs_service_name
  }

  lifecycle {
    # Terraform owns the service and its safe desired-count state. The protected release
    # workflow owns immutable application task-definition revisions.
    ignore_changes = [task_definition]
  }
}
