"""PDF 내장 텍스트를 우선 사용하고 필요한 페이지만 로컬 OCR로 보강한다."""

from __future__ import annotations

import io
import os
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

import pdfplumber

from .extraction_models import ExtractionResult, PageExtraction


MAX_FILE_SIZE = 20 * 1024 * 1024
MAX_PAGE_COUNT = 30
MIN_TEXT_CHARACTERS = 80


class DocumentValidationError(ValueError):
    """사용자가 수정할 수 있는 업로드 문서 오류."""


class OcrUnavailableError(RuntimeError):
    """OCR 실행 환경을 찾지 못했거나 필요한 언어가 없는 경우."""


@dataclass(frozen=True)
class PdfInspection:
    page_count: int
    embedded_texts: tuple[str, ...]


def validate_pdf(filename: str, data: bytes) -> None:
    if not filename.lower().endswith(".pdf"):
        raise DocumentValidationError("PDF 파일만 업로드할 수 있습니다.")
    if not data:
        raise DocumentValidationError("업로드한 파일이 비어 있습니다.")
    if len(data) > MAX_FILE_SIZE:
        raise DocumentValidationError("파일 크기는 20MB 이하여야 합니다.")
    if not data.lstrip().startswith(b"%PDF"):
        raise DocumentValidationError("PDF 형식을 확인할 수 없습니다.")


def inspect_pdf(data: bytes) -> PdfInspection:
    try:
        with pdfplumber.open(io.BytesIO(data)) as document:
            if not document.pages:
                raise DocumentValidationError("페이지가 없는 PDF입니다.")
            if len(document.pages) > MAX_PAGE_COUNT:
                raise DocumentValidationError(f"PDF는 {MAX_PAGE_COUNT}페이지 이하여야 합니다.")
            texts = tuple((page.extract_text() or "").strip() for page in document.pages)
            return PdfInspection(page_count=len(document.pages), embedded_texts=texts)
    except DocumentValidationError:
        raise
    except Exception as error:
        raise DocumentValidationError("암호화되었거나 손상된 PDF는 처리할 수 없습니다.") from error


def _meaningful_character_count(text: str) -> int:
    return sum(character.isalnum() for character in text)


def find_tesseract() -> str | None:
    configured = os.getenv("TESSERACT_CMD", "").strip()
    if configured:
        path = Path(configured).expanduser()
        if path.is_file():
            return str(path)

    executable = shutil.which("tesseract")
    if executable:
        return executable

    candidates = []
    for variable in ("PROGRAMFILES", "LOCALAPPDATA"):
        root = os.getenv(variable)
        if root:
            candidates.append(Path(root) / "Tesseract-OCR" / "tesseract.exe")
            candidates.append(Path(root) / "Programs" / "Tesseract-OCR" / "tesseract.exe")
    candidates.extend(
        Path(path)
        for path in (
            "/opt/homebrew/bin/tesseract",
            "/usr/local/bin/tesseract",
            "/usr/bin/tesseract",
        )
    )
    return next((str(path) for path in candidates if path.is_file()), None)


def _available_languages(executable: str) -> set[str]:
    completed = subprocess.run(
        [executable, "--list-langs"],
        capture_output=True,
        text=True,
        timeout=15,
        check=True,
    )
    return {line.strip() for line in completed.stdout.splitlines()[1:] if line.strip()}


def _ocr_language(executable: str) -> str:
    languages = _available_languages(executable)
    if "kor" not in languages:
        raise OcrUnavailableError("Tesseract 한국어 언어 데이터(kor)가 필요합니다.")
    return "kor+eng" if "eng" in languages else "kor"


def _render_page(data: bytes, page_index: int, dpi: int):
    try:
        import pypdfium2 as pdfium
    except ImportError as error:
        raise OcrUnavailableError("스캔 PDF 처리를 위해 pypdfium2가 필요합니다.") from error

    document = pdfium.PdfDocument(data)
    try:
        return document[page_index].render(scale=dpi / 72).to_pil().convert("RGB")
    finally:
        document.close()


def _ocr_page(data: bytes, page_index: int, executable: str, language: str, dpi: int) -> str:
    image = _render_page(data, page_index, dpi)
    image_bytes = io.BytesIO()
    image.save(image_bytes, format="PNG")
    completed = subprocess.run(
        [executable, "stdin", "stdout", "-l", language, "--psm", "6"],
        input=image_bytes.getvalue(),
        capture_output=True,
        timeout=120,
        check=True,
    )
    return completed.stdout.decode("utf-8", errors="replace").strip()


def extract_pdf_text(
    filename: str,
    data: bytes,
    *,
    dpi: int = 250,
    max_workers: int = 2,
) -> ExtractionResult:
    """문서 텍스트를 추출한다. 충분한 텍스트 레이어는 OCR하지 않는다."""

    started = time.perf_counter()
    validate_pdf(filename, data)
    inspection = inspect_pdf(data)
    sparse_pages = [
        index
        for index, text in enumerate(inspection.embedded_texts)
        if _meaningful_character_count(text) < MIN_TEXT_CHARACTERS
    ]
    ocr_results: dict[int, str] = {}
    warnings: list[str] = []

    if sparse_pages:
        executable = find_tesseract()
        if not executable:
            warnings.append(
                "텍스트가 부족한 페이지가 있지만 Tesseract를 찾지 못해 OCR하지 못했습니다."
            )
        else:
            try:
                language = _ocr_language(executable)
                worker_count = max(1, min(max_workers, len(sparse_pages)))
                with ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="registry-ocr") as executor:
                    futures = {
                        executor.submit(_ocr_page, data, index, executable, language, dpi): index
                        for index in sparse_pages
                    }
                    for future in as_completed(futures):
                        index = futures[future]
                        try:
                            ocr_results[index] = future.result()
                        except (OcrUnavailableError, subprocess.SubprocessError, TimeoutError) as error:
                            warnings.append(f"{index + 1}페이지 OCR 실패: {error}")
            except (OcrUnavailableError, subprocess.SubprocessError) as error:
                warnings.append(str(error))

    pages = []
    for index, embedded_text in enumerate(inspection.embedded_texts):
        ocr_text = ocr_results.get(index, "").strip()
        if ocr_text and _meaningful_character_count(ocr_text) >= _meaningful_character_count(embedded_text):
            text, method = ocr_text, "tesseract"
        elif embedded_text:
            text, method = embedded_text, "embedded_text"
        else:
            text, method = "", "unreadable"
        pages.append(
            PageExtraction(
                page_number=index + 1,
                text=text,
                method=method,
                character_count=_meaningful_character_count(text),
            )
        )

    return ExtractionResult(
        pages=tuple(pages),
        elapsed_seconds=round(time.perf_counter() - started, 3),
        warnings=tuple(warnings),
    )
