"""The pilgrimage route as a branched graph of poles (white paper, Section III-A).

Zone lengths, the pole count and the altitude range are the paper's. Pole positions are
schematic: poles are spread evenly along each zone, and altitude rises linearly between
zone ends. Nothing here is a survey of the real track.

    Banganga --+-- zone 1 (old track, 6.0 km) --+-- zone 3 (Adhkuwari hub, 0.5 km) --+
               +-- zone 2 (Tarakote, 7.0 km) ---+                                    |
         +---------------------------------------------------------------------------+
         +-- zone 4a (Himkoti, 3.5 km) ----+-- zone 5 (Bhawan, 1.0 km) -- zone 6 (Bhairon Ghati, 1.5 km)
         +-- zone 4b (Sanjichhat, 3.0 km) -+
"""
from __future__ import annotations

import heapq
from dataclasses import dataclass

from .params import P

# segment: (name, zone, length_km, poles, start altitude m, end altitude m, fibre LAN)
SEGMENTS = [
    ("old-track", 1, 6.0, 56, 762.0, 1463.0, False),
    ("tarakote", 2, 7.0, 65, 762.0, 1463.0, False),
    ("adhkuwari", 3, 0.5, 20, 1463.0, 1470.0, True),
    ("himkoti", 4, P["zone4_himkoti_km"], 32, 1470.0, 1585.0, False),
    ("sanjichhat", 4, P["zone4_sanjichhat_km"], 28, 1470.0, 1585.0, False),
    ("bhawan", 5, 1.0, 40, 1585.0, 1600.0, True),
    ("bhairon", 6, 1.5, 14, 1600.0, 2017.0, False),
]
# which segments follow which (a segment's last pole connects to the first pole of each successor)
SUCCESSORS = {"old-track": ["adhkuwari"], "tarakote": ["adhkuwari"], "adhkuwari": ["himkoti", "sanjichhat"],
              "himkoti": ["bhawan"], "sanjichhat": ["bhawan"], "bhawan": ["bhairon"], "bhairon": []}
TRANSIT_ZONES = {1, 2, 4, 6}


@dataclass(frozen=True)
class Pole:
    pid: int
    segment: str
    zone: int
    along_m: float       # distance from the start of its segment
    altitude_m: float
    fiber: bool

    @property
    def hits_required(self) -> int:
        """Algorithm 2, line 10: one decoded frame on transit tracks, three in dense hubs."""
        return 1 if self.zone in TRANSIT_ZONES else 3

    @property
    def rssi_gate_dbm(self) -> float:
        return P["rssi_gate_track_dbm"] if self.zone in TRANSIT_ZONES else P["rssi_gate_hub_dbm"]


class Trek:
    """Poles, the edges between them, and distances along the track."""

    def __init__(self):
        self.poles: list[Pole] = []
        self.edges: dict[int, dict[int, float]] = {}
        self.first: dict[str, int] = {}
        self.last: dict[str, int] = {}
        pid = 1
        for name, zone, km, n, a0, a1, fiber in SEGMENTS:
            step = km * 1000.0 / n
            self.first[name] = pid
            for i in range(n):
                along = (i + 0.5) * step
                self.poles.append(Pole(pid, name, zone, along, a0 + (a1 - a0) * along / (km * 1000.0), fiber))
                if i:
                    self._link(pid - 1, pid, step)
                pid += 1
            self.last[name] = pid - 1
        self._step = {name: km * 1000.0 / n for name, _z, km, n, *_ in SEGMENTS}
        # the two base tracks start together at Banganga
        self._link(self.first["old-track"], self.first["tarakote"],
                   (self._step["old-track"] + self._step["tarakote"]) / 2)
        for seg, nexts in SUCCESSORS.items():
            for nxt in nexts:
                self._link(self.last[seg], self.first[nxt], (self._step[seg] + self._step[nxt]) / 2)

    def _link(self, a: int, b: int, metres: float) -> None:
        self.edges.setdefault(a, {})[b] = metres
        self.edges.setdefault(b, {})[a] = metres

    def pole(self, pid: int) -> Pole:
        return self.poles[pid - 1]

    def distances_from(self, source: int) -> dict[int, float]:
        """Shortest track distance in metres from one pole to every other (Dijkstra)."""
        dist, heap = {source: 0.0}, [(0.0, source)]
        while heap:
            d, u = heapq.heappop(heap)
            if d > dist[u]:
                continue
            for v, w in self.edges[u].items():
                if d + w < dist.get(v, float("inf")):
                    dist[v] = d + w
                    heapq.heappush(heap, (d + w, v))
        return dist

    def distance(self, a: int, b: int) -> float:
        """Eq. 1: geodesic distance along the track between two poles."""
        return self.distances_from(a)[b]

    def neighbourhood(self, pid: int, hops: int = 2) -> list[int]:
        """Poles within `hops` edges: the five-pole set of Layer 2, larger at a junction."""
        seen, frontier = {pid}, {pid}
        for _ in range(hops):
            frontier = {v for u in frontier for v in self.edges[u]} - seen
            seen |= frontier
        return sorted(seen)

    def zone_summary(self) -> list[dict]:
        out = {}
        for name, zone, km, n, *_rest, fiber in SEGMENTS:
            z = out.setdefault(zone, dict(zone=zone, km=0.0, poles=0, fiber=fiber, segments=[]))
            z["km"] += km
            z["poles"] += n
            z["segments"].append(name)
        for z in out.values():
            z["spacing_m"] = z["km"] * 1000.0 / z["poles"]
        return [out[k] for k in sorted(out)]
