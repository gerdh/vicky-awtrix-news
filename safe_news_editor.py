#!/usr/bin/env python3

"""Safe deterministic message creation for Vicky."""

from ai_importance_sorter import sort_messages_by_ai_importance
from offline_translator import translate_title


def edit_items_safely(items, maximum=6, target_language="fr"):
    """Create finished messages, then optionally reorder them by AI importance.

    Translation and message creation remain unchanged.  The final AI pass can
    only reorder the completed message dictionaries; it cannot rewrite, add or
    remove news content.  If the AI endpoint is unavailable or returns an
    invalid permutation, the existing order is preserved.
    """

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

    # This is intentionally the final editorial step.  The AI sees only the
    # already-finished messages and may return only their ordering by numeric
    # ID.  sort_messages_by_ai_importance() validates an exact permutation and
    # reuses the original message objects, so no text can come back from the AI.
    return sort_messages_by_ai_importance(messages)
