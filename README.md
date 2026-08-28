# Vicky – Local AI News for AWTRIX

Vicky is a fully local AI-powered news editor for AWTRIX Light. It collects RSS headlines, filters and ranks them, edits or translates them locally, and publishes concise multilingual news bulletins over MQTT.

**Current public version: V7.6**

The reference installation runs on an NVIDIA Jetson Orin with Ubuntu Linux, Mosquitto, llama.cpp and an AWTRIX Light. News processing and AI editing stay local; no cloud AI service is required.

## V7 highlights

- Multilingual output in French, German and English
- Persistent output-language selection
- Shared news pool with ranking and duplicate/history filtering
- Safe multilingual editorial engine with fallback to source headlines
- Automatic RSS feed-health monitoring and failure isolation
- Configurable feed catalogue
- Source labels on AWTRIX messages
- Button-triggered bulletin generation
- Persistent replay/bulletin state
- Automatic clearing of AWTRIX news apps
- Continuous systemd service operation

## How it works

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
Vicky V7.6 editorial engine
(local LLM + safe fallback)
    │
    ▼
MQTT
    │
    ▼
AWTRIX Light
```

Vicky periodically reads the configured feeds, skips broken sources, adds fresh stories to its local pool, selects the most relevant items and publishes the finished bulletin to AWTRIX.

## Requirements

- Linux with Python 3
- Mosquitto or another MQTT broker
- AWTRIX Light connected to the broker
- A local llama.cpp server with an OpenAI-compatible API
- A compatible GGUF instruction model
- Network access to the configured RSS feeds
- systemd for continuous operation

## Reference platform

- NVIDIA Jetson Orin 8 GB
- Ubuntu Linux
- llama.cpp with NVIDIA GPU acceleration
- Ministral 3B Instruct or compatible Mistral/Qwen GGUF model
- Mosquitto MQTT
- AWTRIX Light

## Main V7 files

- `awtrix_news_vicki.py` – main news service
- `editor_v76.py` – V7.6 multilingual editorial engine
- `language_state.py` – persistent FR/DE/EN language state
- `feed_monitor.py` – RSS health monitoring
- `feeds.json` – feed catalogue
- `news_ranker.py` – ranking and selection
- `safe_news_editor.py` – safe editorial fallback

## Version history

V6 established the stable bulletin workflow. V7 added the shared news engine, persistent multilingual operation, safer editorial processing, feed resilience and the V7.6 multilingual editor.

See `CHANGELOG.md` for details.

## Status

V7.6 is the current public source version in this repository. It is developed around the original Jetson Orin installation; fresh installations on other systems may require adaptation and have not been exhaustively tested.
