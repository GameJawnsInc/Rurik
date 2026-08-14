"""The guard contract: a refused value refuses BEFORE anything is sent or changed.

`_fraction` is the wire's last line of defense -- the client dies on
`fraction <= 1.0f` (CharPool.cpp:84) two seconds after a bad float, with no
server-side symptom. But a guard that fires AFTER the first send has already
half-happened: the refusal leaves a partial effect burst on the wire (an
attack with no damage, a revive with no refill), and on the CONNECTION thread
an escaping ValueError goes further -- `handle`'s except tuple is
ConnectionError/socket.timeout/OSError only, so the raise runs the `finally`,
closes the socket, and the client is disconnected by a number that was never
sent.

All of that is DORMANT today: every `_fraction` call site passes a fixed
constant inside [-1, 1]. It stops being dormant the day computed per-skill
values arrive (studies/combat/PLAN.md step 8), which is why this contract
lands FIRST (step 2, amendments C4/C8b/C9).

RED-FIRST, per C8b, so the observed failure mode is on record rather than
assumed. Against the pre-guard tree (cdefe83), section 1 measured:

    hit_enemy with HIT_FRACTION poisoned to 1.5 raised ValueError only AFTER
    sending GV_ATTACK_STARTED (1 message on the wire) and after consuming the
    swing timer and the target's health (100 -> 0 bookkept, nothing sent).

which is exactly the guard-after-effect shape the gate map calls out. The
checks below assert the DESIRED contract and therefore went red on that tree.
"""

import io
import contextlib
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                ".."))
import checks  # noqa: E402

LEDGER = checks.Ledger("guard contract", floor=6)
check = LEDGER.ok


def _fresh_agent():
    return {"name": "target", "dead": False, "last_hit": 0.0,
            "max_health": 100.0, "health": 100.0, "pos": (0.0, 0.0)}


def section_hit_enemy():
    """An out-of-range fraction refuses hit_enemy before ANY effect."""
    import authsrv

    print("1. hit_enemy: guard before effect, both directions of the timer")
    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))
    state = {"agents": {10: _fresh_agent()}, "pos": (0.0, 0.0)}

    saved = authsrv.HIT_FRACTION
    authsrv.HIT_FRACTION = 1.5   # the shape step 8's computed values can take
    try:
        raised = False
        try:
            authsrv.hit_enemy(send, state, 10, 0)
        except ValueError:
            raised = True
        check(raised, "an out-of-range fraction still raises ValueError",
              "the guard is _fraction's refusal, not a silent clamp -- "
              "clamping is exactly what its docstring rules out")
        check(sent == [], "and NOTHING was sent first",
              f"sent={sent!r} -- on the pre-guard tree this held "
              f"GV_ATTACK_STARTED, an attack opened on the wire with no "
              f"damage and no close ever coming")
        agent = state["agents"][10]
        check(agent["health"] == 100.0, "the target's health is untouched",
              f"health={agent['health']} -- the pre-guard tree bookkept "
              f"100 -> 0 while sending nothing, a kill the wire never saw")
        check(agent["last_hit"] == 0.0, "and the swing timer is unconsumed",
              "a refused swing must be retryable next tick, not eaten")
    finally:
        authsrv.HIT_FRACTION = saved

    # The control: with the real constant the same call sends the whole
    # swing. A guard that refuses everything would pass every check above.
    sent.clear()
    state["agents"][10] = _fresh_agent()
    authsrv.hit_enemy(send, state, 10, 0)
    ops = [op for op, _, _ in sent]
    check(len(sent) == 3, "control: the in-range path still sends the swing",
          f"{len(sent)} messages: {ops}")
    check(state["agents"][10]["health"] == 100.0 - 100.0 * authsrv.HIT_FRACTION,
          "control: and the in-range damage is bookkept",
          f"health={state['agents'][10]['health']}")


def main():
    section_hit_enemy()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
