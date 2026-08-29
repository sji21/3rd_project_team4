# 판례 전용 임베딩 비교 인계

PATCH-019의 판례 전용 비교는 PATCH-018의 공통 SQLite·청크·Chroma 구조 위에서
실행한다. 별도 데모 SQLite나 운영용 Chroma 컬렉션을 만들거나 수정하지 않는다.

## 입력과 경계

```text
scripts/load_case_only_demo_corpus.py
  → data/database/knowledge.sqlite3
  → data/chunks/cases.jsonl
  → data/index/chroma_kurev1_1024 / knowledge_chunks   (운영 통합 인덱스)
```

- `cases.jsonl`은 `src.ingestion.load_cases.export_case_chunks`가 생성한 표준 청크다.
- 청크 ID·`case_id`·`case_number`·출처 URL 등 PATCH-018 메타데이터를 그대로 쓴다.
- 판례 전용 실험은 27개 공통 평가 질문 중 13개만 순위 지표에 포함한다. 나머지
  14개는 현행 조문·금액·행정절차 또는 개별 사실관계가 필요하므로 보류한다.
- 현재 26개 판례 본문은 평가용 요약문이다. 실제 판례 원문으로 교체하면 모든
  비교 결과를 다시 실행해야 하며, 결과를 일반 검색 성능으로 주장하면 안 된다.

## 준비

```powershell
python scripts/load_case_only_demo_corpus.py
python -m src.retrieval.index --chunks data/chunks/cases.jsonl --path data/index/chroma_kurev1_1024
```

두 번째 명령은 판례(`doc_type=case`)만 동기화한다. PATCH-017의 색인 범위 규칙에
따라 기존 법령 벡터는 지워지지 않는다.

## 실행

### 통합 KURE-v1 인덱스 평가

```powershell
python scripts/evaluate_case_only_retriever.py
```

기본 결과는 `data/eval/runs/housing_cases_only_kurev1.json`에 쓴다. 이 경로는
재생성 가능한 산출물이며 Git에 커밋하지 않는다.

### 로컬 모델 비교

```powershell
python scripts/compare_case_embedding_models.py --models kure_v1 bge_m3
```

Qwen3까지 포함하려면 모델 다운로드와 충분한 메모리가 필요하다. 모델별 벡터는
`data/index/chroma_case_embedding_comparison`의 **실험 컬렉션**에만 저장한다.

### Hugging Face Inference Providers 비교

```powershell
$env:HF_TOKEN = "..."
python scripts/compare_case_embedding_models_hf_api.py --preflight-only
```

`HF_TOKEN`은 요청 헤더에만 쓰며 보고서와 로그에 기록하지 않는다. 전체 비교는
`--preflight-only`를 생략한다. API 모델별 벡터도
`data/index/chroma_case_hf_api_comparison`의 실험 컬렉션에만 저장한다.

## 결과 해석

- Hit@1·@3·@5·MRR은 답변 가능 13문항에서만 계산한다.
- 보류 14문항은 모든 모델에 동일한 정책이므로, 모델 품질 점수가 아니다.
- 비교 결과는 동일한 `cases.jsonl`, 동일 질문, 동일 정답 판례 ID를 사용한 경우에만
  서로 비교할 수 있다.
