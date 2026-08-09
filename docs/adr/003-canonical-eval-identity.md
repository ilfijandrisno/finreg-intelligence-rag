# ADR 003: Canonical Identity & Structural Suffix Normalization in Benchmarking

**Language:** 🇬🇧 English · [🇮🇩 Bahasa Indonesia](003-canonical-eval-identity.id.md)

## Status
**Accepted**

## Context
Evaluating legal retrieval systems requires matching retrieved chunks against human-annotated ground truth provisions. During Phase 3B semantic legal chunking, long legal nodes (e.g. detailed articles or paragraphs) are split into multiple text chunks. The chunking engine appends split part suffixes to the stored `structural_path` (e.g. `"BAB I/Pasal 1/Ayat (1) [Part 1/2]"`).

Comparing ground truth paths (`"BAB I/Pasal 1/Ayat (1)"`) against database structural paths (`"BAB I/Pasal 1/Ayat (1) [Part 1/2]"`) via exact string equality causes false-negative mismatches, yielding 0.0000 metrics despite retrieving the exact document, article, and pages.

Conversely, relying exclusively on chunk UUIDs (`chunk_id`) makes benchmark ground truth brittle and dependent on mutable database primary keys.

## Decision
We establish a **Canonical Legal Identity Schema** for benchmark evaluation:
1. **Canonical Identity 4-Tuple**: Ground truth evidence and retrieved candidates are uniquely identified by:
   $$(document\_id, normalized\_structural\_path, page\_start, page\_end)$$
2. **Evaluation-Layer Path Normalization**: The evaluation layer applies regex normalization (`PART_SUFFIX_REGEX = re.compile(r"\s*\[Part\s+\d+/\d+\]$")`) strictly inside benchmark comparison functions (`canonical_matches()`, `citation_matches_gt()`).
3. **Immutability of Provenance**: Structural paths stored in database records, `RetrievalChunk`, API response citations, and RAG context blocks are **never mutated**.

## Consequences
### Positive
- **Robust Ground Truth**: Benchmark ground truth relies on stable legal attributes rather than mutable database UUIDs.
- **Accurate Evaluation**: Eliminates text-splitter suffix artifacts from evaluation metric calculations.
- **Zero Side Effects**: Provenance display strings in production API responses remain 100% untouched.

### Negative / Trade-offs
- The evaluation engine must normalize structural paths during every comparison step.
