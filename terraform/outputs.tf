output "workflow_service_url" {
  description = "URL of the Cloud Run workflow service"
  value       = google_cloud_run_v2_service.workflow.uri
}

output "workflow_service_account" {
  description = "Email of the workflow service account"
  value       = google_service_account.workflow_runner.email
}

output "storage_bucket" {
  description = "GCS bucket for workflow data"
  value       = google_storage_bucket.workflow_data.name
}

output "artifact_registry_repository" {
  description = "Artifact Registry repository for container images"
  value       = google_artifact_registry_repository.workflow_images.id
}

output "approval_request_topic" {
  description = "Pub/Sub topic for approval requests"
  value       = google_pubsub_topic.approval_requests.id
}

output "approval_response_subscription" {
  description = "Pub/Sub subscription for approval responses"
  value       = google_pubsub_subscription.approval_responses_pull.id
}

output "docker_image_path" {
  description = "Full path for Docker image"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.workflow_images.repository_id}/${var.service_name}"
}
