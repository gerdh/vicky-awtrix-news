# Vicky 8 Roadmap

Vicky 8 consolidates the actively used AWTRIX functions on the Jetson Orin into one clean, documented project while keeping News, Weather and Victron as independent services.

## V8.0 — Clean production baseline

Status: implementation captured in `v8-clean`; parallel Orin deployment and validation still pending.

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
- active feed catalogue synchronized with the Orin
- no generative LLM editorial dependency in the V8 runtime

## Before V8 becomes the live installation

- install the branch in parallel under `/home/gerd/vicky8`
- create the V8 virtual environment and install requirements
- copy local `config.py` without committing credentials
- preserve or intentionally migrate the selected language and news cache state
- syntax/import-test the News and Victron Python programs
- test the button listener without stopping V7
- validate FR/DE/EN news output
- validate FR/DE/EN rain warnings
- validate SmartSolar, battery and grid AWTRIX pages
- switch systemd services only after the parallel tests succeed
- keep V7 available as rollback until V8 has run stably

## Post-8.0 improvements

Only after the clean V8 baseline is stable:

- improve cross-source duplicate detection if needed
- refine feed ranking and source diversity
- add explicit health/status reporting for the three independent Vicky services
- consider additional AWTRIX information tiles only when they do not complicate the core stack

Historical V7 release notes remain under `docs/releases/` and in `CHANGELOG.md` for reference; they are not part of the V8 runtime architecture.
