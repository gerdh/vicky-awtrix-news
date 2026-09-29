# Vicky 9.0

Vicky 9.0 introduces the coordinated two-site architecture.

## Sites

- Montpellier: original Nvidia Jetson Orin installation
- Davanod: Raspberry Pi 5 Moon installation

The sites are independent. Each uses a local MQTT broker and a different AWTRIX UID. Both AWTRIX devices may use `192.168.1.86` on their separate private LANs.

## Included

- shared source and release for both hardware platforms
- separate Montpellier/Orin and Davanod/Moon configuration profiles
- per-site installation guides
- local configuration generator that keeps credentials out of Git
- path-independent systemd service installer
- documented local-only duplicate diagnosis
- retained Vicky 8.3 market contract: EUR/USD, Gold and Brent, exactly two repetitions, explicit non-white colors

## Upgrade principle

Update both systems to the same Git release, run the matching site configuration, test locally and only then enable services. Never copy `config.py` from one site to the other.
