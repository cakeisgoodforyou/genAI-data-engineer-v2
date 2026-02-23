"""
Local runner - bypasses Flask for local development and testing.
Usage:
    python run_local.py --prompt "your prompt here"
    python run_local.py --plan_path "gs://bucket/path/plan.json"
"""

import os
import json
import logging
import argparse
import uuid
from dotenv import load_dotenv
from workflows.workflow import WorkflowRunner

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Run the data engineering workflow locally")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prompt", type=str, help="Natural language prompt for the workflow")
    group.add_argument("--plan_path", type=str, help="GCS path to a predefined plan JSON")
    parser.add_argument("--project_id", type=str, help="GCP project ID (overrides PROJECT_ID env var)")
    parser.add_argument("--request_id", type=str, help="Optional request ID (auto-generated if not provided)")
    args = parser.parse_args()

    project_id = args.project_id or os.getenv("PROJECT_ID")
    if not project_id:
        raise ValueError("PROJECT_ID must be set via --project_id arg or PROJECT_ID env var")

    request_id = args.request_id or str(uuid.uuid4())

    config = {
        "approval_timeout": int(os.getenv("APPROVAL_TIMEOUT_SECONDS", "1200")),
        "max_retries": int(os.getenv("MAX_RETRIES", "2"))
    }

    logger.info(f"Starting local workflow run — request_id: {request_id}")

    runner = WorkflowRunner(config)
    result = runner.run(
        user_request=args.prompt,
        request_id=request_id,
        project_id=project_id,
        plan_path=args.plan_path
    )

    print("\n--- RESULT ---")
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()