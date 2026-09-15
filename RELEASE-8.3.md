# Vicky 8.3

Vicky 8.3 is the tested market-display release for AWTRIX on Raspberry Pi/MOON
and Nvidia Jetson Orin.

## New in 8.3

- EUR/USD market tile
- gold price in USD per troy ounce
- Brent crude oil price in USD per barrel
- exactly two display repetitions for every market tile
- five-minute automatic refresh
- independent `awtrix-markets.service`, isolated from News and Victron
- retained last known value when one quote provider is temporarily unavailable
- parser tests for all three market data formats

The market display was validated with live EUR/USD, gold and Brent values on
the MOON Raspberry Pi installation before publication.

## Install on an existing checkout

```bash
git fetch origin
git switch v8.3
git pull --ff-only origin v8.3
bash scripts/install-market-service.sh
```

The installer uses the checkout's existing `config.py` and Python virtual
environment. It publishes one test update before enabling the service.

## Verify

```bash
systemctl --no-pager --full status awtrix-markets.service
journalctl -u awtrix-markets.service -n 30 --no-pager
```

Expected AWTRIX market tiles:

```text
EUR/USD 1.1551
Gold $4344.52/oz
Brent $107.44/bbl
```

Prices shown above are examples from the MOON validation run and are not fixed
values.
