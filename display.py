import json
import subprocess
from config import MQTT_HOST, MQTT_USER, MQTT_PASS, BASE_TOPIC, MAX_DISPLAY_TEXT, DEFAULT_DURATION

def shorten(text, limit=MAX_DISPLAY_TEXT):
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    cut = text[:limit - 1].rstrip()
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut + "…"

def publish(
    topic,
    text,
    color="CCCCCC",
    duration=DEFAULT_DURATION,
    icon=None,
    repeat=None,
):
    payload = {
        "text": shorten(text),
        "duration": duration,
        "rainbow": False,
        "color": color,
    }

    if repeat is not None:
        payload.pop("duration", None)
        payload["repeat"] = repeat

    if icon is not None:
        payload["icon"] = icon

    subprocess.run([
        "mosquitto_pub",
        "-h", MQTT_HOST,
        "-u", MQTT_USER,
        "-P", MQTT_PASS,
        "-t", f"{BASE_TOPIC}/{topic}",
        "-r",
        "-m", json.dumps(payload, ensure_ascii=False),
    ], check=False)

def clear(topic):
    subprocess.run([
        "mosquitto_pub",
        "-h", MQTT_HOST,
        "-u", MQTT_USER,
        "-P", MQTT_PASS,
        "-t", f"{BASE_TOPIC}/{topic}",
        "-r",
        "-n",
    ], check=False)
