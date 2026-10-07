r"""test_castgate -- CASTAI, the first cast-policy slice (2026-09-27; DESKWORK-D8 step 6,
studies/deskwork/PLAN.md; owner's ruling to be recorded as PLAN.md sec.7 Q19).

    python toolkit/authsrv/test_castgate.py

WHAT IT IS REALLY CHECKING. Two things shipped together, each behind its own revert:

  * THE LIVE-EFFECT GATE (authsrv.SKIP_LIVE_EFFECT, --no-skip-live-effect): a hostile
    or a party body HOLDS a slot whose effect the target it LANDS on already carries --
    a live same-skill hex / enchantment / weapon spell, or the condition a
    condition-only skill inflicts -- exactly the way SLICE-B3's heal gate holds (the
    cursor stepped past, a same-tick re-pick, the recharge not charged, a slot re-picked
    after being held ends the search). Round robin stays pick_skill's (a declared
    testing fixture, AST-locked by test_heroskilltoggle; this file never edits it).
    Evidence: WIKI GWW "Hero behavior" rev 2741080 (heroes); RECONSTRUCTION for a
    normal-mode monster (CASTAI-W2); OBSERVED 0 of 170 retail AI hex / enchantment
    casts on a live same-skill episode (castethogram; no informative HEX case exists)
    and stances NOT skipped (the JARIN hero's 346, 10 of 17 re-cast while live).
  * THE SELF-CAST WIRE FORM (authsrv.SELF_CAST_FORM, --self-cast-names-target): a cast
    landing on its own caster rides 0x009F [prop, caster, skill], and its property 61
    rides 0x00A2. OBSERVED: 417 of 417 self-kind [60] casts on 0x009F, 0 of 373 0x00A0
    [60] naming the caster (castethogram L1).

  1  the leaf predicate (episodemods.live_effect_class / carries_live_effect) on
     literal inputs -- every edge the docstring states; runs on a bare machine.
  2  (a) the Hatcher's bar (ENEMY_SKILL_BAR, {276, 253, 312, 289}) over a 120 s fight
     through the real ticks on a fake clock: never two live 253 episodes on the player,
     253 re-cast after every close, every slot fires, and after each close the gate's
     first look at 253 HOLDS it for one AI beat (LIVE_EFFECT_REARM, 0.25 s) and the
     first look past the beat lets it through and it is cast THAT tick; (a') a lone-253
     caster re-casts exactly 0.25 s (5 ticks) after each close -- never inside retail's
     0.228 s minimum (n=95) -- and its known-bad arm, --live-effect-rearm 0, re-casts on
     the close's own tick (gap 0, the slice as first shipped); the recharge never
     charged by a hold.
  3  (b) the KNOWN-BAD arm: --no-skip-live-effect gives the pre-CASTAI server's slot
     sequence exactly (the literal below was recorded by driving THIS fixture through
     a `git show 19213513:toolkit/authsrv/authsrv.py` export) and the stacked episodes
     come back.
  4  (c) a stance is refreshed while live, a hostile's and a hero's; (d) a
     self-enchantment is held while the CASTER carries it, and not while only the
     player does; (e) a party body through ally_cast_tick holds the same way and its
     known-bad arm stacks; (f) a condition-only skill is held while the target has
     the condition, a damage skill with a condition rider and an attack skill are not;
     (g) an all-held bar casts nothing, consults each slot once a tick (no spin), and
     resumes when the effect expires.
  5  (h) the self-cast form at every announce site: a hostile self-heal, a hostile
     self-kind non-heal, a hostile ALLY-kind non-heal (CASTAI-R2: Vital Blessing 289 lands
     on the caster, 0x009F and the caster visual; its known-bad arm, the player), a hero
     self-heal, a hero self-stance's [48], the player's own
     press with a foe selected; a targeted cast still rides 0x00A0; property 61
     follows the channel; the revert flag restores today's bytes; the legacy cast form
     is untouched; a rowless self cast (bare machine) rides 0x009F.
  6  (i) source checks: both flags in serverargs and flipped in main(); the gate is
     called from both loops and never from pick_skill; cast_anim_msg resolves the
     landing target.

Sections 2-5's driven halves need the vault's skills table. They declare a skip ONLY when
the vault is absent (vaultpath resolves no content/skills.toml); a present vault missing
a row, or with 253 not at 18 s, is a FAIL. The floor is the BARE-MACHINE green run's (see
the ledger line).
"""
import ast
import contextlib
import io
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
import content                                                 # noqa: E402
import effects                                                 # noqa: E402
import episodemods                                             # noqa: E402
import vaultpath                                               # noqa: E402

# Floor from the BARE-MACHINE green run (RURIK_VAULT=C:/nonexistent-vault), 2026-09-28,
# re-measured after CASTAI-R2: 36 -- section 1's predicate (20), section 5's rowless form
# (5, the legacy property-61 check added) and section 6's source checks (11: the re-arm's
# default and flag, and CASTAI-R2's flag). 81 with the vault; 82 since 2026-10-07 (section
# 2's after-close check runs on both NPC_AFTERCAST arms). A driven section skips ONLY
# when the vault is absent; a present vault missing a row is a FAIL (vault_skills /
# rows_problem).
LEDGER = checks.Ledger("cast gate (CASTAI)", floor=36)
check = checks.adopt(LEDGER)

P = authsrv.PLAYER_AGENT_ID
INT = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
INT_T = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET
FLT = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT
FLT_T = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET
SCOURGE, RESTORE, HOLY, VITAL = 253, 276, 312, 289
HEALING_SIGNET, FRENZY, FLAIL_STANCE = 1, 346, 10
SELF_ENCHANT = 180                   # type 6, target byte 0: lands on the caster
WINDBORNE = 160                      # type 6, target byte 3: the Isle friendly's re-cast
BLINDING_FLASH, IMMOLATE, SEVER = 220, 191, 382
AREA_POISON = 840                    # type 5, byte 0, a caster-centred area Poison
BLIND, BURNING, BLEEDING, POISON = 479, 480, 478, 484
HOSTILE, ALLY, HERO = 10, 11, 200
TICK = 0.05
T0 = 1_000_000.0
FLAGS = ("SKIP_LIVE_EFFECT", "SELF_CAST_FORM", "CAST_FORM", "ENERGY", "NPC_FOLLOW",
         "CASTER_OPENING", "CONDITION_HEAL_RULE", "EFFECTS", "INSTANT_ANNOUNCE",
         "LIVE_EFFECT_REARM", "HOSTILE_ALLY_SKILL_SELF", "NPC_AFTERCAST")
BEAT = 0.25                          # authsrv.LIVE_EFFECT_REARM's default, as a LITERAL

# THE KNOWN-BAD ARM'S LITERAL: the first 24 (tick index, skill) casts of fight(bar=the
# Hatcher's) on the pre-CASTAI server, recorded 2026-09-27 by driving this file's
# `fight` through an export of 19213513's authsrv.py (the scratch driver
# castai-impl/head_literal.py). The gate-off arm must reproduce it byte for byte:
# round robin's own sequence, with the 253s every ~6.3 s that stack on the player.
HEAD_SEQUENCE = None                 # filled in below from the recorded literal


class Clock:
    """A fake `time` module for authsrv: the ticks read `time.time()` and nothing else
    of it that matters; anything else falls through to the real module."""

    def __init__(self, t):
        self.t = t

    def time(self):
        return self.t

    def sleep(self, s):
        self.t += s

    def __getattr__(self, name):
        import time as _real
        return getattr(_real, name)


@contextlib.contextmanager
def arm(A=authsrv, clock=None, **flags):
    """Set the named module flags (and a fake clock) for the block, then restore."""
    saved = {k: getattr(A, k) for k in FLAGS if hasattr(A, k)}
    saved_time = A.time
    base = {"SKIP_LIVE_EFFECT": True, "SELF_CAST_FORM": True, "CAST_FORM": "follows-target",
            "ENERGY": False, "NPC_FOLLOW": False, "CASTER_OPENING": True,
            "CONDITION_HEAL_RULE": True, "EFFECTS": True, "INSTANT_ANNOUNCE": True,
            "LIVE_EFFECT_REARM": BEAT, "HOSTILE_ALLY_SKILL_SELF": True,
            "NPC_AFTERCAST": True}
    base.update(flags)
    for k, v in base.items():
        setattr(A, k, v)
    if clock is not None:
        A.time = clock
    try:
        yield
    finally:
        for k, v in saved.items():
            setattr(A, k, v)
        A.time = saved_time


def body(A, bar, allegiance, pos=(85.0, 0.0), health=100.0, attack_speed=None, **over):
    row = {"name": "caster", "dead": False, "died_at": 0.0, "health": health,
           "max_health": 100.0, "last_hit": 0.0, "pos": pos, "plane": 0,
           "allegiance": allegiance,
           "attack_speed": attack_speed if attack_speed is not None else A.ENEMY_ATTACK_SPEED,
           "effects": 0, "attacks_back": allegiance == agents.ALLEGIANCE_HOSTILE,
           "skills": tuple(tuple(s) for s in bar), "skill_ready": [0.0] * len(bar)}
    row.update(over)
    return row


def world(A, player_health=1e9):
    st = {"agents": {}, "pos": (0.0, 0.0), "player_health": player_health,
          "player_dead": False}
    A.effect_table(st)
    return st


def hatcher_world(A, bar=None):
    """test_agentlife's `_world_ally`: the Hatcher at 85 u and a HURT ally for its
    Restore Condition (a target-other-ally heal a lone hostile cannot cast)."""
    st = world(A)
    st["agents"][HOSTILE] = body(A, bar or A.ENEMY_SKILL_BAR, agents.ALLEGIANCE_HOSTILE)
    st["agents"][ALLY] = body(A, (), agents.ALLEGIANCE_HOSTILE, pos=(120.0, 40.0),
                              health=50.0, attacks_back=False)
    return st


def fight(A, st, secs, ticks=("effect_tick", "enemy_attack_tick", "ally_cast_tick"),
          watch=((P, SCOURGE),), keep_health=True, consults=None):
    """Drive the real ticks on the fake clock for `secs`. Returns a record:

      casts   [(tick index, agent, skill)] -- a slot's recharge moving IS a cast start
      live    {(wearer, skill): max live episodes seen}
      closes  {(wearer, skill): [tick index of each close]}
      early   {(wearer, skill): [tick index of each close BEFORE the episode's expiry]}
              -- a re-cast that REPLACED a live episode
      sends   [(tick index, op, vals)]
      log     the captured stdout
    """
    sends = []

    def send(op, vals, label="", quiet=False):
        sends.append((n_tick[0], op, list(vals)))

    n_tick = [0]
    casts, live, closes, early = [], {}, {}, {}
    prev_buffs = {w: {} for w in watch}
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        for i in range(int(round(secs / TICK))):
            n_tick[0] = i
            if keep_health:
                st["player_health"] = 1e9
            before = {aid: list(a.get("skill_ready") or ())
                      for aid, a in st["agents"].items()}
            for name in ticks:
                getattr(A, name)(send, st, 0)
            for aid, a in st["agents"].items():
                for slot, (b, now_r) in enumerate(zip(before.get(aid, ()),
                                                      a.get("skill_ready") or ())):
                    if now_r > b:
                        casts.append((i, aid, a["skills"][slot][0]))
            for (wearer, sk) in watch:
                buffs = {(e["buff"], e["applied_at"]): e["expires_at"]
                         for e in st["effects"].on_agent(wearer) if e["skill"] == sk}
                live[(wearer, sk)] = max(live.get((wearer, sk), 0), len(buffs))
                gone = set(prev_buffs[(wearer, sk)]) - set(buffs)
                if gone:
                    closes.setdefault((wearer, sk), []).append(i)
                    # an episode gone BEFORE its own expiry was replaced (a refresh)
                    if any(A.time.t < prev_buffs[(wearer, sk)][k] - 1e-6 for k in gone):
                        early.setdefault((wearer, sk), []).append(i)
                prev_buffs[(wearer, sk)] = buffs
            A.time.t += TICK
    return {"casts": casts, "live": live, "closes": closes, "early": early,
            "sends": sends, "log": out.getvalue()}


@contextlib.contextmanager
def recording_consults(A=authsrv):
    """Wrap authsrv.live_effect_hold (its callers look it up by name per call) and
    record (clock time, caster, skill, held?) for every consultation."""
    real = A.live_effect_hold
    seen = []

    def spy(state, caster_id, agent, skill_id, cast_target, now=None):
        out = real(state, caster_id, agent, skill_id, cast_target, now)
        seen.append((A.time.time(), caster_id, skill_id, out is not None))
        return out
    A.live_effect_hold = spy
    try:
        yield seen
    finally:
        A.live_effect_hold = real


# The rows each driven half reads. Sections 2-4 also need 253 at 18 s (the fight's
# expiry arithmetic); section 5 does not, so it has its own list and no duration test.
DRIVEN_ROWS = (SCOURGE, RESTORE, HOLY, VITAL, HEALING_SIGNET, FRENZY, FLAIL_STANCE,
               SELF_ENCHANT, WINDBORNE, BLINDING_FLASH, IMMOLATE, SEVER, AREA_POISON)
FORM_ROWS = (HEALING_SIGNET, SELF_ENCHANT, FRENZY, SCOURGE, VITAL)


def vault_skills():
    """The vault's skills table, or None when the VAULT is absent -- the one condition
    a driven half may skip on (the bare-machine rule). A vault that is present but
    lacks a row, or whose 253 is not 18 s, is a FAIL (rows_problem), never a skip:
    skipping on an odd RESULT is what let a vault-side drift pass green (TH-2)."""
    path = vaultpath.vault_path("content", "skills.toml")
    return path if os.path.isfile(path) else None


def rows_problem(ids, need_253_duration=False):
    """Why the loaded table cannot drive these rows, or None."""
    try:
        for sid in ids:
            agents.WORLD.get("skills", str(sid))
        if need_253_duration:
            row = agents.WORLD.get("skills", str(SCOURGE))
            got = effects.resolve_duration(row, authsrv.ENEMY_SKILL_RANK)
            if got != 18.0:
                return f"253's duration at the enemy rank is {got}, not 18 s"
        return None
    except content.ContentError as exc:
        return f"{exc}"


# ---------------------------------------------------------------------------------
def section_predicate():
    print("== 1. the leaf predicate, on literal inputs ==")
    cls = episodemods.live_effect_class
    check(cls(4) == "same-skill" and cls(6) == "same-skill" and cls(25) == "same-skill",
          "a hex (4), an enchantment (6) and a weapon spell (25) ask 'same skill live?'",
          f"{cls(4)} {cls(6)} {cls(25)}")
    check(cls(4, condition_id=BURNING, damages=True) == "same-skill",
          "  the TYPE decides first: a hex that also damages is still same-skill")
    for code, name in ((3, "stance"), (12, "glyph"), (19, "preparation"), (14, "attack"),
                       (15, "shout"), (16, "type 16")):
        check(cls(code) is None and cls(code, condition_id=BLIND) is None,
              f"a {name} ({code}) is NEVER held -- not even a condition-only one")
    check(cls(5, condition_id=BLIND) == "condition" and cls(10, condition_id=BLIND)
          == "condition" and cls(7, condition_id=BLEEDING) == "condition",
          "a condition-only spell / skill / signet asks 'condition live?'")
    check(cls(5, condition_id=BURNING, damages=True) is None,
          "a DAMAGE spell with a condition rider (Immolate's shape) is not held")
    check(cls(5, condition_id=BLIND, heals=True) is None,
          "a heal with a condition is not held")
    check(cls(5, condition_id=POISON, area=True) is None,
          "a caster-centred area condition (840's shape) is not held")
    check(cls(5) is None and cls(7) is None,
          "a plain spell / signet with no condition is not held")

    table = effects.EffectTable()
    table.apply(P, SCOURGE, 12, 18.0, 0.0, type_code=4, caster=HOSTILE)
    table.apply(P, BLIND, 0, 7.0, 0.0, type_code=8, caster=HOSTILE)
    table.apply(HOSTILE, SELF_ENCHANT, 12, 60.0, 0.0, type_code=6, caster=HOSTILE)
    car = episodemods.carries_live_effect
    check(car(table, P, SCOURGE, "same-skill") is not None,
          "a live 253 on the wearer: carried", f"{car(table, P, SCOURGE, 'same-skill')}")
    check(car(table, P, SELF_ENCHANT, "same-skill") is None,
          "  a skill live on SOMEBODY ELSE is not carried by this wearer")
    check(car(table, HOSTILE, SCOURGE, "same-skill") is None
          and car(table, P, 254, "same-skill") is None,
          "  nor a different skill on the wearer, nor the skill on another agent")
    table2 = effects.EffectTable()
    table2.apply(P, SCOURGE, 12, 18.0, 0.0, type_code=4, caster=ALLY)
    check(car(table2, P, SCOURGE, "same-skill") is not None,
          "  ANY caster: a 253 another body put on the player is carried too")
    check(car(table, P, BLINDING_FLASH, "condition", BLIND) is not None
          and car(table, P, BLINDING_FLASH, "condition", POISON) is None,
          "a live Blind is carried for a Blind skill; a Poison skill is not blocked by it")
    check(car(table, P, SCOURGE, None) is None and car(None, P, SCOURGE, "same-skill") is None,
          "no class or no table: never carried")
    b = table.on_agent(P)[0]["buff"]
    table.close(b)
    check(car(table, P, SCOURGE, "same-skill") is None,
          "a CLOSED episode is not carried -- the slot is eligible again")


# ---------------------------------------------------------------------------------
def _hatcher_fight(skip, secs=120.0, aftercast=True):
    with arm(clock=Clock(T0), SKIP_LIVE_EFFECT=skip, NPC_AFTERCAST=aftercast):
        st = hatcher_world(authsrv)
        with recording_consults() as seen:
            rec = fight(authsrv, st, secs)
    rec["consults"] = seen
    return rec


def _after_close(rec, n253, closes, looks, aftercast_aware):
    """(good, detail) for section 2's after-close check over one fight. With
    `aftercast_aware`, a go tick inside the hostile's aftercast -- a [58] of its within
    the 0.75 s before (NPC_AFTERCAST) -- owes no cast THAT tick; the gate's own facts
    are owed on every close either way."""
    f58 = [i for i, op, v in rec["sends"] if op == INT and v[:2] == [58, HOSTILE]]
    win = int(round(0.75 / TICK))
    good, detail = True, []
    for c in closes:
        tc = T0 + c * TICK - 1e-9
        after = [(t, held) for t, held in looks if t >= tc]
        if not after:
            continue
        t_first, held_first = after[0]
        inside = [held for t, held in after if t < t_first + BEAT - 1e-6]
        past = [(t, held) for t, held in after if t >= t_first + BEAT - 1e-6]
        if not past:
            continue
        t_go, held_go = past[0]
        k_go = int(round((t_go - T0) / TICK))
        cast_inside = [i for i in n253 if c <= i < k_go]
        cover = ([x for x in f58 if x <= k_go < x + win] if aftercast_aware else [])
        detail.append((c, int(round((t_first - T0) / TICK)), k_go, held_first,
                       all(inside), held_go, k_go in n253, cover[:1]))
        good = (good and held_first and all(inside) and not held_go
                and (k_go in n253 or bool(cover)) and not cast_inside)
    return good, detail


def section_hatcher():
    print("== 2. (a) the Hatcher's bar over a 120 s fight, the gate ON ==")
    if vault_skills() is None:
        LEDGER.skip("sections 2-4 (the driven fights): no vault",
                    f"no skills table at {vaultpath.vault_path('content', 'skills.toml')}")
        return False
    why = rows_problem(DRIVEN_ROWS, need_253_duration=True)
    check(why is None,
          "the vault is present, so its skills table carries every row sections 2-4 "
          "drive and 253 lasts 18 s at the enemy rank (a drift is a FAIL, not a skip)",
          f"{why}")
    if why:
        return False
    rec = _hatcher_fight(True)
    hat = [(i, s) for i, a, s in rec["casts"] if a == HOSTILE]
    n253 = [i for i, s in hat if s == SCOURGE]
    closes = rec["closes"].get((P, SCOURGE), [])
    check(rec["live"][(P, SCOURGE)] == 1,
          "the player NEVER carries two live 253 episodes (the known-bad arm peaks at 3)",
          f"max live {rec['live'][(P, SCOURGE)]}")
    check(len(n253) >= 5 and len(closes) >= 4,
          "and 253 keeps coming back: re-cast after its episodes close",
          f"{len(n253)} casts at ticks {n253}, closes at {closes}")
    recast_after = all(any(c <= i for c in closes) for i in n253[1:])
    ordered = all(sum(1 for c in closes if c <= i) == k
                  for k, i in enumerate(n253[1:], start=1))
    check(recast_after and ordered,
          "every re-cast of 253 starts AFTER the previous episode's close -- one close "
          "between each pair of casts", f"casts {n253} closes {closes}")
    fired = {s for _i, s in hat}
    check(fired == {RESTORE, SCOURGE, HOLY, VITAL},
          "every other slot still fires -- the hold steps the cursor past 253 rather "
          "than stalling the bar (DESKWORK-D8 step 4's lesson)",
          f"{sorted(fired)} counts {[sum(1 for _i, s in hat if s == k) for k in (RESTORE, SCOURGE, HOLY, VITAL)]}")
    # AFTER A CLOSE: THE FIRST LOOK HOLDS FOR ONE BEAT, THE FIRST LOOK PAST IT CASTS.
    # RE-AIMED 2026-10-07 (NPC_AFTERCAST, studies/skills 65): "cast on that very tick"
    # now also needs the body OUT of its aftercast -- a CLOCK gate after this WORLD gate
    # -- and on the default arm every go tick falls inside one (the Hatcher's 30-tick
    # cycle, 0.75 s cast + 0.75 s aftercast, puts a [58] on each close's tick). So the
    # check is run twice: on the default arm, the gate's own four facts on every close
    # AND the cast on the go tick wherever no aftercast covers it, the cover itself
    # named per close; and VERBATIM on --no-npc-aftercast, where all five go ticks cast.
    looks = [(t, held) for t, a, s, held in rec["consults"] if a == HOSTILE and s == SCOURGE]
    good, detail = _after_close(rec, n253, closes, looks, aftercast_aware=True)
    check(good and detail,
          "after each close the gate's FIRST look at 253 HOLDS it (the re-arm), every look "
          "inside the next 0.25 s holds, and the first look past the beat lets it through "
          "-- no 253 inside the beat -- and 253 is cast on that very tick unless the "
          "body's aftercast covers it (NPC_AFTERCAST's clock gate; named per close)",
          f"(close, first look, go tick, held first?, held inside?, held at go?, cast?, "
          f"covered by the [58] at tick) {detail}")
    rec_pre = _hatcher_fight(True, aftercast=False)
    n253_pre = [i for i, a, s in rec_pre["casts"] if a == HOSTILE and s == SCOURGE]
    closes_pre = rec_pre["closes"].get((P, SCOURGE), [])
    looks_pre = [(t, held) for t, a, s, held in rec_pre["consults"]
                 if a == HOSTILE and s == SCOURGE]
    good_pre, detail_pre = _after_close(rec_pre, n253_pre, closes_pre, looks_pre,
                                        aftercast_aware=False)
    check(good_pre and detail_pre,
          "  and under --no-npc-aftercast, verbatim: the first look past the beat lets it "
          "through and 253 is cast on that very tick, every close",
          f"{detail_pre}")
    held_while_live = sum(1 for _t, held in looks if held)
    check(held_while_live >= len(closes),
          "and the gate DID hold 253 while it was live (the arm is live, not vacuous)",
          f"{held_while_live} holds")
    lines = [ln for ln in rec["log"].splitlines() if "[CASTAI]" in ln]
    check(lines and all("holds skill 253" in ln and "already carries skill 253" in ln
                        and "the player" in ln for ln in lines)
          and len(lines) <= int(120.0 / 5.0) + 1,
          "its line names the skill, the target and 'already carries', at most once per "
          "5 s", f"{len(lines)} lines: {lines[:1]}")

    print("== 2. (a') a lone-253 caster re-casts ONE AI BEAT (0.25 s) after each close ==")

    def lone(rearm):
        with arm(clock=Clock(T0), LIVE_EFFECT_REARM=rearm):
            st = world(authsrv)
            st["agents"][HOSTILE] = body(authsrv, ((SCOURGE, 1.0, 5.0),),
                                         agents.ALLEGIANCE_HOSTILE, attack_speed=1e6)
            rec = fight(authsrv, st, 80.0)
        n253 = [i for i, a, s in rec["casts"] if a == HOSTILE and s == SCOURGE]
        closes = rec["closes"].get((P, SCOURGE), [])
        gaps = [min((i - c for i in n253 if i >= c), default=None) for c in closes]
        return rec, n253, closes, gaps

    rec, n253, closes, gaps = lone(BEAT)
    # The close's own tick carries the 0x0044 (effect_tick runs before the AI ticks), and
    # the lone slot is looked at every tick, so the re-cast's [60] trails the 0x0044 by
    # exactly the beat: 5 ticks of 50 ms. OBSERVED retail: 0 of 95 AI re-casts inside
    # 0.2 s of a same-skill end, minimum 0.228 s (castethogram-events.json; the Isle
    # friendly's 160, n=79: 0.228 / 0.236 / 0.249 s fastest per build). The beat is
    # RECONSTRUCTION (the ~0.25 s grid retail's AI casts sit on), not a measured constant.
    beat_ticks = int(round(BEAT / TICK))
    check(len(closes) >= 3 and all(g == beat_ticks for g in gaps)
          and all(g * TICK >= 0.228 for g in gaps),
          f"each re-cast starts exactly {BEAT} s ({beat_ticks} ticks) after the close -- never "
          f"inside retail's 0.228 s minimum (n=95 AI re-casts)",
          f"closes {closes} casts {n253} gaps(ticks) {gaps}")
    check(len(n253) == len(closes) + 1 and rec["live"][(P, SCOURGE)] == 1,
          "one cast per episode, never two live -- the recharge (5 s) is not what paces it",
          f"{len(n253)} casts, {len(closes)} closes")
    _rec0, n0, closes0, gaps0 = lone(0.0)
    check(len(closes0) >= 3 and all(g == 0 for g in gaps0),
          "KNOWN-BAD ARM, --live-effect-rearm 0: the re-cast rides the close's own tick "
          "(gap 0, its [60] in the 0x0044's batch) -- the slice as first shipped, faster than "
          "any retail AI re-cast", f"closes {closes0} casts {n0} gaps(ticks) {gaps0}")
    return True


# ---------------------------------------------------------------------------------
def section_known_bad():
    print("== 3. (b) the KNOWN-BAD arm: --no-skip-live-effect is the pre-CASTAI server ==")
    # HEAD_SEQUENCE was recorded on 19213513, which predates NPC_AFTERCAST (2026-10-07)
    # as well as CASTAI: the pre-CASTAI server is BOTH reverts, so this arm sets both
    # (re-aimed 2026-10-07; with the aftercast on, every cast after the first waits
    # 0.75 s past the previous [58] and the literal moves by exactly that).
    rec = _hatcher_fight(False, aftercast=False)
    hat = [(i, s) for i, a, s in rec["casts"] if a == HOSTILE]
    check(hat[:len(HEAD_SEQUENCE)] == HEAD_SEQUENCE,
          "the first 24 casts (tick, skill) equal 19213513's own -- round robin's sequence "
          "exactly as before", f"{hat[:len(HEAD_SEQUENCE)]}")
    check(rec["live"][(P, SCOURGE)] >= 2,
          "and the stacked episodes come back: overlapping 253s on the player",
          f"max live {rec['live'][(P, SCOURGE)]}")
    check(not any(held for _t, _a, _s, held in rec["consults"])
          and "[CASTAI]" not in rec["log"],
          "the gate holds nothing under the flag and prints nothing")


# ---------------------------------------------------------------------------------
def section_classes():
    print("== 4. (c) a stance is refreshed while live ==")
    with arm(clock=Clock(T0)):
        st = world(authsrv)
        st["agents"][HOSTILE] = body(authsrv, ((FLAIL_STANCE, 0.0, 15.0),),
                                     agents.ALLEGIANCE_HOSTILE, attack_speed=1e6)
        with recording_consults() as seen:
            rec = fight(authsrv, st, 50.0, watch=((HOSTILE, FLAIL_STANCE),))
    casts = [i for i, a, s in rec["casts"] if a == HOSTILE and s == FLAIL_STANCE]
    check(len(casts) >= 3 and not any(h for *_x, h in seen),
          "a hostile's stance (Flail 10: 65 s, recharge 15) is cast every recharge while "
          "its episode is live -- never held", f"casts at ticks {casts}")
    check(rec["live"][(HOSTILE, FLAIL_STANCE)] == 1
          and len(rec["early"].get((HOSTILE, FLAIL_STANCE), ())) >= 2,
          "and each re-cast REPLACES the live one (one at a time), the refresh retail's "
          "JARIN hero shows (0x0044 then a fresh 0x0042)",
          f"max live {rec['live'][(HOSTILE, FLAIL_STANCE)]} replaced before expiry at "
          f"{rec['early'].get((HOSTILE, FLAIL_STANCE))}")
    with arm(clock=Clock(T0)):
        st = world(authsrv)
        st["agents"][HERO] = body(authsrv, ((FRENZY, 0.0, 4.0),), agents.ALLEGIANCE_PLAYER,
                                  pos=(50.0, 0.0), health=40.0)
        rec = fight(authsrv, st, 20.0, watch=((HERO, FRENZY),))
    casts = [i for i, a, s in rec["casts"] if a == HERO and s == FRENZY]
    check(len(casts) >= 4 and rec["live"][(HERO, FRENZY)] == 1
          and len(rec["early"].get((HERO, FRENZY), ())) >= 3,
          "a HERO's stance (Frenzy 346: 8 s, recharge 4) is re-cast every recharge while "
          "live, each replacing the live one before its expiry, as the JARIN hero's was "
          "(10 of 17)", f"casts at {casts} replaced at {rec['early'].get((HERO, FRENZY))}")

    print("== 4. (d) a self-enchantment is held while the CASTER carries it ==")
    with arm(clock=Clock(T0)):
        st = world(authsrv)
        st["agents"][HOSTILE] = body(authsrv, ((SELF_ENCHANT, 0.25, 20.0),),
                                     agents.ALLEGIANCE_HOSTILE, attack_speed=1e6)
        rec = fight(authsrv, st, 59.0, watch=((HOSTILE, SELF_ENCHANT),))
        on = [i for i, a, s in rec["casts"] if s == SELF_ENCHANT]
        with arm(clock=Clock(T0), SKIP_LIVE_EFFECT=False):
            st2 = world(authsrv)
            st2["agents"][HOSTILE] = body(authsrv, ((SELF_ENCHANT, 0.25, 20.0),),
                                          agents.ALLEGIANCE_HOSTILE, attack_speed=1e6)
            rec2 = fight(authsrv, st2, 59.0, watch=((HOSTILE, SELF_ENCHANT),))
        off = [i for i, a, s in rec2["casts"] if s == SELF_ENCHANT]
    check(len(on) == 1 and rec["live"][(HOSTILE, SELF_ENCHANT)] == 1,
          "a hostile's 180 (60 s, recharge 20) is cast ONCE in 59 s -- held while it "
          "carries it", f"casts {on}")
    check(len(off) == 3 and rec2["live"][(HOSTILE, SELF_ENCHANT)] >= 2,
          "  the known-bad arm casts it every recharge onto itself, stacking",
          f"casts {off} max live {rec2['live'][(HOSTILE, SELF_ENCHANT)]}")
    with arm(clock=Clock(T0)):
        st = world(authsrv)
        ag = body(authsrv, ((SELF_ENCHANT, 0.25, 20.0),), agents.ALLEGIANCE_HOSTILE)
        st["agents"][HOSTILE] = ag
        st["effects"].apply(P, SELF_ENCHANT, 12, 60.0, T0, type_code=6, caster=99)
        on_player = authsrv.live_effect_hold(st, HOSTILE, ag, SELF_ENCHANT, P)
        st["effects"].apply(HOSTILE, SELF_ENCHANT, 12, 60.0, T0, type_code=6, caster=HOSTILE)
        on_caster = authsrv.live_effect_hold(st, HOSTILE, ag, SELF_ENCHANT, P)
    check(on_player is None,
          "  THE LANDING TARGET: with 180 live on the PLAYER only (the cast_target a "
          "hostile's self-kind skill keeps), the caster is bare and nothing is held")
    check(on_caster is not None and on_caster[0] == HOSTILE,
          "  and with it live on the caster the hold names the CASTER as the wearer",
          f"{on_caster}")

    print("== 4. (e) a party body through ally_cast_tick holds the same way ==")
    runs = {}
    for skip in (True, False):
        with arm(clock=Clock(T0), SKIP_LIVE_EFFECT=skip):
            st = world(authsrv, player_health=40.0)
            st["agents"][HERO] = body(authsrv, ((WINDBORNE, 0.75, 5.0),),
                                      agents.ALLEGIANCE_PLAYER, pos=(50.0, 0.0))
            runs[skip] = fight(authsrv, st, 40.0, keep_health=False,
                               watch=((P, WINDBORNE),))
    on = [i for i, a, s in runs[True]["casts"] if a == HERO]
    closes = runs[True]["closes"].get((P, WINDBORNE), [])
    check(runs[True]["live"][(P, WINDBORNE)] == 1 and len(on) >= 3
          and all(sum(1 for c in closes if c <= i) == k for k, i in enumerate(on)),
          "a hero's Windborne Speed (160: 11 s, recharge 5) on the hurt player: never two "
          "live, one close between each pair of casts", f"casts {on} closes {closes}")
    check(any("party agent 200 holds skill 160" in ln and "already carries" in ln
              for ln in runs[True]["log"].splitlines()),
          "  its line names the party agent, the skill and 'already carries'")
    check(runs[False]["live"][(P, WINDBORNE)] >= 2,
          "  the known-bad arm stacks it on the player",
          f"max live {runs[False]['live'][(P, WINDBORNE)]}")

    print("== 4. (f) a condition-only skill is held while the target has the condition ==")
    def one_tick(bar, pre):
        with arm(clock=Clock(T0)):
            st = world(authsrv)
            ag = body(authsrv, bar, agents.ALLEGIANCE_HOSTILE, attack_speed=1e6)
            st["agents"][HOSTILE] = ag
            for cond in pre:
                st["effects"].apply(P, cond, 0, 30.0, T0, type_code=8, caster=99)
            rec = fight(authsrv, st, TICK, watch=())
            return [s for _i, a, s in rec["casts"] if a == HOSTILE], ag, st
    casts, ag, st = one_tick(((BLINDING_FLASH, 0.75, 8.0),), (BLIND,))
    check(not casts and ag.get("last_slot") == 0 and ag["skill_ready"] == [0.0],
          "Blinding Flash (220, Blind only) at a player who is Blind: HELD -- the cursor "
          "stepped, the recharge not charged", f"casts {casts} ready {ag['skill_ready']}")
    casts, _ag, _st = one_tick(((BLINDING_FLASH, 0.75, 8.0),), (POISON,))
    check(casts == [BLINDING_FLASH],
          "  the same skill at a Poisoned (not Blind) player is cast", f"{casts}")
    casts, _ag, _st = one_tick(((IMMOLATE, 1.0, 5.0),), (BURNING,))
    check(casts == [IMMOLATE],
          "Immolate (191: damage + a Burning rider) at a Burning player is cast -- a "
          "rider does not hold a damage skill", f"{casts}")
    # the wrapper's `area=` fact, driven (TH-1): 840 is a condition-only Poison with no
    # damage and no heal, so ONLY caster_area_row keeps it out of the condition class --
    # dropping the fact holds it here while §1's literal inputs stay green.
    casts, _ag, _st = one_tick(((AREA_POISON, 0.25, 12.0),), (POISON,))
    check(casts == [AREA_POISON],
          "840 (a caster-centred area Poison) at a Poisoned player is cast -- the wrapper "
          "passes the area fact, and one target's Poison says nothing about the rest",
          f"{casts}")
    with arm():
        st = world(authsrv)
        ag = body(authsrv, ((SEVER, 0.0, 0.0),), agents.ALLEGIANCE_HOSTILE)
        st["effects"].apply(P, BLEEDING, 0, 30.0, 0.0, type_code=8, caster=99)
        held = authsrv.live_effect_hold(st, HOSTILE, ag, SEVER, P)
    check(held is None,
          "an ATTACK skill (Sever Artery 382, Bleeding only) at a Bleeding player is not "
          "held -- the swing's business", f"{held}")

    print("== 4. (g) an all-held bar casts nothing, does not spin, and resumes ==")
    with arm(clock=Clock(T0)):
        st = world(authsrv)
        # an ordinary swing clock: with nothing castable the body swings between the
        # looks, which is the fall-through the heal gate's hold has always had
        ag = body(authsrv, ((SCOURGE, 1.0, 5.0), (SCOURGE, 1.0, 5.0)),
                  agents.ALLEGIANCE_HOSTILE)
        st["agents"][HOSTILE] = ag
        st["effects"].apply(P, SCOURGE, 12, 3.0, T0, type_code=4, caster=99)
        with recording_consults() as seen:
            rec = fight(authsrv, st, 3.0 - TICK / 2, watch=((P, SCOURGE),))
            per_tick = {}
            for t, *_x in seen:
                per_tick[round(t, 6)] = per_tick.get(round(t, 6), 0) + 1
            n_ticks = len(per_tick)
            ready_during = list(ag["skill_ready"])
            swing_bound = authsrv.swing_windup(authsrv.ENEMY_ATTACK_SPEED) + 2 * TICK
            rec2 = fight(authsrv, st, 2.0, watch=((P, SCOURGE),))
    check(not [c for c in rec["casts"] if c[1] == HOSTILE] and ready_during == [0.0, 0.0],
          "both slots held for the whole 3 s the hex is live: nothing cast, neither "
          "recharge charged", f"casts {rec['casts']} ready {ready_during}")
    check(n_ticks >= 10 and max(per_tick.values()) == 2,
          "each tick consults each slot ONCE -- two looks a tick, the search ends on the "
          "slot it already held (no spin)", f"{n_ticks} ticks, max looks/tick "
          f"{max(per_tick.values())}")
    check([s for _i, a, s in rec2["casts"] if a == HOSTILE][:1] == [SCOURGE]
          and rec2["casts"][0][0] * TICK <= swing_bound,
          "and once the hex expires the bar resumes with a 253 -- past the 0.25 s re-arm "
          "beat, inside one swing's windup of the close",
          f"{rec2['casts'][:2]}")


# ---------------------------------------------------------------------------------
def _announces(sends):
    return [(op, v) for _i, op, v in sends
            if v and v[0] in (agents.GV_SKILL_ACTIVATED, agents.GV_INSTANT_SKILL_ACTIVATED)
            and op in (INT, INT_T)]


def _start(bar, allegiance, health=100.0, self_form=True, player_health=1e9, secs=TICK,
           ticks=("enemy_attack_tick", "ally_cast_tick"), pos=(85.0, 0.0), who=None):
    who = who or (HOSTILE if allegiance == agents.ALLEGIANCE_HOSTILE else HERO)
    with arm(clock=Clock(T0), SELF_CAST_FORM=self_form):
        st = world(authsrv, player_health=player_health)
        st["agents"][who] = body(authsrv, bar, allegiance, pos=pos, health=health,
                                 attack_speed=1e6)
        rec = fight(authsrv, st, secs, ticks=("effect_tick",) + ticks, watch=(),
                    keep_health=False)
    return _announces(rec["sends"])


def section_self_form():
    print("== 5. (h) the self-cast wire form ==")
    # the rowless case first -- it runs on a bare machine
    with arm():
        op, vals = authsrv.cast_anim_msg(agents.GV_SKILL_ACTIVATED, 5, 5, 999999)
    check((op, vals) == (INT, [60, 5, 999999]),
          "a ROWLESS cast whose target is its own caster rides 0x009F [60, caster, skill] "
          "-- retail never names the caster as its own target (L1)", f"{hex(op)} {vals}")
    with arm(SELF_CAST_FORM=False):
        op, vals = authsrv.cast_anim_msg(agents.GV_SKILL_ACTIVATED, 5, 5, 999999)
    check((op, vals) == (INT_T, [60, 5, 5, 999999]),
          "  --self-cast-names-target restores 0x00A0 naming it", f"{hex(op)} {vals}")
    with arm():
        op, vals = authsrv.cast_anim_msg(agents.GV_SKILL_ACTIVATED, 5, 7, 999999)
        op0, vals0 = authsrv.cast_anim_msg(agents.GV_SKILL_ACTIVATED, 5, 0, 999999)
    check((op, vals) == (INT_T, [60, 5, 7, 999999]) and (op0, vals0) == (INT, [60, 5, 999999]),
          "  a rowless cast at another agent still names it; target 0 still rides 0x009F")
    with arm(CAST_FORM="legacy"):
        op, vals = authsrv.cast_anim_msg(agents.GV_SKILL_ACTIVATED, 5, 5, 999999)
    check((op, vals) == (INT_T, [60, 5, 5, 999999]),
          "  the LEGACY cast form is untouched: always 0x00A0 with the site's target")
    # ... and so is its property 61 (TH-3). A rowless skill's record activation is
    # skill_timing's bare fallback 0.0, so a 2.0 s cast carries the word on either
    # machine; the self cast (target == caster) is the case the two forms split on.
    words = {}
    for form in ("legacy", "follows-target"):
        with arm(CAST_FORM=form):
            sent = []
            with contextlib.redirect_stdout(io.StringIO()):
                authsrv.cast_time_word(lambda op, vals, why="": sent.append((op, list(vals))),
                                       5, 5, 999999, 2.0, "a test")
        words[form] = [(o, v[:3]) for o, v in sent]
    check(words["legacy"] == [(FLT_T, [agents.GV_CASTTIME, 5, 5])]
          and words["follows-target"] == [(FLT, [agents.GV_CASTTIME, 5,
                                                 authsrv._f32(2.0)])],
          "  and the legacy form's property 61 keeps the site's target (0x00A3 [61, 5, 5]) "
          "where the default self cast rides 0x00A2 [61, 5, secs]",
          f"{[(k, [(hex(o), v) for o, v in w]) for k, w in words.items()]}")
    if vault_skills() is None:
        LEDGER.skip("section 5's driven half: no vault",
                    f"no skills table at {vaultpath.vault_path('content', 'skills.toml')}")
        return
    why = rows_problem(FORM_ROWS)
    check(why is None,
          "the vault is present, so its skills table carries every row section 5 drives "
          "(a missing row is a FAIL, not a skip)", f"{why}")
    if why:
        return
    a = _start(((HEALING_SIGNET, 2.0, 4.0),), agents.ALLEGIANCE_HOSTILE, health=40.0)
    b = _start(((HEALING_SIGNET, 2.0, 4.0),), agents.ALLEGIANCE_HOSTILE, health=40.0,
               self_form=False)
    check(a == [(INT, [60, HOSTILE, HEALING_SIGNET])]
          and b == [(INT_T, [60, HOSTILE, HOSTILE, HEALING_SIGNET])],
          "a hurt HOSTILE's self-heal (Healing Signet 1): 0x009F [60, 10, 1]; the revert "
          "restores today's 0x00A0 [60, 10, 10, 1]", f"{a} / {b}")
    a = _start(((SELF_ENCHANT, 0.25, 20.0),), agents.ALLEGIANCE_HOSTILE)
    b = _start(((SELF_ENCHANT, 0.25, 20.0),), agents.ALLEGIANCE_HOSTILE, self_form=False)
    check(a == [(INT, [60, HOSTILE, SELF_ENCHANT])]
          and b == [(INT_T, [60, HOSTILE, P, SELF_ENCHANT])],
          "a hostile's self-kind NON-heal (180): its cast_target stays the player, its "
          "effect lands on itself, and the announce now follows the LANDING -- 0x009F; "
          "the revert restores 0x00A0 naming the player", f"{a} / {b}")
    # CASTAI-R2: a hostile's ALLY-kind non-heal (Vital Blessing 289, byte 3) lands on the
    # CASTER; the known-bad arm is the player (every run before 2026-09-28). OBSERVED
    # retail: a monster's ally-kind enchantment 4 of 4 on itself. 289 opens NO episode
    # (its duration slot is a sentinel apply_effect declines, loudly), so what the landing
    # changes on the wire is the announce and the visual: on the caster it is the caster
    # form 0x009F [21, caster, id], never a [20] naming the player (send_skill_visual's
    # rule). 0.75 s is the record's activation, so no property 61 rides along.
    vb = {}
    for on in (True, False):
        with arm(clock=Clock(T0), HOSTILE_ALLY_SKILL_SELF=on):
            st = world(authsrv)
            st["agents"][HOSTILE] = body(authsrv, ((VITAL, 0.75, 5.0),),
                                         agents.ALLEGIANCE_HOSTILE, attack_speed=1e6)
            rec = fight(authsrv, st, 2.0, ticks=("effect_tick", "enemy_attack_tick"),
                        watch=(), keep_health=True)
            vb[on] = (_announces(rec["sends"]),
                      [(op, v[:2]) for _i, op, v in rec["sends"]
                       if v and v[0] in (agents.GV_EFFECT_ON_TARGET, 21)],
                      [v for _i, op, v in rec["sends"] if v and v[0] == 61])
    check(vb[True][0] == [(INT, [60, HOSTILE, VITAL])]
          and vb[True][1] == [(INT, [21, HOSTILE])] and not vb[True][2],
          "a hostile's ally-kind NON-heal (Vital Blessing 289) lands on ITSELF: 0x009F "
          "[60, 10, 289] and the caster visual 0x009F [21, 10, ...] -- no [20] naming the "
          "player", f"{vb[True]}")
    check(vb[False][0] == [(INT_T, [60, HOSTILE, P, VITAL])]
          and vb[False][1] == [(INT_T, [20, P])],
          "  KNOWN-BAD, --hostile-ally-skill-at-player: 0x00A0 [60, 10, 1, 289] and the "
          "visual [20, 1, 10, ...] on the PLAYER (a foe shown blessing its enemy)",
          f"{vb[False]}")
    a = _start(((HEALING_SIGNET, 2.0, 4.0),), agents.ALLEGIANCE_PLAYER, health=40.0,
               pos=(50.0, 0.0))
    b = _start(((HEALING_SIGNET, 2.0, 4.0),), agents.ALLEGIANCE_PLAYER, health=40.0,
               pos=(50.0, 0.0), self_form=False)
    check(a == [(INT, [60, HERO, HEALING_SIGNET])]
          and b == [(INT_T, [60, HERO, HERO, HEALING_SIGNET])],
          "a hurt HERO's self-heal through ally_cast_tick: 0x009F [60, 200, 1]; the "
          "revert restores 0x00A0 [60, 200, 200, 1]", f"{a} / {b}")
    a = _start(((FRENZY, 0.0, 4.0),), agents.ALLEGIANCE_PLAYER, health=40.0,
               pos=(50.0, 0.0), secs=3 * TICK)
    check(a == [(INT, [agents.GV_INSTANT_SKILL_ACTIVATED, HERO, FRENZY])],
          "a hero's self-STANCE rides 0x009F [48, 200, 346] at its landing and nothing "
          "names the hero as its own target (SKILLS-IA's instant form, unchanged)", f"{a}")
    a = _start(((SCOURGE, 1.0, 5.0),), agents.ALLEGIANCE_HOSTILE)
    b = _start(((SCOURGE, 1.0, 5.0),), agents.ALLEGIANCE_HOSTILE, self_form=False)
    check(a == b == [(INT_T, [60, HOSTILE, P, SCOURGE])],
          "a TARGETED cast (253 at the player) still rides 0x00A0 [60, 10, 1, 253], both "
          "arms", f"{a} / {b}")
    # the player's own press, a self skill with a FOE selected
    for form, want in ((True, [(INT, [60, P, HEALING_SIGNET])]),
                       (False, [(INT_T, [60, P, 40, HEALING_SIGNET])])):
        with arm(SELF_CAST_FORM=form):
            sent = []
            st = {"agents": {}, "pos": (0.0, 0.0),
                  "player_health": float(agents.PLAYER_HEALTH)}
            authsrv.player_pools(st)
            authsrv.effect_table(st)
            st["agents"][40] = body(authsrv, (), agents.ALLEGIANCE_HOSTILE, pos=(200.0, 0.0),
                                    attacks_back=False)
            with contextlib.redirect_stdout(io.StringIO()):
                authsrv.handle_skill_press(
                    [0, HEALING_SIGNET, 7, 40],
                    lambda op, vals, why="", quiet=False: sent.append((0, op, list(vals))),
                    st, 0, authsrv.GAME_CMSG_USE_SKILL)
        got = _announces(sent)
        check(got == want,
              ("the PLAYER's Healing Signet pressed with a foe selected rides 0x009F [60, "
               "1, 1] -- the observer's own 26 of 26 byte-0 casts do" if form else
               "  the revert restores 0x00A0 [60, 1, 40, 1] naming the foe"), f"{got}")
    # property 61 follows the channel
    for form, want_op in ((True, FLT), (False, FLT_T)):
        with arm(SELF_CAST_FORM=form):
            sent = []
            authsrv.cast_time_word(lambda op, vals, why="": sent.append((op, list(vals))),
                                   HOSTILE, P, HEALING_SIGNET, 4.0, "a test")
        check(len(sent) == 1 and sent[0][0] == want_op
              and sent[0][1][:2] == [agents.GV_CASTTIME, HOSTILE]
              and (len(sent[0][1]) == 3) == form,
              ("a modified self cast's property 61 rides 0x00A2 [61, caster, secs], "
               "beside its 0x009F" if form else
               "  the revert restores 0x00A3 [61, caster, target, secs]"),
              f"{[(hex(o), v) for o, v in sent]}")
    with arm():
        sent = []
        authsrv.cast_time_word(lambda op, vals, why="": sent.append((op, list(vals))),
                               HOSTILE, P, SCOURGE, 2.0, "a test")
    check(len(sent) == 1 and sent[0][0] == FLT_T and sent[0][1][:3] == [
              agents.GV_CASTTIME, HOSTILE, P],
          "  a TARGETED modified cast's 61 still rides 0x00A3 naming the target",
          f"{[(hex(o), v) for o, v in sent]}")


# ---------------------------------------------------------------------------------
def _func(tree, name):
    return next(n for n in ast.walk(tree)
                if isinstance(n, ast.FunctionDef) and n.name == name)


def _calls(fn, name):
    return [n for n in ast.walk(fn) if isinstance(n, ast.Call)
            and getattr(n.func, "id", getattr(n.func, "attr", None)) == name]


def _flips(main_fn, attr, glob):
    """True when main() holds `if a.<attr>:` whose body sets `<glob> = False`."""
    for n in ast.walk(main_fn):
        if (isinstance(n, ast.If) and isinstance(n.test, ast.Attribute)
                and n.test.attr == attr):
            for s in n.body:
                if (isinstance(s, ast.Assign) and any(getattr(t, "id", None) == glob
                                                       for t in s.targets)
                        and isinstance(s.value, ast.Constant) and s.value.value is False):
                    return True
    return False


def section_source():
    print("== 6. (i) source checks ==")
    src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
    args = open(os.path.join(HERE, "serverargs.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    check('"--no-skip-live-effect"' in args and '"--self-cast-names-target"' in args,
          "serverargs defines --no-skip-live-effect and --self-cast-names-target")
    main_fn = _func(tree, "main")
    check(_flips(main_fn, "no_skip_live_effect", "SKIP_LIVE_EFFECT"),
          "main() flips SKIP_LIVE_EFFECT off under --no-skip-live-effect")
    check(_flips(main_fn, "self_cast_names_target", "SELF_CAST_FORM"),
          "main() flips SELF_CAST_FORM off under --self-cast-names-target")
    check(authsrv.SKIP_LIVE_EFFECT is True and authsrv.SELF_CAST_FORM is True,
          "both default ON at import")
    check('"--hostile-ally-skill-at-player"' in args
          and _flips(main_fn, "hostile_ally_skill_at_player", "HOSTILE_ALLY_SKILL_SELF")
          and authsrv.HOSTILE_ALLY_SKILL_SELF is True,
          "CASTAI-R2's flag: --hostile-ally-skill-at-player in serverargs, flipped in main(), "
          "the self landing ON at import")
    main_src = ast.get_source_segment(src, main_fn)
    check('"--live-effect-rearm"' in args
          and "LIVE_EFFECT_REARM = a.live_effect_rearm" in main_src
          and authsrv.LIVE_EFFECT_REARM == BEAT,
          "the re-arm beat defaults to 0.25 s at import (the literal, not the module's own "
          "value) and --live-effect-rearm sets it in main()",
          f"{authsrv.LIVE_EFFECT_REARM}")
    check(len(_calls(_func(tree, "enemy_attack_tick"), "live_effect_hold")) == 1
          and len(_calls(_func(tree, "ally_cast_tick"), "live_effect_hold")) == 1,
          "the gate is called once from each loop -- the hostile's and the party's")
    check(not _calls(_func(tree, "pick_skill"), "live_effect_hold")
          and "live_effect" not in ast.get_source_segment(src, _func(tree, "pick_skill")),
          "and never from pick_skill: the selector stays the testing fixture")
    check(len(_calls(_func(tree, "cast_anim_msg"), "cast_announce_target")) == 1
          and len(_calls(_func(tree, "cast_time_word"), "cast_announce_target")) == 1,
          "cast_anim_msg and cast_time_word resolve the LANDING target -- one place each")
    eat = _func(tree, "enemy_attack_tick")
    seg = ast.get_source_segment(src, eat)
    i_gate = seg.find("live_effect_hold(")
    i_heal = seg.find("hostile_heal_target(state, agent_id, _kind)")
    i_reach = seg.find("_caster_skill_reach(agent, _sid)")
    i_pay = seg.find("_pool.can_pay(_cost)")
    check(0 <= i_heal < i_gate < i_reach < i_pay,
          "in the hostile loop the gate sits after the target gate resolves the landing "
          "and before the reach and resource gates (world gates before clock gates, RV-1)",
          f"heal {i_heal} gate {i_gate} reach {i_reach} pay {i_pay}")
    sites = [n for n in _calls(tree, "cast_anim_msg")]
    check(len(sites) == 4,
          "four announce sites call cast_anim_msg (two player press sites, the hostile, "
          "the party) -- so the self form reaches every one", f"{len(sites)}")


HEAD_SEQUENCE = [
    # (tick index, skill) -- 19213513, fight(Hatcher bar), gate absent. See the banner.
    (0, 276), (16, 253), (37, 312), (53, 289), (69, 276), (109, 289), (125, 276),
    (141, 253), (164, 289), (180, 276), (220, 312), (236, 289), (252, 276), (268, 253),
    (291, 289), (307, 276), (347, 289), (363, 276), (388, 253), (409, 312), (425, 289),
    (441, 276), (481, 289), (497, 276),
]


def main():
    section_predicate()
    if section_hatcher():
        section_known_bad()
        section_classes()
    section_self_form()
    section_source()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
