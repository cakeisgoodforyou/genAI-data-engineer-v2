import logging
import json
from langchain_core.messages import AIMessage
from state.state import AgentState, ErrorRefinement, CodeProposal, CallFunction
from agents.agent_utils import load_prompt_template, build_prompt, parse_json_response
from utils_llm.llm import call_llm, get_text_content
from utils.get_tool_descriptions import get_tools_description
from utils.tools import AVAILABLE_TOOLS

logger = logging.getLogger(__name__)

def load_error_refiner_state_ref():
    with open("config/error_refiner_state_ref.json") as f:
        return json.dumps(json.load(f), indent=2)

ERROR_REFINER_STATE_REF = load_error_refiner_state_ref()


def error_refiner_agent(state: AgentState) -> dict:
    logger.info("Error refiner analyzing failed step")

    step = next((s for s in state.plan.steps if s.failed), None)
    if not step:
        logger.warning("Error refiner called but no failed step found")
        return {}

    template = load_prompt_template("error_refiner")
    prompt = build_prompt(template, {
        "step_description": step.description,
        "error_message": step.error,
        "code": step.code.content if step.code else "N/A",
        "agent_state_ref": ERROR_REFINER_STATE_REF
    })

    response = call_llm(agent_name="error_refiner", prompt=prompt)
    raw_response = get_text_content(response)
    logger.info(f"Raw LLM response: {raw_response}")
    refinements = parse_json_response(raw_response)

    error_refinement = ErrorRefinement(
        description=refinements.get("description"),
        evidence=refinements.get("evidence"),
        resolutions=refinements.get("resolutions")
    )

    updated_steps = [
        s.model_copy(update={
            "failed": False,
            "completed": False,
            "error": None,
            "error_refinement": error_refinement
        }) if s.step_id == step.step_id else s
        for s in state.plan.steps
    ]

    logger.info(f"Error analysis complete for step {step.step_id}")

    return {
        "plan": {
            **state.plan.model_dump(),
            "steps": [s.model_dump() for s in updated_steps]
        },
        "messages": state.messages + [AIMessage(content=raw_response)]
    }