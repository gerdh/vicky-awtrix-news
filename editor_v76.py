"""Vicky V7.6 – mehrsprachige LLM-Redaktion mit sicherem Fallback."""

import logging
import re

from safe_news_editor import edit_items_safely
from vicki import ask_vicki, clean


log = logging.getLogger("vicky.editor_v76")


LANGUAGES = {
    "de": "Deutsch",
    "en": "English",
    "fr": "français",
}


def normalize(text):
    """Normalisierte Form für Dublettenprüfung."""
    text = clean(str(text)).lower()
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def complete_unit(text):
    """
    Prüft eine journalistische Einheit.

    Eine Einheit darf aus einem oder mehreren vollständigen
    Sätzen bestehen.
    """
    text = " ".join(str(text).split()).strip()

    if len(text) < 20:
        return ""

    # Typische Anzeichen einer abgeschnittenen Ausgabe.
    if re.search(r"(?:\.\.\.|…|[,;:–—-])$", text):
        return ""

    # Fehlenden Schlusspunkt ergänzen.
    if text[-1] not in ".!?":
        text += "."

    return text


def parse_numbers(value, maximum):
    """Liest gültige RSS-Titelnummern aus der LLM-Ausgabe."""
    result = []

    for match in re.findall(r"\d+", str(value)):
        number = int(match)

        if 1 <= number <= maximum and number not in result:
            result.append(number)

    return result


def build_prompt(titles, target_language, maximum):
    """Erzeugt den allgemeinen, sprachneutralen Redaktionsauftrag."""
    language_name = LANGUAGES[target_language]

    numbered_titles = "\n".join(
        f"{index}. {title}"
        for index, title in enumerate(titles, start=1)
    )

    return f"""
You are Vicky, a careful international news editor.

TARGET LANGUAGE
---------------
{language_name}

Write every output unit only in the requested target language.
Do not favour any language over another.

EDITORIAL TASK
--------------
Select up to {maximum} important and varied news topics.

Merge source headlines that describe the same event.
Prefer a diverse mix of regions, countries and subjects.
Prefer clarity over literal translation.

A journalistic unit may contain one or more complete sentences.
Keep every unit concise, natural and understandable for a general reader.

ACCURACY
--------
Use only information contained in the supplied headlines.
Never invent facts, causes, quotations or consequences.
Preserve important names, places, dates, quantities and numbers.
Remain neutral when the available information is uncertain.

READABILITY
-----------
Briefly explain an unfamiliar abbreviation, acronym, institution,
organisation or specialised term when this materially improves understanding.

Keep explanations short and natural.
Do not explain common or obvious terms.
Do not repeat the same explanation within the bulletin.
Do not add background information that cannot safely be derived
from the supplied headlines.

When useful, identify an important person briefly by role.

TIME
----
Avoid ambiguous relative expressions such as today, yesterday or tomorrow
when they could become misleading.
Prefer an explicit weekday or date when one is present in the source.

STYLE
-----
Use objective journalistic language.
Do not sensationalise.
Do not add opinions.
Do not use Markdown.
Do not add introductions or closing comments.
Never stop in the middle of a sentence.

OUTPUT FORMAT
-------------
Return one unit per line using exactly four fields:

importance|topic|headline numbers|unit

Rules:
- importance must be an integer from 1 to 10;
- topic must be a short country, region or subject label;
- headline numbers must refer to the numbered source headlines;
- separate multiple headline numbers with commas;
- unit may contain one or more complete sentences;
- do not put quotation marks around the unit;
- do not write anything outside the formatted lines.

SOURCE HEADLINES
----------------
{numbered_titles}
""".strip()


def parse_editor_response(raw, titles, maximum):
    """Wandelt die strukturierte LLM-Ausgabe in Vicky-Meldungen um."""
    messages = []
    seen_topics = set()
    seen_units = set()

    for raw_line in str(raw).splitlines():
        line = raw_line.strip()

        # Markdown-Aufzählungszeichen entfernen.
        line = re.sub(r"^[\-\*\s]+", "", line)

        if not line or "|" not in line:
            continue

        parts = [part.strip() for part in line.split("|", 3)]

        if len(parts) != 4:
            continue

        importance_raw, topic, numbers_raw, unit_raw = parts

        try:
            importance = int(importance_raw)
        except (TypeError, ValueError):
            continue

        importance = max(1, min(10, importance))
        topic = clean(topic)
        numbers = parse_numbers(numbers_raw, len(titles))
        unit = complete_unit(unit_raw)

        if not topic or not numbers or not unit:
            continue

        topic_key = normalize(topic)
        unit_key = normalize(unit)

        if topic_key in seen_topics or unit_key in seen_units:
            continue

        headlines = [
            titles[number - 1]
            for number in numbers
        ]

        messages.append({
            "topic": topic,
            "category": "news",
            "importance": importance,
            "text": unit,
            "headlines": headlines,
        })

        seen_topics.add(topic_key)
        seen_units.add(unit_key)

        if len(messages) >= maximum:
            break

    messages.sort(
        key=lambda item: item.get("importance", 5),
        reverse=True,
    )

    return messages[:maximum]


def edit_items_v76(items, maximum=8, target_language="fr"):
    """
    Erstellt ein Bulletin direkt in der gewählten Sprache.

    Bei LLM-Ausfall oder unbrauchbarer Ausgabe wird der sichere
    Editor für dieselbe Zielsprache verwendet.
    """
    target_language = str(target_language).lower().strip()

    def fallback():
        log.warning(
            "V7.6 sicherer Fallback für Sprache %s",
            target_language,
        )

        return edit_items_safely(
            items,
            maximum=maximum,
            target_language=target_language,
        )

    if target_language not in LANGUAGES:
        log.warning(
            "V7.6 unbekannte Zielsprache: %s",
            target_language,
        )
        return fallback()

    titles = []

    for item in items[:30]:
        title = clean(str(item.get("title", "")))

        if title:
            titles.append(title)

    if not titles:
        return []

    prompt = build_prompt(
        titles=titles,
        target_language=target_language,
        maximum=maximum,
    )

    try:
        raw = ask_vicki(
            prompt,
            timeout=180,
            max_tokens=700,
        )
    except Exception as error:
        log.warning(
            "V7.6 LLM nicht verfügbar: %s",
            error,
        )
        return fallback()

    messages = parse_editor_response(
        raw=raw,
        titles=titles,
        maximum=maximum,
    )

    minimum_required = min(3, maximum)

    if len(messages) < minimum_required:
        log.warning(
            "V7.6 LLM lieferte nur %s gültige Units",
            len(messages),
        )
        return fallback()

    log.info(
        "V7.6 LLM-Redaktion erfolgreich: %s Units auf %s",
        len(messages),
        target_language,
    )

    return messages
