# 작업 목록

패치는 위에서 아래 순서로 진행한다. 한 번에 하나만 `진행 중`으로 두며, 선행 패치의 구현·테스트·커밋이 끝나기 전에는 다음 패치를 시작하지 않는다.

| 완료 | 패치 ID | 상태 | 담당자 | 브랜치 | 유형 | 우선순위 | 내용 | 완료 조건 | 의존성 | 이슈 | 등록일 | 완료일 | 구현 커밋 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [x] | PATCH-001 | 완료 | gitcatho | `feat/patch-001-pdf-ocr` | 기능 추가 | 높음 | PDF 검증, 내장 텍스트 추출, Tesseract OCR 보강 | PDF 형식·20MB·30페이지 제한, 텍스트 PDF 직접 추출, 스캔 페이지 `kor+eng` OCR, macOS·Windows 실행 파일 탐색, 추출 단위 테스트 통과 | Tesseract, pdfplumber, pypdfium2, Pillow | - | 2026-08-26 | 2026-08-26 | `c76d2ea` |
| [x] | PATCH-002 | 완료 | gitcatho | `feat/patch-002-risk-signals` | 기능 추가 | 높음 | 개인정보 마스킹과 등기 위험 신호 규칙 | 주민번호·전화·계좌 마스킹, 갑구·을구 핵심 신호 탐지, 근거 페이지·문구·추가 확인사항 반환, 안전 판정 금지, 규칙 테스트 통과 | PATCH-001 | - | 2026-08-26 | 2026-08-26 | `417d86b` |
| [x] | PATCH-003 | 완료 | gitcatho | `feat/patch-003-streamlit-registry-check` | 기능 추가 | 높음 | Streamlit PDF 업로드 및 점검 결과 화면 | 동의 기반 PDF 업로드, 상태·신호·근거·체크리스트 표시, 마스킹된 미리보기, 개인정보 제외 JSON 다운로드, Streamlit 앱 테스트 통과 | PATCH-002 | - | 2026-08-26 | 2026-08-26 | `42c51e1` |
| [ ] | PATCH-004 | 배정됨 | gitcatho | `feat/patch-004-rag-handoff` | 기능 추가 | 중간 | LangChain·LangGraph 후속 연결 인터페이스 | 위험 신호별 RAG 질의 생성, Retriever 입력 스키마 문서화, `ANSWER/ABSTAIN/REFUSE` 연결 경계 명시, 현재 기능은 LLM 없이 실행 | PATCH-002 | - | 2026-08-26 | - | pending |
| [ ] | PATCH-005 | 배정됨 | gitcatho | `feat/patch-005-registry-integration` | 테스트 | 중간 | 실행 문서, 통합 테스트와 Windows 재현 검증 | README·설치 문서 갱신, 실제 샘플 통합 테스트, `pytest -q`·`pip check` 통과, macOS 실측 기록, Windows 팀원 검증 절차와 결과 기록 | PATCH-001, PATCH-002, PATCH-003, PATCH-004 | - | 2026-08-26 | - | pending |

## 현재 작업 경계

- 현재 활성 패치: 없음 (`PATCH-004` 시작 대기)
- 다음 허용 범위: 위험 신호별 RAG 질의와 LangChain·LangGraph 연결 경계
- 다음 패치 시작 조건: `PATCH-004` 전용 브랜치 전환 및 상태를 `진행 중`으로 갱신
- 이미 작성된 후속 패치 코드는 아직 커밋 대상이 아니며 각 패치 차례에 별도로 검토·검증한다.
