# Copy this file to config.py only for manual configuration.
# Prefer: bash scripts/configure-site.sh montpellier|davanod
# Never commit real passwords, AWTRIX UIDs or local credentials.

VICKY_SITE = "replace_with_montpellier_or_davanod"
VICKY_HARDWARE = "replace_with_jetson_orin_or_raspberry_pi_5"
AWTRIX_IP = "192.168.1.86"
AWTRIX_UID = "awtrix_replace_with_local_uid"

MQTT_HOST = "127.0.0.1"
MQTT_USER = "your_mqtt_username"
MQTT_PASS = "your_mqtt_password"
BASE_TOPIC = f"{AWTRIX_UID}/custom"

MAX_DISPLAY_TEXT = 180
DEFAULT_DURATION = 20

# Victron connection remains local and is configured through environment values:
# VICKY_CERBO_HOST=192.168.1.63
# VICKY_CERBO_USER=root
# VICKY_CERBO_SSH_KEY=/home/gerd/.ssh/id_ed25519
