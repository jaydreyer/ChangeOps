resource "aws_secretsmanager_secret" "runtime_db" {
  name                    = "${local.name_prefix}/database/runtime"
  description             = "Least-privilege ChangeOps runtime database username and password"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret" "migration_db" {
  name                    = "${local.name_prefix}/database/migration"
  description             = "Schema-owner username and password for the one-off Alembic task"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret" "model_provider" {
  name                    = "${local.name_prefix}/provider/model"
  description             = "Model-provider API key used only by the FastAPI container"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret" "jira" {
  name                    = "${local.name_prefix}/provider/jira"
  description             = "Dedicated Jira email and API token; Jira remains disabled until populated"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret" "confluence" {
  name                    = "${local.name_prefix}/provider/confluence"
  description             = "Dedicated Confluence email and API token; refresh remains disabled until populated"
  recovery_window_in_days = 7
}
