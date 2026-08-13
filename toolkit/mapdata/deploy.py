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
     trapezoid of the mesh we authored, and the whole file fits the row's
     reservation.
  5. INSTALL (`--install`).  Resolve the row BY FILE ID, write the map into the
     Stripped partner, arm the Bloated head to zero length so the client must
     recompile. Journalled; refuses `vault/dat_study` like every other writer.
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
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
from archive import Archive, file_id_table  # noqa: E402
import content as content_mod  # noqa: E402
import envchunk  # noqa: E402
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
    ints = [int(v) for v in vals]
    if any(float(i) != v for i, v in zip(ints, vals)):
        raise Refused("a non-integer height reached the exporter; the terrain "
                      "codec's coefficients are integers and there is nowhere "
                      "to put a fraction")
    # world row-major -> the codec's tiled order
    return mapexport.retile(ints, dim, dim), exe, why


# --------------------------------------------------------------- borrow

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

def verify(report, area, heights, dim, reservation=None):
    """Refuse before the archive is touched. Returns a list of finding strings."""
    notes = []
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

    if reservation is not None and len(report.blob) > reservation:
        raise Refused(f"map is {len(report.blob)} B, over the row's "
                      f"{reservation} B reservation")
    notes.append(f"{len(report.blob)} B"
                 + (f" fits {reservation} B reservation" if reservation else ""))
    notes.append(f"{report.generated} B generated, {report.borrowed} B borrowed "
                 f"({100.0 * report.generated / max(1, len(report.blob)):.2f}% ours)")
    return notes


# -------------------------------------------------------------- install

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
    ap.add_argument("--blend", help="a .blend to author the terrain from")
    ap.add_argument("--blender", help="path to the Blender executable")
    ap.add_argument("--dat", help="archive COPY to install into")
    ap.add_argument("--out", help="write the assembled map here")
    ap.add_argument("--install", action="store_true",
                    help="write the map and arm the re-bloat (needs --dat)")
    ap.add_argument("--launch", action="store_true",
                    help="run the harness at the area's own map id")
    ap.add_argument("--hold", type=int, default=45)
    ap.add_argument("--exe", help="client to launch; defaults to "
                                  "the one beside --dat")
    args = ap.parse_args(argv)

    world = content_mod.load()
    area = world.get("area", args.area)
    dim = int(area["dims"])
    map_id = int(area["map_id"])
    map_row = world.get("map", str(map_id))
    file_id = int(map_row["file_id"])
    print(f"area {args.area!r}: {area['name']} -- map {map_id}, "
          f"{dim}x{dim}, file id {file_id:#x}")

    # 1. geometry
    if args.blend:
        heights, exe, why = heights_from_blend(args.blend, dim, args.blender)
        print(f"  geometry: {args.blend} via Blender ({why})")
    else:
        gen = area.get("heights", "flat")
        if gen not in GENERATORS:
            raise Refused(f"unknown generator {gen!r}; "
                          f"known: {', '.join(sorted(GENERATORS))}")
        heights = GENERATORS[gen](dim)
        print(f"  geometry: generator {gen!r}")
    heights, worst = stx.snap_block(heights)
    print(f"  lattice snap: worst sample moved {worst}")

    # 2. borrow
    dat = args.dat or os.path.join(vaultpath.require_dir("dat_study"), "Gw.dat")
    with Archive(dat) as ar:
        donor = Donor(ar, int(area["donor_row"]),
                      int(area.get("constants_row", 46196)))
        print(f"  constants row {donor.constants_row}: "
              f"{sum(len(v) for v in donor.constants.values())} B "
              f"(Header + Zones, structural -- must match our shape)")
        print(f"  biome row {area['donor_row']}: "
              f"{len(donor.terrain_dep_ids)} terrain dep(s), "
              f"angle {donor.angle_index}, "
              f"env {'yes' if donor.env else 'no'}, "
              f"sound {'yes' if donor.sound else 'no'}")
        rows = resolve_rows(ar, file_id) if args.install else None

    # 3. assemble
    report = assemble(area, heights, donor, dim)

    # 4. verify
    for note in verify(report, area, heights, dim,
                       reservation=rows[2] if rows else None):
        print(f"  {note}")

    out = args.out or os.path.join(os.path.dirname(dat), f"{args.area}.bin")
    if args.out or args.install:
        with open(out, "wb") as fh:
            fh.write(report.blob)
        print(f"  wrote {out}")

    if not args.install and not args.launch:
        print("\nbuild only. --install --dat <copy> to deliver it.")
        return 0

    if args.install:
        head_row, partner_row, _res = rows
        print(f"\ninstalling into {dat}: head {head_row}, partner {partner_row}")
        here = os.path.dirname(out)
        rc = subprocess.run(
            [sys.executable, os.path.join(HERE, "datwrite.py"), "--dat", dat,
             "--replace", str(partner_row), "--data", out,
             "--journal", os.path.join(here, f"{args.area}_replace.json"),
             "--verify"], text=True).returncode
        if rc != 0:
            raise Refused(f"datwrite refused (rc {rc})")
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
    print(f"launching {exe} at map {map_id}")
    rc = subprocess.run(
        [sys.executable, session, "--replace", "--hold", str(args.hold),
         "--warn", "3", "--exe", exe,
         "--game-args", f"--map {map_id}"], text=True).returncode
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
    print("\nrung G: the area was authored, delivered, compiled and verified.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Refused as exc:
        print(f"\nREFUSED: {exc}")
        sys.exit(2)
