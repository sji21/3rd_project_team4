# 작업 목록

패치는 위에서 아래 순서로 진행한다. 한 번에 하나만 `진행 중`으로 두며, 선행 패치의 구현·테스트·커밋이 끝나기 전에는 다음 패치를 시작하지 않는다.

| 완료 | 패치 ID | 상태 | 담당자 | 브랜치 | 유형 | 우선순위 | 내용 | 완료 조건 | 의존성 | 이슈 | 등록일 | 완료일 | 구현 커밋 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [x] | PATCH-001 | 완료 | gitcatho | `feat/patch-001-pdf-ocr` | 기능 추가 | 높음 | PDF 검증, 내장 텍스트 추출, Tesseract OCR 보강 | PDF 형식·20MB·30페이지 제한, 텍스트 PDF 직접 추출, 스캔 페이지 `kor+eng` OCR, macOS·Windows 실행 파일 탐색, 추출 단위 테스트 통과 | Tesseract, pdfplumber, pypdfium2, Pillow | - | 2026-08-26 | 2026-08-26 | `c76d2ea` |
| [x] | PATCH-002 | 완료 | gitcatho | `feat/patch-002-risk-signals` | 기능 추가 | 높음 | 개인정보 마스킹과 등기 위험 신호 규칙 | 주민번호·전화·계좌 마스킹, 갑구·을구 핵심 신호 탐지, 근거 페이지·문구·추가 확인사항 반환, 안전 판정 금지, 규칙 테스트 통과 | PATCH-001 | - | 2026-08-26 | 2026-08-26 | `417d86b` |
| [x] | PATCH-003 | 완료 | gitcatho | `feat/patch-003-streamlit-registry-check` | 기능 추가 | 높음 | Streamlit PDF 업로드 및 점검 결과 화면 | 동의 기반 PDF 업로드, 상태·신호·근거·체크리스트 표시, 마스킹된 미리보기, 개인정보 제외 JSON 다운로드, Streamlit 앱 테스트 통과 | PATCH-002 | - | 2026-08-26 | 2026-08-26 | `42c51e1` |
| [x] | PATCH-004 | 완료 | gitcatho | `feat/patch-004-rag-handoff` | 기능 추가 | 중간 | LangChain·LangGraph 후속 연결 인터페이스 | 위험 신호별 RAG 질의 생성, Retriever 입력 스키마 문서화, `ANSWER/ABSTAIN/REFUSE` 연결 경계 명시, 현재 기능은 LLM 없이 실행 | PATCH-002 | - | 2026-08-26 | 2026-08-26 | `e7fbf55` |
| [ ] | PATCH-005 | 완료 | gitcatho | `feat/patch-005-registry-integration` | 테스트 | 중간 | 실행 문서, 통합 테스트와 Windows 재현 검증 | README·설치 문서 갱신, 실제 샘플 통합 테스트, `pytest -q`·`pip check` 통과, macOS 실측 기록, Windows 팀원 검증 절차와 결과 기록 | PATCH-001, PATCH-002, PATCH-003, PATCH-004, PATCH-006 | - | 2026-08-26 | - | `0d93f60` |
| [x] | PATCH-006 | 완료 | gitcatho | `fix/patch-006-pdfium-thread-safety` | 버그 수정 | 높음 | pypdfium2 동시 렌더링 segmentation fault 수정 | PDF 렌더링은 단일 흐름으로 수행하고 Tesseract subprocess만 병렬화, 실제 6페이지 샘플 반복 5회 무충돌, 전체 테스트 통과 | PATCH-001 | - | 2026-08-26 | 2026-08-26 | `534920d` |
| [x] | PATCH-007 | 완료 | gitcatho | `fix/patch-007-theme-contrast` | 버그 수정 | 높음 | Streamlit 밝은 배경에서 흰색 본문이 보이지 않는 테마 충돌 수정 | 앱 테마를 명시하고 본문·위젯·사이드바 대비를 확인, 화면 회귀 테스트와 전체 테스트 통과 | PATCH-003 | - | 2026-08-27 | 2026-08-27 | `26f8cd1` |
| [x] | PATCH-008 | 완료 | gitcatho | `feat/patch-008-project-structure` | 리팩터링 | 중간 | README 기준으로 프로젝트 코드·기획 문서·생성 스크립트와 산출물 구조 정리 | 기존 기능과 import 경로를 보존하며 파일을 역할별 디렉터리에 배치하고 README 구조·실행법·산출물 위치를 갱신한 뒤 전체 테스트 통과 | PATCH-007 | - | 2026-08-27 | 2026-08-27 | `0185314` |
| [x] | PATCH-009 | 완료 | gitcatho | `feat/patch-009-knowledge-databases` | 기능 추가 | 높음 | 법령·판례·가이드·위험 규칙 관계형 DB와 RAG 검색용 Chroma DB 기반 구축 | SQLite 관계 스키마와 무결성 제약, DB·Chroma 초기화 명령, 생성 데이터 Git 제외, 관계·초기화 테스트, README 데이터 흐름과 테이블 관계 설명, 전체 테스트 통과 | PATCH-008 | - | 2026-08-27 | 2026-08-27 | `0d7f02c` |
| [x] | PATCH-010 | 완료 | gitcatho | `feat/patch-010-lease-contract-check` | 기능 추가 | 높음 | 주택 임대차계약서 OCR, 필수 작성 항목 누락 점검과 공식 근거 기반 특약 확인·추천 | 기존 교차 플랫폼 PDF 추출·OCR을 재사용하고 휴대폰 촬영 JPG·JPEG·PNG의 EXIF 회전 보정과 로컬 OCR을 지원하며, 계약서 항목을 확인·누락 가능·판독 불가로 구분하고 이미 포함된 특약과 상황별 권장 특약을 근거·한계와 함께 Streamlit에 표시한 뒤 회귀 테스트 통과 | PATCH-001, PATCH-003, PATCH-009 | - | 2026-08-27 | 2026-08-27 | `3192b4b` |
| [x] | PATCH-011 | 완료 | gitcatho | `feat/patch-011-expand-document-types` | 기능 변경 | 중간 | 법령 DB와 RAG 청크의 공식 문서 유형 확장 | `documents.document_type`과 `chunks.source_type`에서 법률·시행령·시행규칙·판례·법령해석·공식 가이드를 허용하고, 새 유형 저장 성공·미지원 유형 거부 테스트와 재생성 필요성을 문서화한 뒤 전체 테스트 통과 | PATCH-009 | - | 2026-08-28 | 2026-08-28 | `8d2299e` |
| [x] | PATCH-012 | 완료 | gitcatho | `feat/patch-012-integrate-main` | 기타 | 높음 | 최신 `origin/main` 검색·평가 기능과 PATCH-001~011 누적 작업 통합 | `origin/main`을 병합하고 충돌을 기능 손실 없이 해결하며 전체 테스트·의존성 검사·Git 그래프 검증을 통과한 뒤 공유 `main`에 비강제 푸시 | PATCH-011 | - | 2026-08-28 | 2026-08-28 | `5b74cdf` |
| [x] | PATCH-013 | 완료 | sji21 | `feat/patch-013-law-sqlite-ingestion` | 기능 추가 | 높음 | 법령 원천 레코드를 관계형 DB에 적재하고 검색용 청크로 추출 | 임베딩 없이 SQLite에 법령·판본·조문·청크를 적재하고, 재실행 시 중복이 생기지 않으며, 조인 결과를 Chroma 규격의 평평한 청크 JSONL로 추출해 `validate_chunks` 검증과 검색 실험에 그대로 쓸 수 있어야 한다 | PATCH-009, PATCH-011 | - | 2026-08-28 | 2026-08-28 | `6261cf0` |
| [x] | PATCH-014 | 완료 | sji21 | `feat/patch-014-kure-chroma-index` | 기능 추가 | 높음 | 임베딩 모델 확정과 Chroma 적재·검색 연결 | 같은 평가셋으로 임베딩 모델을 비교해 근거와 함께 하나를 고르고, 청크를 해당 모델로 임베딩해 Chroma에 멱등 적재하며, 같은 `search(query, k, where)` 인터페이스로 조회해 메모리 계산과 같은 결과가 나와야 한다 | PATCH-013 | - | 2026-08-28 | 2026-08-28 | `39cf361` |
| [x] | PATCH-016 | 완료 | sji21 | `feat/patch-016-hybrid-rrf` | 기능 추가 | 높음 | BM25와 임베딩 검색을 RRF로 결합 | 점수 척도가 다른 두 검색기를 순위로 합치고, 같은 `search(query, k, where)` 인터페이스를 유지하며, 각 검색기가 서로 다른 문항에서 실패하던 것이 결합 후 해소되어야 한다 | PATCH-014 | - | 2026-08-28 | 2026-08-28 | `2e658ae` |
| [x] | PATCH-017 | 완료 | sji21 | `fix/patch-017-index-scope` | 버그 수정 | 높음 | Chroma 색인의 삭제 범위를 입력의 doc_type 으로 한정 | 법령과 판례를 같은 컬렉션에 두고 각각 따로 재색인해도 서로의 문서가 지워지지 않아야 하고, 같은 doc_type 안에서는 빠진 청크가 계속 정리되어야 하며, 빈 입력이 컬렉션을 비우지 않아야 한다 | PATCH-014 | - | 2026-08-28 | 2026-08-28 | `c49921d` |
| [x] | PATCH-018 | 완료 | sji21 | `feat/patch-018-retrieval-entrypoint` | 기능 추가 | 높음 | 검색 진입점: 법령 TOP5 + 판례 TOP5 를 근거로 반환 | 질문 하나에 법령과 판례를 각각 따로 뽑아 본문과 출처가 붙은 형태로 돌려주고, 생성 쪽이 검색 내부를 몰라도 쓸 수 있어야 하며, 묶음별 파라미터를 나중에 따로 튜닝할 수 있는 구조여야 한다 | PATCH-017 | - | 2026-08-28 | 2026-08-28 | `d39dc94` |
| [x] | PATCH-019 | 완료 | yoonjihwan402 | `feat/patch-019` | 기능 추가 | 중간 | PATCH-018 표준 판례 청크 기반 임베딩 비교·평가 통합 | 공통 `cases.jsonl`·메타데이터·Chroma 색인 구조를 사용해 판례 전용 KURE 평가와 로컬·Hugging Face 임베딩 비교를 재현 가능하게 실행하고, 운영용 통합 인덱스를 변경하지 않아야 한다 | PATCH-018 | - | 2026-08-29 | 2026-08-29 | `9ef5911` |
| [x] | PATCH-020 | 완료 | sji21 | `feat/patch-020-holdout-eval` | 검증 | 높음 | 홀드아웃 평가셋 봉인·1회 측정과 공식 안내 원문 적재 | 저장소를 본 적 없는 출처가 쓴 질문으로 평가셋을 만들고, 정답은 법령 원문만 보고 붙이며, 범위 밖 판정을 점수 확인 전에 끝내고, 결과를 보고 설정을 고치지 않아야 하며, 공식 안내는 원문을 수집해 법령·판례와 별도 묶음으로 반환해야 한다 | PATCH-018 | - | 2026-08-29 | 2026-08-30 | `69e662a` |
| [x] | PATCH-021 | 완료 | BellaHez | `feat/patch-021-generation-core` | 기능 추가 | 높음 | 검색 진입점과 로컬 LLM 을 LCEL 체인으로 연결 | `RetrievalService` 가 준 근거로 프롬프트를 만들어 로컬 양자화 LLM(Qwen3-8B)에 넘기고, answered·abstained·refused 세 갈래로만 끝나야 하며, 면책 문구와 출처는 LLM 이 아니라 코드가 붙이고, Ollama 없이도 도는 테스트가 통과해야 한다 | PATCH-015, PATCH-018 | - | 2026-08-29 | 2026-08-30 | `f4cd49a` |
| [x] | PATCH-022 | 완료 | yoonjihwan402 | `feat/patch-022-case-data-ingestion` | 기능 추가 | 높음 | 공식 판례 상세 원천을 표준 판례 레코드로 변환 | 국가법령정보센터 상세 원천 JSONL에서 207건 표준 `case_records.jsonl`을 재현하고, 사건번호 중복·수동 제외 범위를 일관되게 처리하며, SQLite·청크 적재 규격 테스트가 통과해야 한다 | PATCH-018, PATCH-019 | PR #10 | 2026-08-30 | 2026-08-30 | `7e178f7` |
| [x] | PATCH-024 | 완료 | kimjeongjaeae | `feat/patch-024-generation-safety` | 기능 변경 | 높음 | Generation 안전성 및 답변 품질 개선 | 범위 판정·프롬프트 인젝션 방어·비밀정보 마스킹·출처·수치 검증·abstention 로직을 보완하고 Qwen 호출 안정화와 평가 스크립트를 정리한다 | PATCH-021, PATCH-023 | PR #11 | 2026-08-31 | 2026-08-31 | `9039cd5` |
| [x] | PATCH-025 | 완료 | yoonjihwan402 | `fix/patch-025-review-hardening` | 버그 수정 | 높음 | PATCH-022 리뷰 보완: 공식 판례 검증·안전 변환·DB 이관 | `LAW_OPEN_API_OC`로 환경·문서를 통일하고, 후보 수와 성공 수가 일치하고 수집 불가가 0건일 때만 원천을 발행한다. 실패하면 기존 출력은 보존하고 보고서에 `published: false`를 남긴 뒤 실패 종료한다. 날짜·오류·제외·수동 검토·동일성 충돌을 분리하며, 수동 분류 CSV는 승인 건만 포함한다. 기존 사건번호 UNIQUE DB는 인용·청크 관계와 두 날짜/사건번호 인덱스를 보존한 채 이관하고, API 복구·변환·적재·이관 회귀 테스트를 통과해야 한다. 13건과 207건은 각각 공개 API 초기 기준선·역사적 스테이징 기록일 뿐 완료 건수 조건은 아니다. | PATCH-022 | PR #12 | 2026-08-30 | 2026-08-31 | `12c025e` |
| [x] | PATCH-026 | 완료 | sji21 | `feat/patch-026-law-intent-expansion` | 검색 개선 | 높음 | 생성 모델의 법령 TOP3 계약에 맞춘 법령 순위와 복합 근거 확보 개선 | 법령에만 `rrf_k=5`와 효과·절차를 구분하는 문맥 확장을 적용해 서비스 인덱스 법령 24문항의 Hit@1 79.2%를 유지하고 Hit@3 91.7%→100%, Recall@3 97.9%→100%를 재현한다. 판례·안내 설정과 순위를 바꾸지 않으며, 규칙이 관찰 42문항 중 1문항에만 발동한 한계와 새 효과·절차 질문 재검증 과제를 문서화한다. | PATCH-020, PATCH-021 | PR #13 | 2026-08-31 | 2026-08-31 | `ee0108e`, `3692e94` |
| [x] | PATCH-028 | 완료 | yoonjihwan402 | `feat/patch-028-case-holdout-eval` | 검증·버그 수정 | 높음 | 공식 판례 안전 발행 보완과 판례 전용 홀드아웃 평가 | API 상세 응답은 `case_id` 일치와 사건번호·법원·선고일 중 2개 이상 일치해야 하며, 일부 필수 필드 누락·재수집 실패·동일성 불일치 시 기존 원천을 바꾸지 않는다. 수동 검토는 `case_id`로 연결한다. 현재 검증 판례 20건의 판례 전용 문항을 고정하고 BM25·KURE-v1·RRF를 같은 `case_id` 정답으로 비교한 보고서·공유 PDF·회귀 테스트를 제공한다. | PATCH-025, PATCH-019 | - | 2026-08-31 | 2026-08-31 | `5ded534`, `0cf9755` |
| [x] | PATCH-029 | 완료 | kimjeongjaeae | `feat/patch-029-streamlit-chatbot` | 기능 추가 | 높음 | Streamlit LENS 챗봇 UI, 멀티턴 후속 질문 처리와 출처 표시 개선 | 기존 `answer_question()`·Retrieval·Validation 흐름을 유지한 중앙 채팅 UI를 제공하고, 최근 정상 답변 대화를 이용해 `그럼`, `그 특약`, `아까 말한` 등의 후속 질문을 독립 질문으로 재작성해 기존 RAG 흐름에 전달한다. `대화 내용 지우기` 시 세션 대화 맥락도 초기화하고, 답변 출처는 내부 `law`·`case`·`guide` 표기 대신 `관련 법령`·`관련 판례`·`관련 기관 안내`로 구분해 표시한다. OCR·문서 세션 기억은 이번 패치에서 연결하지 않으며 `src/retrieval/*`·`src/generation/models.py`·기존 검색 건수 설정은 변경하지 않는다. Streamlit·멀티턴 회귀 테스트를 통과해야 한다. | PATCH-024, PATCH-026, PATCH-028 | PR #16 | 2026-08-31 | 2026-08-31 | `d47049c`, `fe6fae7`, `170f777`, `8df0f93` |
| [x] | PATCH-030 | 완료 | BellaHez | `feat/patch-030-generation-stability` | 버그 수정 | 높음 | 로컬 Ollama 답변 안정성, 근거 조건 검증과 Streamlit 호환성 개선 | Ollama 호출을 `localhost:11434` 전용으로 정리하고 temperature 0·context 4096으로 법률 답변의 일관성과 메모리 사용을 개선한다. `그 다음 날부터`·`등기가 없는 경우에도` 조건의 의미 반전을 프롬프트·결정적 교정·검증으로 차단하고, 생성 청크가 없을 때만 샘플 청크를 사용하는 fallback을 추가하되 검색 순위·임베딩·쿼리 확장 로직은 변경하지 않는다. 폐기 예정 `st.components.v1.html`을 `st.iframe`으로 교체하고 전체 테스트 450개·하위 테스트 50개 통과, 선택형 PDF 통합 테스트 2개 스킵, Streamlit HTTP 200·로컬 Ollama 실제 질의 `answered`를 확인한다. | PATCH-021, PATCH-024, PATCH-029 | - | 2026-08-31 | 2026-08-31 | `efc3103` |
| [x] | PATCH-032 | 완료 | kimjeongjaeae | `feat/patch-032-generation-validation-hardening` | 기능 변경 | 높음 | LangSmith 실행 추적과 LangGraph 기반 Generation workflow 오케스트레이션 | LangSmith tracing을 연결하고 Streamlit의 기존 멀티턴 흐름을 유지한 채 Generation 실행 경로를 LangGraph로 전환한다. prompt injection·scope·Retrieval·Generation·grounding·deterministic validation·semantic validation을 실제 노드와 조건부 분기로 구성하며, 기존 `ANSWER/ABSTAIN/REFUSE`·abstention·검색 건수·Qwen 설정·검증 기준은 변경하지 않는다. LangGraph·Generation·Streamlit 회귀 테스트를 통과하고 LangSmith에서 단계별 실행 trace를 확인했다. | PATCH-030 | PR #20 | 2026-09-01 | 2026-09-01 | `ff4da6e`, `b81e97a`, `97c6088` |
| [ ] | PATCH-033 | 보류·후속 개선 | sji21 | `feat/patch-033-minbeop-corpus-review` | 검증·기능 추가 | 중간 | 민법 임대차 조문과 조건부 라우팅 영향 검토 | 민법 임대차 조문 후보와 조건부 라우팅을 구현해 Dev·기존 Holdout 회귀, 자연어 발동·오발동을 확인했으나 독립 평가와 운영 코퍼스 재적재 없이 제출 버전에 넣지 않기로 결정했다. 브랜치는 재도입 검토용으로 보존하고 최종 시연·평가에서는 제외한다. | PATCH-026 | - | 2026-09-01 | - | `5663046` … `d76bdc0` |
| [x] | PATCH-034 | 완료 | gitcatho | `feat/patch-034-staged-evidence-routing` | 검색 개선 | 높음 | 단계형 근거 라우팅, 검색 모델 사전 로딩과 조건부 의미 검증 | 질문을 법령·기관 안내·판례 요구 유형으로 판별하고 법령·기관 안내를 먼저 검색한다. 1차 근거로 직접 답할 수 있으면 판례를 생략하며, 판례를 명시적으로 요구하거나 1차 근거가 부족한 경우에만 판례를 추가한다. 선택된 근거만 생성 LLM과 검증기에 전달하고 기존 ANSWER·ABSTAIN·REFUSE 흐름 및 검색 상한을 보존한다. Streamlit 시작 시 KURE-v1 검색 서비스를 준비 상태 안내와 함께 한 번만 사전 로딩·캐시한다. 판례·기관 안내·숫자·시점·조건·예외 등 의미 변형 위험이 있는 답변에만 Qwen 의미 검증을 수행하고, 단순 법령 답변은 결정론적 검증으로 끝낸다. Dev 27문항의 상태·문항별 응답 시간·의미 검증 실행 여부를 기록하고 회귀 테스트를 통과한다. | PATCH-030 | - | 2026-09-01 | 2026-09-01 | `e2e84df` |
| [x] | PATCH-035 | 완료 | BellaHez | `feat/patch-035-ollama-and-local` | 기능 변경 | 높음 | RunPod Ollama 우선 호출과 로컬 Ollama 자동 전환 | `JEONSEON_LLM_BASE_URL`이 설정되면 RunPod Ollama를 우선 사용하고 연결 실패·모델 부재·생성 호출 실패 시 같은 모델이 설치된 `http://localhost:11434`로 자동 전환한다. 원격 URL을 설정하지 않으면 기존처럼 로컬 Ollama만 사용하며, RunPod 프록시 호환 요청 헤더·상태 진단·사용 중인 엔드포인트 안내와 회귀 테스트·README 설명을 함께 제공한다. | PATCH-021, PATCH-032 | - | 2026-09-01 | 2026-09-01 | `8debb71` |
| [x] | PATCH-036 | 완료 | yoonjihwan402 | `feat/patch-036-document-rag-graph` | 기능 변경 | 높음 | 세션 문서 RAG와 Graph 답변 경로 통합 | 채팅 입력창에서 PDF·JPG·PNG 여러 개를 첨부해 세션 OCR 페이지를 BM25로 찾고, 공식 검색 결과와 함께 같은 Graph의 생성·근거 검증 경로로 전달한다. 문서와 공식 근거는 답변 출처에서 구분하며 OCR 원문은 Graph 상태·문서 질의 LangSmith 추적에 넣지 않는다. 원본 구현 커밋은 main의 직접 조상이 아니며 PATCH-037 재적용 브랜치에서 기능을 함께 반영했다. 문서 첨부 후 일반 질문이 막히고 문서 사실에 무관한 법조문이 붙는 기능 오류는 PATCH-037에서 수정했다. | PATCH-031, PATCH-035 | PR #21 (재적용 포함) | 2026-09-01 | 2026-09-01 | `1a06251`, `b48637f` (원본·main 외) |
| [x] | PATCH-037 | 완료 | BellaHez·sji21 | `feat/patch-037-document-rag-upload-fix` | 버그 수정 | 높음 | 문서 OCR 분석과 일반질문 이슈 픽스 | 문서를 첨부한 뒤 일반 질문이 막히던 문제와, 문서에 적힌 사실에 무관한 법조문이 붙던 문제를 고친다. 문서 전용 질문은 공식 검색 상한을 0으로 낮춰 법령·판례를 아예 열지 않고, 문서 근거만으로 답할 때는 공식 출처명을 강제하지 않는다. 등기 위험 규칙과 범위 판정 어휘도 함께 보완한다. 비고: 원본 `feat/patch-037-document-upload-issue-fix`(BellaHez)가 PATCH-034·035 병합 이전에서 갈라져 있어, 최신 main 위의 `feat/patch-037-document-rag-upload-fix`로 다시 얹었다(sji21). `data/sample/chunks_expanded.jsonl` 변경은 제외했다. 병합 과정에서 문서 전용 질문이 `UnboundLocalError`로 죽는 오류를 발견해 함께 고쳤다. 원본 브랜치는 머지 후 삭제했다. | PATCH-034, PATCH-036 | PR #21 | 2026-09-01 | 2026-09-01 | `1a06251`, `b7c96af` |

## 현재 작업 경계

- 현재 완료 패치: `PATCH-014` (PR #1 병합, `PATCH-013` 포함)
- 현재 완료 패치: `PATCH-016` (PR #3 병합)
- 현재 완료 패치: `PATCH-017` (PR #4 병합)
- 현재 완료 패치: `PATCH-018` (PR #5 병합)
- 현재 완료 패치: `PATCH-019` (PR #6 병합, 판례 전용 비교·평가)
- 현재 완료 패치: `PATCH-020` (PR #7 병합, 홀드아웃 평가·공식 안내)
- 현재 완료 패치: `PATCH-021` (PR #9 병합, 생성 코어)
- 현재 완료 패치: `PATCH-022` (공식 판례 원천 JSONL 표준 변환·재생성 경로, PR #10)
- 현재 완료 패치: `PATCH-025` (PATCH-022 리뷰 보완: 공식 API 검증·안전 변환·DB 이관, PR #12)
- 현재 완료 패치: `PATCH-028` (공식 판례 안전 발행 보완·판례 전용 홀드아웃 평가)
- 현재 완료 패치: `PATCH-029` (Streamlit 챗봇 UI·멀티턴 후속 질문·출처 표시 개선, PR #16)
- 현재 완료 패치: `PATCH-030` (로컬 Ollama 답변 안정화·근거 조건 검증·Streamlit 호환성)
- `PATCH-030` 검증: 전체 테스트 450개·하위 테스트 50개 통과, 선택형 PDF 통합 테스트 2개 스킵. `src/retrieval/service.py`는 생성 청크 누락 시 샘플 청크를 연결하는 fallback만 추가했으며 검색 순위·임베딩·쿼리 확장은 변경하지 않았다
- 현재 완료 패치: `PATCH-032` (LangSmith 실행 추적·LangGraph 기반 Generation workflow 오케스트레이션, PR #20. 기존 Streamlit → `conversation.py` 멀티턴 흐름은 유지하고, prompt injection·scope·Retrieval·Generation·grounding·deterministic validation·semantic validation을 LangGraph 노드와 조건부 edge로 연결했다. `chain.py`·`abstention.py`·`validation.py`·`src/retrieval/*`의 기존 판단 기준과 검색 설정은 변경하지 않았다)
- `PATCH-032` 검증: 전체 테스트 471개·하위 테스트 50개 통과, 선택형 테스트 2개 스킵. 남은 오류 2건은 사전 존재하던 Windows 환경변수 32767자 제한에 따른 `tests/test_pdf_extraction.py` 오류로 이번 LangGraph 작업과 무관하다
- 현재 완료 패치: `PATCH-034` (단계형 근거 라우팅·KURE-v1 사전 로딩·조건부 의미 검증)
- 현재 완료 패치: `PATCH-035` (RunPod Ollama 우선 호출·로컬 Ollama 자동 전환)
- 현재 완료 패치: `PATCH-036` (세션 문서 RAG·Graph 답변 경로 통합). 기능 오류는 PATCH-037에서 수정했다
- 현재 완료 패치: `PATCH-037` (문서 OCR 분석·일반질문 이슈 픽스, PR #21). 원본 브랜치가 최신 main 이전에서 갈라져 있어 3-way 병합으로 재적용했고, `data/sample/chunks_expanded.jsonl`은 제외했다. 전체 테스트 505개 통과(실패 1건은 `LANGSMITH_TRACING` 미설정으로 브랜치 무관)
- 생성 파트는 근거를 법령 3건·판례 2건과 공식 안내 최대 2건만 쓴다(`docs/retrieval-handoff.md` 의 건수 조절 안내). 5+5 로는 8B 모델이 초점을 잃어 오답을 냈고, 3+2 로 줄이자 같은 문항이 정답으로 바뀐 측정 결과에 따른 것이다. 더 큰 모델로 바꾸면 재측정해야 한다
- `PATCH-015`는 생성 담당이 완료해 병합됨(PR #2)
- 임베딩 모델: `nlpai-lab/KURE-v1` (1024차원) — 모델 비교 결과로 확정
- PATCH-020 당시 검색 파트 검증: 전체 테스트 189개 통과(스킵 2, 사전 존재하던 Windows 환경변수 길이 오류 2건은 `tests/test_pdf_extraction.py` 소관)·`pip check`·청크 규격 검사 통과(운영 코퍼스 165청크 = 법령 133·판례 26·안내 6, 실험용 샘플 135청크는 별도). 최신 통합 검증은 PATCH-037 기록을 따른다
- 병행 리뷰: `PATCH-005`는 Windows 팀원 검증 결과 기록 대기
- 이미 작성된 후속 패치 코드는 아직 커밋 대상이 아니며 각 패치 차례에 별도로 검토·검증한다.

## 검색 파트 후속 과제

이미 구현·실험한 기반과 실제로 남은 조건을 함께 기록한다. 자세한 배경은
`docs/retrieval-handoff.md` 6절을 따른다. PATCH-033은 실험 브랜치가 있으나 제출에서
제외했으므로 위 표와 아래 후속 과제 양쪽에서 상태를 명시한다.

| 과제 | 완료된 기반 | 실제 남은 일·선행 조건 |
| --- | --- | --- |
| 검증된 판례 코퍼스 확대·재평가 | 수집·파싱·검증·적재 파이프라인과 26건 기준 최종 평가 완료 | 추가 판례의 출처·사건정보·판결요지·주택임대차 적합성을 검토하고 Dev·Holdout 전체 재평가 |
| 법령 Holdout-v2 | 기존 18문항 1회 측정과 공개 후 회귀 확인 완료 | 다음 검색 설정 변경 전에 결과를 보지 않은 새 질문·정답을 봉인해 평가 |
| 가이드 확대·정량 평가 | 공식 안내 2문서·6청크, 주제별 0~2건 반환과 격리 회귀 테스트 완료 | 공식 안내와 관련·무관 문항을 늘린 뒤 주제 조건과 유사도 임계값 비교. 현재 수치에는 합산하지 않음 |
| TOP3·TOP2 리랭커 비교 | BM25+KURE+RRF와 운영 반환 건수 확정 | 리랭커 미구현. 검색 정확도·생성 정확도·지연시간을 함께 비교 |
| 상가 질문 순위 평가 | 상가 신호 라우팅 기능 테스트 완료 | 상가 전용 정답 라벨과 순위 평가. 주택 서비스 제출 범위 밖이므로 낮은 우선순위 |
| 법령·판례별 BM25 `b` 재측정 | 법령 `b=0.25`, 판례 `b=0.75` 초기 실험 완료 | 검증된 판례 확대와 Holdout-v2 후 재측정·운영값 채택 판단 |
| 민법 조건부 라우팅 재도입 검토 | PATCH-033 구현·Dev·기존 Holdout 회귀와 발동·오발동 테스트 완료 | 제출 버전 제외. 독립 평가와 운영 코퍼스 재적재 후 적용 여부 판단 |
| `fetch_law_mock` 샘플 보존 수정 | 덮어쓰기 위험과 복구 절차 문서화 완료 | 비법령 청크를 보존하도록 도구 수정. 현재 제출 차단 사유는 아님 |
