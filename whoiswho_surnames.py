"""Conservative surname proposals without a fixed person registry.

Only mark a single-word surname after local AI proposes a full name,
Wikidata uniquely verifies the full name as a human. Ambiguous matches
are deliberately rejected.
When evidence is weak, return nothing.
"""
import json
import re
from urllib.request import Request, urlopen

from whoiswho_extract import URL, MODEL
from whoiswho_wikidata import lookup_person

def proposals(headline, lang):
    if len(headline.split()) < 5:
        return []
    body = {
        "model": MODEL, "temperature": 0, "max_tokens": 170,
        "messages": [
            {"role":"system","content":
             "Identify only single-word surnames referring to people in a news headline. "
             "Propose each person's full name. Exclude places, organizations, "
             "ordinary words and uncertain cases. Return a JSON object with a people "
             "array; each item has surface and full_name keys. "
             "When uncertain, return an empty people array."},
            {"role":"user","content":headline[:500]}
        ]
    }
    req = Request(URL, data=json.dumps(body).encode("utf-8"),
                  headers={"Content-Type":"application/json"}, method="POST")
    with urlopen(req, timeout=60) as response:
        text = json.load(response)["choices"][0]["message"]["content"]
    try:
        parsed = json.loads(text)
    except (ValueError, TypeError):
        return []
    people = parsed.get("people", []) if isinstance(parsed, dict) else []
    if not isinstance(people, list):
        return []
    result = []
    for item in people[:4]:
        if not isinstance(item, dict):
            continue
        surface, full = item.get("surface"), item.get("full_name")
        if not isinstance(surface, str) or not isinstance(full, str):
            continue
        surface, full = surface.strip(), " ".join(full.split())
        if not re.fullmatch(r"[^\W\d_][\w'-]{2,}", surface, re.UNICODE):
            continue
        if len(full.split()) < 2 or surface.casefold() not in {p.casefold().strip(".,") for p in full.split()}:
            continue
        # Never highlight a substring of a normal word.
        matches = list(re.finditer(r"(?<!\w)" + re.escape(surface) + r"(?!\w)", headline, re.I))
        if not matches:
            continue
        # Full name is a Qwen proposal, not literal headline text. Requiring
        # it to occur verbatim would incorrectly reject surname-only headlines.
        # With no context Wikidata accepts only a single exact human match.
        person = lookup_person(full, lang)
        if not person or not person.get("verified_human") or not person.get("description"):
            continue
        for match in matches:
            result.append((match.start(), match.end()))
    return result
