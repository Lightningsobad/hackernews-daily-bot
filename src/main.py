import argparse
import logging
import sys
from typing import List, Dict, Any

from src.config import load_config, ConfigError
from src.hn_client import fetch_top_stories
from src.article_fetcher import fetch_article_text
from src.summarizer import summarize_article
from src.telegram_sender import format_digest_message, send_telegram_digest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("hn_digest")

def run_pipeline(dry_run: bool = False) -> int:
    """
    Execute the end-to-end Hacker News AI & Programming digest pipeline.
    Returns 0 on success, 1 on failure.
    """
    logger.info("Initializing Hacker News Daily Digest pipeline...")

    # Load configuration
    try:
        config = load_config(dry_run=dry_run)
    except ConfigError as e:
        logger.error(f"Configuration error: {e}")
        return 1

    effective_dry_run = config.dry_run

    # Step 1: Fetch top stories from Hacker News
    logger.info(f"Fetching top {config.max_stories} stories from Hacker News...")
    stories = fetch_top_stories(max_stories=config.max_stories)
    logger.info(f"Retrieved {len(stories)} stories.")

    if not stories:
        logger.warning("No stories found matching target criteria.")
        empty_chunks = format_digest_message([])
        if effective_dry_run:
            print("\n=== DRY RUN MODE: NO STORIES ===")
            print(empty_chunks[0])
            return 0
        success = send_telegram_digest(config.telegram_bot_token, config.telegram_chat_id, empty_chunks)
        return 0 if success else 1

    # Step 2 & 3: Extract article text & summarize with Gemini
    stories_data: List[Dict[str, Any]] = []
    for idx, story in enumerate(stories, start=1):
        logger.info(f"[{idx}/{len(stories)}] Processing: {story.title} ({story.url})")
        article_text = fetch_article_text(story.url)
        if article_text:
            logger.info(f"  Extracted {len(article_text)} characters of article text.")
        else:
            logger.info("  Could not extract text (fallback to title summarization).")

        bullets = summarize_article(
            api_key=config.gemini_api_key,
            title=story.title,
            article_text=article_text,
            preferred_model=config.gemini_model,
        )
        logger.info(f"  Generated {len(bullets)} bullet points.")

        stories_data.append({
            "title": story.title,
            "url": story.url,
            "hn_url": story.hn_url,
            "points": story.points,
            "comments_count": story.comments_count,
            "bullets": bullets,
        })

    # Step 4: Format message chunks
    chunks = format_digest_message(stories_data)
    logger.info(f"Formatted digest into {len(chunks)} Telegram message chunk(s).")

    # Step 5: Deliver or dry-run
    if effective_dry_run:
        print("\n" + "=" * 50)
        print("⚡️ DRY RUN MODE: The following messages would be sent to Telegram:")
        print("=" * 50)
        for i, chunk in enumerate(chunks, start=1):
            print(f"\n--- Chunk {i}/{len(chunks)} ({len(chunk)} chars) ---\n")
            print(chunk)
        print("\n" + "=" * 50 + "\n")
        return 0

    logger.info(f"Sending digest to Telegram chat: {config.telegram_chat_id}...")
    success = send_telegram_digest(
        bot_token=config.telegram_bot_token,
        chat_id=config.telegram_chat_id,
        message_chunks=chunks,
    )

    if success:
        logger.info("Daily digest successfully delivered to Telegram!")
        return 0
    else:
        logger.error("Failed to deliver one or more message chunks to Telegram.")
        return 1

def main() -> int:
    parser = argparse.ArgumentParser(description="Hacker News Daily AI & Programming Telegram Bot")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run pipeline and output formatted digest to stdout without sending Telegram message",
    )
    args = parser.parse_args()
    return run_pipeline(dry_run=args.dry_run)

if __name__ == "__main__":
    sys.exit(main())

