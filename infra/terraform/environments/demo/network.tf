data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "${local.name_prefix}-vpc"
  }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${local.name_prefix}-igw"
  }
}

resource "aws_subnet" "public" {
  count = 2

  vpc_id                  = aws_vpc.main.id
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  cidr_block              = local.public_subnet_cidrs[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name = "${local.name_prefix}-public-${count.index + 1}"
    Tier = "public-runtime"
  }
}

resource "aws_subnet" "database" {
  count = 2

  vpc_id                  = aws_vpc.main.id
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  cidr_block              = local.database_subnet_cidrs[count.index]
  map_public_ip_on_launch = false

  tags = {
    Name = "${local.name_prefix}-database-${count.index + 1}"
    Tier = "isolated-database"
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name = "${local.name_prefix}-public"
  }
}

resource "aws_route_table_association" "public" {
  count = 2

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table" "database" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${local.name_prefix}-database-isolated"
  }
}

resource "aws_route_table_association" "database" {
  count = 2

  subnet_id      = aws_subnet.database[count.index].id
  route_table_id = aws_route_table.database.id
}

resource "aws_security_group" "alb" {
  name        = "${local.name_prefix}-alb"
  description = "Public HTTPS ingress to the Cognito-authenticated ALB"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name = "${local.name_prefix}-alb"
  }
}

resource "aws_vpc_security_group_ingress_rule" "alb_http" {
  security_group_id = aws_security_group.alb.id
  description       = "HTTP redirect only"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80
}

resource "aws_vpc_security_group_ingress_rule" "alb_https" {
  security_group_id = aws_security_group.alb.id
  description       = "Authenticated HTTPS product ingress"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
}

resource "aws_security_group" "task" {
  name        = "${local.name_prefix}-task"
  description = "Fargate task: Next.js only from ALB; FastAPI has no ingress"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name = "${local.name_prefix}-task"
  }
}

resource "aws_vpc_security_group_ingress_rule" "task_web_from_alb" {
  security_group_id            = aws_security_group.task.id
  description                  = "Next.js only from the ALB"
  referenced_security_group_id = aws_security_group.alb.id
  ip_protocol                  = "tcp"
  from_port                    = 3000
  to_port                      = 3000
}

resource "aws_vpc_security_group_egress_rule" "alb_to_web" {
  security_group_id            = aws_security_group.alb.id
  description                  = "Forward authenticated requests to Next.js"
  referenced_security_group_id = aws_security_group.task.id
  ip_protocol                  = "tcp"
  from_port                    = 3000
  to_port                      = 3000
}

resource "aws_vpc_security_group_egress_rule" "alb_https" {
  security_group_id = aws_security_group.alb.id
  description       = "TLS to Cognito authentication endpoints"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
}

resource "aws_security_group" "database" {
  name        = "${local.name_prefix}-database"
  description = "PostgreSQL only from the ChangeOps Fargate task"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name = "${local.name_prefix}-database"
  }
}

resource "aws_vpc_security_group_ingress_rule" "database_from_task" {
  security_group_id            = aws_security_group.database.id
  description                  = "TLS PostgreSQL only from the task security group"
  referenced_security_group_id = aws_security_group.task.id
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
}

resource "aws_vpc_security_group_egress_rule" "task_to_database" {
  security_group_id            = aws_security_group.task.id
  description                  = "PostgreSQL only to the database security group"
  referenced_security_group_id = aws_security_group.database.id
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
}

resource "aws_vpc_security_group_egress_rule" "task_https" {
  security_group_id = aws_security_group.task.id
  description       = "Outbound TLS for ECR, providers, Jira, and Confluence"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
}

resource "aws_vpc_security_group_egress_rule" "task_dns_udp" {
  security_group_id = aws_security_group.task.id
  description       = "DNS through the VPC resolver"
  cidr_ipv4         = local.vpc_dns_resolver_cidr
  ip_protocol       = "udp"
  from_port         = 53
  to_port           = 53
}

resource "aws_vpc_security_group_egress_rule" "task_dns_tcp" {
  security_group_id = aws_security_group.task.id
  description       = "DNS fallback through the VPC resolver"
  cidr_ipv4         = local.vpc_dns_resolver_cidr
  ip_protocol       = "tcp"
  from_port         = 53
  to_port           = 53
}
