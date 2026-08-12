"""Count ArenaNet assert expressions cited in committed prose, to catch a DUMP forming.

WHAT THIS IS FOR, and it is narrower than it looks. The provenance gate's boundary is
MEASUREMENT vs EXPRESSION (owner's ruling 2026-08-11, `PLAN.md` 7 Q3, refined
2026-08-12). Under the refinement:

  * a SINGLE assert expression cited as the evidence for a claim is a MEASUREMENT,
    and is permitted with its file and line;
  * a BULK DUMP of assert strings is still ArenaNet's expression and is refused;
  * asset bytes, `Gw.dat` chunks and decompiled function bodies are refused
    absolutely, and that tier is the one with teeth.

So this module is an ACCUMULATION TRIPWIRE, not a gate. Its job is to notice a
document turning into a string dump. `studies/smsg/FINDINGS.md` quotes 65 asserts to
name twenty GAME_SMSG opcodes and that is FINE -- the quote is what lets a reader
audit the naming argument without the binary in front of them.

HOW IT GOT HERE, because the first version was wrong in an instructive way. Read
literally, the clause "verbatim assert expressions with their source path and line"
made 134 sites across sixteen documents refusable, and one session scrubbed 46 of them
before the owner asked whether provenance was starting to cost more than it protected.
It was: this repo's recorded provenance mistakes are REFUSALS -- an undecided assert
table, unbuilt unit data -- not disclosures. The zero-tolerance version of this file
would have kept demanding rewrites that traded evidence quality for nearly nothing.
What survived is the cheap part: `content.py` enforced the gate's other half from day
one while prose was checked by nobody, and a tripwire with real headroom fixes that
for free.

WHAT IS AND IS NOT COUNTED. A citation is ArenaNet's authored expression text plus its
source file plus its line. Any two of the three are ordinary and this module must stay
quiet on them, because the study docs are built out of the permitted forms and a
checker that reddens at all of them is one nobody can leave switched on:

  * a bare source path (`P:\\Code\\Gw\\Char\\CharPool.cpp`)              -- permitted
  * a path with a line (`AgMsg.cpp:208`)                                 -- permitted
  * a field or bound named in prose (``the `m_attackInterval` bound``)   -- permitted
  * a VA, an offset, a struct layout, a count                            -- permitted
  * `AgMsg:208 "(int)message.time >= 0"`                                 -- COUNTED

Counted is not refused. One is evidence; sixty in a file nobody argued from is a dump.
The ceilings live in `test_provlint.py`, which is where the judgement belongs.

`toolkit/clientscan/asserts.py --grep` prints citations by design and is fine: it is a
TOOL reading the owner's own install. This module is only about what is committed.

THE MODULE-NAME PROBLEM, and why this scans twice. `asserts.py` prints locations as
`AgMsg:208` with no extension, so the naive pattern for one is `Word:digits` -- which
also matches `Build: 38797`, `Today: 2` and every other colon-number pair in English
prose. Rather than guess, pass 1 harvests the set of basenames that appear SOMEWHERE
in the corpus with a real `.cpp`/`.h` extension, and pass 2 accepts a bare
`Module:line` only for a name in that set. The corpus grounds its own vocabulary.

standard library only.

    python toolkit/provlint.py                 # scan the repo, print findings
    python toolkit/provlint.py --files studies # scan one subtree
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from checks import _say  # noqa: E402  console that cannot encode must not kill the run

# ---------------------------------------------------------------------------
# Locations

# ArenaNet's build-machine paths, left in the image by assert() and friends.
PCODE = re.compile(r"P:\\Code\\[^\s`'\"|)\]]*")

# `AgMsg.cpp:208`, `Array.h(587)`. Only C/C++ -- a `.py`, `.java`, `.scala` or
# `.ps1` line reference is ours or an upstream's, and neither is this gate.
#
# The leading `(?<![/\w.])` is load-bearing: ArenaNet's paths use BACKSLASHES, so a
# basename reached through a forward slash (`code/client/character.h:6-33`,
# `Packets/StoC.h:731`) is an upstream mirror. Those cite across a line break, where
# the UPSTREAM word-match on the same line cannot see them.
FILELINE = re.compile(
    r"(?<![/\w.])([A-Za-z_][A-Za-z0-9_]*)\.(cpp|h)\s*(?:\(\s*(\d+)\s*\)|:\s*(\d+))")

# The same file with no line, which is a permitted location but still tells pass 1
# that the basename is an ArenaNet module.
FILEONLY = re.compile(r"(?<![/\w.])([A-Za-z_][A-Za-z0-9_]*)\.(?:cpp|h)\b")

# `asserts.py` output form. Only honoured for a basename pass 1 vouched for.
MODLINE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]{2,})\s*:\s*(\d+)\b")

# ---------------------------------------------------------------------------
# Suppressions. Each is a named reason so a finding can explain its own absence.

# Upstream reimplementations and mirrors. Citing these is the SECOND gate
# (`PLAN.md` 6.1, a licence question) and explicitly NOT this one.
UPSTREAM = re.compile(
    r"OpenTyria|GWCA|Headquarter|gw-preservation|GWToolbox|Py4GW|GWLP-R|"
    r"ldufr|gwdevhub|GregLando113|PathEngine|Dependencies[/\\]|fileserver-utils",
    re.I)

# Upstream headers the studies cite by BARE basename, with no marker word on the
# line to give them away -- so pass 1 vouches them off the bare mention and every
# later `PreGameContext:25` reads as an ArenaNet location. Named here with the
# upstream they belong to rather than loosened, so the exemption stays visible.
NOT_ARENANET = {
    "PreGameContext": "GWCA",         # GWCA/Context/PreGameContext.h
    "StoC": "GWCA",                   # GWCA/Packets/StoC.h
    "Constants": "GWCA",
    "opcodes": "OpenTyria",           # code/opcodes.h
    "GmChar": "OpenTyria",
    "GameMsg": "OpenTyria",
    "AuthMsg": "OpenTyria",
    "GmAgent": "OpenTyria",           # GmAgent.c
    "GameSrv": "OpenTyria",           # GameSrv.c
    "GmPaths": "OpenTyria",
    "constants": "Headquarter",       # include/client/constants.h
    "character": "Headquarter",       # code/client/character.h
    "Player": "GWLP-R",
    # NOT `MapData`: GWLP-R's is `MapData.scala`, which FILEONLY already ignores,
    # while `MapData:4415` in customarea is ArenaNet's own client map loader. Denying
    # the stem would drop a real finding to silence a false one.
}

# Our own tree. `authsrv.py:897-902` is a citation of code we wrote.
OURS = re.compile(
    r"\b(?:toolkit|studies|content|schema|vault|tools|docs)[/\\]|"
    r"\.(?:py|ps1|java|scala|toml|jsonl|json|md|txt|cs|js|ts)\b")

# x86 we disassembled. That is a MEASUREMENT of bytes in the owner's own install,
# not ArenaNet's authored source text, so it is permitted and must not be reported.
ASM = re.compile(
    r"^\s*(mov|movzx|movsx|push|pop|call|cmp|test|lea|j[a-z]{1,3}|f(?:ld|stp|mul|"
    r"add|sub|div|comp?p?)|add|sub|ret|xor|or|and|shl|shr|sar|imul|idiv|inc|dec|"
    r"nop|int3|leave|neg|not|set[a-z]{1,3})\b", re.I)

# A pure address, offset or immediate.
HEXY = re.compile(r"^[+\-]?(?:0x[0-9A-Fa-f]+|\d+)$")

# English. One of these words and it is prose, not a C expression.
PROSE = re.compile(
    r"\b(the|a|an|is|are|was|were|and|or|but|in|on|of|to|for|with|that|this|"
    r"its|it|own|one|two|both|each|every|not|no|which|what|when|why|how|"
    r"vocabulary|paths|path|line|lines|file|files|assert|asserts|same|from)\b",
    re.I)

# What makes a token an EXPRESSION rather than a name. A bare identifier is "the
# field", which the ruling permits; `a <= b` is authored text.
#
# `+ - * / %` are deliberately NOT here on their own. A lone slash makes prose like
# "hide / make untargetable" look like code, and a lone `+` makes the offsets and
# payload literals we MEASURED (`[ecx+0x00]`, `[55, agent, 0, 0]`) look like
# ArenaNet's. Indexing counts only with an identifier in front of the bracket.
OPERATORS = re.compile(
    r"->|<<|>>|<=|>=|==|!=|&&|\|\||[<>=!&|]|"
    r"\bsizeof\b|\barrsize\b|[A-Za-z_][A-Za-z0-9_]*\s*\[")

# A fragment left behind after a line RANGE is split (`ExeFile:252` / `/253`).
RANGE_TAIL = re.compile(r"^[/\-,]\s*\d")

# The crash-dialog form. `Assertion: <expr>` then a location, same line or near.
ASSERTION = re.compile(r"Assertion:\s*(.+?)\s*(?:$|[,|`]|\s{2,})", re.I)

# A quoted run. The opening delimiter must not follow a word character, or every
# possessive apostrophe ("ArenaNet's own ...") opens a match.
QUOTED = re.compile(r"(?<![A-Za-z0-9_])([\"'`])([^\"'`\n]{1,160})\1")

DIALOG_WINDOW = 2  # lines after an `Assertion:` that may carry its location


class Finding:
    __slots__ = ("path", "line", "kind", "expr", "loc", "text")

    def __init__(self, path, line, kind, expr, loc, text):
        self.path, self.line, self.kind = path, line, kind
        self.expr, self.loc, self.text = expr, loc, text

    def __repr__(self):
        return f"{self.path}:{self.line} [{self.kind}] {self.expr!r} @ {self.loc}"


def is_location(text):
    """A path, a file:line, or a line RANGE is a location. The ruling permits those."""
    t = text.strip().rstrip(".,;")
    if t.startswith("P:\\Code") or t.startswith("P:/Code"):
        return True
    # `ExeFile:252/253`, `PrApi.cpp:573/574`, `GmChar.h:95-105`, `GmPaths.c:11-52`.
    # Any extension, not just C/C++: a mirror's path quoted next to an ArenaNet
    # module is still a location and still not an expression.
    if re.fullmatch(r"[\w./\\-]*?[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z]{1,6})?"
                    r"\s*[:(]\s*\d+(?:\s*[-/]\s*\d+)*\)?", t):
        return True
    return False


def expr_like(text):
    """True if `text` is ArenaNet's authored expression rather than a name or a fact."""
    t = text.strip()
    if not t or len(t) > 160:
        return False
    # Our annotated disassembly leads with the VA (`0051457B call 0x7e0da0 ...`).
    # Drop it before the mnemonic test, or every annotated dump reads as an assert.
    t = re.sub(r"^(?:0x)?[0-9A-Fa-f]{6,8}\b[\s:|]*", "", t).strip()
    if not t:
        return False
    if is_location(t) or HEXY.match(t) or ASM.match(t) or RANGE_TAIL.match(t):
        return False
    if OURS.search(t) or UPSTREAM.search(t):
        return False
    if PROSE.search(t):
        return False
    return bool(OPERATORS.search(t))


def known_modules(texts):
    """Pass 1: every basename the corpus shows carrying a `.cpp`/`.h` of ArenaNet's.

    A stem is vouched only if it appears with a C/C++ extension on a line carrying no
    upstream marker. Without that condition GWCA's `PreGameContext.h` gets vouched off
    a bare prose mention and then every `PreGameContext:25` in the doc reads as an
    ArenaNet location -- which is the SECOND gate's business, not this one.
    """
    vouched, upstream_only = set(), set()
    for text in texts:
        for line in text.splitlines():
            bad = bool(UPSTREAM.search(line))
            stems = {m.group(1) for m in FILEONLY.finditer(line)}
            for m in PCODE.finditer(line):
                base = re.split(r"[\\/]", m.group(0))[-1]
                stems.add(re.sub(r"\.(cpp|h)$", "", base))
            for stem in stems:
                if stem:
                    (upstream_only if bad else vouched).add(stem)
    return (vouched - (upstream_only - vouched)) - set(NOT_ARENANET)


def locations(line, modules):
    """Every ArenaNet source location on `line` that carries a LINE NUMBER."""
    out = []
    for m in FILELINE.finditer(line):
        if m.group(1) in NOT_ARENANET:
            continue  # an upstream header cited by bare basename
        out.append(f"{m.group(1)}.{m.group(2)}:{m.group(3) or m.group(4)}")
    for m in PCODE.finditer(line):
        tail = line[m.end():m.end() + 12]
        n = re.match(r"\s*[:(]\s*(\d+)", tail)
        if n:
            out.append(f"{m.group(0)}:{n.group(1)}")
    for m in MODLINE.finditer(line):
        if m.group(1) in modules:
            out.append(f"{m.group(1)}:{m.group(2)}")
    return out


def strip_locations(line, modules):
    """`line` with every ArenaNet location removed, leaving whatever else it said."""
    out = PCODE.sub(" ", line)
    out = FILELINE.sub(" ", out)
    out = re.sub(r"Build\s*:\s*\d+", " ", out)
    out = re.sub(r"When\s*:.*$", " ", out)

    def drop(m):
        return " " if m.group(1) in modules else m.group(0)

    out = MODLINE.sub(drop, out)
    return re.sub(r"\s+", " ", out)


def scan_text(text, path, modules):
    """Every assert citation in one document."""
    out = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = ASSERTION.search(line)
        # An upstream marker anywhere on the line suppresses the two inference-based
        # shapes, because a mirror's file:line beside a mirror's code is the SECOND
        # gate's business. It must NOT suppress the dialog shape: `Assertion:` is the
        # Guild Wars crash dialog's own label, so the text after it is ArenaNet's
        # however much upstream discussion shares the line. Skipping the whole line
        # hid `studies/mapdata/FORMAT.md:233`, where the row happens to mention
        # gw-preservation's id table.
        if UPSTREAM.search(line) and not m:
            continue
        here = locations(line, modules)

        # 1. the crash-dialog form, whose location may be on a following line
        if m:
            expr = m.group(1).strip().strip("`'\"")
            loc = here[:]
            for j in range(i + 1, min(i + 1 + DIALOG_WINDOW, len(lines))):
                loc += locations(lines[j], modules)
            if loc and expr and not is_location(expr):
                out.append(Finding(path, i + 1, "dialog", expr, loc[0], line.strip()))

        # 2. the fenced-block form: an UNQUOTED expression beside its location, or
        #    one line above it. This is what a paste out of the crash dialog or out
        #    of `asserts.py --grep` looks like once the ``` fence is added, and it
        #    is the shape the `Assertion:` matcher misses because the dialog's own
        #    label was dropped when the block was tidied.
        if not m:
            bare = strip_locations(line, modules).strip(" \t`'\"|-—.,")
            if here and expr_like(bare):
                out.append(Finding(path, i + 1, "bare", bare, here[0], line.strip()))
            elif here and not bare and i > 0:
                # location alone on its line: the expression is the line above
                above = strip_locations(lines[i - 1], modules).strip(" \t`'\"|-—.,")
                if expr_like(above):
                    out.append(
                        Finding(path, i, "bare", above, here[0], lines[i - 1].strip()))

        # 3. an assert expression quoted beside its location
        if here:
            for q in QUOTED.finditer(line):
                body = q.group(2)
                # `AgMsg:208 "(int)time >= 0"` is sometimes quoted WHOLE.
                stripped = re.sub(
                    r"^[A-Za-z_][A-Za-z0-9_]*(?:\.(?:cpp|h))?\s*[:(]\s*\d+\)?\s*",
                    "", body).strip()
                if expr_like(stripped):
                    out.append(
                        Finding(path, i + 1, "quoted", stripped, here[0], line.strip()))

    # One line quoting `a <= b` also quotes the `<=` inside it. Keep the longest
    # expression per (line, location): the fragments are the same finding.
    best = {}
    for f in out:
        key = (f.line, f.loc)
        if key not in best or len(f.expr) > len(best[key].expr):
            best[key] = f
    return [best[k] for k in sorted(best)]


# `.claude` holds this repo's WORKTREES, each a full checkout of the same documents.
# Walking into it from the main checkout counts every study doc once per worktree --
# measured 2026-08-12 at 809 citations across 98 files against a true 136 across 17,
# with 81 of those files living under `.claude/worktrees/`. The failure is worse than
# a wrong number: it is tree-dependent, so the suite passed from inside a worktree and
# went red the moment the same commit was checked out on `main`, which is the exact
# drift `CLAUDE.md` warns about under "establish which tree you are actually in".
SKIP_DIRS = (".git", ".claude", "__pycache__", "vault", "node_modules", ".venv")


def markdown_files(root):
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in sorted(files):
            if f.endswith(".md"):
                yield os.path.join(dirpath, f)


def scan_tree(root):
    """Every assert citation in every tracked markdown file under `root`."""
    paths = list(markdown_files(root))
    texts = {}
    for p in paths:
        try:
            texts[p] = open(p, encoding="utf-8").read()
        except (OSError, UnicodeDecodeError):
            continue
    modules = known_modules(texts.values())
    out = []
    for p, text in texts.items():
        out += scan_text(text, os.path.relpath(p, root), modules)
    return out, modules


def main(argv):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if "--files" in argv:
        root = os.path.abspath(argv[argv.index("--files") + 1])
    found, modules = scan_tree(root)
    by_file = {}
    for f in found:
        by_file.setdefault(f.path, []).append(f)
    for path in sorted(by_file):
        _say(f"\n{path}")
        for f in by_file[path]:
            _say(f"  :{f.line:<6} [{f.kind:<6}] {f.loc:<44} {f.expr}")
    _say(f"\n{len(found)} assert citation(s) in {len(by_file)} file(s); "
         f"{len(modules)} ArenaNet module names recognised.")
    _say("Citations are PERMITTED (PLAN.md 7 Q3, refined 2026-08-12). "
         "test_provlint.py holds the dump ceilings.")
    return 0  # counting is not judging; the ceilings live in test_provlint.py


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
