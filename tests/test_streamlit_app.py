"""전세ON Streamlit 챗봇 초기 화면과 질문 처리 테스트."""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType

from streamlit.testing.v1 import AppTest


APP_PATH = Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"


class FakeAnswer:
    status = "answered"
    text = "테스트 답변입니다."
    raw_text = text

    @staticmethod
    def sources() -> list[dict]:
        return []


def install_ui_test_stubs(monkeypatch) -> None:
    """UI 테스트가 실제 검색 인덱스와 LLM을 준비하지 않게 한다."""

    dotenv_module = ModuleType("dotenv")
    dotenv_module.load_dotenv = lambda *_args, **_kwargs: True

    chain_module = ModuleType("src.generation.chain")
    chain_module.answer_question = lambda *_args, **_kwargs: FakeAnswer()

    # Streamlit의 Generation 진입점이 LangGraph로 바뀌었으므로
    # UI 테스트에서도 해당 import 경계만 같은 FakeAnswer로 대체한다.
    graph_module = ModuleType("src.generation.graph")
    graph_module.answer_question = lambda *_args, **_kwargs: FakeAnswer()

    conversation_module = ModuleType("src.generation.conversation")

    class ResolvedQuestion:
        standalone = "독립 질문"
        used_history = False

    conversation_module.resolve_question = (
        lambda _question, _messages: ResolvedQuestion()
    )

    models_module = ModuleType("src.generation.models")
    models_module.Answer = FakeAnswer

    monkeypatch.setitem(sys.modules, "dotenv", dotenv_module)
    monkeypatch.setitem(sys.modules, "src.generation.chain", chain_module)
    monkeypatch.setitem(sys.modules, "src.generation.graph", graph_module)
    monkeypatch.setitem(
        sys.modules,
        "src.generation.conversation",
        conversation_module,
    )
    monkeypatch.setitem(sys.modules, "src.generation.models", models_module)


def load_app(monkeypatch) -> AppTest:
    install_ui_test_stubs(monkeypatch)
    app = AppTest.from_file(APP_PATH)
    return app.run(timeout=20)


def test_initial_screen_is_chat_first_without_quick_questions(monkeypatch) -> None:
    app = load_app(monkeypatch)

    assert not app.exception
    assert len(app.chat_input) == 1
    assert app.chat_input[0].placeholder.startswith("예: 전입신고")
    assert app.sidebar.button[0].label == "🗑️ 대화 내용 지우기"

    button_labels = [button.label for button in app.button]
    assert button_labels == ["🗑️ 대화 내용 지우기"]


def test_chat_input_runs_the_existing_answer_chain(monkeypatch) -> None:
    app = load_app(monkeypatch)
    app.chat_input[0].set_value(
        "전입신고와 확정일자를 받으면 어떤 효력이 있나요?"
    )
    app.run(timeout=20)

    assert not app.exception
    assert any("테스트 답변입니다." in markdown.value for markdown in app.markdown)
