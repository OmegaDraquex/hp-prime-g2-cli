# HP Prime G2 USB HID Protocol (V3)

Reverse-engineered from USBPcap captures (`captures/01_connect_and_send.pcap`, `captures/02_send_diff.pcap`) against **HP Connectivity Kit 2.4.2** and **HP Prime G2** firmware `V2.060.650` (build `15751`).

## 1. USB HID Transport

- **VID / PID:** `0x03F0` / `0x2441` (`HP Prime`, Usage Page `0x0081`, Usage `0x0082`, Interface `0`)
- **Endpoints:** Interrupt OUT (`0x02`) and Interrupt IN (`0x81`), fixed **1024-byte** reports
- **Report ID:** None on the USB wire. On Windows via `hidapi`, prepend a single `0x00` Report ID byte (`1025` bytes total) to `write()`, and `read(1024)` returns the raw 1024-byte report.

## 2. Session Handshake

1. **Ready / Info Probe (`0xFA`):**
   - Host sends `00 fa` + 1022 zero bytes.
   - Calculator responds with `00 fa <proto_ver:u8> ...`:
     - `0x02`: protocol version byte (`0x01` or `0x03`)
     - `0x07..0x46`: UTF-16LE null-terminated Device ID (e.g. `1234567890`)
     - `0x4F..0x52`: `u32le` build number (`15751`)
     - `0x53..0x62`: ASCII firmware string (`V2.060.650`)
     - `0x63..0x72`: ASCII serial number (e.g. `XXXXXXXXXX`)
2. **Session Reset (`0xEC`):**
   - Host sends `ff ec` + 1022 zero bytes and resets its V3 sequence counter (`host_seq = 0`).
3. **Protocol V3 Negotiation (`0xFD`):**
   - Host sends V3 message `fd 01 00 00 00 01 03` (`seq=1`).
   - Calculator ACKs (`fe 01 ...`) and responds with `fd <ver> 00 00 00 01 03`.
   - If `<ver> != 0x03`, send `fd 01 00 00 00 01 03` once more; calculator confirms `fd 03 00 00 00 01 03`.

## 3. V3 Chunk Framing & Transport ACKs

### Message Chunking
- **First chunk (`0x01`):**
  `01 <seq:u32le> <msg_len:u32le> <payload[:1015]>` zero-padded to 1024 bytes.
- **Continuation chunks (`0x02..0xFD`):**
  `<chunk_id:u8> <payload[offset:offset+1023]>` zero-padded to 1024 bytes (`chunk_id` increments `2, 3, ...`, max `253`).

### Transport ACK (`0xFE 0x01`)
Sent by receiver after all chunks of a message arrive:
- `0x00..0x01`: `fe 01`
- `0x02..0x03`: `num_chunks:u16le`
- `0x04..0x07`: `capacity:u32le` (`1015 + (num_chunks - 1) * 1023`)
- `0x08..0x0B`: `acked_seq:u32le`
- `0x0C..0x0F`: `00 00 00 00`
- `0x10..0x17`: `ff ff ff ff ff ff ff ff`
- `0x18..0x1F`: `00 00 00 00 00 00 00 00`
- `0x20..0x23`: `last_own_seq:u32le`

### Heartbeats (`0xFE 0x01 0xFF`)
The calculator sends unsolicited `fe 01 ff ...` status packets roughly every 500 ms. Clients must skip/ignore these while awaiting ACKs or message chunks.

## 4. `0xF7` Object Format & CRC-16

### Outer `0xF7` Framing
- **Uncompressed:** `f7 03 <len(raw):u32be> <raw>`
- **Compressed:** `f7 03 <4 + len(z):u32be> <len(raw):u32le> <zlib_stream>` (`zlib` level 1, header `78 01`)

### Inner `raw` Layout
| Offset | Size | Field |
|---|---|---|
| `0x00` | `1` | `file_type` (`0x00` Settings, `0x02` App, `0x03` List, `0x04` Matrix, `0x06` PPL Program, `0x0B` Custom) |
| `0x01` | `1` | `name_len_bytes` (UTF-16LE byte length of name, without NUL) |
| `0x02` | `2` | `crc16:u16le` |
| `0x04` | `name_len_bytes` | Object name in UTF-16LE |
| `4 + name_len_bytes` | `...` | Object data (for `0x06` PPL programs: `\n`-normalized UTF-16LE source + `00 00`) |

### Header Checksum Algorithm
`crc16` at `raw[2:4]` (little-endian) is **CRC-16/XMODEM** (`poly=0x1021`, `init=0x0000`, `xorout=0x0000`, unreflected) computed over:

```text
b"\xf7\x03" + u32be(len(raw)) + raw[0:2] + b"\x00\x00" + raw[4:]
```

Verified across all 46 `0xF7` objects in `01_connect_and_send.pcap` (46/46 pass) and exact byte-for-byte match against `02_send_diff.pcap` sends (`1+1`, `1+2`, `1+3`).

## 5. Listing / Backup (`0xF9`)
- Host sends V3 message `f9` (1 byte).
- Calculator streams each stored object as an `0xF7` V3 message (host ACKs each with `0xFE 0x01`).
- Calculator terminates the transfer with a `0xF9` message (`f9 03 00 00 00 00`), which the host ACKs.
