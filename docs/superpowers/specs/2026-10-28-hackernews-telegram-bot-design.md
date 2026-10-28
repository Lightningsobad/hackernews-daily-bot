# Hacker News AI & Programming Daily Telegram Digest - Design Document

## 1. Intent and The Why
Software developers and AI practitioners often struggle to keep up with high-signal industry news without getting distracted by endless browsing. Hacker News (HN) provides high-quality community curation, but filtering for AI and programming topics manually takes time. 
This project builds an automated, zero-maintenance pipeline that daily curates top Hacker News stories in AI and programming, summarizes them into clear Vietnamese bullet points using Google Gemini AI, and delivers a concise digest directly to a private Telegram channel/group.

## 2. Goals, Non-Goals, and Anti-Goals

### Goals
- **High-signal curation**: Automatically fetch top upvoted stories on Hacker News matching AI and Programming keywords in the last 24 hours.
- **AI-powered Vietnamese summaries**: Summarize each selected article into 2–3 crisp bullet points in Vietnamese using Google Gemini.
- **One-click links**: Provide direct links to the original article and the HN discussion thread alongside upvote counts.
- **Automated zero-cost execution**: Run fully automated on a daily schedule via GitHub Actions with 0 server/hosting cost.
- **Local runnability**: Allow manual local execution for testing and debugging via standard environment variables or a `.env` file.

### Non-Goals
- Two-way interactive bot commands (no `/start`, `/today`, polling, or webhooks).
- Supporting custom user subscriptions or database of subscribers.
- Supporting news sources other than Hacker News for now.
- Building a web UI or dashboard.

### Anti-Goals
- Complex multi-service infrastructure (no Kubernetes, Redis, Celery, or always-on VPS needed).
- Noisy spammed digests: The bot must not send dozens of messages or overwhelm the user. Limit to top 5–7 quality stories per day in a single consolidated message (or 2 if character limits require).

## 3. Constraints
- **Telegram message limit**: 4,096 characters per message. Digest must be budgeted to stay within this limit or cleanly split without breaking formatting.
- **Gemini Free Tier limits**: 15 Requests Per Minute (RPM), which easily fits 5–7 calls with a short delay or batch processing.
- **GitHub Actions Cron latency**: GitHub cron schedules may have 5–15 minutes queue variance during peak hours.
- **Content extraction safety**: Some websites have paywalls, anti-scraping, or heavy JavaScript. The system must gracefully fall back (e.g., summarize based on title/HN comments, or provide article title with a note) without crashing the pipeline.

## 4. Approaches Considered

### Approach 1: Serverless via GitHub Actions + Python + Gemini (Selected)
- **Architecture**: A lightweight Python script executed on a daily cron schedule via GitHub Actions. API keys and chat IDs are stored in GitHub Secrets.
- **Trade-offs**: Cron time has slight variance, but zero infrastructure cost, zero server maintenance, built-in run history and failure logs.
- **Decision**: Chosen by user because it satisfies all requirements with minimal complexity and zero operating cost.

### Approach 2: Self-hosted Cron / VPS
- **Architecture**: Python daemon or systemd cron on a local machine or rented VPS.
- **Trade-offs**: Strict timing down to the second, but requires an always-on machine or monthly VPS cost and maintenance.
- **Decision**: Rejected as unnecessary overhead for a daily personal digest.

## 5. System Design & How It Works

### Data Flow
1. **Trigger**: GitHub Actions cron triggers `main.py` daily (e.g., 00:00 UTC / 07:00 AM UTC+7).
2. **Fetch**: Query Hacker News Algolia Search API (`https://hn.algolia.com/api/v1/search?tags=story&numericFilters=created_at_i>TIMESTAMP`) with query keywords for AI and programming (e.g. `AI`, `LLM`, `Python`, `compiler`, `machine learning`, etc.). Filter for top points within the last 24h.
3. **Select Top 5–7**: Deduplicate, sort by points descending, pick top 5–7 stories.
4. **Scrape Article Text**: Fetch article HTML with standard headers and extract readable body text (using lightweight extractor like `trafilatura` or `beautifulsoup4`). If fetch fails or page is blocked, use available metadata (story title/HN item details) as fallback.
5. **Summarize via Gemini**: Call Google Gemini API (`gemini-2.5-flash` or `gemini-1.5-flash`) with a system instruction to produce 2–3 concise Vietnamese bullet points per story.
6. **Format & Send**: Format into clean Telegram HTML/Markdown message:
   - 📰 Title (linked to original URL)
   - ⭐️ Points & Comments count
   - 📝 2–3 Vietnamese summary points
   - 💬 Link to HN discussion
   Send to `TELEGRAM_CHAT_ID` using Telegram Bot API `sendMessage`.

### Configuration & Secrets
- `TELEGRAM_BOT_TOKEN`: Bot token from @BotFather.
- `TELEGRAM_CHAT_ID`: Target channel ID or group ID.
- `GEMINI_API_KEY`: API key from Google AI Studio.
- `MAX_STORIES`: Default 5 (configurable).

## 6. What's Left to the Builder
- Choice of article extraction library (`trafilatura` recommended for clean text extraction).
- Choice of Gemini SDK (`google-genai` or direct REST API requests to keep dependencies minimal).
- Exact prompt template for Vietnamese summarization.
- Telegram message chunking logic if text exceeds 4,000 characters.
- Unit / integration test suite with mocked network calls.

