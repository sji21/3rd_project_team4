# Changelog

## 2026-08-26

### Added

- Added validated registry PDF ingestion with embedded-text extraction and cross-platform Tesseract OCR fallback. (commit: `c76d2ea`)
- Added masked evidence and deterministic warning rules for ownership restrictions, collateral rights, tenant registrations, and document freshness. (commit: `417d86b`)
- Added a consent-based Streamlit upload and registry-check screen with warning evidence, follow-up checks, masked preview, and privacy-safe JSON export. (commit: `42c51e1`)
- Added deterministic RAG retrieval queries, a LangGraph handoff state, and an integration boundary that keeps OCR analysis independent from the LLM. (commit: `e7fbf55`)
- Added registry-check setup documentation, optional real-PDF service and Streamlit integration tests, and cross-platform Tesseract discovery tests. Windows device verification remains pending. (commit: `0d93f60`)

### Fixed

- Prevented pypdfium2 segmentation faults by rendering PDF pages sequentially before parallelizing only the Tesseract subprocess calls. (commit: `534920d`)
