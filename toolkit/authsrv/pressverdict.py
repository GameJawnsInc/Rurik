"""The press/swing telemetry rows -- what the server said it did with a keypress.

ROWS, NOT DECISIONS. Nothing in this file chooses anything. Each function either
writes one telemetry event (`press_verdict`, `swing_verdict`, `chain_pause`),
counts a tick that left early, or charges the swing clock by the time that has
passed since the last moving tick. Every decision these rows describe -- which
branch of `attack_tick` returns, whether a press opens a swing, whether the chain
is paced or paused while the body moves -- stays in `authsrv.py` beside the flags
that arm it (`MOVE_KEEPS_CHAIN`, `CHAIN_RESTART_PACED`, `CHAIN_PAUSES_WHILE_MOVING`,
`CHAIN_PAUSE_CHARGES_WITHOUT_TARGET`, `ATTACK_INTERVAL`), and the only callers in
`authsrv.py` are `attack_tick` and `begin_attack`.

WHY THEY ARE ONE FILE. All seven exist for one reason, stated in their own
docstrings below and worth reading together: a tick that decided nothing said
nothing, so the server's own captures could not tell a swing that was refused from
a swing that never happened. `_press_refused` / `_press_answered` / `_press_row`
closed that for the press (ANIMREF-RE 41), `_swing_dropped` for the swing already
in flight (SWINGCANCEL, studies/movecode 1z-cx), and `_chain_pause_note` /
`_chain_pause_flush` / `_chain_pause_charge` for the four branches that were
starving the pause accumulator (MOVECODE-1z-dc, 1z-dg). They are the R11 rule --
"a suppressed grant is PRINTED, never silent" -- applied to the swing path.

POINTERS FOR THE COMMENTS THAT MOVED (their referents did not). The "both
placements (1z-dg's top-of-tick, the legacy bottom)" that `_chain_pause_charge`
names are two call sites inside `attack_tick`; the flag that selects them,
`CHAIN_PAUSE_CHARGES_WITHOUT_TARGET`, keeps its banner in
`authsrv.py`, as do `CHAIN_PAUSES_WHILE_MOVING` and `ATTACK_INTERVAL`.
`_chain_pause_flush` still reports `ATTACK_INTERVAL`, which arrives as a parameter
carrying the constant's own name so that the body is the line that shipped; it is
read at the call site in `authsrv.py`, never bound as a default value, because a
default is evaluated at `def` time and would freeze the flag.

THE FAKE CLOCK DOES NOT REACH HERE. `test_position_trust.py` drives time by
rebinding `authsrv.time`; the three functions below that call `time.time()`
(`_swing_dropped`, `_press_refused`, `_press_answered`) read *this* module's
`time`, which that rebind does not touch. Nothing depends on it today -- these
rows are telemetry and no check compares an `age` against a driven clock -- but a
later test that drives the clock and then asserts on a row would be reading the
wall clock and passing for the wrong reason.

Standard library only, and no import of the server: `authsrv.py` imports this
file, never the other way round. It runs as `__main__`, so an import back would
load a second copy whose flags `main()` never set.
"""
import time


def _chain_pause_charge(state, now):
    """Charge the swing clock for the moving time since the last moving tick
    and stamp this one. Returns what was charged (0.0 on the first tick of a
    run, whose stamp was None). The arithmetic §31 always had, moved into one
    place so both placements (1z-dg's top-of-tick, the legacy bottom) share it."""
    since = state.get("chain_pause_tick")
    charged = 0.0
    if since is not None and now > since:
        charged = now - since
        state["player_last_swing"] = \
            state.get("player_last_swing", 0.0) + charged
        st = state.setdefault("chain_pause_stats",
                              {"charged": 0.0, "ticks_moving": 0, "left": {}})
        st["charged"] += charged
    state["chain_pause_tick"] = now
    return charged


def _press_row(rec, **kw):
    """One `press_verdict` telemetry row (ANIMREF-RE 41). `rec` may be None
    (the tests, the harness control slot before a recorder exists)."""
    if rec is not None:
        try:
            rec.event("press_verdict", **kw)
        except Exception:      # telemetry must never take the tick down
            pass


def _chain_pause_note(state, branch):
    """One moving tick of `attack_tick` that did NOT reach the accumulator.

    THE GAP THIS CLOSES (studies/movecode 1z-dc). The freeze charges
    `now - chain_pause_tick` only on ticks that reach the bottom of
    `attack_tick`; four branches return above it (dead, no target, target
    gone, out of reach). Measured against retail, the pause charges
    **19 % of the real moving span** -- p50 0.234 s charged against a
    0.951 s span -- and charging the whole span would put our moving gap at
    2.701 s against retail's own 2.657 s, within 1.7 %. So the model is
    right and the accumulator is starved, and NOTHING IN THE SERVER SAID SO:
    a tick that leaves early is indistinguishable from a tick that charged
    nothing. Three candidate suppressors were tested against the corpus and
    all three failed (1z-dc.4), which is exactly why this counts rather than
    guesses.

    Per-tick rows would out-number the swings 20:1, so this only counts; the
    summary rides the next swing's own row.
    """
    st = state.setdefault("chain_pause_stats",
                          {"charged": 0.0, "ticks_moving": 0, "left": {}})
    st["ticks_moving"] += 1
    st["left"][branch] = st["left"].get(branch, 0) + 1


def _chain_pause_flush(state, rec, conn_id, ATTACK_INTERVAL):
    """Emit and reset the pause summary -- one row per swing OPENED."""
    st = state.pop("chain_pause_stats", None)
    if st is None:
        return
    if rec is not None:
        try:
            rec.event("chain_pause", charged=round(st["charged"], 3),
                      ticks_moving=st["ticks_moving"], left=dict(st["left"]),
                      interval=float(ATTACK_INTERVAL))
        except Exception:      # telemetry must never take the tick down
            pass
    if st["left"]:
        print(f"[c{conn_id}] chain pause: charged {st['charged']:.3f} s over "
              f"{st['ticks_moving']} moving tick(s); "
              f"{sum(st['left'].values())} left early {st['left']} "
              f"[MOVECODE-1z-dc]", flush=True)


# THE KNOWN-BAD ARM RUNS THROUGH THIS NAME, AND THROUGH authsrv's COPY OF IT.
# `test_playerswing.py:2274` rebinds `authsrv._swing_dropped` to a no-op lambda as
# its declared known-bad arm -- the run that proves the check it guards can go
# red. That rebind lands on *authsrv's* global, and it still reaches this body
# because `_swing_dropped`'s only callers are the five sites inside `attack_tick`,
# which stayed in `authsrv.py` and resolve the name there at call time. IT HOLDS
# ONLY WHILE NOTHING IN THIS FILE CALLS `_swing_dropped`: a call from one of the
# functions below would bind to this module's own global, the rebind would miss
# it, and that known-bad arm would go silently green.
# (Written in prose on purpose: the refactor's own census counts the literal
# assignment form `authsrv.<name> =` across the tree to find monkeypatch sites,
# and a quoted example here would land in it as a false one.)
def _swing_dropped(state, rec, conn_id, branch, **detail):
    """An ARMED swing was thrown away before it could land, and this is the
    row that says so. R11 -- "a suppressed grant is PRINTED, never silent" --
    applied to the half of the swing path that never had it.

    THE GAP THIS CLOSES, measured rather than supposed (studies/movecode
    §1z-cx, RUN-1zCG session 8): `_press_refused` writes nothing once the
    press it describes has been ANSWERED (`pend["answered"] is not None`),
    and a swing in flight is BY DEFINITION one whose press was answered --
    so every one of `attack_tick`'s in-flight drops returned through a
    logger that had already declined to log. Four of the operator's seven
    "full animation, no damage" swings left the server with no row, no
    print and no wire event of any kind. The press half of this path has
    had the discipline since ANIMREF-RE 41; the swing half did not.

    Emitted ONLY when a swing was actually armed -- a tick that drops
    nothing says nothing, or the row would out-number the swings.
    """
    swing = state.get("player_swing")
    if swing is None:
        return
    now = time.time()
    detail.setdefault("target", state.get("attacking"))
    detail["into_windup"] = round(now - swing.get("armed_at", now), 3)
    detail["lands_in"] = round(swing.get("lands_at", now) - now, 3)
    if rec is not None:
        try:
            rec.event("swing_verdict", branch=branch, **detail)
        except Exception:      # telemetry must never take the tick down
            pass
    why = ", ".join(f"{k} {v}" for k, v in detail.items())
    print(f"[c{conn_id}] SWING DROPPED in flight: {branch} ({why}) "
          f"[SWINGCANCEL, studies/movecode 1z-cx]", flush=True)


def _press_refused(state, rec, conn_id, branch, **detail):
    """attack_tick found a PENDING press and did not open its swing this
    tick. The FIRST refusal writes the row and prints -- the R11 rule, "a
    suppressed grant is PRINTED, never silent", applied to the swing -- and
    every later tick only counts. `terminal` closes the press: nothing will
    ever answer it (the order was forgotten or the target went)."""
    pend = state.get("press_pending")
    if pend is None or pend.get("answered") is not None:
        return
    pend["ticks"] += 1
    if pend.get("refused") is not None:
        if detail.pop("terminal", False):
            pend["answered"] = branch
            _press_row(rec, fired=False, reason=branch, target=pend["target"],
                       age=round(time.time() - pend["t"], 3),
                       refused_by=pend["refused"], ticks=pend["ticks"],
                       **detail)
            state["press_pending"] = None
        return
    terminal = detail.pop("terminal", False)
    pend["refused"] = branch
    age = round(time.time() - pend["t"], 3)
    _press_row(rec, fired=False, reason=branch, target=pend["target"],
               age=age, ticks=pend["ticks"], **detail)
    why = ", ".join(f"{k} {v}" for k, v in detail.items())
    print(f"[c{conn_id}] press REFUSED at the tick: {branch}"
          f"{' (' + why + ')' if why else ''} -- agent {pend['target']}, "
          f"{age:.3f} s after the press [ANIMREF-RE 41]", flush=True)
    if terminal:
        pend["answered"] = branch
        state["press_pending"] = None


def _press_answered(state, rec, conn_id, how, **detail):
    """The pending press got its answer: `swing` (ATTACK_STARTED went out) or
    `follow` (the approach's 0x002A did). The row carries the latency and,
    when the press was refused first, which branch held it and for how many
    ticks -- so a capture shows the starve AND its release."""
    pend = state.get("press_pending")
    if pend is None or pend.get("answered") is not None:
        return
    now = time.time()
    age = round(now - pend["t"], 3)
    pend["answered"] = how
    _press_row(rec, fired=True, reason=how, target=pend["target"], age=age,
               refused_by=pend.get("refused"), ticks=pend["ticks"], **detail)
    if pend.get("refused") is not None:
        print(f"[c{conn_id}] press ANSWERED by the {how} {age:.3f} s after "
              f"it, first refused by {pend['refused']} for {pend['ticks']} "
              f"tick(s) [ANIMREF-RE 41]", flush=True)
    state["press_pending"] = None
