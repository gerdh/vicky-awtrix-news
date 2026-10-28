#!/usr/bin/env python3
"""Extract likely full person names from a headline using local Qwen.

No static list. Results are proposals, not verified identities. Pass each
candidate to Wikidata before marking or explaining it.
"""
import json
import os
import re
import sys
from urllib.request import Request, urlopen

URL = os.environ.get("VICKY_WHOISWHO_AI_URL", "http://127.0.0.1:8079/v1/chat/completions")
MODEL = os.environ.get("VICKY_WHOISWHO_AI_MODEL", "local-model")

def normalize_names(values, headline):
    """Repair split name tokens only when they are adjacent in the source text.

    These remain candidates: callers must still verify the identity via Wikidata.
    Never combine across punctuation, missing words or separate headlines.
    """
    names = [" ".join(v.split()) for v in values[:8] if isinstance(v, str)]
    singles = {n for n in names if len(n.split()) == 1 and n
               and len(n) <= 100 and any(c.isalpha() for c in n)
               and all(c.isalpha() or c in "-'’" for c in n)}
    if len(singles) >= 2:
        token = "(?:" + "|".join(re.escape(n) for n in
                                  sorted(singles, key=lambda n: (-len(n), n))) + ")"
        pattern = r"(?<!\w)" + token + r"(?:\s+" + token + r")+(?!\w)"
        names.extend(m.group(0) for m in re.finditer(pattern, headline, re.I))
    found = []
    seen = set()
    for name in names:
        if not 3 <= len(name) <= 100 or len(name.split()) < 2:
            continue
        if name.casefold() in seen:
            continue
        if re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", headline, re.I):
            found.append(name)
            seen.add(name.casefold())
    return found

def extract_person_names(headline):
    headline = " ".join(headline.split())[:500]
    if not headline:
        return []
    if not (URL.startswith("http://127.0.0.1:") or URL.startswith("http://localhost:")):
        raise ValueError("Local AI URL required")
    payload = {
        "model": MODEL, "temperature": 0, "max_tokens": 120,
        "messages": [
            {"role": "system", "content":
             "Extract complete person names explicitly written in the headline. "
             "Each complete name must be ONE string, never separate first and last names. "
             "Do not invent or complete names. Do not return places, organizations, "
             "jobs or surnames without first names. Return JSON only in exactly "
             "this format: {\"names\":[\"First Last\"]}. If none: {\"names\":[]}."},
            {"role": "user", "content": "Headline: " + headline}
        ]
    }
    req = Request(URL, data=json.dumps(payload).encode("utf-8"),
                  headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req, timeout=60) as response:
        answer = json.load(response)["choices"][0]["message"]["content"].strip()
    try:
        obj = json.loads(answer)
    except (ValueError, TypeError):
        match = re.search(r"\{[^{}]*\}", answer, re.S)
        if not match:
            return []
        try:
            obj = json.loads(match.group(0))
        except (ValueError, TypeError):
            return []
    # Local models occasionally wrap the requested JSON object in a list.
    if isinstance(obj, list) and len(obj) == 1 and isinstance(obj[0], dict):
        obj = obj[0]
    values = obj.get("names") if isinstance(obj, dict) else None
    if not isinstance(values, list):
        return []
    return normalize_names(values, headline)

if __name__ == "__main__":
    headline = " ".join(sys.argv[1:]).strip()
    if not headline:
        raise SystemExit("Usage: python whoiswho_extract.py 'Headline'")
    print(json.dumps({"names": extract_person_names(headline)}, ensure_ascii=False))
