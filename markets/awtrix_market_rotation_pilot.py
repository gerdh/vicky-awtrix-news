#!/usr/bin/env python3
"""Experimental market rotation: queue market apps every ~180 seconds.

Do NOT run concurrently with awtrix-markets. This script is a pilot, not
production: AWTRIX stats are periodic, not a frame-accurate end event.
--check is completely read-only; no MQTT connection is made.
"""
import argparse
import json
import logging
import time
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paho.mqtt.client as mqtt
import config
from markets.awtrix_markets import MARKETS, enabled_markets, fetch_json

LOG = logging.getLogger("vicky.market.rotation")
INTERVAL = 180
FETCH_INTERVAL = 300
PREFIX = config.AWTRIX_UID
TOPICS = {m["topic"] for m in MARKETS.values()}

class Rotation:
    def __init__(self, client, names):
        self.client = client
        self.names = names
        self.prices = {}
        self.last_fetch = 0
        self.next_batch = time.monotonic() + INTERVAL
        self.pending = set()
        self.seen = set()
        self.previous_app = None

    def publish(self, topic, payload):
        info = self.client.publish(
            f"{PREFIX}/custom/{topic}", payload, qos=1, retain=False)
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(f"MQTT publish failed: {info.rc}")

    def refresh_prices(self):
        for name in self.names:
            spec = MARKETS[name]
            try:
                price = spec["extract"](fetch_json(spec["url"]))
                self.prices[name] = price
            except Exception as exc:
                LOG.warning("%s fetch failed; using cached value: %s", name, exc)

    def app_event(self, app):
        if not isinstance(app, str):
            return
        if app in self.pending:
            self.seen.add(app)
        # Never remove the tile that AWTRIX reports as currently visible.
        # A periodic stats sample might skip a short tile altogether; in that
        # case leave it pending instead of risking an in-progress interruption.
        old = self.previous_app
        self.previous_app = app
        if old and old != app and old in self.seen and old in self.pending:
            self.publish(old, b"")
            self.pending.remove(old)
            self.seen.remove(old)
            LOG.info("Removed completed market %s", old)
        if not self.pending and self.seen == set():
            self.next_batch = max(self.next_batch, time.monotonic() + INTERVAL)

    def tick(self):
        now = time.monotonic()
        if now - self.last_fetch >= FETCH_INTERVAL:
            self.refresh_prices()
            self.last_fetch = now
        if now < self.next_batch or self.pending:
            return
        self.next_batch = now + INTERVAL
        for name in self.names:
            if name not in self.prices:
                continue
            spec = MARKETS[name]
            msg = {"text": spec["text"](self.prices[name]),
                   "color": spec["color"], "rainbow": False,
                   "repeat": 1}
            self.publish(spec["topic"], json.dumps(msg))
            self.pending.add(spec["topic"])
            LOG.info("Queued %s", spec["topic"])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true",
                        help="Read-only validation, without connecting to MQTT")
    parser.add_argument("--pilot", action="store_true",
                        help="Explicitly start experimental MQTT rotation")
    args = parser.parse_args()
    names = enabled_markets()
    if args.check:
        print(f"AWTRIX UID: {PREFIX}")
        print(f"Markets: {', '.join(names)}")
        print("Target: one market batch approximately every 180 seconds")
        print("Existing market publisher must be stopped before --pilot")
        print("AWTRIX stats may skip fast transitions; no exact guarantee")
        return
    if not args.pilot:
        parser.error("Use --check first; --pilot requires deliberate opt-in")
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                         client_id="vicky-markets-pilot")
    if config.MQTT_USER:
        client.username_pw_set(config.MQTT_USER, config.MQTT_PASS)
    state = Rotation(client, names)
    def connected(c, userdata, flags, reason_code, properties):
        if reason_code == 0:
            c.subscribe(PREFIX + "/stats")
        else:
            LOG.error("MQTT connection refused: %s", reason_code)
    def received(c, userdata, msg):
        try:
            state.app_event(json.loads(msg.payload).get("app"))
        except (ValueError, AttributeError):
            pass
    client.on_connect = connected
    client.on_message = received
    client.connect(config.MQTT_HOST, int(getattr(config, "MQTT_PORT", 1883)))
    client.loop_start()
    try:
        while True:
            state.tick()
            time.sleep(1)
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()
