"""Can an alert or a sighting keep up with someone who is moving? (white paper, Section V-C)."""
from __future__ import annotations

import math

from . import linkbudget, power
from .params import P


# ---------------------------------------------------------------- the Class A downlink trap
def class_a_delay_s() -> float:
    """Worst-case time before a Class A pole can reach a wearable: batch, confirm, downlink, connect."""
    return P["class_a_batch_s"] + P["class_a_confirm_s"] + P["class_a_downlink_s"] + P["class_a_gatt_s"]


def walked_m(seconds: float, speed_mps: float | None = None) -> float:
    return seconds * (P["walk_mps"] if speed_mps is None else speed_mps)


# ---------------------------------------------------------------- BLE frames in a crowd
def primary_packet_ms(phy: str = "coded") -> float:
    """Length of the one packet a scanner on a single primary channel must receive."""
    return power.adv_event_ms("1m") / 3 if phy == "1m" else (376 + (9 * 8 + 27) * 8) / 1000.0


def ble_frame_success(distance_m: float = 10.0, crowd: int = 0, phy: str = "coded",
                      adv_interval_s: float | None = None) -> float:
    """Chance a pole decodes one advertisement: enough signal, and no other wearable on air.

    `crowd` is the number of other wearables in range of the pole. Their advertisements
    arrive unsynchronised on the same primary channel (pure ALOHA with equal packets).
    """
    adv = P["adv_interval_s"] if adv_interval_s is None else adv_interval_s
    sens = P["ble_sens_1m_dbm"] if phy == "1m" else P["ble_sens_coded_dbm"]
    signal = linkbudget.delivery_probability(linkbudget.ble_margin_db(distance_m, sens))
    return signal * math.exp(-2.0 * crowd * primary_packet_ms(phy) / 1000.0 / adv)


# ---------------------------------------------------------------- electric vehicles
def ev_pass_s(speed_mps: float | None = None) -> float:
    """Seconds a passenger spends inside a pole's 25 m core zone."""
    return P["core_zone_m"] / (P["ev_mps"] if speed_mps is None else speed_mps)


def capture_probability(hits_required: int, adv_interval_s: float | None = None, frame_success: float = 1.0,
                        pass_s: float | None = None) -> float:
    """Chance a passenger is reported while crossing a pole's core zone.

    The advertisement phase is random, so a pass of length t holds floor(t/T) or
    floor(t/T)+1 frames; each is decoded independently with probability `frame_success`.
    """
    t = ev_pass_s() if pass_s is None else pass_s
    adv = P["adv_interval_s"] if adv_interval_s is None else adv_interval_s
    n0 = math.floor(t / adv)
    extra = t / adv - n0

    def at_least(n):
        return sum(math.comb(n, k) * frame_success ** k * (1 - frame_success) ** (n - k)
                   for k in range(hits_required, n + 1))
    return (1 - extra) * at_least(n0) + extra * at_least(n0 + 1)


# ---------------------------------------------------------------- Layer 1: band-to-band tether
def scan_hit_probability(window_s: float | None = None, phy: str = "coded",
                         adv_interval_s: float | None = None) -> float:
    """Chance one scan window of the parent tag contains a whole advertisement of the child band.

    The band advertises every T plus a random 0-10 ms; the parent tag does not know the
    phase. A window shorter than the packet hears nothing; a window longer than
    T + 10 ms + packet always hears one.
    """
    w = P["tether_scan_window_s"] if window_s is None else window_s
    adv = (P["adv_interval_s"] if adv_interval_s is None else adv_interval_s) + P["adv_delay_max_s"] / 2
    return max(0.0, min(1.0, (w - primary_packet_ms(phy) / 1000.0) / adv))


def tether_false_alarm(window_s: float | None = None, phy: str = "coded") -> float:
    """Chance that `tether_misses` scans in a row all miss a child who is standing next to the parent."""
    return (1.0 - scan_hit_probability(window_s, phy)) ** P["tether_misses"]


def tether_window_needed_s(phy: str = "coded") -> float:
    """Shortest scan window that cannot miss an in-range advertisement."""
    return P["adv_interval_s"] + P["adv_delay_max_s"] + primary_packet_ms(phy) / 1000.0


def parent_tag_scan_ua(window_s: float) -> float:
    """Mean current of the parent tag's tether scan."""
    return P["i_rx_ma"] * 1000.0 * window_s / P["tether_scan_period_s"]


def tether_alert_delay_s() -> float:
    return P["tether_misses"] * P["tether_scan_period_s"]


def rssi_gate_for_m(distance_m: float) -> float:
    """Median RSSI at a given distance: the gate a tag would need to treat that distance as 'gone'."""
    return linkbudget.ble_rx_dbm(distance_m)
