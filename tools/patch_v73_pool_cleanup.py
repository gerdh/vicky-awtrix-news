#!/usr/bin/env python3

"""Safely patch awtrix_news_vicki.py to use V7.3 pool cleanup.

The script creates a timestamped backup, verifies the exact old code exists,
and refuses to modify an unknown version.
"""

from __future__ import annotations

import argparse
import shutil
from datetime import datetime
from pathlib import Path


OLD_IMPORT = "from news_ranker import prioritize_items\n"
NEW_IMPORT = (
    "from news_ranker import prioritize_items\n"
    "from news_pool_manager import clean_news_pool\n"
)

OLD_CONSTANT = "POOL_HOURS = 48\n"
NEW_CONSTANT = "POOL_HOURS = 24\nPOOL_MAX_ITEMS = 40\n"

OLD_FUNCTION = '''def cleanup_pool(pool):
    cutoff = datetime.now() - timedelta(hours=POOL_HOURS)
    cleaned = []

    for item in pool:
        try:
            first_seen = datetime.fromisoformat(
                item["first_seen"]
            )
        except Exception:
            continue

        if (
            first_seen >= cutoff
            or not item.get("published", False)
        ):
            cleaned.append(item)

    return cleaned
'''

NEW_FUNCTION = '''def cleanup_pool(pool):
    cleaned, stats = clean_news_pool(
        pool,
        ttl_hours=POOL_HOURS,
        max_items=POOL_MAX_ITEMS,
    )

    removed = stats["input"] - stats["output"]
    if removed:
        log(
            "pool cleanup: "
            f"{removed} removed "
            f"(expired={stats['expired']}, "
            f"invalid={stats['invalid']}, "
            f"duplicates={stats['duplicates']}, "
            f"trimmed={stats['trimmed']})"
        )

    return cleaned
'''


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"Expected exactly one {label}, found {count}. "
            "No file was changed."
        )
    return text.replace(old, new, 1)


def patch_file(path: Path, dry_run: bool = False) -> Path | None:
    original = path.read_text(encoding="utf-8")

    if "from news_pool_manager import clean_news_pool" in original:
        print("V7.3 pool cleanup is already installed.")
        return None

    updated = replace_once(original, OLD_IMPORT, NEW_IMPORT, "import anchor")
    updated = replace_once(updated, OLD_CONSTANT, NEW_CONSTANT, "pool constant")
    updated = replace_once(updated, OLD_FUNCTION, NEW_FUNCTION, "cleanup function")

    if dry_run:
        print("Patch can be applied safely; no file was changed.")
        return None

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_name(f"{path.name}.before-v7.3-{stamp}")
    shutil.copy2(path, backup)

    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(updated, encoding="utf-8")
    temporary.replace(path)

    print(f"Patched: {path}")
    print(f"Backup:  {backup}")
    return backup


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "path",
        nargs="?",
        default="awtrix_news_vicki.py",
        help="path to awtrix_news_vicki.py",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    path = Path(args.path).resolve()
    if not path.is_file():
        parser.error(f"file not found: {path}")

    try:
        patch_file(path, dry_run=args.dry_run)
    except RuntimeError as error:
        print(f"ERROR: {error}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
