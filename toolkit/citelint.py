#!/usr/bin/env python3
"""Resolve `file.py:NNN` citations in committed prose against the source at HEAD.

WHAT THIS IS FOR, and it is a rot that has already been measured rather than feared.

Study documents cite source locations as `movetap.py:3049`. Nothing checks them, so
they go stale on the next commit that inserts a line above the target -- silently, and
in the one direction that matters: the number stays plausible, the file still exists,
and a reader who follows the citation lands on unrelated code and has no way to know
the document was ever right. Measured 2026-08-29 on `studies/movement/PROBE-GATEFIRE.md`:
roughly 25 of its ~30 citations pointed at the wrong line, including all eight
`movesync.py` ones -- and those eight sat under a sha256 pin that was GREEN, because
`movesync.py` had not moved since the pin and the citations went stale BEFORE it. A pin
on the file's bytes cannot see a citation that was wrong when it was written.

WHY A CHECKER RATHER THAN A SWEEP. The citations were deliberately not swept, and the
reasoning is right: nothing checks them, they rot again on the next commit, and a
25-citation sweep buys a few days. This repo has already paid once for the other
posture -- `test_provlint.py`'s header records 46 citations rewritten under a rule read
at maximum strictness and all 46 reverted the same day. A sweep is worth doing exactly
once the thing cannot silently rot again, and this module is that precondition.

WHAT MAKES A CITATION CHECKABLE. Most of them name a SYMBOL next to the number:

    `movetap.fence_verdict(reach, flips, pairs, n, rate, seq=())` at `movetap.py:4691`
    `SELFTEST_FLOOR` at `movetap.py:1469`
    `UNREAD_REFUSE_SHARE = 0.25` at `movesync.py:707`

so the citation carries its own referent and the claim "line 4691 of movetap.py is
`fence_verdict`" is machine-checkable. Where no symbol is adjacent, the only claim in
the text is that the line exists, and that is all this asserts. The two are reported as
separate tiers and counted separately, because a document whose citations all degrade
to line-exists is not covered in any useful sense and the count is how you see that.

THE ADJACENCY RULE, which is the whole design and was measured before it was written.
A backticked span is the citation's symbol only when the text BETWEEN them is short and
connective. Over PROBE-GATEFIRE.md's 31 occurrences the real gaps are `at` (14), `(` (3),
`,` (2), `is written at`, and `on them at`; the false pairings are all long
(`returns exactly one hit and it is a comment,`, `. The old row's cited site`, a whole
table cell). So the rule is a length bound plus a refusal of sentence punctuation, and
it is deliberately narrow -- a pairing this cannot make becomes a line-exists check and
is COUNTED as degraded, never guessed at. An intervening citation is erased from the gap
rather than refusing the pairing, so that one symbol can serve a LIST of citations; see
`pair_symbol` for why that is safe and what it still refuses.

LINE WRAPPING IS NOT OPTIONAL, and skipping it hides real rot. Markdown prose here is
hard-wrapped, so a symbol and its citation routinely straddle a newline:

    ... `sep` is written at
    `movetap.py:791`, ...        <- as the document read before the sweep

A same-line resolver sees no symbol there and passes the citation on line-exists. It is
NOT correct: `sep` is written at `movetap.py:1120`. So paragraphs are joined before
scanning, and two of the defects this found were ones a same-line reader would have
reported green.

WHAT IS DELIBERATELY NOT CHECKED, stated so nobody reads more into a green run:

  * FENCED CODE BLOCKS are skipped entirely. A citation inside sample output is a
    reproduction of what a tool printed, not a claim the document is making.
  * The SYMBOL is not resolved semantically. `fence_verdict` on the cited line is a
    substring-with-word-boundary match, not an AST lookup: a citation pointing at a
    CALL of `fence_verdict` rather than its `def` passes. That is the intended
    strength -- documents cite call sites on purpose -- and it means this catches
    displacement, not misattribution.
  * A LINE RANGE (`movetap.py:4289-4296`) passes if the symbol is on any line in it.
  * Line numbers only. Nothing here checks that the cited code says what the document
    claims it says.
  * Symbols shorter than three characters are not enforced; they match too much prose
    to be evidence either way, and are reported as degraded.

VERDICTS, and there are three tiers rather than two. `ok-symbol` and `ok-line` are
GREEN. `not-in-repo` is NEITHER -- see FOREIGN below. The four RED ones are kept
distinct because they want different fixes:

  * `symbol-elsewhere` -- the symbol is in the file, on other lines, which are named.
    A one-number edit, and the commonest verdict by far.
  * `symbol-absent` -- the symbol is nowhere in that file. Usually the document names
    the wrong module, and needs a sentence rewritten rather than a number bumped.
    PROBE-GATEFIRE's C5 row records exactly this shape being caught by hand.
  * `out-of-range` -- the file no longer has that many lines.
  * `ambiguous` -- two source files share the basename (`autoinject.py`, `inject.py`
    and `test_smsgnames.py` each exist twice in `toolkit/`). This refuses to pick;
    `sorted(...)[-1]` has chosen the wrong file three times in this repo already.

standard library only.

    python toolkit/citelint.py                          # scan studies/, print findings
    python toolkit/citelint.py --files studies/movement  # one subtree or one file
    python toolkit/citelint.py --all                     # every verdict, not just red
"""
import os
import re
import sys


# A citation, with an OPTIONAL path prefix. Both spellings are in the corpus and
# both are checkable -- 94 of the 727 citations under `studies/` carry a path
# (`toolkit/authsrv/agents.py:118`), and those are the STRONGER form because they
# resolve without consulting the basename index at all. The negative lookbehind
# anchors the whole match at a word boundary so `a-movetap.py:12` and the tail of
# a URL are not read as citations.
CITE = re.compile(
    r"(?<![\w./\\-])((?:[A-Za-z_][\w.-]*/)*)([A-Za-z_][A-Za-z0-9_]*\.py)"
    r":(\d+)(?:\s*-\s*(\d+))?")
TICK = re.compile(r"`([^`\n]+)`")
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
# A backticked span that is nothing but a file reference names a file, not a symbol.
FILE_REF = re.compile(
    r"^[\w./\\-]+\.(?:py|md|toml|json|jsonl|txt|cpp|h|exe|dat|ps1|cfg|ini)$")


# The adjacency bound, MEASURED (see the header). Every true pairing in the
# pilot document normalizes to 13 characters or fewer; every false one is 25 or
# more. 16 sits in that gap with room on both sides.
MAX_GAP = 16
# Sentence punctuation in the gap means the symbol belongs to a different clause.
GAP_STOP = re.compile(r"[.!?|;:]")
# Too short to be evidence: `id`, `n`, `x48`. Reported, never enforced.
MIN_SYMBOL = 3

SKIP_DIRS = (".git", ".claude", "__pycache__", "vault", "node_modules", ".venv")


def DEFINES(sym):
    """Match a line that DEFINES `sym`: a def, a class, or a module-level assignment.

    Used only to order a `symbol-elsewhere` report so the definition comes first. It
    is a report-quality rule and never a verdict rule -- nothing here passes or fails
    on whether the cited line is a definition, because documents cite call sites on
    purpose and that must keep working.
    """
    s = re.escape(sym)
    return re.compile(rf"\s*(?:def\s+{s}\b|class\s+{s}\b|{s}\s*(?::[^=]*)?=(?!=))")


KEYWORDS = frozenset("""
and as assert async await break class continue def del elif else except finally for
from global if import in is lambda nonlocal not or pass raise return try while with
yield True False None
""".split())

GREEN = ("ok-symbol", "ok-line")
# Checked nothing, and correctly so. A study document citing `PacketSniffer.py:41`
# or `Nightfall_leveler.py:12` is citing an UPSTREAM file that is not in this repo
# and never will be (`PLAN.md` 6.1's register is where those live). Counting those
# red would demand doc edits for citations that are not ours to resolve, and a
# checker red on legitimate prose is one nobody leaves switched on -- the lesson
# `test_provlint.py` and `test_seclint.py` both record. Reported, never enforced.
FOREIGN = ("not-in-repo",)


class Citation:
    """One `file.py:NNN` occurrence, with whatever verdict the source supports."""

    def __init__(self, doc, line, prefix, module, lo, hi, symbol, gap):
        self.doc = doc
        self.line = line              # line in the DOCUMENT, 1-based
        self.prefix = prefix          # `toolkit/clientscan/`, or "" if bare
        self.module = module          # `movetap.py`
        self.lo = lo
        self.hi = hi                  # None unless the citation was a range
        self.symbol = symbol          # primary identifier, or None
        self.gap = gap                # connective text, for auditing the pairing
        self.verdict = None
        self.detail = ""
        self.path = None              # what it resolved to, once resolved

    @property
    def cite(self):
        return (f"{self.prefix}{self.module}:{self.lo}"
                + (f"-{self.hi}" if self.hi else ""))

    @property
    def ok(self):
        """Checked, and it held."""
        return self.verdict in GREEN

    @property
    def red(self):
        """A defect in the DOCUMENT. `not-in-repo` is neither ok nor red."""
        return self.verdict not in GREEN and self.verdict not in FOREIGN

    def __repr__(self):
        return (f"<{self.doc}:{self.line} {self.cite} "
                f"sym={self.symbol!r} {self.verdict}>")


# --------------------------------------------------------------------------
# THE SOURCE INDEX
# --------------------------------------------------------------------------

def index_sources(root):
    """basename -> [repo-relative paths]. A basename with two homes stays a list.

    `autoinject.py`, `inject.py` and `test_smsgnames.py` each exist twice in
    `toolkit/`, so this cannot collapse to a dict of single paths. An ambiguous
    citation is reported as `ambiguous`; picking one would be the `sorted(...)[-1]`
    defect this repo has now paid for three times.
    """
    idx = {}
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if f.endswith(".py"):
                rel = os.path.relpath(os.path.join(dirpath, f), root)
                idx.setdefault(f, []).append(rel.replace("\\", "/"))
    return idx


_SRC_CACHE = {}


def source_lines(root, rel):
    """Read a source file once per run. Returns a list of lines, no terminators."""
    if rel not in _SRC_CACHE:
        with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as fh:
            _SRC_CACHE[rel] = fh.read().splitlines()
    return _SRC_CACHE[rel]


# --------------------------------------------------------------------------
# READING THE DOCUMENT
# --------------------------------------------------------------------------

def paragraphs(text):
    """Yield (joined_text, [line_numbers]) per prose paragraph, fences excluded.

    Citations wrap across hard-wrapped lines, so the scan runs on the joined
    paragraph; the returned line list maps a character offset back to the
    document line the citation is actually printed on. A fenced block is sample
    output rather than a claim and is dropped whole.
    """
    lines = text.splitlines()
    in_fence = False
    buf, nums = [], []
    for n, raw in enumerate(lines, 1):
        stripped = raw.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            if buf:
                yield " \n".join(buf), nums
                buf, nums = [], []
            continue
        if in_fence:
            continue
        if not raw.strip():
            if buf:
                yield " \n".join(buf), nums
                buf, nums = [], []
            continue
        buf.append(raw)
        nums.append(n)
    if buf:
        yield " \n".join(buf), nums


def _line_of(joined, nums, pos):
    """Document line number for a character offset into a joined paragraph."""
    return nums[min(joined.count("\n", 0, pos), len(nums) - 1)]


def primary_symbol(span, module):
    """The identifier a backticked span is about, or None.

    `movetap.fence_verdict(reach, ...)` -> `fence_verdict` (the module qualifier is
    stripped only when it matches the file being cited, so `os.path.getmtime` keeps
    its own head). `UNREAD_REFUSE_SHARE = 0.25` -> `UNREAD_REFUSE_SHARE`. Keywords
    are stepped over so `not fence_verdict(...)` still resolves.

    TWO SPAN SHAPES YIELD NO SYMBOL, and both were false pairings found by running
    this over the whole corpus rather than reasoned about in advance:

      * a BARE FILE REFERENCE (`gwdat.py`, `PLAN.md`, `toolkit/mapdata/deploy.py`)
        names a file, not a symbol in it. Left in, these produced `toolkit`,
        `gwdat` and `PLAN` as symbols and three confident `symbol-absent` reds.
      * a NUMERIC LITERAL. `0x0056` scans as the identifier `x0056`, `0x01B2` as
        `x01B2` -- opcode citations are everywhere in these documents and every one
        of them was reading as a missing symbol. So an identifier whose immediately
        preceding character is a digit is part of a literal and is stepped over.
    """
    if FILE_REF.match(span.strip()):
        return None
    stem = module[:-3] if module.endswith(".py") else module
    if span.startswith(stem + "."):
        span = span[len(stem) + 1:]
    for m in IDENT.finditer(span):
        if m.start() and span[m.start() - 1].isdigit():
            continue
        if m.group(0) not in KEYWORDS:
            return m.group(0)
    return None


def pair_symbol(joined, ticks, cite_start):
    """Nearest preceding backticked span that is connectively adjacent, else None.

    Returns (span_text, normalized_gap) or (None, reason). The gap must be short and
    free of sentence punctuation.

    INTERVENING CITATIONS ARE ERASED, NOT REFUSED, and that is a measured choice. One
    symbol routinely serves a LIST of citations --

        (`SELFTEST_FLOOR` at `movetap.py:1469` and `movesync.py:2759`)

    -- and refusing any gap containing a citation dropped the second one to a
    line-exists check, which is a real green symbol check thrown away. So citation
    spans are removed from the gap and the length and punctuation rules run on what
    is left: `at  and` here, 6 characters. The rules still bite -- ``at `a.py:1`.
    Also see`` normalizes to `at . Also see`, and the full stop refuses it. What this
    cannot do is read the FIRST citation as the second's symbol, because a span that
    is itself a citation is never a candidate.
    """
    prev = None
    for t in ticks:
        if t.end() <= cite_start and not CITE.search(t.group(1)):
            prev = t
    if prev is None:
        return None, "no preceding backticked span"
    gap = joined[prev.end():cite_start]
    gap = TICK.sub(lambda m: " " if CITE.search(m.group(0)) else m.group(0), gap)
    gap = CITE.sub(" ", gap)
    norm = re.sub(r"[*_\s]+", " ", gap).strip()
    if len(norm) > MAX_GAP:
        return None, f"gap {len(norm)} chars > {MAX_GAP}"
    if GAP_STOP.search(norm):
        return None, "sentence punctuation in gap"
    return prev.group(1), norm


def scan_text(text, doc, root, index):
    """Every citation in one document, resolved. Returns a list of Citation."""
    found = []
    for joined, nums in paragraphs(text):
        ticks = list(TICK.finditer(joined))
        for m in CITE.finditer(joined):
            own = next((t for t in ticks
                        if t.start() <= m.start() and m.end() <= t.end()), None)
            left = own.start() if own else m.start()
            span, gap = pair_symbol(joined, ticks, left)
            prefix, module = m.group(1), m.group(2)
            sym = primary_symbol(span, module) if span else None
            if sym is not None and len(sym) < MIN_SYMBOL:
                gap = f"symbol {sym!r} shorter than {MIN_SYMBOL} chars"
                sym = None
            c = Citation(doc, _line_of(joined, nums, m.start()), prefix, module,
                         int(m.group(3)), int(m.group(4)) if m.group(4) else None,
                         sym, gap)
            resolve(c, root, index)
            found.append(c)
    return found


def resolve(c, root, index):
    """Rule on one citation against the source at HEAD. Sets verdict and detail.

    A PATH-QUALIFIED citation is resolved by its own path and never by the basename
    index, which is what makes it the stronger spelling: it cannot be ambiguous, and
    a path that is wrong is a defect the bare form cannot even express.
    """
    if c.prefix:
        rel = (c.prefix + c.module).replace("\\", "/")
        if os.path.isfile(os.path.join(root, rel)):
            c.path = rel
        elif c.module in index:
            # The file exists, somewhere else. That is a real document defect and
            # a different one from a citation of an upstream tree.
            c.verdict = "wrong-path"
            c.detail = (f"no {rel} in this tree; {c.module} lives at "
                        f"{', '.join(index[c.module])}")
            return
        else:
            c.verdict = "not-in-repo"
            c.detail = f"no {rel} in this tree (upstream?)"
            return
    else:
        paths = index.get(c.module, [])
        if not paths:
            c.verdict = "not-in-repo"
            c.detail = f"no source file named {c.module} in this tree (upstream?)"
            return
        if len(paths) > 1:
            c.verdict = "ambiguous"
            c.detail = (f"{len(paths)} files named {c.module}: {paths} -- the "
                        "citation does not say which, and this refuses to pick")
            return
        c.path = paths[0]
    src = source_lines(root, c.path)
    hi = c.hi or c.lo
    if c.lo < 1 or hi > len(src):
        c.verdict = "out-of-range"
        c.detail = f"{c.path} has {len(src)} lines"
        return
    if c.symbol is None:
        c.verdict = "ok-line"
        c.detail = f"no symbol adjacent ({c.gap}); line exists, content unchecked"
        return
    word = re.compile(rf"\b{re.escape(c.symbol)}\b")
    if any(word.search(src[n - 1]) for n in range(c.lo, hi + 1)):
        c.verdict = "ok-symbol"
        c.detail = src[c.lo - 1].strip()[:70]
        return
    where = [n for n, line in enumerate(src, 1) if word.search(line)]
    if not where:
        c.verdict = "symbol-absent"
        c.detail = f"`{c.symbol}` appears nowhere in {c.path}"
        return
    c.verdict = "symbol-elsewhere"
    # DEFINITIONS FIRST, and this is not cosmetic. `fence_verdict` occurs 25 times in
    # `movetap.py` and its `def` is the 25th; a report that led with the first four
    # textual hits named four call sites and left the operator to find the one line
    # the document meant. The corrected number is almost always the definition, so
    # the fix has to be readable straight off the report or the sweep is not cheap.
    defs = [n for n in where if DEFINES(c.symbol).match(src[n - 1])]
    order = defs + [n for n in where if n not in defs]
    shown = ", ".join(f"{n}(def)" if n in defs else str(n) for n in order[:4])
    c.detail = (f"`{c.symbol}` is at {c.path}:{shown}"
                + (f" (+{len(order) - 4} more)" if len(order) > 4 else "")
                + f"; cited line reads: {src[c.lo - 1].strip()[:52]!r}")


# --------------------------------------------------------------------------
# WALKING A TREE
# --------------------------------------------------------------------------

def markdown_files(target, root):
    """Every .md under `target`, or just `target` when it names one file."""
    if os.path.isfile(target):
        return [os.path.relpath(target, root).replace("\\", "/")]
    out = []
    for dirpath, dirs, files in os.walk(target):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in sorted(files):
            if f.endswith(".md"):
                rel = os.path.relpath(os.path.join(dirpath, f), root)
                out.append(rel.replace("\\", "/"))
    return sorted(out)


def scan_tree(root, target=None):
    """Scan `target` (default `studies/`). Returns a flat list of Citation."""
    target = target or os.path.join(root, "studies")
    index = index_sources(root)
    found = []
    for rel in markdown_files(target, root):
        with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as fh:
            found.extend(scan_text(fh.read(), rel, root, index))
    return found


def tally(cites):
    """verdict -> count, for the tripwire and for the reports."""
    out = {}
    for c in cites:
        out[c.verdict] = out.get(c.verdict, 0) + 1
    return out


def say(text):
    """print(), but a console that cannot encode a character never kills the run."""
    try:
        print(text)
    except UnicodeEncodeError:
        enc = sys.stdout.encoding or "ascii"
        print(text.encode(enc, "backslashreplace").decode(enc, "replace"))


def main(argv):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target, show_all = None, False
    i = 0
    while i < len(argv):
        if argv[i] == "--files" and i + 1 < len(argv):
            target = os.path.abspath(argv[i + 1])
            i += 2
        elif argv[i] == "--all":
            show_all = True
            i += 1
        else:
            say(f"unrecognized argument: {argv[i]}")
            return 2
    cites = scan_tree(root, target)
    counts = tally(cites)
    docs = sorted({c.doc for c in cites})

    shown = [c for c in cites if show_all or c.red]
    last = None
    for c in shown:
        if c.doc != last:
            say(f"\n{c.doc}")
            last = c.doc
        say(f"  :{c.line:<5} {c.cite:<26} {c.verdict:<17} {c.detail}")

    say(f"\n{len(cites)} citation(s) in {len(docs)} document(s)")
    for v in sorted(counts):
        say(f"  {counts[v]:>5}  {v}")
    red = sum(1 for c in cites if c.red)
    say(f"  {red:>5}  RED (prose citations pointing at something else)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
