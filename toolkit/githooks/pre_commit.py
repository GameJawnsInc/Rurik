"""The pre-commit gate: a commit that stages a vault-shaped path or credential-shaped
content is refused before it exists.

WHY, in one paragraph. Both of this repository's gates -- the provenance gate and the
personal-data rule -- were enforced by habit for five weeks, and habit held: the
pre-publication audit (studies/prepub/FINDINGS.md) found that no vault file, capture,
key or binary was ever committed. What it DID find was four lines of source pinning a
recoverable form of the owner's account address, and a dozen real players' names in
study prose -- personal data in the tracked tree, which no rule looked at because every
rule was aimed at the vault. The repository is public now (2026-09-08), so a slip goes
out on the push and the history rewrite that fixed the last one cannot be repeated
cheaply. Section 9 of that audit asked for this hook. "A rule nothing checks is a wish."

WHAT IT REFUSES, and every shape below is MEASURED rather than guessed:

  Paths (from a census of the vault on 2026-09-08: 20,208 .png, 6,874 .jpg, 5,914
  .jsonl, 4,399 .log, 3,400 .raw, 1,182 .bin, 507 .u16, 2,153 .f32, 238 .crt, 177 .pem,
  169 .der; the stems hold<N>.png, authsrv-<stamp>-c<N>.jsonl/.raw, portal-<stamp>.jsonl,
  webgate/gamesrv/authsrv.log; the prior-art mirrors' Packet<N>.cs and P<N>_Unknown.java;
  vault/state/sessions.json with cleartext issued sessions):
    * any path with a `vault`, `captures`, `runs` or `probes` segment -- the vault
      wherever it appears, which is .gitignore's first rule and this hook's reason;
    * capture formats: .jsonl .raw .pcap .pcapng .gwcap .log .f32 .u16;
    * binaries and assets: .bin .dat .exe .dll .png .jpg ... (the tracked tree holds
      no binary of any kind; ArenaNet's expression is refused by the provenance gate
      and an image is the likeliest way it would arrive);
    * key material: .pem .der .crt .key .p12 .pfx .cer;
    * the mirrors' languages, .cs and .java: none is tracked, and a file in either is
      almost certainly copied from an upstream, which is the SECOND gate (PLAN.md 6.1's
      derivation register) rather than this one -- the refusal names it;
    * credential stores by name: sessions.json, selftest-sessions.json, Accounts.json,
      *.credentials, .env;
    * any staged blob over SIZE_CEILING (4 MB; the largest tracked file is authsrv.py
      at 1.7 MB) or carrying a NUL byte -- a capture or asset under a text extension.

  Content (staged text blobs only, line-numbered in the refusal):
    * the portal's <Password> element with a base64 body, and an `Authorization: Arena
      <GUID>` session token -- the two credential shapes RUNBOOK's off-disk list names;
    * private-key blocks and the well-known token prefixes (GitHub, AWS, Slack, Google);
    * a Windows profile path naming a real account (PREPUB-F4): C:\\Users\\<anything
      that is not a <placeholder>>;
    * UTF-16 text inside a hex dump, five or more printable-ASCII code units in a row
      (PREPUB-F2: two character names were invisible to every string search because
      they travelled as spaced UTF-16 code units);
    * a real-looking email address: any address whose top-level domain is a real one
      and whose domain is not synthetic (example.com, *.invalid, *.local, *.test, the
      GitHub noreply domain). Every address in the tree today is synthetic (PREPUB-F1,
      F3, and the upstream author's address redacted 2026-09-08).

Every rule must pass on the tree as it stands -- a hook that reddens a clean commit is
a hook people learn to skip -- and `toolkit/test_precommit.py` runs all of them over
every tracked path and every tracked text file to prove it.

THE OVERRIDE is git's own: `git commit --no-verify`. It is printed on every refusal so
nobody has to look it up, and it is deliberate by construction -- you have read the
refusal and decided. CLAUDE.md's rule against skipping hooks is about bypassing a red
you have not read; this is the other case.

INSTALL, once per clone (RUNBOOK.md, "Before that: check it works without the game"):

    git config core.hooksPath .githooks

The wrapper at `.githooks/pre-commit` is a few lines of sh that exec this file,
and it fails the commit rather than passing it if no python can be found.

Run by hand: `python toolkit/githooks/pre_commit.py` judges what is staged right now;
`--repo PATH` judges another checkout (the test uses it on temporary repositories).
Exit 0 clean, 1 refused, 2 could not read the index.
"""
import argparse
import os
import re
import subprocess
import sys

# --- path rules --------------------------------------------------------------------
VAULT_SEGMENTS = {"vault", "captures", "runs", "probes"}
CAPTURE_EXT = {".jsonl", ".raw", ".pcap", ".pcapng", ".gwcap", ".log", ".f32", ".u16"}
BINARY_EXT = {".bin", ".dat", ".exe", ".dll", ".pdb", ".so", ".dylib", ".png", ".jpg",
              ".jpeg", ".gif", ".bmp", ".dds", ".ffna", ".mft", ".tpf", ".atex",
              ".gwmodel", ".gwmap", ".wav", ".mp3", ".ogg", ".zip", ".7z", ".gz", ".bundle"}
KEY_EXT = {".pem", ".der", ".crt", ".key", ".p12", ".pfx", ".cer"}
MIRROR_EXT = {".cs", ".java"}
CREDENTIAL_NAMES = {"sessions.json", "selftest-sessions.json", "accounts.json", ".env"}
SIZE_CEILING = 4 * 1024 * 1024

OVERRIDE = ("To commit anyway, deliberately, after reading the refusal: "
            "git commit --no-verify")


def judge_path(path):
    """The reason a staged path is refused, or None. Pure; POSIX separators."""
    parts = path.replace("\\", "/").split("/")
    name = parts[-1]
    low = name.lower()
    ext = os.path.splitext(low)[1]
    for seg in parts[:-1]:
        if seg.lower() in VAULT_SEGMENTS:
            return (f"a `{seg}/` segment -- the vault, wherever it appears "
                    "(.gitignore's first rule; captures and probe output live there)")
    if ext in CAPTURE_EXT:
        return f"`{ext}` is a capture format (the vault holds thousands; the tree holds none)"
    if ext in BINARY_EXT:
        return (f"`{ext}` is a binary or asset -- the tree tracks no binary of any kind, "
                "and the provenance gate refuses ArenaNet's expression")
    if ext in KEY_EXT:
        return f"`{ext}` is key material"
    if ext in MIRROR_EXT:
        return (f"`{ext}` is a prior-art mirror's language and none is tracked -- if this "
                "is derived from an upstream, it needs a PLAN.md 6.1 register row first "
                "(the second gate), and then a .py rewrite, not a copy")
    if low in CREDENTIAL_NAMES or low.endswith(".credentials"):
        return f"`{name}` is a credential store by name"
    return None


# --- content rules -----------------------------------------------------------------
CONTENT_RULES = [
    ("the portal's <Password> element with a base64 body (PREPUB-F1; RUNBOOK's off-disk list)",
     re.compile(rb"<Password>[A-Za-z0-9+/=]{8,}</Password>")),
    ("an `Authorization: Arena <GUID>` session token",
     re.compile(rb"Authorization: Arena [0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-")),
    ("a private-key block",
     re.compile(rb"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----")),
    ("a GitHub token",
     re.compile(rb"\bghp_[A-Za-z0-9]{36}\b|\bgithub_pat_[A-Za-z0-9_]{22,}")),
    ("an AWS access key id",
     re.compile(rb"\bAKIA[0-9A-Z]{16}\b")),
    ("a Slack token",
     re.compile(rb"\bxox[baprs]-[A-Za-z0-9-]{10,}")),
    ("a Google API key",
     re.compile(rb"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("a Windows profile path naming a real account (PREPUB-F4: write C:\\Users\\<user>)",
     re.compile(rb"(?i)(?:[a-z]:[\\/]{1,2}|/[a-z]/)Users[\\/]{1,2}(?!<)[^\\/\s`'\"<>|]+")),
    ("UTF-16 text inside a hex dump -- names travel this way (PREPUB-F2: search the encoded forms)",
     re.compile(rb"(?:\b00[2-7][0-9A-Fa-f] ){4,}00[2-7][0-9A-Fa-f]\b")),
]

# A real-looking address: a real top-level domain and a domain that is not synthetic.
REAL_TLDS = {"com", "net", "org", "edu", "gov", "mil", "io", "co", "uk", "de", "fr", "ca",
             "us", "me", "info", "biz", "ru", "jp", "cn", "au", "nl", "se", "ch", "it",
             "es", "pl", "br", "in", "dev", "app", "xyz", "gg", "tv", "email", "eu", "be",
             "at", "dk", "no", "fi", "cz", "pt", "nz", "kr", "tw", "hk", "sg", "mx", "ar"}
SYNTHETIC_DOMAINS = {"example.com", "example.net", "example.org", "users.noreply.github.com",
                     "noreply.github.com", "github.com", "anthropic.com"}
SYNTHETIC_SUFFIXES = (".invalid", ".local", ".test", ".example", ".localhost")
EMAIL = re.compile(rb"(?<![A-Za-z0-9._%+-])([A-Za-z0-9._%+-]+)@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*"
                   rb"\.([A-Za-z]{2,}))(?![A-Za-z0-9-])")


def _real_address(domain):
    d = domain.lower()
    if d in SYNTHETIC_DOMAINS or d.endswith(SYNTHETIC_SUFFIXES):
        return False
    return d.rsplit(".", 1)[-1] in REAL_TLDS


def judge_content(data):
    """[(line_number, reason, match_text)] for a text blob. Pure."""
    found = []
    for reason, rx in CONTENT_RULES:
        for m in rx.finditer(data):
            found.append((data.count(b"\n", 0, m.start()) + 1, reason,
                          m.group(0)[:60].decode("utf-8", "replace")))
    for m in EMAIL.finditer(data):
        if _real_address(m.group(2).decode("ascii", "replace")):
            found.append((data.count(b"\n", 0, m.start()) + 1,
                          "a real-looking email address (keep addresses synthetic: "
                          "example.com, *.invalid, *.local -- or resolve at run time)",
                          m.group(0).decode("utf-8", "replace")))
    found.sort()
    return found


# --- the index ---------------------------------------------------------------------
def _git(repo, *args, binary=False):
    return subprocess.run(["git", "-C", repo] + list(args), capture_output=True,
                          check=True, **({} if binary else {"text": True})).stdout


def staged_paths(repo):
    out = _git(repo, "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z")
    return [p for p in out.split("\0") if p]


def staged_blob(repo, path):
    return _git(repo, "cat-file", "-p", ":" + path, binary=True)


def judge_repo(repo):
    """Every refusal for what is staged in `repo`: [(path, line_or_None, reason, match)]."""
    refusals = []
    for path in staged_paths(repo):
        why = judge_path(path)
        if why:
            refusals.append((path, None, why, ""))
            continue
        data = staged_blob(repo, path)
        if len(data) > SIZE_CEILING:
            refusals.append((path, None, f"{len(data) / 1e6:.1f} MB staged -- the ceiling is "
                             f"{SIZE_CEILING // (1024 * 1024)} MB and the largest tracked file is "
                             "1.7 MB; a blob this size is a capture or an asset", ""))
            continue
        if b"\0" in data[:8192]:
            refusals.append((path, None, "binary content under a text-looking name (a NUL "
                             "byte in the first 8 KB); the tree tracks no binaries", ""))
            continue
        for line, reason, match in judge_content(data):
            refusals.append((path, line, reason, match))
    return refusals


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--repo", default=None, help="checkout to judge (default: this one)")
    args = ap.parse_args(argv)
    repo = args.repo or _git(".", "rev-parse", "--show-toplevel").strip()
    try:
        refusals = judge_repo(repo)
    except subprocess.CalledProcessError as e:
        print(f"pre-commit: could not read the index: {e.stderr.strip() if e.stderr else e}")
        return 2
    if not refusals:
        return 0
    paths = sorted({r[0] for r in refusals})
    print(f"pre-commit: REFUSED {len(refusals)} finding(s) in {len(paths)} staged path(s) "
          "-- nothing was committed.")
    for path, line, reason, match in refusals:
        where = f"{path}:{line}" if line else path
        shown = f"  [{match}]" if match else ""
        print(f"  {where}: {reason}{shown}")
    print(OVERRIDE)
    return 1


if __name__ == "__main__":
    sys.exit(main())
