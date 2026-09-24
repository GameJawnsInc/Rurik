"""Proves `toolkit/checks.py` can go red, by breaking each of its rules on purpose.

This is the check on the checker. Every other test in the toolkit now routes its
verdict through `Ledger.verdict()`, so if that function cannot fail, nothing below it
can either -- and the failure would look exactly like a green suite.

Note the shape: each case constructs a run that SHOULD be refused and asserts the exit
code is non-zero. The negative cases (a genuinely complete run) are here too, because a
guard that reddens everything is just as useless as one that reddens nothing -- it gets
switched off within the week.

  python toolkit/test_checks.py
"""
import contextlib
import io
import re
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import checks  # noqa: E402


def run(build):
    """Drive a Ledger through `build`, capturing its output. Returns (code, text)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = build()
    return code, buf.getvalue()


def main():
    led = checks.Ledger("checks.py itself", floor=20)

    # --- the rule that would have caught test_codec.py in 2026-08 ---------------
    def empty():
        return checks.Ledger("empty run", floor=1).verdict()
    code, text = run(empty)
    led.ok(code != 0, "a run with zero checks is refused", f"exit={code}")
    led.ok("NO CHECKS RAN" in text,
           "and the banner says so rather than printing a pass")
    led.ok("ALL CHECKS PASSED" not in text,
           "a zero-check run never prints ALL CHECKS PASSED")

    # --- the rule that would have caught test_movement_fidelity.py -------------
    # Two passing checks, a declared skip, and a floor of three: exactly the shape
    # that printed green on 2026-08-06.
    def partial():
        p = checks.Ledger("partial run", floor=3)
        p.ok(True, "median drift under limit")
        p.ok(True, "accept rate over floor")
        p.skip("run speed", "only 0 straight-run samples; need 10")
        return p.verdict()
    code, text = run(partial)
    led.ok(code != 0,
           "a run that passes every check it ran but misses its floor is refused",
           f"exit={code}")
    led.ok("FLOOR" in text.upper(),
           "and the banner names the shortfall, not just 'failed'")

    # --- skips are never silent -------------------------------------------------
    def skipped():
        p = checks.Ledger("skip visibility", floor=1)
        p.ok(True, "the one mandatory check")
        p.skip("optional section", "fixture absent")
        return p.verdict()
    code, text = run(skipped)
    led.ok(code == 0,
           "a complete run with a declared skip still passes", f"exit={code}")
    led.ok("not measured this run" in text,
           "but the skip is printed in the verdict, not swallowed")

    # --- a real failure is still a failure --------------------------------------
    def failing():
        p = checks.Ledger("failing run", floor=1)
        p.ok(False, "a check that is false")
        return p.verdict()
    code, _ = run(failing)
    led.ok(code != 0, "a failed check is refused", f"exit={code}")

    # --- and the guard does not redden a healthy run -----------------------------
    def healthy():
        p = checks.Ledger("healthy run", floor=2)
        p.ok(True, "one")
        p.ok(True, "two")
        return p.verdict()
    code, text = run(healthy)
    led.ok(code == 0 and "ALL CHECKS PASSED" in text,
           "a run that meets its floor with no failures passes", f"exit={code}")

    # A floor below 1 is a programming error, not a policy choice.
    try:
        checks.Ledger("bad", floor=0)
        raised = False
    except ValueError:
        raised = True
    led.ok(raised, "a floor of 0 is rejected at construction")

    # --- and the suite list is the suite ----------------------------------------
    # TESTS.md IS the definition of "run the tests" (it was CLAUDE.md's pre-flight
    # list until 2026-08-14, when the catalog was split out). A test in
    # the tree but not on the list is one nobody runs: test_pathmap.py,
    # test_skillcast.py and test_textrec.py were each off it for days while
    # passing, which is the same failure as a green vacuous test one level up.
    # Enforced here rather than asserted in prose, per the house rule that a law
    # in a docstring is a wish.
    tree, named = suite_on_disk(), suite_in_docs()
    missing = sorted(tree - named)
    phantom = sorted(named - tree)
    led.ok(not missing, "every test in the tree is named in TESTS.md",
           f"unlisted: {', '.join(missing)}" if missing else f"{len(tree)} tests")
    led.ok(not phantom, "every test the docs name still exists",
           f"missing from tree: {', '.join(phantom)}" if phantom else "")

    # --- the top-level documents point at things that exist ---------------------
    # PLAN.md §3 is now the single status authority and stamps each landed rung with
    # a commit hash, and §3.2 grades R4b/R4c against a manifest. Both are claims that
    # rot silently: a hash typo or a renamed study leaves a document confidently
    # citing nothing. The rule is only worth writing down if something checks it.
    dangling = broken_doc_links()
    led.ok(not dangling, "every repo-relative link in the top-level docs resolves",
           "; ".join(f"{d}: {t}" for d, t in dangling[:4]) if dangling else "")

    bad_hashes = unresolvable_hashes()
    if bad_hashes is None:
        led.skip("commit stamps", "git not available to resolve them")
    else:
        led.ok(not bad_hashes,
               "every commit hash PLAN.md §3 stamps a rung with resolves",
               ", ".join(bad_hashes) if bad_hashes else "")

    # --- and section 8 stays a list of what is OPEN -------------------------------
    # Until 2026-09-17 PLAN.md section 8 was 226 closed entries and 1,113 KB of a
    # 1,402 KB file: every landing prepended an entry and nothing ever left, so the
    # document CLAUDE.md tells each session to read had grown past what any reader
    # holds (`Read` stops at 2,000 lines of 12,110, silently). The entries moved to
    # PLAN-LOG.md. A rule that says "write the landing in the log" is a wish unless
    # something reddens when the landing is written in section 8 instead, so: a byte
    # ceiling. When this fires, MOVE closed entries to the log; raising the number
    # is how the last 1.1 MB happened, one reasonable entry at a time.
    size = plan_section_bytes(read_plan(), "8")
    led.ok(size is not None and size >= SECTION8_FLOOR,
           "PLAN.md section 8 is found and is not empty",
           f"{size} bytes" if size is not None else "no `## 8.` heading -- a renamed "
           "heading would make the ceiling below pass on nothing")
    led.ok(size is not None and size <= SECTION8_CEILING,
           f"and it is under {SECTION8_CEILING:,} bytes -- open items, not a log",
           (f"{size:,} bytes" + ("; MOVE what has landed to PLAN-LOG.md, do not "
                                 "raise the number" if size > SECTION8_CEILING else ""))
           if size else "")
    # CONTROL, both directions, on synthetic text so it cannot rot with the document:
    # the measurer must see a bloated section 8 as bloated, and must stop at the next
    # H2 rather than swallow it.
    fat = ("## 7. Q\nq\n## 8. Immediate next actions\n" + "x" * 90000
           + "\n## 9. Z\nz\n")
    led.ok(plan_section_bytes(fat, "8") == 90001
           and plan_section_bytes(fat, "8") > SECTION8_CEILING
           and plan_section_bytes(fat, "9") == 2
           and plan_section_bytes(fat, "6") is None,
           "CONTROL: the measurer sizes one section, to the next H2, and says None "
           "for a section that is not there")

    # --- and PLAN.md 3.2's content counts are the loader's, not a transcription ---
    # DESKWORK-D12 step 4's first half (2026-09-24). Section 3.2 grades R4c-1 on a
    # census of the content store, and that census went stale twice while the prose
    # around it was re-read: "map 10, npc 56" stood on 2026-08-27 while content.py
    # read map 15, and "map 15, npc 56" stood until 2026-09-24 against map 19, npc
    # 63. So the TRACKED half of the census -- content/*.toml and content/overrides/,
    # no vault -- is quoted behind one marker and recomputed here. Only the tracked
    # half: the vault overlay is machine state (a bare machine has none; a tree that
    # lags main drops label rows it does not know), so a check on it would redden on
    # the machine, not on the document. Which kinds are checked is whatever the
    # marker quotes; today map and npc, the two R4c-1 grades on.
    quoted = census_quote(plan_subsection(read_plan(), "3.2"))
    led.ok(bool(quoted) and "map" in quoted and "npc" in quoted,
           "PLAN.md 3.2 quotes the tracked content census (map and npc at least)",
           f"quoted {quoted}" if quoted else "no `The tracked census ...: kind N, ...` in "
           "3.2 -- a reworded marker would make the next check pass on nothing")
    tracked = tracked_census()
    wrong = census_contradictions(quoted or {}, tracked)
    led.ok(bool(quoted) and not wrong,
           "and every count it quotes is what content.py loads from the tree today",
           "; ".join(f"{k}: 3.2 says {q}, content.py loads {t}" for k, q, t in wrong)
           + ("; UPDATE PLAN.md 3.2 (and date it), do not loosen this" if wrong else ""))
    # CONTROL on synthetic text, so it cannot rot with the document: the known-bad
    # quote (the "map 15" 3.2 carried for four weeks) is caught, the right one is
    # not, a kind the loader lacks is caught, a missing marker reads as None, and
    # the parser stops at the section's end rather than reading 3.3's numbers.
    fx = ("## 3. L\n### 3.2 R4b and R4c\nx **The tracked census** (`content/*.toml`\n"
          "alone): map 15,\nnpc 9. More prose, npc 70.\n### 3.3 Next\nThe tracked census "
          "(y): map 99.\n")
    got = census_quote(plan_subsection(fx, "3.2"))
    led.ok(got == {"map": 15, "npc": 9}
           and census_contradictions(got, {"map": 19, "npc": 9}) == [("map", 15, 19)]
           and census_contradictions({"map": 19, "npc": 9}, {"map": 19, "npc": 9}) == []
           and census_contradictions({"ghost": 1}, {"map": 19}) == [("ghost", 1, None)]
           and census_quote("### 3.2 R\nmap 19, npc 9\n") is None
           and plan_subsection(fx, "3.4") is None,
           "CONTROL: a 3.2 quoting map 15 against a loader reading 19 is caught; the "
           "marker spans a line break, stops at its own list, and 3.3's numbers are "
           "never read")

    return led.verdict()


# Set from the real document on 2026-09-17, the day of the split, with room for
# a busy week's open items -- NOT room for a changelog.
SECTION8_CEILING = 40_000
SECTION8_FLOOR = 500


def read_plan():
    path = os.path.join(repo_root(), "PLAN.md")
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def plan_section_bytes(text, number):
    """UTF-8 bytes of `## <number>.`'s body, up to the next H2 or the end. None if absent."""
    m = re.search(rf"^## {re.escape(number)}\.[^\n]*\n", text, re.M)
    if not m:
        return None
    nxt = re.search(r"^## ", text[m.end():], re.M)
    body = text[m.end():m.end() + nxt.start()] if nxt else text[m.end():]
    return len(body.encode("utf-8"))


def plan_subsection(text, number):
    """The body of `### <number> ...`, up to the next H2 or H3. None if absent."""
    m = re.search(rf"^### {re.escape(number)} [^\n]*\n", text, re.M)
    if not m:
        return None
    nxt = re.search(r"^#{2,3} ", text[m.end():], re.M)
    return text[m.end():m.end() + nxt.start()] if nxt else text[m.end():]


# `The tracked census (<anything without a colon>): kind N, kind N.` -- the first
# such marker in the text. The list may wrap across lines; it ends at the first
# item that is not `word number`.
CENSUS_MARKER = re.compile(r"The tracked census\**[^:]*:\s*"
                           r"((?:[a-z_]+ \d+)(?:,\s*[a-z_]+ \d+)*)")


def census_quote(section):
    """{kind: count} the marker quotes, or None when there is no marker."""
    if not section:
        return None
    m = CENSUS_MARKER.search(section)
    if not m:
        return None
    pairs = re.findall(r"([a-z_]+) (\d+)", m.group(1))
    return {k: int(n) for k, n in pairs}


def census_contradictions(quoted, census):
    """[(kind, quoted, loaded)] for every quoted count the census does not match
    (loaded is None for a kind the loader does not have)."""
    return [(k, q, census.get(k)) for k, q in sorted(quoted.items())
            if census.get(k) != q]


def tracked_census():
    """content.py's census of the TREE's rows alone: no vault overlay, no
    RURIK_CONTENT_EXTRA -- the half of the store a document can be held to."""
    import tempfile
    import content
    with tempfile.TemporaryDirectory() as empty:
        return content.load(vault_dir=empty, extra_dirs=[]).census()


TOP_DOCS = ("CLAUDE.md", "PLAN.md", "PLAN-LOG.md", "RUNBOOK.md", "HANDOFF.md", "TESTS.md")


def broken_doc_links():
    """(doc, target) for every markdown link to a repo path that does not exist."""
    root = repo_root()
    out = []
    for doc in TOP_DOCS:
        path = os.path.join(root, doc)
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        for target in re.findall(r"\]\(([^)#\s]+)\)", text):
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            if not os.path.exists(os.path.join(root, target.split("#")[0])):
                out.append((doc, target))
    return out


def unresolvable_hashes():
    """Short hashes PLAN.md §3 cites that git cannot resolve. None if no git."""
    import subprocess
    root = repo_root()
    path = os.path.join(root, "PLAN.md")
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    section = text[text.find("## 3. The revised ladder"):text.find("## 4.")]
    # Backticked 7-to-10 hex words. Long enough not to catch `0x1B97D` or a year.
    candidates = set(re.findall(r"`([0-9a-f]{7,10})`", section))
    if not candidates:
        return []
    bad = []
    for h in sorted(candidates):
        try:
            r = subprocess.run(["git", "-C", root, "cat-file", "-t", h],
                               capture_output=True, text=True, timeout=15)
        except (OSError, subprocess.SubprocessError):
            return None
        if r.returncode != 0 or r.stdout.strip() != "commit":
            bad.append(h)
    return bad


def repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def suite_on_disk():
    """Every test_*.py under toolkit/, as repo-relative posix paths."""
    root = repo_root()
    out = set()
    for base, dirs, files in os.walk(os.path.join(root, "toolkit")):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            if f.startswith("test_") and f.endswith(".py"):
                rel = os.path.relpath(os.path.join(base, f), root)
                out.add(rel.replace(os.sep, "/"))
    return out


def suite_in_docs():
    """Every toolkit test path the house documents name.

    BOTH files since 2026-08-14, when the catalog moved to TESTS.md (it had
    reached 90% of CLAUDE.md). Not TESTS.md alone: `test_handshake.py` is named
    only inside CLAUDE.md's code fence, so a scan of the catalog by itself is
    short by exactly that one.
    """
    out = set()
    for name in ("TESTS.md", "CLAUDE.md"):
        path = os.path.join(repo_root(), name)
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as fh:
                out |= set(re.findall(r"toolkit/[\w/]*test_\w+\.py", fh.read()))
    return out


if __name__ == "__main__":
    sys.exit(main())
