#!/usr/bin/env python3
"""Conservative Wikidata person lookup for Vicky Who-is-Who.

Only accepts an exact name and a single matching human entity; never guesses
identities from isolated surnames or news text. Independent of the live service.
"""
import json
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

def lookup_person(name, language="de"):
    name = " ".join(name.split())
    if not (3 <= len(name) <= 90) or not re.fullmatch(r"[^\d<>]+", name):
        return None
    if language not in ("de", "fr", "en"):
        language = "de"
    key = language + ":" + name.casefold()
    data = get_cache()
    entry = data.get(key)
    if entry and time.time() - entry.get("ts", 0) < TTL:
        return entry.get("value")
    params = urlencode({"action": "wbsearchentities", "search": name,
                        "language": language, "format": "json", "limit": 10})
    results = request_json(API + "?" + params).get("search", [])
    exact = [x for x in results if x.get("label", "").casefold() == name.casefold()]
    accepted = []
    for item in exact:
        qid = item.get("id", "")
        if not re.fullmatch(r"Q[1-9][0-9]*", qid):
            continue
        obj = request_json(ENTITY_API.format(qid)).get("entities", {}).get(qid, {})
        if human(obj) and exact_label(obj, name):
            accepted.append((qid, obj))
    # If names collide, refuse an automatic identification.
    answer = None
    if len(accepted) == 1:
        qid, obj = accepted[0]
        labels = obj.get("labels", {})
        descriptions = obj.get("descriptions", {})
        answer = {"id": qid, "name": labels.get(language, labels.get("en", {})).get("value", name),
                  "description": descriptions.get(language, descriptions.get("en", {})).get("value", ""),
                  "url": "https://www.wikidata.org/wiki/" + qid,
                  "verified_human": True}
        if not answer["description"]:
            answer = None
    data[key] = {"ts": time.time(), "value": answer}
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
