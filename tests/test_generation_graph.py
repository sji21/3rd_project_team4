"""LangGraph Generation 래퍼 회귀 테스트.

기존 answer_question()의 검색·생성·검증 로직 자체는 테스트하지 않는다.
그 로직은 기존 generation 테스트가 담당한다.

여기서는 다음만 확인한다.

1. Graph가 받은 질문을 기존 answer 함수에 그대로 전달한다.
2. Graph가 기존 answer 함수의 결과를 변경하지 않는다.
3. Graph 입력 전에 개인정보가 마스킹된다.
4. Graph 입력 전에 비밀정보가 마스킹된다.
5. 일반 질문은 마스킹 과정에서 변경되지 않는다.
"""

from __future__ import annotations

from src.generation.graph import (
    answer_with_graph,
    build_generation_graph,
)


class RecordingGraph:
    """answer_with_graph()가 전달한 입력을 기록하는 테스트 대역."""

    def __init__(self, answer):
        self.answer = answer
        self.state = None
        self.config = None

    def invoke(
        self,
        state,
        config=None,
    ):
        self.state = dict(state)
        self.config = config

        return {
            "answer": self.answer,
        }


def test_generation_graph_delegates_to_existing_answer_function():
    seen_questions = []
    expected_answer = object()

    def fake_answer(question: str):
        seen_questions.append(
            question
        )
        return expected_answer

    graph = build_generation_graph(
        answer_fn=fake_answer,
    )

    question = (
        "전입신고를 하면 대항력은 언제 생기나요?"
    )

    result = graph.invoke(
        {
            "question": question,
        }
    )

    assert seen_questions == [
        question
    ]
    assert result["answer"] is expected_answer


def test_answer_with_graph_returns_existing_answer_without_change():
    expected_answer = object()
    graph = RecordingGraph(
        expected_answer
    )

    result = answer_with_graph(
        "확정일자는 왜 필요한가요?",
        graph=graph,
    )

    assert result is expected_answer


def test_answer_with_graph_masks_phone_before_graph_input():
    expected_answer = object()
    graph = RecordingGraph(
        expected_answer
    )

    question = (
        "제 전화번호는 010-1234-5678인데 "
        "대항력은 언제 생기나요?"
    )

    answer_with_graph(
        question,
        graph=graph,
    )

    traced_question = (
        graph.state["question"]
    )

    assert (
        "010-1234-5678"
        not in traced_question
    )
    assert (
        "010-****-5678"
        in traced_question
    )


def test_answer_with_graph_masks_secret_before_graph_input():
    expected_answer = object()
    graph = RecordingGraph(
        expected_answer
    )

    question = (
        "API_KEY=abcdefghijklmnop "
        "대항력은 언제 생기나요?"
    )

    answer_with_graph(
        question,
        graph=graph,
    )

    traced_question = (
        graph.state["question"]
    )

    assert (
        "abcdefghijklmnop"
        not in traced_question
    )
    assert (
        "[REDACTED_SECRET]"
        in traced_question
    )


def test_answer_with_graph_preserves_normal_question():
    expected_answer = object()
    graph = RecordingGraph(
        expected_answer
    )

    question = (
        "임차권등기명령은 언제 신청할 수 있나요?"
    )

    answer_with_graph(
        question,
        graph=graph,
    )

    assert (
        graph.state["question"]
        == question
    )


def test_answer_with_graph_sets_trace_run_name():
    expected_answer = object()
    graph = RecordingGraph(
        expected_answer
    )

    answer_with_graph(
        "대항력은 언제 생기나요?",
        graph=graph,
    )

    assert graph.config == {
        "run_name": "jeonseon_generation_graph",
    }
