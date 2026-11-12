"""Monte Carlo checks of the formulas, and an end-to-end walk through the system.

Every function takes a seed and is deterministic for that seed. Results are simulation,
not measurement.
"""
from __future__ import annotations

import math

import numpy as np

from . import capacity, kinematics, linkbudget, lora
from .edge import FPORT_SOS, PoleEdgeFilter
from .params import P
from .protocol import F_SOS, ROLE_PARENT, build_frame
from .resolver import Registry
from .server import ControlRoom
from .trek import Trek


# ---------------------------------------------------------------- 1. one gateway cell on air
def _pole_reports(rng, poles, period, seconds, mean_items, sizes, jitter=(0.2, 1.5)):
    """Start times and payload sizes of a periodic per-pole report with a Poisson number of items."""
    starts, byts = [], []
    for _ in range(poles):
        t = rng.uniform(0, period)
        while t < seconds:
            at = t + rng.uniform(*jitter)
            for b in sizes(int(rng.poisson(mean_items))):
                starts.append(at)
                byts.append(b)
                at += lora.time_on_air(b) + 0.05          # a pole sends its own frames one after another
            t += period
    return starts, byts


def simulate_cell(architecture: str, tags: int, seconds: float = 1800.0, seed: int = 0,
                  poles: int | None = None, channels: int | None = None, departures: bool = True) -> dict:
    """Put every uplink of one gateway cell on air and count the frames that overlap on a channel.

    Poles run their real timers (15 s and 60 s periods with a random phase and the
    200-1500 ms jitter of Algorithm 2). A frame is lost if any other frame on the same
    channel overlaps it in time: no capture effect, as in the analytical model.
    """
    rng = np.random.default_rng(seed)
    poles = int(P["cell_poles"] if poles is None else poles)
    channels = int(P["lora_channels"] if channels is None else channels)
    limit, tb, db = P["lora_max_app_bytes"], P["arrival_tuple_bytes"], P["departure_bytes"]
    present, arrivals = tags / poles, tags * P["flush_seconds"] / (P["pass_seconds"] * poles)
    split = capacity._split
    streams = {}
    if architecture == "raw":
        n = rng.poisson(tags / P["raw_ping_seconds"] * seconds)
        streams["forwarded ping"] = (list(rng.uniform(0, seconds, n)), [P["raw_ping_bytes"]] * n)
    if architecture == "single":
        n = rng.poisson(tags / P["pass_seconds"] * seconds)
        streams["arrival"] = (list(rng.uniform(0, seconds, n)), [tb] * n)
    if architecture == "batch":
        streams["arrival batch"] = _pole_reports(rng, poles, P["flush_seconds"], seconds, arrivals,
                                                 lambda k: split(k, limit // tb, tb))
    if architecture in ("single", "batch"):
        streams["raw ID heartbeat"] = _pole_reports(rng, poles, P["heartbeat_seconds"], seconds, present,
                                                    lambda k: split(k, limit // db, db))
    if architecture == "rakshasutra":
        streams["arrival chunk"] = _pole_reports(rng, poles, P["flush_seconds"], seconds, arrivals,
                                                 lambda k: split(k, int(P["chunk_tags"]), tb))
        if departures:
            streams["departure list"] = _pole_reports(rng, poles, P["flush_seconds"], seconds, arrivals,
                                                      lambda k: split(k, int(P["departure_ids_per_frame"]), db))
        streams["Bloom heartbeat"] = _pole_reports(rng, poles, P["heartbeat_seconds"], seconds, present,
                                                   lambda k: [64] if k else [])
    names = list(streams)
    start = np.concatenate([np.asarray(streams[n][0], float) for n in names])
    size = np.concatenate([np.asarray(streams[n][1], float) for n in names])
    kind = np.concatenate([np.full(len(streams[n][0]), i) for i, n in enumerate(names)])
    toa_of = {b: lora.time_on_air(int(b)) for b in np.unique(size)}
    end = start + np.array([toa_of[b] for b in size])
    chan = rng.integers(0, channels, len(start))
    lost = np.zeros(len(start), bool)
    for c in range(channels):
        idx = np.where(chan == c)[0]
        idx = idx[np.argsort(start[idx], kind="stable")]
        s, e = start[idx], end[idx]
        prev_end = np.concatenate([[-np.inf], np.maximum.accumulate(e)[:-1]])
        next_start = np.concatenate([s[1:], [np.inf]])
        lost[idx] = (s < prev_end) | (next_start < e)
    keep = (start > 30) & (start < seconds - 30)                 # ignore edge effects
    out = dict(architecture=architecture, tags=tags, seconds=seconds, frames=int(keep.sum()),
               load=float((end - start)[keep].sum() / (seconds - 60) / channels),
               loss=float(lost[keep].mean()), by_stream={})
    for i, n in enumerate(names):
        m = keep & (kind == i)
        if m.any():
            out["by_stream"][n] = dict(frames=int(m.sum()), loss=float(lost[m].mean()))
    return out


# ---------------------------------------------------------------- 2. the band-to-band tether
def simulate_tether(window_s: float | None = None, phy: str = "coded", hours: float = 14.0, seed: int = 0,
                    distance_m: float = 2.0) -> dict:
    """A parent tag scanning for a child band that never leaves its side: how often does it cry wolf?"""
    rng = np.random.default_rng(seed)
    w = P["tether_scan_window_s"] if window_s is None else window_s
    pkt = kinematics.primary_packet_ms(phy) / 1000.0
    sens = P["ble_sens_1m_dbm"] if phy == "1m" else P["ble_sens_coded_dbm"]
    p_signal = linkbudget.delivery_probability(linkbudget.ble_margin_db(distance_m, sens))
    total = hours * 3600.0
    n_adv = int(total / P["adv_interval_s"]) + 2
    adv = np.cumsum(P["adv_interval_s"] + rng.uniform(0, P["adv_delay_max_s"], n_adv)) - rng.uniform(0, 0.8)
    scans = np.arange(0.0, total, P["tether_scan_period_s"]) + rng.uniform(0, P["tether_scan_period_s"])
    first = np.searchsorted(adv, scans)                          # first packet starting inside the window
    heard = np.zeros(len(scans), bool)
    for k in range(2):                                           # a long window can hold more than one packet
        j = np.minimum(first + k, n_adv - 1)
        heard |= (adv[j] >= scans) & (adv[j] + pkt <= scans + w) & (rng.random(len(scans)) < p_signal)
    misses, alarms, run, alarmed = int(P["tether_misses"]), 0, 0, 0
    for h in heard:
        run = 0 if h else run + 1
        alarms += run == misses                                  # the buzzer starts
        alarmed += run >= misses                                 # and stays on until the band is heard again
    return dict(window_ms=w * 1000.0, phy=phy, hours=hours, scans=len(scans), hit_rate=float(heard.mean()),
                false_alarms=alarms, false_alarms_per_hour=alarms / hours, time_in_alarm=alarmed / len(scans),
                scan_current_ua=kinematics.parent_tag_scan_ua(w))


# ---------------------------------------------------------------- 3. passengers in electric vehicles
def simulate_ev(hits_required: int = 1, adv_interval_s: float | None = None, crowd: int = 0, phy: str = "coded",
                passes: int = 20000, seed: int = 0, speed_mps: float | None = None) -> dict:
    """Drive a wearable past a pole many times and count how often the pole reports it."""
    rng = np.random.default_rng(seed)
    adv = P["adv_interval_s"] if adv_interval_s is None else adv_interval_s
    v = P["ev_mps"] if speed_mps is None else speed_mps
    half = P["core_zone_m"] / 2
    sens = P["ble_sens_1m_dbm"] if phy == "1m" else P["ble_sens_coded_dbm"]
    clear = math.exp(-2.0 * crowd * kinematics.primary_packet_ms(phy) / 1000.0 / adv)
    captured = 0
    for _ in range(passes):
        t = rng.uniform(0, adv)
        hits = 0
        while t < 2 * half / v:
            d = max(abs(-half + v * t), 1.0)
            p = linkbudget.delivery_probability(linkbudget.ble_margin_db(math.hypot(d, 3.0), sens)) * clear
            hits += rng.random() < p
            t += adv + rng.uniform(0, P["adv_delay_max_s"])
        captured += hits >= hits_required
    return dict(hits_required=hits_required, adv_interval_s=adv, crowd=crowd, passes=passes,
                capture=captured / passes)


# ---------------------------------------------------------------- 4. how long an SOS takes
def simulate_sos(tags: int = 3000, crowd: int = 50, trials: int = 20000, seed: int = 0,
                 architecture: str = "rakshasutra", fiber: bool = False) -> dict:
    """Seconds from pressing the button to the control-room alarm.

    Button, next 200 ms advertisement, decode at the pole, confirmed LoRa uplink at SF7,
    and if no acknowledgement a repeat at SF9 after `lorawan_retry_s` (up to 7 repeats).
    Background traffic is the cell load for `tags` wearables; the repeat at SF9 is treated
    as colliding with SF7 traffic too, which is pessimistic. A fibre pole skips LoRa.
    """
    rng = np.random.default_rng(seed)
    cell = capacity.cell_load(architecture, tags)
    rate = sum(s.frames_per_s for s in cell.streams)
    air = sum(s.airtime_per_s for s in cell.streams)
    m = P["lora_channels"]
    toa7, toa9 = lora.time_on_air(15, sf=7), lora.time_on_air(15, sf=9)
    loss7 = 1 - math.exp(-(rate * toa7 + air) / m)
    loss9 = 1 - math.exp(-(rate * toa9 + air) / m)
    p_ble = kinematics.ble_frame_success(10.0, crowd, adv_interval_s=P["adv_interval_s"])
    t = rng.uniform(0, P["adv_interval_sos_s"], trials)
    t += (rng.geometric(p_ble, trials) - 1) * P["adv_interval_sos_s"]
    delivered = np.zeros(trials, bool)
    if fiber:
        delivered[:] = True
    else:
        for attempt in range(8):
            todo = ~delivered
            toa, loss = (toa7, loss7) if attempt == 0 else (toa9, loss9)
            t[todo] += toa
            ok = todo & (rng.random(trials) >= loss)
            delivered |= ok
            t[todo & ~ok] += P["lorawan_retry_s"]
    t += P["backhaul_s"]
    t = t[delivered]
    return dict(tags=tags, crowd=crowd, fiber=fiber, first_try_loss=0.0 if fiber else loss7, retry_loss=loss9,
                delivered=float(delivered.mean()), median_s=float(np.median(t)), p95_s=float(np.percentile(t, 95)),
                within_4s=float((t <= 4.0).mean()), within_5s=float((t <= 5.0).mean()),
                toa_sf7_ms=toa7 * 1000, toa_sf9_ms=toa9 * 1000)


# ---------------------------------------------------------------- 5. a family, end to end
DEMO_MASTER = bytes.fromhex("000102030405060708090a0b0c0d0e0f")   # public demonstration key, never a real one
DEMO_SALT = b"rakshasutra-demo"


def demo_registry(t_pair: float = 0.0) -> tuple[Registry, dict]:
    """A registry with one demonstration family: a child's band and a parent's tag."""
    from .protocol import derive_tag_key
    reg, keys = Registry(), {}
    for uid, role, c0 in (("band-0421", "band", 17), ("tag-0421", "parent", 40)):
        keys[uid] = derive_tag_key(DEMO_MASTER, uid.encode(), DEMO_SALT)
        reg.register(uid, keys[uid], c0, t_pair, family="family-0421", role=role)
    return reg, keys


def family_walk(seed: int = 7, uplink_loss: float = 0.12, crowd: int = 30) -> dict:
    """A parent and child reach the Adhkuwari junction together and leave by different branches.

    Both walk at 1.25 m/s. After the hub the parent continues on the Himkoti track and the
    child on the Sanjichhat track. The child presses SOS 150 s after the split. Every
    advertisement is a real signed frame; poles run the real edge filter; each LoRa
    uplink from a non-fibre pole is dropped with probability `uplink_loss`.

    Returns the uplink log the server received and the control room that processed it.
    """
    rng = np.random.default_rng(seed)
    trek = Trek()
    registry, keys = demo_registry()
    room = ControlRoom(registry, trek)
    filters = {p.pid: PoleEdgeFilter(p.hits_required, p.rssi_gate_dbm) for p in trek.poles}
    v = P["walk_mps"]
    start = trek.last["old-track"] - 3
    shared = list(range(start, trek.last["old-track"] + 1)) + \
        list(range(trek.first["adhkuwari"], trek.last["adhkuwari"] + 1))
    routes = {"band-0421": shared + list(range(trek.first["sanjichhat"], trek.first["sanjichhat"] + 12)),
              "tag-0421": shared + list(range(trek.first["himkoti"], trek.first["himkoti"] + 12))}
    along = {}                                                # uid -> distance of each route pole from the start
    for uid, route in routes.items():
        cum = [0.0]
        for a, b in zip(route, route[1:]):
            cum.append(cum[-1] + trek.edges[a][b])
        along[uid] = cum
    split_m = along["band-0421"][len(shared) - 1]
    duration = split_m / v + 420.0
    sos_at = split_m / v + 150.0
    nearby = sorted(set(routes["band-0421"]) | set(routes["tag-0421"]))
    from_pole = {pid: trek.distances_from(pid) for pid in nearby}

    def track_distance(uid, t, pole):
        """Distance along the track from where `uid` is at time t to `pole`."""
        s, route, cum = v * t, routes[uid], along[uid]
        i = max(0, min(len(cum) - 2, int(np.searchsorted(cum, s)) - 1))
        return min(abs(s - cum[i]) + from_pole[route[i]][pole], abs(cum[i + 1] - s) + from_pole[route[i + 1]][pole])

    counters = {u: registry.tags[u].c_init for u in keys}
    log, next_adv = [], {u: rng.uniform(0, 0.8) for u in keys}
    next_flush = {pid: rng.uniform(0, 15) for pid in nearby}
    next_beat = {pid: rng.uniform(0, 60) for pid in nearby}

    def send(t, pid, up):
        if trek.pole(pid).fiber or up.confirmed or rng.random() >= uplink_loss:
            log.append(dict(time_s=round(t, 2), pole=pid, fport=up.fport, payload=up.payload.hex()))
            room.on_uplink(t, pid, up.fport, up.payload)

    t = 0.0
    while t < duration:
        uid = min(next_adv, key=next_adv.get)
        t = next_adv[uid]
        for pid in nearby:                                    # poles run their timers up to now
            while next_flush[pid] <= t:
                for up in filters[pid].flush(next_flush[pid]):
                    send(next_flush[pid] + rng.uniform(0.2, 1.5), pid, up)
                next_flush[pid] += 15.0
            while next_beat[pid] <= t:
                up = filters[pid].heartbeat()
                if up:
                    send(next_beat[pid], pid, up)
                next_beat[pid] += 60.0
        sos = uid == "band-0421" and sos_at <= t < sos_at + 20
        c = (counters[uid] + int(t // 900)) & 0xFFFF
        frame = build_frame(keys[uid], c, flags=F_SOS if sos else 0,
                            battery_volts=2.98, role=ROLE_PARENT if uid.startswith("tag") else 0)
        for pid in nearby:
            d = math.hypot(track_distance(uid, t, pid), 3.0)
            if d > 250:
                continue
            rssi = linkbudget.ble_rx_dbm(d) + rng.normal(0, P["ble_sigma_db"])
            if rssi < P["ble_sens_coded_dbm"] or rng.random() > math.exp(-2 * crowd * 1.168e-3 / 0.8):
                continue
            up = filters[pid].on_advertisement(frame, rssi, t)
            if up is not None and up.fport == FPORT_SOS:
                send(t + lora.time_on_air(15), pid, up)
        next_adv[uid] = t + (0.2 if sos else 0.8) + rng.uniform(0, 0.01)
    return dict(log=log, room=room, registry=registry, keys=keys, trek=trek, split_s=split_m / v, sos_s=sos_at,
                routes=routes, along=along, duration_s=duration)
