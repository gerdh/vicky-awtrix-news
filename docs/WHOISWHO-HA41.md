# Vicky Who-is-Who – experimental opt-in on HA-41

This branch provides a **safe prototype** for the AWTRIX TC001 middle button
(`AWTRIX_UID/stats/buttonSelect`). It has not been field-tested on the user's device.
It does not alter existing news, markets or left/right-button services.

## Behavior
- Subscribes to the AWTRIX MQTT `stats` current-app report and Vicky custom news page topics.
- On a middle-button press (`1`), only explains an entity if the current news
  app and cached headline are both recently confirmed.
- Explains **only explicitly verified names** listed in `whoiswho_glossary.json`.
  This avoids guessing between people with the same name or hallucinating biographies.
- Sends a brief non-retained MQTT notification with a red label, in the saved
  Vicky language (DE, FR or EN).
- If nothing can be verified, it does nothing.
- It **does not yet paint individual names red in the scrolling headline**.
  AWTRIX supports color fragments but that requires a separate news-publisher
  integration with a validated entity index.
- AWTRIX stats timing is not frame-exact. A refresh or transition can race a
  button press; the listener errs on the side of showing no explanation.

## Install on HA-41, not MOON
Do not use the existing Vicky 9.1.3 installer, which expects Victron.

```bash
cd ~/vicky-awtrix-news
git fetch origin feature/whoiswho-middle-button
git switch feature/whoiswho-middle-button
.venv/bin/python -m pip install paho-mqtt
.venv/bin/python -m py_compile whoiswho.py
```

For **manual testing**, run the listener in a terminal:
```bash
cd ~/vicky-awtrix-news
.venv/bin/python whoiswho.py
```
Press middle while a Vicky headline with an explicitly verified glossary name
is currently active. Ctrl-C stops the test.

Only after successful manual testing, optionally create an isolated unit:
```ini
[Unit]
Description=Vicky Who-is-Who (experimental)
After=network-online.target docker.service
Wants=network-online.target

[Service]
User=gerd
WorkingDirectory=/home/gerd/vicky-awtrix-news
ExecStart=/home/gerd/vicky-awtrix-news/.venv/bin/python /home/gerd/vicky-awtrix-news/whoiswho.py
Restart=on-failure
RestartSec=15

[Install]
WantedBy=multi-user.target
```
Save this as `/etc/systemd/system/vicky-whoiswho.service`; then
`sudo systemctl daemon-reload && sudo systemctl enable --now vicky-whoiswho`.
Use `journalctl -u vicky-whoiswho -f` to diagnose; stop/disable to roll back.
Do **not** deploy the prototype until the middle-button telemetry has been
verified on the actual firmware 0.98 device.

## Next implementation steps
1. Confirm whether stats updates provide sufficiently accurate app identity
   for the actual AWTRIX firmware, or use explicit app transition events.
2. Build a Wikipedia/Wikidata-backed resolver with disambiguation, caching and
   reviewable sources. Only verified entities should be advertised as explorable.
3. Insert AWTRIX colored text fragments into the news publisher without changing
   headlines or their loop order; add regression tests for the two repeats,
   selected language and no-Victron site.
