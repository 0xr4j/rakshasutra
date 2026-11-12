<p align="center"><picture><source media="(prefers-reduced-motion: reduce)" srcset="docs/banner.png"><img src="docs/img/hero.svg" alt="Rakshasutra: a thread through the crowd. A parent and a child walk a branching mountain route and take different tracks at a junction." width="100%"></picture></p>

<h1 align="center">Rakshasutra</h1>

<p align="center"><b>An open design for finding separated children and elders on a mountain pilgrimage route, without phones or cellular coverage. Every number recomputed by code you can run.</b></p>

<p align="center">
<a href="https://github.com/0xr4j/rakshasutra/actions"><img src="https://github.com/0xr4j/rakshasutra/actions/workflows/ci.yml/badge.svg" alt="tests"></a>
<img src="https://img.shields.io/badge/python-3.10%2B-3776ab" alt="python">
<img src="https://img.shields.io/badge/firmware-C99%20%C2%B7%20ESP32--S3-555" alt="firmware">
<img src="https://img.shields.io/badge/tests-{{Ntests}}%20passing-2ea44f" alt="{{Ntests}} tests">
<img src="https://img.shields.io/badge/status-design%20%C2%B7%20nothing%20measured-C0271D" alt="status: design, nothing measured">
<img src="https://img.shields.io/badge/license-MIT-green" alt="MIT">
</p>

<p align="center">
<a href="https://0xr4j.github.io/rakshasutra/"><b>Website</b></a> ·
<a href="https://0xr4j.github.io/rakshasutra/explorer.html"><b>Open the explorer</b></a> ·
<a href="docs/A-Thread-Through-the-Crowd-Rakshasutra.pdf"><b>The book</b></a> ·
<a href="docs/Rakshasutra-White-Paper-WP01.pdf"><b>White Paper WP-01</b></a> ·
<a href="AUDIT.md"><b>The audit</b></a>
</p>

<p align="center"><img src="docs/img/walk.gif" alt="A simulated parent and child reach a junction and take different tracks. Poles flash as they send uplinks, rings show where the server places each of them, and the control room flags the separation and then an SOS." width="88%"></p>

<p align="center"><sub>One simulated family at a junction. Every advertisement is a real signed frame, the poles run the real filter, and the server sees only {{WalkUplinks}} uplinks. It flags the separation {{WalkSepDelay}} s after they part and raises the SOS {{WalkSosDelay}} s after the button is pressed.</sub></p>

> [!IMPORTANT]
> **This is a design. Nothing has been built or measured.** Every result here is *calculated* from a stated model or *simulated* with a fixed seed, and says which. It is a design study, not a safety system.

---

## Contents

[Why we started](#why-we-started) · [Quickstart](#quickstart) · [How it works](#how-it-works) · [Where the numbers come from](#where-the-numbers-come-from) · [How we modelled it](#how-we-modelled-it) · [How we tested it](#how-we-tested-it) · [Results](#results) · [The audit](#the-audit) · [The mathematics](#the-mathematics) · [Firmware](#firmware) · [Python API](#python-api) · [Repository map](#repository-map) · [Reproduce everything](#reproduce-everything) · [Limits](#limits) · [Next](#next) · [Contributing and security](#contributing-and-security) · [Cite](#cite)

## Why we started

A family walks a crowded mountain path to a shrine. A child lets go of a hand. Phones are in a locker at the top of the hill, the network is down in the valley, and the path forks twice. The cards issued at the gate say that the child entered, and nothing more.

Four ordinary facts about such a route defeat the trackers you can buy: no usable cellular network, passive RFID cards that are seen only at gates, long steel rain shelters that block radio, and phone-free zones near the sanctum. Rakshasutra, named after the protective thread tied on a wrist, turns the problem round. A coin-cell wristband only announces itself over Bluetooth, with an identity that changes every 15 minutes and a signature the server can check. Poles that already stand along the shelters listen, filter what they hear, and forward it over LoRaWAN.

The design began as a white paper. When we set out to publish it with code, we found we could not reproduce all of its numbers. So this repository is two things: a reference model of the design, and an [audit](AUDIT.md) of the paper's first draft, with the corrected values used everywhere.

## Quickstart

```bash
git clone https://github.com/0xr4j/rakshasutra.git
cd rakshasutra
pip install -e .
rakshasutra trace examples/attack_log.csv --registry examples/registry.json
```

```text
{{cmd:rakshasutra trace examples/attack_log.csv --registry examples/registry.json}}
```

Forged alarms and stale frames are dropped. One replayed sighting is believed and flagged; that is a [stated limit](#limits). Other commands:

```bash
rakshasutra frame --key 000102030405060708090a0b0c0d0e0f --counter 17 --sos   # build a signed frame
rakshasutra capacity --tags 3000        # load and loss of one gateway cell, four designs
rakshasutra airtime --bytes 15 64 200   # LoRaWAN time on air
rakshasutra battery                     # battery life and the cold buzzer pulse
rakshasutra link                        # BLE and LoRa link budgets under the roof
rakshasutra audit --results results/summary.json   # the white paper, recomputed
rakshasutra trace examples/adhkuwari_separation.csv --registry examples/registry.json
```

```text
{{cmd:rakshasutra capacity --tags 3000}}
```

## How it works

<p align="center"><img src="docs/img/pipeline.svg" alt="Data path: a wristband sends a signed 15-byte frame; a pole under the roof reports arrivals once and a 64-byte Bloom heartbeat; LoRaWAN in the IN865 band carries it; the server resolves the pseudonym, verifies every SOS and measures distance on the route graph; alerts go out by a band-to-band tether, a Class C wake token and the control room." width="100%"></p>

<details><summary>The same diagram as a Mermaid flowchart</summary>

```mermaid
flowchart LR
    W["<b>1 · Wristband</b><br/>signed 15-byte frame<br/>new ID every 15 min<br/>SOS button, buzzer"] -->|BLE| P["<b>2 · Pole</b><br/>scans under the roof<br/>reports arrivals once<br/>64-byte Bloom heartbeat"]
    P -->|LoRaWAN IN865| S["<b>4 · Server</b><br/>resolves the pseudonym<br/>verifies every SOS<br/>distance on the route graph"]
    H["60 hub poles"] -->|fibre| S
    S --> A["<b>5 · Alerts</b><br/>Class C wake token<br/>control-room alarm"]
    W <-->|tether| T["Parent tag"]
```

</details>

The fifteen bytes a wristband sends every 800 ms:

```text
{{cmd:rakshasutra frame --key 000102030405060708090a0b0c0d0e0f --counter 17 --sos}}
```

A pole does four things with what it hears:

1. **Forwards an SOS at once**, whole, so the server can verify its signature. At most ten a minute.
2. **Reports each wristband once**, when it arrives, in chunks of at most 25 every 15 seconds.
3. **Summarises who is still there** every 60 seconds as a 64-byte Bloom filter, so a frame never exceeds the 222-byte limit however dense the crowd.
4. **Holds no keys.** A stolen pole reveals no identity and cannot forge a wristband.

## Where the numbers come from

There is no measured data yet. Every input is listed in [`data/params.csv`](data/params.csv) with its status:

| Status | Count | Meaning |
|---|---|---|
| `PAPER` | {{Npaper}} | a design value from White Paper WP-01; not measured |
| `STANDARD` | {{Nstandard}} | fixed by a specification (LoRaWAN regional parameters, Bluetooth Core) |
| `DEFINED` | {{Ndefined}} | an encoding the paper left open and this repository had to fix |
| `ASSUMED` | {{Nassumed}} | no source; chosen so that a calculation can run, and flagged where used |

The route follows the white paper's model of the Shri Mata Vaishno Devi trek: 22.5 km in six zones, 255 poles, 762 m to 2,017 m. Pole positions within a zone are schematic ([`data/poles.csv`](data/poles.csv)); it is not a survey.

## How we modelled it

**The signed frame.** AES-128 and AES-CMAC written out in plain Python and in C, checked against the FIPS 197 and RFC 4493 vectors and against an independent library. Code: [`cmac.py`](src/rakshasutra/cmac.py), [`protocol.py`](src/rakshasutra/protocol.py).

**Radio.** The white paper's log-distance model under the steel roof, turned into a margin, a delivery probability and a range. Code: [`linkbudget.py`](src/rakshasutra/linkbudget.py).

**Airtime and capacity.** Exact LoRa time on air for every frame size; Poisson arrivals at each pole; four forwarding designs; pure-ALOHA loss with mixed frame lengths. Code: [`lora.py`](src/rakshasutra/lora.py), [`capacity.py`](src/rakshasutra/capacity.py).

**The pole and the server.** The edge filter of Algorithm 2 and the verification of Algorithm 1, as running code. Code: [`edge.py`](src/rakshasutra/edge.py), [`resolver.py`](src/rakshasutra/resolver.py), [`server.py`](src/rakshasutra/server.py).

**People and power.** The Class A delay, the tether's scan window, capture of passengers at 20 km/h, the current budget, and the supply during a buzzer pulse as an RC circuit. Code: [`kinematics.py`](src/rakshasutra/kinematics.py), [`power.py`](src/rakshasutra/power.py).

## How we tested it

Nothing can be checked in the field yet, so every formula is checked against something that does not use the formula:

| Check | Against | Code |
|---|---|---|
| Frame bytes | RFC 4493 and FIPS 197 vectors, an independent CMAC library, and the C core on 200 random keys | `tests/test_crypto.py`, `tests/test_firmware.py` |
| Collision formula | a Monte Carlo cell: every frame of an hour put on air, {{McFrames}} frames; agreement within {{McErr}} points | `simulate.py` |
| Edge filter | the C core and the Python reference fed the same ten busy minutes; uplinks must be identical | `tests/test_firmware.py` |
| Bloom false positives | direct counting | `tests/test_bloom_and_edge.py` |
| Buzzer droop | a time-stepped integration of the circuit | `tests/test_models.py` |
| Tether and vehicle capture | Monte Carlo against the closed form | `simulate.py` |
| Browser explorer | its JavaScript kernel against Python, under Node | `tests/test_demo_parity.py` |
| The whole chain | a simulated family walk through 48 poles | `simulate.family_walk` |

**{{Ntests}} automated tests** also pin the headline numbers, keep `data/params.csv` in step with the package, and fail if a saved result no longer matches the code. All seeds are fixed, so a rerun reproduces every saved result exactly.

## Results

**A crowd surge in one gateway cell** <sub>(calculated; 60 poles, 8 channels, SF7)</sub>

| Forwarding design | Frames lost with 500 wristbands | with 3,000 |
|---|---|---|
| One uplink per arrival, raw ID list every 60 s | {{LossSingleLow}}% | {{LossSingle}}% |
| Arrivals batched every 15 s, raw ID list | {{LossBatchLow}}% | {{LossBatch}}% |
| Rakshasutra as first specified (chunks, departure lists, Bloom heartbeat) | {{LossRakLow}}% | {{LossRak}}% |
| **Rakshasutra without departure lists** | {{LossRakNdLow}}% | **{{LossRakNd}}%** |

<p align="center"><img src="docs/img/capacity.png" alt="Left: uplink frame loss against the number of wristbands in one gateway cell for four designs, with Monte Carlo points. Right: channel load of each design at 3,000 wristbands, by stream." width="100%"></p>

| Finding | Number |
|---|---|
| Airtime saved against one uplink per arrival | {{AirRedNd}}% ({{AirRed}}% as first specified) |
| A raw ID list is too long for one frame | at {{OversizeBatch}}% of poles with 3,000 wristbands in the cell; the Bloom heartbeat is always 64 bytes |
| Bloom heartbeat false positives | {{BloomFifty}}% with 50 wristbands at a pole, {{BloomHundred}}% with 100 |
| Loss in the deployed layout (about {{DepPoles}} poles per gateway, 5,000 wristbands on the route) | {{DepLossNd}}% |

**People who move**

| Check | Result |
|---|---|
| SOS, button to control room, under the 3,000-wristband surge <sub>(simulated)</sub> | median {{SosMedian}} s; {{SosFour}}% within 4 s; on fibre poles 95% within {{SosFiberP}} s |
| Passenger at 20 km/h reported by a pole <sub>(calculated)</sub> | {{EvCap}}% with 150 other wristbands in range, {{EvCapDense}}% with 300 |
| Same passenger with accelerometer-gated slow advertising and a three-hit rule | at most {{SlowTwo}}% |
| Class A downlink in place of the tether and Class C | 173 s worst case: the person has walked {{ClassAWalk}} m |

<p align="center"><img src="docs/img/tether_ev.png" alt="Left: the tether scan window against how often the parent tag hears the band and how long it spends in false alarm. Right: capture of a passenger at 20 km/h against the crowd around the pole." width="100%"></p>

**Radio and power** <sub>(calculated from design values)</sub>

| Check | Result |
|---|---|
| Bluetooth range under the roof at 98% delivery | {{RangeCoded}} m on Coded PHY, {{RangeOneM}} m on 1M PHY; poles stand up to 108 m apart |
| Same wristband heard by a pole mounted above the steel roof | {{RangeAbove}} m |
| LoRa margin at 8 km behind one ridge | +{{MarginEightOver}} dB with the whip above the roof, −{{MarginEightUnder}} dB with the antenna below it |
| Battery life on a CR2450, Coded PHY | {{LifeWarmCoded}} months at 25 °C, {{LifeColdCoded}} at −5 °C |
| Battery life on 1M PHY | {{LifeWarm}} months at 25 °C, {{LifeCold}} at −5 °C |

<p align="center"><img src="docs/img/power.png" alt="Left: battery life by PHY and temperature. Right: lowest supply voltage during a buzzer pulse in the cold against the size of the hold-up capacitor." width="100%"></p>

**In one sentence:** the limit of the system is LoRa airtime in a surge; batching does most of the work, a fixed-size Bloom filter keeps every frame legal, and three parts of the first design must change before hardware is built.

## The audit

The first draft of the white paper called its results empirical. Nothing had been measured. Each checkable number was recomputed from the paper's own equations and parameters:

| Verdict | Claims | Meaning |
|---|---|---|
| ✅ reproduced | {{AuditRep}} | the model gives the first draft's number |
| ✏️ differs | {{AuditDiff}} | the model gives another number; the revised paper uses the model's |
| 🔧 design fix | {{AuditFix}} | the mechanism does not work as specified; the fix is stated |
| ❓ open | {{AuditOpen}} | needs a datasheet check or a measurement |

The three mechanisms that do not work as first specified:

- **The tether's scan.** A 5 ms scan window every 5 s hears a band that advertises every 800 ms only {{TetherHit}}% of the time, so the parent tag would be in false alarm {{TetherAlarmSim}}% of the time. It needs {{TetherWindow}} ms, or synchronised scanning.
- **The cold buzzer.** A 100 µF capacitor behind a 42 Ω cold cell has a {{TauMs}} ms time constant against a 100 ms pulse. The supply falls to {{DroopCap}} V, below the chip's 1.70 V. It needs {{CapNeed}} µF, or a pulse under {{PulseMax}} mA.
- **Departure lists.** They cost more airtime than the Bloom heartbeat saves. The first draft's 15.8% loss at 3,000 wristbands is {{LossRak}}% as specified and {{LossRakNd}}% without them.

All {{AuditTotal}} entries with notes: [AUDIT.md](AUDIT.md), or the [audit page](https://0xr4j.github.io/rakshasutra/audit.html).

## The mathematics

**The signed frame.** With tag key $K_u$ and slot counter $c$:

$$\mathrm{ID}_{u,c} = \mathrm{Trunc}_{32}\,\mathrm{CMAC}_{K_u}(\mathtt{0x01}\,\Vert\,c), \qquad \mathrm{MIC} = \mathrm{Trunc}_{32}\,\mathrm{CMAC}_{K_u}(\text{bytes } 2 \ldots 10)$$

**Expected counter at the server**, with a three-slot window around it:

$$\hat c_u(t) = \left(c_{init} + \left\lfloor \frac{t - t_{pair}}{900} \right\rfloor\right) \bmod 65536$$

**Received power under the roof** (log-distance, shadowing $X_\sigma$):

$$P_{rx}(d) = P_{tx} - PL(d_0) - 10\,n\,\log_{10}(d/d_0) - L_{body} - X_\sigma$$

**LoRa time on air** for an application payload of $B$ bytes at spreading factor $SF$, coding rate 4/5:

$$T(B) = \frac{2^{SF}}{BW}\left(20.25 + \max\left(\left\lceil \frac{8(13+B) - 4\,SF + 44}{4\,SF} \right\rceil \cdot 5,\ 0\right)\right)$$

**Pure ALOHA with mixed frame lengths.** A frame of length $T_i$ among streams of rate $\lambda_j$ and length $T_j$ on $M$ channels is lost with probability

$$P_{loss,i} = 1 - \exp\left(-\frac{1}{M}\Big(T_i \sum_j \lambda_j + \sum_j \lambda_j T_j\Big)\right)$$

which is $1 - e^{-2G}$ for equal frames.

**Bloom heartbeat**, 512 bits, three probes, $n$ wristbands: $P_{false} = \left(1 - e^{-3n/512}\right)^3$.

**The buzzer pulse.** A cell of voltage $V_0$ and internal resistance $R$, a hold-up capacitor $C$, a pulse of current $I$:

$$V(t) = V_0 - I R \left(1 - e^{-t/RC}\right)$$

The capacitor only helps while $t \ll RC$.

Full derivations, each worked through with numbers, are in [the book](docs/A-Thread-Through-the-Crowd-Rakshasutra.pdf).

## Firmware

[`firmware/`](firmware) holds a portable C99 core with no dynamic memory: AES-128, AES-CMAC, the signed frame, the wake token, the Bloom heartbeat, LoRa time on air, and the pole's edge filter.

```c
rs_pole pole;
rs_pole_init(&pole, 1, -75.0);                        /* transit track: one hit, -75 dBm gate */
rs_pole_on_adv(&pole, payload, 15, rssi, now, send, NULL);   /* every advertisement heard */
rs_pole_flush(&pole, now, send, NULL);                /* every 15 s: arrivals and departures */
rs_pole_heartbeat(&pole, send, NULL);                 /* every 60 s: 64-byte Bloom filter */
```

- `rakshasutra_pole/rs_core.c`, `rs_core.h`: the core; compiled with `-Wall -Wextra -Werror -pedantic` and compared byte for byte with Python by `tests/test_firmware.py`
- `host_test.c`: the harness that test drives
- `rakshasutra_pole/rakshasutra_pole.ino`: an ESP32-S3 sketch (Coded PHY scan, the core, LoRaWAN). **Reference only: not compiled in CI and never run on hardware.**

There is no wristband firmware yet.

## Python API

```python
from rakshasutra import Registry, build_frame, derive_tag_key, parse_frame

master = bytes(range(16))                               # demonstration key only
key = derive_tag_key(master, b"band-0421", b"salt")
frame = build_frame(key, counter=17, flags=0x01)        # SOS pressed
print(frame.hex(" "), parse_frame(frame).sos)

server = Registry()
server.register("band-0421", key, c_init=17, t_pair=0.0)
print(server.resolve_frame(pole=131, frame=frame, rssi_dbm=-62, t=30.0))
# Result(status='OK', uid='band-0421', sos=True, location=131)
```

```python
from rakshasutra import capacity, power, lora

cell = capacity.cell_load("rakshasutra", tags=3000, departures=False)
print(f"{cell.load:.3f} {cell.loss:.3f}")                # {{LoadRakNdFrac}} {{LossRakNdFrac}}
print(f"{lora.time_on_air(64) * 1000:.2f} ms")           # {{ToaBloom}} ms
print(power.pulse_droop(capacitor_uf=100)["brownout"])  # True
```

## Repository map

```
rakshasutra/
├── src/rakshasutra/       the reference model
│   ├── cmac.py · protocol.py   AES-CMAC; the signed frame, radio address and wake token
│   ├── resolver.py · server.py identity resolution (Algorithm 1) and the control room
│   ├── edge.py · bloom.py      the pole's edge filter (Algorithm 2) and the 64-byte heartbeat
│   ├── lora.py · capacity.py   time on air, ALOHA loss, load of a gateway cell
│   ├── linkbudget.py           BLE and LoRa budgets under the steel roof
│   ├── kinematics.py · power.py   alerts and moving people; battery and the cold pulse
│   ├── trek.py                 the route as a graph of 255 poles
│   ├── simulate.py             Monte Carlo checks and the end-to-end family walk
│   ├── audit.py · params.py    the audit; every parameter with its source
│   └── cli.py                  the `rakshasutra` command
├── firmware/              C core, host test, ESP32-S3 pole sketch
├── experiments/           one script per study, figures, README assets
├── tests/                 {{Ntests}} automated tests
├── data/                  parameters, zones and poles
├── results/               saved output of every study
├── generated/             numbers, tables and figures written from the results
├── examples/              a family walk and an attack log to replay
├── book/ · whitepaper/    LaTeX sources of the book and of WP-01
├── demo/                  sources of the website and the browser explorer
└── docs/                  website, explorer and PDFs (GitHub Pages)
```

## Reproduce everything

```bash
pip install -r requirements.txt && pip install --no-deps -e .
make test         # {{Ntests}} tests, about 15 seconds; compiles the firmware core and runs the browser kernel
make results      # every study, a few seconds, all seeds fixed
make examples generated assets
make book whitepaper site
```

Every number in the book, the white paper, this README and the website is written from the result files by script, never typed by hand. This README is built from [`generated/README.tmpl.md`](generated/README.tmpl.md).

## Limits

- **Nothing is measured.** Roof loss, the path-loss exponent, body loss and the currents are design values. Every range and lifetime depends on them.
- **The route is schematic**, not a survey, and the work is not commissioned or endorsed by the Shrine Board.
- **Ordinary sightings are not authenticated.** Arrival reports carry no MIC, so a frame replayed at another pole inside its 45-minute slot window is believed. Only SOS frames are fully verified. The server flags impossible speeds.
- **A wristband can be followed within one 15-minute slot**, and whoever holds the server's master key can follow all of them.
- **The capacity model is simple and pessimistic:** Poisson movement, pure ALOHA, no capture effect, one spreading factor.
- **Bluetooth scanning in a dense crowd is barely modelled.** A real scanner following extended advertisements will do worse.
- **The latency of the Class C wake token is not modelled.**
- **The pole sketch has never run on hardware** and there is no wristband firmware.
- This is research software and a design study. It is not a safety system and must not be relied on as one.

## Next

<p align="center"><img src="docs/img/roadmap.svg" alt="Roadmap: reference model done in November 2026; protocol revision next; then bench radio, a prototype, a pilot and peer review." width="100%"></p>

The next number should be a measurement. Three inputs carry the radio chapter and can be measured in an afternoon under any galvanised iron shed: roof loss at 2.44 GHz and at 866 MHz, and the path-loss exponent beneath it. Timeline and rules fixed in advance: [ROADMAP.md](ROADMAP.md).

Have a GI shelter and an afternoon, experience with dense Bluetooth scanning, or a role in crowd safety? [Offer a measurement or field access](https://github.com/0xr4j/rakshasutra/issues/new?template=offer-data.yml).

## Contributing and security

Bug reports, measurements and pull requests are welcome; see [CONTRIBUTING.md](CONTRIBUTING.md). To report a security problem privately, including a weakness in the protocol, follow [SECURITY.md](SECURITY.md).

## Cite

```
Jha R. A Thread Through the Crowd. Rakshasutra: Design, Model and Audit.
Self-published, 2026. https://github.com/0xr4j/rakshasutra
```

Citation metadata is in [`CITATION.cff`](CITATION.cff). Code under the MIT licence; the book and white paper under CC BY 4.0. Neither has been peer reviewed.

<sub>Raj Jha · independent researcher</sub>
