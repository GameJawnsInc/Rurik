#!/usr/bin/env python3
"""The position-trust policy: it may refuse, but it may never LATCH.

    python toolkit/authsrv/test_position_trust.py

WHAT EARNS THIS FILE. `_adopt_client_position` refused any client-reported
position more than `CLIENT_POSITION_TRUST_RADIUS` = 900 u from the server's own
model. The radius was measured from `state["pos"]` -- the value the refusal was
preventing from being corrected -- so once the model was more than 900 u wrong,
every true report was also more than 900 u away and was refused in its turn. Run
20260819T113049 refused 50 reports, 36 of them consecutively, 21% of everything
the client said. Nothing in the suite could see it: `position_report` was emitted
from the 0x0047 arm only and carried a literal `accepted=True`, so the flagship
capture's JSONL held 5 of 62 reports and none of the four refusals.

AND THE GUARD NEVER EARNED ITS KEEP. Scored over the 72 refusals the four
harness runs actually printed -- 7 + 11 + 50 + 4, counted from the servers' own
"[map] ignoring a Nu jump" lines, not from a replay -- by asking whether the
client's NEXT report is reachable from the point we refused or from the point we
preferred, at 478 u/s (the most generous speed in Guild Wars, Junundu Tunnel at
+66%, and far above our 288): client right 71, guard right 0, undecidable 1.

TWO NUMBERS THIS FILE DELIBERATELY DOES NOT USE. An earlier replay of the same
question reported 85 refusals and a largest true-but-refused drift of 18,647 u.
Both are artifacts: the servers printed 72, and the largest drift anywhere in the
harness tree is 4,116 u. A test pinned to 18,647 would have gone red forever
against a number no server ever produced, which is why every count below is
re-derived from a capture on disk or asserted as an invariant with no fixture at
all.

THE SHAPE OF THE FIX, and therefore of this file. The budget is
`max(RADIUS, RATE * seconds since the last report we BELIEVED)`, so it is never
smaller than the old flat 900 -- section 1 asserts that as an invariant, because
a tightening was designed, costed at 8 newly-refused true reports, and thrown
away. On top of it, the Nth consecutive refusal is adopted regardless, which is
what makes 36-in-a-row unreachable for any constants. Section 2 is the headline.

THE FILE HAS SINCE BECOME THE HOME OF THE MOVEMENT FLAGS, because they all turn
on the same two values and the same two receive arms: sections 7 to 9 and 11
lock the shapes of --stop-echo, --client-endpoint and --resync, and sections 12
and 13 lock --grant-suppress -- the eighth candidate, and the first that acts by
sending LESS rather than by sending something better. Section 13 replays the
three captures of 2026-08-20 through the policy itself: the reproduction's 196
clicks must all be refused and the ordinary capture's 5 must all be permitted,
because either half alone is passed by a policy that is simply wrong in one
direction.

SECTION 14 IS `--zero-lead` (REALFIX-P2), and it is the first section here that
EXECUTES a receive arm rather than only matching its syntax tree. Two of that
flag's claims are behavioural and no AST matcher can reach them -- a moving
report the shipped `turned or not walking` gate would SKIP is still granted
under the flag, and the very same report sends NOTHING with the flag off -- so
`receive_arm()` lifts the arm's own statements out of the receive loop and runs
them against `authsrv.__dict__`. It executes the file's bytes, re-extracted
every run. The AST locks stay beside it for the things a single execution cannot
show: that ZERO_LEAD is named in the heading arm and in NEITHER the stop arm nor
the click arm, and that exactly one `if ZERO_LEAD:` block in the file sends.

SECTION 15 IS `--plane-carry` (REALFIX-F1), and it is a MODIFIER on section
14's flag rather than a tenth candidate policy. It changes ONE wire field:
field 4 of the zero-lead `0x0029`, which is what the client writes to
`agent+0x80` on the SYNC copy -- a copy one report-chord (~515 u) behind the
client, so on a plane boundary the shipped payload stamps the CLIENT's plane
onto a copy standing somewhere else. REALFIX-L3 measured that as the trigger
for all three of its warps (8 plane-rewriting above-cut grants produced 3
events; 28 unchanged above-cut grants produced 0; Fisher p = 0.0078). The
section reuses section 14's lifted arm with a second flag set, and most of it
exists to prove the delta is exactly one field: carry-ON and carry-OFF runs of
the same reports must agree on every destination, on `state["dest"]` and on the
SYNC model, and differ in field 4 alone. It also drives the composition
decision -- `--plane-carry` without `--zero-lead` is REFUSED rather than
documented as inert, because inert is how a fix gets credited with a null it
never earned.
"""
import ast
import contextlib
import inspect
import io
import json
import math
import os
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

sys.path.insert(0, os.path.join(os.path.dirname(HERE), "clientscan"))

import checks     # noqa: E402
import authsrv    # noqa: E402
import vaultpath  # noqa: E402
# THE OFFLINE SCORER, IMPORTED BY THE TEST AND NEVER BY THE SERVER. Section 16
# rebuilds the --arrival-carry banner's counterfactual table from
# `grantsim.FIELD4_SCREEN` so the banner and the scorer cannot drift apart in
# silence. It has to be this direction: `grantsim` imports `authsrv` (for the
# shipped arrival model), so `authsrv` importing `grantsim` would be a cycle AND
# would put a clientscan module on the server path. The tie is therefore made
# here, on the test side, and `test_grantsim.py` §10 pins FIELD4_SCREEN itself
# against the live computation. Nothing in grantsim runs at import time -- no
# vault, no client image -- so this import is bare-machine safe and both floors
# below move by the same amount.
import grantsim   # noqa: E402

# MEASURED from a real green run: 24 checks with the capture present, 20
# without; section 8 (the unit-vector lock) added 8 on 2026-08-19 and
# section 9 (the --client-endpoint shape lock) added 6, so 38 and 34 --
# and 39/35 was written here first, from a count in the author's head
# rather than from the run, which would have set the floor ABOVE the
# bare-machine total and redded every machine without the capture. The floor is the BARE-MACHINE subset -- sections 0 to 8 are
# pure policy and syntax tree and take no fixture, while section 10 replays
# a real capture and declares LEDGER.skip when this vault has no copy of it.
# Setting the floor at 38 would red every machine that is not the owner's;
# 34 still catches the failure this rule exists for, which is a section
# quietly evaporating.
#
# 2026-08-20: section 11 (the --resync sender) added 35, so 73 with the capture
# and 69 without. Both numbers are from the run printed on the console, not from
# a count in anybody's head -- section 10 contributes exactly 4 checks and is
# the only fixture-bearing one, which is the whole of the arithmetic.
#
# 2026-08-20, later: section 12 (--grant-suppress) and section 13 (its replay of
# that evening's three captures) took it to 113 with every fixture present and
# 105 without. There are now TWO fixture-bearing sections contributing 4 checks
# each -- section 10's single 20260819 capture and section 13's three 20260820
# ones -- so the floor is 113 - 8. Both figures are read off a real green
# console run, and the floor is the BARE-MACHINE subset for the reason the
# paragraph above gives: setting it at 113 would red every machine that is not
# the owner's, while 105 still catches a section quietly evaporating.
#
# 2026-08-21: section 14 (--zero-lead / REALFIX-P2) added 34, taking it to 147
# with every fixture present and 139 without. Section 14 is entirely
# fixture-free -- it drives the shipped predicate, executes the receive arm's
# own statements lifted out of the file, and reads the syntax tree -- so the
# whole of its 34 lands in the bare-machine subset and the two totals move by
# the same amount. BOTH figures are read off real green console runs of their
# own configuration: 147 from a normal run and 139 from one with RURIK_VAULT
# pointing at a directory that does not exist. Neither is an enumeration.
#
# 2026-08-21, AFTER REVIEW: TWO FLOORS, ONE PER FIXTURE CONFIGURATION, and the
# single floor this file carried for a day was a real hole rather than a
# tidiness point. Excess over a floor is not an error in `checks.py`, so a lone
# BARE floor of 139 protected NONE of the 8 checks that only a vaulted machine
# runs -- and the configuration the owner actually runs is the vaulted one. An
# adversarial pass proved it: unhooking one section-14 check from the ledger on
# a vaulted machine printed ALL CHECKS PASSED (146) against a floor of 139,
# while the bare run of the same tree went red at 138 of 139. `test_grantsim.py`
# fixes exactly this with FLOOR_BARE/FLOOR_FULL and this is the same shape.
# BOTH numbers are measured from green runs of their own configuration; the
# probes below decide which applies, and they are the same `os.path.exists`
# checks sections 10 and 13 make for themselves.
#
# The same review added 13 checks to section 14 -- the trust-refusal pair and
# its control, the SYNC-model assertion, the call-site `raise` lock and its
# control, the banner pin and its control, the two vocabulary reads and the
# widened composition matrix -- all fixture-free, so both floors moved by the
# same 13: 152 bare and 160 vaulted, each read off a real green console run of
# its own configuration (160 from a normal run, 152 with RURIK_VAULT pointing
# at a directory that does not exist).
#
# 2026-08-21, REALFIX-F1: section 15 (--plane-carry) added 22, taking the two
# floors to 174 bare and 182 vaulted. Like section 14 it is entirely
# fixture-free -- it drives the same lifted receive arm with a second module
# flag set, reads the syntax tree and the startup banner, and takes no
# capture -- so the whole 22 lands in BOTH subsets and the 8-check gap between
# the two configurations is unchanged. Both numbers are read off real green
# console runs of their own configuration (182 from a normal run, 174 with
# RURIK_VAULT pointing at a directory that does not exist, which also printed
# its 2 declared skips). Neither is an enumeration.
#
# 2026-08-21, F1 SECOND PASS: section 15 took one more check -- a send that
# RAISES must not advance the carry slot, which is the only observable
# difference between writing that slot before the send and after it, and the
# ordering a mutation lane hoisted while every other check stayed green. Also
# fixture-free, so both floors move by the same 1: 175 bare and 183 vaulted,
# each read off a real green console run of its own configuration (183 normal,
# 175 with RURIK_VAULT pointing at a directory that does not exist).
#
# 2026-08-21, REALFIX-F1b: section 16 (--arrival-carry) added 31 and section
# 14's argv-completeness check was rewritten to read the composition function's
# own SIGNATURE instead of a literal list of eight names -- adding a ninth
# parameter turned it red, which is the check working, but "paste the new name
# in" is the only maintenance it can prompt and a list somebody pastes into is
# one that eventually gets pasted into wrongly. Same count, no drift. Section
# 16 is fixture-free like 14 and 15 -- it drives the same lifted receive arm
# with a third module flag and a FAKE CLOCK, exercises the three pure queue
# functions directly, reads the syntax tree and the startup banner, and opens
# nothing -- so the whole 32 lands in BOTH subsets and the 8-check gap between
# the configurations is unchanged: 207 bare and 215 vaulted. Both read off real
# green console runs of their own configuration (215 from a normal run, 207
# with RURIK_VAULT pointing at a directory that does not exist, which also
# printed its 2 declared skips). Neither is an enumeration.
#
# 2026-08-21, AFTER THE F1b MUTATION LANE: one check, and it is the survivor
# that lane found. Section 16's banner had its seventeen PROSE substrings pinned
# and the three-row counterfactual TABLE under them free -- deleting the rows,
# or rewriting the F1b row to the drafted "0 of 69" the offline screen had
# already refuted, left this file green at 215/215 either way. The new check
# rebuilds those rows from `grantsim.FIELD4_SCREEN`. It is fixture-free like the
# rest of 16 (the constant is a module literal; grantsim opens nothing at import),
# so both floors move by the same 1: 208 bare and 216 vaulted, each read off a
# real green run of its own configuration.
# 2026-08-25, the --resync run staging review: section 11 gained 3
# fixture-free checks -- HOLE D's SYNC MODEL NOT SEEDED print asserted to
# fire exactly once on an unseeded state, its refusals asserted to still
# land in the telemetry, and the seeded negative -- because the review's
# mutation pass showed the guard had zero coverage (condition inverted,
# every suite green). Both floors move by the same 3: 211 bare and 219
# vaulted, each read off a real green console run of its own configuration
# (219 from a normal run, 211 with RURIK_VAULT at an empty directory,
# which also printed its 2 declared skips).
# 2026-09-03, the client_pos source lock: section 11 gained 3 fixture-free
# checks -- the press-supersede FORGETS the client-sourced triple, the snap
# guard still reads the re-pinned point (the positive control: it is the whole
# behaviour the second writer existed to produce), and the --press-waits-for-leg
# arm forgets nothing. Each was shown red on its own mutation before the floor
# moved: reverting to ANIMREF-RE 39's write reddens the count AND the forget,
# dropping `state["pos"] = model` reddens the snap guard, and forgetting ahead
# of the flag guard reddens the control.
#
# AND THE FLOORS WERE ALREADY 9 BELOW A GREEN RUN, said out loud rather than
# absorbed into the +3. The declared 211/219 last matched reality on 2026-08-25;
# checks landed after it without the bump this block exists to record, so the
# pre-change run printed 228 vaulted against a floor of 219. A floor 9 light
# still catches a run that measured NOTHING, which is why nothing went red --
# but it is 9 checks of "fewer than a healthy run executes" that no longer had
# a guard, which is the hole the floor is for. Both figures below are read off
# real green console runs of their own configuration: 231 from a normal run,
# 223 with RURIK_VAULT at an empty directory, which also printed its 2 declared
# skips. The 8-check difference is still exactly section 10's 4 and section
# 13's 4, so the fixture accounting above is unchanged.
#
# 2026-09-03, the SECOND modelled placement: section 11 gained 4 more
# fixture-free checks, closing the site the block above named as deliberately
# left out. `_approach_send`'s snap re-pin sends a 0x002C at a point that may
# be OURS or the CLIENT'S, so the four are the forget, the positive control
# that the re-pin still reaches the follow leg it arms, and BOTH controls the
# asymmetry needs -- a re-pin at the client's own report forgets nothing, and
# the `repath=True` arm, which runs no guard at all, forgets nothing either.
# Each was shown red on its own mutation before this line moved, and the
# attribution was clean: deleting the forget reddens only the forget (that is
# HEAD's behaviour), dropping `state["pos"] = model` reddens only the positive
# control, dropping the `src == "leg"` test reddens only the report control,
# and hoisting the forget to the top of the function reddens both controls and
# neither of the first two. Read off real green runs of their own
# configuration: 235 from a normal run, 227 with RURIK_VAULT at an empty
# directory, which also printed its 2 declared skips. The 8-check difference
# is still exactly section 10's 4 and section 13's 4.
FLOOR_BARE = 227
FLOOR_FULL = 235
LEDGER = checks.Ledger("the position-trust policy: refuse, but never latch",
                       floor=FLOOR_BARE)
check = checks.adopt(LEDGER)

# THE FIXTURES, probed once. Section 10 needs the single 20260819 capture and
# section 13 needs all three of the 20260820 ones; each contributes exactly 4
# checks, which is the whole of the 8-check difference between the two floors.
S10_CAPTURE = "authsrv-20260819T114759-c1.jsonl"
S13_CAPTURES = ("authsrv-20260820T183311-c1.jsonl",
                "authsrv-20260820T182934-c1.jsonl",
                "authsrv-20260820T182554-c1.jsonl")


def _have_capture(name):
    return os.path.exists(
        os.path.join(vaultpath.vault_path("captures", "gamesrv"), name))


HAVE_S10 = _have_capture(S10_CAPTURE)
HAVE_S13 = all(_have_capture(n) for n in S13_CAPTURES)
# THE FLOOR FOLLOWS THE FIXTURES. Any mixed configuration keeps FLOOR_BARE,
# which is the protection it already had: a floor for a half-stocked machine
# would have to be measured on that machine, and this one cannot produce the
# measurement without hiding a fixture from itself.
if HAVE_S10 and HAVE_S13:
    LEDGER.floor = FLOOR_FULL

# The two real reports from run 20260819T114743, bit-exact from the capture.
# t=50.549817, the last position the old guard accepted before it latched:
ANCHOR = (9463.3544921875, 7945.9384765625)
# t=54.320344, 2,844 u away in 3.77 s and refused three times running. It is
# bit-identical to the click destination the server had granted 11.594 s
# earlier, and the client's own next report is reachable from it at 285 u/s.
JUMPED = (10995.26953125, 5549.82470703125)
JUMPED_PLANE = 18
# ONE SOURCE OF TRUTH with the floor probe above: if section 10's capture name
# and HAVE_S10's drifted apart, the floor would follow one and the skip the
# other, which is the failure the two floors exist to close.
CAPTURE = S10_CAPTURE


class FakeRec:
    """Records what the real Recorder would have written to the JSONL."""

    def __init__(self):
        self.events = []

    def event(self, kind, **fields):
        self.events.append(dict(fields, kind=kind))

    def of(self, kind):
        return [e for e in self.events if e["kind"] == kind]


def fresh(pos=ANCHOR, plane=0, seen=1000.0):
    return {"pos": pos, "plane": plane, "pos_seen": seen}


def receive_arm(opcode_name, params):
    """The SHIPPED body of one `elif opcode == NAME:` arm, as a callable.

    WHY THIS EXISTS AND WHY IT IS NOT A PARAPHRASE. Sections 7 to 9 lock the
    movement flags with AST matchers, which answer "is the source still shaped
    like the policy" and cannot answer "what goes on the wire when this report
    arrives". `--zero-lead`'s two hardest claims are behavioural -- a report the
    shipped `turned or not walking` gate would SKIP still grants under the flag,
    and the very same report sends NOTHING with the flag off -- and an AST
    matcher can only assert that some source exists near them.

    So the arm's own statements are lifted out of the receive loop, wrapped in a
    function of the four free names it needs, and compiled against
    `authsrv.__dict__` as globals. Every module-level name -- the flags
    included, so flipping `authsrv.ZERO_LEAD` is seen -- resolves to the
    server's own, and the body is re-extracted on every run, so it cannot go
    stale against a file that has moved on. It executes `authsrv.py`'s bytes,
    not a copy of them.

    `params` names the arm's free variables in call order: the heading arm needs
    (values, state, rec, send) and the stop arm needs `conn_id` too.
    """
    tree = ast.parse(open(authsrv.__file__, encoding="utf-8").read())
    node = None
    for n in ast.walk(tree):
        if (isinstance(n, ast.If) and isinstance(n.test, ast.Compare)
                and isinstance(n.test.left, ast.Name)
                and n.test.left.id == "opcode"
                and len(n.test.comparators) == 1
                and isinstance(n.test.comparators[0], ast.Name)
                and n.test.comparators[0].id == opcode_name):
            node = n
    if node is None:
        raise AssertionError(
            f"no `elif opcode == {opcode_name}:` arm in authsrv.py -- the "
            f"extractor must FAIL LOUDLY rather than hand back an empty body, "
            f"which would make every behaviour check below pass vacuously")
    args = ast.arguments(posonlyargs=[], args=[ast.arg(p) for p in params],
                         vararg=None, kwonlyargs=[], kw_defaults=[],
                         kwarg=None, defaults=[])
    fn = ast.FunctionDef(name="_arm", args=args, body=node.body,
                         decorator_list=[], returns=None, type_params=[])
    mod = ast.Module(body=[fn], type_ignores=[])
    ast.fix_missing_locations(mod)
    ns = {}
    exec(compile(mod, authsrv.__file__, "exec"),               # noqa: S102
         authsrv.__dict__, ns)
    return ns["_arm"]


def grantsim_heading_reasons():
    """`grantsim.HEADING_REASONS`, read out of its SOURCE rather than imported.

    Read rather than imported on purpose. `toolkit/clientscan/grantsim.py` is
    an offline scorer with its own import chain (`movesync`, `resyncscore`,
    `origin`) and this file is a server-side policy test that must keep running
    on a bare machine; taking that chain as an import dependency to read one
    frozenset would be paying a large bill for a small fact. The literal is
    parsed out of the file's own syntax tree, so it still cannot go stale, and
    a rename or a deletion raises here rather than passing vacuously.
    """
    path = os.path.join(os.path.dirname(HERE), "clientscan", "grantsim.py")
    tree = ast.parse(open(path, encoding="utf-8").read())
    for n in ast.walk(tree):
        if (isinstance(n, ast.Assign) and len(n.targets) == 1
                and isinstance(n.targets[0], ast.Name)
                and n.targets[0].id == "HEADING_REASONS"):
            return set(ast.literal_eval(n.value.args[0]))
    raise AssertionError(
        "no HEADING_REASONS assignment in grantsim.py -- this reader must FAIL "
        "LOUDLY rather than hand back an empty set, which would make the "
        "disjointness check below pass for the wrong reason")


class Sent:
    """A send() that records, and that stamps the server's own send-side hook."""

    def __init__(self, state, now=None):
        self.state, self.now, self.rows = state, now, []

    def __call__(self, opcode, values, label, quiet=False):
        now = self.now if self.now is not None else time.time()
        authsrv._note_wire_move(self.state, opcode, values, now)
        self.rows.append((opcode, values, label))

    def of(self, opcode):
        return [r for r in self.rows if r[0] == opcode]


def main():
    print("0. the constants carry their derivation")
    check(authsrv.CLIENT_POSITION_TRUST_RADIUS == 900.0,
          "the old radius survives, unchanged, as a FLOOR",
          "not retuned: no measurement supports any other value, and every "
          "value has the same latching defect at a different scale")
    check(authsrv.CLIENT_POSITION_TRUST_RATE == 580.0,
          "the growth rate is 288 + 292, two measured ceilings summed",
          "our integrator's own constant plus a ceiling over the client's "
          "fastest measured cruise step (291.20 u/s, n=184). Nothing fitted -- "
          "the house rule is to prefer the check with no free parameter, and a "
          "decay constant tau would have been one")
    check(authsrv.CLIENT_POSITION_REJECT_STREAK == 2,
          "and the escape hatch is the second consecutive refusal",
          "the 0-for-72 record argues for 1; 2 is the smallest value that "
          "still buys a single-frame refusal of a garbage decode")

    print("\n1. INVARIANT: the fix is a strict LOOSENING, at every dt")
    worst = None
    for i in range(0, 2001):
        dt = i * 0.01
        st = fresh(seen=1000.0 - dt)
        _a, _r, _j, budget = authsrv._position_verdict(st, (0.0, 0.0), 1000.0)
        if budget < authsrv.CLIENT_POSITION_TRUST_RADIUS:
            worst = (dt, budget)
            break
    check(worst is None,
          "over 20 s of silence in 10 ms steps, the budget never drops below "
          "the old 900 u",
          f"{worst} -- so no report today's code accepts can be refused by the "
          f"new one. This is the property that killed the tighter design: "
          f"BASE 120 + RATE*dt would newly refuse 8 corpus reports the flat 900 "
          f"accepts, all 8 in the run whose displacements have no established "
          f"cause")
    st = fresh(seen=1000.0)
    _a, _r, _j, b0 = authsrv._position_verdict(st, (0.0, 0.0), 1000.0)
    check(b0 == 900.0, "and at dt = 0 it IS the old 900 exactly", f"{b0}")

    print("\n2. THE HEADLINE: a refusal streak cannot outlive the streak limit")
    st, rec = fresh(), FakeRec()
    took = []
    now = 1000.0
    for i in range(12):
        now += 0.5
        took.append(authsrv._take_client_position(
            st, JUMPED, JUMPED_PLANE, rec, "0x003D", now=now))
    run = best = 0
    for t in took:
        run = 0 if t else run + 1
        best = max(best, run)
    check(best <= authsrv.CLIENT_POSITION_REJECT_STREAK,
          f"twelve presentations of a 2,844 u jump never refuse more than "
          f"{authsrv.CLIENT_POSITION_REJECT_STREAK} in a row",
          f"longest refusal run was {best}. The old code refused all twelve, "
          f"and refused 36 in a row in run 20260819T113049 -- for as long as "
          f"the player kept walking, the model could never come back")
    check(took[1] is True,
          "specifically, the SECOND presentation is adopted",
          f"{took[:3]} -- the first refusal is the single-frame guard, the "
          f"second is the server admitting it is the one that is lost")

    print("\n3. silence widens the budget, because our claim gets weaker")
    st = fresh(seen=1000.0 - 12.874)   # the measured maximum silence in the run
    accept, reason, jump, budget = authsrv._position_verdict(st, JUMPED, 1000.0)
    check(accept is True and reason == "in-budget",
          "after the measured 12.874 s silence a 2,844 u report is taken at "
          "once, with no refusal at all",
          f"{reason}, budget {budget:.0f}u vs drift {jump:.0f}u -- we had 12.9 "
          f"s of no information, and 900 u was never a defensible bound over "
          f"that interval")
    st = fresh(seen=1000.0 - 0.5)      # the modal report interval
    accept, reason, _j, budget = authsrv._position_verdict(st, JUMPED, 1000.0)
    check(accept is False and reason == "reject",
          "while at the modal 0.5 s cadence the same report is still refused "
          "once",
          f"{reason}, budget {budget:.0f}u -- the guard still exists; it just "
          f"cannot hold the line forever")

    print("\n4. position and plane are ONE fact")
    st, rec = fresh(), FakeRec()
    authsrv._take_client_position(st, JUMPED, JUMPED_PLANE, rec, "0x003D",
                                  now=1000.5)
    check(st["plane"] == 0,
          "a REFUSED report does not leave its plane behind",
          f"plane {st['plane']} -- the 0x003D arm used to write the plane "
          f"unconditionally 28 lines above the position guard, so run "
          f"20260819T114743 held plane 18 against (9463, 7946), a point our own "
          f"navmesh puts on plane 0. The click arm reads that plane to decide "
          f"whether it can place the player at all")
    check(st["pos"] == ANCHOR, "and does not move the position either",
          f"{st['pos']}")
    authsrv._take_client_position(st, JUMPED, JUMPED_PLANE, rec, "0x003D",
                                  now=1001.0)
    check(st["plane"] == JUMPED_PLANE and st["pos"] == JUMPED,
          "and when it is adopted, both land together",
          f"{st['pos']} plane {st['plane']}")

    print("\n5. a refusal does NOT refresh the anchor")
    st, rec = fresh(), FakeRec()
    authsrv._take_client_position(st, JUMPED, JUMPED_PLANE, rec, "0x003D",
                                  now=1000.5)
    check(st["pos_seen"] == 1000.0,
          "pos_seen still points at the last report we BELIEVED",
          f"{st['pos_seen']} -- if a refusal refreshed it the budget would stop "
          f"growing exactly when the model is most wrong, which is the latch "
          f"wearing a formula")

    print("\n6. the telemetry can go both ways, and names its source")
    st, rec = fresh(), FakeRec()
    authsrv._take_client_position(st, JUMPED, JUMPED_PLANE, rec, "0x003D",
                                  now=1000.5)
    recs = rec.of("position_report")
    check(len(recs) == 1 and recs[0]["accepted"] is False,
          "a refused report emits a record saying so",
          f"{recs} -- `accepted` was a LITERAL True until 2026-08-19, and the "
          f"record was emitted from the stop arm only, so no run could produce "
          f"accepted=False and the JSONL carried 5 of 62 reports. A check that "
          f"cannot fail is not a check, and this was one in our own telemetry")
    check(recs[0]["reason"] == "reject" and recs[0]["source"] == "0x003D",
          "carrying the reason and the arm it came from",
          f"{recs[0].get('reason')} / {recs[0].get('source')}")
    st, rec = fresh(), FakeRec()
    ok = authsrv._take_client_position(st, JUMPED, JUMPED_PLANE, rec, "0x0047",
                                       now=1000.5, stop=True)
    recs = rec.of("position_report")
    check(ok is True and recs[0]["reason"] == "stop-report",
          "and the stop arm DECLARES that it takes any distance",
          f"{recs[0].get('reason')} -- it accepted the 2,837 u correction that "
          f"rescued the model in run 20260819T114743, 1.24 s after the guarded "
          f"arm called the same coordinates impossible. Keeping it is measured "
          f"(ArenaNet echoes the client's stated stopping point verbatim in 70 "
          f"of 88 move-cancel windows); what is new is that it says so")
    check(st["pos"] == JUMPED and st["plane"] == JUMPED_PLANE,
          "and it moves both halves too", f"{st['pos']} plane {st['plane']}")

    print("\n7. the stop echo ships OFF, and it echoes the CLIENT")
    check(authsrv.STOP_ECHO is False,
          "--stop-echo is off by default",
          "it is the candidate fix for the teleport and it is unproven. The "
          "same corpus holds 13 grant-triggered displacements that do NOT land "
          "on a granted point, so disarming the destination may fix nothing. "
          "One watched run decides it")
    src = ast.parse(open(authsrv.__file__, encoding="utf-8").read())
    echoes = []
    for node in ast.walk(src):
        if not (isinstance(node, ast.If) and isinstance(node.test, ast.Name)
                and node.test.id == "STOP_ECHO"):
            continue
        for call in ast.walk(node):
            if (isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Name)
                    and call.func.id == "send"
                    and len(call.args) >= 2
                    and isinstance(call.args[1], ast.List)):
                echoes.append(call.args[1].elts)
    check(len(echoes) == 1, "there is exactly one echo send",
          f"{len(echoes)} -- two would mean two policies again")
    # THE MUTATION THIS LOCKS. The echo must carry the position the CLIENT just
    # reported. Rewriting it to send `state["pos"]`, or the click's `dest`,
    # turns a no-op into a real teleport at the player -- the exact damage the
    # 0x0047 arm's own comment records ("teleporting a player nine units is
    # pure damage"), sent on every single stop. A grep cannot tell the two
    # apart; the syntax tree can.
    payload = echoes[0] if echoes else []
    dest_arg = payload[1] if len(payload) > 1 else None
    check(isinstance(dest_arg, ast.Call)
          and isinstance(dest_arg.func, ast.Name) and dest_arg.func.id == "list"
          and len(dest_arg.args) == 1
          and isinstance(dest_arg.args[0], ast.Name)
          and dest_arg.args[0].id == "reported",
          "and its destination is `reported` -- the client's own figure, so the "
          "echo is zero-distance by construction",
          f"{ast.dump(dest_arg) if dest_arg is not None else None} -- if this "
          f"ever becomes state['pos'] or the click's dest, the message stops "
          f"being a no-op and starts teleporting the player on every stop")


    print("\n8. the direction we answer a heading with is UNIT LENGTH")
    # MEASURED on both sides of the wire, 2026-08-19. Retail's 0x0025 vec2:
    # |v| in [0.996546, 1.000000] in 3,789 of 3,789 across the 9 live captures,
    # 0 of 3,789 above 100 u. Ours before this fix: 4,704 of 4,760 at 765-768,
    # because the handler passed the client's own 0x003D heading -- a
    # DISPLACEMENT of magnitude 765.017..768.000 -- straight into a field the
    # client reads as a DIRECTION. Two populations, zero overlap.
    #
    # WHY A TEST FOR AN INERT BUG. It is inert: setter 0x00602660's case 1 is a
    # bare dword copy (so the client stores our number RAW for 82% of sends),
    # but the only float read of +0xBC inside AgAgent is the lazy angle cache at
    # 0x005FFA1D, which calls atan2 -- and atan2 is scale-invariant, so the
    # magnitude cannot reach anything. It is still worth locking, because
    # verbatim-first is how this repo decides what is true, and a wire field that
    # disagrees with retail by 768x is a standing invitation to explain some
    # future symptom with the wrong cause. The lock is here so that the next
    # person who "simplifies" this back to list(heading) argues with a red test.
    move_dir_sends = []
    for call in ast.walk(src):
        if (isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                and call.func.id == "send" and len(call.args) >= 2
                and isinstance(call.args[0], ast.Name)
                and call.args[0].id == "GAME_SMSG_AGENT_MOVE_DIRECTION"
                and isinstance(call.args[1], ast.List)):
            move_dir_sends.append(call.args[1].elts)
    check(len(move_dir_sends) == 1,
          "there is exactly one AGENT_MOVE_DIRECTION send site",
          f"{len(move_dir_sends)} -- a second one is a second policy, and the "
          f"765x defect survived this long because nobody looked at the one")

    def vector_arg(payload):
        """The vec2 slot of an [agent, vec2, byte] payload, or None."""
        return payload[1] if len(payload) > 1 else None

    vec = vector_arg(move_dir_sends[0] if move_dir_sends else [])
    # THE MUTATION THIS LOCKS, stated as the thing it must NOT be. list(heading)
    # is the defect, and it is one keystroke away from the fix.
    raw_passthrough = (isinstance(vec, ast.Call)
                       and isinstance(vec.func, ast.Name)
                       and vec.func.id == "list"
                       and len(vec.args) == 1
                       and isinstance(vec.args[0], ast.Name)
                       and vec.args[0].id == "heading")
    check(not raw_passthrough,
          "and it does not pass the client's raw heading through",
          "it sends list(heading) -- that vector is 765-768 units long, and "
          "retail's is 1.0 in 3,789 of 3,789")
    check(isinstance(vec, ast.Name) and vec.id == "unit",
          "it sends a normalised `unit`",
          f"{ast.dump(vec) if vec is not None else None}")

    # THE CONTROL. An AST matcher that cannot reject is not a check -- and the
    # rejecting branch above is the one that never runs against healthy source,
    # so it is exactly the branch a typo would silently disable. Hand it the
    # defect on purpose and require it to still recognise it.
    bad = ast.parse("send(GAME_SMSG_AGENT_MOVE_DIRECTION,"
                    " [PLAYER_AGENT_ID, list(heading), moving], 'x')")
    bad_payload = []
    for call in ast.walk(bad):
        if (isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                and call.func.id == "send" and len(call.args) >= 2
                and isinstance(call.args[0], ast.Name)
                and call.args[0].id == "GAME_SMSG_AGENT_MOVE_DIRECTION"
                and isinstance(call.args[1], ast.List)):
            bad_payload = call.args[1].elts
    bad_vec = vector_arg(bad_payload)
    check(isinstance(bad_vec, ast.Call) and isinstance(bad_vec.func, ast.Name)
          and bad_vec.func.id == "list",
          "and the same matcher still SEES the defect when handed it on purpose",
          "the matcher no longer recognises list(heading), so the check above "
          "passes for the wrong reason")

    # THE TRAILING BYTE IS ALREADY CORRECT, and this locks it AGAINST a
    # recommendation. Retail echoes the client's own movementType: 2,215 of
    # 2,254 (98.27%), the 39 disagreements all adjacent enum values at
    # transition instants. A 2026-08-19 workflow agent recommended rewriting it
    # as an angle; that was REFUTED in the same pass. Without this check a later
    # reader can find the recommendation and not the refutation.
    byte = move_dir_sends[0][2] if len(move_dir_sends[0]) > 2 else None
    check(isinstance(byte, ast.Name) and byte.id == "moving",
          "and the trailing byte is still the client's own movementType",
          f"{ast.dump(byte) if byte is not None else None} -- retail echoes the "
          f"enum in 98.27% of 2,254; it is not an angle")

    # The arithmetic, against the two magnitudes the client actually emits.
    for m in (765.017539, 768.000000):
        ux, uy = (m * 0.6) / m, (m * 0.8) / m
        check(abs(math.hypot(ux, uy) - 1.0) < 1e-9,
              f"normalising a {m:.3f}-unit heading yields |v| = 1",
              f"{math.hypot(ux, uy)!r}")
    # And the zero guard: 55 of our own sends carried |v| exactly 0, which is a
    # ZeroDivisionError in the naive form and kills the connection mid-session.
    zero_mag = 0.0
    guarded = ([0.0 / zero_mag, 0.0 / zero_mag] if zero_mag > 1e-6
               else [0.0, 0.0])
    check(guarded == [0.0, 0.0],
          "and a zero-length heading is guarded, not divided by",
          f"{guarded} -- 55 of 4,760 of our own sends carried |v| = 0")


    print("\n9. --client-endpoint ships OFF, and grants the CLIENT's own point")
    check(authsrv.CLIENT_ENDPOINT is False,
          "--client-endpoint is off by default",
          "it is the FIFTH candidate fix in this arc and four are dead. It is "
          "unproven until one run scores it")
    ce = []
    for node in ast.walk(src):
        if not (isinstance(node, ast.If) and isinstance(node.test, ast.Name)
                and node.test.id == "CLIENT_ENDPOINT"):
            continue
        for call in ast.walk(node):
            if (isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                    and call.func.id == "send" and len(call.args) >= 2
                    and isinstance(call.args[1], ast.List)):
                ce.append((node, call.args[1].elts))
    check(len(ce) == 1, "there is exactly one client-endpoint send",
          f"{len(ce)} -- two would be two policies, which is how the heading "
          f"arm ended up granting twice per report")

    # THE FIRST OF THE TWO THINGS THAT KILLED --heading-grant. It sent
    # `clip_to_walkable(...)` -- a point shortened wherever OUR navmesh says a
    # wall is. Where that disagrees with the client's own collision we grant a
    # point short of where the player is really going, the authoritative copy
    # stops early, and the separation that becomes the warp opens up. The
    # server's internal model may still clip; the WIRE may not.
    block = ce[0][0] if ce else None
    clipped = block is not None and any(
        isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
        and c.func.id == "clip_to_walkable" for c in ast.walk(block))
    check(not clipped,
          "and it does NOT clip the point it sends",
          "clip_to_walkable is back inside the block -- that is the first of "
          "the two defects that made --heading-grant warp the owner's character")

    # THE SECOND. It computed from `state["pos"]` rather than the report in
    # hand. Those are equal on every ACCEPTED report, so this is not a
    # correctness fix in the common case -- it is a fix for exactly the moment
    # the trust guard refused, which is when our model is least entitled to name
    # a destination.
    names = {n.id for n in ast.walk(block) if isinstance(n, ast.Name)} if block else set()
    check("reported" in names,
          "and it derives the point from `reported`",
          f"{sorted(names)[:8]} -- the client's own figure, so the granted "
          f"endpoint is the client's own proposal")
    subs = [n for n in ast.walk(block)
            if isinstance(n, ast.Subscript)] if block else []
    uses_state_pos = any(
        isinstance(n.value, ast.Name) and n.value.id == "state"
        and isinstance(getattr(n, "slice", None), ast.Constant)
        and n.slice.value == "pos" for n in subs)
    check(not uses_state_pos,
          "and not from state['pos']",
          "state['pos'] is back -- it is the last report the guard ACCEPTED, "
          "which is stale in exactly the window a refusal opens")

    # THE CONTROL. Both matchers above only ever run against healthy source, so
    # both are branches a typo would silently disable. Hand them the defect.
    bad = ast.parse("if CLIENT_ENDPOINT:\n"
                    "    d = clip_to_walkable(state, (state['pos'][0], 0))\n"
                    "    send(OP, [PLAYER_AGENT_ID, list(d), plane, plane], 'x')")
    bnode = next(n for n in ast.walk(bad)
                 if isinstance(n, ast.If) and isinstance(n.test, ast.Name))
    bad_clip = any(isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
                   and c.func.id == "clip_to_walkable" for c in ast.walk(bnode))
    bad_state = any(
        isinstance(n.value, ast.Name) and n.value.id == "state"
        and isinstance(getattr(n, "slice", None), ast.Constant)
        and n.slice.value == "pos"
        for n in ast.walk(bnode) if isinstance(n, ast.Subscript))
    check(bad_clip and bad_state,
          "CONTROL: both matchers still SEE the old defects when handed them",
          f"clip={bad_clip} state_pos={bad_state} -- if either stopped "
          f"matching, the two checks above would pass for the wrong reason")
    print("\n10. replay: the real refusals from run 20260819T114743")
    path = os.path.join(vaultpath.vault_path("captures", "gamesrv"), CAPTURE)
    if not os.path.exists(path):
        LEDGER.skip("capture replay",
                    f"{CAPTURE} is not in this vault; the policy sections "
                    f"above are fixture-free and still ran")
    else:
        rows = []
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    o = json.loads(line)
                except ValueError:
                    continue
                if o.get("kind") == "decoded" and o.get("opcode") in (61, 71):
                    rows.append((o["t"], tuple(o["values"][1]), o["values"][2],
                                 o["opcode"]))
        check(len(rows) >= 60,
              f"the capture still carries its {len(rows)} position reports",
              "62 when this was written: 57 on 0x003D and 5 on 0x0047")
        st = fresh(pos=rows[0][1], plane=rows[0][2], seen=rows[0][0])
        rec = FakeRec()
        refused = best = run = 0
        for t, pos, plane, op in rows[1:]:
            took = authsrv._take_client_position(
                st, pos, plane, rec, "0x0047" if op == 71 else "0x003D",
                now=t, stop=(op == 71))
            run = 0 if took else run + 1
            best = max(best, run)
            refused += (not took)
        check(best <= authsrv.CLIENT_POSITION_REJECT_STREAK,
              f"replaying all {len(rows)} of them, the longest refusal run is "
              f"{best}",
              f"the server printed 4 refusals for this run, 3 of them "
              f"consecutive, and only recovered because the player stopped "
              f"walking and sent a 0x0047")
        check(st["pos"] == rows[-1][1],
              "and the model ends the run where the client says it is",
              f"{st['pos']} vs {rows[-1][1]}")
        check(len(rec.of("position_report")) == len(rows) - 1,
              f"with one telemetry record per report ({len(rows) - 1}), not "
              f"per stop",
              f"{len(rec.of('position_report'))} -- the capture on disk holds 5 "
              f"because the old code only recorded stops")
        print(f"     refused {refused} of {len(rows) - 1}, "
              f"longest run {best}")

    print("\n11. --resync ships OFF, and its payload is the CLIENT's own report")
    # WHAT EARNS THIS SECTION. 0x002C AGENT_UPDATE_POSITION is the only
    # catalogued primitive whose handler reaches BOTH copies the client keeps
    # with no gate (0x005FDAE5 on [agentMgr+0xE8], 0x005FDB49 on
    # [agentMgr+0x14C]) and clears the AgTrack record first (0x005FDA78), so it
    # is the one lever this arc has left. It is ALSO the message an earlier
    # build sent and had removed as "the warp the player described" -- because
    # that build sent OUR INTEGRATOR'S position. The whole difference between a
    # fix and that regression is which value ends up in the payload, and
    # `state["pos"]` is one keystroke away from `state["client_pos"]`. Every
    # check below exists to make that keystroke red.
    check(authsrv.RESYNC is False,
          "--resync is off by default",
          "it is the SEVENTH candidate in this arc and six are dead. A hard "
          "SetPosition at the player is a teleport by construction; it ships "
          "off until a watched run scores it")
    check(authsrv.RESYNC_SEPARATION == 100.0,
          "the trigger is the CLIENT's own 100.0 u radius, not a number we "
          "chose",
          "0x00946560 -- the radius inside which the client's own match test "
          "0x00605AF0 returns 'no snap' before the fallback half runs. It sits "
          "3x under gate 1's real cut of 299.332591 u, and that factor is the "
          "headroom our SYNC model gets to be wrong in")
    ceiling = 299.332591 / (2 * authsrv.DEFAULT_RUN_SPEED)
    check(authsrv.RESYNC_MIN_INTERVAL < ceiling,
          f"and the rate limit sits under its derived ceiling of "
          f"{ceiling:.4f} s",
          f"{authsrv.RESYNC_MIN_INTERVAL} -- two copies moving directly apart "
          f"separate at no more than 2 x 288 u/s, so a limit at or above "
          f"{ceiling:.4f} s lets a full gate's worth of separation accrue "
          f"between two fires, which is the sender being structurally late")
    harm = authsrv.RESYNC_MAX_REPORT_AGE * authsrv.DEFAULT_RUN_SPEED
    check(abs(harm - 100.0) < 1e-9,
          "and the staleness bound IS the harm bound: speed x age = 100.0 u",
          f"{harm!r} -- a SetPosition to the client's last report yanks the "
          f"RENDERED copy backwards by at most how far the client walked since "
          f"that report. Choosing the age chooses the harm, and the age is "
          f"chosen to make the harm the client's own 'close enough' radius. "
          f"CORROBORATED: for report gaps under 0.100 s the client's own step "
          f"is p99 28.80 u against a budget of 28.8 (n = 307), and under "
          f"0.200 s p99 57.60 against 57.6 (n = 685), 73 `ours` captures")

    def armed(client=(1000.0, 0.0), ours=(0.0, 0.0), sync=(0.0, 0.0),
              at=1000.0, plane=0):
        """A state with a fresh client report and a seeded, PARKED sync model."""
        st = {"pos": ours, "plane": plane, "pos_seen": at,
              "client_pos": client, "client_plane": plane,
              "client_pos_at": at,
              "sync_from": sync, "sync_to": None, "sync_at": at}
        return st

    class Wire:
        """A send() that also runs the real model hook, like the server's."""

        def __init__(self, state):
            self.state = state
            self.sent = []

        def __call__(self, opcode, values, label, quiet=False):
            authsrv._note_wire_move(self.state, opcode, values, 1000.0)
            self.sent.append((opcode, values, label))

    # OFF MEANS OFF: not merely "does not send", but does not even evaluate.
    st = armed()
    wire, rec = Wire(st), FakeRec()
    fired = authsrv._maybe_resync(wire, st, rec, now=1000.0)
    check(fired is False and wire.sent == [] and rec.events == [],
          "with the flag off a state that WOULD fire sends nothing and records "
          "nothing",
          f"fired={fired} sent={wire.sent} events={len(rec.events)} -- the "
          f"default build's capture must not grow a resync log it never used")

    saved = authsrv.RESYNC
    authsrv.RESYNC = True
    try:
        # THE HEADLINE: the payload is the CLIENT's figure, and the two are made
        # to DISAGREE on purpose. state["pos"] is a blend -- the world tick's
        # integrator writes it too -- so a sender reading it would put our
        # extrapolation on the wire, which is exactly the removed regression.
        st = armed(client=(1000.0, 0.0), ours=(1234.0, 567.0))
        wire, rec = Wire(st), FakeRec()
        fired = authsrv._maybe_resync(wire, st, rec, now=1000.0)
        check(fired is True and len(wire.sent) == 1,
              "a 1,000 u separation with a fresh report fires exactly one 0x002C",
              f"fired={fired} sent={wire.sent}")
        op, values, _label = wire.sent[0]
        check(op == authsrv.GAME_SMSG_AGENT_UPDATE_POSITION == 0x002C,
              "on the right opcode", f"0x{op:04x}")
        check(values[1] == [1000.0, 0.0] and values[1] != list(st["pos"]),
              "carrying state['client_pos'] and NOT state['pos']",
              f"{values} against ours {st['pos']} -- the build that sent this "
              f"message before sent OUR integrator's position, and its five "
              f"sends carried the client 630, 189 and 765 units. 765 is one "
              f"heading vector: the integrator had walked the whole leg while "
              f"the client had not moved at all")
        check(values[0] == authsrv.PLAYER_AGENT_ID and values[2] == 0,
              "naming the player's agent, with the plane the report arrived on",
              f"{values} -- position and plane are one fact (section 4), and "
              f"this reads the pair the accept path wrote together")

        # REFUSES A PAYLOAD THAT IS NOT CLIENT-SOURCED. A state carrying only
        # our own blend has no client_pos at all, and the verdict must not fall
        # back to it.
        # It carries client_plane and NOT client_pos on purpose: that is the
        # split section 4 is about, and it leaves the missing client POSITION as
        # the only thing standing between this state and a send. A fixture
        # missing three fields would be refused for whichever one is checked
        # first, which is a weaker proof than it looks.
        blind = {"pos": (5000.0, 5000.0), "plane": 0, "pos_seen": 1000.0,
                 "client_plane": 0,
                 "sync_from": (0.0, 0.0), "sync_to": None, "sync_at": 1000.0}
        wire, rec = Wire(blind), FakeRec()
        fired = authsrv._maybe_resync(wire, blind, rec, now=1000.0)
        verdict = authsrv._resync_verdict(blind, 1000.0)
        check(fired is False and wire.sent == []
              and verdict[1] == "no-client-report",
              "a state with no accepted client report sends NOTHING, however "
              "far our own model has drifted",
              f"{verdict} -- 5,000 u of drift and not one byte, because the "
              f"only position this sender is allowed to say is one the client "
              f"said first")
        check(len(rec.of("resync")) == 1
              and rec.of("resync")[0]["fired"] is False,
              "and the refusal is in the event log, not just absent from it",
              f"{rec.of('resync')} -- a resync log holding only its own "
              f"successes cannot be used to score the flag")

        # HOLE D MADE LOUD, AND THE LOUDNESS IS CHECKED. The 2026-08-25
        # review's mutation (d) -- the no-sync-model condition inverted, the
        # once-latch inverted, or the print deleted outright -- survived
        # every test in the tree until this block, and a guard nobody has
        # seen fire is a wish. A state carrying an ACCEPTED report but no
        # sync seed is the permanently-inert regime the p5 recon reproduced
        # by accident (`no-sync-model` x 14, zero fires, a silent
        # zero-exposure null): the guard must say so on the console, ONCE
        # per connection, and never on a seeded state.
        unseeded = {"pos": (5000.0, 5000.0), "plane": 0, "pos_seen": 1000.0,
                    "client_pos": (1000.0, 0.0), "client_pos_at": 1000.0,
                    "client_plane": 0}
        wire, rec = Wire(unseeded), FakeRec()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            f1 = authsrv._maybe_resync(wire, unseeded, rec, now=1000.0)
            f2 = authsrv._maybe_resync(wire, unseeded, rec, now=1000.1)
        prints = buf.getvalue().count("SYNC MODEL NOT SEEDED")
        check(f1 is False and f2 is False and wire.sent == [] and prints == 1
              and authsrv._resync_verdict(unseeded, 1000.0)[1]
              == "no-sync-model",
              "an unseeded sync model prints SYNC MODEL NOT SEEDED exactly "
              "once across repeated verdicts, and still sends nothing",
              f"prints={prints}, verdict "
              f"{authsrv._resync_verdict(unseeded, 1000.0)[1]!r} -- HOLE D "
              f"(followon-notes/p5-resync-disarm.md sec.3.5): without the "
              f"line, a session that skipped the placement seed runs the "
              f"whole flag as a silent zero-exposure null")
        check(len(rec.of("resync")) == 2
              and all(r["reason"] == "no-sync-model"
                      for r in rec.of("resync")),
              "both refusals still land in the event log -- the print is an "
              "addition to the telemetry, never a substitute",
              f"{rec.of('resync')}")
        seeded = armed(client=(1000.0, 0.0), ours=(1234.0, 567.0))
        wire, rec = Wire(seeded), FakeRec()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            authsrv._maybe_resync(wire, seeded, rec, now=1000.0)
        check("SYNC MODEL NOT SEEDED" not in buf.getvalue(),
              "and a seeded state never prints it",
              "the negative half: a warning that fires on healthy sessions "
              "trains the operator to ignore it, which un-louds the guard")

        # REFUSES A STALE PAYLOAD, at the bound and past it.
        st = armed(at=1000.0)
        edge = 1000.0 + authsrv.RESYNC_MAX_REPORT_AGE
        check(authsrv._resync_verdict(st, edge)[0] is True,
              f"a report exactly {authsrv.RESYNC_MAX_REPORT_AGE * 1000:.0f} ms "
              f"old still fires -- the bound is inclusive",
              f"{authsrv._resync_verdict(st, edge)}")
        past = edge + 1e-6
        wire, rec = Wire(st), FakeRec()
        fired = authsrv._maybe_resync(wire, st, rec, now=past)
        check(fired is False and wire.sent == []
              and authsrv._resync_verdict(st, past)[1] == "stale",
              "one microsecond past it, nothing goes out",
              f"{authsrv._resync_verdict(st, past)} -- past the bound the "
              f"payload has stopped being where the client is, and a stale "
              f"payload IS the old failure mode")
        check(authsrv._resync_verdict(st, 999.0)[1] == "stale",
              "and a report dated in the FUTURE is stale too, not fresh",
              f"{authsrv._resync_verdict(st, 999.0)} -- `now - at` goes "
              f"negative under clock skew, and a negative age would sail "
              f"through an upper-bound-only test")

        # THE RATE LIMIT.
        st = armed()
        wire, rec = Wire(st), FakeRec()
        n = 0
        t = 1000.0
        for _i in range(20):
            st["client_pos_at"] = t          # a fresh report every 100 ms
            st["sync_from"], st["sync_to"] = (0.0, 0.0), None
            n += bool(authsrv._maybe_resync(wire, st, rec, now=t))
            t += 0.1
        span = 1.9                            # first fire at t0, last at t0+1.9
        allowed = int(span / authsrv.RESYNC_MIN_INTERVAL) + 1
        check(n <= allowed,
              f"twenty consecutive fireable reports over {span:.1f} s produce "
              f"{n} sends, not 20",
              f"n={n}, ceiling {allowed} at one per "
              f"{authsrv.RESYNC_MIN_INTERVAL:.2f} s -- an unlimited sender is "
              f"a 2 Hz teleport stream at the player")
        check(n >= 1, "and it does not rate-limit itself down to nothing",
              f"n={n} -- a limit that never lets anything through would make "
              f"every check above vacuous")

        # NEVER FIRES ON A REPORT THE TRUST GUARD REFUSED, and this is the
        # one an adversarial review found reachable at 2,282 u. The payload
        # advances only on accept, so a refusal FREEZES it while the client
        # keeps moving -- and the guard refuses exactly when the client claimed
        # a jump over CLIENT_POSITION_TRUST_RADIUS. Inside the staleness window
        # every other gate still passes, so without this the server would
        # hard-SetPosition the player back to their pre-jump point: the
        # regression the whole design exists to avoid, by a different route.
        st = armed(client=(0.0, 0.0), sync=(1000.0, 0.0))
        fire_clean, why_clean = authsrv._resync_verdict(st, 1000.0)[:2]
        check(fire_clean is True and why_clean == "resync",
              "CONTROL: the same state with no refusal on record DOES fire",
              f"{why_clean} -- a check whose control cannot fire is judging "
              f"nothing, and this one is the whole point of the next check")
        st["pos_rejects"] = 1
        wire, rec = Wire(st), FakeRec()
        fired = authsrv._maybe_resync(wire, st, rec, now=1000.0)
        check(fired is False and wire.sent == []
              and authsrv._resync_verdict(st, 1000.0)[1] == "report-refused",
              "but one refused report on record blocks it, payload unsent",
              f"{authsrv._resync_verdict(st, 1000.0)} -- the freshest thing we "
              f"heard was one we did not believe, so the frozen payload is a "
              f"pre-jump position and sending it is the old warp")

        # NEVER FIRES WHEN THE TWO COPIES AGREE.
        st = armed(client=(50.0, 0.0), sync=(0.0, 0.0))
        wire, rec = Wire(st), FakeRec()
        fired = authsrv._maybe_resync(wire, st, rec, now=1000.0)
        check(fired is False and wire.sent == []
              and authsrv._resync_verdict(st, 1000.0)[1] == "in-agreement",
              f"50 u apart is under the {authsrv.RESYNC_SEPARATION:.0f} u "
              f"trigger and sends nothing",
              f"{authsrv._resync_verdict(st, 1000.0)} -- correcting a player "
              f"who is already right is the 'teleporting a player nine units "
              f"is pure damage' case the 0x0047 arm records")

        # THE SYNC MODEL FAILS CLOSED, and it tracks a glide rather than
        # assuming the copy is already parked.
        unseeded = {"pos": (0.0, 0.0), "plane": 0, "pos_seen": 1000.0,
                    "client_pos": (9000.0, 0.0), "client_plane": 0,
                    "client_pos_at": 1000.0}
        check(authsrv._sync_position(unseeded, 1000.0) is None
              and authsrv._resync_verdict(unseeded, 1000.0)[1]
              == "no-sync-model",
              "an unseeded SYNC model produces no separation and no send",
              f"{authsrv._resync_verdict(unseeded, 1000.0)} -- a fixture that "
              f"silently resolves to the wrong thing turns every assertion "
              f"behind it into a no-op; this one raises its hand instead")
        glide = armed(client=(0.0, 0.0), sync=(0.0, 0.0))
        authsrv._note_wire_move(glide, authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT,
                                [authsrv.PLAYER_AGENT_ID, [2880.0, 0.0], 0, 0],
                                1000.0)
        half = authsrv._sync_position(glide, 1005.0)
        check(abs(half[0] - 1440.0) < 1e-6,
              "and a granted leg is walked at 288 u/s, not teleported to its "
              "end",
              f"{half} at t+5 s of a 2,880 u grant -- this is the client's own "
              f"bake (0x005FE950 velocity = unit(d) * speed, 0x005FFB40 "
              f"pos = +0x78 + vel * dt). If the model parked instantly, every "
              f"legitimate click-walk would read as a 2,880 u desync")
        parked = authsrv._sync_position(glide, 1099.0)
        check(parked == (2880.0, 0.0),
              "and it PARKS on the granted point rather than overshooting it",
              f"{parked} -- 0x005FF820's +0x48 arm returns the stored "
              f"destination, which is semantic and not a cache")
        authsrv._note_wire_move(glide, authsrv.GAME_SMSG_AGENT_UPDATE_POSITION,
                                [authsrv.PLAYER_AGENT_ID, [7.0, 8.0], 0],
                                1100.0)
        check(authsrv._sync_position(glide, 1200.0) == (7.0, 8.0),
              "and a 0x002C we send lands the model on the point it carried",
              f"{authsrv._sync_position(glide, 1200.0)} -- 0x00602B20 writes "
              f"+0x68..+0x74 = current on the parked arm, so no destination "
              f"survives a hard set; a model that kept the old one would think "
              f"the copy walked away again")

        # THE ENCODED BYTES ARE THE SCHEMA'S. Not "we believe the shape" -- the
        # real codec, against the real catalog, checked field by field.
        blob = authsrv.codec.encode(
            "GAME_SMSG", authsrv.GAME_SMSG_AGENT_UPDATE_POSITION,
            [authsrv.PLAYER_AGENT_ID, [1234.5, -678.25], 7])
        shape = json.load(open(os.path.join(
            os.path.dirname(os.path.dirname(HERE)), "schema",
            "messages.json"), encoding="utf-8"))
        entry = shape["channels"]["GAME_SMSG"]["messages"]["44"]
        check([f["type"] for f in entry["fields"]]
              == ["msg_header", "dword", "vec2", "word"],
              "the catalog's 0x002C is header / agent id / vec2 / plane",
              f"{[f['type'] for f in entry['fields']]} -- and the client's own "
              f"handler agrees field for field: [ebx+4] is pushed to "
              f"AgTrack::Clear at 0x005FDA78, [ebx+8]/[ebx+0xc] become the "
              f"position block, [ebx+0x10] is its plane word")
        check(len(blob) == entry["declared_unpack_size"] == 16,
              f"and the encoder produces the declared {len(blob)} bytes",
              f"{blob.hex()}")
        check(blob == bytes.fromhex("2c00") + struct.pack(
                  "<Iff H", authsrv.PLAYER_AGENT_ID, 1234.5, -678.25, 7),
              "byte for byte, in that field order",
              f"{blob.hex()} -- field order is the one thing this project has "
              f"already got wrong on a movement message, on 0x0029's two plane "
              f"words, and the client walked players through staircases for it")
        check(authsrv.codec.name_for("GAME_SMSG", 0x002C)
              == "AGENT_UPDATE_POSITION",
              "and the opcode we send is the one the overrides name",
              f"{authsrv.codec.name_for('GAME_SMSG', 0x002C)}")
    finally:
        authsrv.RESYNC = saved
    check(authsrv.RESYNC is False,
          "and the section put the flag back the way it found it",
          f"{authsrv.RESYNC}")

    # A REFUSED REPORT MUST NOT UPDATE THE CLIENT-SOURCED RECORD. This is what
    # makes "the payload came from an accepted report" true rather than merely
    # intended: the accept path is the only writer, so a refusal leaves the
    # sender holding the older -- and ageing -- report.
    st, rec = fresh(), FakeRec()
    authsrv._take_client_position(st, JUMPED, JUMPED_PLANE, rec, "0x003D",
                                  now=1000.5)
    check("client_pos" not in st,
          "a REFUSED report leaves no client-sourced position behind",
          f"{st.get('client_pos')} -- if a refusal wrote it, the resync sender "
          f"would put a position our own trust guard had just called "
          f"impossible onto the wire as a teleport")
    authsrv._take_client_position(st, JUMPED, JUMPED_PLANE, rec, "0x003D",
                                  now=1001.0)
    check(st["client_pos"] == JUMPED and st["client_plane"] == JUMPED_PLANE
          and st["client_pos_at"] == 1001.0,
          "and an ACCEPTED one writes the position, the plane and the instant "
          "together",
          f"{st.get('client_pos')} plane {st.get('client_plane')} at "
          f"{st.get('client_pos_at')}")

    # THE SOURCE LOCK, and the control that keeps it honest. The behavioural
    # checks above can only see the value; this sees the EXPRESSION, because
    # `state["pos"]` and `state["client_pos"]` differ by nine characters and
    # agree on most reports -- exactly the shape that let the 765x direction
    # vector live for weeks.
    writers = []
    for node in ast.walk(src):
        if not isinstance(node, ast.Assign):
            continue
        for tgt in node.targets:
            if (isinstance(tgt, ast.Subscript)
                    and isinstance(tgt.value, ast.Name)
                    and tgt.value.id == "state"
                    and isinstance(getattr(tgt, "slice", None), ast.Constant)
                    and tgt.slice.value == "client_pos"):
                writers.append(node)
    check(len(writers) == 1,
          "exactly one line in the whole file writes state['client_pos']",
          f"{len(writers)} -- two writers is two policies, and the second one "
          f"is where an integrator's opinion gets in. This has gone red once "
          f"for real: ANIMREF-RE 39 (2809d98) added a write in "
          f"_press_supersedes carrying `_click_leg_start`'s dead-reckoned "
          f"point, which is the server's integrator by construction -- and "
          f"it wrote client_pos and client_pos_at but NOT client_plane, "
          f"splitting the triple _take_client_position writes as one fact "
          f"and leaving the cast-stop reckon (which requires all three) free "
          f"to pair a modelled point with a plane measured somewhere else")

    # THE COUNT IS NOT THE POINT, AND ON ITS OWN IT IS A RULE NOTHING CHECKS.
    # A line count cannot see WHY the second writer existed, and that reason
    # was real: `_click_leg_start`'s fallback is `client_pos or pos`, so after
    # a press ends a click leg, a client_pos left at the leg's START is what
    # `_approach_send`'s snap guard reads -- and it would re-pin the body back
    # there, the warp ANIMREF-RE 39 was built to remove. The fix is to FORGET
    # the report rather than to overwrite it with the model: a 0x002C at a
    # modelled point means we no longer know what the client would say, and
    # every consumer of the triple fails closed until it speaks again. These
    # three checks pin the mechanism, so a reorder that puts the forget before
    # `state["pos"]` is set -- or a revert to the write -- goes red HERE and
    # not only in the count above.
    def mid_leg():
        """A body 1.0 s into a 500 u click leg from (0,0), server copy at the
        start, and a client report at the start with its own plane."""
        t0 = time.time() - 1.0
        return {"pos": (0.0, 0.0), "plane": 0,
                "client_pos": (0.0, 0.0), "client_plane": 3,
                "client_pos_at": t0,
                "click_moving_at": t0,
                "click_leg": authsrv._leg_record((0.0, 0.0), (500.0, 0.0),
                                                 t0, 288.0)}

    st = mid_leg()
    authsrv._press_supersedes(lambda *a, **k: None, st, 0, 10)
    check("client_pos" not in st and "client_plane" not in st
          and "client_pos_at" not in st,
          "a press that supersedes the click leg FORGETS the whole "
          "client-sourced triple rather than overwriting it with the model",
          f"pos={st.get('client_pos')} plane={st.get('client_plane')} "
          f"at={st.get('client_pos_at')} -- the placement is OUR point, so "
          f"the last report is now known-wrong AND unreplaceable: "
          f"_resync_verdict answers 'no-client-report', _keepalive_ok "
          f"'no-report', the cast-stop reckon 'no-report'. Overwriting "
          f"instead would hand both wire senders our own extrapolation "
          f"stamped `now`, which passes the RESYNC_MAX_REPORT_AGE freshness "
          f"gate the report's own age exists to bound")
    model = authsrv._click_leg_start(st, time.time(), False)
    check(model is not None and abs(model[0] - 288.0) < 2.0
          and abs(model[1]) < 1e-6,
          "and the snap guard still reads the RE-PINNED point, which is the "
          "whole behaviour the second writer existed to produce",
          f"{model} -- `_click_leg_start`'s fallback is `client_pos or pos` "
          f"and the press set `pos` to the placement one line above the "
          f"forget, so dropping the stale report yields 288 u along the leg "
          f"(1.0 s at 288 u/s) by the SAME arithmetic the write produced it "
          f"with. Left at the leg's start this reads (0, 0) and "
          f"`_approach_send` re-pins the body 288 u backwards")
    saved_press = authsrv.PRESS_SUPERSEDES_LEG
    authsrv.PRESS_SUPERSEDES_LEG = False
    try:
        st2 = mid_leg()
        authsrv._press_supersedes(lambda *a, **k: None, st2, 0, 10)
    finally:
        authsrv.PRESS_SUPERSEDES_LEG = saved_press
    check(st2.get("client_pos") == (0.0, 0.0) and st2.get("client_plane") == 3,
          "CONTROL: the revert arm (--press-waits-for-leg) forgets NOTHING, "
          "so the forget is attributable to the supersede and not to the "
          "fixture",
          f"pos={st2.get('client_pos')} plane={st2.get('client_plane')} -- "
          f"this arm sends no 0x002C, so no placement has contradicted the "
          f"report and it must survive intact. Without this control the "
          f"check above passes on a `_press_supersedes` that clears the "
          f"triple unconditionally, including on the arm that never moved "
          f"the body")

    # THE SECOND MODELLED PLACEMENT, and the ASYMMETRY that tells it from the
    # three that are not. `_approach_send`'s snap guard sends its own 0x002C at
    # `_click_leg_start`'s point when the server's copy has fallen more than the
    # client's 100 u reprieve behind the modelled body. It is NOT a client_pos
    # writer, so the source lock above cannot see it -- and until 2026-09-03 it
    # left exactly the stale report the press-supersede arm used to launder.
    #
    # WHY THAT MATTERS, stated as the failure and not as a tidiness argument:
    # the send re-seeds the sync model onto its OWN point (`_note_wire_move`
    # sets sync_from = point, sync_to = None), so `_keepalive_ok` next computes
    # sep = hypot(client_pos - sync) with client_pos still at the click leg's
    # START. That is the separation which just fired this re-pin, so it is over
    # KEEPALIVE_SEPARATION by construction, and the grant goes out at the leg
    # start -- walking the body back down the leg it just walked.
    # `_resync_verdict` has the same shape and hard-SETS both copies there.
    # Both consumers ship OFF, so these four checks are the only thing standing
    # between the defect and the flag that turns it on.
    #
    # AND THIS SITE IS THE ONLY ONE THAT CAN GO EITHER WAY, which is the whole
    # reason it asks `_click_leg_source` rather than forgetting outright:
    # "leg" is our dead-reckoned lerp and CONTRADICTS the report, while
    # "report" IS the report and agrees with it -- the `_agtrack_maybe_repin` /
    # `_maybe_resync` case, where forgetting would fail every consumer closed
    # over a fact we still hold. Checks 3 and 4 are that half.
    TARGET = {"pos": (2000.0, 0.0), "name": "a test dummy"}

    def approach_mid_leg():
        """A body 1.0 s into a 500 u click leg from (0,0); the server's SYNC
        model still parked at the leg's start, and the client's last report
        there too -- the state the guard's own comment describes."""
        t0 = time.time() - 1.0
        return {"pos": (0.0, 0.0), "plane": 0,
                "client_pos": (0.0, 0.0), "client_plane": 3,
                "client_pos_at": t0,
                "click_moving_at": t0,
                "click_leg": authsrv._leg_record((0.0, 0.0), (500.0, 0.0),
                                                 t0, 288.0),
                "sync_from": (0.0, 0.0), "sync_to": None, "sync_at": t0}

    def approach_run(st, repath=False):
        """Drive the guard and hand back every 0x002C it emitted."""
        pins = []

        def send(opcode, values, _label=None):
            if opcode == authsrv.GAME_SMSG_AGENT_UPDATE_POSITION:
                pins.append(values)

        authsrv._approach_send(send, st, 0, 10, TARGET, time.time(),
                               repath=repath)
        return pins

    st3 = approach_mid_leg()
    pins3 = approach_run(st3)
    check(len(pins3) == 1 and "client_pos" not in st3
          and "client_plane" not in st3 and "client_pos_at" not in st3,
          "the approach snap re-pin FORGETS the client-sourced triple too, "
          "for the same reason the press-supersede does",
          f"{len(pins3)} re-pins, pos={st3.get('client_pos')} "
          f"plane={st3.get('client_plane')} at={st3.get('client_pos_at')} -- "
          f"a report left at the leg's START after a placement at its END is "
          f"what `_keepalive_ok` then measures its separation against, and it "
          f"grants AGENT_MOVE_TO_POINT back at the start. The lock above "
          f"cannot catch this: the site writes nothing, it merely fails to "
          f"drop what it has invalidated")
    check(len(pins3) == 1 and abs(pins3[0][1][0] - 288.0) < 2.0
          and abs(pins3[0][1][1]) < 1e-6
          and st3.get("click_leg") is not None
          and abs(st3["click_leg"]["p0"][0] - 288.0) < 2.0,
          "and the guard still re-pins at the modelled leg end AND the follow "
          "it arms starts from there -- the behaviour, either side of the "
          "forget",
          f"pin={pins3[0][1] if pins3 else None} "
          f"follow p0={(st3.get('click_leg') or {}).get('p0')} -- the payload "
          f"is read BEFORE `state['pos'] = model` and the follow's start is "
          f"read AFTER it, so this brackets the write the forget depends on: "
          f"drop that line and the 0x002C still says 288 while the follow "
          f"walks from 0, which is the leg re-walked. Expected 288 u along "
          f"the leg (1.0 s at 288 u/s) on both")

    def approach_report_point():
        """Parked after a KEYBOARD leg: no click leg, so `_click_leg_source`
        answers "report" -- a fresh report 400 u from where the sync copy
        parked at the last grant. The guard fires at the CLIENT's own point."""
        t0 = time.time() - 0.2
        return {"pos": (400.0, 0.0), "plane": 0,
                "client_pos": (400.0, 0.0), "client_plane": 3,
                "client_pos_at": t0,
                "click_moving_at": None, "click_leg": None,
                "sync_from": (0.0, 0.0), "sync_to": None, "sync_at": t0}

    st4 = approach_report_point()
    pins4 = approach_run(st4)
    check(len(pins4) == 1 and abs(pins4[0][1][0] - 400.0) < 1e-6
          and st4.get("client_pos") == (400.0, 0.0)
          and st4.get("client_plane") == 3,
          "CONTROL: a re-pin that fires at the CLIENT'S OWN REPORT forgets "
          "NOTHING -- the placement agrees with the record, so the record "
          "still holds",
          f"{len(pins4)} re-pins at {pins4[0][1] if pins4 else None}, "
          f"pos={st4.get('client_pos')} plane={st4.get('client_plane')} -- "
          f"this is `_agtrack_maybe_repin`'s and `_maybe_resync`'s case "
          f"reached through the approach, and it is what makes the forget "
          f"above attributable to the point's SOURCE rather than to the site. "
          f"Without it, an unconditional forget passes every check above and "
          f"fails every consumer closed over a report nothing contradicted")

    st5 = approach_mid_leg()
    pins5 = approach_run(st5, repath=True)
    check(not pins5 and st5.get("client_pos") == (0.0, 0.0)
          and st5.get("client_plane") == 3,
          "CONTROL: the re-path arm runs no snap guard, sends no 0x002C and "
          "so forgets nothing",
          f"{len(pins5)} re-pins, pos={st5.get('client_pos')} "
          f"plane={st5.get('client_plane')} -- `repath=True` is the 0.5 Hz "
          f"re-issue while the target moves, and the guard is inside "
          f"`if not repath:`. Hoist the forget out of that block and a moving "
          f"target blows away a fresh report twice a second, on an arm that "
          f"placed nothing")
    resync_sends = []
    for node in ast.walk(src):
        if not (isinstance(node, ast.FunctionDef)
                and node.name == "_maybe_resync"):
            continue
        for call in ast.walk(node):
            if (isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                    and call.func.id == "send" and len(call.args) >= 2
                    and isinstance(call.args[1], ast.List)):
                resync_sends.append((node, call.args[1].elts))
    check(len(resync_sends) == 1,
          "and there is exactly one resync send site",
          f"{len(resync_sends)} -- both receive arms route through the one "
          f"policy function on purpose; a second send is a second policy")

    def payload_is_verdict_value(elts):
        """True iff the vec2 slot is `list(payload)` -- the verdict's own value."""
        if len(elts) < 2:
            return False
        node = elts[1]
        return (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "list" and len(node.args) == 1
                and isinstance(node.args[0], ast.Name)
                and node.args[0].id == "payload")

    check(payload_is_verdict_value(resync_sends[0][1]),
          "whose vec2 is `list(payload)` -- the value _resync_verdict returned, "
          "which it takes from state['client_pos'] and from nowhere else",
          f"{ast.dump(resync_sends[0][1][1])} -- rewrite this to "
          f"list(state['pos']) and the message becomes the one an earlier "
          f"build sent and had removed as 'the warp the player described'")
    block = resync_sends[0][0]
    grabs_blend = any(
        isinstance(n.value, ast.Name) and n.value.id == "state"
        and isinstance(getattr(n, "slice", None), ast.Constant)
        and n.slice.value == "pos"
        and not isinstance(getattr(n, "ctx", None), ast.Store)
        for n in ast.walk(block) if isinstance(n, ast.Subscript))
    check(grabs_blend is True,
          "CONTROL: the matcher below is looking at a function that DOES "
          "mention state['pos']",
          "it does not, so the next check would pass for the wrong reason -- "
          "_maybe_resync logs `ours=state['pos']` beside every verdict, which "
          "is what makes a scorer able to see the two apart")
    # THE MUTATION THIS LOCKS, handed to the matcher on purpose. The rejecting
    # branch is the one that never runs against healthy source.
    bad = ast.parse(
        "def _maybe_resync(send, state, rec, now=None):\n"
        "    send(OP, [PLAYER_AGENT_ID, list(state['pos']), plane], 'x')\n")
    bad_elts = []
    for call in ast.walk(bad):
        if (isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                and call.func.id == "send" and len(call.args) >= 2
                and isinstance(call.args[1], ast.List)):
            bad_elts = call.args[1].elts
    check(len(bad_elts) == 3 and not payload_is_verdict_value(bad_elts),
          "CONTROL: and it still REJECTS the integrator's position when handed "
          "it",
          f"{[ast.dump(e) for e in bad_elts]} -- if the matcher stopped "
          f"recognising list(state['pos']), the lock above would be a no-op")

    # THE FLAG'S OWN BANNER MUST BE PRINTABLE. Found the hard way while writing
    # this: a U+26A0 warning sign in the --resync startup print raised
    # UnicodeEncodeError on a default Windows console, because cp1252 has no
    # code point for it -- so the flag would have killed the very run it exists
    # to enable, before a single packet went out. The em dashes elsewhere in
    # authsrv.py survive because cp1252 DOES have those, which is exactly why a
    # bare "no non-ASCII" rule would be wrong here and the real console encoding
    # is the thing to test against.
    def unprintable(node):
        out = []
        for n in ast.walk(node):
            if isinstance(n, ast.Constant) and isinstance(n.value, str):
                try:
                    n.value.encode("cp1252")
                except UnicodeEncodeError:
                    out.append(n.value[:40])
        return out

    banner = next((n for n in ast.walk(src)
                   if isinstance(n, ast.If)
                   and isinstance(n.test, ast.Attribute)
                   and n.test.attr == "resync"), None)
    check(banner is not None and unprintable(banner) == [],
          "and every string the --resync banner prints survives a cp1252 "
          "console",
          f"{None if banner is None else unprintable(banner)} -- print() raises "
          f"on the first character cp1252 cannot encode, and a flag that kills "
          f"the server at startup cannot be scored")
    planted = ast.parse("if a.resync:\n    print('\\u26a0 careful')\n")
    check(unprintable(planted) != [],
          "CONTROL: and the same scan still catches a planted U+26A0",
          f"{unprintable(planted)} -- a scan that finds nothing is "
          f"indistinguishable from a clean file, which is how the real one "
          f"got written")

    print("\n12. --grant-suppress ships OFF, and it acts by SAYING LESS")
    # WHAT EARNS THIS SECTION. Three captures from 2026-08-20 on the owner's own
    # machine. Keyboard only (182554): 283-287 u/s every interval, zero clicks,
    # zero grants, 0.00 hard jumps/min. Five clicks the server REFUSED (182934):
    # zero grants, zero warps. And the reproduction (183311): the owner held S
    # while spam-clicking forward, 196 clicks -> 140 grants in 44 s, one every
    # 0.13 s, five hard jumps (p50 1,372 u, max 3,010 u, 6.82/min) with four of
    # the five landing 0.10-0.23 s after a grant.
    #
    # 0x0029 is SYNC-ONLY, so a grant sent while the player keyboards drives the
    # authoritative copy away from the rendered one and re-runs the desync test
    # that snaps them together past 299.332591 u. Every check here exists to
    # keep one of the two refusals from being quietly loosened back out.
    check(authsrv.GRANT_SUPPRESS is False,
          "--grant-suppress is off by default",
          "it is the EIGHTH candidate in this arc and seven are dead. It is "
          "unproven until one watched run scores it against 183311")
    check(authsrv.GRANT_LOCAL_WINDOW == 3.0,
          "the locally-driving window is 3.0 s, sized from the corpus",
          f"{authsrv.GRANT_LOCAL_WINDOW} -- over 987 `ours` gamesrv captures "
          f"the gap between consecutive 0x003D-moving reports with no 0x0047 "
          f"between them is n = 3,420, p50 0.500 s, p90 1.801, p99 2.737, "
          f"p99.9 7.858. There is a real mode at 2.74-2.79 s: 144 gaps exceed "
          f"2.00 s and only 9 exceed 3.00 s, so 3.0 is the first round number "
          f"PAST the mode and covers 99.74% of them. A 2.0 s window opens a "
          f"hole in 4.2%, and a hole is where the reproduction gets back in")
    ceiling = 299.332591 / (2 * authsrv.DEFAULT_RUN_SPEED)
    check(authsrv.GRANT_MIN_INTERVAL < ceiling,
          f"the grant floor sits under the same derived ceiling --resync uses, "
          f"{ceiling:.4f} s",
          f"{authsrv.GRANT_MIN_INTERVAL} -- a click HELD longer than the "
          f"shortest time two copies can accrue a full gate's separation is "
          f"itself late enough to open one")
    check(authsrv.GRANT_MIN_INTERVAL >= 0.492,
          "and it is no faster than retail's own median player inter-grant gap "
          "of 0.492 s",
          f"{authsrv.GRANT_MIN_INTERVAL} -- measured over the 2,855 "
          f"player-directed 0x0029 in the live corpus, the figure the heading "
          f"arm's comment already cites. The reproduction ran at 0.13 s, 3.8x "
          f"faster than the thing we are imitating. Two independent "
          f"derivations landing on 0.5 is the only reason it is a round number")
    check(authsrv.GRANT_PENDING_MAX_AGE == 2.0 * authsrv.GRANT_MIN_INTERVAL,
          "and the hold expiry is expressed as a multiple of the floor, so the "
          "two cannot drift apart",
          f"{authsrv.GRANT_PENDING_MAX_AGE} -- a deferred grant is due within "
          f"one floor by construction; twice that is a world tick that has "
          f"missed ten of its 20 Hz intervals, by which point the player has "
          f"moved up to 288 u from where the click's ray was cast")

    def clicking(kbd=None, last=None, pending=None):
        """A state the click arm would be evaluating a grant in."""
        st = {"pos": (0.0, 0.0), "plane": 0, "pos_seen": 1000.0}
        if kbd is not None:
            st["kbd_moving_at"] = kbd
        if last is not None:
            st["grant_at"] = last
        if pending is not None:
            st["grant_pending"] = pending
        return st

    class Wire:
        """A send() that runs the real send-side hook, like the server's."""

        def __init__(self, state, now=1000.0):
            self.state, self.now, self.sent = state, now, []

        def __call__(self, opcode, values, label, quiet=False):
            authsrv._note_wire_move(self.state, opcode, values, self.now)
            self.sent.append((opcode, values, label))

    # OFF MEANS OFF: a state that would be refused twice over still grants, and
    # the deferred sender does not even look at its own pending.
    st = clicking(kbd=1000.0, last=1000.0,
                  pending={"dest": (5.0, 6.0), "plane_first": 0,
                           "plane_second": 0, "at": 1000.0})
    grant, why, _a, _s = authsrv._grant_verdict(st, 1000.0)
    wire, rec = Wire(st), FakeRec()
    flushed = authsrv.grant_flush_tick(wire, st, 1, rec, now=1000.0)
    check(grant is True and why == "off" and flushed is False
          and wire.sent == [] and rec.events == [],
          "with the flag off a state that WOULD be refused grants anyway, and "
          "the deferred sender is inert",
          f"verdict={why} flushed={flushed} sent={wire.sent} -- the default "
          f"build must behave exactly as it did, and must not grow a "
          f"grant_verdict log it never used")
    check(st.get("grant_pending") is not None,
          "and it does not even clear the pending it found",
          f"{st.get('grant_pending')} -- an off flag that mutates state is a "
          f"flag that is partly on")

    saved = authsrv.GRANT_SUPPRESS
    authsrv.GRANT_SUPPRESS = True
    try:
        # RULE 1, at both edges. The bound is inclusive at the window and a
        # NEGATIVE age counts as armed -- clock skew sails straight through an
        # upper-bound-only test, and here failing toward silence is the cheap
        # direction because over-refusing costs a grant the client did not need.
        st = clicking(kbd=1000.0)
        grant, why, age, _s = authsrv._grant_verdict(st, 1000.0)
        check(grant is False and why == "locally-moving",
              "a move report this instant refuses the grant outright",
              f"{why} at age {age} -- this is the reproduction: 196 clicks "
              f"arrived with the latch armed and 140 were answered")
        edge = 1000.0 + authsrv.GRANT_LOCAL_WINDOW
        check(authsrv._grant_verdict(st, edge)[1] == "locally-moving",
              f"a report exactly {authsrv.GRANT_LOCAL_WINDOW:.1f}s old still "
              f"refuses -- the bound is inclusive",
              f"{authsrv._grant_verdict(st, edge)}")
        past = edge + 1e-6
        check(authsrv._grant_verdict(st, past)[0] is True
              and authsrv._grant_verdict(st, past)[1] == "grant",
              "one microsecond past it, the latch has lapsed and the click is "
              "answered",
              f"{authsrv._grant_verdict(st, past)} -- the window is a failsafe "
              f"for a stop we never heard, not a mute button")
        future = clicking(kbd=1001.0)
        check(authsrv._grant_verdict(future, 1000.0)[1] == "locally-moving",
              "and a report dated in the FUTURE counts as armed, not as lapsed",
              f"{authsrv._grant_verdict(future, 1000.0)} -- `now - at` goes "
              f"negative under clock skew, and a negative age would sail "
              f"through an upper-bound-only test into the storm")

        # PERMITS WHEN STOPPED. This is the control for rule 1, and without it
        # every check above is satisfied by a policy that refuses everything.
        stopped = clicking(kbd=None)
        grant, why, _a, _s = authsrv._grant_verdict(stopped, 1000.0)
        check(grant is True and why == "grant",
              "CONTROL: with the latch cleared -- which is what 0x0047 does -- "
              "the very same click is answered",
              f"{why} -- rule 1 refuses 0 of the 5 ordinary clicks in run "
              f"20260820T182934. CORRECTED 2026-08-20: a 0x0047 had arrived "
              f"before FOUR of them, not all five -- click 2 at t=41.79 s had "
              f"no stop before it and a latch age of 8.93 s, so "
              f"GRANT_LOCAL_WINDOW IS load-bearing for 1 of 5 and a window "
              f"under 8.93 s would refuse it. A rule that refuses everything "
              f"is not a rule")

        # MOVECODE-R1-B1 (--answer-kbd-click). Rule 1's refusal is OURS, not
        # ArenaNet's: retail answered 7 of 7 live clicks that arrived with this
        # latch armed (FINDINGS sec.1p.10 item 1). The flag deletes the refusal
        # -- and must delete ONLY that, because rule 2's hold-and-coalesce IS
        # the pair contract REALFIX sec.0.15 actually states.
        check(authsrv.ANSWER_KBD_CLICK is False,
              "ANSWER_KBD_CLICK defaults to False",
              "an eighth candidate that shipped ON would change the click "
              "policy for every session before any run scored it")
        _saved_kbd = authsrv.ANSWER_KBD_CLICK
        try:
            authsrv.ANSWER_KBD_CLICK = True
            st = clicking(kbd=1000.0)
            grant, why, age, _s = authsrv._grant_verdict(st, 1000.0)
            check(grant is True and why == "grant",
                  "with --answer-kbd-click the SAME click rule 1 refused is "
                  "now answered",
                  f"{why} at age {age} -- this is the whole flag, and the "
                  f"check above is its control: the identical state returns "
                  f"'locally-moving' with the flag off")
            # The reason string is deliberately "grant" and not a new value:
            # grantsim.py:2000 filters `w[2] == "grant"` and policyreplay.py
            # switches on "locally-moving", so a new enum would silently shrink
            # those scorers rather than error. The turnaround stays countable
            # because keyboard_age is on the row and GRANTED-with-age-in-window
            # is unreachable without the flag.
            check(age is not None and age <= authsrv.GRANT_LOCAL_WINDOW,
                  "and it still REPORTS the keyboard age, so the turnaround "
                  "set stays countable offline",
                  f"age={age} -- granted with a non-null keyboard_age inside "
                  f"the window is unreachable with the flag off, so that pair "
                  f"is an exact signature and it is the registered exposure "
                  f"floor. A distinct reason string would have been more "
                  f"greppable and would have been dropped on the floor by two "
                  f"scorers that filter on the literal 'grant'")
            # RULE 2 MUST SURVIVE. This is the guard sec.1p.10 names, and
            # without this check the flag would pass by removing both rules.
            recent = clicking(kbd=1000.0)
            recent["grant_at"] = 1000.0 - (authsrv.GRANT_MIN_INTERVAL / 2.0)
            g2, why2, _a2, since2 = authsrv._grant_verdict(recent, 1000.0)
            check(g2 is False and why2 == "rate-limited",
                  "but a click inside the RATE FLOOR is still refused -- and "
                  "refused as rate-limited, so it is HELD rather than dropped",
                  f"{why2} at since={since2} -- the held branch coalesces to "
                  f"the newest destination, which IS sec.0.15's pair contract. "
                  f"A flag that deleted rule 2 as well would be the 'assert "
                  f"more' error running in reverse, and it would pass every "
                  f"other check in this block")
        finally:
            authsrv.ANSWER_KBD_CLICK = _saved_kbd
        check(authsrv._grant_verdict(clicking(kbd=1000.0), 1000.0)[1]
              == "locally-moving",
              "CONTROL: restoring the flag restores the refusal",
              "a module global left set by a test leaks into every section "
              "below it, and this file drives the click policy for the rest "
              "of the run")

        # RULE 2, BOUNDED ABOVE AND BELOW, driven through the REAL send-side
        # hook so the bookkeeping under test is the server's own rather than a
        # paraphrase written for the test.
        st = clicking()
        wire = Wire(st)
        n, t = 0, 1000.0
        for _i in range(20):
            wire.now = t
            if authsrv._grant_verdict(st, t)[0]:
                n += 1
                wire(authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT,
                     [authsrv.PLAYER_AGENT_ID, [float(n), 0.0], 0, 0], "x")
            t += 0.1
        span = 1.9
        allowed = int(span / authsrv.GRANT_MIN_INTERVAL) + 1
        check(n <= allowed,
              f"twenty clicks over {span:.1f} s produce {n} grants, not 20",
              f"n={n}, ceiling {allowed} at one per "
              f"{authsrv.GRANT_MIN_INTERVAL:.2f} s -- the reproduction ran at "
              f"one per 0.13 s, 257 a minute, and each one re-armed an arrival "
              f"tick AND re-ran the desync test")
        check(n >= 1,
              "and it does not rate-limit itself down to nothing",
              f"n={n} -- a limit that lets nothing through makes every check "
              f"above vacuous, and would break click-to-move for a player who "
              f"is not keyboarding at all")
        check(st.get("grant_at") is not None,
              "and the clock it limits against is stamped by the send-side "
              "hook, so EVERY grant counts",
              f"{st.get('grant_at')} -- the click arm, the heading arm, the "
              f"endpoint arm, the stop echo and the click sweep all grant "
              f"through _note_wire_move; a limit fed from the click arm alone "
              f"would be blind to the other four")

        # THE DEFERRED SENDER. One pending, one send, and the pending is gone.
        st = clicking(pending={"dest": (1234.0, -567.0), "plane_first": 3,
                               "plane_second": 4, "at": 1000.0})
        wire, rec = Wire(st, now=1000.2), FakeRec()
        flushed = authsrv.grant_flush_tick(wire, st, 1, rec, now=1000.2)
        moves = [s for s in wire.sent
                 if s[0] == authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT]
        check(flushed is True and len(moves) == 1
              and moves[0][1][1] == [1234.0, -567.0],
              "a held click goes out once the floor opens, carrying the "
              "destination it held",
              f"flushed={flushed} sent={wire.sent}")
        check(st.get("grant_pending") is None
              and authsrv.grant_flush_tick(wire, st, 1, rec, now=1000.3)
              is False,
              "and it is consumed -- the next tick sends nothing",
              f"{st.get('grant_pending')} -- a pending that survived its own "
              f"send is a 20 Hz grant stream, which is the reproduction with "
              f"our name on it")
        check(len(moves[0][1]) == 4 and moves[0][1][2] == 3
              and moves[0][1][3] == 4,
              "with the two plane words in the order the click arm computed "
              "them",
              f"{moves[0][1]} -- destination plane FIRST, current plane "
              f"SECOND. This project has already sent them the wrong way "
              f"round and walked players through staircases for it")

        # THE LATCH BEATS THE HOLD. A player who picks the keyboard back up has
        # superseded their own click, and granting it late is the reproduction
        # with a delay bolted on.
        st = clicking(kbd=1000.1,
                      pending={"dest": (9.0, 9.0), "plane_first": 0,
                               "plane_second": 0, "at": 1000.0})
        wire, rec = Wire(st, now=1000.2), FakeRec()
        flushed = authsrv.grant_flush_tick(wire, st, 1, rec, now=1000.2)
        check(flushed is False and wire.sent == []
              and st.get("grant_pending") is None,
              "a held click is DROPPED, not delayed, once the player starts "
              "keyboarding",
              f"flushed={flushed} pending={st.get('grant_pending')} sent="
              f"{wire.sent}")
        check(len(rec.of("grant_verdict")) == 1
              and rec.of("grant_verdict")[0]["fired"] is False,
              "and the drop is in the event log, not merely absent from it",
              f"{rec.of('grant_verdict')} -- a grant log holding only its own "
              f"successes cannot score the flag against the storm")

        # AND THE HOLD EXPIRES. Bounded on BOTH sides so neither half is
        # vacuous: just under the age it still goes, just over it does not.
        young = clicking(pending={"dest": (1.0, 2.0), "plane_first": 0,
                                  "plane_second": 0, "at": 1000.0})
        wire = Wire(young, now=1000.0 + authsrv.GRANT_PENDING_MAX_AGE)
        check(authsrv.grant_flush_tick(
                  wire, young, 1, None,
                  now=1000.0 + authsrv.GRANT_PENDING_MAX_AGE) is True,
              f"a hold exactly {authsrv.GRANT_PENDING_MAX_AGE:.2f}s old still "
              f"goes out -- the bound is inclusive",
              f"sent={wire.sent}")
        old = clicking(pending={"dest": (1.0, 2.0), "plane_first": 0,
                                "plane_second": 0, "at": 1000.0})
        wire, rec = Wire(old), FakeRec()
        flushed = authsrv.grant_flush_tick(
            wire, old, 1, rec, now=1000.0 + authsrv.GRANT_PENDING_MAX_AGE + 1e-6)
        check(flushed is False and wire.sent == []
              and old.get("grant_pending") is None
              and rec.of("grant_verdict")[0]["reason"] == "pending-expired",
              "one microsecond past it, the hold is dropped unsent",
              f"flushed={flushed} {rec.of('grant_verdict')} -- past that the "
              f"destination is our guess about somebody else's intention")
    finally:
        authsrv.GRANT_SUPPRESS = saved
    check(authsrv.GRANT_SUPPRESS is False,
          "and the section put the flag back the way it found it",
          f"{authsrv.GRANT_SUPPRESS}")

    # THE LATCH HAS EXACTLY TWO WRITERS, and they are the two receive arms.
    # state["walking"] is nine characters away and is cleared BY THE CLICK ARM
    # ITSELF -- so keying rule 1 on it would have let the first click of the
    # reproduction disarm the latch and the other 195 straight through. This is
    # the same shape as state["pos"] vs state["client_pos"] in section 11.
    latch = []
    for node in ast.walk(src):
        if not isinstance(node, ast.Assign):
            continue
        for tgt in node.targets:
            if (isinstance(tgt, ast.Subscript)
                    and isinstance(tgt.value, ast.Name)
                    and tgt.value.id == "state"
                    and isinstance(getattr(tgt, "slice", None), ast.Constant)
                    and tgt.slice.value == "kbd_moving_at"):
                latch.append(node)
    check(len(latch) == 2,
          "exactly two lines in the file write state['kbd_moving_at']",
          f"{len(latch)} -- one arms it on a moving 0x003D, one clears it on a "
          f"0x0047, and a third writer is a third policy")
    arms = [n for n in latch if isinstance(n.value, ast.IfExp)]
    clears = [n for n in latch
              if isinstance(n.value, ast.Constant) and n.value.value is None]
    check(len(arms) == 1 and len(clears) == 1,
          "one arms it CONDITIONALLY on `moving`, the other clears it flat",
          f"armers={len(arms)} clearers={len(clears)}")
    check(arms and isinstance(arms[0].value.test, ast.Name)
          and arms[0].value.test.id == "moving",
          "and the condition is the client's own movementType, not our "
          "state['walking']",
          f"{ast.dump(arms[0].value.test) if arms else None} -- 0x003D is "
          f"emitted only WHILE MOVING, which is what makes the latch readable "
          f"off the wire at all; state['walking'] is cleared by the click arm "
          f"and one click would have disarmed the whole rule")
    # THE CONTROL. Both matchers only ever run against healthy source, so both
    # are branches a typo would silently disable.
    bad = ast.parse("state['walking'] = True if moving else None\n"
                    "state['kbd_moving_at'] = state['walking']\n")
    bad_latch, bad_arms = [], []
    for node in ast.walk(bad):
        if not isinstance(node, ast.Assign):
            continue
        for tgt in node.targets:
            if (isinstance(tgt, ast.Subscript)
                    and isinstance(tgt.value, ast.Name)
                    and tgt.value.id == "state"
                    and isinstance(getattr(tgt, "slice", None), ast.Constant)
                    and tgt.slice.value == "kbd_moving_at"):
                bad_latch.append(node)
                if isinstance(node.value, ast.IfExp):
                    bad_arms.append(node)
    check(len(bad_latch) == 1 and bad_arms == [],
          "CONTROL: the same matchers still SEE a latch keyed off "
          "state['walking'] when handed one",
          f"found={len(bad_latch)} conditional={len(bad_arms)} -- if either "
          f"stopped matching, the three checks above would pass for the wrong "
          f"reason")

    # THE ORDER OF THE THREE REFUSALS. The two geometry refusals must still fire
    # and must still fire FIRST: they say something about the map, and they are
    # the lines the owner reads live. "The player is keyboarding" printed in
    # their place hides a stale position behind a policy decision.
    arm = next((n for n in ast.walk(src)
                if isinstance(n, ast.If) and isinstance(n.test, ast.Compare)
                and isinstance(n.test.left, ast.Name)
                and n.test.left.id == "opcode"
                and isinstance(n.test.comparators[0], ast.Name)
                and n.test.comparators[0].id == "GAME_CMSG_MOVE_TO_COORD"),
               None)
    check(arm is not None, "the click arm is where the matcher expects it",
          "GAME_CMSG_MOVE_TO_COORD's elif was not found; every check below "
          "would be judging an empty set")
    # ITS BODY ONLY, never ast.walk(arm). An `elif` is an `If` living in the
    # PREVIOUS `If`'s orelse, so walking this node reaches every arm below it in
    # the chain -- which is how the send count below first read 2 and found the
    # 0x0047 arm's stop echo. A matcher whose scope is wrong is a matcher
    # judging somebody else's code.
    inside = [n for stmt in arm.body for n in ast.walk(stmt)] if arm else []
    why_strings = sorted(
        n.value for n in inside
        if isinstance(n, ast.Constant) and isinstance(n.value, str)
        and ("straight shot" in n.value or "last saw the player" in n.value
             or "cannot place them" in n.value))
    check(len(why_strings) == 3,
          "and all three geometry reasons survive verbatim in it",
          f"{why_strings} -- 'not a straight shot', 'we last saw the player "
          f"Ns ago' and 'cannot place them'. The gamesrv log of run "
          f"20260820T182934 shows the first two doing the whole job on five "
          f"clicks; a refusal that stops naming itself is a refusal nobody can "
          f"audit from the console")
    blocked_if = next((n for n in inside
                       if isinstance(n, ast.If) and isinstance(n.test, ast.Name)
                       and n.test.id == "blocked"), None)
    verdict_call = next((n for n in inside
                         if isinstance(n, ast.Call)
                         and isinstance(n.func, ast.Name)
                         and n.func.id == "_grant_verdict"), None)
    check(blocked_if is not None and verdict_call is not None
          and blocked_if.lineno < verdict_call.lineno,
          "and the geometry refusal is strictly BEFORE the suppression gate",
          f"blocked at line {getattr(blocked_if, 'lineno', None)}, "
          f"_grant_verdict at {getattr(verdict_call, 'lineno', None)} -- "
          f"reversed, a click that is both stale and mid-keyboard would report "
          f"the policy instead of the map")
    arm_moves = [c for c in inside
                 if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
                 and c.func.id == "send" and len(c.args) >= 2
                 and isinstance(c.args[0], ast.Name)
                 and c.args[0].id == "GAME_SMSG_AGENT_MOVE_TO_POINT"]
    check(len(arm_moves) == 1 and verdict_call is not None
          and arm_moves[0].lineno > verdict_call.lineno,
          "and the arm's ONE grant send sits after the gate, not beside it",
          f"{len(arm_moves)} send(s), at line "
          f"{arm_moves[0].lineno if arm_moves else None} -- a second send site "
          f"is a second policy, which is how the heading arm ended up granting "
          f"twice per report")
    # THE CONTROL for the scoping fix above: the matcher must still find a send
    # that IS in the arm, and must NOT find one that is merely below it in the
    # elif chain. Handed both on purpose.
    bad = ast.parse(
        "if opcode == GAME_CMSG_MOVE_TO_COORD:\n"
        "    send(GAME_SMSG_AGENT_MOVE_TO_POINT, [a, b, c, d], 'in')\n"
        "elif opcode == GAME_CMSG_LAST_POS_BEFORE_MOVE_CANCELED:\n"
        "    send(GAME_SMSG_AGENT_MOVE_TO_POINT, [a, b, c, d], 'below')\n")
    bad_arm = next(n for n in ast.walk(bad)
                   if isinstance(n, ast.If) and isinstance(n.test, ast.Compare)
                   and n.test.comparators[0].id == "GAME_CMSG_MOVE_TO_COORD")
    scoped = [c for stmt in bad_arm.body for c in ast.walk(stmt)
              if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
              and c.func.id == "send"]
    unscoped = [c for c in ast.walk(bad_arm)
                if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
                and c.func.id == "send"]
    check(len(scoped) == 1 and len(unscoped) == 2,
          "CONTROL: body-scoped matching sees 1 send where ast.walk sees 2",
          f"scoped={len(scoped)} walked={len(unscoped)} -- if these agreed, "
          f"the check above would be counting the arms below it and would go "
          f"red for a send nobody added to the click arm")
    # THE PENDING IS A SINGLE SLOT, NEVER A QUEUE. Coalescing is the whole
    # difference between rate-limiting and deferring the storm by one interval:
    # 196 clicks must leave at most ONE destination outstanding.
    holds = []
    for node in ast.walk(src):
        if not isinstance(node, ast.Assign):
            continue
        for tgt in node.targets:
            if (isinstance(tgt, ast.Subscript)
                    and isinstance(tgt.value, ast.Name)
                    and tgt.value.id == "state"
                    and isinstance(getattr(tgt, "slice", None), ast.Constant)
                    and tgt.slice.value == "grant_pending"):
                holds.append(node)
    dicts = [n for n in holds if isinstance(n.value, ast.Dict)]
    appends = [c for c in ast.walk(src)
               if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
               and c.func.attr == "append"
               and isinstance(c.func.value, ast.Subscript)
               and isinstance(getattr(c.func.value, "slice", None), ast.Constant)
               and c.func.value.slice.value == "grant_pending"]
    check(len(dicts) == 1 and appends == [] and len(holds) >= 4,
          "state['grant_pending'] is assigned a single destination and never "
          "appended to",
          f"{len(dicts)} hold(s), {len(appends)} append(s), {len(holds)} "
          f"writers -- a list here would send all 196 of the reproduction's "
          f"clicks half a second later instead of 140 of them now")

    # THE FLAG'S BANNER MUST BE PRINTABLE, same reason as --resync's. Since
    # the 2026-08-22 default flip the banner block tests the RESOLVED local
    # (`if grant_suppress:`), so the matcher accepts Name or Attribute -- and
    # it walks main() only, because zero_lead_composition() now holds bare-name
    # `if grant_suppress:` tests of its own that would shadow the banner.
    _gs_main = next(n for n in ast.walk(src)
                    if isinstance(n, ast.FunctionDef) and n.name == "main")
    banner = next((n for n in ast.walk(_gs_main)
                   if isinstance(n, ast.If)
                   and ((isinstance(n.test, ast.Attribute)
                         and n.test.attr == "grant_suppress")
                        or (isinstance(n.test, ast.Name)
                            and n.test.id == "grant_suppress"))), None)
    check(banner is not None and unprintable(banner) == [],
          "and every string the --grant-suppress banner prints survives a "
          "cp1252 console",
          f"{None if banner is None else unprintable(banner)} -- a flag that "
          f"kills the server at startup cannot be scored")

    print("\n13. replay: tonight's three captures against the policy itself")
    # THE TREATMENT AND ITS CONTROL, from the wire rather than from a fixture we
    # wrote. The reproduction's clicks must be refused; the ordinary capture's
    # clicks must be permitted. Either half alone proves nothing -- a policy
    # that refuses everything passes the first, and today's code passes the
    # second.
    #
    # SCOPE, said out loud: this replays rules 1 and 2 ONLY. The two geometry
    # refusals run upstream of them in the arm and are not modelled here, which
    # is why the ordinary capture's five clicks read as "permitted" even though
    # the real server refused all five on stale position and collision.
    # Read off S13_CAPTURES, not restated: the floor probe and this section
    # must not be able to disagree about which fixtures section 13 needs.
    REPRO, ORDINARY, KEYBOARD = S13_CAPTURES

    def replay(name):
        """(clicks, refused_by_rule_1, granted, headings, stops) or None."""
        path = os.path.join(vaultpath.vault_path("captures", "gamesrv"), name)
        if not os.path.exists(path):
            return None
        ev = []
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    o = json.loads(line)
                except ValueError:
                    continue
                if o.get("kind") == "decoded" and o.get("opcode") in (61, 62, 71):
                    ev.append((o["t"], o["opcode"], o.get("values")))
        ev.sort(key=lambda r: r[0])
        st, clicks, local, granted, heads, stops = {}, 0, 0, 0, 0, 0
        was = authsrv.GRANT_SUPPRESS
        authsrv.GRANT_SUPPRESS = True
        try:
            for t, op, v in ev:
                if op == 61:
                    heads += 1
                    moving = v[4] if v and len(v) > 4 else 0
                    st["kbd_moving_at"] = t if moving else None
                elif op == 71:
                    stops += 1
                    st["kbd_moving_at"] = None
                else:
                    clicks += 1
                    ok, why, _a, _s = authsrv._grant_verdict(st, t)
                    local += (why == "locally-moving")
                    if ok:
                        granted += 1
                        st["grant_at"] = t
        finally:
            authsrv.GRANT_SUPPRESS = was
        return clicks, local, granted, heads, stops

    repro, ordinary, keyboard = replay(REPRO), replay(ORDINARY), replay(KEYBOARD)
    if repro is None or ordinary is None or keyboard is None:
        LEDGER.skip("capture replay of the 2026-08-20 runs",
                    "one of the three captures is not in this vault; section "
                    "12's policy checks are fixture-free and still ran")
    else:
        n, local, granted, heads, stops = repro
        check(n >= 190 and heads >= 120,
              f"the reproduction still carries its {n} clicks and {heads} "
              f"move reports",
              f"196 clicks, 128 headings and {stops} stops when this was "
              f"written -- the owner held S while spam-clicking forward")
        check(local == n and granted == 0,
              f"rule 1 refuses ALL {n} of them, and not one grant survives",
              f"{local} refused as locally-moving, {granted} granted -- the "
              f"server that produced this capture answered 140 of them, a "
              f"grant every 0.13 s, and four of its five hard jumps landed "
              f"0.10-0.23 s after one")
        n, local, granted, heads, stops = ordinary
        check(n >= 5 and granted == n and local == 0,
              f"CONTROL: and it refuses NONE of the {n} ordinary clicks, "
              f"granting all {granted}",
              f"{local} refused, {granted} granted over {heads} headings and "
              f"{stops} stops -- a 0x0047 had arrived before FOUR of the five "
              f"(click 2 at t=41.79 s had none; the 3.0 s window decides that "
              f"one). This is the check that stops 'refuse everything' from "
              f"passing the one above, and it judges real rows rather than an "
              f"empty set")
        n, local, granted, heads, stops = keyboard
        check(n == 0 and heads >= 15 and stops >= 3,
              f"and the keyboard-only run has no clicks at all to decide "
              f"({heads} reports, {stops} stops)",
              f"clicks={n} -- it is in here as the shape of a clean run: "
              f"283-287 u/s every interval, zero grants, 0.00 hard jumps per "
              f"minute. Nothing the flag does can touch it")
        print(f"     repro {repro[1]}/{repro[0]} refused, "
              f"ordinary {ordinary[2]}/{ordinary[0]} granted")

    print("\n14. --zero-lead ships OFF, and it grants the REPORT verbatim")
    # WHAT EARNS THIS SECTION. REALFIX-P2 is the ninth candidate in this arc and
    # eight are dead. It is the only member of the lead family never run, and
    # the one whose design ground is the invariant rather than an analogy: the
    # client's history polyline extends only BACKWARDS while it holds no
    # destination, so LAG is on it by construction and LEAD is not. Both dead
    # members of the family granted 766 u AHEAD.
    #
    # AND ONE CLAIM IN ITS OWN SPEC IS RETRACTED, which is why this section
    # checks the CADENCE as carefully as the payload. The drafted block argued
    # that dropping the shipped `turned or not walking` gate is cheap "because a
    # zero-distance grant takes the <= 1.0 u short-circuit and dispatches
    # nothing". That compare measures from the SYNC COPY (`fsub [esi+0x78]` at
    # 0x005FEB57), not from the client, and 353 of 358 synthesized grants bake a
    # real leg (re-measured 2026-08-21 under the shipped rate limit; the
    # correction's own 533 of 539 predates `_heading_grant_ok` and says the
    # same thing more weakly). The gate-drop is a real cost and the rate limit is what bounds
    # it, so `_heading_grant_ok` is not optional and section 14 treats it as the
    # load-bearing half.
    check(authsrv.ZERO_LEAD is False,
          "--zero-lead is off by default",
          "it is the NINTH candidate in this arc and eight are dead. It is "
          "unproven until REALFIX-L1 scores it against the shipped default")

    # ---- the predicate ------------------------------------------------
    # PURITY FIRST, because everything downstream is built on it: grantsim
    # imports this symbol and runs it against captures, which is only sound if
    # the same state in gives the same verdict out and nothing is written back.
    st = {"pos": ANCHOR, "plane": 0, "pos_seen": 0.0, "grant_at": 1000.0,
          "kbd_moving_at": 1000.0}
    before = json.dumps(st, sort_keys=True, default=str)
    verdicts = [authsrv._heading_grant_ok(st, 1000.9) for _ in range(5)]
    after = json.dumps(st, sort_keys=True, default=str)
    check(len(set(verdicts)) == 1 and before == after,
          "the predicate is PURE: same state in, same verdict out, nothing "
          "written back",
          f"{sorted(set(verdicts))} over 5 calls; state {before} -> {after}. "
          f"_grant_verdict's own docstring says it was made side-effect-free so "
          f"an offline scorer could run the decision rather than a paraphrase "
          f"that agrees with it by construction -- grantsim imports THIS symbol "
          f"for exactly that, and a predicate that mutates would make its "
          f"replay depend on call order")

    floor = authsrv.GRANT_MIN_INTERVAL
    under = authsrv._heading_grant_ok({"grant_at": 1000.0}, 1000.0 + floor - 1e-6)
    at = authsrv._heading_grant_ok({"grant_at": 1000.0}, 1000.0 + floor)
    check(under == (False, "heading-rate", under[2]) and at[0] is True
          and at[1] == "zero-lead",
          f"RULE 2 at the boundary: one microsecond under {floor:.2f}s refuses, "
          f"exactly {floor:.2f}s grants",
          f"under={under} at={at} -- the floor is >= and not >, the same "
          f"comparison the click arm's rule 2 uses, so the two arms cannot "
          f"disagree about what 'a grant per interval' means")
    virgin = authsrv._heading_grant_ok({}, 1000.0)
    check(virgin == (True, "zero-lead", None),
          "with no grant on record it fires, and says `since` is unknown rather "
          "than 0",
          f"{virgin} -- a None `since` reported as 0.0 would read as 'we just "
          f"granted' in a capture and invert the whole telemetry")
    skew = authsrv._heading_grant_ok({"grant_at": 1001.0}, 1000.0)
    check(skew[0] is False and skew[1] == "heading-rate",
          "and a grant stamped in the FUTURE refuses, rather than sailing "
          "through an upper-bound-only test",
          f"{skew} -- `since` is -1.0 under clock skew. Over-refusing costs one "
          f"grant the next 0x003D replaces in ~0.29 s; under-refusing is the "
          f"cadence this flag exists to bound")

    # RULE 1 IS ABSENT, AND THAT IS THE POINT. This is the check that stops
    # somebody "simplifying" the heading arm back onto _grant_verdict: that
    # predicate's rule 1 refuses whenever the locally-driving latch is younger
    # than GRANT_LOCAL_WINDOW, and the heading arm ARMS that latch ten lines
    # before it would ask. Age is ~0 on every call, so P2 would emit zero grants
    # under --grant-suppress and degenerate into --grant-suppress renamed.
    kbd = {"grant_at": 0.0, "kbd_moving_at": 1000.0}
    heading_says = authsrv._heading_grant_ok(kbd, 1000.0)
    saved_gs = authsrv.GRANT_SUPPRESS
    authsrv.GRANT_SUPPRESS = True
    try:
        click_says = authsrv._grant_verdict(kbd, 1000.0)
    finally:
        authsrv.GRANT_SUPPRESS = saved_gs
    check(heading_says[0] is True and click_says[0] is False
          and click_says[1] == "locally-moving",
          "it carries RULE 2 ONLY: a state the click arm refuses as "
          "locally-moving still grants here",
          f"heading={heading_says} click={click_says} -- the heading arm arms "
          f"`kbd_moving_at` ten lines before it would ask, so reusing "
          f"_grant_verdict here emits ZERO grants under --grant-suppress and "
          f"turns --zero-lead into --grant-suppress wearing a new name")
    # THE VOCABULARIES, READ BACK OUT OF THE SHIPPED PREDICATES, and this check
    # used to compare two LITERAL sets. It therefore read nothing from
    # authsrv.py and could not fail: an adversarial pass made
    # _heading_grant_ok return exactly "rate-limited" and "grant" -- the click
    # arm's own two words, the vocabularies overlapping COMPLETELY -- and this
    # line still printed PASS. A check that cannot fail is not a check. Both
    # arms of both predicates are DRIVEN and the strings collected from what
    # they return.
    heading_words = set()
    for st_h, now_h in (({}, 1000.0),                      # fires
                        ({"grant_at": 1000.0}, 1000.0)):   # refuses
        heading_words.add(authsrv._heading_grant_ok(st_h, now_h)[1])
    click_words = set()
    saved_gs2 = authsrv.GRANT_SUPPRESS
    try:
        authsrv.GRANT_SUPPRESS = False
        click_words.add(authsrv._grant_verdict({}, 1000.0)[1])          # off
        authsrv.GRANT_SUPPRESS = True
        click_words.add(authsrv._grant_verdict({}, 1000.0)[1])          # grant
        click_words.add(authsrv._grant_verdict(
            {"kbd_moving_at": 1000.0}, 1000.0)[1])          # locally-moving
        click_words.add(authsrv._grant_verdict(
            {"grant_at": 1000.0}, 1000.0)[1])               # rate-limited
    finally:
        authsrv.GRANT_SUPPRESS = saved_gs2
    check(len(heading_words) == 2 and len(click_words) == 4
          and heading_words.isdisjoint(click_words),
          "and its reason vocabulary is DISJOINT from the click arm's, both "
          "sides READ BACK OUT OF THE SHIPPED PREDICATES",
          f"heading={sorted(heading_words)} click={sorted(click_words)} -- one "
          f"capture from a --zero-lead run carries grant_verdict rows from BOTH "
          f"arms; if the two vocabularies overlapped, a replay could not tell "
          f"which policy produced a row and grantsim's C3 would be scoring the "
          f"wrong predicate. The counts are pinned too, so a predicate that "
          f"collapsed to ONE word would not pass this by being trivially "
          f"disjoint")
    check(set(heading_words) == set(grantsim_heading_reasons()),
          "and grantsim's HEADING_REASONS filter is the same two words the "
          "predicate actually returns",
          f"{sorted(heading_words)} against grantsim's "
          f"{sorted(grantsim_heading_reasons())} -- that frozenset is what "
          f"`replay_verdicts` skips heading rows ON. If the predicate's words "
          f"drifted from it, the first REALFIX-L1 capture would be re-decided "
          f"with the CLICK predicate and the disagreement called a defect")

    # ONE CLOCK, and it is the shared one. A CLICK grant must move the heading
    # floor, because `grant_at` is stamped inside send() for every 0x0029
    # whatever arm sent it. A private heading clock would let the two arms run
    # at 2 x 2 Hz while each believed it was inside the floor.
    shared = {"pos": ANCHOR, "plane": 0, "pos_seen": 0.0}
    wire = Sent(shared, now=2000.0)
    wire(authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT,
         [authsrv.PLAYER_AGENT_ID, [1.0, 2.0], 0, 0], "a click grant")
    check(authsrv._heading_grant_ok(shared, 2000.1)[1] == "heading-rate"
          and authsrv._heading_grant_ok(shared, 2000.0 + floor)[1] == "zero-lead",
          "the floor reads the SHARED grant clock, so a CLICK grant delays a "
          "heading grant",
          f"grant_at={shared.get('grant_at')} -- under --zero-lead "
          f"--grant-suppress the two arms cannot between them exceed one grant "
          f"per {floor:.2f}s, which is the bound the interval was derived for")

    # ---- the arm, EXECUTED --------------------------------------------
    # `conn_id` joined the heading arm's free names on 2026-08-24, when the
    # castmech arc landed `cancel_on_move(send, state, conn_id)` in the
    # movement door -- without it every drive() below dies on a NameError
    # before the first check runs (found red at HEAD by the CANCELWALK arc).
    arm = receive_arm("GAME_CMSG_TURN_TO_DIRECTION",
                      ("values", "state", "rec", "send", "conn_id"))
    HEAD = [1, [1000.5, 2000.25], 7, [766.0, 0.0], 1]
    SAME = [1, [1400.5, 2000.25], 7, [766.0, 0.0], 1]     # same heading, moved

    def drive(reports, flag, stamp_age=0.0, plane=7):
        """Run the shipped arm over `reports` with ZERO_LEAD set to `flag`.

        `stamp_age` back-dates the send-side hook's `grant_at` by that many
        seconds. The arm reads the real clock for its own `now`, so the rate
        limit is driven by moving the LAST GRANT rather than by faking the
        present: `stamp_age=0` leaves every send inside the floor (the rate
        limit bites) and `stamp_age=10` puts every send well outside it (the
        limit is open), with no monkey-patching of `time`.
        """
        st = {"pos": (1000.0, 2000.0), "plane": plane, "pos_seen": 0.0}
        w, r = Sent(st), FakeRec()
        # KBD_SYNC PINNED OFF HERE AND AT EVERY OTHER HARNESS IN THIS FILE,
        # and the reason is what this file is FOR. Its subject is the
        # `--zero-lead` arm: the point it grants, the gate it drops, the plane
        # words it carries. MOVECODE-1z-t (KBD_SYNC, default ON) rides on top
        # of that same send site and LEADS the point 520 u, so a harness that
        # leaves it armed stops measuring zero-lead and starts measuring the
        # composition of two policies -- which is a real thing to test and is
        # tested, in test_kbdsync.py, against its own registered evidence.
        # Pinning it off is not hiding the new default; it is keeping ONE
        # variable per test, which is why these checks could catch anything.
        was = authsrv.ZERO_LEAD
        was_ks = authsrv.KBD_SYNC
        authsrv.ZERO_LEAD = flag
        authsrv.KBD_SYNC = False
        try:
            for v in reports:
                w.now = time.time() - stamp_age
                arm(v, st, r, w, 0)
        finally:
            authsrv.ZERO_LEAD = was
            authsrv.KBD_SYNC = was_ks
        return st, w, r

    st, w, r = drive([HEAD], True, stamp_age=10.0)
    grants = w.of(authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT)
    check(len(grants) == 1 and grants[0][1][1] == [1000.5, 2000.25]
          and grants[0][1][1][0] is not None,
          "PAYLOAD: the granted point is the reported position VERBATIM, to the "
          "byte",
          f"{grants[0][1] if grants else None} against a report of "
          f"[1000.5, 2000.25] and a server model at (1000.0, 2000.0). Not "
          f"state['pos'] (stale in exactly the window a trust refusal opens), "
          f"not model_dest (OUR navmesh's opinion, the first of the two defects "
          f"that made --heading-grant warp), and not reported + anything")
    check(len(grants[0][1]) == 4 and grants[0][1][2] == 7
          and grants[0][1][3] == 7,
          "and both plane words are the client's own reported plane",
          f"{grants[0][1]} -- field 3 is the destination's plane and field 4 the "
          f"current one, closed from the binary three times. For a zero-distance "
          f"grant they are the same plane; forcing 0 writes a wrong map index "
          f"into agent+0x80")
    dirs = w.of(authsrv.GAME_SMSG_AGENT_MOVE_DIRECTION)
    check(len(dirs) == 1 and dirs[0][1][1] == [1.0, 0.0] and dirs[0][1][2] == 1,
          "and exactly ONE 0x0025 rides with it, unit length, echoing the "
          "client's movementType",
          f"{[d[1] for d in dirs]} -- retail's burst shape. Both paths route "
          f"through one send site, so no arrangement of flags can put two "
          f"0x0025 in one report's burst")
    check(w.rows.index(dirs[0]) < w.rows.index(grants[0]),
          "and the 0x0029 is LAST in the burst",
          f"{[row[0] for row in w.rows]} -- 3,023 of 3,071 live retail bursts "
          f"put the grant last, with zero counter-examples")
    check(st.get("dest") == (1766.5, 2000.25)
          and list(st["dest"]) != grants[0][1][1],
          "and state['dest'] still holds the server's own model leg, which is "
          "NOT what went on the wire",
          f"model={st.get('dest')} wire={grants[0][1][1]} -- "
          f"clip_to_walkable(state['pos'] + the client's own 766 u vec2). Said "
          f"precisely, because it matters on one report in the file: the leg is "
          f"built from state['pos'], NOT from `reported`, and those are the "
          f"same point only on an ACCEPTED report -- see the trust-refusal pair "
          f"below, where the model stays at 1766 while the wire carries 41000. "
          f"Our own opinion still respects walls for aggro, interaction and "
          f"collision. If these two were equal the flag would be granting the "
          f"766 u endpoint, which is --heading-grant and is REFUTED")
    # AND THE GRANT IS NOT WIRE-ONLY. `send()` runs _note_wire_move, which moves
    # the SYNC model and stamps the shared grant clock. "Only the wire changes"
    # was in three comments and a startup banner and it was too strong; this is
    # the check that keeps the corrected version honest, because sync_to is the
    # exact operand REALFIX-L1's movetap separation metric reads.
    check(st.get("sync_to") == (1000.5, 2000.25)
          and st.get("grant_at") is not None,
          "and the grant is NOT wire-only: it moves the SYNC model and stamps "
          "the shared grant clock",
          f"sync_to={st.get('sync_to')} sync_at={st.get('sync_at')} "
          f"grant_at={st.get('grant_at')} -- _note_wire_move runs inside send() "
          f"for every player 0x0029 whatever arm sent it. sync_to is what "
          f"movetap's separation metric is compared against, and grant_at is "
          f"the CLICK arm's rate clock, so the flag reaches two server-side "
          f"models besides the wire")

    # ---- THE TRUST GUARD IS ADVISORY ON THE GRANT PATH -----------------
    # WHAT EARNS THIS. Section 2 above is this file's headline: the position
    # trust guard refuses an impossible jump and never latches. Under
    # --zero-lead that guard's refusal DOES NOT stop the grant -- the rejected
    # point goes on the wire verbatim and drags sync_to with it, while
    # state['pos'] correctly holds. That is the design (the client says it is
    # STANDING there, so the point is on its own history polyline whatever we
    # believe, and granting state['pos'] instead would grant a point the player
    # has already left) and it is the sharpest edge on the flag, so it is
    # driven here rather than discovered in REALFIX-L1. It was neither
    # documented nor driven until an adversarial pass found it.
    JUMP = [1, [41000.0, 2000.0], 7, [766.0, 0.0], 1]

    def drive_jump(pos_seen):
        st_j = {"pos": (1000.0, 2000.0), "plane": 7, "pos_seen": pos_seen}
        w_j, r_j = Sent(st_j), FakeRec()
        w_j.now = time.time() - 10.0
        was_j, was_ks = authsrv.ZERO_LEAD, authsrv.KBD_SYNC
        authsrv.ZERO_LEAD = True
        authsrv.KBD_SYNC = False        # one variable -- see the note above
        try:
            arm(JUMP, st_j, r_j, w_j, 0)
        finally:
            authsrv.ZERO_LEAD = was_j
            authsrv.KBD_SYNC = was_ks
        return st_j, w_j, r_j

    # `pos_seen = now` leaves the budget at the flat 900 u, so a 40,000 u claim
    # is refused. Section 1 proves the budget only ever GROWS with silence, so
    # this is the tightest the guard ever is.
    st_j, w_j, r_j = drive_jump(time.time())
    j_grants = w_j.of(authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT)
    refused_report = [e for e in r_j.of("position_report")
                      if e.get("accepted") is False]
    check(len(refused_report) == 1 and st_j["pos"] == (1000.0, 2000.0)
          and len(j_grants) == 1 and j_grants[0][1][1] == [41000.0, 2000.0],
          "TRUST REFUSAL: a report the guard REJECTS is still granted VERBATIM",
          f"pos held at {st_j['pos']}, wire {j_grants[0][1] if j_grants else None} "
          f"-- the guard protects OUR position model from a garbage decode; it "
          f"does not certify a point unreachable. REALFIX-O5's witness argument "
          f"governs the wire: the client reported STANDING there. Granting "
          f"state['pos'] instead would be a lead BACKWARDS, taken in exactly "
          f"the window our model is least entitled to name a destination")
    check(st_j.get("sync_to") == (41000.0, 2000.0)
          and st_j.get("dest") == (1766.0, 2000.0),
          "and the SYNC model follows the rejected point while the MODEL leg "
          "stays on the position we still believe",
          f"sync_to={st_j.get('sync_to')} dest={st_j.get('dest')} -- the two "
          f"halves come apart exactly here, and only here. state['dest'] is "
          f"clip(state['pos'] + vec2) = (1766, 2000), NOT reported + vec2 = "
          f"(41766, 2000). sync_to is what movetap's separation metric reads, "
          f"so REALFIX-L1 must expect this arm to drag it; a run that scores a "
          f"separation spike here is seeing the design and not a defect")
    # THE CONTROL, and without it the pair above is just "a grant happened".
    # The SAME report with a stale `pos_seen` is ACCEPTED (the budget grows at
    # CLIENT_POSITION_TRUST_RATE), and then the model moves too -- so what the
    # two runs differ in is the REFUSAL, not the report or the flag.
    st_a, w_a, r_a = drive_jump(time.time() - 120.0)
    a_grants = w_a.of(authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT)
    check(st_a["pos"] == (41000.0, 2000.0)
          and len(a_grants) == 1 and a_grants[0][1][1] == [41000.0, 2000.0]
          and st_a.get("dest") == (41766.0, 2000.0),
          "CONTROL: the SAME report ACCEPTED grants the same point, and now the "
          "model moves with it",
          f"pos={st_a['pos']} dest={st_a.get('dest')} wire="
          f"{a_grants[0][1][1] if a_grants else None} -- 120 s of silence puts "
          f"the budget past 40,000 u. The wire is identical in both runs, which "
          f"is what makes the refusal ADVISORY rather than merely absent, and "
          f"state['dest'] here IS reported + vec2 because the two points have "
          f"become the same point")

    # THE GATE-DROP, BOTH DIRECTIONS, and this is the pair that cannot be
    # written as an AST match. `SAME` repeats the heading, so `turned` is False
    # and `walking` is already True -- the shipped gate at :9878 SKIPS it.
    st_on, w_on, r_on = drive([HEAD, SAME], True, stamp_age=10.0)
    st_off, w_off, r_off = drive([HEAD, SAME], False, stamp_age=10.0)
    on_grants = w_on.of(authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT)
    check(len(on_grants) == 2 and on_grants[1][1][1] == [1400.5, 2000.25]
          and len(w_on.of(authsrv.GAME_SMSG_AGENT_MOVE_DIRECTION)) == 2,
          "GATE DROP: a moving report the shipped `turned` gate would SKIP is "
          "still granted under the flag, 0x0025 and all",
          f"{[row[2] for row in w_on.rows]} -- on click-free play that gate "
          f"opens on only 11.1/24.3/61.2/80.8% of moving reports (`ours`, "
          f"182554/182934/100340/173940), a 1.24x-9x cadence delta. Dropping it "
          f"is the flag's SECOND named variable and it is not free")
    check(len(w_off.rows) == 1
          and w_off.rows[0][0] == authsrv.GAME_SMSG_AGENT_MOVE_DIRECTION
          and w_off.rows[0][1] == w_on.rows[0][1]
          and "[" not in w_off.rows[0][2],
          "CONTROL: with the flag OFF the same two reports send one 0x0025 and "
          "NOTHING else -- the default path is byte-identical",
          f"off={[row[2] for row in w_off.rows]} vs on="
          f"{[row[2] for row in w_on.rows]}. `legacy_dir or zero_ok` IS "
          f"`legacy_dir` when the flag is off, so it is the same send with the "
          f"same payload in the same order, and the `[dir ...]` suffix on the "
          f"console line appears only under the flag. Without this check the "
          f"restructuring that hoisted `unit` out of the gate could have "
          f"changed the shipped build and nothing would say so")

    # THE RATE LIMIT, ON THE ARM. A second report inside the floor grants
    # NOTHING and holds NOTHING.
    st_r, w_r, r_r = drive([HEAD, SAME], True, stamp_age=0.0)
    refused = [e for e in r_r.of("grant_verdict") if e["fired"] is False]
    check(len(w_r.of(authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT)) == 1
          and len(refused) == 1 and refused[0]["reason"] == "heading-rate",
          "RATE: two reports 0 s apart produce ONE grant, and the refusal is "
          "recorded",
          f"grants={len(w_r.of(authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT))} "
          f"refusals={[e['reason'] for e in refused]}")
    check("grant_pending" not in st_r,
          "and a refused heading grant is DROPPED, not held",
          f"{st_r.get('grant_pending')} -- the next 0x003D supersedes it by "
          f"construction at a measured 0.28-0.30 s median, so holding it would "
          f"grant a position the player has already left. A held CLICK is the "
          f"player's choice; a held heading is our guess about a stale one")

    # THE FOURTH CELL OF THE 2x2: legacy wants the direction, zero-lead is
    # rate-refused. The shipped send must still go out -- a flag that suppresses
    # the default build's own 0x0025 while refusing its grant would make the
    # A/B's treatment arm quieter than the control on a message it does not
    # even govern.
    TURNED = [1, [1400.5, 2000.25], 7, [0.0, 766.0], 1]
    st_t, w_t, r_t = drive([HEAD, TURNED], True, stamp_age=0.0)
    late = r_t.of("grant_verdict")[-1]
    check(len(w_t.of(authsrv.GAME_SMSG_AGENT_MOVE_DIRECTION)) == 2
          and len(w_t.of(authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT)) == 1
          and late["fired"] is False and late["direction"] == "legacy",
          "a report the LEGACY gate wants but the rate limit refuses still "
          "sends its 0x0025, and only that",
          f"{[row[2] for row in w_t.rows]}, last verdict {late['reason']}/"
          f"{late['direction']} -- the four cells of (legacy wants it) x "
          f"(zero-lead wants it) are legacy+zero-lead / zero-lead / legacy / "
          f"none, and all four are now driven")

    # THE TELEMETRY, on the click arm's own channel so one consumer sees both.
    rows_on = r_on.of("grant_verdict")
    rows_r = r_r.of("grant_verdict")
    check(len(rows_on) == 2 and all(e["fired"] for e in rows_on)
          and all(e["reason"] == "zero-lead" and e["arm"] == "zero-lead"
                  for e in rows_on)
          and [e["dest"] for e in rows_on] == [[1000.5, 2000.25],
                                               [1400.5, 2000.25]]
          and rows_on[0]["since_last"] is None,
          "TELEMETRY: every evaluation is recorded on the click arm's own "
          "`grant_verdict` channel, with the new reasons and an `arm` field",
          f"{rows_on} -- a log holding only its own successes cannot score the "
          f"flag against the cadence it exists to bound, and the first row's "
          f"`since_last` is None rather than 0.0 because nothing had been "
          f"granted yet")
    check(len(rows_r) == 2 and [e["fired"] for e in rows_r] == [True, False]
          and [e["reason"] for e in rows_r] == ["zero-lead", "heading-rate"],
          "and a REFUSAL is recorded on the same channel, not dropped silently",
          f"{[(e['fired'], e['reason']) for e in rows_r]} -- grantsim's C3 "
          f"heading arm reads these rows, and a refusal that leaves no row "
          f"makes the replay's denominator the wrong number")
    check([e["direction"] for e in rows_on] == ["legacy+zero-lead", "zero-lead"]
          and rows_r[1]["direction"] == "none",
          "and it records WHICH path asked for the 0x0025, so a capture can "
          "separate the two populations",
          f"{[e['direction'] for e in rows_on]} then "
          f"{rows_r[1]['direction']!r} on the refusal -- report 1 turned (both "
          f"paths wanted the direction, ONE went out); report 2 did not, so "
          f"only the zero-lead path wanted it; and a rate-refused report sends "
          f"no direction at all, which is the cadence the legacy gate would "
          f"have had")

    # THE STOP ARM, BOTH REGIMES -- and this check changed shape on
    # 2026-09-03 rather than being deleted, because the thing it guards is
    # still dangerous and is now guarded from a different side.
    #
    # It used to read "with --zero-lead ON a 0x0047 grants NOTHING", on the
    # ground that a stop-arm 0x0029 IS --stop-echo and --stop-echo is REFUTED
    # (authsrv.py:1071-1152). MOVECODE-1z-t sends one by default, so that
    # sentence is no longer the rule -- and the epitaph's OWN 2026-08-25
    # correction block is why it never was the whole rule: "the harm is the
    # WALK, whose length is |D - the sync copy's settled +0x78| --
    # reconstructed at ~1,286 u for the 2026-08-19 echo, against a ~60 u p50
    # for retail's own stop-ack, which is MECHANICALLY THE SAME MESSAGE."
    # The refutation is of BAKING A LONG LEG FROM A FAR COPY, not of the
    # message. What made 2026-08-19 fatal was a copy 1,286 u away; what keeps
    # 1z-t safe is term 1 holding the copy at one report of lag, which is the
    # precondition the correction names.
    #
    # So the tripwire is re-aimed, not removed, and it now has THREE jobs:
    # the legacy wire still grants nothing; the default sends retail's stop
    # reply in retail's order; and NEITHER regime ever sends 0x0028 on a stop
    # (FINDINGS sec.3.2 states that one as an instruction to a server author,
    # and retail sends it on 7 of 114 stops).
    stop_arm = receive_arm("GAME_CMSG_LAST_POS_BEFORE_MOVE_CANCELED",
                           ("values", "state", "rec", "send", "conn_id"))

    def drive_stop(kbd_sync):
        st = {"pos": (1000.0, 2000.0), "plane": 7, "pos_seen": 0.0,
              "kbd_moving_at": 1000.0, "a2_family_sent": 1}
        w, r = Sent(st), FakeRec()
        was_zl, was_ks = authsrv.ZERO_LEAD, authsrv.KBD_SYNC
        authsrv.ZERO_LEAD, authsrv.KBD_SYNC = True, kbd_sync
        try:
            stop_arm([1, [1400.5, 2000.25], 7], st, r, w, 1)
        finally:
            authsrv.ZERO_LEAD, authsrv.KBD_SYNC = was_zl, was_ks
        return st, w

    st_s, w_s = drive_stop(False)
    check(w_s.of(authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT) == []
          and st_s.get("kbd_moving_at") is None,
          "STOP ARM, --legacy-kbd-sync: a 0x0047 grants NOTHING, and still "
          "clears the latch -- the pre-1z-t wire, unchanged",
          f"{[row[2] for row in w_s.rows]} -- this is the revert arm and it "
          f"must be byte-identical to the server that shipped before "
          f"MOVECODE-1z-t, or --legacy-kbd-sync is not a revert")

    st_k, w_k = drive_stop(True)
    grants_k = w_k.of(authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT)
    speeds_k = w_k.of(authsrv.GAME_SMSG_AGENT_UPDATE_SPEED)
    check(len(grants_k) == 1
          and list(grants_k[0][1][1]) == [1400.5, 2000.25]
          and grants_k[0][1][2] == 7 and grants_k[0][1][3] == 7,
          "STOP ARM, the 1z-t default: ONE zero-distance 0x0029 at the "
          "REPORTED stop, verbatim, with BOTH plane words the client's own",
          f"{grants_k} -- retail's own dominant stop reply: 70 of 114 live "
          f"stops land < 1 u from the reported stop, |dest - stop| p50 "
          f"0.000 u. A point of OUR choosing here would be a lead backwards "
          f"at the one instant the client has told us exactly where it is")
    _i_speed = next(i for i, r in enumerate(w_k.rows)
                    if r[0] == authsrv.GAME_SMSG_AGENT_UPDATE_SPEED)
    _i_grant = next(i for i, r in enumerate(w_k.rows)
                    if r[0] == authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT)
    check(len(speeds_k) == 1 and speeds_k[0][1][1] == 1.0
          and speeds_k[0][1][2] == 9 and _i_speed < _i_grant,
          "and 0x002B [1.0, 9] goes out BEFORE it -- retail's order, and the "
          "client bakes the re-pin from a +0x60 the [1.0, 9] has already set",
          f"{[row[2] for row in w_k.rows]} -- swapped, the wire shows a stop "
          f"burst retail has zero witnesses for, and the re-pin's leg is "
          f"baked at whatever family the last walk left in +0x60")
    check(st_k.get("a2_family_sent") is None
          and st_k.get("kbd_moving_at") is None,
          "and the stop resets the family edge AND still clears the latch",
          f"family_sent={st_k.get('a2_family_sent')} "
          f"kbd={st_k.get('kbd_moving_at')} -- the [1.0, 9] just overwrote "
          f"sync +0x60, so the next leg must re-send its family even "
          f"unchanged; without the reset the copy walks a whole leg at 288 "
          f"while the body backpedals at 190.1")
    check(w_s.of(authsrv.GAME_SMSG_AGENT_STOP_MOVING) == []
          and w_k.of(authsrv.GAME_SMSG_AGENT_STOP_MOVING) == [],
          "NEITHER regime sends 0x0028 on a stop -- the one thing FINDINGS "
          "sec.3.2 tells a server author not to do",
          f"legacy={[r[2] for r in w_s.rows]} default={[r[2] for r in w_k.rows]}"
          f" -- retail sends 0x0028 on 7 of 114 stops (6.1%); 0x0028 halts "
          f"BOTH copies where they stand, so on a stop it freezes the drift "
          f"in instead of collecting it")
    def zl_names(node):
        return [n for n in ast.walk(node)
                if isinstance(n, ast.Name) and n.id == "ZERO_LEAD"]

    def arm_node(name):
        for n in ast.walk(src):
            if (isinstance(n, ast.If) and isinstance(n.test, ast.Compare)
                    and isinstance(n.test.left, ast.Name)
                    and n.test.left.id == "opcode"
                    and len(n.test.comparators) == 1
                    and isinstance(n.test.comparators[0], ast.Name)
                    and n.test.comparators[0].id == name):
                return n
        return None

    zl_blocks = [n for n in ast.walk(src)
                 if isinstance(n, ast.If) and isinstance(n.test, ast.Name)
                 and n.test.id == "ZERO_LEAD"]
    zl_send_blocks = [n for n in zl_blocks
                      if any(isinstance(c, ast.Call)
                             and isinstance(c.func, ast.Name)
                             and c.func.id == "send" for c in ast.walk(n))]
    zl_sends = [c for n in zl_send_blocks for c in ast.walk(n)
                if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
                and c.func.id == "send"]

    def _in_cw_guard(node, block):
        """Is `node` inside the `if cw_dest is not None:` branch of `block`?

        That guard is CANCELWALK's lead arm (2026-08-24): live only on the
        report whose press cancelled a held action, and the one licence for
        a second send (the 0x002B rate rider) inside the zero-lead block.
        """
        for n in ast.walk(block):
            if (isinstance(n, ast.If) and isinstance(n.test, ast.Compare)
                    and isinstance(n.test.left, ast.Name)
                    and n.test.left.id == "cw_dest"
                    and any(node is d for d in ast.walk(n))):
                return True
        return False

    zl_default_sends = [c for c in zl_sends
                        if not _in_cw_guard(c, zl_send_blocks[0])] \
        if zl_send_blocks else []
    check(len(zl_send_blocks) == 1 and len(zl_default_sends) == 1,
          "and exactly ONE `if ZERO_LEAD:` block in the file SENDS anything, "
          "and outside CANCELWALK's cw_dest guard it sends exactly once",
          f"{len(zl_blocks)} ZERO_LEAD blocks of which {len(zl_send_blocks)} "
          f"send, {len(zl_default_sends)} default-path sends of "
          f"{len(zl_sends)} total -- two default sends would be two policies, "
          f"which is how the heading arm once granted twice per report. The "
          f"cw_dest guard is --cancel-answer's lead arm (diagnostic, off by "
          f"default), whose 0x002B rider is the licensed extra. (The second, "
          f"sendless block is the verdict hoist that keeps the 0x0025 to one "
          f"send site.)")
    heading_arm_ast = arm_node("GAME_CMSG_TURN_TO_DIRECTION")
    stop_arm_ast = arm_node("GAME_CMSG_LAST_POS_BEFORE_MOVE_CANCELED")
    click_arm_ast = arm_node("GAME_CMSG_MOVE_TO_COORD")
    check(zl_names(heading_arm_ast) and not zl_names(stop_arm_ast)
          and not zl_names(click_arm_ast),
          "NO STOP-ARM CHANGE AND NO CLICK-ARM CHANGE: ZERO_LEAD is named in "
          "the heading arm and in NEITHER of the other two",
          f"heading={len(zl_names(heading_arm_ast))} "
          f"stop={len(zl_names(stop_arm_ast))} "
          f"click={len(zl_names(click_arm_ast))} -- a stop-arm grant IS "
          f"--stop-echo (REFUTED, :1004-1023) and a click-arm change would make "
          f"REALFIX-L1 a two-variable A/B. The heading count is the positive "
          f"control: a matcher that finds ZERO_LEAD nowhere would pass the "
          f"other two halves for the wrong reason")
    zl = zl_send_blocks[0] if zl_send_blocks else None
    payload = (zl_default_sends[0].args[1].elts
               if zl_default_sends else [])
    dest_arg = payload[1] if len(payload) > 1 else None
    # The point is carried by `zl_point`, whose ONLY assignments in the block
    # must be CANCELWALK's `cw_dest` and the default branch's IfExp
    # `a2_dest if a2_dest is not None else list(reported)` -- so the shipped
    # payload is still the reported position VERBATIM when --d1-lead is off
    # (a2_dest is None unless that flag armed it, and the flag is
    # default-False with its own lattice), and the two other values are the
    # two AUDITED arms: --cancel-answer's lead (diagnostic) and REALFIX-A2's
    # d1 lead (the bundle, REALFIX.md sec.0.9, its own cells and locks in
    # test_d1lead.py). EXTENDED 2026-08-26 for A2: this check originally
    # admitted only list(reported)|cw_dest, and it went red the moment the
    # A2 edit landed -- which is this lock doing its job; the extension is
    # deliberate and names the new value, not a loosening to "anything".
    def _is_list_reported(r):
        return (isinstance(r, ast.Call) and isinstance(r.func, ast.Name)
                and r.func.id == "list" and len(r.args) == 1
                and isinstance(r.args[0], ast.Name)
                and r.args[0].id == "reported")

    def _is_a2_ifexp(r):
        return (isinstance(r, ast.IfExp)
                and isinstance(r.body, ast.Name) and r.body.id == "a2_dest"
                and _is_list_reported(r.orelse)
                and isinstance(r.test, ast.Compare)
                and isinstance(r.test.left, ast.Name)
                and r.test.left.id == "a2_dest")

    zl_point_rhs = [n.value for n in ast.walk(zl)
                    if isinstance(n, ast.Assign) and len(n.targets) == 1
                    and isinstance(n.targets[0], ast.Name)
                    and n.targets[0].id == "zl_point"] if zl else []
    rhs_ok = (len(zl_point_rhs) == 2 and any(
        _is_a2_ifexp(r) for r in zl_point_rhs) and any(
        isinstance(r, ast.Name) and r.id == "cw_dest" for r in zl_point_rhs))
    check(isinstance(dest_arg, ast.Name) and dest_arg.id == "zl_point"
          and rhs_ok,
          "the source grants `zl_point`, and its only values are `cw_dest` "
          "(--cancel-answer's lead arm) and the A2 IfExp whose else-branch "
          "is `list(reported)` -- the shipped default is still the "
          "reported position verbatim, provable from source, with "
          "--d1-lead's a2_dest as the one other audited value",
          f"dest={ast.dump(dest_arg) if dest_arg is not None else None} "
          f"rhs={[ast.dump(r) for r in zl_point_rhs]}")
    zl_clipped = zl is not None and any(
        isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
        and c.func.id == "clip_to_walkable" for c in ast.walk(zl))
    zl_state_pos = zl is not None and any(
        isinstance(n.value, ast.Name) and n.value.id == "state"
        and isinstance(getattr(n, "slice", None), ast.Constant)
        and n.slice.value == "pos"
        for n in ast.walk(zl) if isinstance(n, ast.Subscript))
    check(not zl_clipped and not zl_state_pos,
          "and the block neither clips nor reaches for state['pos']",
          f"clip={zl_clipped} state_pos={zl_state_pos} -- those are the two "
          f"defects that made --heading-grant warp the owner's character, and "
          f"the point is walkable by WITNESS: the client reported standing on it")
    # THE CONTROL. Both matchers above only run against healthy source.
    bad = ast.parse("if ZERO_LEAD:\n"
                    "    d = clip_to_walkable(state, state['pos'])\n"
                    "    send(OP, [PLAYER_AGENT_ID, list(d), plane, plane], 'x')")
    bnode = next(n for n in ast.walk(bad) if isinstance(n, ast.If))
    bad_clip = any(isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
                   and c.func.id == "clip_to_walkable" for c in ast.walk(bnode))
    bad_state = any(
        isinstance(n.value, ast.Name) and n.value.id == "state"
        and isinstance(getattr(n, "slice", None), ast.Constant)
        and n.slice.value == "pos"
        for n in ast.walk(bnode) if isinstance(n, ast.Subscript))
    check(bad_clip and bad_state,
          "CONTROL: both matchers still SEE the old defects when handed them",
          f"clip={bad_clip} state_pos={bad_state} -- if either stopped matching, "
          f"the check above would pass for the wrong reason")

    # ---- the CALL SITE, which is the half the matrix does not reach ----
    # WHAT EARNS THIS. The matrix below drives the pure `zero_lead_composition`
    # six ways, and every one of those cells goes red on a bad refusal. None of
    # them touches the thing that ACTS on the answer. An adversarial pass
    # replaced `raise SystemExit(_zl_refusal)` in main() with a print and this
    # file stayed green at 147 of 147 -- a server started with `--zero-lead
    # --client-endpoint` would then set both flags and answer every 0x003D with
    # two destinations. The function's own docstring says a refusal nobody has
    # seen fire is a wish; a refusal nobody RAISES is the same wish one level
    # up. main() cannot be executed here (it binds a listener), so the call site
    # is read out of the syntax tree.
    main_fn = next((n for n in ast.walk(src)
                    if isinstance(n, ast.FunctionDef) and n.name == "main"),
                   None)
    if main_fn is None:
        raise AssertionError(
            "no main() in authsrv.py -- this reader must FAIL LOUDLY rather "
            "than hand back nothing, which would pass the call-site checks "
            "below vacuously")
    comp_assign = next(
        (n for n in ast.walk(main_fn)
         if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call)
         and isinstance(n.value.func, ast.Name)
         and n.value.func.id == "zero_lead_composition"), None)
    refusal_name = None
    if comp_assign is not None and isinstance(comp_assign.targets[0],
                                              ast.Tuple):
        first = comp_assign.targets[0].elts[0]
        refusal_name = first.id if isinstance(first, ast.Name) else None
    raises = [n for n in ast.walk(main_fn)
              if isinstance(n, ast.If) and isinstance(n.test, ast.Name)
              and refusal_name is not None and n.test.id == refusal_name
              and len(n.body) == 1 and isinstance(n.body[0], ast.Raise)
              and isinstance(n.body[0].exc, ast.Call)
              and isinstance(n.body[0].exc.func, ast.Name)
              and n.body[0].exc.func.id == "SystemExit"]
    check(comp_assign is not None and refusal_name is not None
          and len(raises) == 1,
          "CALL SITE: main() RAISES SystemExit on the refusal -- it does not "
          "print it and carry on",
          f"assign={comp_assign is not None} refusal={refusal_name!r} "
          f"raises={len(raises)} -- replacing this `raise` with a print left "
          f"all 147 checks green while the server ran a combination it had just "
          f"declared impossible. The matrix below tests what the function "
          f"DECIDES; this tests what main() DOES about it")
    comp_kwargs = sorted(k.arg for k in comp_assign.value.keywords) \
        if comp_assign is not None else []
    # THE EXPECTED SET IS THE FUNCTION'S OWN SIGNATURE, not a literal, and that
    # is a 2026-08-21 correction rather than a loosening. This check carried the
    # eight names spelled out; adding `arrival_carry` to
    # `zero_lead_composition` for REALFIX-F1b turned it red, which is the check
    # WORKING -- but the only maintenance it can prompt is "paste the ninth name
    # in", and a list somebody pastes into is a list that eventually gets pasted
    # into wrongly. Read off the signature it is asserting about, the check
    # still goes red on exactly the defect it was built for (a parameter the
    # call site never fills defaults to False, so its refusal can never fire
    # from a real command line -- which is how --stop-echo went unrefused) and
    # can no longer drift. `params` is asserted non-empty so a signature that
    # lost all its keywords cannot make this vacuously true.
    comp_params = sorted(
        inspect.signature(authsrv.zero_lead_composition).parameters)
    check(bool(comp_params) and comp_kwargs == comp_params,
          "and every flag the function can decide about is actually PASSED to "
          "it from argv",
          f"call site {comp_kwargs} against the signature's {comp_params} -- a "
          f"parameter the call site never fills defaults to False, so the "
          f"refusal for it can never fire from a real command line. That is "
          f"exactly how --stop-echo went unrefused: the function is only as "
          f"wide as its narrowest caller")
    # THE CONTROL. Both matchers above only ran against healthy source.
    bad_main = ast.parse(
        "def main():\n"
        "    r, notes = zero_lead_composition(zero_lead=a.zero_lead)\n"
        "    if r:\n"
        "        print(r)\n")
    bad_fn = next(n for n in ast.walk(bad_main)
                  if isinstance(n, ast.FunctionDef))
    bad_assign = next(
        (n for n in ast.walk(bad_fn)
         if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call)
         and isinstance(n.value.func, ast.Name)
         and n.value.func.id == "zero_lead_composition"), None)
    bad_name = bad_assign.targets[0].elts[0].id
    bad_raises = [n for n in ast.walk(bad_fn)
                  if isinstance(n, ast.If) and isinstance(n.test, ast.Name)
                  and n.test.id == bad_name and len(n.body) == 1
                  and isinstance(n.body[0], ast.Raise)]
    bad_kwargs = sorted(k.arg for k in bad_assign.value.keywords)
    check(bad_assign is not None and not bad_raises
          and bad_kwargs == ["zero_lead"],
          "CONTROL: the same two matchers SEE a printed refusal and a "
          "half-filled call when handed them",
          f"raises={len(bad_raises)} kwargs={bad_kwargs} -- if either stopped "
          f"matching, the two checks above would pass for the wrong reason")

    # ---- the pre-registered banner, which is evidence and not decoration ----
    # REALFIX.md sec. 4 and the flag's own comment both rest on "the prediction
    # is printed VERBATIM at startup so it cannot be rationalised afterwards".
    # Nothing read it: deleting the RETRACTED line and the whole PREDICTION
    # block left this file green at 147. If the banner is load-bearing for
    # REALFIX-L1's honesty it has to be pinned; if it is not, the claim has to
    # stop being made. It is pinned -- on the SUBSTANTIVE lines only (the
    # retraction and the three numeric bounds), not on the prose around them,
    # because pinning the prose would make every wording fix a red test.
    zl_arg = next((n for n in ast.walk(main_fn)
                   if isinstance(n, ast.If)
                   and ((isinstance(n.test, ast.Attribute)
                         and n.test.attr == "zero_lead")
                        or (isinstance(n.test, ast.Name)
                            and n.test.id == "zero_lead"))), None)

    def printed_text(node):
        """Only strings that reach a `print(...)`, because only those are seen.

        Collecting every string constant in the block would pass a banner whose
        `print(` had been changed to an assignment -- the text still present in
        the source and no operator ever seeing it. That is not hypothetical: it
        is the first mutation this check was tried against, and it survived the
        looser reader.
        """
        out = []
        for call in ast.walk(node) if node is not None else ():
            if not (isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Name)
                    and call.func.id == "print"):
                continue
            for c in ast.walk(call):
                if isinstance(c, ast.Constant) and isinstance(c.value, str):
                    out.append(c.value)
        return " ".join(out)

    banner = printed_text(zl_arg)
    wanted = ("RETRACTED", "1.0 hard rows per minute", "40 u per active second",
              "p50 <= 150 u and p90 <= 520 u", "FAILURE SIGNATURE",
              "REFUTE THE INVARIANT")
    missing = [w for w in wanted if w not in banner]
    check(zl_arg is not None and not missing,
          "BANNER: the retraction and all three pre-registered numeric bounds "
          "are printed at startup, verbatim",
          f"missing={missing} from a banner of {len(banner)} chars -- "
          f"REALFIX.md sec. 4's own words are 'printed verbatim at startup so "
          f"it cannot be rationalised afterwards', and this arc has already "
          f"lost a candidate (--heading-grant) whose prediction was MET while "
          f"its conclusion was wrong, because the prediction bounded SIZE and "
          f"the harm arrived as FREQUENCY. Both units are in the list above for "
          f"that reason")
    stripped = ast.parse("def main():\n    if a.zero_lead:\n"
                         "        ZERO_LEAD = True\n")
    # AND THE SECOND CONTROL IS THE MUTATION THAT SURVIVED THE FIRST DRAFT:
    # the banner text still in the source but assigned instead of printed.
    unprinted = ast.parse(
        "def main():\n    if a.zero_lead:\n"
        "        _dead = ('RETRACTED 1.0 hard rows per minute "
        "40 u per active second p50 <= 150 u and p90 <= 520 u "
        "FAILURE SIGNATURE REFUTE THE INVARIANT')\n")
    strip_banner = printed_text(
        next(n for n in ast.walk(stripped) if isinstance(n, ast.If)))
    unprinted_banner = printed_text(
        next(n for n in ast.walk(unprinted) if isinstance(n, ast.If)))
    check("--zero-lead" in banner and "REALFIX-P2" in banner
          and [w for w in wanted if w not in strip_banner] == list(wanted)
          and [w for w in wanted if w not in unprinted_banner] == list(wanted),
          "CONTROL: the same reader finds NOTHING in a stripped block, and "
          "nothing in one whose banner is present but never PRINTED",
          f"real banner {len(banner)} chars; stripped {len(strip_banner)}; "
          f"present-but-unprinted {len(unprinted_banner)} -- both are missing "
          f"all {len(wanted)} wanted lines. The second control exists because "
          f"the first version of this reader collected every string constant in "
          f"the block and therefore PASSED a banner whose `print(` had been "
          f"turned into an assignment: the text in the file, no operator ever "
          f"seeing it")

    # ---- the composition matrix ---------------------------------------
    # A refusal nobody has seen fire is a wish, so every cell is driven.
    #
    # AND THE LIST IS READ OFF THE SHIPPED TABLE, not restated here. The gap an
    # adversarial pass found was --stop-echo: the refusal keyed on "answers the
    # same 0x003D" and --stop-echo answers 0x0047, so `--zero-lead --stop-echo`
    # was allowed SILENTLY while REALFIX-P2's own spec block forbids it in
    # capitals and every stop echo stamps the same shared grant clock. A matrix
    # enumerated in the test would have had the identical hole, so the loop
    # takes its cases from authsrv.ZERO_LEAD_REFUSED_ARMS and the count is
    # pinned beside it.
    refused_arms = authsrv.ZERO_LEAD_REFUSED_ARMS
    check(len(refused_arms) == 3
          and sorted(row[0] for row in refused_arms) == [
              "--client-endpoint", "--heading-grant", "--stop-echo"],
          "COMPOSITION: the refusal list is exactly the three refuted arms that "
          "put a player 0x0029 on the wire",
          f"{[row[0] for row in refused_arms]} -- --stop-echo joined on "
          f"2026-08-21 after `--zero-lead --stop-echo` was found ALLOWED. It "
          f"answers 0x0047, so a refusal written as 'the same 0x003D' could not "
          f"see it, and REALFIX-P2's spec forbids it by name")
    for flag, trigger, line, _what in refused_arms:
        kw = flag.lstrip("-").replace("-", "_")
        why = authsrv.zero_lead_composition(zero_lead=True, **{kw: True})[0]
        check(why is not None and "cannot be combined" in why
              and flag in why and "REFUTED" in why
              and f":{line}" in why
              and not any(o[0] in why for o in refused_arms if o[0] != flag),
              f"COMPOSITION: --zero-lead REFUSES to combine with {flag}, and "
              f"cites {flag}'s OWN line",
              f"{why!r} -- each answers the player's own movement with its own "
              f"0x0029 on the one shared grant clock ({flag} on {trigger}), so "
              f"the client would hold two destinations and the run would "
              f"attribute the outcome to neither. The single-clash message used "
              f"to cite ':1049 and :1090' and say 'all of them' whatever was "
              f"passed, so a refusal about one flag offered another's line as "
              f"its ground")
    both = authsrv.zero_lead_composition(zero_lead=True, heading_grant=True,
                                         client_endpoint=True)[0]
    check(both is not None and "--heading-grant and --client-endpoint" in both
          and " are already REFUTED" in both
          and "authsrv.py:1049 and :1090" in both,
          "and it names BOTH when both are passed, in the plural, with both "
          "lines",
          f"{both!r}")
    for other, want in (("grant_suppress", "orthogonal arms"),
                        ("resync", "one arm at a time"),
                        ("click_sweep", "was not click-free")):
        why, notes = authsrv.zero_lead_composition(zero_lead=True,
                                                   **{other: True})
        check(why is None and len(notes) == 1 and want in notes[0],
              f"COMPOSITION: --{other.replace('_', '-')} is ALLOWED, and it "
              f"prints a note",
              f"refusal={why!r} notes={notes!r} -- allowing silently is how two "
              f"variables end up in an A/B built for one")
    pair = authsrv.zero_lead_composition(zero_lead=True, grant_suppress=True,
                                         resync=True)
    check(pair[0] is None and len(pair[1]) == 2,
          "and both allowed flags together print both notes",
          f"{pair}")
    check(authsrv.zero_lead_composition() == (None, [])
          and authsrv.zero_lead_composition(heading_grant=True,
                                            client_endpoint=True) == (None, []),
          "CONTROL: with --zero-lead OFF nothing is refused and nothing is "
          "printed",
          "the two refuted flags may still be run together against each other "
          "-- this function speaks only for --zero-lead, and a refusal that "
          "fires when the flag is off would be refusing everything")

    print("\n15. --plane-carry (REALFIX-F1) carries the PREVIOUS grant's plane")
    # WHAT EARNS THIS SECTION. REALFIX-L3 ran --zero-lead against the shipped
    # default with identical scripted input and scored on REALFIX-E alone (an
    # `async_at` step >= 150 u within <= 0.25 s): P0 0 events with 0 grants, P2
    # 3 events at 476.8 / 465.9 / 242.8 u. All three follow a grant by
    # 0.05-0.11 s, all three carry field 4 = 18 against a previous grant's 0,
    # and all three land on a SYNC copy reading plane 0 while the client is on
    # the bridge deck. The grant-level 2x2 from client memory: 8 plane-rewriting
    # above-cut grants -> 3 events, 28 above-cut grants with the plane word
    # UNCHANGED -> 0 events, Fisher exact p = 0.0078. The control is the
    # finding -- P0 carried 7x the plane-mismatch samples and 97% of its run
    # above the gate-1 cut and never moved its rendered copy more than 43 u.
    #
    # SO THE DELTA IS ONE FIELD, and this section's job is to prove it is one
    # field. Field 3 stays the newest report's plane; field 4 becomes the plane
    # that arrived WITH the point the SYNC copy is standing on, which under
    # zero lead is the previous grant's by construction. Everything the
    # separation half of the prediction rests on -- "F1 touches no position" --
    # is checked by comparing a carry-ON run against a carry-OFF one and
    # requiring every value except field 4 to be identical.
    #
    # AND IT IS A MODIFIER, NOT A POLICY. Two of the checks below exist only to
    # pin that: with --zero-lead off the flag changes nothing at all, and
    # passed alone it REFUSES rather than running inert.
    check(authsrv.PLANE_CARRY is False,
          "--plane-carry is off by default",
          "REALFIX-F1 is a candidate fix aimed at a reproduction, not a "
          "shipped behaviour. It is unproven until an F1 arm scores it against "
          "the --zero-lead arm REALFIX-L3 measured")

    def pc_report(x, plane, vec=(766.0, 0.0)):
        return [1, [x, 2000.25], plane, list(vec), 1]

    def drive_pc(steps, carry, zero_lead=True, wire=None, catch=()):
        """Run the shipped heading arm with ZERO_LEAD/PLANE_CARRY set.

        `steps` is [(report, may_grant), ...]. The rate limit is driven by
        setting the SHARED `grant_at` clock directly before each report --
        `may_grant=False` stamps it at `now`, inside the floor -- because the
        arm reads the real clock for its own `now` and the alternative is
        monkey-patching `time`. That is the same technique section 14's
        `drive()` uses through `Sent.now`, made per-report so a refusal can sit
        BETWEEN two grants, which is the shape the named limit is about.

        `wire` swaps in a different send() (see `PcDeadWire`) and `catch` names
        the exception class the driver absorbs, stashing it on `w.raised` --
        together they let a report be driven through a send that FAILS, which
        is the only way "the slot advances after the send" differs observably
        from "before it". `catch=()` is a real `except` clause that catches
        nothing, so every existing caller keeps propagating.
        """
        st = {"pos": (1000.0, 2000.0), "plane": 7, "pos_seen": 0.0}
        w, r = (Sent(st) if wire is None else wire(st)), FakeRec()
        w.raised = []
        was_zl, was_pc = authsrv.ZERO_LEAD, authsrv.PLANE_CARRY
        was_ks = authsrv.KBD_SYNC
        authsrv.ZERO_LEAD, authsrv.PLANE_CARRY = zero_lead, carry
        authsrv.KBD_SYNC = False        # one variable -- see the note above
        try:
            for values, may in steps:
                now = time.time()
                st["grant_at"] = now - (10.0 if may else 0.0)
                w.now = now - 10.0
                try:
                    arm(values, st, r, w, 0)
                except catch as exc:
                    w.raised.append(exc)
        finally:
            authsrv.ZERO_LEAD, authsrv.PLANE_CARRY = was_zl, was_pc
            authsrv.KBD_SYNC = was_ks
        return st, w, r

    class PcDeadWire(Sent):
        """`Sent`, but the socket dies on the Nth `0x0029` -- as sendall can.

        Faithful to the shipped `send()`'s ORDER, which is what makes the
        result mean anything: `_note_wire_move` runs BEFORE the bytes go out
        and the `sent` record is written AFTER, so a raise leaves the model
        updated and no row behind. That path is not invented here -- the
        shipped `send()` names it in its own words, "A GAP in seq means crypt
        advanced the keystream for a message whose plaintext never reached this
        file -- sendall raised in between".
        """

        def __init__(self, state, die_on):
            super().__init__(state)
            self.die_on, self.seen = die_on, 0

        def __call__(self, opcode, values, label, quiet=False):
            if opcode == authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT:
                self.seen += 1
                if self.seen == self.die_on:
                    authsrv._note_wire_move(
                        self.state, opcode, values,
                        time.time() if self.now is None else self.now)
                    raise OSError("sendall: connection reset by peer")
            return super().__call__(opcode, values, label, quiet)

    def payloads(w):
        return [row[1] for row in w.of(authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT)]

    # ---- the three payload cases the spec names --------------------------
    # (1) THE DOCUMENTED DEFAULT. No previous grant on record, so field 4 falls
    # back to the CURRENT plane -- which is exactly the pre-F1 payload. The
    # first grant of a session has no lagged copy to be wrong about, and a
    # default of 0 here would write a wrong map index into agent+0x80, which is
    # the defect the plane words exist to avoid.
    _, w_first, _ = drive_pc([(pc_report(1000.5, 7), True)], carry=True)
    first = payloads(w_first)
    check(len(first) == 1
          and first[0] == [authsrv.PLAYER_AGENT_ID, [1000.5, 2000.25], 7, 7],
          "FIRST GRANT: with no previous grant on record, field 4 defaults to "
          "the CURRENT plane -- field 4 == field 3",
          f"{first} -- `state.get('zl_last_grant_plane', plane)`. The default "
          f"is the documented one and it is not 0: a 0 would write a wrong map "
          f"index into agent+0x80, which is the whole reason both plane words "
          f"are carried rather than zeroed")

    # (2) THE PLANE BOUNDARY, and this is the case REALFIX-L3 measured. Report
    # 1 is on plane 0, report 2 is on plane 18 -- the bridge deck. F1 must send
    # field 3 = 18 (the destination is the newest report) and field 4 = 0 (the
    # plane that arrived with the point the copy is standing on, i.e. the
    # previous grant's). The shipped payload sends (18, 18), which is the
    # rewrite the 2x2 above associates with 3 of 8 grants.
    st_b, w_b, r_b = drive_pc([(pc_report(1000.5, 0), True),
                               (pc_report(1500.5, 18), True)], carry=True)
    cross = payloads(w_b)
    check(len(cross) == 2
          and cross[0] == [authsrv.PLAYER_AGENT_ID, [1000.5, 2000.25], 0, 0]
          and cross[1] == [authsrv.PLAYER_AGENT_ID, [1500.5, 2000.25], 18, 0],
          "PLANE CHANGE: field 3 is the NEW plane and field 4 is the PREVIOUS "
          "grant's",
          f"{cross} -- REALFIX-L3's three events all carry field 4 = 18 "
          f"against a previous grant's 0, onto a SYNC copy reading plane 0. "
          f"This is the one payload F1 changes, and the direction is 18 -> 0: "
          f"stamp the plane the copy is ON, not the plane the client reached")
    check(st_b.get("zl_last_grant_plane") == 18,
          "and the slot advances to the plane just sent",
          f"{st_b.get('zl_last_grant_plane')} -- the next grant carries THIS "
          f"plane in its field 4, which is what makes the correction "
          f"one-interval and self-maintaining rather than a latch")

    # (3) NO BOUNDARY, NO DELTA. Two grants on the same plane are byte-identical
    # to the shipped payload. Without this check, "F1 changes field 4" could be
    # satisfied by a flag that changes it on EVERY grant, which would be a
    # different policy with a different exposure.
    _, w_same, _ = drive_pc([(pc_report(1000.5, 7), True),
                             (pc_report(1500.5, 7), True)], carry=True)
    same = payloads(w_same)
    check(len(same) == 2 and same[0][2] == same[0][3] == 7
          and same[1][2] == same[1][3] == 7,
          "PLANE UNCHANGED: both fields stay equal, so F1 is inert off a "
          "boundary",
          f"{same} -- F1 must move field 4 ONLY where the two copies are on "
          f"different planes. A flag that rewrote field 4 on every grant would "
          f"pass 'the payload changed' and be a different policy")

    # ---- F1 OFF IS BYTE-IDENTICAL, and it is asserted against a LITERAL ----
    # The whole claim that this is a MODIFIER rests here: with --plane-carry
    # off, the --zero-lead arm must send what it sent before F1 existed. The
    # expected rows are written out by hand rather than compared against
    # another run of the same code, because comparing the code to itself would
    # pass for any pair of flags that agree with each other.
    st_off, w_off_pc, r_off_pc = drive_pc([(pc_report(1000.5, 0), True),
                                           (pc_report(1500.5, 18), True)],
                                          carry=False)
    off_rows = [(row[0], row[1], row[2]) for row in w_off_pc.rows]
    expect_off = [
        (authsrv.GAME_SMSG_AGENT_MOVE_DIRECTION,
         [authsrv.PLAYER_AGENT_ID, [1.0, 0.0], 1],
         "AGENT_MOVE_DIRECTION(1.000,0.000 type 1) [legacy+zero-lead]"),
        (authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT,
         [authsrv.PLAYER_AGENT_ID, [1000.5, 2000.25], 0, 0],
         "ZERO LEAD (1000,2000) plane 0 [dir legacy+zero-lead]"),
        (authsrv.GAME_SMSG_AGENT_MOVE_DIRECTION,
         [authsrv.PLAYER_AGENT_ID, [1.0, 0.0], 1],
         "AGENT_MOVE_DIRECTION(1.000,0.000 type 1) [zero-lead]"),
        (authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT,
         [authsrv.PLAYER_AGENT_ID, [1500.5, 2000.25], 18, 18],
         "ZERO LEAD (1500,2000) plane 18 [dir zero-lead]"),
    ]
    check(off_rows == expect_off,
          "F1 OFF: --zero-lead sends exactly what it sent before F1 existed -- "
          "opcode, payload and label, against a hand-written literal",
          f"{off_rows} against {expect_off} -- the SAME plane-crossing pair "
          f"that makes F1 send (18, 0) sends (18, 18) with the flag off. The "
          f"expectation is a literal and not a second run of this code, "
          f"because code compared against itself agrees by construction. Note "
          f"the label carries no `carry` token off a rewrite either")

    # ---- WITH --zero-lead OFF, F1 CHANGES NOTHING AT ALL -----------------
    # The modifier claim's other half, and the ground for the startup refusal:
    # there is no second send site. Driven rather than argued, because the
    # refusal in zero_lead_composition is only correct if this is true.
    _, w_zloff_on, r_zloff_on = drive_pc([(pc_report(1000.5, 0), True),
                                          (pc_report(1500.5, 18), True)],
                                         carry=True, zero_lead=False)
    _, w_zloff_off, r_zloff_off = drive_pc([(pc_report(1000.5, 0), True),
                                            (pc_report(1500.5, 18), True)],
                                           carry=False, zero_lead=False)
    check(w_zloff_on.rows == w_zloff_off.rows
          and w_zloff_on.of(authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT) == []
          and r_zloff_on.of("grant_verdict") == []
          and len(w_zloff_on.rows) == 1,
          "ZERO-LEAD OFF: --plane-carry changes NOTHING -- same wire, no "
          "0x0029 and no verdict row either way",
          f"on={[row[2] for row in w_zloff_on.rows]} "
          f"off={[row[2] for row in w_zloff_off.rows]} -- F1 has no send site "
          f"of its own, which is exactly why the flag is REFUSED at startup "
          f"without --zero-lead rather than documented as inert. This check is "
          f"the ground for that refusal; without it the refusal is an opinion")

    # ---- F1 TOUCHES NO POSITION, which is half the prediction -------------
    # "separation p50/p90 unchanged within 5%" is pre-registered on the grounds
    # that F1 moves a plane word and nothing else. That is checkable here
    # rather than in a live run: the same reports under carry ON and carry OFF
    # must agree on the destination, on the 0x0025, on the SYNC model and on
    # state["dest"], and differ in field 4 alone.
    on_ops = [row[0] for row in w_b.rows]
    off_ops = [row[0] for row in w_off_pc.rows]
    on_pts = [p[1] for p in cross]
    off_pts = [p[1] for p in payloads(w_off_pc)]
    on_dirs = [row[1] for row
               in w_b.of(authsrv.GAME_SMSG_AGENT_MOVE_DIRECTION)]
    off_dirs = [row[1] for row
                in w_off_pc.of(authsrv.GAME_SMSG_AGENT_MOVE_DIRECTION)]
    check(on_ops == off_ops and on_pts == off_pts and on_dirs == off_dirs
          and st_b.get("sync_to") == st_off.get("sync_to")
          and st_b.get("dest") == st_off.get("dest")
          and [p[3] for p in cross] == [0, 0]
          and [p[3] for p in payloads(w_off_pc)] == [0, 18],
          "NO POSITION MOVES: carry ON and carry OFF agree on every "
          "destination, on the SYNC model and on state['dest'] -- field 4 is "
          "the only difference",
          f"sync_to {st_b.get('sync_to')} vs {st_off.get('sync_to')}; dest "
          f"{st_b.get('dest')} vs {st_off.get('dest')}; field 4 "
          f"{[p[3] for p in cross]} vs {[p[3] for p in payloads(w_off_pc)]} -- "
          f"this is the mechanism behind the pre-registered 'separation p50/p90 "
          f"unchanged within 5%'. movetap measures separation against sync_to, "
          f"so a run where it MOVED would mean F1 had reached a position")

    # ---- THE NAMED LIMIT: the slot tracks SENDS, not evaluations ----------
    # F1 under-corrects when the copy is more than one grant interval behind --
    # after a rate-limit refusal or a stall. The half of that which is testable
    # offline is the bookkeeping: a REFUSED report must not advance the slot,
    # because no grant went out and the copy is still bound for the point the
    # last one named. If a refusal advanced it, the next grant would carry the
    # plane of a point the copy was never sent to, which is a worse error than
    # the one F1 fixes.
    st_l, w_l, r_l = drive_pc([(pc_report(1000.5, 0), True),
                               (pc_report(1200.5, 18), False),
                               (pc_report(1500.5, 18), True)], carry=True)
    lim = payloads(w_l)
    refusals_l = [e for e in r_l.of("grant_verdict") if e["fired"] is False]
    check(len(lim) == 2 and len(refusals_l) == 1
          and refusals_l[0]["reason"] == "heading-rate"
          and lim[1] == [authsrv.PLAYER_AGENT_ID, [1500.5, 2000.25], 18, 0],
          "NAMED LIMIT: a rate-REFUSED report does not advance the slot, so "
          "the next grant still carries the last SENT plane",
          f"{lim} with {[e['reason'] for e in refusals_l]} refused -- no grant "
          f"went out for the refused report, so the copy is still bound for "
          f"the point the last one named and 0 is still the right answer. This "
          f"is also where F1 UNDER-corrects: the copy may be in transit "
          f"between the grant before last and the last one, and if those "
          f"straddle a boundary the carried plane is the wrong one of the "
          f"pair. It is a one-interval correction for a one-interval lag")

    # ---- THE SAME INVARIANT FROM THE OTHER SIDE: a send that FAILED ------
    # WHY THIS CHECK EXISTS, and it is a survivor's fix. A mutation lane moved
    # `state["zl_last_grant_plane"] = plane` from AFTER the send() to BEFORE it,
    # inside the same `if zero_ok:`, and section 15 stayed green -- it was read
    # as a provable no-op, on the grounds that nothing between the read and the
    # write observes the slot. That is true for a send that RETURNS, and the two
    # orderings are not the same program otherwise: `send()` ends in
    # `sock.sendall`, which raises, and the shipped code says so where it
    # explains its own seq gaps. With the write after the send, a message that
    # never reached the wire does not advance the slot; with it before, the next
    # grant carries the plane of a point the copy was never sent to -- exactly
    # the error the refusal case above is about, reached by a different door.
    # The verdict row is a separate matter and is NOT claimed here: it is
    # written before the send, so a dead wire also leaves a `fired=True` row for
    # a message that never went out. That is narrower than the slot -- a session
    # whose sendall raised is over -- but it is worth knowing when reading the
    # last row of a truncated capture.
    st_d, w_d, _r_d = drive_pc([(pc_report(1000.5, 0), True),
                                (pc_report(1500.5, 18), True)], carry=True,
                               wire=lambda st: PcDeadWire(st, 2),
                               catch=OSError)
    check(len(w_d.raised) == 1 and len(payloads(w_d)) == 1
          and st_d.get("zl_last_grant_plane") == 0,
          "and a send that RAISES does not advance the slot either -- the "
          "write is after the send, so the slot names the last plane that "
          "reached the WIRE",
          f"{st_d.get('zl_last_grant_plane')} after {len(payloads(w_d))} "
          f"payload(s) and {len(w_d.raised)} dead send(s) -- the second grant "
          f"was evaluated, was allowed, and died in sendall, so the copy is "
          f"still bound for the FIRST grant's point and 0 is still the right "
          f"field 4. Hoisting the write above the send passes every other "
          f"check in this section, which is how it survived a mutation lane")

    # ---- TELEMETRY: the wire is scoreable without re-deriving the policy ---
    # REALFIX-F1's own falsifier is "the field-4 mismatch count is not 0", so
    # the value actually SENT has to be in the row. A count nobody records is a
    # count somebody reconstructs later from a policy they assume was running --
    # and REALFIX-Q8 is three movetap pairs that are unattributable for exactly
    # that reason, because the gamesrv jsonl header carries no argv.
    rows_b = r_b.of("grant_verdict")
    # `.get`, NOT `[...]`, AND THE REASON IS THE LEDGER. Dropping the kwarg at
    # the call site is a mutation this check must catch, and with subscripts it
    # "caught" it by raising KeyError out of the check's own arguments -- which
    # aborts the run before LEDGER.verdict() and leaves the remaining section-15
    # checks unexecuted and the floor never evaluated. Red either way, but
    # CLAUDE.md's "a run that measured nothing failed" machinery is bypassed by
    # a traceback. A missing field now reads None and FAILS BY NAME. The one
    # place that still needs presence rather than value is the refused row
    # below, where None is the ANSWER and `.get` would make an absent field
    # indistinguishable from the right one.
    check(len(rows_b) == 2
          and [e.get("plane_dest") for e in rows_b] == [0, 18]
          and [e.get("plane_cur") for e in rows_b] == [0, 0]
          and [e.get("plane_differs") for e in rows_b] == [False, True]
          and all(e.get("plane_carry") is True for e in rows_b),
          "TELEMETRY: every grant row records field 3, the field 4 ACTUALLY "
          "SENT, whether they differ, and which arm produced it",
          f"{[(e.get('plane_dest'), e.get('plane_cur'), e.get('plane_differs')) for e in rows_b]} "
          f"-- `plane_differs` IS the pre-registered mismatch count, so the run "
          f"is scored from the capture rather than from a replay of a policy "
          f"nobody recorded. `plane_carry` names the arm in the row because the "
          f"capture header carries no argv (REALFIX-Q8)")
    rows_off_pc = r_off_pc.of("grant_verdict")
    check(len(rows_off_pc) == 2
          and [e.get("plane_cur") for e in rows_off_pc] == [0, 18]
          and [e.get("plane_differs") for e in rows_off_pc] == [False, False]
          and all(e.get("plane_carry") is False for e in rows_off_pc),
          "and the SAME reports with the flag off record the shipped field 4 "
          "and no mismatch",
          f"{[(e.get('plane_dest'), e.get('plane_cur'), e.get('plane_differs')) for e in rows_off_pc]} "
          f"-- the two arms of the A/B are distinguishable from the rows alone")
    refused_row = refusals_l[0]
    check(all(k in refused_row for k in ("plane_dest", "plane_cur",
                                         "plane_differs"))
          and refused_row["plane_dest"] is None
          and refused_row["plane_cur"] is None
          and refused_row["plane_differs"] is None,
          "and a REFUSED evaluation records None rather than the field 4 it "
          "would have sent",
          f"{refused_row} -- nothing went on the wire, so there is no field 4. "
          f"Writing the counterfactual would put rows in the mismatch census "
          f"for grants that never happened, and that census is the falsifier")
    check(set(e["reason"] for e in rows_b) == {"zero-lead"}
          and set(e["reason"] for e in r_l.of("grant_verdict"))
          == {"zero-lead", "heading-rate"}
          and set(e["reason"] for e in rows_b) <= set(heading_words),
          "and the reason VOCABULARY is unchanged by F1",
          f"{sorted(set(e['reason'] for e in r_l.of('grant_verdict')))} against "
          f"the predicate's own {sorted(heading_words)} -- grantsim's "
          f"HEADING_REASONS keys its replay filter on those two words. A fix "
          f"that added a third reason would silently drop rows from C3's "
          f"denominator")

    # ---- THE COMPOSITION DECISION, driven both ways ----------------------
    pc_alone = authsrv.zero_lead_composition(plane_carry=True)
    check(pc_alone[0] is not None and "--plane-carry requires --zero-lead"
          in pc_alone[0] and "MODIFIER" in pc_alone[0]
          and "--zero-lead --plane-carry" in pc_alone[0],
          "COMPOSITION: --plane-carry ALONE is REFUSED, and the message names "
          "the flag it needs",
          f"{pc_alone[0]!r} -- the choice was refuse-or-document-as-inert and "
          f"this is the refusal. An inert --plane-carry would run a server "
          f"identical to the shipped default while the operator's log said 'F1 "
          f"arm', so the fix would be credited with a null it never earned. "
          f"`--zero-lead --stop-echo` was once accepted SILENTLY, which is the "
          f"precedent")
    check(authsrv.zero_lead_composition(zero_lead=True,
                                        plane_carry=True) == (None, []),
          "and --zero-lead --plane-carry is ALLOWED with nothing to say -- it "
          "is the intended pair",
          "the F1 arm. The banner does the talking for this combination, and a "
          "note here would be printed twice")
    check(authsrv.zero_lead_composition(zero_lead=True) == (None, []),
          "CONTROL: the refusal is ONE-directional -- --zero-lead alone still "
          "runs",
          "--zero-lead alone is REALFIX-P2, the arm F1 is measured AGAINST. A "
          "symmetric refusal would have deleted the control arm")
    pc_clash = authsrv.zero_lead_composition(zero_lead=True, plane_carry=True,
                                             stop_echo=True)[0]
    check(pc_clash is not None and "--stop-echo" in pc_clash
          and "requires --zero-lead" not in pc_clash,
          "and with --zero-lead on, the refuted-arm refusals still win over "
          "the F1 pairing",
          f"{pc_clash!r} -- F1 rides on the zero-lead send site, so a "
          f"combination that makes that site unattributable is refused for the "
          f"same reason with or without it")

    # ---- THE BANNER, pinned for the reason section 14's is ---------------
    # REALFIX-F1's prediction, its named limit and its NPC-grounding caveat are
    # evidence, not decoration: the point of printing them is that they cannot
    # be rationalised after the run. Deleting them has to be a red test, and
    # the reader collects only strings that reach a `print(` -- section 14's
    # first draft passed a banner whose `print(` had been turned into an
    # assignment, the text in the file and no operator ever seeing it.
    pc_arg = next((n for n in ast.walk(main_fn)
                   if isinstance(n, ast.If)
                   and ((isinstance(n.test, ast.Attribute)
                         and n.test.attr == "plane_carry")
                        or (isinstance(n.test, ast.Name)
                            and n.test.id == "plane_carry"))), None)
    pc_banner = printed_text(pc_arg)
    # THE BASELINE COUNTS ARE PINNED TOO, and they were not until 2026-08-21.
    # Every other evidential string here was pinned -- "87% and 39%", the 5%
    # band, the X3 count -- so a banner that read "REALFIX-L3 observed 11 in
    # X3, 3 in X1, 6 in X5" went through a 15-mutation campaign untouched. Those
    # numbers are REALFIX.md sec.6.4.1's SIMULATED "instants planned" for a plan
    # that then yielded 8, printed as an observation of the completed run, and
    # they are the baseline the PRIMARY falsifier ("the field-4 mismatch count
    # is not 0") gets scored against. An unpinned number in a pre-registration
    # is a number that can drift back.
    pc_wanted = ("REALFIX-F1", "PREVIOUS GRANT'S plane",
                 "field 4 differs from the SYNC copy's agent+0x80 go to 0",
                 "BASELINE, from REALFIX-L3 itself: 8 plane-rewriting grants "
                 "ABOVE THE CUT and 2 below",
                 "SIMULATED instants planned and was never observed",
                 "UNCHANGED within 5%", "X3 event count goes to 0", "FAILS IF",
                 "NAMED LIMIT", "more than ONE grant interval behind",
                 "OVERWHELMINGLY NPCs", "87% and 39%",
                 "NECESSARY, NOT SUFFICIENT")
    pc_missing = [wtd for wtd in pc_wanted if wtd not in pc_banner]
    check(pc_arg is not None and not pc_missing,
          "BANNER: the prediction, all three FAILS-IF bounds, the named limit "
          "and the NPC-grounding caveat are printed at startup",
          f"missing={pc_missing} from a banner of {len(pc_banner)} chars -- the "
          f"three bounds are the mismatch count, the 5% separation band and the "
          f"X3 count; the limit is that F1 under-corrects past one grant "
          f"interval; and the caveat is that retail's lead/lag order is "
          f"measured over a population that is overwhelmingly NPCs, with the "
          f"player-identified version UNVERIFIED at 87% vs 39%")
    pc_stripped = ast.parse("def main():\n    if a.plane_carry:\n"
                            "        PLANE_CARRY = True\n")
    pc_unprinted = ast.parse(
        "def main():\n    if a.plane_carry:\n"
        "        _dead = (\"REALFIX-F1 PREVIOUS GRANT'S plane FAILS IF "
        "field 4 differs from the SYNC copy's agent+0x80 go to 0 "
        "BASELINE, from REALFIX-L3 itself: 8 plane-rewriting grants ABOVE THE "
        "CUT and 2 below SIMULATED instants planned and was never observed "
        "UNCHANGED within 5% X3 event count goes to 0 NAMED LIMIT "
        "more than ONE grant interval behind OVERWHELMINGLY NPCs 87% and 39% "
        "NECESSARY, NOT SUFFICIENT\")\n")
    pc_strip_text = printed_text(
        next(n for n in ast.walk(pc_stripped) if isinstance(n, ast.If)))
    pc_unprinted_text = printed_text(
        next(n for n in ast.walk(pc_unprinted) if isinstance(n, ast.If)))
    check([w for w in pc_wanted if w not in pc_strip_text] == list(pc_wanted)
          and [w for w in pc_wanted if w not in pc_unprinted_text]
          == list(pc_wanted),
          "CONTROL: the same reader finds NOTHING in a stripped block, and "
          "nothing in one whose banner is present but never PRINTED",
          f"stripped {len(pc_strip_text)} chars; present-but-unprinted "
          f"{len(pc_unprinted_text)} -- both missing all {len(pc_wanted)}. The "
          f"second control is the mutation that survived section 14's first "
          f"reader, which collected every string constant in the block")
    check(pc_arg is not None and unprintable(pc_arg) == [],
          "and every string the --plane-carry banner prints survives a cp1252 "
          "console",
          f"{None if pc_arg is None else unprintable(pc_arg)} -- a U+26A0 here "
          f"raises UnicodeEncodeError on a default Windows console, so the "
          f"flag would kill the very run it exists to enable. --resync's "
          f"banner already paid this once")

    # ---- THE AST HALF: F1 adds no send site and touches no other arm ------
    pc_blocks = [n for n in ast.walk(src)
                 if isinstance(n, ast.If) and isinstance(n.test, ast.Name)
                 and n.test.id == "PLANE_CARRY"]
    pc_sending = [n for n in pc_blocks
                  if any(isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
                         and c.func.id == "send" for c in ast.walk(n))]

    def pc_names(node):
        return [n for n in ast.walk(node)
                if isinstance(n, ast.Name) and n.id == "PLANE_CARRY"]

    check(len(pc_blocks) == 1 and pc_sending == []
          and pc_names(heading_arm_ast) and not pc_names(stop_arm_ast)
          and not pc_names(click_arm_ast),
          "STRUCTURE: exactly ONE `if PLANE_CARRY:` block, it SENDS nothing, "
          "and PLANE_CARRY is named in the heading arm and NEITHER other arm",
          f"{len(pc_blocks)} blocks of which {len(pc_sending)} send; "
          f"heading={len(pc_names(heading_arm_ast))} "
          f"stop={len(pc_names(stop_arm_ast))} "
          f"click={len(pc_names(click_arm_ast))} -- a modifier that grew a "
          f"send site would be a tenth candidate policy, not F1, and section "
          f"14's 'exactly ONE ZERO_LEAD block SENDS' would still pass. The "
          f"heading count is the positive control")
    pc_payload_field4 = payload[3] if len(payload) > 3 else None
    check(isinstance(pc_payload_field4, ast.Name)
          and pc_payload_field4.id == "lead_f4"
          and isinstance(payload[2], ast.Name) and payload[2].id == "lead_f3"
          and "lead_f3, lead_f4 = plane, zl_plane_cur" in open(authsrv.__file__, encoding="utf-8").read(),
          "and the zero-lead send's field 3 is the node `lead_f3` (initialised "
          "from `plane`, the destination's) while field 4 is `lead_f4` "
          "(initialised from the carried value) -- MOVECODE-1z-cl moved both "
          "behind the mesh's answer at the two points",
          f"field3={ast.dump(payload[2]) if len(payload) > 2 else None} "
          f"field4={ast.dump(pc_payload_field4) if pc_payload_field4 else None}"
          f" -- field 3 is the DESTINATION's plane and the destination is the "
          f"newest report, so it must not follow field 4 into the past")

    print("\n16. --arrival-carry (REALFIX-F1b) carries the ARRIVED grant's plane")
    # WHAT EARNS THIS SECTION: F1's OWN PRIMARY FALSIFIER FIRED. Its
    # pre-registration -- printed at startup and pinned by section 15 -- was
    # "grants whose field 4 differs from the SYNC copy's agent+0x80 go to 0".
    # Run 20260821T143411 came in at 5 of 93 against the P2 control's 8 of 88,
    # and all five sit above the gate-1 cut, which is the exact combination that
    # produced 3 of 8 events in the control. Every one is F1's own NAMED LIMIT:
    # a TWO-interval lag, where the client had been on plane 18 for two grants
    # while the copy was still on 0, so "the previous grant" was already 18.
    #
    # SO F1b CHANGES THE OPERAND, not the field. Field 4 becomes the plane of
    # the grant the copy has ARRIVED at, computed with the client's own bake
    # (0x005FE950) over the SYNC model the server already keeps. Three
    # functions, split PURE / PURE / MUTATING so the offline scorer runs the
    # shipped decision rather than a paraphrase of it.
    #
    # THE CASE THIS SECTION EXISTS FOR is the in-flight supersede. A grant that
    # lands while a leg is still in flight re-aims the copy mid-leg: it never
    # reaches the superseded destination, so that plane must never become "the
    # plane the copy arrived at", and the copy's position at that instant is a
    # dead reckon along the old leg rather than the old destination. Get that
    # wrong and F1b invents a NEW way to stamp a plane the copy was never on.
    check(authsrv.ARRIVAL_CARRY is False,
          "--arrival-carry is off by default",
          "REALFIX-F1b is a candidate fix whose own offline pre-screen says it "
          "leaves 3 residual mismatches, not 0. It is unproven until an F1b arm "
          "scores it against the F1 and P2 arms REALFIX-L3 measured")

    S = authsrv.DEFAULT_RUN_SPEED

    def ac_state(pos=(0.0, 0.0), at=1000.0):
        """A SEEDED sync model parked at `pos`, which is what a placed character
        leaves behind: sync_from set, sync_to None, so _sync_position returns
        `pos` exactly and the first leg's distance is a real measurement."""
        return {"sync_from": (float(pos[0]), float(pos[1])), "sync_to": None,
                "sync_at": at, "ac_queue": [], "ac_arrived": None}

    # ---- the arrival formula IS the client's bake ------------------------
    st = ac_state()
    arr, dist = authsrv.arrival_carry_leg(st, 1000.0, (S, 0.0))
    check(abs(dist - S) < 1e-9 and abs(arr - 1001.0) < 1e-9,
          f"a leg of exactly {S:.0f} u arrives exactly 1.000 s later",
          f"dist={dist} arrival=+{arr - 1000.0:.6f}s -- [+0x48] = now + "
          f"trunc(|d| * 1000 / S) with S = [+0x60] * [+0x5C] = moveSpeed * "
          f"maxSpeed. Neither term is fitted: we send moveSpeed 1.0 in 621 of "
          f"621 sends and the client holds 288.0/1.0 in 4,115 of 4,115 movetap "
          f"samples")
    # THE TRUNCATION IS A FLOOR TO WHOLE MILLISECONDS AND IT IS THE CLIENT'S.
    # 100.4 u at 288 u/s is 348.611 ms and the tick is 348, not 349.
    st = ac_state()
    arr_t, _d = authsrv.arrival_carry_leg(st, 0.0, (100.4, 0.0))
    check(abs(arr_t - 0.348) < 1e-9,
          "and the millisecond tick TRUNCATES rather than rounds",
          f"{arr_t * 1000:.6f} ms for 100.4 u, against 348.611 exact -- "
          f"rounding would give 349 and put every arrival up to half a "
          f"millisecond late. The client floors")
    # THE ZERO-DISTANCE SHORT-CIRCUIT, and it is measured from the COPY.
    st = ac_state()
    arr_z, dz = authsrv.arrival_carry_leg(st, 5.0, (1.0, 0.0))
    st_far = ac_state()
    arr_f, _df = authsrv.arrival_carry_leg(st_far, 5.0, (1.001, 0.0))
    check(abs(arr_z - 5.001) < 1e-9 and dz == 1.0 and arr_f > 5.001,
          "|d|^2 <= 1.0 takes the short-circuit and arrives in 1 ms; a hair "
          "further does not",
          f"1.000 u -> +{(arr_z - 5.0) * 1000:.3f} ms, 1.001 u -> "
          f"+{(arr_f - 5.0) * 1000:.3f} ms. 0x005FEA92 writes +0x78..+0x84 = D "
          f"outright and sets the tick to now+1; the compare is against the "
          f"SYNC COPY's +0x78 and NOT the client's, which is REALFIX-P2's "
          f"retracted cheapness claim")
    # THE `max(1, ...)` CLAMP IS UNREACHABLE HERE, AND SAYING SO IS THE CHECK.
    # A tick of 0 would mean "no destination armed", so the client floors it at
    # 1 -- but with the short-circuit taking everything at or under 1.0 u, the
    # shortest leg that can reach the else branch is 1.0+eps u, which is 3.47 ms
    # and truncates to 3. The clamp is defensive and this is the assertion that
    # it is: scan the whole reachable domain and find the smallest tick.
    ticks = set()
    for milli in range(1001, 3001):
        stx = ac_state()
        ax, _dx = authsrv.arrival_carry_leg(stx, 0.0, (milli / 1000.0, 0.0))
        ticks.add(round(ax * 1000.0))
    check(min(ticks) == 3,
          "the millisecond clamp is DEFENSIVE and unreachable: the shortest "
          "non-short-circuit leg already ticks 3 ms",
          f"smallest tick over every leg in (1.000, 3.000] u is {min(ticks)} "
          f"ms -- at {S:.0f} u/s a 1 u leg is {1000.0 / S:.2f} ms, and anything "
          f"shorter takes the |d|^2 <= 1.0 arm instead. `max(1, ...)` is kept "
          f"because a 0 tick would mean 'no destination armed', not because any "
          f"input reaches it")
    check(authsrv.arrival_carry_leg({"sync_from": None}, 0.0, (1.0, 1.0))
          == (None, None),
          "an UNSEEDED sync model answers (None, None) rather than inventing a "
          "start point",
          "_sync_position returns None until the character is placed and every "
          "consumer fails closed on it. An arrival built on a position nobody "
          "measured would carry a plane nobody measured")

    # ---- the queue: the four cases the spec names ------------------------
    # (1) THE FIRST GRANT. Empty queue, so the documented default is the
    # CURRENT plane -- exactly today's payload and exactly F1's default. A 0
    # here would write a wrong map index into agent+0x80.
    st = ac_state()
    f4_first, why_first = authsrv.arrival_carry_field4(st, 1000.0, 7)
    check(f4_first == 7 and why_first == "first-grant",
          "(1) FIRST GRANT: with nothing granted yet, field 4 is the CURRENT "
          "plane",
          f"{f4_first} why={why_first!r} -- at the first grant of a session the "
          f"copy is co-located with the player at the spawn point, so there is "
          f"no lagged copy to be wrong about")

    # (2) A GRANT THAT ARRIVES BEFORE THE NEXT ONE. The ordinary case, and the
    # one F1 already got right.
    st = ac_state()
    a1, _d1 = authsrv.arrival_carry_leg(st, 1000.0, (S, 0.0))       # arrives 1001
    authsrv._note_wire_move(st, authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT,
                            [authsrv.PLAYER_AGENT_ID, [S, 0.0]], 1000.0)
    authsrv.arrival_carry_advance(st, 1000.0, a1, 0, (S, 0.0))
    f4_mid, why_mid = authsrv.arrival_carry_field4(st, 1000.5, 18)
    f4_late, why_late = authsrv.arrival_carry_field4(st, 1002.0, 18)
    check(f4_mid == 18 and why_mid == "in-flight"
          and f4_late == 0 and why_late == "arrived",
          "(2) mid-leg the queue has NOTHING arrived and falls back to the "
          "current plane; past the arrival it carries the granted one",
          f"t+0.5 -> {f4_mid} ({why_mid}), t+2.0 -> {f4_late} ({why_late}) over "
          f"a leg that arrives at t+1.000")

    # (3) THE IN-FLIGHT SUPERSEDE, AND IT IS THE WHOLE DIFFERENCE FROM F1.
    # Grant A at t=1000 to (576,0), arriving t+2.0. Grant B at t=1001, halfway
    # along. The copy is at (288,0) -- NOT at A's destination -- so B's leg is
    # measured from there; and A must be DISCARDED, because the copy re-aimed
    # and will never stand on A's plane.
    # B is (288, 288). From the DEAD-RECKONED copy at (288, 0) that is exactly
    # 288 u = 1.000 s; from A's abandoned destination (576, 0) it would be
    # hypot(288, 288) = 407.29 u = 1.414 s. The two readings are distinguishable
    # to three decimal places, so "which point did the leg start from" is
    # answered by the number rather than asserted.
    B = (S, S)
    st = ac_state()
    aA, _dA = authsrv.arrival_carry_leg(st, 1000.0, (2 * S, 0.0))
    authsrv._note_wire_move(st, authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT,
                            [authsrv.PLAYER_AGENT_ID, [2 * S, 0.0]], 1000.0)
    authsrv.arrival_carry_advance(st, 1000.0, aA, 21, (2 * S, 0.0))
    f4_sup, why_sup = authsrv.arrival_carry_field4(st, 1001.0, 5)
    aB, dB = authsrv.arrival_carry_leg(st, 1001.0, B)
    from_abandoned = math.hypot(B[0] - 2 * S, B[1])
    check(abs(aA - 1002.0) < 1e-9 and f4_sup == 5 and why_sup == "in-flight"
          and abs(dB - S) < 1e-6,
          "(3) IN-FLIGHT SUPERSEDE: the superseded grant's plane is NOT "
          "carried, and the new leg is measured from the DEAD-RECKONED point, "
          "not from the abandoned destination",
          f"A armed t+0.0 arriving t+{aA - 1000.0:.3f}; at t+1.0 field 4 = "
          f"{f4_sup} ({why_sup}), NOT A's 21; B's leg measures {dB:.3f} u from "
          f"the dead-reckoned ({S:.0f},0) against {from_abandoned:.3f} u it "
          f"would measure from A's abandoned ({2 * S:.0f},0). Carrying 21 here "
          f"would stamp a plane the copy never stood on -- a NEW way to write a "
          f"wrong plane, invented by the fix meant to stop writing wrong planes")
    authsrv.arrival_carry_advance(st, 1001.0, aB, 5, B)
    check(len(st["ac_queue"]) == 1 and st["ac_queue"][0][1] == 5
          and st["ac_arrived"] is None,
          "and after the supersede the queue holds ONLY the new leg, with A "
          "gone rather than deferred",
          f"queue={st['ac_queue']} arrived={st['ac_arrived']} -- left in place, "
          f"A's arrival time would quietly come due and hand the NEXT grant "
          f"plane 21. `ac_arrived` stays None because nothing has ever arrived")
    # THE NEGATIVE CONTROL for (3): the same two grants with B late enough that
    # A really did arrive. Same code path, opposite answer, and the leg length
    # says so independently of the plane.
    st2 = ac_state()
    aA2, _x = authsrv.arrival_carry_leg(st2, 1000.0, (2 * S, 0.0))
    authsrv._note_wire_move(st2, authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT,
                            [authsrv.PLAYER_AGENT_ID, [2 * S, 0.0]], 1000.0)
    authsrv.arrival_carry_advance(st2, 1000.0, aA2, 21, (2 * S, 0.0))
    f4_ok, why_ok = authsrv.arrival_carry_field4(st2, 1003.0, 5)
    _aB2, dB2 = authsrv.arrival_carry_leg(st2, 1003.0, B)
    # THE DIFFERENCE IS READ OFF THE TWO MEASURED LEGS, not recomputed from the
    # fixture. It said `from_abandoned - S` -- a constant that never touches
    # `dB` -- so a mutation collapsing the in-flight leg onto the abandoned
    # destination left this control printing "differ by 119.3 u" while both
    # legs actually read 407.294. Check (3) catches that mutation on its own,
    # so the hole was in the narration; an evidence string that cannot
    # contradict the run is still the shape this repo books as a defect, and
    # the separation is now asserted rather than described.
    check(f4_ok == 21 and why_ok == "arrived"
          and abs(dB2 - from_abandoned) < 1e-6 and abs(dB2 - dB) > 1e-6,
          "CONTROL: with the same pair one second later A HAS arrived, so 21 "
          "IS carried and the leg starts from A's destination",
          f"{f4_ok} ({why_ok}), leg {dB2:.3f} u against the in-flight case's "
          f"{dB:.3f} -- the discard is a discard of what is IN FLIGHT, not of "
          f"everything, and the two legs differ by "
          f"{dB2 - dB:.1f} u so the start point is measured")

    # (4) A RATE-LIMIT REFUSAL CHANGES NOTHING, and that is enforced by the read
    # being PURE rather than by the caller remembering to skip it.
    st3 = ac_state()
    a3, _y = authsrv.arrival_carry_leg(st3, 1000.0, (2 * S, 0.0))
    authsrv._note_wire_move(st3, authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT,
                            [authsrv.PLAYER_AGENT_ID, [2 * S, 0.0]], 1000.0)
    authsrv.arrival_carry_advance(st3, 1000.0, a3, 21, (2 * S, 0.0))
    before = (list(st3["ac_queue"]), st3["ac_arrived"])
    for probe in (1000.5, 1001.0, 1003.0, 1009.0):
        authsrv.arrival_carry_field4(st3, probe, 99)
        authsrv.arrival_carry_leg(st3, probe, (99.0, 99.0))
    check((list(st3["ac_queue"]), st3["ac_arrived"]) == before,
          "(4) RATE-LIMIT REFUSAL: reading field 4 and the leg mutates NOTHING, "
          "at four instants including two past the arrival",
          f"{before} unchanged. A refused report puts no grant on the wire, so "
          f"the copy is still bound for the point the last GRANT named -- if a "
          f"refusal could consume the queue or drop the in-flight leg, F1b "
          f"would mis-answer exactly the stall case that is F1's named limit")

    # (5) A STOP. Under --zero-lead the stop arm sends no 0x0029 at all
    # (--stop-echo is REFUTED and now refused by zero_lead_composition), so the
    # queue must survive one untouched: the copy keeps gliding to the granted
    # point and arrives on schedule whatever the player did.
    st4 = ac_state()
    a4, _z = authsrv.arrival_carry_leg(st4, 1000.0, (2 * S, 0.0))
    authsrv._note_wire_move(st4, authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT,
                            [authsrv.PLAYER_AGENT_ID, [2 * S, 0.0]], 1000.0)
    authsrv.arrival_carry_advance(st4, 1000.0, a4, 21, (2 * S, 0.0))
    _st_stop, w_stop, _r_stop = drive_pc([], carry=False)
    stop_state = dict(st4)
    authsrv._note_wire_move(stop_state, authsrv.GAME_CMSG_MOVE_TO_COORD,
                            [authsrv.PLAYER_AGENT_ID, [0.0, 0.0]], 1000.5)
    check(stop_state["ac_queue"] == st4["ac_queue"]
          and authsrv.arrival_carry_field4(st4, 1003.0, 5)[0] == 21,
          "(5) A STOP leaves the queue alone and the copy still arrives",
          f"queue {st4['ac_queue']} -- the stop arm sends no grant under "
          f"--zero-lead, and the authoritative copy is chasing OUR point rather "
          f"than the player's keys, so it parks on it whatever the player did")

    # (6) A HARD SET (0x002C) KILLS THE LEG, and the binary says it must:
    # 0x00602B20's armed arm hands off to 0x006020B0, which CLEARS the arrival
    # tick at 0x006021E6. --resync is ALLOWED beside --arrival-carry, so this
    # is wired rather than assumed.
    st5 = ac_state()
    a5, _q = authsrv.arrival_carry_leg(st5, 1000.0, (2 * S, 0.0))
    authsrv._note_wire_move(st5, authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT,
                            [authsrv.PLAYER_AGENT_ID, [2 * S, 0.0]], 1000.0)
    authsrv.arrival_carry_advance(st5, 1000.0, a5, 21, (2 * S, 0.0))
    authsrv._note_wire_move(st5, authsrv.GAME_SMSG_AGENT_UPDATE_POSITION,
                            [authsrv.PLAYER_AGENT_ID, [10.0, 10.0], 18], 1000.5)
    check(st5["ac_queue"] == [] and st5["ac_arrived"] == 18
          and authsrv.arrival_carry_field4(st5, 1009.0, 5) == (18, "arrived"),
          "(6) a 0x002C HARD SET drops the in-flight leg and takes its OWN "
          "plane as the reached one",
          f"queue={st5['ac_queue']} arrived={st5['ac_arrived']} -- the teleport "
          f"primitive zeroes +0x48, so the outstanding grant never arrives. An "
          f"entry left here would come due at t+2.0 on a leg the client had "
          f"already abandoned, which is the stale-arrival defect the supersede "
          f"discard exists to prevent, arriving by a different door")

    # ---- payload exactness, and the flag-OFF byte identity ---------------
    # F1b must move field 4 and NOTHING else. `drive_pc` sets ZERO_LEAD and
    # PLANE_CARRY; ARRIVAL_CARRY needs the same treatment, so it gets its own
    # driver rather than a widened one -- section 15's checks read `drive_pc`
    # and must keep meaning what they meant.
    class FakeClock:
        """`time`, with `time()` under the test's control and nothing else moved.

        SECTION 15 DID NOT NEED THIS AND SECTION 16 DOES, which is itself the
        finding: F1's carry is a pure lookup with no clock in it, while F1b's
        turns on `arrival <= now`. Driven on the real clock the arm's own
        `now_z = time.time()` advances by whatever the loop happened to take --
        and a 0.559 u first leg arrives 1 ms later, so two reports issued inside
        that millisecond score "in flight" and the payload flips. That is a real
        property of the policy (it is exactly the sub-frame race the offline
        pre-screen measured) and it must be DRIVEN rather than raced: a test
        whose expected payload depends on how fast the machine is proves
        nothing on either outcome.

        Everything except `time()` delegates to the real module, so a `sleep`
        or a `monotonic` anywhere under `arm` still behaves.
        """

        def __init__(self, start=1_000_000.0):
            self.t = start

        def time(self):
            return self.t

        def __getattr__(self, name):
            return getattr(time, name)

    def drive_ac(steps, carry, zero_lead=True, step_dt=1.0):
        st_ = {"pos": (1000.0, 2000.0), "plane": 7, "pos_seen": 0.0,
               "sync_from": (1000.0, 2000.0), "sync_to": None,
               "sync_at": 0.0}
        clock = FakeClock()
        w_, r_ = Sent(st_), FakeRec()
        was_zl, was_pc = authsrv.ZERO_LEAD, authsrv.PLANE_CARRY
        was_ac, was_time = authsrv.ARRIVAL_CARRY, authsrv.time
        was_ks = authsrv.KBD_SYNC
        authsrv.ZERO_LEAD, authsrv.PLANE_CARRY = zero_lead, False
        authsrv.ARRIVAL_CARRY = carry
        authsrv.KBD_SYNC = False        # one variable -- see the note above
        authsrv.time = clock
        try:
            for values, may in steps:
                st_["grant_at"] = clock.t - (10.0 if may else 0.0)
                w_.now = clock.t
                arm(values, st_, r_, w_, 0)
                clock.t += step_dt
        finally:
            authsrv.ZERO_LEAD, authsrv.PLANE_CARRY = was_zl, was_pc
            authsrv.ARRIVAL_CARRY = was_ac
            authsrv.KBD_SYNC = was_ks
            authsrv.time = was_time
        return st_, w_, r_

    # THE STEP IS 2.0 s SO EVERY LEG LANDS. Reports are 400 u apart, which is
    # 1.389 s of travel, so a 1.0 s step would leave every grant superseding a
    # leg still in flight -- a real regime, driven three checks below, but the
    # wrong one to read "does the carry work at all" out of.
    ac_steps = [(pc_report(1000.5, 7), True), (pc_report(1400.0, 18), True),
                (pc_report(1800.0, 18), True)]
    _s_on, w_on, r_on = drive_ac(ac_steps, carry=True, step_dt=2.0)
    _s_off, w_off, r_off = drive_ac(ac_steps, carry=False, step_dt=2.0)
    on_pay, off_pay = payloads(w_on), payloads(w_off)
    check(len(on_pay) == 3 and len(off_pay) == 3
          and [p[:3] for p in on_pay] == [p[:3] for p in off_pay],
          "PAYLOAD: with the flag ON, agent id, point and field 3 are "
          "byte-identical to the flag-OFF run",
          f"on={[p[:3] for p in on_pay]} off={[p[:3] for p in off_pay]} -- "
          f"'F1b touches no position' is half of the pre-registered prediction "
          f"(separation p50/p90 unchanged within 5%), and this is the check "
          f"that makes it a fact about the code rather than a hope")
    check([p[3] for p in off_pay] == [7, 18, 18],
          "CONTROL: with the flag OFF the payload is the pre-F1b build exactly "
          "-- field 4 = field 3 on every grant",
          f"{[p[3] for p in off_pay]} -- that is what makes F1b a MODIFIER on "
          f"this arm rather than a second policy inside it, and it is the "
          f"property `--arrival-carry` alone would silently have while the run "
          f"log said 'F1b arm'")
    check([p[3] for p in on_pay] == [7, 7, 18],
          "and with it ON the carry LAGS field 3 by exactly one arrived grant",
          f"{[p[3] for p in on_pay]} against field 3 {[p[2] for p in on_pay]} "
          f"-- grant 1 defaults to the current plane, grant 2 finds grant 1 "
          f"arrived (0.559 u away, so the short-circuit put the copy there in "
          f"1 ms) and carries its 7, grant 3 finds grant 2's 399.5 u leg "
          f"arrived 1.389 s in and carries its 18")
    # THE SUPERSEDE REGIME THROUGH THE REAL SEND PATH, and it is where F1b and
    # F1 give DIFFERENT payloads. At a 1.0 s cadence a 399.5 u leg (1.389 s)
    # never lands, so grant 3 supersedes grant 2 in flight: F1b holds 7, the
    # plane the copy actually reached, while F1 would carry grant 2's 18 -- the
    # value the copy is still 0.4 s short of. That difference is exactly the
    # two-interval lag F1's five residuals sit in.
    _s_fast, w_fast, r_fast = drive_ac(ac_steps, carry=True, step_dt=1.0)
    _s_f1, w_f1, _r_f1 = drive_pc(ac_steps, carry=True)
    fast_pay = payloads(w_fast)
    check([p[3] for p in fast_pay] == [7, 7, 7]
          and [e.get("carry_why") for e in r_fast.of("grant_verdict")]
          == ["first-grant", "arrived", "superseding"],
          "SUPERSEDE THROUGH THE SEND PATH: at a cadence where no leg lands, "
          "F1b holds the plane the copy REACHED and does not follow the client",
          f"{[p[3] for p in fast_pay]} against field 3 "
          f"{[p[2] for p in fast_pay]} -- grant 3 arrives 1.0 s into grant 2's "
          f"1.389 s leg, so grant 2's 18 is DISCARDED unreached. F1 on the same "
          f"three reports sends {[p[3] for p in payloads(w_f1)]}, carrying an "
          f"18 the copy is still 0.4 s short of: that is the two-interval lag "
          f"its five residuals sit in, reproduced here from the shipped arm")
    ac_rows = r_on.of("grant_verdict")
    check(len(ac_rows) == 3
          and all(e.get("carry") == "arrival-carry" for e in ac_rows)
          and [e.get("carry_why") for e in ac_rows]
          == ["first-grant", "arrived", "arrived"]
          and all(e.get("arrival_in") is not None for e in ac_rows),
          "TELEMETRY: every verdict row NAMES the arm and carries the queue's "
          "own reason and the arrival it just armed",
          f"carry={[e.get('carry') for e in ac_rows]} "
          f"why={[e.get('carry_why') for e in ac_rows]} "
          f"arrival_in={[e.get('arrival_in') for e in ac_rows]} -- "
          f"`plane_carry: false` reads identically for the P2 control and for "
          f"an F1b run, and the gamesrv jsonl header carries NO argv "
          f"(REALFIX-Q8), so a capture that cannot say which arm produced it "
          f"costs a later session a behavioural reconstruction")
    off_rows = r_off.of("grant_verdict")
    check(len(off_rows) == 3 and all(e.get("carry") == "off" for e in off_rows)
          and all(e.get("carry_why") is None for e in off_rows)
          and all(e.get("arrival_in") is None for e in off_rows),
          "CONTROL: the flag-OFF run says so in the same field, and arms no "
          "arrival",
          f"carry={[e.get('carry') for e in off_rows]} "
          f"arrival_in={[e.get('arrival_in') for e in off_rows]} -- the two "
          f"arms of the A/B are distinguishable from the rows alone")

    # THE SLOT TRACKS SENDS. A refused report must not advance the queue, and
    # the observable is the NEXT payload: with the middle report refused, the
    # third grant still carries what the copy reached.
    ac_refused = [(pc_report(1000.5, 7), True), (pc_report(1400.0, 18), False),
                  (pc_report(1800.0, 18), True)]
    _s_r, w_r, _r_r = drive_ac(ac_refused, carry=True)
    ref_pay = payloads(w_r)
    check(len(ref_pay) == 2 and [p[3] for p in ref_pay] == [7, 7],
          "REFUSAL: a rate-refused report arms no entry, so the next grant "
          "still carries the last one that actually WENT OUT",
          f"{[p[3] for p in ref_pay]} from {len(ref_pay)} grants -- the middle "
          f"report was refused, so the copy is still bound for grant 1's point "
          f"and 7 is still the plane it reached. This is precisely F1's NAMED "
          f"LIMIT case (4 of 70 headings refused in REALFIX-L1's arm B), and "
          f"it is the one F1b has to answer differently")

    # A SEND THAT RAISES MUST NOT ADVANCE THE QUEUE -- the same ordering
    # section 15 pins for `zl_last_grant_plane`, and the only observable
    # difference between mutating before the send and after it.
    ac_dead_state = {"pos": (1000.0, 2000.0), "plane": 7, "pos_seen": 0.0,
                     "sync_from": (1000.0, 2000.0), "sync_to": None,
                     "sync_at": 0.0, "ac_queue": [], "ac_arrived": None}
    dead = PcDeadWire(ac_dead_state, die_on=1)
    was = (authsrv.ZERO_LEAD, authsrv.PLANE_CARRY, authsrv.ARRIVAL_CARRY)
    was_ks = authsrv.KBD_SYNC
    authsrv.ZERO_LEAD, authsrv.PLANE_CARRY = True, False
    authsrv.ARRIVAL_CARRY = True
    authsrv.KBD_SYNC = False            # one variable -- see the note above
    try:
        now = time.time()
        ac_dead_state["grant_at"] = now - 10.0
        dead.now = now - 10.0
        try:
            arm(pc_report(1000.5, 7), ac_dead_state, FakeRec(), dead, 0)
        except OSError:
            pass
    finally:
        authsrv.ZERO_LEAD, authsrv.PLANE_CARRY, authsrv.ARRIVAL_CARRY = was
        authsrv.KBD_SYNC = was_ks
    check(ac_dead_state["ac_queue"] == [] and ac_dead_state["ac_arrived"] is None,
          "and a send that RAISES leaves the queue exactly as the last grant "
          "that really went out left it",
          f"queue={ac_dead_state['ac_queue']} "
          f"arrived={ac_dead_state['ac_arrived']} -- sendall can raise, and "
          f"_note_wire_move runs BEFORE the bytes go out while this queue "
          f"advances after them. Arming an entry for a grant no client ever "
          f"received would carry its plane forward on the strength of a "
          f"destination the copy was never sent to")

    # ---- composition: the matrix, both directions ------------------------
    # EVERY REFUSAL BELOW IS SLICED THROUGH `_shown`, AND THAT IS NOT STYLE.
    # These read `zero_lead_composition(...)[0]`, which is None when the
    # composition is ALLOWED -- i.e. exactly when the refusal has been deleted
    # and the check must fail. Python builds the evidence f-string BEFORE
    # `check()` runs, so a bare `ac_alone[:60]` raises TypeError on None: the
    # mutation is still caught by the exit code, but section 16 dies mid-run,
    # its remaining checks never execute and the ledger's floor is never
    # evaluated -- a red run that names nothing and declares no skip, which is
    # the failure both `checks.py` and CLAUDE.md's "a red test names the broken
    # thing" exist to prevent. Two mutations of the F1b lane landed exactly
    # here.
    def _shown(refusal, n):
        return (refusal or "<ALLOWED -- no refusal returned>")[:n]

    ac_alone = authsrv.zero_lead_composition(arrival_carry=True)[0]
    ac_both = authsrv.zero_lead_composition(zero_lead=True, plane_carry=True,
                                            arrival_carry=True)[0]
    ac_ok = authsrv.zero_lead_composition(zero_lead=True, arrival_carry=True)
    check(ac_alone and "--arrival-carry requires --zero-lead" in ac_alone
          and ac_ok == (None, []),
          "COMPOSITION: --arrival-carry alone is REFUSED; with --zero-lead it "
          "runs clean",
          f"alone -> {_shown(ac_alone, 60)!r}...; with --zero-lead -> {ac_ok} -- an "
          f"inert flag would run a server identical to the shipped default "
          f"while the operator's log said 'F1b arm', and the null would be "
          f"published against F1b's prediction. Same refusal --plane-carry "
          f"already carries, for the same reason")
    check(ac_both and "TWO POLICIES FOR ONE WIRE FIELD" in ac_both,
          "and --plane-carry WITH --arrival-carry is refused as two policies "
          "for one field",
          f"{_shown(ac_both, 90)!r}... -- whichever the send site read, the other "
          f"would be inert, and both print their OWN pre-registered prediction "
          f"at startup, so a server carrying both announces two predictions "
          f"and can honestly satisfy neither")
    ac_triple = authsrv.zero_lead_composition(plane_carry=True,
                                              arrival_carry=True)[0]
    check(ac_triple and "TWO POLICIES FOR ONE WIRE FIELD" in ac_triple,
          "CONTROL: with --zero-lead ALSO missing, the two-policies refusal "
          "still wins over the needs-zero-lead one",
          f"{_shown(ac_triple, 60)!r}... -- 'you passed two field-4 policies' is the "
          f"more useful thing to be told when someone passes all three, and "
          f"the ordering of the two checks is what decides which fires")
    ac_clash = authsrv.zero_lead_composition(zero_lead=True, arrival_carry=True,
                                             stop_echo=True)[0]
    check(ac_clash and "--stop-echo" in ac_clash
          and "TWO POLICIES" not in ac_clash,
          "and with --zero-lead on, the refuted-arm refusals still win over "
          "the F1b pairing",
          f"{_shown(ac_clash, 70)!r}... -- F1b rides on the zero-lead send site, so a "
          f"combination that makes that site unattributable is refused for the "
          f"same reason with or without it")
    _ref, ac_notes = authsrv.zero_lead_composition(zero_lead=True,
                                                   arrival_carry=True,
                                                   resync=True)
    check(any("INVALIDATES the arrival queue" in n for n in ac_notes),
          "and --resync ALLOWED beside it says out loud that it invalidates "
          "the queue",
          f"{len(ac_notes)} note(s) -- 0x002C clears the arrival tick, so the "
          f"outstanding grant never arrives; the interaction is wired in "
          f"_note_wire_move and printed here rather than left to be discovered "
          f"in a run")

    # ---- the banner: the SCREENED prediction, not the drafted one --------
    ac_arg = next((n for n in ast.walk(main_fn)
                   if isinstance(n, ast.If)
                   and isinstance(n.test, ast.Attribute)
                   and n.test.attr == "arrival_carry"), None)
    ac_banner = printed_text(ac_arg)
    # THE OFFLINE PRE-SCREEN CHANGED THIS PREDICTION AND THE BANNER HAS TO SAY
    # SO. F1b was drafted predicting the mismatch count reaches 0 -- the
    # falsifier F1 failed. Replaying it offline against both L3 captures says
    # 3, not 0. Printing the drafted 0 would be the exact defect section 15
    # already booked once, a number that cannot be met inside the one artifact
    # whose job is that the baseline cannot be rationalised after the run.
    ac_wanted = ("REALFIX-F1b", "ARRIVED",
                 "F1b DOES NOT REACH ZERO",
                 "come in at ~3", "NOT at 0",
                 "sub-frame RACE", "guard band", "REFUSED",
                 "corrected they are 10 and 6",
                 "UNCHANGED within 5%", "FAILS IF",
                 "F1's ZERO WAS NOT SIGNIFICANT", "p = 0.196",
                 "OVERWHELMINGLY NPCs", "87% and 39%",
                 "NECESSARY, NOT SUFFICIENT", "grantsim.py --planecarry")
    ac_missing = [w for w in ac_wanted if w not in ac_banner]
    check(ac_arg is not None and not ac_missing,
          "BANNER: it prints the OFFLINE-SCREENED prediction (~3, not 0), the "
          "refused guard band, the corrected baselines and F1's own "
          "insignificance",
          f"missing={ac_missing} from a banner of {len(ac_banner)} chars -- "
          f"F1b was DRAFTED predicting 0, its own pre-screen says 3, and a "
          f"banner still claiming 0 would pre-register a number the author "
          f"already knew could not be met")
    # AND THE NUMBERS THOSE SEVENTEEN SUBSTRINGS SUMMARISE. The prose above was
    # pinned and the TABLE under it was not, which a mutation lane proved twice
    # on 2026-08-21: deleting the three counterfactual rows outright left this
    # file green at 215/215, and rewriting the F1b row to "0 of 69" -- the
    # drafted prediction the offline screen had already refuted, printed beside
    # prose still reading "F1b DOES NOT REACH ZERO" and "come in at ~3" -- left
    # it green too. A banner that can contradict itself in its own numeric half
    # is section 15's defect exactly ("REALFIX-L3 observed": a prediction
    # printed as an observation inside the artifact whose whole job is that the
    # baseline cannot be rationalised after the run), one section later.
    #
    # THE ROWS ARE REBUILT FROM `grantsim.FIELD4_SCREEN`, not restated here, so
    # the tie is to the scorer rather than to a second literal that could drift
    # with the first. `authsrv` may not import grantsim (see the import block),
    # so the banner holds literals and this is what binds them; the constant is
    # in turn pinned cell-by-cell against the live computation by
    # `test_grantsim.py` §10, which is the half that makes this one mean
    # something. Whitespace is collapsed because the banner column-aligns
    # ("0 of  8") and the alignment is not the claim.
    ac_flat = " ".join(ac_banner.split())
    ac_rows = {"shipped-zerolead": "shipped --zero-lead",
               "F1-planecarry": "F1 --plane-carry",
               "F1b-arrivalcarry": "F1b --arrival-carry"}
    ac_want_rows, ac_bad_rows = [], []
    for _pol, _label in ac_rows.items():
        _cells = grantsim.FIELD4_SCREEN[_pol]
        _row = _label + " " + " | ".join(
            f"{_cells[s][0]} of {_cells[s][1]}"
            for s, _t, _a in grantsim.FIELD4_PAIRS)
        ac_want_rows.append(_row)
        if _row not in ac_flat:
            ac_bad_rows.append(_row)
    check(ac_arg is not None and not ac_bad_rows and len(ac_want_rows) == 3,
          "and the THREE COUNTERFACTUAL ROWS it prints as the evidence for that "
          "prediction are the offline scorer's own cells, numerator and "
          "denominator",
          f"missing={ac_bad_rows} of {ac_want_rows} -- the F1b row is the sharp "
          f"one: 3 of 69 is the screened result and 0 of 69 is the DRAFTED "
          f"prediction it refuted, and a banner free to print either could "
          f"pre-register the number it already knew it would miss")
    ac_strip = ast.parse("def main():\n    if a.arrival_carry:\n"
                         "        ARRIVAL_CARRY = True\n")
    ac_unprinted = ast.parse(
        "def main():\n    if a.arrival_carry:\n"
        "        _dead = (\"REALFIX-F1b ARRIVED F1b DOES NOT REACH ZERO "
        "come in at ~3 NOT at 0 sub-frame RACE guard band REFUSED "
        "corrected they are 10 and 6 UNCHANGED within 5% FAILS IF "
        "F1's ZERO WAS NOT SIGNIFICANT p = 0.196 OVERWHELMINGLY NPCs "
        "87% and 39% NECESSARY, NOT SUFFICIENT grantsim.py --planecarry\")\n")
    ac_strip_text = printed_text(
        next(n for n in ast.walk(ac_strip) if isinstance(n, ast.If)))
    ac_unp_text = printed_text(
        next(n for n in ast.walk(ac_unprinted) if isinstance(n, ast.If)))
    check([w for w in ac_wanted if w not in ac_strip_text] == list(ac_wanted)
          and [w for w in ac_wanted if w not in ac_unp_text] == list(ac_wanted),
          "CONTROL: the same reader finds NOTHING in a stripped block, and "
          "nothing in one whose banner is present but never PRINTED",
          f"stripped {len(ac_strip_text)} chars; present-but-unprinted "
          f"{len(ac_unp_text)} -- both missing all {len(ac_wanted)}")
    check(ac_arg is not None and unprintable(ac_arg) == [],
          "and every string the --arrival-carry banner prints survives a cp1252 "
          "console",
          f"{None if ac_arg is None else unprintable(ac_arg)} -- a U+26A0 here "
          f"raises UnicodeEncodeError on a default Windows console, so the flag "
          f"would kill the very run it exists to enable")

    # ---- AST: F1b adds no send site and touches no other arm -------------
    ac_blocks = [n for n in ast.walk(src)
                 if isinstance(n, ast.If) and isinstance(n.test, ast.Name)
                 and n.test.id == "ARRIVAL_CARRY"]
    ac_sending = [n for n in ac_blocks
                  if any(isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
                         and c.func.id == "send" for c in ast.walk(n))]

    def ac_names(node):
        return [n for n in ast.walk(node)
                if isinstance(n, ast.Name) and n.id == "ARRIVAL_CARRY"]

    check(ac_sending == [] and ac_names(heading_arm_ast)
          and not ac_names(stop_arm_ast) and not ac_names(click_arm_ast),
          "STRUCTURE: no `if ARRIVAL_CARRY:` block SENDS, and ARRIVAL_CARRY is "
          "named in the heading arm and NEITHER other arm",
          f"{len(ac_blocks)} blocks of which {len(ac_sending)} send; "
          f"heading={len(ac_names(heading_arm_ast))} "
          f"stop={len(ac_names(stop_arm_ast))} "
          f"click={len(ac_names(click_arm_ast))} -- a modifier that grew a send "
          f"site would be a tenth candidate policy, not F1b. The heading count "
          f"is the positive control")
    # AND THE READ IS PURE. `arrival_carry_field4` and `arrival_carry_leg` are
    # called on EVERY evaluation including refused ones, so an assignment to
    # `state[...]` inside either would make a refusal consume the queue -- the
    # defect check (4) drives from the outside, pinned here from the syntax so
    # it cannot come back through a different caller.
    ac_pure = []
    for fname in ("arrival_carry_field4", "arrival_carry_leg"):
        fn = next(n for n in ast.walk(src) if isinstance(n, ast.FunctionDef)
                  and n.name == fname)
        for node in ast.walk(fn):
            if isinstance(node, (ast.Assign, ast.AugAssign)):
                targets = (node.targets if isinstance(node, ast.Assign)
                           else [node.target])
                for t in targets:
                    if isinstance(t, ast.Subscript):
                        ac_pure.append((fname, ast.dump(t)))
    check(ac_pure == [],
          "and both READ functions are pure -- neither assigns into `state`",
          f"{ac_pure} -- they run on every evaluation, fired or refused, so a "
          f"single `state[...] = ...` in either would let a rate-limit refusal "
          f"consume the queue and drop the in-flight leg while nothing went on "
          f"the wire. arrival_carry_advance is the ONE mutation")

    return LEDGER.verdict()


if __name__ == "__main__":
    raise SystemExit(main())
