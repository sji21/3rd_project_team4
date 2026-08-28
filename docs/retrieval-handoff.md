# 검색 엔진 인계 문서 (PATCH-018)

생성·앱을 맡은 팀원이 검색을 붙일 때 필요한 것만 모았습니다. 검색 내부는 몰라도
됩니다. 함수 하나로 감쌌습니다.

- 브랜치: `feat/patch-018-retrieval-entrypoint`
- 기준: `main` = `c49921d` (PATCH-017 병합 시점)

---

## 1. 무엇이 됩니까

질문 하나를 넣으면 **법령 5건과 판례 5건을 따로** 돌려줍니다.

```
질문: 전세 사는 중에 집주인이 바뀌면 보증금은 어떻게 되나요?

[법령 TOP5]                                  [판례 TOP5]
1. 주택임대차보호법 제3조의2(보증금의 회수)      1. 대법원 2011다49523 추심금 (2013-01-17 선고)
2. 주택임대차보호법 제6조의3(계약갱신 요구 등)   2. 대법원 2021다238650 구상금등청구의소
3. 주택임대차보호법 제12조(미등기 전세에의 준용) 3. 대법원 2022다279795 건물인도
4. 주택임대차보호법 제3조(대항력 등)            4. 대법원 2024다326398 임대차보증금반환
5. 주택임대차보호법 제3조의7(임대인의 정보…)   5. 대법원 2009다101275 배당이의
```

---

## 2. 쓰는 법

```python
from src.retrieval.service import RetrievalService

service = RetrievalService.from_index()      # 앱 기동 시 1회
result = service.search("전세 사는 중에 집주인이 바뀌면 보증금은 어떻게 되나요?")

result.laws                  # list[Evidence] — 법령 5건
result.cases                 # list[Evidence] — 판례 5건
result.as_prompt_context()   # 프롬프트에 그대로 넣을 문자열
result.is_empty()            # 근거를 하나도 못 찾았을 때 ABSTAIN 판정용
```

건수 조절이 필요하면 `service.search(question, k_law=3, k_case=2)`.

### Evidence 필드

| 필드 | 내용 |
| --- | --- |
| `rank` | 그 묶음 안에서의 순위 (1부터) |
| `citation` | `주택임대차보호법 제3조(대항력 등)` / `대법원 2011다49523 추심금 (2013-01-17 선고)` |
| `text` | 조문·판시 본문 |
| `score` | RRF 점수. 절대값에 의미 없고 **같은 질문 안에서의 상대 순서**만 봅니다 |
| `source_url` | 국가법령정보센터 링크 |
| `chunk_id` / `doc_type` | 추적용 |

### 모델 로딩은 반드시 1회만

KURE-v1이 2.3GB입니다. 질의마다 올리면 못 씁니다.

```python
import streamlit as st

@st.cache_resource
def get_service():
    return RetrievalService.from_index()
```

---

## 3. 실행 준비 (각자 한 번씩)

DB와 인덱스는 `.gitignore` 대상이라 저장소로 따라가지 않습니다. **받은 뒤 각자
만들어야 합니다.**

```bash
# 1. 법령 133조문을 SQLite 에 넣고 청크로 뽑기
python -m src.ingestion.fetch_law_mock --records data/parsed/law_records.jsonl
python -m src.ingestion.load_laws --records data/parsed/law_records.jsonl --export data/chunks/chunks.jsonl

# 2. 판례 26건 적재
python scripts/load_case_only_demo_corpus.py

# 3. Chroma 색인 (법령 -> 판례 순서)
python -m src.retrieval.index --chunks data/chunks/chunks.jsonl --path data/index/chroma_kurev1_1024
python -m src.retrieval.index --chunks data/chunks/cases.jsonl  --path data/index/chroma_kurev1_1024
```

3번을 두 번 나눠 실행해도 앞의 것이 지워지지 않습니다. 색인의 삭제 범위가 입력의
`doc_type` 안으로 한정되어 있습니다.

### 확인

```bash
python -c "from src.retrieval.service import RetrievalService; print(RetrievalService.from_index().search('대항력은 언제 생기나요?').as_prompt_context()[:300])"
```

컬렉션이 **159건**(law 74 · decree 59 · case 26)이면 정상입니다.

### 인덱스가 아직 없을 때

`RetrievalService(chunks, dense=None)` 으로 만들면 BM25만으로 동작합니다. 품질은
떨어지지만 앱이 뜨긴 합니다. 화면 작업 중에 색인을 기다릴 필요는 없습니다.

---

## 4. 어떤 데이터를 보면 되나

| 경로 | 내용 | 비고 |
| --- | --- | --- |
| `data/database/knowledge.sqlite3` | 원천. 법령 133조문 · 판례 26건 | gitignore |
| `data/chunks/chunks.jsonl` | 법령 청크 133건 | gitignore |
| `data/chunks/cases.jsonl` | 판례 청크 26건 | gitignore |
| `data/index/chroma_kurev1_1024` | KURE-v1 벡터 159건 | gitignore |
| `data/eval/dev.jsonl` | 평가 질문 27문항 (25개에 정답 조문) | 저장소에 있음 |
| `docs/chunk-schema.md` | 청크 규격 | 새 문서 추가 시 필독 |
| `docs/eval-questions.md` | 평가 질문 목록 | |

수록 법령은 넷입니다 — 주택임대차보호법(41청크), 같은 법 시행령(35), 상가건물
임대차보호법(33), 같은 법 시행령(24).

---

## 5. 알고 있어야 할 것

### 법령과 판례를 섞지 않습니다

한 통에 넣고 뽑으면 서로를 밀어냅니다. 섞어서 측정했을 때 법령 Hit@5가 **17.4%p**
떨어졌습니다. 프롬프트에서도 `## 관련 법령` / `## 관련 판례`로 구분을 유지하세요.
판례는 그 사건의 사실관계 위에서 나온 판단이라 조문과 같은 무게로 읽으면 안 됩니다.
섞어 넘기면 모델이 판례 문장을 법조문처럼 인용합니다.

### 상가 법령은 기본으로 빠집니다

전세ON은 주택 서비스인데 법령 133청크 중 57청크(43%)가 상가 법령입니다. 그대로 두면
주택 질문에서 상가 조문이 1위로 올라옵니다. 질문에 상가 신호(`상가`, `점포`, `가게`,
`사무실`, `권리금`, `환산보증금`)가 있을 때만 포함합니다.

| 평가셋 25문항 (전부 주택 질문) | Hit@1 | Hit@5 |
| --- | --- | --- |
| 라우팅 없음 | 40.0% | 92.0% |
| 라우팅 적용 | **76.0%** | 96.0% |

낱말 표에 없는 표현은 못 잡습니다. 사용자가 "제 가게 임대차..."가 아니라 다른 말로
쓰면 주택 범위로 처리됩니다.

### ⚠️ 판례 검색 성능은 수치로 주장하지 마세요

현재 판례 26건의 본문은 **평가 문항을 보고 작성된 요약문**입니다. 질문의 구어체
표현("집주인이 바뀐 경우", "아무 통지 없이 계약이 자동 연장되는")이 문서에 그대로
들어가 있어서, 검색이 잘 되는 것이 당연합니다. 발표에서 판례 검색 정확도를 숫자로
말하면 안 됩니다. **법령 검색 수치는 정상적으로 측정한 것이라 그대로 쓰셔도 됩니다.**

판례를 원문으로 교체하면 전부 다시 재야 합니다.

### 컨텍스트 크기

법령 5 + 판례 5가 약 **4,900자**(한국어 기준 대략 2,400토큰)입니다. 여유 있습니다.

청크는 규격상 `[법령명 제N조(제목)]` 헤더로 시작합니다(159건 전부). `as_prompt_block()`
이 그 경우 출처를 다시 붙이지 않으므로 프롬프트에 같은 문장이 두 번 들어가지 않습니다.

---

## 6. 검색 쪽에 남은 일

우리(검색 담당)가 이어서 할 것입니다. 생성·앱 작업을 막지는 않습니다.

1. **holdout 평가셋** — `data/eval/holdout.jsonl`이 아직 0줄입니다. 지금까지의
   파라미터는 전부 dev 27문항을 보면서 골랐습니다. 한 번도 안 본 문항으로 재봐야
   수치가 진짜인지 알 수 있습니다.
2. **상가 질문 평가 문항** — 라우팅의 상가 분기를 검색 성능으로 검증하지 못했습니다.
3. **묶음별 파라미터 튜닝** — 지금은 법령·판례가 같은 값을 씁니다. 측정상 법령은
   `b=0.25`, 판례는 `b=0.75`가 좋았는데 실데이터가 들어온 뒤로 미뤘습니다.
   `service.py`의 `LAW`/`CASE` 설정값만 바꾸면 됩니다.
4. **실데이터 재측정** — 판례가 원문으로 바뀌거나 법령이 늘면 전부 다시 잽니다.

---

## 7. 검증 상태

```
전체 테스트  148 passed, 2 skipped
진입점 테스트 28 passed
```

오류 2건이 함께 나오는데 `tests/test_pdf_extraction.py`의 parametrize id가 Windows
환경변수 한도(32767자)를 넘는 기존 문제입니다. 검색과 무관합니다.
