#!/usr/bin/env python3
r"""The guard on `grantsim.py` -- and it refuses to let that file become a ranker.

    python toolkit/clientscan/test_grantsim.py

`REALFIX.md` §2.6's calibration gates REALFIX-C0..C5, §2.7's structural asserts,
and the three refusals that must go red. Nothing here launches a client, opens a
socket or writes a byte; §C0 reads the pinned client image and §C1-§C5 read vault
captures, and every section that needs one declares `LEDGER.skip` without it.

THE HEADLINE IS THE CALIBRATION, not the counterfactual. §C2 requires reproducing
the measured hard-jump census on eleven `ours` captures across five
configurations -- 60 measured -- and the check that separates this from its own
first draft is §C2(a): **exactly zero** on the three captures that sent zero
grants, where round 5's separation-only scorer predicted 16, 12 and 34.

TWO ADAPTATIONS OF §2.6, both pre-authorized and both recorded here rather than
only in prose:

**(1) §C2(b)'s "golden fixture capture" is a COMMITTED EXPECTED-COUNT VECTOR.**
The spec asks for a fixture capture with an expected per-capture vector, because
two independent implementations of the same written specification gave 69 and 80
against 60 measured and a `[0.7,1.5]x` band drawn after seeing 1.15 swallows
both. Committing a capture is refused -- the vault is personal data from the
owner's own account and never enters the repo -- so the fixture is split:
`SYNTHETIC` below is a minimal capture this file BUILDS, carrying the structural
behaviour, and `C2_EXPECTED` is the per-capture vector as NUMBERS ONLY, keyed by
stamp. **`C2_EXPECTED` IS IMPLEMENTATION-PINNED.** It is what `grantsim.py`
does, not what `REALFIX.md` §2.3 entails; round 5 §6.2's own resolution is "pin
the spec to a golden fixture or say the number is implementation-dependent" and
this is the second of those said out loud. It is still worth having: it is the
only thing that would notice this file quietly changing its answer.

**(2) §C3 HAS TWO ARMS AND THEY REST ON DIFFERENT EVIDENCE.**
`_heading_grant_ok` LANDED 2026-08-21 with REALFIX-P2's `--zero-lead`, so the
skip that stood here is gone: §6b imports the shipped predicate and the lead
policies apply it as their rate limit. What is still asymmetric is what each arm
can be checked against. §6 replays two captures' own recorded `grant_verdict`
rows, reason for reason. §6b cannot -- no capture in any vault holds a
heading-arm row, because the flag has never been run -- so it drives BOTH arms
of the real predicate against hand-computed expectations on the SYNTHETIC
stream, and its banner says so. **The first REALFIX-L1 capture upgrades §6b to a
message-level replay** pinned exactly as §6's 195137/195315 gate is;
`replay_verdicts` already skips heading rows, so that capture cannot silently
redden the click arm when it arrives.

WHAT §C3 DOES DO, and it is the reason `grantsim.py` imports a server module at
all: it replays `20260820T195137`'s 199 `grant_verdict` rows and
`20260820T195315`'s 154 (152 `locally-moving` + 2 `grant`) through
`authsrv._grant_verdict` ITSELF and asserts exact reproduction, reason for
reason, against the 199 and 2 `0x0029` those captures actually sent. The
predicate's own docstring says it was made pure so an offline scorer could run
the decision rather than a paraphrase that agrees with it by construction, and
§C3 carries a NEGATIVE CONTROL -- the same replay with the flag the other way
round must NOT reproduce `195315` -- so "it agreed" is a result rather than a
tautology.

**§C4 IS WHERE THE INSTRUMENT ADMITS WHAT IT CANNOT SEE.** Deleting the match
test takes 69 to 122 (1.77x) and rotating destinations inflates monotonically
(69/73/99/133 at k = 0/1/5/17) -- but shifting every grant by +0.35 s, destroying
causality outright, scores **60, dead on the measured total**. So the shift null
is gated per capture at +3.0 s only and the +0.35 s failure is PRINTED. And at
matched perturbation scale this file is not "strong on geometry, weak on
cadence": rotate-1 is +5.8% and shift-(-0.35 s) is +10.1%, which §C4 asserts stay
within one order of each other so that the manufactured asymmetry cannot come
back.

**§C5 IS THE REFUSAL.** The band is window {2.5,5,10} s x radius {50,100,200} u x
gate {250,299.33,400} u x MATCH-TEST {ON,OFF} -- 54 cells -- and the fourth axis
is the one the drafted sweep never varied and the one the ranking is not
invariant on. With the match test on, lead 766 is worst everywhere; with it off
it WINS. `rank_or_refuse()` therefore returns None on the real substrate, and
§C5 asserts BOTH directions: None here, and a real ordering on a synthetic band
where one genuinely is invariant, so the refusal is not vacuous.

NO VAULT, NO SOCKET, NO CLIENT for §1-§2; the rest declares what it could not do.
"""
import contextlib
import io
import json
import math
import os
import shutil
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import checks                                                  # noqa: E402
import origin                                                  # noqa: E402
import vaultpath                                               # noqa: E402
import grantsim as GS                                          # noqa: E402
import movesync                                                # noqa: E402

# TWO FLOORS, ONE PER FIXTURE CONFIGURATION, and BOTH MEASURED from a real
# green run on 2026-08-21 rather than enumerated.
#
# `FLOOR_BARE` 19 is what §1 (structural, 10) and §2 (refusals, 9) execute with
# `RURIK_VAULT` pointing at a directory that does not exist: they build their own
# fixtures and read neither the vault nor the client. That run scores
# `ALL CHECKS PASSED (19 checks, 8 declared skip(s))`.
#
# `FLOOR_FULL` 61 is the vaulted total -- §C0 5, §C1 9, §C2 8, §C3 6, §C4 8,
# §C5 4, §M 2 on top of the 19 -- and it is RAISED below once the fixture probes
# have answered, because excess over a floor is not an error in `checks.py` and
# a single bare-machine floor therefore protects none of the 42 checks that only
# a full machine runs. That is not hypothetical: an audit replaced C2(a)'s
# `for s in GS.STRUCTURAL_ZEROS:` with `for s in []:` on a machine with every
# fixture present, deleting the three checks the whole calibration turns on, and
# the run still printed ALL CHECKS PASSED. `test_bit31.py` raises its floor
# mid-run for the same reason and after the same finding.
#
# Set from what a run PRODUCES and never from the enumeration: `REALFIX.md`
# §2.7's own "~44" is an expectation and CLAUDE.md is explicit that shipping the
# enumerated literal is the mistake. The real count came out higher than the
# expectation because every refusal here carries a positive control beside it.
#
# 2026-08-21, LATER THE SAME DAY: `_heading_grant_ok` landed in `authsrv.py`
# with REALFIX-P2's `--zero-lead`, so §C3's heading skip became §6b -- five
# checks that drive the SHIPPED predicate. It reads neither the vault nor the
# client (it imports authsrv, builds nothing and opens nothing), so all five
# land in the bare-machine subset: 19 -> 24 and 61 -> 66. BOTH re-measured from
# real green runs of their own configuration -- 24 with `RURIK_VAULT` pointing
# at a directory that does not exist, 66 with every fixture present -- and
# neither is 19+5 done in anyone's head.
#
# 2026-08-21, AFTER REVIEW: §6b gained two checks and lost none. Its old
# "negative control" counted the moving headings and compared them against a
# count the check above it already pinned, so it could not fail independently;
# it is now a real control (the verdict hook rebound to always fire, and the
# same stream must grant all six). Beside it went a lock that the POLICY runs
# the shipped predicate rather than a paraphrase of it -- perturb the server's
# own GRANT_MIN_INTERVAL and the grant instants must follow -- and a driven
# exercise of `replay_verdicts`'s heading-row filter, which had no capture in
# any vault to filter and was therefore dead source. All three are fixture-free,
# so both floors move by the same 2: 24 -> 26 and 66 -> 68, each re-measured
# from a green run of its own configuration.
#
# 2026-08-21, REALFIX-F1b: section 10 (the field-4 pre-screen) added 15 -- 2
# fixture-free (the three policies driven against a hand-built grant stream,
# proving the replay can tell them apart at all) and 13 that need both the
# gamesrv captures and the movetap taps. So the floors move by DIFFERENT
# amounts, which is the case the two-floor split exists for: 26 -> 28 bare,
# 68 -> 81 vaulted. Both re-measured from green runs of their own configuration
# -- 81 with every fixture present, 28 with `RURIK_VAULT` pointing at a
# directory that does not exist, which also printed its 8 declared skips.
#
# 2026-08-21, AFTER THE F1b MUTATION LANE: section 10 gained 5 -- 2 fixture-free
# (FIELD4_SCREEN's diagonal against FIELD4_MEASURED / FIELD4_F1B_EXPECTED, and
# its coverage of FIELD4_PAIRS) and 3 vaulted (the six-cell screen against the
# live computation, and the pairing window bracketed against each capture's own
# cadence). Two of the three survivors that lane found were the server banner's
# counterfactual table, which no test in the tree read; the screen constant and
# these checks are what `test_position_trust.py` §16 now ties that banner to.
# 28 -> 30 bare, 81 -> 86 vaulted, each re-measured from a green run of its own
# configuration.
FLOOR_BARE = 30
FLOOR_FULL = 86
LEDGER = checks.Ledger("grantsim: the offline grant-policy harness, "
                       "and its refusal to rank", floor=FLOOR_BARE)
check = checks.adopt(LEDGER)


def have(*parts):
    try:
        vaultpath.require_dir(*parts)
        return True
    except SystemExit:
        return False


HAVE_GAMESRV = have("captures", "gamesrv")
HAVE_MOVETAP = have("captures", "movetap")
try:
    HAVE_EXE = bool(GS.read_sqrt_lut()[0])
except BaseException:                                          # noqa: BLE001
    HAVE_EXE = False

# THE FLOOR FOLLOWS THE FIXTURES. Every section below either runs in full or
# declares a skip, so with all three fixtures present the count is not variable
# and FLOOR_FULL is a floor rather than a hope. (This sentence carried the
# literal 61 for a day after the constant had moved to 66, which is why it now
# names the constant instead of restating its value.) Any other configuration keeps
# `FLOOR_BARE`, which is the protection those configurations already had -- a
# floor for a mixed machine would have to be set from a run of that machine, and
# this one cannot produce it without hiding a fixture from itself.
if HAVE_GAMESRV and HAVE_MOVETAP and HAVE_EXE:
    LEDGER.floor = FLOOR_FULL


def ratio(a, b):
    """`a / b`, but a degenerate denominator PRINTS instead of killing the run.

    A detail string is evaluated BEFORE `check()` records anything, so a bare
    `a / b` inside one turns a failing check into a traceback with no verdict
    banner and no floor evaluation -- the operator gets a stack instead of a
    named failure, and `checks.py`'s whole rule stops applying to the run. That
    is not hypothetical: forcing the match test to always match takes every
    total to zero, and C2(c)'s `hi / lo` then died three sections before the
    verdict. `inf` and `nan` format fine and both are honest.
    """
    if b:
        return a / b
    return float("nan") if not a else float("inf")


def captured(fn, *a, **kw):
    """(return value, printed text). A printer's OUTPUT is part of what it asserts."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        out = fn(*a, **kw)
    return out, buf.getvalue()


# =========================================================================
# The synthetic minimal capture -- adaptation (1), the structural half
# =========================================================================

def _grant_bytes(x, y, agent=movesync.PLAYER_AGENT):
    """A `0x0029` payload the way `movesync.load_grants` reads it: from the BYTES."""
    return struct.pack("<HIff", movesync.OP_MOVE_TO_POINT, agent,
                       float(x), float(y)).hex()


def write_synthetic(path, *, clicks=True):
    """A capture with six reports at run speed, one click, one stop, two grants.

    Deliberately TINY and deliberately real: it goes through
    `origin.origin_of`, `movesync.load_wire_reports`, `movesync.load_grants`,
    `resyncscore.track_from_capture` and `grantsim.c2s_moves` unmodified, so a
    reader that stops matching the shape of a real capture fails here rather
    than in a section that needs the vault.
    """
    rows = [{"kind": "origin", "origin": origin.OURS,
             "produced_by": "test_grantsim (synthetic fixture)",
             "server": "127.0.0.1:6112", "client": "127.0.0.1:50001", "t": 0.0,
             "wall": "2026-08-20T00:00:00Z"},
            {"kind": "key_exchange_ok", "t": 0.0}]
    for i in range(6):
        t = 0.25 * i
        rows.append({"kind": "decoded", "opcode": GS.OP_HEADING,
                     "name": "MOVE_SET_HEADING",
                     "values": [1000 + i, [72.0 * i, 0.0], 0, [766.0, 0.0], 7],
                     "t": t, "wall": "2026-08-20T00:00:00Z"})
    if clicks:
        rows.append({"kind": "decoded", "opcode": GS.OP_CLICK,
                     "name": "MOVE_TO_COORD",
                     "values": [1100, [900.0, 0.0], 0], "t": 0.60,
                     "wall": "2026-08-20T00:00:00Z"})
    rows.append({"kind": "decoded", "opcode": GS.OP_STOP,
                 "name": "MOVE_CANCEL_REPORT_POSITION",
                 "values": [1200, [360.0, 0.0], 0], "t": 1.50,
                 "wall": "2026-08-20T00:00:01Z"})
    for t, x in ((0.30, 200.0), (0.80, 400.0)):
        rows.append({"kind": "sent", "opcode": movesync.OP_MOVE_TO_POINT,
                     "plain": _grant_bytes(x, 0.0), "t": t,
                     "wall": "2026-08-20T00:00:00Z"})
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    return path


def write_live_stub(path):
    """A capture that classifies as `live`, so the pooling refusal has something to refuse."""
    rows = [{"kind": "origin", "origin": origin.LIVE,
             "produced_by": "test_grantsim (synthetic control)",
             "connection": "10.0.0.9:51000->54.164.212.177:6112", "t": 0.0}]
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    return path


TMP = tempfile.mkdtemp(prefix="rurik-grantsim-")
SYNTHETIC = write_synthetic(os.path.join(TMP, "authsrv-20260820T000000-c1.jsonl"))
LIVE_STUB = write_live_stub(os.path.join(TMP, "authsrv-20260820T000001-c1.jsonl"))


def main():
    # =====================================================================
    print("1. structural asserts -- REALFIX.md sec. 2.7, on the synthetic fixture")
    # =====================================================================
    # A straight run at exactly RUN_SPEED, so every leg's arithmetic is
    # checkable by hand rather than only by the code that produced it.
    reps = [(0.25 * i, [72.0 * i, 0.0]) for i in range(9)]

    # (a) THE <= 1.0 u SHORT-CIRCUIT DISPATCHES NOTHING. 0x005FEA92 writes
    #     +0x78 = D, zeroes the velocity, arms +0x48 = now+1 and returns, with
    #     no path to 0x005FEBEB nor to the child-bake/collision/arrival fan-out.
    near = GS.simulate(reps, [(0.30, (0.5, 0.0))])
    check(near["n_instants"] == 0 and near["zero_arm"] == 1,
          "a grant within 1.0 u of the copy produces NO test instant",
          f"instants={near['n_instants']} zero_arm={near['zero_arm']} -- if this "
          f"goes non-zero the <=1.0 u arm has grown a dispatch it does not have, "
          f"and REALFIX-P2's whole cheapness argument goes with it")
    far = GS.simulate(reps, [(0.30, (200.0, 0.0))])
    check(far["n_instants"] >= 1 and far["zero_arm"] == 0,
          "CONTROL: a grant further than 1.0 u DOES produce one",
          f"instants={far['n_instants']} -- without this, check (a) would pass "
          f"on a simulator that produces no instants at all")

    # (b) THE COPY PARKS ON ARRIVAL. A 200 u leg at 288 u/s matures 694 ms
    #     later (trunc(200*1000/288) = 694), and the arrival is a class-B
    #     instant at exactly that time.
    #
    #     THE EXPECTATION IS HARD-CODED, and that is the whole point of the
    #     line. It used to read `0.30 + int(200.0 * 1000.0 / GS.COPY_SPEED)`,
    #     which restates the implementation with the same expression and the
    #     same constant it is checking: an audit moved COPY_RATE from 1.0 to
    #     0.9 -- a 1.11x error in the operand of BOTH tests -- and this check
    #     stayed green, because its expectation moved with the defect. 0.994 s
    #     is what 288.0 u/s produces and nothing else does.
    arr = [r for r in far["instants"] if r["kind"] == "arrival"]
    check(len(arr) == 1 and abs(arr[0]["t"] - 0.994) < 1e-9
          and abs(arr[0]["q"][0] - 200.0) < 1e-6,
          "the copy PARKS on arrival, at the destination and at +0x48",
          f"{[(round(r['t'], 4), [round(v, 2) for v in r['q']]) for r in arr]} "
          f"want t=0.9940 q=[200.0, 0.0] -- 0.30 s + trunc(200 u / 288.0 u/s), "
          f"the literal the client's own [+0x60]*[+0x5C] produces")
    #     ...and the tick TRUNCATES rather than rounding, which the 200 u leg
    #     cannot see: 200,000/288 = 694.44 and trunc and round agree there by
    #     luck. 150 u is 520.833 ms -- trunc 520, round 521 -- so this second
    #     leg is the one that pins `0x005FEB2E`'s float->int helper against the
    #     alternative. Swapping `int(...)` for `int(round(...))` in the bake
    #     leaves every other check in this file green.
    frac = GS.simulate(reps, [(0.30, (150.0, 0.0))])
    arr2 = [r for r in frac["instants"] if r["kind"] == "arrival"]
    check(len(arr2) == 1 and abs(arr2[0]["t"] - 0.820) < 1e-9,
          "and the arrival tick TRUNCATES the millisecond: 150 u -> 520 ms, "
          "never 521",
          f"t={arr2[0]['t'] if arr2 else None} want 0.8200 = 0.30 + 0.520; "
          f"150 u / 288.0 u/s = 520.833 ms, so rounding would land 0.821 and "
          f"a 259.2 u/s copy would land 0.878")

    # (c) INSTANTS >= |{grants with |d| > 1}|. Every such grant bakes, and the
    #     arrivals are on top -- which is what makes the count a FLOOR.
    grants = [(0.30, (200.0, 0.0)), (0.55, (400.0, 0.0)), (0.80, (600.0, 0.0)),
              (1.05, (600.4, 0.0))]
    many = GS.simulate(reps, grants)
    baked = sum(1 for r in many["instants"] if r["kind"] == "bake")
    check(many["n_instants"] >= baked >= len(grants) - many["zero_arm"],
          "instant count >= the number of grants that cleared the 1.0 u arm",
          f"instants={many['n_instants']} bakes={baked} grants={len(grants)} "
          f"zero-arm={many['zero_arm']} -- the count is a FLOOR: child recursion "
          f"and the bake's own fan-out multiply both classes")

    # (d) A SNAP RESEEDS AND MOVES armed_since. Grant a point 4,000 u away on a
    #     track that never went there: at the FIRST bake `q` is still on the
    #     client's own track and matches at distance 0 (the bake tests where the
    #     COPY is, not where it is being sent), so the snap arrives at the
    #     SECOND one, once the copy has glided off the polyline.
    off_track = [(0.30, (0.0, 4000.0)), (1.20, (0.0, 4100.0)),
                 (1.60, (0.0, 4200.0))]
    snapped = GS.simulate(reps, off_track)
    check(snapped["snaps"] and snapped["snaps"][0]["kind"] == "bake",
          "a grant far off the client's track SNAPS, at a class-A instant",
          f"{[(round(s['t'], 2), s['kind'], round(s['sep'], 1)) for s in snapped['snaps']]}")
    # AND THE TWO CHECKS BELOW REPORT THROUGH THE LEDGER WHEN THERE IS NO SNAP.
    # `snapped["snaps"][0]` used to be indexed unconditionally: forcing the
    # match test to always match fired the check above and then killed the run
    # with an IndexError, five checks in, with no verdict banner and no floor
    # evaluated. The exit code was still non-zero, so `run_suite.py` scored it
    # red -- but the operator got a traceback instead of a named failure, and
    # the floor rule cannot see a run that never reaches its verdict. Both
    # branches spend the same two checks and the run continues either way, so
    # neither the count nor the other eight sections depend on this one firing.
    kept = GS.simulate(reps, off_track, reseed=False)
    snap_t = snapped["snaps"][0]["t"] if snapped["snaps"] else None
    after = ([r for r in snapped["instants"] if r["t"] > snap_t]
             if snap_t is not None else [])
    after_off = ([r for r in kept["instants"] if r["t"] > snap_t]
                 if snap_t is not None else [])
    if not (after and after_off):
        why = (f"snaps={snapped['n_snaps']} instants after the snap={len(after)} "
               f"-- there is no post-snap instant to read the reseed off, so "
               f"both halves are unmeasurable; the check above names the cause")
        check(False, "the reseed moves armed_since: every instant after a snap "
                     "starts its chain AT the snap", why)
        check(False, "and the copy lands ON the client, not at the runaway point",
              why)
    else:
        before = [r for r in snapped["instants"] if r["t"] < snap_t]
        check(all(abs(r["win_lo"] - snap_t) < 1e-9 for r in after)
              and before and all(r["win_lo"] < snap_t for r in before),
              "the reseed moves armed_since: every instant after a snap starts "
              "its chain AT the snap",
              f"before={[round(r['win_lo'], 3) for r in before]} "
              f"after={[round(r['win_lo'], 3) for r in after]} snap at {snap_t:.2f} "
              f"-- 0x006060A2/0x006060A9 zero every agent's history head "
              f"unconditionally, so the whole roster's chain restarts here and the "
              f"next test cannot match against ground walked before it")
        #     ...and the OTHER half of the reseed: the copy lands on the client.
        #     Without it the post-snap instant would still carry the runaway leg.
        a_on, a_off = after[0], after_off[0]
        landed = GS.client_at(reps, [r[0] for r in reps], snap_t)
        check(math.hypot(a_on["q"][0] - landed[0], a_on["q"][1] - landed[1]) < 1e-6
              and a_on["sep"] < a_off["sep"],
              "and the copy lands ON the client, not at the runaway point",
              f"q at the next instant {[round(v, 1) for v in a_on['q']]} vs the "
              f"client's position at the snap {[round(v, 1) for v in landed]}; "
              f"separation {a_on['sep']:.1f} u with the reseed vs {a_off['sep']:.1f} "
              f"u without it")

    # (e) THE READERS STILL MATCH THE SHAPE OF A REAL CAPTURE.
    moves = GS.c2s_moves(SYNTHETIC)
    kinds = {m["op"] for m in moves}
    check(len(moves) == 8 and kinds == {GS.OP_HEADING, GS.OP_CLICK, GS.OP_STOP}
          and moves[0]["unit"] == (1.0, 0.0) and moves[0]["mt"] == 7,
          "c2s_moves keeps values[3] and values[4], which load_wire_reports drops",
          f"n={len(moves)} ops={sorted(kinds)} first unit={moves[0]['unit']} "
          f"mt={moves[0]['mt']}")
    wire, _walls, src = movesync.load_wire_reports(SYNTHETIC)
    check(len(wire) == 7 and src["heading"] == 6 and src["stop"] == 1
          and len(movesync.load_grants(SYNTHETIC)) == 2,
          "and movesync's own loaders read the same file unchanged",
          f"reports={len(wire)} source={src} grants="
          f"{len(movesync.load_grants(SYNTHETIC))}")

    # =====================================================================
    print("\n2. the refusals -- every one of them must go red on purpose")
    # =====================================================================
    # A refusal nobody has seen fire is a wish. Each of these breaks the rule
    # deliberately and asserts the raise, and each has a positive control so
    # "it raised" cannot be "it raises at everything".
    try:
        GS.require_ours([SYNTHETIC, LIVE_STUB])
        pooled = "did not raise"
    except origin.MixedCorpora as exc:
        pooled = str(exc)
    check("REFUSING to pool" in pooled,
          "pooling `ours` with `live` RAISES",
          f"{pooled[:90]!r} -- a consumer that pools origins is measuring "
          f"neither, and retail has no `ours` grant stream to counterfactual "
          f"against in the first place")
    check(GS.require_ours([SYNTHETIC]) == [SYNTHETIC],
          "CONTROL: an all-`ours` set passes through",
          "without this the refusal above could be refusing everything")

    try:
        GS.policy_named("P2-zerolad")
        named = "did not raise"
    except GS.Refused as exc:
        named = str(exc)
    check("no policy named" in named,
          "an unknown policy name RAISES rather than resolving to no grants",
          f"{named[:90]!r} -- 'no grants and therefore no snaps' is the most "
          f"comfortable wrong answer this file can give")
    check(GS.policy_named("P2-zerolead") is GS.policy_p2_zerolead,
          "CONTROL: a known name resolves")

    # THE LEAD SPINE, pinned by what each policy GRANTS rather than by the
    # attribute it advertises. C5's whole band, M1's identity argument and M2's
    # P3 number are all built on 0 / 86 / 766 u and NOTHING asserted it: an
    # audit handed P2 the 766 u lead and handed P3 39.92 u (by moving the
    # `- 14.0` in LEAD_FIXED) and all 57 checks stayed green -- while §9's M1
    # check printed "the match distance is 0 by IDENTITY" as its own evidence
    # beside a policy carrying a 766 u lead. The synthetic capture's six
    # headings all report at unit (1, 0), so `D[0] - pos[0]` IS the lead, and
    # 85.919968 is hard-coded because `MATCH_RADIUS - 14.0` is the arm of
    # LEAD_FIXED's `min()` that wins and recomputing it here would pin nothing.
    #
    # RE-PINNED 2026-08-21, and the pairing had to change with it. The synthetic
    # capture's six headings are 0.25 s apart, so the shipped
    # GRANT_MIN_INTERVAL = 0.50 s floor passes three of them (t = 0.00, 0.50,
    # 1.00) -- 6 -> 3 grants per policy. The old form zipped `got` against
    # `heads` POSITIONALLY, which is only correct while every report produces a
    # grant; keying on the report's own `t` is right under any rate limit.
    #
    # WHAT THE OLD FORM WOULD ACTUALLY HAVE DONE, corrected 2026-08-21 after
    # review, because the first version of this comment invented a near-miss.
    # It claimed the positional zip "silently paired grant 2 with report 2 and
    # reported a lead of 72.0 u for P2", i.e. that the file went green on a
    # wrong number. IT DID NOT. Measured both ways against the current
    # rate-limited policies: the zip yields offsets [0.0, 72.0, 144.0] for P2
    # (and [85.92, 157.92, 229.92] for P3, [766, 838, 910] for lead-766), so
    # `spine[0][1] == [0.0]` is FALSE and the check goes RED -- as does
    # `all(n == 6 ...)`, since each policy now grants 3. The pairing fix is
    # right and stays; the story that it caught a silent failure is withdrawn.
    # An invented near-miss is worth less than nothing: it is a claim about this
    # instrument's blind spots that the instrument does not have.
    heads = [m for m in moves if m["op"] == GS.OP_HEADING and m["mt"]]
    at_t = {m["t"]: m for m in heads}
    spine = []
    # MOVECODE-1z-cw: the 3-of-6 pin is the 0.5 s ARM's (--kbd-grant-floor 0.5);
    # the keyboard arm ships with no floor since 2026-09-09 (retail answers every
    # report), under which the same policies grant all six -- pinned beside it.
    _A = GS._authsrv()
    _saved_kf = _A.KBD_GRANT_FLOOR
    try:
        _A.KBD_GRANT_FLOOR = _A.GRANT_MIN_INTERVAL
        for pol in (GS.policy_p2_zerolead, GS.policy_p3_shortlead, GS.policy_p_endpoint):
            got = pol(moves)
            offs = sorted({round(D[0] - at_t[t]["pos"][0], 6)
                           for (t, D, _a, _b, _k) in got})
            spine.append((pol.lead, offs, len(got), sorted(t for t, *_ in got)))
    finally:
        _A.KBD_GRANT_FLOOR = _saved_kf
    shipped_n = [len(pol(moves)) for pol in (GS.policy_p2_zerolead, GS.policy_p3_shortlead,
                                             GS.policy_p_endpoint)]
    check(len(heads) == 6 and all(n == 3 for _l, _o, n, _t in spine)
          and all(ts == [0.0, 0.5, 1.0] for _l, _o, _n, ts in spine)
          and shipped_n == [6, 6, 6] and _A.KBD_GRANT_FLOOR == 0.0
          and spine[0][0] == 0.0 and spine[0][1] == [0.0]
          and abs(spine[1][0] - 85.919968) < 5e-7 and spine[1][1] == [85.919968]
          and spine[2][0] == 766.0 and spine[2][1] == [766.0],
          "the lead spine is 0 / 85.919968 / 766 u and each policy GRANTS at "
          "its own, three of six under the 0.5 s arm and six of six shipped (1z-cw)",
          f"{[(round(l, 6), o, n, ts) for l, o, n, ts in spine]} over "
          f"{len(heads)} moving headings 0.25 s apart -- P3's 85.919968 u is "
          f"MATCH_RADIUS - 14.0, the arm of min(RUN_SPEED * 0.30, "
          f"MATCH_RADIUS - 14.0) that wins, and the spine is the one axis C5's "
          f"band varies. RE-PINNED from 6 grants to 3 on 2026-08-21, when "
          f"`_heading_grant_ok` landed and the lead family stopped being "
          f"rate-limit-free: at a {GS._authsrv().GRANT_MIN_INTERVAL:.2f} s "
          f"floor the reports at t = 0.25 / 0.75 / 1.25 are DROPPED, not held")

    inverting = [{"cfg": {"match": True}, "totals": {0.0: 1, 766.0: 9}},
                 {"cfg": {"match": False}, "totals": {0.0: 9, 766.0: 1}}]
    invariant = [{"cfg": {"match": True}, "totals": {0.0: 1, 766.0: 9}},
                 {"cfg": {"match": False}, "totals": {0.0: 4, 766.0: 12}}]
    check(GS.rank_or_refuse(inverting) is None,
          "a band whose ordering INVERTS yields no ordering at all",
          "REALFIX.md sec. 2.6 C5: any ordering claim survives the full band "
          "including the match-test axis, or no ordering is printed")
    check(GS.rank_or_refuse(invariant) == (0.0, 766.0),
          "CONTROL: a band whose ordering holds everywhere DOES yield one",
          f"{GS.rank_or_refuse(invariant)} -- without this, the refusal above "
          f"would be a function that always returns None")
    tied = [{"cfg": {}, "totals": {0.0: 3, 766.0: 3}}]
    check(GS.rank_or_refuse(tied) is None,
          "ties everywhere are not an ordering either")

    try:
        GS.simulate([(0.0, [0.0, 0.0])], [])
        thin = "did not raise"
    except GS.Refused as exc:
        thin = str(exc)
    check("fewer than two client reports" in thin,
          "a capture with no polyline RAISES rather than scoring against a point",
          f"{thin[:80]!r}")

    # =====================================================================
    print("\n3. REALFIX-C0 -- the decision radius, re-derived from the binary")
    # =====================================================================
    if not HAVE_EXE:
        LEDGER.skip("C0 the radius derivation",
                    "the pinned client image is not in this vault; the match "
                    "radius and gate-1 cut cannot be re-derived, so both module "
                    "constants stand UNCHECKED for this run")
    else:
        m = GS.derive_match_radius()
        g = GS.derive_gate1_cut()
        check(m["first_fail_distsq"] == GS.MATCH_BOUNDARY_DISTSQ
              and m["scanned"] == 2048001
              and abs(m["true"] - 99.919968) < 5e-7,
              "the match test's first FAILING distSq is 9984.0f -> 99.919968 u",
              f"distSq={m['first_fail_distsq']!r} true={m['true']:.7f} "
              f"approx={m['approx']:.8f} over {m['scanned']:,} patterns; last "
              f"passing {m['last_pass_distsq']!r} true {m['last_pass_true']:.7f}")
        # THE POSITIVE CONTROL. A method that can only produce the number it was
        # pointed at is not a method: the identical scan over a different
        # 2,560,001-pattern window must reproduce a threshold this tree already
        # carries from an independent derivation.
        check(g["first_fail_distsq"] == GS.GATE1_BOUNDARY_DISTSQ
              and g["scanned"] == 2560001
              and abs(g["true"] - 299.332591) < 5e-7,
              "POSITIVE CONTROL: the same nine instructions give gate 1's "
              "89600.0f -> 299.332591 u",
              f"distSq={g['first_fail_distsq']!r} true={g['true']:.7f} over "
              f"{g['scanned']:,} patterns")
        check(g["snaps_at_300"] and abs(g["at_300"] - 300.18658447265625) < 1e-9,
              "and a true separation of EXACTLY 300.0 u snaps",
              f"the table sqrt of 90000.0 reads {g['at_300']:.8f} > 300.0 -- the "
              f"check with no free parameter")
        # ONE SCAN PREDICATE, TWO ASYMMETRIC CLIENT TESTS, and this is what
        # makes that safe. `_scan_boundary` looks for the first pattern with
        # `approx > cut`, which is exactly gate 1's `> 300.0f` but the OTHER
        # strictness from the match test's `< 100.0` (which fails at `>=`).
        # The two coincide only while no pattern's table sqrt lands exactly on
        # a cut, which is a property of this build's LUT and these windows
        # rather than a theorem -- so it is measured, in both windows, and a
        # rebuild that broke it would redden here instead of moving the match
        # boundary by one pattern in silence.
        check(m["equal_at_cut"] == 0 and g["equal_at_cut"] == 0,
              "no pattern's table sqrt lands EXACTLY on either cut, so strict "
              "and non-strict agree",
              f"match {m['equal_at_cut']} / gate 1 {g['equal_at_cut']} patterns "
              f"equal to the cut below the boundary, over {m['scanned']:,} and "
              f"{g['scanned']:,} scanned")
        # A constant that has drifted from the function that derived it is the
        # defect this whole section exists to catch.
        check(abs(GS.MATCH_RADIUS - m["true"]) < 5e-7
              and abs(GS.GATE1_CUT - g["true"]) < 5e-7,
              "the module constants still agree with their own derivations",
              f"MATCH_RADIUS {GS.MATCH_RADIUS} vs {m['true']:.7f}; GATE1_CUT "
              f"{GS.GATE1_CUT} vs {g['true']:.7f}")

    # =====================================================================
    print("\n4. REALFIX-C1 -- the forward model against a direct memory read")
    # =====================================================================
    # THE GATE IS ON THE GLIDE-CONDITIONED RESIDUAL AND ON TWO PAIRS ONLY.
    # Three of the five pairs are 53-83% parked and their unconditioned p50 of
    # 0.00 measures the parking, not the model.
    C1_P50, C1_MAX = 25.0, 75.0
    PUBLISHED_PARKED = {"20260819T145717": 0.530, "20260819T150336": 0.586,
                        "20260819T150522": 0.831, "20260819T152716": 0.085,
                        "20260819T171153": 0.038}
    if not (HAVE_GAMESRV and HAVE_MOVETAP):
        LEDGER.skip("C1 the glide-conditioned residual",
                    "this vault has no captures/gamesrv and captures/movetap "
                    "pair, so the forward model is unvalidated arithmetic here")
    else:
        c1 = {s: GS.c1_pair(s, t) for s, t in GS.MOVETAP_PAIRS}
        for s in GS.C1_GATED:
            r = c1[s]
            check(r["glide_p50"] <= C1_P50,
                  f"C1 GATED {s}: glide-conditioned p50 <= {C1_P50} u",
                  f"{r['glide_p50']:.2f} u over {r['glide_n']} gliding samples "
                  f"(parked {100 * r['parked_frac']:.1f}%)")
            check(r["glide_max"] <= C1_MAX,
                  f"C1 GATED {s}: glide-conditioned max <= {C1_MAX} u",
                  f"{r['glide_max']:.2f} u against a {GS.MATCH_RADIUS:.2f} u "
                  f"decision radius -- that ratio is the honest bound on any "
                  f"offline verdict this file prints")
        for s in ("20260819T145717", "20260819T150336", "20260819T150522"):
            r = c1[s]
            check(abs(r["parked_frac"] - PUBLISHED_PARKED[s]) < 0.005,
                  f"C1 REPORTED {s}: parked fraction reproduces the record",
                  f"{100 * r['parked_frac']:.1f}% vs a published "
                  f"{100 * PUBLISHED_PARKED[s]:.1f}%; unconditioned p50 "
                  f"{r['p50']:.2f} u, which is the parking and not the model")
        total_n = sum(r["n"] for r in c1.values())
        check(total_n >= 600,
              "the five pairs together carry enough paired samples to mean anything",
              f"n={total_n} over {len(c1)} pairs -- a residual over an empty "
              f"population is not a small residual")
        check(all(c1[s]["glide_n"] >= 50 for s in GS.C1_GATED),
              "and both GATED pairs are genuinely glide-dominated",
              f"{[(s, c1[s]['glide_n'], c1[s]['n']) for s in GS.C1_GATED]}")

    # =====================================================================
    print("\n5. REALFIX-C2 -- snap reproduction on AS-SENT streams")
    # =====================================================================
    # THE COMMITTED PER-CAPTURE VECTOR. Adaptation (1): implementation-pinned,
    # from this file's first verified green run on 2026-08-20. It is a
    # regression gate on `grantsim.py`, not a claim about the specification --
    # two implementations of the same written spec gave 69 and 80 against 60
    # measured, and this one gives 69.
    C2_EXPECTED = {
        "20260819T145717": 9, "20260819T152716": 2, "20260819T171153": 30,
        "20260819T182652": 12, "20260811T173940": 0, "20260820T182554": 0,
        "20260820T182934": 0, "20260820T183311": 6, "20260820T195137": 8,
        "20260820T195315": 1, "20260814T100340": 1,
    }
    C2_MEASURED_TOTAL = 60
    if not HAVE_GAMESRV:
        LEDGER.skip("C2 the as-sent calibration",
                    "this vault has no captures/gamesrv, so the eleven-capture "
                    "census cannot be reproduced and C2(a)'s structural zeros "
                    "stand unchecked")
    else:
        rows, text = captured(GS.print_calibration)
        by = {r["short"]: r for r in rows}
        # (a) THE CHECK THAT CARRIES. Three captures sent zero grants and
        #     measured zero jumps; a caller-aware proxy takes them to exactly
        #     zero STRUCTURALLY, because with no grant there is no caller.
        for s in GS.STRUCTURAL_ZEROS:
            r = by[s]
            check(r["bracket"][0] == 0 and r["bracket"][1] == 0
                  and r["on"]["n_instants"] == 0 and r["measured_hard"] == 0,
                  f"C2(a) {s}: exactly 0 predicted, both arms of the bracket",
                  f"bracket={r['bracket']} instants={r['on']['n_instants']} "
                  f"grants={r['grants']} measured={r['measured_hard']} -- the "
                  f"separation-only scorer predicted 16 / 12 / 34 here, which is "
                  f"what refuted it as a scorer")
        # (b) THE GOLDEN VECTOR. Equality, not a band.
        got = {r["short"]: r["bracket"][0] for r in rows}
        check(got == C2_EXPECTED,
              "C2(b) the per-capture vector matches the committed one exactly",
              f"got {got}\n        want {C2_EXPECTED} -- IMPLEMENTATION-PINNED "
              f"(see adaptation (1)); a band drawn after seeing 1.15x swallows "
              f"90 against 60 and gates nothing")
        # (c) SEPARATION. The high pair must clear the low pair by 3x on
        #     predicted snaps per minute of span.
        hi = min(by[s]["per_min_span"] for s in GS.C2C_HIGH)
        lo = max(by[s]["per_min_span"] for s in GS.C2C_LOW)
        check(hi >= 3.0 * lo,
              "C2(c) the high-separation captures exceed the low by >= 3x",
              f"min(high)={hi:.2f}/min vs max(low)={lo:.2f}/min = "
              f"{ratio(hi, lo):.2f}x")
        # ...and the order INSIDE the low pair inverts, which is printed rather
        # than gated, because gating on it would gate on a coin flip at n = 1.
        a, b = GS.C2C_LOW
        check("INVERSION" in text
              and by[a]["per_min_span"] > by[b]["per_min_span"]
              and by[a]["measured_per_min_span"] < by[b]["measured_per_min_span"],
              "C2(c) the low pair's INVERSION is printed and not gated",
              f"predicted {by[a]['per_min_span']:.2f} > {by[b]['per_min_span']:.2f} "
              f"while measured {by[a]['measured_per_min_span']:.2f} < "
              f"{by[b]['measured_per_min_span']:.2f}")
        # (d) THE ACTIVE-TIME DENOMINATOR IS NAMED, and this is what pins it.
        #     C2(c) gates on `per_min_span`, which is threshold-free, so
        #     ACTIVE_THRESHOLD reaches only `active`, `coverage` and
        #     `displaced_per_active_s` -- all print-only. An audit moved it to
        #     `movesync.FREE_SILENCE` (1.042 s), the other denominator a reader
        #     might assume, and all 57 checks stayed green with C2(c)'s numbers
        #     bit-identical. `20260820T182554` is the capture where the two
        #     denominators are furthest apart, so it is where the swap is
        #     visible: the spread is MEASURED here rather than the literal
        #     being asserted twice.
        den = GS.track_of("20260820T182554")["den"]
        a_used = movesync.active_time(den["gaps"], GS.ACTIVE_THRESHOLD)
        a_free = movesync.active_time(den["gaps"], movesync.FREE_SILENCE)
        check(GS.ACTIVE_THRESHOLD == 2.0
              and abs(by["20260820T182554"]["active"] - a_used) < 1e-6
              and a_used >= 4.0 * a_free,
              "C2(d) the printed rates use the 2.0 s active-time threshold, and "
              "the denominator it is NOT is a different measurement",
              f"active {a_used:.1f} s at {GS.ACTIVE_THRESHOLD:.3f} s vs "
              f"{a_free:.1f} s at movesync's own FREE_SILENCE "
              f"({movesync.FREE_SILENCE:.3f} s) = "
              f"{ratio(a_used, a_free):.2f}x on this capture -- every per-ACTIVE rate "
              f"this file prints moves by that factor, which is why the "
              f"threshold is printed beside its own value and never assumed")
        check(sum(r["measured_hard"] for r in rows) == C2_MEASURED_TOTAL,
              f"and the measured census is still {C2_MEASURED_TOTAL} hard jumps",
              f"{sum(r['measured_hard'] for r in rows)} over "
              f"{len(rows)} captures -- if the BAR moved, every ratio above it "
              f"moved with it and the vector is being compared to a new thing")

    # =====================================================================
    print("\n6. REALFIX-C3 (click-arm) -- the REAL predicate, reason for reason")
    # =====================================================================
    # NOT THE POLICY GATE, and it says so. See adaptation (2).
    C3 = {"20260820T195137": {"suppress": False, "rows": 199, "sends": 199,
                              "reasons": {"off": 199}},
          "20260820T195315": {"suppress": True, "rows": 154, "sends": 2,
                              "reasons": {"locally-moving": 152, "grant": 2}}}
    if not HAVE_GAMESRV:
        LEDGER.skip("C3 (click-arm) the policy replay",
                    "this vault has no captures/gamesrv, so authsrv's own "
                    "_grant_verdict is not exercised against a recorded run")
    else:
        for stamp, want in C3.items():
            path = GS.capture_path(stamp)
            rep = GS.replay_verdicts(path, want["suppress"])
            bad = [r for r in rep if r["recorded"] != r["replayed"]]
            census = {}
            for r in rep:
                census[r["replayed"][1]] = census.get(r["replayed"][1], 0) + 1
            check(len(rep) == want["rows"] and not bad and census == want["reasons"],
                  f"C3 {stamp}: {want['rows']} verdict rows reproduced, reason "
                  f"for reason",
                  f"rows={len(rep)} mismatches={len(bad)} census={census} "
                  f"want={want['reasons']}"
                  + (f" first={bad[0]}" if bad else ""))
            fired = sum(1 for r in rep if r["replayed"][0])
            check(fired == want["sends"] == GS.sent_player_grants(path),
                  f"C3 {stamp}: {want['sends']} fired verdicts and "
                  f"{want['sends']} `0x0029` on the wire",
                  f"fired={fired} sent={GS.sent_player_grants(path)} "
                  f"want={want['sends']} -- the verdict and the send are 1:1 or "
                  f"one of the two is not what it says it is")
        # THE NEGATIVE CONTROL. Replay `195315` with the flag the other way
        # round: `_grant_verdict` returns ("off", True) unconditionally there,
        # so the reproduction must FAIL. Without this, "it agreed" would be
        # what a predicate that always says yes also produces.
        wrong = GS.replay_verdicts(GS.capture_path("20260820T195315"), False)
        agreed = sum(1 for r in wrong if r["recorded"] == r["replayed"])
        check(len(wrong) == 154 and agreed == 0
              and {r["replayed"] for r in wrong} == {(True, "off")},
              "NEGATIVE CONTROL: replaying 195315 with --grant-suppress OFF "
              "reproduces NOTHING",
              f"{agreed} of {len(wrong)} agree; every replayed verdict is "
              f"{sorted({r['replayed'] for r in wrong})}. With the flag off the "
              f"predicate returns ('off', True) unconditionally -- so not even "
              f"the two rows that DID fire agree, because their recorded reason "
              f"is 'grant'. If this were 154 the replay would be ignoring the "
              f"flag and C3 would be a tautology")
        # And the numbers, not only the categories: the recorded keyboard_age
        # is logged to 3 dp, so agreement inside a millisecond is agreement.
        rep = GS.replay_verdicts(GS.capture_path("20260820T195315"), True)
        deltas = [abs(r["recorded_age"] - r["replayed_age"]) for r in rep
                  if r["recorded_age"] is not None and r["replayed_age"] is not None]
        check(deltas and max(deltas) < 0.002,
              "and the replayed keyboard_age matches the recorded one numerically",
              f"n={len(deltas)} worst delta {max(deltas) * 1000:.2f} ms -- the "
              f"log rounds to 3 dp and the verdict is stamped microseconds after "
              f"the decode it reads")
    # =====================================================================
    print("\n6b. REALFIX-C3 (heading arm) -- the REAL predicate, synthetic stream")
    # =====================================================================
    # `authsrv._heading_grant_ok` LANDED 2026-08-21 with REALFIX-P2's
    # `--zero-lead`, so the skip that stood here is gone and the lead policies
    # carry the SHIPPED rate limit. What is still asymmetric is the EVIDENCE:
    # no capture in this vault holds a heading-arm `grant_verdict` row, because
    # the flag has never been run. So this half drives BOTH arms of the real
    # predicate against hand-computed expectations on the synthetic c2s stream,
    # and says so in its own banner.
    #
    # WHAT UPGRADES IT: the first REALFIX-L1 capture. That run's jsonl will
    # carry heading rows on the same `grant_verdict` channel the click arm uses,
    # with `arm="zero-lead"` and reasons from a disjoint vocabulary, and this
    # section becomes a message-level replay pinned exactly as sec. 6's
    # 195137/195315 gate is -- rows, reasons and fired count against the
    # `0x0029` the capture actually sent. `replay_verdicts` already SKIPS those
    # rows, so that capture cannot silently redden the click arm on arrival.
    A = GS._authsrv()
    check(callable(getattr(A, "_heading_grant_ok", None)),
          "C3 (heading) the shipped predicate is importable and this file runs "
          "IT",
          "authsrv._heading_grant_ok -- REALFIX.md sec. 2.6: run the decision "
          "rather than a paraphrase that agrees with it by construction, or "
          "stop calling C3 the policy gate")
    floor = A.GRANT_MIN_INTERVAL
    # MOVECODE-1z-cw: the floor is the keyboard arm's own (KBD_GRANT_FLOOR, 0.0
    # shipped); the mechanism below runs under the 0.5 s revert arm explicitly and
    # the shipped default is pinned at the end of the block.
    _saved_kf = A.KBD_GRANT_FLOOR
    A.KBD_GRANT_FLOOR = floor
    # BOTH ARMS BY HAND. The refused arm first, because a predicate that never
    # refuses would pass the allowed one on its own.
    young = GS.heading_verdict({"grant_at": 100.0}, 100.0 + floor - 1e-6)
    old = GS.heading_verdict({"grant_at": 100.0}, 100.0 + floor)
    virgin = GS.heading_verdict({}, 100.0)
    check(young == (False, "heading-rate", young[2]) and young[2] < floor
          and old[0] is True and old[1] == "zero-lead"
          and virgin == (True, "zero-lead", None),
          f"C3 (heading) both arms: refused a microsecond under {floor:.2f} s, "
          f"allowed at exactly {floor:.2f} s, allowed with nothing on record",
          f"young={young} old={old} virgin={virgin} -- hand-computed against "
          f"GRANT_MIN_INTERVAL, and the refused arm is listed first because a "
          f"predicate that never refuses passes the allowed one by itself")
    check(GS.HEADING_REASONS == frozenset(("zero-lead", "heading-rate"))
          and not (GS.HEADING_REASONS & {"off", "locally-moving",
                                         "rate-limited", "grant"}),
          "C3 (heading) the two arms' reason vocabularies are DISJOINT",
          f"{sorted(GS.HEADING_REASONS)} against the click arm's off / "
          f"locally-moving / rate-limited / grant -- one REALFIX-L1 capture "
          f"carries both, and a replay that could not tell them apart would be "
          f"scoring the wrong predicate against the wrong rows")
    # THE POLICY, END TO END, on the synthetic stream. Six moving headings
    # 0.25 s apart; the 0.50 s floor passes t = 0.00 / 0.50 / 1.00 and DROPS
    # 0.25 / 0.75 / 1.25 -- dropped, never held, so no grant appears late.
    got = GS.policy_p2_zerolead(moves)
    heads_t = sorted(m["t"] for m in moves
                     if m["op"] == GS.OP_HEADING and m["mt"])
    check([t for t, *_ in got] == [0.0, 0.5, 1.0] and heads_t == [
              0.0, 0.25, 0.5, 0.75, 1.0, 1.25],
          f"C3 (heading) the policy applies it: 6 headings 0.25 s apart -> 3 "
          f"grants at the {floor:.2f} s floor",
          f"grants at {[t for t, *_ in got]} from headings at {heads_t} -- "
          f"exactly the instants a floor of {floor:.2f} s admits, and the three "
          f"refused ones produce NO later grant, which is what 'dropped, not "
          f"held' means on the wire")
    # THE NEGATIVE CONTROL, AND IT IS NOW ONE. What stood here counted the
    # moving headings in `moves` and asserted `len(no_limit) == 6 and
    # len(got) == 3` -- but `no_limit` was never a limit-free RUN, just the
    # denominator, and both halves were already pinned by the check immediately
    # above. It could not fail unless that one did, so it added a check to the
    # floor and refuted nothing. A control has to CHANGE something and watch the
    # answer move: the rate limit is removed by rebinding the module's own
    # verdict hook, and the same stream must then grant all six.
    saved_hv = GS.heading_verdict
    try:
        GS.heading_verdict = lambda state, now: (True, "zero-lead", None)
        unlimited = GS.policy_p2_zerolead(moves)
    finally:
        GS.heading_verdict = saved_hv
    heads_n = len([m for m in moves if m["op"] == GS.OP_HEADING and m["mt"]])
    check(heads_n == 6 and len(got) == 3 and len(unlimited) == 6
          and [t for t, *_ in unlimited] == heads_t,
          "NEGATIVE CONTROL: with the verdict forced to always fire, the SAME "
          "stream grants all 6 -- so the predicate is doing the work",
          f"{len(unlimited)} grants at {[t for t, *_ in unlimited]} unlimited "
          f"against {len(got)} at {[t for t, *_ in got]} shipped, over "
          f"{heads_n} moving headings. Before 2026-08-21 this file scored P2 "
          f"and P3 at 6 -- no rate limit existed to import -- and every check "
          f"around it stayed green")
    # AND THE POLICY MUST RUN THE PREDICATE, NOT A PARAPHRASE OF IT. REALFIX-C3's
    # whole stated ground is `_grant_verdict`'s own docstring: run the DECISION
    # rather than a paraphrase that agrees with it by construction. The checks
    # above prove the predicate is importable and that SOMETHING rate-limits the
    # policy; neither proves the policy calls it. An adversarial pass replaced
    # `heading_verdict(...)` inside `lead_policy` with an inline
    # `fired = _since is None or _since >= 0.5` and this file stayed green at
    # 66 of 66. So perturb the SERVER's own constant and require the policy's
    # grant instants to follow: a paraphrase carrying a hard-coded 0.5 cannot.
    try:
        A.KBD_GRANT_FLOOR = 1.0
        widened = GS.policy_p2_zerolead(moves)
    finally:
        A.KBD_GRANT_FLOOR = floor
    restored = GS.policy_p2_zerolead(moves)
    A.KBD_GRANT_FLOOR = _saved_kf
    shipped = GS.policy_p2_zerolead(moves)
    check([t for t, *_ in widened] == [0.0, 1.0]
          and [t for t, *_ in restored] == [0.0, 0.5, 1.0]
          and [t for t, *_ in shipped] == [0.0, 0.25, 0.5, 0.75, 1.0, 1.25],
          "C3 (heading) the POLICY runs the shipped predicate: doubling the "
          "server's own KBD_GRANT_FLOOR moves the policy's grant instants, and the "
          "shipped 0.0 (1z-cw) answers all six",
          f"at 1.00 s the same stream grants at {[t for t, *_ in widened]} and "
          f"at the shipped {floor:.2f} s it grants at "
          f"{[t for t, *_ in restored]} -- an inline paraphrase carrying a "
          f"hard-coded 0.5 would answer the same both times. This is the "
          f"difference between 'the predicate exists' and 'the policy uses it', "
          f"and it is the whole of what REALFIX-C3 was extended to cover")
    # THE HEADING-ROW FILTER, DRIVEN. `replay_verdicts` skips rows carrying
    # `arm == "zero-lead"` or a heading reason so REALFIX-L1's first capture
    # cannot silently redden C3's CLICK arm. No capture in this vault has such a
    # row yet, so nothing exercised those three lines: deleting them left this
    # file green at 66 of 66. Feed it a hand-built capture carrying one row of
    # each kind plus one ordinary click row as the positive control.
    mixed = os.path.join(TMP, "authsrv-20260820T000002-c1.jsonl")
    with open(mixed, "w", encoding="utf-8") as fh:
        for r in ({"kind": "origin", "origin": origin.OURS, "t": 0.0,
                   "produced_by": "test_grantsim (heading-filter fixture)",
                   "server": "127.0.0.1:6112", "client": "127.0.0.1:50001"},
                  {"kind": "grant_verdict", "t": 1.0, "fired": True,
                   "reason": "zero-lead", "arm": "zero-lead"},
                  {"kind": "grant_verdict", "t": 2.0, "fired": False,
                   "reason": "heading-rate"},
                  {"kind": "grant_verdict", "t": 3.0, "fired": True,
                   "reason": "off"}):
            fh.write(json.dumps(r) + "\n")
    kept = GS.replay_verdicts(mixed, suppress=False)
    check(len(kept) == 1 and kept[0]["t"] == 3.0
          and kept[0]["recorded"] == (True, "off"),
          "C3 (heading) `replay_verdicts` SKIPS heading rows and keeps the "
          "click row beside them",
          f"kept {[(r['t'], r['recorded']) for r in kept]} out of three rows -- "
          f"one tagged `arm=zero-lead`, one carrying only the heading reason "
          f"`heading-rate`, one ordinary click row. Both skip paths are driven "
          f"separately because the `arm` field is newer than the reasons and a "
          f"filter keyed on either alone would miss the other; the click row is "
          f"the positive control, without which a filter that dropped "
          f"EVERYTHING would pass")

    # =====================================================================
    print("\n7. REALFIX-C4 -- the nulls, including the one this file FAILS")
    # =====================================================================
    if not HAVE_GAMESRV:
        LEDGER.skip("C4 the nulls",
                    "this vault has no captures/gamesrv, so nothing perturbs "
                    "and the instrument's blind spots stand unmeasured")
    else:
        n, text = captured(GS.print_nulls)
        base = n["base"]
        check(n["match_off"] >= 1.5 * base,
              "C4 deleting the match test inflates the total by >= 1.5x",
              f"{n['match_off']} vs {base} = {ratio(n['match_off'], base):.2f}x -- the "
              f"match test is genuinely load-bearing, which is the one thing "
              f"round 5's null suite established without qualification")
        rot = [n["rotate"][k] for k in GS.ROTATIONS]
        check(all(rot[i] <= rot[i + 1] for i in range(len(rot) - 1)),
              "C4 rotating destinations inflates MONOTONICALLY",
              f"k={list(GS.ROTATIONS)} -> {rot}")
        check(rot[-1] >= 1.5 * base,
              "C4 the largest rotation moves it by half again",
              f"k={GS.ROTATIONS[-1]} -> {rot[-1]} against a base of {base}")
        check(n["rotate"][1] > base,
              "C4 even the SMALLEST rotation moves it",
              f"k=1 -> {n['rotate'][1]} vs {base}; a null that cannot fire at "
              f"its smallest setting is measuring the setting")
        # THE SHIFT NULL IS GATED PER CAPTURE, at +3.0 s only, and the failure
        # at +0.35 s is asserted rather than hidden.
        for s in GS.SHIFT_GATED_CAPTURES:
            after = n["shift_per"][GS.SHIFT_GATED][s]
            check(after < n["per_base"][s],
                  f"C4 {s}: shifting every grant {GS.SHIFT_GATED:+.1f} s drops "
                  f"the prediction",
                  f"{n['per_base'][s]} -> {after} against a measured "
                  f"{n['measured'][s]}")
        meas = sum(n["measured"].values())
        check(n["shift"][0.35] == meas and "THE FAILURE, PRINTED" in text,
              "C4 THE FAILURE IS PRINTED: +0.35 s destroys causality and scores "
              f"{meas}, dead on the measured total",
              f"+0.35 s -> {n['shift'][0.35]}, measured {meas}. The TOTAL is not "
              f"discriminating on sub-report-interval timing and this file says "
              f"so above the number rather than below it")
        rot1 = ratio(abs(n["rotate"][1] - base), base)
        sh = ratio(abs(n["shift"][-0.35] - base), base)
        check(max(rot1, sh) <= 3.0 * max(min(rot1, sh), 1e-9)
              and "NO asymmetry is claimed" in text,
              "C4 at MATCHED perturbation scale, geometry and cadence are the "
              "same order -- no asymmetry is claimed",
              f"rotate-1 {100 * rot1:+.1f}% vs shift-(-0.35 s) {100 * sh:+.1f}% "
              f"= {ratio(max(rot1, sh), min(rot1, sh)):.2f}x. The claimed asymmetry "
              f"set rotate-by-17 beside shift-by-+0.35 s and is manufactured")

    # =====================================================================
    print("\n8. REALFIX-C5 -- the band, and the refusal to rank")
    # =====================================================================
    if not HAVE_GAMESRV:
        LEDGER.skip("C5 the sensitivity band",
                    "this vault has no captures/gamesrv, so the counterfactual "
                    "substrate is absent and the ranking cannot be refused on "
                    "evidence -- only in prose, which is not the same thing")
    else:
        (cells, order), text = captured(GS.print_band)
        want_cells = (len(GS.C5_MATCH) * len(GS.C5_WINDOWS) * len(GS.C5_RADII)
                      * len(GS.C5_GATES))
        check(len(cells) == want_cells
              and {c["cfg"]["match"] for c in cells} == {True, False},
              f"C5 the band is {want_cells} cells and BOTH arms of the "
              f"match-test axis are in it",
              f"{len(cells)} cells; the drafted sweep varied the match RADIUS "
              f"and never its PRESENCE, which is the axis the ranking is not "
              f"invariant on")
        on = [c for c in cells if c["cfg"]["match"]]
        off = [c for c in cells if not c["cfg"]["match"]]
        worst_on = all(c["totals"][GS.LEAD_ENDPOINT] > c["totals"][0.0] for c in on)
        best_off = any(c["totals"][GS.LEAD_ENDPOINT] < c["totals"][0.0] for c in off)
        check(worst_on and best_off,
              "C5 the ranking INVERTS on the match-test axis, and that is the "
              "finding",
              f"match ON: the 766 u lead is worst in {sum(1 for c in on if c['totals'][GS.LEAD_ENDPOINT] > c['totals'][0.0])} "
              f"of {len(on)} cells; match OFF: it WINS in "
              f"{sum(1 for c in off if c['totals'][GS.LEAD_ENDPOINT] < c['totals'][0.0])} "
              f"of {len(off)}")
        check(order is None and "NO ORDERING IS PRINTED" in text,
              "C5 NO ORDERING IS PRINTED on the real substrate",
              f"rank_or_refuse -> {order}. A ranking printed outside the "
              f"invariance band is the defect this whole file exists to refuse; "
              f"the P2-vs-P3 question needs the live A/B")
        check(GS.rank_or_refuse(GS.band(stamps=("20260811T173940",),
                                        leads=(0.0,))) is None,
              "CONTROL: one lead alone is not an ordering either",
              "a single-candidate band has nothing to order, and returning a "
              "one-tuple would read as a verdict")

    # =====================================================================
    print("\n9. REALFIX-M1 and M2 -- each non-empty on its own candidate")
    # =====================================================================
    if not HAVE_GAMESRV:
        LEDGER.skip("M1 / M2 the exposure metrics",
                    "this vault has no captures/gamesrv; the two metrics that "
                    "are NOT tautologies of the proxy's construction cannot be "
                    "measured")
    else:
        tr = GS.track_of("20260814T100340")
        moves = GS.c2s_moves(GS.capture_path("20260814T100340"))
        p2 = GS.score(tr, GS.policy_p2_zerolead, c2s=moves)
        p3 = GS.score(tr, GS.policy_p3_shortlead, c2s=moves)
        m1 = p2["on"]["m1"]
        # THE BOUND IS THE WINDOW, NOT TWICE IT. `lag_age` only inspects points
        # with `t >= lo >= now - window`, so `now - t <= HISTORY_WINDOW` holds
        # BY CONSTRUCTION and a factor of 2 is not slack, it is room for the
        # construction to be deleted unnoticed: dropping `lag_age`'s `lo` bound
        # -- the one modelling call this section's author flagged as a judgement
        # call -- takes the max from 4.55 s to 7.42 s, which `<= 10.0` accepts.
        # At `<= HISTORY_WINDOW` the check is an assertion the artifact can
        # refute rather than a bound nothing can reach.
        check(m1["n"] >= 100 and math.isfinite(m1["p90"])
              and m1["max"] <= GS.HISTORY_WINDOW + 1e-9,
              "REALFIX-M1 (lag age) is non-empty on P2 and bounded by the chain",
              f"n={m1['n']} p50={m1['p50']:.2f} p90={m1['p90']:.2f} "
              f"max={m1['max']:.2f} s against the {GS.HISTORY_WINDOW:.1f} s "
              f"window the metric is measured inside, itself a model of the "
              f"~5,000 ms block-recycle bound. Under zero lead the match "
              f"distance is 0 by IDENTITY -- the proxy's polyline IS the report "
              f"track -- so this age is the only thing about P2 that is "
              f"measured rather than assumed")
        m2 = p3["on"]["m2"]
        check(m2["n"] >= 50 and math.isfinite(m2["next_report"])
              and m2["next_report"] > 0.0,
              "REALFIX-M2 (arrival exposure) is non-empty on P3",
              f"n={m2['n']} arrivals; poly {100 * m2['poly']:.1f}%, next-report "
              f"{100 * m2['next_report']:.1f}%. The two operands answer different "
              f"questions and both are printed: round 5 priced P3 at 45.7% on the "
              f"NEXT-REPORT operand, which is the one its pre-registration used")

    # =====================================================================
    print("\n10. REALFIX-F1b -- the field-4 pre-screen, and its calibration")
    # =====================================================================
    # WHAT THIS SECTION GUARDS. `--planecarry` is how every future field-4
    # policy gets scored before it costs a live arm, and its answer for F1b is
    # a NEGATIVE (3 residuals, not the predicted 0). A negative is exactly the
    # kind of number that quietly becomes a positive when somebody adjusts a
    # tolerance, so the calibration gate, the tautology label on the closed
    # simulator and the refusal to fit a guard band are all pinned here.
    #
    # THE STRUCTURAL HALF RUNS EVERYWHERE. The queue's three cases are driven
    # against a hand-built grant stream with no vault at all, so a bare machine
    # still proves the replay can distinguish the policies.
    fake_taps = [{"t": 1000.0 + 0.1 * i, "plane": 0, "pos": (0.0, 0.0),
                  "sep": 0.0} for i in range(40)]
    S_ = GS._authsrv().DEFAULT_RUN_SPEED
    fake_grants = [
        {"t": 1000.5, "dest": (0.0, 0.0), "w3": 0, "w4": 0},
        {"t": 1001.0, "dest": (S_, 0.0), "w3": 18, "w4": 18},
        {"t": 1002.5, "dest": (2 * S_, 0.0), "w3": 18, "w4": 18},
    ]
    f4 = {n: GS.field4_replay(fake_grants, p, 0, (0.0, 0.0))
          for n, p in GS.FIELD4_POLICIES.items()}
    sent = {n: [r["field4"] for r in v["rows"]] for n, v in f4.items()}
    check(sent["shipped-zerolead"] == [0, 18, 18]
          and sent["F1-planecarry"] == [0, 0, 18]
          and sent["F1b-arrivalcarry"] == [0, 0, 18],
          "the three policies are DISTINGUISHABLE on a driven stream -- "
          "shipped echoes field 3, F1 and F1b both lag it here",
          f"{sent} over grants at t+0.0 / +0.5 / +2.0 with a "
          f"{S_:.0f} u second leg (1.000 s). Grant 3 comes 1.5 s after grant 2, "
          f"so grant 2 HAS arrived and F1b agrees with F1 -- which is the whole "
          f"point of the case below")
    # THE CASE THAT SEPARATES THEM, and it is F1's named limit. Move grant 3 to
    # 0.5 s after grant 2 and grant 2's 288 u leg is still in flight: F1 carries
    # its 18 unreached, F1b holds the 0 the copy is standing on.
    tight = list(fake_grants[:2]) + [
        {"t": 1001.5, "dest": (2 * S_, 0.0), "w3": 18, "w4": 18}]
    tight_sent = {n: [r["field4"] for r in
                      GS.field4_replay(tight, p, 0, (0.0, 0.0))["rows"]]
                  for n, p in GS.FIELD4_POLICIES.items()}
    check(tight_sent["F1-planecarry"] == [0, 0, 18]
          and tight_sent["F1b-arrivalcarry"] == [0, 0, 0],
          "and they SEPARATE on the two-interval lag: with grant 2 still in "
          "flight F1 carries its plane, F1b does not",
          f"F1 {tight_sent['F1-planecarry']} vs F1b "
          f"{tight_sent['F1b-arrivalcarry']} -- grant 3 lands 0.5 s into grant "
          f"2's 1.000 s leg. This is the shape of all of F1's residuals and the "
          f"whole reason F1b exists; a replay that could not tell the two apart "
          f"would score them identically and say nothing")
    # FIELD4_SCREEN IS THE TABLE THE SERVER'S BANNER TRANSCRIBES, and these two
    # checks are the only thing standing between that banner and a number
    # nobody computed. `authsrv.py` may not import this module -- grantsim
    # imports authsrv, and the server path stays dependency-clean -- so the
    # banner holds literals and `test_position_trust.py` §16 rebuilds its three
    # printed rows from this dict. That tie is worth nothing unless the dict is
    # itself pinned, which is the vaulted check below; this one is its
    # fixture-free half, and it is what keeps the screen's own three published
    # scalars from disagreeing with the six-cell table beside them.
    screen_diag = {
        ("shipped-zerolead", "20260821T132546"),
        ("F1-planecarry", "20260821T143411"),
    }
    diag_ok = all(GS.FIELD4_SCREEN[pol][st][0] == GS.FIELD4_MEASURED[st]
                  for pol, st in screen_diag)
    check(diag_ok
          and (GS.FIELD4_SCREEN["F1b-arrivalcarry"]["20260821T143411"][0]
               == GS.FIELD4_F1B_EXPECTED)
          and set(GS.FIELD4_SCREEN) == set(GS.FIELD4_POLICIES),
          "FIELD4_SCREEN's diagonal IS the calibration pin and its F1b cell IS "
          "FIELD4_F1B_EXPECTED -- one table, not three drifting scalars",
          f"diagonal {[GS.FIELD4_SCREEN[p][s][0] for p, s in sorted(screen_diag)]} "
          f"against FIELD4_MEASURED {sorted(GS.FIELD4_MEASURED.values())}; F1b "
          f"cell {GS.FIELD4_SCREEN['F1b-arrivalcarry']['20260821T143411']} "
          f"against FIELD4_F1B_EXPECTED {GS.FIELD4_F1B_EXPECTED}. A screen that "
          f"published 3 in one constant and 0 in the table would let the server "
          f"print either and stay green")
    check(set(GS.FIELD4_SCREEN["F1b-arrivalcarry"])
          == set(GS.FIELD4_SCREEN["F1-planecarry"])
          == set(GS.FIELD4_SCREEN["shipped-zerolead"])
          == {s for s, _tap, _arm in GS.FIELD4_PAIRS},
          "and every policy carries a cell for every capture the census runs",
          f"{sorted(GS.FIELD4_SCREEN['F1b-arrivalcarry'])} against "
          f"{sorted(s for s, _t, _a in GS.FIELD4_PAIRS)} -- adding a third "
          f"capture to FIELD4_PAIRS without extending this table would leave "
          f"the banner printing a two-column screen of a three-column run")
    if not (HAVE_GAMESRV and HAVE_MOVETAP):
        LEDGER.skip("F1b the counterfactual against the L3 captures",
                    "this vault has no captures/gamesrv or no captures/movetap; "
                    "the calibration gate and the 3-policy table both need the "
                    "two REALFIX-L3 arms and their taps")
    else:
        rows, gate_ok = captured(GS.print_planecarry)[0]
        by = {r["stamp"]: r for r in rows}
        check(gate_ok and len(rows) == 2,
              "THE CALIBRATION GATE PASSES on both REALFIX-L3 arms",
              f"gate={gate_ok} over {len(rows)} capture(s) -- replaying each "
              f"capture's OWN arm has to reproduce its wire, or every "
              f"counterfactual printed under it is arithmetic about nothing")
        for stamp, want in GS.FIELD4_MEASURED.items():
            c = by[stamp]["calibration"]
            check(c["own_anchored"] == want and c["own_reproduces_wire"]
                  and c["own_full_coverage"],
                  f"  {stamp}: the own-arm replay reproduces field 4 on all "
                  f"{by[stamp]['grants']} grants and scores {want}",
                  f"anchored={c['own_anchored']} (want {want}), "
                  f"reproduces_wire={c['own_reproduces_wire']}, "
                  f"full_coverage={c['own_full_coverage']}. For the F1 arm this "
                  f"is a real exercise of the policy: its slot advances only on "
                  f"a SEND, so the rate-limit refusals in that capture have to "
                  f"leave it alone or the whole stream drifts")
            # THE PAIRING WINDOW, BRACKETED FROM BOTH SIDES BY THIS CAPTURE.
            # FIELD4_PAIR_GAP used to be one constant doing two jobs, and only
            # the OTHER job (grant attribution, now FIELD4_ATTRIB_GAP) was
            # exercised: widening the shared constant 20x moved neither the
            # anchored headline nor this pin, because every grant's
            # last-strictly-before sample lands within 0.122 s. So the pairing
            # role is checked directly. Wide enough: the worst observed lead
            # fits inside it, or grants would be dropped as unpaired at the
            # margin. Narrow enough: it cannot span three tap intervals, which
            # is the derivation its own comment states ("a sample is ~0.105 s
            # and this admits at most two") and the thing that stops the
            # strictly-before rule reaching back ACROSS a tap dropout on some
            # future capture. Both operands are measured from the capture, and
            # `pair_lead_max` is taken over EVERY grant rather than over the
            # ones that paired, so shrinking the window cannot make its own
            # counter-example disappear.
            check(c["pair_lead_max"] <= GS.FIELD4_PAIR_GAP
                  and GS.FIELD4_PAIR_GAP <= 3.0 * c["tap_dt_median"],
                  f"  and the {GS.FIELD4_PAIR_GAP:.2f}s pairing window is "
                  f"bracketed by this capture's own cadence, not asserted",
                  f"worst grant-to-sample lead {c['pair_lead_max']:.3f}s "
                  f"against a window of {GS.FIELD4_PAIR_GAP:.2f}s, which is "
                  f"{GS.FIELD4_PAIR_GAP / c['tap_dt_median']:.2f} tap intervals "
                  f"at this capture's median {c['tap_dt_median']:.3f}s against "
                  f"a bound of 3.00. The window is NOT binding here -- all "
                  f"{by[stamp]['grants']} grants pair identically at 0.25 s and "
                  f"at 5.0 s -- so nothing else in this file can see it move")
            check(c["own_nearest"] == GS.FIELD4_PUBLISHED_NEAREST[stamp]
                  and c["own_nearest"] < want,
                  f"  and the PUBLISHED nearest-sample count "
                  f"({GS.FIELD4_PUBLISHED_NEAREST[stamp]}) reproduces too, and "
                  f"is lower",
                  f"nearest={c['own_nearest']} anchored={want} -- pairing with "
                  f"the NEAREST sample admits one taken AFTER the grant, which "
                  f"reads the plane word the grant just wrote and scores a "
                  f"genuine rewrite as a match. Both are kept so the correction "
                  f"to FINDINGS is visible rather than silently applied")
        # THE ARRIVAL MODEL IS THE FALSIFIABLE HALF, and only the F1 capture can
        # test it -- under --zero-lead field 4 already equals the client's plane,
        # so the client never has to correct us and never reveals its opinion.
        arr = by["20260821T143411"]["calibration"]["arrival"]
        p2_arr = by["20260821T132546"]["calibration"]["arrival"]
        check(arr["n"] >= 17 and arr["miss"] == 0
              and arr["dt_max"] <= GS.FIELD4_ARRIVAL_GATE,
              "THE ARRIVAL MODEL: every client-authored plane write lands on a "
              "modelled arrival, with no free parameter",
              f"{arr['hit']} of {arr['n']}, |dt| median {arr['dt_median']:.3f}s "
              f"max {arr['dt_max']:.3f}s against a "
              f"{GS.FIELD4_ARRIVAL_GATE:.2f}s gate and a tap running at 9.5 Hz. "
              f"These are writes up to 1.9 s from any grant, so the model had "
              f"every opportunity to be refuted and was not")
        check(p2_arr["n"] == 0,
              "CONTROL: the P2 capture offers the model NOTHING to be tested "
              "against, and the instrument says so rather than scoring 0 of 0 "
              "as a pass",
              f"n={p2_arr['n']} client-authored writes -- under --zero-lead "
              f"field 4 IS the client's current plane, so the client never "
              f"corrects us. Unfalsifiable there BY CONSTRUCTION; a reader who "
              f"took the F1 capture's 17 of 17 as covering both would be "
              f"claiming a validation this capture cannot supply")
        f1b = by["20260821T143411"]["anchored"]["F1b-arrivalcarry"]
        f1 = by["20260821T143411"]["anchored"]["F1-planecarry"]
        check(f1b["mismatch"] == GS.FIELD4_F1B_EXPECTED
              and f1b["mismatch"] > 0 and f1b["mismatch"] < f1["mismatch"],
              "THE HEADLINE, AND IT IS A NEGATIVE: F1b does NOT reach 0 -- it "
              "reaches 3, down from F1's 6",
              f"F1b {f1b['mismatch']} of {f1b['scored']} scored "
              f"({f1b['skipped']} refused as contaminated), F1 "
              f"{f1['mismatch']} of {f1['scored']}. F1b's pre-registration was "
              f"'the field-4 mismatch count reaches 0' -- the falsifier F1 "
              f"failed -- and this screen says it would fail too. That is the "
              f"result, and the flag's startup banner predicts 3 rather than 0 "
              f"because of it")
        races = GS.field4_race(f1b["rows"],
                               by["20260821T143411"]["policies"]
                               ["F1b-arrivalcarry"])
        worst = max(r["since_arrival"] for r in races) if races else float("inf")
        check(races and worst <= 0.050,
              "and all three survivors are a SUB-FRAME RACE on `arrival <= "
              "now`, not a logic error",
              f"they land {', '.join('%.0f' % (r['since_arrival'] * 1000) for r in races)} "
              f"ms after a modelled arrival the client had not yet acted on; "
              f"worst {worst * 1000:.0f} ms. The model is right about the TICK "
              f"and early about the ACT -- against the client's 17 unambiguous "
              f"writes it is strictly early in {arr['early_n']} of "
              f"{arr['hit']}, by at most {arr['early_max'] * 1000:.0f} ms, "
              f"which is the size of a display frame")
        # THE TAUTOLOGY IS LABELLED AND THE LABEL IS CHECKED. The closed
        # simulator returns 0 for F1b because it derives the plane word from the
        # same arrival model F1b's policy reads. It is printed BELOW the
        # anchored table with that said out loud, and this pins both halves.
        closed = by["20260821T143411"]["policies"]
        _r, text = captured(GS.print_planecarry, rows)
        check(closed["F1b-arrivalcarry"]["mismatch"] == 0
              and closed["F1-planecarry"]["mismatch"] < f1["mismatch"]
              and "BY CONSTRUCTION" in text and "TAUTOLOGY" in text,
              "the CLOSED simulation returns 0 for F1b and UNDER-counts F1, and "
              "the printer says both out loud",
              f"closed F1b {closed['F1b-arrivalcarry']['mismatch']}, closed F1 "
              f"{closed['F1-planecarry']['mismatch']} against the wire's "
              f"{f1['mismatch']} -- a simulator that grades a policy with the "
              f"policy's own model agrees with it by construction. It is kept "
              f"because the OTHER two policies do not come out at zero under "
              f"it, and it is printed under a label rather than in the table")
        # EVERY CELL OF THE PUBLISHED SCREEN, against the live computation.
        # This is the pin that makes `test_position_trust.py` §16's banner tie
        # mean something: the banner is rebuilt from FIELD4_SCREEN, and
        # FIELD4_SCREEN is this table. Without it the two files would agree
        # with each other about a number neither had measured.
        live_screen = {pol: {r["stamp"]: (r["anchored"][pol]["mismatch"],
                                          r["anchored"][pol]["scored"])
                             for r in rows}
                       for pol in GS.FIELD4_POLICIES}
        check(live_screen == GS.FIELD4_SCREEN,
              "EVERY CELL of the published 3-policy x 2-capture screen "
              "reproduces, denominators included",
              f"live {live_screen} against FIELD4_SCREEN {GS.FIELD4_SCREEN} -- "
              f"the denominators are the point as much as the counts: 3 of 69 "
              f"and 3 of 3 are not the same claim, and the banner prints both "
              f"halves of every cell")
        check("REFUSED as a fitted parameter" in text
              and "does NOT reach 0" in text,
              "and the printed report REFUSES the guard band that would close "
              "the race",
              "a ~40 ms eps closes all three survivors and has no derivation; "
              "fitting it to the one capture that scores it is the free "
              "parameter the house rule is about. If a frame-consumption term "
              "is real it should be MEASURED, and then it is not free")

    return LEDGER.verdict()


if __name__ == "__main__":
    try:
        sys.exit(main())
    finally:
        shutil.rmtree(TMP, ignore_errors=True)
