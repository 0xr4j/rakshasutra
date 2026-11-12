"""The pole's edge filter (white paper, Algorithm 2).

A pole hears every advertisement in range, several per second per wearable. This state
machine decides what little of that is worth LoRa airtime:

* an SOS frame is forwarded at once, whole, with one byte of signal strength appended so
  the server can tell which pole is nearest (at most 10 a minute, each pseudonym once);
* a wearable is reported once when it arrives, in chunks of at most 25 every 15 s;
* a wearable not heard for 90 s is reported as departed;
* every 60 s one 64-byte Bloom filter says who is still here.

The same logic is implemented in C in firmware/rakshasutra_pole/rs_core.c and the two
are compared byte for byte in tests/test_firmware.py.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .bloom import BloomFilter
from .params import P
from .protocol import COMPANY_ID, F_SOS, FRAME_LEN

FPORT_ARRIVALS, FPORT_DEPARTURES, FPORT_HEARTBEAT, FPORT_SOS = 1, 2, 3, 10


@dataclass
class Uplink:
    fport: int
    payload: bytes
    confirmed: bool = False


@dataclass
class _Entry:
    rssi: float
    hits: int
    last_seen: float
    counter: int
    flags: int
    reported: bool = False


def encode_rssi(rssi_dbm: float) -> int:
    """RSSI as one byte: the magnitude in dB, clamped to 0..255 (so -72.4 dBm is sent as 72)."""
    return max(0, min(255, int(math.floor(-rssi_dbm + 0.5))))


@dataclass
class PoleEdgeFilter:
    hits_required: int = 1
    rssi_gate_dbm: float = P["rssi_gate_track_dbm"]
    table_size: int = P["active_table"]
    table: dict = field(default_factory=dict)          # rolling_id -> _Entry
    arrivals: list = field(default_factory=list)       # 8-byte tuples waiting for the next flush
    departures: list = field(default_factory=list)     # 4-byte pseudonyms waiting for the next flush
    sos_times: list = field(default_factory=list)
    sos_seen: dict = field(default_factory=dict)       # rolling_id -> time forwarded (not repeated for 90 s)
    dropped_full: int = 0

    def on_advertisement(self, payload: bytes, rssi_dbm: float, now: float) -> Uplink | None:
        """Feed one received advertisement. Returns an SOS uplink if one must go out now."""
        if len(payload) != FRAME_LEN or int.from_bytes(payload[0:2], "little") != COMPANY_ID:
            return None
        rid, counter, flags = bytes(payload[5:9]), int.from_bytes(payload[3:5], "little"), payload[9]
        out = None
        if flags & F_SOS:
            self.sos_times = [t for t in self.sos_times if now - t < 60.0]
            fresh = now - self.sos_seen.get(rid, -1e18) >= P["depart_timeout_s"]
            if len(self.sos_times) < P["sos_per_minute"] and fresh:
                self.sos_times.append(now)
                self.sos_seen[rid] = now
                out = Uplink(FPORT_SOS, bytes(payload) + bytes([encode_rssi(rssi_dbm)]), confirmed=True)
        if rssi_dbm < self.rssi_gate_dbm:
            return out
        e = self.table.get(rid)
        if e is None:
            if len(self.table) >= self.table_size:
                self.dropped_full += 1
                return out
            e = self.table[rid] = _Entry(rssi=rssi_dbm, hits=0, last_seen=now, counter=counter, flags=flags)
        else:
            e.rssi = 0.75 * e.rssi + 0.25 * rssi_dbm
        e.hits += 1
        e.last_seen, e.counter, e.flags = now, counter, flags
        if not e.reported and e.hits >= self.hits_required:
            self.arrivals.append(rid + counter.to_bytes(2, "little") + bytes([encode_rssi(e.rssi), flags]))
            e.reported = True
        return out

    def flush(self, now: float) -> list[Uplink]:
        """Every 15 s: age out departed wearables, then send arrivals and departures."""
        for rid in sorted(r for r, e in self.table.items() if now - e.last_seen > P["depart_timeout_s"]):
            if self.table.pop(rid).reported:
                self.departures.append(rid)                # departures go out in pseudonym order
        self.sos_seen = {r: t for r, t in self.sos_seen.items() if now - t < P["depart_timeout_s"]}
        out, chunk, per = [], int(P["chunk_tags"]), int(P["departure_ids_per_frame"])
        for i in range(0, len(self.arrivals), chunk):
            out.append(Uplink(FPORT_ARRIVALS, b"".join(self.arrivals[i:i + chunk])))
        for i in range(0, len(self.departures), per):
            out.append(Uplink(FPORT_DEPARTURES, b"".join(self.departures[i:i + per])))
        self.arrivals, self.departures = [], []
        return out

    def heartbeat(self) -> Uplink | None:
        """Every 60 s: a 64-byte Bloom filter of every wearable already reported as arrived."""
        bloom, active = BloomFilter(), 0
        for rid, e in self.table.items():
            if e.reported:
                bloom.add(rid)
                active += 1
        return Uplink(FPORT_HEARTBEAT, bytes(bloom)) if active else None


def decode_arrivals(payload: bytes) -> list[dict]:
    """Split an FPort 1 payload back into (rolling_id, counter, rssi_dbm, flags) tuples."""
    if len(payload) % 8:
        raise ValueError("an arrival payload is a whole number of 8-byte tuples")
    return [dict(rolling_id=payload[i:i + 4], counter=int.from_bytes(payload[i + 4:i + 6], "little"),
                 rssi_dbm=-payload[i + 6], flags=payload[i + 7]) for i in range(0, len(payload), 8)]
