"""The build-coupled census, and the distinction it exists to make.

    python toolkit/test_buildpins.py

WHY. `studies/crossbuild/PLAN.md` §6's deliverable is a census of every constant
in `toolkit/` that is a fact about ONE client build -- the number that replaces
`PLAN.md` §6:803's "ongoing" and that `PLAN.md` §7 Q2 has been waiting on. Two
earlier attempts disagree and neither can be checked: "409 occurrences across 49
files" reproduces under no regex tried, and `studies/review/FINDINGS.md`:581's
"30 addresses in `toolkit/`" states no method.

THE ONE THING THIS FILE MUST PROVE. The census is worthless unless it separates
a constant a tool COMPUTES with from an address CITED in prose, because the two
want opposite things -- the first is a liability, the second is provenance that
`PLAN.md` §7 Q3 explicitly protects, and the last session to confuse them
rewrote 46 citations and reverted all 46. **The strings are identical.** Section
1 puts the same address in a docstring and in an assignment in one synthetic
module and requires them classified differently, then reproduces the grep
inline and shows it cannot tell -- so the AST is measured against the naive
method rather than merely asserted to be better.

The other sections pin the exclusions, because every one of them was MEASURED
from a real false positive in the first run rather than guessed: bit flags
(`0x00000001`), the image base itself (`0x00400000`), all-ones masks
(`0x00FFFFFF`), two-digit literals (`0x00FF00FF`, `0x00f00000`), and a map file
id cited in five modules (`0x345CC`). Each exclusion has a positive control --
a real address that must SURVIVE it -- because a filter that drops everything
produces a census of zero and a very clean-looking report.

No vault, no client, no socket: a classification defect is not a property of any
binary. Floor 40, ~2 s.
"""
import ast
import json
import collections
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import buildpins as BP                                       # noqa: E402
import checks                                                # noqa: E402

LEDGER = checks.Ledger("build-coupled census", floor=40)
check = checks.adopt(LEDGER)

# One module holding the SAME address twice: once as prose, once as code. This
# is the whole test.
SYNTHETIC = '''"""A module whose docstring cites 0x00487BC0, where a finding came from.

Also mentions 0x00BF96CC in prose, twice: 0x00BF96CC.
"""
# A comment citing 0x007F2E90, which is not in the tree at all.
CALLEE = 0x00487BC0          # live: the tool computes with this one
MASKS = (0x00FFFFFF, 0x00400000, 0x00FF00FF, 0x00000001)
FILE_ID = 0x345CC
BUILD = 38797


def f(pe):
    return pe.base + 0x00C0F300
'''


def write(tmp, name, text):
    p = os.path.join(tmp, name)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)
    return p


print("\n1. the same address, cited and computed with, told apart")

tmp = tempfile.mkdtemp(prefix="rurik_pins_")
try:
    write(tmp, "mod.py", SYNTHETIC)
    rows, problems, _skipped = BP.scan(tmp)
    check(not problems, "the synthetic module parses", str(problems))

    live = [r for r in rows if r["klass"] == BP.LIVE]
    cited = [r for r in rows if r["klass"] == BP.CITATION]
    live_vals = sorted({r["value"] for r in live})

    check(0x00487BC0 in live_vals,
          "0x00487BC0 assigned to a name is LIVE")
    check(sum(1 for r in cited if r["value"] == 0x00487BC0) == 1,
          "and the SAME address in the docstring is a CITATION",
          "identical strings, opposite verdicts -- this is the whole census")
    check(0x00C0F300 in live_vals,
          "an address inside a function body is LIVE")
    check(sum(1 for r in cited if r["value"] == 0x00BF96CC) == 2,
          "an address cited twice in prose counts twice as a citation")
    check(sum(1 for r in cited if r["value"] == 0x007F2E90) == 1,
          "and an address in a COMMENT is a citation",
          "a comment is not in the syntax tree at all, so it can only be text")
    check(not any(r["value"] == 0x007F2E90 for r in live),
          "-- never a live constant")

    # THE NEGATIVE CONTROL: the naive method, reproduced inline, cannot do this.
    naive = re.findall(r"0x[0-9A-Fa-f]{5,}", SYNTHETIC)
    naive_487 = sum(1 for m in naive if int(m, 16) == 0x00487BC0)
    check(naive_487 == 2,
          "a grep sees 0x00487BC0 TWICE and cannot say which is which",
          f"{naive_487} hits, one prose one code -- which is why this is an AST "
          f"walk and not an `rg`")

    check(38797 in live_vals, "a build number is LIVE too")

    print("\n2. the exclusions, each with a positive control")

    for v, why in ((0x00FFFFFF, "an all-ones mask"),
                   (0x00400000, "the image base itself, a single bit"),
                   (0x00FF00FF, "a two-digit literal"),
                   (0x00000001, "a bit flag"),
                   (0x345CC, "a map file id below the image")):
        check(v not in live_vals, f"excluded: {why} (0x{v:X})")

    # Positive controls. A filter that drops everything would pass all five
    # checks above and produce a census of zero.
    check(BP.is_build_coupled(0x00487BC0, "0x00487BC0")[0],
          "kept: a real .text address survives every exclusion")
    check(BP.is_build_coupled(0x00BCAD58, "0x00BCAD58")[0],
          "kept: a real .rdata table address does too")
    check(not BP.mask_shaped(0x00487BC0, "0x00487BC0"),
          "and a real address is not mask-shaped",
          "so the three mask tests are not simply refusing everything")
    check(not BP.is_build_coupled(0x00F00001, "0x00F00001")[0],
          "excluded: above the image's top")
    check(not BP.is_build_coupled(4096, "4096")[0],
          "excluded: a decimal literal, whatever its value")

    print("\n3. a test file's expectations are class (c), not (a)")

    write(tmp, "test_mod.py", "WANT = 0x00487BC0\n")
    rows2, _p, _s = BP.scan(tmp)
    in_test = [r for r in rows2 if r["file"].endswith("test_mod.py")]
    check(all(r["klass"] == BP.TEST for r in in_test if r["value"] == 0x00487BC0),
          "an address in a test_*.py is a TEST expectation",
          "going red on a new build is what it is FOR")
    check(not any(r["klass"] == BP.LIVE and r["file"].endswith("test_mod.py")
                  for r in rows2),
          "and never counted as the liability")

    print("\n4. the baseline is diffable, and a change is a RESULT")

    base_a = BP.baseline(rows2)
    check(len(base_a) >= 2, "a baseline holds the class-(a) sites",
          f"{len(base_a)}")
    gone, arrived, moved = BP.diff(base_a, base_a)
    check(not (gone or arrived or moved),
          "a baseline against itself is empty")

    write(tmp, "mod.py", SYNTHETIC.replace("CALLEE = 0x00487BC0",
                                           "CALLEE = 0x00487999"))
    rows3, _p, _s = BP.scan(tmp)
    gone, arrived, moved = BP.diff(base_a, BP.baseline(rows3))
    check(len(moved) == 1 and moved[0][0]["symbol"] == "CALLEE",
          "a moved address is reported as MOVED, not as gone-and-new",
          f"{len(gone)} gone, {len(arrived)} new, {len(moved)} moved")

    write(tmp, "mod.py", SYNTHETIC + "\nEXTRA = 0x00812345\n")
    rows4, _p, _s = BP.scan(tmp)
    gone, arrived, moved = BP.diff(base_a, BP.baseline(rows4))
    check(any(r["symbol"] == "EXTRA" for r in arrived),
          "a new pinned address is reported as NEW")

    # Exit codes, through main(), because "the census changed" must not read as
    # "the census crashed" -- the same distinction datcheck.py draws.
    stamp = os.path.join(tmp, "base.json")
    rc = BP.main(["--root", tmp, "--json", stamp])
    check(rc == 0, "writing a baseline exits 0", f"rc={rc}")
    rc = BP.main(["--root", tmp, "--diff", stamp])
    check(rc == 0, "an unchanged census exits 0", f"rc={rc}")
    write(tmp, "mod.py", SYNTHETIC.replace("0x00487BC0", "0x00487111", 1))
    rc = BP.main(["--root", tmp, "--diff", stamp])
    check(rc == 1, "a CHANGED census exits 1 -- a result, not an error",
          f"rc={rc}")
finally:
    shutil.rmtree(tmp, ignore_errors=True)


print("\n5. against the real toolkit/")

rows, problems, skipped = BP.scan(HERE)
check(not problems, "every .py under toolkit/ parses", str(problems[:3]))
check("buildpins.py" in " ".join(skipped),
      "the instrument excludes itself, and says so",
      "an instrument that measures itself inflates its own answer")

live = [r for r in rows if r["klass"] == BP.LIVE]
files = {r["file"] for r in live}
check(len(live) == 233,
      "233 class-(a) occurrences -- the census",
      f"{len(live)}; if this moved, the plan's cost number moved with it. 68 "
      f"until genericvalue.py stopped storing its ten table addresses; 63 after; "
      f"64 once buildid.py gave the older build a NUMBER, since a build number "
      f"is itself a build-coupled constant -- and that one is asserted against a "
      f"fresh read of the binary by test_buildid.py; 71 on 2026-08-14, when this "
      f"arc's tooling was cherry-picked onto a `main` that had gained SEVEN more "
      f"while the branch sat unmerged -- mapdata/modelfile.py's three FVF stride "
      f"tables plus their accessor and a build number (rung M2, and the tables "
      f"are ArenaNet's own, re-read out of the vaulted image by "
      f"test_modelfile.py §5), and mapdata/atex.py's FORMAT_FLAGS_VA and "
      f"RUN_TABLE_VA (the ATEX level codec). THAT IS THE POINT OF THIS CHECK "
      f"RATHER THAN A NUISANCE: the liability grows silently, it grew 11% in the "
      f"two days this branch was unmerged, and nothing but a literal here notices. "
      f"73 later the same day, 2026-08-14, when ArenaNet shipped 38833 and it was "
      f"registered in pinned.BUILDS: a build NUMBER and its SIZE are both "
      f"build-coupled constants, so REGISTERING a build costs two pins -- the "
      f"cheapest kind, derived and asserted against a fresh read by "
      f"test_buildid.py §4, but the census counts them because they are real. "
      f"**46 the same evening**, and this is the first time the number has gone "
      f"DOWN by a lot: genericvalue.py's 27 became 0 when its switches were "
      f"derived from the message tables instead of looked up, which is a 37% cut "
      f"to the whole repo's per-build liability in one module "
      f"(studies/crossbuild/FINDINGS.md §8). 47 on 2026-08-15, and this one is a "
      f"pin ADDED ON PURPOSE: atex.py's two VAs named no build, which is exactly "
      f"the class-(b) defect the plan states -- 'a bare VA with no build is the "
      f"defect, not the VA' -- and with nothing recording that they were measured "
      f"on 38797, test_atexlevel.py §7 was free to re-read them against whatever "
      f"client sorted last and did (38833, silently, once the vault gained a "
      f"third build). atex.TABLES_BUILD fixes that and costs one census row. The "
      f"trade is the right way round: a counted pin that a test resolves through "
      f"pinned.find() beats an uncounted address nobody can tell is stale. "
      f"**82 on 2026-08-17, and this is the largest jump the census has ever "
      f"recorded: +35 in ONE DAY, from three files that did not exist the day "
      f"before** -- clientscan/commandertrap.py (20), clientscan/framebus.py "
      f"(13), clientscan/commanderpeek.py (2). That is the hardware-breakpoint "
      f"generation of tooling (the heroes/PvP-UI commander arc and the frame-bus "
      f"reader), and it is a DIFFERENT KIND of pin from everything above it: "
      f"these are execution sites armed in a RUNNING process, so they are not "
      f"merely build-coupled, they are the addresses a debugger writes into "
      f"DR0..DR3 and a wrong one arms a breakpoint on the wrong instruction. "
      f"They are also the cheapest class to re-derive, because every one of them "
      f"is byte-verified against the live process before it is armed and the "
      f"tools refuse to run when the bytes disagree -- which is the mitigation "
      f"this check should be read against: the liability is real and it is "
      f"guarded at the point of use. Do not scrub them. If this number should "
      f"come DOWN, the way is genericvalue.py's -- derive the sites from a table "
      f"the client itself carries instead of naming them."
      f" **86 on 2026-08-18, +4 from two files that did not exist that morning** -- clientscan/fovread.py (3: the field-of-view global at 0x00C078C4 and the camera position and target beside it, 0x00C07860/0x00C0786C) and clientscan/fovaxis.py (1: the same fov global again). These are the CHEAPEST class in the census and the one the mitigation above fits best: both tools resolve every address as an RVA off the module base read at run time, so ASLR is handled rather than assumed, and both refuse loudly when the fov reads 0.0 -- which is what a wrong address looks like. They also earned their keep: the measurement they exist for closed studies/terrain FINDINGS 10-12 (the field of view is 75.000 deg HORIZONTAL, far plane 48000) after a static hunt ended at a runtime VARIABLE with no literal to read."
      f" **99 on 2026-08-19, +13 across three files, and this check had been sitting RED for two of them** -- clientscan/framebus.py +8 (13 -> 21, the frame-bus reader gaining sites), clientscan/movetap.py +1 (RVA_TLS_INDEX, and the 14th file), and clientscan/pinned.py +4 (8 -> 12: PATCHED_TEXT gained the key-tap's CAVE and JUMP, 0x004514E2..0x00451507 and 0x007DC0CE..0x007DC0D3, when the patched-digest SET was added). **113 by 2026-08-20 and this check sat RED at 99 while it happened**, from an arc this one did not run; then **134 on 2026-08-20, +21 and a 16th file, all of it the gate-fire instrument** -- clientscan/movetap.py 1 -> 28 (the AgTrack fence record and the ASYNC twin: stateArray/count/stride off AGBASE+0x1CC, the world[1] array at +0x14C and its count at +0x154, the agent fields the two early-outs read at +0x48/+0xC4/+0x78, and gate 1's 300.0f) and clientscan/movesync.py 0 -> 7 (the same record's field offsets, read back out of the capture rather than out of the process). This is the census doing its job: the instrument for ONE probe cost a fifth of the repo's whole per-build liability, and every one of those addresses is a number that silently means something else on 38833. movetap.py is now the largest block in the census at 28, displacing msgshape.py's 25. The last four are the cheapest kind of all and the one this census should be gladdest to count: they are not addresses a tool computes with, they are the addresses our own patcher WRITES, listed so that patches_touch() can tell a study that its finding landed on our bytes rather than ArenaNet's -- and the two that were missing are exactly why the gate went stale, since patches_touch() answered no for both key-tap sites while the key-tap had been writing .text for days."
      f" **135 on 2026-08-20, +1 and a 17th file, and it is the cheapest row the census has ever taken** -- clientscan/grantsim.py's LUT_VA, the 256-dword lookup table at 0x0093CAC8 behind the client's own table sqrt at 0x0046E870. REALFIX-C0 (studies/movement/REALFIX.md 2.6) needed the match test's EFFECTIVE threshold, which is not the 100.0f the client compares against: re-implementing those nine instructions and scanning all 2,048,001 float patterns in [9000, 11000] puts the boundary at 9984.0f = 99.919968 u, and the identical scan over [80000, 100000] reproduces gate 1's own 299.332591 u as its positive control. The whole module needs exactly ONE address for that, and every other VA it cites -- the bake at 0x005FE950, the <=1.0 u short-circuit at 0x005FEA92, the roster-wide history wipe at 0x006060A2 -- sits in a comment or a docstring, which is class (b): provenance, wanted, not liability. The mitigation is the kind this census likes best. The address is resolved through pinned.find(), which VERIFIES the image sha256 before handing it over, and test_grantsim.py 3 re-runs BOTH exhaustive scans against that image rather than trusting the two constants the module carries -- so an unknown build is refused rather than silently producing a confident wrong table, and a known build whose table moved reddens here and there."
      f" **151 on 2026-08-21, +16 and no new file: REALFIX-I1's history-chain layout, all of it inside clientscan/movetap.py (28 -> 44).** The appender at 0x00605840, its allocator at 0x00604BB0 and the walker at 0x006056A0 between them fix the node's next pointer, its time field, its four-dword point INCLUDING the plane word, the 0x2C allocation stride, the 256-node block cap, the 5000 ms block recycle and the 2500 ms head-age rule -- plus four record-side displacements that REFUTE this file's own prior comment, which said only +0x00 and +0x04 of the AgTrack record were ever touched. THE MITIGATION IS THE SAME ONE THIS CENSUS LIKES BEST AND IT IS WHY THE COUNT IS WORTH PAYING: not one of the sixteen is a literal compared against a copy of itself. `movetap._selftest_fence_bytes` ENCODES the expected instruction FROM the module constant and matches it at the VA in the pinned image, so a displacement that is wrong for a build produces bytes that are not at that address and the section goes red -- which is exactly what an unnoticed 38833 rebase would need. movetap.py stays the largest block and roughly doubles; that is the honest price of reading a linked list out of another process rather than inferring what was on it. **156 the same day, +5 and still no new file (movetap.py 44 -> 49), and every one of the five is a comment this file was ASSERTING rather than checking.** A verifier lane re-derived the layout from 38797 and found the block-recycle sentence naming the wrong node: 0x00604BFF's operand is [eax+edi-0x28] with eax already count*0x2C, i.e. index count-1, the block's NEWEST node -- while the comment said OLDEST and printed inside a green [PASS], because the existing pin encoded only the CONSTANT 5000 and left the operand free. That is the census's own failure mode at one level down: a pinned quantity with an unpinned operand. The five are HIST_RECYCLE_OPERAND (0x00604BFF, encoded FROM HIST_NODE_STRIDE so a belief in the oldest node writes +4 and reddens), the two SEVER stores 0x00604C56 and 0x00604CBB with the record-array stride 0x00604CC2 beside them -- which are the REAL reason a chain cannot dangle into a recycled block, a mechanism this repo had never written down -- and the block span 0x00604C49, encoded from HIST_NODE_STRIDE*HIST_BLOCK_MAX+4. The trade is the one this census keeps making and it is still the right way round: five counted pins for a paragraph that can now go red. **189 on 2026-08-22, +33 over the 156 above, and the split is the point: +32 of it is NOT this arc's and had already reddened this pair on `main` before this arc touched anything** -- clientscan/typenames.py 0 -> 32 (SKILLS-T1, commit 326f439, the client's own skill-type name table and the 18th file), landed by a parallel session that did not move either literal. The remaining **+1 is this arc's and is the cheapest row there is**: registering build 38849 in pinned.BUILDS (pinned.py 12 -> 13) after ArenaNet updated mid-run on 2026-08-20 -- the skills arc had rebuilt on 38849 and closed its own question, but the pinned row lagged, so test_handshake's build-vs-keyfile check sat red against a keyfile no BUILDS row named. A build NUMBER is a build-coupled constant and the census counts it, exactly as the 2026-08-14 registration above paid two. BOTH LITERALS ARE MOVED TOGETHER TO THE WHOLE TREE'S TRUE COUNT, including the 32 this arc did not add, because the alternative is leaving the pair red for a peer's work and thereby blind to the next real drift -- which is the failure recorded at 86-vs-113 above, and it has now happened twice."
      f" **204 on 2026-08-23, +15 and a 19th file, and this pair was ALREADY RED on `main` when the session that moved it arrived** -- clientscan/compositetrap.py 0 -> 14 (the composite arc's runtime instrument, landed the day before across 5a98afc..3cd8597 without either literal moving) and clientscan/commandertrap.py 20 -> 21 (the `postcall` site, 2e6f749, from the same day's commander work). That is the third time in nine days this check has been left red by an arc that finished without paying it, and the pattern is now clear enough to name: the census is moved by whoever NEXT runs the suite, not by whoever added the pins, so treat a red here as a bill rather than as a defect in your own change. The 14 are the composite pipeline's execution sites and the two globals its record resolver reads (RECORD_BASE_PTR 0x00BF9804 / RECORD_COUNT_PTR 0x00BF980C, plus the getids/record/cache/cachesame/clear entries and the CpsPlayer vtable 0x00A96B5C). THE MITIGATION IS THE STRONGEST CLASS THIS CENSUS COUNTS and it is why the 14 are worth paying: every site carries the instruction's own bytes, `verify_sites` matches them in the LIVE process before arming and refuses when they disagree, and test_compositetrap.py 1 re-checks the same bytes against the pinned 38797 image at a desk -- so a wrong address cannot silently arm a breakpoint on the wrong instruction, which is the specific hazard of the hardware-breakpoint generation of tooling. The vtable row is the cheapest kind: a CLASS identity read out of a live object, used only to LABEL an instance in a report, so a stale value degrades to an unrecognised pointer rather than to a wrong finding."
      f" **233 on 2026-08-29, +29 over the 204 above, and a 20th and 21st file.** The split is MEASURED rather than narrated -- a git worktree at a41b5bd, the commit that wrote the 204, scanned with THAT tree's own buildpins.py, reproduces 204 across 19 files to the row, and buildpins.py is byte-identical between the two commits, so the +29 is what landed and not a re-tuned instrument. All 18 other files are unchanged. It is clientscan/compositetrap.py 14 -> 27 (+13, a peer arc: the playercomposite work of 2026-08-24, dba8767 adding 11 and 0faface 2), clientscan/gatetrace.py 0 -> 4 (CANCELWALK-R7, 9a5a37e, landed via 53d2f0f sixteen and a half hours AFTER a41b5bd wrote the 204) and clientscan/movehook/readhook.py 0 -> 12 (the MOVECODE hook reader, born at 10adbd2 on 2026-08-26). **AND THE MITIGATION SENTENCE THIS CHANGELOG ALWAYS WRITES IS, THIS TIME, MOSTLY BAD NEWS -- which is the entry earning its keep rather than the entry failing.** Every paragraph above names how the new pins are guarded. Read the ones above as covering the pins they were written for and NOT these: (1) the 204 entry's \"STRONGEST CLASS ... verify_sites matches them in the LIVE process before arming\" is true of compositetrap's ORIGINAL 14 and of NONE of the +13, which are a namer over a walked EBP chain checked only by dict membership against fixtures carrying the same literals. Worse, and found only because this bill was paid: decoding the pinned 38797 image shows NINE of the eleven UPSTREAM_CALLERS are CALL-SITE VAs (E8 rel32 sits AT the address, targeting SetSlotItem 0x0082D6A0 or the per-slot worker 0x004B1800) while the map is consumed against RETURN addresses off [ebp+4] -- so nine of them can never match a frame, and the two that ever named an answer are the two that were MEASURED rather than read off a disassembly. That is a live defect in a peer's instrument, logged here rather than fixed here, and it means the cheapest reduction available under this census's own doctrine is 233 -> 224. (2) gatetrace's three VA pins look guarded and are not: test_gatetrace.py section 1 encodes its byte patterns FROM module constants for OFF_STATUS/BIT_GATE_A/OFF_FLAGBYTE/BIT_GATE_B/BIT_GATE_C -- none of which is a census row -- while the three counted VAs get HAND-TYPED patterns (55 8b ec, ff 73 14, 5f 5e 33 c0) that occur 14,765, 94 and 531 times in .text. Pointing all three at decoys four megabytes away leaves the section 9 of 9 GREEN, under a control line reading \"the byte checks above are load-bearing\". The control moves OFF_STATUS, which is not one of the four. They ARE genuinely build-coupled -- all six patterns fail against 38833 and 38849 -- but test_gatetrace._pinned_exe() hardcodes the 38797 vault path instead of resolving through pinned.find(gatetrace.BUILD), so the guard can never read a newer build and so can never redden on a rebase. gatetrace.BUILD is read by nothing (`git grep gatetrace.BUILD` is empty; the control, `git grep atex.TABLES_BUILD`, returns six). That is atex.TABLES_BUILD's shape one step short of its fix, and it degrades to a SKIP rather than to a wrong answer, which is the one merciful part. (3) readhook's 12 are correct -- every one re-read out of the pinned image, all seven SetPosition callers 0xE8 rel32 to 0x00602B20, caller sets exhaustive per codescan --xrefs -- but they are a second hand-copy: nine are exactly five bytes past an address content/movecode.toml already records, because the hook stores the RETURN and the toml cites the CALL. The genericvalue-style reduction is available and reaches 9 of 12, NOT 12: lines 849/850 are reseed's caller-returns whose call addresses appear nowhere under content/, and line 900's 0x00602BC2 is the return of setposition's INTERNAL call to agtrack, not a caller of it. Route noted, not taken in a census commit. **AND 233 IS A FLOOR, NOT A COUNT.** mask_shaped() drops any literal written with two or fewer distinct hex digits and its docstring claims \"No address in this tree is shaped like any of them\". That is false: movetap.py:1867 reads bytes at 0x00606000 on the line directly below a COUNTED 0x00605FF9, and compositetrap's TEXT_HI 0x00a00000 is the other. Two virtual addresses are invisible to this meter purely by spelling, so an address that wants to hide only has to choose its digits.")
check(len(files) == 21, "across 21 files", f"{len(files)}: {sorted(files)}")

# The sites the plan names by hand must actually be there. A census that missed
# the two live-memory readers would be reassuring and wrong.
for f, sym in (("clientscan/agentprobe.py", "RVA_ARRAY"),
               ("clientscan/itemprobe.py", "RVA_TLS_INDEX"),
               ("clientscan/avevents.py", "ACTION_38797"),
               ("clientscan/msgshape.py", "TABLES_38797"),
               ("clientscan/asserts.py", "ASSERT_VA_38797")):
    hit = [r for r in live if r["file"] == f and (sym is None or r["symbol"] == sym)]
    check(hit, f"the census finds {f}" + (f" {sym}" if sym else ""),
          f"{len(hit)} row(s)")

# INVERTED 2026-08-14, and the inversion is the result. This asserted that
# genericvalue.py held 27 -- "the largest remaining block" -- with the consolation
# that all 27 were GATED, so the module refused a build it had not been measured
# on rather than returning a stale map. Build 38833 then arrived and it refused,
# correctly and uselessly, taking avevents.py's property map with it. The
# switches are now derived from the client's own receive table, so the block is
# ZERO and the file is the negative case this census most wants to be able to
# state. msgshape.py's 25 is the largest remaining block.
check(not [r for r in live if r["file"] == "clientscan/genericvalue.py"],
      "genericvalue.py contributes NOTHING to the census (was 27, then 0)",
      "the switches are located through the message tables now; a live constant "
      "reappearing here means something went back to being looked up")
check(max(collections.Counter(r["file"] for r in live).values()) == 49,
      "and the largest remaining block is movetap.py's 49 (44 at REALFIX-I1's "
      "landing, its own 28 before that, and msgshape.py's 25 before that)",
      str(collections.Counter(r["file"] for r in live).most_common(3)))

cited = [r for r in rows if r["klass"] == BP.CITATION]
check(len(cited) > len(live) * 3,
      "prose citations outnumber live constants several times over",
      f"{len(cited)} vs {len(live)} -- which is why counting was never the "
      f"deliverable, and why 'scrub the addresses' would be the wrong reading")

sys.exit(LEDGER.verdict())
