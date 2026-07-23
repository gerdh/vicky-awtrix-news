# Avalon Nano 3S module

The Avalon module is the first hardware-monitoring module in the Vicky 7.x line. It reads the miner's local CGMiner API and publishes a compact status message to AWTRIX through the existing MQTT display layer.

## Display

Example:

```text
Avalon: W:133 Hash:6 T:90° Fan:39% OK
```

- `W` is the integer power value reported by `MPO[...]`.
- `Hash` is TH/s, rounded down to an integer.
- `T` is average temperature in degrees Celsius, rounded down.
- `Fan` is fan duty in percent, rounded down.
- Status is `OK`, `WARN`, `HOT`, or `OFFLINE`.

The module polls every 60 seconds by default. It publishes only when at least one displayed integer or the status changes.

## Supported Nano 3S fields

The tested Nano 3S firmware exposes most telemetry inside the `MM ID0` string returned by the `stats` command:

```text
MPO[133] GHSspd[6504.95] TAvg[90] FanR[39%] HW[0]
```

Vicky reads:

- power from `MPO`; the final value in `PS[...]` is used as a fallback;
- hashrate from standard CGMiner summary fields, or `GHSspd`, `GHSavg`, or `MGHS`;
- temperature from `TAvg`;
- fan percentage from `FanR`.

## Test the API

Replace the example address with the miner's local address:

```bash
printf '{"command":"summary"}' | nc -w 3 192.0.2.10 4028 | tr '\0' '\n'
printf '{"command":"stats"}'   | nc -w 3 192.0.2.10 4028 | tr '\0' '\n'
printf '{"command":"pools"}'   | nc -w 3 192.0.2.10 4028 | tr '\0' '\n'
```

Do not expose port 4028 to the public internet.

## Installation

From the repository directory:

```bash
cp avalon_config.example.py avalon_config.py
nano avalon_config.py
mkdir -p cache
python3 -m py_compile avalon.py avalon_layout.py avalon_display.py
python3 avalon.py
```

`avalon_config.py` is ignored by Git because it contains installation-specific network settings.

## systemd

Copy and edit the service template:

```bash
sudo cp systemd/avalon.service /etc/systemd/system/avalon.service
sudo nano /etc/systemd/system/avalon.service
sudo systemctl daemon-reload
sudo systemctl enable --now avalon.service
```

Set the correct user, group, working directory and script path before enabling it.

Useful commands:

```bash
sudo systemctl status avalon.service
journalctl -u avalon.service -f
sudo systemctl restart avalon.service
```

## Status rules

Defaults in `avalon_config.py`:

- `OK`: temperature below the warning threshold, sufficient hashrate, pool alive;
- `WARN`: temperature at or above 95 °C, hashrate below 4 TH/s, or pool unavailable;
- `HOT`: temperature at or above 100 °C;
- `OFFLINE`: the required miner telemetry cannot be read.

Thresholds are configurable.

## Troubleshooting

### AWTRIX shows OFFLINE while the miner is running

Inspect the service log. `OFFLINE` means a required query or telemetry field failed, not merely that a value stayed unchanged.

### The watt value is missing

Check for `MPO[...]` in the raw `stats` response. Firmware variants may use different fields; open an issue with a sanitized response if support is needed.

### The pickaxe icon displays incorrectly

The standard layout deliberately uses text only. Some AWTRIX fonts do not render the Unicode mining-pick symbol correctly.
