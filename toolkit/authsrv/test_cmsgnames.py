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
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
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
LEDGER = checks.Ledger("GAME_CMSG names vs ArenaNet's own client", floor=16)


def main():
    try:
        vaultpath.require_dir()
    except Exception as ex:                                    # pragma: no cover
        LEDGER.skip("the whole file", f"no vault: {ex}")
        return LEDGER.verdict()

    try:
        c2s = {s: cmsgstream.timed(s, "c2s") for s in (NECRO, RANGER)}
        s2c = {s: cmsgstream.timed(s, "s2c") for s in (NECRO, RANGER)}
    except Exception as ex:                                    # pragma: no cover
        LEDGER.skip("the whole file", f"captures unreadable: {ex}")
        return LEDGER.verdict()

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
    mis = cmsgstream.timed(RANGER, "c2s", channel="auth", catalog="GAME_CMSG")
    mis_ops = {o for _t, _c, o, _v in mis}
    real = sum(r["messages"] for r in cmsgstream.frame_report(RANGER, "c2s", "auth"))
    game_ops = {o for _t, _c, o, _v in c2s[RANGER]}
    LEDGER.ok(0x0001 not in game_ops and 0x0005 not in game_ops
              and {0x0001, 0x0005} <= mis_ops,
              "the AUTH channel is not decoded as GAME_CMSG",
              f"0x0001/0x0005 absent from the game channel's {len(game_ops)} opcodes, "
              f"and PRESENT ({sorted(hex(o) for o in mis_ops)}) when the same auth "
              f"stream is deliberately run through the GAME_CMSG tables -- {len(mis)} "
              f"messages before the framing dies, on a connection that really holds "
              f"{real}. Decoding the wrong channel invents rather than errors")

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
