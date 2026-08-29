#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/gerdh/vicky-awtrix-news.git"
BRANCH="v8-clean"

if [[ ${EUID:-$(id -u)} -eq 0 ]]; then
  echo "Bitte als normaler Benutzer starten, nicht direkt als root. sudo wird bei Bedarf verwendet."
  exit 1
fi

INSTALL_USER="${SUDO_USER:-$USER}"
USER_HOME="$(getent passwd "$INSTALL_USER" | cut -d: -f6)"
INSTALL_DIR="${VICKY_INSTALL_DIR:-$USER_HOME/vicky8}"

say() { printf '\n==> %s\n' "$*"; }
need() { command -v "$1" >/dev/null 2>&1 || { echo "FEHLT: $1"; exit 1; }; }

read_default() {
  local prompt="$1" default="$2" var
  read -r -p "$prompt [$default]: " var
  printf '%s' "${var:-$default}"
}

say "Vicky 8 Installer"
echo "Benutzer : $INSTALL_USER"
echo "Ziel      : $INSTALL_DIR"

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

read -r -p "Lokalen Mosquitto-Broker installieren/konfigurieren? [J/n]: " INSTALL_MQTT
INSTALL_MQTT="${INSTALL_MQTT:-J}"

read -r -p "Home-Assistant-Regenautomation jetzt installieren? [j/N]: " INSTALL_RAIN
INSTALL_RAIN="${INSTALL_RAIN:-N}"
HA_CONFIG_DIR=""
if [[ "$INSTALL_RAIN" =~ ^[JjYy]$ ]]; then
  HA_CONFIG_DIR="$(read_default 'Pfad zum Home-Assistant config-Ordner' '/config')"
fi

say "Systempakete installieren"
sudo apt-get update
sudo apt-get install -y git python3 python3-venv python3-pip openssh-client mosquitto-clients curl ca-certificates

if [[ "$INSTALL_MQTT" =~ ^[JjYy]$ ]]; then
  sudo apt-get install -y mosquitto
  say "Mosquitto mit Passwortschutz konfigurieren"
  sudo install -d -m 0755 /etc/mosquitto/conf.d
  sudo touch /etc/mosquitto/passwd
  sudo chmod 0600 /etc/mosquitto/passwd
  printf '%s\n' "$MQTT_PASS" | sudo mosquitto_passwd -b /etc/mosquitto/passwd "$MQTT_USER" "$MQTT_PASS" >/dev/null
  sudo tee /etc/mosquitto/conf.d/vicky8.conf >/dev/null <<EOF
listener 1883 0.0.0.0
allow_anonymous false
password_file /etc/mosquitto/passwd
EOF
  sudo systemctl enable --now mosquitto
fi

say "Vicky 8 holen/aktualisieren"
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
Description=Vicky V8 AWTRIX News Service
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

[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/systemd/system/awtrix-victron.service >/dev/null <<EOF
[Unit]
Description=Vicky V8 AWTRIX Victron Tiles
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
Description=Vicky V8 AWTRIX Button Listener
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

if [[ "$INSTALL_RAIN" =~ ^[JjYy]$ ]]; then
  say "Home-Assistant-Regenautomation installieren"
  AUTO="$HA_CONFIG_DIR/automations.yaml"
  RAIN="$INSTALL_DIR/weather/rain_warning.yaml"
  if [[ ! -f "$AUTO" ]]; then
    echo "WARNUNG: $AUTO nicht gefunden. Regenautomation wurde nicht verändert."
  elif grep -q "1787248345937" "$AUTO"; then
    echo "Regenautomation mit ID 1787248345937 ist bereits vorhanden; keine automatische Überschreibung."
    echo "V8-Datei liegt hier: $RAIN"
  else
    cp "$AUTO" "$AUTO.before-vicky8"
    printf '\n' >> "$AUTO"
    cat "$RAIN" >> "$AUTO"
    echo "Regenautomation ergänzt. Backup: $AUTO.before-vicky8"
  fi
fi

say "Syntax prüfen"
"$PYTHON" -m py_compile \
  "$INSTALL_DIR/awtrix_news_vicki.py" \
  "$INSTALL_DIR/safe_news_editor.py" \
  "$INSTALL_DIR/offline_translator.py" \
  "$INSTALL_DIR/language_state.py" \
  "$INSTALL_DIR/feed_monitor.py" \
  "$INSTALL_DIR/news_ranker.py" \
  "$INSTALL_DIR/display.py" \
  "$INSTALL_DIR/victron/awtrix_victron.py"

say "Installation abgeschlossen"
echo
echo "WICHTIG: Noch nicht automatisch gestartet, damit AWTRIX/Victron erst geprüft werden können."
echo
echo "1. AWTRIX MQTT auf den Broker dieses Rechners einstellen: Port 1883, Benutzer $MQTT_USER."
echo "2. Cerbo/GX SSH-Key autorisieren. Öffentlicher Schlüssel:"
echo "   $SSH_KEY.pub"
echo "   Test: ssh -i '$SSH_KEY' '$CERBO_USER@$CERBO_HOST' 'echo OK'"
echo "3. Victron-Test:"
echo "   cd '$INSTALL_DIR' && '$PYTHON' victron/awtrix_victron.py"
echo "4. News-Test:"
echo "   cd '$INSTALL_DIR' && '$PYTHON' awtrix_news_vicki.py"
echo "5. Wenn beide Tests funktionieren, Dienste starten:"
echo "   sudo systemctl enable --now awtrix-news awtrix-victron vicky-awtrix-button"
echo
echo "Status:"
echo "   systemctl --no-pager --full status awtrix-news awtrix-victron vicky-awtrix-button"
echo
echo "Regen benötigt zusätzlich Home Assistant, die Météo-France next_rain Entität für Billiat und MQTT Discovery."
