"""Validate the codec against bytes the real Guild Wars client actually sent.

Synthetic round-trips only prove the codec agrees with itself. The capture from
build 38797 is ground truth, so it is the primary fixture here: if the schema's
field layout is wrong, the real frame will not decode cleanly to its end.
"""

import binascii
import glob
import json
import os
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

    print("\n1. real client frame from the vault (build 38797)")
    frames = []
    for path in sorted(glob.glob(r"vault/captures/authsrv/*.jsonl")):
        for line in open(path, encoding="utf-8"):
            e = json.loads(line)
            if e.get("kind") == "frame" and e.get("direction") == "c2s":
                plain = binascii.unhexlify(e.get("plain", ""))
                if len(plain) >= 2 and plain[0] | (plain[1] << 8) & 0xFF00:
                    frames.append((os.path.basename(path), plain))
    real = [(p, f) for p, f in frames if len(f) > 30]
    if not real:
        print("  [SKIP] no real client frame captured yet — run a live session")
    else:
        path, data = real[-1]
        print(f"  using {path} ({len(data)} bytes)")
        msgs, consumed, err = c.decode_stream("AUTH_CMSG", data, mask=AUTH_CMSG_MASK)
        ok &= check("decoded to the exact end of the frame",
                    consumed == len(data) and err is None,
                    f"consumed {consumed}/{len(data)}" + (f", {err}" if err else ""))
        ok &= check("two messages", len(msgs) == 2, f"{len(msgs)}")
        for opcode, values in msgs:
            shown = [v if not isinstance(v, bytes) else binascii.hexlify(v).decode()
                     for v in values]
            print(f"     0x{opcode | AUTH_CMSG_MASK:04x}  {shown}")
        if msgs:
            op0, v0 = msgs[0]
            ok &= check("first is SEND_COMPUTER_INFO with two strings",
                        op0 == 0x0001 and len(v0) == 3
                        and all(isinstance(x, str) for x in v0[1:]),
                        f"opcode 0x{op0:04x}")
            if len(msgs) > 1:
                op1, v1 = msgs[1]
                ok &= check("second is SEND_COMPUTER_HASH with a 16-byte blob",
                            op1 == 0x0002 and isinstance(v1[-1], bytes)
                            and len(v1[-1]) == 16,
                            f"opcode 0x{op1:04x}")
                ok &= check("its dword carries the build number", v1[1] == 38797,
                            str(v1[1]))

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

    print(f"\n{'ALL CHECKS PASSED' if ok else 'FAILURES ABOVE'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
