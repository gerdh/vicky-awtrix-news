# Install Vicky 9.1.2 in Davanod on Moon

This installs the Davanod instance on Raspberry Pi 5 Moon. It uses the local Davanod MQTT broker and the Davanod AWTRIX UID.

## 1. Get the release

```bash
git clone https://github.com/gerdh/vicky-awtrix-news.git
cd vicky-awtrix-news
git switch main
```

For an existing checkout such as `/home/gerd/vicky83`:

```bash
cd /home/gerd/vicky83
git fetch origin
git switch main
git pull --ff-only origin main
```

## 2. Create or update the Python environment

```bash
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

## 3. Configure Davanod

```bash
bash scripts/configure-site.sh davanod
```

Enter the UID printed by the Davanod AWTRIX configuration page. Do not reuse the Montpellier UID. The AWTRIX address may also be `192.168.1.86` because the Davanod LAN is separate.

## 4. Install services

```bash
bash scripts/install-vicky9-services.sh
```

## 5. Test before enabling

```bash
.venv/bin/python markets/awtrix_markets.py --once
systemctl --no-pager --full status mosquitto
```

Confirm exactly these local retained apps:

```text
<davanod-awtrix-uid>/custom/market_eurusd
<davanod-awtrix-uid>/custom/market_gold
<davanod-awtrix-uid>/custom/market_brent
<davanod-awtrix-uid>/custom/market_nvidia
```

Then enable the required services:

```bash
sudo systemctl enable --now awtrix-news awtrix-markets awtrix-victron vicky-awtrix-button
```

Verify the button contract:

- right button: cycle Vicky news language `FR → DE → EN → FR` and refresh immediately
- left button: refresh Vicky news without changing language

The button service reads `AWTRIX_UID` from the local `config.py`. For a local
configuration created before Vicky 9.1, it safely derives the UID from
`BASE_TOPIC`; no Montpellier value is copied to Davanod.

Check the listener after installation:

```bash
systemctl --no-pager --full status vicky-awtrix-button
journalctl -u vicky-awtrix-button -n 30 --no-pager
```

Button-triggered bulletins prefer distinct sources before using a second item
from any source. This does not impose a German/French/English quota.

## 6. Optional local importance sorting

Moon can run a local OpenAI-compatible model that may only reorder finished
messages. It never supplies display text. The feature is opt-in and the server
must bind to loopback, not the LAN.

After installing a local `llama-server` binary and GGUF model, follow
[the local AI sorter guide](LOCAL-AI-SORTER.md). The tested Moon helper command
is:

```bash
bash scripts/install-local-ai-sorter-service.sh
```

Do not reuse Montpellier model paths or service configuration.

## 7. Check for duplicate publishers

```bash
pgrep -af 'awtrix_markets.py|awtrix_news_vicki.py|awtrix_victron.py'
systemctl show awtrix-markets.service -p MainPID -p NRestarts -p ExecStart
```

A duplicate shown in Davanod must be diagnosed on Moon/Home Assistant in Davanod; the isolated Montpellier system cannot publish to this broker.
