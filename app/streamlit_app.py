"""전세ON 사용자 화면: 등기사항증명서 주의 신호 점검."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from src.document_check.extraction import DocumentValidationError  # noqa: E402
from src.document_check.analysis_models import DocumentAnalysis  # noqa: E402
from src.document_check.models import RiskSignal  # noqa: E402
from src.document_check.service import analyze_registry_pdf  # noqa: E402
from src.contract_check.models import ContractAnalysis, ContractFieldCheck  # noqa: E402
from src.contract_check.service import analyze_contract_document  # noqa: E402


STATUS_THEME = {
    "review_required": ("우선 확인 필요", "🔴", "#FDECEC", "#A62B2B"),
    "check_required": ("추가 확인 필요", "🟠", "#FFF4E5", "#9A5A00"),
    "no_signal": ("주요 키워드 미탐지", "🔵", "#EAF3F9", "#1E5C87"),
    "core_detected": ("핵심 항목 탐지", "🔵", "#EAF3F9", "#1E5C87"),
    "abstain": ("판독 보류", "⚪", "#F0F2F4", "#53606B"),
}
SEVERITY_LABEL = {"high": "우선 확인", "caution": "주의", "info": "참고"}
SEVERITY_ICON = {"high": "🔴", "caution": "🟠", "info": "🔵"}


def configure_page() -> None:
    st.set_page_config(
        page_title="전세ON | 계약 전 문서 점검",
        page_icon="🏠",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
        <style>
        .stApp { background: #F6F8FB; }
        .block-container { max-width: 1180px; padding-top: 2rem; padding-bottom: 4rem; }
        [data-testid="stSidebar"] { background: #17365D; }
        [data-testid="stSidebar"] * { color: #F7FAFC; }
        .hero {
            padding: 2rem 2.2rem; border-radius: 22px;
            background: linear-gradient(125deg, #17365D 0%, #1E6AA8 100%);
            color: white; margin-bottom: 1.4rem; box-shadow: 0 12px 30px rgba(23,54,93,.16);
        }
        .hero h1 { color: white; margin: 0 0 .45rem 0; font-size: 2.25rem; }
        .hero p { color: #EAF3F9; margin: 0; font-size: 1.02rem; line-height: 1.7; }
        .status-card { padding: 1.1rem 1.25rem; border-radius: 16px; margin: .6rem 0 1rem; }
        .status-card h3 { margin: 0 0 .35rem 0; }
        .status-card p { margin: 0; line-height: 1.55; }
        .eyebrow { color: #1E6AA8; font-weight: 700; letter-spacing: .04em; font-size: .82rem; }
        [data-testid="stMetric"] { background: white; border: 1px solid #DCE5EC; padding: .8rem; border-radius: 14px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> None:
    with st.sidebar:
        st.title("전세ON")
        st.caption("계약 전 근거 기반 자가 점검")
        st.divider()
        st.markdown("**현재 구현**")
        st.markdown("✓ 등기 PDF 텍스트 추출")
        st.markdown("✓ 스캔 페이지 로컬 OCR")
        st.markdown("✓ 위험 키워드 규칙 점검")
        st.markdown("✓ 계약서 핵심 항목 점검")
        st.markdown("✓ 특약 포함 여부·추천")
        st.markdown("✓ 주의사항·근거 문구 표시")
        st.divider()
        st.markdown("**후속 팀 개발**")
        st.markdown("○ LangChain 공식 근거 검색")
        st.markdown("○ LangGraph 답변·보류 라우팅")
        st.markdown("○ LLM 질의응답 챗봇")
        st.divider()
        st.caption("업로드 문서는 외부 API로 전송하지 않으며 서버 파일로 저장하지 않습니다.")


def render_header() -> None:
    st.markdown(
        """
        <section class="hero">
          <div class="eyebrow" style="color:#BFE3FA">HOUSING CONTRACT DOCUMENT CHECK</div>
          <h1>전세계약 전 문서 자가 점검</h1>
          <p>등기 PDF에서는 권리 신호를, 임대차계약서에서는 핵심 작성 항목과 특약 문구를 찾아<br>
          추가 확인사항을 안내합니다. 계약 가능 여부나 법적 효력을 자동 판정하지 않습니다.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_upload() -> None:
    st.subheader("1. 등기 PDF 첨부")
    st.caption("등기사항전부증명서 또는 등기사항요약 PDF · 최대 20MB · 최대 30페이지")
    uploaded = st.file_uploader(
        "분석할 PDF를 선택하세요",
        type=["pdf"],
        accept_multiple_files=False,
        help="텍스트 PDF는 바로 읽고, 스캔된 페이지만 로컬 Tesseract OCR을 사용합니다.",
        key="registry_pdf",
    )
    consent = st.checkbox(
        "문서에 개인정보가 포함될 수 있음을 확인했으며, 정보 제공용 자동 점검의 한계를 이해했습니다.",
        value=False,
        key="registry_consent",
    )
    analyze = st.button(
        "주의 신호 점검하기",
        type="primary",
        use_container_width=True,
        disabled=uploaded is None or not consent,
        key="registry_analyze",
    )
    if analyze and uploaded:
        try:
            with st.status("PDF를 읽고 주의 신호를 찾고 있습니다…", expanded=True) as status:
                st.write("문서 형식과 페이지를 확인합니다.")
                result = analyze_registry_pdf(uploaded.name, uploaded.getvalue())
                st.write("추출된 텍스트에서 갑구·을구 권리 키워드를 점검했습니다.")
                status.update(label="점검이 완료되었습니다.", state="complete", expanded=False)
            st.session_state["registry_analysis"] = result
        except DocumentValidationError as error:
            st.error(str(error))
        except Exception as error:
            st.error("문서 처리 중 오류가 발생했습니다. Tesseract 설치와 PDF 상태를 확인하세요.")
            st.caption(f"오류 유형: {type(error).__name__}")


def status_card(result: DocumentAnalysis | ContractAnalysis) -> None:
    label, icon, background, foreground = STATUS_THEME[result.status]
    st.markdown(
        f"""
        <div class="status-card" style="background:{background}; color:{foreground}; border:1px solid {foreground}33">
          <h3>{icon} {label} · {result.headline}</h3>
          <p>{result.summary}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_signal(signal: RiskSignal) -> None:
    with st.container(border=True):
        left, right = st.columns([4, 1])
        with left:
            st.markdown(f"#### {SEVERITY_ICON[signal.severity]} {signal.title}")
            st.caption(f"{signal.section} · {signal.page_number}페이지 · 탐지어: {signal.matched_keyword}")
        with right:
            st.markdown(f"**{SEVERITY_LABEL[signal.severity]}**")
        st.write(signal.guidance)
        with st.expander("문서에서 확인된 근거와 추가 확인사항"):
            st.markdown("**근거 문구**")
            st.code(signal.evidence, language=None)
            st.markdown("**추가로 확인하세요**")
            for check in signal.checks:
                st.markdown(f"- {check}")
            if signal.sources:
                st.markdown("**공식 참고자료**")
                for source in signal.sources:
                    st.markdown(f"- [{source.title}]({source.url})")


def render_results(result: DocumentAnalysis) -> None:
    st.divider()
    st.subheader("2. 점검 결과")
    status_card(result)

    metrics = st.columns(4)
    metrics[0].metric("문서 페이지", f"{result.extraction.page_count}쪽")
    metrics[1].metric("발견 신호", f"{len(result.signals)}개")
    metrics[2].metric("OCR 사용", f"{result.extraction.ocr_page_count}쪽")
    metrics[3].metric("처리 시간", f"{result.extraction.elapsed_seconds:.2f}초")

    if result.extraction.warnings:
        for warning in result.extraction.warnings:
            st.warning(warning)

    if result.signals:
        st.markdown("### 발견된 확인 항목")
        for signal in result.signals:
            render_signal(signal)
    else:
        st.info("현재 규칙에 등록된 주요 권리 키워드는 발견되지 않았습니다. OCR 누락이나 다른 위험이 없다는 뜻은 아닙니다.")

    st.markdown("### 등기 외에 반드시 확인할 사항")
    with st.container(border=True):
        for item in result.common_checks:
            st.markdown(f"- {item}")

    with st.expander("페이지별 추출 방식과 마스킹된 텍스트 확인"):
        for page in result.extraction.pages:
            method = {
                "embedded_text": "PDF 내장 텍스트",
                "tesseract": "Tesseract OCR",
                "unreadable": "판독 불가",
            }[page.method]
            st.caption(f"{page.page_number}페이지 · {method} · 유효 문자 {page.character_count}자")
        st.text_area(
            "마스킹된 추출 텍스트 미리보기",
            result.masked_text_preview,
            height=240,
            disabled=True,
        )

    st.warning(result.disclaimer)
    st.download_button(
        "개인정보를 제외한 점검 결과 JSON 내려받기",
        data=json.dumps(result.to_public_dict(), ensure_ascii=False, indent=2),
        file_name="registry-risk-check.json",
        mime="application/json",
        use_container_width=True,
    )


FIELD_STATUS = {
    "confirmed": ("작성값 탐지", "✅"),
    "review": ("원본 확인", "🟠"),
    "not_found": ("미탐지", "🔴"),
}
IMPORTANCE_LABEL = {"core": "핵심", "conditional": "조건부", "visual": "육안 확인"}


def render_contract_upload() -> None:
    st.subheader("1. 주택 임대차계약서 첨부")
    st.caption("전세·월세 계약서 PDF 또는 휴대폰 촬영 JPG·JPEG·PNG · 최대 20MB")
    uploaded = st.file_uploader(
        "점검할 계약서 파일을 선택하세요",
        type=["pdf", "jpg", "jpeg", "png"],
        accept_multiple_files=False,
        help="촬영본은 정면에서 글자가 선명하도록 찍어주세요. 외부 API로 보내지 않고 로컬 Tesseract OCR만 사용합니다.",
        key="contract_document",
    )
    consent = st.checkbox(
        "계약서의 개인정보 처리와 OCR 누락 가능성을 확인했으며, 자동 점검 결과를 법률 판단으로 사용하지 않습니다.",
        value=False,
        key="contract_consent",
    )
    analyze = st.button(
        "계약서 작성 항목 점검하기",
        type="primary",
        use_container_width=True,
        disabled=uploaded is None or not consent,
        key="contract_analyze",
    )
    if analyze and uploaded:
        registry_result = st.session_state.get("registry_analysis")
        registry_signal_ids = (
            tuple(signal.rule_id for signal in registry_result.signals)
            if registry_result
            else ()
        )
        try:
            with st.status("계약서를 읽고 작성 항목과 특약을 점검하고 있습니다…", expanded=True) as status:
                st.write("PDF 텍스트 또는 촬영 이미지를 확인합니다.")
                result = analyze_contract_document(
                    uploaded.name,
                    uploaded.getvalue(),
                    registry_signal_ids=registry_signal_ids,
                )
                st.write("핵심 작성값과 계약 전 검토할 특약 문구를 점검했습니다.")
                status.update(label="계약서 점검이 완료되었습니다.", state="complete", expanded=False)
            st.session_state["contract_analysis"] = result
        except DocumentValidationError as error:
            st.error(str(error))
        except Exception as error:
            st.error("계약서 처리 중 오류가 발생했습니다. Tesseract 설치와 파일 상태를 확인하세요.")
            st.caption(f"오류 유형: {type(error).__name__}")


def render_contract_field(field: ContractFieldCheck) -> None:
    label, icon = FIELD_STATUS[field.status]
    with st.container(border=True):
        left, right = st.columns([4, 1])
        with left:
            st.markdown(f"#### {icon} {field.title}")
            location = f"{field.page_number}페이지" if field.page_number else "페이지 미확인"
            st.caption(f"{IMPORTANCE_LABEL[field.importance]} 항목 · {location}")
        with right:
            st.markdown(f"**{label}**")
        st.write(field.guidance)
        if field.evidence or field.sources:
            with st.expander("탐지 근거와 공식 참고자료"):
                if field.evidence:
                    st.code(field.evidence, language=None)
                for source in field.sources:
                    st.markdown(f"- [{source.title}]({source.url})")


def render_contract_results(result: ContractAnalysis) -> None:
    st.divider()
    st.subheader("2. 계약서 점검 결과")
    status_card(result)

    confirmed = sum(field.status == "confirmed" for field in result.fields)
    not_found = sum(
        field.status == "not_found" and field.importance == "core" for field in result.fields
    )
    included = sum(clause.status == "included" for clause in result.clauses)
    metrics = st.columns(4)
    metrics[0].metric("문서 페이지", f"{result.extraction.page_count}쪽")
    metrics[1].metric("작성값 탐지", f"{confirmed}개")
    metrics[2].metric("핵심 항목 미탐지", f"{not_found}개")
    metrics[3].metric("포함 특약", f"{included}개")

    for warning in result.extraction.warnings:
        st.warning(warning)

    if result.status == "abstain":
        st.warning("주택 임대차계약서로 확인되지 않아 항목과 특약을 추측하지 않았습니다.")
    else:
        st.markdown("### 핵심 작성 항목")
        st.caption("‘미탐지’는 실제 공란 확정이 아니라 OCR에서 문구나 값을 찾지 못했다는 뜻입니다.")
        for field in result.fields:
            render_contract_field(field)

        st.markdown("### 특약 포함 여부와 협의 제안")
        st.caption("추천 문구는 자동 법률 문안이 아니며 계약 상황에 맞춰 당사자와 구체적으로 합의해야 합니다.")
        for clause in result.clauses:
            icon = "✅" if clause.status == "included" else "💡"
            label = "관련 문구 탐지" if clause.status == "included" else "검토 권장"
            with st.container(border=True):
                st.markdown(f"#### {icon} {clause.title} · {label}")
                if clause.related_registry_signal:
                    st.warning("앞서 점검한 등기 문서의 관련 위험신호와 연결되는 항목입니다.")
                st.write(clause.reason)
                st.markdown("**당사자와 협의할 내용 예시**")
                st.write(clause.recommendation)
                with st.expander("계약서 탐지 근거와 공식 참고자료"):
                    if clause.evidence:
                        st.code(clause.evidence, language=None)
                    for source in clause.sources:
                        st.markdown(f"- [{source.title}]({source.url})")

    with st.expander("페이지별 추출 방식과 마스킹된 텍스트 확인"):
        for page in result.extraction.pages:
            method = {
                "embedded_text": "PDF 내장 텍스트",
                "tesseract": "Tesseract OCR",
                "unreadable": "판독 불가",
            }[page.method]
            st.caption(f"{page.page_number}페이지 · {method} · 유효 문자 {page.character_count}자")
        st.text_area(
            "마스킹된 계약서 텍스트 미리보기",
            result.masked_text_preview,
            height=240,
            disabled=True,
        )

    st.warning(result.disclaimer)
    st.download_button(
        "개인정보를 제외한 계약서 점검 결과 JSON 내려받기",
        data=json.dumps(result.to_public_dict(), ensure_ascii=False, indent=2),
        file_name="lease-contract-check.json",
        mime="application/json",
        use_container_width=True,
    )


def render_future_integration() -> None:
    st.subheader("후속 RAG·챗봇 연결 구조")
    st.info("현재 화면의 위험 신호 결과는 LLM 없이 규칙으로 생성됩니다. 팀 개발 단계에서 아래 연결을 추가할 수 있습니다.")
    st.code(
        """등기 PDF
  → 텍스트 추출·위험 신호 규칙 (현재 구현)
  → 위험 신호별 RAG 검색 질의 생성 (현재 인터페이스 제공)
  → LangChain Retriever로 법령·정부 가이드 검색
  → LangGraph가 ANSWER / ABSTAIN / REFUSE 분기
  → LLM 답변 + 코드가 조합한 공식 출처""",
        language=None,
    )
    result = st.session_state.get("registry_analysis")
    if result:
        st.markdown("**이 문서에서 자동 생성된 후속 RAG 질의**")
        for query in result.rag_queries:
            st.markdown(f"- `{query}`")


def main() -> None:
    configure_page()
    render_sidebar()
    render_header()
    registry_tab, contract_tab, future_tab = st.tabs(
        ["등기 주의 신호 점검", "임대차계약서 점검", "RAG·챗봇 연결 안내"]
    )
    with registry_tab:
        render_upload()
        result = st.session_state.get("registry_analysis")
        if result:
            render_results(result)
    with contract_tab:
        render_contract_upload()
        contract_result = st.session_state.get("contract_analysis")
        if contract_result:
            render_contract_results(contract_result)
    with future_tab:
        render_future_integration()


if __name__ == "__main__":
    main()
