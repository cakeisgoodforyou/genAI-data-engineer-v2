print(">>> module import start")

import os
import json
import logging
from flask import Flask, request, jsonify
from workflows.workflow import WorkflowRunner

# ---- Logging setup ----
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ---- App setup ----
app = Flask(__name__)
print(">>> flask app created")

config = {
    "approval_timeout": int(os.getenv("APPROVAL_TIMEOUT_SECONDS", "1200")),
    "max_retries": int(os.getenv("MAX_RETRIES", "2"))
}

# Lazy initialization - only create WorkflowRunner on first request
workflow_runner = None

# ---- Routes ----

@app.route("/health", methods=["GET"])
def health():
    return "ok", 200


@app.route("/run", methods=["POST"])
def run_workflow():
    """
    Expected JSON payload:
    {
      "id": "request-123",
      "prompt": "What are orders by region last week?"
      # OR
      "plan_path" : "gs://<my-bucket>/<path to file>.json"
    }
    """
    global workflow_runner
    
    # Initialize workflow runner on first request (lazy loading)
    if workflow_runner is None:
        logger.info("Initializing WorkflowRunner (first request)...")
        workflow_runner = WorkflowRunner(config)
        logger.info("WorkflowRunner initialized successfully")
    
    payload = request.get_json(silent=True)
    if not payload or "id" not in payload or ("prompt" not in payload and "plan_path" not in payload):
        return jsonify({"error": "Invalid request - missing id or prompt / plan_path"}), 400
    
    request_id = payload["id"]
    user_prompt = payload.get("prompt")
    plan_path = payload.get("plan_path")
    project_id = os.getenv("PROJECT_ID")
    
    if not project_id:
        return jsonify({"error": "PROJECT_ID not configured"}), 500

    try:
        logger.info(f"Starting workflow for request: {request_id}")
        result = workflow_runner.run(
            user_request=user_prompt,
            request_id=request_id,
            project_id=project_id,
            plan_path=plan_path
        )
        
        return jsonify({
            "status": result["status"],
            "request_id": request_id,
            "plan": result.get("plan"),
            "execution": result.get("execution"),
            "results": result.get("results")
        }), 200

    except Exception as e:
        logger.error(f"Workflow error: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "request_id": request_id,
            "error": str(e)
        }), 500


# ---- Entry point ----
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting Flask server on port {port}...")
    app.run(host="0.0.0.0", port=port)