"""Find two headings that claim the SAME section number in the same scope.

WHY THIS EXISTS. On 2026-08-21 `studies/skills/FINDINGS.md` carried `## 32.` twice --
the `effect_silent_extend` probe and E10, the recharge gate -- because two sessions
appended to the same document and both took "the next number". Nothing caught it. It
was found by a human reading `PLAN.md` §8's adrenaline entry and noticing that its
"§32" could mean either. The same document had ALREADY been through this once: §26 was
duplicated and resolved as §26.12/§26.13. Two collisions in one file, neither caught,
is what licensed a checker.

THIS IS AN ACCUMULATION TRIPWIRE, NOT A GATE, and the scoping is the whole design.
The naive rule -- "no number may appear twice in a file" -- was measured against this
tree on 2026-08-22 and reported 74 duplicates across 11 files. Nearly all of them are
the HOUSE STYLE and correct:

  * A document written in dated passes restarts the count at 1 per pass, under its own
    `#` divider. `studies/skills` has two §1-§8 blocks that way, `studies/isle` two,
    `studies/review` two, `studies/character` two. A resolver, not a renumber, is the
    standing ruling on those (`studies/idents/HANDOFF.md`'s star box).
  * A `### N.` list nested under one `## ` parent has nothing to do with the `### N.`
    list under the next one. `studies/movement/FINDINGS.md` has SEVEN `### 1.` headings
    and every one is fine.

A checker that reddens at all of those is one nobody can leave switched on -- which is
the lesson `provlint.py` records from the other side. So the rule here is scoped:

  A COLLISION IS TWO HEADINGS WITH THE SAME NUMBER TOKEN, AT THE SAME HEADING LEVEL,
  UNDER THE SAME CHAIN OF ENCLOSING HEADINGS.

That is the shape an append collision actually takes, and it is rare: 6 across 2,102
numbered headings in the tree on 2026-08-22, listed and justified one by one in
`test_seclint.py`. Under this rule the pre-fix `studies/skills/FINDINGS.md` reports its
§32 and the post-fix one is clean, which is the control the test runs.

WHAT IS AND IS NOT A NUMBER TOKEN. The token is what a prose "§N" would have to say to
address the heading, so it keeps the shape the document already uses: `32`, `26.12`,
`8.0`, `6f`, `34.A`, `9a`. Headings with no leading number are ignored entirely -- most
of the tree is prose headings and they cannot collide by number.

Fenced code blocks are skipped. A `# comment` inside a shell block is not a heading,
and `studies/` is full of them.

NOT COVERED BY `identlint.py`, which was the first thing checked before writing this.
That module is the sibling tripwire for IDENTIFIER collisions and its token must be
letter-led (`BARE = [A-Z]{1,2}-?\d{1,3}...`, so `GATEFIRE-C3`, `R-ISLE`, `C6`). A bare
`## 32.` matches none of its definers -- verified, all three heading shapes return None.
The two tripwires are disjoint by construction: `identlint` guards the names an arc
mints, this guards the numbers a document hands out.

ONE DELIBERATE DIVERGENCE FROM `identlint`, which uses a COUNT CEILING (53 collisions,
ceiling 80) rather than a keyed list. A ceiling is right there because 53 is too many to
justify one by one and the entries are churny. Here there are SIX, in a tree of 2,102
numbered headings, so `test_seclint.py` names each with its reason instead: the whole
point is catching the seventh, and inside a ceiling of 9 three could land unseen.
"""
import collections
import os
import re
import sys


def _say(text):
    """print(), but a console that cannot encode a character never kills the run."""
    try:
        print(text)
    except UnicodeEncodeError:
        enc = sys.stdout.encoding or "ascii"
        print(text.encode(enc, "backslashreplace").decode(enc, "replace"))


# Walking into `.claude/` counts every study doc once per worktree, and the count then
# depends on which tree you are standing in -- the exact drift `CLAUDE.md` warns about
# under "establish which tree you are actually in". `provlint.py` records the same list
# and the same reason; keep them in step.
SKIP_DIRS = (".git", ".claude", "__pycache__", "vault", "node_modules", ".venv")

HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
NUMBER = re.compile(r"^(\d+[a-z]?(?:\.[0-9A-Za-z]+)*)[.)]?\s")
FENCE = re.compile(r"^\s*```")


class Collision:
    """One section number claimed by two or more headings in the same scope."""

    def __init__(self, path, token, level, occurrences):
        self.path = path            # repo-relative, forward slashes
        self.token = token          # "32", "26.12", "6f"
        self.level = level          # 2 for `##`, 3 for `###`
        self.occurrences = occurrences   # [(line, heading text), ...]

    @property
    def key(self):
        """What an allowlist entry names: file plus token plus level."""
        return (self.path, self.token, self.level)

    def __repr__(self):
        lines = ", ".join(f"L{n}" for n, _ in self.occurrences)
        return f"<{self.path} §{self.token} x{len(self.occurrences)} ({lines})>"


def scan_text(text, path="<text>"):
    """Every same-scope number collision in one markdown document."""
    stack = {}                       # level -> (line, text) of the enclosing heading
    seen = collections.defaultdict(list)
    fence = False
    for n, line in enumerate(text.split("\n"), 1):
        if FENCE.match(line):
            fence = not fence
            continue
        if fence:
            continue
        m = HEADING.match(line)
        if not m:
            continue
        level = len(m.group(1))
        body = m.group(2).strip()
        # Pop every enclosing heading this one closes, BEFORE reading the scope, so a
        # sibling sees the same chain and a child sees this heading in its chain.
        for open_level in [k for k in stack if k >= level]:
            del stack[open_level]
        num = NUMBER.match(body)
        scope = tuple(sorted(stack.items()))
        stack[level] = (n, body[:40])
        if num:
            seen[(scope, level, num.group(1))].append((n, body))

    out = []
    for (_scope, level, token), occ in seen.items():
        if len(occ) > 1:
            out.append(Collision(path, token, level, occ))
    return sorted(out, key=lambda c: c.occurrences[0][0])


def markdown_files(root):
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in sorted(files):
            if f.endswith(".md"):
                yield os.path.join(dirpath, f)


def scan_tree(root):
    """Every same-scope collision in every markdown file under `root`.

    Returns (collisions, files_read, headings_seen). The last two are what let a
    caller refuse a run that scanned nothing -- a glob that matches no files is the
    failure mode `checks.py` exists to catch, and this scanner is a glob.
    """
    out = []
    files = 0
    headings = 0
    for path in markdown_files(root):
        try:
            text = open(path, encoding="utf-8").read()
        except (OSError, UnicodeDecodeError):
            continue
        files += 1
        rel = os.path.relpath(path, root).replace(os.sep, "/")
        headings += count_numbered(text)
        out += scan_text(text, rel)
    return out, files, headings


def count_numbered(text):
    """How many numbered headings a document has. The denominator for the rate."""
    n = 0
    fence = False
    for line in text.split("\n"):
        if FENCE.match(line):
            fence = not fence
            continue
        if fence:
            continue
        m = HEADING.match(line)
        if m and NUMBER.match(m.group(2).strip()):
            n += 1
    return n


def main(argv):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if "--files" in argv:
        root = os.path.abspath(argv[argv.index("--files") + 1])
    found, files, headings = scan_tree(root)
    for c in found:
        _say(f"\n{c.path}  §{c.token}  (level {c.level})")
        for n, body in c.occurrences:
            _say(f"   L{n}: {'#' * c.level} {body[:84]}")
    _say(f"\n{len(found)} same-scope collision(s) over {headings} numbered heading(s) "
         f"in {files} markdown file(s).")
    _say("Collisions are not automatically wrong -- test_seclint.py holds the "
         "allowlist and the reasons.")
    return 0  # finding is not judging; the judgement lives in test_seclint.py


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
