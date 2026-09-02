# `4팀_RAG기반_LLM(LENS).zip` 기획틀

## 1. 목적

평가자가 별도 개발 이력을 몰라도 설치하고, 데이터베이스를 준비하고, Streamlit 챗봇을
실행하며, 테스트를 재현할 수 있는 코드 제출본을 만든다.

## 2. 권장 ZIP 구조

```text
4팀_RAG기반_LLM(LENS)/
├─ README.md
├─ START_HERE.md
├─ requirements.txt
├─ .env.example
├─ pytest.ini
├─ app/
├─ src/
├─ scripts/
├─ tests/
├─ docs/
├─ data/
│  ├─ sample/
│  ├─ eval/
│  └─ manifest.jsonl
└─ VERSION.txt                    # 기준 커밋·생성일
```

전체 원문·SQLite·Chroma는 데이터 ZIP에 둔다. 소프트웨어 ZIP에는 공개 샘플과 재생성
명령을 넣고, 최종 데모에 반드시 인덱스가 필요하면 데이터 ZIP의 복사 위치를 안내한다.

## 3. README 최종 목차

1. 프로젝트 소개와 해결 문제
2. 핵심 기능
3. 시스템 요구사항
4. 프로젝트 구조
5. 빠른 실행
6. 데이터베이스 준비
7. Ollama·Qwen3 준비
8. Streamlit 실행
9. 검색·생성 설정
10. 테스트 실행
11. 평가 재현
12. 개인정보·안전 정책
13. 알려진 한계
14. 팀원과 역할
15. 기준 버전

## 4. 빠른 실행 초안

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

ollama pull qwen3:8b-q4_K_M
python scripts/init_databases.py
# 데이터 ZIP의 청크·DB·인덱스를 안내 위치에 복사하거나 README의 적재 명령 실행

streamlit run app/streamlit_app.py
```

최종 README에는 Windows PowerShell 명령과 RunPod/Linux 명령을 분리해 적는다.

## 5. PR #17 기준 README 수정 필요사항

현재 README는 최종 코드와 다음 내용이 맞지 않으므로 제출 전에 고쳐야 한다.

- 현재 화면을 “등기 PDF 업로드 화면”으로 설명하지만 실제 화면은 챗봇이다.
- Retriever와 LLM 연결을 “후속 단계”라고 쓰지만 이미 `answer_question()`으로 연결됐다.
- `src/generation/plain_language.py`를 구조에 표시하지만 해당 파일은 없다.
- generation을 “현재 골격”으로 표현하지만 생성·인용·보류·검증이 구현됐다.
- `.env.example`는 OpenAI 후속 연결 중심 설명이며 현재 로컬 Ollama 설정을 설명하지 않는다.
- OCR·계약서 백엔드와 현재 챗봇 UI 미연결 상태를 명확히 구분해야 한다.

## 6. 실행 환경 표

| 항목 | 최종 기록 값 |
| --- | --- |
| OS | `[Windows 11 / Ubuntu 버전]` |
| Python | `3.11.x` |
| GPU | `[로컬/RunPod GPU]` |
| Ollama | `[버전]` |
| LLM | `qwen3:8b-q4_K_M` |
| Embedding | `nlpai-lab/KURE-v1` |
| Vector DB | `Chroma [버전]` |
| 관계형 DB | SQLite |
| 기준 커밋 | `[최종 SHA]` |

## 7. 의존성 관리

`requirements.txt`는 존재하지만 다수 패키지가 버전 미고정이다. 최종 제출 시 아래 중 하나를
선택한다.

- 테스트한 버전을 `requirements.txt`에 직접 고정하거나
- 상위 호환 범위는 유지하고 `requirements-lock.txt`를 추가한다.

최소한 Python, Streamlit, LangChain, Chroma, sentence-transformers, PDF/OCR 관련 패키지
버전은 테스트 보고서와 일치해야 한다.

## 8. 제출에서 제외할 것

- `.git/`, `.venv/`, `__pycache__/`, `.pytest_cache/`
- `.env`, API 키, 개인 경로
- 모델 가중치와 Hugging Face 캐시
- 개인정보가 있는 테스트 문서
- 검토되지 않은 임시 평가 실행 파일
- IDE 설정과 운영체제 임시 파일

## 9. 제출본 검증 절차

1. ZIP을 빈 디렉터리에 해제한다.
2. README만 보고 새 가상환경을 만든다.
3. `pip install -r requirements.txt`를 실행한다.
4. 데이터 ZIP 또는 샘플 데이터로 SQLite·Chroma를 준비한다.
5. `pytest -q`를 실행한다.
6. Streamlit을 실행한다.
7. 법령 질문, 가이드 질문, 범위 밖 질문을 각각 한 번 확인한다.
8. 출처 링크·보류·거절 표시를 확인한다.

## 10. 최종 체크리스트

- [ ] `requirements.txt` 필수 포함
- [ ] README의 모든 명령 실제 재현
- [ ] `.env.example`에 비밀값 없음
- [ ] 기준 커밋 기록
- [ ] 데이터 경로 설명
- [ ] Ollama 모델 준비 설명
- [ ] Windows와 Linux 실행법 구분
- [ ] 테스트 및 평가 명령 설명
- [ ] 알려진 한계와 비목표 설명
- [ ] 압축 해제 후 독립 실행 확인
