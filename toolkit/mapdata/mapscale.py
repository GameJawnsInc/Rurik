r"""WORLDMAPS-W6: how big an authored area can be, answered with measurements.

    python toolkit/mapdata/mapscale.py --dims 32,64,96
    python toolkit/mapdata/mapscale.py --dims 32,64,96,128,192,256 --dat <copy>
    python toolkit/mapdata/mapscale.py --dims 32,64 --dat <copy> --json out.json

WHY THIS EXISTS. Every number the toolkit has about map SIZE is either a cap
read out of a disassembly and never approached, or a measurement at one of
three dims. `terrain._gate_dims` refuses `dim % 32` and `dim_x*dim_y > 2^24`;
`strippedterrain.validate` refuses more than 8,192 per axis because tag 0
stores each axis in one byte. Those are the format's own walls and they are
4096x4096 and 8192 respectively. The largest map this repo has ever ASSEMBLED
is 96x96 -- 9,216 cells, 0.055% of the area cap -- and the largest a retail
client has ever COMPILED for us under compression AND a created chain together
is 64x64. Between "the format allows 16.7 million cells" and "we have built
nine thousand" sits everything a next rung would need to size itself from, and
none of it was written down.

So this module walks a LADDER of dims and reports, per rung, what an authored
map of that size actually costs: the bytes it assembles to, the bytes it
compresses to, the seconds each of those takes, whether the height field
survives the codec sample for sample, and whether the archive copy in front of
it has anywhere to put the result. It measures; it does not extrapolate, and it
prints its own limits beside its numbers because three of them are real.

WHAT IT REFUSES TO DO, and each refusal is a lesson somebody already paid for.

  * IT NEVER REPORTS A WORST-ERROR STATISTIC ALONE. `snap_block` is a one-tile
    function: hand it a whole field and it projects the first 1,024 samples and
    silently leaves every other tile's curvature where it was. At 96x96 that
    lost 2,752 of 9,216 samples while the worst-error number it reported never
    moved, because a linear ramp round-trips exactly whether or not it was
    snapped and only CURVATURE is affected. So every rung carries the PER-SAMPLE
    exact-round-trip count -- how many authored heights the encoded terrain
    chunk gives back unchanged -- and that is the number a reader should look at
    first. `test_mapscale.py` section 2 is the positive control: it hands the
    ladder a deliberately half-snapped field and requires the count to go red
    while the worst error stays small.
  * IT NEVER QUOTES A CAPACITY FIGURE FROM A DOCUMENT. Free-run sizes and MFT
    slack are play-history state of one archive copy: they change the next time
    that copy is played, and one of them (`dat_study_38833`'s 2,892,800-byte
    run) was a detector bug for months. So `--dat` re-measures with
    `datplan.classify_runs` and `datalloc.mft_slack` on every invocation, or the
    capacity columns say "not measured" and mean it. That rule reaches into
    `Report.from_dict`, where it was inverted once and had to be fixed: a
    capacity read back out of JSON keeps its SUMMARY and loses its run list, so
    a restored `Capacity` carries `from_document` and `fit()` REFUSES on it.
    The version that merely passed the empty list through answered a real
    placement question with a fabricated "no run is big enough" -- for a stream
    its own surviving `largest_usable_run_bytes` said fitted 197 times over.
  * IT NEVER FILLS IN A MISSING FIELD. `Rung.from_dict` requires the WHOLE
    field set, not just the absence of unknown ones, because `Rung.__init__`
    defaults every field to None and `snapped_exactly` compared
    `roundtrip_exact == cells` -- so a truncated or older-version record read as
    a rung that round-tripped perfectly, `None == None`. A hole is not a smaller
    measurement, it is an unknown one; the loader refuses it and the property
    refuses to answer over a None.
  * IT GATES DIMS BEFORE IT SPENDS AN ASSEMBLE. Every dim on the ladder is put
    through `gate_dims` first, with the loader's own message, so a typo in a
    six-rung ladder costs a refusal rather than five minutes and then a
    refusal.
  * IT WRITES NO BYTES ANYWHERE except the `--json` report the caller asked
    for, which holds numbers and no payload. The donor is read at run time by
    FILE ID -- the same discipline `deploy.py` uses, for the same reason: a row
    index is meaningful only against the copy it was measured on. Borrowed bytes
    are never stored.

WHAT A RUNG IS NOT. `assemble seconds` is OUR offline cost, not the client's
compile cost -- nothing in this repo has ever measured the client's flood fill
as a function of dims, and that remains the biggest open unknown above 96x96.
And the ladder builds a map from a GENERATOR: `gen_plaza` is deliberately
gentle, so its compression ratio and its trapezoid count say nothing about a
rugged authored landscape of the same size.
"""

import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
from archive import Archive  # noqa: E402
import content as content_mod  # noqa: E402
import datalloc  # noqa: E402  -- mft_slack / id_table_slack, the row budget
import datplan  # noqa: E402  -- classify_runs / best_fit, the byte budget
import deploy  # noqa: E402  -- imported READ-ONLY; this module edits nothing
import mapfile as mfile  # noqa: E402
import stripbuild as sb  # noqa: E402
import strippedterrain as stx  # noqa: E402
import terrain as trn_mod  # noqa: E402
import vaultpath  # noqa: E402

CHUNK = trn_mod.CHUNK_SIZE          # 32, the client's own tile edge
CELL = sb.CELL                      # 96.0 world units per cell
AXIS_TILES_MAX = 0x100              # tag 0 stores dim/32 - 1 in one byte
ENTRY_SIZE = 24                     # one MFT row
ROWS_PER_CREATED_MAP = 2            # a born-empty head plus a Stripped partner

# What the ladder is allowed to claim, printed with every report. Each of these
# is a limit somebody has already read past in this repo.
LIMITS = (
    "the compression ratio is a property of the GENERATOR and the DONOR, not of "
    "the format -- only terrain tag 1 is entropy-coded and the rest of a "
    "generated map is highly repetitive raw bytes, so a rugged authored "
    "landscape at the same dims will not compress like this",
    "a usable-run or MFT-slack figure is PLAY-HISTORY STATE of the one archive "
    "copy named above; it expires the next time that copy is played and must be "
    "re-measured at deploy time, never carried forward from this report",
    "no retail client has compiled anything above 96x96 (stored, relocated into "
    "a retail row), and nothing above 64x64 under compression and a created "
    "chain together -- every rung past those is OFFLINE cost only, and the "
    "client's own map compiler at large dims is unmeasured",
    "assemble and compress seconds are OUR offline cost in CPython on this "
    "machine, and exclude prop placement unless --trees says otherwise -- "
    "`deploy.pick_tree_cells` is the one super-linear step in the assemble path",
)


class Refused(Exception):
    """The ladder refused a rung. The message says which and why."""


# ------------------------------------------------------------------ the gate

def gate_dims(dim_x, dim_y):
    """Both walls the format puts in front of a dimension, before any work.

    The first is `terrain._gate_dims`, raised with ITS OWN message rather than
    a paraphrase -- it is the single choke point both terrain encodings route
    through, and a reader who sees its words can go read the function. The
    second is `strippedterrain.validate`'s separate per-axis cap, which lives
    in a list of findings rather than in a raiser and so cannot be borrowed the
    same way; the text here is that check's text.

    They are independent walls, not one wall stated twice: 8192x2048 clears the
    area cap exactly and clears the axis cap exactly, while 8224x32 is a fifth
    of a per-cent of the area cap and is still unnameable. The test asserts
    both directions for that reason.
    """
    trn_mod._gate_dims(dim_x, dim_y)
    if (dim_x // CHUNK > AXIS_TILES_MAX or dim_y // CHUNK > AXIS_TILES_MAX):
        raise ValueError(f"dims {dim_x}x{dim_y} exceed the 8192 that tag 0's "
                         f"two count bytes can name")


# ----------------------------------------------------------------- the donor

class PlaceholderDonor:
    """Constants of the right SHAPE and none of ArenaNet's content.

    `stripbuild` needs a Header and a Zones chunk or it refuses, and both are
    borrowed from a real map at run time on every real run. A ladder that could
    only run with a vault in reach would be a ladder nobody could test, so this
    is the same stand-in `test_stripbuild.py` sections 0-3 use: two payloads of
    the right length, filled with our own zeros.

    It deliberately carries NO surface, NO environment and NO sound, so a rung
    built on it assembles a strictly smaller map than the same rung on a real
    donor. That difference is why every Rung records which donor it used and
    which chunks it borrowed -- the byte columns of a placeholder ladder are
    not comparable with a real one, and a report that did not say so would
    invite exactly that comparison.
    """

    label = "placeholder (ours, no donor archive)"

    def __init__(self):
        self.constants = {sb.HEADER: bytes(8), sb.ZONES: bytes(34)}
        self.terrain_dep_ids = [1, 2, 3, 4]
        self.table_a = None
        self.table_b = None
        self.tex_word = None
        self.angle_index = None
        self.env = None
        self.sound = None
        self.prop_model_ids = []


def donor_from(dat, area_row):
    """A `deploy.Donor` resolved BY FILE ID out of the archive at `dat`.

    Straight through `deploy._donor_row`, which is the discipline rather than a
    convenience: build 38833 recycled row 7982, so every area row that named a
    donor by index pointed at a 46,556-byte non-map after the update while
    Pre-Searing sat unharmed elsewhere. The pinned index survives as a printed
    cross-check and never as the lookup.

    The donor's bytes stay in memory for the length of the ladder and are never
    written down. The archive is opened read-only and closed here.
    """
    with Archive(dat) as ar:
        biome = deploy._donor_row(ar, area_row, "biome donor",
                                  "donor_file_id", "donor_row")
        const = deploy._donor_row(ar, area_row, "constants donor",
                                  "constants_file_id", "constants_row", 46196)
        donor = deploy.Donor(ar, biome, const)
    donor.label = (f"row {biome} of {os.path.basename(os.path.dirname(dat))}"
                   f"/{os.path.basename(dat)}, constants row {const}")
    return donor


def borrowed_of(donor):
    """Which optional chunks this donor can lend. Order is the report's order."""
    out = []
    if getattr(donor, "table_a", None) is not None:
        out.append("textures")
    if getattr(donor, "angle_index", None) is not None:
        out.append("sun")
    if getattr(donor, "env", None) is not None:
        out.append("environment")
    if getattr(donor, "sound", None) is not None:
        out.append("sound")
    return out


def recipe(donor, dim, trees=0, seed=None):
    """The `area`-shaped dict `deploy.assemble` reads, for one square rung.

    The seed goes at the CENTRE by default, in world units, which is where
    every area row in `content/areas.toml` puts it and for a measured reason:
    `gen_plaza` has a 61-degree cliff at `gx == mid` where the rise side meets
    the dip side, and `stripbuild.check_seed` refuses a seed there rather than
    shipping a map the client would build no navmesh for. The centre cell
    measures 0 degrees.

    IT IS OVERRIDABLE BECAUSE THE SEED MOVES A BYTE COLUMN, which is not
    obvious and cost half an hour of reconciliation. The Path chunk carries the
    boundary point verbatim, so a different seed is the same NUMBER of authored
    bytes and a different set of them -- and compression 8 is sensitive to it.
    `install_bytes`' measured table reads 64x64 -> 2,012 B; this ladder at the
    centre measures 2,008, and at plaza's own `1536,1536` measures 2,012
    exactly. The table is a dims sweep of the plaza ROW with its seed left
    alone, and `--seed 1536,1536` reproduces all three of its rows to the byte.

    Which optional chunks are asked for follows the DONOR rather than a
    constant, so the same ladder runs on a placeholder that lends none of them.
    """
    have = borrowed_of(donor)
    sx, sy = ((dim * (CELL / 2.0), dim * (CELL / 2.0)) if seed is None
              else (float(seed[0]), float(seed[1])))
    return {
        "seed_x": sx,
        "seed_y": sy,
        "textures": "textures" in have,
        "sun": "sun" in have,
        "environment": "environment" in have,
        "sound": "sound" in have,
        "trees": int(trees),
    }


# ------------------------------------------------------------- the two counts

def roundtrip_exact(blob, heights):
    """How many authored samples the ENCODED terrain gives back unchanged.

    THE STATISTIC THAT MATTERS, and the reason this function is not a one-liner
    inside `measure`. `StrippedTerrain.build` snaps every tile itself on the way
    in, so an un-snapped field still ENCODES -- the codec simply moves it, and
    the map is fine, and it is not the map that was authored. The only thing
    that catches that is comparing the decode against the caller's own list,
    sample by sample.

    `deploy.verify` runs the same comparison and REFUSES on any shortfall,
    which is right for a writer and wrong for an instrument: a ladder that
    raised here could not measure the failure it exists to expose. So this
    counts and returns, and the caller decides what a shortfall means.
    """
    back = mfile.MapFile.decode(blob)
    trn = stx.StrippedTerrain.decode(back.find(sb.TERRAIN).payload())
    return sum(1 for a, b in zip(trn.heights, heights) if a == b)


# -------------------------------------------------------------- the capacity

class Capacity:
    """What one archive copy could hold RIGHT NOW, measured on this run.

    Two separate budgets, and a created map needs both:

      * BYTES. `datplan.classify_runs` splits the free space into runs a writer
        may use and runs it may not -- the client rotates its MFT and file-id
        table between recurring slots, and the previous generation is pointed
        at by no row and therefore reads as free. It is not free. A created
        chain's partner needs ONE usable run big enough for the compressed
        stream; the head is born zero-length and owns no extent.
      * ROWS. The MFT grows only into the slack in its own last 512-byte block
        (`datalloc.mft_slack`), plus whatever genuinely spare rows already
        exist. Two rows per created map, and eight bytes of file-id-table
        slack for its id.

    Every field here expires when the copy is next played. Nothing in this
    class is a constant, and the report says so in `LIMITS`.

    `from_document` MARKS ONE THAT WAS NOT MEASURED. The summary numbers
    survive a JSON round trip and the run list does not, so a restored capacity
    can still say how big the largest run WAS and cannot say which run a given
    stream would land in. Those are different questions and only one of them
    survives; `fit()` refuses rather than answering the second from an empty
    pool. The flag is set by `Report.from_dict` alone -- a measured capacity
    never sets it, and there is no way to clear it, because the remedy for a
    stale answer is a fresh `--dat` and never a promotion.
    """

    __slots__ = ("name", "block_size", "runs", "excluded", "usable_bytes",
                 "largest_bytes", "spare_rows", "mft_slack_bytes",
                 "mft_slack_rows", "id_pairs_spare", "created_maps",
                 "from_document")

    def __init__(self, name, block_size, runs, excluded, spare_rows,
                 mft_slack_bytes, id_pairs_spare, from_document=False):
        self.from_document = bool(from_document)
        self.name = name
        self.block_size = block_size
        self.runs = list(runs)
        self.excluded = excluded
        self.usable_bytes = sum(n for _s, n in self.runs) * block_size
        self.largest_bytes = max((n for _s, n in self.runs), default=0) * block_size
        self.spare_rows = spare_rows
        self.mft_slack_bytes = mft_slack_bytes
        self.mft_slack_rows = mft_slack_bytes // ENTRY_SIZE
        self.id_pairs_spare = id_pairs_spare
        self.created_maps = min(
            (spare_rows + self.mft_slack_rows) // ROWS_PER_CREATED_MAP,
            id_pairs_spare)

    def fit(self, nbytes):
        """(blocks needed, chosen run or None) for one stream of `nbytes`.

        `None` for the run means MEASURED AND TOO BIG -- every usable run in
        this copy was checked and none of them holds the stream. That is a
        finding, and `Rung.lines()` prints it as one. It is therefore the one
        answer a capacity with no run list must never be allowed to produce:
        restored from JSON the pool is empty, `best_fit` returns None for
        anything, and a report would print "NO usable run in this copy is big
        enough" for a stream its own summary line said fitted two hundred times
        over. So a restored capacity refuses the question instead.
        """
        if self.from_document:
            raise Refused(
                f"this capacity for {self.name} was restored from a report, "
                f"not measured: the summary survived JSON and the run list did "
                f"not.\n"
                f"    Its largest run was {self.largest_bytes} B WHEN THAT "
                f"REPORT WAS WRITTEN, which is play-history state and may not "
                f"be true now.\n"
                f"    Answering `fit({nbytes})` from the empty pool would "
                f"report `no usable run is big enough`, which is a measurement "
                f"this object cannot make.\n"
                f"    Remedy: re-measure the copy -- capacity_of(dat), or "
                f"mapscale.py --dat <copy>.")
        blocks = datplan.blocks_for(nbytes, self.block_size)
        return blocks, datplan.best_fit(self.runs, blocks)

    def as_dict(self):
        return {
            "name": self.name,
            "block_size": self.block_size,
            "usable_runs": len(self.runs),
            "excluded_runs": self.excluded,
            "usable_bytes": self.usable_bytes,
            "largest_usable_run_bytes": self.largest_bytes,
            "spare_mft_rows": self.spare_rows,
            "mft_slack_bytes": self.mft_slack_bytes,
            "mft_slack_rows": self.mft_slack_rows,
            "id_table_pairs_spare": self.id_pairs_spare,
            "created_maps_the_rows_allow": self.created_maps,
        }

    def lines(self):
        if self.from_document:
            return [
                f"archive {self.name} -- RESTORED FROM A REPORT, NOT MEASURED",
                f"  summary as written: {self.usable_bytes} B usable, largest "
                f"run {self.largest_bytes} B, MFT slack "
                f"{self.mft_slack_bytes} B = {self.mft_slack_rows} row(s), "
                f"{self.id_pairs_spare} spare file-id pair(s)",
                f"  -> {self.created_maps} more CREATED map(s) THE ROWS "
                f"ALLOWED THEN. The run list did not survive the file, so this "
                f"copy cannot be asked where a stream would go; re-measure it.",
            ]
        return [
            f"archive {self.name}",
            f"  {len(self.runs)} usable free run(s), {self.usable_bytes} B "
            f"total, largest {self.largest_bytes} B "
            f"({self.excluded} run(s) withheld as container generations)",
            f"  MFT slack {self.mft_slack_bytes} B = {self.mft_slack_rows} row(s), "
            f"{self.spare_rows} spare row(s) already erased, "
            f"{self.id_pairs_spare} spare file-id pair(s)",
            f"  -> {self.created_maps} more CREATED map(s) this copy has rows "
            f"for, before any question of where the bytes go",
        ]


def capacity_of(dat):
    """Measure one archive copy. Read-only, opened and closed here."""
    with Archive(dat) as ar:
        usable, excluded = datplan.classify_runs(ar)
        block = ar.block_size
        slack = datalloc.mft_slack(ar)
        _off, spare_pairs = datalloc.id_table_slack(ar)
        spare_rows = len(datplan.free_rows(ar))
    return Capacity(os.path.basename(os.path.dirname(dat)) + "/"
                    + os.path.basename(dat),
                    block, usable, len(excluded), spare_rows,
                    slack, spare_pairs // 8)


# ------------------------------------------------------------------ the rung

class Rung:
    """One dim, measured. Every field is a number this run produced."""

    FIELDS = ("dim_x", "dim_y", "cells", "tiles", "rect", "generator",
              "donor", "borrowed", "trees", "seed",
              "authored_bytes", "stream_bytes",
              "stream_pct_of_authored", "saved_bytes", "snap_worst",
              "roundtrip_exact", "snap_seconds", "assemble_seconds",
              "compress_seconds", "roundtrip_seconds", "blocks", "block_size",
              "fits", "run_bytes", "run_start_block")

    __slots__ = FIELDS

    def __init__(self, **kw):
        for name in self.FIELDS:
            setattr(self, name, kw.get(name))

    @property
    def snapped_exactly(self):
        """Did every authored sample come back? REFUSES if it cannot tell.

        `__init__` defaults every field to None, so this used to be the one
        line in the module that turned an ABSENCE into a positive claim:
        `None == None` is True, and a rung with no round-trip count in it
        therefore reported a perfect round trip -- to `Rung.lines()`, and to
        `main()`, which decides the process exit code from exactly this.
        Its sibling `snap_worst` has always been None rather than 0 for the
        same reason, "0 would be a claim"; this is that rule applied to the
        column the module was built around.
        """
        if self.roundtrip_exact is None or self.cells is None:
            where = (f"rung {self.dim_x}x{self.dim_y}" if self.dim_x is not None
                     else "a rung with no dims recorded")
            raise Refused(
                f"{where} cannot say whether the field "
                f"survived: round-trip count "
                f"{self.roundtrip_exact!r} over {self.cells!r} cells.\n"
                f"    A missing count is not a perfect round trip. Re-measure "
                f"the rung -- mapscale.measure(dim, ...) -- rather than "
                f"reading a verdict out of a record that has none.")
        return self.roundtrip_exact == self.cells

    def as_dict(self):
        return {name: getattr(self, name) for name in self.FIELDS}

    @classmethod
    def from_dict(cls, d):
        unknown = sorted(set(d) - set(cls.FIELDS))
        if unknown:
            raise Refused(f"a rung record carries field(s) this version does "
                          f"not know: {', '.join(unknown)}")
        # AND THE OTHER DIRECTION, which is the one that bit. Refusing unknown
        # fields alone let a TRUNCATED record through, and `__init__` fills
        # every absent field with None -- so `Rung.from_dict({})` was accepted
        # and claimed a perfect round trip. A record with a hole in it is not a
        # smaller measurement, it is an unknown one.
        missing = [name for name in cls.FIELDS if name not in d]
        if missing:
            raise Refused(
                f"a rung record is missing field(s) this version requires: "
                f"{', '.join(missing)}.\n"
                f"    Every field of a rung is a number some run produced; an "
                f"absent one is filled with None, and None reads as a "
                f"measurement to anything that compares it.\n"
                f"    Remedy: re-run the ladder that wrote this report rather "
                f"than restoring it -- mapscale.py --dims ... --json OUT.")
        # JSON has no tuples, so a rect round-trips as a list. Normalise on the
        # way in rather than letting an == comparison fail for that reason.
        d = dict(d)
        for name in ("rect", "seed"):
            if d.get(name) is not None:
                d[name] = [float(v) for v in d[name]]
        return cls(**d)

    def lines(self):
        pct = ("n/a" if not self.authored_bytes
               else f"{self.stream_pct_of_authored:.1f}%")
        rt = (f"{self.roundtrip_exact}/{self.cells} samples exact"
              + ("" if self.snapped_exactly
                 else f"  <-- {self.cells - self.roundtrip_exact} LOST"))
        out = [
            f"{self.dim_x}x{self.dim_y}  {self.cells} cells, {self.tiles} tiles, "
            f"rect {self.rect[2]:.0f}x{self.rect[3]:.0f}",
            f"    authored {self.authored_bytes} B -> compression 8 "
            f"{self.stream_bytes} B ({pct} of stored, "
            f"{self.saved_bytes} B saved)",
            f"    lattice snap "
            + ("NOT RUN HERE (field supplied)" if self.snap_worst is None
               else f"worst {self.snap_worst}")
            + f"; round trip {rt}",
            f"    assemble {self.assemble_seconds:.3f} s, compress "
            f"{self.compress_seconds:.3f} s, snap {self.snap_seconds:.3f} s",
        ]
        if self.fits is None:
            out.append("    where it would go: NOT MEASURED -- no archive was "
                       "named, and a capacity figure is a property of one copy")
        elif self.fits:
            out.append(f"    {self.blocks} block(s) of {self.block_size} B: "
                       f"fits the {self.run_bytes} B run at block "
                       f"0x{self.run_start_block:X}")
        else:
            out.append(f"    {self.blocks} block(s) of {self.block_size} B: "
                       f"NO usable run in this copy is big enough")
        return out


def measure(dim, generator="plaza", donor=None, capacity=None, trees=0,
            seed=None, heights=None):
    """One rung of the ladder, square. Returns a `Rung`.

    The order is the order `deploy.main` runs in, deliberately: generate, snap
    the whole field, assemble, compress. A rung that measured its own pipeline
    in a different order from the one that installs maps would be measuring
    something else.

    `heights` HANDS IN A FIELD AND IS NOT SNAPPED, which is the one place this
    function departs from `deploy.main`, and it departs on purpose. A field
    that arrives already authored -- out of Blender, out of another tool, out
    of a half-finished snap -- must be measurable AS IT IS, because projecting
    it onto the lattice first would erase exactly the difference the
    round-trip column exists to report. `snap_worst` is then None: nothing was
    moved by this function, and a zero there would be a claim rather than an
    absence.
    """
    gate_dims(dim, dim)
    if generator not in deploy.GENERATORS:
        raise Refused(f"unknown generator {generator!r}; known: "
                      f"{', '.join(sorted(deploy.GENERATORS))}")
    donor = PlaceholderDonor() if donor is None else donor

    if heights is None:
        raw = deploy.GENERATORS[generator](dim)
        t0 = time.perf_counter()
        snapped, worst = stx.snap_field(raw, dim, dim)
        snap_s = time.perf_counter() - t0
    else:
        if len(heights) != dim * dim:
            raise Refused(f"{len(heights)} heights handed in for {dim}x{dim} "
                          f"= {dim * dim} cells")
        snapped, worst, snap_s = list(heights), None, 0.0
        generator = f"{generator} (field supplied, NOT snapped here)"

    area = recipe(donor, dim, trees, seed)
    t0 = time.perf_counter()
    report = deploy.assemble(area, snapped, donor, dim, verbose=False)
    assemble_s = time.perf_counter() - t0

    t0 = time.perf_counter()
    stream, _code, _note = deploy.install_bytes(report.blob)
    compress_s = time.perf_counter() - t0

    t0 = time.perf_counter()
    exact = roundtrip_exact(report.blob, snapped)
    rt_s = time.perf_counter() - t0

    blocks, run = (None, None)
    if capacity is not None:
        blocks, run = capacity.fit(len(stream))

    return Rung(
        dim_x=dim, dim_y=dim, cells=dim * dim,
        tiles=(dim // CHUNK) * (dim // CHUNK),
        rect=[float(v) for v in sb.default_rect(dim, dim)],
        generator=generator, donor=getattr(donor, "label", "unlabelled"),
        borrowed=borrowed_of(donor), trees=int(trees),
        seed=[area["seed_x"], area["seed_y"]],
        authored_bytes=len(report.blob), stream_bytes=len(stream),
        stream_pct_of_authored=100.0 * len(stream) / max(1, len(report.blob)),
        saved_bytes=len(report.blob) - len(stream),
        snap_worst=worst, roundtrip_exact=exact,
        snap_seconds=snap_s, assemble_seconds=assemble_s,
        compress_seconds=compress_s, roundtrip_seconds=rt_s,
        blocks=blocks,
        block_size=None if capacity is None else capacity.block_size,
        fits=None if capacity is None else run is not None,
        run_bytes=None if not run else run[1] * capacity.block_size,
        run_start_block=None if not run else run[0])


def ladder(dims, generator="plaza", donor=None, capacity=None, trees=0,
           seed=None, verbose=True):
    """Every dim in `dims`, measured. Returns a `Report`.

    EVERY DIM IS GATED FIRST, before a single assemble is spent. A six-rung
    ladder at 256 costs real seconds per rung, and discovering at rung five
    that rung six says 200 is a refusal that should have arrived immediately.
    """
    dims = [int(d) for d in dims]
    if not dims:
        raise Refused("an empty ladder measures nothing")
    for d in dims:
        gate_dims(d, d)
    rungs = []
    for d in dims:
        if verbose:
            print(f"  measuring {d}x{d} ...")
        rungs.append(measure(d, generator, donor, capacity, trees, seed))
    return Report(rungs, capacity)


class Report:
    """A ladder and the copy it was sized against, printable and serialisable."""

    __slots__ = ("rungs", "capacity")

    def __init__(self, rungs, capacity=None):
        self.rungs = list(rungs)
        self.capacity = capacity

    def as_dict(self):
        return {
            "what": "WORLDMAPS-W6 authored-map scale ladder",
            "limits": list(LIMITS),
            "capacity": None if self.capacity is None else self.capacity.as_dict(),
            "rungs": [r.as_dict() for r in self.rungs],
        }

    @classmethod
    def from_dict(cls, d):
        rungs = [Rung.from_dict(r) for r in d["rungs"]]
        cap = d.get("capacity")
        if cap is None:
            return cls(rungs, None)
        # A capacity read back from JSON has no run list -- the summary numbers
        # survive, the runs do not, and `fit()` on a restored report would
        # otherwise answer from an empty pool. `from_document=True` is what
        # says so: it turns the placement question into a refusal naming
        # --dat, instead of into a "no run is big enough" that reads exactly
        # like a measurement and is not one.
        restored = Capacity(cap["name"], cap["block_size"], [],
                            cap["excluded_runs"], cap["spare_mft_rows"],
                            cap["mft_slack_bytes"],
                            cap["id_table_pairs_spare"], from_document=True)
        restored.usable_bytes = cap["usable_bytes"]
        restored.largest_bytes = cap["largest_usable_run_bytes"]
        return cls(rungs, restored)

    def lines(self):
        out = []
        if self.capacity is not None:
            out.extend(self.capacity.lines())
            out.append("")
        for r in self.rungs:
            out.extend(r.lines())
        out.append("")
        out.append("what this ladder does NOT say:")
        for limit in LIMITS:
            out.append(f"  - {limit}")
        return out

    def show(self):
        for line in self.lines():
            print(line)


# ------------------------------------------------------------------- the CLI

def _area_row(area_name, repo_content_only=False):
    """The content row that names the donor file ids. Content, not literals."""
    world = (content_mod.load(vault_dir="") if repo_content_only
             else content_mod.load())
    return world.get("area", area_name)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dims", default="32,64,96",
                    help="comma-separated square dims to measure "
                         "(default 32,64,96)")
    ap.add_argument("--dat", help="archive COPY to size against and to read the "
                                  "donor from. Read-only; nothing is written to "
                                  "it. Without this the ladder runs on "
                                  "placeholder constants and reports no "
                                  "capacity at all")
    ap.add_argument("--donor-area", default="plaza",
                    help="which content/areas.toml row names the donor file "
                         "ids (default plaza)")
    ap.add_argument("--generator", default="plaza",
                    help="a deploy.GENERATORS name (default plaza)")
    ap.add_argument("--trees", type=int, default=0,
                    help="props to place per rung. 0 by default because "
                         "deploy.pick_tree_cells is the one super-linear step "
                         "in the assemble path, and a timing that folded it in "
                         "would not be a timing of the codec")
    ap.add_argument("--seed", help="X,Y world coordinates for the flood seed, "
                                   "the same on every rung. Defaults to each "
                                   "rung's own centre; `--seed 1536,1536` "
                                   "reproduces install_bytes' measured table")
    ap.add_argument("--repo-content-only", action="store_true",
                    help="load content from the repo alone, ignoring the vault "
                         "overlay -- deploy.py's flag, for the same reason")
    ap.add_argument("--json", dest="json_out",
                    help="write the report here. Numbers only; no payload, no "
                         "borrowed bytes")
    args = ap.parse_args(argv)

    dims = [int(d) for d in args.dims.split(",") if d.strip()]
    seed = None
    if args.seed:
        parts = args.seed.split(",")
        if len(parts) != 2:
            raise Refused(f"--seed takes X,Y; got {args.seed!r}")
        seed = (float(parts[0]), float(parts[1]))

    donor, capacity = None, None
    if args.dat:
        if not os.path.isfile(args.dat):
            raise Refused(f"no archive at {args.dat}")
        area = _area_row(args.donor_area, args.repo_content_only)
        print(f"donor from {args.dat} via area {args.donor_area!r}:")
        donor = donor_from(args.dat, area)
        capacity = capacity_of(args.dat)
    else:
        print("no --dat: placeholder constants, and no capacity measured. "
              "The byte columns of this ladder are NOT comparable with a "
              "real-donor run -- see the donor field on each rung.")

    print(f"\nladder {args.dims} on generator {args.generator!r}, "
          f"{args.trees} tree(s) per rung, seed "
          + ("each rung's centre" if seed is None else f"{seed[0]},{seed[1]}")
          + ":")
    rep = ladder(dims, args.generator, donor, capacity, args.trees, seed)
    print("")
    rep.show()

    lost = [r for r in rep.rungs if not r.snapped_exactly]
    if lost:
        print("\nROUND TRIP INCOMPLETE at "
              + ", ".join(f"{r.dim_x}x{r.dim_y}" for r in lost)
              + " -- the authored field is not what the codec gives back, and "
                "the worst-error column will not tell you that")

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(rep.as_dict(), fh, indent=2)
        print(f"\nwrote {args.json_out}")
    return 1 if lost else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Refused as exc:
        print(f"\nREFUSED: {exc}")
        sys.exit(2)
    except ValueError as exc:
        print(f"\nREFUSED: {exc}")
        sys.exit(2)
