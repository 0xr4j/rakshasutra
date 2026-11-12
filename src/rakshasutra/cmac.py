"""AES-128 and AES-CMAC (RFC 4493) in plain Python.

The wearable, the pairing pad and the server must agree on these bytes exactly, so the
reference implementation has no dependencies and is checked against the RFC 4493 test
vectors (tests/test_crypto.py) and against the C core in firmware/.

This is a reference for correctness, not a hardened implementation: it is not
constant-time and must not be used where an attacker can measure timing.
"""
from __future__ import annotations

_SBOX = bytes.fromhex(
    "637c777bf26b6fc53001672bfed7ab76ca82c97dfa5947f0add4a2af9ca472c0"
    "b7fd9326363ff7cc34a5e5f171d8311504c723c31896059a071280e2eb27b275"
    "09832c1a1b6e5aa0523bd6b329e32f8453d100ed20fcb15b6acbbe394a4c58cf"
    "d0efaafb434d338545f9027f503c9fa851a3408f929d38f5bcb6da2110fff3d2"
    "cd0c13ec5f974417c4a77e3d645d197360814fdc222a908846eeb814de5e0bdb"
    "e0323a0a4906245cc2d3ac629195e479e7c8376d8dd54ea96c56f4ea657aae08"
    "ba78252e1ca6b4c6e8dd741f4bbd8b8a703eb5664803f60e613557b986c11d9e"
    "e1f8981169d98e949b1e87e9ce5528df8ca1890dbfe6426841992d0fb054bb16"
)
_RCON = (0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36)


def _xtime(a: int) -> int:
    a <<= 1
    return (a ^ 0x11B) & 0xFF if a & 0x100 else a


def _expand_key(key: bytes) -> list[bytes]:
    w = [key[i:i + 4] for i in range(0, 16, 4)]
    for i in range(4, 44):
        t = w[i - 1]
        if i % 4 == 0:
            t = bytes((_SBOX[t[1]] ^ _RCON[i // 4 - 1], _SBOX[t[2]], _SBOX[t[3]], _SBOX[t[0]]))
        w.append(bytes(a ^ b for a, b in zip(w[i - 4], t)))
    return [b"".join(w[r * 4:r * 4 + 4]) for r in range(11)]


def aes128_encrypt_block(key: bytes, block: bytes) -> bytes:
    """Encrypt one 16-byte block with AES-128 (FIPS 197)."""
    if len(key) != 16 or len(block) != 16:
        raise ValueError("AES-128 needs a 16-byte key and a 16-byte block")
    rk = _expand_key(key)
    s = [b ^ k for b, k in zip(block, rk[0])]
    for rnd in range(1, 11):
        s = [_SBOX[b] for b in s]
        # ShiftRows: state is column-major, s[4*c + r]
        s = [s[(4 * (c + r) + r) % 16] for c in range(4) for r in range(4)]
        if rnd != 10:
            m = []
            for c in range(4):
                a0, a1, a2, a3 = s[4 * c:4 * c + 4]
                m += [
                    _xtime(a0) ^ _xtime(a1) ^ a1 ^ a2 ^ a3,
                    a0 ^ _xtime(a1) ^ _xtime(a2) ^ a2 ^ a3,
                    a0 ^ a1 ^ _xtime(a2) ^ _xtime(a3) ^ a3,
                    _xtime(a0) ^ a0 ^ a1 ^ a2 ^ _xtime(a3),
                ]
            s = m
        s = [b ^ k for b, k in zip(s, rk[rnd])]
    return bytes(s)


def _dbl(block: bytes) -> bytes:
    n = int.from_bytes(block, "big") << 1
    if n >> 128:
        n = (n & ((1 << 128) - 1)) ^ 0x87
    return n.to_bytes(16, "big")


def aes_cmac(key: bytes, message: bytes) -> bytes:
    """AES-CMAC of `message` under a 16-byte key. Returns the full 16-byte tag."""
    k1 = _dbl(aes128_encrypt_block(key, bytes(16)))
    k2 = _dbl(k1)
    n = max(1, -(-len(message) // 16))
    complete = len(message) > 0 and len(message) % 16 == 0
    last = message[(n - 1) * 16:]
    if complete:
        last = bytes(a ^ b for a, b in zip(last, k1))
    else:
        last = last + b"\x80" + bytes(15 - len(last))
        last = bytes(a ^ b for a, b in zip(last, k2))
    x = bytes(16)
    for i in range(n - 1):
        x = aes128_encrypt_block(key, bytes(a ^ b for a, b in zip(x, message[i * 16:i * 16 + 16])))
    return aes128_encrypt_block(key, bytes(a ^ b for a, b in zip(x, last)))
