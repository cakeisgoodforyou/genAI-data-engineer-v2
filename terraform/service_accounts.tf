# Service account for workflow execution
resource "google_service_account" "workflow_runner" {
  account_id   = "${var.service_name}-workflow-${var.environment}"
  display_name = "Agentic Data Department Workflow Runner (${var.environment})"
  description  = "Service account for running agentic workflows"
}

# Grant necessary permissions
resource "google_project_iam_member" "workflow_bigquery_user" {
  project = var.project_id
  role    = "roles/bigquery.user"
  member  = "serviceAccount:${google_service_account.workflow_runner.email}"
}

resource "google_project_iam_member" "workflow_bigquery_data_editor" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.workflow_runner.email}"
}

resource "google_project_iam_member" "workflow_storage_admin" {
  project = var.project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${google_service_account.workflow_runner.email}"
}

resource "google_project_iam_member" "workflow_ai_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.workflow_runner.email}"
}
