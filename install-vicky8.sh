#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/gerdh/vicky-awtrix-news.git"
BRANCH="v8.1"
DRY_RUN=false

if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=true
elif [[ $# -gt 0 ]]; then
  echo "Verwendung: $0 [--dry-run]"
  exit 2
fi

if [[ ${EUID:-$(id -u)} -eq 0 ]]; then
  echo "Bitte als normaler Benutzer starten, nicht direkt als root. sudo wird bei Bedarf verwendet."
  exit 1
fi

INSTALL_USER="${SUDO_USER:-$USER}"
USER_HOME="$(getent passwd "$INSTALL_USER" | cut -d: -f6)"
INSTALL_DIR="${VICKY_INSTALL_DIR:-$USER_HOME/vicky8}"
DEFAULT_HA_CONFIG="$USER_HOME/homeassistant/config"
ARCH="$(uname -m)"

say() { printf '\n==> %s\n' "$*"; }

read_default() {
  local prompt="$1" default="$2" var
  read -r -p "$prompt [$default]: " var
  printf '%s' "${var:-$default}"
}

append_automation_if_missing() {
  local automation_id="$1"
  local source_file="$2"
  local auto_file="$3"

  if grep -q "id: ${automation_id}$" "$auto_file" 2>/dev/null || grep -q "id: '${automation_id}'$" "$auto_file" 2>/dev/null; then
    echo "Automation $automation_id ist bereits vorhanden; keine Überschreibung."
  else
    printf '\n' >> "$auto_file"
    cat "$source_file" >> "$auto_file"
    echo "Automation $automation_id ergänzt."
  fi
}

if ! command -v apt-get >/dev/null 2>&1; then
  echo "Dieser Installer unterstützt Debian/Ubuntu/Raspberry Pi OS mit apt."
  exit 1
fi

if $DRY_RUN; then
  say "Vicky 8.1 DRY-RUN"
  echo "Es werden KEINE Dateien, Pakete, Container oder Dienste verändert."
  echo "Benutzer     : $INSTALL_USER"
  echo "Architektur  : $ARCH"
  echo "Git-Branch   : $BRANCH"
  echo "Ziel         : $INSTALL_DIR"
  echo
  printf '%-28s %s\n' "apt-get" "$(command -v apt-get >/dev/null 2>&1 && echo vorhanden || echo FEHLT)"
  printf '%-28s %s\n' "git" "$(command -v git >/dev/null 2>&1 && echo vorhanden || echo wird installiert)"
  printf '%-28s %s\n' "python3" "$(command -v python3 >/dev/null 2>&1 && echo vorhanden || echo wird installiert)"
  printf '%-28s %s\n' "mosquitto_pub" "$(command -v mosquitto_pub >/dev/null 2>&1 && echo vorhanden || echo wird installiert)"
  printf '%-28s %s\n' "docker" "$(command -v docker >/dev/null 2>&1 && echo vorhanden || echo wird installiert)"

  if [[ "$ARCH" == "aarch64" || "$ARCH" == "arm64" ]]; then
    echo "Raspberry Pi / ARM64        geeignet"
  else
    echo "Architektur                 $ARCH (Installer bleibt nutzbar, Raspberry Pi empfohlen: 64-bit)"
  fi

  if [[ -d "$INSTALL_DIR/.git" ]]; then
    echo "Vicky 8.1 Repository        vorhanden -> würde auf $BRANCH aktualisiert"
  elif [[ -e "$INSTALL_DIR" ]]; then
    echo "Vicky 8.1 Ziel              existiert, aber kein Git-Repo -> echte Installation würde ABBRECHEN"
  else
    echo "Vicky 8.1 Repository        fehlt -> würde aus $BRANCH geklont"
  fi

  if command -v docker >/dev/null 2>&1 && sudo docker inspect homeassistant >/dev/null 2>&1; then
    HA_EXISTING="$(sudo docker inspect homeassistant --format '{{range .Mounts}}{{if eq .Destination "/config"}}{{.Source}}{{end}}{{end}}' 2>/dev/null || true)"
    echo "Home Assistant              vorhanden${HA_EXISTING:+ -> $HA_EXISTING}"
  else
    echo "Home Assistant              fehlt -> Docker/HA-Container würde eingerichtet"
  fi

  if systemctl list-unit-files mosquitto.service >/dev/null 2>&1; then
    echo "Mosquitto                   vorhanden -> würde konfiguriert"
  else
    echo "Mosquitto                   fehlt -> würde installiert"
  fi

  for unit in awtrix-news.service awtrix-victron.service vicky-awtrix-button.service; do
    if [[ -e "/etc/systemd/system/$unit" ]]; then
      echo "$unit vorhanden -> würde ersetzt"
    else
      echo "$unit fehlt -> würde angelegt"
    fi
  done

  echo
  echo "Bei echter Installation würde der Installer anschließend:"
  echo "  1. Systempakete installieren/aktualisieren"
  echo "  2. Mosquitto mit Benutzer/Passwort konfigurieren"
  echo "  3. Docker + Home Assistant installieren, falls nötig"
  echo "  4. Vicky 8.1 aus Branch $BRANCH klonen/aktualisieren"
  echo "  5. Python-venv und Vicky-Abhängigkeiten installieren"
  echo "  6. AWTRIX/MQTT config.py erzeugen"
  echo "  7. SSH-Key für Cerbo/GX vorbereiten"
  echo "  8. News-, Victron- und Button-systemd-Dienste anlegen"
  echo "  9. Home Assistant: Regen, USD/EUR, Gold und Enphase→Victron ergänzen"
  echo " 10. V8.1 AI-Priorisierung konfigurierbar machen"
  echo " 11. Python- und Home-Assistant-Konfiguration prüfen"
  echo
  echo "DRY-RUN beendet: keine Änderungen vorgenommen."
  exit 0
fi

say "Vicky 8.1 Komplett-Installer"
echo "Benutzer     : $INSTALL_USER"
echo "Architektur  : $ARCH"
echo "Git-Branch   : $BRANCH"
echo "Ziel         : $INSTALL_DIR"

AWTRIX_UID="$(read_default 'AWTRIX UID, z.B. awtrix_3e6014' 'awtrix_3e6014')"
MQTT_HOST="$(read_default 'MQTT Host für Vicky' '127.0.0.1')"
MQTT_USER="$(read_default 'MQTT Benutzer' 'vicky')"
read -r -s -p "MQTT Passwort: " MQTT_PASS
echo
if [[ -z "$MQTT_PASS" ]]; then
  echo "MQTT Passwort darf nicht leer sein."
  exit 1
fi

CERBO_HOST="$(read_default 'Cerbo/GX IP oder Hostname' '192.168.1.63')"
CERBO_USER="$(read_default 'Cerbo/GX SSH Benutzer' 'root')"
SSH_KEY="$(read_default 'SSH Key für Cerbo/GX' "$USER_HOME/.ssh/id_ed25519")"
ENPHASE_POWER_ENTITY="$(read_default 'Home-Assistant Entity-ID für aktuelle Enphase-Produktion' 'sensor.envoy_122238059161_aktuelle_stromproduktion')"

read -r -p "Lokalen Mosquitto-Broker installieren/konfigurieren? [J/n]: " INSTALL_MQTT
INSTALL_MQTT="${INSTALL_MQTT:-J}"

read -r -p "V8.1 AI-Priorisierung aktivieren? Nur wenn ein lokaler OpenAI-kompatibler AI-Server läuft. [j/N]: " ENABLE_AI_SORT
ENABLE_AI_SORT="${ENABLE_AI_SORT:-N}"
if [[ "$ENABLE_AI_SORT" =~ ^[JjYy]$ ]]; then
  AI_SORT="1"
  AI_URL="$(read_default 'AI API URL' 'http://127.0.0.1:8080/v1/chat/completions')"
  AI_MODEL="$(read_default 'AI Modellname' 'local-model')"
else
  AI_SORT="0"
  AI_URL="http://127.0.0.1:8080/v1/chat/completions"
  AI_MODEL="local-model"
fi

say "Systempakete installieren"
sudo apt-get update
sudo apt-get install -y \
  git python3 python3-venv python3-pip openssh-client \
  mosquitto-clients curl ca-certificates

if [[ "$INSTALL_MQTT" =~ ^[JjYy]$ ]]; then
  sudo apt-get install -y mosquitto
  say "Mosquitto mit Passwortschutz konfigurieren"
  sudo install -d -m 0755 /etc/mosquitto/conf.d
  sudo touch /etc/mosquitto/passwd
  sudo chmod 0600 /etc/mosquitto/passwd
  sudo mosquitto_passwd -b /etc/mosquitto/passwd "$MQTT_USER" "$MQTT_PASS"
  sudo tee /etc/mosquitto/conf.d/vicky8.conf >/dev/null <<EOF
listener 1883 0.0.0.0
allow_anonymous false
password_file /etc/mosquitto/passwd
EOF
  sudo systemctl enable --now mosquitto
fi

say "Home Assistant prüfen"
if ! command -v docker >/dev/null 2>&1; then
  say "Docker fehlt - Docker und Home Assistant werden installiert"
  sudo apt-get install -y docker.io
  sudo systemctl enable --now docker
fi

HA_CONFIG_DIR=""
if sudo docker inspect homeassistant >/dev/null 2>&1; then
  HA_CONFIG_DIR="$(sudo docker inspect homeassistant --format '{{range .Mounts}}{{if eq .Destination "/config"}}{{.Source}}{{end}}{{end}}')"
  if [[ -z "$HA_CONFIG_DIR" ]]; then
    echo "WARNUNG: Home-Assistant-Container gefunden, aber /config-Mount nicht erkannt."
    HA_CONFIG_DIR="$(read_default 'Home-Assistant config-Ordner' "$DEFAULT_HA_CONFIG")"
  else
    echo "Vorhandener Home Assistant gefunden: $HA_CONFIG_DIR"
  fi
else
  HA_CONFIG_DIR="$(read_default 'Neuer Home-Assistant config-Ordner' "$DEFAULT_HA_CONFIG")"
  say "Home Assistant Container installieren"
  mkdir -p "$HA_CONFIG_DIR"
  chown -R "$INSTALL_USER":"$(id -gn "$INSTALL_USER")" "$(dirname "$HA_CONFIG_DIR")"

  if [[ ! -f "$HA_CONFIG_DIR/configuration.yaml" ]]; then
    cat > "$HA_CONFIG_DIR/configuration.yaml" <<'EOF'
default_config:

automation: !include automations.yaml
script: !include scripts.yaml
scene: !include scenes.yaml
EOF
  fi
  touch "$HA_CONFIG_DIR/automations.yaml" "$HA_CONFIG_DIR/scripts.yaml" "$HA_CONFIG_DIR/scenes.yaml"

  sudo docker pull ghcr.io/home-assistant/home-assistant:stable
  sudo docker run -d \
    --name homeassistant \
    --privileged \
    --restart=unless-stopped \
    --stop-timeout 60 \
    -e TZ=Europe/Paris \
    -v "$HA_CONFIG_DIR:/config" \
    -v /run/dbus:/run/dbus:ro \
    --network=host \
    ghcr.io/home-assistant/home-assistant:stable
fi

say "Vicky 8.1 holen/aktualisieren"
if [[ -d "$INSTALL_DIR/.git" ]]; then
  git -C "$INSTALL_DIR" fetch origin "$BRANCH"
  git -C "$INSTALL_DIR" checkout "$BRANCH"
  git -C "$INSTALL_DIR" pull --ff-only origin "$BRANCH"
else
  if [[ -e "$INSTALL_DIR" ]]; then
    echo "Ziel existiert, ist aber kein Git-Repository: $INSTALL_DIR"
    exit 1
  fi
  git clone -b "$BRANCH" "$REPO_URL" "$INSTALL_DIR"
fi

say "Python-Umgebung aufbauen"
python3 -m venv "$INSTALL_DIR/.venv"
"$INSTALL_DIR/.venv/bin/pip" install --upgrade pip
"$INSTALL_DIR/.venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

say "Vicky-Konfiguration schreiben"
cat > "$INSTALL_DIR/config.py" <<EOF
MQTT_HOST = "${MQTT_HOST}"
MQTT_USER = "${MQTT_USER}"
MQTT_PASS = "${MQTT_PASS}"
BASE_TOPIC = "${AWTRIX_UID}/custom"
MAX_DISPLAY_TEXT = 180
DEFAULT_DURATION = 20
EOF
chmod 0600 "$INSTALL_DIR/config.py"

say "SSH-Schlüssel für Victron prüfen"
install -d -m 0700 "$USER_HOME/.ssh"
if [[ ! -f "$SSH_KEY" ]]; then
  ssh-keygen -t ed25519 -N '' -f "$SSH_KEY"
fi
chown -R "$INSTALL_USER":"$(id -gn "$INSTALL_USER")" "$USER_HOME/.ssh"

say "systemd-Dienste installieren"
PYTHON="$INSTALL_DIR/.venv/bin/python"

sudo tee /etc/systemd/system/awtrix-news.service >/dev/null <<EOF
[Unit]
Description=Vicky V8.1 AWTRIX News Service
After=network-online.target mosquitto.service
Wants=network-online.target

[Service]
Type=simple
User=$INSTALL_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$PYTHON $INSTALL_DIR/awtrix_news_vicki.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1
Environment=VICKY_AI_IMPORTANCE_SORT=$AI_SORT
Environment=VICKY_AI_IMPORTANCE_URL=$AI_URL
Environment=VICKY_AI_IMPORTANCE_MODEL=$AI_MODEL

[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/systemd/system/awtrix-victron.service >/dev/null <<EOF
[Unit]
Description=Vicky V8.1 AWTRIX Victron Tiles
After=network-online.target mosquitto.service
Wants=network-online.target

[Service]
Type=simple
User=$INSTALL_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$PYTHON $INSTALL_DIR/victron/awtrix_victron.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1
Environment=VICKY_CERBO_HOST=$CERBO_HOST
Environment=VICKY_CERBO_USER=$CERBO_USER
Environment=VICKY_CERBO_SSH_KEY=$SSH_KEY

[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/systemd/system/vicky-awtrix-button.service >/dev/null <<EOF
[Unit]
Description=Vicky V8.1 AWTRIX Button Listener
After=network-online.target mosquitto.service
Wants=network-online.target

[Service]
Type=simple
User=$INSTALL_USER
WorkingDirectory=$INSTALL_DIR
Environment=VICKY_DIR=$INSTALL_DIR
ExecStart=$INSTALL_DIR/scripts/vicky-awtrix-button
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

chmod +x "$INSTALL_DIR/scripts/vicky-awtrix-button"
sudo systemctl daemon-reload

say "Home-Assistant Vicky-Automationen und FX-Sensoren installieren"
AUTO="$HA_CONFIG_DIR/automations.yaml"
CONF="$HA_CONFIG_DIR/configuration.yaml"
RAIN="$INSTALL_DIR/weather/rain_warning.yaml"
mkdir -p "$HA_CONFIG_DIR"
touch "$AUTO" "$CONF"
cp "$AUTO" "$AUTO.before-vicky8" 2>/dev/null || true
cp "$CONF" "$CONF.before-vicky8" 2>/dev/null || true

# REST-Sensoren USD/EUR, EUR/USD und Gold. Bei einem normalen 'sensor:'-Block
# werden die Einträge idempotent eingefügt. Include-basierte sensor:-Konfigurationen
# werden aus Sicherheitsgründen nicht automatisch verändert.
if grep -q "name: ['\"]\?USD_EUR['\"]\?" "$CONF" 2>/dev/null; then
  echo "FX-/Gold-Sensoren sind bereits vorhanden."
elif grep -Eq '^sensor:[[:space:]]*!include' "$CONF"; then
  echo "WARNUNG: configuration.yaml verwendet sensor: !include."
  echo "FX-/Gold-Sensoren werden nicht automatisch eingefügt, um die bestehende Include-Struktur nicht zu beschädigen."
else
  python3 - "$CONF" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text() if path.exists() else ""
block = '''  # Vicky 8.1 – FX und Gold, ohne API-Key
  - platform: rest
    name: "USD_EUR"
    resource: "https://api.frankfurter.app/latest?from=USD&to=EUR"
    value_template: "{{ value_json.rates.EUR | float(0) }}"
    unit_of_measurement: "EUR"
    scan_interval: 300
  - platform: rest
    name: "EUR_USD"
    resource: "https://api.frankfurter.app/latest?from=EUR&to=USD"
    value_template: "{{ value_json.rates.USD | float(0) }}"
    unit_of_measurement: "USD"
    scan_interval: 300
  - platform: rest
    name: "Gold_USD"
    resource: "https://api.frankfurter.dev/v2/rate/XAU/USD"
    value_template: "{{ value_json.rate | float(0) }}"
    unit_of_measurement: "USD/oz"
    scan_interval: 300
'''
lines = text.splitlines(True)
for i, line in enumerate(lines):
    if line.strip() == "sensor:" and not line.startswith((" ", "\t")):
        lines.insert(i + 1, block)
        path.write_text("".join(lines))
        break
else:
    if text and not text.endswith("\n"):
        text += "\n"
    path.write_text(text + "\nsensor:\n" + block)
PY
  echo "USD/EUR-, EUR/USD- und Gold-Sensoren ergänzt."
fi

TMP_FX="$(mktemp)"
cat > "$TMP_FX" <<EOF
- alias: AWTRIX – USD/EUR Kurs alle 5 Minuten
  id: awtrix_fx_usd_eur_every_5
  mode: single
  trigger:
    - platform: time_pattern
      minutes: /5
    - platform: homeassistant
      event: start
  variables:
    rate: '{{ states("sensor.eur_usd") | float(0) }}'
  condition:
    - condition: template
      value_template: '{{ rate > 0 }}'
  action:
    - service: mqtt.publish
      data:
        topic: "${AWTRIX_UID}/notify"
        retain: false
        payload: >-
          {"text":"EUR→USD: {{ rate | round(4) }}","duration":12}
EOF
append_automation_if_missing "awtrix_fx_usd_eur_every_5" "$TMP_FX" "$AUTO"
rm -f "$TMP_FX"

TMP_GOLD="$(mktemp)"
cat > "$TMP_GOLD" <<EOF
- id: awtrix_gold_every_5
  alias: AWTRIX – Goldpreis
  mode: single
  trigger:
    - platform: time_pattern
      minutes: /5
    - platform: homeassistant
      event: start
  condition:
    - condition: template
      value_template: '{{ states("sensor.gold_usd") not in ["unknown", "unavailable", "none", ""] }}'
  action:
    - service: mqtt.publish
      data:
        topic: "${AWTRIX_UID}/notify"
        retain: false
        payload: >-
          {"text":"GOLD \${{ states('sensor.gold_usd') | float(0) | round(2) }}","icon":11627,"duration":12,"color":"FFD700"}
EOF
append_automation_if_missing "awtrix_gold_every_5" "$TMP_GOLD" "$AUTO"
rm -f "$TMP_GOLD"

TMP_ENPHASE="$(mktemp)"
cat > "$TMP_ENPHASE" <<EOF
- id: enphase_pv_an_victron_mqtt
  alias: Enphase PV an Victron MQTT
  description: Sendet die aktuelle Enphase-PV-Leistung an Victron über MQTT
  trigger:
    - platform: state
      entity_id: ${ENPHASE_POWER_ENTITY}
    - platform: homeassistant
      event: start
    - platform: time_pattern
      minutes: /5
  condition:
    - condition: template
      value_template: '{{ states("${ENPHASE_POWER_ENTITY}") not in ["unknown", "unavailable", "none"] }}'
  action:
    - service: mqtt.publish
      data:
        topic: enphase_pv/status
        retain: true
        payload: >-
          {"power": {{ (states('${ENPHASE_POWER_ENTITY}') | float(0) * 1000) | round(0) }}, "voltage": 230, "current": {{ (states('${ENPHASE_POWER_ENTITY}') | float(0) * 1000 / 230) | round(2) }}}
  mode: restart
EOF
append_automation_if_missing "enphase_pv_an_victron_mqtt" "$TMP_ENPHASE" "$AUTO"
rm -f "$TMP_ENPHASE"

if grep -q "1787248345937" "$AUTO"; then
  echo "Regenautomation mit ID 1787248345937 ist bereits vorhanden; keine Überschreibung."
else
  printf '\n' >> "$AUTO"
  cat "$RAIN" >> "$AUTO"
  echo "Regenautomation ergänzt."
fi

say "Syntax prüfen"
"$PYTHON" -m py_compile \
  "$INSTALL_DIR/awtrix_news_vicki.py" \
  "$INSTALL_DIR/safe_news_editor.py" \
  "$INSTALL_DIR/ai_importance_sorter.py" \
  "$INSTALL_DIR/offline_translator.py" \
  "$INSTALL_DIR/language_state.py" \
  "$INSTALL_DIR/feed_monitor.py" \
  "$INSTALL_DIR/news_ranker.py" \
  "$INSTALL_DIR/display.py" \
  "$INSTALL_DIR/victron/awtrix_victron.py"

if sudo docker ps --format '{{.Names}}' | grep -qx homeassistant; then
  sudo docker exec homeassistant python -m homeassistant --script check_config --config /config || {
    echo "WARNUNG: Home-Assistant-Konfigurationsprüfung ist noch nicht erfolgreich."
    echo "Bei einer frischen Installation zuerst das HA-Onboarding abschließen und danach erneut prüfen."
  }
fi

say "Installation abgeschlossen"
echo
echo "Installiert/vorbereitet:"
echo "  - Vicky 8.1 News"
echo "  - AWTRIX Sprach-/Button-Steuerung"
echo "  - Victron AWTRIX Tiles"
echo "  - Mosquitto MQTT"
echo "  - Home Assistant Container"
echo "  - V8 Regenautomation"
echo "  - USD/EUR- und EUR/USD-Sensoren + AWTRIX-Anzeige"
echo "  - Goldpreis-Sensor + AWTRIX-Anzeige"
echo "  - Enphase PV → MQTT → Victron-Automation"
if [[ "$AI_SORT" == "1" ]]; then
  echo "  - V8.1 AI-Priorisierung: aktiviert ($AI_URL)"
else
  echo "  - V8.1 AI-Priorisierung: vorbereitet, derzeit deaktiviert"
fi
echo
echo "WICHTIG: Vicky-Dienste werden noch nicht automatisch gestartet, damit AWTRIX und Victron zuerst geprüft werden können."
echo
echo "Noch einmalig erforderlich:"
echo "1. Home Assistant öffnen: http://<IP-DIESES-RECHNERS>:8123 und Onboarding abschließen."
echo "2. In Home Assistant die MQTT-Integration mit Broker $MQTT_HOST:1883, Benutzer $MQTT_USER einrichten."
echo "3. In Home Assistant Météo-France einrichten, sodass die next_rain-Entität für Billiat vorhanden ist."
echo "4. Enphase Envoy in Home Assistant einrichten und die Produktions-Entity prüfen: $ENPHASE_POWER_ENTITY"
echo "5. AWTRIX MQTT auf diesen Broker einstellen: Port 1883, Benutzer $MQTT_USER."
echo "6. Cerbo/GX SSH-Key autorisieren: $SSH_KEY.pub"
echo "   Test: ssh -i '$SSH_KEY' '$CERBO_USER@$CERBO_HOST' 'echo OK'"
if [[ "$AI_SORT" == "1" ]]; then
  echo "7. Lokalen AI-Server prüfen: $AI_URL"
else
  echo "7. Für die V8.1 AI-Priorisierung später einen lokalen OpenAI-kompatiblen AI-Server einrichten und VICKY_AI_IMPORTANCE_SORT=1 setzen."
fi
echo
echo "Danach testen:"
echo "   cd '$INSTALL_DIR' && '$PYTHON' victron/awtrix_victron.py"
echo "   cd '$INSTALL_DIR' && '$PYTHON' awtrix_news_vicki.py"
echo
echo "Wenn beide Tests funktionieren:"
echo "   sudo systemctl enable --now awtrix-news awtrix-victron vicky-awtrix-button"
echo
echo "Status:"
echo "   systemctl --no-pager --full status awtrix-news awtrix-victron vicky-awtrix-button"
