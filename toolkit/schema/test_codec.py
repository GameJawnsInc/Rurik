"""Validate the codec against bytes the real Guild Wars client actually sent.

Synthetic round-trips only prove the codec agrees with itself. The capture from
build 38797 is ground truth, so it is the primary fixture here: if the schema's
field layout is wrong, the real frame will not decode cleanly to its end.
"""

import binascii
import glob
import json
import os
import socket
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from codec import Codec, Undecodable  # noqa: E402

AUTH_CMSG_MASK = 0x8000


def check(name, cond, detail=""):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}{(' — ' + detail) if detail else ''}")
    return cond


def main():
    c = Codec()
    ok = True

    print("\n1. real client frames from the vault (build 38797)")
    # Select the fixture by CONTENT, never by position. This used to take "the
    # last long frame in the newest capture", which silently became a
    # PORTAL_ACCOUNT_LOGIN frame the first time a session captured something
    # other than the login opening -- and then failed with assertions about
    # SEND_COMPUTER_INFO that had nothing to do with the codec. Every captured
    # opening frame is checked instead, so more sessions make this stronger
    # rather than more fragile.
    OPENING = 0x8001                       # SEND_COMPUTER_INFO, first thing sent
    frames = []
    for path in sorted(glob.glob(r"vault/captures/authsrv/*.jsonl")):
        for line in open(path, encoding="utf-8"):
            e = json.loads(line)
            if e.get("kind") != "frame" or e.get("direction") != "c2s":
                continue
            plain = binascii.unhexlify(e.get("plain", ""))
            if len(plain) >= 2 and int.from_bytes(plain[:2], "little") == OPENING:
                frames.append((os.path.basename(path), plain))

    if not frames:
        print("  [SKIP] no client opening frame captured yet — run a live session")
    else:
        print(f"  checking {len(frames)} captured opening frame(s)")
        first = True
        bad = []
        for path, data in frames:
            msgs, consumed, err = c.decode_stream("AUTH_CMSG", data,
                                                  mask=AUTH_CMSG_MASK)
            if first:
                for opcode, values in msgs:
                    shown = [v if not isinstance(v, bytes)
                             else binascii.hexlify(v).decode() for v in values]
                    print(f"     0x{opcode | AUTH_CMSG_MASK:04x}  {shown}")
                first = False
            why = None
            if consumed != len(data) or err is not None:
                why = f"consumed {consumed}/{len(data)}" + (f", {err}" if err else "")
            elif len(msgs) != 2:
                why = f"{len(msgs)} messages, expected 2"
            else:
                (op0, v0), (op1, v1) = msgs
                if not (op0 == 0x0001 and len(v0) == 3
                        and all(isinstance(x, str) for x in v0[1:])):
                    why = f"first message is 0x{op0:04x}, not SEND_COMPUTER_INFO"
                elif not (op1 == 0x0002 and isinstance(v1[-1], bytes)
                          and len(v1[-1]) == 16):
                    why = f"second message is 0x{op1:04x} or lacks a 16-byte blob"
                elif v1[1] != 38797:
                    why = f"build {v1[1]}, expected 38797"
            if why:
                bad.append(f"{path}: {why}")

        ok &= check("every captured opening frame decodes exactly",
                    not bad, "; ".join(bad) if bad else f"{len(frames)} frames")

    print("\n2. round-trip the message we need to send (AUTH_SMSG_SESSION_INFO)")
    blob = c.encode("AUTH_SMSG", 0x0001, [0xDEADBEEF, 0])
    print(f"  encoded {len(blob)} bytes: {binascii.hexlify(blob).decode()}")
    msgs, consumed, err = c.decode_stream("AUTH_SMSG", blob)
    ok &= check("round-trips", consumed == len(blob) and err is None
                and msgs and msgs[0][1][1] == 0xDEADBEEF, err or "")
    ok &= check("is 10 bytes, not 14 — the format table wins over the C struct",
                len(blob) == 10, f"{len(blob)}")

    print("\n3. the codec must refuse what it cannot know")
    nested = [op for op, m in c.channels["GAME_SMSG"]["messages"].items()
              if any(f["type"] == "nested_struct" for f in m["fields"])]
    ok &= check("nested_struct messages exist and are refused, not guessed",
                bool(nested), f"{len(nested)} such messages")
    if nested:
        try:
            c.fields_for("GAME_SMSG", int(nested[0]))
            fake = bytes(64)
            _, _, err = c.decode_stream("GAME_SMSG", fake)
            ok &= check("decoding one reports an error rather than inventing values",
                        err is not None, str(err))
        except Undecodable:
            pass

    print("\n4. the R2 handoff message (AUTH_SMSG_GAME_SERVER_INFO)")
    # The client casts the 24-byte host field straight to a sockaddr, so the
    # endianness is mixed on purpose: family little-endian, port big-endian.
    # Getting the port backwards sends it to a plausible port thousands away
    # from ours, and the only symptom is a connection that never arrives.
    host = (struct.pack("<H", socket.AF_INET) + struct.pack(">H", 6113)
            + socket.inet_aton("127.0.0.1") + b"\x00" * 16)
    ok &= check("the host field is exactly sizeof(sockaddr)", len(host) == 24,
                f"{len(host)}")
    gsi = c.encode("AUTH_SMSG", 0x0009, [0x2A, 0xDEAD, 148, host, 0xBEEF])
    ok &= check("encodes to the schema's declared_unpack_size", len(gsi) == 42,
                f"{len(gsi)} bytes")
    af = struct.unpack_from("<H", gsi, 14)[0]
    port = struct.unpack_from(">H", gsi, 16)[0]
    ip = socket.inet_ntoa(gsi[18:22])
    ok &= check("a sockaddr cast reads back the address we meant",
                af == socket.AF_INET and port == 6113 and ip == "127.0.0.1",
                f"af={af} {ip}:{port}")

    print(f"\n{'ALL CHECKS PASSED' if ok else 'FAILURES ABOVE'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
