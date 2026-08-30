#!/usr/bin/env python3
"""Optional final AI ranking pass for already-finished Vicky messages.

The AI is never allowed to rewrite news text. It only receives numbered IDs and
finished display text and must return a permutation of those IDs. The caller
then reorders the original message dictionaries without modifying them.

If the local OpenAI-compatible endpoint is unavailable, times out, or returns
anything that is not an exact permutation of the supplied IDs, the original
order is returned unchanged.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Callable, Iterable

DEFAULT_URL = "http://127.0.0.1:8080/v1/chat/completions"


def _enabled() -> bool:
    value = os.environ.get("VICKY_AI_IMPORTANCE_SORT", "1").strip().lower()
    return value not in {"0", "false", "no", "off", "disabled"}


def _endpoint() -> str:
    return os.environ.get("VICKY_AI_IMPORTANCE_URL", DEFAULT_URL).strip()


def _model() -> str:
    return os.environ.get("VICKY_AI_IMPORTANCE_MODEL", "local-model").strip()


def _timeout() -> float:
    try:
        return max(1.0, float(os.environ.get("VICKY_AI_IMPORTANCE_TIMEOUT", "20")))
    except ValueError:
        return 20.0


def _prompt(messages: list[dict]) -> str:
    rows = []
    for index, message in enumerate(messages, start=1):
        text = str(message.get("text", "")).strip()
        rows.append(f"{index}: {text}")

    return (
        "Rank the following already-finished news messages from most important "
        "to least important for a general international news bulletin.\n\n"
        "IMPORTANT SAFETY RULES:\n"
        "- Do not rewrite, summarize, correct, merge, delete or add any news.\n"
        "- Do not return news text.\n"
        "- Return every numeric ID exactly once.\n"
        "- Output JSON only, in this exact shape: {\"order\":[3,1,2]}.\n"
        "- Judge only relative news importance; the text itself will never be "
        "taken from your response.\n\n"
        "Consider broad public impact, international significance, major "
        "political/economic/security consequences, scale, urgency and unusual "
        "events. Avoid giving extra weight merely because a headline is more "
        "sensational.\n\n"
        "MESSAGES:\n" + "\n".join(rows)
    )


def _extract_order(content: str) -> list[int] | None:
    content = str(content or "").strip()
    if not content:
        return None

    candidates = [content]
    match = re.search(r"\{.*\}", content, flags=re.DOTALL)
    if match and match.group(0) != content:
        candidates.append(match.group(0))

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        order = parsed.get("order") if isinstance(parsed, dict) else None
        if not isinstance(order, list):
            continue
        try:
            return [int(value) for value in order]
        except (TypeError, ValueError):
            continue
    return None


def _request_order(messages: list[dict]) -> list[int] | None:
    payload = {
        "model": _model(),
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a news-importance sorter. You must never rewrite "
                    "news. Your only output is the requested JSON ordering."
                ),
            },
            {"role": "user", "content": _prompt(messages)},
        ],
    }
    request = urllib.request.Request(
        _endpoint(),
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=_timeout()) as response:
        result = json.loads(response.read().decode("utf-8"))

    try:
        content = result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return None
    return _extract_order(content)


def sort_messages_by_ai_importance(
    messages: Iterable[dict],
    log: Callable[[str], None] | None = None,
) -> list[dict]:
    """Return the same message objects, optionally reordered by local AI."""

    original = list(messages)
    if len(original) < 2 or not _enabled():
        return original

    logger = log or (lambda message: print(message, flush=True))
    expected = list(range(1, len(original) + 1))

    try:
        order = _request_order(original)
    except (OSError, urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as error:
        logger(f"AI importance sort unavailable; keeping current order: {error}")
        return original
    except Exception as error:
        logger(f"AI importance sort failed; keeping current order: {error}")
        return original

    if order is None or len(order) != len(expected) or sorted(order) != expected:
        logger("AI importance sort returned invalid order; keeping current order")
        return original

    if order == expected:
        logger("AI importance sort completed: priority/order unchanged")
        return original

    sorted_messages = [original[index - 1] for index in order]

    if sorted(map(id, sorted_messages)) != sorted(map(id, original)):
        logger("AI importance sort safety check failed; keeping current order")
        return original

    logger("AI importance sort changed order to: " + ",".join(map(str, order)))
    return sorted_messages
