r"""The model-file decoder, and the cross-file oracle that makes it trustable.

    python toolkit/mapdata/test_modelfile.py
    python toolkit/mapdata/test_modelfile.py --all     # the 14-map study sample

THE HEADLINE IS THE f11 IDENTITY AND IT CANNOT BE FORCED BY OUR CODE. The
Bloated prop record's `f11` equals `scale * max 2D vertex radius of the model
file the prop references` -- a number that crosses TWO FILES and eight decode
steps (prop record -> filename index -> dependency pair -> file id -> MFT row
-> geometry chunk -> sub-model walk -> vertex stride). A wrong stride, a wrong
start offset, a misread count or a swapped axis at ANY step moves it. This file
runs the whole chain through COMMITTED code (`props.py`, `mapchunks.py`,
`archive.py`, `modelfile.py`) and requires the identity at 1e-5 on every
comparable prop of both reference maps -- 474/474 and 664/664, MEASURED
2026-08-13 -- with the 3D-radius rival as the control that must stay collapsed
(1 and 7 respectively; 103 of 12,875 corpus-wide).

THE THREE FAILURE POPULATIONS ARE PINNED APART, because §A5's lesson is that
conflating them manufactured a false theory: unique closure, NO closure
(`NoClose`, ~15% corpus, and 77 of Pre-Searing's 229 -- per-map rates vary and
are pinned per map, not averaged), and AMBIGUOUS closure. The ambiguous
population is REAL and has a name: file 0x1BAE2 closes at offsets 97 and 101
with every index in range under BOTH parses, so nothing downstream can break
the tie. Section 3 pins both offsets as literals. It also pins the finding M1
adds: the single corpus occurrence of dat_fvf 0x2C is that file's CHOSEN parse
-- its rival parse is the common format 21 -- so the rare format's existence,
and §B6's one GWMB-table disagreement which rests on it, are both UNCONFIRMED
until rung M2 reads the client's own dispatch.

THE STRIDE RULE IS PINNED AGAINST LITERALS, not against itself: the thirteen
(dat_fvf, stride) pairs the 14-map sample measured are written in this file as
constants (the test_agentlife lesson -- an expectation computed FROM the symbol
under test lets the symbol move). Sections 0-1 need no vault: the synthetic
model file is built here from `struct.pack`, byte by byte, and every refusal
sits beside the positive control that the clean fixture still decodes.

`--all` reproduces the study's full 14-map sample -- 2,048 model files:
1,741 unique / 1 ambiguous / 306 no-close, f11 12,766/12,875 at 1e-5, rival
103, thirteen format pairs, ti and n0 divisible by 3 on 3,834 of 3,834 --
MEASURED 2026-08-13 at 165 s total against the default's 30 s, so budget for
those numbers rather than round ones.
"""

import argparse
import math
import os
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import Archive, ffna_chunks, file_id_table  # noqa: E402
import modelfile  # noqa: E402
from modelfile import (ModelFile, ModelGeometry, NoClose,  # noqa: E402
                       Undecodable, vertex_stride, GEOMETRY_CHUNK,
                       MODEL_FFNA_TYPE, SubModel, ffna_type,
                       FIELD_GROUP, FIELD_DIFFUSE)
from mapfile import MapFile  # noqa: E402
from props import BloatedProps  # noqa: E402
from mapchunks import dependency_file_id  # noqa: E402
import checks  # noqa: E402
import vaultpath  # noqa: E402

PROPS_BLOATED = 0x20000004
PROPS_DEPS_BLOATED = 0x21000004

KAMADAN_FILE_ID = 0x345CC
PRESEARING_FILE_ID = 0x1B97D

#: The TWELVE (dat_fvf, stride) pairs the corpus really holds, MEASURED
#: 2026-08-13 under the client's own tables. M1 measured thirteen; the
#: thirteenth, (44, 20), was a phantom -- see CORRECTED_FILE_ID below.
STRIDE_PAIRS = {
    21: 32, 23: 36, 53: 40, 55: 44, 117: 48, 119: 52,
    245: 56, 247: 60, 12405: 72, 12407: 76, 12533: 80, 12535: 84,
}

#: The client's tables, and where they live. `_section5` re-reads them out of
#: the vaulted image and requires these literals -- so the module's copy is
#: pinned to ArenaNet's bytes rather than to our transcription of them.
CLIENT_EXE = os.path.join("client", "2026-07-29_221c13772c7a", "Gw.exe")
FVF_TABLE_VAS = {"FVF0": (0x00BF5BE0, 16), "FVF1": (0x00BF5BC0, 8),
                 "FVF2": (0x00BF5B80, 16)}

#: THE M2 CORRECTION. Under M1's byte-cost rule this file closed at BOTH 97
#: and 101 and the 97-parse (format 0x2C, stride 20) was chosen; under the
#: client's tables only 101 closes and the format is the common 21. The
#: cross-file oracle confirms it from a source that shares nothing with the
#: binary: this model's props scored f11 0/16 then and 16/16 now.
CORRECTED_FILE_ID = 0x1BAE2
CORRECTED_START = 101
CORRECTED_FVF = 21
CORRECTED_OLD_START = 97
CORRECTED_PROPS = 16

#: The file that is ambiguous under the CLIENT's tables -- a different one,
#: and its extra closure is far out. Both rules pick the same (lowest) start,
#: so nothing downstream moves; it is pinned because closure is not identity.
AMBIGUOUS_FILE_ID = 0x25AA9
#: RESOLVED by rung M6. Under the retired SEARCH this file closed at both 170
#: and 65,842 and the corpus could never break the tie; the computed preamble
#: answers 170 and the rival never arises. The retired rule is still exercised
#: below, so this is a difference between two live answers.
AMBIGUOUS_STARTS = (170,)
RETIRED_AMBIGUOUS_STARTS = (170, 65842)

#: Reference-map census pins, RE-MEASURED 2026-08-13 after rung M6 replaced
#: the brute-force search with the client's own computed preamble walk.
#: `zero` is now 0 on both maps: EVERY prop-referenced model decodes, because
#: the ~15% that never closed were files whose stream continues past the
#: collision meshes (blocks H/I/J), which a walk requiring closure THERE
#: could not satisfy.
#:
#: **The f11 population is split deliberately, and it is the §A5 lesson.**
#: `cmp_old`/`f11_old` are the props whose model the RETIRED search could
#: already read -- that population is UNCHANGED and still scores perfectly,
#: which is what proves M6 did not disturb the oracle. `cmp`/`f11_ok` are the
#: whole map including the newly recovered models, where ~10% disagree. Those
#: two facts must not be averaged into one number: the first says nothing
#: regressed, the second is an OPEN QUESTION about the recovered files.
CENSUS = {
    KAMADAN_FILE_ID: dict(files=86, unique=86, ambig=0, zero=0,
                          cmp=516, f11_ok=510, rival=1,
                          cmp_old=474, f11_old=474, newly=15),
    PRESEARING_FILE_ID: dict(files=229, unique=229, ambig=0, zero=0,
                             cmp=864, f11_ok=846, rival=13,
                             cmp_old=664, f11_old=664, newly=77),
}

#: Per-map format census (sub-models per (dat_fvf, stride)), RE-MEASURED
#: after M6 -- the counts grew because every model now decodes.
FORMATS = {
    KAMADAN_FILE_ID: {(21, 32): 46, (23, 36): 20, (53, 40): 46, (55, 44): 6,
                      (117, 48): 60, (119, 52): 13, (245, 56): 6,
                      (12405, 72): 10},
    PRESEARING_FILE_ID: {(21, 32): 267, (23, 36): 72, (53, 40): 229,
                         (55, 44): 65, (117, 48): 121, (119, 52): 19,
                         (245, 56): 68, (247, 60): 28},
}

#: The full 14-map sample (`--all`). Closure counts are the study's; the f11
#: figure is M2's improvement (12,766 -> 12,782) and the ONLY thing that moved
#: it was the corrected file above.
ALL_FILES = 2048
ALL_UNIQUE = 1741
ALL_AMBIG = 1
ALL_ZERO = 306
ALL_CMP = 12875
ALL_F11_OK = 12782
ALL_F11_OK_BYTECOST = 12766
ALL_RIVAL = 103
ALL_SUBMODELS = 3834

#: The retired byte-cost rule, reproduced here as a live function so M2's
#: correction is a difference between two answers rather than a claim in
#: prose (the `test_codescan` §8 pattern).
def bytecost_stride(dat_fvf):
    s = 0
    if dat_fvf & 1:
        s += 12
    if dat_fvf & 2:
        s += 4
    if dat_fvf & 4:
        s += 12
    s += 8 * bin(dat_fvf & 0xF0).count("1")
    if dat_fvf & 0x3000:
        s += 24
    return s


#: Field-map population figures, MEASURED 2026-08-13 over a 7-map sample
#: (90,108 vertices). Each is a name's refutable prediction plus the control
#: that must collapse. Ranges are generous where the measurement is a
#: population rate rather than an invariant.
NORMAL_UNIT_RATE = 1.0                 # 90,108 / 90,108
NORMAL_CONTROL_MAX = 0.10              # measured 0.027
TANGENT_UNIT_RATE = 1.0                # 10,017 / 10,017
TANGENT_ORTHO_MIN = 0.85               # measured 0.930
TANGENT_ORTHO_CONTROL_MAX = 0.50       # measured 0.260

F11_TOL = 1e-5

# FLOOR: 57, from a real green run on `vault/dat_study/Gw.dat` 2026-08-13
# (121 s; was 34 before M2). Three scores, each MEASURED rather than
# subtracted, because this file now needs TWO vault artifacts and they fail
# independently:
#   57  archive + client image (the full run)
#   33  client image only        (--dat pointed at nothing)
#   29  neither                  (RURIK_VAULT pointed at nothing)
# So a bare-machine run lands 28 short and goes RED: a synthetic model file
# this test built has verified the plumbing and NOTHING about ArenaNet's
# bytes. `--all` adds 10 checks; its runtime is in the module docstring.
# 2026-08-16: +3 (the block-H fixture and the error-0x1D refusal, rung U1
# of studies/unitmodels/PLAN.md), 61 -> 64, measured green before raising.
FLOOR = 70


# ------------------------------------------------------------------ helpers

def raises(fn, *a, **kw):
    """True if `fn` raises ValueError (which Undecodable and KeyError's
    sibling both subclass here). Deliberately not bare except."""
    try:
        fn(*a, **kw)
    except (ValueError, KeyError):
        return True
    return False


def synth_geometry(num_models=2, coll=1, bad_index=False):
    """A geometry chunk payload built byte by byte, from nothing.

    Sub-model 0: format 21 (stride 32), 4 vertices, 6 indices (2 triangles),
    positions chosen so max 2D radius is EXACTLY 50.0 while the 3D radius is
    ~111.8 -- the two radii must be distinguishable or the rival control in
    the vault sections means nothing here. Sub-model 1: format 53 (stride
    40), 3 vertices, 3 indices. One collision mesh: 3 indices, 3 vertices.
    """
    def vert(stride, x, y, z):
        return struct.pack("<3f", x, y, z) + b"\xAA" * (stride - 12)

    sub0 = struct.pack("<9I", 7, 6, 6, 6, 4, 21, 1, 0, 2)
    idx0 = struct.pack("<6H", 0, 1, 2, 2, 1, 3 if not bad_index else 44)
    v0 = (vert(32, 30.0, 40.0, -100.0) + vert(32, 0.0, 0.0, 5.0)
          + vert(32, -10.0, 2.0, 1.0) + vert(32, 3.0, -4.0, 2.0))
    trail0 = b"\xBB" * ((1 + 0 + 2 * 3) * 4)

    sub1 = struct.pack("<9I", 9, 3, 3, 3, 3, 53, 0, 0, 0)
    idx1 = struct.pack("<3H", 0, 1, 2)
    v1 = (vert(40, 1.0, 1.0, 0.0) + vert(40, -2.0, 0.5, 3.0)
          + vert(40, 0.0, -3.0, 1.0))

    body = sub0 + idx0 + v0 + trail0
    if num_models > 1:
        body += sub1 + idx1 + v1
    collision = b""
    if coll:
        collision = (struct.pack("<2I", 3, 3) + struct.pack("<3H", 0, 1, 2)
                     + struct.pack("<9f", 5.0, 0.0, 0.0, 0.0, 5.0, 0.0,
                                   0.0, 0.0, 9.0))
    header = bytearray(0x54)
    # Since rung M6 the decoder COMPUTES the sub-model start the way
    # MdlLoad.cpp does, so a synthetic chunk has to be one the CLIENT would
    # accept -- which makes this fixture stronger than the one it replaced,
    # not merely different. The version word is ArenaNet's own gate
    # (0x00794586); every preamble-block selector is left ZERO so all six
    # blocks are absent and the cursor lands exactly on 0x54, and the three
    # trailing selectors (0x31, 0x48, 0x34) are zero so the walk closes on
    # the final byte.
    struct.pack_into("<I", header, 0x00, modelfile.GEOMETRY_VERSION)
    struct.pack_into("<I", header, 0x44, num_models)
    struct.pack_into("<H", header, 0x4C, coll)
    return bytes(header) + body + collision


def synth_model_file(geometry_payload, extra=()):
    """A whole `ffna` type 2 file around a geometry payload."""
    out = b"ffna" + bytes([MODEL_FFNA_TYPE])
    chunks = [(GEOMETRY_CHUNK, geometry_payload)] + list(extra)
    for cid, payload in chunks:
        out += struct.pack("<II", cid, len(payload)) + payload
    return out


def map_models(ar, table, by_row, map_fid):
    """The committed eight-step chain for one map: every prop joined to its
    model's radii. Returns (per-file classification, per-prop comparisons,
    format census, div3 tallies)."""
    head = by_row[table[map_fid]]
    mf = MapFile.decode(ar.read(head), strict=False)
    bp = BloatedProps.decode(mf.find(PROPS_BLOATED).payload())
    dep = mf.find(PROPS_DEPS_BLOATED)
    fids = dep.value.file_ids

    cls = dict(used=0, unresolved=0, nogeom=0, files=0, unique=0, ambig=0,
               zero=0)
    fmts = {}
    div3 = dict(sub=0, ti=0, n0=0)
    radii = {}
    newly_readable = set()
    for idx in sorted({r.model for r in bp.records}):
        cls["used"] += 1
        fid = fids[idx]
        row = table.get(fid)
        if row is None or by_row.get(row) is None:
            cls["unresolved"] += 1
            continue
        try:
            model = ModelFile.decode(ar.read(by_row[row]))
            geo = model.geometry()
        except NoClose:
            cls["files"] += 1
            cls["zero"] += 1
            continue
        except (Undecodable, ValueError):
            cls["nogeom"] += 1
            continue
        if geo is None:
            cls["nogeom"] += 1
            continue
        cls["files"] += 1
        if geo.ambiguous:
            cls["ambig"] += 1
        else:
            cls["unique"] += 1
        for sm in geo.submodels:
            fmts[(sm.dat_fvf, sm.stride)] = fmts.get(
                (sm.dat_fvf, sm.stride), 0) + 1
            div3["sub"] += 1
            div3["ti"] += sm.ti % 3 == 0
            div3["n0"] += sm.counts[0] % 3 == 0
        if not geo.ambiguous:
            radii[idx] = (geo.max_2d_radius(), geo.max_3d_radius())
            # Could the RETIRED search have read this file? Answered by
            # running it, not by remembering -- so "newly readable" is a
            # difference between two live answers rather than a stored list.
            if not retired_search_closes(model.find(GEOMETRY_CHUNK)):
                newly_readable.add(idx)

    cmps = []
    for rec in bp.records:
        if rec.model not in radii:
            continue
        rxy, r3 = radii[rec.model]
        f11, = struct.unpack("<f", rec.tail)
        cmps.append(Comparison(f11, rec.scale, rxy, r3,
                               rec.model in newly_readable))
    return cls, cmps, fmts, div3


class Comparison:
    """One prop scored against its model. `newly` marks a prop whose model
    only the COMPUTED preamble can read."""

    __slots__ = ("f11", "scale", "rxy", "r3", "newly")

    def __init__(self, f11, scale, rxy, r3, newly):
        self.f11, self.scale, self.rxy, self.r3, self.newly = (
            f11, scale, rxy, r3, newly)

    def __iter__(self):
        return iter((self.f11, self.scale, self.rxy, self.r3))


def retired_search_closes(payload):
    """The BRUTE-FORCE SEARCH rung M6 retired, reproduced here as a live
    function.

    Kept for the same reason `test_modelfile` keeps M2's retired byte-cost
    stride rule: the claim "M6 recovered N models" is only a measurement if
    the old answer is computed rather than remembered, and the claim "the
    ambiguity was the RULE's, not the file's" needs the rule that had it.
    """
    if len(payload) < modelfile.PREAMBLE_MIN:
        return False
    num, = struct.unpack_from("<I", payload, modelfile.NUM_MODELS_AT)
    coll, = struct.unpack_from("<H", payload, modelfile.COLLISION_COUNT_AT)
    limit = len(payload) - modelfile.SUBMODEL_HEADER.size
    for start in range(modelfile.PREAMBLE_MIN, limit):
        walked = modelfile._walk_models(payload, start, num)
        if walked is None:
            continue
        end, _raw = walked
        if coll == 0:
            if end == len(payload):
                return True
        else:
            cw = modelfile._walk_collision(payload, end, coll)
            if cw is not None and cw[0] == len(payload):
                return True
    return False


def score_f11(cmps):
    ok = rival = 0
    for f11, scale, rxy, r3 in cmps:
        if rxy > 0 and abs(f11 - rxy * scale) / (rxy * scale) < F11_TOL:
            ok += 1
        if r3 > 0 and abs(f11 - r3 * scale) / (r3 * scale) < F11_TOL:
            rival += 1
    return ok, rival


# --------------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dat", default=None)
    ap.add_argument("--all", action="store_true",
                    help="reproduce the full 14-map study sample (~170 s)")
    args = ap.parse_args(argv)

    led = checks.Ledger("model file", floor=FLOOR)
    check = checks.adopt(led)
    t0 = time.perf_counter()

    _section0(check)
    _section1(check)
    _vault_sections(check, led, args)

    print(f"\n({time.perf_counter() - t0:.1f}s)")
    return led.verdict()


# --- 0. the stride rule against the measured literals -----------------------

def _section0(check):
    print("\n== 0. the client's stride tables and the field map (no vault) ==")
    bad = [(f, vertex_stride(f), s) for f, s in STRIDE_PAIRS.items()
           if vertex_stride(f) != s]
    check(not bad,
          f"the client's tables reproduce all {len(STRIDE_PAIRS)} corpus "
          f"(dat_fvf, stride) pairs", f"wrong: {bad}" if bad else "12/12")
    check(len(set(STRIDE_PAIRS.values())) == len(STRIDE_PAIRS),
          f"the {len(STRIDE_PAIRS)} strides are all distinct, so a pair check "
          f"cannot pass by collision")

    # THE TABLES ARE ADDITIVE OVER THEIR BITS, which is what makes the field
    # map a MEASUREMENT rather than a division we invented: each of the 40
    # entries is the sum of its set bits' costs.
    for name, tab, nbits in (("FVF0", modelfile.FVF0, 4),
                             ("FVF1", modelfile.FVF1, 3),
                             ("FVF2", modelfile.FVF2, 4)):
        cost = [tab[1 << i] for i in range(nbits)]
        ok = all(tab[v] == sum(c for i, c in enumerate(cost) if v >> i & 1)
                 for v in range(len(tab)))
        check(ok, f"{name} is additive over its bits (per-bit cost {cost})")

    # The field map must SUM to the stride for every corpus format...
    bad = [f for f in STRIDE_PAIRS
           if sum(modelfile.FIELD_SIZE[b] for b in modelfile.field_offsets(f))
           != STRIDE_PAIRS[f]]
    check(not bad, "field_offsets accounts for every byte of every corpus "
                   "format's stride", f"{bad}")
    # ...and every corpus format must carry a position at offset 0 and a
    # normal, which is what M3/M4 will lean on.
    lay = {f: modelfile.field_offsets(f) for f in STRIDE_PAIRS}
    check(all(v.get(modelfile.FIELD_POSITION) == 0 for v in lay.values()),
          "every corpus format puts the position at offset 0")
    check(all(modelfile.FIELD_NORMAL in v for v in lay.values()),
          "every corpus format carries a normal")
    check(all(any(b in v for b in modelfile.FIELD_TEXCOORD_BITS)
              for v in lay.values()),
          "every corpus format carries at least one texcoord set")

    # THE RETIRED RULE, run live: it must agree on the twelve real formats and
    # disagree massively elsewhere -- which is exactly why it survived M1.
    same = [f for f in STRIDE_PAIRS if bytecost_stride(f) == vertex_stride(f)]
    check(len(same) == len(STRIDE_PAIRS),
          "the retired byte-cost rule agrees on all 12 REAL formats -- which "
          "is why a wrong rule survived M1")
    diff = sum(1 for d in range(0x10000) if bytecost_stride(d)
               != vertex_stride(d))
    check(diff > 50000,
          "and disagrees on most of the 65,536-word space, so the agreement "
          "above is about where the corpus lives, not about the rule",
          f"{diff} words differ")
    check(bytecost_stride(0x2C) == 20 and vertex_stride(0x2C) == 24,
          "THE PHANTOM: the retired rule reads 0x2C as stride 20, the client "
          "as 24", f"{bytecost_stride(0x2C)} vs {vertex_stride(0x2C)}")
    check(0x2C not in STRIDE_PAIRS,
          "and 0x2C is NOT in the corpus format list any more")


# --- 1. a model file built from nothing -------------------------------------

def _section1(check):
    print("\n== 1. synthetic model file: decode, radii, refusals (no vault) ==")
    geo_pay = synth_geometry()
    data = synth_model_file(geo_pay, extra=[(0xFA1, b"\x00\x01")])
    mf = ModelFile.decode(data)
    check(mf.ffna_type == MODEL_FFNA_TYPE and len(mf.chunks) == 2,
          "the chunk walk reads both chunks of the synthetic file")
    geo = mf.geometry()
    check(geo.num_models == 2 and geo.collision_count == 1,
          "the header counts survive", f"{geo!r}")
    check(geo.starts == (0x54,),
          "the sub-model walk closes at EXACTLY the one true offset",
          f"{geo.starts}")
    check(not geo.ambiguous, "and the fixture is unambiguous")

    sm0, sm1 = geo.submodels
    check(sm0.dat_fvf == 21 and sm0.stride == 32 and sm0.nv == 4
          and sm1.dat_fvf == 53 and sm1.stride == 40 and sm1.nv == 3,
          "both sub-models carry their format, stride and vertex count")
    check(sm0.ti == 6 and sm0.triangles == [(0, 1, 2), (2, 1, 3)],
          "the index dedup rule gives 6 indices and the two triangles",
          f"ti={sm0.ti}, {sm0.triangles}")
    check(sm0.positions()[0] == (30.0, 40.0, -100.0),
          "positions come off the stride at offset 0")
    check(geo.max_2d_radius() == 50.0,
          "max 2D radius is the planted 50.0 (30-40-50 triangle)",
          f"{geo.max_2d_radius()!r}")
    r3 = geo.max_3d_radius()
    check(abs(r3 - math.sqrt(30 ** 2 + 40 ** 2 + 100 ** 2)) < 1e-9,
          "the 3D radius differs (the rival control has power)", f"{r3:.4f}")
    check(sm0.vertex_data[12:32] == b"\xAA" * 20
          and sm0.trailing == b"\xBB" * 28,
          "non-position vertex bytes and the trailing block are carried "
          "opaquely, byte for byte")
    cm = geo.collisions[0]
    check(len(geo.collisions) == 1 and cm.positions[2] == (0.0, 0.0, 9.0)
          and cm.indices == (0, 1, 2),
          "the collision mesh decodes: position-only, u16 indices")

    # The refusals, each beside the positive control above.
    check(raises(ModelFile.decode, b"ffna\x03" + data[5:]),
          "ffna type 3 (a map) is refused, not misread")
    check(raises(ModelFile.decode, data[:-1]),
          "a truncated chunk walk is refused")
    bad_n = bytearray(geo_pay)
    struct.pack_into("<I", bad_n, 0x44, 5)
    err = None
    try:
        ModelGeometry.decode(bytes(bad_n))
    except NoClose as exc:
        err = exc
    check(isinstance(err, NoClose),
          "a count no walk can close raises NoClose, never a guess",
          type(err).__name__ if err else "returned normally")
    err = None
    try:
        ModelGeometry.decode(synth_geometry(bad_index=True))
    except Undecodable as exc:
        err = exc
    check(isinstance(err, Undecodable) and not isinstance(err, NoClose)
          and "indices" in str(err),
          "an index past the vertex array is refused AS a bad parse "
          "(0 of 3,834 measured sub-models have one)",
          type(err).__name__ if err else "returned normally")
    lone = ModelFile.decode(b"ffna" + bytes([MODEL_FFNA_TYPE])
                            + struct.pack("<II", 0xFA1, 1) + b"\x00")
    check(lone.geometry() is None,
          "a file with no geometry chunk answers None, not an error")

    # BLOCK H, exercised for the first time anywhere (2026-08-16): it
    # occurs on 0 of 20,661 archive geometry chunks (unitmodels FINDINGS
    # §4.1), so the models arc's 20,661/20,661 closure was never evidence
    # for the H term and only a fixture can test it. H = streak systems
    # (16 B each, u8@0x31) + streaks (0x54 B each, u8@0x32), consumed
    # between the collision meshes and block I.
    h_pay = bytearray(synth_geometry())
    h_pay[0x31], h_pay[0x32] = 2, 1
    h_pay += b"\xCC" * (16 * 2 + 0x54 * 1)
    h_geo = ModelGeometry.decode(bytes(h_pay))
    check(h_geo.num_models == 2 and h_geo.starts == (0x54,),
          "a block-H-carrying chunk decodes: the H term consumes "
          "16a + 0x54b and the walk still closes on the final byte")
    check(raises(ModelGeometry.decode, bytes(h_pay[:-4])),
          "and the H term is load-bearing: the same chunk 4 bytes short "
          "is refused rather than closed")
    bad_h = bytearray(h_pay)
    bad_h[0x32] = 0
    err = None
    try:
        ModelGeometry.decode(bytes(bad_h))
    except Undecodable as exc:
        err = exc
    check(err is not None and "0x1D" in str(err),
          "streak systems with zero streaks is refused the way the client "
          "refuses it (error 0x1D at 0x00795664)",
          str(err) if err else "returned normally")


# --- 2-4. the archive -------------------------------------------------------

def _vault_sections(check, led, args):
    dat = args.dat
    if dat is None:
        dat = os.path.join(vaultpath.vault_root(), "dat_study", "Gw.dat")
    if not os.path.isfile(dat):
        why = (f"no archive at {dat} (vault resolved to "
               f"{vaultpath.vault_root()}, {vaultpath.vault_why()})")
        led.skip("2. the reference-map census and the f11 oracle", why)
        led.skip("3. the M2 correction and the ambiguous file", why)
        led.skip("6. the vertex field map against the corpus", why)
        led.skip("7. the skin binding", why)
        if args.all:
            led.skip("4. the 14-map sample", why)
    else:
        with Archive(dat) as ar:
            table = file_id_table(ar)
            by_row = {e.index: e for e in ar.entries}
            _section2(check, ar, table, by_row)
            _section3(check, ar, table, by_row)
            _section6(check, ar, table, by_row)
            _section7(check, ar, table, by_row)
            if args.all:
                _section4(check, ar, table, by_row)
    _section5(check, led)


def _section2(check, ar, table, by_row):
    print("\n== 2. THE ORACLE: f11 across two files, on both reference maps ==")
    for fid in (KAMADAN_FILE_ID, PRESEARING_FILE_ID):
        want = CENSUS[fid]
        cls, cmps, fmts, div3 = map_models(ar, table, by_row, fid)
        print(f"    0x{fid:X}: {cls}  sub-models {div3['sub']}")

        check(cls["unresolved"] == 0 and cls["nogeom"] == 0,
              f"0x{fid:X}: every prop-referenced model resolves and carries "
              f"a geometry chunk", f"{cls}")
        check(cls["files"] == want["files"] and cls["unique"] == want["unique"]
              and cls["ambig"] == want["ambig"]
              and cls["zero"] == want["zero"],
              f"0x{fid:X}: the closure census is the pinned "
              f"{want['unique']}/{want['ambig']}/{want['zero']} "
              f"over {want['files']} files",
              f"{cls['unique']}/{cls['ambig']}/{cls['zero']} "
              f"over {cls['files']}")
        check(fmts == FORMATS[fid],
              f"0x{fid:X}: the format census is the pinned "
              f"{len(FORMATS[fid])} pairs", f"{sorted(fmts.items())}")
        check(div3["ti"] == div3["sub"] and div3["n0"] == div3["sub"],
              f"0x{fid:X}: ti and n0 are divisible by 3 on all "
              f"{div3['sub']} sub-models (triangle lists)",
              f"{div3['ti']}/{div3['sub']}, {div3['n0']}/{div3['sub']}")

        # THE SPLIT THAT PROVES M6 DID NOT DISTURB THE ORACLE, and the §A5
        # lesson applied: the props whose model the RETIRED search could
        # already read are scored SEPARATELY, and that population must still
        # be PERFECT. Averaging it with the newly recovered models would turn
        # "nothing regressed, and the new files raise a question" into one
        # degraded number that says neither.
        old_cmps = [c for c in cmps if not c.newly]
        old_ok, _ = score_f11(old_cmps)
        check(len(old_cmps) == want["cmp_old"] and old_ok == want["f11_old"],
              f"0x{fid:X}: on the props the RETIRED search could already "
              f"read, f11 still holds {want['f11_old']}/{want['cmp_old']} -- "
              f"M6 recovered models without moving the oracle",
              f"{old_ok}/{len(old_cmps)}")
        newly = len(cmps) - len(old_cmps)
        check(newly == want["cmp"] - want["cmp_old"] and newly > 0,
              f"0x{fid:X}: and {newly} props stand on a model only the "
              f"COMPUTED preamble can read -- the control that keeps the "
              f"line above from being vacuous",
              f"{newly} newly readable")

        ok, rival = score_f11(cmps)
        check(len(cmps) == want["cmp"] and ok == want["f11_ok"],
              f"0x{fid:X}: f11 == scale * max-2D-radius at {F11_TOL:g} on "
              f"the pinned {want['f11_ok']}/{want['cmp']} comparable props",
              f"{ok}/{len(cmps)}")
        check(rival == want["rival"] and rival * 20 < ok,
              f"0x{fid:X}: the 3D-radius rival stays collapsed "
              f"(pinned {want['rival']})", f"{rival}/{len(cmps)}")


def _section3(check, ar, table, by_row):
    print("\n== 3. the M2 correction, and closure is NOT identity (§B5) ==")
    # THE CORRECTED FILE. Under M1 this was ambiguous and its chosen parse
    # invented format 0x2C; the client's tables leave one closure.
    mf = ModelFile.decode(ar.read(by_row[table[CORRECTED_FILE_ID]]))
    geo = mf.geometry()
    check(geo.starts == (CORRECTED_START,) and not geo.ambiguous,
          f"file 0x{CORRECTED_FILE_ID:X} now closes at ONE offset "
          f"({CORRECTED_START}) -- M1's ambiguity is resolved",
          f"{geo.starts}")
    check(len(geo.submodels) == 1
          and geo.submodels[0].dat_fvf == CORRECTED_FVF,
          f"and its format is the common {CORRECTED_FVF}, not the phantom "
          f"0x2C", f"{geo.submodels[0]!r}")
    # The retired rule, run live on the same bytes: it must still find BOTH
    # offsets, so the correction is a difference between two answers.
    pay = mf.find(GEOMETRY_CHUNK)
    old = _closing_starts(pay, bytecost_stride)
    check(old == [CORRECTED_OLD_START, CORRECTED_START],
          f"the retired rule still closes at both {CORRECTED_OLD_START} and "
          f"{CORRECTED_START} on these bytes -- the ambiguity was the RULE's, "
          f"not the file's", f"{old}")

    # The file that is ambiguous under the CLIENT's tables is a different one.
    mf2 = ModelFile.decode(ar.read(by_row[table[AMBIGUOUS_FILE_ID]]))
    geo2 = mf2.geometry()
    check(not geo2.ambiguous and geo2.starts == AMBIGUOUS_STARTS,
          f"file 0x{AMBIGUOUS_FILE_ID:X} resolves to the ONE computed offset "
          f"{AMBIGUOUS_STARTS[0]} -- M6 removed the ambiguity by construction, "
          f"closure is still not identity", f"{geo2.starts}")
    check(geo2.start == AMBIGUOUS_STARTS[0],
          "decode keeps the lowest offset, which BOTH rules agree on here, "
          "so nothing downstream moves")


def _closing_starts(payload, stride_fn):
    """Every closing offset under an arbitrary stride rule -- written here so
    the retired rule can be run against real bytes without the module under
    test having to keep it."""
    num, = struct.unpack_from("<I", payload, 0x44)
    coll, = struct.unpack_from("<H", payload, 0x4C)
    out = []
    for s in range(0x54, len(payload) - 36):
        p = s
        ok = True
        for _ in range(num):
            if p + 36 > len(payload):
                ok = False
                break
            _u, n0, n1, n2, nv, fvf, u0, u1, u2 = struct.unpack_from(
                "<9I", payload, p)
            if nv == 0 or nv > 200000 or fvf > 0xFFFFF:
                ok = False
                break
            vs = stride_fn(fvf)
            if vs < 8 or vs > 0x80:
                ok = False
                break
            ti = n0 + (n0 != n1) * n1 + (n1 != n2) * n2
            p += 36 + ti * 2 + nv * vs + (u0 + u1 + u2 * 3) * 4
            if p > len(payload):
                ok = False
                break
        if ok and coll == 0 and p == len(payload):
            out.append(s)
    return out


def _section4(check, ar, table, by_row):
    print("\n== 4. the full 14-map study sample (--all) ==")
    rows = [e for e in ar.entries if (e.flags & 0xFFFF) == 259]
    sel = rows[::25]
    check(len(sel) == 14, "the sample is the study's 14 maps", f"{len(sel)}")

    seen = {}
    tot = dict(files=0, unique=0, ambig=0, zero=0)
    fmts = {}
    div3 = dict(sub=0, ti=0, n0=0)
    cmps = []
    for e in sel:
        try:
            data = ar.read(e)
            ch = {c: (o, s) for c, o, s in ffna_chunks(data)}
        except ValueError:
            continue
        if PROPS_BLOATED not in ch or PROPS_DEPS_BLOATED not in ch:
            continue
        o, s = ch[PROPS_BLOATED]
        bp = BloatedProps.decode(data[o:o + s])
        fo, fs = ch[PROPS_DEPS_BLOATED]
        fids = [dependency_file_id(*struct.unpack_from("<2H", data,
                                                       fo + 5 + 6 * i))
                for i in range((fs - 5) // 6)]
        for idx in sorted({r.model for r in bp.records}):
            fid = fids[idx]
            if fid not in seen:
                seen[fid] = None
                row = table.get(fid)
                if row is None or by_row.get(row) is None:
                    continue
                try:
                    geo = ModelFile.decode(ar.read(by_row[row])).geometry()
                except NoClose:
                    tot["files"] += 1
                    tot["zero"] += 1
                    continue
                except (Undecodable, ValueError):
                    continue
                if geo is None:
                    continue
                tot["files"] += 1
                tot["ambig" if geo.ambiguous else "unique"] += 1
                for sm in geo.submodels:
                    fmts[(sm.dat_fvf, sm.stride)] = fmts.get(
                        (sm.dat_fvf, sm.stride), 0) + 1
                    div3["sub"] += 1
                    div3["ti"] += sm.ti % 3 == 0
                    div3["n0"] += sm.counts[0] % 3 == 0
                seen[fid] = (geo.max_2d_radius(), geo.max_3d_radius())
            if seen[fid] is None:
                continue
            rxy, r3 = seen[fid]
            for rec in bp.records:
                if rec.model != idx:
                    continue
                f11, = struct.unpack("<f", rec.tail)
                cmps.append((f11, rec.scale, rxy, r3))

    check(tot["files"] == ALL_FILES,
          f"the sample reaches the study's {ALL_FILES} model files",
          f"{tot['files']}")
    check(tot["unique"] == ALL_UNIQUE and tot["ambig"] == ALL_AMBIG
          and tot["zero"] == ALL_ZERO,
          f"closure census {ALL_UNIQUE}/{ALL_AMBIG}/{ALL_ZERO}",
          f"{tot['unique']}/{tot['ambig']}/{tot['zero']}")
    check(len(fmts) == len(STRIDE_PAIRS)
          and all(fmts.get((f, s)) for f, s in STRIDE_PAIRS.items()),
          f"all {len(STRIDE_PAIRS)} format pairs occur and no others",
          f"{sorted(fmts)}")
    check(div3["sub"] == ALL_SUBMODELS and div3["ti"] == ALL_SUBMODELS
          and div3["n0"] == ALL_SUBMODELS,
          f"ti and n0 divisible by 3 on {ALL_SUBMODELS}/{ALL_SUBMODELS} "
          f"sub-models", f"{div3}")
    ok, rival = score_f11(cmps)
    check(len(cmps) == ALL_CMP,
          f"the comparable population is the study's {ALL_CMP} props",
          f"{len(cmps)}")
    check(ok == ALL_F11_OK,
          f"THE HEADLINE: f11 identity at {F11_TOL:g} on "
          f"{ALL_F11_OK}/{ALL_CMP}", f"{ok}")
    check(rival == ALL_RIVAL,
          f"the 3D-radius rival scores the pinned {ALL_RIVAL}", f"{rival}")
    check(ok > rival * 100,
          "and the identity beats the rival by over 100x")
    check(ok - ALL_F11_OK_BYTECOST == CORRECTED_PROPS,
          f"M2 improved the identity by exactly the {CORRECTED_PROPS} props "
          f"of the corrected file ({ALL_F11_OK_BYTECOST} -> {ALL_F11_OK})",
          f"+{ok - ALL_F11_OK_BYTECOST}")
    # §A5's second population: models that DID close whose f11 still
    # disagrees. Disjoint from the no-close files, unexplained, and
    # deliberately inside the denominator above. M2 shrank it from 109 to 93.
    check(ALL_CMP - ALL_F11_OK == 93,
          "the unexplained population is 93 props (was 109 before M2) and "
          "stays visible", f"{ALL_CMP - ok}")


# --- 5. the module's tables ARE the client's -------------------------------

def _pe_read(path, va, count):
    """`count` u32 at a virtual address, via a minimal PE section walk.

    Written here out of `struct` rather than taken from `clientscan/` so the
    comparison below is between the module's literals and ArenaNet's bytes,
    with no shared code deciding where to look.
    """
    with open(path, "rb") as fh:
        data = fh.read()
    lfanew, = struct.unpack_from("<I", data, 0x3C)
    nsec, = struct.unpack_from("<H", data, lfanew + 6)
    opt, = struct.unpack_from("<H", data, lfanew + 20)
    base, = struct.unpack_from("<I", data, lfanew + 24 + 28)
    for i in range(nsec):
        o = lfanew + 24 + opt + i * 40
        vsize, sva, rsize, raw = struct.unpack_from("<4I", data, o + 8)
        lo = base + sva
        if lo <= va < lo + max(vsize, rsize):
            off = raw + (va - lo)
            return list(struct.unpack_from(f"<{count}I", data, off))
    raise ValueError(f"VA 0x{va:08X} is in no section of {path}")


def _section5(check, led):
    print("\n== 5. the module's stride tables are the CLIENT's own bytes ==")
    exe = os.path.join(vaultpath.vault_root(), CLIENT_EXE)
    if not os.path.isfile(exe):
        led.skip("5. the client image", f"no client at {exe}")
        return
    for name, (va, count) in FVF_TABLE_VAS.items():
        want = tuple(getattr(modelfile, name))
        got = tuple(_pe_read(exe, va, count))
        check(got == want,
              f"{name} at VA 0x{va:08X} is the module's literal, {count} u32 "
              f"from the vaulted build {modelfile.FVF_BUILD}",
              f"{got}" if got != want else f"{count} values")
    # A control: the same read one u32 EARLY must not reproduce the table, or
    # the check above would pass against any address in the neighbourhood.
    va, count = FVF_TABLE_VAS["FVF0"]
    off = tuple(_pe_read(exe, va - 4, count))
    check(off != tuple(modelfile.FVF0),
          "and the same read four bytes early does NOT match -- the VA is "
          "pinned, not merely nearby")


# --- 6. the vertex field map, by refutable prediction -----------------------

def _section6(check, ar, table, by_row):
    print("\n== 6. the field map: each name is a prediction, with a control ==")
    rows = [e for e in ar.entries if (e.flags & 0xFFFF) == 259]
    n_unit = n_norm = 0
    c_unit = c_norm = 0
    t_unit = t_tot = 0
    o_ok = o_tot = 0
    oc_ok = oc_tot = 0
    uv_in = uv_tot = 0
    idx_hi0 = idx_tot = 0
    idx_vals = set()
    seen = set()
    for e in rows[::50]:
        try:
            data = ar.read(e)
            ch = {c: (o, s) for c, o, s in ffna_chunks(data)}
        except ValueError:
            continue
        if PROPS_BLOATED not in ch or PROPS_DEPS_BLOATED not in ch:
            continue
        o, s = ch[PROPS_BLOATED]
        bp = BloatedProps.decode(data[o:o + s])
        fo, fs = ch[PROPS_DEPS_BLOATED]
        fids = [dependency_file_id(*struct.unpack_from("<2H", data,
                                                       fo + 5 + 6 * i))
                for i in range((fs - 5) // 6)]
        for idx in sorted({r.model for r in bp.records}):
            if idx >= len(fids) or fids[idx] in seen:
                continue
            seen.add(fids[idx])
            row = table.get(fids[idx])
            if row is None or by_row.get(row) is None:
                continue
            try:
                geo = ModelFile.decode(ar.read(by_row[row])).geometry()
            except (Undecodable, ValueError):
                continue
            if geo is None or geo.ambiguous:
                continue
            for sm in geo.submodels:
                normals = sm.normals()
                tf = sm.tangent_frame()
                if normals:
                    for k, (x, y, z) in enumerate(normals[:40]):
                        n_norm += 1
                        n_unit += abs(math.sqrt(x * x + y * y + z * z) - 1.0) \
                            < 1e-3
                    # THE CONTROL: the same three floats four bytes early.
                    off = sm.fields[modelfile.FIELD_NORMAL]
                    if off >= 4:
                        for k in range(min(sm.nv, 40)):
                            x, y, z = struct.unpack_from(
                                "<3f", sm.vertex_data, k * sm.stride + off - 4)
                            c_norm += 1
                            c_unit += abs(math.sqrt(x * x + y * y + z * z)
                                          - 1.0) < 1e-3
                for vecs in tf:
                    if not vecs:
                        continue
                    for x, y, z in vecs[:40]:
                        t_tot += 1
                        t_unit += abs(math.sqrt(x * x + y * y + z * z) - 1.0) \
                            < 1e-3
                if normals and tf[0]:
                    for k in range(min(sm.nv, 40)):
                        nx, ny, nz = normals[k]
                        tx, ty, tz = tf[0][k]
                        o_tot += 1
                        o_ok += abs(nx * tx + ny * ty + nz * tz) < 1e-3
                        if k + 1 < min(sm.nv, 40):
                            ax, ay, az = tf[0][k + 1]
                            oc_tot += 1
                            oc_ok += abs(nx * ax + ny * ay + nz * az) < 1e-3
                for w in range(sm.texcoord_sets):
                    for u, v in (sm.texcoords(w) or [])[:40]:
                        if math.isfinite(u) and math.isfinite(v):
                            uv_tot += 1
                            uv_in += -16 <= u <= 16 and -16 <= v <= 16
                off1 = sm.fields.get(1)
                if off1 is not None:
                    for k in range(min(sm.nv, 40)):
                        w, = struct.unpack_from("<I", sm.vertex_data,
                                                k * sm.stride + off1)
                        idx_tot += 1
                        idx_hi0 += (w >> 8) == 0
                        idx_vals.add(w)

    print(f"    normals {n_unit}/{n_norm} unit (control {c_unit}/{c_norm}), "
          f"tangents {t_unit}/{t_tot} unit")
    print(f"    tangent.normal orthogonal {o_ok}/{o_tot} "
          f"(control {oc_ok}/{oc_tot}), uv in +/-16 {uv_in}/{uv_tot}")
    check(n_norm > 10000 and n_unit == n_norm,
          f"BIT 2 IS THE NORMAL: unit on all {n_norm} sampled vertices",
          f"{n_unit}/{n_norm}")
    check(c_norm > 0 and c_unit / c_norm <= NORMAL_CONTROL_MAX,
          f"and the same read four bytes early is unit on under "
          f"{NORMAL_CONTROL_MAX:.0%} -- the offset is the claim",
          f"{c_unit}/{c_norm}")
    check(t_tot > 1000 and t_unit == t_tot,
          f"BITS 12/13 ARE UNIT VECTORS on all {t_tot} sampled",
          f"{t_unit}/{t_tot}")
    check(o_tot > 1000 and o_ok / o_tot >= TANGENT_ORTHO_MIN,
          f"and bit 12 is orthogonal to the normal on at least "
          f"{TANGENT_ORTHO_MIN:.0%} -- a TANGENT FRAME (which is tangent and "
          f"which binormal is NOT established)",
          f"{o_ok}/{o_tot} = {o_ok / max(o_tot, 1):.3f}")
    check(oc_tot > 0 and oc_ok / oc_tot <= TANGENT_ORTHO_CONTROL_MAX,
          f"with the next-vertex control under "
          f"{TANGENT_ORTHO_CONTROL_MAX:.0%}",
          f"{oc_ok}/{oc_tot} = {oc_ok / max(oc_tot, 1):.3f}")
    check(uv_tot > 10000 and 0.9 < uv_in / uv_tot < 1.0,
          "TEXCOORDS are mostly but NOT entirely inside +/-16 -- retail UVs "
          "wrap, so a consumer must not clamp",
          f"{uv_in}/{uv_tot} = {uv_in / max(uv_tot, 1):.3f}")
    # The DISCRIMINATING half is `idx_hi0 == idx_tot` -- a D3DCOLOR with the
    # top three bytes zero on every single vertex is not a colour. The
    # small-value bound is supporting evidence and its numbers MOVED when M6
    # recovered the previously-undecodable models (10 values / max 9 became
    # 22 / max 21), so it is stated as a bound on the KIND of quantity rather
    # than re-pinned to the exact set: an index that fits in 6 bits.
    check(idx_tot > 1000 and idx_hi0 == idx_tot and len(idx_vals) < 64
          and max(idx_vals) < 64,
          f"BIT 1 IS NOT A COLOUR: its high 3 bytes are zero on all "
          f"{idx_tot} and it takes {len(idx_vals)} small values -- the "
          f"GR_FVF_GROUP index, resolved in section 7",
          f"{len(idx_vals)} values, max {max(idx_vals) if idx_vals else '-'}")


# --- 7. the skin binding, and every claim gets a control --------------------

def _section7(check, ar, table, by_row):
    """`trailing` -> groupTransformCount[] + transforms[], and bit 1 as the
    per-vertex selector into them.

    EVERY assertion here has a rival that must SCORE WORSE, because the whole
    decode is arithmetic over small integers and arithmetic over small
    integers agrees with things by accident. The rivals are the ones a corpus
    sweep measured: reading the two arrays in the opposite order (4.04%), and
    taking the selector from the dword one field later (0.03%)."""
    print()
    print("== 7. the skin binding: closure, surjectivity, and two rivals ==")
    # The flags-259 rows are MAP files; skinned geometry lives in the
    # model-type files those maps depend on, so walk the archive itself.
    # `magic(e, 5)` costs five decompressed bytes, not a whole file.
    sms = []
    for e in ar.entries[::37]:
        try:
            head = bytes(ar.magic(e, 5))
            if head[:4] != b"ffna" or head[4] != MODEL_FFNA_TYPE:
                continue
            g = ModelFile.decode(ar.read(e)).geometry()
        except Exception:
            continue
        if g is not None:
            sms.extend(g.submodels)
        if len(sms) > 4000:
            break
    clo = clo_n = rev = 0
    surj = surj_n = late = late_n = 0
    oracle_bad = 0
    diffuse = 0
    bad_count = 0
    groups_seen = 0
    for sm in sms:
            u0, u1, u2 = sm.u_counts
            if len(sm.trailing) != (u0 + u1 + u2 * 3) * 4:
                continue
            if sm.dat_fvf >> FIELD_DIFFUSE & 1:
                diffuse += 1
            w = struct.unpack_from(f"<{u0 + u1}I", sm.trailing, 0) if u0 + u1 else ()
            clo_n += 1
            if sum(w[:u0]) == u1:
                clo += 1
            # RIVAL: the two arrays in the opposite order
            if u0 + u1 and sum(w[u1:u1 + u0]) == u1:
                rev += 1
            if sum(w[:u0]) == u1 and u0:
                counts = w[:u0]
                if counts and min(counts) >= 1 and max(counts) <= 4:
                    pass
                else:
                    bad_count += 1
            has_group = bool(sm.dat_fvf >> FIELD_GROUP & 1)
            if u0 > 1 and not has_group:
                oracle_bad += 1
            if not has_group:
                continue
            off = sm.fields[FIELD_GROUP]
            try:
                vals = {sm.vertex_data[v * sm.stride + off] for v in range(sm.nv)}
                late_v = {sm.vertex_data[v * sm.stride + off + 4]
                          for v in range(sm.nv)} if off + 4 < sm.stride else None
            except IndexError:
                continue
            groups_seen += 1
            surj_n += 1
            if vals == set(range(u0)):
                surj += 1
            if late_v is not None:
                late_n += 1
                if late_v == set(range(u0)):
                    late += 1
    print(f"    {clo_n} sub-models; {groups_seen} carry GR_FVF_GROUP")

    check(clo_n > 200 and clo == clo_n and rev < clo_n * 0.2,
          "CLOSURE (ArenaNet's own assert, MdlCombine:860): the group "
          "transform counts total the transform array, and the reversed-order "
          "rival does NOT",
          f"{clo}/{clo_n} closes, rival {rev}/{clo_n}")
    check(surj_n > 50 and surj == surj_n and late < max(1, late_n) * 0.2,
          "SURJECTIVITY: the group values are exactly {0..u0-1} -- the tight "
          "form, which the weak `max < u0` cannot discriminate -- and the "
          "same field one dword later is NOT",
          f"{surj}/{surj_n} surjective, rival {late}/{late_n}")
    check(oracle_bad == 0 and groups_seen > 50,
          "CROSS-STRUCTURE ORACLE: no sub-model declares more than one group "
          "without carrying GR_FVF_GROUP to select between them",
          f"{oracle_bad} violation(s)")
    check(diffuse == 0 and clo_n > 200,
          "GR_FVF_DIFFUSE is never set on a model -- the client asserts it "
          "must not be (MdlCombine:2075)",
          f"{diffuse} sub-model(s) carry bit {FIELD_DIFFUSE}")
    check(bad_count == 0 and clo_n > 200,
          "every group binds 1..4 transforms -- the bound the client's own "
          "per-group loop supports",
          f"{bad_count} out of range")

    # SABOTAGE: the closure refusal must be able to FIRE. A decoder whose
    # guard cannot go red is a comment, and this arc has shipped five of those.
    hurt = next((sm for sm in sms
                 if sm.u_counts[0] >= 2 and len(sm.trailing) >= 8), None)
    if hurt is None:
        check(False, "SABOTAGE: found no sub-model to corrupt", "none")
    else:
        good = hurt.group_transforms()
        bent = SubModel(hurt.unk, hurt.counts, hurt.nv, hurt.dat_fvf,
                        hurt.stride, hurt.u_counts, hurt.indices,
                        hurt.vertex_data,
                        struct.pack("<I", struct.unpack_from("<I", hurt.trailing, 0)[0] + 1)
                        + hurt.trailing[4:])
        try:
            bent.group_transforms()
            fired = False
        except Undecodable:
            fired = True
        check(len(good) == hurt.u_counts[0] and fired,
              "SABOTAGE: bumping one count by 1 makes group_transforms REFUSE "
              "-- the closure guard can go red",
              f"{len(good)} groups decoded, refusal fired: {fired}")


if __name__ == "__main__":
    sys.exit(main())
