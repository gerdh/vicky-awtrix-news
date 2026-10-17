#!/usr/bin/env python3
"""Finite, opt-in Montpellier AWTRIX market rotation trial.

Requires awtrix-markets stopped; restores retained market tiles on exit.
AWTRIX stats are sampled, so an exact three-minute interval is not guaranteed.
"""
import argparse
import json
import logging
import signal
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paho.mqtt.client as mqtt
import config
from markets.awtrix_markets import MARKETS, enabled_markets, fetch_json

ROOT = Path(__file__).resolve().parents[1]
BACKUP = ROOT / "cache/market_tiles_backup.json"
UID = config.AWTRIX_UID
NAMES = enabled_markets()
TOPICS = {MARKETS[n]["topic"] for n in NAMES}
INTERVAL = 180
log = logging.getLogger("market-trial")

def snapshot():
    data = json.loads(BACKUP.read_text(encoding="utf-8"))
    expected = {UID + "/custom/" + t for t in TOPICS}
    if data.get("uid") != UID or set(data.get("tiles", {})) != expected:
        raise RuntimeError("Snapshot UID or market topics mismatch; refusing to run")
    return data["tiles"]

def publish(client, topic, payload, retain):
    info = client.publish(UID + "/custom/" + topic, payload, qos=1, retain=retain)
    info.wait_for_publish(timeout=8)
    if not info.is_published():
        raise RuntimeError("MQTT publish failed: " + topic)

def restore(client, saved):
    for fulltopic, payload in saved.items():
        publish(client, fulltopic.split("/custom/", 1)[1],
                json.dumps(payload, ensure_ascii=False), True)
    log.info("Restored four original retained market tiles")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--minutes", type=int, default=8)
    args = parser.parse_args()
    saved = snapshot()
    print("Validated four saved tiles for", UID)
    if args.check:
        print("Read-only check OK. Trial requires stopped awtrix-markets.")
        return
    if not args.run or args.minutes < 4 or args.minutes > 30:
        parser.error("Use --run --minutes 8 (allowed 4..30) for explicit trial")
    active = subprocess.run(["systemctl", "is-active", "--quiet", "awtrix-markets.service"], check=False)
    if active.returncode == 0:
        parser.error("awtrix-markets.service is active. Stop it before --run.")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                         client_id="vicky-market-trial")
    if config.MQTT_USER:
        client.username_pw_set(config.MQTT_USER, config.MQTT_PASS)
    current = {"app": "", "at": 0}
    def on_message(c, userdata, msg):
        try:
            obj = json.loads(msg.payload)
            if isinstance(obj.get("app"), str):
                current.update(app=obj["app"], at=time.monotonic())
        except (ValueError, TypeError, AttributeError):
            pass
    client.on_message = on_message
    client.connect(config.MQTT_HOST, int(getattr(config, "MQTT_PORT", 1883)), 30)
    client.loop_start()
    try:
        client.subscribe(UID + "/stats")
        # The previous market publisher must be stopped manually. Its live
        # publications would otherwise race with this trial.
        # Clear retained market values so a restart cannot resurrect stale apps.
        for topic in TOPICS:
            publish(client, topic, b"", True)
        deadline = time.monotonic() + args.minutes * 60
        next_batch = time.monotonic() + 10
        pending = set()
        seen = set()
        previous = None
        last_fetch = 0
        prices = {}
        while time.monotonic() < deadline:
            now = time.monotonic()
            if now - last_fetch >= 300:
                for name in NAMES:
                    spec = MARKETS[name]
                    try:
                        price = spec["extract"](fetch_json(spec["url"]))
                        prices[name] = spec["text"](price)
                    except Exception as error:
                        log.warning("Price unavailable for %s: %s", name, error)
                        fallback = saved.get(UID + "/custom/" + spec["topic"], {})
                        if fallback.get("text"):
                            prices[name] = fallback["text"]
                last_fetch = now
            app = current["app"] if now - current["at"] < 20 else None
            if app in pending:
                seen.add(app)
            if previous and app and previous != app and previous in seen:
                # Remove only after AWTRIX reports a different foreground app.
                publish(client, previous, b"", False)
                pending.discard(previous)
                seen.discard(previous)
                log.info("Completed: %s", previous)
            if app:
                previous = app
            if not pending and now >= next_batch:
                for name in NAMES:
                    spec = MARKETS[name]
                    if name in prices:
                        topic = spec["topic"]
                        payload = json.dumps({"text": prices[name], "color": spec["color"],
                                              "repeat": 1, "rainbow": False})
                        publish(client, topic, payload, False)
                        pending.add(topic)
                        log.info("Queued %s", topic)
                next_batch = now + INTERVAL
            time.sleep(0.5)
        log.info("Trial finished; restoring previous market tiles")
    finally:
        try:
            restore(client, saved)
        finally:
            client.loop_stop()
            client.disconnect()

if __name__ == "__main__":
    main()
