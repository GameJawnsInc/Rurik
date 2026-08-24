r"""What ARE a donor map's prop models? Measured, offline, with no client.

    python toolkit/mapdata/propscan.py --area ashcoil
    python toolkit/mapdata/propscan.py --donor-row 7982 --max-cells 2

WHY THIS EXISTS, and it is a specific failure rather than a general wish.

WORLDMAPS-W24 authored a place, served it, and the owner walked it. Verdict:
"complete failure", on five fronts, and the second was **"the biome donor's
model 0 is a monumental building, not a tree -- 32 of them scattered like
shrubs loom one-sided over the bowl"**. `deploy.py` wrote
`prop_dep_ids = [donor.prop_model_ids[0]]` and gave every prop `model=0`, so
an authored map could place exactly ONE model and had no say in which.

It was not even a bad default. It was the ONLY default, and nothing in the
toolkit could tell an author what `[0]` was. That is what this module fixes:
the donor lists **229** models, and their horizontal extents run from 27 to
17,145 units against a 96-unit placement pitch.

THE MEASUREMENT, and why it needs no render. `SubModel.positions()` is real
f32 (x, y, z) at the head of each vertex, so a bounding box falls straight out
of the geometry chunk. Extent in PITCH UNITS is the number that matters,
because `deploy.pick_tree_cells` places props on a 96-unit grid: a model 16
cells wide placed on adjacent cells interpenetrates its neighbours, which is
exactly the picture W24 reported.

WHAT THIS DOES NOT DO, stated plainly: it does not NAME a model. "Model 26 is
a tree" is not a claim this module can make -- it measures size, vertex and
triangle counts, and how many times the donor's own map places each one. A
model 3.7 cells wide and 191 units tall that retail scatters 58 times is
vegetation-SCALE; what it depicts is UNVERIFIED until somebody looks at it.
Every caller gets the numbers and makes its own call.

AND ONE HYPOTHESIS THIS MODULE TESTED, so nobody builds on it: **placement
count is a WEAK size signal, not a proxy.** Spearman rho **-0.219** over all
229 -- retail does place its smaller props somewhat more often, but the median
of the twenty it places ten-or-more times is still **7.3 placement cells**
wide. Choosing the most POPULAR model would not have avoided W24 either; only
measuring the size does. The placement count is context, not a filter.

(The first form of that claim said "no correlation at all", from the ten
most-placed against "the ten least-placed". 91 of the 229 are placed exactly
once, so which ten is a TIE-BREAK: one arbitrary slice gives mean 926, another
4163. The test caught it by going red. Corrected to the rank correlation over
every model, which has no ties to break.)

Windows or not, standard library only.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import mapchunks                                                 # noqa: E402
import modelfile                                                 # noqa: E402
import props as propmod                                          # noqa: E402

#: `deploy.pick_tree_cells`' grid step, and the unit this module reports in.
#: A prop wider than this cannot be placed on adjacent cells without
#: interpenetrating, which is the whole point of measuring.
PITCH = 96.0

#: The stripped map's props chunk and its dependency list. Both come from
#: `stripbuild`'s own constants; they are repeated here rather than imported so
#: this module does not drag the builder in to read a map.
PROPS = 0x10000004
PROPS_DEPS = 0x11000004


class PropScanError(RuntimeError):
    pass


class PropModel:
    """One entry of a donor's prop-model list, measured."""

    __slots__ = ("index", "file_id", "row", "extent", "n_verts", "n_tris",
                 "n_submodels", "placed", "error")

    def __init__(self, index, file_id, row=None, extent=None, n_verts=0,
                 n_tris=0, n_submodels=0, placed=0, error=None):
        self.index = index
        self.file_id = file_id
        self.row = row
        self.extent = extent            # (dx, dy, dz) or None
        self.n_verts = n_verts
        self.n_tris = n_tris
        self.n_submodels = n_submodels
        self.placed = placed            # times the DONOR's own map places it
        self.error = error

    @property
    def horizontal(self):
        """The larger of the two ground-plane extents, or None."""
        return None if self.extent is None else max(self.extent[0],
                                                    self.extent[1])

    @property
    def cells(self):
        """Horizontal extent in placement pitches. The actionable number."""
        h = self.horizontal
        return None if h is None else h / PITCH

    @property
    def height(self):
        return None if self.extent is None else self.extent[2]

    @property
    def aspect(self):
        """height / horizontal extent. The most separating single number.

        MEASURED on Pre-Searing's 229: model 0 -- the one `deploy.py` placed
        for every map this toolkit ever authored -- is 16.0 cells wide and
        aspect **0.63**, squat and enormous. The two extremes at the other end
        are 0.84 cells wide with aspect **7.6**, 43 and 56 triangles, and the
        donor places one of them 12 times. Size alone does not separate those
        two populations as cleanly, because a big landmark and a big tree are
        both big.

        Still NOT a name. Tall-and-thin is a shape, not a species, and this
        module refuses to guess which.
        """
        h = self.horizontal
        return None if not h else self.extent[2] / h

    def __repr__(self):
        return (f"PropModel(#{self.index} 0x{self.file_id:X} "
                f"{'?' if self.cells is None else format(self.cells, '.1f')}"
                f" cells placed={self.placed})")


def _bbox(geo):
    lo = [float("inf")] * 3
    hi = [float("-inf")] * 3
    nv = tris = 0
    for sm in geo.submodels:
        nv += sm.nv
        tris += len(sm.indices) // 3
        for p in sm.positions():
            for i in range(3):
                if p[i] < lo[i]:
                    lo[i] = p[i]
                if p[i] > hi[i]:
                    hi[i] = p[i]
    if lo[0] == float("inf"):
        return None, nv, tris
    return tuple(hi[i] - lo[i] for i in range(3)), nv, tris


def scan(archive, stripped, table=None):
    """Measure every prop model a stripped donor map lists.

    `stripped` is a decoded MapFile (what `deploy._stripped_of` returns).
    Returns a list of PropModel, index-aligned with the donor's own dependency
    order -- so `result[k]` is what `prop_dep_ids = [ids[k]]` would install.

    A model that cannot be read gets its `error` set and its measurements left
    empty; it is never dropped, because a caller choosing by index needs the
    indices to stay put.
    """
    dep = stripped.find(PROPS_DEPS)
    if dep is None:
        raise PropScanError("this map lists no prop models (no 0x11000004)")
    ids = list(mapchunks.decode_dependencies(dep.payload()).file_ids)
    if table is None:
        table = mapchunks.file_id_table(archive)

    # How often the donor's OWN map places each index. Context, not a filter --
    # the module docstring records why (it does not track size).
    placed = {}
    pc = stripped.find(PROPS)
    if pc is not None:
        try:
            sp = propmod.StrippedProps.decode(pc.payload())
            for p in sp.props:
                placed[p.model] = placed.get(p.model, 0) + 1
        except Exception as exc:                                # noqa: BLE001
            raise PropScanError(
                f"the donor lists {len(ids)} prop models but its props chunk "
                f"would not decode ({exc}) -- placement counts would be a "
                f"silent zero for every model, so this refuses instead")

    out = []
    for i, fid in enumerate(ids):
        row = table.get(fid)
        if row is None:
            out.append(PropModel(i, fid, error="not in this archive"))
            continue
        try:
            geo = modelfile.ModelFile.decode(
                archive.read(archive.row(row))).geometry()
        except Exception as exc:                                # noqa: BLE001
            out.append(PropModel(i, fid, row=row,
                                 error=f"{type(exc).__name__}: {exc}"))
            continue
        ext, nv, tris = _bbox(geo)
        out.append(PropModel(i, fid, row=row, extent=ext, n_verts=nv,
                             n_tris=tris, n_submodels=len(geo.submodels),
                             placed=placed.get(i, 0)))
    return out


def fits_pitch(model, pitch_cells=1.0):
    """Can this model sit on adjacent placement cells without overlapping?

    The check `deploy.py` never had. A model whose horizontal extent exceeds
    `pitch_cells` pitches interpenetrates a neighbour placed one cell away --
    W24 put 32 copies of a SIXTEEN-cell model on a 96-unit grid and the owner
    described them as looming.

    An unmeasurable model answers None, never True: "we could not read it" and
    "it fits" are different, and only one of them is a licence to place it.
    """
    c = model.cells
    return None if c is None else c <= pitch_cells


def report(models, out=None, max_cells=None, top=None):
    w = (out or sys.stdout).write
    ok = [m for m in models if m.extent is not None]
    w(f"{len(models)} prop model(s), {len(ok)} measured, "
      f"{len(models) - len(ok)} unreadable\n")
    if ok:
        hs = sorted(m.cells for m in ok)
        w(f"horizontal extent in {PITCH:.0f}-unit cells: "
          f"min {hs[0]:.1f}  p50 {hs[len(hs) // 2]:.1f}  max {hs[-1]:.1f}\n")
        small = [m for m in ok if m.cells <= 2.0]
        w(f"{len(small)} model(s) are 2 cells or under\n")
    w("\n")
    rows = models
    if max_cells is not None:
        rows = [m for m in rows if m.cells is not None and m.cells <= max_cells]
        w(f"filtered to {len(rows)} model(s) at most {max_cells} cells wide\n")
    if top:
        rows = sorted(rows, key=lambda m: -m.placed)[:top]
    w(f"{'idx':>4} {'file id':>10} {'cells':>7} {'height':>8} {'aspect':>7} "
      f"{'placed':>7} {'verts':>7} {'tris':>7}  note\n")
    for m in rows:
        if m.extent is None:
            w(f"{m.index:>4} 0x{m.file_id:08X} {'--':>7} {'--':>8} {'--':>7} "
              f"{m.placed:>7} {'--':>7} {'--':>7}  {m.error}\n")
            continue
        w(f"{m.index:>4} 0x{m.file_id:08X} {m.cells:>7.2f} {m.height:>8.0f} "
          f"{m.aspect:>7.1f} {m.placed:>7} {m.n_verts:>7} {m.n_tris:>7}  "
          f"{'' if fits_pitch(m) else 'wider than one placement cell'}\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--area", help="read the donor named by a content area")
    ap.add_argument("--donor-row", type=int,
                    help="the donor map's head row, if not naming an area")
    ap.add_argument("--dat", help="archive to read (default: the study copy)")
    ap.add_argument("--max-cells", type=float,
                    help="list only models at most this many cells wide")
    ap.add_argument("--top", type=int,
                    help="list only the N the donor places most often")
    a = ap.parse_args(argv)
    if not a.area and a.donor_row is None:
        ap.error("name an --area or a --donor-row")

    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "authsrv"))
    import archive as ar_mod
    import deploy
    import vaultpath
    path = a.dat or vaultpath.vault_path("dat_study", "Gw.dat")
    ar = ar_mod.Archive(path)
    print(f"archive: {path}")

    row = a.donor_row
    if a.area:
        import content
        area = content.load().rows("area")[a.area]
        row = deploy._row_for(ar, area, "donor_file_id", "donor_row", None,
                              "donor") if hasattr(deploy, "_row_for") \
            else area.get("donor_row")
        print(f"area {a.area}: donor row {row}")
    models = scan(ar, deploy._stripped_of(ar, int(row), "donor"))
    report(models, max_cells=a.max_cells, top=a.top)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
