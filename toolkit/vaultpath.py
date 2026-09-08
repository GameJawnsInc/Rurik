"""Find the vault from wherever the caller happens to be standing.

The vault exists exactly once, beside the main working tree, and it is
gitignored. A git worktree is a second checkout of the same repository with no
vault of its own, so `<script>/../../vault` there names a directory that does
not exist. A test whose fixture "is not there" is a test that checks nothing:
toolkit/schema/test_codec.py printed ALL CHECKS PASSED while skipping the real
captured client frames its own docstring calls the primary fixture.

Resolution, first hit wins:

  1. $RURIK_VAULT           an explicit answer. Honoured even when it points at
                            nothing, so a typo is reported rather than silently
                            replaced by a different vault.
  2. the main working tree  `git rev-parse --git-common-dir` names the one .git
                            that every worktree shares; the vault sits beside
                            it. This is what makes a worktree work.
  3. <repo>/vault           no git in reach -- an exported copy.
  4. C:\\gd\\Rurik\\vault      this machine, last. Same constant the rest of the
                            toolkit hardcodes.

Rules 2-4 are accepted only if the directory is actually there, so a wrong
guess falls through instead of being returned.

Two jobs, and the second arrived 2026-09-08: `require_dir()` says where a
fixture may be READ from, and `resolve_out()` says where a capture may be
WRITTEN -- refusing every checkout of this repository, since the vault is
personal data and the repository is public.

Callers that need a fixture call require_dir(): it raises SystemExit with the
path it looked at and why it believed in it, rather than handing back a path
that is not there and letting the caller decide to shrug.

    python toolkit/vaultpath.py        # says which rule fired, and where
"""

import os
import subprocess

FALLBACK = r"C:\gd\Rurik\vault"

_resolved = None            # (path, why) once computed; git is not cheap to re-run


def _git_common_dir(start):
    """The .git every worktree of this repo shares, or None."""
    for args in (["--path-format=absolute", "--git-common-dir"],   # git 2.31+
                 ["--git-common-dir"]):
        try:
            out = subprocess.run(["git", "rev-parse"] + args, cwd=start,
                                 capture_output=True, text=True, timeout=15)
        except (OSError, subprocess.SubprocessError):
            return None                     # no git on PATH; rule 3 or 4 answers
        if out.returncode == 0 and out.stdout.strip():
            p = out.stdout.strip()
            # Without the flag git may answer relatively (plain ".git" in the
            # main tree), so resolve against the directory we asked from.
            return os.path.normpath(os.path.join(start, p))
    return None


def _resolve():
    here = os.path.dirname(os.path.abspath(__file__))            # toolkit/
    repo = os.path.dirname(here)

    env = os.environ.get("RURIK_VAULT")
    if env:
        return os.path.abspath(env), "RURIK_VAULT"

    common = _git_common_dir(here)
    if common:
        # The vault is the sibling of .git, i.e. inside the main working tree.
        cand = os.path.join(os.path.dirname(common), "vault")
        if os.path.isdir(cand):
            return cand, f"main working tree of {common}"

    cand = os.path.join(repo, "vault")
    if os.path.isdir(cand):
        return cand, "beside this checkout"

    return FALLBACK, "built-in fallback"


def vault_root():
    """Absolute path to the vault. May not exist -- see require_dir."""
    global _resolved
    if _resolved is None:
        _resolved = _resolve()
    return _resolved[0]


def vault_why():
    """Which rule produced vault_root(), for error messages."""
    vault_root()
    return _resolved[1]


def vault_path(*parts):
    return os.path.join(vault_root(), *parts)


def require_dir(*parts, why=None):
    """A directory under the vault that the caller cannot do without.

    Raises rather than returning a path that is not there: the house rule is
    that a check which cannot fail is not a check, and a fixture that quietly
    resolves to nothing turns every downstream assertion into a no-op.
    """
    path = vault_path(*parts)
    if os.path.isdir(path):
        return path
    lines = [f"vault fixture missing: {path}",
             f"  vault resolved to {vault_root()} ({vault_why()})"]
    if why:
        lines.append(f"  needed for: {why}")
    lines.append("  Set RURIK_VAULT to the vault directory, or see RUNBOOK.md.")
    raise SystemExit("\n".join(lines))




# --------------------------------------------------------------- the write guard
#
# WHERE A CAPTURE MAY LAND. `require_dir` above answers "where do I READ the
# fixture from"; this answers "where am I allowed to WRITE", and it is the other
# half of the same rule.
#
# The vault is personal data recorded from the owner's own account, and it stays
# local (CLAUDE.md). That was enforced by `.gitignore` and by habit until
# 2026-09-08, when studies/prepub/FINDINGS.md sec 9 measured the gap: three capture
# tools took an output path from the command line and wrote wherever they were
# pointed, so a mistyped `--out` put a capture inside the checkout, where
# `.gitignore` covers the vault BY DIRECTORY and therefore did not cover it at all.
# The repository is public now. The commit gate (toolkit/githooks/pre_commit.py)
# refuses such a file at `git commit`; this refuses it at the point of WRITING,
# which is better, because the file never exists to be found later.
#
# The implementation lives here rather than in any one tool because four modules
# already had their own copy of it (`atex`, `bit31`, `mapexport`, `shotlabel`) and
# the repository's own pattern is that the write guard is IMPORTED, not re-typed --
# `refindex.py` says so in as many words.


def _inside(path, root):
    path, root = os.path.abspath(path), os.path.abspath(root)
    return path == root or path.startswith(root + os.sep)


def repo_root():
    """The checkout this file belongs to (may be a worktree, not the main tree)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def working_tree_roots():
    """Every checkout of this repository a write could land in.

    A git worktree is a second checkout of the SAME repository, and `repo_root()`
    there is not the main tree. A refusal that tested only the tree it is running
    in would happily write a capture into the other one -- same repository, same
    publication. So the main tree is resolved too: through `git rev-parse
    --git-common-dir` when git is on PATH, and otherwise by reading the `.git`
    GITFILE directly, so the guard still holds on a machine with no git (the
    bare-machine defect class -- a guard that quietly weakens where it cannot run
    its tool is the silent-success failure `checks.py` exists to refuse).
    """
    roots = [os.path.abspath(repo_root())]

    common = _git_common_dir(roots[0])
    if not common:
        dotgit = os.path.join(roots[0], ".git")
        if os.path.isfile(dotgit):                  # a worktree: ".git" is a file
            try:
                with open(dotgit, encoding="utf-8", errors="replace") as fh:
                    line = fh.read().strip()
            except OSError:
                line = ""
            if line.startswith("gitdir:"):
                gitdir = line.split(":", 1)[1].strip()
                if not os.path.isabs(gitdir):
                    gitdir = os.path.join(roots[0], gitdir)
                node = os.path.abspath(gitdir)
                while os.path.basename(node) != ".git":
                    parent = os.path.dirname(node)
                    if parent == node:
                        node = None
                        break
                    node = parent
                common = node

    if common:
        main = os.path.dirname(os.path.abspath(common))
        if main and not _inside(main, roots[0]):
            roots.append(main)
    return roots


def resolve_out(path, what="capture output"):
    """The absolute path a write may use, or ValueError naming the tree it refused.

    THE ORDER IS LOAD-BEARING and it is `shotlabel.resolve_out`'s order: the vault
    sits INSIDE the main working tree (`<repo>/vault`), so a checkout test that ran
    first would refuse every legitimate destination there is. The vault is checked
    first and returns immediately.

    Anywhere outside both -- a scratch directory, another disk -- is allowed and
    deliberately so: this guard is about not writing personal data into a public
    repository, not about confining the caller to one directory.
    """
    path = os.path.abspath(path)
    if _inside(path, os.path.abspath(vault_root())):
        return path
    for root in working_tree_roots():
        if _inside(path, root):
            where = ("the MAIN checkout, which this worktree shares a repository with"
                     if root != os.path.abspath(repo_root()) else "this checkout")
            raise ValueError(
                f"refusing to write {what} into the working tree: {path}\n"
                f"  That tree is {root} -- {where}.\n"
                f"  The vault is personal data and stays local (CLAUDE.md); this\n"
                f"  repository is public, so a file written here is one `git add -A`\n"
                f"  from being published and cannot be recalled afterwards.\n"
                f"  Write under {vault_path('captures')} instead.")
    return path

if __name__ == "__main__":
    print(f"vault:  {vault_root()}")
    print(f"via:    {vault_why()}")
    print(f"exists: {os.path.isdir(vault_root())}")
