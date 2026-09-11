"""Two scripted sequences played at scripted timing, each on its own thread.

A pre-encrypted TAPE -- a recorded server's plaintext replayed into a live client
at the recording's own segment timing -- and a PROBE's Step list, a scripted
experiment whose steps are deliberately seconds apart so a person can see one
result before the next arrives. Both run off the receive thread because the
receive loop has to keep running throughout or the client times out mid-sequence,
and both swallow their failures and print them: a packet the client rejects is a
result, not a crash.

Nothing here owns a flag or an opcode. `authsrv.py` keeps the two call sites
(both inside `handle()`), keeps the `--tape-*` and `--probe` arguments and their
globals, and hands this module the two values it cannot see from here:

    play_tape(..., codec)              the module-level `Codec()` in authsrv.py
    run_probe(..., PLAYER_AGENT_ID)    the reserved id `probes.get` builds against

-- passed at CALL time by the wrappers that stand where these functions used to,
never imported, because a leaf that imports `authsrv` loads a second copy of the
server whose flags `main()` never set.

`tape.py` is imported INSIDE `tape_transfer_present`, not at module scope, and
that placement is load-bearing: `test_bareimport.py` imports the server with
`RURIK_VAULT` aimed at a directory that does not exist.

Standard library plus `probes`; no vault, no socket of its own, no content read.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bisect                                                   # noqa: E402
import socket                                                   # noqa: E402
import threading                                                # noqa: E402
import time                                                     # noqa: E402

import probes                                                   # noqa: E402


def play_tape(send_raw, conn_id, stop, events, info, speed, codec):
    """Play a recorded server's plaintext into a live session, at recorded timing.

    R1.5. Runs on its own thread for the same reason a probe does: the receive loop
    must keep running throughout or the client times out mid-tape, and the tape is
    48 seconds long.

    THE PREDICTION IS STATED HERE rather than in a commit message, because this is
    an experiment and the house rule is that a probe with no stated expectation can
    be rationalised into agreeing with whatever happened:

      * PREDICTED, and CONFIRMED 2026-08-10: the client loads the recorded map and
        draws its agents. It did far more than that -- 1,209 of 1,209 events with
        zero messages of ours on the channel, and the client skipped the cutscene,
        walked to each quest giver in order, spoke to them, accepted quests and
        walked to the zone exit. Chat arrived. RUN, POSITIVE.
      * THE INFORMATIVE FAILURE, which did NOT happen and is therefore the result:
        an assert naming a player-identity field. THE CLIENT DOES NOT CHECK. The tape
        names the RECORDED character -- an 11-character name in 0x017D and in the
        player's 0x0059 row, player number 26, agent 725, plus 40 other players --
        and the client logged in as ours. Whether it cross-checks the identity it
        SENT against the one it is TOLD about was UNVERIFIED; it is now OBSERVED
        that it does not. Nothing was renamed for the run, so this is the honest
        answer rather than one obtained by sneaking past a check.
      * NOT PREDICTED, and out of scope: control. The tape's 987 move messages
        answer the RECORDED operator's clicks, so the avatar walks the recorded path
        whatever the new operator does, and client-side prediction will fight it. A
        tape shows a load and a populated world; it cannot show control.
      * RUN 2, 2026-08-10, Lakeside County (`:64103`): 1,074/1,074, zero of ours on
        the channel, and IT RENDERED COMBAT -- the recorded operator's fight with a
        Wolf, Vampiric Gaze and Deathly Swarm, played back into a client that had no
        server behind it. Also OBSERVED there: the client drew map 146 while its own
        VERSION had asked for 148, so the identity result above generalises to the
        map id. studies/tape/FINDINGS.md is the log; read it before the next run,
        because two of its findings are about how to READ a run rather than what one
        found -- the recorded avatar stands still for the last 146 s of that tape and
        looks finished, and `--map` is inert here.

    Pacing is per WIRE SEGMENT, not per message, because that is the resolution the
    capture has -- 1,209 timing points for 3,981 messages on the Ascalon tape. Drift
    is corrected against a fixed origin rather than accumulated per sleep, so a slow
    send cannot stretch the whole tape.
    """
    bar = "=" * 62
    print(f"\n{bar}\nTAPE: {info['connection']}\n"
          f"  {info['events']:,} events, {info['bytes']:,} B, {info['seconds']:.1f}s"
          f"{'' if speed == 1.0 else f' at {speed}x'}\n"
          f"  from {info['capture']} ({info['origin']})\n"
          f"  PREDICTS: the client loads the recorded map and draws its agents.\n"
          f"  The informative failure is an assert naming a player-identity field --\n"
          f"  the tape names the RECORDED character, not the one that logged in.\n{bar}",
          flush=True)
    t0 = time.monotonic()
    sent = 0
    try:
        for i, (t, blob) in enumerate(events):
            if stop.is_set():
                print(f"[c{conn_id}] tape stopped at event {i}/{len(events)}", flush=True)
                return False
            due = t0 + (t / speed if speed else 0.0)
            now = time.monotonic()
            if due > now:
                time.sleep(due - now)
            send_raw(blob, f"tape[{i}]")
            sent += 1
            if i and i % 200 == 0:
                print(f"[c{conn_id}] tape {i}/{len(events)} "
                      f"({time.monotonic() - t0:.1f}s)", flush=True)
    except (ConnectionError, OSError) as ex:
        # The client dropped, or asserted and took the socket with it. That is THE
        # RESULT of this experiment, not a crash to swallow -- so say exactly what
        # was in flight when it happened. The client's own assert names a source
        # file and line; this names the bytes that provoked it, and the pair is
        # what turns a crash into a finding.
        #
        # OBSERVED 2026-08-10: the client died at event 739/1209, t=22.4s, and the
        # two events either side of that were the largest in the neighbourhood --
        # 229B and 209B carrying WORLD_CREATE_AGENT plus equipment and property
        # updates, i.e. another player zoning into the outpost. Without this
        # readout that had to be reconstructed afterwards from the tape by hand.
        print(f"\n[c{conn_id}] TAPE ENDED at event {sent}/{len(events)} "
              f"after {time.monotonic() - t0:.1f}s: {type(ex).__name__}: {ex}",
              flush=True)
        lo = max(0, sent - 3)
        # DO NOT CALL THIS A CLIENT ASSERT. This banner used to open "the client
        # asserts on one of these", and on 2026-08-10 it said that about a tape whose
        # client was in perfect health: the HARNESS had reached its verdict target and
        # torn the stack down 1.7s into a 396-second chain, so the socket died under a
        # tape that had barely started. Everything on screen read as crash-on-map-load,
        # and the only thing that contradicted it was the absence of an Assertion line
        # in the client's own log.
        #
        # This end of the socket cannot tell a client assert from a shutdown, so it
        # says both and names the one check that separates them.
        print(f"[c{conn_id}] the client's connection went away. That is EITHER a client "
              f"assert on one of the events below, OR the stack being shut down "
              f"(--keep-open / --hold, or a verdict target already reached).",
              flush=True)
        # CORRECTED 2026-08-11. This used to say "Gw.log decides it: an Assertion
        # line means the client; no Assertion line means the teardown." Gw.log
        # does NOT record asserts -- it is a perf/error log, and a run that
        # asserted at 01:10:56 that day has no Assertion line in it. So that
        # check could never fire, and a conclusion drawn from it on 2026-08-10
        # (that a tape's client was healthy) rested on nothing.
        print(f"[c{conn_id}] The client's ERROR DIALOG decides it, and nothing else "
              f"does: Gw.log carries no asserts, no dump file is written anywhere "
              f"findable, and a reset here happens on clean teardowns too. "
              f"session.py captures the dialog automatically into the run "
              f"directory as crash-dialog.txt; standalone, use "
              f"toolkit/harness/read_error_dialog.py.", flush=True)
        # Frame the tape ONCE, then group each message under the event its FIRST byte
        # falls in. This used to decode each event on its own, which is wrong in the one
        # place a wrong answer costs the most: a tape event is a TCP segment, a message
        # can straddle two, and the event after a straddle begins mid-message -- so its
        # leading bytes framed as whatever opcode they happened to spell. This readout
        # exists to name the bytes that killed the client, and naming an opcode the wire
        # never carried is worse than naming none. Corpus-wide the old idiom lost 19% of
        # messages and invented 117; `tape.decode_all` carries the measurement.
        ends, at = [], 0
        for _t, b in events:
            at += len(b)
            ends.append(at)
        per_event, framed_to = {}, 0
        try:
            framed, framed_to, _e = codec.decode_stream_at(
                "GAME_SMSG", b"".join(b for _t, b in events))
        except Exception:
            framed = []
        for off, op, _v in framed:
            per_event.setdefault(bisect.bisect_right(ends, off), []).append(op)

        for j in range(lo, min(sent + 2, len(events))):
            et, eb = events[j]
            here = per_event.get(j, [])
            ops = " ".join(f"0x{op:04x}" for op in here[:10])
            more = "..." if len(here) > 10 else ""
            if not here:
                # An event with no message of its own has two possible causes and they
                # are not the same news, so do not print one label for both. Either it
                # holds only the tail of a message that began earlier, or the stream
                # stopped framing before reaching it -- and the second is a finding.
                # MEASURED 2026-08-11: the first case happens in NONE of the ten
                # recorded tapes, because it needs a message longer than a whole
                # segment and these do not have one. The branch is for a tape whose
                # segmentation is not ArenaNet's, not for the ordinary case.
                ops = eb[:12].hex(" ")
                more = (" (continues the previous event)"
                        if ends[j] <= framed_to else
                        f" (UNFRAMED -- the tape stopped framing at byte {framed_to:,})")
            flag = "  <<< LAST SENT" if j == sent - 1 else ""
            print(f"[c{conn_id}]   ev{j} t={et:.2f}s {len(eb)}B  {ops}{more}{flag}",
                  flush=True)
        print(f"[c{conn_id}] re-run with --tape-speed 0.25 to spread these out, or "
              f"copy the client's Assertion line -- it names the source file.",
              flush=True)
        return False
    print(f"[c{conn_id}] tape complete: {sent}/{len(events)} events in "
          f"{time.monotonic() - t0:.1f}s", flush=True)
    return True


# A tape that ends in a handoff must end the CONNECTION too, and this is not tidiness.
#
# MEASURED in the recording: the server closes immediately after sending 0x01A5 --
# connection :62994 closes at t=213.70 and :64102 opens at t=213.84, a 0.140 s gap, and
# the same shape at every transition (0.137 s, 0.118 s). The recorded server hangs up.
# Our player did not: it ran out of events and sat on the socket.
#
# WHY THAT MATTERS, from the client's own code (build 38797). The 0x01A5 handler at
# 0x0084f290 branches on bit 0x20 of a flags dword at +0x190:
#
#     mov  eax, [esi + 0x190]
#     test al, 0x20
#     je   0x84f359          <- clear: call 0x850df0 and DIAL NOW
#     or   eax, 0x10         <- set:   stash the sockaddr, mark pending, RETURN
#
# and the connect function 0x850df0 SETS that bit itself (`or [ebx+0x190], 0x20` at
# 0x00850e56, same function body, no ret in between). So the FIRST game-channel
# transfer of a session dials immediately and every LATER one defers, waiting for the
# connection it already has to go away.
#
# OBSERVED 2026-08-10, and it is exactly that shape: hop 1 -> hop 2 dialled at once
# (hop 1's own connection came from the AUTH handoff, so bit 0x20 was still clear), and
# hop 2 -> hop 3 never dialled at all -- correct destination on screen, correct alias in
# the client's overlay, no SYN, auth channel still heartbeating. One transfer per
# session worked and the next hung, which is the signature of a deferred dial whose
# trigger never fired.
# How long to keep reading after our FIN before giving up on a clean two-way close.
# The client answers within milliseconds when it is healthy; this only bounds the
# case where it does not.
GRACEFUL_CLOSE_SECONDS = 2.0


def close_after_transfer(sock, events, codec_obj, conn_id):
    """Hang up if this tape ended by handing the client somewhere else.

    Returns True if the socket was closed. Deliberately keyed on the tape CONTAINING a
    transfer rather than on a flag: a tape that stays in its map (the last hop, or any
    --tape-no-transfer run) must NOT be hung up on, because the whole point of those is
    that the client keeps playing afterwards.
    """
    if tape_transfer_present(events, codec_obj) is None:
        return False
    print(f"[c{conn_id}] tape ended in a handoff -- closing the connection GRACEFULLY, "
          f"which is what the recorded server did (0.14s before the client re-dialled).",
          flush=True)
    # HOW we close decides whether the client reconnects, and the first version of this
    # got it wrong. The client's disconnect path branches on a reason code at [esi+0xc]:
    # reason 0 falls through to `call 0x850df0` at 0x008515b7 and RE-DIALS the stashed
    # address; reason >= 3 pops and returns, doing nothing; reason 7 is special-cased.
    # So a deferred transfer is only released by the disconnect the client considers
    # clean.
    #
    # shutdown(SHUT_RDWR) followed by close() is NOT that. With bytes still unread in the
    # receive buffer -- and there always are, the client keeps sending 0x8008/0x800c
    # after the tape ends -- Windows answers with an RST rather than a FIN. That is a
    # different reason code, and it is why hanging up twice released nothing.
    #
    # So: half-close (send FIN, keep reading), drain what the client is still sending
    # until it closes its half or a short deadline passes, and only then close. That is
    # an ordinary graceful shutdown and it is what the recording shows.
    try:
        sock.shutdown(socket.SHUT_WR)
    except OSError:
        pass
    drained, deadline = 0, time.monotonic() + GRACEFUL_CLOSE_SECONDS
    try:
        sock.settimeout(0.25)
        while time.monotonic() < deadline:
            chunk = sock.recv(4096)
            if not chunk:
                break               # the client closed its half: a clean FIN both ways
            drained += len(chunk)
    except (OSError, socket.timeout):
        pass
    try:
        sock.close()
    except OSError:
        pass
    print(f"[c{conn_id}] closed after draining {drained} B -- an unread receive buffer "
          f"turns close() into an RST, and the client only re-dials on the reason code "
          f"a clean shutdown produces.", flush=True)
    return True


def tape_transfer_present(events, codec_obj):
    """The handoff in this tape, or None. Thin wrapper so authsrv owns no tape logic."""
    import tape as tapemod
    try:
        return tapemod.transfer_of(events, codec_obj)
    except Exception:
        return None


def run_probe(name, send, conn_id, stop, origin, PLAYER_AGENT_ID):
    """Fire a scripted experiment at the client, on its own thread.

    On its own thread because the steps are deliberately seconds apart -- a
    person has to see one result before the next arrives -- and the receive loop
    must keep running throughout or the client times out mid-probe.

    Failures are printed and swallowed. A probe is an experiment; a packet the
    client rejects is a result, not a crash, and it must not take the session
    down with it or we lose the rest of the sequence.

    A step that declares `sends=False` is a REFUSAL and is not sent. That flag was
    added for `probes.check_encodable` on 2026-08-13 and this loop -- the one that
    puts bytes on a socket -- was not taught about it for the rest of the day, which
    fails in BOTH directions. When the codec raises (the empty smsgsweep plan's
    refusal is `0x0000` with no values, and 0x0000 wants one) the swallow above
    prints `SEND FAILED ... that is a result too -- record it`, filing "there was no
    plan" as an experimental result and `continue`ing PAST the `watch` line that
    says what actually happened -- so the one message the step exists to carry is
    the one thing the operator does not see. And when the codec does NOT raise -- a
    refusal built on any opcode whose fields the degenerate encoder can fill -- the
    packet goes on the wire underneath the words "nothing was sent". The second is
    worse: it is a lie printed beside the bytes that contradict it.

    Returns the Thread so a caller can join it. The live call site does not; the
    suite does, because the alternative is a test that sleeps and hopes.
    """
    # origin is where the character is standing. A probe that places something
    # in the world needs it, and can only have it from here -- probes.py is a
    # data module with no view of the session.
    probe = probes.get(name, PLAYER_AGENT_ID, origin)
    if probe is None:
        print(f"[c{conn_id}] no probe named {name!r}; "
              f"known: {', '.join(probes.names())}", flush=True)
        return

    def body():
        bar = "=" * 62
        print(f"\n{bar}\nPROBE: {name}\n  Q: {probe.question}\n"
              f"  predicts: {probe.predicts}", flush=True)
        if probe.note:
            print(f"  note: {probe.note}", flush=True)
        if not probe.steps:
            print(f"  (no packets -- observation only)\n{bar}\n", flush=True)
            return
        for i, step in enumerate(probe.steps, 1):
            if stop.wait(step.delay):
                return
            print(f"\n  --- step {i}/{len(probe.steps)}: {step.label}",
                  flush=True)
            if not getattr(step, "sends", True):
                # Declared refusal -- see this function's docstring. It is a DECLARED
                # flag and never `if not step.values`, because a malformed step with
                # no values is exactly what the encoder check exists to catch and the
                # two are indistinguishable by shape (probes.Step's docstring).
                #
                # Without this arm the refusal reached `send(0x0000, [])`, which raises
                # and lands in the handler below as "SEND FAILED" -- the correct outcome
                # (nothing went on the wire) reported as a malfunction, with the one
                # sentence the operator needed buried under a traceback name. The
                # alternative considered and rejected was returning NO steps, which the
                # runner already prints as "observation only": silent in the wrong
                # direction, since a probe that measures nothing because its plan ran
                # out would then look identical to one designed to send nothing.
                #
                # (Two sessions fixed this independently on 2026-08-13 and reached the
                # same arm. This comment is the union of both; the print text is the
                # one `test_agentlife` asserts on.)
                print(f"      REFUSAL -- no packet sent. {step.watch}", flush=True)
                continue
            try:
                send(step.opcode, step.values, f"PROBE[{name}] {step.label}")
            except Exception as exc:
                print(f"      SEND FAILED: {type(exc).__name__}: {exc}",
                      flush=True)
                print(f"      (that is a result too -- record it)", flush=True)
                continue
            print(f"      WATCH: {step.watch}", flush=True)
        print(f"\n  probe complete. What did you see?\n{bar}\n", flush=True)

    thread = threading.Thread(target=body, daemon=True)
    thread.start()
    return thread
