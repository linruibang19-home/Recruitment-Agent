from pathlib import Path

from app.core.security import is_within_directory, redact_data, redact_text
from app.db.repositories.audit_logs import _safe_screenshot_path


def test_redact_text_masks_personal_data_and_local_path() -> None:
    value = (
        "电话 13800138000，邮箱 test@example.com，身份证 110101199001011234，"
        "微信: recruiter_2026，文件 C:\\Users\\demo\\resume.pdf"
    )
    redacted = redact_text(value)
    assert "13800138000" not in redacted
    assert "test@example.com" not in redacted
    assert "110101199001011234" not in redacted
    assert "recruiter_2026" not in redacted
    assert "C:\\Users" not in redacted
    assert "[手机号]" in redacted
    assert "[邮箱]" in redacted
    assert "[身份证号]" in redacted
    assert "[微信号]" in redacted
    assert "[本地路径]" in redacted


def test_redact_data_recurses_through_collections() -> None:
    payload = {"candidate": {"phone": "13900139000"}, "items": ["a@b.com"]}
    assert redact_data(payload) == {
        "candidate": {"phone": "[手机号]"},
        "items": ["[邮箱]"],
    }


def test_is_within_directory_blocks_path_escape(tmp_path: Path) -> None:
    root = tmp_path / "resumes"
    root.mkdir()
    assert is_within_directory(root / "1" / "resume.pdf", root)
    assert not is_within_directory(tmp_path / "outside.pdf", root)


def test_audit_screenshot_path_is_relative_or_hidden() -> None:
    project_screenshot = (
        Path(__file__).resolve().parents[2] / "data" / "screenshots" / "capture.png"
    )
    assert _safe_screenshot_path(str(project_screenshot)) == "data/screenshots/capture.png"
    assert _safe_screenshot_path("C:\\private\\capture.png") == "[本地路径]"
