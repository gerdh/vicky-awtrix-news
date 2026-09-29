#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SITE="${1:-}"

case "$SITE" in
  montpellier)
    PROFILE="$REPO_ROOT/sites/montpellier-orin.conf.example"
    ;;
  davanod)
    PROFILE="$REPO_ROOT/sites/davanod-moon.conf.example"
    ;;
  *)
    echo "Usage: bash scripts/configure-site.sh montpellier|davanod"
    exit 2
    ;;
esac

# shellcheck disable=SC1090
source "$PROFILE"

read_default() {
  local prompt="$1" default="$2" value
  read -r -p "$prompt [$default]: " value
  printf '%s' "${value:-$default}"
}

echo "Configuring Vicky 9 for $VICKY_SITE on $VICKY_HARDWARE"
AWTRIX_UID="$(read_default 'Local AWTRIX UID' "$AWTRIX_UID")"
if [[ "$AWTRIX_UID" == REPLACE_WITH_* || -z "$AWTRIX_UID" ]]; then
  echo "ERROR: enter the real local AWTRIX UID."
  exit 1
fi
MQTT_HOST="$(read_default 'Local MQTT broker host' "$MQTT_HOST")"
MQTT_USER="$(read_default 'MQTT user' 'mqtt_user')"
read -r -s -p "MQTT password: " MQTT_PASS
echo
if [[ -z "$MQTT_PASS" ]]; then
  echo "ERROR: MQTT password must not be empty."
  exit 1
fi

umask 077
cat >"$REPO_ROOT/config.py" <<EOF
# Generated locally for Vicky 9. Never commit this file.
VICKY_SITE = "$VICKY_SITE"
VICKY_HARDWARE = "$VICKY_HARDWARE"
AWTRIX_IP = "$AWTRIX_IP"
AWTRIX_UID = "$AWTRIX_UID"
MQTT_HOST = "$MQTT_HOST"
MQTT_USER = "$MQTT_USER"
MQTT_PASS = "$MQTT_PASS"
BASE_TOPIC = "$AWTRIX_UID/custom"
MAX_DISPLAY_TEXT = 180
DEFAULT_DURATION = 20
EOF

cat >"$REPO_ROOT/.vicky-site" <<EOF
VICKY_SITE=$VICKY_SITE
VICKY_HARDWARE=$VICKY_HARDWARE
AWTRIX_IP=$AWTRIX_IP
AWTRIX_UID=$AWTRIX_UID
MQTT_HOST=$MQTT_HOST
EOF

chmod 600 "$REPO_ROOT/config.py"
echo "Created $REPO_ROOT/config.py for $VICKY_SITE."
echo "BASE_TOPIC=$AWTRIX_UID/custom"
