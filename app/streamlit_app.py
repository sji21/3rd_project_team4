"""전세ON 챗봇 UI.

현재 확정된 Generation/Retrieval 경계를 그대로 사용한다.
OCR·업로드 문서 세션 기억 기능은 후속 연결 대상으로 남겨 두고,
이 화면에서는 공식 법령·판례·기관 안내 기반 질의응답만 제공한다.
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from src.generation.chain import get_default_service  # noqa: E402
from src.generation.graph import answer_question  # noqa: E402
from src.generation.conversation import resolve_question  # noqa: E402
from src.generation.models import Answer  # noqa: E402


logger = logging.getLogger(__name__)


STATUS_LABELS = {
    "answered": ("근거를 확인해 답변드렸습니다.", "✅"),
    "abstained": ("답변을 바로 제공하기 어렵습니다.", "⚠️"),
    "refused": ("이 질문은 전세ON의 답변 범위에 포함되지 않습니다.", "🚫"),
}

STATUS_CLASSES = {
    "answered": "status-answered",
    "abstained": "status-abstained",
    "refused": "status-refused",
}

WELCOME_MESSAGE = (
    "안녕하세요. 전세계약 과정에서 궁금한 권리나 절차를 질문해 주세요. "
    "확인 가능한 근거와 함께 안내해 드릴게요."
)


@st.cache_resource(show_spinner=False)
def load_retrieval_service():
    """KURE-v1 검색 서비스를 앱 시작 시 한 번 준비하고 모든 rerun에서 재사용한다."""

    return get_default_service()


def configure_page() -> None:
    st.set_page_config(
        page_title="전세ON | 전세계약 법률 챗봇",
        page_icon="🏠",
        layout="centered",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
        <style>
        :root {
            --jeonse-navy: #153556;
            --jeonse-blue: #2176B8;
            --jeonse-sky: #EAF5FD;
            --jeonse-ink: #172B3A;
            --jeonse-muted: #647587;
            --jeonse-line: #DCE5EC;
            --jeonse-surface: #FFFFFF;
        }

        .stApp {
            background:
                radial-gradient(circle at 92% 4%, rgba(80, 164, 224, .10), transparent 23rem),
                #F5F8FB;
        }

        [data-testid="stHeader"] {
            background: transparent;
        }

        #MainMenu,
        footer {
            visibility: hidden;
        }

        .block-container {
            max-width: 920px;
            padding-top: 2rem;
            padding-bottom: 7.5rem;
        }

        /* Sidebar */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #112E4C 0%, #173E65 100%);
            border-right: 0;
        }

        [data-testid="stSidebarContent"] {
            padding-top: 1.1rem;
        }

        [data-testid="stSidebar"] * {
            color: #F7FAFC;
        }

        .sidebar-brand {
            display: flex;
            align-items: center;
            gap: .75rem;
            padding: .25rem 0 1rem;
        }

        .sidebar-logo {
            display: grid;
            width: 44px;
            height: 44px;
            place-items: center;
            border-radius: 14px;
            background: linear-gradient(145deg, #4AA7E6, #2080C4);
            box-shadow: 0 8px 22px rgba(1, 18, 36, .28);
            font-size: .82rem;
            font-weight: 900;
            letter-spacing: -.02em;
        }

        .sidebar-brand-name {
            font-size: 1.25rem;
            font-weight: 850;
            letter-spacing: -.03em;
            line-height: 1.2;
        }

        .sidebar-brand-copy {
            color: #BFD2E4 !important;
            font-size: .8rem;
            margin-top: .15rem;
        }

        .sidebar-status {
            display: flex;
            align-items: center;
            gap: .5rem;
            color: #DCEAF5 !important;
            font-size: .8rem;
            border-top: 1px solid rgba(255,255,255,.10);
            border-bottom: 1px solid rgba(255,255,255,.10);
            padding: .75rem 0;
            margin-bottom: 1.15rem;
        }

        .sidebar-status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #66D7A6;
            box-shadow: 0 0 0 4px rgba(102, 215, 166, .12);
            flex: 0 0 auto;
        }

        .sidebar-section {
            background: rgba(255,255,255,.07);
            border: 1px solid rgba(255,255,255,.11);
            border-radius: 16px;
            padding: 1rem;
            margin: 0 0 .8rem;
        }

        .sidebar-section-title {
            font-size: .85rem;
            font-weight: 800;
            margin-bottom: .7rem;
        }

        .sidebar-tags {
            display: flex;
            flex-wrap: wrap;
            gap: .4rem;
        }

        .sidebar-tags span {
            display: inline-block;
            padding: .28rem .55rem;
            border-radius: 999px;
            background: rgba(255,255,255,.09);
            border: 1px solid rgba(255,255,255,.10);
            color: #DCEAF5 !important;
            font-size: .76rem;
            line-height: 1.2;
        }

        .sidebar-copy {
            color: #C6D7E5 !important;
            font-size: .8rem;
            line-height: 1.58;
        }

        [data-testid="stSidebar"] .stButton > button {
            background: rgba(255,255,255,.96) !important;
            color: #17365D !important;
            border: 0 !important;
            border-radius: 12px !important;
            min-height: 44px;
            font-weight: 800 !important;
            box-shadow: 0 5px 16px rgba(3, 22, 42, .16);
        }

        [data-testid="stSidebar"] .stButton > button * {
            color: #17365D !important;
        }

        [data-testid="stSidebar"] .stButton > button:hover {
            background: #EAF5FD !important;
            transform: translateY(-1px);
        }

        [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
            margin-top: .85rem;
        }

        [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
            color: #AFC5D7 !important;
            font-size: .74rem;
            line-height: 1.5;
        }

        /* Header */
        .chat-hero {
            position: relative;
            overflow: hidden;
            padding: 1.65rem 1.75rem 1.55rem;
            border: 1px solid #D7E7F3;
            border-radius: 22px;
            background:
                linear-gradient(120deg, rgba(255,255,255,.98) 0%, rgba(238,248,255,.98) 100%);
            box-shadow: 0 14px 34px rgba(31, 76, 110, .08);
            margin-bottom: 1.15rem;
        }

        .chat-hero::after {
            content: "";
            position: absolute;
            width: 190px;
            height: 190px;
            border-radius: 50%;
            right: -65px;
            top: -90px;
            background: rgba(45, 139, 202, .10);
        }

        .hero-kicker {
            display: inline-flex;
            align-items: center;
            gap: .45rem;
            border: 1px solid #CDE4F4;
            background: rgba(255,255,255,.78);
            border-radius: 999px;
            padding: .3rem .62rem;
            color: #276C9C;
            font-size: .75rem;
            font-weight: 750;
            margin-bottom: .75rem;
        }

        .chat-hero h1 {
            position: relative;
            z-index: 1;
            color: var(--jeonse-ink);
            margin: 0 0 .45rem;
            font-size: 2rem;
            line-height: 1.25;
            letter-spacing: -.045em;
        }

        .chat-hero h1 span {
            color: var(--jeonse-blue);
        }

        .chat-hero p {
            position: relative;
            z-index: 1;
            color: #586C7E;
            margin: 0;
            line-height: 1.6;
            font-size: .93rem;
        }

        .hero-meta {
            position: relative;
            z-index: 1;
            display: flex;
            flex-wrap: wrap;
            gap: .45rem;
            margin-top: 1rem;
        }

        .hero-meta span {
            border-radius: 8px;
            background: rgba(255,255,255,.82);
            border: 1px solid #DCE9F2;
            color: #466274;
            padding: .3rem .55rem;
            font-size: .75rem;
            font-weight: 650;
        }

        /* Chat */
        [data-testid="stChatMessage"] {
            background: rgba(255,255,255,.92);
            border: 1px solid var(--jeonse-line);
            border-radius: 18px;
            padding: 1rem 1.05rem;
            margin-bottom: .7rem;
            box-shadow: 0 5px 18px rgba(34, 67, 90, .045);
        }

        [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
            background: #DDEFFD;
            border-color: #9FCDEB;
            color: #123D5A;
            margin-left: 3.5rem;
            box-shadow: 0 7px 20px rgba(33, 118, 184, .08);
        }

        [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
            background: #FFFFFF;
            border-color: #D8E2EA;
            margin-right: 3.5rem;
        }

        [data-testid="stChatMessage"] p {
            line-height: 1.7;
        }

        [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) p,
        [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) li,
        [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) strong {
            color: #172B3A !important;
        }

        [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) p,
        [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) li,
        [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) strong {
            color: #123D5A !important;
        }

        [data-testid="stChatMessageAvatarAssistant"] {
            background: #DDEFFA;
        }

        [data-testid="stChatMessageAvatarUser"] {
            background: #C7E3F7;
        }

        .st-key-chat_area {
            min-height: calc(100vh - 370px);
            display: flex;
            flex-direction: column;
            justify-content: flex-end;
            padding: .5rem 0 1rem;
        }

        [data-testid="stChatInput"] {
            border: 1px solid #BFD2E1;
            border-radius: 16px;
            background: #FFFFFF;
            box-shadow: 0 8px 28px rgba(21, 53, 86, .12);
        }

        [data-testid="stChatInput"]:focus-within {
            border-color: #4B9CD3;
            box-shadow: 0 0 0 3px rgba(33, 118, 184, .11),
                        0 8px 28px rgba(21, 53, 86, .12);
        }

        .answer-meta-row {
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: .45rem;
            margin: .4rem 0 .15rem;
        }

        .status-pill {
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            padding: .28rem .62rem;
            margin: 0;
            font-size: .75rem;
            font-weight: 700;
        }

        .elapsed-time {
            display: inline-flex;
            align-items: center;
            color: #647587;
            font-size: .75rem;
            font-weight: 650;
        }

        .status-answered {
            border: 1px solid #BFE6D3;
            background: #EFFAF5;
            color: #24754F;
        }

        .status-abstained {
            border: 1px solid #F0D89B;
            background: #FFF9E8;
            color: #8A6512;
        }

        .status-refused {
            border: 1px solid #E8C5C5;
            background: #FFF3F3;
            color: #9A4444;
        }

        [data-testid="stExpander"] {
            border: 1px solid #DCE5EC;
            border-radius: 13px;
            background: #FAFCFE;
            margin-top: .6rem;
        }

        @media (max-width: 640px) {
            .block-container {
                padding: 1rem .85rem 7rem;
            }

            .chat-hero {
                padding: 1.25rem 1.15rem;
                border-radius: 18px;
            }

            .chat-hero h1 {
                font-size: 1.6rem;
            }

            .chat-hero p br {
                display: none;
            }

            .hero-meta {
                gap: .35rem;
            }

            [data-testid="stChatMessage"] {
                padding: .85rem .8rem;
            }

            [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
                margin-left: .75rem;
            }

            [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
                margin-right: .75rem;
            }

            .st-key-chat_area {
                min-height: calc(100vh - 330px);
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_chat_state() -> None:
    if "chat_messages" not in st.session_state:
        st.session_state["chat_messages"] = [
            {
                "role": "assistant",
                "content": WELCOME_MESSAGE,
                "status": None,
                "sources": [],
                "context_content": "",
            }
        ]


def clear_chat() -> None:
    st.session_state["chat_messages"] = [
        {
            "role": "assistant",
            "content": WELCOME_MESSAGE,
            "status": None,
            "sources": [],
            "context_content": "",
        }
    ]


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-brand">
              <div class="sidebar-logo">ON</div>
              <div>
                <div class="sidebar-brand-name">전세ON</div>
                <div class="sidebar-brand-copy">근거 기반 주택임대차 챗봇</div>
              </div>
            </div>
            <div class="sidebar-status">
              <span class="sidebar-status-dot"></span>
              법령·판례·기관 안내 검색 준비됨
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div class="sidebar-section">
              <div class="sidebar-section-title">답변에 사용하는 근거</div>
              <div class="sidebar-tags">
                <span>주택임대차 법령</span>
                <span>관련 판례</span>
                <span>공식 기관 안내</span>
                <span>근거 검증</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div class="sidebar-section">
              <div class="sidebar-section-title">이용 안내</div>
              <div class="sidebar-copy">
                이전 대화의 맥락을 반영해 후속 질문을 이해합니다.
                근거가 부족하거나 답변 범위를 벗어나면 답변을 보류합니다.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.button(
            "🗑️ 대화 내용 지우기",
            use_container_width=True,
            on_click=clear_chat,
        )

        st.caption(
            "개별 계약의 안전 여부를 확정하거나 법률 자문을 대신하지 않습니다. "
            "중요한 결정 전에는 전문가 또는 관계 기관에 다시 확인해 주세요."
        )


def render_header() -> None:
    st.markdown(
        """
        <section class="chat-hero">
          <div class="hero-kicker">전세ON</div>
          <h1>안전한 부동산 계약을 위한 <span>챗봇 서비스</span></h1>
          <p>전세계약과 주택임대차에 관한 질문을 입력하면 관련 법령·판례·공식 기관 안내를 찾아<br>
          확인 가능한 근거와 함께 이해하기 쉽게 정리해 드립니다.</p>
          <div class="hero-meta">
            <span>출처와 함께 답변</span>
            <span>후속 질문 맥락 반영</span>
            <span>근거 부족 시 답변 보류</span>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def visible_answer_text(answer: Answer) -> str:
    """검증을 거친 사용자용 답변만 화면에 표시한다."""

    text = (answer.text or "").strip()
    if text:
        return text

    # raw_text는 검증 전 생성 원문일 수 있으므로 사용자 화면의 fallback으로 쓰지 않는다.
    return "답변 본문을 표시하지 못했습니다. 다시 질문해 주세요."


def answer_to_message(
    answer: Answer,
    *,
    used_history: bool = False,
    elapsed_seconds: float | None = None,
) -> dict:
    return {
        "role": "assistant",
        "content": visible_answer_text(answer),
        "status": answer.status,
        "sources": answer.sources(),
        # 후속 질문에는 화면용 면책문구가 아니라 실제 생성 본문을 사용한다.
        "context_content": answer.raw_text if answer.status == "answered" else "",
        "used_history": used_history,
        "elapsed_seconds": elapsed_seconds,
    }


def render_source_group(title: str, sources: list[dict]) -> None:
    if not sources:
        return

    st.markdown(f"**{title}**")
    for source in sources:
        label = source.get("label") or source.get("chunk_id") or "출처"
        url = source.get("url")

        if url:
            st.markdown(f"- [{label}]({url})")
        else:
            st.markdown(f"- {label}")


def render_sources(sources: list[dict]) -> None:
    if not sources:
        return

    law_sources = [
        source for source in sources
        if source.get("doc_type") in {"law", "decree", "rule"}
    ]
    case_sources = [
        source for source in sources
        if source.get("doc_type") == "case"
    ]
    guide_sources = [
        source for source in sources
        if source.get("doc_type") == "guide"
    ]
    other_sources = [
        source for source in sources
        if source not in law_sources + case_sources + guide_sources
    ]

    with st.expander(f"답변에 사용한 출처 {len(sources)}건"):
        render_source_group("관련 법령", law_sources)
        render_source_group("관련 판례", case_sources)
        render_source_group("관련 기관 안내", guide_sources)
        render_source_group("기타 출처", other_sources)


def render_assistant_meta(message: dict) -> None:
    status = message.get("status")
    elapsed_seconds = message.get("elapsed_seconds")

    meta_parts = []
    if status:
        label, icon = STATUS_LABELS.get(status, (status, "ℹ️"))
        status_class = STATUS_CLASSES.get(status, "")
        meta_parts.append(
            f'<span class="status-pill {status_class}">{icon} {label}</span>'
        )

    if isinstance(elapsed_seconds, (int, float)):
        meta_parts.append(
            f'<span class="elapsed-time">⏱ {elapsed_seconds:.1f}초</span>'
        )

    if meta_parts:
        st.markdown(
            '<div class="answer-meta-row">' + "".join(meta_parts) + "</div>",
            unsafe_allow_html=True,
        )

    if message.get("used_history"):
        st.caption("↪ 이전 대화 맥락을 반영해 질문을 해석했습니다.")

    render_sources(message.get("sources", []))


def render_history() -> None:
    for message in st.session_state["chat_messages"]:
        avatar = "🏠" if message["role"] == "assistant" else "👤"
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])
            if message["role"] == "assistant":
                render_assistant_meta(message)


def render_live_elapsed_timer() -> None:
    """질문 처리 중 브라우저에서 경과 시간을 계속 갱신한다.

    answer_question()은 서버 쪽에서 동기적으로 실행되므로 그동안 Streamlit rerun은
    일어나지 않는다. 대신 iframe 안의 JavaScript가 0.1초마다 독립적으로 시간을
    갱신해 사용자가 처리 진행 시간을 계속 볼 수 있게 한다.
    """

    st.iframe(
        """
        <style>
          html, body { margin: 0; overflow: hidden; }
        </style>
        <div style="
            display:flex;
            align-items:center;
            gap:8px;
            font-family:Arial, sans-serif;
            font-size:14px;
            color:#647587;
            padding:2px 0 8px 2px;
        ">
          <span>이전 대화와 관련 근거를 확인하고 있어요...</span>
          <strong id="jeonse-elapsed" style="color:#2176B8;">⏱ 0.0초</strong>
        </div>
        <script>
          const startedAt = performance.now();
          const timer = document.getElementById("jeonse-elapsed");

          function updateElapsed() {
            const seconds = (performance.now() - startedAt) / 1000;
            timer.textContent = `⏱ ${seconds.toFixed(1)}초`;
          }

          updateElapsed();
          setInterval(updateElapsed, 100);
        </script>
        """,
        height=42,
    )


def process_question(question: str, retrieval_service) -> None:
    # 현재 질문을 넣기 전 대화만 후속 질문 해석에 사용한다.
    previous_messages = list(st.session_state["chat_messages"])

    st.session_state["chat_messages"].append(
        {
            "role": "user",
            "content": question,
            "status": None,
            "sources": [],
            "context_content": question,
        }
    )

    with st.chat_message("user", avatar="👤"):
        st.markdown(question)

    with st.chat_message("assistant", avatar="🏠"):
        started_at = time.perf_counter()
        timer_slot = st.empty()
        with timer_slot:
            render_live_elapsed_timer()

        try:
            resolved = resolve_question(question, previous_messages)
            answer = answer_question(
                resolved.standalone,
                service=retrieval_service,
            )
        except Exception:
            # 사용자 화면에는 내부 예외를 숨기되 서버 터미널에는 traceback을 남긴다.
            logger.exception("Streamlit 질문 처리 중 예외가 발생했습니다.")
            answer = None
        finally:
            elapsed_seconds = time.perf_counter() - started_at
            timer_slot.empty()

        if answer is None:
            st.error(
                "답변을 불러오지 못했습니다. "
                "검색 인덱스와 Ollama 상태를 확인한 뒤 다시 시도해 주세요."
            )
        else:
            st.markdown(visible_answer_text(answer))
            assistant_message = answer_to_message(
                answer,
                used_history=resolved.used_history,
                elapsed_seconds=elapsed_seconds,
            )
            render_assistant_meta(assistant_message)
            st.session_state["chat_messages"].append(assistant_message)


def main() -> None:
    configure_page()
    init_chat_state()
    render_sidebar()
    render_header()

    try:
        with st.spinner("검색 모델을 준비하고 있습니다. 처음 한 번만 실행됩니다..."):
            retrieval_service = load_retrieval_service()
    except Exception:
        logger.exception("Streamlit 검색 모델 초기화 중 예외가 발생했습니다.")
        st.error(
            "검색 모델을 준비하지 못했습니다. "
            "검색 인덱스와 로컬 환경을 확인한 뒤 앱을 다시 실행해 주세요."
        )
        return

    chat_area = st.container(key="chat_area")
    with chat_area:
        render_history()

    question = st.chat_input(
        "예: 전입신고와 확정일자를 받으면 어떤 효력이 있나요?"
    )
    if question and question.strip():
        with chat_area:
            process_question(question.strip(), retrieval_service)


if __name__ == "__main__":
    main()
