"""Draw every figure from the saved results. Writes generated/fig/*.pdf (for the PDFs)
and docs/img/*.png (for the README and the website)."""
import csv
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "src"))
from rakshasutra import capacity, simulate  # noqa: E402
from rakshasutra.params import P  # noqa: E402
from rakshasutra.trek import SEGMENTS, Trek  # noqa: E402

RES, FIG, IMG = (os.path.join(ROOT, d) for d in ("results", "generated/fig", "docs/img"))
INK, MUTED, GRID, PAPER = "#171A2B", "#6A6F85", "#E4DFD3", "#FFFFFF"
RED, INDIGO, OCHRE, TEAL, GREY = "#C0271D", "#2F4B9A", "#B8860B", "#0E8F84", "#9AA0AE"
# colour follows the design, in every figure
COLOR = {"raw": GREY, "single": OCHRE, "batch": INDIGO, "rakshasutra": RED, "rakshasutra_nodep": TEAL}
LABEL = {"raw": "Raw forwarding", "single": "Single-event arrivals", "batch": "15 s batching",
         "rakshasutra": "Rakshasutra, as specified", "rakshasutra_nodep": "Rakshasutra, no departure lists"}

family = "Inter" if any("Inter" in f.name for f in font_manager.fontManager.ttflist) else "DejaVu Sans"
plt.rcParams.update({
    "font.family": family, "font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "axes.titlesize": 10, "axes.titleweight": "bold", "axes.titlelocation": "left", "lines.linewidth": 2,
    "legend.frameon": False, "figure.facecolor": PAPER, "axes.facecolor": PAPER, "savefig.facecolor": PAPER,
    "pdf.fonttype": 3})


def rows(name):
    with open(os.path.join(RES, name), newline="") as fh:
        return list(csv.DictReader(fh))


def save(fig, name):
    fig.savefig(os.path.join(FIG, name + ".pdf"), bbox_inches="tight")
    fig.savefig(os.path.join(IMG, name + ".png"), dpi=200, bbox_inches="tight")
    plt.close(fig)


def end_label(ax, x, y, text, color, dy=0):
    ax.annotate(text, (x, y), xytext=(6, dy), textcoords="offset points", va="center", fontsize=8, color=INK)
    ax.plot([x], [y], "o", ms=5, color=color, mec=PAPER, mew=1.2, zorder=5)


def fig_capacity():
    curve, mc = rows("capacity_curve.csv"), rows("montecarlo_cell.csv")
    fig, (a, b) = plt.subplots(1, 2, figsize=(9.6, 3.6), gridspec_kw=dict(width_ratios=[1.35, 1], wspace=0.34))
    curve = [r for r in curve if int(r["tags"]) <= 3000]
    x = [int(r["tags"]) for r in curve]
    offs = {"single": 0, "batch": 1, "rakshasutra": 2, "rakshasutra_nodep": -3}
    for key in ("single", "batch", "rakshasutra", "rakshasutra_nodep"):
        y = [100 * float(r[key]) for r in curve]
        a.plot(x, y, color=COLOR[key], label=LABEL[key])
        i = x.index(3000)
        end_label(a, 3000, y[i], f"{y[i]:.0f}%", COLOR[key], dy=offs[key])
    for r in mc:
        key = r["architecture"].replace("-", "_")
        a.plot(int(r["tags"]), 100 * float(r["loss_sim"]), "s", ms=4.5, mfc=PAPER, mec=COLOR[key], mew=1.4, zorder=4)
    a.plot([], [], "s", ms=4.5, mfc=PAPER, mec=MUTED, mew=1.4, label="Monte Carlo, one hour on air")
    a.set_xlim(0, 3350), a.set_ylim(0, 65)
    a.set_xlabel("Wearables in one gateway cell (60 poles, 8 channels)"), a.set_ylabel("Uplink frames lost (%)")
    a.set_title("Loss in a crowd surge (calculated)")
    a.legend(loc="upper left", fontsize=7.6, handlelength=1.6)
    # airtime by stream at 3,000 wearables
    cells = [("single", capacity.cell_load("single", 3000)), ("batch", capacity.cell_load("batch", 3000)),
             ("rakshasutra", capacity.cell_load("rakshasutra", 3000)),
             ("rakshasutra_nodep", capacity.cell_load("rakshasutra", 3000, departures=False))]
    shade = {"arrival": 1.0, "arrival batch": 1.0, "arrival chunk": 1.0, "departure list": 0.62,
             "raw ID heartbeat": 0.34, "Bloom heartbeat": 0.34}
    b.barh([0], [0], color=MUTED, alpha=1.0, label="arrivals")
    b.barh([0], [0], color=MUTED, alpha=0.62, label="departure lists")
    b.barh([0], [0], color=MUTED, alpha=0.34, label="60 s heartbeat")
    b.legend(loc="lower right", fontsize=7.6, handlelength=1.2)
    names = {"arrival": "arrivals", "arrival batch": "arrivals", "arrival chunk": "arrivals",
             "departure list": "departures", "raw ID heartbeat": "heartbeat", "Bloom heartbeat": "heartbeat"}
    for i, (key, cell) in enumerate(cells):
        left = 0.0
        for s in cell.streams:
            w = 100 * s.airtime_per_s / P["lora_channels"]
            b.barh(i, w, left=left, height=0.56, color=COLOR[key], alpha=shade[s.name], edgecolor=PAPER, linewidth=1.5)
            if w > 6:
                b.text(left + w / 2, i, names[s.name], ha="center", va="center", fontsize=7,
                       color="white" if shade[s.name] > 0.5 else INK)
            left += w
        b.text(left + 1.0, i, f"{left:.1f}%", va="center", fontsize=8)
    b.set_yticks(range(4), ["Single-event", "15 s batching", "Rakshasutra,\nas specified", "Rakshasutra,\nno departures"])
    b.invert_yaxis(), b.set_xlim(0, 52), b.grid(axis="y", visible=False)
    b.set_xlabel("Channel load G at 3,000 wearables (%)"), b.set_title("Where the airtime goes")
    save(fig, "capacity")


def fig_link():
    c = rows("link_curve.csv")
    d = [int(r["distance_m"]) for r in c]
    fig, ax = plt.subplots(figsize=(6.2, 3.3))
    ax.plot(d, [100 * float(r["delivery_1m"]) for r in c], color=INDIGO, label="1M PHY, sensitivity -96 dBm")
    ax.plot(d, [100 * float(r["delivery_coded"]) for r in c], color=RED, label="Coded PHY S=8, -103 dBm")
    ax.axhline(98, color=MUTED, lw=0.8, ls=(0, (4, 3)))
    ax.text(298, 96.3, "98% delivery", ha="right", va="top", fontsize=7.5, color=MUTED)
    for x, col in ((82.2, INDIGO), (174.0, RED)):
        ax.plot([x], [98], "o", ms=6, color=col, mec=PAPER, mew=1.3, zorder=5)
        ax.annotate(f"{x:.0f} m", (x, 98), xytext=(0, -13), textcoords="offset points", ha="center", fontsize=8)
    ax.axvspan(0, 108, color=GRID, alpha=0.5, lw=0)
    ax.text(54, 22, "pole spacing on the\nLoRa tracks, up to 108 m", ha="center", fontsize=7.5, color=MUTED)
    ax.set_xlim(0, 300), ax.set_ylim(0, 103)
    ax.set_xlabel("Distance from wearable to pole, under the steel roof (m)")
    ax.set_ylabel("Frames above sensitivity (%)")
    ax.set_title("BLE link from Eq. 2: +8 dBm, 14 dB body loss (calculated, not measured)")
    ax.legend(loc="lower left", fontsize=8)
    save(fig, "link")


def fig_power(S):
    p = S["power"]
    fig, (a, b) = plt.subplots(1, 2, figsize=(9.6, 3.3), gridspec_kw=dict(wspace=0.3))
    vals = [("1M PHY\n25 °C", p["life_warm"], INDIGO), ("1M PHY\n-5 °C", p["life_cold"], INDIGO),
            ("Coded PHY\n25 °C", p["life_warm_coded"], RED), ("Coded PHY\n-5 °C", p["life_cold_coded"], RED)]
    for i, (lab, v, col) in enumerate(vals):
        a.bar(i, v, width=0.55, color=col, alpha=1.0 if i % 2 == 0 else 0.6)
        a.text(i, v + 1, f"{v:.1f}", ha="center", fontsize=8.5)
    a.set_xticks(range(4), [v[0] for v in vals]), a.grid(axis="x", visible=False)
    a.set_ylabel("Months on one CR2450, 14 h a day"), a.set_ylim(0, 56)
    a.set_title("Battery life depends on the PHY (calculated)")
    d = rows("droop_curve.csv")
    x, y = [max(float(r["capacitor_uf"]), 5) for r in d], [float(r["v_min"]) for r in d]
    b.semilogx(x, y, color=RED, marker="o", ms=4, mec=PAPER, mew=1)
    b.axhline(P["brownout_v"], color=INK, lw=0.9, ls=(0, (4, 3)))
    b.text(6, P["brownout_v"] + 0.03, "brown-out, 1.70 V", fontsize=7.5, color=INK)
    b.annotate("100 µF, as specified:\n1.61 V", (100, y[4]), xytext=(18, 62), textcoords="offset points", fontsize=8,
               arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
    b.annotate(f"needs {p['capacitor_needed_uf']:.0f} µF", (p["capacitor_needed_uf"], 1.70), xytext=(8, -18),
               textcoords="offset points", fontsize=8)
    b.set_xlabel("Hold-up capacitor (µF)"), b.set_ylabel("Lowest supply during the pulse (V)")
    b.set_title("Buzzer pulse at -5 °C: 32 mA through 42 Ω")
    b.set_ylim(1.5, 3.0)
    save(fig, "power")


def fig_tether_ev():
    t, e = rows("tether.csv"), rows("ev_capture.csv")
    fig, (a, b) = plt.subplots(1, 2, figsize=(9.6, 3.3), gridspec_kw=dict(wspace=0.3))
    x = [float(r["window_ms"]) for r in t]
    a.plot(x, [100 * float(r["hit_sim"]) for r in t], color=RED, marker="o", ms=4.5, mec=PAPER, mew=1,
           label="Scans that hear the band")
    a.plot(x, [100 * float(r["time_in_false_alarm"]) for r in t], color=INDIGO, marker="s", ms=4.5, mec=PAPER, mew=1,
           label="Time spent in false alarm")
    a.annotate("5 ms, as specified", (5, 98), xytext=(60, 84), fontsize=8, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
    a.set_xlabel("Parent tag scan window every 5 s (ms)"), a.set_ylabel("%"), a.set_ylim(-3, 106)
    a.set_title("Tether, child beside the parent (simulated)")
    a.legend(loc="center right", fontsize=8)
    c = [int(r["crowd"]) for r in e]
    b.plot(c, [100 * float(r["capture_h1_model"]) for r in e], color=RED, label="One decoded frame required")
    b.plot(c, [100 * float(r["capture_h3_model"]) for r in e], color=INDIGO, label="Three frames required")
    b.plot(c, [100 * float(r["capture_h1_sim"]) for r in e], "s", ms=4.5, mfc=PAPER, mec=RED, mew=1.4, label="Monte Carlo")
    b.set_xlabel("Other wearables in range of the pole"), b.set_ylabel("Passes reported (%)"), b.set_ylim(0, 104)
    b.set_title("Passenger at 20 km/h, 800 ms advertising (calculated)")
    b.legend(loc="lower left", fontsize=8)
    save(fig, "tether_ev")


def fig_bloom():
    r = rows("bloom.csv")
    fig, ax = plt.subplots(figsize=(6.2, 3.1))
    ax.plot([int(x["tags"]) for x in r], [100 * float(x["false_positive_rate"]) for x in r], color=RED)
    for n in (50, 100, 300):
        y = 100 * float(next(x for x in r if int(x["tags"]) == n)["false_positive_rate"])
        ax.plot([n], [y], "o", ms=6, color=RED, mec=PAPER, mew=1.3)
        ax.annotate(f"{y:.1f}%" if y < 10 else f"{y:.0f}%", (n, y), xytext=(8, -4), textcoords="offset points", fontsize=8)
    ax.set_xlabel("Wearables held by one pole"), ax.set_ylabel("False positives (%)")
    ax.set_title("64-byte Bloom heartbeat, three probes (calculated)")
    ax.set_xlim(0, 400), ax.set_ylim(0, 80)
    save(fig, "bloom")


def fig_trek():
    t = Trek()
    fig, ax = plt.subplots(figsize=(9.6, 3.2))
    start = {"old-track": 0.0, "tarakote": 0.0}
    start["adhkuwari"] = 7.0
    start["himkoti"] = start["sanjichhat"] = 7.5
    start["bhawan"] = 11.0
    start["bhairon"] = 12.0
    stretch = {"old-track": 7.0 / 6.0, "sanjichhat": 3.5 / 3.0}
    label = {"old-track": "Zone 1 · old track, 6.0 km", "tarakote": "Zone 2 · Tarakote Marg, 7.0 km",
             "adhkuwari": "Zone 3 · Adhkuwari", "himkoti": "Zone 4 · Himkoti, 3.5 km (EV)",
             "sanjichhat": "Zone 4 · Sanjichhat, 3.0 km", "bhawan": "Zone 5 · Bhawan", "bhairon": "Zone 6 · Bhairon Ghati"}
    bump = {"old-track": 150, "tarakote": -150, "himkoti": -110, "sanjichhat": 110}
    for name, zone, km, n, a0, a1, fiber in SEGMENTS:
        ps = [p for p in t.poles if p.segment == name]
        x = [start[name] + p.along_m / 1000 * stretch.get(name, 1.0) for p in ps]
        frac = [p.along_m / (km * 1000) for p in ps]
        y = [p.altitude_m + bump.get(name, 0) * 4 * f * (1 - f) for p, f in zip(ps, frac)]
        ax.plot(x, y, color=RED if not fiber else INK, lw=1.4, zorder=2)
        ax.scatter(x, y, s=9 if not fiber else 6, color=PAPER, edgecolors=RED if not fiber else INK, linewidths=0.9, zorder=3)
        mid = len(x) // 2
        up = name in ("old-track", "sanjichhat", "adhkuwari")
        off = {"bhawan": (6, -16), "bhairon": (-10, 2), "adhkuwari": (-14, 12)}.get(name, (0, 12 if up else -14))
        ax.annotate(label[name], (x[mid], y[mid]), xytext=off, textcoords="offset points",
                    ha={"bhairon": "right"}.get(name, "center"), va="bottom" if (up or name == "bhairon") else "top",
                    fontsize=7.6)
    ax.plot([], [], color=RED, marker="o", ms=4, mfc=PAPER, label="LoRaWAN pole (195)")
    ax.plot([], [], color=INK, marker="o", ms=3.5, mfc=PAPER, label="fibre-LAN pole (60)")
    ax.legend(loc="upper left", fontsize=8)
    ax.set_xlabel("Schematic distance along the route (km); parallel tracks drawn side by side")
    ax.set_ylabel("Altitude (m)"), ax.set_ylim(600, 2150), ax.set_xlim(-0.3, 13.9)
    ax.set_title("The route as a branched graph of 255 poles (schematic, not a survey)")
    save(fig, "trek")


def fig_walk():
    w = simulate.family_walk()
    room, trek = w["room"], w["trek"]
    ref = trek.last["old-track"] - 3
    fig, ax = plt.subplots(figsize=(9.6, 3.3))
    for uid, col, name in (("tag-0421", INDIGO, "Parent tag"), ("band-0421", RED, "Child's band")):
        tr = room.track[uid]
        ax.step([p[0] for p in tr], [trek.distance(ref, p[1]) for p in tr], where="post", color=col, lw=1.8, label=name)
    sep = next(e for e in room.events if e.kind == "SEPARATION")
    sos = next(e for e in room.events if e.kind == "SOS")
    ax.axvline(w["split_s"], color=MUTED, lw=0.8, ls=(0, (4, 3)))
    ax.text(w["split_s"] - 6, 80, "they take different\nbranches at the junction", ha="right", fontsize=7.6, color=MUTED)
    ax.axvline(sep.time, color=INK, lw=0.9)
    ax.text(sep.time + 6, 330, f"separation flagged:\n{sep.detail.split(';')[0]}", fontsize=7.6)
    ax.plot([sos.time], [trek.distance(ref, sos.pole)], "*", ms=13, color=OCHRE, mec=INK, mew=0.7, zorder=6)
    ax.annotate(f"SOS pressed; alarm {sos.time - w['sos_s']:.1f} s later", (sos.time, trek.distance(ref, sos.pole)),
                xytext=(10, -16), textcoords="offset points", fontsize=7.6)
    ax.set_xlabel("Time (s)"), ax.set_ylabel("Track distance from the first pole (m)")
    ax.set_title("One simulated family: what the control room sees (after the junction each line is on its own branch)")
    ax.legend(loc="upper left", fontsize=8), ax.set_xlim(0, 1110)
    save(fig, "walk")


def main():
    os.makedirs(FIG, exist_ok=True), os.makedirs(IMG, exist_ok=True)
    with open(os.path.join(RES, "summary.json")) as fh:
        S = json.load(fh)
    fig_capacity(), fig_link(), fig_power(S), fig_tether_ev(), fig_bloom(), fig_trek(), fig_walk()
    print("wrote 7 figures to generated/fig and docs/img")


if __name__ == "__main__":
    main()
