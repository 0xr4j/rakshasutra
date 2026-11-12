"""LoRa time on air and pure-ALOHA loss for the IN865 band (white paper, Section V-A)."""
from __future__ import annotations

import math

MAC_OVERHEAD = 13          # LoRaWAN MHDR + FHDR + FPort + MIC around the application payload
MAX_APP_PAYLOAD_SF7 = 222  # IN865 DR5, repeater-compatible limit used in the paper
CHANNELS = 8
BW_HZ = 125_000


def symbol_time(sf: int = 7, bw_hz: int = BW_HZ) -> float:
    """Seconds per LoRa symbol."""
    return (2 ** sf) / bw_hz


def payload_symbols(phy_bytes: int, sf: int = 7, cr: int = 1, explicit_header: bool = True,
                    crc: bool = True, low_dr_opt: bool | None = None) -> int:
    """Number of payload symbols (Semtech AN1200.13). `cr` is 1..4 for coding rates 4/5..4/8."""
    de = (sf >= 11) if low_dr_opt is None else low_dr_opt
    num = 8 * phy_bytes - 4 * sf + 28 + (16 if crc else 0) - (0 if explicit_header else 20)
    return 8 + max(math.ceil(num / (4 * (sf - (2 if de else 0)))) * (cr + 4), 0)


def time_on_air(app_bytes: int, sf: int = 7, bw_hz: int = BW_HZ, cr: int = 1, preamble: int = 8,
                mac_overhead: int = MAC_OVERHEAD) -> float:
    """Eq. 7: seconds on air for a LoRaWAN uplink carrying `app_bytes` of application payload."""
    n = payload_symbols(app_bytes + mac_overhead, sf=sf, cr=cr)
    return symbol_time(sf, bw_hz) * (preamble + 4.25 + n)


def aloha_loss(load: float) -> float:
    """Pure ALOHA with equal frames: a frame is lost with probability 1 - exp(-2G)."""
    return 1.0 - math.exp(-2.0 * load)


def mixed_aloha_loss(streams: list[tuple[float, float]], channels: int = CHANNELS) -> list[float]:
    """Loss per stream when frames of different lengths share the channels.

    `streams` is a list of (frames per second, seconds on air). A frame of length T_i
    survives if no other frame starts within T_j before it or T_i after it on the same
    channel, so its loss is 1 - exp(-(rate_total * T_i + sum_j rate_j * T_j) / channels).
    With a single stream this reduces to 1 - exp(-2G).
    """
    rate = sum(r for r, _ in streams)
    air = sum(r * t for r, t in streams)
    return [1.0 - math.exp(-(rate * t + air) / channels) for _, t in streams]
