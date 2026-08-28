"""MOVECODE-K1: the keep-alive re-grant refuses in every direction it should.

    python toolkit/authsrv/test_keepalive.py

WHY THIS FILE IS MOSTLY REFUSALS. `--keepalive-grant` is the SIXTH candidate in a
family that killed five, and the graveyard at `HEADING_GRANT` / `CLIENT_ENDPOINT` is
specific about how they died:

  * `--heading-grant` refreshed FASTER than retail (0.32 s against 0.49 s) and still
    warped, because it computed its point from `state["pos"]` -- the server's own
    integrated model -- rather than the report in hand, and because it CLIPPED that
    point to our navmesh where the client's own collision disagrees.
  * `--client-endpoint` met both terms it was designed for and warped MORE.

So the interesting content of this flag is not that it grants; it is WHAT IT REFUSES
TO SEND and WHERE THE POINT COMES FROM. §5 and §6 are therefore SOURCE checks over
the call site rather than behaviour checks over the verdict: a future edit that
swapped `client_pos` for `pos` would keep every behaviour test green while
reintroducing a measured warp, which is exactly the shape `test_movehook.py` §11 was
added for after a length check could not catch a field reorder.

§7 is the clock check, and it is here because the bug was real during development:
`world_tick` runs on `time.perf_counter()` (an arbitrary epoch, used for the tick
delta) while every stamp the verdict reads -- `grant_at`, `sync_at`, `pos_seen` -- is
`time.time()`. Mixing them does not raise; it makes every interval a nonsense number
and parks `_sync_position` instantly, so the pin gate would read "parked" forever and
the flag would grant on every tick.
"""
import ast
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "harness"))
import checks                                                    # noqa: E402
import authsrv                                                   # noqa: E402

# MEASURED off a real green run, 2026-08-27, counted per section off the banner.
#   §1  5  the flag is off, and off means off        process-free
#   §2  7  each refusal fires for its own reason     process-free
#   §3  4  the positive case, and its numbers        process-free
#   §4  3  the band is the adjudicated 100.0         process-free
#   §5  4  the point is the REPORT, not the model    process-free (source)
#   §6  3  the point is never clipped                process-free (source)
#   §7  3  the call site uses time.time()            process-free (source)
#   §8  3  the override is refused on its own        process-free (source)
#  ---- every section is process-free, so the floor is the whole run.
LEDGER = checks.Ledger("keepalive", floor=32)
check = checks.adopt(LEDGER)


def eq(got, want, label):
    return check(got == want, label,
                 "" if got == want else f"got {got!r}, want {want!r}")


def _state(**kw):
    """A state dict with every field the verdict reads, set to a GRANTING case.

    Built so each test turns exactly ONE thing off. A fixture that starts in a
    refusing state would let a rule stop working without any test noticing -- the
    positive case has to be the default for the negatives to mean anything.
    """
    s = {
        "client_pos": (1000.0, 0.0),     # the report in hand
        "pos": (9999.0, 9999.0),         # the model -- deliberately far away, see §5
        "pos_rejects": 0,
        "sync_from": (0.0, 0.0),
        "sync_to": None,                 # parked
        "sync_at": 1000.0,
        "grant_at": None,
        "plane": 0,
    }
    s.update(kw)
    return s


# ------------------------------------------------------------------ §1
def section_1():
    authsrv.KEEPALIVE_GRANT = False
    ok, why, sep, since = authsrv._keepalive_ok(_state(), 1000.0)
    eq(ok, False, "1. OFF by default the verdict refuses")
    eq(why, "off", "1. and says so")
    eq(sep, None, "1. and computes NO separation when off")
    eq(since, None, "1. and no interval either")
    # The module global is the only switch; nothing else may arm it.
    eq(authsrv.KEEPALIVE_GRANT, False,
       "1. and the module default is False -- an opt-in flag that shipped ON "
       "would put a sixth candidate on the wire for every session")


# ------------------------------------------------------------------ §2
def section_2():
    authsrv.KEEPALIVE_GRANT = True
    now = 1000.0

    ok, why, _s, _i = authsrv._keepalive_ok(_state(client_pos=None), now)
    check(not ok and why == "no-report",
          "2. no report in hand -> refuse", f"got {why}")

    ok, why, _s, _i = authsrv._keepalive_ok(_state(pos_rejects=1), now)
    check(not ok and why == "report-rejected",
          "2. a REJECTED report -> refuse",
          "our model and the client disagree about where the player is, which is "
          "the graveyard's term (1) failing live")

    ok, why, _s, _i = authsrv._keepalive_ok(_state(sync_from=None), now)
    check(not ok and why == "unseeded",
          "2. an unseeded sync model -> refuse",
          "a model that was never seeded must not produce a confident separation")

    ok, why, _s, since = authsrv._keepalive_ok(
        _state(grant_at=now - 0.1), now)
    check(not ok and why == "rate-limited",
          "2. faster than GRANT_MIN_INTERVAL -> refuse", f"got {why}")
    eq(round(since, 3), 0.1, "2. and the interval is reported for the row")

    # Still walking its last leg: sync_to set and the lerp has NOT reached it.
    ok, why, _s, _i = authsrv._keepalive_ok(
        _state(sync_from=(0.0, 0.0), sync_to=(100000.0, 0.0), sync_at=now), now)
    check(not ok and why == "twin-walking",
          "2. a twin still WALKING its last leg -> refuse",
          "only a PARKED twin is falling behind; one still walking is doing what "
          "we asked, and granting over it would restart the leg every tick")

    ok, why, sep, _i = authsrv._keepalive_ok(
        _state(client_pos=(50.0, 0.0)), now)
    check(not ok and why == "in-band",
          "2. a separation inside the band -> refuse", f"got {why} sep={sep}")


# ------------------------------------------------------------------ §3
def section_3():
    authsrv.KEEPALIVE_GRANT = True
    now = 1000.0
    ok, why, sep, since = authsrv._keepalive_ok(_state(), now)
    check(ok, "3. a PARKED twin more than the band away -> GRANT", f"got {why}")
    eq(why, "keepalive", "3. and names itself")
    eq(round(sep, 1), 1000.0,
       "3. and the separation is client_pos vs the MODELLED twin")
    # An arrived leg (sync_to reached) must count as parked, not as walking.
    ok, why, _s, _i = authsrv._keepalive_ok(
        _state(sync_from=(0.0, 0.0), sync_to=(10.0, 0.0), sync_at=now - 100.0),
        now)
    check(ok and why == "keepalive",
          "3. a leg the twin has ARRIVED on counts as parked",
          f"got {why} -- the lerp has reached sync_to, so the twin is pinned at "
          f"m_segmentPoint and is exactly the case this flag exists for")


# ------------------------------------------------------------------ §4
def section_4():
    eq(authsrv.KEEPALIVE_SEPARATION, 100.0,
       "4. the band is 100.0 -- the figure PLAN.md sec.7 Q11 reconciled "
       "RESYNC_SEPARATION to, not a second constant for the same quantity")
    authsrv.KEEPALIVE_GRANT = True
    now = 1000.0
    # Exactly at the band is INSIDE it: the comparison is <=, so the band is a
    # refusal floor rather than a trigger.
    ok, _w, _s, _i = authsrv._keepalive_ok(_state(client_pos=(100.0, 0.0)), now)
    check(not ok, "4. exactly at the band refuses", "the compare is <=")
    ok, _w, _s, _i = authsrv._keepalive_ok(_state(client_pos=(100.1, 0.0)), now)
    check(ok, "4. just past the band grants",
          "and the two together pin which side the boundary falls on")


def _keepalive_block():
    """The world-tick call site, as source text.

    Located by its own marker rather than by line number, so the checks below do
    not silently start reading a different block when the file moves.
    """
    src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
    start = src.index("if KEEPALIVE_GRANT:")
    end = src.index('dest = state.get("dest")', start)
    return src[start:end]


# ------------------------------------------------------------------ §5
def section_5():
    blk = _keepalive_block()
    check('state["client_pos"]' in blk,
          "5. the call site sends state[\"client_pos\"] -- the REPORT in hand",
          "_take_client_position writes it ONLY on the accept path and ONLY from "
          "what the client said")
    check('state["pos"]' not in blk,
          "5. and NEVER state[\"pos\"]",
          "that is the server's integrated model, and computing the point from it "
          "is one of the two failures --heading-grant's epitaph names")
    # And the fixture proves the distinction is live rather than cosmetic: the
    # verdict's separation used client_pos even though pos was 9999,9999.
    authsrv.KEEPALIVE_GRANT = True
    _ok, _w, sep, _i = authsrv._keepalive_ok(_state(), 1000.0)
    check(abs(sep - 1000.0) < 0.01,
          "5. and the verdict measures from the report, not the model",
          f"sep={sep} -- the model sits at (9999,9999) in this fixture, so a "
          f"verdict reading it would be ~14,140 u")
    check("GAME_SMSG_AGENT_MOVE_TO_POINT" in blk
          and "AGENT_UPDATE_POSITION" not in blk,
          "5. it sends 0x0029 and never the hard set",
          "0x0029 resolves through syncPtr and cannot reach the displayed body; "
          "AGENT_UPDATE_POSITION lands on BOTH copies and is the warp the tick's "
          "own epitaph is about")


# ------------------------------------------------------------------ §6
def section_6():
    blk = _keepalive_block()
    for bad in ("clip_to_walkable", "clip(", ".clip"):
        check(bad not in blk,
              f"6. the granted point is not passed through `{bad}`",
              "--heading-grant's other named failure was a point shortened by OUR "
              "navmesh where the client's own collision disagrees; this point is "
              "one the client already stood on, so a clip could only move it "
              "somewhere the client never was")


# ------------------------------------------------------------------ §7
def section_7():
    blk = _keepalive_block()
    check("_keepalive_ok(state, time.time())" in blk,
          "7. the verdict is called with time.time()",
          "every stamp it reads -- grant_at, sync_at, pos_seen -- is time.time()")
    check("_keepalive_ok(state, now)" not in blk,
          "7. and NOT with the tick loop's perf_counter `now`",
          "mixing the two does not raise: it makes every interval nonsense and "
          "parks _sync_position instantly, so the pin gate reads parked forever "
          "and the flag grants on every tick")
    # The block must be reachable for a STANDING player, which is the case both
    # of run 5's real warps had (both velocities exactly 0.0).
    src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
    ka = src.index("if KEEPALIVE_GRANT:")
    early = src.index('dest = state.get("dest")\n                    if not dest:')
    check(ka < early,
          "7. and it runs BEFORE the tick's `dest` early-out",
          "run 5's two real warps both had the player STANDING STILL with the "
          "twin parked hundreds of units away; an early-out on dest would skip "
          "exactly those")


# ------------------------------------------------------------------ §8
def section_8():
    src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(
                node.func, "attr", None) == "add_argument":
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    names.add(arg.value)
    check("--keepalive-grant" in names, "8. the flag is registered in argparse")
    check("--keepalive-separation" in names,
          "8. and so is the negative-control override")
    check("--keepalive-separation needs --keepalive-grant" in src,
          "8. and the override REFUSES on its own",
          "a run launched with only the override would look configured and change "
          "nothing, which is the shape of a measurement that quietly answers a "
          "different question")


def main():
    try:
        section_1()
        section_2()
        section_3()
        section_4()
        section_5()
        section_6()
        section_7()
        section_8()
    finally:
        authsrv.KEEPALIVE_GRANT = False
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
