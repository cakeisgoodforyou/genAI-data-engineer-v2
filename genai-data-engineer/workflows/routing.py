from langgraph.graph import END
from langchain_core.messages import AIMessage
from state.state import AgentState, Approval, StepType

def get_current_step(state: AgentState):
    return next((s for s in state.plan.steps if not s.completed and not s.failed), None)

def route_after_initial_approval(state: AgentState) -> str:
    status = state.plan.approval.status
    
    if status == Approval.GENERATION_APPROVED:
        return "generate"
    if status == Approval.RECREATE_PLAN:
        return "initial_plan"
    if status == Approval.ENDWORKFLOW:
        return END
    
    return END

def route_after_approval(state: AgentState) -> str:
    status = state.plan.approval.status
    
    if status == Approval.EXECUTION_APPROVED:
        step = get_current_step(state)
        if not step:
            return END
        
        if step.step_type == StepType.EXECUTE:
            return "execute"
        if step.step_type == StepType.ANALYZE:
            return "analyze"
        if step.step_type == StepType.AWAIT_PROCEED:
            return "await_proceed"
        
        return END
    
    if status == Approval.REFINE_GENERATION:
        return "generate"
    if status == Approval.RECREATE_PLAN:
        return "initial_plan"
    if status == Approval.ENDWORKFLOW:
        return END
    
    return END


def route_from_execution(state: AgentState) -> str:
    # If executor made tool calls, go to tools node first
    last_message = state.messages[-1] if state.messages else None
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"
    
    step = get_current_step(state)
    if step and step.failed:
        return "refine"
    
    next_step = get_current_step(state)
    if not next_step:
        return END

    if next_step.step_type == StepType.EXECUTE:
        return "execute"
    if next_step.step_type == StepType.ANALYZE:
        return "analyze"
    if next_step.step_type == StepType.AWAIT_PROCEED:
        return "await_proceed"

    return END

def route_from_step(state: AgentState) -> str:
    step = get_current_step(state)
    if not step:
        return END
    
    if step.step_type == StepType.EXECUTE:
        return "execute"
    if step.step_type == StepType.ANALYZE:
        return "analyze"
    if step.step_type == StepType.AWAIT_PROCEED:
        return "await_proceed"
    
    return END

def route_from_proceed(state: AgentState) -> str:
    status = state.plan.approval.status
    
    if status == Approval.PROCEED:
        step = get_current_step(state)
        
        next_step = get_current_step(state)
        if not next_step:
            return END
        
        if next_step.step_type == StepType.EXECUTE:
            return "execute"
        if next_step.step_type == StepType.ANALYZE:
            return "analyze"
        if next_step.step_type == StepType.AWAIT_PROCEED:
            return "await_proceed"
        
        return END
    
    if status == Approval.ENDWORKFLOW:
        return END
    
    return END