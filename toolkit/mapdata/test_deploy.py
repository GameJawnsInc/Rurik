r"""Check rung G's one command: `deploy.py`, the whole ladder from `content/`.

WHAT THIS FILE IS FOR. `deploy.py` is an ORCHESTRATOR -- almost every line it
runs belongs to a module that has its own test. So this does not re-check the
terrain codec or the archive writer; it checks the things that are only true of
the composition, and those are exactly the things the first three runs of the
command got wrong:

  * **The two kinds of borrowing are different.** Structural constants (Header,
    Zones) must come from a map SHAPED LIKE OURS; the biome (textures, sun, env,
    sound) comes from wherever you like. The first run took both from
    Pre-Searing, whose Zones chunk is 7,208 bytes against the 32x32 reference
    map's 34, and built an 11,115-byte map for a 4,608-byte reservation. Section
    2 pins the split by building with both and requiring the borrowed census to
    stay small.
  * **The client you launch must own the archive you armed.** Every run
    directory has its own `Gw.dat`. The first run armed the C2 copy and launched
    the DEFAULT client, which read unarmed bytes and compiled nothing -- the
    same defect as FINDINGS 54's, from the other side. Section 3 asserts on the
    SYNTAX TREE that the exe is derived from `--dat`, because "it happens to be
    right today" is not a check.
  * **A generator must produce a field the codec can actually hold.** Section 1
    runs every named generator through the lattice snap and requires the
    terrain round trip to close exactly, which is what catches a shape whose
    heights are off the reachable sublattice.
  * **The row holds compressed bytes, and the FIT is judged on those.** Since
    2026-08-20 the Stripped partner is installed as a compression-8 stream,
    which is the shape retail's own partners have and is what lifts the 32x32
    cap. Section 7 runs real installs against a hand-laid archive whose
    reservation this file chooses, so "compressed fits where stored did not" is
    a fact about the rule rather than an accident of one retail map.
  * **A map can be CREATED rather than displaced, and the ways that goes wrong
    are silent.** Since 2026-08-20 an area whose map row carries
    `created = true` gets two MFT rows of its own under a new file id instead of
    overwriting a live retail map. Section 8 runs real allocations against the
    same hand-laid archive and reads the raw bytes back, because every failure
    mode here passes the archive's own rules: an id registered on the partner
    instead of the head is deleted by the client's reconcile at the next launch
    with every crc still correct, and an id whose bit-31 sibling exists leaves
    two live registrations nothing we own counts.

  * **A row can be grown BACK into blocks it freed, but only up to a number
    somebody stated, and only in a row we made.** A compressed install shrinks
    a row's reservation and the archive records no entitlement anywhere, so
    until 2026-08-20 the next larger authored map relocated -- always, even into
    a row we created ourselves. Section 9 drives an area's declared
    `reserve_bytes` through all three outcomes on one archive, holds the budget
    against a row we did NOT create and watches it go unspent, and makes the
    grow gate refuse on purpose -- because a fallback that swallowed a claimant
    conflict would look exactly like a success, and so would one that reported a
    gate refusal the gate never gave.

  * **"Created" is a claim content makes; the archive has to agree.** Section 10
    is the residual pass. `map_chain` checks a chain's SHAPE, and 349 retail
    maps have that shape -- so a `created = true` row whose id happens to bind
    one of them displaced it silently, while every line of output said the word
    "created". It now takes the allocation journal as evidence, and the section
    drives both answers on one archive. Beside it: the born-armed guard, which
    was live code nothing exercised; the journal-clobber refusal `datalloc`'s
    CLI has always had and this path went around; the three of `map_chain`'s
    five refusals that had no fixture at all; and the grow-gate join, which used
    to be four fragments of another module's prose.

  * **A chunk we deliberately did NOT author has to be asserted absent.**
    `readback`'s loop over the optional payload chunks used to skip its
    assertion when the staged map omitted one, so WORLDMAPS-W8 installed a map
    with `environment = false`, read a clean 6/6, and had been told nothing
    about the environment -- while the fact the arm turned on, that the client's
    COMPILED map carries none either and so had no fallback, was recovered by
    hand afterwards. Section 11 drives the loop present, absent, and sabotaged,
    because absent-and-unasserted looked exactly like absent-and-confirmed.

NO VAULT, NO ARCHIVE, NO CLIENT for sections 0-1, 3-11. Section 2 needs the
archive because the borrowed halves are read from it at run time -- that is the
provenance rule, not a convenience -- and the floor turns a vault-less run into
the FAIL it is.

    python toolkit/mapdata/test_deploy.py
"""

import ast
import binascii
import contextlib
import io
import json
import os
import shutil
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import Archive  # noqa: E402
import archive as archive_mod  # noqa: E402  -- raw vs convenience id table
import content as content_mod  # noqa: E402
import datalloc  # noqa: E402  -- section 8 drives its shape gate by hand
import datwrite  # noqa: E402  -- section 10e joins on ITS token, not our copy
import deploy  # noqa: E402
import gwdat  # noqa: E402
import gwenc  # noqa: E402
import mapfile as mfile  # noqa: E402
import pathchunk  # noqa: E402  -- section 11 assembles a compiled map's mesh
import pathmap  # noqa: E402
from props import StrippedProps  # noqa: E402
import stripbuild as sb  # noqa: E402
import strippedterrain as stx  # noqa: E402
import checks  # noqa: E402
import vaultpath  # noqa: E402

# MEASURED 2026-08-13 on the plaza area. The census is the load-bearing number:
# Header 8 + Zones 34 + env 639 + sound 89 = 770, and nothing else.
REFERENCE_ROW = 46196          # the 32x32 map whose Zones is 34 B
BIOME_ROW = 7982               # Pre-Searing
BORROWED_MAX = 900             # generous ceiling; the real figure is 770
PRESEARING_ZONES = 7208        # what the first run wrongly pulled in

# FLOOR: 213, MEASURED from a green run 2026-08-21 (sections 0,1,3..11 score 209
# and need no vault -- measured with RURIK_VAULT pointed at an empty directory;
# section 2 reads the archive for the borrowed halves, which is the provenance
# rule rather than a convenience, and the floor sitting ABOVE 209 is what turns
# a vault-less run into the FAIL it is). Per section, counted from the log
# rather than predicted: {0: 3, 1: 2, 2: 4, 3: 8, 4: 8, 5: 6, 6: 10, 6b: 20,
# 7: 15, 8: 36, 9: 55, 10: 36, 11: 10}.
#
# COUNT THE LOG WITH THE SUBPROCESS WRITERS' OWN LINES EXCLUDED. They print in
# the same `[PASS] ...` shape as the ledger and a naive `grep -c "\[PASS\]"`
# reads 220, which is 17 more than the ledger says. There are THREE producers,
# not two, and the arithmetic is worth writing down because the first version of
# this comment got it wrong: `datwrite --verify` prints a `file header crc` line
# AND an `MFT self-crc` line per run (6 runs, 12 lines), and `datmove` prints
# one `0 overlapping row pair(s) afterwards` per move (5 moves, 5 lines).
# 230 - 17 = 213. Anchoring the grep at `^  \[PASS\]` drops datmove's five --
# they carry no indent -- and reads 225, which is 213 + datwrite's 12. Sections
# 9 and 10 are what move these counts, so re-measure both numbers rather than
# adjusting them. (Section 11 is the one place a check's DETAIL quotes another
# producer's `[PASS]` row -- `readback`'s. `verdict_of` strips the quoted row's
# marker so that stays one marker per line: MEASURED 2026-08-21, `grep -o` and
# `grep -c` both read 230, so the occurrence count and the line count agree and
# either grep gives the same answer.)
#
# Was 229 before WORLDMAPS-W17 added the 'ramp' generator, which section 1
# picks up automatically -- it iterates GENERATORS, so a new field costs no
# test-writing and cannot be added without its lattice round-trip being
# checked. 218 before section 13 (WORLDMAPS-W13 recon: `serve_run` could reach a
# verdict from another SESSION's log, about another MAP, after a harness that
# FAILED -- three holes that composed, all three live on 2026-08-21 with three
# worktrees driving one harness), 213 before section 12 (WORLDMAPS-W12: an armed head that was never
# re-bloated, which used to leave `readback` raising out of the FFNA decoder
# about a 0-byte file, plus the control that a re-bloated head still reads
# back clean), 203 before section 11 (WORLDMAPS-W8: `readback`'s optional-chunk loop,
# asserted in the ABSENT direction it used to `continue` past), 195 before the
# R2 fix pass (section 10b: the copied archive, the byte route and its negative,
# the path route's own fixture, and one fixture each for the three journal
# conjuncts that a mutation sweep could delete unnoticed), 167
# before the residual pass (section 10: the born-armed guard, the created-chain
# evidence, the journal-clobber refusal, map_chain's three unexercised refusals,
# and the typed grow-gate join), 150 before the WORLDMAPS-W5 fix pass (the
# `created` half of the budget gate, the negatives in 9(e), and `area_reserve`),
# 112 before section 9's reserve (WORLDMAPS-W5), 92 before section 6b's
# serve-verdict checks, 84 before section 8's dry-run and spill checks, 56
# before section 8 and the create branch, 35 before section 7 and the
# compression checks, 25 before section 6.
LEDGER = checks.Ledger("test_deploy", floor=230)
check = checks.adopt(LEDGER)


def section0():
    print("\n0. the area row loads, and says what it borrows")
    # REPO ONLY, deliberately. `content.load()` merges the VAULT overlay, which
    # is shared between sessions -- so a half-written row over there turns this
    # test red for reasons that have nothing to do with deploy. It happened:
    # another arc's effects.toml cited an extractor it had not committed, and
    # every caller of load() raised, this file included. Area rows live in the
    # repo; the overlay's rules are `test_content.py`'s job.
    world = content_mod.load(vault_dir="")
    area = world.get("area", "plaza")
    check(int(area["map_id"]) in {int(k) for k in world.rows("map")},
          "the area's map_id names a real maps.toml row", f"{area['map_id']}")
    check(area.provenance["source"] == "invented",
          "an authored area is provenance 'invented' -- ours, chosen rather "
          "than observed", f"{area.provenance['source']}")
    check(int(area["constants_row"]) != int(area["donor_row"]),
          "the structural donor and the biome donor are SEPARATE fields",
          f"constants {area['constants_row']}, biome {area['donor_row']}")
    return area


def section1(area):
    print("\n1. every generator lands on the codec's lattice")
    dim = int(area["dims"])
    for name, gen in sorted(deploy.GENERATORS.items()):
        raw = gen(dim)
        snapped, worst = stx.snap_block(raw)
        trn = stx.StrippedTerrain.build(dim, dim, snapped)
        back = stx.StrippedTerrain.decode(trn.encode())
        same = sum(1 for a, b in zip(back.heights, snapped) if a == b)
        check(same == len(snapped),
              f"generator {name!r} round-trips exactly after the snap",
              f"{same}/{len(snapped)}, worst moved {worst}")


def exe_derived_from_dat(source):
    """True iff main() assigns `exe` from dirname(dat).

    Deliberately narrow, and the narrowness is the whole point. The first
    version of this asked whether main() contained ANY `join(dirname(dat), ...)`
    -- and it does, twice, because the output path defaults that way too. So it
    returned True against a sabotaged source that defaulted the exe, i.e. it was
    a check that could not fail. Section 3 now runs that exact sabotage and
    requires this to answer False.
    """
    fn = next(n for n in ast.walk(ast.parse(source))
              if isinstance(n, ast.FunctionDef) and n.name == "main")
    for node in ast.walk(fn):
        targets = ([t.id for t in node.targets if isinstance(t, ast.Name)]
                   if isinstance(node, ast.Assign) else [])
        if "exe" not in targets:
            continue
        for n in ast.walk(node.value):
            if (isinstance(n, ast.Call)
                    and getattr(n.func, "attr", "") == "dirname"
                    and any(isinstance(x, ast.Name) and x.id == "dat"
                            for x in n.args)):
                return True
    return False


def sets_rurik_dat(source, where="launch"):
    """True iff `where` assigns env["RURIK_DAT"] from `dat` AND hands env over.

    Takes the SOURCE rather than reading the module, so section 3 can run it
    against a sabotage and show the answer flips -- the same shape as
    `exe_derived_from_dat`, and for the same reason: a structural check that has
    only ever seen the passing case is a check nobody has watched fail.

    It asks `launch()` rather than `main()` because the harness is now started
    from exactly one place and both runs go through it. That is a stronger
    claim, not a weaker one: with two call sites a fix could reach one and miss
    the other, which is how the serve run would have gone out unpointed.
    """
    fn = next(n for n in ast.walk(ast.parse(source))
              if isinstance(n, ast.FunctionDef) and n.name == where)
    assigned = False
    for node in ast.walk(fn):
        if not (isinstance(node, ast.Assign) and len(node.targets) == 1):
            continue
        t = node.targets[0]
        if not (isinstance(t, ast.Subscript)
                and isinstance(t.value, ast.Name) and t.value.id == "env"
                and isinstance(t.slice, ast.Constant)
                and t.slice.value == "RURIK_DAT"):
            continue
        assigned = any(isinstance(n, ast.Name) and n.id == "dat"
                       for n in ast.walk(node.value))
    handed = any(isinstance(n, ast.keyword) and n.arg == "env"
                 and isinstance(n.value, ast.Name) and n.value.id == "env"
                 for n in ast.walk(fn))
    return assigned and handed


def section3():
    print("\n3. the client is DERIVED from the archive, not defaulted")
    source = open(deploy.__file__, encoding="utf-8").read()
    tree = ast.parse(source)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "main")
    src = ast.dump(fn)
    check(exe_derived_from_dat(source),
          "main() assigns the client path from dirname(dat) -- the client that "
          "reads the archive we armed is the only one that can load it")
    # NEGATIVE CONTROL: default the exe and require the check to notice.
    sabotage = source.replace(
        'exe = args.exe or os.path.join(os.path.dirname(dat), "Gw.exe")',
        'exe = args.exe or DEFAULT_EXE')
    check(sabotage != source and not exe_derived_from_dat(sabotage),
          "and an exe that is DEFAULTED instead makes that check go red -- "
          "without this control the check passed on the output path's own "
          "dirname(dat) and could not fail")
    check('"--exe"' in ast.dump(fn) or "'--exe'" in src,
          "and passes --exe to the harness rather than letting it default")
    check("--map" in open(deploy.__file__, encoding="utf-8").read(),
          "and points the harness at the area's own map id -- a harness PASS "
          "means the client reached A map, not ours")
    # the readback must exist and must be called
    called = any(isinstance(n, ast.Call) and getattr(n.func, "id", "") == "readback"
                 for n in ast.walk(fn))
    check(called, "main() actually calls readback() -- a documented stage that "
                  "no line runs is a docstring, not a check")

    # THE SERVER'S WORLD. After an install the archive we wrote and the server's
    # default (vault/dat_study) disagree about the area's map id, and
    # contentids.preflight refuses the launch -- correctly, since the server
    # would path against ArenaNet's geometry while the client drew ours. The fix
    # is to point the server at the same archive, which `--dat` already names.
    check(sets_rurik_dat(source),
          "launch() sets RURIK_DAT from `dat` and hands the env to the harness "
          "-- server and client read ONE world, so the archive-mismatch guard "
          "passes because the situation is right, not because it was bypassed")
    # NEGATIVE CONTROLS, one per half of that claim.
    hardcoded = source.replace('env["RURIK_DAT"] = os.path.abspath(dat)',
                               'env["RURIK_DAT"] = DEFAULT_DAT')
    check(hardcoded != source and not sets_rurik_dat(hardcoded),
          "and pointing the server somewhere OTHER than `dat` makes it go red")
    dropped = source.replace("text=True, env=env", "text=True")
    check(dropped != source and not sets_rurik_dat(dropped),
          "and building the env without handing it over makes it go red -- "
          "which is precisely the shape of a fix that does nothing")


def section6():
    """The navmesh join: WHEN the server reads the ground.

    The defect this pins was silent in both of its forms and shipped for two
    days. `load_pathmap`'s only call site was instance bring-up -- after the
    client connects -- so:

      * with the server on its default archive it read ARENANET's geometry for
        the same map id. Over a 4,096-point grid on the sculpt map the two
        walkable sets are DISJOINT (49 ours, 435 theirs, 0 shared), and the
        authored spawn is off ArenaNet's mesh entirely, so the server suspended
        collision on arrival. 16 vault runs carry that line.
      * with the server pointed at OUR archive (the RURIK_DAT fix) the client
        already held it open exclusively, so the read returned EACCES and
        collision turned off. Two vault runs carry that one.

    Neither failed a test, neither failed the harness, and the FINDINGS document
    asserted the opposite as measured. What follows is structural because the
    behaviour needs a client; the one thing a client would add -- that the
    server's own log names our trapezoid count -- is what `serve_run` reads, and
    its parsing is checked here against a log this test writes.
    """
    print("\n6. the navmesh is read BEFORE a client can lock the archive")
    # By PATH, not by import. `authsrv` builds the whole world at import time,
    # which needs the content store to load -- a shared vault overlay another
    # session is mid-edit in would turn this section red for a reason that has
    # nothing to do with what it checks.
    path = os.path.join(os.path.dirname(HERE), "authsrv", "authsrv.py")
    check(os.path.isfile(path), f"authsrv.py is where this expects it", path)
    src = open(path, encoding="utf-8").read()
    tree = ast.parse(src)

    # (a) the pre-warm exists and main() calls it.
    names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    check("prewarm_pathmap" in names,
          "authsrv defines prewarm_pathmap() -- the startup read")
    main_fn = next(n for n in ast.walk(tree)
                   if isinstance(n, ast.FunctionDef) and n.name == "main")
    called = any(isinstance(n, ast.Call)
                 and getattr(n.func, "id", "") == "prewarm_pathmap"
                 for n in ast.walk(main_fn))
    check(called, "and main() CALLS it -- a startup read that startup does not "
                  "run is the defect wearing a fix's name")
    # NEGATIVE CONTROL: delete the call, keep the function.
    gutted = src.replace("        prewarm_pathmap(a.map if known else "
                         "FALLBACK_MAP_ID)\n", "")
    gutted_ok = gutted != src and not any(
        isinstance(n, ast.Call) and getattr(n.func, "id", "") == "prewarm_pathmap"
        for n in ast.walk(next(f for f in ast.walk(ast.parse(gutted))
                               if isinstance(f, ast.FunctionDef)
                               and f.name == "main")))
    check(gutted_ok,
          "and removing that one line makes the check go red while "
          "prewarm_pathmap still EXISTS and still reads correctly -- which is "
          "exactly how a documented stage becomes a docstring")

    # (b) the EACCES arm is named, because "Permission denied" on a file this
    # process owns reads as a broken install and sent one session hunting.
    check(any(isinstance(n, ast.ExceptHandler)
              and getattr(n.type, "id", "") == "PermissionError"
              for n in ast.walk(tree)),
          "load_pathmap names PermissionError separately -- the cause is a "
          "client holding the archive, which the bare message does not say")

    # (c) serve_run's verdict is the SERVER's own number against the ARCHIVE's,
    # never a constant. Two independent readers of the same bytes.
    dep = open(deploy.__file__, encoding="utf-8").read()
    fn = next(n for n in ast.walk(ast.parse(dep))
              if isinstance(n, ast.FunctionDef) and n.name == "serve_run")
    check(any(isinstance(n, ast.Name) and n.id == "expect_traps"
              for n in ast.walk(fn)),
          "serve_run compares against a count read from the archive, not a "
          "literal -- a predicted number would be a check that cannot fail")

    # (d) --hold only holds under --keep-open. `session.hold_open` is gated on
    # it, and deploy passed --hold alone -- so the flag named a wait that never
    # happened and both runs of the serve pair finished 17 s apart under
    # `--hold 40`. Asked of the syntax tree because "both flags are in the same
    # argument list" is what matters, and a grep for "--keep-open" would pass on
    # this comment.
    launch_fn = next(n for n in ast.walk(ast.parse(dep))
                     if isinstance(n, ast.FunctionDef) and n.name == "launch")
    flags = {n.value for n in ast.walk(launch_fn)
             if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    check("--hold" in flags and "--keep-open" in flags,
          "launch() passes --keep-open beside --hold -- without it "
          "session.hold_open never runs and --hold is decoration",
          f"keep-open={'--keep-open' in flags}")

    # (e) the log parsing, behaviourally, against a log this test writes.
    LINE = "[map] navmesh 0x287D3: 1 planes, 13 trapezoids"
    hits = deploy.NAVMESH_RE.findall(f"noise\n{LINE}\nmore noise\n")
    check(hits == [("287D3", "1", "13")],
          f"the navmesh line parses to (id, planes, trapezoids)", f"{hits}")
    check(deploy.NAVMESH_RE.findall("[map] no navmesh for 0x287D3: nope") == [],
          "and a FAILED load does not parse as a successful one -- the two "
          "lines share a prefix and a wrong regex reads the failure as a hit")
    check(deploy.NAVMESH_RE.findall(
        "[map] navmesh 0x287D3: 1 planes, 27 trapezoids") == [
            ("287D3", "1", "27")],
        "and ArenaNet's own 27-trapezoid map 143 parses too, so the check is "
        "the COMPARISON and not the pattern -- 27 is what the server actually "
        "logged on 43 runs while the client drew ours")

    section6_population()


# The two lines `spawn_population` can legitimately end on, verbatim as the
# server prints them. OURS, not ArenaNet's -- `authsrv.py` is in this repo and
# section6_population reconstructs both from its syntax tree rather than
# trusting these copies.
PLACED_LINE = "[c1] area 'sculpt': 3 of 3 placed"
EMPTY_LINE = ("[c1] area 'plaza': no population rows; the world is the player "
              "and the geometry")
MESH_LINE = "[map] navmesh 0x287D3: 1 planes, 55 trapezoids"


def render_fstring(node):
    """An f-string's text with its placeholders filled by sample values.

    So a check can ask whether a regex matches what a module ACTUALLY PRINTS
    rather than whether it matches a copy of that line pasted into a test. The
    copy is the thing that rots: `UNPOPULATED_RE` hard-codes eleven words of
    another module's prose, and if somebody rewords the message the pattern
    stops matching a line that still means the same thing -- which is precisely
    the failure this whole section is repairing, one layer up.
    """
    out = []
    for v in node.values:
        if isinstance(v, ast.Constant):
            out.append(v.value)
        elif isinstance(v, ast.FormattedValue):
            name = getattr(v.value, "id", "")
            sample = {"conn_id": "1", "area": "plaza",
                      "placed": "3", "total": "3"}.get(name, "?")
            out.append(repr(sample) if v.conversion == ord("r") else sample)
    return "".join(out)


def find_print_fstring(fn, needle):
    """The rendered f-string of the `print` inside `fn` whose text holds `needle`."""
    for node in ast.walk(fn):
        if not (isinstance(node, ast.Call)
                and getattr(node.func, "id", "") == "print"):
            continue
        for arg in node.args:
            if isinstance(arg, ast.JoinedStr):
                text = render_fstring(arg)
                if needle in text:
                    return text
    return None


class FakeServe:
    """`serve_run` with the client taken out: a canned gamesrv log, nothing launched.

    `serve_run`'s decision is the part that was wrong, and it is pure -- read a
    log, choose a verdict. Everything around it (launching two clients, holding
    a map open for 45 s) is what makes it untestable, so this replaces exactly
    that and leaves the decision alone. `launch` returns rc 0 and
    `newest_harness_log` returns the file we just wrote.
    """

    def __init__(self, text, rc=0):
        self.text = text
        self.rc = rc

    def __enter__(self):
        self.dir = tempfile.mkdtemp()
        self.log = os.path.join(self.dir, "gamesrv.log")
        with open(self.log, "w", encoding="utf-8") as fh:
            fh.write(self.text)
        self.saved = (deploy.launch, deploy.newest_harness_log)
        deploy.launch = lambda *a, **k: self.rc
        # `source=` is accepted and IGNORED here on purpose: this fixture is
        # about the decision, and section 13 tests the attribution separately
        # against real files rather than against a stub that cannot get it
        # wrong.
        deploy.newest_harness_log = lambda after, source=None: self.log
        return self

    def __exit__(self, *exc):
        deploy.launch, deploy.newest_harness_log = self.saved
        return False


def serve_verdict(text, area=None, expect_traps=55, expect_rows=None,
                  file_id=0x287D3, rc=0, note=False):
    """The verdict `serve_run` reaches on a canned log (or (verdict, note))."""
    with FakeServe(text, rc=rc) as f:
        got = deploy.serve_run("exe", "session", "dat", 143, 0, expect_traps,
                               file_id, area=area, expect_rows=expect_rows)
    return got if note else got[0]


def section6_population():
    """An EMPTY area is a state, not a failure -- and the mesh still rules.

    WHAT WENT WRONG. `PLACED_RE` matched one of `spawn_population`'s two
    legitimate exits. The other one -- `area 'plaza': no population rows; the
    world is the player and the geometry` -- fell through to the arm written for
    a server that CRASHED mid-placement, so an area with nobody in it scored
    "the server never got as far as placing bodies" and deploy exited 1.

    Both arms of WORLDMAPS-W2 hit it on 2026-08-20. Each had served the mesh
    correctly -- 55 trapezoids, the server's own count against the archive's --
    and each was reported as a serve FAILURE. The run's finding survived only
    because a human read the gamesrv log and overrode the transcript
    (`vault/research/worldmaps/WORLDMAPS-W2-RUN.md`, RESULTS P6).

    The repair has to hold three things apart, and the third is the one worth
    testing: an empty area may downgrade a PASS to SERVED-UNPOPULATED, and it
    may NEVER lift a FAILED. A mesh that disagrees with the archive is the whole
    reason this run exists.
    """
    print("\n6b. an empty area is its own verdict, and the mesh still rules")
    src = open(os.path.join(os.path.dirname(HERE), "authsrv", "authsrv.py"),
               encoding="utf-8").read()
    tree = ast.parse(src)

    # (a) BOTH patterns against what authsrv ACTUALLY PRINTS, reconstructed from
    # its syntax tree. A test that only checked a pasted copy would stay green
    # through the exact drift that broke this.
    pop = next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
                and n.name == "spawn_population"), None)
    check(pop is not None, "authsrv defines spawn_population()")
    live_empty = find_print_fstring(pop, "no population rows") if pop else None
    check(live_empty is not None,
          "and its no-rows print is found in the tree -- the line this whole "
          "section is about", f"{live_empty!r}")
    if live_empty:
        check(deploy.UNPOPULATED_RE.findall(live_empty) == ["plaza"],
              "UNPOPULATED_RE matches the line authsrv BUILDS, not a copy of "
              "it pasted here -- reword the server's message and this goes red",
              f"{live_empty!r}")
        check(live_empty.endswith(EMPTY_LINE[len("[c1] "):]),
              "and the copy in this file is still the same line, so the "
              "canned logs below are testing the real thing",
              f"{live_empty!r}")

    # (b) the two patterns are DISJOINT, both directions. They share the
    # `area 'X':` prefix, which is exactly how one swallowed the other's line.
    check(deploy.UNPOPULATED_RE.findall(PLACED_LINE) == [],
          "and a populated line does NOT parse as the empty one")
    check(deploy.PLACED_RE.findall(EMPTY_LINE) == [],
          "and the empty line does NOT parse as a populated one -- the bug was "
          "the other half of this, and both halves are one edit apart")

    # (c) the three verdicts, behaviourally, on canned logs.
    check(serve_verdict(f"{MESH_LINE}\n{PLACED_LINE}\n", area="sculpt")
          == deploy.SERVE_PASS,
          "mesh MATCHES + every body placed -> PASS")
    check(serve_verdict(f"{MESH_LINE}\n{EMPTY_LINE}\n", area="plaza")
          == deploy.SERVE_UNPOPULATED,
          "mesh MATCHES + the area is empty -> SERVED-UNPOPULATED, which is "
          "neither of the other two -- this is the W2 case, and it exited 1")
    check(serve_verdict(f"{MESH_LINE}\n", area="plaza") == deploy.SERVE_FAILED,
          "mesh MATCHES + NEITHER line -> FAILED, because a server that threw "
          "on the way to spawn_population prints nothing at all and that still "
          "has to be caught")
    check(deploy.SERVE_UNPOPULATED not in (deploy.SERVE_PASS,
                                           deploy.SERVE_FAILED),
          "and the three verdicts are three distinct values -- an alias would "
          "make the new one unreadable in a transcript",
          f"{deploy.SERVE_PASS}/{deploy.SERVE_UNPOPULATED}/{deploy.SERVE_FAILED}")

    # (d) THE LOAD-BEARING HALF. The mesh is why the second run happens; an
    # empty area must not be able to talk it into passing. Same log as the
    # SERVED-UNPOPULATED case above, one number changed.
    bad_mesh = "[map] navmesh 0x287D3: 1 planes, 27 trapezoids"
    check(serve_verdict(f"{bad_mesh}\n{EMPTY_LINE}\n", area="plaza",
                        expect_traps=55) == deploy.SERVE_FAILED,
          "mesh DISAGREES + the area is empty -> still FAILED. An empty area "
          "downgrades a PASS; it can never lift a FAILED, and 27 vs 55 is the "
          "real pair -- ArenaNet's build of map 143 against ours")
    check(serve_verdict(f"{bad_mesh}\n{PLACED_LINE}\n", area="sculpt",
                        expect_traps=55) == deploy.SERVE_FAILED,
          "and a full population does not rescue a wrong mesh either")
    check(serve_verdict(f"{bad_mesh}\n", expect_traps=55)
          == deploy.SERVE_FAILED,
          "and with no --area at all the mesh is the entire verdict")

    # (e) the SECOND READER. Without this, SERVED-UNPOPULATED is a verdict that
    # cannot fail: the server says "nothing here", we write it down, green. The
    # content drift W2 went looking for would read as a clean run.
    check(serve_verdict(f"{MESH_LINE}\n{EMPTY_LINE}\n", area="plaza",
                        expect_rows=0) == deploy.SERVE_UNPOPULATED,
          "an empty area our content reader ALSO calls empty stays "
          "SERVED-UNPOPULATED -- two readers, agreeing")
    check(serve_verdict(f"{MESH_LINE}\n{EMPTY_LINE}\n", area="plaza",
                        expect_rows=5) == deploy.SERVE_FAILED,
          "but a server finding nothing where our content binds 5 rows is "
          "FAILED -- that is a population that went missing, and it is the one "
          "thing SERVED-UNPOPULATED must not be allowed to hide")
    check(serve_verdict(f"{MESH_LINE}\n{PLACED_LINE}\n", area="sculpt",
                        expect_rows=5) == deploy.SERVE_FAILED,
          "and the same disagreement is caught from the populated side: 3 of 3 "
          "placed is not a pass when our own reader binds 5")

    # (f) spawn_row_count mirrors area_population's filter. It is a SECOND
    # reader only if it reads the same predicates; a copy that drifted would be
    # a rubber stamp with a check's name on it.
    apop = next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
                 and n.name == "area_population"), None)
    check(apop is not None, "authsrv defines area_population()")
    if apop:
        body = ast.dump(apop)
        check("'area'" in body and "'enabled'" in body,
              "and it filters on `area` and `enabled` -- the two predicates "
              "deploy.spawn_row_count mirrors")
    counted = deploy.spawn_row_count(
        _FakeWorld({"a": {"area": "plaza", "enabled": True},
                    "b": {"area": "plaza"},
                    "c": {"area": "plaza", "enabled": False},
                    "d": {"area": "sculpt"},
                    "e": {}}), "plaza")
    check(counted == 2,
          "spawn_row_count takes rows naming the area, defaults `enabled` to "
          "true, and drops disabled rows and other areas", f"{counted}")

    # (g) and main() maps the verdicts to exit codes: ONLY FAILED returns 1.
    # Asked of the syntax tree because the alternative is a real client run.
    dep = open(deploy.__file__, encoding="utf-8").read()
    main_fn = next(n for n in ast.walk(ast.parse(dep))
                   if isinstance(n, ast.FunctionDef) and n.name == "main")
    guarded = [n for n in ast.walk(main_fn)
               if isinstance(n, ast.If)
               and any(isinstance(c, ast.Name) and c.id == "SERVE_FAILED"
                       for c in ast.walk(n.test))
               and any(isinstance(r, ast.Return)
                       and isinstance(r.value, ast.Constant)
                       and r.value.value == 1 for r in ast.walk(n))]
    check(len(guarded) == 1,
          "main() returns 1 from exactly ONE branch, and that branch tests "
          "SERVE_FAILED -- so SERVED-UNPOPULATED exits 0, which is the whole "
          "behaviour change", f"{len(guarded)} such branch(es)")


class _FakeWorld:
    """The one method `spawn_row_count` calls, over rows this test chooses."""

    def __init__(self, rows):
        self._rows = rows

    def rows(self, kind):
        return self._rows if kind == "spawn" else {}


def section4():
    """The size ceiling, and the one-tile snap that hid behind it."""
    print("\n4. bigger than one tile: snap_field, and what snap_block alone does")
    for dim in (32, 64, 96):
        raw = deploy.gen_plaza(dim)
        snapped, worst = stx.snap_field(raw, dim, dim)
        trn = stx.StrippedTerrain.build(dim, dim, snapped)
        back = stx.StrippedTerrain.decode(trn.encode())
        same = sum(1 for a, b in zip(back.heights, snapped) if a == b)
        check(same == dim * dim,
              f"{dim}x{dim} round-trips exactly after snap_field",
              f"{same}/{dim * dim}, worst moved {worst}")

    # NEGATIVE CONTROL. snap_block takes ONE 32x32 tile; handing it a whole
    # multi-tile field snaps tile 0 and silently leaves the rest, which is how
    # a 96x96 map lost 134 samples while reporting a 2-unit worst error. If
    # this ever stops losing samples, snap_block grew a whole-field meaning and
    # snap_field's reason to exist needs re-reading.
    dim = 64
    raw = deploy.gen_plaza(dim)
    one_tile, _w = stx.snap_block(raw)
    trn = stx.StrippedTerrain.build(dim, dim, one_tile)
    back = stx.StrippedTerrain.decode(trn.encode())
    lost = sum(1 for a, b in zip(back.heights, one_tile) if a != b)
    check(lost > 0,
          "snap_block ALONE on a 64x64 field still loses samples -- it is a "
          "one-tile function, and that is what snap_field is for",
          f"{lost} lost past the first 1024-sample tile")

    # and the loss is past tile 0, not scattered -- the signature of the defect
    idx = [i for i, (a, b) in enumerate(zip(back.heights, one_tile)) if a != b]
    check(idx and min(idx) >= stx.CHUNK_SIZE * stx.CHUNK_SIZE,
          "and every lost sample sits past the first tile, which is the "
          "fingerprint rather than a coincidence", f"first at {min(idx)}")

    # THE COMPRESSION GAIN, MEASURED PER SIZE AND BOUNDED LOOSELY. It had to be
    # measured rather than assumed: tag 1 of this chunk is entropy-coded already,
    # and a second general-purpose pass over an entropy coder's own output
    # normally buys nothing. What it buys here is everything AROUND tag 1 -- the
    # tile indices, the bit field, the two tables -- which an authored shape
    # makes extremely repetitive. Bounded as "strictly smaller" and printed with
    # the real figure: a pinned number would go red on any encoder change that
    # was an improvement, and the load-bearing claim is only the direction.
    for dim in (32, 64, 96):
        raw = deploy.gen_plaza(dim)
        snapped, _w = stx.snap_field(raw, dim, dim)
        blob = stx.StrippedTerrain.build(dim, dim, snapped).encode()
        stream = gwenc.encode(blob)
        check(len(stream) < len(blob),
              f"{dim}x{dim} authored terrain compresses -- gwenc is a GAIN on "
              f"our own shapes, not just on retail's",
              f"{len(blob)} B -> {len(stream)} B "
              f"({100.0 * len(stream) / len(blob):.1f}% of stored)")


def writer_argv(fn, script):
    """The string constants of the argv list that names `script`, or [].

    Read the ARGUMENT LIST, not the source text: the first version of this
    grepped the text and went red on deploy.py's own explanatory COMMENT about
    --check-overlaps. A grep cannot tell an argument from prose. Walking the
    whole SUBTREE matters too -- the script name arrives as
    os.path.join(HERE, "datmove.py"), so it is not a direct element of the list.
    """
    for node in ast.walk(fn):
        if not isinstance(node, ast.List):
            continue
        strs = [n.value for n in ast.walk(node)
                if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        if any(s.endswith(script) for s in strs):
            return strs
    return []


def section5(area):
    """Size selects a VERB: replace when it fits, relocate when it does not."""
    print("\n5. the size ceiling selects replace vs relocate")
    src = open(deploy.__file__, encoding="utf-8").read()
    tree = ast.parse(src)
    main_fn = next(n for n in ast.walk(tree)
                   if isinstance(n, ast.FunctionDef) and n.name == "main")
    # THE DISPATCH MOVED, 2026-08-20, and this pin moved WITH it rather than
    # being dropped. It used to ask whether main() itself could reach both
    # writers; the compress-fit-write-prove step is `install_partner` now, so
    # the same claim is two structural facts -- main calls it, and it reaches
    # both -- which is a stronger statement than the one sentence was.
    called = any(isinstance(n, ast.Call)
                 and getattr(n.func, "id", "") == "install_partner"
                 for n in ast.walk(main_fn))
    check(called, "main() calls install_partner() -- the install stage is a "
                  "function main RUNS, not one that merely exists")
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "install_partner")
    dumped = ast.dump(fn)
    check("datmove.py" in dumped and "datwrite.py" in dumped,
          "install can reach BOTH writers -- datwrite fits in place, datmove "
          "relocates, and an authored map bigger than its row needs the second")
    datmove_args = writer_argv(fn, "datmove.py")
    datwrite_args = writer_argv(fn, "datwrite.py")
    check(datmove_args and "--check-overlaps" not in datmove_args,
          "and does NOT pass --check-overlaps to datmove, which is a read-only "
          "verb that returns before moving -- it returned 0 with nothing "
          "written and the run reported success over ArenaNet's own map",
          f"{[a for a in datmove_args if a.startswith('--')]}")
    # THE COMPRESSION FLAGS, at BOTH call sites. Threading them through one of
    # the two branches is the exact shape of a half-fix: the relocate arm is the
    # one an authored map that outgrew its row takes, so a compressed replace
    # beside a stored relocate would put the deviation back precisely where a
    # bigger map lands. Asked of both argument lists for that reason.
    for label, argv in (("datwrite --replace", datwrite_args),
                        ("datmove --move", datmove_args)):
        check("--compression" in argv and "--expect" in argv,
              f"{label} is passed --compression AND --expect -- a compression-8 "
              f"write with no declared payload is refused at the CLI, and a "
              f"declaration is the only refutation that exists after the write",
              f"{[a for a in argv if a.startswith('--')]}")
    # the readback-after-install guard, which is what caught that
    check("the row does not hold what we wrote" in src,
          "install verifies by READING THE ROW BACK rather than by trusting an "
          "exit code")


# ---------------------------------------------------------------- section 7
#
# A HAND-LAID ARCHIVE HOLDING ONE MAP CHAIN. No vault, no client, no 3.9 GB
# copy: every question in section 7 is about which verb ran, what the row was
# marked, and what a reader gets back, and all three are properties of a
# reservation this file CHOOSES. On a real archive the reservation is whatever
# ArenaNet happened to compress into the row, so "compressed fits where stored
# did not" would be an accident of that map rather than a fact about the rule.
#
# THE LAYOUT, in 512-byte blocks:
#
#     b0        row 1  file header
#     b1        row 2  file-id table -- one pair, FILE_ID -> row 4
#     b2        row 4  the Bloated HEAD, flags 259, nextStream = 5
#     b3-b22    row 5  the Stripped PARTNER, flags 1 -- 20 blocks of extent,
#                      but its RESERVATION is ceil(size/512)*512 and `size` is
#                      what each case sets
#     b23-b60          FREE, 38 blocks, so a relocation has somewhere to go
#     b61       row 3  the master file table itself
#
# The map shape is the load-bearing part: `deploy.resolve_rows` finds the
# partner through `mapchunks.MapIndex`, which pairs a head (alloc flags 3,
# stream 1) to whatever row its nextStream names. A fixture that got the flags
# wrong would not resolve at all rather than resolve wrongly.
#
# SIXTEEN DECLARED ROWS, AND THE NUMBER IS NOT COSMETIC (raised from 6 on
# 2026-08-20 for section 8). `FIRST_CLAIMABLE_ROW` is 16: LoadMft never recycles
# a row below it and the client's open-time reconcile does not scan there, so
# `datalloc.plan_alloc` refuses to link a chain to any row underneath. With six
# declared rows an allocation would append at index 6 and be refused for a
# reason that is about the FIXTURE rather than about the code under test. Rows
# 6-15 are left erased and USED-clear; they are below the claimable line, so
# `datplan.free_rows` offers none of them and the created chain APPENDS -- which
# is the case the real archives are in (MEASURED on the C2 copy 2026-08-20: 0
# reusable spares, 48 bytes of MFT slack = exactly two rows = exactly one map).

BLOCK = 512
ENTRY_SIZE = 24
FILE_MAGIC = b"3AN\x1a"
MFT_MAGIC = b"Mft\x1a"
SLACK = 0xCC

ROW_HEADER, ROW_IDTABLE, ROW_SELF, ROW_HEAD, ROW_PARTNER = 1, 2, 3, 4, 5
ENTRY_COUNT = 16
MFT_BLOCK = 61
FILE_SIZE = (MFT_BLOCK + 1) * BLOCK
MFT_OFF = MFT_BLOCK * BLOCK
MFT_SIZE = ENTRY_COUNT * ENTRY_SIZE
HEAD_BLOCK, PARTNER_BLOCK = 2, 3
HEAD_SIZE = 300
FIXTURE_FILE_ID = 0x287D3      # map 143's own id, so the fixture reads like
                               # the row this arc actually installs into
MAP_HEAD_FLAGS = 259           # stream 1 | USED | FIRST_STREAM
MAP_PARTNER_FLAGS = 1          # stream 0 | USED
PLAIN_FILE_FLAGS = 3           # stream 0 | USED | FIRST_STREAM: a file, NOT a map
NEW_FILE_ID = 0x5F0B0          # the id content/maps.toml [map.166] carries, and
                               # the one section 8 creates. Free in the C2 copy
                               # and in this fixture, which holds 0x287D3 alone.
INSTALL_DIM = 64               # 9,051 B authored -> 1,148 B compressed, which
                               # straddles a 1,536 B reservation. At 32x32 the
                               # compressed stream is 472 B and no legal
                               # reservation is small enough to refuse it.


def pattern(seed, n):
    return bytes(1 + ((i * 37 + seed * 101) % 255) for i in range(n))


def self_crc(mft):
    """Row 3's crc, spelled out rather than imported from the writer."""
    acc = binascii.crc32(bytes(mft[0x00:ROW_SELF * ENTRY_SIZE]))
    return binascii.crc32(
        bytes(mft[(ROW_SELF + 1) * ENTRY_SIZE:ENTRY_COUNT * ENTRY_SIZE]), acc)


def build_archive(path, partner_size, file_id=FIXTURE_FILE_ID,
                  head_flags=MAP_HEAD_FLAGS, extra_rows=None):
    """One map chain whose partner declares `partner_size`. -> the head's bytes.

    `file_id` and `head_flags` are parameters for section 8's refusals, which are
    about what the id NAMES rather than about the map: a bit-31 spelling in the
    table, or a head that is a plain file (flags 3, stream 0) instead of a
    Bloated map head (259). Both defaults are the shape section 7 has always
    built, so nothing above changes.

    `extra_rows` is section 9's, and it exists to put a SQUATTER in the blocks a
    shrunk partner freed: {index: (offset, size, compression, flags,
    nextStream)}, merged over the map chain above. `datwrite.claimants` counts
    any row with a non-zero size whose RESERVATION intersects the range, so one
    row in a spare slot is the whole of grow-gate condition 1 -- and condition 1
    is the one that means something real about the archive rather than about the
    geometry. Rows 6-15 are erased and unused, so a squatter there disturbs
    nothing else in the fixture.
    """
    buf = bytearray(bytes([SLACK]) * FILE_SIZE)
    rows = {
        ROW_HEADER:  (0, 32, 0, 3, 0),
        ROW_IDTABLE: (1 * BLOCK, 8, 0, 3, 0),
        ROW_SELF:    (MFT_OFF, MFT_SIZE, 0, 3, 0),
        ROW_HEAD:    (HEAD_BLOCK * BLOCK, HEAD_SIZE, 0, head_flags,
                      ROW_PARTNER),
        ROW_PARTNER: (PARTNER_BLOCK * BLOCK, partner_size, 0,
                      MAP_PARTNER_FLAGS, 0),
    }
    rows.update(extra_rows or {})
    buf[BLOCK:BLOCK + 8] = struct.pack("<II", file_id, ROW_HEAD)
    head_bytes = pattern(ROW_HEAD, HEAD_SIZE)
    buf[HEAD_BLOCK * BLOCK:HEAD_BLOCK * BLOCK + HEAD_SIZE] = head_bytes
    buf[PARTNER_BLOCK * BLOCK:PARTNER_BLOCK * BLOCK + partner_size] = pattern(
        ROW_PARTNER, partner_size)

    head = bytearray(32)
    head[0:4] = FILE_MAGIC
    struct.pack_into("<I", head, 0x04, 32)
    struct.pack_into("<I", head, 0x08, BLOCK)
    struct.pack_into("<Q", head, 0x10, MFT_OFF)
    struct.pack_into("<I", head, 0x18, MFT_SIZE)
    struct.pack_into("<I", head, 0x0C, binascii.crc32(bytes(head[:12])))
    buf[0:32] = head

    mft = bytearray(MFT_SIZE)
    mft[0:4] = MFT_MAGIC
    struct.pack_into("<I", mft, 0x0C, ENTRY_COUNT)
    for row, (off, size, comp, flags, nxt) in rows.items():
        crc = 0 if row in (ROW_HEADER, ROW_SELF) else binascii.crc32(
            bytes(buf[off:off + size]))
        struct.pack_into("<QIHHII", mft, row * ENTRY_SIZE,
                         off, size, comp, flags, nxt, crc)
    struct.pack_into("<I", mft, ROW_SELF * ENTRY_SIZE + 20, self_crc(mft))
    buf[MFT_OFF:MFT_OFF + MFT_SIZE] = mft

    with open(path, "wb") as fh:
        fh.write(bytes(buf))
    return head_bytes


def read_row(path, row):
    """(offset, size, compression, flags, stored bytes) straight from the file.

    Written out of `int.from_bytes` and sharing no code with `archive.py`, for
    the same reason `test_datmove.py` spells out its own overlap walker: the
    question is whether the right bytes reached the right offset under the right
    code, and asking the reader under test is how that goes green by agreement.
    """
    with open(path, "rb") as fh:
        raw = fh.read()
    mft_off = int.from_bytes(raw[0x10:0x18], "little")
    mft_size = int.from_bytes(raw[0x18:0x1C], "little")
    mft = raw[mft_off:mft_off + mft_size]
    off, size, comp, flags, _nxt, _crc = struct.unpack_from(
        "<QIHHII", mft, row * ENTRY_SIZE)
    return off, size, comp, flags, raw[off:off + size]


def read_next(path, row):
    """`alloc.nextStream` of a row (+0x10), straight from the file.

    Section 8's own reader for the one field `read_row` does not return, and the
    only field that makes two rows a CHAIN. Same reason `read_row` exists:
    asking `mapchunks` whether the chain `mapchunks` built is right is agreement,
    not evidence.
    """
    with open(path, "rb") as fh:
        raw = fh.read()
    mft_off = int.from_bytes(raw[0x10:0x18], "little")
    mft_size = int.from_bytes(raw[0x18:0x1C], "little")
    mft = raw[mft_off:mft_off + mft_size]
    return struct.unpack_from("<I", mft, row * ENTRY_SIZE + 0x10)[0]


def read_id_pairs(path):
    """Every RAW (file_id, row) pair in the file-id table, straight from the file.

    RAW, i.e. no bit-31 convenience spelling registered -- the form the CLIENT
    can address. `archive.file_id_table`'s default answers a different question
    (see its docstring, and the three failures listed there), and section 8's
    whole subject is which of the two decides create-versus-install.
    """
    with open(path, "rb") as fh:
        raw = fh.read()
    mft_off = int.from_bytes(raw[0x10:0x18], "little")
    mft_size = int.from_bytes(raw[0x18:0x1C], "little")
    mft = raw[mft_off:mft_off + mft_size]
    off, size = struct.unpack_from("<QI", mft, ROW_IDTABLE * ENTRY_SIZE)
    return [struct.unpack_from("<II", raw, off + i) for i in range(0, size, 8)]


def spill(tmp, name, data):
    path = os.path.join(tmp, name)
    with open(path, "wb") as fh:
        fh.write(data)
    return path


def section7():
    """The install, end to end, against an archive with a known reservation.

    WHAT THIS SECTION IS REALLY ABOUT. Retail's own Stripped partners are
    compression 8 and ours were stored -- readable, but the deviation, and the
    ceiling: `datwrite --replace` refuses anything past the row's existing whole
    512-byte blocks, so an authored map had to be smaller UNCOMPRESSED than
    whatever ArenaNet had compressed into the same row. That is what capped
    every map this toolkit built at 32x32.

    So the headline is case (b): a reservation the authored bytes do NOT fit and
    the compressed stream does, taking `replace` where the old rule took
    `relocate`. Every other case is here to keep that one honest -- that the row
    is marked the way retail marks it, that a reader gets the authored bytes
    back, that the stored arm still writes exactly what it always did, and that
    a lie about the payload is refused before any byte moves.
    """
    print("\n7. the install: a compression-8 partner, judged on the stored size")
    dim = INSTALL_DIM
    snapped, _w = stx.snap_field(deploy.gen_plaza(dim), dim, dim)
    blob = stx.StrippedTerrain.build(dim, dim, snapped).encode()
    stream, code, note = deploy.install_bytes(blob)
    check(code == 8 and len(stream) < len(blob),
          "install_bytes compresses by default -- the retail shape is the "
          "DEFAULT and stored is the flag", f"{note}")
    stored_stream, stored_code, _n = deploy.install_bytes(blob, stored=True)
    check(stored_code == 0 and stored_stream is blob,
          "and --stored-install hands the writer the authored bytes untouched",
          f"code {stored_code}, {len(stored_stream)} B")

    with tempfile.TemporaryDirectory() as tmp:
        out = spill(tmp, "authored.bin", blob)

        def run(name, partner_size, stored=False):
            """One install onto a fresh fixture. -> (path, verb, head bytes)."""
            path = os.path.join(tmp, name)
            head_bytes = build_archive(path, partner_size)
            reservation = ((partner_size + 511) // 512) * 512
            verb = deploy.install_partner(
                path, out, blob, stored_stream if stored else stream,
                0 if stored else 8,
                ROW_HEAD, ROW_PARTNER, reservation, name)
            return path, verb, head_bytes

        # (a) BOTH fit. The plain case, and the one that proves the row comes
        # back as what a reader must get -- `Archive.read` decompresses, so
        # byte-identity here is a statement about the PAYLOAD and not about the
        # stream.
        path, verb, head_bytes = run("both", 9216)
        off, size, comp, _f, raw = read_row(path, ROW_PARTNER)
        check(verb == "replace", "a map that fits its reservation REPLACES in "
                                 "place", f"{verb}")
        check(comp == 8, "and the row is marked compression 8 -- the shape "
                         "retail's own Stripped partners have", f"{comp}")
        check(off == PARTNER_BLOCK * BLOCK and size == len(stream),
              "in place means the SAME offset, with the stream's own length",
              f"offset 0x{off:X}, {size} B")
        back, declared = gwdat.decompress(raw)
        check(back == blob and declared == len(blob),
              "and the row decodes back to the exact authored blob",
              f"{len(back)} B back, trailer declares {declared}")
        _o, _s, _c, _fl, head_now = read_row(path, ROW_HEAD)
        check(head_now == head_bytes,
              "and the HEAD row is untouched -- writing the partner is not "
              "allowed to disturb the row the arming step is about")

        # (b) THE HEADLINE. A reservation between the two sizes: stored does not
        # fit, compressed does. Under the rule this replaced, deploy compared
        # len(report.blob) against the reservation and this map relocated.
        path, verb, _h = run("only-compressed", 1536)
        off, size, comp, _f, raw = read_row(path, ROW_PARTNER)
        check(len(blob) > 1536 and len(stream) <= 1536,
              "the fixture straddles the reservation: stored does NOT fit, "
              "compressed does",
              f"{len(blob)} B stored, {len(stream)} B compressed, 1536 B row")
        check(verb == "replace",
              "and the fit is judged on the COMPRESSED size -- the same map "
              "against the same row RELOCATED under the old rule",
              f"{verb}")
        check(off == PARTNER_BLOCK * BLOCK and comp == 8
              and gwdat.decompress(raw)[0] == blob,
              "and it is still the authored blob, still marked 8, still in "
              "place", f"offset 0x{off:X}, comp {comp}")

        # (c) NEITHER fits. Compression raises the ceiling; it does not remove
        # it, and a badly scoped version of this change would have concluded
        # datmove was no longer reachable.
        path, verb, _h = run("neither", 1024)
        off, size, comp, _f, raw = read_row(path, ROW_PARTNER)
        check(verb == "relocate",
              "a map past its reservation even compressed still RELOCATES -- "
              "compression raised the ceiling, it did not remove it", f"{verb}")
        check(off != PARTNER_BLOCK * BLOCK and comp == 8
              and gwdat.decompress(raw)[0] == blob,
              "and datmove carried the compression code and the payload with "
              "it", f"offset 0x{off:X}, comp {comp}")

        # (d) THE CONTROL ARM. --stored-install must be the OLD bytes, because
        # that is the only thing that makes it useful if the client run says no.
        path, verb, _h = run("stored", 9216, stored=True)
        off, size, comp, _f, raw = read_row(path, ROW_PARTNER)
        check(verb == "replace" and comp == 0 and raw == blob,
              "--stored-install writes the authored bytes verbatim, marked 0 "
              "-- byte for byte what this command wrote before today",
              f"{verb}, comp {comp}, {size} B")

        # (e) SABOTAGE: lie about the payload a reader must get back. The
        # declaration is the ONLY refutation that exists after a compressed
        # write -- the entry crc is over the STORED bytes, so a row holding the
        # wrong payload passes every checksum rule and all ten open-time rules.
        bad = blob[:-1] + bytes([blob[-1] ^ 0xFF])
        liar = spill(tmp, "liar.bin", bad)
        path = os.path.join(tmp, "sabotage")
        build_archive(path, 9216)
        with open(path, "rb") as fh:
            before = fh.read()
        why = ""
        try:
            deploy.install_partner(path, liar, bad, stream, 8,
                                   ROW_HEAD, ROW_PARTNER, 9216, "sabotage")
        except deploy.Refused as exc:
            why = str(exc)
        with open(path, "rb") as fh:
            after = fh.read()
        check(bool(why), "a wrong --expect is REFUSED -- ONE byte of the "
                         "declared payload flipped, and the stream itself is "
                         "the good one", why or "the writer accepted it")
        check(after == before,
              "and NOTHING was written -- the check runs before the first byte "
              "reaches the archive, which is the only moment it can",
              f"{len(after)} B, unchanged")


# ---------------------------------------------------------------- section 8
#
# WORLDMAPS-W3: the map that displaces nobody.
#
# Every authored area before this one rides map 143 -- MFT rows 71496/71497, a
# live retail area in the owner's own copy that nothing in this repo can name
# (FINDINGS 16-P7: there are ZERO provably-dead rows in the archive). That was
# never a design, it was the only verb available: `datwrite` replaces a row and
# `datmove` moves one, and both start from a row ArenaNet made. `datalloc` is
# the third verb and this section is deploy learning to call it.
#
# WHAT CAN GO WRONG HERE IS NOT WHAT GOES WRONG ABOVE. Section 7's failures are
# loud -- a row holds the wrong bytes, a verb did nothing. A created chain fails
# QUIETLY, in ways the archive's own rules do not count: a file id registered on
# the partner instead of the head passes every crc rule and all ten of
# `datcheck`'s open-time rules while the client's reconcile deletes the head and
# frees its extent; a row below `FIRST_CLAIMABLE_ROW` is handed to somebody else
# at the next launch; an id whose bit-31 sibling already exists produces two live
# registrations nothing we own counts (studies/archivewrite/FINDINGS.md 17.5,
# still open). So this section reads the raw bytes back for each of those, with
# its own readers, rather than asking the modules that wrote them.


def section8():
    """The create branch: two rows under an id nothing binds."""
    print("\n8. the chain deploy CREATES, and the four ways it refuses to")
    dim = INSTALL_DIM
    snapped, _w = stx.snap_field(deploy.gen_plaza(dim), dim, dim)
    blob = stx.StrippedTerrain.build(dim, dim, snapped).encode()
    stream, code, _n = deploy.install_bytes(blob)

    # (a) THE SHAPE, WITHOUT AN ARCHIVE. Asked of `create_streams` directly
    # because the head/partner ORDER is the part with the silent failure mode:
    # `plan_alloc` refuses a swapped chain, but nothing downstream of a write
    # would -- MEASURED corpus-wide, the file-id table names 349 map heads and
    # zero partners, so a swap has no witness in the archive at all.
    streams = deploy.create_streams(blob, stream, code)
    check(len(streams) == 2 and streams[0].is_first and not streams[1].is_first,
          "the chain is HEAD FIRST: exactly streams[0] carries FIRST_STREAM, "
          "and that is the row the file id lands on",
          f"flags 0x{streams[0].flags:04X} / 0x{streams[1].flags:04X}")
    check(streams[0].data == b"" and streams[0].flags == MAP_HEAD_FLAGS,
          "and the head is BORN empty -- the zero-length re-bloat trigger is "
          "its only state ever, never an arm applied to a row that had content")
    check(streams[1].data == stream and streams[1].extra_bytes == 8
          and streams[1].expect == blob,
          "and the partner carries the compression-8 stream with the payload a "
          "reader must get back declared beside it -- the only refutation that "
          "exists after a compressed write",
          f"{len(stream)} B stream, expect {len(blob)} B")
    stored = deploy.create_streams(blob, blob, 0)
    check(stored[1].extra_bytes == 0 and stored[1].expect == blob,
          "and --stored-install's chain declares extraBytes 0 while STILL "
          "declaring the payload -- C-6 is reachable from both directions and "
          "`check_declarations` is run on stored streams for that reason")

    with tempfile.TemporaryDirectory() as tmp:
        out = spill(tmp, "authored.bin", blob)

        # (b) THE CREATE. An archive holding one map chain under 0x287D3, asked
        # for a file id it does not have.
        path = os.path.join(tmp, "create")
        build_archive(path, 4608)
        with Archive(path) as ar:
            rows, create = deploy.resolve_or_create(ar, NEW_FILE_ID, True)
        check(rows is None and create,
              "an id that binds nothing, on a map row that asked to own its "
              "file, selects CREATE rather than the install path")
        head_row, partner_row = deploy.create_chain(
            path, NEW_FILE_ID, blob, stream, 8, tmp, "frontier")

        off_h, size_h, _ch, flags_h, _rh = read_row(path, head_row)
        off_p, size_p, comp_p, flags_p, raw_p = read_row(path, partner_row)
        check(flags_h == MAP_HEAD_FLAGS and size_h == 0 and off_h == 0,
              "the created head is a Bloated map head with ZERO length and no "
              "extent -- the shape the client's re-bloat path keys on",
              f"flags 0x{flags_h:04X}, {size_h} B at 0x{off_h:X}")
        check(flags_p == MAP_PARTNER_FLAGS and comp_p == 8
              and size_p == len(stream),
              "and the partner is a stream-0 row marked compression 8, holding "
              "the stream's own length",
              f"flags 0x{flags_p:04X}, comp {comp_p}, {size_p} B at 0x{off_p:X}")
        check(gwdat.decompress(raw_p)[0] == blob,
              "and it decodes back to the exact authored blob -- a created row "
              "is checked by the same decompress-and-compare a replaced one is",
              f"{len(blob)} B")
        check(read_next(path, head_row) == partner_row
              and read_next(path, partner_row) == 0,
              "the head chains to the partner and the partner terminates -- two "
              "rows, one link, which is what makes them a MAP rather than two "
              "files", f"{head_row} -> {partner_row} -> 0")
        pairs = read_id_pairs(path)
        check((NEW_FILE_ID, head_row) in pairs,
              "the file id is registered, and on the HEAD -- an unregistered "
              "USED|FIRST_STREAM row is deleted by the open-time reconcile at "
              "the next launch, extent freed and 24 bytes memset", f"{pairs}")
        check(not [f for f, r in pairs if r == partner_row],
              "and NOT on the partner, which is the symmetric mistake no crc "
              "rule and no datcheck rule counts (0 of 349 real maps do it)")
        check(min(head_row, partner_row) >= 16,
              "both created rows sit at index >= 16 -- below that LoadMft never "
              "recycles and the reconcile never scans, so a row underneath is "
              "outside every rule this chain was reasoned about with",
              f"rows {head_row}, {partner_row}")

        # AND THE STREAM IS ON DISK BESIDE THE ARCHIVE. `install_partner` has to
        # write it -- the two CLI writers take --data FILE -- and `create_chain`
        # does not, since `datalloc` takes bytes. So the path that needed the
        # file least was the only one producing it, and the create path is the
        # one where these bytes have no second copy: a client that rewrites,
        # deletes or refuses the created chain leaves nothing to point at.
        # WORLDMAPS-W4's capture list names this file.
        c8 = os.path.join(tmp, "frontier.c8.bin")
        check(os.path.exists(c8) and open(c8, "rb").read() == stream,
              "the create path SPILLS the compression-8 stream it handed the "
              "allocator, byte for byte -- the install path always did, and this "
              "is the path where the archive is not a second copy of it",
              f"{os.path.basename(c8)}, {len(stream)} B")
        check(deploy.spill_stream(tmp, "storednote", blob, 0) is None
              and not os.path.exists(os.path.join(tmp, "storednote.c8.bin")),
              "and a STORED write spills nothing: there the stream IS the "
              "authored blob, already written, and a second identical file is "
              "one more thing that can drift out of step with the first")

        # (c) IDEMPOTENT. `created` is a claim about where a row CAME FROM, not
        # a mode it stays in: the second deploy of the same area must find the
        # chain and take the ordinary install path.
        # `here=`/`tag=` are how the chain PROVES it is ours: they name the
        # allocation journal `create_chain` wrote a moment ago. Without them a
        # `created = true` row whose id already binds is refused, because
        # `map_chain` checks the shape and 349 retail maps have that shape --
        # section 10 is where both halves of that are driven.
        with Archive(path) as ar:
            rows2, create2 = deploy.resolve_or_create(ar, NEW_FILE_ID, True,
                                                      here=tmp, tag="frontier")
        want = ((len(stream) + 511) // 512) * 512
        check(not create2 and rows2 == (head_row, partner_row, want),
              "a second deploy RESOLVES the chain it just made and falls "
              "through to install, reservation and all", f"{rows2}")
        verb = deploy.install_partner(path, out, blob, stream, 8, head_row,
                                      partner_row, rows2[2], "frontier2")
        check(verb == "replace"
              and gwdat.decompress(read_row(path, partner_row)[4])[0] == blob,
              "and re-installing into a created chain REPLACES in place -- the "
              "created rows are ordinary rows the moment they exist", f"{verb}")

        # (d) THE ID IS TAKEN BY SOMEBODY ELSE. Not a map chain: flags 3 on
        # stream 0 is a plain file. Refusing here is the whole safety of
        # choosing an id -- overwriting it makes one of two files unreachable
        # and nothing in datcheck counts a file id twice.
        path = os.path.join(tmp, "taken")
        build_archive(path, 4608, file_id=NEW_FILE_ID,
                      head_flags=PLAIN_FILE_FLAGS)
        why = ""
        try:
            with Archive(path) as ar:
                deploy.resolve_or_create(ar, NEW_FILE_ID, True)
        except deploy.Refused as exc:
            why = str(exc)
        check("NOT a Bloated map head" in why and f"row {ROW_HEAD}" in why,
              "an id already bound to something that is NOT a map chain is "
              "refused, naming the row and its flags", why.splitlines()[0]
              if why else "accepted")

        # (e) THE BIT-31 SIBLING, which is the gap `plan_alloc` still has:
        # it tests exact membership, so a plain id whose RENAMED spelling is in
        # the table is accepted there and would leave two live registrations.
        path = os.path.join(tmp, "sibling")
        build_archive(path, 4608, file_id=NEW_FILE_ID | 0x80000000)
        why = ""
        try:
            with Archive(path) as ar:
                deploy.resolve_or_create(ar, NEW_FILE_ID, True)
        except deploy.Refused as exc:
            why = str(exc)
        check("bit-31 sibling" in why,
              "an id whose bit-31 sibling is bound is refused BEFORE the "
              "allocator sees it -- FcArchive's rename marker means a "
              "replacement is pending on that row, not that the id is spare",
              why.splitlines()[0] if why else "accepted")
        # NEGATIVE CONTROL for that check: the same archive, asked about the
        # id the sibling is a rename OF, is a different question -- and the
        # plain id it renames is exactly what must NOT resolve.
        with Archive(path) as ar:
            raw_names = dict(archive_mod.file_id_table(ar, raw=True))
        check(NEW_FILE_ID not in raw_names
              and (NEW_FILE_ID | 0x80000000) in raw_names,
              "and the fixture really is the dual-registration shape: the raw "
              "table holds the renamed spelling and not the plain one, which "
              "is the state `file_id_table`'s default would hide", f"{raw_names}")

        # (f) AN ABSENT ID ON A ROW THAT DID NOT ASK. The old refusal, kept:
        # "resolves nowhere" is also what a typo looks like.
        path = os.path.join(tmp, "absent")
        build_archive(path, 4608)
        why = ""
        try:
            with Archive(path) as ar:
                deploy.resolve_or_create(ar, NEW_FILE_ID, False)
        except deploy.Refused as exc:
            why = str(exc)
        check("created = true" in why,
              "an absent id on a row WITHOUT `created = true` still refuses "
              "rather than allocating -- creating on a typo would mint two MFT "
              "rows for a map nobody meant", why.splitlines()[0]
              if why else "accepted")

        # (g) SABOTAGE: lie about the payload, through the CREATE path. The
        # declaration is checked before the plan, so nothing reaches the file.
        bad = blob[:-1] + bytes([blob[-1] ^ 0xFF])
        path = os.path.join(tmp, "liar")
        build_archive(path, 4608)
        with open(path, "rb") as fh:
            before = fh.read()
        why = ""
        try:
            deploy.create_chain(path, NEW_FILE_ID, bad, stream, 8, tmp, "liar")
        except deploy.Refused as exc:
            why = str(exc)
        with open(path, "rb") as fh:
            after = fh.read()
        check(bool(why),
              "a wrong declared payload is REFUSED on the create path too -- "
              "ONE byte flipped, and the stream itself is the good one",
              why.splitlines()[0] if why else "the allocator accepted it")
        check(after == before,
              "and NOTHING was written: the check runs before the plan, let "
              "alone before the first byte", f"{len(after)} B, unchanged")

        # (h) SABOTAGE: register the PARTNER instead of the head. Driven by
        # hand rather than through deploy, because deploy cannot express it --
        # which is the claim being made. `plan_alloc` is the gate that refuses.
        why = ""
        try:
            with Archive(os.path.join(tmp, "create")) as ar:
                datalloc.plan_alloc(ar, [streams[1], streams[0]],
                                    NEW_FILE_ID + 1)
        except datalloc.Refused as exc:
            why = str(exc)
        check("FLAG_FIRST_STREAM" in why,
              "a chain handed over PARTNER FIRST is refused by the allocator's "
              "own shape loop -- the head is the row the id resolves to and the "
              "row the reconcile checks", why.splitlines()[0]
              if why else "accepted")

    # (i) AND main() RUNS IT. Everything above drives the create branch
    # directly, which proves it works and says nothing about whether the COMMAND
    # can reach it -- the same gap section 3 opened for `readback()` and section
    # 5 for `install_partner()`. Asked of the syntax tree, with the sabotage that
    # makes it flip, because a branch no command line reaches is a docstring.
    src = open(deploy.__file__, encoding="utf-8").read()

    def called_in_main(text):
        fn = next(n for n in ast.walk(ast.parse(text))
                  if isinstance(n, ast.FunctionDef) and n.name == "main")
        return {getattr(n.func, "id", "") for n in ast.walk(fn)
                if isinstance(n, ast.Call)}

    names = called_in_main(src)
    check({"resolve_or_create", "create_chain"} <= names,
          "main() calls BOTH resolve_or_create (which decides) and create_chain "
          "(which allocates) -- the decision and the write are separate "
          "functions and a command line that reaches only one is not a feature",
          f"{sorted(names & {'resolve_or_create', 'create_chain', 'install_partner'})}")
    swapped = src.replace("head_row, partner_row = create_chain(",
                          "head_row, partner_row = install_partner(")
    check(swapped != src and "create_chain" not in called_in_main(swapped),
          "and pointing that call at the INSTALL writer instead makes the check "
          "go red -- without this control it would pass on the definition alone")

    # (j) WHAT A DRY RUN SAYS, which is a check about a PREDICTION being
    # scorable rather than about bytes. The decision to allocate is computed
    # only under --install (deciding costs a refusal; a build-only run must not
    # refuse), and the create line used to be printed under that same decision.
    # So `deploy.py --area frontier --dat <copy>` with no --install printed the
    # two sizes and nothing about the row -- and WORLDMAPS-W4's step 1 is
    # exactly that command, run to confirm the create branch WILL fire before a
    # client is started. A correct dry run read as a refutation of the join.
    check(deploy.create_note(NEW_FILE_ID, 2028, None, True, False) is not None
          and "CREATE" in deploy.create_note(NEW_FILE_ID, 2028, None, True, False)
          and hex(NEW_FILE_ID) in deploy.create_note(NEW_FILE_ID, 2028, None,
                                                     True, False),
          "a BUILD-ONLY run against an unbound id on a `created = true` row says "
          "so, naming the id -- the dry run W4's step 1 registers a prediction "
          "against, which said nothing at all until 2026-08-20",
          deploy.create_note(NEW_FILE_ID, 2028, None, True, False))
    said = deploy.create_note(NEW_FILE_ID, 2028, None, True, True)
    check("no reservation to judge" in said and "2028 B" in said,
          "the --install run keeps the line it always printed -- there the row "
          "is not hypothetical, so it says the stream WILL be given one", said)
    said = deploy.create_note(NEW_FILE_ID, 2028, None, False, False)
    check("REFUSE" in said and "created = true" in said,
          "an unbound id on a row that did NOT ask to own its file previews the "
          "refusal instead of the create -- the same distinction "
          "resolve_or_create makes, made before anything is written", said)
    check(deploy.create_note(NEW_FILE_ID, 2028, 71496, True, False) is None,
          "and an id that BINDS something says nothing here: verify() has "
          "already said what that row's reservation does with these bytes, and "
          "two lines about one row is how they drift apart")

    def guarded_by(text, callee, names):
        """The `if` tests, inside main(), that a call to `callee` sits under."""
        fn = next(n for n in ast.walk(ast.parse(text))
                  if isinstance(n, ast.FunctionDef) and n.name == "main")
        found = []
        for node in ast.walk(fn):
            if not isinstance(node, ast.If):
                continue
            if not any(isinstance(c, ast.Call)
                       and getattr(c.func, "id", "") == callee
                       for c in ast.walk(node)):
                continue
            found.extend(sorted({getattr(n, "id", "") or getattr(n, "attr", "")
                                 for n in ast.walk(node.test)} & names))
        return found

    gate = {"create", "install"}
    check("create_note" in names and not guarded_by(src, "create_note", gate),
          "and main() calls create_note OUTSIDE any `create`/`install` test -- "
          "the flag is an ARGUMENT to the note, not the gate on it, which is the "
          "whole content of the fix", f"guards {guarded_by(src, 'create_note', gate)}")
    # THE NEWLINE IN THE PATTERN IS LOAD-BEARING: without it the pattern is a
    # SUBSTRING of its own replacement's indented form, so running this control
    # against an already-guarded source produced `if` with no body and an
    # IndentationError out of ast.parse instead of a clean red.
    walled = src.replace(
        "\n    row_note = create_note(",
        "\n    if create:\n        row_note = create_note(")
    check(walled != src and guarded_by(walled, "create_note", gate) == ["create"],
          "and putting it back under `if create:` makes that check go red -- "
          "without this control it would pass on any source that merely mentions "
          "the function")

    # (k) THE TWO NEW CONTENT ROWS LOAD. Repo only, for section 0's reason.
    world = content_mod.load(vault_dir="")
    m = world.get("map", "166")
    a = world.get("area", "frontier")
    check(int(m["file_id"]) == NEW_FILE_ID and bool(m.get("created")) is True,
          "maps.toml [map.166] carries the created file id and says it is "
          "created", f"{int(m['file_id']):#x}, created={m.get('created')}")
    check(m.provenance["source"] == "invented"
          and a.provenance["source"] == "invented"
          and len(m.provenance.get("verified", "")) > 200,
          "both new rows are provenance 'invented' with a real verified string "
          "-- the map is not observed, it is chosen, and the row says so",
          f"{len(m.provenance.get('verified', ''))} chars")
    check(int(a["map_id"]) == 166 and int(a["dims"]) == INSTALL_DIM,
          "and area.frontier names that map row -- the join deploy makes is "
          "area -> map row -> file id, so an area pointing at 143 would install "
          "into the displacement row and never reach the create branch",
          f"map_id {a['map_id']}, {a['dims']}x{a['dims']}")
    check(166 in world.map_static_config(),
          "and the server's own map_static_config still builds with it in -- a "
          "content row the world cannot index is a row that breaks startup")
    sculpt = world.get("area", "sculpt")
    check(int(a["donor_file_id"]) == int(sculpt["donor_file_id"])
          and int(a["constants_file_id"]) == int(sculpt["constants_file_id"]),
          "and frontier borrows from the SAME donors as sculpt, by FILE ID -- "
          "so the one thing that differs between a proven area and this one is "
          "where its rows came from",
          f"biome {int(a['donor_file_id']):#x}, "
          f"constants {int(a['constants_file_id']):#x}")


# ---------------------------------------------------------------- section 9
#
# WORLDMAPS-W5: the row's own headroom, declared by the area.
#
# THE CASE THIS SECTION EXISTS FOR IS ONE THAT COULD NOT HAPPEN UNTIL TODAY. A
# created partner's reservation was exactly its first install's length and a
# displaced one's was recomputed from its current size, so a row that had been
# shrunk could never be grown back: `install_partner` compared and relocated,
# and `datwrite`'s `grow_to` -- the flag for precisely this -- was never passed
# by anything. The GROWS-BACK-IN-PLACE arm below is therefore the load-bearing
# new check, and it is paired with a control that removes the budget and watches
# the same install relocate instead.
#
# AND THE REFUSAL IS CHECKED AS HARD AS THE SUCCESS. `_grow_gate`'s first
# condition -- another live row has taken the blocks this one freed -- is a fact
# about the archive, and a fallback that swallowed it would turn a claimant
# conflict into a relocation that quietly worked. So the squatter fixture drives
# the gate red on purpose, and the run has to SAY so before it relocates.


@contextlib.contextmanager
def captured():
    """stdout as a string, INCLUDING the grow arm's writer.

    The replace and relocate arms hand their subprocess the real fd, so those
    writers print past this buffer to the console. The GROW arm does not: it
    captures the writer (the fallback decision is made from what the writer
    SAID) and re-writes both streams to `sys.stdout`, which `redirect_stdout`
    has swapped -- so `datwrite`'s own lines land in here. That asymmetry is
    what the FLOOR comment's grep arithmetic is about, and it is why a check
    can assert on the gate's own sentence at all.
    """
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        yield buf


def section9():
    """A declared budget: created with it, grown back into it, and past it."""
    print("\n9. reserve_bytes: the headroom an area declares for its own row")

    def authored(dim):
        snapped, _w = stx.snap_field(deploy.gen_plaza(dim), dim, dim)
        blob = stx.StrippedTerrain.build(dim, dim, snapped).encode()
        stream, code, _n = deploy.install_bytes(blob)
        return blob, stream, code

    b64, s64, _c = authored(64)      # 9,051 B ->  1,148 B, reservation 1,536
    b96, s96, _c = authored(96)      # 20,183 B -> 1,952 B, reservation 2,048
    b128, s128, _c = authored(128)   # 35,542 B -> 2,744 B, reservation 3,072
    BUDGET = 2048                    # chosen here, like section 7's reservations

    # (a) THE CHAIN'S SHAPE. The budget goes on the partner and `datalloc.Stream`
    # refuses it on the head, which is why this is asked of `create_streams`
    # rather than left to the allocator to notice.
    streams = deploy.create_streams(b64, s64, 8, reserve=BUDGET)
    check(streams[1].reserve == BUDGET and streams[0].reserve == 0,
          "the budget rides the PARTNER, the row that holds the geometry -- the "
          "head is born empty and owns no extent to reserve",
          f"head {streams[0].reserve}, partner {streams[1].reserve}")
    why = ""
    try:
        datalloc.Stream(b"", MAP_HEAD_FLAGS, reserve=BUDGET)
    except datalloc.Refused as exc:
        why = str(exc)
    check("owns NO EXTENT" in why,
          "and putting it on the head is REFUSED by the allocator rather than "
          "accepted and ignored", why.splitlines()[0] if why else "accepted")
    check(deploy.create_streams(b64, s64, 8)[1].reserve == 0,
          "CONTROL: with no budget the partner asks for nothing, which is every "
          "run of this command before WORLDMAPS-W5")

    with tempfile.TemporaryDirectory() as tmp:
        out64 = spill(tmp, "a64.bin", b64)
        out96 = spill(tmp, "a96.bin", b96)
        out128 = spill(tmp, "a128.bin", b128)

        # (b) CREATED WITH THE BUDGET, then re-installed THREE times: the
        # iterating loop an author actually runs, in one archive, so each verb
        # is judged against the row the previous one left behind.
        path = os.path.join(tmp, "budget")
        build_archive(path, 4608)
        with captured():
            head_row, partner_row = deploy.create_chain(
                path, NEW_FILE_ID, b64, s64, 8, tmp, "budget", reserve=BUDGET)
        off, size, comp, _f, raw = read_row(path, partner_row)
        check(size == len(s64) and comp == 8 and gwdat.decompress(raw)[0] == b64,
              "the created row declares the PAYLOAD's size and holds it -- a "
              "budget moves the reservation and nothing the client reads",
              f"{size} B at 0x{off:X}, comp {comp}")
        with open(path, "rb") as fh:
            whole = fh.read()
        tail = whole[off + size:off + BUDGET]
        check(len(tail) == BUDGET - size and set(tail) == {0},
              "and the row was GIVEN the whole budget: zeroed to the end of it, "
              "where this fixture fills unclaimed space with 0xCC -- the "
              "reservation is real rather than the 1,536 B a 1,148 B payload "
              "would have taken", f"{len(tail)} B of zeroes past the payload")

        with Archive(path) as ar:
            rows2, create2 = deploy.resolve_or_create(ar, NEW_FILE_ID, True,
                                                      here=tmp, tag="budget")
        check(not create2 and rows2[2] == 1536,
              "and the archive reports that row's ceiling as 1,536 B, NOT the "
              "2,048 it was given -- the 24-byte MFT row has no entitlement "
              "field, which is exactly why the AREA has to state one",
              f"resolve_rows says {rows2[2]} B")

        # THE HEADLINE. 1,952 B is past the 1,536 the archive reports and inside
        # the 2,048 the area declared, so the row takes its own freed blocks
        # back instead of moving. This arm did not exist before today.
        with captured() as buf:
            verb = deploy.install_partner(path, out96, b96, s96, 8, head_row,
                                          partner_row, rows2[2], "grow96",
                                          reserve=BUDGET, created=True)
        grew = buf.getvalue()
        off2, size2, comp2, _f, raw2 = read_row(path, partner_row)
        check(verb == "grow" and off2 == off,
              "a bigger install inside the declared budget GROWS BACK IN PLACE "
              "-- same row, same offset, a reservation annexed from the blocks "
              "this row freed", f"{verb}, 0x{off:X} -> 0x{off2:X}")
        check(size2 == len(s96) and comp2 == 8
              and gwdat.decompress(raw2)[0] == b96,
              "and it holds the new map, still marked 8, read back through the "
              "same decompress-and-compare a replace gets", f"{size2} B")
        check("GROWS BACK" in grew and str(BUDGET) in grew,
              "and the run SAYS which of the three outcomes happened, naming "
              "the entitlement it is spending -- a grown row and a row that "
              "never needed to grow are indistinguishable afterwards",
              next((l.strip() for l in grew.splitlines() if "GROWS BACK" in l),
                   "said nothing")[:96])

        # PAST THE BUDGET. Compression raised the ceiling and a budget raises it
        # again; neither removes it.
        with captured() as buf:
            verb = deploy.install_partner(path, out128, b128, s128, 8, head_row,
                                          partner_row, 2048, "far128",
                                          reserve=BUDGET, created=True)
        far = buf.getvalue()
        off3, size3, comp3, _f, raw3 = read_row(path, partner_row)
        check(verb == "relocate" and off3 != off2,
              "an install past the declared budget RELOCATES -- the budget is a "
              "statement about what this row was given, not a request for more",
              f"{verb}, 0x{off2:X} -> 0x{off3:X}")
        check(f"past the {BUDGET} B" in far,
              "and says the budget is what it is past, rather than reporting a "
              "bare size", next((l.strip() for l in far.splitlines()
                                 if "RELOCATES" in l), "said nothing")[:96])
        check(size3 == len(s128) and gwdat.decompress(raw3)[0] == b128,
              "and the moved row holds the new map", f"{size3} B")

        # AND BACK DOWN. The row now reserves 3,072; a smaller map fits and the
        # first arm still reads "replace", unchanged by any of this.
        with captured() as buf:
            verb = deploy.install_partner(path, out64, b64, s64, 8, head_row,
                                          partner_row, 3072, "back64",
                                          reserve=BUDGET, created=True)
        check(verb == "replace" and "FITS" in buf.getvalue(),
              "a smaller map after that simply FITS -- the ordinary arm is "
              "untouched by the budget", f"{verb}")

        # (c) THE CONTROL FOR THE HEADLINE. Same archive shape, same stream,
        # same shrunk ceiling -- and no declared budget. Without this the grow
        # above could be anything about the fixture rather than about the field.
        def install(name, partner_size, blob, stream, reserve, extra_rows=None,
                    created=True):
            p = os.path.join(tmp, name)
            build_archive(p, partner_size, extra_rows=extra_rows)
            spilled = spill(tmp, f"{name}.bin", blob)
            with captured() as b:
                v = deploy.install_partner(p, spilled, blob, stream, 8,
                                           ROW_HEAD, ROW_PARTNER,
                                           ((partner_size + 511) // 512) * 512,
                                           name, reserve=reserve,
                                           created=created)
            return p, v, b.getvalue()

        p, verb, said = install("nobudget", 1024, b64, s64, 0)
        moved = read_row(p, ROW_PARTNER)[0]
        check(verb == "relocate" and moved != PARTNER_BLOCK * BLOCK,
              "CONTROL: the SAME install with no declared budget relocates, as "
              "every run of this command did before today -- the budget is what "
              "changes the verb, not the geometry and not the fixture",
              f"{verb}, 0x{PARTNER_BLOCK * BLOCK:X} -> 0x{moved:X}")
        p, verb, said = install("withbudget", 1024, b64, s64, 8192)
        check(verb == "grow"
              and read_row(p, ROW_PARTNER)[0] == PARTNER_BLOCK * BLOCK,
              "and with one declared it grows in place instead -- one field "
              "apart, opposite verbs", f"{verb}")

        # AND THE SECOND HALF OF THE GATE. `grow_to` is a statement about what
        # a row was GIVEN. For a chain this toolkit allocated the area's budget
        # IS that statement -- creation asked for exactly it. For a RETAIL row
        # we are displacing it is not: ArenaNet gave that row whatever it gave
        # it, and annexing the blocks behind it because our recipe declares a
        # number would be inventing an entitlement. So the budget alone must not
        # be enough, and this is the same install as the line above with the
        # other field flipped.
        p, verb, said = install("notours", 1024, b64, s64, 8192, created=False)
        moved = read_row(p, ROW_PARTNER)[0]
        check(verb == "relocate" and moved != PARTNER_BLOCK * BLOCK,
              "CONTROL: the same budget on a row we did NOT create is not "
              "spendable -- a displaced retail row fits or relocates exactly as "
              "it did before this field existed",
              f"{verb}, 0x{PARTNER_BLOCK * BLOCK:X} -> 0x{moved:X}")
        check("NOT spendable" in said and "8192" in said,
              "and the run SAYS the budget went unspent rather than leaving an "
              "operator to compare two numbers that fit -- this is the one "
              "relocation whose cause is a rule and not a size",
              next((l.strip() for l in said.splitlines()
                    if "RELOCATES" in l), "said nothing")[:120])
        check("GROWS BACK" not in said,
              "and it never asked datwrite to grow: --grow-to on a retail row "
              "would be us stating what ArenaNet gave it")

        # (d) THE GATE SAYS NO. A squatter sits in the block this row would
        # annex, which is `_grow_gate` condition 1 and the only one of the four
        # that means somebody else is using the space.
        squat = {6: (PARTNER_BLOCK * BLOCK + 1024, 300, 0, MAP_PARTNER_FLAGS, 0)}
        p, verb, said = install("claimed", 1024, b64, s64, 8192,
                                extra_rows=squat)
        moved = read_row(p, ROW_PARTNER)[0]
        check(verb == "relocate" and moved != PARTNER_BLOCK * BLOCK,
              "a grow the gate refuses still gets the map installed -- it "
              "relocates rather than failing the run", f"{verb}")
        check("THE GROW GATE REFUSED" in said and "CLAIMED" in said,
              "and the refusal is PRINTED, quoting the gate's own sentence -- a "
              "silent fallback is how a claimant conflict becomes invisible",
              next((l.strip() for l in said.splitlines()
                    if "GROW GATE REFUSED" in l), "said nothing")[:96])
        check("RELOCATING instead" in said,
              "and the relocation names the refusal as its reason rather than "
              "reading as an ordinary size decision")
        check(gwdat.decompress(read_row(p, ROW_PARTNER)[4])[0] == b64,
              "and the relocated row holds the authored map, proved by the same "
              "readback every other arm gets")
        _o, sq_size, _c, _fl, _r = read_row(p, 6)
        check(sq_size == 300,
              "and the squatter is untouched -- the point of the gate is that "
              "its 300 B are still its own", f"row 6 holds {sq_size} B")

        # (e) AN UNRECOGNISED FAILURE IS NOT A GATE REFUSAL. Same grow, but the
        # declared payload is a lie: the gate PASSES (the blocks are free) and
        # datwrite then refuses on the declaration. Falling back to datmove here
        # would turn "these bytes are not what you declared" into a relocation
        # that quietly succeeded.
        bad = b64[:-1] + bytes([b64[-1] ^ 0xFF])
        liar = spill(tmp, "liar64.bin", bad)
        p = os.path.join(tmp, "liar")
        build_archive(p, 1024)
        with open(p, "rb") as fh:
            before = fh.read()
        why = ""
        with captured() as buf:
            try:
                deploy.install_partner(p, liar, bad, s64, 8, ROW_HEAD,
                                       ROW_PARTNER, 1024, "liar", reserve=8192,
                                       created=True)
            except deploy.Refused as exc:
                why = str(exc)
        said = buf.getvalue()
        with open(p, "rb") as fh:
            after = fh.read()
        check("the archive writer refused" in why,
              "a grow that fails for a reason the gate did not give is RAISED, "
              "not relocated around -- ONE byte of the declared payload flipped",
              why or "it fell through to datmove")
        # AND THE NEGATIVES, WHICH ARE THE CHECK. The two above pass even when
        # the recogniser is broken to accept ANY failure, because `datmove`
        # independently refuses the same lie and re-raises the identical
        # sentence with nothing written -- MEASURED, by breaking it: the
        # behavioural checks stayed green while a declaration fault was
        # misclassified as a claimant conflict and relocated around, which is
        # the exact failure this arm exists to catch. What that sabotage cannot
        # survive is the run having SAID the gate refused when it did not.
        check("THE GROW GATE REFUSED" not in said,
              "and it did not report a gate refusal the gate never gave -- the "
              "recogniser's whole job is telling those two apart, and a "
              "fallback that ran and then failed anyway looks identical from "
              "the outside", next((l.strip() for l in said.splitlines()
                                   if "GROW GATE" in l), "said nothing"))
        check("RELOCATING instead" not in said,
              "and it did not relocate around it: a declaration fault must not "
              "become a move that quietly succeeds on some other archive where "
              "datmove would take these bytes",
              next((l.strip() for l in said.splitlines()
                    if "RELOCATING" in l), "did not relocate"))
        check(after == before,
              "and nothing was written: the declaration is checked before the "
              "first byte either way", f"{len(after)} B, unchanged")
        check(deploy.grow_gate_refusal(
                  "row 5 reserves 1024 bytes and the new payload is 1148") is None
              and deploy.grow_gate_refusal(
                  "row 5 needs to grow ... is CLAIMED by row 6") is not None,
              "and the recogniser itself is asked both ways: an ordinary "
              "refusal is not a gate refusal, and the gate's own sentence is")
        for marker in deploy.GROW_GATE_MARKERS:
            check(deploy.grow_gate_refusal(f"  x {marker} y") is not None,
                  f"the recogniser knows grow-gate condition {marker!r}")

        # (e2) AND A BAD BUDGET IS THIS COMMAND'S REFUSAL, not a traceback.
        # `create_streams` builds a `datalloc.Stream`, so the create path gained
        # a raise site that `deploy.__main__` -- which catches `deploy.Refused`
        # and nothing else -- cannot see. An authoring mistake in
        # content/areas.toml is the likeliest way anybody meets it, and the
        # difference is exit 1 with a stack against exit 2 with a remedy.
        why, kind = "", None
        # BARE `Exception`, because the TYPE is what is being checked: catching
        # deploy.Refused here would let the wrong class through to the runner.
        try:
            with captured():
                deploy.create_chain(os.path.join(tmp, "budget"), NEW_FILE_ID,
                                    b64, s64, 8, tmp, "toosmall", reserve=1000)
        except Exception as exc:                          # noqa: BLE001
            why, kind = str(exc), type(exc)
        # MODULE AND NAME: both classes are called `Refused`, so the bare name
        # reads identically whichever one was raised.
        named = f"{kind.__module__}.{kind.__name__}" if kind else "nothing raised"
        check(kind is deploy.Refused,
              "a budget UNDER its own payload reaches the operator as this "
              "command's own Refused -- `__main__` catches deploy.Refused and "
              "nothing else, so a raw datalloc.Refused is a traceback", named)
        check("reserve_bytes" in why and "areas.toml" in why,
              "and it names the file to edit: the number came from content, so "
              "the remedy is a content edit and not an archive one",
              why.splitlines()[-1].strip() if why else "said nothing")

    # (f) WHAT A DRY RUN SAYS, before any of it. `verify` predicts a verb from
    # the row's CURRENT reservation, which contradicts the install for exactly
    # the case this rung added -- so the budget gets its own line.
    check(deploy.budget_note(1952, 1536, 0, created=True) is None,
          "an area with no budget prints no budget line -- the field is "
          "optional and its absence is silent")
    said = deploy.budget_note(1952, 1536, 2048, created=True)
    check("GROW" in said and "grow gate" in said,
          "past the reservation and inside the budget: the preview says GROW, "
          "and names the gate that can still refuse it", said)
    said = deploy.budget_note(1148, 1536, 2048, created=True)
    check("not needed" in said,
          "inside the reservation: the budget says so rather than claiming "
          "credit for a replace that needed nothing", said)
    said = deploy.budget_note(2744, 2048, 2048, created=True)
    check("RELOCATES" in said,
          "past both: the preview agrees with the verb the install will pick",
          said)
    said = deploy.budget_note(1148, None, 2048, created=True)
    check("CREATE" in said,
          "and on the create path there is no reservation to compare against, "
          "so it states what the allocator will be asked for", said)
    # THE PREVIEW MIRRORS THE GATE, or it predicts a verb the install will not
    # pick. Same numbers as the GROW line above, `created` flipped.
    said = deploy.budget_note(1952, 1536, 2048, created=False)
    check("RELOCATES" in said and "created = true" in said and "GROW" not in said,
          "and on a row we did not create the preview says RELOCATES and names "
          "the missing `created = true` -- a preview that promised a grow the "
          "install refuses to attempt is worse than no line at all", said)

    # THE CONTENT ROW ITSELF, repo only for section 0's reason. The number is a
    # CHOICE and the row says where it came from; what is checked here is that
    # it loads as an int, that it is big enough to be worth declaring, and that
    # the areas which never asked for one still read as zero.
    world = content_mod.load(vault_dir="")
    front = world.get("area", "frontier")
    budget = front.get("reserve_bytes")
    check(isinstance(budget, int) and budget % 512 == 0,
          "content/areas.toml's `reserve_bytes` loads as a whole number of "
          "512-byte blocks -- datalloc refuses a fraction, and a budget that "
          "does not round is a budget with a surprise in it", f"{budget} B")
    check(budget >= 2828,
          "and it holds the largest compressed partner this toolkit has "
          "MEASURED -- 2,828 B at 96x96 on build 38797's donors -- with room "
          "over, which is the whole claim the row makes for it",
          f"{budget} B against 2,828 B")
    check(int(front["dims"]) == INSTALL_DIM and budget > 4 * len(s64),
          "the area it sits on is 64x64 and installs far under it, so the "
          "budget is headroom for a LATER map rather than a fit for this one",
          f"{len(s64)} B installed, {budget} B reserved")
    check(world.get("area", "plaza").get("reserve_bytes", 0) == 0,
          "and an area that never asked for one reads as zero -- the field is "
          "optional and its absence is the pre-WORLDMAPS-W5 behaviour exactly")
    # AND THE ROW IT SITS ON OWNS ITS FILE. A budget on a displacing area is
    # unspendable by design, so the one row that declares one has to be the
    # created kind or the field in the repo is decoration.
    check(bool(world.get("map", str(front["map_id"])).get("created", False)),
          "and the area that declares a budget rides a maps.toml row carrying "
          "`created = true` -- the only kind of row the budget can be spent on",
          f"map {front['map_id']}")

    # WHERE CONTENT BECOMES A NUMBER is where a bad one is refused, and the
    # install path never builds a `datalloc.Stream` to refuse it for us.
    check(deploy.area_reserve({}) == 0 and deploy.area_reserve(front) == budget,
          "`area_reserve` reads the field, and absent is 0 rather than a "
          "refusal -- the field is optional", f"{deploy.area_reserve(front)} B")
    for bad_value in (2048.5, "8192", -512, True):
        got = None
        try:
            deploy.area_reserve({"reserve_bytes": bad_value})
        except deploy.Refused as exc:
            got = str(exc)
        check(got is not None and "areas.toml" in got,
              f"and reserve_bytes={bad_value!r} is REFUSED naming the file to "
              f"edit -- int() would truncate the first silently and the third "
              f"is falsely truthy all the way to a printed line",
              (got or "accepted").splitlines()[0])

    # (g) AND main() THREADS IT. Everything above calls the two writers
    # directly; a budget the command line cannot deliver is a docstring. Asked
    # of the syntax tree with the sabotage that makes it flip, as section 8 does.
    src = open(deploy.__file__, encoding="utf-8").read()

    def calls_with(text, kw):
        fn = next(n for n in ast.walk(ast.parse(text))
                  if isinstance(n, ast.FunctionDef) and n.name == "main")
        return {getattr(n.func, "id", "") for n in ast.walk(fn)
                if isinstance(n, ast.Call)
                and any(k.arg == kw for k in n.keywords)}

    check({"install_partner", "create_chain"} <= calls_with(src, "reserve"),
          "main() passes reserve= to BOTH writers -- the create path chooses "
          "the ceiling and the install path spends it, and a command that "
          "reaches only one leaves the other silently at zero",
          f"{sorted(calls_with(src, 'reserve'))}")
    # AND `created` WITH IT, because the budget is half a gate. `install_partner`
    # defaults it to False -- the pre-WORLDMAPS-W5 behaviour -- so a main() that
    # threads the budget and not the flag reaches the new code path never, and
    # every check above would still be green.
    check("install_partner" in calls_with(src, "created"),
          "and it passes created= to install_partner, the other half of the "
          "gate -- a budget threaded without it grows nothing, and the default "
          "is False for exactly that reason",
          f"{sorted(calls_with(src, 'created'))}")
    check("budget_note" in calls_with(src, "created"),
          "and to budget_note, so the preview is computed from the same two "
          "fields the install decides on")
    # THE SABOTAGE RENAMES rather than deletes: the calls stay parseable and the
    # keyword this asks about is gone, which is what a source that merely
    # mentions the word looks like.
    dropped = src.replace("reserve=reserve", "reserve_off=reserve")
    check(dropped != src and not calls_with(dropped, "reserve"),
          "and taking the keyword back out makes that check go red -- without "
          "this control it would pass on any source that merely mentions the "
          "word", f"{sorted(calls_with(dropped, 'reserve'))}")
    unflagged = src.replace("created=created_row", "created_off=created_row")
    check(unflagged != src and not calls_with(unflagged, "created"),
          "and the same control for created=, which is the keyword whose "
          "absence is silent rather than red",
          f"{sorted(calls_with(unflagged, 'created'))}")


# ---------------------------------------------------------------- section 10
#
# THE FIVE GUARDS WORLDMAPS-W3 LEFT OPEN, and one deferred from W5.
#
# Each of these was a real hole rather than a hypothetical, and three of them
# have the same shape: a rule that is written down in one module and bypassed by
# the path another module actually takes.
#
#   R1  the born-armed guard was LIVE AND UNTESTED -- three lines inside main(),
#       reachable only with a vault, an archive, a donor and a content row.
#   R2  `resolve_or_create`'s fall-through fired identically for OUR created
#       chain and for a retail chain that happens to bind the id, because
#       `map_chain` checks SHAPE and 349 retail maps have that shape. The FIRST
#       version of the fix joined the allocation journal to the archive by the
#       absolute path `datalloc` records, which refused an honest re-deploy on
#       any COPY of the archive -- and archives here are copied whole as a
#       matter of routine. It reads the archive's own bytes now, and each of the
#       four facts it takes as evidence has its own fixture.
#   R3  `datalloc`'s CLI has always refused to write over an existing journal;
#       `create_chain` calls `alloc()` directly and never saw that check.
#   R5  three of `map_chain`'s five raise sites had no fixture at all.
#
# R4 is `contentids.py`'s and is checked in `test_contentids.py` section 6. R6
# is `datwrite`'s typed grow-gate refusal; the writer's half is `test_datwrite`
# section 13 and the JOIN is checked here, in 10e, because the join is deploy's.


def set_row_size(path, row, size):
    """Write a row's `size` field straight into the MFT. -> None.

    Section 10's own writer, spelled out of `struct` for the same reason
    `read_row` is: the question in 10a is whether the guard reads the ARCHIVE,
    and asking `datwrite` to stage the state would put the module under test on
    both sides of it.
    """
    with open(path, "r+b") as fh:
        fh.seek(0x10)
        mft_off = int.from_bytes(fh.read(8), "little")
        fh.seek(mft_off + row * ENTRY_SIZE + 0x08)
        fh.write(struct.pack("<I", size))


def journal_doc(path):
    """An allocation journal as a plain dict, read with `json` alone.

    Section 10's own reader, for the reason `read_row` is section 7's: the
    question in 10b is whether `deploy` reads a journal STRUCTURALLY, and asking
    `datwrite.read_journal` to parse the fixtures that drive that question would
    put a module on both sides of it. An intact journal is one JSON object by
    `read_journal`'s own first branch, so `json.loads` is the whole reader here.
    """
    with open(path, "rb") as fh:
        return json.loads(fh.read().decode("utf-8"))


def journal_edit(doc, offset):
    """The `after` bytes of the one edit at `offset`. -> bytes"""
    hits = [e for e in doc["edits"] if e["offset"] == offset]
    if len(hits) != 1:
        raise AssertionError(f"{len(hits)} edit(s) at {offset:#x}")
    return bytes.fromhex(hits[0]["after"])


def bend_journal(src, dst, offset, blob):
    """Copy a journal with the edit at `offset` rewritten to `blob`. -> dst

    ONE FIELD AT A TIME is the point. `allocation_recorded` names four facts it
    reads out of a journal and three of them had no fixture until this existed
    -- the R5 shape, one module over -- so each is bent on its own, from a
    journal that was real a line earlier, and the CONTROL bends a field back to
    the value it already had to prove the rewrite itself is not what refuses.
    """
    doc = journal_doc(src)
    hits = [e for e in doc["edits"] if e["offset"] == offset]
    if len(hits) != 1:
        raise AssertionError(f"{len(hits)} edit(s) at {offset:#x} in {src}")
    hits[0]["after"] = blob.hex()
    with open(dst, "w", encoding="utf-8") as fh:
        json.dump(doc, fh)
    return dst


def bend_row(src, dst, offset, row_bytes, field, value):
    """`bend_journal`, on one field of one 24-byte MFT row. -> dst"""
    fields = list(struct.unpack("<QIHHII", row_bytes))
    fields[field] = value
    return bend_journal(src, dst, offset, struct.pack("<QIHHII", *fields))


def rename_journal(src, dst, dat):
    """Copy a journal with the archive it NAMES rewritten to `dat`. -> dst

    The other half of 10b's pair: `bend_row` moves what the journal says it
    wrote, this moves where it says it wrote it. Together they let each of
    `allocation_recorded`'s two binding routes be driven with the other one
    unable to answer.
    """
    doc = journal_doc(src)
    doc["dat"] = dat
    with open(dst, "w", encoding="utf-8") as fh:
        json.dump(doc, fh)
    return dst


def poke(path, offset, blob):
    """Write `blob` at `offset`, straight into the file. -> None"""
    with open(path, "r+b") as fh:
        fh.seek(offset)
        fh.write(blob)


def main_fn(text):
    """`deploy.main`'s syntax tree, out of `text`."""
    return next(n for n in ast.walk(ast.parse(text))
                if isinstance(n, ast.FunctionDef) and n.name == "main")


def strings_in(nodes):
    """Every string literal under `nodes`."""
    out = set()
    for n in nodes:
        for x in ast.walk(n):
            if isinstance(x, ast.Constant) and isinstance(x.value, str):
                out.add(x.value)
    return out


def arm_if(text):
    """The INNERMOST `if` in main() whose branches decide the arm. -> If|None

    INNERMOST, and that is not fussiness. `ast.walk` reaches `if args.install:`
    first -- it contains the arm and therefore contains the string -- so the
    first version of this asked every question below about the wrong branch and
    went red naming `args.install`. The arm sits inside that one; the smallest
    candidate is the one whose test is the guard.
    """
    cands = [n for n in ast.walk(main_fn(text))
             if isinstance(n, ast.If) and "rebloat.py" in strings_in([n])]
    return min(cands, key=lambda n: len(list(ast.walk(n)))) if cands else None


def already_from(text):
    """The function names main() computes `already` from. -> set"""
    for node in ast.walk(main_fn(text)):
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == "already"
                   for t in node.targets):
            continue
        return {getattr(c.func, "id", "") or getattr(c.func, "attr", "")
                for c in ast.walk(node.value) if isinstance(c, ast.Call)} | {
                    n.id for n in ast.walk(node.value)
                    if isinstance(n, ast.Name)}
    return set()


def section10():
    """The residual guards: armed, ours, revertible, and shaped like a map."""
    print("\n10. the guards W3 left open: armed, OURS, revertible, a map")
    dim = INSTALL_DIM
    snapped, _w = stx.snap_field(deploy.gen_plaza(dim), dim, dim)
    blob = stx.StrippedTerrain.build(dim, dim, snapped).encode()
    stream, _code, _n = deploy.install_bytes(blob)
    src = open(deploy.__file__, encoding="utf-8").read()

    with tempfile.TemporaryDirectory() as tmp:
        out = spill(tmp, "authored.bin", blob)

        # -- 10a. R1: THE BORN-ARMED GUARD, BOTH WAYS -------------------------
        #
        # `rebloat --arm` refuses a zero-length head, and a created head is born
        # zero-length -- so a create followed by an arm is a dead run. The guard
        # that prevents it reads the ARCHIVE's own `head.size`, deliberately
        # rather than trusting the `create` flag, and until today nothing
        # exercised either answer.
        displaced = os.path.join(tmp, "displaced")
        build_archive(displaced, 4608)
        check(not deploy.head_is_armed(displaced, ROW_HEAD),
              "a DISPLACED retail head is not armed -- it holds a Bloated map, "
              "so the install has to arm it and the client recompiles",
              f"row {ROW_HEAD} holds {read_row(displaced, ROW_HEAD)[1]} B")

        created = os.path.join(tmp, "created")
        build_archive(created, 4608)
        with captured():
            head_row, partner_row = deploy.create_chain(
                created, NEW_FILE_ID, blob, stream, 8, tmp, "r1")
        check(deploy.head_is_armed(created, head_row),
              "and a CREATED head IS armed the moment it exists -- born "
              "zero-length, which is the state `rebloat --arm` refuses to "
              "produce twice and the state the client's re-bloat path keys on",
              f"row {head_row} holds {read_row(created, head_row)[1]} B")

        # AND IT TRACKS THE ROW, NOT THE ORIGIN. This is the case the guard was
        # written for and the reason it asks the archive: a client that has
        # already re-bloated our created head leaves a NON-empty row, and the
        # next deploy must arm it like any other. `create` would still say
        # "created" here and would be answering a different question.
        set_row_size(created, head_row, 300)
        check(not deploy.head_is_armed(created, head_row),
              "and once something writes content into that same created head "
              "the answer FLIPS -- the guard is about the row's current state, "
              "which is what a client re-bloating between two deploys leaves "
              "behind", f"row {head_row} now holds "
                        f"{read_row(created, head_row)[1]} B")
        set_row_size(created, head_row, 0)

        # AND main() ASKS IT, in the branch that decides the arm.
        node = arm_if(src)
        check(node is not None and isinstance(node.test, ast.Name)
              and node.test.id == "already",
              "main()'s arm sits under `if already:` -- one name, computed "
              "once, so the two branches cannot disagree about what was asked",
              ast.dump(node.test)[:60] if node else "no such branch")
        check(node is not None and "rebloat.py" in strings_in(node.orelse)
              and "rebloat.py" not in strings_in(node.body),
              "and `rebloat.py` is reached ONLY from the else -- an armed head "
              "is never armed twice, which would overwrite the first journal "
              "with nothing",
              f"body {sorted(s for s in strings_in(node.body) if '.py' in s)}, "
              f"else {sorted(s for s in strings_in(node.orelse) if '.py' in s)}"
              if node else "no such branch")
        check(already_from(src) == {"head_is_armed", "dat", "head_row"},
              "and `already` comes from head_is_armed(dat, head_row) -- the "
              "ARCHIVE's answer, not `create`'s: 'we just made it empty' is our "
              "word for it and `head.size == 0` is the row's",
              f"{sorted(already_from(src))}")
        # SABOTAGE, both ways, because a syntax-tree check passes on any source
        # that merely mentions the right words.
        trusted = src.replace("already = head_is_armed(dat, head_row)",
                              "already = create")
        check(trusted != src and already_from(trusted) == {"create"},
              "SABOTAGE: pointing it at the `create` flag instead makes that "
              "check go red -- which is the whole difference between asking the "
              "archive and taking our own word for it",
              f"{sorted(already_from(trusted))}")
        flipped = src.replace("        already = head_is_armed(dat, head_row)\n"
                              "        if already:",
                              "        already = head_is_armed(dat, head_row)\n"
                              "        if not already:")
        bad = arm_if(flipped)
        check(flipped != src and bad is not None
              and not isinstance(bad.test, ast.Name),
              "and inverting the test makes the branch check go red too -- "
              "without that control it would pass on any `if` that happens to "
              "contain the string", ast.dump(bad.test)[:60] if bad else "gone")

        # -- 10b. R2: THE CHAIN HAS TO BE PROVABLY OURS -----------------------
        #
        # `map_chain` answers "is this shaped like a map". It cannot answer "did
        # we make it", and the fall-through treated the two as the same
        # question: a `created = true` row whose id binds a genuine ArenaNet map
        # took the ordinary install path and displaced it, with every line of
        # output saying the word "created".
        with Archive(created) as ar:
            rows, create = deploy.resolve_or_create(ar, NEW_FILE_ID, True,
                                                    here=tmp, tag="r1")
        check(not create and rows == (head_row, partner_row,
                                      ((len(stream) + 511) // 512) * 512),
              "THE CASE THIS MUST NOT BREAK: re-deploying our own chain finds "
              "its allocation journal beside the archive and falls through to "
              "install, reservation and all", f"{rows}")

        why = ""
        try:
            with Archive(created) as ar:
                deploy.resolve_or_create(ar, NEW_FILE_ID, True)
        except deploy.Refused as exc:
            why = str(exc)
        check("ALREADY BINDS" in why and f"head row {head_row}" in why
              and f"partner row {partner_row}" in why,
              "and with nowhere to look for that journal it REFUSES, naming "
              "what is actually there -- the rows, their flags and their sizes, "
              "because the remedy depends on what a person makes of them",
              why.splitlines()[0][:110] if why else "accepted")
        ordered = ("_alloc.json" in why and "fresh id" in why
                   and why.index("_alloc.json") < why.index("fresh id"))
        check(ordered and "the journal travels with the archive" in why.lower(),
              "and it names the RECOVERABLE remedy FIRST -- bring the journal "
              "to the archive, which is where a whole-file copy leaves it -- "
              "keeping `allocate under a fresh id` as the last resort it "
              "actually is: that line is wrong advice for a chain that is "
              "provably ours, and a wrong remedy in a refusal is what an "
              "operator does at 2am",
              why.splitlines()[-1][:110] if why else "accepted")

        # THE RETAIL CHAIN. This is the failure itself: a plain fixture holding
        # ArenaNet's own map 143 under its own id, and a content row claiming to
        # have created it. Shape-identical to ours; provenance opposite.
        retail = os.path.join(tmp, "retail")
        build_archive(retail, 4608, file_id=NEW_FILE_ID)
        why = ""
        try:
            with Archive(retail) as ar:
                deploy.resolve_or_create(ar, NEW_FILE_ID, True,
                                         here=tmp, tag="r1")
        except deploy.Refused as exc:
            why = str(exc)
        check("ALREADY BINDS" in why and "349 retail maps" in why,
              "a chain we did NOT make is refused even with a journal for this "
              "area in the directory -- the journal names an archive, an id and "
              "two rows, and this one names none of them",
              why.splitlines()[0][:110] if why else "accepted")
        check(deploy.created_evidence(retail, tmp, "r1", NEW_FILE_ID,
                                      ROW_HEAD, ROW_PARTNER) is None
              and deploy.created_evidence(created, tmp, "r1", NEW_FILE_ID,
                                          head_row, partner_row) is not None,
              "-- and the evidence check is what separates them: the SAME "
              "journal is evidence about one archive and not the other",
              f"{os.path.basename(deploy.alloc_journal_path(tmp, 'r1'))}")
        # AND IT IS READ STRUCTURALLY, not as prose. Each of the facts the
        # journal carries is asked for on its own.
        j = deploy.alloc_journal_path(tmp, "r1")
        check(deploy.allocation_recorded(j, created, NEW_FILE_ID, head_row,
                                         partner_row)
              and not deploy.allocation_recorded(j, created, NEW_FILE_ID + 1,
                                                 head_row, partner_row)
              and not deploy.allocation_recorded(j, created, NEW_FILE_ID,
                                                 head_row + 1, partner_row)
              and not deploy.allocation_recorded(j, created, NEW_FILE_ID,
                                                 head_row, partner_row + 1)
              and not deploy.allocation_recorded(j, retail, NEW_FILE_ID,
                                                 head_row, partner_row),
              "the journal is evidence for exactly ONE (archive, id, head, "
              "partner) -- change any one of the four and it stops being "
              "evidence, which is what makes it a fingerprint rather than a "
              "file that exists")

        # THE ARCHIVE IS ASKED, NOT ITS FILENAME -- and this is the fix a
        # skeptic's probe forced. `datalloc` records an ABSOLUTE path, and
        # archives here are copied WHOLE as a matter of routine: `overlay.py`
        # copies manifest archives with `shutil.copyfile`, `make_run_dir.py`
        # stages one per run directory, and RUNBOOK's own procedure copies
        # `run-live\<build>\Gw.dat` over `run\<build>\Gw.dat`. The first version
        # of this guard joined on that path, so an honest re-deploy of OUR OWN
        # chain on a copy -- journal beside it, describing the copy byte-exactly
        # -- was refused, and the refusal's closing line told the operator to
        # allocate under a fresh id. Wrong advice, in the one state where the
        # chain is provably ours.
        doc = journal_doc(j)
        named = struct.pack("<II", NEW_FILE_ID, head_row)
        id_off = next(e["offset"] for e in doc["edits"]
                      if bytes.fromhex(e["after"]) == named)
        copied_dir = os.path.join(tmp, "copied")
        os.makedirs(copied_dir)
        copied = os.path.join(copied_dir, "Gw.dat")
        shutil.copyfile(created, copied)
        shutil.copyfile(j, deploy.alloc_journal_path(copied_dir, "r1"))
        # CAUGHT rather than allowed to propagate: a regression here is a
        # refusal, and a refusal that escapes the section is a traceback instead
        # of a named FAIL -- which is the shape this whole pass is against.
        rows_c, create_c, denied = None, None, ""
        try:
            with Archive(copied) as ar:
                rows_c, create_c = deploy.resolve_or_create(
                    ar, NEW_FILE_ID, True, here=copied_dir, tag="r1")
        except deploy.Refused as exc:
            denied = str(exc).splitlines()[0]
        check(not denied and not create_c and rows_c == rows
              and os.path.normcase(os.path.abspath(doc["dat"]))
              != os.path.normcase(os.path.abspath(copied)),
              "a WHOLE-FILE COPY of the archive, with its journal beside it, "
              "falls through to install exactly as the original does -- and the "
              "journal names the path it was ALLOCATED at, which this copy is "
              "not, so what joined the two is the archive's own bytes",
              denied[:110] if denied else
              f"{rows_c} at ...{os.sep}"
              f"{os.path.basename(copied_dir)}{os.sep}"
              f"{os.path.basename(copied)}")

        # AND IT IS A BYTE CHECK, not merely "some archive other than the named
        # one". The same copy with the file-id record rebound one row over no
        # longer carries what the allocation wrote, and stops being ours.
        tampered = os.path.join(tmp, "tampered")
        shutil.copyfile(created, tampered)
        poke(tampered, id_off, struct.pack("<II", NEW_FILE_ID, head_row + 1))
        check(deploy.archive_carries(copied, id_off, named)
              and not deploy.archive_carries(tampered, id_off, named)
              and not deploy.allocation_recorded(j, tampered, NEW_FILE_ID,
                                                 head_row, partner_row),
              "and an archive at neither path which does NOT carry that record "
              "is not ours: the file-id record going live is the fingerprint, "
              "so a copy with it rebound to another row is refused while the "
              "byte-identical copy is not",
              f"record at {id_off:#x} is {named.hex()}")

        # AND THE PATH ROUTE IS STILL LOAD-BEARING, which is why it is kept as
        # the FIRST route rather than replaced. The client rewrites the file-id
        # table during ordinary play, so an archive that never moved can stop
        # carrying that record at the offset the allocation put it -- and there
        # the journal's own name for the file is the only join left.
        settled = os.path.join(tmp, "settled")
        shutil.copyfile(created, settled)
        poke(settled, id_off, bytes(len(named)))
        check(not deploy.archive_carries(settled, id_off, named)
              and deploy.allocation_recorded(
                  rename_journal(j, os.path.join(tmp, "j_settled.json"),
                                 settled),
                  settled, NEW_FILE_ID, head_row, partner_row),
              "an archive that STAYED PUT while the id table moved under it no "
              "longer carries the record, and its journal still NAMES it -- so "
              "the two routes cover different failures and neither is "
              "vestigial",
              f"record at {id_off:#x} zeroed, journal names this file")

        # THE THREE CONJUNCTS THAT DESCRIBE THE ROWS, one fixture each. This is
        # R5's own shape one module over: `allocation_recorded` names four facts
        # it reads out of the journal, and until now only the file-id record and
        # the archive were exercised -- so a mutation sweep could delete the
        # head's flags test, the nextStream test or the partner's flags test and
        # this section stayed green. Each is bent ON ITS OWN, out of a journal
        # that was real a line earlier.
        mft = doc["mft_offset"]
        head_off = mft + head_row * ENTRY_SIZE
        partner_off = mft + partner_row * ENTRY_SIZE
        head_after = journal_edit(doc, head_off)
        partner_after = journal_edit(doc, partner_off)
        check(not deploy.allocation_recorded(
                  bend_row(j, os.path.join(tmp, "j_headflags.json"), head_off,
                           head_after, 3, PLAIN_FILE_FLAGS),
                  created, NEW_FILE_ID, head_row, partner_row),
              "a journal whose HEAD row goes down with flags 3 rather than 259 "
              "records somebody allocating a plain file, not a map, and is not "
              "evidence that this chain is ours",
              f"row {head_row} flags {MAP_HEAD_FLAGS} -> {PLAIN_FILE_FLAGS}")
        check(not deploy.allocation_recorded(
                  bend_row(j, os.path.join(tmp, "j_nextstream.json"), head_off,
                           head_after, 4, partner_row + 1),
                  created, NEW_FILE_ID, head_row, partner_row),
              "a journal whose head is chained to a DIFFERENT partner is not "
              "evidence for THIS pair -- nextStream is the only field that "
              "makes two rows one map, and the pair is what the caller is about "
              "to write into",
              f"row {head_row} nextStream {partner_row} -> {partner_row + 1}")
        check(not deploy.allocation_recorded(
                  bend_row(j, os.path.join(tmp, "j_partnerflags.json"),
                           partner_off, partner_after, 3, PLAIN_FILE_FLAGS),
                  created, NEW_FILE_ID, head_row, partner_row),
              "and a journal whose PARTNER row goes down with flags 3 rather "
              "than 1 is not evidence either -- three fields, three fixtures, "
              "because an unexercised conjunct is a conjunct that can be "
              "deleted",
              f"row {partner_row} flags {MAP_PARTNER_FLAGS} -> "
              f"{PLAIN_FILE_FLAGS}")
        check(deploy.allocation_recorded(
                  bend_row(j, os.path.join(tmp, "j_same.json"), head_off,
                           head_after, 3, MAP_HEAD_FLAGS),
                  created, NEW_FILE_ID, head_row, partner_row),
              "CONTROL: the same journal rewritten with the head's flags put "
              "back to the value they already had is still evidence -- so the "
              "three above refuse the BENT FIELD rather than refusing any "
              "journal this test wrote",
              f"row {head_row} flags {MAP_HEAD_FLAGS}, unchanged")

        # CONTROL: a row that does NOT claim to be created is untouched by any
        # of this. The displacement path is the one every area but frontier
        # takes, and it must read exactly as it did before today.
        with Archive(retail) as ar:
            rows_r, create_r = deploy.resolve_or_create(ar, NEW_FILE_ID, False)
        check(not create_r and rows_r[0] == ROW_HEAD
              and rows_r[1] == ROW_PARTNER,
              "CONTROL: the same chain, on a row without `created = true`, "
              "resolves with no evidence asked for at all -- displacement is "
              "what this command has always done and the guard is only about "
              "the claim to have made the file", f"{rows_r}")

        # -- 10c. R3: THE ALLOCATION JOURNAL IS NOT OVERWRITTEN ---------------
        #
        # `datalloc`'s CLI has refused this since it was written and deploy went
        # around it: a second create with the same area name truncated the first
        # run's journal at its first record, then printed the file it had just
        # destroyed as the way back.
        with open(j, "rb") as fh:
            journal_before = fh.read()
        second = os.path.join(tmp, "second")
        build_archive(second, 4608)
        with open(second, "rb") as fh:
            archive_before = fh.read()
        why = ""
        try:
            with captured():
                deploy.create_chain(second, NEW_FILE_ID, blob, stream, 8,
                                    tmp, "r1")
        except deploy.Refused as exc:
            why = str(exc)
        with open(j, "rb") as fh:
            journal_after = fh.read()
        with open(second, "rb") as fh:
            archive_after = fh.read()
        check("already exists" in why and "only way back" in why,
              "a create whose journal file already exists is REFUSED, quoting "
              "datalloc's own reasoning rather than paraphrasing it",
              why.splitlines()[0][:110] if why else "accepted")
        check(journal_after == journal_before,
              "and the first run's journal is byte-for-byte intact -- "
              "overwriting it would leave its edits applied forever while a "
              "later --revert of the new file reported success",
              f"{len(journal_after)} B, unchanged")
        check(archive_after == archive_before,
              "and nothing was allocated: the refusal lands before the spill, "
              "before the plan and before the first byte",
              f"{len(archive_after)} B, unchanged")
        check(not os.path.exists(os.path.join(tmp, "r1.c8.bin.tmp"))
              and deploy.alloc_journal_path("d", "a")
              == os.path.join("d", "a_alloc.json"),
              "and the path both sides talk about is ONE expression -- the "
              "create path refuses it and the install path reads it, so they "
              "have to mean the same file", deploy.alloc_journal_path("d", "a"))

        # -- 10d. R5: map_chain's THREE UNEXERCISED REFUSALS ------------------
        #
        # Five raise sites, two of them driven by section 8. These three have
        # had no fixture at all, so a regression in any of them would go
        # undetected by a green suite -- and each one is a shape that would
        # otherwise reach `resolve_rows`, where `MapIndex.partner` reads
        # `by_row.get(nextStream)` and row 0 is a real MFT row.
        def refusal(name, extra):
            p = os.path.join(tmp, name)
            build_archive(p, 4608, extra_rows=extra)
            try:
                with Archive(p) as ar:
                    deploy.map_chain(ar, FIXTURE_FILE_ID)
            except deploy.Refused as exc:
                return str(exc)
            return ""

        head_at = HEAD_BLOCK * BLOCK
        why = refusal("nonext", {ROW_HEAD: (head_at, HEAD_SIZE, 0,
                                            MAP_HEAD_FLAGS, 0)})
        check("nextStream is 0" in why and "TWO rows and this is one" in why,
              "a map head whose nextStream is 0 is REFUSED -- the chain "
              "terminates there, and `MapIndex.partner` would resolve row 0, "
              "which is the file header rather than None",
              why.splitlines()[0][:110] if why else "accepted")
        why = refusal("gone", {ROW_HEAD: (head_at, HEAD_SIZE, 0,
                                          MAP_HEAD_FLAGS, ENTRY_COUNT + 4)})
        check("absent from this archive's MFT" in why
              and f"row {ENTRY_COUNT + 4}" in why,
              "a head chained to a row this MFT does not have is REFUSED, "
              "naming the row it named", why.splitlines()[0][:110]
              if why else "accepted")
        why = refusal("wrongflags",
                      {ROW_PARTNER: (PARTNER_BLOCK * BLOCK, 4608, 0,
                                     PLAIN_FILE_FLAGS, 0)})
        check(f"0x{PLAIN_FILE_FLAGS:04X}" in why and "bijection" in why,
              "and a partner carrying the wrong flags is REFUSED naming both "
              "flag words -- MEASURED corpus-wide the nextStream link map is a "
              "bijection and every Bloated head chains to one stream-0 row",
              why.splitlines()[0][:110] if why else "accepted")
        # CONTROL: the unmodified fixture is a chain, so the three above are
        # refusing the DEVIATION rather than refusing everything.
        p = os.path.join(tmp, "control")
        build_archive(p, 4608)
        with Archive(p) as ar:
            got = deploy.map_chain(ar, FIXTURE_FILE_ID)
        check(got is not None and got[0].index == ROW_HEAD
              and got[1].index == ROW_PARTNER,
              "CONTROL: the same fixture untouched resolves as a chain -- one "
              "field apart from each of the three above",
              f"head {got[0].index}, partner {got[1].index}")

    # -- 10e. R6: THE GROW-GATE JOIN IS TYPED, WITH THE WORDING AS FALLBACK ---
    #
    # `install_partner` may relocate around a grow the GATE refused and must
    # never relocate around anything else -- a declaration fault turned into a
    # quiet datmove is the failure. It told the two apart by looking for four
    # fixed fragments of datwrite's sentences, so the day one was reworded every
    # claimant conflict became a refused install for a reason with nothing to do
    # with the archive. datwrite names its own refusals now.
    token = f"  {datwrite.GROW_GATE_TOKEN} condition=claimants"
    check(deploy.grow_gate_refusal(token) is not None,
          "a writer's output carrying ONLY the token -- no sentence this file "
          "knows -- is recognised as a gate refusal: the join is the token now, "
          "not the prose", deploy.grow_gate_refusal(token))
    reworded = ("REFUSED: row 5 cannot take those blocks back, some other row "
                "has them.\n" + token)
    check(deploy.grow_gate_refusal(reworded) is not None,
          "so datwrite REWORDING condition 1 no longer turns a claimant "
          "conflict into a refused install -- which is what the old four-marker "
          "join did, silently and in the safe direction",
          deploy.grow_gate_refusal(reworded))
    old = "row 5 needs to grow ... [0x600, 0x800) is CLAIMED by row 6."
    check(deploy.grow_gate_refusal(old) is not None,
          "and an OLDER datwrite that prints no token at all is still "
          "recognised by its sentence -- the fallback is documented, not "
          "vestigial: a vault copy or a bisect is exactly where it bites",
          deploy.grow_gate_refusal(old))
    check(deploy.grow_gate_refusal(
              "row 5 reserves 1024 bytes and the new payload is 1148") is None
          and deploy.grow_gate_refusal(
              "REFUSED: will not write row 5 as compression 8") is None,
          "and an ORDINARY refusal is still not a gate refusal, with or "
          "without a token in the file -- that is the direction where a wrong "
          "answer relocates around a declaration fault")
    said = deploy.grow_gate_refusal(
        "row 5 is CLAIMED by row 6.\n" + token)
    check("CLAIMED by row 6" in said,
          "and when both are present the HUMAN sentence is what comes back: "
          "the token is the decision and the sentence is the report",
          said)
    check(datwrite.GROW_GATE_TOKEN not in "".join(deploy.GROW_GATE_MARKERS)
          and len(deploy.GROW_GATE_MARKERS) == 4
          and len(datwrite.GROW_GATE_CONDITIONS) == 4,
          "and the fallback list still holds one fragment per condition -- four "
          "sentences, four conditions, so a fifth condition cannot be added to "
          "datwrite without this file noticing",
          f"{len(deploy.GROW_GATE_MARKERS)} marker(s), "
          f"{len(datwrite.GROW_GATE_CONDITIONS)} condition(s)")


# --------------------------------------------------------------- section 11
#
# WORLDMAPS-W8: `readback`'s optional-chunk loop, in the direction it never ran.
#
# THE DEFECT THIS SECTION IS ABOUT WAS A CHECK THAT COULD NOT FIRE. The loop
# over the optional payload chunks read `want = staged.find(scid)` and then
# `if want is None: continue`, so an area that declares `environment = false`
# got its environment assertion SKIPPED rather than INVERTED. W8 installed
# exactly that map, `readback` printed a clean 6/6, and it had said nothing at
# all about the environment -- while the fact the whole arm turned on, that the
# client's COMPILED map carries no `0x20000009` either and so had no donor,
# global or cached environment to fall back on, was recovered by hand out of the
# allocation journal after the fact. Absence is what makes "we removed X and
# nothing changed" mean "X was not the cause"; unasserted, the null is about an
# instrument that never looked.
#
# THE ARM THAT MATTERS IS THE SABOTAGE. A compiled map that DOES carry the chunk
# our staged map omitted has to go red, because that is the only arrangement in
# which the omission was not real -- and before the fix it was indistinguishable
# from success: this section's (d) returned `bad == []` against the old code,
# which is the same clean verdict W8 read as evidence.
#
# NO VAULT, NO CLIENT, and no compiler: the "compiled" map is one this file
# assembles, so what each arm carries is a fact about the rule rather than about
# whichever retail map was to hand. The fixture's compiled head holds a pathing
# chunk (so the re-compiled and spawn rows are real) plus whichever optional
# chunks the arm is about, and nothing else -- the height-field and prop rows
# are about chunks a compiler always emits and are a different subject, still
# conditional in `readback` and deliberately not this section's business.

READBACK_DIM = 32
READBACK_SEED = (1536.0, 1536.0)     # dead centre of the one trapezoid below
READBACK_ENV = bytes(range(64)) * 3          # 192 B, stands in for the 639 B
READBACK_SOUND = bytes(range(48))[::-1] * 2  # 96 B, stands in for the 89 B


def readback_area():
    """The three keys `readback` reads out of an area row. Nothing else."""
    return {"seed_x": READBACK_SEED[0], "seed_y": READBACK_SEED[1],
            "dims": READBACK_DIM}


def opaque(chunk_id, payload):
    return mfile.Chunk(chunk_id, bytes(payload), mfile.FORM_OPAQUE)


def staged_map(env=None, sound=None):
    """A Stripped map carrying real terrain and prop chunks, optionals by arm.

    Terrain and props are REAL -- `readback` decodes both unconditionally
    (`stx.StrippedTerrain` for the height field it compares, `StrippedProps` for
    the count it expects) and a stand-in would raise before reaching the loop
    under test.
    """
    snapped, _worst = stx.snap_block(deploy.GENERATORS["flat"](READBACK_DIM))
    chunks = [opaque(sb.HEADER, bytes(8)),
              opaque(sb.PROPS, StrippedProps.minimal().encode()),
              opaque(sb.TERRAIN,
                     stx.StrippedTerrain.build(READBACK_DIM, READBACK_DIM,
                                               snapped).encode())]
    if env is not None:
        chunks.append(opaque(sb.ENV, env))
    if sound is not None:
        chunks.append(opaque(sb.SOUND, sound))
    return mfile.MapFile(chunks=chunks).encode()


def compiled_map(env=None, sound=None):
    """What we pretend the client's compiler produced: a path chunk, optionals.

    One plane, one trapezoid spanning the whole 32x32 map, so the two rows that
    are about the mesh (`the client re-compiled the map`, and the spawn landing
    in exactly one trapezoid) are answered by real geometry rather than skipped.
    A skipped row here would put this section in the same shape as the defect it
    is about.
    """
    trap = pathmap.Trapezoid(
        0, 0, y_top=3072.0, y_bottom=0.0, x_top_left=0.0, x_top_right=3072.0,
        x_bottom_left=0.0, x_bottom_right=3072.0,
        neighbours=(pathmap.NO_NEIGHBOUR,) * 4)
    plane = pathchunk.Plane(index=0, poly=[(0.0, 0.0)], edges=[(0.0, 0.0)],
                            traps=[trap], root_type=2, sinks=[0])
    chunks = [opaque(0x20000008, pathchunk.PathChunk(
        boundary=[(0.0, 0.0), (3072.0, 3072.0)], planes=[plane], plane_map=[0],
        obstacles=pathchunk.Obstacles(3, 3)).encode())]
    if env is not None:
        chunks.append(opaque(0x20000009, env))
    if sound is not None:
        chunks.append(opaque(0x20000012, sound))
    return mfile.MapFile(chunks=chunks).encode()


def head_only_archive(path, blob):
    """An archive whose one map head IS `blob`, under `FIXTURE_FILE_ID`.

    NOT `build_archive`. That fixture's head is a fixed 300-byte pattern in one
    block with the partner in the next, which is right for section 7's subject
    (which verb ran, and what the row was marked) and wrong for this one: here
    the head's BYTES are the subject and a compiled map does not fit in a block.
    No partner row either, and that is a claim rather than a shortcut --
    `readback` resolves the file id to a row, reads THAT row and decodes it, so
    a fixture with a chain would be carrying evidence the code never consults.
    """
    head_block = 2
    mft_block = head_block + -(-len(blob) // BLOCK)
    mft_off, mft_size = mft_block * BLOCK, ENTRY_COUNT * ENTRY_SIZE
    buf = bytearray(bytes([SLACK]) * (mft_off + mft_size))
    buf[BLOCK:BLOCK + 8] = struct.pack("<II", FIXTURE_FILE_ID, ROW_HEAD)
    buf[head_block * BLOCK:head_block * BLOCK + len(blob)] = blob

    head = bytearray(32)
    head[0:4] = FILE_MAGIC
    struct.pack_into("<I", head, 0x04, 32)
    struct.pack_into("<I", head, 0x08, BLOCK)
    struct.pack_into("<Q", head, 0x10, mft_off)
    struct.pack_into("<I", head, 0x18, mft_size)
    struct.pack_into("<I", head, 0x0C, binascii.crc32(bytes(head[:12])))
    buf[0:32] = head

    rows = {ROW_HEADER:  (0, 32, 0, 3, 0),
            ROW_IDTABLE: (BLOCK, 8, 0, 3, 0),
            ROW_SELF:    (mft_off, mft_size, 0, 3, 0),
            ROW_HEAD:    (head_block * BLOCK, len(blob), 0, MAP_HEAD_FLAGS, 0)}
    mft = bytearray(mft_size)
    mft[0:4] = MFT_MAGIC
    struct.pack_into("<I", mft, 0x0C, ENTRY_COUNT)
    for row, (off, size, comp, flags, nxt) in rows.items():
        crc = 0 if row in (ROW_HEADER, ROW_SELF) else binascii.crc32(
            bytes(buf[off:off + size]))
        struct.pack_into("<QIHHII", mft, row * ENTRY_SIZE,
                         off, size, comp, flags, nxt, crc)
    struct.pack_into("<I", mft, ROW_SELF * ENTRY_SIZE + 20, self_crc(mft))
    buf[mft_off:mft_off + mft_size] = mft
    with open(path, "wb") as fh:
        fh.write(bytes(buf))


def run_readback(tmp, name, staged_blob, compiled_blob):
    """`deploy.readback` against a one-arm archive. -> (rows, bad)."""
    dat = os.path.join(tmp, f"{name}.dat")
    head_only_archive(dat, compiled_blob)
    return deploy.readback(dat, FIXTURE_FILE_ID, staged_blob, readback_area())


def verdict_of(rows, needle):
    """(PASS/FAIL, the row with its own marker stripped) for the row `needle` names.

    Asked by SUBSTRING and required to match exactly once, because the arms
    below differ in which rows exist at all -- an arm that produced no
    environment row would otherwise be read as an arm that produced a passing
    one, which is precisely the defect under test wearing a different hat.

    The marker comes OFF the returned body deliberately. These rows go into
    `check`'s detail, and a detail carrying its own `[PASS]` would both read as
    a second verdict on the same line and break the floor comment's grep
    arithmetic, which counts markers.
    """
    hit = [r for r in rows if needle in r]
    if len(hit) != 1:
        return f"{len(hit)} rows", f"{len(hit)} matching row(s)"
    got = "PASS" if "[PASS]" in hit[0] else "FAIL"
    return got, hit[0].replace(f"[{got}]", "", 1).strip()


def section11():
    """The optional-chunk loop, present and absent, with the sabotage."""
    print("\n11. readback asserts an optional chunk's ABSENCE, not just its "
          "presence")
    tmp = tempfile.mkdtemp()
    try:
        # (a) PRESENT, AND CARRIED. The assertion that already existed, run
        # unchanged, so the fix is shown not to have cost the case it had.
        rows, bad = run_readback(tmp, "carried",
                                 staged_map(READBACK_ENV, READBACK_SOUND),
                                 compiled_map(READBACK_ENV, READBACK_SOUND))
        got, line = verdict_of(rows, "our environment payload carried VERBATIM")
        check(got == "PASS" and not bad,
              "an authored environment the compiled map carries verbatim still "
              "PASSes, and the whole readback is clean",
              f"{got}; bad={bad}")
        n_present = len(rows)

        # (b) PRESENT AND DIFFERENT. The other half of the existing assertion:
        # one byte off the end is a compiler that did not carry ours.
        rows, bad = run_readback(tmp, "bent",
                                 staged_map(READBACK_ENV, READBACK_SOUND),
                                 compiled_map(READBACK_ENV[:-1], READBACK_SOUND))
        got, _line = verdict_of(rows, "our environment payload carried VERBATIM")
        check(got == "FAIL" and bad == ["our environment payload carried "
                                        "VERBATIM"],
              "and a compiled environment one byte short of ours goes red, "
              "naming that row and only that row", f"{got}; bad={bad}")

        # (c) ABSENT ON BOTH SIDES -- W8's arm B, and the row it never printed.
        # The clean verdict is asserted TOGETHER WITH the row's existence: W8's
        # readback was clean too, and clean-with-nothing-said is the failure.
        rows, bad = run_readback(tmp, "absent",
                                 staged_map(None, READBACK_SOUND),
                                 compiled_map(None, READBACK_SOUND))
        got, line = verdict_of(rows, "our map carries no environment")
        check(got == "PASS" and not bad,
              "a map that authors NO environment gets a PASSing row saying the "
              "compiled map carries none either -- W8's arm B, which used to "
              "print nothing here", line)
        check("compiled map carries none either" in line
              and "no donor, global or cached" in line,
              "and the row SAYS what the absence buys: no donor, global or "
              "cached environment for the compiler to fall back on, which is "
              "what licenses reading the arm's null as being about our change")
        check(len(rows) == n_present,
              "and the absent arm prints as many rows as the present one -- "
              "the skip is gone, so a reader cannot mistake an unasserted "
              "chunk for an asserted one", f"{len(rows)} vs {n_present}")

        # (d) THE SABOTAGE. We authored no environment and the compiled map has
        # one anyway. MEASURED against the pre-fix loop: this arm returned
        # `bad == []`, indistinguishable from (c).
        rows, bad = run_readback(tmp, "smuggled",
                                 staged_map(None, READBACK_SOUND),
                                 compiled_map(READBACK_ENV, READBACK_SOUND))
        got, line = verdict_of(rows, "our map carries no environment")
        check(got == "FAIL" and bad == ["our map carries no environment, and "
                                        "the compiled map carries none either"],
              "but a compiled map that carries an environment we never authored "
              "goes RED -- the arrangement in which the omission was not real, "
              "and the one the old loop could not tell from success",
              f"{got}; bad={bad}")
        check(f"{len(READBACK_ENV)} B" in line,
              "and the failing row prices the smuggled chunk, so the log says "
              "how much environment came from somewhere we did not author",
              line)

        # (e) SOUND, BOTH WAYS. The loop has two entries and only one has been
        # driven above; a fix that reached `environment` by name would pass
        # everything so far. This is the same pair against 0x20000012.
        rows, bad = run_readback(tmp, "mute",
                                 staged_map(READBACK_ENV, None),
                                 compiled_map(READBACK_ENV, None))
        got, line = verdict_of(rows, "our map carries no sound")
        check(got == "PASS" and not bad,
              "sound is asserted the same way when the area declares none",
              line)
        rows, bad = run_readback(tmp, "dubbed",
                                 staged_map(READBACK_ENV, None),
                                 compiled_map(READBACK_ENV, READBACK_SOUND))
        got, _line = verdict_of(rows, "our map carries no sound")
        check(got == "FAIL" and len(bad) == 1,
              "and a compiled map with a sound chunk we did not author goes red "
              "too -- the inversion is the LOOP's, not one chunk id's",
              f"{got}; bad={bad}")

        # (f) THE LOOP ITSELF, at the source. Both entries of the tuple reach
        # the same two calls, so a third optional chunk added to it inherits
        # both directions rather than only the one somebody remembered.
        fn = next(n for n in ast.walk(ast.parse(
                      open(deploy.__file__, encoding="utf-8").read()))
                  if isinstance(n, ast.FunctionDef) and n.name == "readback")
        loops = [n for n in ast.walk(fn) if isinstance(n, ast.For)
                 and any(isinstance(c, ast.Constant) and c.value == 0x20000009
                         for c in ast.walk(n.iter))]
        bare = [n for n in ast.walk(loops[0]) if isinstance(n, ast.Continue)] \
            if loops else []
        guarded = [n for n in ast.walk(loops[0])
                   if isinstance(n, ast.Call)
                   and getattr(n.func, "id", "") == "row_"] if loops else []
        check(len(loops) == 1 and len(guarded) == 2,
              "the optional-chunk loop reaches row_() on BOTH paths, so a chunk "
              "id added to its tuple is asserted in both directions rather than "
              "in whichever one somebody remembered",
              f"{len(loops)} loop(s), {len(guarded)} row_() call(s), "
              f"{len(bare)} continue(s)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------- section 12
#
# THE DEFECT THIS SECTION IS ABOUT WAS A FAILURE WEARING THE WRONG NAME. When
# `--install` arms a head to zero length and the client never re-bloats it, the
# head stays 0 B. `readback` handed those 0 bytes straight to
# `mapfile.MapFile.decode`, which raised `ValueError: ffna file is 0 bytes,
# shorter than its 5-byte header` -- a traceback out of a decoder three layers
# down, naming neither the map nor the cause. On 2026-08-21 (WORLDMAPS-W12)
# that is exactly what a launch collision produced: another session held the
# harness ports, this session's harness never bound, `harness rc 1` scrolled
# past, and the run ENDED on a stack trace about a file header. An empty head
# is not a corrupt file -- it is the single most likely outcome of a launch
# that did not happen, and it is a RESULT: the compiler never ran.
#
# Both directions are asserted, because a guard that fires on everything is the
# same defect from the other side: (a) the armed head goes red with a row that
# names the file id and points at the harness, and (b) a head the client DID
# re-bloat still produces the full readback -- the early return does not
# swallow the healthy path.


def section12():
    """An un-recompiled head is a named result, not a decoder traceback."""
    print("\n12. an armed head that was never re-bloated FAILS by name")
    tmp = tempfile.mkdtemp()
    try:
        # (a) THE ARMED HEAD. Zero bytes, exactly as --install left it.
        rows, bad = run_readback(tmp, "armed",
                                 staged_map(READBACK_ENV, READBACK_SOUND),
                                 b"")
        check(bool(bad) and len(rows) == 1,
              "a 0-byte head produces exactly one row and a non-empty `bad`, "
              "rather than raising out of the FFNA decoder",
              f"{len(rows)} row(s); bad={bad}")
        got, line = verdict_of(rows, "never re-bloated")
        check(got == "FAIL",
              "and that row is a FAIL naming the thing that did not happen",
              line)
        check(f"{FIXTURE_FILE_ID:#08x}" in line and "0 B" in line,
              "the row names the FILE ID and the zero length, so a reader "
              "knows which map, and what state it was left in", line)
        check("harness rc" in line and "Gw.log" in line,
              "and it points at the harness rc and Gw.log -- the two places "
              "that can say WHY the client never got there, which is the "
              "information the traceback replaced", line)

        # (b) THE CONTROL, and it is the half that matters. A guard that
        # reddens a healthy readback would be worse than the traceback it
        # replaced, and nothing in (a) can tell the difference.
        rows, bad = run_readback(tmp, "rebloated",
                                 staged_map(READBACK_ENV, READBACK_SOUND),
                                 compiled_map(READBACK_ENV, READBACK_SOUND))
        check(not bad and len(rows) > 1,
              "CONTROL: a head the client DID re-bloat still produces the "
              "whole readback, clean -- the early return is scoped to the "
              "empty case and nothing else", f"{len(rows)} row(s); bad={bad}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------- section 13
#
# THREE HOLES THAT COMPOSED INTO ONE FAILURE: `serve_run` could reach a verdict
# from ANOTHER SESSION'S log, about a DIFFERENT MAP, after a harness that
# FAILED. None of the three was hypothetical on 2026-08-21 (WORLDMAPS-W13
# recon), when THREE worktrees were driving this harness at once:
#
#   * `vault/captures/harness/` is shared by every session on the machine, and
#     `newest_harness_log` took the newest `gamesrv.log` by MTIME across the
#     whole directory. MEASURED that day: of the 14 most recent captures, 12
#     belonged to other trees, and one of them (20260821T125215) was 75 seconds
#     NEWER than this session's last run. A `--serve` issued right after would
#     have scored its verdict off a peer's log.
#   * `fid` from the navmesh line reached only the note STRING -- `hits[0]` was
#     read and its map id never compared to ours. The biome donor 0x1B97D is
#     pre-warmed in every run of this harness, so a foreign line was always
#     available to match against.
#   * `rc` from `launch` likewise appeared only inside f-strings, so a harness
#     that failed outright still scored PASS if a log with a matching count
#     turned up.
#
# The attribution half is tested against REAL FILES rather than a stub, because
# a stub cannot get attribution wrong and a test that cannot fail is not a
# test. `authsrv.py` prints `source:  <its own directory>`, which names the
# worktree; no two worktrees share one.


def section13():
    """serve_run must not score another tree's run, another map, or a failure."""
    print("\n13. the serve verdict is about THIS run, THIS map, and a harness "
          "that worked")
    tmp = tempfile.mkdtemp()
    try:
        # (a) log_source reads the line authsrv actually prints.
        root = os.path.join(tmp, "captures", "harness")
        mine_src = deploy.harness_source_dir()
        theirs = os.path.normcase(os.path.abspath(
            os.path.join(tmp, "elsewhere", "toolkit", "authsrv")))

        def capture(name, src, mtime):
            d = os.path.join(root, name)
            os.makedirs(d, exist_ok=True)
            log = os.path.join(d, "gamesrv.log")
            with open(log, "w", encoding="utf-8") as fh:
                fh.write("Rurik AuthSrv\nsource:    %s\n%s\n" % (src, MESH_LINE))
            os.utime(log, (mtime, mtime))
            return log

        ours_log = capture("20260101T000100", mine_src, 1000)
        theirs_log = capture("20260101T000200", theirs, 2000)   # NEWER

        check(deploy.log_source(ours_log) == mine_src,
              "log_source reads the `source:` line authsrv prints and "
              "normalises it", deploy.log_source(ours_log))
        check(deploy.log_source(theirs_log) == theirs,
              "and reads a foreign one as foreign", deploy.log_source(theirs_log))

        # (b) THE DEFECT, reproduced: newest-by-mtime picks the peer's.
        # RESTORE THE RESOLVED CACHE, NOT JUST THE ENV VAR. `vaultpath`
        # memoises the answer in a module global on first call, so putting
        # RURIK_VAULT back leaves every later caller pointed at this temp
        # directory. Caught the same day it was written: section 2 turned into
        # a declared SKIP because it could no longer find vault/dat_study, and
        # a section that silently stops measuring is exactly what the ledger's
        # floor exists to catch -- except the floor had risen enough to hide it.
        saved = os.environ.get("RURIK_VAULT")
        saved_resolved = vaultpath._resolved
        os.environ["RURIK_VAULT"] = tmp
        vaultpath._resolved = None
        try:
            unfiltered = deploy.newest_harness_log(0)
            check(unfiltered == theirs_log,
                  "CONTROL -- unfiltered, it still returns the NEWEST log, "
                  "which here is the other tree's. This is the defect, kept "
                  "runnable so the fix is shown to be about attribution and "
                  "not about ordering", os.path.basename(os.path.dirname(
                      unfiltered or "none")))

            filtered = deploy.newest_harness_log(0, source=mine_src)
            check(filtered == ours_log,
                  "and filtered by source it returns OURS, skipping the newer "
                  "foreign one -- the 2026-08-21 three-session case",
                  os.path.basename(os.path.dirname(filtered or "none")))

            gone = deploy.newest_harness_log(0, source=os.path.normcase(
                os.path.abspath(os.path.join(tmp, "nobody"))))
            check(gone is None,
                  "and a source nothing matches returns None rather than "
                  "falling back to whatever was newest -- the fallback IS the "
                  "defect", repr(gone))
        finally:
            if saved is None:
                os.environ.pop("RURIK_VAULT", None)
            else:
                os.environ["RURIK_VAULT"] = saved
            vaultpath._resolved = saved_resolved

        # (c) the harness rc is a verdict, not decoration.
        v, note = serve_verdict(MESH_LINE, rc=1, note=True)
        check(v == deploy.SERVE_FAILED and "rc 1" in note,
              "a harness that returned non-zero is SERVE_FAILED, whatever the "
              "log says -- it used to score PASS off a matching count", note)
        check("nothing below was measured" in note,
              "and the note says the run failed rather than reporting a mesh "
              "comparison it did not earn", note)

        # (d) the navmesh line must be OUR map.
        other_map = "[map] navmesh 0x1B97D: 58 planes, 55 trapezoids"
        v, note = serve_verdict(other_map, note=True)
        check(v == deploy.SERVE_FAILED,
              "a navmesh line for a DIFFERENT map is SERVE_FAILED even when "
              "the trapezoid count matches exactly -- 0x1B97D is the biome "
              "donor and is pre-warmed in every run of this harness", note)
        check("0x1B97D" in note and f"{0x287D3:#x}" in note,
              "and the note names both what we wanted and what it found", note)

        # (e) CONTROL, and it is the half that matters: the healthy path is
        # untouched. Without this, (c) and (d) are satisfied by a function
        # that always fails.
        both = MESH_LINE + "\n" + other_map
        check(serve_verdict(both) == deploy.SERVE_PASS,
              "CONTROL: our map's line among a foreign one still PASSes -- the "
              "selection picks ours out rather than refusing any log that "
              "mentions another map")
        check(serve_verdict(MESH_LINE) == deploy.SERVE_PASS,
              "CONTROL: the plain healthy case is unchanged")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def section2(area):
    print("\n2. the two donors, and the census that separates them")
    try:
        dat = os.path.join(vaultpath.require_dir("dat_study"), "Gw.dat")
    except SystemExit:
        LEDGER.skip("section 2, which needs the archive",
                    "no vault/dat_study/Gw.dat; the borrowed halves are read "
                    "from it at run time, so this run has measured nothing "
                    "about what an area actually borrows")
        return
    dim = int(area["dims"])
    heights, _worst = stx.snap_block(deploy.GENERATORS[area["heights"]](dim))
    with Archive(dat) as ar:
        good = deploy.Donor(ar, BIOME_ROW, REFERENCE_ROW)
        bad = deploy.Donor(ar, BIOME_ROW, BIOME_ROW)
    n_good = sum(len(v) for v in good.constants.values())
    n_bad = sum(len(v) for v in bad.constants.values())
    check(n_good < n_bad,
          "constants from the 32x32 reference are far smaller than from the "
          "biome donor", f"{n_good} B vs {n_bad} B")
    check(n_bad - n_good > PRESEARING_ZONES - 100,
          "and the difference is the biome donor's per-map Zones chunk, which "
          "is what blew the reservation on the first run",
          f"{n_bad - n_good} B")

    rep = deploy.assemble(area, heights, good, dim, verbose=False)
    check(rep.borrowed <= BORROWED_MAX,
          f"an assembled area borrows under {BORROWED_MAX} B",
          f"{rep.borrowed} B borrowed, {rep.generated} B generated")
    ids = [c.chunk_id for c in mfile.MapFile.decode(rep.blob).chunks]
    check(ids == [c for c in sb.ORDER if c in ids] and sb.ENV in ids
          and sb.SOUND in ids and sb.PROPS_DEPS in ids,
          "and carries the full presentation set in ORDER",
          f"{len(ids)} chunks")


def main():
    area = section0()
    section1(area)
    section3()
    section4()
    section5(area)
    section6()
    section7()
    section8()
    section9()
    section10()
    section11()
    section12()
    section13()
    section2(area)
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
