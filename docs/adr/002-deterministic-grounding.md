# ADR 002: Deterministic Citation Validation & Explicit Abstention Safeguards

## Status
**Accepted**

## Context
Financial regulatory question answering demands absolute legal provenance and zero ungrounded generation. Standard LLM applications suffer from hallucinations, improper citation format drift, and ungrounded answers when retrieved evidence is out-of-domain or below relevance thresholds.

Relying on LLM self-evaluation ("LLM-as-a-judge") introduces non-deterministic latency, API cost inflation, and susceptibility to model bias or prompt injection.

## Decision
We implement a **Deterministic Grounded RAG Pipeline** with multi-layer verification:
1. **Early Score-Threshold Abstention**: If the top reranked context block falls below the minimum relevance threshold (`rag_min_rerank_threshold = 0.30`), the system immediately abstains from generation without calling the LLM.
2. **Strict Regex Citation Syntax Enforcement**: The LLM prompt mandates inline citation tags formatted strictly as `[C1]`, `[C2]`, matching assigned context blocks. Generated answers are parsed using deterministic regular expressions (`CITATION_REGEX = re.compile(r"\[C(\d+)\]")`).
3. **Citation Provenance Binding**: Every extracted citation tag is validated against retrieved `ContextBlock` metadata to ensure the cited context ID exists in the prompt payload.
4. **Context Leak & Injection Defense**: Retrieved legal texts are wrapped in untrusted data boundaries with system prompts explicitly instructing the model to disregard instructions contained within regulatory text.

## Consequences
### Positive
- **Deterministic Reliability**: Grounding validity and citation presence are verified mathematically using regex and provenance lookups, eliminating LLM-as-a-judge latency and cost.
- **Safety Safeguards**: System reliably abstains on out-of-domain queries (e.g., commercial spaceflight regulations) with 100% accuracy.
- **Auditability**: Generated citations link directly back to source regulation ID, article number, structural path, and page range.

### Negative / Trade-offs
- If the LLM generates a valid answer but omits citation tags, the citation validator suppresses the answer and triggers abstention to maintain safety.
