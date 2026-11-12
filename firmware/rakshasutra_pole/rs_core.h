/* Rakshasutra core: the signed advertisement, the Bloom heartbeat and the pole's edge filter.
 *
 * Portable C99, no dynamic memory. The same file builds for the pole (ESP32-S3) and for a
 * host test that is compared byte for byte with the Python reference (tests/test_firmware.py).
 *
 * Status: checked on a host computer only. Nothing here has run on the target hardware yet.
 */
#ifndef RS_CORE_H
#define RS_CORE_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define RS_COMPANY_ID 0xFF5Au
#define RS_VERSION 0x4u
#define RS_FRAME_LEN 15
#define RS_SLOT_SECONDS 900u
#define RS_F_SOS 0x01u
#define RS_F_TETHER_LOST 0x02u
#define RS_F_BUZZER 0x04u
#define RS_F_LOW_BATTERY 0x08u

#define RS_BLOOM_BYTES 64
#define RS_TABLE_SIZE 1024
#define RS_CHUNK_TAGS 25
#define RS_DEPART_PER_FRAME 50
#define RS_DEPART_TIMEOUT_S 90.0
#define RS_SOS_PER_MINUTE 10
#define RS_SOS_CACHE 32

#define RS_FPORT_ARRIVALS 1
#define RS_FPORT_DEPARTURES 2
#define RS_FPORT_HEARTBEAT 3
#define RS_FPORT_SOS 10

/* ---- cryptography (what a wearable and the server run; a pole never holds a tag key) */
void rs_aes128_encrypt(const uint8_t key[16], const uint8_t in[16], uint8_t out[16]);
void rs_cmac(const uint8_t key[16], const uint8_t *msg, size_t len, uint8_t tag[16]);
void rs_rolling_id(const uint8_t key[16], uint16_t counter, uint8_t id[4]);
void rs_mac_address(const uint8_t key[16], uint16_t counter, uint8_t mac[6]);
void rs_build_frame(const uint8_t key[16], uint16_t counter, uint8_t flags, uint8_t battery_code,
                    uint8_t role, uint8_t frame[RS_FRAME_LEN]);
int rs_verify_frame(const uint8_t key[16], const uint8_t frame[RS_FRAME_LEN]);
void rs_wake_token(const uint8_t key[16], uint16_t counter, uint8_t command, uint8_t token[8]);

/* ---- Bloom heartbeat */
uint16_t rs_crc16(const uint8_t *data, size_t len);
uint32_t rs_fnv1a(const uint8_t *data, size_t len);
void rs_bloom_add(uint8_t bloom[RS_BLOOM_BYTES], const uint8_t id[4]);
int rs_bloom_has(const uint8_t bloom[RS_BLOOM_BYTES], const uint8_t id[4]);

/* ---- LoRa time on air in milliseconds for an application payload (SF7..SF10, 125 kHz, 4/5) */
double rs_time_on_air_ms(int app_bytes, int sf);

/* ---- the pole's edge filter (white paper, Algorithm 2) */
typedef struct {
    uint8_t used, reported, flags;
    uint8_t id[4];
    uint16_t counter, hits;
    double rssi, last_seen;
} rs_entry;

typedef struct {
    int hits_required;      /* 1 on transit tracks, 3 in dense hubs */
    double rssi_gate;       /* -75 dBm on tracks, -65 dBm in hubs */
    rs_entry table[RS_TABLE_SIZE];
    uint8_t arrivals[RS_TABLE_SIZE][8];
    int n_arrivals;
    uint8_t departures[RS_TABLE_SIZE][4];
    int n_departures;
    double sos_times[RS_SOS_PER_MINUTE];
    int n_sos;
    uint8_t sos_id[RS_SOS_CACHE][4];
    double sos_at[RS_SOS_CACHE];
    uint32_t dropped_full;
} rs_pole;

typedef void (*rs_send_fn)(uint8_t fport, const uint8_t *payload, size_t len, int confirmed, void *ctx);

void rs_pole_init(rs_pole *p, int hits_required, double rssi_gate);
/* Feed one received advertisement payload. Returns 1 if an SOS uplink was sent. */
int rs_pole_on_adv(rs_pole *p, const uint8_t *payload, size_t len, double rssi_dbm, double now,
                   rs_send_fn send, void *ctx);
/* Call every 15 s: sends arrival chunks (FPort 1) and departure lists (FPort 2). */
void rs_pole_flush(rs_pole *p, double now, rs_send_fn send, void *ctx);
/* Call every 60 s: sends the 64-byte Bloom heartbeat (FPort 3) if anyone is here. */
void rs_pole_heartbeat(rs_pole *p, rs_send_fn send, void *ctx);

#ifdef __cplusplus
}
#endif
#endif
