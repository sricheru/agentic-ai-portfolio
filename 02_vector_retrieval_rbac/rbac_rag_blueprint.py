"""
================================================================================
Enterprise Architecture Blueprint: Identity-Aware Entra ID RBAC Vector Search
Author: Sri Cherukuri (US Patent #7756878)
Domain: Enterprise Retrieval & Zero-Trust Vector Security
================================================================================
Overview:
    This reference blueprint implements the Identity-Aware Access Control List (ACL)
    filtering, Document Chunk metadata schemas, and Reciprocal Rank Fusion (RRF)
    hybrid search engine for enterprise RAG systems integrated with Microsoft Entra ID.
"""

from __future__ import annotations

import enum
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field


# ------------------------------------------------------------------------------
# 1. Identity & Security Context Models (Entra ID / OAuth2 Token Claims)
# ------------------------------------------------------------------------------

class SecurityClearance(str, enum.Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"


class UserSecurityContext(BaseModel):
    """
    Decoded and validated claims from incoming Entra ID (Azure AD) JWT token.
    Passed downstream to enforce Zero-Trust pre-filtering at the Vector DB layer.
    """
    user_id: str
    tenant_id: str
    upn: str  # User Principal Name
    roles: List[str] = Field(default_factory=list)
    entra_group_ids: List[str] = Field(default_factory=list)
    clearance_level: SecurityClearance = SecurityClearance.INTERNAL
    department: str = "General"


class AccessControlPolicy(BaseModel):
    """
    Security boundary metadata embedded on every Document Chunk during ingestion.
    """
    tenant_id: str
    min_clearance: SecurityClearance = SecurityClearance.INTERNAL
    allowed_roles: List[str] = Field(default_factory=list)
    allowed_groups: List[str] = Field(default_factory=list)
    allowed_departments: List[str] = Field(default_factory=list)
    is_public: bool = False


# ------------------------------------------------------------------------------
# 2. Document Chunks & Vector Store Schemas
# ------------------------------------------------------------------------------

class DocumentChunk(BaseModel):
    """
    Individual chunk stored in Vector Database (Qdrant / Chroma / Pinecone / OpenSearch).
    """
    chunk_id: str
    document_id: str
    title: str
    content: str
    token_count: int
    acl: AccessControlPolicy
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ------------------------------------------------------------------------------
# 3. Zero-Trust ACL Filter Builder
# ------------------------------------------------------------------------------

class VectorDBFilterBuilder:
    """
    Translates UserSecurityContext into database-native boolean filter payloads
    to ensure database-level pre-filtering (zero unauthorized vector comparisons).
    """
    @staticmethod
    def build_qdrant_filter(user: UserSecurityContext) -> Dict[str, Any]:
        """Generates Qdrant-compliant boolean filter payload."""
        clearance_hierarchy = {
            SecurityClearance.PUBLIC: [SecurityClearance.PUBLIC],
            SecurityClearance.INTERNAL: [SecurityClearance.PUBLIC, SecurityClearance.INTERNAL],
            SecurityClearance.CONFIDENTIAL: [
                SecurityClearance.PUBLIC, SecurityClearance.INTERNAL, SecurityClearance.CONFIDENTIAL
            ],
            SecurityClearance.RESTRICTED: [
                SecurityClearance.PUBLIC, SecurityClearance.INTERNAL, 
                SecurityClearance.CONFIDENTIAL, SecurityClearance.RESTRICTED
            ]
        }
        
        allowed_clearance_strings = [c.value for c in clearance_hierarchy[user.clearance_level]]
        
        return {
            "must": [
                {"key": "acl.tenant_id", "match": {"value": user.tenant_id}},
                {"key": "acl.min_clearance", "match": {"any": allowed_clearance_strings}}
            ],
            "should": [
                {"key": "acl.is_public", "match": {"value": True}},
                {"key": "acl.allowed_roles", "match": {"any": user.roles}},
                {"key": "acl.allowed_groups", "match": {"any": user.entra_group_ids}},
                {"key": "acl.allowed_departments", "match": {"value": user.department}}
            ]
        }

    @staticmethod
    def evaluate_authorization(user: UserSecurityContext, chunk: DocumentChunk) -> bool:
        """
        Post-retrieval defensive validation check ensuring zero data leakage.
        """
        # Tenant isolation
        if chunk.acl.tenant_id != user.tenant_id:
            return False
            
        if chunk.acl.is_public:
            return True
            
        # Clearance check
        clearance_ranks = {
            SecurityClearance.PUBLIC: 1,
            SecurityClearance.INTERNAL: 2,
            SecurityClearance.CONFIDENTIAL: 3,
            SecurityClearance.RESTRICTED: 4
        }
        if clearance_ranks[user.clearance_level] < clearance_ranks[chunk.acl.min_clearance]:
            return False
            
        # Group or Role overlap check
        has_group = bool(set(user.entra_group_ids).intersection(set(chunk.acl.allowed_groups)))
        has_role = bool(set(user.roles).intersection(set(chunk.acl.allowed_roles)))
        has_dept = user.department in chunk.acl.allowed_departments
        
        return has_group or has_role or has_dept


# ------------------------------------------------------------------------------
# 4. Hybrid Search & Reciprocal Rank Fusion (RRF)
# ------------------------------------------------------------------------------

class SearchResult(BaseModel):
    chunk: DocumentChunk
    score: float
    rank: int


class HybridRankedResult(BaseModel):
    chunk_id: str
    dense_rank: Optional[int] = None
    sparse_rank: Optional[int] = None
    rrf_score: float
    chunk: DocumentChunk


def reciprocal_rank_fusion(
    dense_results: List[SearchResult],
    sparse_results: List[SearchResult],
    k: int = 60
) -> List[HybridRankedResult]:
    """
    Combines dense semantic rankings and sparse BM25 rankings using RRF formula:
    RRF_Score(d) = SUM_{m in M} (1 / (k + rank_m(d)))
    """
    scores: Dict[str, float] = {}
    dense_ranks: Dict[str, int] = {}
    sparse_ranks: Dict[str, int] = {}
    chunk_map: Dict[str, DocumentChunk] = {}
    
    # Process Dense
    for res in dense_results:
        cid = res.chunk.chunk_id
        chunk_map[cid] = res.chunk
        dense_ranks[cid] = res.rank
        scores[cid] = scores.get(cid, 0.0) + (1.0 / (k + res.rank))
        
    # Process Sparse
    for res in sparse_results:
        cid = res.chunk.chunk_id
        chunk_map[cid] = res.chunk
        sparse_ranks[cid] = res.rank
        scores[cid] = scores.get(cid, 0.0) + (1.0 / (k + res.rank))
        
    # Sort descending by RRF score
    sorted_items = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    
    ranked_output: List[HybridRankedResult] = []
    for cid, rrf_val in sorted_items:
        ranked_output.append(
            HybridRankedResult(
                chunk_id=cid,
                dense_rank=dense_ranks.get(cid),
                sparse_rank=sparse_ranks.get(cid),
                rrf_score=round(rrf_val, 6),
                chunk=chunk_map[cid]
            )
        )
    return ranked_output


# ------------------------------------------------------------------------------
# Self-Verification Simulation
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 80)
    print("Identity-Aware RBAC Vector Retrieval - Blueprint Verification")
    print("=" * 80)
    
    # 1. Simulate User from Entra ID
    alice = UserSecurityContext(
        user_id="usr_0182",
        tenant_id="tenant_telecom_global",
        upn="alice.arch@enterprise.com",
        roles=["CloudArchitect", "SecurityEngineer"],
        entra_group_ids=["grp_arch_leads", "grp_secops"],
        clearance_level=SecurityClearance.CONFIDENTIAL,
        department="CorePlatform"
    )
    
    # 2. Build DB Filter
    qdrant_filter = VectorDBFilterBuilder.build_qdrant_filter(alice)
    print(f"[*] Generated DB Pre-Filter for Entra User: {alice.upn}")
    print(f"    Clearance: {alice.clearance_level.value} | Groups: {alice.entra_group_ids}")
    
    # 3. Simulate Ingested Chunks
    chunk_allowed = DocumentChunk(
        chunk_id="chk_arch_doc_01",
        document_id="doc_9901",
        title="Tier-1 Edge Core 5G Routing Architecture",
        content="Edge cell routing topology and BGP peer failover rules.",
        token_count=180,
        acl=AccessControlPolicy(
            tenant_id="tenant_telecom_global",
            min_clearance=SecurityClearance.CONFIDENTIAL,
            allowed_groups=["grp_arch_leads"],
            allowed_departments=["CorePlatform"]
        )
    )
    
    chunk_forbidden = DocumentChunk(
        chunk_id="chk_exec_comp_02",
        document_id="doc_8802",
        title="Executive Compensation & M&A Strategy",
        content="Confidential acquisition targets and partner buyouts.",
        token_count=145,
        acl=AccessControlPolicy(
            tenant_id="tenant_telecom_global",
            min_clearance=SecurityClearance.RESTRICTED,
            allowed_groups=["grp_board_of_directors"],
            allowed_departments=["Executive"]
        )
    )
    
    # 4. Verify Authorization Engine
    auth_allowed = VectorDBFilterBuilder.evaluate_authorization(alice, chunk_allowed)
    auth_forbidden = VectorDBFilterBuilder.evaluate_authorization(alice, chunk_forbidden)
    
    print(f"[*] ACL Validation for '{chunk_allowed.title}': Allowed -> {auth_allowed}")
    print(f"[*] ACL Validation for '{chunk_forbidden.title}': Allowed -> {auth_forbidden}")
    assert auth_allowed is True and auth_forbidden is False
    
    # 5. Hybrid Search Fusion Verification
    dense_res = [SearchResult(chunk=chunk_allowed, score=0.89, rank=1)]
    sparse_res = [SearchResult(chunk=chunk_allowed, score=14.2, rank=2)]
    hybrid = reciprocal_rank_fusion(dense_res, sparse_res)
    
    print(f"[OK] Hybrid RRF Score for '{hybrid[0].chunk_id}': {hybrid[0].rrf_score}")
    print(f"[OK] Zero-Trust Identity-Aware Retrieval verified successfully.")
    print("=" * 80)
