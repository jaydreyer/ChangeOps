resource "aws_lb_target_group" "web" {
  name        = "${local.name_prefix}-web"
  port        = 3000
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = aws_vpc.main.id

  deregistration_delay = 30

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 30
    timeout             = 5
    matcher             = "200"
    path                = var.web_health_check_path
    protocol            = "HTTP"
  }

  tags = {
    Name = "${local.name_prefix}-web"
  }
}

resource "aws_lb" "app" {
  count = var.demo_enabled ? 1 : 0

  name                       = "${local.name_prefix}-alb"
  internal                   = false
  load_balancer_type         = "application"
  security_groups            = [aws_security_group.alb.id]
  subnets                    = aws_subnet.public[*].id
  enable_deletion_protection = false
  idle_timeout               = 180
  drop_invalid_header_fields = true

  tags = {
    Name         = "${local.name_prefix}-alb"
    BillingState = "demo-window"
  }
}

resource "aws_lb_listener" "http" {
  count = var.demo_enabled ? 1 : 0

  load_balancer_arn = aws_lb.app[0].arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"

    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

resource "aws_lb_listener" "https" {
  count = var.demo_enabled ? 1 : 0

  load_balancer_arn = aws_lb.app[0].arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate_validation.app.certificate_arn

  default_action {
    type  = "authenticate-cognito"
    order = 1

    authenticate_cognito {
      user_pool_arn              = aws_cognito_user_pool.app.arn
      user_pool_client_id        = aws_cognito_user_pool_client.alb.id
      user_pool_domain           = aws_cognito_user_pool_domain.app.domain
      on_unauthenticated_request = "authenticate"
      scope                      = "openid"
      session_cookie_name        = "ChangeOpsSession"
      session_timeout            = 3600
    }
  }

  default_action {
    type             = "forward"
    order            = 2
    target_group_arn = aws_lb_target_group.web.arn
  }
}

resource "aws_route53_record" "app_ipv4" {
  count = var.demo_enabled ? 1 : 0

  zone_id = local.hosted_zone_id
  name    = var.application_hostname
  type    = "A"

  alias {
    name                   = aws_lb.app[0].dns_name
    zone_id                = aws_lb.app[0].zone_id
    evaluate_target_health = true
  }
}
