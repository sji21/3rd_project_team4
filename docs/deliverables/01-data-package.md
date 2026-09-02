# `4팀_수집_및_전처리_데이터.zip` 기획틀

## 1. 목적

LENS RAG가 어떤 공식 자료를 수집했고, 어떤 규칙으로 정제·청킹했으며, 최종 검색
데이터를 어떻게 재생성할 수 있는지 증명한다. 단순 데이터 덤프가 아니라 원문 추적성과
전처리 재현성을 함께 제출한다.

## 2. 권장 ZIP 구조

```text
4팀_수집_및_전처리_데이터/
├─ README.md                         # 데이터 범위, 생성일, 사용법, 제외 항목
├─ checksums.sha256                  # 모든 제출 파일 체크섬
├─ manifest.jsonl                    # 출처·수집일·원문·파생 파일 연결
├─ 01_raw/
│  ├─ laws/                          # 국가법령정보센터 법령 원문
│  ├─ cases/                         # 공식 판례 원문 또는 API 응답
│  └─ guides/                        # HUG·국세청 등 공식 안내 원문
├─ 02_parsed/
│  ├─ law_records.jsonl
│  ├─ case_records.jsonl
│  └─ guide_records.jsonl
├─ 03_chunks/
│  ├─ laws.jsonl
│  ├─ cases.jsonl
│  ├─ guides.jsonl
│  └─ chunks_merged.jsonl
├─ 04_derived/
│  ├─ knowledge.sqlite3              # 기준 관계형 DB
│  └─ chroma_kurev1_1024/            # 제출 용량이 허용되면 포함
├─ 05_evaluation/
│  ├─ dev.jsonl
│  ├─ holdout.jsonl
│  ├─ case_holdout_current_20.jsonl
│  └─ README.md                      # 평가셋 사용·봉인 규칙
├─ 06_samples/                       # 공개 가능한 소량 샘플
└─ docs/
   ├─ 수집_및_전처리_설명서.md
   ├─ chunk-schema.md
   ├─ corpus-audit.md
   └─ document-card.md
```

Chroma 전체 제출이 제한되면 `04_derived/chroma_kurev1_1024/` 대신 작은 샘플 인덱스와
전체 인덱스 재생성 명령을 넣는다. 현재 로컬 인덱스 규모는 제출 전 다시 측정한다.

## 3. `수집_및_전처리_설명서.md` 목차

1. 데이터 수집 목적과 프로젝트 범위
2. 데이터 출처와 이용 범위
3. 수집 대상
   - 주택임대차보호법·시행령·시행규칙
   - 공식 판례
   - HUG·국세청 공식 안내
4. 수집 방법과 실행 명령
5. 원문 보존 정책
6. 파싱·정규화 규칙
7. 청크 분할 규칙
8. 필수 메타데이터와 `article_id` 규칙
9. SQLite·Chroma 적재 구조
10. 품질 검증
11. 개인정보·저작권·재배포 주의사항
12. 알려진 한계와 재수집 방법

## 4. 자료별 기록표

최종 작성 시 아래 표를 실제 값으로 채운다.

| 자료 유형 | 공식 출처 | 수집일 | 원문 수 | 파싱 레코드 | 청크 수 | 현재성 기준 | 담당 |
| --- | --- | --- | ---: | ---: | ---: | --- | --- |
| 법령 | 국가법령정보센터 | `[날짜]` | `[수]` | `[수]` | `[수]` | 현행 조문 | `[담당]` |
| 판례 | 국가법령정보센터 판례 | `[날짜]` | `[수]` | `[수]` | `[수]` | 공식 원문 확인 | `[담당]` |
| 기관 안내 | HUG·국세청 | `[날짜]` | `[수]` | `[수]` | `[수]` | 페이지 확인일 | `[담당]` |
| 평가셋 | 팀 작성·외부 작성 | `[날짜]` | `[수]` | - | - | 라벨 검수일 | `[담당]` |

## 5. 전처리 파이프라인

```text
공식 원천
  → raw 원문 및 응답 보존
  → 문서 유형별 parser
  → 표준 JSONL
  → 조문·판례·안내별 청킹
  → metadata 및 checksum 검증
  → SQLite 적재
  → KURE-v1 임베딩
  → Chroma 인덱스
```

연결할 저장소 근거:

- 수집·파싱: `src/ingestion/`
- DB 스키마: `src/database/schema.sql`
- 청크 규격: `docs/chunk-schema.md`
- 판례 적재: `docs/case-data-handoff.md`
- 기관 안내: `src/ingestion/fetch_guides.py`, `load_guides.py`
- 데이터 감사: `docs/corpus-audit.md`, `docs/document-card.md`
- 원문 추적: `data/manifest.jsonl`

## 6. manifest 필수 필드

```json
{
  "source_type": "law|case|guide",
  "title": "자료명",
  "source_url": "공식 URL",
  "collected_at": "YYYY-MM-DD",
  "raw_path": "01_raw/...",
  "parsed_path": "02_parsed/...",
  "chunk_path": "03_chunks/...",
  "sha256": "...",
  "parser_version": "기준 커밋 SHA",
  "status": "current|historical|review"
}
```

현재 저장소의 `data/manifest.jsonl`은 비어 있으므로 최종 제출 전 반드시 실제 데이터로
작성한다. 원문과 청크가 연결되지 않으면 데이터 출처를 증명하기 어렵다.

## 7. 품질 검증 체크리스트

- [ ] JSONL 전 행 파싱 가능
- [ ] `chunk_id` 중복 없음
- [ ] 필수 metadata 누락 없음
- [ ] 평가 라벨의 `article_id`가 실제 청크에 존재
- [ ] `status=current` 기준 확인
- [ ] 법령·판례·안내가 올바른 `doc_type`으로 분리
- [ ] 원문과 파생 파일 체크섬 작성
- [ ] 판례 요약문과 공식 판례 원문을 구분
- [ ] 개인정보 포함 파일 제거
- [ ] ZIP 해제 후 적재 명령 재현

## 8. 제출에서 제외할 것

- 개인이 업로드한 등기·계약서와 OCR 전문
- API 키와 `.env`
- 출처를 확인하지 못한 판례 요약문
- 임시 캐시, 모델 다운로드 파일, Python 가상환경
- 기준이 불명확한 중간 실험 결과
