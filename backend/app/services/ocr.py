from __future__ import annotations

import os
import shutil
from dataclasses import dataclass

import fitz

from app.core.config import settings


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DEFAULT_TESSDATA_DIR = os.path.join(PROJECT_ROOT, "data", "tessdata")


@dataclass(frozen=True)
class OcrResult:
    text: str
    available: bool
    detail: str


def find_tesseract() -> str | None:
    executable = shutil.which("tesseract")
    if executable:
        return executable
    for path in (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ):
        if os.path.exists(path):
            return path
    return None


def extract_text_with_ocr(document: fitz.Document) -> OcrResult:
    executable = find_tesseract()
    if not executable:
        return OcrResult(
            text="",
            available=False,
            detail="本机未安装 Tesseract，扫描版 PDF 需要人工复核",
        )

    tessdata = settings.tessdata_dir or (
        DEFAULT_TESSDATA_DIR
        if os.path.exists(os.path.join(DEFAULT_TESSDATA_DIR, "chi_sim.traineddata"))
        else os.path.join(os.path.dirname(executable), "tessdata")
    )
    texts: list[str] = []
    try:
        for page in document:
            text_page = page.get_textpage_ocr(
                language="chi_sim+eng",
                dpi=200,
                full=True,
                tessdata=tessdata,
            )
            texts.append(page.get_text("text", textpage=text_page))
    except Exception as exc:
        return OcrResult(text="", available=True, detail=f"OCR 失败：{type(exc).__name__}: {exc}")
    return OcrResult(text="\n".join(texts).strip(), available=True, detail="OCR 完成")
