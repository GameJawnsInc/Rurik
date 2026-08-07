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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# clientpatch/ is not on the path by either of the two lines above, and `import cage`
# below therefore failed at MODULE level from 2026-08-06 until this line was added --
# so both launch sites were unrunnable for as long as the cage guard existed in them.
# test_harness.py would have caught it on the first run; it is in CLAUDE.md's suite
# list and was not run. A guard inside a module that cannot be imported is the same
# wish as a rule nothing checks.
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "clientpatch"))
from tcptable import connections  # noqa: E402
from vaultpath import vault_path  # noqa: E402
import cage  # noqa: E402
import accounts  # noqa: E402

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


def is_loopback(value):
    parts = value.split(".")
    return (len(parts) == 4 and parts[0] == "127"
            and all(p.isdigit() and int(p) <= 255 for p in parts))


def newest_run_exe():
    """The most recently assembled vault/run/<build>/Gw.exe, or None.

    Discovered rather than hardcoded: the run dir is rebuilt after every
    ArenaNet update, and a default frozen to one build stamp goes stale the
    moment make_run_dir.py assembles the next one.
    """
    import glob
    cands = glob.glob(os.path.join(vault_path("run"), "*", "Gw.exe"))
    # -probe dirs are experiment copies; prefer the plain build dir.
    plain = [c for c in cands if not os.path.dirname(c).endswith("-probe")]
    pick = plain or cands
    return max(pick, key=os.path.getmtime) if pick else None

user32 = ctypes.WinDLL("user32", use_last_error=True)
VK_RETURN = 0x0D
KEYEVENTF_KEYUP = 0x0002
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

user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.mouse_event.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
                               wintypes.DWORD, ctypes.c_void_p]

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32.GetCurrentThreadId.restype = wintypes.DWORD
SW_RESTORE = 9
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004


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


def assert_safe(exe, args):
    """Refuse a binary we do not stage, and an argv that cannot mean one thing.

    Returns the host this argv points at, for the caller to hand to
    `cage.assert_launch_safe` -- which is what decides whether THIS binary may be
    pointed THERE. The split is deliberate: this function is about the argv, that one
    is about the bytes, and neither can answer the other's question.
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
    ap.add_argument("--exe", default=newest_run_exe())
    # The original 9/5/5 spacing was tuned when the client still ran its updater
    # on boot. With the updater patched out every screen -- load, login, EULA,
    # character select -- comes up fast, and the old delays just sat idle.
    ap.add_argument("--actions", default="5:enter 4:enter 4:enter",
                    help="Whitespace-separated '<delay>:<kind>[:args]' steps. "
                         "kind is enter | click:<fx>,<fy> | shot. Fractions are of "
                         "the window, so scripts survive a resize.")
    ap.add_argument("--linger", type=int, default=25,
                    help="Seconds to keep sampling after the last Enter.")
    ap.add_argument("--outdir", default=vault_path("captures", "harness"))
    ap.add_argument("--keep-open", action="store_true",
                    help="Leave the client running at the end instead of closing it.")
    ap.add_argument("--authsrv", default="127.0.0.1",
                    help="Host for the client's -authsrv flag. 127/8 only -- "
                         "assert_safe refuses anything else. A second loopback "
                         "alias is how the handoff probes make the client's own "
                         "dials say which configured host they follow.")
    a = ap.parse_args()

    if not a.exe:
        raise SystemExit(f"No Gw.exe under {vault_path('run')} — "
                         f"run make_run_dir.py first (RUNBOOK.md, one-time setup).")
    args = ["-authsrv", a.authsrv, "-portal", "127.0.0.1", "-windowed", "-log"]
    # Choose the account rather than inheriting whatever the client autofilled. For a
    # loopback run that is a synthetic credential and no real one: our webgate says yes
    # to anyone, so a real account there buys nothing and is how the owner's password
    # reached 206 capture records. See toolkit/harness/accounts.py.
    acct = accounts.for_target(a.authsrv, a.account)
    args += accounts.login_args(acct)
    print(f"account: {accounts.describe(acct)}")
    host = assert_safe(a.exe, args)
    # And that this BINARY may be pointed at THAT host. assert_safe checks the path and
    # the argv; a binary can pass both and still be the wrong build for where it is
    # aimed -- and one copy sat uncaged for a day passing exactly those two checks.
    # See toolkit/clientpatch/cage.py.
    print(f"cage: {cage.assert_launch_safe(a.exe, host)['dh']} build, cleared for {host}")

    stamp = time.strftime("%Y%m%dT%H%M%S")
    outdir = os.path.join(a.outdir, stamp)
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
        if kind == "click":
            fx, fy = (float(v) for v in parts[2].split(","))
            ok = click(hwnd, proc.pid, fx, fy)
        elif kind == "enter":
            ok = press_enter(hwnd, proc.pid)
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
