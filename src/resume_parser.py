"""阶段4a: PDF 简历文本抽取。

用 PyMuPDF 把 PDF 转成纯文本,交给 profiler 做 LLM 画像。
"""
from __future__ import annotations

from pathlib import Path

from config import cfg
from db import save_resume


def parse_pdf(boss_id: str, pdf_path: str) -> str | None:
    """抽取 PDF 文本并存库。失败记 status=failed 并返回 None。"""
    p = Path(pdf_path)
    if not p.exists():
        save_resume(boss_id, pdf_path, None, "failed")
        return None
    try:
        import fitz  # PyMuPDF
        text_parts = []
        with fitz.open(p) as doc:
            for page in doc:
                text_parts.append(page.get_text())
        text = "\n".join(text_parts).strip()
        if not text:
            # 扫描件无文本层,真实场景需 OCR。这里标记 failed。
            save_resume(boss_id, pdf_path, None, "failed")
            return None
        save_resume(boss_id, pdf_path, text, "ok")
        return text
    except Exception as e:
        save_resume(boss_id, pdf_path, None, "failed")
        print(f"[resume_parser] {boss_id} 解析失败: {e}")
        return None
