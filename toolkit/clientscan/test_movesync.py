#!/usr/bin/env python3
"""The separation instrument, its SOURCE, its BAR, and its refusal semantics.

    python toolkit/clientscan/test_movesync.py

WHAT THIS IS REALLY CHECKING. Two instruments in this arc reported the wrong
thing for two runs each, and both failures were quiet.

`warpscan.py` scored a big client step against the points we had GRANTED, and
said "NOT near any grant" for 10 of its 12 detections. That line was the finding
-- the landing point sits on the server-authoritative agent's glide path, not at
any granted endpoint -- and it read as a puzzle instead, because nothing printed
the quantity that would have explained it.

`movetap.py` scored itself against a floor of `seconds * hz * 0.5`, half the
REQUESTED rate, while the reader sustains about 13 Hz against a default request
of 50. So it printed FAIL over the run that overturned this arc's mechanism. A
floor that fires on every healthy run is worse than no floor: it is how a real
FAIL gets waved through.

`movesync.py` is the missing quantity and this file is its guard. Sections 1-3
and 9-10 are the pure logic, sections 11-13 replay the vault, so the suite still
means something on a machine with no captures.

AND THEN MOVESYNC ITSELF WAS THE INSTRUMENT REPORTING THE WRONG THING. The
2026-08-19 corpus pass found four defects in it, every one of which had already
put a wrong number into a document. Sections 4-8 are the guards on the fixes,
and each one is written so it can go red:

  4 pins the BARS as constants, because `JUMP_UNITS = 300` with no time term was
    a number nobody could see was load-bearing until retail scored 6.4/min on it.
  5 is a client WALKING at run speed across report gaps. The legacy bar flags
    every step; the hard bar must flag none. The row count is asserted FIRST --
    a control over zero rows is this arc's own recorded trap, and it already
    passed once in this very file.
  6 plants a 900 u step over 0.13 s and requires exactly one detection, on the
    SPEED arm and then again on the DISTANCE one.
  7 builds a LEGACY-SHAPED capture -- `position_report` rows at the stops only,
    a full `0x003D` stream between them -- and requires `--wire-only` to read
    the spliced stream. On the real `20260811T173940` the wrong source reads 5
    "unexplained jumps" and the right one reads 2, both of them walking.
  8 is the refusal semantics: when a bar refuses, no quotable count from that
    bar may appear above the refusal. The "5 unexplained jumps" hole was minted
    by quoting a number printed above a REFUSING line.

AND THEN THE FIX HAD ITS OWN HOLE. The 2026-08-19 adversarial pass found the new
verdict-bearing bar was DISTANCE-BLIND -- `dt >= 0.05 s` discarded any short
interval whatever it carried, which silently threw away the corpus's three
fastest genuine events, all at ~32 ms. That refusal was anti-correlated with the
mechanism it was built to find: a resync emits a report either side of the snap.
So §6 grew a second arm and lost the dt control that the arm INVALIDATED (it
planted 900 u over 0.01 s and demanded a refusal, which is now a test that the
fix does not work), §12 grew the tautology disclaimer the tool already printed
and the test never asserted, and:

  14 pins the two counts that MOVED -- `20260819T182652` 11 -> 13 and
     `20260819T171153` 19 -> 20 -- because a guard that only asserts the new
     bar equals the new bar cannot go red when the arm is reverted.
  15 pins the count that must NOT move: `20260811T173940` still reads 0 hard.
  16 re-measures the CALIBRATION rather than inheriting it, off the live corpus's
     own c2s stream: 2,789 retail self-reports, 2,747 intervals, ZERO on either
     arm, fastest believable interval 388.80 u/s, and below the dt floor -- the
     only place the distance arm ever fires -- a largest step of 19.15 u. A
     constant justified in a comment is justified nowhere.

AND THEN THE GUARDS ON THE GATEFIRE PROBE WENT INTO A `--selftest` NOBODY RUNS.
`movetap.py` and `movesync.py` grew 130 checks on 2026-08-20 for changes C1-C9,
and put every one of them in a module-level `--selftest`. `run_suite.py`
discovers `test_*.py` FROM DISK; neither module is one. That is the same defect
as a test missing from TESTS.md, and this repo has shipped it three times
(`test_pathmap.py`, `test_skillcast.py`, `test_textrec.py`). So:

  17 wraps movetap's fence sections -- the displacements re-derived from build
     38797's own bytes, and the refusal semantics that keep a failed read from
     minting the `0` that means "the fence is shut".
  18 wraps movetap's C2/C3/C6/C7/C8/C9 sections: episodes, the flip
     denominator, gate 1's ASYNC twin and clamp, the two early-outs, the
     vocabulary.
  19 wraps movesync's C4/C5/C9 sections: the three-way jump tally, the appender
     witness, the two spellings.
  20 asks BOTH MODULES what sections they define and requires every one to be
     wrapped above, so a section added tomorrow goes red here rather than being
     found missing in a week -- the same both-directions rule `test_srclint.py`
     §7 applies to TESTS.md. It also runs each module's whole `--selftest`, so
     the operator's own pre-flight command cannot diverge from the suite.

  Every wrapped section gets TWO checks -- its verdict, and the number of checks
  it EXECUTED against a floor read off a real green run -- because a section
  whose fixtures stopped matching reports `bad = 0` over nothing at all, and the
  verdict cannot tell that from a pass. Every one is then BROKEN on purpose and
  required to go red. That is not ceremony here: §17's first version compared a
  section's `(bad, ran)` tuple against `0`, which cannot be true, and then
  compared the same tuple with `>`, which raised -- so 16 green sections were
  followed by a TypeError and one check that could never pass.
"""
import ast
import contextlib
import io
import json
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import checks     # noqa: E402
import movesync   # noqa: E402
import movetap    # noqa: E402
import vaultpath  # noqa: E402

# MEASURED from a real green run on 2026-08-20: 150 checks with every capture
# present, 100 without (`RURIK_VAULT` pointed at an empty directory, 7 declared
# skips) -- and the floor before that was written down from a count in the
# author's head, which is the same slip test_interact.py records, so this one is
# read off the run every time it moves. Sections 1-10 are pure logic and take no
# fixture; 11-16 replay the vault and declare LEDGER.skip when it lacks them.
# §17-§20 wrap movetap's and movesync's own `_selftest_*` sections and straddle:
# almost all of them drive FAKE memory or synthetic sequences and run anywhere,
# and only `movetap._selftest_fence_bytes` -- which re-derives the AgTrack and
# gate-1 displacements from build 38797's own bytes -- needs the vault's client
# snapshot, so it and its one control skip without it (2 checks). 100 is the
# bare-machine subset and is the floor.
#
# 100 -> 124 on 2026-08-21 with REALFIX-T1/T2/I1, read off two real green runs
# on that date and not predicted: 174 with the vault present, 124 with
# `RURIK_VAULT` pointed at an empty directory (7 declared skips). The 24 are
# §17's wrap + floor + three controls for movetap's new `_selftest_chain` (5)
# and §21's clock-anchor checks (19), all of which are pure logic, synthetic
# files and one in-process `authsrv.Recorder` -- so every one of them runs on a
# bare machine and belongs in the floor.
#
# 124 -> 127 later on 2026-08-21, off two more real green runs: 177 with the
# vault, 127 with `RURIK_VAULT` empty (the same 7 skips). The three are the
# float arm's MEDIAN control -- one 5 s outlier that moves a mean 36 u and a
# median not at all, the estimator distinction having been guarded on the
# truncated side only -- and an AST import guard on movetap.py and movesync.py,
# which `import pefile` walked straight through on this machine.
#
# 127 -> 131 on 2026-08-27, and this one is a CORRECTION rather than a raise:
# 127 had been 4 BELOW the minimum a green run produces since CANCELWALK-R5 and
# REALFIX-I1 landed (2026-08-24), which is the loose-floor failure the rule
# warns about from the other side. Measured on this date at HEAD, before the
# §16 repair below and again after it, both giving the same two numbers: 131
# with `RURIK_VAULT` pointed at an empty directory (the same 7 declared skips)
# and 183 with the vault present. The §16 repair replaces one check with three,
# so it adds a NET TWO to the vaulted run (181 -> 183, both counted) and NONE to
# the bare one -- §16 skips whole when the live corpus is unreachable, which is
# why the empty-vault number is 131 on both sides of the repair.
LEDGER = checks.Ledger("separation: the quantity that actually predicts a warp",
                       floor=131)
check = checks.adopt(LEDGER)

MOVETAP = "movetap-20260819T171436.jsonl"
CAPTURE = "authsrv-20260819T171153-c1.jsonl"
# The DEFAULT build -- recorded before --heading-grant existed, and the
# capture that carries the corpus's biggest warps (3,405 / 3,166 / 2,583 u).
DEFAULT_BUILD_CAPTURE = "authsrv-20260819T145717-c1.jsonl"
# The LEGACY capture: pre-splice-fix, so its `position_report` rows are the
# 0x0047 stop arm alone. This is the file the "5 unexplained jumps" came from.
LEGACY_CAPTURE = "authsrv-20260811T173940-c1.jsonl"
# The two captures that carry the corpus's three ~32 ms genuine events, which
# the old speed-only bar discarded for being short. 182652 holds two of them
# (740.7 u / 0.0318 s at t=13.424 and 582.1 u / 0.0331 s at t=36.849) and
# 171153 the third (617.0 u / 0.0324 s at t=138.687).
SHORT_DT_CAPTURE = "authsrv-20260819T182652-c1.jsonl"

WALL = "2026-08-19T00:00:00Z"


# --------------------------------------------------------------------------
# THE WRAPPER FOR BOTH MODULES' OWN `_selftest_*` SECTIONS (§17-§20).
#
# `movetap.py` and `movesync.py` both grew their instrument on 2026-08-20 and
# both put the guards in a module-level `--selftest`. `run_suite.py` discovers
# `test_*.py` FROM DISK, and neither module is one, so those 130 checks ran
# only when an operator typed the module name. A test nobody runs is not a
# test: `test_pathmap.py`, `test_skillcast.py` and `test_textrec.py` were each
# in the tree and out of the suite for days. Every section of both is wrapped
# and COUNTED below.
#
# TWO checks per section, never one. The verdict alone cannot catch a section
# whose fixtures stopped matching: `_selftest_gate1` with a broken `_gate1_mem`
# would run zero cases, report `bad = 0` and read as a pass -- which is
# `test_codec.py`'s glob matching nothing, one layer up. So the number of
# checks the section EXECUTED is asserted against a floor read off a real green
# run, and never off a guess.
#
# AND THE RETURN SHAPES DO NOT AGREE, which is how the first version of §17
# broke. movetap's sections return `(bad, ran)` or `(bad, ran, skipped)`;
# movesync's return a bare `bad` with the count only in what they printed. §17
# was written when movetap's returned a bare int, and the change to a tuple
# turned `check(nb == 0, ...)` into a check that could never PASS -- `(0, 28)`
# is not `0` -- and then `check(nbad > 0, ...)` into a TypeError that killed
# the whole run at §17 with 16 sections already green behind it. Normalising
# the shape in one place is half the fix; §20's cross-check of the reported
# count against the PRINTED one is the other half, because a wrapper that
# misreads the shape and a section that miscounts are the same defect from two
# sides.
# --------------------------------------------------------------------------
# Measured, per section, from a real green run on 2026-08-20 -- `ran` off the
# section itself, not off a count in anybody's head. `_selftest_fence_bytes`
# is the one that can legitimately not run (no pinned client snapshot in the
# vault); it declares its own size and this file turns that into a LEDGER.skip.
MOVETAP_SECTIONS = (
    # 28 -> 44 on 2026-08-21: REALFIX-I1 added sixteen node-layout
    # displacements, each encoded FROM the constant and matched at its VA in
    # the appender (0x00605840), its allocator (0x00604BB0) and the walker
    # (0x006056A0). This is also the number the section declares when it skips
    # for want of a client snapshot, so it moves in one place.
    # 44 -> 50 later the same day: the recycle test's OPERAND (0x00604BFF --
    # the comment beside it named the block's oldest node and the bytes say
    # its newest), the two SEVER sites and the block span that are the real
    # reason a chain cannot dangle into a recycled block, and the COFF
    # Characteristics word PTR_MAX's ceiling was asserted from in prose.
    ("_selftest_fence_bytes", 50),
    ("_selftest_fence_refuses", 13),
    ("_selftest_fence_verdict", 7),
    ("_selftest_episodes", 7),
    ("_selftest_flip_denominator", 8),
    ("_selftest_gate1", 26),
    ("_selftest_early_outs", 11),
    ("_selftest_naming", 8),
    # 28 -> 44: a mutation lane opened ten holes this section could not see --
    # a short read, the sync copy's plane word against the w word beside it,
    # a legitimate allocation above the 2 GB line, the module-global rebinding
    # the landing commit wrongly credited to section 17 below, the recycle
    # hazard, the future tolerance's real ground, the read budget, and the
    # printer's OUTPUT rather than its call site.
    ("_selftest_chain", 45),
    # CANCELWALK-R5's decode-only field set: five offsets read from distinct
    # non-zero bytes, their placement inside the already-fetched span, the
    # ASYNC copy surfacing its OWN values, a refused twin blanking every async
    # key, and sample() calling the shared decoder.
    ("_selftest_r5", 9),
)
MOVESYNC_SECTIONS = (
    ("_selftest_jump_tally", 14),
    ("_selftest_appender_witness", 19),
    ("_selftest_spellings", 6),
    ("_selftest_print_fence", 11),
)
# (label, reported ran, printed [PASS]/[FAIL] lines) for every wrapped section
# that reports its OWN count, filled by `_wrap` and ruled on once in §20. A
# section whose count had to be taken from its output is not listed, because
# comparing that count against the output it was derived from is a check that
# cannot fail.
SHAPES = []
# (module, section) for every section `_wrap` ACTUALLY invoked this run. §20
# rules on this and not on the table above: a name can sit in a table while its
# call site is commented out, and then the coverage check certifies a section
# nobody ran -- which is the defect this whole block exists about, one level up.
WRAPPED = set()

# The floors above, by (module, section). ONE source: they briefly sat at the
# call sites as well, and two copies of a measured constant is how one of them
# goes stale with nothing noticing. A `_wrap` for a section the table does not
# name raises KeyError here rather than defaulting to something permissive.
_FLOOR = {(movetap.__name__, n): f for n, f in MOVETAP_SECTIONS}
_FLOOR.update({(movesync.__name__, n): f for n, f in MOVESYNC_SECTIONS})


def _run_section(fn):
    """One section, run quietly. -> (bad, ran, skipped, output, self_reported).

    The two conventions are normalised HERE and nowhere else, so a third one
    cannot be half-adopted. `ran` for a section that reports no count is taken
    from what it printed, and `self_reported` says which of the two happened so
    §20 can cross-check only the sections where the two are independent.
    """
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        got = fn()
    out = buf.getvalue()
    printed = out.count("[PASS]") + out.count("[FAIL]")
    if isinstance(got, tuple):
        bad, ran = got[0], got[1]
        skipped = got[2] if len(got) > 2 else 0
        return bad, ran, skipped, out, True
    return got, printed, 0, out, False


def _wrap(mod, name, what, why, skip_why=None):
    """Run one section under this file's ledger. -> its output, or None if skipped.

    Two checks: the section's verdict, and the count it executed against
    `floor`. A section that passes while having judged nothing is the exact
    shape `toolkit/checks.py` exists to refuse, and it is not caught by the
    verdict.
    """
    floor = _FLOOR[(mod.__name__, name)]
    WRAPPED.add((mod.__name__, name))
    bad, ran, skipped, out, reported = _run_section(getattr(mod, name))
    label = f"{mod.__name__}.{name}"
    if skipped:
        LEDGER.skip(label, skip_why or "the section declared a skip")
        return None
    if reported:
        SHAPES.append((label, ran, out.count("[PASS]") + out.count("[FAIL]")))
    check(bad == 0, f"{what} ({ran} check(s) in {label})", why)
    check(ran >= floor,
          f"...and it executed {ran} of a floor of {floor}",
          "the floor is read off a real green run: a section whose fixtures "
          "stop matching reports bad=0 over nothing at all, and the verdict "
          "cannot tell that from a pass")
    return out


def _control(mod, attr, value, section, what, why):
    """Break ONE thing a section is about; require that section to go red.

    Restored in a `finally`, because a control that leaks its mutation turns
    every later check in the run into a measurement of the control.
    """
    old = getattr(mod, attr)
    setattr(mod, attr, value)
    try:
        bad = _run_section(getattr(mod, section))[0]
    finally:
        setattr(mod, attr, old)
    check(bad > 0, f"CONTROL: {what} ({bad} failure(s))", why)


def write_capture(path, rows):
    """One gamesrv-shaped capture on disk. Fixtures are files, not mocks."""
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    return path


def selfreport(t, x, y, stop=False):
    """One decoded c2s self-report, in the shape authsrv logs.

    `values[1]` is the position vec2 for BOTH opcodes -- that is the whole of
    the splice, and it is why reading only one of them is a blind instrument.
    """
    return {"kind": "decoded", "t": t, "wall": WALL,
            "opcode": movesync.OP_CANCEL_REPORT if stop
                      else movesync.OP_SET_HEADING,
            "name": "MOVE_CANCEL_REPORT_POSITION" if stop else "MOVE_SET_HEADING",
            "values": [32829, [x, y], 0] if stop
                      else [32829, [x, y], 0, [0.0, 765.0], 1]}


def position_report(t, x, y):
    """The row a PRE-2026-08-19 authsrv wrote, from the stop arm only."""
    return {"kind": "position_report", "t": t, "wall": WALL,
            "reported": [x, y], "ours": [x, y], "drift": 0.0,
            "accepted": True, "source": None, "plane": 0}


def main():
    print("1. the truncated-clock offset is estimated from BELOW")
    # The capture stamps whole seconds, so every sample reads floor(unix) - t =
    # true - frac. The mean is biased low by half a second, and half a second at
    # 288 u/s is 144 units -- the same size as the separation being measured, so
    # the choice of estimator is load-bearing rather than stylistic.
    true_off = 5000.5
    walls = [int(true_off + t) - t for t in (0.0, 0.2, 0.45, 0.8, 1.3, 1.95)]
    est, spread = movesync.offset_from_stamps(walls)
    check(est <= true_off, "the estimate never exceeds the truth",
          f"{est} vs {true_off} -- an overestimate would shift every pairing "
          f"the wrong way and inflate separation")
    check(true_off - est < 1.0, "and lands within one second of it",
          f"off by {true_off - est:.3f}")
    check(sum(walls) / len(walls) < est,
          "the mean really is lower, so taking the max is not decorative",
          f"mean {sum(walls) / len(walls):.3f} vs max {est:.3f}")
    check(movesync.offset_from_stamps([]) == (None, None),
          "and no stamps yields None rather than a confident zero",
          "a zero offset would silently pair everything against the wrong time")

    print("\n2. a pair that resolves to nothing is DROPPED, not stretched")
    far = movesync.pair([{"t": 900.0, "live": [0.0, 0.0, 0]}],
                        [(0.0, [0.0, 0.0])], 0.0)
    check(far == [],
          f"a report 900 s from any sample yields no pair",
          f"{len(far)} -- vaultpath.require_dir()'s rule: a fixture that "
          f"silently resolves to the wrong thing turns every assertion behind "
          f"it into a no-op")
    near = movesync.pair([{"t": 10.0, "live": [0.0, 0.0, 0]}],
                         [(0.0, [0.0, 0.0])], 10.0)
    check(len(near) == 1, "and an aligned one is kept", f"{len(near)}")

    print("\n3. the scorer tells a resync from a step that is not one")
    # A resync: the client walks away from a stationary authoritative agent and
    # is snapped back onto it.
    S = [{"t": 100.0 + k * 0.05, "live": [0.0, 0.0, 0]} for k in range(12)]
    reps = [(k * 0.05, [k * 60.0, 0.0]) for k in range(11)] + [(0.55, [5.0, 0.0])]
    _seps, jumps = movesync.score(movesync.pair(S, reps, 100.0))
    col = movesync.collapse(jumps)
    check(len(jumps) == 1, "the synthetic resync yields exactly one jump row",
          f"{len(jumps)}")
    check(col is not None and col[2] > 0.9,
          "and separation collapses across it",
          f"{col[0]:.0f} u -> {col[1]:.0f} u" if col else "no rows")

    # THE CONTROL, and it is the one that matters. Both copies leap together:
    # the step is large and the separation across it does NOT change. A scorer
    # that reports a collapse here is reporting its own procedure.
    # WRITTEN VACUOUS THE FIRST TIME -- the synthetic steps were below the
    # threshold, `jumps` came back empty, and `all([])` is True, so the control
    # passed having judged nothing. The row count is asserted FIRST now.
    S2, reps2 = [], []
    for k in range(12):
        leap = 900.0 if k >= 6 else 0.0
        S2.append({"t": 100.0 + k * 0.05, "live": [k * 10.0 + leap, 0.0, 0]})
        reps2.append((k * 0.05, [k * 10.0 + leap + 600.0, 0.0]))
    _s2, j2 = movesync.score(movesync.pair(S2, reps2, 100.0))
    check(len(j2) >= 1,
          "CONTROL: the no-collapse fixture produces a row to judge",
          "zero rows would make the next check vacuous, which is exactly how "
          "this control passed when it was first written")
    # Indexed rather than unpacked: a jump row is (t, step, before, after, dt)
    # since the distance arm needed the dt at the call site.
    check(bool(j2) and all(abs(j[2] - j[3]) < 50 for j in j2),
          "CONTROL: and separation is unchanged across it",
          ", ".join(f"{j[2]:.0f}->{j[3]:.0f}" for j in j2))

    print("\n4. the bars are PINNED, because each one is a claim")
    check(movesync.JUMP_UNITS == 300.0,
          "the legacy bar is still 300 u, so the old counts stay comparable",
          f"{movesync.JUMP_UNITS} -- two documents quote numbers measured on it")
    check(movesync.RUN_SPEED == 288.0,
          "run speed is 288 u/s, the base retail's 0x0027 declares",
          f"{movesync.RUN_SPEED} -- 65 of 153 player-directed sends")
    check(movesync.HARD_JUMP_SPEED == 400.0,
          "the hard bar is 400 u/s, above every speed retail produces",
          f"{movesync.HARD_JUMP_SPEED} -- retail's own reports maxed at 388.8 "
          f"over the 2,665 intervals in the corpus this was calibrated on "
          f"(14 stamps), just over its 383.04 boost base; a bar below that "
          f"would start counting boosted walking. Section 16 re-measures the "
          f"max against WHATEVER the live corpus holds today -- it has since "
          f"grown to 21 stamps and 388.80 has not moved")
    check(movesync.HARD_JUMP_MIN_DT == 0.05,
          "and it refuses a SPEED verdict on intervals shorter than 0.05 s",
          f"{movesync.HARD_JUMP_MIN_DT} -- a displacement over a near-zero dt "
          f"is an arbitrarily large speed, which would make the gate a "
          f"clock-jitter detector")
    check(movesync.HARD_JUMP_UNITS == 520.0,
          "below which the DISTANCE arm decides at 520 u",
          f"{movesync.HARD_JUMP_UNITS} -- retail-calibrated on the 14-stamp "
          f"corpus of 2026-08-19: 0 of its 2,629 intervals inside 2.0 s "
          f"exceeded 520 u (largest 517.87), and below the dt floor -- the "
          f"only place this arm fires -- retail's largest step was 19.15 u "
          f"over 82 intervals. THOSE ARE THE CHOICE-TIME NUMBERS and they are "
          f"frozen on purpose; section 16 re-measures all four against the "
          f"live corpus, which is where a moving one has to show up")
    # THE DECISION RECORD, and deliberately a frozen one: these are the two
    # rows that bracketed 520 the day it was picked. Both are historical facts
    # and neither is free to move. What IS free to move is the live corpus's
    # extremum -- it has already gone 517.87 -> 518.25 on seven new stamps --
    # and that belongs in section 16 against the constant, not here against a
    # second literal. Re-pinning 517.87 to 518.25 would make this check a
    # record of the newest capture instead of the decision.
    check(movesync.HARD_JUMP_UNITS > 517.87 and movesync.HARD_JUMP_UNITS < 525.3,
          "and it was bracketed on BOTH sides by measured data when it was "
          "chosen",
          f"{movesync.HARD_JUMP_UNITS} sits above retail's largest 2 s step AS "
          f"MEASURED THEN (517.87 u; the live corpus now reads 518.25 u, and "
          f"section 16 is what checks it) and below the smallest of the four "
          f"ordinary WALKING rows the wide `dist>=520 & dt<=2.0s` form would "
          f"have swept in (525.3 u at 285.5 u/s, 20260814T090541) -- the "
          f"narrow form escapes that only because it fires below the dt floor, "
          f"where walking cannot reach. That 7.4 u gap is why the wide form "
          f"was rejected; it was never headroom for the narrow one")
    check(abs(movesync.FREE_SILENCE - 300.0 / 288.0) < 1e-9
          and abs(movesync.FREE_SILENCE - 1.0417) < 1e-3,
          "THE HONEST BAR is derived, not chosen: 300/288 = 1.042 s",
          f"{movesync.FREE_SILENCE:.4f} -- above this much silence an ordinary "
          f"walk clears the legacy bar, so the two are not independent numbers")

    print("\n5. a client WALKING across report gaps is not a jump")
    # 288 u/s with a report every 2 s: every step is 576 u, every step clears
    # the legacy bar, and not one of them is anything but walking. This is the
    # contamination -- retail scores 6.4/min on the legacy bar by exactly this
    # mechanism, with ZERO intervals above 400 u/s.
    walk = [(k * 2.0, [k * 2.0 * movesync.RUN_SPEED, 0.0]) for k in range(12)]
    wrows = movesync.steps(walk)
    check(len(wrows) == 11,
          "the walking fixture produces 11 intervals to judge",
          f"{len(wrows)} -- asserted BEFORE the bars, because a control over "
          f"zero rows is how the section above passed while judging nothing")
    wleg = movesync.legacy_steps(wrows)
    check(len(wleg) == 11,
          f"the LEGACY bar flags all {len(wleg)} of them",
          f"{len(wleg)} -- 576 u per step, and the bar has no time term")
    whard = movesync.hard_steps(wrows)
    check(len(whard) == 0,
          "and the HARD bar flags none",
          f"{len(whard)} -- every implied speed is exactly {movesync.RUN_SPEED} "
          f"u/s, which is walking")
    check(movesync.per_minute(len(wleg), walk[-1][0] - walk[0][0]) > 5.7,
          "the legacy bar rates pure walking above the 5.7/min scoreboard bar",
          f"{movesync.per_minute(len(wleg), 22.0):.1f}/min from a client that "
          f"never did anything -- this is what 'worse than shipping nothing' "
          f"was being measured against")
    wden = movesync.denominator(walk)
    check(wden["free"] == 11 and wden["coverage"] == 0.0,
          "and the denominator says why: every interval is free silence",
          f"free {wden['free']}/{wden['intervals']}, coverage "
          f"{100 * wden['coverage']:.0f}%")

    print("\n6. a planted hard jump is caught exactly once, on EITHER arm")
    planted = walk[:6] + [(walk[5][0] + 0.13, [walk[5][1][0] + 900.0, 0.0])]
    prows = movesync.steps(planted)
    check(len(prows) == 6,
          "the planted fixture produces 6 intervals",
          f"{len(prows)} -- five walking, one planted")
    phard = movesync.hard_steps(prows)
    check(len(phard) == 1,
          "the SPEED arm flags the 900 u / 0.13 s step, and only it",
          f"{len(phard)} -- more than one would mean walking is leaking "
          f"through; zero would mean the detector is dead")
    check(phard and abs(phard[0]["dist"] - 900.0) < 1e-6
          and abs(phard[0]["speed"] - 900.0 / 0.13) < 1.0,
          f"and reports its magnitude and speed",
          f"{phard[0]['dist']:.1f} u at {phard[0]['speed']:.0f} u/s"
          if phard else "no row")
    check(phard and abs(movesync.excess(phard[0])
                        - (900.0 - 288.0 * 0.13)) < 1e-6,
          "and its EXCESS OVER BUDGET, which is the number that gets quoted",
          f"{movesync.excess(phard[0]):.1f} u = 900 - 288*0.13. The implied "
          f"velocity is a denominator artifact the event itself created; "
          f"magnitude and excess do not move with the report cadence"
          if phard else "no row")

    # THE POSITIVE FIXTURE FOR THE DISTANCE ARM. Until 2026-08-19 the dt floor
    # discarded every short interval whatever it carried, which threw away the
    # corpus's three fastest genuine events (740.7 u / 0.0318 s, 617.0 u /
    # 0.0324 s, 582.1 u / 0.0331 s -- each pair in SEPARATE TCP frames, so 32 ms
    # is a real client cadence and not decode-loop coalescing). The refusal was
    # ANTI-correlated with the mechanism: a resync emits a report either side of
    # the snap, so real warps preferentially arrive at short dt.
    caught = walk[:6] + [(walk[5][0] + 0.03, [walk[5][1][0] + 700.0, 0.0])]
    crows = movesync.steps(caught)
    check(len(crows) == 6,
          "the short-dt fixture produces 6 intervals",
          f"{len(crows)} -- counted before it is judged, because the whole "
          f"point of this section is a bar that used to judge zero of them")
    chard = movesync.hard_steps(crows)
    check(len(chard) == 1 and chard[0]["dt"] < movesync.HARD_JUMP_MIN_DT,
          "a 700 u / 0.03 s step is CAUGHT by the distance arm",
          f"{len(chard)} -- the speed-only bar read 0 here, and a 700 u step "
          f"needs 2.43 s of walking at 288 u/s")

    # THE dt GATE'S OWN CONTROL, REBUILT. Its old form planted 900 u over 0.01 s
    # and demanded a REFUSAL -- and under the distance arm that row is correctly
    # CAUGHT, so the control had become a test that the fix does not work. What
    # the dt floor is actually for is a SMALL displacement over a near-zero
    # interval, which is clock jitter and not motion; that is what must still be
    # refused, or the fix has re-opened the hole the floor existed to close.
    jitter = movesync.steps(walk[:6] + [(walk[5][0] + 0.01,
                                         [walk[5][1][0] + 25.0, 0.0])])
    check(len(jitter) == 6,
          "the jitter fixture produces 6 intervals",
          f"{len(jitter)} -- asserted first; a control over zero rows is this "
          f"file's own recorded trap")
    check(len(movesync.hard_steps(jitter)) == 0,
          "CONTROL: 25 u over 0.01 s -- an implied 2,500 u/s -- is still "
          "refused",
          f"{len(movesync.hard_steps(jitter))} of {len(jitter)} rows. It "
          f"clears the 400 u/s speed bar four times over and carries 25 u of "
          f"displacement, which no warp is")
    big = movesync.steps(walk[:6] + [(walk[5][0] + 0.01,
                                      [walk[5][1][0] + 900.0, 0.0])])
    check(len(big) == 6 and len(movesync.hard_steps(big)) == 1,
          "while the SAME 0.01 s carrying 900 u is caught -- the arm is a "
          "distance test, not a dt test",
          f"{len(movesync.hard_steps(big))} of {len(big)}. This row is the one "
          f"the old control demanded be REFUSED, which is why that control had "
          f"to be replaced rather than kept")

    # THE BAR IS SPELLED TWICE AND BOTH SPELLINGS MUST CARRY BOTH ARMS.
    # `hard_steps` scores the wire-only path; `score(min_speed=...)` scores the
    # two-sided paired path, and it had the IDENTICAL distance blindness. A fix
    # applied to one spelling of a bar and not the other is how a hole survives
    # being closed, and nothing on the vault side would have caught it: the
    # movetap window that §11 replays happens to exclude the only corpus row
    # that would have shown it.
    S3 = [{"t": 200.0 + k * 0.05, "live": [0.0, 0.0, 0]} for k in range(14)]
    base = [(k * 0.05, [k * 10.0, 0.0]) for k in range(10)]
    warp = base + [(base[-1][0] + 0.03, [base[-1][1][0] + 700.0, 0.0])]
    jitr = base + [(base[-1][0] + 0.03, [base[-1][1][0] + 25.0, 0.0])]
    pw = movesync.pair(S3, warp, 200.0)
    pj = movesync.pair(S3, jitr, 200.0)
    check(len(pw) == 11 and len(pj) == 11,
          f"the paired fixtures resolve to {len(pw)} and {len(pj)} pairs",
          f"{len(pw)}/{len(pj)} -- counted first; `pair` silently drops "
          f"anything outside {movesync.MAX_PAIR_GAP}s, so an unasserted count "
          f"is a control over nothing")
    _sw, jw = movesync.score(pw, min_units=0.0,
                             min_speed=movesync.HARD_JUMP_SPEED)
    _sj, jj = movesync.score(pj, min_units=0.0,
                             min_speed=movesync.HARD_JUMP_SPEED)
    check(len(jw) == 1 and len(jj) == 0,
          "and score()'s own gate catches the 700 u / 0.03 s step while "
          "refusing 25 u over the same interval",
          f"{len(jw)} and {len(jj)} -- if this reads 0 and 0, the distance arm "
          f"reached `hard_steps` and not the paired path")
    check(bool(jw) and abs(jw[0][4] - 0.03) < 1e-9,
          "carrying the dt, so an excess over budget is computable there too",
          f"{jw[0][4] if jw else 'no row'} -- a jump row is "
          f"(t, step, before, after, dt); without the dt the paired printer "
          f"could only quote an implied velocity")

    print("\n7. --wire-only reads the SPLICED stream, not position_report")
    # A legacy-shaped capture: a dense 0x003D walk with 0x0047 stops, and
    # `position_report` rows at the stops ONLY -- which is what authsrv wrote
    # before 2026-08-19. The two sources must disagree, and the tool must take
    # the spliced one.
    with tempfile.TemporaryDirectory() as td:
        rows = []
        for i in range(81):
            t = i * 0.25
            x = t * movesync.RUN_SPEED
            stop = (i % 40 == 0)
            rows.append(selfreport(t, x, 0.0, stop=stop))
            if stop:
                rows.append(position_report(t, x, 0.0))
        cap = write_capture(os.path.join(td, "legacy-shape.jsonl"), rows)
        spliced, _w, src = movesync.load_wire_reports(cap)
        old, _w2 = movesync.load_reports(cap)
        check(len(spliced) == 81 and src["heading"] == 78 and src["stop"] == 3,
              f"the spliced stream carries {len(spliced)} rows "
              f"({src['heading']} x 0x003D + {src['stop']} x 0x0047)",
              f"{len(spliced)} -- the row count comes before the comparison")
        check(len(old) == 3,
              "while `position_report` carries 3 -- the stop arm alone",
              f"{len(old)} -- this is the blindness that read as 5 unexplained "
              f"jumps in 20260811T173940")
        w = movesync.wire_only(cap)
        check(w["reports"] == 81,
              "and --wire-only scores the spliced stream",
              f"{w['reports']} -- if this were 3 the tool would be reading the "
              f"wrong object, which is defect 1")
        check(w["source"]["position_report"] == 3
              and w["source"]["spliced"] == 81,
              "keeping the disagreeing cross-check in its own output",
              f"{w['source']}")
        oldrows = movesync.legacy_steps(movesync.steps(old))
        check(len(movesync.legacy_steps(movesync.steps(spliced))) == 0
              and len(oldrows) == 2,
              "the two sources give DIFFERENT legacy counts: 0 spliced, 2 "
              "stop-arm-only",
              f"{len(movesync.legacy_steps(movesync.steps(spliced)))} vs "
              f"{len(oldrows)} -- same client, same walk, and the source alone "
              f"decides whether it 'jumped'")

        print("\n8. refusal semantics: no quotable count above a refusal")
        # This dense fixture must NOT refuse -- a gate that always fires is not
        # a gate, it is a constant.
        check(w["legacy_refusals"] == [],
              "CONTROL: a dense capture does not trip the legacy refusal",
              f"{w['legacy_refusals']} -- every gap is 0.25 s, so no walk "
              f"clears 300 u inside one and the count is honest")
        # THE SHAPE THAT DEFEATED THE OLD GATE, built on purpose: four dense
        # blocks at 0.25 s separated by 5 s silences. The MEDIAN gap is 0.25 s,
        # comfortably under the old 0.5 s bar, and the client still walks 1,440
        # u inside each silence -- three free "jumps". This is
        # `20260811T173940` in miniature (p50 0.251 s, max 39.1 s), and it is
        # why the refusal had to move off the median.
        sparse_rows, t, x = [], 0.0, 0.0
        for block in range(4):
            for _k in range(10):
                sparse_rows.append(selfreport(t, x, 0.0))
                t += 0.25
                x += 0.25 * movesync.RUN_SPEED
            t += 4.75                     # a 5.0 s gap, minus the 0.25 above
            x += 4.75 * movesync.RUN_SPEED
        scap = write_capture(os.path.join(td, "sparse.jsonl"), sparse_rows)
        sw = movesync.wire_only(scap)
        sden = sw["den"]
        check(len(sparse_rows) == 40 and sden["intervals"] == 39,
              f"the gap-ridden fixture holds {sden['intervals']} intervals",
              f"{sden['intervals']} -- counted before it is judged")
        check(sden["p50"] <= movesync.GOOD_CADENCE and sden["max"] > 4.0,
              f"whose MEDIAN gap ({sden['p50']:.2f}s) passes the old cadence "
              f"gate while its MAX is {sden['max']:.2f}s",
              f"p50 {sden['p50']:.3f}s vs a {movesync.GOOD_CADENCE}s bar -- a "
              f"median cannot see a gap, which is defect 3")
        check(bool(sw["legacy_refusals"]) and len(sw["legacy"]) == 3
              and len(sw["walkable_legacy"]) == 3 and len(sw["hard"]) == 0,
              "and it refuses the legacy bar while the hard bar still answers",
              f"refusals {len(sw['legacy_refusals'])}, legacy "
              f"{len(sw['legacy'])} (all {len(sw['walkable_legacy'])} of them "
              f"walking), hard {len(sw['hard'])} -- silence lowers an implied "
              f"speed, so no gap can mint a hard jump")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            movesync.print_wire_only(scap, sw)
        lines = buf.getvalue().splitlines()
        refusing = [i for i, l in enumerate(lines) if "REFUSING" in l]
        counts = [i for i, l in enumerate(lines) if "step(s) >=" in l]
        check(bool(refusing) and bool(counts) and min(counts) > min(refusing),
              f"every legacy count line sits BELOW the refusal",
              f"refusal at line {refusing}, counts at {counts} -- the '5 "
              f"unexplained jumps' hole was minted by quoting a number printed "
              f"above a refusing line")
        check(all("refused" in lines[i] for i in counts),
              "and each is marked `refused`",
              "; ".join(lines[i].strip() for i in counts))
        # And the whole-run refusal: too few intervals to RATE anything.
        tiny = write_capture(os.path.join(td, "tiny.jsonl"),
                             [selfreport(k * 0.25, k * 72.0, 0.0)
                              for k in range(5)])
        tw = movesync.wire_only(tiny)
        buf2 = io.StringIO()
        with contextlib.redirect_stdout(buf2):
            movesync.print_wire_only(tiny, tw)
        tl = buf2.getvalue().splitlines()
        ri = [i for i, l in enumerate(tl) if "REFUSING EVERY RATE" in l]
        ci = [i for i, l in enumerate(tl) if "refused rate:" in l]
        check(tw["refuse_all"] and bool(ri) and bool(ci) and ci[0] > ri[0],
              f"a {tw['den']['intervals']}-interval capture refuses every "
              f"RATE, and says so before printing one",
              f"refuse_all {tw['refuse_all']}, refusal at {ri}, rate at {ci} "
              f"-- below {movesync.MIN_INTERVALS} intervals a per-minute rate "
              f"is noise wearing a decimal point")

        # A REFUSAL MUST NOT SUPPRESS A COUNT. The floor used to `return`
        # BEFORE the hard section, so a nine-interval capture carrying a
        # 3,000 u impossible step printed a bare tally and nothing else. Only a
        # per-minute number needs intervals; a count and a magnitude need no
        # denominator at all. Measured impact on the corpus today is nil -- 10
        # vault captures sit under the floor and not one carries a hard or a
        # 300 u step -- which is what makes it cheap now and expensive later.
        loud_rows = [selfreport(k * 0.25, k * 72.0, 0.0) for k in range(9)]
        loud_rows.append(selfreport(9 * 0.25, 8 * 72.0 + 3000.0, 0.0))
        loud = write_capture(os.path.join(td, "loud-but-short.jsonl"), loud_rows)
        lw = movesync.wire_only(loud)
        check(lw["den"]["intervals"] == 9
              and lw["den"]["intervals"] < movesync.MIN_INTERVALS,
              f"the under-floor fixture holds {lw['den']['intervals']} "
              f"intervals, below the {movesync.MIN_INTERVALS} floor",
              f"{lw['den']['intervals']} -- counted before it is judged, and "
              f"it must be UNDER the floor or this section proves nothing")
        check(lw["refuse_all"] and len(lw["hard"]) == 1
              and abs(lw["hard"][0]["dist"] - 3000.0) < 1e-6,
              "and carries one 3,000 u impossible step while refusing the rate",
              f"refuse_all {lw['refuse_all']}, hard {len(lw['hard'])}")
        buf3 = io.StringIO()
        with contextlib.redirect_stdout(buf3):
            movesync.print_wire_only(loud, lw)
        ll = buf3.getvalue()
        check("HARD JUMPS  n = 1 of 9" in ll,
              "the refused run still PRINTS the hard count",
              "the floor governs a per-minute number, not the existence of "
              "the event -- it used to `return` above this line")
        check("magnitude" in ll and "3000 u" in ll and "excess over budget" in ll,
              "and its magnitude and excess beside it",
              "a count with no size is not actionable, and the excess is the "
              "cadence-invariant half of the size")
        check("/min" not in ll,
              "while NO per-minute number appears anywhere in that output",
              "that, and only that, is what nine intervals cannot support")

    print("\n9. movetap's floor is calibrated, not aspirational")
    src_mt = open(os.path.join(HERE, "movetap.py"), encoding="utf-8").read()
    check("def calibrate(" in src_mt,
          "movetap measures what the reader can actually do",
          "without a measured capability the floor is a guess about hardware")
    check("int(a.seconds * a.hz * 0.5)" not in src_mt,
          "and does not score itself against the REQUESTED rate",
          "that floor demanded 7,500 samples from a reader that sustains 13 Hz, "
          "and duly failed the run that overturned this arc's mechanism")
    check("except KeyboardInterrupt" in src_mt,
          "and Ctrl+C still prints a summary",
          "the operator stops when the thing they were reproducing has "
          "happened; that used to escape as a traceback with no verdict")

    print("\n10. wire-only geometry: a landing scored against a granted path")
    # A point ON the segment must read perp 0 and a fraction inside [0,1]; a
    # point off to the side must not.
    d, f = movesync.on_segment([0.0, 0.0], [100.0, 0.0], [40.0, 0.0])
    check(abs(d) < 1e-6 and abs(f - 0.4) < 1e-6,
          "a point on the segment reads perp 0 at its own fraction",
          f"perp {d}, frac {f}")
    d, f = movesync.on_segment([0.0, 0.0], [100.0, 0.0], [40.0, 250.0])
    check(abs(d - 250.0) < 1e-6,
          "and a point beside it reads its true offset",
          f"perp {d} -- if this collapsed to 0 the whole test would pass "
          f"for anything")
    d, f = movesync.on_segment([0.0, 0.0], [100.0, 0.0], [-60.0, 0.0])
    check(f < 0,
          "a landing BEHIND the origin reads a negative fraction",
          f"frac {f} -- those rows exist in the corpus and must not be "
          f"counted as on-path")

    print("\n11. replay: the run that overturned the mechanism")
    try:
        mt = os.path.join(vaultpath.vault_path("captures", "movetap"), MOVETAP)
        cap = os.path.join(vaultpath.vault_path("captures", "gamesrv"), CAPTURE)
        have = os.path.exists(mt) and os.path.exists(cap)
    except Exception:
        have = False
    if not have:
        LEDGER.skip("replay",
                    f"this vault has no {MOVETAP} + {CAPTURE}; the logic above "
                    f"still ran")
    else:
        S = movesync.load_movetap(mt)
        reps, walls, _src = movesync.load_wire_reports(cap)
        off, _spread = movesync.offset_from_stamps(walls)
        prs = movesync.pair(S, reps, off)
        check(len(prs) >= 150,
              f"the two captures overlap on {len(prs)} pairs",
              f"{len(prs)} -- fewer than 150 means the windows barely meet and "
              f"nothing below would mean anything")
        seps, jumps = movesync.score(prs)
        col = movesync.collapse(jumps)
        check(len(jumps) >= 10, f"and carry {len(jumps)} resync jumps",
              f"{len(jumps)}")
        # THE SAME ROWS SURVIVE THE HARD BAR, which is what makes this replay
        # still evidence after the bar changed. If the speed gate had thrown
        # half of them away, the 96% collapse would be a statement about a
        # different population than the one the mechanism was established on.
        _sh, hard = movesync.score(prs, min_units=0.0,
                                   min_speed=movesync.HARD_JUMP_SPEED)
        check(len(hard) == len(jumps) and len(hard) > 0,
              f"all {len(hard)} of them clear the HARD bar too",
              f"{len(hard)} hard vs {len(jumps)} legacy -- these are real "
              f"resyncs, not walking across a gap, and the fixed bar keeps "
              f"every one of them")
        # THAT EQUALITY SURVIVES THE DISTANCE ARM BY LUCK, AND THE LUCK IS
        # PINNED HERE SO IT CANNOT DRIFT SILENTLY. The whole capture gains a row
        # under the repaired bar -- 19 -> 20, the 617.0 u / 0.0324 s step at
        # t=138.687 that the old dt floor discarded. It does not disturb the
        # equality above only because the movetap window is [163.361, 220.619]
        # and 138.687 falls OUTSIDE it. That is not soundness; it is where the
        # operator happened to start the reader. If the window ever moves, the
        # legacy count and the hard count stop matching and the check above goes
        # red for a reason that is correct rather than alarming.
        wt = [p[0] for p in prs]
        check(min(wt) > 138.687,
              f"the paired window [{min(wt):.3f}, {max(wt):.3f}] EXCLUDES the "
              f"row the distance arm restores (t=138.687)",
              f"window starts at {min(wt):.3f}. The equality above is luck, "
              f"not soundness, and this check is what says so out loud")
        check(col[2] > 0.85,
              f"separation collapses {100 * col[2]:.0f}% across them "
              f"({col[0]:.0f} u -> {col[1]:.0f} u)",
              f"{100 * col[2]:.1f}% -- measured at 96% on 13 jumps")
        # The shuffle. THIS is what makes the number above a claim rather than a
        # consequence of pairing anything with anything.
        _s3, j3 = movesync.score(movesync.pair(S, reps, off + 7.0))
        col3 = movesync.collapse(j3)
        check(col3 is None or col3[2] < 0.5 * col[2],
              "CONTROL: pairing 7 s out of true does NOT reproduce it",
              f"{100 * col3[2]:.0f}% against {100 * col[2]:.0f}% -- if the "
              f"shuffle collapsed too, the statistic would be measuring the "
              f"procedure" if col3 else "no jumps under the shuffle")
        # And the alignment sweep must PEAK at the timestamp-derived offset. It
        # was not fitted to the data, so this is an independent check that the
        # clocks are lined up rather than a restatement of the headline.
        best, best_d = -1.0, None
        for d in movesync.SWEEP:
            c = movesync.collapse(movesync.score(movesync.pair(S, reps, off + d))[1])
            if c and c[2] > best:
                best, best_d = c[2], d
        check(best_d == 0.0,
              "and the alignment sweep peaks at the offset the stamps gave",
              f"peak at {best_d:+.2f}s -- the offset came from 8,573 timestamps "
              f"and was never fitted to maximise this, so a peak anywhere else "
              f"means the clocks are misaligned")
        check(max(seps) > 400,
              f"the two copies reach {max(seps):.0f} u apart",
              f"{max(seps):.1f} -- the whole point is that they diverge")

    print("\n12. replay: --wire-only on the DEFAULT-build capture")
    try:
        cap = os.path.join(vaultpath.vault_path("captures", "gamesrv"),
                           DEFAULT_BUILD_CAPTURE)
        have = os.path.exists(cap)
    except Exception:
        have = False
    if not have:
        LEDGER.skip("wire-only replay",
                    f"this vault has no {DEFAULT_BUILD_CAPTURE}")
    else:
        w = movesync.wire_only(cap)
        den = w["den"]
        check(w["source"]["spliced"] == w["source"]["position_report"]
              == w["reports"] == 268,
              f"a POST-fix capture's two sources agree exactly ({w['reports']})",
              f"spliced {w['source']['spliced']} vs position_report "
              f"{w['source']['position_report']} -- the splice fix is free on "
              f"current data and load-bearing on old data")
        check(len(w["hard"]) == 7,
              f"{len(w['hard'])} hard jumps -- the verdict-bearing number",
              f"{len(w['hard'])} of {den['intervals']} intervals; measured at "
              f"7, against the 31 the legacy bar reports")
        rate_span = movesync.per_minute(len(w["hard"]), den["span"])
        rate_act = movesync.per_minute(len(w["hard"]), den["active"])
        check(abs(rate_span - 1.31) < 0.05 and abs(rate_act - 5.66) < 0.10,
              f"at {rate_span:.2f}/min of span and {rate_act:.2f}/min of "
              f"actively-reported time",
              f"{rate_span:.2f} / {rate_act:.2f} -- BOTH denominators are "
              f"printed because 77% of this capture's span carries no reports, "
              f"and a rate is a count over a NAMED denominator or it is not a "
              f"rate")
        mag = movesync.magnitude(w["hard"])
        check(mag[1] > 3000,
              f"magnitude p50 {mag[0]:.0f} u, max {mag[1]:.0f} u",
              f"{mag[1]:.0f} -- the arc shipped a fix that bounded SIZE while "
              f"the harm arrived as FREQUENCY, so both are stated")
        check(bool(w["legacy_refusals"]) and len(w["legacy"]) == 31
              and len(w["walkable_legacy"]) == 23,
              f"the legacy bar is REFUSED here: {len(w['legacy'])} steps >= "
              f"300 u, {len(w['walkable_legacy'])} of them at <= 288 u/s",
              f"{den['free']} of {den['intervals']} intervals exceed "
              f"{movesync.FREE_SILENCE:.3f}s, and the old cadence gate passed "
              f"this capture on a p50 of {den['p50']:.3f}s")
        # THE SPLIT MUST ADD UP. "of which 23 are walking" left 8 unnamed, and
        # a reader completes an unfinished partition with the other category --
        # so the 31 reads as 23 walking and 8 warps when it is 23 + 7 + one row
        # at 360.3 u/s that is neither.
        check(len(w["walkable_legacy"]) + len(w["legacy_hard"])
              + len(w["legacy_between"]) == len(w["legacy"]) == 31,
              f"and the split is EXHAUSTIVE: 31 = "
              f"{len(w['walkable_legacy'])} walking + {len(w['legacy_hard'])} "
              f"hard + {len(w['legacy_between'])} neither",
              f"{len(w['walkable_legacy'])}+{len(w['legacy_hard'])}+"
              f"{len(w['legacy_between'])} against {len(w['legacy'])}")
        check(len(w["legacy_between"]) == 1
              and abs(w["legacy_between"][0]["speed"] - 360.3) < 0.1,
              f"the leftover row is a single step at "
              f"{w['legacy_between'][0]['speed']:.1f} u/s",
              f"faster than a walk and slower than the hard bar; it is neither "
              f"and the output now says so instead of leaving it to arithmetic")

        # THE ACTIVE-TIME RATE IS DIVIDED BY A NUMBER THE LEGACY CONSTANT
        # CHOSE. `active` is the sum of gaps <= FREE_SILENCE = 300/288, from the
        # bar this file calls never-a-verdict. That is load-bearing, not
        # incidental, so the threshold is printed beside the rate.
        gaps = den["gaps"]
        r_short = movesync.per_minute(len(w["hard"]),
                                      movesync.active_time(gaps, 0.3))
        r_long = movesync.per_minute(len(w["hard"]),
                                     movesync.active_time(gaps, 5.0))
        check(abs(r_short - 14.21) < 0.05 and abs(r_long - 3.40) < 0.05,
              f"and the SAME 7 jumps rate {r_short:.2f}/min at a 0.30s "
              f"threshold and {r_long:.2f}/min at 5.00s",
              f"{r_short:.2f} vs {rate_act:.2f} vs {r_long:.2f} -- a 4.2x "
              f"spread with the numerator untouched, which is why the "
              f"threshold is never omitted")
        check(den["active_threshold"] == movesync.FREE_SILENCE,
              "the denominator NAMES that threshold rather than burying it",
              f"{den['active_threshold']:.4f}s -- it is FREE_SILENCE, and a "
              f"rate is a count over a NAMED denominator or it is not a rate")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            movesync.print_wire_only(cap, w)
        out = buf.getvalue()
        check("1.042s" in out and "0.300s -> 14.21/min" in out
              and "5.000s -> 3.40/min" in out,
              "and the real stdout carries the threshold and its sweep",
              f"a quotable 5.66/min with no threshold beside it is the defect")
        # AND THE SPLIT MUST BE EXHAUSTIVE IN THE OUTPUT, not merely in the
        # dict. The dict checks above pass against a printer that still says
        # "of which 23 are walking" and leaves 8 to the reader's arithmetic --
        # which was the actual defect, since nobody reads the dict.
        check("= 23 walking (<= 288 u/s) + 7 clearing the HARD bar + 1 neither"
              in out,
              "and the printed legacy line names all THREE parts",
              f"the number that travelled was the printed one; asserting only "
              f"the dict would leave the wording free to keep the remainder "
              f"unnamed")
        # The same rule for the two lines that keep 23,279 u/s from travelling
        # as a headline: the re-review deleted each and this file stayed green,
        # which made both of them prose, not properties.
        check("arms: 7 by SPEED (> 400 u/s at dt >= 0.05s), "
              "0 by DISTANCE (>= 520 u below that dt)" in out,
              "the printed arms line splits the verdict by which arm fired",
              f"a hard count whose arms are not printed is one bar again, and "
              f"the reader cannot tell a speed event from a sub-floor jump")
        check("THE GATE'S OWN INPUT, not a headline" in out,
              "and the implied-speed demotion label is printed, not implied",
              f"this label is the mechanism by which an implied velocity over "
              f"a window the event created does not travel into documents")
        # 2 of the 7 hard intervals are LONGER than that threshold, i.e. they
        # occurred inside time the `active` denominator EXCLUDES. The rate's
        # numerator counts events its own denominator does not contain.
        check(len(w["hard_outside_active"]) == 2,
              f"{len(w['hard_outside_active'])} of {len(w['hard'])} hard "
              f"intervals are themselves longer than the active threshold",
              f"{[round(r['dt'], 3) for r in w['hard_outside_active']]}s -- "
              f"they happened in excluded time, and the output reconciles it "
              f"rather than letting the rate imply otherwise")
        check("RECONCILE:" in out,
              "and the output says so",
              f"an unreconciled numerator/denominator mismatch is a number "
              f"that reads as measured when it is not")
        # PLANE, carried through from `values[2]` -- annotation, not exclusion.
        check(w["hard_plane_flips"] == 1,
              f"{w['hard_plane_flips']} of {len(w['hard'])} hard rows straddle "
              f"a PLANE flip",
              f"planes 0/18/19 share the x/y frame here, so a flip does not "
              f"make a displacement fictional; warpscan kept this field and "
              f"this file used to drop it")
        check(any(r["plane"] is not None for r in w["steps"]),
              "because load_wire_reports carries the plane at all",
              "values[2] used to be discarded at the reader, so no downstream "
              "check could have asked")
        onp = movesync.on_path(w["hard_scored"])
        con = movesync.on_path(w["hard_control"])
        check(len(w["hard_scored"]) == len(w["hard"]) and onp > con,
              f"{onp} of {len(w['hard_scored'])} hard landings sit on the "
              f"granted path against {con} of {len(w['hard_control'])} on an "
              f"unrelated one",
              f"{onp} vs {con} -- if an unrelated grant scored as well, the "
              f"map's geometry would be doing the work")
        # AND THAT 4-OF-7 IS TAUTOLOGY-CONTAMINATED, which the tool prints and
        # this test used to assert nothing about. In 5 of the 7 rows the
        # grant-time report IS the pre-jump record, so the landing sits on its
        # own segment BY CONSTRUCTION and reads on-path whatever the client did.
        # The honest n is 2. Pinning the headline without pinning the
        # disclaimer is how the contaminated number travels into a document
        # alone.
        check(w["hard_degenerate"] == 5,
              f"but {w['hard_degenerate']} of {len(w['hard_scored'])} are "
              f"DEGENERATE -- origin == pre-jump record",
              f"{w['hard_degenerate']} -- those rows are on their own segment "
              f"by construction; the first version of this analysis read their "
              f"tautological 0.0 as a REFUTATION")
        clean = [r for r in w["hard_scored"] if not r["degenerate"]]
        check(len(clean) == 2 and movesync.on_path(clean) == 2,
              f"leaving a non-degenerate n of {len(clean)}, on-path "
              f"{movesync.on_path(clean)}/{len(clean)}",
              f"{movesync.on_path(clean)} of {len(clean)} -- this is the whole "
              f"of the non-tautological evidence on this capture, and it must "
              f"be quoted beside the 4/7 rather than instead of it")
        perp = sorted(r["perp"] for r in w["hard_scored"])
        cperp = sorted(r["perp"] for r in w["hard_control"])
        p50, cp50 = perp[len(perp) // 2], cperp[len(cperp) // 2]
        # A RATIO NEEDS A FLOOR ON ITS DENOMINATOR. `cperp > 5 * perp` passes
        # trivially on a perp of 0.0 -- which is exactly what a fully degenerate
        # capture produces -- so the ratio would certify a tautology. Require
        # the denominator to be a real measurement first.
        check(p50 > 1.0,
              f"the scored perpendicular p50 is a real measurement "
              f"({p50:.1f} u), not a degenerate zero",
              f"{p50:.4f} -- on a perp of 0 the ratio below passes for any "
              f"control at all, including one that also reads 0")
        check(cp50 > 5 * p50 and cp50 > 500.0,
              "and the control's perpendicular offset is far larger, in "
              "absolute units as well as in ratio",
              f"{cp50:.1f} u vs {p50:.1f} u -- measured at 1582.2 against 78.3 "
              f"on the hard population")

    print("\n13. replay: the capture that minted '5 unexplained jumps'")
    try:
        cap = os.path.join(vaultpath.vault_path("captures", "gamesrv"),
                           LEGACY_CAPTURE)
        have = os.path.exists(cap)
    except Exception:
        have = False
    if not have:
        LEDGER.skip("legacy-source replay",
                    f"this vault has no {LEGACY_CAPTURE}")
    else:
        w = movesync.wire_only(cap)
        old, _walls = movesync.load_reports(cap)
        check(w["source"]["spliced"] == 158
              and w["source"]["position_report"] == 28,
              f"the spliced stream holds {w['source']['spliced']} positions "
              f"where `position_report` holds "
              f"{w['source']['position_report']}",
              f"130 of them were invisible -- the client's whole walk between "
              f"stops")
        oldleg = movesync.legacy_steps(movesync.steps(old))
        check(len(oldleg) == 5 and len(w["legacy"]) == 2,
              f"the wrong source reads {len(oldleg)} legacy jumps and the "
              f"right one reads {len(w['legacy'])}",
              f"{len(oldleg)} vs {len(w['legacy'])} -- the 5 are the hole this "
              f"round is closing, and both survivors are walking")
        check(len(w["hard"]) == 0 and len(w["walkable_legacy"]) == 2,
              "and ZERO clear the hard bar: the client walked the whole way",
              f"hard {len(w['hard'])}, walkable {len(w['walkable_legacy'])} of "
              f"{len(w['legacy'])} -- 74.4 / 196.5 / 10.0 / 122.3 / 243.3 u/s "
              f"on the original five, none above the 288 u/s run speed")

    print("\n14. replay: the three events the dt floor used to discard")
    # THE CORPUS PIN FOR THE DISTANCE ARM, stated as counts that MOVED. A guard
    # that only asserts the new bar's output equals the new bar's output cannot
    # go red when the arm is reverted; these two numbers can, because each is
    # one higher than what the speed-only bar reads on the same bytes.
    try:
        cap2 = os.path.join(vaultpath.vault_path("captures", "gamesrv"),
                            SHORT_DT_CAPTURE)
        cap3 = os.path.join(vaultpath.vault_path("captures", "gamesrv"),
                            CAPTURE)
        have = os.path.exists(cap2) and os.path.exists(cap3)
    except Exception:
        have = False
    if not have:
        LEDGER.skip("distance-arm replay",
                    f"this vault has no {SHORT_DT_CAPTURE} + {CAPTURE}")
    else:
        w2 = movesync.wire_only(cap2)
        w3 = movesync.wire_only(cap3)
        # The speed-only bar, reconstructed here rather than trusted from
        # memory: it is what this file measured before the arm existed.
        def speed_only(rows):
            return [r for r in rows
                    if r["dt"] >= movesync.HARD_JUMP_MIN_DT
                    and r["speed"] > movesync.HARD_JUMP_SPEED]

        old2 = speed_only(w2["steps"])
        old3 = speed_only(w3["steps"])
        check(len(w2["steps"]) == 197 and len(w3["steps"]) == 468,
              f"the two captures hold {len(w2['steps'])} and "
              f"{len(w3['steps'])} intervals",
              "counted before they are judged")
        check(len(w2["hard"]) == 13 and len(old2) == 11,
              f"{SHORT_DT_CAPTURE[8:22]} reads {len(w2['hard'])} hard rows, "
              f"where the speed-only bar read {len(old2)}",
              f"{len(w2['hard'])} vs {len(old2)} -- the two restored rows are "
              f"740.7 u / 0.0318 s and 582.1 u / 0.0331 s, each pair in "
              f"SEPARATE TCP frames (c2s seq 465->466 and 190->191), so 32 ms "
              f"is a real client cadence and not decode-loop coalescing")
        check(len(w3["hard"]) == 20 and len(old3) == 19,
              f"and {CAPTURE[8:22]} reads {len(w3['hard'])} where it read "
              f"{len(old3)}",
              f"{len(w3['hard'])} vs {len(old3)} -- the restored row is "
              f"617.0 u / 0.0324 s at t=138.687 (c2s seq 50->51)")
        by_dist = w2["hard_by_distance"]
        check(len(by_dist) == 2
              and all(r["dt"] < movesync.HARD_JUMP_MIN_DT for r in by_dist)
              and all(r["dist"] >= movesync.HARD_JUMP_UNITS for r in by_dist),
              f"both restored rows come in on the DISTANCE arm, below the dt "
              f"floor",
              ", ".join(f"{r['dist']:.1f} u / {r['dt']:.4f} s"
                        for r in by_dist))
        # AND THE EXCESS, not the implied velocity, is what those rows are
        # worth. 740.7 u needs 2.57 s of walking at 288 u/s; the 23,279 u/s the
        # ratio produces is an artifact of the 32 ms window the snap created.
        # `if by_dist else None` rather than a bare max(): with the arm reverted
        # this list is empty, and a ValueError out of a guard is a red run that
        # stops the remaining sections from executing. A guard should FAIL, not
        # crash -- checks.py's whole subject is runs that stop measuring.
        top = max(by_dist, key=lambda r: r["dist"]) if by_dist else None
        check(top is not None and abs(top["dist"] - 740.7) < 0.1
              and abs(movesync.excess(top) - (top["dist"] - 288.0 * top["dt"]))
              < 1e-9 and movesync.excess(top) > 730.0,
              f"the largest carries {top['dist']:.1f} u and an excess over "
              f"budget of {movesync.excess(top):.1f} u"
              if top else "no distance-arm row to measure",
              f"implied {top['speed']:.0f} u/s, which is the gate's input and "
              f"not the finding: 740.7 u is 2.57 s of walking at 288 u/s, and "
              f"the excess does not move with the report cadence"
              if top else "the arm found nothing on a capture that holds two")
        # THE WIDE FORM IS THE ONE THAT WOULD HAVE BEEN CONTAMINATED, and this
        # is the control that says the narrow one was not chosen by taste.
        wide = [r for r in w2["steps"]
                if r["dist"] >= movesync.HARD_JUMP_UNITS and r["dt"] <= 2.0]
        narrow = [r for r in w2["steps"]
                  if r["dist"] >= movesync.HARD_JUMP_UNITS
                  and r["dt"] < movesync.HARD_JUMP_MIN_DT]
        check(len(narrow) == 2 and len(wide) >= len(narrow),
              f"CONTROL: on this capture the wide `dt <= 2.0s` form matches "
              f"{len(wide)} rows against the narrow form's {len(narrow)}",
              f"corpus-wide the wide form adds four ORDINARY WALKING rows at "
              f"284-286 u/s across ~1.85 s gaps (20260818T103840 538.6 u, "
              f"20260819T150522 533.6 u, 20260816T131839 528.5 u, "
              f"20260814T090541 525.3 u) and the narrow form adds exactly the "
              f"three genuine ones")
        check(bool(narrow)
              and all(r["speed"] > movesync.HARD_JUMP_SPEED for r in narrow),
              "and every narrow-form row would clear the speed bar too, if a "
              "speed at 32 ms were a measurement",
              ", ".join(f"{r['speed']:.0f} u/s" for r in narrow)
              or "no narrow-form row -- `all([])` is True, so the row count "
                 "carries this check")

    print("\n15. the walked-the-whole-way baseline is UNDISTURBED by the arm")
    # This is OUR capture, not retail -- the file that read 5 unexplained jumps
    # through the wrong source and reads 0 hard through the right one. A
    # distance arm that disturbed it would be counting walking again, which is
    # the failure mode the whole 2026-08-19 pass exists to prevent.
    try:
        cap4 = os.path.join(vaultpath.vault_path("captures", "gamesrv"),
                            LEGACY_CAPTURE)
        have = os.path.exists(cap4)
    except Exception:
        have = False
    if not have:
        LEDGER.skip("baseline replay", f"this vault has no {LEGACY_CAPTURE}")
    else:
        w4 = movesync.wire_only(cap4)
        check(len(w4["steps"]) == 157 and len(w4["hard"]) == 0,
              f"{LEGACY_CAPTURE[8:22]} still reads {len(w4['hard'])} hard of "
              f"{len(w4['steps'])} intervals under the REPAIRED bar",
              f"{len(w4['hard'])} -- the mandate for this round names 0 of 157 "
              f"as the number that must not move")
        short = [r for r in w4["steps"]
                 if r["dt"] < movesync.HARD_JUMP_MIN_DT]
        check(short and all(r["dist"] < movesync.HARD_JUMP_UNITS
                            for r in short),
              f"and its {len(short)} sub-{movesync.HARD_JUMP_MIN_DT}s "
              f"interval(s) carry nothing near {movesync.HARD_JUMP_UNITS:.0f} u",
              f"max {max([r['dist'] for r in short], default=0.0):.1f} u -- "
              f"the row count is asserted with the bound, because 'all of zero "
              f"rows are small' is this file's own recorded trap")

    print("\n16. RETAIL, re-measured: zero on BOTH arms")
    # THE CALIBRATION ITSELF, and it is a claim about ArenaNet's client rather
    # than about ours. 520 u is only a bar because retail never clears it, and a
    # constant justified in a comment is justified nowhere. Read from the LIVE
    # corpus's own c2s stream (`0x003D` + `0x0047`, per connection, one clock)
    # so the arm is checked against the thing it was calibrated on and not
    # against a number copied out of FINDINGS.md.
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(HERE), "authsrv"))
        import cmsgstream  # noqa: E402
        live = vaultpath.vault_path("captures", "live")
        stamps = sorted(os.listdir(live))
    except Exception as exc:
        cmsgstream, stamps = None, []
        LEDGER.skip("retail calibration",
                    f"the live corpus is not reachable here ({exc})")
    if cmsgstream is not None:
        rows, reports = [], 0
        for st in stamps:
            try:
                msgs = cmsgstream.timed(st, "c2s", "game")
            except Exception:
                continue          # a stamp with no game wire is not a failure
            byconn = {}
            for t, conn, op, vals in msgs:
                if op not in (movesync.OP_SET_HEADING,
                              movesync.OP_CANCEL_REPORT):
                    continue
                if not isinstance(vals, (list, tuple)) or len(vals) < 2:
                    continue
                p = vals[1]
                if not isinstance(p, (list, tuple)) or len(p) < 2:
                    continue
                byconn.setdefault(conn, []).append(
                    (t, [float(p[0]), float(p[1])]))
            for conn in byconn:
                # PER CONNECTION. Concatenating two connections would invent an
                # interval between the last report of one and the first of the
                # next, which is a displacement across a map load.
                byconn[conn].sort(key=lambda z: z[0])
                reports += len(byconn[conn])
                rows.extend(movesync.steps(byconn[conn]))
        check(reports > 2000 and len(rows) > 2000,
              f"the live corpus yields {reports} retail self-reports over "
              f"{len(rows)} intervals",
              f"{reports}/{len(rows)} -- asserted FIRST: a calibration check "
              f"over an empty corpus certifies the constant while measuring "
              f"nothing, which is precisely the shape this suite exists to "
              f"catch")
        by_speed = [r for r in rows
                    if r["dt"] >= movesync.HARD_JUMP_MIN_DT
                    and r["speed"] > movesync.HARD_JUMP_SPEED]
        by_dist = [r for r in rows
                   if r["dt"] < movesync.HARD_JUMP_MIN_DT
                   and r["dist"] >= movesync.HARD_JUMP_UNITS]
        check(len(by_speed) == 0 and len(by_dist) == 0,
              f"and ZERO of them clear either arm ({len(by_speed)} by speed, "
              f"{len(by_dist)} by distance)",
              f"a single retail row on either arm would mean the bar has "
              f"started counting the game, which is what killed the 300 u one")
        slow = [r for r in rows if r["dt"] >= movesync.HARD_JUMP_MIN_DT]
        top_v = max((r["speed"] for r in slow), default=0.0)
        check(388.0 < top_v < movesync.HARD_JUMP_SPEED,
              f"retail's fastest believable interval is {top_v:.2f} u/s",
              f"{top_v:.2f} -- just over the 383.04 u/s boost base its own "
              f"wire declares, and {movesync.HARD_JUMP_SPEED - top_v:.1f} u/s "
              f"below the speed arm")
        short = [r for r in rows if r["dt"] < movesync.HARD_JUMP_MIN_DT]
        top_d = max((r["dist"] for r in short), default=0.0)
        check(len(short) > 20 and top_d < 50.0,
              f"and BELOW the dt floor -- the only place the distance arm ever "
              f"fires -- its largest step is {top_d:.2f} u over {len(short)} "
              f"interval(s)",
              f"{top_d:.2f} u against a {movesync.HARD_JUMP_UNITS:.0f} u arm: "
              f"{movesync.HARD_JUMP_UNITS / max(top_d, 1e-9):.0f}x of headroom, "
              f"so the arm is not scraping past retail, it is nowhere near it")
        # THE 2.0 s WINDOW -- the REJECTED wide form's witness, not the arm's.
        # This used to read `abs(top2["dist"] - 517.87) < 0.05`, and on
        # 2026-08-27 that went RED at 518.25 u on a corpus that had GROWN from
        # 14 stamps to 21. Re-measured as of the pin (stamps < 20260820) the
        # scanner still reproduces 517.87 u / 2,629 intervals / 388.80 u/s /
        # 82 sub-floor rows at 19.15 u -- every frozen literal in section 4, to
        # the decimal -- so nothing in the scorer moved and nothing in retail
        # got faster: the seven new stamps top out at 385.72 u/s, BELOW the old
        # corpus's 388.80. What grew was the sample. 518.25 u / 1.352 s /
        # 383.21 u/s is one more draw from the same ~1.35 s boost-cadence
        # family that produced 517.87, and an equality against the extremum of
        # a growing corpus is a pin on the SIZE OF THE VAULT.
        #
        # The durable form is the RELATION this check always claimed to be:
        # 520 measured against the corpus's own largest 2 s step, live. That
        # can still go red -- and should, because a step past 520 would mean
        # the constant had lost the property it was chosen for.
        in2 = [r for r in rows if r["dt"] <= 2.0]
        top2 = max(in2, key=lambda r: r["dist"]) if in2 else None
        check(len(in2) > 2000 and top2 is not None,
              f"{len(in2)} of those intervals fall inside 2.0 s",
              f"asserted BEFORE the extremum: `max(..., default=0)` over an "
              f"empty window returns a number that clears a 520 u bar for free, "
              f"which is this section's own vacuity trap one line further on")
        check(top2 is not None and top2["dist"] < movesync.HARD_JUMP_UNITS,
              f"and their largest step is {top2['dist']:.2f} u / "
              f"{top2['dt']:.3f} s = {top2['speed']:.1f} u/s, still under the "
              f"{movesync.HARD_JUMP_UNITS:.0f} u bar it was chosen to clear "
              f"(by {movesync.HARD_JUMP_UNITS - top2['dist']:.2f} u)"
              if top2 else "no retail interval inside 2.0 s",
              f"THE CONSTANT AGAINST THE WIRE, re-measured every run rather "
              f"than quoted from studies/movement/FINDINGS.md. NOTE the "
              f"headroom is small and NOT physically bounded -- at retail's own "
              f"top speed a 2.0 s gap reaches {top_v * 2.0:.0f} u -- so this "
              f"can go red on a long enough report gap. That would NOT be a "
              f"live defect: the distance arm fires only below the "
              f"{movesync.HARD_JUMP_MIN_DT} s floor, where the check above "
              f"measures {top_d:.2f} u against 520. It would mean the DECISION "
              f"RECORD in section 4 had expired, and section 4 says so")
        # NOT A LONE SPIKE -- and this check exists to DISAMBIGUATE the one
        # above, not to fire on its own. Today no lone spike can redden this
        # without also clearing 520, so read the PAIR of verdicts:
        #
        #   relation RED + shoulder RED   -> one row stands alone above the
        #                                    walking cloud. A MOVEMENT FINDING;
        #                                    it belongs to REALFIX, not here.
        #   relation RED + shoulder GREEN -> the cloud itself drifted up. The
        #                                    decision record in section 4 has
        #                                    expired; no jump happened.
        #
        # Both were demonstrated on 2026-08-27 by injection: a single
        # 600 u / 1.6 s row at 375 u/s (deliberately under the speed arm, so
        # this window is the only thing that can see it) reddens both; 40 rows
        # at ~524 u / 1.80 s at ordinary walking speed redden only the first.
        # The equality this replaced pinned WHAT the extremum was and could
        # never tell those two apart -- which is exactly the question that had
        # to be answered before touching it.
        near = [r for r in in2
                if top2 is not None and r["dist"] >= top2["dist"] - 5.0]
        check(top2 is not None and len(near) >= 5,
              f"and it is the tail of a crowded shoulder, not an outlier: "
              f"{len(near)} interval(s) sit within 5 u of it",
              f"corpus growth adds neighbours; a discontinuity arrives alone. "
              f"Read this verdict TOGETHER with the one above -- the pair is "
              f"what separates a movement regression from an expired constant")

    # ---------------------------------------------------------------------
    print("\n17. the AgTrack fence: movetap's selftest 5-7, in the SUITE")
    # movetap has no test file of its own -- §9 above reads its SOURCE, which
    # cannot catch a wrong NUMBER. The fence constants added on 2026-08-20 are
    # displacements into a live process: reading the wrong dword there does not
    # error, it returns 0, and 0 is the value that means "the fence is shut".
    # So the checks that re-derive those constants from the pinned image, and
    # the ones that prove a failed read cannot mint that 0, are run HERE rather
    # than being left in an operator-only `--selftest` nothing in the suite
    # invokes. `movetap.py` imports `keytap`, which is pure ctypes and loads on
    # any Windows box, so this costs no dependency.
    out_b = _wrap(movetap, "_selftest_fence_bytes",
                  "every fence displacement re-derives from build 38797's own "
                  "bytes",
                  "each expected encoding is BUILT FROM the module constant, "
                  "so a wrong constant produces bytes that are not at that VA "
                  "-- comparing a literal against a copy of itself would pass "
                  "forever",
                  skip_why="this machine has no pinned client snapshot in the "
                           "vault")
    if out_b is not None:
        # CONTROL: the derivation must actually bite. Move one constant by one
        # dword and the same section has to go red, or it is decoration.
        _control(movetap, "T_STATE_ARRAY", movetap.T_STATE_ARRAY + 4,
                 "_selftest_fence_bytes",
                 "a one-dword slip in T_STATE_ARRAY turns it red",
                 "a check that cannot fail is not a check, and this one guards "
                 "a number whose wrong value reads as a finding")

    _wrap(movetap, "_selftest_fence_refuses",
          "every way of failing to read the fence lands on \"unread:*\"",
          "0 is a REAL answer here -- it means the fence is shut and the snap "
          "test never runs -- so a failed read that returned 0, None or False "
          "would be indistinguishable from the finding")

    orig = movetap._fence_blank
    movetap._fence_blank = lambda why: dict(
        orig(why), fence_state="shut", gate_reach=movetap.REACH_FENCED[1],
        fence_raw=0)
    nlie = _run_section(movetap._selftest_fence_refuses)[0]
    movetap._fence_blank = orig
    check(nlie > 0,
          f"CONTROL: a failure path rewritten to answer \"shut\" with a raw 0 "
          f"is caught ({nlie} failure(s))",
          "this is the exact defect the sentinel design exists to prevent, so "
          "the check for it must be shown to fire")

    orig_f = movetap.agtrack_fence
    movetap.agtrack_fence = lambda read, agbase, aid, blk: orig(  # only refuses
        "stub")
    nstub = _run_section(movetap._selftest_fence_refuses)[0]
    movetap.agtrack_fence = orig_f
    check(nstub > 0,
          f"and CONTROL the other way: a stub that ONLY ever refuses is caught "
          f"too ({nstub} failure(s))",
          "otherwise the refusal checks above would be satisfied by a reader "
          "that never populates the field at all")

    _wrap(movetap, "_selftest_fence_verdict",
          "the run-level verdict refuses a bad denominator and an aliased "
          "fence",
          "a fence flipping near the reader's own rate cannot be polled, and "
          "that refusal is what decides between this route and the hook")

    # ---------------------------------------------------------------------
    print("\n18. movetap's C2/C3/C6/C7/C8/C9 sections, in the SUITE")
    # The five sections `movetap.py` grew for the gatefire probe. Each is
    # wrapped, counted against its own measured floor, and then BROKEN on
    # purpose: a wrapper that calls a section and ignores what it returns is
    # indistinguishable from one that guards it, and that is precisely what
    # §17 was for a day (`(0, 28) == 0` is False, so its first check could not
    # pass and its second raised).
    _wrap(movetap, "_selftest_episodes",
          "C2: the effective n is EPISODES, and a majority-censored median is "
          "refused",
          "a run length is what the fence question turns on -- 564 samples "
          "across 3 transitions is an n of about 4, and this file used to "
          "print the 564")
    _control(movetap, "episodes", lambda seq: [], "_selftest_episodes",
             "an `episodes` that finds no runs at all is caught",
             "the median refusal, the censoring and the Nyquist bar are all "
             "statements about runs; a run finder that returns nothing must "
             "not leave them printing about nothing")

    _wrap(movetap, "_selftest_flip_denominator",
          "C3: an `unread:` sample breaks the chain instead of scoring two "
          "transitions",
          "10% flaky reads over a fence that never moves scored 0.20 "
          "flips/sample under the old rule -- 40% of the escalation bar, "
          "manufactured out of the reader's own misses")
    _control(movetap, "count_flips", lambda seq: (0, 0),
             "_selftest_flip_denominator",
             "a `count_flips` that always answers (0, 0) is caught",
             "an aliasing guard whose numerator is pinned at zero can never "
             "refuse, which is the failure direction that costs a compiler")

    _wrap(movetap, "_selftest_gate1",
          "C6: the ASYNC twin, 0x005FF820's clamp, and the band this reader "
          "refuses",
          "`below` with the fence open is escalation trigger 2(b), so a read "
          "that failed and still produced a plausible separation would buy a "
          "hook nobody needed")
    _control(movetap, "GATE1_CUT", 400.0, "_selftest_gate1",
             "moving gate 1's cut off the float the image holds is caught",
             "300.0 is read back out of 0x00946564 by section 5; this proves "
             "the classifier actually uses it rather than agreeing with it")

    _wrap(movetap, "_selftest_early_outs",
          "C7/C8: the two exits above gate 1, and their three-valued sentinel",
          "`False` is a real answer to \"did this exit fire\" exactly as 0 is "
          "a real answer to \"is the fence shut\", so an unread block must "
          "return neither")
    _control(movetap, "EARLY_OUT_A_MODE", 8, "_selftest_early_outs",
             "the literal 9 at 0x0060563A is load-bearing",
             "mode 8 is the top of 0x00602660's own switch and mode 1 is what "
             "every 0x002B we send carries -- an off-by-one here would fire "
             "the exit on ordinary traffic")

    _wrap(movetap, "_selftest_naming",
          "C9: `shut:append` is what 0x00605840 does, and the summary says so "
          "in the conditional",
          "the four branch labels go into every stored row permanently, and "
          "the probe's documented landing grep for the old spelling must "
          "return 0")
    _control(movetap, "test_would_run", lambda v: True, "_selftest_naming",
             "counting `world1:append` as fence-open is caught",
             "world 1 is the branch on which the caller skips the test "
             "entirely, so folding it in inflates p and deflates the aliasing "
             "ratio -- the wrong direction for a guard")

    _wrap(movetap, "_selftest_chain",
          "REALFIX-I1: the history chain walks to a NULL terminator and every "
          "other outcome names itself",
          "the chain is the operand of the client's own match test, and a "
          "torn read that returned a short chain would produce \"no node "
          "within MATCH_RADIUS of q\" for free -- which is the sentence that "
          "revives candidate B")
    _control(movetap, "HIST_SEP_GATE", 1e9, "_selftest_chain",
             "the sep > 250 u gate is load-bearing in BOTH directions",
             "raising it past every fixture makes the healthy walk read as "
             "`not-attempted:below-gate`, which is what a gate quietly set too "
             "high would do to a whole live run -- the chain would never be "
             "read and the file would look healthy")
    _control(movetap, "HIST_MAX_NODES", 2, "_selftest_chain",
             "and so is N: a chain longer than N must say TRUNCATED",
             "with N=2 the healthy 4-node fixture stops mid-chain, and a walk "
             "that called that `ok` would licence a null over a polyline it "
             "never finished reading")
    _control(movetap, "PTR_MIN", 0, "_selftest_chain",
             "and so are the pointer bounds",
             "with no low bound a head of 0x400 -- inside the 64 KB "
             "null-guard region no Windows process ever maps -- reads as a "
             "node address rather than as garbage")

    _wrap(movetap, "_selftest_r5",
          "CANCELWALK-R5: the walk-start footprint is decoded from the right "
          "bytes, on BOTH world copies",
          "R5's whole verdict is whether the ASYNC body's walk-start fields "
          "CHANGE across a frozen press, so an offset pointing one dword away "
          "-- or an async decode that silently re-read the sync block -- would "
          "produce a confident 'signature absent' from bytes nobody asked for")
    _control(movetap, "A_REQ_TOKEN", 0x54, "_selftest_r5",
             "the request-token offset is load-bearing and a one-dword slip is "
             "caught",
             "+0x50 is the move-request correlation token the local applier "
             "allocates per SUCCESSFUL walk-start call, so 0 -> N is the "
             "detector that the applier ran rather than bailing at a gate; "
             "reading +0x54 instead returns a confident number that never "
             "changes, which reads as 'the walk-start never ran' and is "
             "indistinguishable from a real freeze")
    _control(movetap, "A_DIR", 0xC4, "_selftest_r5",
             "and so is the facing offset",
             "+0xC4 is the movement MODE, an int; decoding it as the facing "
             "float pair would make the direction classifier read garbage "
             "while still printing two plausible numbers")

    # ---------------------------------------------------------------------
    print("\n19. movesync's C4/C5/C9 sections, in the SUITE")
    # Same argument, the other file. These three were reachable only through
    # `python toolkit/clientscan/movesync.py --selftest`, which nothing in the
    # suite runs.
    _wrap(movesync, "_selftest_jump_tally",
          "C4: the jump table is a THREE-WAY tally that sums to n, and refuses "
          "on holes",
          "a could-not-read used to be swept into the fence-SHUT count in the "
          "headline -- on the real 20260819T171436 that printed \"0 of 13 "
          "snap(s) began with the test REACHABLE\" over 13 rows that were "
          "nothing but missing fields")
    _control(movesync, "classify_reach", lambda v: "fenced",
             "_selftest_jump_tally",
             "a classifier that calls every cell `fenced` is caught",
             "that IS the pre-C4 defect -- the hole and the real state are "
             "indistinguishable once they share a bucket")

    _wrap(movesync, "_selftest_appender_witness",
          "C5: the appender witness is a WRITE observed, and refuses rather "
          "than printing a zero",
          "\"0 witnessed\" on a movetap that carries no `state_record` reads "
          "as \"the appender never ran\", which is a finding minted from a "
          "missing key")
    _control(movesync, "state_fields", lambda s: (None, None),
             "_selftest_appender_witness",
             "a `state_fields` that reads nothing is caught",
             "the witness's positive arms are the only observation in this "
             "lane that is not a state read; a reader that cannot see the "
             "fields must say so and not score them")

    _wrap(movesync, "_selftest_spellings",
          "C9: the vault's pre-rename `:apply` rows are READ and printed "
          "`:append`",
          "every movetap already on disk carries the old spelling; a consumer "
          "that silently mismatched would drop a real fenced sample into the "
          "hole bucket and then refuse on its own drop")
    _control(movesync, "REACH_ALIASES", {}, "_selftest_spellings",
             "a reader that knows only the new spelling is caught",
             "this is the pre-C9 state, and it is the one that fails quietly "
             "-- the row is not an error, it is just not counted")

    _wrap(movesync, "_selftest_print_fence",
          "C4+C5 in the REPORT: print_fence prints the tally AND the witness "
          "below its own population refusal, over the population it names",
          "the round before this pinned the tally at the DICT while the "
          "operator reads the TEXT; this one found the text pinned at the "
          "FUNCTION while the operator reads the PIPELINE -- deleting the "
          "`print_appender_witness` call from print_fence, the only path "
          "`main()` takes, was green at 49/49 and 147/147 with the whole of C5 "
          "gone from the output")
    _control(movesync, "print_appender_witness", lambda *a, **k: 0,
             "_selftest_print_fence",
             "a print_fence whose witness prints NOTHING is caught",
             "that is the mutation the previous review landed green: the "
             "witness is C5's only positive observation, and a report that "
             "silently drops it still ends in a fence share the probe would "
             "quote")

    # ---------------------------------------------------------------------
    print("\n20. and NOTHING in either selftest is left out of the suite")
    # The rule this file is under is that a test nobody runs is not a test.
    # §17-§19 satisfy it for the sections that exist TODAY; this asks the
    # MODULE what sections exist, so a section added tomorrow and not wrapped
    # goes red here instead of being discovered missing in a week. Same shape
    # as `test_srclint.py` §7, which pairs every test file with a TESTS.md
    # entry in both directions.
    #
    # `WRAPPED` and not the table: the set is filled by `_wrap` as it RUNS, so
    # a section whose call site is deleted while its table row stays is caught.
    # The table is checked against the same set for the mirror -- a stale row
    # is a floor nothing enforces.
    for mod, table in ((movetap, MOVETAP_SECTIONS),
                       (movesync, MOVESYNC_SECTIONS)):
        on_disk = {n for n in dir(mod) if n.startswith("_selftest_")}
        wrapped = {n for m, n in WRAPPED if m == mod.__name__}
        tabled = {n for n, _f in table}
        check(bool(on_disk) and on_disk == wrapped and tabled == on_disk,
              f"{mod.__name__} defines {len(on_disk)} `_selftest_*` section(s) "
              f"and this run wrapped all of them",
              f"never wrapped: {sorted(on_disk - wrapped)}; wrapped but gone "
              f"from the module: {sorted(wrapped - on_disk)}; floor rows for "
              f"nothing: {sorted(tabled - on_disk)} -- the set is asserted "
              f"non-empty first, because 'all zero of them are wrapped' is "
              f"this repo's own recorded trap")
        # CONTROL: plant one and require the same computation to name it.
        setattr(mod, "_selftest_planted_control", lambda: (0, 1))
        try:
            planted = sorted({n for n in dir(mod)
                              if n.startswith("_selftest_")} - wrapped)
        finally:
            delattr(mod, "_selftest_planted_control")
        check(planted == ["_selftest_planted_control"],
              f"CONTROL: a section added to {mod.__name__} and not wrapped is "
              f"named ({planted})",
              "a coverage check that cannot see a new section is a coverage "
              "check that will pass forever")

    check(bool(SHAPES) and all(r == p for _l, r, p in SHAPES),
          f"and every self-reporting section's count equals the number of "
          f"[PASS]/[FAIL] lines it printed ({len(SHAPES)} section(s), "
          f"{sum(r for _l, r, _p in SHAPES)} checks)",
          f"disagreements: {[s for s in SHAPES if s[1] != s[2]]} -- a section "
          f"that returns a count it did not execute, and a wrapper that "
          f"misreads the return shape, are the same defect from two sides, "
          f"and the second one is what silently disabled section 17")

    # AND THE OPERATOR'S OWN COMMAND, end to end, floor and all. §17-§19 call
    # the sections directly and would not notice movetap's own SELFTEST_FLOOR
    # going stale, or its sections 1-4 -- the source reads -- ceasing to run.
    rc_mt, out_mt = _run_section(movetap.selftest)[0::3]
    check(rc_mt == 0,
          f"`movetap.py --selftest` is green end to end "
          f"({out_mt.count('[PASS]')} [PASS] against a declared floor of "
          f"{movetap.SELFTEST_FLOOR}, less {out_mt.count('[SKIP]')} declared "
          f"skip(s))",
          "this is the command the probe's step 3 tells the operator to run "
          "before the client is launched, so the suite must not be able to "
          "diverge from it")
    _control(movetap, "SELFTEST_FLOOR", movetap.SELFTEST_FLOOR + 1000,
             "selftest", "movetap's own floor rule can go red",
             "a floor nothing has been seen to enforce is a wish; this raises "
             "it above what a green run executes and requires the module to "
             "refuse itself")

    rc_ms, out_ms = _run_section(movesync.selftest)[0::3]
    check(rc_ms == 0,
          f"and `movesync.py --selftest` is green end to end "
          f"({out_ms.count('[PASS]')} [PASS] against a declared floor of "
          f"{movesync.SELFTEST_FLOOR})",
          "movesync's sections 1-7 are the pre-2026-08-20 guards and are "
          "wrapped nowhere else in this file")
    _control(movesync, "SELFTEST_FLOOR", movesync.SELFTEST_FLOOR + 1000,
             "selftest", "movesync's own floor rule can go red",
             "sections 8-10 carry a `_floor` each and sections 1-7 carried "
             "none, so deleting section 2's only check took the module from 38 "
             "[PASS] to 37 with this file and `--selftest` both still exit 0 -- "
             "a per-section floor under a total nothing checks is half a rule")
    # (1, 6) and not a bare 1: the sections return `(bad, ran)` since the floor
    # landed, and the stub keeps `ran` AT the section's own floor on purpose --
    # so what reddens the run is the summation of `bad`, which is this control's
    # whole subject, and not the floor rule the control above already pins.
    _control(movesync, "_selftest_spellings", lambda: (1, 6), "selftest",
             "a red section really does redden movesync's whole selftest",
             "movesync sums a bare `bad` rather than routing through "
             "`checks.py`, so the summation is the only thing carrying a "
             "failure out, and it is worth seeing it carry one")

    # ---------------------------------------------------------------------
    print("\n21. REALFIX-T1: which clock the offset came from, and the residual")
    # THE WHOLE 1.00 s WAS ON ONE SIDE AND IT WAS ONE LINE. `authsrv.py:8396`
    # stamped `wall` truncated to the second, so `offset_from_stamps` could only
    # bound the offset from below and the measured spread was 0.999920 s (L1 arm
    # A) / 0.999777 s (arm B) -- 288 units at run speed, on every wire<->movetap
    # pairing this arc has made. `wall_unix` is the same instant at 1e-7 s
    # resolution. What this section is really about is that the two estimators
    # are NEVER MIXED and that the file SAYS which one it used: a run that
    # silently fell back to the truncated stamps produces identical-looking
    # numbers everywhere downstream.
    T0 = 1_755_000_000.5

    def cap(path, rows):
        return write_capture(path, rows)

    with tempfile.TemporaryDirectory() as td:
        # A post-T1 capture: every row carries BOTH stamps, exactly as
        # `Recorder.event` now writes them.
        # 40 rows at a 0.317 s cadence, not a handful: the truncated
        # estimator's residual approaches 1.00 s only as the rows sample
        # `frac(unix)` densely, and six rows reach 0.76 -- which would have
        # understated the defect this whole delta is about. A real capture
        # carries hundreds.
        ts = [round(0.317 * k, 3) for k in range(40)]
        post = cap(os.path.join(td, "post.jsonl"), [
            dict(selfreport(t, 100.0 * i, 200.0 * i),
                 wall=time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                    time.gmtime(int(T0 + t))),
                 wall_unix=T0 + t)
            for i, t in enumerate(ts)])
        # A pre-T1 capture: the truncated stamp and nothing else. Every capture
        # in the vault is one of these, so the fallback is not a corner case --
        # it is the whole existing corpus.
        pre = cap(os.path.join(td, "pre.jsonl"), [
            dict(selfreport(t, 100.0 * i, 200.0 * i),
                 wall=time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                    time.gmtime(int(T0 + t))))
            for i, t in enumerate(ts)])

        _reps, w_post, _s = movesync.load_wire_reports(post)
        _reps, w_pre, _s = movesync.load_wire_reports(pre)
        d_post = movesync.offset_detail(w_post)
        d_pre = movesync.offset_detail(w_pre)

        check(d_post["source"] == movesync.OFFSET_SRC_UNIX
              and d_pre["source"] == movesync.OFFSET_SRC_TRUNC,
              f"a capture carrying `wall_unix` is read from it "
              f"({d_post['source']}) and one without falls back "
              f"({d_pre['source']})",
              "the preference is the whole delta; a loader that ignored the "
              "float stamp would leave the 1.00 s in place with nothing saying so")
        check(abs(d_post["offset"] - T0) < 1e-6,
              f"and the float offset is the truth to the microsecond "
              f"({d_post['offset'] - T0:+.9f} s)",
              "per-row `wall_unix - t` IS the offset; anything else here means "
              "the loader is deriving rather than reading it")
        check(d_post["spread"] < 1e-6 and d_post["spread"] * movesync.RUN_SPEED < 0.3,
              f"the achieved residual is {d_post['spread'] * 1000.0:.6f} ms = "
              f"{d_post['spread'] * movesync.RUN_SPEED:.4f} u at "
              f"{movesync.RUN_SPEED:.0f} u/s -- REALFIX section 2.2's "
              f"\"< 1 ms (< 0.3 u)\" line, demonstrated",
              "this is the number the whole clock-anchor delta exists to move")
        check(0.9 < d_pre["spread"] < 1.0,
              f"while the truncated estimator's residual is "
              f"{d_pre['spread']:.6f} s = "
              f"{d_pre['spread'] * movesync.RUN_SPEED:.0f} u -- the 1.00 s "
              f"REALFIX section 2.1 measured, reproduced from a synthetic file",
              "if the fallback did NOT show ~1 s here the fixture is not "
              "exercising the defect and the comparison above means nothing")
        check(d_pre["offset"] <= T0 and T0 - d_pre["offset"] < 1.0,
              f"and the fallback still estimates from BELOW "
              f"({d_pre['offset'] - T0:+.3f} s), unchanged",
              "every capture in the vault is a pre-T1 one, so the old "
              "estimator's behaviour is not free to move")

        # THE FLOAT ARM'S ESTIMATOR IS A MEDIAN, AND UNTIL NOW NOTHING SAID SO.
        # `offset_detail`'s docstring makes median-vs-max the whole design of
        # the two arms, and the TRUNCATED arm's max is well guarded (swapping it
        # for a mean reddens five checks including a vault replay). The float
        # arm had no such control: every fixture above is exact by construction,
        # so mean == median in all of them and substituting one for the other
        # was invisible. A median is chosen precisely to survive a scheduling
        # outlier, so the fixture now plants one: 39 rows on the truth and one
        # row 5 s late. The mean moves 125 ms = 36 u; the median does not move
        # at all.
        out_rows = [dict(selfreport(t, 0.0, 0.0),
                         wall=time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                            time.gmtime(int(T0 + t))),
                         wall_unix=T0 + t + (5.0 if i == 7 else 0.0))
                    for i, t in enumerate(ts)]
        outl = cap(os.path.join(td, "outlier.jsonl"), out_rows)
        _reps, w_out, _s = movesync.load_wire_reports(outl)
        d_out = movesync.offset_detail(w_out)
        offs = sorted(w_out.unix)
        mean = sum(offs) / len(offs)
        check(abs(d_out["offset"] - T0) < 1e-6 and abs(mean - T0) > 0.1
              and abs(d_out["offset"] - mean) > 0.1,
              f"one 5 s scheduling outlier in {len(offs)} rows moves the MEAN "
              f"{(mean - T0) * 1000.0:+.0f} ms = "
              f"{(mean - T0) * movesync.RUN_SPEED:+.0f} u and moves the median "
              f"{(d_out['offset'] - T0) * 1e6:+.1f} us -- the float arm takes "
              f"the median, which is the whole reason it is not a mean",
              "the two estimators were distinguished in prose and by one "
              "guarded arm only; this is the other arm")

        # NEVER SILENTLY MIX. A file with both kinds of row uses one family and
        # counts the other; averaging them would give a number that is neither.
        mixed = cap(os.path.join(td, "mixed.jsonl"), [
            dict(selfreport(t, 0.0, 0.0),
                 wall=time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                    time.gmtime(int(T0 + t))),
                 **({"wall_unix": T0 + t} if i >= len(ts) - 2 else {}))
            for i, t in enumerate(ts)])
        _reps, w_mix, _s = movesync.load_wire_reports(mixed)
        d_mix = movesync.offset_detail(w_mix)
        check(d_mix["source"] == movesync.OFFSET_SRC_UNIX
              and d_mix["n"] == 2 and d_mix["n_trunc"] == len(ts)
              and abs(d_mix["offset"] - T0) < 1e-6,
              f"a MIXED file uses the {d_mix['n']} float row(s) and merely "
              f"counts the {d_mix['n_trunc']} truncated ones "
              f"({d_mix['offset'] - T0:+.9f} s from the truth)",
              "pooling the two families gives an offset biased by the mix "
              "ratio -- neither estimator, and no way to tell from the number")

        # THE LINE ITSELF, read back out of stdout. A residual computed and not
        # printed is the assumption T1 exists to remove, and `offset_from_stamps`
        # is where every consumer in the tree goes through.
        for d, want in ((d_post, "wall_unix"), (d_pre, "truncated")):
            line = movesync.offset_line(d)
            check(want in line and ("REALFIX-T1" in line),
                  f"the printed line names its estimator: {line.strip()[:96]}",
                  "which one was used is invisible in every downstream number, "
                  "so if it is not on this line it is nowhere")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            off, spread = movesync.offset_from_stamps(w_post)
        printed = buf.getvalue()
        check((off, spread) == (d_post["offset"], d_post["spread"])
              and "wall_unix" in printed
              and f"{d_post['spread'] * 1000.0:.3f} ms" in printed,
              "`offset_from_stamps` still returns the two-value contract every "
              "caller unpacks, AND announces the source and residual",
              f"returned {(off, spread)} and printed {printed!r} -- a third "
              f"return value would have broken movesync.pair, resyncscore, "
              f"grantsim and this file's own section 1")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            movesync.offset_from_stamps(w_post, announce=False)
        check(buf.getvalue() == "",
              "and `announce=False` really is silent, for the one caller that "
              "prints the line itself",
              "movesync.main() formats its own header; two copies of the line "
              "would read as two different measurements")

        # A plain list -- which is what every synthetic fixture and every
        # pre-T1 caller hands it -- must take the fallback and NOT raise.
        d_list = movesync.offset_detail([10.0, 10.5, 9.8])
        check(d_list["source"] == movesync.OFFSET_SRC_TRUNC
              and d_list["offset"] == 10.5,
              "a plain `list` of truncated offsets still works unchanged "
              f"({d_list['source']}, max {d_list['offset']})",
              "`getattr(walls, 'unix', ())` IS the fallback test; a list has no "
              "such attribute, so there is no version flag to get wrong")
        check(movesync.offset_detail([])["source"] is None
              and movesync.offset_from_stamps([], announce=False) == (None, None),
              "and no stamps at all still yields None rather than a confident 0",
              "a zero offset would pair every report against the wrong instant")

        # T1's OTHER HALF, on the server: the row really carries both stamps.
        rows = [json.loads(l) for l in open(post, encoding="utf-8")]
        check(all("wall" in r and "wall_unix" in r for r in rows),
              "the post-T1 row shape keeps `wall` beside `wall_unix`",
              "every existing consumer and every vault fixture reads `wall`; "
              "replacing it rather than adding beside it would strand the corpus")

        # --- AND THE WHOLE THING END TO END, THROUGH THE REAL RECORDER ------
        # The fixtures above are hand-built and their `wall_unix` is exact by
        # construction, so their 0.000 ms residual measures the fixture. This
        # writes a capture with `authsrv.Recorder` ITSELF -- the same two
        # adjacent clock reads inside `event()` that a live run makes -- and
        # loads it back through `load_wire_reports`. What it measures is the
        # real thing: `perf_counter` against the system clock, over the real
        # scheduling jitter between the two calls. No socket, no client, no
        # server: `Recorder` only needs a directory.
        sys.path.insert(0, os.path.join(os.path.dirname(HERE), "authsrv"))
        try:
            import authsrv                                   # noqa: E402
        except Exception as exc:                             # pragma: no cover
            LEDGER.skip("21. the real Recorder",
                        f"authsrv would not import: {type(exc).__name__}: {exc}")
        else:
            rdir = os.path.join(td, "rec")
            rec = authsrv.Recorder(rdir, 9)
            for i in range(200):
                rec.event("decoded", opcode=movesync.OP_SET_HEADING,
                          name="MOVE_SET_HEADING",
                          values=[32829, [100.0 * i, 200.0 * i], 0,
                                  [0.0, 765.0], 1])
            rec.meta.close()
            rec.raw.close()
            wrote = [f for f in os.listdir(rdir) if f.endswith(".jsonl")]
            live = os.path.join(rdir, wrote[0])
            reps_r, w_real, _s = movesync.load_wire_reports(live)
            d_real = movesync.offset_detail(w_real)
            check(d_real["source"] == movesync.OFFSET_SRC_UNIX
                  and d_real["n"] == len(reps_r) + 1,
                  f"the real `Recorder` writes {d_real['n']} float-stamped "
                  f"row(s) and the loader reads them",
                  "n is the reports plus the origin row Recorder.__init__ "
                  "emits; anything less means rows are losing the stamp")
            check(d_real["spread"] < 0.001,
                  f"REALFIX-T1 DEMONSTRATED END TO END: the offset spread over "
                  f"{d_real['n']} real rows is "
                  f"{d_real['spread'] * 1e6:.1f} us = "
                  f"{d_real['spread'] * movesync.RUN_SPEED:.4f} u, against the "
                  f"{d_pre['spread']:.3f} s / "
                  f"{d_pre['spread'] * movesync.RUN_SPEED:.0f} u the truncated "
                  f"stamp gives -- REALFIX section 2.2's \"< 1 ms (< 0.3 u)\" "
                  f"clock term, measured rather than assumed",
                  "this is the ONE number the whole clock anchor exists to "
                  "move, and it is measured on the same two adjacent clock "
                  "reads a live run makes")
            trunc_real = movesync.offset_detail(
                movesync.WallStamps(list(w_real), ()))
            check(trunc_real["spread"] > 100.0 * d_real["spread"],
                  f"and the SAME capture scored on its truncated stamps gives "
                  f"{trunc_real['spread']:.3f} s -- "
                  f"{trunc_real['spread'] / max(d_real['spread'], 1e-12):.0f}x "
                  f"worse on the identical rows",
                  "the same file, the two estimators, side by side: this is "
                  "the comparison that says the improvement is the stamp and "
                  "not the fixture. NOTE the truncated arm is FLATTERED here "
                  "-- 200 rows written in a few ms span less than one second, "
                  "so its spread is the span rather than the 1.00 s a real run "
                  "reaches; the synthetic fixture above is where the full "
                  "defect shows, and 100x is deliberately far below it")

    # REALFIX-T2: the harness's leg table is the second clock, and it is
    # ANOTHER +/-0.5 s = +/-143 u on every leg-to-capture mapping.
    # A GREP THAT A COMMENT SATISFIES IS NOT A CHECK. Commenting out
    # `kw["wall_unix"] = time.time()` left the source greps below GREEN -- the
    # behavioural checks above caught it, which is why this is a hardening and
    # not a hole, but a row that can only pass is the mirror of one that can
    # only fail. Every grep in this block runs over LIVE lines only.
    def _live(path):
        return "\n".join(
            l for l in open(path, encoding="utf-8").read().splitlines()
            if not l.lstrip().startswith("#"))

    sess = os.path.join(os.path.dirname(HERE), "harness", "session.py")
    src_ss = _live(sess)
    check(all(k in src_ss for k in ('"started_unix": started_unix',
                                    '"ended_unix": ended_unix',
                                    '"settled_unix": settled_unix')),
          "REALFIX-T2: `walk_legs` records float leg stamps beside the "
          "whole-second strings",
          "the leg row's three stamps were whole-second, worth +/-0.5 s = "
          "+/-143 u on every leg-to-capture mapping in both L1 lanes' analyses")
    check(src_ss.count("started_unix = time.time()") == 1
          and src_ss.count("ended_unix = time.time()") == 1
          and src_ss.count("settled_unix = time.time()") == 1
          and src_ss.index("settled_unix = time.time()")
              > src_ss.index("time.sleep(settle)"),
          "and `settled_unix` is read AFTER the settle sleep, not before it",
          "a settled stamp taken before the sleep is the ended stamp under "
          "another name, and the 1.5 s between them is the whole point")
    src_as = _live(os.path.join(os.path.dirname(HERE), "authsrv", "authsrv.py"))
    check('kw["wall_unix"] = time.time()' in src_as
          and 'kw["wall"] = time.strftime' in src_as,
          "REALFIX-T1: `Recorder.event` stamps `wall_unix` beside `wall`",
          "the truncated stamp is the source of the whole 1.00 s spread and "
          "the float one is one line beside it -- and this grep now runs over "
          "LIVE lines, because commenting the stamp out left it green")

    # PURITY, ASKED OF BOTH SYNTAX TREES. CLAUDE.md carve-out (1) scopes
    # capstone/pefile to msghandler.py and codescan.py; neither of these is one
    # of them, movetap's reader is pure ctypes, and both have to load on a bare
    # machine. `import pefile` was planted at the top of movetap.py and this
    # file, movetap --selftest, test_srclint and test_bareimport were ALL green,
    # because both packages happen to be installed here. movetap guards itself
    # in its own section 3; this is the same guard for movesync, and a second
    # witness for movetap so the guard cannot be deleted from one place quietly.
    for mod in ("movetap.py", "movesync.py"):
        tree_m = ast.parse(open(os.path.join(HERE, mod), encoding="utf-8").read())
        got = set()
        for nd in ast.walk(tree_m):
            if isinstance(nd, ast.Import):
                got |= {al.name.split(".")[0] for al in nd.names}
            elif isinstance(nd, ast.ImportFrom) and nd.module:
                got.add(nd.module.split(".")[0])
        bad_imp = got & {"capstone", "pefile", "PIL", "numpy"}
        check(not bad_imp,
              f"{mod} takes NO third-party import -- carve-out (1) names two "
              f"files and this is not one of them",
              f"found {sorted(bad_imp)}" if bad_imp
              else f"{len(got)} module(s) imported, all stdlib or local")

    return LEDGER.verdict()


if __name__ == "__main__":
    raise SystemExit(main())
