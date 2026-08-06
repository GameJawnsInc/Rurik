"""Encode and decode Guild Wars messages from the imported schema.

Wire rules, taken from OpenTyria's msgpack.c and confirmed against a real capture
from build 38797:

    msg_header, word          u16
    byte                      u8
    dword, float, agent_id    u32 / f32
    vec2, vec3                2 or 3 f32
    blob                      exactly `length` bytes, no count prefix
    string16                  u16 count, then count * 2 bytes of UTF-16LE
    array8 / array16 / array32  u16 count, then count * 1 / 2 / 4 bytes
    nested_struct             u8 count, then count nested records

Watch the counts. In the C source the in-memory struct holds a u32 count while
the WIRE carries u16 — pack() reads u32 from the struct and writes u16 out. Read
that code as if it described the wire and every variable-length message is framed
two bytes wrong. The real capture settles it: `AUTH_CMSG_SEND_COMPUTER_INFO`
begins `05 00` for a five-character string.

nested_struct was deliberately unsupported here, on the grounds that the field
table gave a count prefix and an element cap but said nothing about the element
layout, so any decoder claiming to handle it was guessing. That was correct when
it was written and is now superseded: the client's own message-format tables were
recovered from Gw.exe, and type 12 is documented there as "nested-struct repeat
count; parser rewinds to cmd+4 per repetition" with a ONE-byte wire count
(`studies/msgtable/FINDINGS.md` section 2.2, the `push 8` / mask `0xff` at
0x7dc280). cmd+4 is the descriptor immediately after the type-12 one, so the
element layout is exactly the schema's remaining tail, repeated `count` times.
That is measured, not guessed, and it is why the 13 messages that use it decode
now. The tail fields are NOT separate fields: a caller passes one value for the
nested_struct — a list of rows — and nothing after it.
"""

import json
import os
import struct

DEFAULT_SCHEMA = r"C:\gd\Rurik\schema\messages.json"

FIXED = {"msg_header": 2, "word": 2, "byte": 1, "dword": 4,
         "float": 4, "agent_id": 4, "vec2": 8, "vec3": 12}
COUNTED = {"string16": 2, "array16": 2, "array8": 1, "array32": 4}


class Undecodable(Exception):
    pass


class NeedMoreData(Exception):
    pass


class Codec:
    def __init__(self, path=DEFAULT_SCHEMA, overrides=None):
        with open(path, encoding="utf-8") as f:
            self.schema = json.load(f)
        self.channels = self.schema["channels"]

        # messages.json is generated from OpenTyria and carries
        # `authority: imported`. Where our own captures contradict it, the
        # correction lives beside it rather than inside it, so regenerating from
        # upstream cannot quietly revert a verdict the client already gave us.
        if overrides is None:
            overrides = os.path.join(os.path.dirname(os.path.abspath(path)),
                                     "overrides.json")
        self.overridden = []
        if os.path.exists(overrides):
            with open(overrides, encoding="utf-8") as f:
                over = json.load(f)
            for chan, msgs in over.get("channels", {}).items():
                target = self.channels.setdefault(chan, {"messages": {}})
                for key, msg in msgs.items():
                    target["messages"][key] = msg
                    self.overridden.append(f"{chan}[{key}]")

    def fields_for(self, channel, opcode):
        chan = self.channels.get(channel)
        if not chan:
            raise Undecodable(f"unknown channel {channel}")
        m = chan["messages"].get(str(opcode))
        if not m:
            raise Undecodable(f"{channel} has no opcode {opcode} (0x{opcode:04x})")
        return m["fields"]

    # ---------------------------------------------------------------- decode
    def decode_one(self, channel, data, off=0, mask=0):
        """Decode one message at `off`. Returns (opcode, values, new_off)."""
        if off + 2 > len(data):
            raise NeedMoreData("no header")
        raw_header = struct.unpack_from("<H", data, off)[0]
        opcode = raw_header & ~mask if mask else raw_header
        fields = self.fields_for(channel, opcode)

        values = []
        p = off
        for i, f in enumerate(fields):
            if f["type"] == "msg_header":
                p += 2
                values.append(raw_header)
            elif f["type"] == "nested_struct":
                # One byte of count, then the tail repeated that many times.
                # See the module docstring: the tail IS the element layout, so
                # this consumes the rest of the field list and stops.
                element = fields[i + 1:]
                if not element:
                    raise Undecodable(
                        "nested_struct is the last field: the schema carries no "
                        "element layout for it")
                if p >= len(data):
                    raise NeedMoreData("nested_struct count")
                count = data[p]
                p += 1
                if count > f["length"]:
                    raise Undecodable(
                        f"nested_struct count {count} exceeds declared cap {f['length']}")
                rows = []
                for _ in range(count):
                    row = []
                    for ef in element:
                        v, p = self._decode_field(ef, data, p)
                        row.append(v)
                    rows.append(row)
                values.append(rows)
                break
            else:
                v, p = self._decode_field(f, data, p)
                values.append(v)
        return opcode, values, p

    def _decode_field(self, f, data, p):
        """Decode one non-header, non-nested field. Returns (value, new_off)."""
        t, length = f["type"], f["length"]
        if t in FIXED:
            n = FIXED[t]
            if p + n > len(data):
                raise NeedMoreData(t)
            if t == "byte":
                v = data[p]
            elif t == "word":
                v = struct.unpack_from("<H", data, p)[0]
            elif t == "float":
                v = struct.unpack_from("<f", data, p)[0]
            elif t == "vec2":
                v = struct.unpack_from("<2f", data, p)
            elif t == "vec3":
                v = struct.unpack_from("<3f", data, p)
            else:
                v = struct.unpack_from("<I", data, p)[0]
            return v, p + n
        if t == "blob":
            if p + length > len(data):
                raise NeedMoreData("blob")
            return data[p:p + length], p + length
        if t in COUNTED:
            if p + 2 > len(data):
                raise NeedMoreData("count")
            count = struct.unpack_from("<H", data, p)[0]
            p += 2
            if count > length:
                raise Undecodable(f"{t} count {count} exceeds declared cap {length}")
            need = count * COUNTED[t]
            if p + need > len(data):
                raise NeedMoreData(t)
            raw = data[p:p + need]
            p += need
            if t == "string16":
                return raw.decode("utf-16-le", "replace"), p
            if t == "array8":
                return raw, p
            if t == "array16":
                return list(struct.unpack(f"<{count}H", raw)), p
            return list(struct.unpack(f"<{count}I", raw)), p
        raise Undecodable(f"unhandled field type {t}")

    def decode_stream(self, channel, data, mask=0):
        """Decode as many whole messages as possible.

        Returns (messages, consumed, error). Stops at the first message it cannot
        frame and reports why. It does NOT try to resynchronise: without a length
        prefix there is nothing to resynchronise against, and guessing would turn
        one unknown message into a stream of fictitious ones.
        """
        out, off, err = [], 0, None
        while off < len(data):
            try:
                opcode, values, off = self.decode_one(channel, data, off, mask)
                out.append((opcode, values))
            except NeedMoreData as ex:
                err = f"incomplete: {ex}"
                break
            except Undecodable as ex:
                err = f"stopped at offset {off}: {ex}"
                break
        return out, off, err

    # ---------------------------------------------------------------- encode
    def encode(self, channel, opcode, values, header_value=None):
        fields = self.fields_for(channel, opcode)
        payload = [f for f in fields if f["type"] != "msg_header"]
        # A nested_struct swallows every field after it as its element layout,
        # so the caller supplies one value for the whole repeated tail and none
        # for the tail fields themselves.
        nested = next((i for i, f in enumerate(payload)
                       if f["type"] == "nested_struct"), None)
        want = len(payload) if nested is None else nested + 1
        if len(values) != want:
            raise ValueError(
                f"{channel} 0x{opcode:04x} wants {want} values, got {len(values)}")
        out = bytearray(struct.pack("<H", opcode if header_value is None else header_value))
        for f, v in zip(payload, values):
            if f["type"] == "nested_struct":
                element = payload[nested + 1:]
                if not element:
                    raise ValueError(
                        "nested_struct is the last field: the schema carries no "
                        "element layout for it")
                rows = list(v)
                if len(rows) > f["length"]:
                    raise ValueError(
                        f"nested_struct of {len(rows)} exceeds cap {f['length']}")
                out += struct.pack("<B", len(rows))
                for row in rows:
                    if len(row) != len(element):
                        raise ValueError(
                            f"nested_struct row wants {len(element)} values, "
                            f"got {len(row)}")
                    for ef, ev in zip(element, row):
                        self._encode_field(ef, ev, out)
            else:
                self._encode_field(f, v, out)
        return bytes(out)

    def _encode_field(self, f, v, out):
        """Append one non-header, non-nested field to the bytearray `out`."""
        t, length = f["type"], f["length"]
        if t == "byte":
            out += struct.pack("<B", v)
        elif t == "word":
            out += struct.pack("<H", v)
        elif t == "float":
            out += struct.pack("<f", v)
        elif t == "vec2":
            out += struct.pack("<2f", *v)
        elif t == "vec3":
            out += struct.pack("<3f", *v)
        elif t in ("dword", "agent_id"):
            out += struct.pack("<I", v)
        elif t == "blob":
            b = bytes(v)
            if len(b) != length:
                raise ValueError(f"blob wants exactly {length} bytes, got {len(b)}")
            out += b
        elif t == "string16":
            s = str(v)
            if len(s) > length:
                raise ValueError(f"string of {len(s)} exceeds cap {length}")
            out += struct.pack("<H", len(s)) + s.encode("utf-16-le")
        elif t in ("array8", "array16", "array32"):
            seq = list(v)
            if len(seq) > length:
                raise ValueError(f"{t} of {len(seq)} exceeds cap {length}")
            out += struct.pack("<H", len(seq))
            if t == "array8":
                out += bytes(seq)
            elif t == "array16":
                out += struct.pack(f"<{len(seq)}H", *seq)
            else:
                out += struct.pack(f"<{len(seq)}I", *seq)
        else:
            raise ValueError(f"cannot encode field type {t}")
