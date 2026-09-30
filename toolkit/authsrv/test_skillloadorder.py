"""The load's skill block: the bar 0x00DA BEFORE the character library 0x00DB --
RANGERPRE-S4 (SECONDARY-A), studies/presearing/RANGERPRE.md §4.

    python toolkit/authsrv/test_skillloadorder.py

WHAT THIS PINS, and what each part rests on:

  * §1 RETAIL (OBSERVED, vault-gated; capture 20260929T150923, the Reforged
    pre-Searing Ranger, 11 game connections): on every one the first 0x00DA
    precedes the first 0x00DB, and that 0x00DA is the OWN agent's bar (the
    agent of the connection's first 0x00B7). The design lane's census found the
    same on 126 of 126 live connections carrying both; this section re-reads
    the one capture it cites rather than the corpus. POSITIVE CONTROL: the
    same instrument sees 0x001D BEFORE the pair on :59969 and AFTER it on
    :63359, so "first index" can answer either way and the 11 of 11 is the
    tape's, not the reader's. The literal RETAIL_PLAYER_BLOCK is :53756's
    player block at t=998.208, pinned here against the tape so §2 needs no
    capture.
  * §2 OURS (no capture, but the content overlay's attribute rows): the REAL
    load burst (_handle_request_players, the module's defaults, no hero rig)
    in a town and a field -- the burst's attribute_state refuses without the
    cost rows, so without them §2 declares a skip, the same limit
    test_secondary's drives have, and a bare machine runs §3 alone. The player's
    0x00DA comes before the 0x00DB, 0x001D before both; restricted to the
    opcodes both player blocks carry, ours runs in RETAIL_PLAYER_BLOCK's order;
    and the burst is the revert's with the one 0x00DB moved to right after the
    player's 0x00DA, values included. KNOWN-BAD ARM: under
    --no-retail-skill-order (57e89956's order) the same predicates must FAIL.
  * §3 SOURCE: exactly two 0x00DB sites in _handle_request_players, the
    revert's guarded by `not SKILL_LOAD_RETAIL_ORDER` ahead of the bar's send
    and the default's by `SKILL_LOAD_RETAIL_ORDER` after it; the flag defaults
    True; serverargs declares --no-retail-skill-order and main() flips the
    flag under it.

Nothing here re-pins test_secondary §7: its BASE_OPS literals are 57e89956's
recording, and its three drives pin SKILL_LOAD_RETAIL_ORDER False for that
reason. Floor from the green run (see the ledger line).
"""
import ast
import contextlib
import inspect
import io
import os
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
if os.path.dirname(HERE) not in sys.path:
    sys.path.insert(0, os.path.dirname(HERE))
if os.path.join(os.path.dirname(HERE), "schema") not in sys.path:
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
import checks                                                # noqa: E402
import authsrv                                               # noqa: E402

led = checks.Ledger("the load's skill-block order (RANGERPRE-S4)", floor=18)   # 2026-09-29: 18 from the first green run with the vault (§1 5, §2 10, §3 3); a bare machine runs §3's 3 and declares §1 / §2 skipped -- the load needs the overlay's attribute rows, as test_secondary's drives do

BAR, LIBRARY, ACCOUNT = 0x00DA, 0x00DB, 0x001D
assert authsrv.GAME_SMSG_SKILLBAR_UPDATE == BAR
assert authsrv.GAME_SMSG_UPDATE_UNLOCKED_SKILLS == LIBRARY
assert authsrv.GAME_SMSG_PVP_UPDATE_UNLOCKED_SKILLS == ACCOUNT

TAPE = "20260929T150923"
TAPE_CONNS = 11
WITNESS_CONN = "_53756-"                     # the player block quoted below
CONTROL_BEFORE, CONTROL_AFTER = "_59969-", "_63359-"
# OBSERVED: :53756's player block at t=998.208, from the player's 0x0037 to the
# 0x00EF (§1 pins it against the tape). 0x0041 is the Reforged effect.
RETAIL_PLAYER_BLOCK = [0x0037, 0x00B7, 0x00B6, 0x00DA, 0x009F, 0x009F, 0x009C,
                       0x0041, 0x008B, 0x008A, 0x00B5, 0x00DB, 0x00E9, 0x00EF]
BLOCK_FIRST, BLOCK_LAST = RETAIL_PLAYER_BLOCK[0], RETAIL_PLAYER_BLOCK[-1]


class FakeRec:
    def event(self, kind, **kw):
        pass


_saved = {k: getattr(authsrv, k) for k in
          ("PERSIST", "SPAWN_PROFESSION", "SPAWN_SECONDARY", "OUTPOST",
           "EXPLORABLE", "SKILL_LOAD_RETAIL_ORDER")}
_saved_bar = list(authsrv.SKILLBAR)


def drive_load(*, town, retail):
    """The REAL load burst with the module's defaults (no hero rig), as
    test_secondary's rig "none" drives it. [(op, vals, label)] in send order."""
    for k, v in _saved.items():
        setattr(authsrv, k, v)
    del authsrv.SKILLBAR[:]
    authsrv.SKILLBAR.extend(_saved_bar)
    authsrv.PERSIST = False
    authsrv.SPAWN_PROFESSION, authsrv.SPAWN_SECONDARY = 1, 0
    authsrv.OUTPOST, authsrv.EXPLORABLE = bool(town), not town
    authsrv.SKILL_LOAD_RETAIL_ORDER = retail
    st = {"agents": {}, "char_uuid": "3" * 32, "map_id": 148}
    sent = []

    def send(op, vals, label=None):
        sent.append((op, vals, label))
    with contextlib.redirect_stdout(io.StringIO()):
        authsrv._handle_request_players(send, st, 0, threading.Event(), FakeRec())
    return sent


def player_block(ops, agents_of, player):
    """The player's block: from its 0x0037 through the next 0x00EF."""
    i = next((k for k, op in enumerate(ops)
              if op == BLOCK_FIRST and agents_of[k] == player), None)
    if i is None or BLOCK_LAST not in ops[i:]:
        return None
    return ops[i:ops.index(BLOCK_LAST, i) + 1]


def retail_ordered(block):
    """True when `block`, restricted to the opcodes it shares with retail's
    player block (each once in ours), runs in retail's relative order."""
    common = [op for op in block if op in RETAIL_PLAYER_BLOCK]
    ret = [op for op in RETAIL_PLAYER_BLOCK if op in common]
    return len(common) == len(set(common)) and common == ret


def first(ops, op):
    return ops.index(op) if op in ops else None


def section_retail():
    print(f"\n1. retail: the bar before the library, capture {TAPE}")
    import vaultpath
    try:
        vaultpath.require_dir("captures", "live", why="the load-order witness")
    except (Exception, SystemExit) as exc:                     # noqa: BLE001
        # require_dir raises SystemExit on a bare machine (test_srclint's rule)
        led.skip("1. retail's load order", f"no live captures: {exc} -- 5 checks")
        return
    import livewire
    cap = vaultpath.vault_path("captures", "live", TAPE)
    files = livewire.connections(cap) if os.path.isdir(cap) else []
    decoded = {g: livewire.decode_conn(cap, g) for g in files}
    ok_all = all(ok for _c, _m, ok in decoded.values())
    led.ok(len(files) == TAPE_CONNS and ok_all
           and livewire.capture_origin(cap)[0] == "live",
           f"the live root is present, so {TAPE} must be in it: {TAPE_CONNS} game "
           f"connections, origin live, every one decoding closed (a FAIL, never a skip)",
           f"{len(files)} files, ok {[ok for _c, _m, ok in decoded.values()]}")
    if not files or not ok_all:
        return
    rows = {}
    for g, (_conn, merged, _ok) in decoded.items():
        s2c = [(op, v) for _t, d, op, v in merged if d == "s2c"]
        ops = [op for op, _v in s2c]
        # decoded values carry the header first: the agent is field 1
        own = next((v[1] for op, v in s2c if op == 0x00B7), None)
        i_da, i_db, i_1d = first(ops, BAR), first(ops, LIBRARY), first(ops, ACCOUNT)
        rows[g] = (i_da, i_db, i_1d, s2c[i_da][1][1] if i_da is not None else None, own)
    both = {g: r for g, r in rows.items() if r[0] is not None and r[1] is not None}
    bar_first = [g for g, r in both.items() if r[0] < r[1]]
    led.ok(len(both) == TAPE_CONNS and len(bar_first) == TAPE_CONNS,
           f"the first 0x00DA precedes the first 0x00DB on {len(bar_first)} of "
           f"{len(both)} connections carrying both (OBSERVED; floor N = {TAPE_CONNS})",
           f"{[(g[5:22], r[0], r[1]) for g, r in rows.items()]}")
    led.ok(all(r[3] is not None and r[3] == r[4] for r in both.values()),
           "and that first 0x00DA is the OWN agent's bar (its agent is the "
           "connection's first 0x00B7's), 11 of 11 -- the player's bar, not a hero's",
           f"{[(g[5:22], r[3], r[4]) for g, r in both.items()]}")
    before = [r for g, r in rows.items() if CONTROL_BEFORE in g]
    after = [r for g, r in rows.items() if CONTROL_AFTER in g]
    led.ok(len(before) == 1 and len(after) == 1
           and before[0][2] is not None and before[0][2] < before[0][0]
           and after[0][2] is not None and after[0][2] > after[0][1],
           "POSITIVE CONTROL: the same first-index reader sees 0x001D BEFORE the "
           "pair on :59969 and AFTER it on :63359 -- it can answer either way",
           f"before {before}, after {after}")
    wit = [g for g in files if WITNESS_CONN in g]
    blk = t37 = None
    if len(wit) == 1:
        merged = decoded[wit[0]][1]
        s2c = [(t, op, v) for t, d, op, v in merged if d == "s2c"]
        ops = [op for _t, op, _v in s2c]
        agents_of = [v[1] if len(v) > 1 else None for _t, _op, v in s2c]
        own = next((v[1] for _t, op, v in s2c if op == 0x00B7), None)
        blk = player_block(ops, agents_of, own)
        i37 = next((k for k, op in enumerate(ops) if op == BLOCK_FIRST
                    and agents_of[k] == own), None)
        t37 = round(s2c[i37][0], 3) if i37 is not None else None
    led.ok(blk == RETAIL_PLAYER_BLOCK and t37 == 998.208,
           "RETAIL_PLAYER_BLOCK is :53756's player block at t=998.208, 0x0037 "
           "through 0x00EF, byte for byte in opcodes",
           f"{[hex(o) for o in blk] if blk else blk}")


def section_ours():
    print("\n2. ours: the real load burst, both arms, town and field")
    if not authsrv.agents.WORLD.rows("attribute"):
        # the burst's attribute_state refuses without the cost rows (attribspend)
        led.skip("2. our load burst", "no attribute cost rows in the content "
                 "(clientscan/attribpoints.py --emit-content) -- 10 checks")
        return
    for town in (True, False):
        where = "town" if town else "field"
        on = drive_load(town=town, retail=True)
        off = drive_load(town=town, retail=False)
        P = authsrv.PLAYER_AGENT_ID

        def shape(sent):
            ops = [op for op, _v, _l in sent]
            ag = [v[0] if isinstance(v, list) and v and not isinstance(v[0], list)
                  else None for _op, v, _l in sent]
            bars = [k for k, op in enumerate(ops) if op == BAR and ag[k] == P]
            libs = [k for k, op in enumerate(ops) if op == LIBRARY]
            return ops, ag, bars, libs

        ops, ag, bars, libs = shape(on)
        led.ok(len(bars) == 1 and len(libs) == 1 and bars[0] < libs[0],
               f"[{where}] one player 0x00DA and one 0x00DB, the bar FIRST (retail, "
               f"126 of 126)", f"bar at {bars}, library at {libs}")
        i1d = first(ops, ACCOUNT)
        led.ok(i1d is not None and bars and i1d < bars[0],
               f"[{where}] 0x001D still ahead of the pair (it does not take part in "
               f"the order -- section 1's control)", f"0x001D at {i1d}")
        blk = player_block(ops, ag, P)
        led.ok(blk is not None and retail_ordered(blk),
               f"[{where}] restricted to the opcodes both player blocks carry, ours "
               f"runs in retail's order (:53756 t=998.208)",
               f"{[hex(o) for o in blk] if blk else blk}")
        o_ops, o_ag, o_bars, o_libs = shape(off)
        moved = None
        if len(o_bars) == 1 and len(o_libs) == 1:
            moved = [(op, v) for op, v, _l in off]
            lib = moved.pop(o_libs[0])
            i_bar = o_bars[0] - (1 if o_libs[0] < o_bars[0] else 0)
            moved.insert(i_bar + 1, lib)
        led.ok(moved is not None and moved == [(op, v) for op, v, _l in on],
               f"[{where}] the burst is the revert's with its one 0x00DB moved to "
               f"right after the player's 0x00DA -- values included, nothing else moves",
               f"{len(on)} sends vs {len(off)}")
        o_blk = player_block(o_ops, o_ag, P)
        led.ok(len(o_bars) == 1 and len(o_libs) == 1 and o_libs[0] < o_bars[0]
               and o_blk is not None and not retail_ordered(o_blk),
               f"[{where}] KNOWN-BAD ARM (--no-retail-skill-order, 57e89956's order): "
               f"0x00DB before the bar, and the retail-order predicate REJECTS it",
               f"library at {o_libs}, bar at {o_bars}")


def _guard_of(fn_tree, call_pred):
    """[(lineno, guard)] for each call matching call_pred inside fn_tree, where
    guard is 'flag', 'not flag' or None (unguarded / another test)."""
    out = []

    def walk(node, guard):
        for child in ast.iter_child_nodes(node):
            g = guard
            if isinstance(node, ast.If) and child in node.body:
                t = node.test
                if isinstance(t, ast.Name) and t.id == "SKILL_LOAD_RETAIL_ORDER":
                    g = "flag"
                elif (isinstance(t, ast.UnaryOp) and isinstance(t.op, ast.Not)
                      and isinstance(t.operand, ast.Name)
                      and t.operand.id == "SKILL_LOAD_RETAIL_ORDER"):
                    g = "not flag"
                else:
                    g = None
            if isinstance(child, ast.Call) and call_pred(child):
                out.append((child.lineno, g))
            walk(child, g)
    walk(fn_tree, None)
    return sorted(out)


def _sends(name):
    def pred(call):
        return (isinstance(call.func, ast.Name) and call.func.id == "send"
                and call.args and isinstance(call.args[0], ast.Name)
                and call.args[0].id == name)
    return pred


def section_source():
    print("\n3. source: the two sites, the flag, the CLI")
    fn = ast.parse(inspect.getsource(authsrv._handle_request_players).lstrip())
    libs = _guard_of(fn, _sends("GAME_SMSG_UPDATE_UNLOCKED_SKILLS"))
    bars = _guard_of(fn, _sends("GAME_SMSG_SKILLBAR_UPDATE"))
    bar_line = bars[0][0] if len(bars) == 1 else None
    led.ok(len(libs) == 2 and bar_line is not None
           and libs[0][1] == "not flag" and libs[0][0] < bar_line
           and libs[1][1] == "flag" and libs[1][0] > bar_line,
           "exactly two 0x00DB sites in _handle_request_players: the revert's under "
           "`not SKILL_LOAD_RETAIL_ORDER` ahead of the bar's send, the default's under "
           "`SKILL_LOAD_RETAIL_ORDER` after it", f"0x00DB {libs}, bar {bars}")
    mod = ast.parse(open(authsrv.__file__, encoding="utf-8").read())
    top = [n.value.value for n in mod.body if isinstance(n, ast.Assign)
           and any(isinstance(t, ast.Name) and t.id == "SKILL_LOAD_RETAIL_ORDER"
                   for t in n.targets) and isinstance(n.value, ast.Constant)]
    led.ok(top == [True],
           "SKILL_LOAD_RETAIL_ORDER defaults True at module level (the retail order "
           "is what a session gets by not choosing)", f"{top}")
    import serverargs
    ap = serverargs.build_parser(
        doc="x", GAME_SRV_HOST=authsrv.GAME_SRV_HOST, GAME_SRV_PORT=authsrv.GAME_SRV_PORT,
        HOST_FIELD_ENCODING=authsrv.HOST_FIELD_ENCODING, TEST_SKILLBAR=authsrv.TEST_SKILLBAR,
        GRANT_MIN_INTERVAL=authsrv.GRANT_MIN_INTERVAL, PROF_WARRIOR=authsrv.PROF_WARRIOR,
        VAULT_DEFAULT=authsrv.VAULT_DEFAULT)
    a0, a1 = ap.parse_args([]), ap.parse_args(["--no-retail-skill-order"])
    main_fn = next(n for n in mod.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    flips = []
    for node in ast.walk(main_fn):
        if (isinstance(node, ast.If) and isinstance(node.test, ast.Attribute)
                and node.test.attr == "no_retail_skill_order"):
            flips += [s for s in node.body if isinstance(s, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == "SKILL_LOAD_RETAIL_ORDER"
                              for t in s.targets)
                      and isinstance(s.value, ast.Constant) and s.value.value is False]
            flips += [s for s in node.body if isinstance(s, ast.Global)
                      and "SKILL_LOAD_RETAIL_ORDER" in s.names]
    led.ok(a0.no_retail_skill_order is False and a1.no_retail_skill_order is True
           and len(flips) == 2,
           "--no-retail-skill-order parses (default off) and main() sets the global "
           "SKILL_LOAD_RETAIL_ORDER = False under it", f"{len(flips)} of 2 statements")


try:
    section_retail()
    section_ours()
    section_source()
finally:
    for k, v in _saved.items():
        setattr(authsrv, k, v)
    del authsrv.SKILLBAR[:]
    authsrv.SKILLBAR.extend(_saved_bar)

sys.exit(led.verdict())
