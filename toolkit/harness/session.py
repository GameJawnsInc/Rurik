"""One command instead of three terminals: bring up the whole Rurik stack,
prove each server is actually listening, drive the patched client, and judge
the run by the client's own messages.

    python toolkit/harness/session.py                  # stack + client, judge to "in a map"
    python toolkit/harness/session.py --until login    # stop after the login verdict
    python toolkit/harness/session.py --serve          # just the stack; Ctrl-C stops it
    python toolkit/harness/session.py --replace        # stop stale python listeners first

WHY THE VERDICT COMES FROM THE CAPTURE. Every verb here ends in checkpoints
read from the live capture: messages only the client sends (its version header,
PORTAL_ACCOUNT_LOGIN, REQUEST_GAME_INSTANCE, the spawn rung). Reaching a
checkpoint means the client decided to advance -- not that we managed to send
something, and not that a screenshot looked right. Two runs once produced
byte-identical screenshots while stopping at different rungs; only the capture
told them apart.

WHY PRE-FLIGHT EXISTS. Both servers already refuse to bind a taken port --
SO_EXCLUSIVEADDRUSE, after a stale server silently shadowed a fresh one and
cost two sessions. This moves that discovery before anything starts: the stale
listener is named (pid and image) while nothing is half-launched. --replace
stops it only if it is a python process; anything else is refused by name,
because killing an unidentified process on a hunch is how a machine gets wrecked.

WHY THE INPUT RHYTHM IS NOT GATED ON CHECKPOINTS. The action script fires on
the same fixed schedule drive_client proved out. Which input each screen
accepts was not guessable (the login screen ignored a focus-verified Enter);
holding inputs until a capture event confirms the previous screen would stack
a new guess -- "this event means that screen is gone" -- on top of a rhythm
that already works. Observation is layered OVER the proven schedule, not
wired into it.
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
from tcptable import connections  # noqa: E402
from vaultpath import vault_path  # noqa: E402
from livecapture import CaptureTail, by  # noqa: E402
import drive_client as dc  # noqa: E402

TOOLKIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
# argtypes are not optional: a HANDLE truncated to a 32-bit int silently
# corrupts every call that receives it back. Same scar as drive_client.
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


# ------------------------------------------------------------- pre-flight ----

def server_specs(portal_port=6601, auth_port=6112, game_port=6113,
                 capture_root=None, auth_host="127.0.0.1"):
    """The three server processes, as (name, port, argv).

    The game channel is served by a second authsrv.py instance: the client
    declares its channel in its version header, so the same listener decodes
    the game catalog with no extra flag -- only the port and capture dir differ.
    capture_root overrides the vault capture dirs (tests use a temp dir).

    auth_host moves ONLY the authsrv listener (and must be handed to the
    client as -authsrv too). The webgate stays on 127.0.0.1: the -portal and
    -authsrv hosts have to be separable for the handoff probe to say which of
    the two the client's game dial follows.
    """
    def cap(sub):
        return (os.path.join(capture_root, sub) if capture_root
                else vault_path("captures", sub))
    py = [sys.executable, "-u"]
    return [
        ("webgate", portal_port,
         py + [os.path.join(TOOLKIT, "portal", "webgate.py"),
               "--port", str(portal_port), "--vault", cap("portal")]),
        ("authsrv", auth_port,
         py + [os.path.join(TOOLKIT, "authsrv", "authsrv.py"),
               "--port", str(auth_port), "--bind", auth_host,
               "--vault", cap("authsrv"), "--game-port", str(game_port)]),
        ("gamesrv", game_port,
         py + [os.path.join(TOOLKIT, "authsrv", "authsrv.py"),
               "--port", str(game_port), "--vault", cap("gamesrv"),
               "--game-port", str(game_port)]),
    ]


def listeners_on(port):
    return [c for c in connections()
            if c["state"] == "LISTEN" and c["local"].endswith(f":{port}")]


def image_name(pid):
    h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return "?"
    try:
        buf = ctypes.create_unicode_buffer(1024)
        n = wintypes.DWORD(1024)
        if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n)):
            return buf.value
        return "?"
    finally:
        kernel32.CloseHandle(h)


def preflight(specs, replace=False):
    """Every port free, or a loud exit naming exactly what is in the way."""
    for name, port, _ in specs:
        for row in listeners_on(port):
            img = image_name(row["pid"])
            base = os.path.basename(img).lower()
            if replace and base in ("python.exe", "pythonw.exe"):
                print(f"pre-flight: stopping stale {name} listener "
                      f"pid {row['pid']} on :{port}")
                os.kill(row["pid"], 15)
            else:
                hint = ("re-run with --replace to stop it"
                        if base in ("python.exe", "pythonw.exe") else
                        "not a python server -- REFUSING to touch it; stop it yourself")
                raise SystemExit(
                    f"Port {port} ({name}) is taken by pid {row['pid']} ({img}).\n"
                    f"  {hint}.")
    # Verify the kills landed rather than assuming: TerminateProcess is
    # asynchronous and a bind that races the dying listener still fails.
    deadline = time.monotonic() + 5
    while replace and time.monotonic() < deadline:
        if not any(listeners_on(p) for _, p, _ in specs):
            return
        time.sleep(0.1)
    leftover = [(n, p) for n, p, _ in specs if listeners_on(p)]
    if leftover:
        raise SystemExit(f"pre-flight: ports still taken after --replace: {leftover}")


# ------------------------------------------------------------------ stack ----

class Stack:
    """The three servers as child processes, each proven to own its port."""

    def __init__(self, specs, logdir, echo=False):
        self.specs = specs
        self.logdir = logdir
        self.echo = echo
        self.procs = {}          # name -> Popen
        self.logs = {}           # name -> path

    def _pump(self, name, proc, logf):
        for line in proc.stdout:
            logf.write(line)
            logf.flush()
            if self.echo:
                print(f"[{name}] {line}", end="", flush=True)
        logf.close()

    def start(self, timeout=20):
        os.makedirs(self.logdir, exist_ok=True)
        for name, port, cmd in self.specs:
            self.logs[name] = os.path.join(self.logdir, f"{name}.log")
            logf = open(self.logs[name], "a", encoding="utf-8")
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
            self.procs[name] = proc
            threading.Thread(target=self._pump, args=(name, proc, logf),
                             daemon=True).start()

        # Listening is proven per-pid: the port must be LISTEN *and* owned by
        # the child we just started. "Something answers on 6112" was exactly
        # the symptom of the stale-server bug this exists to prevent.
        deadline = time.monotonic() + timeout
        pending = {name: port for name, port, _ in self.specs}
        while pending and time.monotonic() < deadline:
            for name, port in list(pending.items()):
                proc = self.procs[name]
                if proc.poll() is not None:
                    self.stop()
                    raise SystemExit(
                        f"{name} exited with code {proc.returncode} before "
                        f"listening.\n{self._tail(name)}")
                if any(r["pid"] == proc.pid for r in listeners_on(port)):
                    print(f"  {name} up: port {port}  pid {proc.pid}")
                    del pending[name]
            time.sleep(0.1)
        if pending:
            tails = "\n".join(self._tail(n) for n in pending)
            self.stop()
            raise SystemExit(f"servers never listened: {sorted(pending)}\n{tails}")

    def _tail(self, name, n=15):
        try:
            with open(self.logs[name], encoding="utf-8", errors="replace") as f:
                lines = f.readlines()[-n:]
            return f"--- last lines of {name} ---\n" + "".join(lines)
        except OSError:
            return f"--- no log for {name} ---"

    def stop(self):
        # terminate(), not a console signal: both servers flush every capture
        # line as it is written, so an abrupt exit loses nothing -- and a
        # CTRL_BREAK reaches them as SIGBREAK, which python dies on anyway.
        for name, proc in self.procs.items():
            if proc.poll() is None:
                proc.terminate()
        for name, proc in self.procs.items():
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print(f"  {name} did not exit; leaving pid {proc.pid} to the OS")


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
# The game-channel checkpoints watch BOTH capture dirs. OBSERVED 2026-08-06
# (three discriminating runs, studies/handshake/PLAN.md §10): the client dials
# <GAME_SERVER_INFO host> : hardcoded 6112 for the game channel -- the
# advertised port is decorative, and -authsrv plays no part in the game dial.
# Under this stack's defaults that host is 127.0.0.1, so the dial lands on the
# AUTH listener, whose catalog self-selection serves the game and records to
# captures/authsrv; the gamesrv instance only receives it if the handoff names
# a host of its own. The harness asserts on where the events actually land.
MAP_CHECKPOINTS = [
    ("client asked for a game instance", "auth", by(kind="game_instance_request"),
     "no Play request -- did the client reach character select?"),
    ("client opened its game channel", "game", by(kind="version", channel="game"),
     "no game-channel connection anywhere -- did the client die after Play?"),
    ("game channel keyed", "game", by(kind="key_exchange_ok"),
     "game DH failed -- same keys serve both channels, so this is new information"),
    ("client requested its spawn", "game", by(kind="decoded", opcode=0x0088),
     "connected but stopped before the spawn rung -- run progress.py for the ladder"),
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


# ------------------------------------------------------------ client run ----

# Every step is a CLICK, never an Enter. Proven repeatedly: drive_client
# recorded the login screen ignoring a focus-verified Enter on 2026-08-05, the
# harness re-proved it on 2026-08-06 (three delivered Enters, screenshots of an
# untouched login screen, zero portal traffic), and the EULA dialog ignored two
# more. The fractions are button centers within the window, read from run
# screenshots: Log In (login screen), I Accept (EULA), Play (character select).
# The EULA appears on every login -- nothing server-side remembers ACCEPT_EULA.
ACTIONS = {
    "login": "5:click:0.316,0.385",
    "map": "5:click:0.316,0.385 4:click:0.556,0.875 4:click:0.835,0.973",
}


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


def run_client(a, outdir):
    tails = {"auth": CaptureTail(vault_path("captures", "authsrv")),
             "game": CaptureTail(vault_path("captures", "authsrv"),
                                 vault_path("captures", "gamesrv"))}

    # Instrumentation first, always -- an instrument that was not yet running
    # produces absence of evidence, never evidence of absence.
    sampler = dc.Sampler()
    sampler.start()

    args = ["-authsrv", a.auth_host, "-portal", "127.0.0.1", "-windowed", "-log"]
    dc.assert_safe(a.exe, args)
    log_path = os.path.join(os.path.dirname(a.exe), "Gw.log")
    if os.path.exists(log_path):
        os.remove(log_path)

    proc = subprocess.Popen([a.exe] + args, cwd=os.path.dirname(a.exe))
    sampler.pid = proc.pid
    print(f"client pid {proc.pid}: {os.path.basename(a.exe)} {' '.join(args)}")

    actions = a.actions or ACTIONS[a.until]
    sent, results, ok, undec = [], [], False, []
    try:
        for i, spec in enumerate(actions.split()):
            parts = spec.split(":")
            delay, kind = float(parts[0]), parts[1]
            time.sleep(delay)
            hwnd, _ = dc.wait_window(proc.pid, timeout=5)
            if not hwnd:
                sent.append({"spec": spec, "sent": False})
                print(f"  action {spec}: NO WINDOW", flush=True)
                continue
            if kind == "click":
                fx, fy = (float(v) for v in parts[2].split(","))
                delivered = dc.click(hwnd, proc.pid, fx, fy)
            elif kind == "enter":
                delivered = dc.press_enter(hwnd, proc.pid)
            else:
                raise SystemExit(f"unknown action kind {kind!r} in {spec!r}")
            sent.append({"spec": spec, "sent": delivered})
            time.sleep(0.6)
            shot_if_foreground(hwnd, proc.pid,
                               os.path.join(outdir, f"{i + 1}-{kind}.png"))
            print(f"  action {spec}: "
                  f"{'sent' if delivered else 'NOT SENT (no focus)'}", flush=True)

        checkpoints = (LOGIN_CHECKPOINTS if a.until == "login"
                       else LOGIN_CHECKPOINTS + MAP_CHECKPOINTS)
        print("\n=== verdict, from the client's own messages ===")
        results, ok = judge(tails, checkpoints, sampler.t0)

        undec = [e for t in tails.values() for e in t.events
                 if e.get("kind") == "undecodable"]
        if undec:
            print(f"  NOTE: {len(undec)} undecodable event(s) -- the framer "
                  f"stopped; the leading bytes are the next thing to identify")

        hwnd, _ = dc.wait_window(proc.pid, timeout=5)
        if hwnd:
            shot_if_foreground(hwnd, proc.pid, os.path.join(outdir, "final.png"))
    finally:
        if not a.keep_open:
            dc.close_client(proc)
        sampler.stop()

    for t in tails.values():
        t.poll()                     # pick up anything written during close
    gwlog = ""
    if os.path.exists(log_path):
        gwlog = open(log_path, encoding="utf-8", errors="replace").read()
    report = {
        "exe": a.exe, "until": a.until, "actions": sent,
        "checkpoints": results, "passed": ok,
        "captures": sorted(f for t in tails.values() for f in t.files()),
        "endpoints": sampler.events,
        "undecodable": len(undec), "gw_log": gwlog.splitlines(),
    }
    with open(os.path.join(outdir, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)

    unsent = [s["spec"] for s in sent if not s["sent"]]
    if unsent and not ok:
        print(f"\n  NB: input was never delivered for {unsent} (focus refused --"
              f" the machine was in use). That, not the server, is the likely cause.")
    print(f"\n{'RUN VERDICT: PASS' if ok else 'RUN VERDICT: FAIL'}  "
          f"(target: {a.until})")
    print(f"report + screenshots: {outdir}")
    return 0 if ok else 1


# ------------------------------------------------------------------ main ----

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--serve", action="store_true",
                    help="run the stack only, echoing server output; Ctrl-C stops it")
    ap.add_argument("--until", choices=("login", "map"), default="map",
                    help="how far the client run must get to pass")
    ap.add_argument("--replace", action="store_true",
                    help="stop stale python listeners found on our ports")
    ap.add_argument("--keep-open", action="store_true",
                    help="leave the client running after the verdict")
    ap.add_argument("--exe", default=None,
                    help="patched client exe; default: newest under vault/run")
    ap.add_argument("--actions", default=None,
                    help="override the input script; default depends on --until "
                         f"(login: {ACTIONS['login']!r}, map: {ACTIONS['map']!r})")
    ap.add_argument("--game-port", type=int, default=6113,
                    help="Port the handoff advertises AND the gamesrv listens "
                         "on. OBSERVED (handshake PLAN §10): the client never "
                         "dials it -- it dials the handoff HOST at 6112. This "
                         "flag ran the probe that established that.")
    ap.add_argument("--auth-host", default="127.0.0.1",
                    help="Loopback address for the authsrv listener and the "
                         "client's -authsrv flag. 127/8 only. A second alias "
                         "(127.0.0.2) ran the probe that showed -authsrv plays "
                         "no part in the game dial (handshake PLAN §10).")
    a = ap.parse_args()

    if not dc.is_loopback(a.auth_host):
        raise SystemExit(f"--auth-host {a.auth_host!r} is not a 127/8 loopback "
                         f"address. The client must stay unable to reach ArenaNet.")

    specs = server_specs(game_port=a.game_port, auth_host=a.auth_host)
    preflight(specs, replace=a.replace)

    stamp = time.strftime("%Y%m%dT%H%M%S")
    outdir = vault_path("captures", "harness", stamp)
    os.makedirs(outdir, exist_ok=True)

    stack = Stack(specs, logdir=outdir, echo=a.serve)
    print("starting the stack:")
    stack.start()
    try:
        if a.serve:
            print("\nstack is up. Launch the client yourself, or Ctrl-C to stop.")
            while True:
                for name, proc in stack.procs.items():
                    if proc.poll() is not None:
                        raise SystemExit(f"{name} exited with "
                                         f"code {proc.returncode}\n"
                                         + stack._tail(name))
                time.sleep(0.5)
        a.exe = a.exe or dc.newest_run_exe()
        if not a.exe:
            raise SystemExit(f"No Gw.exe under {vault_path('run')} — "
                             f"run make_run_dir.py first (RUNBOOK.md).")
        return run_client(a, outdir)
    except KeyboardInterrupt:
        print("\nstopping")
        return 130
    finally:
        stack.stop()


if __name__ == "__main__":
    sys.exit(main())
