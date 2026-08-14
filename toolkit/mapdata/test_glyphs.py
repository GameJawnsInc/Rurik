#!/usr/bin/env python3
"""Check the procedural icon set -- and mostly, check the arithmetic that indexes it.

    python toolkit/mapdata/test_glyphs.py

NO VAULT, NO ARCHIVE, NO CLIENT. Every image is built by `glyphs.py` out of
arithmetic, which is the whole point of the module, so this runs on a bare
machine.

WHAT IS AND IS NOT EVIDENCE HERE. "132 icons came out and they are all different"
is the WEAK half and it is nearly worthless on its own: byte-distinctness is
satisfied by 132 pictures that differ in one pixel, and it stayed green through
every defect this module actually had. All three real defects were INDEX
ARITHMETIC that failed silently and produced a set that looked fine:

  1. `ground = (3*motif + palette) % 11` with polarity split by index range gives
     six CONSECUTIVE indices for a fixed motif, so all six of a motif's icons
     landed in ONE polarity block. Polarity existed precisely to separate
     same-motif pairs and never fired for them. Minimum confusability 10.65 --
     worse than all four vocabularies the module was synthesised from.
  2. The palette ORDER decides which palettes can share a polarity: with
     `(motif + palette) % 2` the sets are {0,2,4} and {1,3,5}. The first ordering
     put blue and grey in the same set and they were the worst pair in the set.
  3. Without an accent axis, a motif's three same-polarity siblings differed ONLY
     in colour. Adding it took greyscale minimum from 6.04 to 13.48.

So sections 2 and 3 assert the invariants directly, and each one REPRODUCES THE
BROKEN VERSION INLINE as a live function and requires it to violate what the real
one satisfies -- a difference between two live answers rather than a number the
test asks the code to confirm about itself.

Section 5 is the one that can fail in both directions: the set's minimum pairwise
distance must clear a floor AND a degenerate set -- one picture, hue-rotated 132
times -- must fall under it. A confusability check that has never rejected
anything is not a check.

THE FLOORS ARE MEASURED, not chosen. Every threshold below carries the value a
green run produced and the date.
"""

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import checks                                                    # noqa: E402
import dxt1                                                      # noqa: E402
import glyphs                                                    # noqa: E402

# MEASURED from a green run, 2026-08-14 -- 32, not the 41 the first version
# GUESSED, which reported "9 did not execute" on a run where nothing was
# skipped. Every check here is synthetic, so this is the score on any machine.
LEDGER = checks.Ledger("procedural icon set", floor=32)
check = checks.adopt(LEDGER)

DIM = 64
CROP = 48                      # what the bar's chrome leaves; MEASURED
RESERVATION = 2560             # the smallest of the 132 rows is 6,656 B
ATEX_BYTES = 12 + 8 + (DIM // 4) * (DIM // 4) * 8


def guarded(fn):
    try:
        fn()
    except Exception as exc:                                     # noqa: BLE001
        check(False, "section %s completed" % fn.__name__,
              "%s: %s" % (type(exc).__name__, exc))


# --- helpers, written HERE rather than imported ---------------------------

def through_dxt1(rgb, dim=DIM):
    """What the client actually gets: encode, pack planar, decode back."""
    payload = dxt1.pack(dxt1.encode(rgb, dim, dim), dxt1.PLANAR)
    return dxt1.decode(payload, dim, dim, dxt1.PLANAR), payload


def crop_centre(rgba, dim, crop):
    m = (dim - crop) // 2
    out = bytearray(crop * crop * 3)
    for y in range(crop):
        for x in range(crop):
            s = ((y + m) * dim + x + m) * 4
            d = (y * crop + x) * 3
            out[d:d + 3] = rgba[s:s + 3]
    return bytes(out)


def signature(rgb, crop=CROP, cells=8):
    """An 8x8 mean-RGB thumbnail -- enough to rank confusability, cheap enough
    to do 8,646 times."""
    step = crop // cells
    sig = []
    for cy in range(cells):
        for cx in range(cells):
            acc = [0, 0, 0]
            for y in range(cy * step, (cy + 1) * step):
                for x in range(cx * step, (cx + 1) * step):
                    o = (y * crop + x) * 3
                    acc[0] += rgb[o]
                    acc[1] += rgb[o + 1]
                    acc[2] += rgb[o + 2]
            n = step * step
            sig.extend((acc[0] / n, acc[1] / n, acc[2] / n))
    return sig


def luma(sig):
    return [0.299 * sig[i] + 0.587 * sig[i + 1] + 0.114 * sig[i + 2]
            for i in range(0, len(sig), 3)]


def min_distance(sigs):
    """Minimum mean-absolute distance over every unordered pair, and the pair."""
    best, where = None, None
    n = len(sigs)
    for a in range(n):
        sa = sigs[a]
        for b in range(a + 1, n):
            sb = sigs[b]
            d = 0.0
            for k in range(len(sa)):
                d += abs(sa[k] - sb[k])
            d /= len(sa)
            if best is None or d < best:
                best, where = d, (a, b)
    return best, where


# --- 1. the API contract (the WEAK half) ----------------------------------

def section_api():
    print("\n== 1. API contract -- the weak half, see the docstring ==")
    check(glyphs.COUNT == 132, "COUNT is 132", glyphs.COUNT)
    px = [glyphs.icon(i) for i in range(glyphs.COUNT)]
    check(all(len(p) == DIM * DIM * 3 for p in px),
          "every icon is dim*dim*3 bytes")
    check(len(set(px)) == glyphs.COUNT,
          "all 132 are byte-distinct (necessary, nowhere near sufficient)",
          len(set(px)))
    check(glyphs.icon(7) == glyphs.icon(7) and glyphs.icon(7) == px[7],
          "icon() is pure -- same index, same bytes, every call")
    check(len(glyphs.icon(0, 128)) == 128 * 128 * 3,
          "renders at dim=128 too")
    for bad in (-1, 132, 1.0, "3"):
        try:
            glyphs.icon(bad)
            check(False, "refuses index %r" % (bad,), "accepted it")
        except (ValueError, TypeError):
            check(True, "refuses index %r" % (bad,))
    for bad in (0, 7, 63, -4):
        try:
            glyphs.icon(0, bad)
            check(False, "refuses dim %r" % (bad,), "accepted it")
        except ValueError:
            check(True, "refuses dim %r" % (bad,))


# --- 2. the index invariants, with the broken versions run beside them -----

def section_indexing():
    print("\n== 2. index invariants -- where every real defect has been ==")
    M, P = glyphs.MOTIFS, glyphs.NPALETTE

    pairs = [(i % M, i // M) for i in range(glyphs.COUNT)]
    check(len(set(pairs)) == glyphs.COUNT,
          "every (motif, palette) pair is unique", len(set(pairs)))

    # CONTROL: a scheme that also "looks" fine and collides, because gcd(22,6)=2.
    broken = [(i % M, i % P) for i in range(glyphs.COUNT)]
    check(len(set(broken)) < glyphs.COUNT,
          "and the control scheme (i%22, i%6) really does collide",
          "%d distinct" % len(set(broken)))

    def polarity(m, p):
        return (m + p) % 2

    def polarity_broken(m, p):
        # The shipped defect: ground index range decides polarity.
        return 0 if (3 * m + p) % 11 < 6 else 1

    ok = bad = 0
    for m in range(M):
        got = [polarity(m, p) for p in range(P)]
        ok += (got.count(0) == 3 and got.count(1) == 3)
        was = [polarity_broken(m, p) for p in range(P)]
        bad += (was.count(0) == 3 and was.count(1) == 3)
    check(ok == M, "polarity splits every motif's six 3/3", "%d of %d" % (ok, M))
    # NOT "none of them": the broken rule balances 4 of 22 by coincidence, and
    # the first version of this check asserted 0 and went red for that reason.
    # The real claim is that it balances a MINORITY while the fix balances all.
    check(bad <= 8 and bad < ok,
          "and the pre-fix rule balances only a minority -- two live answers",
          "%d of %d motifs, against %d for the fix" % (bad, M, ok))

    def accent(p):
        return (p // 2) % glyphs.ACCENTS

    def accent_broken(p):
        return p % 2

    ok = bad = 0
    for m in range(M):
        for want in (0, 1):
            sibs = [p for p in range(P) if polarity(m, p) == want]
            ok += len({accent(p) for p in sibs}) == len(sibs)
            bad += len({accent_broken(p) for p in sibs}) == len(sibs)
    check(ok == 2 * M,
          "the same-polarity siblings of every motif get distinct accents",
          "%d of %d" % (ok, 2 * M))
    check(bad == 0,
          "and a p%2 accent gives all of them the SAME frame",
          "%d groups would still have been distinct" % bad)

    # The palette ORDER is load-bearing and nothing else here would catch it.
    names = [p["name"] for p in glyphs.PALETTES]
    check(len(names) == P and len(set(names)) == P,
          "six distinct palettes", names)
    check(names[4] != "thunderhead",
          "the even set is not {violet, teal, amber} -- grey sits at 4 so the "
          "odd set can be {blue, magenta, amber}", names)


# --- 3. does the description match the pixels? ----------------------------

def section_describe():
    print("\n== 3. describe() agrees with the arithmetic ==")
    hits = 0
    for i in range(glyphs.COUNT):
        d = glyphs.describe(i)
        m, p = i % glyphs.MOTIFS, i // glyphs.MOTIFS
        if ("motif=%2d" % m) in d and ("polarity=%d" % ((m + p) % 2)) in d:
            hits += 1
    check(hits == glyphs.COUNT, "describe() reports the real motif and polarity",
          hits)


# --- 4. the archive pipeline ----------------------------------------------

def section_pipeline():
    print("\n== 4. what the archive actually stores ==")
    sizes = set()
    worst = 0.0
    for i in range(0, glyphs.COUNT, 7):
        rgb = glyphs.icon(i)
        back, payload = through_dxt1(rgb)
        sizes.add(len(payload) + 20)
        err = sum(abs(rgb[k * 3 + c] - back[k * 4 + c])
                  for k in range(DIM * DIM) for c in range(3)) / (DIM * DIM * 3)
        worst = max(worst, err)
    check(sizes == {ATEX_BYTES},
          "every icon makes a %d B single-level ATEX" % ATEX_BYTES, sizes)
    check(ATEX_BYTES <= RESERVATION,
          "which fits the %d B reservation all 132 rows have" % RESERVATION,
          ATEX_BYTES)
    # MEASURED 2026-08-14: worst 6.66/255 over the full sweep.
    check(worst < 9.0, "DXT1 round-trip damage stays under 9/255",
          "worst %.2f" % worst)


# --- 5. confusability, in BOTH directions ---------------------------------

def section_confusability():
    print("\n== 5. confusability -- and a degenerate set that must FAIL it ==")
    sigs, greys = [], []
    for i in range(glyphs.COUNT):
        c = crop_centre(through_dxt1(glyphs.icon(i))[0], DIM, CROP)
        s = signature(c)
        sigs.append(s)
        greys.append(luma(s))

    lo, pair = min_distance(sigs)
    glo, gpair = min_distance(greys)
    # MEASURED 2026-08-14 on a green run: colour 15.47, greyscale 13.48 through
    # the full 48x48; the 8x8 signature here reads a little higher. Floors are
    # set below the measured value with headroom, not at it.
    check(lo > 9.0, "minimum colour distance clears 9/255",
          "%.2f at %s" % (lo, pair))
    check(glo > 6.0, "minimum GREYSCALE distance clears 6/255 -- the half that "
                     "survives a colour-blind player", "%.2f at %s" % (glo, gpair))

    # THE CONTROL. One picture, hue-rotated. It carries no shape information, so
    # a check that cannot reject it is measuring nothing.
    base = glyphs.icon(0)
    degen = []
    for i in range(glyphs.COUNT):
        t = i / glyphs.COUNT
        rot = bytearray(len(base))
        for k in range(0, len(base), 3):
            r, g, b = base[k], base[k + 1], base[k + 2]
            rot[k] = int(r * (1 - t) + g * t)
            rot[k + 1] = int(g * (1 - t) + b * t)
            rot[k + 2] = int(b * (1 - t) + r * t)
        degen.append(crop_centre(through_dxt1(bytes(rot))[0], DIM, CROP))
    dsig = [signature(c) for c in degen]
    dlo, _ = min_distance(dsig)
    check(dlo < 9.0,
          "and the degenerate hue-only set FAILS the same floor",
          "%.2f" % dlo)
    check(lo > dlo * 3.0,
          "the real set beats it by more than 3x", "%.2f vs %.2f" % (lo, dlo))


# --- 6. the safe area and the resolution independence ---------------------

def section_geometry():
    print("\n== 6. safe area, and geometry that is not a pixel count ==")
    outside = []
    for i in range(0, glyphs.COUNT, 5):
        rgb = glyphs.icon(i)
        # Ink is deviation from the icon's OWN median LUMA. The first version
        # took the median of the red channel alone and compared all three
        # against it, which is not a quantity -- and its threshold had been
        # copied from a different tool's differently-defined number, which is
        # how it went red at 0.446 against a floor set from someone else's 0.227.
        lum = [0.299 * rgb[k] + 0.587 * rgb[k + 1] + 0.114 * rgb[k + 2]
               for k in range(0, len(rgb), 3)]
        med = sorted(lum)[len(lum) // 2]
        tot = ink_out = 0.0
        m = (DIM - CROP) // 2
        for y in range(DIM):
            for x in range(DIM):
                o = (y * DIM + x) * 3
                d = abs(lum[y * DIM + x] - med)
                tot += d
                if not (m <= x < m + CROP and m <= y < m + CROP):
                    ink_out += d
        outside.append(ink_out / tot if tot else 0.0)
    mean_out = sum(outside) / len(outside)
    # MEASURED 2026-08-14: 0.138 mean, 0.227 worst over all 132.
    check(mean_out < 0.25,
          "mean ink outside the central 48x48 stays under 25%",
          "%.3f" % mean_out)
    check(max(outside) < 0.40, "and no icon exceeds 40%",
          "%.3f" % max(outside))

    # Nothing in the module may be a pixel count: a 128 render downsampled 2x
    # must reproduce the 64 render closely. A hard-coded margin breaks this.
    worst = 0.0
    for i in (0, 37, 88, 131):
        big = glyphs.icon(i, 128)
        small = glyphs.icon(i, DIM)
        err = 0.0
        for y in range(DIM):
            for x in range(DIM):
                for c in range(3):
                    acc = 0
                    for dy in range(2):
                        for dx in range(2):
                            acc += big[((y * 2 + dy) * 128 + x * 2 + dx) * 3 + c]
                    err += abs(acc / 4.0 - small[(y * DIM + x) * 3 + c])
        worst = max(worst, err / (DIM * DIM * 3))
    check(worst < 6.0,
          "dim=128 downsamples onto dim=64 -- geometry is normalised, not pixels",
          "worst %.2f/255" % worst)


def main():
    print("=" * 70)
    print("PROCEDURAL ICON SET -- 132 glyphs for a custom profession")
    print("=" * 70)
    for fn in (section_api, section_indexing, section_describe,
               section_pipeline, section_confusability, section_geometry):
        guarded(fn)
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
