# 전세ON

주택임대차 법령 근거 기반 전세계약 점검 RAG 질의응답 시스템 (SKN33 3차 단위 프로젝트)

현재 초기 기능은 등기사항증명서 PDF를 첨부하면 근저당·압류·신탁·임차권 등 계약 전에 확인할 문구와 추가 확인사항을 보여준다. 이 기능은 계약 안전성을 판정하지 않으며, 후속 단계에서 LangChain 기반 공식 근거 검색과 LangGraph·LLM 챗봇을 연결한다.

## 구조

```
jeonse-on/
├─ app/                # 사용자 화면 (Streamlit)
├─ scripts/            # 문서 생성 등 개발 보조 명령
├─ src/
│  ├─ ingestion/       # 수집 · 정제 · 청킹
│  ├─ retrieval/       # 임베딩 · Vector DB · Retriever
│  ├─ generation/      # Prompt · Chain · 인용 검증
│  ├─ document_check/  # 등기 PDF 추출 · OCR · 위험 신호 규칙
│  └─ evaluation/      # 평가 지표 · 실험 비교
├─ data/
│  ├─ raw/ parsed/ chunks/ index/   # gitignore (재생성 가능)
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
