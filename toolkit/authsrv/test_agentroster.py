r"""The per-agent roster reader, and the identity that survives a recycled agent id.

WHAT THIS PINS, and why each pin is a check that can fail:

  * THE CROSS-SESSION STATION. Two live sessions three days apart on map 148 declare
    the identical (slot 1470, model 116698, pos (8436.0, 4819.0), plane 0) -- four
    creates each, all under agent 44, all `nonc`. That row is `studies/isle/PLAN.md`
    rung 1's exit criterion verbatim: it is what makes an Isle roster a TABLE rather
    than a session log. If the wire stops agreeing, the premise of the whole Isle
    plan changes and this file says so before a live minute is spent on it.

  * THE PARTITION. Create field 2's mask is meaningful ONLY for the NPC class (tag
    2). MEASURED here: 331 player creates masked anyway yield 0 collisions with the
    declared definition set and a non-empty set of PHANTOM slots -- so a reader that
    masks unconditionally does not corrupt real definitions, it INVENTS types that
    were never declared, which is worse because nothing downstream can notice. The
    sabotage is run both directions: the partitioned read has zero phantoms, the
    unconditional mask has a measured, non-zero count.

  * THE POSITION. A create's position is the vec2 at decoded index 5, NOT
    `tuple(v[3:5])` -- the bug `studies/isle/PLAN.md` §3.2 found live in
    `behaviourrun.py`, where every reported position was actually (type, kind) and
    the test was green because its fixture had a shape no wire ever produced. The
    synthetic check here builds a create whose fields 3/4 differ from its field-5
    components, so reading the wrong slots cannot come back right.

Sections 0-3 and 5 need `vault/captures/live/`; without it they skip and the floor
takes the run red -- ArenaNet's own bytes are the only oracle for a roster of
ArenaNet's agents.

    python toolkit/authsrv/test_agentroster.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
import agentroster  # noqa: E402
import checks  # noqa: E402
import npcdefs  # noqa: E402

# Floor 27, measured from a green run on 2026-08-16: 2 refusal + 4 corpus +
# 6 partition + 3 position + 8 cross-session + 3 sabotage + 2 edge -- every one
# executes on every healthy run, so the floor is the count. Vault-dependent sections
# declare their skips, and a run without the live captures lands at 2 of 27 and goes
# RED rather than green-by-absence.
LEDGER = checks.Ledger("agentroster: creates -> stations -> cross-session identity",
                       floor=27)

# Measured 2026-08-16 over the three keyed live captures, and written as literals:
# a symbol imported from the module under test is not a check.
ROSTERS, TOTAL_CREATES = 12, 1068
M148 = {
    # capture -> (item, npc, player) create counts on its map-148 game connection
    "20260807T143055": (14, 82, 109),
    "20260810T235916": (15, 86, 222),
}
PIN = (2, 1470, 116698, (8436.0, 4819.0), 0)   # tag, slot, model, pos, plane
PIN_CREATES, PIN_AGENT, PIN_TOKEN = 4, 44, "nonc"
JOIN_148 = (19, 15, 22)                        # both, only_a, only_b
JOIN_164 = (6, 0, 0)                           # a whole outpost, byte-stable
MASKED_PLAYERS = 331                           # player creates across the 148 pair


def synthetic_create(tag, low16, pos, plane=7):
    """Decoded values for one create: opcode at [0], the layout agents.create_agent
    authors. Fields 3/4 are set to values that would LOOK like a position if the
    v[3:5] bug were reintroduced -- that is the point of them."""
    tagged = (tag << 28) | low16
    return [0x0020, 51, tagged, 1, 9, pos, plane,
            (1.0, 0.0), 1, 1.25, 1.0, 0x41400000,
            0x6E6F6E63]  # 'cnon' wire order -> 'nonc'


def main():
    try:
        caps = npcdefs.live_captures()
    except SystemExit:
        caps = []

    # ---- 4. the refusal, vault or no vault -----------------------------------
    # Run first so a bare machine still measures SOMETHING real before the skips.
    print("4. the class-tag refusal")
    try:
        agentroster.create_row(1.0, synthetic_create(0x5, 0x1234, (1.0, 2.0)))
        refused, msg = False, ""
    except agentroster.RosterError as e:
        refused, msg = True, str(e)
    LEDGER.ok(refused, "an unseen class tag STOPS the read",
              "tag 0x5 never appears in the corpus")
    if refused:
        LEDGER.ok("0x5" in msg and "agent 51" in msg,
                  "and the refusal names the tag and the agent", msg[:70])

    if not caps:
        for why in ("the corpus reads whole", "the partition holds",
                    "positions decode from field 5", "the cross-session station",
                    "the phantom-slot sabotage"):
            LEDGER.skip(why, "no decrypted live captures in the vault")
        return LEDGER.verdict()

    rosters = agentroster.read_roster(caps)

    # ---- 0. the corpus --------------------------------------------------------
    print("0. the corpus")
    LEDGER.ok(len(rosters) == ROSTERS, f"{ROSTERS} game channels read whole",
              f"{len(rosters)} (read_roster refuses any partial frame)")
    total = sum(len(r["creates"]) for r in rosters)
    LEDGER.ok(total == TOTAL_CREATES, f"{TOTAL_CREATES} creates decoded",
              str(total))
    seen_tags = {c["tag"] for r in rosters for c in r["creates"]}
    LEDGER.ok(seen_tags == {0, 2, 3}, "class tags observed are exactly {0, 2, 3}",
              str(sorted(seen_tags)))
    LEDGER.ok(all(r["origin"] == "live" for r in rosters),
              "every roster is origin=live", "the vault's live dir holds no others")

    # ---- 1. the partition -----------------------------------------------------
    print("1. the partition")
    bad_p = sum(1 for r in rosters for c in r["creates"]
                if c["tag"] == agentroster.TAG_PLAYER and c["definition"] is not None)
    bad_n = sum(1 for r in rosters for c in r["creates"]
                if c["tag"] == agentroster.TAG_NPC and c["definition"] is None)
    LEDGER.ok(bad_p == 0, "no player create carries a definition", str(bad_p))
    LEDGER.ok(bad_n == 0, "every NPC create carries one", str(bad_n))

    m148 = {r["capture"]: r for r in rosters
            if r["map_id"] == 148 and r["creates"]}
    LEDGER.ok(set(m148) == set(M148), "both map-148 game connections present",
              str(sorted(m148)))
    for cap, (n_item, n_npc, n_play) in sorted(M148.items()):
        r = m148[cap]
        got = tuple(sum(1 for c in r["creates"] if c["tag"] == t) for t in (0, 2, 3))
        LEDGER.ok(got == (n_item, n_npc, n_play),
                  f"{cap} partitions to item/npc/player = {(n_item, n_npc, n_play)}",
                  str(got))

    # A tag-3 create refuses the mask even when its low bits look like a slot.
    row = agentroster.create_row(2.0, synthetic_create(0x3, 0x05BC, (9.0, 9.0)))
    LEDGER.ok(row["definition"] is None and row["raw"] & 0xFFFF == 0x05BC,
              "a player create's definition is None, not its masked low bits",
              f"raw low16 = {row['raw'] & 0xFFFF:#06x}")

    # ---- 2. the position ------------------------------------------------------
    print("2. the position (the v[3:5] regression)")
    bad_pos = sum(1 for r in rosters for c in r["creates"]
                  if not (isinstance(c["pos"], tuple) and len(c["pos"]) == 2
                          and all(isinstance(v, float) for v in c["pos"])))
    LEDGER.ok(bad_pos == 0, "every decoded position is a 2-tuple of floats",
              f"{total} creates")
    # The synthetic create puts (1, 9) at fields 3/4 and (123.5, -42.0) at field 5.
    row = agentroster.create_row(3.0, synthetic_create(0x2, 1470, (123.5, -42.0)))
    LEDGER.ok(row["pos"] == (123.5, -42.0),
              "position reads field 5, never tuple(v[3:5])",
              f"pos={row['pos']}, decoy fields 3/4 = (1, 9)")
    LEDGER.ok(row["plane"] == 7 and row["speed"] == 1.25 and row["token"] == "nonc",
              "plane, speed and token read their own fields",
              f"{row['plane']}, {row['speed']}, {row['token']!r}")

    # ---- 3. the cross-session station -----------------------------------------
    print("3. the cross-session station (rung 1's exit criterion)")
    a = m148["20260807T143055"]
    b = m148["20260810T235916"]
    join = agentroster.cross_session(a, b)
    LEDGER.ok(PIN in join["both"],
              "slot 1470 / model 116698 / (8436, 4819) stands in BOTH sessions",
              "three days apart, byte-identical")
    for label, r in (("first", a), ("second", b)):
        st = agentroster.stations(r).get(PIN)
        LEDGER.ok(st is not None and st["creates"] == PIN_CREATES
                  and st["agents"] == {PIN_AGENT} and st["tokens"] == {PIN_TOKEN},
                  f"the {label} session saw it x{PIN_CREATES} under agent "
                  f"{PIN_AGENT}, {PIN_TOKEN}",
                  str(st and (st["creates"], sorted(st["agents"]),
                              sorted(st["tokens"]))))
    got = (len(join["both"]), len(join["only_a"]), len(join["only_b"]))
    LEDGER.ok(got == JOIN_148, f"map 148 joins {JOIN_148}", str(got))
    LEDGER.ok(not any(k[0] == agentroster.TAG_PLAYER
                      for part in join.values() for k in part),
              "players never enter the join", "a player is wherever the player walked")

    m164 = [r for r in rosters if r["map_id"] == 164 and r["creates"]]
    LEDGER.ok(len(m164) == 2, "map 164 appears in both captures", str(len(m164)))
    j164 = agentroster.cross_session(m164[0], m164[1])
    got = (len(j164["both"]), len(j164["only_a"]), len(j164["only_b"]))
    LEDGER.ok(got == JOIN_164,
              f"the whole outpost is byte-stable: {JOIN_164}", str(got))

    # ---- 5. sabotage: the unconditional mask ----------------------------------
    print("5. sabotage: mask without partitioning")
    declared = set(a["definitions"]) | set(b["definitions"])
    masked = [c["raw"] & 0xFFFF
              for r in (a, b) for c in r["creates"]
              if c["tag"] == agentroster.TAG_PLAYER]
    LEDGER.ok(len(masked) == MASKED_PLAYERS,
              f"{MASKED_PLAYERS} player creates on the 148 pair", str(len(masked)))
    collisions = [m for m in masked if m in declared]
    phantoms = set(masked) - declared
    LEDGER.ok(len(collisions) == 0,
              "0 masked player words collide with a declared definition",
              f"{len(collisions)} -- so the corruption mode is INVENTION")
    LEDGER.ok(len(phantoms) > 0,
              "the unconditional mask would invent phantom definition slots",
              f"{len(phantoms)} distinct slots no 0x0056 ever declared")

    # ---- 6. refusals and the JSON edge ----------------------------------------
    print("6. refusals and the JSON edge")
    try:
        agentroster.cross_session(dict(a, origin="ours"), b)
        mixed = False
    except agentroster.RosterError:
        mixed = True
    LEDGER.ok(mixed, "cross_session refuses to join ours against live",
              "toolkit/origin.py's rule, enforced here too")
    blob = json.dumps(agentroster._jsonable(rosters))
    LEDGER.ok(len(blob) > 100_000, "the full roster serialises to JSON",
              f"{len(blob):,} bytes (sets and tuples all converted)")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
