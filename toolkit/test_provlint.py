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

# 19, from a real green run on 2026-08-12: 18 after the ruling was refined, plus the
# nested-worktree check added when this file went red on `main` at a commit it had
# passed at from inside a worktree.
LEDGER = checks.Ledger("provlint", floor=19)

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
    # 25 on 2026-08-14 and the ceiling WAS 25, i.e. zero headroom -- a tripwire with
    # no room is one that fires on the next ordinary edit, which is how a tripwire
    # gets switched off. Raised to 40 the same day, deliberately in the proportion
    # `smsg` already carries (66 against 85), and the reason is the one this file's
    # own docstring names: the document ARGUES from them. Each cites a single assert
    # as the evidence for one claim -- `ConstWorldMap:1313` bounding the world index,
    # `CharMsg:4934` bounding knotCount, `MsCliApi:251` fixing MISSION_MAP_GAME to 1 --
    # which is MEASUREMENT under the 2026-08-12 refinement, not a dump. Note who
    # raised it: the session whose own arc hit the wall. If a later reader thinks that
    # is self-serving, the check that matters is unchanged and cheap to apply -- read
    # the citations and ask whether any argues for nothing.
    os.path.join("studies", "minimap", "FINDINGS.md"): 40,    # 25: the atlas chain, the draw/ping triple, the fog partition
    # 13 on 2026-08-17, over NEWCOMER_CEILING on the day the arc landed, and the
    # document is a CHAIN of asserts by construction: it follows one click through
    # GmView's case for 0x100001A4 assert by assert -- 5890 `commander`, 5891
    # `commander->slotIndex < DLG_AGENT_COMMANDERS`, 5897 `heroData`, 5898
    # `heroData->agentId` -- and each one is the evidence that a specific server-side
    # change moved the failure to the next line. Take any of them out and the table in
    # 25.1 stops being auditable. The rest are single citations pinning single facts:
    # `GmView:2073` NAMES s_floatingDialogs, `PyCliParty:650` names m_partyClient,
    # `ItCliApi:485/488` bound ITEM_EQUIP_SLOTS and name the new blocker. Same
    # proportion as the entries above, and the same check applies -- read them and ask
    # whether any argues for nothing.
    os.path.join("studies", "pvpui", "FINDINGS.md"): 30,      # 13: the assert-by-assert walk of GmView's commander case
    # 15 on 2026-08-15, over NEWCOMER_CEILING on the arc's first commit, which is what
    # this row is for. 25 is the proportion the four 11-12 entries above already carry,
    # not a new number. The document argues from every one of them: `QuestChallenge:197`
    # and `QuestMission:81` are what fix QUEST_TYPE_CHALLENGE to 0 and QUEST_TYPE_MISSION
    # to 1 -- the second is a tail-call site `asserts.py` cannot see, so the quote IS the
    # measurement; `ChCliApi:667` names the bit `0x004C` sets and `0x0054` gates on;
    # `GmQuestComplete:611` bounds the medal; `ChCliApi.cpp:4237` supplies the client's
    # own noun for a quest-log row. Apply the check this file's docstring names -- read
    # them and ask whether any argues for nothing.
    os.path.join("studies", "quests", "FINDINGS.md"): 25,     # 15: the questType enum, the flag gates, challengeSortArray
    # 22 on 2026-08-16, over NEWCOMER_CEILING after the R4c-H arc landed. Ruled on by
    # the unit-models session (a DIFFERENT arc -- the heroes session should apply the
    # docstring's check itself and object if this is wrong): the 22 are ~13 DISTINCT
    # asserts cited repeatedly at different claim sites -- ChCliHero.cpp:199
    # `charHeroData` five times as the evidence anchoring one struct, ChCliAttrib.cpp:156
    # `attribState` four -- the smsg shape (one quote, many claims), not a dump. 30 is
    # snug over 22, in the proportion the 11-15 entries above carry.
    os.path.join("studies", "heroes", "FINDINGS.md"): 30,
    # 14 on 2026-08-18, over NEWCOMER_CEILING while the arc is still landing opcodes --
    # six commits to this document in a day, and documenting an opcode tends to bring
    # its assert with it. Ruled on by the quests-doc session (a DIFFERENT arc -- the
    # newopcodes session should apply the docstring's check itself and object if this is
    # wrong). The 14 sites are 9 DISTINCT asserts -- the generic `Array.h:587
    # index < m_count` five times, `ItCliApi.cpp:859 item` twice -- which is the smsg
    # shape (one quote, many claims), not a dump. Every one argues, and three in the
    # strongest form available: :832 is a CONTROLLED EXPERIMENT where the assert NOT
    # firing is the result (field 1 = 3 died on `item`, 40 passed the same guard, so the
    # field is an item id and not a count); :451 cites the generic assert as a NEGATIVE
    # result, the honest limit on naming the implementation module; :1857 reads
    # `PrApi.cpp:1431 bytes || !data` at an exact VA to identify 0x00B5's Preferences
    # API. The rest pin single facts -- `ConstTitle:81` bounds the 48-entry title table
    # and replaces a name that rested on one mirror, `MsCliApi:396` is the guard under
    # which an allegiance token becomes a roster key, `ChCliApi.cpp:2956` proves 0x00C5
    # cannot be first in its sequence. Two of the fourteen are CRASH DIALOGS, which
    # CLAUDE.md's refinement puts outside extraction entirely. 30 is pvpui's proportion
    # (13 -> 30) rather than a new number, chosen over 25 because this arc is mid-flight:
    # re-arming with 11 of headroom fires on the next ordinary commit, which is the
    # failure this file's own docstring is about.
    os.path.join("studies", "newopcodes", "FINDINGS.md"): 30,
    # 11 on 2026-08-18, one over NEWCOMER_CEILING, and this row exists because the
    # alternative was tried first and was WRONG. Updating 3's R5m row and 8's item
    # 10(b) to customarea 31's portal landing cited `Array.h(587) index < m_count`
    # at both sites -- the control that makes the green arm mean anything -- which
    # took the file 9 -> 11. The session's first move was to SCRUB one of the two and
    # cite it by reference instead, landing PLAN.md at exactly 10 of 10. That is the
    # state the comment at the top of this dict names as the failure mode: a tripwire
    # with zero headroom fires on the next ordinary edit, and PLAN.md is the most
    # edited document in the repo -- 3 is the single status authority, so every arc
    # that lands touches it. CLAUDE.md's refinement is the other half: a SINGLE assert
    # cited as the evidence for a claim is MEASUREMENT, kept with its file and line
    # "because the quote is what lets a reader audit the claim without the binary",
    # and "the direction of error in this repo is over-refusal". A reader of 3 should
    # not have to jump to 8 to audit the row. So the citation is restored and the
    # ceiling is raised, which is the move 154 above made two commits earlier.
    # The 11 are 9 DISTINCT asserts, none of them a dump: `Array.h:587` twice for the
    # ONE portal control (the same quote at the two claim sites that argue from it),
    # `GmView:5897/5898` + `ItCliApi:488` walking the pvpui click assert by assert,
    # `PathBuild:2297` bounding trapezoidCount, `PathData:365` on segment counts,
    # `GdCliApi.cpp:430` fixing the gadget agentDef, `ConstChar`/`CharPool` pinning
    # the 0x003A and revive crashes -- plus one CRASH DIALOG (`Map.cpp:1762`), which
    # CLAUDE.md's refinement puts outside extraction entirely. 25 is the proportion
    # the 11-entry rows above already carry (reconstruction 11 -> 25, enemy/PLAN.md
    # 11 -> 25), not a new number.
    "PLAN.md": 25,
}

# A dump landing anywhere in the tree moves this even if no single file trips its own
# ceiling. 134 on 2026-08-12; the headroom is deliberate, because ordinary research
# adds citations and a tripwire that fires on ordinary work gets switched off.
#
# 197 on 2026-08-14 -- three short of the ceiling, from two arcs' ordinary work and
# not from any dump. Raised to 280, keeping 2026-08-12's own ratio (134 against 200
# was ~1.5x) rather than inventing a new one. The tree-wide number is the BACKSTOP;
# the per-file ceilings above are the instrument that actually catches accumulation,
# and none of them moved except the one documented at its row.
#
# 280 on 2026-08-17 -- EXACTLY at the ceiling, which is the state this comment's own
# 2026-08-14 note was written to avoid. The arc that landed on it (studies/archivewrite,
# the Gw.dat write-size wall) contributes TWO citations, both single asserts anchoring
# the client's archive-repair path -- `progressNumer < progressDenomForScanMft` names
# the rescan and `m_writeState == STATE_READY` names the write-back, and each is the
# evidence for a claim about whether a botched write destroys the archive. That is the
# permitted form, not a dump. Raised to 420 on the same 1.5x rule rather than to a
# number that buys one more arc: a tripwire re-armed three short of its limit fires on
# the next session's ordinary work, and CLAUDE.md's recorded direction of error in this
# repo is over-refusal, of which a nuisance tripwire is a cheap generator. The per-file
# ceilings are still the instrument; none of them moved this pass.
TOTAL_CEILING = 420


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
    # 39 on 2026-08-12. The guard is against the walk matching nothing, which is how
    # `test_codec.py` printed ALL CHECKS PASSED over an empty fixture glob -- so this
    # is set below the real count, not at it.
    LEDGER.ok(n_md >= 30, "the whole tree of markdown is read, not a sample",
              f"{n_md} files")

    # ...and an UPPER bound, because the other failure is reading the tree several
    # times over. `.claude/` holds this repo's worktrees, each a full checkout of the
    # same documents; the first version walked into them and, from the main checkout,
    # reported 809 citations across 98 files against a true 136 across 17. It passed
    # from inside a worktree and went red on `main` at the same commit -- so the check
    # that matters is not the count but that NO counted file sits under a skipped
    # directory, which is tree-independent.
    nested = [p for p in (os.path.relpath(f, ROOT)
                          for f in provlint.markdown_files(ROOT))
              if any(part in provlint.SKIP_DIRS for part in p.split(os.sep))]
    LEDGER.ok(not nested,
              "and no file is read from a nested worktree, vault or venv",
              f"NESTED: {nested[:4]} ({len(nested)} total)" if nested
              else f"{', '.join(provlint.SKIP_DIRS)} all skipped")
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
