"""Formatting and status rules for the Vicky 7 Avalon module."""

import math

from avalon_config import (
    COLOR_HOT,
    COLOR_OFFLINE,
    COLOR_OK,
    COLOR_WARN,
    HOT_TEMPERATURE,
    MINER_NAME,
    MINIMUM_HASHRATE_TH,
    WARN_TEMPERATURE,
)


def floor_value(value):
    return math.floor(float(value))


def determine_status(hashrate_th, temperature, pool_ok=True):
    if temperature >= HOT_TEMPERATURE:
        return "HOT", COLOR_HOT
    if temperature >= WARN_TEMPERATURE:
        return "WARN", COLOR_WARN
    if hashrate_th < MINIMUM_HASHRATE_TH or not pool_ok:
        return "WARN", COLOR_WARN
    return "OK", COLOR_OK


def build_display(power_w, hashrate_th, temperature, fan_percent, pool_ok=True):
    power = floor_value(power_w)
    hashrate = floor_value(hashrate_th)
    temp = floor_value(temperature)
    fan = floor_value(fan_percent)
    status, color = determine_status(hashrate, temp, pool_ok)

    text = (
        f"{MINER_NAME}: W:{power} Hash:{hashrate} "
        f"T:{temp}° Fan:{fan}% {status}"
    )
    values = {
        "power": power,
        "hash": hashrate,
        "temp": temp,
        "fan": fan,
        "status": status,
    }
    return text, color, values


def build_offline_display():
    return (
        f"{MINER_NAME}: OFFLINE",
        COLOR_OFFLINE,
        {"power": 0, "hash": 0, "temp": 0, "fan": 0, "status": "OFFLINE"},
    )
