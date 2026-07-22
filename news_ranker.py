#!/usr/bin/env python3
import json
import re
from pathlib import Path

PREFS_FILE = Path(__file__).resolve().parent / "preferences.json"

def normalize(text):
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def load_prefs():
    try:
        return json.loads(PREFS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {
            "important_topics": [],
            "avoid_topics": [],
            "source_priority": {}
        }

def score_item(item):
    prefs = load_prefs()
    title = normalize(item.get("title", ""))
    source = item.get("source", "")

    score = 0

    score += prefs.get("source_priority", {}).get(source, 0)

    for word in prefs.get("important_topics", []):
        if normalize(word) in title:
            score += 8

    for word in prefs.get("avoid_topics", []):
        if normalize(word) in title:
            score -= 20

    return score

def prioritize_items(items):
    return sorted(items, key=score_item, reverse=True)
