"""CRC-16/XMODEM checksum utilities for HP Prime 0xF7 object headers."""

from __future__ import annotations

import struct


def _build_crc16_table(poly: int = 0x1021) -> tuple[int, ...]:
    table = []
    for byte in range(256):
        crc = byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ poly) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
        table.append(crc)
    return tuple(table)


_CRC16_XMODEM_TABLE = _build_crc16_table()


def crc16_xmodem(data: bytes) -> int:
    """Compute CRC-16/XMODEM (poly=0x1021, init=0x0000, xorout=0x0000)."""
    crc = 0
    table = _CRC16_XMODEM_TABLE
    for b in data:
        crc = ((crc << 8) ^ table[((crc >> 8) ^ b) & 0xFF]) & 0xFFFF
    return crc


def compute_f7_crc(raw: bytes) -> int:
    """Compute the 16-bit header CRC for an uncompressed 0xF7 payload.

    HP Connectivity Kit hashes the 6-byte 0xF7 V3 frame header (with the
    uncompressed payload length in big-endian) followed by the raw object
    with bytes [2:4] zeroed out.
    """
    if len(raw) < 4:
        raise ValueError(f"0xF7 raw payload too short ({len(raw)} bytes)")
    buf = b"\xf7\x03" + struct.pack(">I", len(raw)) + raw[:2] + b"\x00\x00" + raw[4:]
    return crc16_xmodem(buf)


def verify_f7_raw(raw: bytes) -> bool:
    """Return True if the embedded little-endian CRC at raw[2:4] matches."""
    if len(raw) < 4:
        return False
    expected = struct.unpack_from("<H", raw, 2)[0]
    return compute_f7_crc(raw) == expected
