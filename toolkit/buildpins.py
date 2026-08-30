"""Every constant in `toolkit/` that is a fact about one client build.

    python toolkit/buildpins.py                  # the census, by class
    python toolkit/buildpins.py --live           # only class (a), the liability
    python toolkit/buildpins.py --json FILE      # write a baseline to diff later
    python toolkit/buildpins.py --diff BEFORE    # what moved since that baseline

WHY. `PLAN.md` §6:803 costs "client auto-patches over ground truth" as **ongoing**,
which is a placeholder rather than a number, and `PLAN.md` §7 Q2 -- whether to
re-platform onto the WASM client -- is waiting on that number. Nobody had
counted, and the two attempts on record disagree: a draft said "409 occurrences
across 49 files" (does not reproduce under any regex tried) and
`studies/review/FINDINGS.md`:581 says "30 addresses in `toolkit/`" with no stated
method. This module states its method, so its answer can be refuted.

THE CLASSES, from `studies/crossbuild/PLAN.md` §6. Counting is not the
deliverable; classifying is, because the three want opposite things:

  (a) LIVE      a constant the tool COMPUTES with. The per-build liability, and
                the only class that needs work.
  (b) CITATION  an address in a comment or docstring, recording where a finding
                came from. HARMLESS AND WANTED -- provenance under `PLAN.md`
                §7 Q3. A bare VA with no build id is the defect, not the VA.
                Reported so the ratio is visible, never as something to fix.
  (c) TEST      an expectation in a `test_*.py`. WANTED: going red on a new
                build is the correct behaviour. What it must do is SAY so.

WHY AN AST AND NOT A GREP, which is the whole reason this file exists rather
than a one-line `rg`. A grep cannot tell class (a) from class (b) -- the strings
are identical -- and this repo has been bitten by exactly that substitution
twice: `test_cmsgnames.py` had a grep that asserted its own arm's formatting and
reddened on a line break, and `sweeploop.py`'s cage check matched the docstring
explaining the rule. The distinction is structural and the parser already knows
it: **a number in a comment is not in the tree at all, and a number in a
docstring is a `str`.** Only a real `int` literal can be computed with. So
class (a) is "an int Constant in the AST", class (b) is "hex-looking text in a
comment or a string", and no heuristic is needed to separate them.

WHAT COUNTS AS BUILD-COUPLED. Stated, because an unstated rule is why the two
earlier numbers cannot be checked:

  * an int literal written in HEX landing inside the client's image,
    0x00401000..0x00F00000 -- a virtual address; and
  * any literal equal to a known client build number.

AND WHAT IT EXCLUDES, which is the half that had to be MEASURED rather than
guessed. The first draft also took "any hex literal of >= 5 digits below the
image base" as an RVA or file offset, and ran: it swept in `0x00000001` and
`0x00000008` (skill-table bit flags), `0x00010000`, `0x345CC` (a map file id
cited in five modules), `0x10000`, and the `gwdat` code-length thresholds. Not
one is build-coupled. The bucket earned nothing -- the DH struct RVA `0x6843e8`,
the case it was written for, appears only in prose, because `dump_dh_params.py`
finds that struct by signature -- so it is gone. Mask-shaped values are excluded
too, by three tests that together removed `0x00400000` (the image base itself),
`0x00FFFFFF`, `0x00FF00FF` and `0x00f00000`: a single set bit, an all-ones run,
or a literal spelled with two or fewer distinct hex digits.

THE LIMIT, and it must be quoted with the number. This counts ADDRESSES and
BUILD NUMBERS. It does not count build-coupled constants of other shapes, and at
least one exists: the client's version header, `0x000C0500` on build 38797 where
upstream sources said `0x000C0700` (`authsrv.py`:100-107). That one is already
handled well -- an allowlist that rejects-and-logs rather than a single constant
-- but a reader must not take this census as "every build-coupled fact in the
tree". It is every build-coupled ADDRESS.

READ ONLY. Parses source; opens no client and no archive.

READ ONLY. Parses source; opens no client and no archive.
"""
import argparse
import ast
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "clientscan"))

# The client's mapped image, above the PE header. 0x00401000 rather than the
# image base, because 0x00400000 IS the base and is a constant about the PE
# format rather than about a build.
IMAGE_LO, IMAGE_HI = 0x00401000, 0x00F00000
MIN_HEX_DIGITS = 5


def mask_shaped(value, text):
    """Is this a bit mask or a flag rather than an address?

    Three tests, each of which removed real false positives from the first run:
    a single set bit (`0x00400000`, `0x00010000`), an all-ones run
    (`0x00FFFFFF`), and a literal written with two or fewer distinct hex digits
    (`0x00FF00FF`, `0x00f00000`).

    THE THIRD TEST HAS A BLIND SPOT AND THIS DOCSTRING USED TO DENY IT. It said
    "No address in this tree is shaped like any of them, and every constant that
    is turned out not to be an address." MEASURED 2026-08-29, that is false in
    exactly two places, and the sharper one is a line-neighbour of a counted pin:

        movetap.py:1866   _bytes_at(buf, secs, 0x00605FF9, 7)   <- COUNTED
        movetap.py:1867   _bytes_at(buf, secs, 0x00606000, 2)   <- INVISIBLE

    Both are virtual addresses read out of the same image in the same
    expression; the second is dropped because its digits are {0, 6}.
    `compositetrap.TEXT_HI` 0x00a00000 is the other. The remaining five VA-range
    literals the filter drops in non-test files ARE correctly excluded (three in
    mapdata/gwdat.py's size table, two in authsrv/questdefs.py's masks), which is
    why the heuristic stays: it is right far more often than it is wrong, and
    tightening it would re-admit those.

    So THE CENSUS TOTAL IS A FLOOR, NOT A COUNT, and the two known invisible
    addresses are named above so the floor is a stated one. An address that
    wanted to hide from this meter would only have to choose its digits; nothing
    here would notice, and test_buildpins.py's literal would stay green.
    """
    if value <= 0:
        return True
    if value & (value - 1) == 0:                 # exactly one bit set
        return True
    if value & (value + 1) == 0:                 # 0b111...1
        return True
    digits = set((text or "").lower().lstrip("0x").replace("_", ""))
    return len(digits) <= 2

# Filled from `pinned.BUILDS` so the two lists cannot drift apart. Falls back to
# the one number that is spelled all over the tree if that import ever fails.
try:
    import pinned
    BUILD_NUMBERS = {b.number for b in pinned.BUILDS if b.number}
except Exception:                                            # pragma: no cover
    BUILD_NUMBERS = {38797}

LIVE, CITATION, TEST = "live", "citation", "test"

# A VA-shaped run in prose. Anchored on `0x` so a bare decimal in a sentence is
# not swept in; the width floor is the same one the AST side uses.
PROSE_HEX = re.compile(r"0x[0-9A-Fa-f]{%d,}" % MIN_HEX_DIGITS)


def is_build_coupled(value, text):
    """(bool, kind). `text` is the literal exactly as written in the source."""
    if value in BUILD_NUMBERS:
        return True, "build-number"
    t = (text or "").strip().lower().replace("_", "")
    if not t.startswith("0x"):
        return False, ""
    if len(t) - 2 < MIN_HEX_DIGITS:
        return False, ""
    if IMAGE_LO <= value < IMAGE_HI and not mask_shaped(value, t):
        return True, "va"
    return False, ""


def enclosing_name(path_stack):
    """The class/def a literal sits inside, as `Class.method` or `-` for module."""
    names = [n for n in path_stack if n]
    return ".".join(names) if names else "-"


class Walker(ast.NodeVisitor):
    """Collects every build-coupled int literal, with where it lives."""

    def __init__(self, src, relpath):
        self.src, self.relpath = src, relpath
        self.stack = []
        self.assign_to = []
        self.hits = []

    # -- context ---------------------------------------------------------
    def _scoped(self, node, name):
        self.stack.append(name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_FunctionDef(self, node):
        self._scoped(node, node.name)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        self._scoped(node, node.name)

    def visit_Assign(self, node):
        names = [t.id for t in node.targets if isinstance(t, ast.Name)]
        self.assign_to.append(names[0] if names else None)
        self.generic_visit(node)
        self.assign_to.pop()

    def visit_Constant(self, node):
        # bool is a subclass of int; True is not an address.
        if not isinstance(node.value, int) or isinstance(node.value, bool):
            return
        text = ast.get_source_segment(self.src, node)
        ok, kind = is_build_coupled(node.value, text)
        if not ok:
            return
        self.hits.append({
            "file": self.relpath,
            "line": node.lineno,
            "value": node.value,
            "text": (text or "").strip(),
            "kind": kind,
            "symbol": next((n for n in reversed(self.assign_to) if n), None)
                      or enclosing_name(self.stack),
            "scope": enclosing_name(self.stack),
        })


def prose_hits(src):
    """Build-coupled addresses in COMMENTS and STRINGS -- class (b).

    Counted by subtraction rather than by a second parse: every hex run in the
    file, minus the ones the AST accounted for as real literals. A comment is
    not in the tree, so it cannot be found there; and doing it this way means
    the two classes are guaranteed to partition rather than overlap.
    """
    return PROSE_HEX.findall(src)


def scan_file(path, root):
    rel = os.path.relpath(path, root).replace("\\", "/")
    with open(path, encoding="utf-8", errors="replace") as fh:
        src = fh.read()
    try:
        tree = ast.parse(src, filename=path)
    except SyntaxError as exc:
        return None, f"{rel}: does not parse: {exc}"
    w = Walker(src, rel)
    w.visit(tree)

    is_test = os.path.basename(path).startswith("test_")
    for h in w.hits:
        h["klass"] = TEST if is_test else LIVE

    # Class (b): every hex run in the text, less those the AST claimed. Counted
    # per VALUE and per occurrence, because one address is often cited many
    # times and the interesting number is how many distinct facts are recorded.
    literal_texts = [h["text"].lower() for h in w.hits]
    prose = []
    for run in prose_hits(src):
        if literal_texts and run.lower() in literal_texts:
            literal_texts.remove(run.lower())
            continue
        try:
            v = int(run, 16)
        except ValueError:                                   # pragma: no cover
            continue
        ok, kind = is_build_coupled(v, run)
        if ok:
            prose.append({"file": rel, "value": v, "text": run, "kind": kind,
                          "klass": CITATION})
    return w.hits + prose, None


# The instrument does not measure itself. `IMAGE_LO` is an address in the
# client's image by construction and `BUILD_NUMBERS`' fallback is a build number,
# so scanning this file adds two rows that describe the ruler rather than the
# thing measured -- and they would churn the baseline every time the range is
# tuned. Named rather than silent: the count of what was skipped is printed.
SELF = ("buildpins.py", "test_buildpins.py")


def scan(root):
    """(rows, problems, skipped) over every .py under `root`."""
    rows, problems, skipped = [], [], []
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs
                   if d not in ("__pycache__", ".git", "node_modules", ".venv")]
        for f in sorted(files):
            if not f.endswith(".py"):
                continue
            if f in SELF:
                skipped.append(os.path.relpath(os.path.join(base, f), root))
                continue
            got, err = scan_file(os.path.join(base, f), root)
            if err:
                problems.append(err)
            else:
                rows += got
    return rows, problems, skipped


def summarise(rows):
    out = {}
    for k in (LIVE, TEST, CITATION):
        sel = [r for r in rows if r["klass"] == k]
        out[k] = {"occurrences": len(sel),
                  "distinct_values": len({r["value"] for r in sel}),
                  "files": len({r["file"] for r in sel})}
    return out


def baseline(rows):
    """The diffable shape: class (a) only, keyed by where it is.

    Only class (a), because (b) and (c) are supposed to churn -- prose gets
    written and test expectations get updated -- and a baseline that reddens on
    those is a baseline nobody will keep running.
    """
    return sorted(
        ({"file": r["file"], "symbol": r["symbol"], "value": r["value"],
          "kind": r["kind"]}
         for r in rows if r["klass"] == LIVE),
        key=lambda r: (r["file"], r["value"], r["symbol"] or ""))


def diff(before, after):
    """(gone, arrived, moved) between two baselines."""
    def key(r):
        return (r["file"], r["symbol"])
    b = {key(r): r for r in before}
    a = {key(r): r for r in after}
    gone = [b[k] for k in sorted(b.keys() - a.keys())]
    arrived = [a[k] for k in sorted(a.keys() - b.keys())]
    moved = [(b[k], a[k]) for k in sorted(b.keys() & a.keys())
             if b[k]["value"] != a[k]["value"]]
    return gone, arrived, moved


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=HERE, help="tree to scan (default toolkit/)")
    ap.add_argument("--live", action="store_true", help="list class (a) only")
    ap.add_argument("--json", metavar="FILE", help="write a baseline here")
    ap.add_argument("--diff", metavar="BEFORE", help="compare against a baseline")
    a = ap.parse_args(argv)

    rows, problems, skipped = scan(a.root)
    for p in problems:
        print(f"  UNREADABLE: {p}", file=sys.stderr)

    s = summarise(rows)
    print(f"root: {a.root}")
    if skipped:
        print(f"  (not scanned, the instrument itself: {', '.join(skipped)})")
    print(f"  (a) live constants   {s[LIVE]['occurrences']:5d} occurrence(s), "
          f"{s[LIVE]['distinct_values']:4d} distinct, "
          f"{s[LIVE]['files']:3d} file(s)   <- the liability")
    print(f"  (b) prose citations  {s[CITATION]['occurrences']:5d} occurrence(s), "
          f"{s[CITATION]['distinct_values']:4d} distinct, "
          f"{s[CITATION]['files']:3d} file(s)   provenance, wanted")
    print(f"  (c) test expectations{s[TEST]['occurrences']:5d} occurrence(s), "
          f"{s[TEST]['distinct_values']:4d} distinct, "
          f"{s[TEST]['files']:3d} file(s)   red on a new build is correct")

    if a.live:
        print()
        for r in sorted((r for r in rows if r["klass"] == LIVE),
                        key=lambda r: (r["file"], r["line"])):
            print(f"  {r['file']}:{r['line']:<5d} {r['text']:<12} "
                  f"{r['kind']:<14} {r['symbol']}")

    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"baseline": baseline(rows)}, fh, indent=1)
        print(f"\nbaseline written: {a.json} "
              f"({len(baseline(rows))} class-(a) site(s))")

    if a.diff:
        with open(a.diff, encoding="utf-8") as fh:
            before = json.load(fh)["baseline"]
        gone, arrived, moved = diff(before, baseline(rows))
        print(f"\nvs {a.diff}: {len(gone)} gone, {len(arrived)} new, "
              f"{len(moved)} changed value")
        for r in gone:
            print(f"  GONE    {r['file']} {r['symbol']} {r['value']:#x}")
        for r in arrived:
            print(f"  NEW     {r['file']} {r['symbol']} {r['value']:#x}")
        for b, c in moved:
            print(f"  MOVED   {b['file']} {b['symbol']} "
                  f"{b['value']:#x} -> {c['value']:#x}")
        # A changed baseline is a RESULT, not an error -- the same distinction
        # `datcheck.py --diff` draws, and for the same reason.
        return 1 if (gone or arrived or moved) else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
