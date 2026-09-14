#!/usr/bin/env python3
"""Publish EUR/USD, gold and Brent prices as retained AWTRIX custom apps."""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


POLL_SECONDS = max(60, int(os.environ.get("VICKY_MARKET_POLL_SECONDS", "300")))
HTTP_TIMEOUT = max(3, int(os.environ.get("VICKY_MARKET_HTTP_TIMEOUT", "15")))

EUR_USD_URL = os.environ.get(
    "VICKY_EUR_USD_URL",
    "https://api.frankfurter.app/latest?from=EUR&to=USD",
)
GOLD_USD_URL = os.environ.get(
    "VICKY_GOLD_USD_URL",
    "https://api.frankfurter.dev/v2/rate/XAU/USD",
)
BRENT_USD_URL = os.environ.get(
    "VICKY_BRENT_USD_URL",
    "https://query1.finance.yahoo.com/v8/finance/chart/BZ%3DF?interval=5m&range=1d",
)


def fetch_json(url, timeout=HTTP_TIMEOUT):
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "Vicky-AWTRIX/8.2",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        return json.load(response)


def positive_number(value, name):
    number = float(value)
    if number <= 0:
        raise ValueError(f"{name} must be positive")
    return number


def extract_eur_usd(payload):
    return positive_number(payload["rates"]["USD"], "EUR/USD")


def extract_gold_usd(payload):
    return positive_number(payload["rate"], "gold")


def extract_brent_usd(payload):
    result = payload["chart"]["result"]
    if not result:
        raise ValueError("Brent response contains no result")
    meta = result[0]["meta"]
    value = meta.get("regularMarketPrice")
    if value is None:
        closes = result[0].get("indicators", {}).get("quote", [{}])[0].get("close", [])
        value = next((close for close in reversed(closes) if close is not None), None)
    if value is None:
        raise ValueError("Brent response contains no current price")
    return positive_number(value, "Brent")


MARKETS = {
    "EURUSD": {
        "url": EUR_USD_URL,
        "extract": extract_eur_usd,
        "topic": "market_eurusd",
        "text": lambda price: f"EUR/USD {price:.4f}",
        "color": "00FFFF",
    },
    "GOLD": {
        "url": GOLD_USD_URL,
        "extract": extract_gold_usd,
        "topic": "market_gold",
        "text": lambda price: f"Gold ${price:.2f}/oz",
        "color": "FFD700",
    },
    "BRENT": {
        "url": BRENT_USD_URL,
        "extract": extract_brent_usd,
        "topic": "market_brent",
        "text": lambda price: f"Brent ${price:.2f}/bbl",
        "color": "FF8C00",
    },
}


def enabled_markets():
    requested = os.environ.get("VICKY_MARKETS", "EURUSD,GOLD,BRENT")
    names = [name.strip().upper() for name in requested.split(",") if name.strip()]
    unknown = [name for name in names if name not in MARKETS]
    if unknown:
        raise ValueError(f"Unknown VICKY_MARKETS value(s): {', '.join(unknown)}")
    return names


def publish_tile(topic, text, color):
    # Import only when publishing so parser tests do not require a local config.py.
    from display import publish

    publish(topic, text, color=color, repeat=2)


def publish_once(fetcher=fetch_json, publisher=publish_tile):
    published = 0
    for name in enabled_markets():
        market = MARKETS[name]
        try:
            payload = fetcher(market["url"])
            price = market["extract"](payload)
            text = market["text"](price)
            publisher(market["topic"], text, market["color"])
            print(f"{name}: {text}", flush=True)
            published += 1
        except Exception as error:
            # Keep the last retained AWTRIX value if one provider is temporarily down.
            print(f"{name} ERROR: {type(error).__name__}: {error}", flush=True)
    return published


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="fetch and publish one update")
    args = parser.parse_args()

    while True:
        publish_once()
        if args.once:
            return
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
