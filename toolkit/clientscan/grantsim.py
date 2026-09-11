#!/usr/bin/env python3
r"""WOULD A DIFFERENT GRANT POLICY HAVE SNAPPED -- and this file cannot rank them.

    python toolkit/clientscan/grantsim.py --radius        # REALFIX-C0, the derivation
    python toolkit/clientscan/grantsim.py --calibrate     # C1/C2 against the vault
    python toolkit/clientscan/grantsim.py --counterfactual
    python toolkit/clientscan/grantsim.py --band          # C5, and the refusal to rank

REALFIX-H1, built to the committed spec at `studies/movement/REALFIX.md` §2. It
replays one of OUR captures' own c2s control stream (`0x003D` heading with its
`vec2` and `movementType`, `0x003E` click, `0x0047` stop) through a candidate
grant policy, drives a byte-shaped rebuild of the client's `0x005FE950`
destination bake with the resulting grants, and asks the client's own question --
does the SYNC copy's dead-reckoned `+0x78` still lie on the client's own history
polyline -- at the client's own two caller classes.

WHAT IT IS FOR, and the sentence is `REALFIX.md` §2.1 verbatim: a CALIBRATION
instrument, a REFUSAL instrument and an EXPOSURE meter -- **not a ranker.**
Round 5's §6.4 is the reason and it is a finding rather than a limitation: with
the match test on, leads 0 u and 86 u score identically on three of four
counterfactual captures and only the already-REFUTED 766 u lead separates; with
the match test off the ordering INVERTS and the refuted configuration wins on
three of four. The parameter the ranking is not invariant on is the match test's
PRESENCE, which the drafted sweep never varied. So `rank_or_refuse()` prints an
ordering only when one survives the whole band including that axis, and on the
real substrate it prints nothing. A ranking printed outside the band is a RED
check in `test_grantsim.py`, not a caveat in prose.

WHERE IT SITS AMONG ITS NEIGHBOURS. `resyncscore` prices an ADDITIVE fix (send a
`0x002C` we never send); `grantsuppress` prices the SUBTRACTION (send fewer);
this prices a SUBSTITUTION (send something else). All three read the same
captures through the same `movesync` loaders and none of them defines a bar of
its own.

----------------------------------------------------------------------------
THE THREE THINGS THIS FILE MEASURES, and the one it refuses to
----------------------------------------------------------------------------

**REALFIX-C0 -- the decision radius, re-derived from the binary.** The client's
match test compares a SQUARED distance against `100.0f` through the table sqrt at
`0x0046E870` (nine instructions, a 256-dword lookup table at `LUT_VA` below).
That approximation is not exact, so the effective threshold is not 100.0 u. The
derivation is exhaustive rather than sampled -- every one of the 2,048,001 float
patterns in [9000, 11000] -- and its positive control is gate 1, whose own
exhaustive scan over [80000, 100000] (2,560,001 patterns) reproduces the
`89600.0f` boundary this tree already carries. See `derive_match_radius()` and
`derive_gate1_cut()`; `MATCH_RADIUS` and `GATE1_CUT` are those two functions'
answers, and `test_grantsim.py` §C0 re-runs both scans against the pinned image
rather than trusting the constants.

**REALFIX-M1 -- lag age.** How far BACK on the client's own polyline the copy's
`q` sits, in seconds of client travel, against the ~5,000 ms block-recycle bound.
This is the metric REALFIX-P2 (zero lead) has, and it is the one thing about P2
that is not a tautology of the proxy's construction: under zero lead `q` is a
point the client itself reported and the proxy's polyline IS the report track,
so the match distance is 0 by identity. The AGE is not.

**REALFIX-M2 -- arrival exposure.** The fraction of class-B (arrival) instants
whose `q = D` misses the client's track by at least the match radius. This is
REALFIX-P3 (short lead)'s axis: at arrival `+0x78 = D` exactly, so the match
operand is precisely `|D - the client's track|`.

**And the bracket, always, never a skip.** Every row prints
`[snaps with the match test ON, snaps with it OFF]` -- a lower and an upper
bound. This deliberately REPLACES the drafted "skip the match test where the
report chord p90 exceeds the radius" rule, which fires on 4 of 4 counterfactual
and 7 of 11 calibration captures and would degrade the whole instrument to the
separation-only scorer round 5 refuted (16/12/34 predicted snaps on three
captures that sent zero grants and measured zero).

----------------------------------------------------------------------------
THE MODEL, stated so it can be argued with (`REALFIX.md` §2.3, FINDINGS §2.4)
----------------------------------------------------------------------------

    d        = D - [+0x78]                    # 0x005FEB57, measured from the COPY
    S        = [+0x60] * [+0x5C]              # 1.0 * 288.0
    if |d|^2 <= 1.0:                          # 0x005FEA85 fcom / jp 0x5feae1
        [+0x78..+0x84] = D ; velocity = 0 ; [+0x48] = now+1 ; RETURN
        # 0x005FEADE ret 0xc -- NO dispatch, NO child bake, NO collision frame,
        # NO arrival fan-out. This arm is the whole reason a zero-distance grant
        # is nearly free, and it is asserted structurally in the test.
    [+0xB0],[+0xB4] = unit(d) * S
    [+0x58]  = now ; [+0x48] = now + trunc(|d|*1000/S), clamp >= 1
    read(t)  = [+0x78] + vel*((t - [+0x58])*0.001)      # 0x005FFB40
                                                        # park on arrival

TEST INSTANTS, and both classes are a FLOOR. Class A is the bake's own dispatch
at `0x005FEBEB`; class B is a hard SetPosition, here the arrival consumption.
The floor is not a hedge: `0x0060221E` recurses the teleport primitive over the
child array, and the bake's post-dispatch fan-out (`0x005FEC7E` / `0x005FEC9A` /
`0x005FECAC`, and `0x00602BE5`) multiplies both. Gate 2 and gate 3 can only ADD
snaps and are invisible offline. Every number this file prints is a lower bound
on total harm.

MATCH PROXY -- `q` against the client's own report track over
`[max(armed_since, t - 5.0), t]` at `MATCH_RADIUS`, STRAIGHT-LINE ONLY, and that
IS a simplification. FINDINGS §2.2's predicate is a CONJUNCTION: straight-line
`< 100.0` STRICT **and** a walkable path length `<= 100.0` INCLUSIVE, the second
pushed at `0x00605C40`. This file implements the first conjunct alone. The
exception is real and it is narrow: `0x00605AFF`/`0x00605B0C` route a DEGENERATE
segment into a point test whose success at `0x00605B5E je 0x605c60` jumps past
the walkable query entirely, and segment 0 is degenerate exactly when
`+0x48 == 0` at the recording instant -- which is the whole of KEYBOARD movement
(REALFIX-O1). It does not cover segments 1..n in any regime, and it does not
cover segment 0 whenever the client holds a destination -- the click-driven
regime of `145717` / `171153` / `182652` / `195137`, four of the eleven
calibration captures. This note used to read "correct in this regime rather than
a simplification", which over-read the exception onto the whole proxy. Dropping
a conjunct can only make matching EASIER and snaps RARER, so the direction is
optimistic and the inventory below now carries it.

GATE-1 PROXY -- `sep >= GATE1_CUT` snaps. A true separation of exactly 300.0 u
snaps, which is the check with no free parameter.

RESEED -- a snap is ROSTER-WIDE (`0x006060A2`/`0x006060A9` zero every agent's
history head unconditionally), so the model puts the copy at the client's
position and moves `armed_since` to the snap instant: the next test runs against
a polyline that starts there.

----------------------------------------------------------------------------
THE THREE PROXY BIASES, direction stated, magnitude NOT FOUND for all three
----------------------------------------------------------------------------

Optimistic (we under-predict): the match test is missing its SECOND CONJUNCT
(the walkable path length above), and a test with one of two conditions dropped
passes more often, so snaps are rarer here than in the client; the real chain is
truncated on a match (`lastMatch->next = NULL` at `0x00605746`), so the 5 s
window is more generous than the client's; and the polyline is not client-only
-- a world-0 agent with `clientControlled == 0` falls through at `0x00606103`
and APPENDS, so our own sync-side writes push nodes during fence-closed windows.
Pessimistic (we over-predict): the client's history nodes are pushed at its own
local-move rate, so our report track is a SUBSAMPLE -- our polyline lies
chordally inside the true one and our distance-to-polyline is systematically
over-estimated. Combined with `resyncscore.sync_track`'s own p90 30-41 u / max
60 u error in the high-grant regime (REALFIX-C1 below), the two proxy errors are
of the same order as the 99.92 u decision radius. Say so beside any number.

----------------------------------------------------------------------------
WHAT THE HEADLINE IS ACTUALLY SENSITIVE TO -- read this before quoting 69
----------------------------------------------------------------------------
The eleven-capture as-sent total (69 predicted against 60 measured) is INSENSITIVE
to everything REALFIX-C0 measures and SENSITIVE to conventions nothing measured.
OBSERVED 2026-08-21, one knob at a time against identical inputs, by re-running
`assent_census()` under each variant -- through its `**kw` where `simulate()`
already exposes the knob, and otherwise through an exec'd copy of this module
with exactly one line changed:

    match radius   99.6 / 99.919968 / 100.0 u ....... 69 / 69 / 69
    ...and every integer radius 95..110 u .......... 69, except 68 at 101-104
    gate-1 cut     299.0 / 299.332591 / 300.0 u .... 69 / 69 / 69
    arrival tick   trunc vs round ................... 69 / 69
    gate 1 taken at `>=` vs `>` ...................... 69 / 69

    `client_at` STEP instead of linear ............... 81   (+17.4%)
    polyline drops the pre-`lo` seed point ........... 79   (+14.5%)
    polyline drops the trailing interpolated point ... 75    (+8.7%)
    HISTORY_WINDOW 2.5 s / 5.0 s / 10.0 s ......... 75 / 69 / 70
    extrapolate past the last report (deviation 5) ... 74    (+7.2%)
    `armed` NOT moved on a reseed .................... 72    (+4.3%)
    no class-B arrival instants ...................... 59   (-14.5%)

So the number swings 59-81 on modelling conventions -- which BRACKETS round 5
§6.2's own 69-vs-80 spread from the same written specification and names its
cause -- while seven significant figures of measured client behaviour are worth
zero to it. C0 is still the right kind of check (it re-derives a constant from
the image with no free parameter, and it is the one thing here that CANNOT be
tuned), but it is not what the calibration rests on, and a reader who takes 69
as corroborated by it has been misled. In particular: this file agreeing with
round 5's first reference implementation on the total AND on the per-capture
vector is a PIN against one of the two implementations §6.2 recorded as
irreconcilable -- not external corroboration. Deviation (3) says the same thing
in the language of the fixture; this table is the measurement behind it.

----------------------------------------------------------------------------
FOUR DELIBERATE DEVIATIONS FROM `REALFIX.md` §2, each with its ground
----------------------------------------------------------------------------

**(1) THIS FILE IMPORTS `authsrv.py`, LAZILY, AND §2.2 SAYS IT MUST NOT.**
§2.2's house rule is inherited from `grantsuppress.py`, which mirrors
`GRANT_SUPPRESS`/`GRANT_LOCAL_WINDOW`/`GRANT_MIN_INTERVAL` out of the server's
SOURCE TEXT. §2.6's REALFIX-C3 then requires the opposite and is the newer,
narrower instruction: *"`_grant_verdict`'s own docstring says it was made
side-effect-free so an offline scorer could run the decision rather than a
paraphrase that agrees with it by construction -- or stop calling C3 the policy
gate."* Running the real predicate is the whole value of C3, so the import
stands, and it is deferred to first use (`_authsrv()`) so nothing vault-shaped
or server-shaped happens at import time. `GRANT_SUPPRESS` is a module global set
once from argv, so `_grant_suppress()` sets and RESTORES it around the call --
the only way to drive both arms of the shipped predicate rather than two
paraphrases of it.

**(2) REALFIX-C3's TWO ARMS ARE NOT THE SAME KIND OF CHECK, and the heading one
is not yet a message-level replay.** This note used to read "the heading arm's
predicate does not exist in `authsrv.py` yet"; it landed on **2026-08-21**
(`authsrv._heading_grant_ok`, REALFIX-P2's `--zero-lead`), so P2 and P3 now
carry the SHIPPED rate limit rather than none, imported and run exactly as the
click arm's is. What is still asymmetric is the EVIDENCE: the click arm is
replayed against two captures' own recorded `grant_verdict` rows, reason for
reason, while no capture in the vault contains a heading-arm row -- the flag has
never been run. So §C3's heading half drives both arms of the real predicate
against a SYNTHETIC c2s stream and hand-computed expectations, and is labelled
as such. **The first REALFIX-L1 capture upgrades it to a message-level replay**
on the same footing as `195137`/`195315`, and `replay_verdicts` already skips
heading rows so that capture cannot silently redden the click arm.

**(3) REALFIX-C2(b)'s "golden fixture capture" is a COMMITTED EXPECTED-COUNT
VECTOR instead.** §2.6 asks for a committed fixture capture with an expected
per-capture vector. Committing a capture is refused by the house rules -- the
vault is personal data from the owner's own account and never enters the repo --
so the fixture is split in two: a SYNTHETIC minimal capture, built by the test
itself, carries the structural behaviour; and the per-capture vector is
committed as NUMBERS ONLY, keyed by capture stamp, pinned from this
implementation's first verified run. That is the resolution round 5 §6.2 names
in as many words -- *"pin the spec to a golden fixture or say the number is
implementation-dependent"* -- and the vector is recorded in the test as
IMPLEMENTATION-PINNED: it is what THIS code does, not what the specification
entails. Two independent implementations of the same written spec gave 69 and 80
against 60 measured, so a per-capture equality assertion against one of them is
a regression gate on this file and nothing more. It is still worth having: it is
the only thing that would notice this file quietly changing its answer.

**(4) The `<= 1.0 u` arm arms `+0x48 = now+1` in the binary and produces NO test
instant here.** `REALFIX.md` §2.7's structural assert requires exactly that ("a
`<=1.0 u` grant produces no instant"), and REALFIX-Q2 records the 1 ms arrival's
dispatch as RECONSTRUCTION rather than OBSERVED. The direction is safe: on that
arm `+0x78` has already been written to `D`, so an arrival instant there would
test `q = D` against the same polyline the bake would have -- it can only ADD
instants, never remove one, which leaves the instant count a FLOOR either way.

ONE MORE MODELLING CHOICE, named because it is not in the spec's five lines.
The bake SETTLES the copy before it re-aims: `+0x78` is brought forward to
`read(now)` and `[+0x58] = now`. **OBSERVED**, and this note used to hedge it as
UNVERIFIED because the settle is not in the bake's own body: `0x005FE950` writes
`+0x78` exactly ONCE, at `0x005FEA92`, the `<= 1.0 u` arm, and never writes
`+0x58` at all. The glide arm's re-pin is one frame out. `0x005FE9EA` calls
`0x005FF880` unconditionally -- the only control transfer in
`[0x005FE9C0, 0x005FE9EA)` is a two-byte `EB 02` inside an assert epilogue --
and that helper does `8D 7E 78 lea edi,[esi+0x78]` (`0x005FF890`),
`83 7E 48 00 cmp dword [esi+0x48],0` (`0x005FF89A`) with its `74 37 je`
(`0x005FF8A8`) -- bring the position forward only while GLIDING -- then
`E8 8A 02 00 00 call 0x005FFB40` (`0x005FF8B1`, the read function) and writes
the four returned dwords into `+0x78..+0x84` (`89 0F` / `89 4F 04` / `89 4F 08`
/ `89 47 0C` at `0x005FF8B9`/`BE`/`C4`/`CE`). Both paths join at
`0x005FF932 89 46 58 mov [esi+0x58],eax`, so `+0x58 = now` is stamped whether
the copy was gliding or parked. The bake then overwrites its own `now` PARAMETER
with it -- `0x005FE9EF 8B 46 58` / `0x005FE9F3 89 45 08` -- and `[ebp+8]` is the
slot the `<= 1.0` arm reads at `0x005FEAAF 8B 45 08` and the glide arm adds at
`0x005FEB35 03 4D 08`. So `pos <- read(now); t58 <- now` is what the client
does, and the alternative this note used to fear -- every leg measured from the
previous leg's START, and therefore longer -- is REFUTED. Read out of the pinned
image (build 38797) with a stdlib PE walk on 2026-08-21, byte patterns quoted.

ORIGINS ARE NEVER POOLED. `track_of()` goes through `resyncscore.track_from_capture`,
whose `origin=ours` refusal is the gate, and `require_ours()` raises
`origin.MixedCorpora` on any call that mixes corpora. Retail is not an input to
this file at all: it has no `ours` grant stream to counterfactual against.

READS ONLY. Opens vault captures and the pinned client image; writes nothing,
sends nothing, launches nothing. Nothing at import time touches either.
"""

import argparse
import bisect
import contextlib
import json
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import origin                                                  # noqa: E402
import vaultpath                                               # noqa: E402
from gwpe import PE                                            # noqa: E402
import movesync                                                # noqa: E402
import pinned                                                  # noqa: E402
import resyncscore                                             # noqa: E402


# `class Refused` lives in `grantinputs.py` now -- ONE definition and never a
# second one, because it subclasses `SystemExit`: a copy defined here as well
# would make `except GS.Refused` silently stop catching the one the resolvers
# raise, and an uncaught `SystemExit` exits the test process with no banner.
# Re-exported HERE, at the site it was cut from, because this file raises it by
# the bare name at eleven sites below and `test_grantsim.py` catches
# `GS.Refused` (§B, §C0).
from grantinputs import Refused                                 # noqa: F401,E402


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


# =========================================================================
# The simulator's own constants -- every one of them the client's
# =========================================================================

# S = [+0x60] * [+0x5C]. The harness models no 0x002B, so the family rate is
# pinned at 1.0 and REALFIX-P1/P4/P5 are OUTSIDE this instrument: under P1's
# family rates a BACK leg runs at 190.1 u/s while this bakes 288, a 1.51x error
# in the operand of BOTH tests.
COPY_RATE = 1.0
COPY_SPEED = COPY_RATE * movesync.RUN_SPEED

# `0x005FEA85 fcom st(1) / test ah,0x41 / jp 0x5feae1`. The fall-through at
# 0x005FEA92 is the `<= 1.0` arm and it dispatches NOTHING.
ZERO_DIST_SQ = 1.0

# `0x00604C03 cmp ecx,0x1388` -- a 256-entry history block is recycled when its
# NEWEST entry is older than 5000 ms. It is a per-BLOCK bound, not a per-node
# expiry, so the true chain span is looser and unmeasured; `seg_match` itself
# (0x00605AF0..0x00605C6A) applies no time filter at all. This window is
# therefore a MODELLING CHOICE and the file says so -- "zero free parameters"
# was withdrawn in round 5.
HISTORY_WINDOW = 5.0

# The active-time threshold. NAMED at every rate this file prints, because
# `movesync.denominator`'s own FREE_SILENCE (1.042 s) and round 5's substrate
# table (2.0 s) are different denominators and the rate moves 4x between the
# thresholds a reader might assume.
ACTIVE_THRESHOLD = 2.0

# How far past the radius a predicted snap has to land before it stops being
# INSIDE the instrument's own error bar. `resyncscore.sync_track`'s residual runs
# p90 30.5-38.5 u and max 59.5-60.5 u on the two high-grant calibration pairs
# against a 99.92 u decision radius, so 1.5x the radius is the honest edge of
# "this file cannot tell". Reporting only; never a filter.
MARGIN_FACTOR = 1.5

# REALFIX-P3's fixed lead: min(RUN_SPEED * 0.30, MATCH_RADIUS - 14.0) = 86.0 u,
# where 0.30 s is our own report cadence p50 on click-heavy `ours` play.
REFRESH_P50 = 0.30
LEAD_FIXED = min(movesync.RUN_SPEED * REFRESH_P50, MATCH_RADIUS - 14.0)

# The shape of the already-REFUTED `--client-endpoint`, kept as the third point
# of the lead spine 0 / 86 / 766 so C5's band has something to invert on.
LEAD_ENDPOINT = 766.0

OP_HEADING = movesync.OP_SET_HEADING        # 61 = 0x003D MOVE_SET_HEADING
OP_CLICK = 62                               # 62 = 0x003E MOVE_TO_COORD
OP_STOP = movesync.OP_CANCEL_REPORT         # 71 = 0x0047 MOVE_CANCEL_REPORT_POSITION


# =========================================================================
# Inputs -- the stamps, and which gate each one is allowed to serve
# =========================================================================

# REALFIX-C1's five movetap pairs. All `ours`.
MOVETAP_PAIRS = (
    ("20260819T145717", "movetap-20260819T145939.jsonl"),
    ("20260819T150336", "movetap-20260819T150349.jsonl"),
    ("20260819T150522", "movetap-20260819T150537.jsonl"),
    ("20260819T152716", "movetap-20260819T152723.jsonl"),
    ("20260819T171153", "movetap-20260819T171436.jsonl"),
)

# THE TWO HIGH-GRANT PAIRS, and C1 gates on THESE ONLY. The other three are
# 53-83% parked and their unconditioned p50 of 0.00 measures the parking rather
# than the model; they are reported and not gated.
C1_GATED = ("20260819T152716", "20260819T171153")

# REALFIX-U1: three of the five pairs are named in no study document and their
# run configuration is UNVERIFIED (the gamesrv jsonl headers carry no argv).
# `REALFIX.md` §2.5: use them for C1 only, never for a policy attribution.
UNDOCUMENTED_PAIRS = ("20260819T150336", "20260819T150522", "20260819T152716")

# REALFIX-C2's calibration set: eleven `ours` captures across five
# configurations, 60 measured hard jumps between them. `150336` and `150522`
# are NOT here -- they appear only as movetap pairs and are C1-only.
# `152716` IS here, because C2 scores the AS-SENT stream, which is a fact about
# the wire rather than an attribution to a named flag.
CALIBRATION_11 = (
    "20260819T145717", "20260819T152716", "20260819T171153", "20260819T182652",
    "20260811T173940", "20260820T182554", "20260820T182934", "20260820T183311",
    "20260820T195137", "20260820T195315", "20260814T100340",
)

# REALFIX-C2(a): the three that sent ZERO grants and measured ZERO jumps. A
# caller-aware proxy must take them to exactly 0 STRUCTURALLY -- no caller, no
# test. The separation-only scorer predicted 16, 12 and 34 here.
STRUCTURAL_ZEROS = ("20260811T173940", "20260820T182554", "20260820T182934")

# REALFIX-C2(c): the high-separation pair must exceed the low pair by >= 3x on
# predicted snaps per minute of span. The `145717`-vs-`195315` order INVERTS and
# is printed rather than gated.
C2C_HIGH = ("20260819T182652", "20260820T195137")
C2C_LOW = ("20260819T145717", "20260820T195315")

# THE COUNTERFACTUAL SUBSTRATE: `ours`, zero-grant, and both of its biases are
# load-bearing. Player speed p50 262-283 u/s against a declared 288 -- the
# regime where any lead policy's runaway rate (S - v_player) is SMALLEST -- and
# clicks number 0/5/21/0, so the shipped default sends ~0 grants and survives by
# doing nothing. THE INSTRUMENT PRICES HARM A CANDIDATE ADDS. IT CANNOT PRICE
# HARM A CANDIDATE REMOVES.
COUNTERFACTUAL = ("20260811T173940", "20260820T182934",
                  "20260814T100340", "20260820T182554")

SUBSTRATE_WARNING = (
    "SUBSTRATE: fast-running (v_player p50 262-283 u/s against a declared 288) "
    "and click-free (0/5/21/0 clicks). This is where every lead policy is LEAST "
    "harmful and where P0 survives by sending nothing. A null here is not an "
    "acquittal, and this file cannot price harm a candidate REMOVES.")


# The three path-and-origin resolvers live in `grantinputs.py` now, and this cut
# is the one in this file that lands INSIDE a banner: the stamps above and
# `_TRACK_CACHE`/`track_of` below are still this file's, only the resolvers they
# feed moved. Re-exported HERE, at the site they were cut from, because
# `track_of()` below calls `capture_path()` by the bare name, as do eight
# further sites in this file, and `test_grantsim.py` reads all three off the
# module (`GS.capture_path`, `GS.movetap_path`, `GS.require_ours`).
from grantinputs import (                                       # noqa: F401,E402
    capture_path, movetap_path, require_ours)


_TRACK_CACHE = {}


def track_of(stamp):
    """One capture, through `resyncscore`'s loader -- whose origin refusal is the gate.

    MEMOISED, and nothing here mutates a track: REALFIX-C4 alone re-scores the
    eleven calibration captures nine times, so re-parsing 61 MB of jsonl on
    every pass turned a 3 s answer into a 22 s one. The origin refusal still
    runs on the first load of each stamp, which is the only place it can fire.
    """
    if stamp not in _TRACK_CACHE:
        _TRACK_CACHE[stamp] = resyncscore.track_from_capture(capture_path(stamp))
    return _TRACK_CACHE[stamp]


# =========================================================================
# The c2s control stream -- the one reader this file adds, and why
# =========================================================================

def c2s_moves(path):
    """[{t, op, pos, plane, vec2, unit, mt}] -- the client's own control traffic.

    `movesync.load_wire_reports` is the SPLICED report track and this file uses
    it VERBATIM for the polyline. What it drops is `values[3]` (the heading
    vec2) and `values[4]` (the movementType), which are exactly the two fields a
    heading policy computes from -- so this reader exists to keep them, and NOT
    to re-decode a position. A second position decoder would be a second chance
    to disagree about what the client said.

    `0x003E` (click) is kept too: it is the trigger for REALFIX-P0 and P6.
    """
    out = []
    for line in open(path, encoding="utf-8", errors="replace"):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("kind") != "decoded":
            continue
        op = r.get("opcode")
        if op not in (OP_HEADING, OP_CLICK, OP_STOP):
            continue
        v = r.get("values")
        # A shape that is not what the schema says is DROPPED rather than
        # indexed into: a silent IndexError inside a broad except is how a
        # census gets zeroed, and `movesync.load_wire_reports` refuses the same
        # way for the same reason.
        if not isinstance(v, (list, tuple)) or len(v) < 2:
            continue
        p = v[1]
        if not isinstance(p, (list, tuple)) or len(p) < 2:
            continue
        plane = v[2] if len(v) > 2 and isinstance(v[2], int) else None
        vec2 = unit = mt = None
        if op == OP_HEADING and len(v) >= 5:
            h = v[3]
            if isinstance(h, (list, tuple)) and len(h) >= 2:
                vec2 = [float(h[0]), float(h[1])]
                m = math.hypot(vec2[0], vec2[1])
                if m > 1e-6:
                    unit = (vec2[0] / m, vec2[1] / m)
            mt = v[4] if isinstance(v[4], int) else None
        out.append({"t": r["t"], "op": op, "pos": [float(p[0]), float(p[1])],
                    "plane": plane, "vec2": vec2, "unit": unit, "mt": mt})
    out.sort(key=lambda m: m["t"])
    return out


# =========================================================================
# The candidate policies -- pure functions, `REALFIX.md` §2.3 step 2
# =========================================================================
#
# Signature: policy(c2s, params) -> [(t, D, plane_dest, plane_cur, kind)].
#
# PLANES. Offline the only plane available is the client's own echo, so every
# policy here sends `(plane, plane)`. That is the ORDER `authsrv.py:9987`
# already uses (field 3 = destination plane, field 4 = current plane, closed
# from the binary three times) and it is what makes gate 2 unexpressible here
# rather than wrongly expressed: gate 2 has n = 0 observed firings and is
# structurally invisible offline either way.

# `_AUTHSRV` and `_authsrv()` live in `grantinputs.py` now. Re-exported HERE,
# at the site they were cut from, because this file calls `_authsrv()` by the
# bare name below and `test_grantsim.py` reads `GS._authsrv()` (§C3, §10).
# `_AUTHSRV` itself is NOT re-exported and must not be: it is a mutable memo, so
# a `from grantinputs import _AUTHSRV` would bind the `None` it holds at import
# time and never see it fill -- a second, permanently-stale copy.
from grantinputs import _authsrv                                # noqa: F401,E402


@contextlib.contextmanager
def _grant_suppress(on):
    """Drive `_grant_verdict`'s own flag, then put it back exactly as found.

    `GRANT_SUPPRESS` is a module global written once from argv, so there is no
    parameter to pass. Setting and restoring it is what lets BOTH arms of the
    shipped predicate be run rather than paraphrased -- which is the whole
    ground on which deviation (1) imports this module at all.
    """
    A = _authsrv()
    was = A.GRANT_SUPPRESS
    A.GRANT_SUPPRESS = bool(on)
    try:
        yield A
    finally:
        A.GRANT_SUPPRESS = was


def grant_verdict(state, now, suppress):
    """(fired, reason, keyboard_age, since_last) from `authsrv._grant_verdict`.

    THE REAL PREDICATE. Not a mirror of it, not a re-statement of its two rules.
    `authsrv.py:3004-3011` says in as many words that it was made pure and
    side-effect-free so an offline scorer could run the decision rather than a
    paraphrase that agrees with it by construction; this is that scorer.
    """
    with _grant_suppress(suppress) as A:
        return A._grant_verdict(state, now)


def heading_verdict(state, now):
    """(fired, reason, since_last) from `authsrv._heading_grant_ok`.

    THE REAL PREDICATE, and unlike the click arm's it needs NO flag wrangling:
    `_heading_grant_ok` carries rule 2 and nothing else and short-circuits on
    nothing, so there is no `ZERO_LEAD` to set and restore around the call.
    Since MOVECODE-1z-cw it reads ONE module global, `KBD_GRANT_FLOOR` (0.0
    shipped: retail answers every heading report; 0.5 is the arm that shipped
    until 2026-09-09), so a replay of a capture recorded under the old arm must
    set it from that capture's `flags` row -- test_grantsim does so explicitly. The lead policies below apply it as their rate limit, which
    is what makes REALFIX-C3's heading arm a policy gate rather than a
    paraphrase of one.

    Its reason vocabulary -- `zero-lead` / `heading-rate` -- is DISJOINT from
    `_grant_verdict`'s, so a capture from a `--zero-lead` run carrying both
    arms' `grant_verdict` rows can be split by reason alone (and by the `arm`
    field besides). `replay_verdicts` filters on exactly that.
    """
    return _authsrv()._heading_grant_ok(state, now)


# The reason strings only the HEADING arm emits. `replay_verdicts` skips these
# rows so the click-arm replay's denominator stays the click arm's, and the
# heading replay that REALFIX-L1's first capture will earn selects on them.
HEADING_REASONS = frozenset(("zero-lead", "heading-rate"))


def _click_arm(c2s, suppress, log=None):
    """REALFIX-P0 / P6: the shipped CLICK arm, driven by the real predicate.

    The latch model is `authsrv.py`'s own and touched in no third place:
    `kbd_moving_at` is stamped by the `0x003D` arm when `movementType` is
    non-zero and CLEARED by the `0x0047` arm (`:9715`, `:10274`), and
    `grant_at` is stamped inside `send()` for every `0x0029` (`:2731`).

    THE DEFERRED FLUSH IS MODELLED, and it is the one part of this arm that is a
    paraphrase rather than an import: `grant_flush_tick` prints and sends, so it
    cannot be called. What is reproduced is its shape -- ONE destination held,
    newest wins, dropped past `GRANT_PENDING_MAX_AGE`, dropped outright when
    rule 1 fires -- with the verdict itself still taken from the real
    `_grant_verdict`. It is polled at c2s event instants rather than at the
    server's 20 Hz world tick, so a held grant can be emitted up to one report
    gap late. Both approximations can only move a grant, never invent one.
    """
    A = _authsrv()
    state, out = {}, []
    pending = None

    def emit(t, dest, plane):
        state["grant_at"] = t
        out.append((t, (float(dest[0]), float(dest[1])), plane, plane, "click"))

    for m in c2s:
        t = m["t"]
        # The held click is polled first, so a grant released at this instant is
        # ordered before whatever the client said at it.
        if pending is not None:
            age = t - pending["at"]
            if age > A.GRANT_PENDING_MAX_AGE or age < 0.0:
                pending = None
            else:
                fired, why, _ka, _sl = grant_verdict(state, t, suppress)
                if fired:
                    emit(t, pending["dest"], pending["plane"])
                    pending = None
                elif why != "rate-limited":
                    pending = None          # their own hands supersede it
        if m["op"] == OP_HEADING:
            state["kbd_moving_at"] = t if m["mt"] else None
        elif m["op"] == OP_STOP:
            state["kbd_moving_at"] = None
        elif m["op"] == OP_CLICK:
            fired, why, kage, since = grant_verdict(state, t, suppress)
            if log is not None:
                log.append({"t": t, "fired": fired, "reason": why,
                            "keyboard_age": kage, "since_last": since,
                            "dest": list(m["pos"])})
            if fired:
                pending = None
                emit(t, m["pos"], m["plane"])
            elif why == "locally-moving":
                pending = None              # DROPPED, not held
            else:
                pending = {"dest": tuple(m["pos"]), "plane": m["plane"], "at": t}
    return out


def replay_verdicts(path, suppress):
    """REALFIX-C3 (click-arm). The capture's own `grant_verdict` rows, re-decided.

    Returns [(t, recorded, replayed)] where each half is `(fired, reason)`, plus
    the recorded `keyboard_age` and the replayed one so the two can be compared
    numerically rather than only categorically.

    THE INSTANTS COME FROM THE LOG AND THE DECISION DOES NOT. That division is
    deliberate: which clicks REACH the policy is decided by three geometry
    refusals and a navmesh clip that this file cannot express offline, and
    inventing them would make C3 a test of the invention. What C3 tests is the
    POLICY -- given that the server asked, does the replay answer the same way,
    reason for reason -- and the answer is taken from `authsrv._grant_verdict`
    itself rather than from a paraphrase.

    The latch model is the server's own and touched in no third place:
    `kbd_moving_at` from the `0x003D` arm (`:9715`) cleared by `0x0047`
    (`:10274`), `grant_at` from `send()` (`:2731`).
    """
    import struct as _struct                                   # noqa: PLC0415
    state, out = {}, []
    for line in open(path, encoding="utf-8", errors="replace"):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        kind, t = r.get("kind"), r.get("t")
        if not isinstance(t, (int, float)):
            continue
        if kind == "decoded" and r.get("opcode") == OP_HEADING:
            v = r.get("values")
            if isinstance(v, (list, tuple)) and len(v) >= 5:
                state["kbd_moving_at"] = t if v[4] else None
        elif kind == "decoded" and r.get("opcode") == OP_STOP:
            state["kbd_moving_at"] = None
        elif kind == "sent" and r.get("opcode") == movesync.OP_MOVE_TO_POINT:
            raw = r.get("plain")
            if raw:
                b = bytes.fromhex(raw)
                if len(b) >= 14 and _struct.unpack_from("<I", b, 2)[0] \
                        == movesync.PLAYER_AGENT:
                    state["grant_at"] = t
        elif kind == "grant_verdict":
            # THE CLICK ARM'S ROWS ONLY. A `--zero-lead` capture carries the
            # heading arm's verdicts on this same channel by design, and
            # re-deciding one of those with the CLICK predicate would compare
            # two different policies and call the disagreement a defect. No
            # capture in the vault has such a row yet; the filter is here so the
            # first REALFIX-L1 capture does not silently redden C3.
            # And the F-B click rows (arm="click-d1", 2026-08-26): under
            # --d1-lead the click arm answers per RETAIL's contract (Rule 1
            # bypassed, rate-only), so re-deciding its rows with the shipped
            # click predicate compares two different policies -- the same
            # ground as the zero-lead filter above, added the same way:
            # BEFORE the first such capture reddens C3 (the F-B review's
            # REV-1, demonstrated 2/2 offline before a capture existed).
            if (r.get("arm") in ("zero-lead", "click-d1")
                    or r.get("reason") in HEADING_REASONS):
                continue
            fired, why, age, since = grant_verdict(state, t, suppress)
            out.append({"t": t,
                        "recorded": (r.get("fired"), r.get("reason")),
                        "replayed": (fired, why),
                        "recorded_age": r.get("keyboard_age"),
                        "replayed_age": age,
                        "recorded_since": r.get("since_last"),
                        "replayed_since": since})
    return out


def sent_player_grants(path):
    """How many `0x0029` the capture actually put on the wire for the player."""
    return len(movesync.load_grants(path))


def policy_p0_default(c2s, params=None):
    """REALFIX-P0 -- the shipped control. Click grants only, `--grant-suppress` OFF.

    The clicked point VERBATIM. The shipped arm clips it against our navmesh
    first, which this file cannot express and does not pretend to: no pathmap,
    no plane table, and round 5 graded our clip an approximation of retail's D2
    rather than an instance of it. The three geometry refusals (stale, blocked,
    ambiguous plane) are likewise not modelled, so P0's synthesized grant count
    is an UPPER bound on what the shipped server would actually have sent.
    """
    return _click_arm(c2s, suppress=False)


def policy_p6_grant_suppress(c2s, params=None):
    """REALFIX-P6 -- the shipped control with `--grant-suppress` ON.

    Same arm, same predicate, the flag flipped. Rule 1 refuses while the
    locally-driving latch is younger than `GRANT_LOCAL_WINDOW`; rule 2 floors
    the interval at `GRANT_MIN_INTERVAL`. Both constants are the server's own,
    read through the import rather than mirrored.
    """
    return _click_arm(c2s, suppress=True)


def lead_policy(lead):
    """REALFIX-P2 at 0 u, P3 at 86 u, and `--client-endpoint`'s shape at 766 u.

    ONE AXIS between the three. The trigger is every `0x003D` while moving --
    which DROPS the shipped heading gate at `authsrv.py:9758`
    (`turned or walking is not True`), a named variable rather than a hidden
    one: on click-free play that gate opens on only 11.1 / 24.3 / 61.2 / 80.8%
    of moving reports (`182554` / `182934` / `100340` / `173940`), a 1.24x-9x
    cadence delta, while on the click-heavy refuted runs it is invisible
    (`182652` 193/193, `171153` 447/447).

    NO CLIP, deliberately, on all three: adding `clip_to_walkable` to the middle
    one would make it a two-variable step from BOTH neighbours, and our heading
    arm's clip suspends collision entirely when our mesh does not cover the
    player, so it would not even express retail's D2.

    THE RATE LIMIT IS THE SHIPPED ONE. `authsrv._heading_grant_ok` LANDED
    2026-08-21 and is imported and run here, not paraphrased -- REALFIX-P2's
    rule 2 and nothing else, refusing while the last grant is younger than
    `GRANT_MIN_INTERVAL`. A refused heading grant is DROPPED, never held, which
    is the predicate's own documented semantics and the reason this loop needs
    no pending machinery to match the server's.

    `state["grant_at"]` is the server's SHARED grant clock, stamped inside
    `send()` for every player `0x0029` whatever arm sent it. In the server, a
    click grant therefore delays a heading grant. Here the lead policies are
    heading-only streams by construction, so the only thing on this clock is
    this policy's own emissions -- an approximation that can only make the
    synthesized stream DENSER than the shipped one would be under
    `--grant-suppress`, never sparser. Said out loud because the direction
    matters: this file's numbers stay a FLOOR on harm.
    """
    def policy(c2s, params=None):
        A = _authsrv()                              # noqa: F841 -- import gate
        state, out = {}, []
        for m in c2s:
            if m["op"] != OP_HEADING or not m["mt"]:
                continue
            p = m["pos"]
            if lead == 0.0:
                D = (p[0], p[1])
            elif m["unit"] is None:
                continue                # no heading, no direction, no grant
            else:
                u = m["unit"]
                D = (p[0] + lead * u[0], p[1] + lead * u[1])
            fired, _why, _since = heading_verdict(state, m["t"])
            if not fired:
                continue                # DROPPED, not held -- see the docstring
            state["grant_at"] = m["t"]
            out.append((m["t"], D, m["plane"], m["plane"], "heading"))
        return out
    policy.lead = lead
    return policy


policy_p2_zerolead = lead_policy(0.0)
policy_p3_shortlead = lead_policy(LEAD_FIXED)
policy_p_endpoint = lead_policy(LEAD_ENDPOINT)


def policy_assent(c2s, params=None):
    """NOT A CANDIDATE -- the capture's own as-sent `0x0029` stream.

    REALFIX-C2 calibrates against THIS: the grants the server actually put on
    the wire, decoded by `movesync.load_grants` from the logged bytes rather
    than from a label. `params` must carry `{"track": track}` because the
    as-sent stream is a property of the capture and not of the c2s traffic.
    """
    tr = (params or {}).get("track")
    if tr is None:
        raise Refused("grantsim: policy_assent needs params={'track': track} -- "
                      "the as-sent stream is read off the capture, not synthesized")
    plane = None
    return [(t, (D[0], D[1]), plane, plane, "as-sent") for t, D in tr["grants"]]


POLICIES = {
    "as-sent": policy_assent,
    "P0-default": policy_p0_default,
    "P2-zerolead": policy_p2_zerolead,
    "P3-shortlead": policy_p3_shortlead,
    "P6-grant-suppress": policy_p6_grant_suppress,
    "lead-766": policy_p_endpoint,
}


def policy_named(name):
    """A policy by name, or refuse. An unknown name is never an empty stream."""
    try:
        return POLICIES[name]
    except KeyError:
        raise Refused(
            f"grantsim: no policy named {name!r}.\n"
            f"  known: {', '.join(sorted(POLICIES))}\n"
            f"  A typo must not resolve to 'no grants and therefore no snaps', "
            f"which is the most comfortable wrong answer this file can give.")


# =========================================================================
# Geometry -- the match proxy and gate 1
# =========================================================================

def client_at(reps, ts, t):
    """The client's own position, linearly interpolated between its reports."""
    i = bisect.bisect_right(ts, t) - 1
    if i < 0:
        return list(reps[0][1])
    if i + 1 >= len(reps):
        return list(reps[i][1])
    t0, p0 = reps[i][0], reps[i][1]
    t1, p1 = reps[i + 1][0], reps[i + 1][1]
    if t1 <= t0:
        return list(p0)
    f = (t - t0) / (t1 - t0)
    return [p0[0] + f * (p1[0] - p0[0]), p0[1] + f * (p1[1] - p0[1])]


def seg_dist(q, a, b):
    """|q - closestPoint(q, seg(a,b))|. STRAIGHT-LINE, which is the point."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy
    if L2 <= 1e-9:
        return math.hypot(q[0] - a[0], q[1] - a[1])
    f = min(max(((q[0] - a[0]) * dx + (q[1] - a[1]) * dy) / L2, 0.0), 1.0)
    return math.hypot(q[0] - (a[0] + f * dx), q[1] - (a[1] + f * dy))


def polyline(reps, ts, lo, hi):
    """[(t, xy)] -- the client's own track over [lo, hi], plus its position AT hi.

    The trailing point models the chain's seed: `seg_match` walks newest->oldest
    with `prev` seeded from `state.position`, and the recorder writes the same
    block into both `node.position` and that seed when `+0x48 == 0`.
    """
    i = max(bisect.bisect_left(ts, lo) - 1, 0)
    j = bisect.bisect_right(ts, hi)
    pts = [(reps[k][0], reps[k][1]) for k in range(i, j)]
    pts.append((hi, client_at(reps, ts, hi)))
    return pts


def poly_distance(q, pts):
    """The straight-line distance from q to the polyline, or to its single point."""
    if len(pts) == 1:
        return math.hypot(q[0] - pts[0][1][0], q[1] - pts[0][1][1])
    return min(seg_dist(q, pts[k - 1][1], pts[k][1]) for k in range(1, len(pts)))


def lag_age(q, pts, now, radius, lo):
    """REALFIX-M1. Age of the NEWEST polyline POINT within `radius` of q, or None.

    A point rather than a segment: the metric is "how far back on the chain the
    copy sits", and only a node carries a time. `None` means no node is within
    the radius -- the match either failed outright or passed on a SEGMENT
    INTERIOR -- and that population is counted separately rather than folded in
    as a zero.

    BOUNDED BY `lo`, and this is not cosmetic. `polyline()` deliberately keeps
    one point OLDER than the window so the segment straddling `lo` exists; that
    point is a legitimate part of the match test and an illegitimate answer to
    "how old is the newest node the copy is standing on". Without the bound the
    metric reported a 266.29 s lag against a ~5 s chain bound on
    `20260814T100340`, which is the window's artifact and not the client's.
    """
    for t, p in reversed(pts):
        if t < lo:
            break
        if math.hypot(q[0] - p[0], q[1] - p[1]) < radius:
            return now - t
    return None


# =========================================================================
# The bake -- `REALFIX.md` §2.3 steps 3-7, byte-exact
# =========================================================================

def simulate(reps, grants, *, match_on=True, window=HISTORY_WINDOW,
             radius=MATCH_RADIUS, gate=GATE1_CUT, speed=COPY_SPEED,
             reseed=True):
    """Replay a grant stream through the client's bake and count the snaps.

    Returns a dict; `instants` is a FLOOR (see the module docstring) and so is
    every count derived from it.
    """
    reps = list(reps)
    if len(reps) < 2:
        raise Refused(
            "grantsim: fewer than two client reports -- there is no polyline to "
            "match against and no interpolated position to gate against, so "
            "this would score every instant against a single point")
    ts = [r[0] for r in reps]
    t_end = ts[-1]

    grants = sorted(grants, key=lambda g: g[0])

    pos = list(reps[0][1])          # +0x78
    t58 = ts[0]                     # +0x58
    vel = (0.0, 0.0)                # +0xB0 / +0xB4
    t48 = None                      # +0x48, None == 0 == parked
    target = None                   # +0x88.. (the destination)
    armed = ts[0]                   # the history seed epoch; a snap moves it

    instants, snaps = [], []
    zero_arm = 0                    # grants that took the <= 1.0 u short-circuit

    def read(t):
        if target is None or t48 is None or t >= t48:
            return list(target) if target is not None else list(pos)
        return [pos[0] + vel[0] * (t - t58), pos[1] + vel[1] * (t - t58)]

    def gap_at(t):
        """The report interval this instant landed in -- the blind spot's size."""
        i = bisect.bisect_right(ts, t) - 1
        if i < 0 or i + 1 >= len(ts):
            return float("nan")
        return ts[i + 1] - ts[i]

    def test(t, q, kind):
        nonlocal pos, vel, target, t48, t58, armed
        lo = max(armed, t - window)
        pts = polyline(reps, ts, lo, t)
        dist = poly_distance(q, pts)
        age = lag_age(q, pts, t, radius, lo)
        C = client_at(reps, ts, t)
        sep = math.hypot(q[0] - C[0], q[1] - C[1])
        matched = bool(match_on and dist < radius)
        row = {"t": t, "kind": kind, "q": list(q), "poly": dist, "sep": sep,
               "lag_age": age, "matched": matched, "snapped": False,
               "gap": gap_at(t),
               # WHERE THE CHAIN STARTS for this instant. Recorded rather than
               # inferred so the roster-wide reseed is observable from outside:
               # after a snap `armed` is the snap instant, so the next test
               # cannot match against anything the client walked before it.
               "win_lo": lo}
        instants.append(row)
        if matched:
            return
        if sep >= gate:
            row["snapped"] = True
            snaps.append(row)
            if reseed:
                # ROSTER-WIDE, 0x006060A2/0x006060A9. The copy lands on the
                # client and the chain restarts here.
                pos, vel, target, t48, t58, armed = list(C), (0.0, 0.0), None, None, t, t

    gi = 0
    while True:
        ng = grants[gi][0] if gi < len(grants) else None
        if ng is not None and ng > t_end:
            # PAST THE LAST REPORT there is no client track, so this grant and
            # every later one are dropped -- but any leg still outstanding is
            # drained first. Clicks are not report instants, so a click arm CAN
            # produce a grant after the track ends; dropping it by `break` would
            # have swallowed the arrival that was already due.
            ng, gi = None, len(grants)
        # An arrival that matures first is consumed first. Past the last report
        # there is no client track to test against, so the loop stops rather
        # than extrapolating one -- which is a real difference from round 5's
        # reference implementation, whose interpolator clamps to the final
        # report and scored one extra snap on the 766 u arm of all four
        # counterfactual captures for exactly that reason.
        if t48 is not None and target is not None and (ng is None or t48 <= ng):
            if t48 > t_end:
                break
            ta, q = t48, list(target)
            pos, vel, t58, t48 = list(target), (0.0, 0.0), ta, None
            target = None
            test(ta, q, "arrival")          # class B: the arrival SetPosition
            continue
        if ng is None:
            break
        t, D = grants[gi][0], grants[gi][1]
        gi += 1
        q = read(t)
        # THE BAKE SETTLES FIRST. See the module docstring's last modelling note.
        pos, t58 = list(q), t
        dx, dy = D[0] - q[0], D[1] - q[1]
        n2 = dx * dx + dy * dy
        if n2 <= ZERO_DIST_SQ:
            # 0x005FEA92: hard-write +0x78 = D, `fldz` into +0xB0/+0xB4, arm
            # +0x48 = now+1, `ret 0xc`. NO dispatch and NO fan-out, so no
            # instant of either class -- REALFIX.md §2.7's structural assert.
            pos, vel, target, t48 = [D[0], D[1]], (0.0, 0.0), None, None
            zero_arm += 1
            continue
        n = math.sqrt(n2)
        vel = (dx / n * speed, dy / n * speed)
        target = [D[0], D[1]]
        ms = int(n * 1000.0 / speed)        # trunc, and the client clamps >= 1
        t48 = t + max(1, ms) / 1000.0
        test(t, q, "bake")                  # class A: 0x005FEBEB

    arrivals = [r for r in instants if r["kind"] == "arrival"]
    ages = [r["lag_age"] for r in instants if r["lag_age"] is not None]
    # A snap whose polyline distance is barely over the radius is inside the
    # instrument's OWN error band -- `sync_track`'s p90 30-41 u / max 60 u in
    # the high-grant regime, plus the subsample bias where the report chord is
    # wide -- and must be read as such rather than as a firing. MARGIN_FACTOR
    # is a reporting threshold, never a gate: nothing here is filtered by it.
    marginal = [r for r in snaps if r["poly"] < radius * MARGIN_FACTOR]
    return {
        "instants": instants, "snaps": snaps,
        "n_instants": len(instants), "n_snaps": len(snaps),
        "n_bake": len(instants) - len(arrivals), "n_arrival": len(arrivals),
        "snaps_a": sum(1 for r in snaps if r["kind"] == "bake"),
        "snaps_b": sum(1 for r in snaps if r["kind"] == "arrival"),
        "marginal": len(marginal),
        "zero_arm": zero_arm,
        "first_snap": snaps[0]["t"] if snaps else None,
        "m1": {"n": len(ages), "unmatched": len(instants) - len(ages),
               "p50": movesync.pct(ages, 0.5) if ages else float("nan"),
               "p90": movesync.pct(ages, 0.9) if ages else float("nan"),
               "max": max(ages) if ages else float("nan")},
        "m2": _m2(arrivals, reps, ts, radius),
        "sep": {"p50": movesync.pct([r["sep"] for r in instants], 0.5),
                "p90": movesync.pct([r["sep"] for r in instants], 0.9),
                "max": max((r["sep"] for r in instants), default=float("nan"))},
        "params": {"match_on": match_on, "window": window, "radius": radius,
                   "gate": gate, "speed": speed, "reseed": reseed},
    }


def _m2(arrivals, reps, ts, radius):
    """REALFIX-M2, on BOTH operands, because the two answer different questions.

    `poly` is the spec's own wording -- the fraction of class-B instants whose
    `|D - the client track|` reaches the radius, i.e. the match failing at
    arrival. `next_report` is the operand round 5 actually measured when it
    priced P3 at 45.7%: the distance from D to the client's NEXT report. The
    first is the harness's; the second is the pre-registered prediction's. They
    are not interchangeable and both are printed.
    """
    if not arrivals:
        return {"n": 0, "poly": float("nan"), "next_report": float("nan")}
    miss_poly = sum(1 for r in arrivals if r["poly"] >= radius)
    miss_next = 0
    for r in arrivals:
        j = bisect.bisect_left(ts, r["t"])
        if j >= len(reps):
            j = len(reps) - 1
        P = reps[j][1]
        if math.hypot(r["q"][0] - P[0], r["q"][1] - P[1]) >= radius:
            miss_next += 1
    n = len(arrivals)
    return {"n": n, "poly": miss_poly / n, "next_report": miss_next / n}


# =========================================================================
# Scoring one capture under one policy -- `REALFIX.md` §2.4
# =========================================================================

def cadence(track):
    """The capture's own report gap and chord, printed BESIDE every row.

    Non-hard intervals at or under ACTIVE_THRESHOLD, which is the definition
    round 5 §4 used. It is here because it sizes every blind spot this file has:
    where the chord p90 exceeds the match radius, the polyline between two
    reports is a chord across ground the client did not walk in a straight line,
    and the proxy's distance is over-estimated there.
    """
    rows = [r for r in track["rows"]
            if r["dt"] <= ACTIVE_THRESHOLD and not movesync.hard_step(r)]
    gaps = [r["dt"] for r in rows]
    chords = [r["dist"] for r in rows]
    return {"n": len(rows),
            "gap_p50": movesync.pct(gaps, 0.5), "gap_p90": movesync.pct(gaps, 0.9),
            "chord_p50": movesync.pct(chords, 0.5),
            "chord_p90": movesync.pct(chords, 0.9)}


def _path_length(reps, t0, t1):
    """How far the client itself travelled over [t0, t1] -- the survival distance."""
    total = 0.0
    ts = [r[0] for r in reps]
    prev_p = client_at(reps, ts, t0)
    for t, p, *_rest in reps:
        if t <= t0:
            continue
        if t >= t1:
            break
        total += math.hypot(p[0] - prev_p[0], p[1] - prev_p[1])
        prev_p = p
    end = client_at(reps, ts, t1)
    total += math.hypot(end[0] - prev_p[0], end[1] - prev_p[1])
    return total


def score(track, policy, *, c2s=None, params=None, **kw):
    """One capture, one policy: the bracket, the metrics, and the censor.

    The BRACKET is unconditional. `[match ON, match OFF]` is a lower and an
    upper bound and the file never prints one arm alone.
    """
    if c2s is None:
        c2s = c2s_moves(capture_path(track["label"].split("-")[1]))
    p = dict(params or {})
    p.setdefault("track", track)
    grants = policy(c2s, p)

    reps = track["reps"]
    on = simulate(reps, grants, match_on=True, **kw)
    off = simulate(reps, grants, match_on=False, **kw)

    den = track["den"]
    span = den["span"]
    active = movesync.active_time(den["gaps"], ACTIVE_THRESHOLD)
    hard = movesync.hard_steps(track["rows"])
    first_hard = hard[0]["t"] if hard else None

    t0 = reps[0][0]
    censors = [(on["first_snap"], "predicted-snap"),
               (first_hard, "measured-hard-step")]
    live = [(t, why) for t, why in censors if t is not None]
    if live:
        censor_t, censor_by = min(live, key=lambda r: r[0])
    else:
        censor_t, censor_by = reps[-1][0], "capture-end (no violation of either kind)"

    displaced = sum(r["sep"] for r in on["snaps"])
    return {
        "stamp": track["label"], "origin": track["origin"],
        "grants": len(grants), "assent_grants": len(track["grants"]),
        "zero_arm": on["zero_arm"],
        "bracket": [on["n_snaps"], off["n_snaps"]],
        "on": on, "off": off,
        "span": span, "active": active, "active_threshold": ACTIVE_THRESHOLD,
        "coverage": (active / span) if span > 0 else float("nan"),
        "per_min_span": movesync.per_minute(on["n_snaps"], span),
        "per_min_active": movesync.per_minute(on["n_snaps"], active),
        "displaced_per_active_s": (displaced / active) if active > 0 else float("nan"),
        "measured_hard": len(hard),
        "measured_per_min_span": movesync.per_minute(len(hard), span),
        "survival_t": censor_t - t0,
        "survival_u": _path_length(reps, t0, censor_t),
        "censor_by": censor_by, "censor_t": censor_t,
        "cadence": cadence(track),
    }


# =========================================================================
# REALFIX-C1 -- the simulator against a direct memory read, glide-conditioned
# =========================================================================

def glide_flags(track, run_speed=movesync.RUN_SPEED):
    """[(t, modelled pos, gliding)] at every report. `sync_track` is NOT forked.

    `REALFIX.md` §2.2 forbids forking `resyncscore.sync_track`'s glide, and this
    obeys it literally: the leg schedule is recovered by SAMPLING the same
    function on a finer time grid. `sync_track` evaluates `at(t)` at each row of
    `track["reps"]` and its state depends only on `reps[0]` and `grants`, so
    adding a pseudo-report at every grant instant changes nothing about the
    model and hands back `at(grant_time)` -- which is the leg's start point, and
    the one value a caller cannot otherwise see.

    Verified against the published round-5 figures to the second decimal on all
    five pairs (parked 53.0/58.6/83.1/8.5/3.8%, glide p50 27.55/23.54/24.53/
    20.68/14.62 u).
    """
    reps, grants = track["reps"], track["grants"]
    if not reps:
        return []
    t0 = reps[0][0]
    fine = list(reps) + [(gt, [0.0, 0.0]) for gt, _D in grants if gt > t0]
    fine.sort(key=lambda r: r[0])
    at_fine = {}
    for t, p in resyncscore.sync_track({"reps": fine, "grants": grants}, run_speed):
        at_fine.setdefault(t, p)
    ends = []
    for gt, D in grants:
        frm = at_fine.get(gt)
        if gt <= t0 or frm is None:
            continue
        ends.append((gt, gt + math.hypot(D[0] - frm[0], D[1] - frm[1]) / run_speed))
    gts = [e[0] for e in ends]
    out = []
    for t, p in resyncscore.sync_track(track, run_speed):
        i = bisect.bisect_right(gts, t) - 1
        out.append((t, p, i >= 0 and t < ends[i][1]))
    return out


def c1_pair(stamp, tap):
    """REALFIX-C1 for one movetap pair: the residual, conditioned on gliding.

    THE UNCONDITIONED p50 IS DILUTED and is not the gate. Three of the five
    pairs are 53-83% parked, and a parked copy sitting exactly where the model
    parks it contributes a residual of 0.00 that measures the parking rather
    than the model.
    """
    path = capture_path(stamp)
    samples = movesync.load_movetap(movetap_path(tap))
    reps, walls, _src = movesync.load_wire_reports(path)
    off, spread = movesync.offset_from_stamps(walls)
    if off is None or not samples:
        raise Refused(f"grantsim: {stamp} has no clock stamps or no movetap samples")
    pairs = movesync.pair(samples, reps, off)
    track = resyncscore.track_from_capture(path)
    model = {t: (p, g) for t, p, g in glide_flags(track)}
    allr, glide, park = [], [], []
    for st, _p, s, _gap in pairs:
        if st not in model:
            continue
        v = s.get("live")
        if not v or not all(math.isfinite(c) for c in v[:2]):
            continue
        m, gliding = model[st]
        r = math.hypot(m[0] - v[0], m[1] - v[1])
        allr.append(r)
        (glide if gliding else park).append(r)
    if not allr:
        raise Refused(
            f"grantsim: {stamp} paired 0 movetap samples with client reports -- "
            f"a residual over an empty population is not a small residual")
    q = movesync.pct
    return {"stamp": stamp, "tap": tap, "n": len(allr), "offset_spread": spread,
            "parked_frac": len(park) / len(allr),
            "p50": q(allr, 0.5), "p90": q(allr, 0.9), "max": max(allr),
            "glide_n": len(glide),
            "glide_p50": q(glide, 0.5) if glide else float("nan"),
            "glide_p90": q(glide, 0.9) if glide else float("nan"),
            "glide_max": max(glide) if glide else float("nan"),
            "park_n": len(park)}


# =========================================================================
# REALFIX-C2 / C4 -- calibration on as-sent streams, and the nulls
# =========================================================================

def assent_census(stamps=CALIBRATION_11, **kw):
    """REALFIX-C2. Predicted vs measured hard jumps, per capture, as-sent."""
    require_ours([capture_path(s) for s in stamps],
                 what="REALFIX-C2's as-sent calibration")
    rows = []
    for s in stamps:
        tr = track_of(s)
        r = score(tr, policy_assent, c2s=[], params={"track": tr}, **kw)
        r["short"] = s
        rows.append(r)
    return rows


def rotate_grants(grants, k):
    """REALFIX-C4's geometry null: keep every timestamp, permute the destinations."""
    if not grants or k == 0:
        return list(grants)
    n = len(grants)
    return [(grants[i][0],) + tuple(grants[(i + k) % n][1:]) for i in range(n)]


def shift_grants(grants, dt):
    """REALFIX-C4's cadence null: keep every destination, move every timestamp."""
    return [(g[0] + dt,) + tuple(g[1:]) for g in grants]


def null_total(stamps, mutate, **kw):
    """Total predicted snaps over `stamps` with the grant stream mutated."""
    total, per = 0, {}
    for s in stamps:
        tr = track_of(s)
        g = mutate(policy_assent([], {"track": tr}))
        n = simulate(tr["reps"], g, **kw)["n_snaps"]
        per[s] = n
        total += n
    return total, per


# =========================================================================
# REALFIX-C5 -- the sensitivity band, and the refusal to rank
# =========================================================================

C5_WINDOWS = (2.5, 5.0, 10.0)
C5_RADII = (50.0, 100.0, 200.0)
C5_GATES = (250.0, 299.33, 400.0)
C5_MATCH = (True, False)
C5_LEADS = (0.0, LEAD_FIXED, LEAD_ENDPOINT)


def band(stamps=COUNTERFACTUAL, leads=C5_LEADS):
    """Every (window x radius x gate x MATCH-TEST-PRESENCE) cell, per lead.

    THE FOURTH AXIS IS THE POINT. The drafted sweep varied the match RADIUS and
    never the match test's PRESENCE, which is the axis the ranking is not
    invariant on. Returns [{"cfg": ..., "totals": {lead: n}}].
    """
    require_ours([capture_path(s) for s in stamps], what="REALFIX-C5's band")
    tracks = [(s, track_of(s)) for s in stamps]
    c2s = {s: c2s_moves(capture_path(s)) for s in stamps}
    out = []
    for m in C5_MATCH:
        for w in C5_WINDOWS:
            for rad in C5_RADII:
                for g in C5_GATES:
                    totals = {}
                    for lead in leads:
                        pol = lead_policy(lead)
                        n = 0
                        for s, tr in tracks:
                            n += simulate(tr["reps"], pol(c2s[s]), match_on=m,
                                          window=w, radius=rad, gate=g)["n_snaps"]
                        totals[lead] = n
                    out.append({"cfg": {"match": m, "window": w, "radius": rad,
                                        "gate": g},
                                "totals": totals})
    return out


def rank_or_refuse(cells):
    """The ordering of the leads if ONE survives the whole band, else None.

    `REALFIX.md` §2.6 C5: *"any ordering claim survives the full band including
    the match-test axis, or no ordering is printed."* This is the function that
    enforces it, and `test_grantsim.py` §C5 asserts BOTH directions -- that it
    returns None on the real substrate, and that it returns an ordering on a
    synthetic band where one genuinely is invariant, so the refusal is not
    vacuous.

    "Survives" means: for every ordered pair (a, b) the sign of
    `total[a] - total[b]` never changes across cells, and at least one pair is
    strictly ordered somewhere. Ties everywhere are not an ordering.
    """
    if not cells:
        return None
    leads = sorted(cells[0]["totals"])
    strict = False
    for i, a in enumerate(leads):
        for b in leads[i + 1:]:
            signs = set()
            for c in cells:
                d = c["totals"][a] - c["totals"][b]
                signs.add(0 if d == 0 else (1 if d > 0 else -1))
            nz = signs - {0}
            if len(nz) > 1:
                return None                 # inverts somewhere: refuse
            if nz:
                strict = True
    if not strict:
        return None
    return tuple(sorted(leads, key=lambda L: sum(c["totals"][L] for c in cells)))


# =========================================================================
# REALFIX-F1b -- the FIELD-4 POLICY PRE-SCREEN, and it is a different
# instrument from everything above it
# =========================================================================
#
# WHAT IT IS FOR. Everything above this line scores whether a policy would have
# SNAPPED. This scores a different question, cheaply and against captures the
# vault already holds: given a candidate policy for the 0x0029's FIELD 4 -- the
# plane word the client writes to agent+0x80 on the SYNC copy -- how many
# grants would have carried a value that disagreed with the plane that copy was
# actually on? That count is REALFIX-F1's own pre-registered falsifier, it is
# the one F1 FAILED (5 of 93), and it is measurable offline because the grants
# are on the wire and the copy's true plane is in movetap.
#
# WHY IT IS WORTH A PERMANENT MODULE rather than a scratch script: this is how
# every future field-4 policy gets pre-screened before it costs a live arm.
# Three have now been proposed, two have been run, and one of the two ran
# against a prediction that an hour of offline replay would have shown it could
# not meet.
#
# WHAT IT MEASURES THAT IS NOT A TAUTOLOGY, stated first because the headline
# number IS partly one and saying so afterwards would be too late:
#
#   1. THE ARRIVAL MODEL IS FALSIFIABLE AND IT SURVIVES. The SYNC copy's plane
#      word is written by TWO writers: field 4 at the grant, and field 3 again
#      at ARRIVAL, when the client consumes the destination into m_point. In
#      capture 20260821T143411 the word changes 24 times and 17 of those are
#      NOT at a grant -- and all 17 land on an arrival this model predicts,
#      with ZERO free parameters (the formula is the client's own bake, the
#      speed is the 288.0 the client itself holds in 4,115 of 4,115 samples).
#      Had the model been wrong, 17 writes at up to 1.9 s from any grant had
#      every opportunity to say so.
#   2. THE REPLAY REPRODUCES BOTH CAPTURES' MEASURED COUNTS. Run each capture's
#      OWN arm through the simulator and it must return the number measured
#      directly against movetap -- 8 for the P2 control, 5 for the F1 arm.
#      That is the calibration gate and it is checked, not assumed.
#
# AND THE PART THAT IS ANALYTIC, NAMED HERE SO NOBODY HAS TO DISCOVER IT: once
# the arrival model is granted, F1b's zero FOLLOWS *under the closed model*.
# The copy's plane word is the more recent of (the last field 4 we sent) and
# (the field 3 of the last grant that arrived); F1b sends exactly the second of
# those; and when no arrival has intervened since the last grant, F1b's own
# previous send is already that same value. So `field4_replay` returning 0 for
# F1b is a THEOREM OF THAT SIMULATOR and NOT a measurement of the fix. It is
# reported, labelled, and it is NOT the headline.
#
# WHICH IS WHY THE PRIMARY METRIC IS `field4_anchored`, NOT `field4_replay`.
# It compares a policy's field 4 against the plane word MOVETAP ACTUALLY READ in
# the sample before the grant, and it refuses every grant where the observation
# has been contaminated by the counterfactual's own divergence. It cannot be
# satisfied by a model agreeing with itself -- and on the F1 capture it says
# F1b would have left THREE mismatches, not zero. See `FIELD4_RESIDUAL_NOTE`.

# The two REALFIX-L3 arms, their taps, and WHICH POLICY ACTUALLY RAN in each.
# The third L3 arm (P0 default, 20260821T131938) is NOT here: it sent zero
# grants, so it has no field-4 stream to score and a 0-of-0 would read as a
# perfect policy.
FIELD4_PAIRS = (
    ("20260821T132546", "movetap-20260821T132603.jsonl", "shipped-zerolead"),
    ("20260821T143411", "movetap-20260821T143429.jsonl", "F1-planecarry"),
)

# THE PUBLISHED NUMBERS, and this instrument CORRECTS THEM UPWARDS BY TWO AND
# BY ONE. `studies/movement/FINDINGS.md` (REALFIX-F1 RAN) records 8 of 88 and 5
# of 93, measured by pairing each grant with the movetap sample NEAREST it. That
# pairing admits a sample taken AFTER the grant -- and a sample after the grant
# reads the plane word THE GRANT JUST WROTE, so a genuine rewrite scores as a
# match. It happens twice in the P2 capture (leads +0.044 s, +0.043 s) and once
# in the F1 capture (+0.016 s). Pairing with the last sample STRICTLY BEFORE the
# grant gives 10 and 6, and 10 is independently corroborated: FINDINGS's own L3
# table already reports "plane-word changes 10" for that arm, beside the 8.
# Both are kept so the correction is visible rather than silently applied.
FIELD4_PUBLISHED_NEAREST = {"20260821T132546": 8, "20260821T143411": 5}
FIELD4_MEASURED = {"20260821T132546": 10, "20260821T143411": 6}

# WHAT THE COUNTERFACTUAL FOUND, recorded here because it is a NEGATIVE and
# negatives are the ones that get quietly dropped. REALFIX-F1b's pre-registered
# prediction is "the field-4 mismatch count reaches 0". Against the F1 capture,
# observation-anchored, IT DOES NOT: 3 of 69 scorable grants survive, at capture
# t = 50.21 / 77.42 / 104.67 -- three of the same five rows FINDINGS lists as
# F1's residual.
#
# THE THREE ARE A TIMING RACE, NOT A LOGIC ERROR, and the distinction is the
# whole diagnosis. F1b's field 4 turns on one comparison, `arrival <= now`, and
# all three grants land 8 / 24 / 35 ms AFTER a modelled arrival that the client
# had not yet performed. Measured against the client's own 17 unambiguous
# arrival writes, the model lands INSIDE the observation bracket in 13 of 17 and
# is strictly early by AT MOST 20 ms in the other 4. That one-sided residual is
# the size of a display frame, and the client consumes an arrival on a frame
# rather than on the tick -- so the model is right about the tick and early
# about the ACT.
#
# F1b's LOGIC nonetheless fixes what it was built to fix: of F1's 6 anchored
# residuals, the 3 that are genuine TWO-INTERVAL lags are GONE. Only the race
# remains, and it is a class of error F1 shares -- those same three grants are
# in F1's residual too, and FINDINGS reads all five of F1's as two-interval
# lags. Three of them are not; they are this race, and F1 hit them by sending
# the right value 24 ms early rather than by lagging.
#
# THE OBVIOUS PATCH IS REFUSED. A guard band -- treat a grant as arrived only
# past `arrival + eps` -- closes all three at eps ~ 40 ms. It is NOT adopted:
# eps has no derivation, it would be fitted to the one capture that scores it,
# and the house rule is to prefer the check with no free parameter. If a
# frame-consumption term is real it should be MEASURED (the client's frame clock
# is readable) and then it stops being free. Until then F1b ships with its
# residual stated rather than tuned away, and its startup banner predicts 3
# rather than 0.
FIELD4_RESIDUAL_NOTE = (
    "F1b does NOT reach 0. Anchored on the F1 capture it leaves 3 of 69, all "
    "three grants landing 8-35 ms after a modelled arrival the client had not "
    "yet performed -- a sub-frame race on `arrival <= now`, not a logic error. "
    "Its logic does close all 3 of F1's genuine two-interval lags. A ~40 ms "
    "guard band would close the rest and is REFUSED as a fitted parameter.")

# What `--zero-lead --arrival-carry` should be expected to produce on a rerun of
# the REALFIX-L3 plan, and it is the number the server's startup banner prints.
# NOT zero. Scored offline, above.
FIELD4_F1B_EXPECTED = 3

# THE SIX CELLS THE SERVER'S --arrival-carry BANNER TRANSCRIBES, so that the
# banner and the scorer cannot drift apart in silence. `authsrv.py` prints this
# table as the evidence for its own pre-registered prediction and MAY NOT import
# this module (grantsim imports authsrv; the server path stays dependency-clean),
# so the tie is made on the test side: `test_grantsim.py` §10 pins every cell
# against the live computation, and `test_position_trust.py` §16 rebuilds the
# banner's three printed rows from this dict and requires them verbatim.
#
# WHY IT IS A CONSTANT AND NOT A COMMENT. It was a comment. A mutation lane
# rewrote the banner's F1b row from "3 of 69" to "0 of 69" -- the DRAFTED
# prediction this screen had already refuted, printed beside prose still reading
# "F1b DOES NOT REACH ZERO" and "come in at ~3" -- and the whole suite stayed
# green at 215/215. That is section 15's own defect (a number the artifact
# exists to make unrationalisable, left free) reappearing in the numeric half of
# the same banner one section later.
#
# (mismatch, scored) per policy per capture; `scored` is the denominator AFTER
# the contamination refusal, which is why the two counterfactual columns on the
# P2 capture score over 8 grants and not 88.
FIELD4_SCREEN = {
    "shipped-zerolead": {"20260821T132546": (10, 88),
                         "20260821T143411": (18, 36)},
    "F1-planecarry": {"20260821T132546": (0, 8),
                      "20260821T143411": (6, 93)},
    "F1b-arrivalcarry": {"20260821T132546": (0, 8),
                         "20260821T143411": (3, 69)},
}

# TWO ROLES, TWO CONSTANTS, and they were ONE constant until 2026-08-21.
#
# (a) PAIRING. Pair a grant with a tap sample, refusing past this. Both files
# carry `wall_unix`, so this is REALFIX-T1-exact -- the residual is the float
# stamp's own 0.354 ms, not a clock alignment -- and 0.25 s is the same window
# REALFIX-E is defined over. The tap runs at 7.8-9.5 Hz against a 20 Hz request,
# so a sample is 0.103-0.108 s wide (median, both captures) and this admits at
# most two. Used by `_nearest_tap`, `field4_seed` and `field4_anchored`.
#
# ⚠ THIS ROLE IS NOT BINDING ON THE TWO CAPTURES WE HAVE, which is exactly why
# it needs its own name and its own check rather than sharing a number. Every
# grant's last-strictly-before sample lands within 0.122 s, so all 88 and all 93
# pair identically at 0.25 s and at 5.0 s: a 20x widening moves neither the
# anchored headline nor the calibration pin, and nothing would have gone red.
# On a capture with a real tap dropout the strictly-before rule would reach back
# ACROSS the gap and only this constant would stop it. `test_grantsim.py` §10
# therefore brackets it from BOTH sides against the captures' own cadence --
# wide enough that the observed pairing lead fits, narrow enough that it cannot
# span three tap intervals -- so the guard is a check the data can refute.
FIELD4_PAIR_GAP = 0.25

# (b) ATTRIBUTION. "Is this plane-word transition one WE wrote?" A transition
# within this of a grant is ours (field 4 stamped it); everything else is a
# write by the CLIENT and is the population the arrival model is falsified
# against. Used by `field4_client_writes` and `field4_arrival_check`.
#
# THIS ROLE IS BINDING, and it is the one a mutation reddens: widening it makes
# every transition attributable to a grant, the arrival control loses its
# population, and the instrument refuses 0-of-0 rather than passing it. Same
# value as (a) today and derived the same way -- two tap intervals -- but they
# answer different questions and either could move without the other.
FIELD4_ATTRIB_GAP = 0.25

# The gate for "a non-grant plane write lands on a modelled arrival". Three tap
# intervals at the rate these captures actually achieved. REALFIX-T3 said the
# residual becomes sample-phase-bound once the clock stopped being the problem;
# it did, and this is that bound rather than a tolerance chosen to pass.
FIELD4_ARRIVAL_GATE = 0.30

# Per-sample agreement the plane-word model must reach on both captures. Set
# from real runs (99.73% and 99.66%), floored below both at a round number that
# a genuinely broken model could not reach: predicting the word wrongly at ANY
# of the 24 transitions costs far more than 1% of 2,600 samples.
FIELD4_WORD_AGREEMENT = 0.99


def field4_grants(path):
    """[{t, dest, w3, w4}] -- every player 0x0029, WITH BOTH PLANE WORDS.

    `movesync.load_grants` reads the same rows and drops the plane words on the
    floor, which is fine for a position metric and useless here. The layout is
    the schema's own for GAME_SMSG 41 (`declared_unpack_size` 18): dword agent,
    vec2 point, word plane_dest, word plane_cur.

    FROM THE WIRE, NOT FROM THE TELEMETRY, and that is not a style preference.
    The `grant_verdict` row's `plane_cur` field did not exist when the P2
    control was captured -- it landed with `--plane-carry` later the same day --
    so a telemetry reader scores one of these two captures and refuses the
    other. The bytes are in both.

    `t` is `wall_unix`, so it is directly comparable with a movetap sample's own
    `t` with no offset estimate in between.
    """
    out = []
    for line in open(path, encoding="utf-8", errors="replace"):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("kind") != "sent" or r.get("opcode") != movesync.OP_MOVE_TO_POINT:
            continue
        raw, when = r.get("plain"), r.get("wall_unix")
        if not raw or when is None:
            continue
        b = bytes.fromhex(raw)
        if len(b) < 18:
            continue
        aid, x, y, w3, w4 = struct.unpack_from("<IffHH", b, 2)
        if aid != movesync.PLAYER_AGENT:
            continue
        out.append({"t": float(when), "dest": (x, y), "w3": w3, "w4": w4})
    return out


def field4_taps(path):
    """[{t, plane, pos, sep}] -- the SYNC copy's plane word, per movetap sample.

    `sync_at` is `position_at(agent_block, sync_clock)` and its third element is
    the plane. On the INTEGRATED branch -- which is 5,212 of 5,212 samples
    across both captures -- that is `agent+0x80` read verbatim, which is the
    exact field REALFIX-F1's falsifier names. Samples whose gate-1 read was
    refused carry `sync_at: null` and are dropped: a refusal there means the
    reader could not resolve the twin, so the row has no plane to offer.
    """
    out = []
    for s in movesync.load_movetap(path):
        sa = s.get("sync_at")
        if not sa or len(sa) < 3:
            continue
        out.append({"t": float(s["t"]), "plane": int(sa[2]),
                    "pos": (float(sa[0]), float(sa[1])), "sep": s.get("sep")})
    return out


def _nearest_tap(taps, ts, when):
    """The tap sample nearest `when`, or None past FIELD4_PAIR_GAP."""
    i = bisect.bisect_left(ts, when)
    best = None
    for j in (i - 1, i, i + 1):
        if 0 <= j < len(taps):
            d = abs(ts[j] - when)
            if best is None or d < best[0]:
                best = (d, j)
    if best is None or best[0] > FIELD4_PAIR_GAP:
        return None
    return taps[best[1]]


def field4_observed(grants, taps):
    """The DIRECT measurement: as-sent field 4 against the copy's own plane word.

    Returns {n, paired, mismatch, rows}. No model, no replay -- this is the
    number `FIELD4_MEASURED` records and the one the simulator has to hit.

    THE PAIRED SAMPLE IS THE ONE NEAREST THE GRANT AND IN PRACTICE IT IS THE ONE
    JUST BEFORE IT (median lead 0.04 s), which is what makes the metric mean
    "did this grant REWRITE the copy's plane word". That is exactly REALFIX-L3's
    treated condition: 8 plane-rewriting above-cut grants produced 3 warps, 28
    unchanged above-cut grants produced 0, Fisher p = 0.0078.
    """
    ts = [t["t"] for t in taps]
    rows, paired = [], 0
    for g in grants:
        s = _nearest_tap(taps, ts, g["t"])
        if s is None:
            continue
        paired += 1
        if g["w4"] != s["plane"]:
            rows.append({"t": g["t"], "dest": g["dest"], "w3": g["w3"],
                         "w4": g["w4"], "copy_plane": s["plane"],
                         "sep": s["sep"]})
    return {"n": len(grants), "paired": paired, "mismatch": len(rows),
            "rows": rows}


# THE THREE POLICIES. Each takes the replay's server-shaped `state`, the grant
# instant and field 3, and returns (field 4, why). All three are driven through
# the SHIPPED code where shipped code exists -- `policy_f1b` calls
# `authsrv.arrival_carry_field4` rather than restating it -- for the reason
# `_heading_grant_ok`'s docstring gives: a scorer that paraphrases the policy
# agrees with it by construction and can never catch it being wrong.

def policy_shipped_zerolead(state, now, w3):
    """REALFIX-P2 as shipped. Field 4 = field 3 = the newest report's plane."""
    return w3, "zero-lead"


def policy_f1_planecarry(state, now, w3):
    """REALFIX-F1. Field 4 = the PREVIOUS GRANT'S plane, defaulting to field 3.

    One line, and it is the shipped one: `state.get("zl_last_grant_plane",
    plane)`. The slot is advanced by the replay loop after each grant, which is
    where the shipped send site advances it.
    """
    return state.get("zl_last_grant_plane", w3), "plane-carry"


def policy_f1b_arrivalcarry(state, now, w3):
    """REALFIX-F1b. Field 4 = the plane of the grant the copy has ARRIVED at."""
    return _authsrv().arrival_carry_field4(state, now, w3)


FIELD4_POLICIES = {
    "shipped-zerolead": policy_shipped_zerolead,
    "F1-planecarry": policy_f1_planecarry,
    "F1b-arrivalcarry": policy_f1b_arrivalcarry,
}


def field4_replay(grants, policy, seed_plane, seed_pos):
    """Replay ONE field-4 policy over one capture's own grant stream.

    Returns {n, mismatch, rows, writes, queue_max}. `rows` carries every grant
    with the field 4 the policy would have sent, the plane word the copy would
    have been holding at that instant, and whether they disagree.

    THE PLANE WORD HAS TO BE SIMULATED, and the reason is the whole subtlety of
    this scorer. Field 4 is WRITTEN to `agent+0x80`, so changing the policy
    changes the copy's plane-word history too -- the observed movetap trace is
    ground truth only for the policy that actually ran. What is POLICY-INVARIANT
    is everything else: the grant instants, the destinations and field 3 are
    identical under all three candidates (they differ in field 4 alone), so the
    ARRIVAL SCHEDULE is the same in every replay and the arrival writes are the
    same. Only the grant writes move.

    THE MODEL, and both writers are measured rather than assumed:
      * at a GRANT, the client writes field 4 to agent+0x80. Measured: 10 of 10
        plane-word transitions in the P2 capture are at a grant, and the paired
        sample before each residual reads the previous field 4 in 87 of 87.
      * at ARRIVAL, the client writes field 3 -- it consumes the destination
        into m_point, and m_point's plane is +0x80. Measured: 17 of 17 non-grant
        transitions in the F1 capture land on a modelled arrival.

    A PENDING ARRIVAL THAT A NEW GRANT SUPERSEDES NEVER FIRES, and dropping it
    is the same discard `arrival_carry_advance` makes for the same reason: the
    copy re-aims mid-leg and never reaches that destination, so its plane is
    never written. A simulator that let it fire would credit every policy with
    a write the client does not make.

    SEEDED FROM THE TAP because these captures start mid-session: the copy's
    position and plane word at the first grant are read once from the sample
    before it. The live server has no such need -- it seeds its SYNC model where
    it places the character -- and the seed is reported so a reader can see how
    little of the answer rests on it (one grant of 88, and both captures begin
    parked at the spawn point with the copy and the player on the same plane).
    """
    A = _authsrv()
    if not grants:
        raise Refused("grantsim: a field-4 replay over an empty grant stream")
    state = {"sync_from": (float(seed_pos[0]), float(seed_pos[1])),
             "sync_to": None, "sync_at": grants[0]["t"],
             "ac_queue": [], "ac_arrived": None}
    word = int(seed_plane)
    pending = None                       # (arrival_t, field3) not yet due
    rows, writes, queue_max = [], [], 0
    for g in grants:
        now, dest, w3 = g["t"], g["dest"], g["w3"]
        # (1) an arrival that came due since the last grant already wrote.
        if pending is not None and pending[0] is not None and pending[0] <= now:
            word = pending[1]
            writes.append((pending[0], pending[1], "arrival"))
        field4, why = policy(state, now, w3)
        rows.append({"t": now, "dest": dest, "w3": w3, "field4": field4,
                     "word_before": word, "mismatch": field4 != word,
                     "why": why, "as_sent": g["w4"]})
        # (2) the leg, computed BEFORE the send moves the SYNC model -- the
        # ordering that makes the in-flight supersede case come out right.
        arrival, _dist = A.arrival_carry_leg(state, now, dest)
        # (3) the grant writes field 4; any pending arrival is superseded.
        word = field4
        writes.append((now, field4, "grant"))
        pending = (arrival, w3)
        # (4) advance the server's own model exactly as the shipped send does.
        A._note_wire_move(state, A.GAME_SMSG_AGENT_MOVE_TO_POINT,
                          [A.PLAYER_AGENT_ID, list(dest)], now)
        state["zl_last_grant_plane"] = w3
        A.arrival_carry_advance(state, now, arrival, w3, dest)
        queue_max = max(queue_max, len(state["ac_queue"]))
    if pending is not None and pending[0] is not None:
        writes.append((pending[0], pending[1], "arrival"))
    writes.sort(key=lambda w: w[0])
    return {"n": len(grants), "mismatch": sum(1 for r in rows if r["mismatch"]),
            "rows": rows, "writes": writes, "queue_max": queue_max,
            "seed": (seed_plane, tuple(seed_pos))}


def field4_seed(grants, taps):
    """(plane, position) of the SYNC copy at the first grant, from the tap."""
    ts = [t["t"] for t in taps]
    s = _nearest_tap(taps, ts, grants[0]["t"])
    if s is None:
        raise Refused(
            "grantsim: the first grant pairs with no movetap sample inside "
            f"{FIELD4_PAIR_GAP:.2f} s -- the replay would be seeded from a "
            "position and a plane nobody measured")
    return s["plane"], s["pos"]


def field4_arrival_check(replay, taps):
    """Does the model's ARRIVAL schedule explain the writes WE did not make?

    This is the falsifiable half of the instrument. Walk the observed plane-word
    transitions; ignore any within `FIELD4_ATTRIB_GAP` of a grant (we wrote those
    ourselves through field 4); every remaining one is a write by the CLIENT,
    and the model says it must be an arrival carrying that plane as its field 3.

    Returns {n, hit, miss, dt_median, dt_max, rows}. `miss` is the number the
    model cannot explain, and it is the count that can go red.
    """
    grant_ts = [w[0] for w in replay["writes"] if w[2] == "grant"]
    arrivals = [(w[0], w[1]) for w in replay["writes"] if w[2] == "arrival"]
    hit, miss, dts, early, rows = 0, 0, [], [], []
    prev, prev_t = None, None
    for s in taps:
        p = s["plane"]
        if prev is not None and p != prev:
            i = bisect.bisect_left(grant_ts, s["t"])
            near = min([abs(grant_ts[j] - s["t"])
                        for j in (i - 1, i) if 0 <= j < len(grant_ts)]
                       or [float("inf")])
            if near <= FIELD4_ATTRIB_GAP:
                prev, prev_t = p, s["t"]
                continue
            cand = sorted(((abs(a - s["t"]), a)
                           for a, pl in arrivals if pl == p))
            if cand and cand[0][0] <= FIELD4_ARRIVAL_GATE:
                hit += 1
                dts.append(cand[0][0])
                # THE SIGNED RESIDUAL, and it is the one that matters for F1b.
                # The client's write happened somewhere in (prev_t, s.t] -- the
                # tap bracket. `early_by > 0` means the model fired BEFORE that
                # bracket even opened, which is the only way F1b can call a
                # grant "arrived" that the client has not yet acted on.
                early.append(prev_t - cand[0][1])
            else:
                miss += 1
                rows.append({"t": s["t"], "was": prev, "now": p,
                             "best": cand[0][0] if cand else float("inf")})
        prev, prev_t = p, s["t"]
    early_s = sorted(early)
    return {"n": hit + miss, "hit": hit, "miss": miss, "rows": rows,
            "dt_median": (sorted(dts)[len(dts) // 2] if dts else float("nan")),
            "dt_max": (max(dts) if dts else float("nan")),
            "early_n": sum(1 for e in early if e > 0.0),
            "early_max": (max(early_s) if early_s else float("nan")),
            "early_median": (early_s[len(early_s) // 2] if early_s
                             else float("nan"))}


def field4_race(rows, replay):
    """For each anchored residual: how long after a MODELLED ARRIVAL did it land?

    The diagnosis, not a verdict. A residual a few tens of milliseconds after an
    arrival the client had not yet performed is a RACE on `arrival <= now`; one
    seconds away from any arrival is a policy LAG. Returns the same rows with
    `since_arrival` added, so the reader sees the two populations rather than a
    threshold somebody chose.
    """
    arrivals = sorted(w[0] for w in replay["writes"] if w[2] == "arrival")
    out = []
    for r in rows:
        i = bisect.bisect_right(arrivals, r["t"]) - 1
        r = dict(r)
        r["since_arrival"] = (r["t"] - arrivals[i]) if i >= 0 else float("nan")
        out.append(r)
    return out


def field4_word_check(replay, taps, seed_plane):
    """Per-sample: does the write schedule predict the observed plane word?

    2,500-odd trials per capture against 24 transitions, so a model that had the
    arrival times wrong could not sit above 99%. Returns {n, ok, frac, wrong}.
    """
    wt = [w[0] for w in replay["writes"]]
    ok = 0
    for s in taps:
        i = bisect.bisect_right(wt, s["t"]) - 1
        pred = replay["writes"][i][1] if i >= 0 else seed_plane
        if pred == s["plane"]:
            ok += 1
    n = len(taps)
    return {"n": n, "ok": ok, "wrong": n - ok,
            "frac": (ok / n if n else float("nan"))}


def field4_client_writes(grants, taps):
    """The plane-word writes the CLIENT made for itself. PURELY OBSERVATIONAL.

    Every transition of the observed word that is not within FIELD4_ATTRIB_GAP
    of a grant. No model is consulted -- that is the point: these are the instants
    at which the client overwrote whatever we had stamped, so they are where the
    observed trace RE-ANCHORS and becomes usable again for a counterfactual.

    They are also POLICY-INVARIANT. Every candidate sends the same destinations
    at the same instants with the same field 3 and differs in field 4 alone, so
    the copy's position track -- and therefore when it arrives and what the
    client writes on arriving -- is the same under all of them.
    """
    gts = [g["t"] for g in grants]
    out, prev = [], None
    for s in taps:
        p = s["plane"]
        if prev is not None and p != prev:
            i = bisect.bisect_left(gts, s["t"])
            near = min([abs(gts[j] - s["t"])
                        for j in (i - 1, i) if 0 <= j < len(gts)]
                       or [float("inf")])
            if near > FIELD4_ATTRIB_GAP:
                out.append((s["t"], p))
        prev = p
    return out


def field4_anchored(grants, taps, replay):
    """THE PRIMARY METRIC. A policy's field 4 against the word MOVETAP READ.

    Returns {scored, mismatch, skipped, rows, why_skipped}.

    THE OPERAND IS THE LAST SAMPLE STRICTLY BEFORE THE GRANT, never the nearest.
    A sample taken after the grant reads the plane word the grant itself just
    wrote, which turns a genuine rewrite into a match -- that is the defect this
    instrument found in the published counts (8 and 5 become 10 and 6; see
    FIELD4_PUBLISHED_NEAREST).

    CONTAMINATION, and refusing it is what stops this being another model
    agreeing with itself. The observed word is a record of what the arm that
    ACTUALLY RAN stamped. The moment a counterfactual policy would have sent a
    different field 4, every later observation is a reading of the wrong
    history -- until the CLIENT overwrites it at an arrival, which is
    policy-invariant and re-anchors the trace. So a grant is scored only while
    `dirty` is clear, and `dirty` is set by a divergence and cleared by a client
    write. `skipped` is reported beside every count, because 3 of 69 and 3 of 3
    are not the same claim.

    ⚠ THE P2 CAPTURE HAS ZERO CLIENT WRITES, so on it nothing ever re-anchors
    and both counterfactual columns score over ~8 grants. That is not a defect
    of this metric, it is the capture: under `--zero-lead` field 4 always equals
    the client's current plane, so the client never has to correct us and never
    reveals what it thinks. The F1 capture is the one that carries the result,
    and it does so BECAUSE F1's field 4 lags -- the lag is what makes the
    client's own opinion observable 17 times.
    """
    ts = [t["t"] for t in taps]
    writes = field4_client_writes(grants, taps)
    dirty, ci = False, 0
    scored, rows, skipped = 0, [], {"contaminated": 0, "unpaired": 0}
    # THE PAIRING WINDOW'S OWN MARGIN, reported rather than assumed. `lead_max`
    # is the largest gap between a grant and the last sample STRICTLY BEFORE it
    # -- taken whether or not that sample fell inside the window, which is the
    # whole point. Recording only the ones that PAIRED would make the margin
    # unfalsifiable from the narrow side: shrink the window and the offending
    # grants simply stop being counted, so `lead_max <= FIELD4_PAIR_GAP` would
    # hold by construction. Measured over every grant it goes red in BOTH
    # directions. Policy-invariant (pairing reads no field 4).
    leads = []
    for k, g in enumerate(grants):
        while ci < len(writes) and writes[ci][0] <= g["t"]:
            dirty = False
            ci += 1
        j = bisect.bisect_left(ts, g["t"]) - 1
        if j >= 0 and g["t"] - ts[j] >= 0.0:
            leads.append(g["t"] - ts[j])
        paired = j >= 0 and 0.0 <= g["t"] - ts[j] <= FIELD4_PAIR_GAP
        f4 = replay["rows"][k]["field4"]
        if not paired:
            skipped["unpaired"] += 1
        elif dirty:
            skipped["contaminated"] += 1
        else:
            scored += 1
            if f4 != taps[j]["plane"]:
                rows.append({"t": g["t"], "dest": g["dest"], "w3": g["w3"],
                             "field4": f4, "observed": taps[j]["plane"],
                             "lead": g["t"] - ts[j], "sep": taps[j]["sep"]})
        if f4 != g["w4"]:
            dirty = True
    return {"scored": scored, "mismatch": len(rows), "rows": rows,
            "skipped": sum(skipped.values()), "why_skipped": skipped,
            "client_writes": len(writes),
            "lead_max": max(leads) if leads else float("nan")}


def field4_capture(stamp, tap, arm):
    """One capture, every policy, plus the two calibration checks. All `ours`."""
    path = capture_path(stamp)
    require_ours([path], what="REALFIX-F1b's field-4 counterfactual")
    grants = field4_grants(path)
    taps = field4_taps(movetap_path(tap))
    if not grants or not taps:
        raise Refused(
            f"grantsim: {stamp} has {len(grants)} grants and {len(taps)} "
            f"readable movetap samples -- a field-4 census over either empty "
            f"population is not a low mismatch count")
    seed_plane, seed_pos = field4_seed(grants, taps)
    obs = field4_observed(grants, taps)
    out = {"stamp": stamp, "tap": tap, "arm": arm, "observed": obs,
           "grants": len(grants), "taps": len(taps),
           "seed_plane": seed_plane, "policies": {}, "anchored": {}}
    for name, pol in FIELD4_POLICIES.items():
        rep = field4_replay(grants, pol, seed_plane, seed_pos)
        out["policies"][name] = rep
        out["anchored"][name] = field4_anchored(grants, taps, rep)
    own = out["policies"][arm]
    own_anchored = out["anchored"][arm]
    out["calibration"] = {
        # THE GATE. Replaying a capture's OWN arm reproduces exactly what it
        # sent, so the anchored score of that replay must equal the anchored
        # score of the wire -- and `dirty` can never be set, so every grant is
        # scored. That is the pin, and it is 10 / 6 rather than the published
        # 8 / 5 for the pairing reason at FIELD4_PUBLISHED_NEAREST.
        "own_arm": arm,
        "own_anchored": own_anchored["mismatch"],
        "own_anchored_scored": own_anchored["scored"],
        "own_replay": own["mismatch"],
        "own_nearest": obs["mismatch"],
        "measured_pin": FIELD4_MEASURED.get(stamp),
        "published_nearest": FIELD4_PUBLISHED_NEAREST.get(stamp),
        "own_agrees": own_anchored["mismatch"] == FIELD4_MEASURED.get(stamp),
        "own_full_coverage": own_anchored["scored"] == len(grants),
        # THE SHARPEST HALF OF THE GATE, stated on its own because "the counts
        # agree" could in principle be two errors cancelling. Replaying a
        # capture's own arm must reproduce its field 4 BYTE FOR BYTE, all 88 and
        # all 93. For F1 that is a real exercise of the policy: its slot
        # advances only on a SEND, so the 6 rate-limit refusals in that capture
        # have to leave it alone or the stream drifts.
        "own_reproduces_wire": all(
            r["field4"] == r["as_sent"] for r in own["rows"]),
        "arrival": field4_arrival_check(own, taps),
        "word": field4_word_check(own, taps, seed_plane),
        # THE PAIRING WINDOW, BRACKETED FROM BOTH SIDES BY THE CAPTURE ITSELF.
        # `pair_lead_max` is how close FIELD4_PAIR_GAP came to binding (it does
        # not, on either capture) and `tap_dt_median` is the cadence the
        # constant's own derivation cites -- "a sample is ~0.105 s wide and this
        # admits at most two". §10 checks the constant against both, so a
        # widened window is caught by a check the data can refute instead of
        # only indirectly, through the arrival control collapsing to 0-of-0.
        "pair_lead_max": own_anchored["lead_max"],
        "tap_dt_median": (sorted(b["t"] - a["t"]
                                 for a, b in zip(taps, taps[1:]))[
                              max(len(taps) - 1, 1) // 2]
                          if len(taps) > 1 else float("nan")),
    }
    return out


def field4_census(pairs=FIELD4_PAIRS):
    return [field4_capture(*row) for row in pairs]


# =========================================================================
# Printing
# =========================================================================

def _say(text=""):
    try:
        print(text)
    except UnicodeEncodeError:
        enc = sys.stdout.encoding or "ascii"
        print(text.encode(enc, "backslashreplace").decode(enc, "replace"))


def _ratio(a, b):
    """`a / b` for a PRINTED line, where a zero denominator must not kill the run.

    Every ratio this file prints is a count over a count, and the degenerate
    case -- no predicted snaps at all -- is exactly the state a reader most
    needs printed. A `ZeroDivisionError` raised inside an f-string takes the
    whole verdict with it, which is the same defect `checks.py`'s own printing
    note is about: forcing the match test to always match killed
    `test_grantsim.py` three sections before it could report the five checks
    that had already gone red. `inf` and `nan` both format and both are honest.
    """
    if b:
        return a / b
    return float("nan") if not a else float("inf")


def print_radius():
    m = derive_match_radius()
    g = derive_gate1_cut()
    _say("REALFIX-C0 -- the decision radius, from the pinned client image")
    _say(f"  exe: {m['exe']}")
    _say(f"       {m['why']}")
    _say(f"  LUT at {hex(LUT_VA)}, 256 dwords, stdlib PE section walk")
    for row, win in ((m, MATCH_SCAN), (g, GATE1_SCAN)):
        _say(f"\n  {row['what']}: {row['scanned']:,} float patterns scanned over "
             f"distSq [{win[0]:.0f}, {win[1]:.0f}], cut {row['cut']}")
        _say(f"    last passing distSq {row['last_pass_distsq']!r}"
             f"  true {row['last_pass_true']:.7f}  approx {row['last_pass_approx']:.8f}")
        _say(f"    first failing distSq {row['first_fail_distsq']!r}"
             f"  true {row['true']:.7f}  approx {row['approx']:.8f}")
        _say(f"    -> effective TRUE threshold {row['true']:.6f} u")
        _say(f"    patterns whose table sqrt lands EXACTLY on the cut: "
             f"{row['equal_at_cut']} -- at 0 the strict and non-strict "
             f"boundaries coincide, which is what lets one scan serve gate 1's "
             f"`> 300.0f` and the match test's `< 100.0`")
    _say(f"\n  POSITIVE CONTROL: a true separation of exactly {GATE1_NOMINAL} u "
         f"reads {g['at_300']:.5f} through the table sqrt, so it "
         f"{'SNAPS' if g['snaps_at_300'] else 'does NOT snap'}.")
    _say(f"  module constants: MATCH_RADIUS {MATCH_RADIUS}  GATE1_CUT {GATE1_CUT}")


def _row(r):
    c = r["cadence"]
    return (f"  {r['short']:<17} {r['grants']:6d} {r['on']['n_instants']:6d}"
            f"   [{r['bracket'][0]:3d},{r['bracket'][1]:3d}] {r['measured_hard']:5d}"
            f"  {r['per_min_span']:8.2f} {r['per_min_active']:10.2f}"
            f"    {c['gap_p50']:.3f}/{c['gap_p90']:.3f}"
            f"   {c['chord_p50']:6.1f}/{c['chord_p90']:6.1f}")


def print_calibration():
    _say("REALFIX-C1 -- the forward model against a DIRECT MEMORY READ, "
         "glide-conditioned")
    _say("  pair               n  parked%   p50    p90    max |  glide n   p50    "
         "p90    max   gated")
    for stamp, tap in MOVETAP_PAIRS:
        r = c1_pair(stamp, tap)
        _say(f"  {stamp}  {r['n']:4d} {100 * r['parked_frac']:6.1f}% "
             f"{r['p50']:6.2f} {r['p90']:6.2f} {r['max']:6.2f} | "
             f"{r['glide_n']:6d} {r['glide_p50']:6.2f} {r['glide_p90']:6.2f} "
             f"{r['glide_max']:6.2f}   {'YES' if stamp in C1_GATED else 'reported'}")
    _say("  The three parked-dominated pairs are REPORTED, not gated: their "
         "unconditioned p50 of 0.00 measures the parking.")

    _say("\nREALFIX-C2 -- snap reproduction on AS-SENT streams "
         f"({len(CALIBRATION_11)} `ours` captures)")
    _say("  capture           grants   inst  [on,off]  meas  rate/span rate/active"
         "    gap p50/p90   chord p50/p90")
    rows = assent_census()
    for r in rows:
        _say(_row(r))
    pred = sum(r["bracket"][0] for r in rows)
    meas = sum(r["measured_hard"] for r in rows)
    _say(f"  TOTAL predicted {pred}  measured {meas}  ratio {_ratio(pred, meas):.2f}x"
         f"   (active-time threshold {ACTIVE_THRESHOLD:.1f} s, NAMED)")
    zeros = {r["short"]: r["bracket"][0] for r in rows if r["short"] in STRUCTURAL_ZEROS}
    _say(f"  C2(a) structural zeros: {zeros} -- the separation-only scorer said "
         f"16 / 12 / 34 here.")
    by = {r["short"]: r["per_min_span"] for r in rows}
    _say(f"  C2(c) separation: high {[f'{by[s]:.2f}' for s in C2C_HIGH]} vs low "
         f"{[f'{by[s]:.2f}' for s in C2C_LOW]} per minute of span")
    _say(f"        INVERSION, printed rather than gated: {C2C_LOW[0]} predicted "
         f"{by[C2C_LOW[0]]:.2f} > {C2C_LOW[1]} {by[C2C_LOW[1]]:.2f}, while measured "
         f"is the other way round "
         f"({[r['measured_per_min_span'] for r in rows if r['short'] == C2C_LOW[0]][0]:.2f}"
         f" < "
         f"{[r['measured_per_min_span'] for r in rows if r['short'] == C2C_LOW[1]][0]:.2f}).")
    return rows


CLICK_ARMS = ("P0-default", "P6-grant-suppress")


def print_counterfactual(names=("P0-default", "P2-zerolead", "P3-shortlead",
                                "P6-grant-suppress", "lead-766")):
    _say("REALFIX-H1 -- the counterfactual substrate, `ours`, zero-grant")
    _say("  " + SUBSTRATE_WARNING)
    _say("  THIS FILE IS NOT A RANKER. The bracket is [match ON, match OFF]; the "
         "ON arm is a LOWER bound and the OFF arm an UPPER bound.")
    scored = {}
    for s in COUNTERFACTUAL:
        tr = track_of(s)
        c2s = c2s_moves(capture_path(s))
        c = cadence(tr)
        _say(f"\n  {s}  span {tr['den']['span']:.1f} s  reports {len(tr['reps'])}"
             f"  measured hard {len(movesync.hard_steps(tr['rows']))}"
             f"  gap p50/p90 {c['gap_p50']:.3f}/{c['gap_p90']:.3f} s"
             f"  chord p50/p90 {c['chord_p50']:.1f}/{c['chord_p90']:.1f} u")
        if c["chord_p90"] >= MATCH_RADIUS:
            _say(f"      NOTE: chord p90 {c['chord_p90']:.1f} u exceeds the "
                 f"{MATCH_RADIUS:.2f} u radius -- the proxy over-estimates "
                 f"distance-to-polyline here. The bracket carries it; the "
                 f"drafted 'skip the match test' rule would have fired and is "
                 f"REPLACED by the bracket.")
        for name in names:
            r = score(tr, policy_named(name), c2s=c2s)
            scored[(s, name)] = r
            on = r["on"]
            extra = ""
            if name in CLICK_ARMS and r["grants"] > r["assent_grants"]:
                extra = (f"  <-- the shipped server sent {r['assent_grants']} here; "
                         f"the {r['grants'] - r['assent_grants']} difference is the "
                         f"THREE GEOMETRY REFUSALS and `clip_to_walkable`, which "
                         f"this file does not model. UPPER BOUND, not a prediction.")
            _say(f"      {name:<20} grants {r['grants']:4d} (zero-arm "
                 f"{r['zero_arm']:4d})  inst {on['n_instants']:5d} "
                 f"(A {on['n_bake']:4d} / B {on['n_arrival']:4d}, FLOOR)  "
                 f"bracket [{r['bracket'][0]:3d},{r['bracket'][1]:3d}]  "
                 f"{r['per_min_span']:5.2f}/min span  {r['per_min_active']:5.2f}"
                 f"/min active  {r['displaced_per_active_s']:6.1f} u/active s"
                 + extra)
            _say(f"      {'':<20} survival {r['survival_t']:7.1f} s / "
                 f"{r['survival_u']:8.1f} u, censored by {r['censor_by']}"
                 f"   sep p50/p90/max {on['sep']['p50']:.0f}/"
                 f"{on['sep']['p90']:.0f}/{on['sep']['max']:.0f} u"
                 f"   snaps A {on['snaps_a']} / B {on['snaps_b']}"
                 f", {on['marginal']} of them MARGINAL (polyline distance under "
                 f"{MARGIN_FACTOR:.1f}x the radius)")
            _say(f"      {'':<20} REALFIX-M1 lag age n {on['m1']['n']} "
                 f"(no node in radius: {on['m1']['unmatched']})  p50 "
                 f"{on['m1']['p50']:.2f} p90 {on['m1']['p90']:.2f} max "
                 f"{on['m1']['max']:.2f} s  against the ~{HISTORY_WINDOW:.0f} s "
                 f"block-recycle bound")
            _say(f"      {'':<20} REALFIX-M2 arrival exposure n {on['m2']['n']}  "
                 f"poly {100 * on['m2']['poly']:.1f}%  next-report "
                 f"{100 * on['m2']['next_report']:.1f}%")
            for snap in on["snaps"]:
                _say(f"      {'':<20}   snap t={snap['t']:8.2f} class "
                     f"{'A' if snap['kind'] == 'bake' else 'B'}  polyline "
                     f"{snap['poly']:8.1f} u  separation {snap['sep']:8.1f} u  "
                     f"in a {snap['gap']:.2f} s report gap")
    _say("")
    print_falsifier(scored)
    return scored


def print_falsifier(scored):
    """REALFIX-D0's REPLACEMENT set-level falsifier, stated with its caveats.

    *"The set fails if any candidate predicts a class-A snap on a zero-grant
    capture"* -- i.e. if a candidate manufactures harm the control did not have.
    Printed rather than gated, and printed with two things beside it: whether
    the snap is MARGINAL (polyline distance inside the instrument's own error
    band) and how wide the report gap it landed in was, because the subsample
    bias is largest exactly there.

    The two CLICK arms are named separately: on this substrate they are upper
    bounds, since the shipped server refused every one of `20260820T182934`'s
    five clicks and 19 of `20260814T100340`'s 21 through the geometry refusals
    this file does not model.
    """
    _say("  SET-LEVEL FALSIFIER (REALFIX-D0's replacement): does any candidate "
         "predict a class-A snap")
    _say("  on a capture whose own server sent zero grants and measured zero "
         "hard jumps?")
    fired = []
    for (s, name), r in sorted(scored.items()):
        if s not in STRUCTURAL_ZEROS or not r["on"]["snaps_a"]:
            continue
        arm = "CONTROL ARM, upper bound" if name in CLICK_ARMS else "CANDIDATE"
        fired.append((s, name))
        _say(f"    {name:<20} {s}  class-A snaps {r['on']['snaps_a']}"
             f"  ({r['on']['marginal']} marginal)   [{arm}]")
    if not fired:
        _say("    no -- every candidate holds at zero class-A snaps on the "
             "zero-grant captures.")
    else:
        _say("    YES, and it is printed rather than swallowed. Read each row "
             "against its own marginality and gap columns above.")


ROTATIONS = (0, 1, 5, 17)
SHIFTS = (-0.35, 0.35, 3.0)
SHIFT_GATED = 3.0
SHIFT_GATED_CAPTURES = ("20260820T195137", "20260819T182652")


def nulls(stamps=CALIBRATION_11):
    """REALFIX-C4. Every null this instrument has, including the one it FAILS."""
    base, per_base = null_total(stamps, lambda g: g)
    out = {"base": base, "per_base": per_base,
           "match_off": null_total(stamps, lambda g: g, match_on=False)[0],
           "rotate": {}, "shift": {}, "shift_per": {}}
    for k in ROTATIONS:
        out["rotate"][k] = null_total(stamps, lambda g, k=k: rotate_grants(g, k))[0]
    for dt in SHIFTS:
        t, per = null_total(stamps, lambda g, dt=dt: shift_grants(g, dt))
        out["shift"][dt] = t
        out["shift_per"][dt] = per
    out["measured"] = {}
    for s in stamps:
        out["measured"][s] = len(movesync.hard_steps(track_of(s)["rows"]))
    return out


def print_nulls():
    n = nulls()
    base = n["base"]
    _say("REALFIX-C4 -- the nulls, and the one this instrument FAILS")
    _say(f"  base total {base} over {len(CALIBRATION_11)} `ours` captures, "
         f"measured {sum(n['measured'].values())}")
    _say(f"  MATCH TEST DELETED: {n['match_off']}  "
         f"({_ratio(n['match_off'], base):.2f}x) -- the match test is load-bearing")
    _say("  ROTATE destinations (timestamps kept): "
         + "  ".join(f"k={k} {n['rotate'][k]} "
                     f"({100.0 * _ratio(n['rotate'][k] - base, base):+.1f}%)"
                     for k in ROTATIONS))
    _say("  SHIFT timestamps (destinations kept):  "
         + "  ".join(f"{dt:+.2f}s {n['shift'][dt]} "
                     f"({100.0 * _ratio(n['shift'][dt] - base, base):+.1f}%)"
                     for dt in SHIFTS))
    meas_total = sum(n["measured"].values())
    _say(f"  *** THE FAILURE, PRINTED: shifting every grant by +0.35 s destroys "
         f"causality outright (the inter-grant median is 0.490 s) and scores "
         f"{n['shift'][0.35]} against a measured {meas_total}. The TOTAL is not "
         f"discriminating on sub-report-interval timing, so the shift null is "
         f"gated PER CAPTURE at {SHIFT_GATED:+.1f} s only. ***")
    for s in SHIFT_GATED_CAPTURES:
        _say(f"      {s}: base {n['per_base'][s]} -> "
             f"{n['shift_per'][SHIFT_GATED][s]} at {SHIFT_GATED:+.1f} s, "
             f"against a measured {n['measured'][s]}")
    rot1 = 100.0 * _ratio(n["rotate"][1] - base, base)
    sh = 100.0 * _ratio(n["shift"][-0.35] - base, base)
    _say(f"  MATCHED SCALE, and NO asymmetry is claimed: the smallest geometry "
         f"perturbation (rotate-1) moves the total {rot1:+.1f}% and the smallest "
         f"cadence perturbation (shift -0.35 s) moves it {sh:+.1f}%. The claim "
         f"that this file is 'strong on geometry, weak on cadence' sets "
         f"rotate-by-17 beside shift-by-+0.35 s and is manufactured.")
    return n


def print_band():
    cells = band()
    _say("REALFIX-C5 -- the sensitivity band, window x radius x gate x MATCH-TEST")
    _say(f"  {len(cells)} cells, leads {['%.0f' % L for L in C5_LEADS]}, over "
         f"{len(COUNTERFACTUAL)} counterfactual captures")
    for m in C5_MATCH:
        sub = [c for c in cells if c["cfg"]["match"] is m]
        tot = {L: [c["totals"][L] for c in sub] for L in C5_LEADS}
        _say(f"  match {'ON ' if m else 'OFF'}: " + "  ".join(
            f"L={L:.0f} {min(tot[L])}-{max(tot[L])}" for L in C5_LEADS))
    order = rank_or_refuse(cells)
    if order is None:
        _say("  NO ORDERING IS PRINTED. The lead ranking does not survive the "
             "band -- it inverts on the match-test axis, which is the finding "
             "(round 5 sec. 6.4) and not a limitation. The P2-vs-P3 question needs "
             "the live A/B.")
    else:
        _say(f"  ordering survives the whole band: {order}")
    return cells, order


def print_planecarry(rows=None):
    """REALFIX-F1b: the calibration gate, then the 3-policy x 2-capture table.

    The GATE PRINTS FIRST AND ITS VERDICT IS EXPLICIT, because a counterfactual
    number printed above an unstated calibration is the failure mode this whole
    file was built against.
    """
    rows = field4_census() if rows is None else rows
    names = list(FIELD4_POLICIES)
    _say("REALFIX-F1b -- the FIELD-4 policy pre-screen, offline, against the "
         "vault")
    _say("  METRIC: grants whose field 4 disagrees with the SYNC copy's own "
         "agent+0x80.")
    _say("          That is REALFIX-F1's pre-registered falsifier, and the one "
         "it FAILED.")
    _say("")
    _say("  CALIBRATION GATE -- replay each capture's OWN arm and it must "
         "reproduce the wire")
    ok = True
    for r in rows:
        c = r["calibration"]
        # THE WORD FLOOR IS PART OF THE GATE AND NOT DECORATION. It printed
        # "floor 99%" beside a number nothing compared against it for exactly
        # as long as this function existed in draft -- a bar in a report that
        # no verdict reads is the shape `checks.py`'s whole rule is about.
        ok = (ok and c["own_agrees"] and c["own_full_coverage"]
              and c["own_reproduces_wire"]
              and c["word"]["frac"] >= FIELD4_WORD_AGREEMENT)
        _say(f"    {r['stamp']}  arm {c['own_arm']}")
        _say(f"      anchored replay {c['own_anchored']} of "
             f"{c['own_anchored_scored']} scored   vs pin "
             f"{c['measured_pin']} of {r['grants']}   "
             f"{'PASS' if c['own_agrees'] else 'FAIL'}"
             f"{'' if c['own_full_coverage'] else '  [PARTIAL COVERAGE]'}")
        _say(f"      and the replay reproduces the wire's field 4 on all "
             f"{r['grants']} grants: "
             f"{'YES' if c['own_reproduces_wire'] else 'NO'}")
        _say(f"      nearest-sample pairing gives {c['own_nearest']}, which is "
             f"the published {c['published_nearest']} -- and it UNDERCOUNTS by "
             f"{c['measured_pin'] - c['own_nearest']}: a sample taken after the "
             f"grant reads the plane the grant just wrote")
        a, w = c["arrival"], c["word"]
        if a["n"]:
            _say(f"      ARRIVAL MODEL, zero free parameters: {a['hit']} of "
                 f"{a['n']} client-authored plane writes land on a modelled "
                 f"arrival (|dt| median {a['dt_median']:.3f}s max "
                 f"{a['dt_max']:.3f}s); strictly EARLY in {a['early_n']} of "
                 f"{a['hit']}, at most {a['early_max']:.3f}s")
        else:
            _say("      ARRIVAL MODEL: this capture makes NO client-authored "
                 "plane write -- under --zero-lead field 4 already equals the "
                 "client's plane, so the client never has to correct us and "
                 "never reveals its own opinion. Unfalsifiable here BY "
                 "CONSTRUCTION; the F1 capture is where the model is tested.")
        _say(f"      plane-word model predicts {w['ok']}/{w['n']} samples "
             f"({w['frac'] * 100:.2f}%), floor "
             f"{FIELD4_WORD_AGREEMENT * 100:.0f}%  "
             f"{'PASS' if w['frac'] >= FIELD4_WORD_AGREEMENT else 'FAIL'}")
        _say(f"      pairing window {FIELD4_PAIR_GAP:.2f}s: worst grant-to-"
             f"sample lead {c['pair_lead_max']:.3f}s over a tap whose median "
             f"sample is {c['tap_dt_median']:.3f}s -- NOT BINDING here, so it "
             f"is bracketed rather than assumed")
    _say(f"    GATE: {'PASS' if ok else 'FAIL'}")
    _say("")
    _say("  THE COUNTERFACTUAL -- what each policy WOULD have sent, anchored on "
         "the word movetap read")
    _say(f"    {'policy':<20}" + "".join(f"{r['stamp'][-6:]:>22}" for r in rows))
    for n in names:
        cells = []
        for r in rows:
            a = r["anchored"][n]
            cells.append(f"{a['mismatch']:>7} of {a['scored']:<3} "
                         f"(-{a['skipped']:<3})")
        _say(f"    {n:<20}" + "".join(f"{c:>22}" for c in cells))
    _say("    (-N) = grants NOT scored: the observation is contaminated by the "
         "counterfactual's own divergence, or has no sample before the grant.")
    _say("")
    for r in rows:
        a = r["anchored"]["F1b-arrivalcarry"]
        if not a["rows"]:
            continue
        _say(f"  F1b's RESIDUAL on {r['stamp']} -- "
             f"{a['mismatch']} of {a['scored']}:")
        for row in field4_race(a["rows"], r["policies"]["F1b-arrivalcarry"]):
            _say(f"    ({row['dest'][0]:.0f},{row['dest'][1]:.0f}) w3="
                 f"{row['w3']} field4={row['field4']} vs observed "
                 f"{row['observed']}  sep {row['sep']}  observed "
                 f"{row['lead'] * 1000:.0f} ms before the grant, which landed "
                 f"{row['since_arrival'] * 1000:.0f} ms after a modelled "
                 f"arrival")
    _say("")
    for line in FIELD4_RESIDUAL_NOTE.split(". "):
        if line.strip():
            _say("  !! " + line.strip().rstrip(".") + ".")
    _say("")
    _say("  AND THE CLOSED SIMULATION, printed BELOW the anchored table and "
         "labelled, because for F1b it is a TAUTOLOGY:")
    for n in names:
        cells = [f"{r['policies'][n]['mismatch']:>7} of "
                 f"{r['policies'][n]['n']:<3}      " for r in rows]
        _say(f"    {n:<20}" + "".join(f"{c:>22}" for c in cells))
    _say("    F1b returns 0 here BY CONSTRUCTION: the simulator derives the "
         "copy's plane word from the same arrival model F1b's policy reads, so "
         "the two agree with each other. It is printed only to show that the "
         "other two policies do NOT come out at zero under it -- and that it "
         "UNDER-counts F1's own residual (3 against the wire's 6), which is "
         "why it is not the headline.")
    return rows, ok


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--radius", action="store_true",
                    help="REALFIX-C0: re-derive the match radius and gate-1 cut")
    ap.add_argument("--calibrate", action="store_true",
                    help="REALFIX-C1 and C2 against the vault")
    ap.add_argument("--counterfactual", action="store_true",
                    help="the candidate policies on the zero-grant substrate")
    ap.add_argument("--nulls", action="store_true",
                    help="REALFIX-C4: the nulls, including the one this fails")
    ap.add_argument("--band", action="store_true",
                    help="REALFIX-C5: the sensitivity band and the refusal to rank")
    ap.add_argument("--planecarry", action="store_true",
                    help="REALFIX-F1b: the FIELD-4 policy pre-screen -- three "
                         "policies against the two REALFIX-L3 captures, with "
                         "the calibration gate printed first")
    a = ap.parse_args(argv)
    if not any((a.radius, a.calibrate, a.counterfactual, a.nulls, a.band,
                a.planecarry)):
        a.radius = a.calibrate = a.counterfactual = a.nulls = a.band = True
        a.planecarry = True
    if a.radius:
        print_radius()
        _say("")
    if a.calibrate:
        print_calibration()
        _say("")
    if a.nulls:
        print_nulls()
        _say("")
    if a.counterfactual:
        print_counterfactual()
        _say("")
    if a.band:
        print_band()
        _say("")
    if a.planecarry:
        print_planecarry()
    return 0


if __name__ == "__main__":
    sys.exit(main())
