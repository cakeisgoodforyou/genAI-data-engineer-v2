import logging
import json
from langchain_core.messages import AIMessage
from state.state import AgentState, CodeProposal, StepType, CallFunction
from agents.agent_utils import load_prompt_template, build_prompt, parse_json_response
from utils_llm.llm import call_llm, get_text_content
from utils.get_tool_descriptions import get_tools_description
from utils.tools import AVAILABLE_TOOLS

logger = logging.getLogger(__name__)

def load_generator_state_ref():
    with open("config/generator_state_ref.json") as f:
        return json.dumps(json.load(f), indent=2)

GENERATOR_STATE_REF = load_generator_state_ref()


def generator_agent(state: AgentState) -> dict:
    logger.info("Generator filling code for all EXECUTE steps")

    template = load_prompt_template("generator")
    prompt = build_prompt(template, {
        "available_tools": get_tools_description(AVAILABLE_TOOLS),
        "plan": state.plan.model_dump_json(),
        "user_request": state.request.original_prompt,
        "agent_state_ref": GENERATOR_STATE_REF
    })

    response = call_llm(agent_name="generator", prompt=prompt)
    raw_response = get_text_content(response)
    logger.info(f"Raw LLM response: {raw_response}")
    parsed_response = parse_json_response(raw_response)
    plan = parsed_response.get("plan")

    # Build updated steps using model_copy
    updated_steps = []
    for s in state.plan.steps:
        if s.step_type == StepType.EXECUTE:
            step_data = next((d for d in plan.get("steps", []) if d.get("step_id") == s.step_id), None)
            if step_data:
                s = s.model_copy(update={
                    "call_function": CallFunction(step_data["call_function"]) if step_data.get("call_function") else s.call_function,
                    "call_function_args": step_data.get("call_function_args", s.call_function_args),
                    "code": CodeProposal(**step_data["code"]) if step_data.get("code") else s.code
                })
        updated_steps.append(s)

    logger.info("Generator completed code generation")

    return {
        "plan": {
            **state.plan.model_dump(),
            "steps": [s.model_dump() for s in updated_steps]
        },
        "messages": state.messages + [AIMessage(content=raw_response)]
    }