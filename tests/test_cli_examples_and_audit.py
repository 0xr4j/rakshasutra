"""The command line, the shipped examples, the parameter table and the audit."""
import csv
import json
import os

import pytest

from rakshasutra import audit, cli
from rakshasutra.params import TABLE, P, STATUS

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
EX = os.path.join(ROOT, "examples")


def run(capsys, *argv):
    code = cli.main(list(argv))
    return code, capsys.readouterr().out


def test_frame_and_verify_round_trip(capsys):
    key = "000102030405060708090a0b0c0d0e0f"
    code, out = run(capsys, "frame", "--key", key, "--counter", "17", "--sos", "--json")
    frame = json.loads(out)["frame"]
    assert code == 0 and frame == "5aff0411003c34fdc901968c83e42f"
    assert run(capsys, "verify", frame, "--key", key)[0] == 0
    assert run(capsys, "verify", frame[:-2] + "00", "--key", key)[0] == 1


def test_airtime_command(capsys):
    _, out = run(capsys, "airtime")
    assert "66.82 ms" in out and "138.50 ms" in out and "338.18 ms" in out


@pytest.mark.parametrize("command", ["capacity", "link", "battery", "bloom", "audit"])
def test_report_commands_run(capsys, command):
    code, out = run(capsys, command)
    assert code == 0 and len(out.splitlines()) >= 4


def test_trace_of_the_family_walk(capsys):
    code, out = run(capsys, "trace", os.path.join(EX, "adhkuwari_separation.csv"), "--registry",
                    os.path.join(EX, "registry.json"), "--json")
    kinds = [e["kind"] for e in json.loads(out)]
    assert code == 0 and "SEPARATION" in kinds and kinds.count("SOS") == 1
    assert "DROPPED" not in kinds and "FORGED_SOS" not in kinds


def test_trace_of_the_attack_log(capsys):
    _, out = run(capsys, "trace", os.path.join(EX, "attack_log.csv"), "--registry",
                 os.path.join(EX, "registry.json"), "--json")
    ev = json.loads(out)
    assert [e["kind"] for e in ev] == ["ARRIVED", "FORGED_SOS", "FORGED_SOS", "DROPPED", "SOS", "ARRIVED",
                                       "SUSPECT", "DROPPED", "DROPPED"]
    # the sixth event is the known limit: an unsigned sighting replayed inside its slot window is believed,
    # and only flagged because nobody could have covered five kilometres in thirty seconds
    assert ev[5]["pole"] == 250 and ev[6]["kind"] == "SUSPECT"


def test_examples_are_what_the_generator_writes():
    from rakshasutra import simulate
    with open(os.path.join(EX, "adhkuwari_separation.csv"), newline="") as fh:
        saved = list(csv.DictReader(fh))
    fresh = simulate.family_walk()["log"]
    assert len(saved) == len(fresh)
    assert all(s["payload"] == f["payload"] and int(s["pole"]) == f["pole"] for s, f in zip(saved, fresh))


def test_params_csv_is_in_step_with_the_package():
    with open(os.path.join(ROOT, "data", "params.csv"), newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert [r["key"] for r in rows] == [t[0] for t in TABLE]
    assert all(r["value"] == str(t[1]) and r["status"] == t[3] for r, t in zip(rows, TABLE))


def test_every_parameter_has_a_status_and_a_source():
    assert len(P) == len(TABLE)                                  # no duplicate keys
    assert set(STATUS.values()) <= {"PAPER", "STANDARD", "DATASHEET", "DEFINED", "ASSUMED"}
    assert all(len(t[4]) > 8 for t in TABLE)


def test_audit_verdicts():
    items = audit.entries()
    by = {e["claim"]: e for e in items}
    assert by["Time on air, SOS frame (15 B, SF7)"]["verdict"] == "reproduced"
    assert by["Maximum allowable LoRa path loss, whip above the roof"]["verdict"] == "reproduced"
    assert by["Mean current on the trek (Table V)"]["verdict"] == "reproduced"
    assert by["Uplink loss, Rakshasutra, 3,000 tags in the cell"]["verdict"] == "differs"
    assert by["Supply during the pulse with the 100 uF capacitor"]["verdict"] == "design fix"
    assert len({e["id"] for e in items}) == len(items)
    s = audit.summary(items)
    assert sum(s.values()) == len(items) and s["reproduced"] >= 15


def test_saved_results_match_a_fresh_calculation():
    """Every analytical number in results/summary.json is what the code gives today."""
    from rakshasutra import capacity, power
    with open(os.path.join(ROOT, "results", "summary.json")) as fh:
        s = json.load(fh)
    for arch, rows in s["capacity"].items():
        for row in rows:
            c = capacity.cell_load("rakshasutra", row["tags"], departures=False) if arch.endswith("nodep") \
                else capacity.cell_load(arch, row["tags"])
            assert round(c.loss, 4) == row["loss"] and round(c.load, 4) == row["load"]
    assert s["power"]["active_ua"] == round(power.active_current_ua(), 2)
    with open(os.path.join(ROOT, "results", "audit.json")) as fh:
        saved = json.load(fh)
    fresh = audit.entries(s)
    assert [(e["id"], e["verdict"], str(e["model"])) for e in saved] == \
           [(e["id"], e["verdict"], str(e["model"])) for e in fresh]


def test_readme_python_examples_run_and_print_what_they_say(capsys):
    import re
    with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as fh:
        text = fh.read()
    blocks = re.findall(r"```python\n(.*?)```", text, re.S)
    assert len(blocks) == 2
    for block in blocks:
        exec(block, {})
    out = capsys.readouterr().out
    for said in re.findall(r"#\s+(Result\(.*\)|[\d.]+ [\d.]+|[\d.]+ ms|True)\s*$", "\n".join(blocks), re.M):
        assert said in out, said


def test_readme_and_site_have_no_unfilled_placeholders():
    for name in ("README.md", "AUDIT.md", "docs/index.html", "docs/explorer.html", "docs/audit.html"):
        with open(os.path.join(ROOT, name), encoding="utf-8") as fh:
            assert "{{" not in fh.read(), name


def test_every_local_link_in_the_readme_exists():
    import re
    for name in ("README.md", "ROADMAP.md", "CONTRIBUTING.md", "SECURITY.md", "firmware/README.md", "data/README.md"):
        with open(os.path.join(ROOT, name), encoding="utf-8") as fh:
            text = fh.read()
        base = os.path.dirname(os.path.join(ROOT, name))
        for target in re.findall(r"\]\(([^)#]+)(?:#[^)]*)?\)", text) + re.findall(r'(?:src|srcset|href)="([^"#]+)"', text):
            if target.startswith(("http", "mailto")):
                continue
            assert os.path.exists(os.path.join(base, target)), f"{name}: {target}"
