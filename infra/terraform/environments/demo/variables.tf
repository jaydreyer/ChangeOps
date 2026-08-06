variable "aws_region" {
  description = "AWS Region selected by ADR-0022."
  type        = string
  default     = "us-east-1"

  validation {
    condition     = var.aws_region == "us-east-1"
    error_message = "ADR-0022 fixes the initial deployment Region to us-east-1."
  }
}

variable "environment" {
  description = "Stable environment identifier used in names and authorization tags."
  type        = string
  default     = "demo"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,15}$", var.environment))
    error_message = "environment must be 2-16 lowercase alphanumeric or hyphen characters."
  }
}

variable "hosted_zone_name" {
  description = "Public DNS zone name, for example example.com."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$", var.hosted_zone_name))
    error_message = "hosted_zone_name must be a lowercase public DNS name."
  }
}

variable "application_hostname" {
  description = "Public ChangeOps hostname inside hosted_zone_name."
  type        = string

  validation {
    condition     = endswith(var.application_hostname, ".${var.hosted_zone_name}") && var.application_hostname != var.hosted_zone_name
    error_message = "application_hostname must be a subdomain of hosted_zone_name."
  }
}

variable "existing_hosted_zone_id" {
  description = "Existing public Route 53 hosted zone ID. Leave null to let this root create the zone."
  type        = string
  default     = null
  nullable    = true
}

variable "github_repository" {
  description = "GitHub owner/repository allowed to assume the AWS roles."
  type        = string
  default     = "jaydreyer/ChangeOps"

  validation {
    condition     = can(regex("^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", var.github_repository))
    error_message = "github_repository must use owner/repository form."
  }
}

variable "github_environment" {
  description = "Protected GitHub Environment required by the OIDC trust policies."
  type        = string
  default     = "production"

  validation {
    condition     = length(trimspace(var.github_environment)) > 0
    error_message = "github_environment must not be empty."
  }
}

variable "demo_enabled" {
  description = "Create billable ingress and run one ECS task for a declared demo window."
  type        = bool
  default     = false
}

variable "infrastructure_prerequisites_confirmed" {
  description = "Must be true only after every ADR-0022 application prerequisite is implemented and tested."
  type        = bool

  validation {
    condition     = var.infrastructure_prerequisites_confirmed
    error_message = "ADR-0022 prohibits AWS provisioning until its application prerequisites are implemented and tested."
  }
}

variable "alert_email" {
  description = "Email for operational and budget notifications. Leave null to create no subscriptions."
  type        = string
  default     = null
  nullable    = true

  validation {
    condition     = var.alert_email == null || can(regex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", var.alert_email))
    error_message = "alert_email must be null or a syntactically valid email address."
  }
}

variable "container_image_tag" {
  description = "Immutable commit SHA image tag used for both repositories."
  type        = string
  default     = "bootstrap"

  validation {
    condition     = var.container_image_tag == "bootstrap" || can(regex("^[0-9a-f]{40}$", var.container_image_tag))
    error_message = "container_image_tag must be bootstrap or a full 40-character Git commit SHA."
  }
}

variable "vpc_cidr" {
  description = "CIDR for the two-AZ ChangeOps VPC."
  type        = string
  default     = "10.44.0.0/16"

  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0)) && split("/", var.vpc_cidr)[1] == "16"
    error_message = "vpc_cidr must be a valid IPv4 /16."
  }
}

variable "database_name" {
  description = "Initial PostgreSQL database name."
  type        = string
  default     = "changeops"

  validation {
    condition     = can(regex("^[a-z][a-z0-9_]{0,62}$", var.database_name))
    error_message = "database_name must be a valid lowercase PostgreSQL identifier."
  }
}

variable "database_admin_username" {
  description = "Break-glass RDS master username. Its password is generated and managed by RDS."
  type        = string
  default     = "changeops_admin"

  validation {
    condition     = can(regex("^[a-zA-Z][a-zA-Z0-9_]{0,62}$", var.database_admin_username))
    error_message = "database_admin_username must be a valid PostgreSQL identifier."
  }
}

variable "allow_database_destroy" {
  description = "Explicitly disable RDS deletion protection for a separately reviewed teardown."
  type        = bool
  default     = false
}

variable "database_destroy_confirmation" {
  description = "Must exactly match environment when allow_database_destroy is true."
  type        = string
  default     = ""

  validation {
    condition     = !var.allow_database_destroy || var.database_destroy_confirmation == var.environment
    error_message = "database_destroy_confirmation must exactly match environment when database destruction is allowed."
  }
}

variable "database_final_snapshot_identifier" {
  description = "Final RDS snapshot identifier used only during intentional deletion; set a new unique value for each teardown."
  type        = string
  default     = "changeops-demo-final"

  validation {
    condition     = can(regex("^[a-zA-Z](?:[a-zA-Z0-9-]{0,253}[a-zA-Z0-9])?$", var.database_final_snapshot_identifier)) && !strcontains(var.database_final_snapshot_identifier, "--")
    error_message = "database_final_snapshot_identifier must be a valid RDS snapshot identifier."
  }
}

variable "enable_jira" {
  description = "Inject the Jira secret only after its complete dedicated value is populated."
  type        = bool
  default     = false
}

variable "enable_confluence" {
  description = "Inject the Confluence secret only after its complete dedicated value is populated."
  type        = bool
  default     = false
}

variable "jira_base_url" {
  description = "Non-secret Jira base URL."
  type        = string
  default     = ""
}

variable "jira_project_id_or_key" {
  description = "Non-secret Jira project identifier."
  type        = string
  default     = ""
}

variable "jira_issue_type_id" {
  description = "Non-secret Jira Task issue-type identifier."
  type        = string
  default     = ""
}

variable "confluence_base_url" {
  description = "Non-secret Confluence base URL."
  type        = string
  default     = ""
}

variable "confluence_manager_guide_page_id" {
  description = "Non-secret ID of the one permitted Confluence page."
  type        = string
  default     = ""
}

variable "web_health_check_path" {
  description = "Next.js health endpoint required before deployment."
  type        = string
  default     = "/healthz"

  validation {
    condition     = startswith(var.web_health_check_path, "/")
    error_message = "web_health_check_path must begin with /."
  }
}
