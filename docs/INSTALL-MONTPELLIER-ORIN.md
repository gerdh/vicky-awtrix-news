# Install Vicky 9.1.3 in Montpellier on Orin

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

Before configuration, prepare a private SSH key that Orin can use to reach the
local Montpellier Cerbo/GX. Keep its absolute path local; do not add it or the
Cerbo address to GitHub. If the key has not yet been authorized on the Cerbo,
install its public half with the actual local values:

```bash
MONTPELLIER_CERBO_KEY=/absolute/local/path/to/private_key
MONTPELLIER_CERBO_USER=enter_local_user
MONTPELLIER_CERBO_HOST=enter_local_host
ssh-copy-id -i "$MONTPELLIER_CERBO_KEY.pub" \
  "$MONTPELLIER_CERBO_USER@$MONTPELLIER_CERBO_HOST"
```

```bash
bash scripts/configure-site.sh montpellier
```

Enter the UID printed by the Montpellier AWTRIX configuration page. Do not reuse the Davanod UID. The AWTRIX address may remain `192.168.1.86` because it is local to Montpellier.

The configurator also asks for the local Montpellier Cerbo/GX host, SSH user
and absolute private-key path. It writes them only to the ignored local files
`config.py` and `.vicky-site`.

Validate the exact generated SSH path before installing services:

```bash
set -a
source ./.vicky-site
set +a
test -r "$VICKY_CERBO_SSH_KEY"
ssh -o BatchMode=yes -o ConnectTimeout=10 \
  -i "$VICKY_CERBO_SSH_KEY" \
  "$VICKY_CERBO_USER@$VICKY_CERBO_HOST" \
  'dbus -y com.victronenergy.system /Dc/Battery/Soc GetValue'
```

## 4. Install services

```bash
bash scripts/install-vicky9-services.sh
systemctl cat awtrix-victron.service
```

## 5. Test before enabling

```bash
.venv/bin/python markets/awtrix_markets.py --once
systemctl --no-pager --full status mosquitto
sudo systemctl start awtrix-victron.service
systemctl --no-pager --full status awtrix-victron.service
journalctl -u awtrix-victron.service -n 50 --no-pager
```

Verify that only the Montpellier AWTRIX receives EUR/USD, Gold, Brent and NVIDIA, each twice and with a non-white color.

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
