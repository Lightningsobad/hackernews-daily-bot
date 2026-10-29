# ⚡️ Hacker News AI & Programming Daily Telegram Digest Bot

<p align="center">
  <strong>English</strong> | <a href="README.vi.md">Tiếng Việt</a>
</p>

A lightweight, automated daily digest bot running 100% free on **GitHub Actions** ($0 server cost):
1. Curates top trending stories on **Artificial Intelligence (AI)** and **Programming** from Hacker News over the last 24 hours.
2. Extracts full article content and leverages **Google Gemini AI** to produce concise 2–3 bullet point summaries.
3. Formats and dispatches a clean, structured Telegram digest to your channel or group daily at 07:17 AM (UTC+7 / 00:17 UTC).

---

## 🚀 How to Obtain Required Secrets

### 1. `TELEGRAM_BOT_TOKEN`
1. Open Telegram and search for the official **[@BotFather](https://t.me/BotFather)**.
2. Send `/newbot`, then follow the prompts to choose a display name and username.
3. `@BotFather` will reply with your API token (e.g. `123456789:ABCdefGhIJKlmNoPQRstuVWXyz`).

### 2. `TELEGRAM_CHAT_ID`
- **Sending to a Channel or Group**:
  1. Add your newly created bot to the Channel/Group as an **Administrator** with *Post Messages* permission.
  2. Send any test message into the channel/group.
  3. Get channel ID: Add **[@userinfobot](https://t.me/userinfobot)** or **[@getmyid_bot](https://t.me/getmyid_bot)** to check the ID (typically starts with `-100...`, e.g. `-1001234567890`).
- **Sending to Personal Direct Messages**:
  1. Open a chat with your bot and click `/start`.
  2. Open a chat with **[@userinfobot](https://t.me/userinfobot)**, which will display your user ID (positive integer, e.g. `987654321`).

### 3. `GEMINI_API_KEY`
1. Go to [Google AI Studio](https://aistudio.google.com/).
2. Sign in with your Google account.
3. Click **Get API Key** -> **Create API Key in new project**.
4. Copy the generated API key (free tier with 15 requests/minute).

---

## ⚙️ GitHub Configuration (Automated Execution)

After pushing the repository to GitHub:
1. Open your repository -> Navigate to **Settings**.
2. In the left sidebar, click **Secrets and variables** -> **Actions**.
3. Click **New repository secret** and add these 3 secrets:
   - `TELEGRAM_BOT_TOKEN`: Token from BotFather.
   - `TELEGRAM_CHAT_ID`: Channel/group or user ID.
   - `GEMINI_API_KEY`: API Key from Google AI Studio.
4. *(Optional)* To switch AI models (defaults to `gemini-3.8-flash`), go to the **Variables** tab -> Click **New repository variable** -> name `GEMINI_MODEL` (e.g., `gemini-3.5-flash-lite`).

The bot triggers automatically via cron at **00:17 UTC (07:17 AM UTC+7)** daily. You can also trigger it manually anytime by navigating to the **Actions** tab -> Selecting **Daily Hacker News Digest** -> Clicking **Run workflow**.

---

## 🛡️ Model Cascade Resilience

The application features built-in self-healing and model cascade mechanisms:
- If the configured model (`GEMINI_MODEL`) is deprecated or returns HTTP 404, the bot cascades through fallbacks:
  `gemini-3.8-flash` ➡️ `gemini-3.5-flash-lite`.
- If Google AI services experience complete network failure, the bot **still delivers the digest** with story titles, upvotes, direct links, and discussion links with an informative note—ensuring your morning updates are never interrupted.

---

## 💻 Local Development & Testing

### 1. Set Up Environment
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment:
# On Windows PowerShell:
.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Local Environment Variables
Create `.env` from the provided example template:
```bash
cp .env.example .env
```
Open `.env` and fill in your credentials. *(Note: `.env` is ignored by `.gitignore` to prevent secret leaks)*.

### 3. Run Locally
- **Dry Run Mode**: Fetches real stories, generates AI summaries, and prints the formatted digest to the terminal **without sending to Telegram**:
  ```bash
  python -m src.main --dry-run
  ```
- **Live Run Mode**: Fetches stories, summarizes, and sends directly to Telegram:
  ```bash
  python -m src.main
  ```

### 4. Run Test Suite
```bash
pytest -v
```
