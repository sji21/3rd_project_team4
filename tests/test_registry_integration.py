"""PATCH-005 실제 등기 PDF를 사용하는 선택적 통합 테스트."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src.document_check.service import analyze_registry_pdf


ROOT = Path(__file__).resolve().parents[1]
LOCAL_SAMPLE = ROOT / "test" / "data" / "부동산등기부등본.pdf"
APP_PATH = ROOT / "app" / "streamlit_app.py"


def sample_path() -> Path:
    configured = os.getenv("REGISTRY_SAMPLE_PDF", "").strip()
    return Path(configured).expanduser() if configured else LOCAL_SAMPLE


@pytest.mark.integration
def test_registry_pdf_end_to_end() -> None:
    path = sample_path()
    if not path.is_file():
        pytest.skip("REGISTRY_SAMPLE_PDF를 지정하면 로컬 등기 PDF 통합 테스트를 실행합니다.")

    result = analyze_registry_pdf(path.name, path.read_bytes())

    assert result.extraction.page_count > 0
    assert result.extraction.unreadable_page_count == 0
    assert result.status in {"review_required", "check_required", "no_signal"}
    assert result.extraction.elapsed_seconds > 0
    assert result.rag_queries
    assert "masked_text_preview" not in result.to_public_dict()


@pytest.mark.integration
def test_registry_pdf_upload_in_streamlit() -> None:
    path = sample_path()
    if not path.is_file():
        pytest.skip("REGISTRY_SAMPLE_PDF를 지정하면 Streamlit PDF 통합 테스트를 실행합니다.")

    app = AppTest.from_file(APP_PATH).run(timeout=20)
    app.get("file_uploader")[0].upload(path.name, path.read_bytes(), "application/pdf")
    app.checkbox[0].check()
    app.button[0].click()
    app.run(timeout=60)

    assert not app.exception
    signal_count = len(app.session_state.registry_analysis.signals)
    assert [metric.value for metric in app.metric][:2] == ["6쪽", f"{signal_count}개"]
    assert app.get("download_button")
