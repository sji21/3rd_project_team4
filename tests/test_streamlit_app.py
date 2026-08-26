"""PATCH-003 Streamlit 초기 화면과 업로드 검증 테스트."""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest


APP_PATH = Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"


def load_app() -> AppTest:
    app = AppTest.from_file(APP_PATH)
    return app.run(timeout=20)


def test_initial_screen_has_upload_consent_and_disabled_action() -> None:
    app = load_app()

    assert not app.exception
    assert app.get("file_uploader")
    assert app.checkbox[0].value is False
    assert app.button[0].label == "주의 신호 점검하기"
    assert app.button[0].disabled is True


def test_invalid_pdf_shows_validation_error() -> None:
    app = load_app()
    app.get("file_uploader")[0].upload("registry.pdf", b"not a pdf", "application/pdf")
    app.checkbox[0].check()
    app.button[0].click()
    app.run(timeout=20)

    assert not app.exception
    assert any("PDF 형식" in error.value for error in app.error)
