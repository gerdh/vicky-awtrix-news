from datetime import datetime, timedelta

from news_pool_manager import clean_news_pool


NOW = datetime(2026, 7, 26, 21, 0, 0)


def item(title, hours_old=0, *, item_id=None, published=False):
    return {
        "id": item_id or title.lower(),
        "title": title,
        "first_seen": (NOW - timedelta(hours=hours_old)).isoformat(),
        "published": published,
    }


def test_old_unpublished_item_expires():
    cleaned, stats = clean_news_pool(
        [item("Old", 48, published=False)],
        now=NOW,
        ttl_hours=24,
        max_items=40,
    )

    assert cleaned == []
    assert stats["expired"] == 1


def test_newest_duplicate_wins():
    older = item("Same older", 3, item_id="same")
    newer = item("Same newer", 1, item_id="same")

    cleaned, stats = clean_news_pool(
        [older, newer], now=NOW, ttl_hours=24, max_items=40
    )

    assert [entry["title"] for entry in cleaned] == ["Same newer"]
    assert stats["duplicates"] == 1


def test_pool_is_limited_to_newest_items():
    pool = [item(f"News {number}", number) for number in range(10)]

    cleaned, stats = clean_news_pool(
        pool, now=NOW, ttl_hours=24, max_items=4
    )

    assert [entry["title"] for entry in cleaned] == [
        "News 3",
        "News 2",
        "News 1",
        "News 0",
    ]
    assert stats["trimmed"] == 6


def test_invalid_entries_are_removed():
    cleaned, stats = clean_news_pool(
        [None, {}, {"title": "No timestamp"}],
        now=NOW,
        ttl_hours=24,
        max_items=40,
    )

    assert cleaned == []
    assert stats["invalid"] == 3
