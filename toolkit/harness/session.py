"""One command instead of three terminals: bring up the whole Rurik stack,
prove each server is actually listening, drive the patched client, and judge
the run by the client's own messages.

    python toolkit/harness/session.py                  # stack + client, judge to "in a map"
    python toolkit/harness/session.py --until login    # stop after the login verdict
    python toolkit/harness/session.py --serve          # just the stack; Ctrl-C stops it
    python toolkit/harness/session.py --replace        # stop THIS tree's stale listeners first

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

AND "PYTHON" IS NOT ENOUGH. One session per worktree (CLAUDE.md) means a
parallel session's LIVE stack is also "a python on our ports", and on
2026-08-20 ~23:00 --replace killed exactly that: another worktree's webgate
(pid 18520) and authsrv (pid 8412), mid-run, started from a tree this session
had never seen. So --replace now reads the listener's command line and stops
it only when the script it names resolves into THIS session's tree -- compared
tree to tree, never by path prefix, because worktrees nest UNDER the main
checkout and a prefix test would call every one of them "ours". A listener it
cannot claim is refused with its tree printed, so the operator knows which
session to go coordinate with.

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
sys.path.insert(0, os.path.join(TOOLKIT, "mapdata"))
from tcptable import connections  # noqa: E402
from vaultpath import vault_path, vault_why  # noqa: E402
from livecapture import CaptureTail, by  # noqa: E402
import drive_client as dc  # noqa: E402
import control  # noqa: E402
import cage  # noqa: E402
import accounts  # noqa: E402
import datcheck  # noqa: E402  -- toolkit/mapdata, the archive half of the gate

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
# argtypes are not optional: a HANDLE truncated to a 32-bit int silently
# corrupts every call that receives it back. Same scar as drive_client.
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.LocalFree.argtypes = [wintypes.HLOCAL]
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

# Reading a listener's COMMAND LINE, for the --replace ownership test below.
# NtQueryInformationProcess(ProcessCommandLineInformation) answers for any
# same-user process since Win 8.1 and needs only the LIMITED right image_name
# already opens with -- no PEB walk, no third-party dependency, the same pure
# ctypes budget keytap.py runs its cross-process reads on. The split is
# CommandLineToArgvW rather than shlex because the operand is ANOTHER
# process's argv: it gets the OS's own quoting rules, not ours.
ntdll = ctypes.WinDLL("ntdll")
ntdll.NtQueryInformationProcess.argtypes = [
    wintypes.HANDLE, wintypes.ULONG, wintypes.LPVOID, wintypes.ULONG,
    ctypes.POINTER(wintypes.ULONG)]
ntdll.NtQueryInformationProcess.restype = ctypes.c_uint32       # NTSTATUS
shell32 = ctypes.WinDLL("shell32", use_last_error=True)
shell32.CommandLineToArgvW.argtypes = [wintypes.LPCWSTR,
                                       ctypes.POINTER(ctypes.c_int)]
shell32.CommandLineToArgvW.restype = ctypes.POINTER(wintypes.LPWSTR)
PROCESS_COMMAND_LINE_INFORMATION = 60
STATUS_INFO_LENGTH_MISMATCH = 0xC0000004


class UNICODE_STRING(ctypes.Structure):
    # Buffer as c_void_p, not c_wchar_p: Length is authoritative and excludes
    # the terminator, so the read below is wstring_at(ptr, Length // 2) rather
    # than trusting a NUL that the contract does not promise.
    _fields_ = [("Length", ctypes.c_ushort),
                ("MaximumLength", ctypes.c_ushort),
                ("Buffer", ctypes.c_void_p)]


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


def hold_implies_keep_open(a):
    """--hold N means hold for N seconds, with or without --keep-open.

    run_client() gates the hold on a.keep_open ALONE, so `--hold 60` on its
    own used to be silently inert: the session tore down at the verdict, and
    the healthy client's orderly exit -- game 0x0008, auth 0x0009, status
    Offline, then the RST -- reads exactly like a client-side death.
    OBSERVED 2026-08-16: fourteen launches misdiagnosed that way before the
    missing flag was noticed (studies/isle/FINDINGS.md "Rung 4").

    --hold has no meaning other than bounding the hold, so it implies the
    hold rather than being refused -- the same resolution the tape chain
    made, which sets a.keep_open itself for the same reason. Mutates and
    returns the namespace, like that path does.
    """
    if a.hold and not a.keep_open:
        a.keep_open = True
    return a


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


def persist_args(game_args):
    """['--persist'] if game_args carries it, else [].

    The SECOND game flag the authsrv also needs, same reasoning as
    --spawn-profession above: the character store's roster and settings
    write-back live on the AUTH channel while the sheet loads on the GAME
    channel, so one instance armed without the other is a character that
    saves but never loads back (or loads but never saves). Unlike a --probe,
    arming both copies is the point, not a hazard -- they share one store
    directory and the auth side is the only writer.
    """
    return ["--persist"] if "--persist" in list(game_args) else []


# A run that cannot be pinned to one map must not narrow the pre-flight. Tape
# playback picks its own map from the recording's 0x0195, and a tape CHAIN hops
# between maps by design -- so for these, which map loads is not ours to say.
_TRAVELLING_FLAGS = ("--tape", "--tape-chain", "--tape-connection",
                     "--tape-chain-from", "--labelrun")


def served_maps(game_args):
    """{map_id} the run will load, or None when that cannot be known.

    Feeds `contentids.preflight(served=...)`, whose whole safety rests on the
    None case: None means "check every content row", so every path through here
    that is not certain returns None and loses no protection.

    Returns None -- deliberately, not an empty set -- when:

      * no `--map` is given, because the gamesrv then picks its own default and
        this function would be guessing;
      * any tape flag is present, because the recording decides the map and a
        chain deliberately moves between them. Narrowing there would clear a
        row the run is about to load, which is worse than the false positive
        this function exists to remove;
      * `--map` is present but its value is not an integer, which is a typo the
        gamesrv will reject anyway -- and a guard must not be disarmed by a
        malformed argument.

    `--file-id` is NOT excluded, and the direction is deliberate: it re-points
    the served slot at other geometry, so the content row's binding is bypassed
    rather than relied on. Keeping the row in scope only ever refuses MORE.
    """
    args = list(game_args)
    if any(tok.split("=", 1)[0] in _TRAVELLING_FLAGS for tok in args):
        return None
    raw = None
    for i, tok in enumerate(args):
        if tok == "--map" and i + 1 < len(args):
            raw = args[i + 1]
        elif tok.startswith("--map="):
            raw = tok.split("=", 1)[1]
    if raw is None:
        return None
    try:
        return {int(raw, 0)}
    except (TypeError, ValueError):
        return None


def server_specs(portal_port=6601, auth_port=6112, game_port=6112,
                 capture_root=None, auth_host="127.0.0.1",
                 game_host="127.0.0.3", game_args=(), hops=(),
                 portal_host="127.0.0.1"):
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
    client as -authsrv too). portal_host does the same for the webgate and
    DEFAULTS TO 127.0.0.1 so that separability is unchanged: the -portal,
    -authsrv and handoff hosts still have to be separable for a probe to say
    which of them the client's game dial follows.

    It exists because 6601 was the ONE port with no override, so a second
    session holding it blocked a run that had already moved its authsrv and
    gamesrv aside (2026-08-15: another worktree's --keep-open run on map 449
    held 127.0.0.1:6601 and there was no flag to route around it). Moving it
    costs nothing: the client takes -portal as a HOST, exactly as -authsrv.

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
        ("webgate", portal_host, portal_port,
         py + [os.path.join(TOOLKIT, "portal", "webgate.py"),
               "--port", str(portal_port), "--bind", portal_host,
               "--vault", cap("portal")]),
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
         + spawn_profession_args(game_args)
         + persist_args(game_args)),
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


def cmdline(pid):
    """The process's full command line, or None when it cannot be read.

    None is an ANSWER, not an error state to hide: the caller refuses to stop
    what it cannot identify, so a pid that exited between the table read and
    this call, an access-denied handle and a truncated buffer all land on the
    same safe side.
    """
    h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return None
    try:
        need = wintypes.ULONG(0)
        st = ntdll.NtQueryInformationProcess(
            h, PROCESS_COMMAND_LINE_INFORMATION, None, 0, ctypes.byref(need))
        if st != STATUS_INFO_LENGTH_MISMATCH or not need.value:
            return None
        buf = ctypes.create_string_buffer(need.value)
        st = ntdll.NtQueryInformationProcess(
            h, PROCESS_COMMAND_LINE_INFORMATION, buf, need.value,
            ctypes.byref(need))
        if st != 0:
            return None
        us = UNICODE_STRING.from_buffer(buf)
        if not us.Buffer or not us.Length:
            return None
        return ctypes.wstring_at(us.Buffer, us.Length // 2)
    finally:
        kernel32.CloseHandle(h)


def argv_of(cmd):
    """Split a Windows command line exactly as the OS would. [] on failure."""
    if not cmd:
        return []
    argc = ctypes.c_int(0)
    p = shell32.CommandLineToArgvW(cmd, ctypes.byref(argc))
    if not p:
        return []
    try:
        return [p[i] for i in range(argc.value)]
    finally:
        kernel32.LocalFree(ctypes.cast(p, wintypes.HLOCAL))


def tree_of(path):
    """The git tree owning `path`: the NEAREST ancestor with a `.git` entry.

    Nearest, not outermost, and that distinction is load-bearing: worktrees
    live UNDER the main checkout (`.claude/worktrees/<name>`), so testing "is
    the path inside my root" by prefix would call every worktree's stack the
    main session's own -- the 2026-08-20 kill again, from a different angle.
    A worktree's `.git` is a FILE (gitdir pointer), the main checkout's a
    directory; os.path.exists answers for both. None when no ancestor
    qualifies.
    """
    d = os.path.abspath(path)
    while True:
        if os.path.exists(os.path.join(d, ".git")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def this_tree():
    """THIS session's tree: the one this session.py was loaded from, which is
    also the tree whose servers server_specs() builds argvs for. Matches
    `git rev-parse --show-toplevel` run beside this file, without shelling out
    -- the test proves that equivalence against git's own answer."""
    return tree_of(os.path.realpath(os.path.abspath(__file__)))


def replace_verdict(cmd, our_tree):
    """(may_stop, listener_tree, why): may --replace stop the python listener
    whose command line is `cmd`?

    The rule is OWNERSHIP, not species. "Is it python" was the whole test
    until 2026-08-20 ~23:00, when it matched a parallel session's live stack
    -- one session per worktree means two sessions' servers are identical by
    image name -- and --replace killed that session's webgate and authsrv
    mid-run. Now the script the command line names must resolve into OUR
    tree, tree compared to tree.

    Everything unprovable refuses: a command line that could not be read, no
    script token in it, a RELATIVE script path (a hand-run three-terminal
    server, started from a shell whose cwd this process cannot see). The
    direction is deliberate -- an over-refusal costs the operator one
    taskkill; the under-refusal cost a parallel session its live stack.
    """
    if not our_tree:
        return (False, None, "THIS tree has no .git ancestor, so ownership "
                             "cannot be proven for anything")
    if not cmd:
        return (False, None, "its command line could not be read")
    scripts = [t for t in argv_of(cmd) if t.lower().endswith((".py", ".pyw"))]
    if not scripts:
        return (False, None, "no python script in its command line")
    script = scripts[0]
    if not os.path.isabs(script):
        return (False, None,
                f"its script path {script!r} is relative -- started from a "
                f"shell whose cwd this pre-flight cannot see")
    their = tree_of(os.path.realpath(script))
    if their is None:
        return (False, None, f"{script} is outside any git tree")
    if os.path.normcase(their) != os.path.normcase(os.path.realpath(our_tree)):
        return (False, their, "it was started from a DIFFERENT tree")
    return (True, their, "")


def preflight(specs, replace=False):
    """Every endpoint free, or a loud exit naming exactly what is in the way.

    Host-aware on purpose: authsrv and gamesrv both use port 6112, at
    different loopback aliases. A port-only match would report each as
    squatting on the other's endpoint. The gamesrv alias (127.0.0.3 by
    default) and every chain hop are in `specs` and get the same check --
    main() hands this the WHOLE list, and the test pins that with a listener
    parked on the alias.

    --replace stops a listener only when THREE things hold: it is python, its
    command line could be read, and the script that command line names lives
    in THIS session's tree (replace_verdict). A refusal prints the other
    listener's tree, because the operator's next move is to coordinate with
    whoever is working THERE, and a pid alone does not say who that is.
    """
    ours = this_tree()
    for name, host, port, _ in specs:
        for row in listeners_on(port, host):
            img = image_name(row["pid"])
            base = os.path.basename(img).lower()
            is_python = base in ("python.exe", "pythonw.exe")
            cmd = cmdline(row["pid"]) if is_python else None
            may_stop, their_tree, why = (replace_verdict(cmd, ours)
                                         if is_python else (False, None, ""))
            if replace and may_stop:
                print(f"pre-flight: stopping stale {name} listener "
                      f"pid {row['pid']} on {row['local']} (this tree's own)")
                os.kill(row["pid"], 15)
                continue
            if not is_python:
                hint = ("not a python server -- REFUSING to touch it; "
                        "stop it yourself")
            elif may_stop:
                hint = ("this tree's own stale listener -- re-run with "
                        "--replace to stop it")
            else:
                hint = (
                    f"python, but NOT provably this tree's: {why}.\n"
                    + (f"  its tree:  {their_tree}\n" if their_tree else "")
                    + (f"  its argv:  {cmd}\n" if cmd else "")
                    + f"  this tree: {ours}\n"
                    f"  A parallel session's LIVE stack looks exactly like a "
                    f"stale one from here\n"
                    f"  (one was killed mid-run 2026-08-20), so --replace "
                    f"refuses it too. Coordinate\n"
                    f"  with that tree's session, or stop the pid yourself")
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
        # NORMALISE BEFORE AIMING. PLAY_FX/PLAY_FY are a position in ONE window
        # shape, and character select does not lay its buttons out by
        # proportion: at 716x1040 this same fraction is the DELETE button
        # (2026-08-18, another session had resized the client; see
        # drive_client.CLIENT_W). Resizing to the calibrated geometry is what
        # makes the fraction mean what it was measured to mean.
        ok, before, after = dc.normalize_window(hwnd)
        if before != after:
            print(f"  play: window {before} -> {after} "
                  f"(calibrated {dc.CLIENT_W}x{dc.CLIENT_H})", flush=True)
        if not ok:
            # FAIL CLOSED. An un-normalised window means we do not know what is
            # under the cursor, and the observed cost of guessing wrong is a
            # character-deletion dialog, not a wasted click.
            print(f"  play: REFUSING to click -- the window is {after} and the "
                  f"Play fraction is calibrated for {dc.CLIENT_W}x"
                  f"{dc.CLIENT_H}. At a different aspect this coordinate is a "
                  f"DIFFERENT BUTTON (it was Delete on 2026-08-18). Resize the "
                  f"client, or recalibrate PLAY_FX/PLAY_FY and say so here.",
                  flush=True)
            return False
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
        yaw:400     right-drag 400 px HORIZONTALLY; positive turns the view right
        left:2      hold a NAMED key (alt, ctrl, shift, space, left/right/up/down)
        alt:4       -- ALT held shows every nameplate; pair with --shots
        shot:1      take a screenshot NOW, on the plan's own clock
        wait:3      do nothing for 3 seconds
        click:0.411,0.609      left-click one window-relative point (a panel
                    button; dc.click checks focus first)
        attack:10   order a swing at agent 10 -- fires INSIDE the shot
                    window, which the action-script form cannot
        hover:0.044,0.054,38   park the cursor over a window-relative point
                    for 38s, clicking nothing -- a HUD tooltip is the only
                    readable surface for some state, and this is how a probe
                    run reads one unattended
        steer:W,300,3          hold W for 3 s WHILE right-dragging the view 300 px
                    (positive = right) in quarter-second slices -- the
                    operator's own regime, a body that keeps moving while its
                    heading changes, which no sequence of single steps can
                    produce (RUN-1zCW pair 1: every leg ends in a stop)

    -> [('key', 'W', 6.0), ('zoom', '', -14.0), ...]

    One plan rather than a --walk and a separate --camera: reproducing
    FINDINGS 25.5's fault means zooming out, THEN pitching up, THEN backing into
    a corner, and two flags cannot express that sequence.

    yaw/alt/left/shot landed 2026-08-17, and together they retire the "this
    harness cannot aim" caveat for everything except a world-anchored CLICK:
    zoom out, yaw toward a known offset, hold ALT, and the shot reads the
    scene's own labels. The interact: action remains the answer for clicking.
    """
    steps = []
    for spec in str(text).split():
        head, _, arg = spec.partition(":")
        head = head.lower()
        if not arg:
            raise SystemExit(f"walk step wants an argument: {spec!r}")
        if head == "attack":
            # attack:AGENT_ID -- order a swing at a hostile, mid-plan.
            #
            # IT IS A WALK VERB *AND* AN ACTION, and the reason is a trap this
            # repo has now paid for twice. Actions all fire BEFORE the walk and
            # the hold, and `--shots` drives its shooter thread across the walk
            # and the hold only -- so an attack ordered from the action script
            # can have its whole fight finish before a single frame is taken.
            # That is exactly what happened on 2026-08-20: the critical landed
            # at 20:11:39 and the first hold frame was stamped 20:13:58, 139
            # seconds later, with the numbers on screen the entire time nobody
            # was photographing. Anchoring frames by TIMESTAMP rather than by
            # filename is what caught it, which is the lesson already recorded
            # for a different arc.
            #
            # As a walk step it fires INSIDE the shot window, so a fight and
            # its frames overlap by construction rather than by luck.
            try:
                agent_id = int(arg, 0)
            except ValueError:
                raise SystemExit(f"walk step {spec!r}: attack wants an agent id")
            steps.append(("attack", str(agent_id), 0.0))
            continue
        if head == "steer":
            parts = arg.split(",")
            if len(parts) != 3:
                raise SystemExit(f"walk step {spec!r}: steer wants KEY,PX,SECONDS")
            k = parts[0]
            if k in dc.NAMED_KEYS:
                kname = k
            elif len(k) == 1:
                kname = k.upper()
            else:
                raise SystemExit(f"walk step {spec!r}: {k!r} is not a key")
            try:
                px, secs = float(parts[1]), float(parts[2])
            except ValueError:
                raise SystemExit(f"walk step {spec!r}: steer wants numbers")
            if px == 0:
                raise SystemExit(f"walk step {spec!r} turns the view nowhere")
            if secs <= 0:
                raise SystemExit(f"walk step {spec!r} holds for {secs}s")
            steps.append(("steer", f"{kname},{px:g}", secs))
            continue
        if head in ("hover", "click"):
            # hover:FX,FY,SECONDS -- park the cursor over a window-relative
            # point, no click. Three numbers because the point matters as much
            # as the duration, and a fixed HUD element's fractions are the
            # whole reason the verb is usable unattended.
            parts = arg.split(",")
            want = 3 if head == "hover" else 2
            if len(parts) != want:
                raise SystemExit(f"walk step {spec!r}: {head} wants "
                                 + ("FX,FY,SECONDS" if want == 3 else "FX,FY"))
            try:
                nums = [float(p) for p in parts]
            except ValueError:
                raise SystemExit(f"walk step {spec!r}: {head} wants numbers")
            fx, fy = nums[0], nums[1]
            secs = nums[2] if want == 3 else 1.0
            if not (0.0 < fx < 1.0 and 0.0 < fy < 1.0):
                raise SystemExit(f"walk step {spec!r}: {head} fractions must sit "
                                 f"inside the window, exclusive 0..1")
            if secs <= 0:
                raise SystemExit(f"walk step {spec!r} hovers for {secs}s")
            steps.append((head, f"{fx:g},{fy:g}", secs))
            continue
        try:
            value = float(arg)
        except ValueError:
            raise SystemExit(f"walk step {spec!r}: {arg!r} is not a number")
        if head in ("zoom", "pitch", "yaw"):
            if value == 0:
                raise SystemExit(f"walk step {spec!r} moves the camera nowhere")
            steps.append((head, "", value))
        elif head == "wait":
            if value <= 0:
                raise SystemExit(f"walk step {spec!r} waits {value}s")
            steps.append(("wait", "", value))
        elif head == "shot":
            steps.append(("shot", "", 1.0))
        elif head in dc.NAMED_KEYS:
            if value <= 0:
                raise SystemExit(f"walk step {spec!r} holds for {value}s")
            steps.append(("key", head, value))
        elif len(head) == 1:
            if value <= 0:
                raise SystemExit(f"walk step {spec!r} holds for {value}s")
            steps.append(("key", head.upper(), value))
        else:
            raise SystemExit(f"walk step {spec!r}: {head!r} is not a key, "
                             f"a named key ({', '.join(sorted(dc.NAMED_KEYS))}), "
                             f"zoom, pitch, yaw, shot, wait, hover, click or steer")
    return steps


def steer(hwnd, pid, vk, px, seconds, slice_s=0.25):
    """Hold `vk` for `seconds` while right-dragging the view `px` pixels in slices.

    The key is held on its own thread through dc.hold_key -- the same hold, the
    same focus re-checks, the same guaranteed keyup -- and the drag runs beside
    it as dc.orbit calls of px / n each, paced at `slice_s`; each slice is one
    heading change the client reports with a fresh 0x003D while the body keeps
    walking. Returns the seconds the key was actually held (hold_key's own
    figure, cut short if focus was lost) so a short leg is visible as one.
    """
    held = [0.0]

    def hold():
        held[0] = dc.hold_key(hwnd, pid, vk, seconds)
    th = threading.Thread(target=hold, daemon=True)
    th.start()
    time.sleep(0.15)                      # the body is walking before the first turn
    n = max(1, int(round(seconds / slice_s)))
    t0 = time.perf_counter()
    for i in range(n):
        if not th.is_alive():
            break
        dc.orbit(hwnd, pid, px / n, 0, steps=4)
        due = t0 + (i + 1) * slice_s
        while time.perf_counter() < due and th.is_alive():
            time.sleep(0.01)
    th.join(seconds + 2.0)
    return held[0]


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
        # REALFIX-T2. The three leg stamps below are whole-second strings, which
        # is +/-0.5 s = +/-143 u at run speed on every leg-to-capture mapping --
        # a systematic nobody had priced, on the same clock defect REALFIX-T1
        # fixes on the wire side. The strings STAY (every existing reader of a
        # walk row takes them); the `_unix` floats are the same instants at full
        # resolution, read one line apart.
        started_unix = time.time()
        started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        if kind == "key":
            vk = dc.NAMED_KEYS.get(key) if key in dc.NAMED_KEYS else ord(key)
            did = dc.hold_key(hwnd, proc.pid, vk, value)
        elif kind == "zoom":
            did = value if dc.scroll(hwnd, proc.pid, value) else 0.0
        elif kind == "pitch":
            # dy is NEGATED: dragging the mouse DOWN raises the camera's angle,
            # so "pitch:300" reads as "raise it" rather than as a screen delta.
            did = value if dc.orbit(hwnd, proc.pid, 0, -value) else 0.0
        elif kind == "yaw":
            # dx is passed straight through; the sign convention is VERIFIED
            # from the validation frames, not assumed: positive drags right,
            # and the camera turns the view toward the character's right.
            did = value if dc.orbit(hwnd, proc.pid, value, 0) else 0.0
        elif kind == "shot":
            # On the PLAN's clock, which the cadence shooter is not: a state
            # the plan just arranged (an ALT hold, a fresh yaw) gets its frame
            # HERE rather than whenever the interval next fires.
            shot_n[0] += 1
            p = shot_if_foreground(hwnd, proc.pid,
                                   os.path.join(outdir,
                                                f"w{shot_n[0]:03d}-step{i+1}.png"))
            did = 1.0 if p else 0.0
        elif kind == "wait":
            time.sleep(value)
            did = value
        elif kind == "attack":
            # NOT INPUT -- the same mailbox `interact:` uses, and the same
            # caveat: begin_attack is what the client's own ATTACK_AGENT arm
            # calls, so every swing, the armour term, the critical and the
            # number the client draws are real. The CLICK is what did not
            # happen. See harness/control.py request_attack.
            control.request_attack(int(key))
            did = 1.0
        elif kind == "hover":
            fx, fy = (float(p) for p in key.split(","))
            did = value if dc.hover(hwnd, proc.pid, fx, fy, value) else 0.0
        elif kind == "steer":
            k, px = key.split(",")
            vk = dc.NAMED_KEYS.get(k) if k in dc.NAMED_KEYS else ord(k)
            did = steer(hwnd, proc.pid, vk, float(px), value)
        elif kind == "click":
            # A UI click at a FIXED window fraction -- a panel button, not a
            # world target. dc.click verifies the client owns the foreground
            # before it presses anything, the same guard every key takes.
            fx, fy = (float(p) for p in key.split(","))
            did = 1.0 if dc.click(hwnd, proc.pid, fx, fy) else 0.0
        else:
            raise SystemExit(f"unknown walk step kind {kind!r}")
        ended_unix = time.time()
        ended = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        # Let the client come to rest and send its stop before the next step
        # starts, so two steps cannot share one deceleration.
        time.sleep(settle)
        settled_unix = time.time()
        settled = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        out.append({"kind": kind, "key": key, "asked": value,
                    "did": round(did, 2), "started": started, "ended": ended,
                    "settled": settled, "started_unix": started_unix,
                    "ended_unix": ended_unix, "settled_unix": settled_unix})
        print(f"  walk {label}: {did:g} of {value:g} "
              f"({started} -> {ended})", flush=True)
        shot_if_foreground(hwnd, proc.pid,
                           os.path.join(outdir, f"walk{i + 1}-{kind}{key}.png"))
    stop_shots.set()
    return out


# The four watchers moved to `runwatch.py`. They are re-exported here BY NAME --
# never behind a module prefix -- because `walk_legs`'s camera thread, `run_client`
# (its action shots, its final shot, the hold and the `finally`) and `main` all call
# them as bare names, and `test_harness.py` reaches `session.hold_open`,
# `session.verdict_after_hold` and `session.capture_error_dialog` through this module.
from runwatch import (  # noqa: F401,E402
    shot_if_foreground, hold_open, verdict_after_hold, capture_error_dialog)


def run_client(a, outdir):
    tails = {"auth": CaptureTail(vault_path("captures", "authsrv")),
             "game": CaptureTail(vault_path("captures", "gamesrv"))}

    # Instrumentation first, always -- an instrument that was not yet running
    # produces absence of evidence, never evidence of absence.
    sampler = dc.Sampler()
    sampler.start()

    args = ["-authsrv", a.auth_host, "-portal", a.portal_host,
            "-windowed", "-log"]
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
    host = dc.assert_safe(a.exe, args,
                          served_maps=served_maps(split_args(
                              getattr(a, "game_args", ""))))
    # Both launch sites run the gate independently rather than one trusting the other.
    # A guard that only guards one of two doors is the shape of the defect it is here
    # to prevent -- vault/run held two patched binaries and one was caged.
    print(f"cage: {cage.assert_launch_safe(a.exe, host)['dh']} build, cleared for {host}")
    # And the archive, for the same reason and by the same rule as the line
    # above. The client opens `Gw.dat` from its OWN process directory -- there is
    # no flag for it -- so the archive this launch is really about is the one
    # beside the exe, and a copy that fails an open-time rule is repaired,
    # rebuilt or silently emptied rather than refused.
    client_dat = os.path.join(os.path.dirname(a.exe), "Gw.dat")
    print(f"archive: {datcheck.assert_archive_safe(client_dat, why='launch')['summary']}")
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
            if kind == "interact":
                # NOT INPUT. Asks the SERVER to run its own INTERACT arm for a
                # named agent, because this harness cannot aim: projecting an
                # agent's world position to a screen pixel needs a camera yaw
                # nothing here tracks, and a blind click at a guessed spot
                # failed three runs running without producing one interaction.
                # Everything downstream is real -- real messages, real client,
                # real screen. The click is what did not happen, and the
                # gamesrv prints the same caveat when it fires.
                control.request_interact(int(parts[2]))
                delivered = True
            elif kind == "attack":
                # Same mailbox, different order. See control.request_attack:
                # the swing, the armour term, the critical and the number the
                # client draws are all real; the click is not.
                control.request_attack(int(parts[2]))
                delivered = True
            elif kind == "click":
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
                                   settle=a.settle, shot_every=a.shots)
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
            held = hold_open(proc, a.hold, tails, outdir,
                             quiet=prompts_operator(a), shot_every=a.shots)
            # THE HOLD CAN TAKE THE VERDICT AWAY, same as the walk above. Until
            # 2026-08-18 this call dropped its own return and a client that died
            # during the hold still printed PASS -- see verdict_after_hold.
            was_ok, ok = ok, verdict_after_hold(ok, held)
            if was_ok and not ok:
                print("  RUN VERDICT RETRACTED: the run passed its checkpoints, "
                      "then the client died during the hold.", flush=True)
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
                    help="stop stale python listeners found on our ports -- "
                         "only ones whose command line resolves into THIS "
                         "session's tree. A parallel worktree's stack is "
                         "refused with its tree named (2026-08-20: the old "
                         "any-python rule killed one mid-run)")
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
    ap.add_argument("--portal-host", default="127.0.0.1",
                    help="Loopback address for the webgate listener and the "
                         "client's -portal flag. 127/8 only. Defaults to "
                         "127.0.0.1, which is what every probe result so far "
                         "was measured on; move it only to run beside another "
                         "session that already holds 6601.")
    ap.add_argument("--auth-host", default="127.0.0.1",
                    help="Loopback address for the authsrv listener and the "
                         "client's -authsrv flag. 127/8 only. A second alias "
                         "(127.0.0.2) ran the probe that showed -authsrv plays "
                         "no part in the game dial (handshake PLAN §10).")
    ap.add_argument("--settle", type=float, default=1.5, metavar="SECONDS",
                    help="Pause after every walk step (default 1.5). RUN-1zCW: the "
                         "default keeps every leg's next report 1.5 s from the "
                         "previous grant, so a script cannot reproduce a report "
                         "inside the keyboard arm's old 0.5 s floor without it.")
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
                         "zoom:N, pitch:N, yaw:N (drag-turn the view), "
                         "alt:N / left:N (hold a named key -- ALT shows every "
                         "nameplate), shot:1 (screenshot on the plan's clock), "
                         "attack:10 (order a swing at an agent, mid-plan, so "
                         "the fight lands inside the --shots window) "
                         "and wait:N. "
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
                    help="Hold the session up for SECONDS after the verdict, "
                         "then tear down. Implies --keep-open, whose hold this "
                         "bounds -- alone, --keep-open holds until the client "
                         "exits. What a probe needs is its own step delays "
                         "plus slack; --list-probes prints them.")
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
                         "one-command loop could not run a probe at all. "
                         "USE THE = FORM FOR A SINGLE FLAG: --game-args="
                         "'--trace-move'. argparse reads a value starting with "
                         "'-' as another option unless it contains a space, so "
                         "two flags in one string happen to work and one flag "
                         "alone dies with 'expected one argument'.")
    ap.add_argument("--client-arg", action="append", metavar="FLAG",
                    help="Extra flag for the CLIENT, repeatable -- the other "
                         "side of --game-args, which reaches only the server. "
                         "Write it with an equals sign, `--client-arg=-perf`, "
                         "or argparse eats the leading dash as an option of its "
                         "own. -perf draws triangles, fps and transfer rate in "
                         "the top-right corner. Flags that decide where the "
                         "client points are REFUSED.")
    a = ap.parse_args()
    hold_implies_keep_open(a)

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
        cam = sum(1 for k, _, _ in legs if k in ("zoom", "pitch", "yaw"))
        print(f"walk plan: {len(legs)} step(s), {held:.1f}s of keys and waits, "
              f"{cam} camera move(s), "
              f"{sum(1 for k, _, _ in legs if k == 'shot')} scripted shot(s)")

    specs = server_specs(game_port=a.game_port, auth_host=a.auth_host,
                         portal_host=a.portal_host,
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
        # ABSOLUTE, ONCE, BEFORE ANY CONSUMER SEES IT -- and this is a real
        # defect that cost an operator session on 2026-09-03, not tidiness.
        #
        # `run_client` launches with `Popen([a.exe] + args,
        # cwd=os.path.dirname(a.exe))`. Windows resolves a RELATIVE application
        # name against the working directory it is handed, so
        # `--exe vault/run/<build>/Gw.exe` made CreateProcess look for
        # `vault/run/<build>/vault/run/<build>/Gw.exe` and die with
        # `FileNotFoundError: [WinError 2]` -- AFTER the stack was up, the cage
        # cleared and the 4 GB archive verified, so the failure arrived a good
        # twenty seconds in and looked nothing like a bad path.
        #
        # WHY IT HID FOR SO LONG: every consumer ABOVE the Popen -- the DH
        # binding check, `datcheck`, the `Gw.log` unlink -- reads the file
        # through the ordinary open() path, which resolves relative names
        # against the PROCESS cwd and therefore works fine. Only the spawn
        # takes the new cwd, so the relative form is correct everywhere except
        # the one line that matters, and whether it fires depends on the shell
        # the operator launched from. The runsheets carry the relative form and
        # it had worked repeatedly from PowerShell.
        #
        # Normalising here rather than at the Popen keeps ONE spelling of the
        # path in the report, the console line and the cage's own error text --
        # `sorted(exes)[-1]` picking the wrong build three times in this repo
        # is the standing lesson about launch paths that differ from what the
        # log says (project-rurik-sorted-last-defect).
        # AND resolve a `vault/...`-relative spelling against the REAL vault,
        # because a git worktree has no vault of its own. Every other tool here
        # reaches the vault through vaultpath for exactly this reason; `--exe`
        # was the one path a human types by hand, so it kept the cwd-relative
        # behaviour and silently pointed at nothing from a worktree. That is
        # already a recorded trap ("from a worktree, relative vault paths
        # fail -- use absolute") and it is cheaper to honour the spelling than
        # to keep the trap. Tried in order: as given, then under the vault.
        _exe_given = a.exe
        if not os.path.isfile(os.path.abspath(a.exe)):
            _parts = a.exe.replace("\\", "/").split("/")
            if _parts and _parts[0] == "vault":
                _under = vault_path(*_parts[1:])
                if os.path.isfile(_under):
                    a.exe = _under
                    print(f"client: resolved {_exe_given} under the vault "
                          f"({vault_why()})")
        a.exe = os.path.abspath(a.exe)
        if not os.path.isfile(a.exe):
            raise SystemExit(
                f"--exe does not name a file: {a.exe}\n"
                f"(resolved from the value you passed, against "
                f"{os.getcwd()}). Refused BEFORE the client launch and before "
                f"the DH-binding and archive checks -- the same mistake used "
                f"to surface as a FileNotFoundError out of CreateProcess "
                f"~20 s in, with the cage cleared and 4 GB of archive already "
                f"verified, which looks nothing like a bad path. The stack "
                f"above is torn down on the way out.")
        return run_client(a, outdir)
    except KeyboardInterrupt:
        print("\nstopping")
        return 130
    finally:
        stack.stop()


if __name__ == "__main__":
    sys.exit(main())
