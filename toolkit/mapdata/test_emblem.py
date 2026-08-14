#!/usr/bin/env python3
"""Check the authored profession emblem against the sheet it has to sit in.

    python toolkit/mapdata/test_emblem.py

`emblem.py` is art, and most of what makes art right is not testable. What IS
testable is the set of MEASURED numbers its docstring claims about ArenaNet's
sheet -- and those are exactly the claims that would rot silently, because a
wrong one produces an emblem that still looks fine on its own and reads wrong
in the row. So sections 2 and 3 re-measure them from the archive rather than
trusting the constants, and every threshold here is a number a green run
produced (2026-08-14), not a guess.

THE TRAP THIS FILE EXISTS FOR. `emblem.cell()` returns BGRA, because that is
what the DDS stores -- dword masks `R=0x00FF0000 G=0x0000FF00 B=0x000000FF`,
which is byte order B,G,R,A. Getting that backwards produces a perfectly
plausible image with the red and blue channels swapped: our violet bolt would
render orange, and nothing about the file size, the alpha or the luma would
change. Section 1 pins the channel order against the emblem's own declared
palette, which is the only check here that a channel swap fails.

Sections 0-1 need no vault. Sections 2-3 read `vault/dat_study/Gw.dat` and
declare a skip without it.
"""

import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import checks                                                    # noqa: E402
import emblem                                                    # noqa: E402
import vaultpath                                                 # noqa: E402

# MEASURED from green runs 2026-08-14: 11 with no vault, 17 with one. The first
# version GUESSED 12/18 and reported "1 did not execute" on a vault-less run
# where nothing was skipped beyond the two declared sections -- the same mistake
# test_glyphs.py made hours earlier, in the same session, after recording it.
LEDGER = checks.Ledger("profession emblem", floor=11)
check = checks.adopt(LEDGER)

SHEET_ID = 152638           # the glyph sheet, RESKIN 22
FRAMES = (14, 15)           # profession 8, from the jump table at VA 0x005A5EB8
CELL = emblem.CELL


def guarded(fn):
    try:
        fn()
    except Exception as exc:                                     # noqa: BLE001
        check(False, "section %s completed" % fn.__name__,
              "%s: %s" % (type(exc).__name__, exc))


def luma(c):
    s = 0.0
    for k in range(0, len(c), 4):
        b, g, r, a = c[k:k + 4]
        s += (0.299 * r + 0.587 * g + 0.114 * b) * (a / 255.0)
    return s / (CELL * CELL)


def alpha_profile(c):
    al = [c[k + 3] for k in range(0, len(c), 4)]
    return (sum(1 for v in al if v == 255),
            sum(1 for v in al if 0 < v < 255),
            sum(1 for v in al if v == 0))


def section_shape():
    print("\n== 0. shape and purity ==")
    lit, dim = emblem.pair()
    for name, c in (("lit", lit), ("dim", dim)):
        check(len(c) == CELL * CELL * 4, "%s cell is %d bytes" % (name, CELL * CELL * 4),
              len(c))
    check(emblem.pair()[0] == lit and emblem.cell(True) == lit,
          "cell() is pure -- same bytes every call")
    check(lit != dim, "the lit and dim frames differ")
    check(emblem.cell(False) == dim, "and cell(False) is the dim one")


def section_channels():
    print("\n== 1. BGRA byte order -- the check a channel swap fails ==")
    lit = emblem.cell(True)
    # The bolt core is near-white but the MID is strongly violet: red and blue
    # high, green low. Find the texel closest to BOLT_MID and read its bytes.
    want = emblem.BOLT_MID
    best, bo = None, 0
    for k in range(0, len(lit), 4):
        b, g, r, a = lit[k:k + 4]
        if a != 255:
            continue
        d = ((r / 255.0 - want[0]) ** 2 + (g / 255.0 - want[1]) ** 2
             + (b / 255.0 - want[2]) ** 2)
        if best is None or d < best:
            best, bo = d, k
    b, g, r, a = lit[bo:bo + 4]
    check(best is not None and best < 0.02,
          "some texel matches BOLT_MID under a BGRA reading", "%.4f" % (best or -1))
    check(b > g and r > g,
          "and it is violet -- blue and red above green, which a channel swap "
          "keeps true only by accident", (b, g, r))
    # The decisive one: BOLT_MID is more blue than red, so B must exceed R.
    check(want[2] > want[0] and b > r,
          "B exceeds R, matching the declared palette -- an RGBA writer would "
          "put the larger value in the first byte and fail here", (b, r))


def section_ratio():
    print("\n== 2. the lit/dim ratio, against the sheet's own band ==")
    lit, dim = emblem.pair()
    ours = luma(dim) / luma(lit)
    try:
        dat = vaultpath.vault_path("dat_study", "Gw.dat")
    except SystemExit:
        dat = None
    if not (dat and os.path.exists(dat)):
        LEDGER.skip("section 2: no vault", "the band is re-measured from the sheet")
        check(0.687 <= ours <= 0.788,
              "ours sits in the recorded band 0.687-0.788", "%.3f" % ours)
        return
    from mapdata import archive as arch                          # noqa: E402
    a = arch.Archive(dat)
    try:
        blob = a.read(a.row(arch.file_id_table(a)[SHEET_ID]))
    finally:
        a.close()
    h, w = struct.unpack_from("<II", blob, 12)
    px = blob[128:]
    cols = w // CELL

    def cellbytes(i):
        cy, cx = divmod(i, cols)
        out = bytearray()
        for y in range(CELL):
            o = ((cy * CELL + y) * w + cx * CELL) * 4
            out += px[o:o + CELL * 4]
        return bytes(out)

    check((w, h) == (256, 128) and blob[:4] == b"DDS ",
          "the sheet is still a 256x128 DDS", (blob[:4], w, h))
    ratios = []
    for p in range(11):
        x, y = luma(cellbytes(2 * p)), luma(cellbytes(2 * p + 1))
        if x:
            ratios.append(y / x)
    check(len(ratios) == 11, "eleven lit/dim pairs measured", len(ratios))
    lo, hi = min(ratios), max(ratios)
    check(0.60 < lo and hi < 0.85,
          "the sheet's own band is where the docstring says", "%.3f..%.3f" % (lo, hi))
    check(lo <= ours <= hi,
          "and ours falls INSIDE the sheet's measured band -- re-measured, not "
          "compared against a copied constant", "%.3f in %.3f..%.3f" % (ours, lo, hi))


def section_alpha():
    print("\n== 3. the alpha disc, and that we overwrite only our own cells ==")
    lit = emblem.cell(True)
    op, part, clear = alpha_profile(lit)
    check(op + part + clear == CELL * CELL, "alpha accounts for every texel",
          (op, part, clear))
    check(op > 600 and clear > 100,
          "it is a filled disc, not a full square and not empty", (op, clear))
    try:
        dat = vaultpath.vault_path("dat_study", "Gw.dat")
    except SystemExit:
        dat = None
    if not (dat and os.path.exists(dat)):
        LEDGER.skip("section 3: no vault", "the disc is compared to the sheet's")
        return
    from mapdata import archive as arch                          # noqa: E402
    a = arch.Archive(dat)
    try:
        blob = a.read(a.row(arch.file_id_table(a)[SHEET_ID]))
    finally:
        a.close()
    h, w = struct.unpack_from("<II", blob, 12)
    px = blob[128:]
    cols = w // CELL

    def cellbytes(i):
        cy, cx = divmod(i, cols)
        out = bytearray()
        for y in range(CELL):
            o = ((cy * CELL + y) * w + cx * CELL) * 4
            out += px[o:o + CELL * 4]
        return bytes(out)

    theirs = [alpha_profile(cellbytes(i)) for i in range(32)]
    check(len({t for t in theirs}) == 1,
          "every one of the 32 cells shares one alpha profile", theirs[0])
    top, tpart, tclear = theirs[0]
    check(abs(op - top) < 60,
          "and ours has the same opaque area to within 60 texels",
          "ours %d, theirs %d" % (op, top))
    # The splice must land on OUR frames and nowhere else -- the property the
    # arming script asserted before writing, restated here so it cannot rot.
    check(FRAMES == (14, 15) and all(f // cols == 1 and f % cols in (6, 7)
                                     for f in FRAMES),
          "profession 8's frames are row 1, columns 6-7", FRAMES)


def main():
    print("=" * 70)
    print("PROFESSION EMBLEM -- the authored Stormcaller glyph")
    print("=" * 70)
    for fn in (section_shape, section_channels, section_ratio, section_alpha):
        guarded(fn)
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
