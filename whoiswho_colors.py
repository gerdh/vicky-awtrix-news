"""Color only Wikidata-verified names; cache successes by complete headline."""
import hashlib
import json
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

def fragments(headline, color, lang):
    surname_mode = os.environ.get("VICKY_WHOISWHO_SURNAMES") == "1"
    key = _key(headline, lang, surname_mode)
    now = time.time()
    cache = _load()
    entry = cache.get(key)
    if isinstance(entry, dict):
        ts, spans = entry.get("ts"), entry.get("spans")
        if (isinstance(ts, (int, float)) and 0 <= now - ts < TTL
            and isinstance(spans, list) and spans
            and all(isinstance(p, list) and len(p) == 2
                    and all(type(v) is int for v in p)
                    and 0 <= p[0] < p[1] <= len(headline) for p in spans)):
            return _render(headline, color, [tuple(p) for p in spans])
    candidates = []
    for name in extract_person_names(headline):
        verified = lookup_person(name, lang, headline=headline)
        if not (verified and verified.get("verified_human")):
            continue
        for match in re.finditer(r"(?<!\w)" + re.escape(name) + r"(?!\w)",
                                 headline, flags=re.I):
            candidates.append((match.start(), match.end()))
    if surname_mode:
        try:
            from whoiswho_surnames import proposals
            candidates.extend(proposals(headline, lang))
        except Exception:
            pass
    if candidates:
        cache[key] = {"ts": now, "spans": [list(p) for p in candidates]}
        kept = [(k, v) for k, v in cache.items()
                if isinstance(v, dict) and isinstance(v.get("ts"), (int, float))
                and 0 <= now - v["ts"] < TTL]
        kept.sort(key=lambda kv: kv[1]["ts"])
        _save(dict(kept[-MAX_ENTRIES:]))
    return _render(headline, color, candidates)
