from datetime import datetime
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from state.state import AgentState, MetaState, RequestState, PlanState
from agents.orchestrator import orchestrator_agent
from agents.generator import generator_agent
from agents.analyzer import analyzer_agent
from agents.executor import executor_agent
from agents.error_refiner import error_refiner_agent
from utils.tools import AVAILABLE_TOOLS


from workflows.approval import await_initial_approval, await_approval, await_proceed
from workflows.routing import (
    route_after_initial_approval,
    route_after_approval,
    route_from_execution,
    route_from_step,
    route_from_proceed,
)

def build_workflow() -> StateGraph:

    graph = StateGraph(AgentState)
    
    graph.add_node("initial_plan", orchestrator_agent)
    graph.add_node("await_initial_approval", await_initial_approval)
    graph.add_node("generate", generator_agent)
    graph.add_node("await_approval", await_approval)
    graph.add_node("await_proceed", await_proceed)
    graph.add_node("analyze", analyzer_agent)
    graph.add_node("execute", executor_agent)
    graph.add_node("tools", ToolNode(AVAILABLE_TOOLS)) 
    graph.add_node("refine", error_refiner_agent)
    
    graph.set_entry_point("initial_plan")
    graph.add_edge("initial_plan", "await_initial_approval")
    graph.add_conditional_edges("await_initial_approval", route_after_initial_approval)
    graph.add_edge("generate", "await_approval")
    graph.add_conditional_edges("await_approval", route_after_approval)
    graph.add_conditional_edges("execute", route_from_execution)
    graph.add_edge("tools", "execute")
    graph.add_conditional_edges("analyze", route_from_step)
    graph.add_edge("refine", "await_approval")
    graph.add_conditional_edges("await_proceed", route_from_proceed)
    
    return graph.compile()

class WorkflowRunner:
    def __init__(self, config: dict):
        self.config = config
        self.workflow = build_workflow()

    def run(self, user_request: str, request_id: str, project_id: str, plan_path: str | None = None) -> dict:
        
        initial_state = AgentState(
            meta=MetaState(
                request_id=request_id,
                project_id=project_id,
                plan_path=plan_path,
                plan_loaded=False,
                created_at=datetime.utcnow()
            ),
            request=RequestState(
                original_prompt=user_request or "Loaded predefined plan"
            ),
            plan=PlanState()
        )
        
        result = self.workflow.invoke(initial_state)
        if isinstance(result, dict):
            final_state = AgentState(**result)
        else:
            final_state = result
        
        return {
            "status": final_state.meta.status,
            "plan": final_state.plan.model_dump(mode='json') if final_state.plan else None,
            "execution": final_state.execution.model_dump(mode='json') if final_state.execution else None,
            "results": final_state.results.model_dump(mode='json') if final_state.results else None
        }