"""Count DEFINING sites for single-letter work-item identifiers, and their collisions.

WHAT THIS IS FOR. `studies/idents/HANDOFF.md` §1 states the problem in one sentence: a
session writes *"C-8 finished, looking into C-9 next"* and the reader cannot tell which
document defines `C-8`, what KIND of thing it is, or whether `C-9` exists. §2.1 measured
108 such tokens across ten documents; §2.2 named three defects, of which the first is
**cross-document collision** -- the same bare token defined in more than one place.

This module measures that collision count and prints the census behind it.

IT IS AN ACCUMULATION TRIPWIRE, NOT A GATE, and that is decision 5 of the handoff,
option two of three. The option this deliberately is NOT is a hard gate that reddens
when a new token lacks an arc prefix: 80 documents predate any convention, and the
handoff's own top box is a standing warning against the cure costing more than the
disease -- the 2026-08-12 provenance scrub rewrote 46 citations across sixteen
documents and all 46 were reverted. `toolkit/provlint.py` is the pattern this file
copies: count here, judge in `test_identlint.py`, and give the ceiling real headroom so
ordinary research does not fire it.

WHAT A "DEFINING SITE" IS. Two shapes, both of which put the token FIRST, because that
is what a document does when it is introducing a thing rather than mentioning one:

  * a table row whose first cell begins with the token   `| **C8** | Derive ... |`
  * a heading whose text begins with the token           `### C8 -- Two more opcodes`

A leading backtick disqualifies both. `` | `C-1`-`C-13` | archivewrite | `` is a row in
`studies/idents/HANDOFF.md`'s own census table -- it CITES those tokens, it does not
define them, and a checker that cannot read the document describing it is not one to
trust with anything else.

THE COUNT IS A FLOOR, and this is the same discipline `asserts.py` counts carry. It is
written down at length in `census_limits()` below and reported in the tool's own output,
because `studies/idents/HANDOFF.md` §6 says 108 is a floor and a later session read the
wider scan at roughly 290-330. Both numbers are floors. What this module needs is not
the true total -- it is a number computed the same way every run, so that GROWTH is
visible. A stable undercount does that job; a wobbling estimate does not.

HYPHENS ARE NOT A NAMESPACE. `archivewrite` writes `C-8` and `movement` writes `C8`;
the handoff calls the hyphen "a *weak* signal ... not a rule and must not be taught as
one". So tokens are normalised by dropping the hyphen before collision keys are built,
which is what makes `C-8` and `C8` collide -- and they should, because §1's opening
sentence is about the hyphenated one and lands on all three sites.

standard library only.

    python toolkit/identlint.py              # the census, the collisions, the summary
    python toolkit/identlint.py --tokens     # every token, with every site
    python toolkit/identlint.py --root PATH  # scan another checkout
    python toolkit/whichrung.py C8           # resolve one token (same machinery)
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from checks import _say  # noqa: E402  a console that cannot encode must not kill a run

# Three shapes a defining site may open with, anchored by the callers at the start of
# a cell or a heading, never searched free in prose -- free search cannot tell a
# definition from a mention and this module refuses to guess.
#   bare:      `R0a`, `R1.5`, `C-13`, `U10`, `Q2b` -- the grandfathered corpus. One or
#              two capitals, optional hyphen, digits, optional `.N`, optional trailing
#              lowercase letter.
#   prefixed:  `GATEFIRE-C3`, `ITEMMODS-M1`, `PROPS-P1` -- what CONVENTION.md sec 1
#              mints. The word is 4+ chars and the LOCAL TAIL must carry a digit,
#              which is what keeps `PROBE-GATEFIRE` (a filename) and
#              `R4C2-FEASIBILITY` (a title) out of the census.
#   ladder:    `R-ISLE`, `R-IDENTS` -- PLAN.md sec 3's own namespace, the one
#              exception that stays bare. Without this arm the resolver could not
#              answer for the rung this convention itself landed under.
BARE = r"[A-Z]{1,2}-?\d{1,3}(?:\.\d)?[a-z]?"
PREFIXED = r"[A-Z][A-Z0-9]{3,}-[A-Z]{0,2}\d{1,3}(?:\.\d)?[a-z]?"
LADDER = r"R-[A-Z]{2,}"
TOKEN = rf"(?:{PREFIXED}|{LADDER}|{BARE})"

# Emphasis and strike wrappers a row may carry. `PLAN.md` §3 bolds every rung, and
# `HANDOFF.md`'s repair pattern strikes a superseded one in place rather than deleting
# it -- `studies/idents/HANDOFF.md` §2.3 is the record of why. A struck row still
# defines its token, so `~~` is stripped, not treated as a disqualifier.
WRAP = r"(?:\*\*|__|~~|\*)*"

# A table row whose FIRST cell opens with the token.
ROW_DEFINER = re.compile(rf"^\|\s*{WRAP}\s*({TOKEN})\b")

# A heading whose text opens with the token.
HEAD_DEFINER = re.compile(rf"^(#{{1,6}})\s+{WRAP}\s*({TOKEN})\b")

# This repo's worktrees are full checkouts of the same documents, so walking into
# `.claude/` would count every study doc once per tree -- the tree-dependent number
# `provlint.py` records in full. Here the walk enters only `studies/` plus three
# named root files, so a nested checkout is structurally unreachable and this prune
# is currently INERT -- kept as future-proofing for the day the walk widens.
# `test_identlint.py` asserts the corpus scope directly, which CAN go red.
SKIP_DIRS = (".git", ".claude", "__pycache__", "vault", "node_modules", ".venv")

# The corpus is the one `studies/idents/HANDOFF.md` §2 measured: three root documents
# plus every study document. `RUNBOOK.md` is deliberately out, as it was there --
# it mints its own F-namespace and references the R ladder without defining it, so
# adding it would move the number without moving the defect.
ROOT_DOCS = ("PLAN.md", "HANDOFF.md", "TESTS.md")
STUDY_DIR = "studies"


class Site:
    """One place a document introduces a token."""

    __slots__ = ("path", "line", "token", "kind", "text")

    def __init__(self, path, line, token, kind, text):
        self.path, self.line, self.token = path, line, token
        self.kind, self.text = kind, text

    def __repr__(self):
        return f"{self.path}:{self.line} [{self.kind}] {self.token}"


def normalize(token):
    """Collision key. The hyphen is a weak signal, not a namespace -- so it goes."""
    return token.replace("-", "").upper()


def scan_text(text, path):
    """Every defining site in one document, in line order."""
    out = []
    for i, line in enumerate(text.splitlines()):
        m = ROW_DEFINER.match(line)
        if m:
            out.append(Site(path, i + 1, m.group(1), "row", line.strip()))
            continue
        m = HEAD_DEFINER.match(line)
        if m:
            out.append(Site(path, i + 1, m.group(2), "head", line.strip()))
    return out


def corpus_files(root):
    """The documents §2 measured: three at the root, and `studies/` recursively."""
    out = []
    for name in ROOT_DOCS:
        p = os.path.join(root, name)
        if os.path.isfile(p):
            out.append(p)
    for dirpath, dirs, files in os.walk(os.path.join(root, STUDY_DIR)):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for f in sorted(files):
            if f.endswith(".md"):
                out.append(os.path.join(dirpath, f))
    return out


def scan_tree(root):
    """Every defining site in the corpus, paths relative to `root`."""
    out = []
    for p in corpus_files(root):
        try:
            text = open(p, encoding="utf-8").read()
        except (OSError, UnicodeDecodeError):
            continue
        out += scan_text(text, os.path.relpath(p, root).replace(os.sep, "/"))
    return out


def by_token(sites):
    """`{normalised token: [Site, ...]}`, each list in corpus order."""
    out = {}
    for s in sites:
        out.setdefault(normalize(s.token), []).append(s)
    return out


def collisions(sites):
    """`{normalised token: [document, ...]}` for tokens defined in 2+ DOCUMENTS.

    Documents, not sites: a document that defines `C1`..`C9` down one table is one
    namespace doing its job, and counting its nine rows as nine collisions would bury
    the signal `studies/idents/HANDOFF.md` §2.2(a) is actually about.
    """
    out = {}
    for tok, hits in by_token(sites).items():
        docs = sorted({s.path for s in hits})
        if len(docs) > 1:
            out[tok] = docs
    return out


def defining_sites(root, token):
    """Every site defining `token`, hyphen-insensitively. The resolver's whole engine."""
    want = normalize(token)
    return [s for s in scan_tree(root) if normalize(s.token) == want]


def census_limits():
    """What this pattern MISSES. Printed by the tool, because a floor must say so.

    Kept as text next to the code that earns it, so the caveat cannot drift away from
    the number the way `studies/idents/HANDOFF.md` §2.1's own 108 did.
    """
    return [
        "prose definitions -- a token first named mid-sentence has no anchor a regex "
        "can tell from a mention, and this module refuses to guess rather than "
        "inflate the number with references",
        "bold list-lead definers (`- **C6** -- ...`) -- whole arcs define this way "
        "(profession/FINDINGS.md's L-tiers, reconstruction/FINDINGS.md's O-claims), "
        "and a wider scan put the true floor near 290-330 rather than this one",
        "headings that introduce a token in the MIDDLE of their text "
        "(`## Answers to PLAN sec 7, Q1-Q5`)",
        "single-letter systems with no digit -- customarea/FINDINGS.md sec 11's "
        "`### A.` / `### B.` corrections headings, which are defect (c) itself",
        "RUNBOOK.md's F-namespace, and PLAN.md sec 7's Q-numbered owner decisions, "
        "both outside the corpus the handoff's census measured",
        "commit subjects -- sec 2.4's bare-integer prefixes `29:`..`42:` live only in "
        "the git log and no document defines them",
        "a hyphen-digit tail truncates: isle/FINDINGS.md's `R4-1`..`R4-4` all record "
        "as token `R4`, which then collides with WORKAROUNDS.md's own `R4` -- the "
        "truncation can MANUFACTURE a collision, not merely blur a spelling "
        "(`R4c-2` -> `R4c` is the harmless shape)",
        "a document that cannot be read (OSError, bad UTF-8) is silently dropped -- "
        "the SITE/DOC floors in test_identlint.py are what bound that shrink",
    ]


def report(root):
    """Print the census, the collisions and the summary. Returns (sites, collisions)."""
    sites = scan_tree(root)
    docs = {}
    for s in sites:
        docs.setdefault(s.path, []).append(s)

    _say("DEFINING SITES BY DOCUMENT")
    for path in sorted(docs):
        toks = []
        for s in docs[path]:
            if s.token not in toks:
                toks.append(s.token)
        _say(f"\n  {path}  ({len(docs[path])} site(s))")
        _say(f"    {' '.join(toks)}")

    coll = collisions(sites)
    _say("\n\nCROSS-DOCUMENT COLLISIONS -- one bare token, several definers")
    for tok in sorted(coll):
        _say(f"\n  {tok}  ({len(coll[tok])} documents)")
        for s in by_token(sites)[tok]:
            _say(f"    {s.path}:{s.line}  [{s.kind}]  {s.token}")

    _say("\n\nTHIS COUNT IS A FLOOR. It does not see:")
    for miss in census_limits():
        _say(f"  - {miss}")

    _say(f"\n{len(sites)} defining site(s) in {len(docs)} document(s); "
         f"{len(by_token(sites))} distinct token(s); "
         f"{len(coll)} of them collide across documents.")
    _say("Collisions are NOT refused -- 80 documents predate any convention. "
         "test_identlint.py holds the growth ceiling.")
    return sites, coll


def main(argv):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if "--root" in argv:
        i = argv.index("--root")
        if i + 1 >= len(argv):
            _say("--root needs a path")
            return 2
        root = os.path.abspath(argv[i + 1])
        if not os.path.isdir(root):
            _say(f"{root}: not a directory")  # a typo'd root is a confident zero census
            return 2
    sites, _coll = report(root)
    if "--tokens" in argv:
        _say("\n\nEVERY TOKEN, EVERY SITE")
        index = by_token(sites)
        for tok in sorted(index):
            _say(f"\n  {tok}")
            for s in index[tok]:
                _say(f"    {s.path}:{s.line}  [{s.kind}]  {s.text[:110]}")
    return 0  # counting is not judging; the ceiling lives in test_identlint.py


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
