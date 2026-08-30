"""The scale ladder: the gate, the arithmetic, and the count that catches a snap.

`mapscale.py` exists to say how big an authored area can be with numbers instead
of inference, so most of what it must get right is arithmetic over a pipeline
somebody else already proved. What this file pins is the three things that are
not arithmetic.

SECTION 0 IS THE GATE, AND IT IS TWO WALLS RATHER THAN ONE. `terrain._gate_dims`
refuses `dim % 32` and `dim_x*dim_y > 2^24`; `strippedterrain.validate` refuses
more than 8,192 per axis, because tag 0 stores each axis as `dim/32 - 1` in a
single byte. Those are independent, and the section proves it in both
directions: 8192x2048 clears both walls exactly and is accepted, while 8224x32
is a fifth of a per-cent of the area cap and is still unnameable. The section
also proves the gate runs BEFORE an assemble is spent -- `deploy.assemble` is
replaced with a raiser and a ladder containing one bad dim must come back with
the loader's refusal, not the raiser's.

SECTION 2 IS THE WHOLE POINT OF THE FILE. `snap_block` is a one-tile function:
handed a whole field it projects the first 1,024 samples and silently leaves
every other tile's curvature alone. That bug shipped once and hid behind the
worst-error statistic, because a linear ramp round-trips exactly whether or not
it was snapped and only CURVATURE is lost. This section measures both numbers on
the same 64x64 field and the result is the argument for the whole design:

    snap_block over the whole field -> worst error 4, 2,060 of 4,096 exact
    snap_field  over the whole field -> worst error 4, 4,096 of 4,096 exact

The worst error is IDENTICAL. The statistic literally cannot tell the broken
snap from the correct one, and the per-sample count separates them by 2,036
samples. So the section asserts the two worst errors agree (the statistic's
blindness, measured rather than asserted from memory), asserts the per-sample
count goes red on the half-snapped field, and asserts it stays green on the
snapped one -- the control, without which "refuse everything" would pass.

SECTION 3 IS ABOUT WHAT A REPORT STOPS BEING ABLE TO ANSWER. Two absences ship
through a JSON round trip and both of them used to come back as confident
answers. A `Capacity` loses its run list and keeps its summary, so `fit()` on a
restored one reported "no usable run in this copy is big enough" -- the exact
words a MEASURED refusal prints -- for a stream the same object's surviving
`largest_usable_run_bytes` said fitted two hundred times over; it now carries
`from_document` and refuses. And `Rung.from_dict` policed unknown fields while
`__init__` filled absent ones with None, so a truncated record was accepted and
`snapped_exactly` read `None == None` as every sample surviving, which is the
value `main()` sets its exit code from. Both directions are checked here, each
with the control that the measured object still answers -- otherwise "refuse
everything" would pass, and these are guards whose failure mode is silence.

SECTION 4 NEEDS THE VAULT and declares a skip without it. It measures one
archive copy's capacity fresh -- free runs, MFT slack, id-table slack -- because
every one of those is play-history state that expires when the copy is next
played, and it asserts only relationships, never a remembered number. It also
carries the RECONCILIATION: with the plaza row's own configuration (5 trees,
seed 1536,1536) the ladder reproduces `deploy.install_bytes`' measured table to
the byte at all three of its dims. That is what makes the ladder a measurement
of deploy's pipeline rather than of a re-implementation that drifted.

THE DEFAULT LADDER IS SMALL ON PURPOSE. 32 and 64 in section 1, one 64 in
section 2, three dims in section 4: the whole file runs in about three and a
half seconds. The big rungs -- 128, 192, 256 -- are section 5 and need `--big`,
because the suite is run constantly and a rung nobody is waiting for is a rung
that gets skipped by a person instead of by a flag. Without `--big` section 5
declares its skip and says which command runs it. Measured: 48 checks with no
vault, 62 with, 66 with `--big`.

    python toolkit/mapdata/test_mapscale.py
    python toolkit/mapdata/test_mapscale.py --big
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import checks  # noqa: E402
import datplan  # noqa: E402
import deploy  # noqa: E402
import mapscale  # noqa: E402
import strippedterrain as stx  # noqa: E402
import terrain as trn_mod  # noqa: E402
import vaultpath  # noqa: E402

# FLOOR: 62, MEASURED from a green run on 2026-08-20 and not guessed -- the
# first draft said 47, the run scored 54, and section 3's eight restore checks
# took it to 62. Sections 0-3 score 48 with no vault in reach; section 4 adds
# 14 against the c2 copy; `--big` adds 4 more for 66. The floor is set from the
# run WITHOUT `--big` on purpose: a floor only a flag can reach turns the
# ordinary suite red, and the flag exists so the big rungs are opt-in rather
# than a tax on every run.
LEDGER = checks.Ledger("mapscale", floor=62)
check = checks.adopt(LEDGER)

# The copy WORLDMAPS-W2 and W4 ran against. Named rather than discovered,
# because a capacity figure means nothing without saying whose it is -- and
# read-only: nothing in this file writes a byte into an archive.
COPY = "2026-07-29_221c13772c7a-c2"

# install_bytes' own measured table, and the configuration that produced it.
# The seed is load-bearing: it is carried verbatim in the Path chunk, so moving
# it changes no byte COUNT and changes which bytes, and compression 8 notices.
# At each rung's centre 64x64 measures 2,008; at plaza's own 1536,1536 it
# measures 2,012, which is the docstring's number.
#
# 32x32's STREAM column moved 1,316 -> 1,312 on 2026-08-29, and it moved because
# THE CODE MOVED -- not because an archive did, and not because the pipeline
# regressed. This is the one number in this file that is deliberately EXACT
# rather than a floor: the whole point of the row is byte identity with
# `deploy.install_bytes`, and a floor here would pass a pipeline that had
# silently started emitting something else. So it is re-pinned only with the
# bisect that names the cause.
#
# MEASURED, same archive (vault/run/2026-07-29_221c13772c7a-c2/Gw.dat), same
# donor (row 7982, constants row 46196), same 5 trees at seed 1536,1536, the
# repo checked out at two commits:
#
#   6b3d31d and every commit before it ... 32x32 -> 1,316 B
#   b93ab1d and every commit after it .... 32x32 -> 1,312 B
#
# b93ab1d is WORLDMAPS-W24, and the four bytes are a BUG FIX in `deploy.py`'s
# tree scatter. Grid row 0 renders at world maxY, so the prop's world y must be
# `(dim - 1 - gy) * 96 + 48`; it used to be `gy * 96 + 48` while z was sampled
# from the authored cell, which stood every tree on terrain from a DIFFERENT
# grid row. Verified as exactly that flip: the five props' y values go
# 1488->1584, 2928->144, 144->2928, 2928->144, 144->2928, i.e. gy -> 31-gy on
# all five, and the nine changed bytes lie entirely inside the props chunk
# (0x10000004, body 0x4E..0xBE). The authored column is UNCHANGED at all three
# rungs, so this is the same map with its trees in the right place.
#
# ALL THREE rungs' props chunks changed (9 bytes at 32, 13 at 64 and at 96) --
# 64 and 96 compress to the same size by coincidence, not because W24 missed
# them. Do not read 2,012 and 2,828 as evidence those rungs were untouched.
INSTALL_BYTES_TABLE = {32: (3941, 1312), 64: (10654, 2012), 96: (21786, 2828)}
TABLE_TREES = 5
TABLE_SEED = (1536.0, 1536.0)


def wobbly(dim):
    """A field with curvature everywhere and gentle slopes, in tiled order.

    Deliberately NOT a ramp. A linear field is exactly representable, so it
    round-trips whether or not anybody snapped it -- which is precisely why the
    one-tile bug survived every slope-based test it was ever run through. The
    period-5 wobble here is +/-2 units against a 96-unit cell pitch, so the
    steepest quad is about 2.4 degrees and the seed stands on walkable ground,
    while essentially no 4x4 sub-block of it sits on the codec's lattice.
    """
    out = [0] * (dim * dim)
    for gy in range(dim):
        for gx in range(dim):
            out[trn_mod.Terrain.index(gx, gy, dim)] = (
                -13 + ((gx * 7 + gy * 13) % 5) - 2)
    return out


def refuses(fn, *args, **kw):
    """(did it raise, the message). Refusals are checked by their words too.

    It catches `Exception` rather than the two refusal classes, and prefixes
    the type, because the sabotage that matters here raises something else
    entirely: break the gate's ordering and `ladder` reaches an assemble, which
    fails with an AssertionError. A narrow catch turns that into a traceback
    and a red exit with no [FAIL] line naming the check that broke; a wide one
    with the type in the detail turns it into exactly that line.
    """
    try:
        fn(*args, **kw)
    except Exception as exc:                             # noqa: BLE001
        return True, f"{type(exc).__name__}: {exc}"
    return False, ""


# --------------------------------------------------------------- section 0

def section0():
    print("\n0. the gate: two independent walls, both before any work")

    for dx, dy, why in ((32, 32, "the smallest legal map"),
                        (96, 96, "the largest ever assembled"),
                        (4096, 4096, "exactly MAX_CELLS, 2^24 cells"),
                        (8192, 2048, "exactly MAX_CELLS AND exactly the "
                                     "8,192 tag-0 axis cap")):
        ok, msg = refuses(mapscale.gate_dims, dx, dy)
        check(not ok, f"{dx}x{dy} is accepted -- {why}", msg)

    ok, msg = refuses(mapscale.gate_dims, 48, 48)
    check(ok and "multiples" in msg,
          "48x48 is refused, in _gate_dims' own words", msg)

    ok, msg = refuses(mapscale.gate_dims, 0, 32)
    check(ok, "0x32 is refused", msg)

    ok, msg = refuses(mapscale.gate_dims, 4128, 4128)
    check(ok and str(trn_mod.MAX_CELLS) in msg,
          "4128x4128 is refused by the area cap, which the message names", msg)

    # The two walls are not one wall stated twice, and this is the pair that
    # proves it: an area a fifth of a per-cent of the cap that tag 0 still
    # cannot name, because 8224/32 - 1 is 256 and the field is one byte.
    ok, msg = refuses(mapscale.gate_dims, 8224, 32)
    check(ok and "8192" in msg,
          "8224x32 is refused by the tag-0 axis cap, not the area cap", msg)
    check(8224 * 32 <= trn_mod.MAX_CELLS,
          "CONTROL: and its area clears the area cap with room to spare",
          f"{8224 * 32} of {trn_mod.MAX_CELLS}")

    ok, msg = refuses(mapscale.ladder, [])
    check(ok, "an empty ladder is refused rather than reported as green", msg)

    ok, msg = refuses(mapscale.measure, 32, "no-such-generator")
    check(ok and "known" in msg,
          "an unknown generator is refused and the known ones are named", msg)

    # THE GATE RUNS FIRST. A six-rung ladder at 256 costs real seconds a rung,
    # so a bad dim at the end must refuse immediately rather than after five
    # assembles. Proved by making an assemble impossible and asking for one.
    real = deploy.assemble

    def never(*a, **kw):
        raise AssertionError("an assemble was spent before the gate ran")

    deploy.assemble = never
    try:
        ok, msg = refuses(mapscale.ladder, [32, 48], verbose=False)
    finally:
        deploy.assemble = real
    check(ok and "multiples" in msg,
          "a ladder gates EVERY dim before spending the first assemble", msg)


# --------------------------------------------------------------- section 1

def section1():
    print("\n1. the arithmetic, on a placeholder donor and no vault")

    rep = mapscale.ladder([32, 64], verbose=False)
    small, big = rep.rungs
    check(len(rep.rungs) == 2, "a two-rung ladder returns two rungs")

    for r, dim, tiles in ((small, 32, 1), (big, 64, 4)):
        check(r.cells == dim * dim and r.tiles == tiles,
              f"{dim}x{dim}: {r.cells} cells over {r.tiles} tile(s)")
        check(r.rect == [0.0, 0.0, dim * 96.0, dim * 96.0],
              f"and its rect is the derived dims*96, {r.rect[2]:.0f} wide")
        check(r.roundtrip_exact == r.cells and r.snapped_exactly,
              f"and all {r.cells} samples survive the codec exactly")
        check(r.saved_bytes == r.authored_bytes - r.stream_bytes
              and 0 < r.stream_bytes < r.authored_bytes,
              "and compression 8 gained, with the arithmetic closing",
              f"{r.authored_bytes} -> {r.stream_bytes} B")
        check(abs(r.stream_pct_of_authored
                  - 100.0 * r.stream_bytes / r.authored_bytes) < 1e-9,
              "and the reported ratio is those two numbers and not a third")

    check(big.cells == 4 * small.cells,
          "four times the cells at twice the dim", f"{big.cells}/{small.cells}")
    check(big.authored_bytes > small.authored_bytes
          and big.stream_pct_of_authored < small.stream_pct_of_authored,
          "a bigger map is bigger and compresses further",
          f"{small.stream_pct_of_authored:.1f}% -> "
          f"{big.stream_pct_of_authored:.1f}%")

    check(isinstance(small.snap_worst, int) and small.snap_worst >= 0,
          "the lattice snap reports a whole-unit worst error",
          f"{small.snap_worst}")
    check(small.borrowed == [] and "placeholder" in small.donor,
          "a placeholder donor lends nothing, and the rung says which donor "
          "it was", small.donor)

    # NOT MEASURED IS ITS OWN STATE. With no archive named there is no answer
    # to "where would this go", and a zero there would be an answer.
    check(small.fits is None and small.blocks is None
          and small.block_size is None,
          "with no archive named the capacity columns are None, not 0")
    check(all(getattr(small, f) >= 0.0 for f in
              ("snap_seconds", "assemble_seconds", "compress_seconds",
               "roundtrip_seconds")),
          "and every stage reports its own seconds")


# --------------------------------------------------------------- section 2

def section2():
    print("\n2. the count that catches a snap the worst error cannot")

    dim = 64
    raw = wobbly(dim)
    half, worst_half = stx.snap_block(list(raw))     # the historical bug
    good, worst_good = stx.snap_field(list(raw), dim, dim)

    check(worst_half == worst_good,
          "snap_block over a whole field and snap_field report the SAME worst "
          "error -- the statistic cannot tell them apart",
          f"{worst_half} and {worst_good}")

    r_half = mapscale.measure(dim, heights=half)
    r_good = mapscale.measure(dim, heights=good)

    check(r_half.roundtrip_exact < r_half.cells and not r_half.snapped_exactly,
          "and the PER-SAMPLE count goes red on the half-snapped field",
          f"{r_half.roundtrip_exact}/{r_half.cells} exact, "
          f"{r_half.cells - r_half.roundtrip_exact} lost")
    check(r_half.cells - r_half.roundtrip_exact > 1024,
          "losing more than a whole tile's worth, which is where the bug lives",
          f"{r_half.cells - r_half.roundtrip_exact} lost past tile 0")
    check(r_good.roundtrip_exact == r_good.cells and r_good.snapped_exactly,
          "CONTROL: the same field through snap_field round-trips exactly, so "
          "the check is not `refuse everything`",
          f"{r_good.roundtrip_exact}/{r_good.cells}")
    check(r_half.authored_bytes > 0 and r_good.authored_bytes > 0,
          "and both fields assembled -- the failure is silent, which is why it "
          "needs measuring rather than catching")

    check(r_half.snap_worst is None,
          "a supplied field reports snap_worst None rather than 0: nothing was "
          "moved here, and 0 would be a claim")

    ok, msg = refuses(mapscale.measure, dim, heights=[0] * 10)
    check(ok and str(dim * dim) in msg,
          "a supplied field of the wrong length is refused, naming the count",
          msg)


# --------------------------------------------------------------- section 3

def section3():
    print("\n3. the report survives JSON")

    rep = mapscale.ladder([32], verbose=False)
    text = json.dumps(rep.as_dict())
    back = mapscale.Report.from_dict(json.loads(text))

    check([r.as_dict() for r in back.rungs] == [r.as_dict() for r in rep.rungs],
          "every rung field round-trips through JSON unchanged")
    check(back.capacity is None,
          "and a report with no capacity comes back with no capacity")

    doc = json.loads(text)
    check(len(doc["limits"]) == len(mapscale.LIMITS) and doc["limits"],
          "the report carries its own limits into the file, so a reader who "
          "only ever sees the JSON still gets them",
          f"{len(doc['limits'])} limit(s)")

    bad = dict(doc["rungs"][0])
    bad["future_field"] = 1
    ok, msg = refuses(mapscale.Rung.from_dict, bad)
    check(ok and "future_field" in msg,
          "a rung record from a version this one does not know is refused, "
          "rather than silently dropping the field", msg)

    # AND THE OTHER DIRECTION, which is the one that shipped broken. Refusing
    # unknown fields does nothing about MISSING ones, and `Rung.__init__`
    # fills every absent field with None -- so an empty record was accepted
    # and, because `None == None`, claimed a perfect round trip.
    ok, msg = refuses(mapscale.Rung.from_dict, {})
    check(ok and "missing" in msg,
          "an EMPTY rung record is refused rather than accepted as a rung of "
          "Nones", msg)
    holed = dict(doc["rungs"][0])
    holed.pop("roundtrip_exact")
    ok, msg = refuses(mapscale.Rung.from_dict, holed)
    check(ok and "roundtrip_exact" in msg,
          "and a real record with ONE field dropped is refused, naming it -- "
          "the truncated-or-older-version case", msg)

    ok, msg = refuses(getattr, mapscale.Rung(), "snapped_exactly")
    check(ok and "not a perfect round trip" in msg,
          "and the property itself refuses over a None instead of reading "
          "None == None as every sample surviving -- this is what main() sets "
          "the exit code from", msg)
    check(back.rungs[0].snapped_exactly is True,
          "CONTROL: a rung that HAS both numbers still answers, so the guard "
          "is not `refuse everything`",
          f"{back.rungs[0].roundtrip_exact}/{back.rungs[0].cells}")

    # A RESTORED CAPACITY REFUSES A PLACEMENT QUESTION. Built by hand so the
    # check needs no archive: the run list is ours, the arithmetic is the
    # module's. `fit()` returning None means MEASURED AND TOO BIG, so it is
    # the one answer an empty pool must never be allowed to manufacture.
    live = mapscale.Capacity("synthetic/Gw.dat", 512, [(0x100, 2000)], 0, 0,
                             48, 47)
    blocks, run = live.fit(4820)
    check(run is not None and blocks == datplan.blocks_for(4820, 512),
          "CONTROL: a MEASURED capacity places a 4,820 B stream in its run",
          f"{blocks} block(s) into run {run}")

    restored = mapscale.Report.from_dict(
        {"rungs": [], "capacity": live.as_dict()}).capacity
    check(restored.largest_bytes == live.largest_bytes and restored.runs == [],
          "a capacity's summary survives JSON and its run list does not",
          f"largest {restored.largest_bytes} B over {len(restored.runs)} run(s)")
    ok, msg = refuses(restored.fit, 4820)
    check(ok and "--dat" in msg,
          "so the restored one REFUSES the identical question, naming the "
          "remedy -- rather than answering `no usable run is big enough` for a "
          "stream its own surviving summary says fits 197 times over", msg)
    check("RESTORED" in " ".join(restored.lines()),
          "and it prints as restored rather than as a measurement",
          restored.lines()[0])


# --------------------------------------------------------------- section 4

def section4():
    print("\n4. one archive copy, measured fresh")

    try:
        root = vaultpath.require_dir("run")
    except SystemExit:
        LEDGER.skip("section 4, which needs the vault",
                    "no vault in reach; capacity and the install_bytes "
                    "reconciliation are both archive measurements")
        return
    dat = os.path.join(root, COPY, "Gw.dat")
    if not os.path.isfile(dat):
        LEDGER.skip("section 4, which needs one archive copy",
                    f"{dat} is not there")
        return

    cap = mapscale.capacity_of(dat)
    for line in cap.lines():
        print(f"    {line}")

    # RELATIONSHIPS ONLY. Every number here expires the next time this copy is
    # played, so a test that pinned one would be pinning play history.
    check(cap.block_size == 512, "the archive's block size", f"{cap.block_size}")
    check(cap.runs and cap.largest_bytes > 0
          and cap.usable_bytes >= cap.largest_bytes,
          "it has usable free runs, and the total covers the largest",
          f"{len(cap.runs)} runs, largest {cap.largest_bytes} B")
    # Re-derived from the archive's own geometry rather than restated: the
    # table may grow to the end of the block it already occupies and no
    # further, so its size plus its slack must land exactly on a block edge.
    # An off-by-one in mft_slack fails this; restating rows*24 + remainder
    # could not fail at all.
    with mapscale.Archive(dat) as ar:
        edge = (ar.mft_size + cap.mft_slack_bytes) % ar.block_size
        under = cap.mft_slack_bytes < ar.block_size
    check(edge == 0 and under,
          "MFT size plus its slack lands exactly on a block edge, and the "
          "slack is under one block",
          f"{cap.mft_slack_bytes} B = {cap.mft_slack_rows} row(s)")
    check(cap.created_maps == min((cap.spare_rows + cap.mft_slack_rows) // 2,
                                  cap.id_pairs_spare),
          "and the created-map budget is two rows and one id pair per map",
          f"{cap.created_maps} map(s)")

    blocks, run = cap.fit(cap.largest_bytes + 1)
    check(run is None,
          "one byte past the largest usable run does not fit, and says so "
          "rather than rounding down", f"{blocks} block(s) needed")

    area = mapscale._area_row("plaza")
    donor = mapscale.donor_from(dat, area)
    check(set(donor.constants) == set(mapscale.sb.BORROWED)
          and mapscale.borrowed_of(donor) == ["textures", "sun",
                                              "environment", "sound"],
          "the donor resolves by FILE ID and lends all four optional chunks",
          donor.label)

    rep = mapscale.ladder(sorted(INSTALL_BYTES_TABLE), donor=donor,
                          capacity=cap, trees=TABLE_TREES, seed=TABLE_SEED,
                          verbose=False)
    for r in rep.rungs:
        want_authored, want_stream = INSTALL_BYTES_TABLE[r.dim_x]
        check((r.authored_bytes, r.stream_bytes) == (want_authored, want_stream),
              f"{r.dim_x}x{r.dim_x} reproduces install_bytes' measured row to "
              f"the byte", f"{r.authored_bytes} -> {r.stream_bytes} B")
        check(r.fits and r.run_bytes >= r.stream_bytes
              and r.blocks == datplan.blocks_for(r.stream_bytes, cap.block_size),
              "and its block count and chosen run agree with datplan",
              f"{r.blocks} block(s) into a {r.run_bytes} B run")

    check(all(r.roundtrip_exact == r.cells for r in rep.rungs),
          "every rung on the real donor round-trips exactly",
          ", ".join(f"{r.roundtrip_exact}/{r.cells}" for r in rep.rungs))

    # The section-3 guard, against the real copy and the real stream size: the
    # live capacity places rung 0 (checked above), and the same capacity read
    # back out of JSON refuses the same question rather than reporting the
    # fabricated "no usable run is big enough" an empty pool produces.
    doc = mapscale.Report.from_dict(json.loads(json.dumps(rep.as_dict())))
    ok, msg = refuses(doc.capacity.fit, rep.rungs[0].stream_bytes)
    check(doc.capacity is not None
          and doc.capacity.largest_bytes == cap.largest_bytes
          and doc.capacity.runs == [] and ok and "--dat" in msg,
          "a capacity survives JSON as its summary and NOT as its run list, so "
          "a restored report REFUSES a placement question it no longer has the "
          "data for", msg)


# --------------------------------------------------------------- section 5

def section5(big):
    print("\n5. the big rungs")

    if not big:
        LEDGER.skip("section 5, the 128/192/256 rungs",
                    "not asked for; run `python toolkit/mapdata/"
                    "test_mapscale.py --big`. They cost a few seconds each and "
                    "the suite runs constantly")
        return

    rep = mapscale.ladder([128, 192, 256], verbose=False)
    print("    on the PLACEHOLDER donor -- these byte columns are not "
          "comparable with a real-donor run, and the checks below are "
          "relations rather than values. For real bytes at these dims run "
          "mapscale.py --dat against a copy.")
    for r in rep.rungs:
        for line in r.lines():
            print(f"    {line}")
    check(all(r.roundtrip_exact == r.cells for r in rep.rungs),
          "128, 192 and 256 all round-trip exactly",
          ", ".join(f"{r.roundtrip_exact}/{r.cells}" for r in rep.rungs))
    check([r.cells for r in rep.rungs] == [16384, 36864, 65536],
          "and their cell counts are dim squared")
    check(all(a.stream_pct_of_authored > b.stream_pct_of_authored
              for a, b in zip(rep.rungs, rep.rungs[1:])),
          "the compression ratio keeps falling as the map grows",
          " -> ".join(f"{r.stream_pct_of_authored:.1f}%" for r in rep.rungs))
    check(rep.rungs[-1].cells * 256 == trn_mod.MAX_CELLS,
          "and 256x256 is one 256th of the loader's own 2^24 cell cap -- the "
          "biggest map this toolkit has ever assembled is still 0.39% of it",
          f"{100.0 * rep.rungs[-1].cells / trn_mod.MAX_CELLS:.2f}%")


def main():
    big = "--big" in sys.argv
    section0()
    section1()
    section2()
    section3()
    section4()
    section5(big)
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
