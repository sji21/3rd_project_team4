# Changelog

## 2026-08-28

### Added

- Added Chroma indexing and a Chroma-backed retriever, and settled on `nlpai-lab/KURE-v1` (1024 dimensions) after comparing embedding models on the same evaluation set. It scores Hit@1 80.0% and MRR 0.860 against 52.0% / 0.647 for `text-embedding-3-small`, and answers a query in 0.141s on CPU. (commit: `39cf361`)
- Added law ingestion that loads source article records into the relational store and exports flattened chunks for retrieval, so parsing quality can be verified before an embedding model is chosen. Reloading the same records does not duplicate rows. (commit: `6261cf0`)

### Changed

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
