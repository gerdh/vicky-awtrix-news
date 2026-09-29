# Install Vicky 9 in Davanod on Moon

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
```

Then enable the required services:

```bash
sudo systemctl enable --now awtrix-news awtrix-markets awtrix-victron vicky-awtrix-button
```

## 6. Check for duplicate publishers

```bash
pgrep -af 'awtrix_markets.py|awtrix_news_vicki.py|awtrix_victron.py'
systemctl show awtrix-markets.service -p MainPID -p NRestarts -p ExecStart
```

A duplicate shown in Davanod must be diagnosed on Moon/Home Assistant in Davanod; the isolated Montpellier system cannot publish to this broker.
