# 공식 주택임대차 판례 데이터 스테이징·최신 main 호환 보고서

## 기준과 범위

- 기준 커밋: `origin/main`의 `f4cd49a` (PATCH-021 포함)
- 작업 브랜치: `feat/patch-022-case-data-ingestion`
- 출처: 국가법령정보 공동활용 OPEN API의 공식 판례 상세정보
- 대상: 주택임대차 관련 민사 판례의 공식 판결요지
- 청크 규칙: 판례 1건 = 청크 1개
- 원천·SQLite·청크·Chroma는 `.gitignore` 대상이며, 이 문서는 데이터 자체가 아닌 재현·검증 상태를 기록한다.

## 현재 로컬 스테이징 산출물

| 항목 | 실제 수량 | 경로 |
| --- | ---: | --- |
| 최종 공식 후보 목록 | 348건 | `data/raw/final_phase_official_case_candidates.jsonl` |
| 공식 상세 응답 | 517건 | `data/raw/phase1_official_case_details.jsonl` |
| 표준 적재 대상 `CaseRecord` | 207건 | `data/parsed/case_records.jsonl` |
| 스테이징 SQLite 판례 | 207건 | `data/database/phase1_official_cases.sqlite3` |
| 검색용 판례 청크 | 207건 | `data/chunks/phase1_official_cases.jsonl` |
| 스테이징 Chroma 벡터 | 207건 | `data/index/phase1_official_cases_kurev1_1024/` |

SQLite를 읽기 전용으로 점검한 결과, 사건번호 중복은 0건이며 207건 모두 정확히 하나의
`case:{case_id}#0` 청크를 갖는다. 따라서 기존 프로젝트의 **판례 1건 = 청크 1개** 규칙은 유지된다.
`case_records.jsonl`은 517건 공식 상세 응답을 다시 변환해도 기존
`phase1_official_case_records.jsonl`의 207건과 사건 ID 집합이 동일함을 확인했다.

## 최신 main과의 호환성

| 최신 main의 계약 | 판례 스테이징 상태 | 판정 |
| --- | --- | --- |
| 공통 SQLite의 `documents`·`cases`·`chunks` 사용 | `src.ingestion.load_cases`가 기존 테이블만 적재 | 호환 |
| 공통 Chroma `knowledge_chunks`와 KURE-v1 1024차원 경로 | `doc_type=case` 및 동일 메타데이터 규격으로 추출 | 호환 |
| `RetrievalService`가 법령·판례·안내를 분리 반환 | 판례 청크에 `case_id`, `case_number`, `court_name`, `decision_date`, `source_url` 포함 | 호환 |
| LLM 답변은 판례를 사례로 표시하고 출처 링크는 화면이 별도 표시 | 판례 `Evidence`의 citation과 `source_url` 생성 가능 | 호환 |

판례 청크만 색인할 때 Chroma 정리 범위는 `doc_type=case`로 제한된다. 따라서 같은 컬렉션에
들어 있는 법령(`law`·`decree`·`rule`)과 안내(`guide`) 벡터는 삭제되지 않는다.

## 아직 운영 통합이 아닌 이유

현재 `data/database/knowledge.sqlite3`에는 법령·판례·청크가 모두 0건이다. 207건은
`phase1_official_cases.sqlite3`와 별도 스테이징 Chroma에만 있다. 즉 최신 검색·생성 코드와
형식은 맞지만, 기본 경로의 운영 통합 SQLite/Chroma에는 아직 동기화하지 않았다.

운영 반영은 아래 순서로만 수행한다. 두 결과물은 Git에 커밋하지 않는다.

```powershell
python -m src.ingestion.load_cases `
  --records data/parsed/case_records.jsonl `
  --database data/database/knowledge.sqlite3 `
  --export data/chunks/cases.jsonl

python -m src.retrieval.index `
  --chunks data/chunks/cases.jsonl `
  --path data/index/chroma_kurev1_1024
```

실행 전에는 같은 기본 SQLite에 적재된 실제 법령 청크와 함께 검색해야 한다. 판례만 있는
스테이징으로는 최신 `RetrievalService`의 법령·판례 결합 답변을 운영 수준으로 판정할 수 없다.

## 평가 기록의 상태

기존 `data/parsed/phase1_case_retrieval_smoke_test.json`은 **129건** 코퍼스와 19개 자동
키워드 정답군 기준의 과거 스모크 테스트다. 이 파일의 Hit@1 73.68%, Hit@5 84.21%, MRR 0.7807은
현재 207건 코퍼스 또는 최신 main의 통합 검색 성능을 의미하지 않는다.

따라서 운영 동기화 전에는 207건 입력과 실제 법령 청크를 함께 사용해 질문·정답 판례번호가
확정된 수동 평가를 다시 실행하고, 그 결과를 별도 보고서에 기록해야 한다. 특히 최우선변제,
확정일자·우선변제, 임차권등기명령은 이전 스모크 테스트에서 정답 누락이 있었으므로 재확인 대상이다.

## 이번 기준 정리의 결론

최신 main에 맞추기 위해 DB 스키마나 검색·생성 코드를 변경할 필요는 없었다. 다만 공식
상세 원천을 표준 입력으로 재생성할 수 있도록 `src.ingestion.parse_cases`를 추가했다. 이
변환기는 수동 범위 제외 3건과 중복 사건번호를 같은 규칙으로 처리해 207건을 재현한다.
원격 main에는 이 작업으로 인한 변경이나 푸시를 하지 않는다.
