"""The signed, pseudonymous BLE advertisement (white paper, Section IV).

Byte layout of the 15-byte manufacturer-specific payload (Table II):

    0-1   Company_ID   0xFF5A, sent low byte first as BLE does (5A FF)
    2     V_type       bits 0-3 protocol version (4), bit 4 role (0 band, 1 parent tag)
    3-4   Slot_Counter little-endian 16-bit counter, +1 every 900 s
    5-8   Rolling_ID   first 4 bytes of AES-CMAC(K_u, 0x01 || counter_le)
    9     F_stat       bit0 SOS, bit1 tether lost, bit2 buzzer/LED on, bit3 low battery
    10    B_mv         supply voltage in 20 mV steps
    11-14 MIC          first 4 bytes of AES-CMAC(K_u, bytes 2..10)

Where the paper leaves an encoding open, this module fixes it and says so:
truncation keeps the leading bytes of the CMAC (RFC 4493 convention), and the
counter enters every CMAC input in the same little-endian form it has on air.
"""
from __future__ import annotations

from dataclasses import dataclass

from .cmac import aes_cmac

COMPANY_ID = 0xFF5A
PROTOCOL_VERSION = 0x4
SLOT_SECONDS = 900
FRAME_LEN = 15
ROLE_BAND, ROLE_PARENT = 0, 1
F_SOS, F_TETHER_LOST, F_BUZZER, F_LOW_BATTERY = 0x01, 0x02, 0x04, 0x08
ADV_INTERVAL_S = 0.8
ADV_INTERVAL_SOS_S = 0.2
WAKE_TOKEN_LEN = 8
CMD_FIND, CMD_SEPARATION = 0x01, 0x02


def _c16(counter: int) -> bytes:
    return (counter & 0xFFFF).to_bytes(2, "little")


def derive_tag_key(master_key: bytes, uid: bytes, system_salt: bytes) -> bytes:
    """Eq. 3: K_u = AES-CMAC(K_master, UID_u || Salt_system)."""
    return aes_cmac(master_key, uid + system_salt)


def rolling_id(tag_key: bytes, counter: int) -> bytes:
    """Eq. 4: the 32-bit pseudonym for one 15-minute slot."""
    return aes_cmac(tag_key, b"\x01" + _c16(counter))[:4]


def mac_address(tag_key: bytes, counter: int) -> bytes:
    """Eq. 5: a BLE static random address for the slot.

    46 bits come from the CMAC; the two most significant bits are set to 1, which is
    what marks a static random address. Returned most significant byte first.
    """
    raw = bytearray(aes_cmac(tag_key, b"\x02" + _c16(counter))[:6])
    raw[0] |= 0xC0
    return bytes(raw)


def encode_battery(volts: float) -> int:
    return max(0, min(255, round(volts / 0.02)))


@dataclass(frozen=True)
class Frame:
    version: int
    role: int
    counter: int
    rolling_id: bytes
    flags: int
    battery_code: int
    mic: bytes
    raw: bytes

    @property
    def sos(self) -> bool:
        return bool(self.flags & F_SOS)

    @property
    def battery_volts(self) -> float:
        return self.battery_code * 0.02


def build_frame(tag_key: bytes, counter: int, flags: int = 0, battery_volts: float = 3.0,
                role: int = ROLE_BAND) -> bytes:
    """The 15 bytes a wearable broadcasts in slot `counter`."""
    body = bytes([PROTOCOL_VERSION | (role & 1) << 4]) + _c16(counter) + rolling_id(tag_key, counter) \
        + bytes([flags & 0xFF, encode_battery(battery_volts)])
    mic = aes_cmac(tag_key, body)[:4]
    return COMPANY_ID.to_bytes(2, "little") + body + mic


def parse_frame(raw: bytes) -> Frame:
    """Split a 15-byte payload into fields. Raises ValueError if it is not a Rakshasutra frame."""
    if len(raw) != FRAME_LEN:
        raise ValueError(f"frame must be {FRAME_LEN} bytes, got {len(raw)}")
    if int.from_bytes(raw[0:2], "little") != COMPANY_ID:
        raise ValueError("wrong Company_ID")
    if raw[2] & 0x0F != PROTOCOL_VERSION:
        raise ValueError("unknown protocol version")
    return Frame(version=raw[2] & 0x0F, role=(raw[2] >> 4) & 1, counter=int.from_bytes(raw[3:5], "little"),
                 rolling_id=bytes(raw[5:9]), flags=raw[9], battery_code=raw[10], mic=bytes(raw[11:15]),
                 raw=bytes(raw))


def verify_frame(tag_key: bytes, raw: bytes) -> bool:
    """True if the pseudonym and the MIC both match this tag key."""
    try:
        f = parse_frame(raw)
    except ValueError:
        return False
    return f.rolling_id == rolling_id(tag_key, f.counter) and f.mic == aes_cmac(tag_key, raw[2:11])[:4]


def wake_token(tag_key: bytes, counter: int, command: int = CMD_FIND) -> bytes:
    """The 8-byte Find-Mode wake token a pole broadcasts to one wearable.

    The paper fixes only the sizes (8 bytes in total, 24 bits of authentication). The
    layout chosen here is Rolling_ID (4) || command (1) || first 3 bytes of
    AES-CMAC(K_u, 0x03 || counter_le || command).
    """
    tag = aes_cmac(tag_key, b"\x03" + _c16(counter) + bytes([command]))[:3]
    return rolling_id(tag_key, counter) + bytes([command]) + tag


def verify_wake_token(tag_key: bytes, counter: int, token: bytes) -> bool:
    """What the wearable checks before it sounds its buzzer. Accepts the current slot only."""
    return len(token) == WAKE_TOKEN_LEN and token == wake_token(tag_key, counter, token[4])


def tether_table(tag_key: bytes, start_counter: int, slots: int = 96) -> list[bytes]:
    """The child band's next pseudonyms, written into the parent tag at pairing (96 slots = 24 h)."""
    return [rolling_id(tag_key, (start_counter + k) & 0xFFFF) for k in range(slots)]
