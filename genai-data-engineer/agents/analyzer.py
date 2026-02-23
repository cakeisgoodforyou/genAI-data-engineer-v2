import logging
import json
from langchain_core.messages import AIMessage
from state.state import AgentState, AnalysisSummary
from agents.agent_utils import load_prompt_template, build_prompt, parse_json_response
from utils_llm.llm import call_llm, get_text_content

logger = logging.getLogger(__name__)

def load_analyzer_state_ref():
    with open("config/analyzer_state_ref.json") as f:
        return json.dumps(json.load(f), indent=2)

ANALYZER_STATE_REF = load_analyzer_state_ref()

def analyzer_agent(state: AgentState) -> dict:
    logger.info("Analyzer analyzing results for current step")
    step = next((s for s in state.plan.steps if not s.completed and not s.failed), None)
    if not step:
        logger.warning("Analyzer called but no pending step found")
        return {}
    
    logger.info(f"STEP_ID = {step.step_id}")

    execution = next((e for e in state.execution.executions if e.step_id == step.execution_outputs_step_id), None)
    if execution:
        outputs = [
            o.model_dump() if hasattr(o, "model_dump") else o
            for o in execution.output_content
        ]
        logger.info(f"EXECUTION OUTPUTS = {outputs}")
    else:
        outputs = []
        logger.info(f"No execution found for step {step.step_id}")

    template = load_prompt_template("analyzer")
    prompt = build_prompt(template, {
        "step_description": step.description,
        "outputs": outputs,
        "context": state.request.original_prompt,
        "agent_state_ref": ANALYZER_STATE_REF
    })

    response = call_llm(agent_name="analyzer", prompt=prompt)
    raw_response = get_text_content(response)
    logger.info(f"Raw LLM response: {raw_response}")
    analysis_data = parse_json_response(raw_response)

    updated_steps = [
        s.model_copy(update={"completed": True}) if s.step_id == step.step_id else s
        for s in state.plan.steps
    ]

    logger.info(f"Analysis complete for step {step.step_id}")

    return {
        "results": {
            "analysis": AnalysisSummary(**analysis_data),
            "outputs": state.results.outputs
        },
        "plan": {
            **state.plan.model_dump(),
            "steps": [s.model_dump() for s in updated_steps]
        },
        "messages": state.messages + [AIMessage(content=raw_response)]
    }