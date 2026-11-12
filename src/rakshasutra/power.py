"""Wearable power budget and the cold-weather buzzer pulse (white paper, Section VI-C and Table V)."""
from __future__ import annotations

import math

from .params import P

DAYS_PER_MONTH = 365.25 / 12


def adv_event_ms(phy: str = "1m", payload_bytes: int = 15) -> float:
    """Milliseconds of transmission in one advertising event.

    "1m": legacy ADV_NONCONN_IND on the three primary channels at 1 Mbit/s.
    "coded": extended advertising on LE Coded PHY, S=8 (125 kbit/s): ADV_EXT_IND on the
    three primary channels, then one AUX_ADV_IND carrying the data.
    Packet lengths follow the Bluetooth Core Specification 5.1, Vol 6, Part B.
    """
    ad = 2 + payload_bytes                      # length, type 0xFF, payload
    if phy == "1m":
        pdu = 2 + 6 + ad                        # header, AdvA, AD structure
        return 3 * (1 + 4 + pdu + 3) * 8 / 1000.0
    if phy == "coded":
        def packet(pdu_bytes):                  # preamble 80, access address 256, CI 16, TERM1 24 microseconds
            return (376 + (pdu_bytes * 8 + 24 + 3) * 8) / 1000.0
        ext_ind = 2 + 1 + 1 + 2 + 3             # header, ext-header length, flags, ADI, AuxPtr
        aux_ind = 2 + 1 + 1 + 6 + 2 + ad        # header, ext-header length, flags, AdvA, ADI, AD structure
        return 3 * packet(ext_ind) + packet(aux_ind)
    raise ValueError("phy must be '1m' or 'coded'")


def budget(tx_ms: float | None = None, adv_interval_s: float | None = None) -> list[dict]:
    """Rows of Table V: state, peak current, on-time, period and mean current in microamps."""
    tx_ms = P["t_tx_ms"] if tx_ms is None else tx_ms
    adv = (P["adv_interval_s"] if adv_interval_s is None else adv_interval_s) * 1000.0
    rows = [
        dict(state="Sleep, 32.768 kHz clock and RAM retention", peak_ma=P["i_sleep_ua"] / 1000, on_ms=None,
             period_ms=None, mean_ua=P["i_sleep_ua"]),
        dict(state="Signed advertisement", peak_ma=P["i_tx_ma"], on_ms=tx_ms, period_ms=adv,
             mean_ua=P["i_tx_ma"] * 1000 * tx_ms / adv),
        dict(state="Scan window for a wake token", peak_ma=P["i_rx_ma"], on_ms=P["t_scan_ms"],
             period_ms=P["scan_period_ms"], mean_ua=P["i_rx_ma"] * 1000 * P["t_scan_ms"] / P["scan_period_ms"]),
        dict(state="AES-CMAC slot rotation", peak_ma=P["i_cmac_ma"], on_ms=P["t_cmac_ms"],
             period_ms=P["slot_seconds"] * 1000.0,
             mean_ua=P["i_cmac_ma"] * 1000 * P["t_cmac_ms"] / (P["slot_seconds"] * 1000.0)),
    ]
    return rows


def active_current_ua(**kw) -> float:
    return sum(r["mean_ua"] for r in budget(**kw))


def battery_life_months(cold: bool = False, active_hours: float | None = None, **kw) -> float:
    """Months until the cell is empty, at `active_hours` on the trek and the rest on the storage rack."""
    hours = P["active_hours"] if active_hours is None else active_hours
    daily_uah = hours * active_current_ua(**kw) + (24 - hours) * P["i_rack_ua"]
    capacity = P["battery_mah"] * (1 - P["battery_cold_derate"] if cold else 1.0)
    return capacity * 1000.0 / daily_uah / DAYS_PER_MONTH


def pulse_droop(capacitor_uf: float | None = None, pulse_ma: float | None = None, on_ms: float | None = None,
                off_ms: float | None = None, resistance_ohm: float | None = None,
                v_open: float | None = None) -> dict:
    """Lowest supply voltage while the buzzer and LED pulse in the cold.

    The cell is an ideal source behind its internal resistance R, with a hold-up capacitor C
    across the load. During a pulse of current I the supply falls towards V - I*R with time
    constant R*C, and recovers with the same time constant between pulses. The figure
    returned is the periodic steady state.
    """
    c = (P["holdup_uf"] if capacitor_uf is None else capacitor_uf) * 1e-6
    i = (P["i_pulse_ma"] if pulse_ma is None else pulse_ma) / 1000.0
    on = (P["pulse_on_ms"] if on_ms is None else on_ms) / 1000.0
    off = (P["pulse_off_ms"] if off_ms is None else off_ms) / 1000.0
    r = P["battery_r_cold_ohm"] if resistance_ohm is None else resistance_ohm
    v0 = P["battery_v_cold"] if v_open is None else v_open
    full = i * r
    if c <= 0:
        droop = full
    else:
        a, b = math.exp(-on / (r * c)), math.exp(-off / (r * c))
        droop = full * (1 - a) / (1 - a * b)       # droop at the end of each pulse, steady state
    return dict(full_droop_v=full, droop_v=droop, v_min=v0 - droop, time_constant_ms=r * c * 1000.0,
                brownout=(v0 - droop) < P["brownout_v"],
                mean_current_droop_v=full * on / (on + off))


def capacitor_needed_uf(**kw) -> float:
    """Smallest hold-up capacitor that keeps the supply above the brown-out voltage."""
    lo, hi = 0.0, 1e6
    if not pulse_droop(capacitor_uf=0.0, **kw)["brownout"]:
        return 0.0
    for _ in range(80):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if pulse_droop(capacitor_uf=mid, **kw)["brownout"] else (lo, mid)
    return hi


def max_pulse_ma_without_capacitor() -> float:
    return (P["battery_v_cold"] - P["brownout_v"]) / P["battery_r_cold_ohm"] * 1000.0
