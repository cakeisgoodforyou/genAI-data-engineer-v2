"""Shared utilities for all agents."""

import json
import yaml
import json_repair
import re
from pathlib import Path
from typing import Dict, Any

# Configuration paths
PROMPTS_DIR = Path("config/prompts")
AGENT_STATE_REF = Path("config/agent_state_ref.json")


def load_agent_state_ref() -> str:
    #Load agent state reference documentation
    with open(AGENT_STATE_REF) as f:
        return json.dumps(json.load(f), indent=2)


def load_prompt_template(agent_name: str) -> Dict[str, str]:
    #Load prompt template for a specific agent.
    prompt_file = PROMPTS_DIR / f"{agent_name}.yaml"
    with open(prompt_file) as f:
        return yaml.safe_load(f)


def build_prompt(template: Dict[str, str], variables: Dict[str, Any]) -> str:
    #Build a complete prompt from template and variables.
    system = template["system"].format(**variables)
    return f"{system}\n"


def clean_llm_response(response: str) -> str:
    cleaned = re.sub(
        r'^```(?:json|sql|python|shell|yaml)?\s*',
        '',
        response.strip(),
        flags=re.IGNORECASE | re.MULTILINE
    )
    cleaned = re.sub(r'```\s*$', '', cleaned, flags=re.MULTILINE)
    return cleaned.strip()

def parse_json_response(response: str) -> dict:
    cleaned = clean_llm_response(response)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        try:
            return json_repair.loads(cleaned)
        except Exception:
            raise ValueError(f"Could not parse JSON response: {cleaned[:200]}")

def parse_plan_steps(data: dict) -> list:
    # Parse plan steps from plan data dictionary using Pydantic validation"
    from state.state import PlanStep
    plan = data.get("plan", data)
    steps_data = plan.get("steps", [])
    return [PlanStep(**step_data) for step_data in steps_data]

# Load configuration once at module import
AGENT_STATE_REF = load_agent_state_ref()