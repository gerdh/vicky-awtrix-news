"""Color only Wikidata-verified names; cache successes by complete headline."""
import hashlib
import json
import logging
import os
import re
import time
from pathlib import Path

from whoiswho_extract import extract_person_names
from whoiswho_wikidata import lookup_person

RED = "FF3333"
CACHE_FILE = Path(__file__).resolve().parent / "cache" / "whoiswho_names.json"
TTL = 7 * 86400
MAX_ENTRIES = 200

def _load():
    try:
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}

def _save(data):
    tmp = None
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = CACHE_FILE.with_name(CACHE_FILE.name + "." + str(os.getpid()) + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, CACHE_FILE)
    except OSError:
        if tmp:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass

def _key(headline, lang, surname_mode):
    raw = json.dumps([headline, lang, surname_mode], ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def _render(headline, color, candidates):
    candidates.sort(key=lambda x: (x[0], -(x[1] - x[0])))
    parts = []
    at = 0
    for start, end in candidates:
        if start < at:
            continue
        if start > at:
            parts.append({"t": headline[at:start], "c": color})
        parts.append({"t": headline[start:end], "c": RED})
        at = end
    if at < len(headline):
        parts.append({"t": headline[at:], "c": color})
    return parts if any(p["c"] == RED for p in parts) else headline

def cached_people(headline, lang):
    """Use identities saved by the publisher, including surname-mode results."""
    cache = _load()
    for surname_mode in (True, False):
        entry = cache.get(_key(headline, lang, surname_mode))
        if not isinstance(entry, dict):
            continue
        ts = entry.get("ts")
        if not isinstance(ts, (int, float)) or not 0 <= time.time() - ts < TTL:
            continue
        people = entry.get("people")
        if isinstance(people, list) and people and all(
            isinstance(p, dict) and p.get("verified_human") is True
            and re.fullmatch(r"Q[1-9][0-9]*", str(p.get("id", "")))
            and isinstance(p.get("name"), str) and p.get("description")
            for p in people
        ):
            return people
    return []


def resolve_people(headline, lang, surname_mode=False):
    """Return verified identities alongside their literal headline spans."""
    rows = []
    for name in extract_person_names(headline):
        person = lookup_person(name, lang, headline=headline)
        if not (person and person.get("verified_human") and person.get("description")):
            continue
        for match in re.finditer(r"(?<!\w)" + re.escape(name) + r"(?!\w)", headline, re.I):
            rows.append({"span": (match.start(), match.end()), "person": person})
    if surname_mode:
        from whoiswho_surnames import proposals
        try:
            rows.extend(proposals(headline, lang, with_people=True))
        except Exception as exc:
            logging.getLogger("vicky.whoiswho").warning("Surname lookup unavailable: %s", exc)
    rows.sort(key=lambda row: (row["span"][0], -row["span"][1]))
    return rows


def fragments(headline, color, lang):
    surname_mode = os.environ.get("VICKY_WHOISWHO_SURNAMES") == "1"
    key = _key(headline, lang, surname_mode)
    now = time.time()
    cache = _load()
    entry = cache.get(key)
    if isinstance(entry, dict):
        ts, spans = entry.get("ts"), entry.get("spans")
        if (isinstance(ts, (int, float)) and 0 <= now - ts < TTL
            and entry.get("people") and isinstance(spans, list) and spans
            and all(isinstance(p, list) and len(p) == 2
                    and all(type(v) is int for v in p)
                    and 0 <= p[0] < p[1] <= len(headline) for p in spans)):
            return _render(headline, color, [tuple(p) for p in spans])
    rows = resolve_people(headline, lang, surname_mode)
    candidates = [row["span"] for row in rows]
    people = []
    for row in rows:
        if row["person"]["id"] not in {p["id"] for p in people}:
            people.append(row["person"])
    if candidates:
        cache[key] = {"ts": now, "spans": [list(p) for p in candidates], "people": people}
        kept = [(k, v) for k, v in cache.items()
                if isinstance(v, dict) and isinstance(v.get("ts"), (int, float))
                and 0 <= now - v["ts"] < TTL]
        kept.sort(key=lambda kv: kv[1]["ts"])
        _save(dict(kept[-MAX_ENTRIES:]))
    return _render(headline, color, candidates)
