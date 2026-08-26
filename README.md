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
