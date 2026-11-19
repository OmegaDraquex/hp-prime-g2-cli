# hpprime — HP Prime G2 USB HID CLI

A lightweight, pure-Python CLI and library for inspecting, sending, and pulling **HP Prime Programming Language (PPL)** programs on the **HP Prime G2** graphing calculator over **USB HID Protocol V3**—without needing the official HP Connectivity Kit GUI or custom kernel drivers.

Built by reverse-engineering USBPcap captures between **HP Connectivity Kit 2.4.2** and an **HP Prime G2** (tested on firmware `V2.060.650`, build `15751`).

---

## Features

- **Direct USB HID communication (`VID=0x03F0`, `PID=0x2441`):** Uses Windows/OS built-in HID drivers via `hidapi`.
- **Full Protocol V3 implementation:** `0xFA` info probe, `0xEC` transport reset, `0xFD` Protocol V3 handshake, multi-chunk `0x01`/`0x02+` framing (1024-byte HID reports), `0xFE 0x01` ACKs, and automatic `0xFE 0x01 0xFF` heartbeat filtering.
- **Send PPL source files (`hpprime send`):**
  - Reads UTF-8 (`utf-8-sig`) or UTF-16 (BOM auto-detected) `.ppl` / text files and normalizes line endings to `\n`.
  - Computes the exact `0xF7` CRC-16/XMODEM header checksum verified against HP Connectivity Kit wire captures.
  - Supports automatic or forced `zlib` compression (`--compress` / `--no-compress`) and multi-chunk transfers (> 1,015 bytes).
  - Optional `--verify` flag reads the program back via `0xF9` to confirm exact source and CRC match on the calculator.
- **Inspect & pull (`hpprime info`, `hpprime list`, `hpprime pull`):** Query device metadata, list stored programs or all objects (`--all`), and pull program source back to stdout or disk.
- **Reusable Python library:** Import `HPPrimeG2`, `encode_ppl_program`, and `decode_f7_message` directly in scripts or build pipelines.

---

## Requirements

- **Hardware:** HP Prime G2 graphing calculator (`VID=0x03F0`, `PID=0x2441`) connected via USB
- **OS:** Windows (tested) or any OS supported by `hidapi` (Linux/macOS with appropriate USB HID permissions)
- **Python:** `>= 3.12`
- **Dependencies:** `hidapi >= 0.14`, `click >= 8.1`

> [!IMPORTANT]
> Close **HP Connectivity Kit** before running `hpprime`. Windows does not share exclusive HID handles cleanly across both processes, and concurrent reads/writes will drop packets.

---

## Installation

```powershell
# Clone the repository
git clone https://github.com/OmegaDraquex/hp-prime-g2-cli.git
cd hp-prime-g2-cli

# Create a virtual environment and install hpprime in editable mode
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
```

After installation, the CLI entrypoint is available at `.\.venv\Scripts\hpprime.exe` (or `hpprime` when `.venv` is activated).

---

## CLI Usage

### `hpprime info`
Queries the calculator via `0xFA` and prints hardware/firmware metadata without modifying device state.

```powershell
.\.venv\Scripts\hpprime.exe info
```

Example output:
```text
Model:            HP Prime G2 (VID=0x03F0, PID=0x2441)
Firmware:         V2.060.650
Build:            15751
Serial:           XXXXXXXXXX
Device ID:        1234567890
Protocol Version: 3
```

### `hpprime list`
Negotiates Protocol V3, requests the calculator backup stream (`0xF9`), and lists stored PPL programs (or all objects with `--all`, including Settings, Apps, Lists, Matrices, and Custom items).

```powershell
.\.venv\Scripts\hpprime.exe list
.\.venv\Scripts\hpprime.exe list --all
```

Example output:
```text
Name         Type       Bytes  CRC   Mode
-----------  -------  -------  ----  ----
MYPROG       Program      134  OK    zlib
T1           Program       64  OK    raw
CLITEST_BIG  Program     3302  OK    zlib
```

### `hpprime send`
Encodes a plain-text PPL file and transfers it to the calculator.

```powershell
# Program name defaults to the file stem ("clitest")
.\.venv\Scripts\hpprime.exe send examples\clitest.ppl --verify

# Explicit program name (note: pull matches names case-sensitively)
.\.venv\Scripts\hpprime.exe send examples\clitest.ppl --name CLITEST --verify

# Force zlib compression or uncompressed multi-chunk mode
.\.venv\Scripts\hpprime.exe send examples\clitest_big.ppl --name CLITEST_BIG --compress --verify
.\.venv\Scripts\hpprime.exe send examples\clitest_big.ppl --name CLITEST_BIG --no-compress --verify
```

Options:
- `--name NAME` — Program name on the calculator (defaults to `Path(filepath).stem`)
- `--compress / --no-compress` — Force `zlib` compression on or off (default: auto-compress when raw payload exceeds 800 bytes)
- `--verify` — Read back objects via `0xF9` after sending and confirm name, CRC-16, and exact source text match

### `hpprime pull`
Pulls a PPL program from the calculator (case-sensitive name match) and prints to stdout or writes to `-o OUTFILE`.

```powershell
.\.venv\Scripts\hpprime.exe pull CLITEST
.\.venv\Scripts\hpprime.exe pull CLITEST -o clitest_backup.ppl
```

### `hpprime delete`
Deletes one or more PPL programs from the calculator via `0xEB` (case-sensitive name match). Pass `--verify` to confirm removal via `0xF9`.

```powershell
.\.venv\Scripts\hpprime.exe delete CLITEST --verify
.\.venv\Scripts\hpprime.exe delete PROG1 PROG2 --verify
```

---

## Python Library API

```python
from hpprime.protocol import HPPrimeG2
from hpprime.files import TYPE_PROGRAM, decode_ppl_source

with HPPrimeG2() as calc:
    info = calc.connect()
    print(f"Connected to {info.firmware_version} (build {info.build_number})")

    calc.send_ppl(
        "HELLO",
        'EXPORT HELLO()\nBEGIN\n  MSGBOX("Hello from Python!");\nEND;\n',
    )

    for obj in calc.list_objects():
        if obj.file_type == TYPE_PROGRAM and obj.name == "HELLO":
            print(decode_ppl_source(obj))
```

---

## Repository Structure

| Path | Purpose |
|---|---|
| [pyproject.toml](pyproject.toml) | Package metadata and `hpprime` CLI script entrypoint |
| [hpprime/crc.py](hpprime/crc.py) | `crc16_xmodem`, `compute_f7_crc`, and `verify_f7_raw` |
| [hpprime/files.py](hpprime/files.py) | `0xF7` object encoder/decoder (`encode_ppl_program`, `decode_f7_message`, `decode_ppl_source`) |
| [hpprime/protocol.py](hpprime/protocol.py) | `HPPrimeG2` USB HID V3 transport, chunking (`chunk_v3_message`), ACKs, and handshake |
| [hpprime/cli.py](hpprime/cli.py) | Click CLI (`info`, `list`, `send`, `pull`) |
| [docs/protocol.md](docs/protocol.md) | Reverse-engineered HP Prime G2 USB HID V3 protocol reference |
| [tools/decode_pcap.py](tools/decode_pcap.py) | Standalone USBPcap HID interrupt parser and `zlib` inspector |
| [tests/test_protocol_offline.py](tests/test_protocol_offline.py) | Offline protocol, chunking, compression, and wire-vector regression tests |
| [examples/clitest.ppl](examples/clitest.ppl) | Minimal PPL test program |
| [examples/clitest_big.ppl](examples/clitest_big.ppl) | Multi-chunk / `zlib` test program |

---

## Protocol Overview

The full wire specification is documented in [docs/protocol.md](docs/protocol.md). Key findings from USBPcap analysis:

1. **HID Reports:** Interrupt OUT (`0x02`) and IN (`0x81`) use fixed **1024-byte** reports with no Report ID byte on the USB wire. On Windows `hidapi`, `write()` expects a leading `0x00` Report ID byte (1025 bytes passed to `hid.device.write()`), which Windows strips before transmitting the 1024-byte report.
2. **Handshake:** `0xFA` (device info) → `0xEC` (transport reset, `host_seq = 0`) → `0xFD` (`fd 01 00 00 00 01 03`, repeated once if needed until calculator replies `fd 03 ...`).
3. **V3 Framing:**
   - First chunk (`0x01`): `01 <seq:u32le> <msg_len:u32le> <payload[:1015]>`
   - Continuation chunks (`0x02..0xFD`): `<chunk_id:u8> <payload[off:off+1023]>`
   - Transport ACKs (`0xFE 0x01`) include `<num_chunks:u16le>`, `<capacity:u32le>`, `<acked_seq:u32le>`, and `<last_own_seq:u32le>`. Unsolicited `0xFE 0x01 0xFF` keepalive heartbeats arrive roughly every 500 ms and are ignored during reads.
4. **`0xF7` Program Format & CRC-16:**
   - Uncompressed `raw`: `<type=0x06:u8> <name_len_bytes:u8> <crc16:u16le> <name_utf16le> <source_utf16le> 00 00`
   - Outer wire frame: `f7 03 <payload_len:u32be> <raw>` (or `<u32le len(raw)> + zlib.compress(raw, level=1)` when compressed)
   - Checksum: **CRC-16/XMODEM** (`poly=0x1021`, `init=0x0000`, `xorout=0x0000`) computed over:
     ```python
     b"\xf7\x03" + struct.pack(">I", len(raw)) + raw[:2] + b"\x00\x00" + raw[4:]
     ```

---

## Extending to Other File Types

Currently `hpprime` implements PPL programs (`0x06`), while `decode_f7_message` inspects all `0xF7` types returned by `0xF9` (`Settings`, `App`, `List`, `Matrix`, `Program`, `Custom`). To add support for MicroPython scripts, Notes, Lists, Matrices, or Apps:

1. Capture a USBPcap trace of **HP Connectivity Kit** sending two minimal examples differing by one character:
   ```powershell
   & "C:\Program Files\USBPcap\USBPcapCMD.exe" -d \\.\USBPcap1 -o captures\my_type.pcap --devices <addr> --inject-descriptors
   ```
   *(Run from an Administrator PowerShell window, then press **Ctrl+C** after the transfer to flush the `.pcap`.)*
2. Dissect the capture with [tools/decode_pcap.py](tools/decode_pcap.py):
   ```powershell
   .\.venv\Scripts\python.exe tools\decode_pcap.py captures\my_type.pcap
   ```
3. Add an encoder in [hpprime/files.py](hpprime/files.py) and a byte-for-byte wire vector test in [tests/test_protocol_offline.py](tests/test_protocol_offline.py).

---

## Running Tests

Offline tests validate CRC-16 calculation, V3 chunking, `zlib` round-tripping, and exact byte-for-byte wire payloads (plus full 46-object verification if local `.pcap` captures are present in `captures/`):

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

---

## Troubleshooting

- **`Unable to open HP Prime G2 HID device`:** Close **HP Connectivity Kit** (and any background updater/monitor holding the HID handle) and unplug/replug if needed.
- **`HP Prime G2 (VID=0x03F0, PID=0x2441) not found`:** Confirm the calculator is powered on and awake; older G1 hardware revisions use different PIDs (`0x0441` / `0x1541`) and 64-byte packet framing, which this tool does not target.
- **Case-sensitive `pull`:** Remember `hpprime send myprog.ppl` creates `myprog` on the calculator unless `--name MYPROG` is passed, and `hpprime pull` matches the exact name shown in `hpprime list`.
