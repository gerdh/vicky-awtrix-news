#!/usr/bin/env python3
"""Backup and restore the four retained Montpellier AWTRIX market tiles.

Backup is read-only; restore requires --restore and an existing snapshot.
The snapshot is stored locally, not committed to GitHub.
"""
import argparse
import json
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paho.mqtt.client as mqtt
import config
from markets.awtrix_markets import MARKETS, enabled_markets

SNAPSHOT = Path(__file__).resolve().parents[1] / "cache/market_tiles_backup.json"
PREFIX = config.AWTRIX_UID
TOPICS = [PREFIX + "/custom/" + MARKETS[n]["topic"] for n in enabled_markets()]

def connect():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if config.MQTT_USER:
        client.username_pw_set(config.MQTT_USER, config.MQTT_PASS)
    client.connect(config.MQTT_HOST, int(getattr(config, "MQTT_PORT", 1883)), 20)
    return client

def backup():
    messages = {}
    def connected(client, userdata, flags, reason, properties):
        if reason != 0:
            raise RuntimeError("MQTT connection refused")
        for topic in TOPICS:
            client.subscribe(topic, qos=1)
    def received(client, userdata, msg):
        if msg.retain and msg.topic in TOPICS and msg.payload:
            obj = json.loads(msg.payload)
            if not isinstance(obj, dict) or not isinstance(obj.get("text"), str):
                return
            messages[msg.topic] = obj
    client = connect()
    client.on_connect = connected
    client.on_message = received
    client.loop_start()
    try:
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline and len(messages) < len(TOPICS):
            time.sleep(0.1)
    finally:
        client.loop_stop()
        client.disconnect()
    if len(messages) != len(TOPICS):
        missing = sorted(set(TOPICS) - set(messages))
        raise RuntimeError("Missing retained tiles; no backup written: " + ", ".join(missing))
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(json.dumps({"uid": PREFIX, "tiles": messages},
                                   ensure_ascii=False, indent=2), encoding="utf-8")
    SNAPSHOT.chmod(0o600)
    print("Saved 4 retained tiles to", SNAPSHOT)

def restore():
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    if snapshot.get("uid") != PREFIX or set(snapshot.get("tiles", {})) != set(TOPICS):
        raise RuntimeError("Backup UID/topics mismatch; no restore performed")
    client = connect()
    client.loop_start()
    try:
        for topic in TOPICS:
            payload = json.dumps(snapshot["tiles"][topic], ensure_ascii=False)
            message = client.publish(topic, payload, qos=1, retain=True)
            message.wait_for_publish(timeout=10)
            if not message.is_published():
                raise RuntimeError("MQTT publish failed: " + topic)
        print("Restored four retained market tiles")
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--backup", action="store_true", help="Read-only MQTT snapshot")
    action.add_argument("--restore", action="store_true", help="Explicit MQTT restoration")
    args = parser.parse_args()
    if args.backup:
        backup()
    else:
        restore()
