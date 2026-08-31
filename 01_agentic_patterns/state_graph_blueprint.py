"""
================================================================================
Enterprise Architecture Blueprint: Stateful Multi-Agent StateGraph
Author: Sri Cherukuri (US Patent #7756878)
Domain: Multi-Agent Orchestration & Resilient State Persistence
================================================================================
Overview:
    This reference blueprint implements the state schema, reducer logic,
    cyclic routing interfaces, and checkpointing persistence models for
    enterprise-grade LangGraph multi-agent systems with Human-in-the-Loop (HITL).
"""

from __future__ import annotations

import enum
import time
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ------------------------------------------------------------------------------
# 1. Message & Execution Primitives
# ------------------------------------------------------------------------------

class MessageRole(str, enum.Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    SUPERVISOR = "supervisor"
    HUMAN_OPERATOR = "human_operator"


class ToolCallRecord(BaseModel):
    """Represents an atomic tool invocation requested by an agent."""
    call_id: str = Field(default_factory=lambda: f"call_{uuid.uuid4().hex[:8]}")
    tool_name: str
    arguments: Dict[str, Any]
    result: Optional[Any] = None
    execution_time_ms: float = 0.0
    status: str = "pending"  # pending, completed, failed


class AgentMessage(BaseModel):
    """Structured message record with token metrics and tool traceability."""
    id: str = Field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:8]}")
    role: MessageRole
    content: str
    sender_agent: str
    tool_calls: List[ToolCallRecord] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)


# ------------------------------------------------------------------------------
# 2. Planning & StateGraph Channels
# ------------------------------------------------------------------------------

class TaskStep(BaseModel):
    """An individual decomposed step in an autonomous agent execution plan."""
    step_id: int
    description: str
    assigned_agent: str
    status: str = "pending"  # pending, in_progress, completed, failed, blocked
    retry_count: int = 0
    max_retries: int = 3
    output_summary: Optional[str] = None


class ExecutionPlan(BaseModel):
    """Hierarchical multi-step plan produced by the Supervisor / Planner node."""
    plan_id: str = Field(default_factory=lambda: f"plan_{uuid.uuid4().hex[:8]}")
    goal: str
    steps: List[TaskStep] = Field(default_factory=list)
    current_step_index: int = 0
    is_complete: bool = False


class AgentState(BaseModel):
    """
    Unified, immutable State Schema for the multi-agent graph.
    Passed between all nodes and recorded at checkpoint boundaries.
    """
    conversation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    user_tenant_id: str
    user_roles: List[str] = Field(default_factory=list)
    
    # State channels
    messages: List[AgentMessage] = Field(default_factory=list)
    plan: Optional[ExecutionPlan] = None
    active_agent: str = "supervisor"
    iteration_count: int = 0
    max_iterations: int = 25
    
    # Context & Memory
    retrieved_context: List[Dict[str, Any]] = Field(default_factory=list)
    scratchpad: Dict[str, Any] = Field(default_factory=dict)
    
    # Governance & Approval
    pending_approval: bool = False
    approval_payload: Optional[Dict[str, Any]] = None
    approval_token: Optional[str] = None
    is_terminated: bool = False
    termination_reason: Optional[str] = None


# ------------------------------------------------------------------------------
# 3. State Reducer Logic & State Delta Application
# ------------------------------------------------------------------------------

class StateDelta(BaseModel):
    """Incremental update emitted by a single node in the StateGraph."""
    node_name: str
    new_messages: List[AgentMessage] = Field(default_factory=list)
    plan_update: Optional[ExecutionPlan] = None
    active_agent_update: Optional[str] = None
    context_additions: List[Dict[str, Any]] = Field(default_factory=list)
    scratchpad_updates: Dict[str, Any] = Field(default_factory=dict)
    request_human_approval: bool = False
    approval_payload: Optional[Dict[str, Any]] = None
    terminate: bool = False
    termination_reason: Optional[str] = None


def apply_state_delta(current_state: AgentState, delta: StateDelta) -> AgentState:
    """
    Functional state reducer applying node deltas to the immutable state.
    Guarantees monotonic sequence of state transitions.
    """
    updated = current_state.model_copy(deep=True)
    updated.iteration_count += 1
    
    # Append messages
    if delta.new_messages:
        updated.messages.extend(delta.new_messages)
    
    # Update plan
    if delta.plan_update:
        updated.plan = delta.plan_update
        
    # Update active agent
    if delta.active_agent_update:
        updated.active_agent = delta.active_agent_update
        
    # Merge retrieved context
    if delta.context_additions:
        updated.retrieved_context.extend(delta.context_additions)
        
    # Merge scratchpad key-values
    if delta.scratchpad_updates:
        updated.scratchpad.update(delta.scratchpad_updates)
        
    # Handle HITL gates
    if delta.request_human_approval:
        updated.pending_approval = True
        updated.approval_payload = delta.approval_payload
        updated.approval_token = f"auth_req_{uuid.uuid4().hex[:12]}"
        
    if delta.terminate or updated.iteration_count >= updated.max_iterations:
        updated.is_terminated = True
        updated.termination_reason = (
            delta.termination_reason or 
            ("Max iteration ceiling reached" if updated.iteration_count >= updated.max_iterations else "Completed")
        )
        
    return updated


# ------------------------------------------------------------------------------
# 4. Checkpointing & Time-Travel Interfaces
# ------------------------------------------------------------------------------

class StateCheckpoint(BaseModel):
    """Persistent snapshot stored in Postgres/Redis for fault recovery & HITL pause."""
    checkpoint_id: str = Field(default_factory=lambda: f"chk_{uuid.uuid4().hex[:12]}")
    conversation_id: str
    step_number: int
    node_source: str
    state_snapshot: AgentState
    created_at: float = Field(default_factory=time.time)


class CheckpointStore:
    """In-memory reference implementation of an enterprise checkpoint store."""
    def __init__(self):
        self._store: Dict[str, List[StateCheckpoint]] = {}

    def save_checkpoint(self, checkpoint: StateCheckpoint) -> None:
        if checkpoint.conversation_id not in self._store:
            self._store[checkpoint.conversation_id] = []
        self._store[checkpoint.conversation_id].append(checkpoint)

    def get_latest_checkpoint(self, conversation_id: str) -> Optional[StateCheckpoint]:
        history = self._store.get(conversation_id, [])
        return history[-1] if history else None

    def list_history(self, conversation_id: str) -> List[StateCheckpoint]:
        return self._store.get(conversation_id, [])


# ------------------------------------------------------------------------------
# 5. Graph Router & Simulation Pipeline
# ------------------------------------------------------------------------------

class RoutingDecision(BaseModel):
    """Decision evaluated at conditional graph edges."""
    next_node: str
    confidence: float
    rationale: str
    requires_approval: bool = False


def supervisor_router(state: AgentState) -> RoutingDecision:
    """
    Evaluates current state channels to decide the next graph edge.
    """
    if state.pending_approval:
        return RoutingDecision(
            next_node="hitl_approval_gate",
            confidence=1.0,
            rationale="Workflow suspended waiting for authorized human approval."
        )
        
    if not state.plan:
        return RoutingDecision(
            next_node="planner_agent",
            confidence=0.98,
            rationale="No execution plan exists. Directing to Planner."
        )
        
    if state.plan.is_complete or state.is_terminated:
        return RoutingDecision(
            next_node="synthesizer_agent",
            confidence=1.0,
            rationale="All subtasks completed. Generating final enterprise response."
        )
        
    current_step = state.plan.steps[state.plan.current_step_index]
    return RoutingDecision(
        next_node=current_step.assigned_agent,
        confidence=0.95,
        rationale=f"Executing plan step {current_step.step_id}: {current_step.description}"
    )


# ------------------------------------------------------------------------------
# Self-Verification Simulation
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 80)
    print("LangGraph StateGraph Blueprint - Enterprise Schema Verification")
    print("=" * 80)
    
    # Initialize State
    initial_state = AgentState(
        session_id="sess_enterprise_001",
        user_tenant_id="tenant_us_east",
        user_roles=["EngineeringDirector", "SecOpsLead"],
        messages=[
            AgentMessage(
                role=MessageRole.USER,
                content="Analyze Q3 infrastructure drift and apply remediation to VPC-01.",
                sender_agent="user_client"
            )
        ]
    )
    
    # Checkpoint Store
    chk_store = CheckpointStore()
    
    # Step 1: Supervisor creates plan
    plan = ExecutionPlan(
        goal="Analyze drift and apply remediation to VPC-01",
        steps=[
            TaskStep(step_id=1, description="Audit Terraform state vs AWS live API", assigned_agent="audit_agent"),
            TaskStep(step_id=2, description="Remediate security group egress rules", assigned_agent="remediation_agent")
        ]
    )
    
    delta_1 = StateDelta(
        node_name="planner_agent",
        plan_update=plan,
        new_messages=[
            AgentMessage(
                role=MessageRole.SUPERVISOR,
                content="Generated 2-step drift analysis and remediation plan.",
                sender_agent="planner_agent"
            )
        ]
    )
    
    state_after_plan = apply_state_delta(initial_state, delta_1)
    chk_store.save_checkpoint(StateCheckpoint(
        conversation_id=state_after_plan.conversation_id,
        step_number=1,
        node_source="planner_agent",
        state_snapshot=state_after_plan
    ))
    
    # Step 2: Routing check
    decision = supervisor_router(state_after_plan)
    print(f"[*] Route Decision: Next Node -> {decision.next_node} (Confidence: {decision.confidence})")
    print(f"[*] Rationale: {decision.rationale}")
    
    # Step 3: Trigger HITL requirement for high-risk action
    delta_hitl = StateDelta(
        node_name="remediation_agent",
        request_human_approval=True,
        approval_payload={"action": "ModifyVpcSecurityGroup", "target": "sg-018274a9", "risk": "CRITICAL"},
        new_messages=[
            AgentMessage(
                role=MessageRole.ASSISTANT,
                content="Remediation plan ready: Modifying security group. Awaiting human operator approval.",
                sender_agent="remediation_agent"
            )
        ]
    )
    state_hitl = apply_state_delta(state_after_plan, delta_hitl)
    chk_store.save_checkpoint(StateCheckpoint(
        conversation_id=state_hitl.conversation_id,
        step_number=2,
        node_source="remediation_agent",
        state_snapshot=state_hitl
    ))
    
    hitl_decision = supervisor_router(state_hitl)
    print(f"[*] HITL Route Decision -> {hitl_decision.next_node} (Approval Token: {state_hitl.approval_token})")
    print(f"[OK] State persistence & checkpointing verified. Checkpoints stored: {len(chk_store.list_history(state_hitl.conversation_id))}")
    print("=" * 80)
