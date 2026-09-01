"""전세ON Generation의 LangGraph 관측용 래퍼.

기존 ``src.generation.chain.answer_question()``의 검색·생성·검증 정책은
이 파일에서 변경하지 않는다.

LangGraph는 현재 Generation runtime을 하나의 명시적인 실행 그래프로 감싸는
역할만 한다. Retrieval 설정, LLM 설정, 프롬프트, validation, ANSWER/ABSTAIN/
REFUSE 조건은 모두 기존 ``answer_question()``에 그대로 위임한다.

LangSmith tracing이 활성화된 경우 Graph 입력에 사용자 원문 개인정보나 비밀값이
남지 않도록, Graph에 넣기 전에 기존 프로젝트와 동일한 마스킹 규칙을 적용한다.
"""

from __future__ import annotations

import importlib
from typing import Any, Callable, TypedDict

from langgraph.graph import END, START, StateGraph

from src.document_check.privacy import mask_sensitive_text
from src.security.secret_filter import redact_secrets


AnswerCallable = Callable[[str], Any]


class GenerationGraphState(TypedDict, total=False):
    """Generation Graph가 전달하는 최소 상태."""

    question: str
    answer: Any


def _safe_question(question: str) -> str:
    """Graph trace에 넣기 전에 기존 프로젝트 규칙으로 민감정보를 가린다."""

    secret_masked = redact_secrets(question or "").text
    return mask_sensitive_text(secret_masked)


def build_generation_graph(
    answer_fn: AnswerCallable | None = None,
):
    """기존 answer_question()을 단일 노드로 실행하는 Graph를 만든다.

    ``answer_fn``을 주지 않으면 실행 시점의
    ``src.generation.chain.answer_question``을 사용한다.

    테스트에서는 가짜 함수를 주입할 수 있도록 의존성을 인자로 열어 두되,
    실제 서비스의 기존 Generation 로직은 복제하지 않는다.
    """

    def answer_node(
        state: GenerationGraphState,
    ) -> GenerationGraphState:
        runtime_answer_fn = answer_fn

        if runtime_answer_fn is None:
            # chain.py와 순환 import를 만들지 않고
            # 실행 시점에 기존 공개 진입점을 읽는다.
            chain_module = importlib.import_module(
                "src.generation.chain"
            )
            runtime_answer_fn = chain_module.answer_question

        answer = runtime_answer_fn(
            state["question"]
        )

        return {
            "answer": answer,
        }

    builder = StateGraph(
        GenerationGraphState
    )

    builder.add_node(
        "answer_question",
        answer_node,
    )

    builder.add_edge(
        START,
        "answer_question",
    )

    builder.add_edge(
        "answer_question",
        END,
    )

    return builder.compile()


# 기본 실행용 Graph는 import 시 한 번만 compile한다.
_DEFAULT_GRAPH = build_generation_graph()


def answer_with_graph(
    question: str,
    *,
    graph=None,
):
    """마스킹된 질문을 LangGraph를 통해 기존 Generation runtime에 전달한다.

    기존 ``answer_question()``의 반환값을 그대로 돌려준다.
    """

    safe_question = _safe_question(
        question
    )

    runtime_graph = (
        graph
        if graph is not None
        else _DEFAULT_GRAPH
    )

    state = runtime_graph.invoke(
        {
            "question": safe_question,
        },
        config={
            "run_name": "jeonseon_generation_graph",
        },
    )

    if "answer" not in state:
        raise RuntimeError(
            "Generation Graph가 answer를 반환하지 않았습니다."
        )

    return state["answer"]
