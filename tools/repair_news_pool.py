#!/usr/bin/env python3

"""Repair and compact Vicky's news pool.

This tool removes malformed entries, enforces a strict age limit for every
entry, removes duplicate IDs/titles and keeps only the newest entries.
It writes the result atomically and creates a timestamped backup first.
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


def parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def normalized_title(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.lower().split())


def repair_pool(pool: Any, max_age_hours: int, max_items: int) -> tuple[list[dict], dict]:
    now = datetime.now()
    cutoff = now - timedelta(hours=max_age_hours)

    stats = {
        "input": 0,
        "malformed": 0,
        "expired": 0,
        "duplicates": 0,
        "trimmed": 0,
        "output": 0,
    }

    if not isinstance(pool, list):
        stats["malformed"] = 1
        return [], stats

    stats["input"] = len(pool)
    valid: list[dict] = []

    for item in pool:
        if not isinstance(item, dict):
            stats["malformed"] += 1
            continue

        first_seen = parse_timestamp(item.get("first_seen"))
        title = str(item.get("title", "")).strip()

        if first_seen is None or not title:
            stats["malformed"] += 1
            continue

        # Strict TTL: old entries are removed regardless of published state.
        if first_seen < cutoff:
            stats["expired"] += 1
            continue

        valid.append(item)

    valid.sort(
        key=lambda item: parse_timestamp(item.get("first_seen")) or datetime.min,
        reverse=True,
    )

    unique: list[dict] = []
    seen: set[str] = set()

    for item in valid:
        item_id = str(item.get("id", "")).strip()
        title_key = normalized_title(item.get("title"))
        key = item_id or title_key

        if not key or key in seen:
            stats["duplicates"] += 1
            continue

        seen.add(key)
        unique.append(item)

    if len(unique) > max_items:
        stats["trimmed"] = len(unique) - max_items
        unique = unique[:max_items]

    stats["output"] = len(unique)
    return unique, stats


def atomic_write(path: Path, value: list[dict]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Repair Vicky's news pool")
    parser.add_argument(
        "--pool",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "cache/news_pool_v4.json",
        help="path to news_pool_v4.json",
    )
    parser.add_argument("--max-age-hours", type=int, default=24)
    parser.add_argument("--max-items", type=int, default=40)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show what would change without writing",
    )
    args = parser.parse_args()

    if args.max_age_hours <= 0 or args.max_items <= 0:
        parser.error("--max-age-hours and --max-items must be positive")

    try:
        original = json.loads(args.pool.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"Pool file not found: {args.pool}")
        return 2
    except json.JSONDecodeError as error:
        print(f"Invalid JSON in {args.pool}: {error}")
        return 2

    repaired, stats = repair_pool(original, args.max_age_hours, args.max_items)

    print(
        "pool repair: "
        f"input={stats['input']} "
        f"malformed={stats['malformed']} "
        f"expired={stats['expired']} "
        f"duplicates={stats['duplicates']} "
        f"trimmed={stats['trimmed']} "
        f"output={stats['output']}"
    )

    if args.dry_run:
        return 0

    backup = args.pool.with_name(
        f"{args.pool.stem}.backup-{datetime.now():%Y%m%d-%H%M%S}{args.pool.suffix}"
    )
    shutil.copy2(args.pool, backup)
    atomic_write(args.pool, repaired)

    print(f"backup: {backup}")
    print(f"written: {args.pool}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
