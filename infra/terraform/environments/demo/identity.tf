resource "aws_route53_zone" "app" {
  count = var.existing_hosted_zone_id == null ? 1 : 0

  name    = var.hosted_zone_name
  comment = "Public DNS for ChangeOps ${var.environment}"
}

resource "aws_acm_certificate" "app" {
  domain_name       = var.application_hostname
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name = var.application_hostname
  }
}

resource "aws_route53_record" "certificate_validation" {
  allow_overwrite = true
  zone_id         = local.hosted_zone_id
  name            = one(aws_acm_certificate.app.domain_validation_options).resource_record_name
  type            = one(aws_acm_certificate.app.domain_validation_options).resource_record_type
  ttl             = 60
  records         = [one(aws_acm_certificate.app.domain_validation_options).resource_record_value]
}

resource "aws_acm_certificate_validation" "app" {
  certificate_arn         = aws_acm_certificate.app.arn
  validation_record_fqdns = [aws_route53_record.certificate_validation.fqdn]
}

resource "aws_cognito_user_pool" "app" {
  name                     = "${local.name_prefix}-users"
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]
  mfa_configuration        = "ON"

  admin_create_user_config {
    allow_admin_create_user_only = true
  }

  software_token_mfa_configuration {
    enabled = true
  }

  password_policy {
    minimum_length                   = 14
    require_lowercase                = true
    require_numbers                  = true
    require_symbols                  = true
    require_uppercase                = true
    temporary_password_validity_days = 1
  }

  tags = {
    Name = "${local.name_prefix}-users"
  }
}

resource "aws_cognito_user_pool_domain" "app" {
  domain       = "${local.name_prefix}-${data.aws_caller_identity.current.account_id}"
  user_pool_id = aws_cognito_user_pool.app.id
}

resource "aws_cognito_user_pool_client" "alb" {
  name                                 = "${local.name_prefix}-alb"
  user_pool_id                         = aws_cognito_user_pool.app.id
  generate_secret                      = true
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid"]
  supported_identity_providers         = ["COGNITO"]
  callback_urls                        = ["https://${var.application_hostname}/oauth2/idpresponse"]
  logout_urls                          = ["https://${var.application_hostname}/"]
  prevent_user_existence_errors        = "ENABLED"

  access_token_validity  = 1
  id_token_validity      = 1
  refresh_token_validity = 1

  token_validity_units {
    access_token  = "hours"
    id_token      = "hours"
    refresh_token = "days"
  }

  explicit_auth_flows = [
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH",
  ]
}

resource "aws_cognito_user_group" "reviewer" {
  name         = "reviewer"
  description  = "Closed ChangeOps reviewer role"
  user_pool_id = aws_cognito_user_pool.app.id
  precedence   = 20
}

resource "aws_cognito_user_group" "admin" {
  name         = "admin"
  description  = "Closed ChangeOps administrator role"
  user_pool_id = aws_cognito_user_pool.app.id
  precedence   = 10
}
