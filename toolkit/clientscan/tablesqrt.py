#!/usr/bin/env python3
r"""REALFIX-C0 -- the client's table sqrt, and the two exhaustive boundary scans
it makes possible.

The client never calls a real square root on the two distances that decide a
snap. It calls the nine instructions at `0x0046E870`, which read a 256-dword
lookup table and reduce to one shift, one add and one add; the result is close
to `sqrt` and is not `sqrt`. So the match test's `< 100.0f` is not a 100.0 u
threshold and gate 1's `> 300.0f` is not a 300.0 u one, and the only honest way
to say what they ARE is to walk every float pattern in a bracketing window
through the client's own arithmetic and read off where it crosses. That is what
`derive_match_radius()` and `derive_gate1_cut()` do -- 2,048,001 and 2,560,001
patterns, nothing sampled -- and the second is the first's positive control,
because it lands on an `89600.0f` boundary this tree already carries from an
independent derivation. The banner below is the argument in full and it
travelled here verbatim with the code it argues about.

WHO READS THIS. `grantsim.py` re-exports every public name from here, at the
site this block was cut from, and it is this module's only in-tree consumer
besides `test_grantsim.py`, whose §C0 re-runs both scans against the pinned
image rather than trusting `MATCH_RADIUS` and `GATE1_CUT`. Nothing else in the
tree imports either name.

`import pinned` IS LOAD-BEARING, NOT DECORATIVE -- do not let an unused-import
sweep take it. `LUT_VA` is a class-(a) build pin, counted by
`toolkit/buildpins.py`, and `buildpins.anchors()` classifies a file that carries
a live row by whether that file imports `pinned`: with the import this module is
ANCHOR_PIN, without it the same row becomes unanchored and shows up on the
bill. The import is also what the pin is FOR -- `read_sqrt_lut()` asks
`pinned.find()` for a build whose sha256 it has verified, so an unknown client
is refused rather than silently producing a confident wrong table.

TWO POINTERS, because two moved lines name a referent that did not move with
them. Neither line was reworded.

  (1) The banner's "THE ONLY BUILD-PINNED ADDRESS IN THIS FILE" was written
      about `grantsim.py` and is now true of THIS file: `LUT_VA` is the one
      class-(a) row here, `grantsim.py` has none left, and the other address
      the banner cites (`0x0046E870`) still lives in a comment, which is
      provenance rather than liability -- `PLAN.md` §7 Q3's boundary, and
      buildpins' class (b).

  (2) THE REFUSAL MESSAGES SAY `grantsim:` AND THAT IS DELIBERATE, not a rename
      this move forgot. They travelled verbatim and they are still correct:
      this module has no CLI, and the command whose output a reader is holding
      when one of them fires is
      `python toolkit/clientscan/grantsim.py --radius`.

READS ONLY, and nothing here runs at import time: `read_sqrt_lut()` is what
calls `pinned.find()` and what opens the image, both on first use, so this
module imports cleanly on a machine with no vault and no client.
"""
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
if os.path.dirname(HERE) not in sys.path:
    sys.path.insert(0, os.path.dirname(HERE))

import pinned                                                  # noqa: E402
from gwpe import PE                                            # noqa: E402
from grantinputs import Refused                                # noqa: E402


# =========================================================================
# REALFIX-C0 -- the decision radius and gate 1's cut, re-derived from the exe
# =========================================================================
#
# THE ONLY BUILD-PINNED ADDRESS IN THIS FILE, and it is counted by
# `toolkit/buildpins.py`. The table sqrt at 0x0046E870 reads a 256-dword lookup
# table; the nine instructions reduce to
#
#     approx_bits = ((exponent_byte + 0x3F) << 23) + LUT[mantissa_top_byte]
#
# with both operands taken from the float's own bit pattern. Every other address
# this file cites lives in a comment or a docstring, which is provenance rather
# than liability -- `PLAN.md` §7 Q3's boundary, and buildpins' class (b).
LUT_VA = 0x0093CAC8

# The scan windows, wide enough that the boundary is interior to both. Stated as
# floats so they are cadence-free: the scan walks every FLOAT PATTERN between
# them, not a sampled grid, which is what makes the answer exhaustive.
MATCH_SCAN = (9000.0, 11000.0)          # 2,048,001 patterns
GATE1_SCAN = (80000.0, 100000.0)        # 2,560,001 patterns
MATCH_NOMINAL = 100.0                   # the literal the client compares against
GATE1_NOMINAL = 300.0                   # ...and MapDist's own 300.0f

# THE ANSWERS, and the functions that produce them are named so nobody has to
# take these on trust: `derive_match_radius()` and `derive_gate1_cut()` re-run
# both exhaustive scans against the pinned image and `test_grantsim.py` §C0 does
# exactly that. Three independent derivations agree (round 5's radius lane, the
# skeptic pass, and this file).
#
#   MATCH: last passing distSq 9983.9990234375 (true 99.9199631), first failing
#          0x461C0000 = 9984.0f (true 99.9199680, approx 100.23970795).
#   GATE1: first snapping distSq 0x47AF0000 = 89600.0f -> true 299.3325909,
#          and a true separation of exactly 300.0 u SNAPS (approx 300.18658).
#
# The single-leg effective threshold is 99.919968 u. `[99.61, 100.00]` is the
# many-leg ACCUMULATION limit and is a different quantity -- do not substitute
# one for the other. The ~99.6 u figure this tree carried until round 5 is
# retired.
MATCH_RADIUS = 99.919968                # derive_match_radius()["true"]
GATE1_CUT = 299.332591                  # derive_gate1_cut()["true"]

# The two boundary patterns, as FLOATS rather than as bit constants: a float
# literal says the same thing without spending a census row, and `_bits()` gets
# the pattern back exactly.
MATCH_BOUNDARY_DISTSQ = 9984.0          # 0x461C0000
GATE1_BOUNDARY_DISTSQ = 89600.0         # 0x47AF0000

_LUT_CACHE = {}


def _bits(x):
    return struct.unpack("<I", struct.pack("<f", float(x)))[0]


def _float(bits):
    return struct.unpack("<f", struct.pack("<I", bits & 0xFFFFFFFF))[0]


def read_sqrt_lut(exe=None):
    """(lut, path, why) -- the 256 dwords at LUT_VA, read with a stdlib PE walk.

    `gwpe.PE` and not `pefile`: CLAUDE.md scopes the disassembler carve-out to
    `msghandler.py` and `codescan.py`, and this is a fixed-offset read that must
    keep working on a bare machine. `pinned.find()` verifies the image's sha256
    before returning it, so an unknown build is refused rather than silently
    producing a confident wrong table.
    """
    if exe is None:
        exe, why = pinned.find()
    else:
        why = "given by the caller"
    key = os.path.abspath(exe)
    if key not in _LUT_CACHE:
        pe = PE(exe)
        off = pe.rva_to_off(LUT_VA - pe.image_base)
        if off is None:
            raise Refused(
                f"grantsim: {hex(LUT_VA)} is not backed by file bytes in {exe}.\n"
                f"  The table sqrt's lookup table cannot be read, so the match "
                f"radius cannot be derived and every number below it would be a "
                f"guess wearing seven significant figures.")
        _LUT_CACHE[key] = list(struct.unpack_from("<256I", pe.data, off))
    return _LUT_CACHE[key], exe, why


def approx_sqrt_bits(bits, lut):
    """The client's nine instructions at 0x0046E870, on a float's bit pattern."""
    exp_byte = (bits >> 24) & 0xFF
    mant_byte = (bits >> 16) & 0xFF
    return (lut[mant_byte] + (((exp_byte + 0x3F) << 23) & 0xFFFFFFFF)) & 0xFFFFFFFF


def approx_sqrt(x, lut):
    """`sqrt(x)` the way the client computes it, error and all."""
    return _float(approx_sqrt_bits(_bits(x), lut))


def _scan_boundary(lut, lo, hi, cut):
    """The FIRST float pattern in [lo, hi] whose table sqrt exceeds `cut`.

    Exhaustive over patterns, not over a value grid: consecutive float bit
    patterns are consecutive representable values, so incrementing the integer
    enumerates every float in the interval exactly once. A sampled scan is what
    produced the "0 under-estimates in 20,000 samples" claim round 5 had to
    withdraw.

    ONE PREDICATE FOR TWO ASYMMETRIC CLIENT TESTS, and `equal_at_cut` is why
    that is safe rather than merely convenient. `> cut` is EXACT for gate 1,
    whose own test is `> 300.0f` (FINDINGS §2.3). The match test is the other
    strictness -- `< 100.0` STRICT (§2.2), so it fails at `>=` -- and the two
    scans coincide only while no pattern's table sqrt lands EXACTLY on the cut.
    That is a fact about this build's LUT and this window, not a theorem, so it
    is COUNTED here and asserted in `test_grantsim.py` §C0 rather than asserted
    in a comment: if a rebuild or a wider window ever makes it non-zero, the
    match boundary moves by one pattern and the check goes red instead of the
    number quietly changing meaning. The counted population is every pattern
    BEFORE the boundary, which is exactly the population that decides it -- a
    tie at or after `first` cannot move a first-crossing either way.
    """
    b_lo, b_hi = _bits(lo), _bits(hi)
    first = None
    equal_at_cut = 0
    for b in range(b_lo, b_hi + 1):
        v = _float(approx_sqrt_bits(b, lut))
        if v == cut:
            equal_at_cut += 1
        if v > cut:
            first = b
            break
    scanned = b_hi - b_lo + 1
    if first is None:
        raise Refused(
            f"grantsim: no float pattern in [{lo}, {hi}] makes the table sqrt "
            f"exceed {cut}. The scan window does not contain the boundary, so "
            f"the derivation has not been performed -- widen it rather than "
            f"reporting the edge.")
    if first == b_lo:
        raise Refused(
            f"grantsim: the boundary is at or below {lo}, the low edge of the "
            f"scan window. The window must BRACKET the boundary or the answer "
            f"is the window's, not the client's.")
    prev = first - 1
    return {
        "first_fail_bits": first,
        "first_fail_distsq": _float(first),
        "true": math.sqrt(_float(first)),
        "approx": _float(approx_sqrt_bits(first, lut)),
        "last_pass_distsq": _float(prev),
        "last_pass_true": math.sqrt(_float(prev)),
        "last_pass_approx": _float(approx_sqrt_bits(prev, lut)),
        "scanned": scanned,
        "equal_at_cut": equal_at_cut,
        "cut": cut,
    }


def derive_match_radius(exe=None):
    """REALFIX-C0. The match test's effective TRUE threshold, exhaustively.

    The client tests `approx_sqrt(distSq) > 100.0f` and misses. So the answer is
    the true sqrt of the first pattern that fails, which is 99.919968 u and not
    100.0 u. 2,048,001 patterns; nothing is sampled.
    """
    lut, exe, why = read_sqrt_lut(exe)
    out = _scan_boundary(lut, MATCH_SCAN[0], MATCH_SCAN[1], MATCH_NOMINAL)
    out.update({"exe": exe, "why": why, "what": "match radius"})
    return out


def derive_gate1_cut(exe=None):
    """REALFIX-C0's POSITIVE CONTROL. Gate 1's cut, by the same nine instructions.

    A method that can only produce the answer it was pointed at is not a method.
    This runs the identical scan against a threshold the tree already carries
    from an independent derivation (`89600.0f`, `authsrv.py`'s own 299.332591),
    over a different 2,560,001-pattern window. It also settles the question a
    round number invites: a true separation of exactly 300.0 u SNAPS, because
    the table sqrt of 90000.0 reads 300.18658.
    """
    lut, exe, why = read_sqrt_lut(exe)
    out = _scan_boundary(lut, GATE1_SCAN[0], GATE1_SCAN[1], GATE1_NOMINAL)
    out["at_300"] = approx_sqrt(GATE1_NOMINAL * GATE1_NOMINAL, lut)
    out["snaps_at_300"] = out["at_300"] > GATE1_NOMINAL
    out.update({"exe": exe, "why": why, "what": "gate-1 cut"})
    return out
