"""Prove the provenance-prose checker catches the refused triple, and stays quiet.

`provlint.py` exists because the provenance gate had been enforced on exactly one
side. `toolkit/content.py` refuses an unprovenanced `source = "client-table"` row and
`test_content.py` proves the refusal fires -- but the same ruling's OTHER half, the one
that refuses "verbatim assert expressions with their source path and line", was enforced
by nobody and applied to nothing. Seventeen study documents accumulated assert text
pasted straight out of the crash dialog while the content store was refusing rows.

THREE THINGS ARE TESTED AND THE SECOND IS THE REAL ONE.

  1. It catches all three shapes the drift actually took (section 2).
  2. IT DOES NOT REDDEN AT THE PERMITTED FORMS. The study docs are BUILT out of
     locations, field names, bounds and VAs -- all permitted, all explicitly named in
     the ruling as the constraint we may keep. A checker that flags those is one that
     gets switched off within a day, and switching it off restores the exact silence
     it exists to end. Section 3 is therefore the long one.
  3. The corpus itself, with the un-scrubbed files named and bounded (section 5), so
     the remainder is visible rather than pending.

A NOTE ON WHAT IS NOT TESTED. This checker reads PROSE, so its judgement of "is this
string an expression" is a heuristic and will always have a residual error rate in both
directions. That is acceptable here in a way it would not be for a wire codec: the
consequence of a miss is a line of drift that the next run catches once someone widens
a pattern, and the consequence of a false positive is a rewritten sentence. What is NOT
acceptable is the checker silently reading zero files, so section 5 asserts the corpus
size before it asserts the corpus is clean.

standard library only.

    python toolkit/test_provlint.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import checks  # noqa: E402
import provlint  # noqa: E402

# 19, from a real green run on 2026-08-12.
LEDGER = checks.Ledger("provlint", floor=19)

ROOT = os.path.dirname(HERE)

# Files still carrying the refused triple, MEASURED 2026-08-12 at the counts below.
# These predate the 2026-08-11 ruling and are drift, not defiance -- see the scrub
# note in `studies/agentprops/FINDINGS.md`. The rule here is NOT-GROWING rather than
# an exact match: scrubbing one is progress and must not redden the suite, while a new
# one is the drift resuming and must. Delete a row when its file reaches zero.
BASELINE = {
    os.path.join("studies", "smsg", "FINDINGS.md"): 65,
    os.path.join("studies", "monsterai", "FINDINGS.md"): 12,
    os.path.join("studies", "reconstruction", "FINDINGS.md"): 11,
    os.path.join("studies", "customarea", "FINDINGS.md"): 9,
    os.path.join("studies", "skillcast", "FINDINGS.md"): 7,
}

# The sites scrubbed on 2026-08-12. Each file must now be CLEAN: these are the exact
# documents the drift was found in, so a regression here is the work coming undone.
SCRUBBED = [
    os.path.join("studies", "agentprops", "FINDINGS.md"),
    os.path.join("studies", "cmsg", "FINDINGS.md"),
    os.path.join("studies", "tape", "FINDINGS.md"),
    os.path.join("studies", "enemy", "PLAN.md"),
    os.path.join("studies", "datwrite", "FINDINGS.md"),
    os.path.join("studies", "character", "FINDINGS.md"),
    os.path.join("studies", "mapdata", "FORMAT.md"),
    os.path.join("studies", "review", "FINDINGS.md"),
    os.path.join("studies", "divergence", "FINDINGS.md"),
    os.path.join("studies", "texture", "FINDINGS.md"),
    "PLAN.md",
]


def hits(text, modules=None):
    """Findings in one snippet. Modules are vouched from the snippet unless given."""
    mods = modules if modules is not None else provlint.known_modules([text])
    return provlint.scan_text(text, "<test>", mods)


def main():
    # ---- 1. it runs at all -----------------------------------------------------
    print("1. the checker parses and reports")
    LEDGER.ok(hits("Nothing to see here.\n") == [],
              "a line of ordinary prose reports nothing")

    # ---- 2. THE THREE SHAPES THE DRIFT TOOK ------------------------------------
    print("\n2. every shape found in the tree on 2026-08-12")
    dialog = "Assertion: fraction <= 1.0f      P:\\Code\\Gw\\Char\\CharPool.cpp(84)\n"
    LEDGER.ok(len(hits(dialog)) == 1,
              "the crash-dialog form is caught",
              "studies/agentprops/FINDINGS.md:390 exactly")

    # The location on the NEXT line, which is how the dialog wraps in a fenced block.
    wrapped = ("```\nAssertion: m_attackInterval\n"
               "P:\\Code\\Gw\\AgentView\\AvChar.cpp(4791)\n```\n")
    LEDGER.ok(len(hits(wrapped)) == 1,
              "and when its location wrapped onto the following line",
              "studies/enemy/PLAN.md:1172")

    quoted = '- AgMsg.cpp:513 "index < m_count" -- field 1 is bounds-checked\n'
    LEDGER.ok(len(hits(quoted)) == 1,
              "the `asserts.py --grep` form, expression quoted beside its location",
              "studies/smsg/FINDINGS.md:116")

    bare = ("    (rotation >= -1.0f) && (rotation <= 1.0f)      "
            "P:\\Code\\Gw\\Char\\Cli\\ChCliApi.cpp:5562\n")
    LEDGER.ok(len(hits(bare)) == 1,
              "and the UNQUOTED form inside a fenced block",
              "studies/cmsg/FINDINGS.md:308 -- no `Assertion:` label and no quotes, "
              "so neither of the other two matchers sees it")

    # ---- 3. AND IT STAYS QUIET ON EVERYTHING THE RULING PERMITS ----------------
    print("\n3. the permitted forms are not flagged")
    # Every one of these is named in PLAN.md 7 Q3 as a measurement we may keep, or is
    # something the study docs do constantly. A hit on any of them switches the
    # checker off in practice.
    permitted = {
        "bare path": "The whole archive layer is `P:\\Code\\Base\\Rtl\\Exe\\ExeArchive.cpp`.\n",
        "path with line": "The handler is at `AgMsg.cpp:208`, which we resolved.\n",
        "module:line alone": "Bracketed by ChCliApi:792 .. ChCliApi:4966, so it lives there.\n",
        "field name in prose": "The non-zero bound on `m_attackInterval` at `AvChar.cpp(4791)`.\n",
        "a bound in words": "`ChCliApi.cpp:5562` bounds it to **[-1.0, 1.0]** inclusive.\n",
        "a VA": "The decoder is at **VA 0x007cb000** and its first act is a compare.\n",
        "a struct offset": "`playerFlags` is `+0x2a8`; the flag is bit 1 at `0x008513a7`.\n",
        "a count": "Exactly **888** records validate before the string block at Const.cpp:12.\n",
        "our own disassembly": "`0x0080DFA3 cmp dword ptr [ebp + 0xc], 3` at ChCliApi.cpp:4331\n",
        "a measured payload": "Arg is `[55, agent, 0, 0]` per CharData.cpp:202's layout.\n",
        "upstream citation": "GWCA's `GWCA/Packets/StoC.h:239-247` carries the same field.\n",
        "upstream bare header": "ldufr disambiguates them (`character.h:25` vs `:27`).\n",
        "our own source": "This is `authsrv.py:897-904`, and `toolkit/content.py:31`.\n",
        "a line range": "See `ExeFile:252/253` and `PrApi.cpp:573/574` for the pair.\n",
        "prose with a slash": "The rival reading was `AgAgent:2309` hide / make untargetable.\n",
    }
    noisy = {k: [f.expr for f in got]
             for k, v in permitted.items() if (got := hits(v))}
    LEDGER.ok(not noisy,
              f"none of {len(permitted)} permitted forms is reported",
              "a checker that reddens at the constraint restores the silence it "
              "exists to end" + (f" -- FLAGGED: {noisy}" if noisy else ""))

    # ---- 4. THE VACUITY GUARDS -------------------------------------------------
    print("\n4. the checker cannot be quietly disarmed")
    # `Module:123` is indistinguishable from English prose without a vocabulary, so
    # pass 1 harvests one. If that harvest ever returns everything, `Build: 38797`
    # becomes a source location and the false-positive rate makes the tool unusable;
    # if it returns nothing, every `asserts.py`-form finding silently vanishes.
    corpus = ["The handler in AgMsg.cpp does the work.\n",
              "Build: 38797     When: 8/6/2026 01:53:06\n"]
    mods = provlint.known_modules(corpus)
    LEDGER.ok("AgMsg" in mods and "Build" not in mods,
              "pass 1 vouches a real module and not a prose word",
              f"{sorted(mods)}")
    LEDGER.ok(hits("Build: 38797 and the value 1 < 2 was fine\n", mods) == [],
              "so `Build: 38797` is not a source location")
    LEDGER.ok(len(hits('AgMsg:208 "(int)message.time >= 0" guards the field\n', mods)) == 1,
              "while a vouched module in the same form IS one")

    # The denylist is the other direction: it must not be able to swallow a real
    # ArenaNet module. `MapData` was on it for a draft because GWLP-R ships a
    # `MapData.scala`, which would have silently dropped customarea's real findings.
    LEDGER.ok("MapData" not in provlint.NOT_ARENANET,
              "the upstream denylist does not shadow a real ArenaNet module",
              "GWLP-R's is `MapData.scala`, excluded by extension; ArenaNet's "
              "`MapData.cpp` is the client map loader and must stay checkable")
    LEDGER.ok(len(hits('MapData:4415 "s_chunkInfo[id].load != NULL" is the gate\n',
                       {"MapData"})) == 1,
              "and that module still produces findings")

    # An upstream marker suppresses the inference-based shapes but must NOT suppress
    # the crash dialog: `Assertion:` is Guild Wars' own label, so the text after it is
    # ArenaNet's however much upstream discussion shares the line. Skipping the whole
    # line hid studies/mapdata/FORMAT.md:233 for the length of a draft.
    mixed = ("| what gw-preservation's table carries | rejected. "
             "`Assertion: found`, `P:\\Code\\Engine\\Map\\Map.cpp(1762)` |\n")
    LEDGER.ok(len(hits(mixed)) == 1,
              "an upstream mention on the line does not hide a crash dialog",
              "FORMAT.md:233 -- the row happens to name gw-preservation")
    LEDGER.ok(hits('GWCA reads `StoC.h:239` as "count <= MAX" there\n') == [],
              "but it does still suppress an upstream file:line + expression",
              "that is the SECOND gate (PLAN.md 6.1), a licence question, not this one")

    # ---- 5. the real corpus, which is the point --------------------------------
    print("\n5. the tree itself")
    found, modules = provlint.scan_tree(ROOT)
    n_md = len(list(provlint.markdown_files(ROOT)))
    # 38 on 2026-08-12. The guard is against the walk matching nothing, which is how
    # `test_codec.py` printed ALL CHECKS PASSED over an empty fixture glob -- so this
    # is set below the real count, not at it.
    LEDGER.ok(n_md >= 30, "the whole tree of markdown is read, not a sample",
              f"{n_md} files")
    LEDGER.ok(len(modules) >= 100,
              "and pass 1 built a real module vocabulary from it",
              f"{len(modules)} names")

    by_file = {}
    for f in found:
        by_file[f.path] = by_file.get(f.path, 0) + 1

    dirty = sorted(p for p in SCRUBBED if by_file.get(p))
    LEDGER.ok(not dirty,
              f"all {len(SCRUBBED)} files scrubbed on 2026-08-12 are still clean",
              f"REGRESSED: {[(p, by_file[p]) for p in dirty]}" if dirty else "clean")

    grown = {p: (n, BASELINE[p]) for p, n in by_file.items()
             if p in BASELINE and n > BASELINE[p]}
    LEDGER.ok(not grown,
              f"and none of the {len(BASELINE)} un-scrubbed files has grown",
              f"GREW: {grown}" if grown else
              f"{sum(by_file.get(p, 0) for p in BASELINE)} remaining, "
              f"baseline {sum(BASELINE.values())}")

    unknown = {p: n for p, n in by_file.items()
               if p not in BASELINE and p not in SCRUBBED}
    LEDGER.ok(not unknown,
              "and no file outside the baseline carries the refused triple",
              f"NEW DRIFT: {unknown}" if unknown else "none")

    # The baseline is only meaningful if it is still reachable. A checker whose
    # patterns rot reports a clean tree and the shrinking count looks like progress.
    total_baseline = sum(by_file.get(p, 0) for p in BASELINE)
    LEDGER.ok(total_baseline > 0,
              "the un-scrubbed files still produce findings",
              f"{total_baseline} -- if this ever hits 0 without a scrub commit, the "
              "patterns have rotted rather than the tree having been cleaned")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
