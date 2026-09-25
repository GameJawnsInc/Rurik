"""The pre-commit gate refuses what it must and NOTHING the tree already holds.

Two claims, and the second is the one that keeps a hook installed. A gate that refuses a
capture is easy; a gate that never reddens a clean commit is what stops people learning
`--no-verify` as a reflex. So sections 1 and 2 run every path rule over EVERY tracked
path and every content rule over EVERY tracked text file, and assert zero refusals --
the same posture as `test_provlint.py`'s tree sweep. When a rule is added, that sweep is
the check that says whether the tree can carry it.

Section 3 is the gate as git runs it: temporary repositories with real indexes, the
module invoked the way the wrapper invokes it, exit codes and the printed refusal read
back. Section 4 pins the wrapper -- shebang, the module it execs, its mode in the index
-- and that THIS clone has it installed, because a hook on disk that `core.hooksPath`
does not name is the audit's own definition of a wish. "Installed" is read the way git
reads it -- the merged value, a relative one resolved against the worktree root -- and
means it names a directory holding the wrapper, NOT that it equals the string
`.githooks`: an app-made worktree carries main's absolute path instead and is gated all
the same. Section 4b rebuilds that config in a temporary repository, commits through it
to read back which copy of what ran, and holds the check able to go red.

**EVERY FIXTURE BELOW IS ASSEMBLED FROM PARTS, AND THAT IS NOT A STYLE CHOICE.**
Section 2 sweeps every tracked text file, and this file is one of them. A secret written
out here as a literal would be found by the sweep it is meant to exercise, so the test
would redden the moment it was added -- and the hook would refuse the commit that added
it, which is a closed loop with no way out but `--no-verify`. The first draft of this
file was written that way. Worse, its literals were the REAL ones: a credential GUID and
a fragment of a character name, both of which had been removed from every blob and
message in this repository hours earlier by a two-pass history rewrite
(`studies/prepub/FINDINGS.md` sec 8). Committing them would have put them back, in the
one file whose job is to keep them out. So: nothing here is a real secret, and nothing
here is contiguous on disk. `probe_self` at the end of section 2 is the check that
proves it, by running the content rules over this very file.

Stdlib only, no vault, no socket, no client. Git is required (section 3 skips without
it, declared).
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "githooks"))
import checks  # noqa: E402
import pre_commit as pc  # noqa: E402

LEDGER = checks.Ledger("pre-commit gate", floor=60)

TEXT_EXT = (".py", ".md", ".toml", ".json", ".txt", ".ps1", ".c", ".h", ".wikitext",
            ".gitignore", ".gitattributes", ".cfg", ".ini", ".yml", ".yaml")

# --- fixtures, assembled so no secret shape is contiguous in this file --------------
_PW = b"<Pass" + b"word>"
_PW_END = b"</Pass" + b"word>"
# Not either of the GUIDs the rewrite removed -- a made-up one of the same shape.
_FAKE_GUID = b"11111111-2222-3333-4444-" + b"555555555555"
_UTF16_RUN = b" ".join(b"%04X" % c for c in b"Test!")        # five printable units
_ADDR = b"alice.b@" + b"gmail" + b".com"
_PROFILE = b"C:\\Users\\" + b"jsmith" + b"\\AppData\\Local\\x.log"
_PROFILE_FWD = b"/c/Users/" + b"jsmith" + b"/Documents"
_PEM = b"-----BEGIN " + b"RSA PRIVATE KEY-----\nMIIE\n"
_GHP = b"ghp_" + b"a" * 36
_AKIA = b"AKIA" + b"IOSFODNN7EXAMPLE"
_SLACK = b"xoxb-" + b"1234567890-abcdefghij"
_GOOGLE = b"AIza" + b"A" * 35


def tracked():
    out = subprocess.run(["git", "-C", ROOT, "ls-files", "-z"], capture_output=True,
                         text=True, check=True).stdout
    return [p for p in out.split("\0") if p]


# What makes a pre-commit OUR wrapper: the module it execs, cwd-relative.
WRAPPER_EXEC = b"toolkit/githooks/pre_commit.py"
# The hook_install states in which a commit here is judged by this tree's rules.
INSTALLED = ("own", "shared", "differs")


def hook_install(root, env=None):
    """(state, configured, hooks_dir): what `core.hooksPath` makes git run at `root`.

    Read MERGED -- worktree, local, global, system -- because that is the value git uses,
    and a relative path resolves against `root`, the directory git runs hooks from
    (githooks(5)). States: "unset"; "missing", no pre-commit there; "foreign", a
    pre-commit that is not our wrapper; "own", `root`'s own `.githooks`; "shared", another
    tree's, its wrapper byte-identical to `root`'s; "differs", another tree's, not.
    """
    configured = subprocess.run(["git", "-C", root, "config", "--type=path",
                                 "core.hooksPath"], capture_output=True, text=True,
                                env=env).stdout.strip()
    if not configured:
        return "unset", configured, None
    hooks_dir = configured if os.path.isabs(configured) else os.path.join(root, configured)
    try:
        with open(os.path.join(hooks_dir, "pre-commit"), "rb") as fh:
            runs = fh.read()
    except OSError:
        return "missing", configured, hooks_dir
    if WRAPPER_EXEC not in runs:
        return "foreign", configured, hooks_dir
    own_dir = os.path.join(root, ".githooks")
    if os.path.isdir(own_dir) and os.path.samefile(hooks_dir, own_dir):
        return "own", configured, hooks_dir
    try:
        with open(os.path.join(own_dir, "pre-commit"), "rb") as fh:
            carried = fh.read()
    except OSError:
        carried = None
    return ("shared" if runs == carried else "differs"), configured, hooks_dir


def _rmtree(path):
    """rmtree that also removes git's read-only object files, which Windows keeps."""
    for dirpath, _, files in os.walk(path):
        for f in files:
            try:
                os.chmod(os.path.join(dirpath, f), 0o666)
            except OSError:
                pass
    shutil.rmtree(path, ignore_errors=True)


def main():
    # ---- 1. path rules ----------------------------------------------------------------
    print("\n1. path rules: every measured vault shape refused, every tracked path allowed")
    refused = {
        "vault/captures/portal/portal-20260804T120000.jsonl": "vault",
        "studies/x/vault/notes.md": "vault",
        "captures/live/tape.md": "captures",
        "toolkit/runs/r1/report.json": "runs",
        "probes/p1/out.txt": "probes",
        "toolkit/authsrv-20260901T101010-c1.raw": ".raw",
        "studies/chat/authsrv-20260901T101010-c1.jsonl": ".jsonl",
        "studies/movecode/hold12.png": ".png",
        "docs/screen.jpg": ".jpg",
        "oracle/Gw.dat": ".dat",
        "toolkit/clientpatch/Gw.exe": ".exe",
        "toolkit/movehook.dll": ".dll",
        "studies/x/snd_3.bin": ".bin",
        "studies/x/gamesrv.log": ".log",
        "studies/x/heights.f32": ".f32",
        "mirror/Packet7.cs": ".cs",
        "mirror/P5_Unknown.java": ".java",
        "keys/server.pem": ".pem",
        "keys/ca.crt": ".crt",
        "state/sessions.json": "sessions.json",
        "toolkit/Accounts.json": "Accounts.json",
        ".env": ".env",
        "toolkit/live.credentials": ".credentials",
        "a/b/tape.gwcap": ".gwcap",
    }
    for path, token in refused.items():
        why = pc.judge_path(path)
        LEDGER.ok(why is not None and token.lower() in (why + path).lower(),
                  f"refuses {path}", why or "ALLOWED")
    paths = tracked()
    LEDGER.ok(len(paths) >= 600, "the tracked tree is read whole, not sampled",
              f"{len(paths)} paths")
    bad = [(p, pc.judge_path(p)) for p in paths if pc.judge_path(p)]
    LEDGER.ok(not bad, f"and all {len(paths)} tracked paths pass the path rules",
              "; ".join(f"{p}: {w}" for p, w in bad[:5]))
    for p in ("toolkit/clientscan/movehook/movehook.c", "toolkit/clientscan/movehook/sites.h",
              "studies/movecode/RUN-1zCG.md", "content/maps.toml", "schema/messages.json"):
        LEDGER.ok(pc.judge_path(p) is None, f"the tree's own shapes are allowed: {p}")
    LEDGER.ok(pc.judge_path("toolkit/githooks/pre_commit.py") is None
              and pc.judge_path(".githooks/pre-commit") is None,
              "and the gate's own two files are committable under its own rules")

    # ---- 2. content rules -------------------------------------------------------------
    print("\n2. content rules: each shape refused, its placeholder form allowed, the tree clean")
    positives = {
        "<Password>": b"x\n" + _PW + b"aGVsbG8gd29ybGQ=" + _PW_END + b"\n",
        "Arena": b"Authorization: Arena " + _FAKE_GUID + b"\n",
        "PRIVATE KEY": _PEM,
        "GitHub": b"token=" + _GHP + b"\n",
        "AWS": b"key " + _AKIA + b" here\n",
        "Slack": _SLACK + b"\n",
        "Google": _GOOGLE + b"\n",
        "profile path": b"log at " + _PROFILE + b"\n",
        "profile path (fwd)": b"see " + _PROFILE_FWD + b"\n",
        "UTF-16": b"0107 " + _UTF16_RUN + b" 0001\n",
        "email": b"contact " + _ADDR + b" for keys\n",
        "email (sentence end)": b"wrote to bob@hotmail" + b".co.uk.\n",
    }
    for label, data in positives.items():
        hits = pc.judge_content(data)
        LEDGER.ok(len(hits) == 1, f"refuses {label}", f"{len(hits)} hit(s): {hits[:2]}")
    allowed = {
        "the <user> placeholder": b"C:\\Users\\<user>\\AppData\\Local\\Temp\\x\n",
        "the doubled-backslash placeholder": b"`C:\\\\Users\\\\<a real name>\\\\Documents`\n",
        "the f-string Password template": _PW + b"{b64encode(b'hunter2').decode()}" + _PW_END + b"\n",
        "the elided Password element": _PW + "…".encode("utf-8") + _PW_END + b"\n",
        "a non-ASCII UTF-16 run": b"009F 00F0 0020 006D 0026 00B0\n",
        "synthetic addresses": b"loopback@rurik.invalid selftest@rurik.local owner@example.com "
                               b"player7@example.invalid 1234+x@users.noreply.github.com\n",
        "an attribute chain that looks like an address": b"n@functools.cache\n",
        "a wire hex dump without text": b"1706 F80F ACBB 4FA2 010A 0BA9 0107 0001\n",
    }
    for label, data in allowed.items():
        hits = pc.judge_content(data)
        LEDGER.ok(not hits, f"allows {label}", str(hits[:2]))
    text_files = [p for p in paths if p.lower().endswith(TEXT_EXT)]
    dirty = []
    for p in text_files:
        with open(os.path.join(ROOT, p), "rb") as fh:
            data = fh.read()
        for line, reason, match in pc.judge_content(data):
            dirty.append(f"{p}:{line} {reason} [{match}]")
    LEDGER.ok(len(text_files) >= 600, "every tracked text file is swept",
              f"{len(text_files)} files")
    LEDGER.ok(not dirty, f"and all {len(text_files)} pass the content rules -- the hook "
              "cannot redden a clean commit", "; ".join(dirty[:5]))

    # The fixtures above are assembled precisely so this file survives its own sweep.
    with open(os.path.abspath(__file__), "rb") as fh:
        probe_self = pc.judge_content(fh.read())
    LEDGER.ok(not probe_self,
              "and THIS file passes the rules it exercises -- no fixture is contiguous",
              "; ".join(f"{ln}: {why} [{m}]" for ln, why, m in probe_self[:4])
              or "a literal here would make the hook refuse the commit that adds this test")

    # ---- 3. the gate as git runs it ---------------------------------------------------
    print("\n3. real indexes: refusals name path and line, a clean commit passes, "
          "a deletion is not judged")
    if shutil.which("git") is None:
        LEDGER.skip("3. real indexes", "no git on PATH")
    else:
        tmp = tempfile.mkdtemp(prefix="rurik-precommit-")
        try:
            def g(*a):
                return subprocess.run(["git", "-C", tmp] + list(a), capture_output=True,
                                      text=True, check=True).stdout

            g("init", "-q")
            g("config", "user.email", "t@example.invalid")
            g("config", "user.name", "t")

            def put(rel, data):
                full = os.path.join(tmp, rel)
                os.makedirs(os.path.dirname(full) or tmp, exist_ok=True)
                with open(full, "wb") as fh:
                    fh.write(data)

            put("notes.md", b"clean\n")
            put("vault/captures/x.jsonl", b"{}\n")
            put("study.md", b"line one\ncontact " + _ADDR + b"\nline three\n")
            put("blob.md", b"text\x00binary\n")
            g("add", "-Af")
            found = pc.judge_repo(tmp)
            by_path = {r[0]: r for r in found}

            LEDGER.ok("notes.md" not in by_path,
                      "a clean file in a dirty commit is not refused",
                      "the refusal must name the offender, not the commit")
            LEDGER.ok("vault/captures/x.jsonl" in by_path,
                      "the capture is refused by path")
            LEDGER.ok("study.md" in by_path and by_path["study.md"][1] == 2,
                      "the address is refused with its LINE NUMBER",
                      f"got line {by_path.get('study.md', (None, None))[1]}, expected 2")
            LEDGER.ok("blob.md" in by_path
                      and "NUL" in by_path["blob.md"][2],
                      "and binary content under a .md name is caught by its NUL byte",
                      str(by_path.get("blob.md", ("", "", "none"))[2])[:70])

            # The module, invoked the way the wrapper invokes it.
            r = subprocess.run([sys.executable,
                                os.path.join(HERE, "githooks", "pre_commit.py"),
                                "--repo", tmp],
                               capture_output=True, text=True)
            LEDGER.ok(r.returncode == 1,
                      "invoked as the wrapper invokes it, a dirty index exits 1",
                      f"exit {r.returncode}")
            LEDGER.ok("vault/captures/x.jsonl" in r.stdout and "study.md:2" in r.stdout,
                      "and prints every refusal with path and line for a human to act on",
                      r.stdout.strip().splitlines()[:2])
            LEDGER.ok("--no-verify" in r.stdout,
                      "and names the deliberate override rather than hiding it")

            # A clean index passes, and a DELETION of a refused shape is not judged.
            g("rm", "-q", "--cached", "vault/captures/x.jsonl", "study.md", "blob.md")
            os.remove(os.path.join(tmp, "vault", "captures", "x.jsonl"))
            LEDGER.ok(pc.judge_repo(tmp) == [],
                      "with only the clean file staged, nothing is refused")
            r2 = subprocess.run([sys.executable,
                                 os.path.join(HERE, "githooks", "pre_commit.py"),
                                 "--repo", tmp], capture_output=True, text=True)
            LEDGER.ok(r2.returncode == 0 and not r2.stdout.strip(),
                      "a clean commit exits 0 and says nothing",
                      f"exit {r2.returncode}, said {r2.stdout.strip()[:60]!r}")

            g("commit", "-q", "-m", "clean")
            put("vault/captures/y.jsonl", b"{}\n")
            g("add", "-Af")
            g("commit", "-q", "--no-verify", "-m", "seed a refused shape")
            g("rm", "-q", "vault/captures/y.jsonl")
            LEDGER.ok(pc.judge_repo(tmp) == [],
                      "and DELETING a vault-shaped path is not refused",
                      "--diff-filter=ACMR: a deletion cannot leak anything, and a gate "
                      "that blocked cleanups would be uninstalled within a week")

            # Size: a blob over the ceiling, under a source extension.
            put("big.py", b"x" * (pc.SIZE_CEILING + 1))
            g("add", "-Af")
            big = [r for r in pc.judge_repo(tmp) if r[0] == "big.py"]
            LEDGER.ok(len(big) == 1 and "MB" in big[0][2],
                      "a blob over the size ceiling is refused under any extension",
                      str(big[0][2])[:70] if big else "not refused")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    # ---- 4. the wrapper, and that this clone has it installed --------------------------
    print("\n4. the wrapper git actually runs, and its installation here")
    hook = os.path.join(ROOT, ".githooks", "pre-commit")
    if not os.path.exists(hook):
        LEDGER.skip("4. the wrapper", f"no wrapper at {hook}")
    else:
        with open(hook, "rb") as fh:
            src = fh.read()
        LEDGER.ok(src.startswith(b"#!/bin/sh"),
                  "the wrapper is POSIX sh -- what git runs, on Windows too")
        LEDGER.ok(WRAPPER_EXEC in src,
                  "and it execs THIS module, not some other copy",
                  "two gates in one tree is how one of them goes stale unnoticed")
        LEDGER.ok(b"exit 1" in src,
                  "and a missing python FAILS the commit rather than passing it",
                  "checks.py: a gate whose failure mode is silent success is worse "
                  "than no gate")
        mode = subprocess.run(["git", "-C", ROOT, "ls-files", "-s", ".githooks/pre-commit"],
                              capture_output=True, text=True).stdout.split()
        if not mode:
            LEDGER.skip("4. the wrapper's mode", "not tracked yet (first commit of it)")
        else:
            LEDGER.ok(mode[0] == "100755",
                      "and it is executable IN THE INDEX, so a fresh clone can run it",
                      f"index mode {mode[0]} -- fix with git update-index --chmod=+x")
        # This used to require core.hooksPath == ".githooks" and was red in every
        # worktree the desktop app makes: the app writes main's ABSOLUTE hooks path into
        # .git/worktrees/<name>/config.worktree (observed 2026-09-25), so git runs MAIN's
        # wrapper there. That clone is gated, and by THIS tree's rules: git runs a hook
        # from the worktree root, the wrapper execs a cwd-relative WRAPPER_EXEC, and that
        # module judges the cwd's index -- only the dozen lines of sh are borrowed. 4b
        # commits through exactly that config and reads back which copy of each ran.
        #   * "shared", main's wrapper byte-identical to this one: a PASS, noted -- what
        #     git runs is what this tree carries.
        #   * "differs", this branch has edited the wrapper: a PASS on installation plus a
        #     declared SKIP. Not a pass on the wrapper, because the three checks above
        #     then describe a file git does not run here and no commit made in this
        #     worktree exercises the edit. Not a FAIL, because the clone is gated by this
        #     tree's rules and the difference is the app's config meeting an unlanded
        #     branch, gone when it lands; red there would say "unguarded" of a guarded
        #     clone. The skip prints under "not measured" with the one-line fix.
        state, configured, hooks_dir = hook_install(ROOT)
        fix = "install with `git config core.hooksPath .githooks` (RUNBOOK.md)"
        whose = "ANOTHER tree's hooks"
        if state in ("shared", "differs"):
            common = subprocess.run(["git", "-C", ROOT, "rev-parse", "--path-format=absolute",
                                     "--git-common-dir"], capture_output=True,
                                    text=True).stdout.strip()
            main_hooks = os.path.join(os.path.dirname(common), ".githooks")
            if os.path.isdir(main_hooks) and os.path.samefile(hooks_dir, main_hooks):
                whose = "MAIN's hooks (an app-made worktree)"
        LEDGER.ok(state in INSTALLED,
                  "and THIS clone has it installed (core.hooksPath)",
                  {"unset": f"core.hooksPath is unset; {fix}",
                   "missing": f"core.hooksPath={configured!r} holds no pre-commit; {fix}",
                   "foreign": f"core.hooksPath={configured!r} holds a pre-commit that is "
                              f"not this wrapper (no {WRAPPER_EXEC.decode()}); {fix}",
                   "own": f"core.hooksPath={configured!r}: this tree's own .githooks",
                   "shared": f"core.hooksPath={configured!r}: {whose}, not this tree's "
                             ".githooks -- the wrapper is byte-identical to this tree's "
                             "and execs this tree's rules",
                   "differs": f"core.hooksPath={configured!r}: {whose}, whose wrapper "
                              "DIFFERS from this tree's -- see the skip"}[state])
        if state == "differs":
            LEDGER.skip("4. this branch's wrapper, as git runs it here",
                        f"git runs {os.path.join(hooks_dir, 'pre-commit')}, not this "
                        "tree's edited .githooks/pre-commit (the rules module is still "
                        "this tree's); run the edit with "
                        "`git config --worktree core.hooksPath .githooks`")

        # ---- 4b. that check against the app's config rebuilt, and able to go red ------
        print("\n4b. core.hooksPath as git reads it: the app's worktree config committed "
              "through, and the states that are not installed")
        tmp = tempfile.mkdtemp(prefix="rurik-hookspath-")
        try:
            # The owner's global and system config must not decide a fixture: a global
            # core.hooksPath would make "unset" unreachable.
            quiet = os.path.join(tmp, "empty.gitconfig")
            open(quiet, "wb").close()
            env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
            env.update(GIT_CONFIG_GLOBAL=quiet, GIT_CONFIG_NOSYSTEM="1")
            main_tree, wt = os.path.join(tmp, "main"), os.path.join(tmp, "wt")

            def git(repo, *a, check=True):
                return subprocess.run(["git", "-C", repo] + list(a), capture_output=True,
                                      text=True, env=env, check=check)

            def write(path, data, mode=0o644):
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "wb") as fh:
                    fh.write(data)
                os.chmod(path, mode)

            def rules(who):
                # Stands in for the rules module: names whose copy ran, then refuses --
                # so a commit that goes THROUGH ran no rules at all.
                return f"print('rules: {who}')\nraise SystemExit(1)\n".encode()

            def commit():
                r = git(wt, "commit", "-q", "--allow-empty", "-m", "probe", check=False)
                return r.returncode, (r.stdout + r.stderr).strip()

            def point(value):
                git(wt, "config", "--worktree", "core.hooksPath", value)
                return hook_install(wt, env)[0]

            os.makedirs(main_tree)
            git(main_tree, "init", "-q")
            git(main_tree, "config", "user.email", "t@example.invalid")
            git(main_tree, "config", "user.name", "t")
            git(main_tree, "config", "extensions.worktreeConfig", "true")
            write(os.path.join(main_tree, ".githooks", "pre-commit"), src, 0o755)
            write(os.path.join(main_tree, "toolkit", "githooks", "pre_commit.py"),
                  rules("main"))
            git(main_tree, "add", "-A")
            git(main_tree, "commit", "-q", "-m", "seed")
            git(main_tree, "worktree", "add", "-q", "-b", "wt", wt)
            write(os.path.join(wt, "toolkit", "githooks", "pre_commit.py"),
                  rules("worktree"))

            # The app's config, verbatim in shape: main's absolute path, worktree scope.
            state = point(os.path.join(main_tree, ".githooks"))
            LEDGER.ok(state == "shared",
                      "the app's config -- main's absolute .githooks in config.worktree -- "
                      "reads as installed, and as MAIN's", state)
            code, out = commit()
            hooks_run = "no python on PATH" not in out
            if not hooks_run:
                LEDGER.skip("4b. commits through the hook",
                            "the wrapper found no python on git's sh PATH")
            else:
                LEDGER.ok(code != 0 and "rules: worktree" in out and "rules: main" not in out,
                          "and a commit there is refused by THIS tree's rules, run through "
                          "main's wrapper -- why SHARED is a pass", f"exit {code}: {out[:80]!r}")

            # This branch edits its wrapper: the same config no longer runs what it carries.
            write(os.path.join(wt, ".githooks", "pre-commit"),
                  src.replace(b"\n", b"\necho 'wrapper: worktree' >&2\n", 1), 0o755)
            state = hook_install(wt, env)[0]
            LEDGER.ok(state == "differs",
                      "with this tree's wrapper edited, the same config reads as DIFFERS",
                      state)
            if hooks_run:
                code, out = commit()
                LEDGER.ok(code != 0 and "rules: worktree" in out
                          and "wrapper: worktree" not in out,
                          "and git runs MAIN's wrapper, not the edit -- why DIFFERS is a "
                          "declared skip, not a pass", f"exit {code}: {out[:80]!r}")

            # The fix the skip names: relative, resolved against the worktree root.
            state = point(".githooks")
            LEDGER.ok(state == "own",
                      "`.githooks` resolves against the worktree root: this tree's own",
                      state)
            if hooks_run:
                code, out = commit()
                LEDGER.ok(code != 0 and "wrapper: worktree" in out
                          and "rules: worktree" in out,
                          "and git then runs this tree's edited wrapper -- the skip's fix works",
                          f"exit {code}: {out[:80]!r}")

            # The negatives: each must fail the check above, not merely read differently.
            git(wt, "config", "--worktree", "--unset", "core.hooksPath")
            state = hook_install(wt, env)[0]
            LEDGER.ok(state == "unset" and state not in INSTALLED,
                      "UNSET is refused -- the check goes red", state)
            if hooks_run:
                code, out = commit()
                LEDGER.ok(code == 0 and "rules:" not in out,
                          "and a commit then goes through with no rules run -- the control: "
                          "the refusals above WERE the hook", f"exit {code}: {out[:80]!r}")
            os.makedirs(os.path.join(tmp, "nohooks"))
            state = point(os.path.join(tmp, "nohooks"))
            LEDGER.ok(state == "missing" and state not in INSTALLED,
                      "a directory holding no pre-commit is refused", state)
            write(os.path.join(tmp, "otherhooks", "pre-commit"), b"#!/bin/sh\nexit 0\n",
                  0o755)
            state = point(os.path.join(tmp, "otherhooks"))
            LEDGER.ok(state == "foreign" and state not in INSTALLED,
                      "and so is one whose pre-commit is not this wrapper", state)
        finally:
            _rmtree(tmp)

    # ---- 5. the rules are independent, proved by breaking each one ---------------------
    print("\n5. sabotage: with one rule removed, only its own control stops refusing")
    saved = (pc.CAPTURE_EXT, pc.VAULT_SEGMENTS, pc.CONTENT_RULES)
    try:
        pc.CAPTURE_EXT = set()
        LEDGER.ok(pc.judge_path("studies/x/heights.f32") is None,
                  "with CAPTURE_EXT emptied, the extension control passes",
                  "so section 1's .f32 refusal was that rule and nothing else")
        LEDGER.ok(pc.judge_path("vault/x.f32") is not None,
                  "but a vault PATH is still refused with every capture extension allowed",
                  "the two rules are independent, not one rule counted twice")
        pc.CAPTURE_EXT = saved[0]

        pc.VAULT_SEGMENTS = set()
        LEDGER.ok(pc.judge_path("captures/live/tape.md") is None,
                  "with VAULT_SEGMENTS emptied, a markdown under captures/ passes")
        pc.VAULT_SEGMENTS = saved[1]

        pc.CONTENT_RULES = []
        LEDGER.ok(not pc.judge_content(_PEM),
                  "with CONTENT_RULES emptied, the private key passes")
        LEDGER.ok(len(pc.judge_content(b"contact " + _ADDR + b"\n")) == 1,
                  "but the address rule still fires -- it is not one of CONTENT_RULES",
                  "the email rule is separate code and the sabotage proves it")
    finally:
        pc.CAPTURE_EXT, pc.VAULT_SEGMENTS, pc.CONTENT_RULES = saved
    LEDGER.ok(pc.judge_path("studies/x/heights.f32") is not None
              and pc.judge_content(_PEM),
              "and every rule is restored afterwards",
              "a sabotage that leaked would disarm the gate for the rest of the run")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
