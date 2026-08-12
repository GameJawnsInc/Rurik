"""The 0x000C/0x0009/0x000D round trip that drives the client's net graph.

    python toolkit/authsrv/test_ping.py

studies/smsg `0x000C` CLIENT_PERF_REQUEST and `0x000D` LATENCY_REPORT, read out
of the client's own handler table (0x00491E50 and 0x00491ED0) rather than
guessed. The exchange is three messages: server `0x000C` (empty) -> client
`0x0009` (its perf state) -> server `0x000D[elapsed_ms]`, which the client
clamps, averages over ten samples and plots on `s_netGraph`.

What is worth testing here is NOT that a timer fires. It is the handful of
places where a plausible implementation quietly lies:

  * sending a second request while one is outstanding would move the start
    time and make the round trip read SHORTER than it was -- a latency meter
    that under-reports exactly when the link is bad;
  * answering an unprompted reply would put an invented number on the one
    readout an operator would take as measured (0 of 79 in the corpus are
    unprompted, so this is not a case the protocol has);
  * sending a value over the client's own 5000 ms cutoff produces a message
    the client DISCARDS at 0x0048DA40 (`cmp esi,0x1388 / ja skip`), so the
    graph never moves and the feature looks dead rather than wrong.

Section 4 is the one that is not about this feature at all: a tape run requires
ZERO messages of our own on the channel, and PLAN.md §3.4 records a run whose
client assert was un-attributable because our 20 Hz ticker talked over
ArenaNet's recording. A 5 s timer is a slower version of that same
contamination, so the tape guard is asserted structurally rather than trusted.

Standard library only. No vault, no socket, no client.
"""
import ast
import contextlib
import io
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
import checks  # noqa: E402
from codec import Codec  # noqa: E402

LEDGER = checks.Ledger("net-graph ping loop", floor=22)

AUTHSRV_PY = os.path.join(HERE, "authsrv.py")


class Sends(list):
    """Collect (opcode, values, label) the way the real `send` is called."""

    def __call__(self, opcode, values, label="", quiet=False):
        self.append((opcode, values, label))


def tick_thread_is_tape_guarded(tree):
    """Is `world_tick` started ONLY under `TAPE_EVENTS is None`?

    Structural, because the property is not local to ping_tick: the timer is
    safe because of where its thread is started, three hundred lines away.
    """
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not (isinstance(test, ast.Compare)
                and isinstance(test.left, ast.Name)
                and test.left.id == "TAPE_EVENTS"
                and len(test.ops) == 1
                and isinstance(test.ops[0], ast.Is)
                and isinstance(test.comparators[0], ast.Constant)
                and test.comparators[0].value is None):
            continue
        for sub in ast.walk(node):
            if (isinstance(sub, ast.Call)
                    and isinstance(sub.func, ast.Attribute)
                    and sub.func.attr == "Thread"):
                for kw in sub.keywords:
                    if (kw.arg == "target" and isinstance(kw.value, ast.Name)
                            and kw.value.id == "world_tick"):
                        return True
    return False


def called_in_finally(tree, fname):
    """Is `fname` called from a `finally:` block? Reachability, not behaviour.

    The check that was missing: `report_ping` sat after the read loop inside
    the `try` and never ran, because the loop exits by ConnectionResetError
    when the harness kills the client. Sections 1-7 above all passed anyway --
    they call the function directly, so none of them asks whether anything
    else does.
    """
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        for stmt in node.finalbody:
            for call in ast.walk(stmt):
                if (isinstance(call, ast.Call)
                        and isinstance(call.func, ast.Name)
                        and call.func.id == fname):
                    return True
    return False


def dispatches(tree, const_name):
    """Is there an `opcode == <const_name>` arm anywhere in the file?"""
    for node in ast.walk(tree):
        if (isinstance(node, ast.Compare)
                and isinstance(node.left, ast.Name)
                and node.left.id == "opcode"
                and len(node.ops) == 1
                and isinstance(node.ops[0], ast.Eq)
                and isinstance(node.comparators[0], ast.Name)
                and node.comparators[0].id == const_name):
            return True
    return False


def main():
    import authsrv

    codec = Codec()
    tree = ast.parse(open(AUTHSRV_PY, encoding="utf-8").read())

    # ---- 0. the constants are ArenaNet's, not ours --------------------------
    LEDGER.ok(authsrv.PING_SECONDS == 5.0,
              "the cadence is the measured 5.000 s",
              f"PING_SECONDS={authsrv.PING_SECONDS}. 75 of 76 gaps inside "
              f"100 ms across three tapes; 0x000C/0x000D are the only periodic "
              f"messages in the corpus, next-lowest CV 0.586")
    LEDGER.ok(authsrv.LATENCY_MAX_MS == 5000,
              "and the cutoff is the client's own 0x1388",
              f"LATENCY_MAX_MS={authsrv.LATENCY_MAX_MS}, from "
              f"`cmp esi,0x1388 / ja skip` at 0x0048DA40")
    LEDGER.ok(authsrv.GAME_SMSG_CLIENT_PERF_REQUEST == 0x000C
              and authsrv.GAME_SMSG_LATENCY_REPORT == 0x000D
              and authsrv.GAME_CMSG_CLIENT_PERF_REPORT == 0x0009,
              "and all three opcodes match the client's handler table",
              f"{authsrv.GAME_SMSG_CLIENT_PERF_REQUEST:#06x} "
              f"{authsrv.GAME_SMSG_LATENCY_REPORT:#06x} "
              f"{authsrv.GAME_CMSG_CLIENT_PERF_REPORT:#06x}")

    # ---- 1. the wire shapes are what the schema declares ---------------------
    req = codec.encode("GAME_SMSG", 0x000C, [])
    LEDGER.ok(len(req) == 2 and req == b"\x0c\x00",
              "0x000C is two bytes and carries NOTHING",
              f"{req.hex()} -- the request has no payload; everything "
              f"interesting is in the reply and in our own clock")
    rep = codec.encode("GAME_SMSG", 0x000D, [1234])
    LEDGER.ok(len(rep) == 6 and rep[2:] == (1234).to_bytes(4, "little"),
              "0x000D is a header and one little-endian dword",
              f"{rep.hex()}")

    # ---- 2. the timer: fires, then holds for the interval --------------------
    send, state = Sends(), {}
    authsrv.ping_tick(send, state, 1)
    LEDGER.ok(len(send) == 1
              and send[0][0] == authsrv.GAME_SMSG_CLIENT_PERF_REQUEST,
              "the first tick sends a request",
              f"{[(hex(o), v) for o, v, _ in send]}")
    LEDGER.ok(send[0][1] == [],
              "with an empty value list",
              f"{send[0][1]}")

    for _ in range(50):
        authsrv.ping_tick(send, state, 1)
    LEDGER.ok(len(send) == 1,
              "and 50 more ticks inside the interval send NOTHING",
              f"{len(send)} sends -- the world tick runs at 20 Hz, so an "
              f"unguarded timer would emit 20 requests a second")

    # wind the clock back past the interval rather than sleeping 5 s
    state["ping_at"] -= authsrv.PING_SECONDS + 0.01
    authsrv.ping_tick(send, state, 1)
    LEDGER.ok(len(send) == 2,
              "a tick after the interval sends the next one",
              f"{len(send)} sends")

    # ---- 3. the under-report trap: never move the start time -----------------
    send2, state2 = Sends(), {}
    authsrv.ping_tick(send2, state2, 2)
    first_start = state2["ping_sent"]
    state2["ping_at"] -= authsrv.PING_SECONDS + 0.01
    authsrv.ping_tick(send2, state2, 2)          # reply still outstanding
    LEDGER.ok(state2["ping_sent"] == first_start,
              "a second request with one outstanding KEEPS the original start "
              "time -- the under-report trap",
              f"start moved by {state2['ping_sent'] - first_start:.6f}s. "
              f"Moving it would make a bad link report a SHORTER round trip, "
              f"which is the one direction a latency meter must not fail in")
    LEDGER.ok(state2.get("ping_missed") == 1,
              "and the unanswered request is counted",
              f"ping_missed={state2.get('ping_missed')}")

    # ---- 4. the reply ---------------------------------------------------------
    send3, state3 = Sends(), {}
    state3["ping_sent"] = time.perf_counter() - 0.050
    authsrv.handle_perf_report([0, 33, 1], send3, state3, 3)
    LEDGER.ok(len(send3) == 1
              and send3[0][0] == authsrv.GAME_SMSG_LATENCY_REPORT,
              "a reply produces a LATENCY_REPORT",
              f"{[(hex(o), v) for o, v, _ in send3]}")
    ms = send3[0][1][0]
    LEDGER.ok(40 <= ms <= 200,
              "carrying the real elapsed time, not a constant",
              f"{ms} ms for a 50 ms-old request (a wide band: this is a "
              f"wall-clock measurement on a loaded machine, and the point is "
              f"that it TRACKS rather than that it is exact)")
    LEDGER.ok(state3.get("ping_sent") is None,
              "and the outstanding request is cleared",
              f"ping_sent={state3.get('ping_sent')}")
    LEDGER.ok(state3.get("ping_last_ms") == ms,
              "and remembered for the disconnect summary",
              f"ping_last_ms={state3.get('ping_last_ms')}")

    # a SECOND reply to the same request is now unprompted and must be dropped
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        authsrv.handle_perf_report([0, 33, 1], send3, state3, 3)
    LEDGER.ok(len(send3) == 1,
              "a second reply to the same request sends nothing",
              f"{len(send3)} sends")
    LEDGER.ok("no request outstanding" in buf.getvalue(),
              "and says why, rather than failing silently",
              f"{buf.getvalue().strip()!r}")

    # ---- 5. an unprompted reply is never answered with an invented number ----
    send4, state4 = Sends(), {}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        authsrv.handle_perf_report([0, 33, 1], send4, state4, 4)
    LEDGER.ok(len(send4) == 0,
              "an unprompted reply is DROPPED, not answered",
              f"{len(send4)} sends. 0 of 79 replies in the corpus are "
              f"unprompted, so inventing an elapsed time here would put a "
              f"fabricated number on the net graph")

    # ---- 6. over the client's cutoff we send nothing -------------------------
    send5, state5 = Sends(), {}
    state5["ping_sent"] = time.perf_counter() - 6.0     # 6000 ms > 5000
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        authsrv.handle_perf_report([0, 33, 1], send5, state5, 5)
    LEDGER.ok(len(send5) == 0,
              "a round trip over the client's 5000 ms cutoff is NOT sent",
              f"{len(send5)} sends -- the client discards it at 0x0048DA40 "
              f"before touching the shift register, so sending it is a no-op "
              f"that looks like a working feature from our side")
    LEDGER.ok("discard" in buf.getvalue(),
              "and the operator is told, because a still net graph otherwise "
              "reads as a dead feature",
              f"{buf.getvalue().strip()!r}")

    # ---- 7. the disconnect summary ------------------------------------------
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        authsrv.report_ping({}, 7)
    LEDGER.ok(buf.getvalue() == "",
              "a connection that never pinged reports nothing",
              f"{buf.getvalue()!r}")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        authsrv.report_ping(state2, 7)
    LEDGER.ok("unanswered" in buf.getvalue(),
              "and one that lost a request says so",
              f"{buf.getvalue().strip()!r} -- ping_missed counted and never "
              f"printed would be D9(a) in miniature")

    # ---- 8. tape safety, asserted structurally ------------------------------
    LEDGER.ok(tick_thread_is_tape_guarded(tree),
              "world_tick -- which owns the 5 s timer -- starts ONLY when "
              "TAPE_EVENTS is None",
              "a tape run requires zero messages of our own on the channel; "
              "PLAN.md §3.4 records a run whose client assert was "
              "un-attributable because our ticker talked over the recording")
    LEDGER.ok(dispatches(tree, "GAME_CMSG_CLIENT_PERF_REPORT"),
              "and the reply has a real dispatch arm",
              "otherwise it would land on D9(a)'s catch-all, which is where "
              "it was until 2026-08-11")

    LEDGER.ok(called_in_finally(tree, "report_ping"),
              "and report_ping is called from a `finally`, so a reset still "
              "prints the round trip",
              "MEASURED 2026-08-11: the 45 s loopback run completed 10 of 10 "
              "round trips and wrote ZERO ping summaries, because the call sat "
              "in the `try` and the connection ended on ConnectionResetError")

    # ---- 9. the structural checks must be able to go red --------------------
    sab0 = ast.parse("def f():\n"
                     "    try:\n"
                     "        report_ping(s, c, r)\n"
                     "    finally:\n"
                     "        rec.close()\n")
    LEDGER.ok(not called_in_finally(sab0, "report_ping"),
              "CONTROL: a call in the TRY body is not reachable on a reset",
              "this is the arrangement that shipped and never ran")
    sab = ast.parse("def f():\n"
                    "    if TAPE_EVENTS is not None:\n"
                    "        threading.Thread(target=world_tick).start()\n")
    LEDGER.ok(not tick_thread_is_tape_guarded(sab),
              "CONTROL: the tape guard reversed is caught",
              "`is not None` is the exact inversion that would make every "
              "tape run contaminated, and it is one character from correct")
    sab2 = ast.parse("def f():\n"
                     "    if TAPE_EVENTS is None:\n"
                     "        threading.Thread(target=something_else).start()\n")
    LEDGER.ok(not tick_thread_is_tape_guarded(sab2),
              "CONTROL: a guard around a DIFFERENT thread does not count",
              "the check must be about world_tick specifically")
    LEDGER.ok(not dispatches(ast.parse("x = 1"), "GAME_CMSG_CLIENT_PERF_REPORT"),
              "CONTROL: the dispatch detector says no when there is no arm",
              "otherwise the check above passes for the wrong reason")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
