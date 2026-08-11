"""Check `trnshadow.py` against real terrain bytes, and against its own controls.

    python toolkit/mapdata/test_trnshadow.py
    python toolkit/mapdata/test_trnshadow.py --all        # all 349 maps, slow

WHAT IS BEING CHECKED, and why each part could go red.

  1. The codec's laws, on bitmaps this file builds itself. No archive bytes are
     needed and none are stored here -- the two rules ArenaNet's emitter has and
     a naive one does not (the leading zero-length run, and 254 being one byte
     rather than 0xFF followed by nothing) are exercised on synthetic rows, and
     so are the three ways a malformed payload must be refused.

  2. The same codec against `Gw.dat`. This is the part that is evidence: the
     decoder throws the bytes away and `encode_rows` rebuilds them from the
     bitmap alone, so a byte-identical result on retail blocks is a statement
     about ArenaNet's writer, not about ours. A round-trip through opaque bytes
     would prove framing and nothing else, which is exactly what `terrain.py`
     already had and why this module exists.

  3. The tail rule, WITH its controls. `tail_from_rows` predicting the stored
     128 bytes is only interesting because the neighbouring window widths do
     not: section 3 asserts that pad 0 and pad 2 both disagree on real blocks.
     Without that, "our rule reproduces the tail" would be a claim with no
     alternative it beat.

  4. Polarity. A set bit meaning IN SHADOW is not a convention we may choose --
     it is checked against a different record, tag 9's lightmap, on the
     reference map. Cells whose tail bit is set must be darker.

FIXTURE. `Gw.dat` is read out of the vault by `vaultpath`, never by a relative
walk, and every archive-backed section declares a skip if it is not there. The
file itself is opened `rb` and this test writes nothing.
"""

import argparse
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import Archive, file_id_table                 # noqa: E402
from terrain import Terrain, CHUNK_SIZE                    # noqa: E402
import trnshadow                                           # noqa: E402
import checks                                              # noqa: E402
import vaultpath                                           # noqa: E402

SMALL_FILE_ID = 0x22E2C          # row 46196, the smallest complete map
KAMADAN_FILE_ID = 0x345CC        # row 22371

# MEASURED 2026-08-11 on vault/dat_study/Gw.dat.
SMALL_BLOCK_K = 544              # 272 rows x (0xFF, 0x12) -- an unshadowed block
EDGE = trnshadow.BLOCK_EDGE      # 272

DEFAULT_SAMPLE = 8

# FLOOR: 24 -- what a green run executes, and it does not vary with --sample or
# --all, which change how many blocks each check walks and not how many checks
# run. MEASURED from a real run on vault/dat_study/Gw.dat, 2026-08-11: 14 in
# section 1 (synthetic, always run), 5 in section 2, 3 in section 3, 2 in
# section 4. A run with no archive declares one skip and scores 14, which is
# below the floor and therefore RED -- deliberately, because the synthetic half
# alone cannot refute anything about ArenaNet's format.
LEDGER = checks.Ledger("terrain tag 7 shadow codec", floor=24)
check = checks.adopt(LEDGER)


def _blank_rows():
    return [0] * EDGE


def _full_rows():
    return [(1 << EDGE) - 1] * EDGE


def section_codec():
    print("\n1. The run coding, on bitmaps this file builds")

    blank = _blank_rows()
    enc = trnshadow.encode_rows(blank)
    check(enc == bytes([0xFF, 0x12]) * EDGE,
          "an unshadowed block is 272 rows of one 272-run",
          f"{len(enc)} bytes")
    check(len(enc) == SMALL_BLOCK_K,
          "and that is the k retail ships for a flat 32x32 map",
          f"{len(enc)} vs {SMALL_BLOCK_K}")
    check(trnshadow.decode_rows(enc) == blank, "it decodes back to all-clear")

    full = _full_rows()
    encf = trnshadow.encode_rows(full)
    check(encf == bytes([0x00, 0xFF, 0x12]) * EDGE,
          "a fully shadowed row opens with a zero-length run",
          f"first bytes {encf[:3].hex()}")
    check(trnshadow.decode_rows(encf) == full,
          "and the zero-length run decodes away again")

    # The two run lengths whose encoding a naive writer gets wrong.
    rows = _blank_rows()
    rows[0] = ((1 << 254) - 1) << 1                      # one run of exactly 254
    got = trnshadow.encode_rows(rows)
    check(got[:3] == bytes([0x01, 0xFE, 0x11]),
          "a run of exactly 254 is one 0xFE byte, not 0xFF 0x00",
          f"{got[:3].hex()}")
    rows[0] = ((1 << 255) - 1) << 1                      # one run of 255
    got = trnshadow.encode_rows(rows)
    check(got[:4] == bytes([0x01, 0xFF, 0x01, 0x10]),
          "a run of 255 is 0xFF then 1", f"{got[:4].hex()}")

    for name, payload in (
            ("a run that overruns its row", bytes([0xFF, 0xFF, 0x13])),
            ("a payload that stops mid-row", bytes([0x40])),
            ("a payload one row short", bytes([0xFF, 0x12]) * (EDGE - 1))):
        try:
            trnshadow.decode_rows(payload)
            ok = False
        except ValueError:
            ok = True
        check(ok, f"decode refuses {name}")

    check(trnshadow.tail_from_rows(blank) == bytes(128),
          "an unshadowed block's derived tail is all zero")
    check(trnshadow.tail_from_rows(full) == b"\xff" * 128,
          "a fully shadowed block's derived tail is all ones")

    # One cell shadowed exactly, with no skirt: the 10x10 window is not full, so
    # the flag must stay clear. Widen it by one sample all round and it sets.
    ox, oy = trnshadow.cell_origin(5, 7)
    tight = _blank_rows()
    for dy in range(8):
        tight[oy + dy] = ((1 << 8) - 1) << ox
    check(trnshadow.tail_bit(trnshadow.tail_from_rows(tight), 5, 7) == 0,
          "a cell shadowed to its own 8x8 edge does not set the flag")
    wide = _blank_rows()
    for dy in range(-1, 9):
        wide[oy + dy] = ((1 << 10) - 1) << (ox - 1)
    check(trnshadow.tail_bit(trnshadow.tail_from_rows(wide), 5, 7) == 1,
          "one sample of skirt more and it does")


def _load(ar, table, file_id):
    return Terrain.load(file_id, archive=ar, table=table)


def section_archive(ar, table, rows_to_walk):
    print("\n2. Every retail block decodes and re-encodes to the same bytes")
    blocks = decoded = exact = 0
    tail_ok = tail_bits = 0
    pad0 = pad2 = 0
    nontrivial = 0
    zeros = zeros_lead = 0
    t0 = time.perf_counter()
    refusals = []
    for row in rows_to_walk:
        trn = Terrain.from_row(row, ar)
        for blk in trn.shadow:
            blocks += 1
            # Counted, not propagated: `decode_rows` raising would abort the run
            # with a traceback and the check below could then never go red --
            # which is the shape of a check that cannot fail.
            try:
                rr = trnshadow.decode_rows(blk.payload)
            except ValueError as exc:
                refusals.append(f"row {row}: {exc}")
                continue
            decoded += 1
            exact += trnshadow.encode_rows(rr) == blk.payload
            bad = trnshadow.tail_disagreement(rr, blk.tail)
            tail_bits += trnshadow.CELL_BITS
            tail_ok += trnshadow.CELL_BITS - bad
            b0 = trnshadow.tail_disagreement(rr, blk.tail, pad=0)
            b2 = trnshadow.tail_disagreement(rr, blk.tail, pad=2)
            pad0 += b0
            pad2 += b2
            if b0 or b2:
                nontrivial += 1
            z, zl = trnshadow.zero_bytes(blk.payload)
            zeros += z
            zeros_lead += zl
    dt = time.perf_counter() - t0
    print(f"   {len(rows_to_walk)} maps, {blocks} blocks, {dt:.1f}s")
    check(blocks > 0, "the sample yielded blocks to walk", f"{blocks}")
    check(decoded == blocks,
          "every block closes on 272 rows of 272 samples",
          f"{decoded}/{blocks}"
          + (f"; first refusal -- {refusals[0]}" if refusals else ""))
    check(exact == blocks,
          "every block re-encodes byte for byte from the bitmap alone",
          f"{exact}/{blocks}")
    check(tail_ok == tail_bits,
          "the 10x10 rule reproduces every stored tail bit",
          f"{tail_ok}/{tail_bits}")
    check(zeros > 0 and zeros == zeros_lead,
          "every 0x00 byte in retail payloads opens a row, none is a run",
          f"{zeros_lead}/{zeros} zeros at a row start")

    print("\n3. ...and the neighbouring window widths do not")
    check(pad0 > 0, "an 8x8 window disagrees with the stored tail",
          f"{pad0} of {tail_bits} cell bits")
    check(pad2 > 0, "a 12x12 window disagrees with the stored tail",
          f"{pad2} of {tail_bits} cell bits")
    check(nontrivial > 0,
          "the controls were exercised on blocks that could tell them apart",
          f"{nontrivial} of {blocks} blocks")


def section_polarity(ar, table):
    print("\n4. A set bit means IN SHADOW, checked against tag 9")
    trn = _load(ar, table, KAMADAN_FILE_ID)
    dx = trn.dim_x
    cx = trn.chunks_x
    lit_sum = lit_n = dark_sum = dark_n = 0
    for bi, blk in enumerate(trn.shadow):
        tx, ty = bi % cx, bi // cx
        for cyy in range(CHUNK_SIZE):
            for cxx in range(CHUNK_SIZE):
                v = trn.shade[Terrain.index(tx * CHUNK_SIZE + cxx,
                                            ty * CHUNK_SIZE + cyy, dx)]
                if trnshadow.tail_bit(blk.tail, cxx, cyy):
                    dark_sum += v
                    dark_n += 1
                else:
                    lit_sum += v
                    lit_n += 1
    check(dark_n > 0 and lit_n > 0,
          "the reference map has cells of both kinds",
          f"{dark_n} flagged, {lit_n} not")
    dark = dark_sum / max(1, dark_n)
    lit = lit_sum / max(1, lit_n)
    check(dark < lit - 10.0,
          "flagged cells are darker in the lightmap, by more than a rounding",
          f"tag 9 mean {dark:.1f} flagged vs {lit:.1f} not")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dat", default=None)
    ap.add_argument("--sample", type=int, default=DEFAULT_SAMPLE,
                    help="how many maps section 2 walks")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    section_codec()

    dat = args.dat
    if dat is None:
        try:
            dat = os.path.join(
                vaultpath.require_dir(
                    "dat_study", why="tag 7's only real fixture"),
                "Gw.dat")
        except SystemExit as exc:
            LEDGER.skip("every archive-backed section",
                        str(exc).replace("\n", " | "))
            return LEDGER.verdict()
    if not os.path.isfile(dat):
        LEDGER.skip("every archive-backed section", f"no archive at {dat}")
        return LEDGER.verdict()

    with Archive(dat) as ar:
        table = file_id_table(ar)
        heads = sorted(e.index for e in ar.entries
                       if e.flags == 259 and e.size)
        # Two named maps first so the sample always covers a flat block and a
        # heavily shadowed one, then fill up to --sample.
        want = [table[SMALL_FILE_ID], table[KAMADAN_FILE_ID]]
        if args.all:
            want = heads
        else:
            for r in heads:
                if len(want) >= max(2, args.sample):
                    break
                if r not in want:
                    want.append(r)
        section_archive(ar, table, want)
        section_polarity(ar, table)

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
