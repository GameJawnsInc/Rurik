"""The checkpoint ladders: what a login and what a map load are supposed to
look like on the wire, and how a capture is judged against them.

Lifted out of `session.py` unchanged. The verdict comes from the capture and
nowhere else -- messages only the client sends -- because reaching a checkpoint
means the client decided to advance, not that we managed to send something and
not that a screenshot looked right.

THE TABLES ARE BUILT AT IMPORT TIME, out of `livecapture.by` and the `by_any`
below, and that bind is vault-free today. Keep it that way: importing this
module must not need a vault, a capture directory or a running server.

THE REFERENTS THAT STAYED BEHIND. `judge` is called once, by `run_client` in
`session.py`, which picks `LOGIN_CHECKPOINTS` or `LOGIN_CHECKPOINTS +
MAP_CHECKPOINTS` off `--until`; `_play` -- the event-driven Play click, still in
`session.py` -- is the other reader of `by_any`; and `ACTIONS`, `--game-host`
and `progress.py`'s LADDER, all named by the comments below, live elsewhere too.
`session.py` re-exports all four names, so those call sites are the bare names
they always were.

Every comment below travels verbatim: the `login_rejected` rationale, the
2026-08-06 three-run result (studies/handshake/PLAN.md §10) that separated the
auth and the game host, and the 0x0090 rung that stopped R2 being assumed by
every run rather than asserted by any of them.
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLKIT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, TOOLKIT)
from livecapture import by  # noqa: E402


# ------------------------------------------------------------ checkpoints ----

def by_any(*preds):
    return lambda ev: any(p(ev) for p in preds)


# (label, tail-name, predicate, hint printed when the deadline passes without it)
# The "login accepted" predicate matches the rejection too, deliberately: a
# rejection is a verdict, not a timeout waiting to happen, and judge() turns a
# matched login_rejected into an immediate named failure.
LOGIN_CHECKPOINTS = [
    ("client keyed the auth channel", "auth", by(kind="key_exchange_ok"),
     "client never completed DH on 6112 -- unpatched exe, or wrong keys"),
    ("client sent PORTAL_ACCOUNT_LOGIN", "auth",
     by(kind="decoded", name="PORTAL_ACCOUNT_LOGIN"),
     "channel keyed but no login -- the login screen ignores Enter; "
     "it needs the click on Log In (see ACTIONS)"),
    ("login accepted", "auth",
     by_any(by(kind="login_ok"), by(kind="login_rejected")),
     "no login reply at all: portal and authsrv disagree on sessions.json"),
]
# The game-channel checkpoints watch the gamesrv capture dir ALONE. OBSERVED
# 2026-08-06 (three discriminating runs, studies/handshake/PLAN.md §10): the
# client dials <GAME_SERVER_INFO host> : hardcoded 6112 for the game channel --
# the advertised port is decorative, and -authsrv plays no part in the game
# dial. The default stack therefore advertises a loopback alias the gamesrv
# owns (--game-host, 127.0.0.3) and binds the gamesrv there on 6112, so game
# traffic records to captures/gamesrv. Before the hosts were separated the
# dial landed on the AUTH listener, whose catalog self-selection served the
# game into captures/authsrv -- watching only the gamesrv dir makes that
# regression a named failure instead of a silent pass on the wrong listener.
MAP_CHECKPOINTS = [
    ("client asked for a game instance", "auth", by(kind="game_instance_request"),
     "no Play request -- did the client reach character select?"),
    ("client opened its game channel", "game", by(kind="version", channel="game"),
     "no game-channel connection on the gamesrv host -- did the client die "
     "after Play? A game channel in captures/authsrv instead means the "
     "handoff advertised the auth host, not --game-host"),
    ("game channel keyed", "game", by(kind="key_exchange_ok"),
     "game DH failed -- same keys serve both channels, so this is new information"),
    ("client requested its spawn", "game", by(kind="decoded", opcode=0x0088),
     "connected but stopped before the spawn rung -- run progress.py for the ladder"),
    # R2's own acceptance criterion is "your own body standing in a real map", and
    # this ladder used to stop one rung short of it: 0x0088 is the client ASKING for
    # its spawn, which it does before it has one. 0x0090 is the last rung in
    # progress.py's LADDER and the client only sends it once it is in the instance
    # asking who else is there. Until 2026-08-06 R2 was assumed by every run rather
    # than asserted by any of them.
    ("body is in the map", "game", by(kind="decoded", opcode=0x0090),
     "reached the spawn request and stopped -- the client asked for its spawn and "
     "never asked for the player list, so it did not finish loading in. This is R2's "
     "acceptance criterion; run progress.py to see the furthest rung reached"),
]


def judge(tails, checkpoints, t0, timeout_each=45):
    """Walk the checkpoints in order against the live capture. Returns results.

    Order is enforced through the tail cursor: an event from before the
    previous checkpoint's match can never satisfy the next one, so a ladder
    climbed out of order fails rather than flattering the run.
    """
    results, ok = [], True
    cursors = {name: 0 for name in tails}
    for label, tname, pred, hint in checkpoints:
        tail = tails[tname]
        if not ok:
            results.append({"label": label, "ok": False, "skipped": True})
            continue
        ev, cursors[tname] = tail.wait_for(pred, timeout_each,
                                           since=cursors[tname])
        t = round(time.perf_counter() - t0, 1)
        if ev and ev.get("kind") == "login_rejected":
            print(f"  [FAIL] t+{t:6.1f}s  {label}: login REJECTED for "
                  f"{ev.get('who')}\n         portal and authsrv disagree on "
                  f"sessions.json -- restarting the stack re-issues it")
            results.append({"label": label, "ok": False,
                            "rejected": ev.get("who")})
            ok = False
        elif ev:
            print(f"  [PASS] t+{t:6.1f}s  {label}")
            results.append({"label": label, "ok": True, "t": ev.get("t")})
        else:
            print(f"  [FAIL] t+{t:6.1f}s  {label}\n         {hint}")
            results.append({"label": label, "ok": False, "hint": hint})
            ok = False
    return results, ok
