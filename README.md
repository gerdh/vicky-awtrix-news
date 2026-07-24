# Vicky – Local AI News for AWTRIX

Vicky is a fully local AI-powered news editor for AWTRIX. It collects RSS headlines, filters duplicates, ranks their relevance, rewrites them with a local language model, translates them into one of the supported languages (French, German or English), and publishes concise news bulletins to an AWTRIX Light via MQTT. The reference platform is an NVIDIA Jetson Orin 8 GB.

Vicky is designed for users who want complete local control over AI-generated news. No cloud AI services are required; all processing is performed locally using a compatible Large Language Model (LLM).

The working V6 installation currently runs on an NVIDIA Jetson Orin with Ubuntu Linux, Mosquitto, llama.cpp and an AWTRIX Light. News processing stays on the local network; no cloud AI service is required. No cloud subscription or AI service fees are required.

**Project status:** The cleaned V6 source files are available in this repository. V6 works on the original Jetson Orin installation. Fresh installations on other systems have not yet been fully tested.

## Features

- Reads multiple RSS news sources
- Maintains a temporary local news pool
- Filters duplicate, old and already published stories
- Ranks stories by importance
- Uses a local LLM to shorten, translate and edit headlines
- Supports French, German and English output
- Publishes rotating custom apps to AWTRIX Light over MQTT
- Clears news apps automatically after their display period
- Stores the selected output language persistently
- Runs continuously as a systemd service

The current feeds include sources from France, Germany and the United Kingdom. Feed selection and output language are configurable.

## How it works

```text
RSS feeds
    │
    ▼
Local news pool
    │
    ▼
Duplicate and history filter
    │
    ▼
Importance ranking
    │
    ▼
Local LLM
(shorten, edit, translate)
    │
    ▼
MQTT broker
    │
    ▼
AWTRIX Light
```

Vicky checks the configured feeds, adds new stories to its local pool, removes duplicates and previously displayed items, selects the most relevant stories and sends the finished bulletin to AWTRIX.

## Requirements

The current V6 setup uses:

- Linux with Python 3
- An MQTT broker, tested with Mosquitto
- An AWTRIX Light connected to the same broker
- A local llama.cpp server with an OpenAI-compatible API
- A compatible GGUF instruction model
- Network access to the configured RSS feeds
- systemd for continuous operation

### Tested platform

- NVIDIA Jetson Nano Super Orin 8 GB
- Ubuntu Linux
- llama.cpp with NVIDIA GPU acceleration
- Ministral 3B Instruct in GGUF format
- Mosquitto
- AWTRIX Light

Other Linux computers may work, but have not yet been documented or tested by this project.

## Requirements

Vicky performs all AI processing locally using a Large Language Model (LLM). A system capable of running a local LLM is therefore strongly recommended.

### Reference platform

The project is developed and tested on the following hardware:

- NVIDIA Jetson Orin 8 GB
- Ubuntu Linux
- llama.cpp with NVIDIA GPU acceleration
- Ministral 3B Instruct or other Mistral/Qwen GGUF models
- Mosquitto MQTT
- AWTRIX Light

(remaining content unchanged from current README)