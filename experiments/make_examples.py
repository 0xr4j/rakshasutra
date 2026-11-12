"""Write the example logs in examples/: one family walk and one attack log."""
import csv
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "src"))
from rakshasutra import simulate  # noqa: E402
from rakshasutra.edge import FPORT_ARRIVALS, FPORT_SOS  # noqa: E402
from rakshasutra.protocol import F_SOS, build_frame, rolling_id  # noqa: E402

EX = os.path.join(ROOT, "examples")


def write_log(name, rows):
    with open(os.path.join(EX, name), "w", newline="") as fh:
        w = csv.DictWriter(fh, ["time_s", "pole", "fport", "payload"], lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def main():
    os.makedirs(EX, exist_ok=True)
    walk = simulate.family_walk()
    write_log("adhkuwari_separation.csv", walk["log"])
    reg = walk["registry"]
    with open(os.path.join(EX, "registry.json"), "w") as fh:
        json.dump({"note": "Demonstration keys derived from a public test master key. Never use them on a real device.",
                   "tags": [dict(uid=t.uid, key=t.key.hex(), c_init=t.c_init, t_pair=t.t_pair, family=t.family,
                                 role=t.role) for t in reg.tags.values()]}, fh, indent=1)
        fh.write("\n")

    # An attack log against the same family: what the server must drop.
    key = walk["keys"]["band-0421"]
    c0 = reg.tags["band-0421"].c_init

    def tup(counter, rssi=60, flags=0, k=key):
        return (rolling_id(k, counter) + counter.to_bytes(2, "little") + bytes([rssi, flags])).hex()

    forged = bytearray(build_frame(key, c0))
    forged[9] |= F_SOS                                       # SOS bit set by someone without the key
    random_mic = bytearray(build_frame(key, c0, flags=F_SOS))
    random_mic[11:15] = b"\x00\x11\x22\x33"
    rows = [
        dict(time_s=10.0, pole=130, fport=FPORT_ARRIVALS, payload=tup(c0)),                       # genuine sighting
        dict(time_s=20.0, pole=131, fport=FPORT_SOS, payload=bytes(forged).hex() + "37"),         # flipped SOS bit
        dict(time_s=21.0, pole=131, fport=FPORT_SOS, payload=bytes(random_mic).hex() + "37"),     # guessed MIC
        dict(time_s=30.0, pole=200, fport=FPORT_ARRIVALS, payload="deadbeef" + tup(c0)[8:]),      # unknown pseudonym
        dict(time_s=40.0, pole=131, fport=FPORT_SOS,
             payload=build_frame(key, c0, flags=F_SOS).hex() + "37"),                             # genuine SOS
        dict(time_s=70.0, pole=250, fport=FPORT_ARRIVALS, payload=tup(c0)),                       # replay, same slot,
        #   at a pole kilometres away: ACCEPTED. Arrival tuples are unsigned. This is a known limit.
        dict(time_s=3700.0, pole=250, fport=FPORT_ARRIVALS, payload=tup(c0)),                     # replay an hour later
        dict(time_s=3710.0, pole=250, fport=FPORT_SOS,
             payload=build_frame(key, c0, flags=F_SOS).hex() + "37"),                             # replayed SOS
    ]
    write_log("attack_log.csv", rows)
    print("wrote examples/adhkuwari_separation.csv (%d uplinks), registry.json, attack_log.csv" % len(walk["log"]))


if __name__ == "__main__":
    main()
