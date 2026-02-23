# Artifact Registry repository for container images
resource "google_artifact_registry_repository" "workflow_images" {
  location      = var.region
  repository_id = "${var.service_name}-${var.environment}"
  description   = "Docker repository for agentic workflow containers"
  format        = "DOCKER"
  
  labels = {
    environment = var.environment
    service     = var.service_name
  }
}
