"""The column-major attribute block, and the CharData.cpp(202) crash that
established its shape.

ONE ENCODER AND THE THREE BOUNDS IT ENFORCES. `attribute_columns` builds the
payload of GAME_SMSG 0x003A -- three contiguous columns, ids | ranks |
effective -- and refuses, rather than clamping, anything outside a bound the
client itself asserts. The opcode, the send site and the spend/ack triple stay
in `authsrv.py`; what is here is the arithmetic, which is why it can be
exercised with no socket at all (`test_spawn_burst.py:235-323`,
`test_attribspend.py:38`).

WHY IT IS A MODULE. The function's docstring is the longest single piece of
measured evidence in the server file -- the handler's own division-by-three
arithmetic, the three assert-named slots, and the 34-message corpus reading that
CONFIRMED slot 3 rather than refuting it. It was sitting between the character
accessors and a 35-line banner about a different number (42), and a reader
looking for "what shape is 0x003A" had no reason to look there.

WHAT STAYED BEHIND, and it is deliberately NOT the same number:
`REAL_PROFESSION_ATTRIBUTE_COUNT = 42` (`authsrv.py:3242`) and its banner stay.
42 is a true fact about a different set -- the attributes the ten playable
professions own -- and is NOT the wire's index space, which is `CHAR_ATTRIBS`,
here. The banner says "see attribute_columns below"; the function is now in this
file, and the re-export left at `authsrv.py:2947` is the pointer.

ONE OUTSIDE READER OF A BOUND: `authsrv.py`'s `attribute_state` reads
`ATTRIBUTE_COLUMN_MAX` -- the build-template half of 0x003A's wire, which did
not move -- so it reaches it through the re-export rather than from here. And
`toolkit/authsrv/probes.py:1429` does a lazy `from authsrv import
attribute_columns` inside a probe builder; that is a real second import of
`authsrv`, and the re-export is what keeps it working.

Standard library plus `agents` (the content store), and no import of the server:
`authsrv.py` runs as `__main__`, so importing it back would load a second copy.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agents  # noqa: E402

# The client's own s_attrib bound: the first slot of every triple must be
# below this, and the writer asserts it (ChCliAttrib:249).
CHAR_ATTRIBS = 51
# ArenaNet's own rank cap, asserted twice: AcctTemplate:441
# `data.attribValue[index] <= 12`, and CharData:202's `cmp esi, 0xd` guarding
# the s_attribPoints lookup at 0..12.
ATTRIBUTE_RANK_MAX = 12
# The wire's own ceiling: 0x003A's array32 is declared at 48 elements, which is
# exactly 16 attributes across THREE COLUMNS (see attribute_columns -- the
# payload is column-major, not interleaved) -- and AcctTemplate:423 bounds a
# build template at `attribCount < 16`. The two agree, which is why ONE message
# always suffices for a real character: primary plus secondary profession is at
# most ten attributes. The ceil(N/16) batching ATTRIBUTES.md 6 describes is the
# RESKIN arc's problem (custom tables above 16), not combat's.
ATTRIBUTE_COLUMN_MAX = 16


def attribute_columns(ranks=None, bonuses=None):
    """0x003A's payload: THREE CONTIGUOUS COLUMNS, ids | ranks | ranks.

    NOT interleaved triples. This function was `attribute_triples` and emitted
    `[id0, rank0, rank0, id1, rank1, rank1, ...]` for one day, 2026-08-15, and
    it killed the client every session it ran in:

        Assertion: level < arrsize(s_attribPoints)
        P:\\Code\\Gw\\Char\\CharData.cpp(202)

    The docstring it carried was RIGHT -- it said "three parallel arrays", and
    so did studies/combat/PLAN.md 8a, which had named the wire arrays
    `payload+0xc`, `+0xc+4n` and `+0xc+8n` a day earlier. The code did not do
    what either said. See studies/combat/PLAN.md 14 for the whole trace.

    THE SHAPE IS MEASURED, from the handler's own arithmetic. 0x003A's handler
    (0x0091D920 on build 38833) takes the wire count, divides it by three, and
    builds three pointers into ONE flat array before forwarding:

        n = count / 3                    mov eax,0xAAAAAAAB; mul [ecx+8]; shr edx,1
        arr1 = payload + 0x0C            lea eax,[ecx+0xc]
        arr2 = payload + 0x0C + n*4      lea eax,[eax+edx*4]
        arr3 = payload + 0x0C + n*8      lea eax,[eax+edx*8]

    so element i of each column is n*4 bytes from the last, NOT 4. The loop
    (0x00819C00) walks them with MSVC's induction-variable form -- it holds
    `arr2 - arr1` and `arr3 - arr2` as deltas and adds them to the arr1 cursor
    -- and hands `(record, arr1[i], arr2[i], arr3[i])` to the writer 0x00819270.

    WHY INTERLEAVING IS FATAL RATHER THAN MERELY WRONG. Column 2 lands on
    whatever the flat array holds from index n on, which for interleaved input
    is a mix of ids and ranks. Attribute ids run to 50; the rank the client
    reads out of column 2 goes straight into `s_attribPoints[rank]`, whose
    `arrsize` is 13 (toolkit/clientscan/attribpoints.py, read out of the
    client's own `cmp esi, 0Dh`). Any id of 13 or more is a modal assert box.
    With the five content ranks the interleaved form put 19 in column 2 at
    i=1 and the client stopped there.

    Slot 1 is `attrib`, the id, bound-checked against 51; slot 2 is
    `baseValue`, the rank, and the assert that names it reads
    `[record + attrib*20 + 8]`, which is what ties the name to that slot
    rather than to its neighbour (studies/combat/PLAN.md 8a).

    SLOT 3 IS RECONSTRUCTION AND IS THE ONE THING HERE TO DISTRUST. No assert
    names it. What is measured is that the client's own pending-change apply
    adds the IDENTICAL delta to it and to `baseValue` (0x0081877C and
    0x00818789-0x0081878C read the same `[edx+8]`), so from a common zero the
    two stay equal -- and sending the rank in both reproduces that invariant
    rather than inventing a second number. The reading that fits everything
    seen is base-rank vs effective-rank-including-bonuses, which are equal for
    a character wearing no runes; ours wears none. If a capture ever shows the
    two differing, THIS is the line that was wrong.

    **A CAPTURE DID, AND THE READING WAS RIGHT (2026-08-20).** The corpus holds
    34 of these messages, and in 26 -- every sighting of one character --
    column 3 is column 2 PLUS ONE on attribute 20 alone, while 17, 21, 29 and
    30 stay equal. The gap is 0 or +1 and nothing else across 94 (attribute,
    sighting) pairs. So SLOT 3 is CONFIRMED as effective-including-bonuses
    rather than refuted, and the half of that sentence which changed is the
    other one: ours can wear something now. `bonuses` is how, it defaults to
    empty, and a caller passing nothing still sends the equal-columns
    invariant this docstring describes.

    Refuses rather than clamping, the same rule `_fraction` follows: every
    bound below is the client's own, and a value outside one is a bug in the
    caller that a clamp would hide.
    """
    ranks = agents.PLAYER_ATTRIBUTE_RANKS if ranks is None else ranks
    if len(ranks) > ATTRIBUTE_COLUMN_MAX:
        raise ValueError(
            f"refusing to send {len(ranks)} attributes in one 0x003A: "
            f"the array32 is declared at 48 elements = {ATTRIBUTE_COLUMN_MAX} "
            f"per column, and AcctTemplate:423 bounds a build template at 16 "
            f"too. More than that needs ceil(N/16) messages, which no real "
            f"character reaches -- primary plus secondary is at most ten.")
    seen, ids, values, effective = set(), [], [], []
    for attrib_id, rank in ranks:
        if not 0 <= attrib_id < CHAR_ATTRIBS:
            raise ValueError(
                f"refusing attribute id {attrib_id}: the client's s_attrib "
                f"table has {CHAR_ATTRIBS} rows and its writer asserts "
                f"`attrib < arrsize(attribState->attrib)` (ChCliAttrib:249). "
                f"Ids are contiguous 0..{CHAR_ATTRIBS - 1}; there are no gaps "
                f"in the index space (studies/combat/PLAN.md 10).")
        if not 0 <= rank <= ATTRIBUTE_RANK_MAX:
            raise ValueError(
                f"refusing rank {rank} for attribute {attrib_id}: ArenaNet's "
                f"own cap is {ATTRIBUTE_RANK_MAX} (AcctTemplate:441 "
                f"`data.attribValue[index] <= 12`), and CharData:202 bounds "
                f"the s_attribPoints lookup at 0..12.")
        if attrib_id in seen:
            raise ValueError(
                f"attribute {attrib_id} appears twice. Each triple WRITES its "
                f"slot, so a duplicate silently means 'the last one wins' -- "
                f"refused because that is a caller bug wearing a valid shape.")
        seen.add(attrib_id)
        ids.append(attrib_id)
        values.append(rank)
        # Effective is deliberately NOT bound-checked against
        # ATTRIBUTE_RANK_MAX: retail sent effective 13 against a spend cap of
        # 12 in 26 of 26 sightings, so the cap belongs to the base rank alone.
        effective.append(rank + int((bonuses or {}).get(attrib_id, 0)))
    # The one line the crash was in. Column-major: every id, then every rank,
    # then the third column -- because the client slices ONE flat array at n
    # and 2n, and `+ [a, r, r]` per attribute is the reading that does not
    # survive contact with that.
    return ids + values + effective
