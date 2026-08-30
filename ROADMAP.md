# Vicky 8 Roadmap

Vicky 8 consolidates the actively used AWTRIX functions on the Jetson Orin into one clean, documented project while keeping News, Weather and Victron as independent services.

## V8.0 — Released production baseline

Status: **released and validated** as `V8.0.0` from the stable `v8` branch.

Included:

- deterministic multilingual news pipeline
- local CTranslate2 / OPUS-MT translation for FR, DE and EN
- persistent shared language state
- left AWTRIX button for news refresh
- right AWTRIX button for `FR → DE → EN → FR`
- middle AWTRIX button left to AWTRIX itself
- multilingual Météo-France rain warning through Home Assistant
- Victron SmartSolar, battery SoC and grid import/export AWTRIX pages
- version-controlled systemd units for News, Buttons and Victron
- active feed catalogue synchronized with the reference installation
- no generative LLM editorial dependency in the V8 runtime
- complete Debian/Ubuntu installer with Mosquitto and Home Assistant preparation
- non-destructive installer `--dry-run` mode

## Why V8 does not use a generative news AI

Older Vicky generations experimented with a local llama.cpp editorial model. V8 deliberately removes that generative stage.

The goal is not to avoid machine learning entirely: V8 still uses local neural OPUS-MT translation through CTranslate2. The difference is that translation is a constrained task, while free-form editorial generation can alter, combine or embellish source information.

For an always-on news display, V8 prioritizes:

- factual fidelity to the original headline
- deterministic, testable behavior
- lower resource use and simpler maintenance
- clearer failure modes
- safe fallback to the original headline when translation cannot be completed

Therefore V8 should be described as **local AI-assisted translation with deterministic news processing**, not as a fully AI-based news editor.

## V8.0 validation completed

The reference deployment has validated:

- RSS/feed retrieval and bulletin generation
- French, German and English language cycling
- right-button language selection and left-button refresh behavior
- retained MQTT language state
- Home Assistant MQTT Discovery language sensor
- multilingual Home Assistant rain warning
- Victron AWTRIX `Sol`, `Batt`, `In` and `Out` pages
- direct Victron script startup without manual `PYTHONPATH`
- installer dry-run support

## Post-8.0 improvements

Only after the clean V8 baseline is stable:

- improve cross-source duplicate detection if needed
- refine feed ranking and source diversity
- improve weak/generic feed-title filtering where needed
- add explicit health/status reporting for the three independent Vicky services
- further harden the fresh-system installer and automated validation
- consider additional AWTRIX information tiles only when they do not complicate the core stack

Historical V7 release notes remain under `docs/releases/` and in `CHANGELOG.md` for reference; they are not part of the V8 runtime architecture.
