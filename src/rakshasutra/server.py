"""The control room: turns pole uplinks into locations and alerts."""
from __future__ import annotations

from dataclasses import dataclass, field

from .bloom import BloomFilter
from .edge import FPORT_ARRIVALS, FPORT_DEPARTURES, FPORT_HEARTBEAT, FPORT_SOS, decode_arrivals
from .params import P
from .protocol import CMD_SEPARATION, rolling_id, wake_token
from .resolver import DROP_FORGED_SOS, DROP_FRAME, OK, Registry
from .trek import Trek


@dataclass
class Event:
    time: float
    kind: str            # ARRIVED, SUSPECT, SOS, SEPARATION, REUNITED, DROPPED, FORGED_SOS
    uid: str | None
    pole: int | None
    detail: str = ""


@dataclass
class ControlRoom:
    registry: Registry
    trek: Trek = field(default_factory=Trek)
    events: list = field(default_factory=list)
    track: dict = field(default_factory=dict)        # uid -> [(time, pole)]
    separated: set = field(default_factory=set)      # families currently flagged
    wakes: list = field(default_factory=list)        # (time, uid, poles, token)
    last_sos: dict = field(default_factory=dict)     # uid -> [time, poles that heard it, event, track point added]

    def _log(self, *a, **k) -> Event:
        e = Event(*a, **k)
        self.events.append(e)
        return e

    def on_uplink(self, time: float, pole: int, fport: int, payload: bytes) -> list[Event]:
        """Process one LoRaWAN (or fibre) uplink from a pole."""
        before = len(self.events)
        if fport == FPORT_ARRIVALS:
            for a in decode_arrivals(payload):
                # tuples carry no MIC, so the SOS bit is ignored here; a real SOS arrives on FPort 10
                r = self.registry.resolve(pole, a["rolling_id"], a["counter"], a["rssi_dbm"], a["flags"] & ~1, time)
                self._after(r, time, pole)
        elif fport == FPORT_SOS:
            # the whole signed frame, plus one byte of RSSI so that several poles can be arbitrated
            rssi = -float(payload[15]) if len(payload) > 15 else P["rssi_gate_hub_dbm"]
            r = self.registry.resolve_frame(pole, payload[:15], rssi, time)
            if r.status == OK and r.sos:
                first = self.last_sos.get(r.uid)
                if first is None or time - first[0] > 60.0:
                    first = self.last_sos[r.uid] = [time, 1, self._log(time, "SOS", r.uid, r.location, ""), False]
                else:
                    first[1] += 1
                e = first[2]                          # later poles refine where the alarm is shown
                e.pole = r.location
                e.detail = f"priority alarm, MIC verified; heard by {first[1]} pole(s), strongest here"
                tr = self.track.setdefault(r.uid, [])
                if first[3]:
                    tr[-1] = (tr[-1][0], r.location)      # same alarm, better pole: correct the point
                elif not tr or tr[-1][1] != r.location:
                    tr.append((time, r.location))
                    first[3] = True
            elif r.status == DROP_FORGED_SOS:
                self._log(time, "FORGED_SOS", r.uid, pole, "MIC does not match; dropped")
            else:
                self._log(time, "DROPPED", None, pole, "unknown or stale pseudonym")
        elif fport == FPORT_HEARTBEAT:
            bloom = BloomFilter(payload)
            self.registry.refresh(time)
            for uid, (where, _t) in list(self.registry.location.items()):
                if where == pole:
                    c = self.registry.expected_counter(uid, time)
                    key = self.registry.tags[uid].key
                    if any(rolling_id(key, (c + d) & 0xFFFF) in bloom for d in (-1, 0, 1)):
                        self.registry.location[uid] = (pole, time)
        elif fport == FPORT_DEPARTURES:
            pass                                      # departures only clear presence; arrivals move a tag
        self._check_families(time)
        return self.events[before:]

    def _after(self, r, time, pole) -> None:
        if r.status == DROP_FRAME:
            self._log(time, "DROPPED", None, pole, "unknown or stale pseudonym")
        elif r.status == OK:
            self._moved(r.uid, time, r.location)

    def _moved(self, uid, time, pole) -> None:
        tr = self.track.setdefault(uid, [])
        if not tr or tr[-1][1] != pole:
            detail, suspect = "", False
            if tr:
                dt = time - tr[-1][0]
                d = self.trek.distance(tr[-1][1], pole)
                if dt > 0:
                    detail = f"{d:.0f} m in {dt:.0f} s, {d / dt:.1f} m/s"
                    suspect = d > P["suspect_min_m"] and d / dt > P["suspect_speed_mps"]
            tr.append((time, pole))
            self._log(time, "ARRIVED", uid, pole, detail)
            if suspect:                               # nobody on this track moves that fast: likely a replayed frame
                self._log(time, "SUSPECT", uid, pole, "faster than any vehicle on the track; possible replay")

    def separation_m(self, family: str) -> float | None:
        """Largest track distance between any band of a family and its parent tag."""
        members = [t for t in self.registry.tags.values() if t.family == family]
        parents = [t.uid for t in members if t.role == "parent" and t.uid in self.registry.location]
        bands = [t.uid for t in members if t.role != "parent" and t.uid in self.registry.location]
        if not parents or not bands:
            return None
        return max(self.trek.distance(self.registry.location[b][0], self.registry.location[p][0])
                   for b in bands for p in parents)

    def _check_families(self, time: float) -> None:
        for family in {t.family for t in self.registry.tags.values() if t.family}:
            d = self.separation_m(family)
            if d is None:
                continue
            if d >= P["separation_alert_m"] and family not in self.separated:
                self.separated.add(family)
                for t in self.registry.tags.values():
                    if t.family == family:
                        pole = self.registry.location[t.uid][0]
                        poles = self.trek.neighbourhood(pole)
                        token = wake_token(t.key, self.registry.expected_counter(t.uid, time), CMD_SEPARATION)
                        self.wakes.append((time, t.uid, poles, token))
                self._log(time, "SEPARATION", family, None, f"{d:.0f} m apart along the track; wake tokens multicast")
            elif d < P["separation_alert_m"] / 2 and family in self.separated:
                self.separated.discard(family)
                self._log(time, "REUNITED", family, None, f"{d:.0f} m apart")
