import pytest

from markets.awtrix_markets import (
    extract_brent_usd,
    extract_eur_usd,
    extract_gold_usd,
)


def test_extract_eur_usd():
    assert extract_eur_usd({"rates": {"USD": 1.2345}}) == 1.2345


def test_extract_gold_usd():
    assert extract_gold_usd({"rate": 2345.67}) == 2345.67


def test_extract_brent_regular_market_price():
    payload = {"chart": {"result": [{"meta": {"regularMarketPrice": 81.25}}]}}
    assert extract_brent_usd(payload) == 81.25


def test_extract_brent_falls_back_to_last_close():
    payload = {
        "chart": {
            "result": [{
                "meta": {},
                "indicators": {"quote": [{"close": [80.1, None, 81.2]}]},
            }]
        }
    }
    assert extract_brent_usd(payload) == 81.2


def test_extract_brent_rejects_missing_price():
    payload = {"chart": {"result": [{"meta": {}, "indicators": {"quote": [{}]}}]}}
    with pytest.raises(ValueError):
        extract_brent_usd(payload)
