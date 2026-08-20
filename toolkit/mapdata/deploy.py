r"""Rung G: one command from `content/` to a map you can walk around.

    python toolkit/mapdata/deploy.py --area plaza
    python toolkit/mapdata/deploy.py --area plaza --blend scene.blend
    python toolkit/mapdata/deploy.py --area plaza --install --dat <copy>
    python toolkit/mapdata/deploy.py --area plaza --install --launch --dat <copy>

Everything under this was proved one rung at a time and then driven by a
bespoke script per rung, living in the vault. That is how research should go
and it is not a pipeline: nine scripts that each hard-code a row index, a
donor and a file path are nine places to get it wrong. This is the same ladder
with the numbers pulled out into `content/areas.toml`.

WHAT IT DOES, in order, refusing rather than continuing at each step:

  1. GEOMETRY.  A named generator, or `--blend` for a real Blender scene, which
     is run headless through `tools/blender/export_gwmap.py` and read back as a
     terrain interchange. Either way the field is SNAPPED onto the terrain
     codec's own lattice before anything else -- a freely authored height is
     essentially never representable (the transform's determinant is 8 per
     axis), and a builder that quantises silently loses the difference between
     "the artist put a hill here" and "the codec moved it".
  2. BORROW.  Textures, sun, environment and sound are read from ONE donor map
     in the owner's archive AT RUN TIME, never stored in this repo. One donor
     rather than four keeps the result coherent.
  3. ASSEMBLE.  `stripbuild.build`, which is where every earlier rung's proof
     now lives.
  4. VERIFY, offline and before any archive is touched: the map round-trips,
     the seed stands on walkable ground, the spawn lands in exactly ONE
     trapezoid of the mesh we authored, and the file fits the row's reservation
     -- judged on the bytes that will actually be STORED, which since
     2026-08-20 are compressed ones. A run WITHOUT `--install` says which row
     the stream would go into as well, including "none, this id binds nothing
     and would be created": a dry run whose output cannot tell those apart is
     one nobody can compare against a prediction.
  5. INSTALL (`--install`).  Resolve the row BY FILE ID, write the map into the
     Stripped partner as a compression-8 stream (`--stored-install` for the old
     uncompressed shape), arm the Bloated head to zero length so the client must
     recompile. Journalled; refuses `vault/dat_study` like every other writer.
     OR CREATE IT: when the area's map row carries `created = true` and its file
     id binds nothing, deploy allocates the chain instead of displacing a retail
     one -- two rows under a new id via `datalloc`, the head born empty. That is
     WORLDMAPS-W3; whether a retail client compiles a map from a chain it has
     never seen is WORLDMAPS-W4 and is a client question, not an offline one.
  6. LAUNCH (`--launch`).  The harness, pointed at the area's own map id --
     which is a thing worth writing down, because a harness PASS means "the
     client reached A map", and pointing it at the wrong one produced two runs
     that looked green while compiling nothing (FINDINGS 54).
  7. READ BACK.  The compiled head, compared against what we authored.

WHAT IT IS NOT. It is not a hot reload: the client compiles a map when it
loads one, so "iterate" means run this again. It does not write to the owner's
install, and it cannot -- `datwrite` refuses anything but a copy.
"""

import argparse
import json
import os
import re
import struct
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
from archive import (Archive, file_id_table,  # noqa: E402
                     COMPRESSION_HUFFMAN, COMPRESSION_STORED, FILE_ID_HIGH_BIT)
import content as content_mod  # noqa: E402
import datalloc  # noqa: E402  -- the third verb: rows that did not exist
import datcheck  # noqa: E402  -- the launch-side archive gate
import envchunk  # noqa: E402
import gwenc  # noqa: E402  -- the compression-8 encoder
import mapchunks  # noqa: E402
import mapexport  # noqa: E402
import mapfile as mfile  # noqa: E402
import pathchunk  # noqa: E402
import pathmap  # noqa: E402
from props import Prop, StrippedProps  # noqa: E402
import soundchunk  # noqa: E402
import stripbuild as sb  # noqa: E402
import strippedterrain as stx  # noqa: E402
import terrain as trn_mod  # noqa: E402
import vaultpath  # noqa: E402

TERRAIN_DEPS = 0x11000002
ENV, ENV_DEPS = 0x10000009, 0x11000009
SOUND, SOUND_DEPS = 0x10000012, 0x11000012
PROPS_CHUNK = 0x10000004

# The terrain chunk's sun byte and the environment chunk's are two quantisations
# of one authored angle, at a ratio of exactly 127/32 (FINDINGS 55). A map that
# sets one and not the other has a baked lightmap and a runtime sky pointing in
# different directions, which is what every rung before (e10i) shipped.
SUN_RATIO = 127.0 / 32.0


class Refused(Exception):
    """A stage refused. The message says which and why."""


# ------------------------------------------------------------- geometry

def gen_flat(dim, h=-13):
    return [h] * (dim * dim)


def gen_plaza(dim, base=-13):
    """A flat apron, a low rise to one side, a dip to the other.

    Deliberately gentle: every slope here is inside the walkable band measured
    in FINDINGS 48 (the boundary is 35 degrees), so the shape is about proving
    the pipeline rather than about re-testing the classifier.
    """
    out = [0] * (dim * dim)
    mid = dim // 2
    for gy in range(dim):
        for gx in range(dim):
            d = max(abs(gx - mid), abs(gy - mid))
            if d <= 5:
                h = base                      # the plaza itself, dead flat
            elif gx > mid:
                h = base - 8 * (d - 5)        # a rise (heights are negated)
            else:
                h = base + 4 * (d - 5)        # a shallow dip
            out[trn_mod.Terrain.index(gx, gy, dim)] = h
    return out


GENERATORS = {"flat": gen_flat, "plaza": gen_plaza}


def heights_from_blend(blend, dim, blender=None, workdir=None):
    """Run the Blender exporter headless and read the interchange back."""
    from test_blenderimport import find_blender
    exe, why = (blender, "given") if blender else find_blender()
    if exe is None:
        raise Refused("no Blender found; pass --blender or use a generator")
    exporter = os.path.join(os.path.dirname(os.path.dirname(HERE)),
                            "tools", "blender", "export_gwmap.py")
    outdir = workdir or os.path.join(os.path.dirname(blend), "_gwmap")
    os.makedirs(outdir, exist_ok=True)
    cmd = [exe, "--background", "--factory-startup", "--python-exit-code", "66",
           "--python", exporter, "--", "--blend", blend, "--out", outdir,
           "--name", "deploy"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        raise Refused(f"Blender export failed (rc {proc.returncode}):\n"
                      f"{(proc.stdout + proc.stderr)[-1500:]}")
    js = [f for f in os.listdir(outdir)
          if f.endswith(".json") and f != "manifest.json"]
    if len(js) != 1:
        raise Refused(f"expected one interchange json in {outdir}, found {js}")
    meta = json.load(open(os.path.join(outdir, js[0]), encoding="utf-8"))
    side = next(s for s in meta["sidecars"] if s["kind"] == "heights")
    blob = open(os.path.join(outdir, side["name"]), "rb").read()
    vals = list(struct.unpack("<%df" % (len(blob) // 4), blob))
    if len(vals) != dim * dim:
        raise Refused(f"{len(vals)} samples exported, area declares {dim}x{dim}"
                      f" = {dim * dim}")
    # A BRUSH PRODUCES FRACTIONS, and refusing them refuses the workflow this
    # command exists for. The first version raised here -- correct while the
    # only producer was a Python generator emitting integers, and wrong the
    # moment a real sculpt arrived: 1,010 of 4,225 vertices of the first
    # Blender scene came back non-integer, which is simply what moving a vertex
    # with a falloff does. So round, and REPORT, exactly as the lattice snap
    # does. The residual is <= 0.5 against a 96-unit cell pitch, and the snap
    # that follows moves samples by up to 3 anyway.
    if any(v != v or v in (float("inf"), float("-inf")) for v in vals):
        raise Refused("a non-finite height (NaN or inf) reached the exporter; "
                      "there is no value to round it to")
    ints = [round(v) for v in vals]
    worst = max((abs(i - v) for i, v in zip(ints, vals)), default=0.0)
    frac = sum(1 for i, v in zip(ints, vals) if float(i) != v)
    # world row-major -> the codec's tiled order
    return mapexport.retile(ints, dim, dim), exe, why, worst, frac


# --------------------------------------------------------------- borrow

def _donor_row(archive, area, what, id_key, row_key, default_row=None):
    """Which row `what` comes from IN THIS ARCHIVE, resolved by file id.

    A row index is meaningful only against the copy it was measured on
    (`mapchunks.py`:117), and build 38833 collected on that: the update recycled
    row 7982, so every area row named a 46,556-byte non-map (flags 3) as its
    biome donor while Pre-Searing Ascalon itself sat unharmed at row 177262.
    `_stripped_of` fails closed, so this was a refusal rather than a wrong map
    -- and a refusal on all three areas against any current archive.

    The pinned index survives as a CROSS-CHECK that prints when it disagrees,
    never as the lookup -- the same demotion `asserts.py` and `msgshape.py` gave
    their VAs. Disagreement is expected on any archive but 38797; what would not
    be acceptable is not knowing which row you got.
    """
    fid = area.get(id_key)
    pinned_row = area.get(row_key, default_row)
    if fid is None:
        if pinned_row is None:
            raise Refused(f"area names neither {id_key} nor {row_key} for {what}")
        print(f"  {what}: row {int(pinned_row)} (no {id_key}; an index alone, "
              f"which is only valid against build 38797's archive)")
        return int(pinned_row)
    row = file_id_table(archive).get(int(fid))
    if row is None:
        raise Refused(
            f"{what} file id 0x{int(fid):X} binds to no row in this archive. "
            f"That is the PORTABLE key, so this is a real absence rather than a "
            f"stale index -- check which archive generation you are installing "
            f"into before editing content.")
    if pinned_row is not None and int(pinned_row) != row:
        print(f"  {what}: file id 0x{int(fid):X} -> row {row} "
              f"(pinned {int(pinned_row)} is 38797's answer; this archive differs)")
    else:
        print(f"  {what}: file id 0x{int(fid):X} -> row {row}")
    return row


def _stripped_of(archive, head_row, what):
    mi = mapchunks.MapIndex(archive)
    head = next((h for h, _p in mi.pairs if h.index == head_row), None)
    if head is None:
        raise Refused(f"{what} row {head_row} is not a map head in this archive")
    return mfile.MapFile.decode(archive.read(mi.partner(head)), strict=False)


class Donor:
    """What a map lends, read once -- and it lends TWO different kinds of thing.

    THE STRUCTURAL CONSTANTS (`constants_row`) are Header and Zones, and they
    must come from a map SHAPED LIKE OURS. That is not a style point: Zones is
    per-map, and Pre-Searing's is 7,208 bytes against the 32x32 reference map's
    34. Taking constants from the biome donor built an 11,115-byte map for a
    4,608-byte reservation on the first run of this command -- the tool caught
    it, but the schema had invited it, so the two rows are separate fields now.

    THE BIOME (`head_row`) is everything a map wears: terrain textures, the sun
    angle, the environment chunk, the sound chunk, the prop models. Those are
    the parts that should come from one place so the result is coherent.
    """

    def __init__(self, archive, head_row, constants_row):
        self.stripped = _stripped_of(archive, head_row, "donor")
        cs = (self.stripped if constants_row == head_row
              else _stripped_of(archive, constants_row, "constants"))
        self.constants = {cid: cs.find(cid).payload() for cid in sb.BORROWED}
        self.constants_row = constants_row
        trn = stx.StrippedTerrain.decode(self.stripped.find(sb.TERRAIN).payload())
        self.angle_index = trn.angle_index
        self.table_a = bytes(trn.table_a)
        self.table_b = bytes(trn.table_b)
        self.tex_word = trn.tex_word
        d = self.stripped.find(TERRAIN_DEPS)
        self.terrain_dep_ids = list(
            mapchunks.decode_dependencies(d.payload()).file_ids) if d else []
        self.env = self._pair(ENV, ENV_DEPS)
        self.sound = self._pair(SOUND, SOUND_DEPS)
        self.prop_model_ids = self._prop_models()

    def _pair(self, cid, did):
        c, d = self.stripped.find(cid), self.stripped.find(did)
        if c is None or d is None:
            return None
        return (c.payload(),
                list(mapchunks.decode_dependencies(d.payload()).file_ids))

    def _prop_models(self):
        c = self.stripped.find(0x11000004)
        return list(mapchunks.decode_dependencies(c.payload()).file_ids) if c else []


# ---------------------------------------------------------------- build

def pick_tree_cells(heights, dim, n, seed_cell, pitch=96.0):
    """Deterministic farthest-point pick over FLAT cells, away from the seed.

    Flat matters: a prop on a corner-spread cell sits visibly off the ground,
    and the (e10-next) driver refused its own hard-coded list for exactly that.
    """
    flat = []
    for gy in range(1, dim - 1):
        for gx in range(1, dim - 1):
            hs = [heights[trn_mod.Terrain.index(gx + dx, gy + dy, dim)]
                  for dx in (0, 1) for dy in (0, 1)]
            if max(hs) - min(hs) <= 12 and (gx, gy) != seed_cell:
                flat.append((gx, gy))
    if not flat:
        return []
    picked = [flat[len(flat) // 2]]
    while len(picked) < n and len(picked) < len(flat):
        best, bestd = None, -1
        for c in flat:
            if c in picked:
                continue
            d = min((c[0] - p[0]) ** 2 + (c[1] - p[1]) ** 2 for p in picked)
            if d > bestd:
                best, bestd = c, d
        if best is None:
            break
        picked.append(best)
    return picked[:n]


def assemble(area, heights, donor, dim, verbose=True):
    """Everything the area declares, into one Stripped map."""
    seed = (float(area["seed_x"]), float(area["seed_y"]))
    kw = dict(constants=donor.constants, dep_ids=donor.terrain_dep_ids)

    if area.get("textures", True):
        kw.update(table_a=donor.table_a, table_b=donor.table_b,
                  tex_word=donor.tex_word)
    if area.get("sun", True):
        kw["angle_index"] = donor.angle_index
    if area.get("environment", True):
        if donor.env is None:
            raise Refused("area asks for environment, donor carries none")
        payload, ids = donor.env
        if area.get("sun", True):
            # keep the two suns in step -- see SUN_RATIO
            ec = envchunk.EnvChunk.decode(payload)
            want = int(round(donor.angle_index / SUN_RATIO))
            g = bytearray(ec.global_env())
            if g[16] != want:
                g[16] = want
                ec.section(envchunk.TAG_GLOBAL).records[0] = bytes(g)
                payload = ec.encode()
                if verbose:
                    print(f"  sun: env byte adjusted to {want} to match "
                          f"terrain angle_index {donor.angle_index}")
        kw.update(env_payload=payload, env_dep_ids=ids)
    if area.get("sound", True):
        if donor.sound is None:
            raise Refused("area asks for sound, donor carries none")
        kw["sound_payload"], kw["sound_dep_ids"] = donor.sound

    n_trees = int(area.get("trees", 0) or 0)
    if n_trees:
        if not donor.prop_model_ids:
            raise Refused("area asks for trees, donor lists no prop models")
        seed_cell = (int(seed[0] // 96.0), int(seed[1] // 96.0))
        cells = pick_tree_cells(heights, dim, n_trees, seed_cell)
        if len(cells) < n_trees:
            raise Refused(f"only {len(cells)} flat cells for {n_trees} trees")
        props = []
        for gx, gy in cells:
            z = float(heights[trn_mod.Terrain.index(gx, gy, dim)])
            props.append(Prop(model=0, x=gx * 96.0 + 48.0, y=gy * 96.0 + 48.0,
                              z=z, rot=(0, 0, 0), scale=0x7F, flags=0,
                              outline=()))
        kw["props"] = StrippedProps(props=props, refs4=[], refs6=None)
        kw["prop_dep_ids"] = [donor.prop_model_ids[0]]
        if verbose:
            print(f"  props: {len(props)} at {cells}")

    return sb.build(dim, dim, heights, seed, **kw)


# --------------------------------------------------------------- verify

def verify(report, area, heights, dim, reservation=None, install_size=None,
           compression=COMPRESSION_STORED):
    """Refuse before the archive is touched. Returns a list of finding strings.

    `install_size` is the length of the bytes that will actually OCCUPY the row
    -- the compressed stream, unless `--stored-install`. It defaults to the
    blob's own length so a caller that has not compressed yet still gets the old
    preview. `compression` is carried only so the note can NAME which of the two
    sizes it judged: a preview that says "fits" without saying "fits as what" is
    the kind of line a later reader assumes the wrong meaning of, and the two
    numbers differ by 7.7x on a 96x96 map.
    """
    notes = []
    size = len(report.blob) if install_size is None else install_size
    how = "compression 8" if compression == COMPRESSION_HUFFMAN else "stored"
    back = mfile.MapFile.decode(report.blob)

    trn = stx.StrippedTerrain.decode(back.find(sb.TERRAIN).payload())
    same = sum(1 for a, b in zip(trn.heights, heights) if a == b)
    if same != len(heights):
        raise Refused(f"terrain round trip lost {len(heights) - same} of "
                      f"{len(heights)} samples -- the field was not on the "
                      f"codec's lattice and something quantised it silently")
    notes.append(f"terrain round trip {same}/{len(heights)} samples exact")

    # The STRIPPED path chunk is the compiler's INPUT and carries only the
    # boundary polygon -- the mesh is what the client builds FROM it, so the
    # spawn-in-one-trapezoid test cannot run here. It runs in readback(),
    # against the mesh the client produced. Decoding with the Bloated codec
    # would raise, and the two codecs refuse each other's bytes on purpose.
    sp = pathchunk.StrippedPath.from_chunk(back.find(sb.PATH).payload())
    notes.append(f"authored path chunk {len(back.find(sb.PATH).payload())} B, "
                 f"{len(sp.boundary)} boundary point(s), seq {sp.sequence}")
    if not sp.boundary:
        raise Refused("the authored path chunk carries no boundary point; the "
                      "client's flood fill has no seed and will build no mesh")

    # NOT a refusal any more, and the change is the point: over-reservation used
    # to be fatal because `datwrite` is the only writer that fits in place. The
    # install path relocates instead when it must, so size selects a VERB rather
    # than ending the run.
    #
    # AND THE SIZE IT JUDGES IS THE STORED ONE. This used to read len(report.blob)
    # unconditionally, which was the same number the row would hold; it is not any
    # more, and a preview computed on the plaintext would disagree with the verb
    # the install then picks -- exactly the "the plan said one thing and the run
    # did another" shape the readback below exists to catch after the fact.
    if reservation is None:
        notes.append(f"{size} B ({how})")
    elif size <= reservation:
        notes.append(f"{size} B ({how}) fits the {reservation} B "
                     f"reservation -- replace in place")
    else:
        notes.append(f"{size} B ({how}) exceeds the {reservation} B "
                     f"reservation -- install will RELOCATE the row")
    notes.append(f"{report.generated} B generated, {report.borrowed} B borrowed "
                 f"({100.0 * report.generated / max(1, len(report.blob)):.2f}% ours)")
    return notes


# -------------------------------------------------------------- install

def install_bytes(blob, stored=False):
    """The bytes that will actually OCCUPY the row. -> (stream, code, note).

    RETAIL'S OWN STRIPPED PARTNERS ARE COMPRESSION 8. Ours were stored, and that
    was the deviation rather than the shape -- readable (FINDINGS 35-58 are all
    on stored partners) but not what the client is shipped. It was also the
    ceiling: `datwrite --replace` fits a payload into the row's existing
    whole-block reservation or refuses, so an authored map had to be smaller
    UNCOMPRESSED than whatever ArenaNet had compressed into the same row. That
    is what capped every map this toolkit built at 32x32.

    THE GAIN IS MEASURED, EVERY RUN, AND NEVER ASSUMED. It is not a constant of
    the format: only tag 1 of the terrain chunk is entropy-coded, and the rest of
    an authored map -- tile indices, the bit field, the two tables, props, path
    and both deps chunks -- is raw and, on a generated shape, extremely
    repetitive. MEASURED on `gen_plaza` against build 38797's donors, 2026-08-20:

        32x32   3,941 B -> 1,316 B   (33.4%)
        64x64  10,654 B -> 2,012 B   (18.9%)
        96x96  21,786 B -> 2,828 B   (13.0%)

    against map 143's 4,608 B partner reservation -- so 96x96 now REPLACES in
    place where 32x32 was previously the largest that fit at all. Those are
    figures for one generator on one donor, which is why the note is printed
    rather than the numbers being relied upon.

    `gwenc.encode` keeps its `verify=True` default: it round-trips the stream
    through `gwdat.decompress` and raises before returning if the result is not
    the input. That is the same "refuse before the archive is touched" the whole
    command is built on, and the failure it catches is silent -- a stream one
    word short decodes SHORT rather than raising, and every checksum an archive
    applies is over the stored bytes.
    """
    if stored:
        return blob, COMPRESSION_STORED, (
            f"stored install: {len(blob)} B uncompressed, no gwenc -- the shape "
            f"every map this command installed before 2026-08-20")
    stream = gwenc.encode(blob)
    return stream, COMPRESSION_HUFFMAN, (
        f"compressed install: {len(blob)} B authored -> {len(stream)} B "
        f"compression 8 ({100.0 * len(stream) / len(blob):.1f}% of stored, "
        f"{len(blob) - len(stream)} B saved)")


def spill_stream(here, tag, stream, compression):
    """Write the exact bytes the ROW will hold, beside the archive. -> path|None

    `install_partner` HAS to: `datwrite` and `datmove` take `--data FILE` and a
    compressed stream exists only in memory until something writes it down.
    `create_chain` does NOT -- it hands `datalloc` the bytes directly -- and that
    asymmetry is why this is a function rather than four lines inside the writer's
    arm. It spilled on one path and not the other, so `<area>.c8.bin` existed
    after an install and not after a create, which is backwards: THE CREATE PATH
    IS THE ONE WHERE THESE BYTES ARE OTHERWISE UNRECOVERABLE. After an install
    the row can be read back and decompressed at any time; a created chain that
    the client then rewrites, deletes or refuses leaves no copy of the stream
    `gwenc` produced from this run's blob, and a red arm in WORLDMAPS-W4 has to
    be able to point at exactly what was handed over.

    A STORED WRITE SPILLS NOTHING, on purpose. For compression 0 the stream IS
    the plain payload, already written to `<area>.bin`; a second identical file
    beside it is one more thing that can drift out of step with the first.
    """
    if compression == COMPRESSION_STORED:
        return None
    path = os.path.join(here, f"{tag}.c8.bin")
    with open(path, "wb") as fh:
        fh.write(stream)
    print(f"  wrote {path}")
    return path


def install_partner(dat, out, plain, stream, compression, head_row, partner_row,
                    reservation, tag):
    """Put `stream` in the Stripped partner row and PROVE the row holds it.

    `out` is the file already holding `plain`, and `plain` is the payload a
    READER must get back. That file is the `--expect` both writers demand for a
    compression-8 write, and it is passed on the stored arm too: for a stored row
    the bytes ARE the payload, so declaring them is a statement rather than an
    override -- `datwrite.declaration_fault` consults the decode either way, and
    C-6 (a green archive holding an unreadable file) is reachable through both.

    REPLACE IF IT FITS, RELOCATE IF IT DOES NOT, and the size that decides is the
    one the row will HOLD -- `len(stream)`, never `len(plain)`. This comment used
    to say `datwrite` "writes UNCOMPRESSED and
    refuses to grow a reservation -- correctly, since its invariant is same row,
    same offset, same length -- so an authored map only fits where it is smaller
    than what ArenaNet compressed into that row. That is what capped every map
    this toolkit built at 32x32." Half of that stands: `replace` still never
    relocates, and the reservation is still the row's own whole 512-byte blocks.
    What is gone is the asymmetry -- we compress now too, so the comparison is
    between like and like.

    NOT GROWN BACK, and this is the case the next change is about. `replace`
    writes the size field, so a compressed install SHRINKS the row's reservation
    (map 143's partner: 4,608 B -> 1,536 B after a 1,316 B plaza). The next,
    larger authored map is then past a ceiling the row's own freed blocks sit
    behind, and this function relocates rather than growing in place.
    `datwrite`'s `grow_to` is exactly the flag for it and is deliberately NOT
    wired here: it is a separate change with its own claimant/EOF/withheld-run
    gate, and folding it into this one would make a failed install ambiguous
    between the two.

    Returns the verb that ran: "replace" or "relocate".
    """
    here = os.path.dirname(out)
    # ONE FILE ON THE STORED ARM, deliberately: --data and --expect naming the
    # same bytes is the whole content of "stored" and keeps that arm byte-for-byte
    # what the command wrote before --stored-install existed. `spill_stream`
    # returns None there for exactly that reason.
    data_path = spill_stream(here, tag, stream, compression) or out

    if len(stream) <= reservation:
        verb = "replace"
        print(f"  {len(stream)} B fits the {reservation} B reservation "
              f"-- replacing in place")
        argv = [sys.executable, os.path.join(HERE, "datwrite.py"), "--dat", dat,
                "--replace", str(partner_row), "--data", data_path,
                "--compression", str(compression), "--expect", out,
                "--journal", os.path.join(here, f"{tag}_replace.json"),
                "--verify"]
    else:
        verb = "relocate"
        print(f"  {len(stream)} B does NOT fit the {reservation} B "
              f"reservation -- RELOCATING the row")
        # NO --check-overlaps here: it is a READ-ONLY verb that returns
        # before any move, so passing it got rc 0 with nothing written and
        # this function reported "installed". datmove runs the overlap
        # check itself after a real move.
        argv = [sys.executable, os.path.join(HERE, "datmove.py"), "--dat", dat,
                "--row", str(partner_row), "--data", data_path, "--move",
                "--confirm", "--compression", str(compression),
                "--expect", out,
                "--journal", os.path.join(here, f"{tag}_move.json")]
    rc = subprocess.run(argv, text=True).returncode
    if rc != 0:
        raise Refused(f"the archive writer refused (rc {rc})")
    prove_partner(dat, head_row, plain, compression)
    return verb


def prove_partner(dat, head_row, plain, compression):
    """Read the Stripped partner back and refuse unless it holds what we wrote.

    AN EXIT CODE IS NOT EVIDENCE. This exists because `rc 0` from a writer once
    meant "your flags selected a different verb and nothing happened", and the
    run went on to arm the head and print success over an archive that still
    held ArenaNet's own map.

    `Archive.read` DECOMPRESSES, so this compares what a reader gets back
    against what we authored -- which is the check that got stronger rather than
    weaker when the row stopped being stored. The compression code is asked
    separately, because "the payload is right" and "the row is marked the way
    retail marks it" are two claims and a stored write that silently ignored our
    flag would pass the first.

    SHARED BY BOTH WRITE PATHS, and that is the point of it being a function.
    `install_partner` puts bytes in a row ArenaNet made; `create_chain` makes the
    row. They fail differently and they are checked identically -- a created
    chain that reads back wrong is exactly as unusable as a replaced row that
    does, and WORLDMAPS-W4's whole question is what a client does with bytes it
    has never seen under an id nothing has ever named.

    Resolves the partner through `MapIndex`, i.e. through the head's own
    `nextStream`, rather than through a row index the caller remembers: for a
    created chain the caller's index came from the allocator's plan, and asking
    the archive is how a plan that was carried out wrongly gets caught.
    """
    with Archive(dat) as ar:
        partner = mapchunks.MapIndex(ar).partner(
            next(e for e in ar.entries if e.index == head_row))
        code = partner.compression
        got = ar.read(partner)
    if got != plain:
        raise Refused(
            f"the row does not hold what we wrote: {len(got)} B back "
            f"against {len(plain)} B written. The writer returned "
            f"success and the archive disagrees, so the archive wins")
    if code != compression:
        raise Refused(
            f"the row reads back correctly but is marked compression {code}, "
            f"not the {compression} this install asked for. The bytes and the "
            f"code are two declarations and only one of them was checked")
    print(f"  verified: the row reads back the {len(got)} B we wrote, "
          f"stored as compression {code} in {partner.size} B")
    return partner


# --------------------------------------------------------------- create
#
# WORLDMAPS-W3. Everything above puts an authored map into a row ArenaNet made,
# which means every authored area so far has DISPLACED a live retail one -- map
# 143, file id 0x287D3, and `content/maps.toml` says in its own note that we do
# not know which area we are sitting on. `datalloc` is the verb that stops
# needing a victim, and this is deploy learning to call it.
#
# WHAT IS NEW HERE IS THE SHAPE, NOT THE MECHANISM. A9 (2026-08-20,
# studies/archivewrite/FINDINGS.md 18.6) proved the retail client resolves,
# decompresses and parses a chain `datalloc.alloc` created under a brand-new
# file id. That chain was a model skeleton with real content on every stream. A
# MAP is two rows, and its head is EMPTY on purpose -- the zero-length re-bloat
# trigger -- so a created map chain combines "an id the client has never seen"
# with "a stream the client must COMPILE rather than read", and no run has ever
# put those two together. FINDINGS 36 item 4 names it open. That run is
# WORLDMAPS-W4 and nothing offline can answer it.

MAP_HEAD_FLAGS_U16 = mapchunks.MAP_HEAD_FLAGS_U16          # 259: stream 1, USED|FIRST
MAP_PARTNER_FLAGS_U16 = mapchunks.MAP_PARTNER_FLAGS_U16    # 1:   stream 0, USED


def sibling_of(file_id):
    """The bit-31 spelling of a plain file id: FcArchive's rename marker."""
    return file_id | FILE_ID_HIGH_BIT


def map_chain(ar, file_id):
    """The (head, partner) entries `file_id` names, or None if nothing names it.

    THE QUESTION IS ASKED OF THE RAW TABLE, and that is not a detail. The
    default `file_id_table` registers a bit-31 id under BOTH spellings as a
    convenience of ours; the client does no such thing and compares 32 bits
    exactly. Here the answer decides CREATE versus INSTALL -- that is, whether
    deploy writes into a row that a pending replacement already names, or
    allocates a fresh one -- so it has to be the client's answer.
    `archive.py`'s own docstring lists three failures from getting this
    backwards; this would have been the fourth.

    A BIT-31 SIBLING IS A REFUSAL EITHER WAY, and this is the known gap in the
    allocator rather than a new rule: `plan_alloc` tests `file_id in raw` and so
    ACCEPTS a plain id whose renamed spelling is already in the table, while
    `next_free_file_id` would never suggest it (studies/archivewrite/FINDINGS.md
    17.5, still open 2026-08-20). Allocating there produces two live
    registrations -- a rename pending and a fresh plain claim -- that no crc
    rule and none of `datcheck`'s ten open-time rules counts. `datalloc` is not
    modified to fix that; the caller refuses to walk into it.

    REFUSES rather than returning None when the id names something that is not a
    two-row map chain. "Nothing binds this id" and "this id binds somebody
    else's file" are different states with different remedies, and only the
    first one may create. The shape is checked positively -- head flags 259, a
    non-zero `nextStream`, a partner carrying flags 1 -- because
    `MapIndex.partner` reads `by_row.get(nextStream)` and `nextStream == 0`
    TERMINATES a chain while row 0 is a real MFT row, so a head with no partner
    resolves to the file header rather than to None.
    """
    raw = file_id_table(ar, raw=True)
    twin = sibling_of(file_id)
    if twin in raw:
        raise Refused(
            f"file id {file_id:#x} has a bit-31 sibling {twin:#x} bound to row "
            f"{raw[twin]} in this archive, and this command will not touch "
            f"either spelling.\n"
            f"  Bit 31 is not a spelling variant: FcArchive binds "
            f"`id | 0x80000000` and deletes the plain name when it has REQUESTED "
            f"A REPLACEMENT, so the sibling is the archive announcing that this "
            f"row is stale and a new file is on its way (content/maps.toml "
            f"[map.148] is the whole story).\n"
            f"  `plan_alloc` would accept the plain id here -- it tests exact "
            f"membership -- and leave two live registrations that nothing we own "
            f"counts (studies/archivewrite/FINDINGS.md 17.5). Choose another id "
            f"with `datalloc.py --next-id`, which skips both spellings.")
    row = raw.get(file_id)
    if row is None:
        return None
    by_row = {e.index: e for e in ar.entries}
    head = by_row.get(row)
    if head is None:
        raise Refused(f"file id {file_id:#x} names row {row}, which is absent")
    if not mapchunks.is_map_head(head):
        raise Refused(
            f"file id {file_id:#x} already binds row {row} in this archive, and "
            f"that row is NOT a Bloated map head: alloc.flags "
            f"0x{mapchunks.alloc_flags(head):02X}, stream "
            f"{mapchunks.alloc_stream(head)}, {head.size} B, compression "
            f"{head.compression}.\n"
            f"  A map head is flags 3 (USED|FIRST_STREAM) on stream 1, the u16 "
            f"259. What sits here is somebody else's file, and the remedy is a "
            f"different id rather than a different flag -- overwriting it would "
            f"make one of two files unreachable, which no rule in datcheck "
            f"counts.")
    nxt = mapchunks.next_stream(head)
    if not nxt:
        raise Refused(
            f"file id {file_id:#x} binds row {row}, a map head whose nextStream "
            f"is 0 -- the chain terminates there, so this file has no Stripped "
            f"partner to install into.\n"
            f"  A map is TWO rows and this is one. Nothing here can repair it: "
            f"`datalloc` creates whole chains and `datwrite` writes rows that "
            f"exist.")
    partner = by_row.get(nxt)
    if partner is None:
        raise Refused(
            f"file id {file_id:#x} binds row {row}, whose nextStream names row "
            f"{nxt}, which is absent from this archive's MFT")
    if partner.flags != MAP_PARTNER_FLAGS_U16:
        raise Refused(
            f"file id {file_id:#x} binds row {row}, chained to row {nxt} with "
            f"flags 0x{partner.flags:04X} rather than the Stripped partner's "
            f"0x{MAP_PARTNER_FLAGS_U16:04X} (stream 0, USED).\n"
            f"  MEASURED corpus-wide, the nextStream link map is a bijection "
            f"and every Bloated head chains to exactly one stream-0 row. This "
            f"chain is a shape we have never seen the client produce, so it is "
            f"named rather than installed into.")
    return head, partner


def resolve_or_create(ar, file_id, created):
    """(rows, create). `rows` is None exactly when the chain must be CREATED.

    `created` is the maps.toml row's own `created = true` -- an area that asked
    for a file of its own. It is deliberately NOT inferred from the archive: "the
    id does not resolve" is also what a WRONG id looks like, and until 2026-08-20
    that was this command's loudest refusal. A row that does not claim to be
    created keeps that refusal.
    """
    chain = map_chain(ar, file_id)
    if chain is not None:
        # IDEMPOTENT BY DESIGN. A created chain that already exists is just a
        # map row, and re-deploying an area is the normal iterating loop -- the
        # second run replaces the partner in place and finds the head already
        # armed. Nothing about a row's origin survives into how it is written.
        return resolve_rows(ar, file_id), False
    if not created:
        raise Refused(
            f"file id {file_id:#x} does not resolve in this archive, and its "
            f"maps.toml row does not carry `created = true`.\n"
            f"  That is the old refusal and it is kept: an id that resolves "
            f"nowhere is what a WRONG id looks like, and creating one silently "
            f"would turn a typo into two new MFT rows. If this area is meant to "
            f"own its file, say so in the row.")
    return None, True


def create_note(file_id, size, bound, created, install):
    """What this run says about the ROW the stream is going into. -> str|None

    ASKED ON EVERY RUN, INSTALL OR NOT, and that is the whole reason it is a
    function rather than a line under `if create:`. The decision to allocate is
    computed only under `--install`, correctly -- deciding costs a refusal and a
    build-only run must not refuse -- so a build-only run printed the two sizes
    and stopped, and a dry run against an id NOTHING binds was indistinguishable
    from a dry run against an id everything binds.

    THAT IS NOT COSMETIC, and it was found the way these things are found: by
    running the command. WORLDMAPS-W4's step 1 is a build-only run whose output
    the operator compares against a prediction registered beforehand, and the
    prediction that matters at that step is that the create branch WILL fire --
    that the area -> map row -> file id join lands on a row carrying
    `created = true` whose id binds nothing in this archive. A run that cannot
    say so leaves a correct dry run reading as a refutation of the join, which is
    the same defect as a check that cannot fail, from the other side.

    `bound` IS THE RAW TABLE'S ANSWER, or None: the row the CLIENT's own lookup
    would find (`map_chain`'s docstring has the three failures that come from
    asking the convenience form instead). It is asked here without the shape
    checks that can refuse, because a preview that refuses is not a preview --
    the shape is `map_chain`'s question and it is asked on the install path,
    where a refusal is the correct outcome.

    Returns None when the id binds something: `verify` has already said what that
    row's reservation does with these bytes, and two lines about one row is how
    they drift apart.
    """
    if bound is not None:
        return None
    if created and install:
        return (f"no reservation to judge: file id {file_id:#x} binds nothing "
                f"in this archive, so the {size} B stream will be given a row "
                f"of its own rather than fitted into one")
    if created:
        return (f"no reservation to judge: file id {file_id:#x} binds nothing "
                f"in this archive, so --install would CREATE the chain rather "
                f"than fit the {size} B stream into a row")
    return (f"file id {file_id:#x} binds nothing in this archive and this "
            f"area's map row does not carry `created = true`, so --install "
            f"would REFUSE here rather than allocate -- an id that resolves "
            f"nowhere is also what a WRONG id looks like")


def create_streams(plain, stream, compression):
    """The two rows of a NEW map chain, HEAD FIRST. -> [Stream, Stream].

    Separated from the write so the SHAPE can be inspected without an archive,
    because the shape is the part with a silent failure mode.

    THE HEAD IS EMPTY, and that emptiness is the whole mechanism. A zero-length
    Bloated row is the documented re-bloat trigger: the client fails to load the
    map, logs `Attempting to re-bloat`, compiles the Bloated form from the
    Stripped partner and writes it back. Everywhere else in this toolkit that
    state is produced by ARMING a row that had content (`rebloat.arm`); here it
    is the row's only state ever, which is precisely the case FINDINGS 36 item 4
    names untested.

    THE HEAD IS FIRST BECAUSE THE FILE ID LANDS ON `streams[0]`, and registering
    the partner instead is the natural symmetric mistake. It is refused by
    `plan_alloc`'s shape loop -- but MEASURED corpus-wide the file-id table names
    349 map heads and zero partners, and no crc rule, no `datcheck` rule and no
    overlap sweep would notice the swap. So the order is stated here, in one
    place, rather than at a call site.

    `expect` IS PASSED ON BOTH ARMS. For compression 8 it is mandatory and it is
    the only refutation that exists after the write (the entry crc is over the
    STORED bytes, so a stream that decodes to the wrong payload is green
    everywhere -- FINDINGS C-6). For a stored row the bytes ARE the payload, so
    passing it is the caller stating that positively, exactly as
    `install_partner` does.
    """
    extra = 8 if compression == COMPRESSION_HUFFMAN else 0
    return [datalloc.Stream(b"", MAP_HEAD_FLAGS_U16),
            datalloc.Stream(stream, MAP_PARTNER_FLAGS_U16,
                            extra_bytes=extra, expect=plain)]


def create_chain(dat, file_id, plain, stream, compression, here, tag):
    """Allocate a map's two rows under an id nothing binds yet. -> (head, partner).

    THE PLAN IS PRINTED AND THEN THROWN AWAY. `alloc(plan=...)` exists and is not
    used: a handed-in plan skips `plan_alloc` on the write path, and that gate is
    the whole safety argument (the id is free in the RAW table, exactly one row
    carries FIRST_STREAM, the MFT grows only into its own last block, placement
    consumes runs so two rows of one file cannot collide, every nextStream target
    lands in `[16, count)`). A plan computed a moment earlier is also a placement
    computed against an archive state that may have moved. So the preview is a
    preview -- it costs one read and it is what a person approves -- and the
    write re-plans under its own open.

    NOT ARMED AFTERWARDS, and nothing here calls `rebloat`. The head is BORN
    armed; `rebloat.arm` refuses a zero-length row anyway, correctly, since it
    cannot journal a baseline mesh from a row that has none. `main` reaches the
    same conclusion from the ARCHIVE rather than from this function's word for
    it, which is the stronger of the two checks and is why it was left in place.

    THE STREAM IS SPILLED even though nothing here needs a file: `datalloc` takes
    the bytes in memory, unlike the two CLI writers `install_partner` drives. It
    is written anyway because this is the path where those bytes have no other
    copy -- see `spill_stream`, and WORLDMAPS-W4's capture list, which names the
    file. It happens BEFORE the plan so that a chain the allocator refuses still
    leaves behind the thing that was refused.
    """
    spill_stream(here, tag, stream, compression)
    streams = create_streams(plain, stream, compression)
    try:
        with Archive(dat) as ar:
            preview = datalloc.plan_alloc(ar, streams, file_id)
    except datalloc.Refused as exc:
        raise Refused(f"the allocator will not plan this chain:\n  {exc}") from exc
    preview.show()

    journal = os.path.join(here, f"{tag}_alloc.json")
    try:
        plan = datalloc.alloc(dat, streams, file_id, journal, confirm=True)
    except datalloc.Refused as exc:
        raise Refused(f"the allocator refused the write:\n  {exc}") from exc
    head_row, partner_row = plan.rows[0].index, plan.rows[1].index

    # AND THE ARCHIVE IS ASKED WHETHER THE PLAN HAPPENED. Every claim below is
    # one the allocator could have got wrong in a way nothing else would catch:
    # the id must name the HEAD (a partner registration passes every checksum),
    # the head must be zero length (or the client has nothing to re-bloat), the
    # chain must link head -> partner, and both rows must sit at index >= 16
    # (LoadMft never recycles a row below that, and the open-time reconcile only
    # scans from there, so a row underneath is outside every rule we reasoned
    # about).
    with Archive(dat) as ar:
        raw = file_id_table(ar, raw=True)
        by_row = {e.index: e for e in ar.entries}
        bound = raw.get(file_id)
        head = by_row.get(head_row)
        partner = by_row.get(partner_row)
        also = sorted(k for k, v in raw.items() if v == partner_row)
    if bound != head_row:
        raise Refused(
            f"the chain was allocated but file id {file_id:#x} resolves to "
            f"{bound!r}, not to the head row {head_row}. The open-time reconcile "
            f"DELETES a USED|FIRST_STREAM row no file-id record names")
    if also:
        raise Refused(
            f"the partner row {partner_row} is named by file id(s) "
            f"{', '.join(hex(a) for a in also)}. Only the head may carry an id: "
            f"MEASURED, the table names 349 map heads and zero partners")
    if head is None or partner is None:
        raise Refused(f"rows {head_row}/{partner_row} are not in the MFT after "
                      f"the allocation")
    if head.flags != MAP_HEAD_FLAGS_U16 or partner.flags != MAP_PARTNER_FLAGS_U16:
        raise Refused(
            f"the created rows carry flags 0x{head.flags:04X}/"
            f"0x{partner.flags:04X}, not the map chain's "
            f"0x{MAP_HEAD_FLAGS_U16:04X}/0x{MAP_PARTNER_FLAGS_U16:04X}")
    if head.size != 0:
        raise Refused(
            f"the created head is {head.size} B, not zero. A map head is armed "
            f"by being empty, and a non-empty one is a Bloated map the client "
            f"will load instead of compiling ours")
    if mapchunks.next_stream(head) != partner_row:
        raise Refused(
            f"the created head chains to row {mapchunks.next_stream(head)}, not "
            f"to its partner {partner_row}")
    low = [r for r in (head_row, partner_row) if r < datalloc.FIRST_CLAIMABLE_ROW]
    if low:
        raise Refused(
            f"created row(s) {low} sit below FIRST_CLAIMABLE_ROW "
            f"({datalloc.FIRST_CLAIMABLE_ROW}); rows underneath it are never "
            f"recycled by LoadMft and the reconcile does not scan them")
    print(f"  created: head row {head_row} (zero length -- BORN armed, the "
          f"re-bloat trigger is its only state ever), partner row "
          f"{partner_row}, file id {file_id:#x} registered on the head")
    prove_partner(dat, head_row, plain, compression)
    return head_row, partner_row


def readback(dat, file_id, staged_blob, area):
    """What the client's compiler actually produced, against what we authored.

    The whole verdict is mechanical, which is the point: nobody has to look at
    or listen to anything for this to be a result. Every row here is a thing the
    compiler could have contradicted.
    """
    import terrain as trn_bloated
    from props import BloatedProps

    staged = mfile.MapFile.decode(staged_blob, strict=False)
    with Archive(dat) as ar:
        row = file_id_table(ar)[file_id]        # re-resolve; the head RELOCATES
        head = next(e for e in ar.entries if e.index == row)
        blob = ar.read(head)
    hm = mfile.MapFile.decode(blob, strict=False)

    out, bad = [], []

    def row_(ok, label, detail=""):
        out.append(f"  [{'PASS' if ok else 'FAIL'}] {label}"
                   + (f"  {detail}" if detail else ""))
        if not ok:
            bad.append(label)

    path = hm.find(0x20000008)
    row_(path is not None and len(path.payload()) > 0,
         "the client re-compiled the map",
         f"{len(path.payload()) if path else 0} B path chunk")
    pm = None
    if path is not None:
        pm = pathmap.PathingMap.from_chunk(path.payload())
        out.append(f"         mesh: {len(pm.trapezoids)} trapezoids "
                   f"the client built from our terrain")

    st = stx.StrippedTerrain.decode(staged.find(sb.TERRAIN).payload())
    bt = hm.find(0x20000002)
    if bt is not None:
        same = sum(1 for a, b in zip(trn_bloated.Terrain.decode(bt.payload()).heights,
                                     st.heights) if a == b)
        row_(same == len(st.heights),
             "the compiled height field equals the one we authored",
             f"{same}/{len(st.heights)} samples")

    for cid, scid, what in ((0x20000009, ENV, "environment"),
                            (0x20000012, SOUND, "sound")):
        want = staged.find(scid)
        got = hm.find(cid)
        if want is None:
            continue
        row_(got is not None and got.payload() == want.payload(),
             f"our {what} payload carried VERBATIM", f"{len(want.payload())} B")

    bp = hm.find(0x20000004)
    n_want = len(StrippedProps.decode(staged.find(PROPS_CHUNK).payload()).props)
    if bp is not None:
        row_(len(BloatedProps.decode(bp.payload()).records) == n_want,
             f"our {n_want} prop(s) are in the compiled map")

    # the spawn test every maps.toml row carries, against the CLIENT's mesh
    if pm is not None:
        sx, sy = float(area["seed_x"]), float(area["seed_y"])
        n = sum(1 for t in pm.trapezoids if t.contains(sx, sy))
        row_(n == 1, f"the spawn ({sx:.0f}, {sy:.0f}) lands in exactly one "
                     f"trapezoid of the compiled mesh", f"{n}")
    return out, bad


# --------------------------------------------------------------- launch

def launch(exe, session, dat, map_id, hold, area=None):
    """Run the harness once, with the server pointed at OUR archive.

    `--dat` already decides which client runs, so it decides which world the
    server serves too: `RURIK_DAT` makes both halves name the same file, which
    is also what `contentids.preflight` requires (studies/maprows FINDINGS 8).
    """
    env = dict(os.environ)
    env["RURIK_DAT"] = os.path.abspath(dat)
    print(f"  server world: RURIK_DAT={env['RURIK_DAT']}")
    # The archive gate, run HERE and not left to the harness. session.py's own
    # rule about the cage applies unchanged: a guard that only guards one of two
    # doors is the shape of the defect it is here to prevent. This is also the
    # site with the most to lose -- the archive it is about is one we just WROTE
    # into, and an armed head or a half-finished replace is exactly the state the
    # ten open-time rules and the payload CRC sweep exist to name.
    print(f"  archive: {datcheck.assert_archive_safe(dat, why='serve')['summary']}")
    # --keep-open IS WHAT MAKES --hold MEAN ANYTHING. `session.hold_open` is
    # gated on `keep_open`, which otherwise only the tape chain sets -- so every
    # run of this command before 2026-08-13 asked for 40 s of client time and
    # held for none of it, tearing down as soon as the body reached the map
    # (MEASURED: the two runs of the serve pair started 17 s apart under
    # `--hold 40`). Nothing failed, because the client compiles the map during
    # LOAD and that fits; the flag was describing a wait that was not happening,
    # and a bigger map is exactly where that stops being free.
    # --area rides in --game-args, which session.py forwards to the gamesrv. It
    # is what makes the zone POPULATED rather than empty ground: the server
    # serves this area's spawn rows at their own coordinates and checks each one
    # against the navmesh it pre-warmed. Passed always, so an area with no rows
    # says so in the log rather than quietly serving the global test enemy in
    # the middle of somebody's arrangement.
    game_args = f"--map {map_id}" + (f" --area {area}" if area else "")
    return subprocess.run(
        [sys.executable, session, "--replace", "--keep-open", "--hold", str(hold),
         "--warn", "3", "--exe", exe,
         "--game-args", game_args], text=True, env=env).returncode


def trapezoid_count(dat, file_id):
    """How many trapezoids the client's compiler actually built, from the row."""
    with Archive(dat) as ar:
        pm = pathmap.PathingMap.load(file_id, archive=ar)
    return len(pm.trapezoids)


def newest_harness_log(after):
    """The gamesrv log of the newest harness run started after `after`."""
    root = os.path.join(vaultpath.require_dir(), "captures", "harness")
    best, best_t = None, after
    for name in os.listdir(root):
        d = os.path.join(root, name)
        log = os.path.join(d, "gamesrv.log")
        if not os.path.isfile(log):
            continue
        t = os.path.getmtime(log)
        if t > best_t:
            best, best_t = log, t
    return best


NAVMESH_RE = re.compile(
    r"\[map\] navmesh 0x([0-9A-Fa-f]+): (\d+) planes, (\d+) trapezoids")

# `area 'sculpt': 3 of 3 placed`. Checked because the alternative was measured:
# on the first populated run `spawn_population` threw inside instance bring-up,
# every body was absent, and NOTHING said so -- harness rc 0, all six map
# readback checks green (correctly, they are about the map), the serve check
# matched the navmesh, exit 0. The only evidence was a traceback in a log
# nobody was reading.
PLACED_RE = re.compile(r"area '([^']+)': (\d+) of (\d+) placed")


def serve_run(exe, session, dat, map_id, hold, expect_traps, area=None):
    """A SECOND run, unarmed, that proves the SERVER read our mesh.

    WHY TWO RUNS, and it is not a scheduling detail. `--install` arms the head
    to zero so the client is forced to recompile, so at the moment the server
    starts there is no compiled mesh in the archive to read -- and once the
    client is up it holds the archive open exclusively, so reading it later
    fails (EACCES). The run that PRODUCES the mesh can therefore never serve it.
    This one starts from an archive that already holds it, with nothing else
    open, which is the only configuration where the server can win.

    The verdict is the server's OWN log line rather than anything we compute:
    `[map] navmesh 0x287D3: 1 planes, 13 trapezoids` must name the count we
    just read out of the archive. Comparing against a number we predicted would
    be a check that cannot fail -- this compares two independent readers of the
    same bytes, ours through `pathmap` and the server's through its own load.
    """
    t0 = time.time()
    rc = launch(exe, session, dat, map_id, hold, area=area)
    log = newest_harness_log(t0)
    if log is None:
        return False, f"  harness rc {rc}, but no gamesrv log was written"
    with open(log, "r", encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    hits = NAVMESH_RE.findall(text)
    where = os.path.basename(os.path.dirname(log))
    if not hits:
        why = ("PRE-WARM FAILED" if "PRE-WARM FAILED" in text
               else "no navmesh line at all")
        return False, (f"  harness rc {rc}; {where}: {why} -- the server "
                       f"served no collision")
    fid, planes, traps = hits[0]
    traps = int(traps)
    ok = traps == expect_traps
    note = (f"  harness rc {rc}; {where}: server loaded 0x{fid} with "
            f"{planes} plane(s), {traps} trapezoids "
            f"({'MATCHES' if ok else 'DISAGREES WITH'} the "
            f"{expect_traps} in the archive)")

    # AND THE POPULATION, if one was asked for. Separate from the mesh check
    # because they fail separately: the bodies are created at instance
    # bring-up, well after the navmesh is read, so a throw there leaves the
    # mesh line correct and every map check green.
    if area:
        p = PLACED_RE.findall(text)
        if not p:
            ok = False
            note += (f"\n  area {area!r}: NO population line -- the server "
                     f"never got as far as placing bodies (look for a "
                     f"traceback in {where}/gamesrv.log)")
        else:
            _, placed, total = p[0]
            good = placed == total and int(total) > 0
            ok = ok and good
            note += (f"\n  area {area!r}: {placed} of {total} bodies placed"
                     + ("" if good else "  <-- NOT ALL"))
    return ok, note


def resolve_rows(archive, file_id):
    """(head row, partner row, partner reservation). By FILE ID, never remembered."""
    row = file_id_table(archive).get(file_id)
    if row is None:
        raise Refused(f"file id {file_id:#x} does not resolve in this archive")
    head = next((e for e in archive.entries if e.index == row), None)
    if head is None:
        raise Refused(f"file id {file_id:#x} names row {row}, which is absent")
    mi = mapchunks.MapIndex(archive)
    partner = mi.partner(head)
    reservation = ((partner.size + 511) // 512) * 512
    return head.index, partner.index, reservation


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--area", required=True)
    ap.add_argument("--repo-content-only", action="store_true",
                    help="load content from the repo alone, ignoring the vault "
                         "overlay. For when another session is mid-edit in "
                         "vault/content/ and its rows will not load -- it "
                         "narrows the world, it does NOT relax a check")
    ap.add_argument("--blend", help="a .blend to author the terrain from")
    ap.add_argument("--blender", help="path to the Blender executable")
    ap.add_argument("--dat", help="archive COPY to install into")
    ap.add_argument("--out", help="write the assembled map here")
    ap.add_argument("--install", action="store_true",
                    help="write the map and arm the re-bloat (needs --dat)")
    ap.add_argument("--stored-install", action="store_true",
                    help="write the Stripped partner UNCOMPRESSED, as every run "
                         "of this command before 2026-08-20 did. The default is "
                         "compression 8 because that is the shape retail's own "
                         "Stripped partners have; this is the CONTROL arm for "
                         "the client run that settles whether the map loader "
                         "takes ours, and the escape hatch if it does not")
    ap.add_argument("--launch", action="store_true",
                    help="run the harness at the area's own map id")
    ap.add_argument("--serve", action="store_true",
                    help="after the compile run, launch a SECOND time without "
                         "arming, so the server reads the mesh the client just "
                         "built and paths against OUR geometry. Needs --launch; "
                         "see serve_run() for why one run cannot do both")
    ap.add_argument("--hold", type=int, default=45)
    ap.add_argument("--exe", help="client to launch; defaults to "
                                  "the one beside --dat")
    args = ap.parse_args(argv)

    # The vault overlay is shared between sessions, so a half-written row over
    # there stops this command dead. --repo-content-only skips the overlay; it
    # does not weaken the provenance gate, which still runs on every row that
    # remains, and an area row lives in the repo anyway.
    world = (content_mod.load(vault_dir="") if args.repo_content_only
             else content_mod.load())
    area = world.get("area", args.area)
    dim = int(area["dims"])
    map_id = int(area["map_id"])
    map_row = world.get("map", str(map_id))
    file_id = int(map_row["file_id"])
    # `created` is a CLAIM THE ROW MAKES, not a fact about any archive: the row
    # says this area owns its file rather than displacing a retail one. Whether
    # the file exists yet is the archive's answer and is asked below.
    created_row = bool(map_row.get("created", False))
    print(f"area {args.area!r}: {area['name']} -- map {map_id}, "
          f"{dim}x{dim}, file id {file_id:#x}"
          + ("  (created: this area owns its file)" if created_row else ""))

    # 1. geometry
    if args.blend:
        heights, exe, why, wr, frac = heights_from_blend(
            args.blend, dim, args.blender)
        print(f"  geometry: {args.blend} via Blender ({why})")
        print(f"  rounding: {frac} of {dim * dim} heights were fractional, "
              f"worst moved {wr:.3f} (cell pitch is 96)")
    else:
        gen = area.get("heights", "flat")
        if gen not in GENERATORS:
            raise Refused(f"unknown generator {gen!r}; "
                          f"known: {', '.join(sorted(GENERATORS))}")
        heights = GENERATORS[gen](dim)
        print(f"  geometry: generator {gen!r}")
    heights, worst = stx.snap_field(heights, dim, dim)
    print(f"  lattice snap: worst sample moved {worst}")

    # 2. borrow
    dat = args.dat or os.path.join(vaultpath.require_dir("dat_study"), "Gw.dat")
    with Archive(dat) as ar:
        biome_row = _donor_row(ar, area, "biome donor",
                               "donor_file_id", "donor_row")
        const_row = _donor_row(ar, area, "constants donor",
                               "constants_file_id", "constants_row", 46196)
        donor = Donor(ar, biome_row, const_row)
        print(f"  constants row {donor.constants_row}: "
              f"{sum(len(v) for v in donor.constants.values())} B "
              f"(Header + Zones, structural -- must match our shape)")
        print(f"  biome row {biome_row}: "
              f"{len(donor.terrain_dep_ids)} terrain dep(s), "
              f"angle {donor.angle_index}, "
              f"env {'yes' if donor.env else 'no'}, "
              f"sound {'yes' if donor.sound else 'no'}")
        # RESOLVE, OR DECIDE TO CREATE. `created = true` on the maps.toml row
        # plus an id that binds nothing is the one combination that allocates;
        # everything else either installs into the chain that is there or
        # refuses naming what sits in the way. See resolve_or_create().
        #
        # `bound` IS ASKED ON EVERY RUN and `rows`/`create` only under --install:
        # deciding costs a refusal, reporting does not, and a build-only run that
        # cannot say whether the id binds anything is a dry run whose output does
        # not distinguish the case it was run to preview. See create_note().
        bound = file_id_table(ar, raw=True).get(file_id)
        rows, create = ((None, False) if not args.install
                        else resolve_or_create(ar, file_id, created_row))

    # 3. assemble
    report = assemble(area, heights, donor, dim)

    # 3b. compress. Run on EVERY invocation, install or not: the ratio is a
    # measurement of the map that was just authored, it costs 0.04 s on the
    # largest area in content/, and it is the number the size preview below and
    # the verb the install picks are both computed from. A build-only run that
    # printed the stored size alone would be reporting a number no writer uses.
    stream, compression, size_note = install_bytes(
        report.blob, stored=args.stored_install)
    print(f"  {size_note}")

    # 4. verify
    for note in verify(report, area, heights, dim,
                       reservation=rows[2] if rows else None,
                       install_size=len(stream), compression=compression):
        print(f"  {note}")
    row_note = create_note(file_id, len(stream), bound, created_row, args.install)
    if row_note:
        print(f"  {row_note}")

    out = args.out or os.path.join(os.path.dirname(dat), f"{args.area}.bin")
    if args.out or args.install:
        with open(out, "wb") as fh:
            fh.write(report.blob)
        print(f"  wrote {out}")

    if not args.install and not args.launch:
        print("\nbuild only. --install --dat <copy> to deliver it.")
        return 0

    if args.install:
        here = os.path.dirname(out)
        if create:
            print(f"\ncreating file id {file_id:#x} in {dat}: nothing binds it, "
                  f"and this area's map row asked to own its file")
            head_row, partner_row = create_chain(
                dat, file_id, report.blob, stream, compression, here, args.area)
        else:
            head_row, partner_row, reservation = rows
            print(f"\ninstalling into {dat}: head {head_row}, "
                  f"partner {partner_row}")
            verb = install_partner(dat, out, report.blob, stream, compression,
                                   head_row, partner_row, reservation,
                                   args.area)
            print(f"  the partner row was written by {verb}")
        # ARM ONLY IF IT IS NOT ALREADY ARMED. `rebloat --arm` refuses a
        # zero-length head -- rightly, since it cannot record a baseline mesh
        # from a row that has none, and a second arm would overwrite the first
        # journal with nothing. But "already armed" is not an error HERE: the
        # client recompiles on load either way, and this command is meant to be
        # run repeatedly while iterating on a shape. The previous version turned
        # every re-run after an interrupted one into a dead end.
        #
        # A CREATED HEAD IS BORN ARMED and lands here already zero length, so
        # this takes the same branch for the same reason. It is asked of the
        # ARCHIVE rather than of `create` on purpose: "we just made it empty" is
        # our word for it, and `head_now.size == 0` is the row's.
        with Archive(dat) as ar:
            head_now = next(e for e in ar.entries if e.index == head_row)
            already = head_now.size == 0
        if already:
            print("  the head is already zero length -- already armed, so the "
                  "client will recompile; not arming twice")
        else:
            rc = subprocess.run(
                [sys.executable, os.path.join(HERE, "rebloat.py"), "--dat", dat,
                 "--file-id", hex(file_id), "--arm", "--confirm",
                 "--baseline", os.path.join(here, f"{args.area}_baseline.json"),
                 "--journal", os.path.join(here, f"{args.area}_rebloat.json")],
                text=True).returncode
            if rc != 0:
                raise Refused(f"rebloat refused (rc {rc})")

    if not args.launch:
        print("\ninstalled and armed. --launch to run the client.")
        return 0

    # 6. launch -- at the area's OWN map id, with the client that OWNS this
    # archive. Both halves are earned. A harness PASS means the client reached
    # A map, so pointing it at the default one compiles nothing (FINDINGS 54);
    # and every run directory has its own Gw.dat, so launching the default
    # client after arming a different copy runs against unarmed bytes -- which
    # is the same defect from the other side, and is what the first run of this
    # command did before `--exe` was derived here.
    exe = args.exe or os.path.join(os.path.dirname(dat), "Gw.exe")
    if not os.path.isfile(exe):
        raise Refused(f"no client beside the archive at {exe}; the client that "
                      f"reads {dat} is the only one that can load what we armed")
    session = os.path.join(os.path.dirname(HERE), "harness", "session.py")

    # THE SERVER MUST READ THE ARCHIVE WE JUST WROTE TO, and this is the whole
    # reason `RURIK_DAT` is set here rather than typed into a shell. The server
    # takes its navmesh from `vault/dat_study/Gw.dat` by default; we install the
    # authored map into a COPY, so after an install the two disagree about this
    # very map id -- the server would path against ArenaNet's geometry while the
    # client draws ours, and `contentids.preflight` refuses the launch for
    # exactly that reason (studies/maprows FINDINGS 8). It is a good guard and
    # the fix is not to bypass it: `--dat` already decides which client runs, so
    # it decides which world the server serves too. Both halves then name the
    # same file and the guard passes because the situation is actually right.
    #
    # THE HAZARD IS REAL AND THIS COMMENT USED TO DENY IT. It said the run
    # completes "because the server reads the world at startup, before the
    # client is launched". The world, yes; the NAVMESH, no -- `load_pathmap`
    # ran at instance bring-up, after the client was up and holding this
    # archive open exclusively, so the read returned EACCES and collision
    # turned off silently. Before this env var existed it was quieter still:
    # the server read `dat_study` and got ARENANET's geometry for the same map
    # id, whose walkable set is disjoint from ours (0 of 4,096 grid points
    # shared). `authsrv.prewarm_pathmap` now reads it at startup, which is the
    # only moment the archive both holds our map and is unlocked -- and that is
    # why serving an authored mesh takes TWO runs. See serve_run().
    print(f"launching {exe} at map {map_id}")
    rc = launch(exe, session, dat, map_id, args.hold, area=args.area)
    print(f"\nharness rc {rc}")

    # 7. read back. A harness PASS says the client reached a map; only this
    # says it compiled OURS.
    print("\nreadback -- what the compiler produced, against what we authored:")
    lines, bad = readback(dat, file_id, report.blob, area)
    for line in lines:
        print(line)
    if bad:
        print(f"\n{len(bad)} READBACK CHECK(S) FAILED")
        return 1

    # 8. serve. Everything above is about the CLIENT: it compiled our geometry
    # and drew it. Whether the SERVER agrees about the ground is a separate
    # claim and was false for every run of this command until 2026-08-13.
    if args.serve:
        traps = trapezoid_count(dat, file_id)
        print(f"\nserve -- a second run, unarmed, so the server reads the "
              f"{traps}-trapezoid mesh the client just built:")
        ok, note = serve_run(exe, session, dat, map_id, args.hold, traps,
                             area=args.area)
        print(note)
        if not ok:
            print("\nSERVE CHECK FAILED -- the client walked on our map and "
                  "the server did not")
            return 1
    else:
        print("\nnote: the SERVER did not path against this mesh. It is in the "
              "archive now, so --serve runs again unarmed and proves it does.")

    print("\nrung G: the area was authored, delivered, compiled and verified.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Refused as exc:
        print(f"\nREFUSED: {exc}")
        sys.exit(2)
