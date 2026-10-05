# Vicky 9.1

Vicky 9.1 extends the coordinated two-site Vicky 9 architecture with NVIDIA market data.

## Sites

- Montpellier: Nvidia Jetson Orin installation
- Davanod: Raspberry Pi 5 Moon installation

The sites remain independent. Each uses its own local MQTT broker and AWTRIX UID. GitHub coordinates the common source, tests, documentation and releases.

## Market contract

Every five minutes the market service publishes four retained AWTRIX custom apps:

| Tile | Topic suffix | Color | Repetitions |
|---|---|---|---|
| EUR/USD | `market_eurusd` | `00FFFF` | 2 |
| Gold | `market_gold` | `FFD700` | 2 |
| Brent | `market_brent` | `FF8C00` | 2 |
| NVIDIA | `market_nvidia` | `76B900` | 2 |

Each tile is published once with `repeat: 2`; there is no second outer publication loop. The contract tests reject missing market names, white or empty colors, and repetition counts other than two.

## Upgrade

Update both systems to tag `V9.1.0`, run the matching local site configuration, install the services, test one market update and only then enable or restart the locally required services.

```bash
git fetch --tags origin
git switch --detach V9.1.0
bash scripts/configure-site.sh montpellier  # on Orin
# OR
bash scripts/configure-site.sh davanod      # on Moon
bash scripts/install-vicky9-services.sh
.venv/bin/python markets/awtrix_markets.py --once
```

Never copy `config.py`, MQTT credentials, AWTRIX UIDs or Cerbo/GX SSH settings between the two sites.
