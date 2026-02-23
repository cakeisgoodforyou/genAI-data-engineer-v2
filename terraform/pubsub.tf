# ============================================
# APPROVAL REQUEST TOPIC & SUBSCRIPTION
# ============================================

resource "google_pubsub_topic" "approval_requests" {
  name = "approval-requests-${var.environment}"
  labels = {
    environment = var.environment
    service     = var.service_name
    purpose     = "human-approval-requests"
  }
  message_retention_duration = "86400s"  # 24 hours
}

resource "google_pubsub_topic" "approval_requests_dlq" {
  name = "approval-requests-dlq-${var.environment}"
  labels = {
    environment = var.environment
    service     = var.service_name
    purpose     = "approval-requests-dlq"
  }
}

resource "google_pubsub_subscription" "approval_requests_pull" {
  name  = "approval-requests-pull-${var.environment}"
  topic = google_pubsub_topic.approval_requests.name
  
  message_retention_duration = "604800s"  # 7 days
  ack_deadline_seconds       = 600        # 10 minutes for human to respond
  
  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.approval_requests_dlq.id
    max_delivery_attempts = 5
  }
  
  labels = {
    environment = var.environment
    service     = var.service_name
    type        = "pull"
    purpose     = "human-approval"
  }
}

# ============================================
# APPROVAL RESPONSE TOPIC & SUBSCRIPTION
# ============================================

resource "google_pubsub_topic" "approval_responses" {
  name = "approval-responses-${var.environment}"
  labels = {
    environment = var.environment
    service     = var.service_name
    purpose     = "human-approval-responses"
  }
  message_retention_duration = "86400s"  # 24 hours
}

resource "google_pubsub_topic" "approval_responses_dlq" {
  name = "approval-responses-dlq-${var.environment}"
  labels = {
    environment = var.environment
    service     = var.service_name
    purpose     = "approval-responses-dlq"
  }
}

resource "google_pubsub_subscription" "approval_responses_pull" {
  name  = "approval-responses-pull-${var.environment}"
  topic = google_pubsub_topic.approval_responses.name
  
  message_retention_duration = "604800s"  # 7 days
  ack_deadline_seconds       = 20         # Workflow polls frequently
  
  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.approval_responses_dlq.id
    max_delivery_attempts = 5
  }
  
  labels = {
    environment = var.environment
    service     = var.service_name
    type        = "pull"
    purpose     = "workflow-polling"
  }
}

# ============================================
# IAM PERMISSIONS
# ============================================

# Grant Cloud Run service account permission to publish approval requests
resource "google_pubsub_topic_iam_member" "workflow_approval_request_publisher" {
  topic  = google_pubsub_topic.approval_requests.name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:${google_service_account.workflow_runner.email}"
}

# Grant Cloud Run service account permission to subscribe to approval responses
resource "google_pubsub_subscription_iam_member" "workflow_approval_response_subscriber" {
  subscription = google_pubsub_subscription.approval_responses_pull.name
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:${google_service_account.workflow_runner.email}"
}

# Grant Cloud Run service account permission to publish approval responses
# (needed for CLI running in Cloud Run or with this service account)
resource "google_pubsub_topic_iam_member" "workflow_approval_response_publisher" {
  topic  = google_pubsub_topic.approval_responses.name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:${google_service_account.workflow_runner.email}"
}

# Grant Cloud Run service account permission to subscribe to approval requests
# (needed for CLI or monitoring tools)
resource "google_pubsub_subscription_iam_member" "workflow_approval_request_subscriber" {
  subscription = google_pubsub_subscription.approval_requests_pull.name
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:${google_service_account.workflow_runner.email}"
}

# Optional: Grant domain group access (if var.domain is set)
resource "google_pubsub_subscription_iam_member" "human_approval_request_subscriber" {
  count        = var.domain != "" ? 1 : 0
  subscription = google_pubsub_subscription.approval_requests_pull.name
  role         = "roles/pubsub.subscriber"
  member       = "group:data-approvers@${var.domain}"
}

resource "google_pubsub_topic_iam_member" "human_approval_response_publisher" {
  count  = var.domain != "" ? 1 : 0
  topic  = google_pubsub_topic.approval_responses.name
  role   = "roles/pubsub.publisher"
  member = "group:data-approvers@${var.domain}"
}
