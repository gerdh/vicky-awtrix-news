#!/usr/bin/env python3
"""Conservative Wikidata person lookup for Vicky Who-is-Who.

Only accepts an exact name and a single matching human entity; never guesses
identities from isolated surnames or news text. Independent of the live service.
"""
import json
import hashlib
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API = "https://www.wikidata.org/w/api.php"
ENTITY_API = "https://www.wikidata.org/wiki/Special:EntityData/{}.json"
AGENT = "VickyWhoIsWho/0.2 (personal AWTRIX assistant; wikidata lookup)"
CACHE = Path(__file__).resolve().parent / "cache" / "whoiswho_wikidata.json"
TTL = 7 * 86400

def request_json(url):
    req = Request(url, headers={"User-Agent": AGENT, "Accept": "application/json"})
    with urlopen(req, timeout=15) as response:
        return json.load(response)

def get_cache():
    try:
        data = json.loads(CACHE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}

def save_cache(data):
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    tmp = CACHE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, CACHE)

def human(entity):
    claims = entity.get("claims", {}).get("P31", [])
    for claim in claims:
        try:
            if claim["mainsnak"]["datavalue"]["value"]["id"] == "Q5":
                return True
        except (KeyError, TypeError):
            pass
    return False

def exact_label(entity, name):
    labels = entity.get("labels", {})
    aliases = entity.get("aliases", {})
    values = [x.get("value", "") for x in labels.values()]
    values += [v.get("value", "") for group in aliases.values() for v in group]
    return any(v.casefold() == name.casefold() for v in values)

def choose_with_context(name, headline, candidates):
    """AI advisory decision only; reject anything outside verified candidate IDs."""
    if not headline or name.casefold() not in headline.casefold():
        return None
    endpoint = os.environ.get(
        "VICKY_WHOISWHO_AI_URL", "http://127.0.0.1:8079/v1/chat/completions")
    if not endpoint.startswith("http://127.0.0.1:") and not endpoint.startswith("http://localhost:"):
        return None
    rows = []
    for item in candidates:
        rows.append(item["id"] + " | " + item["description"])
    prompt = (
        "Identify the named person in this news headline using context. "
        "Candidate descriptions are from Wikidata. "
        "Return ONLY the matching Q-ID or NONE. If the headline cannot "
        "distinguish candidates, return NONE. Never invent an ID.\n"
        "Name: " + name + "\nHeadline: " + headline + "\nCandidates:\n" +
        "\n".join(rows))
    payload = {"model": os.environ.get("VICKY_WHOISWHO_AI_MODEL", "local-model"),
               "temperature": 0, "max_tokens": 32,
               "messages": [{"role": "system", "content": "Reply with exactly one candidate Q-ID or NONE."},
                            {"role": "user", "content": prompt}]}
    req = Request(endpoint, data=json.dumps(payload).encode("utf-8"),
                  headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=30) as response:
            output = json.load(response)["choices"][0]["message"]["content"].strip()
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        return None
    ids = {row["id"] for row in candidates}
    return output if output in ids else None


def lookup_person(name, language="de", headline=None):
    """Resolve a full name; with context ask local AI only for ambiguous humans."""
    name = " ".join(name.split())
    if not (3 <= len(name) <= 90) or not re.fullmatch(r"[^\d<>]+", name):
        return None
    if language not in ("de", "fr", "en"):
        language = "de"
    context = " ".join((headline or "").split())[:350]
    # A headline consisting only of the name provides no disambiguating context.
    # Reject before consulting cached results so old AI guesses cannot bypass this.
    if context and context.casefold().strip(" .,;:!?") == name.casefold():
        return None
    cache_key = language + ":" + name.casefold()
    if context:
        cache_key += ":" + hashlib.sha256(context.encode("utf-8")).hexdigest()[:20]
    data = get_cache()
    entry = data.get(cache_key)
    if entry and time.time() - entry.get("ts", 0) < TTL:
        return entry.get("value")
    params = urlencode({"action": "wbsearchentities", "search": name,
                        "language": language, "format": "json", "limit": 10})
    results = request_json(API + "?" + params).get("search", [])
    exact = [x for x in results if x.get("label", "").casefold() == name.casefold()]
    accepted = []
    seen = set()
    for item in exact:
        qid = item.get("id", "")
        if not re.fullmatch(r"Q[1-9][0-9]*", qid) or qid in seen:
            continue
        seen.add(qid)
        obj = request_json(ENTITY_API.format(qid)).get("entities", {}).get(qid, {})
        if human(obj) and exact_label(obj, name):
            desc = obj.get("descriptions", {}).get(language, obj.get("descriptions", {}).get("en", {})).get("value", "")
            accepted.append({"id": qid, "entity": obj, "description": desc})
    chosen = None
    if len(accepted) == 1:
        chosen = accepted[0]
    elif len(accepted) > 1 and context:
        selected_id = choose_with_context(name, context, accepted)
        chosen = next((c for c in accepted if c["id"] == selected_id), None)
    answer = None
    if chosen:
        qid, obj = chosen["id"], chosen["entity"]
        labels = obj.get("labels", {})
        description = chosen["description"]
        if description:
            answer = {"id": qid,
                      "name": labels.get(language, labels.get("en", {})).get("value", name),
                      "description": description,
                      "url": "https://www.wikidata.org/wiki/" + qid,
                      "verified_human": True}
    # Only cache positive choices: NONE can change as descriptions or context improve.
    if answer:
        data[cache_key] = {"ts": time.time(), "value": answer}
        save_cache(data)
    return answer

if __name__ == "__main__":
    candidate = " ".join(sys.argv[1:]).strip()
    if not candidate:
        print("Usage: python whoiswho_wikidata.py 'Full Name'")
        raise SystemExit(2)
    try:
        print(json.dumps(lookup_person(candidate), ensure_ascii=False, indent=2))
    except Exception as exc:
        print("Wikidata lookup failed: " + str(exc), file=sys.stderr)
        raise SystemExit(1)
