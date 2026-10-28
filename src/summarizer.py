import logging
import re
import requests
from typing import List

logger = logging.getLogger(__name__)

FALLBACK_MODELS = ["gemini-3.8-flash", "gemini-3.5-flash-lite"]

class ModelUnavailableError(Exception):
    """Raised when a specific Gemini model is deprecated, not found, or returns 404."""
    pass

def call_gemini_single_model(
    api_key: str,
    model: str,
    prompt: str,
    timeout_seconds: int = 25,
) -> str:
    """
    Call Google Gemini REST API generateContent for a given model.
    Sends API key in x-goog-api-key header for security.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 800,
        },
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=timeout_seconds)
    if resp.status_code == 404:
        raise ModelUnavailableError(f"Model '{model}' not found or deprecated (HTTP 404).")
    
    if resp.status_code != 200:
        err_msg = resp.text
        if "not found" in err_msg.lower() or "deprecated" in err_msg.lower():
            raise ModelUnavailableError(f"Model '{model}' unavailable: {err_msg}")
        raise RuntimeError(f"Gemini API error (HTTP {resp.status_code}): {err_msg}")

    data = resp.json()
    candidates = data.get("candidates", [])
    if not candidates:
        raise RuntimeError("Gemini API returned no candidates.")

    parts = candidates[0].get("content", {}).get("parts", [])
    if not parts or "text" not in parts[0]:
        raise RuntimeError("Gemini API response missing text part.")

    return parts[0]["text"]

def clean_bullets(raw_text: str) -> List[str]:
    """Parse raw LLM output into clean bullet points, filtering out preambles."""
    lines = raw_text.strip().split("\n")
    bullets = []
    for line in lines:
        cleaned = line.strip()
        if not cleaned:
            continue
        # Drop conversational intro ending with colon (e.g. "Dưới đây là tóm tắt:")
        if cleaned.endswith(":") and len(cleaned) < 80:
            continue
        # Check if line was originally a bullet item
        has_bullet_prefix = bool(re.match(r"^(\s*[-*•]|\d+\.)\s*", cleaned))
        stripped = re.sub(r"^(\s*[-*•]|\d+\.)\s*", "", cleaned).strip()
        if not stripped:
            continue
        
        # If line had bullet prefix, keep it. If no bullet prefix, ignore if conversational
        if has_bullet_prefix:
            bullets.append(stripped)
        elif len(stripped) > 20 and not stripped.lower().startswith(("hy vọng", "chúc", "cảm ơn", "bài viết này")):
            bullets.append(stripped)

    return bullets

def summarize_article(
    api_key: str,
    title: str,
    article_text: str,
    preferred_model: str = "gemini-3.8-flash",
) -> List[str]:
    """
    Summarize a tech article into 2-3 concise Vietnamese bullet points.
    Uses dynamic model cascading: if preferred_model fails with 404/deprecation,
    it automatically falls back through FALLBACK_MODELS.
    Guarantees zero-crash: returns title-based fallback bullet if all models fail.
    """
    if not api_key:
        return [f"Bài viết thảo luận về: {title} (Chưa cấu hình API Key AI)"]

    # Construct prompt
    if article_text and len(article_text.strip()) > 50:
        # Truncate article to 12,000 characters to stay safely within prompt limits
        sample_text = article_text.strip()[:12000]
        prompt = (
            f"Bạn là một biên tập viên tin tức công nghệ và AI.\n"
            f"Dưới đây là nội dung bài viết có tiêu đề: '{title}'.\n\n"
            f"Nội dung bài viết:\n{sample_text}\n\n"
            f"Yêu cầu:\n"
            f"Hãy tóm tắt nội dung chính thành 2-3 gạch đầu dòng súc tích bằng tiếng Việt.\n"
            f"Mỗi gạch đầu dòng bắt đầu bằng dấu '-', nêu bật thông tin cốt lõi, giá trị thực tiễn hoặc điểm đột phá.\n"
            f"Không dùng lời chào hay kết luận rườm rà."
        )
    else:
        prompt = (
            f"Bạn là một biên tập viên tin tức công nghệ và AI.\n"
            f"Bài viết có tiêu đề: '{title}'.\n"
            f"Do trang web gốc hạn chế truy cập, không thể tải nội dung chi tiết.\n"
            f"Dựa vào tiêu đề trên, hãy giải thích ngắn gọn trong 1-2 gạch đầu dòng bằng tiếng Việt về chủ đề hoặc công nghệ được thảo luận.\n"
            f"Mỗi gạch đầu dòng bắt đầu bằng dấu '-'."
        )

    # Build model cascade list: preferred_model first, then fallback models
    models_to_try = [preferred_model]
    for fb in FALLBACK_MODELS:
        if fb != preferred_model and fb not in models_to_try:
            models_to_try.append(fb)

    last_error = None
    for model in models_to_try:
        try:
            logger.info(f"Attempting summarization with model: {model}")
            raw_output = call_gemini_single_model(api_key, model, prompt)
            bullets = clean_bullets(raw_output)
            if bullets:
                return bullets
        except ModelUnavailableError as e:
            logger.warning(f"Model '{model}' unavailable, trying next model in cascade: {e}")
            last_error = e
        except Exception as e:
            logger.warning(f"Error calling model '{model}': {e}")
            last_error = e

    # Zero-crash ultimate fallback
    logger.error(f"All Gemini models in cascade failed for article '{title}': {last_error}")
    return [f"Bài viết thảo luận về: {title} (Tóm tắt AI tạm thời không khả dụng)"]

