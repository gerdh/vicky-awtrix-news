"""Conservative surname proposals without a fixed person registry.

Only mark a single-word surname after local AI proposes a full name,
Wikidata verifies human candidates; headline context may disambiguate.
Uncertain cases are rejected.
When evidence is weak, return nothing.
"""
import json
import re
from urllib.request import Request, urlopen

from whoiswho_extract import URL, MODEL
from whoiswho_wikidata import lookup_person, request_json, API, ENTITY_API, human, choose_with_context
from urllib.parse import urlencode

def resolve_surname(surname, lang, headline=None):
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
    seen_ids = set()
    for row in rows:
        qid = row.get("id", "")
        label = row.get("label", "")
        # Only exact surname as final token; no substring matching.
        if not re.fullmatch(r"Q[1-9][0-9]*", qid):
            continue
        if not label or label.split()[-1].casefold() != surname.casefold() or qid in seen_ids:
            continue
        obj = request_json(ENTITY_API.format(qid)).get("entities", {}).get(qid, {})
        if human(obj):
            descriptions = obj.get("descriptions", {})
            desc = descriptions.get(lang, descriptions.get("en", {})).get("value", "")
            if desc:
                humans.append({"id": qid, "description": label + " — " + desc})
                seen_ids.add(qid)
    # Wikidata often returns only a family-name entry for a surname.
    # Search Wikipedia for full article titles and independently verify each
    # person through the existing strict Wikidata full-name lookup.
    if not humans:
        wiki_lang = lang if lang in ("de", "fr", "en") else "de"
        wiki_url = "https://" + wiki_lang + ".wikipedia.org/w/api.php?" + urlencode({
            "action": "query", "list": "search", "srsearch": surname,
            "srlimit": 20, "format": "json"
        })
        try:
            titles = request_json(wiki_url).get("query", {}).get("search", [])
        except (OSError, ValueError, KeyError):
            titles = []
        for item in titles:
            title = item.get("title", "")
            # Require a genuine full personal name, ending with the surname.
            if (not isinstance(title, str) or len(title.split()) < 2
                    or title.split()[-1].casefold() != surname.casefold()):
                continue
            person = lookup_person(title, wiki_lang)
            if person and person.get("verified_human") and person["id"] not in seen_ids:
                humans.append({"id": person["id"],
                               "description": person["name"] + " — " + person["description"]})
                seen_ids.add(person["id"])
    if len(humans) == 1:
        return humans[0]["id"]
    if len(humans) > 1 and headline:
        return choose_with_context(surname, headline, humans)
    return None

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
    # Small local models sometimes wrap the JSON object in a one-item list.
    if isinstance(parsed, list) and len(parsed) == 1 and isinstance(parsed[0], dict):
        parsed = parsed[0]
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
            confirmed = bool(resolve_surname(surface, lang, headline))
        if not confirmed:
            continue
        for match in matches:
            result.append((match.start(), match.end()))
    return result
