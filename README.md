# 전세ON

주택임대차 법령 근거 기반 전세계약 점검 RAG 질의응답 시스템 (SKN33 3차 단위 프로젝트)

현재 Streamlit 챗봇은 공식 법령·판례·기관 안내를 검색해 답변한다. 같은 브라우저 세션에서는 등기사항증명서와 임대차계약서를 여러 건 추가해 OCR 페이지를 검색 근거로 함께 쓸 수 있다. 업로드 문서는 공용 DB·Chroma에 저장하지 않으며, 문서 근거와 공식 근거는 답변에서 구분한다. 이 기능은 계약 안전성을 판정하지 않는다.

## 구조

```
jeonse-on/
├─ README.md
├─ app/                # 사용자 화면 (Streamlit)
├─ scripts/            # 데이터 적재·평가·문서 생성 등 개발 보조 명령
├─ src/
│  ├─ database/        # 법령 · 판례 관계형 DB와 Chroma 초기화
│  ├─ ingestion/       # 수집 · 정제 · 청킹
│  ├─ retrieval/       # 임베딩 · Chroma · Retriever · 검색 진입점
│  ├─ generation/      # AI 답변 생성 연동 경계 (현재 골격)
│  │  ├─ __init__.py
│  │  ├─ models.py     # 검색 근거 · 답변 초안 공용 모델 경계
│  │  ├─ llm.py        # LLM 연결 경계
│  │  ├─ prompt.py     # 근거 기반 QA 프롬프트 경계
│  │  ├─ evidence_routing.py # 질문 유형·근거 충분성 기반 단계형 검색
│  │  ├─ chain.py      # Retriever → Prompt → LLM 연결 경계
│  │  ├─ citation.py   # metadata 기반 출처 조합 · 검증 경계
│  │  ├─ abstention.py # ANSWER · ABSTAIN · REFUSE 처리 경계
│  │  └─ validation.py # 근거 밖 주장 · 숫자/날짜/조문 검증 경계
│  ├─ security/        # LLM 안전장치
│  │  ├─ __init__.py
│  │  ├─ prompt_injection.py
│  │  └─ secret_filter.py
│  ├─ document_check/  # 등기 PDF 추출 · OCR · 위험 신호 규칙
│  ├─ contract_check/  # 임대차계약서 항목 · 특약 점검
│  └─ evaluation/      # 평가 지표 · 실험 비교
├─ data/
│  ├─ raw/ parsed/ chunks/           # gitignore (재수집/재생성 가능)
│  ├─ database/        # SQLite 관계형 DB (gitignore)
│  ├─ index/           # Chroma Vector DB (gitignore)
│  ├─ eval/            # Dev · Holdout 평가셋, 선별된 기준 실험 결과
│  ├─ sample/          # 공개 가능 샘플 문서 (커밋)
│  └─ manifest.jsonl   # 원문 추적 (커밋)
├─ tests/              # 기능별 단위 · 통합 · 회귀 테스트
├─ docs/               # 실행법 · 데이터 규격 · 평가 · 기획 문서
├─ .env.example
└─ requirements.txt
```

`data/`에는 RAG 수집·평가·샘플 데이터만 둔다. 프로젝트 기획 자료는 `docs/planning/`, 재사용 가능한 생성·관리 명령은 `scripts/`에 둔다.

## 실행

```bash
pip install -r requirements.txt
cp .env.example .env   # 키 값 채우기
streamlit run app/streamlit_app.py
```

Windows PowerShell에서는 `cp` 대신 다음 명령을 쓴다.

```powershell
Copy-Item .env.example .env
```

### Ollama와 RunPod 연결

기본 설정은 이 PC에서 실행 중인 Ollama(`http://localhost:11434`)를 사용한다.

```bash
ollama pull qwen3:8b-q4_K_M
ollama serve
```

RunPod의 Ollama를 직접 호출하려면 Pod 템플릿에서 `11434/http`를 공개하고 `.env`의
`JEONSEON_LLM_BASE_URL`을 현재 Pod ID에 맞게 변경한다. Pod를 새로 만들면 ID도 바뀌므로
예전 URL을 재사용하지 않는다.

```dotenv
JEONSEON_LLM_BASE_URL=https://YOUR_POD_ID-11434.proxy.runpod.net/v1
JEONSEON_LLM_MODEL=qwen3:8b-q4_K_M
```

RunPod 주소가 설정되어 있어도 연결할 수 없거나 해당 모델이 없으면 로컬
`http://localhost:11434`로 자동 전환한다. 자동 전환을 사용하려면 로컬에서도
`ollama serve`가 실행 중이고 같은 모델을 받아 둔 상태여야 한다. RunPod 주소를
설정하지 않으면 처음부터 로컬 Ollama만 사용한다.

Ollama API 자체에는 인증이 없으므로 개인 개발에서는 11434를 공개하는 대신 Full SSH
터널로 연결하는 방식을 권장한다. 터널을 사용하면 `.env`는 기본 localhost 값을 유지한다.

```bash
ssh -N -L 11434:127.0.0.1:11434 \
  root@PUBLIC_IP -p MAPPED_PORT -i ~/.ssh/id_ed25519
```

스캔 PDF를 처리하려면 Tesseract와 한국어 언어 데이터가 필요하다. 텍스트 레이어가 있는 PDF는 Tesseract 없이도 처리된다. macOS·Windows 설치법과 기능 한계는 `docs/registry-check.md`를 참고한다.

## 현재 화면 기능

- PDF 형식·크기·페이지 검증
- PDF 내장 텍스트 우선 추출
- 스캔 페이지 Tesseract OCR 보강
- 주민등록번호·전화번호·계좌번호 마스킹
- 갑구·을구 위험 신호 규칙 탐지
- 근거 문구, 추가 확인사항, 공식 참고자료 표시
- 개인정보를 제외한 JSON 결과 다운로드
- 후속 RAG Retriever용 자동 질의 생성
- 주택 임대차계약서 PDF와 휴대폰 촬영 JPG·JPEG·PNG의 핵심 작성값 탐지
- 계약서 촬영 이미지의 실제 형식·해상도 검증과 EXIF 회전 보정 후 로컬 OCR
- 공란 가능 항목과 OCR 판독 불명확 항목 구분
- 기존 특약 문구 탐지와 공식 가이드 기반 협의 항목 추천
- 앞서 탐지한 등기 위험신호와 관련 특약 연결

## 챗봇 RAG 생성 흐름

```text
사용자 질문
  → 필요한 경우 후속 질문을 독립 질문으로 재작성
  → 개인정보·비밀정보 마스킹
  → 프롬프트 인젝션·서비스 범위 검사
  → 문서 전용 질문이면 공식 검색을 열지 않음(아래 「업로드 문서 RAG」)
  → 질문 유형 판별(법령 / 기관 안내 / 판례 요청)
  → 법령·기관 안내 1차 검색
  → 유형에 맞는 1차 근거 존재 여부 확인
  → 판례 직접 요청 또는 1차 근거 부족 시에만 판례 추가 검색
  → 선택된 근거와 업로드 문서 근거를 Qwen3-8B 생성 프롬프트에 전달
  → 출력 후처리(reasoning·URL 제거, 잘린 문장 정리)
  → 근거 기반 제한적 Grounding
  → 출처·숫자·조건 결정론적 검증
  → 위험 조건에 해당할 때만 Qwen 의미 검증
  → ANSWER / ABSTAIN / REFUSE
```

일반 법령 질문에 판례를 항상 섞지 않는다. 법령이나 기관 안내만으로 직접 답할 수
있으면 판례 검색을 생략하고, 사용자가 판례를 요청하거나 질문 유형에 맞는 1차 근거를
찾지 못한 경우에만 판례를 추가한다. 이 단계는 별도 LLM 호출 없이 결정론적으로
동작해 응답 시간과 분류 실패 가능성을 늘리지 않는다. Streamlit은 앱 초기화 때
KURE-v1 검색 서비스를 한 번 사전 로딩하고 `st.cache_resource`로 재사용하므로 첫 질문에서
임베딩 모델을 새로 올리지 않는다.

실행 순서와 조건 분기는 LangGraph `StateGraph`가 담당한다(`src/generation/graph.py`).
Graph 는 새 판정 규칙을 만들지 않는다. 기존 `chain.py`·`abstention.py`·`validation.py`·
`RetrievalService` 의 함수를 그대로 호출하고 **실행 순서·상태 전달·conditional edge 만**
관리하므로, Graph 도입으로 검색 건수나 판정 조건이 달라지지 않는다.

```text
input_guard → injection_check → (필요 시 injection_semantic)
  → scope_check → (필요 시 scope_semantic)
  → retrieval → generation → grounding
  → deterministic_validation → (필요 시 semantic_validation)
  → ANSWER / ABSTAIN / REFUSE
```

생성 프롬프트는 `src/generation/prompt.py`, 단계형 근거 라우팅은
`src/generation/evidence_routing.py`, 전체 실행 순서는 `src/generation/chain.py`에 있다.
메인 프롬프트는 검색된 근거 밖의 지식 사용 금지, 실제 사용한 출처명 표시, 숫자·시점·
주체·예외 보존, 법령·판례·기관 안내의 성격 구분, 개별 계약 안전 판정 금지와 간결한
한국어 존댓말 답변을 요구한다. 면책 문구와 출처 링크는 LLM이 만들지 않고 코드가 붙인다.

작은 모델이 근거 블록의 `[1]`·`[2]` 같은 번호만 보고 출처를 혼동하지 않도록, 프롬프트
앞부분에 답변에 그대로 복사해 쓸 수 있는 출처명을 따로 정리해 넣는다.

```text
[답변에 쓸 출처명]
- 관련 법령: 주택임대차보호법 제3조
- 관련 판례: 대법원 2011다49523
- 관련 기관 안내: 주택도시보증공사 안내
```

### 업로드 문서 RAG

같은 브라우저 세션에서 등기사항증명서·임대차계약서를 첨부하면 OCR 결과를 그 세션
안에서만 검색해 근거로 쓴다. 공용 SQLite·Chroma 에는 저장하지 않는다.

```text
OCR ExtractionResult → SessionDocumentChunk → SessionDocumentRetriever
                                                    ↓
                                          SessionDocumentEvidence
```

- **공식 근거와 타입을 분리한다.** 법령·판례·안내는 `Evidence`, 업로드 문서는
  `SessionDocumentEvidence` 로 유지한다. 계약서에 적힌 문구를 법적 근거로 오인하지
  않게 하고, 공식 citation 검증과 문서 페이지 출처 표시를 다른 규칙으로 처리한다.
- **문서 검색에는 법령 용어 확장을 적용하지 않는다.** 사용자가 낸 계약서·등기 문구에
  법률 용어를 덧붙이면 원문에 없는 의미가 검색 단계에서 생긴다.
- OCR 페이지 한 쪽을 검색 단위 하나로 쓰고, 판독 불가 페이지와 빈 텍스트는 제외한다.

**문서에 적힌 사실만 묻는 질문은 공식 검색을 아예 열지 않는다.**
`answer_document_question()` 이 `_is_document_only_question()` 으로 판정해 `k_law`·
`k_case`·`k_guide` 를 0으로 낮춘다. 보증금 액수나 특약 문구처럼 답이 문서에만 있는
질문에 무관한 법령을 함께 넣으면, 작은 모델이 억지로 법조문을 인용하고 의미 검증이
그 답을 거절한다. 해석·위험 분석 질문은 기존 공식 검색을 그대로 쓴다.

공식 검색 결과와 문서 근거가 **둘 다 없을 때만** `ABSTAIN` 한다. 공식 자료가 없어도
문서에서 관련 내용을 찾았으면 문서 근거로 답하고, 둘 다 있으면 두 근거를 함께
프롬프트에 넣는다. 이때 문서 근거만으로 답할 수 있으면 공식 출처명을 강제하지 않고
`파일명 + 쪽수` 를 출처로 표시한다.

업로드 문서 근거가 포함된 질문은 LangSmith 추적을 **비활성화**한다. OCR 원문은 Graph
상태에 저장하지 않고 node closure 안에서만 쓰므로, 개발 환경에서 tracing 을 켜도
계약서·등기 원문이 외부로 전송되지 않는다.

### LLM 런타임

| 설정 | 값 |
| --- | --- |
| 모델 | `qwen3:8b-q4_K_M` |
| API | Ollama native `/api/chat` |
| Temperature | `0.0` |
| 본답변 max tokens | `256` |
| 보조 판정 max tokens | `160` |
| Context | `4096` |
| Keep alive | `30m` |
| Thinking | `false` |
| 1순위 / 대체 | RunPod Ollama / 로컬 Ollama |

OpenAI 호환 `/v1` 경로에서는 Qwen3 의 `think=false` 가 실제 요청에 안정적으로 적용되지
않아, 내부 reasoning 이 출력 토큰을 먼저 소비하고 최종 `content` 가 비거나 답변이 중간에
잘렸다. LangChain 프롬프트와 LCEL 구조는 그대로 두고 **HTTP 통신 경로만** native
`/api/chat` 으로 바꿨다. `think=false` 를 top-level 필드로 보내 서버 단계에서 끄고,
프롬프트 끝의 `/no_think` 로 한 번 더 제어한다.

### 출력 후처리

Qwen 결과를 그대로 검증에 넘기지 않는다(`src/generation/llm.py`).

```text
Qwen raw output
  → strip_reasoning()      <think>...</think> 제거
  → unlink()               모델이 만든 Markdown URL 제거
  → trim_to_last_sentence() 토큰 상한에서 잘린 미완성 문장 정리
  → clean_output()
  → Grounding / Validation
```

`strip_reasoning()` 은 reasoning 노출을 막을 뿐 아니라, **reasoning 안에 등장한 조문
번호가 실제 답변의 인용처럼 검증에 잡히는 문제**도 함께 막는다. `unlink()` 는 출처
링크를 코드가 붙이므로 필요 없기도 하고, 모델이 URL 을 쓰다 토큰 상한에 걸려 문장이
잘린 사례가 있어 넣었다.

### 멀티턴 질문 재작성

`"그럼 언제 해야 해?"` 처럼 앞 문맥 없이는 검색할 수 없는 질문이 있다. 그렇다고 모든
질문에 대화 이력을 넣으면 검색어가 길어지고 모델이 지난 답변의 숫자·조건을 현재
질문에 섞는다. `src/generation/conversation.py` 는 **문맥이 명시적으로 필요한 질문만**
독립 질문으로 바꾼다.

- `그럼`·`그러면`·`그 경우`·`그 특약`·`아까 말한` 같은 표현이 있을 때만 재작성
- 최근 `answered` 대화만 사용하고, 최대 2개 대화쌍·2,400자까지만 참고
- `ABSTAIN`·`REFUSE` 된 대화는 다음 질문의 근거로 쓰지 않음
- 재작성 결과에 대화에 없던 숫자나 핵심 조건이 생기면 폐기
- 원 질문의 핵심 용어나 부정 의미가 사라지면 폐기
- 재작성 LLM 호출이 실패해도 원 질문으로 기존 흐름을 계속 실행

장기 메모리를 만드는 장치가 아니라 **검색 가능한 질문을 안전하게 복원하는 전처리**다.

### 답변 검증

프롬프트를 강화해도 생성 모델이 근거의 의미를 항상 보존하지는 않는다. 법률 문장은
시점이나 부정 표현 한 단어로 결론이 뒤집히므로 생성 이후 검증 계층을 따로 둔다.

실제로 확인된 오류다.

```text
근거: "주민등록을 마친 때에는 그 다음 날부터 효력이 생긴다"
생성: "전입신고를 마친 날부터 효력이 생깁니다"        ← 시점 변형

근거: "그 등기가 없는 경우에도 ..."
생성: "대항력을 위해 등기가 필요합니다"              ← 조건 반전
```

**제한적 Grounding** — 모든 문장을 고치지 않는다. 근거에 해당 조건이 분명히 있고 생성
답변이 같은 법적 개념을 말할 때만 적용하고, 남은 오류는 아래 검증에서 다시 본다.

**결정론적 검증** — LLM 없이 코드가 먼저 본다. 실패하면 추가 Qwen 호출 없이 즉시
`ABSTAIN` 한다.

- 실제 검색 결과에 없는 법령·판례·기관 안내 인용
- 근거에 없는 직접 인용, 금액·비율·기간·날짜, 조문 항 번호
- 핵심 시점과 조건의 의미 반전, 답변의 안전성 단정
- **같은 금액의 법적 역할 오용** — 소액임차인 규정에서 *우선변제 대상이 되는 보증금
  범위*(`eligibility`)와 *실제로 우선변제받는 일정액*(`payout`)은 역할이 다르다. 값이
  맞아도 역할을 바꾸면 오답이므로 둘을 구분해 검사한다. 목록형 답변에서는 금액이 적힌
  줄뿐 아니라 바로 앞 설명 헤더까지 함께 본다.

**의미 검증** — 코드로 잡기 어려운 변형만 보조 Qwen 이 확인한다. 조건·예외 누락, 시점
변형, 긍정·부정 반전, 임대인·임차인 주체 교체, 판례를 일반 법규처럼 단정, 기관 안내를
법적 의무처럼 표현, **업로드 문서의 사실과 공식 법적 근거의 혼동**이 대상이다. 공식
근거와 문서 근거는 의미 검증에도 따로 전달해, 계약서에 적혀 있다는 이유만으로 그
문장이 법률상 요건처럼 판단되지 않게 한다.

검색 단계에서 정답 근거 자체가 없었던 실패는 생성 오류와 구분해 기록한다. 그 문항을
통과시키려고 인용 검증이나 검증기를 느슨하게 바꾸지 않는다.

| 상태 | 의미 |
| --- | --- |
| `answered` | 검색 근거로 생성한 답변이 최종 검증까지 통과 |
| `abstained` | 근거 없음, 생성 실패, 빈 응답 또는 검증 실패 |
| `refused` | 프롬프트 인젝션 또는 서비스 범위 밖 요청을 생성 전에 차단 |

검증을 통과하지 못한 생성 원문은 대체 답변으로도 노출하지 않는다.

### 설계 판단 기록

- **근거를 5+5 에서 3+2 로 줄였다.** 법령·판례를 각각 5건씩 넣으면 약 2,200토큰이
  되는데, 8B 양자화 모델이 그 안에서 핵심 조문에 집중하지 못해 임차권등기명령의
  시점이나 비용처럼 **검색된 조문에 적힌 내용을 반대로 답하는** 사례가 나왔다. 3+2 로
  줄이자 같은 문항이 정답으로 바뀌었다. 검색 후보를 많이 소비하기보다 현재 모델이
  정확히 읽을 수 있는 근거량을 우선한다.
- **별도 쉬운 설명 LLM 을 없앴다.** 근거 기반 답변을 만든 뒤 다시 쉬운 문장으로
  재작성하는 단계가 있었는데, 호출이 하나 늘어 느려지는 것보다 **재작성 중 법률 용어와
  조건·예외·숫자의 의미가 바뀌는 것**이 문제였다. 대신 본 프롬프트에 "근거 정확성이
  쉬운 표현보다 우선"을 넣고, 법률 용어를 지우지 않되 처음 나올 때 짧은 풀이를 붙인다.
- **LLM 판단과 코드 판단을 나눴다.** 명백한 인젝션·범위 밖 질문은 결정론적 규칙이
  먼저 거르고 애매한 것만 보조 Qwen 이 본다. 본답변 자동 재시도는 끄고, 보조 판정은
  본답변보다 짧은 160토큰 상한을 쓴다. 멀티턴 재작성도 앞 대화가 실제로 필요한
  질문에만 실행한다.

## 지식 DB 구조

전세ON은 법령·판례·정부 가이드의 원문 관계를 보존하는 **SQLite 관계형 DB**와 검색 속도를 위한 **Chroma Vector DB**를 함께 사용한다. MVP는 별도 서버 없이 실행할 수 있도록 SQLite를 사용하며, 다중 사용자 서비스로 확장할 때 같은 관계 구조를 PostgreSQL로 이전할 수 있다.

| 저장소 | 기본 경로 | 역할 | 원본 여부 |
| --- | --- | --- | --- |
| 원문 파일 | `data/raw/` | 공식 API·PDF·HTML 원문 보관 | 원본 |
| SQLite | `data/database/knowledge.sqlite3` | 법령 버전, 조항, 판례, 가이드, 위험 규칙과 출처 관계 관리 | 기준 DB |
| Chroma | `data/index/chroma_kurev1_1024/` | 청크 임베딩과 유사도 검색 | 재생성 가능한 파생 인덱스 |
| 평가셋 | `data/eval/` | Dev·Holdout 질문과 정답 근거·실험 결과 | 평가 기준 |

SQLite와 Chroma 생성물은 원문에서 다시 만들 수 있고 사용자 환경마다 경로가 다를 수 있으므로 Git에 커밋하지 않는다. 저장소에는 스키마, 초기화 코드, 공개 평가셋, 선별된 기준 실험 결과와 `data/manifest.jsonl`만 포함한다. 새 실행 보고서·모델 비교 결과는 재현한 뒤 검토를 거쳐 필요한 것만 커밋한다.

### DB 초기화

```bash
python scripts/init_databases.py
```

기본 실행 결과:

```text
data/database/knowledge.sqlite3
data/index/chroma_kurev1_1024/
└─ knowledge_chunks
```

경로를 변경하려면 `.env` 또는 실행 환경에 다음 값을 지정한다.

```dotenv
JEONSEON_DATABASE_PATH=/absolute/path/to/knowledge.sqlite3
JEONSEON_CHROMA_PATH=/absolute/path/to/chroma
```

명령 인자로 일회성 경로를 지정할 수도 있다.

```bash
python scripts/init_databases.py \
  --database data/database/knowledge.sqlite3 \
  --chroma-path data/index/chroma_kurev1_1024 \
  --collection knowledge_chunks
```

초기화는 멱등적이다. 같은 명령을 다시 실행해도 테이블이나 컬렉션을 중복 생성하지 않는다. 현재 초기화는 스키마와 빈 검색 컬렉션을 만들며, 공식 문서 수집·파싱·청킹·임베딩 적재는 후속 ingestion/indexing 단계에서 수행한다.

Chroma 인덱스 디렉터리 이름에는 임베딩 모델과 차원을 넣는다(`chroma_kurev1_1024`).
**컬렉션 하나에는 차원이 하나만 존재**하므로 법령과 판례가 같은 컬렉션에 들어가려면
같은 모델이어야 하고, 모델을 바꾸면 컬렉션을 새로 만들어야 한다. 이름으로 구분해 두면
두 모델을 나란히 두고 비교할 수 있다. SQLite 원문은 모델을 바꿔도 그대로 재사용한다.

`documents.document_type`과 `chunks.source_type`은 다음 공식 자료 유형을 허용한다.

| 값 | 자료 유형 |
| --- | --- |
| `law` | 법률 |
| `decree` | 대통령령·시행령 |
| `rule` | 부령·시행규칙 |
| `case` | 판례 |
| `interp` | 법령해석·유권해석 |
| `guide` | 정부·공공기관 공식 안내 |

스키마 파일의 `CHECK` 제약 변경은 이미 생성된 SQLite 테이블을 자동 변경하지 않는다. 현재 개발 단계의 생성 DB는 필요한 데이터를 백업한 뒤 `data/database/knowledge.sqlite3`을 새로 생성해야 변경된 유형이 적용된다. 운영 데이터가 생긴 이후에는 파일 삭제 대신 별도 스키마 마이그레이션으로 테이블을 재구성해야 한다.

### 관계형 DB 테이블

스키마 원본은 `src/database/schema.sql`이다.

| 테이블 | 역할 |
| --- | --- |
| `documents` | 법령·판례·가이드 공통 출처, 기관, URL, 수집일, 체크섬과 원문 경로 |
| `laws` | 법령 자체의 고유 정보 |
| `law_versions` | 공포번호·시행일·종료일을 포함한 법령 개정 버전 |
| `law_articles` | 버전별 조·항·호와 조문 원문 |
| `cases` | 사건번호, 법원, 선고일, 판결요지와 판결문 |
| `case_law_citations` | 판례와 적용·인용 법조항의 다대다 관계 |
| `guides` | HUG·국토교통부·국세청 등 공식 실무 안내 |
| `guide_law_references` | 정부 가이드가 참고하는 법조항 |
| `risk_rules` | 등기 위험신호의 등급·안내·내부 정책 버전 |
| `risk_rule_keywords` | 위험 규칙별 OCR 탐지 키워드 |
| `rule_evidence` | 위험 규칙과 법조항·판례·가이드 중 하나의 근거 연결 |
| `chunks` | RAG 검색 단위와 원문 위치·파서 버전·체크섬 |
| `evaluation_questions` | Dev·Holdout 질문과 ANSWER·ABSTAIN·REFUSE 기대 동작 |
| `evaluation_evidence` | 평가 질문의 정답 법조항·판례·가이드 |

`schema_migrations`는 스키마 버전을 기록한다. 외래키와 `CHECK` 제약을 사용해 출처 없는 판례 인용이나, 법조항·판례·가이드를 동시에 가리키는 모호한 근거가 저장되지 않게 한다.

### 데이터 관계

```text
documents
 ├─ laws ── law_versions ── law_articles
 │                              ▲
 │                              │ N:M
 ├─ cases ── case_law_citations ┘
 │
 └─ guides ── guide_law_references ── law_articles

risk_rules ── risk_rule_keywords
     │
     └─ rule_evidence
          ├─ 법조항 1개
          ├─ 판례 1개
          └─ 가이드 1개 중 정확히 하나

law_articles ─┐
cases ────────┼─ chunks ── Chroma knowledge_chunks
guides ───────┘

evaluation_questions ── evaluation_evidence
                              ├─ law_articles
                              ├─ cases
                              └─ guides
```

법령은 현재 조문만 덮어쓰지 않고 `laws → law_versions → law_articles`로 개정 버전을 보존한다. 판례는 `case_law_citations`를 통해 판결 당시 적용하거나 인용한 조항과 연결한다. 하나의 판례가 여러 조항을 인용하고 하나의 조항이 여러 판례에서 사용될 수 있으므로 다대다 관계다.

위험 규칙은 `rule_evidence`를 통해 법적 의미를 설명하는 조항, 적용 사례를 보여주는 판례 또는 계약 전 행동을 설명하는 정부 가이드와 연결한다. `severity_basis`에는 법 조문이 직접 정한 위험인지 프로젝트 내부 점검 정책인지 구분해 기록한다.

### SQLite와 Chroma의 연결

`chunks.chunk_id`를 Chroma 문서 ID로 그대로 사용한다. **Chroma에는 JOIN이 없으므로**
검색 필터에 쓰는 값은 SQLite 조인 결과를 적재 시점에 평평하게 펼쳐 넣는다.

```json
{
  "article_id": "주택임대차보호법-제3조의3",
  "title": "주택임대차보호법",
  "doc_type": "law",
  "article_no": "제3조의3",
  "article_title": "임차권등기명령",
  "source_url": "https://www.law.go.kr/법령/주택임대차보호법/제3조의3",
  "status": "current",
  "effective_date": "2026-01-02",
  "expiry_date": "",
  "doc_id": "law-주택임대차보호법-20260102",
  "chunk_index": 0
}
```

**`article_id`는 두 종류가 있고 값이 다르다.** SQLite의 `law_articles.article_id`는
판본과 항·호를 구분하는 대리키이고, 위 메타데이터의 `article_id`는 **조문 단위 논리 ID**다.
평가셋의 정답 라벨이 후자와 문자열로 대조되므로, 대리키를 넣으면 검색은 되는데 채점이
전부 오답이 된다. 증상이 검색 품질 저하로만 보여 원인을 찾기 어렵다.

Retriever는 Chroma에서 `chunk_id`와 위 메타데이터로 후보를 좁히고, 화면에 보여줄 상세
정보가 더 필요하면 SQLite에서 추가로 조회한다. 원문과 관계는 SQLite가 기준이므로 Chroma를
삭제하거나 임베딩 모델을 바꾸더라도 검색 인덱스를 다시 만들 수 있다.

전체 규격과 적재 시 주의사항은 `docs/chunk-schema.md`를 따른다. 적재 전 검증은 다음과 같다.

```bash
python -m src.ingestion.validate_chunks data/chunks/chunks.jsonl --eval-set data/eval/dev.jsonl
```

### 개인정보 저장 정책

사용자가 업로드한 등기 PDF·계약서, OCR 전체 원문과 이름·주소 등 개인정보는 공용 SQLite 또는 Chroma에 넣지 않는다. OCR 청크는 Streamlit 세션 메모리에서만 처리하고 원본 파일을 저장하지 않는다. 첨부 문서는 같은 브라우저 세션의 후속 질문에만 사용되며, 새로고침·세션 종료·앱 재시작 뒤에는 다시 사용할 수 없다.

## 테스트

```bash
pytest -q
```

## 기획서 PDF 재생성

```bash
python scripts/build_project_plan_pdf.py
```

입력은 `docs/planning/project-plan.md`, 출력은 `docs/planning/jeonseon-project-plan.pdf`이다. PDF 생성에는 `reportlab`과 한국어 TTF 글꼴이 필요하다. macOS의 AppleGothic, Windows의 맑은 고딕과 일부 Linux Nanum/Noto 경로를 자동 탐색하며, 찾지 못하면 `.env` 또는 실행 환경의 `KOREAN_FONT_PATH`에 글꼴 경로를 지정한다.

## 참고 문서

- `docs/registry-check.md` — 등기 PDF 점검 실행법, 구조, 한계와 후속 RAG 연결
- `docs/rag-handoff.md` — LangChain Retriever와 LangGraph 연결 경계
- `docs/windows-verification.md` — Windows 설치·테스트 절차와 검증 기록
- `docs/contract-check.md` — 임대차계약서 작성 항목·특약 점검 기준과 한계
- `docs/chunk-schema.md` — 수집 문서에서 SQLite·Chroma까지의 청크 스키마와 검증 규칙
- `docs/eval-audit.md` — 검색 평가셋·실험 결과 감사와 한계
- `docs/eval-patch034-conditional-semantic.md` — 조건부 의미 검증 Dev 27문항 응답 시간과 실패 분석
- `docs/ocr-session-rag-connection.md` — 세션 OCR 문서 RAG 연결 경계와 개인정보 처리
- `docs/retrieval-handoff.md` — 검색 진입점 사용법, 실행 준비, 참고 데이터 (생성·앱 담당용)
- `docs/case-data-handoff.md` — PATCH-018 표준 판례 청크 기반 적재·평가·임베딩 비교 실행법
- `docs/planning/project-plan.md` — 프로젝트 범위, 아키텍처, 평가와 단계별 실행 기획
- `docs/planning/jeonseon-project-plan.pdf` — 팀 공유용 프로젝트 실행 기획서
- `docs/planning/assets/` — 파이프라인과 프로젝트 단계 참고 이미지
- `docs/planning/reference/` — 기획서 작성에 사용한 기준 자료

## 검색 평가 하네스 (검색 엔진 파트)

팀원의 실제 수집 파이프라인이 완성되기 전, 연습용 코퍼스로 검색기와 채점 프로그램을
먼저 개발하기 위한 구성입니다. 외부 API 키 없이 바로 실행됩니다.

```bash
python -m src.ingestion.build_mock                          # 연습용 코퍼스 생성
python -m src.evaluation.run_eval --run-id baseline          # 기준 측정
python -m src.evaluation.run_eval --run-id exp01-k8 --k 8 --compare baseline
```

- 연습용 코퍼스: `data/sample/chunks_mock.jsonl` (주택임대차보호법 20개 조문 + 가이드 2건)
- 평가 문항: `data/eval/dev.jsonl` (정답 근거는 **조문 id**로 지정 — 청킹 방식이 바뀌어도 안 깨짐)
- 실험 기록: `data/eval/runs/{run_id}.json`

실제 코퍼스로 교체할 때는 `--chunks` 경로만 바꾸면 됩니다. 청크 스키마는
`build_mock.py`가 생성하는 형식을 따릅니다.

### 검색 방식 비교

동일한 평가셋에서 BM25와 TF-IDF를 비교하고, 쉬운 설명을 추가한 코퍼스의 효과를
별도로 확인할 수 있습니다.

```bash
python -m src.evaluation.benchmark_retrievers \
  --output data/eval/runs/retriever-comparison.json
```

`enriched` 결과는 Dev 질문을 참고해 작성한 쉬운 설명을 포함하므로 튜닝 결과입니다.
일반화 성능은 별도로 작성한 `holdout.jsonl`에서 최종 확인해야 합니다.

### 법령 적재와 Chroma 인덱싱

임베딩 없이 SQLite까지 먼저 넣어 파싱 품질을 확인한 뒤, 벡터 인덱스를 만듭니다.
모델을 바꿔도 SQLite 결과는 그대로 재사용합니다.

```bash
# 1. 원천 레코드 → SQLite → 검색용 청크 JSONL
python -m src.ingestion.load_laws \
  --records data/parsed/law_records.jsonl \
  --export data/chunks/chunks.jsonl

# 2. 규격 검증 (필수 필드 · article_id 형식 · 평가 정답 존재 여부)
python -m src.ingestion.validate_chunks data/chunks/chunks.jsonl \
  --eval-set data/eval/dev.jsonl

# 3. 임베딩 → Chroma 적재
python -m src.retrieval.index --chunks data/chunks/chunks.jsonl
```

재실행하면 **입력이 현재 상태가 됩니다.** 같은 입력을 다시 넣어도 행이 중복되지 않고,
레코드 순서가 바뀌어도 결과가 같다. 조문을 빼고 `load_laws`를 다시 실행하면 SQLite와
청크 JSONL에서 빠진 조문이 사라지고, 이어서 색인 명령을 실행하면 Chroma에서도 같은
`doc_type` 범위의 오래된 벡터가 정리된다.

**Chroma 에서 지우는 범위는 입력에 들어 있는 `doc_type` 안입니다.** 법령과 판례를
같은 컬렉션에 두고 각각 따로 재색인하는 운영을 전제하기 때문입니다.

```bash
# 판례 26건 → 공통 SQLite → PATCH-018 표준 청크
python scripts/load_case_only_demo_corpus.py

# 판례 청크만 통합 Chroma에 적재. 법령 벡터는 그대로 남습니다.
python -m src.retrieval.index --chunks data/chunks/cases.jsonl
```

컬렉션 전체를 기준으로 잡으면 판례만 다시 넣었을 때 법령이 전부 "이번 입력에 없는
문서"가 되어 사라집니다. 통합 파일로 한 번에 넣는 방식도 그대로 동작합니다 — 입력에
모든 `doc_type` 이 들어 있으므로 범위가 컬렉션 전체와 같아집니다.

어떤 종류를 코퍼스에서 통째로 뺄 때만 `--prune-all` 로 범위를 넘깁니다. 기본값이
아닌 이유는 이 동작이 다른 담당자가 넣은 문서를 말없이 지울 수 있기 때문입니다.
청크 파일 경로를 잘못 준 실행이 컬렉션을 비우지 않도록, 빈 입력은 아무것도 지우지
않습니다.

임베딩 캐시는 모델명과 **청크 본문**으로 지문을 만듭니다. 청크에 설명을 덧붙이는 식으로
본문만 고쳐도 캐시가 무효화되므로, 바뀐 내용이 반영되지 않은 옛 벡터로 평가되는 일이
없습니다.

### 검색 진입점 — 법령 TOP5 + 판례 TOP5

생성 쪽이 검색 내부를 몰라도 되도록 함수 하나로 감쌌습니다. 돌려주는 것은 청크
딕셔너리가 아니라 본문과 출처가 붙은 `Evidence` 입니다.

```python
from src.retrieval.service import RetrievalService

service = RetrievalService.from_index()        # 모델 로딩 1회, 벡터는 Chroma 에서 읽음
result = service.search("전세 사는 중에 집주인이 바뀌면 보증금은 어떻게 되나요?")

result.laws     # 법령 5건  (Evidence: rank, citation, text, score, source_url)
result.cases    # 판례 5건
result.as_prompt_context()   # 프롬프트에 그대로 넣을 문자열
```

실제 결과입니다.

```
[법령 TOP5]                                    [판례 TOP5]
1. 주택임대차보호법 제3조의2(보증금의 회수)       1. 대법원 2011다49523 추심금 (2013-01-17 선고)
2. 주택임대차보호법 제6조의3(계약갱신 요구 등)    2. 대법원 2021다238650 구상금등청구의소
3. 주택임대차보호법 제12조(미등기 전세에의 준용)  3. 대법원 2022다279795 건물인도
4. 주택임대차보호법 제3조(대항력 등)             4. 대법원 2024다326398 임대차보증금반환
5. 주택임대차보호법 제3조의7(임대인의 정보 제시)  5. 대법원 2009다101275 배당이의
```

**법령과 판례를 따로 뽑습니다.** 한 통에 넣고 뽑으면 서로를 밀어냅니다 — 섞어서
측정했을 때 법령 Hit@5 가 17.4%p 떨어졌습니다. 질문 하나에 필요한 것은 "근거 조문
몇 개"와 "그 쟁점을 다룬 판례 몇 개"이지, 둘을 섞은 상위 5개가 아닙니다.

나누는 방식은 검색기마다 다릅니다. **BM25 는 코퍼스를 쪼개서** 만듭니다. IDF 가
코퍼스 전체 기준이라 "대항력"의 희소성이 법령 133조문 안에서와 판례 26건 안에서
다르기 때문입니다. **임베딩은 Chroma 컬렉션 하나를 공유**하고 `doc_type` 필터로
가릅니다. 벡터는 문서마다 독립적이라 쪼갤 이유가 없습니다.

판례 출처에 법원·사건번호·선고일을 함께 싣습니다. 사건명만으로는 무의미합니다 —
"추심금", "배당이의"는 여럿이라 그것만으로 답변에서 인용할 수 없습니다.

#### 상가 법령 라우팅

**기본 범위는 주택입니다.** 전세ON은 주택임대차 서비스인데 코퍼스의 법령 133청크 중
57청크(43%)가 상가 법령이라, 그대로 두면 주택 질문에서 상가 조문이 상위를 차지합니다.
실제로 "집주인이 바뀌면" 질문에 상가건물 임대차보호법 제5조가 1위로 올라왔습니다.

질문에 상가 신호(`상가`, `점포`, `가게`, `사무실`, `권리금`, `환산보증금`)가 있으면
제외를 풉니다. **상가로 바꾸는 것이 아니라 제외를 푸는 것**입니다 — "상가주택"처럼
둘 다 걸린 질문에서 주택 조문이 사라지면 안 되기 때문입니다.

평가셋 25문항(전부 주택 질문) 기준입니다.

| | Hit@1 | Hit@5 |
| --- | --- | --- |
| 라우팅 없음 (상가 포함) | 40.0% | 92.0% |
| **라우팅 적용** | **76.0%** | **96.0%** |

#### 처음 보는 문항으로 재본 결과 (holdout)

위 수치는 **설정을 고르는 데 쓴 문항**으로 잰 것입니다. 같은 문항으로 다시 재면 잘
나오는 게 당연하므로, 저장소를 본 적 없는 다른 AI 에게 질문 20개를 받아 봉인했다가
**한 번만** 돌렸습니다. 자세한 절차와 한계는 `docs/eval-holdout.md` 입니다.

| | n | Hit@1 | Hit@3 | Hit@5 | MRR |
| --- | --- | --- | --- | --- | --- |
| `dev` (설정을 고른 문항) | 25 | 76.0% | 88.0% | 96.0% | 0.833 |
| **`holdout`** (처음 보는 문항) | 18 | **66.7%** | **94.4%** | **94.4%** | **0.796** |

과적합의 뚜렷한 증거는 없습니다. Hit@1 이 9.3%p 낮지만 holdout 의 표준오차가 11.1%p 라
그 안이고, Hit@3 은 오히려 holdout 이 높습니다. 다만 18문항으로는 9%p 차이를 판별할 수
없으므로 **"과적합이 없다"고 단정하지도 않습니다.**

#### 공식 안내 (HUG · 국세청)

법령·판례로 답할 수 없는 질문이 있습니다. "전세보증금반환보증이 뭔가요?"는 HUG 상품
안내이지 조문이 아니고, "집주인이 세금을 안 냈는지 확인할 수 있나요?"는 제3조의7이
열람 권리를 정할 뿐 **어떻게** 열람하는지는 국세청 안내에 있습니다.

안내가 없을 때는 검색기가 엉뚱한 조문을 자신 있게 내놓았고, `is_empty()`도 False라
ABSTAIN으로 걸러지지 않았습니다. **못 찾는 것보다 나쁜 상태**였습니다.

**원문을 그대로 수집합니다**(HUG 2,807자 · 국세청 595자 → 6청크). 요약해서 넣으면
그 요약을 쓴 사람의 관점에 맞는 문서가 되고 측정도 부풀려집니다.

`result.guides`로 **따로** 돌려주고 프롬프트에서도 `## 참고 안내 (법적 근거가 아닌
기관 안내)`로 구분합니다. 법령과 한 묶음이면 모델이 안내 문장을 법조문처럼 인용하고,
조문 5칸 중 하나를 안내가 차지합니다.

| 정답 **근거**가 반환된 결과 안에 있는가 | 안내 없음 | 안내 포함 |
| --- | --- | --- |
| `dev` (25문항) | 96.0% | **100.0%** |
| `holdout` (18문항) | 94.4% | 94.4% |

**법령 검색 성능은 그대로입니다** — dev Hit@1 76.0%, holdout 66.7%로 안내 적재 전후가
같습니다. 위 dev의 4%p는 검색기가 좋아진 것이 아니라 `dev-023`의 정답 문서가 코퍼스에
들어온 것입니다.

**안내는 질문이 그 주제일 때만 나갑니다.** 고정 2건이 아니라 0~2건 가변입니다 —
관련 없으면 0건, 단일 주제면 1건, 두 주제이거나 한 청크로 부족하면 최대 2건입니다.
안내가 6청크뿐이라 아무 질문에나 검색하면 항상 상위 몇 건이 나오기 때문입니다.
유사도 임계값 대신 재현 가능한 주제 조건을 씁니다 — 문서 2건으로 문턱을 정하면 그
표본에 맞춘 값이 됩니다. 자세한 기준은 `docs/retrieval-handoff.md` 참고.

> ⚠️ **위 표와 아래 Hybrid 절의 표는 서로 다른 코퍼스에서 측정했습니다.**
> 위 표 — 서비스가 실제로 보는 코퍼스: `chunks.jsonl` + `cases.jsonl` + `guides.jsonl`
> (165청크). 법령 지표는 안내와 무관하지만, `dev-023`의 정답인 HUG 안내가 이제
> 코퍼스에 있어 근거 반환률은 100%입니다.
> Hybrid 절 — 실험용 코퍼스: `data/sample/chunks_expanded.jsonl`
> (135청크, **가이드 2건 포함**, 상한 100%).
> 두 수치를 나란히 비교하지 마세요.

이 수치는 **주택 질문에 대한 효과만** 보여줍니다. 평가셋에 상가 질문이 0문항이라
상가 분기는 검색 성능으로 검증하지 못했습니다. 질문 판정 자체는 테스트로 잠갔습니다.
낱말 표에 없는 표현은 잡지 못하는 것도 한계입니다.

> **파라미터는 지금 양쪽이 같습니다. 나눠 둔 것은 구조이지 값이 아닙니다.**
> 측정 결과 법령은 `b=0.25`, 판례는 `b=0.75` 가 좋았지만(긴 조문이 알맹이인 법령과
> 달리 판례는 길이를 눌러야 합니다) 그 튜닝은 실데이터가 들어온 뒤로 미룹니다.
> 그때 `service.py` 의 `LAW`/`CASE` 설정값만 바꾸면 됩니다.

**폐지·구버전 조문은 반환하지 않습니다.** `status=current`가 기본 필터에 들어 있습니다
(`docs/chunk-schema.md`의 규정과 같습니다). 폐지된 조문을 근거로 답하면 사용자가 지금
없는 권리를 믿게 됩니다. 옛 조문을 일부러 찾아야 하는 화면이 생기면 아래처럼 풉니다.

```python
from dataclasses import replace
from src.retrieval.service import LAW, RetrievalService

historical = replace(LAW, status="")          # status 조건만 뺀 사본
service = RetrievalService(chunks, dense, law=historical)
```

**빈 질문은 빈 결과를 냅니다.** BM25는 토큰이 없어 스스로 아무것도 내지 않지만 임베딩은
공백도 벡터로 바꿔 아무 문서나 가장 가까운 것으로 돌려줍니다. 그대로 두면 엔터만 쳐도
무관한 근거 10건이 LLM에 넘어갑니다.

청크는 규격상 `[법령명 제N조(제목)]` 헤더로 시작합니다(현재 코퍼스 165건 전부).
그 앞에 출처를 또 붙이면 같은 문장이 두 번 들어가므로, 헤더가 있으면 본문을 그대로
씁니다. `Evidence.citation` 필드는 남겨 둡니다 — 화면에 출처만 따로 보여줄 때 본문에서
헤더를 다시 떼어내지 않아도 되기 때문입니다.

법령 5건 + 판례 5건이 약 4,900자(한국어 기준 대략 2,400토큰)입니다. 상가 라우팅과
헤더 중복 제거로 6,228자에서 22% 줄었습니다. Streamlit 에서는 `RetrievalService` 를 `@st.cache_resource` 로 감싸
모델을 한 번만 올리세요.

### 임베딩 모델 — `nlpai-lab/KURE-v1` (1024차원)

같은 코퍼스·평가셋에 임베딩만 바꿔 비교한 결과입니다. (법령 135청크, 채점 25문항)

| 모델 | Hit@1 | Hit@5 | MRR | 질의(초) |
| --- | --- | --- | --- | --- |
| **nlpai-lab/KURE-v1** | **80.0%** | **96.0%** | **0.860** | 0.141 |
| BM25 (용어사전 적용) | 76.0% | 96.0% | 0.847 | 0.000 |
| BAAI/bge-m3 | 76.0% | 84.0% | 0.793 | 0.131 |
| text-embedding-3-small | 52.0% | 80.0% | 0.647 | 0.207 |

Hit@1 차이가 28%p로 표준오차(3.9%p)를 크게 넘습니다. 순위가 한국어 학습량 순서와
일치하며, KURE-v1은 bge-m3의 한국어 추가 학습본입니다. CPU에서 0.141초/질의로 API보다
빨라 GPU가 필요 없습니다. 재현은 다음과 같습니다.

```bash
python -m src.evaluation.compare_embeddings --local KURE bge
```

> 위 수치는 연습용 코퍼스 기준입니다. 실제 법령·판례가 적재되면 다시 측정해야 합니다.

### Hybrid 검색 (BM25 + KURE)

> 이 절의 수치는 **실험용 코퍼스**(`data/sample/chunks_expanded.jsonl`, 135청크,
> 가이드 2건 포함) 기준입니다. 서비스가 보는 코퍼스와 다릅니다 — 위 검색 진입점
> 절의 경고를 함께 보세요.

두 방식은 **서로 다른 문항에서만 실패합니다.** 어휘 기반은 조문번호나 법률용어처럼
정확일치가 필요한 질의에 강하고, 임베딩은 사용자가 쓰는 말과 조문의 말이 다를 때
강합니다. 순위를 합치면 서로의 빈틈을 메웁니다.

| 방식 | Hit@1 | Hit@3 | Recall@3 | Hit@5 | Recall@5 | MRR | 정답을 못 찾은 문항 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| BM25 (용어사전) | 76.0% | 96.0% | 90.0% | 96.0% | 96.0% | 0.847 | dev-008 |
| KURE-v1 | 80.0% | 88.0% | 86.0% | 96.0% | 94.0% | 0.860 | dev-003 |
| **Hybrid RRF (`rrf_k=5`)** | **80.0%** | **100.0%** | **98.0%** | **100.0%** | **98.0%** | **0.887** | 없음 |

**현재 생성 계약에는 Hit@3보다 Recall@3가 중요합니다.** 생성 모델은 법령 상위 3건만
사용합니다. Hit@3는 정답 조문 중 하나만 있어도 통과하지만 Recall@3는 필요한 정답
조문을 얼마나 모두 확보했는지 봅니다. 채점 25문항 중 6문항(`dev-001, 015, 017, 021,
022, 024`)은 정답이 둘 이상입니다. 추적용 코퍼스의 Hybrid는 Hit@3 100%여도
Recall@3는 98.0%이며, `dev-015`에서 두 조문 중 하나만 가져옵니다. Recall@5도 98.0%라
상위 5건으로 늘려도 이 문항은 아직 반쪽입니다.

```python
from src.retrieval.hybrid import HybridRetriever, Member

retriever = HybridRetriever([
    Member(bm25, "bm25", weight=1.0, expand_weight=1.0),
    Member(dense, "kure", weight=1.0, expand_weight=0.0),
])
```

**점수가 아니라 순위로 합칩니다.** BM25는 0~50 범위의 열린 점수를, 코사인은 0~1을
냅니다. 그대로 더하면 BM25가 압도합니다. RRF는 각 검색기에서 몇 등이었는지만 보므로
척도를 맞출 필요가 없습니다.

`expand_weight`를 검색기마다 따로 두는 이유는 용어 사전이 어휘 기반에서만 효과가
있기 때문입니다. 임베딩에서는 측정상 변화가 없었습니다.

`rrf_k`(5~100), `depth`(5~60), 가중치(2:1 ~ 1:2)를 축별로 훑었습니다. 생성 모델이
법령 5건을 모두 쓰던 때에는 Hit@5가 모든 설정에서 100%라 관례값 `rrf_k=60`을
유지했습니다. 이후 Qwen3-8B가 법령 상위 3건만 사용하도록 바뀌면서 `dev-003`의 제3조와
`dev-008`의 제4조가 모두 4위에서 잘리는 문제가 실제 답변 오답으로 이어졌습니다.

위 비교표의 Hit@1 80.0%는 추적용 `chunks_expanded` 코퍼스의 25문항 결과이고, 아래
Hit@1 79.2%는 실제 서비스 인덱스에서 정답 조문이 존재하는 법령 문항 24개만 채점한
결과입니다. 코퍼스와 분모가 달라 두 수치를 직접 비교하지 않습니다.

현재 서비스 인덱스의 법령 채점 24문항에서 `rrf_k=5`는 Hit@1 79.2%를 유지하면서
Hit@3를 91.7%(22/24)에서 100%(24/24)로 올리고 두 조문을 모두 3위에 넣었습니다.
따라서 **법령 묶음에만 `rrf_k=5`를 적용**합니다. 판례·안내는 평가 조건이 다르므로
관례값 60을 유지합니다. 이 결과는 dev 설정 선택 기록입니다.

`dev-001`처럼 전입신고와 확정일자의 **효과를 함께 묻는 질문**에는 법령 BM25만
`확정일자 → 우선변제권·우선하여 변제`를 문맥 확장합니다. “확정일자는 어디서
받나요?” 같은 절차 질문에는 적용하지 않습니다. 실제 서비스 인덱스에서 제3조는 2위를
유지하고 제3조의2가 7위에서 3위로 올라, 법령 24문항의 Hit@1 19/24와 Hit@3 24/24는
유지하면서 평균 Recall@3가 **97.9%에서 100%**로 개선됐습니다. 법령 평가에서는 법령
코퍼스에 존재하는 법률·시행령·시행규칙 정답만 분모에 넣습니다. 안내 정답까지 법령
Recall 분모에 넣어 계산했던 95.8%→97.9% 기록은 잘못된 범위이므로 폐기했습니다.
다른 dev 정답 순위의 하락은 없었습니다. 판례·안내는 공통 용어 확장기를 계속 사용하므로
이 보강이 번지지 않습니다.

다만 이 문맥 규칙은 확인한 dev 24문항과 공개 holdout 18문항, 총 42문항 중
`dev-001` 한 문항에서만 발동했습니다. 효과와 절차를 구분하는 도메인 방향 및 표현 변형
회귀 테스트는 타당하지만, 현재 수치만으로 일반화를 주장하지 않습니다. 확정일자의
효과·절차를 서로 다르게 묻는 질문을 추가 확보해 새 평가셋에서 다시 검증합니다.
`"없이"` 같은 일반 낱말은 조건으로 쓰지 않습니다. 부정 표현이 확정일자에 직접 붙고
신청·발급·서류·수수료 같은 절차 신호가 없거나, 우선변제·효력 등 효과 의도가 명시된
경우에만 효과 용어를 확장합니다.

변경 후 퇴행 여부만 확인하려고 이미 결과를 공개한 기존 holdout 18문항을 **두 번째로**
재측정했습니다. Hit@1은 66.7%(12/18), Hit@3·Hit@5는 94.4%(17/18)로 모두 같았고,
`holdout-005`만 3위에서 2위로 올라 순위 하락은 없었습니다. 이 재측정은 설정 선택이나
새로운 독립 성능 주장에 사용하지 않는 참고용 퇴행 확인입니다. 다음 일반화 성능 확인에는
새 holdout이 필요합니다.

재현과 원자료는 다음과 같습니다.

```bash
python -m src.evaluation.compare_hybrid --sweep
python -m src.evaluation.compare_law_top3
```

- 비교표 원자료: `data/eval/runs/hybrid-comparison.json`
- 스윕 원자료: `data/eval/runs/hybrid-sweep.json`
- 서비스 법령 TOP3 원자료: `data/eval/runs/law-top3-comparison.json`
