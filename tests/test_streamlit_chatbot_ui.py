from pathlib import Path


APP = Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"
TEXT = APP.read_text(encoding="utf-8")


def test_streamlit_ui_is_chat_first():
    assert "st.chat_message" in TEXT
    assert "st.chat_input" in TEXT


def test_streamlit_uses_generation_entrypoint():
    assert "answer_question" in TEXT
    assert "get_default_service" in TEXT


def test_ocr_is_not_wired_yet():
    assert "analyze_registry_pdf" not in TEXT
    assert "analyze_contract_document" not in TEXT


def test_user_facing_status_messages_are_descriptive():
    assert '"answered": ("근거를 확인해 답변드렸습니다.", "✅")' in TEXT
    assert '"abstained": ("답변을 바로 제공하기 어렵습니다.", "⚠️")' in TEXT
    assert '"refused": ("이 질문은 전세ON의 답변 범위에 포함되지 않습니다.", "🚫")' in TEXT


def test_sidebar_has_examples_and_visible_clear_button():
    assert "이런 질문을 해보세요" in TEXT
    assert "🗑️ 대화 내용 지우기" in TEXT
    assert "[data-testid=\"stSidebar\"] .stButton > button" in TEXT
    assert "color: #17365D !important" in TEXT


def test_streamlit_wires_multiturn_before_existing_answer_chain():
    assert "from src.generation.conversation import resolve_question" in TEXT
    assert 'previous_messages = list(st.session_state["chat_messages"])' in TEXT
    assert "resolve_question(question, previous_messages)" in TEXT
    assert "answer_question(resolved.standalone, service=service)" in TEXT


def test_answer_raw_text_is_kept_for_followup_context():
    assert '"context_content": answer.raw_text if answer.status == "answered" else ""' in TEXT
    assert "이전 대화 맥락을 반영해 질문을 해석했습니다." in TEXT


def test_sources_are_grouped_by_user_facing_categories():
    assert 'render_source_group("관련 법령", law_sources)' in TEXT
    assert 'render_source_group("관련 판례", case_sources)' in TEXT
    assert 'render_source_group("관련 기관 안내", guide_sources)' in TEXT
    assert '답변에 사용한 출처' in TEXT
    assert '· `{doc_type}` ·' not in TEXT
