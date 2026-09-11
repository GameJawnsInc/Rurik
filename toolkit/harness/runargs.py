"""Reading the run's arguments, and the argv each process in the stack gets.

Lifted out of `session.py` unchanged -- the whole of what that file used to head
`# ---- pre-flight ----`, now that the port-ownership half of that section has
gone to `portclaim.py` and the banner has nothing left to head. Two questions,
and they are one question: what did the operator ask for (`--labelrun`,
`--probe`, `--hold`, `--enemy`, `--tape`), and what argv does each of portal,
authsrv and gamesrv therefore get. The second is the first, plumbed.

DELIBERATELY ONE FILE, not two. An earlier plan split this into `runargs` (the
predicates) and `stackspec` (the argv builders), and the seam was in the wrong
place: `spawn_profession_args` and `persist_args` feed `server_specs` and
NOTHING else, so the split bought a leaf-to-leaf import, a second ~20-line
header and a second place to answer one question.

Every comment travels verbatim, and several are the record of a run that
reported the wrong thing: the `--hold N` that was inert without `--keep-open`
and made a healthy client's orderly exit read as a crash (fourteen launches
misdiagnosed, 2026-08-16); the `--probe` prompts that went to gamesrv.log while
the operator sat at a silent terminal; the chained tape run that stopped at its
own verdict, before the experiment it existed for had started, and printed PASS.
`is_labelling`'s docstring carries the NameError that `test_srclint.py` was
built out of -- a name computed in `main()` and read in `run_client()`, which
survived ast.parse and the whole suite and failed thirty seconds into a real
session.

THE REFERENTS THAT STAYED BEHIND, measured on the tree rather than guessed.
`main()` reads `hold_implies_keep_open`, `split_args`,
`warn_probe_without_enemy`, `resolve_enemy`, `chain_specs`, `chain_hold`,
`server_specs`, `is_labelling` and `prompts_operator`; `run_client()` reads
`served_maps`, `split_args` and `prompts_operator`; nothing ELSE IN `session.py`
reads `is_probing`, `spawn_profession_args`, `persist_args`, `hop_aliases` or
`_TRAVELLING_FLAGS`. That is not the same as having no reader, and the
difference is what the re-export is for: `test_harness.py` reaches eleven of the
fourteen off `session.py` as an attribute, and two of them are on that list --
`_sess.spawn_profession_args` at :658-665 and `_sess.is_probing` at :713/:719 --
so dropping either from the shim reddens a test whose floor of 159 has ZERO
headroom. Only `persist_args` and `hop_aliases` have no reader anywhere outside
this file; `_TRAVELLING_FLAGS` is private and `served_maps` is its only reader
in the tree, which is why it is not re-exported at all.
`Stack`, `_play` and `steer` are still in `session.py`, which re-exports
every public name here. Two of those call sites are pinned as BARE NAMES by
`test_harness.py`, which parses `session.py`'s own syntax tree and requires
`prompts_operator` inside both `main` and `run_client` and
`hold_implies_keep_open` inside `main` -- so the re-export is by name and never
behind a module prefix. THERE IS A THIRD SUCH PIN AND IT IS IN ANOTHER FILE:
`test_preflight_owner.py`:318-324 requires main()'s `specs` to be assigned from
a Call whose func is the Name `server_specs`, and the same file reads
`session.server_specs` as an attribute at :287 and :296 -- so `test_harness.py`
is not the only reader of these names, and the bare-Name set is three, not two.
Its floor is 29 against a measure of 30, one check of headroom.
`contentids.preflight` (named by `served_maps`) and
`drive_client.assert_safe` (which points AT `session.served_maps` for when
narrowing is legitimate) live elsewhere and are untouched.

WHY BOTH sys.path INSERTS. `server_specs` reads `vault_path` on its
`capture_root=None` default path, and `toolkit/vaultpath.py` is one level UP
from this directory -- the HERE insert alone would not find it. `chain_hold` and
`chain_specs` keep their in-body `sys.path.insert(..., "authsrv")` +
`import tape as tapemod` verbatim; those are deliberately function-local and are
not hoisted.

No import of `session.py` (R4): it runs as `__main__`, so importing it back
would load a second copy whose flags `main()` never set.
"""
import os
import shlex
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLKIT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, TOOLKIT)
from vaultpath import vault_path  # noqa: E402


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
