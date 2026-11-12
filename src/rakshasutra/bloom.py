"""The fixed 64-byte presence heartbeat (white paper, Algorithm 2, lines 18-24).

A pole summarises every wearable it currently holds as a 512-bit Bloom filter with
three probes, bit_j = (CRC16(id) + j * FNV1a(id)) mod 512 for j = 0, 1, 2
(Kirsch and Mitzenmacher double hashing). CRC16 is CRC-16/CCITT-FALSE and FNV1a is
the 32-bit variant, both over the four Rolling_ID bytes as sent.
"""
from __future__ import annotations

import math

BITS = 512
BYTES = BITS // 8
PROBES = 3


def crc16_ccitt(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def fnv1a32(data: bytes) -> int:
    h = 0x811C9DC5
    for b in data:
        h = ((h ^ b) * 0x01000193) & 0xFFFFFFFF
    return h


def bit_indices(rolling_id: bytes) -> tuple[int, int, int]:
    h1, h2 = crc16_ccitt(rolling_id), fnv1a32(rolling_id)
    return tuple((h1 + j * h2) % BITS for j in range(PROBES))


class BloomFilter:
    """512 bits, three probes. Bit i lives in byte i // 8 at mask 1 << (i % 8)."""

    def __init__(self, data: bytes | None = None):
        self.data = bytearray(data) if data is not None else bytearray(BYTES)
        if len(self.data) != BYTES:
            raise ValueError(f"a heartbeat is {BYTES} bytes")

    def add(self, rolling_id: bytes) -> None:
        for i in bit_indices(rolling_id):
            self.data[i >> 3] |= 1 << (i & 7)

    def __contains__(self, rolling_id: bytes) -> bool:
        return all(self.data[i >> 3] & (1 << (i & 7)) for i in bit_indices(rolling_id))

    def bits_set(self) -> int:
        return sum(bin(b).count("1") for b in self.data)

    def __bytes__(self) -> bytes:
        return bytes(self.data)


def false_positive_rate(tags: int, bits: int = BITS, probes: int = PROBES) -> float:
    """Chance that a wearable which is not at the pole still tests as present."""
    return (1.0 - math.exp(-probes * tags / bits)) ** probes


def capacity_for(rate: float, bits: int = BITS, probes: int = PROBES) -> int:
    """Largest number of wearables a filter can hold with a false-positive rate at or below `rate`."""
    return int(-bits / probes * math.log(1.0 - rate ** (1.0 / probes)))
