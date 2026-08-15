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

    AN UNBALANCED QUOTE IS REFUSED WITH ITS CAUSE NAMED, not left to shlex's
    bare ValueError. PowerShell 5.1 rewrites a trailing `""` inside a
    single-quoted argument into ONE double quote -- measured 2026-08-12:
    `--game-args '... --skills ""'` reached Python as `... --skills "` -- and
    the resulting traceback pointed at this module rather than at the shell.
    Same rule as parse_walk: a typo in an argument must be found before the
    stack starts, and found with a message that says what to type instead.
    """
    out = []
    try:
        toks = shlex.split(text or "", posix=False)
    except ValueError as ex:
        raise SystemExit(
            f"--game-args {text!r}: {ex}. An unbalanced quote usually means "
            f"PowerShell rewrote a nested \"\" -- it collapses a trailing "
            f'`""` inside single quotes into one `"`. For an empty skillbar '
            f"use --skills 0 (a bar of zeroes) instead of --skills \"\".")
    for tok in toks:
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


def is_probing(a):
    """Is --probe among the gamesrv flags?

    Same shape as is_labelling and the same failure when missed: a probe
    prompts a HUMAN through the gamesrv's stdout -- probes.py prints the
    question, the prediction and every step's watch line there, and the watch
    lines are the experiment ("NOW open the skills menu"). Until 2026-08-12
    only --labelrun earned the echo, so a --probe run's prompts went to
    gamesrv.log alone and the operator sat at a silent terminal: a client
    session burned, and a capture whose steps nobody performed -- the exact
    2026-08-10 labelrun failure, on the other flag that prompts.
    """
    return "--probe" in split_args(getattr(a, "game_args", ""))


def prompts_operator(a):
    """Does this run drive a human through the gamesrv's stdout?

    One predicate, two consumers, like is_labelling: the echo decision in
    main() and the hold's progress-line silencing in run_client(). Both
    matter -- an unechoed prompt is invisible, and a "holding 8s" line
    interleaved with the prompts is how one gets misread by glancing.
    """
    return is_labelling(a) or is_probing(a)


def resolve_enemy(game_args, enemy=False):
    """Decide whether the gamesrv spawns the standing hostile. Default: NO.

    THE HARNESS DEFAULTS TO A WORLD WITH NO ENEMY IN IT, and that is a change of
    behaviour made 2026-08-12 after the hostile disrupted a second unrelated
    test. What it disrupted the second time was FINDINGS 40's movement session:
    the walk plan asked for 19 s of held keys, `W:6` and `D:4` completed, the
    character was killed (`player hit by skill 253: 0/100`, 7 damage events --
    and it is the ONLY one of that run's four sessions with any damage at all),
    the client lost the foreground, and `hold_key` cut `S:5` and `A:4` to 1.50 s
    each. The run's archive result survived because it rested on a control that
    fired regardless; the movement half simply did not happen.

    IT IS NOT "PROGRAMMED TO ATTACK", and the difference decides the fix. The
    chase gate at `authsrv.py:1853` is a real distance test against
    `AGGRO_RANGE = 1200.0`. What makes it unconditional is
    `content/world.toml [spawn.test_enemy]`: `offset_x = 300.0` from the
    PLAYER'S ARRIVAL POINT, `enabled = true`. 300 is four times inside the
    aggro radius, in every map, on every session -- so the behaviour is
    indistinguishable from a hard-coded attack while the mechanism is not.
    Moving the offset would have been the other fix and is worse: it would leave
    a hostile wandering into range on a long run, which is the same surprise
    later.

    Nothing about `authsrv.py` or `content/world.toml` changes. `authsrv.py`
    standalone still spawns it, and the combat arc gets it back with `--enemy`.

    Returns the gamesrv arg list. Explicit beats implicit and a contradiction is
    refused rather than silently resolved.
    """
    args = list(game_args)
    if "--no-enemy" in args:
        if enemy:
            raise SystemExit(
                "--enemy and --game-args '--no-enemy' contradict each other. "
                "Say it once.")
        return args                     # already explicit; do not duplicate it
    if enemy:
        return args                     # opt in: leave the world as world.toml has it
    return args + ["--no-enemy"]


def warn_probe_without_enemy(game_args, enemy=False):
    """A probe in a world with no hostile is the silent no-op this rule risks.

    Defaulting the enemy off makes every combat probe a run that quietly
    measures nothing, which is the exact failure this repository keeps paying
    for. So say it, loudly, at the top of the run rather than in the report.
    Returns the message (for a test to assert on) or None.
    """
    if enemy or "--probe" not in list(game_args):
        return None
    return ("WARNING: a --probe is running in a world with NO HOSTILE. The "
            "harness now defaults to --no-enemy; pass --enemy if this probe "
            "is about combat, or this run measures an empty world.")


def spawn_profession_args(game_args):
    """['--spawn-profession', 'N'] if game_args carries it, else [].

    The roster and the avatar must agree about who you are. Everything else in
    --game-args is a GAME-channel experiment and must NOT reach the authsrv --
    handing it the whole list would arm a second, idle copy of the same probe,
    which is the asymmetry `server_specs` documents at length.
    """
    args = list(game_args)
    for i, tok in enumerate(args):
        if tok == "--spawn-profession" and i + 1 < len(args):
            return ["--spawn-profession", args[i + 1]]
        if tok.startswith("--spawn-profession="):
            return [tok]
    return []


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
               "--game-host", game_host, "--game-port", str(game_port)]
         # --spawn-profession is the ONE game flag the authsrv also needs, and
         # it is forwarded rather than left to --game-args. The character-select
         # ROSTER is served on the auth channel, from the character blob, while
         # the in-world avatar is served on the game channel -- so with the flag
         # reaching only the gamesrv the roster read "Warrior" for a character
         # that was profession 8 everywhere else (OBSERVED 2026-08-13, harness
         # 20260813T111856). Two answers to one question, which is exactly the
         # split `appearance_for` exists to prevent one level down.
         + spawn_profession_args(game_args)),
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


def chain_specs(capture_dir, game_args=(), first="127.0.0.3", start_at=None):
    """(game_args_for_hop1, hops, order, hosts) for a whole recorded chain.

    Each hop is armed with its own tape and told to repoint its handoff at the NEXT
    hop's alias; the last hop is truncated instead, because there is nowhere left to
    send the client and an un-rewritten handoff would dial ArenaNet.
    """
    sys.path.insert(0, os.path.join(TOOLKIT, "authsrv"))
    import tape as tapemod
    order = tapemod.chain(capture_dir)
    if start_at:
        # Start the chain partway in. This exists for ONE experiment and it is worth
        # naming: hop 1 -> hop 2 has worked on every run and hop 2 -> hop 3 has failed on
        # every run, and two explanations fit equally well -- "only the FIRST transfer of
        # a session ever dials" or "that particular transition is broken". Starting the
        # chain at hop 2 makes the failing transition the FIRST one, which tells the two
        # apart in a single short run instead of by argument.
        match = [c for c in order if c.startswith(start_at) or start_at in c]
        if len(match) != 1:
            raise SystemExit(
                f"--tape-chain-from {start_at!r} matches {len(match)} of "
                f"{len(order)} connections: {[c.split('->')[0] for c in order]}")
        order = order[order.index(match[0]):]
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
        """Relay one server's stdout to its log and, optionally, to our console.

        THIS THREAD MAY NEVER DIE WHILE THE SERVER LIVES, and the reason is worse than
        a lost log line. It is the only reader of that pipe: when it stops reading, the
        pipe buffer fills, and the next `print(..., flush=True)` ANYWHERE in the server
        blocks forever. The server does not crash and nothing says so.

        MEASURED 2026-08-13, on the first run of the screenshot-labelling loop. One
        server line carried U+FFFD -- our own `string16` decoder's replacement
        character, which is what GW's encoded names produce when a code unit lands in
        the UTF-16 surrogate range -- and this print raised UnicodeEncodeError against
        a cp1252 console. The pump thread died, the gamesrv wedged on its next print,
        and the probe never sent a single opcode. The run still reported **RUN VERDICT:
        PASS**, because the one thing that kept working was the 20 Hz world tick: it
        passes `quiet=True` and is the only send in the server that does NOT print. So
        the capture filled with 649 plausible events, `gamesrv.log` stopped mid-startup
        at 949 bytes, and three opcodes were recorded as run when nothing was sent.

        The lesson was already written down in `toolkit/checks.py` -- "a test
        instrument that dies on the data it is reading is not an instrument", after
        `test_textrec.py` died the same way on cp1252 in 2026-08-06 -- and every test
        prints through its `_say` for exactly this. The harness never got the same
        treatment, and it is the one place where the failure blocks a SERVER rather
        than ending a script.

        `errors="replace"` on our OWN stdout is the fix rather than reconfiguring the
        console encoding: the log file is already UTF-8 and keeps the real character,
        and only the console -- whose encoding we do not choose -- degrades. The
        `except` beneath it is not belt-and-braces for the same fault; it is for every
        OTHER way a write can fail (a closed pipe when the terminal goes away), because
        the rule is that NOTHING stops this loop reading.
        """
        for line in proc.stdout:
            logf.write(line)
            logf.flush()
            if self._echoes(name):
                # No [name] prefix when only one server is echoed: the prompts are
                # formatted banners meant to be read at a glance, and a prefix on
                # every line of one wrecks the alignment.
                prefix = "" if self.echo is not True else f"[{name}] "
                text = f"{prefix}{line}"
                try:
                    enc = getattr(sys.stdout, "encoding", None) or "utf-8"
                    sys.stdout.write(text.encode(enc, "replace").decode(enc, "replace"))
                    sys.stdout.flush()
                except Exception:
                    pass                # never stop reading the pipe: see above
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


def _play(tails, proc, outdir, warn=3.0):
    """Wait for login, then click the Play button until the client enters the world.

    Event-driven: it starts once login completes (character select is up, -character
    already selected) and STOPS the instant the client requests its game instance, so it
    never clicks into the map. dc.click raises the client foreground first.

    The countdown fires AFTER login completes rather than at launch, because that
    is when the clicking actually starts -- a warning at launch would expire
    during the load screen and tell the operator nothing about the moment that
    matters.
    """
    login = by_any(by(kind="login_ok"), by(kind="login_rejected"))
    ev, idx = tails["auth"].wait_for(login, timeout=90)
    if not ev:
        print("  play: login never completed", flush=True)
        return False
    dc.warn_hands_off(warn)
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


# Keyboard movement, and why it is its own phase rather than another --actions
# entry. Actions run BEFORE the verdict, on a fixed delay from launch; a walk has
# to start once the character is actually standing in the map, which is what the
# spawn checkpoint establishes and what no delay can promise.
#
# WHY KEYBOARD AND NOT A CLICK. Both move the character and they are not
# interchangeable as instruments. A click sends GAME_CMSG 0x003E and the client
# then waits to be granted a destination -- so what it does next is a fact about
# OUR server's clip. A held key sends 0x003D, our server answers with a
# DIRECTION and nothing else, and the client walks itself until it hits
# something (authsrv.py, GAME_CMSG_TURN_TO_DIRECTION: "there is nothing to clip
# -- we are not naming a point"). The server's own integrator broadcasts nothing
# at all. So where a keyboard walk stops is the client's own collision, measured
# through the position the client reports back four times a second.
def parse_walk(text):
    """A plan of ordered steps. Movement and CAMERA in one script, because order matters.

        W:6         hold the W key for 6 seconds
        zoom:-14    turn the mouse wheel 14 notches; negative pulls the camera OUT
        pitch:300   right-drag 300 px; positive raises the camera's angle
        wait:3      do nothing for 3 seconds

    -> [('key', 'W', 6.0), ('zoom', '', -14.0), ...]

    One plan rather than a --walk and a separate --camera: reproducing
    FINDINGS 25.5's fault means zooming out, THEN pitching up, THEN backing into
    a corner, and two flags cannot express that sequence.
    """
    steps = []
    for spec in str(text).split():
        head, _, arg = spec.partition(":")
        head = head.lower()
        if not arg:
            raise SystemExit(f"walk step wants an argument: {spec!r}")
        try:
            value = float(arg)
        except ValueError:
            raise SystemExit(f"walk step {spec!r}: {arg!r} is not a number")
        if head in ("zoom", "pitch"):
            if value == 0:
                raise SystemExit(f"walk step {spec!r} moves the camera nowhere")
            steps.append((head, "", value))
        elif head == "wait":
            if value <= 0:
                raise SystemExit(f"walk step {spec!r} waits {value}s")
            steps.append(("wait", "", value))
        elif len(head) == 1:
            if value <= 0:
                raise SystemExit(f"walk step {spec!r} holds for {value}s")
            steps.append(("key", head.upper(), value))
        else:
            raise SystemExit(f"walk step {spec!r}: {head!r} is not a key, "
                             f"zoom, pitch or wait")
    return steps


def walk_legs(proc, legs, outdir, warn=3.0, settle=1.5, shot_every=0.0):
    """Hold each movement key in turn, and record when each leg ran.

    The wall clock is the join between this and the capture: every recorded
    event carries one, so a leg's window selects the position reports the client
    sent while that key was down. `held` is what actually happened rather than
    what was asked for -- dc.hold_key cuts a leg short if the client loses the
    foreground, and a short leg that is read as a full one turns "the character
    stopped" into a measurement of the operator's alt-tab.
    """
    dc.warn_hands_off(warn)
    # A CAMERA THAT RUNS THROUGH THE STEPS, not only between them. FINDINGS
    # 25.5's fault appeared and finished INSIDE one leg -- models stopped
    # drawing five seconds before the terrain did -- so a screenshot per leg
    # boundary cannot resolve it and could miss it entirely. shot_if_foreground
    # only READS the foreground, it never raises a window, so this cannot steal
    # focus from the input the plan is delivering.
    stop_shots = threading.Event()
    shot_n = [0]

    def shoot():
        while not stop_shots.wait(shot_every):
            hwnd, _ = dc.find_window(proc.pid)
            if hwnd:
                shot_n[0] += 1
                shot_if_foreground(hwnd, proc.pid,
                                   os.path.join(outdir, f"w{shot_n[0]:03d}.png"))
    if shot_every > 0:
        threading.Thread(target=shoot, daemon=True).start()
        print(f"  walk: a screenshot every {shot_every:g}s for the whole plan",
              flush=True)

    out = []
    for i, (kind, key, value) in enumerate(legs):
        # THE CLIENT MAY HAVE DIED SINCE THE LAST STEP, and until 2026-08-11
        # nothing here noticed. OBSERVED: a portal chunk with a bad index
        # crashed the client 17 s into a run -- `Assertion: index < m_count,
        # Array.h(587)` -- and the harness printed RUN VERDICT: PASS, because
        # judge() runs BEFORE the walk and had already passed on the spawn.
        # Every later step then failed to find a window and was logged as
        # "NO WINDOW", which reads like a focus problem rather than a corpse.
        if proc.poll() is not None:
            out.append({"kind": kind, "key": key, "asked": value, "did": 0.0,
                        "note": f"client exited (code {proc.returncode}) "
                                f"before this step"})
            print(f"\n  *** THE CLIENT IS GONE (exit code {proc.returncode}). "
                  f"It died before step {i + 1} of {len(legs)}.\n"
                  f"  *** A Guild Wars assert leaves a crash dialog and writes "
                  f"the reason to the\n"
                  f"  *** client's own error log; the run verdict above was "
                  f"read before the walk\n"
                  f"  *** and says nothing about it. Stopping the plan.",
                  flush=True)
            break
        hwnd, _ = dc.wait_window(proc.pid, timeout=5)
        label = f"{key or kind}:{value:g}"
        if not hwnd:
            out.append({"kind": kind, "key": key, "asked": value, "did": 0.0,
                        "note": "no window"})
            print(f"  walk {label}: NO WINDOW", flush=True)
            continue
        started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        if kind == "key":
            did = dc.hold_key(hwnd, proc.pid, ord(key), value)
        elif kind == "zoom":
            did = value if dc.scroll(hwnd, proc.pid, value) else 0.0
        elif kind == "pitch":
            # dy is NEGATED: dragging the mouse DOWN raises the camera's angle,
            # so "pitch:300" reads as "raise it" rather than as a screen delta.
            did = value if dc.orbit(hwnd, proc.pid, 0, -value) else 0.0
        elif kind == "wait":
            time.sleep(value)
            did = value
        else:
            raise SystemExit(f"unknown walk step kind {kind!r}")
        ended = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        # Let the client come to rest and send its stop before the next step
        # starts, so two steps cannot share one deceleration.
        time.sleep(settle)
        settled = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        out.append({"kind": kind, "key": key, "asked": value,
                    "did": round(did, 2), "started": started, "ended": ended,
                    "settled": settled})
        print(f"  walk {label}: {did:g} of {value:g} "
              f"({started} -> {ended})", flush=True)
        shot_if_foreground(hwnd, proc.pid,
                           os.path.join(outdir, f"walk{i + 1}-{kind}{key}.png"))
    stop_shots.set()
    return out


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
    # Same passthrough and the SAME refusal as drive_client, deliberately not
    # imported-and-trusted: this file already keeps its own copy of the launch
    # gate three lines below, for the reason stated there.
    for extra in (getattr(a, "client_arg", None) or []):
        if extra.split("=", 1)[0].lower() in dc.FORBIDDEN_CLIENT_ARGS:
            raise SystemExit(
                f"--client-arg {extra!r} is refused: it decides where the client "
                f"points, which is the cage's job. See FORBIDDEN_CLIENT_ARGS.")
        args.append(extra)
    if getattr(a, "client_arg", None):
        print(f"extra client flags: {' '.join(a.client_arg)}")
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
    sent, results, ok, undec, walked = [], [], False, [], []
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
                delivered = _play(tails, proc, outdir, warn=a.warn)
            elif kind == "key":
                # "key:1" presses skill slot 1. Added 2026-08-11 so the harness
                # can provoke a GAME_CMSG 0x0027 -- ArenaNet's attack-skill
                # message, which this server had no arm for until that day and
                # which nothing here could produce to check the fix with. The
                # loopback character is a Warrior, whose attack skills carry the
                # same s_skill type_code (14) as the Ranger's Power Shot that
                # revealed the opcode.
                ch = parts[2]
                if len(ch) != 1:
                    raise SystemExit(f"key action wants ONE character: {spec!r}")
                delivered = dc.press_key(hwnd, proc.pid, ord(ch.upper()))
            elif kind == "vk":
                # "vk:0x29:alt+force" -- a RAW virtual key under modifiers, for
                # codes no character maps to. Added for the s_netGraph toggle,
                # which wants key 0x29 with modifier 4 (studies/smsg). `force`
                # sends bScan=0 when the layout has no position for the key,
                # which is true of 0x29 on an ordinary keyboard; see press_vk.
                vk = int(parts[2], 0)
                raw = parts[3] if len(parts) > 3 and parts[3] else ""
                force = "force" in raw.split("+")
                mods = tuple(m for m in raw.split("+") if m and m != "force")
                bad = [m for m in mods if m not in dc.MOD_KEYS]
                if bad:
                    raise SystemExit(f"unknown modifier(s) {bad} in {spec!r} -- "
                                     f"want {sorted(dc.MOD_KEYS)} or 'force'")
                delivered = dc.press_vk(hwnd, proc.pid, vk, mods,
                                        allow_no_scan=force)
                if delivered is None:
                    print(f"  vk {vk:#04x} has NO SCAN CODE on this layout and "
                          f"'force' was not given -- not sent. That is a fact "
                          f"about the key, not a harness fault.", flush=True)
                    delivered = False
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

        # After the verdict, because a walk is only meaningful once the client
        # says the character is standing in the map -- and only if it is. Walking
        # a client that never spawned would fill the capture with nothing and
        # read as "the character could not move".
        if a.walk:
            if ok:
                walked = walk_legs(proc, parse_walk(a.walk), outdir, warn=a.warn,
                                   shot_every=a.shots)
                # A client that died mid-plan RETRACTS the verdict. It was read
                # before the walk, so it is true about the spawn and silent
                # about everything after -- and "PASS" is the wrong word for a
                # run whose client crashed 17 s in.
                if any("client exited" in str(w.get("note", "")) for w in walked):
                    ok = False
                    print("  RUN VERDICT RETRACTED: the spawn checkpoints passed, "
                          "then the client died during the walk.", flush=True)
            else:
                print("  walk: SKIPPED -- the run did not reach the map, so "
                      "there is nothing to walk", flush=True)

        if a.keep_open:
            hold_open(proc, a.hold, tails, outdir,
                      quiet=prompts_operator(a), shot_every=a.shots)
    finally:
        # READ THE CRASH DIALOG BEFORE ANYTHING CLOSES IT, ON EVERY PATH.
        # `capture_error_dialog` used to be reachable ONLY from hold_open(),
        # which line 1087 runs only under --keep-open -- so an ordinary
        # `--hold N` run captured nothing. MEASURED 2026-08-12: rung E10a's six
        # sessions crashed the client twice, and both asserts (`deps` at
        # TrnCreate:242 and `state->zones` at MapData:660) survived only because
        # the owner read them off the screen. The extraction itself was never
        # broken -- the same run under --keep-open wrote a crash-dialog.txt
        # holding both lines -- so this was a call site missing, which is the
        # cheapest kind of gap to have and the most expensive kind to discover.
        #
        # It goes FIRST because `close_client` destroys the dialog, and it is
        # quiet and short here: most runs end without one, and the --keep-open
        # path has already had its longer look.
        capture_error_dialog(outdir, wait=2.0, quiet=True)
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
        "exe": a.exe, "until": a.until, "actions": sent, "walk": walked,
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
    ap.add_argument("--warn", type=float, default=3.0, metavar="SECONDS",
                    help="Countdown printed before the harness sends its first "
                         "click, so a human at the machine can take their hands "
                         "off the keyboard and mouse. Competing input makes a run "
                         "fail for a reason unrelated to what was being tested, "
                         "and the transcript still looks like evidence. "
                         "0 for unattended runs.")
    ap.add_argument("--walk", metavar="LEGS",
                    help="After the spawn verdict, run an ordered plan of "
                         "movement and CAMERA steps: \"zoom:-14 pitch:300 S:8\" "
                         "pulls the camera out 14 notches, raises its angle, "
                         "then backs up for 8s. Steps are W:6 (hold a key), "
                         "zoom:N, pitch:N and wait:N. "
                         "Keyboard rather than a click on purpose -- the server "
                         "answers a held key with a DIRECTION and broadcasts no "
                         "position, so where the client stops is the client's "
                         "own collision and not our clip. The client reports "
                         "where it is four times a second, so the capture "
                         "carries the whole trace.")
    ap.add_argument("--shots", type=float, default=0.0, metavar="SECONDS",
                    help="With --keep-open, screenshot the client every SECONDS "
                         "during the hold. For faults only a human can provoke: "
                         "reaching for a screenshot key means letting go of the "
                         "input that produces them.")
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
    ap.add_argument("--tape-chain-from", metavar="CONNECTION", default=None,
                    help="Start a --tape-chain partway in, e.g. --tape-chain-from 62994. "
                         "The discriminating experiment for a transition that never "
                         "dials: make it the FIRST transfer of the session instead of "
                         "the second.")
    ap.add_argument("--enemy", action="store_true",
                    help="Spawn the standing hostile. OFF BY DEFAULT since "
                         "2026-08-12: content/world.toml puts it 300 units from "
                         "the player's arrival point and AGGRO_RANGE is 1200, so "
                         "it engages on every session in every map, and it had "
                         "wrecked two unrelated tests by then -- most recently "
                         "FINDINGS 40's movement session, where it killed the "
                         "character 10s in and the last two walk legs were cut "
                         "short. Combat work wants this flag; map, archive and "
                         "movement work does not. authsrv.py standalone is "
                         "unchanged and still spawns it.")
    ap.add_argument("--game-args", default="",
                    help="Extra authsrv flags for the GAMESRV only, space "
                         "separated -- e.g. --game-args '--probe attack_anim' "
                         "or '--map 146 --explorable'. The instance loads on "
                         "the game channel, so anything about the world lives "
                         "there; the authsrv gets none of it. Without this the "
                         "one-command loop could not run a probe at all.")
    ap.add_argument("--client-arg", action="append", metavar="FLAG",
                    help="Extra flag for the CLIENT, repeatable -- the other "
                         "side of --game-args, which reaches only the server. "
                         "Write it with an equals sign, `--client-arg=-perf`, "
                         "or argparse eats the leading dash as an option of its "
                         "own. -perf draws triangles, fps and transfer rate in "
                         "the top-right corner. Flags that decide where the "
                         "client points are REFUSED.")
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
    warning = warn_probe_without_enemy(game_args, a.enemy)
    if warning:
        print(warning)
    game_args = resolve_enemy(game_args, a.enemy)
    if a.tape_chain:
        game_args, hops, order, hosts = chain_specs(
            a.tape_chain, split_args(a.game_args), a.game_host, a.tape_chain_from)
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

    # Before the stack starts and long before a client launches: a typo in
    # --walk would otherwise be found after the map has loaded, which costs the
    # whole run and a client session.
    if a.walk:
        legs = parse_walk(a.walk)
        held = sum(v for k, _, v in legs if k in ("key", "wait"))
        cam = sum(1 for k, _, _ in legs if k in ("zoom", "pitch"))
        print(f"walk plan: {len(legs)} step(s), {held:.1f}s of keys and waits, "
              f"{cam} camera move(s)")

    specs = server_specs(game_port=a.game_port, auth_host=a.auth_host,
                         game_host=a.game_host,
                         game_args=game_args, hops=hops)
    preflight(specs, replace=a.replace)

    stamp = time.strftime("%Y%m%dT%H%M%S")
    outdir = vault_path("captures", "harness", stamp)
    os.makedirs(outdir, exist_ok=True)

    # --labelrun and --probe both prompt a HUMAN through the gamesrv's stdout, so that
    # stdout has to reach this terminal. Detected from the flags rather than added as a
    # second flag here: the operator already says --probe once, and a run where they
    # said it and saw nothing is worse than useless -- it burns a client session and
    # produces a capture whose steps nobody performed.
    labelling = is_labelling(a)
    prompting = prompts_operator(a)
    # Under a chain the operator's only truthful progress signal is each hop's own
    # "tape complete: N/N" line, and hops 2..N are different processes -- echoing only
    # "gamesrv" would show the first hop and then go silent for six minutes while the
    # run was working perfectly. Same failure as the labelled run's on 2026-08-10,
    # where the script driving the human was invisible.
    echoing = {s[0] for s in specs if s[0].startswith("gamesrv")} if a.tape_chain \
        else ({"gamesrv"} if prompting else False)
    stack = Stack(specs, logdir=outdir, echo=True if a.serve else echoing)
    if prompting:
        which = "--labelrun" if labelling else "--probe"
        print(f"{which}: the gamesrv's prompts will appear IN THIS WINDOW.\n"
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
        if not a.exe:
            # Selected by BUILD, not by mtime -- see dc.select_run_exe. A
            # newest-wins pick sent this at the 38833 snapshot the day it
            # landed, whose Gw.dat never had the maps 146/148 replacement.
            a.exe, why = dc.select_run_exe()
            if not a.exe:
                raise SystemExit(why)
            print(f"client: {why}")
        return run_client(a, outdir)
    except KeyboardInterrupt:
        print("\nstopping")
        return 130
    finally:
        stack.stop()


if __name__ == "__main__":
    sys.exit(main())
