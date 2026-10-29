import time
import requests
from dataclasses import dataclass
from typing import List, Optional

ALGOLIA_SEARCH_URL = "https://hn.algolia.com/api/v1/search"
DEFAULT_KEYWORDS = [
    "AI",
    "LLM",
    "machine learning",
    "programming",
    "Flutter",
    "Android",
    "Kotlin",
    "Java",
    "developer",
    "deep learning",
]

@dataclass(frozen=True)
class HNStory:
    object_id: str
    title: str
    url: str
    points: int
    comments_count: int
    hn_url: str
    created_at: int

def fetch_top_stories(
    keywords: Optional[List[str]] = None,
    hours_back: int = 24,
    max_stories: int = 5,
    timeout_seconds: int = 15,
) -> List[HNStory]:
    """
    Fetch top Hacker News stories matching keywords, prioritizing active Front Page stories
    at report time, falling back to recent stories from the last `hours_back` hours if needed.
    """
    if keywords is None:
        keywords = DEFAULT_KEYWORDS

    cutoff_timestamp = int(time.time()) - (hours_back * 3600)
    seen_ids = set()

    def _query(tags: str, numeric_filters: Optional[str] = None) -> List[HNStory]:
        results = []
        for kw in keywords:
            params = {
                "tags": tags,
                "query": kw,
                "hitsPerPage": 50,
            }
            if numeric_filters:
                params["numericFilters"] = numeric_filters
            try:
                resp = requests.get(ALGOLIA_SEARCH_URL, params=params, timeout=timeout_seconds)
                if resp.status_code != 200:
                    continue
                data = resp.json()
            except Exception:
                continue

            for hit in data.get("hits", []):
                obj_id = str(hit.get("objectID") or "")
                if not obj_id or obj_id in seen_ids:
                    continue

                seen_ids.add(obj_id)
                hn_url = f"https://news.ycombinator.com/item?id={obj_id}"
                results.append(
                    HNStory(
                        object_id=obj_id,
                        title=hit.get("title") or "No Title",
                        url=hit.get("url") or hn_url,
                        points=hit.get("points") or 0,
                        comments_count=hit.get("num_comments") or 0,
                        hn_url=hn_url,
                        created_at=hit.get("created_at_i") or 0,
                    )
                )
        results.sort(key=lambda s: s.points, reverse=True)
        return results

    # Priority 1: Stories currently active on the Hacker News Front Page
    front_page_stories = _query(tags="front_page")
    if len(front_page_stories) >= max_stories:
        return front_page_stories[:max_stories]

    # Priority 2: Fallback to recent 24h stories if front page has fewer matches
    fallback_stories = _query(tags="story", numeric_filters=f"created_at_i>{cutoff_timestamp}")
    combined = front_page_stories + fallback_stories
    return combined[:max_stories]


