import os
import pytest
from src.config import load_config, ConfigError

def test_load_config_success(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake_bot_token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "-100123456789")
    monkeypatch.setenv("GEMINI_API_KEY", "fake_gemini_key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash")
    monkeypatch.setenv("MAX_STORIES", "5")
    monkeypatch.setenv("DRY_RUN", "false")

    config = load_config()
    assert config.telegram_bot_token == "fake_bot_token"
    assert config.telegram_chat_id == "-100123456789"
    assert config.gemini_api_key == "fake_gemini_key"
    assert config.gemini_model == "gemini-2.5-flash"
    assert config.max_stories == 5
    assert config.dry_run is False

def test_load_config_default_model(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake_bot_token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "-100123456789")
    monkeypatch.setenv("GEMINI_API_KEY", "fake_gemini_key")
    monkeypatch.delenv("GEMINI_MODEL", raising=False)

    config = load_config()
    assert config.gemini_model == "gemini-2.5-flash"

def test_load_config_missing_secret_raises_error(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "-100123456789")
    monkeypatch.setenv("GEMINI_API_KEY", "fake_gemini_key")
    monkeypatch.setenv("DRY_RUN", "false")

    with pytest.raises(ConfigError) as exc_info:
        load_config()
    assert "TELEGRAM_BOT_TOKEN" in str(exc_info.value)

def test_gitignore_contains_sensitive_files():
    with open(".gitignore", "r", encoding="utf-8") as f:
        content = f.read()
    assert ".env" in content
    assert "*.env" in content or ".env*" in content

