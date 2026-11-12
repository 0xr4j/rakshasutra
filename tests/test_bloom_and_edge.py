"""The 64-byte heartbeat and the pole's edge filter (Algorithm 2)."""
import random

from rakshasutra import bloom
from rakshasutra.edge import (FPORT_ARRIVALS, FPORT_DEPARTURES, FPORT_HEARTBEAT, FPORT_SOS, PoleEdgeFilter,
                              decode_arrivals)
from rakshasutra.protocol import F_SOS, build_frame, rolling_id

KEYS = [bytes([i]) * 16 for i in range(1, 80)]


def test_hash_check_values():
    assert bloom.crc16_ccitt(b"123456789") == 0x29B1          # CRC-16/CCITT-FALSE check value
    assert bloom.fnv1a32(b"a") == 0xE40C292C                  # FNV-1a 32-bit reference value
    assert bloom.fnv1a32(b"foobar") == 0xBF9CF968


def test_bloom_has_no_false_negatives():
    ids = [rolling_id(k, 3) for k in KEYS]
    f = bloom.BloomFilter()
    for i in ids:
        f.add(i)
    assert len(bytes(f)) == 64 and all(i in f for i in ids)


def test_bloom_false_positive_rate_matches_the_formula():
    rng = random.Random(1)
    for n in (50, 100, 200):
        hits = trials = 0
        for _ in range(40):
            f = bloom.BloomFilter()
            for _ in range(n):
                f.add(rng.randbytes(4))
            for _ in range(500):
                hits += rng.randbytes(4) in f
                trials += 1
        assert abs(hits / trials - bloom.false_positive_rate(n)) < 0.02, n


def test_bloom_capacity():
    assert bloom.false_positive_rate(bloom.capacity_for(0.05)) <= 0.05 < bloom.false_positive_rate(
        bloom.capacity_for(0.05) + 1)


def frame(i, counter=3, flags=0):
    return build_frame(KEYS[i], counter, flags=flags)


def test_arrival_is_reported_once():
    p = PoleEdgeFilter(hits_required=1)
    for t in range(40):
        assert p.on_advertisement(frame(0), -60.0, t * 0.8) is None
    ups = p.flush(15.0)
    assert [u.fport for u in ups] == [FPORT_ARRIVALS]
    (a,) = decode_arrivals(ups[0].payload)
    assert a["rolling_id"] == rolling_id(KEYS[0], 3) and a["counter"] == 3 and a["rssi_dbm"] == -60
    for t in range(40, 60):
        p.on_advertisement(frame(0), -60.0, t * 0.8)
    assert p.flush(30.0) == []                                # nothing new: no airtime


def test_dense_hub_needs_three_hits():
    p = PoleEdgeFilter(hits_required=3, rssi_gate_dbm=-65.0)
    p.on_advertisement(frame(0), -50.0, 0.0)
    p.on_advertisement(frame(0), -50.0, 0.8)
    assert p.flush(1.0) == []
    p.on_advertisement(frame(0), -50.0, 1.6)
    assert len(p.flush(2.0)) == 1


def test_weak_and_foreign_advertisements_are_ignored():
    p = PoleEdgeFilter(hits_required=1, rssi_gate_dbm=-75.0)
    p.on_advertisement(frame(0), -90.0, 0.0)                  # too weak: someone at the next pole
    p.on_advertisement(b"\x4c\x00" + bytes(13), -40.0, 0.0)   # another company's beacon
    p.on_advertisement(frame(1)[:14], -40.0, 0.0)             # truncated
    assert p.flush(1.0) == [] and p.heartbeat() is None


def test_arrivals_are_chunked_at_25_tags():
    p = PoleEdgeFilter()
    for i in range(60):
        p.on_advertisement(frame(i), -60.0, 0.1 * i)
    ups = p.flush(15.0)
    assert [len(u.payload) for u in ups] == [200, 200, 80]
    assert all(len(u.payload) <= 222 for u in ups)


def test_departure_after_90_seconds_and_heartbeat():
    p = PoleEdgeFilter()
    p.on_advertisement(frame(0), -60.0, 0.0)
    p.on_advertisement(frame(1), -60.0, 0.0)
    p.flush(15.0)
    hb = p.heartbeat()
    assert hb.fport == FPORT_HEARTBEAT and len(hb.payload) == 64
    f = bloom.BloomFilter(hb.payload)
    assert rolling_id(KEYS[0], 3) in f and rolling_id(KEYS[1], 3) in f
    p.on_advertisement(frame(1), -60.0, 80.0)                 # tag 1 is still here
    ups = p.flush(105.0)
    assert [u.fport for u in ups] == [FPORT_DEPARTURES]
    assert ups[0].payload == rolling_id(KEYS[0], 3)
    assert rolling_id(KEYS[0], 3) not in bloom.BloomFilter(p.heartbeat().payload)


def test_sos_goes_out_at_once_even_below_the_rssi_gate():
    p = PoleEdgeFilter(rssi_gate_dbm=-65.0)
    sos = frame(0, flags=F_SOS)
    up = p.on_advertisement(sos, -88.0, 5.0)
    assert up.fport == FPORT_SOS and up.confirmed and up.payload == sos + bytes([88])
    assert p.on_advertisement(sos, -88.0, 5.2) is None        # the same pseudonym is not repeated
    assert p.on_advertisement(sos, -88.0, 96.0) is not None   # but it is after 90 s


def test_sos_rate_limit_of_ten_a_minute():
    p = PoleEdgeFilter()
    sent = sum(p.on_advertisement(frame(i, flags=F_SOS), -50.0, i * 1.0) is not None for i in range(30))
    assert sent == 10
    assert p.on_advertisement(frame(40, flags=F_SOS), -50.0, 61.0) is not None


def test_table_is_bounded():
    p = PoleEdgeFilter(table_size=8)
    for i in range(20):
        p.on_advertisement(frame(i), -60.0, 0.0)
    assert len(p.table) == 8 and p.dropped_full == 12
