import json
import re
import urllib.request

MODEL = "qwen2.5:3b"
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"

JUNK_PATTERNS = [
    "quiz", "testez vos connaissances", "recipe", "rezept", "kuchen",
    "shopping", "promi", "tv-tipps", "bildergalerie",
    "ce qu'il faut savoir", "what you need to know",
]

TOPIC_HINTS = [
    {"le pen", "bardella", "rn", "présidentielle", "condamnée"},
    {"lecornu", "peines", "agressions", "élus", "projet de loi", "gouvernement"},
    {"trump", "iran", "ceasefire", "grönland", "spanien", "spain"},
    {"nato", "otan", "missile", "raketen"},
]

def clean(text):
    text = re.sub(r"<[^>]+>", "", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text

def is_junk(text):
    low = clean(text).lower()
    return any(p in low for p in JUNK_PATTERNS)

def topic_key(text):
    low = clean(text).lower()

    for idx, hints in enumerate(TOPIC_HINTS):
        if any(h in low for h in hints):
            return f"topic_{idx}"

    names = re.findall(r"\b[A-ZÉÈÊÀÂÎÔÛÄÖÜ][a-zéèêàâîôûäöüß'-]{2,}\b", text)
    if names:
        return "name_" + "_".join(names[:2]).lower()

    words = re.findall(r"[a-zA-Zéèêàâîôûäöüß]{5,}", low)
    return "misc_" + "_".join(words[:2]) if words else "misc"

def group_headlines(headlines):
    groups = {}
    order = []

    for h in headlines:
        h = clean(h)
        if not h or is_junk(h):
            continue

        key = topic_key(h)
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(h)

    return [groups[k] for k in order]

def ask_vicki(prompt, timeout=120, max_tokens=160):
    data = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.0,
            "top_p": 0.3,
            "num_predict": 300,
            "num_ctx": 4096,
        }
    }

    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))["response"].strip()

def edit_group(group):
    if len(group) == 1:
        return group[0]

    prompt = """Tu es Vicki, rédactrice en chef.

Fusionne ces titres en UNE phrase factuelle.
Utilise seulement les faits présents.
N'invente rien.
Ne commente pas.
Garde la langue principale.
La phrase doit répondre: qui fait quoi, et à propos de quoi.

Titres:
"""
    for i, h in enumerate(group, 1):
        prompt += f"{i}. {h}\n"

    prompt += "\nPhrase finale:\n"

    out = ask_vicki(prompt)
    return clean(out.splitlines()[0])

def vicki_edit(headlines, max_items=8):
    groups = group_headlines(headlines)
    results = []

    for group in groups:
        try:
            text = edit_group(group)
            if text:
                results.append(text)
        except Exception as e:
            results.append("Vicki error: " + str(e)[:80])

        if len(results) >= max_items:
            break

    return results

if __name__ == "__main__":
    test = [
        "Marine Le Pen condamnée en appel.",
        "Marine Le Pen lance sa campagne présidentielle.",
        "Jordan Bardella soutient sa candidature.",
        "Sébastien Lecornu veut tripler les peines.",
        "Le projet concerne les agressions contre les élus.",
        "Le gouvernement présente aujourd'hui son projet de loi.",
        "Quiz du jour : testez vos connaissances.",
    ]

    print("GROUPS:")
    for g in group_headlines(test):
        print("-", g)

    print("\nRESULT:")
    for line in vicki_edit(test):
        print("-", line)

# ============================================================
# Vicky GPU backend – llama.cpp / Ministral 3 3B
# Spätere Definition überschreibt die frühere Ollama-Funktion.
# ============================================================

LLAMA_API_URL = "http://127.0.0.1:8080/v1/chat/completions"
LLAMA_MODEL = "vicky"


def ask_vicki(prompt, timeout=120, max_tokens=160):
    import json
    import urllib.request
    import urllib.error

    # Ministral erhält den Prompt unverändert.
    full_prompt = str(prompt).strip()

    payload = {
        "model": LLAMA_MODEL,
        "messages": [
            {
                "role": "user",
                "content": full_prompt,
            }
        ],
        "temperature": 0,
        "max_tokens": max_tokens,
        "stream": False,
    }

    request = urllib.request.Request(
        LLAMA_API_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))

    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"llama.cpp HTTP {exc.code}: {details[:500]}"
        ) from exc

    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"llama.cpp nicht erreichbar: {exc}"
        ) from exc

    try:
        message = result["choices"][0]["message"]
        text = message.get("content", "").strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(
            "Ungültige llama.cpp-Antwort: "
            + json.dumps(result, ensure_ascii=False)[:500]
        ) from exc

    if not text:
        reasoning = ""
        try:
            reasoning = message.get("reasoning_content", "").strip()
        except Exception:
            pass

        raise RuntimeError(
            "llama.cpp lieferte keinen Antworttext"
            + (f"; reasoning={reasoning[:200]}" if reasoning else "")
        )

    return text
