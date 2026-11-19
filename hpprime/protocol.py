"""USB HID V3 transport and session protocol for the HP Prime G2."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import struct
import time

import hid

from hpprime.files import PrimeObject, decode_f7_message, encode_ppl_program


@dataclass(slots=True)
class DeviceInfo:
    """Device identification metadata returned by the 0xFA ready/info probe."""

    protocol_version: int
    device_id: str
    firmware_version: str
    serial_number: str
    build_number: int


def chunk_v3_message(seq: int, payload: bytes) -> list[bytes]:
    """Split a V3 protocol message into 1024-byte HID interrupt reports."""
    first_body = payload[:1015]
    first = (
        b"\x01"
        + struct.pack("<II", seq, len(payload))
        + first_body
    ).ljust(HPPrimeG2.REPORT_SIZE, b"\x00")
    chunks = [first]

    offset = 1015
    chunk_id = 2
    while offset < len(payload):
        if chunk_id > 253:
            raise ValueError(
                f"Message too large ({len(payload)} bytes exceeds 253 HID chunks)"
            )
        part = payload[offset : offset + 1023]
        chunks.append((bytes([chunk_id]) + part).ljust(HPPrimeG2.REPORT_SIZE, b"\x00"))
        offset += 1023
        chunk_id += 1

    return chunks


class HPPrimeG2:
    """Context-managed USB HID client for the HP Prime G2 (VID=0x03F0, PID=0x2441)."""

    VID = 0x03F0
    PID = 0x2441
    REPORT_SIZE = 1024

    def __init__(self) -> None:
        self._dev: hid.device | None = None
        self._host_seq = 0
        self._last_calc_seq = 0
        self._rx_queue: deque[bytes] = deque()

    def __enter__(self) -> HPPrimeG2:
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def open(self) -> None:
        """Open the USB HID handle to the connected HP Prime G2."""
        devices = hid.enumerate(self.VID, self.PID)
        if not devices:
            raise RuntimeError(
                "HP Prime G2 (VID=0x03F0, PID=0x2441) not found on USB HID. "
                "Check the USB cable and make sure the calculator is awake."
            )

        dev = hid.device()
        try:
            dev.open_path(devices[0]["path"])
        except OSError as exc:
            raise RuntimeError(
                f"Unable to open HP Prime G2 HID device: {exc}. "
                "Make sure HP Connectivity Kit is closed."
            ) from exc
        self._dev = dev
        self._rx_queue.clear()

    def close(self) -> None:
        """Close the HID handle if open."""
        if self._dev is not None:
            try:
                self._dev.close()
            finally:
                self._dev = None

    def _require_dev(self) -> hid.device:
        if self._dev is None:
            raise RuntimeError("HID device is not open")
        return self._dev

    def _write_report(self, report: bytes) -> None:
        if len(report) != self.REPORT_SIZE:
            raise ValueError(f"Expected {self.REPORT_SIZE}-byte report, got {len(report)}")
        dev = self._require_dev()
        # Windows hidapi expects a leading Report ID byte (0x00) for devices without Report IDs.
        written = dev.write(b"\x00" + report)
        if written <= 0:
            raise OSError(f"HID write failed (returned {written})")

    def _read_report(self, timeout_ms: int = 3000) -> bytes:
        dev = self._require_dev()
        data = dev.read(self.REPORT_SIZE, timeout_ms)
        if not data:
            raise TimeoutError(f"Timed out after {timeout_ms} ms waiting for HID packet")
        return bytes(data)

    def _drain_input(self) -> None:
        dev = self._require_dev()
        for _ in range(16):
            data = dev.read(self.REPORT_SIZE, 20)
            if not data:
                break

    def _next_packet(self, timeout_ms: int = 3000) -> bytes:
        """Return the next non-heartbeat HID report within timeout_ms."""
        if self._rx_queue:
            pkt = self._rx_queue.popleft()
            if pkt[:3] != b"\xfe\x01\xff":
                return pkt

        deadline = time.monotonic() + (timeout_ms / 1000.0)
        while True:
            remaining_ms = max(1, int((deadline - time.monotonic()) * 1000))
            pkt = self._read_report(remaining_ms)
            if pkt[:3] == b"\xfe\x01\xff":
                if time.monotonic() >= deadline:
                    raise TimeoutError("Timed out waiting for non-heartbeat HID packet")
                continue
            return pkt

    def get_info(self, timeout_ms: int = 3000) -> DeviceInfo:
        """Send 0xFA ready/info probe and parse device metadata."""
        self._drain_input()
        probe = b"\x00\xfa".ljust(self.REPORT_SIZE, b"\x00")
        self._write_report(probe)

        deadline = time.monotonic() + (timeout_ms / 1000.0)
        while True:
            remaining_ms = max(1, int((deadline - time.monotonic()) * 1000))
            pkt = self._next_packet(remaining_ms)
            if pkt[:2] == b"\x00\xfa":
                break
            if time.monotonic() >= deadline:
                raise TimeoutError("Timed out waiting for 0xFA info reply")

        proto_ver = pkt[2]
        device_id = pkt[7:71].decode("utf-16le", errors="replace").split("\x00", 1)[0]
        build_number = struct.unpack_from("<I", pkt, 0x4F)[0]
        firmware_version = pkt[0x53:0x63].split(b"\x00", 1)[0].decode("ascii", errors="replace")
        serial_number = pkt[0x63:0x73].split(b"\x00", 1)[0].decode("ascii", errors="replace")
        return DeviceInfo(
            protocol_version=proto_ver,
            device_id=device_id,
            firmware_version=firmware_version,
            serial_number=serial_number,
            build_number=build_number,
        )

    def connect(self) -> DeviceInfo:
        """Perform 0xFA probe, 0xEC transport reset, and 0xFD Protocol V3 negotiation."""
        info = self.get_info()
        self._write_report(b"\xff\xec".ljust(self.REPORT_SIZE, b"\x00"))
        time.sleep(0.03)

        self._host_seq = 0
        self._last_calc_seq = 0
        self._rx_queue.clear()

        negotiate = b"\xfd\x01\x00\x00\x00\x01\x03"
        self.send_message(negotiate)
        reply = self.recv_message()
        if len(reply) >= 2 and reply[0] == 0xFD and reply[1] != 0x03:
            self.send_message(negotiate)
            reply = self.recv_message()

        if len(reply) < 2 or reply[0] != 0xFD or reply[1] != 0x03:
            raise RuntimeError(f"Protocol V3 negotiation failed: {reply.hex(' ')}")

        return info

    def _send_ack(self, acked_seq: int, num_chunks: int) -> None:
        capacity = 1015 + (num_chunks - 1) * 1023
        pkt = (
            b"\xfe\x01"
            + struct.pack("<HII", num_chunks, capacity, acked_seq)
            + (b"\x00" * 4)
            + (b"\xff" * 8)
            + (b"\x00" * 8)
            + struct.pack("<I", self._host_seq)
        ).ljust(self.REPORT_SIZE, b"\x00")
        self._write_report(pkt)

    def send_message(self, payload: bytes, timeout_ms: int = 5000) -> None:
        """Send a V3 message and wait for its 0xFE 0x01 transport ACK."""
        self._host_seq += 1
        seq = self._host_seq
        for chunk in chunk_v3_message(seq, payload):
            self._write_report(chunk)

        deadline = time.monotonic() + (timeout_ms / 1000.0)
        deferred: list[bytes] = []
        try:
            while True:
                remaining_ms = max(1, int((deadline - time.monotonic()) * 1000))
                pkt = self._next_packet(remaining_ms)
                if pkt[:2] == b"\xfe\x01":
                    acked_seq = struct.unpack_from("<I", pkt, 8)[0]
                    if acked_seq == seq:
                        return
                    continue
                deferred.append(pkt)
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"Timed out waiting for ACK of seq={seq}")
        finally:
            for item in reversed(deferred):
                self._rx_queue.appendleft(item)

    def recv_message(self, timeout_ms: int = 5000) -> bytes:
        """Receive a complete V3 message from the calculator and ACK it."""
        deadline = time.monotonic() + (timeout_ms / 1000.0)
        while True:
            remaining_ms = max(1, int((deadline - time.monotonic()) * 1000))
            pkt = self._next_packet(remaining_ms)
            if pkt[0] == 0x01:
                break
            if pkt[:2] == b"\xfe\x01":
                continue
            if time.monotonic() >= deadline:
                raise TimeoutError("Timed out waiting for V3 message start chunk")

        calc_seq, msg_len = struct.unpack_from("<II", pkt, 1)
        self._last_calc_seq = calc_seq
        buf = bytearray(pkt[9:])
        num_chunks = 1 if msg_len <= 1015 else 1 + ((msg_len - 1015 + 1022) // 1023)

        for expected_chunk_id in range(2, num_chunks + 1):
            remaining_ms = max(1, int((deadline - time.monotonic()) * 1000))
            cont = self._next_packet(remaining_ms)
            if cont[0] != expected_chunk_id:
                raise RuntimeError(
                    f"Out-of-order chunk {cont[0]} (expected {expected_chunk_id}) for seq={calc_seq}"
                )
            buf.extend(cont[1:])

        self._send_ack(calc_seq, num_chunks)
        return bytes(buf[:msg_len])

    def list_objects(self, timeout_ms: int = 10000) -> list[PrimeObject]:
        """Request calculator object list via 0xF9 and decode all 0xF7 entries."""
        self.send_message(b"\xf9", timeout_ms=timeout_ms)
        objects: list[PrimeObject] = []
        while True:
            msg = self.recv_message(timeout_ms=timeout_ms)
            if msg[0] == 0xF9:
                break
            if msg[0] == 0xF7:
                objects.append(decode_f7_message(msg))
        return objects

    def send_ppl(
        self,
        name: str,
        source: str,
        *,
        compress: bool | None = None,
        timeout_ms: int = 5000,
    ) -> None:
        """Encode and send a PPL program to the calculator."""
        wire_msg = encode_ppl_program(name, source, compress=compress)
        self.send_message(wire_msg, timeout_ms=timeout_ms)
