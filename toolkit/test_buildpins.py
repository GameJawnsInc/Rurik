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
check(len(live) == 82,
      "82 class-(a) occurrences -- the census",
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
      f"the client itself carries instead of naming them")
check(len(files) == 11, "across 11 files", f"{len(files)}: {sorted(files)}")

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
check(max(collections.Counter(r["file"] for r in live).values()) == 25,
      "and the largest remaining block is msgshape.py's 25",
      str(collections.Counter(r["file"] for r in live).most_common(3)))

cited = [r for r in rows if r["klass"] == BP.CITATION]
check(len(cited) > len(live) * 3,
      "prose citations outnumber live constants several times over",
      f"{len(cited)} vs {len(live)} -- which is why counting was never the "
      f"deliverable, and why 'scrub the addresses' would be the wrong reading")

sys.exit(LEDGER.verdict())
