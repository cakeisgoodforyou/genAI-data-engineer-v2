"""Simplified approval notifications via Pub/Sub."""
import yaml
import json
import os
import logging
from datetime import datetime
from google.cloud import pubsub_v1
from state.state import AgentState
from utils.load_yaml_config import load_config

logger = logging.getLogger(__name__)

def send_approval_request(state: AgentState):
    project_id = load_config("config/agent_llm_config.yaml").get("defaults", {}).get("project_id")
    environment = os.getenv('ENVIRONMENT', 'dev')
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(
        project_id or state.meta.project_id, 
        f"approval-requests-{environment}"
    )
    
    message = {
        "request_id": state.meta.request_id,
        "timestamp": datetime.utcnow().isoformat(),
        "user_request": state.request.original_prompt,
        "state": state.model_dump(mode='json')
    }
    
    publisher.publish(topic_path, json.dumps(message).encode('utf-8'))
    logger.info(f"Approval request sent for {state.meta.request_id}")


def get_approval_response(state: AgentState, timeout: int = 300) -> dict:
    project_id = load_config("config/agent_llm_config.yaml").get("defaults", {}).get("project_id")
    environment = os.getenv('ENVIRONMENT', 'dev')
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(
        project_id or state.meta.project_id,
        f"approval-responses-pull-{environment}"
    )
    
    try:
        start_time = datetime.utcnow()
        while (datetime.utcnow() - start_time).total_seconds() < timeout:
            response = subscriber.pull(
                request={"subscription": subscription_path, "max_messages": 10},
                timeout=timeout
            )
            if not response.received_messages:
                continue
            for message in response.received_messages:
                data = json.loads(message.message.data.decode('utf-8'))
                
                if data.get("request_id") == state.meta.request_id:
                    subscriber.acknowledge(
                        request={"subscription": subscription_path, "ack_ids": [message.ack_id]}
                    )                    
                    if "action" not in data:
                        logger.warning(f"No action in response for {state.meta.request_id}")
                        return None
                    logger.info(f"Received {data['action']} for {state.meta.request_id}")
                    return data
                else:
                    subscriber.modify_ack_deadline(
                        request={
                            "subscription": subscription_path,
                            "ack_ids": [message.ack_id],
                            "ack_deadline_seconds": 300
                        }
                    )
        logger.error(f"Timeout waiting for approval response for {state.meta.request_id}")
        return None
    except Exception as e:
        logger.error(f"Error getting approval response: {e}")
        return None