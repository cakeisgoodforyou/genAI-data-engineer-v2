"""
Executor Agent Flow:
1. check to see if call function = READ_FILE and if so invoke directly and return resullt (never reaches steps 2 or 3).
2. check to see if step is a ToolMessage and if so parse and return result 
3. If call_function != READ_FILE and no existing ToolMessage in last step, call LLM with prompt
"""
import json
import logging
from datetime import datetime
from langchain_core.messages import HumanMessage, ToolMessage
from state.state import AgentState, ExecutionRecord, CallFunction
from utils_llm.llm import get_llm
from utils.tools import AVAILABLE_TOOLS, read_file

logger = logging.getLogger(__name__)

llm_with_tools = get_llm("executor", tools=AVAILABLE_TOOLS)


def _get_output_content(latest_tool_result: ToolMessage, step) -> list:
    """
    read file functions invoked directly rather than tool handoff.
    done to ensure content is passed through correctly.
    """
    if step.call_function == CallFunction.READ_FILE:
        try:
            full_result = read_file.invoke(step.call_function_args)
            return [full_result]
        except Exception as e:
            logger.warning(f"Could not retrieve full file content: {e}")
    return [latest_tool_result.content]


def executor_agent(state: AgentState) -> dict:
    step = next((s for s in state.plan.steps if not s.completed and not s.failed), None)
    if not step:
        logger.info("No pending steps found")
        return {}
    logger.info(f"Executing step {step.step_id}: {step.call_function}")
    last_message = state.messages[-1] if state.messages else None

    # Handle read_file directly - bypass ToolNode to preserve bytes
    if step.call_function == CallFunction.READ_FILE and not isinstance(last_message, ToolMessage):
        try:
            full_result = read_file.invoke(step.call_function_args)
            record = ExecutionRecord(
                step_id=step.step_id,
                action_ref=str(step.call_function.value),
                started_at=datetime.utcnow(),
                finished_at=datetime.utcnow(),
                success=True,
                output_content=[full_result]
            )
            updated_steps = [
                s.model_copy(update={"completed": True}) if s.step_id == step.step_id else s
                for s in state.plan.steps
            ]
            logger.info(f"Step {step.step_id} completed via direct read_file invocation")
            return {
                "execution": {"executions": state.execution.executions + [record]},
                "plan": {**state.plan.model_dump(), "steps": [s.model_dump() for s in updated_steps]},
            }
        except Exception as e:
            logger.error(f"Step {step.step_id} read_file failed: {e}")
            updated_steps = [
                s.model_copy(update={"failed": True, "error": str(e)}) if s.step_id == step.step_id else s
                for s in state.plan.steps
            ]
            return {
                "plan": {**state.plan.model_dump(), "steps": [s.model_dump() for s in updated_steps]},
            }

    # Returning from ToolNode
    if isinstance(last_message, ToolMessage):
        failed = last_message.status == "error"
        success = not failed
        error_msg = None if success else last_message.content

        record = ExecutionRecord(
            step_id=step.step_id,
            action_ref=step.code.content[:100] if step.code else str(step.call_function.value),
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow(),
            success=success,
            error=error_msg,
            output_content=[last_message.content]
        )
        updated_steps = [
            s.model_copy(update={"completed": success, "failed": failed, "error": error_msg})
            if s.step_id == step.step_id else s
            for s in state.plan.steps
        ]
        logger.info(f"Step {step.step_id} {'completed' if success else 'failed'}")
        return {
            "execution": {"executions": state.execution.executions + [record]},
            "plan": {**state.plan.model_dump(), "steps": [s.model_dump() for s in updated_steps]},
        }

    # Ask LLM to make a tool call
    prompt = f"""Execute the following step using the available tools.
    Step ID: {step.step_id}
    Description: {step.description}
    Suggested tool: {step.call_function.value}
    Args: {json.dumps(step.call_function_args)}
    Code: {step.code.content if step.code else 'N/A'}
    Project ID: {state.meta.project_id}
    """
    messages = state.messages + [HumanMessage(content=prompt)]
    response = llm_with_tools.invoke(messages)

    if response.tool_calls:
        logger.info(f"Step {step.step_id} invoking tools: {[t['name'] for t in response.tool_calls]}")
        return {"messages": messages + [response]}

    logger.warning(f"Step {step.step_id} produced no tool calls")
    return {"messages": messages + [response]}