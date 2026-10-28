from unittest.mock import patch, MagicMock
from src.article_fetcher import fetch_article_text

def test_fetch_article_text_success():
    sample_html = "<html><body><article><h1>Tech News</h1><p>Important details about AI architecture.</p></article></body></html>"
    with patch("requests.get") as mock_get, \
         patch("src.article_fetcher.extract_text_from_html", return_value="Important details about AI architecture."):
        mock_get.return_value = MagicMock(status_code=200, text=sample_html)
        text = fetch_article_text("https://example.com/article")
    assert "Important details about AI architecture." in text

def test_fetch_article_text_handles_network_failure():
    with patch("requests.get", side_effect=Exception("Connection timed out")):
        text = fetch_article_text("https://example.com/timeout")
    assert text == ""

def test_fetch_article_text_handles_http_error():
    with patch("requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=403, text="Forbidden")
        text = fetch_article_text("https://example.com/forbidden")
    assert text == ""

def test_fetch_article_text_skips_non_html():
    with patch("requests.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            headers={"Content-Type": "application/pdf"},
            text="%PDF-1.5..."
        )
        text = fetch_article_text("https://example.com/paper.pdf")
    assert text == ""

