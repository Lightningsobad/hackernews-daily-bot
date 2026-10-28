import os
from dataclasses import dataclass
from dotenv import load_dotenv

class ConfigError(Exception):
    """Raised when configuration validation fails."""
    pass

@dataclass(frozen=True)
class Config:
    telegram_bot_token: str
    telegram_chat_id: str
    gemini_api_key: str
    gemini_model: str = "gemini-3.8-flash"
    max_stories: int = 5
    dry_run: bool = False

def load_config(env_file: str | None = None, dry_run: bool | None = None) -> Config:
    """
    Load and validate application configuration from environment variables.
    Optionally reads from a .env file if present.
    """
    if env_file:
        load_dotenv(env_file)
    else:
        load_dotenv()

    if dry_run is None:
        dry_run_raw = os.getenv("DRY_RUN", "false").strip().lower()
        effective_dry_run = dry_run_raw in ("true", "1", "yes")
    else:
        effective_dry_run = bool(dry_run)

    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
    gemini_model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip() or "gemini-3.8-flash"

    try:
        max_stories = int(os.getenv("MAX_STORIES", "5").strip())
    except ValueError:
        max_stories = 5

    # If dry_run is False, all secrets must be provided
    if not effective_dry_run:
        missing = []
        if not telegram_bot_token:
            missing.append("TELEGRAM_BOT_TOKEN")
        if not telegram_chat_id:
            missing.append("TELEGRAM_CHAT_ID")
        if not gemini_api_key:
            missing.append("GEMINI_API_KEY")

        if missing:
            raise ConfigError(
                f"Missing required environment variable(s): {', '.join(missing)}. "
                "Ensure they are set in your environment or .env file."
            )

    return Config(
        telegram_bot_token=telegram_bot_token,
        telegram_chat_id=telegram_chat_id,
        gemini_api_key=gemini_api_key,
        gemini_model=gemini_model,
        max_stories=max_stories,
        dry_run=effective_dry_run,
    )

