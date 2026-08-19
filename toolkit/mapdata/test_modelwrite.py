r"""The 0xFA0 geometry writer: identity, and the controls that make it mean something.

    python toolkit/mapdata/test_modelwrite.py
    python toolkit/mapdata/test_modelwrite.py --all      # the wide sweep

WHY IDENTITY IS THE CRITERION AND NOT RE-PARSE EQUIVALENCE, restated here
because it is the whole reason this file exists: a writer that stashed the
source block would pass every re-parse oracle while decoding nothing (the
memcpy-loader defect, `studies/models/FINDINGS.md` §4.5). So §4 is not a
formality -- it MUTATES one typed value and requires the output to change at
exactly the bytes that value occupies. A memcpy writer fails it; this one does
not.

The synthetic fixtures in §1 exist for the same reason `test_skelwrite.py`'s
do: they exercise what retail cannot. Retail carries `u2` blocks on 9.12% of
sub-models and never a zero-length one, never a two-group binding on a
three-vertex mesh, and never the refusals §5 provokes.
"""

import argparse
import os
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import checks  # noqa: E402
import vaultpath  # noqa: E402
from archive import Archive, FFNA_MAGIC, ffna_chunks, file_id_table  # noqa: E402
import modelfile as mf  # noqa: E402
import modelwrite as mw  # noqa: E402

FLOOR = 20

HATCHER_MESH = 116703
WORM_MESH = 116366


# --------------------------------------------------------------- fixtures

def synth(nv=3, fvf=0x0017, u=(2, 3, 1), unk=0xAB, ncoll=0, tail=b""):
    """A whole 0xFA0 chunk built with struct.pack. No ArenaNet bytes."""
    u0, u1, u2 = u
    head = bytearray(0x54)
    struct.pack_into("<I", head, 0, mf.GEOMETRY_VERSION)
    struct.pack_into("<I", head, mf.NUM_MODELS_AT, 1)
    struct.pack_into("<H", head, mf.COLLISION_COUNT_AT, ncoll)
    # block J's gate: `if u32@0x34: that many bytes` (0x007957B4). A tail
    # without its gate set is not a tail, it is trailing garbage, and the
    # client's own closure at 0x007957CB refuses the chunk -- which the
    # fixture discovered rather than assumed.
    struct.pack_into("<I", head, 0x34, len(tail))
    ti = nv
    body = mf.SUBMODEL_HEADER.pack(unk, ti, ti, ti, nv, fvf, u0, u1, u2)
    body += struct.pack(f"<{ti}H", *range(ti))
    for v in range(nv):
        body += struct.pack("<3f", v * 1.5, v * 2.5, v * 3.5)
        body += struct.pack("<I", v % max(1, u0))
        body += struct.pack("<3f", 0.0, 0.0, 1.0)
        body += struct.pack("<2f", v * 0.25, v * 0.75)
    if u0:
        counts = [1] * u0
        counts[-1] += u1 - u0
        body += struct.pack(f"<{u0}I", *counts)
        body += struct.pack(f"<{u1}I", *range(7, 7 + u1))
    for r in range(u2):
        body += struct.pack("<3I", r, 0xDEAD, 0xBEEF)
    for c in range(ncoll):
        body += mf.COLLISION_HEADER.pack(3, 2)
        body += struct.pack("<3H", 0, 1, 2)
        body += struct.pack("<3f", 1.0, 2.0, 3.0)
        body += struct.pack("<3f", 4.0, 5.0, 6.0)
    return bytes(head) + body + tail


def _geometry_of(data):
    return next((bytes(data[o:o + s]) for c, o, s in ffna_chunks(data)
                 if c == mf.GEOMETRY_CHUNK), None)


# --------------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dat", default=None)
    ap.add_argument("--all", action="store_true",
                    help="sweep every model row rather than a stride sample")
    args = ap.parse_args(argv)

    led = checks.Ledger("model writer", floor=FLOOR)
    check = checks.adopt(led)
    t0 = time.perf_counter()

    _section1(check)
    _section4(check)
    _section5(check)
    _vault(check, led, args)

    print(f"\n({time.perf_counter() - t0:.1f}s)")
    return led.verdict()


# --- 1. synthetic: what retail does not carry -------------------------------

def _section1(check):
    print()
    print("== 1. synthetic fixtures -- no ArenaNet bytes ==")
    a = synth()
    check(mw.encode(mw.extract(a)) == a,
          "a hand-built chunk round-trips byte-identically", f"{len(a)} bytes")

    b = synth(u=(0, 0, 0))
    check(mw.encode(mw.extract(b)) == b,
          "a sub-model with NO skin binding round-trips -- the rigid case, "
          "53.89% of retail", f"{len(b)} bytes")

    c = synth(ncoll=2)
    t = mw.extract(c)
    check(mw.encode(t) == c and len(t["collisions"]) == 2,
          "collision meshes round-trip through typed indices and positions",
          f"{len(t['collisions'])} mesh(es)")

    d = synth(tail=b"\x00" * 16)
    t = mw.extract(d)
    check(mw.encode(t) == d and t["tail"] == b"\x00" * 16,
          "the H/I/J tail is carried and named, not silently dropped",
          f"{len(t['tail'])} bytes carried")

    # the counts inside the carried preamble are RE-DERIVED, so they are the
    # one part of `head` a modification cannot leave stale
    t = mw.extract(a)
    t["head"] = bytearray(t["head"])
    struct.pack_into("<I", t["head"], mf.NUM_MODELS_AT, 99)
    check(mw.encode(bytes_head(t)) == a,
          "a WRONG sub-model count in the carried preamble is corrected from "
          "the typed list, not carried through", "99 -> 1")


def bytes_head(t):
    t["head"] = bytes(t["head"])
    return t


# --- 4. identity is not vacuous ---------------------------------------------

def _section4(check):
    print()
    print("== 4. THE MEMCPY CONTROL: identity must be informative ==")
    a = synth()
    t = mw.extract(a)
    stride = mf.vertex_stride(0x0017)
    off = mf.field_offsets(0x0017)[mf.FIELD_POSITION]
    n = mw.scale_positions(t, 2.0)
    out = mw.encode(t)
    diff = [i for i in range(len(a)) if out[i] != a[i]]
    body = len(a) - len(mw.extract(a)["head"]) - 0
    base = len(mw.extract(a)["head"]) + mf.SUBMODEL_HEADER.size + 3 * 2
    windows = [range(base + v * stride + off, base + v * stride + off + 12)
               for v in range(3)]
    inside = all(any(i in w for w in windows) for i in diff)
    check(n == 3 and diff and inside,
          "scaling POSITIONS changes bytes only inside the position field of "
          "each vertex -- so the writer re-derives the vertex block rather "
          "than copying it",
          f"{len(diff)} byte(s) differ, all inside the {3 * 12} position bytes")

    # and a mutation the source bytes cannot supply must survive the trip
    t2 = mw.extract(a)
    t2["submodels"][0]["verts"][mf.FIELD_GROUP] = [1, 0, 1]
    out2 = mw.encode(t2)
    g2 = mf.ModelGeometry.decode(out2).submodels[0]
    check(list(g2.groups()) == [1, 0, 1] and out2 != a,
          "a changed GR_FVF_GROUP value is written and reads back -- the "
          "field named this morning is now writable",
          f"{list(g2.groups())}")


# --- 5. the refusals --------------------------------------------------------

def _section5(check):
    print()
    print("== 5. refusals, each provoked ==")

    t = mw.extract(synth())
    t["submodels"][0]["group_counts"] = (1, 1)      # totals 2, not 3
    check(_refuses(t), "a group-transform closure violation is REFUSED "
                       "(MdlCombine:860)", "counts total 2 of 3")

    t = mw.extract(synth())
    t["submodels"][0]["u2_records"] = b"\x00" * 7
    check(_refuses(t), "a u2 block that is not a whole number of 12-byte "
                       "records is REFUSED", "7 bytes")

    t = mw.extract(synth())
    t["submodels"][0]["counts"] = (2, 2, 2)         # implies 2 indices, has 3
    check(_refuses(t), "counts that disagree with the index array are REFUSED",
          "implies 2, has 3")

    t = mw.extract(synth())
    t["submodels"][0]["verts"][mf.FIELD_POSITION] = [(0.0, 0.0, 0.0)]
    check(_refuses(t), "a field with the wrong number of values is REFUSED "
                       "by NAME, never padded", "1 value for 3 vertices")

    t = mw.extract(synth())
    t["head"] = b"\x00" * 8
    check(_refuses(t), "a truncated preamble is REFUSED", "8 bytes")

    check(_raises(lambda: mw.scale_positions(mw.extract(synth()), 0.0)),
          "a zero scale is REFUSED -- it would collapse the mesh to a point",
          "factor 0")

    ok = True
    try:
        mw.rebuild_container(b"ffna\x02" + struct.pack("<II", 0xFA1, 0),
                             geometry=b"\x00")
        ok = False
    except mw.Unwritable:
        pass
    check(ok, "substituting geometry into a container that has NO 0xFA0 is "
              "REFUSED -- a caller must not believe it modified a file it "
              "did not", "raised Unwritable")


def _refuses(t):
    try:
        mw.encode(t)
        return False
    except mw.Unwritable:
        return True


def _raises(fn):
    try:
        fn()
        return False
    except mw.Unwritable:
        return True


# --- 2/3. the archive -------------------------------------------------------

def _vault(check, led, args):
    dat = args.dat
    if dat is None:
        dat = os.path.join(vaultpath.vault_root(), "dat_study", "Gw.dat")
    if not os.path.isfile(dat):
        why = (f"no archive at {dat} (vault resolved to "
               f"{vaultpath.vault_root()}, {vaultpath.vault_why()})")
        led.skip("2. the two unit anchors", why)
        led.skip("3. the corpus sweep", why)
        return
    with Archive(dat) as ar:
        _section2(check, ar)
        _section3(check, ar, args)


def _section2(check, ar):
    print()
    print("== 2. the two unit anchors ==")
    table = file_id_table(ar, raw=True)
    for fid, name in ((HATCHER_MESH, "hatcher"), (WORM_MESH, "worm")):
        row = table.get(fid)
        if row is None:
            check(False, f"{name} mesh {fid} is in the archive", "absent")
            continue
        data = ar.read(ar.row(row))
        chunk = _geometry_of(data)
        check(chunk is not None and mw.roundtrip(chunk) == chunk,
              f"the {name}'s mesh ({fid}) re-serializes byte-identically",
              f"{len(chunk) if chunk else 0} bytes")
        check(mw.rebuild_container(data) == data,
              f"and its whole ffna container does too -- every other chunk "
              f"carried verbatim, headers re-packed from parsed values",
              f"{len(data)} bytes")


def _section3(check, ar, args):
    print()
    print("== 3. the corpus ==")
    stride = 1 if args.all else 53
    ok = bad = skipped = 0
    fmts = set()
    for e in ar.entries[::stride]:
        try:
            head = bytes(ar.magic(e, 5))
            if head[:4] != FFNA_MAGIC or head[4] != mf.MODEL_FFNA_TYPE:
                continue
            data = ar.read(e)
            chunk = _geometry_of(data)
        except Exception:
            continue
        if chunk is None:
            continue
        try:
            t = mw.extract(chunk)
            same = mw.encode(t) == chunk
        except Exception:
            skipped += 1
            continue
        for s in t["submodels"]:
            fmts.add(s["dat_fvf"])
        ok += same
        bad += not same
        if not args.all and ok + bad >= 250:
            break
    print(f"    {ok + bad} chunks, {len(fmts)} distinct vertex formats, "
          f"{skipped} undecodable")
    check(ok + bad >= 150 and bad == 0,
          "every decodable geometry chunk re-serializes BYTE-IDENTICALLY from "
          "typed values", f"{ok}/{ok + bad}")
    check(len(fmts) >= 8,
          "and the sample spans enough vertex formats that the field map is "
          "exercised rather than one shape repeated", f"{len(fmts)} formats")


if __name__ == "__main__":
    sys.exit(main())
