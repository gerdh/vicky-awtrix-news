#!/usr/bin/env python3

"""Small health monitor for Vicky RSS feeds.

This module does not publish anything to AWTRIX. It records whether configured
feeds answered successfully, how many entries they returned, and whether
feedparser reported malformed content.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
import json
import os
import tempfile

import feedparser


Parser = Callable[[str], Any]


@dataclass
class FeedHealth:
    name: str
    url: str
    ok: bool
    entries: int
    checked_at: str
    warning: str = ""
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def check_feed(feed: dict[str, Any], parser: Parser = feedparser.parse) -> FeedHealth:
    name = str(feed.get("name", "")).strip() or "unnamed"
    url = str(feed.get("url", "")).strip()
    checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    if not url:
        return FeedHealth(
            name=name,
            url=url,
            ok=False,
            entries=0,
            checked_at=checked_at,
            error="missing feed URL",
        )

    try:
        parsed = parser(url)
        entries = len(getattr(parsed, "entries", []) or [])
        warning = ""
        if getattr(parsed, "bozo", False):
            warning = str(getattr(parsed, "bozo_exception", "") or "malformed feed")

        return FeedHealth(
            name=name,
            url=url,
            ok=entries > 0,
            entries=entries,
            checked_at=checked_at,
            warning=warning,
            error="" if entries > 0 else "feed returned no entries",
        )
    except Exception as error:
        return FeedHealth(
            name=name,
            url=url,
            ok=False,
            entries=0,
            checked_at=checked_at,
            error=f"{type(error).__name__}: {error}",
        )


def check_feeds(
    feeds: list[dict[str, Any]],
    parser: Parser = feedparser.parse,
) -> list[FeedHealth]:
    results: list[FeedHealth] = []
    for feed in feeds:
        if not isinstance(feed, dict) or not feed.get("enabled", True):
            continue
        results.append(check_feed(feed, parser=parser))
    return results


def write_report(path: str | Path, results: list[FeedHealth]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "feeds": [result.to_dict() for result in results],
        "summary": {
            "total": len(results),
            "ok": sum(result.ok for result in results),
            "failed": sum(not result.ok for result in results),
            "warnings": sum(bool(result.warning) for result in results),
        },
    }

    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=str(target.parent),
        text=True,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary_name, target)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise
