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

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from codec import Codec, Undecodable  # noqa: E402
import vaultpath  # noqa: E402
import checks  # noqa: E402

AUTH_CMSG_MASK = 0x8000

# Floor 11 = every check below, all of them unconditional: section 1 contributes
# exactly one whatever the vault holds (the three branches each score a single
# verdict), then 2 + 5 + 3 for sections 2, 3 and 4. Measured from a green run on
# 2026-08-06 against 162 captured opening frames. This file is the reason
# checks.py exists — it once printed ALL CHECKS PASSED with its capture glob
# matching nothing — so the floor is what makes section 1 going quiet a failure
# rather than a shorter list of passes.
LEDGER = checks.Ledger("codec vs captured bytes", floor=15)
check = checks.adopt_named(LEDGER)


def main():
    c = Codec()
    ok = True   # kept only so the `ok &= check(...)` call sites read unchanged;
                # the verdict now lives in LEDGER, which also counts the checks.

    print("\n1. real client frames from the vault (build 38797)")
    # Select the fixture by CONTENT, never by position. This used to take "the
    # last long frame in the newest capture", which silently became a
    # PORTAL_ACCOUNT_LOGIN frame the first time a session captured something
    # other than the login opening -- and then failed with assertions about
    # SEND_COMPUTER_INFO that had nothing to do with the codec. Every captured
    # opening frame is checked instead, so more sessions make this stronger
    # rather than more fragile.
    #
    # Resolve the vault rather than trusting the working directory. This glob
    # was relative to the CWD, so anywhere but the repo root — and a git
    # worktree, which has no vault of its own, is always anywhere else — it
    # matched nothing, printed [SKIP], and the run still ended in ALL CHECKS
    # PASSED with the ground truth never consulted. A fixture the docstring
    # calls primary is not optional: its absence is a failure, not a note.
    OPENING = 0x8001                       # SEND_COMPUTER_INFO, first thing sent
    vault = vaultpath.require_dir(
        "captures", "authsrv",
        why="real client frames are this test's only ground truth")
    captures = sorted(glob.glob(os.path.join(vault, "*.jsonl")))
    frames = []
    for path in captures:
        for line in open(path, encoding="utf-8"):
            e = json.loads(line)
            if e.get("kind") != "frame" or e.get("direction") != "c2s":
                continue
            plain = binascii.unhexlify(e.get("plain", ""))
            if len(plain) >= 2 and int.from_bytes(plain[:2], "little") == OPENING:
                frames.append((os.path.basename(path), plain))

    if not captures:
        ok &= check("the vault has sessions to check the codec against", False,
                    f"no *.jsonl under {vault} — run a live session")
    elif not frames:
        ok &= check("a captured session carries the client's opening frame", False,
                    f"{len(captures)} capture(s) under {vault}, none containing "
                    f"a 0x{OPENING:04x} frame — run a live session")
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

    print("\n3. nested_struct (client field type 12)")
    # This block used to assert that nested_struct was REFUSED. That was the
    # right behaviour while the element layout was unknown, and it stopped being
    # a real check the moment studies/msgtable recovered the client's own tables:
    # type 12 is a one-byte repeat count and the parser "rewinds to cmd+4 per
    # repetition", so the element layout is the schema tail. Worse, the old check
    # passed for the wrong reason -- it decoded 64 zero bytes, which is opcode 0,
    # not a nested message at all, and any error at all satisfied it.
    #
    # What replaces it can actually fail: encode CREATE_NAMED_ITEM with a known
    # modifier list, decode it back, and require the bytes to land where the
    # one-byte count says they must.
    nested = [op for op, m in c.channels["GAME_SMSG"]["messages"].items()
              if any(f["type"] == "nested_struct" for f in m["fields"])]
    ok &= check("nested_struct messages exist in the schema",
                bool(nested), f"{len(nested)} such messages")

    CREATE_NAMED_ITEM = 0x0161
    mods = [[0x24B80000], [0xA4880503]]
    item = c.encode("GAME_SMSG", CREATE_NAMED_ITEM,
                    [1, 0x80009B60, 15, 6, 0, 0, 0, 0x22201000, 0, 1699, 1,
                     "ABCD", mods])
    # 2 header + 4 item_id + 4 file_id + 1 type + 1 tint + 2 colors
    # + 2 materials + 1 unk1 + 4 flags + 4 value + 4 model + 4 quantity = 33,
    # + name (2 count + 4 chars * 2) = 10, + modifiers (1 count + 2 * 4) = 9.
    ok &= check("a 2-modifier item is 52 bytes, with a ONE-byte modifier count",
                len(item) == 52, f"{len(item)}")
    ok &= check("the count byte is where the arithmetic above puts it",
                item[43] == 2, f"item[43]={item[43]}")
    msgs, consumed, err = c.decode_stream("GAME_SMSG", item)
    ok &= check("it round-trips", consumed == len(item) and err is None
                and msgs and msgs[0][1][13] == mods, err or f"{msgs[0][1][13] if msgs else None}")
    # An empty list is the case we actually send first, and an off-by-one in the
    # count would show up here as a decode error rather than as silence.
    empty = c.encode("GAME_SMSG", CREATE_NAMED_ITEM,
                     [1, 0x80009B60, 15, 6, 0, 0, 0, 0x22201000, 0, 1699, 1, "", []])
    msgs, consumed, err = c.decode_stream("GAME_SMSG", empty)
    ok &= check("zero modifiers round-trips too", consumed == len(empty)
                and err is None and msgs and msgs[0][1][13] == [], err or "")

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

    # --- the catalog this checkout loads, and the names it now carries ----------
    # DEFAULT_SCHEMA was a hardcoded absolute path into the MAIN checkout until
    # 2026-08-10, so every worktree decoded against a file its own branch did not
    # contain -- and a schema edit made in a worktree did nothing while this suite
    # went green anyway. Same failure vaultpath.py exists to prevent, inverted.
    import codec as codec_mod
    repo = os.path.dirname(os.path.dirname(HERE))
    LEDGER.ok(os.path.abspath(codec_mod.DEFAULT_SCHEMA)
              == os.path.abspath(os.path.join(repo, "schema", "messages.json")),
              "the codec loads THIS checkout's schema, not another one's",
              codec_mod.DEFAULT_SCHEMA)

    # GAME_CMSG had 194 layouts and zero names. Names live in overrides.json beside
    # the evidence, and are added only by a labelled run (studies/cmsg/FINDINGS.md).
    named = {0x0026: "ATTACK", 0x0039: "INTERACT", 0x0046: "USE_SKILL",
             0x0064: "CHAT_SEND", 0x00C1: "TARGET_SELECT"}
    got = {op: c.name_for("GAME_CMSG", op) for op in named}
    LEDGER.ok(got == named,
              "the client-to-server opcodes we have earned names for resolve",
              ", ".join(f"0x{o:04X}={n}" for o, n in sorted(got.items())))
    LEDGER.ok(c.name_for("GAME_CMSG", 0x0028) == "?"
              and c.name_for("GAME_CMSG", 0x1234) == "?"
              and c.name_for("NO_SUCH_CHANNEL", 1) == "?",
              "and anything unnamed stays '?' rather than borrowing a label",
              "0x0028 is witnessed but unexplained; a plausible name would be a "
              "guess entering the catalog as fact")

    # The names must not have moved a single field, or they would change decoding.
    base = json.load(open(os.path.join(repo, "schema", "messages.json"),
                          encoding="utf-8"))["channels"]["GAME_CMSG"]["messages"]
    over = json.load(open(os.path.join(repo, "schema", "overrides.json"),
                         encoding="utf-8"))["channels"].get("GAME_CMSG", {})
    moved = [k for k, v in over.items()
             if "name" in v and k in base and v["fields"] != base[k]["fields"]]
    LEDGER.ok(not moved,
              "a named entry copies its layout verbatim and changes no field",
              f"moved: {moved}" if moved else
              f"{len(over)} GAME_CMSG override(s), layouts untouched -- the names "
              f"record what a message MEANS, which its marshalling types cannot say")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
