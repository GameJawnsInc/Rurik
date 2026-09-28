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
    decision (named medium / unnamed, dropped, not armed) and ONE exact
    per-tape witness of the evidence behind it.
  * §5 REFUSALS: a root with no live capture makes `main()` exit 2 rather than
    print a clean table, and a dispatch chain that cannot be located refuses.
  * §6 STATIC hints: on a machine with the pinned client the send-site census
    joins -- 0x001F's wrapper is 0x0091FF30 on 38797 -- else a skip.

Floor 20 -- the MANDATORY CORE, measured on 2026-09-23 with RURIK_VAULT pointed
at an empty directory (§1, §3's file half, §4's file half, §5: the checks that
need no vault and no client). With the vault and the pinned client present the
same run executes 34 (42 since 2026-09-28: the declared-gap pin and its
known-bad arm, three Zaishen decisions, the Zaishen witness); §2, §3's live
half, §4's live half, the witness and §6 declare skips
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
    # earlier tape carried. Triaged from its own evidence: two NAMED medium in
    # overrides.json (the why is there), one UNNAMED at n=1, all three on the
    # allowlist -- the server has no arena to arm them against (R7).
    for op, nm in ((0x009A, "ZAISHEN_CHALLENGE_LIST_REQUEST"),
                   (0x00A6, "ZAISHEN_CHALLENGE_ENTER"), (0x00A3, None)):
        led.ok((named.get(op, (None, ""))[0] == nm)
               and (nm is None or named[op][1] == "medium")
               and op in dropped and op in live[0] and op not in (handled or {}),
               f"0x{op:04X} is {'named ' + nm + ' (medium)' if nm else 'UNNAMED (n=1)'}, "
               f"on retail's wire, NOT armed and on the allowlist with its reason "
               f"(CASTAI-Z1)",
               f"name {named.get(op)}, dropped {op in dropped}, "
               f"seen {op in live[0]}, handled {op in (handled or {})}")
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
