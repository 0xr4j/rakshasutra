"""The signed advertisement: RFC and FIPS vectors, frame layout, and what must be rejected."""
import pytest

from rakshasutra import protocol as pr
from rakshasutra.cmac import aes128_encrypt_block, aes_cmac

K = bytes.fromhex("2b7e151628aed2a6abf7158809cf4f3c")
M = bytes.fromhex("6bc1bee22e409f96e93d7e117393172aae2d8a571e03ac9c9eb76fac45af8e51"
                  "30c81c46a35ce411e5fbc1191a0a52eff69f2445df4f9b17ad2b417be66c3710")
TAG = bytes.fromhex("000102030405060708090a0b0c0d0e0f")


def test_aes128_fips197_vector():
    out = aes128_encrypt_block(TAG, bytes.fromhex("00112233445566778899aabbccddeeff"))
    assert out.hex() == "69c4e0d86a7b0430d8cdb78070b4c55a"


@pytest.mark.parametrize("length,expected", [
    (0, "bb1d6929e95937287fa37d129b756746"), (16, "070a16b46b4d4144f79bdd9dd04a287c"),
    (40, "dfa66747de9ae63030ca32611497c827"), (64, "51f0bebf7e3b9d92fc49741779363cfe")])
def test_aes_cmac_rfc4493_vectors(length, expected):
    assert aes_cmac(K, M[:length]).hex() == expected


def test_cmac_matches_an_independent_library():
    crypto = pytest.importorskip("cryptography.hazmat.primitives.cmac")
    from cryptography.hazmat.primitives.ciphers import algorithms
    for n in (0, 1, 3, 9, 15, 16, 17, 31, 32, 33, 100):
        c = crypto.CMAC(algorithms.AES(K))
        c.update(M[:n] if n <= len(M) else M + M[:n - len(M)])
        assert c.finalize() == aes_cmac(K, M[:n] if n <= len(M) else M + M[:n - len(M)])


def test_frame_layout_matches_table_ii():
    raw = pr.build_frame(TAG, counter=0x1234, flags=pr.F_SOS, battery_volts=3.0)
    assert len(raw) == 15
    assert raw[0:2] == b"\x5a\xff"                 # Company_ID 0xFF5A, low byte first
    assert raw[2] == 0x04                          # version 4, band
    assert raw[3:5] == b"\x34\x12"                 # little-endian counter
    assert raw[5:9] == aes_cmac(TAG, b"\x01\x34\x12")[:4]
    assert raw[9] == 0x01 and raw[10] == 150       # SOS; 3.00 V in 20 mV steps
    assert raw[11:15] == aes_cmac(TAG, raw[2:11])[:4]
    assert raw.hex() == pr.build_frame(TAG, 0x1234, pr.F_SOS, 3.0).hex()


def test_known_frame_is_pinned():
    assert pr.build_frame(TAG, 17, pr.F_SOS, 3.0).hex() == "5aff0411003c34fdc901968c83e42f"
    assert pr.mac_address(TAG, 17).hex() == "d41b8a54a8dc"


def test_parent_tag_role_bit():
    assert pr.parse_frame(pr.build_frame(TAG, 5, role=pr.ROLE_PARENT)).role == 1
    assert pr.parse_frame(pr.build_frame(TAG, 5)).role == 0


def test_verify_accepts_own_frame_and_rejects_any_changed_bit():
    raw = pr.build_frame(TAG, 77, flags=0, battery_volts=2.9)
    assert pr.verify_frame(TAG, raw)
    for byte in range(2, 15):
        for bit in range(8):
            bad = bytearray(raw)
            bad[byte] ^= 1 << bit
            assert not pr.verify_frame(TAG, bytes(bad)), (byte, bit)


def test_verify_rejects_another_key_and_wrong_lengths():
    raw = pr.build_frame(TAG, 77)
    assert not pr.verify_frame(K, raw)
    assert not pr.verify_frame(TAG, raw[:-1])
    assert not pr.verify_frame(TAG, raw + b"\x00")


def test_pseudonym_and_address_change_every_slot():
    ids = {pr.rolling_id(TAG, c) for c in range(2000)}
    macs = {pr.mac_address(TAG, c) for c in range(2000)}
    assert len(ids) == 2000 and len(macs) == 2000
    assert all(m[0] & 0xC0 == 0xC0 for m in macs)   # static random address


def test_pseudonym_bits_look_uniform():
    ones = sum(bin(int.from_bytes(pr.rolling_id(TAG, c), "big")).count("1") for c in range(4000))
    assert abs(ones / (4000 * 32) - 0.5) < 0.01


def test_tag_keys_differ_per_wearable():
    master, salt = bytes(range(16)), b"salt"
    keys = {pr.derive_tag_key(master, f"band-{i}".encode(), salt) for i in range(500)}
    assert len(keys) == 500


def test_wake_token_is_bound_to_key_slot_and_command():
    t = pr.wake_token(TAG, 9, pr.CMD_FIND)
    assert len(t) == 8 and t[:4] == pr.rolling_id(TAG, 9)
    assert pr.verify_wake_token(TAG, 9, t)
    assert not pr.verify_wake_token(TAG, 10, t)       # replayed in a later slot
    assert not pr.verify_wake_token(K, 9, t)
    forged = t[:4] + bytes([pr.CMD_SEPARATION]) + t[5:]
    assert not pr.verify_wake_token(TAG, 9, forged)


def test_tether_table_covers_24_hours():
    table = pr.tether_table(TAG, 65530)
    assert len(table) == 96 and len(b"".join(table)) == 384
    assert table[10] == pr.rolling_id(TAG, 4)         # the counter wraps at 65536
