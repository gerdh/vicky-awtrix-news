# Vicky 8 – AWTRIX information stack

Vicky 8 is the cleaned-up successor to the V7 family. It brings the AWTRIX functions used on the reference Jetson Orin installation into one documented project while keeping the individual services independent.

**Current development branch: `v8-clean`**

Vicky 8 covers three functional areas:

- multilingual news bulletins
- local rain warnings from Home Assistant / Météo-France
- the Victron energy display stack

The news and rain-warning components share one persistent output language: French, German or English. The compact Victron labels (`Sol`, `Batt`, `In`, `Out`, `Home`) stay language-neutral because they are intentionally short and widely understandable.

## V8 design goals

- one clear Vicky generation instead of accumulated V5/V6/V7 compatibility paths
- independent services so a news, weather or Victron failure does not take down the other functions
- deterministic headline translation instead of generative rewriting
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

The V8 button controller is versioned as `scripts/vicky-awtrix-button`.

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

The reference Orin installation also runs an independent `awtrix-victron.service` which reads the Victron system and displays compact AWTRIX pages for solar power, battery state of charge, grid import/export and house consumption.

Typical labels are:

- `Sol 694W`
- `Batt 73%`
- `In 69W` / `Out 350W`
- `Home 2515W`

The Victron runtime is intentionally independent of the news and weather services. Its current production script and service definition are being migrated into the V8 repository from the running Orin installation; V8 documentation treats it as part of the stack, but the exact production files should only be committed after comparison with the live system.

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

Victron files will be added after the live `awtrix_victron.py` and `awtrix-victron.service` have been captured and verified.

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

- network access from the Orin to the Victron GX / Cerbo system
- working Victron D-Bus values on the GX device
- MQTT access to the AWTRIX broker

## Reference installation

The project is developed around the original installation consisting of:

- NVIDIA Jetson Orin running Vicky, Home Assistant and Mosquitto
- AWTRIX Light `awtrix_3e6014`
- Victron GX / Cerbo system on the local network
- local translation models under the Orin filesystem

Hostnames, addresses, credentials, AWTRIX UIDs and Home Assistant entity IDs are installation-specific and should be treated as configuration, not portable defaults.

## Migration from V7

V8 is intentionally a cleanup rather than another compatibility layer.

Removed from the V8 runtime path are the old generative editorial chain and parallel historical source trees, including the V7.6 `editor_v76.py` path. V7 remains available on the previous branch/main history as a rollback reference while `v8-clean` is completed and tested.

The running Orin installation should not be switched to V8 until the News, Button, Rain and Victron production files have all been captured, reviewed and tested together.

## Version history

See `CHANGELOG.md` for the V7 history and the V8 cleanup work.
