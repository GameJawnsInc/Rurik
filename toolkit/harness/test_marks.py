"""Prove `marks.py` reads the keyboard, never writes it, and puts a mark on wire time.

    python toolkit/harness/test_marks.py
    python toolkit/harness/test_marks.py --module <path>   # run against a sabotage

No vault, no socket, no client, no Windows. Every hotkey check runs against a FAKE
`user32` the way `test_harness.py` fakes one for `hold_key`, and every clock is injected
the way `wirecapture.open_capture` already takes one -- so this file measures the real
module on any platform. That is the shape `test_keytap.py` could not have: it skips whole
off Windows because `keytap.py` binds `ctypes.wintypes` at import. `marks.py` was written
not to, and this file is what makes that worth the trouble.

WHAT §8.9 ASKS FOR, AND WHERE IT IS.

  criterion  bind() returns every mark on wire time and ASSERTS the two-clock
             agreement rather than assuming it                          -- sections 6, 7
  control 1  an edge fires once per PRESS and not once per poll                -- 4
  control 2  the syntax tree contains no SendInput                             -- 5
  control 3  bind() goes red when the two clocks disagree past tolerance       -- 7
  control 4  a mark before t0 is refused                                       -- 8
  control 5  a changed plan file is refused                                    -- 9
  control 6  advancing past the last step is refused                           -- 3

FOUR SECTIONS ARE NOT IN §8.9 AND EACH EXISTS BECAUSE A SKEPTIC PASS BROKE SOMETHING THE
FILE CLAIMED. 4b is the hotkey teardown (five live leak paths against a fake that keeps
its own OS-side ledger); 16 is the THIRD clock channel and the capture's span, which is
where a binding that both clock witnesses call perfect is caught; 17 is the destination
guard this module shipped without, which truncated a 4,096-byte file named off `--out`
before writing a single mark. The fourth is not a section at all: `guarded()` and
`BoundedHotkeys` exist because sixteen of 109 sabotages produced a CRASH or a HANG rather
than a red check, and a floor cannot catch vacuity in a process that never reaches its
verdict.

THE HEADLINE IS SECTION 6 AND IT IS DELIBERATELY NOT "bind() RETURNED SOMETHING".
`t = t_perf - t0_perf` is arithmetic; a binder that got it wrong would still return a
list of plausible seconds. So section 6 does not check the number against a number this
file wrote down -- it builds the wire capture with the REAL `wirecapture.open_capture`,
takes a mark off the SAME clock reading a segment was stamped with, and requires the
bound mark's `t` to equal that segment's own `t` to the bit. Two modules, two epochs,
one answer. If the epoch were dropped, doubled or taken from the marks file instead, the
equality breaks; nothing this test computes can force it.

WHICH CHECKS ARE LOAD-BEARING WAS MEASURED, NOT ASSUMED. Six sabotages were built as
scratch copies of `marks.py` and run through `--module`; the numbers are in the floor
comment. Two of them are worth naming here because they are the ones a plausible
implementation would actually be:

  * `mods=MOD_NOREPEAT` dropped from `RegisterHotKey`. The module still uses the message
    queue, still swallows the key, still never polls -- and a HELD F9 emits one mark per
    wakeup instead of one per press. Nothing structural sees it. Section 4 does, because
    the fake models the OS rule: auto-repeat posts a fresh WM_HOTKEY per wait UNLESS
    MOD_NOREPEAT was passed at registration. The rival is run in the same process on the
    same fake, so "1 against 5" is a difference between two live answers.
  * the drift assertion deleted from `bind()`. Every round trip in this file still
    passes, because those fixtures agree; only section 7's six disagreeing checks redden.
    That is the point of §8.9's criterion -- an unchecked binding is indistinguishable
    from a checked one on data that happens to be fine, so the only thing that can tell
    them apart is a fixture built to disagree.

THE THREE WAYS SECTION 5 ASKS ABOUT `SendInput`, AND WHAT EACH ONE MISSES. This is the
line the live-automation rule turns on -- `drive_client.hold_key` is the other side of it
-- so one detector is not enough:

  1. the SYNTAX TREE (identifiers): every `ast.Attribute.attr` and `ast.Name.id`. Catches
     `user32.SendInput(...)`. MISSES `getattr(u, "SendInput")`, and misses anything whose
     name is computed.
  2. non-docstring STRING CONSTANTS. Catches `getattr(u, "SendInput")`. MISSES
     `getattr(u, "Send" + "Input")`, where no constant is the name.
  3. a POSITIVE WHITELIST plus a ban on dynamic lookup: the only things fetched off the
     handle -- by ATTRIBUTE or by SUBSCRIPT, through the name `user32` or through an
     ALIAS of it -- are the four `Hotkeys` documents, and the module contains none of the
     twenty spellings in `DYNAMIC_LOOKUP`. This is the one that catches (2)'s blind spot.

  THAT THIRD PARAGRAPH USED TO END "and it is the only one of the three that can", AND
  THE CLAIM WAS FALSE FOR THE GENERAL CASE IT NAMED. Detector 3 was a scan for the
  literal words `getattr`/`setattr` plus a whitelist of attributes fetched off something
  spelled `user32`, so any computed lookup that was neither walked past all three. A
  skeptic built five copies of `marks.py`, each reaching `SendInput` by a different route,
  and ran the whole file against them: two were caught (6 red and 5 red), and THREE
  PASSED ALL 139 CHECKS AND EXITED 0 --

      self.user32["Send" + "Input"](1, None, 28)
      __import__("operator").attrgetter("Send" + "Input")(self.user32)(1, None, 28)
      u = self.user32; u["".join(["Send", "Input"])](1, None, 28)

  -- and `object.__getattribute__` besides. None is exotic: a SUBSCRIPT of a
  `ctypes.WinDLL` resolves a function exactly as an attribute does, verified on a live
  handle where `u["GetSystem" + "Metrics"](0)` returns the same 1920 as `u.GetSystemMetrics(0)`.
  This is the line CLAUDE.md's live-automation rule turns on, so the answer was not only a
  wider scan: `Hotkeys.__init__` now BINDS the four functions and lets the handle go out
  of scope, and section 4 checks on the OBJECT that no attribute holds it. A scan says
  what it noticed; a class with no handle on it says what exists. All three routes are
  kept below as sabotage rows and all three now redden.

  All three are run, plus the naive one for contrast: a RAW grep of `marks.py` for
  "SendInput" finds a hit, and EVERY occurrence of the word in the file is in a
  DOCSTRING -- including the sentence promising there is none. So a grep for the rule
  reddens on the documentation of the rule. That is measured rather than argued:
  `test_cmsgnames.py` shipped a grep that asserted its arm's formatting and went red
  when the arm wrapped across two lines, and `test_sweeploop`'s syntax-tree check exists
  because the grep version reddened on the comment explaining the rule. The claim is
  stated as "every hit is prose" rather than as "there is exactly one hit", because a
  count would redden the day somebody rewords the header while a real call would still
  pass. `drive_client.py` is the positive control: the module on the other side of the
  line must be FLAGGED by detector 1, or the detector is measuring nothing. FOUR
  sabotaged copies of the module under test are built and parsed in every run -- one on
  which each detector is the ONLY one that fires, plus the plain call -- so section 5
  reports which detector caught which, and none of the three is decoration.

SECTION 16 IS THE CHANNEL THIS MODULE SHIPPED WITHOUT, AND IT IS THE ONE THAT SECURES THE
BINDING RATHER THAN THE CLOCKS. `wirecapture.write_mark` has carried three channels all
along and the third is `wire_t` -- the capture's own last `t`, read off the file -- while
`marks.py` kept the two that can only restate each other. A skeptic built a capture whose
published `(t0_perf, t0_wall)` pair was sampled adjacently (so both clocks agree
perfectly) but 0.9 s LATER than the `t0` its segments were stamped from: `bind()` BOUND
it, every mark 0.9 s off its own segment, reporting worst |dperf - dwall| = 0.0001 ms.
And a mark taken an HOUR after a capture whose last segment is at t=12.0 bound silently at
t=3600.0 -- reachable, because the sniffer has a hard `--seconds` ceiling and
`livesession` prints "THE OFF-WIRE CAPTURE DIED" and deliberately keeps the session going
while `marks.py` watches the CLIENT and knows nothing about the sniffer. Section 16
covers both, and the second one is deliberately split: DISJOINT is refused (the artifact
can prove it and no threshold is needed), a PARTIAL overlap is REPORTED, because "the
network went quiet" and "the sniff stopped" are not separable from the artifact.

SECTION 10 IS THE COMPATIBILITY PARAGRAPH, AND ITS TEETH ARE NOT WHERE THE SPEC POINTS.
§10.5.1 says a mark must not carry an `origin` field, because `origin.origin_of` reads
EVERY record looking for contradictions. Measured: it does not, today -- `origin_of` only
reads `origin` off a record whose `kind` is `"origin"`, so a mark carrying one is inert
and the rule is insurance against a future relaxation. The field that flips a verdict
TODAY is any of `origin.PEER_FIELDS`, which are read off every record regardless of kind,
and the flip is measured here in both directions: a live capture stating `live` with no
address of its own reads `live (uncorroborated)`, and the same file with ONE mark
carrying `"server": "127.0.0.1:6112"` reads `unknown -- CONTRADICTED`. `require_single`
then refuses to pool it, so the one artifact this project cannot reproduce drops out of
its own corpus over a field name. Both rules are asserted; only the second is a
measurement, and this file says which is which.

WHAT THE TOLERANCE CAN ACTUALLY DETECT, BECAUSE THE DOCSTRING USED TO OVERSTATE IT.
§10.5.1's `|dperf - dwall| <= 0.250` was described as turning "perf_counter is comparable
across processes on Windows" into a measurement. Measured on this machine (win32,
QueryPerformanceCounter against GetSystemTimePreciseAsFileTime): two processes stamping
the pair adjacently agree to 5 MICROSECONDS worst case over 12 spawns and drift at
-0.004 ppm, which is 688 days to reach 250 ms. So the tolerance is ~50,000x the
phenomenon it is named for and will never fire for it. It CAN fire on a per-process perf
epoch -- caught at a 30 s and a 2 s launch gap, missed at 0.24 s and 0.05 s, so even that
power is an accident of launch order and evaporates the day `marks` is spawned beside the
sniffer in `livesession.run` -- and on a wall clock that stepped or drifted. And it is
structurally blind to the thing §8.9's criterion is really about: `t_perf` and `t_wall`
are sampled adjacently in ONE process, so their difference only ever measures the OS-wide
(QPC - system time) offset against itself and can say NOTHING about the axis the segments
are on. That is why section 16 exists and why `wire_t` is now a third channel. The 0.250
is kept because it is the spec's number and the two faults above are real; what changed
is that nothing here claims it measures what it cannot.

THREE OPEN ITEMS, REPORTED HERE RATHER THAN CHECKED, because they are gaps in the
integration and not defects in the module -- a test that asserted them would be a
permanently red test that gets deleted:

  * §10.5.1 says the plan's sha256 "goes in `manifest.json`". `livesession.py` writes
    that manifest and nothing in this tree imports `marks` at all, so today the seal
    lives only in `marks_meta` and the operator's own record. `--check-plan` is the
    pre-flight that makes that workable; the manifest key is still to be wired. It also
    means `bind()` HAS NEVER RUN AGAINST A BYTE ARENANET SENT: `wire_epoch` refuses all
    ten `wire.jsonl` in the vault, and not for the reason the refusal used to give --
    measured, every one of them carries NEITHER epoch, because `t0_wall` landed
    2026-08-11 and the newest live capture is 2026-08-10. Every fixture behind every
    claim in this file is synthetic, and this module's first real input is the next run.
  * `Marker(path, [], sha).advance()` raises `IndexError`, not `PlanExhausted`, because
    the refusal message reads `self.steps[-1]`. Unreachable through `open_marks`, which
    refuses an empty plan -- but it is the one refusal in the module that is not a
    `MarksError`, which is the property the header is otherwise careful about.
  * a plan STEP's text reaches `plan_marks.jsonl` verbatim and comes back out of
    `scrub_captures.scrub_record` byte-identical, because `text` is not a handled field
    and falls through the trailing `else` with no count and no report. The module's PII
    property is real and narrower than it read: the RUN has no input path, so a session
    cannot acquire text it did not start with. `marks.py`'s header now says which.
    Naming `text` in the scrub's handled set would make that a decision rather than a
    fall-through; it is a change to another module and is not made here.

TWO THINGS NOBODY HAS MEASURED, stated so the next reader does not assume otherwise: what
a real system suspend does to QueryPerformanceCounter versus the system time on this
hardware (Microsoft documents QPC as including sleep time on current Windows, which would
mean no skew and no detection), and whether a real `MsgWaitForMultipleObjects`/
`PeekMessageW` pair on a thread that owns no window behaves as `FakeUser32` models it.
The fake models the two OS rules the design turns on and models them correctly as far as
could be checked, but it is our model of Windows and not Windows. What IS measured is the
backstop under the whole teardown: a hard-killed process releases its global hotkey
immediately, proved against VK_F24 with a live WinError 1409 control while the process
lived.

Standard library only. No vault, no socket, no client, no Windows. ~1.2 s.
"""
import argparse
import ast
import collections
import importlib.util
import io
import json
import os
import sys
import tempfile
import traceback
import types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import checks  # noqa: E402
import origin  # noqa: E402

# 179, MEASURED from the green run of 2026-08-13 and not guessed -- it is the exact count,
# because every check in this file is unconditional. There is no vault fixture, no socket,
# no client and no platform branch that can drop a section: the hotkey half runs on a fake
# `user32`, the clock half on injected clocks, the Windows-only `_load_user32` and
# `process_alive` paths are reached by swapping `marks.ctypes` for a shim with no `windll`
# (so the refusal is exercised ON Windows too, where it otherwise never runs), and
# `wirecapture` is imported behind a stub `tcptable` when the real one will not load. A
# floor left trailing its run is a floor that would not notice a whole section going
# missing, which is what happened to `test_dispatch.py` at 20 against a run of 23.
#
# AND UNTIL 2026-08-13 THE FLOOR WAS UNREACHABLE AS A GUARD, WHICH IS WORSE THAN TRAILING.
# A skeptic ran 109 sabotages against the 139-check version: TWELVE died with a traceback
# between check 17 and check 126 and FOUR HUNG past a 120 s timeout -- no verdict banner,
# no ledger, no floor line, in sixteen of them. Every vacuity mode that could be
# constructed showed up as a crash or a wedge and never as a short ledger, so the number
# was a static count assertion rather than the partial-vacuity net `checks.py` describes.
# `guarded()` turns a crash into a named failing check and `BoundedHotkeys` turns a lost
# ending into a red instead of a hang; both are documented at their definitions.
#
# THE SABOTAGES, BUILT AND RUN as scratch copies of `marks.py` through `--module` -- this
# is what says which checks here are load-bearing rather than decorative. All 25 exit 1
# against a green 179, none hangs, and thirteen redden exactly ONE check:
#
#   VK_F9/F10/F11 set to ESCAPE/ENTER/SPACE                3 red   (section 4)
#   the handle retained + self.user32["Send"+"Input"]      5 red   (sections 4, 5)
#   __import__("operator").attrgetter("Send"+"Input")      2 red   (section 5)
#   an ALIASED subscript, u = self.user32; u[computed]     5 red   (sections 4, 5)
#   plan_sha256 normalising CRLF and trailing space        1 red   (section 1)
#   driver_marks_name() returning the pinned literal       1 red   (section 12)
#   bind() returning every mark in REVERSE                 9 red   (sections 6, 11)
#   run() loses the STOP-file ending                       2 red   (section 13)
#   run() loses the alive() ending                         3 red   (section 13)
#   run() loses the seconds ceiling                        1 red   (section 13)
#   _drain peeks only WM_HOTKEY instead of the whole range 4 red   (sections 4, 13)
#   bind() takes the WALL epoch from the MARKS file        1 red   (section 6)
#   the tolerance comparison `>` changed to `>=`           1 red   (section 7)
#   TOLERANCE = 0.400                                      2 red   (section 7)
#   drift_shape loses its STEP arm                         3 red   (section 7)
#   the wire_t witness deleted from bind()                 1 red   (section 16)
#   the disjoint-capture refusal deleted                   1 red   (section 16)
#   worst_skew() returning 0.0 for an empty table          1 red   (section 16)
#   resolve_out() not called by Marker.open                5 red   (section 17)
#   resolve_out() refusing EVERYTHING                      9 red   (section 17 + 4 named
#                                                                   section crashes)
#   the atexit hook moved back after the registration loop 1 red   (section 4b)
#   register()'s guard narrowed to `except Exception`      1 red   (section 4b, LEAK 3)
#   unregister() popping the id before the call            1 red   (section 4b, LEAK 5)
#   unregister() ignoring UnregisterHotKey's return        2 red   (section 4b, LEAK 4)
#   the already-exists refusal removed                     1 red   (section 17)
#
# AND FIVE AGAINST `wirecapture.py`, run as whole COPIED TREES because section 6 imports
# the real producer. The pair that matters is the first two: the unmodified control and a
# BEHAVIOUR-PRESERVING reformat (`**{"t0" + "_perf": t0}`) are BOTH GREEN at 179, where
# the raw grep this replaced reddened on the reformat and never ran when the key was
# genuinely broken. Renaming the key, publishing the WALL epoch as t0_perf, and publishing
# a t0_perf 0.9 s off the segments' own origin each redden the producer check BY NAME.
# The last one is the skeptic's silent-mislabelling capture, and section 6's own fixture
# then catches it downstream too: "2 of 3 mark(s) report having SEEN a segment stamped
# later than the mark itself -- mark 1 binds to t=31.350s and its wire_t is 32.250s,
# +0.900s ahead", from a capture the real producer wrote.
#
# THE OLDEST SABOTAGE HERE FOUND A DEFECT IN THIS FILE AND IT IS STILL THE ONE TO
# REMEMBER. Section 6's fixture originally had the two wall clocks in EXACT agreement,
# which is what a fixture built by one Clock naturally does -- and with zero skew,
# `t_wall - t0_wall` and `t_perf - t0_perf` are the same number, so the segment-equality
# headline passed against a wall-clock binder and the sabotage reddened 2 checks, neither
# in the section whose whole subject it is. The fixture now carries 100 ms of skew, and
# the marks file's own epoch sits 31 s after the capture's for the same reason one level
# up. A control built out of one clock agrees with itself.
LEDGER = checks.Ledger("marks (pre-registered operator marks)", floor=179)
CHECK = checks.adopt(LEDGER)

DRIVE_CLIENT_PY = os.path.join(HERE, "drive_client.py")
# NO `WIRECAPTURE_PY` HERE ANY MORE, AND ITS ABSENCE IS THE POINT. The producer half of
# the t0_perf contract used to be checked by reading wirecapture.py's raw source and
# looking for `'"t0_perf": t0'`. Section 6 now BUILDS a capture with the real producer and
# a distinctive epoch instead, so the path constant has no reader left.
TAPE_PY = os.path.join(os.path.dirname(HERE), "authsrv", "tape.py")


def load_module(path):
    """Import a `marks.py` by PATH, so a sabotaged copy can be run through this file.

    `--module` is `test_msgmix.py`'s idiom and it is not a convenience. "A check that
    cannot fail is not a check" is only demonstrable by running the broken version, and a
    scratch copy of the module with one line changed is the closest reconstruction of a
    shipped defect there is -- closer than an inline reimplementation, which drifts into
    being a different bug. The inline rivals in sections 4, 5 and 7 are kept as well,
    because they put both answers in one run where a reader sees them side by side.
    """
    spec = importlib.util.spec_from_file_location("marks_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def refused(fn, *a, **kw):
    """Did `fn` raise? Returns the exception, or None if it returned.

    `Exception`, deliberately, and never `BaseException`: every refusal in `marks.py` is
    a `MarksError`, which is an `Exception` for exactly this reason. `test_atex.py` and
    `test_stripbuild.py` both paid for the other choice -- a `SystemExit` refusal is a
    `BaseException`, so a control written this way does not catch it, the run dies with
    no verdict banner and no ledger, and a caught defect reads as a crash.
    """
    try:
        fn(*a, **kw)
        return None
    except Exception as exc:                      # noqa: BLE001 -- that IS the check
        return exc


# ------------------------------------------------------------------- clocks ----
class Clock:
    """One controllable `perf_counter`/`time` pair, shared by every writer in a fixture.

    The whole of `marks.bind` rests on a claim about two processes: that a `perf_counter`
    reading taken in the marks process is comparable to one taken in the sniffer
    subprocess. A fixture cannot prove that about Windows -- only a live run can -- but it
    can prove that the ARITHMETIC is right when it holds, and that the module NOTICES when
    it does not. So this class is one clock handed to both, and `skew` is the knob that
    makes the two disagree by a stated amount.

    `wall()` is derived from `perf` rather than sampled independently, so a fixture with
    `skew = 0` has EXACTLY zero disagreement and section 7's tolerance boundary can be
    approached to the millisecond instead of to whatever the machine happened to do.
    """

    def __init__(self, perf0=1000.0, wall0=1_700_000_000.0):
        self.perf0, self.wall0 = perf0, wall0
        self.perf = perf0
        self.skew = 0.0

    def tick(self, dt=0.5):
        self.perf += dt
        return self.perf

    def perf_counter(self):
        return self.perf

    def time(self):
        return self.wall0 + (self.perf - self.perf0) + self.skew


# -------------------------------------------------------------- fake user32 ----
class FakeUser32:
    """The four `user32` calls `Hotkeys` documents, plus a keyboard nobody has to press.

    `Hotkeys`'s own docstring names the surface, and a fake that models only that surface
    would be a mirror: it would agree with whatever the module did. So this one models the
    two OS RULES the module's design turns on, and both are things the module can get
    wrong:

      * MOD_NOREPEAT. A key held down auto-repeats. Windows posts a fresh WM_HOTKEY per
        repeat UNLESS MOD_NOREPEAT was passed at registration, in which case a hold is ONE
        message however long it is held. That flag is half of "an edge fires once per
        press"; the fake honours it, so dropping it is visible here.
      * a queue, not a level. WM_HOTKEY is a QUEUED message and `PM_REMOVE` takes each
        exactly once, so the number of actions is the number of presses however often the
        loop wakes up. `GetAsyncKeyState` is a LEVEL -- it answers "is it down now" every
        time it is asked -- and it is here on the fake precisely so section 4 can run the
        polling rival against the same held key and get a different number.

    `PeekMessageW` honours its `lo`/`hi` filter, because `_drain`'s comment claims the
    whole range is peeked for a reason: a filtered peek leaves everything else in the
    queue forever. The fake records the range it was asked for, and section 4 runs the
    filtered rival to show what it leaves behind.

    The `msg._obj` idiom is `test_harness.FakeUser32.GetWindowThreadProcessId`'s -- the
    module passes `ctypes.byref(...)`, and a fake reads the referent back off it.

    THE FOUR FAILURE MODES BELOW ARE THE SECTION THAT WAS MISSING, and their absence was
    measured. `fail_on` models RegisterHotKey RETURNING 0, which is the one path the
    module handled -- and `UnregisterHotKey` was hard-coded `return 1`, so no check in
    this file could ever see a failed release. Meanwhile five real leak paths were live in
    the shipped module and the suite was green at 139. A fake that can only produce the
    failures the code already handles is a mirror.

      `fail_on`            RegisterHotKey returns 0 on the Nth call (the handled one)
      `raise_on`           RegisterHotKey RAISES on the Nth call -- a ctypes error
      `interrupt_on`       RegisterHotKey raises KeyboardInterrupt on the Nth call
      `unregister_fails`   UnregisterHotKey returns 0 and does NOT release. This is not
                           hypothetical: a real UnregisterHotKey called from a thread that
                           does not own the hotkey returns 0 with WinError 1419 and the
                           key stays taken -- measured on this machine against VK_F24.
      `unregister_raises`  UnregisterHotKey raises KeyboardInterrupt (Ctrl-C in teardown)

    `registered` is the OS-SIDE ledger and is deliberately not the object's bookkeeping:
    every leak check below reads this dict, so "the module thinks it released" can differ
    from "the key is free", which is the whole of finding 3c.
    """

    def __init__(self, fail_on=None, mod_norepeat=0x4000, wm_hotkey=0x0312,
                 raise_on=None, interrupt_on=None, unregister_fails=False,
                 unregister_raises=None):
        self.MOD_NOREPEAT = mod_norepeat
        self.WM_HOTKEY = wm_hotkey
        self.registered = {}          # hotkey id -> (mods, vk). THE OS-SIDE LEDGER.
        self.unregistered = []
        self.queue = collections.deque()
        self.held = set()             # keys physically down right now
        self.calls = []               # every user32 call, in order
        self.peek_ranges = []
        self.register_calls = 0
        self.unregister_calls = 0
        self.fail_on = fail_on        # 1-based index of the RegisterHotKey call that fails
        self.raise_on = raise_on
        self.interrupt_on = interrupt_on
        self.unregister_fails = unregister_fails
        self.unregister_raises = unregister_raises

    # -- the four the module uses -------------------------------------------
    def RegisterHotKey(self, hwnd, hk_id, mods, vk):
        self.calls.append("RegisterHotKey")
        self.register_calls += 1
        if self.raise_on is not None and self.register_calls == self.raise_on:
            raise OSError(f"[fake] RegisterHotKey blew up on call {self.register_calls}")
        if self.interrupt_on is not None and self.register_calls == self.interrupt_on:
            raise KeyboardInterrupt
        if self.fail_on is not None and self.register_calls == self.fail_on:
            return 0
        if any(v == vk for _m, v in self.registered.values()):
            return 0                  # the real "already held" answer
        self.registered[hk_id] = (mods, vk)
        return 1

    def UnregisterHotKey(self, hwnd, hk_id):
        self.calls.append("UnregisterHotKey")
        self.unregister_calls += 1
        if (self.unregister_raises is not None
                and self.unregister_calls == self.unregister_raises):
            raise KeyboardInterrupt
        if self.unregister_fails:
            return 0                  # WinError 1419: refused, and the key STAYS TAKEN
        self.unregistered.append(hk_id)
        self.registered.pop(hk_id, None)
        return 1

    def MsgWaitForMultipleObjects(self, count, handles, wait_all, ms, mask):
        self.calls.append("MsgWaitForMultipleObjects")
        for hk_id, (mods, vk) in self.registered.items():
            if vk in self.held and not (mods & self.MOD_NOREPEAT):
                self.queue.append((self.WM_HOTKEY, hk_id))   # auto-repeat
        return 0 if self.queue else 0x00000102               # WAIT_TIMEOUT

    def PeekMessageW(self, msg, hwnd, lo, hi, flags):
        self.calls.append("PeekMessageW")
        self.peek_ranges.append((lo, hi))
        for i, (message, wparam) in enumerate(self.queue):
            if lo == 0 and hi == 0 or lo <= message <= hi:
                del self.queue[i]
                msg._obj.message = message
                msg._obj.wParam = wparam
                return 1
        return 0

    # -- the level-triggered surface the polling rival reads ------------------
    def GetAsyncKeyState(self, vk):
        return -32768 if vk in self.held else 0

    # -- a keyboard --------------------------------------------------------
    def _post_hotkey(self, vk):
        for hk_id, (_mods, v) in self.registered.items():
            if v == vk:
                self.queue.append((self.WM_HOTKEY, hk_id))

    def press(self, vk):
        """One press and release: exactly one WM_HOTKEY, whatever the mods."""
        self._post_hotkey(vk)

    def hold(self, vk):
        """Press and KEEP DOWN. Auto-repeat then depends on MOD_NOREPEAT."""
        self.held.add(vk)
        self._post_hotkey(vk)

    def release(self, vk):
        self.held.discard(vk)

    def post_raw(self, message, wparam=0):
        """Anything else that lands in a thread's queue -- WM_QUIT, a stray timer."""
        self.queue.append((message, wparam))


class Watchdog(Exception):
    """`run()` polled more times than any ending in this fixture should have allowed."""


class BoundedHotkeys:
    """`Hotkeys` with a hard pass ceiling, so a lost ENDING reddens instead of HANGING.

    THIS IS THE SHAPE OF THE PROBLEM, AND IT IS NOT COVERAGE. A skeptic broke each of
    run()'s endings one at a time -- the stop_file test removed, the `alive()` test
    disabled, the seconds ceiling disabled, and `_drain`'s whole-range peek narrowed to
    WM_HOTKEY only -- and ALL FOUR RUNS HUNG. No exit code, no verdict banner, no ledger,
    past a 120 s timeout. Section 13's later sub-runs pass no alive, no stop file and no
    seconds, so a run() that has lost any one ending loops forever, and under CLAUDE.md's
    "run all of it" any of those four one-line defects blocks the entire suite instead of
    naming itself. The peek case is the one that shows the checks themselves were real:
    #43/#44/#45 printed [FAIL] and THEN the process wedged at the next sub-run.

    `poll` is the only call `run()` makes unconditionally every pass, so bounding it
    bounds any loop however the endings are broken. The ceiling is generous -- these
    fixtures end within a handful of passes -- and section 13's first check is that the
    watchdog FIRES on a run with no ending at all, because a bound that has never been
    reached is not a bound.
    """

    def __init__(self, hk, limit=64):
        self.hk = hk
        self.limit = limit
        self.passes = 0

    def poll(self, timeout_ms=200):
        self.passes += 1
        if self.passes > self.limit:
            raise Watchdog(f"run() polled {self.passes} times without ending")
        return self.hk.poll(timeout_ms)

    def unregister(self, say=None):
        return self.hk.unregister(say=say)


def run_bounded(M, marker, hk, limit=64, **kw):
    """(why, watchdog_or_None, passes). `run()` under a ceiling it cannot lose."""
    bounded = BoundedHotkeys(hk, limit)
    try:
        return M.run(marker, bounded, **kw), None, bounded.passes
    except Watchdog as exc:
        return None, exc, bounded.passes


def poll_by_level(user32, bindings):
    """The rival `marks.py` refuses to be: `GetAsyncKeyState`, asked once per pass.

    Reproduced live rather than described, so section 4's claim is a difference between
    two answers in one process rather than between an answer and a sentence. It is also
    what a reader would write if the hotkey registration failed and the module fell back
    instead of refusing -- which is the fallback `Hotkeys.register` explicitly does not
    have, because a poll does not SWALLOW the key: every mark would also fire whatever
    Guild Wars binds to that F-key and change the traffic the mark exists to describe.
    """
    return [action for vk, action in bindings
            if user32.GetAsyncKeyState(vk) & 0x8000]


# ------------------------------------------------------- syntax-tree probes ----
# Win32's input-WRITING surface. Not "everything in user32" -- `Hotkeys` legitimately
# calls four functions and reads a message queue. These are the ones that put a keystroke,
# a click or a message into somebody else's input path, which is the side of the line
# `drive_client.py` is on and `marks.py` may never be on.
INPUT_WRITERS = (
    "SendInput", "keybd_event", "mouse_event", "SetCursorPos",
    "SendMessage", "SendMessageA", "SendMessageW",
    "PostMessage", "PostMessageA", "PostMessageW",
    "SetKeyboardState", "BlockInput", "SendKeys", "ClipCursor",
)

# What `Hotkeys` says it uses, and nothing else. A positive whitelist rather than a
# denylist, because a denylist can only refuse the names somebody thought of.
ALLOWED_USER32 = {"RegisterHotKey", "UnregisterHotKey",
                  "MsgWaitForMultipleObjects", "PeekMessageW"}


def _docstring_nodes(tree):
    """The `Constant` nodes that ARE docstrings, by identity.

    Section 5 searches string constants for `"SendInput"`, and `marks.py`'s own header
    contains the sentence promising there is none. A detector that cannot tell the
    promise from the deed reddens on the documentation -- which is `test_cmsgnames.py`'s
    grep and `test_sweeploop.py`'s, both of which went red on prose. Comments never reach
    the tree at all; docstrings do, so they are excluded here by identity rather than by
    matching their text.
    """
    out = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                                 ast.ClassDef)):
            continue
        body = getattr(node, "body", None)
        if (body and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)):
            out.add(id(body[0].value))
    return out


def writers_by_identifier(tree):
    """DETECTOR 1: input-writing names used as identifiers anywhere in the tree.

    `ast.Attribute.attr` and `ast.Name.id`, which is `user32.SendInput(...)` and a bare
    `SendInput(...)` alike. Blind to `getattr`.
    """
    found = set()
    for node in ast.walk(tree):
        name = None
        if isinstance(node, ast.Attribute):
            name = node.attr
        elif isinstance(node, ast.Name):
            name = node.id
        if name in INPUT_WRITERS:
            found.add(name)
    return found


def writers_by_constant(tree):
    """DETECTOR 2: input-writing names appearing as non-docstring string constants.

    This is what catches `getattr(user32, "SendInput")`, which detector 1 cannot see.
    Blind in turn to `"Send" + "Input"`, where the name is never a constant.
    """
    docs = _docstring_nodes(tree)
    found = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                and id(node) not in docs):
            for w in INPUT_WRITERS:
                if w in node.value:
                    found.add(w)
    return found


# Every primitive that turns a STRING into an attribute or a function at run time. The
# first version of detector 3a was `("getattr", "setattr")` and nothing else, and a
# skeptic walked past it three ways on a live handle -- `operator.attrgetter("Send" +
# "Input")`, `object.__getattribute__`, and `vars(handle)[computed]`. The claim this list
# supports is not "these are the dangerous names": it is that `marks.py` contains NO
# dynamic lookup at all, which is what makes the whitelist below a total statement instead
# of a sample. A module with none of these can only call names its own source spells out.
DYNAMIC_LOOKUP = (
    "getattr", "setattr", "delattr", "vars", "eval", "exec", "compile",
    "__import__", "globals", "locals", "__getattribute__", "__getattr__",
    "__dict__", "attrgetter", "methodcaller", "itemgetter", "importlib", "operator",
    "__class__", "__builtins__", "__subclasses__",
)


def dynamic_attribute_calls(tree):
    """DETECTOR 3a: every dynamic-lookup primitive in the tree, by any spelling.

    Names AND attributes AND imported modules, because the three routes that beat the
    old version were spelled `__import__(...)`, `.attrgetter(...)` and `vars(...)` and
    only the first is an `ast.Name` at the head of a call. `marks.py` has none of them,
    and that -- not the whitelist alone -- is what makes the whitelist total.
    """
    out = []
    for node in ast.walk(tree):
        name = None
        if isinstance(node, ast.Attribute):
            name = node.attr
        elif isinstance(node, ast.Name):
            name = node.id
        elif isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] in DYNAMIC_LOOKUP:
                    out.append(f"import {a.name}")
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module.split(".")[0] in DYNAMIC_LOOKUP:
                out.append(f"from {node.module} import ...")
        if name in DYNAMIC_LOOKUP:
            out.append(name)
    return sorted(set(out))


def _handle_names(tree):
    """Every local name that holds the `user32` handle, `user32` plus its aliases.

    `u = self.user32` then `u[computed](...)` was one of the three routes that passed:
    `u` is not spelled `user32`, so a scan anchored on the spelling saw nothing. Two
    passes are enough for the aliases a real module would have, and the ALIAS SET IS
    REPORTED by the check that uses it so a longer chain shows up as a surprise rather
    than as silence.
    """
    names = {"user32"}
    for _ in range(2):
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            val = node.value
            src = None
            if isinstance(val, ast.Name):
                src = val.id
            elif isinstance(val, ast.Attribute):
                src = val.attr
            if src in names:
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        names.add(t.id)
                    elif isinstance(t, ast.Attribute):
                        names.add(t.attr)
    return names


def user32_attributes(tree):
    """DETECTOR 3b: everything fetched off the handle -- attribute OR SUBSCRIPT, or alias.

    `user32.X`, `self.user32.X`, `user32["X"]` and `u["X"]` where `u` was assigned from
    the handle. A SUBSCRIPT of a `ctypes.WinDLL` resolves a function exactly as an
    attribute does -- verified on a real handle, `u["GetSystem" + "Metrics"](0)` returns
    the same 1920 as the attribute form -- and the first version of this walked
    `ast.Attribute` only, so `self.user32["Send" + "Input"](...)` was invisible to all
    three detectors and passed 139 checks.

    A fetch whose key is NOT a compile-time constant is reported as the string
    `"<computed>"`, which can never be in `ALLOWED_USER32`, so a computed name reddens
    without this having to guess what it computes to.
    """
    handles = _handle_names(tree)
    out = set()
    for node in ast.walk(tree):
        base, key = None, None
        if isinstance(node, ast.Attribute):
            base, key = node.value, node.attr
        elif isinstance(node, ast.Subscript):
            base = node.value
            sl = node.slice
            key = (sl.value if isinstance(sl, ast.Constant) and isinstance(sl.value, str)
                   else "<computed>")
        if base is None:
            continue
        if ((isinstance(base, ast.Name) and base.id in handles)
                or (isinstance(base, ast.Attribute) and base.attr in handles)):
            out.add(key)
    return out


def naive_grep(src, needle="SendInput"):
    """The rival check: count `needle` in the RAW source, docstrings and all."""
    return src.count(needle)


def docstring_text(tree):
    """Every docstring in the tree, concatenated. The prose a grep cannot tell from code.

    Section 5 uses this to state its claim in the one form that is not brittle: not "the
    naive grep finds exactly one hit" -- which would redden the day somebody rewords the
    header -- but "every occurrence of the word in this file is in PROSE". That stays true
    under any rewording and goes red the moment a real call appears.
    """
    out = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            doc = ast.get_docstring(node, clean=False)
            if doc:
                out.append(doc)
    return "\n".join(out)


def identifiers(tree):
    """Every name used as an identifier: attributes, names, and imported module names."""
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            out.add(node.attr)
        elif isinstance(node, ast.Name):
            out.add(node.id)
        elif isinstance(node, ast.Import):
            out |= {a.name.split(".")[-1] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            out |= {a.name for a in node.names}
            if node.module:
                out.add(node.module.split(".")[-1])
    return out


def calls_os_kill(tree):
    """Is `os.kill` reached anywhere? `process_alive`'s docstring says why it must not be.

    On Windows CPython implements `os.kill(pid, 0)` with `TerminateProcess`, so the
    harmless POSIX liveness idiom would KILL THE CLIENT mid-session -- destroying the one
    artifact a live run cannot reproduce, from inside the tool whose whole job is to
    annotate it.
    """
    for node in ast.walk(tree):
        if (isinstance(node, ast.Attribute) and node.attr == "kill"
                and isinstance(node.value, ast.Name) and node.value.id == "os"):
            return True
    return False


def imports_of(tree):
    """Every module name imported anywhere in the tree, including inside functions."""
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.add(node.module.split(".")[0])
    return out


def _first_stmt(fn, pred):
    """Index of the first TOP-LEVEL statement of `fn` containing a node matching `pred`.

    Statement INDEX rather than line number, because the claim being made is an ordering
    within a function body and a line number would move under any reformat. None if no
    statement matches. `test_dispatch.py`'s and `test_sweeploop.py`'s idiom: "A comes
    before B" is a fact about the tree that a grep can see both halves of and still not
    answer.
    """
    if fn is None:
        return None
    for i, stmt in enumerate(fn.body):
        for node in ast.walk(stmt):
            if pred(node):
                return i
    return None


def dict_has_key(tree, func_name, key):
    """Does a dict literal inside `func_name` carry the constant key `key`?"""
    for node in ast.walk(tree):
        if not (isinstance(node, ast.FunctionDef) and node.name == func_name):
            continue
        for sub in ast.walk(node):
            if isinstance(sub, ast.Dict):
                for k in sub.keys:
                    if isinstance(k, ast.Constant) and k.value == key:
                        return True
    return False


# ----------------------------------------------------------------- fixtures ----
def write_plan(path, rows, trailer=""):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        for kind, text in rows:
            fh.write(f"{kind}\t{text}\n" if text else f"{kind}\n")
        fh.write(trailer)
    return path


PLAN_ROWS = [("select", "character select, settled"),
             ("open", "merchant Sanura, first open"),
             ("close", "panel closed")]


def import_wirecapture():
    """The real `wirecapture`, imported behind a stub `tcptable` if it will not load.

    `wirecapture` imports `tcptable`, which binds `ctypes.wintypes` at module scope and is
    therefore unimportable off Windows -- the exact reason `marks.driver_marks_name()`
    pins its own literal and prefers the real one only when it is reachable. `open_capture`
    never touches `tcptable`; only the WinDivert sniff loop does. So the stub stands in
    for a module this section does not call, and section 6 measures the REAL producer's
    real output on every platform instead of declaring a skip.

    Returns (module, how) so the run says which path it took.
    """
    try:
        import wirecapture
        return wirecapture, "imported directly"
    except ImportError as exc:                    # pragma: no cover -- off Windows
        sys.modules.setdefault("tcptable", types.ModuleType("tcptable"))
        import wirecapture
        return wirecapture, f"imported behind a stub tcptable ({exc})"


def write_marks_file(path, rows, sha="0" * 64, steps=3, t0_perf=1031.0,
                     t0_wall=1_700_000_031.0, extra_meta=None):
    """A marks file written BY HAND, for the shapes the real writer cannot produce.

    Sections 7 and 8 need marks whose two clocks disagree by a stated amount, and marks
    stamped before the capture's epoch. Both are states `Marker` will not enter with a
    sane clock, and reaching them by feeding it a lying clock would make the fixture a
    statement about `Marker` rather than about `bind`.

    THE META EPOCH DEFAULTS 31 SECONDS AFTER THE CAPTURE'S, and it used to default to the
    same numbers. That equality is what let a bind() sourcing either epoch from the MARKS
    file pass all 139 checks -- the fixtures could not tell which of the two files was
    being read, which is the only thing that makes this a cross-process check. The
    marks-side epoch is when the MARKER opened, and in every real run that is after the
    sniffer went up. `mark_rec` keeps stamping its records against the CAPTURE's epoch,
    which is what a correct binder resolves them against.
    """
    with open(path, "w", encoding="utf-8") as fh:
        meta = {"kind": "marks_meta", "plan_sha256": sha, "plan": "plan.tsv",
                "steps": steps, "t0_perf": t0_perf, "t0_wall": t0_wall, "pid": 9}
        meta.update(extra_meta or {})
        fh.write(json.dumps(meta) + "\n")
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    return path


def mark_rec(seq, mark, step, text, dperf, dwall, t0_perf=1000.0,
             t0_wall=1_700_000_000.0):
    return {"kind": "mark", "seq": seq, "mark": mark, "step": step, "text": text,
            "t_perf": t0_perf + dperf, "t_wall": t0_wall + dwall}


def write_wire(path, t0_perf=1000.0, t0_wall=1_700_000_000.0, meta=True,
               segments=(), stamp="live", addressless=True):
    """A hand-written `wire.jsonl`, for the shapes a real capture cannot be made to have.

    Section 6 uses the REAL `wirecapture.open_capture` instead. This one exists for the
    refusals -- no `wire_meta` at all, a `wire_meta` with no `t0_perf` (every capture
    written before 2026-08-13) -- and for section 10, which needs a file whose ONLY
    address can be the one an inlined mark would contribute.
    """
    with open(path, "w", encoding="utf-8") as fh:
        if stamp:
            fh.write(json.dumps(origin.record("wirecapture.py", stamp)) + "\n")
        if meta:
            rec = {"kind": "wire_meta", "pid": 1, "server_ports": [80]}
            if not addressless:
                rec.update({"client": "10.0.0.2:63155", "server": "54.164.212.177:80"})
            if t0_perf is not None:
                rec["t0_perf"] = t0_perf
            if t0_wall is not None:
                rec["t0_wall"] = t0_wall
            fh.write(json.dumps(rec) + "\n")
        for t, payload in segments:
            fh.write(json.dumps({"kind": "wire", "dir": "s2c", "seq": 1, "t": t,
                                 "payload": payload}) + "\n")
    return path


# ================================================================ sections ====
def section_plan(M, tmp):
    """1. The plan is a PRE-REGISTRATION, and every way of not having one is refused."""
    print("\n1. the plan: an ordinal into a prediction written before the client launched")
    p = write_plan(os.path.join(tmp, "plan.tsv"),
                   PLAN_ROWS, trailer="\n# an operator note, not a step\n\n")
    steps = M.load_plan(p)
    CHECK([(s.index, s.kind, s.text) for s in steps]
          == [(0, "select", "character select, settled"),
              (1, "open", "merchant Sanura, first open"),
              (2, "close", "panel closed")],
          "kind<TAB>text parses to ordinals 0..n-1",
          f"{[tuple(s) for s in steps]} -- blank lines and full-line comments do NOT "
          f"consume an ordinal, so a plan can be annotated for the operator without "
          f"moving the numbers the marks refer to")

    sha = M.plan_sha256(p)
    CHECK(len(sha) == 64 and int(sha, 16) >= 0, "the seal is a sha256 hexdigest", sha[:16])
    write_plan(os.path.join(tmp, "same.tsv"), PLAN_ROWS, trailer="\n# a DIFFERENT note\n\n")
    CHECK(M.plan_sha256(os.path.join(tmp, "same.tsv")) != sha,
          "and it is over RAW BYTES, so a comment-only edit is a different plan",
          "the seal is what says the prediction was not rewritten to agree with its "
          "result. A normalising hash would let the text of every step be preserved "
          "while the file was edited, which is most of what an edit would be for")
    CHECK([(s.index, s.kind) for s in M.load_plan(os.path.join(tmp, "same.tsv"))]
          == [(0, "select"), (1, "open"), (2, "close")],
          "CONTROL: and that comment-only edit changed no STEP",
          "so the sha check above is about the file and not about the parse -- "
          "otherwise it would be passing for the wrong reason")

    # ---- "RAW BYTES" IS A CLAIM ABOUT BYTES, AND THE COMMENT FIXTURE COULD NOT SEE IT.
    # A skeptic replaced plan_sha256's body with a hash over
    # `fh.read().replace(b"\r\n", b"\n").rstrip()` -- the two normalisations the docstring
    # names by name and nothing else -- and this file went ALL CHECKS PASSED, 139, exit 0.
    # The two fixtures above differ in the TEXT of a comment, which ANY content-sensitive
    # hash sees, so what they measured was "the hash depends on the file". These three
    # differ ONLY in bytes the parse throws away, which is the realistic accident: the
    # plan is hand-edited on Windows and a CRLF plan is one Notepad save away.
    lf = os.path.join(tmp, "eol_lf.tsv")
    crlf = os.path.join(tmp, "eol_crlf.tsv")
    trail = os.path.join(tmp, "eol_trail.tsv")
    body = "".join(f"{k}\t{t}\n" for k, t in PLAN_ROWS)
    for path, raw in ((lf, body), (crlf, body.replace("\n", "\r\n")),
                      (trail, body + "\n\n   \n")):
        with open(path, "wb") as fh:
            fh.write(raw.encode("utf-8"))
    seals = {p: M.plan_sha256(p) for p in (lf, crlf, trail)}
    CHECK(len(set(seals.values())) == 3,
          "and it is over RAW BYTES: CRLF, LF and a trailing-whitespace tail seal apart",
          f"{ {os.path.basename(p): s[:12] for p, s in seals.items()} } -- a seal that "
          f"NORMALISED line endings would let a plan be rewritten with every step's text "
          f"preserved and still hash the same, which is most of what an edit would be "
          f"for. The comment-only fixture above cannot measure this: it differs in "
          f"CONTENT, so any content-sensitive hash passes it")
    parses = {p: [(s.index, s.kind, s.text) for s in M.load_plan(p)] for p in seals}
    CHECK(len({tuple(v) for v in parses.values()}) == 1,
          "CONTROL: and all three PARSE identically, so only the bytes differ",
          f"{parses[lf]} -- otherwise the check above would be passing because the plans "
          f"are different plans, which is the reason the comment fixture proved nothing")

    for label, arg, why in (
            ("no plan at all", None,
             "an unlabelled run must not be reachable by accident"),
            ("a plan that is not there", os.path.join(tmp, "nope.tsv"),
             "the plan is hashed BEFORE the client launches"),
    ):
        exc = refused(M.load_plan, arg)
        CHECK(isinstance(exc, M.PlanError), f"REFUSED: {label}", f"{exc} -- {why}")

    empty = write_plan(os.path.join(tmp, "empty.tsv"), [], trailer="\n# only a comment\n")
    exc = refused(M.load_plan, empty)
    CHECK(isinstance(exc, M.PlanError), "REFUSED: a plan with no steps",
          f"{exc} -- the unlabelled run wearing a file, refused for the same reason "
          f"a missing one is")

    kindless = os.path.join(tmp, "kindless.tsv")
    with open(kindless, "w", encoding="utf-8") as fh:
        fh.write("ok\tfine\n\ttext with no kind\n")
    exc = refused(M.load_plan, kindless)
    CHECK(isinstance(exc, M.PlanError) and "line 2" in str(exc),
          "REFUSED: a step that names nothing, by line number",
          f"{exc} -- a step with no kind cannot be a prediction, and the line number "
          f"is what makes the refusal actionable at 03:00 with a client waiting")

    notes = os.path.join(tmp, "notes.tsv")
    with open(notes, "w", encoding="utf-8") as fh:
        fh.write("1\tthe tooltip said 12g\n# a comment\n2\tsecond note\n")
    CHECK(M.load_notes(notes) == {1: "the tooltip said 12g", 2: "second note"},
          "notes are a SIDE FILE keyed by ordinal, so the plan's seal survives them",
          "§10.5.1 says a note's text is added 'by editing the plan' AND that a plan "
          "whose sha disagrees is refused. Following both literally makes every "
          "annotated run unbindable; the seal is the more important half")
    CHECK(M.load_notes(None) == {} and M.load_notes("") == {},
          "and no notes file is not an error", "annotation is optional; the seal is not")
    exc = refused(M.load_notes, os.path.join(tmp, "gone.tsv"))
    CHECK(isinstance(exc, M.PlanError), "REFUSED: a notes file that was named and is absent",
          f"{exc} -- silently returning {{}} would drop the operator's own annotations "
          f"and read as a run that had none")


def section_writer(M, tmp):
    """2. The record shapes are §10.5.1's, and a note carries NO TEXT."""
    print("\n2. the records: exactly the shapes the spec names, and no operator text")
    p = write_plan(os.path.join(tmp, "w_plan.tsv"), PLAN_ROWS)
    clk = Clock()
    m = M.open_marks(tmp, p, out=os.path.join(tmp, "w_marks.jsonl"), pid=4321,
                     clock=clk.perf_counter, wall=clk.time)
    clk.tick(); m.advance()
    clk.tick(); m.repeat()
    clk.tick(); m.note()
    clk.tick(); m.advance()
    clk.tick(); m.close("test")

    meta, marks = M.read(m.path)
    for key in ("kind", "plan_sha256", "steps", "t0_perf", "t0_wall", "pid"):
        CHECK(key in meta, f"marks_meta carries {key!r}", f"{sorted(meta)}")
    CHECK(meta["plan_sha256"] == M.plan_sha256(p) and meta["steps"] == 3
          and meta["pid"] == 4321,
          "and its seal, step count and pid are the run's own",
          f"{meta['plan_sha256'][:16]}..., {meta['steps']} steps, pid {meta['pid']}")

    want = ("kind", "seq", "mark", "step", "text", "t_perf", "t_wall")
    CHECK(all(all(k in r for k in want) for r in marks),
          "every mark carries kind/seq/mark/step/text/t_perf/t_wall",
          f"first: {sorted(marks[0])}")
    CHECK([r["seq"] for r in marks] == [1, 2, 3, 4],
          "seq is 1-based and increments by one", f"{[r['seq'] for r in marks]}")
    CHECK([(r["mark"], r["step"]) for r in marks]
          == [("advance", 0), ("repeat", 0), ("note", 0), ("advance", 1)],
          "advance opens the next step, repeat re-emits the current one, a note does "
          "not move it",
          f"{[(r['mark'], r['step']) for r in marks]}")
    CHECK(marks[0]["text"] == "character select, settled"
          and marks[1]["text"] == marks[0]["text"],
          "advance and repeat carry the PLAN's text", f"{marks[0]['text']!r}")

    note = marks[2]
    CHECK(note["text"] == "" and note.get("note_ordinal") == 1,
          "a NOTE carries no text at all, only its ordinal",
          "this is the PII property and it is by CONSTRUCTION, not by a scrubber: "
          "nothing the operator types during the run can reach the artifact because "
          "there is no path for it. test_scrub.py already reports one leak it cannot "
          "clean, in a field that carries the account email as UTF-16")

    end = [json.loads(l) for l in open(m.path, encoding="utf-8")
           if '"marks_end"' in l]
    CHECK(len(end) == 1 and end[0]["marks"] == 4 and end[0]["notes"] == 1
          and end[0]["last_step"] == 1,
          "and the file closes with a marks_end naming what happened",
          f"{end} -- without it a file truncated by a kill is indistinguishable from "
          f"one that finished, and 'the operator stopped marking' and 'the marker "
          f"died' are different facts about a session")
    CHECK(refused(m.close) is None and len(
        [l for l in open(m.path, encoding="utf-8") if '"marks_end"' in l]) == 1,
        "close is idempotent -- a second call writes no second end record",
        "run()'s finally and main()'s finally both call it")

    exc = refused(M.Marker(os.path.join(tmp, "closed.jsonl"), [], "x")._write, {"a": 1})
    CHECK(isinstance(exc, M.MarksError),
          "REFUSED: writing a record with the file not open",
          f"{exc}")


def section_exhausted(M, tmp):
    """3. §8.9 control 6: advancing past the last step is refused rather than wrapping."""
    print("\n3. advance past the last step REFUSES; it does not wrap to the top")
    p = write_plan(os.path.join(tmp, "e_plan.tsv"), PLAN_ROWS)
    clk = Clock()
    m = M.open_marks(tmp, p, out=os.path.join(tmp, "e_marks.jsonl"),
                     clock=clk.perf_counter, wall=clk.time)
    got = []
    for _ in range(3):
        clk.tick()
        got.append(m.advance()["step"])
    CHECK(got == [0, 1, 2],
          "POSITIVE CONTROL: exactly len(plan) advances open exactly the plan",
          f"{got} -- a refusal that fires one step early is the same defect wearing "
          f"the other sign, and it would end a session's labelling silently")

    clk.tick()
    exc = refused(m.advance)
    CHECK(isinstance(exc, M.PlanExhausted), "REFUSED: the fourth advance", f"{exc}")
    CHECK(m.cur == 2 and m.seq == 3,
          "and it moved NOTHING -- not the step, not the sequence",
          f"cur={m.cur} seq={m.seq}. A wrapped ordinal would silently re-label the "
          f"rest of the session as the top of the script, which is worse than an "
          f"unlabelled run because it looks labelled")
    CHECK(m.refused == 1, "and the refusal is COUNTED, into the artifact",
          f"refused={m.refused} -- the operator is looking at the game, not at this "
          f"console, so a refusal that only printed would be a refusal nobody saw")
    m.close()
    end = [json.loads(l) for l in open(m.path, encoding="utf-8") if '"marks_end"' in l]
    CHECK(end and end[0]["refused"] == 1,
          "and marks_end carries the count, so the artifact says so too", f"{end}")

    m2 = M.open_marks(tmp, p, out=os.path.join(tmp, "e2.jsonl"),
                      clock=clk.perf_counter, wall=clk.time)
    exc = refused(m2.repeat)
    CHECK(isinstance(exc, M.NothingToRepeat),
          "REFUSED: repeat before the first advance",
          f"{exc} -- there is no current step to re-emit, and inventing step 0 would "
          f"attribute the operator's action to a step they had not reached")
    CHECK(m2.seq == 0 and m2.cur is None, "and it wrote no record either",
          f"seq={m2.seq} cur={m2.cur}")
    m2.close()


def section_hotkeys(M, tmp):
    """4. §8.9 control 1: an edge fires ONCE PER PRESS and not once per poll."""
    print("\n4. the hotkey pump: one action per PRESS, against a fake user32")
    fake = FakeUser32(mod_norepeat=M.MOD_NOREPEAT, wm_hotkey=M.WM_HOTKEY)
    hk = M.Hotkeys(user32=fake, last_error=lambda: 0).register()
    # 0x78/0x79/0x7A ARE LITERALS HERE AND THAT IS THE WHOLE CHECK. This read
    # `== {M.VK_F9, M.VK_F10, M.VK_F11}`, computed FROM the module's own symbols, so a
    # marks.py that took GLOBAL hotkeys on 0x1B/0x0D/0x20 -- ESCAPE, ENTER and SPACE,
    # SWALLOWED away from Guild Wars for a whole live session -- passed all 139 checks
    # and exited 0, MEASURED. `_vk_name` relabels them too, so even the refusal message
    # still said "VK_F9". That is exactly the failure section 7's TOLERANCE literal cites
    # test_agentlife.py for (twelve of fourteen combat constants free to move with 125
    # checks green), and it was applied to the tolerance and not to the three constants
    # §10.5.1 names most explicitly. A symbol appearing in a test file is not a check.
    CHECK((M.VK_F9, M.VK_F10, M.VK_F11) == (0x78, 0x79, 0x7A),
          "VK_F9/F10/F11 are 0x78/0x79/0x7A -- the three keys §10.5.1 NAMES",
          f"{(hex(M.VK_F9), hex(M.VK_F10), hex(M.VK_F11))} -- a global RegisterHotKey "
          f"swallows its key from every application on the desktop, so which key is not "
          f"a detail: the module's own argument for refusing the GetAsyncKeyState "
          f"fallback is that a mark must not also do something in the game")
    CHECK(len(fake.registered) == 3
          and {vk for _m, vk in fake.registered.values()} == {0x78, 0x79, 0x7A},
          "and those three, not the module's idea of them, are what get registered",
          f"{fake.registered} -- global because the CLIENT owns the foreground; the "
          f"operator is looking at Guild Wars, not at this console")
    CHECK([_vk for _vk, _a in M.DEFAULT_BINDINGS] == [0x78, 0x79, 0x7A]
          and [a for _vk, a in M.DEFAULT_BINDINGS] == ["advance", "repeat", "note"],
          "and F9->advance, F10->repeat, F11->note, in §10.5.1's own order",
          f"{M.DEFAULT_BINDINGS} -- the ORDER matters as much as the set: swapping "
          f"advance and repeat leaves the same three keys registered and mislabels every "
          f"mark in the session")
    CHECK(all(mods & M.MOD_NOREPEAT for mods, _vk in fake.registered.values()),
          "each with MOD_NOREPEAT, which is the OS doing the edge detection",
          f"mods={sorted({m for m, _ in fake.registered.values()})}")

    # ---- THE HANDLE DOES NOT SURVIVE __init__. This is the capability half of section
    # 5's structural claim, and it is measured on the OBJECT rather than on the tree:
    # section 5 can only say what the scan noticed, while this says what exists.
    held = [k for k, v in vars(hk).items() if v is fake]
    CHECK(not held,
          "the Hotkeys object retains NO reference to the user32 handle",
          f"attributes holding it: {held} (object has {sorted(vars(hk))}) -- "
          f"`self.user32` used to be public, and `hk.user32['Send' + 'Input']` resolves a "
          f"real _FuncPtr on a real WinDLL, verified against a live handle. Three "
          f"sabotages reaching SendInput that way passed all 139 checks. Binding the four "
          f"functions in __init__ and letting the handle go out of scope removes the "
          f"capability instead of scanning for its use")

    # ---- THE CONTROL. A key HELD DOWN across several passes of the loop.
    fake.hold(M.VK_F9)
    edge = [hk.poll(0) for _ in range(5)]
    level = [poll_by_level(fake, M.DEFAULT_BINDINGS) for _ in range(5)]
    CHECK(sum(len(x) for x in edge) == 1 and edge[0] == ["advance"],
          "a HELD F9 across five passes emits ONE advance",
          f"{edge} -- this is the check that separates a queue from a level. A mark "
          f"is an instant the operator chose; five marks for one press would put four "
          f"labels on traffic nobody labelled")
    CHECK(sum(len(x) for x in level) == 5,
          "CONTROL: the GetAsyncKeyState rival emits FIVE for the same held key",
          f"{level} -- reproduced live in this process on this same fake, so the "
          f"comparison is between two answers rather than between an answer and a "
          f"sentence. It is also what the module would be if RegisterHotKey failed "
          f"and it fell back instead of refusing")
    CHECK(all(x == [] for x in edge[1:]),
          "and the four passes after the edge are quiet, not merely deduplicated",
          f"{edge[1:]} -- a de-duplicating poller would also report one action and "
          f"would report a SECOND press during the same hold as nothing")
    fake.release(M.VK_F9)

    # ---- the same claim from the other side: drop MOD_NOREPEAT and it breaks.
    sab = FakeUser32(mod_norepeat=M.MOD_NOREPEAT, wm_hotkey=M.WM_HOTKEY)
    hk_sab = M.Hotkeys(user32=sab, mods=0, last_error=lambda: 0).register()
    sab.hold(M.VK_F9)
    sab_out = [hk_sab.poll(0) for _ in range(5)]
    CHECK(sum(len(x) for x in sab_out) == 5,
          "SABOTAGE: the same module with mods=0 emits FIVE for one held key",
          f"{sab_out} -- MOD_NOREPEAT is not decoration and nothing structural sees "
          f"it: the queue, the swallow and the refusal-to-poll are all still there. "
          f"Run against the real bindings this is the only check that reddens")
    sab.release(M.VK_F9)
    hk_sab.unregister()

    # ---- presses, in order, one per press
    fake.press(M.VK_F9)
    fake.press(M.VK_F10)
    fake.press(M.VK_F11)
    CHECK(hk.poll(0) == ["advance", "repeat", "note"],
          "three presses in one pass come back in press order",
          "WM_HOTKEY is queued, so the pass rate never changes the count or the order")
    CHECK(hk.poll(0) == [], "and the queue is then empty", "PM_REMOVE takes each once")

    # ---- the drain comes before the wait
    before = len([c for c in fake.calls if c == "MsgWaitForMultipleObjects"])
    fake.press(M.VK_F9)
    fake.calls.clear()
    hk.poll(200)
    CHECK(fake.calls and fake.calls[0] == "PeekMessageW"
          and "MsgWaitForMultipleObjects" not in fake.calls,
          "a press already in the queue is served with NO wait at all",
          f"calls this pass: {fake.calls} (waits before: {before}) -- 'wait, then peek "
          f"once' is the classic Win32 message-loop bug and it costs a timeout per "
          f"mark at best. The drain comes first")

    # ---- and it peeks the WHOLE range
    fake.post_raw(0x0113)                              # WM_TIMER, nothing to do with us
    fake.press(M.VK_F10)
    fake.peek_ranges.clear()
    out = hk.poll(0)
    CHECK(out == ["repeat"] and not fake.queue,
          "an unrelated message is REMOVED and discarded, not left in the queue",
          f"{out}, queue now {list(fake.queue)} -- a filtered peek leaves it there and "
          f"MsgWaitForMultipleObjects then wakes instantly forever on a message nobody "
          f"removes: a busy loop that looks like a working one")
    CHECK(all(r == (0, 0) for r in fake.peek_ranges),
          "because the peek asks for the whole range",
          f"ranges {fake.peek_ranges}")

    # ---- WM_QUIT is a pseudo-action, not a mark
    fake.post_raw(M.WM_QUIT)
    CHECK(hk.poll(0) == ["quit"], "WM_QUIT comes back as the pseudo-action 'quit'",
          "so something in the process can end the run without the operator")
    took = sorted(hk.ids) or sorted(fake.unregistered)
    hk.unregister()
    CHECK(sorted(fake.unregistered) == sorted(took) and not fake.registered
          and not hk.ids,
          "and unregister releases every hotkey it took, all three of them",
          f"took {took}, released {sorted(fake.unregistered)} -- a leaked global hotkey "
          f"swallows the operator's F9 for every later session, and 'already "
          f"registered' is one of this module's own refusals, so a leak would make the "
          f"NEXT run refuse to start")
    CHECK(refused(hk.unregister) is None and len(fake.unregistered) == 3,
          "and unregister is safe to call again, releasing nothing twice",
          f"{fake.unregistered} -- run()'s finally calls it, and so does __exit__, and "
          f"so does the atexit hook")

    # ---- all or nothing
    f2 = FakeUser32(mod_norepeat=M.MOD_NOREPEAT, wm_hotkey=M.WM_HOTKEY, fail_on=2)
    exc = refused(M.Hotkeys(
        user32=f2, last_error=lambda: M.ERROR_HOTKEY_ALREADY_REGISTERED).register)
    CHECK(isinstance(exc, M.HotkeyRefused),
          "REFUSED: a hotkey that cannot be taken ends the run before it starts",
          f"{str(exc).splitlines()[0]}")
    CHECK("GetAsyncKeyState" in str(exc) or "poll" in str(exc),
          "and the refusal says WHY there is no fallback to polling",
          "a poll does not swallow the key, so every mark would also fire whatever GW "
          "binds to that F-key. A silently perturbing instrument is worse than none, "
          "and this is the only place a reader finds that out")
    CHECK(not f2.registered and f2.unregistered == [M.HOTKEY_BASE],
          "and it leaves NO partial registration behind -- it took F9 and gave it back",
          f"registered={f2.registered} released={f2.unregistered} against "
          f"[{M.HOTKEY_BASE}]. The failure is on the SECOND key, so 'no partial state' "
          f"is a claim about the first one specifically: leaving F9 held by a process "
          f"that then exited is precisely what makes a later run refuse")


def section_teardown(M, tmp):
    """4b. A hotkey cannot survive this object -- the five paths on which it once did."""
    print("\n4b. teardown: five leak paths, against a fake keeping its OWN OS-side ledger")

    # THE LEDGER IS THE FAKE'S `registered` DICT, never the object's bookkeeping. Finding
    # 3c is precisely that the two can disagree: UnregisterHotKey returned 0, the module
    # popped the id anyway, and `hk.ids` was empty while the OS held all three keys. A
    # check reading `hk.ids` would have passed on every one of these.
    f_clean = FakeUser32(mod_norepeat=M.MOD_NOREPEAT, wm_hotkey=M.WM_HOTKEY)
    hk_clean = M.Hotkeys(user32=f_clean, last_error=lambda: 0).register()
    left = hk_clean.unregister()
    CHECK(not f_clean.registered and not left,
          "POSITIVE CONTROL: an ordinary register/unregister leaves the OS ledger EMPTY",
          f"ledger {f_clean.registered}, unreleased {left} -- a teardown that refused "
          f"everything, or a ledger that is always empty, would make all five checks "
          f"below pass while measuring nothing")

    # ---- (1) RegisterHotKey RAISES mid-loop. The failure branch only ever fired on a
    # falsy RETURN, and the atexit hook was installed AFTER the loop, so there was no net
    # of any kind: ledger {F9, F10}, UnregisterHotKey called 0 times, 0 atexit callbacks.
    f1 = FakeUser32(mod_norepeat=M.MOD_NOREPEAT, wm_hotkey=M.WM_HOTKEY, raise_on=3)
    exc = refused(M.Hotkeys(user32=f1, last_error=lambda: 0).register)
    CHECK(isinstance(exc, OSError) and not f1.registered,
          "LEAK 1: RegisterHotKey RAISING on the third key releases the first two",
          f"{type(exc).__name__}, ledger now {f1.registered} (released "
          f"{f1.unregistered}) -- the raise propagates, which is right, but it must not "
          f"take two global hotkeys with it")

    # ---- (2) the same through main()'s `with Hotkeys() as hk`: __enter__ raised, so
    # __exit__ never ran and the context manager was no net either.
    f2 = FakeUser32(mod_norepeat=M.MOD_NOREPEAT, wm_hotkey=M.WM_HOTKEY, raise_on=2)

    def enter_it():
        with M.Hotkeys(user32=f2, last_error=lambda: 0):
            pass
    exc = refused(enter_it)
    CHECK(exc is not None and not f2.registered,
          "LEAK 2: and through `with Hotkeys() as hk`, which is what main() writes",
          f"{type(exc).__name__}, ledger {f2.registered} -- __enter__ raised so __exit__ "
          f"never ran; the release has to happen inside register() or not at all")

    # ---- (3) Ctrl-C between two RegisterHotKey calls. KeyboardInterrupt is a
    # BaseException, so `except Exception` around the loop would not have seen it.
    f3 = FakeUser32(mod_norepeat=M.MOD_NOREPEAT, wm_hotkey=M.WM_HOTKEY, interrupt_on=2)
    hk3 = M.Hotkeys(user32=f3, last_error=lambda: 0)
    try:
        hk3.register()
        interrupted = False
    except KeyboardInterrupt:
        interrupted = True
    CHECK(interrupted and not f3.registered,
          "LEAK 3: Ctrl-C between two registrations still releases the first key",
          f"ledger {f3.registered} -- an operator interrupting a run that is starting is "
          f"the ordinary way to change their mind, and it left F9 held")

    # ---- (4) UnregisterHotKey RETURNING 0. Measured on real Win32: called from a thread
    # that does not own the hotkey it returns 0 with WinError 1419 and the key stays
    # taken, and a fresh RegisterHotKey then gets 1409. The module discarded the answer.
    f4 = FakeUser32(mod_norepeat=M.MOD_NOREPEAT, wm_hotkey=M.WM_HOTKEY,
                    unregister_fails=True)
    hk4 = M.Hotkeys(user32=f4, last_error=lambda: 0).register()
    said = []
    left4 = hk4.unregister(say=said.append)
    CHECK(len(left4) == 3 and len(f4.registered) == 3 and hk4.unreleased == left4,
          "LEAK 4: a release the OS REFUSES is reported, not believed",
          f"unreleased {left4} with the OS still holding {sorted(f4.registered)} -- the "
          f"return value used to be discarded, so 'released' and 'refused' were the same "
          f"answer, and the module's own next refusal reads 'something already holds it: "
          f"another marks.py, or an app that binds the F-keys globally' with this "
          f"process being that app")
    CHECK(said and any("still be held" in s for s in said),
          "and it SAYS so, because the operator is looking at the game",
          f"{said[:1]} -- run()'s finally passes `say` for exactly this")

    # ---- (5) Ctrl-C INSIDE unregister. The id used to be popped from `_taken` BEFORE the
    # call, so after the interrupt no later unregister -- including the atexit hook's --
    # could ever reach it, and `except Exception` did not catch it either.
    f5 = FakeUser32(mod_norepeat=M.MOD_NOREPEAT, wm_hotkey=M.WM_HOTKEY,
                    unregister_raises=1)
    hk5 = M.Hotkeys(user32=f5, last_error=lambda: 0).register()
    try:
        hk5.unregister()
        hit = False
    except KeyboardInterrupt:
        hit = True
    still = dict(f5.registered)
    hk5.unregister()                       # the second chance: atexit's, in effect
    CHECK(hit and len(still) == 3 and not f5.registered,
          "LEAK 5: Ctrl-C in teardown leaves the id RETRYABLE, and the retry frees it",
          f"interrupted with {len(still)} keys held, and a second unregister released "
          f"all of them (ledger now {f5.registered}). Popping the id before the call is "
          f"what made the retry a no-op -- the object had forgotten a key the OS still "
          f"had")

    # ---- and the ORDERING that makes leak 1 impossible, asked of the syntax tree.
    tree = ast.parse(open(M.__file__, encoding="utf-8").read())
    fn = next((n for n in ast.walk(tree)
               if isinstance(n, ast.FunctionDef) and n.name == "register"), None)
    hook = _first_stmt(fn, lambda n: (isinstance(n, ast.Call)
                                      and isinstance(n.func, ast.Attribute)
                                      and n.func.attr == "register"
                                      and isinstance(n.func.value, ast.Name)
                                      and n.func.value.id == "atexit"))
    loop = _first_stmt(fn, lambda n: isinstance(n, ast.For))
    CHECK(hook is not None and loop is not None and hook < loop,
          "and the atexit hook is installed BEFORE the registration loop, not after it",
          f"atexit.register at body statement {hook}, the loop at {loop} -- asked of the "
          f"tree because 'before the loop' is invisible to a grep, which sees both lines "
          f"and cannot order them. With the hook after the loop there is no net on any "
          f"path that does not complete the loop, which is leaks 1, 2 and 3")


def section_no_sendinput(M, tmp, module_path):
    """5. §8.9 control 2: the syntax tree contains no SendInput. Three detectors."""
    print("\n5. it READS the keyboard: no SendInput, three detectors and their blind spots")
    src = open(module_path, encoding="utf-8").read()
    tree = ast.parse(src)

    ident = writers_by_identifier(tree)
    const = writers_by_constant(tree)
    dyn = dynamic_attribute_calls(tree)
    attrs = user32_attributes(tree)

    CHECK(not ident, "DETECTOR 1 (identifiers): no input-writing call anywhere",
          f"found {sorted(ident)} -- searched {len(INPUT_WRITERS)} names: "
          f"{', '.join(INPUT_WRITERS)}")
    CHECK(not const, "DETECTOR 2 (string constants, docstrings excluded): none named",
          f"found {sorted(const)} -- this is the one that catches "
          f"getattr(user32, 'SendInput')")
    CHECK(not dyn, "DETECTOR 3a: NO dynamic-lookup primitive in the module, of any kind",
          f"found {dyn} -- searched {len(DYNAMIC_LOOKUP)} spellings: "
          f"{', '.join(DYNAMIC_LOOKUP)}. This was `getattr`/`setattr` by Name and nothing "
          f"else, and three live SendInput routes walked past it: "
          f"`__import__('operator').attrgetter('Send' + 'Input')(...)`, "
          f"`object.__getattribute__(...)` and `vars(handle)[computed]`. With none of "
          f"these present, the module can only call names its own source spells out, "
          f"which is what makes the whitelist below total rather than a sample")
    CHECK(attrs == ALLOWED_USER32,
          "DETECTOR 3b: the ONLY things fetched off the handle are the four Hotkeys names",
          f"{sorted(attrs)} against {sorted(ALLOWED_USER32)}, over handle names "
          f"{sorted(_handle_names(tree))} -- a positive whitelist, because a denylist can "
          f"only refuse the names somebody thought of. It now reads SUBSCRIPTS and "
          f"ALIASES as well as attributes: `handle['Send' + 'Input']` resolves a real "
          f"_FuncPtr on a real WinDLL (verified: `u['GetSystem' + 'Metrics'](0)` returns "
          f"the same 1920 as the attribute form) and used to be invisible here")

    CHECK(not calls_os_kill(tree), "and os.kill is never reached",
          "on Windows CPython implements os.kill(pid, 0) with TerminateProcess, so the "
          "harmless POSIX liveness idiom would kill the CLIENT mid-session -- from "
          "inside the tool whose only job is to annotate that session")
    CHECK("drive_client" not in imports_of(tree),
          "and drive_client is not imported",
          f"imports: {sorted(imports_of(tree))} -- hold_key is the thing on the other "
          f"side of this line; importing the module would put a keyboard writer one "
          f"attribute away from a tool the live rule allows to run")

    # ---- the naive rival, measured rather than argued
    raw = naive_grep(src)
    in_prose = naive_grep(docstring_text(tree))
    CHECK(raw == in_prose,
          "CONTROL: every occurrence of the word 'SendInput' in this file is PROSE",
          f"{raw} occurrence(s) in the raw source, {in_prose} of them inside "
          f"docstrings -- so a RAW GREP for the rule reddens on the sentence promising "
          f"there is none. That is exactly how test_cmsgnames.py's grep failed (it "
          f"asserted its arm's formatting and went red when the arm wrapped across two "
          f"lines) and why test_sweeploop.py's check moved to the syntax tree. The "
          f"claim is stated this way rather than as 'raw == 1' on purpose: a count "
          f"would redden the day somebody rewords the header, while this stays true "
          f"under any rewording and fails the moment a real call appears")

    # ---- the positive control: the module on the OTHER side of the line
    dc = ast.parse(open(DRIVE_CLIENT_PY, encoding="utf-8").read())
    dc_found = writers_by_identifier(dc)
    CHECK({"keybd_event", "mouse_event", "SetCursorPos"} <= dc_found,
          "POSITIVE CONTROL: drive_client.py IS flagged by detector 1",
          f"{sorted(dc_found)} -- a detector that has never fired proves nothing, and "
          f"this is the file the live-automation rule is about: the operator plays and "
          f"the harness sends no keystrokes and no clicks, because the traffic pattern "
          f"scripted input produces is what closes accounts")

    # ---- four sabotages, BUILT and parsed in every run, and the predicted detector
    # set is written out per row because that is the measurement: each of the three
    # detectors is the ONLY one that fires on one of these four, so none is decoration.
    # THE LAST THREE ROWS ARE THE ONES A SKEPTIC BUILT AS WORKING CODE AND RAN, and all
    # three passed this file at 139 checks, exit 0, before the detectors were widened.
    # They are not exotic: each resolves a real _FuncPtr off a real ctypes.WinDLL, proved
    # against a live handle (resolved, never called).
    #
    # THE `any(got)` ROW IS GONE, and its removal is a result rather than a tidy-up. It
    # asserted `any(got)` on the line after `got == want`, and `any(got)` cannot be False
    # while `got == want` is True for any row here -- four of the 139 floor checks that
    # added no independent way to fail, measured across 109 sabotage runs in which the two
    # never once disagreed. A strictly weaker restatement of the line above it is not a
    # check; it is the floor reading four higher than the file's real coverage.
    sabotages = (
        ("a bare call, the name imported: SendInput(1, None, 28)",
         "        SendInput(1, None, 28)\n", (True, False, False)),
        ("a plain call through the handle: self.user32.SendInput(...)",
         "        self.user32.SendInput(1, None, 28)\n", (True, False, True)),
        ('getattr(self.user32, "SendInput")(...)',
         '        getattr(self.user32, "SendInput")(1, None, 28)\n', (False, True, True)),
        ('getattr(self.user32, "Send" + "Input")(...)',
         '        getattr(self.user32, "Send" + "Input")(1, None, 28)\n',
         (False, False, True)),
        ('SUBSCRIPT of the handle: self.user32["Send" + "Input"](...)',
         '        self.user32["Send" + "Input"](1, None, 28)\n', (False, False, True)),
        ('attrgetter: __import__("operator").attrgetter("Send" + "Input")(...)',
         '        __import__("operator").attrgetter("Send" + "Input")'
         '(self.user32)(1, None, 28)\n', (False, False, True)),
        ("an ALIASED subscript: u = self.user32; u[''.join([...])](...)",
         "        u = self.user32\n"
         "        u[''.join(['Send', 'Input'])](1, None, 28)\n", (False, False, True)),
    )
    anchor = "    def _drain(self):\n"
    CHECK(anchor in src, "the sabotage anchor is still in the source",
          f"{anchor.strip()!r} -- the sabotages are built by INSERTION at a real line, "
          f"so if the module is refactored past this point they must be re-aimed "
          f"rather than silently inserted into nothing")
    for label, line, (want1, want2, want3) in sabotages:
        bad = src.replace(anchor, anchor + line, 1)
        bt = ast.parse(bad)
        got = (bool(writers_by_identifier(bt)), bool(writers_by_constant(bt)),
               bool(dynamic_attribute_calls(bt)) or
               not user32_attributes(bt) <= ALLOWED_USER32)
        CHECK(got == (want1, want2, want3),
              f"SABOTAGE caught, and by the right detector: {label}",
              f"detectors (identifier, constant, dynamic/whitelist) fired {got}, "
              f"predicted {(want1, want2, want3)}. This is the measurement that says "
              f"which detector is load-bearing: 1 is the ONLY one that sees a bare "
              f"imported name, 2 the only one that sees a getattr on a literal that "
              f"is not routed through the handle, and 3 the only one that sees a name "
              f"assembled at run time -- which is now three different ways of assembling "
              f"it, because the first version of 3 knew only the word `getattr`")


def section_bind(M, tmp):
    """6. THE CRITERION: a mark lands on the same axis as a real capture's segments."""
    print("\n6. bind(): a mark on WIRE time, against a capture the real producer wrote")
    wc, how = import_wirecapture()
    print(f"   wirecapture {how}")

    # ---- THE PRODUCER, MEASURED RATHER THAN GREPPED, AND FIRST IN THE SECTION.
    # This was `'"t0_perf": t0' in src` over wirecapture.py's raw source, and it could
    # only ever go red for the wrong reason: a BEHAVIOUR-PRESERVING reformat
    # (`**{"t0" + "_perf": t0}`) reddened it, 1 red with everything else green, while a
    # genuinely broken key CRASHED the run at check 67 before the grep was reached. A raw
    # grep of another module's source, in a file whose own header lectures about
    # test_cmsgnames.py's. What the contract needs is that t0_perf is the RAW perf reading
    # AND is the origin every segment is stamped from -- ONE number used twice -- which a
    # capture with a distinctive epoch states directly. It runs before anything in this
    # section can fail, so when the producer is broken this is what names it.
    # MEASURED against four copied trees: unmodified 0 red, the reformat 0 red (it
    # changed nothing and must not redden), the key renamed to "t0_PERF" red, t0_perf
    # published as the WALL epoch red, and t0_perf published 0.9 s off the segments' own
    # origin red -- which is the skeptic's silent-mislabelling capture, from the
    # producer's side.
    c2 = Clock(perf0=777.5, wall0=1_600_000_000.0)
    p2 = os.path.join(tmp, "producer.jsonl")
    fh2, rec2 = wc.open_capture(p2, "10.0.0.2:1", "10.0.0.3:80", 7, {80},
                                clock=c2.perf_counter, wall=c2.time)
    c2.tick(2.5)
    rec2("s2c", 1, b"\x09")
    fh2.close()
    pm = [json.loads(l) for l in open(p2, encoding="utf-8") if '"wire_meta"' in l][0]
    ps = [json.loads(l) for l in open(p2, encoding="utf-8") if '"kind": "wire"' in l][0]
    CHECK(pm.get("t0_perf") == 777.5 and pm.get("t0_wall") == 1_600_000_000.0
          and abs(ps["t"] - 2.5) < 1e-9
          and abs((ps["t"] + pm.get("t0_perf", 0)) - c2.perf) < 1e-9,
          "the PRODUCER's t0_perf is the raw perf reading its segments measure from",
          f"wire_meta t0_perf={pm.get('t0_perf')} t0_wall={pm.get('t0_wall')}, segment "
          f"t={ps['t']} at perf {c2.perf} -- ONE t0 for the header and for every stamp. "
          f"A producer publishing a DIFFERENT t0 from the one its segments were stamped "
          f"against binds SILENTLY: a skeptic built exactly that 0.9 s apart and both "
          f"clock channels reported 0.0001 ms of skew, because both clocks were fine")

    clk = Clock()
    wpath = os.path.join(tmp, "wire.jsonl")
    fh, record = wc.open_capture(wpath, "10.0.0.2:63155", "54.164.212.177:80", 1234,
                                 {80}, clock=clk.perf_counter, wall=clk.time)
    p = write_plan(os.path.join(tmp, "b_plan.tsv"), PLAN_ROWS)
    # THE MARKER OPENS 31 SECONDS AFTER THE SNIFFER, and that gap is a control, not
    # colour. Every fixture in this file used to set marks_meta's epoch EQUAL to
    # wire_meta's, so the test could not tell WHICH file's epoch bind() was reading --
    # which is the one thing that makes it a cross-process check at all. A skeptic built
    # a bind() sourcing the WALL half from the MARKS file's own t0_wall and it passed all
    # 139 checks, then silently bound a mark at t=10.0 that belonged at t=40.0. In a real
    # run the sniffer goes up first and the operator starts marking afterwards, so the
    # gap is also what the artifact actually looks like.
    clk.tick(31.0)
    m = M.open_marks(tmp, p, out=os.path.join(tmp, "b_marks.jsonl"),
                     clock=clk.perf_counter, wall=clk.time, wire_path=wpath)

    # THE 100 ms IS NOT DECORATION AND IT WAS PUT HERE BY A SABOTAGE. With the two wall
    # clocks in exact agreement, a binder returning `t_wall - t0_wall` gives the SAME
    # number as one returning `t_perf - t0_perf`, so the segment equality below passed
    # against a wall-clock binder and this section could not tell the two apart --
    # MEASURED, the `wallbind` sabotage reddened 2 checks and neither was in this
    # section. A hundred milliseconds of disagreement is inside tolerance (so the bind
    # still succeeds, which is the realistic condition) and is exactly enough to make
    # the wrong epoch land off every segment.
    clk.skew = 0.100

    clk.tick(1.25)
    record("s2c", 1, b"\x01\x02")
    m.advance()                       # the SAME clock reading as that segment
    clk.tick(3.0)
    record("s2c", 2, b"\x03")
    m.note()
    clk.tick(0.75)
    m.advance()
    m.close()
    fh.close()

    segs = [json.loads(l) for l in open(wpath, encoding="utf-8")
            if '"kind": "wire"' in l]
    rows = M.bind(wpath, m.path, plan=p)

    # THE ORDER CLAIM NEEDS A NON-PALINDROME. `[r.mark for r in rows]` was
    # ["advance", "note", "advance"], which reads the same backwards -- so a bind() built
    # from `zip(marks[::-1], rows[::-1])`, returning every mark in REVERSE, left this
    # check GREEN. It was caught by five others, so the run was red; but the check that
    # claims order could not see a reversal. The step ordinals and the times can.
    CHECK(len(rows) == 3
          and [(r.mark, r.step) for r in rows] == [("advance", 0), ("note", 0),
                                                   ("advance", 1)]
          and [r.t for r in rows] == sorted(r.t for r in rows),
          "every mark comes back, in order -- by kind, by step ordinal AND by time",
          f"{[(r.mark, r.step, r.t) for r in rows]} -- a reversal gives "
          f"[('advance', 1), ('note', 0), ('advance', 0)], which the kinds alone cannot "
          f"tell from the truth because advance/note/advance is a palindrome")
    CHECK(rows[0].t == segs[0]["t"] and rows[1].t == segs[1]["t"],
          "AND A MARK TAKEN AT A SEGMENT'S INSTANT LANDS ON THAT SEGMENT'S OWN t",
          f"marks {rows[0].t}, {rows[1].t} against segments {segs[0]['t']}, "
          f"{segs[1]['t']} -- this is the criterion, and it is deliberately not a "
          f"comparison with a number this file wrote down. The epoch comes from "
          f"wirecapture's wire_meta, the stamps from marks.py's Marker, and the two "
          f"modules never speak: a binder that dropped the epoch, doubled it or took "
          f"it from the MARKS file instead returns plausible seconds and fails here")
    CHECK(rows[2].t == segs[1]["t"] + 0.75,
          "and a mark taken between segments lands between them",
          f"{rows[2].t} -- monotonic on the capture's own axis")
    CHECK(tuple(rows[0]) == (rows[0].t, "advance", 0, "character select, settled"),
          "the rows are (t, mark, step, text) 4-tuples and unpack as such",
          f"{tuple(rows[0])} -- §10.5.1's shape; a namedtuple so `t, mark, step, text "
          f"= rows[0]` works and `rows[0] == (…)` compares equal to a plain tuple")

    # ---- THE SAME CRITERION ON TICKS THAT ARE NOT DYADIC RATIONALS, because the `==`
    # above is exact only by the fixture's arithmetic. 1.25/3.0/0.75 survive bind()'s
    # `round(dperf, 6)` to the bit; 1.30/3.10/0.70 do NOT -- a skeptic re-ran this section
    # with those ticks and got 0 of 3 (mark t=1.3 against segment t=1.2999999999999545),
    # and twenty ticks of 7.3 gave 0 of 20. The error is ~1e-13 s and harmless, but the
    # claim as written could not hold against a real capture, where every perf delta is an
    # arbitrary float. So the exact form is kept (it is the strongest available and it is
    # TRUE for those ticks) and the general form is stated beside it at bind()'s own
    # rounding, with the wall-epoch rival 100 ms away as the control that 1 us is not a
    # tolerance wide enough to hide a wrong epoch in.
    c3 = Clock(perf0=5000.0)
    w3 = os.path.join(tmp, "nondyadic_wire.jsonl")
    fh3, rec3 = wc.open_capture(w3, "10.0.0.2:2", "10.0.0.3:80", 8, {80},
                                clock=c3.perf_counter, wall=c3.time)
    p3 = write_plan(os.path.join(tmp, "nd_plan.tsv"), PLAN_ROWS)
    c3.tick(11.0)
    m3 = M.open_marks(tmp, p3, out=os.path.join(tmp, "nd_marks.jsonl"),
                      clock=c3.perf_counter, wall=c3.time, wire_path=w3)
    c3.skew = 0.100
    nd_pairs = []
    for dt in (1.30, 3.10, 0.70, 7.3, 0.1):
        c3.tick(dt)
        rec3("s2c", 1, b"\x01")
        m3.advance() if len(nd_pairs) < 3 else m3.note()
        nd_pairs.append(dt)
    m3.close()
    fh3.close()
    nd_segs = [json.loads(l)["t"] for l in open(w3, encoding="utf-8")
               if '"kind": "wire"' in l]
    nd_rows = M.bind(w3, m3.path)
    off = [abs(r.t - s) for r, s in zip(nd_rows, nd_segs)]
    CHECK(len(nd_rows) == 5 and max(off) <= 1e-6,
          "and it holds on NON-DYADIC ticks too, to bind()'s own 1 us rounding",
          f"worst |mark.t - segment.t| = {max(off):.3e} s over {len(off)} pairs at ticks "
          f"{nd_pairs} -- exact equality is a property of 1.25/3.0/0.75, not of the "
          f"binding, and a real capture has neither. The wall-epoch rival is 0.100 s "
          f"away, five orders above this bound, so 1 us cannot hide a wrong epoch")

    # ---- the rival epoch: t_wall - t0_wall, which is the OTHER plausible binding
    t0_perf, t0_wall = M.wire_epoch(wpath)
    _meta, raw_marks = M.read(m.path)
    by_wall = [round(r["t_wall"] - t0_wall, 6) for r in raw_marks]
    CHECK(all(abs(abs(w - r.t) - 0.100) < 1e-9 for w, r in zip(by_wall, rows))
          and not any(w == s["t"] for w in by_wall for s in segs),
          "SABOTAGE: a binder using the WALL delta lands on none of the segments",
          f"wall-bound {by_wall} against segments {[s['t'] for s in segs]} -- the two "
          f"clocks in this fixture disagree by 100 ms, which is inside tolerance and "
          f"is what two real processes look like. `t_wall - t0_wall` is the other "
          f"plausible reading of the same two records and it is wrong by exactly that: "
          f"wall is the WITNESS, perf is the answer")

    d = M.drift(wpath, m.path)
    worst = max(abs(r.skew) for r in d)
    CHECK(len(d) == 3 and abs(worst - 0.100) < 1e-6,
          "drift() reports the same computation with no verdict, and measures the 100 ms",
          f"worst |dperf - dwall| = {worst * 1000:.4f} ms against the 100 ms this "
          f"fixture was built with -- so the tolerance in section 7 is approached from "
          f"a KNOWN skew rather than from whatever this machine happened to do. The "
          f"1 us slack is float64 and not a fudge: a UTC wall clock is ~1.7e9, where "
          f"the representable step is about 240 ns, so a wall DELTA cannot be exact "
          f"however carefully the fixture is built. The perf side, whose origin is "
          f"1000.0, is exact -- which is why the segment equality above is `==`")

    notes = os.path.join(tmp, "b_notes.tsv")
    with open(notes, "w", encoding="utf-8") as nf:
        nf.write("1\tthe tooltip said 12g\n")
    annotated = M.bind(wpath, m.path, plan=p, notes=notes)
    CHECK(annotated[1].text == "the tooltip said 12g"
          and rows[1].text == "",
          "a note's text is attached AFTERWARDS, by ordinal, from the side file",
          f"{annotated[1]} -- and the same bind without notes still reads "
          f"{rows[1].text!r}, so the text lives outside the capture until somebody "
          f"puts it there deliberately")

    # ---- THE RIVAL EPOCH SOURCE: marks_meta's own t0, which is 31 s later.
    meta_marks, _raw = M.read(m.path)
    by_marks_epoch = [round(r["t_perf"] - meta_marks["t0_perf"], 6) for r in raw_marks]
    CHECK(abs(meta_marks["t0_perf"] - t0_perf - 31.0) < 1e-9
          and not any(abs(w - r.t) < 1e-9 for w, r in zip(by_marks_epoch, rows)),
          "SABOTAGE: a binder reading the epoch from the MARKS file lands 31 s early",
          f"marks-epoch {by_marks_epoch} against bind()'s {[r.t for r in rows]} -- the "
          f"marks file carries its OWN t0_perf/t0_wall (when the marker opened) and the "
          f"capture carries the capture's. They are different numbers in every real run, "
          f"and until this fixture made them different a binder that confused the two "
          f"was indistinguishable from the right one")

    return wpath, m.path, p


def section_drift(M, tmp, wpath):
    """7. §8.9 control 3: bind() goes red when the two clocks disagree past tolerance."""
    print("\n7. the two-clock agreement is ASSERTED, in both directions")
    CHECK(M.wire_epoch(wpath) == (1000.0, 1_700_000_000.0),
          "the hand-built fixtures below are aimed at the capture's REAL epoch",
          f"{M.wire_epoch(wpath)} -- every skew in this section is a delta from those "
          f"two numbers, so if Clock's defaults ever moved, 'inside tolerance' and "
          f"'outside tolerance' would both become 'wildly outside' and the positive "
          f"control would redden for a reason that has nothing to do with drift. This "
          f"names the coupling instead of leaving it in two places")
    inside = write_marks_file(
        os.path.join(tmp, "d_ok.jsonl"),
        [mark_rec(1, "advance", 0, "a", 1.0, 1.0),
         mark_rec(2, "advance", 1, "b", 5.0, 5.249),
         mark_rec(3, "note", 1, "", 9.0, 9.0)])
    # GUARDED, because when the tolerance is TIGHTENED this positive control is what
    # refuses -- and it used to do so as a bare traceback out of section 7, with no
    # verdict banner and no ledger. A skeptic swept TOLERANCE to 0.100 and 0.0005 and got
    # exit 1 with ZERO reds both times: the whole run died in the section whose subject
    # is the tolerance. main()'s `guarded` catches it now; this keeps the section running.
    rows_or = refused(M.bind, wpath, inside)
    rows = [] if rows_or is not None else M.bind(wpath, inside)
    CHECK(rows_or is None and len(rows) == 3 and rows[1].t == 5.0,
          "POSITIVE CONTROL: 249 ms of disagreement is INSIDE tolerance and binds",
          f"{rows_or if rows_or is not None else rows} -- a binder that refuses "
          f"everything is useless, and this is the check that says the tolerance is a "
          f"tolerance rather than a wall. The bound t is still the PERF delta; wall is "
          f"the witness, not the answer")

    # ---- THE BOUNDARY, TO THE MILLISECOND, IN BOTH DIRECTIONS. §10.5.1 says
    # `|dperf - dwall| <= 0.250`, so EXACTLY 250 ms binds. Two skeptic sabotages survived
    # the old fixtures: `>` changed to `>=` (139 green), and TOLERANCE swept to 0.400 or
    # 0.599 (ONE red, the literal below). The fixtures sat at 249 ms and 600 ms, so every
    # value in (0.249, 0.600) left all the BEHAVIOURAL checks green and the number was
    # held by a single equality -- test_agentlife.py's failure in the section that cites
    # it. 0.25 is exactly representable in binary, so this pair is exact rather than
    # approximate: the two checks below are 1 ms apart and no tolerance can satisfy both
    # unless it is 0.250 with a strict `>`.
    at = write_marks_file(os.path.join(tmp, "d_at.jsonl"),
                          [mark_rec(1, "advance", 0, "a", 5.0, 5.25)])
    just_past = write_marks_file(os.path.join(tmp, "d_past.jsonl"),
                                 [mark_rec(1, "advance", 0, "a", 5.0, 5.250001)])
    at_exc = refused(M.bind, wpath, at)
    past_exc = refused(M.bind, wpath, just_past)
    CHECK(at_exc is None,
          "BOUNDARY: EXACTLY 250 ms of disagreement binds -- §10.5.1 says `<= 0.250`",
          f"{at_exc} -- a `>=` comparison refuses here and is otherwise invisible: it "
          f"passed all 139 checks. 0.25 is exact in binary, so this is a real boundary "
          f"and not a rounding argument")
    CHECK(isinstance(past_exc, M.ClockDrift),
          "and 250.001 ms REFUSES, so the tolerance is pinned from both sides",
          f"{type(past_exc).__name__} -- these two are 1 ms apart, so any tolerance "
          f"other than 0.250 reddens one of them BEHAVIOURALLY. The literal below is now "
          f"a statement of intent rather than the only thing holding the number")

    outside = write_marks_file(
        os.path.join(tmp, "d_bad.jsonl"),
        [mark_rec(1, "advance", 0, "a", 1.0, 1.0),
         mark_rec(2, "advance", 1, "b", 5.0, 5.60),
         mark_rec(3, "note", 1, "", 9.0, 9.0)])
    exc = refused(M.bind, wpath, outside)
    CHECK(isinstance(exc, M.ClockDrift),
          "REFUSED: 600 ms of disagreement on ONE mark",
          f"{type(exc).__name__}: {str(exc).splitlines()[0][:150]}")
    CHECK(isinstance(exc, M.BindError),
          "and ClockDrift is a BindError, so a caller catching the general refusal "
          "catches it", f"mro: {[c.__name__ for c in type(exc).__mro__[:4]]}")
    CHECK("1 of 3" in str(exc),
          "and it names the SHAPE: one mark of three, i.e. a stamping fault",
          f"{str(exc).splitlines()[0][:200]} -- one violator out of three is a bad "
          f"stamp at that mark; all three is clock incomparability, and they are "
          f"different diagnoses. A bare 'mark 2 is off by 0.35s' throws that away")

    everything = write_marks_file(
        os.path.join(tmp, "d_all.jsonl"),
        [mark_rec(1, "advance", 0, "a", 1.0, 2.0),
         mark_rec(2, "advance", 1, "b", 5.0, 7.0),
         mark_rec(3, "note", 1, "", 9.0, 12.0)])
    exc_all = refused(M.bind, wpath, everything)
    CHECK(isinstance(exc_all, M.ClockDrift) and "EVERY mark" in str(exc_all),
          "and when EVERY mark disagrees it says the timebase itself is not shared",
          f"{str(exc_all).splitlines()[0][:200]}")
    CHECK("RATE" in str(exc_all) or "rate" in str(exc_all),
          "and a skew that GROWS is reported as a rate, not as an offset",
          f"{str(exc_all).splitlines()[0][-160:]} -- a drifting clock and a constant "
          f"offset are different faults with different fixes, and the numbers to tell "
          f"them apart are already in hand")

    flat = write_marks_file(
        os.path.join(tmp, "d_flat.jsonl"),
        [mark_rec(1, "advance", 0, "a", 1.0, 2.0),
         mark_rec(2, "advance", 1, "b", 5.0, 6.0),
         mark_rec(3, "note", 1, "", 9.0, 10.0)])
    exc_flat = refused(M.bind, wpath, flat)
    CHECK(isinstance(exc_flat, M.ClockDrift) and "constant offset" in str(exc_flat),
          "CONTROL: a FLAT skew is reported as an offset, not as a rate",
          f"{str(exc_flat).splitlines()[0][-150:]} -- the two messages must differ, or "
          f"the diagnosis above is a fixed string that says 'rate' whatever happened")

    # ---- THE THIRD SHAPE, AND IT IS THE COMMONEST REAL CAUSE. The vocabulary had two
    # words -- OFFSET and RATE -- and a skeptic fed it the one it could not say: a single
    # +0.5 s wall-clock step at t=70 of a 146 s session, an NTP correction or a resume,
    # with the perf axis untouched and all 20 perf-derived times CORRECT. It answered with
    # BOTH of its hypotheses and was wrong about both -- "11 of 20 marks disagree, so this
    # is a stamping fault at those marks" (it was ONE clock event) and "the skew moves
    # -3.6 ms per second, so it is a RATE" (a step averaged over a session looks exactly
    # like a rate). wirecapture.mark_skew already carries the lesson in a comment: a wrong
    # diagnosis sends someone hunting an NTP event that never happened.
    step = write_marks_file(
        os.path.join(tmp, "d_step.jsonl"),
        [mark_rec(1, "advance", 0, "a", 1.0, 1.0),
         mark_rec(2, "advance", 1, "b", 2.0, 2.0),
         mark_rec(3, "note", 1, "", 3.0, 3.5),
         mark_rec(4, "note", 1, "", 4.0, 4.5),
         mark_rec(5, "note", 1, "", 5.0, 5.5)])
    exc_step = refused(M.bind, wpath, step)
    CHECK(isinstance(exc_step, M.ClockDrift) and "STEP" in str(exc_step)
          and "mark 2" in str(exc_step) and "mark 3" in str(exc_step),
          "and a single wall-clock STEP is named as one discontinuity, at its boundary",
          f"{str(exc_step).splitlines()[0][:230]} -- the skew is flat either side and "
          f"jumps once between marks 2 and 3. Three of five marks 'disagree' and there "
          f"is ONE fault; the count is not the number of faults")
    CHECK("RATE" not in str(exc_step) and "stamping fault" not in str(exc_step),
          "CONTROL: and it does NOT also call the step a rate or a bad stamp",
          f"{str(exc_step).splitlines()[0][-200:]} -- both of those are what it used to "
          f"say about this exact fixture. A diagnosis that offers every hypothesis is "
          f"not a diagnosis, and the two it offered were the two it could express")
    shape, _why = M.drift_shape(M.drift(wpath, step))
    flat_shape, _w2 = M.drift_shape(M.drift(wpath, flat))
    CHECK(shape == "STEP" and flat_shape == "OFFSET",
          "and drift_shape separates a STEP from an OFFSET on the same three numbers",
          f"step fixture -> {shape}, flat fixture -> {flat_shape}. The cumulative skew "
          f"decides WHETHER to refuse (a constant offset -- the launch-gap hypothesis, "
          f"the one thing this check has real power over -- is invisible pairwise); the "
          f"PAIRWISE differences decide what to call it (a step is invisible "
          f"cumulatively, because every mark after it inherits the displacement)")

    CHECK(M.TOLERANCE == 0.250,
          "the tolerance is §10.5.1's 0.250 s",
          "written as a literal here rather than read off the module. It is no longer "
          "the ONLY thing holding the number -- the 250/250.001 pair above reddens "
          "behaviourally for any other value, which is what a sweep to 0.400 and 0.599 "
          "showed was missing: ONE red each, this equality, while every behavioural "
          "check stayed green. That is test_agentlife.py's failure, twelve of fourteen "
          "combat constants free to move with 125 checks green. What the tolerance can "
          "actually DETECT is stated in marks.py's header and is not what its name "
          "suggests: two processes on this machine agree to 5 MICROSECONDS over 12 "
          "spawns, so 0.250 s is ~50,000x the phenomenon and will never fire for it. It "
          "fires on a per-process perf epoch (a launch gap) and on a wall clock that "
          "moved, and the number is kept because it is the spec's")

    # ---- the sabotage: a binder with no assertion at all
    def tolerant_bind(wire_path, marks_path):
        """bind() with the drift check deleted -- the version §8.9 exists to forbid."""
        _meta, marks = M.read(marks_path)
        t0_perf, _t0_wall = M.wire_epoch(wire_path)
        return [M.Mark(round(r["t_perf"] - t0_perf, 6), r["mark"], r["step"],
                       r.get("text") or "") for r in marks]

    loose_ok = tolerant_bind(wpath, inside)
    loose_bad = tolerant_bind(wpath, outside)
    CHECK([tuple(r) for r in loose_ok] == [tuple(r) for r in rows]
          and len(loose_bad) == 3,
          "SABOTAGE: an unchecked binder returns the SAME rows for the good fixture "
          "and happily binds the bad one",
          f"good: identical to bind()'s own answer. bad: {len(loose_bad)} rows where "
          f"bind() refuses. That is the whole of §8.9's criterion -- on data that "
          f"happens to agree, a checked binding and an unchecked one are the same "
          f"function, and only the disagreeing fixture can tell them apart")

    missing = write_marks_file(
        os.path.join(tmp, "d_noclock.jsonl"),
        [{"kind": "mark", "seq": 1, "mark": "advance", "step": 0, "text": "a",
          "t_perf": 1001.0}])
    exc = refused(M.bind, wpath, missing)
    CHECK(isinstance(exc, M.BindError),
          "REFUSED: a mark carrying only ONE of the two clocks",
          f"{exc} -- the second stamp is the witness. A mark with no witness cannot be "
          f"checked, and binding it anyway would put an unchecked row in a list whose "
          f"whole claim is that every row was checked")


def section_early(M, tmp, wpath):
    """8. §8.9 control 4: a mark before t0, named as the capture-started-late defect."""
    print("\n8. a mark before the capture's epoch, and the two refusals beside it")
    early = write_marks_file(
        os.path.join(tmp, "early.jsonl"),
        [mark_rec(1, "advance", 0, "a", -0.5, -0.5),
         mark_rec(2, "advance", 1, "b", 5.0, 5.0)])
    exc = refused(M.bind, wpath, early)
    CHECK(isinstance(exc, M.BindError), "REFUSED: a mark stamped before t0_perf",
          f"{str(exc)[:120]}")
    CHECK("20260807T124912" in str(exc),
          "and it is named as the capture-started-late defect, from the marks side",
          f"{str(exc)[:260]} -- the sniff opened after the thing it was meant to "
          f"record, so the artifact looks complete and is missing its beginning. A "
          f"mark before t0 is that same failure seen from the other end: the operator "
          f"was already marking while the capture had not begun")
    CHECK("clamped" in str(exc) or "refused rather than" in str(exc),
          "and it refuses rather than clamping the mark to t=0",
          "a clamped mark is a label on traffic that was never recorded, sitting in a "
          "list of labels on traffic that was")

    ok = write_marks_file(os.path.join(tmp, "notearly.jsonl"),
                          [mark_rec(1, "advance", 0, "a", 0.0, 0.0)])
    CHECK(len(M.bind(wpath, ok)) == 1,
          "POSITIVE CONTROL: a mark stamped exactly AT t0 is fine",
          "t == t0 is the first instant of the capture, not before it -- an off-by-one "
          "here would refuse the mark that says 'the sniff is up, begin'")

    nometa = write_wire(os.path.join(tmp, "nometa.jsonl"), meta=False)
    exc = refused(M.wire_epoch, nometa)
    CHECK(isinstance(exc, M.BindError) and "20260807T124912" in str(exc),
          "REFUSED: a wire.jsonl with no wire_meta -- the same defect at its limit",
          f"{str(exc)[:200]} -- open_capture writes wire_meta immediately after "
          f"WinDivertOpen succeeds, so its absence means the sniff never opened")

    noperf = write_wire(os.path.join(tmp, "noperf.jsonl"), t0_perf=None)
    exc = refused(M.wire_epoch, noperf)
    CHECK(isinstance(exc, M.BindError) and "t0_perf" in str(exc)
          and "t0_wall" in str(exc),
          "REFUSED: a capture carrying only t0_wall, and the message names WHICH it has",
          f"{str(exc)[:220]} -- refused by NAME rather than bound to a t=0 that means "
          f"nothing")

    # THE REFUSAL USED TO ASSERT A FACT THE VAULT CONTRADICTS. It read "a capture written
    # before 2026-08-13 has only t0_wall", and measured, every one of the TEN real
    # wire.jsonl under vault/captures/ and vault/captures-scrubbed/ carries NEITHER --
    # the keys are client, kind, pid, server, server_ports. `t0_wall` landed 2026-08-11
    # and the newest live capture is 2026-08-10, so the whole existing corpus is a vintage
    # older than the message claimed and this module's first real input is the NEXT live
    # run. A refusal that misdescribes the artifact sends its reader looking for a field
    # that was never there.
    noneither = write_wire(os.path.join(tmp, "noepoch.jsonl"), t0_perf=None, t0_wall=None)
    exc = refused(M.wire_epoch, noneither)
    CHECK(isinstance(exc, M.BindError) and "NEITHER epoch" in str(exc),
          "REFUSED: the shape every capture in the vault actually has -- NEITHER epoch",
          f"{str(exc)[:220]} -- the message says what it FOUND rather than naming a "
          f"vintage, because the vintage it named was wrong about all ten of them")

    exc = refused(M.wire_epoch, os.path.join(tmp, "no-such-wire.jsonl"))
    CHECK(isinstance(exc, M.BindError), "REFUSED: no wire.jsonl in the directory at all",
          f"{str(exc)[:140]}")

    exc = refused(M.read, os.path.join(tmp, "no-such-marks.jsonl"))
    CHECK(isinstance(exc, M.BindError), "REFUSED: no marks file either", f"{str(exc)[:140]}")

    nometa_marks = os.path.join(tmp, "marks_nometa.jsonl")
    with open(nometa_marks, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(mark_rec(1, "advance", 0, "a", 1.0, 1.0)) + "\n")
    exc = refused(M.read, nometa_marks)
    CHECK(isinstance(exc, M.BindError) and "marks_meta" in str(exc),
          "REFUSED: a marks file with no marks_meta line",
          f"{str(exc)[:180]} -- without it the plan cannot be identified, so the marks "
          f"are ordinals into nothing")


def section_plan_seal(M, tmp, wpath, mpath, plan_path):
    """9. §8.9 control 5: a changed plan file is refused."""
    print("\n9. the plan's seal: an edited prediction cannot be used to read the marks"
          "\n   (printed last on purpose: this section EDITS the plan file that every"
          "\n    bind fixture above was sealed against, so it has to run after them)")
    CHECK(len(M.bind(wpath, mpath, plan=plan_path)) == 3,
          "POSITIVE CONTROL: the UNEDITED plan binds",
          "a seal that refuses every plan would make --plan unusable and get dropped")

    with open(plan_path, "a", encoding="utf-8") as fh:
        fh.write("# what actually happened, written afterwards\n")
    exc = refused(M.bind, wpath, mpath, plan=plan_path)
    CHECK(isinstance(exc, M.PlanError),
          "REFUSED: the plan file changed after the run",
          f"{str(exc)[:200]}")
    CHECK("PRE-REGISTERED" in str(exc) or "pre-registered" in str(exc).lower(),
          "and the refusal says what a seal is FOR",
          "a probe states its prediction first; a plan edited after the fact is a "
          "prediction rewritten to agree with its result, which is the one thing the "
          "hash exists to make impossible")
    CHECK(len(M.bind(wpath, mpath)) == 3,
          "and binding WITHOUT --plan still works, because the text is in the records",
          "the seal is a check on the plan, not a dependency of the binding -- so an "
          "operator who lost the plan file still gets their marks, and knows they are "
          "unverified")

    shorter = write_plan(os.path.join(tmp, "shorter.tsv"), PLAN_ROWS[:2])
    exc = refused(M.bind, wpath, mpath, plan=shorter)
    CHECK(isinstance(exc, M.PlanError), "REFUSED: a DIFFERENT plan, of a different length",
          f"{str(exc)[:140]}")

    steps = M.load_plan(os.path.join(tmp, "shorter.tsv"))
    exc = refused(M.bind, wpath, mpath, plan=steps)
    CHECK(isinstance(exc, M.PlanError) and "3 steps" not in str(exc)[:40],
          "and an already-loaded [Step] list is checked on its COUNT",
          f"{str(exc)[:160]} -- a list has no bytes to hash, so the seal cannot apply; "
          f"the count is what remains and the refusal says so rather than passing a "
          f"plan nothing checked")


def section_wire_witness(M, tmp):
    """16. The THIRD channel, and the two failures only it can see."""
    print("\n16. wire_t: the one witness that is on the SEGMENTS' own axis")
    wc, _how = import_wirecapture()

    # ---- A CAPTURE WHOSE PUBLISHED EPOCH IS NOT THE ONE ITS SEGMENTS WERE STAMPED FROM.
    # Both clock channels are PERFECT here -- t_perf and t_wall are sampled adjacently in
    # one process, so their difference only ever measures the OS-wide (QPC - system time)
    # offset against itself and can say nothing about the segment axis. A skeptic built
    # this 0.9 s apart and bind() BOUND it, reporting worst |dperf - dwall| = 0.0001 ms
    # while every mark was 0.9 s off its own segment. That is the capture-started-late
    # family from the PRODUCER's side and it is what the third channel is for.
    shifted = os.path.join(tmp, "shifted_wire.jsonl")
    with open(shifted, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(origin.record("wirecapture.py", "live")) + "\n")
        fh.write(json.dumps({"kind": "wire_meta", "pid": 1, "server_ports": [80],
                             "t0_perf": 1000.9, "t0_wall": 1_700_000_000.9}) + "\n")
        for t in (1.0, 4.0):
            fh.write(json.dumps({"kind": "wire", "dir": "s2c", "seq": 1, "t": t,
                                 "payload": "01"}) + "\n")
    ahead = write_marks_file(
        os.path.join(tmp, "ahead.jsonl"),
        [dict(mark_rec(1, "advance", 0, "a", 1.0, 1.0), wire_t=1.0),
         dict(mark_rec(2, "advance", 1, "b", 4.0, 4.0), wire_t=4.0)],
        t0_perf=1000.9, t0_wall=1_700_000_000.9)
    exc = refused(M.bind, shifted, ahead)
    CHECK(isinstance(exc, M.BindError) and "cannot see the future" in str(exc),
          "REFUSED: a mark that reports having SEEN a segment stamped after itself",
          f"{str(exc)[:230]} -- the marks bind to t=0.1 and t=3.1 and their wire_t is "
          f"1.0 and 4.0, so the published epoch is 0.9 s late. Both clock channels agree "
          f"perfectly, because both clocks ARE perfect; only the channel taken off the "
          f"capture's own file can tell")
    d = M.drift(shifted, ahead)
    CHECK(M.worst_skew(d) is not None and M.worst_skew(d) < 1e-6,
          "CONTROL: and the two-clock witness reports NO skew at all on that file",
          f"worst |dperf - dwall| = {M.worst_skew(d) * 1000:.4f} ms -- which is the "
          f"whole argument for a third channel. Two witnesses sampled a microsecond "
          f"apart in one process can only ever restate each other")

    backwards = write_marks_file(
        os.path.join(tmp, "backwards.jsonl"),
        [dict(mark_rec(1, "advance", 0, "a", 1.0, 1.0), wire_t=1.0),
         dict(mark_rec(2, "advance", 1, "b", 4.0, 4.0), wire_t=0.5)])
    exc = refused(M.bind, wpath_of(tmp), backwards)
    CHECK(isinstance(exc, M.BindError) and "BACKWARDS" in str(exc),
          "REFUSED: a wire_t that goes BACKWARDS between two marks",
          f"{str(exc)[:180]} -- the capture's last recorded t cannot decrease while a "
          f"session runs, so the file was replaced or truncated under the marker and "
          f"these marks are not all describing the same recording")

    # ---- THE CAPTURE-STARTED-LATE DEFECT FROM THE END, which had no refusal at all.
    # A skeptic bound a mark at t0 + 3600 s against a capture whose last segment is at
    # t=12.0: BOUND, no complaint, an hour of wire time that does not exist. It is
    # reachable -- the sniffer is spawned with a hard `--seconds` ceiling, livesession
    # prints "THE OFF-WIRE CAPTURE DIED" and deliberately keeps the session going, and
    # marks.py watches the CLIENT and knows nothing about the sniffer.
    short = write_wire(os.path.join(tmp, "short_wire.jsonl"),
                       segments=((1.0, "01"), (12.0, "02")))
    after = write_marks_file(os.path.join(tmp, "after.jsonl"),
                             [mark_rec(1, "advance", 0, "a", 3600.0, 3600.0)])
    exc = refused(M.bind, short, after)
    CHECK(isinstance(exc, M.BindError) and "do not overlap" in str(exc),
          "REFUSED: marks and capture that do not overlap AT ALL",
          f"{str(exc)[:220]} -- disjointness is the one case the artifact can PROVE, "
          f"and it needs no threshold: every label is on traffic that was never recorded")

    partial = write_marks_file(
        os.path.join(tmp, "partial.jsonl"),
        [mark_rec(1, "advance", 0, "a", 2.0, 2.0),
         mark_rec(2, "advance", 1, "b", 60.0, 60.0),
         mark_rec(3, "note", 1, "", 90.0, 90.0)])
    prows = M.bind(short, partial)
    late, t_last = M.unbacked(short, prows)
    CHECK(len(prows) == 3 and [r.t for r in late] == [60.0, 90.0] and t_last == 12.0,
          "but a PARTIAL overlap is REPORTED and not refused -- 2 of 3, past t=12.0",
          f"unbacked {[r.t for r in late]} against t_last={t_last} -- refusing here "
          f"would need a threshold nobody has measured: a mark seconds after the last "
          f"packet is ordinary (the client closed, the network went quiet) and a mark "
          f"eight minutes after it means the sniffer died. Those are not separable from "
          f"the artifact, so this names the fact and refuses to guess between them")
    CHECK(not M.unbacked(short, [prows[0]])[0],
          "CONTROL: and a mark INSIDE the capture is not reported",
          f"a report that fires on every mark is noise, and would make the warning "
          f"above unreadable in the run it matters for")

    # ---- A RUN THAT MEASURED NOTHING FAILED, in the operator's only readout.
    empty = write_marks_file(os.path.join(tmp, "empty.jsonl"), [])
    CHECK(M.bind(short, empty) == [] and M.worst_skew(M.drift(short, empty)) is None,
          "a marks file with zero marks binds to [] and its worst skew is None",
          "None rather than 0.0, and that one word is the whole point: the CLI printed "
          "'worst |dperf - dwall| = 0.0 ms against a 250 ms tolerance' for a session in "
          "which the operator never pressed a key -- a run that measured NOTHING "
          "reporting the best possible measurement, which is the failure toolkit/"
          "checks.py exists to prevent, reproduced inside a tool")
    err = io.StringIO()
    real_err = sys.stderr
    try:
        sys.stderr = err
        rc = M.main(["--bind", "--wire", short, "--out", empty])
    finally:
        sys.stderr = real_err
    CHECK(rc == 2 and "UNMEASURED" in err.getvalue(),
          "and the CLI REFUSES it rather than printing a perfect score",
          f"rc={rc}: {err.getvalue().strip()[:160]}")


def wpath_of(tmp):
    """Section 6's capture, by path. The bind fixtures all aim at its real epoch."""
    return os.path.join(tmp, "wire.jsonl")


def section_where(M, tmp):
    """17. Where a marks file may be written -- the guard this module shipped without."""
    print("\n17. resolve_out: this is a WRITER, and it had no destination guard at all")
    # THE ONLY CONDITIONAL ON THE DESTINATION WAS THE DRIVER-FILENAME BASENAME COMPARE.
    # A skeptic read the tree: one write-mode `open(self.path, "w")` straight off argv,
    # ZERO calls to resolve_out / working_tree_roots / require_dir, and then ran it --
    # `--out` aimed at a pre-existing 4,096-byte file named Gw.dat in scratch replaced it
    # with 533 bytes of JSON, because "w" truncates ON OPEN, before the first mark. That
    # is `atex.py --make C:\gw\Gw.dat` in a new module, the defect test_atex.py section 3
    # was built for, and a git checkout was written into without complaint besides.
    def opens(path):
        return refused(M.Marker(path, [], "x").open)

    ok = opens(os.path.join(tmp, "allowed.jsonl"))
    CHECK(ok is None and os.path.isfile(os.path.join(tmp, "allowed.jsonl")),
          "POSITIVE CONTROL: an ordinary scratch path is still allowed",
          f"{ok} -- a guard that refuses everything protects nothing, because the tool "
          f"then never runs and gets deleted. Every refusal below is paired with this")

    exc = opens(os.path.join(M.LIVE_INSTALL, "plan_marks.jsonl"))
    CHECK(isinstance(exc, M.MarksError) and "read-only" in str(exc),
          f"REFUSED: {M.LIVE_INSTALL} -- the owner's own install",
          f"{str(exc)[:180]} -- and the file is opened 'w', so naming an existing file "
          f"there TRUNCATES it. Nothing was written to reach this: the tree shows no "
          f"path-dependent branch beyond the basename compare, so a refusal measured on "
          f"a stand-in is a refusal")

    exc = opens(os.path.join(tmp, "vault", "dat_study", "plan_marks.jsonl"))
    CHECK(isinstance(exc, M.MarksError) and "dat_study" in str(exc),
          "REFUSED: vault/dat_study, the SOURCE snapshot studies/ was measured against",
          f"{str(exc)[:170]} -- it is INSIDE the vault and the vault is an allowed "
          f"destination, so it has to be refused BEFORE the allow or the allow swallows "
          f"it. atex.resolve_out calls that ordering load-bearing for the same reason")

    # THE PATH COMES FROM THE MODULE'S OWN `working_tree_roots`, NEVER FROM THIS FILE'S
    # `HERE`, AND THAT DISTINCTION COST A WRITE INTO THE REPO. The first version aimed at
    # `os.path.join(HERE, "plan_marks.jsonl")` -- the TEST's directory. Under `--module`
    # the module under test lives in a scratch tree, so ITS REPO_ROOT is the scratch tree
    # and `<repo>/toolkit/harness/` is a path it has no reason to refuse: 24 sabotage runs
    # each reddened this check for the wrong reason AND each created
    # `toolkit/harness/plan_marks.jsonl` in the working tree, which is the exact write
    # this guard exists to prevent, arriving through the check that tests it. A guard
    # check must be aimed with the guard's own idea of where it stands.
    roots = M.working_tree_roots()
    exc = opens(os.path.join(roots[0], "toolkit", "harness", "plan_marks.jsonl"))
    CHECK(isinstance(exc, M.MarksError) and "checkout of this repository" in str(exc),
          f"REFUSED: every checkout of this repo -- {len(roots)} of them",
          f"{str(exc)[:170]}\n  roots: {roots} -- a git worktree's repo root is NOT the "
          f"main checkout's, so a refusal testing only REPO_ROOT allows a write straight "
          f"into the other tree of the same repository. mapbuild.py measured that. A "
          f"capture and its marks are vault data: personal, gitignored on purpose")
    CHECK(len(roots) >= 1 and all(os.path.isabs(r) for r in roots)
          and not os.path.isfile(os.path.join(
              roots[0], "toolkit", "harness", "plan_marks.jsonl")),
          "and nothing was written there -- the refusal happened BEFORE the open()",
          f"roots {roots} -- `open(path, 'w')` truncates on open, so a guard that ran "
          f"after it would report a refusal on a file it had already destroyed. This is "
          f"the same claim as the 4,096-byte control below, at the destination that "
          f"matters most")

    taken = os.path.join(tmp, "taken.jsonl")
    with open(taken, "wb") as fh:
        fh.write(b"x" * 4096)
    exc = opens(taken)
    CHECK(isinstance(exc, M.MarksError) and os.path.getsize(taken) == 4096,
          "REFUSED: a path that already exists, WITHOUT truncating it",
          f"{str(exc)[:150]} -- still {os.path.getsize(taken)} bytes. This is the exact "
          f"shape the skeptic ran: 4096 -> 533 and the original gone before a single "
          f"mark. A marks file already in a capture directory is a previous run's "
          f"artifact in the one place a live session cannot be reproduced")

    # ---- and the guard is CALLED, not merely present. A guard that exists, is
    # documented and is greppable while never being reached is test_atex.py section 3's
    # whole subject: the refusals above would all pass against a module that defined
    # resolve_out and opened the file anyway, if the refusals were reached some other way.
    tree = ast.parse(open(M.__file__, encoding="utf-8").read())
    writes, guarded_writes = 0, 0
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "open" and len(node.args) >= 2):
            continue
        mode = node.args[1]
        if not (isinstance(mode, ast.Constant) and isinstance(mode.value, str)
                and ("w" in mode.value or "a" in mode.value or "+" in mode.value)):
            continue
        writes += 1
    fn = next((n for n in ast.walk(tree)
               if isinstance(n, ast.FunctionDef) and n.name == "open"), None)
    call = _first_stmt(fn, lambda n: (isinstance(n, ast.Call)
                                      and isinstance(n.func, ast.Name)
                                      and n.func.id == "resolve_out"))
    wopen = _first_stmt(fn, lambda n: (isinstance(n, ast.Call)
                                       and isinstance(n.func, ast.Name)
                                       and n.func.id == "open"))
    guarded_writes = 1 if (call is not None and wopen is not None
                           and call < wopen) else 0
    CHECK(writes == 1 and guarded_writes == 1,
          "and Marker.open RESOLVES the path before it opens it, on the syntax tree",
          f"{writes} write-mode open() in the module; resolve_out at body statement "
          f"{call}, open() at {wopen} -- asked of the tree because 'the guard is called "
          f"first' is invisible to a grep, which sees both names and cannot order them. "
          f"A second write-mode open() appearing anywhere reddens this too")


def section_origin(M, tmp):
    """10. The compatibility paragraph, and which half of it is a measurement."""
    print("\n10. a mark carries no origin field, and no peer field either")
    p = write_plan(os.path.join(tmp, "o_plan.tsv"), PLAN_ROWS)
    clk = Clock()
    m = M.open_marks(tmp, p, out=os.path.join(tmp, "o_marks.jsonl"),
                     clock=clk.perf_counter, wall=clk.time)
    clk.tick(); m.advance()
    clk.tick(); m.note()
    clk.tick(); m.close()
    records = [json.loads(l) for l in open(m.path, encoding="utf-8") if l.strip()]

    CHECK(len(records) == 4 and not any("origin" in r for r in records),
          "no record this module writes carries an 'origin' field",
          f"{len(records)} records, fields {sorted({k for r in records for k in r})} "
          f"-- §10.5.1 names this rule. MEASURED here: it is INSURANCE today, not a "
          f"live hazard, because origin.origin_of reads 'origin' only off a record "
          f"whose kind is 'origin'. It becomes load-bearing the moment marks are "
          f"inlined into wire.jsonl or that gate is relaxed")
    peers = {f for r in records for f in origin.PEER_FIELDS if f in r}
    CHECK(not peers,
          "and none carries any of origin.PEER_FIELDS either -- THIS is the live one",
          f"found {sorted(peers)} against {list(origin.PEER_FIELDS)}. peers_in() reads "
          f"these off EVERY record regardless of kind, so one of them on a mark votes "
          f"in the capture's own provenance verdict")

    # ---- the consequence, measured in both directions
    base = [{"kind": "origin", "origin": origin.LIVE, "produced_by": "wirecapture.py"},
            {"kind": "wire_meta", "pid": 1, "server_ports": [80],
             "t0_perf": 1000.0, "t0_wall": 1_700_000_000.0}]

    def verdict(extra):
        path = os.path.join(tmp, "o_probe.jsonl")
        with open(path, "w", encoding="utf-8") as fh:
            for rec in base + extra:
                fh.write(json.dumps(rec) + "\n")
        return origin.origin_of(path)

    clean = verdict([])
    CHECK(clean[0] == origin.LIVE,
          "CONTROL: the capture alone reads LIVE", f"{clean}")
    poisoned = verdict([{"kind": "mark", "seq": 1, "mark": "advance", "step": 0,
                         "text": "x", "t_perf": 1001.0, "t_wall": 1_700_000_001.0,
                         "server": "127.0.0.1:6112"}])
    CHECK(poisoned[0] == origin.UNKNOWN and "CONTRADICTED" in poisoned[1],
          "and ONE inlined mark carrying 'server' flips it to UNKNOWN",
          f"{poisoned} -- this is what would break. origin.require_single then refuses "
          f"to pool an unknown with the live corpus, so the one artifact this project "
          f"cannot reproduce drops out of its own dataset over a field NAME. The mark "
          f"would be right about the marks process and wrong about the capture")
    inert = verdict([{"kind": "mark", "seq": 1, "mark": "advance", "step": 0,
                      "text": "x", "t_perf": 1001.0, "t_wall": 1_700_000_001.0,
                      "origin": origin.OURS}])
    CHECK(inert[0] == origin.LIVE,
          "CONTROL: an inlined mark carrying 'origin' does NOT flip it today",
          f"{inert} -- which is why the first check above is stated as insurance. "
          f"Reporting it as a measured hazard would be claiming a consequence that "
          f"does not exist, and the next reader would trust the wrong one of the two")

    tree = ast.parse(open(TAPE_PY, encoding="utf-8").read())
    CHECK(dict_has_key(tree, "load_tape", "t0"),
          "and tape.load_tape now RETURNS its t0, which §10.5.1 asks to land together",
          "a tape event's time is relative to that connection's first s2c segment, so "
          "a mark in wire time and an event in tape time are two numbers that look "
          "comparable and are not. It was computed and discarded")


def section_on_tape(M, tmp, wpath, mpath):
    """11. on_tape: the second rebasing, and the negative it must NOT refuse."""
    print("\n11. on_tape(): a mark rebased onto one connection's own clock")
    rows = M.bind(wpath, mpath)
    # 33.0 SITS BETWEEN THE FIRST AND SECOND MARK ON PURPOSE: the third check below needs
    # a NEGATIVE result to exist, which means the tape's first s2c segment must land
    # after some mark. A t0 below every mark would make it vacuous.
    tape_t0 = 33.0
    shifted = M.on_tape({"t0": tape_t0, "connection": "10.0.0.2:1->54.1.1.1:80"}, rows)
    CHECK([round(r.t, 6) for r in shifted] == [round(r.t - tape_t0, 6) for r in rows],
          "every mark moves by exactly the tape's t0",
          f"{[r.t for r in rows]} -> {[r.t for r in shifted]}")
    CHECK([r.mark for r in shifted] == [r.mark for r in rows]
          and [r.text for r in shifted] == [r.text for r in rows],
          "and nothing else about a mark changes", f"{shifted}")
    CHECK(any(r.t < 0 for r in shifted),
          "a NEGATIVE result is returned, not refused",
          f"{[r.t for r in shifted]} -- a mark taken during the handshake, or on an "
          f"earlier connection, genuinely precedes this tape's first server byte. "
          f"Refusing it would throw away exactly the marks that describe the instance "
          f"load, which is the part of a session c2s cannot label at all")

    exc = refused(M.on_tape, {"connection": "c"}, rows)
    CHECK(isinstance(exc, M.BindError) and "t0" in str(exc),
          "REFUSED: a tape info with no t0 (a load_tape from before 2026-08-13)",
          f"{str(exc)[:170]}")
    exc = refused(M.on_tape, {"t0": None, "connection": "c"}, rows)
    CHECK(isinstance(exc, M.BindError),
          "REFUSED: a tape with no events, which has no first segment to measure from",
          f"{str(exc)[:150]} -- a 0.0 there would be a made-up origin that reads as a "
          f"real one")


def section_channel(M, tmp):
    """12. The driver already owns `marks.jsonl`, and two writers on one file is loss."""
    print("\n12. this module's channel is NOT livesession.py's, and says so")
    CHECK(M.PLAN_MARKS_NAME != M.DRIVER_MARKS_NAME == "marks.jsonl",
          "the output file is plan_marks.jsonl, not the spec's marks.jsonl",
          f"{M.PLAN_MARKS_NAME!r} against the driver's {M.DRIVER_MARKS_NAME!r} -- a "
          f"CORRECTION to §10.5.1, because livesession.py opens marks.jsonl in 'w' "
          f"mode and holds the handle for the whole session. Appends from a second "
          f"writer are overwritten from the driver's own stale offset: silent loss, in "
          f"the one artifact a live run cannot reproduce")
    wc, _how = import_wirecapture()
    CHECK(M.driver_marks_name() == wc.MARKS_NAME,
          "the reserved name AGREES with wirecapture.MARKS_NAME today",
          f"{M.driver_marks_name()!r} == {wc.MARKS_NAME!r} -- necessary and, on its own, "
          f"not sufficient: see the next two checks")

    # THIS CHECK CLAIMED THE NAME WAS "RESOLVED, NOT MERELY PINNED" AND COULD NOT SEE THE
    # DIFFERENCE. A skeptic made driver_marks_name() return the pinned literal
    # unconditionally -- a function that resolves nothing, which is the whole of what the
    # claim denies -- and this file went ALL CHECKS PASSED, 139, exit 0. It reddened only
    # once the two names had ALREADY DRIFTED, so it detected the drift and not the failure
    # to resolve. The difference is only visible against a wirecapture whose MARKS_NAME is
    # NOT the pinned literal, so one is built here: two live answers, not a comparison of
    # a constant with itself.
    real_wc = sys.modules.get("wirecapture")
    try:
        stub = types.ModuleType("wirecapture")
        stub.MARKS_NAME = "somebody_renamed_this.jsonl"
        sys.modules["wirecapture"] = stub
        resolved = M.driver_marks_name()
    finally:
        if real_wc is None:
            sys.modules.pop("wirecapture", None)
        else:
            sys.modules["wirecapture"] = real_wc
    CHECK(resolved == "somebody_renamed_this.jsonl",
          "and it is RESOLVED from wirecapture, not merely pinned -- it follows a rename",
          f"answered {resolved!r} against a wirecapture whose MARKS_NAME had been "
          f"changed, while marks.py's own literal is still "
          f"{M.DRIVER_MARKS_NAME!r}. A pinned-only implementation answers the literal "
          f"here and passed the old form of this check perfectly")

    try:
        broken = types.ModuleType("wirecapture")
        del broken.MARKS_NAME          # noqa -- there is none; force the attribute error
    except AttributeError:
        pass
    real_wc = sys.modules.get("wirecapture")
    try:
        sys.modules["wirecapture"] = broken
        fell_back = M.driver_marks_name()
    finally:
        if real_wc is None:
            sys.modules.pop("wirecapture", None)
        else:
            sys.modules["wirecapture"] = real_wc
    CHECK(fell_back == M.DRIVER_MARKS_NAME,
          "CONTROL: and when wirecapture cannot answer, it falls back to the literal",
          f"{fell_back!r} -- which is the platform case the fallback exists for: "
          f"wirecapture imports tcptable, which binds ctypes.wintypes at module scope "
          f"and is unimportable off Windows. Without this control the check above could "
          f"be satisfied by a version that resolves and then CRASHES off Windows, taking "
          f"the whole module with it")

    exc = refused(M.Marker(os.path.join(tmp, "marks.jsonl"), [], "x").open)
    CHECK(isinstance(exc, M.MarksError) and "marks.jsonl" in str(exc),
          "REFUSED: writing to the driver's own filename",
          f"{str(exc)[:180]}")
    exc = refused(M.Marker(os.path.join(tmp, "MARKS.JSONL"), [], "x").open)
    CHECK(isinstance(exc, M.MarksError),
          "and the refusal is case-insensitive, because the filesystem is",
          f"{str(exc)[:100]} -- NTFS would happily let 'MARKS.JSONL' and 'marks.jsonl' "
          f"be the same file while a case-sensitive check said they were not")

    merged = os.path.join(tmp, "merged.jsonl")
    with open(merged, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"kind": "marks_meta", "plan_sha256": "x", "steps": 1,
                             "t0_perf": 1000.0, "t0_wall": 1.0, "pid": 1}) + "\n")
        fh.write(json.dumps(mark_rec(1, "advance", 0, "a", 1.0, 1.0)) + "\n")
        fh.write(json.dumps({"kind": "mark", "n": 1, "label": "step 1", "wall": 1.0,
                             "perf": 2.0, "wire_t": 3.0}) + "\n")
    exc = refused(M.read, merged)
    CHECK(isinstance(exc, M.BindError) and "livesession" in str(exc),
          "REFUSED: a file holding BOTH mark shapes, named as the collision it is",
          f"{str(exc)[:200]} -- both channels use kind=='mark' and their fields do not "
          f"overlap, so a merged file reads as a run with holes in it rather than as "
          f"an error. Naming it is the only way it stays visible")


def section_run(M, tmp):
    """13. The run loop: four endings, and a finger-slip that does not end the session."""
    print("\n13. run(): every ending releases the keys and closes the file")
    p = write_plan(os.path.join(tmp, "r_plan.tsv"), PLAN_ROWS)
    clk = Clock()
    fake = FakeUser32(mod_norepeat=M.MOD_NOREPEAT, wm_hotkey=M.WM_HOTKEY)
    hk = M.Hotkeys(user32=fake, last_error=lambda: 0).register()
    m = M.open_marks(tmp, p, out=os.path.join(tmp, "r_marks.jsonl"),
                     clock=clk.perf_counter, wall=clk.time)

    stop = os.path.join(tmp, "STOP")
    passes = {"n": 0}

    def alive():
        passes["n"] += 1
        clk.tick(0.2)
        if passes["n"] == 1:
            fake.press(M.VK_F9)
        elif passes["n"] == 2:
            fake.press(M.VK_F9)
        elif passes["n"] == 3:
            for _ in range(4):                    # three too many: a finger slip
                fake.press(M.VK_F9)
        elif passes["n"] == 4:
            fake.press(M.VK_F11)                  # AFTER the slip: a note is always legal
        elif passes["n"] == 5:
            open(stop, "w").close()
        return True

    said = []
    why, dog, polls = run_bounded(M, m, hk, alive=alive, stop_file=stop, timeout_ms=0,
                                  say=said.append)
    CHECK(why == "STOP file" and dog is None,
          "a STOP file ends the run, with no console focus needed",
          f"ended: {why!r} after {polls} passes (watchdog: {dog}) -- the operator ends "
          f"a session by closing the CLIENT, not by alt-tabbing to this terminal, which "
          f"is the same reason livesession._hold grew one")
    CHECK(not fake.registered and fake.unregistered,
          "and the finally released every hotkey", f"released {fake.unregistered}")

    _meta, marks = M.read(m.path)
    CHECK([(r["mark"], r["step"]) for r in marks]
          == [("advance", 0), ("advance", 1), ("advance", 2), ("note", 2)],
          "three advances and then a note were recorded, in order",
          f"{[(r['mark'], r['step']) for r in marks]} -- the FIRST press of pass 3 "
          f"opened step 2, and the three after it had nowhere to go")
    CHECK(len(marks) == 4 and marks[2]["step"] == 2,
          "and the plan is exhausted at step 2, not wrapped", f"{marks[2]}")
    CHECK(sum("refused" in s for s in said) == 3,
          "the three presses past the end were ANNOUNCED",
          f"{[s for s in said if 'refused' in s][:1]}")
    CHECK(marks[-1]["mark"] == "note" and passes["n"] >= 5,
          "and the session KEPT MARKING afterwards -- the note on pass 4 is recorded",
          f"last mark {marks[-1]['mark']!r} after {passes['n']} passes. This is the "
          f"independent form of 'the refusal did not end the run': asserting the "
          f"ending was still the STOP file would be re-checking the line above, which "
          f"cannot fail for this reason. An operator whose finger slips must not lose "
          f"the rest of the session's marks while they are looking at the game")
    end = [json.loads(l) for l in open(m.path, encoding="utf-8") if '"marks_end"' in l]
    CHECK(end and end[0]["why"] == "STOP file" and end[0]["refused"] == 3,
          "and marks_end carries both the ending and the refusal count",
          f"{end} -- visible in the ARTIFACT, not only on a console nobody was reading")

    # ---- the other endings
    for label, kwargs, want in (
            ("the subject process exits", {"alive": lambda: False}, "subject exited"),
            ("the seconds ceiling", {"seconds": 1}, "ceiling"),
    ):
        f2 = FakeUser32(mod_norepeat=M.MOD_NOREPEAT, wm_hotkey=M.WM_HOTKEY)
        h2 = M.Hotkeys(user32=f2, last_error=lambda: 0).register()
        m2 = M.open_marks(tmp, p, out=os.path.join(tmp, f"r_{want[:4]}.jsonl"),
                          clock=clk.perf_counter, wall=clk.time)
        c2 = Clock(perf0=0.0)
        got, dog, polls = run_bounded(M, m2, h2, timeout_ms=0, say=lambda _s: None,
                                      clock=lambda: c2.tick(2.0), **kwargs)
        CHECK(got == want and dog is None, f"{label} ends the run",
              f"{got!r} after {polls} passes -- and the watchdog did not fire "
              f"({dog}), which is the half that used to be a HANG: with this ending "
              f"removed the loop has no other, and the run wedged past 120 s with no "
              f"exit code and no ledger instead of reddening here")
        CHECK(not f2.registered and m2.fh is None,
              f"and {label} still releases the keys and closes the file",
              f"registered={f2.registered} fh={m2.fh}")

    f3 = FakeUser32(mod_norepeat=M.MOD_NOREPEAT, wm_hotkey=M.WM_HOTKEY)
    h3 = M.Hotkeys(user32=f3, last_error=lambda: 0).register()
    m3 = M.open_marks(tmp, p, out=os.path.join(tmp, "r_quit.jsonl"),
                      clock=clk.perf_counter, wall=clk.time, wire_path="")
    f3.post_raw(M.WM_QUIT)
    got, dog, _n = run_bounded(M, m3, h3, timeout_ms=0, say=lambda _s: None)
    CHECK(got == "WM_QUIT" and dog is None and not f3.registered and m3.fh is None,
          "WM_QUIT ends it too, and the finally still runs on that path",
          f"{got!r} -- it RETURNS from inside the loop, which is the shape that skips "
          f"a cleanup written after the while instead of in a finally. This sub-run is "
          f"where the narrowed-peek sabotage wedged: WM_QUIT never reaches _drain, so "
          f"there is no ending left at all")

    # ---- THE WATCHDOG ITSELF, because a bound that has never been reached is not a
    # bound and would make every `dog is None` above vacuous.
    f4 = FakeUser32(mod_norepeat=M.MOD_NOREPEAT, wm_hotkey=M.WM_HOTKEY)
    h4 = M.Hotkeys(user32=f4, last_error=lambda: 0).register()
    m4 = M.open_marks(tmp, p, out=os.path.join(tmp, "r_nofin.jsonl"),
                      clock=clk.perf_counter, wall=clk.time, wire_path="")
    got, dog, polls = run_bounded(M, m4, h4, limit=8, timeout_ms=0,
                                  say=lambda _s: None)
    CHECK(got is None and isinstance(dog, Watchdog) and polls == 9,
          "POSITIVE CONTROL: a run with NO ending at all trips the watchdog and reports",
          f"{dog} after {polls} passes -- this is what each of the four broken endings "
          f"turns into now. It is still a red check with a verdict and a ledger, which "
          f"is the entire difference from a suite that stops")
    CHECK(not f4.registered and m4.fh is None,
          "and even then the finally released the keys and closed the file",
          f"registered={f4.registered} fh={m4.fh} -- the watchdog raises through run()'s "
          f"finally, so this also says the finally is not conditional on a clean ending")


def section_platform(M, tmp):
    """14. The Windows-only paths, reached on every platform by removing windll."""
    print("\n14. the Windows-only halves refuse cleanly, and are exercised here anyway")
    real_ctypes = M.ctypes
    try:
        M.ctypes = types.SimpleNamespace()         # no `windll` attribute at all
        exc = refused(M._load_user32)
        CHECK(isinstance(exc, M.HotkeyRefused),
              "REFUSED: the hotkey loop with no windll -- a clean refusal, not a crash",
              f"{str(exc)[:160]}")
        CHECK("Windows-only" in str(exc) and "plan" in str(exc),
              "and it says which HALF of the module is Windows-only",
              "the plan, writer, reader and binder are pure and run anywhere; only the "
              "run itself needs the OS. A reader who takes 'Windows-only' to mean the "
              "file cannot be imported writes another test_keytap.py")
        CHECK(M.process_alive(1234) is None,
              "and process_alive answers None rather than pretending",
              "run() then never asks about liveness, and the STOP file and the ceiling "
              "are still two working endings")
    finally:
        M.ctypes = real_ctypes

    CHECK(M.process_alive(0) is None and M.process_alive(None) is None,
          "process_alive(0) and (None) are None on every platform",
          "--pid is optional; 0 means 'no subject', and a liveness probe on pid 0 "
          "would answer about the system idle process")
    if sys.platform == "win32":
        probe = M.process_alive(os.getpid())
        CHECK(callable(probe) and probe() is True,
              "and on Windows it answers True for a process that is running",
              f"pid {os.getpid()} -- via OpenProcess/WaitForSingleObject, never "
              f"os.kill, which on Windows is TerminateProcess")
    else:                                          # pragma: no cover
        CHECK(M.process_alive(os.getpid()) is None,
              "and off Windows it declines rather than guessing",
              f"platform {sys.platform}")

    names = identifiers(ast.parse(open(M.__file__, encoding="utf-8").read()))
    CHECK("wintypes" not in names,
          "and no `wintypes` name appears anywhere in the module's CODE",
          f"asked the syntax tree, not the text -- the header discusses `wintypes` at "
          f"length and a grep would redden on that. keytap.py and tcptable.py both bind "
          f"`ctypes.wintypes` at import and are therefore unimportable off Windows, "
          f"which is why test_keytap.py has to skip whole. MSG is spelled in "
          f"platform-neutral ctypes types instead, and that one decision is what lets "
          f"every check in this file run anywhere")
    CHECK("wintypes" in identifiers(ast.parse(
        open(os.path.join(HERE, "tcptable.py"), encoding="utf-8").read())),
        "POSITIVE CONTROL: tcptable.py IS flagged by the same reader",
        "the module whose module-scope `from ctypes import wintypes` is the reason "
        "wirecapture cannot be imported off Windows. A detector that has never fired "
        "is not a detector")
    # AND THE OTHER DIRECTION, ON SOURCE BUILT HERE. A skeptic tried to demonstrate the
    # control above by removing the import from a scratch tcptable and could not: the
    # copy then died at IMPORT with a NameError before section 14 was ever reached, and
    # making it genuinely wintypes-free is a rewrite rather than a one-line sabotage. So
    # the pair is stated on two strings instead, where both directions are reachable: a
    # positive control whose subject cannot be moved has only ever been seen to fire, and
    # a reader that flags EVERYTHING would pass it just as well.
    flags_it = identifiers(ast.parse(
        "from ctypes import wintypes\nx = wintypes.DWORD\n"))
    misses_it = identifiers(ast.parse(
        "import ctypes\n# wintypes is discussed at length in this comment\n"
        "x = ctypes.c_ulong\ns = 'wintypes'\n"))
    CHECK("wintypes" in flags_it and "wintypes" not in misses_it,
          "and the same reader does NOT flag a module that only MENTIONS wintypes",
          f"flagged {sorted(flags_it)} / clean {sorted(misses_it)} -- the second string "
          f"names wintypes in a comment and in a string constant, which is exactly what "
          f"marks.py's header does at length and what a grep would redden on. Both "
          f"directions on live source, so the control cannot be passing because the "
          f"reader says yes to everything")


def section_cli(M, tmp):
    """15. The CLI: a refusal is an exit code, never a traceback."""
    print("\n15. main(): --check-plan is the pre-flight, and refusals exit 2")
    p = write_plan(os.path.join(tmp, "cli_plan.tsv"), PLAN_ROWS)
    buf = io.StringIO()
    real = sys.stdout
    try:
        sys.stdout = buf
        rc = M.main(["--check-plan", p])
    finally:
        sys.stdout = real
    out = buf.getvalue()
    CHECK(rc == 0 and M.plan_sha256(p) in out and "3 steps" in out,
          "--check-plan prints the seal and the steps, and exits 0",
          f"rc={rc}, printed the sha and {out.count(chr(10))} lines -- this is the "
          f"pre-flight: run it BEFORE the client launches and record the hash, which "
          f"is what makes the plan a pre-registration rather than a file")

    err = io.StringIO()
    real_err = sys.stderr
    try:
        sys.stderr = err
        rc = M.main(["--capture", tmp])            # no --plan
    finally:
        sys.stderr = real_err
    CHECK(rc == 2 and "REFUSED" in err.getvalue(),
          "a run with no plan exits 2 and says REFUSED on stderr",
          f"rc={rc}: {err.getvalue().strip()[:140]} -- an exit code, not a traceback, "
          f"because the operator is about to launch a client and needs to know this "
          f"failed rather than to read a stack")

    tree = ast.parse(open(M.__file__, encoding="utf-8").read())
    fn = next((n for n in ast.walk(tree)
               if isinstance(n, ast.FunctionDef) and n.name == "main"), None)
    handlers = [h for n in ast.walk(fn or ast.Module(body=[], type_ignores=[]))
                if isinstance(n, ast.Try) for h in n.handlers]
    caught = {ast.unparse(h.type) for h in handlers if h.type is not None}
    CHECK("MarksError" in caught,
          "and main() is the ONLY thing that turns a refusal into an exit code",
          f"main catches {sorted(caught)} -- every refusal in the module is a "
          f"MarksError, an Exception and never a SystemExit, because a SystemExit is a "
          f"BaseException: a control written `except Exception` does not catch it, the "
          f"run dies with no verdict banner and no ledger, and a caught defect reads "
          f"as a crash. test_atex.py and test_stripbuild.py both paid for that")


def guarded(fn, *a, **kw):
    """Run a section; a crash becomes a NAMED FAILING CHECK, never a bare traceback.

    THE FLOOR WAS UNREACHABLE AS A GUARD UNTIL THIS EXISTED, and a skeptic pass measured
    it exactly: of 109 sabotages run against this file, TWELVE died with a traceback
    between check 17 and check 126 -- no verdict banner, no ledger, no floor line. Several
    sections call refusing functions bare (section 7's positive control `M.bind(wpath,
    ok)`, section 2's `meta["plan_sha256"]`), so a sabotage that makes a good fixture
    refuse kills the run instead of reddening. Exit codes stayed non-zero, so nothing went
    green wrongly -- but "the run crashed" and "check 74 failed" are different facts and
    the first one names nothing. It is `test_content.py`'s documented failure: a run that
    measured nothing cannot report that it measured nothing from inside a process that
    never reaches its verdict.

    Returns the section's value, or None if it crashed.
    """
    try:
        return fn(*a, **kw)
    except Exception as exc:                       # noqa: BLE001 -- that IS the point
        where = traceback.extract_tb(sys.exc_info()[2])[-1]
        CHECK(False, f"SECTION {fn.__name__} ran to completion",
              f"it raised instead: {type(exc).__name__}: {str(exc)[:200]} "
              f"(at {os.path.basename(where.filename)}:{where.lineno}). The checks it "
              f"had not reached are missing from the ledger, so the floor shortfall "
              f"below is the real size of this failure")
        return None


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--module", default=os.path.join(HERE, "marks.py"),
                    help="path to the marks.py under test (for running a sabotage)")
    args = ap.parse_args()

    print(f"marks under test: {args.module}")
    M = load_module(args.module)

    with tempfile.TemporaryDirectory(prefix="test_marks_") as tmp:
        guarded(section_plan, M, tmp)
        guarded(section_writer, M, tmp)
        guarded(section_exhausted, M, tmp)
        guarded(section_hotkeys, M, tmp)
        guarded(section_teardown, M, tmp)
        guarded(section_no_sendinput, M, tmp, args.module)
        built = guarded(section_bind, M, tmp)
        if built is None:
            LEDGER.skip("sections 7-9, 11, 16",
                        "section 6 did not produce a capture to bind against")
            wpath = mpath = plan_path = None
        else:
            wpath, mpath, plan_path = built
            guarded(section_drift, M, tmp, wpath)
            guarded(section_early, M, tmp, wpath)
            guarded(section_on_tape, M, tmp, wpath, mpath)
            guarded(section_wire_witness, M, tmp)
        guarded(section_origin, M, tmp)
        guarded(section_channel, M, tmp)
        guarded(section_where, M, tmp)
        guarded(section_run, M, tmp)
        guarded(section_platform, M, tmp)
        guarded(section_cli, M, tmp)
        # LAST, because it EDITS the plan file the bind fixtures were sealed against.
        if built is not None:
            guarded(section_plan_seal, M, tmp, wpath, mpath, plan_path)

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
