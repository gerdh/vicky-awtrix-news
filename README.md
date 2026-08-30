# Vicky 8 – AWTRIX information stack

Vicky 8 is the released successor to the V7 family. It brings the AWTRIX functions used on the reference Jetson Orin installation into one documented project while keeping the individual services independent.

**Stable branch: `v8`**  
**Release: `V8.0.0` / Vicky 8.0**

Vicky 8 covers three functional areas:

- multilingual news bulletins
- local rain warnings from Home Assistant / Météo-France
- the Victron energy display stack

The news and rain-warning components share one persistent output language: French, German or English. The compact Victron labels (`Sol`, `Batt`, `In`, `Out`) stay language-neutral because they are intentionally short and widely understandable.

## AI / machine-learning scope

Vicky 8 is **not a generative-AI news editor**. The news pipeline is intentionally deterministic: RSS retrieval, feed-health checks, duplicate/history filtering, ranking and safe headline handling are performed with normal program logic rather than a free-form large language model.

Vicky 8 does use local neural machine-translation models through CTranslate2 / OPUS-MT for French, German and English translation. That translation layer can reasonably be described as local AI/ML, but the overall system is not "fully AI based".

Generative AI **was used in earlier Vicky versions**. A local llama.cpp language model was part of the editorial pipeline and was asked to rewrite or improve news headlines before publication. During real-world testing, however, this approach proved unsuitable for a factual news display: even when the source headline was correct, generative models could occasionally add details that were not present in the source, alter the meaning, combine information from different items or make a headline sound more certain than the original report.

For Vicky 8, that generative editorial stage was therefore deliberately removed. This was not because AI could not run locally, but because factual reliability is more important than stylistic rewriting for short news headlines. Vicky should display what the source actually reported, not what a language model considers a plausible improvement.

The V8 design therefore favors:

- factual fidelity: no invented names, numbers, causes, context or conclusions
- predictable behavior: headlines follow a controlled processing path
- source integrity: one story remains one story and is not merged with another
- easier fault diagnosis and testing
- lower CPU/RAM and model-management overhead on the always-on Orin
- graceful fallback: if translation fails, Vicky shows the original headline instead of generating substitute content

In short: **local AI-assisted translation, deterministic news processing**.

## V8 design goals

- one clear Vicky generation instead of accumulated V5/V6/V7 compatibility paths
- independent services so a news, weather or Victron failure does not take down the other functions
- deterministic headline processing instead of generative rewriting
- one shared FR/DE/EN language state for user-facing prose
- reproducible AWTRIX button behavior
- version-controlled Home Assistant and systemd integration
- minimal runtime state in Git; caches, logs and local credentials stay outside the repository

## Components

### News

The news service periodically reads the configured RSS feeds, checks feed health, maintains a local headline pool, ranks unpublished stories and publishes short AWTRIX bulletins.

The V8 editorial path is deliberately simple:

```text
RSS feeds
    │
    ▼
Feed health checks
    │
    ▼
Local news pool
    │
    ▼
Duplicate/history filtering
    │
    ▼
Importance ranking
    │
    ▼
safe_news_editor
    │
    ▼
offline_translator
(CTranslate2 + local OPUS-MT models)
    │
    ▼
MQTT
    │
    ▼
AWTRIX Light
```

There is no V8 `editor_v76.py` or llama.cpp editorial stage. If a translation cannot be produced safely, Vicky falls back to the original headline rather than inventing or combining information.

Current bulletin behavior:

- RSS polling every 5 minutes
- regular bulletin interval: 10 minutes
- up to 8 bulletin messages
- news visible for 10 minutes
- configurable feed catalogue in `feeds.json`
- source-code prefixes such as `LM`, `F24`, `SPG`, `BBC`, `FIG`
- persistent local output-language selection
- automatic clearing of old AWTRIX news topics

### Language and AWTRIX buttons

The V8 button controller is versioned as `scripts/vicky-awtrix-button` and its service definition as `systemd/vicky-awtrix-button.service`.

- **left short press:** force a fresh news bulletin
- **right short press:** cycle output language `FR → DE → EN → FR`, then refresh the news
- **middle button:** reserved for AWTRIX itself and not used by Vicky

The selected language is stored by `language_state.py` and also published as retained MQTT state. Home Assistant receives the same language through MQTT Discovery, allowing other Vicky components to follow the selection.

### Rain warning

`weather/rain_warning.yaml` contains the Home Assistant automation for the Billiat Météo-France `next_rain` sensor.

It checks the one-hour rain forecast every 5 minutes and publishes an AWTRIX warning only when the forecast contains `Pluie faible`, `Pluie modérée` or `Pluie forte`. A dry forecast such as `Temps sec` produces no warning and clears the retained `custom/rain` app.

The warning follows Vicky's selected language:

- French: `Pluie dans 20 min.` / `Forte pluie dans 20 min.`
- German: `Regen in 20 Min.` / `Starker Regen in 20 Min.`
- English: `Rain in 20 min.` / `Heavy rain in 20 min.`

The same logic covers light rain and rain starting immediately.

### Victron display

The current Victron AWTRIX script is versioned as `victron/awtrix_victron.py`. The V8 service definition is `systemd/awtrix-victron.service`.

It connects from the Orin to the Cerbo/GX system over SSH, reads Victron D-Bus values and publishes compact AWTRIX pages independently from the News and Rain services.

Current displayed pages are:

- SmartSolar power when output is at least 100 W: `Sol 694W`
- battery state of charge: `Batt 73%`
- grid import/export: `In 69W` / `Out 350W`

The script also reads house-consumption data from `/Ac/Consumption/L1/Power`, but the current loop does not publish a `Home` page.

MQTT credentials are not stored inside the Victron source file in V8. The script shares the normal Vicky `config.py` values. Cerbo host, user and SSH-key path can be overridden with environment variables.

## Installation

`install-vicky8.sh` is the complete Debian/Ubuntu installer for a fresh system. It can prepare or install:

- required Linux packages and Python virtual environment
- Vicky 8 from GitHub
- Mosquitto MQTT
- Docker when required
- Home Assistant Container when Home Assistant is not already installed
- Vicky News, Button and Victron systemd services
- local Vicky configuration
- SSH-key preparation for Cerbo/GX access
- the V8 Home Assistant rain-warning automation

The installer intentionally does not blindly start all Vicky services before AWTRIX and Victron connectivity have been checked.

A non-destructive preview is available with:

```bash
./install-vicky8.sh --dry-run
```

A fresh Home Assistant installation still requires its one-time UI onboarding, MQTT integration setup and Météo-France location/entity setup.

## Main V8 files

- `awtrix_news_vicki.py` – main news service
- `safe_news_editor.py` – deterministic one-headline-per-message editor
- `offline_translator.py` – local FR/DE/EN headline translation
- `language_state.py` – persistent language state
- `feed_monitor.py` – RSS feed-health checks
- `news_ranker.py` – ranking and selection
- `feeds.json` – feed catalogue
- `display.py` – MQTT/AWTRIX publishing helpers
- `scripts/vicky-awtrix-button` – left/right AWTRIX button controller and shared MQTT language state
- `weather/rain_warning.yaml` – multilingual Home Assistant rain warning
- `victron/awtrix_victron.py` – Victron AWTRIX display logic
- `systemd/awtrix-news.service` – V8 news service
- `systemd/vicky-awtrix-button.service` – V8 button listener
- `systemd/awtrix-victron.service` – V8 Victron display service
- `install-vicky8.sh` – complete installer and `--dry-run` checker

## Requirements

### News service

- Linux with Python 3
- Mosquitto or another MQTT broker
- AWTRIX Light connected to the broker
- network access to configured RSS feeds
- local CTranslate2-compatible OPUS-MT translation models for the desired language pairs
- systemd for continuous operation on the reference installation

### Rain warning

- Home Assistant
- MQTT integration connected to the same broker
- Météo-France `next_rain` sensor for the configured location

### Victron display

- network access from the host to the Victron GX / Cerbo system
- passwordless SSH key access to the GX device
- working Victron D-Bus values on the GX device
- MQTT access to the AWTRIX broker

## Reference installation and validation

Vicky 8 was developed and validated on a reference installation consisting of:

- NVIDIA Jetson Orin running Vicky, Home Assistant and Mosquitto
- AWTRIX Light
- Victron GX / Cerbo system on the local network
- local translation models

The V8 validation covered the News service, RSS feeds, French/German/English language switching, retained MQTT language state, Home Assistant language discovery, multilingual rain warning and Victron `Sol`, `Batt`, `In` / `Out` display.

Hostnames, addresses, credentials, AWTRIX UIDs and Home Assistant entity IDs are installation-specific and should be treated as configuration, not portable defaults.

## Migration from V7

V8 is intentionally a cleanup rather than another compatibility layer.

Removed from the V8 runtime path are the old generative editorial chain, the unused collectors abstraction, the obsolete separate pool manager and version-specific patch helpers. V7 remains available in repository history as a rollback reference.

Vicky 8.0 is published under tag `V8.0.0` from the stable `v8` branch.

See `ROADMAP.md` for future improvements and `CHANGELOG.md` for version history.
