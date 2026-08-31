# GenAI Enterprise Use Cases - Master Architecture Guide

This document details the architecture, component flow, and technical implementation for 20 Enterprise GenAI reference architectures.

---

## 1. Model Context Protocol (MCP) Server
**Goal:** Standardize AI agent interactions with external enterprise data sources using the open Model Context Protocol (MCP).

### Architecture
```mermaid
graph TD
    Client["AI Agent Client"] -->|1. JSON-RPC Request| Gateway["FastAPI MCP Gateway"]
    Gateway -->|2. Route to Tool| ToolManager["MCP Tool Manager"]
    ToolManager -->|3. Query Enterprise DB| Database["SQLite / Postgres DB"]
    Database -->|4. Tool Results| Formatter["MCP ToolResult Formatter"]
    Formatter -->|5. Standardized Response| Client
```

### Component Flow
1. **Client Request**: Agent sends a `call_tool` request (e.g., `get_customer_data`) via HTTP/SSE.
2. **Protocol Parsing**: Gateway parses and validates the JSON-RPC 2.0 message.
3. **Execution**: Server executes the corresponding Python tool function with parameter validation.
4. **Response**: Data is formatted as a standardized MCP `ToolResult` and returned to the agent.

---

## 2. Agent-to-Agent Communication (A2A)
**Goal:** Enable autonomous coordination between specialized agents using an Event-Driven architecture.

### Architecture
```mermaid
sequenceDiagram
    participant User as End User
    participant SupportAgent as Support Triage Agent
    participant Bus as Redis Event Bus
    participant OrderAgent as Order Fulfillment Agent
    User->>SupportAgent: Inquire about Order #123
    SupportAgent->>Bus: Publish request.order_info
    Bus->>OrderAgent: Deliver event to subscriber
    OrderAgent->>OrderAgent: Fetch order status from ERP
    OrderAgent->>Bus: Publish response.order_info
    Bus->>SupportAgent: Deliver payload to callback channel
    SupportAgent->>User: Return formatted status update
```

### Component Flow
1. **Event Trigger**: Source agent publishes a task/query to a Redis channel.
2. **Routing**: The message broker (Redis Pub/Sub) distributes the event to subscribed agents.
3. **Async Processing**: Target agent (`OrderAgent`) wakes up, processes the payload, and performs the task.
4. **Callback**: The result is published back to a response channel, allowing the original agent to proceed.

---

## 3. LangGraph Orchestrator
**Goal:** Build complex, stateful multi-agent workflows with cyclic loops and conditional routing.

### Architecture
```mermaid
graph LR
    StartNode["Input Query"] --> Router{"Router Agent"}
    Router -->|Document Analysis| Classifier["Document Classifier"]
    Router -->|Data Extraction| Extractor["Entity Extractor"]
    Classifier --> StateReducer["Shared State Container"]
    Extractor --> StateReducer
    StateReducer --> Evaluator{"Quality Evaluator"}
    Evaluator -->|Score < 0.85| Router
    Evaluator -->|Score >= 0.85| EndNode["Final Output"]
```

### Component Flow
1. **State Initialization**: A global `StateDict` is created with input data.
2. **Node Execution**: The graph executes nodes (Agents) based on current state.
3. **Conditional Edges**: Logic determines next step (e.g., "If confidence < 0.85, retry").
4. **Conclusion**: Workflow terminates when the `END` node is reached, returning final state.

---

## 4. Production RAG System
**Goal:** Enterprise-grade Retrieval-Augmented Generation with document ingestion and vector search.

### Architecture
```mermaid
graph TD
    Docs["PDF and Text Documents"] --> Ingestion["Text Chunking & Splitting"]
    Ingestion --> Embedder["Embedding Service"]
    Embedder --> VectorDB["Chroma / Qdrant Vector Store"]

    User["User Query"] --> QueryEngine["RAG Retrieval Chain"]
    QueryEngine -->|Semantic Similarity Search| VectorDB
    VectorDB -->|Retrieved Context Chunks| ContextBuilder["Context Prompt Builder"]
    ContextBuilder --> LLM["LLM Generation"]
    LLM --> Answer["Grounded Response"]
```

### Component Flow
1. **Ingestion**: Documents are chunked, embedded, and stored in a Vector DB.
2. **Retrieval**: User query is embedded; DB finds most similar chunks (Cosine Similarity).
3. **Synthesis**: Retrieved chunks + Query are fed into the LLM context window.
4. **Generation**: LLM generates a grounded response citing the source chunks.

---

## 5. Autonomous ReAct Agent
**Goal:** An agent capable of planning and executing multi-step goals using tools (ReAct Pattern).

### Architecture
```mermaid
graph TD
    Goal["User Goal"] --> Planner["Planning Engine"]
    Planner --> Loop{"Thought-Action Loop"}
    Loop -->|Select Tool| ToolDispatcher["Tool Interface"]
    ToolDispatcher -->|Execute API| Env["External Environment"]
    Env -->|Tool Observation| Reasoning["Reasoning Engine"]
    Reasoning -->|Update Context| Loop
    Loop -->|Goal Satisfied| Result["Final Answer"]
```

### Component Flow
1. **Plan**: Agent decomposes the user's high-level goal into steps.
2. **Action**: Agent selects a tool (Search, Calculator, API) to solve the current step.
3. **Observation**: Tool output is fed back into the agent's context.
4. **Refinement**: Agent iterates until the goal is satisfied.

---

## 6. Advanced Prompt Engineering Lab
**Goal:** Framework for managing, optimizing, and evaluating complex prompt strategies.

### Architecture
```mermaid
graph LR
    UserQuery["User Query"] --> Template["Prompt Template Engine"]
    Template --> Logic["Prompt Strategy Manager"]
    Logic --> LLM["LLM Inference"]
    LLM --> Eval["Evaluation & Scoring"]
    Eval -->|Optimization Feedback| Template
```

### Component Flow
1. **Templating**: Dynamic construction of prompts using Jinja2/f-strings.
2. **Strategy Selection**: Applying Zero-shot, Few-shot, or Chain-of-Thought patterns based on task.
3. **Evaluation**: Comparing outputs against a baseline to refine prompt phrasing.

---

## 7. LLMOps Pipeline
**Goal:** Automate the lifecycle of LLM applications including testing, deployment, and monitoring.

### Architecture
```mermaid
graph TD
    Code["Git Push"] --> CI["GitHub Actions Runner"]
    CI --> Lint["Ruff Lint & Type Check"]
    Lint --> Security["Bandit & Gitleaks Scan"]
    Security --> Pytest["Unit Tests (>85% Gate)"]
    Pytest --> Ragas["RAGAS Eval Benchmark"]
    Ragas -->|Pass (>=0.85)| CD["Deploy Canary Pods"]
    CD --> Prod["Production EKS Cluster"]
```

### Component Flow
1. **Commit**: Developer pushes code/prompt changes.
2. **CI Trigger**: GitHub Actions runs unit tests and LLM evaluations (Ragas).
3. **Gate**: Pipeline stops if accuracy drops below threshold.
4. **Deployment**: Successful builds are deployed to the production environment.

---

## 8. Vector Database Engine
**Goal:** Scalable storage and retrieval of high-dimensional embeddings.

### Architecture
```mermaid
graph TD
    RawData["Raw Documents"] --> Embedder["Embedding Service"]
    Embedder -->|Dense Vectors| QdrantCluster["Qdrant Vector Cluster"]
    QdrantCluster --> Index["HNSW Indexing Engine"]
    QueryVector["Query Vector"] --> Index
    Index -->|ANN Cosine Distance| RankedResults["Top-K Matching Chunks"]
```

### Component Flow
1. **Embedding**: Converting text/images into vector representations.
2. **Indexing**: Creating HNSW (Hierarchical Navigable Small World) graphs for fast search.
3. **Querying**: Performing Approximate Nearest Neighbor (ANN) search to find matches in milliseconds.

---

## 9. Hybrid Search System
**Goal:** Combine semantic understanding (Dense Retrieval) with keyword matching (Sparse Retrieval).

### Architecture
```mermaid
graph TD
    Query["User Query"] --> Dense["Vector Search (Semantic)"]
    Query --> Sparse["BM25 Search (Keyword)"]
    Dense --> DenseHits["Dense Score List"]
    Sparse --> SparseHits["Sparse Score List"]
    DenseHits --> RRF["Reciprocal Rank Fusion (RRF)"]
    SparseHits --> RRF
    RRF --> CrossEncoder["Cross-Encoder Reranker"]
    CrossEncoder --> FinalResults["Top-K Re-ranked Documents"]
```

### Component Flow
1. **Dual Retrieval**: Query is processed by both Vector DB and keyword engine (e.g., BM25).
2. **Normalization**: Scores from both systems are normalized (0-1).
3. **Fusion**: RRF algorithm combines lists to prioritize documents found by both methods.

---

## 10. AI Guardrails Gateway
**Goal:** Ensure safety, compliance, and quality control on Model Inputs and Outputs.

### Architecture
```mermaid
graph TD
    RawInput["User Input"] --> PII["PII / PHI Redactor (spaCy NER)"]
    PII -->|Cleaned Text| Sandbox["Prompt Injection Delimiter Guard"]
    Sandbox -->|Safe Payload| Model["LLM Inference Engine"]
    Model --> RawResponse["Model Response"]
    RawResponse --> SchemaValidator["Pydantic V2 Schema Gate"]
    SchemaValidator -->|Valid Schema| SafeOutput["Sanitized Response"]
    SchemaValidator -->|Validation Error| Fallback["Safe Refusal Handler"]
```

### Component Flow
1. **Input Rails**: Check for PII, toxic content, or forbidden topics before hitting the LLM.
2. **Generation**: LLM produces a draft response.
3. **Output Rails**: Verify response for hallucinations or policy violations (e.g., "Don't give financial advice").
4. **Action**: Block, redacted, or deliver the message.

---

## 11. Enterprise API Gateway
**Goal:** Unified API Gateway pattern to abstract diverse enterprise backends (Salesforce, ServiceNow, Slack).

### Architecture
```mermaid
graph TD
    ClientApp["Client Application"] -->|API Request| Gateway["FastAPI Gateway"]
    Gateway --> Auth["OAuth2 / JWT Claims Validator"]
    Auth --> CircuitBreaker["Circuit Breaker & Rate Limiter"]
    CircuitBreaker --> CRM["Salesforce Adapter"]
    CircuitBreaker --> ITSM["ServiceNow Adapter"]
    CircuitBreaker --> Slack["Slack API Adapter"]
    CRM --> Normalizer["Unified Response Normalizer"]
    ITSM --> Normalizer
    Slack --> Normalizer
    Normalizer --> ClientApp
```

### Component Flow
1. **Request**: Client sends a unified request (e.g., "Create Ticket").
2. **Auth**: Gateway verifies OAuth token.
3. **Routing**: Request routed to the specific backend adapter (ServiceNow).
4. **Resilience**: Circuit breaker wraps the call; retries on failure.
5. **Normalization**: Response transformed into a standard schema before returning.

---

## 12. Responsible AI & Explainability
**Goal:** Framework for fairness, bias detection, and explainability in model decisions.

### Architecture
```mermaid
graph LR
    InputData["Candidate Profile"] --> BiasEngine["Fairness & Bias Detector"]
    BiasEngine --> ModelInference["Decision Model"]
    ModelInference --> Prediction["Model Decision"]
    ModelInference --> SHAP["SHAP Feature Explainer"]
    SHAP --> AuditTrail["Immutable Compliance Audit Log"]
    Prediction --> AuditTrail
```

### Component Flow
1. **Pre-processing**: Analyze training data for disparate impact (e.g., Gender bias).
2. **Inference**: Model makes a prediction (e.g., "Hire Candidate").
3. **Explainability**: SHAP values are calculated to explain *why* (e.g., "Experience +5").
4. **Auditing**: Decision and explanation are logged for compliance.

---

## 13. RAGAS Quality Evaluation Pipeline
**Goal:** Automated quality assurance using RAGAS metrics (Faithfulness, Answer Relevance).

### Architecture
```mermaid
graph TD
    GoldenDataset["Golden Q&A Benchmark Dataset"] --> Evaluator["RAGAS Evaluation Engine"]
    RAGSystem["Production RAG Pipeline"] -->|Actual Responses| Evaluator
    Evaluator --> Metrics["Faithfulness & Relevance Scorer"]
    Metrics --> ThresholdGate{"Quality Gate (Score >= 0.85)"}
    ThresholdGate -->|Passed| ReleaseReport["Release Approval Dashboard"]
    ThresholdGate -->|Failed| Alert["Regression Alert & Block PR"]
```

### Component Flow
1. **Test Generation**: Load a "Golden Dataset" of questions and expected answers.
2. **Batch Inference**: Run the RAG system against the dataset to get actual answers.
3. **Scoring**: Use LLM-as-a-Judge (RAGAS) to score Faithfulness and Relevance.
4. **Reporting**: Generate an HTML report highlighting failing cases.

---

## 14. Cost Optimization & Semantic Caching
**Goal:** Reduce inference costs via Two-Tier Caching and Cascading Model Routing.

### Architecture
```mermaid
graph TD
    InboundQuery["User Query"] --> Cache{"Tier-1: Redis Semantic Cache"}
    Cache -->|Cache Hit (>0.92 Sim)| ReturnCached["Return Cached Response (<15ms, $0)"]
    Cache -->|Cache Miss| Router{"Tier-2: Cascading Model Router"}
    Router -->|Simple Query| SmallModel["Gemini 1.5 Flash / GPT-4o-mini"]
    Router -->|Complex Query| LargeModel["Claude 3.5 Sonnet / GPT-4o"]
    SmallModel --> Tracker["Cost Tracker & Cache Updater"]
    LargeModel --> Tracker
    Tracker --> UserResponse["Client Response"]
```

### Component Flow
1. **Check Cache**: Compute embedding of query; check for similar past queries.
2. **Cache Hit**: Return stored response immediately ($0 cost).
3. **Cache Miss**: Router analyzes query complexity.
4. **Inference**: Route to cheapest capable model.
5. **Update**: Log cost and update cache with new Q&A pair.

---

## 15. Dynamic Model Routing
**Goal:** Dynamically select the optimal LLM based on task complexity and context length.

### Architecture
```mermaid
graph TD
    Prompt["Inbound Prompt"] --> Scorer["Complexity & Code Heuristic Scorer"]
    Scorer --> Matcher["Registry Policy Matcher"]
    Matcher --> Registry["Foundation Model Registry"]
    Registry --> ExecutionEngine["LLM Execution Engine"]
    ExecutionEngine --> DecisionLogger["Routing Decision Telemetry"]
    DecisionLogger --> OutputResponse["Client Output"]
```

### Component Flow
1. **Analysis**: Scorer detects code, math, or long context in the query.
2. **Matching**: Router checks Model Registry capabilities (e.g., "Needs 100k context").
3. **Selection**: Picks the cheapest model that satisfies requirements.
4. **Logging**: Records specific routing decision for future tuning.

---

## 16. Human-in-the-Loop (HITL) Workflow
**Goal:** Human oversight and verification for high-stakes agent actions.

### Architecture
```mermaid
graph TD
    AgentProposal["Agent Action Proposal"] --> RiskEngine{"Risk Threshold Policy"}
    RiskEngine -->|Low Risk (Auto)| ExecutionNode["Execute Production Mutation"]
    RiskEngine -->|High Risk (Escalate)| EscalationQueue["Manager Approval Queue"]
    EscalationQueue --> HumanReviewer["Human Approver / Manager"]
    HumanReviewer -->|Approved| ExecutionNode
    HumanReviewer -->|Rejected| AbortNode["Abort Action & Log Audit Trail"]
    ExecutionNode --> Receipt["Transaction Confirmation Receipt"]
```

### Component Flow
1. **Proposal**: Agent proposes an action (e.g., "Transfer $50,000").
2. **Policy Check**: System detects amount > Threshold.
3. **Pause**: Execution suspends; request added to Approval Queue.
4. **Review**: Human manager approves via Dashboard/API.
5. **Resume**: Agent creates transaction receipt or aborts.

---

## 17. GraphRAG Knowledge Graph
**Goal:** GraphRAG for structured reasoning and multi-hop relationship traversal.

### Architecture
```mermaid
graph LR
    SourceDocs["Raw Unstructured Text"] --> Extractor["Entity-Relation Triple Extractor"]
    Extractor --> GraphStore["NetworkX / Neo4j Graph DB"]
    UserQuestion["User Question"] --> QuerySubGraph["2-Hop Subgraph Traversal"]
    GraphStore --> QuerySubGraph
    QuerySubGraph --> ContextPrompt["Augmented Structural Context"]
    ContextPrompt --> LLMReasoning["LLM Multi-Hop Reasoning"]
    LLMReasoning --> GroundedAnswer["Structured Graph-Grounded Answer"]
```

### Component Flow
1. **Ingestion**: Text is parsed into Subject-Verb-Object triples.
2. **Storage**: Entities and relationships stored in Graph DB.
3. **Retrieval**: Query entities mapped to graph nodes; 2-hop traversal fetches context.
4. **Reasoning**: LLM answers using the structural relationships found.

---

## 18. Event-Driven Agentic Architecture
**Goal:** Reactive agents capable of asynchronous processing via Message Bus.

### Architecture
```mermaid
graph TD
    OrderService["Order Ingestion Service"] -->|1. Publish Event| EventBus["Kafka Message Bus"]
    EventBus -->|2. Route to Topic| AgentConsumer["Worker Agent Consumer"]
    AgentConsumer -->|3. Async Processing| BusinessLogic["Autonomous Business Logic"]
    BusinessLogic -->|4. Emit Status| EventBus
    EventBus -->|5. Update CRM| DownstreamService["Downstream Notification Service"]
```

### Component Flow
1. **Event**: External system publishes `order.created`.
2. **Consumption**: Agent subscribes to topic and picks up message.
3. **Processing**: Agent validates order (Async/Non-blocking).
4. **Reaction**: Agent publishes `inventory.check` event for downstream services.

---

## 19. Full-Stack Observability & Tracing
**Goal:** Full operational visibility into agent operations (Logs, Metrics, Traces).

### Architecture
```mermaid
graph TD
    AgentApp["Agent Execution Engine"] --> Logger["JSON Structured Logger"]
    AgentApp --> Tracer["OpenTelemetry / Langfuse Tracer"]
    AgentApp --> Metrics["Prometheus Telemetry Client"]
    Logger --> LogAggregator["CloudWatch / Elastic Log Aggregator"]
    Tracer --> LangfuseUI["Langfuse Distributed Tracing UI"]
    Metrics --> Grafana["Grafana Real-Time SLO Dashboard"]
```

### Component Flow
1. **Instrumentation**: Agent code wrapped with Tracing spans and Metric counters.
2. **Execution**: Every request increments counters and logs JSON events.
3. **Scraping**: Prometheus scrapes `/metrics` endpoint.
4. **Analysis**: Dashboards visualize error rates, P99 latency, and token usage.

---

## 20. Cloud Infrastructure Deployment
**Goal:** Production-grade deployment on AWS EKS with Infrastructure-as-Code (Terraform).

### Architecture
```mermaid
graph TD
    DevCommit["Developer Git Push"] --> Pipeline["GitHub Actions CI/CD"]
    Pipeline --> DockerBuild["Build & Cosign Docker Image"]
    Pipeline --> Terraform["Terraform Cloud Provisioning"]
    Terraform --> EKSCluster["AWS EKS Kubernetes Cluster"]
    EKSCluster --> AgentPods["Horizontal Pod Autoscaler (HPA)"]
    AgentPods --> LoadBalancer["AWS ALB Ingress Controller"]
    LoadBalancer --> EndUsers["External Consumer Traffic"]
```

### Component Flow
1. **Build**: Docker container created from Source.
2. **Provision**: Terraform brings up VPC and EKS Cluster.
3. **Deploy**: Kubernetes manifests apply Deployment, Service, and HPA.
4. **Run**: Pods start, health checks pass, LoadBalancer exposes IP.
