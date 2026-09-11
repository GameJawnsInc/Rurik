r"""The refindex gate: is the id we are about to edit one this index could have seen?

Four functions and one constant, lifted VERBATIM out of `overlay.py` so that
file is about manifests, plans and the six verbs and this one is about the gate:

    INDEX_COST       what building an index from scratch costs, printed first
    resolve_index    the index this plan is gated on -- handed in, named, built
    index_faults     refuse an index that could not SEE what the gate trusts
    index_row_fault  does the index agree with the ARCHIVE about which row?
    gate_edit        who else consumes this file id, and is every one acked?

WHY THE REASONING IS NOT HERE. The five docstring sections that argue this gate
are `overlay.py`'s and they STAYED there, because they are also `plan()`'s
refusal reasoning and `main()`'s `--help`. Read them in the module docstring of
`toolkit/mapdata/overlay.py`, by title:

  * THE REFINDEX GATE, AND WHY IT IS TIERED -- the measured 572-head all-zero
    group, and why a co-reader always refuses while a contentless co-wearer
    group only notes.
  * EVERY ID IS NORMALISED THROUGH `refindex.canonical_id` BEFORE IT IS
    COMPARED -- 38,396 rows, 12,860 of them flags-515 heads, and why a gate
    comparing the numbers as written reports a COMPLETE declaration as
    incomplete.
  * THE FLOOR SENTENCE IS PRINTED VERBATIM -- why `str(answer)` is never
    re-composed here into "N co-readers".
  * BUILDING AN INDEX OF A REAL ARCHIVE COSTS ~15.5 MINUTES AND ~10 MB SAVED --
    why the manifest may name one, and why the cost is printed BEFORE the wait.
  * AN INDEX THAT COULD NOT SEE IT IS NOT AN INDEX THAT SAW NOTHING -- the
    three-bullet specification `index_faults` below implements.

TWO POINTERS BELOW DO NOT MEAN THIS FILE, and they travelled without a word
changed, because rewording a moved comment is how a comment stops being
evidence: `gate_edit`'s "See the module docstring" means `overlay.py`'s module
docstring, the first section named above; and `index_faults`'s "MEASURED, on
this module's own fixture" means `test_overlay.py`'s fixture -- the two heads it
builds with real FA8 lists and damaged container magic -- which is `overlay.py`'s
test and reaches this file through the re-export `overlay.py` keeps.

Nothing here imports `overlay`. Every production caller is `overlay.plan()`,
which reaches these four by bare name through that re-export, at the site they
were cut from.
"""

import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import refindex                                            # noqa: E402
from refindex import canonical_id                          # noqa: E402

INDEX_COST = ("a full pass reads and decompresses every flags-515 container "
              "-- about 15.5 minutes and ~10 MB of JSON on a retail archive")


# ---------------------------------------------------------------------------
# The refindex gate
# ---------------------------------------------------------------------------

def resolve_index(manifest, ar, index=None, echo=True):
    """The reference index this plan is gated on: handed in, named, or built.

    `refindex.load(path, ar)` is ALWAYS called with the archive. An index
    loaded without one answers confidently for rows that have since moved, and
    "nobody else reads this row" is the single wrong answer the gate exists to
    prevent -- the same shape `vaultpath.require_dir` refuses from the other
    side.
    """
    if index is not None:
        refindex.check_stamp(index, ar, why="gate an overlay against")
        return index
    if manifest.refindex_path:
        if echo:
            print(f"  refindex <- {manifest.refindex_path}")
        return refindex.load(manifest.refindex_path, ar)
    if echo:
        # THE COST IS PRINTED BEFORE THE WAIT, not discovered during it.
        print(f"  the manifest names no refindex, so one is being BUILT from "
              f"{manifest.retail}.\n"
              f"  {INDEX_COST}. Build it once and name it:\n"
              f"    python toolkit/mapdata/refindex.py --dat {manifest.retail} "
              f"--build-json <vault path>\n"
              f"    refindex = \"<that path>\"      # in [overlay]")
    t0 = time.time()
    index = refindex.build(ar, progress=refindex.PROGRESS_EVERY if echo else 0)
    if echo:
        print(f"  refindex built in {time.time() - t0:.0f}s")
    return index


def _problem_lines(index, limit=6):
    out = []
    for rec in index.problems[:limit]:
        fid = rec.get("file_id")
        name = f"0x{fid:X}" if isinstance(fid, int) else "(no file id)"
        out.append(f"    row {rec.get('row')} {name}: {rec.get('why')}")
    if len(index.problems) > limit:
        out.append(f"    ... and {len(index.problems) - limit} more "
                   f"(index.problems carries all of them)")
    return out


def index_faults(index, manifest):
    """Refuse an index that could not SEE what this gate is about to trust.

    THE STAMP IS NOT THIS CHECK. `refindex.check_stamp` answers "is this index
    about this archive?"; these two fields answer "did it read the archive?",
    and an index can pass the first while failing the second. A head whose
    container would not decode is WALKED and not INDEXED -- `index.walked` and
    `len(index.heads)` differ for exactly that reason -- so its FA8 list is not
    in the graph, and a row that list names comes back with no referrers. That
    is the confident empty answer, arrived at with every other guard green.

    MEASURED, on this module's own fixture: two heads carrying real FA8 lists
    naming an edited row, with their container magic damaged to `ffnX`. The
    archive is healthy (`preflight` clean, `crc_sweep` clean), the index builds,
    `problems` names both rows, and `who_reads` on the edited row answers `[]`.
    Before this function the plan cleared the gate and the build ran.

    `partial` is refused outright and `problems` is refused unless the manifest
    declares the count. The asymmetry is the same one the skeleton tier rests
    on: a partial index has no honest reading, while an unreadable container is
    a real and bounded thing an operator can go and look at.
    """
    if index.partial:
        raise SystemExit(
            f"REFUSED: the reference index gating overlay {manifest.name!r} is "
            f"PARTIAL.\n"
            f"  It walked {index.walked} named head row(s), not the archive, so "
            f"every count off it is a floor of a floor: any head it did not "
            f"walk could be reading the row this manifest edits, and the index "
            f"has no way to say so.\n"
            f"  There is no acknowledgement for this one -- a subset was a spot "
            f"check and a gate is not.\n"
            f"  Build a whole one, once:\n"
            f"    python toolkit/mapdata/refindex.py --dat {manifest.retail} "
            f"--build-json <vault path>\n"
            f"    refindex = \"<that path>\"      # in [overlay]")
    n = len(index.problems)
    declared = manifest.accept_unread
    if n and declared is None:
        raise SystemExit(
            "\n".join([
                f"REFUSED: the reference index gating overlay "
                f"{manifest.name!r} could not read {n} container(s) or "
                f"list(s), and this manifest does not say so.",
                *_problem_lines(index),
                f"  Every one of those is a reference list this index did NOT "
                f"read. A head among them can name the row this manifest edits "
                f"and the answer still comes back empty -- an index that could "
                f"not see it is not an index that saw nothing, and this gate's "
                f"whole job is to tell those two apart.",
                f"  Look at them, then declare the number you looked at, in "
                f"[overlay]:",
                f"    accept_unread = {n}",
                f"  A count and not a flag: a new unreadable head moves the "
                f"number and this refusal comes back, where a `true` would go "
                f"on covering a blind spot as it grew.",
                f"  python toolkit/mapdata/refindex.py --dat {manifest.retail} "
                f"--build-json <vault path>   prints them under BLIND SPOT."]))
    if declared is not None and declared != n:
        raise SystemExit(
            "\n".join([
                f"REFUSED: overlay {manifest.name!r} declares accept_unread = "
                f"{declared} and this index could not read {n}.",
                *_problem_lines(index),
                f"  The number moved, which means the set of things this gate "
                f"cannot see is not the set that was looked at. Look again, "
                f"then write the new number:",
                f"    accept_unread = {n}      # in [overlay]"]))
    return n


def index_row_fault(index, edit, row):
    """Does the index agree with the ARCHIVE about which row this id names?

    -> a reason string, or None.

    `refindex.who_reads` resolves its argument to a row through the index's own
    spelling map and answers about THAT row. This caller has already resolved
    the same id against RETAIL's raw table, so the two resolutions can be
    compared -- and they are the one pair of facts that can catch a file-id
    table edited in place without its row's crc being updated, which is a state
    the MFT stamp cannot see (`refindex`'s own "THE STAMP AND WHAT IT DOES NOT
    CATCH"). An index answering about a different row than the one being
    written would answer "nobody" perfectly confidently.
    """
    seen = index.row_of(edit.file_id)
    if seen is not None and seen != row:
        return (f"the index resolves {edit.label} to row {seen}; the archive's "
                f"own file-id table resolves it to row {row}. Every answer "
                f"about this edit would be an answer about the wrong row.")
    if seen is None and (row in index.heads or row in index.targets):
        return (f"the index holds row {row}, but under none of {edit.label}'s "
                f"spellings, so a query with this id resolves to no row at all "
                f"and answers empty for a reason that is not 'nobody reads it'.")
    return None


def gate_edit(index, edit, row=None):
    """Who else consumes this file id, and is every one of them acknowledged?

    -> (unacknowledged, notes, answers). `unacknowledged` is the list of
    `(canonical_id, why)` pairs a refusal must name; empty means this edit
    clears the gate.

    `row` is the row the ARCHIVE resolved this id to. When it is given and the
    index holds no record of that row at all, the empty answer is annotated
    with what it is empty OF -- "no indexed reference list named row N", which
    is a fact, rather than a bare list a reader can take for a census.

    BOTH SIDES ARE NORMALISED THROUGH `canonical_id`, always. A row carries
    several file ids and an operator who wrote one spelling while the index
    reports another has made a COMPLETE declaration -- refusing it would send
    them off to add an id that is already there, and a gate that refuses
    correct declarations is a gate that gets a `--force` bolted on.

    THE TIER: co-readers always count; co-wearers count unless the shared key
    is contentless. See the module docstring -- 572 heads in one all-zero group
    on retail, and an acknowledgement of 571 unrelated models is a rubber
    stamp.
    """
    own = canonical_id(index, edit.file_id)
    ack = {canonical_id(index, a) for a in edit.acknowledge}

    reads = refindex.who_reads(index, edit.file_id)
    shares = refindex.who_shares_skeleton(index, edit.file_id)

    kinds = {}
    for referrer, kind in reads:
        kinds.setdefault(canonical_id(index, referrer), set()).add(kind)
    co_readers = sorted(k for k in kinds if k != own)
    co_wearers = sorted({canonical_id(index, f) for f in shares} - {own})

    contentless = shares.facts.get("contentless") is True

    notes, unack = [], []
    for fid in co_readers:
        if fid not in ack:
            unack.append((fid, "reads it via "
                               + "/".join(sorted(kinds[fid]))))
    if contentless and co_wearers:
        # A NOTE, NOT A REFUSAL. The group is real and the criterion did not
        # move; what the answer says is that the key carries no pose, so these
        # heads group because none of them has one.
        notes.append(str(shares))
        notes.append(
            f"  the {len(co_wearers)} co-wearer(s) above are NOT required in "
            f"acknowledge_shared_with: the shared key is contentless "
            f"(node_count {shares.facts.get('node_count')}), so it groups "
            f"heads that carry no pose rather than heads that share one.")
    else:
        for fid in co_wearers:
            if fid not in ack:
                unack.append((fid, "wears the same blk2C base array "
                                   f"({shares.facts.get('node_count')} node(s))"))

    blind = [p for p in index.problems if p.get("row") == row]
    if row is not None and blind:
        # THE SHARPEST CASE OF THE SAME THING. `accept_unread` counts this row;
        # this names it. An unreadable head carries no skeleton hash, so it
        # joins no sharing group, so the co-wearer answer below is empty for a
        # reason that is not "nobody else wears it" -- which is what
        # `refindex.who_shares_skeleton` says from its own side.
        notes.append(
            f"  row {row} is ITSELF one of the {len(index.problems)} thing(s) "
            f"this index could not read ({blind[0].get('why')}). It carries no "
            f"skeleton hash here and joins no sharing group, so an empty "
            f"co-wearer answer for it means 'not indexed', never 'nobody else "
            f"wears it'")
    if row is not None and reads.facts.get("resolved") is not True:
        # THE EMPTY ANSWER, NAMED. `refindex` cannot tell "an id this archive
        # does not hold" from "a row nothing here references" -- it says so --
        # but this caller resolved the id against the archive first, so it can,
        # and an unqualified empty list is the shape that reads as a census.
        notes.append(
            f"  this index holds no record of row {row}: it is not among the "
            f"heads it indexed and no reference list it read names it. The "
            f"empty answer above is therefore 'no list this index read names "
            f"row {row}', not 'this id is unknown' -- and what it could not "
            f"read is accounted for separately, by accept_unread")

    stale = sorted(a for a in ack
                   if a not in set(co_readers) | set(co_wearers))
    if stale:
        notes.append(
            "  acknowledged but not a co-consumer this index can see: "
            + ", ".join(f"0x{a:X}" for a in stale)
            + " -- harmless, and worth checking the id was not mistyped")
    return unack, notes, (reads, shares)
