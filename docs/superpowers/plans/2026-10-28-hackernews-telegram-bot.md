# Hacker News AI & Programming Daily Telegram Digest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a zero-maintenance Python pipeline running daily via GitHub Actions that curates top Hacker News stories on AI and programming, generates concise Vietnamese summaries via Google Gemini AI with resilient model fallbacks, and sends a formatted digest to a Telegram channel/group while keeping all secrets safe from public repository commits.

**Architecture:** A standalone scheduled Python application without persistent web servers or databases. Algolia HN API queries top stories from the past 24 hours matching AI/programming queries; `trafilatura` extracts article body text; Google Gemini (`gemini-2.5-flash` with cascade fallback to `gemini-2.0-flash`, `gemini-1.5-flash` or graceful degradation) generates 2–3 Vietnamese bullet points; Telegram Bot API posts the formatted HTML digest. GitHub Actions triggers execution daily via cron and injects repository secrets as environment variables.

**Tech Stack:** Python 3.11+ / 3.14+, `requests`, `google-genai` / `google-generativeai`, `trafilatura`, `python-dotenv`, `pytest`, GitHub Actions.

**Spec:** [docs/superpowers/specs/2026-10-28-hackernews-telegram-bot-design.md](file:///d:/Automation-app/hackernews-daily-bot/docs/superpowers/specs/2026-10-28-hackernews-telegram-bot-design.md)

## Global Constraints
- Secrets (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `GEMINI_API_KEY`) must never be hardcoded or committed to git.
- Repository must include `.gitignore` explicitly covering `.env*` and virtual environment folders.
- Missing required environment variables must fail fast with descriptive error messages.
- Digest size must be capped to top 5–7 articles per run to keep within Telegram's 4,096 character message limit.
- If article body extraction fails (due to anti-bot, paywall, or network timeout), the pipeline must gracefully fall back to summarizing based on title and metadata rather than halting.
- **AI Model Resilience**: Do not hardcode a single Gemini model. Model name must be configurable via `GEMINI_MODEL`, supported by a fallback cascade (`gemini-2.5-flash` -> `gemini-2.0-flash` -> `gemini-1.5-flash`), with ultimate fallback to non-AI metadata if all AI calls fail.

## Review Focus
1. **Accidental secret leak**: Committing `.env` file containing live credentials to GitHub. (Guarded by `.gitignore`, `.env.example` template, and tests asserting `.env` is ignored).
2. **Missing or invalid secrets**: Running in an environment where secrets are omitted or malformed. (Guarded by validation in `config.py` raising custom exceptions).
3. **AI Model Deprecation / API 404 / Quota Outage**: Configured Gemini model becomes deprecated or quota depleted. (Guarded by model cascade in `summarizer.py` and zero-crash fallback to metadata).
4. **Paywalled / anti-scraping websites**: Articles hosted behind Cloudflare, CAPTCHA, or paywalls returning HTTP 403/503 or empty HTML. (Guarded by fallback logic in `article_fetcher.py`).
5. **Message length limit**: Digest exceeding Telegram's 4,096-character limit causing API HTTP 400 Bad Request. (Guarded by chunking/splitting in `telegram_sender.py`).

---

### Task 1: Project Setup, Environment Config & Secret Safety

**Files:**
- Create: `.gitignore`
- Create: `.env.example`
- Create: `requirements.txt`
- Create: `src/__init__.py`
- Create: `src/config.py`
- Create: `tests/__init__.py`
- Create: `tests/test_config.py`

**Interfaces:**
- Consumes: Environment variables (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `GEMINI_API_KEY`, optional `GEMINI_MODEL`, optional `MAX_STORIES`, optional `DRY_RUN`).
- Produces: `Config` dataclass (`telegram_bot_token: str`, `telegram_chat_id: str`, `gemini_api_key: str`, `gemini_model: str`, `max_stories: int`, `dry_run: bool`), and function `load_config() -> Config`.

- [ ] **Step 1: Write the failing tests for configuration and secret safety**

```python
# tests/test_config.py
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
    assert config.gemini_model == "gemini-2.5-flash"  # sensible default

def test_load_config_missing_secret_raises_error(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "-100123456789")
    monkeypatch.setenv("GEMINI_API_KEY", "fake_gemini_key")

    with pytest.raises(ConfigError) as exc_info:
        load_config()
    assert "TELEGRAM_BOT_TOKEN" in str(exc_info.value)

def test_gitignore_contains_sensitive_files():
    with open(".gitignore", "r", encoding="utf-8") as f:
        content = f.read()
    assert ".env" in content
    assert "*.env" in content or ".env*" in content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`  
Expected: FAIL with `ModuleNotFoundError: No module named 'src.config'`

- [ ] **Step 3: Implement `.gitignore`, `.env.example`, `requirements.txt`, and `src/config.py`**

- Initialize git if not already initialized (`git init`).
- Create `.gitignore` containing:
  ```
  .env
  .env.*
  *.env
  .venv/
  venv/
  __pycache__/
  *.pyc
  .pytest_cache/
  ```
- Create `.env.example` containing:
  ```
  TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
  TELEGRAM_CHAT_ID=your_telegram_chat_id_here
  GEMINI_API_KEY=your_gemini_api_key_here
  GEMINI_MODEL=gemini-2.5-flash
  MAX_STORIES=5
  DRY_RUN=false
  ```
- Create `requirements.txt` containing `requests`, `google-genai`, `trafilatura`, `python-dotenv`, `pytest`.
- Implement `src/config.py` using `dotenv.load_dotenv()` and `os.getenv()`, validating that required secrets are present unless `DRY_RUN=true`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add .gitignore .env.example requirements.txt src/ tests/
git commit -m "feat: setup project structure, config loader and secret safety"
```

---

### Task 2: Hacker News Fetcher & Filtering

**Files:**
- Create: `src/hn_client.py`
- Create: `tests/test_hn_client.py`

**Interfaces:**
- Consumes: `query_keywords: list[str]`, `hours_back: int = 24`, `max_stories: int = 5`.
- Produces: `HNStory` dataclass (`object_id: str`, `title: str`, `url: str`, `points: int`, `comments_count: int`, `hn_url: str`, `created_at: int`) and function `fetch_top_stories(keywords: list[str] = None, hours_back: int = 24, max_stories: int = 5) -> list[HNStory]`.

- [ ] **Step 1: Write the failing tests for HN Algolia fetcher**

```python
# tests/test_hn_client.py
from unittest.mock import patch, MagicMock
from src.hn_client import fetch_top_stories, HNStory

def test_fetch_top_stories_filters_and_sorts():
    mock_response = {
        "hits": [
            {
                "objectID": "101",
                "title": "New Deep Learning Breakthrough",
                "url": "https://example.com/dl",
                "points": 350,
                "num_comments": 80,
                "created_at_i": 1700000000
            },
            {
                "objectID": "102",
                "title": "Python 3.14 Released",
                "url": "https://example.com/python",
                "points": 500,
                "num_comments": 120,
                "created_at_i": 1700000100
            },
            {
                "objectID": "103",
                "title": "Low Upvote AI Article",
                "url": "https://example.com/ai-low",
                "points": 10,
                "num_comments": 2,
                "created_at_i": 1700000200
            }
        ]
    }
    with patch("requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: mock_response)
        stories = fetch_top_stories(keywords=["AI", "Python"], max_stories=2)

    assert len(stories) == 2
    assert stories[0].title == "Python 3.14 Released"
    assert stories[0].points == 500
    assert stories[0].hn_url == "https://news.ycombinator.com/item?id=102"
    assert stories[1].title == "New Deep Learning Breakthrough"
    assert stories[1].points == 350
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_hn_client.py -v`  
Expected: FAIL with `ModuleNotFoundError: No module named 'src.hn_client'`

- [ ] **Step 3: Implement `fetch_top_stories` in `src/hn_client.py`**

- Use Algolia search endpoint: `https://hn.algolia.com/api/v1/search`.
- Query AI and programming keywords.
- Deduplicate by `objectID`.
- Handle cases where `url` is None (default to HN discussion link).
- Sort descending by `points` and return top `max_stories`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_hn_client.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/hn_client.py tests/test_hn_client.py
git commit -m "feat: implement Hacker News Algolia client and story filtering"
```

---

### Task 3: Article Content Extractor with Fallbacks

**Files:**
- Create: `src/article_fetcher.py`
- Create: `tests/test_article_fetcher.py`

**Interfaces:**
- Consumes: `url: str`, `timeout_seconds: int = 10`.
- Produces: `fetch_article_text(url: str, timeout_seconds: int = 10) -> str`.

- [ ] **Step 1: Write the failing tests for article extractor**

```python
# tests/test_article_fetcher.py
from unittest.mock import patch, MagicMock
from src.article_fetcher import fetch_article_text

def test_fetch_article_text_success():
    sample_html = "<html><body><article><h1>Tech News</h1><p>Important details about AI architecture.</p></article></body></html>"
    with patch("requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, text=sample_html)
        text = fetch_article_text("https://example.com/article")
    assert "Important details about AI architecture." in text

def test_fetch_article_text_handles_network_failure():
    with patch("requests.get", side_effect=Exception("Connection timed out")):
        text = fetch_article_text("https://example.com/timeout")
    assert text == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_article_fetcher.py -v`  
Expected: FAIL with `ModuleNotFoundError: No module named 'src.article_fetcher'`

- [ ] **Step 3: Implement `fetch_article_text` in `src/article_fetcher.py`**

- Use `requests.get` with standard desktop `User-Agent` headers and timeout.
- Use `trafilatura.extract(response.text)` for extracting body text.
- Fallback gracefully on any exception to empty string `""`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_article_fetcher.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/article_fetcher.py tests/test_article_fetcher.py
git commit -m "feat: implement article text extractor with resilient fallbacks"
```

---

### Task 4: Gemini AI Vietnamese Summarizer with Dynamic Model Cascade

**Files:**
- Create: `src/summarizer.py`
- Create: `tests/test_summarizer.py`

**Interfaces:**
- Consumes: `api_key: str`, `title: str`, `article_text: str`, `preferred_model: str = "gemini-2.5-flash"`.
- Produces: `summarize_article(api_key: str, title: str, article_text: str, preferred_model: str = "gemini-2.5-flash") -> list[str]` (returning 2–3 Vietnamese bullet points).
- Constants: `FALLBACK_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]`.

- [ ] **Step 1: Write failing tests for Gemini summarizer and model fallback cascade**

```python
# tests/test_summarizer.py
from unittest.mock import patch, MagicMock
from src.summarizer import summarize_article, ModelUnavailableError

def test_summarize_article_success():
    mock_text = "- Đây là bước đột phá mới về mô hình AI.\n- Cải thiện tốc độ suy luận gấp 2 lần."
    with patch("src.summarizer.call_gemini_single_model", return_value=mock_text):
        bullets = summarize_article(
            api_key="fake_key",
            title="Next Gen LLM Announced",
            article_text="Full article text...",
            preferred_model="gemini-2.5-flash"
        )
    assert len(bullets) == 2
    assert "đột phá" in bullets[0]

def test_summarize_article_cascades_to_fallback_model_on_deprecation():
    # Primary model throws ModelUnavailableError (e.g. 404 deprecated)
    call_counts = {"attempts": 0}

    def fake_call(api_key, model, prompt):
        call_counts["attempts"] += 1
        if model == "deprecated-model":
            raise ModelUnavailableError("Model deprecated")
        return "- Tóm tắt thành công từ mô hình dự phòng."

    with patch("src.summarizer.call_gemini_single_model", side_effect=fake_call):
        bullets = summarize_article(
            api_key="fake_key",
            title="Tech News",
            article_text="Content...",
            preferred_model="deprecated-model"
        )

    assert len(bullets) >= 1
    assert "dự phòng" in bullets[0]
    assert call_counts["attempts"] >= 2  # Proves cascade happened

def test_summarize_article_zero_crash_on_total_ai_failure():
    # If all models fail, return safe fallback bullet rather than crashing pipeline
    with patch("src.summarizer.call_gemini_single_model", side_effect=Exception("Total quota exhaustion")):
        bullets = summarize_article(
            api_key="fake_key",
            title="Important Python Update",
            article_text="Content...",
            preferred_model="gemini-2.5-flash"
        )
    assert len(bullets) >= 1
    assert "Important Python Update" in bullets[0] or "Tóm tắt" in bullets[0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_summarizer.py -v`  
Expected: FAIL with `ModuleNotFoundError: No module named 'src.summarizer'`

- [ ] **Step 3: Implement `summarize_article` with Model Cascade in `src/summarizer.py`**

- Define `FALLBACK_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]`.
- Construct list of models to try: `[preferred_model] + [m for m in FALLBACK_MODELS if m != preferred_model]`.
- Iterate through models: if one throws 404/not found/deprecated or rate limit, log warning and try next model.
- If all models fail, catch exception and return a clean fallback bullet: `[f"Bài viết thảo luận về: {title} (Tóm tắt AI tạm thời không khả dụng)"]`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_summarizer.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/summarizer.py tests/test_summarizer.py
git commit -m "feat: implement Gemini summarizer with dynamic model cascade and resilient fallback"
```

---

### Task 5: Telegram Formatter & Message Sender

**Files:**
- Create: `src/telegram_sender.py`
- Create: `tests/test_telegram_sender.py`

**Interfaces:**
- Consumes: `stories: list[dict]`, `bot_token: str`, `chat_id: str`.
- Produces: `format_digest_message(stories: list[dict], date_str: str = None) -> list[str]`, `send_telegram_digest(bot_token: str, chat_id: str, message_chunks: list[str]) -> bool`.

- [ ] **Step 1: Write failing tests for Telegram sender & chunker**

```python
# tests/test_telegram_sender.py
from unittest.mock import patch, MagicMock
from src.telegram_sender import format_digest_message, send_telegram_digest

def test_format_digest_message_html_structure():
    stories = [
        {
            "title": "Python 3.14 Released",
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
    assert "Hacker News AI &amp; Programming Daily Digest" in chunk or "Hacker News AI & Programming Daily Digest" in chunk
    assert '<a href="https://python.org">Python 3.14 Released</a>' in chunk
    assert "450 điểm" in chunk
    assert "Cải thiện tốc độ 30%" in chunk

def test_send_telegram_digest_success():
    with patch("requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200, json=lambda: {"ok": True})
        success = send_telegram_digest(
            bot_token="fake_token",
            chat_id="-100123",
            message_chunks=["Hello World"]
        )
    assert success is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_telegram_sender.py -v`  
Expected: FAIL with `ModuleNotFoundError: No module named 'src.telegram_sender'`

- [ ] **Step 3: Implement `format_digest_message` and `send_telegram_digest`**

- Formatter builds HTML with title, points, comments link, bullet points.
- If message length approaches 3,800 chars, split cleanly into multiple chunks.
- Send each chunk to Telegram Bot API `sendMessage`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_telegram_sender.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/telegram_sender.py tests/test_telegram_sender.py
git commit -m "feat: implement Telegram message formatter and sender"
```

---

### Task 6: Pipeline Orchestration (`main.py`) & Dry-Run CLI

**Files:**
- Create: `src/main.py`
- Create: `tests/test_main.py`

**Interfaces:**
- Consumes: CLI invocation `python -m src.main` or `python src/main.py [--dry-run]`.
- Produces: `run_pipeline(dry_run: bool = False) -> int`.

- [ ] **Step 1: Write failing tests for main pipeline**

```python
# tests/test_main.py
from unittest.mock import patch, MagicMock
from src.main import run_pipeline

def test_run_pipeline_dry_run_does_not_send_telegram(monkeypatch, capsys):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake_bot")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "-100")
    monkeypatch.setenv("GEMINI_API_KEY", "fake_gemini")

    mock_stories = [
        MagicMock(
            object_id="1",
            title="AI Revolution",
            url="https://ai.org",
            points=200,
            comments_count=50,
            hn_url="https://news.ycombinator.com/item?id=1"
        )
    ]
    with patch("src.main.fetch_top_stories", return_value=mock_stories), \
         patch("src.main.fetch_article_text", return_value="Sample content"), \
         patch("src.main.summarize_article", return_value=["Ý chính 1"]), \
         patch("src.main.send_telegram_digest") as mock_send:
        
        exit_code = run_pipeline(dry_run=True)
        assert exit_code == 0
        mock_send.assert_not_called()
        captured = capsys.readouterr()
        assert "DRY RUN MODE" in captured.out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_main.py -v`  
Expected: FAIL with `ModuleNotFoundError: No module named 'src.main'`

- [ ] **Step 3: Implement `src/main.py`**

- Connect stages: config -> HN fetch -> text extraction -> Gemini summarization (passing `config.gemini_model`) -> Telegram formatting -> send/dry-run.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_main.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/main.py tests/test_main.py
git commit -m "feat: implement main pipeline orchestrator and dry-run CLI"
```

---

### Task 7: GitHub Actions Workflow & Deployment Documentation

**Files:**
- Create: `.github/workflows/daily_digest.yml`
- Create: `README.md`

**Interfaces:**
- Consumes: GitHub Secrets (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `GEMINI_API_KEY`, optional `GEMINI_MODEL`).
- Produces: Scheduled daily run at 00:00 UTC (07:00 AM UTC+7) + manual trigger button.

- [ ] **Step 1: Write `.github/workflows/daily_digest.yml`**

Include `GEMINI_MODEL: ${{ vars.GEMINI_MODEL || 'gemini-2.5-flash' }}` alongside secrets.

- [ ] **Step 2: Write comprehensive `README.md`**

Cover secret management, how to create tokens, how to add GitHub Secrets, and how model fallback works.

- [ ] **Step 3: Run full project tests**

Run: `pytest -v`  
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/daily_digest.yml README.md
git commit -m "docs: add GitHub Actions workflow and secret configuration documentation"
```
