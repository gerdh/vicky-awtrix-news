# Copy this file to config.py and adapt the values locally.
# Never commit real passwords or local credentials.

# Shared MQTT / AWTRIX settings used by News and Victron.
MQTT_HOST = "127.0.0.1"
MQTT_USER = "your_mqtt_username"
MQTT_PASS = "your_mqtt_password"

BASE_TOPIC = "awtrix_xxxxxx/custom"

MAX_DISPLAY_TEXT = 180
DEFAULT_DURATION = 20

# Victron connection settings are intentionally environment variables rather
# than credentials in this file. The V8 defaults are:
#
#   VICKY_CERBO_HOST=192.168.1.63
#   VICKY_CERBO_USER=root
#   VICKY_CERBO_SSH_KEY=/home/gerd/.ssh/id_ed25519
#
# Override them in the service environment when another GX/Cerbo host or SSH
# key is used. Passwordless SSH access from the Orin to the GX device is
# required by victron/awtrix_victron.py.
