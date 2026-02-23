#!/usr/bin/env python3
import argparse
import os
import sys
import json
from datetime import datetime
from google.cloud import pubsub_v1

def print_state_summary(state: dict):
    print(f"\n{'='*80}")
    print(f"APPROVAL REQUEST")
    print(f"{'='*80}")
    print(f"Request ID:  {state['meta']['request_id']}")
    print(f"Status:      {state['meta']['status']}")
    print(f"Created:     {state['meta']['created_at']}")
    print(f"\nUser Request:\n{state['request']['original_prompt']}")
    
    plan = state['plan']
    print(f"\n--- PLAN (Version {plan['version']}) ---")
    print(f"Goal: {plan.get('goal', 'N/A')}")
    print(f"Steps: {len(plan['steps'])}")
    
    for i, step in enumerate(plan['steps'], 1):
        print(f"\n  Step {i}: {step['step_id']}")
        print(f"    Type: {step['step_type']}")
        print(f"    Description: {step['description']}")
        print(f"    Function: {step.get('call_function', 'NONE')}")
        
        if step.get('code') and step['code'].get('content'):
            code = step['code']
            print(f"    Code ({code['language']}):")
            print(f"      {code['content'][:200]}{'...' if len(code['content']) > 200 else ''}")
            if code.get('rationale'):
                print(f"      Rationale: {code['rationale']}")
    
    print(f"\n{'='*80}\n")

def get_pending_approval(project_id: str, environment: str, request_id: str = None):
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(
        project_id,
        f"approval-requests-pull-{environment}"
    )
    
    response = subscriber.pull(
        request={"subscription": subscription_path, "max_messages": 10},
        timeout=5.0
    )
    
    if not response.received_messages:
        return None, None
    
    for message in response.received_messages:
        data = json.loads(message.message.data.decode('utf-8'))
        
        if request_id and data.get('request_id') != request_id:
            subscriber.modify_ack_deadline(
                request={
                    "subscription": subscription_path,
                    "ack_ids": [message.ack_id],
                    "ack_deadline_seconds": 0
                }
            )
            continue
        
        return data, message.ack_id
    
    return None, None

def send_approval_response(project_id: str, environment: str, request_id: str, action: str, feedback: str = None):
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(
        project_id,
        f"approval-responses-{environment}"
    )
    
    response_data = {
        "request_id": request_id,
        "action": action,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if feedback:
        response_data["feedback"] = feedback
    
    publisher.publish(topic_path, json.dumps(response_data).encode('utf-8'))

def acknowledge_message(project_id: str, environment: str, ack_id: str):
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(
        project_id,
        f"approval-requests-pull-{environment}"
    )
    subscriber.acknowledge(request={"subscription": subscription_path, "ack_ids": [ack_id]})

def determine_approval_stage(state: dict):
    has_code = any(step.get('code') for step in state['plan']['steps'])
    return 'generation' if has_code else 'initial'

def main():
    parser = argparse.ArgumentParser(description='Human approval tool for workflow')
    parser.add_argument('--environment', default=os.getenv('ENVIRONMENT', 'dev'))
    parser.add_argument('--project-id', default=os.getenv('PROJECT_ID'))
    parser.add_argument('--request-id', help='Filter by specific request ID (e.g., T001)')
    parser.add_argument('--auto-refresh', action='store_true')
    
    args = parser.parse_args()
    
    if not args.project_id:
        print("Error: PROJECT_ID required")
        sys.exit(1)
    
    print(f"\n{'*'*80}")
    print(f"  WORKFLOW APPROVAL CLI - {args.environment.upper()}")
    if args.request_id:
        print(f"  Filtering for Request ID: {args.request_id}")
    print(f"{'*'*80}\n")
    
    while True:
        approval_data, ack_id = get_pending_approval(args.project_id, args.environment, args.request_id)
        
        if not approval_data:
            msg = f"[{datetime.now().strftime('%H:%M:%S')}] No pending approvals"
            if args.request_id:
                msg += f" for {args.request_id}"
            print(msg)
            
            if args.auto_refresh:
                print("Checking again in 20 seconds... (Ctrl+C to exit)")
                try:
                    import time
                    time.sleep(20)
                    continue
                except KeyboardInterrupt:
                    print("\n\nExiting...")
                    sys.exit(0)
            else:
                sys.exit(0)
        
        state = approval_data['state']
        request_id = approval_data['request_id']
        
        print_state_summary(state)
        
        approval_stage = determine_approval_stage(state)
        
        if approval_stage == 'initial':
            print("\nOptions (Initial Plan):")
            print("  a - Approve (send to code generation)")
            print("  p - Recreate Plan (start over with feedback)")
            print("  x - Reject (end workflow)")
            print("  s - Skip (leave in queue)")
            
            decision = input("\nYour decision: ").strip().lower()
            
            if decision == 's':
                print("Skipping (message left in queue)")
                continue
            
            if decision not in ['a', 'p', 'x']:
                print("Invalid decision")
                continue
            
            action_map = {'a': 'approve', 'p': 'recreate_plan', 'x': 'reject'}
            action = action_map[decision]
            
        else:
            print("\nOptions (Generated Code):")
            print("  a - Approve (start execution)")
            print("  g - Refine Generation (regenerate code with feedback)")
            print("  p - Recreate Plan (start over with new plan)")
            print("  x - Reject (end workflow)")
            print("  s - Skip (leave in queue)")
            
            decision = input("\nYour decision: ").strip().lower()
            
            if decision == 's':
                print("Skipping (message left in queue)")
                continue
            
            if decision not in ['a', 'g', 'p', 'x']:
                print("Invalid decision")
                continue
            
            action_map = {'a': 'approve', 'g': 'refine_generation', 'p': 'recreate_plan', 'x': 'reject'}
            action = action_map[decision]
        
        feedback = None
        if action in ['refine_generation', 'recreate_plan']:
            feedback = input(f"\nProvide feedback (optional, press Enter to skip): ").strip()
        
        send_approval_response(
            args.project_id,
            args.environment,
            request_id,
            action,
            feedback if feedback else None
        )
        
        acknowledge_message(args.project_id, args.environment, ack_id)
        
        print(f"\n✓ {action.upper()} response sent successfully!")
        
        cont = input("\nCheck for another approval? (y/n): ").strip().lower()
        if cont != 'y':
            break
    
    print("\nExiting...")

if __name__ == "__main__":
    main()