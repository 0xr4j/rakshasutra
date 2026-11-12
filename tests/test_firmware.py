"""The C core in firmware/ must produce the same bytes as the Python reference."""
import os
import random
import shutil
import subprocess

import pytest

from rakshasutra import lora
from rakshasutra import protocol as pr
from rakshasutra.cmac import aes_cmac
from rakshasutra.edge import PoleEdgeFilter

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


@pytest.fixture(scope="module")
def host(tmp_path_factory):
    cc = shutil.which("gcc") or shutil.which("cc") or shutil.which("clang")
    if cc is None:
        pytest.skip("no C compiler")
    fw = os.path.join(ROOT, "firmware")
    exe = str(tmp_path_factory.mktemp("fw") / "host_test")
    subprocess.check_call([cc, "-O2", "-std=c99", "-Wall", "-Wextra", "-Werror", "-pedantic",
                           "-I", os.path.join(fw, "rakshasutra_pole"), os.path.join(fw, "host_test.c"),
                           os.path.join(fw, "rakshasutra_pole", "rs_core.c"), "-lm", "-o", exe])

    def run(lines):
        out = subprocess.run([exe], input="\n".join(lines) + "\n", capture_output=True, text=True, check=True)
        return out.stdout.strip().splitlines()
    return run


def test_cmac_matches(host):
    rng = random.Random(0)
    cases = [(rng.randbytes(16), rng.randbytes(n)) for n in (0, 1, 3, 9, 15, 16, 17, 31, 32, 33, 48, 100)]
    out = host([f"M {k.hex()} {m.hex() or '-'}" for k, m in cases])
    assert out == [aes_cmac(k, m).hex() for k, m in cases]


def test_frames_addresses_and_wake_tokens_match(host):
    rng = random.Random(1)
    cases = [(rng.randbytes(16), rng.randrange(65536), rng.randrange(16), rng.randrange(120, 160), rng.randrange(2))
             for _ in range(200)]
    out = host([f"F {k.hex()} {c} {f} {b} {r}" for k, c, f, b, r in cases])
    for (k, c, f, b, r), line in zip(cases, out):
        frame = pr.build_frame(k, c, flags=f, battery_volts=b * 0.02, role=r)
        assert line == f"{frame.hex()} {pr.mac_address(k, c).hex()} {pr.wake_token(k, c, pr.CMD_FIND).hex()}"


def test_verification_matches(host):
    rng = random.Random(2)
    lines, expected = [], []
    for _ in range(100):
        k = rng.randbytes(16)
        frame = bytearray(pr.build_frame(k, rng.randrange(65536)))
        if rng.random() < 0.5:
            frame[rng.randrange(15)] ^= 1 << rng.randrange(8)
        lines.append(f"V {k.hex()} {frame.hex()}")
        expected.append(str(int(pr.verify_frame(k, bytes(frame)))))
    assert host(lines) == expected


def test_time_on_air_matches(host):
    cases = [(b, sf) for sf in (7, 8, 9, 10) for b in (0, 1, 15, 16, 64, 100, 200, 222)]
    out = host([f"T {b} {sf}" for b, sf in cases])
    assert [float(x) for x in out] == [round(lora.time_on_air(b, sf=sf) * 1000, 3) for b, sf in cases]


@pytest.mark.parametrize("hits,gate,seed", [(1, -75.0, 0), (3, -65.0, 1), (1, -75.0, 2)])
def test_edge_filter_matches_over_a_busy_ten_minutes(host, hits, gate, seed):
    """Sixty wearables come and go past one pole; every uplink must be identical."""
    rng = random.Random(seed)
    keys = [rng.randbytes(16) for _ in range(60)]
    events = []
    for i, k in enumerate(keys):
        t, leave = rng.uniform(0, 400), 0.0
        leave = t + rng.uniform(5, 200)
        sos_from = rng.uniform(t, leave) if i % 9 == 0 else None
        while t < leave:
            sos = sos_from is not None and sos_from <= t < sos_from + 10
            frame = pr.build_frame(k, 40 + int(t // 300), flags=pr.F_SOS if sos else 0)
            events.append((t, "A", round(rng.uniform(-95, -45), 2), frame))
            t += 0.2 if sos else 0.8 + rng.uniform(0, 0.01)
    events += [(t, "X", None, None) for t in range(15, 615, 15)] + [(t + 0.5, "H", None, None)
                                                                     for t in range(60, 660, 60)]
    events.sort(key=lambda e: (e[0], e[1]))
    py, lines, expected = PoleEdgeFilter(hits, gate), [f"I {hits} {gate}"], []
    for t, kind, rssi, frame in events:
        if kind == "A":
            lines.append(f"A {t!r} {rssi!r} {frame.hex()}")
            ups = [py.on_advertisement(frame, rssi, t)]
        elif kind == "X":
            lines.append(f"X {t!r}")
            ups = py.flush(float(t))
        else:
            lines.append("H")
            ups = [py.heartbeat()]
        expected += [f"U {u.fport} {int(u.confirmed)} {u.payload.hex()}" for u in ups if u is not None]
    out = host(lines)
    assert len(expected) > 40
    assert out == expected
