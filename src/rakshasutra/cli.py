"""The `rakshasutra` command."""
from __future__ import annotations

import argparse
import csv
import json
import sys

from . import __version__, audit, bloom, capacity, kinematics, linkbudget, lora, power
from .params import P
from .protocol import F_SOS, build_frame, mac_address, parse_frame, verify_frame
from .resolver import Registry
from .server import ControlRoom


def _bar(fraction: float, width: int = 24) -> str:
    n = max(0, min(width, round(fraction * width)))
    return "[" + "#" * n + "." * (width - n) + "]"


def _key(text: str) -> bytes:
    key = bytes.fromhex(text)
    if len(key) != 16:
        raise SystemExit("a tag key is 16 bytes (32 hex digits)")
    return key


def cmd_frame(a) -> int:
    key = _key(a.key)
    raw = build_frame(key, a.counter, flags=F_SOS if a.sos else 0, battery_volts=a.battery)
    f = parse_frame(raw)
    if a.json:
        print(json.dumps(dict(frame=raw.hex(), counter=f.counter, rolling_id=f.rolling_id.hex(), mic=f.mic.hex(),
                              mac=mac_address(key, a.counter).hex(":"), sos=f.sos)))
        return 0
    print(f"Frame ({len(raw)} bytes)   {raw.hex(' ')}")
    print(f"  Company_ID     {raw[0:2].hex(' ')}          0xFF5A, low byte first")
    print(f"  V_type         {raw[2]:02x}             version {f.version}, {'parent tag' if f.role else 'band'}")
    print(f"  Slot_Counter   {raw[3:5].hex(' ')}          slot {f.counter} ({f.counter * 15} min after power-on)")
    print(f"  Rolling_ID     {f.rolling_id.hex(' ')}    changes every 15 minutes")
    print(f"  F_stat         {f.flags:02x}             {'SOS pressed' if f.sos else 'no flags'}")
    print(f"  B_mv           {f.battery_code:02x}             {f.battery_volts:.2f} V")
    print(f"  MIC            {f.mic.hex(' ')}    AES-CMAC over bytes 2 to 10")
    print(f"  Radio address  {mac_address(key, a.counter).hex(':')}")
    return 0


def cmd_verify(a) -> int:
    ok = verify_frame(_key(a.key), bytes.fromhex(a.frame))
    print("VALID: pseudonym and MIC match this key" if ok else "REJECTED: not signed by this key")
    return 0 if ok else 1


def cmd_airtime(a) -> int:
    print(f"LoRaWAN time on air, IN865, SF{a.sf}, 125 kHz, coding rate 4/5")
    for b in a.bytes:
        flag = "" if b <= P["lora_max_app_bytes"] else "   over the 222-byte limit"
        print(f"  {b:4d} B application payload   {lora.time_on_air(b, sf=a.sf) * 1000:8.2f} ms{flag}")
    return 0


def cmd_capacity(a) -> int:
    rows = [capacity.cell_load(arch, a.tags, poles=a.poles) for arch in capacity.ARCHITECTURES]
    if a.json:
        print(json.dumps([dict(architecture=r.architecture, load=r.load, loss=r.loss,
                               oversize_probability=r.oversize_probability) for r in rows]))
        return 0
    print(f"One gateway cell: {a.tags:,} wearables, {a.poles} poles, 8 channels, SF7   (analytical model)")
    print(f"  {'design':<38}{'load':>8}{'frames lost':>14}")
    for r in rows:
        print(f"  {capacity.SHORT[r.architecture]:<38}{r.load * 100:7.1f}%{r.loss * 100:9.1f}%   {_bar(r.loss, 20)}")
    nd = capacity.cell_load("rakshasutra", a.tags, poles=a.poles, departures=False)
    print(f"  {'Rakshasutra without departure lists':<38}{nd.load * 100:7.1f}%{nd.loss * 100:9.1f}%   "
          f"{_bar(nd.loss, 20)}")
    for arch, text in capacity.ARCHITECTURES.items():
        print(f"    {capacity.SHORT[arch]}: {text}")
    return 0


def cmd_link(_a) -> int:
    print("Link budgets from Eq. 2 of the white paper (calculated; nothing measured yet)")
    for r in linkbudget.table():
        if "range_m" in r:
            print(f"  {r['link']:<42}{r['phy']:<16}{r['range_m']:7.1f} m at 98% delivery")
        else:
            print(f"  {r['link']:<42}{r['phy']:<16}{r['margin_8km_db']:+7.1f} dB margin at 8 km behind one ridge")
    return 0


def cmd_battery(_a) -> int:
    coded = power.adv_event_ms("coded")
    print("Wearable on a CR2450, 14 h a day on the trek   (calculated from Table V)")
    for label, kw in (("1M PHY, 1.25 ms per advertisement", {}), (f"Coded PHY, {coded:.2f} ms per advertisement",
                                                                  dict(tx_ms=coded))):
        print(f"  {label:<40}{power.active_current_ua(**kw):7.1f} uA   {power.battery_life_months(**kw):5.1f} "
              f"months at 25 C   {power.battery_life_months(cold=True, **kw):5.1f} months at -5 C")
    d = power.pulse_droop()
    print(f"  Buzzer pulse at -5 C with 100 uF: supply falls to {d['v_min']:.2f} V "
          f"({'below' if d['brownout'] else 'above'} the 1.70 V limit); needs {power.capacitor_needed_uf():.0f} uF")
    return 0


def cmd_bloom(a) -> int:
    print("64-byte Bloom heartbeat, 3 probes")
    for n in a.tags:
        print(f"  {n:5d} wearables at the pole   false positives {bloom.false_positive_rate(n) * 100:6.2f}%")
    return 0


def read_log(path: str) -> list[dict]:
    with open(path, newline="") as fh:
        return [dict(time_s=float(r["time_s"]), pole=int(r["pole"]), fport=int(r["fport"]),
                     payload=bytes.fromhex(r["payload"])) for r in csv.DictReader(fh)]


def load_registry(path: str) -> Registry:
    with open(path) as fh:
        data = json.load(fh)
    reg = Registry()
    for t in data["tags"]:
        reg.register(t["uid"], bytes.fromhex(t["key"]), t["c_init"], t["t_pair"], t.get("family", ""),
                     t.get("role", "band"))
    return reg


def cmd_trace(a) -> int:
    room = ControlRoom(load_registry(a.registry))
    log = read_log(a.log)
    for r in log:
        room.on_uplink(r["time_s"], r["pole"], r["fport"], r["payload"])
    if a.json:
        print(json.dumps([e.__dict__ for e in room.events]))
        return 0
    print(f"Rakshasutra {__version__}  |  {len(log)} uplinks from {len({r['pole'] for r in log})} poles, "
          f"{log[-1]['time_s'] - log[0]['time_s']:.0f} s")
    for e in room.events:
        where = "" if e.pole is None else f"pole {e.pole:<3d} {room.trek.pole(e.pole).segment:<11}"
        print(f"  {e.time:7.1f} s  {e.kind:<11}{(e.uid or ''):<13}{where:<21}{e.detail}")
    for uid, (pole, t) in sorted(room.registry.location.items()):
        print(f"  Last seen: {uid} at pole {pole} ({room.trek.pole(pole).segment}), {t:.0f} s")
    drops = sum(room.registry.stale_or_unknown.values())
    forged = sum(room.registry.forged_sos.values())
    print(f"  Dropped: {drops} unknown or stale, {forged} forged SOS")
    return 0


def cmd_audit(a) -> int:
    sim = {}
    if a.results:
        with open(a.results) as fh:
            sim = json.load(fh)
    items = audit.entries(sim)
    if a.json:
        print(json.dumps(items))
        return 0
    for e in items:
        print(f"  {e['id']}  {e['verdict']:<11} {e['claim']:<62} paper {e['paper']!s:>12}  model {e['model']!s} "
              f"{e['unit']}")
    s = audit.summary(items)
    print("  " + ", ".join(f"{v} {k}" for k, v in s.items()))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="rakshasutra", description="Reference model of the Rakshasutra system. "
                                "All results are calculated or simulated; no hardware has been measured.")
    p.add_argument("--version", action="version", version=f"rakshasutra {__version__}")
    sub = p.add_subparsers(dest="command", required=True)
    s = sub.add_parser("frame", help="build the signed 15-byte advertisement for one slot")
    s.add_argument("--key", required=True, help="16-byte tag key in hex")
    s.add_argument("--counter", type=int, default=0)
    s.add_argument("--sos", action="store_true")
    s.add_argument("--battery", type=float, default=3.0)
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_frame)
    s = sub.add_parser("verify", help="check a frame against a tag key")
    s.add_argument("frame", help="15 bytes in hex")
    s.add_argument("--key", required=True)
    s.set_defaults(fn=cmd_verify)
    s = sub.add_parser("airtime", help="LoRaWAN time on air")
    s.add_argument("--bytes", type=int, nargs="+", default=[15, 64, 200])
    s.add_argument("--sf", type=int, default=7, choices=range(7, 13))
    s.set_defaults(fn=cmd_airtime)
    s = sub.add_parser("capacity", help="load and loss of one gateway cell for each forwarding design")
    s.add_argument("--tags", type=int, default=3000)
    s.add_argument("--poles", type=int, default=60)
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_capacity)
    s = sub.add_parser("link", help="BLE and LoRa link budgets under the steel shelters")
    s.set_defaults(fn=cmd_link)
    s = sub.add_parser("battery", help="wearable battery life and the cold buzzer pulse")
    s.set_defaults(fn=cmd_battery)
    s = sub.add_parser("bloom", help="false-positive rate of the 64-byte heartbeat")
    s.add_argument("--tags", type=int, nargs="+", default=[25, 50, 100, 200, 300])
    s.set_defaults(fn=cmd_bloom)
    s = sub.add_parser("trace", help="replay a log of pole uplinks through the control room")
    s.add_argument("log", help="CSV with time_s, pole, fport, payload (hex)")
    s.add_argument("--registry", required=True, help="JSON file of paired wearables")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_trace)
    s = sub.add_parser("audit", help="every checkable number of the white paper, recomputed")
    s.add_argument("--results", help="results/summary.json, to include the simulated entries")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_audit)
    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
