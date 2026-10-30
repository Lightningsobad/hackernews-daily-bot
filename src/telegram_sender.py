import html
import logging
import time
from enum import Enum
from datetime import datetime
from typing import List, Dict, Any, Optional
import requests

logger = logging.getLogger(__name__)

TELEGRAM_MAX_CHARS = 4096
DEFAULT_SAFE_CHUNK_LIMIT = 3800

def format_story_html(story: Dict[str, Any]) -> str:
    """Format a single story item into Telegram-compatible HTML."""
    title = html.escape(str(story.get("title", "No Title")))
    url = html.escape(str(story.get("url", "")), quote=True)
    hn_url = html.escape(str(story.get("hn_url", "")), quote=True)
    points = story.get("points", 0)
    comments_count = story.get("comments_count", 0)
    bullets = story.get("bullets", [])

    lines = [
        f'🔹 <b><a href="{url}">{title}</a></b>',
        f'⭐️ {points} điểm | 💬 <a href="{hn_url}">{comments_count} thảo luận</a>',
    ]

    for b in bullets:
        escaped_b = html.escape(str(b))
        lines.append(f'• {escaped_b}')

    return "\n".join(lines)

def format_digest_message(
    stories: List[Dict[str, Any]],
    date_str: Optional[str] = None,
    max_chunk_chars: int = DEFAULT_SAFE_CHUNK_LIMIT,
) -> List[str]:
    """
    Format a list of story items into one or more Telegram HTML message chunks.
    Ensures message sizes do not exceed Telegram's length limits.
    """
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    if not stories:
        return [
            f"⚡️ <b>Hacker News AI &amp; Programming Daily Digest</b> (<code>{date_str}</code>)\n\n"
            "Hôm nay không có bài viết nổi bật nào đạt ngưỡng hiển thị."
        ]

    header = (
        f"⚡️ <b>Hacker News AI &amp; Programming Daily Digest</b> (<code>{date_str}</code>)\n\n"
    )

    chunks = []
    current_chunk = header

    for story in stories:
        item_html = format_story_html(story) + "\n\n"
        if len(current_chunk) + len(item_html) > max_chunk_chars and current_chunk != header:
            chunks.append(current_chunk.strip())
            current_chunk = item_html
        else:
            current_chunk += item_html

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks

class DeliveryResult(Enum):
    SUCCESS = "success"
    UNREACHABLE = "unreachable"
    FAILED = "failed"


class TelegramSender:
    """One sender per broadcast keeps pacing across chunks and recipients."""

    def __init__(self, bot_token: str, timeout_seconds: int = 15, *, sleep=None, clock=None):
        self.bot_token = bot_token
        self.timeout = timeout_seconds
        self.sleep = sleep or time.sleep
        self.clock = clock or time.monotonic
        self.last_request = None
        self.not_before = 0.0

    def send(self, chat_id: str, chunks: List[str]) -> DeliveryResult:
        if not self.bot_token or not chat_id:
            return DeliveryResult.FAILED
        waited = 0.0
        retry_delay = 0.0
        for chunk in chunks:
            for attempt in range(3):
                pace = 0 if self.last_request is None else max(0, 1 - (self.clock() - self.last_request))
                delay = max(pace, retry_delay, self.not_before - self.clock())
                if waited + delay > 120:
                    return DeliveryResult.FAILED
                if delay:
                    self.sleep(delay)
                    waited += delay
                self.last_request = self.clock()
                self.not_before = 0.0
                retry_delay = 0
                try:
                    response = requests.post(
                        f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                        json={"chat_id": chat_id, "text": chunk, "parse_mode": "HTML",
                              "disable_web_page_preview": True},
                        timeout=self.timeout, allow_redirects=False,
                    )
                    try:
                        data = response.json()
                    except ValueError:
                        data = {}
                    if not isinstance(data, dict):
                        data = {}
                    if response.status_code == 200 and data.get("ok") is True:
                        break
                    description = str(data.get("description", "")).lower()
                    if response.status_code == 403 and description in (
                        "forbidden: bot was blocked by the user", "forbidden: user is deactivated",
                    ):
                        return DeliveryResult.UNREACHABLE
                    if response.status_code == 429:
                        parameters = data.get("parameters")
                        seconds = parameters.get("retry_after") if isinstance(parameters, dict) else None
                        if type(seconds) is not int or seconds < 0:
                            return DeliveryResult.FAILED
                        retry_delay = max(1, seconds)
                        self.not_before = self.clock() + retry_delay
                    elif response.status_code >= 500:
                        retry_delay = 2 ** attempt
                    else:
                        return DeliveryResult.FAILED
                except requests.RequestException:
                    # Exceptions can contain the bot URL/token: never log their text.
                    retry_delay = 2 ** attempt
                if attempt == 2:
                    return DeliveryResult.FAILED
        return DeliveryResult.SUCCESS


def send_telegram_digest(bot_token: str, chat_id: str, message_chunks: List[str],
                         timeout_seconds: int = 15) -> bool:
    """Compatibility wrapper for the fixed-recipient mode."""
    return TelegramSender(bot_token, timeout_seconds).send(chat_id, message_chunks) == DeliveryResult.SUCCESS

