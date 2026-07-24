# Vicky – Local AI News for AWTRIX

Vicky is a self-hosted news editor that collects headlines from RSS feeds, filters and ranks them, rewrites them with a local language model, and publishes compact news bulletins to an AWTRIX Light display through MQTT.

The working V6 installation currently runs on an NVIDIA Jetson Orin with Ubuntu Linux, Mosquitto, llama.cpp and an AWTRIX Light. News processing stays on the local network; no cloud AI service is required.

> **Project status:** The cleaned V6 source files are available in this repository. V6 works on the original Jetson Orin installation. Fresh installations on other systems have not yet been fully tested.

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

After configuring MQTT, AWTRIX and the local LLM, start Vicky with:

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

News preferences and feed settings are stored in the JSON configuration files included with the project.

## Language selection

The working V6 installation uses the AWTRIX middle button to cycle through the available output languages:

```text
FRANCAIS → DEUTSCH → ENGLISH → FRANCAIS
```

Each button press selects the next language and briefly displays its name on AWTRIX. The choice is stored in:

```text
cache/current_language.txt
```

The selected language is used for the **next newly generated bulletin**. Messages that were already generated remain unchanged.

This avoids unnecessary LLM processing when the language is changed and makes the selection persistent across service restarts.

> The public repository may require installation-specific adaptation of the MQTT button topic and helper service. AWTRIX device prefixes and credentials must remain configurable and must never be hard-coded with private values.

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
  "text": "A short news message prepared by Vicky.",
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

The working system uses Ministral 3B Instruct as a quantized GGUF model. Other instruction-tuned models such as Qwen or Mistral may work when they fit the available memory and follow the requested output format reliably.

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

Typical service commands are:

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
- Repository history should be checked for old credentials before public releases.

## Troubleshooting

### No messages appear on AWTRIX

Check the MQTT connection, AWTRIX prefix and service log:

```bash
journalctl -u awtrix-news.service -n 100 --no-pager
```

Subscribe temporarily to the AWTRIX topic tree to verify published messages:

```bash
mosquitto_sub \
  -h <MQTT_HOST> \
  -u <MQTT_USER> \
  -P <MQTT_PASSWORD> \
  -t '<AWTRIX_PREFIX>/#' \
  -v
```

### The selected language does not affect old messages

This is expected. Language changes apply only to newly generated bulletins. Existing messages are not translated again.

### The LLM is slow or runs out of memory

Use a smaller quantized GGUF model, reduce the context size or lower the number of GPU layers.

## Project direction

AWTRIX Light is the first working output. Future versions may add:

- Additional configurable languages
- Improved topic diversity and regional balance
- Easier setup of the AWTRIX button service
- Additional matrix-display or e-paper output modules
- More installation examples for non-Jetson Linux systems

These items are project directions and are not all implemented in the current public version.

## Version

The current development line is called **V6**.

 V6 release has been created.

## License

Vicky is released under the [MIT License](LICENSE).

## Contributing

Bug reports and carefully scoped improvements are welcome. Do not include MQTT credentials, private addresses, logs containing secrets or model files in reports or contributions.
