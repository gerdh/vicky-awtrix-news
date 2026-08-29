#!/usr/bin/env python3

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

# Allow direct execution as `python victron/awtrix_victron.py` by adding the
# repository root (which contains config.py) to the import path.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config import BASE_TOPIC, MQTT_HOST, MQTT_PASS, MQTT_USER

CERBO_HOST = os.environ.get("VICKY_CERBO_HOST", "192.168.1.63")
CERBO_USER = os.environ.get("VICKY_CERBO_USER", "root")
SSH_KEY = os.environ.get("VICKY_CERBO_SSH_KEY", "/home/gerd/.ssh/id_ed25519")


def run(cmd, timeout=15):
    return subprocess.check_output(cmd, shell=True, text=True, timeout=timeout).strip()


def number(text, default=0.0):
    match = re.search(r"[-+]?\d+(?:\.\d+)?", str(text))
    return float(match.group(0)) if match else default


def get_victron():
    out = run(
        f"""ssh -o ConnectTimeout=10 -o ConnectionAttempts=3 \
-o ServerAliveInterval=5 -o ServerAliveCountMax=2 -o BatchMode=yes \
-i {SSH_KEY} -l {CERBO_USER} {CERBO_HOST} '
SOLAR=$(dbus -y | grep -m1 com.victronenergy.solarcharger)
echo GRID=$(dbus -y com.victronenergy.system /Ac/Grid/L1/Power GetValue)
echo HOUSE=$(dbus -y com.victronenergy.system /Ac/Consumption/L1/Power GetValue)
echo SOC=$(dbus -y com.victronenergy.system /Dc/Battery/Soc GetValue)
if [ -n "$SOLAR" ]; then
  echo SMARTSOLAR=$(dbus -y "$SOLAR" /Yield/Power GetValue)
else
  echo SMARTSOLAR=0
fi
'"""
    )

    values = {}
    for line in out.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = number(value)
    return values


def mqtt_page(name, text, icon=53183, color="FF8C00"):
    payload = {
        "text": text,
        "icon": icon,
        "duration": 6,
        "rainbow": False,
        "color": color,
    }
    topic = f"{BASE_TOPIC}/{name}"
    subprocess.run(
        [
            "mosquitto_pub",
            "-h",
            MQTT_HOST,
            "-u",
            MQTT_USER,
            "-P",
            MQTT_PASS,
            "-t",
            topic,
            "-m",
            json.dumps(payload, ensure_ascii=False),
        ],
        check=False,
    )


def clear_page(name):
    subprocess.run(
        [
            "mosquitto_pub",
            "-h",
            MQTT_HOST,
            "-u",
            MQTT_USER,
            "-P",
            MQTT_PASS,
            "-t",
            f"{BASE_TOPIC}/{name}",
            "-r",
            "-n",
        ],
        check=False,
    )


def cleanup():
    for app in [
        "victron_house",
        "victron_grid",
        "victron_battery",
        "victron_smartsolar",
        "victron_error",
        "vicky_house",
        "vicky_grid",
        "vicky_battery",
        "vicky_smartsolar",
        "vicky_error",
    ]:
        clear_page(app)


def main():
    cleanup()
    time.sleep(2)

    while True:
        try:
            values = get_victron()
            grid = values.get("GRID", 0)
            soc = values.get("SOC", 0)
            smartsolar = values.get("SMARTSOLAR", 0)

            if smartsolar >= 100:
                mqtt_page("vicky_smartsolar", f"Sol {smartsolar:.0f}W", 53183, "FFFF00")
                time.sleep(15)
            else:
                # Remove the retained daytime SmartSolar page when solar power is low.
                clear_page("vicky_smartsolar")

            mqtt_page("vicky_battery", f"Batt {soc:.0f}%", 554, "00FF00")
            time.sleep(15)

            if grid < 0:
                mqtt_page("vicky_grid", f"Out {abs(grid):.0f}W", 503, "0080FF")
            else:
                mqtt_page("vicky_grid", f"In {grid:.0f}W", 503, "FF0000")
            time.sleep(15)

        except Exception as exc:
            print(f"Victron refresh failed: {exc}", flush=True)
            time.sleep(10)


if __name__ == "__main__":
    main()
