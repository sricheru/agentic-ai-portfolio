# 🤖 05. Adaptive Agentic RAG (Self-RAG & Corrective RAG)

[![Domain](https://img.shields.io/badge/Domain-Agentic_RAG_%26_Self--Correction-blue.svg)](#)
[![Pattern](https://img.shields.io/badge/Pattern-Corrective_RAG_(CRAG)_%2B_Self--RAG-green.svg)](#)
[![Grading](https://img.shields.io/badge/Grading-Autonomous_Document_Filter-orange.svg)](#)
[![Verification](https://img.shields.io/badge/Defense-Hallucination_Evaluator-purple.svg)](#)

---

## 🏛️ Architectural Overview

Standard passive RAG systems blindly accept whatever documents a vector database returns, inject potentially irrelevant or noisy context into the LLM prompt, and hallucinate when the retrieved data is incomplete.

This reference architecture implements **Adaptive Agentic RAG**:
1. **Autonomous Document Grading (CRAG):** Evaluates retrieved document chunks individually using LLM-as-a-Judge to classify each as `RELEVANT`, `IRRELEVANT`, or `AMBIGUOUS`.
2. **Dynamic Query Rewriting & Multi-Hop Fallback:** If zero chunks pass the relevance threshold, the agent pauses generation, rewrites the search query using query decomposition, and triggers secondary retrieval (e.g. Vector DB fallback or Web search).
3. **Self-RAG Hallucination Verification:** Inspects the synthesized response against the authorized source chunks to ensure 100% factual grounding before returning output to the user.
4. **Graph Cyclic Routing:** Implemented as a stateful LangGraph node graph with bounded iteration counts.

---

## 📐 System Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor User as Enterprise Operator
    participant Router as Agentic RAG Controller
    participant VDB as Vector Database (Qdrant/Pinecone)
    participant Grader as Document Relevance Grader
    participant Rewriter as Query Rewriter
    participant Generator as LLM Generator
    participant Verifier as Hallucination Evaluator

    User->>Router: Complex Technical Query
    Router->>VDB: Initial Vector Search
    VDB-->>Router: Retrieved Document Chunks (1..N)
    
    Router->>Grader: Evaluate Chunk Relevance
    Grader-->>Router: Filtered Relevant Chunks
    
    alt No Relevant Chunks Found (Context Gap)
        Router->>Rewriter: Rewrite Query (Query Decomposition)
        Rewriter-->>Router: Optimized Search Query
        Router->>VDB: Secondary Search with Rewritten Query
        VDB-->>Router: Fallback Document Chunks
    end

    Router->>Generator: Generate Response (Grounded in Verified Chunks)
    Generator-->>Router: Draft Response
    Router->>Verifier: Check Factual Grounding (Self-RAG)
    alt Hallucination Detected
        Verifier-->>Router: Flag Unsupported Claims
        Router->>Generator: Re-generate with Strict Grounding Constraint
        Generator-->>Router: Verified Factual Response
    end
    Router-->>User: Grounded Enterprise Answer + Citations
```

---

## 📂 Blueprint Files

* [`agentic_rag_blueprint.py`](./agentic_rag_blueprint.py): Complete, executable Pydantic V2 state models, Document Graders, Query Rewriters, Hallucination Evaluators, and cyclic execution controller.

### Quick Verification
```bash
python 05_agentic_rag/agentic_rag_blueprint.py
```
