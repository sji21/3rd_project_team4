from __future__ import annotations

from src.document_check.extraction_models import ExtractionResult, PageExtraction
from src.document_check.session_retrieval import (
    SessionDocumentRetriever,
    build_session_document_context,
    question_references_uploaded_document,
)


def extraction(*pages: PageExtraction) -> ExtractionResult:
    return ExtractionResult(pages=pages, elapsed_seconds=0.1)


def test_routes_only_explicit_uploaded_document_questions_to_session_ocr():
    for question in (
        "이 계약서에서 보증금이 얼마인지 알려줘",
        "업로드한 등기부 등본 분석해줘",
        "바로 전에 올렸던 등기부 등본의 발급일은?",
        "특약사항이 있으면 알려줘",
    ):
        assert question_references_uploaded_document(question), question

    for question in (
        "전입신고 효력은?",
        "대항력은 언제부터 생기나요?",
        "보증금 반환은 언제 청구할 수 있나요?",
    ):
        assert not question_references_uploaded_document(question), question


def test_builds_one_session_chunk_per_readable_page():
    context = build_session_document_context(
        "lease-contract.pdf",
        extraction(
            PageExtraction(1, "임대차기간은 2년입니다.", "embedded_text", 12),
            PageExtraction(2, "전세대출 특약: 임대인의 협조가 필요합니다.", "tesseract", 24),
        ),
        "browser-abc",
    )

    assert context.filename == "lease-contract.pdf"
    assert context.session_id == "browser-abc"
    assert [chunk.chunk_id for chunk in context.chunks] == [
        "session:browser-abc:page:1:0",
        "session:browser-abc:page:2:0",
    ]
    assert context.chunks[1].extraction_method == "tesseract"
    assert len(context.chunks[0].checksum) == 64


def test_skips_unreadable_and_empty_pages_without_persisting_them():
    context = build_session_document_context(
        "registry.pdf",
        extraction(
            PageExtraction(1, "", "unreadable", 0),
            PageExtraction(2, "   ", "embedded_text", 0),
            PageExtraction(3, "근저당권 설정", "embedded_text", 7),
        ),
        "browser-abc",
    )

    assert [chunk.page_number for chunk in context.chunks] == [3]
    assert not context.is_empty


def test_retrieves_matching_page_with_document_specific_evidence():
    context = build_session_document_context(
        "lease-contract.pdf",
        extraction(
            PageExtraction(1, "임대차기간은 2년입니다.", "embedded_text", 12),
            PageExtraction(2, "전세대출 특약: 임대인의 협조가 필요합니다.", "tesseract", 24),
        ),
        "browser-abc",
    )

    found = SessionDocumentRetriever(context).search("전세대출 특약이 있나요?", k=1)

    assert len(found) == 1
    assert found[0].page_number == 2
    assert found[0].filename == "lease-contract.pdf"
    assert found[0].extraction_method == "tesseract"
    assert "전세대출 특약" in found[0].text


def test_retrieves_text_when_ocr_inserts_spaces_between_korean_characters():
    context = build_session_document_context(
        "registry.pdf",
        extraction(
            PageExtraction(
                1,
                "등 기 부 등 본 발 급 일 2 0 2 6 년 8 월 2 0 일",
                "tesseract",
                20,
            ),
        ),
        "browser-abc",
    )

    found = SessionDocumentRetriever(context).search("등기부등본 발급일", k=1)

    assert len(found) == 1
    assert found[0].text.startswith("등 기 부 등 본")


def test_session_ids_keep_document_chunk_ids_isolated():
    result = extraction(PageExtraction(1, "특약 문구", "embedded_text", 5))

    first = build_session_document_context("lease-contract.pdf", result, "browser-a")
    second = build_session_document_context("lease-contract.pdf", result, "browser-b")

    assert first.chunks[0].chunk_id != second.chunks[0].chunk_id
    assert first.chunks[0].checksum == second.chunks[0].checksum


def test_document_ids_keep_same_session_page_ids_isolated():
    result = extraction(PageExtraction(1, "근저당권 설정", "embedded_text", 8))

    registry = build_session_document_context(
        "registry.pdf", result, "browser-a", document_id="registry-1"
    )
    contract = build_session_document_context(
        "contract.pdf", result, "browser-a", document_id="contract-1"
    )

    assert registry.chunks[0].chunk_id != contract.chunks[0].chunk_id
    assert registry.chunks[0].document_id == "registry-1"
    assert contract.chunks[0].document_id == "contract-1"


def test_empty_context_and_blank_question_return_no_document_evidence():
    context = build_session_document_context(
        "registry.pdf",
        extraction(PageExtraction(1, "", "unreadable", 0)),
        "browser-abc",
    )
    retriever = SessionDocumentRetriever(context)

    assert context.is_empty
    assert retriever.search("근저당권") == []
    assert retriever.search("", k=3) == []


def test_rejects_missing_session_identity():
    result = extraction(PageExtraction(1, "계약서", "embedded_text", 3))

    try:
        build_session_document_context("lease-contract.pdf", result, "")
    except ValueError as error:
        assert "session_id" in str(error)
    else:
        raise AssertionError("빈 session_id는 허용하면 안 됩니다.")
