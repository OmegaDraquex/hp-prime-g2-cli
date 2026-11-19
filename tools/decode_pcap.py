"""Decode USBPcap HID interrupt packets from an HP Prime capture file."""

from __future__ import annotations

import argparse
import struct
import zlib
from pathlib import Path


def parse_pcap_usb_hid(path: Path):
    """Yield (frame_no, rel_ts, direction, payload) for 1024-byte HID interrupt transfers."""
    data = path.read_bytes()
    magic, _, _, _, _, _, linktype = struct.unpack_from("<IHHIIII", data, 0)
    if magic not in (0xA1B2C3D4, 0xA1B23C4D):
        raise ValueError(f"Unsupported pcap magic: 0x{magic:08x} (linktype={linktype})")

    offset = 24
    frame_no = 0
    t0 = None

    while offset + 16 <= len(data):
        ts_sec, ts_usec, incl_len, _orig_len = struct.unpack_from("<IIII", data, offset)
        offset += 16
        pkt = data[offset : offset + incl_len]
        offset += incl_len
        frame_no += 1

        ts = ts_sec + ts_usec * 1e-6
        if t0 is None:
            t0 = ts

        if len(pkt) < 27:
            continue
        hdr_len = struct.unpack_from("<H", pkt, 0)[0]
        if hdr_len < 27 or len(pkt) < hdr_len:
            continue

        # USBPcap pseudoheader:
        # 0:2 headerLen, 2:10 irpId, 10:14 status, 14:16 function, 16:17 info,
        # 17:19 bus, 19:21 device, 21:22 endpoint, 22:23 transfer, 23:27 dataLength
        info = pkt[16]
        endpoint = pkt[21]
        transfer = pkt[22]
        data_len = struct.unpack_from("<I", pkt, 23)[0]

        # transfer == 1 (URB_INTERRUPT), data_len > 0
        if transfer != 1 or data_len == 0:
            continue

        # info bit 0: 0 = FDO->PDO (submit), 1 = PDO->FDO (complete)
        is_in = (endpoint & 0x80) != 0
        if is_in and (info & 1) == 0:
            continue  # skip IN IRP submission (empty buffer)
        if (not is_in) and (info & 1) != 0:
            continue  # skip OUT IRP completion (status only)

        payload = pkt[hdr_len : hdr_len + data_len]
        direction = "IN " if is_in else "OUT"
        yield frame_no, ts - t0, direction, payload


def ascii_preview(b: bytes) -> str:
    return "".join(chr(x) if 32 <= x < 127 else "." for x in b)


def find_zlib_offsets(b: bytes):
    results = []
    for i in range(len(b) - 6):
        if b[i] == 0x78 and b[i + 1] in (0x01, 0x5E, 0x9C, 0xDA):
            try:
                d = zlib.decompressobj()
                out = d.decompress(b[i:])
                out += d.flush()
                results.append((i, len(b) - i - len(d.unused_data), out))
            except Exception:
                pass
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pcap", type=Path)
    ap.add_argument("--max-frames", type=int, default=200)
    ap.add_argument("--bytes", type=int, default=96)
    ap.add_argument("--skip-keepalive", action="store_true")
    args = ap.parse_args()

    shown = 0
    total = 0
    for frame_no, rel_ts, direction, payload in parse_pcap_usb_hid(args.pcap):
        total += 1
        # Trim trailing zeros to see active length
        trimmed = payload.rstrip(b"\x00")
        if args.skip_keepalive and len(trimmed) <= 2 and trimmed[:2] in (b"\x00\xfa", b"\x00\xec"):
            continue
        if shown >= args.max_frames:
            continue
        shown += 1

        head = payload[: args.bytes]
        print(
            f"[{frame_no:4d}] +{rel_ts:7.3f}s {direction} len={len(payload)} active={len(trimmed):4d} "
            f"hex={head.hex(' ')}"
        )
        print(f"       ascii={ascii_preview(head)}")

        # Also check UTF-16LE strings or zlib in trimmed payload
        for z_off, z_len, z_out in find_zlib_offsets(payload):
            print(f"       zlib@{z_off} (comp={z_len} -> raw={len(z_out)}): {ascii_preview(z_out[:120])}")

    print(f"\nTotal HID data frames: {total}, shown: {shown}")


if __name__ == "__main__":
    main()
