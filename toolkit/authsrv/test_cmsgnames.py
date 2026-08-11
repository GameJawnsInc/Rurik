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
"""
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
# print as a pass. 11 since the server-dispatch check was added.
LEDGER = checks.Ledger("GAME_CMSG names vs ArenaNet's own client", floor=11)


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
    auth = cmsgstream.timed(RANGER, "c2s", channel="auth")
    game_ops = {o for _t, _c, o, _v in c2s[RANGER]}
    LEDGER.ok(0x0001 not in game_ops and 0x0005 not in game_ops,
              "the AUTH channel is not decoded as GAME_CMSG",
              f"0x0001/0x0005 absent from the game channel's {len(game_ops)} opcodes. "
              f"They ARE present on the auth connection ({len(auth)} messages there), "
              f"and a reader that pooled the two reported them as real GAME_CMSG "
              f"opcodes. Decoding the wrong channel invents rather than errors")

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
    src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
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
