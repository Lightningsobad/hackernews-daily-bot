from unittest.mock import patch, MagicMock
from src.telegram_sender import format_digest_message, send_telegram_digest

def test_format_digest_message_html_structure():
    stories = [
        {
            "title": "Python 3.14 & AI Tools <New>",
            "url": "https://python.org",
            "points": 450,
            "comments_count": 89,
            "hn_url": "https://news.ycombinator.com/item?id=101",
            "bullets": ["Cải thiện tốc độ 30%", "Bỏ GIL mặc định"]
        }
    ]
    chunks = format_digest_message(stories, date_str="2026-10-28")
    assert len(chunks) == 1
    chunk = chunks[0]
    # Check header
    assert "Hacker News AI &amp; Programming Daily Digest" in chunk
    assert "2026-10-28" in chunk
    # Check escaped title & link
    assert '<a href="https://python.org">Python 3.14 &amp; AI Tools &lt;New&gt;</a>' in chunk
    # Check stats
    assert "450 điểm" in chunk
    assert "89 thảo luận" in chunk
    # Check bullets
    assert "• Cải thiện tốc độ 30%" in chunk

def test_format_digest_message_chunking():
    # Create many stories with long content to force chunking (> 3800 chars)
    long_stories = []
    for i in range(15):
        long_stories.append({
            "title": f"Story {i} with a very detailed technical breakthrough title",
            "url": f"https://example.com/story-{i}",
            "points": 300 + i,
            "comments_count": 50 + i,
            "hn_url": f"https://news.ycombinator.com/item?id={i}",
            "bullets": [
                f"Bullet 1: Detailed analysis of system architecture and performance in component {i}." * 3,
                f"Bullet 2: Deep dive into benchmark results and implications for software engineering." * 3,
            ]
        })
    chunks = format_digest_message(long_stories, date_str="2026-10-28")
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 4000

def test_send_telegram_digest_success():
    with patch("requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200, json=lambda: {"ok": True})
        success = send_telegram_digest(
            bot_token="fake_token",
            chat_id="-100123",
            message_chunks=["Hello World"]
        )
    assert success is True

def test_send_telegram_digest_failure():
    with patch("requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=400, text="Bad Request")
        success = send_telegram_digest(
            bot_token="fake_token",
            chat_id="-100123",
            message_chunks=["Hello World"]
        )
    assert success is False
