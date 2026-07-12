import urllib.request
import xml.etree.ElementTree as ET
import subprocess
import json
import time
import html
import re

MQTT_HOST = "127.0.0.1"
MQTT_USER = "your_mqtt_user"
MQTT_PASS = "your_mqtt_password"
BASE_TOPIC = "awtrix_yourdevice/custom"

NEWS_SOURCES = [
    {
        "name": "france",
        "url": "https://www.lemonde.fr/politique/rss_full.xml",
        "color": "66CCFF",
    },
    {
        "name": "spiegel",
        "url": "https://www.spiegel.de/schlagzeilen/index.rss",
        "color": "FFCC00",
    },
    {
        "name": "bbc",
        "url": "https://feeds.bbci.co.uk/news/world/rss.xml",
        "color": "FFFFFF",
    },
    {
        "name": "cnn",
        "url": "http://rss.cnn.com/rss/edition_world.rss",
        "color": "FF4444",
    },
    # Reuters deaktiviert: feeds.reuters.com löst hier nicht auf.
]

COUNT_PER_SOURCE = 5
REFRESH_SECONDS = 900

def clean_text(text):
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def similar_key(text):
    t = text.lower()
    t = re.sub(r"[^a-z0-9äöüßéèêàçùâîôû]+", " ", t)
    words = [w for w in t.split() if len(w) > 3]
    return " ".join(words[:8])

def fetch_titles(url, limit=10):
    req = urllib.request.Request(url, headers={"User-Agent": "Vicky-AWTRIX-News/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = r.read()

    root = ET.fromstring(data)
    titles = []

    for item in root.findall(".//item"):
        title = clean_text(item.findtext("title"))
        if title and title not in titles:
            titles.append(title)
        if len(titles) >= limit:
            break

    return titles

def publish(topic_name, text, color):
    payload = {
        "text": text[:220],
        "duration": 20,
        "rainbow": False,
        "color": color
    }

    subprocess.run([
        "mosquitto_pub",
        "-h", MQTT_HOST,
        "-u", MQTT_USER,
        "-P", MQTT_PASS,
        "-t", f"{BASE_TOPIC}/{topic_name}",
        "-r",
        "-m", json.dumps(payload, ensure_ascii=False)
    ], check=False)

def clear_topic(topic_name):
    subprocess.run([
        "mosquitto_pub",
        "-h", MQTT_HOST,
        "-u", MQTT_USER,
        "-P", MQTT_PASS,
        "-t", f"{BASE_TOPIC}/{topic_name}",
        "-r",
        "-n"
    ], check=False)

def update_source(source, global_seen):
    try:
        raw_titles = fetch_titles(source["url"], COUNT_PER_SOURCE * 3)
        titles = []

        for title in raw_titles:
            key = similar_key(title)
            if key and key not in global_seen:
                global_seen.add(key)
                titles.append(title)
            if len(titles) >= COUNT_PER_SOURCE:
                break

        for i in range(COUNT_PER_SOURCE):
            topic = f"vicky_{source['name']}_{i+1}"
            if i < len(titles):
                publish(topic, titles[i], source["color"])
            else:
                clear_topic(topic)

    except Exception as e:
        publish(f"vicky_{source['name']}_1", f"RSS Fehler {source['name']}: {str(e)[:80]}", "FF0000")

def cleanup_old_topics():
    old = [
        "vicky_france_politique",
        "testplain",
        "testicon",
    ]
    for topic in old:
        clear_topic(topic)

def main():
    cleanup_old_topics()

    while True:
        global_seen = set()

        for source in NEWS_SOURCES:
            update_source(source, global_seen)

        time.sleep(REFRESH_SECONDS)

if __name__ == "__main__":
    main()
