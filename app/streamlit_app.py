"""전세ON 챗봇 UI.

현재 확정된 Generation/Retrieval 경계를 그대로 사용한다.
OCR·업로드 문서 세션 기억 기능은 후속 연결 대상으로 남겨 두고,
이 화면에서는 공식 법령·판례·기관 안내 기반 질의응답만 제공한다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from src.generation.chain import answer_question, get_default_service  # noqa: E402
from src.generation.conversation import resolve_question  # noqa: E402
from src.generation.models import Answer  # noqa: E402


STATUS_LABELS = {
    "answered": ("근거를 확인해 답변드렸습니다.", "✅"),
    "abstained": ("답변을 바로 제공하기 어렵습니다.", "⚠️"),
    "refused": ("이 질문은 전세ON의 답변 범위에 포함되지 않습니다.", "🚫"),
}

WELCOME_MESSAGE = (
    "안녕하세요. 전세ON입니다. "
    "전세계약과 주택임대차 관련 권리·절차·법적 근거를 질문해 주세요. "
    "답변은 검색된 법령·판례·공식 기관 안내를 근거로 제공합니다."
)


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
        .stApp {
            background: #F7F9FC;
        }
        .block-container {
            max-width: 900px;
            padding-top: 1.4rem;
            padding-bottom: 7rem;
        }
        [data-testid="stSidebar"] {
            background: #17365D;
        }
        [data-testid="stSidebar"] * {
            color: #F7FAFC;
        }
        [data-testid="stSidebar"] .sidebar-card {
            background: rgba(255,255,255,.08);
            border: 1px solid rgba(255,255,255,.12);
            border-radius: 14px;
            padding: .9rem 1rem;
            margin: .45rem 0 .8rem 0;
        }
        [data-testid="stSidebar"] .sidebar-card-title {
            font-weight: 700;
            margin-bottom: .35rem;
        }
        [data-testid="stSidebar"] .sidebar-muted {
            color: #C7D5E3 !important;
            font-size: .88rem;
            line-height: 1.55;
        }
        [data-testid="stSidebar"] .stButton > button {
            background: #F7FAFC !important;
            color: #17365D !important;
            border: 1px solid #DCE5EC !important;
            border-radius: 12px !important;
            min-height: 44px;
            font-weight: 800 !important;
        }
        [data-testid="stSidebar"] .stButton > button * {
            color: #17365D !important;
        }
        [data-testid="stSidebar"] .stButton > button:hover {
            background: #EAF3F9 !important;
            border-color: #B9D2E6 !important;
        }
        .chat-hero {
            padding: 1.2rem 1.4rem;
            border-radius: 18px;
            background: linear-gradient(125deg, #17365D 0%, #1E6AA8 100%);
            margin-bottom: 1rem;
            color: white;
        }
        .chat-hero h1 {
            color: white;
            margin: 0 0 .25rem 0;
            font-size: 1.85rem;
        }
        .chat-hero p {
            color: #EAF3F9;
            margin: 0;
            line-height: 1.55;
        }
        .status-pill {
            display: inline-block;
            border: 1px solid #D9E2EC;
            background: white;
            border-radius: 999px;
            padding: .24rem .65rem;
            margin: .35rem 0 .15rem 0;
            font-size: .82rem;
            color: #425466;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_resource(show_spinner="법령·판례 검색기를 준비하고 있습니다...")
def load_retrieval_service():
    """한 Streamlit 프로세스에서 KURE/RetrievalService를 한 번만 준비한다."""

    return get_default_service()


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
        }
    ]


def render_sidebar() -> None:
    with st.sidebar:
        st.title("전세ON")
        st.caption("근거 기반 주택임대차 챗봇")

        st.markdown(
            """
            <div class="sidebar-card">
              <div class="sidebar-card-title">현재 챗봇 범위</div>
              <div class="sidebar-muted">
                ✓ 주택임대차 법령<br>
                ✓ 판례<br>
                ✓ 공식 기관 안내<br>
                ✓ 근거 검증 후 답변<br>
                ✓ 이전 대화를 반영한 후속 질문<br>
                ✓ 범위 밖·근거 부족 질문은 답변 보류
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div class="sidebar-card">
              <div class="sidebar-card-title">이런 질문을 해보세요</div>
              <div class="sidebar-muted">
                • 전입신고와 확정일자는 왜 필요한가요?<br>
                • 임대차가 끝났는데 보증금을 못 받으면 어떻게 하나요?<br>
                • 임차권등기명령은 언제 신청할 수 있나요?
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div class="sidebar-card">
              <div class="sidebar-card-title">문서 기능</div>
              <div class="sidebar-muted">
                등기사항증명서·임대차계약서 OCR과 문서 세션 기억 기능은
                후속 연결 예정입니다.
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
            "개별 계약의 안전 여부를 확정적으로 판정하지 않으며, "
            "제공된 근거 범위 안에서 권리·절차를 안내합니다."
        )


def render_header() -> None:
    st.markdown(
        """
        <section class="chat-hero">
          <h1>🏠 전세ON</h1>
          <p>전세계약에 대해 궁금한 점을 물어보세요.<br>
          법령·판례·공식 기관 안내를 검색해 근거와 함께 답변합니다.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def answer_to_message(answer: Answer, *, used_history: bool = False) -> dict:
    return {
        "role": "assistant",
        "content": answer.text,
        "status": answer.status,
        "sources": answer.sources(),
        # 후속 질문에는 화면용 면책문구가 아니라 실제 생성 본문을 사용한다.
        "context_content": answer.raw_text if answer.status == "answered" else "",
        "used_history": used_history,
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
    if status:
        label, icon = STATUS_LABELS.get(status, (status, "ℹ️"))
        st.markdown(
            f'<span class="status-pill">{icon} {label}</span>',
            unsafe_allow_html=True,
        )

    if message.get("used_history"):
        st.caption("↪ 이전 대화 맥락을 반영해 질문을 해석했습니다.")

    render_sources(message.get("sources", []))


def render_history() -> None:
    for message in st.session_state["chat_messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant":
                render_assistant_meta(message)


def process_question(question: str) -> None:
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

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown("이전 대화와 근거를 확인하고 있습니다...")

        try:
            resolved = resolve_question(question, previous_messages)
            service = load_retrieval_service()
            # 기존 Retrieval·scope·injection·validation 경계는 그대로 사용한다.
            answer = answer_question(resolved.standalone, service=service)
        except Exception as error:
            # 내부 예외 세부정보는 사용자 화면에 노출하지 않는다.
            answer = None
            placeholder.error(
                "답변 처리 중 오류가 발생했습니다. "
                "검색 인덱스와 Ollama 실행 상태를 확인해 주세요."
            )
            st.caption(f"오류 유형: {type(error).__name__}")
        else:
            placeholder.markdown(answer.text)
            assistant_message = answer_to_message(
                answer,
                used_history=resolved.used_history,
            )
            render_assistant_meta(assistant_message)
            st.session_state["chat_messages"].append(assistant_message)


def main() -> None:
    configure_page()
    init_chat_state()
    render_sidebar()
    render_header()
    render_history()

    question = st.chat_input(
        "예: 전입신고와 확정일자를 받으면 어떤 효력이 있나요?"
    )
    if question and question.strip():
        process_question(question.strip())


if __name__ == "__main__":
    main()
