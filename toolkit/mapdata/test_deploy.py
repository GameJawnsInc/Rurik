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

NO VAULT, NO ARCHIVE, NO CLIENT for sections 0-1, 3-7. Section 2 needs the
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
import content as content_mod  # noqa: E402
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

# FLOOR: 56, MEASURED from a green run 2026-08-20 (sections 0,1,3,4,5,6,7 score
# 52 and need no vault; section 2 reads the archive for the borrowed halves,
# which is the provenance rule rather than a convenience, and the floor sitting
# ABOVE 52 is what turns a vault-less run into the FAIL it is). Was 35 before
# section 7 and the compression checks, 25 before section 6.
LEDGER = checks.Ledger("test_deploy", floor=56)
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

BLOCK = 512
ENTRY_SIZE = 24
FILE_MAGIC = b"3AN\x1a"
MFT_MAGIC = b"Mft\x1a"
SLACK = 0xCC

ROW_HEADER, ROW_IDTABLE, ROW_SELF, ROW_HEAD, ROW_PARTNER = 1, 2, 3, 4, 5
ENTRY_COUNT = 6
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


def build_archive(path, partner_size):
    """One map chain whose partner declares `partner_size`. -> the head's bytes."""
    buf = bytearray(bytes([SLACK]) * FILE_SIZE)
    rows = {
        ROW_HEADER:  (0, 32, 0, 3, 0),
        ROW_IDTABLE: (1 * BLOCK, 8, 0, 3, 0),
        ROW_SELF:    (MFT_OFF, MFT_SIZE, 0, 3, 0),
        ROW_HEAD:    (HEAD_BLOCK * BLOCK, HEAD_SIZE, 0, MAP_HEAD_FLAGS,
                      ROW_PARTNER),
        ROW_PARTNER: (PARTNER_BLOCK * BLOCK, partner_size, 0,
                      MAP_PARTNER_FLAGS, 0),
    }
    buf[BLOCK:BLOCK + 8] = struct.pack("<II", FIXTURE_FILE_ID, ROW_HEAD)
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
    section2(area)
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
