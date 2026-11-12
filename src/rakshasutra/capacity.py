"""How much LoRa airtime each forwarding design needs in one gateway cell (white paper, Table IV).

The model is stated in full so that every number can be recomputed:

* `tags` wearables move through a cell of `poles` poles and reach a new pole every
  `pass_s` seconds on average, so each pole sees Poisson arrivals at tags / (pass_s * poles)
  per second and holds Poisson(tags / poles) wearables at any moment.
* Four designs turn that into uplinks (see `ARCHITECTURES`).
* Offered load G is the airtime per second divided by the number of channels, and loss
  follows pure ALOHA. `loss` uses the equal-length formula 1 - exp(-2G) that the paper
  uses; `loss_by_stream` uses the mixed-length formula from `lora.mixed_aloha_loss`.

Capture effect and spreading-factor orthogonality are ignored, so losses are pessimistic.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from . import lora
from .params import P

ARCHITECTURES = {
    "raw": "Raw BLE forwarding: every ping becomes an uplink",
    "single": "One uplink per arrival, plus a raw list of IDs every 60 s",
    "batch": "Arrivals batched every 15 s, plus a raw list of IDs every 60 s",
    "rakshasutra": "25-tag arrival chunks, departure lists and a 64-byte Bloom heartbeat",
}


SHORT = {"raw": "Raw forwarding", "single": "Single-event arrivals", "batch": "15 s batching",
         "rakshasutra": "Rakshasutra (as specified)"}


def _poisson(mean: float, tail: float = 1e-12) -> list[float]:
    """Poisson probabilities for k = 0, 1, ... until the remaining tail is negligible."""
    pmf, k, p, total = [], 0, math.exp(-mean), 0.0
    while total < 1 - tail or k <= mean:
        pmf.append(p)
        total += p
        k += 1
        p *= mean / k
        if k > mean + 60 * math.sqrt(mean + 1) + 60:
            break
    return pmf


def _split(count: int, per_frame: int, unit_bytes: int) -> list[int]:
    """Application payload sizes when `count` items of `unit_bytes` go `per_frame` to a frame."""
    full, rest = divmod(count, per_frame)
    return [per_frame * unit_bytes] * full + ([rest * unit_bytes] if rest else [])


@dataclass
class Stream:
    name: str
    frames_per_s: float
    airtime_per_s: float
    mean_bytes: float

    @property
    def mean_toa(self) -> float:
        return self.airtime_per_s / self.frames_per_s if self.frames_per_s else 0.0


@dataclass
class CellLoad:
    architecture: str
    tags: int
    poles: int
    streams: list[Stream]
    load: float                 # G, airtime per second per channel
    loss: float                 # 1 - exp(-2G)
    loss_by_stream: dict = field(default_factory=dict)
    oversize_probability: float = 0.0   # chance a single report would need more than 222 bytes
    max_frame_bytes: int = 0

    @property
    def airtime_per_s(self) -> float:
        return sum(s.airtime_per_s for s in self.streams)


def _periodic_stream(name: str, poles: int, period: float, mean_items: float, sizes) -> Stream:
    """A report each pole sends every `period` s whose size depends on a Poisson count.

    `sizes(k)` gives the list of frame payloads for k items.
    """
    frames = air = byts = 0.0
    for k, p in enumerate(_poisson(mean_items)):
        for b in sizes(k):
            frames += p
            air += p * lora.time_on_air(b)
            byts += p * b
    rate = poles / period
    return Stream(name, rate * frames, rate * air, byts / frames if frames else 0.0)


def cell_load(architecture: str, tags: int, poles: int | None = None, pass_s: float | None = None,
              channels: int | None = None, departures: bool = True) -> CellLoad:
    """Airtime, load and loss for one gateway cell."""
    poles = int(P["cell_poles"] if poles is None else poles)
    pass_s = P["pass_seconds"] if pass_s is None else pass_s
    channels = int(P["lora_channels"] if channels is None else channels)
    limit = P["lora_max_app_bytes"]
    tuple_b, dep_b = P["arrival_tuple_bytes"], P["departure_bytes"]
    present = tags / poles                                  # wearables held by a pole
    arrivals = tags * P["flush_seconds"] / (pass_s * poles)  # per pole per flush
    streams: list[Stream] = []
    oversize, max_frame = 0.0, 0

    def raw_heartbeat():
        per = limit // dep_b
        s = _periodic_stream("raw ID heartbeat", poles, P["heartbeat_seconds"], present,
                                lambda k: _split(k, per, dep_b))
        pmf = _poisson(present)
        return s, sum(p for k, p in enumerate(pmf) if k > per)

    if architecture == "raw":
        b = P["raw_ping_bytes"]
        rate = tags / P["raw_ping_seconds"]
        streams.append(Stream("forwarded ping", rate, rate * lora.time_on_air(b), b))
        max_frame = b
    elif architecture == "single":
        rate = tags / pass_s
        streams.append(Stream("arrival", rate, rate * lora.time_on_air(tuple_b), tuple_b))
        hb, oversize = raw_heartbeat()
        streams.append(hb)
        max_frame = limit
    elif architecture == "batch":
        per = limit // tuple_b
        s = _periodic_stream("arrival batch", poles, P["flush_seconds"], arrivals,
                                lambda k: _split(k, per, tuple_b))
        streams.append(s)
        hb, oversize = raw_heartbeat()
        streams.append(hb)
        max_frame = limit
    elif architecture == "rakshasutra":
        chunk = int(P["chunk_tags"])
        s = _periodic_stream("arrival chunk", poles, P["flush_seconds"], arrivals,
                                lambda k: _split(k, chunk, tuple_b))
        streams.append(s)
        if departures:
            per = int(P["departure_ids_per_frame"])
            s = _periodic_stream("departure list", poles, P["flush_seconds"], arrivals,
                                    lambda k: _split(k, per, dep_b))
            streams.append(s)
        active = 1.0 - math.exp(-present)
        rate = poles * active / P["heartbeat_seconds"]
        streams.append(Stream("Bloom heartbeat", rate, rate * lora.time_on_air(64), 64))
        max_frame = chunk * tuple_b
    else:
        raise ValueError(f"unknown architecture {architecture!r}; choose from {list(ARCHITECTURES)}")

    load = sum(s.airtime_per_s for s in streams) / channels
    by = lora.mixed_aloha_loss([(s.frames_per_s, s.mean_toa) for s in streams], channels)
    return CellLoad(architecture, tags, poles, streams, load, lora.aloha_loss(load),
                    {s.name: v for s, v in zip(streams, by)}, oversize, max_frame)


def table(tag_counts=(500, 1000, 2000, 3000), **kw) -> dict:
    """The white paper's Table IV, recomputed: {architecture: [CellLoad, ...]}."""
    return {a: [cell_load(a, n, **kw) for n in tag_counts] for a in ARCHITECTURES}


def deployed_cell(total_tags: int = 5000) -> CellLoad:
    """The deployed layout: 195 LoRa poles over 6 gateways, wearables spread evenly over all 255 poles."""
    lora_poles = P["poles_total"] - P["poles_fiber"]
    poles = lora_poles / P["gateways"]
    tags = total_tags * lora_poles / P["poles_total"] / P["gateways"]
    return cell_load("rakshasutra", round(tags), poles=round(poles))
