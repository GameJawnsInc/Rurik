"""GAME_CMSG names, against ArenaNet's own client traffic in two live sessions.

On 2026-08-11 GAME_CMSG went from SEVEN names of 194 to sixteen. The seven were
all earned by labelled runs against OUR OWN server (`labelrun.py`): an operator
is told to do one thing, and the opcode that appears is named for it. This corpus
is different in kind -- it is ArenaNet's own server, and the session was narrated
afterwards, so the times can be matched to what a human actually did. That makes
it an independent witness against the seven rather than more of the same, and one
of them did not survive contact with it.

THE HEADLINE, and it is a hole in our server rather than a naming detail.
`0x0046` USE_SKILL was named from a Necromancer casting on our server. A whole
narrated Ranger session -- two Power Shots, both visible in the server's own
skill-activated messages -- sent **zero** `0x0046`. Attack skills leave on
`0x0027` instead, and our server has no dispatch arm for it at all: the only
mention of 0x0027 anywhere in `authsrv.py` is a comment about a GAME_SMSG of the
same number in a different channel. So every physical attack skill a player
presses lands on the silent-ignore path. The name USE_SKILL is not wrong; it is
half the story, and the missing half is the entire physical side of the game.

WHAT THIS FILE ASSERTS. Properties of ArenaNet's recorded traffic, with ONE
deliberate exception at the end: that our server actually dispatches both halves.
That check is here rather than elsewhere because it is the change this corpus
forced, and separating a finding from the fix it demanded is how a fix gets
quietly reverted. Claims resting on the binary (send-site addresses, assert text)
are NOT re-checked here -- that is `asserts.py`'s ground and needs the vaulted
build.

A BUG THIS FILE EXISTS PARTLY TO PIN. The first reader of this corpus fed the
AUTH connection through the GAME_CMSG tables and produced two confident
"opcodes", 0x0001 and 0x0005, that are not GAME_CMSG messages at all. They
reached a naming pass as real findings. Decoding the wrong channel does not
error, it invents -- so section 1 checks the channel split directly.

AND SECTION 1 WAS PASSING WHILE THE BUG WAS STILL LIVE, which is the reason
sections 1b and 1c exist. `cmsgstream.timed()` accepted a `channel` argument,
documented that it refused to guess, and then chose the catalog from DIRECTION
alone -- so `channel="auth"` handed the auth stream to GAME_CMSG anyway. Section
1 read `(2 messages there)` off that mis-decode and printed PASS, because its
assertion was about the GAME connection only and the auth half was prose. The
whole auth channel -- 78 c2s and 91 s2c messages over four live connections, 22
opcodes -- was unreadable by this repo and nothing was red.

So 1b is the measurement the fix earns, stated in the one form a wrong catalog
cannot satisfy: with the right tables the four auth connections frame to
residual **0** in both directions, 8 of 8, and with the GAME tables **0 of 8**
survive, each dying within 3-9 bytes. Both halves are asserted. The first alone
would also be true of a decoder that framed anything at all -- and section 2 of
the sabotage log proves that is not hypothetical, because a decoder patched to
swallow its own framing errors passes 1b's first half and reddens only its
second.
"""
import ast
import math
import contextlib
import io
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import capgaps  # noqa: E402
import checks  # noqa: E402
import cmsgstream  # noqa: E402
import vaultpath  # noqa: E402

NECRO = "20260807T143055"
RANGER = "20260810T235916"

# Every live capture in the vault that recorded an AUTH connection: four of the
# six stamps. The other two (20260807T135532, 20260807T141736) hold no channel
# file at all and would contribute nothing but a zero to every denominator.
AUTH_STAMPS = ("20260807T124912", "20260807T133758", NECRO, RANGER)

# MEASURED 2026-08-13 over those four connections with the catalogs corrected.
# Written here as literals rather than computed from what the decoder returned,
# because a set compared against itself is not a check: this is the inventory
# the fix unlocked, and it moves if the framing or the corpus changes.
AUTH_C2S_OPCODES = {0x00, 0x01, 0x02, 0x09, 0x0A, 0x0E,
                    0x20, 0x21, 0x23, 0x29, 0x35, 0x38}
AUTH_S2C_OPCODES = {0x00, 0x01, 0x03, 0x07, 0x09,
                    0x11, 0x14, 0x16, 0x17, 0x26}
AUTH_C2S_BYTES = 4075
AUTH_S2C_BYTES = 3939
AUTH_C2S_MESSAGES = 78
AUTH_S2C_MESSAGES = 91

USE_SKILL = 0x0046
ATTACK_SKILL = 0x0027
ATTACK = 0x0026
TARGET_SELECT = 0x00C1
MOVE_SET_HEADING = 0x003D
MOVE_TO_COORD = 0x003E
MOVE_CANCEL = 0x0047
EQUIP_COLOR = 0x0084
SKILL_ACTIVATED = 0x00E3          # GAME_SMSG
STATUS = 0x00F1                   # GAME_SMSG; bit 0x10 is CHAR_STATUS_DEAD

# MEASURED from real green runs, never guessed: the first version declared 12
# and ran 10, and the floor guard caught it rather than letting a short run
# print as a pass. 11 since the server-dispatch check was added, 16 since
# sections 1b and 1c made the auth channel readable.
# 2026-09-28 (CASTAI-Z1, the cms lane): 20 -- section 0's two bare checks on the
# gap set-aside (so a BARE run is 2, below the floor, where it used to be 0),
# section 1's refusal of the short wrong-catalog decode, and section 0b's
# whole-corpus audit. Set from the green run.
LEDGER = checks.Ledger("GAME_CMSG names vs ArenaNet's own client", floor=20)

GAPPED_STAMP = "20260928T103123"
GAPPED_CONN = "10.0.0.210:65009->98.95.137.136:80"
# OBSERVED 2026-09-28: the c2s half of the one gapped connection, which its manifest
# declares WHOLE, frames to 192 GAME_CMSG messages. Exact, on that one tape.
GAPPED_CONN_C2S_MESSAGES = 192


def _fake_capture(root, stamp, conns, manifest):
    """A synthetic capture: `conns` is {port: [(seq, payload), ...]} of S2C segments
    from 6.7.8.9:80 to 1.2.3.4:<port>, each with a keyed game channel file."""
    cap = os.path.join(root, stamp)
    os.makedirs(cap)
    with open(os.path.join(cap, "wire.jsonl"), "w", encoding="utf-8") as fh:
        for port, segs in conns.items():
            for i, (seq, payload) in enumerate(segs):
                fh.write(json.dumps({"kind": "wire", "dir": "s2c", "src": "6.7.8.9",
                                     "sport": 80, "dst": "1.2.3.4", "dport": port,
                                     "seq": seq, "t": 0.1 * (i + 1),
                                     "payload": payload.hex()}) + "\n")
    for port in conns:
        with open(os.path.join(cap, f"game-1.2.3.4_{port}-to-6.7.8.9_80.jsonl"), "w",
                  encoding="utf-8") as fh:
            fh.write(json.dumps({"kind": "session_key", "arc4_key": "00" * 20}) + "\n")
    with open(os.path.join(cap, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump({"report": {"connections": manifest}}, fh)
    return cap


def section_gaps_bare():
    """0. THE GAP SET-ASIDE, on synthetic captures (runs on a bare machine).

    `_streams` used to discard `reassemble`'s hole list and frame straight through.
    Now: a hole the manifest declares, IN THE DIRECTION READ, is set aside by name;
    any other hole is loud. Every arm here can go red."""
    seed = (0x1601).to_bytes(2, "little") + bytes(20)          # SERVER_SEED, then cipher
    whole = [(1000, seed + bytes(8)), (1030, bytes(10))]          # 40 bytes, no hole
    holed = [(1000, seed + bytes(8)), (1034, bytes(10))]          # a 4-byte hole at 30
    out = io.StringIO()
    with tempfile.TemporaryDirectory() as td:
        # port 5: s2c holed AND declared; port 7: s2c whole, only its c2s declared
        cap1 = _fake_capture(td, "20990101T000001", {5: holed, 7: whole}, [
            {"connection": "1.2.3.4:5->6.7.8.9:80", "gaps": {"s2c": [[30, 4]]}},
            {"connection": "1.2.3.4:7->6.7.8.9:80", "gaps": {"c2s": [[0, 5]]}}])
        # port 6: s2c holed, NOT declared
        cap2 = _fake_capture(td, "20990101T000002", {6: holed}, [
            {"connection": "1.2.3.4:6->6.7.8.9:80", "gaps": {}}])
        # port 8: s2c holed, declared with the WRONG hole
        cap3 = _fake_capture(td, "20990101T000003", {8: holed}, [
            {"connection": "1.2.3.4:8->6.7.8.9:80", "gaps": {"s2c": [[30, 5]]}}])
        into = []
        with contextlib.redirect_stdout(out):
            got = [c for c, _p, _h, _m in cmsgstream._streams(cap1, "s2c", "game", into)]
        printed = out.getvalue()
        loud = {}
        for name, cap in (("undeclared", cap2), ("mismatch", cap3),
                          ("known-bad: declaration ignored", cap1)):
            try:
                list(cmsgstream._streams(cap, "s2c", "game",
                                         honour_declared=(cap is not cap1)))
                loud[name] = None
            except cmsgstream.StreamRefused as ex:
                loud[name] = str(ex)
        ref = (cmsgstream.refuses(cap1, "1.2.3.4:5->6.7.8.9:80"),
               cmsgstream.refuses(cap1, "1.2.3.4:7->6.7.8.9:80"))
        new_ok, _why = capgaps.audit(into, [cap1], cmsgstream.refuses)
    LEDGER.ok(got == ["1.2.3.4:7->6.7.8.9:80"]
              and into == [{"capture": "20990101T000001",
                            "connection": "1.2.3.4:5->6.7.8.9:80",
                            "gaps": {"s2c": [[30, 4]]}}]
              and "SET ASIDE 20990101T000001 1.2.3.4:5->6.7.8.9:80" in printed
              and ref == (True, False) and not new_ok,
              "cmsgstream sets aside ONLY a hole its manifest declares in the direction "
              "read, prints it by name and records it; a c2s-only declaration leaves the "
              "s2c read; the set-aside one is still refused; and a declared gap "
              "KNOWN_GAPPED does not name keeps the audit RED",
              f"yielded {got}; set aside {into}; refuses (declared, whole) = {ref}; "
              f"audit of an unnamed gap ok={new_ok}")
    LEDGER.ok(all(loud.values())
              and "1.2.3.4:6->6.7.8.9:80" in loud["undeclared"]
              and "1.2.3.4:8->6.7.8.9:80" in loud["mismatch"]
              and "1.2.3.4:5->6.7.8.9:80" in loud["known-bad: declaration ignored"],
              "and every OTHER hole is LOUD, naming its connection: an undeclared one, a "
              "declaration the reassembly does not reproduce, and (KNOWN-BAD) the "
              "declared one itself once its declaration is not honoured",
              "; ".join(f"{k}: {v}" for k, v in loud.items()))


def section_gaps_corpus():
    """0b. The whole live corpus through `timed`, both directions of the game channel:
    nothing refused, the s2c set-aside audited against the manifests and KNOWN_GAPPED,
    no c2s set-aside at all, and the gapped connection's whole c2s half still read."""
    live = str(vaultpath.require_dir("captures", "live"))
    caps = [os.path.join(live, s) for s in sorted(os.listdir(live))
            if os.path.isfile(os.path.join(live, s, "wire.jsonl"))]
    aside = {"s2c": [], "c2s": []}
    rows, refused = {"s2c": 0, "c2s": 0}, None
    z_c2s = None
    try:
        for cap in caps:
            stamp = os.path.basename(cap)
            for d in ("s2c", "c2s"):
                got = cmsgstream.timed(stamp, d, "game", set_aside=aside[d])
                rows[d] += len(got)
                if stamp == GAPPED_STAMP and d == "c2s":
                    z_c2s = sum(1 for _t, c, _o, _v in got if c == GAPPED_CONN)
    except cmsgstream.StreamRefused as ex:
        refused = str(ex)
    ok, why = capgaps.audit(aside["s2c"], caps, cmsgstream.refuses)
    bad_ok, _ = capgaps.audit(aside["s2c"], caps, lambda _c, _n: False)
    c2s_declared = {(os.path.basename(c), n) for c in caps
                    for n in cmsgstream.declared_in(c, "c2s")}
    LEDGER.ok(refused is None and ok and not bad_ok
              and len(aside["s2c"]) == len(capgaps.KNOWN_GAPPED)
              and aside["c2s"] == [] and c2s_declared == set()
              and z_c2s == GAPPED_CONN_C2S_MESSAGES,
              "timed() over every live capture: nothing refused; the s2c set-aside is "
              "EXACTLY capgaps.KNOWN_GAPPED, still refused (KNOWN-BAD: an audit told it "
              "decodes goes red); nothing set aside in c2s, where no manifest declares a "
              "gap; and the gapped connection's whole c2s half is read",
              f"{len(caps)} captures, {rows['s2c']} s2c / {rows['c2s']} c2s rows; "
              f"refused: {refused}; {why}; c2s declared {sorted(c2s_declared)}; "
              f"{GAPPED_STAMP} {GAPPED_CONN} c2s {z_c2s} messages "
              f"(expected {GAPPED_CONN_C2S_MESSAGES})")


def main():
    section_gaps_bare()
    try:
        vaultpath.require_dir()
    except (Exception, SystemExit) as ex:                                    # pragma: no cover
        LEDGER.skip("every vault section (all but section 0)", f"no vault: {ex}")
        return LEDGER.verdict()

    try:
        c2s = {s: cmsgstream.timed(s, "c2s") for s in (NECRO, RANGER)}
        s2c = {s: cmsgstream.timed(s, "s2c") for s in (NECRO, RANGER)}
    except Exception as ex:                                    # pragma: no cover
        LEDGER.skip("the whole file", f"captures unreadable: {ex}")
        return LEDGER.verdict()

    section_gaps_corpus()

    def ops(stamp, op, side=None):
        return [(t, v) for t, _c, o, v in (side or c2s)[stamp] if o == op]

    total = sum(len(v) for v in c2s.values())
    LEDGER.ok(total > 800 and all(len(v) > 300 for v in c2s.values()),
              "both live sessions' CLIENT half decodes",
              f"{total} GAME_CMSG messages ({', '.join(str(len(v)) for v in c2s.values())}), "
              f"{len({o for v in c2s.values() for _t, _c, o, _v in v})} distinct opcodes. "
              f"None of this was readable until the 0x8000 the client ORs into every "
              f"game-channel opcode was masked off -- without it, not one message decodes")

    # ---- 1. the channel split, which is where fictitious opcodes came from ----
    # `catalog="GAME_CMSG"` is DELIBERATE and it is the whole point of this line.
    # Until 2026-08-13 no override was needed, because `timed()` fed the auth
    # stream to GAME_CMSG whatever `channel` said -- so this control got its
    # mis-decode for free from the very defect it was meant to guard against, and
    # the day that defect was fixed the check would have gone on passing for an
    # entirely new reason: `0x0001/0x0005 absent from the game channel` is still
    # true when the auth stream is read correctly, and the detail line would have
    # gone on calling 78 correctly-decoded AUTH_CMSG messages evidence of
    # invention. So the mis-decode is now ASKED FOR, and the claim that it
    # invents is ASSERTED rather than narrated.
    # 2026-09-28 (CASTAI-Z1, the cms lane): `timed()` no longer returns a short
    # decode's prefix -- it raises `StreamRefused` naming the connection -- so the
    # mis-decode is read where it is still REPORTED, `frame_report`, from the same
    # one `_streams` path and the same `decode_stream_at` call, i.e. the same
    # messages `timed` used to return. The 0x0001/0x0005 literals are asserted on
    # the same stream as before; the refusal is asserted beside them.
    mis_rows = cmsgstream.frame_report(RANGER, "c2s", "auth", catalog="GAME_CMSG")
    mis_ops = {o for r in mis_rows for o in r["opcodes"]}
    mis_n = sum(r["messages"] for r in mis_rows)
    try:
        cmsgstream.timed(RANGER, "c2s", channel="auth", catalog="GAME_CMSG")
        refused = None
    except cmsgstream.StreamRefused as ex:
        refused = str(ex)
    real = sum(r["messages"] for r in cmsgstream.frame_report(RANGER, "c2s", "auth"))
    game_ops = {o for _t, _c, o, _v in c2s[RANGER]}
    LEDGER.ok(0x0001 not in game_ops and 0x0005 not in game_ops
              and {0x0001, 0x0005} <= mis_ops,
              "the AUTH channel is not decoded as GAME_CMSG",
              f"0x0001/0x0005 absent from the game channel's {len(game_ops)} opcodes, "
              f"and PRESENT ({sorted(hex(o) for o in mis_ops)}) when the same auth "
              f"stream is deliberately run through the GAME_CMSG tables -- {mis_n} "
              f"messages before the framing dies, on a connection that really holds "
              f"{real}. Decoding the wrong channel invents rather than errors")
    LEDGER.ok(refused is not None and "framed" in refused and mis_n < real,
              "and timed() REFUSES that short decode instead of returning its prefix",
              f"StreamRefused: {refused}. Until 2026-09-28 timed() discarded "
              f"decode_stream_at's error and handed back the {mis_n} invented messages "
              f"as if they were the stream")

    # ---- 1b. the AUTH channel, which was unreadable until 2026-08-13 ----------
    # Two-sided on purpose. "The auth streams frame cleanly" is satisfied by any
    # decoder tolerant enough to swallow its own errors; "the GAME tables cannot
    # frame them" is what makes the first half a statement about the catalog.
    clean = {}                 # (stamp, dir) -> rows, right catalog
    wrong = {}                 # (stamp, dir) -> rows, GAME catalog on the same bytes
    for stamp in AUTH_STAMPS:
        for want_dir in ("c2s", "s2c"):
            clean[(stamp, want_dir)] = cmsgstream.frame_report(
                stamp, want_dir, "auth")
            wrong[(stamp, want_dir)] = cmsgstream.frame_report(
                stamp, want_dir, "auth",
                catalog=cmsgstream.CATALOGS[("game", want_dir)])

    ok_rows = [r for rows in clean.values() for r in rows]
    n_c2s = sum(r["messages"] for k, rows in clean.items() if k[1] == "c2s"
                for r in rows)
    n_s2c = sum(r["messages"] for k, rows in clean.items() if k[1] == "s2c"
                for r in rows)
    b_c2s = sum(r["consumed"] for k, rows in clean.items() if k[1] == "c2s"
                for r in rows)
    b_s2c = sum(r["consumed"] for k, rows in clean.items() if k[1] == "s2c"
                for r in rows)
    n_clean = sum(1 for r in ok_rows if r["residual"] == 0 and r["error"] is None)
    LEDGER.ok(len(ok_rows) == 8 and n_clean == 8
              and (n_c2s, n_s2c) == (AUTH_C2S_MESSAGES, AUTH_S2C_MESSAGES)
              and (b_c2s, b_s2c) == (AUTH_C2S_BYTES, AUTH_S2C_BYTES),
              "the AUTH catalogs account for every byte of all four auth connections",
              f"{n_clean}/{len(ok_rows)} connection-directions frame to residual 0: "
              f"{n_c2s} c2s / {b_c2s} B and {n_s2c} s2c / {b_s2c} B. Residual 0 over a "
              f"whole decrypted stream is a claim the bytes can refute -- every "
              f"message's declared shape has to consume exactly its own bytes all the "
              f"way to the last one. Expected {AUTH_C2S_MESSAGES}/{AUTH_C2S_BYTES} and "
              f"{AUTH_S2C_MESSAGES}/{AUTH_S2C_BYTES}")

    bad_rows = [r for rows in wrong.values() for r in rows]
    survivors = [r for r in bad_rows if r["residual"] == 0 and r["error"] is None]
    died_by = [r["consumed"] for r in bad_rows]
    LEDGER.ok(len(bad_rows) == 8 and not survivors and max(died_by) <= 9,
              "and the GAME catalogs cannot frame a single one of them",
              f"{len(bad_rows) - len(survivors)}/8 die, every one within "
              f"{min(died_by)}-{max(died_by)} bytes of the start. This is the control "
              f"that makes the check above a measurement: a decoder tolerant enough to "
              f"frame anything would pass that one on its own, and one built to do "
              f"exactly that (swallow its own framing errors) passes it and reddens "
              f"only this line")

    got_c2s = {o for k, rows in clean.items() if k[1] == "c2s"
               for r in rows for o in r["opcodes"]}
    got_s2c = {o for k, rows in clean.items() if k[1] == "s2c"
               for r in rows for o in r["opcodes"]}
    LEDGER.ok(got_c2s == AUTH_C2S_OPCODES and got_s2c == AUTH_S2C_OPCODES,
              "and the auth opcode inventory is exactly the 12 and the 10 measured",
              f"c2s {sorted(hex(o) for o in got_c2s)}; s2c "
              f"{sorted(hex(o) for o in got_s2c)}. Before the catalog fix this repo "
              f"could see TWO auth opcodes, both fictitious. 22 of `authsrv.py`'s "
              f"UPSTREAM auth names now have ArenaNet's own traffic to answer to")

    # ---- 1c. the mask, which is NOT part of the difference -------------------
    # It looks like it should be, so it is checked from the wire rather than
    # assumed: `AUTH_CMSG_MASK` and the game channel's mask are the same 0x8000,
    # and only the catalog differs. If that were wrong, the residual-0 result
    # above would be the thing that broke, so this is the check that would name
    # the cause.
    hdr_c2s = {h for k, rows in clean.items() if k[1] == "c2s"
               for r in rows for h in r["headers"]}
    hdr_s2c = {h for k, rows in clean.items() if k[1] == "s2c"
               for r in rows for h in r["headers"]}
    set_c2s = sum(1 for h in hdr_c2s if h & cmsgstream.CMSG_MASK)
    set_s2c = sum(1 for h in hdr_s2c if h & cmsgstream.CMSG_MASK)
    LEDGER.ok(hdr_c2s and hdr_s2c
              and set_c2s == len(hdr_c2s) and set_s2c == 0,
              "every auth c2s header carries 0x8000 and every s2c header does not",
              f"{set_c2s} of {len(hdr_c2s)} distinct c2s headers carry the bit; "
              f"{set_s2c} of {len(hdr_s2c)} distinct s2c headers do. Measured off "
              f"ArenaNet's own bytes, so it is the client's behaviour rather than "
              f"our constant")

    src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
    auth_mask = next(
        (n.value.value for n in ast.walk(ast.parse(src))
         if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant)
         and any(getattr(t, "id", None) == "AUTH_CMSG_MASK" for t in n.targets)),
        None)
    LEDGER.ok(auth_mask == cmsgstream.CMSG_MASK,
              "and authsrv.py's own AUTH_CMSG_MASK agrees with it",
              f"authsrv.py AUTH_CMSG_MASK={auth_mask!r}, cmsgstream.CMSG_MASK="
              f"{cmsgstream.CMSG_MASK!r}. Read out of the syntax tree rather than "
              f"imported, because importing the server module to read one integer "
              f"starts a Codec and resolves the vault. The two drifting apart is how "
              f"the mask would quietly become part of the channel difference")

    # ---- 2. THE SKILL SPLIT: the finding with a hole in our server behind it --
    necro_use, necro_atk = len(ops(NECRO, USE_SKILL)), len(ops(NECRO, ATTACK_SKILL))
    rang_use, rang_atk = len(ops(RANGER, USE_SKILL)), len(ops(RANGER, ATTACK_SKILL))
    LEDGER.ok(necro_use > 0 and necro_atk == 0 and rang_use == 0 and rang_atk > 0,
              "a caster's skills go out on 0x0046 and a Ranger's on 0x0027",
              f"Necromancer {necro_use}x 0x0046 / {necro_atk}x 0x0027; "
              f"Ranger {rang_use}x 0x0046 / {rang_atk}x 0x0027. A clean swap across two "
              f"characters. USE_SKILL was named from a caster on our own server, and a "
              f"whole narrated session of a Ranger casting produced none of it")

    for stamp, op, label in ((NECRO, USE_SKILL, "0x0046"), (RANGER, ATTACK_SKILL, "0x0027")):
        casts = [t for t, _v in ops(stamp, op)]
        acts = [t for t, _v in ops(stamp, SKILL_ACTIVATED, s2c)]
        paired = sum(1 for c in casts if any(0 < a - c <= 4.0 for a in acts))
        LEDGER.ok(acts and paired >= min(len(casts), len(acts)),
                  f"and {label} is answered by the server's own skill-activated",
                  f"{paired} of {len(casts)} sends are followed by GAME_SMSG 0x00E3 "
                  f"within 4 s ({len(acts)} activations in the session). Both opcodes "
                  f"produce the same server response, which is what makes them two "
                  f"halves of one thing rather than unrelated messages")

    # ---- 3. ATTACK lands in the windows the operator described ----------------
    deaths = [t for t, v in ops(RANGER, STATUS, s2c) if len(v) > 2 and v[2] & 0x10]
    atk = [t for t, _v in ops(RANGER, ATTACK)]
    covered = sum(1 for a in atk if any(0 < d - a <= 25.0 for d in deaths))
    LEDGER.ok(atk and deaths and covered == len(atk),
              "every ATTACK sits in the run-up to one of the two kills",
              f"{covered}/{len(atk)} ATTACK sends fall within 25 s before one of the "
              f"{len(deaths)} deaths in the session. The operator described exactly two "
              f"fights and nothing else -- a corpus where ATTACK fired while nothing was "
              f"being killed would sink the name")

    # ---- 4. the two byte-identical movement messages, told apart --------------
    def near_player(stamp, op):
        """How often this message's vec2 sits where the player just said it was."""
        heads = ops(stamp, MOVE_SET_HEADING)
        hit = tot = 0
        for t, v in ops(stamp, op):
            vec = next((x for x in v if isinstance(x, (list, tuple)) and len(x) == 2), None)
            if vec is None:
                continue
            ref = [(abs(t - ht), hv) for ht, hv in heads if abs(t - ht) <= 1.5]
            if not ref:
                continue
            _d, hv = min(ref, key=lambda r: r[0])
            pos = next((x for x in hv if isinstance(x, (list, tuple)) and len(x) == 2), None)
            if pos is None:
                continue
            tot += 1
            if math.dist(vec, pos) <= 200.0:
                hit += 1
        return hit, tot

    ch, ct_ = near_player(NECRO, MOVE_CANCEL)
    eh, et = near_player(NECRO, MOVE_TO_COORD)
    LEDGER.ok(ct_ and ch == ct_ and (et == 0 or eh == 0),
              "0x0047 reports where the player IS; 0x003E names somewhere else",
              f"0x0047 within 200 units of the player's own reported position "
              f"{ch}/{ct_}; 0x003E {eh}/{et}. The two have a byte-identical layout "
              f"(vec2 + u32), so nothing but the values tells them apart -- and a report "
              f"and a destination are opposite meanings")

    # ---- 5. structural facts a second character could have broken ------------
    col = {s: len(ops(s, EQUIP_COLOR)) for s in (NECRO, RANGER)}
    LEDGER.ok(len(set(col.values())) == 1 and list(col.values())[0] > 0,
              "0x0084 fires the same number of times for both characters",
              f"{col[NECRO]} and {col[RANGER]}. Two different characters of different "
              f"professions making different choices send it an IDENTICAL number of "
              f"times, which is what rules out a player action and makes it part of a "
              f"fixed character-creation sequence")

    tgt = ops(RANGER, TARGET_SELECT)
    LEDGER.ok(tgt and all(len(v) > 2 and not (v[1] and v[1] == v[2]) for _t, v in tgt),
              "TARGET_SELECT never repeats a nonzero id in both its fields",
              f"n={len(tgt)}: 0 samples have field1 == field2 nonzero. The client's own "
              f"branch picks manual-if-nonzero-else-auto, so the two fields being equal "
              f"and set is a state it does not produce")

    heads = ops(RANGER, MOVE_SET_HEADING)
    mags = []
    for _t, v in heads:
        vecs = [x for x in v if isinstance(x, (list, tuple)) and len(x) == 2]
        if len(vecs) >= 2:
            mags.append(math.hypot(*vecs[-1]))
    LEDGER.ok(mags and max(mags) - min(mags) < 10.0,
              "MOVE_SET_HEADING's direction vector is fixed-length",
              f"n={len(mags)}, |v| in [{min(mags):.2f}, {max(mags):.2f}] -- a spread of "
              f"{max(mags) - min(mags):.2f} over the whole session while the position "
              f"field ranges over the map. A heading, not a destination")

    # ---- 6. the exception: our server must dispatch BOTH halves -------------
    # `src` is authsrv.py, already read in section 1c.
    # Match on the source with its whitespace COLLAPSED. This grep read the raw text
    # until 2026-08-11, so it asserted the arm's FORMATTING and not its content: the
    # day the arm grew a `player_dead` guard it wrapped across two lines, the literal
    # stopped matching, and this went red while the thing it claims to check was
    # untouched and still true. A check that fails on a line break is not checking the
    # server. Collapsing whitespace makes it fail only when the two opcodes actually
    # stop sharing an arm, which is the drift it was written to catch.
    flat = " ".join(src.split())
    has_const = "GAME_CMSG_ATTACK_SKILL = 0x0027" in flat
    shared_arm = "opcode in (GAME_CMSG_USE_SKILL, GAME_CMSG_ATTACK_SKILL)" in flat
    # And the other way the claim could fail: a SECOND arm testing the attack half on
    # its own is exactly the split this forbids, and the substring above cannot see it.
    split_arm = "opcode == GAME_CMSG_ATTACK_SKILL" in flat
    LEDGER.ok(has_const and shared_arm and not split_arm,
              "our server dispatches the attack-skill half too, in the SAME arm",
              f"constant={has_const}, shared arm={shared_arm}, split arm={split_arm}. "
              f"Until 2026-08-11 only "
              f"0x0046 was handled, so every physical attack skill fell through to "
              f"silent-ignore and got nothing back. That was written up as a "
              f"correctness bug citing studies/divergence D9(b)'s buffer discard; "
              f"corrected 2026-08-11 -- 0x0027 is schema-KNOWN (GAME_CMSG_0039), so "
              f"it took D9(a), which ignores WITHOUT touching the buffer, and D9(b) "
              f"covers schema-unknown opcodes only. A missing feature, not a "
              f"correctness bug. One arm rather than "
              f"two because they are halves of one action and would otherwise drift")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
