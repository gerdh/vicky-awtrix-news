from datetime import datetime

import pytest

from collectors.base import make_item


def test_make_item_creates_pool_compatible_structure():
    item = make_item(
        title="Bitcoin steigt deutlich",
        source="market",
        category="bitcoin",
        priority=120,
        language="de",
        timestamp=datetime(2026, 7, 26, 12, 0, 0),
        metadata={"change_percent": 8.1},
    )

    assert item["title"] == "Bitcoin steigt deutlich"
    assert item["source"] == "market"
    assert item["category"] == "bitcoin"
    assert item["priority"] == 100
    assert item["first_seen"] == "2026-07-26T12:00:00"
    assert item["published"] is False
    assert item["metadata"]["change_percent"] == 8.1


def test_item_identity_is_stable_for_punctuation_and_case():
    first = make_item(title="Tesla: Update verfügbar!", source="tesla")
    second = make_item(title="tesla update verfügbar", source="tesla")

    assert first["id"] == second["id"]


def test_same_title_from_different_sources_has_different_identity():
    first = make_item(title="Important event", source="bbc")
    second = make_item(title="Important event", source="reuters")

    assert first["id"] != second["id"]


def test_empty_title_is_rejected():
    with pytest.raises(ValueError):
        make_item(title="   ", source="test")
