"""Authenticated access to the subscription Worker; never logs credentials."""
from dataclasses import dataclass
from urllib.parse import urlsplit

import requests


class SubscriberError(Exception):
    pass


def valid_api_url(url: str) -> bool:
    try:
        parsed = urlsplit(url)
        # Accessing port also validates malformed or out-of-range port values.
        parsed.port
        return bool(parsed.scheme == "https" and parsed.hostname and not parsed.username
                    and not parsed.password and not parsed.query and not parsed.fragment)
    except ValueError:
        return False


@dataclass(frozen=True)
class Subscriber:
    chat_id: str
    version: int


class SubscriberClient:
    def __init__(self, base_url: str, token: str):
        if not valid_api_url(base_url):
            raise SubscriberError("Subscriber API requires an HTTPS base URL without credentials or query.")
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {token}"}

    def _request(self, method: str, path: str, **kwargs):
        try:
            response = getattr(requests, method)(
                self.base_url + path, headers=self.headers, timeout=15,
                allow_redirects=False, **kwargs,
            )
            if response.status_code != 200:
                raise SubscriberError("Subscriber API returned an unsuccessful status.")
            return response.json()
        except (requests.RequestException, ValueError):
            raise SubscriberError("Subscriber API request failed.") from None

    def list_active(self) -> list[Subscriber]:
        subscribers = {}
        cursor = None
        seen_cursors = set()
        while True:
            data = self._request("get", "/subscribers", params={} if cursor is None else {"cursor": cursor})
            if not isinstance(data, dict) or not isinstance(data.get("subscribers"), list) or "next_cursor" not in data:
                raise SubscriberError("Invalid subscriber list response.")
            for item in data["subscribers"]:
                if (not isinstance(item, dict) or not isinstance(item.get("chat_id"), str)
                        or not item["chat_id"].isascii() or not item["chat_id"].isdigit()
                        or type(item.get("version")) is not int or item["version"] < 1):
                    raise SubscriberError("Invalid subscriber entry.")
                subscribers[item["chat_id"]] = Subscriber(item["chat_id"], item["version"])
            cursor = data["next_cursor"]
            if cursor is None:
                return list(subscribers.values())
            if not isinstance(cursor, str) or not cursor or cursor in seen_cursors:
                raise SubscriberError("Invalid subscriber pagination cursor.")
            seen_cursors.add(cursor)

    def disable(self, subscriber: Subscriber) -> None:
        data = self._request("post", "/subscribers/disable", json={
            "chat_id": subscriber.chat_id, "version": subscriber.version,
        })
        if not isinstance(data, dict) or type(data.get("disabled")) is not bool:
            raise SubscriberError("Invalid disable response.")
