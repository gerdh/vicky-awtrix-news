"""Public configuration template for the Vicky 7 Avalon module.

Copy this file to ``avalon_config.py`` and adapt it locally.
Do not commit private addresses or credentials.
"""

MINER_NAME = "Avalon"
MINER_HOST = "192.0.2.10"
MINER_PORT = 4028
POLL_SECONDS = 60
SOCKET_TIMEOUT = 5

AWTRIX_TOPIC = "avalon"
STATE_FILE = "cache/avalon_last_display.json"

MINIMUM_HASHRATE_TH = 4
WARN_TEMPERATURE = 95
HOT_TEMPERATURE = 100

COLOR_OK = "00FF00"
COLOR_WARN = "FFFF00"
COLOR_HOT = "FF0000"
COLOR_OFFLINE = "FF0000"
