"""test_animaltoken -- a charmable animal stands passive under 'anim', and the player's
first landed hit turns it to 'anin' in retail's order, then it fights back (RANGERPRE-S12,
the ANIMAL item, 2026-09-30; studies/presearing/RANGERPRE.md).

    python toolkit/authsrv/test_animaltoken.py

WHAT RETAIL SENDS (OBSERVED, n = 1). Capture 20260929T150923, connection :55934 (build
38888, the player agent 31): definition 1343 is declared by 0x0056 at t=503.515 and agent
161 is created carrying team token 'anim'. No attack start names it before the hit (the
design lane put the player within ~258 u at closest, from move destinations -- approximate);
the client selects it and presses an attack skill at it. At
t=565.0302 the arrow lands and every message naming 161, with the tick between, is
RETAIL_BURST: 0x009F [65, 161, 0], 0x009B (its name), 0x009F [36, 161, 1], 0x009F [42,
161, 80], 0x00A3 [16, 161, 31, -0.3125], 0x001E, 0x002F [161, 'anin'], 0x002B [161, 1.0,
1], 0x002A [161, <the player's point>, 0, 0, 31] -- the only 0x002F on the connection.
Then 0x0035 [161, 2.0, 1.0] and an attack start every 2.0 s; the client's 0x00C1 [0, 0]
at 565.1515, and its re-select 0x00C1 [161, 0] at the same instant, draw no reply. A
'mon1' body's first hit carries none of 65 / 0x009B / 36 / 0x002F (agents 48 and 215).
Ours could not spawn an 'anim' body at all.

  * 0 CONTENT (bare machine): npc.animal_1343 -- definition 1343 as npcdefs compiles
    it -- builds retail's 0x0056 fields, and spawn.animal_probe names it as "animal".
  * 1 RETAIL (vault-gated; the live root absent is a declared skip, present without
    this capture a FAIL): the facts above from the bytes, npcdefs re-run and equal to
    the tracked row field for field, and our 0x0056 encoded equal to retail's.
  * 2 OURS (bare machine): the real spawn_population over the tracked row plus a
    hostile control in one table, then the real hit_enemy, enemy_move_tick and
    enemy_attack_tick around one simulated 0x001E. The projection of what names the
    body is RETAIL_BURST EXACTLY, values included; a second hit turns nothing; it
    swings on a 2.0 s interval; the player's armour-ignoring word turns it the same way;
    and a body IN REACH at the hit (a melee player) does not swing until it has turned
    (RECONSTRUCTION: retail's only witness is a ranged hit).
  * 3 CONTROLS: --no-animal-token-flip (the known-bad arm) projects [9F/42, A3/16,
    2B, 2A] and the comparator says so; a passive 'hostile' row gets none of the
    turn; a hostile's hit provokes nothing; an unhit turn (provoke alone) sends its
    whole burst before its first chase order; --no-passive-hostiles turns nothing; a
    body killed by its first hit is not turned as a corpse.
  * 4 LOAD GUARD: an unknown allegiance name is refused at area_population, naming
    the row; "animal" is accepted.
  * 5 SOURCE: the flag's module default, parser and main() flip; the turn called
    first in both enemy ticks; the world tick counting 0x001E before it sends one;
    the prelude inside the declare helper ahead of its 42; the 0x00C1 arm sends
    nothing.

Floor from the green run (the ledger line).
"""
import ast
import contextlib
import inspect
import io
import os
import statistics
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
PARENT = os.path.dirname(HERE)
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)
if os.path.join(PARENT, "schema") not in sys.path:
    sys.path.insert(0, os.path.join(PARENT, "schema"))

import checks                                                  # noqa: E402
import agents                                                  # noqa: E402
import authsrv                                                 # noqa: E402
import content                                                 # noqa: E402
import vaultpath                                               # noqa: E402

# Floor from the green run of 2026-09-30 on a machine with NO captures (RURIK_VAULT at an
# empty directory; section 1 a declared skip): 23. With the vault: 33 (section 1's 10).
# (22 / 32 until check 2j, the in-reach turn, was added in review.)
LEDGER = checks.Ledger("charmable animal turn (RANGERPRE-S12)", floor=23)
check = checks.adopt(LEDGER)

PLAYER = authsrv.PLAYER_AGENT_ID
ANIM, ANIN, MONS = agents.TOKEN_ANIMAL, agents.TOKEN_ANIMAL_PROVOKED, agents.ALLEGIANCE_HOSTILE
assert (ANIM, ANIN) == (0x616E696D, 0x616E696E)
OP_DEF, OP_CREATE, OP_INT, OP_NAME, OP_WORD = 0x0056, 0x0020, 0x009F, 0x009B, 0x00A3
OP_TICK, OP_TURN, OP_SPEED, OP_FOLLOW, OP_INTT, OP_ATKSPD = (0x001E, 0x002F, 0x002B,
                                                             0x002A, 0x00A0, 0x0035)
OP_ROTATE = 0x002E
assert (authsrv.GAME_SMSG_AGENT_UPDATE_ALLEGIANCE, authsrv.GAME_SMSG_AGENT_SET_NAME,
        authsrv.GAME_SMSG_WORLD_SIMULATION_TICK,
        authsrv.GAME_SMSG_AGENT_UPDATE_ROTATION) == (OP_TURN, OP_NAME, OP_TICK, OP_ROTATE)

# ---- retail's literals (OBSERVED; section 1 re-derives every one from the bytes) -------
STAMP = "20260929T150923"
CONN = ":55934->"
OBSERVER = 31
ANIMAL = 161
DEFINITION = 1343
MODEL_WORD = 0x2000053F                        # 536872255 = 0x20000000 | 1343
DEF_T, TURN_T, SPEED_T = 503.515, 565.0302, 565.6669
# c2s 0x00C1 [0, 0] and the re-select 0x00C1 [161, 0] at one instant, 121 ms after the turn
CANCEL_T = 565.1515
ARROW_BITS = 3198156800                        # -0.3125 = 25 of 80
MON1_FIRST_HITS = ((48, 414.3195), (215, 516.9892))
RETAIL_BURST = ["9F/65", "9B", "9F/36", "9F/42", "A3/16", "1E", "2F", "2B", "2A"]
# What the fix-disabled arm sends (--no-animal-token-flip): the maximum, the word, and
# the chase under the create token on the hit's own tick -- no prelude, no turn, no
# tick between (MONSTERAI-J's provoked chase, as for any passive hostile).
FLAG_OFF_BURST = ["9F/42", "A3/16", "2B", "2A"]
ENC_1343 = [3851, 49443, 34856, 21815]


def token(op, v, aid):
    """The name of message (op, [op, *fields]) in the retail vocabulary when it names
    agent `aid`; "1E" for a simulation tick; None otherwise."""
    if op == OP_TICK:
        return "1E"
    f = v[1:]
    if op == OP_INT and len(f) >= 2 and f[1] == aid:
        return f"9F/{f[0]}"
    if op == OP_WORD and len(f) >= 2 and f[1] == aid:
        return f"A3/{f[0]}"
    if op == OP_INTT and len(f) >= 3 and aid in (f[1], f[2]):
        return f"A0/{f[0]}"
    if (op in (OP_NAME, OP_TURN, OP_SPEED, OP_FOLLOW, OP_ATKSPD, OP_ROTATE)
            and f and f[0] == aid):
        return {OP_NAME: "9B", OP_TURN: "2F", OP_SPEED: "2B", OP_FOLLOW: "2A",
                OP_ATKSPD: "35", OP_ROTATE: "2E"}[op]
    if f and f[0] == aid:
        return f"{op:04X}"
    return None


def projection(msgs, aid):
    """[(token, fields)] from the first 9F/65 naming `aid` through the first 2A naming
    it: every message naming it, and every 0x001E between. [] when there is no 9F/65 --
    so a stream that never turns projects from its first message naming the body."""
    toks = [(token(op, v, aid), v[1:]) for op, v in msgs]
    start = next((i for i, (t, _f) in enumerate(toks) if t == "9F/65"), None)
    if start is None:
        start = next((i for i, (t, _f) in enumerate(toks) if t not in (None, "1E")), None)
    if start is None:
        return []
    out = []
    for t, f in toks[start:]:
        if t is None:
            continue
        out.append((t, f))
        if t == "2A":
            break
    return out


def names(proj):
    return [t for t, _f in proj]


def fourcc(x):
    return int(x).to_bytes(4, "big").decode("latin1")


# ---------------------------------------------------------------------------------------
def section_content():
    print("\n0. content: the tracked template and the tracked spawn row")
    world = content.load(vault_dir="")
    tpl = dict(world.get("npc", "animal_1343"))
    row = world.get("spawn", "animal_probe")
    built = agents.npc_properties(DEFINITION, dict(tpl, enc_name=agents._encstring(tpl["enc_name"])))
    check(built == [DEFINITION, 16689, 0, 0x64000000, 0, 9, 2, 1,
                    agents._encstring(ENC_1343)] and tpl.get("max_health") == 80
          and tpl.get("attack_interval") == 2.0 and "model_id" not in tpl
          and "name" not in tpl,
          "0a. npc.animal_1343 (tracked, no vault) builds retail's 0x0056 fields -- 1343, "
          "file 16689, scale 0x64000000, flags 9, profession 2, level 1, its four name "
          "words -- with max 80 and a 2.0 s attack, no model_id and no name", built)
    check(dict(row) == {"area": "animal_probe", "npc": "animal_1343", "agent_id": 96,
                        "definition": DEFINITION, "offset_x": 400.0, "offset_y": 0.0,
                        "allegiance": "animal", "max_health": 80, "attack_speed": 2.0,
                        "skills": [], "enabled": True}
          and row.provenance.get("source") == "invented",
          "0b. spawn.animal_probe (tracked): allegiance 'animal', 400 u east, agent 96 on "
          "retail's definition 1343, max 80, attack 2.0 s, no skills; source invented",
          dict(row))


# ---------------------------------------------------------------------------------------
def section_retail():
    print("\n1. retail's bytes: the create, the turn, its order, the fight, the rows")
    try:
        vaultpath.require_dir("captures", "live", why="the charmable-animal witness")
    except SystemExit as exc:
        LEDGER.skip("1. retail's bytes", str(exc).splitlines()[0])
        return
    import bufflog
    import cmsgstream
    import deepwoundjoin
    import npcdefs
    import spellhitjoin
    import tape
    codec = bufflog.Codec()
    cap = vaultpath.require_dir("captures", "live", STAMP, why="the Reforged capture")
    conns = [r["connection"] for r in tape.channel_files(cap) if CONN in r["connection"]]
    check(len(conns) == 1, f"fixture: exactly one connection matches {CONN!r}", conns)
    if len(conns) != 1:
        return
    conn = conns[0]
    seq = deepwoundjoin.sequence(cap, conn, codec)
    check(tape.client_version(cap, conn)["build"] == 38888
          and spellhitjoin.observer_of(seq, [])[0] == OBSERVER,
          f"fixture: {STAMP} {conn} is build 38888 and its observer is agent {OBSERVER}")

    # 1a. the declaration, and ours encodes to its bytes
    decl = [(round(t, 3), v) for _i, t, op, v in seq if op == OP_DEF and v[1] == DEFINITION]
    tpl = agents.npc_template("animal_1343")
    ours = codec.encode("GAME_SMSG", OP_DEF, agents.npc_properties(DEFINITION, tpl))
    check(len(decl) == 1 and abs(decl[0][0] - DEF_T) <= 0.001
          and codec.encode("GAME_SMSG", OP_DEF, decl[0][1][1:]) == ours
          and not any(op == 0x0057 and v[1] == DEFINITION for _i, _t, op, v in seq),
          "1a. 0x0056 declares 1343 once (t=503.515), no 0x0057, and OUR 0x0056 from the "
          "tracked row encodes to its bytes, byte for byte",
          [(t, v[1:9]) for t, v in decl])

    # 1b. the create: slot 1343, 'anim'
    creates = [(round(t, 4), v[2], v[12]) for _i, t, op, v in seq
               if op == OP_CREATE and v[1] == ANIMAL]
    check(creates and all(w == MODEL_WORD and tok == ANIM for _t, w, tok in creates),
          "1b. agent 161's create carries model word 0x2000053F (1343) and team token 'anim'",
          [(t, hex(w), fourcc(tok)) for t, w, tok in creates])

    # 1c. the only 0x002F on the connection
    turns = [(round(t, 4), v[1:]) for _i, t, op, v in seq if op == OP_TURN]
    check(len(turns) == 1 and abs(turns[0][0] - TURN_T) <= 0.001
          and turns[0][1] == [ANIMAL, ANIN],
          "1c. exactly one 0x002F on the connection: [161, 'anin'] at t=565.0302",
          [(t, v[0], fourcc(v[1])) for t, v in turns])

    # 1d. the order around the 42, values included
    inst = [(op, v) for _i, t, op, v in seq if abs(t - TURN_T) <= 0.001]
    proj = projection(inst, ANIMAL)
    vals = dict(proj)
    name_at_create = [v[2] for _i, t, op, v in seq if op == OP_NAME and v[1] == ANIMAL
                      and t < TURN_T - 1.0]
    check(names(proj) == RETAIL_BURST
          and vals["9F/65"] == [65, ANIMAL, 0] and vals["9F/36"] == [36, ANIMAL, 1]
          and vals["9F/42"] == [42, ANIMAL, 80]
          and vals["A3/16"] == [16, ANIMAL, OBSERVER, ARROW_BITS]
          and vals["9B"][1] == agents._encstring(ENC_1343) == decl[0][1][9]
          and name_at_create[:1] == [vals["9B"][1]]
          and vals["2F"] == [ANIMAL, ANIN] and vals["2B"] == [ANIMAL, 1.0, 1]
          and vals["2A"][4] == OBSERVER,
          "1d. what names 161 at t=565.0302, the tick included, is RETAIL_BURST -- 65 = 0, "
          "its name (the 0x0056's words, the create batch's 0x009B), level 1, max 80, the "
          "arrow 25/80, a 0x001E, then 'anin', rate 1.0 and the follow naming the player",
          names(proj))

    # 1e. passive before, fights after on a 2.0 s interval
    starts = [round(t, 4) for _i, t, op, v in seq
              if op == OP_INTT and v[1] == 4 and v[2] == ANIMAL]
    before = [t for t in starts if t < TURN_T]
    after = [t for t in starts if t > TURN_T]
    gaps = [round(b - a, 3) for a, b in zip(after, after[1:])]
    rate = [(round(t, 4), v[1:]) for _i, t, op, v in seq if op == OP_ATKSPD and v[1] == ANIMAL]
    check(not before and len(after) >= 5 and all(1.9 <= g <= 2.2 for g in gaps)
          and abs(statistics.median(gaps) - 2.0) <= 0.05
          and len(rate) >= 1 and abs(rate[0][0] - SPEED_T) <= 0.001
          and rate[0][1] == [ANIMAL, 0x40000000, 0x3F800000],
          "1e. no attack start from 161 before the turn; after it 0x0035 [161, 2.0, 1.0] "
          "(t=565.6669) and a start every 2.0 s (median gap)", (before, after, gaps))

    # 1f. the paired negative: a 'mon1' body's first landed hit turns nothing
    bad = []
    for aid, t0 in MON1_FIRST_HITS:
        got = names(projection([(op, v) for _i, t, op, v in seq if abs(t - t0) <= 0.001], aid))
        if "9F/42" not in got or "A3/16" not in got or {"9F/65", "9B", "9F/36", "2F"} & set(got):
            bad.append((aid, got))
    check(not bad,
          "1f. the paired negative: agents 48 (414.3195) and 215 (516.9892), 'mon1', carry "
          "the 42 and the word on their first hit and none of 65 / 0x009B / 36 / 0x002F", bad)

    # 1g. cancel-target on it draws no reply. The cancel is not alone: the client
    # re-selects 161 at the same instant (0x00C1 [0, 0] then [161, 0]), 121 ms after
    # the 0x002F -- OBSERVED n = 1; whether the turn caused it is UNVERIFIED.
    c2s = [(t, op, v) for t, c, op, v in cmsgstream.timed(STAMP, "c2s") if CONN in c]
    s2c = [(t, op, v) for t, c, op, v in cmsgstream.timed(STAMP, "s2c") if CONN in c]
    cancel = [t for t, op, v in c2s if op == 0x00C1 and v[1:] == [0, 0]
              and abs(t - CANCEL_T) <= 0.001]
    reselect = [t for t, op, v in c2s if op == 0x00C1 and v[1:] == [ANIMAL, 0]
                and abs(t - CANCEL_T) <= 0.001]
    replies = [(round(t2 - cancel[0], 3), op2) for t2, op2, _v in s2c
               if cancel and cancel[0] < t2 <= cancel[0] + 0.300 and op2 != OP_TICK]
    pressed = [v[1:] for t, op, v in c2s if op == 0x0027 and v[3] == ANIMAL and t < TURN_T]
    check(len(cancel) == 1 and len(reselect) == 1 and replies == [] and pressed,
          "1g. the client's 0x00C1 [0, 0] at 565.1515 (after the turn), with its re-select "
          "[161, 0] at the same instant, draws NO s2c within 300 ms but ticks; and before "
          "the turn it pressed an attack skill at the 'anim' body (0x0027 naming 161) -- so "
          "'anim' is attackable", (cancel, reselect, replies, pressed[:2]))

    # 1h. the tracked row IS the extractor's
    defs, _iv = npcdefs.read([cap])
    want = defs[DEFINITION].row()
    tracked = content.load(vault_dir="").get("npc", "animal_1343")
    prov = tracked.provenance
    check(dict(tracked) == want and prov.get("build") == npcdefs.capture_build(cap)
          and prov.get("mode") == npcdefs.capture_mode(cap) == "reforged"
          and prov.get("extractor") == "toolkit/authsrv/npcdefs.py"
          and prov.get("capture") == STAMP and sorted(defs[DEFINITION].tokens) == ["anim"],
          "1h. npc.animal_1343 IS npcdefs.read's row for 1343 over this capture, field for "
          "field (its every create 'anim'), and names the capture, its build, reforged and "
          "npcdefs.py", (dict(tracked), want))


# ---------------------------------------------------------------------------------------
class OneTable:
    """agents.WORLD with the spawn table replaced; every other kind is the real store's."""

    def __init__(self, spawn, real):
        self._spawn, self._real = spawn, real

    def rows(self, kind):
        return dict(self._spawn) if kind == "spawn" else self._real.rows(kind)

    def get(self, kind, key):
        return self._spawn[key] if kind == "spawn" else self._real.get(kind, key)

    def __getattr__(self, name):
        return getattr(self._real, name)


ANIMAL_ID, CONTROL_ID, PASSIVE_ID = 96, 20, 21


def table():
    tracked = dict(content.load(vault_dir="").get("spawn", "animal_probe"))
    return {
        "animal_probe": tracked,
        # the paired control: a hostile row that says nothing, 900 u west
        "control": {"area": "animal_probe", "npc": "hatcher", "agent_id": CONTROL_ID,
                    "definition": 5, "offset_x": -900.0, "offset_y": 0.0,
                    "allegiance": "hostile", "max_health": 100, "enabled": True},
        # a PASSIVE hostile (retail's 'mon1' shape for a first hit), 600 u north
        "passive": {"area": "animal_probe", "npc": "hatcher", "agent_id": PASSIVE_ID,
                    "definition": 5, "offset_x": 0.0, "offset_y": 600.0,
                    "allegiance": "hostile", "passive": True, "attacks_back": True,
                    "max_health": 100, "enabled": True},
    }


def fresh():
    """spawn_population over table(); returns (state, sent, send)."""
    sent = []

    def send(op, vals, label="", **_kw):
        sent.append((op, [op] + list(vals)))
    real = agents.WORLD
    st = {"agents": {}, "pos": (0.0, 0.0), "pathmap": None}
    try:
        agents.WORLD = OneTable(table(), real)
        with contextlib.redirect_stdout(io.StringIO()):
            authsrv.spawn_population(send, st, (0.0, 0.0, 0), 1, area="animal_probe")
    finally:
        agents.WORLD = real
    return st, sent, send


def ticks(st, send, quiet=True):
    """One world tick's move and swing passes, as world_tick runs them."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out) if quiet else contextlib.nullcontext():
        for a in st["agents"].values():
            a["moved_at"] = time.time() - 0.05
        authsrv.enemy_move_tick(send, st, 1)
        authsrv.enemy_attack_tick(send, st, 1)
    return out.getvalue()


def sim_tick(st, sent):
    """What world_tick does before its passes: count the tick, send the 0x001E."""
    st["sim_ticks"] = st.get("sim_ticks", 0) + 1
    sent.append((OP_TICK, [OP_TICK, 50]))


def hit_and_turn(st, sent, send, aid=ANIMAL_ID):
    """The player's arrow on `aid` (25 points), the SAME tick's passes, one 0x001E, the
    next tick's passes. Returns (the projection, what the same-tick passes sent, log)."""
    st["agents"][aid]["last_hit"] = 0.0
    mark = len(sent)
    with contextlib.redirect_stdout(io.StringIO()):
        authsrv.hit_enemy(send, st, aid, 1, exact=25.0, swing=False)
    hit_end = len(sent)
    ticks(st, send)
    same_tick = [token(op, v, aid) for op, v in sent[hit_end:]]
    sim_tick(st, sent)
    log = ticks(st, send)
    return projection(sent[mark:], aid), [t for t in same_tick if t], log


def section_ours():
    print("\n2. ours: the real spawn, hit and ticks around one 0x001E")
    st, sent, send = fresh()
    a, b = st["agents"][ANIMAL_ID], st["agents"][CONTROL_ID]
    check(a["allegiance"] == MONS and a.get("team_token") == ANIM
          and a.get("token_on_provoke") == ANIN and a["passive"] is True
          and a["attacks_back"] is True and a["attack_speed"] == 2.0
          and b.get("team_token") is None and b["passive"] is False
          and b["attacks_back"] is False,
          "2a. the 'animal' row is the FOE CLASS 'mons' with team token 'anim' (turning to "
          "'anin'), passive and attacking back by default, 2.0 s; the hostile row that says "
          "nothing has no team token and is neither",
          ({k: a.get(k) for k in ("allegiance", "team_token", "passive", "attacks_back")},
           {k: b.get(k) for k in ("team_token", "passive", "attacks_back")}))
    creates = {v[1]: v for op, v in sent if op == OP_CREATE}
    rates = {v[1]: v[2:] for op, v in sent if op == OP_ATKSPD}
    check(creates[ANIMAL_ID][12] == ANIM and creates[ANIMAL_ID][2] == MODEL_WORD
          and creates[CONTROL_ID][12] == MONS
          and rates[ANIMAL_ID] == [0x40000000, 0x3F800000],
          "2b. its 0x0020 carries 'anim' in field 12 and retail's model word 0x2000053F; "
          "the control's carries 'mons'; its 0x0035 is retail's [2.0, 1.0]",
          (fourcc(creates[ANIMAL_ID][12]), hex(creates[ANIMAL_ID][2]),
           fourcc(creates[CONTROL_ID][12]), rates.get(ANIMAL_ID)))

    sent.clear()
    tid = authsrv.hostile_target(st, ANIMAL_ID, a, time.time())
    ticks(st, send)
    ticks(st, send)
    check(tid is None and not [t for t in (token(op, v, ANIMAL_ID) for op, v in sent) if t],
          "2c. unhit with the player 400 u off: it picks nobody, and two ticks' move and "
          "swing passes send nothing naming it", sent)

    sent.clear()
    proj, same_tick, log = hit_and_turn(st, sent, send)
    vals = dict(proj)
    check(names(proj) == RETAIL_BURST,
          "2d. THE TURN, IN RETAIL'S ORDER: what names the body from the prelude to its "
          "first follow, the tick included, is RETAIL_BURST exactly", names(proj))
    check(vals.get("9F/65") == [65, ANIMAL_ID, 0]
          and vals.get("9B") == [ANIMAL_ID, agents._encstring(ENC_1343)]
          and vals.get("9F/36") == [36, ANIMAL_ID, 1]
          and vals.get("9F/42") == [42, ANIMAL_ID, 80]
          and vals.get("A3/16") == [16, ANIMAL_ID, PLAYER, ARROW_BITS]
          and vals.get("2F") == [ANIMAL_ID, ANIN] and vals.get("2B") == [ANIMAL_ID, 1.0, 1]
          and (vals.get("2A") or [None] * 5)[4] == PLAYER
          and a.get("team_token") == ANIN and a.get("token_due") is None,
          "2e. and retail's values: 65 = 0, the template's name words, level 1, max 80, "
          "25/80 as retail's bits, 'anin', rate 1.0, the follow naming the player; the "
          "row now carries 'anin'", proj)
    check(same_tick == [] and "[ANIMAL-TURN] agent 96" in log and "[RANGERPRE-S12]" in log,
          "2f. the hit's OWN tick sends nothing more naming it (the turn waits for the "
          "0x001E), and the turn prints its [ANIMAL-TURN] line", (same_tick, log[:200]))

    sent.clear()
    mark = len(sent)
    a["last_hit"] = 0.0                  # the player's own interval gate, not the turn's
    with contextlib.redirect_stdout(io.StringIO()):
        authsrv.hit_enemy(send, st, ANIMAL_ID, 1, exact=5.0, swing=False)
    sim_tick(st, sent)
    ticks(st, send)
    got = [t for t in (token(op, v, ANIMAL_ID) for op, v in sent[mark:]) if t]
    check("A3/16" in got and not {"2F", "9F/65", "9B", "9F/36", "9F/42"} & set(got),
          "2g. a second hit sends its word and none of 65 / 0x009B / 36 / 42 / 0x002F", got)

    # 2h. it fights back on its own 2.0 s interval
    a["pos"], a["follow"], a["moving"] = (60.0, 0.0), None, False
    a.pop("swing_owed_at", None)
    sent.clear()
    ticks(st, send)
    first = [v for op, v in sent if op == OP_INTT and v[1:3] == [4, ANIMAL_ID]]
    now = time.time()
    a["swing_lands_at"] = None
    a["last_swing"] = now - 1.9
    sent.clear()
    with contextlib.redirect_stdout(io.StringIO()):
        authsrv.enemy_attack_tick(send, st, 1)
    early = [v for op, v in sent if op == OP_INTT and v[1:3] == [4, ANIMAL_ID]]
    a["swing_lands_at"] = None
    a["last_swing"] = time.time() - 2.05
    sent.clear()
    with contextlib.redirect_stdout(io.StringIO()):
        authsrv.enemy_attack_tick(send, st, 1)
    due = [v for op, v in sent if op == OP_INTT and v[1:3] == [4, ANIMAL_ID]]
    check(first == [[OP_INTT, 4, ANIMAL_ID, PLAYER, 0]] and early == []
          and due == [[OP_INTT, 4, ANIMAL_ID, PLAYER, 0]],
          "2h. in reach it swings at the player at once, not again 1.9 s later, and again "
          "at 2.05 s -- the row's 2.0 s interval (retail: a start every 2.0 s)",
          (first, early, due))

    # 2i. the same turn from the player's ARMOUR-IGNORING word (a skill's adjacent damage):
    # the provoke there now precedes the declare call, so the prelude still sits right
    # before the 42 (RECONSTRUCTION for this site -- retail's witness is an arrow)
    st2, sent2, send2 = fresh()
    sent2.clear()
    with contextlib.redirect_stdout(io.StringIO()):
        authsrv.armour_ignoring_damage(send2, st2, ANIMAL_ID, PLAYER, 10.0, 1,
                                       "the player's adjacent damage")
    ticks(st2, send2)
    sim_tick(st2, sent2)
    ticks(st2, send2)
    got = names(projection(sent2, ANIMAL_ID))
    check(got == ["9F/65", "9B", "9F/36", "9F/42", "A3/55", "1E", "2F", "2B", "2A"],
          "2i. the player's armour-ignoring word provokes it the same way: the prelude "
          "right before the 42 and the [55] word, the turn after the tick", got)

    # 2j. IN REACH at the hit -- a melee player standing next to it. The body stands
    # 60 u off (inside enemy_reach()'s 92 u), so the hit's own tick would
    # swing at once but for enemy_attack_tick's pending skip: it must not fight while
    # still 'anim', and its first swing comes after the 0x002F. The order is
    # RECONSTRUCTION: retail's only witness (565.0302) is a ranged hit, which chases.
    st3, sent3, send3 = fresh()
    a3 = st3["agents"][ANIMAL_ID]
    a3["pos"] = a3["anchor"] = (60.0, 0.0)
    sent3.clear()
    proj, same_tick, log = hit_and_turn(st3, sent3, send3)
    got, vals = names(proj), dict(proj)
    check(same_tick == []
          and got == ["9F/65", "9B", "9F/36", "9F/42", "A3/16", "1E", "2F", "2E", "A0/4"]
          and vals.get("A0/4") == [4, ANIMAL_ID, PLAYER, 0]
          and a3.get("team_token") == ANIN and "whole burst" not in log,
          "2j. IN REACH (60 u, a melee player): the hit's own tick sends nothing naming it "
          "-- no swing under 'anim' -- and after the tick the 0x002F precedes its facing "
          "and its first swing: [9F/65, 9B, 9F/36, 9F/42, A3/16, 1E, 2F, 2E, A0/4 [4, 96, "
          "player, 0]] (RECONSTRUCTION: no in-reach retail witness)", (same_tick, got))


# ---------------------------------------------------------------------------------------
def section_controls():
    print("\n3. controls")
    saved = (authsrv.ANIMAL_TOKEN_FLIP, authsrv.PASSIVE_HOSTILES)
    try:
        # 3a. the known-bad arm
        authsrv.ANIMAL_TOKEN_FLIP = False
        st, sent, send = fresh()
        sent.clear()
        proj, _same, _log = hit_and_turn(st, sent, send)
        a = st["agents"][ANIMAL_ID]
        check(names(proj) == FLAG_OFF_BURST and names(proj) != RETAIL_BURST
              and a.get("team_token") == ANIM and a.get("provoked") is True,
              "3a. KNOWN-BAD ARM (--no-animal-token-flip): [9F/42, A3/16, 2B, 2A] on the "
              "hit's own tick -- the order comparator reports it against RETAIL_BURST -- "
              "and the body fights under 'anim'", names(proj))
        authsrv.ANIMAL_TOKEN_FLIP = True

        # 3b. a passive 'hostile' row: provoked, never turned
        st, sent, send = fresh()
        sent.clear()
        proj, _same, _log = hit_and_turn(st, sent, send, aid=PASSIVE_ID)
        p = st["agents"][PASSIVE_ID]
        check(p.get("provoked") is True and "A3/16" in names(proj)
              and not {"2F", "9F/65", "9B", "9F/36"} & set(names(proj))
              and p.get("team_token") is None,
              "3b. a passive 'hostile' row hit the same way is provoked and gets none of the "
              "turn (retail's 'mon1' first hits, 1f)", names(proj))

        # 3c. a hostile's hit provokes nothing and turns nothing
        st, sent, send = fresh()
        with contextlib.redirect_stdout(io.StringIO()):
            got = authsrv.provoke_hostile(st, ANIMAL_ID, CONTROL_ID, 1)
        a = st["agents"][ANIMAL_ID]
        check(got == [] and a.get("token_due") is None and not a.get("provoked"),
              "3c. a hit whose source is another hostile provokes nothing and turns nothing",
              got)

        # 3d. provoked with no word (a group-mate, a party body's hit): the whole burst
        st, sent, send = fresh()
        sent.clear()
        with contextlib.redirect_stdout(io.StringIO()):
            authsrv.provoke_hostile(st, ANIMAL_ID, PLAYER, 1)
        ticks(st, send)
        own_tick = [t for t in (token(op, v, ANIMAL_ID) for op, v in sent) if t]
        sim_tick(st, sent)
        ticks(st, send)
        got = names(projection(sent, ANIMAL_ID))
        check(own_tick == [] and got == ["9F/65", "9B", "9F/36", "2F", "2B", "2A"],
              "3d. turned with no hitter's word (a group-mate, a party body's hit): nothing "
              "on the provoke's own tick, then its WHOLE burst -- 65, 0x009B, 36, 0x002F -- "
              "ahead of its first follow (RECONSTRUCTION: no witness)", (own_tick, got))

        # 3f. --no-passive-hostiles: no provoke, no turn
        authsrv.PASSIVE_HOSTILES = False
        st, sent, send = fresh()
        with contextlib.redirect_stdout(io.StringIO()):
            got = authsrv.provoke_hostile(st, ANIMAL_ID, PLAYER, 1)
        check(got == [] and st["agents"][ANIMAL_ID].get("token_due") is None,
              "3f. under --no-passive-hostiles provoking is a no-op, so nothing turns (the "
              "documented interplay: it fights on proximity under 'anim')", got)
        authsrv.PASSIVE_HOSTILES = True

        # 3g. killed by the first hit: no 0x002F to a corpse
        st, sent, send = fresh()
        st["agents"][ANIMAL_ID]["last_hit"] = 0.0
        sent.clear()
        with contextlib.redirect_stdout(io.StringIO()):
            authsrv.hit_enemy(send, st, ANIMAL_ID, 1, exact=80.0, swing=False)
        sim_tick(st, sent)
        ticks(st, send)
        got = [t for t in (token(op, v, ANIMAL_ID) for op, v in sent) if t]
        a = st["agents"][ANIMAL_ID]
        check(a.get("dead") and "2F" not in got and a.get("token_due") == ANIN,
              "3g. a first hit that kills it carries the prelude, and no 0x002F goes to the "
              "corpse (the turn stays pending)", got)
    finally:
        authsrv.ANIMAL_TOKEN_FLIP, authsrv.PASSIVE_HOSTILES = saved


# ---------------------------------------------------------------------------------------
def section_load_guard():
    print("\n4. the load guard")
    real = agents.WORLD

    def run(name):
        t = table()
        t["animal_probe"] = dict(t["animal_probe"], allegiance=name)
        try:
            agents.WORLD = OneTable(t, real)
            return [k for k, _r in authsrv.area_population("animal_probe")], None
        except authsrv.PopulationError as exc:
            return None, str(exc)
        finally:
            agents.WORLD = real

    bad, why = run("anmial")
    good, _ = run("animal")
    check(bad is None and "'animal_probe'" in (why or "") and "'anmial'" in (why or "")
          and good is not None and "animal_probe" in good,
          "4a. area_population refuses allegiance 'anmial' naming the row (it was a bare "
          "KeyError inside bring-up) and accepts 'animal'", why)


# ---------------------------------------------------------------------------------------
def section_source():
    print("\n5. source: the flag, the call sites, the tick count, the silent 0x00C1")
    src = open(authsrv.__file__, encoding="utf-8").read()
    mod = ast.parse(src)
    top = [n.value.value for n in mod.body if isinstance(n, ast.Assign)
           and any(isinstance(t, ast.Name) and t.id == "ANIMAL_TOKEN_FLIP" for t in n.targets)
           and isinstance(n.value, ast.Constant)]
    import serverargs
    ap = serverargs.build_parser(
        doc="x", GAME_SRV_HOST=authsrv.GAME_SRV_HOST, GAME_SRV_PORT=authsrv.GAME_SRV_PORT,
        HOST_FIELD_ENCODING=authsrv.HOST_FIELD_ENCODING, TEST_SKILLBAR=authsrv.TEST_SKILLBAR,
        GRANT_MIN_INTERVAL=authsrv.GRANT_MIN_INTERVAL, PROF_WARRIOR=authsrv.PROF_WARRIOR,
        VAULT_DEFAULT=authsrv.VAULT_DEFAULT)
    main_fn = next(n for n in mod.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    flips = []
    for node in ast.walk(main_fn):
        if (isinstance(node, ast.If) and isinstance(node.test, ast.Attribute)
                and node.test.attr == "no_animal_token_flip"):
            flips += [s for s in node.body if isinstance(s, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == "ANIMAL_TOKEN_FLIP"
                              for t in s.targets)
                      and isinstance(s.value, ast.Constant) and s.value.value is False]
            flips += [s for s in node.body if isinstance(s, ast.Global)
                      and "ANIMAL_TOKEN_FLIP" in s.names]
    check(top == [True] and ap.parse_args([]).no_animal_token_flip is False
          and ap.parse_args(["--no-animal-token-flip"]).no_animal_token_flip is True
          and len(flips) == 2,
          "5a. ANIMAL_TOKEN_FLIP defaults True at module level; --no-animal-token-flip parses "
          "(default off) and main() sets the global False under it", (top, len(flips)))

    mv = inspect.getsource(authsrv.enemy_move_tick)
    at = inspect.getsource(authsrv.enemy_attack_tick)
    dh = inspect.getsource(authsrv.declare_body_max_on_hit)

    def first_after_pools(s):
        i = s.find("player_pools(state)\n")
        j = s.find("send_due_tokens(send, state, conn_id)")
        k = s.find("for agent_id, agent in list(")
        return 0 < i < j < k
    i_pre = dh.find("animal_turn_prelude(send, agent_id, agent, why)")
    i_42 = dh.find("[agents.PROP_HEALTH_MAX, agent_id,")
    check(first_after_pools(mv) and first_after_pools(at)
          and mv.count("animal_turn_pending(agent)") == 1
          and at.count("animal_turn_pending(agent)") == 1
          and 0 < i_pre < i_42 and dh.find("if not always:") > i_pre,
          "5b. both enemy ticks turn what is due before their loop and skip a body still "
          "pending; the prelude sits in the declare helper ahead of its gates and its 42")

    i_count = src.find('state["sim_ticks"] = state.get("sim_ticks", 0) + 1')
    i_send = src.find("send(GAME_SMSG_WORLD_SIMULATION_TICK, [delta_ms],")
    check(src.count('state["sim_ticks"] = state.get("sim_ticks", 0) + 1') == 1
          and 0 < i_count < i_send < i_count + 900,
          "5c. the world tick counts each 0x001E once, just BEFORE sending it (a hit from "
          "the client thread in between waits a tick more, never less)", (i_count, i_send))

    arm = None
    for node in ast.walk(mod):
        if (isinstance(node, ast.If) and isinstance(node.test, ast.Compare)
                and isinstance(node.test.left, ast.Name) and node.test.left.id == "opcode"
                and len(node.test.comparators) == 1
                and isinstance(node.test.comparators[0], ast.Name)
                and node.test.comparators[0].id == "GAME_CMSG_TARGET_SELECT"):
            arm = node
            break
    calls = sorted({c.func.id for s in (arm.body if arm else []) for c in ast.walk(s)
                    if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)})
    writes = sorted({ast.unparse(t) for s in (arm.body if arm else []) for t in
                     (s.targets if isinstance(s, ast.Assign) else [])})
    writes = [w.replace('"', "'") for w in writes]
    check(arm is not None and calls == [] and writes == ["state['target']",
                                                         "state['target_auto']"],
          "5d. the 0x00C1 TARGET_SELECT arm sends nothing and calls nothing -- it stores "
          "the selection -- so cancel-target on the animal (0x00C1 [0, 0]) draws no reply, "
          "as retail's 565.1515 did not", (calls, writes))


def main():
    print("test_animaltoken -- a charmable animal turns 'anim' -> 'anin' on its first "
          "landed hit, in retail's order (RANGERPRE-S12)")
    t0 = time.time()
    section_content()
    section_retail()
    section_ours()
    section_controls()
    section_load_guard()
    section_source()
    print(f"\n({time.time() - t0:.1f} s)")
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
