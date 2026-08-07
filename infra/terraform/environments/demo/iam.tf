data "aws_iam_policy_document" "ecs_tasks_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "application_execution" {
  name               = "${local.name_prefix}-application-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_assume.json
}

resource "aws_iam_role" "migration_execution" {
  name               = "${local.name_prefix}-migration-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_assume.json
}

resource "aws_iam_role" "application_task" {
  name               = "${local.name_prefix}-application-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_assume.json
  description        = "ChangeOps application task role; intentionally has no AWS API permissions"
}

resource "aws_iam_role" "migration_task" {
  name               = "${local.name_prefix}-migration-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_assume.json
  description        = "ChangeOps migration task role; database authority comes only from its injected credential"
}

data "aws_iam_policy_document" "application_execution" {
  statement {
    sid    = "ECRAuthorization"
    effect = "Allow"
    actions = [
      "ecr:GetAuthorizationToken",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "ReadApplicationImages"
    effect = "Allow"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:BatchGetImage",
      "ecr:GetDownloadUrlForLayer",
    ]
    resources = [
      aws_ecr_repository.api.arn,
      aws_ecr_repository.web.arn,
    ]
  }

  statement {
    sid    = "WriteApplicationLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = [
      "${aws_cloudwatch_log_group.api.arn}:*",
      "${aws_cloudwatch_log_group.web.arn}:*",
      "${aws_cloudwatch_log_group.bootstrap.arn}:*",
    ]
  }

  statement {
    sid     = "ReadNamedApplicationSecrets"
    effect  = "Allow"
    actions = ["secretsmanager:GetSecretValue"]
    resources = concat(
      [
        aws_secretsmanager_secret.runtime_db.arn,
        aws_secretsmanager_secret.model_provider.arn,
      ],
      var.enable_jira ? [aws_secretsmanager_secret.jira.arn] : [],
      var.enable_confluence ? [aws_secretsmanager_secret.confluence.arn] : [],
    )
  }
}

resource "aws_iam_role_policy" "application_execution" {
  name   = "least-privilege-application-execution"
  role   = aws_iam_role.application_execution.id
  policy = data.aws_iam_policy_document.application_execution.json
}

data "aws_iam_policy_document" "migration_execution" {
  statement {
    sid       = "ECRAuthorization"
    effect    = "Allow"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  statement {
    sid    = "ReadBackendImage"
    effect = "Allow"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:BatchGetImage",
      "ecr:GetDownloadUrlForLayer",
    ]
    resources = [aws_ecr_repository.api.arn]
  }

  statement {
    sid    = "WriteMigrationLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["${aws_cloudwatch_log_group.migration.arn}:*"]
  }

  statement {
    sid       = "ReadMigrationSecretOnly"
    effect    = "Allow"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [aws_secretsmanager_secret.migration_db.arn]
  }
}

resource "aws_iam_role_policy" "migration_execution" {
  name   = "least-privilege-migration-execution"
  role   = aws_iam_role.migration_execution.id
  policy = data.aws_iam_policy_document.migration_execution.json
}

variable "existing_github_oidc_provider_arn" {
  description = "Existing GitHub Actions OIDC provider ARN. Leave null to create it in this account."
  type        = string
  default     = null
  nullable    = true
}

resource "aws_iam_openid_connect_provider" "github" {
  count = var.existing_github_oidc_provider_arn == null ? 1 : 0

  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
}

locals {
  github_oidc_provider_arn = var.existing_github_oidc_provider_arn != null ? var.existing_github_oidc_provider_arn : aws_iam_openid_connect_provider.github[0].arn
}

data "aws_iam_policy_document" "github_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [local.github_oidc_provider_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = [local.github_oidc_subject]
    }
  }
}

resource "aws_iam_role" "github_deploy" {
  name               = "${local.name_prefix}-github-deploy"
  description        = "OIDC role for immutable image push, gated migration, and ECS deployment"
  assume_role_policy = data.aws_iam_policy_document.github_assume.json

  max_session_duration = 3600
}

data "aws_iam_policy_document" "github_deploy" {
  statement {
    sid       = "ECRAuthorization"
    effect    = "Allow"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  statement {
    sid    = "PushNamedImages"
    effect = "Allow"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:CompleteLayerUpload",
      "ecr:GetDownloadUrlForLayer",
      "ecr:InitiateLayerUpload",
      "ecr:PutImage",
      "ecr:UploadLayerPart",
    ]
    resources = [
      aws_ecr_repository.api.arn,
      aws_ecr_repository.web.arn,
    ]
  }

  statement {
    sid    = "ReadNamedImageMetadata"
    effect = "Allow"
    actions = [
      "ecr:DescribeImages",
      "ecr:DescribeRepositories",
    ]
    resources = [
      aws_ecr_repository.api.arn,
      aws_ecr_repository.web.arn,
    ]
  }

  statement {
    sid    = "RegisterReviewedTaskDefinitions"
    effect = "Allow"
    actions = [
      "ecs:RegisterTaskDefinition",
      "ecs:TagResource",
    ]
    resources = ["*"]

    condition {
      test     = "StringEquals"
      variable = "aws:RequestTag/Application"
      values   = ["ChangeOps"]
    }
  }

  statement {
    sid     = "RunNamedTaskDefinitions"
    effect  = "Allow"
    actions = ["ecs:RunTask"]
    resources = [
      "arn:${data.aws_partition.current.partition}:ecs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:task-definition/${local.migration_family}:*",
      "arn:${data.aws_partition.current.partition}:ecs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:task-definition/${local.bootstrap_family}:*",
    ]

    condition {
      test     = "ArnEquals"
      variable = "ecs:cluster"
      values   = [aws_ecs_cluster.main.arn]
    }
  }

  statement {
    sid       = "StopNamedClusterTasks"
    effect    = "Allow"
    actions   = ["ecs:StopTask"]
    resources = ["arn:${data.aws_partition.current.partition}:ecs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:task/${local.ecs_cluster_name}/*"]

    condition {
      test     = "ArnEquals"
      variable = "ecs:cluster"
      values   = [aws_ecs_cluster.main.arn]
    }
  }

  statement {
    sid       = "UpdateNamedService"
    effect    = "Allow"
    actions   = ["ecs:UpdateService"]
    resources = [local.ecs_service_arn]
  }

  statement {
    sid    = "ReadDeploymentState"
    effect = "Allow"
    actions = [
      "ecs:DescribeServices",
      "ecs:DescribeTaskDefinition",
      "ecs:DescribeTasks",
      "ecs:ListTaskDefinitions",
      "ecs:ListTasks",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "ReadNamedLogs"
    effect = "Allow"
    actions = [
      "logs:GetLogEvents",
      "logs:FilterLogEvents",
    ]
    resources = [
      "${aws_cloudwatch_log_group.api.arn}:*",
      "${aws_cloudwatch_log_group.web.arn}:*",
      "${aws_cloudwatch_log_group.migration.arn}:*",
      "${aws_cloudwatch_log_group.bootstrap.arn}:*",
    ]
  }

  statement {
    sid     = "PassNamedECSRolesOnly"
    effect  = "Allow"
    actions = ["iam:PassRole"]
    resources = [
      aws_iam_role.application_execution.arn,
      aws_iam_role.application_task.arn,
      aws_iam_role.migration_execution.arn,
      aws_iam_role.migration_task.arn,
    ]

    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy" "github_deploy" {
  name   = "changeops-deployment-only"
  role   = aws_iam_role.github_deploy.id
  policy = data.aws_iam_policy_document.github_deploy.json
}

resource "aws_iam_role" "github_lifecycle" {
  name               = "${local.name_prefix}-github-lifecycle"
  description        = "OIDC role for separately approved demo startup and destructive teardown workflows"
  assume_role_policy = data.aws_iam_policy_document.github_assume.json

  max_session_duration = 3600
}

data "aws_iam_policy_document" "github_lifecycle" {
  statement {
    sid    = "ManageNamedDatabaseLifecycle"
    effect = "Allow"
    actions = [
      "rds:CreateDBSnapshot",
      "rds:DeleteDBInstance",
      "rds:ModifyDBInstance",
      "rds:StartDBInstance",
      "rds:StopDBInstance",
    ]
    resources = [
      aws_db_instance.main.arn,
      "arn:${data.aws_partition.current.partition}:rds:${var.aws_region}:${data.aws_caller_identity.current.account_id}:snapshot:${local.name_prefix}-*",
    ]
  }

  statement {
    sid    = "RestoreOnlyTaggedChangeOpsDatabase"
    effect = "Allow"
    actions = [
      "rds:RestoreDBInstanceFromDBSnapshot",
    ]
    resources = [
      "arn:${data.aws_partition.current.partition}:rds:${var.aws_region}:${data.aws_caller_identity.current.account_id}:db:${local.name_prefix}-*",
      "arn:${data.aws_partition.current.partition}:rds:${var.aws_region}:${data.aws_caller_identity.current.account_id}:snapshot:${local.name_prefix}-*",
      "arn:${data.aws_partition.current.partition}:rds:${var.aws_region}:${data.aws_caller_identity.current.account_id}:subgrp:${aws_db_subnet_group.main.name}",
      "arn:${data.aws_partition.current.partition}:rds:${var.aws_region}:${data.aws_caller_identity.current.account_id}:pg:${aws_db_parameter_group.postgres17.name}",
    ]

    condition {
      test     = "StringEquals"
      variable = "aws:RequestTag/Application"
      values   = ["ChangeOps"]
    }

    condition {
      test     = "StringEquals"
      variable = "rds:DatabaseClass"
      values   = ["db.t4g.micro"]
    }

    condition {
      test     = "Bool"
      variable = "rds:PubliclyAccessible"
      values   = ["false"]
    }

    condition {
      test     = "NumericLessThanEquals"
      variable = "rds:StorageSize"
      values   = ["50"]
    }
  }

  statement {
    sid       = "TagOnlyRestoredChangeOpsDatabase"
    effect    = "Allow"
    actions   = ["rds:AddTagsToResource"]
    resources = ["arn:${data.aws_partition.current.partition}:rds:${var.aws_region}:${data.aws_caller_identity.current.account_id}:db:${local.name_prefix}-*"]

    condition {
      test     = "StringEquals"
      variable = "aws:RequestTag/Application"
      values   = ["ChangeOps"]
    }
  }

  statement {
    sid    = "ReadDatabaseState"
    effect = "Allow"
    actions = [
      "rds:DescribeDBInstances",
      "rds:DescribeDBSnapshots",
    ]
    resources = ["*"]
  }

  statement {
    sid       = "CreateTaggedLoadBalancer"
    effect    = "Allow"
    actions   = ["elasticloadbalancing:CreateLoadBalancer"]
    resources = ["*"]

    condition {
      test     = "StringEquals"
      variable = "aws:RequestTag/Application"
      values   = ["ChangeOps"]
    }
  }

  statement {
    sid     = "CreateTaggedListeners"
    effect  = "Allow"
    actions = ["elasticloadbalancing:CreateListener"]
    resources = [
      "arn:${data.aws_partition.current.partition}:elasticloadbalancing:${var.aws_region}:${data.aws_caller_identity.current.account_id}:loadbalancer/app/${local.name_prefix}-alb/*",
      "arn:${data.aws_partition.current.partition}:elasticloadbalancing:${var.aws_region}:${data.aws_caller_identity.current.account_id}:listener/app/${local.name_prefix}-alb/*/*",
      aws_lb_target_group.web.arn,
    ]

    condition {
      test     = "StringEquals"
      variable = "aws:RequestTag/Application"
      values   = ["ChangeOps"]
    }
  }

  statement {
    sid    = "ManageNamedIngress"
    effect = "Allow"
    actions = [
      "elasticloadbalancing:AddTags",
      "elasticloadbalancing:DeleteListener",
      "elasticloadbalancing:DeleteLoadBalancer",
      "elasticloadbalancing:ModifyListener",
    ]
    resources = [
      "arn:${data.aws_partition.current.partition}:elasticloadbalancing:${var.aws_region}:${data.aws_caller_identity.current.account_id}:loadbalancer/app/${local.name_prefix}-alb/*",
      "arn:${data.aws_partition.current.partition}:elasticloadbalancing:${var.aws_region}:${data.aws_caller_identity.current.account_id}:listener/app/${local.name_prefix}-alb/*/*",
      aws_lb_target_group.web.arn,
    ]

    condition {
      test     = "StringEquals"
      variable = "aws:ResourceTag/Application"
      values   = ["ChangeOps"]
    }
  }

  statement {
    sid    = "ReadIngress"
    effect = "Allow"
    actions = [
      "elasticloadbalancing:DescribeListeners",
      "elasticloadbalancing:DescribeLoadBalancers",
      "elasticloadbalancing:DescribeTargetHealth",
    ]
    resources = ["*"]
  }

  statement {
    sid       = "UpdateApplicationAlias"
    effect    = "Allow"
    actions   = ["route53:ChangeResourceRecordSets"]
    resources = ["arn:${data.aws_partition.current.partition}:route53:::hostedzone/${local.hosted_zone_id}"]

    condition {
      test     = "ForAllValues:StringEquals"
      variable = "route53:ChangeResourceRecordSetsNormalizedRecordNames"
      values   = [var.application_hostname]
    }

    condition {
      test     = "ForAllValues:StringEquals"
      variable = "route53:ChangeResourceRecordSetsRecordTypes"
      values   = ["A"]
    }

    condition {
      test     = "ForAllValues:StringEquals"
      variable = "route53:ChangeResourceRecordSetsActions"
      values   = ["CREATE", "UPSERT", "DELETE"]
    }
  }

  statement {
    sid    = "ReadIngressAndDNS"
    effect = "Allow"
    actions = [
      "route53:GetChange",
      "route53:ListResourceRecordSets",
      "route53:ListHostedZonesByName",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "RegisterTaggedApplicationTask"
    effect = "Allow"
    actions = [
      "ecs:RegisterTaskDefinition",
      "ecs:TagResource",
    ]
    resources = ["*"]

    condition {
      test     = "StringEquals"
      variable = "aws:RequestTag/Application"
      values   = ["ChangeOps"]
    }
  }

  statement {
    sid       = "UpdateNamedApplicationService"
    effect    = "Allow"
    actions   = ["ecs:UpdateService"]
    resources = [local.ecs_service_arn]
  }

  statement {
    sid    = "ReadApplicationService"
    effect = "Allow"
    actions = [
      "ecs:DescribeServices",
      "ecs:DescribeTaskDefinition",
    ]
    resources = ["*"]
  }

  statement {
    sid     = "PassNamedApplicationRolesOnly"
    effect  = "Allow"
    actions = ["iam:PassRole"]
    resources = [
      aws_iam_role.application_execution.arn,
      aws_iam_role.application_task.arn,
    ]

    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy" "github_lifecycle" {
  name   = "changeops-environment-lifecycle-only"
  role   = aws_iam_role.github_lifecycle.id
  policy = data.aws_iam_policy_document.github_lifecycle.json
}
