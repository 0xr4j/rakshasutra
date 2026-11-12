"""Server-side identity resolution and location arbitration (white paper, Section IV-D, Algorithm 1).

A Python dictionary stands in for the Redis hash map of the deployed design: the lookup
is the same single hash probe per uplink event.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .cmac import aes_cmac
from .params import P
from .protocol import F_SOS, SLOT_SECONDS, parse_frame, rolling_id

OK, DROP_FRAME, DROP_FORGED_SOS = "OK", "DROP_FRAME", "DROP_FORGED_SOS"


@dataclass
class Tag:
    uid: str
    key: bytes
    c_init: int
    t_pair: float
    family: str = ""
    role: str = "band"


@dataclass
class Sighting:
    time: float
    pole: int
    rssi_dbm: float
    flags: int


@dataclass
class Result:
    status: str
    uid: str | None = None
    sos: bool = False
    location: int | None = None


@dataclass
class Registry:
    """Paired wearables and the sliding-window lookup table H[Rolling_ID] -> (tag, slot)."""
    tags: dict = field(default_factory=dict)
    _table: dict = field(default_factory=dict)
    _built: dict = field(default_factory=dict)        # uid -> centre slot of the window in the table
    sightings: dict = field(default_factory=dict)     # uid -> recent sightings
    location: dict = field(default_factory=dict)      # uid -> (pole, time)
    stale_or_unknown: dict = field(default_factory=dict)
    forged_sos: dict = field(default_factory=dict)

    def register(self, uid: str, key: bytes, c_init: int, t_pair: float, family: str = "",
                 role: str = "band") -> Tag:
        """Pairing at the registration counter: record the counter seen on the pad and the time."""
        tag = self.tags[uid] = Tag(uid, key, c_init & 0xFFFF, t_pair, family, role)
        return tag

    def unregister(self, uid: str) -> None:
        """Exit unpairing: forget the tag and everything recorded about it."""
        self.tags.pop(uid, None)
        self._built.pop(uid, None)
        self.sightings.pop(uid, None)
        self.location.pop(uid, None)
        self._table = {r: [x for x in v if x[0] != uid] for r, v in self._table.items()}
        self._table = {r: v for r, v in self._table.items() if v}

    def expected_counter(self, uid: str, t: float) -> int:
        """Eq. 6."""
        tag = self.tags[uid]
        return (tag.c_init + int((t - tag.t_pair) // SLOT_SECONDS)) & 0xFFFF

    def refresh(self, t: float) -> None:
        """Keep the three-slot window {c-1, c, c+1} of every tag in the table."""
        for uid, tag in self.tags.items():
            c = self.expected_counter(uid, t)
            if self._built.get(uid) == c:
                continue
            for rid in [r for r, v in self._table.items() if any(x[0] == uid for x in v)]:
                self._table[rid] = [x for x in self._table[rid] if x[0] != uid]
                if not self._table[rid]:
                    del self._table[rid]
            for k in (c - 1, c, c + 1):
                k &= 0xFFFF
                self._table.setdefault(rolling_id(tag.key, k), []).append((uid, k))
            self._built[uid] = c

    def table_size(self) -> int:
        return sum(len(v) for v in self._table.values())

    def _lookup(self, rid: bytes, counter: int):
        for uid, k in self._table.get(rid, ()):
            if k == counter:
                return self.tags[uid]
        return None

    def resolve(self, pole: int, rid: bytes, counter: int, rssi_dbm: float, flags: int, t: float,
                frame: bytes | None = None) -> Result:
        """Algorithm 1 for one uplink event.

        Arrival tuples carry no MIC, so they are accepted on pseudonym and counter alone.
        An SOS is forwarded as the whole 15-byte frame and its MIC is checked here.
        """
        self.refresh(t)
        tag = self._lookup(bytes(rid), counter)
        if tag is None:
            self.stale_or_unknown[pole] = self.stale_or_unknown.get(pole, 0) + 1
            return Result(DROP_FRAME)
        sos = bool(flags & F_SOS)
        if sos:
            if frame is None or aes_cmac(tag.key, frame[2:11])[:4] != frame[11:15]:
                self.forged_sos[pole] = self.forged_sos.get(pole, 0) + 1
                return Result(DROP_FORGED_SOS, tag.uid)
        recent = [s for s in self.sightings.get(tag.uid, []) if t - s.time <= P["arbitration_s"]]
        recent.append(Sighting(t, pole, rssi_dbm, flags))
        self.sightings[tag.uid] = recent
        best = max(recent, key=lambda s: (s.rssi_dbm, s.time))
        self.location[tag.uid] = (best.pole, t)
        return Result(OK, tag.uid, sos, best.pole)

    def resolve_frame(self, pole: int, frame: bytes, rssi_dbm: float, t: float) -> Result:
        """Resolve a complete 15-byte frame (the SOS path, FPort 10)."""
        try:
            f = parse_frame(frame)
        except ValueError:
            self.stale_or_unknown[pole] = self.stale_or_unknown.get(pole, 0) + 1
            return Result(DROP_FRAME)
        return self.resolve(pole, f.rolling_id, f.counter, rssi_dbm, f.flags, t, frame=frame)


def collision_probability(tags: int, window: int | None = None) -> float:
    """Chance that at least two table entries share a 32-bit pseudonym (birthday bound)."""
    import math
    n = tags * (P["window_slots"] if window is None else window)
    return 1.0 - math.exp(-n * (n - 1) / 2.0 / 2 ** 32)
