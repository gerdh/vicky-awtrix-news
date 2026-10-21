# Vicky Who-is-Who: right button

This optional listener explains people on the current Vicky news page. The
right button cycles through the verified people. A Wikipedia introduction is
preferred, with the Wikidata description as a fallback. No new news text is
invented. Unknown people produce no explanation.

Red-name rendering and explanations share verified identities in
`cache/whoiswho_names.json`, keyed by the exact displayed headline and language.
Surname-only headlines retain the person's Q-ID and full name. Old span-only
cache entries are rebuilt on the next news publication. Without an identity
cache, the listener uses the same full-name and surname resolver.

## Installation on the existing news host

Use the same checkout, user, local `config.py`, cache and Python environment
as the running news publisher. Do not copy credentials between sites.

```bash
.venv/bin/python -m pip install 'paho-mqtt>=2,<3'
.venv/bin/python whoiswho.py
```

The listener needs the publisher's retained `custom/vicky_news_[ab]_[1-5]`
payloads, current `stats.app`, and `stats/buttonRight` press payload `1`.
It refuses unknown/stale current apps rather than selecting another headline.
Check its log if a button press produces no explanation. The local name
extractor requires the existing local AI endpoint; cached identities do not.

## Avoid a conflicting language notification

The older button service also uses the right button for language. When running
Who-is-Who, set `VICKY_WHOISWHO_RIGHT=1` in that service's environment. Its
language action then moves to the middle button (`buttonSelect`); left remains
refresh. With the option unset, the old button behavior remains unchanged.

For an existing systemd installation, use `sudo systemctl edit
vicky-awtrix-button` and add:

```ini
[Service]
Environment=VICKY_WHOISWHO_RIGHT=1
```

Restart that button service after updating its script. Run Who-is-Who manually
first; only enable a persistent service after checking it on the actual AWTRIX.
Use the local news service's User, WorkingDirectory and Python interpreter for
that service, with `whoiswho.py` as its script. It must inherit any custom
`VICKY_WHOISWHO_AI_URL` / `VICKY_WHOISWHO_AI_MODEL` settings.

## Validation

```bash
python3 -m unittest discover -s tests -p 'test_whoiswho_explanations.py'
```

Automated tests use fake people and mocked network/MQTT; they do not verify the
installed firmware, live button telemetry or service state. This fix does not
deploy or restart a running installation.
