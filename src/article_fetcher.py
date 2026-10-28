import logging
import requests
import trafilatura

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
}

def extract_text_from_html(html_content: str) -> str:
    """
    Extract readable article body text from HTML using trafilatura.
    Returns clean text or empty string if extraction yields nothing.
    """
    if not html_content:
        return ""
    try:
        extracted = trafilatura.extract(
            html_content,
            include_comments=False,
            include_tables=False,
            no_fallback=False,
        )
        return (extracted or "").strip()
    except Exception as e:
        logger.warning(f"Error parsing HTML text: {e}")
        return ""

def fetch_article_text(url: str, timeout_seconds: int = 10) -> str:
    """
    Fetch the webpage at `url` and extract its main article body text.
    Gracefully returns an empty string on network timeout, HTTP error, or paywall.
    """
    if not url or not url.startswith("http"):
        return ""

    try:
        resp = requests.get(
            url,
            headers=DEFAULT_HEADERS,
            timeout=timeout_seconds,
            allow_redirects=True,
        )
        if resp.status_code != 200:
            logger.warning(f"Failed to fetch article {url}: HTTP {resp.status_code}")
            return ""

        text = extract_text_from_html(resp.text)
        return text
    except Exception as e:
        logger.warning(f"Exception fetching article {url}: {e}")
        return ""
