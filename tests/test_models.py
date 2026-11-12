"""Link budget, power, kinematics and the trek graph."""
import math

from rakshasutra import kinematics as k
from rakshasutra import linkbudget as lb
from rakshasutra import power, simulate
from rakshasutra.params import P
from rakshasutra.trek import Trek


# ---------------------------------------------------------------- link budget
def test_lora_mapl_matches_the_white_paper():
    assert round(lb.lora_mapl_db(), 1) == 145.4


def test_ble_margin_from_eq_2():
    expected = 8.0 - 40.2 - 10 * 2.15 * math.log10(50) - 14.0 + 103.0
    assert math.isclose(lb.ble_margin_db(50.0), expected)
    assert round(lb.ble_margin_db(50.0), 1) == 20.3


def test_reliable_range_is_where_delivery_meets_98_percent():
    for row in lb.table()[:3]:
        d = row["range_m"]
        m = lb.ble_margin_db(d, row["sens_dbm"], tx_dbm=row["tx_dbm"], roof_loss_db=row["roof_db"])
        assert math.isclose(lb.delivery_probability(m), 0.98, abs_tol=1e-6)
    r = [row["range_m"] for row in lb.table()[:3]]
    assert round(r[0], 1) == 4.1 and round(r[1]) == 82 and round(r[2]) == 174


def test_split_antenna_recovers_the_roof_loss():
    under, over = lb.table()[3], lb.table()[4]
    assert math.isclose(over["mapl_db"] - under["mapl_db"], 18.4 + 3.0 - 0.9)
    assert under["margin_8km_db"] < 0 < over["margin_8km_db"]


# ---------------------------------------------------------------- power
def test_table_v_mean_current():
    rows = power.budget()
    assert round(rows[1]["mean_ua"], 2) == 22.19 and round(rows[2]["mean_ua"], 2) == 5.75
    assert round(power.active_current_ua(), 2) == 29.74


def test_advertising_event_lengths():
    assert math.isclose(power.adv_event_ms("1m"), 0.792)
    assert math.isclose(power.adv_event_ms("coded"), 5.952)


def test_battery_life_is_pinned():
    assert round(power.battery_life_months(), 1) == 48.2
    assert round(power.battery_life_months(cold=True), 1) == 33.8
    coded = power.adv_event_ms("coded")
    assert round(power.battery_life_months(tx_ms=coded), 1) == 12.8
    assert round(power.battery_life_months(cold=True, tx_ms=coded), 1) == 9.0


def test_cold_pulse_droop():
    assert round(power.pulse_droop(capacitor_uf=0)["v_min"], 2) == 1.61       # the paper's unbuffered figure
    d = power.pulse_droop()
    assert d["brownout"] and round(d["v_min"], 2) == 1.61                     # 100 uF does not help
    need = power.capacitor_needed_uf()
    assert 880 < need < 910
    assert not power.pulse_droop(capacitor_uf=need * 1.01)["brownout"]
    assert power.pulse_droop(capacitor_uf=need * 0.99)["brownout"]
    assert round(power.max_pulse_ma_without_capacitor(), 1) == 29.8


def test_droop_matches_a_time_stepped_circuit():
    """Integrate the RC circuit directly and compare with the closed form."""
    r, c, i, v0 = 42.0, 470e-6, 0.032, 2.95
    v, dt, lowest = v0, 1e-5, v0
    for step in range(int(5.0 / dt)):
        load = i if (step * dt) % 0.5 < 0.1 else 0.0
        v += dt * ((v0 - v) / r - load) / c
        lowest = min(lowest, v) if step * dt > 4.0 else lowest
    assert abs(lowest - power.pulse_droop(capacitor_uf=470)["v_min"]) < 0.005


# ---------------------------------------------------------------- kinematics
def test_class_a_trap():
    assert k.class_a_delay_s() == 173
    assert round(k.walked_m(173)) == 216


def test_ev_capture():
    assert round(k.ev_pass_s(), 1) == 4.5
    assert math.floor(k.ev_pass_s() / 0.8) == 5
    assert k.capture_probability(1) == 1.0
    assert k.capture_probability(3, adv_interval_s=5.0) == 0.0                # slow ping: three hits impossible
    assert k.capture_probability(3, adv_interval_s=2.0) < 0.26
    p = k.ble_frame_success(10.0, 150)
    assert round(k.capture_probability(1, frame_success=p), 3) == 0.997


def test_ev_simulation_agrees_with_the_formula():
    sim = simulate.simulate_ev(1, crowd=300, passes=6000, seed=2)["capture"]
    model = k.capture_probability(1, frame_success=k.ble_frame_success(10.0, 300))
    assert abs(sim - model) < 0.02


def test_tether_scan_window():
    assert k.scan_hit_probability() < 0.006                    # 5 ms window: almost never
    assert k.tether_false_alarm() > 0.97
    w = k.tether_window_needed_s()
    assert 0.81 < w < 0.82 and k.scan_hit_probability(w) == 1.0
    assert round(k.parent_tag_scan_ua(w)) == 746


def test_tether_simulation():
    narrow = simulate.simulate_tether(hours=4, seed=1)
    wide = simulate.simulate_tether(window_s=k.tether_window_needed_s(), hours=4, seed=1)
    assert abs(narrow["hit_rate"] - k.scan_hit_probability()) < 0.004
    assert narrow["false_alarms"] > 0 and wide["false_alarms"] == 0 and wide["hit_rate"] == 1.0


def test_sos_latency_simulation():
    s = simulate.simulate_sos(seed=1)
    assert s["delivered"] > 0.999 and 0.4 < s["median_s"] < 0.7 and 0.88 < s["within_4s"] < 0.95
    f = simulate.simulate_sos(seed=1, fiber=True)
    assert f["within_4s"] == 1.0 and f["p95_s"] < 1.0


# ---------------------------------------------------------------- trek
def test_trek_totals():
    t = Trek()
    zones = t.zone_summary()
    assert len(t.poles) == P["poles_total"] == 255
    assert math.isclose(sum(z["km"] for z in zones), P["trek_km"])
    assert sum(z["poles"] for z in zones if z["fiber"]) == P["poles_fiber"]
    assert min(p.altitude_m for p in t.poles) >= 762 and max(p.altitude_m for p in t.poles) <= 2017


def test_distance_is_a_metric_on_the_graph():
    t = Trek()
    a, b, c = t.first["old-track"] + 10, t.first["himkoti"] + 4, t.last["bhairon"]
    assert t.distance(a, a) == 0
    assert math.isclose(t.distance(a, b), t.distance(b, a))
    assert t.distance(a, c) <= t.distance(a, b) + t.distance(b, c) + 1e-9


def test_branches_are_far_apart_even_when_pole_numbers_are_close():
    t = Trek()
    a, b = t.last["himkoti"], t.first["sanjichhat"]                 # consecutive pole numbers
    assert abs(a - b) == 1
    assert t.distance(a, b) > 3000                                  # but over 3 km apart by track


def test_hits_required_by_zone():
    t = Trek()
    assert t.pole(t.first["old-track"]).hits_required == 1
    assert t.pole(t.first["adhkuwari"]).hits_required == 3
    assert t.pole(t.first["bhawan"]).rssi_gate_dbm == -65.0


def test_neighbourhood_is_five_poles_on_a_line_and_more_at_a_junction():
    t = Trek()
    mid = t.first["tarakote"] + 30
    assert t.neighbourhood(mid) == [mid - 2, mid - 1, mid, mid + 1, mid + 2]
    assert len(t.neighbourhood(t.last["adhkuwari"])) > 5
