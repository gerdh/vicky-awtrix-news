# Vicky 9.1.2

Vicky 9.1.2 fixes source clustering after an AWTRIX button refresh and adds a
reproducible, optional local importance-sorter setup.

## Button bulletin source selection

The button refresh now selects the newest available headline from distinct
sources first. Only when fewer than five sources are available does it fill
remaining slots with additional headlines from those sources.

This is source diversity, not a language quota. The configured German, French
and English feeds continue to compete under the same freshness and priority
rules.

The button contract remains unchanged:

- right button: cycle Vicky news `FR → DE → EN → FR`, then refresh
- left button: refresh without changing the Vicky news language

## Optional local AI ranking

The final AI importance sorter is now opt-in. When explicitly enabled, it may
only reorder completed messages by numeric ID. It cannot alter headline text.
If the endpoint is missing or returns an invalid permutation, the existing
order is retained.

See [docs/LOCAL-AI-SORTER.md](docs/LOCAL-AI-SORTER.md) for the tested Davanod
Moon setup. All model, binary and service paths remain local to the site.

## Upgrade on Moon

Preserve local changes before switching releases. Do not automatically restore
an old `display.py` or `markets/awtrix_markets.py` over the release.

```bash
cd /home/gerd/vicky83
git fetch --tags origin
git switch --detach V9.1.2
python3 -m venv --clear .venv
.venv/bin/python -m pip install -r requirements.txt
bash scripts/install-vicky9-services.sh
sudo systemctl restart awtrix-news vicky-awtrix-button
```

An already-installed `/etc/systemd/system/awtrix-news.service.d/` drop-in is
preserved when the main service unit is reinstalled.
