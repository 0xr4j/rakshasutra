"""Run every study and save the results. A few minutes on one core; all seeds are fixed.

    python experiments/run_all.py            full run
    python experiments/run_all.py --quick    smaller Monte Carlo sizes, for a smoke test
"""
import csv
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "src"))
from rakshasutra import audit, bloom, capacity, kinematics, linkbudget, lora, power, resolver, simulate  # noqa: E402
from rakshasutra.params import P  # noqa: E402
from rakshasutra.trek import Trek  # noqa: E402

RES = os.path.join(ROOT, "results")
QUICK = "--quick" in sys.argv


def save_csv(name, header, rows):
    with open(os.path.join(RES, name), "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def r(x, n=4):
    return round(float(x), n)


def main():
    os.makedirs(RES, exist_ok=True)
    S = {"version": "2026.11", "note": "All values are calculated or simulated. Nothing has been measured."}

    # 1. time on air
    S["airtime_ms"] = {str(b): r(lora.time_on_air(b) * 1000, 2) for b in (7, 8, 15, 16, 64, 200, 222)}
    S["airtime_sos_sf9_ms"] = r(lora.time_on_air(15, sf=9) * 1000, 2)

    # 2. capacity: the recomputed Table IV, a fine curve, and the no-departure variant
    counts = (500, 1000, 2000, 3000)
    rows, S["capacity"] = [], {}
    for arch in list(capacity.ARCHITECTURES) + ["rakshasutra-nodep"]:
        S["capacity"][arch] = []
        for n in counts:
            c = capacity.cell_load("rakshasutra", n, departures=False) if arch.endswith("nodep") \
                else capacity.cell_load(arch, n)
            S["capacity"][arch].append(dict(tags=n, load=r(c.load), loss=r(c.loss), oversize=r(c.oversize_probability),
                                            airtime_s=r(c.airtime_per_s),
                                            streams={s.name: dict(frames_per_s=r(s.frames_per_s), mean_bytes=r(s.mean_bytes, 1),
                                                                  loss=r(c.loss_by_stream[s.name])) for s in c.streams}))
            rows.append([arch, n, r(c.load), r(c.loss), r(c.oversize_probability)])
    save_csv("capacity_table.csv", ["architecture", "tags", "load", "loss", "oversize_probability"], rows)
    curve = []
    for n in range(100, 5001, 100):
        row = [n]
        for arch in ("single", "batch", "rakshasutra"):
            row.append(r(capacity.cell_load(arch, n).loss))
        row.append(r(capacity.cell_load("rakshasutra", n, departures=False).loss))
        curve.append(row)
    save_csv("capacity_curve.csv", ["tags", "single", "batch", "rakshasutra", "rakshasutra_nodep"], curve)
    single, rak = capacity.cell_load("single", 3000), capacity.cell_load("rakshasutra", 3000)
    nodep, batch = capacity.cell_load("rakshasutra", 3000, departures=False), capacity.cell_load("batch", 3000)
    S["airtime_reduction_vs_single"] = r(1 - rak.airtime_per_s / single.airtime_per_s)
    S["airtime_reduction_vs_single_nodep"] = r(1 - nodep.airtime_per_s / single.airtime_per_s)
    S["airtime_change_vs_batch"] = r(rak.airtime_per_s / batch.airtime_per_s - 1)
    S["airtime_change_vs_batch_nodep"] = r(nodep.airtime_per_s / batch.airtime_per_s - 1)
    cross = next(n for n in range(100, 6000, 10)
                 if capacity.cell_load("rakshasutra", n, departures=False).load < capacity.cell_load("batch", n).load)
    S["bloom_pays_from_tags"] = cross
    dep = capacity.deployed_cell()
    dep_nd = capacity.cell_load("rakshasutra", dep.tags, poles=dep.poles, departures=False)
    S["deployed"] = dict(tags=dep.tags, poles=dep.poles, load=r(dep.load), loss=r(dep.loss),
                         load_nodep=r(dep_nd.load), loss_nodep=r(dep_nd.loss))

    # 3. Monte Carlo check of the capacity formula
    secs = 600 if QUICK else 3600
    mc = []
    for arch in ("single", "batch", "rakshasutra"):
        for n in counts:
            sim = simulate.simulate_cell(arch, n, seconds=secs, seed=11)
            model = capacity.cell_load(arch, n)
            mc.append([arch, n, sim["frames"], r(sim["load"]), r(model.load), r(sim["loss"]), r(model.loss)])
    for n in counts:
        sim = simulate.simulate_cell("rakshasutra", n, seconds=secs, seed=11, departures=False)
        model = capacity.cell_load("rakshasutra", n, departures=False)
        mc.append(["rakshasutra-nodep", n, sim["frames"], r(sim["load"]), r(model.load), r(sim["loss"]), r(model.loss)])
    save_csv("montecarlo_cell.csv", ["architecture", "tags", "frames", "load_sim", "load_model", "loss_sim",
                                     "loss_model"], mc)
    S["montecarlo"] = dict(seconds=secs, frames=sum(m[2] for m in mc),
                           max_abs_loss_error=r(max(abs(m[5] - m[6]) for m in mc)),
                           max_abs_load_error=r(max(abs(m[3] - m[4]) for m in mc)))

    # 4. link budget
    lb = linkbudget.table()
    S["link"] = dict(rows=[{k: (r(v, 2) if isinstance(v, float) else v) for k, v in row.items()} for row in lb],
                     margin_50m_db=r(linkbudget.ble_margin_db(50.0), 1), mapl_db=r(linkbudget.lora_mapl_db(), 1),
                     core_zone_gate_m=r(10 ** ((P["ble_tx_dbm"] - P["ble_pl0_db"] - P["ble_body_db"]
                                               - P["rssi_gate_track_dbm"]) / (10 * P["ble_exponent"])), 1),
                     hub_gate_m=r(10 ** ((P["ble_tx_dbm"] - P["ble_pl0_db"] - P["ble_body_db"]
                                         - P["rssi_gate_hub_dbm"]) / (10 * P["ble_exponent"])), 1))
    save_csv("link_curve.csv", ["distance_m", "margin_1m_db", "margin_coded_db", "delivery_1m", "delivery_coded"],
             [[d, r(linkbudget.ble_margin_db(d, P["ble_sens_1m_dbm"]), 2), r(linkbudget.ble_margin_db(d), 2),
               r(linkbudget.delivery_probability(linkbudget.ble_margin_db(d, P["ble_sens_1m_dbm"]))),
               r(linkbudget.delivery_probability(linkbudget.ble_margin_db(d)))] for d in range(1, 301)])

    # 5. power
    coded = power.adv_event_ms("coded")
    S["power"] = dict(
        table=[{k: (r(v) if isinstance(v, float) else v) for k, v in row.items()} for row in power.budget()],
        active_ua=r(power.active_current_ua(), 2), life_warm=r(power.battery_life_months(), 1),
        life_cold=r(power.battery_life_months(cold=True), 1), adv_ms_1m=r(power.adv_event_ms("1m"), 3),
        adv_ms_coded=r(coded, 3), active_ua_coded=r(power.active_current_ua(tx_ms=coded), 1),
        life_warm_coded=r(power.battery_life_months(tx_ms=coded), 1),
        life_cold_coded=r(power.battery_life_months(cold=True, tx_ms=coded), 1),
        droop_unbuffered=r(power.pulse_droop(capacitor_uf=0)["v_min"], 2),
        droop_100uf=r(power.pulse_droop()["v_min"], 2), tau_ms=r(power.pulse_droop()["time_constant_ms"], 1),
        capacitor_needed_uf=r(power.capacitor_needed_uf(), 0), max_pulse_ma=r(power.max_pulse_ma_without_capacitor(), 1))
    save_csv("droop_curve.csv", ["capacitor_uf", "v_min"],
             [[c, r(power.pulse_droop(capacitor_uf=c)["v_min"], 3)] for c in
              (0, 10, 22, 47, 100, 220, 330, 470, 680, 1000, 1500, 2200, 3300, 4700, 10000)])

    # 6. tether
    hours = 14 if QUICK else 140
    tether = []
    for w_ms in (5, 20, 50, 100, 200, 400, 600, 800, 812):
        sim = simulate.simulate_tether(window_s=w_ms / 1000.0, hours=hours, seed=4)
        tether.append([w_ms, r(kinematics.scan_hit_probability(w_ms / 1000.0)), r(sim["hit_rate"]),
                       r(sim["time_in_alarm"]), r(sim["scan_current_ua"], 1)])
    save_csv("tether.csv", ["window_ms", "hit_model", "hit_sim", "time_in_false_alarm", "scan_current_ua"], tether)
    need = kinematics.tether_window_needed_s()
    S["tether"] = dict(hit_5ms=r(kinematics.scan_hit_probability(), 4), miss4_5ms=r(kinematics.tether_false_alarm(), 3),
                       time_in_false_alarm_5ms=tether[0][3], window_needed_ms=r(need * 1000, 0),
                       scan_ua_needed=r(kinematics.parent_tag_scan_ua(need), 0), scan_ua_5ms=r(kinematics.parent_tag_scan_ua(0.005), 1),
                       parent_life_months=r(P["battery_mah"] * 1000 / (P["active_hours"] * (kinematics.parent_tag_scan_ua(need) + power.active_current_ua())
                                                                      + (24 - P["active_hours"]) * P["i_rack_ua"]) / power.DAYS_PER_MONTH, 1),
                       alert_delay_s=kinematics.tether_alert_delay_s(), range_m=r(linkbudget.ble_reliable_range_m(), 0),
                       rssi_gate_30m=r(kinematics.rssi_gate_for_m(30.0), 0))

    # 7. electric vehicles
    passes = 4000 if QUICK else 40000
    ev = []
    for crowd in (0, 50, 100, 150, 200, 300, 400):
        p = kinematics.ble_frame_success(10.0, crowd)
        ev.append([crowd, r(p), r(kinematics.capture_probability(1, frame_success=p)),
                   r(simulate.simulate_ev(1, crowd=crowd, passes=passes, seed=5)["capture"]),
                   r(kinematics.capture_probability(3, frame_success=p))])
    save_csv("ev_capture.csv", ["crowd", "frame_success", "capture_h1_model", "capture_h1_sim", "capture_h3_model"], ev)
    S["ev"] = dict(pass_s=r(kinematics.ev_pass_s(), 2), capture_150=ev[3][2], capture_300=ev[5][2],
                   slow2_h3=r(kinematics.capture_probability(3, adv_interval_s=2.0)),
                   slow5_h3=r(kinematics.capture_probability(3, adv_interval_s=5.0)),
                   slow5_h1=r(kinematics.capture_probability(1, adv_interval_s=5.0)),
                   class_a_s=kinematics.class_a_delay_s(), class_a_walk_m=r(kinematics.walked_m(kinematics.class_a_delay_s()), 0))

    # 8. SOS latency
    trials = 20000 if QUICK else 200000
    S["sos"] = {k: r(v) if isinstance(v, float) else v for k, v in simulate.simulate_sos(trials=trials, seed=6).items()}
    S["sos_500"] = {k: r(v) if isinstance(v, float) else v
                    for k, v in simulate.simulate_sos(tags=500, trials=trials, seed=6).items()}
    S["sos_fiber"] = {k: r(v) if isinstance(v, float) else v
                      for k, v in simulate.simulate_sos(trials=trials, seed=6, fiber=True).items()}

    # 9. Bloom heartbeat and pseudonyms
    save_csv("bloom.csv", ["tags", "false_positive_rate"], [[n, r(bloom.false_positive_rate(n), 5)] for n in range(0, 401, 5)])
    S["bloom"] = dict(fpr_50=r(bloom.false_positive_rate(50)), fpr_100=r(bloom.false_positive_rate(100)),
                      fpr_300=r(bloom.false_positive_rate(300)), cap_1pct=bloom.capacity_for(0.01),
                      cap_5pct=bloom.capacity_for(0.05))
    S["pseudonym_clash_10000"] = r(resolver.collision_probability(10000))

    # 10. the trek
    t = Trek()
    S["trek"] = dict(poles=len(t.poles), zones=[{k: (r(v, 1) if isinstance(v, float) else v) for k, v in z.items()}
                                                for z in t.zone_summary()],
                     end_to_end_km=r(t.distance(1, len(t.poles)) / 1000, 2),
                     branch_example_m=r(t.distance(t.last["himkoti"], t.first["sanjichhat"]), 0))

    # 11. the family walk
    w = simulate.family_walk()
    sep = next(e for e in w["room"].events if e.kind == "SEPARATION")
    sos = next(e for e in w["room"].events if e.kind == "SOS")
    S["walk"] = dict(uplinks=len(w["log"]), split_s=r(w["split_s"], 1), separation_flag_s=r(sep.time, 1),
                     separation_delay_s=r(sep.time - w["split_s"], 1), separation_detail=sep.detail,
                     sos_pressed_s=r(w["sos_s"], 1), sos_alarm_s=r(sos.time, 1), sos_delay_s=r(sos.time - w["sos_s"], 2),
                     sos_pole=sos.pole, events=len(w["room"].events))

    # 12. the audit
    items = audit.entries(S)
    S["audit_summary"] = audit.summary(items)
    with open(os.path.join(RES, "audit.json"), "w") as fh:
        json.dump(items, fh, indent=1)
    with open(os.path.join(RES, "summary.json"), "w") as fh:
        json.dump(S, fh, indent=1)
    print("wrote results/: summary.json, audit.json and", len([f for f in os.listdir(RES) if f.endswith(".csv")]), "CSV files")
    print("audit:", S["audit_summary"])


if __name__ == "__main__":
    main()
