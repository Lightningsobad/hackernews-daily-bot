from unittest.mock import patch, MagicMock
from src.main import run_pipeline

def test_run_pipeline_dry_run_does_not_send_telegram(monkeypatch, capsys):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake_bot")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "-100")
    monkeypatch.setenv("GEMINI_API_KEY", "fake_gemini")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash")

    mock_story = MagicMock(
        object_id="1",
        title="AI Revolution",
        url="https://ai.org",
        points=200,
        comments_count=50,
        hn_url="https://news.ycombinator.com/item?id=1",
        created_at=1700000000,
    )

    with patch("src.main.fetch_top_stories", return_value=[mock_story]), \
         patch("src.main.fetch_article_text", return_value="Sample article content"), \
         patch("src.main.summarize_article", return_value=["Ý chính 1"]), \
         patch("src.main.send_telegram_digest") as mock_send:

        exit_code = run_pipeline(dry_run=True)
        assert exit_code == 0
        mock_send.assert_not_called()
        captured = capsys.readouterr()
        assert "DRY RUN MODE" in captured.out
        assert "AI Revolution" in captured.out

def test_run_pipeline_live_send_success(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake_bot")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "-100")
    monkeypatch.setenv("GEMINI_API_KEY", "fake_gemini")

    mock_story = MagicMock(
        object_id="2",
        title="Python Performance",
        url="https://python.org",
        points=300,
        comments_count=40,
        hn_url="https://news.ycombinator.com/item?id=2",
        created_at=1700000000,
    )

    with patch("src.main.fetch_top_stories", return_value=[mock_story]), \
         patch("src.main.fetch_article_text", return_value="Sample content"), \
         patch("src.main.summarize_article", return_value=["Ý chính 1"]), \
         patch("src.main.send_telegram_digest", return_value=True) as mock_send:

        exit_code = run_pipeline(dry_run=False)
        assert exit_code == 0
        mock_send.assert_called_once()

def test_run_pipeline_dry_run_without_any_credentials(monkeypatch, capsys):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("DRY_RUN", raising=False)

    mock_story = MagicMock(
        object_id="3",
        title="Offline Test",
        url="https://offline.org",
        points=100,
        comments_count=10,
        hn_url="https://news.ycombinator.com/item?id=3",
        created_at=1700000000,
    )

    with patch("src.main.fetch_top_stories", return_value=[mock_story]), \
         patch("src.main.fetch_article_text", return_value=""), \
         patch("src.main.summarize_article", return_value=["Ý 1"]), \
         patch("src.main.send_telegram_digest") as mock_send:

        exit_code = run_pipeline(dry_run=True)
        assert exit_code == 0
        mock_send.assert_not_called()
        captured = capsys.readouterr()
        assert "DRY RUN MODE" in captured.out

def test_run_pipeline_empty_stories(monkeypatch, capsys):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake_bot")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "-100")
    monkeypatch.setenv("GEMINI_API_KEY", "fake_gemini")

    with patch("src.main.fetch_top_stories", return_value=[]), \
         patch("src.main.send_telegram_digest", return_value=True) as mock_send:

        exit_code = run_pipeline(dry_run=False)
        assert exit_code == 0
        mock_send.assert_called_once()

def test_run_pipeline_dry_run_without_any_credentials(monkeypatch, capsys):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("DRY_RUN", raising=False)

    mock_story = MagicMock(
        object_id="3",
        title="Offline Test",
        url="https://offline.org",
        points=100,
        comments_count=10,
        hn_url="https://news.ycombinator.com/item?id=3",
        created_at=1700000000,
    )

    with patch("src.main.fetch_top_stories", return_value=[mock_story]), \
         patch("src.main.fetch_article_text", return_value=""), \
         patch("src.main.summarize_article", return_value=["Ý 1"]), \
         patch("src.main.send_telegram_digest") as mock_send:

        exit_code = run_pipeline(dry_run=True)
        assert exit_code == 0
        mock_send.assert_not_called()
        captured = capsys.readouterr()
        assert "DRY RUN MODE" in captured.out

