#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID:-$(id -u)} -eq 0 ]]; then
  echo "Run as the normal Vicky user; sudo is used only to install systemd units."
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$REPO_ROOT/.venv/bin/python"
RUN_USER="$(id -un)"

[[ -f "$REPO_ROOT/config.py" ]] || {
  echo "Missing config.py. Run: bash scripts/configure-site.sh montpellier|davanod"
  exit 1
}
[[ -x "$PYTHON" ]] || {
  echo "Missing Python environment. Run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
}

install_unit() {
  local name="$1" command="$2" description="$3" temp
  temp="$(mktemp)"
  cat >"$temp" <<EOF
[Unit]
Description=$description
After=network-online.target mosquitto.service
Wants=network-online.target

[Service]
Type=simple
User=$RUN_USER
WorkingDirectory=$REPO_ROOT
ExecStart=$command
Restart=on-failure
RestartSec=15
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF
  sudo install -m 0644 "$temp" "/etc/systemd/system/$name"
  rm -f "$temp"
}

install_unit awtrix-news.service "$PYTHON $REPO_ROOT/awtrix_news_vicki.py" "Vicky 9 AWTRIX News"
install_unit awtrix-markets.service "$PYTHON $REPO_ROOT/markets/awtrix_markets.py" "Vicky 9 AWTRIX Markets"
install_unit awtrix-victron.service "$PYTHON $REPO_ROOT/victron/awtrix_victron.py" "Vicky 9 AWTRIX Victron"
install_unit vicky-awtrix-button.service "$REPO_ROOT/scripts/vicky-awtrix-button" "Vicky 9 AWTRIX Button Listener"

sudo systemctl daemon-reload
echo "Vicky 9 units installed but not started."
echo "Test first:"
echo "  $PYTHON $REPO_ROOT/markets/awtrix_markets.py --once"
echo "Then enable locally required services, for example:"
echo "  sudo systemctl enable --now awtrix-news awtrix-markets awtrix-victron vicky-awtrix-button"
