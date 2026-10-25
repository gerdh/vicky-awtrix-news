# Vicky Who-is-Who: left button

This optional listener explains people on the current Vicky news page. The
left button cycles through the verified people. A Wikipedia introduction is
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
payloads, current `stats.app`, and `stats/buttonLeft` press payload `1`.
It refuses unknown/stale current apps rather than selecting another headline.
Check its log if a button press produces no explanation. The local name
extractor requires the existing local AI endpoint; cached identities do not.

## Button ownership

- Left (`buttonLeft`): Who-is-Who only, handled by `whoiswho.py`.
- Right (`buttonRight`): language switching, handled by `scripts/vicky-awtrix-button`.
- Middle (`buttonSelect`): neither service subscribes; existing behavior is untouched.

Left no longer refreshes news. No environment toggle is needed. Restart the
button service after updating its script, since an already running shell may
still have the old subscriptions. Run Who-is-Who manually first, then install
its persistent service using the news host's existing Python environment and
local configuration. Preserve local files before updating; do not switch branches
or overwrite the news publisher's local changes blindly.

## Validation

```bash
python3 -m unittest discover -s tests -p 'test_whoiswho_explanations.py'
```

Automated tests use fake people and mocked network/MQTT; they do not verify the
installed firmware, live button telemetry or service state. This fix does not
deploy or restart a running installation.
