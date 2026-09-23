"""The retail c2s triage (c2striage.py) against the vault -- DESKWORK-D1 step 3
(studies/cmsg/FINDINGS.md DESKWORK-D1).

    python toolkit/authsrv/test_c2striage.py

WHAT THIS PINS.

  * §1 THE WALK, on a synthetic stream: `census_connection` is driven with a
    hand-built merged list and must attribute the first s2c strictly after each
    c2s within the window (the clock 0x001E counted in the strict column and
    skipped in the other), a reply outside the window as none, and a trailing
    c2s as none. Known-bad: a window of 0 empties the reply columns. This is
    the check the vault cannot give -- on real tapes every c2s has SOME s2c
    after it, so a walker that pointed one message off would still fill every
    column.
  * §2 THE CORPUS: the live census runs (>= 96 connections, >= 57 opcodes,
    >= 13,320 c2s -- the 2026-09-23 floors; the corpus is append-only), every
    connection's receipt closes, and two tape anchors hold: the henchman add
    0x009F answers 0x00B0 first 3 of 3 and MAP_TRAVEL 0x00B1 answers 0x01D9
    first on 9 of 10. Vault-gated; a missing vault declares a skip.
  * §3 THE COMMITTED FILE against the vault: retail_c2s.json holds every
    opcode the live census sees (a new tape with a new opcode reddens this
    until `--write` runs and the opcode is triaged), no count in the file
    exceeds the live count, and the file names the tool. Known-bad: a table
    with one opcode removed is caught.
  * §4 THE DECISION: `untriaged()` over the live census is EMPTY on this tree
    (acceptance (c) of the route: zero retail c2s opcodes neither handled,
    named nor dropped on purpose), it agrees with test_dispatch §10's restated
    predicate, and removing one allowlist row names that row alone.
  * §5 REFUSALS: a root with no live capture makes `main()` exit 2 rather than
    print a clean table, and a dispatch chain that cannot be located refuses.
  * §6 STATIC hints: on a machine with the pinned client the send-site census
    joins -- 0x001F's wrapper is 0x0091FF30 on 38797 -- else a skip.

Floor 20 -- the MANDATORY CORE, measured on 2026-09-23 with RURIK_VAULT pointed
at an empty directory (§1, §3's file half, §4's file half, §5: the checks that
need no vault and no client). With the vault and the pinned client present the
same run executes 34; §2, §3's live half, §4's live half and §6 declare skips
without them. The first cut set the floor at 34 and so failed a vault-free run
by construction (checks.py: the floor is the core, not the fullest run).
"""
import contextlib
import io
import os
import sys
import tempfile
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
if os.path.dirname(HERE) not in sys.path:
    sys.path.insert(0, os.path.dirname(HERE))
import checks                                                # noqa: E402
import c2striage                                             # noqa: E402
import livewire                                              # noqa: E402
import test_dispatch as dispatchmod                          # noqa: E402

led = checks.Ledger("retail c2s triage (DESKWORK-D1 step 3)", floor=20)

# ---- §1 the walk, on a synthetic stream -------------------------------------
# t, dir, opcode, values -- sorted by (t, c2s first on a tie) like livewire's.
STREAM = [
    (0.000, "c2s", 0x009F, [0x809F, 4]),
    (0.021, "s2c", 0x001E, [0x1E, 20]),          # the clock
    (0.039, "s2c", 0x00B0, [0xB0, 14, 2]),       # the answer
    (0.040, "s2c", 0x01BF, [0x1BF]),
    (5.000, "c2s", 0x0040, [0x8040, 1.0]),
    (7.000, "s2c", 0x0029, [0x29]),              # 2.0 s later: outside 1.5
    (9.000, "c2s", 0x0008, [0x8008]),             # nothing follows
]
rows = defaultdict(c2striage._new_row)
meta = {"c2s_total": 0}
c2striage.census_connection(STREAM, rows, meta, 1.5, capture="synth", conn="c")
led.ok(meta["c2s_total"] == 3 and set(rows) == {0x009F, 0x0040, 0x0008},
       "the walk counts the three c2s and nothing else",
       f"total {meta['c2s_total']}, opcodes {sorted(rows)}")
led.ok(rows[0x009F]["first_reply"] == {0x001E: 1}
       and rows[0x009F]["first_non_tick"] == {0x00B0: 1},
       "the strict column takes the clock at 21 ms; the clock-skipped column "
       "takes 0x00B0 at 39 ms -- the two columns disagree on exactly the case "
       "that makes the second one worth keeping",
       f"strict {dict(rows[0x009F]['first_reply'])}, skipped "
       f"{dict(rows[0x009F]['first_non_tick'])}")
led.ok(abs(rows[0x009F]["non_tick_dt"][0] - 0.039) < 1e-9
       and abs(rows[0x009F]["reply_dt"][0] - 0.021) < 1e-9,
       "and both latencies are the reply's own, not the message after it",
       f"{rows[0x009F]['reply_dt']}, {rows[0x009F]['non_tick_dt']}")
led.ok(rows[0x0040]["first_reply"] == {None: 1}
       and rows[0x0040]["first_non_tick"] == {None: 1},
       "an s2c 2.0 s later is OUTSIDE a 1.5 s window: none, in both columns")
led.ok(rows[0x0008]["first_reply"] == {None: 1},
       "a trailing c2s with nothing after it is none (the pointer past the end)")
# KNOWN-BAD: a zero window empties every reply column.
rows0 = defaultdict(c2striage._new_row)
c2striage.census_connection(STREAM, rows0, {"c2s_total": 0}, 0.0)
led.ok(all(r["first_reply"] == {None: r["count"]}
           and r["first_non_tick"] == {None: r["count"]} for r in rows0.values()),
       "KNOWN-BAD: a 0 s window attributes NO replies -- the window is read, "
       "not decorative", f"{[dict(r['first_reply']) for r in rows0.values()]}")
# KNOWN-BAD: a wide window turns the 2.0 s straggler into a reply.
rows9 = defaultdict(c2striage._new_row)
c2striage.census_connection(STREAM, rows9, {"c2s_total": 0}, 9.0)
led.ok(rows9[0x0040]["first_reply"] == {0x0029: 1},
       "KNOWN-BAD: a 9 s window DOES take the 2.0 s straggler -- so the 1.5 s "
       "refusal above is the window's doing")

# The JSON shape drops status and name (derived at test time, not measured).
tab = c2striage.table(rows, {"live_captures": 1, "captures": 1,
                             "connections": 1, "connections_not_ok": 0,
                             "c2s_total": 3, "window": 1.5},
                      handled={}, named={}, dropped={})
led.ok(set(tab["opcodes"]["0x009F"]) == {"count", "captures", "connections",
                                          "first_reply", "reply_p50_ms",
                                          "first_non_tick", "non_tick_p50_ms"},
       "a table row is counts and replies only -- no status, no name (those "
       "are read off the tree at test time, so the file cannot go stale)",
       f"keys {sorted(tab['opcodes']['0x009F'])}")
led.ok(tab["opcodes"]["0x009F"]["first_non_tick"] == {"0x00B0": 1}
       and tab["opcodes"]["0x0040"]["first_reply"] == {"none": 1},
       "and the counters serialise with hex keys and 'none'")

# ---- §2 the corpus -----------------------------------------------------------
live = None
if livewire.live_captures():
    live_rows, live_meta = c2striage.census()
    live = (live_rows, live_meta)
    led.ok(live_meta["connections"] >= 96 and len(live_rows) >= 57
           and live_meta["c2s_total"] >= 13320,
           "the live census reaches the 2026-09-23 floors: >= 96 connections, "
           ">= 57 opcodes, >= 13,320 c2s",
           f"{live_meta['connections']} conns, {len(live_rows)} opcodes, "
           f"{live_meta['c2s_total']} c2s over {live_meta['captures']} of "
           f"{live_meta['live_captures']} live captures")
    led.ok(live_meta["connections_not_ok"] == 0,
           "every live connection's receipt closes (0 shortfalls)",
           f"{live_meta['connections_not_ok']} not ok -- a partial decode would "
           f"under-count")
    hen = live_rows.get(0x009F)
    led.ok(hen is not None and hen["count"] >= 3
           and hen["first_reply"].get(0x00B0, 0) >= 3
           and hen["first_non_tick"].get(0x00B0, 0) >= 3,
           "TAPE ANCHOR: the henchman add 0x009F answers 0x00B0 FIRST, 3 of 3, "
           "in both columns (20260819T132414)",
           f"{None if hen is None else dict(hen['first_non_tick'])}")
    trv = live_rows.get(0x00B1)
    led.ok(trv is not None and trv["count"] >= 10
           and trv["first_non_tick"].get(0x01D9, 0) >= 9,
           "TAPE ANCHOR: MAP_TRAVEL 0x00B1 answers 0x01D9 first on >= 9 of 10",
           f"{None if trv is None else dict(trv['first_non_tick'])}")
    kick = live_rows.get(0x001F)
    # `>= 1`, not `== 1`: a second live kick is confirming evidence and must
    # not redden a floor (the corpus counts redden on confirming evidence
    # otherwise); what is pinned is that the one witness's first non-clock
    # s2c is the ambient 0x0029, so the column stays a correlation.
    led.ok(kick is not None and kick["count"] >= 1
           and kick["first_non_tick"].get(0x0029, 0) >= 1,
           "and the kick's first non-clock s2c is NOT its 0x0075 (an outpost "
           "0x0029 lands at 21 ms, the batch at 42 ms) -- the column is a "
           "CORRELATION, which is why test_herokick pins the batch by bytes",
           f"{None if kick is None else dict(kick['first_non_tick'])}")
else:
    led.skip("§2 the live census", "no origin=LIVE captures under the vault")

# ---- §3 the committed file against the vault ---------------------------------
committed = c2striage.load_table()
led.ok(committed is not None and committed.get("tool") == c2striage.TOOL
       and committed.get("window_s") == c2striage.REPLY_WINDOW,
       "retail_c2s.json is committed, names its tool and its window",
       f"{c2striage.TABLE_PATH}: "
       f"{None if committed is None else committed.get('generated')}")
cops = c2striage.table_opcodes(committed)
if live is not None:
    live_rows, live_meta = live
    missing = sorted(set(live_rows) - set(cops))
    led.ok(not missing,
           "every opcode the live census sees is in the committed file (a new "
           "tape with a new opcode reddens this until --write runs and the "
           "opcode is triaged)",
           "MISSING FROM retail_c2s.json: "
           + (", ".join(f"0x{o:04x}" for o in missing) or "none")
           + f" -- run `python toolkit/authsrv/c2striage.py --write`")
    over = sorted(o for o, v in cops.items()
                  if o in live_rows and v["count"] > live_rows[o]["count"])
    led.ok(not over and committed["connections"] <= live_meta["connections"],
           "no committed count exceeds the live count (the corpus is "
           "append-only, so the file is a floor of the vault)",
           f"over: {[f'0x{o:04x}' for o in over]}; file {committed['connections']}"
           f" conns vs live {live_meta['connections']}")
    # KNOWN-BAD: drop one opcode from the table and the staleness check names it.
    stale = dict(cops)
    stale.pop(0x0009, None)
    led.ok(sorted(set(live_rows) - set(stale)) == [0x0009],
           "KNOWN-BAD: a table missing 0x0009 is caught, and 0x0009 alone is "
           "named")
else:
    led.skip("§3 the file against the vault", "no live captures to compare")
led.ok(len(cops) >= dispatchmod.RETAIL_C2S_MIN_OPCODES
       and (committed or {}).get("connections", 0) >= dispatchmod.RETAIL_C2S_MIN_CONNECTIONS,
       "the file meets test_dispatch's own floors (57 opcodes, 96 connections)",
       f"{len(cops)} opcodes, {(committed or {}).get('connections')} conns")

# ---- §4 the decision ---------------------------------------------------------
handled = c2striage.handled_opcodes()
named = c2striage.schema_names()
dropped = dispatchmod.DROPPED_ON_PURPOSE
led.ok(handled is not None and len(handled) >= 34,
       "the dispatch chain is located and has not shrunk (34 game arms on "
       "2026-09-23)", f"{None if handled is None else len(handled)} arms")
un_file = c2striage.untriaged(cops, handled or {}, named, dropped)
led.ok(cops and un_file == [],
       "ACCEPTANCE (c): every retail c2s opcode in the committed census is "
       "handled, named or dropped on purpose -- zero UNTRIAGED",
       f"untriaged {[f'0x{o:04x}' for o in un_file]}")
if live is not None:
    un_live = c2striage.untriaged(live[0], handled or {}, named, dropped)
    led.ok(un_live == [],
           "...and the same over the LIVE census, not just the file",
           f"untriaged {[f'0x{o:04x}' for o in un_live]}")
    # The three named at step 3 are in the census with their reply chains; two
    # still wait for their arm, and 0x004F ITEM_MOVE got its arm at step 8
    # (2026-09-23) -- so it must now be HANDLED and off the allowlist.
    for op, nm in ((0x009F, "HENCHMAN_ADD"), (0x00B1, "MAP_TRAVEL")):
        led.ok(named.get(op, ("", ""))[0] == nm and op in dropped
               and op in live[0] and op not in (handled or {}),
               f"0x{op:04X} is named {nm} (medium), on retail's wire, not yet "
               f"armed, and its drop carries a reason",
               f"name {named.get(op)}, dropped {op in dropped}, "
               f"seen {op in live[0]}")
    for op, nm in ((0x004F, "ITEM_MOVE"), (0x0030, "EQUIP_ITEM")):
        led.ok(named.get(op, ("", ""))[0] == nm and op not in dropped
               and op in live[0] and op in (handled or {}),
               f"0x{op:04X} is named {nm}, on retail's wire, ARMED (DESKWORK-D1 "
               f"step 8) and no longer on the allowlist",
               f"name {named.get(op)}, dropped {op in dropped}, "
               f"seen {op in live[0]}, handled {op in (handled or {})}")
else:
    led.skip("§4 the live half", "no live captures")
# The status vocabulary, and the reverse predicate's known-bad arm.
led.ok(c2striage.status_of(0x0009, handled or {}, named, dropped) == "handled"
       and c2striage.status_of(0x0008, handled or {}, named, dropped) == "dropped"
       and c2striage.status_of(0x00FE, {}, {}, {}) == "UNTRIAGED"
       and c2striage.status_of(0x0001, {}, {0x0001: ("X", "low")}, {}) == "named-only",
       "status_of: handled / dropped / UNTRIAGED / named-only")
without_8 = {k: v for k, v in dropped.items() if k != 0x0008}
led.ok(c2striage.untriaged(cops, handled or {}, named, without_8) == [0x0008],
       "KNOWN-BAD: remove the 0x0008 allowlist row and the predicate names "
       "0x0008, alone")
led.ok(c2striage.untriaged({0x00FE: {}, 0x0009: {}}, handled or {}, named,
                           dropped) == [0x00FE],
       "KNOWN-BAD: a census with an undecided opcode names it, and only it")
led.ok(c2striage.untriaged({}, handled or {}, named, dropped) == [],
       "an empty census is vacuously clean -- which is why the floors above "
       "exist")

# ---- §5 refusals -------------------------------------------------------------
empty = tempfile.mkdtemp(prefix="c2striage-empty-")
try:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = c2striage.main(["--root", empty])
    led.ok(rc == 2 and "REFUSED" in buf.getvalue(),
           "a root with no live capture is REFUSED with exit 2, never printed "
           "as a clean 'retail sends nothing'",
           f"rc {rc}: {buf.getvalue().strip()[:120]}")
    r0, m0 = c2striage.census(empty)
    led.ok(r0 == {} and m0["connections"] == 0 and m0["live_captures"] == 0,
           "census() over that root is empty with zero connections")
finally:
    os.rmdir(empty)
# A source with no locatable game chain refuses too.
_fd, nochain = tempfile.mkstemp(prefix="c2striage-nochain-", suffix=".py")
with os.fdopen(_fd, "w", encoding="utf-8") as f:
    f.write("def f():\n    pass\n")
try:
    led.ok(c2striage.handled_opcodes(nochain) is None,
           "a source without the game dispatch chain yields None, not {} (the "
           "vacuity the CLI refuses on)")
finally:
    os.remove(nochain)

# ---- §6 static hints ----------------------------------------------------------
hints, where = c2striage.static_hints()
if hints is None:
    led.skip("§6 static hints", where)
else:
    rows_1f = hints.get(0x001F, [])
    rows_1e = hints.get(0x001E, [])
    # The kick/add wrapper PAIR per build -- (0x0091FF30, 0x0091FF00) on 38797,
    # (0x009208B0, 0x00920880) on 38888 -- must match as a pair: accepting
    # either kick wrapper alone would also accept 38797's 0x0044 wrapper
    # (0x009208B0 there), which is the trap a per-opcode `or` sets.
    PAIRS = {(0x0091FF30, 0x0091FF00), (0x009208B0, 0x00920880)}
    led.ok(any((w1f, w1e) in PAIRS
               for w1f, _m, _c, _l in rows_1f for w1e, _m2, _c2, _l2 in rows_1e),
           "the send-site census joins: 0x001F/0x001E's wrappers are one build's "
           "pair -- 0x0091FF30/0x0091FF00 (38797) or 0x009208B0/0x00920880 (38888)",
           f"{where}: 1F {[hex(w) for w, m, c, l in rows_1f]}, "
           f"1E {[hex(w) for w, m, c, l in rows_1e]}")
    led.ok(0x000D not in hints and 0x0009 in hints,
           "and it says NO game-channel send site for 0x000D while 0x0009 has "
           "one -- the census does not invent a wrapper",
           f"0x000D {hints.get(0x000D)}, 0x0009 {hints.get(0x0009)}")

sys.exit(led.verdict())
