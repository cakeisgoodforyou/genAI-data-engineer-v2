import logging
import yaml
import json
from langchain_core.messages import AIMessage
from state.state import AgentState, PlanStep, Approval
from utils_llm.llm import call_llm, get_text_content
from utils.load_json_from_gcs import load_json_from_gcs
from utils.get_tool_descriptions import get_tools_description
from agents.agent_utils import load_prompt_template, build_prompt, parse_json_response
from utils.tools import AVAILABLE_TOOLS

logger = logging.getLogger(__name__)

def load_orchestrator_state_ref():
    with open("config/orchestrator_state_ref.json") as f:
        return json.dumps(json.load(f), indent=2)

ORCHESTRATOR_STATE_REF = load_orchestrator_state_ref()

def orchestrator_agent(state: AgentState) -> dict:
    logger.info(f"Orchestrator creating plan for request: {state.meta.request_id}")

    if state.meta.plan_path and not state.meta.plan_loaded:
        logger.info(f"Loading predefined plan from: {state.meta.plan_path}")
        plan = load_json_from_gcs(state.meta.plan_path).get("plan")
        plan_loaded = True
        raw_response = "Loaded predefined plan"
    else:
        template = load_prompt_template("orchestrator")
        prompt = build_prompt(template, {
            "available_tools": get_tools_description(AVAILABLE_TOOLS),
            "user_request": state.request.original_prompt,
            "agent_state_ref": ORCHESTRATOR_STATE_REF
        })

        response     = call_llm(agent_name="orchestrator", prompt=prompt)
        raw_response = get_text_content(response)
        logger.info(f"Raw LLM response: {raw_response}")
        parsed_response = parse_json_response(raw_response)
        plan = parsed_response.get("plan")
        plan_loaded = False

    steps = [PlanStep(**step_data) for step_data in plan.get("steps", [])]
    logger.info(f"Created plan with {len(steps)} steps")

    return {
        "meta": {**state.meta.model_dump(), "plan_loaded": plan_loaded or state.meta.plan_loaded},
        "plan": {
            "steps": [s.model_dump() for s in steps],
            "goal": plan.get("goal"),
            "agent_comments": plan.get("agent_comments"),
            "approval": {"status": Approval.PENDING}
        },
        "messages": state.messages + [AIMessage(content=raw_response)]
    }