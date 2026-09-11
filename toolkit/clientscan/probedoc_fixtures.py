#!/usr/bin/env python3
"""THE ONE PLACE the sample output in `studies/movement/PROBE-GATEFIRE.md` §6 comes from.

    python toolkit/clientscan/probedoc_fixtures.py --list
    python toolkit/clientscan/probedoc_fixtures.py --write <outdir>
    python toolkit/clientscan/probedoc_fixtures.py --show FIX-01

WHY THIS FILE EXISTS, and it is a defect report rather than a design note.

`PROBE-GATEFIRE.md` is an operator procedure. Its §6 tells the operator what the
instrument prints, so that a real run can be matched against it. Those blocks
were written **before the instrument existed**, and by 2026-08-20 they had
drifted in five separate ways at once: a whole `ALIASING: ... white 0.409` line
that no code has ever printed and no `white` field to print it from; a 2-line
fence header where the code prints 3; an `unread:*  0  0.0%` row that
`fence_verdict` cannot emit because it iterates `sorted(reach.items())`; an
EPISODES section that differed in nearly every particular; and an APPENDER
WITNESS section attributed to `movetap`, which has no such printer.

**Nothing noticed, for as long as the document existed.** Not a test, not a
lint, not a reader. The document said RECONSTRUCTION on one block and that label
was read as a licence rather than as a debt.

So the sample blocks are now generated, never typed, and they are generated from
**here** -- one module, imported by both consumers, so the two cannot diverge:

  * `toolkit/clientscan/test_probedoc.py` regenerates every block and asserts it
    is present in the document byte for byte. That test is the tripwire.
  * anyone regenerating §6 runs `--write <dir>` and pastes the files. The splice
    is mechanical; nothing is retyped.

If those two ever read different fixtures the guarantee is gone, which is why
there is exactly one copy and it is this one.

WHAT IS AND IS NOT A MEASUREMENT HERE. Every `FIX-*` fixture is **real code over
hand-laid synthetic input**: the *shape* of the output is a measurement of
`movetap.py` and `movesync.py`, and **every number inside it is an illustration,
not an observation of the client**. §6 says so per block and §11 files them in
their own tier. The `REAL-*` entries are the opposite: genuine stdout over
genuine vault captures, and they are OBSERVED. There is no third tier, because
`vault/captures/movetap/` holds five files, all 2026-08-19, and none carries
`gate_reach`, `state_record` or `hist_head` -- n = 0 post-C9 captures exist, so
no real closing block from the tap can exist yet.

DETERMINISM IS A REQUIREMENT, NOT A HOPE. A fixture that moves between runs
turns the test into noise and the noise into a lowered bar. Every fixture is
either a hand-laid state list or a seeded `random.Random`; `test_probedoc.py`
renders each one twice and asserts the two are identical, so a fixture that
picks up a clock, a path or an unseeded RNG goes red on the day it is written
rather than on the day it matters.

PROVENANCE. The fixture bodies were first laid down by the 2026-08-20 capture
lane (scratch `capture_blocks.py`) and are carried here unchanged in substance;
what changed is that they now live in the repo, resolve their own tree instead
of hard-coding a worktree path, and are addressable one at a time.
"""
import argparse
import contextlib
import io
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "harness"))

import movetap    # noqa: E402
import movesync   # noqa: E402

# The document these fixtures are quoted in. Resolved from THIS file so a
# worktree reads its own copy -- never `../../studies`, and never a pinned
# absolute path, which is the defect that put 23 commands in §6 pointing at a
# worktree 36 commits stale.
REPO = os.path.dirname(os.path.dirname(HERE))
DOC = os.path.join(REPO, "studies", "movement", "PROBE-GATEFIRE.md")

# The files §6 pins by sha256. Named here so the test does not re-derive
# the list from prose. `movefence.py` joined on 2026-09-11, when the fence
# section was cut out of `movesync.py`: the three printers §6 quotes live there
# now, so a two-name list would have kept the staleness pin on a file that no
# longer contains them and would have dropped the printers out of §4's
# `white`-literal scan while it stayed green over the remainder.
PINNED_SOURCES = ("movetap.py", "movesync.py", "movefence.py")

HZ_DEFAULT = 10.4
DROPS = (movetap.REACH_DROPPED, movetap.REACH_UNRESOLVED)

_REGISTRY = {}
_ORDER = []


def fixture(name, what):
    """Register one fixture. The body prints; the runner captures what it printed."""
    def deco(fn):
        if name in _REGISTRY:
            raise ValueError(f"duplicate fixture id {name!r}")
        fn.fixture_name = name
        fn.what = what
        _REGISTRY[name] = fn
        _ORDER.append(name)
        return fn
    return deco


def render(name):
    """(rc, text) for one fixture. `text` is exactly the bytes the printer printed."""
    fn = _REGISTRY[name]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = fn()
    return rc, buf.getvalue()


def names():
    """Every fixture id, in declaration order."""
    return list(_ORDER)


def what(name):
    return _REGISTRY[name].what


# ==========================================================================
# THE SHARED BUILDERS
# ==========================================================================

def run(segments, hz=HZ_DEFAULT, t0=0.0):
    """(seq, reach, n, flips, pairs, poll_hz) from [(state, count), ...].

    `seq` is one tuple per POLL, exactly as `movetap.main()` builds it: a poll
    that produced no row still leaves its drop marker in `seq`, and drop markers
    are NOT tallied into `reach` or into `n`. That gap is what the poll-rate
    line reports, and getting it wrong here would make the fixtures agree with
    a printer that is reading a different denominator.
    """
    states = []
    for st, k in segments:
        states.extend([st] * k)
    dt = 1.0 / hz
    seq = [(round(t0 + i * dt, 4), s) for i, s in enumerate(states)]
    reach = {}
    for _t, s in seq:
        if s in DROPS:
            continue
        reach[s] = reach.get(s, 0) + 1
    n = sum(reach.values())
    flips, pairs = movetap.count_flips(seq)
    span = seq[-1][0] - seq[0][0]
    return seq, reach, n, flips, pairs, ((len(seq) - 1) / span if span else None)


def gate1_split(n, above, below, band, plane):
    """A gate-1 tally that SUMS TO n, plus the `why` breakdown of its undecided cell.

    Nothing is hand-computed: the caller states three parts and the fourth is
    whatever is left, and the assert refuses a tally that does not close.
    """
    und = band + plane
    assert above + below + und == n, (above, below, und, n)
    g1 = {movetap.GATE1_ABOVE: above, movetap.GATE1_BELOW: below,
          movetap.GATE1_UNDECIDED: und}
    return g1, {"band": band, "plane-mismatch": plane}


def simulate(open_ms, shut_ms, hz, seconds, seed):
    """Sample a two-state fence with EXPONENTIAL dwells at `hz`.

    The model `movetap`'s own aliasing comment describes -- 15 ms open against
    185 ms shut at 10.4 Hz -- reproduced so the refusal block in the document is
    a real output of the real guard rather than a shape somebody drew.
    """
    rng = random.Random(seed)
    t, st = 0.0, False
    edges = [(0.0, False)]
    while t < seconds + 1.0:
        mean = (open_ms if st else shut_ms) / 1000.0
        t += rng.expovariate(1.0 / mean)
        st = not st
        edges.append((t, st))
    dt, ei, states = 1.0 / hz, 0, []
    for i in range(int(seconds * hz)):
        now = i * dt
        while ei + 1 < len(edges) and edges[ei + 1][0] <= now:
            ei += 1
        states.append(movetap.REACH_TEST_RUNS if edges[ei][1] else "shut:append")
    return states


# --- the movetap sequences, built once and shared by several fixtures ------

def _seq01():
    """45 s at 12.5 Hz. shut:append 402 in 4 runs (169/90/102/41, median 96,
    first and last censored by the block boundary); test-runs 162 in 3 interior
    runs (103/47/12, median 47). Nothing unread, nothing dropped."""
    seq, reach, n, flips, pairs, _ = run(
        [("shut:append", 169), ("test-runs", 103),
         ("shut:append", 90), ("test-runs", 47),
         ("shut:append", 102), ("test-runs", 12),
         ("shut:append", 41)], hz=12.5)
    assert n == 564 and reach["shut:append"] == 402 and reach["test-runs"] == 162
    return seq, reach, n, flips, pairs, n / 45.1


def _seq02():
    """45 s at 10.4 Hz carrying EVERY label movetap can print: both fenced
    tails, world1:append, a real-sample unread, and both poll-produced-no-row
    markers -- which are in `seq` and in NEITHER `reach` nor `n`."""
    seg = [("shut:append", 120), ("test-runs", 22), ("shut:append", 50),
           (movetap.REACH_DROPPED, 3), ("shut:append", 45), ("test-runs", 31),
           ("shut:append", 8), ("world1:append", 9), ("shut:noop", 14),
           ("world1:append", 6), ("shut:append", 55),
           ("unread:agent-id-mismatch", 5), ("shut:append", 26),
           ("test-runs", 18), ("shut:append", 1), ("test-runs", 2),
           ("shut:append", 30), (movetap.REACH_UNRESOLVED, 2),
           ("shut:append", 20)]
    seq, reach, n, flips, pairs, _ = run(seg, hz=10.4)
    return seq, reach, n, flips, pairs, n / 45.0


def _seq03():
    """54 s at 10.4 Hz. test-runs in TWO runs, both touching the block
    boundary, so the median is REFUSED and the effective n is 3 episodes."""
    seq, reach, n, flips, pairs, _ = run(
        [("test-runs", 254), ("shut:append", 56), ("test-runs", 254)], hz=10.4)
    return seq, reach, n, flips, pairs, n / 54.5


def _seq04():
    """The agent id disagrees with the id resolved through ChCli on ~30% of
    samples. The share table still prints and the refusal then voids it."""
    seg = []
    for i in range(40):
        seg += [("shut:append", 7), ("unread:agent-id-mismatch", 3)]
        if i % 6 == 5:
            seg += [("test-runs", 4), ("unread:agent-id-mismatch", 1)]
    seq, reach, n, flips, pairs, _ = run(seg, hz=10.4)
    return seq, reach, n, flips, pairs, n / (len(seq) / 10.4)


def _seq05():
    """60 s at 10.4 Hz against a fence whose true dwells are 15 ms open /
    185 ms shut -- about ten true transitions a second, wholly unresolvable.
    Seeded, so the block reproduces byte for byte."""
    seq, reach, n, flips, pairs, _ = run(
        [(s, 1) for s in simulate(15, 185, 10.4, 60.0, seed=20260820)], hz=10.4)
    return seq, reach, n, flips, pairs, n / 60.0


def _seq06():
    """H1 at its strongest: 40 s of `shut:append` and nothing else. There is no
    aliasing ratio to compute, and the printer says so rather than printing 0."""
    seq, reach, n, flips, pairs, _ = run([("shut:append", 416)], hz=10.4)
    return seq, reach, n, flips, pairs, n / 40.0


# ==========================================================================
# MOVETAP -- the tap's own closing block (PROBE-GATEFIRE.md step 13)
# ==========================================================================

@fixture("FIX-01", "movetap.fence_verdict: STRAIGHT / H1 confirmed, 402 shut:append "
                   "+ 162 test-runs over n=564")
def _fix_01():
    seq, reach, n, flips, pairs, rate = _seq01()
    return movetap.fence_verdict(reach, flips, pairs, n, rate, seq)


@fixture("FIX-01b", "movetap.gate1_verdict: clean -- above 489 / below 61 / "
                    "undecided 14, both early-outs zero")
def _fix_01b():
    _seq, _reach, n, _f, _p, _rate = _seq01()
    g1, why = gate1_split(n, above=489, below=61, band=9, plane=5)
    return movetap.gate1_verdict(g1, why, {False: n}, {False: n}, n)


@fixture("FIX-02", "movetap.fence_verdict: block A with ALL FOUR labels, a real "
                   "unread, and both poll-produced-no-row markers")
def _fix_02():
    seq, reach, n, flips, pairs, rate = _seq02()
    return movetap.fence_verdict(reach, flips, pairs, n, rate, seq)


@fixture("FIX-02b", "movetap.gate1_verdict: early_out_a FIRED (the *** line), with "
                    "unread sentinels in both tallies")
def _fix_02b():
    _seq, _reach, n, _f, _p, _rate = _seq02()
    g1, why = gate1_split(n, above=n - 74 - 11, below=74, band=7, plane=4)
    return movetap.gate1_verdict(
        g1, why,
        {False: n - 31 - 6, True: 31, "unread:agent-block-short": 6},
        {False: n - 6, "unread:agent-block-short": 6}, n)


@fixture("FIX-03", "movetap.fence_verdict: WIGGLE / H2 shape, test-runs 90.1%, "
                   "median REFUSED (both runs censored)")
def _fix_03():
    seq, reach, n, flips, pairs, rate = _seq03()
    return movetap.fence_verdict(reach, flips, pairs, n, rate, seq)


@fixture("FIX-03b", "movetap.gate1_verdict: below-dominant, the H2 half")
def _fix_03b():
    _seq, _reach, n, _f, _p, _rate = _seq03()
    g1, why = gate1_split(n, above=39, below=511, band=10, plane=4)
    return movetap.gate1_verdict(g1, why, {False: n}, {False: n}, n)


@fixture("FIX-04", "movetap.fence_verdict: THE UNREAD REFUSAL at 29%, rc 1")
def _fix_04():
    seq, reach, n, flips, pairs, rate = _seq04()
    return movetap.fence_verdict(reach, flips, pairs, n, rate, seq)


@fixture("FIX-05", "movetap.fence_verdict: THE ALIASING REFUSAL, A = 1.02, rc 1")
def _fix_05():
    seq, reach, n, flips, pairs, rate = _seq05()
    return movetap.fence_verdict(reach, flips, pairs, n, rate, seq)


@fixture("FIX-06", "movetap.fence_verdict: single-state STRAIGHT block, 0 flips, so "
                   "there is NO aliasing ratio to compute")
def _fix_06():
    seq, reach, n, flips, pairs, rate = _seq06()
    return movetap.fence_verdict(reach, flips, pairs, n, rate, seq)


@fixture("FIX-06b", "movetap.gate1_verdict: above-dominant")
def _fix_06b():
    _seq, _reach, n, _f, _p, _rate = _seq06()
    g1, why = gate1_split(n, above=402, below=8, band=4, plane=2)
    return movetap.gate1_verdict(g1, why, {False: n}, {False: n}, n)


@fixture("FIX-07", "movetap.fence_verdict: `reach` empty -- no sample carried the "
                   "field at all, and it refuses rather than printing a zero")
def _fix_07():
    return movetap.fence_verdict({}, 0, 0, 0, 0.0, [])


@fixture("FIX-07b", "movetap.gate1_verdict: `g1` empty -- same, and it says the "
                    "fence verdict above is unaffected")
def _fix_07b():
    return movetap.gate1_verdict({}, {}, {}, {}, 0)


@fixture("FIX-08", "movetap.gate1_verdict: THE ASYNC-TWIN REFUSAL at 30%, rc 1")
def _fix_08():
    n = 500
    g1 = {movetap.GATE1_ABOVE: 280, movetap.GATE1_BELOW: 55,
          movetap.GATE1_UNDECIDED: 15,
          "unread:async-slot-null": 90, "unread:async-id-mismatch": 60}
    assert sum(g1.values()) == n
    return movetap.gate1_verdict(g1, {"band": 11, "plane-mismatch": 4},
                                 {False: n}, {False: n - 12, True: 12}, n)


@fixture("FIX-09", "movetap.fence_verdict called with no `seq`: EPISODES not computed")
def _fix_09():
    _seq, reach, n, flips, pairs, rate = _seq01()
    return movetap.fence_verdict(reach, flips, pairs, n, rate)


@fixture("FIX-10", "movetap.print_episodes standalone: four labels + drop markers")
def _fix_10():
    seq, _reach, _n, _f, _p, rate = _seq02()
    return movetap.print_episodes(seq, rate)


@fixture("FIX-10b", "movetap.print_episodes on an empty sequence")
def _fix_10b():
    return movetap.print_episodes([], None)


# ==========================================================================
# MOVESYNC -- the secondary cross-tab (PROBE-GATEFIRE.md step 14)
# ==========================================================================

def sample_row(t, reach, head, cache):
    return {"t": round(t, 4), "live": [0.0, 0.0, 0],
            movesync.FENCE_KEY: reach,
            "state_record": movesync._rec(head, cache=cache)}


def free_block(hz=10.4, seconds=300.0, seed=4242):
    """A 300 s FREE block: the sample stream, and the paired subset.

    The fence is mostly shut with short open bursts; a world-1 stretch carries
    both of the labels the document's old quoted table omitted. The history head
    advances on an append about every 2.6 s and returns to 0 on a Clear, which
    is what the appender witness reads.
    """
    rng = random.Random(seed)
    dt = 1.0 / hz
    n = int(seconds * hz)
    states = []
    while len(states) < n:
        shut = rng.randint(70, 260)
        opn = rng.randint(6, 40)
        states += ["shut:append"] * shut + ["test-runs"] * opn
    states = states[:n]
    # THE WORLD-1 STRETCH, spliced at a fixed index. `world1:append` and
    # `shut:noop` are the two labels the old §6 table omitted, and an operator
    # who has never seen them printed will not know the table has four rows.
    states[900:930] = ["world1:append"] * 12 + ["shut:noop"] * 18
    S, head, cache = [], 1, 100
    since = 0.0
    for k, st in enumerate(states):
        t = k * dt
        since += dt
        if since >= 2.6 and st in ("shut:append", "world1:append"):
            head += 1
            cache += 7
            since = 0.0
        # Two Clears, mid-run, with the fence state UNCHANGED across the pair:
        # this is arm (b), the aliasing witness that does not depend on the
        # state field whose aliasing is the question.
        if k in (1477, 2603):
            head = 0
        S.append(sample_row(t, st, head, cache))
    pairs = [(S[k]["t"], [0.0, 0.0], S[k], 0.0) for k in range(0, n, 8)]
    return S, pairs


def pick_jumps(pairs, want_reachable, want_fenced, seed=7):
    """Jump rows whose BEFORE cell is the state we asked for.

    The BEFORE cell is the PREVIOUS paired sample, so the row is chosen by
    looking at `pairs[i-1]` -- exactly the way `fence_at_jumps` reads it.
    """
    rng = random.Random(seed)
    by_state = {"reachable": [], "fenced": []}
    for i in range(1, len(pairs)):
        b = movesync.classify_reach(pairs[i - 1][2].get(movesync.FENCE_KEY))
        if b in by_state:
            by_state[b].append(i)
    idx = (rng.sample(by_state["reachable"], want_reachable)
           + rng.sample(by_state["fenced"], want_fenced))
    rows = []
    for i in sorted(idx):
        t = pairs[i][0]
        step = round(600.0 + 480.0 * ((i * 37) % 11), 1)
        rows.append((t, step, step * 1.05, 22.0, 0.19))
    return rows


@fixture("FIX-11", "movesync.print_fence in full: four-label distribution WITH the "
                   "bucket column, 9 jump rows, 1 reachable / 8 fenced / 0 unread, "
                   "and a MEASURING appender witness")
def _fix_11():
    samples, pairs = free_block()
    return movesync.print_fence(pairs, pick_jumps(pairs, 1, 8), samples=samples)


@fixture("FIX-12", "movesync.print_fence: PARTIAL line + pre-rename `:apply` NOTE + "
                   "the jump-tally REFUSAL at 38%")
def _fix_12():
    # 200 paired samples of which 150 carry the field (PARTIAL), 40 of those in
    # movetap's pre-rename `shut:apply` spelling (NOTE), 10 unread (6.7%, under
    # the population bar) -- and 8 jump rows of which 3 land on a sample with no
    # field at all, which is 37.5% and trips the jump bar.
    P = []
    for k in range(200):
        t = k * 0.25
        if k % 4 == 3:
            P.append((t, [0.0, 0.0], {"t": t, "live": [0.0, 0.0, 0]}, 0.0))
            continue
        if k % 15 == 7:
            v = "unread:agent-id-mismatch"
        elif k % 3 == 0:
            v = "shut:apply"                       # movetap's PRE-RENAME spelling
        elif k % 11 == 5:
            v = "test-runs"
        else:
            v = "shut:append"
        P.append((t, [0.0, 0.0],
                  {"t": t, "live": [0.0, 0.0, 0], movesync.FENCE_KEY: v}, 0.0))
    # Row indices chosen by what the PREVIOUS paired sample carries, because the
    # BEFORE cell is that sample: three land after a row with no field at all
    # (3 of 8 = 37.5%, over the 25% bar), one after `test-runs`, four after a
    # fenced state -- two of them in the pre-rename spelling.
    J = [(P[i][0], 700.0 + 90.0 * j, 900.0, 30.0, 0.2)
         for j, i in enumerate([4, 6, 7, 10, 14, 16, 18, 28])]
    return movesync.print_fence(P, J, samples=None)


@fixture("FIX-13", "movesync.print_fence: the POPULATION refusal at 30%, zero jumps, "
                   "and the paired-subset witness population named because "
                   "samples=None")
def _fix_13():
    P = []
    for k in range(240):
        t = k * 0.25
        v = ("unread:agent-id-mismatch" if k % 10 < 3
             else ("test-runs" if k % 7 == 0 else "shut:append"))
        s = {"t": t, "live": [0.0, 0.0, 0], movesync.FENCE_KEY: v,
             "state_record": movesync._rec(1 + k // 20, cache=50 + k // 20)}
        P.append((t, [0.0, 0.0], s, 0.0))
    return movesync.print_fence(P, [], samples=None)


_ROWS_14 = [(12.500, 1968.9, "test-runs", "shut:append"),
            (34.750, 971.2, "shut:append", "shut:append"),
            (51.000, 3166.2, "shut:append", "test-runs"),
            (77.250, 2016.6, "world1:append", "shut:append"),
            (98.500, 838.6, "shut:append", "shut:append"),
            (120.750, 3405.3, "shut:noop", "shut:append"),
            (141.000, 1204.0, "shut:append", "shut:append"),
            (166.250, 655.5, "test-runs", "shut:append"),
            (190.500, 2740.1, "shut:append", "shut:append")]


@fixture("FIX-14", "movesync.print_jump_tally standalone, with its sentence")
def _fix_14():
    return movesync.print_jump_tally(_ROWS_14)


@fixture("FIX-14b", "movesync.print_jump_tally over zero rows")
def _fix_14b():
    return movesync.print_jump_tally([])


@fixture("FIX-14c", "movesync.print_jump_tally: one hole in nine rows (11%), under "
                    "the 25% bar, so the sentence still prints")
def _fix_14c():
    return movesync.print_jump_tally(
        [(t, st, ("unread:agent-id-mismatch" if i == 4 else be), at)
         for i, (t, st, be, at) in enumerate(_ROWS_14)])


@fixture("FIX-15", "movesync.print_appender_witness standalone, with the PARTIAL line")
def _fix_15():
    # 400 samples at 10.4 Hz; 30 of them carry no record at all on one side, so
    # the PARTIAL line prints and those pairs enter NEITHER arm.
    W = []
    h, c = 1, 40
    for k in range(400):
        t = k / 10.4
        st = "shut:append" if k % 97 else "test-runs"
        if k % 27 == 0:
            h += 1
            c += 3
        if k in (150, 311):
            h = 0
        if 200 <= k < 230:
            W.append({"t": round(t, 4), movesync.FENCE_KEY: st})   # no record
        else:
            W.append(sample_row(t, st, h, c))
    return movesync.print_appender_witness(W)


@fixture("FIX-15b", "movesync.print_appender_witness: refusal, no fields on either side")
def _fix_15b():
    return movesync.print_appender_witness(
        [{"t": k / 10.4, movesync.FENCE_KEY: "shut:append"} for k in range(60)])


@fixture("FIX-15c", "movesync.print_appender_witness: refusal, one sample is not a pair")
def _fix_15c():
    return movesync.print_appender_witness([sample_row(0.0, "shut:append", 1, 2)])


# ==========================================================================
# THE OBSERVED BLOCKS -- real stdout over real vault captures
# ==========================================================================
#
# These two are NOT fixtures and must never become fixtures. They are the only
# blocks in §6 that are measurements, and both show the post-C9 instrument
# REFUSING BY NAME on a pre-C9 capture, which is what an operator sees on day
# one. Reproduced by running the exact command the document prints.
#
# The vault is gitignored and a bare machine does not have one, so the test
# declares a SKIP rather than inventing a pass when a capture is missing.

GAMESRV = ("captures", "gamesrv", "authsrv-20260819T145717-c1.jsonl")
MOVETAP_CAP = ("captures", "movetap", "movetap-20260819T145939.jsonl")

OBSERVED = {
    "REAL-02": {
        "what": "movesync paired, movetap-20260819T145939 x authsrv-20260819T145717-c1: "
                "the day-one degrade path -- all three fence lanes refuse by name",
        "needs": (MOVETAP_CAP, GAMESRV),
        "argv": lambda p: ["--movetap", p[0], "--capture", p[1]],
    },
    "REAL-01": {
        "what": "movesync --wire-only over authsrv-20260819T145717-c1: prints NO fence "
                "section at all, because print_wire_only is a separate printer",
        "needs": (GAMESRV,),
        "argv": lambda p: ["--wire-only", "--capture", p[0]],
    },
}


# ==========================================================================
# WHICH BLOCK OF THE DOCUMENT EACH ONE IS
# ==========================================================================
#
# §6 holds fifteen fenced blocks with no language tag, in this order. Two of the
# document's numbered blocks print two fences (block 6's fence + gate-1 pair,
# block 10's pair of dead-instrument refusals), which is why the list is longer
# than the document's numbering.
#
# `tier` here is this module's SECOND witness. The test also reads the tier out
# of the document's own prose, and the two must agree -- so a block relabelled
# in the document without a corresponding change here goes red instead of
# quietly dropping out of scrutiny. That matters most for RECONSTRUCTION: the
# old §6 carried that label on a block nobody ever regenerated, and the label
# read as a licence rather than as a debt.

DOC_BLOCKS = (
    dict(block="Block 1",  tier="FIXTURE-DRIVEN", source="FIX-01"),
    dict(block="Block 2",  tier="FIXTURE-DRIVEN", source="FIX-01b"),
    dict(block="Block 3",  tier="FIXTURE-DRIVEN", source="FIX-06"),
    dict(block="Block 4",  tier="FIXTURE-DRIVEN", source="FIX-02"),
    dict(block="Block 5",  tier="FIXTURE-DRIVEN", source="FIX-02b"),
    dict(block="Block 6a", tier="FIXTURE-DRIVEN", source="FIX-03"),
    dict(block="Block 6b", tier="FIXTURE-DRIVEN", source="FIX-03b"),
    dict(block="Block 7",  tier="FIXTURE-DRIVEN", source="FIX-05"),
    dict(block="Block 8",  tier="FIXTURE-DRIVEN", source="FIX-04"),
    dict(block="Block 9",  tier="FIXTURE-DRIVEN", source="FIX-08"),
    dict(block="Block 10a", tier="FIXTURE-DRIVEN", source="FIX-07"),
    dict(block="Block 10b", tier="FIXTURE-DRIVEN", source="FIX-07b"),
    dict(block="Block 11", tier="FIXTURE-DRIVEN", source="FIX-11"),
    dict(block="Block 12", tier="OBSERVED",       source="REAL-02"),
    dict(block="Block 13", tier="OBSERVED",       source="REAL-01"),
)

# Fixtures that exist but are NOT quoted in the document. They are still
# rendered and still checked for determinism, because they are the ones a future
# §6 edit will reach for, and a fixture that has rotted since it was written is
# worse than one that was never there.
UNQUOTED = tuple(n for n in _ORDER
                 if n not in {b["source"] for b in DOC_BLOCKS})


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--list", action="store_true", help="every fixture and what it is")
    ap.add_argument("--write", metavar="DIR",
                    help="write every fixture to DIR as <name>.txt")
    ap.add_argument("--show", metavar="NAME", help="print one fixture to stdout")
    a = ap.parse_args(argv)

    if a.show:
        rc, text = render(a.show)
        sys.stdout.write(text)
        return 0

    if a.list or not a.write:
        quoted = {b["source"]: b["block"] for b in DOC_BLOCKS}
        for name in _ORDER:
            where = quoted.get(name, "-- not quoted in the document --")
            print(f"{name:8s}  {where:12s}  {what(name)}")
        for name, spec in OBSERVED.items():
            print(f"{name:8s}  {quoted.get(name, '?'):12s}  {spec['what']}")
        return 0

    os.makedirs(a.write, exist_ok=True)
    for name in _ORDER:
        rc, text = render(name)
        path = os.path.join(a.write, name + ".txt")
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        print(f"[{name}] rc={rc}  {len(text.splitlines())} line(s) -> {path}")
    print(f"\n{len(_ORDER)} fixture(s) -> {a.write}")
    print("The OBSERVED blocks are NOT written here: they are real stdout over "
          "vault captures.\nRe-derive them with the commands the document itself "
          "prints in §6 blocks 12 and 13.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
