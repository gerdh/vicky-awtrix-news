# Vicky 9 – coordinated two-site AWTRIX stack

Vicky 9 runs the same versioned information stack at two independent sites:

| Site | Computer | Hardware | Runtime |
|---|---|---|---|
| Montpellier | Orin | Nvidia Jetson Orin | local MQTT and local AWTRIX |
| Davanod | Moon | Raspberry Pi 5 | local MQTT and local AWTRIX |

**Stable branch:** `main`  
**Release:** `V9.0.0` / Vicky 9.0  
**Hugging Face Space:** https://huggingface.co/spaces/gerdh/vicky-awtrix-news

The sites are not connected at runtime. Each has its own broker and AWTRIX UID. Both AWTRIX devices may use the same private IP address `192.168.1.86` because they are on separate LANs. GitHub coordinates code, tests, documentation and releases; it does not bridge MQTT traffic.

See [V9 architecture](docs/ARCHITECTURE-V9.md), [Montpellier/Orin installation](docs/INSTALL-MONTPELLIER-ORIN.md) and [Davanod/Moon installation](docs/INSTALL-DAVANOD-MOON.md).

## Functions

- multilingual deterministic RSS news bulletins
- local CTranslate2/OPUS-MT translation for French, German and English
- persistent language state and AWTRIX button control
- optional Home Assistant/Météo-France rain warning
- Victron values read from Cerbo/GX D-Bus over SSH
- EUR/USD, Gold, Brent and NVIDIA market tiles
- independent systemd services so one component failure does not stop the others

Vicky does not use generative AI to rewrite factual news. If local translation fails, it keeps the source headline.

## V9 site model

All portable code is shared. Only local configuration differs:

- `VICKY_SITE`
- `VICKY_HARDWARE`
- local MQTT broker and credentials
- local AWTRIX UID
- local Cerbo/GX address and SSH key
- Home Assistant entity IDs

Real credentials and `config.py` are ignored by Git and must never be committed. Do not copy one site's `config.py` to the other site.

The local custom-app prefix is always:

```text
<local AWTRIX UID>/custom
```

The legacy Home Assistant endpoint `http://192.168.1.86/api/notify` is not the normal Vicky custom-app path.

## Market display contract

Every five minutes `markets/awtrix_markets.py` publishes four retained custom apps:

| Tile | Topic suffix | Color | Repetitions |
|---|---|---|---|
| EUR/USD | `market_eurusd` | `00FFFF` | 2 |
| Gold | `market_gold` | `FFD700` | 2 |
| Brent | `market_brent` | `FF8C00` | 2 |
| NVIDIA | `market_nvidia` | `76B900` | 2 |

The code calls `publish(..., color=<explicit color>, repeat=2)`. It does not publish the same tile twice in an outer loop. A duplicate must be diagnosed locally for multiple services, manual processes, old Home Assistant automations, cron jobs or restart loops.

## Installation

Clone or update the repository, then create the environment:

```bash
git clone https://github.com/gerdh/vicky-awtrix-news.git
cd vicky-awtrix-news
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

Configure exactly one site:

```bash
# Montpellier / Orin
bash scripts/configure-site.sh montpellier

# OR Davanod / Moon
bash scripts/configure-site.sh davanod
```

Install path-independent systemd units:

```bash
bash scripts/install-vicky9-services.sh
```

The units are installed but not started automatically. First test one market update:

```bash
.venv/bin/python markets/awtrix_markets.py --once
```

Then enable the locally required services:

```bash
sudo systemctl enable --now awtrix-news awtrix-markets awtrix-victron vicky-awtrix-button
```

## Main components

- `awtrix_news_vicki.py` – news service
- `display.py` – retained MQTT/AWTRIX publishing
- `markets/awtrix_markets.py` – EUR/USD, Gold, Brent and NVIDIA
- `victron/awtrix_victron.py` – Victron D-Bus display
- `scripts/vicky-awtrix-button` – button and language controller
- `weather/rain_warning.yaml` – Home Assistant rain-warning example
- `scripts/configure-site.sh` – local V9 configuration
- `scripts/install-vicky9-services.sh` – service installer
- `sites/*.conf.example` – non-secret site profiles

## Validation

Run:

```bash
PYTHONPATH=. .venv/bin/pytest -q
```

The V9 contract tests protect the four market names, their explicit non-white colors and exactly two display repetitions.

See [RELEASE-9.0.md](RELEASE-9.0.md) and [CHANGELOG.md](CHANGELOG.md) for release details.
