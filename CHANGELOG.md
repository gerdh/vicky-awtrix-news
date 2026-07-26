# Changelog

All notable changes to Vicky are documented here.

## [7.3.0] - Unreleased

### Planned
- Expand the news source catalogue beyond the five currently active feeds.
- Add broader international coverage for world, France, Germany, business, technology, AI, science, energy, Bitcoin and Tesla.
- Introduce source weights and topic weights.
- Limit the active news pool and remove expired entries automatically.
- Improve cross-source duplicate detection so the same event is shown only once.
- Move feed definitions toward a separate configuration file.
- Add feed health and pool statistics to the logs.

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

### Known limitations
- The pool file can retain too many old entries.
- Duplicate detection across differently worded sources is still limited.
- Only a small subset of available feeds may be active in the running configuration.

## [7.1.0] - 2026-07

### Added
- Stable foundation based on the V6 bulletin service.
- Middle-button forced refresh through a request file and systemd restart.
- Local LLM editing and translation through a llama.cpp OpenAI-compatible endpoint.
- MQTT publishing to retained AWTRIX custom apps.
- Automatic removal of displayed news after the configured visibility period.

### Changed
- Bulletin generation and button handling were separated more clearly.
- Service operation and diagnostics were improved for continuous use on the Jetson Orin.

### Known limitations
- Feed configuration remains embedded in Python code.
- Pool lifetime and maximum size are not yet enforced consistently.
- Installation outside the original system is not yet fully tested.

## [6.0.0] - 2026-07

- Introduced the forced-refresh bulletin workflow.
- Added the replay mechanism for button-triggered news display.
- Consolidated the continuously running AWTRIX news service.

## Earlier versions

Earlier releases established RSS collection, MQTT publishing, French translation, bulletin rotation, duplicate filtering and local LLM integration. Their exact historical boundaries will be refined as older source snapshots are reviewed.
