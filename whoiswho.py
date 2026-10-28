#!/usr/bin/env python3
"""Opt-in AWTRIX Who-is-Who: left button explains verified names on current Vicky page.

Dynamic Qwen name extraction + Wikidata identification. Each press cycles to the next person.
"""
import json
import logging
import os
import re
import time
import threading
from pathlib import Path
from whoiswho_extract import extract_person_names
from whoiswho_wikidata import lookup_person
from whoiswho_wikipedia import wikipedia_intro
import paho.mqtt.client as mqtt

ROOT = Path(__file__).resolve().parent
GLOSSARY = ROOT / "whoiswho_glossary.json"
import config

PREFIX = getattr(config, "AWTRIX_UID", "") or getattr(config, "BASE_TOPIC", "").removesuffix("/custom")
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
current_app_live = False
cycle_app = None
cycle_text = None
cycle_index = 0
busy = threading.Lock()

def language():
    try:
        from language_state import load_output_language
        value = load_output_language()
        return value if value in ("de", "fr", "en") else "de"
    except Exception:
        return "de"

def verified_people(text, lang):
    """Explain the identities used for red names, including surname-only names."""
    from whoiswho_colors import cached_people, resolve_people
    result = cached_people(text, lang)
    if result:
        return result
    # Legacy caches only held spans. Re-resolve once after upgrading.
    for row in resolve_people(text, lang, surname_mode=True):
        person = row["person"]
        if person["id"] not in {p["id"] for p in result}:
            result.append(person)
    return result

def accept_app(app):
    return bool(re.fullmatch(r"vicky_news_[ab]_[1-5]", app or ""))

def disconnected(client, userdata, flags, reason_code, properties):
    global current_app, current_app_time, current_app_live
    current_app, current_app_time, current_app_live = None, 0, False

def handle(client, userdata, msg):
    global current_app, current_app_time, current_app_live, cycle_app, cycle_text, cycle_index
    suffix = msg.topic[len(PREFIX)+1:]
    try:
        payload = msg.payload.decode("utf-8")
    except UnicodeDecodeError:
        return
    # Retained custom payloads are needed at startup, but retained telemetry
    # must not select an old page or replay a button press after reconnecting.
    if suffix.startswith("stats") and getattr(msg, "retain", False):
        return
    if suffix == "stats/currentApp":
        # AWTRIX sends this on changes, not periodically. A long scrolling
        # headline remains current until the next event or disconnection.
        current_app, current_app_time = payload.strip(), time.monotonic()
        current_app_live = True
    elif suffix == "stats":
        try:
            app = json.loads(payload).get("app")
        except (ValueError, AttributeError):
            return
        # Stats are a startup/older-firmware fallback. Once the change stream
        # is available it owns the selection, including non-news pages.
        if isinstance(app, str) and not current_app_live:
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
            if cycle_app == app and headlines.get(app, ("",))[0] != str(value):
                cycle_app, cycle_text, cycle_index = None, None, 0
            headlines[app] = (str(value), time.monotonic())
        except ValueError:
            return
    elif suffix == "stats/buttonLeft" and payload.strip() == "1":
        # Snapshot the displayed page before native left-button navigation
        # reports the next app. Do not reuse a news page after a market event.
        now = time.monotonic()
        if not accept_app(current_app) or (not current_app_live and now-current_app_time > ACTIVE_SECONDS):
            LOG.info("Left ignored: app=%s source=%s age=%.1fs", current_app,
                     "currentApp" if current_app_live else "stats", now-current_app_time)
            return
        item = headlines.get(current_app)
        if not item or now-item[1] > CACHE_SECONDS:
            LOG.info("Left ignored: no recent headline for %s", current_app)
            return
        text = item[0]
        lang = language()
        # Network/API requests must never block paho's MQTT callback: otherwise
        # stats and subsequent button events would become stale while Qwen runs.
        if not busy.acquire(blocking=False):
            LOG.info("Left ignored: previous lookup still running")
            return
        app_snapshot = current_app
        def explain():
            global cycle_app, cycle_text, cycle_index
            try:
                people = verified_people(text, lang)
                if not people:
                    LOG.info("Left: no verified person in %s", app_snapshot)
                    return
                if cycle_app != app_snapshot or cycle_text != text:
                    cycle_app, cycle_text, cycle_index = app_snapshot, text, 0
                person = people[cycle_index % len(people)]
                cycle_index = (cycle_index + 1) % len(people)
                try:
                    intro = wikipedia_intro(person["id"], lang)
                except Exception as exc:
                    LOG.warning("Wikipedia unavailable: %s", exc)
                    intro = None
                explanation = intro["text"] if intro else person["description"]
                # AWTRIX's repeat count takes precedence over duration for
                # scrolling text. Finish the full explanation once; duration
                # remains the fallback for text that fits without scrolling.
                message = {"text": person["name"] + ": " + explanation,
                           "repeat": 1, "duration": 15, "color": "#FF4444",
                           "textCase": 2, "stack": False}
                info = client.publish(PREFIX+"/notify",
                                      json.dumps(message, ensure_ascii=False), qos=0)
                LOG.info("Who-is-Who %s (%s) person %s/%s on %s; wikipedia=%s publish_rc=%s",
                         person["name"], person["id"], cycle_index or len(people),
                         len(people), app_snapshot, bool(intro), info.rc)
            except Exception as exc:
                LOG.warning("Who-is-Who lookup failed: %s", exc)
            finally:
                busy.release()
        threading.Thread(target=explain, daemon=True).start()

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if not PREFIX:
        raise ValueError("AWTRIX_UID or BASE_TOPIC is required")
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="vicky-whoiswho")
    if AUTH_USER:
        client.username_pw_set(AUTH_USER, AUTH_PASS)
    client.on_message = handle
    client.on_disconnect = disconnected
    def connected(client, userdata, flags, reason_code, properties):
        disconnected(client, userdata, None, None, None)
        if reason_code != 0:
            LOG.error("MQTT refused: %s", reason_code)
            return
        client.subscribe([(PREFIX+"/stats", 0),
                          (PREFIX+"/stats/currentApp", 0),
                          (PREFIX+"/stats/buttonLeft", 0),
                          (PREFIX+"/custom/+", 0)])
    client.on_connect = connected
    LOG.info("Who-is-Who: left=explanation; tracking stats/currentApp; uid=%s", PREFIX)
    client.connect(BROKER, int(getattr(config, "MQTT_PORT", 1883)), 60)
    client.loop_forever()

if __name__ == "__main__":
    main()
