"""Watching the client while it runs: photograph it only when it owns the
foreground, read its crash dialog, hold it open past the verdict, and take the
PASS back if it died.

Lifted out of `session.py` unchanged. Every comment below is the record of a run
that reported the wrong thing, and three of them are about a client that had
already asserted while the harness printed RUN VERDICT: PASS -- so the comments
are the evidence, not decoration, and they travel verbatim.

THE REFERENTS THAT STAYED BEHIND. `walk_legs` (the other retraction, for a client
that dies BETWEEN steps), `run_client` (the `finally` that calls
`capture_error_dialog` a second time with a shorter wait, and the call site that
consumes `hold_open`'s return) and `main` (`--keep-open`, whose `finally` used to
stop the servers out from under the client) are all still in `session.py`, which
re-exports all four names here.

That re-export is load-bearing rather than tidy. `test_harness.py` reads this
code through `inspect.getsource(session.hold_open)`, reaches this module's
`verdict_after_hold` through `getattr(session, "verdict_after_hold", None)`, and
monkeypatches a fake `read_error_dialog` into `sys.modules` around
`session.capture_error_dialog` -- which works only because that import is
FUNCTION-LOCAL, below, and must stay there. `shot_if_foreground` is called five
times BEFORE the verdict as well as during the hold, so "what happens after the
verdict" is the wrong subject for this file and is how something gets mis-filed
here later.
"""
import ctypes
import os
import sys
import time
from ctypes import wintypes

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLKIT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, TOOLKIT)
import drive_client as dc  # noqa: E402


def shot_if_foreground(hwnd, pid, path):
    """Screenshot only when the client actually owns the foreground.

    ImageGrab captures a REGION OF SCREEN, not a window: shot taken while
    another window covers the client photographs that window instead. The
    first harness run filed a screenshot of the owner's Discord as the
    client's final state. No screenshot beats a screenshot of the wrong thing.
    """
    fg = dc.user32.GetForegroundWindow()
    owner = wintypes.DWORD()
    dc.user32.GetWindowThreadProcessId(fg, ctypes.byref(owner))
    if owner.value != pid:
        print(f"  [shot] skipped {os.path.basename(path)}: client not foreground")
        return None
    return dc.shot(hwnd, path)


def hold_open(proc, seconds, tails, outdir, quiet=False, shot_every=0.0):
    """Keep the whole session alive past the verdict, and stay instrumented.

    WHY THIS IS NOT `--keep-open` ON ITS OWN. `--keep-open` used to spare the
    client and let main()'s `finally` stop the servers anyway. The client's
    only peer was those servers, so it dropped the connection and fell back to
    character select with "Your connection to the server was lost. (Code=007)".

    That mattered because everything interesting happens AFTER the verdict. A
    --probe fires seconds after the spawn rung the verdict is read at, so the
    stack was being killed in the gap between arming an experiment and running
    it. The symptom was the worst kind: a client still up, still responding,
    with no assert dialog -- indistinguishable from a probe that ran and found
    nothing. This project has been wrong about absences produced by instruments
    that were not running three times already, and that is four.

    So the hold blocks HERE, inside the run, rather than orphaning the stack:
    the log pumps are daemon threads on this process, so an exit would stop the
    gamesrv log at exactly the line before the interesting one.

    Ends early when the client exits, which is what a crash looks like -- there
    is no point holding a session whose client is a fatal-error dialog.
    """
    end = time.monotonic() + seconds if seconds else None
    where = f"{seconds:.0f}s" if seconds else "until the client exits"
    print(f"\n--keep-open: stack and client stay up ({where}). "
          f"Ctrl-C stops both.")
    if shot_every > 0:
        print(f"  --shots: a screenshot every {shot_every:.0f}s into {outdir}")
    last, last_shot, shots = 0.0, 0.0, 0
    while proc.poll() is None and (end is None or time.monotonic() < end):
        time.sleep(0.5)
        for t in tails.values():
            t.poll()                 # keep the capture flowing during the hold
        now = time.monotonic()
        # OBSERVED 2026-08-11: the operator saw the floor and the character
        # models vanish while backing into a wall, and did not photograph it
        # because reaching for a screenshot key means letting go of the input
        # that produces it. An intermittent visual fault that only a human can
        # provoke needs a camera the human is not holding.
        if shot_every > 0 and now - last_shot >= shot_every:
            last_shot = now
            hwnd, _ = dc.find_window(proc.pid)
            if hwnd:
                shots += 1
                shot_if_foreground(hwnd, proc.pid,
                                   os.path.join(outdir, f"hold{shots:03d}.png"))
        if now - last >= 15:
            last = now
            if quiet:
                # A labelled run owns this terminal and prints its own progress.
                # A "...holding" every 15s lands in the middle of a 9s step's
                # prompt and reads, to the operator, like the thing they are
                # supposed to be reading. Silence here is the useful output.
                continue
            left = f"{end - now:.0f}s left" if end else "holding"
            print(f"  ...{left}", flush=True)
    if proc.poll() is not None:
        # A client that left on its own is a result, not a timeout. The assert
        # text is in its dialog if there is one; read_error_dialog.py gets it
        # without pressing "Send report to ArenaNet".
        print(f"  client exited with code {proc.returncode} during the hold")
        capture_error_dialog(outdir)
        # AND THAT RETRACTS THE VERDICT TOO. walk_legs already retracts when the
        # client dies BETWEEN steps, but a client can also die after the last
        # step -- E1d's control did exactly that, and the run still printed
        # RUN VERDICT: PASS over a client that had asserted on Array.h:587. The
        # verdict is read before the walk; a corpse afterwards unmakes it.
        return "exited"
    else:
        # AND THE HOLD RUNNING OUT IS NOT PROOF OF LIFE. This branch is here
        # because on 2026-08-11 the harness printed RUN VERDICT: PASS on a run
        # where the client had asserted -- `CharPool.cpp:84 fraction <= 1.0f`,
        # two seconds after the first kill this server ever drove to a revive.
        # A Guild Wars assert puts up a MODAL DIALOG AND KEEPS THE PROCESS
        # ALIVE waiting for a click, so `poll()` stays None, the hold expires on
        # its timer, and the only branch that looks for the dialog never runs.
        # The crash text existed on screen the whole time and the run reported
        # green -- the exact failure the docstring below was written about, from
        # the one direction it did not cover.
        #
        # Short wait: we are not expecting a dialog here, only checking. Silent
        # when there is none, because most holds end this way.
        capture_error_dialog(outdir, wait=1.0, quiet=True)


def verdict_after_hold(ok, hold_result):
    """Fold the hold's outcome into the run verdict. It may only ever REMOVE a pass.

    THIS FUNCTION EXISTS BECAUSE THE RETURN ABOVE USED TO GO NOWHERE. `hold_open`
    has returned "exited" for a client that died during the hold since 97f681a --
    the portal commit -- and the comment at that `return` says "a corpse
    afterwards unmakes it". It did not: the only call site was a bare expression
    statement, `ok` was never reassigned after it, and a run whose client
    asserted during the hold still printed RUN VERDICT: PASS and exited 0.
    `customarea/FINDINGS.md` 31.4 recorded the defect as FIXED on the strength of
    that `return`. The statement shipped; the wiring did not.

    So the rule lives in a pure function with a truth table in `test_harness.py`
    rather than inline at the call site, and the test also asserts STRUCTURALLY
    that `run_client` consumes `hold_open`'s value -- because a correct helper
    nobody invokes is precisely the bug being fixed, and it would otherwise look
    identical from here.

    Retraction only. A hold cannot turn a failed run green: the verdict is read
    before the walk and says something true about the spawn, and the hold can
    only add bad news.
    """
    return bool(ok) and hold_result != "exited"


def capture_error_dialog(outdir, wait=12.0, quiet=False):
    """Read the client's fatal-error dialog into the run's own report.

    WHY THIS IS AUTOMATIC AND USED NOT TO BE. Until 2026-08-11 the harness
    printed "read the dialog with read_error_dialog.py" and stopped there. That
    is a hint aimed at a human who happens to be watching, and it fails in the
    two cases that matter: an unattended run has nobody to read it, and by the
    time anyone does the dialog can be gone. The cost was measured on
    2026-08-11 -- an evening spent guessing at a client assert whose text
    existed the whole time on the operator's screen and nowhere else.

    THE THREE THINGS THAT DO NOT WORK, so nobody re-tries them: `Gw.log` does
    NOT record asserts (it is a perf/error log -- a run that asserted at
    01:10:56 has no Assertion line in it, and authsrv.py told sessions to use
    exactly that as the decider); no dump file is written anywhere findable
    despite the dialog naming one; and ConnectionResetError in the gamesrv log
    appears on a clean teardown as readily as on a crash. This dialog is the
    only machine-readable evidence a client assert leaves.

    THE PROCESS IS NOT NECESSARILY GONE. This used to be called only after
    poll() reported an exit, and said so -- but a Guild Wars assert keeps the
    process ALIVE behind a modal dialog, so that call site could not see the
    case it most needed to. It is now called on both exits from the hold, which
    is also why it enumerates rather than reusing the handle we had: on the
    crashed-but-running path the dialog belongs to the client we launched, and
    on the exited path it belongs to some other Gw process.

    `quiet` suppresses the no-dialog line for the polling call, where finding
    nothing is the normal case rather than a result.

    READ ONLY, and that is a safety property rather than a style choice. The
    dialog's default button is "Send report to ArenaNet", which would upload a
    crash dump FROM A PATCHED CLIENT to the vendor. Nothing here may click.
    """
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import read_error_dialog as red
    except Exception as ex:                                    # pragma: no cover
        print(f"  (could not load read_error_dialog: {ex})")
        return None

    # FIRST CAPTURE WINS. This is called twice on a --keep-open run -- once from
    # hold_open with a 12 s look, then again from run_client's finally with a
    # 2 s one -- and the first had the better chance of catching a dialog that
    # is on its way up. Re-reading is harmless but re-WRITING a shorter look
    # over a longer one is not.
    path = os.path.join(outdir, "crash-dialog.txt")
    if os.path.exists(path):
        return path

    deadline = time.monotonic() + wait
    found = []
    while time.monotonic() < deadline:
        pids = red.gw_pids()
        if pids:
            found = red.dump(pids)
            if found:
                break
        time.sleep(0.5)
    if not found:
        if not quiet:
            print(f"  no error dialog within {wait:.0f}s -- the client exited "
                  f"WITHOUT one, which is a clean exit rather than a silent crash")
        return None

    with open(path, "w", encoding="utf-8") as fh:
        for hwnd, title, blocks in found:
            fh.write(f"=== window {hwnd:#x}  title={title!r}\n")
            for cls, text in blocks:
                fh.write(f"--- control class={cls}  ({len(text)} chars)\n{text}\n")

    # Surface the line that names the fault. The dialog's long control holds the
    # whole report and the assert record is at the TOP of it -- which is exactly
    # the part a screenshot of a scrolled view misses, and why screenshots gave
    # three runs in a row nothing but the tail of Gw.log.
    assert_line = None
    for _hwnd, _title, blocks in found:
        for _cls, text in blocks:
            for ln in text.splitlines():
                if "Assertion:" in ln or "Exception:" in ln:
                    assert_line = ln.strip()
                    break
            if assert_line:
                break
        if assert_line:
            break
    print(f"  ERROR DIALOG captured -> {path}")
    if assert_line:
        print(f"  >>> {assert_line}")
    return path
