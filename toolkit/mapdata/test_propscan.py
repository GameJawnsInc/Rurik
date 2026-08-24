r"""The prop-model catalogue, and the fit check `deploy.py` never had.

    python toolkit/mapdata/test_propscan.py

WHAT THIS IS AGAINST. WORLDMAPS-W24 authored a place, served it, and the owner
walked it: "the biome donor's model 0 is a monumental building, not a tree --
32 of them scattered like shrubs loom one-sided over the bowl". `deploy.py`
could place exactly one model and had no say in which, and nothing in the
toolkit could tell an author what that model WAS.

So the checks are in two halves:

  1-2  the ARITHMETIC, against synthetic geometry: a bounding box, an aspect
       ratio, extent in placement cells, and `fits_pitch` refusing to answer
       True for a model it could not measure. No archive.
  3    the ARCHIVE, against the real donor: 229 models, all decodable, and the
       one number that matters -- model 0 is SIXTEEN placement cells wide.
       Skips with its reason without a vault.

The `fits_pitch` None case is the one worth reading. "We could not read this
model" and "this model fits" are different answers and only one of them is a
licence to place 32 copies of it; a boolean would have collapsed them.
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import checks                                                    # noqa: E402
import propscan                                                  # noqa: E402

# Floor = the mandatory core: sections 1-2 need no vault. Section 3 does and
# declares a skip. Measured from a green run, never guessed.
LEDGER = checks.Ledger("prop scan", floor=11)
check = checks.adopt(LEDGER)

P = propscan.PropModel

print("== 1. the measured numbers, on models whose answers are known ==")
tree = P(77, 0x1B85C, row=1, extent=(80.6, 76.8, 619.0), n_verts=44,
         n_tris=43, n_submodels=1, placed=12)
build = P(0, 0x1B6B3, row=2, extent=(1536.1, 690.9, 963.0), n_verts=1538,
          n_tris=1172, n_submodels=4, placed=3)
dead = P(9, 0xDEAD, error="Undecodable: synthetic")

check(abs(tree.horizontal - 80.6) < 1e-6 and abs(build.horizontal - 1536.1) < 1e-4,
      "horizontal extent is the LARGER ground-plane axis, not x -- a model "
      "long in y and thin in x still occupies its long axis on the grid",
      f"{tree.horizontal} / {build.horizontal}")
check(abs(tree.cells - 80.6 / 96.0) < 1e-9 and abs(build.cells - 16.0) < 0.01,
      "and it converts to PLACEMENT CELLS, which is the actionable unit: "
      "model 0 is 16.0 cells wide against a 96-unit pitch",
      f"{tree.cells:.2f} / {build.cells:.2f}")
check(round(tree.aspect, 1) == 7.7 and round(build.aspect, 2) == 0.63,
      "aspect (height / horizontal) separates the two populations where size "
      "alone does not -- a big landmark and a big tree are both big",
      f"{tree.aspect:.2f} / {build.aspect:.2f}")
check(propscan.fits_pitch(tree) is True
      and propscan.fits_pitch(build) is False,
      "fits_pitch: the 0.84-cell model fits the grid, the 16-cell one does "
      "not. THIS is the check W24 did not have")
check(propscan.fits_pitch(dead) is None,
      "and an UNMEASURABLE model answers None, never True -- 'we could not "
      "read it' and 'it fits' are different answers and only one is a "
      "licence to place 32 copies",
      f"{propscan.fits_pitch(dead)!r}")
check(dead.cells is None and dead.horizontal is None and dead.aspect is None,
      "an unmeasurable model reports None for every derived number rather "
      "than a zero that would sort first and read as tiny")
check(propscan.fits_pitch(tree, pitch_cells=0.5) is False,
      "and the fit bound is a PARAMETER: at half a cell the same model no "
      "longer fits, so a denser placement can ask a stricter question")

print("\n== 2. the report says what it measured, and what it could not ==")
buf = io.StringIO()
propscan.report([tree, build, dead], out=buf)
blob = buf.getvalue()
check("3 prop model(s), 2 measured, 1 unreadable" in blob,
      "the header counts measured against unreadable, so a scan that could "
      "read almost nothing cannot be skimmed as a full catalogue", blob[:200])
check("wider than one placement cell" in blob,
      "the oversize model is FLAGGED in the listing, not left for the reader "
      "to divide 1536 by 96")
check("Undecodable: synthetic" in blob,
      "and the unreadable one is listed WITH its error rather than dropped -- "
      "an author choosing by index needs the indices to stay put")
buf2 = io.StringIO()
propscan.report([tree, build, dead], out=buf2, max_cells=1.0)
check("filtered to 1 model(s)" in buf2.getvalue(),
      "--max-cells filters to what will actually fit, which is the query an "
      "author has when they want scatter vegetation",
      buf2.getvalue()[:300])

print("\n== 3. the real donor: 229 models, and model 0 is the building ==")
try:
    sys.path.insert(0, os.path.dirname(HERE))
    import archive as ar_mod
    import deploy
    import vaultpath
    path = vaultpath.vault_path("dat_study", "Gw.dat")
    with ar_mod.Archive(path) as ar:
        models = propscan.scan(ar, deploy._stripped_of(ar, 7982, "donor"))
except Exception as exc:                                        # noqa: BLE001
    LEDGER.skip("the archive scan", f"study archive unavailable: {exc}")
else:
    ok = [m for m in models if m.extent is not None]
    check(len(models) == 229 and len(ok) == 229,
          f"Pre-Searing lists 229 prop models and ALL 229 decode -- "
          f"`deploy.py` reached exactly one of them until today",
          f"{len(models)} listed, {len(ok)} measured")
    m0 = models[0]
    check(round(m0.cells, 1) == 16.0 and m0.file_id == 0x1B6B3,
          f"model 0 -- what every area this toolkit ever authored placed -- "
          f"is {m0.cells:.1f} placement cells wide and {m0.height:.0f} tall. "
          f"That is W24's 'monumental building', as a number",
          f"0x{m0.file_id:X} {m0.cells:.2f} cells")
    check(propscan.fits_pitch(m0) is False,
          "and it does NOT fit the placement grid, so the report fires on "
          "every area that still uses it")
    m77 = models[77]
    check(propscan.fits_pitch(m77) is True and m77.aspect > 5,
          f"model 77, which `area.ashcoil` now names, DOES fit and is "
          f"{m77.aspect:.1f}x taller than wide -- the two properties the row "
          f"claims, checked against the archive rather than the comment",
          f"{m77.cells:.2f} cells, aspect {m77.aspect:.1f}")
    check(sum(m.placed for m in models) == 864,
          "the donor's own map places 864 props across those models -- the "
          "placement counts are read, not defaulted to zero",
          f"{sum(m.placed for m in models)}")
    # THE WEAK SIGNAL, pinned with its strength -- and this check went RED on
    # its first form, which is why it is written this way. That form compared
    # the ten most-placed models against "the ten least-placed" and concluded
    # NO correlation. But 91 of the 229 are placed exactly once, so which ten
    # you get is a tie-break: one arbitrary slice gives mean 926, another
    # 4163. The conclusion was an artifact of the sort, not a fact about the
    # archive. Measured properly instead, over ALL 229 and with no ties to
    # break. [[feedback-error-bars-before-conclusions]]
    def _rank(vals):
        order = sorted(range(len(vals)), key=lambda i: vals[i])
        r = [0] * len(vals)
        for pos, i in enumerate(order):
            r[i] = pos
        return r

    n = len(ok)
    rx, ry = _rank([m.placed for m in ok]), _rank([m.horizontal for m in ok])
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((rx[i] - mx) * (ry[i] - my) for i in range(n))
    den = ((sum((rx[i] - mx) ** 2 for i in range(n))
            * sum((ry[i] - my) ** 2 for i in range(n))) ** 0.5)
    rho = num / den
    check(-0.40 < rho < -0.05,
          f"placement count is a WEAK size signal, not a proxy: Spearman rho "
          f"{rho:+.3f} over all {n} models. Retail does place its smaller "
          f"props more often, but nowhere near tightly enough to select on",
          f"rho {rho:+.3f}")
    many = sorted(m.horizontal for m in ok if m.placed >= 10)
    med = many[len(many) // 2]
    check(med / propscan.PITCH > 4.0,
          f"and THIS is why that matters: even among the {len(many)} models "
          f"retail places ten or more times, the median is "
          f"{med / propscan.PITCH:.1f} placement cells wide. Choosing the "
          f"most POPULAR model would not have avoided W24 either -- only "
          f"measuring the size does",
          f"median {med:.0f} units = {med / propscan.PITCH:.1f} cells")

sys.exit(LEDGER.verdict())
