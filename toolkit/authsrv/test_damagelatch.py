r"""test_damagelatch -- the player's hit closes its swing with [1] BEFORE its damage word,
so the client draws the number on the player's own swing (ANIMREF-RE 43, 2026-09-30;
studies/animref/FINDINGS.md 43).

WHAT IT IS REALLY CHECKING. The client keeps a one-slot latch: 0x009F [1|46|49, agent]
sets it to that agent (0x007F6BC0), any 0x00A0 [4|50] clears it (0x007F6C10), and a
damage word's effect allocator (0x007F5340) splices the number into the LATCHED agent's
pending animation node, so the number is drawn when THAT agent's animation lands.
Retail's batch at the windup is [1, me, 0], the gain, the word -- [1] first, 1,376 of
1,376. Ours sent [1] last, so a hit arriving while the raider's [1] was latched was
drawn on the raider's swing: the owner's "my attacks delay, then double-hit". The file
replays that latch (`client_latch`) over what the server sends, and checks the rule
against retail before it judges ours.

  1  a plain armed sword hit through the real hit_enemy: [1, me, 0], then 0x00CF,
     then the word (the first-hit maximum, when sent, between the gain and the word);
     exactly one [1].
  2  THE LATCH: the raider's swing just landed ([1, raider] then its word on the
     player), then the player's hit -- the client's latch names the PLAYER at the
     player's word; and the raider's word was latched to the raider.
  3  a scythe swing with an extra target: [1] ahead of BOTH words (WEAPONS-W3's batch).
  4  the KNOWN-BAD arm (--hit-finish-last): [1] after the word, and the latch names
     the RAIDER at the player's word -- the red this file exists for.
  5  the switch's wiring.
  6  RETAIL (vault): the observer's [1] precedes its word in every hit stamp, and the
     latch replay pairs >= 85 % of the observer's words with itself. Skipped without
     the captures.
"""
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
PARENT = os.path.dirname(HERE)
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

import checks                                                  # noqa: E402
import agents                                                  # noqa: E402
import authsrv                                                 # noqa: E402

# Floor from the BARE-MACHINE green run of 2026-09-30 (RURIK_VAULT at an empty
# directory): 9 -- sections 1-5; section 6 (the captures) declares a skip. 11 with the
# vault. HIT_FINISH_FIRST = False in the source reddens 7.
LEDGER = checks.Ledger("damage latch", floor=9)
check = checks.adopt(LEDGER)

P = authsrv.PLAYER_AGENT_ID
FOE, NEAR, RAIDER = 110, 21, 30
INT = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
INT_T = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET
FLOAT_T = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET
GAIN = 0x00CF
FIN = agents.GV_MELEE_ATTACK_FINISHED


def client_latch(stream):
    """The client's rule over (op, values): returns [(source, latched)] per damage word.
    Values are the payload only ([prop, agent, ...] / [prop, target, source, f])."""
    latch, out = 0, []
    for op, v in stream:
        if op == INT and len(v) > 1 and v[0] in (1, 46, 49):
            latch = v[1]
        elif op == INT_T and len(v) > 1 and v[0] in (4, 50):
            latch = 0
        elif op == FLOAT_T and len(v) > 2 and v[0] in (16, 17):
            out.append((v[2], latch))
    return out


class Wire:
    def __init__(self):
        self.sent = []

    def __call__(self, op, vals, label="", quiet=False):
        self.sent.append((op, list(vals)))


def _foe(pos, health=9000.0):
    return {"name": "t", "dead": False, "died_at": 0.0, "health": health,
            "max_health": health, "last_hit": 0.0, "pos": pos, "plane": 0,
            "armor_rating": 20.0, "allegiance": agents.ALLEGIANCE_HOSTILE,
            "effects": 0, "attacks_back": False, "skills": (), "skill_ready": [],
            "npc": {"level": 3, "profession": 1}}


def _world(extra=None):
    ags = {FOE: _foe((60.0, 0.0))}
    for aid, pos in (extra or {}).items():
        ags[aid] = _foe(pos, 500.0)
    return {"agents": ags, "pos": (0.0, 0.0), "level": 3}


def _arm(weapon):
    authsrv.apply_party_character({"player_weapon": weapon})
    authsrv.PLAYER_SWING_DAMAGE = (10, 10)


def _idx(sent, pred):
    return [i for i, (op, v) in enumerate(sent) if pred(op, v)]


def _raider_swing():
    """What the raider's landed swing on the player puts on the wire (the NPC path,
    which already closes first): its [1], then its word on the player."""
    return [(INT_T, [4, RAIDER, P, 0]), (INT, [FIN, RAIDER, 0]),
            (FLOAT_T, [16, P, RAIDER, 0.05])]


def section_order():
    print("== 1. the plain hit: [1], the gain, the word ==")
    _arm("starter_sword")
    w = Wire()
    authsrv.hit_enemy(w, _world(), FOE, 1, armed=True)
    fin = _idx(w.sent, lambda op, v: op == INT and v[:2] == [FIN, P])
    gain = _idx(w.sent, lambda op, v: op == GAIN)
    word = _idx(w.sent, lambda op, v: op == FLOAT_T and v[0] in (16, 17) and v[2] == P)
    # The gain rides only a bar that carries an adrenal skill (the DARK rule,
    # test_adrenwire): with the vault's skills table the default bar does, on a bare
    # machine it does not -- so the gain's slot is checked when it is sent.
    check(len(fin) == 1 and len(word) == 1 and fin[0] < word[0]
          and (not gain or (len(gain) == 1 and fin[0] < gain[0] < word[0])),
          "an armed sword hit is [1, me, 0], then 0x00CF (when the bar earns one), then the "
          "word -- retail's batch, 1,376 of 1,376 -- with exactly one [1]",
          f"[1]@{fin} gain@{gain} word@{word}: {w.sent}")
    check(fin and fin[0] == 0,
          "and the [1] is the batch's FIRST message", f"{w.sent[:3]}")
    return w.sent


def section_latch(batch):
    print("== 2. the client's latch names the player at the player's word ==")
    stream = _raider_swing() + [(INT_T, [4, P, FOE, 0])] + batch
    pairs = client_latch(stream)
    check(pairs == [(RAIDER, RAIDER), (P, P)],
          "after the raider's landed swing, the player's word is latched to the PLAYER (and "
          "the raider's to the raider) -- the number rides the player's own swing",
          f"{pairs}")
    # the same with the player's start ARMED long before (no [4] between): the raider's
    # [1] is still latched when the player's batch arrives
    pairs = client_latch(_raider_swing() + batch)
    check(pairs[-1] == (P, P),
          "and with no start between them -- the raider's [1] still latched when the player's "
          "batch arrives, the case that drew the owner's hits on the raider -- still the "
          "player", f"{pairs}")


def section_scythe():
    print("== 3. a scythe's batch: [1] ahead of both words ==")
    saved = (authsrv.blind_miss, authsrv.blocks, authsrv.critical_rate)
    try:
        authsrv.blind_miss = lambda st_, a: False
        authsrv.blocks = lambda st_, t: False
        authsrv.critical_rate = lambda r: 0.0
        _arm("starter_scythe")
        w = Wire()
        st = _world({NEAR: (138.0, 0.0)})
        authsrv.hit_enemy(w, st, FOE, 1, armed=True)
        fin = _idx(w.sent, lambda op, v: op == INT and v[:2] == [FIN, P])
        words = _idx(w.sent, lambda op, v: op == FLOAT_T and v[0] in (16, 17) and v[2] == P)
        check(len(fin) == 1 and len(words) == 2 and fin[0] < words[0],
              "a scythe swing that words an extra foe sends [1] ahead of BOTH words -- "
              "WEAPONS-W3's [1, me, 0] then per hit the gain and the word",
              f"[1]@{fin} words@{words}")
        pairs = client_latch(w.sent)
        check(pairs and all(src == P and lat == P for src, lat in pairs),
              "and both numbers latch to the player", f"{pairs}")
    finally:
        authsrv.blind_miss, authsrv.blocks, authsrv.critical_rate = saved
        _arm("starter_sword")


def section_known_bad():
    print("== 4. the known-bad arm: --hit-finish-last ==")
    saved = authsrv.HIT_FINISH_FIRST
    authsrv.HIT_FINISH_FIRST = False
    try:
        _arm("starter_sword")
        w = Wire()
        authsrv.hit_enemy(w, _world(), FOE, 1, armed=True)
        fin = _idx(w.sent, lambda op, v: op == INT and v[:2] == [FIN, P])
        word = _idx(w.sent, lambda op, v: op == FLOAT_T and v[0] in (16, 17) and v[2] == P)
        check(len(fin) == 1 and word and fin[0] > word[0],
              "the [1] trails the word -- the order before the fix", f"{w.sent}")
        pairs = client_latch(_raider_swing() + w.sent)
        check(pairs[-1] == (P, RAIDER),
              "and the client's latch names the RAIDER at the player's word: the number is "
              "drawn on the raider's swing (30 % of the owner's hits on 20260930T202753)",
              f"{pairs}")
    finally:
        authsrv.HIT_FINISH_FIRST = saved


def section_wiring():
    print("== 5. the switch ==")
    src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
    args = open(os.path.join(HERE, "serverargs.py"), encoding="utf-8").read()
    check(authsrv.HIT_FINISH_FIRST is True and '"--hit-finish-last"' in args
          and "if a.hit_finish_last:" in src and "HIT_FINISH_FIRST = False" in src,
          "HIT_FINISH_FIRST ships ON and --hit-finish-last reverts it", "")


def section_retail():
    print("== 6. retail: [1] first, and the latch pairs the observer with itself ==")
    try:
        import livewire
        import henchjoin
        root = livewire.captures_root()
    except Exception as exc:                                    # pragma: no cover
        LEDGER.skip("the retail census", f"livewire unavailable: {exc}")
        return
    if not root or not os.path.isdir(root):
        LEDGER.skip("the retail census", "no live captures on this machine")
        return
    order = collections.Counter()
    latch = collections.Counter()
    for capdir, _who in livewire.live_captures():
        for cf in livewire.connections(capdir):
            c, merged, _ok = livewire.decode_conn(capdir, cf)
            if c is None or not merged:
                continue
            me = henchjoin.whose_agent(merged)
            if me is None:
                continue
            s2c = [(t, op, [int(x) if isinstance(x, int) else x for x in v[1:]])
                   for t, d, op, v in merged if d == "s2c"]
            for src, lat in client_latch([(op, v) for _t, op, v in s2c]):
                if src == me:
                    latch["self" if lat == me else "nobody" if lat == 0 else "another"] += 1
            for k, (t, op, v) in enumerate(s2c):
                if not (op == FLOAT_T and len(v) > 2 and v[0] in (16, 17) and v[2] == me):
                    continue
                fins = [j for j in range(max(0, k - 6), min(len(s2c), k + 7))
                        if s2c[j][1] == INT and s2c[j][2][:2] == [1, me]
                        and abs(s2c[j][0] - t) <= 0.01]
                if fins:
                    order["before" if fins[0] < k else "after"] += 1
    check(order["before"] >= 1300 and order["after"] == 0,
          "every observer hit with its [1] in the stamp sends the [1] FIRST",
          f"{dict(order)}")
    n = sum(latch.values())
    check(n >= 1500 and latch["self"] / n >= 0.85 and latch["another"] / n <= 0.03,
          "and the client's latch pairs >= 85 % of the observer's words with the observer "
          "itself (<= 3 % with another agent) -- the rule this file applies to ours",
          f"{dict(latch)}")


def main():
    batch = section_order()
    section_latch(batch)
    section_scythe()
    section_known_bad()
    section_wiring()
    section_retail()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
