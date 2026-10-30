from unittest.mock import MagicMock, patch

import pytest
import requests

from src.main import run_pipeline
from src.subscribers import Subscriber, SubscriberError
from src.telegram_sender import DeliveryResult, TelegramSender


@pytest.fixture(autouse=True)
def config(monkeypatch):
    monkeypatch.setattr("src.config.load_dotenv", lambda *a, **k: None)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake")
    monkeypatch.setenv("GEMINI_API_KEY", "fake")
    monkeypatch.setenv("SUBSCRIBER_API_URL", "https://bot.example")
    monkeypatch.setenv("SUBSCRIBER_API_TOKEN", "secret")
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.setenv("DRY_RUN", "false")


def reply(status=200, **data):
    return MagicMock(status_code=status, json=lambda: {"ok": status == 200, **data})


def test_shared_digest_ai_once_and_dedupes_fixed_chat(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    story = MagicMock(title="AI", url="https://example.com", hn_url="https://news.ycombinator.com", points=1, comments_count=1)
    with patch("src.main.SubscriberClient") as client, \
         patch("src.main.fetch_top_stories", return_value=[story]), \
         patch("src.main.fetch_article_text", return_value="article"), \
         patch("src.main.summarize_article", return_value=["summary"]) as ai, \
         patch("src.main.TelegramSender") as sender:
        client.return_value.list_active.return_value = [Subscriber("1", 1), Subscriber("2", 3)]
        sender.return_value.send.return_value = DeliveryResult.SUCCESS
        assert run_pipeline() == 0
        ai.assert_called_once()
        calls = sender.return_value.send.call_args_list
        assert [c.args[0] for c in calls] == ["1", "2"]
        assert calls[0].args[1] == calls[1].args[1]


def test_no_recipients_skips_ai_and_fetch():
    with patch("src.main.SubscriberClient") as client, patch("src.main.fetch_top_stories") as fetch:
        client.return_value.list_active.return_value = []
        assert run_pipeline() == 0
        fetch.assert_not_called()


def test_failed_subscriber_api_aborts_before_ai(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    with patch("src.main.SubscriberClient") as client, patch("src.main.fetch_top_stories") as fetch:
        client.return_value.list_active.side_effect = SubscriberError("unavailable")
        assert run_pipeline() == 1
        fetch.assert_not_called()


def test_blocked_recipient_disabled_and_other_recipient_still_sent():
    with patch("src.main.SubscriberClient") as client, \
         patch("src.main.fetch_top_stories", return_value=[]), patch("src.main.TelegramSender") as sender:
        client.return_value.list_active.return_value = [Subscriber("1", 4), Subscriber("2", 2)]
        sender.return_value.send.side_effect = [DeliveryResult.UNREACHABLE, DeliveryResult.SUCCESS]
        assert run_pipeline() == 0
        client.return_value.disable.assert_called_once_with(Subscriber("1", 4))
        assert sender.return_value.send.call_count == 2


def test_operational_error_continues_and_fails_job():
    with patch("src.main.SubscriberClient") as client, \
         patch("src.main.fetch_top_stories", return_value=[]), patch("src.main.TelegramSender") as sender:
        client.return_value.list_active.return_value = [Subscriber("1", 1), Subscriber("2", 2)]
        sender.return_value.send.side_effect = [DeliveryResult.FAILED, DeliveryResult.SUCCESS]
        assert run_pipeline() == 1
        client.return_value.disable.assert_not_called()
        assert sender.return_value.send.call_count == 2


def test_dry_run_never_reads_or_writes_subscribers():
    with patch("src.main.SubscriberClient") as client, \
         patch("src.main.fetch_top_stories", return_value=[]), patch("src.main.TelegramSender") as sender:
        assert run_pipeline(dry_run=True) == 0
        client.assert_not_called()
        sender.assert_not_called()


@pytest.mark.parametrize("failure", [requests.Timeout("fake secret"), reply(500)])
def test_sender_retries_transient_failure(failure):
    clock = MagicMock(return_value=0)
    sleep = MagicMock()
    with patch("src.telegram_sender.requests.post", side_effect=[failure, reply()]) as post:
        assert TelegramSender("token", sleep=sleep, clock=clock).send("1", ["hi"]) == DeliveryResult.SUCCESS
        assert post.call_count == 2
        assert sum(c.args[0] for c in sleep.call_args_list) >= 1


def test_sender_obeys_retry_after_and_limits_wait():
    with patch("src.telegram_sender.requests.post", side_effect=[reply(429, parameters={"retry_after": 7}), reply()]) as post:
        sleep = MagicMock()
        assert TelegramSender("token", sleep=sleep, clock=lambda: 0).send("1", ["hi"]) == DeliveryResult.SUCCESS
        assert 7 in [c.args[0] for c in sleep.call_args_list]
    with patch("src.telegram_sender.requests.post", return_value=reply(429, parameters={"retry_after": 121})) as post:
        sleep = MagicMock()
        assert TelegramSender("token", sleep=sleep, clock=lambda: 0).send("1", ["hi"]) == DeliveryResult.FAILED
        assert post.call_count == 1
        sleep.assert_not_called()


def test_sender_three_attempts_and_shared_pacing():
    sleep = MagicMock()
    with patch("src.telegram_sender.requests.post", return_value=reply(503)) as post:
        assert TelegramSender("token", sleep=sleep, clock=lambda: 0).send("1", ["hi"]) == DeliveryResult.FAILED
        assert post.call_count == 3
    with patch("src.telegram_sender.requests.post", return_value=reply()):
        sleep.reset_mock()
        sender = TelegramSender("token", sleep=sleep, clock=lambda: 0)
        sender.send("1", ["a", "b"])
        sender.send("2", ["a"])
        assert [c.args[0] for c in sleep.call_args_list] == [1, 1]


@pytest.mark.parametrize("status,description,expected", [
    (403, "Forbidden: bot was blocked by the user", "unreachable"),
    (403, "Forbidden: user is deactivated", "unreachable"),
    (403, "Forbidden: bot is not a member of the channel chat", "failed"),
    (400, "Bad Request: can't parse entities", "failed"),
])
def test_sender_only_classifies_explicit_unreachable_users(status, description, expected):
    with patch("src.telegram_sender.requests.post", return_value=reply(status, description=description)) as post:
        assert TelegramSender("token").send("1", ["hi"]).value == expected
        assert post.call_count == 1


def test_rate_limit_cooldown_applies_to_following_recipients():
    with patch("src.telegram_sender.requests.post", return_value=reply(429, parameters={"retry_after": 121})) as post:
        sender = TelegramSender("token", sleep=MagicMock(), clock=lambda: 0)
        assert sender.send("1", ["hi"]) == DeliveryResult.FAILED
        assert sender.send("2", ["hi"]) == DeliveryResult.FAILED
        # The second recipient must not bypass Telegram's global cooldown.
        assert post.call_count == 1


def test_disable_failure_is_operational_but_does_not_stop_broadcast():
    with patch("src.main.SubscriberClient") as client, \
         patch("src.main.fetch_top_stories", return_value=[]), patch("src.main.TelegramSender") as sender:
        client.return_value.list_active.return_value = [Subscriber("1", 1), Subscriber("2", 2)]
        client.return_value.disable.side_effect = SubscriberError("unavailable")
        sender.return_value.send.side_effect = [DeliveryResult.UNREACHABLE, DeliveryResult.SUCCESS]
        assert run_pipeline() == 1
        assert sender.return_value.send.call_count == 2
