# Cloud Run service for agentic workflows
resource "google_cloud_run_v2_service" "workflow" {
  name     = "${var.service_name}-workflow-${var.environment}"
  location = var.region
  
  template {
    service_account = google_service_account.workflow_runner.email
    
    containers {
      # Image will be pushed separately via CI/CD
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.workflow_images.repository_id}/agentic-${var.service_name}:latest"

      startup_probe {
        timeout_seconds = 10
        period_seconds  = 15
        failure_threshold = 20
        tcp_socket {
          port = 8080
        }
      }

      resources {
        limits = {
          cpu    = var.cloud_run_cpu
          memory = var.cloud_run_memory
        }
      }
      
      # Environment variables
      env {
        name  = "PROJECT_ID"
        value = var.project_id
      }
      
      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }
      
      env {
        name  = "GCS_BUCKET"
        value = google_storage_bucket.workflow_data.name
      }
      
      env {
        name  = "APPROVAL_TIMEOUT_SECONDS"
        value = tostring(var.approval_timeout)
      }
    }
    
    timeout = "${var.cloud_run_timeout}s"
    
    # Scaling
    scaling {
      min_instance_count = 0
      max_instance_count = 1  # Allow concurrent workflow executions
    }
  }
  
  # Traffic configuration
  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
  
  labels = {
    environment = var.environment
    service     = var.service_name
  }
  
  lifecycle {
    ignore_changes = [
      template[0].containers[0].image
    ]
  }
}
