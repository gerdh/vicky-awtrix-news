# Vicky 9 two-site architecture

Vicky 9 coordinates two independent installations through one GitHub codebase.

| Site | Computer | Hardware | AWTRIX network | Runtime relationship |
|---|---|---|---|---|
| Montpellier | Orin | Nvidia Jetson Orin | local LAN | independent |
| Davanod | Moon | Raspberry Pi 5 | local LAN | independent |

Each site has its own MQTT broker and its own AWTRIX Light. Both AWTRIX devices may use the same private address `192.168.1.86` because the LANs are separate. They have different AWTRIX UIDs and are not connected to each other.

GitHub coordinates source code, tests, documentation and releases. It does not bridge runtime MQTT traffic between the sites.

## Invariants

- One local publisher per AWTRIX topic and site.
- `BASE_TOPIC=<local AWTRIX UID>/custom`.
- Local MQTT credentials and real AWTRIX UIDs are never committed.
- Market tiles are EUR/USD, Gold, Brent and NVIDIA.
- Every market tile sets `repeat: 2`.
- Market colors are explicit: EUR/USD `00FFFF`, Gold `FFD700`, Brent `FF8C00`, NVIDIA `76B900`.
- Neither site relies on the legacy Home Assistant endpoint `http://192.168.1.86/api/notify` for normal Vicky custom apps.
- Site and hardware differences live in local configuration, not separate drifting source branches.

## Duplicate-message rule

Since the sites are not connected, duplicate messages cannot originate from the other site. Check the affected site for multiple systemd services, manually started scripts, old Home Assistant REST automations, cron jobs or service restart loops.
