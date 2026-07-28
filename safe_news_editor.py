#!/usr/bin/env python3

"""Safe deterministic message creation for Vicky."""

from offline_translator import translate_title


def edit_items_safely(items, maximum=6, target_language="fr"):
    messages = []

    for item in items[:maximum]:
        original = str(item.get("title", "")).strip()
        if not original:
            continue

        language = str(item.get("language", "")).strip().lower()
        translated = translate_title(original, language, target_language)

        try:
            importance = int(item.get("priority", 5))
        except (TypeError, ValueError):
            importance = 5

        messages.append({
            "topic": str(item.get("source", "actualité")),
            "category": "actualité",
            "importance": max(1, min(10, importance)),
            "text": translated,
            "headlines": [original],
        })

    return messages
