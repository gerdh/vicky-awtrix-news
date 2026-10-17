#!/usr/bin/env python3
"""Opt-in AWTRIX Who-is-Who: select button explains verified names on current Vicky page.

Conservative implementation: only names in a locally curated glossary are supported.
No speculative identity resolution and no remote API needed in the button handler.
"""
import json
import logging
import os
import re
import time
from pathlib import Path
import paho.mqtt.client as mqtt

ROOT = Path(__file__).resolve().parent
GLOSSARY = ROOT / "whoiswho_glossary.json"
import config

PREFIX = config.AWTRIX_UID
BROKER = config.MQTT_HOST
AUTH_USER = getattr(config, "MQTT_USER", "")
AUTH_PASS = getattr(config, "MQTT_PASS", "")
LANG = ROOT / "language_state.py"
LOG = logging.getLogger("vicky.whoiswho")
CACHE_SECONDS = 3600
ACTIVE_SECONDS = 20
headlines = {}
current_app = None
current_app_time = 0

def glossary():
    try:
        data = json.loads(GLOSSARY.read_text(encoding="utf-8"))
        return [row for row in data if isinstance(row, dict) and row.get("name") and row.get("explanations")]
    except (OSError, ValueError) as exc:
        LOG.warning("Glossary unavailable: %s", exc)
        return []

def language():
    try:
        from language_state import load_output_language
        value = load_output_language()
        return value if value in ("de", "fr", "en") else "de"
    except Exception:
        return "de"

def find_verified_name(text):
    for entry in sorted(glossary(), key=lambda x: len(x["name"]), reverse=True):
        name = entry["name"]
        if re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", text, re.IGNORECASE):
            if entry.get("verified") is True:
                return entry
    return None

def accept_app(app):
    return bool(re.fullmatch(r"vicky_news_[ab]_[1-5]", app or ""))

def handle(client, userdata, msg):
    global current_app, current_app_time
    suffix = msg.topic[len(PREFIX)+1:]
    try:
        payload = msg.payload.decode("utf-8")
    except UnicodeDecodeError:
        return
    if suffix == "stats":
        try:
            app = json.loads(payload).get("app")
        except (ValueError, AttributeError):
            return
        if isinstance(app, str):
            current_app, current_app_time = app, time.monotonic()
    elif suffix.startswith("custom/"):
        app = suffix[len("custom/"):]
        if not accept_app(app):
            return
        try:
            obj = json.loads(payload)
            value = obj.get("text", "") if isinstance(obj, dict) else ""
            if isinstance(value, list):
                value = "".join(str(part.get("t","")) for part in value if isinstance(part, dict))
            headlines[app] = (str(value), time.monotonic())
        except ValueError:
            return
    elif suffix == "stats/buttonSelect" and payload.strip() == "1":
        # Safety: refuse if current page is unknown/stale, instead of explaining
        # a different headline. AWTRIX stats are not a frame-accurate event.
        now = time.monotonic()
        if not accept_app(current_app) or now-current_app_time > ACTIVE_SECONDS:
            LOG.info("Select ignored: current news page unknown/stale")
            return
        item = headlines.get(current_app)
        if not item or now-item[1] > CACHE_SECONDS:
            LOG.info("Select ignored: no recent headline for %s", current_app)
            return
        entity = find_verified_name(item[0])
        if not entity:
            LOG.info("Select: no verified glossary match for %s", current_app)
            return
        lang = language()
        explanation = entity["explanations"].get(lang) or entity["explanations"].get("de")
        if not explanation:
            return
        message = {"text": entity["name"] + ": " + explanation, "duration": 15,
                   "color": "#FF4444", "textCase": 2, "stack": False}
        client.publish(PREFIX+"/notify", json.dumps(message, ensure_ascii=False), qos=0)
        LOG.info("Explained verified entry %s on %s", entity["name"], current_app)

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="vicky-whoiswho")
    if AUTH_USER:
        client.username_pw_set(AUTH_USER, AUTH_PASS)
    client.on_message = handle
    def connected(client, userdata, flags, reason_code, properties):
        if reason_code != 0:
            LOG.error("MQTT refused: %s", reason_code)
            return
        client.subscribe([(PREFIX+"/stats", 0),
                          (PREFIX+"/stats/buttonSelect", 0),
                          (PREFIX+"/custom/+", 0)])
    client.on_connect = connected
    client.connect(BROKER, int(getattr(config, "MQTT_PORT", 1883)), 60)
    client.loop_forever()

if __name__ == "__main__":
    main()
