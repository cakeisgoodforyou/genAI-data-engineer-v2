## Cloud Scheduler job to trigger workflows
#resource "google_cloud_scheduler_job" "workflow_trigger" {
#  name        = "${var.service_name}-workflow-trigger-${var.environment}"
#  description = "Scheduled workflow execution"
#  schedule    = var.workflow_schedule
#  time_zone   = "UTC"
#  region      = var.region
#  
#  http_target {
#    uri         = "${google_cloud_run_v2_service.workflow.uri}/run"
#    http_method = "POST"
#    
#    headers = {
#      "Content-Type" = "application/json"
#    }
#    
#    body = base64encode(jsonencode({
#      id     = "scheduled-${var.environment}"
#      prompt = "Run scheduled workflow"
#    }))
#    
#    oidc_token {
#      service_account_email = google_service_account.workflow_runner.email
#      audience              = google_cloud_run_v2_service.workflow.uri
#    }
#  }
#}
