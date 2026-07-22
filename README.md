# Vicky – Local AI News for AWTRIX

Vicky is a self-hosted news editor that collects headlines from RSS feeds, ranks them, translates and shortens them with a local language model, and publishes compact news bulletins to an AWTRIX Light display through MQTT.

The working V6 installation currently runs on an NVIDIA Jetson Orin with Ubuntu Linux, Mosquitto, llama.cpp and an AWTRIX Light. Processing stays on the local network; no cloud AI service is required.

> **Project status:** The cleaned V6 source files are now available in this repository. V6 works on the original Jetson Orin installation; fresh installations on other systems have not yet been tested.

## What works today

- Reading several RSS news sources
- Combining headlines in a temporary news pool
- Filtering old and duplicate stories
- Ranking stories by importance
- Translating and shortening headlines into French
- Local AI processing through a llama.cpp server
- Publishing rotating messages to AWTRIX Light over MQTT
- Automatically removing news messages after their display period
- Manual refresh from the AWTRIX middle button
- Running continuously as a systemd service

The current feeds include sources from France, Germany and the United Kingdom. Feed selection and output language are configurable in the working installation.

## How it works

1. Vicky checks the configured RSS feeds.
2. New stories are added to a local pool.
3. Duplicate and previously displayed items are discarded.
4. The most relevant stories are selected.
5. A local LLM translates and edits each headline.
6. The finished bulletin is sent to AWTRIX through MQTT.
7. The news topics are cleared automatically after the configured display time.

## Requirements

The current V6 setup uses:

- Linux with Python 3
- An MQTT broker, tested with Mosquitto
- An AWTRIX Light connected to the same MQTT broker
- A local llama.cpp server with an OpenAI-compatible API
- A compatible GGUF instruction model
- Network access to the configured RSS feeds
- systemd for continuous operation

### Tested platform

- NVIDIA Jetson Orin 8 GB
- Ubuntu Linux
- llama.cpp with NVIDIA GPU acceleration
- Ministral 3B Instruct in GGUF format
- Mosquitto
- AWTRIX Light

Other Linux computers may work, but have not yet been documented or tested by this project.

## Installation

Clone the repository and create a local Python environment:

```bash
git clone https://github.com/gerdh/vicky-awtrix-news.git
cd vicky-awtrix-news

cp config.example.py config.py
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

After configuring MQTT, AWTRIX and the local LLM, Vicky will be started with:

```bash
python3 awtrix_news_vicki.py
```


## Configuration

Private addresses and passwords must be stored only in `config.py`. Do not commit that file to GitHub.

The supplied `config.example.py` contains safe placeholders:

```python
MQTT_HOST = "127.0.0.1"
MQTT_USER = "your_mqtt_username"
MQTT_PASS = "your_mqtt_password"

BASE_TOPIC = "awtrix_xxxxxx/custom"

LLAMA_API_URL = "http://127.0.0.1:8080/v1/chat/completions"
LLAMA_MODEL = "vicky"
```

News preferences, including the French output language, are configured in `preferences.json`.

## MQTT and AWTRIX

Vicky publishes JSON messages to AWTRIX custom-app topics:

```text
<AWTRIX_PREFIX>/custom/<APP_NAME>
```

Example with placeholders:

```text
awtrix_xxxxxx/custom/vicky_news_a_1
```

Example payload:

```json
{
  "text": "Une nouvelle actualité résumée par Vicky.",
  "color": "66CCFF",
  "duration": 15
}
```

The MQTT broker address, username, password and AWTRIX prefix are installation-specific. Never copy real credentials or private network addresses into a public repository.

## Local LLM support

Vicky uses the OpenAI-compatible HTTP endpoint provided by llama.cpp:

```text
http://127.0.0.1:8080/v1/chat/completions
```

The working system uses Ministral 3B Instruct as a quantized GGUF model. The model translates incoming headlines into French and rewrites them as short, clear display messages.

A simplified llama.cpp server example is:

```bash
llama-server \
  --model /path/to/your-model.gguf \
  --host 127.0.0.1 \
  --port 8080 \
  --ctx-size 1024 \
  --n-gpu-layers 8
```

Model paths, GPU-layer counts and context size depend on the computer and available memory.

## Running as a service

The working installation runs Vicky through systemd. A cleaned service template is included under:

```text
systemd/awtrix-news.service
```

This will allow:

```bash
sudo systemctl enable --now awtrix-news.service
sudo systemctl status awtrix-news.service
journalctl -u awtrix-news.service -f
```

## Privacy and security

- News editing is performed locally.
- MQTT credentials are not included in the repository.
- Private IP addresses are represented by placeholders.
- `config.py`, logs, caches and model files must remain excluded through `.gitignore`.
- GGUF model files should not be committed to GitHub.

Before any public release, the repository history should also be checked for old credentials and private addresses.

## Project direction

AWTRIX Light is the first working output. The internal design should remain open to additional output modules, including other matrix displays and e-paper devices. These outputs are a future direction and are not implemented in the current public version.

## Version

The current development line is simply called **V6**.

No public V6 release has been created yet.

## License

A public license has not yet been selected. Until a license is added, the source remains copyrighted and no redistribution rights are granted.

## Contributing

Bug reports and carefully scoped improvements are welcome. Please do not include MQTT credentials, private addresses, logs or model files in reports or contributions.
