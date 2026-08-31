# 🚀 06. 6-Stage LLMOps CI/CD Pipeline & Automated RAGAS Evaluation

[![Domain](https://img.shields.io/badge/Domain-LLMOps_%26_Evaluation_CI%2FCD-blue.svg)](#)
[![RAGAS](https://img.shields.io/badge/Eval_Gate-RAGAS_Faithfulness_%E2%89%A5_0.85-green.svg)](#)
[![CI/CD](https://img.shields.io/badge/Pipeline-6--Stage_GitHub_Actions-000000.svg)](#)
[![Infrastructure](https://img.shields.io/badge/Deploy-AWS_EKS_%2B_Canary-orange.svg)](#)

---

## 🏛️ Architectural Overview

Deploying GenAI applications without automated evaluation gates frequently leads to catastrophic **prompt regressions**, where an unvetted prompt edit or fine-tuned model checkpoint passes unit tests but causes severe factual hallucinations in production.

This reference architecture implements an **Enterprise 6-Stage LLMOps Pipeline with Automated RAGAS Quality Gates**:
1. **Stage 1 (Lint & Static Analysis):** Ruff, Black, Mypy type-checking, Pydantic V2 schema validation.
2. **Stage 2 (Security & Secret Scan):** Bandit, CodeQL, Gitleaks, OWASP LLM vulnerability audits.
3. **Stage 3 (Unit & StateGraph Tests):** Pytest suite covering state reducers, checkpointing, and tool dispatchers (>85% code coverage).
4. **Stage 4 (RAGAS Evaluation Gate):** Automated LLM-as-a-Judge benchmarking across Golden Datasets requiring **Faithfulness $\ge 0.85$** and **Answer Relevance $\ge 0.85$** to unblock deployment.
5. **Stage 5 (Container Hardening & Cosign Signing):** Distroless Docker build with cryptographic image signing.
6. **Stage 6 (Canary Deployment on AWS EKS):** Helm-managed canary release with Prometheus metric-driven automated rollback on `error_rate > 1%`.

---

## 📐 System Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor Dev as AI Engineer
    participant Git as GitHub PR / Merge
    participant Runner as GitHub Actions Runner
    participant Eval as RAGAS Evaluation Engine
    participant Registry as Container Registry (Cosign)
    participant EKS as AWS EKS Cluster
    participant Prom as Prometheus / OpenTelemetry

    Dev->>Git: Push Prompt / Model Changes
    Git->>Runner: Trigger 6-Stage LLMOps Pipeline
    Runner->>Runner: 1. Ruff Lint + Mypy Type Check
    Runner->>Runner: 2. Security Vulnerability Scan (Gitleaks, Bandit)
    Runner->>Runner: 3. Pytest Unit Tests (>85% Coverage Gate)
    
    Runner->>Eval: 4. Execute RAGAS Golden Dataset Benchmarks
    Eval->>Eval: Compute Faithfulness & Relevance Scores
    alt Mean Faithfulness < 0.85 (Prompt Regression Detected)
        Eval-->>Runner: Quality Gate FAILED
        Runner-->>Dev: Block PR & Alert Team with HTML Eval Report
    else Quality Gate Passed (>= 0.85)
        Eval-->>Runner: Quality Gate PASSED
        Runner->>Registry: 5. Build Container & Sign with Cosign
        Runner->>EKS: 6. Deploy 10% Canary Pods via Helm
        EKS->>Prom: Stream Telemetry & Latency Metrics
        Prom-->>EKS: Verify Error Rate < 1% & P95 < 1500ms
        EKS->>EKS: Promote to 100% Production Traffic
        Runner-->>Dev: Production Release Complete (45min total)
    end
```

---

## 📂 Blueprint Files

* [`ragas_eval_pipeline_blueprint.py`](./ragas_eval_pipeline_blueprint.py): Complete, executable Pydantic V2 schemas for Golden datasets, RAGAS score calculators, Quality gate threshold evaluators, and pipeline reporters.

### Quick Verification
```bash
python 06_llmops_ragas_eval/ragas_eval_pipeline_blueprint.py
```
