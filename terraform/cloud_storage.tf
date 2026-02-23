# GCS bucket for workflow outputs and artifacts
resource "google_storage_bucket" "workflow_data" {
  name          = "${var.project_id}-${var.service_name}-${var.environment}"
  location      = var.region
  force_destroy = false
  
  uniform_bucket_level_access = true
  
  versioning {
    enabled = true
  }
  
  lifecycle_rule {
    condition {
      age = 90  # days
    }
    action {
      type = "Delete"
    }
  }
  
  labels = {
    environment = var.environment
    service     = var.service_name
    purpose     = "workflow-data"
  }
}

# Grant service account access to bucket
resource "google_storage_bucket_iam_member" "workflow_bucket_admin" {
  bucket = google_storage_bucket.workflow_data.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.workflow_runner.email}"
}
