# Install Vicky 9 in Montpellier on Orin

This installs the Montpellier instance. It uses the local Montpellier MQTT broker and the Montpellier AWTRIX UID.

## 1. Get the release

```bash
git clone https://github.com/gerdh/vicky-awtrix-news.git
cd vicky-awtrix-news
git switch main
```

For an existing checkout:

```bash
git fetch origin
git switch main
git pull --ff-only origin main
```

## 2. Create the Python environment

```bash
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

## 3. Configure Montpellier

```bash
bash scripts/configure-site.sh montpellier
```

Enter the UID printed by the Montpellier AWTRIX configuration page. Do not reuse the Davanod UID. The AWTRIX address may remain `192.168.1.86` because it is local to Montpellier.

## 4. Install services

```bash
bash scripts/install-vicky9-services.sh
```

## 5. Test before enabling

```bash
.venv/bin/python markets/awtrix_markets.py --once
systemctl --no-pager --full status mosquitto
```

Verify that only the Montpellier AWTRIX receives EUR/USD, Gold and Brent, each twice and with a non-white color.

Then enable the required services:

```bash
sudo systemctl enable --now awtrix-news awtrix-markets awtrix-victron vicky-awtrix-button
```

## 6. Check for duplicate publishers

```bash
pgrep -af 'awtrix_markets.py|awtrix_news_vicki.py|awtrix_victron.py'
systemctl show awtrix-markets.service -p MainPID -p NRestarts -p ExecStart
```

Remove or disable old Home Assistant actions that publish normal Vicky pages through `/api/notify`.
