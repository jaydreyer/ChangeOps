resource "aws_sns_topic" "operations" {
  name = "${local.name_prefix}-operations"
}

resource "aws_sns_topic_subscription" "email" {
  count = var.alert_email == null ? 0 : 1

  topic_arn = aws_sns_topic.operations.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

data "aws_iam_policy_document" "operations_topic" {
  statement {
    sid       = "AllowCloudWatchAndEventBridge"
    effect    = "Allow"
    actions   = ["sns:Publish"]
    resources = [aws_sns_topic.operations.arn]

    principals {
      type = "Service"
      identifiers = [
        "cloudwatch.amazonaws.com",
        "events.amazonaws.com",
      ]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }

  statement {
    sid       = "AllowNamedRDSEvents"
    effect    = "Allow"
    actions   = ["sns:Publish"]
    resources = [aws_sns_topic.operations.arn]

    principals {
      type        = "Service"
      identifiers = ["events.rds.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }

    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"
      values   = [aws_db_instance.main.arn]
    }
  }
}

resource "aws_sns_topic_policy" "operations" {
  arn    = aws_sns_topic.operations.arn
  policy = data.aws_iam_policy_document.operations_topic.json
}

locals {
  alarm_actions = [aws_sns_topic.operations.arn]
}

resource "aws_cloudwatch_log_metric_filter" "application_errors" {
  name           = "${local.name_prefix}-application-errors"
  log_group_name = aws_cloudwatch_log_group.api.name
  pattern        = "{ $.level = \"ERROR\" }"

  metric_transformation {
    name          = "ApplicationErrors"
    namespace     = "ChangeOps/${var.environment}"
    value         = "1"
    default_value = "0"
  }
}

resource "aws_cloudwatch_metric_alarm" "application_errors" {
  count = var.demo_enabled ? 1 : 0

  alarm_name          = "${local.name_prefix}-application-errors"
  alarm_description   = "FastAPI emitted one or more structured ERROR records during a demo window."
  namespace           = "ChangeOps/${var.environment}"
  metric_name         = "ApplicationErrors"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_actions
  ok_actions          = local.alarm_actions
}

resource "aws_cloudwatch_metric_alarm" "alb_unhealthy_targets" {
  count = var.demo_enabled ? 1 : 0

  alarm_name          = "${local.name_prefix}-alb-unhealthy-targets"
  alarm_description   = "The authenticated ALB has an unhealthy Next.js target."
  namespace           = "AWS/ApplicationELB"
  metric_name         = "UnHealthyHostCount"
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 2
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "breaching"
  alarm_actions       = local.alarm_actions
  ok_actions          = local.alarm_actions

  dimensions = {
    LoadBalancer = aws_lb.app[0].arn_suffix
    TargetGroup  = aws_lb_target_group.web.arn_suffix
  }
}

resource "aws_cloudwatch_metric_alarm" "alb_5xx" {
  count = var.demo_enabled ? 1 : 0

  alarm_name          = "${local.name_prefix}-alb-5xx"
  alarm_description   = "The ALB returned server errors during a demo window."
  namespace           = "AWS/ApplicationELB"
  metric_name         = "HTTPCode_ELB_5XX_Count"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_actions
  ok_actions          = local.alarm_actions

  dimensions = {
    LoadBalancer = aws_lb.app[0].arn_suffix
  }
}

resource "aws_cloudwatch_metric_alarm" "target_5xx" {
  count = var.demo_enabled ? 1 : 0

  alarm_name          = "${local.name_prefix}-target-5xx"
  alarm_description   = "Next.js returned server errors during a demo window."
  namespace           = "AWS/ApplicationELB"
  metric_name         = "HTTPCode_Target_5XX_Count"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_actions
  ok_actions          = local.alarm_actions

  dimensions = {
    LoadBalancer = aws_lb.app[0].arn_suffix
    TargetGroup  = aws_lb_target_group.web.arn_suffix
  }
}

resource "aws_cloudwatch_metric_alarm" "alb_response_time" {
  count = var.demo_enabled ? 1 : 0

  alarm_name          = "${local.name_prefix}-alb-response-time"
  alarm_description   = "P95 ALB response time is abnormal for the bounded synchronous path."
  namespace           = "AWS/ApplicationELB"
  metric_name         = "TargetResponseTime"
  extended_statistic  = "p95"
  period              = 300
  evaluation_periods  = 2
  threshold           = 120
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_actions
  ok_actions          = local.alarm_actions

  dimensions = {
    LoadBalancer = aws_lb.app[0].arn_suffix
    TargetGroup  = aws_lb_target_group.web.arn_suffix
  }
}

resource "aws_cloudwatch_metric_alarm" "ecs_running_task" {
  count = var.demo_enabled ? 1 : 0

  alarm_name          = "${local.name_prefix}-ecs-running-task"
  alarm_description   = "The declared demo window does not have its one desired task."
  namespace           = "ECS/ContainerInsights"
  metric_name         = "RunningTaskCount"
  statistic           = "Minimum"
  period              = 60
  evaluation_periods  = 2
  threshold           = 1
  comparison_operator = "LessThanThreshold"
  treat_missing_data  = "breaching"
  alarm_actions       = local.alarm_actions
  ok_actions          = local.alarm_actions

  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = aws_ecs_service.app.name
  }
}

resource "aws_cloudwatch_metric_alarm" "ecs_cpu" {
  count = var.demo_enabled ? 1 : 0

  alarm_name          = "${local.name_prefix}-ecs-cpu"
  alarm_description   = "Sustained high application task CPU."
  namespace           = "AWS/ECS"
  metric_name         = "CPUUtilization"
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 2
  threshold           = 85
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_actions
  ok_actions          = local.alarm_actions

  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = aws_ecs_service.app.name
  }
}

resource "aws_cloudwatch_metric_alarm" "ecs_memory" {
  count = var.demo_enabled ? 1 : 0

  alarm_name          = "${local.name_prefix}-ecs-memory"
  alarm_description   = "Sustained high application task memory."
  namespace           = "AWS/ECS"
  metric_name         = "MemoryUtilization"
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 2
  threshold           = 85
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_actions
  ok_actions          = local.alarm_actions

  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = aws_ecs_service.app.name
  }
}

resource "aws_cloudwatch_metric_alarm" "rds_cpu" {
  alarm_name          = "${local.name_prefix}-rds-cpu"
  alarm_description   = "Sustained high PostgreSQL CPU."
  namespace           = "AWS/RDS"
  metric_name         = "CPUUtilization"
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 2
  threshold           = 85
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_actions
  ok_actions          = local.alarm_actions

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.identifier
  }
}

resource "aws_cloudwatch_metric_alarm" "rds_free_storage" {
  alarm_name          = "${local.name_prefix}-rds-free-storage"
  alarm_description   = "PostgreSQL free storage dropped below 2 GiB."
  namespace           = "AWS/RDS"
  metric_name         = "FreeStorageSpace"
  statistic           = "Minimum"
  period              = 300
  evaluation_periods  = 2
  threshold           = 2147483648
  comparison_operator = "LessThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_actions
  ok_actions          = local.alarm_actions

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.identifier
  }
}

resource "aws_cloudwatch_metric_alarm" "rds_connections" {
  alarm_name          = "${local.name_prefix}-rds-connections"
  alarm_description   = "PostgreSQL connections are unexpectedly high for the single-task baseline."
  namespace           = "AWS/RDS"
  metric_name         = "DatabaseConnections"
  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 2
  threshold           = 60
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_actions
  ok_actions          = local.alarm_actions

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.identifier
  }
}

resource "aws_db_event_subscription" "availability" {
  name      = "${local.name_prefix}-database-availability"
  sns_topic = aws_sns_topic.operations.arn

  source_type = "db-instance"
  source_ids  = [aws_db_instance.main.identifier]
  event_categories = [
    "availability",
    "failure",
    "failover",
    "low storage",
    "maintenance",
    "notification",
    "recovery",
  ]

  depends_on = [aws_sns_topic_policy.operations]
}

resource "aws_cloudwatch_event_rule" "ecs_deployment_failed" {
  name        = "${local.name_prefix}-ecs-deployment-failed"
  description = "Report ECS deployment circuit-breaker failures."

  event_pattern = jsonencode({
    source        = ["aws.ecs"]
    "detail-type" = ["ECS Deployment State Change"]
    detail = {
      eventName  = ["SERVICE_DEPLOYMENT_FAILED"]
      clusterArn = [aws_ecs_cluster.main.arn]
    }
  })
}

resource "aws_cloudwatch_event_target" "ecs_deployment_failed" {
  rule      = aws_cloudwatch_event_rule.ecs_deployment_failed.name
  target_id = "operations"
  arn       = aws_sns_topic.operations.arn
}

resource "aws_cloudwatch_event_rule" "application_task_failed" {
  name        = "${local.name_prefix}-application-task-failed"
  description = "Report unexpected application task stops while excluding normal scheduler replacement."

  event_pattern = jsonencode({
    source        = ["aws.ecs"]
    "detail-type" = ["ECS Task State Change"]
    detail = {
      clusterArn        = [aws_ecs_cluster.main.arn]
      lastStatus        = ["STOPPED"]
      taskDefinitionArn = [{ prefix = "arn:${data.aws_partition.current.partition}:ecs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:task-definition/${local.application_family}:" }]
      stopCode          = [{ "anything-but" = "ServiceSchedulerInitiated" }]
    }
  })
}

resource "aws_cloudwatch_event_target" "application_task_failed" {
  rule      = aws_cloudwatch_event_rule.application_task_failed.name
  target_id = "operations"
  arn       = aws_sns_topic.operations.arn
}

resource "aws_cloudwatch_event_rule" "migration_failed" {
  name        = "${local.name_prefix}-migration-failed"
  description = "Report nonzero exits from the one-off migration task."

  event_pattern = jsonencode({
    source        = ["aws.ecs"]
    "detail-type" = ["ECS Task State Change"]
    detail = {
      clusterArn        = [aws_ecs_cluster.main.arn]
      lastStatus        = ["STOPPED"]
      taskDefinitionArn = [{ prefix = "arn:${data.aws_partition.current.partition}:ecs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:task-definition/${local.migration_family}:" }]
      containers = {
        exitCode = [{ "anything-but" = 0 }]
      }
    }
  })
}

resource "aws_cloudwatch_event_target" "migration_failed" {
  rule      = aws_cloudwatch_event_rule.migration_failed.name
  target_id = "operations"
  arn       = aws_sns_topic.operations.arn
}

resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${local.name_prefix}-operations"

  dashboard_body = jsonencode({
    widgets = concat(
      [
        {
          type   = "metric"
          x      = 0
          y      = 0
          width  = 12
          height = 6
          properties = {
            title  = "ECS CPU and memory"
            region = var.aws_region
            metrics = [
              ["AWS/ECS", "CPUUtilization", "ClusterName", aws_ecs_cluster.main.name, "ServiceName", aws_ecs_service.app.name],
              [".", "MemoryUtilization", ".", ".", ".", "."],
            ]
          }
        },
        {
          type   = "metric"
          x      = 12
          y      = 0
          width  = 12
          height = 6
          properties = {
            title  = "RDS health"
            region = var.aws_region
            metrics = [
              ["AWS/RDS", "CPUUtilization", "DBInstanceIdentifier", aws_db_instance.main.identifier],
              [".", "DatabaseConnections", ".", "."],
              [".", "FreeStorageSpace", ".", ".", { yAxis = "right" }],
            ]
          }
        },
      ],
      var.demo_enabled ? [
        {
          type   = "metric"
          x      = 0
          y      = 6
          width  = 24
          height = 6
          properties = {
            title  = "Authenticated ingress"
            region = var.aws_region
            metrics = [
              ["AWS/ApplicationELB", "HTTPCode_ELB_5XX_Count", "LoadBalancer", aws_lb.app[0].arn_suffix],
              [".", "TargetResponseTime", ".", ".", { stat = "p95" }],
              [".", "UnHealthyHostCount", ".", ".", "TargetGroup", aws_lb_target_group.web.arn_suffix],
            ]
          }
        },
      ] : [],
    )
  })
}

resource "aws_budgets_budget" "monthly" {
  name         = "${local.name_prefix}-monthly"
  budget_type  = "COST"
  limit_amount = "20"
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  cost_filter {
    name   = "TagKeyValue"
    values = ["user:Application$ChangeOps"]
  }

  dynamic "notification" {
    for_each = var.alert_email == null ? [] : [50, 80, 100]

    content {
      comparison_operator        = "GREATER_THAN"
      threshold                  = notification.value
      threshold_type             = "PERCENTAGE"
      notification_type          = "ACTUAL"
      subscriber_email_addresses = [var.alert_email]
    }
  }
}
