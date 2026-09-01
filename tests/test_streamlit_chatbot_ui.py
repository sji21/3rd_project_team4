from pathlib import Path


APP = Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"
TEXT = APP.read_text(encoding="utf-8")


def test_streamlit_ui_is_chat_first():
    assert "st.chat_message" in TEXT
    assert "st.chat_input" in TEXT


def test_streamlit_preloads_and_reuses_retrieval_service():
    assert "answer_question" in TEXT
    assert "get_default_service" in TEXT
    assert "@st.cache_resource(show_spinner=False)" in TEXT
    assert "def load_retrieval_service()" in TEXT
    assert "retrieval_service = load_retrieval_service()" in TEXT
    assert "service=retrieval_service" in TEXT
    assert "처음 한 번만 실행됩니다" in TEXT


def test_ocr_is_not_wired_yet():
    assert "analyze_registry_pdf" not in TEXT
    assert "analyze_contract_document" not in TEXT


def test_user_facing_status_messages_are_descriptive():
    assert '"answered": ("근거를 확인해 답변드렸습니다.", "✅")' in TEXT
    assert '"abstained": ("답변을 바로 제공하기 어렵습니다.", "⚠️")' in TEXT
    assert '"refused": ("이 질문은 전세ON의 답변 범위에 포함되지 않습니다.", "🚫")' in TEXT


def test_sidebar_is_compact_and_has_visible_clear_button():
    assert "답변에 사용하는 근거" in TEXT
    assert "이용 안내" in TEXT
    assert "🗑️ 대화 내용 지우기" in TEXT
    assert "[data-testid=\"stSidebar\"] .stButton > button" in TEXT
    assert "color: #17365D !important" in TEXT


def test_header_uses_project_title_and_quick_questions_are_removed():
    assert "안전한 부동산 계약을 위한" in TEXT
    assert "챗봇 서비스" in TEXT
    assert "EXAMPLE_QUESTIONS" not in TEXT
    assert "render_quick_questions" not in TEXT
    assert "이런 질문을 해보세요" not in TEXT


def test_chat_area_is_bottom_aligned_above_input():
    assert 'st.container(key="chat_area")' in TEXT
    assert ".st-key-chat_area" in TEXT
    assert "justify-content: flex-end" in TEXT
    assert "@media (max-width: 640px)" in TEXT


def test_chat_messages_and_statuses_have_distinct_styles():
    assert '[data-testid="stChatMessage"]' in TEXT
    assert "background: #DDEFFD" in TEXT
    assert "background: #FFFFFF" in TEXT
    assert "margin-left: 3.5rem" in TEXT
    assert "margin-right: 3.5rem" in TEXT
    assert ".status-answered" in TEXT
    assert ".status-abstained" in TEXT
    assert ".status-refused" in TEXT


def test_processing_state_has_live_elapsed_timer_without_internal_exception_type():
    assert "streamlit.components.v1 as components" not in TEXT
    assert "st.iframe(" in TEXT
    assert "def render_live_elapsed_timer()" in TEXT
    assert 'id="jeonse-elapsed"' in TEXT
    assert "setInterval(updateElapsed, 100)" in TEXT
    assert "timer_slot.empty()" in TEXT
    assert "오류 유형" not in TEXT


def test_streamlit_wires_multiturn_before_existing_answer_chain():
    assert "from src.generation.conversation import resolve_question" in TEXT
    assert 'previous_messages = list(st.session_state["chat_messages"])' in TEXT
    assert "resolve_question(question, previous_messages)" in TEXT
    assert "answer_question(" in TEXT
    assert "resolved.standalone" in TEXT
    assert "service=retrieval_service" in TEXT


def test_answer_raw_text_is_kept_for_followup_context():
    assert '"context_content": answer.raw_text if answer.status == "answered" else ""' in TEXT
    assert "이전 대화 맥락을 반영해 질문을 해석했습니다." in TEXT


def test_sources_are_grouped_by_user_facing_categories():
    assert 'render_source_group("관련 법령", law_sources)' in TEXT
    assert 'render_source_group("관련 판례", case_sources)' in TEXT
    assert 'render_source_group("관련 기관 안내", guide_sources)' in TEXT
    assert '답변에 사용한 출처' in TEXT
    assert '· `{doc_type}` ·' not in TEXT


def test_assistant_answer_text_has_explicit_visible_color():
    assert 'AvatarAssistant"]) p' in TEXT
    assert "color: #172B3A !important" in TEXT


def test_answer_render_does_not_expose_raw_text_as_fallback():
    assert "def visible_answer_text(answer: Answer)" in TEXT
    assert "st.markdown(visible_answer_text(answer))" in TEXT
    assert '"content": visible_answer_text(answer)' in TEXT
    assert "raw_text = (answer.raw_text" not in TEXT
    assert "검증 전 생성 원문일 수 있으므로" in TEXT


def test_answer_elapsed_time_is_shown_in_chat_meta():
    assert "import time" in TEXT
    assert "started_at = time.perf_counter()" in TEXT
    assert "elapsed_seconds = time.perf_counter() - started_at" in TEXT
    assert '"elapsed_seconds": elapsed_seconds' in TEXT
    assert '⏱ {elapsed_seconds:.1f}초' in TEXT
    assert ".answer-meta-row" in TEXT


def test_streamlit_logs_server_exception_without_showing_details():
    assert "logger = logging.getLogger(__name__)" in TEXT
    assert 'logger.exception("Streamlit 질문 처리 중 예외가 발생했습니다.")' in TEXT
    assert "오류 유형" not in TEXT


def test_live_timer_runs_during_blocking_answer_call():
    timer_pos = TEXT.index("render_live_elapsed_timer()")
    answer_pos = TEXT.index("answer = answer_question(")
    clear_pos = TEXT.index("timer_slot.empty()")
    assert timer_pos < answer_pos < clear_pos
