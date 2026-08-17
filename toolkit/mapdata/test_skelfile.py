r"""The skeleton-chunk decoder, its closure oracle, and the fixtures the corpus
cannot provide.

    python toolkit/mapdata/test_skelfile.py           # synthetics + anchors +
                                                      #   a strided corpus pass
    python toolkit/mapdata/test_skelfile.py --all     # the complete flags=515
                                                      #   population (slow)

THE HEADLINE IS CLOSURE, AND HERE IT IS OUR ASSERTION, NOT THE CLIENT'S. The
FA1 parser's success path (`0x00796905`) never compares its cursor to the
chunk's end, so `cursor == len(payload)` is a check the artifact can refuse --
unlike the geometry chunk, whose own closure gate forces agreement. The study
measured **14,571 of 14,571 FA1 chunks closing byte-exact** over the complete
flags=515 population (2026-08-16); `--all` reproduces that number exactly, the
default run reproduces it on a deterministic stride-89 sample.

WHAT THE SYNTHETIC SECTION IS FOR, and it is not decoration: three terms of
the derived layout fire on ZERO or nearly zero corpus files (`n56`: 0 of
14,571 -- its stride is disasm-only and no census can ever test it). The
block-H lesson from the models arc applies verbatim: a term no corpus file
exercises needs a synthetic fixture, not another census. The builder here
writes payloads from ITS OWN size literals, sharing no arithmetic with
`skelfile.TERMS`, and the full-options fixture's total length is asserted as
a HAND-COMPUTED constant -- so builder and decoder are two derivations that
must meet, byte for byte.

THE INDEPENDENT WALKER: every sampled corpus payload is also walked by a
straight-line transliteration in this file with hardcoded strides (no import
of `TERMS`), and the two must agree on the closure VERDICT -- on success
each walker's cursor independently equals the payload end by its own
arithmetic, and comparing the cursors to each other would be a check that
cannot fail (this file's first version claimed exactly that and the review
struck it). Its variant with the n38 var-array moved past the key table is
the ORDER CONTROL: order is only testable where a block reads counts out of
the stream, so the control must collapse where the move is non-vacuous
(n38>0 and n3C>0), must still close where the loop runs over unmoved bytes
(n38>0, n3C==0), and the n38==0 population is EXCLUDED as untestable rather
than counted as passes -- two code paths that are textually identical
cannot disagree.

SABOTAGE: one term altered per variant, scored only over the subpopulation
that fired the term (crediting a mutation with survivals it never faced is
the recorded mistake). Every variant must collapse closure to at most a
MEASURED aliasing ceiling. "Collapses to zero" was this file's first
assertion and the full population REFUTED it (2026-08-16, the same day):
six variants the n=600 study sample and the n=160 default sample both
called clean carry 1-29 survivors at n=14,571 -- a shifted read landing on
bytes that happen to re-close the walk, the same mechanism the study
verified by inspection for n38_mult (row 7868). Worst case is hdr=0x5C at
29/14,571 = 0.2%, so every term stays load-bearing; the ceilings below are
that run's exact counts, survivor rows are printed for inspection, and a
future run above a ceiling is a real regression, not noise. The heavy
aliasers (n38_mult 12.0%, n50_mult) keep their minority bound.

INVARIANTS THE DECODER CANNOT FORCE, run over every sampled sequence record:
span binding `lo <= hi <= n3C` (the key table located independently of the
sequence records; 50,127/50,127 in the study), per-span NON-DECREASING key
times (strictness is deliberately NOT asserted: 10 corpus files carry exact
duplicates, and ArenaNet's MdlAnim:367 reads a different array), and the
1/30 s key-time grid on >= 99% of non-zero times (study: 99.95%).

The anchors are pinned by byte size: 116228 (the hatcher's 0x0056 shell,
FA1 = 29,495 B, COMPOSITED, no geometry chunk), 116366 (the burrowing worm,
FA1 = 82,169 B, not composited, has geometry), and 116703 (the hatcher's
0x0057 body) is pinned to carry NO FA1 chunk at all -- the absence is the
composite mechanism's other half.
"""

import argparse
import os
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import Archive, ffna_chunks, file_id_table  # noqa: E402
from skelfile import (Skeleton, Undecodable, walk,  # noqa: E402
                      container_has_geometry, TERMS, SKELETON_CHUNK,
                      SKELETON_VERSION)
import checks  # noqa: E402
import vaultpath  # noqa: E402

HEAD_FLAGS = 515                 # "addressable model-file head" (FINDINGS §2.1)
STRIDE = 89                      # default sample; prime, ~241 of 21,421 rows

ANCHOR_SHELL = 116228            # FA1 29,495 B; FA6+FA1+FA8, no FA0
ANCHOR_WORM = 116366             # FA1 82,169 B; FA0+FA1+FA5+FA6
ANCHOR_BODY = 116703             # FA0+FA5 -- carries NO FA1
SHELL_FA1_SIZE = 29495
WORM_FA1_SIZE = 82169

#: --all literals, MEASURED 2026-08-16 on the study archive (build 38797).
ALL_HEADS = 21421
ALL_FA1 = 14571
ANOMALY_ROW = 8316               # flags=515, 28 bytes, no ffna magic


# ---------------------------------------------------------------------------
# Section 0 fixtures: a builder with ITS OWN literals. If skelfile.TERMS
# drifts from these, closure on the synthetics goes red -- that is the point.
# ---------------------------------------------------------------------------

def synth(n14=0, n34=0, b2c=((0, 0, 0),), n38=(), keys=(), seqs=(),
          n52=(), n40=0, n44=0, b48=(), n50=(), n54=(), n55=(),
          n56=(), n57=(), n3e=0, flags=None, version=SKELETON_VERSION):
    """A synthetic FA1 payload. `b2c`/`b48` are per-record word tuples;
    `n38`/`n52`/`n5x` are per-record tail counts; `keys` is (time, tag)
    pairs; `seqs` is (lo, hi) pairs. Filler is 0xAA so any mutation that
    reads a count from the wrong offset meets garbage, not zeros."""
    FILL = 0xAA
    h = bytearray(0x58)
    struct.pack_into("<I", h, 0x00, version)
    struct.pack_into("<I", h, 0x14, n14)
    struct.pack_into("<I", h, 0x18, len(seqs))
    struct.pack_into("<I", h, 0x2C, len(b2c))
    struct.pack_into("<I", h, 0x34, n34)
    struct.pack_into("<I", h, 0x38, len(n38))
    struct.pack_into("<H", h, 0x3C, len(keys))
    struct.pack_into("<H", h, 0x3E, n3e)
    struct.pack_into("<I", h, 0x40, n40)
    struct.pack_into("<I", h, 0x44, n44)
    struct.pack_into("<I", h, 0x48, len(b48))
    struct.pack_into("<H", h, 0x50, len(n50))
    struct.pack_into("<H", h, 0x52, len(n52))
    h[0x54], h[0x55], h[0x56], h[0x57] = (len(n54), len(n55),
                                          len(n56), len(n57))
    if flags is None:
        flags = ((8 if n34 else 0) | (0x10 if seqs else 0)
                 | (0x20 if b48 else 0) | (0x40 if n50 else 0)
                 | (0x80 if n38 else 0))
    h[0x08] = flags

    out = bytearray(h)
    out += bytes([FILL]) * (n14 * 16)                       # n14: 16 B each
    out += bytes([FILL]) * (n34 * 24)                       # n34: 24 B each
    out += bytes([FILL]) * (len(b2c) * 16)                  # blk2C fixed: 16 B
    for w0, w2, w4 in b2c:                                  # blk2C variable
        out += struct.pack("<HHH", w0, w2, w4)
        out += bytes([FILL]) * ((w0 + w4) * 16 + w2 * 20)
    for tail in n38:                                        # n38: 12 B + n*4
        rec = bytearray([FILL]) * 12
        struct.pack_into("<I", rec, 4, tail)
        out += rec + bytes([FILL]) * (tail * 4)
    for t, _ in keys:                                       # keys: SoA
        out += struct.pack("<i", t)
    out += bytes(tag for _, tag in keys)
    for lo, hi in seqs:                                     # seqs: 23 B each
        rec = bytearray([FILL]) * 23
        rec[0x0D], rec[0x0E] = lo, hi
        out += rec
    for tail in n52:                                        # n52: 16 B + n*4
        rec = bytearray([FILL]) * 16
        struct.pack_into("<I", rec, 0x0C, tail)
        out += rec + bytes([FILL]) * (tail * 4)
    out += bytes([FILL]) * (n40 * 0x16 + n44 * 12)          # n40/n44
    out += bytes([FILL]) * (len(b48) * 20)                  # blk48 fixed: 20 B
    for w0, w2 in b48:                                      # blk48 variable
        out += struct.pack("<HH", w0, w2)
        out += bytes([FILL]) * ((w0 + w2) * 16)
    for tails, mult in ((n50, 8), (n54, 8), (n55, 8), (n56, 5), (n57, 20)):
        for tail in tails:                                  # 8 B + n*mult
            rec = bytearray([FILL]) * 8
            struct.pack_into("<I", rec, 4, tail)
            out += rec + bytes([FILL]) * (tail * mult)
    out += bytes([FILL]) * (n3e * 4)                        # n3E arrays
    out += bytes([FILL]) * (n3e * 8)
    return bytes(out)


#: The full-options fixture: every optional block fires, every variable tail
#: is non-zero somewhere. Its length is asserted against this HAND-COMPUTED
#: constant -- worked out block by block in the U1 session notes, not by
#: running either implementation.
FULL_KW = dict(
    n14=2, n34=1, b2c=((1, 1, 0), (0, 0, 2)), n38=(0, 3),
    keys=((0, 2), (3333, 6), (3333, 2), (6667, 6)),
    seqs=((0, 2), (2, 4)), n52=(2,), n40=1, n44=2, b48=((1, 1),),
    n50=(1,), n54=(2,), n55=(2,), n56=(3,), n57=(1,), n3e=2)
FULL_LEN = 623

#: One term altered per variant, mirrored from the study's suite. Each is
#: held to its MEASURED full-population aliasing ceiling (2026-08-16 --all
#: run; see the docstring). n38_mult and n50_mult alias on repeated small
#: counts far more often and get a fractional bound instead.
SABOTAGE_CLEAN = [
    ("hdr=0x54", "hdr", 0x54), ("hdr=0x5C", "hdr", 0x5C),
    ("n14_elem=12", "n14_elem", 12), ("n34_elem=20", "n34_elem", 20),
    ("b2c_fixed=12", "b2c_fixed", 12), ("b2c_sub=4", "b2c_sub", 4),
    ("b2c_m04=12", "b2c_m04", 12), ("b2c_m20=16", "b2c_m20", 16),
    ("n3c_elem=4", "n3c_elem", 4), ("n18_elem=0x16", "n18_elem", 0x16),
    ("n40_elem=0x14", "n40_elem", 0x14), ("b48_fixed=16", "b48_fixed", 16),
    ("b48_m=20", "b48_m", 20), ("n57_mult=8", "n57_mult", 8),
]
SABOTAGE_ALIASING = [
    ("n38_mult=8", "n38_mult", 8), ("n50_mult=4", "n50_mult", 4),
]

#: The exact survivor counts of the 2026-08-16 full-population run --
#: deterministic against the pinned study archive, so exceeding one is a
#: regression in the walk, not sampling noise. Default-stride pools are
#: subsets of the population, so these ceilings hold there by construction
#: (measured 0 survivors at stride 89).
SABOTAGE_CEILING = {
    "hdr=0x54": 1, "hdr=0x5C": 29, "n14_elem=12": 1, "n34_elem=20": 1,
    "b2c_fixed=12": 0, "b2c_sub=4": 1, "b2c_m04=12": 0, "b2c_m20=16": 0,
    "n3c_elem=4": 1, "n18_elem=0x16": 2, "n40_elem=0x14": 0,
    "b48_fixed=16": 0, "b48_m=20": 0, "n57_mult=8": 0,
}
DEPENDS = {
    "hdr": None, "n14_elem": "n14", "n34_elem": "n34",
    "b2c_fixed": None, "b2c_sub": None, "b2c_m04": "b2c_w04",
    "b2c_m20": "b2c_w2", "n38_mult": "n38", "n3c_elem": "n3C",
    "n18_elem": "n18", "n40_elem": "n40", "b48_fixed": "n48",
    "b48_m": "b48_w", "n50_mult": "n50", "n57_mult": "n57",
}


def mutate(key, val):
    T = dict(TERMS)
    T[key] = val
    return T


# ---------------------------------------------------------------------------
# The independent walker: hardcoded strides, no import of TERMS. With
# move_n38=True the n38 var-array is consumed AFTER the key table -- the
# order control. All other terms untouched.
# ---------------------------------------------------------------------------

def indep_walk(p, move_n38=False):
    """Returns (ok, cursor, gate)."""
    n = len(p)
    if n < 4 or struct.unpack_from("<I", p, 0)[0] != 0x26 or n < 0x58:
        return False, 0, "pre"
    u8 = lambda o: p[o]
    u16 = lambda o: struct.unpack_from("<H", p, o)[0]
    u32 = lambda o: struct.unpack_from("<I", p, o)[0]
    n14, n18 = u32(0x14), u32(0x18)
    n2c, n34, n38 = u32(0x2C), u32(0x34), u32(0x38)
    n3c, n3e = u16(0x3C), u16(0x3E)
    n40, n44, n48 = u32(0x40), u32(0x44), u32(0x48)
    n50, n52 = u16(0x50), u16(0x52)
    n54, n55, n56, n57 = u8(0x54), u8(0x55), u8(0x56), u8(0x57)
    if n2c == 0:
        return False, 0x58, "n2c_zero"
    c = 0x58

    class Dead(Exception):
        pass

    def take(k):
        nonlocal c
        if k < 0 or c + k > n:
            raise Dead()
        c += k

    def var(count, elem, cnt_at, mult):
        nonlocal c
        for _ in range(count):
            rec = c
            take(elem)
            if rec + cnt_at + 4 > n:
                raise Dead()
            take(u32(rec + cnt_at) * mult)

    def do_n38():
        var(n38, 12, 4, 4)

    def do_keys():
        take(n3c * 5)

    try:
        take(n14 * 16)
        take(n34 * 24)
        take(n2c * 16)
        for _ in range(n2c):
            sub = c
            take(6)
            take((u16(sub) + u16(sub + 4)) * 16 + u16(sub + 2) * 20)
        if move_n38:
            do_keys(), do_n38()
        else:
            do_n38(), do_keys()
        take(n18 * 23)
        var(n52, 16, 12, 4)
        take(n40 * 22 + n44 * 12)
        take(n48 * 20)
        for _ in range(n48):
            sub = c
            take(4)
            take((u16(sub) + u16(sub + 2)) * 16)
        var(n50, 8, 4, 8)
        var(n54, 8, 4, 8)
        var(n55, 8, 4, 8)
        var(n56, 8, 4, 5)
        var(n57, 8, 4, 20)
        take(n3e * 4)
        take(n3e * 8)
    except Dead:
        return False, c, "gate"
    return c == n, c, "close" if c == n else "short"


# ---------------------------------------------------------------------------


def section0(check):
    print("\n== section 0: synthetics (no vault) ==")

    minimal = synth()
    check(len(minimal) == 110,
          "minimal fixture is 110 bytes by the builder's own arithmetic",
          f"got {len(minimal)}")
    check(walk(minimal)["ok"], "minimal fixture closes")
    check(Skeleton.decode(minimal).sound_events() == [],
          "sound_events() is [] when n40 == n44 == 0 -- the walker records "
          "no n40n44 span there, and the unguarded unpack was the U6 "
          "strided writer's first crash (2026-08-16)")

    full = synth(**FULL_KW)
    check(len(full) == FULL_LEN,
          f"full-options fixture is the hand-computed {FULL_LEN} bytes",
          f"got {len(full)}")
    r = walk(full)
    check(r["ok"], "full-options fixture closes")
    exercised = {"n14", "n34", "b2c_w04", "b2c_w2", "n38", "n3C", "n18",
                 "n52", "n40", "n44", "n48", "b48_w", "n50", "n54", "n55",
                 "n56", "n57", "n3E"}
    check(exercised <= r["fired"],
          "every optional term fires in the full fixture -- including n56, "
          "which 0 of 14,571 corpus files can test",
          f"missing: {sorted(exercised - r['fired'])}")

    # decode layer
    sk = Skeleton.decode(full)
    check(sk.seq_count == 2, "seq_count reads +0x18")
    ss = sk.sequences()
    check([(s["lo"], s["hi"]) for s in ss] == [(0, 2), (2, 4)],
          "sequence lo/hi round-trip through the typed layer")
    check(sk.key_times_raw() == [0, 3333, 3333, 6667]
          and sk.key_tags() == [2, 6, 2, 6],
          "key table is structure-of-arrays: times then tags, not AoS")
    check(abs(sk.key_times_s()[3] - 0.06667) < 1e-9,
          "key times scale by 1e-5 s")
    spans = sorted(sk.spans, key=lambda s: s[1])
    tiled = spans[0][1] == 0 and all(
        spans[i][1] + spans[i][2] == spans[i + 1][1]
        for i in range(len(spans) - 1)) \
        and spans[-1][1] + spans[-1][2] == len(full)
    check(tiled, "spans tile the payload exactly -- what a U6 writer preserves")
    blk = sk.block_bytes("blk2C")
    check(blk is not None and len(blk) == 2 * 16 + 42 + 38
          and sk.block_bytes("no-such-block") is None,
          "block_bytes returns the blk2C span (fixed 32 + records 42 and "
          "38, the builder's own arithmetic) and None for an unknown name")

    # the client's own refusals, each beside the passing control above
    r = walk(synth(b2c=()))
    check(not r["ok"] and r["gate"] == "G05_n2C_zero",
          "n2C == 0 is the client's hard reject (error 12), not a walk")
    try:
        Skeleton.decode(synth(b2c=()))
        check(False, "decode raises on n2C == 0")
    except Undecodable as e:
        check(e.gate == "G05_n2C_zero", "decode raises on n2C == 0")
    r = walk(synth(version=0x27))
    check(not r["ok"] and r["gate"] == "G01_version",
          "version != 0x26 refused (0x0079495D)")
    check(walk(b"\x26\x00")["gate"] == "G00_size4", "under 4 bytes refused")
    check(walk(bytes(80))["gate"] == "G01_version",
          "an 80-byte zero payload dies at the version gate first")

    r = walk(full[:-10])
    check(not r["ok"] and r["gate"] == "G23_n3E_b",
          "a truncated payload dies AT A NAMED GATE, never silently",
          f"gate {r['gate']}")

    # sabotage on the synthetic -- the only place n56's stride is testable.
    # One check PER variant: the ledger's floor is what notices if this loop
    # silently stops iterating, and 18 measurements reported as 1 check was
    # this file's own reviewed defect.
    for name, key, val in SABOTAGE_CLEAN + SABOTAGE_ALIASING + [
            ("n56_mult=8", "n56_mult", 8), ("n56_mult=4", "n56_mult", 4)]:
        check(not walk(full, mutate(key, val))["ok"],
              f"synthetic sabotage {name} breaks the full fixture")

    ok, cur, _ = indep_walk(full)
    check(ok and cur == len(full),
          "the independent transliteration agrees on the full fixture")
    ok, _, _ = indep_walk(full, move_n38=True)
    check(not ok, "moving n38 past the key table breaks the fixture "
                  "(order is real where counts come off the stream)")


def synth_anim():
    """The U2 typed-layer fixture: an FA1 whose channel PAYLOADS carry real
    content (synth() fills them with 0xAA), built from its own literals so
    the accessors and the builder are two derivations that must meet.

    Layout under test (studies/anim/FINDINGS.md §2): blk2C payload
    sections are times-prefix SoA -- w0 int32 times + w0 vec3f, w2 int32
    times + w2 float4, w4 absent here; blk48's sub-header is 4 bytes and
    both its sections are times + vec3f; n40 is n40 sorted u32 seq
    indices then n40 18-byte bodies; n3E is times then {type, param}.
    """
    h = bytearray(0x58)
    struct.pack_into("<I", h, 0x00, SKELETON_VERSION)
    struct.pack_into("<I", h, 0x18, 1)               # n18 = 1 sequence
    struct.pack_into("<I", h, 0x2C, 1)               # n2C = 1 node
    struct.pack_into("<H", h, 0x3C, 2)               # n3C = 2 keys
    struct.pack_into("<H", h, 0x3E, 2)               # n3E = 2 events
    struct.pack_into("<I", h, 0x40, 1)               # n40 = 1 sound event
    struct.pack_into("<I", h, 0x44, 1)               # n44 = 1 tail record
    struct.pack_into("<I", h, 0x48, 1)               # n48 = 1 track
    h[0x08] = 0x30                                   # bits 4|5: n18, n48
    out = bytearray(h)
    # blk2C: fixed {base, flags bit28}, payload w0=2, w2=2, w4=0
    out += struct.pack("<3fI", 1.5, 2.5, 3.5, 0x10000000)
    out += struct.pack("<3H", 2, 2, 0)
    out += struct.pack("<2i", 0, 100000)             # trans times
    out += struct.pack("<6f", 0, 0, 0, 10, 20, 30)   # trans vec3s
    out += struct.pack("<2i", 0, 100000)             # rot times
    out += struct.pack("<8f", 0, 0, 0, 1, 1, 0, 0, 0)  # rot quats
    # keys (SoA), then the 23-byte sequence record
    out += struct.pack("<2i", 0, 100000)
    out += bytes((2, 6))
    seq = bytearray(23)
    seq[0x00] = 7
    struct.pack_into("<I", seq, 0x01, 42)
    struct.pack_into("<I", seq, 0x05, 0)             # clamp-window start
    struct.pack_into("<I", seq, 0x09, 100000)        # clamp-window end
    seq[0x0D], seq[0x0E] = 0, 2                      # lo, hi
    struct.pack_into("<I", seq, 0x0F, 0)
    struct.pack_into("<f", seq, 0x13, 1.0)
    out += seq
    # n40 (SoA: index array then 18-byte bodies), then the n44 tail
    out += struct.pack("<I", 0)                      # seq index 0
    out += struct.pack("<iI", 50000, 0) + bytes(10)  # body: time, path, tail
    out += bytes(range(12))                          # n44: carried raw
    # blk48: fixed {base, flags bit27, u10}, payload w0=2, w2=0
    out += struct.pack("<3fII", 0.0, 0.0, 0.5, 0x08000000, 9)
    out += struct.pack("<2H", 2, 0)
    out += struct.pack("<2i", 0, 200000)
    out += struct.pack("<6f", 0, 0, 1, 0, 0, 2)
    # n3E: arrA times, arrB {type, param}
    out += struct.pack("<2i", 0, 50000)
    out += struct.pack("<4I", 0, 0, 1, 5)
    return bytes(out)


def section0b(check):
    print("\n== section 0b: the U2 typed animation layer (no vault) ==")
    p = synth_anim()
    r = walk(p)
    check(r["ok"], "anim fixture closes", f"gate {r['gate']}")
    sk = Skeleton.decode(p)

    an = sk.anims()
    check(len(an) == 1, "anims(): one record per node (n2C)")
    a = an[0]
    check(a["base"] == (1.5, 2.5, 3.5),
          "anims(): the record's first 12 bytes are the base vec3")
    check(a["flags"] == 0x10000000 and a["emitter_count"] == 0
          and not a["light_attach"] and a["link"] == 0,
          "anims(): flags dword and its named bit-fields round-trip")
    check(a["trans"] == ([0, 100000],
                         [(0.0, 0.0, 0.0), (10.0, 20.0, 30.0)]),
          "anims(): translation channel is times-prefix SoA "
          "(N int32 times, then N vec3f)")
    check(a["rot"] == ([0, 100000],
                       [(0.0, 0.0, 0.0, 1.0), (1.0, 0.0, 0.0, 0.0)]),
          "anims(): rotation channel is times then float4 quaternions")
    check(a["aux"] is None, "anims(): absent w4 section reads as None")

    tr = sk.tracks()
    check(len(tr) == 1 and tr[0]["base"] == (0.0, 0.0, 0.5)
          and tr[0]["u10"] == 9 and tr[0]["looping"],
          "tracks(): blk48 record fields, including the bit-27 loop flag")
    check(tr[0]["ch0"] == ([0, 200000],
                           [(0.0, 0.0, 1.0), (0.0, 0.0, 2.0)])
          and tr[0]["ch1"] is None,
          "tracks(): blk48 sections are times + vec3f after a 4-byte "
          "sub-header")

    ev = sk.sound_events()
    check(ev == [{"seq": 0, "time": 50000, "path_index": 0,
                  "raw_tail": bytes(10)}],
          "sound_events(): n40 is SoA -- seq-index array, then 18-byte "
          "{time, pathIndex} bodies")

    times, recs = sk.event_track()
    check(times == [0, 50000] and recs == [(0, 0), (1, 5)],
          "event_track(): n3E arrA times + arrB {type, param} records")

    s = sk.sequences()[0]
    check(s["u8_00"] == 7 and s["u32_01"] == 42 and s["u32_0F"] == 0,
          "sequences(): raw fields round-trip")
    check(s["start"] == 0 and s["end"] == 100000
          and s["start"] == s["u32_05"] and s["end"] == s["u32_09"],
          "sequences(): start/end (the MdlSeq 0x00792F56 clamp window, "
          "disk u32@+0x05/+0x09) alias the raw fields")


def section1(check, ar, idt):
    print("\n== section 1: the anchors ==")
    shell = ar.read(ar.row(idt[ANCHOR_SHELL]))
    sk = Skeleton.from_container(shell)
    check(sk is not None and len(sk.payload) == SHELL_FA1_SIZE,
          f"116228 (hatcher shell): FA1 is {SHELL_FA1_SIZE} B and decodes",
          f"got {len(sk.payload) if sk else None}")
    check(sk is not None and sk.composited,
          "116228 carries MODEL_SKELETON_FLAG_COMPOSITED")
    check(not container_has_geometry(shell),
          "116228 carries no geometry chunk -- the bit and the chunk table "
          "agree from two places in the archive")

    worm = ar.read(ar.row(idt[ANCHOR_WORM]))
    sk = Skeleton.from_container(worm)
    check(sk is not None and len(sk.payload) == WORM_FA1_SIZE,
          f"116366 (worm): FA1 is {WORM_FA1_SIZE} B and decodes")
    check(sk is not None and not sk.composited
          and container_has_geometry(worm),
          "116366 is self-contained: bit clear, geometry present")

    body = ar.read(ar.row(idt[ANCHOR_BODY]))
    check(Skeleton.from_container(body) is None,
          "116703 (the 0x0057 body) carries NO FA1 chunk -- the absence is "
          "the composite mechanism's other half")

    via_load = Skeleton.load(ANCHOR_WORM, ar)
    check(via_load is not None and via_load.payload == (sk.payload
          if sk is not None else None),
          "Skeleton.load(file_id) resolves through the id table to the "
          "same payload as the container path")

    # U2 typed layer against real bytes (values measured 2026-08-16; a
    # drift here is a decoder regression, the archive is pinned). The two
    # unforceable checks each carry a FAILING CONTROL beside them -- the U2
    # review's R-5: an assertion whose rival is never run is not a
    # measurement, and both controls' values were measured by the review
    # before being pinned here.
    an = sk.anims()
    check(len(an) == 20 == sk.header["n2C"]
          and sum(a["emitter_count"] for a in an) == 10 == sk.header["n34"],
          "worm: 20 blk2C node records whose emitter-attach counts sum to "
          "n34 -- the invariant the MdlAnim:1121 assert enforces at "
          "runtime, from file bytes the decoder cannot force")
    import math as _math
    quats = [q for a in an if a["rot"] for q in a["rot"][1]]
    unit = sum(1 for q in quats
               if abs(_math.sqrt(sum(c * c for c in q)) - 1) < 0.01)
    check(len(quats) == 3919 and unit == 3919,
          "worm: all 3,919 rotation-channel float4s are unit quaternions "
          "within 1% -- the reading the misaligned 2026-08-16 overlay "
          "refuted at 4/19,460",
          f"{unit}/{len(quats)}")
    # CONTROL: the same PAYLOAD BYTES under a misaligned float4 overlay
    # (stride 20, the refuted reading's rotation-group stride). HONESTY
    # BOUND: on THIS anchor no misaligned overlay collapses to the
    # corpus-wide ~0.3% -- the worm's rotations are dominated by
    # near-identity quaternions, so any 4-float window holding one +-1
    # and three ~0s reads unit-norm and every misalignment scores ~35%
    # here (measured: 16-byte tiling 35.0%, stride 20 34.9%). The control
    # therefore asserts the GAP (<50% vs the true layout's 100.000%), and
    # the 0.30%-vs-100.000% separation at equal tolerance lives in the
    # corpus run (study P4 + review R-2), not in this anchor.
    blk = sk.block_bytes("blk2C")
    var = blk[16 * sk.header["n2C"]:]
    aos_n = (len(var) - 16) // 20 + 1 if len(var) >= 16 else 0
    aos_unit = sum(
        1 for i in range(aos_n)
        if abs(_math.sqrt(sum(
            c * c for c in struct.unpack_from("<4f", var, 20 * i))) - 1)
        < 0.01)
    check(aos_n and aos_unit < aos_n * 0.5,
          "CONTROL: a misaligned float4 overlay on the same bytes falls "
          "far below the true layout's 100.000% (gap, not collapse -- "
          "see comment)",
          f"{aos_unit}/{aos_n}")
    ev = sk.sound_events()
    check(len(ev) == 6
          and [e["seq"] for e in ev] == sorted(e["seq"] for e in ev)
          and all(e["seq"] < sk.seq_count for e in ev),
          "worm: 6 sound events, seq-index prefix sorted (the client "
          "binary-searches it) and in range")
    links = [a["link"] for a in an]
    check(all(b < len(an) and b <= i for i, b in enumerate(links)),
          "worm: every node's link byte references an earlier-or-self "
          "node (the hierarchy invariant, 121,532/121,532 corpus-wide)")
    # CONTROL: shuffled links must violate `link <= index` -- `< n2C`
    # alone is a multiset property a shuffle preserves, so only this half
    # carries the hierarchy claim (review-measured: ~23% violations under
    # shuffle corpus-wide). Deterministic rotation, no RNG in tests.
    shuffled = links[10:] + links[:10]
    check(any(not (b <= i) for i, b in enumerate(shuffled)),
          "CONTROL: rotating the worm's links violates the invariant "
          "(the check above has power)")


def section2(check, led, ar, stride):
    print(f"\n== section 2: corpus, stride {stride} ==")
    t0 = time.time()
    heads = [e.index for e in ar.entries if e.flags == HEAD_FLAGS]
    if stride == 1:
        check(len(heads) == ALL_HEADS,
              f"flags={HEAD_FLAGS} head population is exactly {ALL_HEADS}",
              f"got {len(heads)}")
    else:
        check(len(heads) > 20000,
              f"flags={HEAD_FLAGS} head population enumerated",
              f"{len(heads)} rows")

    sample = heads[::stride]
    payloads = []                     # (row, fa1_payload, has_geo)
    no_fa1 = anomalies = 0
    for row in sample:
        data = ar.read(ar.row(row))
        if data[:4] != b"ffna":
            anomalies += 1
            if stride == 1:
                check(row == ANOMALY_ROW,
                      "the single non-ffna head is the known row 8316",
                      f"row {row}")
            continue
        fa1 = None
        for cid, off, size in ffna_chunks(data):
            if cid == SKELETON_CHUNK:
                fa1 = bytes(data[off:off + size])
                break
        if fa1 is None:
            no_fa1 += 1
            continue
        payloads.append((row, fa1, container_has_geometry(data)))
    print(f"  sample: {len(sample)} rows -> {len(payloads)} FA1 carriers, "
          f"{no_fa1} without FA1, {anomalies} non-ffna "
          f"({time.time() - t0:.0f}s)")
    check(len(payloads) > 0,
          "the sample is non-empty -- every aggregate below would pass "
          "vacuously on zero payloads", f"{len(payloads)} carriers")

    # closure, the independent walker, and the COMPOSITED equivalence
    closed = agree = comp_ok = 0
    for row, p, has_geo in payloads:
        r = walk(p)
        if r["ok"]:
            closed += 1
        ok, _cur, _ = indep_walk(p)
        # The comparison is the closure VERDICT. On success each walker's
        # cursor independently equals the payload end by its own arithmetic
        # -- comparing them to each other would be n == n, a check that
        # cannot fail (this file's own reviewed defect); on failure the two
        # report death differently (the module reports the take's start,
        # the transliteration its running cursor), so only ok is compared.
        if ok == r["ok"]:
            agree += 1
        h = r["hdr"]
        if h is not None and bool(h["flags"] & 1) == (not has_geo):
            comp_ok += 1
    n = len(payloads)
    if stride == 1:
        check(n == ALL_FA1, f"FA1 population is exactly {ALL_FA1}",
              f"got {n}")
    check(closed == n, f"closure {closed}/{n} -- and closure is OUR check; "
          "the client never compares cursor to end", f"short {n - closed}")
    check(agree == n, "the independent transliteration agrees on every "
          f"closure verdict ({agree}/{n})")
    check(comp_ok == n,
          f"COMPOSITED bit <=> no geometry chunk, {comp_ok}/{n} -- two "
          "independent places in the archive, unforceable by this decoder")

    # invariants over the typed layer -- and the presence bitmap through the
    # MODULE'S OWN flags_presence(), not a private copy of its pairs (the
    # reviewed defect: a wrong bit in the shipped method would have passed
    # green while the test measured its own inline table)
    span_viol = spans_seen = mono_viol = 0
    grid_ok = grid_n = 0
    presence_ok = presence_n = 0
    quiet_n = quiet_ok = 0
    quiet_err = None
    for row, p, _ in payloads:
        sk = Skeleton.decode(p)
        if sk.header["n40"] == 0 and sk.header["n44"] == 0:
            # The no-n40n44-span majority (72.5% of the corpus):
            # sound_events() must answer [], not raise. It raised a
            # TypeError here until 2026-08-16, found by rung U6's first
            # strided writer run over the corpus and fixed under the U6
            # review's scoped permission (studies/unitwrite/FINDINGS.md
            # §2). Guarded so a regression is the named FAIL below, not
            # a dead run with no verdict.
            quiet_n += 1
            try:
                if sk.sound_events() == []:
                    quiet_ok += 1
            except Exception as e:                        # noqa: BLE001
                quiet_err = quiet_err or f"row {row}: {e!r}"
        for _bit, flagged, present in sk.flags_presence():
            presence_n += 1
            if flagged == present:
                presence_ok += 1
        times = sk.key_times_raw()
        n3c = sk.header["n3C"]
        for s in sk.sequences():
            lo, hi = s["lo"], s["hi"]
            if not lo <= hi <= n3c:
                span_viol += 1
                continue
            spans_seen += 1
            seg = times[lo:hi]
            if any(seg[i + 1] < seg[i] for i in range(len(seg) - 1)):
                mono_viol += 1
        for t in times:
            if t:
                grid_n += 1
                # 1/30 s is 3333.3~ raw units -- never an exact integer, so
                # "on the grid" means NEAREST integer to a frame multiple,
                # the study's own formula (keytimes.py: |t*1e-5*30 - round|
                # < 1e-3 of a frame).
                f30 = t * 1e-5 * 30.0
                if abs(f30 - round(f30)) < 1e-3:
                    grid_ok += 1
    check(presence_ok == presence_n,
          f"flag bits 3/5/6/7 mirror block presence via the module's own "
          f"flags_presence(), {presence_ok}/{presence_n}")
    check(quiet_n > 0 and quiet_ok == quiet_n,
          f"sound_events() returns [] on every sampled no-n40n44-span "
          f"file ({quiet_ok}/{quiet_n}) -- the U6-found TypeError, "
          "regression-pinned", quiet_err or "")
    check(span_viol == 0,
          f"span binding lo <= hi <= n3C over {spans_seen} records, "
          "0 violations -- the check the decoder cannot force")
    check(mono_viol == 0,
          f"key times NON-DECREASING within every span ({spans_seen}); "
          "strictness deliberately not asserted (10 corpus duplicates)")
    if grid_n:
        check(grid_ok / grid_n >= 0.99,
              f"non-zero key times on the 1/30 s grid: "
              f"{grid_ok}/{grid_n} ({grid_ok / grid_n:.2%}, study 99.95%)")
    else:
        led.skip("key-time grid", "sample carried no non-zero key times")

    # sabotage, scored over the subpopulation that fired each term
    for name, key, val in SABOTAGE_CLEAN:
        dep = DEPENDS[key]
        pool = [(row, p) for row, p, _ in payloads
                if dep is None or dep in walk(p)["fired"]]
        if not pool:
            led.skip(f"sabotage {name}", "no sampled file fires the term")
            continue
        surv = [row for row, p in pool if walk(p, mutate(key, val))["ok"]]
        ceiling = SABOTAGE_CEILING[name]
        check(len(surv) <= ceiling,
              f"sabotage {name}: closure collapses {len(pool)} -> at most "
              f"the measured aliasing ceiling of {ceiling}",
              f"{len(surv)} survived"
              + (f" (rows {surv[:8]})" if surv else ""))
    for name, key, val in SABOTAGE_ALIASING:
        dep = DEPENDS[key]
        pool = [p for _, p, _ in payloads if dep in walk(p)["fired"]]
        if not pool:
            led.skip(f"sabotage {name}", "no sampled file fires the term")
            continue
        survivors = sum(1 for p in pool if walk(p, mutate(key, val))["ok"])
        check(survivors < len(pool) * 0.25,
              f"sabotage {name}: data-aliasing survivors stay a minority "
              f"({survivors}/{len(pool)}; study measured 12% for n38)")

    # The order control, both directions -- with the vacuous half SPLIT,
    # because 'still closes with n38 == 0' compares two textually identical
    # code paths and cannot fail (the reviewed defect). Only files where the
    # moved loop actually runs over relocated bytes are informative.
    hot, semi, triv = [], [], []
    for _row, p, _ in payloads:
        h = walk(p)["hdr"]
        if not h:
            continue
        if h["n38"] and h["n3C"]:
            hot.append(p)
        elif h["n38"]:
            semi.append(p)          # loop runs, but over unmoved bytes
        else:
            triv.append(p)          # zero-iteration loop; cannot differ
    if hot:
        moved_ok = sum(1 for p in hot if indep_walk(p, move_n38=True)[0])
        check(moved_ok == 0,
              f"order control: moving n38 past the keys collapses all "
              f"{len(hot)} non-vacuous files")
    else:
        led.skip("order control (hot half)", "no sampled file has n38 and n3C")
    if semi:
        semi_ok = sum(1 for p in semi if indep_walk(p, move_n38=True)[0])
        check(semi_ok == len(semi),
              f"order control: with n3C == 0 the move relocates nothing and "
              f"all {len(semi)} n38-carrying files still close "
              f"({len(triv)} further files have n38 == 0 and are excluded "
              f"as untestable, not counted as passes)")
    else:
        led.skip("order control (vacuous-but-informative half)",
                 "no sampled file has n38 without n3C")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true",
                    help="the complete flags=515 population (slow: reads and "
                         "decompresses every head row, ~45 min)")
    args = ap.parse_args()

    # Floor from the real green default run, 2026-08-17: 92 checks executed
    # (stride 89, the study archive; 71 before the U2 typed-layer section
    # 0b landed, 89 before the U2 review added the two failing controls
    # and folded one forced check, then TWO sound_events empty-span
    # regression checks -- U6's arc pinned the corpus population and a
    # parallel session pinned the synthetic fixture, independently within
    # the hour; the merge keeps BOTH because they cover different ground.
    # Set below that only by the checks whose pools can legitimately
    # empty on a different sample (the 16 corpus sabotage variants and
    # the two order-control halves declare skips); the mandatory core
    # is 74.
    led = checks.Ledger("skeleton chunk (0xFA1)", floor=84)
    check = checks.adopt(led)

    section0(check)
    section0b(check)

    dat = os.path.join(
        vaultpath.require_dir("dat_study", why="the FA1 closure corpus"),
        "Gw.dat")
    ar = Archive(dat)
    idt = file_id_table(ar)
    section1(check, ar, idt)
    section2(check, led, ar, stride=1 if args.all else STRIDE)

    sys.exit(led.verdict())


if __name__ == "__main__":
    main()
