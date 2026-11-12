"""Write data/params.csv, data/zones.csv and data/poles.csv from the package."""
import csv
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "src"))
from rakshasutra.params import TABLE  # noqa: E402
from rakshasutra.trek import Trek  # noqa: E402


def main():
    data = os.path.join(ROOT, "data")
    with open(os.path.join(data, "params.csv"), "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["key", "value", "unit", "status", "source"])
        for row in TABLE:
            w.writerow(row)
    trek = Trek()
    with open(os.path.join(data, "zones.csv"), "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["zone", "segments", "length_km", "poles", "mean_spacing_m", "backhaul", "hits_required"])
        for z in trek.zone_summary():
            w.writerow([z["zone"], "+".join(z["segments"]), z["km"], z["poles"], round(z["spacing_m"], 1),
                        "fibre LAN" if z["fiber"] else "LoRaWAN", 3 if z["fiber"] else 1])
    with open(os.path.join(data, "poles.csv"), "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["pole", "segment", "zone", "along_m", "altitude_m", "backhaul", "neighbours"])
        for p in trek.poles:
            w.writerow([p.pid, p.segment, p.zone, round(p.along_m, 1), round(p.altitude_m, 1),
                        "fibre" if p.fiber else "lora", " ".join(str(n) for n in sorted(trek.edges[p.pid]))])
    print("wrote data/params.csv, data/zones.csv, data/poles.csv")


if __name__ == "__main__":
    main()
