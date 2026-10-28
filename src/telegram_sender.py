import html
import logging
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
import requests

logger = logging.getLogger(__name__)

TELEGRAM_MAX_CHARS = 4096
DEFAULT_SAFE_CHUNK_LIMIT = 3800

def format_story_html(story: Dict[str, Any]) -> str:
    """Format a single story item into Telegram-compatible HTML."""
    title = html.escape(str(story.get("title", "No Title")))
    url = story.get("url", "")
    hn_url = story.get("hn_url", "")
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

def send_telegram_digest(
    bot_token: str,
    chat_id: str,
    message_chunks: List[str],
    timeout_seconds: int = 15,
) -> bool:
    """
    Send formatted digest chunks to a Telegram chat or channel via Bot API.
    """
    if not bot_token or not chat_id:
        logger.error("Missing bot_token or chat_id.")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    all_success = True
    for idx, chunk in enumerate(message_chunks):
        payload = {
            "chat_id": chat_id,
            "text": chunk,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        try:
            resp = requests.post(url, json=payload, timeout=timeout_seconds)
            if resp.status_code == 200:
                logger.info(f"Successfully sent Telegram chunk {idx + 1}/{len(message_chunks)}")
            else:
                logger.error(
                    f"Failed to send chunk {idx + 1}: HTTP {resp.status_code} - {resp.text}"
                )
                all_success = False
        except Exception as e:
            logger.error(f"Exception sending Telegram chunk {idx + 1}: {e}")
            all_success = False

        if idx < len(message_chunks) - 1:
            time.sleep(0.5)

    return all_success
