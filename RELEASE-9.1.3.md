# Vicky 9.1.3

Vicky 9.1.3 completes the site-local Cerbo/GX SSH configuration path for
Davanod/Moon and Montpellier/Orin.

## Cerbo/GX configuration

The committed site profiles contain placeholders only. During local
configuration, Vicky asks for the site's Cerbo/GX host, SSH user and absolute
private-key path. These values are written to ignored local `config.py` and
`.vicky-site` files and are never shared between sites.

The generated `awtrix-victron.service` unit loads `.vicky-site` through
`EnvironmentFile=`. The Python client accepts those environment values, with
the generated local `config.py` as its direct-run fallback. There is no longer
a committed fallback Cerbo IP, SSH user or private-key path.

## Upgrade

After checking out `V9.1.3`, run the site configurator again because older
local files do not contain the three Cerbo/GX values:

```bash
# Run exactly one of these on the matching host:
bash scripts/configure-site.sh davanod
bash scripts/configure-site.sh montpellier

bash scripts/install-vicky9-services.sh
sudo systemctl restart awtrix-victron.service
systemctl --no-pager --full status awtrix-victron.service
journalctl -u awtrix-victron.service -n 50 --no-pager
```

Use the real values only at the local prompt. Do not edit the committed example
profiles with site addresses or key paths.
