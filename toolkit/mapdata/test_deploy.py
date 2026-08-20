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

NO VAULT, NO ARCHIVE, NO CLIENT for sections 0-1, 3-8. Section 2 needs the
archive because the borrowed halves are read from it at run time -- that is the
provenance rule, not a convenience -- and the floor turns a vault-less run into
the FAIL it is.

    python toolkit/mapdata/test_deploy.py
"""

import ast
import binascii
import os
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
import deploy  # noqa: E402
import gwdat  # noqa: E402
import gwenc  # noqa: E402
import mapfile as mfile  # noqa: E402
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

# FLOOR: 92, MEASURED from a green run 2026-08-20 (sections 0,1,3,4,5,6,7,8
# score 88 and need no vault -- measured with RURIK_VAULT pointed at an empty
# directory; section 2 reads the archive for the borrowed halves, which is the
# provenance rule rather than a convenience, and the floor sitting ABOVE 88 is
# what turns a vault-less run into the FAIL it is). Was 84 before section 8's
# dry-run and spill checks, 56 before section 8 and the create branch, 35 before
# section 7 and the compression checks, 25 before section 6.
LEDGER = checks.Ledger("test_deploy", floor=92)
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
                  head_flags=MAP_HEAD_FLAGS):
    """One map chain whose partner declares `partner_size`. -> the head's bytes.

    `file_id` and `head_flags` are parameters for section 8's refusals, which are
    about what the id NAMES rather than about the map: a bit-31 spelling in the
    table, or a head that is a plain file (flags 3, stream 0) instead of a
    Bloated map head (259). Both defaults are the shape section 7 has always
    built, so nothing above changes.
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
        with Archive(path) as ar:
            rows2, create2 = deploy.resolve_or_create(ar, NEW_FILE_ID, True)
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
    section2(area)
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
