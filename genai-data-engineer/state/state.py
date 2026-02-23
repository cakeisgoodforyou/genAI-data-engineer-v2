from langgraph.graph import StateGraph
from langchain_core.messages import BaseMessage
from typing import List, Optional, Dict, Any, Literal, Union
from pydantic import BaseModel, Field, field_validator
from enum import Enum
from datetime import datetime


class Approval(str, Enum):
    PENDING = "PENDING"
    GENERATION_APPROVED = "GENERATION_APPROVED"
    RECREATE_PLAN     = "RECREATE_PLAN"
    REFINE_GENERATION = "REFINE_GENERATION"
    EXECUTION_APPROVED = "EXECUTION_APPROVED"
    ENDWORKFLOW = "ENDWORKFLOW"
    PROCEED = "PROCEED"

class WorkflowStatus(str, Enum):
    RUNNING = "RUNNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    WAITING_PROCEED = "WAITING_PROCEED"
    COMPLETE = "COMPLETE"
    ERROR = "ERROR"

class StepType(str, Enum):
    ANALYZE  = "ANALYZE"
    EXECUTE  = "EXECUTE"
    AWAIT_PROCEED = "AWAIT_PROCEED"

class CallFunction(str, Enum):
    NONE               = "NONE"
    EXECUTE_QUERY      = "execute_query"
    GET_TABLE_SCHEMA   = "get_table_schema"
    GET_DATASET_SCHEMA = "get_dataset_schema"
    READ_FILE          = "read_file"
    WRITE_FILE         = "write_file"

class MetaState(BaseModel):
    request_id: str
    project_id: str
    plan_path: Optional[str] = None
    plan_loaded: bool = False
    schema_version: str = "0.1"
    status: WorkflowStatus = WorkflowStatus.RUNNING
    current_step_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    @field_validator("status", mode="before")
    def normalize_status(cls, v):
        if isinstance(v, str):
            try:
                return WorkflowStatus(v.upper())
            except ValueError:
                raise ValueError(f"Invalid WorkflowStatus: {v}")
        return v

class RequestState(BaseModel):
    original_prompt: str
    clarified_prompt: Optional[str] = None
    assumptions: List[str] = []

class CodeProposal(BaseModel):
    language: str #Literal["sql", "python", "shell"]
    content: str
    rationale: Optional[str] = None
    confidence: Optional[float] = None

class ErrorRefinement(BaseModel):
    description: str
    evidence: Optional[str] = None
    resolutions: Optional[str] = None

class PlanApproval(BaseModel):
    status: Approval = Approval.PENDING
    approved_at: Optional[datetime] = None
    human_feedback: Optional[str] = None
    @field_validator("status", mode="before")
    def normalize_approval_status(cls, v):
        if isinstance(v, str):
            try:
                return Approval(v.upper())
            except ValueError:
                raise ValueError(f"Invalid Approval: {v}")
        return v

class PlanStep(BaseModel):
    step_id: str
    step_type: StepType 
    description: str
    call_function: CallFunction = CallFunction.NONE
    call_function_args: Dict[str, Any] = Field(default_factory=dict)
    expected_outputs: List[str] = []
    execution_outputs_step_id: Optional[str] = None
    code: Optional[CodeProposal] = None
    completed: bool = False
    failed: bool = False
    error: Optional[str] = None
    error_refinement: Optional[ErrorRefinement] = None
    @field_validator("step_type", mode="before")
    def normalize_step_type(cls, v):
        if isinstance(v, str):
            try:
                return StepType(v.upper())
            except ValueError:
                raise ValueError(f"Invalid step_type: {v}")
        return v
    @field_validator("call_function", mode="before")
    def normalize_call_function(cls, v):
        if isinstance(v, CallFunction):
            return v  # already correct type, pass through
        if isinstance(v, str):
            try:
                return CallFunction(v)
            except ValueError:
                pass
            try:
                return CallFunction[v.upper()]
            except KeyError:
                raise ValueError(f"Invalid call_function: {v}")
        raise ValueError(f"Invalid call_function: {v}")

class PlanState(BaseModel):
    goal: Optional[str] = None
    agent_comments: Optional[str] = None
    steps: List[PlanStep] = []
    max_steps: int = 20
    version: int = 1
    approval: PlanApproval = Field(default_factory=PlanApproval)

class ExecutionOutput(BaseModel):
    type: str
    uri: str
    role: str
    description: str
    content: Optional[bytes] = None

class ExecutionRecord(BaseModel):
    step_id: str
    action_ref: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    success: bool = False
    error: Optional[str] = None
    output_content: List[Union[ExecutionOutput, str, Dict[str, Any]]]
    output_refs: List[str] = []
    @field_validator('output_content', mode='before')
    @classmethod
    def ensure_list(cls, v):
        if not isinstance(v, list):
            return [v]
        return v
    
class ExecutionState(BaseModel):
    executions: List[ExecutionRecord] = []
    blocked_reason: Optional[str] = None

class AnalysisSummary(BaseModel):
    summary: str
    recommendations: List[str] = []
    outputs: List[str] = []

class ResultsState(BaseModel):
    outputs: List[str] = []
    analysis: Optional[AnalysisSummary] = None

class FileLoadParameters(BaseModel):
    path: str

class FileWriteParameters(BaseModel):
    path: str
    content: Any
    format: str = "text"

class AgentState(BaseModel):
    meta: MetaState
    request: RequestState
    plan: PlanState = Field(default_factory=PlanState)
    execution: ExecutionState = Field(default_factory=ExecutionState)
    results: ResultsState = Field(default_factory=ResultsState)
    messages: List[BaseMessage] = Field(default_factory=list)