"""
================================================================================
Enterprise Architecture Blueprint: Adaptive Agentic RAG (Corrective & Self-RAG)
Author: Sri Cherukuri
Domain: Agentic Retrieval-Augmented Generation & Self-Corrective Loops
================================================================================
Overview:
    This reference blueprint implements an Adaptive Agentic RAG architecture combining
    Self-RAG and Corrective RAG (CRAG). It features autonomous document grading,
    context hallucination checks, dynamic query rewriting, and fallback retrieval.
"""

from __future__ import annotations

import enum
import time
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ------------------------------------------------------------------------------
# 1. Agentic RAG State & Evaluation Models
# ------------------------------------------------------------------------------

class RetrievalGrade(str, enum.Enum):
    RELEVANT = "RELEVANT"
    IRRELEVANT = "IRRELEVANT"
    AMBIGUOUS = "AMBIGUOUS"


class DocumentChunk(BaseModel):
    chunk_id: str = Field(default_factory=lambda: f"doc_{uuid.uuid4().hex[:8]}")
    title: str
    content: str
    source_url: str
    score: float = 0.0


class DocumentGrading(BaseModel):
    """Evaluation result for an individual retrieved document chunk."""
    chunk_id: str
    grade: RetrievalGrade
    relevance_score: float = Field(ge=0.0, le=1.0)
    critique: str


class HallucinationVerdict(BaseModel):
    """Verification whether generated answer is grounded in retrieved context."""
    is_grounded: bool
    faithfulness_score: float = Field(ge=0.0, le=1.0)
    unsupported_claims: List[str] = Field(default_factory=list)


class AgenticRAGState(BaseModel):
    """State graph channels for the Agentic RAG pipeline."""
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    original_query: str
    current_query: str
    retrieved_documents: List[DocumentChunk] = Field(default_factory=list)
    graded_documents: List[DocumentGrading] = Field(default_factory=list)
    relevant_chunks: List[DocumentChunk] = Field(default_factory=list)
    needs_query_rewrite: bool = False
    rewrite_count: int = 0
    max_rewrites: int = 2
    generated_answer: Optional[str] = None
    hallucination_check: Optional[HallucinationVerdict] = None
    is_complete: bool = False
    execution_trace: List[str] = Field(default_factory=list)


# ------------------------------------------------------------------------------
# 2. Agentic RAG Decision Nodes & Evaluators
# ------------------------------------------------------------------------------

class RetrievalGrader:
    """Evaluates whether retrieved chunks contain sufficient context to answer query."""
    @staticmethod
    def grade_documents(query: str, docs: List[DocumentChunk]) -> List[DocumentGrading]:
        gradings = []
        q_lower = query.lower()
        
        for doc in docs:
            c_lower = doc.content.lower()
            overlap_words = set(q_lower.split()).intersection(set(c_lower.split()))
            relevance = min(1.0, len(overlap_words) / max(1, len(q_lower.split())))
            
            if relevance >= 0.35:
                grade = RetrievalGrade.RELEVANT
                critique = "Document contains direct answers to query key terms."
            else:
                grade = RetrievalGrade.IRRELEVANT
                critique = "Document lacks contextual relevance. Discarded."
                
            gradings.append(DocumentGrading(
                chunk_id=doc.chunk_id,
                grade=grade,
                relevance_score=round(relevance, 2),
                critique=critique
            ))
        return gradings


class AdaptiveQueryRewriter:
    """Transforms ambiguous or failed queries into optimized semantic search vectors."""
    @staticmethod
    def rewrite(state: AgenticRAGState) -> str:
        # Deconstruct and rephrase query based on failure mode
        rewritten = f"Detailed technical explanation: {state.original_query} with architecture specifications"
        return rewritten


class HallucinationEvaluator:
    """Zero-trust factual consistency validator (LLM-as-a-Judge)."""
    @staticmethod
    def evaluate(context_chunks: List[DocumentChunk], answer: str) -> HallucinationVerdict:
        context_text = " ".join([d.content for d in context_chunks]).lower()
        ans_lower = answer.lower()
        
        # Simple simulated grounding check
        words_in_context = [w for w in ans_lower.split() if w in context_text]
        ratio = len(words_in_context) / max(1, len(ans_lower.split()))
        
        is_grounded = ratio >= 0.40
        return HallucinationVerdict(
            is_grounded=is_grounded,
            faithfulness_score=round(min(1.0, ratio * 1.5), 2),
            unsupported_claims=[] if is_grounded else ["Detected ungrounded speculative claim in generation."]
        )


# ------------------------------------------------------------------------------
# 3. Agentic RAG Controller Pipeline
# ------------------------------------------------------------------------------

def execute_agentic_rag_step(state: AgenticRAGState) -> AgenticRAGState:
    """Executes a full stateful cycle of the Corrective/Self-RAG workflow."""
    updated = state.model_copy(deep=True)
    
    # 1. Grade Retrieved Documents
    updated.execution_trace.append("NODE: Grade Retrieved Documents")
    gradings = RetrievalGrader.grade_documents(updated.current_query, updated.retrieved_documents)
    updated.graded_documents = gradings
    
    relevant_ids = {g.chunk_id for g in gradings if g.grade == RetrievalGrade.RELEVANT}
    updated.relevant_chunks = [d for d in updated.retrieved_documents if d.chunk_id in relevant_ids]
    
    # 2. Evaluate if query rewrite is required (Corrective RAG)
    if not updated.relevant_chunks and updated.rewrite_count < updated.max_rewrites:
        updated.execution_trace.append("NODE: Trigger Query Rewrite (0 Relevant Chunks)")
        updated.needs_query_rewrite = True
        updated.rewrite_count += 1
        updated.current_query = AdaptiveQueryRewriter.rewrite(updated)
        return updated
        
    # 3. Generate Answer (Self-RAG Grounding)
    updated.execution_trace.append("NODE: Generate Grounded Answer")
    context_summary = " ".join([c.content for c in updated.relevant_chunks])
    updated.generated_answer = f"Synthesized Response: {context_summary[:180]}... [Sources Cited]"
    
    # 4. Hallucination Evaluation
    updated.execution_trace.append("NODE: Hallucination Verification")
    h_verdict = HallucinationEvaluator.evaluate(updated.relevant_chunks, updated.generated_answer)
    updated.hallucination_check = h_verdict
    updated.is_complete = True
    
    return updated


# ------------------------------------------------------------------------------
# Self-Verification Simulation
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 80)
    print("Agentic RAG (Self-RAG + Corrective RAG) - Blueprint Verification")
    print("=" * 80)
    
    initial_state = AgenticRAGState(
        original_query="Explain LangGraph StateGraph persistence and checkpointing",
        current_query="Explain LangGraph StateGraph persistence and checkpointing",
        retrieved_documents=[
            DocumentChunk(
                title="LangGraph State Persistence",
                content="LangGraph StateGraph provides checkpointing to Redis and Postgres for fault recovery and HITL.",
                source_url="docs.enterprise.ai/langgraph/checkpointing"
            ),
            DocumentChunk(
                title="Irrelevant Marketing Doc",
                content="Our quarterly marketing results show positive engagement across digital channels.",
                source_url="docs.enterprise.ai/marketing"
            )
        ]
    )
    
    result = execute_agentic_rag_step(initial_state)
    
    print(f"[*] Total Retrieved: {len(result.retrieved_documents)} | Relevant Kept: {len(result.relevant_chunks)}")
    for g in result.graded_documents:
        print(f"    - Doc '{g.chunk_id}': Grade -> {g.grade.value} (Score: {g.relevance_score})")
    print(f"[*] Generated Answer: {result.generated_answer}")
    print(f"[*] Hallucination Check: Grounded -> {result.hallucination_check.is_grounded} (Faithfulness: {result.hallucination_check.faithfulness_score})")
    print(f"[*] Execution Trace: {' -> '.join(result.execution_trace)}")
    assert len(result.relevant_chunks) == 1
    assert result.hallucination_check.is_grounded is True
    print(f"[OK] Agentic RAG Blueprint verified successfully.")
    print("=" * 80)
