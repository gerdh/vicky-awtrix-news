#!/usr/bin/env python3
"""Retrieve a short Wikipedia introduction linked to a verified Wikidata Q-ID."""
import json
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen

HEADERS = {"User-Agent": "VickyWhoIsWho/0.3 (personal AWTRIX encyclopedia reader)",
           "Accept": "application/json"}

def get(url):
    with urlopen(Request(url, headers=HEADERS), timeout=15) as reply:
        return json.load(reply)

def wikipedia_intro(qid, language="de"):
    if not re.fullmatch(r"Q[1-9][0-9]*", str(qid)):
        return None
    if language not in ("de", "fr", "en"):
        language = "de"
    entity = get("https://www.wikidata.org/wiki/Special:EntityData/" + qid + ".json")
    sitelinks = entity.get("entities", {}).get(qid, {}).get("sitelinks", {})
    for lang in (language, "en"):
        item = sitelinks.get(lang + "wiki", {})
        title = item.get("title")
        if not title:
            continue
        args = urlencode({"action":"query", "format":"json", "prop":"extracts",
                          "exintro":"1", "explaintext":"1", "redirects":"1",
                          "titles":title})
        pages = get("https://" + lang + ".wikipedia.org/w/api.php?" + args).get("query", {}).get("pages", {})
        extract = next((v.get("extract", "") for v in pages.values() if v.get("extract")), "")
        extract = " ".join(extract.split())
        # Do not split at date ordinals such as "6. Mai" or "11. November".
        sentences = re.split(r"(?<!\d)(?<=[.!?])\s+(?=[A-ZÀ-ÝÄÖÜ])", extract)
        summary = " ".join(sentences[:3]).strip()
        if len(summary) > 480:
            prefix = summary[:480].rsplit(" ", 1)[0].rstrip(" ,;:")
            summary = prefix + "…"
        if summary:
            return {"text": summary, "url": "https://" + lang +
                    ".wikipedia.org/wiki/" + title.replace(" ", "_"), "language": lang}
    return None
