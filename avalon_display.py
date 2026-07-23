"""AWTRIX publishing with persistent change detection."""

import json
import os
import tempfile

from avalon_config import AWTRIX_TOPIC, STATE_FILE
from display import publish


def load_last_values():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as handle:
            return json.load(handle).get("values")
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def save_last_values(values):
    directory = os.path.dirname(STATE_FILE) or "."
    os.makedirs(directory, exist_ok=True)
    fd, temporary_path = tempfile.mkstemp(prefix="avalon_", suffix=".json", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump({"values": values}, handle, ensure_ascii=False, indent=2)
        os.replace(temporary_path, STATE_FILE)
    finally:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)


def publish_if_changed(text, color, values):
    if load_last_values() == values:
        return False
    publish(AWTRIX_TOPIC, text, color=color, repeat=1)
    save_last_values(values)
    return True
