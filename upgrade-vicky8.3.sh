#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID:-$(id -u)} -eq 0 ]]; then
  echo "Bitte als normaler Benutzer starten; sudo wird nur für systemd verwendet."
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION="$(tr -d '[:space:]' < "$REPO_ROOT/VERSION")"

if [[ "$VERSION" != "8.3.0" ]]; then
  echo "FEHLER: Erwartet wurde Vicky 8.3.0, gefunden wurde: $VERSION"
  exit 1
fi

if [[ ! -f "$REPO_ROOT/config.py" ]]; then
  echo "FEHLER: Lokale MQTT-Konfiguration fehlt: $REPO_ROOT/config.py"
  exit 1
fi

if [[ ! -x "$REPO_ROOT/.venv/bin/python" ]]; then
  echo "FEHLER: Python-Umgebung fehlt: $REPO_ROOT/.venv/bin/python"
  exit 1
fi

echo "Vicky 8.3 Marktdienst installieren ..."
bash "$REPO_ROOT/scripts/install-market-service.sh"

echo
echo "Vicky 8.3 Upgrade abgeschlossen."
echo "Status prüfen:"
echo "  systemctl --no-pager --full status awtrix-markets.service"
