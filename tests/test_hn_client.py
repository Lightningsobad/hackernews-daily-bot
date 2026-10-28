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
    assert stories[0].title == "Python 3.14 Released"  # Higher points first
    assert stories[0].points == 500
    assert stories[0].hn_url == "https://news.ycombinator.com/item?id=102"
    assert stories[1].title == "New Deep Learning Breakthrough"
    assert stories[1].points == 350

def test_fetch_top_stories_handles_missing_url():
    mock_response = {
        "hits": [
            {
                "objectID": "201",
                "title": "Ask HN: Favorite AI tools?",
                "url": None,
                "points": 250,
                "num_comments": 95,
                "created_at_i": 1700000300
            }
        ]
    }
    with patch("requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: mock_response)
        stories = fetch_top_stories(keywords=["AI"], max_stories=1)

    assert len(stories) == 1
    assert stories[0].url == "https://news.ycombinator.com/item?id=201"

def test_fetch_top_stories_deduplication():
    mock_response = {
        "hits": [
            {
                "objectID": "301",
                "title": "AI in Rust",
                "url": "https://example.com/rust-ai",
                "points": 150,
                "num_comments": 30,
                "created_at_i": 1700000400
            }
        ]
    }
    # Multiple keywords returning same article
    with patch("requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: mock_response)
        stories = fetch_top_stories(keywords=["AI", "Rust"], max_stories=5)

    assert len(stories) == 1
    assert stories[0].object_id == "301"

