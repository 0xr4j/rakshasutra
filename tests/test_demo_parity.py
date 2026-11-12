"""The browser explorer's JavaScript kernel must agree with the Python reference."""
import json
import os
import shutil
import subprocess

import pytest

from rakshasutra import bloom, capacity, linkbudget, lora, power
from rakshasutra import protocol as pr
from rakshasutra.cmac import aes_cmac

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SCRIPT = """
const RS = require(process.argv[2]);
const out = {};
const key = RS.unhex("000102030405060708090a0b0c0d0e0f");
out.cmac = [0, 1, 15, 16, 17, 40, 64].map(n => RS.hex(RS.aesCmac(key, Array.from({length: n}, (_, i) => (i * 7 + 3) & 255))));
out.frames = [[0, 0, 150, 0], [17, 1, 150, 0], [65535, 9, 141, 1], [4660, 0, 120, 0]].map(a => RS.hex(RS.buildFrame(key, ...a)));
out.mac = RS.hex(RS.macAddress(key, 17));
out.toa = [[15, 7], [64, 7], [200, 7], [15, 9], [222, 8]].map(a => RS.timeOnAir(...a));
out.cells = [];
for (const arch of ["raw", "single", "batch", "rakshasutra"]) for (const n of [100, 500, 1700, 3000])
  out.cells.push(RS.cellLoad(arch, n).load);
out.nodep = [500, 3000].map(n => RS.cellLoad("rakshasutra", n, 60, false).load);
out.small = RS.cellLoad("rakshasutra", 637, 32).loss;
out.bloom = [0, 50, 100, 300].map(RS.bloomFpr);
out.adv = [RS.advEventMs("1m"), RS.advEventMs("coded")];
out.life = [["table", false], ["table", true], ["coded", false], ["coded", true]].map(a => RS.batteryMonths(...a).months);
out.range = [RS.bleRange(-96, 4, 24.1, 14), RS.bleRange(-96, 8, 0, 14), RS.bleRange(-103, 8, 0, 14)];
out.droop = [0, 100, 470, 1000].map(c => RS.pulseVmin(c, 32, 100, 400));
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def js(tmp_path_factory):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    script = tmp_path_factory.mktemp("js") / "run.js"
    script.write_text(SCRIPT)
    out = subprocess.run([node, str(script), os.path.join(ROOT, "demo", "kernel.js")], capture_output=True,
                         text=True, check=True).stdout
    return json.loads(out)


KEY = bytes(range(16))


def test_cmac_and_frames(js):
    assert js["cmac"] == [aes_cmac(KEY, bytes((i * 7 + 3) & 255 for i in range(n))).hex()
                          for n in (0, 1, 15, 16, 17, 40, 64)]
    cases = [(0, 0, 150, 0), (17, 1, 150, 0), (65535, 9, 141, 1), (4660, 0, 120, 0)]
    assert js["frames"] == [pr.build_frame(KEY, c, flags=f, battery_volts=b * 0.02, role=r).hex()
                            for c, f, b, r in cases]
    assert js["mac"] == pr.mac_address(KEY, 17).hex()


def test_airtime_and_capacity(js):
    assert js["toa"] == pytest.approx([lora.time_on_air(b, sf=sf) for b, sf in
                                       ((15, 7), (64, 7), (200, 7), (15, 9), (222, 8))], rel=1e-12)
    expected = [capacity.cell_load(a, n).load for a in ("raw", "single", "batch", "rakshasutra")
                for n in (100, 500, 1700, 3000)]
    assert js["cells"] == pytest.approx(expected, rel=1e-9)
    assert js["nodep"] == pytest.approx([capacity.cell_load("rakshasutra", n, departures=False).load
                                         for n in (500, 3000)], rel=1e-9)
    assert js["small"] == pytest.approx(capacity.cell_load("rakshasutra", 637, poles=32).loss, rel=1e-9)


def test_bloom_power_and_link(js):
    assert js["bloom"] == pytest.approx([bloom.false_positive_rate(n) for n in (0, 50, 100, 300)], rel=1e-12)
    assert js["adv"] == pytest.approx([power.adv_event_ms("1m"), power.adv_event_ms("coded")])
    coded = power.adv_event_ms("coded")
    assert js["life"] == pytest.approx([power.battery_life_months(), power.battery_life_months(cold=True),
                                        power.battery_life_months(tx_ms=coded),
                                        power.battery_life_months(cold=True, tx_ms=coded)], rel=1e-9)
    assert js["range"] == pytest.approx([r["range_m"] for r in linkbudget.table()[:3]], rel=1e-9)
    assert js["droop"] == pytest.approx([power.pulse_droop(capacitor_uf=c)["v_min"] for c in (0, 100, 470, 1000)],
                                        rel=1e-9)
