# 🧠 01. Stateful Multi-Agent StateGraph Architecture

[![Domain](https://img.shields.io/badge/Domain-Multi--Agent_Orchestration-blue.svg)](#)
[![Orchestrator](https://img.shields.io/badge/Engine-LangGraph_StateGraph-green.svg)](#)
[![Persistence](https://img.shields.io/badge/Persistence-PostgreSQL_%2F_Redis_Checkpointer-orange.svg)](#)
[![Governance](https://img.shields.io/badge/Governance-HITL_Approval_Gates-purple.svg)](#)

---

## 🏛️ Architectural Overview

In enterprise deployments, non-deterministic single-prompt agent loops fail under production SLAs due to context drift, unbounded loops, and lack of rollback capabilities. 

This architecture implements a **Stateful LangGraph StateGraph Pattern** with:
1. **Strongly-Typed State Channels:** Pydantic-enforced state boundaries ensuring memory monotonicity across node transitions.
2. **Deterministic Supervisor Routing:** Context-aware routing evaluating agent confidence, task dependencies, and policy constraints.
3. **Resilient Checkpointing:** Serializable snapshots persisted to PostgreSQL/Redis after every node execution for fault-recovery and time-travel debugging.
4. **Zero-Trust Human-in-the-Loop (HITL) Gates:** Asynchronous pause/resume mechanics for high-risk write operations (e.g., cloud resource mutation, financial transactions, database writes).

---

## 📐 System Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor User as Enterprise Operator
    participant Supervisor as Supervisor / Router Node
    participant Planner as Hierarchical Planner
    participant Worker as Specialized Worker Node
    participant HITL as HITL Approval Gate
    participant Store as Redis/Postgres Checkpointer

    User->>Supervisor: User Goal / Task Request
    Supervisor->>Store: Save State (Initial Checkpoint)
    Supervisor->>Planner: Request Decomposed Execution Plan
    Planner-->>Supervisor: Return ExecutionPlan (TaskSteps 1..N)
    Supervisor->>Store: Save State (Plan Checkpoint)

    loop For each TaskStep in ExecutionPlan
        Supervisor->>Worker: Dispatch Step Payload
        Worker->>Worker: Execute ReAct Loop / Tool Invocation
        Worker-->>Supervisor: Return StateDelta (intermediate_steps, context)
        Supervisor->>Store: Persist Node Checkpoint

        opt High-Risk Mutation Triggered
            Worker->>Supervisor: Flag request_human_approval = True
            Supervisor->>HITL: Suspend Graph Execution (Generate ApprovalToken)
            Supervisor->>User: Request Cryptographic Approval Signature
            User->>HITL: Approve Execution (Signed Token)
            HITL->>Supervisor: Resume Graph from Checkpoint
        end
    end

    Supervisor->>Supervisor: Synthesize Final Enterprise Response
    Supervisor->>Store: Persist Final State
    Supervisor-->>User: Structured Enterprise Output & Audit Trail
```

---

## 📂 Blueprint Files

* [`state_graph_blueprint.py`](./state_graph_blueprint.py): Complete, executable Pydantic V2 state schema, reducer functions, checkpointing interface, and routing simulation.

### Quick Verification
```bash
python 01_agentic_patterns/state_graph_blueprint.py
```

---

## 📊 Key Architectural Specifications

| Specification | Implementation Standard | Enterprise Benefit |
| :--- | :--- | :--- |
| **State Immutability** | Pydantic V2 Deep-Copy Reducers | Prevents race conditions in parallel subgraphs |
| **Fault Recovery** | Point-in-Time Checkpointer (`StateCheckpoint`) | Eliminates state loss during container restarts |
| **Loop Protection** | Monotonic `iteration_count` ceiling | Guards against unbounded token consumption |
| **Security Control** | Cryptographic Approval Tokens (`auth_req_*`) | Enforces separation of duties for mutating actions |
