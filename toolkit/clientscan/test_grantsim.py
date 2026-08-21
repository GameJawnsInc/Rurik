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

**(2) §C3 covers the CLICK ARM ONLY and is labelled `C3 (click-arm)`.** §2.6
allows exactly that, on the condition that it stop being called the policy gate,
which this docstring and its section banner do. `_heading_grant_ok` does not
exist in `authsrv.py` yet -- REALFIX-P2 specifies it as new code carrying Rule 2
only -- so there is no heading-arm predicate to import and §C3's heading half
declares a skip naming the missing symbol.

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
FLOOR_BARE = 19
FLOOR_FULL = 61
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
# and 61 is a floor rather than a hope. Any other configuration keeps
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
    heads = [m for m in moves if m["op"] == GS.OP_HEADING and m["mt"]]
    spine = []
    for pol in (GS.policy_p2_zerolead, GS.policy_p3_shortlead, GS.policy_p_endpoint):
        got = pol(moves)
        offs = sorted({round(D[0] - m["pos"][0], 6)
                       for (_t, D, _a, _b, _k), m in zip(got, heads)})
        spine.append((pol.lead, offs, len(got)))
    check(len(heads) == 6 and all(n == 6 for _l, _o, n in spine)
          and spine[0][0] == 0.0 and spine[0][1] == [0.0]
          and abs(spine[1][0] - 85.919968) < 5e-7 and spine[1][1] == [85.919968]
          and spine[2][0] == 766.0 and spine[2][1] == [766.0],
          "the lead spine is 0 / 85.919968 / 766 u and each policy GRANTS at "
          "its own",
          f"{[(round(l, 6), o, n) for l, o, n in spine]} over {len(heads)} "
          f"moving headings -- P3's 85.919968 u is MATCH_RADIUS - 14.0, the "
          f"arm of min(RUN_SPEED * 0.30, MATCH_RADIUS - 14.0) that wins, and "
          f"the spine is the one axis C5's band varies")

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
    LEDGER.skip("C3 the HEADING arm",
                "authsrv.py has no `_heading_grant_ok`; REALFIX-P2 specifies it "
                "as NEW code carrying Rule 2 only, so there is no heading-arm "
                "predicate to import and no heading-arm policy to replay. This "
                "is why sec. 6 is labelled C3 (click-arm) and why this file does "
                "not call C3 the policy gate")

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

    return LEDGER.verdict()


if __name__ == "__main__":
    try:
        sys.exit(main())
    finally:
        shutil.rmtree(TMP, ignore_errors=True)
