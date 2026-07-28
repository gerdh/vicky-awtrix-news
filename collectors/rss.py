#!/usr/bin/env python3

"""RSS collector using Vicky's existing feed configuration."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import feedparser

from .base import make_item


class RSSCollector:
    name = "rss"

    def __init__(self, feeds: list[dict[str, Any]], max_per_feed: int = 5):
        self.feeds = feeds
        self.max_per_feed = max(1, int(max_per_feed))

    def collect(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        collected_at = datetime.now()

        for feed in self.feeds:
            if not isinstance(feed, dict) or not feed.get("enabled", True):
                continue

            source = str(feed.get("name", "")).strip()
            url = str(feed.get("url", "")).strip()
            if not source or not url:
                continue

            parsed = feedparser.parse(url)
            for entry in parsed.entries[: self.max_per_feed]:
                title = str(getattr(entry, "title", "") or "").strip()
                if not title:
                    continue

                items.append(
                    make_item(
                        title=title,
                        source=source,
                        category=str(feed.get("category", "news")),
                        priority=feed.get("priority", 5),
                        language=str(feed.get("language", "")),
                        color=str(feed.get("resolved_color", feed.get("color", "CCCCCC"))),
                        timestamp=collected_at,
                        metadata={
                            "collector": self.name,
                            "url": str(getattr(entry, "link", "") or ""),
                            "feed_url": url,
                            "feed_warning": str(getattr(parsed, "bozo_exception", "") or "")
                            if getattr(parsed, "bozo", False)
                            else "",
                        },
                    )
                )

        return items
