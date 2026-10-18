"""Format a Vicky headline with red Wikidata-verified person names.

Opt-in; no static person directory. Never mark an unverified name.
AWTRIX 3 supports text fragments as {"t": text, "c": hex}.
"""
import re
from whoiswho_extract import extract_person_names
from whoiswho_wikidata import lookup_person

RED = "FF3333"

def fragments(headline, color, lang):
    candidates = []
    for name in extract_person_names(headline):
        verified = lookup_person(name, lang, headline=headline)
        if not (verified and verified.get("verified_human")):
            continue
        for match in re.finditer(r"(?<!\w)" + re.escape(name) + r"(?!\w)",
                                 headline, flags=re.I):
            candidates.append((match.start(), match.end()))
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
