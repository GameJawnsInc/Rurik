r"""test_shouts -- a party-wide shout reaches every living ally in earshot, and the tape
that says so (DESKWORK-D5 step 5, 2026-09-23).

WHAT IT IS REALLY CHECKING. Until today "Charge!" (364) opened its episode on the
caster alone -- world.toml's own row said "Earshot is not modelled". `shoutjoin.py`
reads the live corpus: 65 shout applies on 96 connections, 42 the observer's own cast
and 23 another ally's (17 on the observer, 6 on a hero), every one attributed by the
`[48, caster, skill]` announce in its own batch, 0 of 8 foe shouts applying, the batch
re-declaring the other party members' speed. The server now opens one episode per
living ally inside the skill's own `aoe_range` (the client's record, 1000 u for 364 and
348 = WIKI earshot) behind `--no-party-wide-shouts`.

Section 1 needs no vault (the sender): the player shouting reaches a hero and a
henchman inside the radius and not a hero beyond it, a dead ally or a foe; the hero's
0x0042 goes out and the henchman's is suppressed (effect_list_send, MANTID); each
wearer gets its own buff id and its own speed word; the shout cures an ally's
Crippled; a hero shouting reaches the PLAYER (retail's 17 foreign applies); a stance
reaches nobody; the boundary is inclusive; a row without a radius or a caster
without a position reaches nobody and says so; `--no-party-wide-shouts` is the
caster-alone arm and the hero at 500 u gets NOTHING under it (the known-bad arm).

Section 2 reads `vault/captures/live/` through `shoutjoin.census()` and is declared
a skip without it. It pins the composition on tapes stamped 2026-09-23 or earlier
(a later tape does not redden it): 48 applies of 364 and 11 of 348 on the observer,
6 on a hero, 42 self / 17 other, 0 unattributed, 0 prop-60 announces of a Shout id,
0 foe applies, 4 foe shouts inside 1000 u with none applying, 0 REFUTING crossings of
the 1000 u radius, the largest resolved apply distance above 900 u, and P6.
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
PARENT = os.path.dirname(HERE)
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

import checks                                                  # noqa: E402
import agents                                                  # noqa: E402
import authsrv                                                 # noqa: E402
import effects                                                 # noqa: E402
import vaultpath                                               # noqa: E402

# Floor from the green run of 2026-09-23: section 1 alone (the sender, no vault;
# 30 of the 42). Section 2 (the tape, 12) is declared a skip without the vault.
LEDGER = checks.Ledger("party-wide shouts", floor=30)
check = checks.adopt(LEDGER)

P = authsrv.PLAYER_AGENT_ID
APPLY = authsrv.GAME_SMSG_EFFECT_APPLY
REMOVE = authsrv.GAME_SMSG_EFFECT_REMOVE
SPEED = authsrv.GAME_SMSG_AGENT_UPDATE_SPEED_BASE
CHARGE, WATCH_YOURSELF, FRENZY = 364, 348, 346
CRIPPLED = effects.CONDITION_BY_NAME["Crippled"]
HERO, HENCH, FAR_HERO, DEAD_HERO, FOE = 30, 31, 32, 33, 40


def _body(pos, hero=None, dead=False, allegiance=agents.ALLEGIANCE_PLAYER):
    row = {"name": "a body", "dead": dead, "died_at": 0.0, "health": 400.0,
           "max_health": 400.0, "last_hit": 0.0, "pos": pos, "plane": 0,
           "allegiance": allegiance, "attacks_back": False, "skills": (),
           "skill_ready": [], "last_swing": 0.0}
    if hero is not None:
        row["hero"] = hero
    return row


def _fake(far=(1500.0, 0.0)):
    sent = []
    send = lambda op, vals, why="", quiet=False: sent.append((op, list(vals)))   # noqa: E731
    st = {"agents": {}, "pos": (0.0, 0.0), "player_health": float(agents.PLAYER_HEALTH)}
    authsrv.player_pools(st)
    authsrv.effect_table(st)
    # A hero row carries its HERO ID (hero_body_id: the create entry's `hero`,
    # 6 = Koss and so on, never 0 -- effect_list_visible reads it as a truth).
    st["agents"][HERO] = _body((500.0, 0.0), hero=6)
    st["agents"][HENCH] = _body((300.0, 0.0))
    st["agents"][FAR_HERO] = _body(far, hero=7)
    st["agents"][DEAD_HERO] = _body((100.0, 0.0), hero=8, dead=True)
    st["agents"][FOE] = _body((200.0, 0.0), allegiance=agents.ALLEGIANCE_HOSTILE)
    return sent, send, st


def _wearing(st, skill):
    return sorted(ep["agent"] for ep in st["effects"].live.values() if ep["skill"] == skill)


def _ops_for(sent, agent, op):
    return [v for o, v in sent if o == op and v and v[0] == agent]


def section_sender():
    print("== 1. the sender: one episode per living ally in earshot ==")
    saved = (authsrv.PARTY_WIDE_SHOUTS, authsrv.EFFECTS, authsrv.MOVE_SPEED_EFFECTS,
             authsrv.EFFECT_LIST_SELF_ONLY)
    try:
        authsrv.PARTY_WIDE_SHOUTS = True
        authsrv.EFFECTS = True
        authsrv.MOVE_SPEED_EFFECTS = True
        authsrv.EFFECT_LIST_SELF_ONLY = True
        row = agents.WORLD.get("skill_effect", str(CHARGE))
        check(row.get("party_wide") == "earshot" and row.get("opens_episode") == "shout",
              "the 364 row: party_wide = earshot on a shout that opens an episode")
        srow = agents.WORLD.get("skills", str(CHARGE))
        check(float(srow.get("aoe_range") or 0) == 1000.0 and int(srow["type_code"]) == 15,
              "the client's own record for 364: type Shout, aoe_range 1000.0 (= WIKI earshot)",
              f"{srow.get('aoe_range')} type {srow.get('type_code')}")
        check(sorted(authsrv.allies_of(_fake()[2], P)) == [HERO, HENCH, FAR_HERO],
              "VACUITY GUARD: the fixture's living party is the hero, the henchman and the "
              "far hero (the dead hero and the foe are not allies)",
              f"{sorted(authsrv.allies_of(_fake()[2], P))}")

        # THE PLAYER SHOUTS.
        sent, send, st = _fake()
        ep = authsrv.apply_effect(send, st, P, CHARGE, 12, None, 0)
        check(ep is not None and ep["agent"] == P and ep["skill"] == CHARGE,
              "the primary episode is the caster's own")
        check(_wearing(st, CHARGE) == sorted([P, HERO, HENCH]),
              "the player's shout opens an episode on the player, the hero at 500 u and the "
              "henchman at 300 u -- not on the hero at 1500 u, the dead hero or the foe",
              f"{_wearing(st, CHARGE)}")
        buffs = {ep["agent"]: ep["buff"] for ep in st["effects"].live.values()}
        check(len(set(buffs.values())) == 3,
              "three episodes, three distinct buff ids", f"{buffs}")
        applies = [v for o, v in sent if o == APPLY]
        check([v[0] for v in applies] == [P, HERO]
              and all(v[1] == CHARGE for v in applies),
              "0x0042 goes out for the player and the hero (their effect lists are on the "
              "wire) and NOT for the henchman (MANTID: suppressed, counted)",
              f"{applies}")
        check(st.get("effect_list_suppressed", 0) == 1,
              "the henchman's apply is the one suppressed message",
              f"{st.get('effect_list_suppressed')}")
        for aid in (P, HERO, HENCH):
            base = authsrv.agent_speed_base(st, aid)
            words = _ops_for(sent, aid, SPEED)
            check(len(words) == 1 and abs(words[0][1] - base * 1.33) < 1e-3,
                  f"agent {aid} gets exactly one 0x0027 at base x 1.33 ({base:.0f} -> "
                  f"{base * 1.33:.2f}), the shout's +33 % (F48)", f"{words}")
        check(not _ops_for(sent, FAR_HERO, SPEED) and not _ops_for(sent, FOE, SPEED)
              and not _ops_for(sent, DEAD_HERO, SPEED),
              "no speed word for the far hero, the foe or the dead hero")
        for aid in (P, HERO):
            i_apply = next(i for i, (o, v) in enumerate(sent) if o == APPLY and v[0] == aid)
            i_speed = next(i for i, (o, v) in enumerate(sent) if o == SPEED and v[0] == aid)
            check(i_apply < i_speed,
                  f"agent {aid}: its 0x0042 precedes its 0x0027 (retail's per-wearer order)")

        # THE CURE ON AN ALLY: the hero is Crippled, the shout cures it.
        sent, send, st = _fake()
        authsrv.apply_condition(send, st, HERO, CRIPPLED, 9.0, 12, 0, 392)
        crip = [ep for ep in st["effects"].on_agent(HERO) if ep["skill"] == CRIPPLED]
        check(len(crip) == 1, "SETUP: the hero wears Crippled", f"{crip}")
        sent, send, st2 = sent, send, st
        del sent[:]
        authsrv.apply_effect(send, st2, P, CHARGE, 12, None, 0)
        check(not [ep for ep in st2["effects"].on_agent(HERO) if ep["skill"] == CRIPPLED]
              and any(o == REMOVE and v[0] == HERO and v[1] == crip[0]["buff"] for o, v in sent),
              "the player's shout cures the hero's Crippled: the episode closes and the "
              "hero's 0x0044 goes out (the row's `removes_condition`, per wearer)",
              f"{[v for o, v in sent if o == REMOVE]}")
        words = _ops_for(sent, HERO, SPEED)
        base = authsrv.agent_speed_base(st2, HERO)
        check(words and abs(words[-1][1] - base * 1.33) < 1e-3,
              "and the hero's last speed word is the boosted base, Crippled gone",
              f"{words}")

        # A HERO SHOUTS: the player is an ally and gets the apply -- retail's
        # 17 foreign applies on the observer.
        sent, send, st = _fake(far=(1600.0, 0.0))
        ep = authsrv.apply_effect(send, st, HERO, CHARGE, 12, None, 0)
        check(ep is not None and ep["agent"] == HERO, "the hero's own episode first")
        check(_wearing(st, CHARGE) == sorted([P, HERO, HENCH]),
              "a hero at (500, 0) shouting reaches the player at 500 u and the henchman "
              "at 200 u; the hero at 1100 u away is out of earshot",
              f"{_wearing(st, CHARGE)}")
        check([v[0] for v in [v for o, v in sent if o == APPLY]] == [HERO, P],
              "the hero's 0x0042 then the PLAYER's 0x0042 -- the foreign apply on the "
              "observer retail shows 17 times", f"{[v for o, v in sent if o == APPLY]}")

        # THE BOUNDARY IS INCLUSIVE.
        sent, send, st = _fake(far=(1000.0, 0.0))
        authsrv.apply_effect(send, st, P, CHARGE, 12, None, 0)
        check(FAR_HERO in _wearing(st, CHARGE), "an ally at exactly 1000 u is in earshot")
        sent, send, st = _fake(far=(1000.5, 0.0))
        authsrv.apply_effect(send, st, P, CHARGE, 12, None, 0)
        check(FAR_HERO not in _wearing(st, CHARGE), "an ally at 1000.5 u is not")

        # A STANCE REACHES NOBODY (no party_wide on its row).
        sent, send, st = _fake()
        authsrv.apply_effect(send, st, P, FRENZY, 0, None, 0)
        check(_wearing(st, FRENZY) == [P],
              "Frenzy (a stance, no party_wide) opens on the caster alone",
              f"{_wearing(st, FRENZY)}")

        # NO RADIUS / NO POSITION: nobody, and said so.
        sent, send, st = _fake()
        check(authsrv.shout_wearers(st, P, {"aoe_range": 0.0}, P, 0) == [],
              "a row carrying no aoe_range reaches nobody (no radius is guessed)")
        check(authsrv.shout_wearers(st, P, {}, P, 0) == [],
              "a row with no aoe_range key at all reaches nobody")
        st_nopos = dict(st)
        st_nopos.pop("pos", None)
        check(authsrv.shout_wearers(st_nopos, P, srow, P, 0) == [],
              "a caster with no known position reaches nobody")
        check(authsrv.shout_wearers(st, P, srow, P, 0) == [HERO, HENCH],
              "and with the real row and position: the hero and the henchman, sorted, "
              "the primary excluded", f"{authsrv.shout_wearers(st, P, srow, P, 0)}")

        # THE KNOWN-BAD ARM.
        authsrv.PARTY_WIDE_SHOUTS = False
        sent, send, st = _fake()
        authsrv.apply_effect(send, st, P, CHARGE, 12, None, 0)
        check(_wearing(st, CHARGE) == [P],
              "--no-party-wide-shouts: the caster alone -- the hero at 500 u gets NOTHING "
              "(the server as it was until 2026-09-23)", f"{_wearing(st, CHARGE)}")
        check([v[0] for v in [v for o, v in sent if o == APPLY]] == [P]
              and not _ops_for(sent, HERO, SPEED),
              "  and no 0x0042 or 0x0027 for the hero")
        authsrv.PARTY_WIDE_SHOUTS = True
        sent, send, st = _fake()
        authsrv.apply_effect(send, st, P, CHARGE, 12, None, 0)
        check(HERO in _wearing(st, CHARGE),
              "  the two arms differ on the hero (the A/B is an A/B)")
    finally:
        (authsrv.PARTY_WIDE_SHOUTS, authsrv.EFFECTS, authsrv.MOVE_SPEED_EFFECTS,
         authsrv.EFFECT_LIST_SELF_ONLY) = saved


def section_corpus():
    print("== 2. the tape: shoutjoin.census() on the live corpus ==")
    try:
        vaultpath.require_dir("captures", "live", why="test_shouts section 2")
    except (Exception, SystemExit) as exc:                          # noqa: BLE001
        LEDGER.skip("section 2 (the tape, 12 checks)", f"{type(exc).__name__}: {exc}")
        return
    import shoutjoin
    c = shoutjoin.census()
    cutoff = "20260923T235959"
    f = dict(c)
    f["applies"] = [r for r in c["applies"] if r["capture"] <= cutoff]
    f["reach"] = [r for r in c["reach"] if r["capture"] <= cutoff]
    s = shoutjoin.score(f)
    check(s["connections"] >= 96 and s["refused"] == 0,
          "96+ connections decode whole, none refused", f"{s['connections']} / {s['refused']}")
    check(s["on_observer_by_skill"] == {364: 48, 348: 11} and s["on_hero"] == 6,
          "on tapes to 2026-09-23: 48 applies of 364 and 11 of 348 on the observer, 6 on a "
          "hero (the survey's 65 in total)", f"{s['on_observer_by_skill']} hero {s['on_hero']}")
    check(s["self"] == 42 and s["other"] == 17 and s["other_plus_hero"] == 23,
          "42 the observer's own, 23 another ally's (17 + 6) -- the survey's split",
          f"self {s['self']} other {s['other']} (+hero {s['other_plus_hero']})")
    check(s["unattributed"] == 0 and s["p2"],
          "every apply has its [48, caster, skill] announce inside 1.5 s (P2)",
          f"unattributed {s['unattributed']}")
    check(s["prop60_control"] == 0,
          "CONTROL: no prop-60 announce carries a Shout id (the first cut looked there)",
          f"{s['prop60_control']}")
    check(s["p3"] and s["other_foe"] == 0 and s["other_side_unknown"] == 0,
          "every foreign apply on the observer is an ally's (P3)",
          f"ally {s['other_ally']} foe {s['other_foe']} unknown {s['other_side_unknown']}")
    check(s["foe_applied"] == 0 and s["reach_foe"] >= 8 and s["foe_within_earshot"] >= 4,
          "0 of the foe shouts applied, 4+ of them inside 1000 u (the exclusion is not "
          "vacuous)", f"foe {s['reach_foe']} applied {s['foe_applied']} within {s['foe_within_earshot']}")
    check(s["refuting"] == 0 and s["p4"],
          "no RESOLVED crossing of the 1000 u radius either way (P4)",
          f"refuting {s['refuting']} unresolved {s['unresolved']}")
    check(s["resolved_applied_max"] is not None and 900.0 <= s["resolved_applied_max"] <= 1000.0,
          "the largest resolved apply distance sits in [900, 1000] u -- the tape's lower "
          "bound on earshot", f"{s['resolved_applied_max']}")
    check(s["ally_applied_in"] >= 20 and s["unresolved"] >= 3,
          "20+ ally applies inside the radius; the crossings are inside their own error "
          "(stated, not fitted)", f"in {s['ally_applied_in']} unresolved {s['unresolved']}")
    check(s["p5"] and sorted(s["hero_dist"])[0] <= 1000.0,
          "the six hero applies are attributed (P5)", f"{s['hero_dist']}")
    check(s["p6"] and s["boost_words_on_others"] >= 80 and s["boost_words_on_foes"] == 0,
          "the observer's 364 batches carry 80+ boost words on OTHER party members and none "
          "on a foe-token agent (P6)", f"{s['boost_words_on_others']} / {s['boost_words_on_foes']}")


def main():
    section_sender()
    section_corpus()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
