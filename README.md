# 전세ON

주택임대차 법령 근거 기반 전세계약 점검 RAG 질의응답 시스템 (SKN33 3차 단위 프로젝트)

현재 초기 기능은 등기사항증명서 PDF를 첨부하면 근저당·압류·신탁·임차권 등 계약 전에 확인할 문구와 추가 확인사항을 보여준다. 이 기능은 계약 안전성을 판정하지 않으며, 후속 단계에서 LangChain 기반 공식 근거 검색과 LangGraph·LLM 챗봇을 연결한다.

## 구조

```
jeonse-on/
├─ app/                # 사용자 화면 (Streamlit)
├─ scripts/            # 문서 생성 등 개발 보조 명령
├─ src/
│  ├─ database/        # 법령 · 판례 관계형 DB와 Chroma 초기화
│  ├─ ingestion/       # 수집 · 정제 · 청킹
│  ├─ retrieval/       # 임베딩 · Vector DB · Retriever
│  ├─ generation/      # Prompt · Chain · 인용 검증
│  ├─ document_check/  # 등기 PDF 추출 · OCR · 위험 신호 규칙
│  └─ evaluation/      # 평가 지표 · 실험 비교
├─ data/
│  ├─ raw/ parsed/ chunks/           # gitignore (재수집/재생성 가능)
│  ├─ database/        # SQLite 관계형 DB (gitignore)
│  ├─ index/           # Chroma Vector DB (gitignore)
│  ├─ eval/            # Dev · Holdout 평가셋, 실험 로그 (커밋)
│  ├─ sample/          # 공개 가능 샘플 문서 (커밋)
│  └─ manifest.jsonl   # 원문 추적 (커밋)
├─ tests/
├─ docs/
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

## 지식 DB 구조

전세ON은 법령·판례·정부 가이드의 원문 관계를 보존하는 **SQLite 관계형 DB**와 검색 속도를 위한 **Chroma Vector DB**를 함께 사용한다. MVP는 별도 서버 없이 실행할 수 있도록 SQLite를 사용하며, 다중 사용자 서비스로 확장할 때 같은 관계 구조를 PostgreSQL로 이전할 수 있다.

| 저장소 | 기본 경로 | 역할 | 원본 여부 |
| --- | --- | --- | --- |
| 원문 파일 | `data/raw/` | 공식 API·PDF·HTML 원문 보관 | 원본 |
| SQLite | `data/database/knowledge.sqlite3` | 법령 버전, 조항, 판례, 가이드, 위험 규칙과 출처 관계 관리 | 기준 DB |
| Chroma | `data/index/chroma/` | 청크 임베딩과 유사도 검색 | 재생성 가능한 파생 인덱스 |
| 평가셋 | `data/eval/` | Dev·Holdout 질문과 정답 근거·실험 결과 | 평가 기준 |

SQLite와 Chroma 생성물은 원문에서 다시 만들 수 있고 사용자 환경마다 경로가 다를 수 있으므로 Git에 커밋하지 않는다. 저장소에는 스키마, 초기화 코드, 공개 평가셋과 `data/manifest.jsonl`만 포함한다.

### DB 초기화

```bash
python scripts/init_databases.py
```

기본 실행 결과:

```text
data/database/knowledge.sqlite3
data/index/chroma/
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
  --chroma-path data/index/chroma \
  --collection knowledge_chunks
```

초기화는 멱등적이다. 같은 명령을 다시 실행해도 테이블이나 컬렉션을 중복 생성하지 않는다. 현재 초기화는 스키마와 빈 검색 컬렉션을 만들며, 공식 문서 수집·파싱·청킹·임베딩 적재는 후속 ingestion/indexing 단계에서 수행한다.

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

`chunks.chunk_id`를 Chroma 문서 ID로 그대로 사용한다. Chroma 메타데이터에는 최소한 다음 식별자를 넣는다.

```json
{
  "chunk_id": "law-housing-v1-article-3-3-0",
  "document_id": "doc-law-v1",
  "source_type": "law",
  "article_id": "article-3-3",
  "case_id": "",
  "guide_id": "",
  "status": "current",
  "effective_from": "2026-01-01"
}
```

Retriever는 Chroma에서 유사한 `chunk_id`를 찾고 SQLite에서 조문 번호, 법령 버전, 사건번호, 시행일과 공식 URL을 다시 조회한다. 따라서 Chroma를 삭제하거나 임베딩 모델을 바꾸더라도 SQLite와 원문으로 검색 인덱스를 재생성할 수 있다.

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
- `docs/planning/project-plan.md` — 프로젝트 범위, 아키텍처, 평가와 단계별 실행 기획
- `docs/planning/jeonseon-project-plan.pdf` — 팀 공유용 프로젝트 실행 기획서
- `docs/planning/assets/` — 파이프라인과 프로젝트 단계 참고 이미지
- `docs/planning/reference/` — 기획서 작성에 사용한 기준 자료
