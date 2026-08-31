"""Twenty GAME_SMSG names, and the wire invariants that can take them back.

On 2026-08-10 the catalog went from ONE named GAME_SMSG opcode of 487 to twenty-one.
The names came from joining two witnesses that were not consulted to produce each
other: the client's own dispatch handlers and its 19,620 compiled assert expressions
on one side, and 10,944 real ArenaNet server messages on the other (capture
20260807T143055, four tapes, 146 distinct opcodes, framing 100% clean with zero
unconsumed bytes).

WHY THIS FILE EXISTS RATHER THAN THE SCHEMA ENTRY ALONE. A `name` in a JSON file is
an assertion nothing can refute. `schema/overrides.json` now carries twenty of them
and every one is a claim about ArenaNet's server that our own decoder is perfectly
happy to keep believing while being wrong. The checks below are the half that can go
red: each is an invariant the CORPUS could have violated and did not.

WHAT IS AND IS NOT ASSERTED HERE. Everything below is a property of ArenaNet's
recorded traffic, not of our server -- so a change to `authsrv.py` cannot make this
file pass or fail, and that is deliberate. The claims that rest on reading the binary
(assert text, handler addresses, jump-table bounds) are NOT re-checked here; that is
`toolkit/clientscan/asserts.py`'s ground and needs the vaulted build. What lives here
is exactly the set of claims a `.raw` in the vault can arbitrate.

THE ONE THAT MATTERS MOST is section 1. `0x001E` is 36.3% of everything ArenaNet's
server sent -- more than the next five opcodes combined -- and the obvious reading of
a one-dword message at that frequency is a heartbeat. It is not: the payload is
elapsed milliseconds, and summing it across a tape reconstructs that tape's own wall
clock to within 18 ms over 13-185 seconds. Our server has never sent this correctly.
No heartbeat reading survives that check, which is why it is the first one.

THE CAVEAT THIS FILE SHIPPED WITH IS RETIRED, and how is worth keeping. On 2026-08-10
every number here came from four tapes of ONE session, one character -- "4/4 tapes" was
four samples sharing a character record, and a name that was really a fact about one
Necromancer would have passed. On 2026-08-11 a second session was captured on a
deliberately different character (a Ranger) walking the SAME three maps, so the
character was the variable and the map content was not. Every invariant below now runs
over both, pooled: 8 tapes, 21,543 messages. Nothing needed changing to make that pass,
which is the result -- and the two sessions' opcode vocabularies turn out to be nearly
identical (146 distinct each, 148 in union, 2 in and 2 out), so the surface an ordinary
session touches is stable across characters.

WHAT A GREEN RUN STILL DOES NOT COVER: two characters, one account, one campaign's
starting area. It does not speak for other campaigns, for post-Searing, for parties
larger than one, or for the 339 GAME_SMSG opcodes neither session ever used.
"""
import collections
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
import checks  # noqa: E402
import content  # noqa: E402
import tape as tapemod  # noqa: E402
import vaultpath  # noqa: E402
from codec import Codec  # noqa: E402

# Two live sessions, two characters of different professions, same three maps.
CAPTURES = ("20260807T143055",      # Necromancer
            "20260810T235916")      # Ranger, and it killed two things

TICK = 0x001E
CREATE = 0x0020
REMOVE = 0x0021
MOVE_DIR = 0x0025
UPDATE_FLAGS = 0x0026
MOVE_TO_POINT = 0x0029
UPDATE_SPEED = 0x002B
UPDATE_ROTATION = 0x002E
TABARD = 0x0048
NPC_PROPS = 0x0056
MONSTER_COMPOSITE = 0x0057
VISUAL_EQUIPMENT = 0x006E
PROFESSION = 0x00A6
INITIAL_STATUS = 0x00F0
UPDATE_STATUS = 0x00F1
CREATE_BAG = 0x013F
ITEM_MOVED = 0x013E
NAMED_ITEM = 0x0161

# The bit GmCoreAction's target gate reads off the player's OWN equipped weapon
# (studies/enemy/PLAN.md 10.4). 0x005147F0 fetches equipment slot 0 and returns
# `(*(uint32 *)(record + 0xc) >> 25) & 1`; a zero withholds the target entirely.
# itemprobe.py measured record+0xc to be the wire `flags` word of 0x0161.
GATE_BIT = 1 << 25
BAG_TYPE_EQUIPPED = 2
EQUIP_SLOT_WEAPON = 0

# Set from a real green run of the sections below, never from a guess.
LEDGER = checks.Ledger("GAME_SMSG names vs ArenaNet's own wire", floor=26)


def load(stamp):
    """Return [(tape, carry), ...], one entry per chained tape, in chain order.

    Frames across segment boundaries: a wire segment is a TCP write, not a message,
    and a message can straddle two of them. Carrying the remainder is what makes the
    'zero unconsumed bytes' claim meaningful rather than an artifact of truncation.

    KEPT, not overlooked, when `tape.decode_all` landed on 2026-08-11. That helper
    exists because most consumers framed each event on its own and lost 19% of the
    corpus; this loop never did. Measured across all ten live tapes, it yields the
    same message sequence as framing the stream whole, with zero carry left over --
    so there is nothing here to fix, and the one behavioural difference is a
    deliberate reason not to touch it: a straddled message is stamped where it
    COMPLETES here and where it STARTS in decode_all, and this file's headline is a
    timing claim measured under this convention.
    """
    codec = Codec(overrides=os.path.join(os.path.dirname(os.path.dirname(HERE)),
                                         "schema", "overrides.json"))
    cap = tapemod.resolve_capture(stamp)
    tapes = []
    for conn in tapemod.chain(cap):
        _meta, events = tapemod.load_tape(cap, conn)
        seq, carry = [], b""
        for t, blob in events:
            buf = carry + blob
            msgs, used, _rest = codec.decode_stream("GAME_SMSG", buf)
            carry = buf[used:]
            seq += [(t, op, v) for op, v in msgs]
        tapes.append((seq, carry))
    return tapes


def main():
    try:
        vaultpath.require_dir()
    except (Exception, SystemExit) as ex:                                    # pragma: no cover
        LEDGER.skip("the whole file", f"no vault: {ex}")
        return LEDGER.verdict()

    # Pool BOTH live captures. Every invariant below is asserted over two
    # sessions on two DIFFERENT characters of different professions, walking the
    # same three maps -- which is what retires the caveat this file shipped with
    # on 2026-08-10 ("4/4 tapes is four samples sharing a character record").
    # Anything that survives here survived a change of character; anything that
    # is really a character property had its chance to break the run.
    loaded, per_capture = [], {}
    for stamp in CAPTURES:
        try:
            got = load(stamp)
        except Exception as ex:                                # pragma: no cover
            LEDGER.skip(f"capture {stamp}", f"unreadable: {ex}")
            continue
        per_capture[stamp] = got
        loaded += got
    if len(per_capture) < 2:                                   # pragma: no cover
        LEDGER.skip("the cross-character half",
                    f"only {len(per_capture)} of {len(CAPTURES)} captures readable "
                    f"-- the invariants below still run, but on one character")
    if not loaded:                                             # pragma: no cover
        return LEDGER.verdict()

    LEDGER.ok(len(per_capture) == 2,
              "the corpus is TWO live sessions on two different characters",
              f"{len(per_capture)} captures, "
              f"{', '.join(f'{s}={sum(len(t) for t, _c in g)} msgs' for s, g in per_capture.items())}. "
              f"Different professions, same three maps (Ascalon City -> Lakeside "
              f"County -> Ashford Abbey), so the character is the variable that "
              f"changed and the map content is not")

    tapes = [seq for seq, _carry in loaded]
    leftover = sum(len(carry) for _seq, carry in loaded)
    allm = [m for seq in tapes for m in seq]
    LEDGER.ok(len(tapes) == 8 and len(allm) >= 20000,
              "and it frames to eight chained tapes",
              f"{len(tapes)} tapes, {len(allm)} GAME_SMSG messages, "
              f"{len({op for _t, op, _v in allm})} distinct opcodes -- a floor, so a "
              f"capture tree that quietly shrinks is noticed rather than making every "
              f"check below easier to pass")
    LEDGER.ok(leftover == 0,
              "and every byte of it frames",
              f"{leftover} B unconsumed" if leftover else
              "0 B unconsumed across all eight tapes -- the counts below are over the "
              "WHOLE recorded stream, not the part our decoder happened to like")

    def of(op):
        return [v for _t, o, v in allm if o == op]

    # ---- 1. 0x001E WORLD_SIMULATION_TICK: the payload IS elapsed milliseconds ----
    worst_drift, worst_ratio = 0.0, None
    for seq in tapes:
        ticks = [(t, v[1]) for t, op, v in seq if op == TICK]
        if len(ticks) < 2:
            continue
        # the first tick's payload covers time BEFORE it, so it is not in the span
        total = sum(v for _t, v in ticks[1:])
        span = (ticks[-1][0] - ticks[0][0]) * 1000.0
        drift = total - span
        if abs(drift) > abs(worst_drift):
            worst_drift, worst_ratio = drift, total / span
    LEDGER.ok(abs(worst_drift) <= 50.0,
              "0x001E's payload summed reconstructs each tape's own wall clock",
              f"worst drift {worst_drift:+.1f} ms (ratio {worst_ratio:.4f}) across "
              f"tapes spanning 13-185 s. This is the check no heartbeat reading "
              f"survives: a keepalive's payload is echoed or ignored, and this one "
              f"integrates to real time. The client's own two names for the field are "
              f"message.time (AgMsg.cpp:208) and elapsedMs (AgTimer.cpp:32)")

    ticks = of(TICK)
    LEDGER.ok(len(ticks) > len(allm) * 0.3,
              "and it really is the corpus's largest opcode",
              f"{len(ticks)} of {len(allm)} = {100.0 * len(ticks) / len(allm):.1f}%, "
              f"more than the next five opcodes combined -- which is why getting it "
              f"wrong is expensive and why our server sending it on a fixed sleep is "
              f"the largest single divergence from ArenaNet's traffic")
    LEDGER.ok(all(0 < v[1] <= 2000 for v in ticks),
              "and every delta is a plausible frame time",
              f"{len({v[1] for v in ticks})} distinct values in "
              f"[{min(v[1] for v in ticks)}, {max(v[1] for v in ticks)}] ms; a "
              f"constant or a wall-clock timestamp would both fail this")

    # ---- 2. direction vs destination: the discriminator that names both ----
    dirs = [math.hypot(*v[2]) for v in of(MOVE_DIR)]
    pts = [math.hypot(*v[2]) for v in of(MOVE_TO_POINT)]
    LEDGER.ok(dirs and all(abs(d - 1.0) < 0.01 for d in dirs),
              "0x0025's vec2 is a UNIT vector, without exception",
              f"n={len(dirs)}, |v| in [{min(dirs):.5f}, {max(dirs):.5f}] -- "
              f"{sum(1 for d in dirs if abs(d - 1.0) < 0.01)}/{len(dirs)} within 1%")
    LEDGER.ok(pts and not any(abs(d - 1.0) < 0.01 for d in pts),
              "and 0x0029's is a world POSITION, never once unit length",
              f"n={len(pts)}, |v| in [{min(pts):.1f}, {max(pts):.1f}] world units, "
              f"0 within 1% of 1.0. Two messages whose vec2 fields are indistinguishable "
              f"by type and unmistakable by magnitude -- this is the whole basis for "
              f"calling one a direction and the other a destination, and it is the same "
              f"trap that scored test_rotate.py's first version zero")

    # ---- 3. the create burst: 0x00F0 is a PREFIX, not a post-create update ----
    hit = tot = 0
    for seq in tapes:
        nontick = [(op, v) for _t, op, v in seq if op != TICK]
        for i, (op, v) in enumerate(nontick):
            if op != INITIAL_STATUS:
                continue
            tot += 1
            if (i + 1 < len(nontick) and nontick[i + 1][0] == CREATE
                    and v[1] == nontick[i + 1][1][1]):
                hit += 1
    LEDGER.ok(tot and hit == tot,
              "0x00F0 is immediately followed by its OWN agent's create",
              f"{hit}/{tot}, once 0x001E ticks are filtered out -- and the subject link "
              f"is checked, not just the adjacency: the status message and the create "
              f"name the same agent every time. This is what makes it INITIAL_STATUS "
              f"rather than a status update, and it is the message ArenaNet sends 472 "
              f"times that our server has never sent at all")

    # Two DIFFERENT things, and conflating them makes this check assert the wrong
    # number: an 0x00F1 that arrives before a create it later gets (which is what
    # 0x00F0 does 472 times), versus one naming an agent the tape never creates at
    # all -- an agent carried in from outside the recorded window. Only the first
    # bears on initial-versus-update.
    early, foreign = 0, 0
    for seq in tapes:
        created = {v[1] for _t, op, v in seq if op == CREATE}
        seen = set()
        for _t, op, v in seq:
            if op == CREATE:
                seen.add(v[1])
            elif op == UPDATE_STATUS:
                if v[1] not in created:
                    foreign += 1
                elif v[1] not in seen:
                    early += 1
    LEDGER.ok(early == 0,
              "and 0x00F1 never precedes a create it does get, where 0x00F0 always does",
              f"{early} of {len(of(UPDATE_STATUS))} 0x00F1 arrive before their own "
              f"agent's create, against 0x00F0's {tot}. The asymmetry is the entire "
              f"initial-versus-update distinction; without it the two opcodes are "
              f"interchangeable. Separately {foreign} name an agent this tape never "
              f"creates -- carried in from outside the recorded window, which is a "
              f"different thing and is NOT evidence either way")

    # ---- 4. referential integrity: these messages never name a stranger ----
    for op, label in ((REMOVE, "0x0021 removes"), (UPDATE_FLAGS, "0x0026 flags")):
        orphan = 0
        for seq in tapes:
            seen = set()
            for _t, o, v in seq:
                if o == CREATE:
                    seen.add(v[1])
                elif o == op and v[1] not in seen:
                    orphan += 1
        n = len(of(op))
        LEDGER.ok(orphan == 0,
                  f"{label} only agents 0x0020 created earlier in the same tape",
                  f"{n - orphan}/{n}, 0 orphans. An all-or-nothing property over the "
                  f"whole corpus: one stranger and the create/remove reading of the "
                  f"pair is wrong")

    # ---- 5. the client's own asserted bounds, met by ArenaNet's own traffic ----
    speeds = [v[2] for v in of(UPDATE_SPEED)]
    LEDGER.ok(speeds and all(0.01 <= s <= 1.0 for s in speeds),
              "0x002B's float obeys the client's asserted AGENT_MIN/MAX_MOVE_SPEED",
              f"n={len(speeds)}, [{min(speeds):.4f}, {max(speeds):.4f}] against the "
              f"asserted [0.01, 1.0] (AgAgent.cpp:2366-2367). The cap is why the "
              f"server's old 'SpeedModifier' gloss cannot be right -- a movement buff "
              f"has nowhere to go in a field that tops out at 1.0")
    facings = [v[3] for v in of(UPDATE_SPEED)]
    LEDGER.ok(facings and all(f & ~0xF == 0 for f in facings),
              "and its byte obeys AGENT_FACING_MASK",
              f"values {sorted(set(facings))}, all within the 4 bits "
              f"AgAgent.cpp:2368 asserts")

    # BOTH fields are marshalled u32 and hold IEEE-754 floats -- the same split that
    # named GAME_CMSG 0x0040, and the reason overrides.json must keep typing them
    # `dword`. Reading them raw is not a small mistake: it makes the angle check
    # compare garbage against pi, and it makes the turn-rate check ("all positive")
    # pass vacuously, since a raw dword is almost always positive. The first draft
    # of this file did exactly that and this comment is why it does not now.
    def as_float(u32):
        return struct.unpack("<f", struct.pack("<I", u32 & 0xFFFFFFFF))[0]

    rots = of(UPDATE_ROTATION)
    angles = [as_float(v[2]) for v in rots]
    finite = [a for a in angles if math.isfinite(a)]
    nonfinite = [a for a in angles if not math.isfinite(a)]
    LEDGER.ok(finite and all(-math.pi <= a <= math.pi for a in finite),
              "0x002E's field 2 is an ANGLE: every finite value inside +/-pi",
              f"n={len(finite)} finite in [{min(finite):.5f}, {max(finite):.5f}] "
              f"(read as float32 from the u32 wire field). REFUTES the upstream "
              f"rotation_cos/rotation_sin reading, which this corpus kills outright -- "
              f"sin^2+cos^2 over these samples is never 1")
    LEDGER.ok(nonfinite and all(math.isinf(a) for a in nonfinite)
              and not any(math.isnan(a) for a in angles),
              "and its only non-finite values are the two +/-inf sentinels",
              f"{len(nonfinite)} non-finite, all infinite ({sorted(set(nonfinite))}), "
              f"0 NaN -- the same sentinel idiom that named GAME_CMSG 0x0040, loaded "
              f"from two .rdata constants")
    rates = sorted({as_float(v[3]) for v in rots})
    LEDGER.ok(rates and all(0 < r <= 20 * math.pi for r in rates),
              "and its turn rate is a bounded, quantised rad/s",
              f"{len(rates)} distinct rates, {[round(r, 5) for r in rates]}; "
              f"{max(rates):.7f} is 2*pi/3 to the bit. A per-creature constant, not a "
              f"per-message value -- and note this check is only meaningful BECAUSE the "
              f"field is reinterpreted: raw u32 would satisfy 'positive' for free")

    profs = of(PROFESSION)
    LEDGER.ok(profs and all(v[2] != 0 for v in profs),
              "0x00A6's primary profession is never 0, its secondary often is",
              f"n={len(profs)}: field 2 in "
              f"[{min(v[2] for v in profs)}, {max(v[2] for v in profs)}] and never 0; "
              f"field 3 is 0 in {sum(1 for v in profs if v[3] == 0)}. The client's own "
              f"invariant is GmDeckBuilder:2321 'agentPrimaryProf != agentSecondaryProf', "
              f"and a corpus that violated 'primary is mandatory' would sink the name")

    # ---- 6. the pairs, checked on the SUBJECT and not merely the adjacency ----
    def follows(a, b, akey=1, bkey=1):
        hit = tot = 0
        for seq in tapes:
            flat = [(op, v) for _t, op, v in seq]
            for i, (op, v) in enumerate(flat):
                if op != a:
                    continue
                tot += 1
                if (i + 1 < len(flat) and flat[i + 1][0] == b
                        and v[akey] == flat[i + 1][1][bkey]):
                    hit += 1
        return hit, tot

    hit, tot = follows(VISUAL_EQUIPMENT, TABARD)
    LEDGER.ok(tot and hit == tot,
              "0x006E is followed by 0x0048 naming the same agent, without exception",
              f"{hit}/{tot}. 0x0048's agent set is exactly 0x006E's, which is what "
              f"lets a medium-confidence name stand on a call site rather than an "
              f"assert naming the bit")

    comp_hit = comp_tot = 0
    for seq in tapes:
        flat = [(op, v) for _t, op, v in seq]
        for i, (op, v) in enumerate(flat):
            if op != MONSTER_COMPOSITE:
                continue
            comp_tot += 1
            if i and flat[i - 1][0] == NPC_PROPS and flat[i - 1][1][1] == v[1]:
                comp_hit += 1
    LEDGER.ok(comp_tot and comp_hit == comp_tot,
              "every 0x0057 is preceded by an 0x0056 declaring the same definition",
              f"{comp_hit}/{comp_tot}, 0 orphans -- the composite always extends a "
              f"definition the same tape already opened, which is the ordering a "
              f"server has to reproduce")

    # ---- 7. the bag table: fixed in shape, session-scoped in its ids ----
    triples, rowcounts = set(), []
    for seq in tapes:
        rows = [v for _t, op, v in seq if op == CREATE_BAG]
        rowcounts.append(len(rows))
        triples.add(tuple((r[2], r[3], r[5]) for r in rows))
    LEDGER.ok(len(set(rowcounts)) == 1 and rowcounts[0] == 9,
              "0x013F arrives exactly nine times per instance",
              f"per tape: {rowcounts}. Nine of these is the entire reason the client "
              f"has an inventory to draw, and we send ONE of the nine -- the equipped "
              f"bag, which is enough for the attack gate below to find slot 0 but not "
              f"for anything a backpack or a belt pouch would hold")
    # ---- 8. a definition is declared ONCE and reused across every create ----
    # This is the question 0c was blocked on -- whether the client keeps an NPC
    # definition across a removal -- and ArenaNet's own traffic answers it, which
    # is better than the probe we built for it: the SAME client is on both ends.
    # If the client dropped the definition when the agent went away, 31 of the
    # worm's 32 creates would reference a definition slot it no longer holds, and
    # a create against an undeclared slot takes the client down on Array.h's
    # `index < m_count`. It does not go down. So the client keeps it.
    worst_ratio_def, worst_slot = 0, None
    for seq in tapes:
        declared = collections.Counter(v[1] for _t, op, v in seq if op == NPC_PROPS)
        used = collections.Counter((v[2] & 0x0FFFFFFF) for _t, op, v in seq
                                   if op == CREATE)
        for slot, n_used in used.items():
            n_dec = declared.get(slot, 0)
            if n_dec and n_used // max(n_dec, 1) > worst_ratio_def:
                worst_ratio_def, worst_slot = n_used // n_dec, (slot, n_dec, n_used)
    LEDGER.ok(worst_ratio_def >= 10,
              "an NPC definition is declared ONCE and reused by many creates",
              f"the most-reused definition in the corpus was declared "
              f"{worst_slot[1]} time(s) and referenced by {worst_slot[2]} creates "
              f"({worst_ratio_def}x). The client therefore KEEPS a definition across "
              f"agent removal -- 0c's open question, settled from ArenaNet's own "
              f"traffic rather than from our probe, because it is the same client on "
              f"both ends. A server may declare once and re-create freely")

    # ---- 9. the bit the client gates attacking on, on ArenaNet's own weapon ----
    # studies/enemy/PLAN.md 10.4. The gate is on OUR side of the interaction, so
    # this is a claim about a value we CONTROL -- which makes it exactly the kind
    # of thing that rots silently when someone tunes content/items.toml. Joined
    # the long way (equipped bag -> slot 0 -> the item's own declaration) rather
    # than by trusting the weapon-set message, so the check follows the same path
    # 0x845890 -> 0x845470 -> 0x8451e0 the client walks.
    # v[0] is the OPCODE and the fields follow it -- the same convention section 7
    # above relies on for its (r[2], r[3], r[5]) triple. Getting this off by one
    # is not a crash: it silently reads a neighbouring field and answers
    # confidently, which is how a first pass over this corpus produced two
    # GAME_CMSG opcodes that do not exist.
    #   CREATE_BAG  [op, stream, bagType, model, bagId, slots, ?]
    #   ITEM_MOVED  [op, stream, itemId, bagId, slot]
    #   NAMED_ITEM  [op, itemId, fileId, type, dyeTint, dyeColors, materials,
    #                unk1, FLAGS, value, modelId, quantity, encName, modifiers]
    equipped, gated, checked_caps = [], 0, 0
    for _stamp, group in per_capture.items():
        seq = [m for tape, _carry in group for m in tape]
        bags = {v[4] for _t, op, v in seq
                if op == CREATE_BAG and len(v) > 5 and v[2] == BAG_TYPE_EQUIPPED}
        slot0 = {v[2] for _t, op, v in seq
                 if op == ITEM_MOVED and len(v) > 4
                 and v[3] in bags and v[4] == EQUIP_SLOT_WEAPON}
        decl = {v[1]: v for _t, op, v in seq if op == NAMED_ITEM and len(v) > 8}
        found = [decl[i] for i in slot0 if i in decl]
        if found:
            checked_caps += 1
        equipped += found
        gated += sum(1 for v in found if v[8] & GATE_BIT)
    LEDGER.ok(checked_caps == 2 and equipped and gated == len(equipped),
              "every weapon ArenaNet equips in slot 0 carries the gate bit",
              f"{gated}/{len(equipped)} slot-0 items across {checked_caps} capture(s) "
              f"carry bit 25 of their 0x0161 flags word. That bit is the WHOLE test "
              f"0x005147F0 applies before the client will offer an enemy as a target, "
              f"and it reads it off the PLAYER's weapon, never off the target")

    allflags = [v[8] for _t, op, v in allm if op == NAMED_ITEM and len(v) > 8]
    setflags = sum(1 for f in allflags if f & GATE_BIT)
    LEDGER.ok(allflags and 0 < setflags < len(allflags),
              "and it is not simply set on everything",
              f"{setflags} of {len(allflags)} declared items carry it. A bit that was "
              f"always set, or never, would make the check above vacuous -- the "
              f"equipped weapons having it is then a fact about WEAPONS")

    theirs = {v[8] for v in equipped}
    try:
        ourflags = int(content.load().get("item", "starter_hammer")["flags"])
    except Exception as ex:                                    # pragma: no cover
        LEDGER.skip("our own weapon vs theirs", f"content unreadable: {ex}")
    else:
        LEDGER.ok(bool(ourflags & GATE_BIT) and ourflags in theirs,
                  "and the weapon WE send carries it, with a word they also send",
                  f"content/items.toml starter_hammer flags 0x{ourflags:08X}, bit 25 "
                  f"{'set' if ourflags & GATE_BIT else 'CLEAR'}; ArenaNet's own slot-0 "
                  f"words are {sorted(hex(f) for f in theirs)}. Measured live on "
                  f"2026-08-11: the client stores this word at item+0x28 and the gate "
                  f"PASSES, which is what refuted studies/enemy/PLAN.md 10.3")

    LEDGER.ok(len(triples) == 1,
              "and its (bagType, slot, capacity) triples are identical across tapes",
              f"{len(triples)} distinct table(s) across {len(rowcounts)} tapes. NOTE "
              f"the limit of this: the WHOLE rows are NOT identical -- two of the six "
              f"fields are session-scoped ids a server must allocate itself, so this "
              f"is a fixed SHAPE and not a shippable constant table. The naming pass's "
              f"synthesis claimed the latter and it is wrong")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
