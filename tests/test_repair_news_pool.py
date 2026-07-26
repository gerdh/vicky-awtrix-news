from datetime import datetime, timedelta

from tools.repair_news_pool import repair_pool


def item(title: str, age_hours: int, item_id: str, published: bool = False):
    return {
        "id": item_id,
        "title": title,
        "first_seen": (datetime.now() - timedelta(hours=age_hours)).isoformat(
            timespec="seconds"
        ),
        "published": published,
    }


def test_expired_unpublished_items_are_removed():
    pool = [
        item("new", 1, "new"),
        item("old unpublished", 48, "old", published=False),
    ]

    repaired, stats = repair_pool(pool, max_age_hours=24, max_items=40)

    assert [entry["id"] for entry in repaired] == ["new"]
    assert stats["expired"] == 1


def test_newest_unique_items_are_kept_and_limited():
    pool = [
        item("same title", 1, "same"),
        item("same title", 2, "same"),
        item("second", 3, "second"),
        item("third", 4, "third"),
    ]

    repaired, stats = repair_pool(pool, max_age_hours=24, max_items=2)

    assert [entry["id"] for entry in repaired] == ["same", "second"]
    assert stats["duplicates"] == 1
    assert stats["trimmed"] == 1
