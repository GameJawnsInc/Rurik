#!/usr/bin/env python3
"""`citelint.py`, and the one document whose citations are ruled on rather than counted.

    python toolkit/test_citelint.py

WHAT THIS IS REALLY CHECKING. Study documents cite source locations as
`movetap.py:3049`, and nothing checked them, so they rotted silently: measured
2026-08-29, roughly 25 of `studies/movement/PROBE-GATEFIRE.md`'s ~30 citations pointed
at the wrong line. All eight of its `movesync.py` citations were stale UNDER A GREEN
sha256 PIN -- the pin says `movesync.py` has not moved since it was taken, which is
true and says nothing at all about citations that were already wrong when it was taken.

The citations were deliberately not swept at the time, and that call was right: a sweep
with no checker behind it buys a few days and this repo has already paid once for the
eager version (`test_provlint.py`'s header: 46 citations rewritten, all 46 reverted).
So the checker came first and the sweep came second, in that order and in one commit.

TWO POSTURES, ON PURPOSE, because they are two different problems.

  * `studies/movement/PROBE-GATEFIRE.md` is RULED ON. Zero red, no headroom. It is the
    document that was measured, it has been swept, and section 6 holds it there.
  * EVERY OTHER `studies/**/*.md` is COUNTED, with a ceiling and real headroom
    (section 8). 142 of its citations are red today and a checker that goes red on all
    of them is one nobody leaves switched on -- the lesson `test_provlint.py` and
    `test_seclint.py` both record from opposite directions. The ceiling catches a
    wholesale regression; it does not demand a 142-citation sweep at 2am.

WHAT IS NOT COVERED, said plainly so a green run is not over-read. Only `studies/`;
`CLAUDE.md`, `RUNBOOK.md`, `TESTS.md`, `PLAN.md` and `HANDOFF.md` carry citations too
and are outside this. Line numbers only -- nothing here checks that the cited code
says what the document claims. And the corpus count in section 8 includes some parser
noise (a backticked commit sha reading as a symbol), which is a further reason it is a
ceiling and not a zero. `citelint.py`'s own header carries the rest of the limits.

HOW THIS GOES RED, and section 7 proves it rather than asserting it. A scratch copy of
the real document has ONE citation's line number moved by one, and the run asserts the
verdict flips to `symbol-elsewhere`, that the report names the document, the document
line, the symbol, the lines the symbol is really on AND which of those is its
definition, and that the red count rises by exactly one and no more. A checker whose
failure has never been seen is the kind of thing `checks.py` exists to complain about.

AND HOW IT CANNOT SILENTLY FIND NOTHING. Section 5 pins three named citations from the
real document to their expected verdicts, including two that must come back
`ok-symbol`. A resolver that matched nothing, or that degraded every symbol to a
line-exists check, would fail section 5 while every "no red found" check in sections 6
and 8 sailed through green. That is the vacuity hole in every linter of this shape and
it is the reason those three are written down.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import checks      # noqa: E402
import citelint    # noqa: E402

ROOT = os.path.dirname(HERE)
PILOT = "studies/movement/PROBE-GATEFIRE.md"

# MEASURED from a real green run on 2026-08-30 in the worktree
# `.claude/worktrees/keen-pare-c3af01` at HEAD 22bfe86: **50 checks**, read off
# `python toolkit/test_citelint.py` and not counted in anyone's head. Every section
# runs off files in git -- no vault, no socket, no client -- so there is no
# bare-machine subset, no optional section and no declared skip, and the floor is the
# whole run rather than a mandatory core.
#
# 45 is also reachable and is NOT the floor: section 7's five report-content checks
# sit behind `if hit`, so a perturbation the scanner failed to catch would drop them.
# That run also FAILS on the check above them, which is the intended behaviour --
# the floor is not what makes it red, it is the second line of defence.
LEDGER = checks.Ledger("source citations in study prose resolve at HEAD", floor=50)
check = checks.adopt(LEDGER)


def say(text):
    """print(), but a console that cannot encode a character never kills the run."""
    try:
        print(text)
    except UnicodeEncodeError:
        enc = sys.stdout.encoding or "ascii"
        print(text.encode(enc, "backslashreplace").decode(enc, "replace"))


def head(title):
    say("\n" + title)
    say("-" * len(title))


# --------------------------------------------------------------------------
# CITATIONS THE PILOT DOCUMENT IS ALLOWED TO LEAVE STALE
# --------------------------------------------------------------------------
# A document sometimes cites a location IN ORDER TO SAY IT IS DEAD. Those must not be
# swept -- rewriting them would destroy the claim -- and they must not be silently
# tolerated either, so each is named here with the sentence that makes it deliberate.
# Checked in BOTH directions by section 6: a new red fails, and an entry the scanner
# no longer produces fails too, because a stale exemption reads as coverage that is
# not there. Keyed on (document, citation text) rather than on a document line, so an
# edit elsewhere in the file does not invalidate the entry.
HISTORICAL = {
    (PILOT, "movesync.py:602-606"):
        "C4's row: 'The old `tested = sum(...)` at `movesync.py:602-606` no longer "
        "exists.' The citation IS the claim -- it names where the deleted code used "
        "to be. Fixing the number would assert the opposite of what the row says.",
}

# --------------------------------------------------------------------------
# POSITIVE CONTROLS -- named citations, their expected verdicts, and why
# --------------------------------------------------------------------------
# Two must resolve at the SYMBOL tier and one at the LINE tier. Without these, a
# resolver that silently matched nothing would leave sections 6 and 8 green.
CONTROLS = [
    (PILOT, "movetap.py:1481", "ok-symbol", "SELFTEST_FLOOR",
     "`SELFTEST_FLOOR` at `movetap.py:1481` -- was `:1469` until 3e7ed3a2 "
     "(MOVECODE-1z-cb, 2026-09-05) inserted twelve lines at `movetap.py:460` and "
     "moved every citation below it; the document was re-pointed with it on "
     "2026-09-07, and this control MUST move with the document, because it names "
     "the citation text and a stale one has zero hits. The check that proves the "
     "symbol tier fires at all"),
    (PILOT, "movesync.py:2759", "ok-symbol", "SELFTEST_FLOOR",
     "the SECOND citation in `(`SELFTEST_FLOOR` at `movetap.py:1481` and "
     "`movesync.py:2759`)`. It only resolves because `pair_symbol` erases an "
     "intervening citation instead of refusing the pairing, so this control is "
     "what stops that rule from being quietly removed"),
    (PILOT, "test_movesync.py:125", "ok-line", None,
     "no symbol is adjacent -- the nearest backticked span is a 500-character table "
     "cell away -- so the only claim is that the line exists, and that is all this "
     "asserts. The control that proves the degraded tier is reachable and green"),
]


def by_cite(cites):
    """(citation text) -> [Citation], for looking a named control up."""
    out = {}
    for c in cites:
        out.setdefault(c.cite, []).append(c)
    return out


def main():
    say(__doc__.strip().splitlines()[0])
    say("=" * 78)

    index = citelint.index_sources(ROOT)
    pilot_text = open(os.path.join(ROOT, PILOT), encoding="utf-8").read()
    pilot = citelint.scan_text(pilot_text, PILOT, ROOT, index)

    # ---- 1. the citation pattern ------------------------------------------
    head("1. what is and is not a citation")
    # The corpus is built out of colon-number pairs that are not citations, so the
    # negative controls here are load-bearing in exactly the way `provlint.py`'s
    # section 3 is: a checker that fires on ordinary prose is one nobody leaves on.
    POS = [
        ("`movetap.py:3049`", "movetap.py", 3049, None),
        ("(`movetap.py:2688-2692`)", "movetap.py", 2688, 2692),
        ("see toolkit/authsrv/agents.py:118 for it", "agents.py", 118, None),
        ("bare movesync.py:12 in prose", "movesync.py", 12, None),
    ]
    for text, mod, lo, hi in POS:
        m = citelint.CITE.search(text)
        check(m is not None and m.group(2) == mod
              and int(m.group(3)) == lo
              and (int(m.group(4)) if m.group(4) else None) == hi,
              f"reads {text.strip()!r} as {mod}:{lo}" + (f"-{hi}" if hi else ""),
              f"got {m.groups() if m else None}")
    NEG = [
        ("Build: 38797", "a colon-number pair that is not a location"),
        ("`a-movetap.py:12`", "a hyphenated word ending in a module name"),
        ("`x.pyc:12`", "not a .py file"),
        ("run at 2026-08-29:14 today", "a timestamp"),
    ]
    for text, why in NEG:
        check(citelint.CITE.search(text) is None,
              f"refuses {text!r} -- {why}",
              f"matched {citelint.CITE.search(text).group(0)!r}"
              if citelint.CITE.search(text) else "")

    # A citation inside a fenced block is a reproduction of tool output, not a claim.
    fenced = "prose `a.py:1` here\n\n```\ntraceback at b.py:99\n```\n\nmore `c.py:3`\n"
    got = [m.group(2) for para, _n in citelint.paragraphs(fenced)
           for m in citelint.CITE.finditer(para)]
    check(got == ["a.py", "c.py"],
          "skips citations inside fenced code blocks",
          "" if got == ["a.py", "c.py"] else f"got {got}, wanted ['a.py', 'c.py']")

    # ---- 2. the adjacency rule --------------------------------------------
    head("2. when a backticked span is the citation's symbol")

    def paired(text):
        """(symbol, gap) for the FIRST citation in a one-paragraph text."""
        para = next(iter(citelint.paragraphs(text)))[0]
        ticks = list(citelint.TICK.finditer(para))
        m = citelint.CITE.search(para)
        own = next((t for t in ticks
                    if t.start() <= m.start() and m.end() <= t.end()), None)
        return citelint.pair_symbol(para, ticks, own.start() if own else m.start())

    check(paired("`fence_verdict` at `movetap.py:3049`")[0] == "fence_verdict",
          "pairs across ` at `", str(paired("`fence_verdict` at `movetap.py:3049`")))
    check(paired("`REACH_ALIASES`, `movesync.py:592`")[0] == "REACH_ALIASES",
          "pairs across `, `")
    # The hard-wrap case. A same-line reader misses this and passes the citation on
    # line-exists; two real defects in the pilot document hide exactly here.
    check(paired("`sep` is written at\n`movetap.py:791`, and")[0] == "sep",
          "pairs across a hard-wrapped newline")
    # One symbol, a LIST of citations: the second must still pair.
    two = "(`SELFTEST_FLOOR` at `movetap.py:1481` and `movesync.py:2759`)"
    para = next(iter(citelint.paragraphs(two)))[0]
    ticks = list(citelint.TICK.finditer(para))
    second = list(citelint.CITE.finditer(para))[1]
    owner = next(t for t in ticks
                 if t.start() <= second.start() and second.end() <= t.end())
    check(citelint.pair_symbol(para, ticks, owner.start())[0] == "SELFTEST_FLOOR",
          "an intervening citation is erased, so a citation LIST shares one symbol")
    NOT_PAIRED = [
        ("`grep -i white` returns exactly one hit and it is a comment, `movetap.py:2610`",
         "a long gap"),
        ("`len(seq)-1`. The old row's cited site `movetap.py:968`",
         "a full stop between them"),
        ("`foo` at `a.py:1`. Also see `b.py:2`",
         "punctuation survives the citation erasure"),
    ]
    for text, why in NOT_PAIRED:
        got = (paired(text)[0] if "Also see" not in text
               else citelint.pair_symbol(
                   next(iter(citelint.paragraphs(text)))[0],
                   list(citelint.TICK.finditer(text)),
                   list(citelint.CITE.finditer(text))[-1].start() - 1)[0])
        check(got is None, f"refuses to pair over {why}", f"paired {got!r}")

    # ---- 3. which identifier a span is about ------------------------------
    head("3. the primary symbol of a backticked span")
    SYM = [
        ("movetap.fence_verdict(reach, flips)", "movetap.py", "fence_verdict",
         "the module qualifier is stripped when it names the cited file"),
        ("os.path.getmtime(p)", "movesync.py", "os",
         "and is NOT stripped when it does not"),
        ("UNREAD_REFUSE_SHARE = 0.25", "movesync.py", "UNREAD_REFUSE_SHARE",
         "an assignment yields its left side"),
        ("GATE1_ABOVE, GATE1_BELOW", "movetap.py", "GATE1_ABOVE",
         "a list yields its first"),
        ("not fence_verdict(x)", "movetap.py", "fence_verdict",
         "keywords are stepped over"),
        ("0x0056", "agents.py", None,
         "a hex literal is not the identifier `x0056`"),
        ("gwdat.py", "pathmap.py", None, "a bare file reference names no symbol"),
        ("toolkit/mapdata/deploy.py", "deploy.py", None,
         "and neither does a path"),
    ]
    for span, mod, want, why in SYM:
        got = citelint.primary_symbol(span, mod)
        check(got == want, f"`{span}` -> {want!r} -- {why}", f"got {got!r}")

    # ---- 4. every verdict, over a fixture whose contents are known --------
    head("4. resolution, one fixture per verdict")
    # A synthetic source file so each verdict is produced by construction rather
    # than found in the tree, where it could stop occurring at any time.
    fixture = "toolkit/citelint.py"          # 400+ lines, and it is us
    src = citelint.source_lines(ROOT, fixture)
    green_line = next(n for n, line in enumerate(src, 1) if "MAX_GAP = " in line)
    VERDICTS = [
        (f"`MAX_GAP` at `citelint.py:{green_line}`", "ok-symbol",
         "the symbol is on the cited line"),
        (f"a note about the parser (`citelint.py:{green_line}`)", "ok-line",
         "no symbol adjacent, and the line exists"),
        (f"`MAX_GAP` at `citelint.py:{green_line + 3}`", "symbol-elsewhere",
         "the symbol is in the file, on other lines"),
        ("`no_such_name_anywhere` at `citelint.py:5`", "symbol-absent",
         "the symbol is nowhere in that file"),
        (f"`MAX_GAP` at `citelint.py:{len(src) + 500}`", "out-of-range",
         "the file is not that long"),
        ("`Sniffer` at `PacketSniffer.py:41`", "not-in-repo",
         "an upstream file, which is not ours to resolve"),
        ("`hook` at `autoinject.py:10`", "ambiguous",
         "two files share the basename, and this refuses to pick"),
        ("`MAX_GAP` at `toolkit/nope/citelint.py:1`", "wrong-path",
         "the path is wrong but the file exists elsewhere"),
    ]
    for text, want, why in VERDICTS:
        got = citelint.scan_text(text, "FIXTURE.md", ROOT, index)
        check(len(got) == 1 and got[0].verdict == want,
              f"{want:<17} -- {why}",
              f"got {[(c.cite, c.verdict) for c in got]}")
    # A range passes when the symbol is anywhere inside it, and only then.
    rng = citelint.scan_text(
        f"`MAX_GAP` at `citelint.py:{green_line - 2}-{green_line + 2}`",
        "FIXTURE.md", ROOT, index)
    check(rng and rng[0].verdict == "ok-symbol",
          "a line RANGE passes when the symbol is inside it",
          f"got {[(c.cite, c.verdict) for c in rng]}")

    # ---- 5. positive controls on the real document ------------------------
    head("5. named citations that must resolve (the vacuity guard)")
    found = by_cite(pilot)
    for doc, cite, want, sym, why in CONTROLS:
        hits = found.get(cite, [])
        ok = len(hits) == 1 and hits[0].verdict == want and hits[0].symbol == sym
        check(ok, f"{cite} is {want} (symbol {sym!r})",
              "" if ok else f"got {[(c.verdict, c.symbol) for c in hits]} -- {why}")
    # And the tiers are not degenerate: if every citation degraded to `ok-line`,
    # sections 6 and 8 would still pass and this document would be unchecked.
    tiers = citelint.tally(pilot)
    n_sym = tiers.get("ok-symbol", 0)
    check(n_sym >= 2,
          f"at least 2 citations resolve at the SYMBOL tier "
          f"(got {n_sym} of {len(pilot)})",
          "" if n_sym >= 2 else
          "every symbol degraded to a line-exists check; the document is not "
          "covered even though nothing is red")

    # ---- 6. the ruled-on document -----------------------------------------
    head("6. PROBE-GATEFIRE.md: every citation resolves, or is a named historical one")
    red = [c for c in pilot if c.red]
    unexpected = [c for c in red if (c.doc, c.cite) not in HISTORICAL]
    check(not unexpected,
          f"{len(pilot)} citations in {PILOT}, {len(unexpected)} unexplained red",
          "; ".join(f"{c.doc}:{c.line} {c.cite} {c.verdict} -- {c.detail}"
                    for c in unexpected[:6]))
    # The reverse direction. An exemption the scanner no longer produces reads as
    # coverage that is not there -- the same defect as a missing one, from the
    # other side, and the shape `test_srclint.py` 7 checks on the suite list.
    live = {(c.doc, c.cite) for c in red}
    stale = sorted(k for k in HISTORICAL if k not in live)
    check(not stale,
          f"and all {len(HISTORICAL)} historical exemption(s) still fire",
          f"STALE: {stale} -- the citation was fixed or removed; delete the entry"
          if stale else "")

    # ---- 7. the red proof -------------------------------------------------
    head("7. moving one citation by one line reddens it, and names it")
    # The whole file is worth nothing if this cannot fail. So: take the real
    # document, move ONE known-green citation's line number by one, and require the
    # scanner to catch it, name it, and catch nothing else.
    ctrl = CONTROLS[0][1]                      # `movetap.py:1481`, ok-symbol
    mod, lineno = ctrl.split(":")
    moved = f"{mod}:{int(lineno) + 1}"
    scratch = pilot_text.replace(f"`{ctrl}`", f"`{moved}`")
    check(scratch != pilot_text, f"the scratch copy actually changed {ctrl}")
    hurt = citelint.scan_text(scratch, "SCRATCH-" + PILOT, ROOT, index)
    hit = [c for c in hurt if c.cite == moved]
    check(len(hit) == 1 and hit[0].verdict == "symbol-elsewhere",
          f"{ctrl} -> {moved} is caught as symbol-elsewhere",
          f"got {[(c.cite, c.verdict) for c in hit]}")
    if hit:
        report = f"{hit[0].doc}:{hit[0].line} {hit[0].cite} {hit[0].detail}"
        check("PROBE-GATEFIRE.md" in report, "the failure names the DOCUMENT", report)
        check(f":{hit[0].line}" in report and hit[0].line > 1,
              f"and the document LINE ({hit[0].line})", report)
        check(f"`{CONTROLS[0][3]}`" in report,
              f"and the SYMBOL (`{CONTROLS[0][3]}`)", report)
        check(f"{mod}:{lineno}" in report,
              f"and where the symbol really is ({mod}:{lineno})", report)
        # The corrected number is almost always the DEFINITION, and it must be the
        # first one offered. `fence_verdict`'s def is the 25th of its 25 occurrences
        # in `movetap.py`; a report leading with four call sites makes the operator
        # do the search the tool just did, and a sweep that is not cheap does not
        # happen.
        check(f"{lineno}(def)" in report,
              f"and names it as the DEFINITION, first ({lineno}(def))", report)
    check(sum(1 for c in hurt if c.red) == len(red) + 1,
          f"exactly one new red, not a cascade "
          f"({sum(1 for c in hurt if c.red)} vs {len(red)} baseline)")

    # ---- 8. the rest of studies/: a tripwire, not a gate -------------------
    head("8. every other studies/ document: accumulation ceiling")
    corpus = citelint.scan_tree(ROOT)
    docs = {c.doc for c in corpus}
    others = [c for c in corpus if c.doc != PILOT]
    # Vacuity first. A walk that found nothing would make every count below pass.
    enough = len(docs) >= 40 and len(corpus) >= 500
    check(enough,
          f"the walk read {len(corpus)} citations across {len(docs)} documents",
          "" if enough else
          "far below the 727 measured 2026-08-30; the walk is finding nothing")
    check(PILOT in docs, f"and {PILOT} is among them")
    other_red = sum(1 for c in others if c.red)
    # BASELINE 142, measured 2026-08-30 after the pilot sweep. The ceiling is 210,
    # the same ~1.5x headroom `test_provlint.py` used for 134->200 and
    # `test_identlint.py` for 53->80 -- not a new rule. The headroom is wider than
    # it looks necessary because this count is VOLATILE by construction: one commit
    # inserting lines near the top of `agents.py` can move every citation of it at
    # once, so a tight bar would fire on ordinary work and get lowered in irritation.
    # These 142 are NOT a fix list. Raising the ceiling when it fires is a normal
    # edit; what it must never do is drift without anyone noticing.
    CEILING = 210
    check(other_red <= CEILING,
          f"{other_red} red citations outside the pilot, ceiling {CEILING}",
          "" if other_red <= CEILING else
          "a lane's worth of rot arrived at once. Run "
          "`python toolkit/citelint.py` and either fix or raise the ceiling "
          "deliberately")
    say(f"     (baseline 142 on 2026-08-30; {len(corpus) - len(others)} in the pilot)")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
