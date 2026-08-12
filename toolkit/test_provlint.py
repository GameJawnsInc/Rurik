"""Prove the provenance-prose checker catches the refused triple, and stays quiet.

`provlint.py` exists because the provenance gate had been enforced on exactly one
side. `toolkit/content.py` refuses an unprovenanced `source = "client-table"` row and
`test_content.py` proves the refusal fires -- but the same ruling's OTHER half, the one
that refuses "verbatim assert expressions with their source path and line", was enforced
by nobody and applied to nothing. Seventeen study documents accumulated assert text
pasted straight out of the crash dialog while the content store was refusing rows.

WHAT IT IS FOR CHANGED ON 2026-08-12, AND THE CHANGE MATTERS MORE THAN THE CODE.
The first version was a zero-tolerance gate, on a literal reading of the ruling. The
owner refined the ruling the same day (`PLAN.md` 7 Q3) after asking whether provenance
was starting to cost more than it protected: **a single assert cited as evidence is a
measurement and is permitted; the refusal targets BULK dumps and decompiled bodies.**
So this is now an ACCUMULATION TRIPWIRE. It does not care that
`studies/smsg/FINDINGS.md` quotes 65 asserts to name twenty opcodes -- that is the
auditable half of the naming argument. It cares whether a document is turning into a
string dump.

THREE THINGS ARE TESTED AND THE SECOND IS THE REAL ONE.

  1. It catches all three shapes assert citation actually takes (section 2).
  2. IT DOES NOT REDDEN AT THE PERMITTED FORMS. The study docs are BUILT out of
     locations, field names, bounds and VAs -- all permitted, all explicitly named in
     the ruling as the constraint we may keep. A checker that flags those is one that
     gets switched off within a day, and switching it off restores the exact silence
     it exists to end. Section 3 is therefore the long one.
  3. The corpus, against per-file and tree-wide ceilings with real headroom
     (section 5). Headroom is the point: ordinary research adds citations, and a
     tripwire that fires on ordinary work is one nobody leaves on.

A NOTE ON WHAT IS NOT TESTED. This checker reads PROSE, so its judgement of "is this
string an expression" is a heuristic with a residual error rate in both directions, and
it matches three machine formats and no prose paraphrase. That is fine at the job it
now has -- a dump is not going to be hand-written in paraphrase -- and it would NOT
have been fine for the zero-tolerance version, which is part of why that version was
the wrong design. What is not acceptable is the checker silently reading zero files, so
section 5 asserts the corpus size and the detector's own liveness around the ceilings.

standard library only.

    python toolkit/test_provlint.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import checks  # noqa: E402
import provlint  # noqa: E402

# 18, from a real green run on 2026-08-12 after the ruling was refined.
LEDGER = checks.Ledger("provlint", floor=18)

ROOT = os.path.dirname(HERE)

# WHAT THIS SECTION ENFORCES CHANGED ON 2026-08-12, and the change was a LOOSENING.
#
# The first version held eleven scrubbed files at zero and five others at a
# not-growing baseline, on a literal reading of "verbatim assert expressions with
# their source path and line". The owner refined the ruling the same day (`PLAN.md`
# 7 Q3): a SINGLE assert cited as evidence is a measurement and is permitted; the
# refusal targets BULK dumps and decompiled bodies. `studies/smsg/FINDINGS.md` quotes
# 65 of them to name twenty GAME_SMSG opcodes, and the quote is what lets a reader
# audit the naming without the binary -- so a gate demanding zero was costing more
# evidence than it protected.
#
# AND THEN THE 46 SCRUBBED SITES WERE REVERTED, the same day, for the same reason.
# With citation permitted, every one of those rewrites was a net loss: the paraphrases
# ran longer and repeatedly dropped the exact symbol -- `MissionCliIsGameMaster()`
# became "a game-master predicate", `!s_reusableAgentArray.Count()` became "an
# empty-list bound", and four crash-dialog transcripts became second-hand reports of
# a primary artifact. The tree is back to its pre-audit text and the counts below are
# the ORIGINAL ones. What survived the whole exercise is this file.
#
# So the ceiling below is an ACCUMULATION TRIPWIRE, not a debt schedule. A document
# is allowed to cite; it is not allowed to become a string dump. The grandfathered
# entries are the documents that legitimately argue from assert text; anything else
# gets NEWCOMER_CEILING before somebody should look at it. Raise a number when a
# document has a real reason to argue from more asserts -- that is a normal edit, not
# a defeat, and it is much cheaper than what the alternative reading cost.
NEWCOMER_CEILING = 10
GRANDFATHERED = {
    os.path.join("studies", "smsg", "FINDINGS.md"): 85,      # 65: names 20 opcodes
    os.path.join("studies", "monsterai", "FINDINGS.md"): 25,  # 12
    os.path.join("studies", "customarea", "FINDINGS.md"): 25,  # 12
    os.path.join("studies", "reconstruction", "FINDINGS.md"): 25,  # 11
    os.path.join("studies", "enemy", "PLAN.md"): 25,          # 11
    os.path.join("studies", "skillcast", "FINDINGS.md"): 20,  # 7
}

# A dump landing anywhere in the tree moves this even if no single file trips its own
# ceiling. 134 on 2026-08-12; the headroom is deliberate, because ordinary research
# adds citations and a tripwire that fires on ordinary work gets switched off.
TOTAL_CEILING = 200


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

    over = {p: (n, GRANDFATHERED.get(p, NEWCOMER_CEILING))
            for p, n in by_file.items()
            if n > GRANDFATHERED.get(p, NEWCOMER_CEILING)}
    LEDGER.ok(not over,
              "no document is becoming an assert-string dump",
              f"OVER CEILING: {over}" if over else
              f"worst is {max(by_file.values(), default=0)} in a file allowed "
              f"{max(GRANDFATHERED.values())}")

    total = sum(by_file.values())
    LEDGER.ok(total <= TOTAL_CEILING,
              f"and the tree-wide count is under {TOTAL_CEILING}",
              f"{total} across {len(by_file)} files")

    # The ceilings are only meaningful if the detector still fires. A checker whose
    # patterns rot reports a clean tree, and under a not-growing rule that reads as
    # progress rather than as breakage -- which is the one way this test could go
    # quietly useless while staying green.
    LEDGER.ok(total > 0,
              "and the detector still finds the citations it is measuring",
              f"{total} -- a drop to 0 with no scrub commit means the patterns "
              "rotted, not that the tree got cleaner")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
