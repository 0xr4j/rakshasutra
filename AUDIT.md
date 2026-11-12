# Reproduction audit

Every checkable number in the first draft of White Paper WP-01 (October 2026), recomputed by the code in this
repository from the paper's own equations and parameters. The revised paper and the book use the model's
numbers. This file is written by `generated/make_numbers.py` from `results/audit.json`; run
`rakshasutra audit --results results/summary.json` to print it.

**42 claims: 16 reproduced, 16 differ, 6 need a design fix, 4 are open.** Nothing here has been measured; every value is calculated or simulated.

| | Section | Claim | First draft | This model | Verdict |
|---|---|---|---|---|---|
| A01 | V-A | Time on air, SOS frame (15 B, SF7) | 66.82 | 66.82 ms | ✅ reproduced |
| A02 | V-A | Time on air, Bloom heartbeat (64 B, SF7) | 138.5 | 138.5 ms | ✅ reproduced |
| A03 | V-A | Time on air, 25-tag chunk (200 B, SF7) | 338.18 | 338.18 ms | ✅ reproduced |
| A04 | V-B | Pseudonyms that fit one raw 222-byte list | 55 | 55 IDs | ✅ reproduced |
| A05 | III-B | Maximum allowable LoRa path loss, whip above the roof | 145.4 | 145.4 dB | ✅ reproduced |
| A06 | III-B | BLE Coded PHY margin at 50 m, heavy crowd | 28.6 | 20.3 dB | ✏️ differs |
| A07 | VI-A | BLE range at 98% delivery, pole above the roof, 1M PHY, +4 dBm | 4.2 | 4.1 m | ✅ reproduced |
| A08 | VI-A | BLE range at 98% delivery, pole under the roof, 1M PHY | 28.5 | 82.2 m | ✏️ differs |
| A09 | VI-A | BLE range at 98% delivery, pole under the roof, Coded PHY | 92.0 | 174.0 m | ✏️ differs |
| A10 | VI-A | LoRa range, whip above the roof | 5.4-8.8 km | 16.1 dB margin at 8 km  | ❓ open |
| A11 | VI-A | LoRa range, antenna under the roof | 0.85 km | -4.4 dB margin at 8 km  | ❓ open |
| A12 | VI-B | Uplink loss, raw forwarding, 500 tags in the cell | 97.7 | 97.1 % | ✅ reproduced |
| A13 | VI-B | Uplink loss, raw forwarding, 3,000 tags in the cell | 100.0 | 100.0 % | ✅ reproduced |
| A14 | VI-B | Uplink loss, single-event arrivals, 500 tags in the cell | 12.2 | 14.1 % | ✏️ differs |
| A15 | VI-B | Uplink loss, single-event arrivals, 3,000 tags in the cell | 54.2 | 57.6 % | ✏️ differs |
| A16 | VI-B | Uplink loss, 15 s batching, 500 tags in the cell | 5.8 | 8.6 % | ✏️ differs |
| A17 | VI-B | Uplink loss, 15 s batching, 3,000 tags in the cell | 22.1 | 25.3 % | ✏️ differs |
| A18 | VI-B | Uplink loss, Rakshasutra, 500 tags in the cell | 4.1 | 14.3 % | ✏️ differs |
| A19 | VI-B | Uplink loss, Rakshasutra, 3,000 tags in the cell | 15.8 | 30.5 % | ✏️ differs |
| A20 | VI-B | Uplink loss, Rakshasutra without departure lists, 3,000 tags | 15.8 | 21.3 % | 🔧 design fix |
| A21 | Abstract | Reduction in LoRa airtime, 3,000 tags | 82.4 | 57.6 % | ✏️ differs |
| A22 | VI-B | Uplink loss in the deployed layout, 5,000 tags on the trek | < 6 | 11.0 % | ✏️ differs |
| A23 | V-C | Class A worst-case alert delay | 173 | 173.0 s | ✅ reproduced |
| A24 | V-C | Distance walked during that delay | 215 | 216 m | ✅ reproduced |
| A25 | V-C | Time an EV passenger spends in a 25 m core zone | 4.5 | 4.5 s | ✅ reproduced |
| A26 | V-C | EV capture with one decoded frame required | 99.4 | 99.7 % | ✅ reproduced |
| A27 | V-C | Tether: chance one 5 ms scan hears the child's band | assumed 1 | 0.48 % | 🔧 design fix |
| A28 | V-C | Tether: separation at which the alert sounds | 25-30 m | 174 m  | 🔧 design fix |
| A29 | VI-C | Mean current on the trek (Table V) | 29.74 | 29.74 uA | ✅ reproduced |
| A30 | VI-C | Battery life at 25 C, from Table V | 14.2 | 48.2 months | ✏️ differs |
| A31 | VI-C | Battery life at -5 C, from Table V | 11.1 | 33.8 months | ✏️ differs |
| A32 | VI-C | Transmit time per advertisement on Coded PHY | 1.25 | 5.95 ms | ✏️ differs |
| A33 | VI-C | Supply during an unbuffered buzzer pulse at -5 C | 1.61 | 1.61 V | ✅ reproduced |
| A34 | VI-C | Supply during the pulse with the 100 uF capacitor | 2.68 | 1.61 V | 🔧 design fix |
| A35 | IV-E | Chance of forging an SOS in one try | 2.33e-10 | 2.33e-10  | ✅ reproduced |
| A36 | IV-E | Chance of forging a wake token in one try | 5.96e-08 | 5.96e-08  | ✅ reproduced |
| A37 | IV-D | Pseudonyms are unique in the lookup table | assumed | 10% chance of a clash  | 🔧 design fix |
| A38 | IV-A | Replayed frames are rejected | all | outside the 3-slot window  | 🔧 design fix |
| A39 | V-B | Bloom heartbeat false-positive rate | not stated | 1.6% at 50 tags, 57% at 300  | ❓ open |
| A40 | III-A | Pole spacing on the LoRa tracks | 25-100 m | 108 m  | ✏️ differs |
| A41 | III-B | Wearable transmit power on the nRF52811 | +8 dBm | +4 dBm  | ❓ open |
| A42 | Abstract | SOS reaches the control room within 4 s (3,000-tag surge) | all | 92% (median 0.5 s)  | ✏️ differs |

## Notes

- **A06** Eq. 2 with the stated parameters gives 20.3 dB. The first draft's figure needs 8.3 dB of antenna gain that the paper does not specify.
- **A08** Eq. 2 gives a longer range than the first draft's table. Either way it covers the pole spacing.
- **A09** Eq. 2 gives a longer range than the first draft's table. Either way it covers the pole spacing.
- **A10** The paper states no pole-to-gateway path-loss model, so a range cannot be recomputed. With free-space loss and one assumed 20 dB ridge the split antenna keeps a positive margin at 8 km.
- **A11** Same model: the 18.4 dB roof loss and 3 dB body loss leave a negative margin at 8 km.
- **A12** Same order of magnitude; the paper does not give the size of a forwarded ping (7 B assumed here).
- **A13** Same order of magnitude; the paper does not give the size of a forwarded ping (7 B assumed here).
- **A14** The first draft counted arrivals only; the model also counts the 60 s raw heartbeat.
- **A15** The first draft counted arrivals only; the model also counts the 60 s raw heartbeat.
- **A16** The first draft counted arrivals only; the model also counts the 60 s raw heartbeat.
- **A17** The first draft counted arrivals only; the model also counts the 60 s raw heartbeat.
- **A18** The model counts all three streams of Algorithm 2: arrival chunks, departure lists and the Bloom heartbeat. The first draft's figures are not reached by any of them.
- **A19** The model counts all three streams of Algorithm 2: arrival chunks, departure lists and the Bloom heartbeat. The first draft's figures are not reached by any of them.
- **A20** Departure lists (FPort 2) cost more airtime than the Bloom heartbeat saves. Dropping them, and inferring departure from the next arrival and the heartbeat, cuts the load by a third.
- **A21** Against single-event forwarding. Without departure lists the reduction is 72.1%.
- **A22** 637 tags and 32 poles per gateway cell.
- **A26** The paper gives no per-frame success rate. With 150 other wearables in range of the pole the model gives this figure; with 300 it falls to 95.0%.
- **A27** A 5 ms window every 5 s almost never coincides with an advertisement sent every 800 ms: four scans in a row all miss 98% of the time with the child beside the parent. A window of 811 ms cannot miss; it costs 746 uA.
- **A28** Losing the signal happens at the edge of radio range, not at 25-30 m. To alert at 30 m the parent tag must treat an RSSI below about -78 dBm as a miss.
- **A30** Table V as printed gives a much longer life than the first draft stated.
- **A31** As above.
- **A32** 1.25 ms fits a 1M PHY event. On Coded PHY S=8 the same 15 bytes take 5.95 ms, which gives 12.8 months at 25 C and 9.0 months at -5 C.
- **A34** 100 uF behind 42 ohm has a time constant of 4.2 ms, far shorter than the 100 ms pulse, so it does not hold the supply up. Either the capacitor must be at least 895 uF or the pulse current at most 29.8 mA.
- **A37** With 10,000 tags and a three-slot window, two entries share a 32-bit pseudonym about one time in ten. The table therefore maps a pseudonym to a list and separates clashes by the slot counter.
- **A38** Arrival tuples carry no MIC and poles hold no keys, so a frame replayed at another pole within its own slot window (up to 45 minutes) is accepted as a sighting. Only SOS frames are fully verified.
- **A39** 64 bytes hold about 78 wearables at a 5% error rate. Dense hub poles are on fibre and can send a larger filter.
- **A40** 195 poles over 21.0 km of track is one pole per 108 m. Still inside the Coded PHY range of Eq. 2.
- **A41** The nRF52811 is specified up to +4 dBm. +8 dBm needs a part such as the nRF52820 or nRF52833. To be confirmed against the datasheet before the bill of materials is fixed.
- **A42** Simulation. The first LoRa attempt is lost 23% of the time under the surge, and a repeat waits an assumed 3 s. On fibre poles every SOS arrives in under a second.

## What the verdicts mean

- **reproduced**: the model gives the first draft's number.
- **differs**: the model gives a different number; the revised paper uses the model's.
- **design fix**: the mechanism does not work as first specified; the note says what does.
- **open**: cannot be settled by calculation; it needs a datasheet check or a measurement.
