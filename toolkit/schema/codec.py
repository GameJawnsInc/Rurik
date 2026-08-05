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

nested_struct is deliberately unsupported. The field table gives a count prefix
and an element cap but says nothing about the element layout, so any decoder that
claims to handle it is guessing. Messages using it are reported as undecodable
rather than decoded wrongly — 13 of 777 do.
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
        for f in fields:
            t, length = f["type"], f["length"]
            if t == "msg_header":
                p += 2
                values.append(raw_header)
            elif t in FIXED:
                n = FIXED[t]
                if p + n > len(data):
                    raise NeedMoreData(t)
                if t == "byte":
                    values.append(data[p])
                elif t == "word":
                    values.append(struct.unpack_from("<H", data, p)[0])
                elif t == "float":
                    values.append(struct.unpack_from("<f", data, p)[0])
                elif t == "vec2":
                    values.append(struct.unpack_from("<2f", data, p))
                elif t == "vec3":
                    values.append(struct.unpack_from("<3f", data, p))
                else:
                    values.append(struct.unpack_from("<I", data, p)[0])
                p += n
            elif t == "blob":
                if p + length > len(data):
                    raise NeedMoreData("blob")
                values.append(data[p:p + length])
                p += length
            elif t in COUNTED:
                if p + 2 > len(data):
                    raise NeedMoreData("count")
                count = struct.unpack_from("<H", data, p)[0]
                p += 2
                if count > length:
                    raise Undecodable(f"{t} count {count} exceeds declared cap {length}")
                width = COUNTED[t]
                need = count * width
                if p + need > len(data):
                    raise NeedMoreData(t)
                raw = data[p:p + need]
                p += need
                if t == "string16":
                    values.append(raw.decode("utf-16-le", "replace"))
                elif t == "array8":
                    values.append(raw)
                elif t == "array16":
                    values.append(list(struct.unpack(f"<{count}H", raw)))
                else:
                    values.append(list(struct.unpack(f"<{count}I", raw)))
            elif t == "nested_struct":
                raise Undecodable("nested_struct: element layout is not in the schema")
            else:
                raise Undecodable(f"unhandled field type {t}")
        return opcode, values, p

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
        if len(values) != len(payload):
            raise ValueError(
                f"{channel} 0x{opcode:04x} wants {len(payload)} values, got {len(values)}")
        out = bytearray(struct.pack("<H", opcode if header_value is None else header_value))
        for f, v in zip(payload, values):
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
        return bytes(out)
