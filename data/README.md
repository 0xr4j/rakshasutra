# Data

There are no measurements in this repository yet. These files are the model's inputs, written from the package by
`experiments/write_params.py`.

| File | Content |
|---|---|
| `params.csv` | Every model parameter with its value, unit, status and source. Status is `PAPER` (a design value from White Paper WP-01, not measured), `STANDARD` (fixed by a specification), `DEFINED` (an encoding this repository had to fix), or `ASSUMED` (no source; chosen so a calculation can run). |
| `zones.csv` | The six zones of the model route: length, poles, mean spacing, backhaul. |
| `poles.csv` | The 255 poles: segment, zone, position along the segment, altitude, backhaul and neighbours. |

Zone lengths, the pole total and the altitude range follow the white paper, which models the Shri Mata Vaishno Devi
route. Pole positions and altitudes within a zone are schematic. This is not a survey of the real track.
