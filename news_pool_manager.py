#!/usr/bin/env python3

"""News-pool validation, expiry, deduplication and size limiting."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Iterable


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def clean_news_pool(
    pool: Iterable[Any],
    *,
    now: datetime | None = None,
    ttl_hours: int = 24,
    max_items: int = 40,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Return a valid, recent, unique and bounded news pool.

    Expiry applies to every item, including unpublished headlines. When two
    entries have the same id, the newest entry wins. Items without an id fall
    back to their normalized title as a deduplication key.
    """

    if ttl_hours <= 0:
        raise ValueError("ttl_hours must be greater than zero")
    if max_items <= 0:
        raise ValueError("max_items must be greater than zero")

    current_time = now or datetime.now()
    cutoff = current_time - timedelta(hours=ttl_hours)
    stats = {
        "input": 0,
        "invalid": 0,
        "expired": 0,
        "duplicates": 0,
        "trimmed": 0,
        "output": 0,
    }

    candidates: list[tuple[datetime, dict[str, Any]]] = []

    for raw_item in pool:
        stats["input"] += 1

        if not isinstance(raw_item, dict):
            stats["invalid"] += 1
            continue

        title = str(raw_item.get("title", "")).strip()
        first_seen = _parse_time(raw_item.get("first_seen"))

        if not title or first_seen is None:
            stats["invalid"] += 1
            continue

        if first_seen < cutoff:
            stats["expired"] += 1
            continue

        item = dict(raw_item)
        item["title"] = title
        candidates.append((first_seen, item))

    candidates.sort(key=lambda pair: pair[0], reverse=True)

    unique: list[tuple[datetime, dict[str, Any]]] = []
    seen_keys: set[str] = set()

    for first_seen, item in candidates:
        item_id = str(item.get("id", "")).strip()
        fallback = " ".join(item["title"].lower().split())
        key = item_id or fallback

        if not key:
            stats["invalid"] += 1
            continue

        if key in seen_keys:
            stats["duplicates"] += 1
            continue

        seen_keys.add(key)
        unique.append((first_seen, item))

    if len(unique) > max_items:
        stats["trimmed"] = len(unique) - max_items
        unique = unique[:max_items]

    # Store oldest-to-newest to preserve the historic pool-file ordering.
    cleaned = [item for _, item in reversed(unique)]
    stats["output"] = len(cleaned)
    return cleaned, stats
