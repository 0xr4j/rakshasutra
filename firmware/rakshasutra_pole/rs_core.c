/* Rakshasutra core. See rs_core.h. */
#include "rs_core.h"

#include <math.h>
#include <string.h>

/* ------------------------------------------------------------------ AES-128 (FIPS 197) */
static const uint8_t SBOX[256] = {
    0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,
    0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,
    0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,
    0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,
    0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,
    0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,
    0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,
    0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,
    0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,
    0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,
    0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,
    0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,
    0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,
    0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,
    0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,
    0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16};
static const uint8_t RCON[10] = {0x01,0x02,0x04,0x08,0x10,0x20,0x40,0x80,0x1b,0x36};

static uint8_t xtime(uint8_t a) { return (uint8_t)((a << 1) ^ ((a & 0x80) ? 0x1b : 0x00)); }

void rs_aes128_encrypt(const uint8_t key[16], const uint8_t in[16], uint8_t out[16]) {
    uint8_t rk[176], s[16], t[16];
    int i, r, c;
    memcpy(rk, key, 16);
    for (i = 16; i < 176; i += 4) {
        uint8_t w[4];
        memcpy(w, rk + i - 4, 4);
        if (i % 16 == 0) {
            uint8_t x = w[0];
            w[0] = (uint8_t)(SBOX[w[1]] ^ RCON[i / 16 - 1]);
            w[1] = SBOX[w[2]]; w[2] = SBOX[w[3]]; w[3] = SBOX[x];
        }
        for (c = 0; c < 4; c++) rk[i + c] = (uint8_t)(rk[i - 16 + c] ^ w[c]);
    }
    for (i = 0; i < 16; i++) s[i] = (uint8_t)(in[i] ^ rk[i]);
    for (r = 1; r <= 10; r++) {
        for (i = 0; i < 16; i++) s[i] = SBOX[s[i]];
        for (c = 0; c < 4; c++)                       /* ShiftRows, state is column-major */
            for (i = 0; i < 4; i++) t[4 * c + i] = s[(4 * (c + i) + i) % 16];
        if (r != 10) {
            for (c = 0; c < 4; c++) {
                uint8_t a0 = t[4*c], a1 = t[4*c+1], a2 = t[4*c+2], a3 = t[4*c+3];
                s[4*c]   = (uint8_t)(xtime(a0) ^ xtime(a1) ^ a1 ^ a2 ^ a3);
                s[4*c+1] = (uint8_t)(a0 ^ xtime(a1) ^ xtime(a2) ^ a2 ^ a3);
                s[4*c+2] = (uint8_t)(a0 ^ a1 ^ xtime(a2) ^ xtime(a3) ^ a3);
                s[4*c+3] = (uint8_t)(xtime(a0) ^ a0 ^ a1 ^ a2 ^ xtime(a3));
            }
        } else {
            memcpy(s, t, 16);
        }
        for (i = 0; i < 16; i++) s[i] ^= rk[16 * r + i];
    }
    memcpy(out, s, 16);
}

/* ------------------------------------------------------------------ AES-CMAC (RFC 4493) */
static void dbl(uint8_t b[16]) {
    int i, carry = b[0] & 0x80;
    for (i = 0; i < 15; i++) b[i] = (uint8_t)((b[i] << 1) | (b[i + 1] >> 7));
    b[15] = (uint8_t)(b[15] << 1);
    if (carry) b[15] ^= 0x87;
}

void rs_cmac(const uint8_t key[16], const uint8_t *msg, size_t len, uint8_t tag[16]) {
    uint8_t k1[16] = {0}, k2[16], x[16] = {0}, last[16];
    size_t n = len ? (len + 15) / 16 : 1, i, j, rem = len - (n - 1) * 16;
    int complete = len > 0 && len % 16 == 0;
    rs_aes128_encrypt(key, k1, k1);
    dbl(k1);
    memcpy(k2, k1, 16);
    dbl(k2);
    for (i = 0; i + 1 < n; i++) {
        for (j = 0; j < 16; j++) x[j] ^= msg[16 * i + j];
        rs_aes128_encrypt(key, x, x);
    }
    memset(last, 0, 16);
    if (len) memcpy(last, msg + 16 * (n - 1), rem);
    if (!complete) last[rem] = 0x80;
    for (j = 0; j < 16; j++) x[j] ^= (uint8_t)(last[j] ^ (complete ? k1[j] : k2[j]));
    rs_aes128_encrypt(key, x, tag);
}

/* ------------------------------------------------------------------ the signed advertisement */
void rs_rolling_id(const uint8_t key[16], uint16_t counter, uint8_t id[4]) {
    uint8_t m[3] = {0x01, (uint8_t)(counter & 0xff), (uint8_t)(counter >> 8)}, tag[16];
    rs_cmac(key, m, 3, tag);
    memcpy(id, tag, 4);
}

void rs_mac_address(const uint8_t key[16], uint16_t counter, uint8_t mac[6]) {
    uint8_t m[3] = {0x02, (uint8_t)(counter & 0xff), (uint8_t)(counter >> 8)}, tag[16];
    rs_cmac(key, m, 3, tag);
    memcpy(mac, tag, 6);
    mac[0] |= 0xC0;                                   /* static random address: two top bits set */
}

void rs_build_frame(const uint8_t key[16], uint16_t counter, uint8_t flags, uint8_t battery_code,
                    uint8_t role, uint8_t frame[RS_FRAME_LEN]) {
    uint8_t tag[16];
    frame[0] = (uint8_t)(RS_COMPANY_ID & 0xff);
    frame[1] = (uint8_t)(RS_COMPANY_ID >> 8);
    frame[2] = (uint8_t)(RS_VERSION | ((role & 1u) << 4));
    frame[3] = (uint8_t)(counter & 0xff);
    frame[4] = (uint8_t)(counter >> 8);
    rs_rolling_id(key, counter, frame + 5);
    frame[9] = flags;
    frame[10] = battery_code;
    rs_cmac(key, frame + 2, 9, tag);
    memcpy(frame + 11, tag, 4);
}

int rs_verify_frame(const uint8_t key[16], const uint8_t frame[RS_FRAME_LEN]) {
    uint8_t id[4], tag[16], diff = 0;
    uint16_t counter = (uint16_t)(frame[3] | (frame[4] << 8));
    int i;
    if (frame[0] != (RS_COMPANY_ID & 0xff) || frame[1] != (RS_COMPANY_ID >> 8)) return 0;
    if ((frame[2] & 0x0f) != RS_VERSION) return 0;
    rs_rolling_id(key, counter, id);
    rs_cmac(key, frame + 2, 9, tag);
    for (i = 0; i < 4; i++) diff |= (uint8_t)((id[i] ^ frame[5 + i]) | (tag[i] ^ frame[11 + i]));
    return diff == 0;
}

void rs_wake_token(const uint8_t key[16], uint16_t counter, uint8_t command, uint8_t token[8]) {
    uint8_t m[4] = {0x03, (uint8_t)(counter & 0xff), (uint8_t)(counter >> 8), command}, tag[16];
    rs_rolling_id(key, counter, token);
    token[4] = command;
    rs_cmac(key, m, 4, tag);
    memcpy(token + 5, tag, 3);
}

/* ------------------------------------------------------------------ Bloom heartbeat */
uint16_t rs_crc16(const uint8_t *data, size_t len) {
    uint16_t crc = 0xFFFF;
    size_t i;
    int b;
    for (i = 0; i < len; i++) {
        crc ^= (uint16_t)(data[i] << 8);
        for (b = 0; b < 8; b++) crc = (uint16_t)((crc & 0x8000) ? ((crc << 1) ^ 0x1021) : (crc << 1));
    }
    return crc;
}

uint32_t rs_fnv1a(const uint8_t *data, size_t len) {
    uint32_t h = 0x811C9DC5u;
    size_t i;
    for (i = 0; i < len; i++) h = (h ^ data[i]) * 0x01000193u;
    return h;
}

static uint32_t bloom_bit(const uint8_t id[4], int j) {
    uint64_t h1 = rs_crc16(id, 4), h2 = rs_fnv1a(id, 4);
    return (uint32_t)((h1 + (uint64_t)j * h2) % 512u);
}

void rs_bloom_add(uint8_t bloom[RS_BLOOM_BYTES], const uint8_t id[4]) {
    int j;
    for (j = 0; j < 3; j++) {
        uint32_t i = bloom_bit(id, j);
        bloom[i >> 3] |= (uint8_t)(1u << (i & 7));
    }
}

int rs_bloom_has(const uint8_t bloom[RS_BLOOM_BYTES], const uint8_t id[4]) {
    int j;
    for (j = 0; j < 3; j++) {
        uint32_t i = bloom_bit(id, j);
        if (!(bloom[i >> 3] & (1u << (i & 7)))) return 0;
    }
    return 1;
}

/* ------------------------------------------------------------------ LoRa time on air */
double rs_time_on_air_ms(int app_bytes, int sf) {
    int pl = app_bytes + 13;                           /* LoRaWAN MAC overhead */
    double tsym = (double)(1 << sf) / 125.0;           /* milliseconds at 125 kHz */
    double n = ceil((8.0 * pl - 4.0 * sf + 28.0 + 16.0) / (4.0 * sf)) * 5.0;
    if (n < 0) n = 0;
    return tsym * (8 + 4.25 + 8 + n);
}

/* ------------------------------------------------------------------ edge filter */
void rs_pole_init(rs_pole *p, int hits_required, double rssi_gate) {
    memset(p, 0, sizeof(*p));
    p->hits_required = hits_required;
    p->rssi_gate = rssi_gate;
}

static uint8_t encode_rssi(double rssi) {
    double v = floor(-rssi + 0.5);
    return (uint8_t)(v < 0 ? 0 : v > 255 ? 255 : v);
}

static int sos_allowed(rs_pole *p, const uint8_t id[4], double now) {
    int i, n = 0, slot = 0;
    for (i = 0; i < p->n_sos; i++)                     /* keep only the last 60 s */
        if (now - p->sos_times[i] < 60.0) p->sos_times[n++] = p->sos_times[i];
    p->n_sos = n;
    if (p->n_sos >= RS_SOS_PER_MINUTE) return 0;
    for (i = 0; i < RS_SOS_CACHE; i++) {
        if (p->sos_at[i] != 0.0 && memcmp(p->sos_id[i], id, 4) == 0 &&
            now - p->sos_at[i] < RS_DEPART_TIMEOUT_S) return 0;
        if (p->sos_at[i] < p->sos_at[slot]) slot = i;  /* oldest (or empty) slot */
    }
    memcpy(p->sos_id[slot], id, 4);
    p->sos_at[slot] = now;
    p->sos_times[p->n_sos++] = now;
    return 1;
}

int rs_pole_on_adv(rs_pole *p, const uint8_t *payload, size_t len, double rssi_dbm, double now,
                   rs_send_fn send, void *ctx) {
    const uint8_t *id;
    uint16_t counter;
    uint8_t flags;
    int i, sent = 0, free_slot = -1;
    rs_entry *e = NULL;
    if (len != RS_FRAME_LEN || payload[0] != (RS_COMPANY_ID & 0xff) || payload[1] != (RS_COMPANY_ID >> 8))
        return 0;
    id = payload + 5;
    counter = (uint16_t)(payload[3] | (payload[4] << 8));
    flags = payload[9];
    if ((flags & RS_F_SOS) && sos_allowed(p, id, now)) {
        uint8_t up[RS_FRAME_LEN + 1];
        memcpy(up, payload, RS_FRAME_LEN);
        up[RS_FRAME_LEN] = encode_rssi(rssi_dbm);
        send(RS_FPORT_SOS, up, sizeof(up), 1, ctx);
        sent = 1;
    }
    if (rssi_dbm < p->rssi_gate) return sent;
    for (i = 0; i < RS_TABLE_SIZE; i++) {
        if (p->table[i].used) {
            if (memcmp(p->table[i].id, id, 4) == 0) { e = &p->table[i]; break; }
        } else if (free_slot < 0) {
            free_slot = i;
        }
    }
    if (e == NULL) {
        if (free_slot < 0) { p->dropped_full++; return sent; }
        e = &p->table[free_slot];
        memset(e, 0, sizeof(*e));
        e->used = 1;
        memcpy(e->id, id, 4);
        e->rssi = rssi_dbm;
    } else {
        e->rssi = 0.75 * e->rssi + 0.25 * rssi_dbm;
    }
    if (e->hits < 0xFFFF) e->hits++;
    e->last_seen = now;
    e->counter = counter;
    e->flags = flags;
    if (!e->reported && e->hits >= p->hits_required && p->n_arrivals < RS_TABLE_SIZE) {
        uint8_t *a = p->arrivals[p->n_arrivals++];
        memcpy(a, id, 4);
        a[4] = (uint8_t)(counter & 0xff);
        a[5] = (uint8_t)(counter >> 8);
        a[6] = encode_rssi(e->rssi);
        a[7] = flags;
        e->reported = 1;
    }
    return sent;
}

void rs_pole_flush(rs_pole *p, double now, rs_send_fn send, void *ctx) {
    int i, j;
    for (i = 0; i < RS_TABLE_SIZE; i++) {
        rs_entry *e = &p->table[i];
        if (e->used && now - e->last_seen > RS_DEPART_TIMEOUT_S) {
            if (e->reported) {                         /* insert in pseudonym order */
                for (j = p->n_departures; j > 0 && memcmp(p->departures[j - 1], e->id, 4) > 0; j--)
                    memcpy(p->departures[j], p->departures[j - 1], 4);
                memcpy(p->departures[j], e->id, 4);
                p->n_departures++;
            }
            e->used = 0;
        }
    }
    for (i = 0; i < p->n_arrivals; i += RS_CHUNK_TAGS) {
        int n = p->n_arrivals - i < RS_CHUNK_TAGS ? p->n_arrivals - i : RS_CHUNK_TAGS;
        send(RS_FPORT_ARRIVALS, p->arrivals[i], (size_t)n * 8, 0, ctx);
    }
    for (i = 0; i < p->n_departures; i += RS_DEPART_PER_FRAME) {
        int n = p->n_departures - i < RS_DEPART_PER_FRAME ? p->n_departures - i : RS_DEPART_PER_FRAME;
        send(RS_FPORT_DEPARTURES, p->departures[i], (size_t)n * 4, 0, ctx);
    }
    p->n_arrivals = p->n_departures = 0;
}

void rs_pole_heartbeat(rs_pole *p, rs_send_fn send, void *ctx) {
    uint8_t bloom[RS_BLOOM_BYTES] = {0};
    int i, active = 0;
    for (i = 0; i < RS_TABLE_SIZE; i++)
        if (p->table[i].used && p->table[i].reported) { rs_bloom_add(bloom, p->table[i].id); active++; }
    if (active) send(RS_FPORT_HEARTBEAT, bloom, RS_BLOOM_BYTES, 0, ctx);
}
