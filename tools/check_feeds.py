#!/usr/bin/env python3

"""Check configured Vicky RSS feeds and write a compact JSON report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from feed_monitor import check_feeds, write_report


def load_feeds(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if isinstance(data, dict):
        feeds = data.get("feeds", [])
    else:
        feeds = data

    if not isinstance(feeds, list):
        raise ValueError("feed configuration must contain a list")
    return feeds


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default=str(ROOT / "feeds.json"),
        help="path to feeds.json",
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "cache" / "feed_health.json"),
        help="path for the JSON health report",
    )
    args = parser.parse_args()

    feeds = load_feeds(Path(args.config))
    results = check_feeds(feeds)
    write_report(args.output, results)

    for result in results:
        state = "OK" if result.ok else "FEHLER"
        details = f"{result.entries} Meldungen"
        if result.error:
            details = result.error
        elif result.warning:
            details += f"; Warnung: {result.warning}"
        print(f"{state:6} {result.name:20} {details}")

    failed = sum(not result.ok for result in results)
    print(f"\nFeeds: {len(results)}, Fehler: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
