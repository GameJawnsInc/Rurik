"""The vault resolver, and the write guard that says where a capture may land.

`vaultpath` is the most-depended-on module in the toolkit and it had no test of its
own until 2026-09-08. That is not a small omission: its whole reason for existing is
that a fixture path which silently resolves to the wrong place turns every assertion
behind it into a no-op, which is the defect `toolkit/checks.py` was written about.

Two halves, and the second is new:

  * `vault_root()` / `require_dir()` -- where a fixture may be READ from. Section 1
    pins the resolution ORDER against synthetic roots, including the property that
    makes a git worktree work at all, and section 2 pins that `require_dir` RAISES
    rather than handing back a path that is not there.
  * `resolve_out()` -- where a capture may be WRITTEN. Sections 3-5. It refuses every
    checkout of this repository and allows the vault, and the ORDER of those two
    tests is the whole design: the vault lives INSIDE the main checkout, so a guard
    that tested the checkout first would refuse every legitimate destination there
    is. Section 4 is the control for that, and it is the check that would have caught
    the guard being written the other way round.

Section 5 is the reason the guard exists at all (`studies/prepub/FINDINGS.md` sec 9
item 3): it asserts the three capture tools actually CALL it. A guard nothing calls is
the same as no guard, and this repository has shipped that exact shape before --
`test_atex.py` and `test_marks.py` both carry sections built after a writer was found
with no destination check at all.

Stdlib only. No vault fixture is required: every path here is synthetic or temporary,
so this runs on a bare machine.
"""
import ast
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import checks     # noqa: E402
import vaultpath  # noqa: E402

# 24 on the 2026-09-08 green run. The floor is 23: section 4's ordering control
# declares a skip when RURIK_VAULT points outside a checkout, and a floor equal
# to today's total would turn that legitimate configuration into a red suite.
LEDGER = checks.Ledger("vaultpath: finding the vault, and guarding the write", floor=23)

_TMP = []


def tmpdir(prefix="vaultpath_"):
    d = tempfile.mkdtemp(prefix=prefix)
    _TMP.append(d)
    return d


def main():
    # ---- 1. resolution order -------------------------------------------------
    print("\n1. RURIK_VAULT wins, and it is honoured even when it points at nothing")
    saved_env = os.environ.get("RURIK_VAULT")
    saved_cache = vaultpath._resolved
    try:
        missing = os.path.join(tmpdir(), "not-there")
        os.environ["RURIK_VAULT"] = missing
        vaultpath._resolved = None
        LEDGER.ok(vaultpath.vault_root() == os.path.abspath(missing),
                  "an explicit RURIK_VAULT is returned even though it does not exist",
                  "a typo must be REPORTED, not silently replaced by another vault -- "
                  "that is the difference between a wrong answer and a confusing one")
        LEDGER.ok(vaultpath.vault_why() == "RURIK_VAULT",
                  "and the module says which rule fired")
        LEDGER.ok(not os.path.isdir(vaultpath.vault_root()),
                  "CONTROL: the fixture really is absent, so the check above is not "
                  "passing for the wrong reason")

        real = tmpdir()
        os.environ["RURIK_VAULT"] = real
        vaultpath._resolved = None
        LEDGER.ok(vaultpath.vault_path("captures", "x")
                  == os.path.join(os.path.abspath(real), "captures", "x"),
                  "vault_path joins under the resolved root")
    finally:
        if saved_env is None:
            os.environ.pop("RURIK_VAULT", None)
        else:
            os.environ["RURIK_VAULT"] = saved_env
        vaultpath._resolved = saved_cache

    # ---- 2. require_dir raises rather than shrugging --------------------------
    print("\n2. require_dir: a missing fixture is an exception, never a path")
    saved_env = os.environ.get("RURIK_VAULT")
    saved_cache = vaultpath._resolved
    try:
        base = tmpdir()
        os.makedirs(os.path.join(base, "captures"))
        os.environ["RURIK_VAULT"] = base
        vaultpath._resolved = None
        LEDGER.ok(vaultpath.require_dir("captures") == os.path.join(base, "captures"),
                  "a directory that IS there comes back")
        try:
            vaultpath.require_dir("nope", why="the test's own fixture")
            raised = None
        except SystemExit as exc:
            raised = str(exc)
        LEDGER.ok(raised is not None,
                  "and one that is not raises SystemExit rather than returning a path")
        LEDGER.ok(raised and "nope" in raised and base in raised,
                  "naming the path it looked at and the vault it looked in",
                  (raised or "").splitlines()[:2])
        LEDGER.ok(raised and "the test's own fixture" in raised,
                  "and what the caller wanted it for")
    finally:
        if saved_env is None:
            os.environ.pop("RURIK_VAULT", None)
        else:
            os.environ["RURIK_VAULT"] = saved_env
        vaultpath._resolved = saved_cache

    # ---- 3. the write guard refuses every checkout ----------------------------
    print("\n3. resolve_out: every checkout of this repository is refused")
    roots = vaultpath.working_tree_roots()
    LEDGER.ok(roots and all(os.path.isabs(r) for r in roots),
              f"every working tree is known ({len(roots)})", str(roots))
    LEDGER.ok(os.path.abspath(ROOT) in [os.path.abspath(r) for r in roots],
              "including the one this file is running in")
    refused = 0
    for root in roots:
        for rel in ("cap.jsonl", os.path.join("toolkit", "cap.jsonl"),
                    os.path.join("studies", "movecode", "hold1.png")):
            try:
                vaultpath.resolve_out(os.path.join(root, rel))
            except ValueError:
                refused += 1
    LEDGER.ok(refused == 3 * len(roots),
              f"and a write anywhere inside one is refused ({refused} paths)",
              "root, a source directory and a study directory, in every tree")
    try:
        vaultpath.resolve_out(os.path.join(ROOT, "x.jsonl"), "a wire capture")
        msg = ""
    except ValueError as exc:
        msg = str(exc)
    LEDGER.ok("a wire capture" in msg,
              "the refusal names what was being written")
    LEDGER.ok("vault" in msg.lower() and "public" in msg.lower(),
              "and says where to write it instead, and why it matters",
              "a refusal a person cannot act on gets worked around")

    # ---- 4. the control: the vault is ALLOWED, and order is why ---------------
    print("\n4. CONTROL: the vault is allowed -- and it sits INSIDE the checkout")
    v = vaultpath.vault_path("captures", "authsrv", "x.jsonl")
    LEDGER.ok(vaultpath.resolve_out(v) == os.path.abspath(v),
              "a path under the vault comes back unchanged",
              "a guard that refused everything would protect nothing, because the "
              "tool would simply never run")
    inside = [r for r in roots
              if vaultpath._inside(vaultpath.vault_root(), r)]
    if not inside:
        LEDGER.skip("4. the ordering control",
                    "this vault is not inside a checkout (RURIK_VAULT points elsewhere), "
                    "so the ordering cannot be exercised here")
    else:
        LEDGER.ok(True,
                  "and the vault really is inside a working tree, so the ORDER of the "
                  "two tests is load-bearing",
                  f"{vaultpath.vault_root()} is inside {inside[0]} -- a checkout test "
                  f"running first would refuse the only legal destination")
    scratch = os.path.join(tmpdir(), "cap.jsonl")
    LEDGER.ok(vaultpath.resolve_out(scratch) == os.path.abspath(scratch),
              "and a path outside both is allowed",
              "the guard is about not publishing personal data, not about confining "
              "the caller to one directory")

    # ---- 5. the three tools actually CALL it ----------------------------------
    print("\n5. the capture tools route through the guard (sec 9 item 3)")
    tools = {
        "toolkit/harness/wirecapture.py": "a.out",
        "toolkit/harness/drive_client.py": "a.outdir",
        "toolkit/authsrv/authsrv.py": "a.vault",
    }
    for rel, flag in tools.items():
        src = open(os.path.join(ROOT, rel), encoding="utf-8", errors="replace").read()
        tree = ast.parse(src)
        calls = [n for n in ast.walk(tree)
                 if isinstance(n, ast.Call)
                 and ((isinstance(n.func, ast.Name) and n.func.id == "resolve_out")
                      or (isinstance(n.func, ast.Attribute)
                          and n.func.attr == "resolve_out"))]
        LEDGER.ok(len(calls) >= 1,
                  f"{rel} calls resolve_out on its output path ({flag})",
                  "a guard the tool does not call is the same as no guard -- "
                  "test_atex and test_marks both carry a section built after "
                  "exactly that was found")
    LEDGER.ok("resolve_out" in open(os.path.join(ROOT, "toolkit", "authsrv",
                                                 "shotlabel.py"),
                                    encoding="utf-8").read(),
              "and shotlabel still exposes resolve_out after delegating it",
              "its own test calls it, and the public name is the contract")
    sl_src = open(os.path.join(ROOT, "toolkit", "authsrv", "shotlabel.py"),
                  encoding="utf-8").read()
    LEDGER.ok("def working_tree_roots" not in sl_src,
              "shotlabel no longer carries its own COPY of the walk",
              "refindex.py:161 -- the write guard is imported, not re-typed; two "
              "copies is how one goes stale unnoticed")

    # ---- 6. the guard holds without git ---------------------------------------
    print("\n6. and it still holds on a machine with no git (the bare-machine class)")
    fake = tmpdir("vaultpath_nogit_")
    main_tree = os.path.join(fake, "main")
    os.makedirs(os.path.join(main_tree, ".git", "worktrees", "wt"))
    wt = os.path.join(fake, "wt")
    os.makedirs(wt)
    with open(os.path.join(wt, ".git"), "w", encoding="utf-8") as fh:
        fh.write(f"gitdir: {os.path.join(main_tree, '.git', 'worktrees', 'wt')}\n")
    saved_repo = vaultpath.repo_root
    saved_git = vaultpath._git_common_dir
    try:
        vaultpath.repo_root = lambda: wt
        vaultpath._git_common_dir = lambda start: None      # git is not on PATH
        got = [os.path.abspath(r) for r in vaultpath.working_tree_roots()]
        LEDGER.ok(os.path.abspath(main_tree) in got,
                  "the MAIN checkout is found by reading the .git gitfile",
                  f"{got} -- a worktree's .git is a FILE naming the shared gitdir")
        LEDGER.ok(os.path.abspath(wt) in got,
                  "and the worktree itself is still refused")
    finally:
        vaultpath.repo_root = saved_repo
        vaultpath._git_common_dir = saved_git
    LEDGER.ok(len(vaultpath.working_tree_roots()) == len(roots),
              "and the real roots are unchanged afterwards",
              "a monkeypatch that leaked would disarm the guard for the rest of the run")

    for p in _TMP:
        shutil.rmtree(p, ignore_errors=True)
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
