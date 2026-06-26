from app.api.routes import health


def test_ai_health_does_not_expose_api_key(monkeypatch) -> None:
    monkeypatch.setattr(health, "find_tesseract", lambda: r"C:\Tesseract\tesseract.exe")
    monkeypatch.setattr(health.settings, "llm_enabled", True)
    monkeypatch.setattr(health.settings, "deepseek_api_key", "secret-key")
    monkeypatch.setattr(health.settings, "llm_model", "deepseek-v4-flash")

    result = health.ai_health_check()

    assert result["status"] == "ok"
    assert result["ocr"]["available"] is True
    assert result["llm"]["enabled"] is True
    assert result["llm"]["configured"] is True
    assert result["llm"]["model"] == "deepseek-v4-flash"
    assert "secret-key" not in str(result)
