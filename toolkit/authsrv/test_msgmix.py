"""msgmix's two blind spots and its record-versus-message arithmetic.

    python toolkit/authsrv/test_msgmix.py
    python toolkit/authsrv/test_msgmix.py --module <path>   # run against a sabotage

`msgmix.py` is the only tool that ranks our server's missing traffic against
ArenaNet's, and PLAN.md §8 item 0h calls it "the best next-actions source this
project has had". It shipped for two days answering confidently about a corpus it
had not read, and none of the three defects looked like a bug at the call site:

  (1) `sorted(..., key=os.path.getmtime)[-6:]` read 6 of 439 captures (2026-08-13;
      the vault grows, so corpus figures here are dated). A window is
      indistinguishable from a corpus in the output unless the tool says which it
      took, and studies/recon FINDINGS D is a figure quoted as a corpus number that
      was a windowed read.
  (2) `if r.get("kind") != "sent": continue`. `sent` is the OUTBOUND log, so the
      client-to-server direction -- the direction a "what should we build next" tool
      exists to rank -- was 0 of 12,000+ messages. Fixing (1) alone still yields
      zero c2s and fixing (2) alone reads six files.
  (3) 948 `unhandled` RECORDS was quoted as a message count. `note_unhandled` writes
      one record per (session, opcode) FIRST OCCURRENCE, so the record count counts
      distinct opcode sightings. Two digs disagreed by exactly it, studies/recon
      FINDINGS B.

WHAT THIS FILE CHECKS, AND WHY IT CAN. Everything above is a pure function over
dicts: `scan_session`, `population`, `dropped_messages`, `dropped_records`,
`instrumentation_era`, `unattributable` and `aggregate` take records and return
counts. So no vault, no socket, no client, and the fixtures are written here where a
reader can see what shape they are.

EVERY CLAIM HAS A CONTROL, and the controls are the point rather than the garnish.
A check that a c2s count is 3 passes against a tool that has never seen a `sent`
record; so section 1 REPRODUCES the old `kind != "sent"` filter inline over the same
fixture and requires the two to differ, which makes "3 against 0" a difference
between two live answers rather than a number the test asked the code to confirm
about itself -- `test_codescan.py` §8's pattern. Section 3 does the same for the
records/messages pair: 2 records against 7 messages over one fixture, both computed.

Sections 4 and 5 are the ones that would be easy to write so they cannot fail.
Section 4's era split exists because `note_unhandled` LANDED PARTWAY THROUGH THE
CORPUS (2026-08-12T00:19:42Z in the vault, 94 older captures, 0 of which carry one
of its records), so a pre-D9a capture dropped messages and logged nothing, and its
drops are unmeasurable rather than zero. The failure mode to refuse is imputing them
by opcode, which is the pooling this repo keeps recording as a defect -- and the
corpus refutes it directly: 0x000C is flagged in 2 messages and handled in the
other 42, because the ping round trip gained a handler partway through. So the
fixture here has an opcode that is flagged in one session and handled in another,
and the check is that it is NOT counted dropped in the session that handled it.

Section 5 requires the two populations to stay apart. Its control is the number that
makes the split load-bearing: pooled, a sweep capture's deliberate sends make our
server look like it emits every opcode, so the aggregate of one population must NOT
contain an opcode only the other sent.

Section 6 pins the file selection against a temp directory of its own making, with
explicit mtimes, because "sorted by mtime" and "the newest N" are both things that
work by accident on a directory whose files were written in order.

Standard library only. No vault, no socket, no client.
"""
import argparse
import collections
import importlib.util
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
import checks  # noqa: E402

# 56 is what a green run executes, measured 2026-08-13 from a real run and not from
# a guess. Every section runs unconditionally -- there is no vault, no socket and no
# client to be missing -- so there is no legitimate reason for this run to be short
# and no skip to declare.
LEDGER = checks.Ledger("msgmix (what to build next)", floor=56)
CHECK = checks.adopt(LEDGER)


def load_module(path):
    """Import a msgmix.py by PATH, so a sabotaged copy can be run through this file.

    `--module` is not a convenience. "A check that cannot fail is not a check" is
    only demonstrable by running the broken version, and a scratch copy of the module
    with one line reverted is the closest reconstruction of the shipped defect there
    is -- closer than an inline reimplementation, which can drift into being a
    different bug. The inline reproductions in sections 1 and 3 are kept as well,
    because they put both answers in one run where a reader sees them side by side.
    """
    spec = importlib.util.spec_from_file_location("msgmix_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---- fixtures ------------------------------------------------------------
#
# Records in the shape `authsrv.Recorder` writes them. Only the fields the tool
# reads are present; a real capture carries more, and a scan that needed the rest
# would be reading something this file cannot check.

def sent(t, opcode, label=""):
    return {"kind": "sent", "t": t, "opcode": opcode, "label": label,
            "wall": "2026-08-12T10:00:00Z"}


def decoded(t, opcode):
    return {"kind": "decoded", "t": t, "opcode": opcode, "name": "?",
            "wall": "2026-08-12T10:00:00Z"}


def unhandled(t, opcode):
    return {"kind": "unhandled", "t": t, "opcode": opcode, "name": "?",
            "channel": "GAME_CMSG", "wall": "2026-08-12T10:00:00Z"}


def summary(total, wall="2026-08-12T10:00:00Z"):
    return {"kind": "unhandled_summary", "t": 99.0, "total": total, "opcodes": 1,
            "counts": {}, "wall": wall}


def played_session():
    """A hand-played session: ordinary sends, a client that talks, two dropped ops."""
    return [
        {"kind": "connect", "t": 0.0, "peer": "127.0.0.1:1",
         "wall": "2026-08-12T10:00:00Z"},
        sent(1.0, 0x001E, "WORLD_SIMULATION_TICK"),
        sent(2.0, 0x001E, "WORLD_SIMULATION_TICK"),
        sent(3.0, 0x0020, "WORLD_CREATE_AGENT"),
        decoded(1.5, 0x0092),
        decoded(1.6, 0x0092),
        decoded(1.7, 0x0092),
        decoded(2.5, 0x00C1),
        decoded(2.6, 0x00C1),
        decoded(2.7, 0x0088),          # handled: never flagged
        decoded(2.8, 0x000C),          # handled HERE, flagged in the sweep fixture
        unhandled(1.5, 0x0092),        # ONE record for three messages
        unhandled(2.5, 0x00C1),        # ONE record for two messages
        {"kind": "sent", "t": 11.0, "opcode": 0x000D, "label": "LATENCY_REPORT",
         "wall": "2026-08-12T10:00:00Z"},
        summary(5),                    # 3 x 0x0092 + 2 x 0x00C1
    ]


def sweep_session():
    """An unattended smsgsweep run: the label, and a pile of deliberate sends."""
    recs = [
        {"kind": "connect", "t": 0.0, "peer": "127.0.0.1:2",
         "wall": "2026-08-12T11:00:00Z"},
        sent(1.0, 0x001E, "WORLD_SIMULATION_TICK"),
    ]
    # The opcodes a sweep transmits ON PURPOSE and a played session never does.
    for i, op in enumerate((0x0150, 0x0151, 0x0152, 0x0153)):
        recs.append(sent(2.0 + i, op, f"PROBE[smsgsweep] 0x{op:04x} [0, map 148]"))
    recs += [
        decoded(6.0, 0x0092),
        decoded(6.1, 0x000C),          # flagged HERE, handled in the played fixture
        unhandled(6.0, 0x0092),
        unhandled(6.1, 0x000C),
        sent(9.0, 0x000D, "LATENCY_REPORT"),
        summary(2),
    ]
    return [dict(r, wall="2026-08-12T11:00:00Z") for r in recs]


def probe_session():
    """A hand-driven probe run. Scripted SERVER sends, but a human in the client."""
    return [dict(r, wall="2026-08-12T12:00:00Z") for r in (
        sent(1.0, 0x00F1, "PROBE[attack_anim] AGENT_UPDATE_STATUS"),
        decoded(2.0, 0x0092),
        unhandled(2.0, 0x0092),
        summary(1),
    )]


def pre_d9a_session():
    """A capture from before `note_unhandled` existed: drops, and no witness at all."""
    return [dict(r, wall="2026-08-05T05:10:37Z") for r in (
        {"kind": "connect", "t": 0.0, "peer": "127.0.0.1:3",
         "wall": "2026-08-05T05:10:37Z"},
        sent(1.0, 0x001E, "WORLD_SIMULATION_TICK"),
        decoded(2.0, 0x00C1),
        decoded(2.1, 0x00C1),
        decoded(2.2, 0x0088),
    )]


def old_c2s_count(records):
    """The SHIPPED filter, reproduced. `sent` is the outbound log; this reads us.

    Kept as a live computation rather than as a remembered zero so that section 1
    compares two answers instead of asserting one.
    """
    n = 0
    for r in records:
        if r.get("kind") != "sent":
            continue
        try:
            int(r["opcode"])
        except (KeyError, TypeError, ValueError):
            continue
        n += 1
    return n


# ---- 1. both directions --------------------------------------------------

def section_scan(M):
    print("\n-- 1. scan_session reads BOTH directions --")
    s = M.scan_session(played_session())
    c2s = sum(s["c2s"].values())
    s2c = sum(s["s2c"].values())
    old = old_c2s_count(played_session())
    CHECK(c2s == 7, "c2s messages counted from `decoded` records", f"{c2s} (want 7)")
    CHECK(s2c == 4, "s2c messages counted from `sent` records", f"{s2c} (want 4)")
    CHECK(old != c2s,
          "CONTROL: the shipped `kind != \"sent\"` filter gives a DIFFERENT answer",
          f"old filter counts {old} 'c2s' messages, all of them ours")
    CHECK(s["c2s"][0x0092] == 3 and s["c2s"][0x00C1] == 2,
          "per-opcode c2s counts land on the right opcodes",
          f"0x0092={s['c2s'][0x0092]} 0x00C1={s['c2s'][0x00C1]}")
    CHECK(s["s2c"][0x001E] == 2,
          "per-opcode s2c counts survive the widening", f"0x001E={s['s2c'][0x001E]}")
    # The span comes off the SENT timestamps, which is where in-world seconds have
    # always come from; widening the corpus must not quietly redefine the denominator.
    CHECK(abs(s["seconds"] - 10.0) < 1e-9,
          "in-world seconds is the sent-timestamp span", f"{s['seconds']}")
    empty = M.scan_session([])
    CHECK(sum(empty["c2s"].values()) == 0 and sum(empty["s2c"].values()) == 0
          and empty["seconds"] == 0.0,
          "an empty capture summarises to zeroes rather than raising")
    junk = M.scan_session([{"kind": "decoded"}, {"kind": "sent", "opcode": "x"},
                           {"kind": "decoded", "opcode": None}, "not a dict"])
    CHECK(sum(junk["c2s"].values()) == 0 and sum(junk["s2c"].values()) == 0,
          "malformed records are skipped, not counted and not fatal")


# ---- 2. the population split ---------------------------------------------

def section_population(M):
    print("\n-- 2. sweep against played --")
    played = M.scan_session(played_session())
    sweep = M.scan_session(sweep_session())
    probe = M.scan_session(probe_session())
    CHECK(M.population(sweep) == "sweep",
          "a capture carrying PROBE[smsgsweep] is SWEEP")
    CHECK(M.population(played) == "played",
          "a capture with no probe label at all is PLAYED")
    CHECK(M.population(probe) == "played",
          "a capture driven by a DIFFERENT probe is PLAYED",
          "a probe scripts the server's sends; the c2s half is still a human")
    CHECK(probe["probes"] == {"attack_anim"} and sweep["probes"] == {"smsgsweep"},
          "the probe tag is reported so a reader can see what was folded in",
          f"probe={sorted(probe['probes'])} sweep={sorted(sweep['probes'])}")
    # The witness is prose, which is a real weakness and is stated in msgmix's
    # docstring. Pin the direction it fails in: a label that merely MENTIONS the
    # sweep in some other probe's text must not silently be read as one, and the
    # substring must be the bracketed form rather than the bare word.
    near = M.scan_session([sent(1.0, 0x0001, "PROBE[burrow] smsgsweep-adjacent")])
    CHECK(M.population(near) == "played",
          "CONTROL: the bare word 'smsgsweep' in another probe's label is not a sweep",
          "the witness is the bracketed PROBE[smsgsweep], not a keyword")
    exact = M.scan_session([sent(1.0, 0x0001, "PROBE[smsgsweep] 0x0150 [0, map 148]")])
    CHECK(M.population(exact) == "sweep",
          "POSITIVE CONTROL: the real label still classifies",
          "a discriminator that refuses everything discriminates nothing")


# ---- 3. records are not messages -----------------------------------------

def section_records_vs_messages(M):
    print("\n-- 3. `unhandled` RECORDS against dropped MESSAGES --")
    s = M.scan_session(played_session())
    recs = M.dropped_records(s)
    msgs = sum(M.dropped_messages(s).values())
    CHECK(recs == 2, "`unhandled` records: one per (session, opcode) first occurrence",
          f"{recs} (0x0092 and 0x00C1)")
    CHECK(msgs == 5, "dropped MESSAGES, rebuilt from the `decoded` stream",
          f"{msgs} (3 x 0x0092 + 2 x 0x00C1)")
    CHECK(recs != msgs,
          "CONTROL: the two quantities differ over the same capture",
          f"{recs} records against {msgs} messages -- the 948 misread, in miniature")
    d = M.dropped_messages(s)
    CHECK(d[0x0092] == 3 and d[0x00C1] == 2,
          "the drop is attributed per opcode, not spread over the session",
          f"0x0092={d[0x0092]} 0x00C1={d[0x00C1]}")
    CHECK(0x0088 not in d,
          "a HANDLED opcode the client sent is not counted as dropped")
    # The oracle: the server counted these as they happened, this file rebuilds them
    # afterwards from a different record kind. They share no code and can disagree.
    CHECK(M.summary_agrees(s) is True,
          "ORACLE: the server's own `unhandled_summary.total` agrees",
          "5 == 5")
    lying = played_session() + [summary(99)]
    CHECK(M.summary_agrees(M.scan_session(lying)) is False,
          "CONTROL: a summary that disagrees is REPORTED, not rounded away",
          "an oracle that has never said no is not an oracle")
    CHECK(M.summary_agrees(M.scan_session(pre_d9a_session())) is None,
          "a capture that never reached a clean disconnect returns None, not False",
          "no report is not a disagreement")


# ---- 4. the instrumentation era ------------------------------------------

def section_era(M):
    print("\n-- 4. captures from before `note_unhandled` existed --")
    sessions = [M.scan_session(played_session()), M.scan_session(sweep_session()),
                M.scan_session(pre_d9a_session())]
    boundary = M.instrumentation_era(sessions)
    CHECK(boundary == "2026-08-12T10:00:00Z",
          "the boundary is the earliest capture that CARRIES an unhandled record",
          f"{boundary} -- derived from the corpus, not hardcoded to a commit date")
    pre = M.scan_session(pre_d9a_session())
    CHECK(M.instrumented(pre, boundary) is False,
          "a capture older than the boundary is not instrumented")
    CHECK(M.instrumented(M.scan_session(played_session()), boundary) is True,
          "POSITIVE CONTROL: a capture at or after the boundary is instrumented")
    flagged_anywhere = set()
    for s in sessions:
        flagged_anywhere |= s["flagged"]
    CHECK(0x000C in flagged_anywhere and 0x00C1 in flagged_anywhere,
          "the corpus-wide flagged set is the union over sessions",
          f"{sorted(hex(o) for o in flagged_anywhere)}")
    una = M.unattributable(pre, boundary, flagged_anywhere)
    CHECK(sum(una.values()) == 2 and una[0x00C1] == 2,
          "a pre-D9a capture's flagged-elsewhere messages land in their OWN bucket",
          f"{sum(una.values())} message(s)")
    CHECK(sum(M.dropped_messages(pre).values()) == 0,
          "and they are NOT counted as dropped -- the server logged nothing",
          "unmeasurable is not zero, and it is not 'probably dropped' either")
    CHECK(0x0088 not in una,
          "an opcode no session ever flagged stays out of the bucket too")
    post = M.unattributable(M.scan_session(played_session()), boundary,
                            flagged_anywhere)
    CHECK(sum(post.values()) == 0,
          "CONTROL: an INSTRUMENTED capture contributes nothing to the bucket",
          "otherwise the bucket is just the drop count again, under another name")
    # The refutation that makes this a measurement and not a preference: an opcode
    # flagged in one session and HANDLED in another. Imputing by opcode would report
    # it dropped in both.
    played = M.scan_session(played_session())
    sweep = M.scan_session(sweep_session())
    CHECK(0x000C in sweep["flagged"] and 0x000C not in played["flagged"],
          "the fixture holds the real corpus's 0x000C case: flagged here, handled there",
          "44 messages in the vault, 2 of them flagged")
    CHECK(played["c2s"][0x000C] == 1
          and M.dropped_messages(played)[0x000C] == 0,
          "and the session that HANDLED it does not have it counted as dropped",
          "an 'any session flagged it' rule over-attributes 0x000C by 21x in the vault")
    CHECK(M.instrumentation_era([M.scan_session(pre_d9a_session())]) is None,
          "a corpus with no instrumented capture has no boundary to draw",
          "None rather than a guessed date")


# ---- 5. aggregation never pools ------------------------------------------

def section_aggregate(M):
    print("\n-- 5. the two populations stay apart --")
    # Partitioned THROUGH `population()`, the way main() does it, rather than by
    # hand. Handing this section two pre-sorted lists would let the classifier break
    # while every aggregate check stayed green -- which is what the first version of
    # this section did, and the pooling sabotage reddened two checks in section 2 and
    # none here.
    allsess = [M.scan_session(played_session()), M.scan_session(probe_session()),
               M.scan_session(sweep_session()), M.scan_session(pre_d9a_session())]
    played = [s for s in allsess if M.population(s) == "played"]
    sweep = [s for s in allsess if M.population(s) == "sweep"]
    boundary = M.instrumentation_era(allsess)
    flagged = set()
    for s in allsess:
        flagged |= s["flagged"]
    ap = M.aggregate(played, boundary, flagged)
    asw = M.aggregate(sweep, boundary, flagged)
    CHECK(ap["files"] == 3 and asw["files"] == 1,
          "each aggregate counts only its own population's captures",
          f"played={ap['files']} sweep={asw['files']}")
    sweep_only = set(asw["s2c"]) - set(ap["s2c"])
    CHECK(sweep_only == {0x0150, 0x0151, 0x0152, 0x0153},
          "the sweep sends opcodes the played population never does",
          f"{sorted(hex(o) for o in sweep_only)} -- 320 of them in the vault")
    CHECK(not (set(ap["s2c"]) & sweep_only),
          "and NONE of them leak into the played aggregate",
          "pooled, our server looks like it sends 421 of 487 and the gap list dies")
    CHECK(sum(ap["c2s"].values()) == 11 and sum(asw["c2s"].values()) == 2,
          "c2s totals stay per-population",
          f"played={sum(ap['c2s'].values())} sweep={sum(asw['c2s'].values())}")
    # 6, not 8: the pre-D9a capture in this population saw two 0x00C1 and logged
    # nothing about them. This is the realistic shape -- 94 of the vault's 182 played
    # captures predate D9a -- and it is the check the imputing sabotage has to get
    # past, because imputing puts those two here and makes the number 8.
    CHECK(sum(ap["dropped"].values()) == 6 and sum(asw["dropped"].values()) == 2,
          "so do the drop counts, and a pre-D9a capture adds NOTHING to them",
          f"played={sum(ap['dropped'].values())} sweep={sum(asw['dropped'].values())}")
    CHECK(sum(ap["unattributable"].values()) == 2 and ap["pre_files"] == 1,
          "its messages sit in the population's own unattributable bucket instead",
          f"unattributable={sum(ap['unattributable'].values())} "
          f"pre_files={ap['pre_files']}")
    CHECK(ap["unh_records"] == 3 and asw["unh_records"] == 2,
          "and the record counts, which are the number NOT to quote as messages",
          f"played={ap['unh_records']} sweep={asw['unh_records']}")
    # 10.0 from the played fixture's four sends (t=1..11) and 0.0 from the probe
    # fixture's single one -- a one-send capture has no span, which is the honest
    # answer and not a bug.
    CHECK(abs(ap["seconds"] - 10.0) < 1e-9,
          "in-world seconds sum within a population", f"{ap['seconds']}")
    pooled = M.aggregate(allsess, boundary, flagged)
    CHECK(len(pooled["s2c"]) > len(ap["s2c"]),
          "CONTROL: pooling really does inflate the opcode set",
          f"pooled {len(pooled['s2c'])} against played {len(ap['s2c'])} -- "
          "this is what the report must never print as 'ours'")
    prea = M.aggregate([M.scan_session(pre_d9a_session())], boundary, flagged)
    CHECK(prea["pre_files"] == 1 and sum(prea["unattributable"].values()) == 2
          and sum(prea["dropped"].values()) == 0,
          "an aggregate keeps the unattributable bucket separate from the drops",
          f"pre_files={prea['pre_files']} "
          f"unattributable={sum(prea['unattributable'].values())} "
          f"dropped={sum(prea['dropped'].values())}")


# ---- 6. how many files get read ------------------------------------------

def section_snapshot(M):
    print("\n-- 6. the file selection --")
    tmp = tempfile.mkdtemp(prefix="msgmix-snap-")
    try:
        names = []
        for i in range(10):
            p = os.path.join(tmp, f"authsrv-2026081{i}T000000-c1.jsonl")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write("{}\n")
            # Explicit mtimes. "sorted by mtime" and "the newest N" both work by
            # accident on a directory written in order, and this directory is.
            os.utime(p, (1_700_000_000 + i * 60, 1_700_000_000 + i * 60))
            names.append(os.path.basename(p))
        with open(os.path.join(tmp, "notes.txt"), "w", encoding="utf-8") as fh:
            fh.write("not a capture\n")

        allf = M.gamesrv_snapshot(tmp)
        CHECK(len(allf) == 10,
              "the DEFAULT is every capture in the directory",
              f"{len(allf)} of 10 -- the shipped default was 6 of 439 (1.4%)")
        CHECK(all(p.endswith(".jsonl") for p in allf),
              "non-capture files in the directory are ignored")
        CHECK([os.path.basename(p) for p in allf] == names,
              "and they come back oldest-first by mtime")

        win = M.gamesrv_snapshot(tmp, 6)
        CHECK(len(win) == 6, "--sessions N is a WINDOW and takes the newest N",
              f"{len(win)}")
        CHECK([os.path.basename(p) for p in win] == names[-6:],
              "the newest N, by mtime, not by name",
              "hostile filename order picked the wrong client build once already")
        CHECK(len(M.gamesrv_snapshot(tmp, 0)) == 10,
              "CONTROL: 0 means all, so the flag's own default cannot re-window it")
        CHECK(len(M.gamesrv_snapshot(tmp, 99)) == 10,
              "a window larger than the corpus is the corpus, not an error")
        empty = tempfile.mkdtemp(prefix="msgmix-empty-")
        try:
            CHECK(M.gamesrv_snapshot(empty) == [],
                  "an empty directory returns nothing rather than raising")
        finally:
            shutil.rmtree(empty, ignore_errors=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---- 7. the names it prints ----------------------------------------------

def section_names(M):
    print("\n-- 7. c2s names come from the c2s channel --")
    # GAME_CMSG and GAME_SMSG number independently. Before the c2s half existed
    # `name()` had no channel parameter at all and read GAME_SMSG, so printing a c2s
    # table through it would have labelled every dropped opcode with whatever the
    # server-to-client catalog happens to hold at that number -- a name that is not
    # merely missing but WRONG, which is the failure test_cmsgnames.py records as
    # "decoding the AUTH channel against the GAME_CMSG tables does not error, it
    # invents".
    CHECK(M.name("GAME_CMSG", 0x00C1) == "TARGET_SELECT",
          "0x00C1 c2s is TARGET_SELECT")
    CHECK(M.name("GAME_CMSG", 0x0092) == "MISSION_MASK_REPORT",
          "0x0092 c2s is MISSION_MASK_REPORT")
    # 0x0026 is the ONLY opcode named on both channels today, which is exactly what
    # makes it the control worth having: two non-empty names for one number. A
    # control built on 0x0092 would pass merely because GAME_SMSG has no name there,
    # i.e. it would be satisfied by a lookup that always returned "".
    CHECK(M.name("GAME_CMSG", 0x0026) == "ATTACK"
          and M.name("GAME_SMSG", 0x0026) == "AGENT_UPDATE_FLAGS",
          "CONTROL: 0x0026 is named on BOTH channels and means different things",
          f"c2s={M.name('GAME_CMSG', 0x0026)!r} s2c={M.name('GAME_SMSG', 0x0026)!r}")
    CHECK(M.name("GAME_CMSG", 0x7FFF) == "",
          "an unnamed opcode is \"\", never a borrowed name")
    CHECK(M.name("NO_SUCH_CHANNEL", 0x0092) == "",
          "and an unknown channel does not raise")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--module", default=os.path.join(HERE, "msgmix.py"),
                    help="path to the msgmix.py under test (for running a sabotage)")
    args = ap.parse_args()

    print(f"msgmix under test: {args.module}")
    M = load_module(args.module)

    section_scan(M)
    section_population(M)
    section_records_vs_messages(M)
    section_era(M)
    section_aggregate(M)
    section_snapshot(M)
    section_names(M)
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
