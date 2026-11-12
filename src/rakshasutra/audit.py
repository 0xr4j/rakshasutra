"""Every checkable number in White Paper WP-01 (first draft, October 2026), recomputed.

Each entry gives what the first draft of the paper stated, what the model in this
repository gives when the paper's own equations and parameters are evaluated, and a
verdict:

  reproduced   the model gives the paper's number
  differs      the model gives a different number; the revised paper uses the model's
  design fix   the mechanism does not work as first specified; the fix is stated
  open         cannot be checked by calculation; needs a datasheet check or a measurement
"""
from __future__ import annotations

from . import bloom, capacity, kinematics, linkbudget, lora, power, resolver
from .params import P
from .trek import Trek

REPRODUCED, DIFFERS, FIX, OPEN = "reproduced", "differs", "design fix", "open"


def _close(a: float, b: float, rel: float = 0.01) -> bool:
    return abs(a - b) <= rel * max(abs(a), abs(b), 1e-12)


def entries(sim: dict | None = None) -> list[dict]:
    """The audit. `sim` may carry Monte Carlo results (results/summary.json) for the entries that need them."""
    sim = sim or {}
    out = []

    def add(section, claim, paper, model, verdict=None, note="", unit="", rel=0.01):
        if verdict is None:
            verdict = REPRODUCED if _close(float(paper), float(model), rel) else DIFFERS
        out.append(dict(id=f"A{len(out) + 1:02d}", section=section, claim=claim, paper=paper, model=model,
                        unit=unit, verdict=verdict, note=note))

    # --- time on air
    for b, ms, name in ((15, 66.82, "SOS frame"), (64, 138.50, "Bloom heartbeat"), (200, 338.18, "25-tag chunk")):
        add("V-A", f"Time on air, {name} ({b} B, SF7)", ms, round(lora.time_on_air(b) * 1000, 2), unit="ms")
    add("V-B", "Pseudonyms that fit one raw 222-byte list", 55, P["lora_max_app_bytes"] // 4, unit="IDs")
    # --- link budgets
    add("III-B", "Maximum allowable LoRa path loss, whip above the roof", 145.4,
        round(linkbudget.lora_mapl_db(), 1), unit="dB")
    add("III-B", "BLE Coded PHY margin at 50 m, heavy crowd", 28.6, round(linkbudget.ble_margin_db(50.0), 1),
        unit="dB", note="Eq. 2 with the stated parameters gives 20.3 dB. The first draft's figure needs "
        "8.3 dB of antenna gain that the paper does not specify.")
    rows = linkbudget.table()
    for row, paper, label in zip(rows[:3], (4.2, 28.5, 92.0),
                                 ("pole above the roof, 1M PHY, +4 dBm", "pole under the roof, 1M PHY",
                                  "pole under the roof, Coded PHY")):
        add("VI-A", f"BLE range at 98% delivery, {label}", paper, round(row["range_m"], 1), unit="m", rel=0.05,
            note="" if _close(paper, row["range_m"], 0.05) else
            "Eq. 2 gives a longer range than the first draft's table. Either way it covers the pole spacing.")
    add("VI-A", "LoRa range, whip above the roof", "5.4-8.8 km", f"{rows[4]['margin_8km_db']:.1f} dB margin at 8 km",
        OPEN, "The paper states no pole-to-gateway path-loss model, so a range cannot be recomputed. With "
        "free-space loss and one assumed 20 dB ridge the split antenna keeps a positive margin at 8 km.")
    add("VI-A", "LoRa range, antenna under the roof", "0.85 km", f"{rows[3]['margin_8km_db']:.1f} dB margin at 8 km",
        OPEN, "Same model: the 18.4 dB roof loss and 3 dB body loss leave a negative margin at 8 km.")
    # --- capacity
    tab = capacity.table()
    paper_iv = {"raw": [(188.0, 97.7), (376.0, 99.9), (752.0, 100.0), (1128.0, 100.0)],
                "single": [(6.5, 12.2), (13.0, 22.9), (26.0, 40.5), (39.0, 54.2)],
                "batch": [(3.0, 5.8), (6.0, 11.3), (9.2, 16.8), (12.5, 22.1)],
                "rakshasutra": [(2.1, 4.1), (4.2, 8.1), (6.4, 12.0), (8.6, 15.8)]}
    notes = {"raw": "Same order of magnitude; the paper does not give the size of a forwarded ping (7 B assumed here).",
             "single": "The first draft counted arrivals only; the model also counts the 60 s raw heartbeat.",
             "batch": "The first draft counted arrivals only; the model also counts the 60 s raw heartbeat.",
             "rakshasutra": "The model counts all three streams of Algorithm 2: arrival chunks, departure lists "
                            "and the Bloom heartbeat. The first draft's figures are not reached by any of them."}
    for arch, label in (("raw", "raw forwarding"), ("single", "single-event arrivals"),
                        ("batch", "15 s batching"), ("rakshasutra", "Rakshasutra")):
        for n, (g, loss), cell in zip((500, 1000, 2000, 3000), paper_iv[arch], tab[arch]):
            if n in (500, 3000):
                add("VI-B", f"Uplink loss, {label}, {n:,} tags in the cell", loss, round(cell.loss * 100, 1),
                    unit="%", rel=0.03, note=notes[arch])
    nodep = capacity.cell_load("rakshasutra", 3000, departures=False)
    add("VI-B", "Uplink loss, Rakshasutra without departure lists, 3,000 tags", 15.8, round(nodep.loss * 100, 1),
        FIX, "Departure lists (FPort 2) cost more airtime than the Bloom heartbeat saves. Dropping them, and "
        "inferring departure from the next arrival and the heartbeat, cuts the load by a third.", unit="%")
    single, rak = tab["single"][3], tab["rakshasutra"][3]
    add("Abstract", "Reduction in LoRa airtime, 3,000 tags", 82.4,
        round((1 - rak.airtime_per_s / single.airtime_per_s) * 100, 1), unit="%",
        note=f"Against single-event forwarding. Without departure lists the reduction is "
        f"{(1 - nodep.airtime_per_s / single.airtime_per_s) * 100:.1f}%.")
    dep = capacity.deployed_cell()
    add("VI-B", "Uplink loss in the deployed layout, 5,000 tags on the trek", "< 6", round(dep.loss * 100, 1),
        DIFFERS, f"{dep.tags} tags and {dep.poles} poles per gateway cell.", unit="%")
    # --- kinematics
    add("V-C", "Class A worst-case alert delay", 173, kinematics.class_a_delay_s(), unit="s")
    add("V-C", "Distance walked during that delay", 215, round(kinematics.walked_m(kinematics.class_a_delay_s())),
        unit="m")
    add("V-C", "Time an EV passenger spends in a 25 m core zone", 4.5, round(kinematics.ev_pass_s(), 1), unit="s")
    cap = kinematics.capture_probability(1, frame_success=kinematics.ble_frame_success(10.0, 150))
    add("V-C", "EV capture with one decoded frame required", 99.4, round(cap * 100, 1), unit="%",
        note="The paper gives no per-frame success rate. With 150 other wearables in range of the pole the "
        "model gives this figure; with 300 it falls to "
        f"{kinematics.capture_probability(1, frame_success=kinematics.ble_frame_success(10.0, 300)) * 100:.1f}%.")
    add("V-C", "Tether: chance one 5 ms scan hears the child's band", "assumed 1", round(
        kinematics.scan_hit_probability() * 100, 2), FIX,
        f"A 5 ms window every 5 s almost never coincides with an advertisement sent every 800 ms: four scans in "
        f"a row all miss {kinematics.tether_false_alarm() * 100:.0f}% of the time with the child beside the parent. "
        f"A window of {kinematics.tether_window_needed_s() * 1000:.0f} ms cannot miss; it costs "
        f"{kinematics.parent_tag_scan_ua(kinematics.tether_window_needed_s()):.0f} uA.", unit="%")
    add("V-C", "Tether: separation at which the alert sounds", "25-30 m",
        f"{linkbudget.ble_reliable_range_m():.0f} m", FIX,
        "Losing the signal happens at the edge of radio range, not at 25-30 m. To alert at 30 m the parent tag "
        f"must treat an RSSI below about {kinematics.rssi_gate_for_m(30.0):.0f} dBm as a miss.")
    # --- power
    add("VI-C", "Mean current on the trek (Table V)", 29.74, round(power.active_current_ua(), 2), unit="uA")
    add("VI-C", "Battery life at 25 C, from Table V", 14.2, round(power.battery_life_months(), 1), unit="months",
        note="Table V as printed gives a much longer life than the first draft stated.")
    add("VI-C", "Battery life at -5 C, from Table V", 11.1, round(power.battery_life_months(cold=True), 1),
        unit="months", note="As above.")
    coded = power.adv_event_ms("coded")
    add("VI-C", "Transmit time per advertisement on Coded PHY", 1.25, round(coded, 2), DIFFERS,
        f"1.25 ms fits a 1M PHY event. On Coded PHY S=8 the same 15 bytes take {coded:.2f} ms, which gives "
        f"{power.battery_life_months(tx_ms=coded):.1f} months at 25 C and "
        f"{power.battery_life_months(cold=True, tx_ms=coded):.1f} months at -5 C.", unit="ms")
    d0 = power.pulse_droop(capacitor_uf=0.0)
    add("VI-C", "Supply during an unbuffered buzzer pulse at -5 C", 1.61, round(d0["v_min"], 2), unit="V")
    d = power.pulse_droop()
    add("VI-C", "Supply during the pulse with the 100 uF capacitor", 2.68, round(d["v_min"], 2), FIX,
        f"100 uF behind 42 ohm has a time constant of {d['time_constant_ms']:.1f} ms, far shorter than the 100 ms "
        f"pulse, so it does not hold the supply up. Either the capacitor must be at least "
        f"{power.capacitor_needed_uf():.0f} uF or the pulse current at most "
        f"{power.max_pulse_ma_without_capacitor():.1f} mA.", unit="V")
    # --- identity
    add("IV-E", "Chance of forging an SOS in one try", "2.33e-10", f"{2 ** -32:.2e}", REPRODUCED)
    add("IV-E", "Chance of forging a wake token in one try", "5.96e-08", f"{2 ** -24:.2e}", REPRODUCED)
    add("IV-D", "Pseudonyms are unique in the lookup table", "assumed",
        f"{resolver.collision_probability(10000) * 100:.0f}% chance of a clash", FIX,
        "With 10,000 tags and a three-slot window, two entries share a 32-bit pseudonym about one time in ten. "
        "The table therefore maps a pseudonym to a list and separates clashes by the slot counter.")
    add("IV-A", "Replayed frames are rejected", "all", "outside the 3-slot window", FIX,
        "Arrival tuples carry no MIC and poles hold no keys, so a frame replayed at another pole within its "
        "own slot window (up to 45 minutes) is accepted as a sighting. Only SOS frames are fully verified.")
    add("V-B", "Bloom heartbeat false-positive rate", "not stated",
        f"{bloom.false_positive_rate(50) * 100:.1f}% at 50 tags, {bloom.false_positive_rate(300) * 100:.0f}% at 300",
        OPEN, f"64 bytes hold about {bloom.capacity_for(0.05)} wearables at a 5% error rate. Dense hub poles are "
        "on fibre and can send a larger filter.")
    # --- parts and layout
    t = Trek()
    spacing = max(z["spacing_m"] for z in t.zone_summary())
    add("III-A", "Pole spacing on the LoRa tracks", "25-100 m", f"{spacing:.0f} m", DIFFERS,
        "195 poles over 21.0 km of track is one pole per 108 m. Still inside the Coded PHY range of Eq. 2.")
    add("III-B", "Wearable transmit power on the nRF52811", "+8 dBm", "+4 dBm", OPEN,
        "The nRF52811 is specified up to +4 dBm. +8 dBm needs a part such as the nRF52820 or nRF52833. "
        "To be confirmed against the datasheet before the bill of materials is fixed.")
    if "sos" in sim:
        s = sim["sos"]
        add("Abstract", "SOS reaches the control room within 4 s (3,000-tag surge)", "all",
            f"{s['within_4s'] * 100:.0f}% (median {s['median_s']:.1f} s)", DIFFERS,
            f"Simulation. The first LoRa attempt is lost {s['first_try_loss'] * 100:.0f}% of the time under the "
            f"surge, and a repeat waits an assumed {P['lorawan_retry_s']:.0f} s. On fibre poles every SOS "
            "arrives in under a second.")
    return out


def summary(items: list[dict]) -> dict:
    return {v: sum(1 for e in items if e["verdict"] == v) for v in (REPRODUCED, DIFFERS, FIX, OPEN)}
