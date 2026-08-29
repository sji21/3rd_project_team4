"""LCEL 체인 — Retriever → Prompt → LLM → 답변.

흐름은 세 갈래로만 끝난다.

  refused   : 서비스 범위 밖 질문. **검색도 LLM 호출도 하지 않는다.**
  abstained : 검색은 했지만 근거가 없다. LLM 을 부르지 않고 그대로 보류한다.
  answered  : 근거가 있을 때만 LLM 을 부른다. 면책 문구는 코드가 붙인다.

검색은 `src.retrieval.service.RetrievalService` 하나만 쓴다. 어떤 검색기를
어떻게 섞는지(BM25 + KURE 하이브리드, 상가 라우팅, status 필터)는 전부 그 안에
있고 이 파일은 몰라도 된다 — docs/retrieval-handoff.md 가 정한 경계다.

## 다른 담당자의 파일과 만나는 자리

`abstention.py`(ANSWER·ABSTAIN·REFUSE 정책), `citation.py`(출처 검증),
`validation.py`(근거 밖 주장 검증)는 다른 담당자의 파일이라 여기서 구현하지
않는다. 대신 `answer_question()` 이 그 자리를 인자로 열어 둔다.

    answer_question(question, refuse_check=abstention.is_out_of_scope)

지금 기본값은 "범위 판정을 하지 않음" 이다. 아무 판정도 없는 편이, 여기서 대충
만든 규칙이 나중에 진짜 정책과 어긋난 채 굳는 것보다 낫다. 근거가 아예 없을 때의
ABSTAIN 만 기본으로 동작한다 — 그건 정책이 아니라 검색 결과가 비었다는 사실이다.
"""

from __future__ import annotations

import logging

from pathlib import Path

from typing import Callable

from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable, RunnableLambda

from src.generation import prompt as prompt_module
from src.generation import llm as llm_module
from src.generation.llm import clean_output, get_llm
from src.generation.models import Answer
from src.retrieval.service import RetrievalResult, RetrievalService

logger = logging.getLogger(__name__)

# ★ 검색이 주는 기본값(법령 5 · 판례 5)보다 적게 쓴다. 측정 결과다.
#
#   질문                  법령5·판례5              법령3·판례2
#   임차권등기명령 시기    "임대차 기간 내에" 오답   "임대차가 끝난 후" 정답
#   임차권등기 비용       "임차인 부담" 오답        "임대인에게 청구" 정답
#   경매 우선변제         47자에서 잘림            확정일자·금액 구간까지 정답
#
# 5+5 는 컨텍스트가 2,200토큰이 되는데 8B 양자화 모델은 그 안에서 초점을 잃는다.
# 눈앞의 제3조의3 ⑧을 두고 "명시적 규정이 없다"고 답한 경우까지 있었다.
#
# 대가는 정답 조문이 근거에 아예 안 들어오는 경우가 는다는 것이다(dev 27문항
# 기준 dev-003·dev-008). "흐릿한 5건"보다 "제대로 읽는 3건"이 낫다는 판단이고,
# 더 큰 모델(14B 이상)로 바꾸면 다시 올려 재측정해야 한다.
DEFAULT_K_LAW = 3
DEFAULT_K_CASE = 2

# 공식 안내는 상한이다. 검색이 질문 주제일 때만 0~2건을 내므로 무관한 질문에는
# 따라붙지 않는다. 법적 근거가 아니라 실무 절차 자료라 법령·판례와 별도로 센다.
DEFAULT_K_GUIDE = 2

_SETUP_HINT = (
    "검색 인덱스를 찾지 못했습니다. docs/retrieval-handoff.md 3절 순서대로 준비하세요.\n"
    "  python -m src.ingestion.fetch_law_mock --records data/parsed/law_records.jsonl\n"
    "  python -m src.ingestion.load_laws --records data/parsed/law_records.jsonl "
    "--export data/chunks/chunks.jsonl\n"
    "  python scripts/load_case_only_demo_corpus.py\n"
    "  python -m src.ingestion.fetch_guides --records data/parsed/guide_records.jsonl\n"
    "  python -m src.ingestion.load_guides --records data/parsed/guide_records.jsonl "
    "--export data/chunks/guides.jsonl\n"
    "  python -m src.retrieval.index --chunks data/chunks/chunks.jsonl "
    "--path data/index/chroma_kurev1_1024\n"
    "  python -m src.retrieval.index --chunks data/chunks/cases.jsonl "
    "--path data/index/chroma_kurev1_1024\n"
    "  python -m src.retrieval.index --chunks data/chunks/guides.jsonl "
    "--path data/index/chroma_kurev1_1024"
)

_service: RetrievalService | None = None


# ── 검색 진입점 ────────────────────────────────────────────────

def get_default_service() -> RetrievalService:
    """검색 서비스를 한 번만 만들어 재사용한다.

    KURE-v1 이 2.3GB 라 질의마다 올리면 쓸 수 없다. Streamlit 에서는 이 함수
    대신 `@st.cache_resource` 로 감싼 팩토리를 쓰고 그 결과를 인자로 넘긴다.

    ★ 인덱스를 못 열면 어휘 검색만으로 동작하고, 그 상태가 이 캐시에 그대로
      굳는다. 품질이 떨어진 줄 모르고 답변을 평가하는 것이 가장 찾기 어려운
      문제라 로그를 남긴다. 인덱스를 만든 뒤에는 reset_default_service() 를
      부르거나 프로세스를 다시 띄워야 반영된다.
    """
    global _service
    if _service is None:
        _service = _build_service()
    return _service


def fallback_chunk_paths() -> tuple:
    """인덱스 없이 뜰 때 읽을 청크 파일들.

    ★ 검색의 `from_index` 기본값과 같아야 한다. 어긋나면 특정 묶음만 조용히
      빠진 채로 서비스가 뜬다. 안내(guide)가 추가됐을 때 실제로 그랬다.
      `tests/test_generation_chain.py`의 FallbackCorpusTests 가 두 값을 대조한다.
    """
    from src.retrieval.service import CASE_CHUNKS, GUIDE_CHUNKS, LAW_CHUNKS

    return (LAW_CHUNKS, CASE_CHUNKS, GUIDE_CHUNKS)


def _build_service() -> RetrievalService:
    try:
        return RetrievalService.from_index()
    except Exception as error:
        # 인덱스 없음·패키지 미설치·메모리 부족·검색팀 코드의 버그까지 함께
        # 삼키는 자리라, 트레이스백이 없으면 원인을 되짚을 수 없다.
        logger.warning(
            "Chroma 인덱스를 열지 못해 어휘 검색만 사용합니다: %s", error, exc_info=True
        )

    # 검색팀 모듈의 공개 이름만 쓴다. 밑줄로 시작하는 이름은 예고 없이 바뀐다.
    from src.retrieval.retriever import load_chunks

    chunks: list[dict] = []
    for path in fallback_chunk_paths():
        if Path(path).exists():          # 한쪽이 없어도 나머지로 동작해야 한다
            chunks.extend(load_chunks(path))

    if not chunks:
        raise RuntimeError(_SETUP_HINT)
    return RetrievalService(chunks, dense=None)


def reset_default_service() -> None:
    """테스트에서 캐시를 비울 때 쓴다."""
    global _service
    _service = None


# ── LCEL 체인 ─────────────────────────────────────────────────

def build_qa_chain(llm=None) -> Runnable:
    """prompt | llm | 문자열 파싱 | 후처리(사고 과정 제거 · 잘린 문장 다듬기).

    `clean_output` 을 체인 안에 두는 이유는, 체인을 직접 가져다 쓰는 쪽
    (앱의 스트리밍 등)도 같은 후처리를 거치게 하기 위해서다. 밖에서 하면
    부르는 곳마다 빠뜨릴 수 있다.
    """
    llm = llm if llm is not None else get_llm()
    return (
        prompt_module.build_qa_prompt()
        | llm
        | StrOutputParser()
        | RunnableLambda(clean_output)
    )


# ── 질문 하나 처리 ─────────────────────────────────────────────

def answer_question(
    question: str,
    service: RetrievalService | None = None,
    llm=None,
    k_law: int = DEFAULT_K_LAW,
    k_case: int = DEFAULT_K_CASE,
    k_guide: int = DEFAULT_K_GUIDE,
    refuse_check: Callable[[str], bool] | None = None,
) -> Answer:
    """질문 하나에 대해 검색 → 프롬프트 → LLM → 답변을 전부 실행한다.

    refuse_check 는 범위 밖 질문을 걸러내는 함수다(abstention.py 담당). 참을
    돌려주면 검색과 LLM 호출을 건너뛴다 — 비용도 아끼지만, 애초에 답하면 안 되는
    질문에 근거를 모아 주는 일 자체를 막는 것이 목적이다.
    """
    if refuse_check is not None and refuse_check(question):
        return Answer(
            question=question,
            status="refused",
            text=f"{prompt_module.NON_VERDICT_NOTICE}\n\n{prompt_module.DISCLAIMER}",
        )

    service = service if service is not None else get_default_service()
    result: RetrievalResult = service.search(
        question, k_law=k_law, k_case=k_case, k_guide=k_guide
    )

    # 빈 질문과 근거 없음이 여기서 함께 걸린다. 검색 쪽이 빈 질문에 빈 결과를
    # 주기로 되어 있어(docs/retrieval-handoff.md 5절) 따로 검사하지 않는다.
    if result.is_empty():
        return Answer(
            question=question,
            status="abstained",
            text=f"{prompt_module.NO_EVIDENCE_TEXT}\n\n{prompt_module.DISCLAIMER}",
        )

    chain = build_qa_chain(llm)
    try:
        raw_text = chain.invoke(
            {
                "context": prompt_module.format_context(result),
                "question": question,
            }
        )
    except Exception as error:
        # Ollama 가 꺼져 있거나 상한 시간을 넘긴 경우. 예외를 그대로 흘리면
        # 세 갈래로만 끝난다는 약속이 깨지고 부르는 쪽마다 try/except 가 붙는다.
        logger.warning("LLM 호출이 실패했습니다: %s", error, exc_info=True)
        return Answer(
            question=question,
            status="abstained",
            text=f"{prompt_module.GENERATION_FAILED_TEXT}\n\n{prompt_module.DISCLAIMER}",
            laws=tuple(result.laws),
            cases=tuple(result.cases),
            guides=tuple(result.guides),
        )

    # 근거는 찾았는데 모델이 답을 못 만든 경우. 대개 사고 과정에 토큰 예산을
    # 다 써서 답변이 시작되지도 못한 것이다.
    if not raw_text.strip():
        logger.warning(
            "모델이 빈 답변을 반환했습니다. 사고 과정이 토큰 상한(%s)을 모두 "
            "소진했을 가능성이 큽니다. JEONSEON_LLM_MAX_TOKENS 를 늘리거나 "
            "사고 과정 비활성화를 확인하세요.",
            llm_module.LLM_MAX_TOKENS,   # 값 복사가 아니라 호출 시점 값
        )
        return Answer(
            question=question,
            status="abstained",
            text=f"{prompt_module.GENERATION_FAILED_TEXT}\n\n{prompt_module.DISCLAIMER}",
            laws=tuple(result.laws),
            cases=tuple(result.cases),
            guides=tuple(result.guides),
        )

    return Answer(
        question=question,
        status="answered",
        text=f"{raw_text}\n\n{prompt_module.DISCLAIMER}",
        raw_text=raw_text,
        laws=tuple(result.laws),
        cases=tuple(result.cases),
        guides=tuple(result.guides),
    )
