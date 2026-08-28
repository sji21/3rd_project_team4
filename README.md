# 전세ON

주택임대차 법령 근거 기반 전세계약 점검 RAG 질의응답 시스템 (SKN33 3차 단위 프로젝트)

현재 초기 기능은 등기사항증명서 PDF를 첨부하면 근저당·압류·신탁·임차권 등 계약 전에 확인할 문구와 추가 확인사항을 보여준다. 이 기능은 계약 안전성을 판정하지 않으며, 후속 단계에서 LangChain 기반 공식 근거 검색과 LangGraph·LLM 챗봇을 연결한다.

## 구조

```
jeonse-on/
├─ AGENTS.md           # Codex 작업 지침
├─ README.md
├─ app/                # 사용자 화면 (Streamlit)
├─ scripts/            # 문서 생성 등 개발 보조 명령
├─ src/
│  ├─ database/        # 법령 · 판례 관계형 DB와 Chroma 초기화
│  ├─ ingestion/       # 수집 · 정제 · 청킹
│  ├─ retrieval/       # 임베딩 · Vector DB · Retriever
│  ├─ generation/      # AI 답변 생성 Core
│  │  ├─ __init__.py
│  │  ├─ models.py     # 검색 근거 · 답변 초안 공용 모델
│  │  ├─ llm.py        # 로컬 양자화 LLM 연결
│  │  ├─ prompt.py     # 근거 기반 QA · 쉬운 설명 프롬프트
│  │  ├─ chain.py      # Retriever → Prompt → LLM 체인
│  │  ├─ citation.py   # metadata 기반 출처 조합 · 검증
│  │  ├─ abstention.py # ANSWER · ABSTAIN · REFUSE 처리
│  │  └─ validation.py # 근거 밖 주장 · 숫자/날짜/조문 검증
│  ├─ assistants/      # 사용자 보조 LLM 기능
│  │  ├─ __init__.py
│  │  └─ plain_language.py  # 어려운 법령·안내문의 쉬운 설명
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
│  ├─ eval/            # Dev · Holdout 평가셋, 실험 로그 (커밋)
│  ├─ sample/          # 공개 가능 샘플 문서 (커밋)
│  └─ manifest.jsonl   # 원문 추적 (커밋)
├─ tests/
│  ├─ test_generation_llm.py
│  ├─ test_generation_prompt.py
│  ├─ test_generation_chain.py
│  ├─ test_generation_citation.py
│  ├─ test_generation_abstention.py
│  ├─ test_generation_validation.py
│  ├─ test_plain_language.py
│  ├─ test_prompt_injection.py
│  └─ test_secret_filter.py
├─ docs/
│  ├─ chunk-schema.md
│  ├─ rag-handoff.md
│  ├─ document-card.md
│  ├─ corpus-audit.md
│  └─ planning/        # 기획서 원문·공유 PDF·구조 이미지
│     ├─ assets/
│     └─ reference/
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

## 지식 DB 구조

전세ON은 법령·판례·정부 가이드의 원문 관계를 보존하는 **SQLite 관계형 DB**와 검색 속도를 위한 **Chroma Vector DB**를 함께 사용한다. MVP는 별도 서버 없이 실행할 수 있도록 SQLite를 사용하며, 다중 사용자 서비스로 확장할 때 같은 관계 구조를 PostgreSQL로 이전할 수 있다.

| 저장소 | 기본 경로 | 역할 | 원본 여부 |
| --- | --- | --- | --- |
| 원문 파일 | `data/raw/` | 공식 API·PDF·HTML 원문 보관 | 원본 |
| SQLite | `data/database/knowledge.sqlite3` | 법령 버전, 조항, 판례, 가이드, 위험 규칙과 출처 관계 관리 | 기준 DB |
| Chroma | `data/index/chroma_kurev1_1024/` | 청크 임베딩과 유사도 검색 | 재생성 가능한 파생 인덱스 |
| 평가셋 | `data/eval/` | Dev·Holdout 질문과 정답 근거·실험 결과 | 평가 기준 |

SQLite와 Chroma 생성물은 원문에서 다시 만들 수 있고 사용자 환경마다 경로가 다를 수 있으므로 Git에 커밋하지 않는다. 저장소에는 스키마, 초기화 코드, 공개 평가셋과 `data/manifest.jsonl`만 포함한다.

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

사용자가 업로드한 등기 PDF, OCR 전체 원문과 이름·주소 등 개인정보는 공용 SQLite 또는 Chroma에 넣지 않는다. 현재는 Streamlit 세션 메모리에서만 처리하고 원본 파일을 저장하지 않는다. 향후 문서 기반 대화를 추가할 경우에도 사용자별 임시 컬렉션을 분리하고 세션 종료 시 삭제해야 한다.

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
- `docs/retrieval-handoff.md` — 검색 진입점 사용법, 실행 준비, 참고 데이터 (생성·앱 담당용)
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
레코드 순서가 바뀌어도 결과가 같으며, 조문을 빼고 다시 넣으면 빠진 조문과 그 청크가
SQLite와 Chroma 양쪽에서 사라집니다.

**Chroma 에서 지우는 범위는 입력에 들어 있는 `doc_type` 안입니다.** 법령과 판례를
같은 컬렉션에 두고 각각 따로 재색인하는 운영을 전제하기 때문입니다.

```bash
python -m src.retrieval.index --chunks cases.jsonl   # 법령은 그대로 남습니다
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
1. 상가건물 임대차보호법 제5조(보증금의 회수)      1. 대법원 2011다49523 추심금 (2013-01-17 선고)
2. 주택임대차보호법 제3조의2(보증금의 회수)        2. 대법원 2021다238650 구상금등청구의소
3. 주택임대차보호법 제6조의3(계약갱신 요구 등)     3. 대법원 2022다279795 건물인도
4. 주택임대차보호법 제12조(미등기 전세에의 준용)   4. 대법원 2024다326398 임대차보증금반환
5. 주택임대차보호법 제3조(대항력 등)              5. 대법원 2009다101275 배당이의
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

**Hit@5 96%가 이 코퍼스의 상한입니다.** 못 맞춘 한 문항(`dev-023` — "전세보증금반환보증은
어떤 제도인가요?")은 정답이 `guide-HUG-전세보증금반환보증`인데 서비스 코퍼스에 가이드
문서가 없습니다. 검색 실패가 아니라 데이터 부재이고, 라우팅은 상한을 그대로 달성했습니다.

> ⚠️ **위 표와 아래 Hybrid 절의 표는 서로 다른 코퍼스에서 측정했습니다.**
> 위 표 — 서비스가 실제로 보는 코퍼스: `data/chunks/chunks.jsonl` + `cases.jsonl`
> (159청크, **가이드 없음**, Hit@5 상한 96%).
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

청크는 규격상 `[법령명 제N조(제목)]` 헤더로 시작합니다(현재 코퍼스 159건 전부).
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

| 방식 | Hit@1 | Hit@3 | Hit@5 | Recall@5 | MRR | 정답을 못 찾은 문항 |
| --- | --- | --- | --- | --- | --- | --- |
| BM25 (용어사전) | 76.0% | 96.0% | 96.0% | 96.0% | 0.847 | dev-008 |
| KURE-v1 | 80.0% | 88.0% | 96.0% | 94.0% | 0.860 | dev-003 |
| **Hybrid RRF** | **80.0%** | 92.0% | **100.0%** | **98.0%** | **0.880** | 없음 |

**Hit@5와 Recall@5를 함께 봐야 합니다.** Hit@5는 "정답 조문 중 **하나라도**
상위 5개 안에 들어왔는가"입니다. 채점 25문항 중 6문항(`dev-001, 015, 017, 021,
022, 024`)은 정답 조문이 둘 이상이라, Hit@5 100%가 "필요한 근거를 전부 가져왔다"는
뜻은 아닙니다. 정답 비율까지 보는 Recall@5는 98.0%이고, Hybrid도 `dev-001`에서는
두 조문 중 하나만 가져옵니다. LLM에 넘기는 근거로 보면 이 문항은 아직 반쪽입니다.

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

`rrf_k`(5~100), `depth`(5~60), 가중치(2:1 ~ 1:2)를 축별로 훑어본 결과
**Hit@5는 모든 설정에서 100%, Recall@5는 98~100%**였고, 나머지 지표 차이는
문항 1~2개(= 4.0~8.0%p) 수준이었습니다. 이는 Hit@5 96% 지점의 표준오차 3.9%p와
비슷하거나 그보다 큰 폭이므로, **차이가 오차 범위 안이라고 말할 수는 없습니다.**
다만 25문항에서 한두 문항의 등락으로 설정을 고르면 그 문항에 맞춰 튜닝하는 셈이라,
관례값 `rrf_k=60`, `depth=20`, 가중치 1:1을 그대로 씁니다. 문항 수를 늘리기 전까지는
이 스윕으로 설정의 우열을 가리지 않습니다.

재현과 원자료는 다음과 같습니다.

```bash
python -m src.evaluation.compare_hybrid --sweep
```

- 비교표 원자료: `data/eval/runs/hybrid-comparison.json`
- 스윕 원자료: `data/eval/runs/hybrid-sweep.json`
