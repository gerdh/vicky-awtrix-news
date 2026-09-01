#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID:-$(id -u)} -eq 0 ]]; then
  echo "Bitte als normaler Benutzer starten; sudo wird bei Bedarf verwendet."
  exit 1
fi

INSTALL_USER="${SUDO_USER:-$USER}"
USER_HOME="$(getent passwd "$INSTALL_USER" | cut -d: -f6)"
CERBO_HOST="${VICKY_CERBO_HOST:-192.168.1.63}"
CERBO_USER="${VICKY_CERBO_USER:-root}"
SSH_KEY="${VICKY_CERBO_SSH_KEY:-$USER_HOME/.ssh/id_ed25519}"
MQTT_USER="${VICKY_MQTT_USER:-mqtt_user}"
MQTT_PASS="${VICKY_MQTT_PASS:-}"
LAN_IP="$(hostname -I 2>/dev/null | tr ' ' '\n' | awk '/^192\.168\.|^10\.|^172\.(1[6-9]|2[0-9]|3[01])\./ {print; exit}')"

printf '\n==> Vicky 8.2 MOON Upgrade\n'

printf '\n==> Mosquitto LAN-Listener und Rechte korrigieren\n'
sudo install -d -m 0755 /etc/mosquitto/conf.d
if [[ ! -f /etc/mosquitto/passwd ]]; then
  sudo touch /etc/mosquitto/passwd
fi
sudo chown root:mosquitto /etc/mosquitto/passwd
sudo chmod 0640 /etc/mosquitto/passwd
sudo tee /etc/mosquitto/conf.d/vicky8.conf >/dev/null <<'EOF'
listener 1883 0.0.0.0
allow_anonymous false
password_file /etc/mosquitto/passwd
EOF
sudo systemctl enable mosquitto >/dev/null
sudo systemctl restart mosquitto

if ! sudo -u mosquitto test -r /etc/mosquitto/passwd; then
  echo "FEHLER: /etc/mosquitto/passwd ist für mosquitto nicht lesbar."
  exit 1
fi

if ! sudo ss -ltnp | grep -qE '0\.0\.0\.0:1883|\*:1883'; then
  echo "FEHLER: Mosquitto lauscht nicht auf dem LAN-Port 1883."
  sudo ss -ltnp | grep 1883 || true
  exit 1
fi

if [[ -n "$MQTT_PASS" ]]; then
  mosquitto_pub -h 127.0.0.1 -u "$MQTT_USER" -P "$MQTT_PASS" -t test/vicky8 -m "vicky8.2" >/dev/null
  echo "MQTT Login/Publish erfolgreich."
else
  echo "Hinweis: Für einen automatischen MQTT-Login-Test VICKY_MQTT_PASS setzen."
fi

printf '\n==> Cerbo/GX SSH Host-Key vorbereiten\n'
install -d -m 0700 "$USER_HOME/.ssh"
if [[ ! -f "$SSH_KEY" ]]; then
  ssh-keygen -t ed25519 -N '' -f "$SSH_KEY"
fi
ssh-keygen -R "$CERBO_HOST" >/dev/null 2>&1 || true
ssh-keyscan -H "$CERBO_HOST" >> "$USER_HOME/.ssh/known_hosts" 2>/dev/null || {
  echo "WARNUNG: Cerbo/GX $CERBO_HOST konnte nicht per ssh-keyscan erreicht werden."
}
chmod 0600 "$USER_HOME/.ssh/known_hosts" 2>/dev/null || true
chown -R "$INSTALL_USER":"$(id -gn "$INSTALL_USER")" "$USER_HOME/.ssh"

printf '\n==> Passwortlosen Cerbo/GX SSH-Zugang prüfen\n'
if ssh -o BatchMode=yes -o ConnectTimeout=10 -i "$SSH_KEY" "$CERBO_USER@$CERBO_HOST" 'echo OK' 2>/dev/null | grep -qx OK; then
  echo "Cerbo/GX Key-Login ist bereits passwortlos eingerichtet."
else
  echo "Der öffentliche Schlüssel muss einmal auf dem Cerbo/GX installiert werden."
  echo "Dabei wird einmal das Passwort von $CERBO_USER@$CERBO_HOST abgefragt."
  echo
  echo "Ausführen:"
  echo "  ssh-copy-id -i '$SSH_KEY.pub' '$CERBO_USER@$CERBO_HOST'"
  echo
  echo "Danach zwingend ohne Passwort testen:"
  echo "  ssh -o BatchMode=yes -i '$SSH_KEY' '$CERBO_USER@$CERBO_HOST' 'echo OK'"
  echo "Erwartet: sofort OK, ohne Passwortabfrage."
fi

echo
echo "Vicky 8.2 Upgrade abgeschlossen."
if [[ -n "$LAN_IP" ]]; then
  echo "AWTRIX MQTT Broker: $LAN_IP"
else
  echo "AWTRIX MQTT Broker: LAN-IP dieses Rechners (hostname -I prüfen)"
fi
echo "AWTRIX MQTT Port:   1883"
echo "Cerbo/GX Host:      $CERBO_HOST"
echo
echo "MQTT prüfen: sudo ss -ltnp | grep 1883"
echo "SSH prüfen:  ssh -o BatchMode=yes -i '$SSH_KEY' '$CERBO_USER@$CERBO_HOST' 'echo OK'"
