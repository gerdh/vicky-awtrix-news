# Copy this file to config.py and adapt the values locally.
# Never commit real passwords or local credentials.

# Shared MQTT / AWTRIX settings used by News and Victron.
MQTT_HOST = "127.0.0.1"
MQTT_USER = "your_mqtt_username"
MQTT_PASS = "your_mqtt_password"

BASE_TOPIC = "awtrix_xxxxxx/custom"

MAX_DISPLAY_TEXT = 180
DEFAULT_DURATION = 20

# Optional final AI importance sorter
# -----------------------------------
# The normal Vicky 8 pipeline remains unchanged. After the messages have been
# selected, safely handled and translated, Vicky can send only the finished
# message texts plus numeric IDs to a local OpenAI-compatible model. The model
# may return only a permutation of those IDs. Python then reorders the original
# message objects; no model-generated news text is ever used.
#
# Environment variables:
#   VICKY_AI_IMPORTANCE_SORT=1
#   VICKY_AI_IMPORTANCE_URL=http://127.0.0.1:8080/v1/chat/completions
#   VICKY_AI_IMPORTANCE_MODEL=local-model
#   VICKY_AI_IMPORTANCE_TIMEOUT=20
#
# Set VICKY_AI_IMPORTANCE_SORT=0 to disable the extra pass. If the endpoint is
# unavailable or the model returns anything other than every supplied ID exactly
# once, Vicky keeps the existing order unchanged.

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
