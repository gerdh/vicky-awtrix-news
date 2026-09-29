import sys
from types import SimpleNamespace

from markets.awtrix_markets import MARKETS, publish_tile


def test_market_names_and_colors_are_fixed():
    assert list(MARKETS) == ["EURUSD", "GOLD", "BRENT"]
    assert MARKETS["EURUSD"]["color"] == "00FFFF"
    assert MARKETS["GOLD"]["color"] == "FFD700"
    assert MARKETS["BRENT"]["color"] == "FF8C00"
    assert all(item["color"] not in {"FFFFFF", "CCCCCC", ""} for item in MARKETS.values())


def test_market_publish_contract_is_exactly_two_repetitions(monkeypatch):
    calls = []

    def fake_publish(topic, text, **kwargs):
        calls.append((topic, text, kwargs))

    monkeypatch.setitem(sys.modules, "display", SimpleNamespace(publish=fake_publish))
    publish_tile("market_gold", "Gold $100.00/oz", "FFD700")

    assert calls == [
        (
            "market_gold",
            "Gold $100.00/oz",
            {"color": "FFD700", "repeat": 2},
        )
    ]
