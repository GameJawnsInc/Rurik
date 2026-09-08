"""Drive the patched Guild Wars client end to end, unattended, with the
instrumentation already running before the client starts.

The client autofills its credentials, so the whole path to standing in a map is
three Enter presses: sign in, accept the EULA, Play. That makes the run scriptable,
which matters because the manual loop -- launch, click, screenshot, report -- was
costing several minutes per hypothesis and kept producing partial evidence.

WHY INSTRUMENTATION STARTS FIRST. On 2026-08-05 three conclusions in a row were
wrong ("the client never opens a socket", "it gave up on that endpoint", "it does
not act on our handoff") and all three came from sampling AFTER the moment of
interest and reading the empty result as proof. The thing that finally worked was a
50 ms sampler running DURING the click, which caught 127.0.0.1:80 in SYN_SENT.
So: sampler first, client second, always. An instrument that was not yet running
produces absence of evidence, never evidence of absence.

SAFETY. This refuses to launch unless the target is a patched copy under vault/run
AND the command line carries `-authsrv 127.0.0.1 -portal 127.0.0.1`. That pair is
what makes reaching ArenaNet's auth service impossible. The owner's standing rule is
that a modded client must never touch ArenaNet's servers, so it is enforced here in
code rather than left to whoever types the command. C:\\gw is never a valid target.
"""

import argparse
import ctypes
import json
import os
import subprocess
import sys
import threading
import time
from ctypes import wintypes

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLKIT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, TOOLKIT)
# `cage.py` lives in clientpatch/, not here, so without this line the `import
# cage` below raises ModuleNotFoundError and THIS module -- the only one that
# launches a client -- cannot be imported at all. That is how `test_harness.py`
# sat red from 7ac7fbc, the commit that added the cage assertion, until
# 2026-08-06: the guard that makes every launch check the cage stopped the
# launcher from loading. Stated here rather than left to whoever imports us
# first; `session.py` used to work only because it imported drive_client one
# line before it imported cage, which is an ordering accident, not a path.
sys.path.insert(0, os.path.join(TOOLKIT, "clientpatch"))
# And `clientscan/` for the two modules that answer "which build is this exe" --
# `pinned` for what we are pinned TO, `buildid` for what a file actually IS.
# Both are stdlib-only, so this does not put a dependency on the launch path.
sys.path.insert(0, os.path.join(TOOLKIT, "clientscan"))
# And `mapdata/` for `datcheck`, the archive half of the launch gate. Same
# reasoning as the `clientpatch/` line above, and stdlib-only for the same
# reason: this module is the one that launches a client, so anything it imports
# has to load on a bare machine or the launcher stops loading at all.
sys.path.insert(0, os.path.join(TOOLKIT, "mapdata"))
from tcptable import connections  # noqa: E402
from vaultpath import resolve_out, vault_path  # noqa: E402
import buildid  # noqa: E402
import cage  # noqa: E402
import accounts  # noqa: E402
import pinned  # noqa: E402
import datcheck  # noqa: E402  -- toolkit/mapdata, the archive half of the gate

RUN_ROOT = os.path.normcase(vault_path("run"))
# The live-capture build is staged apart so isolate_client.ps1's bare sweep, which
# cages every Gw.exe under vault/run, cannot cage the one binary that must not be.
LIVE_ROOT = os.path.normcase(vault_path("run-live"))
# Both flags must be present and both must name a 127/8 address. Any loopback
# alias is as unreachable-from-ArenaNet as 127.0.0.1 itself, and the handoff
# probes need a second alias (127.0.0.2) precisely so the wire can show WHICH
# configured host the client dials. What stays absolute: a missing flag or a
# routable address is refused, never warned about.
REQUIRED_FLAGS = ["-authsrv", "-portal"]
# Flags `--client-arg` may NEVER add. Everything else in the client's 41-entry
# argument table is a display or audio option and is harmless here, but these
# three decide where the binary points, which is the one thing the cage exists
# to fix. A second `-authsrv` is the sharp case: `assert_safe`'s parse keeps the
# LAST value it sees while the client may act on the first, so the gate would
# clear one host and the client would dial another -- the entire launch safety
# story defeated by something that reads like a display option. `-portaldll` is
# dead code in this build (PLAN.md §1.6) and is refused anyway, because "it does
# nothing today" is a property of build 38797 rather than of the flag.
FORBIDDEN_CLIENT_ARGS = {"-authsrv", "-portal", "-portaldll"}


def is_loopback(value):
    parts = value.split(".")
    return (len(parts) == 4 and parts[0] == "127"
            and all(p.isdigit() and int(p) <= 255 for p in parts))


def select_run_exe(build=None):
    """(path, why) -- the newest vault/run/<dir>/Gw.exe THAT IS `build`.

    `why` is meant to be printed, in both outcomes. `path` is None when nothing
    qualifies, and then `why` is the whole diagnosis.

    NEWEST IS NOT A BUILD SELECTOR, and this function used to think it was: it
    globbed vault/run/*/Gw.exe and returned `max(..., key=os.path.getmtime)`.
    That is the third appearance of one defect. `sorted(exes)[-1]` picked the
    wrong client the day both DH configurations first existed (CLAUDE.md says
    so, twice, in two files), `pinned.PINNED` was `BUILDS[-1]` until 2026-08-14,
    and this line was the one nobody had converted -- so when build 38833 was
    snapshotted at 18:24 that day it became "newest" and the harness silently
    changed which client it launches.

    Silently is the operative word. It did not fail at the exe: it failed later
    and elsewhere, because the two generations' archives bind maps 146/148 to
    DIFFERENT bytes than each other and than the server's dat_study. (This
    paragraph had the two states swapped until 2026-08-16, and the inverted
    version was load-bearing prose in a function about which client launches,
    so the measured truth, from the file-id tables themselves: the 38797 run
    dirs were cut mid-replacement -- 0x1B97D present only as the bit-31 rename
    0x8001B97D -> row 7982, unresolvable to the client's exact-compare lookup
    until datwrite --relink-plain re-bound it on 2026-08-16 -- while the 38833
    dir binds 0x1B97D plainly to ArenaNet's own 38833-generation file, which
    is sha-identical to the pristine 2026-08-13 snapshot and run-live copies
    but NOT to the dat_study row the server paths against.) A newest-wins
    default turns an ArenaNet update into a wrong answer somewhere downstream
    rather than into an error here.

    SO THE BUILD IS MEASURED, never inferred from the directory name -- the same
    rule the vault's DH split lives by. `buildid.read()` reads the client's own
    `mov eax, <build>; ret` getter out of the image in ~0.07 s, which is cheap
    enough to do on every launch, and it works on copies whose hash we never
    recorded: `identify()` calls vault/run/reskin-roster "unknown", and its
    exe says 38797 quite clearly.

    Defaults to `pinned.BUILD` -- 38797 -- because that is what every address in
    `studies/` was measured against and the generation whose map bytes dat_study
    serves. Moving the harness to a new build is a re-measurement arc, not a
    side effect of snapshotting one.

    NEVER RAISES. `--exe`'s argparse default used to call this eagerly, so a
    refusal here would take `--help` and even an explicit `--exe` down with it.
    Callers decide what a None means; both of ours print `why` and stop.
    """
    import glob
    want = pinned.BUILD if build is None else build
    cands = glob.glob(os.path.join(vault_path("run"), "*", "Gw.exe"))
    if not cands:
        return None, (f"No Gw.exe under {vault_path('run')} — run "
                      f"make_run_dir.py first (RUNBOOK.md, one-time setup).")

    matched, others = [], []
    for c in cands:
        try:
            number = buildid.read(c)[0]
        except BaseException as exc:                          # noqa: BLE001
            # An unreadable candidate is skipped and REPORTED, never silently
            # dropped: "we could not look" and "we looked and it was the wrong
            # build" are different answers and the second is the only one that
            # should ever narrow the field.
            others.append((c, f"unreadable: {type(exc).__name__}"))
            continue
        (matched if number == want else others).append(
            (c, f"build {number}"))

    if not matched:
        lines = [f"No client of build {want} under {vault_path('run')}.",
                 f"  {len(cands)} run director(ies) exist and none is it:"]
        for c, what in sorted(others):
            lines.append(f"      {os.path.basename(os.path.dirname(c))}  -- {what}")
        lines.append(f"  This tool's offsets, its captures and the maps 146/148")
        lines.append(f"  replacement are all pinned to {want}. Re-assemble that run")
        lines.append(f"  directory (RUNBOOK.md), or pass an explicit --exe if you")
        lines.append(f"  genuinely mean to drive another build.")
        return None, "\n".join(lines)

    # AND WITHIN THE BUILD, THE CANONICAL DIRECTORY -- also not by mtime.
    #
    # This was the same bug a second time and filtering by build alone did not
    # fix it: with 38833 excluded the newest 38797 copy is `reskin-roster`
    # (assembled 2026-08-14 12:29), an experiment copy, beating the real one at
    # 2026-08-10 23:54. The old `-probe` exclusion covered exactly one spelling
    # of "experiment" and there are three on disk: `-c2`, `-probe`,
    # `reskin-roster`.
    #
    # `make_run_dir.py` names the canonical directory after the build's own
    # vault STAMP (`dest = run_root/tag`, tag off `Gw.custom.<tag>.exe`);
    # everything else on disk got its name from an explicit `--dest`. So ask for
    # the stamp. That is a name with a producer and a meaning, rather than a
    # timestamp that means "whatever was touched last".
    by_dir = {os.path.basename(os.path.dirname(c)): c for c, _ in matched}
    stamp = next((b.stamp for b in pinned.BUILDS if b.number == want), None)
    if stamp and stamp in by_dir:
        return by_dir[stamp], _why(want, by_dir[stamp], others)
    # No canonical directory: fall back to a variant, but SAY the name, because
    # an experiment copy carries whatever that experiment changed -- reskinned
    # models, a repointed Gw.dat -- and a run that silently used one would be
    # measuring the experiment.
    pick = max((c for c, _ in matched), key=os.path.getmtime)
    return pick, (_why(want, pick, others) + f"; NO canonical {stamp} directory, "
                  f"this is a VARIANT copy and may carry experiment changes")


def _why(want, pick, others):
    why = f"build {want}, {os.path.basename(os.path.dirname(pick))}"
    if others:
        skipped = sorted(os.path.basename(os.path.dirname(c)) for c, _ in others)
        why += (f" (chosen by BUILD and name, never by mtime; "
                f"skipped {', '.join(skipped)})")
    return why


# `newest_run_exe()` USED TO LIVE HERE and is deliberately not kept as a
# wrapper. It no longer returns the newest anything -- selection is by build and
# by name now -- so the name would be a false statement about what the function
# does, in a module whose whole subject is which binary gets launched. That is a
# worse trap than a missing function: a caller reading `newest_run_exe()` would
# believe it. Nothing in the tree called it once both call sites moved to
# `select_run_exe`, which returns the reason as well as the path.

user32 = ctypes.WinDLL("user32", use_last_error=True)
VK_RETURN = 0x0D
KEYEVENTF_KEYUP = 0x0002
MAPVK_VK_TO_VSC = 0
WM_CLOSE = 0x0010

# Declaring argtypes is not optional here. Without them ctypes marshals a Python
# int as a 32-bit C int, which TRUNCATES a 64-bit HWND -- EnumWindows hands back a
# valid handle and every call that takes it back silently receives a corrupt one.
# The first version of this file looked like it worked (it found and named the
# window) while every SetForegroundWindow, keybd_event and GetWindowRect after it
# operated on garbage. Nothing errored; the screenshots were simply empty and the
# keystrokes went nowhere.
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetWindowRect.restype = wintypes.BOOL
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.PostMessageW.argtypes = [wintypes.HWND, ctypes.c_uint, wintypes.WPARAM, wintypes.LPARAM]
user32.keybd_event.argtypes = [ctypes.c_ubyte, ctypes.c_ubyte,
                               wintypes.DWORD, ctypes.c_void_p]
user32.GetForegroundWindow.restype = wintypes.HWND
user32.BringWindowToTop.argtypes = [wintypes.HWND]
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
user32.AttachThreadInput.restype = wintypes.BOOL
user32.SystemParametersInfoW.argtypes = [wintypes.UINT, wintypes.UINT, ctypes.c_void_p,
                                         wintypes.UINT]
user32.SystemParametersInfoW.restype = wintypes.BOOL
user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                                ctypes.c_int, ctypes.c_int, wintypes.UINT]
user32.SetWindowPos.restype = wintypes.BOOL

SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010

# THE GEOMETRY EVERY FRACTIONAL CLICK IS CALIBRATED IN, and why this is a
# constant rather than a comment. `click()` takes fractions "so the same action
# script survives a resized window", and for anything the game draws by
# proportion that is true. **Character select is not drawn by proportion.** On
# 2026-08-18 another session left the client at 716x1040 and PLAY_FX/PLAY_FY --
# measured in a ~1926x1039 window -- landed on **Delete**, six times, opening
# the "type the name to delete Test Warrior" confirmation. Nothing was lost
# (that dialog needs the name typed and defaults to Cancel) but the harness
# reported only "clicks landed: True" and a failed map checkpoint, so a run that
# opened a DELETION dialog looked exactly like an ordinary timeout.
#
# The fix is to stop guessing where the button moved to and make the window the
# size the calibration assumes. `normalize_window` is called before the Play
# click; if it cannot get there, `_play` REFUSES to click rather than firing at
# a coordinate whose meaning is unknown -- fail closed, because the failure mode
# is destructive and silent.
CLIENT_W, CLIENT_H = 1936, 1040
# How far the aspect may drift before a fractional click is meaningless. 2% is
# well inside the 1.862-vs-0.688 disaster and well outside ordinary border jitter.
ASPECT_TOLERANCE = 0.02


def window_size(hwnd):
    """(width, height) of the window rect, or None if it cannot be read."""
    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None
    return (rect.right - rect.left, rect.bottom - rect.top)


def normalize_window(hwnd, w=CLIENT_W, h=CLIENT_H):
    """Resize the client to the geometry the click fractions were measured in.

    Returns (ok, before, after). `ok` is True when the window ends up within
    ASPECT_TOLERANCE of the target aspect -- not when SetWindowPos returns true,
    because a window can refuse to take the size it was given and the only thing
    that matters here is the size it actually IS.

    Position and z-order are left alone (SWP_NOMOVE|SWP_NOZORDER) and the window
    is not activated: this runs while the harness is already driving the client,
    and stealing activation here would fight `_force_foreground` rather than help
    it. Resizing a windowed D3D client is something the game already handles --
    the operator does it by dragging, which is how it got to 716 wide.
    """
    before = window_size(hwnd)
    if before is None:
        return False, None, None
    if before != (w, h):
        user32.SetWindowPos(hwnd, None, 0, 0, w, h,
                            SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE)
        time.sleep(0.4)          # let the client rebuild its UI at the new size
    after = window_size(hwnd)
    if not after or after[1] <= 0:
        return False, before, after
    want = w / float(h)
    got = after[0] / float(after[1])
    return abs(got - want) / want <= ASPECT_TOLERANCE, before, after
SPI_SETFOREGROUNDLOCKTIMEOUT = 0x2001
_fg_lock_cleared = False

user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.mouse_event.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
                               wintypes.DWORD, ctypes.c_void_p]

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32.GetCurrentThreadId.restype = wintypes.DWORD
SW_RESTORE = 9
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MOVE = 0x0001         # RELATIVE motion, and it generates an event
MOUSEEVENTF_WHEEL = 0x0800
WHEEL_DELTA = 120                 # one notch, as the API defines it


# ---------------------------------------------------------------- safety ----

ARENANET_DEFAULT = "<ArenaNet, the client's compiled-in default>"


def intended_target(args):
    """Where this argv actually points the client. Refuses an incoherent mix.

    ABSENCE IS NOT NEUTRAL, and that is the whole reason this is a function rather
    than a loop over REQUIRED_FLAGS. A client launched with no `-portal` does not fail
    to have a portal -- it uses the one compiled into it, which is ArenaNet's. So a
    MISSING flag names the live service just as surely as typing the hostname would,
    and PLAN.md §6.2 calls that the sharpest hazard in the whole live-capture change:
    a DH-patched client launched without `-portal` completes a REAL Stage A login with
    the autofilled credential and only then dies at Stage B. The account-visible event
    happens before the patch matters.

    The old code read a missing flag as "refuse", which was right while loopback was
    the only legal target and is not expressive enough now that there are two. Here it
    resolves to the live target and the caller's DH check decides -- so the same
    omission that used to be refused by a rule is now refused by a measurement, and a
    live-capture build may legitimately be launched with no server flags at all.
    """
    flat = [str(a).lower() for a in args]
    seen = {}
    for flag in REQUIRED_FLAGS:
        if flag not in flat:
            continue
        i = flat.index(flag)
        seen[flag] = flat[i + 1] if i + 1 < len(flat) else ""

    if not seen:
        return ARENANET_DEFAULT
    loop = {f: v for f, v in seen.items() if is_loopback(v)}
    routable = {f: v for f, v in seen.items() if not is_loopback(v)}
    if loop and routable:
        raise SystemExit(
            f"REFUSING to launch: this argv points at both sides at once.\n"
            f"  loopback: {loop}\n"
            f"  routable: {routable}\n"
            f"  A client has one identity. Half a session against our server and half\n"
            f"  against ArenaNet's is not a configuration, it is two mistakes.")
    if loop and len(seen) < len(REQUIRED_FLAGS):
        missing = [f for f in REQUIRED_FLAGS if f not in seen]
        raise SystemExit(
            f"REFUSING to launch: {', '.join(missing)} missing from a LOOPBACK argv.\n"
            f"  An absent flag is not an unset one -- the client falls back to its\n"
            f"  compiled-in ArenaNet endpoint for it, so this argv would send part of\n"
            f"  the login to the real service. Name every one of "
            f"{', '.join(REQUIRED_FLAGS)}.")
    return seen.get("-authsrv") or next(iter(seen.values()))


def assert_safe(exe, args, served_maps=None):
    """Refuse a binary we do not stage, and an argv that cannot mean one thing.

    Returns the host this argv points at, for the caller to hand to
    `cage.assert_launch_safe` -- which is what decides whether THIS binary may be
    pointed THERE. The split is deliberate: this function is about the argv, that one
    is about the bytes, and neither can answer the other's question.

    `served_maps` is passed straight to `contentids.preflight`, which treats
    None -- the default -- as "check every content row". A caller that knows
    which map its run pins (the gamesrv's `--map`) narrows the content-id
    pre-flight to it; a caller that says nothing keeps the historical, wider
    refusal. See `session.served_maps` for when narrowing is legitimate and
    `contentids.preflight` for why an empty set is not.
    """
    real = os.path.normcase(os.path.abspath(exe))
    if not any(real.startswith(root + os.sep) for root in (RUN_ROOT, LIVE_ROOT)):
        raise SystemExit(
            f"REFUSING to launch {exe}\n"
            f"  Only staged copies under {RUN_ROOT} or {LIVE_ROOT} may be driven.\n"
            f"  C:\\gw is the live install and is never a valid target for automation.")

    # An incomplete run directory. make_run_dir.py copies a 4 GB Gw.dat last, and it
    # cannot copy it at all while a client holds the source open -- so a half-staged
    # directory is a normal outcome of a normal interruption, not an exotic one. A
    # client launched without Gw.dat fails somewhere far from the cause.
    dat = os.path.join(os.path.dirname(exe), "Gw.dat")
    if os.path.isfile(exe) and not os.path.isfile(dat):
        raise SystemExit(
            f"REFUSING to launch {exe}\n"
            f"  Its run directory has no Gw.dat, so staging did not finish.\n"
            f"  Re-run: python toolkit/clientpatch/make_run_dir.py"
            f"{' --live' if real.startswith(LIVE_ROOT + os.sep) else ''}\n"
            f"  (with every Guild Wars client closed -- a running one holds the\n"
            f"  source file open exclusively).")

    # Do the two archives this run uses agree about what our content ids NAME?
    # A file id is archive STATE, not a property of the map (studies/maprows/
    # FINDINGS.md 8): the server reads its own copy for the navmesh and the
    # client opens THIS one for the geometry, and nothing checked they match.
    # They do today, and the two copies have already drifted in the very field
    # that decides it (25 bit-31 ids against 29), so it is measured rather than
    # assumed. The failure it refuses is loud on the client and silent here.
    #
    # LOOPBACK ONLY, and that gate is the point: a live run answers to
    # ArenaNet's server, which sends its own ids, so `content/maps.toml` says
    # nothing about it and refusing on our rows would be wrong.
    if real.startswith(RUN_ROOT + os.sep) and os.path.isfile(dat):
        import contentids
        contentids.preflight(dat, served=served_maps)
    return intended_target(args)


# ------------------------------------------------------------- sampling ----

class Sampler(threading.Thread):
    """Record every distinct (state, remote) the client touches, with timestamps."""

    def __init__(self, interval=0.02):
        super().__init__(daemon=True)
        self.interval = interval
        self.pid = None
        self.events = []
        self._seen = set()
        self._stop = threading.Event()
        self.t0 = time.perf_counter()

    def run(self):
        # Transition-based, not "distinct endpoints ever seen". Deduping on
        # (state, remote) forever hides the second and third dial to an address
        # already recorded -- and repeated dials to one endpoint is exactly the
        # signal we are hunting. Record what APPEARS and what DISAPPEARS instead,
        # keyed on the local port so two connections to the same server are
        # distinguishable.
        prev = {}
        while not self._stop.is_set():
            cur = {}
            if self.pid:
                for c in connections(self.pid):
                    if c["remote"] == "0.0.0.0:0":
                        continue
                    cur[(c["local"], c["remote"])] = c["state"]

            now = round(time.perf_counter() - self.t0, 3)
            for k, state in cur.items():
                if k not in prev:
                    self.events.append({"t": now, "event": "open", "state": state,
                                        "local": k[0], "remote": k[1]})
                elif prev[k] != state:
                    self.events.append({"t": now, "event": state, "state": state,
                                        "local": k[0], "remote": k[1]})
            for k in prev:
                if k not in cur:
                    self.events.append({"t": now, "event": "gone", "state": prev[k],
                                        "local": k[0], "remote": k[1]})
            prev = cur
            time.sleep(self.interval)

    def stop(self):
        self._stop.set()


# --------------------------------------------------------------- window ----

def find_window(pid):
    """Top-level visible window owned by pid, if it has one yet."""
    found = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, _):
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid and user32.IsWindowVisible(hwnd):
            n = user32.GetWindowTextLengthW(hwnd)
            if n:
                buf = ctypes.create_unicode_buffer(n + 1)
                user32.GetWindowTextW(hwnd, buf, n + 1)
                found.append((hwnd, buf.value))
        return True

    user32.EnumWindows(cb, 0)
    return found[0] if found else (None, None)


def wait_window(pid, timeout=60.0):
    """Resolve the client's CURRENT top-level window. Never cache the result.

    The client puts up a splash/patcher window, destroys it, and creates the real
    one. A handle captured at startup is invalid by the time the login screen
    exists, and every call using it then fails with ERROR_INVALID_WINDOW_HANDLE
    (1400) -- which surfaces as an empty screenshot and keystrokes that vanish,
    not as anything resembling a window problem.
    """
    end = time.time() + timeout
    while time.time() < end:
        hwnd, title = find_window(pid)
        if hwnd:
            return hwnd, title
        time.sleep(0.1)
    return None, None


def _force_foreground(hwnd):
    """Raise hwnd, working around Windows' foreground lock. Returns success."""
    if user32.GetForegroundWindow() == hwnd:
        return True
    global _fg_lock_cleared
    if not _fg_lock_cleared:
        # Windows denies a background process SetForegroundWindow for a timeout after the
        # user's last input -- the "foreground lock". The AttachThreadInput dance below
        # defeats it usually but not always, which is why an automated Play click could
        # need the operator's own mouse to land. Setting the lock timeout to 0 lifts it.
        # fWinIni=0: change the running value only, do not persist to the registry -- it
        # resets on the next reboot, and this is a driving harness, not a system tweak.
        user32.SystemParametersInfoW(SPI_SETFOREGROUNDLOCKTIMEOUT, 0, None, 0)
        _fg_lock_cleared = True
    fg = user32.GetForegroundWindow()
    cur = kernel32.GetCurrentThreadId()
    other = user32.GetWindowThreadProcessId(fg, None) if fg else 0
    attached = bool(other) and bool(user32.AttachThreadInput(cur, other, True))
    try:
        user32.ShowWindow(hwnd, SW_RESTORE)
        user32.SetForegroundWindow(hwnd)
        user32.BringWindowToTop(hwnd)
    finally:
        if attached:
            user32.AttachThreadInput(cur, other, False)
    time.sleep(0.25)
    return user32.GetForegroundWindow() == hwnd


def warn_hands_off(seconds=3.0):
    """Count down before any synthetic input, loudly enough to react to.

    This harness synthesises clicks and keypresses into the client's window. A
    human touching the mouse or keyboard while it fires competes with it, and the
    run then fails for a reason that has nothing to do with what was being
    tested -- which is worse than a plain failure, because the transcript still
    looks like evidence.

    OBSERVED 2026-08-11, during rung C2: the operator had no way to tell when
    input was about to start and no warning to react to, and said so. There is no
    cleverness available here -- the client cannot be asked to ignore real input
    while accepting ours, because ours IS real input as far as Windows is
    concerned (SendInput/PostMessage into the same queue). A countdown is the
    whole fix, and it costs `seconds` once per run against a run tens of seconds
    long.

    Pass 0 for unattended runs.
    """
    if seconds <= 0:
        return
    print()
    print("  " + "=" * 56)
    print("  ==  EXECUTING HARNESS -- HANDS OFF KEYBOARD AND MOUSE  ==")
    print("  " + "=" * 56, flush=True)
    whole = int(seconds)
    for remaining in range(whole, 0, -1):
        print(f"  ==  synthetic input begins in {remaining}...", flush=True)
        time.sleep(1.0)
    frac = seconds - whole
    if frac > 0:
        time.sleep(frac)
    print("  ==  firing now", flush=True)
    print()


def hover(hwnd, pid, fx, fy, seconds):
    """Park the cursor over a fractional window position and click NOTHING.

    Exists for tooltips: a Guild Wars HUD element under a resting cursor draws
    its tooltip, and for some state the tooltip is the ONLY readable surface
    (an effect icon's scaled numbers -- skillcast 14.4's contested field has no
    other consumer the static analysis could find). The cursor is nudged one
    pixel back and forth on a slow rhythm rather than parked dead still,
    because a tooltip needs mouse-move hit-testing and an element that APPEARS
    beneath an already-stationary cursor may never receive one.

    Same focus discipline as click(): SetCursorPos is GLOBAL, so every nudge
    re-verifies the client owns the foreground and the function returns early
    the moment it does not. No button is ever pressed. Returns True if the
    cursor was placed at least once.
    """
    end = time.time() + max(0.0, seconds)
    flip = 0
    moved = False
    while time.time() < end:
        if not _own_foreground(hwnd, pid):
            return moved
        rect = wintypes.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return moved
        x = int(rect.left + (rect.right - rect.left) * fx) + flip
        y = int(rect.top + (rect.bottom - rect.top) * fy)
        user32.SetCursorPos(x, y)
        moved = True
        flip = 1 - flip
        time.sleep(0.4)
    return moved


def click(hwnd, pid, fx, fy):
    """Click at a fractional position inside the client window.

    Fractions rather than pixels so the same action script survives a resized
    window. Focus is verified exactly as for keys -- a stray click into whatever
    the owner is doing is no better than a stray keystroke.
    """
    if not _force_foreground(hwnd):
        return False
    fg = user32.GetForegroundWindow()
    owner = wintypes.DWORD()
    user32.GetWindowThreadProcessId(fg, ctypes.byref(owner))
    if owner.value != pid:
        return False

    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return False
    x = int(rect.left + (rect.right - rect.left) * fx)
    y = int(rect.top + (rect.bottom - rect.top) * fy)
    user32.SetCursorPos(x, y)
    time.sleep(0.08)
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, None)
    time.sleep(0.06)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, None)
    return True


def _own_foreground(hwnd, pid):
    """Raise the client and confirm it really owns the foreground. Never send blind.

    Factored out of press_key/press_enter/hold_key when the camera verbs were
    added, because four copies of a safety check is four places for one of them
    to drift. The property it protects is the one press_enter's docstring is
    about: keybd_event and mouse_event are GLOBAL, and an input aimed at the
    client while something else has focus lands in whatever the owner is doing.
    """
    if not _force_foreground(hwnd):
        return False
    fg = user32.GetForegroundWindow()
    owner = wintypes.DWORD()
    user32.GetWindowThreadProcessId(fg, ctypes.byref(owner))
    return owner.value == pid


def scroll(hwnd, pid, notches):
    """Turn the mouse wheel `notches` clicks. Negative zooms the camera OUT.

    Guild Wars binds the wheel to camera distance, which is the one axis the
    harness could not reach and the one the operator was using when a rendering
    fault appeared (FINDINGS 25.5). A fault that only a human can provoke cannot
    be bisected, so this exists to make that camera state scriptable.

    The sign is the Windows convention -- away from the user is positive -- and
    on this client away/positive zooms IN. Verified by watching the frame, not
    assumed: `--walk "zoom:-14"` from the spawn visibly pulls the camera back.
    """
    if not _own_foreground(hwnd, pid):
        return False
    # One notch at a time. A single 14-notch event is legal and the client
    # coalesces it into one jump; separate events give the camera the same
    # rhythm a hand does, which is what the fault was provoked with.
    for _ in range(abs(int(notches))):
        user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0,
                           WHEEL_DELTA if notches > 0 else -WHEEL_DELTA, None)
        time.sleep(0.04)
    return True


def orbit(hwnd, pid, dx, dy, steps=12):
    """Right-drag the camera by (dx, dy) pixels. Positive dy pitches the view UP.

    Guild Wars orbits on a held right button. The drag is broken into `steps`
    because the client reads mouse MOVEMENT, and one teleporting jump from start
    to finish is a single huge delta that the camera clamps -- the same reason
    hold_key exists rather than a tap.

    THE BUTTON IS ALWAYS RELEASED, for the reason hold_key's is: mouse_event
    sets global button state, and a right button left down is stuck for the
    whole desktop and outlives this process.
    """
    if not _own_foreground(hwnd, pid):
        return False
    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return False
    # Park the pointer in the middle first. SetCursorPos is fine for THIS --
    # it only decides where the drag starts.
    user32.SetCursorPos(int((rect.left + rect.right) / 2),
                        int((rect.top + rect.bottom) / 2))
    time.sleep(0.05)
    # RELATIVE MOVE EVENTS, not SetCursorPos, and this is the whole reason the
    # first version did nothing. MEASURED 2026-08-11: the operator reported
    # "weird mouse movement with no camera shift", and the frames agreed --
    # terrain 78.8% before the pitch step and 79.1% after, i.e. the view did not
    # move at all. SetCursorPos WARPS the pointer; it does not synthesise an
    # input event, so a client reading the raw input path sees no motion. It is
    # the same defect as hold_key's bScan=0, in the same file, on the same day:
    # the verb emitted something, a test confirmed it emitted something, and the
    # client ignored all of it.
    #
    # A test cannot catch this on its own -- both versions emit a button down, a
    # sequence of moves and a button up, and only the client can say whether the
    # view turned. What the test CAN pin is that the movement goes through the
    # API that generates input events, which is why section 11 asserts on the
    # flags rather than only on the cursor positions.
    steps = max(1, int(steps))
    try:
        user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, None)
        time.sleep(0.05)
        sent_x = sent_y = 0
        for i in range(1, steps + 1):
            want_x, want_y = int(dx * i / steps), int(dy * i / steps)
            user32.mouse_event(MOUSEEVENTF_MOVE, want_x - sent_x,
                               want_y - sent_y, 0, None)
            sent_x, sent_y = want_x, want_y
            time.sleep(0.02)
    finally:
        user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, None)
    return True


VK_SHIFT, VK_CONTROL, VK_MENU = 0x10, 0x11, 0x12
MOD_KEYS = {"shift": VK_SHIFT, "ctrl": VK_CONTROL, "alt": VK_MENU}

# Keys a walk plan can HOLD by name -- the ones a single character cannot
# spell. ALT is the load-bearing entry: Guild Wars shows every ally/item
# nameplate while it is down, so "alt:4" with a shot cadence running is how a
# script reads names off the world without aiming at anything. LEFT/RIGHT are
# the keyboard turn, which rotates the character (and the chase camera with
# it) at the client's own fixed rate -- a timed hold is a yaw the server can
# neither see nor spoil, since turning in place sends nothing.
NAMED_KEYS = {
    "alt": VK_MENU, "ctrl": VK_CONTROL, "shift": VK_SHIFT,
    "space": 0x20, "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
}


def press_vk(hwnd, pid, vk, mods=(), allow_no_scan=False):
    """Press a RAW virtual key, optionally under modifier keys held down.

    Two differences from `press_key`, and both were forced by the target.

    THE SCAN CODE IS REAL. `press_key` passes `bScan=0`, which a UI reader
    accepts and the raw-input path silently drops -- the scar recorded in
    CLAUDE.md, where a client ignored 65 seconds of held W while the harness
    reported success. `MapVirtualKeyW(vk, MAPVK_VK_TO_VSC)` asks the active
    layout for the real one, exactly as `hold_key` does.

    A ZERO SCAN CODE IS REPORTED, NOT SENT. Some virtual keys have no position
    on the current layout -- `VK_SELECT` (0x29) is a live candidate, since the
    net-graph toggle wants that code and no ordinary keyboard produces it. If
    the layout has no scan code, sending one anyway would be the bScan=0 defect
    again with a different excuse, so this returns a distinct answer instead:
    the caller learns "this key cannot be typed here", which is a RESULT about
    the experiment rather than a failure of it.

    Returns True on send, False if focus was lost, and None if the key has no
    scan code on this layout.
    """
    if not _force_foreground(hwnd):
        return False
    fg = user32.GetForegroundWindow()
    owner = wintypes.DWORD()
    user32.GetWindowThreadProcessId(fg, ctypes.byref(owner))
    if owner.value != pid:
        return False

    scan = user32.MapVirtualKeyW(vk, MAPVK_VK_TO_VSC)
    if not scan and not allow_no_scan:
        return None
    # allow_no_scan sends bScan=0 DELIBERATELY, and it is not always wrong.
    # CLAUDE.md's scar is specific: a zero scan code is accepted by a UI reader
    # and dropped by the RAW INPUT path the client reads movement through. A
    # target that is itself a UI-message handler is therefore reachable this
    # way and only this way, when the layout has no position for the key. The
    # caller must ask for it, and the result is worth less than a real
    # keystroke: a silent client cannot distinguish "the key did nothing" from
    # "the key never arrived".
    held = [MOD_KEYS[m] for m in mods]
    try:
        for m in held:
            user32.keybd_event(m, user32.MapVirtualKeyW(m, MAPVK_VK_TO_VSC), 0, 0)
        time.sleep(0.03)
        user32.keybd_event(vk, scan, 0, 0)
        time.sleep(0.06)
        user32.keybd_event(vk, scan, KEYEVENTF_KEYUP, 0)
    finally:
        # Released on EVERY path, in reverse order. A modifier left latched by
        # an exception would ride into every later action in the script and
        # into the operator's own desktop afterwards.
        for m in reversed(held):
            user32.keybd_event(m, user32.MapVirtualKeyW(m, MAPVK_VK_TO_VSC),
                               KEYEVENTF_KEYUP, 0)
    return True


def press_key(hwnd, pid, vk):
    """Send one virtual key to the client, and ONLY ever to the client.

    Generalised out of press_enter on 2026-08-11 so the harness can press a skill
    slot. It keeps press_enter's safety property verbatim, because that property
    is the whole reason this function is shaped the way it is -- see below.

    Skill slots 1..8 are VK 0x31..0x38 ('1'..'8'), which is what makes an attack
    skill reachable from a script: GAME_CMSG 0x0027 exists in ArenaNet's traffic
    and our server had no arm for it until today, and nothing in this harness
    could provoke one to check the fix.

    IT SENT bScan=0 UNTIL 2026-08-14, AND THAT MEANT IT DID NOTHING IN WORLD.
    This function was written before `hold_key` found the scan-code trap, and
    when `hold_key` and `press_vk` were fixed it was left behind -- `keybd_event`
    was still called as `(vk, 0, 0, 0)`. A zero scan code is accepted by a UI
    reader and DROPPED by the raw input path the client reads in-world input
    through, so every scripted `key:` action since 2026-08-11 was delivered to
    nothing while this returned True and the harness printed "sent". Found when a
    `key:K` action reported sent and the Skills panel never opened; the owner
    pressed K by hand and it opened immediately.

    Everything reachable this way is in-world -- skill slots and panel hotkeys --
    so there is no case here that wants the zero. It now DELEGATES to `press_vk`
    rather than keeping a third copy of the send: three copies is how two of them
    got fixed and one did not.
    """
    return press_vk(hwnd, pid, vk)


def hold_key(hwnd, pid, vk, seconds, check_every=0.5):
    """Hold one key DOWN for `seconds`, then release it. Returns seconds held.

    Guild Wars moves the character while a movement key is held; `press_key`'s
    60 ms tap produces at most one stride and usually none. A walk long enough to
    reach a wall has to be a real hold, which means a keydown that is not paired
    with its keyup for several seconds -- and that is the dangerous part.

    THE KEY IS ALWAYS RELEASED. `keybd_event` sets global keyboard state, so a
    keydown left unpaired does not stay inside the client: it is a physically
    stuck key for the whole desktop, surviving this process's death. Every exit
    path from here, exception included, goes through the keyup in the `finally`.

    Focus is re-verified DURING the hold, not only at the start, and the hold is
    cut short the moment the client stops owning the foreground. Without that,
    an operator alt-tabbing away mid-walk would have several seconds of 'W'
    typed into whatever they switched to. Cutting short is reported by the
    return value -- a leg that ran for 1.2 of its 6.0 seconds is not the leg the
    caller asked for and the caller must be able to see that.
    """
    if not _force_foreground(hwnd):
        return 0.0
    fg = user32.GetForegroundWindow()
    owner = wintypes.DWORD()
    user32.GetWindowThreadProcessId(fg, ctypes.byref(owner))
    if owner.value != pid:
        return 0.0                        # someone else has focus - stay silent

    # WITH THE SCAN CODE, and that is the whole difference between this working
    # and not. MEASURED 2026-08-11: the first version passed bScan=0 the way
    # press_key and press_enter do, held W for 8 s into a client that was
    # foreground and fully in the world, and the client sent not one message --
    # the character did not move, did not turn, and nothing was typed into the
    # open chat box either. The keys reached the window and the client ignored
    # them.
    #
    # press_enter's docstring already names the reason without following it
    # through: this is a DirectX client reading the RAW INPUT path. That path
    # carries the hardware scan code, and a synthetic event with bScan=0 carries
    # no key at all as far as it is concerned. A UI-level reader takes the
    # virtual key and is happy; movement is not a UI-level reader.
    #
    # MapVirtualKey(vk, MAPVK_VK_TO_VSC) is the layout's own answer, so this
    # stays correct on a non-US keyboard where 'W' is not where it is here.
    scan = user32.MapVirtualKeyW(vk, MAPVK_VK_TO_VSC)
    started = time.perf_counter()
    # The keydown is INSIDE the try. It was outside it in the first version, and
    # the one path that leaves a key physically stuck for the whole desktop is a
    # keydown whose failure skips the finally. Releasing a key that was never
    # pressed is a no-op; the reverse is not.
    try:
        user32.keybd_event(vk, scan, 0, 0)
        while True:
            held = time.perf_counter() - started
            if held >= seconds:
                return held
            time.sleep(min(check_every, seconds - held))
            fg = user32.GetForegroundWindow()
            user32.GetWindowThreadProcessId(fg, ctypes.byref(owner))
            if owner.value != pid:
                return time.perf_counter() - started
    finally:
        user32.keybd_event(vk, scan, KEYEVENTF_KEYUP, 0)


def press_enter(hwnd, pid):
    """Send Enter to the client, and ONLY ever to the client.

    keybd_event is GLOBAL -- it goes to whatever window has focus right now, not to
    a window you name. SetForegroundWindow fails whenever the calling process is not
    already the foreground process, which is the normal case for a background
    harness, and it fails by returning FALSE rather than by raising. The first
    version ignored that return value, so on 2026-08-05 an Enter intended for the
    client was delivered into the owner's terminal session while they were typing.

    So: raise the window, then VERIFY the foreground window actually belongs to the
    client process, and refuse to send anything at all otherwise. Never send blind.

    keybd_event rather than PostMessage because this is a DirectX client reading
    input through the raw input path, which ignores posted window messages.
    """
    if not _force_foreground(hwnd):
        return False
    fg = user32.GetForegroundWindow()
    owner = wintypes.DWORD()
    user32.GetWindowThreadProcessId(fg, ctypes.byref(owner))
    if owner.value != pid:
        return False                      # someone else has focus - stay silent

    user32.keybd_event(VK_RETURN, 0, 0, 0)
    time.sleep(0.06)
    user32.keybd_event(VK_RETURN, 0, KEYEVENTF_KEYUP, 0)
    return True


def shot(hwnd, path):
    """Grab the client window. Reports failures rather than returning None quietly.

    A screenshot that silently does not happen is worse than no screenshot at all:
    the first version swallowed every error, so an empty output directory read as
    "nothing interesting" when it actually meant the window handle was corrupt.
    """
    try:
        from PIL import ImageGrab
    except ImportError:
        print("  [shot] PIL missing - no screenshots")
        return None
    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        print(f"  [shot] GetWindowRect failed, err={ctypes.get_last_error()}")
        return None
    box = (rect.left, rect.top, rect.right, rect.bottom)
    if box[2] <= box[0] or box[3] <= box[1]:
        print(f"  [shot] degenerate window rect {box}")
        return None
    try:
        ImageGrab.grab(bbox=box, all_screens=True).save(path)
        return path
    except Exception as ex:
        print(f"  [shot] {type(ex).__name__}: {ex}")
        return None


# ------------------------------------------------------------------ main ----

def close_client(proc):
    """Close the client cleanly enough that Gw.log survives.

    WM_CLOSE, not terminate(). The client buffers Gw.log and only flushes on a
    clean shutdown -- killing it throws away the very record we launched it to
    collect, which is how an earlier run came back with an 11-line log that
    stopped before anything interesting happened.
    """
    closer, _ = wait_window(proc.pid, timeout=5)
    if closer:
        user32.PostMessageW(closer, WM_CLOSE, 0, 0)
    try:
        proc.wait(timeout=20)
    except Exception:
        print("  clean close timed out - terminating, Gw.log may be truncated")
        try:
            proc.terminate()
            proc.wait(timeout=10)
        except Exception:
            pass
    time.sleep(1.0)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--account", default=None,
                    help="account label from vault/keys/accounts.json. "
                         "Omit for a loopback run: a synthetic credential is "
                         "used and no real account is involved.")
    # Resolved AFTER parsing, not as an eager default. As a default it scanned
    # the vault (and now reads a PE per candidate) on every `--help` and on
    # every run that passes an explicit --exe, and it had nowhere to report why
    # it came back empty.
    ap.add_argument("--exe", default=None,
                    help=f"Client to drive. Default: the newest vault/run copy "
                         f"OF BUILD {pinned.BUILD}, selected by reading each "
                         f"candidate's own build getter -- never by directory "
                         f"name or mtime.")
    # The original 9/5/5 spacing was tuned when the client still ran its updater
    # on boot. With the updater patched out every screen -- load, login, EULA,
    # character select -- comes up fast, and the old delays just sat idle.
    ap.add_argument("--actions", default="5:enter 4:enter 4:enter",
                    help="Whitespace-separated '<delay>:<kind>[:args]' steps. "
                         "kind is enter | key:<char> | click:<fx>,<fy> | interact:<agent_id> | "
                         "shot. Fractions are of "
                         "the window, so scripts survive a resize.")
    ap.add_argument("--linger", type=int, default=25,
                    help="Seconds to keep sampling after the last Enter.")
    ap.add_argument("--warn", type=float, default=3.0, metavar="SECONDS",
                    help="Countdown printed before any synthetic input, so a "
                         "human at the machine can take their hands off the "
                         "keyboard and mouse. Competing input makes a run fail "
                         "for a reason unrelated to what was being tested. "
                         "0 disables it (for unattended runs).")
    ap.add_argument("--outdir", default=vault_path("captures", "harness"))
    ap.add_argument("--keep-open", action="store_true",
                    help="Leave the client running at the end instead of closing it.")
    ap.add_argument("--authsrv", default="127.0.0.1",
                    help="Host for the client's -authsrv flag. 127/8 only -- "
                         "assert_safe refuses anything else. A second loopback "
                         "alias is how the handoff probes make the client's own "
                         "dials say which configured host they follow.")
    ap.add_argument("--client-arg", action="append", metavar="FLAG",
                    help="Extra flag for the client, repeatable. For experiments "
                         "needing UI the default launch does not show -- e.g. "
                         "`--client-arg -perf`, which draws triangles, fps and "
                         "transfer rate in the top-right corner. Flags that "
                         "decide where the client points are REFUSED; see "
                         "FORBIDDEN_CLIENT_ARGS.")
    a = ap.parse_args()

    if not a.exe:
        a.exe, why = select_run_exe()
        if not a.exe:
            raise SystemExit(why)
        print(f"client: {why}")
    args = ["-authsrv", a.authsrv, "-portal", "127.0.0.1", "-windowed", "-log"]
    # Choose the account rather than inheriting whatever the client autofilled. For a
    # loopback run that is a synthetic credential and no real one: our webgate says yes
    # to anyone, so a real account there buys nothing and is how the owner's password
    # reached 206 capture records. See toolkit/harness/accounts.py.
    acct = accounts.for_target(a.authsrv, a.account)
    args += accounts.login_args(acct)
    print(f"account: {accounts.describe(acct)}")
    for extra in (a.client_arg or []):
        if extra.split("=", 1)[0].lower() in FORBIDDEN_CLIENT_ARGS:
            raise SystemExit(
                f"--client-arg {extra!r} is refused: it decides where the client "
                f"points, which is the cage's job. See FORBIDDEN_CLIENT_ARGS.")
        args.append(extra)
    if a.client_arg:
        print(f"extra client flags: {' '.join(a.client_arg)}")
    host = assert_safe(a.exe, args)
    # And that this BINARY may be pointed at THAT host. assert_safe checks the path and
    # the argv; a binary can pass both and still be the wrong build for where it is
    # aimed -- and one copy sat uncaged for a day passing exactly those two checks.
    # See toolkit/clientpatch/cage.py.
    print(f"cage: {cage.assert_launch_safe(a.exe, host)['dh']} build, cleared for {host}")
    # And the archive, by the same rule as the line above and at THIS door too.
    # `session.py` states the rule -- "a guard that only guards one of two doors
    # is the shape of the defect it is here to prevent" -- and the two doors it
    # names are `session.py` and this file (PLAN.md: "both launch sites
    # (`drive_client.py`, `session.py`) assert it"). The client opens `Gw.dat`
    # from its OWN process directory; there is no flag for it, so the archive
    # this launch is really about is the one beside the exe, and a copy that
    # fails an open-time rule is repaired, rebuilt or silently emptied rather
    # than refused.
    client_dat = os.path.join(os.path.dirname(a.exe), "Gw.dat")
    print(f"archive: {datcheck.assert_archive_safe(client_dat, why='launch')['summary']}")

    stamp = time.strftime("%Y%m%dT%H%M%S")
    # WHERE THE RUN MAY WRITE (the audit's sec 9 item 3: an output path from the command line used to be written wherever it pointed). The DEFAULT is already the
    # vault; this is about the path an operator passes, and it is resolved
    # before the client is launched rather than after.
    try:
        outdir = resolve_out(os.path.join(a.outdir, stamp), "a client run")
    except ValueError as exc:
        raise SystemExit(str(exc))
    os.makedirs(outdir, exist_ok=True)

    # Instrumentation FIRST. See the module docstring.
    sampler = Sampler()
    sampler.start()
    print(f"sampler running at {sampler.interval*1000:.0f}ms")

    log_path = os.path.join(os.path.dirname(a.exe), "Gw.log")
    if os.path.exists(log_path):
        os.remove(log_path)        # so the run's log is only this run

    proc = subprocess.Popen([a.exe] + args, cwd=os.path.dirname(a.exe))
    sampler.pid = proc.pid
    print(f"launched pid {proc.pid}: {os.path.basename(a.exe)} "
          f"{' '.join(accounts.redact(args))}")

    hwnd, title = wait_window(proc.pid)
    if hwnd:
        print(f"window up: {title!r}")
    else:
        print("no window appeared - is the patcher stuck?")

    # HANDS OFF THE KEYBOARD AND MOUSE, and say so loudly enough to react to.
    #
    # This harness synthesises clicks and keypresses into the client's window. A
    # human touching the mouse or keyboard while it fires competes with it, and
    # the run can then fail for a reason that has nothing to do with what was
    # being tested -- which is worse than a plain failure, because the transcript
    # looks like evidence. OBSERVED 2026-08-11 during rung C2: the operator could
    # not tell when input was about to start, and there was no warning to react to.
    #
    # A countdown is enough. It costs `warn` seconds once per run, and the run is
    # already tens of seconds long.
    warn_hands_off(a.warn)

    # Scripted actions rather than three hardcoded Enters, because which input the
    # client accepts at each screen turned out not to be guessable: the login
    # screen ignored a focus-verified Enter even with the Log In button visibly
    # highlighted. Format: "<delay>:<kind>[:args]", e.g. "9:click:0.316,0.385".
    for i, spec in enumerate(a.actions.split()):
        parts = spec.split(":")
        delay, kind = float(parts[0]), parts[1]
        time.sleep(delay)
        hwnd, _ = wait_window(proc.pid, timeout=5)
        now = time.perf_counter() - sampler.t0
        if not hwnd:
            print(f"  t+{now:6.1f}s  NO WINDOW, skipped {spec}", flush=True)
            continue
        if kind == "interact":
            # NOT INPUT. Asks the SERVER to run its own INTERACT arm for a named
            # agent, because the harness cannot aim: projecting an agent's world
            # position to a screen pixel needs a camera yaw it does not have, and
            # a blind click at a guessed spot failed three runs in a row without
            # producing one interaction. Everything downstream is real -- real
            # messages, real client, real screen. What did not happen is a click,
            # and both this line and the gamesrv say so.
            import control
            control.request_interact(int(parts[2]))
            print(f"  t+{now:6.1f}s  interact:{parts[2]} -> asked the SERVER "
                  f"(no click was synthesised)", flush=True)
            ok = True
        elif kind == "click":
            fx, fy = (float(v) for v in parts[2].split(","))
            ok = click(hwnd, proc.pid, fx, fy)
        elif kind == "enter":
            ok = press_enter(hwnd, proc.pid)
        elif kind == "key":
            # "key:1" presses skill slot 1. Single characters only, mapped by
            # ord(), which covers 0-9 and A-Z -- the slots and the hotkeys.
            ch = parts[2]
            if len(ch) != 1:
                print(f"  key action wants ONE character, got {ch!r}"); continue
            ok = press_key(hwnd, proc.pid, ord(ch.upper()))
        elif kind == "vk":
            # "vk:0x29" or "vk:0x29:alt" or "vk:0x29:ctrl+shift". A RAW virtual
            # key, for codes no character maps to -- the net-graph toggle wants
            # 0x29, which is VK_SELECT and is on no ordinary keyboard.
            vk = int(parts[2], 0)
            raw = parts[3] if len(parts) > 3 and parts[3] else ""
            force = "force" in raw.split("+")
            mods = tuple(m for m in raw.split("+") if m and m != "force")
            bad = [m for m in mods if m not in MOD_KEYS]
            if bad:
                print(f"  unknown modifier(s) {bad} -- want "
                      f"{sorted(MOD_KEYS)} (or 'force')"); continue
            ok = press_vk(hwnd, proc.pid, vk, mods, allow_no_scan=force)
            if force:
                print(f"  t+{now:6.1f}s  vk {vk:#04x} sent with bScan=0 "
                      f"(FORCED) mods={mods or '-'} -- a UI handler accepts "
                      f"this; the raw-input path would drop it", flush=True)
            if ok is None:
                # Distinct from failure: the layout has no scan code for it.
                print(f"  t+{now:6.1f}s  vk {vk:#04x} has NO SCAN CODE on this "
                      f"layout -- not sent. That is an answer about the key, "
                      f"not a harness fault.", flush=True)
                ok = False
        elif kind == "shot":
            ok = True
        else:
            print(f"  unknown action {kind!r}"); continue
        time.sleep(0.6)
        shot(hwnd, os.path.join(outdir, f"{i+1}-{kind}.png"))
        # Never retried blind: without proven focus the input would land in
        # whatever the owner is typing in.
        print(f"  t+{now:6.1f}s  {spec} {'ok' if ok else 'NOT SENT (no focus)'}",
              flush=True)

    time.sleep(a.linger)
    hwnd, _ = wait_window(proc.pid, timeout=5)
    if hwnd:
        shot(hwnd, os.path.join(outdir, "4-final.png"))

    sampler.stop()
    time.sleep(0.1)

    if not a.keep_open:
        close_client(proc)

    gwlog = ""
    if os.path.exists(log_path):
        gwlog = open(log_path, encoding="utf-8", errors="replace").read()

    report = {
        # redact_for_file(), not args. This manifest lands in the vault beside the
        # captures, and accounts.redact's own docstring says it exists because "a
        # password that is merely 'not supposed to be logged' ends up logged" -- which
        # is what this line was doing: the console print two calls below was redacted
        # and the file was not. Found 2026-08-06, before a real automation account had
        # ever used it. Recording the label instead is what the field was for.
        "stamp": stamp, "exe": a.exe, "pid": proc.pid,
        "args": accounts.redact_for_file(args), "account": acct["label"],
        "endpoints": sampler.events, "gw_log": gwlog.splitlines(),
    }
    with open(os.path.join(outdir, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)

    print("\n=== endpoints the client touched ===")
    for e in sampler.events:
        note = ""
        port = int(e["remote"].rsplit(":", 1)[1])
        if port == 6112:
            note = "  <- our AuthSrv"
        elif port == 6601:
            note = "  <- our webgate"
        elif port in (80, 443):
            note = "  <- HTTP"
        print(f"  t+{e['t']:6.2f}s  {e['event']:12s} {e['state']:12s} "
              f"{e['remote']}{note}")
    if not sampler.events:
        print("  (none - the client opened no sockets at all)")

    print("\n=== Gw.log ===")
    for line in gwlog.splitlines()[-25:]:
        print("  " + line)

    print(f"\nreport + screenshots: {outdir}")


if __name__ == "__main__":
    sys.exit(main())
