import json
import re
from datetime import date, datetime
from pathlib import Path

from vicki import ask_vicki, clean


BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / "cache"
MEMORY_FILE = CACHE_DIR / "editor_memory_v5.json"
LANGUAGE_FILE = CACHE_DIR / "display_language.json"
BUTTON_FILE = Path("/tmp/vicky-news-force-refresh")

LANGUAGE_ORDER = ("fr", "de", "en")
LANGUAGE_NAMES = {
    "fr": "français",
    "de": "allemand",
    "en": "anglais",
}
LANGUAGE_LABELS = {
    "fr": "Français",
    "de": "Deutsch",
    "en": "English",
}


def normalize(text):
    text = clean(str(text)).lower()
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def unique_headlines(headlines):
    result = []
    seen = set()
    for headline in headlines:
        headline = clean(str(headline))
        key = normalize(headline)
        if headline and key and key not in seen:
            seen.add(key)
            result.append(headline)
    return result


def load_language():
    try:
        data = json.loads(LANGUAGE_FILE.read_text(encoding="utf-8"))
        language = str(data.get("language", "fr")).lower()
    except Exception:
        language = "fr"
    return language if language in LANGUAGE_ORDER else "fr"


def save_language(language):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    LANGUAGE_FILE.write_text(
        json.dumps(
            {
                "language": language,
                "label": LANGUAGE_LABELS[language],
                "updated_at": datetime.now().isoformat(timespec="seconds"),
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )


def rotate_language():
    current = load_language()
    next_index = (LANGUAGE_ORDER.index(current) + 1) % len(LANGUAGE_ORDER)
    language = LANGUAGE_ORDER[next_index]
    save_language(language)
    print(
        f"[Vicky] Display language: {LANGUAGE_LABELS[current]} -> "
        f"{LANGUAGE_LABELS[language]}",
        flush=True,
    )
    return language


def rotate_language_on_button_startup():
    """The existing middle-button helper creates BUTTON_FILE and restarts the service."""
    if BUTTON_FILE.exists():
        rotate_language()


# This runs during service startup, before awtrix_news_vicki.py consumes the file.
rotate_language_on_button_startup()


def load_memory():
    today = date.today().isoformat()
    try:
        memory = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        memory = {}

    if memory.get("date") != today:
        memory = {"date": today, "shown": []}
    if not isinstance(memory.get("shown"), list):
        memory["shown"] = []
    return memory


def save_memory(memory):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    memory["shown"] = memory.get("shown", [])[-100:]
    MEMORY_FILE.write_text(
        json.dumps(memory, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def recent_memory_text(memory, language):
    shown = [
        item for item in memory.get("shown", [])
        if item.get("language") == language
    ][-3:]
    topics = []
    for item in shown:
        topic = clean(str(item.get("topic", "")))
        if topic and topic not in topics:
            topics.append(topic)
    return ", ".join(topics) or "Aucun sujet récent."


def parse_editor_lines(raw, titles, maximum, language):
    messages = []
    seen_topics = set()
    seen_texts = set()
    used_indices = set()

    for raw_line in str(raw).splitlines():
        line = raw_line.strip().lstrip("-").strip()
        if not line or line.count("|") < 3:
            continue

        importance_raw, topic, indices_raw, final_text = [
            part.strip() for part in line.split("|", 3)
        ]
        topic = clean(topic)
        final_text = clean(final_text)
        if not final_text:
            continue

        try:
            importance = int(importance_raw)
        except (TypeError, ValueError):
            importance = 5

        indices = []
        for part in re.split(r"[,;\s]+", indices_raw):
            try:
                index = int(part)
            except (TypeError, ValueError):
                continue
            if 1 <= index <= len(titles) and index not in used_indices:
                indices.append(index)

        topic_key = normalize(topic or final_text)
        text_key = normalize(final_text)
        if not indices or not topic_key or topic_key in seen_topics or text_key in seen_texts:
            continue

        used_indices.update(indices)
        seen_topics.add(topic_key)
        seen_texts.add(text_key)
        messages.append({
            "topic": topic or "news",
            "category": "news",
            "importance": max(1, min(10, importance)),
            "text": final_text,
            "headlines": [titles[index - 1] for index in indices],
            "language": language,
        })
        if len(messages) >= maximum:
            break

    messages.sort(key=lambda item: item["importance"], reverse=True)
    return messages[:maximum]


def remember_messages(memory, messages, language):
    now = datetime.now().isoformat(timespec="seconds")
    for message in messages:
        memory["shown"].append({
            "topic": message.get("topic", ""),
            "text": message.get("text", ""),
            "headlines": message.get("headlines", []),
            "language": language,
            "shown_at": now,
        })
    save_memory(memory)


def edit_batch(titles, memory_text, maximum, language):
    numbered_titles = "\n".join(
        f"{index}. {title}" for index, title in enumerate(titles, start=1)
    )
    target_name = LANGUAGE_NAMES[language]

    prompt = f"""Tu es Vicky, rédactrice en chef d'un fil d'actualité pour un petit écran AWTRIX.

Analyse uniquement les titres fournis, quelle que soit leur langue d'origine.
Traduis et rédige CHAQUE résultat exclusivement en {target_name}.
Toutes les lignes d'un bulletin doivent être dans la même langue.

Règles strictes:
- conserve les noms, lieux, nombres et faits essentiels;
- n'ajoute aucune information absente des titres;
- regroupe uniquement les titres décrivant clairement le même événement;
- en cas de doute, garde les sujets séparés;
- écris une phrase courte, naturelle, neutre et précise;
- aucun Markdown, commentaire, préfixe ou guillemet;
- ne mélange jamais plusieurs langues dans une même réponse.

Informations déjà diffusées dans cette langue:
{memory_text}

Réponds avec au maximum {maximum} lignes.
Format obligatoire:
importance|sujet|numéros|texte final en {target_name}

Titres:
{numbered_titles}
"""

    raw = ask_vicki(prompt, timeout=180, max_tokens=300)
    return parse_editor_lines(raw, titles, maximum, language)


def vicki_topic_edit(headlines, max_topics=6):
    titles = unique_headlines(headlines)[:18]
    if not titles:
        return []

    language = load_language()
    memory = load_memory()
    memory_text = recent_memory_text(memory, language)
    all_messages = []

    for batch in (titles[:9], titles[9:18]):
        if batch:
            all_messages.extend(
                edit_batch(
                    batch,
                    memory_text=memory_text,
                    maximum=3,
                    language=language,
                )
            )

    result = []
    seen_topics = set()
    seen_texts = set()
    for message in sorted(
        all_messages,
        key=lambda item: item.get("importance", 5),
        reverse=True,
    ):
        topic_key = normalize(message.get("topic", ""))
        text_key = normalize(message.get("text", ""))
        if topic_key in seen_topics or text_key in seen_texts:
            continue
        seen_topics.add(topic_key)
        seen_texts.add(text_key)
        result.append(message)
        if len(result) >= max_topics:
            break

    if result:
        remember_messages(memory, result, language)
        print(
            f"[Vicky] {len(result)} headline(s) in {LANGUAGE_LABELS[language]}",
            flush=True,
        )
    return result
