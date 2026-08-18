"""The content store: that it loads, that the rows are the ones we migrated, and --
the part that matters -- that its two refusals actually refuse.

A loader with a provenance rule nobody has watched reject anything is a comment with
extra steps. So most of this file constructs rows that SHOULD be rejected and asserts
they are: a row with no provenance, a row with an invented source, and a row citing an
all-rights-reserved upstream with nothing recorded about what we verified. That last
one is the licence rule from PLAN.md section 1.1 turned into a load error, and it is
the reason this store can be trusted to grow.

The other half is a regression gate on the migration itself. `content/*.toml` replaced
Python literals on 2026-08-06, and the failure mode of that kind of move is a value
quietly changing. The expected numbers below were read off the pre-migration modules,
so a wrong edit to the TOML reddens here rather than at the client.

    python toolkit/test_content.py
"""
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "authsrv"))
import checks  # noqa: E402
import content  # noqa: E402

# 4 load + 7 migration + 8 refusal + 4 extracted-source (the 2026-08-11 loosening,
# PLAN.md section 7 Q3: three refusals and one positive) + 4 source-condition (the
# hole that ruling left on its first day: measured/capture/wiki had no conditions --
# three refusals and one positive for the measured/build asymmetry) + 4 game-mode
# (Reforged scales health/armour ~20% and cannot be recovered afterwards)
# + 3 overlay + 2 shape. It was 22 until rung C2 added a ninth map
# row: the migration section now names the addition instead of pinning a length, so a
# new row is a decision somebody wrote down rather than a number that drifted.
#
# That itemisation sums to 36 while a real run scored 38, so two checks were added at
# some point without touching the tally and the floor had been carrying two checks of
# slack. It is set from a MEASURED run below rather than from the sum, which is the rule
# the drift broke.
#
# The four checks added 2026-08-13 are the first here to read the REAL `vault/content/`
# overlay, which is gitignored and machine-local -- so the floor is the VAULT-LESS score:
# a bare machine declares one skip and scores 39 (MEASURED with RURIK_VAULT pointed at an
# empty directory), a machine whose overlay carries a row with a source in EXTRACTED
# scores 42, and one whose overlay has rows but no such row scores 40 and declares the
# mutation skip. That last case is not hypothetical and is why the mutation target is
# chosen by PARSING rather than by grepping for `extractor = "`: an extractor on a row
# OUTSIDE `EXTRACTED` is inert -- `capture` rows carry the field and nothing validates
# it -- so the grep version picked a row with no condition-1 claim to break, got no
# refusal, and reddened naming the gate while the gate was fine. It did that within
# minutes of landing, when a parallel session removed `effects.toml` and left
# `npcs.toml`, whose rows are all `capture`.
#
# They exist because every other check in this file passes `vault_dir=""` or a temp dir.
# For the whole life of the file the store's own overlay -- the input the server, the
# harness and `deploy.py` actually load -- was the one input it never read, and the bare
# `content.load()` it opened with was a fixture rather than a claim. On 2026-08-13 the
# overlay shipped 2,077 effect rows citing an extractor that had not been committed;
# `_check_extracted` refused them, `content.load()` raised for every caller, and this
# file did not go red -- it DIED at line 1 of main() with a traceback and printed no
# verdict, no ledger and no floor shortfall, which is the one failure `checks.py` cannot
# see.
#
# Which of the four are load-bearing was MEASURED, not assumed -- four sabotages, and the
# two that matter are the ones the pre-existing checks survive:
#   A  the extractor deleted (the real defect):  3 red, and the two synthetic overlay
#      checks stay GREEN -- previously a traceback with no verdict at all
#   B  the overlay emptied:                      1 red (the contribution check alone)
#   C  the existence check gutted:               2 red, one synthetic and one here
#   D  the vault dropped from load()'s dirs:     4 red, two synthetic and two here
# C and D are caught by the synthetic checks too; A and B are caught by nothing else, and
# A is the one that actually happened.
LEDGER = checks.Ledger("content store", floor=39)


def write(dirpath, name, text):
    with open(os.path.join(dirpath, name), "w", encoding="utf-8") as fh:
        fh.write(text)
    return dirpath


def refuses(toml_text, because):
    """Load a one-file store and return the ContentError message, or None."""
    with tempfile.TemporaryDirectory() as tmp:
        write(tmp, "t.toml", toml_text)
        try:
            content.load(repo_dir=tmp, vault_dir="")
        except content.ContentError as exc:
            return str(exc)
        return None


# A minimal row that must always load. It carries an `extractor` because `measured` is in
# EXTRACTED as of 2026-08-11 -- this constant was `source = "measured"` alone and stopped
# loading the moment that landed, which is the ripple worth noticing: a shared fixture is
# the first thing a tightened rule breaks, and if it had been silently loosened instead of
# fixed, every check downstream of it would have been testing a weaker rule than the one
# that ships.
GOOD_PROV = ('[thing.a.provenance]\nsource = "measured"\n'
             'extractor = "toolkit/content.py"\n')


def main():
    # This is the call the server, `deploy.py` and every tool actually make, and it
    # reads the REAL `vault/content/` overlay. Until 2026-08-13 it was made bare --
    # `world = content.load()` -- and that is the whole of what this file knew about
    # the overlay: not a check, just a fixture. When the overlay shipped 2,077 effect
    # rows citing an extractor that had not been committed, `_check_extracted` refused
    # them (correctly -- that is condition 1 of the 2026-08-11 ruling doing its job)
    # and this line RAISED. The run died at it: no verdict, no ledger, no floor
    # shortfall, a traceback from line 82. That is worse than a red test and is exactly
    # the hole `checks.py` exists to close -- "a run that measured nothing failed"
    # cannot fire in a process that never reaches its verdict, and a reader of that
    # output reports "content.py is broken" rather than "the suite cannot see the
    # overlay". So the load is guarded, the failure is a NAMED CHECK, and the file
    # falls back to the tracked rows so the remaining checks still run and still
    # report a verdict against the floor.
    try:
        world, world_err = content.load(), None
    except content.ContentError as exc:
        world, world_err = content.load(vault_dir=""), str(exc)
    LEDGER.ok(world_err is None,
              "content.load() -- no arguments, the call the server makes -- accepts "
              "this machine's vault overlay",
              world_err or f"census {world.census()}")

    # --- it loads, and it loaded the tables we expect ------------------------
    LEDGER.ok(world.census().get("map", 0) == 12,
              "twelve maps load (map.27, the terrain tag-3 capture target, "
              "landed 2026-08-18)",
              f"{world.census().get('map')}")
    LEDGER.ok(all(world.census().get(k) for k in
                  ("npc", "item", "spawn", "player", "attack_speed")),
              "every table has at least one row", str(world.census()))
    LEDGER.ok(all(r.provenance.get("source") in content.SOURCES
                  for kind in world.tables for r in world.rows(kind).values()),
              "every row in the shipped store carries a known source")
    unlicensed = [(k, key) for k in world.tables
                  for key, r in world.rows(k).items()
                  if r.provenance["source"] in content.UNLICENSED]
    LEDGER.ok(all(isinstance(world.get(k, key).provenance.get("verified"), str)
                  and world.get(k, key).provenance["verified"].strip()
                  for k, key in unlicensed),
              "every row citing an unlicensed upstream records what we verified",
              f"{len(unlicensed)} such row(s)")

    # --- the migration did not change a value --------------------------------
    # Read off the pre-migration authsrv.py / agents.py, 2026-08-06.
    #
    # MAP 148'S FILE ID IS THE ONE VALUE THAT HAS MOVED SINCE, and it moved on
    # purpose: 0x8001B97D -> 0x1B97D on 2026-08-14. The migration claim this
    # section makes is intact -- moving the data out of authsrv.py changed
    # nothing -- and this is a later, separate, measured correction, so the old
    # literal is kept here as the FROM rather than quietly dropped.
    #
    # Bit 31 is a RENAME, not a spelling: FcArchive binds `id | 0x80000000` and
    # deletes the plain name when it has REQUESTED A REPLACEMENT, and DnArchive
    # re-links the plain id once that lands. So the renamed form is a transient
    # state of ONE archive copy, not the map's identity. Build 38833 installed
    # the replacement: 0x8001B97D does not bind in that archive AT ALL, and
    # 0x1B97D binds to a genuinely different file -- 1,300,044 B crc 0x33F1A289
    # against old row 7982's 1,300,036 B crc 0xA0AE500A. archive.py's
    # file_id_table() had already drawn the rule this now follows: send the plain
    # logical id and serve from an archive that binds it. The full measurement is
    # in content/maps.toml [map.148].
    msc = world.map_static_config()
    LEDGER.ok(msc[148] == (0x1B97D, (9826.0, 8077.0), 0, False),
              "map 148 carries the PLAIN file id, not the renamed bit-31 form",
              f"{msc[148]} -- was 0x8001B97D until 2026-08-14; reverting it makes "
              f"the map unbindable by any post-update client")
    LEDGER.ok(msc[449] == (0x345CC, (-9067.0, 13218.0), 0, False),
              "map 449 (the fallback) is unchanged", str(msc[449]))
    MIGRATED = {148, 146, 449, 194, 55, 474, 558, 90}
    LEDGER.ok(MIGRATED <= set(msc),
              "all eight migrated map ids are still present",
              f"missing {sorted(MIGRATED - set(msc))}")
    # Rows added since the migration are named here rather than absorbed into a
    # count, because "the table grew" and "a row changed meaning" look identical
    # to a length check. 143 is rung C2's experiment row (studies/customarea
    # FINDINGS 18.11): it points at MFT row 71496, which holds DIFFERENT content
    # in the C2 archive copies than in `vault/dat_study/Gw.dat`.
    # 144 is rung E1d's row (FINDINGS 31): the portal test done legally, which
    # needs a props chunk and therefore a row whose reservation holds one. It
    # points at MFT row 26209 in the C2 archive copies only.
    # 280 is the Isle of the Nameless (studies/isle/PLAN.md rung 5, 2026-08-16):
    # file id 0x287B3 = 165811 binds MFT row 21641 in all five vault/run copies;
    # its spawn is OURS (mesh-centre probe, exactly-1 trapezoid on plane 0) and
    # the retail arrival point replaces it after rung 6's capture.
    # 27 is the terrain arc's tag-3 capture target (studies/terrain/FINDINGS.md
    # 7.20's open list, 2026-08-18). Unlike 143 and 144 it writes NOTHING into
    # any archive: file id 0xB5FF is MFT row 34429 in the pristine archive, and
    # the row exists only to make tile block (4,3) -- 590 of 1,024 cells with
    # authored terrain tag 3 -- reachable, every prior capture having landed on
    # a block where tag 3 is zero throughout. The spawn is the block's centre
    # and lands in exactly 1 trapezoid against 0 in both controls.
    ADDED = {143, 144, 280, 27}
    LEDGER.ok(set(msc) == MIGRATED | ADDED,
              "and the only additions are the ones this test names",
              f"unnamed: {sorted(set(msc) - MIGRATED - ADDED)}")
    LEDGER.ok(msc.get(143) == (0x287D3, (1536.0, 1536.0), 0, False),
              "map 143 is C2's target row, spawned at the centre of the "
              "DELIVERED map's rect", str(msc.get(143)))
    # The two experiment rows must name DIFFERENT archive rows. They very nearly
    # did not: 71496 reserves 9,728 B and a two-plane map needs 14,976 with its
    # props chunk, which is the whole reason 144 exists.
    LEDGER.ok(msc.get(144) == (0x5D037, (1536.0, 1536.0), 0, False),
              "map 144 is E1d's target row", str(msc.get(144)))
    LEDGER.ok(msc[143][0] != msc[144][0],
              "and the two experiment rows point at different map files",
              f"0x{msc[143][0]:X} vs 0x{msc[144][0]:X}")

    hatcher = world.get("npc", "hatcher")
    LEDGER.ok((hatcher["file_id"], hatcher["model_id"], hatcher["flags"],
               hatcher["scale"], hatcher["profession"], hatcher["level"]) ==
              (116228, 116703, 0x20C, 0x64000000, 3, 1),
              "the Hatcher's six numeric fields are unchanged")
    LEDGER.ok(hatcher["enc_name"] == [0x328A, 0xE3B9, 0xAA36, 0x2E69],
              "and its EncString words are unchanged -- these cannot be invented")

    # --- REFUSAL 1: a row with no provenance ---------------------------------
    msg = refuses('[thing.a]\nvalue = 1\n', "no provenance")
    LEDGER.ok(msg is not None, "a row with no provenance is REFUSED")
    LEDGER.ok(msg and "provenance.source" in msg,
              "and the error names what is missing", (msg or "")[:60])

    # --- REFUSAL 2: a source outside the vocabulary --------------------------
    msg = refuses('[thing.a]\nvalue = 1\n[thing.a.provenance]\nsource = "vibes"\n',
                  "unknown source")
    LEDGER.ok(msg is not None, "a row with an unknown source is REFUSED")
    LEDGER.ok(msg and "vibes" in msg, "and the error quotes the bad source")

    # --- REFUSAL 3: the licence rule, which is the reason this file exists ----
    msg = refuses('[thing.a]\nvalue = 1\n'
                  '[thing.a.provenance]\nsource = "gw-preservation"\n',
                  "unlicensed, unverified")
    LEDGER.ok(msg is not None,
              "a row citing an all-rights-reserved upstream with no `verified` "
              "is REFUSED")
    LEDGER.ok(msg and "never copy from them" in msg,
              "and the error quotes the rule it is enforcing",
              "PLAN.md section 1.1")

    # ...but the same row WITH a verification loads. A gate that refuses the
    # legitimate case too is not a gate, it is an outage.
    with tempfile.TemporaryDirectory() as tmp:
        write(tmp, "t.toml",
              '[thing.a]\nvalue = 1\n[thing.a.provenance]\n'
              'source = "gw-preservation"\nverified = "resolves to MFT row 7982"\n')
        ok = content.load(repo_dir=tmp, vault_dir="")
    LEDGER.ok(ok.get("thing", "a")["value"] == 1,
              "the same row WITH a verification loads normally")

    # --- REFUSAL 3b: `verified` must be descriptive text, not a bare truthy value --
    # `verified = true` is the authoring slip that most defeats the rule's purpose:
    # it looks like "yes, verified" while recording NOTHING about what was checked,
    # which is the entire thing the field exists to force. A truthiness test passed
    # it -- str(True or "").strip() is "True", non-empty -- so a boolean, or a number,
    # loaded as if it were a real verification. Only non-empty text counts now.
    msg = refuses('[thing.a]\nvalue = 1\n[thing.a.provenance]\n'
                  'source = "gw-preservation"\nverified = true\n',
                  "verified = true")
    LEDGER.ok(msg is not None,
              "an unlicensed row whose `verified` is a bare `true` is REFUSED",
              "a boolean records nothing about what was checked")

    # --- REFUSAL 4: the 2026-08-11 loosening, and the conditions that bound it ---
    # PLAN.md section 7 Q3 permits facts extracted from the client IN BULK. That is the
    # loosening direction, so it is the direction that needs a check: conditions 1 and 2
    # (the extractor is in this repo and named; the row records the build) are enforced by
    # content.py, and this block is what proves they can go red. A permission whose
    # conditions nothing tests is the same wish section 1.1 already caught once.
    EXTRACTED_OK = ('[thing.a]\nlevel = 5\n[thing.a.provenance]\n'
                    'source = "client-table"\nextractor = "toolkit/content.py"\n'
                    'build = "38797"\n')
    msg = refuses(EXTRACTED_OK.replace('extractor = "toolkit/content.py"\n', ""),
                  "extracted, no extractor")
    LEDGER.ok(msg is not None and "extractor" in (msg or ""),
              "an extracted row that does not name its extractor is REFUSED",
              "without the tool the artifact does not regenerate, which is the "
              "entire basis of the permission")

    # The condition is that the tool IS HERE, not that the row says a word. A
    # string-non-empty test passes for a path that was renamed, deleted or never
    # committed -- which is precisely the state the condition exists to catch -- so the
    # path is resolved and required to exist.
    msg = refuses(EXTRACTED_OK.replace("toolkit/content.py",
                                       "toolkit/clientscan/no_such_tool.py"),
                  "extractor does not exist")
    LEDGER.ok(msg is not None and "does not exist" in (msg or ""),
              "and one naming an extractor that is not in this checkout is REFUSED",
              "a named tool that is not here regenerates nothing")

    msg = refuses(EXTRACTED_OK.replace('build = "38797"\n', ""), "extracted, no build")
    LEDGER.ok(msg is not None and "build" in (msg or ""),
              "an extracted row with no `build` is REFUSED",
              "ArenaNet's tables move between builds; a number with no build can be "
              "neither re-derived nor refuted")

    # ...and the legitimate row loads. Same reason as REFUSAL 3's positive case: a gate
    # that refuses the permitted case is not a gate, it is the old ambiguity with extra
    # steps -- and that ambiguity is what this ruling exists to end.
    with tempfile.TemporaryDirectory() as tmp:
        write(tmp, "t.toml", EXTRACTED_OK)
        got = content.load(repo_dir=tmp, vault_dir="")
    LEDGER.ok(got.get("thing", "a")["level"] == 5,
              "a fully-conditioned extracted row loads",
              "extractor present in the repo, build stated, provenance per row")

    # --- REFUSAL 5: the hole the ruling left on its first day -----------------
    # The 2026-08-11 conditions were attached to the TOKEN `client-table`. `measured` is
    # defined as "read or checked against our own artifacts on this machine", which covers
    # reading a table out of the vaulted client -- the identical act -- and it triggered
    # NOTHING. The conditions were opt-in by word choice, which is the same defect the
    # ruling exists to fix, one level down. Found by asking what a row could get away with
    # rather than by re-reading the rule, which is the only way this kind of hole is ever
    # found.
    msg = refuses('[thing.a]\nlevel = 5\n[thing.a.provenance]\nsource = "measured"\n',
                  "measured, no extractor")
    LEDGER.ok(msg is not None and "extractor" in (msg or ""),
              "a `measured` row with no extractor is REFUSED, same as `client-table`",
              "otherwise the ruling's conditions are opt-in by word choice")

    # ...but `build` is required only for `client-table`, and the asymmetry is the point:
    # a table read out of Gw.exe is a fact about THAT BUILD, while a value measured in an
    # archive is a fact about an artifact the row's `verified` text identifies. Forcing a
    # build number onto the second buys a field that is guessed or meaningless.
    with tempfile.TemporaryDirectory() as tmp:
        write(tmp, "t.toml", '[thing.a]\nlevel = 5\n[thing.a.provenance]\n'
                             'source = "measured"\nextractor = "toolkit/content.py"\n')
        meas = content.load(repo_dir=tmp, vault_dir="")
    LEDGER.ok(meas.get("thing", "a")["level"] == 5,
              "and `measured` needs no `build`, while `client-table` still does",
              "a build number on an archive measurement would be guessed or meaningless")

    # --- REFUSAL 6: a capture row must name its session -----------------------
    # A capture value depends on session properties no later reader can recover. Reforged
    # Mode is the one that bites: it scales enemy health ~20%, nothing records it, and it
    # is unrecoverable afterwards -- so a captured health is base or base x 0.8 with
    # nothing able to say which. `mode` is deliberately NOT required yet, because nothing
    # can supply it truthfully and a required field nothing can fill buys invented values.
    msg = refuses('[thing.a]\nhealth = 999\n[thing.a.provenance]\nsource = "capture"\n',
                  "capture, no stamp")
    LEDGER.ok(msg is not None and "capture" in (msg or ""),
              "a `capture` row that does not name its capture is REFUSED",
              "it had NO conditions at all until 2026-08-11 -- the source whose value "
              "depends most on the session was the one asked least about it")

    # --- REFUSAL 6b: a captured combat stat must name the game mode -----------
    # Reforged Mode scales enemy health and armour ~20%, leaves no mark on the recorded
    # stream, and cannot be recovered afterwards -- so an unstamped stat is base or
    # base x 0.8 forever, at a size that reads as a plausible base value rather than an
    # obvious error. `livesession.py --mode` has been required since 2026-08-11, so a
    # capture taken from now on can answer this.
    CAP = 'source = "capture"\ncapture = "20260807T143055"\norigin = "live"\n'
    msg = refuses('[thing.a]\nmax_health = 8\n[thing.a.provenance]\n' + CAP,
                  "capture health, no mode")
    LEDGER.ok(msg is not None and "mode" in (msg or ""),
              "a capture row carrying health with no `mode` is REFUSED",
              "an unstamped health number can never be graded")

    msg = refuses('[thing.a]\nmax_health = 8\n[thing.a.provenance]\n' + CAP +
                  'mode = "yes"\n', "capture health, junk mode")
    LEDGER.ok(msg is not None,
              "and a `mode` outside base|reforged|unrecorded is REFUSED",
              "a free string would let 'Base' or 'reforge' stamp a capture with a value "
              "nothing downstream knows how to read")

    # "unrecorded" LOADS, and that is the point rather than a leak. Every capture taken
    # before the flag existed genuinely cannot answer, and origin.py's three-valued
    # ours/live/unknown is the precedent: `unknown` exists so a file is never forced into
    # a claim it cannot support. What is refused is SILENCE, not ignorance -- and the
    # three health readings in the vault are exactly this case.
    with tempfile.TemporaryDirectory() as tmp:
        write(tmp, "t.toml", '[thing.a]\nmax_health = 8\n[thing.a.provenance]\n' + CAP +
                             'mode = "unrecorded"\n')
        unrec = content.load(repo_dir=tmp, vault_dir="")
    LEDGER.ok(unrec.get("thing", "a")["max_health"] == 8,
              "but `mode = \"unrecorded\"` LOADS -- silence is refused, ignorance is not",
              "the pre-2026-08-11 captures cannot answer and must not be forced to")

    # CONTROL: the gate is on the mode-SENSITIVE fields, not on capture rows generally.
    # Without this, requiring `mode` everywhere would look identical from the checks above
    # while making every non-combat capture row carry a meaningless field -- and the
    # shipped `lakeside_worm` row, whose `speed` Reforged does not touch, would have to
    # claim a mode it has no reason to know.
    with tempfile.TemporaryDirectory() as tmp:
        write(tmp, "t.toml", '[thing.a]\nspeed = 12.0\n[thing.a.provenance]\n' + CAP)
        nonstat = content.load(repo_dir=tmp, vault_dir="")
    LEDGER.ok(nonstat.get("thing", "a")["speed"] == 12.0,
              "CONTROL: a capture row with no mode-sensitive field needs no `mode`",
              f"the gated fields are {', '.join(content.MODE_SENSITIVE)}")

    # --- REFUSAL 7: a wiki row must say where ---------------------------------
    # This is the cheapest possible fake green: 35 rows of plausible numbers with
    # `source = "wiki"`, each a guess wearing a citation. It loaded clean until now.
    msg = refuses('[thing.a]\nhealth = 999\n[thing.a.provenance]\nsource = "wiki"\n',
                  "wiki, no page")
    LEDGER.ok(msg is not None and "page" in (msg or ""),
              "a `wiki` row with no page is REFUSED",
              "a fabricated health = 999 loaded clean before this check existed")

    # --- an empty store is refused, not defaulted ----------------------------
    with tempfile.TemporaryDirectory() as tmp:
        try:
            content.load(repo_dir=tmp, vault_dir="")
            empty_refused = False
        except content.ContentError:
            empty_refused = True
    LEDGER.ok(empty_refused,
              "an empty store is REFUSED rather than falling back to something "
              "invented")

    # --- the vault overlay -----------------------------------------------------
    with tempfile.TemporaryDirectory() as repo, tempfile.TemporaryDirectory() as vault:
        # Every fixture row here carries the conditions its source now requires. The
        # overlay is bulk `vault/content/` merged over the tracked rows, which is exactly
        # where a capture-derived table would land, so these rows are written the way a
        # real one would have to be rather than with the minimum that used to load.
        cap = ('source = "capture"\ncapture = "20260807T143055"\norigin = "live"\n')
        write(repo, "a.toml",
              '[thing.a]\nvalue = 1\n' + GOOD_PROV +
              '[thing.b]\nvalue = 2\n[thing.b.provenance]\nsource = "measured"\n'
              'extractor = "toolkit/content.py"\n')
        write(vault, "a.toml",
              '[thing.b]\nvalue = 22\n[thing.b.provenance]\n' + cap +
              '[thing.c]\nvalue = 3\n[thing.c.provenance]\n' + cap)
        merged = content.load(repo_dir=repo, vault_dir=vault)
    # Read through `rows()` rather than `get()`: `get()` RAISES on a missing key, so a
    # loader that dropped the overlay entirely killed this section with a traceback at
    # the third check instead of reddening it -- no verdict, no ledger, and the two
    # checks after it never ran. Same defect as the bare `content.load()` this file
    # opened with, one level down, and found by the sabotage that removes the vault
    # from `load()`'s directory list.
    merged_thing = merged.rows("thing")
    LEDGER.ok(merged_thing.get("a", {}) and merged_thing["a"]["value"] == 1,
              "a repo row the vault does not mention survives the overlay")
    LEDGER.ok(merged_thing.get("b", {}) and merged_thing["b"]["value"] == 22,
              "a vault row overrides the repo row of the same key")
    LEDGER.ok(merged_thing.get("c", {}) and merged_thing["c"]["value"] == 3,
              "and the vault may add rows the repo does not have",
              f"loaded keys: {sorted(merged_thing)}")

    # --- the REAL vault overlay, which nothing here loaded until 2026-08-13 ----
    # Every load above passes `vault_dir=""` or a temp dir, so the three checks above
    # pin the MERGE SEMANTICS and say nothing about the bytes on this machine. On
    # 2026-08-13 `vault/content/effects.toml` shipped 2,077 rows citing
    # `toolkit/clientscan/consttable.py`, which existed only in the worktree that wrote
    # them and had not been committed. `_check_extracted` refused all 2,077 -- correctly,
    # that is condition 1 doing its job -- so `content.load()` raised for the server,
    # for `deploy.py` and for every session that called it. This file printed ALL CHECKS
    # PASSED throughout, because not one of its 36 checks had ever touched the vault.
    # The gate worked; the suite could not see it. The store's own overlay was the one
    # input it never read.
    #
    # These four are vault-dependent and declare a skip on a bare machine, so the floor
    # stays the vault-less score. Checks 3 and 4 are what stop check 1 from being
    # vacuous: `load()` SKIPS a vault directory that is not there (`content.py` line 358),
    # so "it loaded" is equally what a machine with no overlay prints -- and renaming the
    # overlay aside is exactly the workaround that was reached for the morning this gap
    # was found, which would otherwise leave this section green over an empty vault.
    try:
        real_vault = content.vaultpath.vault_path("content")
    except Exception:
        real_vault = None
    if not (real_vault and os.path.isdir(real_vault)):
        LEDGER.skip("the real vault overlay (3 checks)",
                    "no vault/content/ on this machine; the overlay is gitignored and "
                    "machine-local, so there is nothing here to accept or refuse")
    else:
        # 1. Non-vacuity for the guarded load at the top of main(). `load()` SKIPS a
        #    vault directory that is not there (`content.py` line 358), so "it loaded"
        #    is equally what an absent overlay prints -- and renaming the overlay aside
        #    is the workaround that was reached for the morning this gap was found, so
        #    this is not a hypothetical way for that check to pass while measuring
        #    nothing.
        #
        #    What this CANNOT decide, stated rather than implied by the label: it is a
        #    total over every file, so it catches an overlay that is absent or wholly
        #    sidelined and NOT one file of several renamed aside. Catching that needs
        #    a per-file expectation, and there is nothing tracked to check one against
        #    -- the overlay is gitignored and its file list is a property of the
        #    machine. The mutation controls below are what cover the rows that ARE
        #    present.
        repo_only = content.load(vault_dir="")
        n_repo = sum(repo_only.census().values())
        n_live = sum(world.census().values())
        LEDGER.ok(world_err is None and n_live > n_repo,
                  "the overlay CONTRIBUTED rows rather than being absent or wholly "
                  "sidelined",
                  f"{n_repo} rows from content/ alone, {n_live} with the vault merged "
                  f"over it")

        # 2/3. The gate must RUN over these rows, not merely tolerate them. Copy the
        #      overlay, break ONE row's extractor the way 2026-08-13 broke 2,077 of
        #      them, and require the refusal -- with the unmutated copy as the control,
        #      so the refusal is attributable to the mutation and not to the copying.
        with tempfile.TemporaryDirectory() as tmp:
            copy = os.path.join(tmp, "content")
            shutil.copytree(real_vault, copy)
            # The target must be a row whose SOURCE actually reaches `_check_extracted`,
            # and grepping for `extractor = "` does not find one. An extractor on a row
            # outside `content.EXTRACTED` is inert -- `capture` rows carry the field and
            # nothing validates it -- so mutating one changes nothing, no refusal comes
            # back, and the check reddens naming the gate when the gate is fine. That is
            # not hypothetical: it is what this check did the moment a parallel session
            # removed `effects.toml` and left `npcs.toml`, whose rows are all `capture`.
            # So the row is chosen by PARSING for a source in EXTRACTED, and the file's
            # own extractor VALUE is what gets replaced -- which works whether the row
            # writes provenance inline or as a `[x.provenance]` block, and cannot pick a
            # row that has no condition-1 claim to break.
            target = None
            for name in sorted(os.listdir(copy)):
                if not name.endswith(".toml"):
                    continue
                path = os.path.join(copy, name)
                with open(path, "rb") as fh:
                    try:
                        doc = content.tomllib.load(fh)
                    except Exception:
                        continue
                for rows in doc.values():
                    if not isinstance(rows, dict):
                        continue
                    for row in rows.values():
                        if not isinstance(row, dict):
                            continue
                        prov = row.get("provenance")
                        if not isinstance(prov, dict):
                            continue
                        cited = prov.get("extractor")
                        if (prov.get("source") in content.EXTRACTED
                                and isinstance(cited, str) and cited.strip()):
                            target = (path, cited)
                            break
                    if target:
                        break
                if target:
                    break
            if target is None:
                LEDGER.skip("the extractor mutation (2 checks)",
                            "no row in this vault carries a source in EXTRACTED with an "
                            "`extractor`, so there is no condition-1 claim here to break")
            else:
                path, cited = target
                with open(path, encoding="utf-8") as fh:
                    text = fh.read()
                try:
                    content.load(vault_dir=copy)
                    copy_err = None
                except content.ContentError as exc:
                    copy_err = str(exc)
                LEDGER.ok(copy_err is None,
                          "CONTROL: an unmutated copy of the overlay loads",
                          copy_err or f"copied {os.path.basename(path)} and its siblings")

                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(text.replace(cited, "toolkit/clientscan/NOT_COMMITTED.py"))
                try:
                    content.load(vault_dir=copy)
                    broke = None
                except content.ContentError as exc:
                    broke = str(exc)
                LEDGER.ok(broke is not None and "NOT_COMMITTED" in (broke or ""),
                          "ONE real overlay row repointed at an uncommitted extractor is "
                          "REFUSED -- the 2026-08-13 defect, reproduced",
                          broke or "the loader accepted a row whose named tool is not in "
                                   "this checkout, which is condition 1 not running")

    # --- an unknown key is an error, not a None ------------------------------
    try:
        world.get("map", 99999)
        raised = False
    except content.ContentError:
        raised = True
    LEDGER.ok(raised, "asking for a row that does not exist raises rather than "
                      "returning None for something downstream to misread")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
