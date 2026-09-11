"""The connection's own instruments -- the latency round trip and the miss ledger.

Two instruments, both about the CONNECTION rather than about the world, and neither
one puts anything in front of a player. The first is the three-message round trip
the client plots on its net graph: server `0x000C` (empty) -> client `0x0009` (its
perf state) -> server `0x000D[elapsed_ms]`. The second is studies/divergence D9(a)'s
ledger -- the c2s opcodes the schema KNOWS and this server has no arm for, which is
19 distinct GAME_CMSG opcodes and 1,126 of 11,502 game-channel messages in our own
corpus, 9.8%, and is worse against live-shaped traffic where `0x8009` alone is 19.3%
of game c2s. Both exist for the same reason: a server that stays quiet about what it
did NOT do looks exactly like a client that did nothing.

WHAT STAYED IN `authsrv.py`, and both halves matter. The call sites did: D9(a)'s
catch-all `else` on both dispatch chains, the `finally` that prints the two
disconnect summaries on a connection reset, and `world_tick`'s poll of the 5 s
timer. The five constants did too, and they arrive here as PARAMETERS spelled
exactly as `authsrv.py` spells them -- `PING_SECONDS` is `global`-rebound by
`--ping-seconds`, `AUTH_CMSG_MASK` is read as a literal `NAME = value` line by
`test_cmsgnames.py`, and a value bound as a default at `def` time here would freeze
whichever number this module happened to be imported with.

TAPE SAFETY IS NOT LOCAL TO THIS FILE. `ping_tick`'s docstring below states the
property; its referents stayed behind, so this is the pointer. `world_tick`, which
owns the timer, and `TAPE_EVENTS`, which gates the thread that starts it, both live
in `authsrv.py`, and `test_ping.py` section 8 asserts that gate structurally against
that file's syntax tree. A tape run requires ZERO messages of our own on the channel.

Standard library only, and no import of the server: this module is imported BY
`authsrv.py`, never the other way round.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import labelrun  # noqa: E402


def ping_tick(send, state, conn_id, PING_SECONDS,
              GAME_SMSG_CLIENT_PERF_REQUEST):
    """Send `0x000C` every PING_SECONDS. Called from the world tick.

    First leg of the three-message round trip: server `0x000C` (empty) ->
    client `0x0009` (its perf state) -> server `0x000D[elapsed_ms]`, which the
    client plots on its net graph. studies/smsg established the whole exchange
    from the client's own handler table; the parts that constrain THIS function
    are that the cadence is 5.000 s and that the message carries nothing at all
    -- 2 bytes, header only, per `schema/messages.json`.

    ONE OUTSTANDING PING AT A TIME. The corpus is 79/79 requests answered
    inside their own 5 s window and 0/79 replies unprompted, so the client
    never queues these. We stamp `ping_sent` and do NOT overwrite it while a
    reply is outstanding: if the client is late or silent, sending a second
    request would move the start time and make the eventual round trip read
    SHORTER than it was. A latency meter that under-reports when the link is
    bad is worse than one that reports nothing.

    TAPE-SAFE BY CONSTRUCTION, and worth stating because it is not local: this
    runs only inside `world_tick`, and `world_tick` is started only when
    `TAPE_EVENTS is None`. Its partner is safe the same way -- under a tape the
    game c2s chain `continue`s before any arm, so nothing of ours answers the
    client's `0x0009` either. That matters more than it looks: a tape run
    requires ZERO messages of our own on the channel, and PLAN.md §3.4 records
    a run whose client assert was un-attributable precisely because our 20 Hz
    ticker was talking over ArenaNet's recording. A 5 s timer would have been a
    slower, subtler version of the same contamination.
    """
    now = time.perf_counter()
    last = state.get("ping_at")
    if last is not None and now - last < PING_SECONDS:
        return
    state["ping_at"] = now
    if state.get("ping_sent") is None:
        # No reply outstanding: this is a fresh round trip, so start the clock.
        state["ping_sent"] = now
    else:
        # Previous request never answered. Keep the ORIGINAL start time so the
        # eventual 0x000D tells the truth, and count the miss for the operator.
        state["ping_missed"] = state.get("ping_missed", 0) + 1
    send(GAME_SMSG_CLIENT_PERF_REQUEST, [], "CLIENT_PERF_REQUEST", quiet=True)


def handle_perf_report(values, send, state, conn_id, LATENCY_MAX_MS,
                       GAME_SMSG_LATENCY_REPORT):
    """Answer the client's `0x0009` with `0x000D[elapsed_ms]`.

    The reply's two dwords are the client's own GrPerf frame interval and an
    FrApi flag; they carry nothing from our request and we do not yet know what
    to do with them, so they are recorded and not acted on. What we owe back is
    the elapsed time since OUR `0x000C`, which is what the client graphs.

    UNPROMPTED REPLIES ARE DROPPED. 0 of 79 in the corpus lacked a request
    within 1.0 s before them, so a reply with no outstanding request is not a
    thing this protocol does -- inventing an elapsed time for one would put a
    fabricated number on the net graph, which is the one place an operator
    would read it as measured.
    """
    sent_at = state.get("ping_sent")
    if sent_at is None:
        print(f"[c{conn_id}] CLIENT_PERF_REPORT with no request outstanding -- "
              f"dropped rather than answered with an invented latency",
              flush=True)
        return
    state["ping_sent"] = None
    elapsed_ms = int(round((time.perf_counter() - sent_at) * 1000))
    # Negative is impossible from perf_counter, but a clamp at 0 costs nothing
    # and the field is an unsigned dword on the wire.
    elapsed_ms = max(0, elapsed_ms)
    state["ping_last_ms"] = elapsed_ms
    if elapsed_ms > LATENCY_MAX_MS:
        # Above the client's own cutoff this message is dropped on arrival, so
        # sending it would be a no-op that LOOKS like a working feature here.
        print(f"[c{conn_id}] round trip {elapsed_ms} ms exceeds the client's "
              f"{LATENCY_MAX_MS} ms cutoff -- not sending LATENCY_REPORT, the "
              f"client would discard it", flush=True)
        return
    send(GAME_SMSG_LATENCY_REPORT, [elapsed_ms],
         f"LATENCY_REPORT({elapsed_ms} ms)", quiet=True)


def note_unhandled(state, conn_id, channel, opcode, name, rec,
                   AUTH_CMSG_MASK):
    """Record a c2s opcode the schema KNOWS and this server has no arm for.

    studies/divergence D9(a). Both dispatch chains used to end without an
    `else`, so a schema-known opcode with no handler was printed as received
    and then fell off the end of the chain: nothing sent, NOTHING LOGGED AS A
    MISS, socket healthy. Measured over our own corpus that is 19 distinct
    GAME_CMSG opcodes and 1,126 of 11,502 game-channel messages -- 9.8% --
    and against live-shaped traffic it is worse, since `0x8009` alone is 19.3%
    of live game c2s. The cost of the silence is not the missing feature; it
    is that the missing feature is INVISIBLE, so "the client did nothing" and
    "we ignored what the client did" look identical in the log.

    Deliberately NOT an error and NOT a disconnect. Unhandled-but-known is the
    normal state of most of the catalog today -- 194 layouts against nine
    handlers -- so treating it as a fault would make every session look broken
    and train the operator to ignore the loudest thing in the log. D9(b) is the
    one that ends connections, and it is a different case: an opcode the schema
    does not contain at all cannot be framed past safely.

    First occurrence per connection prints; the rest are counted and reported
    once at disconnect. That split is the point -- printing every one buries
    the log (0x8009 arrives every 5 s, and movement opcodes far faster than
    that), while printing none is the defect being fixed. A labelled run
    suppresses the echo for the same reason the decoded line does: the operator
    is reading a countdown in that terminal.
    """
    seen = state.setdefault("unhandled", {})
    key = (channel, opcode)
    first = key not in seen
    seen[key] = seen.get(key, 0) + 1
    if first:
        if not labelrun.ACTIVE:
            print(f"[c{conn_id}] UNHANDLED {channel} "
                  f"0x{opcode | AUTH_CMSG_MASK:04x} {name} -- schema knows it, "
                  f"this server has no arm for it (D9(a); first occurrence, "
                  f"further ones counted)", flush=True)
        if rec is not None:
            rec.event("unhandled", channel=channel, opcode=opcode, name=name)


def report_unhandled(state, conn_id, rec, AUTH_CMSG_MASK):
    """Print the D9(a) tally once, at disconnect. Silent when there is none."""
    seen = state.get("unhandled") or {}
    if not seen:
        return
    total = sum(seen.values())
    parts = ", ".join(
        f"0x{op | AUTH_CMSG_MASK:04x}x{n}"
        for (_ch, op), n in sorted(seen.items(), key=lambda kv: -kv[1]))
    print(f"[c{conn_id}] unhandled-but-known c2s this session: {total} messages "
          f"over {len(seen)} opcodes -- {parts}", flush=True)
    if rec is not None:
        rec.event("unhandled_summary", total=total, opcodes=len(seen),
                  counts={f"{ch}:0x{op:04x}": n for (ch, op), n in seen.items()})


def report_ping(state, conn_id, rec=None):
    """Say how the round trip went, once, at disconnect. Silent if never used.

    `ping_missed` counts requests that were still outstanding when the next one
    fell due. Counting it and never printing it would be the D9(a) defect in
    miniature -- a number the server knows and the operator cannot see.
    """
    if state.get("ping_at") is None:
        return
    missed = state.get("ping_missed", 0)
    last = state.get("ping_last_ms")
    print(f"[c{conn_id}] net graph: last round trip "
          f"{'--' if last is None else str(last) + ' ms'}"
          f"{f', {missed} request(s) went unanswered' if missed else ''}",
          flush=True)
    if rec is not None:
        rec.event("ping_summary", last_ms=last, missed=missed)
