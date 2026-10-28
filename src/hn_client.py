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
    "Python",
    "Rust",
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
    Fetch and filter top upvoted Hacker News stories related to target keywords
    from the last `hours_back` hours.
    """
    if keywords is None:
        keywords = DEFAULT_KEYWORDS

    cutoff_timestamp = int(time.time()) - (hours_back * 3600)
    seen_ids = set()
    stories_map = {}

    for kw in keywords:
        params = {
            "tags": "story",
            "query": kw,
            "numericFilters": f"created_at_i>{cutoff_timestamp}",
            "hitsPerPage": 50,
        }
        try:
            resp = requests.get(ALGOLIA_SEARCH_URL, params=params, timeout=timeout_seconds)
            if resp.status_code != 200:
                continue
            data = resp.json()
        except Exception:
            # Continue checking other keywords if one request fails
            continue

        hits = data.get("hits", [])
        for hit in hits:
            obj_id = str(hit.get("objectID") or "")
            if not obj_id or obj_id in seen_ids:
                continue

            seen_ids.add(obj_id)
            title = hit.get("title") or "No Title"
            points = hit.get("points") or 0
            comments_count = hit.get("num_comments") or 0
            created_at = hit.get("created_at_i") or 0
            hn_url = f"https://news.ycombinator.com/item?id={obj_id}"
            url = hit.get("url") or hn_url

            story = HNStory(
                object_id=obj_id,
                title=title,
                url=url,
                points=points,
                comments_count=comments_count,
                hn_url=hn_url,
                created_at=created_at,
            )
            stories_map[obj_id] = story

    all_stories = list(stories_map.values())
    all_stories.sort(key=lambda s: s.points, reverse=True)
    return all_stories[:max_stories]

