"""Offline unit and capture-regression tests for the HP Prime G2 protocol."""

from __future__ import annotations

from pathlib import Path
import struct
import unittest

from hpprime.files import (
    TYPE_PROGRAM,
    decode_f7_message,
    decode_ppl_source,
    encode_ppl_program,
)
from hpprime.protocol import chunk_v3_message
from tools.decode_pcap import parse_pcap_usb_hid

ROOT = Path(__file__).resolve().parent.parent
CAPTURES = ROOT / "captures"


def _reassemble_v3_messages(pcap_path: Path) -> dict[int, bytes]:
    """Reassemble V3 messages keyed by the starting pcap frame number."""
    out: dict[int, bytes] = {}
    cur = None
    for fno, _ts, _direction, pkt in parse_pcap_usb_hid(pcap_path):
        if pkt[:3] in (b"\xfe\x01\xff", b"\xfe\x01\x01"):
            continue
        if pkt[0] == 0x01:
            _seq, length = struct.unpack_from("<II", pkt, 1)
            body = bytearray(pkt[9:])
            if len(body) >= length:
                out[fno] = bytes(body[:length])
                cur = None
            else:
                cur = [fno, length, body]
        elif cur is not None and pkt[0] >= 0x02:
            cur[2].extend(pkt[1:])
            if len(cur[2]) >= cur[1]:
                out[cur[0]] = bytes(cur[2][: cur[1]])
                cur = None
    return out


class TestProtocolOffline(unittest.TestCase):
    def test_known_wire_vectors(self) -> None:
        vectors = [
            (
                "new program",
                "",
                "f7 03 00 00 00 1c 06 16 c4 36 "
                "6e 00 65 00 77 00 20 00 70 00 72 00 6f 00 67 00 72 00 61 00 6d 00 00 00",
            ),
            (
                "T1",
                "EXPORT T1() BEGIN 1+1; END;",
                "f7 03 00 00 00 40 06 04 4c d5 "
                "54 00 31 00 45 00 58 00 50 00 4f 00 52 00 54 00 20 00 54 00 31 00 28 00 29 00 "
                "20 00 42 00 45 00 47 00 49 00 4e 00 20 00 31 00 2b 00 31 00 3b 00 20 00 45 00 "
                "4e 00 44 00 3b 00 00 00",
            ),
            (
                "T1",
                "EXPORT T1() BEGIN 1+2; END;",
                "f7 03 00 00 00 40 06 04 01 3d "
                "54 00 31 00 45 00 58 00 50 00 4f 00 52 00 54 00 20 00 54 00 31 00 28 00 29 00 "
                "20 00 42 00 45 00 47 00 49 00 4e 00 20 00 31 00 2b 00 32 00 3b 00 20 00 45 00 "
                "4e 00 44 00 3b 00 00 00",
            ),
            (
                "T1",
                "EXPORT T1() BEGIN 1+3; END;",
                "f7 03 00 00 00 40 06 04 25 95 "
                "54 00 31 00 45 00 58 00 50 00 4f 00 52 00 54 00 20 00 54 00 31 00 28 00 29 00 "
                "20 00 42 00 45 00 47 00 49 00 4e 00 20 00 31 00 2b 00 33 00 3b 00 20 00 45 00 "
                "4e 00 44 00 3b 00 00 00",
            ),
        ]
        for name, src, expected_hex in vectors:
            with self.subTest(name=name, src=src):
                encoded = encode_ppl_program(name, src, compress=False)
                self.assertEqual(encoded, bytes.fromhex(expected_hex))
                decoded = decode_f7_message(encoded)
                self.assertTrue(decoded.crc_ok)
                self.assertEqual(decoded.name, name)
                self.assertEqual(decode_ppl_source(decoded), src)

    @unittest.skipUnless(
        (CAPTURES / "01_connect_and_send.pcap").exists(),
        "local USBPcap capture not present",
    )
    def test_all_0xf7_crcs_in_capture_01(self) -> None:
        msgs = _reassemble_v3_messages(CAPTURES / "01_connect_and_send.pcap")
        f7_objs = [decode_f7_message(m) for m in msgs.values() if m[0] == 0xF7]
        self.assertEqual(len(f7_objs), 46)
        for obj in f7_objs:
            self.assertTrue(obj.crc_ok, f"CRC mismatch for {obj.name!r}")

    @unittest.skipUnless(
        (CAPTURES / "01_connect_and_send.pcap").exists(),
        "local USBPcap capture not present",
    )
    def test_exact_match_new_program_frame_971(self) -> None:
        msgs = _reassemble_v3_messages(CAPTURES / "01_connect_and_send.pcap")
        encoded = encode_ppl_program("new program", "", compress=False)
        self.assertEqual(encoded, msgs[971])

    @unittest.skipUnless(
        (CAPTURES / "02_send_diff.pcap").exists(),
        "local USBPcap capture not present",
    )
    def test_exact_match_diff_sends_capture_02(self) -> None:
        msgs = _reassemble_v3_messages(CAPTURES / "02_send_diff.pcap")
        expected = [
            (1029, "EXPORT T1() BEGIN 1+1; END;"),
            (1203, "EXPORT T1() BEGIN 1+2; END;"),
            (1311, "EXPORT T1() BEGIN 1+3; END;"),
        ]
        for frame_no, src in expected:
            with self.subTest(frame=frame_no):
                encoded = encode_ppl_program("T1", src, compress=False)
                self.assertEqual(encoded, msgs[frame_no])

    def test_compressed_round_trip(self) -> None:
        src = 'EXPORT BIGTEST()\nBEGIN\n  // line\n  PRINT("Hello G2");\nEND;\n' * 30
        msg = encode_ppl_program("BIGTEST", src, compress=True)
        obj = decode_f7_message(msg)
        self.assertTrue(obj.compressed)
        self.assertTrue(obj.crc_ok)
        self.assertEqual(obj.file_type, TYPE_PROGRAM)
        self.assertEqual(obj.name, "BIGTEST")
        self.assertEqual(decode_ppl_source(obj), src)

    def test_v3_chunking_sizes(self) -> None:
        short_chunks = chunk_v3_message(1, b"abc")
        self.assertEqual(len(short_chunks), 1)
        self.assertEqual(len(short_chunks[0]), 1024)
        self.assertEqual(short_chunks[0][0], 0x01)

        big_payload = b"X" * 2500
        big_chunks = chunk_v3_message(7, big_payload)
        self.assertEqual(len(big_chunks), 3)
        self.assertTrue(all(len(c) == 1024 for c in big_chunks))
        self.assertEqual([c[0] for c in big_chunks], [1, 2, 3])
        rebuilt = big_chunks[0][9:] + big_chunks[1][1:] + big_chunks[2][1:]
        self.assertEqual(rebuilt[:2500], big_payload)


if __name__ == "__main__":
    unittest.main()
