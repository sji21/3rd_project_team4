# 전세ON

주택임대차 법령 근거 기반 전세계약 점검 RAG 질의응답 시스템 (SKN33 3차 단위 프로젝트)

> **주제 미확정**: 이 저장소의 구조는 `주제선정, 기획 자료/전세ON_프로젝트_계획서.pdf` 초안을 기준으로 미리 세팅한 스캐폴드입니다. 팀 회의에서 주제가 확정되기 전까지 세부 구현은 보류합니다.

## 구조

```
jeonse-on/
├─ app/                # 사용자 화면 (Streamlit)
├─ src/
│  ├─ ingestion/       # 수집 · 정제 · 청킹
│  ├─ retrieval/       # 임베딩 · Vector DB · Retriever
│  ├─ generation/      # Prompt · Chain · 인용 검증
│  └─ evaluation/      # 평가 지표 · 실험 비교
├─ data/
│  ├─ raw/ parsed/ chunks/ index/   # gitignore (재생성 가능)
│  ├─ eval/            # Dev · Holdout 평가셋, 실험 로그 (커밋)
│  ├─ sample/          # 공개 가능 샘플 문서 (커밋)
│  └─ manifest.jsonl   # 원문 추적 (커밋)
├─ tests/
├─ docs/
│  ├─ document-card.md
│  └─ corpus-audit.md
├─ .env.example
└─ requirements.txt
```

## 실행 (예정)

```bash
pip install -r requirements.txt
cp .env.example .env   # 키 값 채우기
streamlit run app/streamlit_app.py
```

## 참고 문서

- `3th_project_basic_guide_documents/3th_project_guide.md` — 과정 공통 가이드
- `주제선정, 기획 자료/전세ON_프로젝트_계획서.pdf` — 프로젝트 계획서 초안

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
