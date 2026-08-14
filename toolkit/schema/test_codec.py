"""Validate the codec against bytes the real Guild Wars client actually sent.

Synthetic round-trips only prove the codec agrees with itself. The capture from
build 38797 is ground truth, so it is the primary fixture here: if the schema's
field layout is wrong, the real frame will not decode cleanly to its end.
"""

import binascii
import collections
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

# Floor 29, RE-MEASURED from a green run on 2026-08-14: section 1 contributes exactly
# one whatever the vault holds (its three branches each score a single verdict), then
# 2 + 5 + 3 for sections 2, 3 and 4, 5 for section 5, and 13 under section 6's heading
# (its own round trip plus the catalog block that prints beneath it). It was 18 before
# the string16 sections landed, then 27 -- and 27 was STALE: the run had grown to 28
# without the floor following, so the file carried a check of slack, which is the
# state this floor exists to prevent. The arithmetic above is now counted from the
# output rather than reasoned about, because the old comment's own sum (1+2+5+3+5+4+7)
# was the number that drifted.
# This file is the reason checks.py exists — it once printed ALL CHECKS PASSED with
# its capture glob matching nothing — so the floor is what makes a section going
# quiet a failure rather than a shorter list of passes. Section 6 needs the live
# captures and declares four skips without them, which puts a vault-less run four
# below the floor and therefore RED: ArenaNet's own bytes are the only oracle for
# the round trip, and a run that could not consult them has not checked it.
LEDGER = checks.Ledger("codec vs captured bytes", floor=29)
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

    print("\n5. string16 carries CODE UNITS, not text (no vault needed)")
    # `string16` decoded with errors="replace" until 2026-08-11. GW's encoded
    # names are not text -- they are code units that index string tables, and many
    # land in the UTF-16 surrogate range -- so "replace" turned each one into
    # U+FFFD and the message could never be re-encoded to the bytes it arrived as.
    # Section 6 measures that against ArenaNet's own traffic; this section is the
    # half that runs on a bare machine, and it holds the three controls that
    # separate "carries raw code units" from two implementations that only look
    # like it.
    #
    # Fixture: GAME_SMSG 0x0054 is [msg_header, dword, string16] -- a neighbouring
    # field to mutate and nothing else to confuse the picture. It is also one of
    # the twelve opcodes that really failed (2 of its messages).
    STR_OP = 0x0054
    LONE = "\udE01"                      # one low surrogate, as one code unit
    lone_msg = c.encode("GAME_SMSG", STR_OP, [0x11111111, LONE])
    got, consumed, err = c.decode_stream("GAME_SMSG", lone_msg)
    round2 = (c.encode("GAME_SMSG", STR_OP, list(got[0][1])[1:],
                       header_value=got[0][1][0]) if got else b"")
    ok &= check("a lone surrogate survives decode and re-encodes to the same bytes",
                consumed == len(lone_msg) and err is None and len(got) == 1
                and got[0][1][2] == LONE and round2 == lone_msg,
                f"{err or ''} decoded={got[0][1][2]!r} identical={round2 == lone_msg}"
                if got else "nothing decoded")

    # The second bug, which the first one was hiding. A valid surrogate PAIR
    # decodes to ONE Python character while occupying TWO code units, so the old
    # `len(s)` wrote a count two bytes short of the data it then appended -- and
    # that is a desync, not a lossy field: the NEXT message frames from inside
    # this one. It could not fire while decode was "replace" (U+FFFD is one unit
    # and one character), so it was unreachable until the real fix exposed it.
    # The check is therefore on the FOLLOWING message, which is where the damage
    # actually lands.
    ASTRAL = "\U0001F600"                # one character, two code units
    pair = c.encode("GAME_SMSG", STR_OP, [0x22222222, ASTRAL])
    tail = c.encode("GAME_SMSG", STR_OP, [0x33333333, "ok"])
    both, consumed2, err2 = c.decode_stream("GAME_SMSG", pair + tail)
    declared = struct.unpack_from("<H", pair, 6)[0]
    ok &= check("an astral character counts as TWO units, so the next message "
                "still frames",
                declared == 2 and len(pair) == 12 and consumed2 == len(pair + tail)
                and err2 is None and len(both) == 2
                and both[1][1][1] == 0x33333333,
                f"declared={declared} units, {len(pair)} B, consumed "
                f"{consumed2}/{len(pair + tail)}, {len(both)} messages"
                + (f", {err2}" if err2 else ""))

    # str(bytes) is "b'AB'", which encodes happily and puts the repr on the wire.
    # A caller holding raw code units would have been silently wrong.
    try:
        c.encode("GAME_SMSG", STR_OP, [0, b"\x01\xDE"])
        refused = False
    except ValueError:
        refused = True
    ok &= check("encode refuses bytes rather than encoding their repr", refused,
                "ValueError" if refused else "bytes were accepted")

    # CONTROL B, and it is the one that catches the sabotage the round-trip
    # cannot. An implementation that stashes the original bytes ON THE VALUE and
    # replays them at encode round-trips every message it ever decoded, byte for
    # byte, and survives the mutation control below -- mutating a neighbouring
    # field leaves the string's value object and its stash untouched. What it
    # cannot do is encode a value it never decoded. So: build the value from raw
    # code units, never having seen it on a wire, and require the exact bytes out.
    # The naive encoder raising on the same input is what makes this discriminate
    # rather than merely pass.
    BUILT = "".join(chr(u) for u in (0x2186, 0xDE01, 0x0041))
    try:
        BUILT.encode("utf-16-le")
        naive_raised = False
    except UnicodeEncodeError:
        naive_raised = True
    built_msg = c.encode("GAME_SMSG", STR_OP, [0x44444444, BUILT])
    want = b"\x86\x21\x01\xDE\x41\x00"
    ok &= check("a value we CONSTRUCTED from code units encodes to exactly them",
                naive_raised and built_msg[6:8] == b"\x03\x00"
                and built_msg[8:] == want,
                f"naive encoder raised={naive_raised}, count="
                f"{struct.unpack_from('<H', built_msg, 6)[0]}, "
                f"payload={binascii.hexlify(built_msg[8:]).decode()}")

    # CONTROL C: the message-level byte cache. Decode stashes the whole plaintext
    # and encode replays it -- round-trip 100%, U+FFFD zero, and completely
    # broken, because it discards anything the caller changed. Mutate the
    # neighbour, re-encode, and DECODE THE RESULT: both halves must hold, and
    # asserting only the string half is what let this survive an earlier draft of
    # the criterion.
    dec = c.decode_stream("GAME_SMSG", lone_msg)[0][0][1]
    mutated = list(dec)[1:]
    mutated[0] = 0x55555555
    re_enc = c.encode("GAME_SMSG", STR_OP, mutated, header_value=dec[0])
    back = c.decode_stream("GAME_SMSG", re_enc)[0][0][1]
    cache_sabotage = lone_msg                       # what a byte cache emits
    ok &= check("mutating a neighbour moves that field and leaves the string "
                "intact",
                back[1] == 0x55555555 and back[2] == LONE
                and re_enc != cache_sabotage,
                f"dword=0x{back[1]:08X} string={back[2]!r} "
                f"differs-from-cache={re_enc != cache_sabotage}")

    print("\n6. the whole live corpus re-encodes to ArenaNet's own bytes")
    # THE CRITERION, and the reason this section is worth its runtime: every
    # GAME_SMSG in every decrypted live connection must re-encode to the exact
    # bytes ArenaNet sent. Before the string16 fix this was 133 failures over
    # 22,524 messages, and the failing set was EXACTLY the set whose decoded
    # values carried U+FFFD -- one defect, one number, in twelve opcodes, none
    # differing in length. Both figures are measured by this reader, from the
    # same loop, so the invariant below can fail in either direction.
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "authsrv"))
    import tape  # noqa: E402  -- cross-package, the repo has no packages
    live = vaultpath.require_dir(
        "captures", "live",
        why="ArenaNet's own bytes are the only oracle for this round trip")
    caps = sorted(d for d in os.listdir(live)
                  if glob.glob(os.path.join(live, d, "game-*.jsonl")))
    if not caps:
        LEDGER.skip("the live corpus re-encodes byte-identically",
                    f"no decrypted game channels under {live}")
        LEDGER.skip("no decoded value carries U+FFFD", "same")
        LEDGER.skip("the failure set and the U+FFFD set are the same set", "same")
        LEDGER.skip("0x004C and 0x0161 specifically", "same")
    else:
        total = conns = 0
        fails = collections.Counter()
        replaced = collections.Counter()
        seen = collections.Counter()
        lendiff = 0
        for cap in caps:
            d = os.path.join("captures", "live", cap)
            for row in tape.channel_files(d):
                _info, events = tape.load_tape(d, row["connection"])
                blob = b"".join(b for _t, b in events)
                msgs, consumed, err = c.decode_stream_at("GAME_SMSG", blob, 0)
                conns += 1
                for i, (off, op, vals) in enumerate(msgs):
                    end = msgs[i + 1][0] if i + 1 < len(msgs) else consumed
                    total += 1
                    seen[op] += 1
                    if any(isinstance(x, str) and "�" in x for x in vals):
                        replaced[op] += 1
                    try:
                        enc = c.encode("GAME_SMSG", op, list(vals)[1:],
                                       header_value=vals[0])
                    except Exception:
                        fails[op] += 1
                        continue
                    if enc != blob[off:end]:
                        fails[op] += 1
                        if len(enc) != len(blob[off:end]):
                            lendiff += 1
        nfail, nrep = sum(fails.values()), sum(replaced.values())
        print(f"  {conns} connections, {total} GAME_SMSG, "
              f"{nfail} round-trip failures, {nrep} values carrying U+FFFD")
        ok &= check("every live GAME_SMSG re-encodes byte-identically",
                    total > 0 and nfail == 0,
                    f"{total - nfail}/{total}" + (
                        f" — failing: "
                        f"{ {f'0x{k:04X}': v for k, v in sorted(fails.items())} }"
                        if fails else
                        f" over {conns} connections; was 133/22,524 before the "
                        f"string16 fix, in twelve opcodes"))
        ok &= check("no decoded value carries U+FFFD", nrep == 0,
                    f"{nrep}" + (
                        f" — {  {f'0x{k:04X}': v for k, v in sorted(replaced.items())} }"
                        if replaced else " (a replacement char is an unrecoverable "
                        "code unit, not a rendering nicety)"))
        # The invariant, which is the honest form of "one defect, one number": the
        # two sets were identical before the fix and must stay identical after.
        # It can fail in BOTH directions -- a re-encode failure with no U+FFFD is
        # a different bug, and a U+FFFD with no failure would mean the round trip
        # is not actually comparing bytes.
        ok &= check("the round-trip failures and the U+FFFD values are the SAME "
                    "set, per opcode",
                    dict(fails) == dict(replaced),
                    f"fails={ {hex(k): v for k, v in fails.items()} } "
                    f"ffd={ {hex(k): v for k, v in replaced.items()} }"
                    if dict(fails) != dict(replaced) else
                    "both empty now; both were the same 12-opcode multiset before")
        # Named because they are the two the study document quotes, and a
        # regression that spared them would still be a regression.
        ok &= check("0x004C and 0x0161 are whole, and were the worst two",
                    fails.get(0x004C, 0) == 0 and fails.get(0x0161, 0) == 0
                    and seen.get(0x004C, 0) > 0 and seen.get(0x0161, 0) > 0,
                    f"0x004C {seen.get(0x004C, 0) - fails.get(0x004C, 0)}/"
                    f"{seen.get(0x004C, 0)} (was 0/40), "
                    f"0x0161 {seen.get(0x0161, 0) - fails.get(0x0161, 0)}/"
                    f"{seen.get(0x0161, 0)} (was 363/394)")

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
    #
    # Scoped to every channel, not just GAME_CMSG. It checked GAME_CMSG alone until
    # 2026-08-10, which was fine while only that channel had names -- and stopped being
    # fine the moment GAME_SMSG 0x01A5 got one. A check whose stated principle is
    # "a named entry changes no field" must look everywhere that principle applies, or
    # the first exception to it arrives unnoticed.
    #
    # TWO entries are allowed to differ, and they are named here rather than filtered
    # silently: GAME_SMSG 421's layout correction (38 -> 39 bytes, a trailing byte our
    # import missed) came from the client's own cmds[] table, predates the name by
    # days, and is now independently corroborated by ArenaNet's stream -- all three
    # tapes put the next message exactly 39 bytes later. Adding a name did not move it.
    #
    # GAME_SMSG 146 (COMPASS_PING, 2026-08-14) is the same shape and is deliberately
    # held to the same test: its correction (10 -> 12 bytes, a trailing `word` our
    # import missed) also came from the client's own cmds[] table -- cmd 0x204 is a
    # 2-byte unsigned int, and the MsgFormatRecv entry statically holds count=4 -- and
    # it, too, was in overrides.json BEFORE the name arrived, which is the property
    # this check actually cares about: the name moved nothing. Where it is WEAKER than
    # 421 and the difference is stated rather than glossed: 421's correction is
    # corroborated on the wire and 146's CANNOT be, because 0x0092 occurs 0 times in
    # all 22,524 live GAME_SMSG. It rests on the binary alone. If a capture ever
    # carries one, that is the check this exemption is waiting for.
    LAYOUT_FIXED = {("GAME_SMSG", "421"), ("GAME_SMSG", "146")}
    all_base = json.load(open(os.path.join(repo, "schema", "messages.json"),
                              encoding="utf-8"))["channels"]
    all_over = json.load(open(os.path.join(repo, "schema", "overrides.json"),
                              encoding="utf-8"))["channels"]
    named_over = [(ch, k) for ch, msgs in all_over.items()
                  for k, v in msgs.items() if "name" in v]
    # A NAME-ONLY row carries no `fields` at all, and that satisfies this check in its
    # strongest form: it cannot move a layout it does not contain. `shotlabel --merge`
    # writes such rows from a screen reading, which learns what a message DRAWS and
    # nothing about its marshalling, so carrying a copied layout would be the schema
    # asserting something the evidence never touched.
    moved = [(ch, k) for ch, k in named_over
             if (ch, k) not in LAYOUT_FIXED
             and k in all_base.get(ch, {}).get("messages", {})
             and "fields" in all_over[ch][k]
             and all_over[ch][k]["fields"]
             != all_base[ch]["messages"][k]["fields"]]
    # ...but "no fields" must mean NO LAYOUT, not "fields under another key". A row that
    # renamed an opcode while flipping `variable_length` or `declared_unpack_size` would
    # pass the check above by having no `fields`, which is the loophole the shape invites.
    LAYOUT_KEYS = {"fields", "variable_length", "declared_unpack_size", "table"}
    sneaky = [(ch, k) for ch, k in named_over
              if "fields" not in all_over[ch][k]
              and (set(all_over[ch][k]) & LAYOUT_KEYS)]
    LEDGER.ok(not sneaky,
              "a name-only override carries no layout key at all",
              f"{sneaky}" if sneaky else
              f"{sum(1 for ch, k in named_over if 'fields' not in all_over[ch][k])} "
              f"name-only row(s), none of which touch a layout field")
    LEDGER.ok(not moved,
              "a named entry copies its layout verbatim and changes no field",
              f"moved: {moved}" if moved else
              f"{len(named_over)} named override(s) across "
              f"{len({ch for ch, _k in named_over})} channel(s), layouts untouched "
              f"apart from the declared exception -- the names record what a message "
              f"MEANS, which its marshalling types cannot say")

    # ...and the exemption list is checked in the OTHER direction too, because an
    # allowlist that only ever grows is how this check would quietly stop working. A
    # row for an entry that no longer differs is inert today and silently re-permits a
    # layout move the day someone edits that entry -- test_dispatch.py's
    # DROPPED_ON_PURPOSE has the same rule for the same reason. Every exemption must
    # still be DOING something.
    stale_fixed = [(ch, k) for ch, k in sorted(LAYOUT_FIXED)
                   if k not in all_over.get(ch, {})
                   or "name" not in all_over[ch][k]
                   or "fields" not in all_over[ch][k]
                   or all_over[ch][k]["fields"]
                   == all_base.get(ch, {}).get("messages", {}).get(k, {}).get("fields")]
    LEDGER.ok(not stale_fixed,
              "and every declared layout exception is still load-bearing",
              f"stale: {stale_fixed}" if stale_fixed else
              f"{len(LAYOUT_FIXED)} exemption(s), each still a named entry whose "
              f"layout genuinely differs from the imported catalog -- a row that "
              f"stopped differing would re-permit a move on that entry unnoticed")

    codec_named = codec_mod.Codec()
    LEDGER.ok(codec_named.name_for("GAME_SMSG", 0x01A5) == "GAME_SERVER_TRANSFER",
              "and GAME_SMSG has its first name at all",
              "487 layouts, 0 names until 0x01A5 -- earned the same way the GAME_CMSG "
              "seven were, from a witness not consulted to make the claim: its three "
              "tail ids equal the NEXT connection's own VERSION frame, 12/12 fields "
              "across three recorded transitions")

    # The 2026-08-10 naming pass. Spot-check the load-bearing ones resolve rather
    # than the whole set: this check is that the entries are wired into the codec,
    # not that any particular reading is right -- test_smsgnames.py is where the
    # claims themselves are put at risk against the wire.
    SMSG_NAMED = {0x001E: "WORLD_SIMULATION_TICK", 0x0020: "WORLD_CREATE_AGENT",
                  0x0021: "WORLD_REMOVE_AGENT", 0x0029: "AGENT_MOVE_TO_POINT",
                  0x00F0: "AGENT_INITIAL_STATUS", 0x00F1: "AGENT_UPDATE_STATUS"}
    wrong = {f"0x{op:04X}": codec_named.name_for("GAME_SMSG", op)
             for op, want in SMSG_NAMED.items()
             if codec_named.name_for("GAME_SMSG", op) != want}
    LEDGER.ok(not wrong,
              "and the 2026-08-10 GAME_SMSG names resolve through the codec",
              f"mismatched: {wrong}" if wrong else
              f"{len(SMSG_NAMED)} spot-checked of 20 added; the catalog went from 1 "
              f"named GAME_SMSG opcode to 21, and 0x00F0/0x00F1 changed their NOUN "
              f"from 'effects' to the client's own m_status")

    over_smsg = all_over.get("GAME_SMSG", {})
    unconfident = [k for k, v in over_smsg.items()
                   if "name" in v and k != "421"
                   and v.get("name_confidence") not in ("high", "medium")]
    LEDGER.ok(not unconfident,
              "every GAME_SMSG name declares the confidence it earned",
              f"missing/!={unconfident}" if unconfident else
              "each carries name_confidence, and it is the POST-refutation value -- "
              "a second reader re-derived each proposal and struck four headline "
              "citations and two verdicts, so filing confidence is not self-assessed")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
