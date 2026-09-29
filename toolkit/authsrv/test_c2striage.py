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
    SINCE 2026-09-28 (CASTAI-Z1) "every connection" means every one its
    capture's own manifest does not declare gapped: census() sets a declared
    connection aside BY NAME (livewire.declared_gaps), the set-aside set is
    pinned EXACTLY (20260928T103123 :65009, match 2) and must still be refused
    by decode_conn, and a known-bad arm re-runs that capture with the manifest
    unread and must see the shortfall.
  * §3 THE COMMITTED FILE against the vault: retail_c2s.json holds every
    opcode the live census sees (a new tape with a new opcode reddens this
    until `--write` runs and the opcode is triaged), no count in the file
    exceeds the live count, and the file names the tool. Known-bad: a table
    with one opcode removed is caught.
  * §4 THE DECISION: `untriaged()` over the live census is EMPTY on this tree
    (acceptance (c) of the route: zero retail c2s opcodes neither handled,
    named nor dropped on purpose), it agrees with test_dispatch §10's restated
    predicate, and removing one allowlist row names that row alone. The
    Zaishen tape's three new opcodes (0x009A, 0x00A3, 0x00A6) carry their
    decision (all three named medium, 0x00A3 by the owner's decision of
    2026-09-28; dropped, not armed) and ONE exact
    per-tape witness of the evidence behind it. SINCE 2026-09-29 (CASTAI-Z2)
    the second Zaishen tape's one new opcode, 0x0042 [agent_id], carries its
    decision too (UNNAMED at n=2, dropped, not armed -- the reason is
    test_dispatch's row), two vault-free arms show that row alone triages it,
    and six per-tape witnesses (20260929T100038) pin the evidence: the own
    agent on each of the 11 connections by three routes -- the SELF-SCOPED
    anchor (int property 41, adrenjoin.whose_agent), 0x0199's player number
    through PLAYER_INFO, and the first PLAYER_INFO -- agreeing on all 11
    (round 3 defined the own agent by the first PLAYER_INFO, the rule
    moralescan.py refuted in 2026-08; it is right on this tape and wrong or
    empty on 43 of the corpus's 110 instance loads, so the anchor is what
    every witness reads since 2026-09-29's round 4); both sends with their
    same-timestamp c2s, EVERY message either way within 50 ms after, and the
    target's AND the PLAYER's last 0x00F1 / 0x0026 words (the player --
    agent 7 by the anchor -- was DEAD at the first send, 5.3 s into a death,
    and 21 ms out of one at the second); every TARGET_SELECT of
    agent 9 on the tape with the target's, the player's and the controlled
    agent's state (the two with a 0x0042 are the only ones sent while the
    player was dead or just revived); the :62925 control track (0x0022 [9, 0]
    in one chunk with WORLD_REMOVE_AGENT of agents 1 and 2 at 245.279, while
    the player was dead, and its return 0x0022 [7, 1] with their re-creates
    and the player's revival at 259.459); every 0x0022 on the tape (that pair
    is its only mid-connection control change); and every TARGET_SELECT sent
    while the player was dead (five, four of them inside that one death).
  * §5 REFUSALS: a root with no live capture makes `main()` exit 2 rather than
    print a clean table, and a dispatch chain that cannot be located refuses.
  * §6 STATIC hints: on a machine with the pinned client the send-site census
    joins -- 0x001F's wrapper is 0x0091FF30 on 38797 -- else a skip.

Floor 22 -- the MANDATORY CORE, measured with RURIK_VAULT pointed at an empty
directory (§1, §3's file half, §4's file half, §5: the checks that need no
vault and no client): 20 on 2026-09-23, 22 since 2026-09-29 (CASTAI-Z2: the
two vault-free 0x0042 arms; 6 declared skips). With the vault and the pinned
client present the same run executes 34 (42 since 2026-09-28: the declared-gap
pin and its known-bad arm, three Zaishen decisions, the Zaishen witness; 45
after the ENTER field-2 pins; 53 since 2026-09-29: the 0x0042 decision, its
five witnesses and the two arms; 54 the same day, round 4: WITNESS 0, the
own agent by three routes); §2, §3's live half, §4's live half, the
witnesses and §6 declare skips without them. The first cut set the floor at 34
and so failed a vault-free run by construction (checks.py: the floor is the
core, not the fullest run).
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
import adrenjoin  # noqa: E402  whose_agent: the self-scoped own-agent anchor

# Floor 20 measured bare 2026-09-23; 22 since 2026-09-29 (CASTAI-Z2: +2 -- the
# two vault-free 0x0042 arms in §4, measured 22 with RURIK_VAULT at an empty
# directory, 6 declared skips).
led = checks.Ledger("retail c2s triage (DESKWORK-D1 step 3)", floor=22)

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
           "every live connection's receipt closes (0 shortfalls) -- every one "
           "its capture's manifest does not declare gapped (the next check)",
           f"{live_meta['connections_not_ok']} not ok -- a partial decode would "
           f"under-count")
    # 2026-09-28 (CASTAI-Z1): the first gapped live connection. Its capture's
    # OWN manifest declares 38 + 20 s2c bytes the sniffer never saw
    # (livewire.declared_gaps, commit d69bf7a0), decode_conn refuses it by
    # design, and census() sets it aside BY NAME rather than folding a capture
    # fact into the shortfall count above. The declared set is pinned EXACTLY,
    # so a second gapped connection -- declared or not -- reddens a check
    # instead of being absorbed, and each one must still be REFUSED.
    gapped = sorted((g["capture"], g["connection"], repr(g["gaps"]), g["refused"])
                    for g in live_meta["declared_gapped"])
    for g in live_meta["declared_gapped"]:
        print(f"  set aside by its manifest: {g['capture']} {g['connection']} "
              f"gaps {g['gaps']} refused={g['refused']}")
    # Exact on whichever corpus is present: the witness capture's one row when
    # it is in the vault, and NOTHING set aside when it is not (every older
    # capture predates the manifest field or declares no gap).
    want_gapped = ([("20260928T103123", "10.0.0.210:65009->98.95.137.136:80",
                     repr({"s2c": [[38045, 38], [38548, 20]]}), True)]
                   if os.path.isdir(os.path.join(livewire.captures_root(),
                                                 "20260928T103123")) else [])
    led.ok(gapped == want_gapped,
           "the ONE connection set aside is CASTAI-Z1's match 2, by its "
           "manifest's own declaration (38 + 20 s2c bytes at stream offsets "
           "38045 / 38548), and decode_conn still REFUSES it",
           f"{gapped}")
    if want_gapped:
        # KNOWN-BAD: the same census over that one capture with the manifest's
        # declaration NOT read -- the connection must come back as a receipt
        # shortfall and nothing set aside, so the set-aside above is the
        # declaration's doing and not the census losing the connection.
        zcap = os.path.join(livewire.captures_root(), "20260928T103123")
        _real_lc, _real_dg = livewire.live_connections, livewire.declared_gaps
        try:
            livewire.live_connections = lambda root=None: [
                (zcap, g) for g in livewire.connections(zcap)]
            _r1, m_decl = c2striage.census()
            livewire.declared_gaps = lambda capdir: {}
            _r2, m_blind = c2striage.census()
        finally:
            livewire.live_connections, livewire.declared_gaps = _real_lc, _real_dg
        led.ok(m_decl["connections_not_ok"] == 0 and len(m_decl["declared_gapped"]) == 1
               and m_blind["connections_not_ok"] == 1 and m_blind["declared_gapped"] == []
               and m_blind["connections"] == m_decl["connections"] + 1,
               "KNOWN-BAD: over that capture alone, with its manifest unread the "
               "same connection is a receipt SHORTFALL and nothing is set aside",
               f"declared: {m_decl['connections']} folded, "
               f"{m_decl['connections_not_ok']} not ok, "
               f"{len(m_decl['declared_gapped'])} aside; blind: "
               f"{m_blind['connections']} folded, {m_blind['connections_not_ok']} "
               f"not ok, {len(m_blind['declared_gapped'])} aside")
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
    # The three named at step 3 are in the census with their reply chains, and
    # none waits any more: 0x009F HENCHMAN_ADD was armed at step 5, 0x00B1
    # MAP_TRAVEL at step 7, 0x004F ITEM_MOVE and 0x0030 EQUIP_ITEM at step 8
    # (all 2026-09-23) -- so each must be HANDLED and off the allowlist.
    for op, nm in ((0x009F, "HENCHMAN_ADD"), (0x004F, "ITEM_MOVE"),
                   (0x0030, "EQUIP_ITEM"), (0x00B1, "MAP_TRAVEL")):
        led.ok(named.get(op, ("", ""))[0] == nm and op not in dropped
               and op in live[0] and op in (handled or {}),
               f"0x{op:04X} is named {nm}, on retail's wire, ARMED (DESKWORK-D1) "
               f"and no longer on the allowlist",
               f"name {named.get(op)}, dropped {op in dropped}, "
               f"seen {op in live[0]}, handled {op in (handled or {})}")
    # The owner's confirmation pass (2026-09-23): the general move was seen
    # ONLY on our own client (1 of 1,581 loopback logs), never on retail's
    # wire -- so it is named and armed as RECONSTRUCTION and must stay OUT of
    # the live census; a retail tape carrying it would be the witness the arm
    # lacks, and this check going red is how that tape announces itself.
    led.ok(named.get(0x0072, ("", ""))[0] == "ITEM_MOVE_BY_ID"
           and 0x0072 in (handled or {}) and 0x0072 not in dropped
           and 0x0072 not in live[0],
           "0x0072 is named ITEM_MOVE_BY_ID, ARMED (RECONSTRUCTION), and on NO "
           "live tape -- seen only on our client (a retail send would make this "
           "red: read it, it is the witness)",
           f"name {named.get(0x0072)}, handled {0x0072 in (handled or {})}, "
           f"dropped {0x0072 in dropped}, live {0x0072 in live[0]}")
    # CASTAI-Z1 (2026-09-28): the Zaishen Challenge tape brought three c2s no
    # earlier tape carried. Triaged from its own evidence: all three NAMED medium
    # in overrides.json (the why is there) -- 0x00A3 at n=1 by the owner's decision
    # the same day, on the PARTY_LEAVE precedent -- and all three on the
    # allowlist: the server has no arena to arm them against (R7).
    for op, nm in ((0x009A, "ZAISHEN_CHALLENGE_LIST_REQUEST"),
                   (0x00A6, "ZAISHEN_CHALLENGE_ENTER"),
                   (0x00A3, "ZAISHEN_CHALLENGE_CANCEL")):
        led.ok((named.get(op, (None, ""))[0] == nm)
               and (nm is None or named[op][1] == "medium")
               and op in dropped and op in live[0] and op not in (handled or {}),
               f"0x{op:04X} is {'named ' + nm + ' (medium)' if nm else 'UNNAMED (n=1)'}, "
               f"on retail's wire, NOT armed and on the allowlist with its reason "
               f"(CASTAI-Z1)",
               f"name {named.get(op)}, dropped {op in dropped}, "
               f"seen {op in live[0]}, handled {op in (handled or {})}")
    # CASTAI-Z2 (2026-09-29): the second Zaishen tape brought ONE c2s no
    # earlier tape carried -- 0x0042 [agent_id], n=2, both naming the Zaishen
    # Fighter henchman at the instant of a TARGET_SELECT of it. UNNAMED on the
    # 0x00A3 precedent: no upstream names it and its sender is read only to
    # its module (GmView), so the house bar for a name is not met; the reason
    # is test_dispatch.DROPPED_ON_PURPOSE's row, and the server has nothing
    # to answer it with. `>= 2`, not `== 2`: a third send on a later tape is
    # confirming evidence, and the exact rows are the per-tape witness below.
    z2 = live[0].get(0x0042)
    led.ok(named.get(0x0042) is None and 0x0042 in dropped and z2 is not None
           and z2["count"] >= 2 and 0x0042 not in (handled or {}),
           "0x0042 is UNNAMED (n >= 2), on retail's wire, NOT armed and on the "
           "allowlist with its reason (CASTAI-Z2)",
           f"name {named.get(0x0042)}, dropped {0x0042 in dropped}, count "
           f"{None if z2 is None else z2['count']}, handled "
           f"{0x0042 in (handled or {})}")
else:
    led.skip("§4 the live half", "no live captures")


# The Zaishen triage's evidence, as ONE exact per-tape witness (R5): every send
# of the three on 20260928T103123 -- (client port, t, opcode, payload, the
# non-clock s2c within 50 ms as (opcode, summary), the map of the first 0x01A5
# transfer within 4 s or None). Scoped to that capture, so a later tape can
# add evidence but never redden it. What it pins: 0x009A is answered by the
# 0x01D7 menu (maps 321/318/320/319/322 and the ids of its six (id, dword,
# dword) triples, 51/52/55/57/50/60) 4 of 4; 0x00A6 [map, team, 0] by
# 0x01D9 [2, 1] + 0x01BB and a transfer to ITS map 4 of 4 -- except the one
# followed by 0x00A3, answered 0x01D9 [0, 0] with NO transfer (the control).
ZAISHEN_OPS = (0x009A, 0x00A3, 0x00A6)


def zaishen_sends(capdir):
    """(sends, aside): sends as above; aside = {connection: how many of the
    three its (whole) c2s side carries} for each connection the capture's
    manifest declares gapped -- set aside BY NAME and printed, never dropped
    silently. Its s2c is refused, so it can answer nothing, but its c2s still
    decodes and is counted."""
    gaps = livewire.declared_gaps(capdir)
    out, aside = [], {}
    for gf in livewire.connections(capdir):
        name = livewire.conn_name(gf)
        _conn, merged, _ok = livewire.decode_conn(capdir, gf)
        if name in gaps:
            aside[name] = sum(1 for _t, d, op, _v in merged
                              if d == "c2s" and op in ZAISHEN_OPS)
            print(f"      [aside] {name}: declared gapped by its manifest "
                  f"({gaps[name]}); {aside[name]} of the three on its c2s")
            continue
        port = int(name.split("->")[0].rsplit(":", 1)[1])
        for i, (t, d, op, v) in enumerate(merged):
            if d != "c2s" or op not in ZAISHEN_OPS:
                continue
            ans, transfer = [], None
            for t2, d2, op2, v2 in merged[i + 1:]:
                if t2 - t > 4.0:
                    break
                if d2 != "s2c":
                    continue
                if t2 - t <= 0.050 and op2 != c2striage.TICK:
                    ans.append((op2, (tuple(v2[1]), tuple(x[0] for x in v2[2]))
                                if op2 == 0x01D7 else tuple(v2[1:3])))
                if op2 == 0x01A5 and transfer is None:
                    transfer = v2[4]
            out.append((port, round(t, 3), op, tuple(v[1:]), tuple(ans), transfer))
    return sorted(out, key=lambda r: r[1]), aside


def _ints(v):
    if isinstance(v, (list, tuple)):
        for x in v:
            yield from _ints(x)
    elif isinstance(v, int):
        yield v


def zaishen_matches(capdir):
    """(matches, aside) for every 0x00A6 whose 0x01A5 transfer came (within
    4 s, as zaishen_sends reads it). The match connection is the FIRST
    connection to start after that transfer whose server address is the one
    the transfer names (0x01A5 field 1 is a sockaddr_in: family 2, port
    6112, then the IPv4 -- RECONSTRUCTION, refuted here if the link lands
    nowhere). matches = {connection: (team = the 0x00A6's field 2, the map
    the ENTER named, the map the connection's own first 0x0099 loads, s2c
    messages carrying the value 2809 anywhere in their fields)}; aside =
    {connection: (team, map)} for a linked connection its manifest declares
    gapped -- its s2c is refused, so it is printed by name, never counted."""
    gaps = livewire.declared_gaps(capdir)
    starts, decoded = [], {}
    for gf in livewire.connections(capdir):
        name = livewire.conn_name(gf)
        _c, ev, _e = livewire.build_events(capdir, gf, "c2s")
        starts.append((ev[0][0] if ev else float("inf"), name, gf))
        decoded[name] = livewire.decode_conn(capdir, gf)[1]
    starts.sort()
    matches, aside = {}, {}
    for name, merged in decoded.items():
        if name in gaps:
            continue
        for i, (t, d, op, v) in enumerate(merged):
            if d != "c2s" or op != 0x00A6:
                continue
            xfer = next(((t2, v2) for t2, d2, op2, v2 in merged[i + 1:]
                         if d2 == "s2c" and op2 == 0x01A5 and t2 - t <= 4.0),
                        None)
            if xfer is None:
                continue          # the cancelled entry: no transfer, no match
            t_x, sa = xfer[0], bytes(xfer[1][1])
            ip = ".".join(str(b) for b in sa[4:8])
            nxt = next((n for s, n, _g in starts
                        if s > t_x and n.split("->")[1].rsplit(":", 1)[0] == ip),
                       None)
            team, emap = v[2], v[1]
            if nxt is None:
                matches[f"(no connection to {ip} after t={t_x:.3f})"] = (
                    team, emap, None, None)
            elif nxt in gaps:
                aside[nxt] = (team, emap)
                print(f"      [aside] {nxt}: ENTER [{emap}, {team}] leads here; "
                      f"declared gapped by its manifest ({gaps[nxt]}), its s2c "
                      f"refused -- not counted")
            else:
                m = decoded[nxt]
                lmap = next((v2[1] for _t, d2, op2, v2 in m
                             if d2 == "s2c" and op2 == 0x0099), None)
                n = sum(1 for _t, d2, _op, v2 in m
                        if d2 == "s2c" and 2809 in _ints(v2))
                matches[nxt] = (team, emap, lmap, n)
    return matches, aside


MENU = (0x01D7, ((321, 318, 320, 319, 322), (51, 52, 55, 57, 50, 60)))
HOLD = ((0x01D9, (2, 1)), (0x01BB, (3, 1)))
ZAISHEN_WITNESS = [
    (51300, 86.55, 0x009A, (), (MENU,), None),
    (51300, 91.439, 0x00A6, (320, 55, 0), HOLD, 320),
    (64997, 246.478, 0x009A, (), ((0x000C, ()), MENU), None),
    (64997, 250.149, 0x00A6, (318, 55, 0), HOLD, 318),
    (50267, 372.072, 0x009A, (), (MENU,), None),
    (50267, 375.142, 0x00A6, (320, 55, 0), HOLD, None),
    (50267, 377.611, 0x00A3, (), ((0x01D9, (0, 0)),), None),
    (50267, 412.398, 0x00A6, (322, 52, 0), HOLD, 322),
    (64494, 541.594, 0x009A, (), (MENU,), None),
    (64494, 545.081, 0x00A6, (318, 55, 0), HOLD, 318),
]
zdir = os.path.join(livewire.captures_root(), "20260928T103123")
# Which connection each transferred ENTER led to, and what it carried: skill
# id 2809 (WIKI label Obsidian Flame (PvP), the Obsidian Spike team's skill)
# is on the team-52 match only -- the evidence behind overrides.json 0x00A6's
# "field 2 selects the OPPONENTS". Exact, scoped to this one capture.
ZAISHEN_MATCHES = {
    "10.0.0.210:50061->54.198.7.73:80": (55, 320, 320, 0),
    "10.0.0.210:50295->54.198.7.73:80": (52, 322, 322, 34),
    "10.0.0.210:58544->98.95.137.136:80": (55, 318, 318, 0),
}
ZAISHEN_MATCH_ASIDE = {"10.0.0.210:65009->98.95.137.136:80": (55, 318)}
if os.path.isdir(zdir):
    zs, zaside = zaishen_sends(zdir)
    led.ok(zs == ZAISHEN_WITNESS,
           "WITNESS (20260928T103123, exact): 0x009A -> the 0x01D7 menu (maps "
           "and triple ids) 4 of 4; 0x00A6 [map, team, 0] -> 0x01D9 [2, 1] + "
           "0x01BB and a transfer to ITS map 4 of 4; the one 0x00A6 followed by "
           "0x00A3 -> 0x01D9 [0, 0] and NO transfer",
           "\n      " + "\n      ".join(repr(r) for r in zs))
    led.ok(zaside == {"10.0.0.210:65009->98.95.137.136:80": 0},
           "...the witness sets aside exactly the manifest's gapped connection "
           "(match 2), by name, and its decodable c2s carries none of the three",
           f"aside {zaside}")
    # Every ENTER's map and team come from the menu its connection received:
    # the last 0x009A before it on the same port was answered by 0x01D7, and
    # [map, team] are a map of its list and an id of its triples.
    menu_of, picks = {}, []
    for port, _t, op, pay, ans, _x in zs:
        if op == 0x009A:
            menu_of[port] = next((a[1] for a in ans if a[0] == 0x01D7), None)
        elif op == 0x00A6:
            mn = menu_of.get(port)
            picks.append(mn is not None and pay[0] in mn[0] and pay[1] in mn[1])
    led.ok(len(picks) == 5 and all(picks),
           "every 0x00A6 (5 of 5) names a map from its connection's 0x01D7 map "
           "list and a team id from its 0x01D7 triples",
           f"picks {picks}")
    zm, zmaside = zaishen_matches(zdir)
    led.ok(zm == ZAISHEN_MATCHES and zmaside == ZAISHEN_MATCH_ASIDE,
           "0x00A6 field 2 SELECTS THE OPPONENTS (20260928T103123, exact): each "
           "transferred ENTER links to the next connection at the address its "
           "0x01A5 names, that connection loads the ENTER's map, and skill id "
           "2809 is on 34 s2c of the team-52 match and 0 of both decodable "
           "team-55 matches; the gapped team-55 match is set aside by name",
           f"matches {zm}; aside {zmaside}")
else:
    led.skip("the Zaishen witness", "capture 20260928T103123 (CASTAI-Z1) missing")


# CASTAI-Z2's evidence as SIX exact per-tape witnesses, all scoped to
# 20260929T100038 so a later tape adds evidence and never reddens them (C4).
#
# WITNESS 1: every c2s 0x0042 on the tape as
#   (client port, t, payload,
#    MATES  -- every OTHER c2s at the same timestamp, as (opcode, payload),
#    WINDOW -- every non-clock message EITHER WAY within 50 ms after the send,
#              in wire order, as (dir, opcode, fields 1-2),
#    TARGET -- the target's last 0x00F1 [target, effects] and last 0x0026
#              [target, flags] before the send, each as (t, word) or None,
#    PLAYER -- (the own agent, by the self-scoped anchor own_agent() below;
#              its last 0x00F1 and last 0x0026 before the send, each as
#              (t, word) or None)).
# The window carries c2s ON PURPOSE. Round 1 (657d9222) kept only s2c there
# and so pinned the s2c 0x0022 [9, 0] as "0x0042's answer" while structurally
# hiding the nearer candidate: a SECOND TARGET_SELECT [9, 0] at 245.268, 26 ms
# after the 0x0042 and 11 ms before the 0x0022 (the contract reviewer's first
# C10 block, 2026-09-29). Round 2 (f676b6b3) read the TARGET's state and left
# the PLAYER's unread -- the operand that separates the two sends from the
# nine selects without one (the second block, same day). What the literal
# says now: n=2, both [9]; each at the timestamp of a TARGET_SELECT [9, x];
# the FIRST 5.285 s into the PLAYER's death (0x00F1 [7, 0x10] + 0x0026 [7, 4]
# at 239.957 -- effects bit 4 is death, studies/agentprops/FINDINGS.md §1c,
# OBSERVED both ways; 0x0026 4/5 the player's death/revival, adrenjoin.py)
# with the target ALSO dead (0x00F1 0x10 + 0x0026 8 since 243.458; 8/9 an
# NPC's dead/alive track, studies/isle), followed within 50 ms by 0x00E6,
# that second TARGET_SELECT [9, 0], 0x0021 WORLD_REMOVE_AGENT of agents 1 and
# 2 and the next 0x0022, [9, 0]; the SECOND 21 ms after the player's revival
# (0x00F1 [7, 0] + 0x0026 [7, 5] at 402.778) with the target alive (effects
# 0x800, no 0x0026 of it yet), followed by nothing. Which of the two c2s 11
# and 37 ms before the 0x0022 drew it is not shown at n=1; what that 0x0022
# IS -- a handoff of control while dead -- reads off witness 3.
PLAYER_INFO = 0x0059          # [player NUMBER, agent, appearance, ...] -- the
                              # server sends one per PLAYER in the instance
INSTANCE_LOAD_INFO = 0x0199   # field 1 is the OWN player's NUMBER (the send
                              # site in authsrv.py; studies/heroes/FINDINGS.md 22)


def own_routes(merged):
    """The connection's own agent by three routes, as (anchor, load, first),
    each None where it cannot resolve.
      ANCHOR -- adrenjoin.whose_agent over the s2c: int property 41 on 0x009F
        is SELF-SCOPED (studies/skills/FINDINGS.md 23: every one in the corpus
        names the observing player's own agent), a hero's copy broken by the
        kind-5 0x0020 (JARIN, 2026-09-14). The sound rule, and the one the
        witnesses below read.
      LOAD -- 0x0199's field 1, the own player's NUMBER, mapped through the
        PLAYER_INFO (number, agent) pairs: moralescan.py's independent second
        route, which agrees with the anchor on every corpus connection where
        both resolve (110 of 116 on 2026-09-29, z2c2s-r4-own.py).
      FIRST -- field 2 of the PLAYER_INFO whose number is 1. NOT a definition:
        round 3 (72e2ba21) took it for one, and it is the class of rule
        moralescan.py refuted on 2026-08-21 ("wrong 20 times in 44") -- over
        the live corpus it names the WRONG agent on 34 of 116 connections and
        none on 14 more, 43 of the 110 instance loads (20260807T143055 :60935
        says 536 where the anchor and scriptrun.py say 725). Carried so the
        tape's agreement is a measurement (WITNESS 0), never as a fallback."""
    s2c = [(t, op, v) for t, d, op, v in merged if d == "s2c"]
    anchor = adrenjoin.whose_agent(s2c)
    pairs = {v[1]: v[2] for _t, op, v in s2c
             if op == PLAYER_INFO and len(v) > 2}
    number = next((v[1] for _t, op, v in s2c
                   if op == INSTANCE_LOAD_INFO and len(v) > 1), None)
    # FIRST is the FIRST PLAYER_INFO numbered 1, as documented (2026-09-29, the
    # orchestrator, the round-4 reviewer's note): `pairs` keeps the LAST entry
    # per number, which named 328 on 20260807T143055 :60935 where the first is
    # 536. The two readings disagree on 4 corpus connections and are wrong on
    # the same 34.
    first = next((v[2] for _t, op, v in s2c
                  if op == PLAYER_INFO and len(v) > 2 and v[1] == 1), None)
    return anchor, pairs.get(number), first


def own_agent(merged):
    """The connection's own agent: own_routes' ANCHOR, cross-checked against
    its LOAD route -- None when the anchor cannot resolve or the two disagree.
    A refusal, never a guess (adrenjoin.whose_agent's NO FALLBACK): a None
    empties every PLAYER column downstream and reddens the witness that
    pinned it, with the three routes printed by WITNESS 0."""
    anchor, load, _first = own_routes(merged)
    if anchor is None or (load is not None and load != anchor):
        return None
    return anchor


def life_state(merged, upto, agent):
    """(last 0x00F1 [agent, effects], last 0x0026 [agent, flags]) among the
    s2c strictly before index `upto`, each as (t, word) or None."""
    eff = flags = None
    for t, d, op, v in merged[:upto]:
        if d != "s2c" or len(v) < 3 or v[1] != agent:
            continue
        if op == 0x00F1:
            eff = (round(t, 3), v[2])
        elif op == 0x0026:
            flags = (round(t, 3), v[2])
    return eff, flags


def sends_0042(capdir):
    """(sends, aside) as above; aside = {connection: its 0x0042 count} for a
    connection the capture's manifest declares gapped -- set aside BY NAME and
    printed, never dropped silently (this tape declares none)."""
    gaps = livewire.declared_gaps(capdir)
    out, aside = [], {}
    for gf in livewire.connections(capdir):
        name = livewire.conn_name(gf)
        _conn, merged, _ok = livewire.decode_conn(capdir, gf)
        if name in gaps:
            aside[name] = sum(1 for _t, d, op, _v in merged
                              if d == "c2s" and op == 0x0042)
            print(f"      [aside] {name}: declared gapped by its manifest "
                  f"({gaps[name]}); {aside[name]} x 0x0042 on its c2s")
            continue
        port = int(name.split("->")[0].rsplit(":", 1)[1])
        own = own_agent(merged)
        for i, (t, d, op, v) in enumerate(merged):
            if d != "c2s" or op != 0x0042:
                continue
            mates = tuple((op2, tuple(v2[1:])) for t2, d2, op2, v2 in merged
                          if d2 == "c2s" and op2 != 0x0042 and abs(t2 - t) < 0.001)
            # Both directions: a c2s in the window is a competing candidate
            # for whatever s2c follows it, and the literal must carry it.
            window = tuple((d2, op2, tuple(v2[1:3]))
                           for t2, d2, op2, v2 in merged[i + 1:]
                           if t2 - t <= 0.050
                           and not (d2 == "s2c" and op2 == c2striage.TICK)
                           and not (d2 == "c2s" and abs(t2 - t) < 0.001))
            out.append((port, round(t, 3), tuple(v[1:]), mates, window,
                        life_state(merged, i, v[1]),
                        (own,) + life_state(merged, i, own)))
    return sorted(out, key=lambda r: r[1]), aside


def selects_of(capdir, agent):
    """Every c2s TARGET_SELECT [agent, x] on the capture as (client port, t,
    field 2, a 0x0042 at the same timestamp?, the agent's last 0x00F1 effects
    word before it or None, the OWN agent's last 0x00F1 word, its last 0x0026
    word, the last s2c 0x0022 before it as (agent, x) -- the control in
    force -- or None); gapped connections set aside by name as above."""
    gaps = livewire.declared_gaps(capdir)
    out, aside = [], {}
    for gf in livewire.connections(capdir):
        name = livewire.conn_name(gf)
        _conn, merged, _ok = livewire.decode_conn(capdir, gf)
        if name in gaps:
            aside[name] = sum(1 for _t, d, op, v in merged
                              if d == "c2s" and op == 0x00C1 and v[1] == agent)
            print(f"      [aside] {name}: declared gapped by its manifest "
                  f"({gaps[name]}); {aside[name]} x TARGET_SELECT [{agent}]")
            continue
        port = int(name.split("->")[0].rsplit(":", 1)[1])
        own = own_agent(merged)
        t42 = [t for t, d, op, _v in merged if d == "c2s" and op == 0x0042]
        eff = own_eff = own_flags = control = None
        for t, d, op, v in merged:
            if d == "s2c" and op == 0x00F1 and len(v) > 2 and v[1] == agent:
                eff = v[2]
            if d == "s2c" and op == 0x00F1 and len(v) > 2 and v[1] == own:
                own_eff = v[2]
            elif d == "s2c" and op == 0x0026 and len(v) > 2 and v[1] == own:
                own_flags = v[2]
            elif d == "s2c" and op == 0x0022 and len(v) > 2:
                control = (v[1], v[2])
            elif d == "c2s" and op == 0x00C1 and v[1] == agent:
                out.append((port, round(t, 3), v[2],
                            any(abs(t2 - t) < 0.001 for t2 in t42), eff,
                            own_eff, own_flags, control))
    return sorted(out, key=lambda r: r[1]), aside


# The two agents the handoff removes and the return re-creates (0x0020 at the
# load as types 3424 / 3426, kind 3 -- what they are is unread).
TRACK_AGENTS = (1, 2)


def control_track(capdir, port):
    """(own agent, rows) for the connection with that client port: every s2c
    0x0022 [agent, x], every 0x0020 [agent, type, kind] / 0x0021 [agent] of
    TRACK_AGENTS and every 0x00F1 / 0x0026 [own, word], as (t, opcode,
    fields) in wire order. (None, []) when no connection has the port."""
    for gf in livewire.connections(capdir):
        name = livewire.conn_name(gf)
        if int(name.split("->")[0].rsplit(":", 1)[1]) != port:
            continue
        _conn, merged, _ok = livewire.decode_conn(capdir, gf)
        own = own_agent(merged)
        rows = []
        for t, d, op, v in merged:
            if d != "s2c":
                continue
            if op == 0x0022:
                rows.append((round(t, 3), op, tuple(v[1:3])))
            elif op == 0x0020 and len(v) > 3 and v[1] in TRACK_AGENTS:
                rows.append((round(t, 3), op, tuple(v[1:4])))
            elif op == 0x0021 and len(v) > 1 and v[1] in TRACK_AGENTS:
                rows.append((round(t, 3), op, tuple(v[1:2])))
            elif op in (0x00F1, 0x0026) and len(v) > 2 and v[1] == own:
                rows.append((round(t, 3), op, tuple(v[1:3])))
        return own, rows
    return None, []


def controls(capdir):
    """({client port: every s2c 0x0022 on the connection as (t, (agent, x))},
    aside) over every connection the manifest does not declare gapped; a
    gapped one is set aside by name with its count, as above."""
    gaps = livewire.declared_gaps(capdir)
    out, aside = {}, {}
    for gf in livewire.connections(capdir):
        name = livewire.conn_name(gf)
        _conn, merged, _ok = livewire.decode_conn(capdir, gf)
        rows = [(round(t, 3), tuple(v[1:3])) for t, d, op, v in merged
                if d == "s2c" and op == 0x0022]
        if name in gaps:
            aside[name] = len(rows)
            print(f"      [aside] {name}: declared gapped by its manifest "
                  f"({gaps[name]}); {len(rows)} x 0x0022 on its s2c")
            continue
        out[int(name.split("->")[0].rsplit(":", 1)[1])] = rows
    return out, aside


def dead_selects(capdir):
    """Every c2s TARGET_SELECT sent while the OWN agent's last 0x0026 word was
    4 (its death; 5 is the revival -- adrenjoin.py), as (client port, t,
    (agent, x), a 0x0042 at the same timestamp?, the target's 0x0020 type
    dword or None, the 0x0022 in force as (agent, x)); gapped connections set
    aside by name as above."""
    gaps = livewire.declared_gaps(capdir)
    out, aside = [], {}
    for gf in livewire.connections(capdir):
        name = livewire.conn_name(gf)
        _conn, merged, _ok = livewire.decode_conn(capdir, gf)
        port = int(name.split("->")[0].rsplit(":", 1)[1])
        own = own_agent(merged)
        t42 = [t for t, d, op, _v in merged if d == "c2s" and op == 0x0042]
        types, rows = {}, []
        flags = control = None
        for t, d, op, v in merged:
            if d != "c2s":
                if op == 0x0020 and len(v) > 2:
                    types[v[1]] = v[2]
                elif op == 0x0026 and len(v) > 2 and v[1] == own:
                    flags = v[2]
                elif op == 0x0022 and len(v) > 2:
                    control = (v[1], v[2])
            elif op == 0x00C1 and flags == 4:
                rows.append((port, round(t, 3), tuple(v[1:3]),
                             any(abs(t2 - t) < 0.001 for t2 in t42),
                             types.get(v[1]), control))
        if name in gaps:
            aside[name] = len(rows)
            print(f"      [aside] {name}: declared gapped by its manifest "
                  f"({gaps[name]}); {len(rows)} x TARGET_SELECT while dead")
            continue
        out.extend(rows)
    return sorted(out, key=lambda r: r[1]), aside


def owns(capdir):
    """({client port: own_routes(connection)}, aside) over every connection
    the manifest does not declare gapped; a gapped one is set aside by name
    with its routes, as above."""
    gaps = livewire.declared_gaps(capdir)
    out, aside = {}, {}
    for gf in livewire.connections(capdir):
        name = livewire.conn_name(gf)
        _conn, merged, _ok = livewire.decode_conn(capdir, gf)
        routes = own_routes(merged)
        if name in gaps:
            aside[name] = routes
            print(f"      [aside] {name}: declared gapped by its manifest "
                  f"({gaps[name]}); own routes {routes}")
            continue
        out[int(name.split("->")[0].rsplit(":", 1)[1])] = routes
    return out, aside


# WITNESS 0: the own agent on each of the tape's 11 connections by the three
# routes of own_routes -- (anchor, load, first), exact: 7 on the five match
# connections, 11 on the six outpost ones, all three routes agreeing on all
# 11. This is WHY witnesses 1-5 below survived round 4's correction of the
# rule that built them: the own player's number is 1 on every connection of
# this tape (0x0199 field 1), so the refuted first-PLAYER_INFO rule happens
# to name the anchor's agent here, where on 43 of the corpus's 110 instance
# loads it does not (34 wrong, 9 none). Scoped to the tape (C4); the anchor
# is what the other five read.
Z2_OWN = {
    51077: (11, 11, 11), 51090: (7, 7, 7), 51187: (11, 11, 11),
    51199: (7, 7, 7), 57580: (7, 7, 7), 59334: (11, 11, 11),
    60536: (11, 11, 11), 62915: (11, 11, 11), 62925: (7, 7, 7),
    64548: (11, 11, 11), 64557: (7, 7, 7),
}
Z2_0042_WITNESS = [
    (62925, 245.242, (9,), ((0x00C1, (9, 3)),),
     (("s2c", 0x00E6, (7, 364)), ("c2s", 0x00C1, (9, 0)),
      ("s2c", 0x0021, (1,)), ("s2c", 0x0021, (2,)), ("s2c", 0x0022, (9, 0))),
     ((243.458, 0x10), (243.458, 8)),
     (7, (239.957, 0x10), (239.957, 4))),
    (51090, 402.799, (9,), ((0x00C1, (9, 0)),), (),
     ((397.555, 0x800), None),
     (7, (402.778, 0), (402.778, 5))),
]
# WITNESS 2: every TARGET_SELECT of agent 9 (the Zaishen Fighter on all three
# match connections: WORLD_CREATE_AGENT type 0x20000018, professions 1/0) on
# the tape as (port, t, field 2, a 0x0042 at the same timestamp?, the
# target's last effects word, the PLAYER's last 0x00F1 and 0x0026 words, the
# 0x0022 in force). 11 of them. The two with a 0x0042 are the only selects of
# agent 9 made while the player was dead (245.242: 0x10 / 4) or had just
# revived (402.799: 0 / 5, 21 ms after 0x0026 [7, 5]); of the nine without,
# seven came with the player alive and the other two fall inside the SAME
# death -- 245.268, 26 ms after the 0x0042 had already gone out, and 256.269,
# with control ALREADY on agent 9 (the [9, 0] in force from 245.279 to
# 259.459), so nothing was left to hand over and that select is no evidence
# either way. Round 2 wrote "neither life-state nor first-select separates
# them" off the TARGET's state alone and read 256.269 as disconfirming; the
# player's state does separate them on this tape (n=2 -- a RECONSTRUCTION of
# the rule until a run varies it, witness 5 its control).
Z2_SEL9_WITNESS = [
    (57580, 137.899, 6, False, 0x10, 0, 5, (7, 3)),
    (57580, 142.007, 6, False, 0, 0x800, 5, (7, 3)),
    (57580, 142.318, 3, False, 0, 0x800, 5, (7, 3)),
    (57580, 164.124, 0, False, 0, 0, 5, (7, 3)),
    (62925, 245.242, 3, True, 0x10, 0x10, 4, (7, 3)),
    (62925, 245.268, 0, False, 0x10, 0x10, 4, (7, 3)),
    (62925, 256.269, 0, False, 0, 0x10, 4, (9, 0)),
    (51090, 402.799, 0, True, 0x800, 0, 5, (7, 3)),
    (51090, 403.100, 5, False, 0x800, 0, 5, (7, 3)),
    (51090, 407.738, 5, False, 0x10, 0, 5, (7, 3)),
    (51090, 408.406, 4, False, 0x10, 0, 5, (7, 3)),
]
# WITNESS 3: the :62925 CONTROL TRACK (control_track above). What it pins: the
# player (7) died at 239.957; at 245.279 -- 37 ms after the 0x0042 and 11 ms
# after the second TARGET_SELECT [9, 0] -- ONE chunk carried 0x0021
# WORLD_REMOVE_AGENT of agents 1 and 2 and 0x0022 [9, 0]; at 259.459 ONE
# batch re-created 1 and 2 (the same types and kind as at the load), sent
# 0x0022 [7, 1] and revived the player (0x00F1 [7, 0] + 0x0026 [7, 5]). So
# control passed to agent 9 while the player was dead and came back when it
# revived: 0x0022 [x, 0] as the handoff and [own, 1] as the return is a
# RECONSTRUCTION (UPSTREAM name WORLD_UPDATE_CONTROLLED_AGENT, Headquarter /
# OpenTyria), and the same [other, 1] then [own, 1] pair shape sits on EVERY
# earlier tape with a mid-connection 0x0022, own by the anchor: 20260807T143055
# ([300, 1] 18.200 then [725, 1] 20.140; own 725), 20260810T235916 ([201, 1]
# 20.053 then [176, 1] 22.054; own 176), 20260817T180610 ([73, 1] 268.147
# then [8, 1] 279.220; own 8) and 20260913T210901 ([73, 1] 73.874 then [8, 1]
# 117.877; own 8) -- four pairs, not the two round 3 named: its
# first-PLAYER_INFO rule read 807's and 810's own as 536 and 63 and so called
# both pairs "both other". The player's second death on the connection
# (300.460 - 305.705, no
# TARGET_SELECT sent in it) drew neither.
Z2_CONTROL_TRACK = [
    (182.663, 0x0020, (1, 3424, 3)),
    (182.663, 0x0020, (2, 3426, 3)),
    (182.663, 0x0022, (7, 3)),
    (239.957, 0x00F1, (7, 0x10)),
    (239.957, 0x0026, (7, 4)),
    (245.279, 0x0021, (1,)),
    (245.279, 0x0021, (2,)),
    (245.279, 0x0022, (9, 0)),
    (259.459, 0x0020, (1, 3424, 3)),
    (259.459, 0x0020, (2, 3426, 3)),
    (259.459, 0x0022, (7, 1)),
    (259.459, 0x00F1, (7, 0)),
    (259.459, 0x0026, (7, 5)),
    (267.971, 0x00F1, (7, 0x800)),
    (297.976, 0x00F1, (7, 0)),
    (300.460, 0x00F1, (7, 0x10)),
    (300.460, 0x0026, (7, 4)),
    (305.705, 0x00F1, (7, 0)),
    (305.705, 0x0026, (7, 5)),
]
# WITNESS 4: every 0x0022 on the tape's 11 connections -- [own, 3] at each
# load (own = 11 in the outpost, 7 in a match) and the :62925 pair, the tape's
# ONLY mid-connection control change: the player's eleven other deaths on the
# five match connections drew none.
Z2_CONTROLS = {
    51077: [(335.705, (11, 3))],
    51090: [(347.914, (7, 3))],
    51187: [(467.798, (11, 3))],
    51199: [(480.201, (7, 3))],
    57580: [(83.950, (7, 3))],
    59334: [(49.902, (11, 3))],
    60536: [(680.620, (11, 3))],
    62915: [(170.964, (11, 3))],
    62925: [(182.663, (7, 3)), (245.279, (9, 0)), (259.459, (7, 1))],
    64548: [(583.141, (11, 3))],
    64557: [(595.542, (7, 3))],
}
# WITNESS 5: every TARGET_SELECT sent while the player's last 0x0026 word was
# 4 -- five. Four are that one death's: the 0x0042's own [9, 3], the [9, 0]
# 26 ms later, and [0, 0] + [9, 0] at 256.269 under agent 9's control; the
# fifth is of a FOE (agent 4, type 0x2000007C, :51199 at 572.355, no 0x0042).
# So the tape holds no select of a PARTY member while dead that did not carry
# a 0x0042, except inside the death the first one had already served -- the
# observe-while-dead reading's control, not its proof (one death with a
# select in it).
Z2_DEAD_SELECTS = [
    (62925, 245.242, (9, 3), True, 0x20000018, (7, 3)),
    (62925, 245.268, (9, 0), False, 0x20000018, (7, 3)),
    (62925, 256.269, (0, 0), False, None, (9, 0)),
    (62925, 256.269, (9, 0), False, 0x20000018, (9, 0)),
    (51199, 572.355, (4, 0), False, 0x2000007C, (7, 3)),
]
z2dir = os.path.join(livewire.captures_root(), "20260929T100038")
if os.path.isdir(z2dir):
    z2owns, z2ownsaside = owns(z2dir)
    led.ok(z2owns == Z2_OWN and z2ownsaside == {},
           "WITNESS 0 (20260929T100038, exact): the own agent by the self-scoped "
           "anchor (property 41), by 0x0199's player number through PLAYER_INFO "
           "and by the first PLAYER_INFO agree on all 11 connections -- 7 on the "
           "five matches, 11 on the six outposts; no connection set aside",
           "\n      " + "\n      ".join(f"{p}: {z2owns[p]}" for p in sorted(z2owns))
           + f"\n      aside {z2ownsaside}")
    z2s, z2aside = sends_0042(z2dir)
    led.ok(z2s == Z2_0042_WITNESS and z2aside == {},
           "WITNESS 1 (20260929T100038, exact): 0x0042 [9] x2, each at the "
           "timestamp of a TARGET_SELECT [9, x]; the first 5.285 s into the "
           "PLAYER's death (0x00F1 [7, 0x10] + 0x0026 [7, 4] at 239.957) with "
           "the target also dead, followed within 50 ms by 0x00E6, a SECOND "
           "TARGET_SELECT [9, 0], 0x0021 x2 and the next 0x0022, [9, 0]; the "
           "second 21 ms after the player's revival (0x0026 [7, 5] at 402.778) "
           "with the target alive, followed by nothing; no connection set aside",
           "\n      " + "\n      ".join(repr(r) for r in z2s)
           + f"\n      aside {z2aside}")
    z2sel, z2selaside = selects_of(z2dir, 9)
    led.ok(z2sel == Z2_SEL9_WITNESS and z2selaside == {},
           "WITNESS 2 (20260929T100038, exact): 11 TARGET_SELECTs of agent 9 on "
           "3 match connections -- the 2 with a 0x0042 are the only ones sent "
           "while the player was dead (245.242) or 21 ms revived (402.799); of "
           "the 9 without, 7 with the player alive and 2 inside that same death "
           "(245.268, after the 0x0042; 256.269, control already on 9); no "
           "connection set aside",
           "\n      " + "\n      ".join(repr(r) for r in z2sel)
           + f"\n      aside {z2selaside}")
    z2own, z2track = control_track(z2dir, 62925)
    led.ok(z2own == 7 and z2track == Z2_CONTROL_TRACK,
           "WITNESS 3 (20260929T100038 :62925, exact): the player (7 by the "
           "anchor) dead at 239.957; 0x0022 [9, 0] in one chunk with "
           "WORLD_REMOVE_AGENT of agents 1 and 2 at 245.279; its return 0x0022 "
           "[7, 1] with their re-creates and the player's revival at 259.459; "
           "the second death (300.460-305.705) drew neither",
           f"\n      own {z2own}\n      "
           + "\n      ".join(f"({t}, 0x{op:04X}, {f})" for t, op, f in z2track))
    z2ctl, z2ctlaside = controls(z2dir)
    led.ok(z2ctl == Z2_CONTROLS and z2ctlaside == {},
           "WITNESS 4 (20260929T100038, exact): every 0x0022 on the tape's 11 "
           "connections -- [own, 3] at each load and the :62925 pair [9, 0] / "
           "[7, 1], the only mid-connection control change; no connection set "
           "aside",
           "\n      " + "\n      ".join(f"{p}: {z2ctl[p]}" for p in sorted(z2ctl))
           + f"\n      aside {z2ctlaside}")
    z2dead, z2deadaside = dead_selects(z2dir)
    led.ok(z2dead == Z2_DEAD_SELECTS and z2deadaside == {},
           "WITNESS 5 (20260929T100038, exact): 5 TARGET_SELECTs while the "
           "player's last 0x0026 word was 4 -- the 0x0042's, then [9, 0] 26 ms "
           "later and [0, 0] + [9, 0] under agent 9's control, all in that one "
           "death, and one of a foe (agent 4) on :51199 with no 0x0042; no "
           "party-member select while dead is without a 0x0042 outside the "
           "death the first one served; no connection set aside",
           "\n      " + "\n      ".join(repr(r) for r in z2dead)
           + f"\n      aside {z2deadaside}")
else:
    led.skip("the CASTAI-Z2 0x0042 witnesses",
             "capture 20260929T100038 (CASTAI-Z2) missing")
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
# CASTAI-Z2 (2026-09-29): 0x0042's decision is its DROPPED_ON_PURPOSE row and
# nothing else -- vault-free, over a literal census, so a bare machine checks
# the decision too: dropped with the row, UNTRIAGED and named alone without it.
led.ok(c2striage.status_of(0x0042, handled or {}, named, dropped) == "dropped"
       and c2striage.untriaged({0x0042: {}}, handled or {}, named, dropped) == [],
       "0x0042 is triaged by its allowlist row alone: status dropped, and a "
       "census of just it has nothing untriaged (CASTAI-Z2)",
       f"status {c2striage.status_of(0x0042, handled or {}, named, dropped)}, "
       f"named {named.get(0x0042)}")
without_42 = {k: v for k, v in dropped.items() if k != 0x0042}
led.ok(c2striage.status_of(0x0042, handled or {}, named, without_42) == "UNTRIAGED"
       and c2striage.untriaged({0x0042: {}, 0x0009: {}}, handled or {}, named,
                               without_42) == [0x0042],
       "KNOWN-BAD: remove the 0x0042 row and it is UNTRIAGED, named alone",
       f"status {c2striage.status_of(0x0042, handled or {}, named, without_42)}")
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
