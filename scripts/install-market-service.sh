#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID:-$(id -u)} -eq 0 ]]; then
  echo "Bitte als normaler Benutzer starten; sudo wird nur für systemd verwendet."
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$REPO_ROOT/.venv/bin/python"
SERVICE_NAME="awtrix-markets.service"
SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME"
RUN_USER="$(id -un)"

if [[ ! -x "$PYTHON" ]]; then
  echo "Python-Umgebung fehlt: $PYTHON"
  exit 1
fi
if [[ ! -f "$REPO_ROOT/config.py" ]]; then
  echo "Vicky-Konfiguration fehlt: $REPO_ROOT/config.py"
  exit 1
fi

echo "Marktdaten einmalig abrufen und an AWTRIX senden ..."
"$PYTHON" "$REPO_ROOT/markets/awtrix_markets.py" --once

TMP_SERVICE="$(mktemp)"
trap 'rm -f "$TMP_SERVICE"' EXIT
cat >"$TMP_SERVICE" <<EOF
[Unit]
Description=Vicky V8.3 AWTRIX Market Tiles
After=network-online.target mosquitto.service
Wants=network-online.target

[Service]
Type=simple
User=$RUN_USER
WorkingDirectory=$REPO_ROOT
ExecStart=$PYTHON $REPO_ROOT/markets/awtrix_markets.py
Restart=always
RestartSec=15
Environment=PYTHONUNBUFFERED=1
Environment=VICKY_MARKETS=EURUSD,GOLD,BRENT
Environment=VICKY_MARKET_POLL_SECONDS=300

[Install]
WantedBy=multi-user.target
EOF

sudo install -m 0644 "$TMP_SERVICE" "$SERVICE_PATH"
sudo systemctl daemon-reload
sudo systemctl enable --now "$SERVICE_NAME"
sudo systemctl --no-pager --full status "$SERVICE_NAME"
