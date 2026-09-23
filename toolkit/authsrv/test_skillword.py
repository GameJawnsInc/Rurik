"""test_skillword -- the skill-damage word (property 10) and the player's own maximum
before a damage word, read off retail's tapes and locked on our sender
(DESKWORK-D5 step 3 (a) and (b), 2026-09-22).

WHAT IT IS REALLY CHECKING. Two residues of the damage batch at the PLAYER:

  (b) property 10 -- `[10, victim, skill]` -- is the skill the next damage number
      belongs to (skillcast 16.6: the client stores it at charContext+0x640 and the
      16/17/18 and 55/56 bodies consume and clear it). On retail's wire it is
      SELF-SCOPED: every one of the corpus's 92 names the observer, the very next
      message is a damage word to the observer, and none of the observer's own hits
      on a foe carries one (with exposure). `authsrv.skill_damage_word` now sends it
      between the player's own gain and the word wherever a SKILL damages the player,
      and never for the player's hits; `--no-skill-damage-word` is the pre-2026-09-22
      arm.
  (a) the player's own property 42 rides a word at the observer only when the
      maximum MOVED -- retail puts it immediately ahead of a damage word 0 of 3
      (armour-ignoring) / 0 of 401 (16/17). The observer's 42 rides the Deep
      Wound's own open/close batches (the maximum moving) and 13 of 47 heals; a
      first cut misread four Reversal-of-Fortune heals as damage-word
      declarations ("4 of 402"), which they are not. `armour_ignoring_damage`'s
      player branch declared it before every word; now `declare_player_max`
      sends it only when it differs from the last declared value, and
      `deep_wound_open`/`deep_wound_close` update the tracker as they send their
      own 42 (so the next word does not re-declare it -- ENG-1).
      `--player-max-always` is the pre-2026-09-22 arm.

Section 1 needs no vault (the sender, with a known-bad arm per flag). Section 2 reads
`vault/captures/live/` and is declared as a skip without it.
"""
import collections
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

# Floor from the green run of 2026-09-22: section 1 alone (the fixture-less core),
# 8 -> 10 with the two Deep Wound tracker checks (ENG-1). Section 2 (the tape,
# incl. the ENG-11 swing/attack-skill pins) is declared a skip without the vault.
LEDGER = checks.Ledger("the skill-damage word and the player's maximum", floor=10)
check = checks.adopt(LEDGER)

PLAYER = authsrv.PLAYER_AGENT_ID
INT = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
FLT = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET
P10 = agents.GV_SKILL_DAMAGE
P42 = agents.PROP_HEALTH_MAX
# the corpus on 2026-09-22 (floors; a tape does not shrink)
CORPUS_P10 = 92
CORPUS_OWN_HITS = 45        # the observer's own skill hits on foes with a word
CORPUS_OWN_55 = 3           # armour-ignoring words at the observer


def _fake():
    sent = []
    send = lambda op, vals, why="", quiet=False: sent.append((op, list(vals)))   # noqa: E731
    st = {"agents": {}, "pos": (0.0, 0.0),
          "player_health": float(agents.PLAYER_HEALTH)}
    authsrv.player_pools(st)
    st["agents"][10] = {
        "name": "a caster", "dead": False, "last_hit": 0.0,
        "health": 100.0, "max_health": 100.0, "armor_rating": 60,
        "pos": (10.0, 0.0), "skills": ((186, 0.0, 0.0),), "attacks_back": True}
    return sent, send, st


def _ops(sent):
    return [(op, v[0] if op in (INT, FLT) else None) for op, v in sent]


def section_sender():
    print("\n1. the sender: [10] between the gain and the word, the 42 only when moved")
    saved = (authsrv.SKILL_DAMAGE_WORD, authsrv.PLAYER_MAX_ALWAYS)
    try:
        authsrv.SKILL_DAMAGE_WORD, authsrv.PLAYER_MAX_ALWAYS = True, False
        # (b) a body's spell at the player
        sent, send, st = _fake()
        frac = authsrv._damage_fraction(12.0, authsrv.player_max_health(st),
                                        agents.PROP_DAMAGE, "a test spell")
        authsrv.body_spell_word(send, st, 10, 186, PLAYER, False, 12.0, frac,
                                None, 12.0, 0)
        ops = [op for op, _v in sent]
        i10 = next((i for i, (op, v) in enumerate(sent) if op == INT and v[0] == P10), None)
        check(i10 is not None and sent[i10][1] == [P10, PLAYER, 186]
              and ops[i10 + 1] == FLT and sent[i10 + 1][1][:3] == [agents.PROP_DAMAGE, PLAYER, 10]
              and ops[i10 - 1] == authsrv.AGENT_ADRENALINE_GAIN,
              "a body's spell at the player: gain, then [10, player, 186], then the word",
              f"{sent} -- retail's order for a spell onto the observer (0xA7, 0xA0, 0xCF, "
              f"[10], [16]; 16 + 10 + 9 of 92), the word IMMEDIATELY after the 10 as the "
              f"client's +0x640 consume-and-clear requires (skillcast 16.6)")
        # the known-bad arm
        authsrv.SKILL_DAMAGE_WORD = False
        sent, send, st = _fake()
        authsrv.body_spell_word(send, st, 10, 186, PLAYER, False, 12.0, frac,
                                None, 12.0, 0)
        check(not any(op == INT and v[0] == P10 for op, v in sent)
              and any(op == FLT for op, _v in sent),
              "KNOWN-BAD ARM: --no-skill-damage-word sends the word with no [10] ahead",
              f"{sent} -- the sender as it was until 2026-09-22")
        authsrv.SKILL_DAMAGE_WORD = True
        # (b) the negative: the PLAYER's skill on a foe carries none (0 of 45 on retail)
        sent, send, st = _fake()
        authsrv.hit_enemy(send, st, 10, 0, exact=12.0, swing=False, label="skill 186")
        check(any(op == FLT and v[1] == 10 for op, v in sent)
              and not any(op == INT and v[0] == P10 for op, v in sent),
              "the player's own skill hit on a foe carries NO [10] -- self-scoped, 0 of 45",
              f"{sent} -- a word on the foe went out and no property 10 anywhere; retail's 92 "
              f"all name the observer")
        # (b) a hostile's ATTACK SKILL on the player names its skill; a plain swing does not
        sent, send, st = _fake()
        body = st["agents"][10]
        body.update({"weapon": "starter_sword", "next_swing": 0.0, "attack_interval": 1.33,
                     "swing_target": PLAYER, "skill_ready": [0.0]})
        try:
            authsrv.land_swing(send, st, 10, body, 0, skill_id=322)
            swung = True
        except Exception as exc:                                # noqa: BLE001
            swung, sent = False, [("EXC", [str(exc)])]
        words = [i for i, (op, v) in enumerate(sent) if op == FLT and v[:2] == [agents.PROP_DAMAGE, PLAYER]]
        tens = [i for i, (op, v) in enumerate(sent) if op == INT and v[0] == P10]
        check(swung and words and tens and tens[0] == words[0] - 1
              and sent[tens[0]][1] == [P10, PLAYER, 322],
              "a hostile's attack skill 322 at the player: [10, player, 322] immediately before "
              "its word",
              f"{sent} -- 322 / 327 are among the corpus's 92 property-10 skills")
        sent, send, st = _fake()
        body = st["agents"][10]
        body.update({"weapon": "starter_sword", "next_swing": 0.0, "attack_interval": 1.33,
                     "swing_target": PLAYER})
        try:
            authsrv.land_swing(send, st, 10, body, 0)
        except Exception as exc:                                # noqa: BLE001
            sent = [("EXC", [str(exc)])]
        check(any(op == FLT and v[:2] == [agents.PROP_DAMAGE, PLAYER] for op, v in sent)
              and not any(op == INT and v[0] == P10 for op, v in sent),
              "and a plain swing at the player carries none",
              f"{sent} -- property 10 names a SKILL; a swing has none to name")
        # (a) the player's own 42: not before a 55 when it did not move. The
        # word's skill here is 143 (a life steal) -- the 3 corpus property-10
        # words that precede a 55 at the observer are all skill 143.
        sent, send, st = _fake()
        st["player_max_declared"] = int(authsrv.player_max_health(st))   # the create declared it
        authsrv.armour_ignoring_damage(send, st, PLAYER, 10, 9.0, 0, "a life steal", skill_id=143)
        ops = _ops(sent)
        check((INT, P42) not in ops and (FLT, agents.GV_ARMOR_IGNORING) in ops
              and (INT, P10) in ops
              and ops.index((INT, P10)) == ops.index((FLT, agents.GV_ARMOR_IGNORING)) - 1,
              "an armour-ignoring word at the player with the maximum unmoved: no 42, and "
              "[10, player, 143] immediately ahead of the 55",
              f"{sent} -- retail: 0 of 3 armour-ignoring words at the observer carry the "
              f"observer's 42; the 3 of the 92 property-10 words that precede a 55 are skill 143")
        # (a) ... declare_player_max's own logic: the 42 goes out when the tracker
        # is stale (a UNIT test of "differs"; the detail is now the corrected count)
        st["player_max_declared"] = int(authsrv.player_max_health(st)) - 20
        sent.clear()
        authsrv.armour_ignoring_damage(send, st, PLAYER, 10, 9.0, 0, "another")
        ops = _ops(sent)
        check(ops and ops[0] == (INT, P42)
              and sent[0][1] == [P42, PLAYER, int(authsrv.player_max_health(st))]
              and st["player_max_declared"] == int(authsrv.player_max_health(st)),
              "with the maximum moved since the last declaration the 42 goes out first and "
              "the tracker follows",
              f"{sent} -- retail: 0 of 401 damage words carry the observer's 42 immediately "
              f"ahead; it rides the Deep Wound's own batches (480 <-> 384 on 20260916T213125)")
        # (a) ENG-1: a REAL Deep Wound moves the maximum, and the tracker must
        # follow it so the next armour-ignoring word does NOT re-declare the 42.
        # This drives deep_wound_open rather than faking the tracker, so it
        # reddens if deep_wound_open stops updating `player_max_declared`.
        saved_dw = authsrv.DEEP_WOUND
        try:
            authsrv.DEEP_WOUND = True
            sent, send, st = _fake()
            st["player_max_declared"] = int(authsrv.player_max_health(st))
            authsrv.deep_wound_open(send, st, PLAYER, 0)
            dw_42 = [v for op, v in sent if op == INT and v[0] == P42]
            new_max = int(authsrv.player_max_health(st))
            check(len(dw_42) == 1 and dw_42[0] == [P42, PLAYER, new_max]
                  and st["player_max_declared"] == new_max,
                  "deep_wound_open declares the moved maximum ONCE and updates the tracker",
                  f"{sent}, tracker {st['player_max_declared']} vs max {new_max}")
            sent.clear()
            authsrv.armour_ignoring_damage(send, st, PLAYER, 10, 9.0, 0, "after a Deep Wound",
                                           skill_id=143)
            ops = _ops(sent)
            check((INT, P42) not in ops and (FLT, agents.GV_ARMOR_IGNORING) in ops,
                  "and the next armour-ignoring word after the Deep Wound sends NO redundant "
                  "42 (the tracker already holds the reduced maximum)",
                  f"{sent} -- before ENG-1 the stale tracker re-declared [42, player, "
                  f"{new_max}] ahead of the 55, the exact case retail shows 0 of 3")
        finally:
            authsrv.DEEP_WOUND = saved_dw
        # the known-bad arm
        authsrv.PLAYER_MAX_ALWAYS = True
        sent.clear()
        authsrv.armour_ignoring_damage(send, st, PLAYER, 10, 9.0, 0, "again")
        check(_ops(sent) and _ops(sent)[0] == (INT, P42),
              "KNOWN-BAD ARM: --player-max-always declares the 42 before every word",
              f"{sent} -- the sender as it was until 2026-09-22 ('3 of 3 on the tape', which "
              f"were a FOE's maximum ahead of Empathy's word)")
    finally:
        authsrv.SKILL_DAMAGE_WORD, authsrv.PLAYER_MAX_ALWAYS = saved


def _f32(dw):
    return struct.unpack("<f", struct.pack("<I", int(dw) & 0xFFFFFFFF))[0]


def _i(x):
    return int(x) if isinstance(x, (int, float)) else None


def section_corpus():
    print("\n2. retail's tapes: property 10 is self-scoped; the observer's 42 only when moved")
    try:
        live = vaultpath.require_dir("captures", "live", why="the skill-damage word")
    except (Exception, SystemExit) as exc:                     # noqa: BLE001
        LEDGER.skip("2. retail's tapes", str(exc))
        return
    import adrenjoin
    import tape
    from codec import Codec
    codec = Codec()
    n10 = 0
    victims = collections.Counter()
    followed = collections.Counter()
    own_hits = 0
    own_hits_with_10 = 0
    own55 = 0
    own55_with_42 = 0
    own_dmg = 0
    own_dmg_with_42 = 0
    own_heal = 0
    own_heal_with_42 = 0
    # ENG-11: the OTHER direction of the [10] rule, pinned too -- a word closed
    # by a plain swing (property 1 naming the source) carries no [10]; one closed
    # by an attack skill (property 46 naming the source) carries it every time.
    swing_words = 0
    swing_words_with_10 = 0
    atk_words = 0
    atk_words_with_10 = 0
    for stamp in sorted(os.listdir(live)):
        cap = os.path.join(live, stamp)
        if not os.path.isdir(cap):
            continue
        for chan in tape.channel_files(cap):
            try:
                _info, events = tape.load_tape(cap, chan["connection"])
                msgs, _r = tape.decode_all(events, codec, "GAME_SMSG", 0)
            except Exception:                                  # noqa: BLE001
                continue
            me = adrenjoin.whose_agent(msgs)
            if me is None:
                continue
            batches = collections.defaultdict(list)
            for t, op, v in msgs:
                batches[t].append((op, v))
            for _t, items in batches.items():
                for k, (op, v) in enumerate(items):
                    if op == 0x9F and len(v) > 3 and _i(v[1]) == 10:
                        n10 += 1
                        victims["observer" if _i(v[2]) == me else "other"] += 1
                        nxt = items[k + 1] if k + 1 < len(items) else None
                        ok = (nxt is not None and nxt[0] in (0xA2, 0xA3) and len(nxt[1]) > 2
                              and _i(nxt[1][1]) in (16, 17, 55) and _i(nxt[1][2]) == _i(v[2]))
                        followed["damage word, same agent" if ok else "OTHER"] += 1
                    if op == 0xA3 and len(v) > 4 and _i(v[1]) in (16, 17):
                        tgt, src = _i(v[2]), _i(v[3])
                        prev = items[k - 1] if k > 0 else None
                        has10 = (prev is not None and prev[0] == 0x9F and len(prev[1]) > 2
                                 and _i(prev[1][1]) == 10)
                        if src == me and tgt != me:
                            own_hits += 1
                            own_hits_with_10 += has10
                        if tgt == me:
                            own_dmg += 1
                            prev = items[k - 1] if k > 0 else None
                            # ADJACENT, not "somewhere earlier in the batch":
                            # the four batches on 20260916T213125 that hold the
                            # observer's 42 AND a damage word put the 42 ahead
                            # of a POSITIVE 55 (Reversal of Fortune's heal to
                            # self), never ahead of the damage word
                            own_dmg_with_42 += (prev is not None and prev[0] == 0x9F
                                                and len(prev[1]) > 3 and _i(prev[1][1]) == 42
                                                and _i(prev[1][2]) == me)
                            # ENG-11: classify by what CLOSED the attack -- a
                            # property 1 (melee finished) or 46 (attack skill
                            # finished) earlier in the batch naming the source
                            closing = None
                            for pop, pv in reversed(items[:k]):
                                if (pop == 0x9F and len(pv) > 2 and _i(pv[1]) in (1, 46)
                                        and _i(pv[2]) == src):
                                    closing = _i(pv[1])
                                    break
                            if closing == 1:
                                swing_words += 1
                                swing_words_with_10 += has10
                            elif closing == 46:
                                atk_words += 1
                                atk_words_with_10 += has10
                    if (op == 0xA3 and len(v) > 4 and _i(v[1]) == 55 and _i(v[2]) == me
                            and _f32(v[4]) > 0.0):
                        prev = items[k - 1] if k > 0 else None
                        own_heal += 1
                        own_heal_with_42 += (prev is not None and prev[0] == 0x9F
                                             and len(prev[1]) > 3 and _i(prev[1][1]) == 42
                                             and _i(prev[1][2]) == me)
                    if (op == 0xA3 and len(v) > 4 and _i(v[1]) == 55 and _i(v[2]) == me
                            and _f32(v[4]) < 0.0):
                        own55 += 1
                        own55_with_42 += any(pop == 0x9F and len(pv) > 3 and _i(pv[1]) == 42
                                             and _i(pv[2]) == me for pop, pv in items[:k])
    check(n10 >= CORPUS_P10 and victims.get("other", 0) == 0
          and followed.get("OTHER", 0) == 0,
          f"{n10} property-10 words, every one naming the OBSERVER, every one followed "
          f"immediately by a damage word to it",
          f"victims {dict(victims)}, followed by {dict(followed)} -- the client's +0x640 is "
          f"written and consumed in the same batch, and retail tells you the skill that hit "
          f"YOU, never the one you landed")
    check(own_hits >= CORPUS_OWN_HITS and own_hits_with_10 == 0,
          f"and none of the observer's own {own_hits} hits on others carries one (exposure: the "
          f"PvP tape's 45 accepted attack skills)",
          f"{own_hits_with_10} of {own_hits} -- a real negative, not a missing population")
    check(swing_words >= 40 and swing_words_with_10 == 0
          and atk_words >= 15 and atk_words_with_10 == atk_words,
          f"a damage word at the observer closed by a PLAIN SWING carries no [10] "
          f"({swing_words_with_10} of {swing_words}); one closed by an ATTACK SKILL carries it "
          f"every time ({atk_words_with_10} of {atk_words})",
          f"the other direction of the 92/92 rule, pinned so the sender's 'a swing has no "
          f"skill to name' rests on the tape and not on reasoning (ENG-11)")
    check(own55 >= CORPUS_OWN_55 and own55_with_42 == 0,
          f"the observer's own 42 rides NONE of its {own55} armour-ignoring words",
          f"{own55_with_42} of {own55} -- so `armour_ignoring_damage`'s player branch stops "
          f"declaring it before every 55")
    check(own_dmg >= 400 and own_dmg_with_42 == 0,
          f"and NONE of {own_dmg} damage words at the observer has its 42 immediately ahead",
          f"{own_dmg_with_42} of {own_dmg}. The observer's 42 rides the Deep Wound's own "
          f"open/close batches (the maximum moving) and sits ahead of a HEAL fraction -- never "
          f"ahead of a damage word. A first cut of this check counted a 42 anywhere earlier in "
          f"the batch and read four Reversal-of-Fortune heals as damage-word declarations")
    check(own_heal >= 47 and own_heal_with_42 >= 13 and own_heal_with_42 < own_heal,
          f"while {own_heal_with_42} of the observer's {own_heal} positive-55 HEAL words carry its "
          f"42 immediately ahead -- some, not all",
          f"13 of 47 on 2026-09-22 (Reversal of Fortune's conversion heals among the 13; Healing "
          f"Signet's self-heals among the 34 without). WHICH heals carry the declaration is "
          f"OPEN and recorded for the heal sender, which this pass does not touch; the floors "
          f"keep the observation from being read as either 'always' or 'never'")


def main():
    section_sender()
    section_corpus()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
