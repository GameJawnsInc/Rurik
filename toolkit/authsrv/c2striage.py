"""Retail's c2s triage: every GAME_CMSG opcode ArenaNet's own client sent on
the live wire, and what THIS server does with each one.

    python toolkit/authsrv/c2striage.py                # the table
    python toolkit/authsrv/c2striage.py --untriaged    # only the rows that need a decision
    python toolkit/authsrv/c2striage.py --static       # + the send-site census per opcode
    python toolkit/authsrv/c2striage.py --write        # regenerate retail_c2s.json
    python toolkit/authsrv/c2striage.py --json         # the table as JSON on stdout

DESKWORK-D1 step 3 (studies/deskwork/PLAN.md, studies/cmsg/FINDINGS.md). Every
"c2s NOT FOUND" and every "the server ignores X" in this repo rested on a
one-off script over one capture. This is the committed recipe: over EVERY
origin=LIVE game connection (`livewire.live_connections`, the refuse-to-mix
loader), per c2s opcode -- how many, on how many captures and connections,
whether the schema NAMES it, whether the server HANDLES it (the dispatch chain,
read by syntax tree the way `test_dispatch.py` reads it), whether the drop is
ON PURPOSE (`test_dispatch.DROPPED_ON_PURPOSE`, the ONE place a drop reason
lives), and what retail's server answered FIRST within `REPLY_WINDOW` seconds.

THE REVERSE GUARD. `test_dispatch.py` §7 asks "is every NAMED opcode handled
or dropped on purpose?" -- a name earns a decision. It could not ask about an
opcode nothing has named, and retail's wire carries several of those. So this
tool writes the census to `retail_c2s.json` beside it (`--write`), and
`test_dispatch.py` §10 reads THAT file -- no vault, as that test insists -- and
reddens on any opcode retail sent that is neither handled, named, nor dropped
on purpose. `test_c2striage.py` keeps the file honest against the vault: a new
live tape carrying a new opcode reddens it until `--write` runs and the opcode
is triaged. The file is a measurement (ids, counts, timings), not expression.

WHAT A ROW CAN AND CANNOT SAY. `first_reply` is the first s2c opcode after the
c2s within the window, on the same connection -- a CORRELATION on a busy wire
(0x001E ticks fall every 20-500 ms, so a tick is the most common "reply" to
anything), never a proof that the server answered. The kick (0x001F -> 0x0075
at 42 ms, 1 of 1) and the henchman add (0x009F -> 0x00B0 at 31-132 ms, 3 of
3) are what a real reply looks like in this column; `--window` narrows it.
`values[0]` of every decoded message is the header word, so a payload starts
at `values[1]` (livewire prints 32799 = 0x801F first for the kick).

`--static` joins the send-site census (`toolkit/clientscan/sendsites.py`,
bare-machine) on the pinned build: the wrapper VA, its caller count, the
nearest assert module. That is a LABEL for where the client sends the opcode
from, not a name -- a name still needs a witness or a read of the caller.

A run over ZERO live connections is refused (exit 2), never printed as a clean
"retail sends nothing". Standard library only; no client, no socket.
"""
import argparse
import ast
import datetime
import json
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
if os.path.dirname(HERE) not in sys.path:
    sys.path.insert(0, os.path.dirname(HERE))
if os.path.join(os.path.dirname(HERE), "schema") not in sys.path:
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))

import livewire                                              # noqa: E402
import codec as codecmod                                     # noqa: E402
# DROPPED_ON_PURPOSE and the dispatch-chain harvester live in the test on
# purpose: the reason a drop is deliberate is a decision on the record, and
# the record is the file that fails when the decision is missing. Importing
# the test runs none of its checks (they are all inside main()).
import test_dispatch as dispatchmod                          # noqa: E402

REPLY_WINDOW = 1.5
# GAME_SMSG 0x001E WORLD_SIMULATION_TICK is the clock (36 % of the s2c corpus,
# overrides.json high): it follows EVERYTHING within 20-500 ms and is never an
# answer, so the census keeps two first-reply columns -- strict, and with the
# clock skipped.
TICK = 0x001E
TABLE_PATH = os.path.join(HERE, "retail_c2s.json")
AUTHSRV_PY = os.path.join(HERE, "authsrv.py")
TOOL = "toolkit/authsrv/c2striage.py"


def _new_row():
    return {"count": 0, "captures": set(), "connections": set(),
            "first_reply": Counter(), "first_non_tick": Counter(),
            "reply_dt": [], "non_tick_dt": []}


def census_connection(merged, rows, meta, window=REPLY_WINDOW, capture="?",
                      conn="?"):
    """Fold ONE decoded connection into `rows`/`meta` (the unit the test drives
    with a synthetic stream). `merged` is livewire's [(t, dir, opcode, values)],
    sorted by (t, c2s-before-s2c on a tie)."""
    # The next s2c at or after each index, precomputed backwards so the walk
    # is linear; one pointer per column.
    n = len(merged)
    nxt = [None] * (n + 1)
    nxt_nt = [None] * (n + 1)
    for i in range(n - 1, -1, -1):
        t, d, op, _v = merged[i]
        nxt[i] = (t, op) if d == "s2c" else nxt[i + 1]
        nxt_nt[i] = (t, op) if d == "s2c" and op != TICK else nxt_nt[i + 1]
    for i, (t, d, op, _v) in enumerate(merged):
        if d != "c2s":
            continue
        r = rows[op]
        r["count"] += 1
        r["captures"].add(capture)
        r["connections"].add(conn)
        meta["c2s_total"] += 1
        for col, dts, ptr in (("first_reply", "reply_dt", nxt),
                              ("first_non_tick", "non_tick_dt", nxt_nt)):
            reply = ptr[i + 1]
            if reply is not None and reply[0] - t <= window:
                r[col][reply[1]] += 1
                r[dts].append(reply[0] - t)
            else:
                r[col][None] += 1


def census(root=None, window=REPLY_WINDOW):
    """({opcode: row}, meta) over every LIVE game connection under `root`.

    row: count, captures (set), connections (set), first_reply (Counter of
    the first s2c opcode within `window`, None when nothing followed),
    first_non_tick (the same with 0x001E skipped), reply_dt / non_tick_dt
    (seconds). meta: live_captures (every origin=LIVE directory), captures
    (those with a game connection), connections, connections_not_ok,
    c2s_total, window.
    """
    rows = defaultdict(_new_row)
    meta = {"live_captures": len(livewire.live_captures(root)),
            "captures": set(), "connections": 0, "connections_not_ok": 0,
            "c2s_total": 0, "window": window}
    for capdir, gf in livewire.live_connections(root):
        conn, merged, ok = livewire.decode_conn(capdir, gf)
        meta["connections"] += 1
        meta["captures"].add(os.path.basename(capdir))
        if not ok:
            meta["connections_not_ok"] += 1
        census_connection(merged, rows, meta, window,
                          capture=os.path.basename(capdir), conn=conn)
    meta["captures"] = len(meta["captures"])
    return dict(rows), meta


def schema_names():
    """{opcode: (name, confidence)} for every GAME_CMSG the codec names."""
    cod = codecmod.Codec()
    out = {}
    for k, m in cod.channels["GAME_CMSG"]["messages"].items():
        if m.get("name"):
            out[int(k)] = (m["name"], m.get("name_confidence") or "?")
    return out


def handled_opcodes(src_path=AUTHSRV_PY):
    """{opcode: constant name} for every GAME_CMSG arm on the dispatch chain,
    read off the syntax tree exactly as test_dispatch.py reads it. None when
    the chain cannot be located -- the caller must refuse, not assume []."""
    with open(src_path, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    arms = dispatchmod.dispatch_arms(tree)
    return None if arms is None else arms["GAME_CMSG"]


def status_of(op, handled, named, dropped):
    """One of handled / dropped / named-only / UNTRIAGED.

    `named-only` (named, unhandled, not dropped) is already red in
    test_dispatch §7; `UNTRIAGED` (unnamed, unhandled, not dropped) is what the
    reverse guard exists for. Both need a decision; only the last was invisible.
    """
    if op in handled:
        return "handled"
    if op in dropped:
        return "dropped"
    if op in named:
        return "named-only"
    return "UNTRIAGED"


def untriaged(seen, handled, named, dropped):
    """The reverse-guard predicate, shared with test_dispatch §10: opcodes
    retail sent that are neither handled, named, nor dropped on purpose."""
    return sorted(op for op in seen
                  if op not in handled and op not in named and op not in dropped)


def static_hints(exe=None):
    """{opcode: [(wrapper_va, module, n_callers, length)]} for the GAME
    channel from the send-site census on `exe` (default: the pinned build).
    None when the census cannot run here (no vaulted client) -- a LABEL for
    where the client sends from, never a name."""
    try:
        cs = os.path.join(os.path.dirname(HERE), "clientscan")
        if cs not in sys.path:
            sys.path.insert(0, cs)
        import sendsites                                     # noqa: E402
        from gwpe import PE                                  # noqa: E402
        exe = exe or sendsites.find_exe()[0]
        rows = sendsites.census(PE(exe))
    except Exception as exc:                                 # noqa: BLE001
        return None, f"no send-site census here ({exc})"
    out = defaultdict(list)
    for r in rows:
        if r.get("channel") == "game" and r.get("opcode") is not None:
            out[r["opcode"]].append((r["wrapper_va"], r["module"],
                                     len(r["callers"]), r["length"]))
    return dict(out), os.path.basename(os.path.dirname(exe))


def _p50(xs):
    if not xs:
        return None
    s = sorted(xs)
    return s[len(s) // 2]


def table(rows, meta, handled, named, dropped):
    """The census as a JSON-ready dict (what --write commits)."""
    def counter_json(c):
        return {("none" if k is None else "0x%04X" % k): v
                for k, v in sorted(c.items(),
                                   key=lambda kv: (-kv[1], kv[0] is None,
                                                   kv[0] or 0))}

    ops = {}
    for op in sorted(rows):
        r = rows[op]
        p50 = _p50(r["reply_dt"])
        p50n = _p50(r["non_tick_dt"])
        ops["0x%04X" % op] = {
            "count": r["count"],
            "captures": len(r["captures"]),
            "connections": len(r["connections"]),
            "first_reply": counter_json(r["first_reply"]),
            "reply_p50_ms": None if p50 is None else round(p50 * 1000, 1),
            "first_non_tick": counter_json(r["first_non_tick"]),
            "non_tick_p50_ms": None if p50n is None else round(p50n * 1000, 1),
            # No status and no name: those are read off the TREE at test time
            # (test_dispatch §10), so the file stays a measurement that a
            # later arm or name cannot make stale.
        }
    return {
        "generated": datetime.date.today().isoformat(),
        "tool": TOOL,
        "what": "every GAME_CMSG opcode on ArenaNet's live wire (origin=LIVE "
                "captures only), with counts and the first s2c within the "
                "window (strict, and with the 0x001E clock skipped) -- a "
                "measurement, regenerated with --write; test_dispatch.py "
                "section 10 reads it, test_c2striage.py checks it against "
                "the vault",
        "window_s": meta["window"],
        "live_captures": meta["live_captures"],
        "captures": meta["captures"],
        "connections": meta["connections"],
        "connections_not_ok": meta["connections_not_ok"],
        "c2s_total": meta["c2s_total"],
        "opcodes": ops,
    }


def load_table(path=TABLE_PATH):
    """The committed census, or None when the file is absent."""
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def table_opcodes(tab):
    """{opcode: row} with int keys, from a loaded table."""
    return {int(k, 16): v for k, v in (tab or {}).get("opcodes", {}).items()}


def _fmt(rows, meta, handled, named, dropped, hints=None, only_untriaged=False):
    lines = []
    lines.append(f"retail c2s triage: {meta['connections']} live game "
                 f"connection(s) over {meta['captures']} capture(s) (of "
                 f"{meta['live_captures']} origin=LIVE), {meta['c2s_total']} "
                 f"c2s message(s), {len(rows)} distinct opcode(s); first-reply "
                 f"window {meta['window']} s; {meta['connections_not_ok']} "
                 f"connection(s) decoded with a receipt shortfall (counted, "
                 f"flagged)")
    lines.append(f"  handled arms {len(handled)}, named {len(named)}, dropped "
                 f"on purpose {len(dropped)}")
    lines.append("  " + f"{'opcode':<8}{'status':<11}{'name':<30}{'n':>6}"
                 f"{'caps':>5}{'conns':>6}  first s2c in window, clock "
                 f"skipped (p50 ms) | strict")

    def top3(c):
        return ", ".join(f"{'none' if k is None else '0x%04X' % k} x{v}"
                         for k, v in c.most_common(3))

    for op in sorted(rows):
        st = status_of(op, handled, named, dropped)
        if only_untriaged and st == "handled":
            continue
        r = rows[op]
        p50n = _p50(r["non_tick_dt"])
        nm = named.get(op, ("-", ""))[0]
        lines.append(f"  0x{op:04X}  {st:<11}{nm:<30}{r['count']:>6}"
                     f"{len(r['captures']):>5}{len(r['connections']):>6}  "
                     f"{top3(r['first_non_tick'])}"
                     + (f" ({p50n * 1000:.0f})" if p50n is not None else "")
                     + f" | {top3(r['first_reply'])}")
        if hints is not None:
            for wva, mod, nc, ln in hints.get(op, []):
                lines.append(f"{'':>10}static: wrapper 0x{wva:08X} {mod} "
                             f"callers {nc} len {ln}")
            if op not in hints:
                lines.append(f"{'':>10}static: NO game-channel send site on "
                             f"the pinned build")
    un = untriaged(rows, handled, named, dropped)
    lines.append(f"  UNTRIAGED (seen on retail, not handled, not named, not "
                 f"dropped on purpose): "
                 + (", ".join("0x%04X" % o for o in un) or "none"))
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=None,
                    help="live-capture root (default: the vault's)")
    ap.add_argument("--window", type=float, default=REPLY_WINDOW,
                    help=f"first-reply window in seconds (default "
                         f"{REPLY_WINDOW})")
    ap.add_argument("--untriaged", action="store_true",
                    help="hide the handled rows")
    ap.add_argument("--static", action="store_true",
                    help="join the send-site census on the pinned build")
    ap.add_argument("--json", action="store_true",
                    help="print the table as JSON instead")
    ap.add_argument("--write", action="store_true",
                    help=f"write the table to {os.path.basename(TABLE_PATH)}")
    args = ap.parse_args(argv)

    handled = handled_opcodes()
    if handled is None:
        print("REFUSED: the game dispatch chain could not be located in "
              "authsrv.py (test_dispatch.game_dispatch_if found not exactly "
              "one); nothing below would be a triage")
        return 2
    named = schema_names()
    dropped = dispatchmod.DROPPED_ON_PURPOSE
    rows, meta = census(args.root, args.window)
    if meta["connections"] == 0 or not rows:
        print(f"REFUSED: {meta['connections']} live connection(s) and "
              f"{len(rows)} c2s opcode(s) under "
              f"{args.root or livewire.captures_root()} -- an empty vault or a "
              f"wrong root, not a clean 'retail sends nothing'")
        return 2
    tab = table(rows, meta, handled, named, dropped)
    if args.write:
        with open(TABLE_PATH, "w", encoding="utf-8") as f:
            json.dump(tab, f, indent=1, sort_keys=False)
            f.write("\n")
        print(f"wrote {TABLE_PATH}: {len(tab['opcodes'])} opcode(s) over "
              f"{meta['connections']} connection(s)")
    if args.json:
        print(json.dumps(tab, indent=1))
        return 0
    hints = None
    if args.static:
        hints, where = static_hints()
        if hints is None:
            print(f"  static: {where}")
        else:
            print(f"  static: send-site census on {where}")
    print(_fmt(rows, meta, handled, named, dropped, hints, args.untriaged))
    return 0


if __name__ == "__main__":
    sys.exit(main())
