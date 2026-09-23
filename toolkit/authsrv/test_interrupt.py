"""test_interrupt -- the interrupt on the wire: retail's two witnessed batches locked on
our sender, byte-order against the tape (DESKWORK-D5 step 2, 2026-09-23).

WHAT IT IS REALLY CHECKING. Until today this server could interrupt nothing (castmech
P1, animref D5: "no interrupt has ever been captured"). Two tapes carry property 35,
both with the PLAYER as victim, and `interruptjoin.py` re-derives them with a
denominator (34 [59], 12 [49], 237 [3] -- every other stop a cancel; 4 [63], none
riding a stop). `authsrv.interrupt_player` sends the two shapes:

  a CAST in activation (Disrupting Chop 340 on Healing Signet, 20260916T213125
  t=484.333), after the interrupter's word:
      [8, P, 0]  E5 [P, skill, copy, R]  [59, P, 0]  E2 [P, skill, copy]  [35, P, 0]
      E5 [P, skill, copy, R + 20]
  and the E6 lands at R + 20 (24.007 s on the tape) -- the second E5 owns the clock.
  an AUTO-ATTACK (Lightning Javelin 230, 20260917T224104 t=434.658), before the
  caster's [10] and word:
      [8, P, 0]  [3, P, 0]  [35, P, 0]  [8, P, 1]
  the chain surviving on its ORIGINAL swing clock.

RECONSTRUCTION, said so at the call sites and pinned here as ours: [49] for an
interrupted attack skill (the cancel family's split); the un-queue of a queued cast
(WIKI); a BODY as victim (`interrupt_body`: the stop + [35] without the hold, a hero's
bar getting the E5 / E2 / E5 mirror). `--no-interrupts` is the known-bad arm.

THE FIX PASS (2026-09-23, D5B-R1/R2, ENG-1/4/5/10d) added: the body victim through
`land_swing_on_body` (a hostile's 340 on a party body -- the first cut had no hook on
that path, so no NPC attack skill interrupted anything), the two hook sites that had no
test (`hit_enemy`, `land_player_spell_shot`), and the three NOT-swinging states the
swing branch used to fire in (a chain paused in a cast's aftercast -- retail 3 of 3
such hits carry no [35] -- a follow leg walking in, a target out of reach), plus the
`mode` override that is D6's entry point.

Section 1 needs no vault (the sender). Section 2 reads `vault/captures/live/` through
`interruptjoin.census()` and is declared a skip without it; it compares section 1's
OWN output against the tape's bytes, agent id substituted, so a hand-copied constant
is never the reference.
"""
import os
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
PARENT = os.path.dirname(HERE)
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)
SCHEMA = os.path.join(PARENT, "schema")
if SCHEMA not in sys.path:
    sys.path.insert(0, SCHEMA)

import checks                                                  # noqa: E402
import agents                                                  # noqa: E402
import authsrv                                                 # noqa: E402
import vaultpath                                               # noqa: E402

# Floor from the green run of 2026-09-23: section 1 alone (the fixture-less sender,
# 28 of the 38 after the fix pass; 21 of 30 before it). Section 2 (the tape, 10) is
# declared a skip without the vault. The first cut declared 22 from a guess and the
# count came back 21 -- set from the run, both times.
LEDGER = checks.Ledger("the interrupt on the wire", floor=28)
check = checks.adopt(LEDGER)

P = authsrv.PLAYER_AGENT_ID
INT = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
FLT = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET
E2 = authsrv.GAME_SMSG_SKILL_REFUSED
E5 = authsrv.GAME_SMSG_SKILL_RECHARGE
E6 = authsrv.GAME_SMSG_SKILL_RECHARGED
HOLD, STOP_ATK, INTERRUPTED, STOP_ATKSKILL, STOP_SKILL = 8, 3, 35, 49, 59
CHOP, JAVELIN, SIGNET, POWER_ATTACK = 340, 230, 1, 322
CHOP_DISABLE = 20

# What section 1 produced, for section 2 to hold against the tape.
PRODUCED = {}


def _fake():
    sent = []
    send = lambda op, vals, why="", quiet=False: sent.append((op, list(vals)))   # noqa: E731
    st = {"agents": {}, "pos": (0.0, 0.0), "action_hold": 1,
          "player_health": float(agents.PLAYER_HEALTH)}
    authsrv.player_pools(st)
    st["agents"][104] = {
        "name": "an axe warrior", "dead": False, "last_hit": 0.0,
        "health": 100.0, "max_health": 100.0, "armor_rating": 60,
        "pos": (10.0, 0.0), "skills": ((CHOP, 0.0, 1.0),), "attacks_back": True,
        "weapon": "starter_sword", "next_swing": 0.0, "attack_interval": 1.33,
        "swing_target": P, "skill_ready": [0.0]}
    return sent, send, st


def _cast(skill_id=SIGNET, recharge=4, attack=False, begun=True, now=None):
    now = time.time() if now is None else now
    return {"skill_id": skill_id, "copy": 0, "begun": begun, "cost": 0, "units": 0,
            "target": None, "begin_at": now, "attack": attack,
            "e5_at": now + 1.0, "e3_at": now + 1.75, "e6_at": now + 1.0 + recharge,
            "recharge": int(recharge), "e5_sent": False, "e3_sent": False,
            "approach": None, "activation": 2.0, "aftercast": 0.75,
            "recharge_s": float(recharge)}


def section_sender():
    print("\n1. the sender: the two witnessed shapes, the books, the known-bad arm, the body")
    saved = authsrv.INTERRUPTS
    try:
        authsrv.INTERRUPTS = True
        # (a) THE CAST WITNESS: Disrupting Chop on Healing Signet mid-activation.
        sent, send, st = _fake()
        st["pending_casts"] = [_cast()]
        before = time.time()
        res = authsrv.interrupt_player(send, st, 0, CHOP, 104)
        expect = [(INT, [HOLD, P, 0]), (E5, [P, SIGNET, 0, 4]), (INT, [STOP_SKILL, P, 0]),
                  (E2, [P, SIGNET, 0]), (INT, [INTERRUPTED, P, 0]),
                  (E5, [P, SIGNET, 0, 4 + CHOP_DISABLE])]
        PRODUCED["cast"] = list(sent)
        check(res == "cast" and sent == expect,
              "a cast in activation, interrupted by 340: [8,0] E5(4) [59] E2 [35] E5(24), "
              "in that order and nothing else",
              f"{res} {sent} -- retail's victim run on 20260916T213125 t=484.333")
        cast = st["pending_casts"][0]
        check(cast["e5_sent"] and cast["e3_sent"] and cast.get("released")
              and cast["recharge"] == 24 and abs(cast["e6_at"] - (before + 24.0)) < 0.5
              and st.get("cast_busy_until", 0.0) <= time.time(),
              "the books: released, recharging 24 s from the interrupt (the second E5 owns "
              "the clock), no E3 owed, the caster free at once",
              f"e5_sent {cast['e5_sent']} e3_sent {cast['e3_sent']} released "
              f"{cast.get('released')} recharge {cast['recharge']} e6 in "
              f"{cast['e6_at'] - time.time():.2f}s")
        # (b) the tick afterwards: NOTHING until the E6, then exactly the E6.
        sent.clear()
        authsrv.cast_tick(send, st, 0)
        check(sent == [] and st["pending_casts"] == [cast],
              "the tick sends nothing for the interrupted entry before its E6 (no "
              "completion, no damage, no E3)",
              f"{sent}")
        cast["e6_at"] = time.time() - 0.01
        authsrv.cast_tick(send, st, 0)
        check(sent == [(E6, [P, SIGNET, 0])] and st["pending_casts"] == [],
              "at R + 20 the tick sends the E6 alone and drops the entry (retail: 0x00E6 "
              "[25, 1, 0] at +24.007 s)",
              f"{sent}")
        # (c) KNOWN-BAD ARM
        authsrv.INTERRUPTS = False
        sent, send, st = _fake()
        st["pending_casts"] = [_cast()]
        res = authsrv.interrupt_player(send, st, 0, CHOP, 104)
        check(res is None and sent == [] and not st["pending_casts"][0]["e5_sent"],
              "KNOWN-BAD ARM: --no-interrupts sends nothing and the cast runs on",
              f"{res} {sent} -- the server as it was until 2026-09-23")
        authsrv.INTERRUPTS = True
        # (d) "attacking" (230) leaves a SPELL in activation alone ...
        sent, send, st = _fake()
        st["pending_casts"] = [_cast()]
        res = authsrv.interrupt_player(send, st, 0, JAVELIN, 117)
        check(res is None and sent == [] and not st["pending_casts"][0]["e5_sent"],
              "Lightning Javelin ('interrupts attacking foes') does not touch a spell in "
              "activation -- the chain is paused for a cast, the victim is not attacking",
              f"{res} {sent}")
        # ... and interrupts an ATTACK SKILL in activation with [49] (RECONSTRUCTION)
        sent, send, st = _fake()
        st["pending_casts"] = [_cast(skill_id=POWER_ATTACK, recharge=4, attack=True)]
        res = authsrv.interrupt_player(send, st, 0, JAVELIN, 117)
        check(res == "cast" and sent == [(INT, [HOLD, P, 0]), (E5, [P, POWER_ATTACK, 0, 4]),
                                         (INT, [STOP_ATKSKILL, P, 0]),
                                         (E2, [P, POWER_ATTACK, 0]),
                                         (INT, [INTERRUPTED, P, 0])],
              "an attack skill in activation gets the attack family's [49] and no second E5 "
              "(230 carries no disable) -- RECONSTRUCTION from the cancel split, said so",
              f"{res} {sent}")
        # (e) the un-queue (WIKI): a queued entry behind the interrupted one is cancelled
        sent, send, st = _fake()
        st["pending_casts"] = [_cast(), _cast(skill_id=POWER_ATTACK, begun=False)]
        res = authsrv.interrupt_player(send, st, 0, CHOP, 104)
        queued = st["pending_casts"][1]
        check(res == "cast" and queued.get("cancelled") and not queued["e5_sent"]
              and (E2, [P, POWER_ATTACK, 0]) not in sent,
              "a cast still QUEUED behind the interrupted one is marked cancelled for the "
              "tick's pre-begin release ([45] + E2), not released here",
              f"{queued.get('cancelled')} {sent}")
        # (f) THE SWING WITNESS: the auto-attack chain, hold held
        sent, send, st = _fake()
        st["attacking"] = 104
        st["player_swing"] = {"target": 104, "lands_at": time.time() + 0.5}
        st["player_last_swing"] = 123.456
        res = authsrv.interrupt_player(send, st, 0, JAVELIN, 117)
        PRODUCED["swing"] = list(sent)
        check(res == "swing" and sent == [(INT, [HOLD, P, 0]), (INT, [STOP_ATK, P, 0]),
                                          (INT, [INTERRUPTED, P, 0]), (INT, [HOLD, P, 1])],
              "the auto-attack chain, interrupted by 230: [8,0] [3] [35] [8,1], in that order",
              f"{res} {sent} -- retail's victim run on 20260917T224104 t=434.658")
        check(st.get("player_swing_cancel") == "interrupted" and st["attacking"] == 104
              and st["player_last_swing"] == 123.456 and st["action_hold"] == 1,
              "the armed swing is handed to the tick to drop, the chain and its clock "
              "survive, the hold is re-taken (the next START came on the original clock)",
              f"cancel {st.get('player_swing_cancel')} attacking {st['attacking']} "
              f"last_swing {st['player_last_swing']} hold {st['action_hold']}")
        # ... with no hold held (our auto swing holds no walk gate): the two stops alone
        sent, send, st = _fake()
        st["attacking"] = 104
        st["action_hold"] = 0
        res = authsrv.interrupt_player(send, st, 0, JAVELIN, 117)
        check(res == "swing" and sent == [(INT, [STOP_ATK, P, 0]), (INT, [INTERRUPTED, P, 0])],
              "with no hold held neither 8 goes out -- transition-only, the chain does not "
              "acquire a walk gate it never had",
              f"{res} {sent}")
        # (g) nothing to interrupt; (h) a non-interrupting skill
        sent, send, st = _fake()
        res = authsrv.interrupt_player(send, st, 0, CHOP, 104)
        check(res is None and sent == [],
              "neither casting nor attacking: nothing goes out", f"{res} {sent}")
        sent, send, st = _fake()
        st["pending_casts"] = [_cast()]
        res = authsrv.interrupt_player(send, st, 0, POWER_ATTACK, 104)
        check(res is None and sent == [] and not st["pending_casts"][0]["e5_sent"],
              "a skill whose row does not say `interrupts` (322) interrupts nothing",
              f"{res} {sent}")
        # (i) END TO END, the attack skill: land_swing(340) at the player mid-cast --
        # the word FIRST, then the run (retail's order, 1 of 1)
        sent, send, st = _fake()
        st["pending_casts"] = [_cast()]
        body = st["agents"][104]
        try:
            authsrv.land_swing(send, st, 104, body, 0, skill_id=CHOP)
            swung = True
        except Exception as exc:                                # noqa: BLE001
            swung, sent = False, [("EXC", [str(exc)])]
        words = [i for i, (op, v) in enumerate(sent) if op == FLT and v[:2] == [agents.PROP_DAMAGE, P]]
        holds = [i for i, (op, v) in enumerate(sent) if op == INT and v[:3] == [HOLD, P, 0]]
        run = sent[holds[0]:] if holds else []
        PRODUCED["land_swing"] = list(sent)
        check(swung and words and holds and words[0] < holds[0]
              and run == PRODUCED["cast"],
              "through land_swing: the word lands, THEN the interrupt run, identical to (a)",
              f"{sent}")
        # (j) END TO END, the spell: body_spell_word(230) at the attacking player -- the
        # run BEFORE the [10] and the word (retail's order, 1 of 1)
        sent, send, st = _fake()
        st["attacking"] = 104
        frac = authsrv._damage_fraction(12.0, authsrv.player_max_health(st),
                                        agents.PROP_DAMAGE, "a javelin")
        authsrv.body_spell_word(send, st, 117, JAVELIN, P, False, 12.0, frac, None, 12.0, 0)
        i10 = next((i for i, (op, v) in enumerate(sent) if op == INT and v[0] == agents.GV_SKILL_DAMAGE), None)
        i35 = next((i for i, (op, v) in enumerate(sent) if op == INT and v[0] == INTERRUPTED), None)
        iw = next((i for i, (op, v) in enumerate(sent) if op == FLT and v[:2] == [agents.PROP_DAMAGE, P]), None)
        PRODUCED["spell_word"] = list(sent)
        check(i10 is not None and i35 is not None and iw is not None and i35 < i10 < iw
              and sent[i10 + 1] == sent[iw],
              "through body_spell_word: [8,0] [3] [35] [8,1], THEN [10, player, 230], THEN "
              "the word",
              f"{sent}")
        # (k) A BODY AS VICTIM -- RECONSTRUCTION: a hostile mid-cast
        sent, send, st = _fake()
        body = st["agents"][104]
        body.update({"skills": ((SIGNET, 2.0, 4.0),), "skill_ready": [0.0], "casting": 0,
                     "cast_lands_at": time.time() + 1.0})
        before = time.time()
        res = authsrv.interrupt_body(send, st, 104, body, 0, CHOP, P)
        check(res == "cast" and sent == [(INT, [STOP_SKILL, 104, 0]), (INT, [INTERRUPTED, 104, 0])]
              and body["casting"] is None and body["cast_lands_at"] is None
              and abs(body["skill_ready"][0] - (before + 24.0)) < 0.5,
              "a hostile mid-cast: [59, body, 0] [35, body, 0], no hold, no bar messages; "
              "the slot recharges 24 s from the interrupt (RECONSTRUCTION)",
              f"{res} {sent} ready in {body['skill_ready'][0] - time.time():.2f}s")
        # ... a HERO mid-cast: the bar mirror on its own id
        saved_hw = authsrv.HERO_WIRE_POOLS
        try:
            authsrv.HERO_WIRE_POOLS = True
            sent, send, st = _fake()
            body = st["agents"][104]
            body.update({"skills": ((SIGNET, 2.0, 4.0),), "skill_ready": [0.0], "casting": 0,
                         "cast_lands_at": time.time() + 1.0, "hero": 0})
            res = authsrv.interrupt_body(send, st, 104, body, 0, CHOP, P)
            check(res == "cast" and sent == [(E5, [104, SIGNET, 0, 4]), (INT, [STOP_SKILL, 104, 0]),
                                             (E2, [104, SIGNET, 0]), (INT, [INTERRUPTED, 104, 0]),
                                             (E5, [104, SIGNET, 0, 24])]
                  and SIGNET in body.get("hero_recharged_due", {}),
                  "a hero mid-cast: E5(4) [59] E2 [35] E5(24) on the hero's id and the E6 "
                  "due (RECONSTRUCTION: the player's run without the hold)",
                  f"{res} {sent}")
        finally:
            authsrv.HERO_WIRE_POOLS = saved_hw
        # (l) a body's swing in flight; (m) a body doing neither
        sent, send, st = _fake()
        body = st["agents"][104]
        body.update({"swinging": True, "swing_lands_at": time.time() + 0.3, "last_swing": 7.0})
        res = authsrv.interrupt_body(send, st, 104, body, 0, JAVELIN, P)
        check(res == "swing" and sent == [(INT, [STOP_ATK, 104, 0]), (INT, [INTERRUPTED, 104, 0])]
              and body["swing_lands_at"] is None and body["swinging"] and body["last_swing"] == 7.0,
              "a hostile's swing in flight: [3, body, 0] [35, body, 0], the landing dropped, "
              "the chain and its clock untouched (RECONSTRUCTION)",
              f"{res} {sent}")
        sent, send, st = _fake()
        res = authsrv.interrupt_body(send, st, 104, st["agents"][104], 0, CHOP, P)
        check(res is None and sent == [],
              "a body neither casting nor swinging: nothing", f"{res} {sent}")
        # ... and the body arm under the known-bad flag
        authsrv.INTERRUPTS = False
        sent, send, st = _fake()
        body = st["agents"][104]
        body.update({"skills": ((SIGNET, 2.0, 4.0),), "skill_ready": [0.0], "casting": 0,
                     "cast_lands_at": time.time() + 1.0})
        res = authsrv.interrupt_body(send, st, 104, body, 0, CHOP, P)
        check(res is None and sent == [] and body["casting"] == 0,
              "KNOWN-BAD ARM on the body: --no-interrupts leaves the body's cast running",
              f"{res} {sent}")
        authsrv.INTERRUPTS = True
        # (n) the content rows the sender reads
        check(authsrv.skill_interrupts(CHOP) == "action"
              and authsrv.skill_interrupt_disable(CHOP) == CHOP_DISABLE
              and authsrv.skill_interrupts(JAVELIN) == "attacking"
              and authsrv.skill_interrupt_disable(JAVELIN) == 0
              and authsrv.skill_interrupts(POWER_ATTACK) is None,
              "content/world.toml: 340 interrupts any action with +20, 230 only an attacking "
              "victim with no disable, 322 nothing",
              f"{authsrv.skill_interrupts(CHOP)} +{authsrv.skill_interrupt_disable(CHOP)}, "
              f"{authsrv.skill_interrupts(JAVELIN)} +{authsrv.skill_interrupt_disable(JAVELIN)}")
        # ---- THE FIX PASS (2026-09-23, D5B-R1/R2, ENG-1/4/5/10d) -------------------
        # (o) END TO END, a BODY as victim through land_swing_on_body: a hostile's
        # 340 at a PARTY BODY mid-cast -- the word, THEN the body's run. The first
        # cut hooked land_swing's PLAYER branch only, so no NPC's attack skill could
        # interrupt a hero or a henchman (RECONSTRUCTION, as every body victim).
        sent, send, st = _fake()
        st["agents"][20] = _party_body_casting()
        body = st["agents"][104]
        res = authsrv.land_swing(send, st, 104, body, 0, skill_id=CHOP, target_id=20)
        hero = st["agents"][20]
        iw = _idx(sent, FLT, [agents.PROP_DAMAGE, 20])
        i59 = _idx(sent, INT, [STOP_SKILL, 20])
        i35 = _idx(sent, INT, [INTERRUPTED, 20])
        check(res == "landed" and iw is not None and i59 is not None and i35 == i59 + 1
              and iw < i59 and hero["casting"] is None and hero["cast_lands_at"] is None
              and abs(hero["skill_ready"][0] - (time.time() + 24.0)) < 0.5,
              "through land_swing_on_body: a hostile's 340 on a party body mid-cast lands "
              "its word, THEN [59, body, 0] [35, body, 0]; the body's cast is dropped and its "
              "slot recharges 24 s (RECONSTRUCTION; the first cut had no hook on this path)",
              f"{res} {sent}")
        # (p) END TO END, hit_enemy: the PLAYER's 340 (skill_strike) on a hostile
        # mid-cast -- the word, then the body's run (this site had no test).
        sent, send, st = _fake()
        body = st["agents"][104]
        body.update({"skills": ((SIGNET, 2.0, 4.0),), "skill_ready": [0.0], "casting": 0,
                     "cast_lands_at": time.time() + 1.0,
                     "health": 1000.0, "max_health": 1000.0})
        res = authsrv.hit_enemy(send, st, 104, 0, bonus_damage=20.0, skill_strike=True,
                                skill_id=CHOP)
        iw = _word_idx(sent, 104)          # 16, or 17 on a critical roll
        i59 = _idx(sent, INT, [STOP_SKILL, 104])
        i35 = _idx(sent, INT, [INTERRUPTED, 104])
        check(res == "landed" and iw is not None and i59 is not None and i35 == i59 + 1
              and iw < i59 and body["casting"] is None
              and abs(body["skill_ready"][0] - (time.time() + 24.0)) < 0.5,
              "through hit_enemy: the player's 340 on a hostile mid-cast -- the word, then "
              "[59, body, 0] [35, body, 0], the slot recharging 24 s (RECONSTRUCTION)",
              f"{res} {sent}")
        # (q) END TO END, land_player_spell_shot: the PLAYER's 230 arriving on a
        # hostile whose swing is in flight -- the word (hit_enemy's), then [3] [35].
        sent, send, st = _fake()
        body = st["agents"][104]
        body.update({"swinging": True, "swing_lands_at": time.time() + 0.3, "last_swing": 7.0,
                     "health": 1000.0, "max_health": 1000.0})
        shot = {"spell": {"skill_id": JAVELIN, "amount": 12.0, "visual": None, "first": False},
                "target": 104}
        res = authsrv.land_player_spell_shot(send, st, 0, shot)
        iw = _word_idx(sent, 104)
        i3 = _idx(sent, INT, [STOP_ATK, 104])
        i35 = _idx(sent, INT, [INTERRUPTED, 104])
        check(res == "landed" and iw is not None and i3 is not None and i35 == i3 + 1
              and iw < i3 and body["swing_lands_at"] is None and body["last_swing"] == 7.0,
              "through land_player_spell_shot: the player's 230 on a hostile's swing in "
              "flight -- the word, then [3, body, 0] [35, body, 0], the landing dropped, the "
              "clock untouched (RECONSTRUCTION: a body's word is hit_enemy's, ahead of the run)",
              f"{res} {sent}")
        # (r) NOT SWINGING: the chain PAUSED in a cast's AFTERCAST (E5 sent, E3 owed).
        # Retail: 3 of 3 such hits by 340 / 230 carry no [35] (_player_chain_running).
        sent, send, st = _fake()
        st["attacking"] = 104
        done = _cast()
        done["e5_sent"] = True
        st["pending_casts"] = [done]
        r340 = authsrv.interrupt_player(send, st, 0, CHOP, 104)
        r230 = authsrv.interrupt_player(send, st, 0, JAVELIN, 117)
        check(r340 is None and r230 is None and sent == [] and st["attacking"] == 104,
              "AFTERCAST: a chain paused for a cast (E5 sent, E3 owed) is not swinging -- "
              "neither 340 nor 230 sends the swing run (retail: 3 of 3 aftercast hits, no [35])",
              f"{r340} {r230} {sent}")
        # (s) NOT SWINGING: the follow leg is walking the body in (`approach`).
        sent, send, st = _fake()
        st["attacking"] = 104
        st["approach"] = {"target": 104, "t0": time.time()}
        res = authsrv.interrupt_player(send, st, 0, CHOP, 104)
        check(res is None and sent == [],
              "APPROACH: a chain whose follow leg is still walking in is not swinging -- "
              "nothing goes out (UNOBSERVED on retail; left alone)",
              f"{res} {sent}")
        # (t) NOT SWINGING: the target out of reach (the chain stalls there).
        sent, send, st = _fake()
        st["attacking"] = 104
        st["agents"][104]["pos"] = (5000.0, 0.0)
        res = authsrv.interrupt_player(send, st, 0, CHOP, 104)
        check(res is None and sent == [],
              "OUT OF REACH: a chain whose target is 5000 u away is not swinging -- nothing "
              "goes out",
              f"{res} {sent}")
        # (u) D6's hook: `mode` overrides the row -- a skill-less "action" interrupt
        # on an open cast runs the cast shape with no disable.
        sent, send, st = _fake()
        st["pending_casts"] = [_cast()]
        res = authsrv.interrupt_player(send, st, 0, POWER_ATTACK, 104, mode="action")
        check(res == "cast" and sent == [(INT, [HOLD, P, 0]), (E5, [P, SIGNET, 0, 4]),
                                         (INT, [STOP_SKILL, P, 0]), (E2, [P, SIGNET, 0]),
                                         (INT, [INTERRUPTED, P, 0])],
              "mode='action' passed explicitly (D6's entry point) interrupts the cast on a "
              "skill whose row says nothing, with no second E5",
              f"{res} {sent}")
    finally:
        authsrv.INTERRUPTS = saved


def _idx(sent, op, head):
    """Index of the first message with this opcode whose values open with `head`."""
    return next((i for i, (o, v) in enumerate(sent) if o == op and v[:len(head)] == head),
                None)


def _word_idx(sent, victim):
    """Index of the first damage word at `victim`: property 16, or 17 when the
    player's roll came up a critical (hit_enemy's own word for one)."""
    return next((i for i, (o, v) in enumerate(sent)
                 if o == FLT and len(v) > 1 and v[1] == victim and v[0] in (16, 17)), None)


def _party_body_casting():
    """A party body (a hero) mid-cast on Healing Signet, for a hostile's swing to land on."""
    return {"name": "a hero", "dead": False, "died_at": 0.0, "health": 500.0,
            "max_health": 500.0, "last_hit": 0.0, "pos": (5.0, 0.0), "plane": 0,
            "allegiance": agents.ALLEGIANCE_PLAYER, "attack_speed": authsrv.ENEMY_ATTACK_SPEED,
            "effects": 0, "attacks_back": False, "skills": ((SIGNET, 2.0, 4.0),),
            "skill_ready": [0.0], "last_swing": 0.0, "casting": 0,
            "cast_lands_at": time.time() + 1.0}


def _f32(dw):
    return struct.unpack("<f", struct.pack("<I", int(dw) & 0xFFFFFFFF))[0]


def _subst(msgs, victim):
    """Our sender's messages with the PLAYER id replaced by the tape's victim id --
    in the AGENT SLOT only (a property's second field, a bar message's first).
    PLAYER_AGENT_ID is 1, which is also Healing Signet's id and the hold's set
    value, so a blind replace rewrote both (the first cut of this test)."""
    out = []
    for op, v in msgs:
        v = list(v)
        if op in (INT, FLT, authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET,
                  authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT) and len(v) > 1 and v[1] == P:
            v[1] = victim
        elif op in (E2, E5, E6) and v and v[0] == P:
            v[0] = victim
        out.append((op, v))
    return out


def _shape(msgs, victim):
    """(op, property) per property message addressed to `victim`, (op, skill) per
    bar message on it, the 0x00CF gain set aside (the adrenaline arc's, tested
    there): the ORDER of the event."""
    out = []
    for op, v in msgs:
        if op in (INT, FLT, authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET,
                  authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT) and len(v) > 1 and v[1] == victim:
            out.append((op, v[0]))
        elif op in (E2, E5) and len(v) > 1 and v[0] == victim:
            out.append((op, v[1]))
    return out


def section_corpus():
    print("\n2. retail's tapes: the denominator, the two runs against section 1's output")
    try:
        vaultpath.require_dir("captures", "live", why="the interrupt witnesses")
    except (Exception, SystemExit) as exc:                     # noqa: BLE001
        LEDGER.skip("2. retail's tapes", str(exc))
        return
    import interruptjoin
    c = interruptjoin.census()
    sc = interruptjoin.score(c)
    tfs = c["thirty_fives"]
    # The write-up's corpus: [35] on tapes stamped up to the day it was written.
    dated = [r for r in tfs if r["capture"] <= "20260923T235959"]
    check(len(dated) == 2 and sc["n59"] >= 34 and sc["n49"] >= 12 and sc["n10"] >= 92,
          "the corpus as of 2026-09-23 holds EXACTLY 2 property-35 messages (a third on a "
          "tape of that day or earlier reddens this); >= 34 [59], >= 12 [49], >= 92 [10]",
          f"[35] {len(dated)} of {len(tfs)} dated, [59] {sc['n59']}, [49] {sc['n49']}, "
          f"[3] {sc['n3']}, [10] {sc['n10']}, [63] {sc['n63']}")
    check(sc["p2"] and all(r["own"] and r["run_opens_family"] for r in tfs),
          "both victims are the observer; in each batch the FIRST interrupt-family message "
          "at the victim is the hold release [8, victim, 0] (no stop or bar message ahead of "
          "it) and the run is contiguous",
          f"{[(r['capture'], r['own'], r['run_opens_family'], r['run_contiguous']) for r in tfs]}")
    check(sc["p5"] and sc["knockdown_with_35"] == 0,
          "P5 as registered: no batch holds a [63] and a [35] on one agent (a real "
          "predicate now; the first cut's ended in `or True`)",
          f"p5 {sc['p5']}, [63] with [35]: {sc['knockdown_with_35']}")
    check(sc["knockdown_with_35"] == 0
          and all(r["kind"] != "knockdown" for r in c["stops"]),
          "no [63] rides a [35] batch and no stop rides a [63] batch: a knock-down is not "
          "an interrupt on the wire (WIKI agrees)",
          f"{sc['kinds']}, [63] with [35]: {sc['knockdown_with_35']}")
    cast = sc["witnesses"].get("20260916T213125 57894 cast")
    swing = sc["witnesses"].get("20260917T224104 62557 swing")
    if cast is None or swing is None:
        LEDGER.skip("2b. the two witnesses", f"not both found: {list(sc['witnesses'])}")
        return
    if "cast" not in PRODUCED or "swing" not in PRODUCED:
        LEDGER.skip("2b. the two witnesses", "section 1 produced nothing to compare")
        return
    check(_subst(PRODUCED["cast"], cast["agent"]) == cast["run"],
          "OUR cast run == the tape's, byte for byte with the victim id substituted "
          "([8,0] E5(4) [59] E2 [35] E5(24))",
          f"ours {_subst(PRODUCED['cast'], cast['agent'])}\n      tape {cast['run']}")
    check(_subst(PRODUCED["swing"], swing["agent"]) == swing["run"],
          "OUR swing run == the tape's, byte for byte with the victim id substituted "
          "([8,0] [3] [35] [8,1])",
          f"ours {_subst(PRODUCED['swing'], swing['agent'])}\n      tape {swing['run']}")
    # The whole event's ORDER at the victim, end to end through land_swing /
    # body_spell_word: the tape's victim-addressed messages against ours.
    tape_cast = [(op, v[1] if op in (E2, E5) else v[0])
                 for op, v in cast["victim_batch"] if op != 0x00CF]
    tape_swing = [(op, v[1] if op in (E2, E5) else v[0])
                  for op, v in swing["victim_batch"] if op != 0x00CF]
    check("land_swing" in PRODUCED and _shape(PRODUCED["land_swing"], P) == tape_cast,
          "end to end (land_swing 340): [10] word [8] E5 [59] E2 [35] E5 -- the tape's "
          "order at the victim",
          f"ours {_shape(PRODUCED.get('land_swing', []), P)}\n      tape {tape_cast}")
    # The swing witness's batch carries two impact visuals and the caster's 0x00A7
    # ahead of the run; ours sends the impact from the projectile path, not from
    # body_spell_word, so the comparison starts at the hold release.
    ours_swing = _shape(PRODUCED.get("spell_word", []), P)
    k = next((i for i, (op, f) in enumerate(tape_swing) if (op, f) == (INT, HOLD)), None)
    check(k is not None and ours_swing and ours_swing[0] == (INT, HOLD)
          and ours_swing == tape_swing[k:],
          "end to end (body_spell_word 230): [8] [3] [35] [8] [10] word -- the tape's order "
          "at the victim from the hold release",
          f"ours {ours_swing}\n      tape {tape_swing[k:] if k is not None else tape_swing}")
    # The E6 that closes the interrupted skill: at R + 20 on the tape, so the
    # SECOND E5 is the one the client's clock honours.
    import bufflog
    import deepwoundjoin
    live = vaultpath.require_dir("captures", "live", why="the interrupt witnesses")
    seq = deepwoundjoin.sequence(os.path.join(live, "20260916T213125"), cast["connection"],
                                 bufflog.Codec())
    e6 = [t for _i, t, op, v in seq
          if op == E6 and v[1:] == [cast["agent"], SIGNET, 0] and t > cast["t"]]
    gap = (e6[0] - cast["t"]) if e6 else None
    check(gap is not None and abs(gap - 24.0) < 0.1,
          "the tape's 0x00E6 [victim, 1, 0] lands 24.0 +- 0.1 s after the interrupt: the "
          "second E5's 24, not the first's 4",
          f"gap {gap}")
    check(cast["interrupter"] == CHOP and cast["e5"] == [(SIGNET, 4), (SIGNET, 4 + CHOP_DISABLE)]
          and swing["interrupter"] == JAVELIN and swing["e2"] == [] and swing["e5"] == [],
          "the interrupters read off the [10] words are 340 and 230; the signet's recharges "
          "4 then 24; the swing interrupt carries no bar message",
          f"{cast['interrupter']} {cast['e5']} / {swing['interrupter']} {swing['e2']} {swing['e5']}")


def main():
    print("test_interrupt -- the interrupt on the wire (DESKWORK-D5 step 2)")
    section_sender()
    section_corpus()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
