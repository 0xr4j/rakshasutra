# Firmware

| File | What it is | Status |
|---|---|---|
| `rakshasutra_pole/rs_core.c`, `rs_core.h` | Portable C99 core: AES-128, AES-CMAC, the signed 15-byte frame, the wake token, the 64-byte Bloom heartbeat, LoRa time on air, and the pole's edge filter (Algorithm 2). No dynamic memory. | Compiled with `-Wall -Wextra -pedantic` and compared byte for byte with the Python reference by `tests/test_firmware.py`. |
| `host_test.c` | Command-driven harness used by that test. | Runs in CI. |
| `rakshasutra_pole/rakshasutra_pole.ino` | ESP32-S3 sketch: Coded PHY scan, the core, LoRaWAN uplinks. | **Reference only. Not compiled in CI, never run on hardware.** |

The wearable firmware (nRF52 family) is not written yet. It needs only `rs_build_frame`,
`rs_mac_address` and a wake-token check from the core, all of which are tested here.

## Build the host test

```bash
gcc -O2 -std=c99 -Wall -Wextra -pedantic -I firmware/rakshasutra_pole \
    firmware/host_test.c firmware/rakshasutra_pole/rs_core.c -lm -o host_test
echo "F 000102030405060708090a0b0c0d0e0f 17 1 150 0" | ./host_test
# 5aff0411003c34fdc901968c83e42f d41b8a54a8dc 3c34fdc90198043e
```

## What a pole may and may not hold

A pole holds its own LoRaWAN keys and nothing else. It never receives the master key or
any tag key, so a stolen pole reveals no identities and cannot forge a wearable. Keys do
not belong in source code: the sketch reads them from encrypted storage.

The AES in `rs_core.c` is a plain table implementation for checking bytes. It is not
constant-time. On the wearable, use the SoC's AES hardware.
