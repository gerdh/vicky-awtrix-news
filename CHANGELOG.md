# Changelog

All notable changes to Vicky are documented here.

## [8.0.0-dev] - 2026-08-28

### Added
- New `v8-clean` development line for a clean Vicky 8 architecture.
- Versioned AWTRIX button controller in `scripts/vicky-awtrix-button`.
- Shared retained MQTT language state for French, German and English output.
- Home Assistant MQTT Discovery for the selected Vicky language.
- Multilingual Billiat rain warning in `weather/rain_warning.yaml` using the Météo-France `next_rain` sensor.
- Figaro added to the active feed catalogue used by the running Orin installation.
- Vicky 8 documentation covering News, Buttons, Rain and the independent Victron display stack.

### Changed
- News editing now uses the deterministic `safe_news_editor` path directly.
- Offline CTranslate2/OPUS-MT translation is the active multilingual translation layer.
- Button-triggered news refresh no longer changes the language inside the news process itself.
- Right AWTRIX button owns the language cycle `FR → DE → EN → FR`.
- Left AWTRIX button remains the manual news refresh action.
- Middle AWTRIX button is reserved for AWTRIX and is not handled by Vicky.
- Rain warnings now follow the same selected output language as the news bulletins.
- Victron labels remain intentionally language-neutral (`Sol`, `Batt`, `In`, `Out`, `Home`).

### Removed
- V7.6 `editor_v76.py` generative editorial path from the V8 branch.
- Old `news_editor_v5.py` path from the V8 branch.
- Parallel historical `src/` source tree from the V8 branch.
- Legacy llama.cpp `vicki.py` client and LLM configuration from the V8 runtime configuration.

### Migration status
- The running `/home/gerd/vicky7` installation on the Orin has not yet been switched to V8.
- The production Victron script and `awtrix-victron.service` still need to be captured from the live Orin and committed after verification.
- V7/main remains the rollback reference while `v8-clean` is completed and tested.

## [7.6.0] - 2026-07-28

### Added
- Multilingual V7.6 editorial engine in `editor_v76.py`.
- Language-neutral editorial prompting for French, German and English output.
- Safer validation of complete journalistic units and source selections.
- Source-code prefixes on AWTRIX bulletin messages.
- Feed-health reporting with persistent status in `cache/feed_health.json`.

### Changed
- Bulletin creation now uses the V7.6 editor with safe fallback behavior.
- Button-triggered bulletins use the persistent language state.
- Feed failures are isolated so one broken RSS source does not stop the bulletin.
- News-title cleanup removes common live/breaking prefixes that waste AWTRIX space.
- Public repository documentation now identifies V7.6 as the current version.

## [7.5.0] - 2026-07-28

### Added
- Offline translation support and cleaned news titles.

### Changed
- Improved factual fidelity and title normalization.

## [7.4.0] - 2026-07-26

### Added
- Automatic feed-health reporting during normal news retrieval.
- Deterministic offline translation from German and English to French with CTranslate2 and OPUS-MT.
- Safe one-headline-per-message editor with automatic fallback to the original title.
- Persistent health report in `cache/feed_health.json`.
- Logging of healthy and failed RSS sources.

### Changed
- Empty or failed feeds are skipped automatically.
- A failing feed no longer blocks the remaining news sources.

## [7.3.0] - 2026-07

### Added
- Broader international feed catalogue and configurable source metadata.
- Source and topic ranking groundwork.
- Improved cross-source duplicate handling and pool management.

## [7.2.0] - 2026-07

### Added
- Persistent replay cache for the most recently selected bulletin messages.
- Persistent language selection for French, German and English output.
- Improved bulletin scheduling and automatic clearing of AWTRIX news topics.
- Better ranking and editorial processing before publication.

### Changed
- News selection moved from simple per-feed display toward a shared news pool.
- Button actions became independent from the normal polling interval.
- Logging was expanded to show feed counts, pool additions and bulletin timing.

## [7.1.0] - 2026-07

### Added
- Stable foundation based on the V6 bulletin service.
- Button-triggered forced refresh through a request file and service handling.
- Local LLM editing and translation through a llama.cpp OpenAI-compatible endpoint.
- MQTT publishing to retained AWTRIX custom apps.
- Automatic removal of displayed news after the configured visibility period.

### Changed
- Bulletin generation and button handling were separated more clearly.
- Service operation and diagnostics were improved for continuous use on the Jetson Orin.

## [6.0.0] - 2026-07

- Introduced the forced-refresh bulletin workflow.
- Added the replay mechanism for button-triggered news display.
- Consolidated the continuously running AWTRIX news service.

## Earlier versions

Earlier releases established RSS collection, MQTT publishing, French translation, bulletin rotation, duplicate filtering and local LLM integration.
