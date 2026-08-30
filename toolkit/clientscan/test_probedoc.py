#!/usr/bin/env python3
"""The operator procedure quotes the instrument. This is what makes that true.

    python toolkit/clientscan/test_probedoc.py

WHAT THIS IS REALLY CHECKING, and it is a specific failure that already happened.

`studies/movement/PROBE-GATEFIRE.md` is a procedure an operator follows during a
live client run. Its §6 quotes what `movetap.py` and `movesync.py` print, so the
operator can match a real run against it and know which of three hypotheses the
run just selected. Those sample blocks were written **before the instrument
existed**, and by the time anybody looked they had drifted five ways at once:

  * an `ALIASING: phi 0.011 ... white 0.409, A = 0.026.` line that no code has
    ever printed, naming a `white` field no code has ever had;
  * a 2-line fence header where the printer emits 3;
  * an `unread:*  0  0.0%` row that `fence_verdict` **cannot** emit, because it
    iterates `sorted(reach.items())` and a label with no occurrences is not in
    the dict at all;
  * an EPISODES section wrong in nearly every particular -- no poll-rate line,
    no `effective n = ... QUOTE THE EPISODES.` line, one Nyquist threshold where
    the code names two, and no censoring marker;
  * an APPENDER WITNESS section attributed to `movetap`, which has no such
    printer -- it lives in `movesync.print_fence`.

**Nothing caught any of it, for as long as the document existed.** One block
carried a RECONSTRUCTION label, and the label was read as a licence rather than
as a debt -- §12 item 10 recorded two of the five drifts as accepted residue and
undercounted the rest. A label on a shape does not check the shape.

So: a rule nothing checks is a wish. This checks it.

WHAT IT DOES. Every fenced block in §6 is regenerated from the real printers over
the fixtures in `probedoc_fixtures.py` -- ONE module, imported both by this test
and by whoever regenerates the document, so the two cannot drift apart -- and
asserted byte for byte against the document. The two OBSERVED blocks are
reproduced by running the exact command the document prints, over the vault
captures it names.

A NOTE ON NUMBERING, because two things here are called §N: the DOCUMENT's
sections (its §6 is the one being pinned) and THIS FILE's own sections, printed
as §1-§7 when it runs. Where it matters below, the owner is named.

THE FOUR WAYS THIS GOES RED, each demonstrated on a scratch copy before the floor
was written down, and none of them a hypothetical:

  (a) one character changed inside a quoted block -> exactly ONE check reddens,
      naming the block, its document line range, and the first differing line
      with both sides printed. Proven: `402` -> `403` in the document's block 1.
  (b) a printer's output changed -> every block that printer feeds reddens at
      once, which is the drift this file exists for. Proven: `WOULD` -> `MIGHT`
      in `fence_verdict`'s header reddens 8 -- the sha256 pin and 7 blocks.
  (c) a block relabelled RECONSTRUCTION in the document -> its content check
      becomes a DECLARED SKIP (never a silent pass) *and* this file's §5 tier
      check reddens, because the fixture registry still names a fixture that
      could have checked it. Relabelling is not a way out.
  (d) both witnesses saying RECONSTRUCTION -> a declared skip and a green run,
      which is the shape a future block with no output yet takes. This one found
      a real hole in the first draft: a `continue` dropped a registry-side
      RECONSTRUCTION with no check AND no skip. This file's §6 tally is the fix.
  (+) the vault capture behind an OBSERVED block missing -> a declared skip,
      printed in the verdict, with the run still above its floor because the
      floor is the bare-machine core.

WHAT IT DOES NOT CHECK, stated so nobody reads more into a green run than is
there. Only the document's §6 fenced blocks are pinned. The document's §3
pre-flight greps (`gate_reach` = 31, `shut:apply` = 0), its §5 build lines, its
§7 failure table and its §10 addresses are prose and are NOT covered -- that is
named residue, not an oversight, and it is the obvious next lane. And the fixture
NUMBERS are not measurements of the client: `probedoc_fixtures.py` is real code
over hand-laid input, so what this file pins is the SHAPE the code prints. The
document's §6, §11 and §12 all say so per block, and this test does not upgrade
them.
"""
import ast
import hashlib
import inspect
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "harness"))

import checks             # noqa: E402
import movesync           # noqa: E402
import movetap            # noqa: E402
import probedoc_fixtures as FIX   # noqa: E402
import vaultpath          # noqa: E402

# MEASURED from a real green run on 2026-08-20 in
# `.claude/worktrees/gatefire-doc-sync-3e12b7` at HEAD 0841f5e: **74 checks**
# with both vault captures present, **72** with `RURIK_VAULT` pointed at an
# empty directory (2 declared skips). 72 is the bare-machine subset and is the
# floor, per checks.py's own rule -- set the floor to the mandatory core and let
# the optional sections declare skips. The two OBSERVED blocks are the only part
# of this file that needs the vault; everything else is the document, the source
# and the fixtures, all of which are in git. Both numbers were read off runs,
# not counted in anyone's head: `python toolkit/clientscan/test_probedoc.py` and
# the same with `RURIK_VAULT` pointed at an empty directory.
LEDGER = checks.Ledger("PROBE-GATEFIRE §6 quotes the instrument, not a memory of it",
                       floor=72)
check = checks.adopt(LEDGER)

# The document. Overridable so the red-proof can point at a perturbed scratch
# copy without touching the real one.
DOC = os.environ.get("RURIK_PROBEDOC_DOC", FIX.DOC)

SECTION = "## 6. THE ANALYSIS"
TIER_RE = re.compile(r"\b(RECONSTRUCTION|FIXTURE-DRIVEN|OBSERVED)\b")
# §6's staleness pin: "`movetap.py` sha256 `<hex>`". The document says a moved
# hash voids every block, which is a claim about the code and therefore checkable.
PIN_RE = r"`%s`\s+sha256\s+`([0-9a-f]{64})`"


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
# READING THE DOCUMENT
# --------------------------------------------------------------------------

def read_doc(path):
    with open(path, "rb") as fh:
        return fh.read().decode("utf-8").replace("\r\n", "\n").split("\n")


def all_fences(lines, lo, hi):
    """[(open_lineno, close_lineno, info)] for every fence in lines[lo:hi], 0-based."""
    out, start, info = [], None, None
    for i in range(lo, hi):
        if lines[i].startswith("```"):
            if start is None:
                start, info = i, lines[i][3:].strip()
            else:
                out.append((start, i, info))
                start = None
    if start is not None:
        out.append((start, hi, info))       # unterminated -- reported by the caller
    return out


def section_bounds(lines):
    """(lo, hi) line indices of §6, or None."""
    lo = None
    for i, ln in enumerate(lines):
        if ln.strip() == SECTION:
            lo = i
            break
    if lo is None:
        return None
    for j in range(lo + 1, len(lines)):
        if lines[j].startswith("## "):
            return lo, j
    return lo, len(lines)


def doc_tiers(lines, lo, fences):
    """The tier the DOCUMENT'S OWN PROSE declares for each bare fenced block.

    This is the second witness. `probedoc_fixtures.DOC_BLOCKS` is the first, and
    the two must agree -- so a block relabelled in the document goes red rather
    than quietly dropping out of scrutiny. The rule is deliberately simple and
    written down here rather than inferred: the tier of a block is the LAST tier
    word appearing in the prose since the previous fence closed, and a block with
    no tier word of its own inherits the previous block's (which is how the
    document's blocks 6 and 10 carry two fences under one label).
    """
    fenced_lines = set()
    for a, b, _info in fences:
        fenced_lines.update(range(a, b + 1))
    bare = [f for f in fences if f[2] == ""]
    tiers, prev_end, current = [], lo, None
    for a, b, _info in bare:
        gap = [lines[i] for i in range(prev_end, a) if i not in fenced_lines]
        found = TIER_RE.findall("\n".join(gap))
        if found:
            current = found[-1]
        tiers.append(current)
        prev_end = b + 1
    return bare, tiers


# --------------------------------------------------------------------------
# COMPARING ONE BLOCK
# --------------------------------------------------------------------------

def report_mismatch(label, doc_lines, got_lines, where):
    """Print the first difference, both sides, so the failure NAMES the drift."""
    say(f"    {label}: {where}")
    say(f"      document {len(doc_lines)} line(s), regenerated {len(got_lines)} line(s)")
    for k in range(max(len(doc_lines), len(got_lines))):
        d = doc_lines[k] if k < len(doc_lines) else "<document ends>"
        g = got_lines[k] if k < len(got_lines) else "<output ends>"
        if d != g:
            say(f"      first difference at block line {k + 1}:")
            say(f"        document : {d[:170]!r}")
            say(f"        printer  : {g[:170]!r}")
            return
    say("      (no line differs -- the mismatch is in the line count alone)")


def compare(label, doc_lines, text, where):
    got = text.splitlines()
    if doc_lines == got:
        return True
    report_mismatch(label, doc_lines, got, where)
    return False


# --------------------------------------------------------------------------
# THE OBSERVED BLOCKS -- real stdout over real vault captures
# --------------------------------------------------------------------------

def observed_paths(spec):
    """Absolute capture paths, or None if any is missing.

    Resolved through `vaultpath`, never `../../vault`: a worktree has no vault of
    its own, and a fixture that silently resolves to nothing turns every
    assertion behind it into a no-op.
    """
    try:
        root = vaultpath.vault_root()
    except Exception:
        return None
    paths = [os.path.join(root, *parts) for parts in spec["needs"]]
    return paths if all(os.path.isfile(p) for p in paths) else None


def run_movesync(argv):
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    cmd = [sys.executable, os.path.join(HERE, "movesync.py")] + argv
    p = subprocess.run(cmd, capture_output=True, timeout=600, env=env)
    return p.stdout.decode("utf-8", "replace").replace("\r\n", "\n")


# --------------------------------------------------------------------------

def main():
    say("PROBE-GATEFIRE §6: does the document still quote the code?")
    say(f"  document : {DOC}")
    say(f"  fixtures : {FIX.__file__}")

    # ----------------------------------------------------------------- §1
    head("§1  THE DOCUMENT PARSES, AND ITS BLOCK COUNT IS PINNED")
    if not os.path.isfile(DOC):
        check(False, "the document exists", DOC)
        return LEDGER.verdict()
    lines = read_doc(DOC)
    check(True, "the document reads", f"{len(lines)} line(s)")

    bounds = section_bounds(lines)
    if not check(bounds is not None, f"{SECTION!r} is present"):
        return LEDGER.verdict()
    lo, hi = bounds
    fences = all_fences(lines, lo, hi)
    bare, tiers = doc_tiers(lines, lo, fences)

    # A block quietly added to or removed from §6 is exactly the drift this file
    # exists to catch, so the count is asserted BEFORE anything is compared --
    # otherwise a deleted block would just stop being checked, silently.
    check(len(bare) == len(FIX.DOC_BLOCKS),
          "§6 holds exactly the number of untagged fenced blocks the registry names",
          f"document {len(bare)}, registry {len(FIX.DOC_BLOCKS)}")

    sources = [b["source"] for b in FIX.DOC_BLOCKS]
    check(len(set(sources)) == len(sources),
          "no fixture is claimed by two blocks",
          f"{len(sources)} block(s), {len(set(sources))} distinct source(s)")
    known = set(FIX.names()) | set(FIX.OBSERVED)
    missing = [s for s in sources if s not in known]
    check(not missing, "every block's named source actually exists",
          f"unresolved: {missing}" if missing else f"{len(sources)} resolved")
    check(all(t in ("FIXTURE-DRIVEN", "OBSERVED", "RECONSTRUCTION")
              for t in tiers) and tiers[0] is not None,
          "every block carries a provenance tier in the document's own prose",
          f"{tiers.count('FIXTURE-DRIVEN')} fixture-driven, "
          f"{tiers.count('OBSERVED')} observed, "
          f"{tiers.count('RECONSTRUCTION')} reconstruction")

    n = min(len(bare), len(FIX.DOC_BLOCKS))

    # ----------------------------------------------------------------- §2
    head("§2  THE SHA256 PIN §6 STATES ABOUT THE CODE IT QUOTES")
    say("  §6 says a moved hash voids every block below it. That is a claim about")
    say("  the source, so it is checked here rather than trusted.")
    blob = "\n".join(lines[lo:hi])
    for src in FIX.PINNED_SOURCES:
        m = re.search(PIN_RE % re.escape(src), blob)
        with open(os.path.join(HERE, src), "rb") as fh:
            real = hashlib.sha256(fh.read()).hexdigest()
        if m is None:
            check(False, f"§6 pins a sha256 for {src}",
                  "no pin found -- the document's own staleness signal is gone")
            continue
        check(m.group(1) == real, f"§6's pinned sha256 for {src} is the file on disk",
              f"document {m.group(1)[:16]}..., disk {real[:16]}..."
              if m.group(1) != real else real[:16] + "...")

    # ----------------------------------------------------------------- §3
    head("§3  THE PRINTER SIGNATURES THE DOCUMENT AND THE OPERATOR DEPEND ON")
    say("  §6 records `gate1_verdict(g1, g1why, early_a, point_bad, n)` and says")
    say("  early_a/point_bad are TALLY DICTS -- a caller passing ints raises")
    say("  AttributeError at movetap.py's `.get(True, 0)`. A signature that moved")
    say("  would break every regeneration below, so it is pinned by name.")
    for owner, fn, want in (
            (movetap, "fence_verdict", "(reach, flips, pairs, n, rate, seq=())"),
            (movetap, "gate1_verdict", "(g1, g1why, early_a, point_bad, n)"),
            (movetap, "print_episodes", "(seq, rate=None)"),
            (movesync, "print_fence", "(pairs, jumps, indent='   ', samples=None)"),
            (movesync, "print_jump_tally", "(rows, indent='   ')"),
            (movesync, "print_appender_witness",
             "(samples, indent='   ', population='movetap sample(s)')")):
        got = str(inspect.signature(getattr(owner, fn)))
        check(got == want, f"{owner.__name__}.{fn}{want}",
              "" if got == want else f"is actually {got}")

    # ----------------------------------------------------------------- §4
    head("§4  THE TWO SOURCE-SIDE CLAIMS §6 MAKES ABOUT ITS OWN HISTORY")

    def string_literals(path):
        with open(path, "rb") as fh:
            tree = ast.parse(fh.read().decode("utf-8"))
        return [nd.value for nd in ast.walk(tree)
                if isinstance(nd, ast.Constant) and isinstance(nd.value, str)]

    for src in FIX.PINNED_SOURCES:
        bad = [s for s in string_literals(os.path.join(HERE, src))
               if "white" in s.lower()]
        check(not bad,
              f"no printable string in {src} carries a `white` field",
              "the ALIASING line the old §6 invented named one; "
              f"{len(bad)} literal(s) do now" if bad else "0 literal(s)")
    with open(os.path.join(HERE, "movetap.py"), "rb") as fh:
        tap_src = fh.read().decode("utf-8")
    check("appender_witness" not in tap_src,
          "movetap.py has no appender witness at all",
          "the old §6 printed one under `movetap`; the printer is movesync's")
    check(hasattr(movesync, "print_appender_witness"),
          "movesync owns the appender witness the document relocated it to")

    # ----------------------------------------------------------------- §5
    head("§5  THE DOCUMENT'S OWN TIER LABEL AGREES WITH THE FIXTURE REGISTRY")
    say("  Two witnesses, and they must agree. A block relabelled RECONSTRUCTION")
    say("  in the document while a fixture still exists for it is a CONTRADICTION,")
    say("  not a licence: the content check below becomes a declared skip, and")
    say("  this check goes red. Relabelling is not a way out.")
    for i in range(n):
        spec, tier = FIX.DOC_BLOCKS[i], tiers[i]
        a, b, _ = bare[i]
        ok = tier == spec["tier"]
        check(ok, f"§6 {spec['block']} (doc lines {a + 1}-{b + 1}) is {spec['tier']}",
              "" if ok else
              f"the document's prose says {tier}, the registry says {spec['tier']}"
              f" and still names {spec['source']}")

    # ----------------------------------------------------------------- §6
    head("§6  EVERY BLOCK: REGENERATED AND COMPARED, OR DECLARED SKIPPED")
    say("  ONE loop over ALL fifteen blocks, and the tally under it asserts that")
    say("  each produced exactly one outcome. That accounting is not decoration:")
    say("  the first draft of this file had a `continue` that dropped a")
    say("  registry-side RECONSTRUCTION with no check and no skip -- a block that")
    say("  quietly stopped being covered, which is this document's original sin")
    say("  reproduced inside its own guard. The tally is what caught it.")
    say("  FIXTURE-DRIVEN blocks are regenerated from probedoc_fixtures.py.")
    say("  OBSERVED blocks are re-run over the vault captures they name; the")
    say("  vault is gitignored, so a machine without it declares a skip.")
    # THE TALLY IS READ OFF THE LEDGER, and that is the whole point of it.
    # It was `handled = 0` here and `handled += 1` as the FIRST statement of the
    # loop body -- above both `continue`s -- so it counted ITERATIONS and
    # `handled == n` could not go red. It printed `15 of 15 accounted for` and
    # always would have.
    #
    # That is worse than a dead check, because of WHAT this one is for. The
    # docstring above credits this tally with catching this file's original
    # sin: a `continue` that dropped a registry-side RECONSTRUCTION with no
    # check AND no skip, a block that quietly stopped being covered. The repair
    # put the counter where a recurrence of precisely that bug is invisible.
    #
    # Counting the LEDGER's own movement fixes it independently of where any
    # future `continue` is placed: a block that falls through emits neither a
    # check nor a skip, so the sum comes up SHORT. Exactly one of the two is
    # emitted on every path today (RECONSTRUCTION -> skip; vault absent ->
    # skip; FIXTURE-DRIVEN -> check; OBSERVED -> check; unknown tier ->
    # check(False)), which is what makes the equality the right assertion
    # rather than an inequality.
    ran0, skips0 = LEDGER.ran, len(LEDGER.skips)
    for i in range(n):
        spec, tier = FIX.DOC_BLOCKS[i], tiers[i]
        a, b, _ = bare[i]
        body = lines[a + 1:b]
        label = f"§6 {spec['block']} == {spec['source']}"
        where = f"doc lines {a + 1}-{b + 1}"

        # EITHER witness saying RECONSTRUCTION is enough to stop the comparison.
        # The document's label is honoured so the block is never REPORTED as
        # verified; §5 above is what refuses to let the label be a way out.
        said = [w for w, t in (("the document", tier),
                               ("the registry", spec["tier"]))
                if t == "RECONSTRUCTION"]
        if said:
            verb = "mark" if len(said) > 1 else "marks"
            LEDGER.skip(f"{label} content",
                        f"{' and '.join(said)} {verb} this block RECONSTRUCTION, so "
                        "nothing here regenerates it and NOTHING here says it is "
                        "right")
            continue

        if spec["tier"] == "FIXTURE-DRIVEN":
            rc, text = FIX.render(spec["source"])
            check(compare(label, body, text, where),
                  f"{label}  ({FIX.what(spec['source'])[:70]})",
                  f"{len(body)} line(s), printer rc={rc}")
        elif spec["tier"] == "OBSERVED":
            obs = FIX.OBSERVED[spec["source"]]
            paths = observed_paths(obs)
            if paths is None:
                LEDGER.skip(f"{label} content",
                            "the vault capture(s) this block was measured from are "
                            "not on this machine: "
                            f"{[os.path.join(*p) for p in obs['needs']]}")
                continue
            check(compare(label, body, run_movesync(obs["argv"](paths)), where),
                  f"{label}  ({obs['what'][:70]})", f"{len(body)} line(s)")
        else:
            check(False, f"{label}: the registry names a tier nothing handles",
                  repr(spec["tier"]))

    handled = (LEDGER.ran - ran0) + (len(LEDGER.skips) - skips0)
    check(handled == n,
          "every block in §6 was compared or declared skipped -- none fell through",
          f"{handled} of {n} accounted for -- counted as checks and skips the "
          f"loop actually emitted, so a block that falls through subtracts one")

    # ----------------------------------------------------------------- §7
    head("§7  EVERY FIXTURE IS DETERMINISTIC, AND THE UNQUOTED ONES STILL RUN")
    say("  A fixture that moves between runs turns this test into noise, and noise")
    say("  is how a bar gets lowered. Each renders twice and the two must be equal.")
    say(f"  {len(FIX.UNQUOTED)} of {len(FIX.names())} fixture(s) are not quoted in §6;")
    say("  they are rendered anyway, because a rotted fixture is worse than none.")
    for name in FIX.names():
        try:
            rc1, t1 = FIX.render(name)
            rc2, t2 = FIX.render(name)
            same = (rc1, t1) == (rc2, t2)
            detail = f"rc={rc1}, {len(t1.splitlines())} line(s)"
        except Exception as exc:                      # noqa: BLE001 -- a raise IS the finding
            same, detail = False, f"raised {type(exc).__name__}: {exc}"
        check(same, f"{name} renders identically twice", detail)

    return LEDGER.verdict()


if __name__ == "__main__":
    raise SystemExit(main())
