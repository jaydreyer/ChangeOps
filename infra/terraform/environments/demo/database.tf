resource "aws_db_subnet_group" "main" {
  name       = "${local.name_prefix}-database"
  subnet_ids = aws_subnet.database[*].id

  tags = {
    Name = "${local.name_prefix}-database"
  }
}

resource "aws_db_parameter_group" "postgres17" {
  name   = "${local.name_prefix}-postgres17"
  family = "postgres17"

  parameter {
    name  = "rds.force_ssl"
    value = "1"
  }

  tags = {
    Name = "${local.name_prefix}-postgres17"
  }
}

resource "aws_db_instance" "main" {
  identifier = local.database_identifier

  engine         = "postgres"
  engine_version = "17"
  instance_class = "db.t4g.micro"
  multi_az       = false

  allocated_storage     = 20
  max_allocated_storage = 50
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name                     = var.database_name
  username                    = var.database_admin_username
  manage_master_user_password = true
  port                        = 5432

  db_subnet_group_name   = aws_db_subnet_group.main.name
  parameter_group_name   = aws_db_parameter_group.postgres17.name
  vpc_security_group_ids = [aws_security_group.database.id]
  publicly_accessible    = false

  backup_retention_period = 7
  backup_window           = "03:00-04:00"
  maintenance_window      = "sun:04:00-sun:05:00"
  copy_tags_to_snapshot   = true

  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  auto_minor_version_upgrade      = true

  deletion_protection       = !var.allow_database_destroy
  delete_automated_backups  = false
  skip_final_snapshot       = false
  final_snapshot_identifier = var.database_final_snapshot_identifier

  depends_on = [
    aws_cloudwatch_log_group.rds_postgresql,
    aws_cloudwatch_log_group.rds_upgrade,
  ]

  tags = {
    Name            = local.database_identifier
    DataSensitivity = "portfolio-demo"
  }
}
