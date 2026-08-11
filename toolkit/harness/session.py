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
import shlex
import subprocess
import sys
import threading
import time
from ctypes import wintypes

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLKIT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, TOOLKIT)
# See drive_client.py for the whole story: `cage.py` is in clientpatch/, not
# here. This module got away without the line only because it imports
# drive_client one line before it imports cage and inherited the path that
# module inserts -- an ordering accident that breaks the day the two swap.
sys.path.insert(0, os.path.join(TOOLKIT, "clientpatch"))
from tcptable import connections  # noqa: E402
from vaultpath import vault_path  # noqa: E402
from livecapture import CaptureTail, by  # noqa: E402
import drive_client as dc  # noqa: E402
import cage  # noqa: E402
import accounts  # noqa: E402

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

def split_args(text):
    r"""Split a --game-args string WITHOUT eating Windows backslashes.

    shlex.split defaults to posix=True, where a backslash is an ESCAPE character.
    On this platform that silently destroys every path it is handed -- splitting
    r"--tape C:\gd\Rurik\vault" yields ['--tape', 'C:gdRurikvault'].

    That is what happened on 2026-08-10: the tape refused to load and named a path
    with every separator missing. The mangling was here, one process before the
    error, and the only reason it was diagnosable in one read is that the refusal
    printed the path it had actually been given rather than the one it wanted.

    posix=False keeps backslashes but leaves quote characters attached to the
    token, so surrounding quotes are stripped here; that pair is what lets a quoted
    path containing spaces survive as well.
    """
    out = []
    for tok in shlex.split(text or "", posix=False):
        if len(tok) >= 2 and tok[0] == tok[-1] and tok[0] in ("'", '"'):
            tok = tok[1:-1]
        out.append(tok)
    return out


def is_labelling(a):
    """Is --labelrun among the gamesrv flags?

    A function rather than a local, because the answer is needed in main() (to route
    the gamesrv's stdout to the screen) AND in run_client() (to silence the hold's
    progress line). The first version computed it once in main() and read it in
    run_client, which is a different scope: `NameError: name 'labelling' is not
    defined`, at runtime, thirty seconds into a real session, after ast.parse and
    every test in the suite had passed. See test_srclint.py.
    """
    return "--labelrun" in split_args(getattr(a, "game_args", ""))


def server_specs(portal_port=6601, auth_port=6112, game_port=6112,
                 capture_root=None, auth_host="127.0.0.1",
                 game_host="127.0.0.3", game_args=(), hops=()):
    """The three server processes, as (name, host, port, argv).

    The game channel is served by a second authsrv.py instance: the client
    declares its channel in its version header, so the same listener decodes
    the game catalog with no extra flag. OBSERVED (handshake PLAN §10): the
    client dials <GAME_SERVER_INFO host> : hardcoded 6112, so the gamesrv gets
    a loopback alias of its own (game_host) and binds 6112 there, and the
    authsrv advertises exactly that endpoint in the handoff. Auth and game may
    share port 6112 because their hosts differ.
    capture_root overrides the vault capture dirs (tests use a temp dir).

    auth_host moves ONLY the authsrv listener (and must be handed to the
    client as -authsrv too). The webgate stays on 127.0.0.1: the -portal,
    -authsrv and handoff hosts have to be separable for a probe to say which
    of them the client's game dial follows.

    game_args goes to the GAMESRV alone, and that asymmetry is the point. The
    instance loads on the game channel, so --probe, --map, --no-enemy and
    --no-weapon all have to reach that listener; handing them to the authsrv
    as well would arm a second, idle copy of the same experiment. Without this
    the one-command loop and the probe mechanism could not be used together at
    all -- the probes had to be run from the hand-rolled three-terminal loop,
    which is the one that has no port pre-flight and no capture checkpoints.
    """
    def cap(sub):
        return (os.path.join(capture_root, sub) if capture_root
                else vault_path("captures", sub))
    py = [sys.executable, "-u"]
    return [
        ("webgate", "127.0.0.1", portal_port,
         py + [os.path.join(TOOLKIT, "portal", "webgate.py"),
               "--port", str(portal_port), "--vault", cap("portal")]),
        ("authsrv", auth_host, auth_port,
         py + [os.path.join(TOOLKIT, "authsrv", "authsrv.py"),
               "--port", str(auth_port), "--bind", auth_host,
               "--vault", cap("authsrv"),
               "--game-host", game_host, "--game-port", str(game_port)]),
        ("gamesrv", game_host, game_port,
         py + [os.path.join(TOOLKIT, "authsrv", "authsrv.py"),
               "--port", str(game_port), "--bind", game_host,
               "--vault", cap("gamesrv"),
               "--game-host", game_host, "--game-port", str(game_port)]
         + list(game_args)),
    ] + [
        # R1.5 chaining (PLAN §8.0 item 0b): one gamesrv per further hop, each on its
        # own 127.x alias. The client dials <host>:6112 and the advertised port is
        # decorative, so hops CANNOT be separated by port -- an alias each is the only
        # arrangement that works, and it is also the one that changes one variable:
        # every recorded hop went to a different address, so re-dialling the SAME
        # endpoint is a client behaviour the capture never witnessed.
        #
        # Distinct capture dirs are not tidiness. Every instance names its files
        # `authsrv-<stamp>-c1.jsonl` with a conn_id that restarts at 1 per process, so
        # two hops starting in the same second would write over each other's capture
        # and the run would look fine.
        (f"gamesrv{i + 2}", host, game_port,
         py + [os.path.join(TOOLKIT, "authsrv", "authsrv.py"),
               "--port", str(game_port), "--bind", host,
               "--vault", cap(os.path.join("gamesrv", f"hop{i + 2}")),
               "--game-host", host, "--game-port", str(game_port)]
         + list(argv))
        for i, (host, argv) in enumerate(hops)
    ]


def chain_hold(capture_dir, order, per_hop=15.0, slack=30.0):
    """(hold_seconds, tape_seconds) -- how long a chained run must stay up.

    Derived from the tapes rather than asked of the operator, because the verdict this
    harness prints cannot be used as the stop signal under a tape. "Body is in the map"
    is true within about five seconds and says nothing about the six minutes that follow,
    so a chain run that stops at its verdict target stops before the experiment starts.
    That is not hypothetical: it is what the first chain run did, and it printed PASS.
    """
    sys.path.insert(0, os.path.join(TOOLKIT, "authsrv"))
    import tape as tapemod
    total = sum(tapemod.load_tape(capture_dir, c)[0]["seconds"] for c in order)
    return total + per_hop * len(order) + slack, total


def hop_aliases(n, first="127.0.0.3"):
    """[host] for n chained gamesrv instances, starting at `first`.

    127.0.0.3, .4, .5, ... Any 127/8 address is loopback to `origin.is_loopback`, to
    the launch gate and to authsrv's own bind refusal, so extra aliases need no new
    safety plumbing and Windows answers on all of them without configuration.
    """
    head = first.rsplit(".", 1)
    base = int(head[1])
    if base + n - 1 > 254:
        raise ValueError(f"{n} hops from {first} runs past the end of the octet")
    return [f"{head[0]}.{base + i}" for i in range(n)]


def chain_specs(capture_dir, game_args=(), first="127.0.0.3"):
    """(game_args_for_hop1, hops, order, hosts) for a whole recorded chain.

    Each hop is armed with its own tape and told to repoint its handoff at the NEXT
    hop's alias; the last hop is truncated instead, because there is nowhere left to
    send the client and an un-rewritten handoff would dial ArenaNet.
    """
    sys.path.insert(0, os.path.join(TOOLKIT, "authsrv"))
    import tape as tapemod
    order = tapemod.chain(capture_dir)
    if not order:
        raise SystemExit(
            f"no chain in {capture_dir}: no tape there hands the client to another "
            f"connection recorded in the same capture. Play a single tape with "
            f"--game-args '--tape ...' instead.")
    hosts = hop_aliases(len(order), first)
    argvs = []
    for i, conn in enumerate(order):
        argv = list(game_args) + ["--tape", capture_dir, "--tape-connection", conn]
        if i + 1 < len(order):
            argv += ["--tape-rewrite-next", hosts[i + 1]]
        else:
            argv += ["--tape-no-transfer"]
        argvs.append(argv)
    return argvs[0], list(zip(hosts[1:], argvs[1:])), order, hosts


def listeners_on(port, host=None):
    """LISTEN rows on a port; with host, only rows that would collide there.

    host=None keeps the old port-only reading. With a host, a row matches if
    it is bound to that exact host OR to the 0.0.0.0 wildcard -- a wildcard
    bind owns the port on every alias, so it is never out of the way.
    """
    rows = [c for c in connections()
            if c["state"] == "LISTEN" and c["local"].endswith(f":{port}")]
    if host is None:
        return rows
    return [r for r in rows
            if r["local"] in (f"{host}:{port}", f"0.0.0.0:{port}")]


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
    """Every endpoint free, or a loud exit naming exactly what is in the way.

    Host-aware on purpose: authsrv and gamesrv both use port 6112, at
    different loopback aliases. A port-only match would report each as
    squatting on the other's endpoint.
    """
    for name, host, port, _ in specs:
        for row in listeners_on(port, host):
            img = image_name(row["pid"])
            base = os.path.basename(img).lower()
            if replace and base in ("python.exe", "pythonw.exe"):
                print(f"pre-flight: stopping stale {name} listener "
                      f"pid {row['pid']} on {row['local']}")
                os.kill(row["pid"], 15)
            else:
                hint = ("re-run with --replace to stop it"
                        if base in ("python.exe", "pythonw.exe") else
                        "not a python server -- REFUSING to touch it; stop it yourself")
                raise SystemExit(
                    f"{host}:{port} ({name}) is taken by pid {row['pid']} ({img}).\n"
                    f"  {hint}.")
    # Verify the kills landed rather than assuming: TerminateProcess is
    # asynchronous and a bind that races the dying listener still fails.
    deadline = time.monotonic() + 5
    while replace and time.monotonic() < deadline:
        if not any(listeners_on(p, h) for _, h, p, _ in specs):
            return
        time.sleep(0.1)
    leftover = [(n, h, p) for n, h, p, _ in specs if listeners_on(p, h)]
    if leftover:
        raise SystemExit(f"pre-flight: endpoints still taken after --replace: {leftover}")


# ------------------------------------------------------------------ stack ----

class Stack:
    """The three servers as child processes, each proven to own its port."""

    def __init__(self, specs, logdir, echo=False):
        """`echo` is False, True for every server, or a set of server names.

        The set exists for --labelrun, which prompts a human through the GAMESRV's
        stdout. Without it those prompts go only to gamesrv.log and the operator
        sees nothing but this process's own "holding" line -- which is exactly what
        happened on 2026-08-10, and the run was unusable because the script it was
        driving was invisible. Echoing all three servers instead would bury the
        prompts in webgate and authsrv chatter, so the filter is per-name.
        """
        self.specs = specs
        self.logdir = logdir
        self.echo = echo
        self.procs = {}          # name -> Popen
        self.logs = {}           # name -> path

    def _echoes(self, name):
        return self.echo is True or (bool(self.echo) and name in self.echo)

    def _pump(self, name, proc, logf):
        for line in proc.stdout:
            logf.write(line)
            logf.flush()
            if self._echoes(name):
                # No [name] prefix when only one server is echoed: the prompts are
                # formatted banners meant to be read at a glance, and a prefix on
                # every line of one wrecks the alignment.
                prefix = "" if self.echo is not True else f"[{name}] "
                print(f"{prefix}{line}", end="", flush=True)
        logf.close()

    def start(self, timeout=20):
        os.makedirs(self.logdir, exist_ok=True)
        for name, host, port, cmd in self.specs:
            self.logs[name] = os.path.join(self.logdir, f"{name}.log")
            logf = open(self.logs[name], "a", encoding="utf-8")
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
            self.procs[name] = proc
            threading.Thread(target=self._pump, args=(name, proc, logf),
                             daemon=True).start()

        # Listening is proven per-pid: the endpoint must be LISTEN *and* owned
        # by the child we just started. "Something answers on 6112" was exactly
        # the symptom of the stale-server bug this exists to prevent -- and now
        # that two servers share port 6112 at different hosts, the host is part
        # of what must be proven.
        deadline = time.monotonic() + timeout
        pending = {name: (host, port) for name, host, port, _ in self.specs}
        while pending and time.monotonic() < deadline:
            for name, (host, port) in list(pending.items()):
                proc = self.procs[name]
                if proc.poll() is not None:
                    self.stop()
                    raise SystemExit(
                        f"{name} exited with code {proc.returncode} before "
                        f"listening.\n{self._tail(name)}")
                if any(r["pid"] == proc.pid for r in listeners_on(port, host)):
                    print(f"  {name} up: {host}:{port}  pid {proc.pid}")
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


# ------------------------------------------------------------ client run ----

# Every step is a CLICK, never an Enter. Proven repeatedly: drive_client
# recorded the login screen ignoring a focus-verified Enter on 2026-08-05, the
# harness re-proved it on 2026-08-06 (three delivered Enters, screenshots of an
# untouched login screen, zero portal traffic), and the EULA dialog ignored two
# more. The fractions are button centers within the window, read from run
# screenshots: Log In (login screen), I Accept (EULA), Play (character select).
# The EULA appears on every login -- nothing server-side remembers ACCEPT_EULA.
# With -email/-password/-character (accounts.login_args) the client keys the channel, logs
# in past a suppressed EULA (authsrv sends the current revision in ACCOUNT_INFO), and lands
# on character select with the account's character already selected. -character only
# SELECTS it -- it does not enter the world -- so `map` needs one Play click. That click is
# EVENT-DRIVEN (`play`), not on a timer: the game loads near-instantly, so a fixed delay
# either clicks the loading screen or, set late to be safe, clicks into the map after Play
# already entered. `play` waits for login, then clicks Play and STOPS the instant the
# client requests its instance, so it never clicks twice on the map. `login` needs no
# input; auto-login gets there on its own.
ACTIONS = {
    "login": "3:enter",
    "map": "0:play",
}

# Play button centre, MEASURED from a real character-select screenshot (green button at
# pixel (1607,1010) in a 1926x1039 window) -- and the same spot the working 2026-08-06
# drive clicked. An earlier value of 0.936 was measured against a wrong height and landed
# just above the button.
PLAY_FX, PLAY_FY = 0.834, 0.972


def _play(tails, proc, outdir):
    """Wait for login, then click the Play button until the client enters the world.

    Event-driven: it starts once login completes (character select is up, -character
    already selected) and STOPS the instant the client requests its game instance, so it
    never clicks into the map. dc.click raises the client foreground first.
    """
    login = by_any(by(kind="login_ok"), by(kind="login_rejected"))
    ev, idx = tails["auth"].wait_for(login, timeout=90)
    if not ev:
        print("  play: login never completed", flush=True)
        return False
    delivered = False
    for attempt in range(6):
        hwnd, _ = dc.wait_window(proc.pid, timeout=5)
        if not hwnd:
            break
        time.sleep(0.5)                          # let character select paint
        if dc.click(hwnd, proc.pid, PLAY_FX, PLAY_FY):
            delivered = True
        got, idx = tails["auth"].wait_for(by(kind="game_instance_request"),
                                          timeout=2.0, since=idx)
        if got:
            print(f"  play: entered the world (click {attempt + 1})", flush=True)
            return True
    print("  play: clicked Play but saw no game-instance request "
          f"(clicks landed: {delivered})", flush=True)
    return delivered


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


def hold_open(proc, seconds, tails, outdir, quiet=False):
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
    last = 0.0
    while proc.poll() is None and (end is None or time.monotonic() < end):
        time.sleep(0.5)
        for t in tails.values():
            t.poll()                 # keep the capture flowing during the hold
        now = time.monotonic()
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
        print(f"  client exited with code {proc.returncode} during the hold — "
              f"read the dialog with toolkit/harness/read_error_dialog.py")


def run_client(a, outdir):
    tails = {"auth": CaptureTail(vault_path("captures", "authsrv")),
             "game": CaptureTail(vault_path("captures", "gamesrv"))}

    # Instrumentation first, always -- an instrument that was not yet running
    # produces absence of evidence, never evidence of absence.
    sampler = dc.Sampler()
    sampler.start()

    args = ["-authsrv", a.auth_host, "-portal", "127.0.0.1", "-windowed", "-log"]
    acct = accounts.for_target(a.auth_host, getattr(a, "account", None))
    args += accounts.login_args(acct)
    print(f"account: {accounts.describe(acct)}")
    host = dc.assert_safe(a.exe, args)
    # Both launch sites run the gate independently rather than one trusting the other.
    # A guard that only guards one of two doors is the shape of the defect it is here
    # to prevent -- vault/run held two patched binaries and one was caged.
    print(f"cage: {cage.assert_launch_safe(a.exe, host)['dh']} build, cleared for {host}")
    log_path = os.path.join(os.path.dirname(a.exe), "Gw.log")
    if os.path.exists(log_path):
        os.remove(log_path)

    proc = subprocess.Popen([a.exe] + args, cwd=os.path.dirname(a.exe))
    sampler.pid = proc.pid
    print(f"client pid {proc.pid}: {os.path.basename(a.exe)} "
          f"{' '.join(accounts.redact(args))}")

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
            elif kind == "play":
                delivered = _play(tails, proc, outdir)
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

        if a.keep_open:
            hold_open(proc, a.hold, tails, outdir,
                      quiet=is_labelling(a))
    finally:
        # ALWAYS close the client, --keep-open included. The hold above is the
        # whole of what keep-open buys; once it ends the stack is about to be
        # stopped, and a client with no servers is not a running session, it is
        # a zombie sitting on Code=007. Worse, it keeps an exclusive handle on
        # Gw.log, so the NEXT run dies with PermissionError before it can even
        # launch -- which is exactly what happened once this hold existed.
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
                    help="hold the client AND the stack up after the verdict, "
                         "then shut both down together. Anything that happens "
                         "AFTER the map verdict -- a probe, a fight, a revive "
                         "-- needs this: the verdict is read at the spawn "
                         "rung, and a probe's first step lands seconds later. "
                         "Without --hold it holds until you close the client.")
    ap.add_argument("--account", default=None,
                    help="account label from vault/keys/accounts.json. "
                         "Omit for a loopback run: a synthetic credential is "
                         "used and no real account is involved.")
    ap.add_argument("--exe", default=None,
                    help="patched client exe; default: newest under vault/run")
    ap.add_argument("--actions", default=None,
                    help="override the input script; default depends on --until "
                         f"(login: {ACTIONS['login']!r}, map: {ACTIONS['map']!r})")
    ap.add_argument("--game-host", default="127.0.0.3",
                    help="Loopback alias the gamesrv binds and the handoff "
                         "advertises. 127/8 only. OBSERVED (handshake PLAN "
                         "§10): the client dials this host at hardcoded 6112, "
                         "so it must differ from --auth-host for the game "
                         "channel to reach the gamesrv at all.")
    ap.add_argument("--game-port", type=int, default=6112,
                    help="Port the handoff advertises AND the gamesrv listens "
                         "on. OBSERVED (handshake PLAN §10): the client never "
                         "dials it -- it dials --game-host at hardcoded 6112, "
                         "so any other value leaves the gamesrv unreachable. "
                         "This flag ran the probe that established that.")
    ap.add_argument("--auth-host", default="127.0.0.1",
                    help="Loopback address for the authsrv listener and the "
                         "client's -authsrv flag. 127/8 only. A second alias "
                         "(127.0.0.2) ran the probe that showed -authsrv plays "
                         "no part in the game dial (handshake PLAN §10).")
    ap.add_argument("--hold", type=float, default=0.0, metavar="SECONDS",
                    help="With --keep-open, stop holding after SECONDS instead "
                         "of waiting for the client to exit. What a probe needs "
                         "is its own step delays plus slack; --list-probes "
                         "prints them.")
    ap.add_argument("--tape-chain", metavar="CAPTURE_DIR", default=None,
                    help="R1.5 chaining (PLAN §8.0 item 0b): play a whole recorded "
                         "session, hop by hop. Discovers the chain from the capture "
                         "-- each tape's 0x01A5 handoff must match the next "
                         "connection's own VERSION or it is REFUSED, never ordered "
                         "by timestamp -- then starts one gamesrv per hop on its own "
                         "127.x alias, each repointing its handoff at the next. The "
                         "last hop is truncated. --game-args still reaches every hop.")
    ap.add_argument("--game-args", default="",
                    help="Extra authsrv flags for the GAMESRV only, space "
                         "separated -- e.g. --game-args '--probe attack_anim' "
                         "or '--map 146 --explorable'. The instance loads on "
                         "the game channel, so anything about the world lives "
                         "there; the authsrv gets none of it. Without this the "
                         "one-command loop could not run a probe at all.")
    a = ap.parse_args()

    if not dc.is_loopback(a.auth_host):
        raise SystemExit(f"--auth-host {a.auth_host!r} is not a 127/8 loopback "
                         f"address. The client must stay unable to reach ArenaNet.")
    if not dc.is_loopback(a.game_host):
        raise SystemExit(f"--game-host {a.game_host!r} is not a 127/8 loopback "
                         f"address. The client must stay unable to reach ArenaNet.")
    if a.game_host == a.auth_host and a.game_port == 6112:
        raise SystemExit(
            f"--game-host {a.game_host} is the auth host: the gamesrv would "
            f"try to bind the authsrv's own endpoint {a.auth_host}:6112. "
            f"Give the game channel an alias of its own (default 127.0.0.3).")

    game_args, hops, order, hosts = split_args(a.game_args), (), (), ()
    if a.tape_chain:
        game_args, hops, order, hosts = chain_specs(
            a.tape_chain, split_args(a.game_args), a.game_host)
        # A CHAIN IMPLIES --keep-open, and this is not a convenience.
        #
        # OBSERVED 2026-08-10, first run: the harness ticked all eight checkpoints at
        # t+4.9s, printed "RUN VERDICT: PASS (target: map)" and tore the stack down
        # 1.7 SECONDS into a 396-second chain. The gamesrv then reported
        # "TAPE ENDED at event 59/1209" with a ConnectionResetError and helpfully
        # listed the messages "in flight" for a client assert that never happened --
        # the reset WAS the teardown. Every visible signal said crash-on-map-load and
        # the run had simply been declared finished.
        #
        # That is the worst shape a defect can take here: a green verdict for work
        # that did not happen. The verdict answers "did the client reach the map",
        # which under a tape is true within five seconds and says nothing about the
        # six minutes that are the actual experiment. So the hold is derived from the
        # tape itself rather than asked of the operator.
        if not a.keep_open:
            a.keep_open = True
        if not a.hold:
            a.hold, total = chain_hold(a.tape_chain, order)
            print(f"tape chain: holding {a.hold:.0f}s "
                  f"({total:.0f}s of tape + dial gaps + slack). "
                  f"Override with --hold.")
        print(f"tape chain: {len(order)} hop(s) from {a.tape_chain}")
        for i, (conn, host) in enumerate(zip(order, hosts), 1):
            nxt = f"-> {hosts[i]}" if i < len(hosts) else "(last: truncated)"
            print(f"  {i}. {host}:{a.game_port}  {conn.split('->')[0]}  {nxt}")
        print(f"  the operator does NOTHING for the whole chain -- a tape cannot "
              f"show control, and each hop's avatar stops moving well before its "
              f"tape ends. Watch each 'tape complete: N/N' line instead.")

    specs = server_specs(game_port=a.game_port, auth_host=a.auth_host,
                         game_host=a.game_host,
                         game_args=game_args, hops=hops)
    preflight(specs, replace=a.replace)

    stamp = time.strftime("%Y%m%dT%H%M%S")
    outdir = vault_path("captures", "harness", stamp)
    os.makedirs(outdir, exist_ok=True)

    # --labelrun prompts a HUMAN through the gamesrv's stdout, so that stdout has to
    # reach this terminal. Detected from the flags rather than added as a second flag
    # here: the operator already says --labelrun once, and a run where they said it and
    # saw nothing is worse than useless -- it burns a client session and produces a
    # capture whose steps nobody performed.
    labelling = is_labelling(a)
    # Under a chain the operator's only truthful progress signal is each hop's own
    # "tape complete: N/N" line, and hops 2..N are different processes -- echoing only
    # "gamesrv" would show the first hop and then go silent for six minutes while the
    # run was working perfectly. Same failure as the labelled run's on 2026-08-10,
    # where the script driving the human was invisible.
    echoing = {s[0] for s in specs if s[0].startswith("gamesrv")} if a.tape_chain \
        else ({"gamesrv"} if labelling else False)
    stack = Stack(specs, logdir=outdir, echo=True if a.serve else echoing)
    if labelling:
        print("--labelrun: the gamesrv's prompts will appear IN THIS WINDOW.\n"
              "  Put this window beside the game. Read it by glancing -- clicking\n"
              "  here takes focus off the game and your next action goes nowhere.")
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
