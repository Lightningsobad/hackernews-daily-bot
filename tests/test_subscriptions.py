from unittest.mock import MagicMock, patch

import pytest
import requests

from src.config import ConfigError, load_config
from src.subscribers import Subscriber, SubscriberClient, SubscriberError


@pytest.fixture(autouse=True)
def clean_config(monkeypatch):
    monkeypatch.setattr("src.config.load_dotenv", lambda *a, **k: None)
    for key in ("SUBSCRIBER_API_URL", "SUBSCRIBER_API_TOKEN", "TELEGRAM_CHAT_ID"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake")
    monkeypatch.setenv("GEMINI_API_KEY", "fake")
    monkeypatch.setenv("DRY_RUN", "false")


def test_config_allows_subscribers_without_fixed_chat(monkeypatch):
    monkeypatch.setenv("SUBSCRIBER_API_URL", "https://bot.example")
    monkeypatch.setenv("SUBSCRIBER_API_TOKEN", "secret")
    assert load_config().subscriber_api_url == "https://bot.example"


@pytest.mark.parametrize("key", ["SUBSCRIBER_API_URL", "SUBSCRIBER_API_TOKEN"])
def test_partial_subscriber_config_rejected_even_with_fixed_chat(monkeypatch, key):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    monkeypatch.setenv(key, "https://bot.example" if key.endswith("URL") else "secret")
    with pytest.raises(ConfigError):
        load_config()


def response(data, status=200):
    return MagicMock(status_code=status, json=lambda: data)


def test_client_reads_all_pages_and_passes_auth():
    with patch("src.subscribers.requests.get", side_effect=[
        response({"subscribers": [{"chat_id": "1", "version": 2}], "next_cursor": "1"}),
        response({"subscribers": [{"chat_id": "2", "version": 1}], "next_cursor": None}),
    ]) as get:
        assert SubscriberClient("https://bot.example", "secret").list_active() == [
            Subscriber("1", 2), Subscriber("2", 1)]
        assert get.call_args.kwargs["params"] == {"cursor": "1"}
        assert get.call_args.kwargs["headers"]["Authorization"] == "Bearer secret"
        assert get.call_args.kwargs["allow_redirects"] is False


@pytest.mark.parametrize("data", [None, {}, {"subscribers": [{"chat_id": "1"}], "next_cursor": None}])
def test_client_rejects_invalid_response(data):
    with patch("src.subscribers.requests.get", return_value=response(data)):
        with pytest.raises(SubscriberError):
            SubscriberClient("https://bot.example", "secret").list_active()


def test_client_network_error_does_not_expose_token():
    with patch("src.subscribers.requests.get", side_effect=requests.ConnectionError("secret")):
        with pytest.raises(SubscriberError) as error:
            SubscriberClient("https://bot.example", "secret").list_active()
        assert "secret" not in str(error.value)


def test_disable_uses_expected_version():
    with patch("src.subscribers.requests.post", return_value=response({"disabled": False})) as post:
        SubscriberClient("https://bot.example", "secret").disable(Subscriber("1", 5))
        assert post.call_args.kwargs["json"] == {"chat_id": "1", "version": 5}


@pytest.mark.parametrize("url", ["http://example.com", "https://[broken", "https://name:secret@example.com", "https://example.com?token=secret"])
def test_invalid_api_url_is_a_safe_config_error(monkeypatch, url):
    monkeypatch.setenv("SUBSCRIBER_API_URL", url)
    monkeypatch.setenv("SUBSCRIBER_API_TOKEN", "secret")
    with pytest.raises(ConfigError) as error:
        load_config()
    assert "secret" not in str(error.value)


def test_repeated_pagination_cursor_is_rejected():
    with patch("src.subscribers.requests.get", return_value=response({"subscribers": [], "next_cursor": "1"})):
        with pytest.raises(SubscriberError):
            SubscriberClient("https://bot.example", "secret").list_active()


def test_http_auth_failure_rejected():
    with patch("src.subscribers.requests.get", return_value=response({}, 401)):
        with pytest.raises(SubscriberError):
            SubscriberClient("https://bot.example", "secret").list_active()
