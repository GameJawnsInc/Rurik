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
import agentroster  # noqa: E402
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
LEDGER = checks.Ledger("npcdefs: capture -> content rows", floor=59)
# floor 25 -> 32 on 2026-08-16, measured from the green run that added the
# named-capture selection, the fourth-capture proof and the mode plumbing;
# 32 -> 40 on 2026-08-22 with section 7 (field 9 is per-instance, the full
# pool reads without refusing)
# (studies/isle/PLAN.md rung 5). Every new check runs whenever the vault does.
# 42 -> 55 on 2026-09-24 with section 8 (DESKWORK-Q5): --build, the by-name
# refusal of a pool spanning builds, the build stamp on every emitted row, and
# the honest R4c-2 recount over the September map-146 tapes. Sabotaged in a
# scratch driver before the floor was set: require_one_build never refusing
# reddens 3, to_toml dropping the stamp reddens 2.
# 55 -> 59 on 2026-09-24 (the lane's review): a lone capture of unknown build
# is ACCEPTED (it was refused with an impossible remedy), the unknown capture
# beside a known one still refused, `--build NOSUCH` refused rather than a
# TypeError, `--capture 20260817T180610` running as at base; and the map-146
# roster check now READS map 146 (agentroster, map_id == 146, exact set) where
# it tested a subset of the whole pool -- 129 swapped in for 1397 passed that
# and reddens this. The new test run against HEAD's old npcdefs.py reddens 3.

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
    print("\n7. a large single-build pool: field 9 is instantaneous, and read() "
          "no longer refuses on a snare")
    # POOL ONE BUILD. read() pools by definition index, and an index is not a
    # global name across client builds: pooling every live capture refuses on
    # definition 7809, which is a level-5 creature (shell 141285) in the
    # 2026-07-29 build and a level-20 one (shell 16271) in the 2026-09-01 build.
    # That is a real cross-build content drift -- NOT a field-9 snare, and NOT
    # something to average -- so §7's field-9 claim is proved within one build,
    # where the index IS stable. The 2026-08-13 build is chosen because it is a
    # six-capture pool that carries both of the field-9 snares this section pins;
    # the cross-build drift itself is asserted just below.
    POOL_BUILD = "2026-08-13_64fae3b1369b"
    all_caps = npcdefs.live_captures()
    build_caps = npcdefs.live_captures(build=POOL_BUILD)
    LEDGER.ok(len(build_caps) > len(caps) and len(all_caps) > len(build_caps),
              "one build's pool is larger than the three keyed here and smaller "
              "than the whole vault",
              f"{len(build_caps)} in build {POOL_BUILD}, {len(caps)} keyed, "
              f"{len(all_caps)} total")
    # The headline: pooling one build no longer raises. Before 2026-08-22 this
    # refused on definition 159's second field-9 speed.
    try:
        pooled, _iv = npcdefs.read(build_caps)
        pooled_ok = True
    except npcdefs.NpcDefsError as exc:
        pooled, pooled_ok = {}, False
        print(f"   read() refused: {exc}")
    LEDGER.ok(pooled_ok,
              "read() pools one build's captures WITHOUT refusing on field 9",
              "the fix: field 9 is instantaneous, so a second value is a snare, "
              "not a merge conflict")
    LEDGER.ok(len(pooled) > len(defs),
              "and the pool resolves far more definitions than the 3-capture "
              "subset -- what makes the downstream figures stop being "
              "3-capture numbers", f"{len(pooled)} vs {len(defs)}")
    # THE CROSS-BUILD DRIFT, asserted rather than hit as a surprise: pooling the
    # whole vault refuses, and it refuses on 7809's IDENTITY (file_id + level),
    # which is drift, not a field-9 snare. Read each build's 7809 to name both.
    try:
        npcdefs.read(all_caps)
        LEDGER.ok(False, "pooling every build refuses on 7809's cross-build drift",
                  "it did not refuse")
    except npcdefs.NpcDefsError as exc:
        LEDGER.ok("7809" in str(exc) and "declared twice" in str(exc),
                  "pooling every build refuses on 7809's cross-build drift -- an "
                  "index is not a global name across builds",
                  str(exc).splitlines()[0])
    july = npcdefs.read(npcdefs.live_captures(build="2026-07-29_221c13772c7a"))[0]
    sept = npcdefs.read(npcdefs.live_captures(build="2026-09-01_44fbd68767a8"))[0]
    LEDGER.ok(7809 in july and 7809 in sept
              and july[7809].payload[0] == 141285 and july[7809].payload[6] == 5
              and sept[7809].payload[0] == 16271 and sept[7809].payload[6] == 20,
              "7809 is a DIFFERENT creature per build: shell 141285 level 5 in "
              "2026-07-29, shell 16271 level 20 in 2026-09-01 -- a real drift, "
              "not the instantaneous field-9 value §7 is about",
              f"july {july[7809].payload[0]}/{july[7809].payload[6]}, "
              f"sept {sept[7809].payload[0]}/{sept[7809].payload[6]}"
              if 7809 in july and 7809 in sept else "7809 missing")
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

    # ---- 8. a definition index is scoped by build: --build, the refusal, the
    #         build on every row, and the honest R4c-2 recount --------------
    print("\n8. --build: the pool is one build or it is refused by name "
          "(DESKWORK-Q5)")
    groups = npcdefs.builds_of(all_caps)
    LEDGER.ok(len(groups) >= 5 and None in groups
              and sum(len(v) for v in groups.values()) == len(all_caps),
              "builds_of partitions every keyed capture, and the one capture "
              "with no exe in its manifest keys as None rather than vanishing",
              f"{ {k: len(v) for k, v in groups.items()} }")
    try:
        npcdefs.require_one_build(all_caps)
        why = ""
    except npcdefs.NpcDefsError as exc:
        why = str(exc)
    LEDGER.ok(bool(why) and all(k in why for k in groups if k)
              and "unknown" in why and "20260817T180610" in why
              and "--build" in why,
              "the whole vault is REFUSED, naming every build, the unknown "
              "capture by stamp, and the flag that selects one",
              why.splitlines()[0] if why else "not refused")
    LEDGER.ok(npcdefs.require_one_build(build_caps) == POOL_BUILD,
              f"one build's pool passes and names itself ({POOL_BUILD})")
    # A pool of ONE capture is accepted whatever its build -- one capture
    # cannot span two -- and names no build when its manifest names no exe.
    # The first version refused the lone unknown capture and told the
    # operator to pass the --capture STAMP they had just passed; at base
    # `--capture 20260817T180610` ran (8 declared, 0 hostile), so that was a
    # regression with no flag to restore it.
    unknown = [c for c in all_caps if npcdefs.capture_build(c) is None]
    try:
        lone = npcdefs.require_one_build(unknown)
    except npcdefs.NpcDefsError as exc:
        lone = f"REFUSED: {exc}"
    LEDGER.ok(len(unknown) == 1 and lone is None,
              "a pool of ONE capture passes whatever its build: the capture "
              "with no exe in its manifest is accepted alone and names no "
              "build (None -- no stamp is written for it)",
              f"{[os.path.basename(c) for c in unknown]} -> {str(lone)[:60]}")
    try:
        npcdefs.require_one_build(unknown + build_caps[:1])
        mixed = ""
    except npcdefs.NpcDefsError as exc:
        mixed = str(exc)
    LEDGER.ok("unknown" in mixed and POOL_BUILD in mixed,
              "and the same capture beside ONE of a known build is refused "
              "naming both -- an unknown build is not 'any build'",
              mixed.splitlines()[0] if mixed else "not refused")
    # The CLI: a bare census refuses; --build selects. main() takes argv so
    # the plumbing is exercised, not re-derived.
    import contextlib
    import io
    try:
        npcdefs.main([])
        bare = "ran"
    except npcdefs.NpcDefsError as exc:
        bare = str(exc)
    LEDGER.ok(bare != "ran" and "refusing to pool" in bare,
              "a bare `npcdefs` census over the whole vault is REFUSED",
              bare.splitlines()[0][:80])
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = npcdefs.main(["--build", "2026-07-29_221c13772c7a"])
    LEDGER.ok(rc == 0 and "3 capture(s) of build 2026-07-29_221c13772c7a" in buf.getvalue()
              and f"{DEFINITIONS} definition(s) declared" in buf.getvalue(),
              f"`--build 2026-07-29_221c13772c7a` runs the census over its three "
              f"captures and finds the {DEFINITIONS} pinned definitions",
              buf.getvalue().splitlines()[0][:90])
    # A mistyped key is REFUSED naming the builds the vault holds. The first
    # version crashed here instead: the refusal sorted a set holding None
    # (the unknown capture) against str.
    try:
        npcdefs.main(["--build", "NOSUCH"])
        bad = "ran"
    except npcdefs.NpcDefsError as exc:
        bad = str(exc)
    except TypeError as exc:
        bad = f"TypeError: {exc}"
    LEDGER.ok(bad.startswith("no keyed live capture of build 'NOSUCH'")
              and POOL_BUILD in bad and "'unknown'" in bad,
              "`--build NOSUCH` is REFUSED naming the vault's builds, the "
              "unknown one included -- not a TypeError", bad[:100])
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            rc = npcdefs.main(["--capture", os.path.basename(unknown[0])])
        except npcdefs.NpcDefsError as exc:
            rc = f"REFUSED: {exc}"
    LEDGER.ok(rc == 0 and "1 capture(s) of build unknown" in buf.getvalue()
              and "8 definition(s) declared, 0 hostile" in buf.getvalue(),
              "`--capture 20260817T180610` alone runs as it did at base (8 "
              "declared, 0 hostile), printed as build unknown",
              (buf.getvalue().splitlines() or [str(rc)])[0][:90])
    # Every emitted row says which build it was read from, and content.py
    # loads the stamped rows.
    text = npcdefs.to_toml(host, build="2026-07-29_221c13772c7a")
    LEDGER.ok(text.count('build = "2026-07-29_221c13772c7a"') == len(host)
              and 'build = "2026-07-29_221c13772c7a"' in text.split("[npc.def_1442.provenance]")[1].split("[npc.")[0],
              f"to_toml(build=...) writes `build` into all {len(host)} rows' "
              f"provenance", "under each row's [provenance], beside capture and origin")
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "npcs.toml"), "w", encoding="utf-8") as fh:
            fh.write(text)
        world = content.load(repo_dir=tmp, vault_dir="")
        prov = world.get("npc", "def_1442").provenance
    LEDGER.ok(prov.get("build") == "2026-07-29_221c13772c7a",
              "and content.py loads the stamped rows with the build readable off "
              "the row", repr(prov.get("build")))
    LEDGER.ok("build = " not in npcdefs.to_toml(host),
              "CONTROL: with no build given the rows carry none -- the stamp is "
              "a fact, never a default")
    # THE HONEST R4c-2 RECOUNT (PLAN.md 3.2). The September (2026-09-01
    # build) map-146 tapes, per definition, never pooled across builds: six
    # of the original seven hostiles are created there (1434 is not), and
    # seven definitions the 2026-08-11 corpus never saw. Pinned as literals.
    sept = npcdefs.read(npcdefs.live_captures(build="2026-09-01_44fbd68767a8"))[0]
    sept_host = npcdefs.hostile(sept)
    LEDGER.ok(len({i: d for i, d in sept.items() if d.declared}) == 294
              and len(sept_host) == 40,
              "the 2026-09-01 build's 13-capture pool declares 294 definitions, "
              "40 hostile (every map: the Isle's furniture is in there)",
              f"{len(sept)} declared, {len(sept_host)} hostile")
    ON_146 = {1346, 1397, 1405, 1409, 1411, 1420, 1421, 1428, 1431, 1432,
              1433, 1437, 1442}
    # THE MAP FILTER IS THE CHECK. The first version asserted only that
    # ON_146 is a subset of the whole September pool's 40 hostiles -- 21 of
    # which are the Isle's (129..165, 2937) and 6 map 430's -- so 129 swapped
    # in for 1397 passed it. The roster is read per connection with its
    # VERSION frame's map_id, and the hostile definitions CREATED on map 146
    # must equal the 13 exactly.
    rosters = agentroster.read_roster(
        npcdefs.live_captures(build="2026-09-01_44fbd68767a8"))
    on146 = [r for r in rosters if r["map_id"] == 146]
    created = {c["definition"] for r in on146 for c in r["creates"]
               if c["tag"] == agentroster.TAG_NPC
               and c["token"] in npcdefs.HOSTILE_TOKENS}
    LEDGER.ok(len(on146) == 5 and len({r["capture"] for r in on146}) == 4
              and created == ON_146,
              "the September tapes reach map 146 in 5 connections of 4 "
              "captures, and the hostile definitions CREATED there (mon1/band "
              "on an NPC-tag create) are EXACTLY the 13",
              f"{len(on146)} connection(s); created - pinned = "
              f"{sorted(created - ON_146)}, pinned - created = "
              f"{sorted(ON_146 - created)}")
    LEDGER.ok(1434 not in created and (ON_146 & HOSTILE) == HOSTILE - {1434}
              and ON_146 <= set(sept_host),
              "1434 is not created on any September map-146 tape; six of the "
              "original seven are; all 13 are hostile in the build's own pool",
              f"missing from the pool: {sorted(ON_146 - set(sept_host))}")
    LEDGER.ok(sept[1431].health and sept[1431].health[0][1] == 56
              and sept[1432].health and sept[1432].health[0][1] == 96
              and sept[1437].health and sept[1437].health[0][1] == 64
              and sept[1397].attack == (1.9, 1.0)
              and sept[1431].attack == (1.75, 1.0)
              and sept[1432].attack == (1.75, 1.0)
              and sept[1437].attack == (2.475, 1.0)
              and not sept[1397].health,
              "and the four with a stat past the declaration: three with a "
              "health reading (1431 56, 1432 96, 1437 64) and four with an "
              "attack rate (1397 1.9, 1431 1.75, 1432 1.75, 1437 2.475) -- the "
              "first version's label left 1431/1432's rates out",
              f"1431 {sept[1431].health} {sept[1431].attack} 1432 "
              f"{sept[1432].health} {sept[1432].attack} 1437 {sept[1437].health} "
              f"{sept[1437].attack} 1397 {sept[1397].health} {sept[1397].attack}")
    # The one cross-build disagreement, counted rather than met: 7809 alone.
    july_d = {i for i, d in july.items() if d.declared}
    sept_d = {i for i, d in sept.items() if d.declared}
    differ = sorted(i for i in july_d & sept_d if july[i].payload != sept[i].payload)
    LEDGER.ok(differ == [7809],
              f"of the {len(july_d & sept_d)} indices both builds declare, "
              f"exactly ONE has a different body: 7809", f"{differ}")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
