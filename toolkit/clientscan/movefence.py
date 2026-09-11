#!/usr/bin/env python3
"""THE GATE-FIRE FENCE: was the client's snap test ever consulted, and what did
the appender do about it.

WHERE THIS CAME FROM, and read it before reading anything below. Every line in
this file was cut VERBATIM out of `movesync.py` on 2026-09-11 -- the fence
section that used to sit between `score()` and `collapse()`, and the four
`_selftest_*` sections that bind it. Nothing was reworded, renumbered or
re-indented in the move, so a comment here that says "this file" or "further
down" is talking about the file those words were written in. The split is
size, not subject: `movesync.py` is still the instrument, still owns SEPARATION
and the two-arm hard bar, and still runs the CLI.

THE HISTORY THIS SECTION IS AN ANSWER TO IS IN `movesync.py`'s HEADER and stays
there, because it is one numbered list of eleven defects and only the last three
are this file's:

  * defects 1-8 -- the wrong source, the contaminated detector, the blind
    denominator, refusal semantics, and the 2026-08-19 adversarial round's four
    -- are about the bars and live with them;
  * defect 9 (THE SENTINEL HOLE IN THE JUMP TABLE), defect 10 (NOTHING IN THIS
    SECTION WAS AN OBSERVATION) and defect 11 (TWO SPELLINGS FOR ONE STATE) are
    the 2026-08-20 gate-fire review -- probe changes C4, C5 and C9 -- and they
    are what this file is. They sit under `movesync.py`'s "AND THEN THE FENCE
    SECTION HAD THE SAME FAMILY OF HOLE" heading, and were left whole there
    rather than splitting three items off a list of eleven.

WHO READS WHAT IS HERE. `movesync.py` re-exports `FENCE_KEY`, `classify_reach`,
`print_jump_tally`, `print_appender_witness`, `print_fence`, `_rec` and the four
`_selftest_*` sections at the two sites this code was cut from, so
`movesync.selftest()`, `movesync.main()`, `probedoc_fixtures.py` and
`test_probedoc.py` reach them under the name they always used. `test_movesync.py`
patches the CLASSIFIER and the PRINTERS on THIS module, because the sections that
read them live here now and resolve them out of these globals.

THE GLOBALS ARE PART OF THE UNIT. `_selftest_jump_tally` rewrites
`UNREAD_REFUSE_SHARE` through `globals()` and `_selftest_appender_witness`
rewrites `APPEND_DEDUP_CHAIN` and `APPEND_TARGET` the same way, to prove the bar
and the printed addresses come from the constants rather than from a literal
typed into the sentence. `srclint.py:18` says outright that it cannot see a
`globals()` write, so nothing in the tree would notice a constant left behind in
`movesync.py` while its consumer moved here: the control would go green over an
unmutated global. That is why the constants and their printers travelled
together and why they must stay together.

READ ONLY. Opens nothing and writes nothing; standard library only.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))


# --- the fence on 0x006055E0, as read by movetap ----------------------------
#
# WHY THIS SECTION EXISTS. The separation statistic below says WHEN the client
# snaps. It cannot say whether the client's snap TEST was ever consulted: over
# 623 paired intervals, 0 of 24 snaps began below the test's own 300 u gate and
# yet 303 of 327 above-threshold intervals did not snap. A gate 92.7% of its
# population walks past is not deciding anything, and the candidate explanation
# is that the test is FENCED OFF (`clientControlled`, AgTrack record+0x00) and
# never evaluated. `movetap` reads that fence per sample as `gate_reach`; this
# prints it beside the jumps, which is the pairing the question needs.
#
# A MOVETAP THAT PREDATES THE FIELD MUST NOT SCORE AS 0%. Every capture in the
# vault on 2026-08-20 was taken before `gate_reach` existed, so the absent key
# is the common case and a share computed over it would be a confident lie
# about a client that was never asked. That is a refusal with a named fix, not
# a zero.
FENCE_KEY = "gate_reach"

# `gate_reach` IS A COUNTERFACTUAL LABEL ON A STATE READ, and every sentence
# this file prints about it is written to that. `movetap` reads two fields out
# of the AgTrack state record -- `clientControlled` (record+0x00) and the
# agent's world index -- and names the branch the caller at 0x00605FC0 WOULD
# take if it ran. It never reads the instruction pointer. So anything here about
# 0x006055E0 or 0x00605840 RUNNING is an INFERENCE from those two fields plus
# the caller's tail (0x00606009, 0x00606013), and is printed saying so. The one
# positive observation available is the appender witness further down, and it is
# positive precisely because it watches a WRITE rather than a state.
#
# THE TWO SPELLINGS, and why this file reads both while printing one. `movetap`
# wrote `shut:apply` / `world1:apply` until the 2026-08-20 rename (probe change
# C9). "apply" reads as "the server's position was applied", which is the
# opposite of what that branch does -- 0x00605840 APPENDS to the position
# history (0x00605A50 allocates, 0x00605A5D links new->old head) and corrects
# nothing -- and the string is written into every stored row permanently, so the
# captures already in the vault cannot be re-spelled. A consumer that silently
# failed to match the old name would score a real fenced sample as an unknown
# label and drop it into the unread bucket, which is worse than refusing. So
# BOTH spellings are accepted on read, canonicalised here, and only the NEW name
# is ever printed.
REACH_ALIASES = {"shut:apply": "shut:append", "world1:apply": "world1:append"}
# The one value in which the snap test at 0x006055E0 is reached at all.
REACH_TEST_RUNS = "test-runs"
# The values in which it is not: fence shut (either tail), or fence open on the
# world-1 copy, which goes to 0x00605840 without consulting any gate.
REACH_FENCED = ("shut:append", "shut:noop", "world1:append")
# At or above this share of UNREADABLE rows, the jump-row sentence is refused
# rather than qualified. Nine rows with three holes is not a measurement.
UNREAD_REFUSE_SHARE = 0.25


def unread_refuses(unread, n):
    """THE BAR, computed from `UNREAD_REFUSE_SHARE` and from nowhere else.

    It used to be spelled `unread * 4 >= n` at both call sites while the
    printed prose said "the 25% bar" off the constant -- two copies of one
    number, and only one of them checked. Setting `UNREAD_REFUSE_SHARE` to
    0.90 left the code still refusing at 25% and the output still claiming a
    90% bar, with every check green. A constant the code does not read is
    documentation, and documentation that disagrees with the code is worse
    than none: this is the number that decides whether the probe's headline
    sentence is printed at all.
    """
    return n > 0 and unread >= UNREAD_REFUSE_SHARE * n


def reach_label(v):
    """One `gate_reach` value in its canonical spelling. Old name in, new out."""
    if isinstance(v, str):
        return REACH_ALIASES.get(v, v)
    return v


def classify_reach(v):
    """THE THREE-WAY SPLIT: 'reachable' | 'fenced' | 'unread'.

    Everything that is not one of movetap's four real states -- a `None` from a
    sample that has no such key, an `unread:<why>` sentinel from the reader, a
    `missing:*` sentinel from `fence_at_jumps`, or a label this file has never
    heard of -- lands in 'unread' and NEVER in 'fenced'. Folding a could-not-read
    into a real state is the exact defect this function exists to make
    impossible: it put could-not-reads inside the one headline count the probe
    turns on.
    """
    v = reach_label(v)
    if v == REACH_TEST_RUNS:
        return "reachable"
    if v in REACH_FENCED:
        return "fenced"
    return "unread"


def fence_rows(pairs):
    """(counts, n_with_field, n_total, n_legacy_spelling) over gate_reach.

    Counts are keyed by the CANONICAL label, so a capture written before the C9
    rename tallies under the same key as one written after it, and `legacy` is
    how many rows arrived in the old spelling -- printed as provenance, because
    a normalisation the reader cannot see is a normalisation they cannot audit.
    """
    counts, have, legacy = {}, 0, 0
    for _t, _p, s, _g in pairs:
        v = s.get(FENCE_KEY)
        if v is None:
            continue
        have += 1
        if isinstance(v, str) and v in REACH_ALIASES:
            legacy += 1
        k = reach_label(v)
        counts[k] = counts.get(k, 0) + 1
    return counts, have, len(pairs), legacy


# The three ways a cell in the table below can fail to be a state read. They are
# `missing:*` strings rather than `None` because a bare `None` printed as the
# word "None" and tallied as a fenced sample: the sentinel has to survive into
# the count, not just into the display.
MISSING_NO_PRIOR = "missing:no-earlier-paired-sample"
MISSING_UNPAIRED = "missing:jump-t-not-in-pairs"
MISSING_NO_FIELD = "missing:sample-carries-no-gate_reach"


def fence_at_jumps(pairs, jumps):
    """[(t, step, before_reach, at_reach)] -- the fence either side of a snap.

    `before` is the state at the sample that OPENS the interval, because that is
    the read the jump came out of; `at` is the state once it landed.

    EVERY CELL IS A NAMED VALUE AND NONE IS `None`. Three separate things used to
    arrive here as a bare `None` -- the first paired sample has no predecessor, a
    jump `t` need not be in `by_t` at all, and a sample can carry no `gate_reach`
    -- and every one of them was then counted as a real fence-shut in the
    headline. They are `missing:*` sentinels now, in a value domain that cannot
    collide with movetap's four real states or its `unread:<why>` strings, so
    `classify_reach` can separate them and the table prints what happened.

    THE `at` COLUMN IS NOT AN OBSERVATION OF A BRANCH. On the snap branch the
    caller is documented to call AgTrack::Clear (0x00605F70) at 0x0060602E, so
    `before` != `at` is CONSISTENT with that branch having run. It is not
    evidence that it did: the sampler reads the record and never the instruction
    pointer, and at the ~10 Hz this reader sustains any number of branches can
    run between two reads.
    """
    by_t = {t: s for t, _p, s, _g in pairs}
    order = [t for t, _p, _s, _g in pairs]
    prev = {order[i]: order[i - 1] for i in range(1, len(order))}
    out = []
    for row in jumps:
        t = row[0]
        pt = prev.get(t)
        if t not in by_t:
            be = at = MISSING_UNPAIRED
        else:
            at = by_t[t].get(FENCE_KEY) or MISSING_NO_FIELD
            if pt is None:
                be = MISSING_NO_PRIOR
            else:
                be = by_t[pt].get(FENCE_KEY) or MISSING_NO_FIELD
        out.append((t, row[1], reach_label(be), reach_label(at)))
    return out


def jump_tally(rows):
    """THE THREE-WAY TALLY over the BEFORE column. The three sum to n, always.

    `labels` keeps the per-bucket breakdown so nothing disappears into a
    category name: a `world1:append` and a `shut:noop` are both "the test was
    not reached" and are still different states of the client.
    """
    out = {"n": len(rows), "reachable": 0, "fenced": 0, "unread": 0,
           "labels": {"reachable": {}, "fenced": {}, "unread": {}}}
    for _t, _s, be, _a in rows:
        c = classify_reach(be)
        out[c] += 1
        k = str(reach_label(be))
        out["labels"][c][k] = out["labels"][c].get(k, 0) + 1
    return out


def _detail(counts):
    return ", ".join(f"{k} x{v}" for k, v in
                     sorted(counts.items(), key=lambda kv: -kv[1])) or "none"


def print_jump_tally(rows, indent="   "):
    """The three-way tally, its refusal, and the sentence -- in that order.

    Returns 0 if the sentence was printed, 1 if it was refused. THE SENTENCE IS
    REFUSED, not qualified, when a quarter or more of the jump rows could not be
    classified: this is the number §6 of the probe quotes as its evidence, and a
    footnote under a headline is not a refusal.
    """
    tl = jump_tally(rows)
    n = tl["n"]
    if n == 0:
        print(f"{indent}  REFUSED: zero jump rows to judge. A tally over an "
              f"empty population is not a measurement.")
        return 1
    # The row count is asserted before anything is judged, and the partition is
    # asserted to be exhaustive: a three-way split that does not add up invites
    # the reader to complete it with whichever bucket they expected.
    assert tl["reachable"] + tl["fenced"] + tl["unread"] == n
    print(f"{indent}  THREE-WAY over the BEFORE column, and they sum to {n}:")
    print(f"{indent}    reachable       {tl['reachable']:4d}   BEFORE read "
          f"`{REACH_TEST_RUNS}` -- fence open, world != 1")
    print(f"{indent}    fenced          {tl['fenced']:4d}   BEFORE read a real "
          f"state in which the test is NOT reached "
          f"({_detail(tl['labels']['fenced'])})")
    print(f"{indent}    unread/missing  {tl['unread']:4d}   "
          f"({_detail(tl['labels']['unread'])}) -- NOT folded into either "
          f"count above, which is what this bucket exists for")
    if unread_refuses(tl["unread"], n):
        print(f"{indent}  REFUSED: {tl['unread']} of {n} jump row(s) "
              f"({100.0 * tl['unread'] / n:.0f}%) could not be classified, at "
              f"or above the {100 * UNREAD_REFUSE_SHARE:.0f}% bar. There is no "
              f"sentence about the client available from {n} row(s) with that "
              f"many holes in them.")
        print(f"{indent}  ...and the population refusal above cannot stand in "
              f"for this one: it is a different denominator over a different "
              f"population -- every paired sample, hundreds of rows -- while "
              f"this bar is over these {n}.")
        return 1
    print(f"{indent}  {tl['reachable']} of {n} snap(s) began with the record in "
          f"the ONE state where 0x006055E0 is reached; {tl['fenced']} began in "
          f"a state whose branch is 0x00605840 or a bare return.")
    print(f"{indent}  THAT SECOND HALF IS AN INFERENCE AND HERE IS ITS PREMISE: "
          f"the sampler reads `clientControlled` (AgTrack record+0x00) and the "
          f"agent's world index, never the instruction pointer, and the "
          f"caller's tail at 0x00606009/0x00606013 selects the branch from "
          f"exactly those two fields. NOTHING HERE OBSERVED 0x00605840 EXECUTE. "
          f"For an observation rather than an inference, read the appender "
          f"witness below.")
    return 0


# THE TABLE READ BACK OUT OF ITS OWN OUTPUT.
#
# Every check above this line asks `jump_tally` for a dict. The operator reads
# the TEXT, and `PROBE-GATEFIRE.md` §6 quotes the text -- so the two can
# disagree and nothing notices. They did: swapping the printed `reachable` and
# `fenced` cells, hard-wiring the printed `unread` count to 0, printing the
# unread label breakdown in the fenced row, and DELETING THE WHOLE TABLE while
# keeping the tally and the refusal were each fully green, because the checks
# grepped for marker substrings and one sentence.
#
# A missing row is an ABSENT KEY and never a zero. `{}` means the table was not
# printed at all, so a comparison against the dict fails loudly rather than
# defaulting to agreement -- the same rule as `state_fields` refusing to return
# 0 for a field it could not read.
_THREE_WAY_ROW = re.compile(r"^\s*(reachable|fenced|unread/missing)\s+(\d+)\s+(\S.*)$")
_THREE_WAY_NAME = {"unread/missing": "unread"}


def read_back_three_way(out):
    """{bucket: (printed_count, printed_detail)} parsed from printed text."""
    seen = {}
    for line in out.splitlines():
        m = _THREE_WAY_ROW.match(line)
        if m:
            seen[_THREE_WAY_NAME.get(m.group(1), m.group(1))] = (
                int(m.group(2)), m.group(3).strip())
    return seen


# --- the appender witness, from fields movetap already stores ---------------
#
# WHY THIS EXISTS AND WHAT MAKES IT DIFFERENT. Everything above is a state read:
# `gate_reach` names the branch the caller WOULD take, and no sample ever sees
# the caller run. These two counts are the only POSITIVE observations available
# from data already on disk, and they are positive because each is a CHANGE the
# client wrote between two of our reads:
#
#   (a) `hist_head` (record+0x04) or the last-appended position cache at
#       record+0x08..+0x14 differs across two consecutive samples. 0x00605840 is
#       the history APPENDER -- 0x00605A50 allocates a node, 0x00605A5D links
#       new -> old head -- so a changed head is a node that came into existence
#       between our reads and a changed cache is that path's own bookkeeping.
#       The WRITE is observed; that the appender is what wrote it is the
#       inference, and the premise is that those are the fields it writes.
#   (b) `hist_head` went to 0 while `gate_reach` did NOT change. A head returns
#       to 0 through an arm or an AgTrack::Clear, so this witnesses that
#       something ran BETWEEN two samples -- an aliasing detector that does not
#       depend on the state field whose aliasing is the question.
#
# TWO LIMITS, PRINTED EVERY TIME, because a zero here is weak evidence and would
# otherwise read as a strong one:
#   - the appender DEDUPS at 2500 ms (`0x0060593A cmp eax, 0x9c4`) -- BUT ONLY
#     TOGETHER WITH A MATCHING SAMPLE, which is narrower than this file claimed
#     until 2026-08-20 and is the correction below.
#   - the `shut:noop` branch writes nothing and is unobservable by construction.
#
# LIMIT 1 AS THIS FILE USED TO STATE IT WAS WRONG, and it was wrong in the text
# `PROBE-GATEFIRE.md` §6 quotes: "it cannot append twice inside that window".
# Re-read out of build 38797's own bytes with
# `python toolkit/clientscan/codescan.py --dis 0x00605910 --count 70`, the 2500 ms
# test is the FIRST of a chain and not the whole guard:
#
#   0x0060592A  mov edi,[esi+4] / test edi,edi / je   0x605A2F  (empty head)
#   0x0060593A  cmp eax,0x9c4   ................ jg   0x605A2F  (> 2500 ms)
#   0x0060594B  fucompp [esi+8]  ............... jp   0x605A2F  (cache x)
#   0x0060595E  fucompp [esi+0xC] ............   jp   0x605A2F  (cache y)
#   0x0060596B  cmp edx,[esi+0x10] ...........   jne  0x605A2F  (cache word)
#   0x0060597B  call 0x604760 / test eax,eax ..  jne  0x605A2F  (head node cmp)
#
# Every one of them jumps to the SAME append target, 0x00605A2F, which writes the
# cache at [esi+8..+0x18] and then allocates (0x00605A50) and links new -> old
# head (0x00605A55/0x00605A5D). So the append is suppressed only when the head is
# younger than 2500 ms AND the sample still matches the cached one: a MOVING
# agent CAN append twice inside the window. The direction of the old error was
# conservative -- it made a zero look weaker than it is -- but it was stated as a
# fact about the client, so it is corrected rather than left as the safe lie.
S_HIST_HEAD = 0x04          # movetap.S_HIST_HEAD -- 0x00605F4F, 0x006056AF
S_CACHE_LO = 0x08           # the last-appended position cache, +0x08..+0x14
S_CACHE_HI = 0x18           # ...ending where the record's time field begins
APPEND_DEDUP_S = 2.5        # `0x0060593A cmp eax, 0x9c4` = 2500 ms
# The other tests in the chain above, and the one target they all reach. They are
# CONSTANTS rather than literals inside the sentence because the sentence is the
# artifact: a printed address that no constant feeds is an address nothing can
# be wrong about, and the clause this replaces was exactly that.
APPEND_DEDUP_CHAIN = (0x0060594B, 0x0060595E, 0x0060596B, 0x0060597B)
APPEND_TARGET = 0x00605A2F


def state_fields(s):
    """(hist_head, cache_hex) from one sample; either is None where unread.

    Read out of `state_record` -- the whole 28 bytes movetap stores -- and falls
    back to the `hist_head` field alone when the record is absent. Returns None
    per field rather than a zero, because 0 is a REAL head value (an empty
    chain) and a zero standing in for "not read" is the family of defect this
    file keeps finding in itself.
    """
    rec = s.get("state_record")
    if isinstance(rec, str) and len(rec) >= 2 * S_CACHE_HI:
        try:
            b = bytes.fromhex(rec)
        except ValueError:
            b = None
        if b is not None and len(b) >= S_CACHE_HI:
            return (int.from_bytes(b[S_HIST_HEAD:S_HIST_HEAD + 4], "little"),
                    b[S_CACHE_LO:S_CACHE_HI].hex())
    h = s.get("hist_head")
    return (h if isinstance(h, int) else None), None


def appender_witness(samples):
    """The two positive observations over consecutive samples. Counts only.

    Every denominator it will need is carried out with it, because a count whose
    denominator is computed somewhere else is a count that gets quoted alone.
    """
    n = len(samples)
    w = {"samples": n, "adjacent": max(0, n - 1), "judged": 0, "unjudgeable": 0,
         "head_pairs": 0, "cache_pairs": 0, "head_changed": 0,
         "cache_changed": 0, "witnessed": 0, "reach_pairs": 0,
         "head_to_zero": 0, "dts": []}
    for i in range(1, n):
        a, b = samples[i - 1], samples[i]
        ha, ca = state_fields(a)
        hb, cb = state_fields(b)
        head_ok = ha is not None and hb is not None
        cache_ok = ca is not None and cb is not None
        if not head_ok and not cache_ok:
            w["unjudgeable"] += 1
            continue
        w["judged"] += 1
        w["head_pairs"] += int(head_ok)
        w["cache_pairs"] += int(cache_ok)
        hc = head_ok and ha != hb
        cc = cache_ok and ca != cb
        w["head_changed"] += int(hc)
        w["cache_changed"] += int(cc)
        # THE OR IS THE POINT. Either field changing is one write observed; the
        # cache moves on appends the head does not (the head only changes when a
        # node is allocated), so a head-only tally would miss them.
        w["witnessed"] += int(hc or cc)
        ta, tb = a.get("t"), b.get("t")
        if isinstance(ta, (int, float)) and isinstance(tb, (int, float)):
            w["dts"].append(tb - ta)
        ra, rb = reach_label(a.get(FENCE_KEY)), reach_label(b.get(FENCE_KEY))
        # THE GATE IS `classify_reach` AND NOT A LOCAL SPELLING RULE, and the
        # local rule it replaces is the same disagreement the distribution
        # printer had one section down. `not ra.startswith("unread:")` catches
        # movetap's OWN sentinel and nothing else, so anything this file has
        # never heard of -- a movetap that grows a fifth state, a rename nobody
        # taught this reader, a typo -- passed as a REAL state and entered arm
        # (b)'s DENOMINATOR, where a head -> 0 beside it counts as an arm having
        # run. That denominator is the aliasing witness §6 reads to decide
        # between polling and paying for a hook DLL. `classify_reach` is the
        # function every check interrogates, so it is the function the code
        # asks; `None` and every `missing:*`/`unread:*` sentinel land in
        # 'unread' through it too, which is why no `isinstance` guard is needed
        # in front of it.
        if head_ok and ra == rb and classify_reach(ra) != "unread":
            w["reach_pairs"] += 1
            if ha != 0 and hb == 0:
                w["head_to_zero"] += 1
    return w


def print_appender_witness(samples, indent="   ", population="movetap sample(s)"):
    """Both counts, both denominators, both limits. Refuses; never prints a 0.

    Returns 0 if it measured something, 1 if it refused.
    """
    w = appender_witness(samples)
    print(f"\n{indent}APPENDER WITNESS -- the only POSITIVE observations in this "
          f"section, over {w['adjacent']} consecutive pair(s) of "
          f"{w['samples']} {population}:")
    if w["adjacent"] == 0:
        print(f"{indent}  REFUSED: {w['samples']} sample(s) is not a pair, so "
              f"there is nothing to observe a change across.")
        return 1
    if w["judged"] == 0:
        print(f"{indent}  REFUSED: none of the {w['adjacent']} pair(s) carries "
              f"`state_record` or `hist_head` on BOTH sides "
              f"({w['unjudgeable']} unjudgeable). This movetap predates those "
              f"fields -- re-run `python toolkit/clientscan/movetap.py` and "
              f"pair the new file. This is NOT 'the appender never ran'.")
        return 1
    if w["unjudgeable"]:
        print(f"{indent}  PARTIAL: {w['judged']} of {w['adjacent']} pair(s) "
              f"judged; {w['unjudgeable']} could not be read on both sides and "
              f"are counted in NEITHER arm below.")
    print(f"{indent}  (a) a WRITE to the state record landed between two "
          f"samples: {w['witnessed']} of {w['judged']} judged pair(s) "
          f"(hist_head moved on {w['head_changed']}, the +0x08..+0x14 cache on "
          f"{w['cache_changed']}; the arms overlap and the tally is the OR)")
    print(f"{indent}      arm coverage: hist_head readable both sides on "
          f"{w['head_pairs']} pair(s), the cache on {w['cache_pairs']}. The "
          f"write is OBSERVED; that 0x00605840 is what wrote it is the "
          f"inference, premised on those being the fields it writes.")
    # Phrased so it reads correctly AT ZERO: "an arm ran between two samples"
    # asserts an event that a count of 0 says did not happen.
    print(f"{indent}  (b) hist_head -> 0 with gate_reach UNCHANGED: "
          f"{w['head_to_zero']} of {w['reach_pairs']} pair(s) where both "
          f"gate_reach reads are real and equal. EACH SUCH PAIR is an arm or an "
          f"AgTrack::Clear running BETWEEN two samples -- an aliasing witness "
          f"that does not depend on the state field whose aliasing is the "
          f"question.")
    dts = sorted(w["dts"])
    p50 = dts[len(dts) // 2] if dts else float("nan")
    dmax = dts[-1] if dts else float("nan")
    far = sum(1 for d in dts if d >= APPEND_DEDUP_S)
    chain = ", ".join(f"0x{va:08X}" for va in APPEND_DEDUP_CHAIN)
    print(f"{indent}  LIMIT 1 -- a zero above is WEAK, and the window is "
          f"CONDITIONAL: the appender dedups at {APPEND_DEDUP_S * 1000:.0f} ms "
          f"(`0x0060593A cmp eax, 0x9c4`), but that test is only the FIRST of a "
          f"chain -- {chain} each jump to the SAME append target "
          f"0x{APPEND_TARGET:08X} on INEQUALITY -- so the append is suppressed "
          f"only when the head is younger than {APPEND_DEDUP_S * 1000:.0f} ms "
          f"AND the sample still matches the cached one. A MOVING agent CAN "
          f"append twice inside the window; silence across a shorter pair "
          f"proves nothing only where the cached fields also held still. "
          f"Spacing p50 {p50:.3f}s, max {dmax:.3f}s; "
          f"{far} of {len(dts)} judged pair(s) span {APPEND_DEDUP_S:.1f}s or "
          f"more.")
    print(f"{indent}  LIMIT 2: the `shut:noop` branch writes nothing at all and "
          f"is unobservable by construction -- an absent witness is not "
          f"evidence that it did not run.")
    return 0


# THE WITNESS READ BACK OUT OF ITS OWN OUTPUT, for the reason above. Arm (a)'s
# `witnessed` hard-wired to 0, `judged` substituted for `reach_pairs` as arm
# (b)'s denominator, and the arm-coverage and PARTIAL lines deleted outright
# were each fully green: the checks asked the dict, and the dict was never the
# artifact. A count printed beside the WRONG denominator is the same defect C4
# was about -- a share whose bottom half nobody checked.
#
# Every field is keyed off a distinctive substring of the sentence that carries
# it, so a deleted line yields an ABSENT key rather than a zero.
_WITNESS_FIELDS = (
    ("witnessed", r"\(a\) a WRITE to the state record landed between two "
                  r"samples: (\d+) of \d+ judged pair"),
    ("judged", r"\(a\) a WRITE to the state record landed between two "
               r"samples: \d+ of (\d+) judged pair"),
    ("head_changed", r"hist_head moved on (\d+), the \+0x08"),
    ("cache_changed", r"the \+0x08\.\.\+0x14 cache on (\d+); the arms overlap"),
    ("head_pairs", r"arm coverage: hist_head readable both sides on (\d+) pair"),
    ("cache_pairs", r"arm coverage: hist_head readable both sides on \d+ "
                    r"pair\(s\), the cache on (\d+)\."),
    ("head_to_zero", r"\(b\) hist_head -> 0 with gate_reach UNCHANGED: "
                     r"(\d+) of \d+ pair"),
    ("reach_pairs", r"\(b\) hist_head -> 0 with gate_reach UNCHANGED: "
                    r"\d+ of (\d+) pair"),
    ("partial_judged", r"PARTIAL: (\d+) of \d+ pair\(s\) judged"),
    ("partial_adjacent", r"PARTIAL: \d+ of (\d+) pair\(s\) judged"),
    ("partial_unjudgeable", r"judged; (\d+) could not be read on both sides"),
)


def read_back_witness(out):
    """{field: printed_int} parsed from `print_appender_witness`'s own text."""
    seen = {}
    for name, pat in _WITNESS_FIELDS:
        m = re.search(pat, out)
        if m:
            seen[name] = int(m.group(1))
    return seen


def print_fence(pairs, jumps, indent="   ", samples=None):
    """Returns 0 if the fence share was read, 1 if it refused. Prints either way.

    `samples` is the WHOLE movetap sample stream when the caller has one. The
    appender witness is about consecutive SAMPLES, not about paired reports, and
    pairing drops every sample that had no report beside it -- so handing it the
    paired subset stretches the intervals it judges. It falls back to the paired
    samples with the population NAMED, because a witness over a subset is still
    a positive observation and printing nothing would be worse.

    The return value is about the fence SHARE alone. The jump tally and the
    witness carry their own refusals over their own populations, and print on
    every path including the refusing ones -- one refusal standing in for
    another is what C4 exists to undo.
    """
    rc = 0
    counts, have, total, legacy = fence_rows(pairs)
    print(f"\nTHE FENCE ON THE SNAP TEST (0x006055E0), from movetap's "
          f"`{FENCE_KEY}` -- a COUNTERFACTUAL label on a state read, not an "
          f"observation that the caller ran:")
    if not have:
        print(f"{indent}REFUSED: none of the {total} paired samples carries "
              f"`{FENCE_KEY}`. This movetap predates the field -- re-run "
              f"`python toolkit/clientscan/movetap.py` and pair the new file. "
              f"Nothing here is a fact about the client, and in particular it "
              f"is NOT 'the fence was never open'.")
        rc = 1
    else:
        if have < total:
            print(f"{indent}PARTIAL: {have} of {total} paired samples carry the "
                  f"field; the shares below are over {have}, not {total}.")
        # THE PRINTER AND THE CLASSIFIER ARE ONE FUNCTION NOW, AND THEY WERE TWO.
        # This sum read `str(k).startswith("unread:")`, which catches movetap's
        # own could-not-read sentinel and NOTHING ELSE, while `classify_reach`
        # -- the function every check in this file interrogates -- also lands a
        # label this file has never heard of in `unread`. So an UNRECOGNISED
        # `gate_reach` value was a hole to the dict and a REAL CLIENT STATE to
        # the printer, with a percentage beside it and nothing refusing: 9 rows
        # of `a-label-from-the-future` in 10 printed `90.0%` at rc 0. That is
        # C4's defect one section ABOVE C4's site, in the very distribution
        # `PROBE-GATEFIRE.md` §6 quotes. The BUCKET is printed per row for the
        # same reason: a share whose classification is not beside it is a number
        # the reader completes with whichever bucket they expected.
        unread = sum(c for k, c in counts.items()
                     if classify_reach(k) == "unread")
        for k, c in sorted(counts.items(), key=lambda kv: -kv[1]):
            print(f"{indent}{str(k):34} {c:6d}  {100.0 * c / have:5.1f}%  "
                  f"{classify_reach(k)}")
        if legacy:
            print(f"{indent}NOTE: {legacy} of {have} row(s) carry movetap's "
                  f"pre-rename spelling (`:apply`) and are counted under the "
                  f"`:append` name above. Stored rows are not rewritable, so "
                  f"both spellings are accepted on read and only the new one "
                  f"is printed.")
        if unread_refuses(unread, have):
            # ...and the sentence says what the count now means. "could not
            # read the record" was true of the `unread:` sentinel and false of
            # a label this file has never heard of, and the second kind is
            # exactly what this refusal was blind to until 2026-08-20.
            print(f"{indent}REFUSED: {unread} of {have} carry no state this "
                  f"file can read -- a could-not-read sentinel, or a label it "
                  f"has never heard of. No share above is a fact about the "
                  f"client. This bar is over the WHOLE paired population and "
                  f"says nothing about the jump rows below, which carry their "
                  f"own.")
            rc = 1
    rows = fence_at_jumps(pairs, jumps)
    print(f"{indent}the fence at each hard jump (n={len(rows)}):")
    if not rows:
        print(f"{indent}  (no hard jump in this window -- the distribution "
              f"above is the whole result)")
    else:
        # The BEFORE column is 38 wide because the `missing:*` sentinels are up
        # to 36 characters and a name that overflows its column pushes the AT
        # column out of line -- which is how a table stops being readable at
        # exactly the rows that matter most.
        print(f"{indent}  server t     step   "
              f"{'fence BEFORE':38} fence AT")
        for t, step, be, at in rows:
            print(f"{indent}  {t:9.3f}  {step:7.1f}   {str(be):38} {str(at)}")
        print_jump_tally(rows, indent)
    if samples is None:
        pop = [s for _t, _p, s, _g in pairs]
        name = ("PAIRED sample(s) -- the caller passed no full sample stream, "
                "so consecutive here can skip unpaired samples")
    else:
        pop, name = samples, "movetap sample(s)"
    print_appender_witness(pop, indent, name)
    return rc


def _rec(head, cache=0, controlled=1, tail=0):
    """One 28-byte AgTrack state record, hex, exactly as movetap stores it.

    +0x00 clientControlled, +0x04 the history head, +0x08..+0x14 the
    last-appended position cache, +0x18 a time; STRIDE 0x1C.
    """
    words = (controlled, head, cache, cache, cache, cache, tail)
    return b"".join(w.to_bytes(4, "little") for w in words).hex()


def _fake_pair(t, reach=None, rec=None):
    """One `pair()` row -- (server_t, report_xy, sample, gap)."""
    s = {"t": float(t), "live": [0.0, 0.0, 0]}
    if reach is not None:
        s[FENCE_KEY] = reach
    if rec is not None:
        s["state_record"] = rec
    return (float(t), [0.0, 0.0], s, 0.0)


def _line_with(out, needle):
    """The ONE printed line carrying `needle`, or None if zero or many do.

    THE WHOLE LINE, so a check can compare it against a HAND-COMPUTED string
    rather than grep a substring out of it. Every hole this file has found in
    itself twice over is a number printed beside the wrong denominator, and a
    substring test passes on all of them: `"REFUSED" in out` is satisfied by a
    refusal that names any two integers at all. Returning None on a DUPLICATE
    as well as on an absence is deliberate -- a sentence printed twice with two
    different numbers in it is not a line anybody can quote.
    """
    hits = [ln for ln in out.splitlines() if needle in ln]
    return hits[0] if len(hits) == 1 else None


def _floor(name, n, want):
    """A section that judged fewer rows than a green run does has FAILED.

    Set from a real green run and never from a guess. A section whose fixtures
    stop matching prints PASS on nothing at all otherwise, which is the defect
    `test_codec.py` shipped with its glob matching zero files.
    """
    if n >= want:
        return 0
    print(f"   [FAIL] section {name} executed {n} check(s), below its floor of "
          f"{want}. A run that measured nothing failed.")
    return 1


def _selftest_jump_tally():
    """C4: the sentinel hole in the jump table, and the three-way tally.

    THE DEFECT THIS PINS, and it sat at the one number the whole probe turns on.
    `tested = sum(1 for ... if be == "test-runs")` was printed against
    `len(rows)`, so `be is None` -- the first paired sample, or a jump `t` that
    is not in `by_t` at all -- and `be == "unread:<why>"` were both swept into
    "The rest reached 0x00605840 ... the HISTORY APPENDER". A could-not-read
    counted as a real fence-shut, in the headline.
    """
    import contextlib
    import io
    bad = n = 0
    print("\n8. C4: the jump table is a THREE-WAY tally, and refuses on holes")

    # Every way a BEFORE cell can fail to be a state read, one row each.
    pairs = [_fake_pair(1, "shut:append"), _fake_pair(2, "shut:append"),
             _fake_pair(3, "test-runs"), _fake_pair(4, "test-runs"),
             _fake_pair(5, "shut:append"), _fake_pair(6),
             _fake_pair(7, "shut:append"), _fake_pair(8, "shut:append")]
    #        t=1 is FIRST, so it has no predecessor; t=9 was never paired;
    #        t=7's predecessor carries no `gate_reach` at all.
    jumps = [(1.0, 900.0, 0.0, 0.0, 0.1), (9.0, 900.0, 0.0, 0.0, 0.1),
             (3.0, 900.0, 0.0, 0.0, 0.1), (5.0, 900.0, 0.0, 0.0, 0.1),
             (7.0, 900.0, 0.0, 0.0, 0.1)]
    rows = fence_at_jumps(pairs, jumps)
    # THE ROW COUNT FIRST. A control that judges zero rows is a defect.
    ok = len(rows) == 5
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the fixture yields {len(rows)} jump "
          f"row(s) to judge -- counted before anything is judged")

    bes = [r[2] for r in rows]
    # THE DISTINCTNESS IS HALF THE CLAIM, and it was the unchecked half: the
    # subset test alone is satisfied when all three constants hold the SAME
    # string, so collapsing them to one name left this check green while its
    # own message still said "their OWN named sentinel" -- a check that cannot
    # fail on the sentence it prints.
    named = {MISSING_NO_PRIOR, MISSING_UNPAIRED, MISSING_NO_FIELD}
    ok = None not in bes and len(named) == 3 and named <= set(bes)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] all three ways a cell can fail "
          f"arrive as their OWN named sentinel, never as a bare None and never "
          f"as each other ({len(named)} distinct name(s)): "
          f"{sorted(set(bes) - {'shut:append', 'test-runs'})}")

    tl = jump_tally(rows)
    ok = (tl["reachable"] == 1 and tl["fenced"] == 1 and tl["unread"] == 3
          and tl["reachable"] + tl["fenced"] + tl["unread"] == tl["n"] == 5)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] reachable {tl['reachable']} + "
          f"fenced {tl['fenced']} + unread {tl['unread']} = {tl['n']}: the "
          f"three sum to n, and the 3 holes are NOT in the fenced count")

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = print_jump_tally(rows)
    out = buf.getvalue()
    ok = (rc == 1 and "REFUSED" in out and "60%" in out
          and "began with the record in the ONE state" not in out)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] 3 of 5 rows unreadable is at or "
          f"above the {100 * UNREAD_REFUSE_SHARE:.0f}% bar, so the sentence is "
          f"REFUSED rather than qualified (rc {rc})")
    ok = "0x00605840 without any gate being evaluated" not in out
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and the old sentence -- which "
          f"asserted an execution nobody observed -- is gone from the output")

    # ...AND THE TABLE IS STILL PRINTED ON THE REFUSING PATH. Deleting it while
    # keeping the tally and the refusal was green: the refusal names a total and
    # the table is the only place the three parts appear. A refusal that also
    # withholds the breakdown leaves the reader with the pre-C4 fold.
    seen = read_back_three_way(out)
    ok = (len(seen) == 3 and seen["reachable"][0] == tl["reachable"]
          and seen["fenced"][0] == tl["fenced"]
          and seen["unread"][0] == tl["unread"])
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the three-way table is PRINTED "
          f"even on the refusing path, and its cells read back as the dict "
          f"({ {k: v[0] for k, v in sorted(seen.items())} } against reachable "
          f"{tl['reachable']} / fenced {tl['fenced']} / unread {tl['unread']})")

    # THE BAR IS ONE CONSTANT NOW. It was two -- `unread * 4 >= n` in the code
    # beside a "25% bar" printed off `UNREAD_REFUSE_SHARE` -- so raising the
    # constant to 0.90 left the code refusing at 25% and the prose claiming 90%,
    # with everything green. Both directions, because a bar that only ever
    # loosens is as unchecked as one that never moves.
    g = globals()
    keep = g["UNREAD_REFUSE_SHARE"]
    try:
        g["UNREAD_REFUSE_SHARE"] = 0.90
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc90 = print_jump_tally(rows)
        out90 = buf.getvalue()
    finally:
        g["UNREAD_REFUSE_SHARE"] = keep
    ok = rc90 == 0 and "REFUSED" not in out90
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the bar the CODE enforces is "
          f"`UNREAD_REFUSE_SHARE` itself: at 0.90 the same 60% of holes is "
          f"under it and the sentence prints (rc {rc90})")

    # THE MIRROR, or the refusal above is a constant: the same machinery under
    # the bar must print the sentence, with all three counts.
    marks = [None, "shut:append", "shut:append", "test-runs", "shut:append",
             "unread:record-unreadable", "shut:append", "world1:append",
             "shut:noop", "test-runs", "shut:append"]
    pairs2 = [_fake_pair(t, marks[t]) for t in range(1, 11)]
    jumps2 = [(float(t), 900.0, 0.0, 0.0, 0.1) for t in range(2, 10)]
    rows2 = fence_at_jumps(pairs2, jumps2)
    ok = len(rows2) == 8
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the sub-bar fixture yields "
          f"{len(rows2)} row(s) -- counted before it is judged")
    tl2 = jump_tally(rows2)
    ok = (tl2["reachable"] == 1 and tl2["fenced"] == 6 and tl2["unread"] == 1
          and tl2["reachable"] + tl2["fenced"] + tl2["unread"] == 8)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] reachable {tl2['reachable']} + "
          f"fenced {tl2['fenced']} + unread {tl2['unread']} = 8, one hole at "
          f"12.5% -- under the bar")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc2 = print_jump_tally(rows2)
    out2 = buf.getvalue()
    ok = (rc2 == 0 and "REFUSED" not in out2
          and "1 of 8 snap(s) began with the record in the ONE state" in out2
          and "INFERENCE" in out2)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] so it prints the sentence (rc "
          f"{rc2}) -- as an INFERENCE with its premise named, not as an "
          f"observation")

    # ...and the bar TIGHTENS off the same constant. One hole in eight is 12.5%
    # and passes at 0.25; at 0.10 it must refuse, or `UNREAD_REFUSE_SHARE` is
    # only being read on the loosening side.
    try:
        g["UNREAD_REFUSE_SHARE"] = 0.10
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc10 = print_jump_tally(rows2)
        out10 = buf.getvalue()
    finally:
        g["UNREAD_REFUSE_SHARE"] = keep
    ok = (rc10 == 1 and "REFUSED" in out10 and "10% bar" in out10
          and "began with the record in the ONE state" not in out10)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and it TIGHTENS off the same "
          f"constant: at 0.10 the same 1-in-8 is at the bar and the sentence is "
          f"refused (rc {rc10}), with the printed bar naming 10% -- one number, "
          f"not two")

    # THE PRINTED CELLS, against a fixture whose three counts are ALL DIFFERENT.
    # The two fixtures above cannot catch a swap -- reachable and fenced are
    # both 1 in the first and reachable and unread are both 1 in the second --
    # and swapping two printed cells was one of the mutations that stayed green.
    # 2 / 5 / 1 makes every permutation of the three visible.
    marks3 = [None, "test-runs", "test-runs", "shut:append", "shut:append",
              "shut:noop", "world1:append", "shut:append",
              "unread:record-unreadable", "test-runs"]
    pairs3 = [_fake_pair(t, marks3[t]) for t in range(1, 10)]
    jumps3 = [(float(t), 900.0, 0.0, 0.0, 0.1) for t in range(2, 10)]
    rows3 = fence_at_jumps(pairs3, jumps3)
    tl3 = jump_tally(rows3)
    ok = (len(rows3) == 8 and tl3["reachable"] == 2 and tl3["fenced"] == 5
          and tl3["unread"] == 1)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the swap fixture yields "
          f"{len(rows3)} row(s) tallying reachable {tl3['reachable']} / fenced "
          f"{tl3['fenced']} / unread {tl3['unread']} -- three DIFFERENT numbers, "
          f"asserted before anything is read back")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc3 = print_jump_tally(rows3)
    out3 = buf.getvalue()
    seen3 = read_back_three_way(out3)
    ok = (rc3 == 0 and len(seen3) == 3
          and seen3["reachable"][0] == tl3["reachable"]
          and seen3["fenced"][0] == tl3["fenced"]
          and seen3["unread"][0] == tl3["unread"])
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the PRINTED cells are the dict's "
          f"own three counts, each in its own row "
          f"({ {k: v[0] for k, v in sorted(seen3.items())} }) -- a swapped "
          f"pair, a hard-wired 0 or a deleted table all fail here")
    ok = (_detail(tl3["labels"]["fenced"]) in seen3["fenced"][1]
          and _detail(tl3["labels"]["unread"]) in seen3["unread"][1]
          and _detail(tl3["labels"]["unread"]) not in seen3["fenced"][1])
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and each breakdown sits beside its "
          f"OWN count -- fenced `{_detail(tl3['labels']['fenced'])}`, unread "
          f"`{_detail(tl3['labels']['unread'])}` -- so printing one where the "
          f"other belongs is caught, not just printing something")

    # THE TABLE'S OTHER TWO PRINTED NUMBERS, and they were the ones still free.
    # Every check above reads the three CELLS. The header's "and they sum to
    # {n}" and the refusal's "{unread} of {n} jump row(s) ({pct}%)" were read by
    # nothing at all, so repointing EITHER at `reachable + fenced` -- dropping
    # the unread-or-missing holes out of the denominator, which is the pre-C4
    # defect restated as a fraction -- was green through this selftest AND
    # `test_movesync.py`. Both lines are compared WHOLE against a hand-computed
    # string here, because the sentence is what §6 quotes and a substring test
    # ("REFUSED" in out) is satisfied by a refusal naming any two integers.
    #
    # THE FIXTURE IS BUILT SO NO ARITHMETIC COINCIDENCE CAN SATISFY THEM: the
    # three cells are 1 / 2 / 3, their sum is 6, and `reachable + fenced` is 3
    # -- four numbers, all different, and 3 of 6 (50%) reads 100% over the
    # narrowed denominator. Every fixture above has two cells sharing a value.
    marks4 = [None, "test-runs", "shut:append", "world1:append",
              "unread:record-unreadable", None, "a-label-from-the-future",
              "shut:append"]
    pairs4 = [_fake_pair(t, marks4[t]) for t in range(1, 8)]
    jumps4 = [(float(t), 900.0, 0.0, 0.0, 0.1) for t in range(2, 8)]
    rows4 = fence_at_jumps(pairs4, jumps4)
    tl4 = jump_tally(rows4)
    narrowed = tl4["reachable"] + tl4["fenced"]
    ok = (len(rows4) == 6 and tl4["n"] == 6 and tl4["reachable"] == 1
          and tl4["fenced"] == 2 and tl4["unread"] == 3 and narrowed == 3
          and len({tl4["reachable"], tl4["fenced"], tl4["unread"],
                   tl4["n"]}) == 4 and narrowed != tl4["n"])
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the pinned-line fixture yields "
          f"{len(rows4)} row(s) at reachable {tl4['reachable']} / fenced "
          f"{tl4['fenced']} / unread {tl4['unread']}, summing to {tl4['n']} "
          f"while `reachable + fenced` is {narrowed} -- four DIFFERENT numbers, "
          f"counted before a line is read")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc4 = print_jump_tally(rows4)
    out4 = buf.getvalue()
    hdr = _line_with(out4, "THREE-WAY over the BEFORE column")
    want_hdr = "     THREE-WAY over the BEFORE column, and they sum to 6:"
    ok = hdr == want_hdr
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the HEADER line is exactly "
          f"{want_hdr!r} -- it sums the three-way tally over all {tl4['n']} "
          f"rows and not over the {narrowed} that carry a state; got {hdr!r}")
    ref = _line_with(out4, "could not be classified")
    want_ref = ("     REFUSED: 3 of 6 jump row(s) (50%) could not be "
                "classified, at or above the 25% bar. There is no sentence "
                "about the client available from 6 row(s) with that many holes "
                "in them.")
    ok = rc4 == 1 and ref == want_ref
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and the REFUSAL line is exactly "
          f"{want_ref!r} (rc {rc4}) -- 3 of 6 is 50%, where the same 3 over "
          f"the {narrowed} classified rows would read 100%, so a narrowed "
          f"denominator cannot print this line")
    # THE REFUSAL'S SECOND LINE CARRIES A THIRD FREE `n`, and it is the one
    # that tells the reader the population refusal upstairs is NOT this bar.
    # Repointing it at `narrowed` (3) said "this bar is over these 3" beside a
    # refusal that had just said 3 of 6 -- a sentence that reads as though the
    # holes were the whole population -- and nothing anywhere failed.
    stand = _line_with(out4, "population refusal above cannot stand in")
    want_stand = ("     ...and the population refusal above cannot stand in "
                  "for this one: it is a different denominator over a "
                  "different population -- every paired sample, hundreds of "
                  "rows -- while this bar is over these 6.")
    ok = stand == want_stand
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and the line that separates the two "
          f"refusals is exactly {want_stand!r} -- it names {tl4['n']}, every "
          f"jump row, and not the {narrowed} that carry a state; got "
          f"{stand!r}")

    # THE SENTENCE ITSELF, WHOLE, AND IT WAS THE LAST FREE NUMBER IN HERE. Both
    # lines above are on the REFUSING path. The path that PRINTS was checked by
    # one substring -- `"1 of 8 snap(s) began with the record in the ONE state"
    # in out2` -- which says nothing at all about the SECOND half of the same
    # sentence, so `{tl['fenced']}` -> `{tl['unread']}` was `--selftest` 75/75
    # and `test_movesync.py` green while printing the HOLE count as the number
    # of snaps that began fenced. That is the pre-C4 fold arriving through the
    # printer instead of through the tally, into the one sentence
    # `PROBE-GATEFIRE.md` §6 quotes as its H1 evidence.
    #
    # NO ARITHMETIC COINCIDENCE CAN SATISFY IT: 3 / 8 / 1 sum to 12, and every
    # cell differs from every other cell, from n, from `reachable + fenced`
    # (11) and from `n - reachable` (9) -- so a swap, a borrowed denominator or
    # a substituted count all move a printed digit. One hole in twelve is 8%,
    # under the bar, so the sentence prints rather than refusing.
    marks5 = [None, "test-runs", "test-runs", "test-runs",
              "shut:append", "shut:append", "shut:append",
              "shut:noop", "shut:noop", "shut:noop",
              "world1:append", "world1:append",
              "unread:record-unreadable", "shut:append"]
    pairs5 = [_fake_pair(t, marks5[t]) for t in range(1, 14)]
    jumps5 = [(float(t), 900.0, 0.0, 0.0, 0.1) for t in range(2, 14)]
    rows5 = fence_at_jumps(pairs5, jumps5)
    tl5 = jump_tally(rows5)
    narrowed5 = tl5["reachable"] + tl5["fenced"]
    ok = (len(rows5) == 12 and tl5["n"] == 12 and tl5["reachable"] == 3
          and tl5["fenced"] == 8 and tl5["unread"] == 1 and narrowed5 == 11
          and len({tl5["reachable"], tl5["fenced"], tl5["unread"], tl5["n"],
                   narrowed5, tl5["n"] - tl5["reachable"]}) == 6
          and not unread_refuses(tl5["unread"], tl5["n"]))
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the SUCCESS-sentence fixture yields "
          f"{len(rows5)} row(s) at reachable {tl5['reachable']} / fenced "
          f"{tl5['fenced']} / unread {tl5['unread']}, summing to {tl5['n']} "
          f"with `reachable + fenced` {narrowed5} and `n - reachable` "
          f"{tl5['n'] - tl5['reachable']} -- six DIFFERENT numbers, one hole in "
          f"twelve so the bar does not fire, all counted before a line is read")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc5 = print_jump_tally(rows5)
    out5 = buf.getvalue()
    sent = _line_with(out5, "snap(s) began with the record in the ONE state")
    want_sent = ("     3 of 12 snap(s) began with the record in the ONE state "
                 "where 0x006055E0 is reached; 8 began in a state whose branch "
                 "is 0x00605840 or a bare return.")
    ok = rc5 == 0 and sent == want_sent
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and the SENTENCE is exactly "
          f"{want_sent!r} (rc {rc5}) -- BOTH halves, so the `{tl5['fenced']}` "
          f"after the semicolon can no longer be the unread count "
          f"({tl5['unread']}), the reachable count ({tl5['reachable']}), the "
          f"total ({tl5['n']}) or `n - reachable` "
          f"({tl5['n'] - tl5['reachable']}); got {sent!r}")
    return bad + _floor("8", n, 20), n


def _selftest_appender_witness():
    """C5: the two positive observations, and the zero it refuses to print."""
    import contextlib
    import io
    bad = n = 0
    print("\n9. C5: the appender witness -- a WRITE observed, not a state read")

    blind = [{"t": 0.0, "live": [0, 0, 0]}, {"t": 0.1, "live": [0, 0, 0]}]
    w = appender_witness(blind)
    ok = w["adjacent"] == 1 and w["judged"] == 0 and w["unjudgeable"] == 1
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] a movetap with no `state_record` "
          f"judges {w['judged']} of {w['adjacent']} pair(s) -- the fixture is "
          f"counted, so the refusal below is not vacuous")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = print_appender_witness(blind)
    out = buf.getvalue()
    ok = rc == 1 and "REFUSED" in out and "NOT 'the appender never ran'" in out
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and it REFUSES (rc {rc}) instead of "
          f"printing 0 witnessed -- a zero here would read as 'the appender "
          f"never ran'")

    def _s(t, rec, reach="shut:append"):
        return {"t": t, "live": [0, 0, 0], "state_record": rec,
                FENCE_KEY: reach}

    head = appender_witness([_s(0.0, _rec(0x1000, 1)), _s(0.1, _rec(0x2000, 1))])
    ok = (head["judged"] == 1 and head["head_changed"] == 1
          and head["cache_changed"] == 0 and head["witnessed"] == 1)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] hist_head 0x1000 -> 0x2000 is "
          f"witnessed ({head['witnessed']} of {head['judged']}): a node was "
          f"allocated between two reads")

    # THE OR ARM, and it is the reason this is not a hist_head detector. The
    # cache moves on appends that allocate no node, so a head-only tally misses
    # them and would print a silence that is an artifact of the arm chosen.
    cache = appender_witness([_s(0.0, _rec(0x1000, 1)), _s(0.1, _rec(0x1000, 2))])
    ok = (cache["judged"] == 1 and cache["head_changed"] == 0
          and cache["cache_changed"] == 1 and cache["witnessed"] == 1)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and a +0x08..+0x14 cache change "
          f"with the head UNMOVED is witnessed too "
          f"({cache['witnessed']} of {cache['judged']}) -- the tally is the OR "
          f"of both arms, not hist_head alone")

    static = appender_witness([_s(0.0, _rec(0x1000, 1)), _s(0.1, _rec(0x1000, 1))])
    ok = static["judged"] == 1 and static["witnessed"] == 0
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] CONTROL: an unchanged record over a "
          f"judged pair witnesses {static['witnessed']} -- the count reads the "
          f"bytes and is not a constant")

    # ARM (b): a head that returns to 0 while the fence label does not move.
    zero = appender_witness([_s(0.0, _rec(0x1000, 1)), _s(0.1, _rec(0, 1))])
    ok = zero["reach_pairs"] == 1 and zero["head_to_zero"] == 1
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] hist_head -> 0 with gate_reach "
          f"UNCHANGED: {zero['head_to_zero']} of {zero['reach_pairs']} -- an "
          f"arm or a Clear ran BETWEEN two samples")
    moved = appender_witness([_s(0.0, _rec(0x1000, 1)),
                              _s(0.1, _rec(0, 1), "test-runs")])
    ok = moved["reach_pairs"] == 0 and moved["head_to_zero"] == 0
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] CONTROL: the same head -> 0 with "
          f"gate_reach CHANGING scores {moved['head_to_zero']} of "
          f"{moved['reach_pairs']} -- arm (b) needs the label held still, or it "
          f"is just the fence moving")
    # ...AND THE OTHER HALF OF ARM (b), WHICH NO FIXTURE ANYWHERE EXERCISED.
    # The guard is `ha != 0 and hb == 0`, and every fixture in this file and in
    # `test_movesync.py` starts from a NON-ZERO head -- so dropping the first
    # conjunct to a bare `hb == 0` was green through all 65 selftest checks and
    # all 150 of the suite's. What that mutation does is score EVERY held-still
    # consecutive pair of an agent whose history chain is already empty as "an
    # arm or an AgTrack::Clear ran BETWEEN two samples", which is the aliasing
    # witness the probe reads to decide between polling and paying for a hook
    # DLL. A false positive here is the expensive direction, so the case is
    # pinned: a head that was ALREADY 0 across a held-still pair is a TRANSITION
    # THAT DID NOT HAPPEN.
    empty_chain = [_s(0.0, _rec(0, 1)), _s(0.1, _rec(0, 1))]
    already = appender_witness(empty_chain)
    ok = already["judged"] == 1 and already["reach_pairs"] == 1
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] CONTROL: a head ALREADY 0 across a "
          f"label-held-still pair is judged and reaches arm (b)'s denominator "
          f"({already['reach_pairs']} pair(s), {already['judged']} judged) -- "
          f"asserted non-zero FIRST, because a control that judges zero rows "
          f"cannot refute anything")
    ok = already["head_to_zero"] == 0
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] ...and it scores "
          f"{already['head_to_zero']} of {already['reach_pairs']} -- 0 -> 0 is "
          f"not a head RETURNING to 0, so nothing ran between these two reads; "
          f"a bare `hb == 0` reads 1 of 1 here and calls an empty chain an arm")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc_z = print_appender_witness(empty_chain)
    out_z = buf.getvalue()
    arm_b = _line_with(out_z, "(b) hist_head -> 0 with gate_reach UNCHANGED")
    want_b = ("     (b) hist_head -> 0 with gate_reach UNCHANGED: 0 of 1 "
              "pair(s) where both gate_reach reads are real and equal. EACH "
              "SUCH PAIR is an arm or an AgTrack::Clear running BETWEEN two "
              "samples -- an aliasing witness that does not depend on the "
              "state field whose aliasing is the question.")
    ok = rc_z == 0 and arm_b == want_b
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and the PRINTED arm (b) line is "
          f"exactly {want_b!r} (rc {rc_z}) -- the sentence asserts an event, so "
          f"the 0 in front of it is the whole of what makes it true; got "
          f"{arm_b!r}")

    unread = appender_witness([_s(0.0, _rec(0x1000, 1), "unread:record-unreadable"),
                               _s(0.1, _rec(0, 1), "unread:record-unreadable")])
    ok = unread["reach_pairs"] == 0
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and two equal `unread:` labels are "
          f"NOT 'unchanged' ({unread['reach_pairs']} pair(s) judged for arm b) "
          f"-- equality between two could-not-reads is not a fact")

    # ...AND THE OTHER HALF OF THAT REFUSAL, WHICH THE GATE WAS SPELLED WRONG
    # FOR. `not ra.startswith("unread:")` admits everything that is not
    # movetap's own sentinel, so a label this file has never heard of was a
    # REAL state in arm (b)'s denominator -- while `classify_reach`, the
    # function every check above interrogates, calls it a hole. The fixture
    # below is the `unread:` one with the ONE thing changed that the old gate
    # could not see, and it is the same printer-vs-classifier disagreement
    # section 11 pins one screen down, arriving here in a DENOMINATOR instead
    # of in a share.
    future_label = "a-label-from-the-future"
    future = [_s(0.0, _rec(0x1000, 1), future_label),
              _s(0.1, _rec(0, 1), future_label)]
    wf = appender_witness(future)
    ok = (wf["adjacent"] == 1 and wf["judged"] == 1
          and classify_reach(future_label) == "unread"
          and not future_label.startswith("unread:"))
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the unrecognised-label fixture is "
          f"{wf['judged']} of {wf['adjacent']} pair(s) JUDGED, held still at "
          f"`{future_label}` -- which `classify_reach` calls "
          f"`{classify_reach(future_label)}` while the retired "
          f"`unread:`-prefix rule called it real; counted first, because a "
          f"control that judges zero rows cannot refute anything")
    ok = wf["reach_pairs"] == 0 and wf["head_to_zero"] == 0
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] ...and it enters NEITHER arm-(b) "
          f"count ({wf['head_to_zero']} of {wf['reach_pairs']}), where the old "
          f"gate scored this exact 0x1000 -> 0 as 1 of 1 -- an aliasing witness "
          f"minted out of a state nobody can name")

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print_appender_witness([_s(0.0, _rec(0x1000, 1)), _s(0.1, _rec(0x2000, 2))])
    out = buf.getvalue()
    ok = ("0x0060593A" in out and "2500 ms" in out and "shut:noop" in out)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] both limits print beside the "
          f"counts: the 2500 ms dedup at 0x0060593A, and `shut:noop` writing "
          f"nothing at all")

    # LIMIT 1 SAID SOMETHING THE IMAGE REFUTES, and the only check on it was the
    # substring pair above -- which is satisfied by every sentence containing
    # "2500 ms" and "0x0060593A", including the wrong one. `0x0060593A jg
    # 0x605A2F` is the FIRST test of a chain (0x0060594B, 0x0060595E,
    # 0x0060596B, 0x0060597B), each of which jumps to the SAME append target on
    # INEQUALITY, so "it cannot append twice inside that window" is false of a
    # MOVING agent. The retired clause is asserted ABSENT and the chain asserted
    # PRESENT, address by address, so neither half can drift back.
    retired = "cannot append twice inside that window"
    want_chain = [f"0x{va:08X}" for va in APPEND_DEDUP_CHAIN]
    missing = [a for a in want_chain if a not in out]
    ok = (retired not in out and not missing and len(APPEND_DEDUP_CHAIN) == 4
          and f"0x{APPEND_TARGET:08X}" in out
          and "AND the sample still matches the cached one" in out)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] LIMIT 1 states the CONDITIONAL "
          f"window the image supports -- younger than 2500 ms AND matching the "
          f"cache -- naming all {len(APPEND_DEDUP_CHAIN)} further tests "
          f"({', '.join(want_chain)}) and the one target "
          f"0x{APPEND_TARGET:08X}; the retired \"{retired}\" clause is gone "
          f"(missing addresses: {missing or 'none'})")

    # ...and those addresses are READ FROM THE CONSTANTS, not typed into the
    # sentence. A check that greps a hard-coded literal certifies the literal.
    g9 = globals()
    keep_chain, keep_target = g9["APPEND_DEDUP_CHAIN"], g9["APPEND_TARGET"]
    try:
        g9["APPEND_DEDUP_CHAIN"] = (0x00111111,)
        g9["APPEND_TARGET"] = 0x00222222
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            print_appender_witness([_s(0.0, _rec(0x1000, 1)),
                                    _s(0.1, _rec(0x2000, 2))])
        outc = buf.getvalue()
    finally:
        g9["APPEND_DEDUP_CHAIN"], g9["APPEND_TARGET"] = keep_chain, keep_target
    ok = ("0x00111111" in outc and "0x00222222" in outc
          and all(a not in outc for a in want_chain))
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] CONTROL: moving "
          f"`APPEND_DEDUP_CHAIN`/`APPEND_TARGET` moves every address in the "
          f"printed sentence -- the text is generated from the constants a "
          f"reader can audit, not from four literals nothing feeds")

    # THE MALFORMED RECORD, which is the `except ValueError` arm of
    # `state_fields`. Returning `0, "00"` there was fully green: a zero head is
    # a REAL head value (an empty chain), so a not-read wearing one is
    # indistinguishable from a client that emptied its history -- the same
    # family of defect as the sentinel hole C4 closed, one level down.
    junk = "zz" + "00" * 27          # 56 chars: long enough, not hex
    ok = state_fields({"state_record": junk}) == (None, None)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] a `state_record` that is not hex "
          f"reads back {state_fields({'state_record': junk})} -- None per "
          f"field, never a 0 that means an empty history")
    ok = state_fields({"state_record": junk, "hist_head": 0x1234}) == (0x1234, None)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] ...and it falls back to the row's "
          f"own `hist_head` when there is one "
          f"({state_fields({'state_record': junk, 'hist_head': 0x1234})}) -- "
          f"the fallback is the documented path, and 0x1234 is not 0")
    wj = appender_witness([{"t": 0.0, "state_record": junk, FENCE_KEY: "shut:append"},
                           {"t": 0.1, "state_record": junk, FENCE_KEY: "shut:append"}])
    ok = wj["adjacent"] == 1 and wj["judged"] == 0 and wj["unjudgeable"] == 1
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] so a pair of malformed records is "
          f"UNJUDGEABLE ({wj['judged']} judged, {wj['unjudgeable']} "
          f"unjudgeable) rather than a judged pair that witnessed nothing")

    # --- THE PRINTED NUMBERS, not the dict behind them -----------------------
    #
    # Everything above asks `appender_witness` for a dict. What travels into
    # PROBE-GATEFIRE.md is the TEXT, and the two were free to disagree: arm
    # (a)'s printed `witnessed` hard-wired to 0, `judged` substituted for
    # `reach_pairs` as arm (b)'s DENOMINATOR, and the arm-coverage and PARTIAL
    # lines deleted outright were each fully green.
    #
    # ONE FIXTURE, BUILT SO THE SUBSTITUTIONS ARE VISIBLE. Every number below
    # differs from the ones a mutation would put in its place -- in particular
    # `judged` (8) != `reach_pairs` (6), so arm (b) borrowing arm (a)'s
    # denominator is caught, which two equal numbers would have waved through.
    # (`judged` and `head_pairs` are equal BY CONSTRUCTION and not by luck:
    # `state_fields` only ever returns a cache when it returned a head, so
    # cache-readable implies head-readable and no fixture can separate them.)
    mixed = [_s(0.0, _rec(0x1000, 1)),                  # p01 head+cache move
             _s(0.4, _rec(0x2000, 2)),
             {"t": 0.8, "live": [0, 0, 0], FENCE_KEY: "shut:append"},  # blind
             _s(1.2, _rec(0x3000, 2)),                  # p23 unjudgeable too
             _s(1.6, _rec(0, 2)),                       # p34 head -> 0
             _s(2.0, _rec(0, 2), "test-runs"),          # p45 label moves
             {"t": 2.4, "live": [0, 0, 0], "hist_head": 0x4000,
              FENCE_KEY: "test-runs"},                  # p56 head-only read
             _s(2.8, _rec(0x4000, 5), "test-runs"),     # p67 no change
             _s(3.2, _rec(0x4000, 9), "test-runs"),     # p78 cache alone
             _s(3.6, _rec(0x5000, 9), "test-runs"),     # p89 head alone
             _s(4.0, _rec(0x5000, 9), "test-runs")]     # p9-10 nothing
    wm = appender_witness(mixed)
    ok = (wm["adjacent"] == 10 and wm["judged"] == 8 and wm["unjudgeable"] == 2
          and wm["witnessed"] == 5 and wm["head_changed"] == 4
          and wm["cache_changed"] == 2 and wm["head_pairs"] == 8
          and wm["cache_pairs"] == 6 and wm["reach_pairs"] == 7
          and wm["head_to_zero"] == 1)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the read-back fixture judges "
          f"{wm['judged']} of {wm['adjacent']} pair(s) at "
          f"witnessed {wm['witnessed']} / head {wm['head_changed']} / cache "
          f"{wm['cache_changed']} / reach {wm['reach_pairs']} -- counted "
          f"BEFORE the printout is read, and no two of them collide")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rcm = print_appender_witness(mixed)
    outm = buf.getvalue()
    got = read_back_witness(outm)
    ok = (rcm == 0 and got.get("witnessed") == wm["witnessed"]
          and got.get("judged") == wm["judged"]
          and got.get("head_changed") == wm["head_changed"]
          and got.get("cache_changed") == wm["cache_changed"])
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] arm (a) PRINTS the dict's own "
          f"numbers: {got.get('witnessed')} of {got.get('judged')}, head "
          f"{got.get('head_changed')} / cache {got.get('cache_changed')} -- a "
          f"hard-wired zero or a borrowed count fails here")
    ok = (got.get("head_pairs") == wm["head_pairs"]
          and got.get("cache_pairs") == wm["cache_pairs"])
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the ARM-COVERAGE line is printed "
          f"and carries {got.get('head_pairs')} / {got.get('cache_pairs')} -- "
          f"deleting it leaves the two arm counts with no denominator at all, "
          f"which is the shape C4 was about")
    ok = (got.get("head_to_zero") == wm["head_to_zero"]
          and got.get("reach_pairs") == wm["reach_pairs"]
          and wm["reach_pairs"] != wm["judged"])
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] arm (b) prints "
          f"{got.get('head_to_zero')} of {got.get('reach_pairs')} and NOT of "
          f"{wm['judged']} -- its denominator is the label-held-still "
          f"population, and the two differ in this fixture on purpose")
    ok = (got.get("partial_judged") == wm["judged"]
          and got.get("partial_adjacent") == wm["adjacent"]
          and got.get("partial_unjudgeable") == wm["unjudgeable"])
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and the PARTIAL line is printed "
          f"whenever a pair could not be read: {got.get('partial_judged')} of "
          f"{got.get('partial_adjacent')} judged, "
          f"{got.get('partial_unjudgeable')} unjudgeable -- deleting it hides "
          f"that the arms above are over a subset")
    return bad + _floor("9", n, 24), n


def _selftest_spellings():
    """C9: two spellings accepted on read, one printed, none inventing a state."""
    import contextlib
    import io
    bad = n = 0
    print("\n10. C9: the vault's OLD `:apply` rows are read, and printed `:append`")

    got = {k: classify_reach(k) for k in
           ("shut:apply", "world1:apply", "shut:append", "world1:append",
            "shut:noop", "test-runs", "unread:record-unreadable",
            "a-label-from-the-future", None)}
    ok = (got["shut:apply"] == "fenced" and got["world1:apply"] == "fenced"
          and got["shut:append"] == "fenced" and got["shut:noop"] == "fenced"
          and got["test-runs"] == "reachable")
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the pre-rename spellings classify "
          f"as the SAME state as the new ones -- a capture written before "
          f"2026-08-20 is read, not silently dropped into the hole bucket")
    ok = (got["unread:record-unreadable"] == "unread" and got[None] == "unread"
          and got["a-label-from-the-future"] == "unread")
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] while a could-not-read, a missing "
          f"sample and a label this file has never heard of all land in "
          f"`unread` -- refusing to guess is the point of the third bucket")

    legacy = [_fake_pair(1, "shut:apply", _rec(0x1000, 1)),
              _fake_pair(2, "test-runs", _rec(0x2000, 2))]
    counts, have, total, nleg = fence_rows(legacy)
    ok = (have == 2 and total == 2 and nleg == 1
          and counts.get("shut:append") == 1 and "shut:apply" not in counts)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] fence_rows tallies the old row "
          f"under the NEW key ({counts}) and reports {nleg} legacy-spelled "
          f"row(s) as provenance")

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print_fence(legacy, [(2.0, 900.0, 400.0, 20.0, 1.0)])
    out = buf.getvalue()
    ok = "shut:append" in out and "shut:apply" not in out
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and the printed output carries "
          f"`shut:append` and never `shut:apply` -- both read, one printed")
    ok = "pre-rename spelling" in out
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] with a NOTE saying the row was "
          f"normalised, because a normalisation the reader cannot see is one "
          f"they cannot audit")
    ok = ("without any gate being evaluated" not in out
          and "INFERENCE" in out
          and "never the instruction pointer" in out)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and every sentence about "
          f"0x00605840 running is labelled an INFERENCE with its premise "
          f"named -- the sampler reads a record, never the instruction pointer")
    return bad + _floor("10", n, 6), n


# The lines `print_fence` emits, keyed off a distinctive substring of the
# sentence that carries each number, for the same reason `_WITNESS_FIELDS` is:
# a deleted line must arrive as an ABSENT KEY and never as a zero.
_FENCE_LINES = (
    ("refused_unread", r"REFUSED: (\d+) of \d+ carry no state this file can read"),
    ("refused_have", r"REFUSED: \d+ of (\d+) carry no state this file can read"),
    ("partial_have", r"PARTIAL: (\d+) of \d+ paired samples carry the field"),
    ("partial_total", r"PARTIAL: \d+ of (\d+) paired samples carry the field"),
    ("partial_says_have", r"the shares below are over (\d+), not \d+"),
    ("partial_says_total", r"the shares below are over \d+, not (\d+)"),
    ("note_legacy", r"NOTE: (\d+) of \d+ row\(s\) carry movetap's"),
    ("note_den", r"NOTE: \d+ of (\d+) row\(s\) carry movetap's"),
    ("witness_pairs", r"over (\d+) consecutive pair\(s\) of \d+ "),
    ("witness_pop", r"over \d+ consecutive pair\(s\) of (\d+) "),
    ("jump_n", r"the fence at each hard jump \(n=(\d+)\)"),
)


def read_back_fence(out):
    """{field: printed_int} parsed from `print_fence`'s own text."""
    seen = {}
    for name, pat in _FENCE_LINES:
        m = re.search(pat, out)
        if m:
            seen[name] = int(m.group(1))
    return seen


def _dist_row(out, label):
    """(count, share, bucket) off the distribution row for `label`, or None.

    THE WHOLE ROW AND NOT THE SHARE ALONE. This used to read the percentage and
    stop, which left the printer free to disagree with `classify_reach` about
    what the row IS: an unrecognised label printed as a real client state at
    90.0% while the classifier called it a hole. Reading the bucket column here
    is what makes that disagreement a FAIL rather than a paragraph in §6.
    """
    m = re.search(r"^\s*" + re.escape(label)
                  + r"\s+(\d+)\s+([\d.]+)%\s+(\S+)\s*$", out, re.M)
    return (int(m.group(1)), float(m.group(2)), m.group(3)) if m else None


def _selftest_print_fence():
    """C4+C5 IN THE REPORT: what `main()` actually prints, not what it could.

    THE DEFECT THIS PINS, and it is the same one twice at two altitudes. The
    round before this pinned the jump tally at the DICT while the operator reads
    the TEXT. This round found the text pinned at the FUNCTION while the
    operator reads the PIPELINE: deleting `print_appender_witness(pop, indent,
    name)` from `print_fence` -- the only path `main()` takes -- left
    `--selftest` at 49/49 and `test_movesync.py` at 147/147, with the whole of
    C5 gone from the output. Six more branches of `print_fence` judged ZERO rows
    in the entire suite and every mutation of them was green: the PARTIAL line
    deleted, the per-label share denominator moved from `have` to `total`, the
    `samples=` stream ignored while the population was still NAMED as the full
    one, the population REFUSAL deleted, the legacy NOTE quoting `total` where
    it means `have`, and `if rc: return rc` making the population refusal
    swallow the tally and the witness -- which is precisely the substitution C4
    exists to undo.

    ONE FIXTURE TAKES ALL OF IT, because these branches only co-occur on the
    production path: `samples=` supplied AND `have < total` AND unread at or
    above the bar. Every number in it is distinct from the one a substitution
    would put in its place.
    """
    import contextlib
    import io
    bad = n = 0
    print("\n11. C4+C5 in the REPORT: print_fence's own output, refusal and all")

    rec = _rec(0x1000, 1)
    pairs = [_fake_pair(1), _fake_pair(2),
             _fake_pair(3, "shut:apply", rec), _fake_pair(4, "shut:append", rec),
             _fake_pair(5, "shut:append", rec), _fake_pair(6, "test-runs", rec),
             _fake_pair(7, "unread:record-unreadable"),
             _fake_pair(8, "unread:record-unreadable")]
    jumps = [(float(t), 900.0, 400.0, 20.0, 0.1) for t in (5, 6, 7)]
    counts, have, total, legacy = fence_rows(pairs)
    rows = fence_at_jumps(pairs, jumps)
    tl = jump_tally(rows)
    # THE COUNTS FIRST, AND THEY ARE ALL DIFFERENT. 6 != 8 makes a `have`/`total`
    # swap visible; 3 of 6 shut:append is 50.0% over `have` and 37.5% over
    # `total`; 2 of 6 unread is over the 25% bar while 2 of 8 would be AT it, so
    # the refusal below is over the population the code claims.
    ok = (len(pairs) == 8 and have == 6 and total == 8 and legacy == 1
          and counts.get("shut:append") == 3 and counts.get("test-runs") == 1
          and counts.get("unread:record-unreadable") == 2
          and len(rows) == 3 and tl["reachable"] == 1 and tl["fenced"] == 2
          and tl["unread"] == 0)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the fixture carries {have} of "
          f"{total} paired samples with the field ({legacy} legacy-spelled, "
          f"{counts.get('unread:record-unreadable')} unread) and {len(rows)} "
          f"jump row(s) tallying {tl['reachable']}/{tl['fenced']}/"
          f"{tl['unread']} -- counted before print_fence is called at all")

    def _s11(t, head, cache):
        return {"t": t, "live": [0, 0, 0], "state_record": _rec(head, cache),
                FENCE_KEY: "shut:append"}
    samples = [_s11(0.0, 0x1000, 1), _s11(0.4, 0x2000, 1), _s11(0.8, 0x2000, 2),
               _s11(1.2, 0x2000, 2), _s11(1.6, 0x3000, 2), _s11(2.0, 0x3000, 3),
               _s11(2.4, 0x3000, 3), _s11(2.8, 0x4000, 3), _s11(3.2, 0x4000, 4),
               _s11(3.6, 0x4000, 4), _s11(4.0, 0x5000, 4)]
    wfull = appender_witness(samples)
    wpaired = appender_witness([s for _t, _p, s, _g in pairs])
    ok = (len(samples) == 11 and wfull["adjacent"] == 10
          and wfull["judged"] == 10 and wfull["witnessed"] == 7
          and wpaired["adjacent"] == 7 and wpaired["judged"] == 3
          and wpaired["witnessed"] == 0)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and the FULL sample stream is a "
          f"different population from the paired subset: {len(samples)} "
          f"sample(s) / {wfull['judged']} judged / {wfull['witnessed']} "
          f"witnessed against {len(pairs)} / {wpaired['judged']} / "
          f"{wpaired['witnessed']} -- so a printer that quietly uses the subset "
          f"cannot print the same numbers")

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = print_fence(pairs, jumps, samples=samples)
    out = buf.getvalue()
    got = read_back_fence(out)
    ok = (rc == 1 and got.get("refused_unread") == 2
          and got.get("refused_have") == have)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the POPULATION refusal fires and "
          f"names its own denominator: {got.get('refused_unread')} of "
          f"{got.get('refused_have')} carry no state this file can read "
          f"(rc {rc})")

    ok = (got.get("partial_have") == have and got.get("partial_total") == total
          and got.get("partial_says_have") == have
          and got.get("partial_says_total") == total)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the PARTIAL line prints "
          f"{got.get('partial_have')} of {got.get('partial_total')} and says "
          f"the shares are over {got.get('partial_says_have')}, not "
          f"{got.get('partial_says_total')} -- deleting it hides that every "
          f"share below is over a subset")

    row = _dist_row(out, "shut:append")
    share = row[1] if row else None
    over_have = round(100.0 * counts["shut:append"] / have, 1)
    over_total = round(100.0 * counts["shut:append"] / total, 1)
    ok = (row is not None and row[0] == counts["shut:append"]
          and abs(share - over_have) < 0.05
          and abs(share - over_total) > 0.05 and row[2] == "fenced")
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and the per-label shares really are "
          f"over `have`: shut:append prints {share}% in bucket "
          f"`{row[2] if row else None}`, where {counts['shut:append']}/{have} "
          f"is {over_have}% and the same count over {total} would be "
          f"{over_total}%")

    ok = got.get("note_legacy") == legacy and got.get("note_den") == have
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the legacy NOTE's denominator is "
          f"`have` too: it prints {got.get('note_legacy')} of "
          f"{got.get('note_den')} row(s) carrying the pre-rename spelling, "
          f"where `have` is {have} and `total` is {total}")

    # THE ORDER IS THE CLAIM. `print_fence`'s docstring says the tally and the
    # witness print on every path INCLUDING the refusing one; inserting
    # `if rc: return rc` above them was green, and that is one refusal standing
    # in for two others.
    i_ref = out.find("carry no state this file can read")
    i_tal = out.find("THREE-WAY over the BEFORE column")
    i_wit = out.find("APPENDER WITNESS")
    seen3 = read_back_three_way(out)
    ok = (-1 < i_ref < i_tal < i_wit and len(seen3) == 3
          and seen3["reachable"][0] == tl["reachable"]
          and seen3["fenced"][0] == tl["fenced"]
          and seen3["unread"][0] == tl["unread"]
          and got.get("jump_n") == len(rows)
          and "1 of 3 snap(s) began with the record in the ONE state" in out)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the jump tally AND the witness "
          f"still print BELOW the population refusal (at {i_ref} < {i_tal} < "
          f"{i_wit}), with the three-way cells intact "
          f"({ {k: v[0] for k, v in sorted(seen3.items())} }) -- a refusal that "
          f"swallows the two sections beneath it is the pre-C4 fold again")

    ok = (got.get("witness_pop") == len(samples)
          and got.get("witness_pairs") == wfull["adjacent"]
          and "movetap sample(s)" in out and "PAIRED sample(s)" not in out)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the witness's population is the "
          f"stream the caller handed in: {got.get('witness_pairs')} pair(s) of "
          f"{got.get('witness_pop')} movetap sample(s), which is "
          f"{len(samples)} and not the {len(pairs)} paired ones")

    gotw = read_back_witness(out)
    ok = (gotw.get("witnessed") == wfull["witnessed"]
          and gotw.get("judged") == wfull["judged"]
          and gotw.get("head_changed") == wfull["head_changed"]
          and gotw.get("cache_changed") == wfull["cache_changed"]
          and wfull["witnessed"] != wpaired["witnessed"])
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and its NUMBERS are that stream's: "
          f"{gotw.get('witnessed')} of {gotw.get('judged')} judged, head "
          f"{gotw.get('head_changed')} / cache {gotw.get('cache_changed')} -- "
          f"deleting the `print_appender_witness` call from print_fence, or "
          f"feeding it the paired subset, empties or moves every one of them")

    # THE MIRROR, or the two refusals above are constants. Same machinery, two
    # rows relabelled and no `samples=`: nothing refuses, the PARTIAL line does
    # not print because there is nothing partial, and the witness falls back to
    # the PAIRED population WITH THAT NAME.
    # ...and its `total` is 7 rather than 8 ON PURPOSE, so a PARTIAL line
    # hard-wired to the first fixture's "6 of 8" fails here.
    mirror = pairs[1:6] + [_fake_pair(7, "shut:append", rec),
                           _fake_pair(8, "shut:append", rec)]
    m_counts, m_have, m_total, _m_leg = fence_rows(mirror)
    ok = m_have == 6 and m_total == 7 and not any(
        str(k).startswith("unread:") for k in m_counts)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the mirror fixture carries "
          f"{m_have} of {m_total} with the field and no unread row at all -- "
          f"counted before it is judged")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rcm = print_fence(mirror, jumps)
    outm = buf.getvalue()
    gm = read_back_fence(outm)
    ok = (rcm == 0 and "REFUSED" not in outm
          and gm.get("partial_have") == m_have
          and gm.get("partial_total") == m_total
          and gm.get("witness_pop") == len(mirror)
          and "PAIRED sample(s)" in outm)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and with no unread row it does NOT "
          f"refuse (rc {rcm}), still prints PARTIAL "
          f"{gm.get('partial_have')} of {gm.get('partial_total')}, and names "
          f"the fallback population `PAIRED sample(s)` over "
          f"{gm.get('witness_pop')} -- so both the refusal and the population "
          f"name read the arguments rather than being constants")

    # THE PRINTER AND THE CLASSIFIER DISAGREED, AND THE PRINTER WAS THE WRONG
    # ONE. `classify_reach` -- the function every check above interrogates --
    # lands a label this file has never heard of in `unread`. The distribution
    # loop's own hole tally read `str(k).startswith("unread:")`, which catches
    # movetap's sentinel and nothing else, so an UNRECOGNISED `gate_reach`
    # printed as a REAL CLIENT STATE with a percentage beside it and no refusal:
    # measured at 90.0% over n = 10, rc 0. Same defect class as C4, one section
    # ABOVE the C4 site, in the distribution `PROBE-GATEFIRE.md` §6 quotes.
    unknown = "a-label-from-the-future"
    pairs5 = [_fake_pair(t, unknown) for t in range(1, 10)]
    pairs5.append(_fake_pair(10, "test-runs"))
    c5, have5, total5, _leg5 = fence_rows(pairs5)
    old_rule = sum(c for k, c in c5.items() if str(k).startswith("unread:"))
    new_rule = sum(c for k, c in c5.items() if classify_reach(k) == "unread")
    ok = (len(pairs5) == 10 and have5 == 10 and total5 == 10
          and c5.get(unknown) == 9 and c5.get("test-runs") == 1
          and classify_reach(unknown) == "unread"
          and old_rule == 0 and new_rule == 9)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the disagreement fixture: {have5} "
          f"of {total5} paired samples carry the field, {c5.get(unknown)} of "
          f"them a label this file has never heard of -- which "
          f"`classify_reach` calls `{classify_reach(unknown)}` while the "
          f"printer's old `unread:`-prefix rule counted {old_rule} of them "
          f"against the classifier's {new_rule}")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc5 = print_fence(pairs5, [])
    out5 = buf.getvalue()
    row5 = _dist_row(out5, unknown)
    want_row = ("   a-label-from-the-future                 9   90.0%  unread")
    ok = (row5 == (9, 90.0, "unread")
          and _line_with(out5, unknown) == want_row)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] its distribution row prints "
          f"{want_row!r} -- the BUCKET is the classifier's own verdict beside "
          f"the share, so a row the dict calls a hole can no longer read as a "
          f"state of the client; got {_line_with(out5, unknown)!r}")
    ref5 = _line_with(out5, "carry no state this file can read")
    want_ref5 = ("   REFUSED: 9 of 10 carry no state this file can read -- a "
                 "could-not-read sentinel, or a label it has never heard of. "
                 "No share above is a fact about the client. This bar is over "
                 "the WHOLE paired population and says nothing about the jump "
                 "rows below, which carry their own.")
    ok = rc5 == 1 and ref5 == want_ref5
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and the population refusal FIRES on "
          f"it (rc {rc5}), exactly {want_ref5!r} -- the old rule counted 0 "
          f"holes here and printed a 90.0% share of a client state that does "
          f"not exist, with no refusal at all; got {ref5!r}")

    # THE MIRROR, or the refusal above is a rule about the number 9. Same shape,
    # same 90.0%, a label the file DOES know: nothing refuses and the bucket
    # says `fenced`. So the printer is reading `classify_reach` and not the
    # count.
    pairs6 = [_fake_pair(t, "shut:append") for t in range(1, 10)]
    pairs6.append(_fake_pair(10, "test-runs"))
    c6, have6, _t6, _l6 = fence_rows(pairs6)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc6 = print_fence(pairs6, [])
    out6 = buf.getvalue()
    row6 = _dist_row(out6, "shut:append")
    ok = (have6 == 10 and c6.get("shut:append") == 9 and rc6 == 0
          and row6 == (9, 90.0, "fenced")
          and _line_with(out6, "carry no state this file can read") is None)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] MIRROR: the same {c6.get('shut:append')} "
          f"of {have6} at the same {row6[1] if row6 else None}% under a label "
          f"the file KNOWS prints bucket `{row6[2] if row6 else None}` and does "
          f"NOT refuse (rc {rc6}) -- the refusal reads the classifier, not the "
          f"share")
    return bad + _floor("11", n, 15), n
