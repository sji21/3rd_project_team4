# Changelog

## 2026-08-31

### Changed

- PATCH-026 aligns law retrieval with Qwen3-8B's top-three evidence contract. Law-only RRF now uses `rrf_k=5` while case and guide retrieval remain at 60, raising service-index law Hit@3 from 91.7% to 100% without changing Hit@1. A law-only contextual expansion for confirmation-date effects then raises law-scoped Recall@3 from 97.9% to 100%. The rule fired for only `dev-001` among the 42 observed dev/holdout questions, so this is documented as a limited fix rather than generalization evidence; new effect/procedure variants remain a follow-up. (commit: pending)

## 2026-08-30

### Added

- Added a reproducible official-case ingestion path that converts Law.go.kr detail-response JSONL into standard `CaseRecord` JSONL for the shared SQLite and Chroma pipeline. It keeps one holding per case chunk, rejects incomplete records, handles duplicate case numbers deterministically, and preserves the reviewed scope exclusions. Parsing and SQLite ingestion no longer require Chroma to be installed. (commit: `7e178f7`)

### Fixed

- PATCH-023 hardens the reviewed case-ingestion path: a verified-source JSONL is published only after every API candidate succeeds (otherwise it is preserved and the command exits 1); real calendar dates are validated; legacy SQLite migration recreates both case-number and decision-date indexes; and manual-review CSV approvals alone expand the verified corpus. (local changes; commit pending)

## 2026-08-28

### Added

- Sealed a holdout evaluation set and measured it once, and ingested the official HUG and NTS guides from their source pages. Guides are returned as a separate group (`result.guides`) and labelled as non-statutory in the prompt. Without them, "what is jeonse deposit return insurance?" returned unrelated statutes while `is_empty()` stayed False, so abstention never triggered. (commit: pending)

- Added a retrieval entry point (`RetrievalService`) that returns the top 5 statutes and top 5 court cases for one question, as `Evidence` objects carrying text and citation rather than raw chunks. The two kinds are searched separately because mixing them costs 17.4%p of statute Hit@5. (commit: pending)
- Added routing that excludes the Commercial Building Lease Protection Act from housing questions by default; 57 of 133 statute chunks (43%) belong to it and were crowding out housing articles. Hit@1 went from 40.0% to 76.0% on the 25-question set. Commercial signals in the question lift the exclusion. (commit: pending)
- Added `status=current` to the default search filter so repealed or superseded articles are never returned as grounds, and made blank questions return nothing — embeddings turn whitespace into a vector and would otherwise return arbitrary documents. (commit: pending)

- Added a case loader and chunk merger: the supplied 26 Supreme Court housing cases now use the shared SQLite schema and can be combined with law chunks for the shared KURE Chroma collection. The MVP intentionally leaves `case_law_citations` empty until verified citation data is available. (commit: pending)
- Added hybrid retrieval that fuses BM25 and KURE-v1 rankings with reciprocal rank fusion. The two methods failed on different questions, and combining them clears both: Hit@5 reaches 100% and MRR 0.880 against 0.847 and 0.860 alone. (commit: pending)
- Added Chroma indexing and a Chroma-backed retriever, and settled on `nlpai-lab/KURE-v1` (1024 dimensions) after comparing embedding models on the same evaluation set. It scores Hit@1 80.0% and MRR 0.860 against 52.0% / 0.647 for `text-embedding-3-small`, and answers a query in 0.141s on CPU. (commit: `39cf361`)
- Added law ingestion that loads source article records into the relational store and exports flattened chunks for retrieval, so parsing quality can be verified before an embedding model is chosen. Reloading the same records does not duplicate rows. (commit: `6261cf0`)

### Changed

- Restricted Chroma stale-vector cleanup to the incoming `doc_type` scope. Reindexing cases no longer removes laws in the shared collection; `--prune-all` remains the explicit cross-type cleanup option. (commit: pending)
- Expanded relational document and RAG chunk source types to support laws, decrees, ministerial rules, cases, legal interpretations, and official guides while continuing to reject unknown types. (commit: `8d2299e`)

## 2026-08-27

### Fixed (Bug Fixes)

- Fixed unreadable white text on the light Streamlit background by applying an explicit high-contrast light theme. (commit: `26f8cd1`)

### Changed

- Organized planning documents, reference assets, and the shareable PDF under `docs/planning/`; moved the cross-platform PDF builder to `scripts/` and documented its reproducible paths and dependencies. (commit: `0185314`)

### Added

- Added a versioned SQLite knowledge schema for laws, articles, cases, official guides, registry-risk evidence and evaluation references, plus an idempotent Chroma collection initializer and documented source-to-vector relationships. (commit: `0d7f02c`)
- Added local OCR-based housing lease contract checks for PDF and mobile-captured JPG/JPEG/PNG files, including image validation and EXIF rotation correction, written core values, visually unverifiable signatures, detected special-term concepts, registry-linked clause recommendations, official references, and privacy-reduced JSON export. (commit: `3192b4b`)

## 2026-08-26

### Added

- Added validated registry PDF ingestion with embedded-text extraction and cross-platform Tesseract OCR fallback. (commit: `c76d2ea`)
- Added masked evidence and deterministic warning rules for ownership restrictions, collateral rights, tenant registrations, and document freshness. (commit: `417d86b`)
- Added a consent-based Streamlit upload and registry-check screen with warning evidence, follow-up checks, masked preview, and privacy-safe JSON export. (commit: `42c51e1`)
- Added deterministic RAG retrieval queries, a LangGraph handoff state, and an integration boundary that keeps OCR analysis independent from the LLM. (commit: `e7fbf55`)
- Added registry-check setup documentation, optional real-PDF service and Streamlit integration tests, and cross-platform Tesseract discovery tests. Windows device verification remains pending. (commit: `0d93f60`)

### Fixed

- Prevented pypdfium2 segmentation faults by rendering PDF pages sequentially before parallelizing only the Tesseract subprocess calls. (commit: `534920d`)
