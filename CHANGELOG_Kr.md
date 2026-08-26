# 변경 이력

## 2026-08-26

### 추가

- 등기 PDF 검증, 내장 텍스트 추출과 운영체제 독립적인 Tesseract OCR 보강 기능을 추가했습니다. (commit: `c76d2ea`)
- 개인정보가 마스킹된 근거와 소유권 제한·담보권·임차권·문서 최신성에 대한 결정론적 주의 신호 규칙을 추가했습니다. (commit: `417d86b`)
- 동의 기반 PDF 업로드, 주의 신호 근거·추가 확인사항·마스킹 미리보기와 개인정보 제외 JSON 다운로드를 제공하는 Streamlit 화면을 추가했습니다. (commit: `42c51e1`)
- OCR 분석을 LLM과 분리한 상태로 위험 신호별 RAG 검색 질의, LangGraph 전달 상태와 후속 연결 경계를 추가했습니다. (commit: `e7fbf55`)

### 수정

- PDF 페이지를 순차 렌더링한 뒤 Tesseract subprocess만 병렬 실행하도록 분리해 pypdfium2 segmentation fault를 방지했습니다. (commit: `534920d`)
