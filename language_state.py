#!/usr/bin/env python3

"""Persistent output-language selection for Vicky."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
STATE_FILE = BASE_DIR / "cache/output_language.json"
LANGUAGES = ("fr", "de", "en")
LANGUAGE_LABELS = {
    "fr": "FRANÇAIS",
    "de": "DEUTSCH",
    "en": "ENGLISH",
}


def load_output_language(path: str | Path = STATE_FILE) -> str:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        language = str(data.get("language", "")).lower().strip()
    except Exception:
        language = ""

    return language if language in LANGUAGES else "fr"


def save_output_language(
    language: str,
    path: str | Path = STATE_FILE,
) -> str:
    language = str(language).lower().strip()
    if language not in LANGUAGES:
        raise ValueError(f"unsupported output language: {language}")

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=str(target.parent),
        text=True,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump({"language": language}, handle, indent=2)
            handle.write("\n")
        os.replace(temporary_name, target)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise

    return language


def cycle_output_language(path: str | Path = STATE_FILE) -> str:
    current = load_output_language(path)
    index = LANGUAGES.index(current)
    next_language = LANGUAGES[(index + 1) % len(LANGUAGES)]
    return save_output_language(next_language, path)


def language_label(language: str) -> str:
    return LANGUAGE_LABELS.get(
        str(language).lower().strip(),
        LANGUAGE_LABELS["fr"],
    )
