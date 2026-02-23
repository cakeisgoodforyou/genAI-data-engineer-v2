import logging
from state.state import AgentState, WorkflowStatus, Approval

logger = logging.getLogger(__name__)

def await_initial_approval(state: AgentState) -> AgentState:
    from utils.notifications import send_approval_request, get_approval_response
    logger.info(f"Awaiting initial plan approval for {state.meta.request_id}")
    
    if not state.plan.steps:
        logger.error("No steps in plan")
        state.meta.status = WorkflowStatus.ERROR
        return state
    
    state.meta.status = WorkflowStatus.WAITING_APPROVAL
    send_approval_request(state)
    response = get_approval_response(state)
    logger.info(f"approval response = {str(response)}")

    if not response:
        logger.error("No approval response received")
        state.meta.status = WorkflowStatus.ERROR
        return state
    action   = response.get("action")
    feedback = response.get("feedback")
    if action == "approve":
        state.plan.approval.status = Approval.GENERATION_APPROVED
    elif action == "recreate_plan":
        state.plan.approval.status = Approval.RECREATE_PLAN
        if feedback:
            state.plan.approval.human_feedback = feedback
    elif action == "reject":
        state.plan.approval.status = Approval.ENDWORKFLOW
        state.meta.status = WorkflowStatus.COMPLETE
    
    return state

def await_approval(state: AgentState) -> AgentState:
    from utils.notifications import send_approval_request, get_approval_response
    
    logger.info(f"Awaiting generation approval for {state.meta.request_id}")
    
    state.meta.status = WorkflowStatus.WAITING_APPROVAL
    send_approval_request(state)
    
    response = get_approval_response(state)
    
    if not response:
        logger.error("No approval response received")
        state.meta.status = WorkflowStatus.ERROR
        return state
    
    action = response.get("action")
    feedback = response.get("feedback")
    
    if action == "approve":
        state.plan.approval.status = Approval.EXECUTION_APPROVED
    elif action == "refine_generation":
        state.plan.approval.status = Approval.REFINE_GENERATION
        if feedback:
            state.plan.approval.human_feedback = feedback
    elif action == "recreate_plan":
        state.plan.approval.status = Approval.RECREATE_PLAN
        if feedback:
            state.plan.approval.human_feedback = feedback
    elif action == "reject":
        state.plan.approval.status = Approval.ENDWORKFLOW
        state.meta.status = WorkflowStatus.COMPLETE
    
    return state

def await_proceed(state: AgentState) -> AgentState:
    from utils.notifications import send_approval_request, get_approval_response
    
    logger.info(f"Awaiting proceed approval for {state.meta.request_id}")
    
    state.meta.status = WorkflowStatus.WAITING_PROCEED
    send_approval_request(state)
    
    response = get_approval_response(state)
    
    if not response:
        logger.error("No approval response received")
        state.meta.status = WorkflowStatus.ERROR
        return state
    
    action = response.get("action")
    
    if action == "proceed":
        state.plan.approval.status = Approval.PROCEED
    elif action == "reject":
        state.plan.approval.status = Approval.ENDWORKFLOW
        state.meta.status = WorkflowStatus.COMPLETE
    
    return state
