# Vicky 9.1.1

Vicky 9.1.1 is a focused news and button-control maintenance release for the
coordinated Montpellier/Orin and Davanod/Moon installations.

## News sources

The common feed catalogue adds three German-language sources:

- FAZ (`FAZ`)
- Süddeutsche Zeitung (`SZ`)
- Abendzeitung München (`AZ`)

They participate in the existing selection by freshness, importance and source
diversity. Vicky does not impose a German/French/English quota.

## Button contract

The established behavior remains unchanged:

- right AWTRIX button: cycle Vicky news language `FR → DE → EN → FR`
- left AWTRIX button: refresh Vicky news without changing language

The listener is now path-independent, resolves the local AWTRIX UID from the
local configuration, supports older configurations that contain only
`BASE_TOPIC`, and wakes the news service promptly after a button request.

## Stale-message cleanup

Vicky clears obsolete legacy news custom-app names during a news refresh and
dismisses a notification left pending by an older Vicky process. This cleanup
does not change native AWTRIX language or other device settings. A recurring
notification from Home Assistant or another external publisher must still be
removed at that external source.

## Upgrade on Moon

```bash
cd /home/gerd/vicky83
git fetch --tags origin
git switch --detach V9.1.1
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
bash scripts/install-vicky9-services.sh
sudo systemctl restart awtrix-news vicky-awtrix-button
```

Keep Davanod's local MQTT credentials, AWTRIX UID and Cerbo/GX SSH settings.
Never replace them with Montpellier values.
