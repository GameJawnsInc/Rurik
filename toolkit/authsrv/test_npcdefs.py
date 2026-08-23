r"""The capture -> content compiler, and the join that decides whether it lies.

THE HEADLINE IS THE WEAK HALF. "126 of 126 declarations re-encode to ArenaNet's own
bytes" is worth its exit code only because of what sits under it: a compiler that
stored the declaration blob and replayed it would print the same number while
understanding nothing. So the rows are rebuilt FIELD BY FIELD out of the extractor's
own typed output -- definition, file_id, scale, flags, profession, level, enc_name --
and handed to the codec fresh. If any field is mis-typed or mis-ordered the bytes move.

THE CHECK THAT EARNED THE FILE is section 3. A property message must be joined to the
create IN EFFECT AT ITS TIMESTAMP, because agent ids are recycled. In this corpus:

    20260807T143055  :62994  agent 38  t=18.169  PROP_HEALTH_MAX = 8
        interval join    -> definition 1434 `mon1`   <- correct
        last-create-wins -> definition 1343 `anim`   <- wrong, and green 99.8% of the time

That is one of the FIVE NPC health readings in existence, so the naive join corrupts
20% of the strongest evidence this project has about a server-only stat. Three readers
have made that mistake here. So the test asserts BOTH answers rather than the right
one: the day they agree, the control says so instead of passing.

THE FIRST VERSION OF THIS FILE DID NOT CATCH THAT SABOTAGE, and the reason is worth
more than the check. Section 3 originally asserted the aggregate `{1346: 96, 1434: 8,
1442: 40}` -- and running the naive join against the real corpus leaves that map
COMPLETELY UNCHANGED, because agent 43 in the other capture observes 1434 = 8
independently and its last create really is 1434. **The redundancy that makes the
finding strong -- two captures, three days apart, agreeing -- is exactly what made the
check blind to a misattribution.** What catches it is pinning the ATTRIBUTION: the
per-definition event counts (1434 drops from two events to one) and the rule that no
non-hostile definition may carry a health reading (1343 `anim` gains one). Both halves
of the move, from both sides.

Three sabotages were run against the extractor and all three fail the suite:

  * the naive join                        -> 2 red checks (section 3)
  * `_f32` reinterpreting instead of      -> 2 red checks (section 4)
    reading the dword's bits

FIELD 9 IS PER-INSTANCE TOO, and this file used to say otherwise. Until
2026-08-22 `read()` REFUSED on a second field-9 value ("field 9 is
single-valued per definition"), which was true only of the three-capture
subset this test pins and blocked the full 15-capture pool -- so every
unitassembly/unitmodels figure downstream was a 3-capture number. It is
false: field 9 is the agent's speed AT THE CREATE TICK, so a snared create
reports a reduced value. Section 7 pools ALL live captures, shows `read()`
no longer refuses, and pins the two definitions (159, 114) whose creates
caught a snare -- base preserved as the max, the reduced state recorded.
Field 10 stays unread as speed for the reason the module docstring gives
(it is per-instance and carries unrelated values).

Sections 0-2 and 6 need `vault/captures/live/`; without it they skip and the floor
takes the run red. ArenaNet's own bytes are the only oracle for any of this.

    python toolkit/authsrv/test_npcdefs.py
"""
import os
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
import checks  # noqa: E402
import content  # noqa: E402
import npcdefs  # noqa: E402
import tape  # noqa: E402
from codec import Codec  # noqa: E402

# Floor 23, measured from a green run on 2026-08-11: 4 corpus + 3 declaration +
# 2 round-trip + 4 interval/sabotage + 3 typing + 4 row-shape + 3 content-gate. Every
# vault-dependent section declares its skips, so a run without the live captures lands
# below the floor and goes RED -- which is the point, since a compiler checked against
# nothing is the failure checks.py exists for.
LEDGER = checks.Ledger("npcdefs: capture -> content rows", floor=40)
# floor 25 -> 32 on 2026-08-16, measured from the green run that added the
# named-capture selection, the fourth-capture proof and the mode plumbing;
# 32 -> 40 on 2026-08-22 with section 7 (field 9 is per-instance, the full
# pool reads without refusing)
# (studies/isle/PLAN.md rung 5). Every new check runs whenever the vault does.

# Measured 2026-08-11 over the three keyed captures. Written as literals rather than
# computed from the module under test, because a symbol appearing in a test file is not
# a check -- test_agentlife.py's section 9 is the standing reminder: twelve of fourteen
# constants could be set to a wrong value with 125 checks green.
HOSTILE = {1346, 1420, 1421, 1431, 1432, 1434, 1442}
HEALTH = {1346: 96, 1434: 8, 1442: 40}
DECLARATIONS, DEFINITIONS, INSTANTIATED = 126, 54, 48
SURROGATE_DEFS = {397, 1469, 1473, 1488, 1505, 7809}
# The corpus every count above was measured on. A LIST OF NAMES, deliberately:
# the pins are facts about these captures, not about whatever the vault holds.
CAPTURES = ("20260807T133758", "20260807T143055", "20260810T235916")


def main():
    codec = Codec()
    try:
        # NAMED, not globbed. Every pin below (126 declarations, 54 definitions,
        # the health map) is a fact about THESE THREE captures; unfiltered, the
        # day a fourth keyed capture lands -- the Isle sessions are exactly that
        # -- six pins go red at once for a reason that is not a defect
        # (studies/isle/PLAN.md gap 4). The refusal in live_captures(names=...)
        # keeps this from silently matching nothing if a stamp is renamed.
        caps = npcdefs.live_captures(names=CAPTURES)
    except SystemExit:
        caps = []
    if not caps:
        for why in ("the corpus frames clean", "declarations agree",
                    "rows re-encode to ArenaNet's bytes", "the interval join"):
            LEDGER.skip(why, "no decrypted live captures in the vault")
        return LEDGER.verdict()

    defs, intervals = npcdefs.read(caps, codec)
    declared = {i: d for i, d in defs.items() if d.declared}
    host = npcdefs.hostile(defs)

    # ---- 0. the corpus this is compiled from ---------------------------------
    print("0. the corpus")
    LEDGER.ok(len(caps) == 3, "three keyed live captures", f"{len(caps)}")

    # THE FOURTH-CAPTURE PROOF (studies/isle/PLAN.md rung 5's exit criterion):
    # a synthetic keyed capture dropped into the vault must not move a single
    # pin, because the pins select by NAME. Built and removed inside one try --
    # the suite already writes selftest captures into the vault, so a marker
    # directory is within precedent, and the finally keeps it from surviving.
    synth = os.path.join(os.path.dirname(caps[0]), "_synthetic_test_19700101")
    try:
        os.makedirs(synth, exist_ok=True)
        open(os.path.join(synth, "game-synthetic.jsonl"), "w").close()
        unfiltered = npcdefs.live_captures()
        named = npcdefs.live_captures(names=CAPTURES)
        LEDGER.ok(any(os.path.basename(p) == "_synthetic_test_19700101"
                      for p in unfiltered),
                  "a fourth keyed capture IS seen by the unfiltered glob",
                  f"{len(unfiltered)} dirs -- so this check can tell the "
                  f"filter from a vault that never changed")
        LEDGER.ok([os.path.basename(p) for p in named] == sorted(CAPTURES),
                  "and the NAMED selection does not move",
                  "the pins are facts about these three captures")
    finally:
        try:
            os.remove(os.path.join(synth, "game-synthetic.jsonl"))
            os.rmdir(synth)
        except OSError:
            pass

    # The mode plumbing (gap 5): all three captures predate manifest recording,
    # so they resolve 'unrecorded'; a declaration fills in; and the refusal that
    # protects the pooled emit is exercised on a synthetic manifest pair.
    LEDGER.ok(all(npcdefs.capture_mode(c) == "unrecorded" for c in caps),
              "all three captures honestly read mode=unrecorded",
              "their manifests carry game_mode: null")
    LEDGER.ok(npcdefs.resolve_mode(caps) == "unrecorded"
              and npcdefs.resolve_mode(caps, declared="base") == "base",
              "resolve_mode: unrecorded pools default, a declaration fills in")
    with tempfile.TemporaryDirectory() as td:
        a_dir = os.path.join(td, "a")
        b_dir = os.path.join(td, "b")
        os.makedirs(a_dir)
        os.makedirs(b_dir)
        with open(os.path.join(a_dir, "manifest.json"), "w") as fh:
            fh.write('{"game_mode": "base"}')
        with open(os.path.join(b_dir, "manifest.json"), "w") as fh:
            fh.write('{"game_mode": "reforged"}')
        try:
            npcdefs.resolve_mode([a_dir, b_dir])
            mixed_ok = False
        except npcdefs.NpcDefsError:
            mixed_ok = True
        try:
            npcdefs.resolve_mode([a_dir], declared="reforged")
            contra_ok = False
        except npcdefs.NpcDefsError:
            contra_ok = True
        LEDGER.ok(mixed_ok, "base + reforged captures REFUSE to pool",
                  "their stats differ ~20% -- two games, not one dataset")
        LEDGER.ok(contra_ok, "a declaration contradicting the manifest is REFUSED",
                  "the manifest was written at capture time")
        LEDGER.ok(npcdefs.resolve_mode([a_dir]) == "base",
                  "and a recorded mode is used without any flag",
                  "gap 5's whole point")
    LEDGER.ok(len(declared) == DEFINITIONS,
              f"{DEFINITIONS} definitions are declared", f"{len(declared)}")
    instantiated = sum(1 for d in declared.values() if d.creates)
    LEDGER.ok(instantiated == INSTANTIATED,
              f"{INSTANTIATED} of them are ever created", f"{instantiated}")
    # The client's own `index < m_count` assert makes this one load-bearing: an agent
    # whose definition was never declared takes the client down. ArenaNet never does it.
    LEDGER.ok(all(d.declared for d in defs.values()),
              "and ZERO agents are created against a definition never declared",
              "the client asserts index < m_count on exactly this")

    # ---- 1. the declarations agree with themselves ---------------------------
    print("\n1. declarations")
    total_decl = sum(len(d.connections) for d in declared.values())
    LEDGER.ok(total_decl >= DEFINITIONS,
              "every definition is declared at least once", f"{total_decl} declaration sites")
    repeated = sum(1 for d in declared.values() if len(d.connections) > 1)
    LEDGER.ok(repeated == 38,
              "38 are declared in more than one connection and none disagrees",
              f"{repeated}; npcdefs.declare() RAISES on a disagreement, so a green run "
              f"here is the assertion")
    LEDGER.ok(set(host) == HOSTILE,
              "the hostile partition is exactly the seven measured definitions",
              f"{sorted(host)}")

    # ---- 2. the round trip, rebuilt field by field ---------------------------
    print("\n2. our extracted rows re-encode to ArenaNet's own bytes")
    identical = differing = 0
    for capture_dir in caps:
        for row in tape.channel_files(capture_dir):
            _info, events = tape.load_tape(capture_dir, row["connection"])
            blob = b"".join(b for _t, b in events)
            framed, consumed, _err = codec.decode_stream_at("GAME_SMSG", blob, 0)
            for i, (off, opcode, values) in enumerate(framed):
                if opcode != npcdefs.NPC_PROPERTIES:
                    continue
                end = framed[i + 1][0] if i + 1 < len(framed) else consumed
                r = defs[values[1]].row()
                # Rebuilt from the TYPED row, not from the captured message. A compiler
                # that kept the original blob would pass by memcpy; this cannot.
                rebuilt = codec.encode(
                    "GAME_SMSG", npcdefs.NPC_PROPERTIES,
                    [r["definition"], r["file_id"], 0, r["scale"], 0, r["flags"],
                     r["profession"], r["level"],
                     "".join(chr(w) for w in r["enc_name"])],
                    header_value=values[0])
                if rebuilt == blob[off:end]:
                    identical += 1
                else:
                    differing += 1
    LEDGER.ok(identical == DECLARATIONS and differing == 0,
              f"{DECLARATIONS} of {DECLARATIONS} declarations rebuild byte-identically",
              f"{identical} identical, {differing} differing")
    # Six definitions carry an EncString word in the UTF-16 surrogate range, and until
    # codec.py's string16 fix (2026-08-11) `str.encode('utf-16-le')` raised on every one
    # of them -- so this server could not have sent these six NPCs at all. The round
    # trip above therefore also proves the codec fix, on ArenaNet's own data.
    sur = {i for i, d in declared.items()
           if any(0xD800 <= w <= 0xDFFF for w in d.row()["enc_name"])}
    LEDGER.ok(sur == SURROGATE_DEFS,
              "six definitions carry a SURROGATE EncString word -- unsendable before "
              "the string16 fix", f"{sorted(sur)}")

    # ---- 3. the interval join, and the sabotage that must disagree -----------
    print("\n3. the interval join (the check that earned this file)")
    iv = intervals.get(("20260807T143055",
                        [c for c in intervals if c[0] == "20260807T143055"
                         and ":62994" in c[1]][0][1])) if intervals else None
    if iv is None:
        LEDGER.skip("the agent-38 trap", "capture 20260807T143055 :62994 not loaded")
        LEDGER.skip("the naive join disagrees", "same")
    else:
        correct = iv.at(38, 18.169)
        naive = iv.last(38)
        LEDGER.ok(correct == (1434, "mon1"),
                  "agent 38's health at t=18.169 joins to definition 1434 `mon1`",
                  f"{correct}")
        # THE CONTROL. If these two ever agree, the trap has stopped being a trap and
        # every later reader would take a green run as proof the join is right.
        LEDGER.ok(naive == (1343, "anim") and naive != correct,
                  "and last-create-wins gives 1343 `anim` -- the two MUST disagree",
                  f"naive={naive}; if this ever matches, the fixture no longer "
                  f"exercises the defect and the check above is vacuous")

    LEDGER.ok({i: d.health[0][1] for i, d in host.items() if d.health} == HEALTH,
              "the three hostile health readings are 1346=96, 1434=8, 1442=40",
              "five prop-42 events resolve to an NPC; 1442 is read twice at 40")
    LEDGER.ok(sum(len(d.health) for d in defs.values()) == 5,
              "and there are exactly five of them in the whole corpus",
              "the rung is coverage-blocked, not instrument-blocked -- say the number")

    # THE CHECK THAT ACTUALLY CATCHES THE NAIVE JOIN, and the two above do NOT.
    # Measured: sabotaging read() to use last-create-wins leaves the aggregate
    # {1346: 96, 1434: 8, 1442: 40} completely UNCHANGED, because agent 43 in the other
    # capture observes 1434 = 8 independently and its last create really is 1434. The
    # redundancy that makes the finding strong -- two captures, three days apart,
    # agreeing -- is exactly what makes an aggregate check blind to a misattribution.
    # So pin the ATTRIBUTION: the per-definition event COUNTS, over every definition
    # rather than the hostile ones. Under the naive join 1434 drops to one event and
    # 1343 `anim` gains one, and both halves of that move are caught here.
    events = {i: sorted(v for _c, v in d.health) for i, d in defs.items() if d.health}
    LEDGER.ok(events == {1346: [96], 1434: [8, 8], 1442: [40, 40]},
              "each health event is attributed to the definition it was measured on",
              f"{events} -- an aggregate of the VALUES cannot see the naive join; the "
              f"per-definition counts can")
    LEDGER.ok(all(defs[i].hostile for i in events),
              "and no non-hostile definition carries a health reading at all",
              "the naive join hands one to 1343 `anim`, which is the same defect from "
              "the other side")

    # ---- 4. field typing -----------------------------------------------------
    print("\n4. typing: dwords that hold floats, and the field that is per-instance")
    LEDGER.ok(defs[1346].attack == (2.0, 1.0) and defs[1442].attack == (1.75, 1.0),
              "attack rates decode as dwords HOLDING floats", f"{defs[1346].attack}")
    # The ROTATE_PLAYER trap from the other side: reading the raw dword as a float32
    # gives 2.5e-39, which is not 2.0 and is not obviously wrong in a log either.
    raw = struct.unpack("<f", struct.pack("<I", 0x40000000))[0]
    LEDGER.ok(abs(raw - 2.0) < 1e-9 and npcdefs._f32(0x40000000) == raw,
              "and _f32 is that conversion, not a reinterpretation of the field",
              "the wire type is dword and the client's own table says so")
    LEDGER.ok(defs[1442].move_speed == 12.0 and not defs[1442].reduced_speeds,
              "move_speed is create field 9's BASE (max); 1442 is a clean 12.0",
              "1442 is 12.0 in 202 of 202 creates, which reproduces the hand-written "
              "speed in content/npcs.toml -- and it is never snared, so no reduced "
              "value. Field 9 being per-instance is section 7's ground.")

    # ---- 5. what a row refuses to carry --------------------------------------
    print("\n5. the row's shape")
    r = defs[1442].row()
    LEDGER.ok(not ({"name", "armor", "armour", "energy", "allegiance"} & set(r)),
              "no name, no armour, no energy, no allegiance",
              "each absent for a measured reason, not caution -- see the docstring")
    LEDGER.ok(isinstance(r["enc_name"], list)
              and all(isinstance(w, int) for w in r["enc_name"]),
              "enc_name is a list of string IDS, never decoded text",
              "the ruling's commit-the-id half, and TOML cannot hold a lone surrogate")
    LEDGER.ok(r["enc_name"] == [0x0F41, 0xBE66, 0xF22A, 0x04D4],
              "and 1442's four words are the ones content/npcs.toml already ships",
              "the shipped row was hand-written from this capture; the compiler agrees")
    LEDGER.ok(defs[1431].row()["file_id"] == defs[1434].row()["file_id"],
              "1431/1432/1434 share one file id at three levels",
              "one wiki page can be three definition slots -- which is why R4c-2 must "
              "be graded in slots, not names")

    # ---- 6. the emitted rows load, and the mode gate holds -------------------
    print("\n6. the emitted TOML loads through content.py")
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "npcs.toml"), "w", encoding="utf-8") as fh:
            fh.write(npcdefs.to_toml(host))
        world = content.load(repo_dir=tmp, vault_dir="")
    LEDGER.ok(world.census().get("npc") == len(host),
              f"all {len(host)} hostile rows load", f"{world.census()}")
    LEDGER.ok(world.get("npc", "def_1442")["move_speed"] == 12.0,
              "and a row round-trips through TOML with its values intact")
    # The mode gate: a stat row that does not say which game mode produced it is
    # refused, because Reforged scales health ~20% and cannot be recovered afterwards.
    with tempfile.TemporaryDirectory() as tmp:
        text = npcdefs.to_toml(host).replace('mode = "unrecorded"\n', "")
        with open(os.path.join(tmp, "npcs.toml"), "w", encoding="utf-8") as fh:
            fh.write(text)
        try:
            content.load(repo_dir=tmp, vault_dir="")
            refused = False
        except content.ContentError as exc:
            refused = "mode" in str(exc)
    LEDGER.ok(refused,
              "CONTROL: strip `mode` from the health rows and content.py REFUSES them",
              "an unstamped health number is base or base x 0.8 forever")

    # ---- 7. field 9 is per-instance, and the full pool now READS -------------
    print("\n7. the full live pool: field 9 is instantaneous, and read() no "
          "longer refuses on a snare")
    all_caps = npcdefs.live_captures()
    LEDGER.ok(len(all_caps) > len(caps),
              "the vault holds more captures than the three keyed here",
              f"{len(all_caps)} total vs {len(caps)} keyed -- the pool this "
              f"section proves is readable")
    # The headline: pooling EVERY live capture no longer raises. Before
    # 2026-08-22 this refused on definition 159's second field-9 speed.
    try:
        pooled, _iv = npcdefs.read(all_caps)
        pooled_ok = True
    except npcdefs.NpcDefsError as exc:
        pooled, pooled_ok = {}, False
        print(f"   read() refused: {exc}")
    LEDGER.ok(pooled_ok,
              "read() pools all live captures WITHOUT refusing on field 9",
              "the fix: field 9 is instantaneous, so a second value is a snare, "
              "not a merge conflict")
    LEDGER.ok(len(pooled) > len(defs),
              "and the pool resolves far more definitions than the 3-capture "
              "subset -- what makes the downstream figures stop being "
              "3-capture numbers", f"{len(pooled)} vs {len(defs)}")
    # The two definitions whose creates caught a snare, pinned by name.
    LEDGER.ok(159 in pooled and pooled[159].move_speed == 288.0
              and pooled[159].reduced_speeds == [144.0],
              "def 159: base 288, one reduced state 144 = 288 x 0.5 (a snare)",
              f"speeds={dict(pooled.get(159).speeds) if 159 in pooled else None}")
    LEDGER.ok(114 in pooled and pooled[114].move_speed == 288.0
              and pooled[114].reduced_speeds == [230.4],
              "def 114: base 288, one reduced state 230.4 = 288 x 0.8",
              f"speeds={dict(pooled.get(114).speeds) if 114 in pooled else None}")
    # The base is the MAX, not the min or the mode-by-accident: a reduced
    # value must never become the base.
    reduced_defs = [i for i, d in pooled.items() if d.reduced_speeds]
    LEDGER.ok(all(pooled[i].move_speed > max(pooled[i].reduced_speeds)
                  for i in reduced_defs) and reduced_defs,
              "every reduced value is strictly BELOW its definition's base -- "
              "a snare only reduces, and no create exceeds the base",
              f"{len(reduced_defs)} definitions carry a reduced speed")
    # The whole family is tiny: field 9 is a base with rare snare exceptions,
    # not a per-instance free-for-all (which is what field 10 would look like).
    total_reduced = sum(len(d.reduced_speeds) for d in pooled.values())
    LEDGER.ok(total_reduced <= 5,
              "only a handful of definitions are ever seen snared -- field 9 "
              "reads as a base, not per-instance noise",
              f"{total_reduced} definitions with any reduced speed")
    # A row carries its snare states so the fact is on file, not lost.
    LEDGER.ok(pooled[159].row().get("move_speed_reduced") == [144.0],
              "and the reduced state reaches the content row as evidence",
              "move_speed_reduced is on the row only when a snare was seen")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
