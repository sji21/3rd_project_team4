"""전세ON 챗봇 UI.

현재 확정된 Generation/Retrieval 경계를 그대로 사용한다.
OCR·업로드 문서 세션 기억 기능은 후속 연결 대상으로 남겨 두고,
이 화면에서는 공식 법령·판례·기관 안내 기반 질의응답만 제공한다.
"""

from __future__ import annotations

import logging
import sys
import time
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import streamlit as st
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from src.contract_check.service import analyze_contract_document  # noqa: E402
from src.document_check.service import analyze_registry_pdf  # noqa: E402
from src.document_check.session_retrieval import (  # noqa: E402
    SessionDocumentRetriever,
    build_session_document_context,
    question_references_uploaded_document,
)
from src.generation.chain import get_default_service  # noqa: E402
from src.generation.graph import answer_document_question, answer_question  # noqa: E402
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

    if "session_document_id" not in st.session_state:
        st.session_state["session_document_id"] = uuid4().hex
    if "session_documents" not in st.session_state:
        st.session_state["session_documents"] = {}


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


def _document_id(kind: str, data: bytes) -> str:
    """같은 파일을 반복 선택해도 중복 적재하지 않을 세션 내 식별자."""

    return sha256(f"{kind}:".encode("utf-8") + data).hexdigest()[:20]


def _document_label(kind: str) -> str:
    return "등기부등본" if kind == "registry" else "임대차계약서"


def _infer_document_kind(uploaded_file, question: str) -> str:
    """별도 선택창 없이 파일명·동반 질문에서 등기부 여부를 판단한다."""

    hint = f"{uploaded_file.name} {question}".replace(" ", "")
    return "registry" if any(token in hint for token in ("등기부", "등기사항")) else "contract"


def _add_uploaded_document(uploaded_file, kind: str) -> str | None:
    data = uploaded_file.getvalue()
    document_id = _document_id(kind, data)
    documents = st.session_state["session_documents"]
    if document_id in documents:
        return None

    if kind == "registry":
        if not uploaded_file.name.lower().endswith(".pdf"):
            return "등기부등본은 PDF 파일만 추가할 수 있습니다."
        analysis = analyze_registry_pdf(uploaded_file.name, data)
    else:
        analysis = analyze_contract_document(uploaded_file.name, data)

    context = build_session_document_context(
        uploaded_file.name,
        analysis.extraction,
        st.session_state["session_document_id"],
        document_id=document_id,
        document_kind=_document_label(kind),
    )
    documents[document_id] = {
        "document_id": document_id,
        "kind": kind,
        "label": _document_label(kind),
        "filename": uploaded_file.name,
        "page_count": analysis.extraction.page_count,
        "analysis": analysis,
        "context": context,
    }
    return None


def find_document_evidences(question: str):
    """현재 세션의 문서들에서 양의 BM25 점수를 가진 페이지만 모은다."""

    documents = st.session_state["session_documents"]
    if not documents:
        return ()

    normalized = question.replace(" ", "")
    selected_kind = None
    if any(token in normalized for token in ("등기부", "등기사항", "등기")):
        selected_kind = "registry"
    elif any(token in normalized for token in ("계약서", "임대차계약")):
        selected_kind = "contract"

    found = []
    for document in documents.values():
        if selected_kind and document["kind"] != selected_kind:
            continue
        found.extend(SessionDocumentRetriever(document["context"]).search(question, k=2))

    found.sort(key=lambda evidence: (-evidence.score, evidence.chunk_id))
    return tuple(found[:4])


def render_document_manager() -> None:
    """채팅으로 추가한 문서를 본문에서 확인한다."""

    documents = st.session_state["session_documents"]
    if not documents:
        return

    with st.expander(f"첨부 문서 {len(documents)}개", expanded=False):
        st.caption("첨부 문서는 현재 브라우저 세션에서만 검색에 사용됩니다.")
        for document in documents.values():
            st.caption(
                f"{document['filename']} · {document['label']} · "
                f"{document['page_count']}쪽"
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
    document_sources = (
        answer.document_sources()
        if hasattr(answer, "document_sources")
        else []
    )
    return {
        "role": "assistant",
        "content": visible_answer_text(answer),
        "status": answer.status,
        "sources": document_sources + answer.sources(),
        # 후속 질문에는 화면용 면책문구가 아니라 실제 생성 본문을 사용한다.
        "context_content": answer.raw_text if answer.status == "answered" else "",
        "used_history": used_history,
        "elapsed_seconds": elapsed_seconds,
        "document_ids": tuple(
            source["document_id"]
            for source in document_sources
            if source.get("document_id")
        ),
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

    document_sources = [
        source for source in sources
        if source.get("doc_type") == "uploaded_document"
    ]
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
        if source not in document_sources + law_sources + case_sources + guide_sources
    ]

    with st.expander(f"답변에 사용한 출처 {len(sources)}건"):
        render_source_group("업로드 문서 근거", document_sources)
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


def _store_uploaded_documents(uploaded_files, question: str) -> tuple[list[str], list[str]]:
    added_names: list[str] = []
    errors: list[str] = []
    for uploaded_file in uploaded_files:
        try:
            error = _add_uploaded_document(
                uploaded_file,
                _infer_document_kind(uploaded_file, question),
            )
        except Exception:
            logger.exception("채팅 첨부 문서 분석 중 오류가 발생했습니다.")
            error = "문서를 분석하지 못했습니다. 파일 형식과 OCR 상태를 확인해 주세요."
        if error:
            errors.append(f"{uploaded_file.name}: {error}")
        else:
            added_names.append(uploaded_file.name)
    return added_names, errors


def process_question(question: str, uploaded_files=(), retrieval_service=None) -> None:
    # 현재 질문을 넣기 전 대화만 후속 질문 해석에 사용한다.
    previous_messages = list(st.session_state["chat_messages"])
    added_names, upload_errors = _store_uploaded_documents(uploaded_files, question)
    visible_question = question or "문서를 첨부했습니다."

    st.session_state["chat_messages"].append(
        {
            "role": "user",
            "content": visible_question,
            "status": None,
            "sources": [],
            "context_content": question,
        }
    )

    with st.chat_message("user", avatar="👤"):
        st.markdown(visible_question)
        if added_names:
            st.caption("첨부: " + ", ".join(added_names))
        for error in upload_errors:
            st.warning(error)

    if not question:
        notice = (
            "문서를 현재 세션에 추가했습니다. 이어서 문서에서 확인할 내용을 질문해 주세요."
            if added_names
            else "질문이나 첨부 문서를 함께 보내 주세요."
        )
        with st.chat_message("assistant", avatar="🏠"):
            st.markdown(notice)
        st.session_state["chat_messages"].append(
            {
                "role": "assistant",
                "content": notice,
                "status": None,
                "sources": [],
                "context_content": "",
            }
        )
        return

    with st.chat_message("assistant", avatar="🏠"):
        started_at = time.perf_counter()
        timer_slot = st.empty()
        with timer_slot:
            render_live_elapsed_timer()

        try:
            resolved = resolve_question(question, previous_messages)
            # 사전 로딩한 RetrievalService 를 그대로 넘긴다. 문서 전용 질문이면
            # answer_document_question 이 공식 검색 상한을 0으로 낮춘다.
            use_uploaded_document = (
                bool(st.session_state["session_documents"])
                and question_references_uploaded_document(question)
            )
            document_evidences = (
                find_document_evidences(resolved.standalone)
                if use_uploaded_document
                else ()
            )
            if use_uploaded_document:
                answer = answer_document_question(
                    resolved.standalone,
                    document_evidences,
                    service=retrieval_service,
                )
            else:
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
    render_header()
    render_document_manager()

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

    submission = st.chat_input(
        "예: 전입신고 효력은? · 파일을 함께 첨부해 문서 내용을 질문할 수 있어요.",
        accept_file="multiple",
        file_type=("pdf", "jpg", "jpeg", "png"),
    )
    if submission:
        question = (getattr(submission, "text", submission) or "").strip()
        uploaded_files = tuple(getattr(submission, "files", ()) or ())
        if not question and not uploaded_files:
            return
        with chat_area:
            process_question(question, uploaded_files, retrieval_service)


if __name__ == "__main__":
    main()
