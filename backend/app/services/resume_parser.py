from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz

from app.services.ocr import extract_text_with_ocr


@dataclass(frozen=True)
class ParsedResumeText:
    text: str
    native_text: str
    ocr_text: str
    ocr_used: bool
    status: str
    detail: str


def parse_pdf_text(file_path: str | Path) -> ParsedResumeText:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"简历文件不存在：{path}")

    with fitz.open(path) as document:
        if document.page_count == 0:
            return ParsedResumeText("", "", "", False, "failed", "PDF 没有页面")
        native_text = "\n".join(page.get_text("text") for page in document).strip()
        if len(native_text) >= 80:
            return ParsedResumeText(
                text=native_text,
                native_text=native_text,
                ocr_text="",
                ocr_used=False,
                status="ok",
                detail="使用 PDF 原生文本",
            )

        ocr_result = extract_text_with_ocr(document)
        combined = ocr_result.text.strip() or native_text
        status = "ok" if len(combined) >= 40 else "needs_review"
        return ParsedResumeText(
            text=combined,
            native_text=native_text,
            ocr_text=ocr_result.text,
            ocr_used=bool(ocr_result.text),
            status=status,
            detail=ocr_result.detail,
        )
