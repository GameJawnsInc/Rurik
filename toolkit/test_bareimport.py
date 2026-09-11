#!/usr/bin/env python3
"""The server must IMPORT and RUN on a machine with no vault. Proves it, names the line.

    python toolkit/test_bareimport.py

WHAT EARNS THIS FILE. On 2026-08-15 `probes.py` grew
`GIVER_NPC = npc_template("def_1480")` at module level. `def_1480` is a
bulk-extracted live NPC definition and lives only in `vault/content/npcs.toml`,
so from that commit forward `import authsrv` raised `ContentError` on any
machine without a vault -- the SERVER's own import, not merely a test's.

Nothing went red, and that is the point of this file. The suite runs on a
machine that HAS a vault, so the defect was invisible for three days while
twelve tests carried docstrings that were now false, four of them stating
"no vault, no socket, no client" flatly (`test_ping.py`, `test_dispatch.py`,
`test_population.py`, `test_killwindow.py`). They did not even fail their
floors: the exception escaped at import, before `checks.py` could rule on
anything, so a bare run produced a traceback rather than a verdict naming the
shortfall. `test_quests.py` declared `floor=73` -- "what ONE quest row runs on a
bare machine" -- and could not reach check 1 of those 73.

WHY THE FIX WAS NOT A REPO-SIDE COPY OF THE ROW. It was permitted --
CLAUDE.md's measurement-vs-expression boundary allows a measured NPC row whose
extractor is named and whose provenance is per row, and `def_1480` has all of
that. It was still wrong. Those rows are only ever read to build Step sequences
that DRIVE A REAL CLIENT, and client builds live in the vault too, so on the one
machine where a repo-side row would be read there is no client to run the probe
against. It would have bought an import, not a capability -- and the vault row
overrides the repo row by key on every machine where the probe CAN run, so the
committed copy would be dead weight free to drift from `npcdefs.py`'s output.
The bind moved to call time instead (`probequest.py`, `_vault_npc` -- it was
`probes.py` until the 2026-09-11 split of that file).

WHAT THIS CHECKS, and section 2 is the one that survives the next mistake:
section 0 imports the server in a subprocess with `RURIK_VAULT` aimed at a
directory that does not exist, section 1 does the same for `probes` alone, and
section 2 reads the source and refuses a module-level content bind whose key is
not in the REPO tables -- naming file and line, before anyone has to reproduce a
bare machine to find out. The control in section 0 is load-bearing: without it,
"the server imported fine" would also be what you see if the fake vault were
quietly resolving to the real one, and the check would assert nothing.

SECTION 3 IS THE SAME DEFECT ONE LAYER DOWN, added 2026-08-31: importing is not
running, and the second failure was on the press path rather than at module
scope. `player_rank_for_skill` read a `skills` row with no fallback, so the
server logged `skill_timing`'s "falling back to 0" announcement and then died on
that same missing row two lines later -- and section 2's scanner is structurally
unable to see it, because the read is inside a function. So section 3 EXECUTES a
press instead of reading the source, with a control proving the energy gate that
performs the read was actually on. The general lesson is the one this whole file
is about and it now has two instances: the suite runs where a vault exists, so a
bare-machine defect goes red nowhere until something reproduces a bare machine.

NO VAULT, NO SOCKET, NO CLIENT -- and unlike the four files above, this one is
in a position to prove it.
"""
import ast
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import checks                                                  # noqa: E402
import content                                                 # noqa: E402

# MEASURED 2026-08-18 from a green run: 6 checks, none of them skippable.
# Nothing here reads the vault, the client or a socket -- the subprocesses are
# told to have NO vault, which is the one fixture this file needs and it is a
# path that does not exist. So the healthy count and the floor are the same
# number, and if they ever differ this file has grown something that can skip.
#
# 6 -> 8 on 2026-08-31: section 3's press and its ENERGY control. Re-measured
# from a green run, not incremented on faith.
LEDGER = checks.Ledger("the server imports with no vault", floor=8)
check = checks.adopt(LEDGER)

SERVER_DIR = os.path.join(HERE, "authsrv")

# A path that cannot exist, rather than an empty temp dir: an empty directory
# resolves and `content.load` merges nothing from it, which is the same OUTCOME
# but tests a weaker thing. The bare machine we care about has no vault at all.
NO_VAULT = os.path.join(tempfile.gettempdir(), "rurik-no-such-vault-4a1f9c2e")


def _run(code):
    """Run `code` in a fresh interpreter with RURIK_VAULT aimed at nothing.

    A SUBPROCESS, not an import guarded by try/except, for two reasons. This
    process already imported `content` with the real vault and a module cached in
    `sys.modules` would answer from that; and `RURIK_VAULT` is read once and
    memoised in `vaultpath`, so flipping it in-process proves nothing about a
    machine that never had one.
    """
    env = dict(os.environ, RURIK_VAULT=NO_VAULT)
    pre = (f"import sys; sys.path.insert(0, {HERE!r}); "
           f"sys.path.insert(0, {SERVER_DIR!r})\n")
    return subprocess.run([sys.executable, "-c", pre + code],
                          capture_output=True, text=True, env=env, timeout=180)


def _last_line(text):
    lines = (text or "").strip().splitlines()
    return lines[-1] if lines else ""


def main():
    print(f"vault for every subprocess below: {NO_VAULT}")
    check(not os.path.exists(NO_VAULT),
          "the stand-in vault genuinely does not exist",
          "if this path were ever created, every check below would be measuring "
          "a machine that HAS a vault and would pass for the wrong reason")

    print("\n0. the server itself")
    r = _run("import authsrv\nprint('imported')")
    check(r.returncode == 0 and "imported" in r.stdout,
          "`import authsrv` succeeds with no vault",
          f"rc={r.returncode} {_last_line(r.stderr)} -- this is the SERVER path, "
          f"not a test: a module-level content bind on a vault row means the "
          f"server cannot start on a bare machine, and it stops twelve tests "
          f"before checks.py can rule on any of them")

    # CONTROL: the fake vault must actually be empty as far as content is
    # concerned. Without this, a green section 0 is also what a fake vault that
    # silently resolved to the real one would produce, and the check asserts
    # nothing. `def_1480` is the exact row that broke it, so this is the original
    # failure reproduced on purpose.
    r = _run("import agents\nagents.npc_template('def_1480')")
    check(r.returncode != 0 and "def_1480" in (r.stderr or ""),
          "CONTROL: a vault-only row is still unreachable in that subprocess",
          f"rc={r.returncode} -- if this SUCCEEDS the stand-in vault is resolving "
          f"to a real one and section 0 proved nothing")

    print("\n1. probes, on its own")
    # Directly, not through authsrv, because probes is where the bind was and an
    # import chain that happens to work today could route around it tomorrow.
    r = _run("import probes\nprint('imported')")
    check(r.returncode == 0 and "imported" in r.stdout,
          "`import probes` succeeds with no vault",
          f"rc={r.returncode} {_last_line(r.stderr)}")

    print("\n2. no module-level bind on a row the repo does not have")
    repo_only = content.load(vault_dir="")
    binds, dynamic = _module_level_binds()
    # A scan that matched nothing would pass this section while checking
    # nothing -- the `test_codec.py` fixture-glob defect, one level up.
    check(len(binds) >= 4,
          f"the scan found module-level content binds to rule on ({len(binds)})",
          f"{[f'{f}:{ln}' for f, ln, _k, _key in binds]} -- if this hits zero the "
          f"scanner stopped matching and every verdict below it is vacuous, not "
          f"clean. Dynamic keys it could not resolve: {dynamic or 'none'}")

    missing = []
    for path, line, kind, key in binds:
        try:
            repo_only.get(kind, key)
        except Exception:                                       # noqa: BLE001
            missing.append(f"{path}:{line} {kind} {key!r}")
    check(not missing,
          "every one of them resolves from content/*.toml alone",
          f"{missing} -- a module-level bind on a vault row makes the vault a "
          f"hard IMPORT dependency of everything downstream. Bind it at call "
          f"time instead (probequest.py `_vault_npc` is the worked example, "
          f"probes.py before the 2026-09-11 split); do not "
          f"copy the row into content/ to make this green, because a machine "
          f"with no vault has no client either and could not use it")

    print("\n3. and the server RUNS: a skill press with no vault")
    # WHAT EARNS THIS SECTION, and it is the hole in section 2's own stated
    # boundary. `_module_level_binds` rules on module level only, on the
    # reasoning that "the same call inside a function body is fine, because a
    # machine that cannot resolve the row was never going to reach that
    # function". `handle_skill_press` is the counterexample: it is the hot path
    # of every skill press, `ENERGY` is on by default, and until 2026-08-31
    # `player_rank_for_skill` read `skills` there with no fallback -- so a bare
    # machine got `skill_timing`'s "lifecycle timings fall back to 0" printed
    # to the log and then a `ContentError` two lines later, killing the
    # connection thread. Importing proved nothing about it. Nothing went red
    # for as long as the defect existed, exactly as with `def_1480`: the suite
    # runs on a machine that HAS a vault, and the two tests that drove this
    # path (test_castcycle, test_castcancel) died in a traceback before
    # checks.py could rule, one of them under a docstring promising a bare
    # machine ran it.
    r = _run("import authsrv\n"
             "sent = []\n"
             "send = lambda op, vals, label='', quiet=False: sent.append(op)\n"
             "authsrv.handle_skill_press([0, 42, 7, 0], send, {'agents': {}},\n"
             "                           0, authsrv.GAME_CMSG_USE_SKILL)\n"
             "print('E4' if authsrv.GAME_SMSG_SKILL_ACTIVATED_BROADCAST\n"
             "      in sent else 'no-e4')")
    check(r.returncode == 0 and "E4" in r.stdout,
          "a press runs the whole gate and reaches the wire with no vault",
          f"rc={r.returncode} {_last_line(r.stderr)} -- a content read on the "
          f"press path with no bare-machine fallback takes the connection "
          f"thread down on any machine without the overlay. The fallback "
          f"belongs in the server next to `skill_timing`'s, not in a test stub")

    # CONTROL, and it is the arm that makes the check above mean something: the
    # press must have gone through the ENERGY gate rather than around it. With
    # `ENERGY` off the whole `player_rank_for_skill` call is skipped, so a
    # green check above would also be what the ORIGINAL defect produced on a
    # server with energy disabled -- passing for the wrong reason, which is the
    # failure mode section 0's own control exists to rule out.
    r = _run("import authsrv\nprint('on' if authsrv.ENERGY else 'off')")
    check(r.returncode == 0 and "on" in r.stdout,
          "CONTROL: `ENERGY` is on in that subprocess, so the press above "
          "really did run the gate that reads the skill row",
          f"rc={r.returncode} {_last_line(r.stdout)} -- with the gate off the "
          f"check above cannot see the defect it exists to catch")

    return LEDGER.verdict()


def _module_level_binds():
    """Every top-level `X = ...npc_template("k")` / `WORLD.get("kind", "k")`.

    Module level ONLY, because that is what this scanner can rule on statically:
    a module-level bind makes the vault a hard IMPORT dependency of everything
    downstream, which is the `def_1480` failure.

    THE SECOND SENTENCE HERE USED TO BE A CLAIM RATHER THAN A SCOPE, and it was
    false: "the same call inside a function body is fine, because a machine that
    cannot resolve the row was never going to reach that function". A bare
    machine reaches `handle_skill_press` on the first skill any client presses,
    and on 2026-08-31 that path had an unguarded `skills` read in it
    (`player_rank_for_skill`) that no scan here could see. A call in a function
    body is not fine -- it is merely out of THIS function's reach, and section 3
    covers the one path that matters by executing it instead of reading it.
    """
    named = {"npc_template": "npc", "item_template": "item"}
    binds, dynamic = [], []
    for name in sorted(os.listdir(SERVER_DIR)):
        if not name.endswith(".py") or name.startswith("test_"):
            continue
        path = os.path.join(SERVER_DIR, name)
        with open(path, encoding="utf-8") as fh:
            src = fh.read()
        for node in ast.parse(src, filename=path).body:
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            for sub in ast.walk(node):
                if not isinstance(sub, ast.Call):
                    continue
                got = _bind_of(sub, named)
                if got == "dynamic":
                    dynamic.append(f"{name}:{sub.lineno}")
                elif got:
                    binds.append((name, sub.lineno) + got)
    return binds, dynamic


def _bind_of(call, named):
    """(kind, key) for a content lookup, "dynamic" if the key is computed."""
    f = call.func
    if isinstance(f, ast.Name) and f.id in named and call.args:
        a = call.args[0]
        return ((named[f.id], a.value) if isinstance(a, ast.Constant)
                else "dynamic")
    # WORLD.get("npc", "hatcher") / agents.WORLD.get(...) -- the receiver is
    # matched by NAME because that is what the import sites actually write.
    if (isinstance(f, ast.Attribute) and f.attr == "get" and len(call.args) == 2
            and ((isinstance(f.value, ast.Name) and f.value.id == "WORLD")
                 or (isinstance(f.value, ast.Attribute)
                     and f.value.attr == "WORLD"))):
        k, key = call.args
        if isinstance(k, ast.Constant) and isinstance(key, ast.Constant):
            return (k.value, key.value)
        return "dynamic"
    return None


if __name__ == "__main__":
    sys.exit(main())
