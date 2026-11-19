"""Encoding and decoding for HP Prime 0xF7 objects (PPL programs and backups)."""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass

from hpprime.crc import compute_v3_object_crc, verify_f7_raw

TYPE_SETTINGS = 0x00
TYPE_APP = 0x02
TYPE_LIST = 0x03
TYPE_MATRIX = 0x04
TYPE_PROGRAM = 0x06
TYPE_CUSTOM = 0x0B

FILE_TYPE_NAMES: dict[int, str] = {
    TYPE_SETTINGS: "Settings",
    TYPE_APP: "App",
    TYPE_LIST: "List",
    TYPE_MATRIX: "Matrix",
    TYPE_PROGRAM: "Program",
    TYPE_CUSTOM: "Custom",
}

DEFAULT_COMPRESS_THRESHOLD = 800


@dataclass(slots=True)
class PrimeObject:
    """Decoded 0xF7 object transferred to or from an HP Prime calculator."""

    file_type: int
    name: str
    raw: bytes
    body: bytes
    crc_ok: bool
    compressed: bool

    @property
    def type_name(self) -> str:
        return FILE_TYPE_NAMES.get(self.file_type, f"0x{self.file_type:02x}")


def _build_raw_object(cmd: int, file_type: int, name: str, body: bytes = b"") -> bytes:
    """Build a raw V3 object payload with its embedded CRC-16 header."""
    if not name:
        raise ValueError("Object name must be non-empty")

    name_bytes = name.encode("utf-16le")
    if len(name_bytes) > 255:
        raise ValueError(f"Object name too long ({len(name_bytes)} UTF-16LE bytes, max 255)")

    raw_stub = bytes([file_type, len(name_bytes), 0, 0]) + name_bytes + body
    crc = compute_v3_object_crc(cmd, raw_stub)
    return bytes([file_type, len(name_bytes)]) + struct.pack("<H", crc) + name_bytes + body


def encode_ppl_program(
    name: str,
    source: str,
    *,
    compress: bool | None = None,
) -> bytes:
    """Encode a PPL program into a complete 0xF7 V3 wire message."""
    clean_source = source.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    body_bytes = clean_source.encode("utf-16le") + b"\x00\x00"
    raw = _build_raw_object(0xF7, TYPE_PROGRAM, name, body_bytes)

    use_compress = (len(raw) > DEFAULT_COMPRESS_THRESHOLD) if compress is None else compress
    if use_compress:
        payload = struct.pack("<I", len(raw)) + zlib.compress(raw, level=1)
    else:
        payload = raw

    return b"\xf7\x03" + struct.pack(">I", len(payload)) + payload


def encode_delete_object(name: str, *, file_type: int = TYPE_PROGRAM) -> bytes:
    """Encode an 0xEB delete request for an object on the calculator."""
    raw = _build_raw_object(0xEB, file_type, name)
    return b"\xeb\x03" + struct.pack(">I", len(raw)) + raw


def decode_f7_message(msg: bytes) -> PrimeObject:
    """Decode a reassembled 0xF7 V3 wire message into a PrimeObject."""
    if len(msg) < 10 or msg[0] != 0xF7:
        raise ValueError(f"Not a valid 0xF7 message (len={len(msg)}, cmd=0x{msg[0]:02x})")

    compressed = False
    raw = msg[6:]

    if (
        len(msg) >= 12
        and msg[10] == 0x78
        and msg[11] in (0x01, 0x5E, 0x9C, 0xDA)
    ):
        expected_raw_len = struct.unpack_from("<I", msg, 6)[0]
        if expected_raw_len > 0:
            try:
                decompressed = zlib.decompress(msg[10:])
                if len(decompressed) == expected_raw_len:
                    raw = decompressed
                    compressed = True
            except zlib.error:
                pass

    if len(raw) < 4:
        raise ValueError(f"0xF7 payload too short ({len(raw)} bytes)")

    file_type = raw[0]
    name_len = raw[1]
    if 4 + name_len > len(raw):
        raise ValueError(f"0xF7 name_len={name_len} exceeds raw length {len(raw)}")

    name = raw[4 : 4 + name_len].decode("utf-16le", errors="replace")
    body = raw[4 + name_len :]
    crc_ok = verify_f7_raw(raw)

    return PrimeObject(
        file_type=file_type,
        name=name,
        raw=raw,
        body=body,
        crc_ok=crc_ok,
        compressed=compressed,
    )


def decode_ppl_source(obj: PrimeObject) -> str:
    """Extract UTF-16LE PPL source code from a program PrimeObject."""
    if obj.file_type != TYPE_PROGRAM:
        raise ValueError(f"Object {obj.name!r} is type {obj.type_name}, not Program")
    data = obj.body
    if len(data) % 2 == 1:
        data = data[:-1]
    text = data.decode("utf-16le", errors="replace")
    return text.rstrip("\x00")
