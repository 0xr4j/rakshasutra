"""Write generated/numbers.tex, generated/tables.tex and AUDIT.md from the saved results.
No number in the book, the white paper, the README or the website is typed by hand."""
import csv
import json
import os
import subprocess
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "src"))
from rakshasutra.params import TABLE  # noqa: E402

with open(os.path.join(ROOT, "results", "summary.json")) as fh:
    S = json.load(fh)
with open(os.path.join(ROOT, "results", "audit.json")) as fh:
    AUDIT = json.load(fh)


def tex(s):
    s = str(s)
    for a, b in (("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("_", r"\_"), ("#", r"\#"), ("<", r"$<$"),
                 (">", r"$>$"), ("|", r"\textbar{}")):
        s = s.replace(a, b)
    return s.replace(" uA", r" \textmu A").replace(" uF", r" \textmu F").replace("-5 C", r"$-5$\,\textdegree C") \
        .replace("25 C", r"25\,\textdegree C").replace(" ohm", r" $\Omega$")


def count_tests():
    out = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", os.path.join(ROOT, "tests")],
                         capture_output=True, text=True).stdout
    return int(out.strip().splitlines()[-1].split()[0])


def numbers():
    cap = {a: {r["tags"]: r for r in rows} for a, rows in S["capacity"].items()}
    L, P_, T, E, O, B, W = S["link"], S["power"], S["tether"], S["ev"], S["sos"], S["bloom"], S["walk"]
    pct = lambda x, n=1: f"{100 * x:.{n}f}"   # noqa: E731
    n = {
        "ToaSos": S["airtime_ms"]["15"], "ToaBloom": f'{S["airtime_ms"]["64"]:.2f}', "ToaChunk": S["airtime_ms"]["200"],
        "ToaSosNine": f'{S["airtime_sos_sf9_ms"]:.1f}',
        "LossSingle": pct(cap["single"][3000]["loss"]), "LossBatch": pct(cap["batch"][3000]["loss"]),
        "LossRak": pct(cap["rakshasutra"][3000]["loss"]), "LossRakNd": pct(cap["rakshasutra-nodep"][3000]["loss"]),
        "LoadSingle": pct(cap["single"][3000]["load"]), "LoadBatch": pct(cap["batch"][3000]["load"]),
        "LoadRak": pct(cap["rakshasutra"][3000]["load"]), "LoadRakNd": pct(cap["rakshasutra-nodep"][3000]["load"]),
        "LossRakLow": pct(cap["rakshasutra"][500]["loss"]), "LossRakNdLow": pct(cap["rakshasutra-nodep"][500]["loss"]),
        "LossBatchLow": pct(cap["batch"][500]["loss"]), "OversizeBatch": pct(cap["batch"][3000]["oversize"], 0),
        "LossChunk": pct(cap["rakshasutra"][3000]["streams"]["arrival chunk"]["loss"], 0),
        "AirRed": pct(S["airtime_reduction_vs_single"]), "AirRedNd": pct(S["airtime_reduction_vs_single_nodep"]),
        "AirVsBatch": pct(S["airtime_change_vs_batch"], 0), "AirVsBatchNd": pct(-S["airtime_change_vs_batch_nodep"], 0),
        "BloomPays": f'{S["bloom_pays_from_tags"]:,}'.replace(",", "{,}"),
        "DepTags": S["deployed"]["tags"], "DepPoles": S["deployed"]["poles"], "DepLoss": pct(S["deployed"]["loss"]),
        "DepLossNd": pct(S["deployed"]["loss_nodep"]),
        "McFrames": f'{S["montecarlo"]["frames"]:,}'.replace(",", "{,}"), "McErr": pct(S["montecarlo"]["max_abs_loss_error"]),
        "RangeAbove": f'{L["rows"][0]["range_m"]:.1f}', "RangeOneM": f'{L["rows"][1]["range_m"]:.0f}',
        "RangeCoded": f'{L["rows"][2]["range_m"]:.0f}', "MarginFifty": L["margin_50m_db"], "Mapl": L["mapl_db"],
        "MaplUnder": L["rows"][3]["mapl_db"], "MarginEightOver": f'{L["rows"][4]["margin_8km_db"]:.1f}',
        "MarginEightUnder": f'{-L["rows"][3]["margin_8km_db"]:.1f}', "MarginFourUnder": f'{L["rows"][3]["margin_4km_db"]:.1f}',
        "MarginFourOver": f'{L["rows"][4]["margin_4km_db"]:.1f}',
        "GateTrackM": f'{L["core_zone_gate_m"]:.0f}', "GateHubM": f'{L["hub_gate_m"]:.1f}',
        "Iactive": P_["active_ua"], "LifeWarm": P_["life_warm"], "LifeCold": P_["life_cold"],
        "AdvCoded": f'{P_["adv_ms_coded"]:.2f}', "AdvOneM": f'{P_["adv_ms_1m"]:.2f}', "IactiveCoded": P_["active_ua_coded"],
        "LifeWarmCoded": P_["life_warm_coded"], "LifeColdCoded": f'{P_["life_cold_coded"]:.1f}',
        "DroopUnbuf": P_["droop_unbuffered"], "DroopCap": P_["droop_100uf"], "CapNeed": f'{P_["capacitor_needed_uf"]:.0f}',
        "PulseMax": P_["max_pulse_ma"], "TauMs": P_["tau_ms"],
        "TetherHit": pct(T["hit_5ms"], 2), "TetherAlarm": pct(T["miss4_5ms"], 0),
        "TetherAlarmSim": pct(T["time_in_false_alarm_5ms"], 0), "TetherWindow": f'{T["window_needed_ms"]:.0f}',
        "TetherUa": f'{T["scan_ua_needed"]:.0f}', "ParentLife": T["parent_life_months"], "TetherRange": f'{T["range_m"]:.0f}',
        "TetherGate": f'{-T["rssi_gate_30m"]:.0f}',
        "EvCap": pct(E["capture_150"]), "EvCapDense": pct(E["capture_300"]), "SlowTwo": pct(E["slow2_h3"], 0),
        "SlowFiveOne": pct(E["slow5_h1"], 0), "ClassAWalk": f'{E["class_a_walk_m"]:.0f}',
        "SosMedian": f'{O["median_s"]:.1f}', "SosFour": pct(O["within_4s"], 0), "SosFirstLoss": pct(O["first_try_loss"], 0),
        "SosPninefive": f'{O["p95_s"]:.1f}', "SosFiberP": f'{S["sos_fiber"]["p95_s"]:.1f}',
        "SosFourLow": pct(S["sos_500"]["within_4s"], 0),
        "BloomFifty": pct(B["fpr_50"]), "BloomHundred": pct(B["fpr_100"]), "BloomThree": pct(B["fpr_300"], 0),
        "BloomCapFive": B["cap_5pct"], "BloomCapOne": B["cap_1pct"], "Clash": pct(S["pseudonym_clash_10000"], 0),
        "WalkSepDelay": f'{W["separation_delay_s"]:.0f}', "WalkSepM": W["separation_detail"].split()[0],
        "WalkSosDelay": f'{W["sos_delay_s"]:.1f}', "WalkUplinks": W["uplinks"],
        "BranchExample": f'{S["trek"]["branch_example_m"] / 1000:.1f}',
        "AuditRep": S["audit_summary"]["reproduced"], "AuditDiff": S["audit_summary"]["differs"],
        "AuditFix": S["audit_summary"]["design fix"], "AuditOpen": S["audit_summary"]["open"], "AuditTotal": len(AUDIT),
        "Ntests": count_tests(), "Nparams": len(TABLE), "Nassumed": sum(1 for t in TABLE if t[3] == "ASSUMED"),
        "Ndefined": sum(1 for t in TABLE if t[3] == "DEFINED"),
        "Npaper": sum(1 for t in TABLE if t[3] == "PAPER"), "Nstandard": sum(1 for t in TABLE if t[3] == "STANDARD"),
        "LossSingleLow": pct(cap["single"][500]["loss"]),
        "LoadRakNdFrac": f'{cap["rakshasutra-nodep"][3000]["load"]:.3f}',
        "LossRakNdFrac": f'{cap["rakshasutra-nodep"][3000]["loss"]:.3f}',
    }
    with open(os.path.join(ROOT, "generated", "numbers.tex"), "w") as fh:
        fh.write("% Written by generated/make_numbers.py from results/summary.json. Do not edit.\n")
        for k, v in n.items():
            fh.write(f"\\newcommand{{\\{k}}}{{{v}}}\n")
    with open(os.path.join(ROOT, "generated", "numbers.json"), "w") as fh:
        json.dump({k: str(v).replace("{,}", ",") for k, v in n.items()}, fh, indent=1)
    return n


def tables():
    out = ["% Written by generated/make_numbers.py. Do not edit."]
    cap = S["capacity"]
    paper = {"raw": "97.7 / 99.9 / 100 / 100", "single": "12.2 / 22.9 / 40.5 / 54.2", "batch": "5.8 / 11.3 / 16.8 / 22.1",
             "rakshasutra": "4.1 / 8.1 / 12.0 / 15.8", "rakshasutra-nodep": "--"}
    names = {"raw": "Raw forwarding (2 s pings)", "single": "Single-event arrivals + raw ID heartbeat",
             "batch": "15 s batching + raw ID heartbeat", "rakshasutra": "Rakshasutra as specified",
             "rakshasutra-nodep": "Rakshasutra without departure lists"}
    body = []
    for a in names:
        cells = " & ".join(f"{100 * r['load']:.1f} / {100 * r['loss']:.1f}" for r in cap[a])
        big = "over 222 B" if cap[a][3]["oversize"] > 0.01 else ("7 B" if a == "raw" else r"$\leq$ 200 B")
        body.append(f"{names[a]} & {cells} & {big} \\\\")
    out.append("\\newcommand{\\TableCapacity}{\\begin{tabular}{@{}p{0.25\\linewidth}rrrrl@{}}\\toprule\n"
               "Forwarding design & 500 & 1,000 & 2,000 & 3,000 & Largest frame\\\\\\midrule\n" + "\n".join(body) +
               "\n\\bottomrule\\end{tabular}}")
    body = [f"{names[a]} & {paper[a]} & " + " / ".join(f"{100 * r['loss']:.1f}" for r in cap[a]) + " \\\\" for a in names]
    out.append("\\newcommand{\\TableCapacityCompare}{\\begin{tabular}{@{}p{0.36\\linewidth}ll@{}}\\toprule\n"
               "Forwarding design & First draft, loss (\\%) & This model, loss (\\%)\\\\\\midrule\n" + "\n".join(body) +
               "\n\\bottomrule\\end{tabular}}")
    rows = S["link"]["rows"]
    body = [f"{tex(r['link'])} & {tex(r['phy'])} & {r['tx_dbm']:+.0f} & {r['roof_db']:.1f} & {r['sens_dbm']:.1f} & "
            + (f"{r['range_m']:.1f} m" if "range_m" in r else f"{r['margin_8km_db']:+.1f} dB") + " \\\\"
            for r in rows]
    out.append("\\newcommand{\\TableLink}{\\begin{tabular}{@{}p{0.30\\linewidth}lrrrl@{}}\\toprule\n"
               "Link & PHY & $P_{tx}$ & Roof & $S_{rx}$ & Range or margin\\\\\\midrule\n"
               + "\n".join(body) + "\n\\bottomrule\\end{tabular}}")
    body = []
    for r in S["power"]["table"]:
        body.append(f"{tex(r['state'])} & " + ("continuous" if r["period_ms"] is None else f"every {r['period_ms'] / 1000:g} s")
                    + f" & {r['peak_ma']:g} & " + ("--" if r["on_ms"] is None else f"{r['on_ms']:g}")
                    + f" & {r['mean_ua']:.2f} \\\\")
    out.append("\\newcommand{\\TablePower}{\\begin{tabular}{@{}p{0.27\\linewidth}lrrr@{}}\\toprule\n"
               "State & Interval & Peak, mA & On, ms & Mean, \\textmu A\\\\\\midrule\n" + "\n".join(body) +
               f"\n\\midrule Total on the trek &&&& {S['power']['active_ua']:.2f} \\\\\n\\bottomrule\\end{{tabular}}}}")
    body = [f"{z['zone']} & {tex(' + '.join(z['segments']))} & {z['km']:.1f} & {z['poles']} & {z['spacing_m']:.0f} & "
            f"{'fibre LAN' if z['fiber'] else 'LoRaWAN'} \\\\" for z in S["trek"]["zones"]]
    out.append("\\newcommand{\\TableZones}{\\begin{tabular}{@{}llrrrl@{}}\\toprule\n"
               "Zone & Segments & km & Poles & Spacing (m) & Backhaul\\\\\\midrule\n" + "\n".join(body) +
               "\n\\midrule & Total & 22.5 & 255 & & \\\\\\bottomrule\\end{tabular}}")
    body = [f"{e['id']} & {tex(e['claim'])} & {tex(e['paper'])} & {tex(e['model'])} {tex(e['unit'])} & {e['verdict']} \\\\"
            for e in AUDIT]
    out.append("\\newcommand{\\TableAudit}{\\begin{longtable}{@{}lp{0.40\\linewidth}p{0.13\\linewidth}p{0.21\\linewidth}l@{}}\\toprule\n"
               "& Claim & First draft & This model & Verdict\\\\\\midrule\\endhead\n" + "\n".join(body) +
               "\n\\bottomrule\\end{longtable}}")
    body = [f"\\texttt{{{tex(k)}}} & \\raggedright {tex(v)} {tex(u)} & {st.lower()} & {tex(src)} \\\\" for k, v, u, st, src in TABLE]
    out.append("\\newcommand{\\TableParams}{\\begin{longtable}{@{}p{0.25\\linewidth}p{0.14\\linewidth}lp{0.31\\linewidth}@{}}\\toprule\n"
               "Parameter & Value & Status & Source or note\\\\\\midrule\\endhead\n" + "\n".join(body) +
               "\n\\bottomrule\\end{longtable}}")
    with open(os.path.join(ROOT, "generated", "tables.tex"), "w") as fh:
        fh.write("\n".join(out) + "\n")


def audit_md(n):
    mark = {"reproduced": "✅ reproduced", "differs": "✏️ differs", "design fix": "🔧 design fix", "open": "❓ open"}
    lines = [
        "# Reproduction audit", "",
        "Every checkable number in the first draft of White Paper WP-01 (October 2026), recomputed by the code in this",
        "repository from the paper's own equations and parameters. The revised paper and the book use the model's",
        "numbers. This file is written by `generated/make_numbers.py` from `results/audit.json`; run",
        "`rakshasutra audit --results results/summary.json` to print it.", "",
        f"**{n['AuditTotal']} claims: {n['AuditRep']} reproduced, {n['AuditDiff']} differ, {n['AuditFix']} need a design "
        f"fix, {n['AuditOpen']} are open.** Nothing here has been measured; every value is calculated or simulated.", "",
        "| | Section | Claim | First draft | This model | Verdict |", "|---|---|---|---|---|---|"]
    for e in AUDIT:
        lines.append(f"| {e['id']} | {e['section']} | {e['claim']} | {e['paper']} | {e['model']} {e['unit']} | "
                     f"{mark[e['verdict']]} |")
    lines += ["", "## Notes", ""]
    lines += [f"- **{e['id']}** {e['note']}" for e in AUDIT if e["note"]]
    lines += ["", "## What the verdicts mean", "",
              "- **reproduced**: the model gives the first draft's number.",
              "- **differs**: the model gives a different number; the revised paper uses the model's.",
              "- **design fix**: the mechanism does not work as first specified; the note says what does.",
              "- **open**: cannot be settled by calculation; it needs a datasheet check or a measurement.", ""]
    with open(os.path.join(ROOT, "AUDIT.md"), "w") as fh:
        fh.write("\n".join(lines))


def readme(n):
    """README.md from generated/README.tmpl.md: {{Key}} is a number, {{cmd:...}} the output of a command."""
    import re
    import shlex
    with open(os.path.join(ROOT, "generated", "README.tmpl.md"), encoding="utf-8") as fh:
        text = fh.read()

    def run(m):
        args = shlex.split(m.group(1))
        assert args[0] == "rakshasutra"
        out = subprocess.run([sys.executable, "-m", "rakshasutra"] + args[1:], capture_output=True, text=True, cwd=ROOT,
                             env=dict(os.environ, PYTHONPATH=os.path.join(ROOT, "src")))
        return out.stdout.rstrip()
    text = re.sub(r"\{\{cmd:(.+?)\}\}", run, text)
    text = re.sub(r"\{\{(\w+)\}\}", lambda m: str(n[m.group(1)]).replace("{,}", ","), text)
    with open(os.path.join(ROOT, "README.md"), "w", encoding="utf-8") as fh:
        fh.write(text)


if __name__ == "__main__":
    n = numbers()
    tables()
    audit_md(n)
    readme(n)
    print(f"wrote generated/numbers.tex ({len(n)} numbers), generated/tables.tex, generated/numbers.json, AUDIT.md")
