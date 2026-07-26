#!/usr/bin/env python3

"""Shared collector interface and normalized Vicky item creation."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import Any, Protocol


class Collector(Protocol):
    """A source that returns normalized Vicky information items."""

    name: str

    def collect(self) -> list[dict[str, Any]]:
        """Collect current items from the source."""


def normalize_text(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^\w\s]", " ", value, flags=re.UNICODE)
    return re.sub(r"\s+", " ", value).strip()


def make_item(
    *,
    title: str,
    source: str,
    category: str = "news",
    priority: int = 5,
    language: str = "",
    color: str = "CCCCCC",
    timestamp: datetime | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create the common item structure used by all Vicky collectors.

    The generated structure remains compatible with the current news pool while
    adding category, timestamp and metadata fields needed by the V7.4 engine.
    """

    clean_title = str(title).strip()
    clean_source = str(source).strip()

    if not clean_title:
        raise ValueError("title must not be empty")
    if not clean_source:
        raise ValueError("source must not be empty")

    try:
        clean_priority = int(priority)
    except (TypeError, ValueError) as error:
        raise ValueError("priority must be an integer") from error

    clean_priority = max(0, min(100, clean_priority))
    seen_at = timestamp or datetime.now()

    identity = f"{clean_source}|{normalize_text(clean_title)}"
    item_id = hashlib.sha1(identity.encode("utf-8")).hexdigest()

    return {
        "id": item_id,
        "source": clean_source,
        "title": clean_title,
        "category": str(category).strip() or "news",
        "priority": clean_priority,
        "language": str(language).strip(),
        "color": str(color).strip() or "CCCCCC",
        "first_seen": seen_at.isoformat(timespec="seconds"),
        "timestamp": seen_at.isoformat(timespec="seconds"),
        "published": False,
        "metadata": dict(metadata or {}),
    }
