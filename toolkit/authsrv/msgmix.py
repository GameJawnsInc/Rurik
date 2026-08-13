"""What our server sends and what it drops, against what ArenaNet's does.

    python toolkit/authsrv/msgmix.py                 # whole gamesrv corpus
    python toolkit/authsrv/msgmix.py --sessions 6    # newest 6 only (the old behaviour)
    python toolkit/authsrv/msgmix.py --rank-on sweep # rank the s2c gap on sweep runs

WHY THIS EXISTS. Until 2026-08-10 this comparison could not be READ: one
GAME_SMSG opcode of 487 had a name, so a table of counts was a table of numbers.
With 21 named it becomes a ranked list of what our server does not do, measured
against ArenaNet's own traffic rather than against anyone's opinion.

THREE DEFECTS FIXED 2026-08-13, and each of them made this tool answer confidently
about a corpus it had not read. They are recorded here rather than in a commit
message because the numbers this file prints get quoted into PLAN.md and into
studies, and a reader needs to know which of them are new and why the old ones
will not reproduce.

  (1) `sorted(..., key=os.path.getmtime)[-6:]` read SIX of 439 gamesrv captures
      (2026-08-13; the corpus grows, so every count in this docstring is dated) --
      2.0% of the corpus, chosen by nothing but recency. It was a debugging
      convenience that outlived its debugging. studies/recon FINDINGS D is the cost:
      "21,543 s2c over 8 connections" was quoted as a corpus figure and was a
      windowed read of the newest six files. The default is now EVERY capture; the
      whole corpus is 82 MB and 508k lines and reads in about 1.5 s, so the window
      was never buying anything. `--sessions N` keeps the window reachable, and
      exists so the old number can be reproduced deliberately rather than by accident.

  (2) `if r.get("kind") != "sent": continue` -- `sent` is the server's OUTBOUND log,
      so this tool, whose entire job is ranking what we do not implement, read ZERO
      of the client-to-server direction. Every c2s message in the corpus is a
      `decoded` record. Fixing (1) alone still yields zero c2s and fixing (2) alone
      reads six files, which is why they are one change.

  (3) 948 was in circulation as a c2s drop count and is a count of LOG RECORDS, not
      of messages. `note_unhandled` writes one record per (session, opcode) FIRST
      OCCURRENCE and counts the rest silently, so the record count is a count of
      distinct opcode sightings. studies/recon FINDINGS B caught two digs
      disagreeing by exactly that number. This file now prints both quantities on
      adjacent lines with their denominators, because the misread is cheap to repeat
      and the two numbers differ by more than an order of magnitude.

TWO POPULATIONS, AND WHY THEY ARE NEVER POOLED. 257 of 439 gamesrv captures are
unattended `smsgsweep` runs, not played sessions. Pooling them is not a rounding
error, it is the destruction of the result:

  * a played session's server emits 101 DISTINCT s2c opcodes; a sweep session's
    emits 381, because transmitting opcodes we would never otherwise send IS what
    the sweep does. 320 opcodes appear in sweep captures and in no played one.
    Pooled, our server looks like it sends 421 of 487 GAME_SMSG opcodes and the
    "opcodes ArenaNet sends that we NEVER send" list -- the reason this tool
    exists -- collapses to almost nothing.
  * the sweep's c2s half is dominated by login and instance-load boilerplate,
    because `sweeploop` reconnects hundreds of times and nobody plays. That is
    what puts MISSION_MASK_REPORT and the machine-spec pair at the top of a pooled
    drop ranking: they arrive roughly once per connection, so the ranking measures
    how many times we reconnected.

A capture is SWEEP if it holds a `sent` record whose label carries
`PROBE[smsgsweep]` -- the same witness `smsgsweep.read_capture` scores a run by.
That is a real weakness stated rather than hidden (the label is prose), and it
fails toward calling a sweep run "played", which is the direction that pollutes
the played population. It has not happened in this corpus: every capture with a
sweep label has thousands of them.

WHAT COUNTS AS DROPPED, AND THE ONE THING THIS CANNOT KNOW. A c2s message is
DROPPED when the server itself flagged its opcode with `note_unhandled` in THAT
session. That is a measurement, not an inference, and it has an oracle: for every
capture carrying an `unhandled_summary` the server's own total must equal the count
this file derives from the `decoded` records. The two share no code and the archive
could refuse: 326 of 326 agree and 0 disagree as of 2026-08-13, and the run prints
the tally every time so a future divergence is loud rather than averaged away.

But `note_unhandled` landed on 2026-08-12T00:19:42Z (the earliest capture in the
corpus that carries one of its records; 94 captures are older and 0 of those 94
carry one). Before it, the dispatch chains had no `else` at all -- D9(a) -- so the
messages were dropped and NOTHING WAS LOGGED. Those messages cannot be attributed
from the capture, so they go in their own bucket, are printed under their own
heading, and are never added into the headline. Imputing them by opcode is exactly
the pooling this repo keeps recording as a defect, and the corpus refutes it
directly: 0x000C is flagged in 2 messages and handled in the other 42, because the
ping round trip gained a handler partway through. An "any session flagged it, so
all of them dropped it" rule over-attributes that opcode by 21x.

WHAT IT IS NOT. Rates depend on what happened in the session. Ours comes from
loopback runs whose clicks mostly land outside the server's 1-second
position-freshness window, so AGENT_MOVE_TO_POINT reads 0 -- that is a true
statement about those runs, not a claim that the server can never issue a move.
Read a 0 as "did not happen here", and go and look at why before believing it
means "cannot".

Both sides are real captures: ours from vault/captures/gamesrv, theirs from the two
live tapes. Rates are per 100 seconds of in-world time, because the sessions differ
in length by an order of magnitude and raw counts would say nothing.

The gamesrv directory is LIVE -- a parallel session running the harness appends to
it while this runs, and the file count moved three times during the session that
wrote this. The snapshot is taken once, up front, and its size and newest member are
printed, so a quoted number names the corpus it came from.

Standard library only.
"""
import argparse
import collections
import json
import os
import sys

# Resolve the tree from THIS FILE, never from a hardcoded path. It used to say
# `ROOT = r"C:\gd\Rurik"` and chdir there, so a copy of this script running in a
# worktree imported MAIN's toolkit and measured main's code while sitting in a
# branch -- the failure CLAUDE.md's "establish which tree you are actually in" rule
# is about, in its worst form, because an absolute path does not even have the
# decency to be relative to the shell. It surfaced on 2026-08-11 only because a
# function added in the worktree was missing from the module this imported.
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "toolkit"))
sys.path.insert(0, os.path.join(ROOT, "toolkit", "authsrv"))
sys.path.insert(0, os.path.join(ROOT, "toolkit", "schema"))

# No chdir either. Every path below is absolute: one resolved from this file for the
# tree, one resolved by vaultpath for the vault. Those are two different questions and
# a chdir answered both with the same wrong guess.
OVERRIDES = os.path.join(ROOT, "schema", "overrides.json")
OV = json.load(open(OVERRIDES, encoding="utf-8"))["channels"]

# The two live tapes this comparison is measured against.
LIVE_STAMPS = ("20260807T143055", "20260810T235916")

# The witness that a capture is an unattended sweep run rather than a played session.
# `smsgsweep.read_capture` uses the same string on the same field; it is duplicated
# here rather than imported so that this module stays importable (and testable) with
# no vault and no server module on the path.
SWEEP_LABEL = "PROBE[smsgsweep]"


def name(channel, op):
    """The catalog's name for an opcode, or "" -- never a borrowed one.

    Both directions now need this. GAME_CMSG and GAME_SMSG number independently and
    a name taken from the wrong channel is worse than no name at all, which is why
    the channel is a parameter rather than a default.
    """
    r = OV.get(channel, {}).get(str(op))
    return r["name"] if r and "name" in r else ""


# ---- the pure half: one capture in, one summary out -----------------------
#
# Everything below this line down to `read_arenanet` is a pure function over dicts.
# That is deliberate and is what `test_msgmix.py` exercises: the population split and
# the record-versus-message arithmetic are the two things this tool has been wrong
# about, and neither of them needs a vault, a socket or a client to check.


def scan_session(records, sweep_label=SWEEP_LABEL):
    """Summarise one gamesrv capture from its records. Pure; no I/O.

    `records` is any iterable of already-parsed record dicts. Returns a dict:

      sweep       bool    -- an unattended smsgsweep run rather than a played session
      probes      set     -- every PROBE[...] tag seen, for the report's own footnote
      s2c         Counter -- opcode -> messages the server SENT   (`sent` records)
      c2s         Counter -- opcode -> messages the client sent   (`decoded` records)
      flagged     set     -- opcodes THIS session logged as unhandled-but-known
      unh_records int     -- `unhandled` RECORDS, which is not the message count
      summary     int|None-- the server's own drop total at disconnect, when it got there
      seconds     float   -- span of the s2c timestamps
      wall        str|None-- ISO stamp of the first record, used only for the era split

    The `sent`/`decoded` asymmetry is the defect this file was carrying: the recorder
    logs the two directions with different record kinds, and reading only `sent` reads
    only ourselves. `smsgsweep.read_capture`'s own docstring warns about the mirror
    image of this ("reading frames finds zero stimuli"), which is how one tool in this
    directory knew and the other did not.
    """
    out = {
        "sweep": False,
        "probes": set(),
        "s2c": collections.Counter(),
        "c2s": collections.Counter(),
        "flagged": set(),
        "unh_records": 0,
        "summary": None,
        "seconds": 0.0,
        "wall": None,
    }
    lo = hi = None
    for r in records:
        if not isinstance(r, dict):
            continue
        if out["wall"] is None and r.get("wall"):
            out["wall"] = r["wall"]
        kind = r.get("kind")
        if kind == "sent":
            label = r.get("label") or ""
            if sweep_label in label:
                out["sweep"] = True
            if "PROBE[" in label:
                tag = label.split("PROBE[", 1)[1].split("]", 1)[0]
                out["probes"].add(tag)
            try:
                op = int(r["opcode"])
                t = float(r["t"])
            except (KeyError, TypeError, ValueError):
                continue
            out["s2c"][op] += 1
            lo = t if lo is None else min(lo, t)
            hi = t if hi is None else max(hi, t)
        elif kind == "decoded":
            # THE c2s DIRECTION. Every game-channel message the client sent us is one
            # of these, opcode already stripped of the client's 0x8000 mask by the
            # recorder (labelrun.py:52 says so, and test_cmsgnames is the file that
            # would catch it if it stopped being true).
            try:
                out["c2s"][int(r["opcode"])] += 1
            except (KeyError, TypeError, ValueError):
                continue
        elif kind == "unhandled":
            out["unh_records"] += 1
            try:
                out["flagged"].add(int(r["opcode"]))
            except (KeyError, TypeError, ValueError):
                continue
        elif kind == "unhandled_summary":
            try:
                out["summary"] = int(r["total"])
            except (KeyError, TypeError, ValueError):
                pass
    if lo is not None and hi is not None:
        out["seconds"] = max(hi - lo, 0.0)
    return out


def population(sess):
    """"sweep" or "played". The only split this tool makes, and it makes it early."""
    return "sweep" if sess["sweep"] else "played"


def dropped_messages(sess):
    """Counter of c2s MESSAGES this session dropped, by opcode.

    A message is dropped when THIS session flagged its opcode. Not "some session
    flagged it": 0x000C is flagged in 2 messages of 44 across the corpus because the
    ping handler arrived partway through the captures, and a rule that generalised
    one session's flag to every session would report 44.

    This is the quantity `report_unhandled` prints as `total`, rebuilt from the other
    side of the capture -- which is what makes it checkable rather than trusted.
    """
    return collections.Counter(
        {op: n for op, n in sess["c2s"].items() if op in sess["flagged"]})


def dropped_records(sess):
    """The `unhandled` RECORD count -- one per (session, opcode) first occurrence.

    Not a message count, and the reason this function exists at all is that the two
    were confused: 948 of these was quoted as a message figure and two digs
    disagreed by exactly it (studies/recon FINDINGS B). Kept as a named function so
    the report can print both and label which is which.
    """
    return sess["unh_records"]


def summary_agrees(sess):
    """None if the session never reported; else whether the server and we agree.

    THE ORACLE. `report_unhandled` counts drops as they happen, in the dispatch
    chain; `dropped_messages` rebuilds the same number afterwards from the `decoded`
    stream and the `unhandled` flags. They share no code and can disagree, so this is
    an assertion the artifact can refute rather than one our decoder forces true.
    """
    if sess["summary"] is None:
        return None
    return sum(dropped_messages(sess).values()) == sess["summary"]


def instrumentation_era(sessions):
    """The wall clock of the earliest capture carrying an `unhandled` record.

    D9(a)'s `else` arms did not always exist. Captures older than this logged nothing
    when they dropped a message, so their drops are unmeasurable rather than zero,
    and the report must say which bucket a capture is in instead of quietly counting
    it as clean.

    Derived from the corpus rather than hardcoded, because a hardcoded date is a
    claim about a commit that nothing here can check. The direction of error is
    stated: a session AFTER the boundary that happened to drop nothing is
    indistinguishable from an instrumented clean one and is correctly called
    instrumented; a session BEFORE it that was instrumented and clean would be called
    un-instrumented, which moves its messages into the unattributable bucket and
    never inflates the flagged number. Returns None if nothing in the corpus is
    instrumented, in which case there is no boundary to draw.
    """
    stamps = [s["wall"] for s in sessions if s["unh_records"] and s["wall"]]
    return min(stamps) if stamps else None


def instrumented(sess, boundary):
    """Whether this session's server would have logged a drop had one happened."""
    if boundary is None:
        return False
    return bool(sess["wall"]) and sess["wall"] >= boundary


def unattributable(sess, boundary, flagged_anywhere):
    """c2s messages in a PRE-instrumentation capture whose opcode is flagged elsewhere.

    Reported under its own heading and never summed into the drop count. It is the
    honest name for "we cannot tell": the server of the day had no `else`, so these
    were probably dropped, and "probably" is not a measurement.
    """
    if instrumented(sess, boundary):
        return collections.Counter()
    return collections.Counter(
        {op: n for op, n in sess["c2s"].items() if op in flagged_anywhere})


def aggregate(sessions, boundary, flagged_anywhere):
    """Pool a list of sessions that are already known to be ONE population."""
    agg = {
        "files": len(sessions),
        "s2c": collections.Counter(),
        "c2s": collections.Counter(),
        "dropped": collections.Counter(),
        "unattributable": collections.Counter(),
        "unh_records": 0,
        "seconds": 0.0,
        "probes": set(),
        "pre_files": 0,
    }
    for s in sessions:
        agg["s2c"].update(s["s2c"])
        agg["c2s"].update(s["c2s"])
        agg["dropped"].update(dropped_messages(s))
        agg["unattributable"].update(
            unattributable(s, boundary, flagged_anywhere))
        agg["unh_records"] += dropped_records(s)
        agg["seconds"] += s["seconds"]
        agg["probes"] |= s["probes"]
        if not instrumented(s, boundary):
            agg["pre_files"] += 1
    return agg


# ---- the I/O half --------------------------------------------------------

def gamesrv_snapshot(directory, sessions_limit=0):
    """The file list, taken ONCE. Newest last.

    Snapshotting matters here: a parallel session running the harness appends to this
    directory, and the count moved from 415 to 439 during the session that rewrote
    this file. A tool that re-listed mid-run would print a total that matched none of
    its own sub-totals.
    """
    files = sorted(
        (os.path.join(directory, f)
         for f in os.listdir(directory)
         if f.endswith(".jsonl")),
        key=os.path.getmtime)
    return files[-sessions_limit:] if sessions_limit else files


def read_session_file(path):
    """One capture off disk into `scan_session`. Bad lines are skipped, not fatal."""
    def records():
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    yield json.loads(line)
                except ValueError:
                    continue
    return scan_session(records())


def read_arenanet(codec_obj):
    """ArenaNet's s2c mix and its in-world seconds, from the two live tapes."""
    import tape
    theirs, secs = collections.Counter(), 0.0
    for stamp in LIVE_STAMPS:
        cap = tape.resolve_capture(stamp)
        for conn in tape.chain(cap):
            meta, events = tape.load_tape(cap, conn)
            secs += meta["seconds"]
            # decode_all rather than a hand-rolled carry across events. The carry
            # version this replaces was CORRECT -- measured 2026-08-11, it yields the
            # same message sequence as framing the stream whole on all ten live tapes
            # -- but it was unguarded: it discarded the framing error, so a tape that
            # stopped framing would have quietly lowered every rate printed below.
            # strict=True refuses instead, which is the point of a script whose output
            # gets quoted.
            msgs, _receipt = tape.decode_all(events, codec_obj, "GAME_SMSG")
            theirs.update(op for _t, op, _v in msgs)
    return theirs, secs


# ---- report --------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sessions", type=int, default=0, metavar="N",
                    help="read only the newest N gamesrv captures (default: all). "
                         "The old behaviour was a hardcoded 6 of 439 (2026-08-13).")
    ap.add_argument("--rank-on", choices=("played", "sweep"), default="played",
                    help="which population drives the s2c gap table (default: "
                         "played -- a sweep session sends opcodes on purpose and "
                         "would answer 'we send everything')")
    ap.add_argument("--top", type=int, default=26, help="rows in the s2c table")
    args = ap.parse_args(argv)

    import codec
    import vaultpath
    codec_obj = codec.Codec(overrides=OVERRIDES)

    # vaultpath, not a relative `vault/...` walk: a worktree has no vault of its own,
    # so the relative form resolved to nothing and died inside os.listdir.
    # require_dir raises and names the vault instead -- the same door
    # tape.resolve_capture already covers.
    gamesrv = vaultpath.require_dir("captures", "gamesrv",
                                    why="our own server's half of this comparison")
    files = gamesrv_snapshot(gamesrv, args.sessions)
    if not files:
        print(f"no .jsonl captures under {gamesrv}")
        return 1

    sessions = [read_session_file(p) for p in files]
    boundary = instrumentation_era(sessions)
    flagged_anywhere = set()
    for s in sessions:
        flagged_anywhere |= s["flagged"]

    pops = {
        "played": aggregate([s for s in sessions if population(s) == "played"],
                            boundary, flagged_anywhere),
        "sweep": aggregate([s for s in sessions if population(s) == "sweep"],
                           boundary, flagged_anywhere),
    }

    print(f"corpus : {len(files)} gamesrv capture(s) under {gamesrv}")
    print(f"         snapshot taken once; newest is "
          f"{os.path.basename(files[-1])}"
          + ("" if not args.sessions else
             f"  [--sessions {args.sessions}: a WINDOW, not the corpus]"))
    print(f"         `unhandled` logging (D9a) first appears "
          f"{boundary or 'nowhere in this window'}; "
          f"{pops['played']['pre_files'] + pops['sweep']['pre_files']} capture(s) "
          f"predate it and could not log a drop")

    # ---- populations, before anything is pooled --------------------------
    print("\nPOPULATIONS  (SWEEP = a capture holding a `sent` record labelled "
          f"{SWEEP_LABEL})")
    print(f"{'':9} {'files':>6} {'s2c msgs':>10} {'s2c ops':>8} {'in-world s':>11} "
          f"{'c2s msgs':>9} {'c2s ops':>8}")
    for pop in ("played", "sweep"):
        a = pops[pop]
        print(f"  {pop:7} {a['files']:6} {sum(a['s2c'].values()):10} "
              f"{len(a['s2c']):8} {a['seconds']:11.0f} "
              f"{sum(a['c2s'].values()):9} {len(a['c2s']):8}")
    only_sweep = set(pops["sweep"]["s2c"]) - set(pops["played"]["s2c"])
    both = set(pops["played"]["s2c"]) | set(pops["sweep"]["s2c"])
    print(f"  NOT POOLED: {len(only_sweep)} opcode(s) appear in sweep captures and in "
          f"no played one.")
    print(f"  Pooled, our server would look like it sends {len(both)} distinct "
          f"GAME_SMSG opcodes")
    print(f"  and the NEVER-SENT list below -- the reason this tool exists -- would "
          f"collapse.")
    other = (pops["played"]["probes"] | pops["sweep"]["probes"]) - {"smsgsweep"}
    if other:
        print(f"  other PROBE tags seen, counted as PLAYED (a probe drives the "
              f"SERVER's sends;")
        print(f"  the c2s half is still a human in a client): "
              f"{', '.join(sorted(other))}")

    # ---- s2c: what we send, against ArenaNet -----------------------------
    theirs, their_secs = read_arenanet(codec_obj)
    rank = pops[args.rank_on]
    ours, our_secs = rank["s2c"], rank["seconds"]

    print(f"\ns2c MIX  (ours = {args.rank_on.upper()} population only)")
    print(f"  ArenaNet: {sum(theirs.values())} msgs over {their_secs:.0f}s "
          f"({len(theirs)} opcodes)")
    print(f"  ours    : {sum(ours.values())} msgs over {our_secs:.0f}s "
          f"({len(ours)} opcodes) from {rank['files']} capture(s)")
    if not ours:
        print("\nNO s2c RECORDS FOUND -- the field names below are what was "
              "looked for.")
        with open(files[-1], encoding="utf-8", errors="replace") as fh:
            for line in list(fh)[:3]:
                try:
                    print("  sample record keys:", sorted(json.loads(line)))
                except ValueError:
                    pass
        return 1

    tr = 100.0 / their_secs if their_secs else 0.0
    orr = 100.0 / our_secs if our_secs else 0.0
    rows = []
    for op in set(theirs) | set(ours):
        rows.append((theirs[op] * tr, ours[op] * orr, op))
    rows.sort(key=lambda r: -r[0])

    print(f"\n{'opcode':8} {'name':30} {'ArenaNet/100s':>14} {'ours/100s':>10}  gap")
    print("-" * 78)
    for their_rate, our_rate, op in rows[:args.top]:
        if their_rate < 1 and our_rate < 1:
            continue
        if our_rate == 0 and their_rate > 0:
            gap = "NEVER SENT"
        elif their_rate == 0:
            gap = "ours only"
        else:
            gap = f"{our_rate / their_rate:5.2f}x"
        print(f"0x{op:04X}   {name('GAME_SMSG', op)[:30]:30} "
              f"{their_rate:14.1f} {our_rate:10.1f}  {gap}")

    never = [(r[0], r[2]) for r in rows if r[1] == 0 and r[0] >= 1.0]
    print(f"\nnamed GAME_SMSG opcodes ArenaNet sends at >=1/100s that we NEVER send: "
          f"{sum(1 for r, op in never if name('GAME_SMSG', op))}")
    for rate, op in never:
        if name("GAME_SMSG", op):
            print(f"  0x{op:04X}  {name('GAME_SMSG', op):32} {rate:7.1f}/100s")
    # This list got SHORTER when the corpus was widened, and that is the correct
    # direction rather than a regression. "NEVER SENT" over 6 captures was a claim
    # about six sessions; over {rank['files']} it is a claim about all of them, so an
    # opcode we emit once in a probe run no longer qualifies. The ranking signal has
    # moved into the `gap` column: 0.00x-0.02x is "implemented in name only" and is
    # the same finding one row down in strength.
    print(f"  (over {rank['files']} captures, so an opcode we send ONCE anywhere "
          f"leaves this list --")
    print(f"   read the 0.00x-0.02x rows of the table above as the same finding, "
          f"one row weaker)")

    # ---- c2s: what the client says that we drop --------------------------
    print("\nc2s DROPS  (the client spoke, the dispatch chain had no arm -- D9a)")
    print("  RECORDS are not MESSAGES. `note_unhandled` writes one record per")
    print("  (session, opcode) FIRST OCCURRENCE and counts the rest silently, so the")
    print("  record count is a count of distinct opcode sightings. The message count")
    print("  below comes from the `decoded` records. Two digs once disagreed by")
    print("  exactly the record count (studies/recon FINDINGS B); do not repeat it.")
    for pop in ("played", "sweep"):
        a = pops[pop]
        tot = sum(a["c2s"].values())
        drop = sum(a["dropped"].values())
        pct = (100.0 * drop / tot) if tot else 0.0
        print(f"\n  -- {pop.upper()} --  {a['files']} capture(s)")
        print(f"     c2s MESSAGES        : {tot}")
        print(f"     dropped MESSAGES    : {drop}  ({pct:.2f}% of c2s)")
        print(f"     `unhandled` RECORDS : {a['unh_records']}   "
              f"<- NOT the message count")
        una = sum(a["unattributable"].values())
        if una:
            print(f"     unattributable      : {una} message(s) in "
                  f"{a['pre_files']} pre-D9a capture(s) --")
            print(f"                           opcodes flagged in OTHER sessions, "
                  f"never logged in these.")
            print(f"                           NOT added above. Imputing them is the "
                  f"pooling this repo keeps")
            print(f"                           recording as a defect: 0x000C is "
                  f"flagged in some sessions and")
            print(f"                           handled in others.")
        if a["dropped"]:
            print(f"     {'opcode':8} {'name':26} {'msgs':>7}")
            for op, n in a["dropped"].most_common(15):
                print(f"     0x{op:04X}   {name('GAME_CMSG', op)[:26]:26} {n:7}")

    # ---- the oracle ------------------------------------------------------
    verdicts = [summary_agrees(s) for s in sessions]
    agree = sum(1 for v in verdicts if v is True)
    disagree = sum(1 for v in verdicts if v is False)
    silent = sum(1 for v in verdicts if v is None)
    print(f"\nORACLE  the server's own `unhandled_summary.total` against the count "
          f"rebuilt here")
    print(f"  from the `decoded` stream: {agree} agree, {disagree} DISAGREE, "
          f"{silent} never reported")
    print(f"  (a capture only reports at a clean disconnect, so `never reported` is "
          f"normal;")
    print(f"   a DISAGREE means one of the two counts is wrong and is worth stopping "
          f"for)")
    return 1 if disagree else 0


if __name__ == "__main__":
    sys.exit(main())
