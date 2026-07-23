#!/usr/bin/env python3
"""Vicky 7 Avalon Nano 3S monitor for AWTRIX.

Reads the CGMiner API once per minute and publishes only when one of the
integer display values changes.
"""

import json
import logging
import re
import socket
import time

from avalon_config import MINER_HOST, MINER_NAME, MINER_PORT, POLL_SECONDS, SOCKET_TIMEOUT
from avalon_display import publish_if_changed
from avalon_layout import build_display, build_offline_display

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
log = logging.getLogger("avalon")


def cgminer_request(command):
    request = json.dumps({"command": command}).encode("utf-8")
    with socket.create_connection((MINER_HOST, MINER_PORT), timeout=SOCKET_TIMEOUT) as connection:
        connection.settimeout(SOCKET_TIMEOUT)
        connection.sendall(request)
        chunks = []
        while True:
            try:
                chunk = connection.recv(65536)
            except socket.timeout:
                break
            if not chunk:
                break
            chunks.append(chunk)

    raw = b"".join(chunks).decode("utf-8", errors="replace").replace("\x00", "").strip()
    if not raw:
        raise RuntimeError(f"No response from {MINER_HOST}:{MINER_PORT}")
    return json.loads(raw)


def first_record(response, section):
    records = response.get(section, [])
    return records[0] if records else {}


def number_from_value(value):
    if isinstance(value, (int, float)):
        return float(value)
    if value is None:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", str(value))
    return float(match.group(0)) if match else None


def walk_strings(data):
    if isinstance(data, dict):
        for value in data.values():
            yield from walk_strings(value)
    elif isinstance(data, list):
        for value in data:
            yield from walk_strings(value)
    elif isinstance(data, str):
        yield data


def embedded_metric(data, names):
    for text in walk_strings(data):
        for name in names:
            patterns = (
                rf"\b{re.escape(name)}\s*\[\s*(-?\d+(?:\.\d+)?)",
                rf"\b{re.escape(name)}\s*[:=]\s*(-?\d+(?:\.\d+)?)",
            )
            for pattern in patterns:
                match = re.search(pattern, text, flags=re.IGNORECASE)
                if match:
                    return float(match.group(1))
    return None


def extract_hashrate_th(summary_response, stats_response):
    summary = first_record(summary_response, "SUMMARY")
    candidates = (
        ("THS 5s", 1.0), ("THS av", 1.0),
        ("GHS 5s", 0.001), ("GHS av", 0.001),
        ("MHS 5s", 0.000001), ("MHS av", 0.000001),
    )
    for key, multiplier in candidates:
        value = number_from_value(summary.get(key))
        if value is not None and value >= 0:
            return value * multiplier

    # Avalon Nano 3S firmware exposes GHSspd/GHSavg inside MM ID0.
    value = embedded_metric(stats_response, ("GHSspd", "GHSavg", "MGHS"))
    if value is not None:
        return value / 1000.0
    raise RuntimeError("Hashrate not found")


def extract_power_w(stats_response):
    # Nano 3S: MPO[133]. The final PS value carries the same watt figure.
    power = embedded_metric(stats_response, ("MPO",))
    if power is not None:
        return power

    for text in walk_strings(stats_response):
        match = re.search(r"\bPS\s*\[([^\]]+)\]", text, flags=re.IGNORECASE)
        if match:
            values = re.findall(r"-?\d+(?:\.\d+)?", match.group(1))
            if values:
                return float(values[-1])
    raise RuntimeError("Power value MPO/PS not found")


def extract_temperature(stats_response):
    value = embedded_metric(stats_response, ("TAvg", "MTavg", "Temp", "Temperature"))
    if value is None:
        raise RuntimeError("Temperature not found")
    return value


def extract_fan_percent(stats_response):
    value = embedded_metric(stats_response, ("FanR", "FanPercent"))
    if value is None:
        raise RuntimeError("Fan percentage not found")
    return value


def pool_is_alive(pools_response):
    pools = pools_response.get("POOLS", [])
    for pool in pools:
        status = str(pool.get("Status", "")).lower()
        stratum = str(pool.get("Stratum Active", "")).lower()
        if status in {"alive", "active"} or stratum in {"true", "yes", "1"}:
            return True
    return False


def read_avalon():
    summary = cgminer_request("summary")
    stats = cgminer_request("stats")
    try:
        pool_ok = pool_is_alive(cgminer_request("pools"))
    except Exception as error:
        # Miner telemetry remains valid when the optional pool query is unsupported.
        log.warning("Pool status unavailable: %s", error)
        pool_ok = True

    return {
        "power_w": extract_power_w(stats),
        "hashrate_th": extract_hashrate_th(summary, stats),
        "temperature": extract_temperature(stats),
        "fan_percent": extract_fan_percent(stats),
        "pool_ok": pool_ok,
    }


def run_once():
    values = read_avalon()
    text, color, display_values = build_display(
        values["power_w"], values["hashrate_th"], values["temperature"],
        values["fan_percent"], pool_ok=values["pool_ok"],
    )
    changed = publish_if_changed(text, color, display_values)
    log.info("Published: %s" if changed else "No change: %s", text)


def main():
    log.info(
        "%s display started: %s:%s, polling every %s seconds",
        MINER_NAME, MINER_HOST, MINER_PORT, POLL_SECONDS,
    )
    while True:
        started = time.monotonic()
        try:
            run_once()
        except Exception as error:
            log.exception("Avalon query failed: %s", error)
            text, color, values = build_offline_display()
            if publish_if_changed(text, color, values):
                log.warning("Published: %s", text)
        time.sleep(max(1, POLL_SECONDS - (time.monotonic() - started)))


if __name__ == "__main__":
    main()
