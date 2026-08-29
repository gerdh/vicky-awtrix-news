#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/gerdh/vicky-awtrix-news.git"
BRANCH="v8-clean"
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

say() { printf '\n==> %s\n' "$*"; }

read_default() {
  local prompt="$1" default="$2" var
  read -r -p "$prompt [$default]: " var
  printf '%s' "${var:-$default}"
}

if ! command -v apt-get >/dev/null 2>&1; then
  echo "Dieser Installer unterstützt derzeit Debian/Ubuntu-Systeme mit apt."
  exit 1
fi

if $DRY_RUN; then
  say "Vicky 8 DRY-RUN"
  echo "Es werden KEINE Dateien, Pakete, Container oder Dienste verändert."
  echo "Benutzer : $INSTALL_USER"
  echo "Ziel      : $INSTALL_DIR"
  echo
  printf '%-28s %s\n' "apt-get" "$(command -v apt-get >/dev/null 2>&1 && echo vorhanden || echo FEHLT)"
  printf '%-28s %s\n' "git" "$(command -v git >/dev/null 2>&1 && echo vorhanden || echo wird installiert)"
  printf '%-28s %s\n' "python3" "$(command -v python3 >/dev/null 2>&1 && echo vorhanden || echo wird installiert)"
  printf '%-28s %s\n' "mosquitto_pub" "$(command -v mosquitto_pub >/dev/null 2>&1 && echo vorhanden || echo wird installiert)"
  printf '%-28s %s\n' "docker" "$(command -v docker >/dev/null 2>&1 && echo vorhanden || echo wird installiert)"

  if [[ -d "$INSTALL_DIR/.git" ]]; then
    echo "Vicky 8 Repository          vorhanden -> würde aktualisiert"
  elif [[ -e "$INSTALL_DIR" ]]; then
    echo "Vicky 8 Ziel                existiert, aber kein Git-Repo -> echte Installation würde ABBRECHEN"
  else
    echo "Vicky 8 Repository          fehlt -> würde aus $BRANCH geklont"
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
  echo "  4. Vicky 8 klonen/aktualisieren und Python-venv bauen"
  echo "  5. AWTRIX/MQTT config.py erzeugen"
  echo "  6. SSH-Key für Cerbo/GX vorbereiten"
  echo "  7. News-, Victron- und Button-systemd-Dienste anlegen"
  echo "  8. V8-Regenautomation in Home Assistant ergänzen"
  echo "  9. Python- und Home-Assistant-Konfiguration prüfen"
  echo
  echo "DRY-RUN beendet: keine Änderungen vorgenommen."
  exit 0
fi

say "Vicky 8 Komplett-Installer"
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

say "V8 Regenautomation in Home Assistant installieren"
AUTO="$HA_CONFIG_DIR/automations.yaml"
RAIN="$INSTALL_DIR/weather/rain_warning.yaml"
mkdir -p "$HA_CONFIG_DIR"
touch "$AUTO"
if grep -q "1787248345937" "$AUTO"; then
  echo "Regenautomation mit ID 1787248345937 ist bereits vorhanden; keine Überschreibung."
else
  cp "$AUTO" "$AUTO.before-vicky8"
  printf '\n' >> "$AUTO"
  cat "$RAIN" >> "$AUTO"
  echo "Regenautomation ergänzt. Backup: $AUTO.before-vicky8"
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

if sudo docker ps --format '{{.Names}}' | grep -qx homeassistant; then
  sudo docker exec homeassistant python -m homeassistant --script check_config --config /config || {
    echo "WARNUNG: Home-Assistant-Konfigurationsprüfung ist noch nicht erfolgreich."
    echo "Bei einer frischen Installation zuerst das HA-Onboarding abschließen und danach erneut prüfen."
  }
fi

say "Installation abgeschlossen"
echo
echo "Installiert/vorbereitet:"
echo "  - Vicky 8 News"
echo "  - AWTRIX Sprach-/Button-Steuerung"
echo "  - Victron AWTRIX Tiles"
echo "  - Mosquitto MQTT"
echo "  - Home Assistant Container"
echo "  - V8 Regenautomation"
echo
echo "WICHTIG: Vicky-Dienste werden noch nicht automatisch gestartet, damit AWTRIX und Victron zuerst geprüft werden können."
echo
echo "Noch einmalig erforderlich:"
echo "1. Home Assistant öffnen: http://<IP-DIESES-RECHNERS>:8123 und Onboarding abschließen."
echo "2. In Home Assistant die MQTT-Integration mit Broker $MQTT_HOST:1883, Benutzer $MQTT_USER einrichten."
echo "3. In Home Assistant Météo-France einrichten, sodass die next_rain-Entität für Billiat vorhanden ist."
echo "4. AWTRIX MQTT auf diesen Broker einstellen: Port 1883, Benutzer $MQTT_USER."
echo "5. Cerbo/GX SSH-Key autorisieren: $SSH_KEY.pub"
echo "   Test: ssh -i '$SSH_KEY' '$CERBO_USER@$CERBO_HOST' 'echo OK'"
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
