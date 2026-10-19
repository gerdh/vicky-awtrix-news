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
from whoiswho_wikidata import lookup_person, request_json, API, ENTITY_API, human
from urllib.parse import urlencode

def resolve_surname(surname, lang):
    """Fail closed unless Wikidata returns exactly one plausible human.

    An API result list can be truncated: reject full result sets, which cannot
    support a unique-person claim. No manually curated identities.
    """
    params = urlencode({"action": "wbsearchentities", "search": surname,
                        "language": lang, "format": "json", "limit": 50})
    rows = request_json(API + "?" + params).get("search", [])
    if len(rows) >= 50:
        return None
    humans = []
    for row in rows:
        qid = row.get("id", "")
        label = row.get("label", "")
        # Only exact surname as final token; no substring matching.
        if not re.fullmatch(r"Q[1-9][0-9]*", qid):
            continue
        if not label or label.split()[-1].casefold() != surname.casefold():
            continue
        obj = request_json(ENTITY_API.format(qid)).get("entities", {}).get(qid, {})
        if human(obj):
            humans.append(qid)
            if len(humans) > 1:
                return None
    return humans[0] if len(humans) == 1 else None

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
        if surface.casefold() not in {p.casefold().strip(".,") for p in full.split()}:
            continue
        # Never highlight a substring of a normal word.
        matches = list(re.finditer(r"(?<!\w)" + re.escape(surface) + r"(?!\w)", headline, re.I))
        if not matches:
            continue
        # Full name is a Qwen proposal, not literal headline text. Requiring
        # it to occur verbatim would incorrectly reject surname-only headlines.
        # With no context Wikidata accepts only a single exact human match.
        if len(full.split()) >= 2:
            person = lookup_person(full, lang)
            confirmed = bool(person and person.get("verified_human"))
        else:
            confirmed = bool(resolve_surname(surface, lang))
        if not confirmed:
            continue
        for match in matches:
            result.append((match.start(), match.end()))
    return result
