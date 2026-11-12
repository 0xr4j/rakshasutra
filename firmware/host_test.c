/* Host test for rs_core.c. Reads commands on stdin, prints results; tests/test_firmware.py
 * runs the same commands through the Python reference and compares the output.
 *
 *   F <key hex> <counter> <flags> <battery code> <role>   -> frame, radio address, wake token
 *   V <key hex> <frame hex>                               -> 1 or 0
 *   M <key hex> <message hex or ->                        -> AES-CMAC
 *   T <app bytes> <sf>                                    -> time on air, ms
 *   I <hits required> <rssi gate>                         -> start a pole
 *   A <time> <rssi> <payload hex>                         -> feed an advertisement
 *   X <time>                                              -> 15 s flush
 *   H                                                     -> 60 s heartbeat
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "rs_core.h"

static rs_pole pole;

static size_t unhex(const char *s, uint8_t *out, size_t max) {
    size_t n = 0;
    unsigned v;
    if (s[0] == '-') return 0;
    while (s[0] && s[1] && n < max && sscanf(s, "%2x", &v) == 1) { out[n++] = (uint8_t)v; s += 2; }
    return n;
}

static void hex(const uint8_t *b, size_t n) { size_t i; for (i = 0; i < n; i++) printf("%02x", b[i]); }

static void send(uint8_t fport, const uint8_t *payload, size_t len, int confirmed, void *ctx) {
    (void)ctx;
    printf("U %d %d ", fport, confirmed);
    hex(payload, len);
    printf("\n");
}

int main(void) {
    char line[1024], a[512], b[512];
    uint8_t key[16], buf[256], out[16];
    while (fgets(line, sizeof line, stdin)) {
        int i1, i2, i3, i4;
        double d1, d2;
        if (sscanf(line, "F %511s %d %d %d %d", a, &i1, &i2, &i3, &i4) == 5) {
            uint8_t frame[RS_FRAME_LEN], mac[6], token[8];
            unhex(a, key, 16);
            rs_build_frame(key, (uint16_t)i1, (uint8_t)i2, (uint8_t)i3, (uint8_t)i4, frame);
            rs_mac_address(key, (uint16_t)i1, mac);
            rs_wake_token(key, (uint16_t)i1, 1, token);
            hex(frame, RS_FRAME_LEN); printf(" "); hex(mac, 6); printf(" "); hex(token, 8); printf("\n");
        } else if (sscanf(line, "V %511s %511s", a, b) == 2) {
            unhex(a, key, 16);
            printf("%d\n", unhex(b, buf, sizeof buf) == RS_FRAME_LEN ? rs_verify_frame(key, buf) : 0);
        } else if (sscanf(line, "M %511s %511s", a, b) == 2) {
            size_t n;
            unhex(a, key, 16);
            n = unhex(b, buf, sizeof buf);
            rs_cmac(key, buf, n, out);
            hex(out, 16); printf("\n");
        } else if (sscanf(line, "T %d %d", &i1, &i2) == 2) {
            printf("%.3f\n", rs_time_on_air_ms(i1, i2));
        } else if (sscanf(line, "I %d %lf", &i1, &d1) == 2) {
            rs_pole_init(&pole, i1, d1);
        } else if (sscanf(line, "A %lf %lf %511s", &d1, &d2, a) == 3) {
            size_t n = unhex(a, buf, sizeof buf);
            rs_pole_on_adv(&pole, buf, n, d2, d1, send, NULL);
        } else if (sscanf(line, "X %lf", &d1) == 1) {
            rs_pole_flush(&pole, d1, send, NULL);
        } else if (line[0] == 'H') {
            rs_pole_heartbeat(&pole, send, NULL);
        }
    }
    return 0;
}
