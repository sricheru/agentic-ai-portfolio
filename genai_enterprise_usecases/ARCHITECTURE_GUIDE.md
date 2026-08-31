# GenAI Enterprise Use Cases - Master Architecture Guide

This document details the architecture, component flow, and technical implementation for 20 Enterprise GenAI projects.

---

## 1. Model Context Protocol (MCP) Server
**Goal:** Standardize AI agent interactions with external data sources using the open MCP standard.

### Architecture
```mermaid
graph TD
    Client["AI Agent Client"] -->|JSON-RPC Request| API[FastAPI Server]
    API -->|Route Handler| Manager[MCP Manager]
    Manager -->|Query| DB["SQLite Database"]
    DB -->|Result| Manager
    Manager -->|JSON-RPC Response| Client
```

### Component Flow
1. **Client Request**: Agent sends a `call_tool` request (e.g., `get_customer_data`) via HTTP/SSE.
2. **Protocol Parsing**: `mcp_server` parses the JSON-RPC message.
3. **Execution**: Server executes the corresponding Python function (e.g., querying CRM database).
4. **Response**: Data is formatted as an MCP `ToolResult` and sent back to the agent.

---

## 2. Agent-to-Agent Communication
**Goal:** Enable autonomous coordination between specialized agents using an Event-Driven architecture.

### Architecture
```mermaid
sequenceDiagram
    participant User
    participant SupportAgent
    participant Redis as Redis Pub/Sub
    participant OrderAgent
    User->>SupportAgent: "Where is my order #123?"
    SupportAgent->>Redis: Publish event: request.order_info
    Redis->>OrderAgent: Deliver event
    OrderAgent->>OrderAgent: Fetch Order Status
    OrderAgent->>Redis: Publish event: response.order_info
    Redis->>SupportAgent: Deliver response
    SupportAgent->>User: "Your order is shipped."
```

### Component Flow
1. **Event Trigger**: Source agent publishes a task/query to a Redis channel.
2. **Routing**: The message broker (Redis) distributes the event to subscribed agents.
3. **Async Processing**: Target agent (`OrderAgent`) wakes up, processes the payload, and performs the task.
4. **Callback**: The result is published back to a response channel, allowing the original agent to proceed.

---

## 3. LangGraph Orchestrator
**Goal:** Build complex, stateful multi-agent workflows with cyclic loops and conditional routing.

### Architecture
```mermaid
graph LR
    Start --> Router{Router Node}
    Router -->|Doc Analysis| Classifier[Classifier Agent]
    Router -->|Extraction| Extractor[Extractor Agent]
    Classifier --> State[Shared State]
    Extractor --> State
    State -->|Update| Router
    Router -->|Done| EndNode["End"]
```

### Component Flow
1. **State Initialization**: A global `StateDict` is created with input data.
2. **Node Execution**: The graph executes nodes (Agents) based on current state.
3. **Conditional Edges**: Logic determines next step (e.g., "If confidence < 0.8, retry").
4. **Conclusion**: Workflow terminates when the `END` node is reached, returning final state.

---

## 4. Production RAG System
**Goal:** Enterprise-grade Retrieval-Augmented Generation with document ingestion and vector search.

### Architecture
```mermaid
graph TD
    Docs["PDF and Text Documents"] -->|Ingest| Splitter[Text Splitter]
    Splitter -->|Embed| Model[Embedding Model]
    Model -->|Upsert| VectorDB["Chroma and Qdrant Vector Store"]
    User -->|Query| Chain[RAG Chain]
    Chain -->|Search| VectorDB
    VectorDB -->|Context| Chain
    Chain -->|Prompt| LLM
    LLM -->|Answer| User
```

### Component Flow
1. **Ingestion**: Documents are chunked, embedded, and stored in a Vector DB.
2. **Retrieval**: User query is embedded; DB finds most similar chunks (Cosine Similarity).
3. **Synthesis**: Retrieved chunks + Query are fed into the LLM context window.
4. **Generation**: LLM generates a grounded response citing the source chunks.

---

## 5. Autonomous Agent
**Goal:** An agent capable of planning and executing multi-step goals using tools (ReAct Pattern).

### Architecture
```mermaid
graph TD
    Goal[User Goal] --> Planner[Planning Engine]
    Planner -->|Thought| Loop{Execution Loop}
    Loop -->|Action| Tool[Tool Interface]
    Tool -->|Observation| Loop
    Loop -->|Reasoning| Loop
    Loop -->|Final Answer| Result
```

### Component Flow
1. **Plan**: Agent decomposes the user's high-level goal into steps.
2. **Action**: Agent selects a tool (Search, Calculator, API) to solve the current step.
3. **Observation**: Tool output is fed back into the agent's context.
4. **Refinement**: Agent iterates until the goal is satisfied.

---

## 6. Advanced Prompt Engineering
**Goal:** Framework for managing, optimizing, and evaluating complex prompt strategies.

### Architecture
```mermaid
graph LR
    User --> Template[Prompt Template]
    Template -->|Inject Variables| Logic[Prompt Manager]
    Logic -->|Chain-of-Thought| LLM
    LLM -->|Result| Eval[Evaluation]
    Eval -->|Feedback| Logic
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
    Code[Git Repo] -->|Push| CI[GitHub Actions]
    CI -->|Test| Pytest[Unit Tests]
    CI -->|Eval| Ragas[Quality Eval]
    Ragas -->|Pass| CD[Deploy]
    CD -->|Update| Prod[Production Env]
```

### Component Flow
1. **Commit**: Developer pushes code/prompt changes.
2. **CI Trigger**: GitHub Actions runs unit tests and LLM evaluations (Ragas).
3. **Gate**: Pipeline stops if accuracy drops below threshold.
4. **Deployment**: Successful builds are deployed to the production environment.

---

## 8. Vector Database Implementation
**Goal:** Scalable storage and retrieval of high-dimensional embeddings.

### Architecture
```mermaid
graph TD
    Data --> Embedder[Embedding Service]
    Embedder -->|Vectors| Qdrant["Qdrant Cluster"]
    Qdrant -->|HNSW Index| Storage
    Query -->|Search| Qdrant
    Qdrant -->|ANN| Results
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
    Query --> Dense["Vector Search Semantic"]
    Query --> Sparse["BM25 Keyword Search"]
    Dense --> Results1
    Sparse --> Results2
    Results1 --> Fusion[Reciprocal Rank Fusion]
    Results2 --> Fusion[Reciprocal Rank Fusion]
    Fusion --> Final[Ranked List]
```

### Component Flow
1. **Dual Retrieval**: Query is processed by both Vector DB and keyword engine (e.g., BM25).
2. **Normalization**: Scores from both systems are normalized (0-1).
3. **Fusion**: RRF (Reciprocal Rank Fusion) algorithm combines lists to prioritize documents found by both methods.

---

## 10. AI Guardrails
**Goal:** Ensure safety, compliance, and quality control on Model Inputs and Outputs.

### Architecture
```mermaid
graph TD
    Input --> PII[PII Detector]
    PII -->|Pass| Topics[Topic Filter]
    Topics -->|Pass| LLM
    LLM --> LLMOutput["Model Output"]
    LLMOutput["Model Output"] --> Hallucination[Fact Checker]
    Hallucination -->|Safe| User
    Hallucination -->|Unsafe| Block[Refusal Message]
```

### Component Flow
1. **Input Rails**: Check for PII, toxic content, or forbidden topics before hitting the LLM.
2. **Generation**: LLM produces a draft response.
3. **Output Rails**: Verify response for hallucinations or policy violations (e.g., "Don't give financial advice").
4. **Action**: Block, redacted, or deliver the message.

---

*(Continued in Part 2...)*

## 11. Enterprise API
**Goal:** Unified API Gateway pattern to abstract diverse enterprise backends (Salesforce, ServiceNow, Slack).

### Architecture
```mermaid
graph TD
    Client -->|API Request| Gateway[FastAPI Gateway]
    Gateway -->|Auth| OAuth[OAuth2 Manager]
    Gateway -->|Circuit Breaker| Service
    Service -->|Retries| CRM[Salesforce Mock]
    Service -->|Retries| ITSM[ServiceNow Mock]
    Service -->|Retries| Chat[Slack Mock]
    CRM --> |Response| Gateway
    ITSM --> |Response| Gateway
    Chat --> |Response| Gateway
    Gateway -->|Unified JSON| Client
```

### Component Flow
1. **Request**: Client sends a unified request (e.g., "Create Ticket").
2. **Auth**: Gateway verifies OAuth token.
3. **Routing**: Request routed to the specific backend adapter (ServiceNow).
4. **Resilience**: Circuit breaker wraps the call; retries on failure.
5. **Normalization**: Response transformed into a standard schema before returning.

---

## 12. Responsible AI
**Goal:** Framework for fairness, bias detection, and explainability in model decisions.

### Architecture
```mermaid
graph LR
    Data --> Bias[Bias Detector]
    Bias -->|Fairness Metrics| Dashboard
    Data --> Model[Hiring Model]
    Model --> Prediction
    Model --> Explainer[SHAP Explainer]
    Explainer -->|Feature Importance| Audit[Audit Log]
    Prediction --> Audit
```

### Component Flow
1. **Pre-processing**: Analyze training data for disparate impact (e.g., Gender bias).
2. **Inference**: Model makes a prediction (e.g., "Hire Candidate").
3. **Explainability**: SHAP values are calculated to explain *why* (e.g., "Experience +5").
4. **Auditing**: Decision and explanation are logged for compliance.

---

## 13. Evaluation Pipeline
**Goal:** Automated quality assurance using RAGAS metrics (Faithfulness, Answer Relevance).

### Architecture
```mermaid
graph TD
    Dataset[Golden Dataset] --> Eval[Evaluator]
    RAG[RAG System] -->|Answer| Eval
    Eval -->|Compute| Metrics[RAGAS Metrics]
    Metrics -->|Score| Report[HTML Report]
    Report -->|Alert| DevTeam
```

### Component Flow
1. **Test Generation**: Load a "Golden Dataset" of questions and expected answers.
2. **Batch Inference**: Run the RAG system against the dataset to get actual answers.
3. **Scoring**: Use LLM-as-a-Judge (RAGAS) to score Faithfulness and Relevance.
4. **Reporting**: Generate an HTML report highlighting failing cases.

---

## 14. Cost Optimization
**Goal:** Reduce inference costs via Caching and Smart Routing.

### Architecture
```mermaid
graph TD
    UserQuery --> Cache{Semantic Cache}
    Cache -->|Hit| Return[Cached Response]
    Cache -->|Miss| Router{Model Router}
    Router -->|Simple| GPT3["GPT-3.5 Model"]
    Router -->|Complex| GPT4["GPT-4 Model"]
    GPT3 --> |Response| Tracker[Cost Tracker]
    GPT4 --> |Response| Tracker[Cost Tracker]
    Tracker -->|Update| Cache
    Tracker --> User
```

### Component Flow
1. **Check Cache**: Compute embedding of query; check for similar past queries.
2. **Cache Hit**: Return stored response immediately ($0 cost).
3. **Cache Miss**: Router analyzes query complexity.
4. **Inference**: Route to cheapest capable model.
5. **Update**: Log cost and update cache with new Q&A pair.

---

## 15. Model Routing
**Goal:** Dynamically select the optimal LLM based on task complexity and context.

### Architecture
```mermaid
graph TD
    Query --> Scorer[Complexity Scorer]
    Scorer -->|Attributes| Router
    Router -->|Match| Registry[Model Registry]
    Registry -->|Select| Model
    Model -->|Execute| Response
    Response --> Logger[Decision Logger]
```

### Component Flow
1. **Analysis**: Scorer detects code, math, or long context in the query.
2. **Matching**: Router checks Model Registry capabilities (e.g., "Needs 100k context").
3. **Selection**: Picks the cheapest model that satisfies requirements.
4. **Logging**: Records specific routing decision for future tuning.

---

## 16. HITL (Human-in-the-Loop) Workflow
**Goal:** Human oversight for high-stakes agent actions.

### Architecture
```mermaid
graph TD
    Agent -->|Action Proposal| Policy{Policy Check}
    Policy -->|Safe| Execute
    Policy -->|Flagged| Queue[Approval Queue]
    Queue -->|Wait| Human[Manager]
    Human -->|Approve/Reject| Queue
    Queue -->|Resume| Agent
    Agent -->|Execute/Abort| Result
```

### Component Flow
1. **Proposal**: Agent proposes an action (e.g., "Transfer $50,000").
2. **Policy Check**: System detects amount > Threshold.
3. **Pause**: Execution suspends; request added to Approval Queue.
4. **Review**: Human manager approves via Dashboard/API.
5. **Resume**: Agent creates transaction receipt or aborts.

---

## 17. Knowledge Graph
**Goal:** GraphRAG for structured reasoning and relationship traversal.

### Architecture
```mermaid
graph LR
    Text --> Extractor[Entity Extractor]
    Extractor -->|Triples| GraphDB["NetworkX and Neo4j"]
    Query -->|Entities| GraphDB
    GraphDB -->|Neighbors| Context
    Context -->|Augment| LLM
    LLM --> Answer
```

### Component Flow
1. **Ingestion**: Text is parsed into Subject-Verb-Object triples.
2. **Storage**: Entities and relationships stored in Graph DB.
3. **Retrieval**: Query entities mapped to graph nodes; 2-hop traversal fetches context.
4. **Reasoning**: LLM answers using the structural relationships found.

---

## 18. Event-Driven Architecture
**Goal:** Reactive agents capable of asynchronous processing via Message Bus.

### Architecture
```mermaid
graph TD
    Source[Order Service] -->|Publish| Bus["Kafka Message Bus"]
    Bus -->|Subscribe| Consumer[Agent Consumer]
    Consumer -->|Process| Logic[Business Logic]
    Logic -->|Publish| Bus
    Bus -->|Event| Inventory[Inventory Service]
```

### Component Flow
1. **Event**: External system publishes `order.created`.
2. **Consumption**: Agent subscribes to topic and picks up message.
3. **Processing**: Agent validates order (Async/Non-blocking).
4. **Reaction**: Agent publishes `inventory.check` event for downstream services.

---

## 19. Observability
**Goal:** Full visibility into agent operations (Logs, Metrics, Traces).

### Architecture
```mermaid
graph TD
    Agent -->|Log Request| Logger[JSON Logger]
    Agent -->|Measure Latency| Metrics[Prometheus Client]
    Agent -->|Trace Span| Tracer[OpenTelemetry]
    Metrics -->|Scrape| dashboard["Grafana and Prometheus"]
    Tracer -->|Export| Jaeger["Console and Jaeger"]
```

### Component Flow
1. **Instrumentation**: Agent code wrapped with Tracing spans and Metric counters.
2. **Execution**: Every request increments counters and logs JSON events.
3. **Scraping**: Prometheus scrapes `/metrics` endpoint.
4. **Analysis**: Dashboards visualize error rates, P99 latency, and token usage.

---

## 20. Cloud Deployment
**Goal:** Production-grade deployment on Kubernetes with IaC.

### Architecture
```mermaid
graph TD
    Dev -->|Push| Loop["CI and CD Pipeline"]
    Loop -->|Build| Docker[Docker Image]
    Loop -->|Terraform| Infra[AWS EKS]
    Loop -->|Helm and Manifests| K8s[Kubernetes Cluster]
    K8s -->|Pod| Container[Agent Container]
    Container -->|Service| LoadBalancer
```

### Component Flow
1. **Build**: Docker container created from Source.
2. **Provision**: Terraform brings up VPC and EKS Cluster.
3. **Deploy**: Kubernetes manifests apply Deployment, Service, and HPA.
4. **Run**: Pods start, health checks pass, LoadBalancer exposes IP.
