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


if __name__ == "__main__":
    print(f"vault:  {vault_root()}")
    print(f"via:    {vault_why()}")
    print(f"exists: {os.path.isdir(vault_root())}")
