import json
import re
from datetime import date, datetime
from pathlib import Path

from vicki import ask_vicki, clean


BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

MEMORY_FILE = CACHE_DIR / "editor_memory_v5.json"


def normalize(text):
    text = clean(str(text))
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def unique_headlines(headlines):
    result = []
    seen = set()

    for headline in headlines:
        headline = clean(str(headline))
        key = normalize(headline)

        if not headline or not key:
            continue

        if key in seen:
            continue

        seen.add(key)
        result.append(headline)

    return result



REGION_KEYWORDS = {
    "France": [
        "france", "français", "française", "paris", "elysée", "elysee",
        "macron", "bardella", "le pen", "assemblée nationale"
    ],
    "Allemagne": [
        "allemagne", "germany", "deutschland", "berlin", "merz",
        "bundestag", "bundesregierung", "vw", "volkswagen"
    ],
    "Europe": [
        "europe", "européen", "européenne", "union européenne",
        "bruxelles", "ue ", "nato", "otan", "italie", "italy",
        "pologne", "poland", "ukraine", "russie", "russia"
    ],
    "Moyen-Orient": [
        "iran", "israël", "israel", "gaza", "liban", "lebanon",
        "syrie", "syria", "irak", "iraq", "hormuz", "tehran", "téhéran"
    ],
    "Afrique": [
        "afrique", "africa", "nigeria", "soudan", "sudan",
        "congo", "rdc", "drc", "egypte", "egypt", "liberia"
    ],
    "Amérique du Nord": [
        "usa", "u.s.", "united states", "etats-unis", "états-unis",
        "canada", "toronto", "washington", "new york", "trump",
        "sénat américain", "senator"
    ],
    "Amérique latine": [
        "argentine", "argentina", "brésil", "brazil", "mexique",
        "mexico", "colombie", "colombia"
    ],
    "Asie": [
        "chine", "china", "japon", "japan", "inde", "india",
        "corée", "korea", "taiwan"
    ],
    "Océanie": [
        "australie", "australia", "nouvelle-zélande", "new zealand"
    ],
}


def guess_region(title):
    text = normalize(title)

    matches = []

    for region, keywords in REGION_KEYWORDS.items():
        score = sum(
            1
            for keyword in keywords
            if normalize(keyword) in text
        )

        if score:
            matches.append((score, region))

    if not matches:
        return "International"

    matches.sort(reverse=True)
    return matches[0][1]

def load_memory():
    today = date.today().isoformat()

    try:
        memory = json.loads(
            MEMORY_FILE.read_text(encoding="utf-8")
        )
    except Exception:
        memory = {}

    if memory.get("date") != today:
        memory = {
            "date": today,
            "shown": [],
        }

    if not isinstance(memory.get("shown"), list):
        memory["shown"] = []

    return memory


def save_memory(memory):
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    memory["shown"] = memory.get("shown", [])[-100:]

    MEMORY_FILE.write_text(
        json.dumps(
            memory,
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )


def parse_editor_lines(raw, titles, maximum):
    """
    Erwartetes KI-Format:
    Wichtigkeit|Thema|Titelnummern|Französischer Meldungstext

    Beispiel:
    9|Iran|3,4,5|Les Etats-Unis ont mené de nouvelles frappes en Iran.
    """
    messages = []
    seen_topics = set()
    seen_texts = set()
    used_indices = set()

    for raw_line in str(raw).splitlines():
        line = raw_line.strip().lstrip("-").strip()

        if not line or line.count("|") < 3:
            continue

        importance_raw, topic, indices_raw, final_text = [
            part.strip()
            for part in line.split("|", 3)
        ]

        topic = clean(topic)
        final_text = clean(final_text)

        if not final_text:
            continue

        try:
            importance = int(importance_raw)
        except (TypeError, ValueError):
            importance = 5

        headline_indices = []

        for part in re.split(r"[,;\s]+", indices_raw):
            if not part:
                continue

            try:
                index = int(part)
            except ValueError:
                continue

            if 1 <= index <= len(titles):
                headline_indices.append(index)

        # Ohne Originaltitel kann mark_published() später nichts markieren.
        if not headline_indices:
            continue

        topic_key = normalize(topic or final_text)
        text_key = normalize(final_text)

        if not topic_key or topic_key in seen_topics:
            continue

        if text_key in seen_texts:
            continue

        # Eine Originalheadline darf nur einer Meldung zugeordnet werden.
        available_indices = [
            index
            for index in headline_indices
            if index not in used_indices
        ]

        if not available_indices:
            continue

        used_indices.update(available_indices)
        seen_topics.add(topic_key)
        seen_texts.add(text_key)

        messages.append({
            "topic": topic or "actualité",
            "category": "actualité",
            "importance": max(1, min(10, importance)),
            "text": final_text,
            "headlines": [
                titles[index - 1]
                for index in available_indices
            ],
        })

        if len(messages) >= maximum:
            break

    messages.sort(
        key=lambda item: item["importance"],
        reverse=True,
    )

    return messages[:maximum]


def remember_messages(memory, messages):
    now = datetime.now().isoformat(timespec="seconds")

    for message in messages:
        memory["shown"].append({
            "topic": message.get("topic", ""),
            "text": message.get("text", ""),
            "headlines": message.get("headlines", []),
            "shown_at": now,
        })

    save_memory(memory)


def recent_memory_text(memory):
    shown = memory.get("shown", [])[-3:]

    if not shown:
        return "Aucun sujet récent."

    topics = []

    for item in shown:
        topic = clean(str(item.get("topic", "")))

        if topic and topic not in topics:
            topics.append(topic)

    return ", ".join(topics) or "Aucun sujet récent."


def edit_batch(titles, memory_text, maximum):
    numbered_titles = "\n".join(
        f"{index}. [{guess_region(title)}] {title}"
        for index, title in enumerate(titles, start=1)
    )

    prompt = f"""Tu es TRIXY, rédactrice en chef d'un fil d'actualité destiné à un petit écran AWTRIX.

Analyse uniquement les titres fournis.

Règles strictes:
- regroupe des titres uniquement s'ils décrivent clairement le même événement;
- les étiquettes entre crochets indiquent la région probable;
- ne regroupe jamais des régions, pays ou événements différents;
- en cas de doute, conserve les sujets séparés;
- conserve tous les faits essentiels, notamment les noms, lieux, nombres et quantités;
- n'ajoute aucune information absente des titres;
- n'invente rien;
- écris en français naturel, neutre et précis;
- chaque phrase doit être courte et directement compréhensible;
- évite les titres vagues, les jeux de mots et les formulations journalistiques inventées;
- aucun Markdown, aucun texte en gras, aucun commentaire;
- le champ sujet doit contenir un pays, une région ou un thème précis;
- la phrase française ne doit pas commencer par « Phrase française ».

Informations déjà diffusées:
{memory_text}

Réponds avec au maximum {maximum} lignes.

Format obligatoire, une ligne par sujet:
importance|sujet|numéros|phrase française

Contraintes:
- importance: entier de 1 à 10;
- sujet: pays, région ou thème court;
- numéros: numéros exacts des titres utilisés, séparés par des virgules;
- phrase française: une seule phrase courte, sans préfixe, sans guillemets et sans Markdown.

Exemples:
9|Iran|2,4|Les États-Unis ont mené de nouvelles frappes en Iran.
7|Libéria|6|Cinq personnes ont été inculpées après la saisie de plus de 200 kg de cocaïne.

Titres:
{numbered_titles}
"""

    raw = ask_vicki(
        prompt,
        timeout=180,
        max_tokens=260,
    )

    return parse_editor_lines(
        raw,
        titles=titles,
        maximum=maximum,
    )


def vicki_topic_edit(headlines, max_topics=6):
    titles = unique_headlines(headlines)[:18]

    if not titles:
        return []

    memory = load_memory()
    memory_text = recent_memory_text(memory)

    batches = [
        titles[:9],
        titles[9:18],
    ]

    all_messages = []

    for batch in batches:
        if not batch:
            continue

        messages = edit_batch(
            batch,
            memory_text=memory_text,
            maximum=3,
        )

        all_messages.extend(messages)

    # Doppelte Themen/Textausgaben aus beiden Gruppen entfernen.
    unique_messages = []
    seen_topics = set()
    seen_texts = set()

    for message in all_messages:
        topic_key = normalize(message.get("topic", ""))
        text_key = normalize(message.get("text", ""))

        if topic_key in seen_topics or text_key in seen_texts:
            continue

        seen_topics.add(topic_key)
        seen_texts.add(text_key)
        unique_messages.append(message)

    unique_messages.sort(
        key=lambda item: item.get("importance", 5),
        reverse=True,
    )

    result = unique_messages[:max_topics]

    if result:
        remember_messages(memory, result)

    return result
