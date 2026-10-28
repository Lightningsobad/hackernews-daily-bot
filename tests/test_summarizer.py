from unittest.mock import patch
from src.summarizer import summarize_article, ModelUnavailableError, FALLBACK_MODELS

def test_summarize_article_success():
    mock_text = "- Đây là bước đột phá mới về mô hình AI.\n- Cải thiện tốc độ suy luận gấp 2 lần."
    with patch("src.summarizer.call_gemini_single_model", return_value=mock_text):
        bullets = summarize_article(
            api_key="fake_key",
            title="Next Gen LLM Announced",
            article_text="Full article text...",
            preferred_model="gemini-2.5-flash",
        )
    assert len(bullets) == 2
    assert "đột phá" in bullets[0]
    assert "Cải thiện" in bullets[1]

def test_summarize_article_cascades_to_fallback_model_on_deprecation():
    call_records = []

    def fake_call(api_key, model, prompt, timeout_seconds=25):
        call_records.append(model)
        if model == "deprecated-model":
            raise ModelUnavailableError("Model deprecated or not found")
        return "- Tóm tắt thành công từ mô hình dự phòng."

    with patch("src.summarizer.call_gemini_single_model", side_effect=fake_call):
        bullets = summarize_article(
            api_key="fake_key",
            title="Tech News",
            article_text="Content...",
            preferred_model="deprecated-model",
        )

    assert len(bullets) >= 1
    assert "dự phòng" in bullets[0]
    assert call_records[0] == "deprecated-model"
    assert len(call_records) >= 2  # Proves cascade happened

def test_summarize_article_fallback_when_empty_content():
    captured_prompts = []

    def fake_call(api_key, model, prompt, timeout_seconds=25):
        captured_prompts.append(prompt)
        return "- Phân tích dựa trên tiêu đề: Bản cập nhật mới."

    with patch("src.summarizer.call_gemini_single_model", side_effect=fake_call):
        bullets = summarize_article(
            api_key="fake_key",
            title="Show HN: A new compiler",
            article_text="",
            preferred_model="gemini-2.5-flash",
        )
    assert len(bullets) >= 1
    assert "Show HN: A new compiler" in captured_prompts[0]

def test_summarize_article_zero_crash_on_total_ai_failure():
    # If all models fail, return safe fallback bullet rather than crashing pipeline
    with patch("src.summarizer.call_gemini_single_model", side_effect=Exception("Total quota exhaustion")):
        bullets = summarize_article(
            api_key="fake_key",
            title="Important Python Update",
            article_text="Content...",
            preferred_model="gemini-2.5-flash",
        )
    assert len(bullets) >= 1
    assert "Important Python Update" in bullets[0]
