variable "project_id" {
  default = "genai-data-engineer"
  type        = string
}

variable "region" {
  description = "GCP region for resources"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "service_name" {
  description = "Base name for the service"
  type        = string
  default     = "data-dept"
}

variable "workflow_schedule" {
  description = "Cron schedule for workflow execution (default: daily at 9am UTC)"
  type        = string
  default     = "0 9 * * *"
}

variable "cloud_run_cpu" {
  description = "CPU allocation for Cloud Run service"
  type        = string
  default     = "1"
}

variable "cloud_run_memory" {
  description = "Memory allocation for Cloud Run service"
  type        = string
  default     = "512Mi"
}

variable "cloud_run_timeout" {
  description = "Timeout for Cloud Run service (seconds)"
  type        = number
  default     = 1800  # 30 minutes for approval workflows
}

variable "approval_timeout" {
  description = "Timeout for human approval (seconds)"
  type        = number
  default     = 1200  # 20 minutes
}

variable "domain" {
  description = "Domain for IAM group bindings (e.g., example.com)"
  type        = string
  default     = ""
}
