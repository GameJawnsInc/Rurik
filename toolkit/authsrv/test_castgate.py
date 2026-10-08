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
     through the real ticks on a fake clock, in the SHIPPING configuration (the removal
     gate ON, as every gate here is): never two live 253 episodes on the player, 253
     re-cast after every close, 276 never cast at the clean squad and every OTHER slot
     fires, and after each close the gate's first look at 253 HOLDS it for one AI beat
     (LIVE_EFFECT_REARM, 0.25 s) and the first look past the beat lets it through and it
     is cast THAT tick; (a') a lone-253 caster re-casts exactly 0.25 s (5 ticks) after
     each close -- never inside retail's 0.228 s minimum (n=95) -- and its known-bad arm,
     --live-effect-rearm 0, re-casts on the close's own tick (gap 0, the slice as first
     shipped); the recharge never charged by a hold.
  3  (b) the KNOWN-BAD arm: --no-skip-live-effect with --no-removal-needs-affliction (the
     pre-CASTAI server had neither gate) gives that server's slot sequence exactly (the
     literal below was recorded by driving THIS fixture through a `git show
     19213513:toolkit/authsrv/authsrv.py` export) and the stacked episodes come back.
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
  7  CASTAI-RM (2026-10-07; studies/monsterai 18.5): THE REMOVAL GATE
     (authsrv.REMOVAL_NEEDS_AFFLICTION, --no-removal-needs-affliction) -- a removal slot
     (275 / 276 / 277 cure conditions, 301 removes a hex) aims at an ally CARRYING what
     it removes, at any health, and is HELD (the heal hold's way) when nobody does. On
     CARRIED rows (RM_RECORD), so it runs on a bare machine: (a) the predicates
     (episodemods.removal_class / carries_removable) on literal inputs and on the shipped
     hand rows; (b) removal_target's candidates and order; (c) a hostile and a hero with
     [276, 281] and a hurt CLEAN ally cast only 281 (276 held, uncharged, one look a tick
     -- every driven tick runs pick_skill under a counter that raises past len(bar) + 1,
     so a hold that forgot `_held` is a FAIL by name, not a hang); (d) Bleeding planted:
     276 lands, removes it, heals once -- and at 100 % health too; (e) two allies, the
     afflicted one named over the hurt-most clean one; (f) 277 cures its own caster, 276
     never -- in the hostile loop AND the party loop (a hero's 277 on its own Bleeding,
     a hero's 301 on its own hex); (g) a hero cures the bleeding player at full health;
     (h) 301 held with no hex, the NEWEST of two removed, the [7]s and the 0x800 clear only
     with the last, an Incendiary Bonds removed fires no end burst (a control shows the
     expiry path does), a removed Suffering (a hex with pips) sends its [44] back to 0,
     a removed Deep Freeze (a hex with a snare) declares the 0x0027 base back;
     (i) KNOWN-BAD ARM: the flag off reproduces 642d8957's bytes (RM_HEAD) -- the 276
     fights, and a hero's 301 at a hexed player and a self-hexed hostile's 301, which
     remove nothing there; (j) source checks.
  8  (vault-only) (a) the carried rows against the vault's own; (b) the RETAIL removal
     casts (castethogram over the two Zaishen tapes) replayed through removal_target:
     it holds 0 of 116 and names retail's target each time; KNOWN-BAD ARM, the pre-gate
     heal rule (hostile_heal_target, real server code) over the same casts, refuses
     every one at a target at 0.9 or above: 2 of 92 275s and 5 of 10 301s.

Sections 2-5's driven halves need the vault's skills table. They declare a skip ONLY when
the vault is absent (vaultpath resolves no content/skills.toml); a present vault missing
a row, or with 253 not at 18 s, is a FAIL. The floor is per machine, decided on the
vault's content DIRECTORY (see the ledger line).
"""
import ast
import contextlib
import io
import os
import struct
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
# default and flag, and CASTAI-R2's flag). 81 with the vault; 83 since 2026-10-07 (section
# 2's after-close check runs on both NPC_AFTERCAST arms, and ON_SEQUENCE pins the default
# arm's cadence). A driven section skips ONLY
# when the vault is absent; a present vault missing a row is a FAIL (vault_skills /
# rows_problem). RE-MEASURED 2026-10-07 after CASTAI-RM (section 7 runs on its CARRIED
# rows, so it is bare-machine; section 8 is vault-only): 88 bare (36 + 52), 138 with the
# vault (+ section 8's 1 row check and 4 replay checks).
# 2026-10-07 (the CASTAI-RM review, CD-7): TWO floors, decided on the vault's content
# DIRECTORY -- test_mechanics' and test_agentlife's FLOOR_VAULT / FLOOR_BARE pattern --
# and never on what loaded, so a vault run that silently loses its vault-only checks is
# red (one floor of 88 let a vault run with sections 2-5 and 8 gone print ALL PASSED).
# MEASURED after the review's fixes, each from its green run: 146 with the vault, 95
# bare with RURIK_VAULT at a nonexistent path (4 declared skips: sections 2-4, section
# 5's driven half, 8 (a), 8 (b)). The +8 / +7 over 138 / 88: section 7 (f)'s two party-loop
# self cures, (h)'s removed Suffering [44], (i)'s two 301 reverts with their gate-ON
# contrasts (+4), and -- vault only -- section 2's "the removal gate holds 276" check.
# 2026-10-08 (the review's second round, VF-1): +1 on both machines -- section 7 (h)'s
# removed Deep Freeze declaring the 0x0027 base back. MEASURED: 147 with the vault, 96 bare
# (RURIK_VAULT=C:/nonexistent-vault, the same 4 declared skips).
# 2026-10-08 (the pass-9 landing, CASTAI-RM + SKILLS-AC): +2 with the vault -- the
# NPC_AFTERCAST lane's two vault-only section-2 checks (the aftercast-aware after-close
# check and ON_SEQUENCE, re-recorded on the merged tree); it kept the old single floor of
# 36. MEASURED at the merge: 149 with the vault, 96 bare (RURIK_VAULT at an empty
# directory, 4 declared skips).
HAVE_VAULT_CONTENT = os.path.isdir(vaultpath.vault_path("content"))
FLOOR_VAULT = 149
FLOOR_BARE = 96
LEDGER = checks.Ledger("cast gate (CASTAI)",
                       floor=FLOOR_VAULT if HAVE_VAULT_CONTENT else FLOOR_BARE)
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
         "LIVE_EFFECT_REARM", "HOSTILE_ALLY_SKILL_SELF", "REMOVAL_NEEDS_AFFLICTION",
         "NPC_AFTERCAST")
BEAT = 0.25                          # authsrv.LIVE_EFFECT_REARM's default, as a LITERAL

# THE KNOWN-BAD ARM'S LITERAL: the first 24 (tick index, skill) casts of fight(bar=the
# Hatcher's) on the pre-CASTAI server, recorded 2026-09-27 by driving this file's
# `fight` through an export of 19213513's authsrv.py (the scratch driver
# castai-impl/head_literal.py). The gate-off arm must reproduce it byte for byte:
# round robin's own sequence, with the 253s every ~6.3 s that stack on the player.
HEAD_SEQUENCE = None                 # filled in below from the recorded literal
# THE DEFAULT ARM'S LITERAL (added 2026-10-07 after review, EV-6): the first 24 (tick,
# skill) casts of `_hatcher_fight(True)` with NPC_AFTERCAST on, recorded from a green run
# of the desk-aftercast lane (scratch impl-desk-aftercast/fix/record_on_sequence.py; two
# runs identical, 79 casts in 120 s). Section 2's after-close check proves the gate's own
# four facts but cannot say WHEN 253 comes back once its aftercast cover ends -- a 253
# held 2 s past every aftercast, or released a tick late, left this file green -- so the
# cadence is pinned whole, the way section 3 pins the known-bad arm.
ON_SEQUENCE = None                   # filled in below from the recorded literal


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
    # REMOVAL_NEEDS_AFFLICTION defaults ON in this fixture, as it ships (CASTAI-RM,
    # 2026-10-07). The first cut defaulted it OFF for every section so that sections 2-5's
    # Hatcher bar kept casting 276 at its clean hurt ally -- which left the bar every
    # standing hostile carries driven only in a configuration no run ships (the review's
    # CD-4: the removal hold, its re-pick and the live-effect hold on 253 / 289 together
    # were never exercised). Now sections 2-5 run the shipping combination; the one place
    # that needs the pre-CASTAI server, section 3's HEAD_SEQUENCE, turns it off by name,
    # and section 7's known-bad arms do the same.
    base = {"SKIP_LIVE_EFFECT": True, "SELF_CAST_FORM": True, "CAST_FORM": "follows-target",
            "ENERGY": False, "NPC_FOLLOW": False, "CASTER_OPENING": True,
            "CONDITION_HEAL_RULE": True, "EFFECTS": True, "INSTANT_ANNOUNCE": True,
            "LIVE_EFFECT_REARM": BEAT, "HOSTILE_ALLY_SKILL_SELF": True,
            "REMOVAL_NEEDS_AFFLICTION": True, "NPC_AFTERCAST": True}
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
def _hatcher_fight(skip, secs=120.0, removal=True, aftercast=True):
    with arm(clock=Clock(T0), SKIP_LIVE_EFFECT=skip, REMOVAL_NEEDS_AFFLICTION=removal,
             NPC_AFTERCAST=aftercast):
        st = hatcher_world(authsrv)
        with recording_consults() as seen, recording_removals() as rm_seen:
            rec = fight(authsrv, st, secs)
    rec["consults"] = seen
    rec["removals"] = rm_seen
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
    # RE-AIMED 2026-10-07 (CASTAI-RM; the review's CD-4): this ran with the removal gate
    # OFF and asked for all four slots. In the shipping configuration the squad is clean,
    # so 276 is never cast -- the removal gate holds it -- and the property this check
    # exists for is unchanged: the holds (276's AND 253's) step the cursor past rather
    # than stalling the bar, so every OTHER slot fires.
    check(fired == {SCOURGE, HOLY, VITAL},
          "276 is never cast at the clean squad, and every OTHER slot fires -- the holds "
          "step the cursor past 276 and 253 rather than stalling the bar (DESKWORK-D8 "
          "step 4's lesson)",
          f"{sorted(fired)} counts {[sum(1 for _i, s in hat if s == k) for k in (RESTORE, SCOURGE, HOLY, VITAL)]}")
    rm_looks = [(cid, kind, klass, out) for _t, cid, kind, klass, out in rec["removals"]
                if cid == HOSTILE]
    rm_lines = [ln for ln in rec["log"].splitlines() if "[CASTAI-RM]" in ln]
    check(len(rm_looks) >= 10 and all(o is None and k == "other_ally" and c == "condition"
                                       for _a, k, c, o in rm_looks)
          and rm_lines and all("holds skill 276" in ln for ln in rm_lines)
          and len(rm_lines) <= int(120.0 / 5.0) + 1,
          "  and it IS the removal gate that holds it: every look at 276 asks removal_target "
          "for an other-ally condition carrier and gets None, the line at most once per 5 s",
          f"{len(rm_looks)} looks, answers {sorted({o for *_x, o in rm_looks}, key=str)}, "
          f"{len(rm_lines)} lines")
    # AFTER A CLOSE: THE FIRST LOOK HOLDS FOR ONE BEAT, THE FIRST LOOK PAST IT CASTS.
    # RE-AIMED 2026-10-07 (NPC_AFTERCAST, studies/skills 65): "cast on that very tick"
    # now also needs the body OUT of its aftercast -- a CLOCK gate after this WORLD gate
    # -- and on the default arm every go tick falls inside one (the Hatcher's 30-tick
    # cycle, 0.75 s cast + 0.75 s aftercast, puts a [58] on each close's tick). So the
    # check is run twice: on the default arm, the gate's own four facts on every close
    # AND the cast on the go tick wherever no aftercast covers it, the cover itself
    # named per close; and VERBATIM on --no-npc-aftercast, where all five go ticks cast.
    # What the default arm does NOT claim (corrected after review, EV-6 / CD-5): that
    # 253 is cast when its cover ends. The aftercast hold leaves last_slot alone and the
    # next tick re-picks from the cursor, so a slot ready earlier in the scan takes the
    # turn (traced: 253 held 416-419, 312 picked at 420 and cast at 425, 253 at 515) --
    # round robin's business, pinned whole by ON_SEQUENCE just below.
    looks = [(t, held) for t, a, s, held in rec["consults"] if a == HOSTILE and s == SCOURGE]
    good, detail = _after_close(rec, n253, closes, looks, aftercast_aware=True)
    check(good and detail,
          "after each close the gate's FIRST look at 253 HOLDS it (the re-arm), every look "
          "inside the next 0.25 s holds, and the first look past the beat lets it through "
          "-- no 253 inside the beat -- and the go tick either casts 253 or sits inside the "
          "body's aftercast (NPC_AFTERCAST's clock gate; the cover named per close)",
          f"(close, first look, go tick, held first?, held inside?, held at go?, cast?, "
          f"covered by the [58] at tick) {detail}")
    check(hat[:len(ON_SEQUENCE)] == ON_SEQUENCE,
          "and the default arm's first 24 casts (tick, skill) equal the cadence recorded "
          "with the aftercast on (ON_SEQUENCE: each cast starts the previous one's "
          "activation + its 0.75 s aftercast after it; 253 back when round robin's "
          "cursor comes round)",
          f"{hat[:len(ON_SEQUENCE)]}")
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
    # Every gate 19213513 predates is off, by name: it had neither the live-effect gate
    # nor the removal gate (CASTAI-RM, 2026-10-07: its sequence casts 276 at the clean
    # ally) nor NPC_AFTERCAST (SKILLS-AC, 2026-10-07: with the aftercast on, every cast
    # after the first waits 0.75 s past the previous [58] and the literal moves by exactly
    # that). Both lanes re-aimed this arm separately; the pass-9 landing joined them.
    rec = _hatcher_fight(False, removal=False, aftercast=False)
    hat = [(i, s) for i, a, s in rec["casts"] if a == HOSTILE]
    check(hat[:len(HEAD_SEQUENCE)] == HEAD_SEQUENCE,
          "the first 24 casts (tick, skill) equal 19213513's own -- round robin's sequence "
          "exactly as before (--no-skip-live-effect --no-removal-needs-affliction)",
          f"{hat[:len(HEAD_SEQUENCE)]}")
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
    """True when main() holds `if a.<attr>:` whose body sets `<glob> = False`, AND main()
    declares `global <glob>`. Without the global the assignment binds a LOCAL: the flag
    parses and never reaches the module bool -- the house rule's named defect, and the
    one this check could not see until the CASTAI-RM review (CD-1: the global line
    deleted, every caller stayed green). Python applies a `global` to the whole function,
    so it is looked for anywhere in main(), not only in the If's body."""
    if not any(isinstance(n, ast.Global) and glob in n.names for n in ast.walk(main_fn)):
        return False
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


# ---------------------------------------------------------------------------------
# CASTAI-RM (2026-10-07; studies/monsterai/FINDINGS.md 18.5): THE REMOVAL GATE. A removal
# slot (275 / 276 / 277 cure conditions, 301 removes a hex) aims at an ally CARRYING what
# it removes, at any health, and is HELD when nobody does (REMOVAL_NEEDS_AFFLICTION,
# --no-removal-needs-affliction).
MEND_COND, MEND_AIL, REMOVE_HEX, ORISON, INC_BONDS, EMPATHY = 275, 277, 301, 281, 179, 26
SUFFERING = 108                      # a hex with health-degeneration pips (skill_effect.108)
DEEP_FREEZE = 234                    # a hex with a movement snare (skill_effect.234: the flat 66)
ALLY2, HERO2 = 12, 201
# The rows sections 7's driven halves read, CARRIED so a bare machine runs them: the
# vault's LOADED skills rows (toolkit/clientscan/skilltable.py at build 38974), in
# test_agentlife's SKILL_COLUMNS order. rm_carried() REPLACES the skills table with
# exactly these for the block, so the vault run and the bare run read the same rows, and
# section_rm_rows (vault-only) holds each against the vault's own, column for column.
RM_COLUMNS = ("activation", "aftercast", "recharge", "energy", "adrenaline",
              "adrenaline_units", "attribute", "profession", "type_code", "target",
              "combo", "combo_req", "weapon_req", "aoe_range", "skill_arguments",
              "duration0", "duration15", "scale0", "scale15", "bonus_scale0",
              "bonus_scale15", "projectile", "impact_visual", "touch_range",
              "half_range")
RM_BUILD = 38974
RM_RECORD = {
    "26": (2.0, 0.75, 10, 10, 0, 0, 2, 5, 4, 5, 0, 0, 0, 0.0, 7, 5, 15, 10, 55, 1, 15, 2077, 2077, False, False),        # Empathy (a Mesmer hex)
    "108": (1.0, 0.75, 10, 15, 0, 0, 7, 4, 4, 16, 0, 0, 0, 240.0, 1, 6, 30, 0, 3, 0, 0, 2077, 2077, False, False),      # Suffering (a hex with pips)
    "179": (1.0, 0.75, 7, 10, 0, 0, 10, 6, 4, 5, 0, 0, 0, 240.0, 6, 3, 3, 20, 80, 1, 3, 2077, 2077, False, False),      # Incendiary Bonds
    "234": (2.0, 0.75, 15, 25, 0, 0, 11, 6, 4, 16, 0, 0, 0, 312.0, 2, 10, 10, 10, 85, 66, 66, 2077, 414, False, False),  # Deep Freeze (a hex with a snare)
    "275": (0.75, 0.75, 2, 5, 0, 0, 15, 3, 5, 4, 0, 0, 0, 0.0, 2, 0, 0, 5, 70, 0, 0, 2077, 2077, False, False),         # Mend Condition
    "276": (0.75, 0.75, 2, 5, 0, 0, 15, 3, 5, 4, 0, 0, 0, 0.0, 2, 0, 0, 10, 70, 0, 0, 2077, 2077, False, False),        # Restore Condition
    "277": (0.75, 0.75, 5, 5, 0, 0, 15, 3, 5, 3, 0, 0, 0, 0.0, 2, 0, 0, 5, 70, 0, 0, 2077, 2077, False, False),         # Mend Ailment
    "281": (1.0, 0.75, 2, 5, 0, 0, 13, 3, 5, 3, 0, 0, 0, 0.0, 2, 0, 0, 30, 80, 0, 0, 2077, 2077, False, False),         # Orison of Healing
    "301": (1.0, 0.75, 8, 5, 0, 0, 51, 3, 5, 3, 0, 0, 0, 0.0, 0, 0, 0, 0, 0, 0, 0, 2077, 2077, False, False),           # Remove Hex
}


@contextlib.contextmanager
def rm_carried():
    """WORLD's skills table REPLACED by exactly RM_RECORD's rows for the block, then put
    back (test_agentlife's `carried`, cut to this section's rows)."""
    tables = agents.WORLD.tables
    kept = tables.get("skills")
    tables["skills"] = {k: content.Row(dict(zip(RM_COLUMNS, v)), "skills", k,
                                       {"source": "client-table",
                                        "extractor": "toolkit/clientscan/skilltable.py",
                                        "build": RM_BUILD})
                        for k, v in RM_RECORD.items()}
    try:
        yield
    finally:
        if kept is None:
            tables.pop("skills", None)
        else:
            tables["skills"] = kept


@contextlib.contextmanager
def recording_removals(A=authsrv):
    """Wrap authsrv.removal_target (both loops look it up by name per call) and record
    (clock time, caster, kind, klass, answer) for every consultation."""
    real = A.removal_target
    seen = []

    def spy(state, caster_id, kind, klass):
        out = real(state, caster_id, kind, klass)
        seen.append((A.time.time(), caster_id, kind, klass, out))
        return out
    A.removal_target = spy
    try:
        yield seen
    finally:
        A.removal_target = real


class _Unbounded(Exception):
    """A tick that consulted pick_skill past len(bar) + 1 times for one body."""


@contextlib.contextmanager
def bounded_picks(A=authsrv):
    """Run pick_skill through a counter that RAISES past len(bar) + 1 picks for one body
    in one tick (the review's CD-5; test_agentlife's RV-2 pattern, DESKWORK-D8). A tick
    makes at most that many -- the first pick, then one re-pick per hold, each hold adding
    a slot `_held` did not have -- so a hold that forgot `_held.add(slot)` re-picks the
    same slot forever, and run_suite runs a test with NO timeout: the review's mutant hung
    section 7 for 400 s with no verdict. Raised, it is caught by rm_run and read by the
    checks as a FAIL by name. pick_skill itself is untouched (test_heroskilltoggle's lock);
    this wraps the module attribute the loops look up per call."""
    real = A.pick_skill
    count = {}

    def bounded(agent, now):
        key = (id(agent), A.time.time())
        count[key] = count.get(key, 0) + 1
        n = len(agent.get("skills") or ())
        if count[key] > n + 1:
            raise _Unbounded(f"{count[key]} picks in one tick on a bar of {n} "
                             f"(slots {[s[0] for s in agent.get('skills') or ()]})")
        return real(agent, now)
    A.pick_skill = bounded
    try:
        yield
    finally:
        A.pick_skill = real


def rm_world(bar, who, ally_health=100.0, player_health=1e9):
    """A caster with `bar` and a HURT CLEAN ally: for a hostile (10) a fellow hostile at
    `ally_health` of 500 (11); for a hero (200) the player at `player_health`."""
    st = world(authsrv, player_health=player_health)
    if who == HOSTILE:
        st["agents"][HOSTILE] = body(authsrv, bar, agents.ALLEGIANCE_HOSTILE,
                                     attack_speed=1e6)
        st["agents"][ALLY] = body(authsrv, (), agents.ALLEGIANCE_HOSTILE, pos=(120.0, 40.0),
                                  health=ally_health, max_health=500.0, attacks_back=False)
    else:
        st["agents"][HERO] = body(authsrv, bar, agents.ALLEGIANCE_PLAYER, pos=(50.0, 0.0),
                                  attack_speed=1e6)
    return st


def rm_run(bar, who, secs=2.0, gate=True, setup=None, player_health=1e9, ally_health=100.0,
           aftercast=True):
    """Drive the real ticks for `secs` with the removal gate `gate` (and NPC_AFTERCAST
    `aftercast`: the pass-9 landing joined SKILLS-AC, whose hold moves a second cast's
    tick, so an arm compared with 642d8957's bytes turns it off too). The hostile runs
    enemy_attack_tick, the hero ally_cast_tick; effect_tick first, as the world tick does.
    Every tick runs under bounded_picks: an overrun ends the run and is returned as
    rec["overrun"] (None on a healthy run), with no sends -- so every check reading the
    run goes red, and the spin check says why."""
    loop = "enemy_attack_tick" if who == HOSTILE else "ally_cast_tick"
    overrun = None
    with rm_carried(), arm(clock=Clock(T0), REMOVAL_NEEDS_AFFLICTION=gate,
                           NPC_AFTERCAST=aftercast):
        st = rm_world(bar, who, ally_health=ally_health, player_health=player_health)
        if setup is not None:
            setup(st)
        with recording_removals() as seen, bounded_picks():
            try:
                rec = fight(authsrv, st, secs, ticks=("effect_tick", loop), watch=(),
                            keep_health=False)
            except _Unbounded as exc:
                overrun = f"{exc}"
                rec = {"casts": [], "live": {}, "closes": {}, "early": {}, "sends": [],
                       "log": ""}
        rec["want_heal"] = {sid: authsrv.skill_heal(sid, authsrv.agent_skill_rank(
            st["agents"][who], sid)) for sid in (RESTORE, MEND_AIL, MEND_COND, ORISON)}
    rec["st"], rec["seen"], rec["overrun"] = st, seen, overrun
    rec["ann"] = _announces(rec["sends"])
    return rec


def _bleed(*who, at=T0, secs=30.0):
    def setup(st):
        for w in who:
            st["effects"].apply(w, BLEEDING, 0, secs, at, type_code=8, caster=99)
    return setup


def _conds(st, aid):
    return [ep["skill"] for ep in st["effects"].on_agent(aid)
            if ep["skill"] in effects.CONDITION_SKILLS]


def section_rm_predicate():
    print("== 7. (a) CASTAI-RM: the removal predicates, on literal inputs ==")
    rc = episodemods.removal_class
    check(rc({"removes_conditions": "all"}) == "condition"
          and rc({"removes_conditions": 1}) == "condition"
          and rc({"removes_hexes": 1}) == "hex" and rc({"removes_hexes": "all"}) == "hex",
          "removes_conditions ('all' or a count) is a CONDITION removal; removes_hexes a HEX "
          "removal")
    check(rc({"removes_condition": "Crippled"}) is None and rc({}) is None and rc(None) is None
          and rc({"scale_means": "Healing"}) is None,
          "364's singular removes_condition (a shout's side effect), an empty row, no row and "
          "a plain heal are NOT removal slots")
    check(rc({"removes_conditions": True}) is None and rc({"removes_conditions": 0}) is None
          and rc({"removes_hexes": -1}) is None,
          "a bool, a zero and a negative count name no removal (True is a typo, not a 1)")
    check(rc({"removes_conditions": 1, "removes_hexes": 1}) is None,
          "a row naming BOTH kinds asks no single question: ungated (no row has that shape)")
    table = effects.EffectTable()
    table.apply(ALLY, BLEEDING, 0, 30.0, 0.0, type_code=8, caster=99)
    table.apply(ALLY2, EMPATHY, 12, 30.0, 0.0, type_code=4, caster=99)
    table.apply(HOSTILE, SELF_ENCHANT, 12, 30.0, 0.0, type_code=6, caster=HOSTILE)
    car = episodemods.carries_removable
    check(car(table, ALLY, "condition") and car(table, ALLY, "hex") is None,
          "a Bleeding body carries a CONDITION and no hex", f"{car(table, ALLY, 'condition')}")
    check(car(table, ALLY2, "hex") and car(table, ALLY2, "condition") is None,
          "a hexed body carries a HEX and no condition", f"{car(table, ALLY2, 'hex')}")
    check(car(table, HOSTILE, "condition") is None and car(table, HOSTILE, "hex") is None,
          "an ENCHANTED body carries neither (an enchantment is neither class)")
    check(car(None, ALLY, "condition") is None and car(table, ALLY, None) is None
          and car(table, ALLY, "enchantment") is None,
          "no table, no class or an unknown class: never carried")
    table.close(table.on_agent(ALLY)[0]["buff"])
    check(car(table, ALLY, "condition") is None,
          "a CLOSED condition is not carried -- the slot is held again")
    # the hand rows that ship (content/world.toml): what the AI loops actually read
    rows = {sid: episodemods.removal_class(authsrv.skill_effect_row(sid))
            for sid in (MEND_COND, RESTORE, MEND_AIL, REMOVE_HEX, 364, VITAL, ORISON)}
    check(rows == {MEND_COND: "condition", RESTORE: "condition", MEND_AIL: "condition",
                   REMOVE_HEX: "hex", 364: None, VITAL: None, ORISON: None},
          "the shipped rows: 275 / 276 / 277 cure conditions, 301 removes a hex; 364 "
          "(Charge!), 289 and 281 are not removal slots", f"{rows}")
    with arm(REMOVAL_NEEDS_AFFLICTION=True, CONDITION_HEAL_RULE=False):
        off_heal = authsrv.removal_slot_class(RESTORE)
    with arm(REMOVAL_NEEDS_AFFLICTION=False):
        off_flag = authsrv.removal_slot_class(RESTORE)
    with arm(REMOVAL_NEEDS_AFFLICTION=True):
        on = authsrv.removal_slot_class(RESTORE)
    check(on == "condition" and off_flag is None and off_heal is None,
          "removal_slot_class: 'condition' with the gate on; None under "
          "--no-removal-needs-affliction and under --no-condition-heal-rule (nothing is "
          "removed there, so there is nothing to need)", f"{on} {off_flag} {off_heal}")


def section_rm_target():
    print("== 7. (b) removal_target: carriers only, no floor, the byte's candidates ==")
    with rm_carried(), arm(REMOVAL_NEEDS_AFFLICTION=True):
        st = world(authsrv, player_health=float(agents.PLAYER_HEALTH))
        st["agents"][HOSTILE] = body(authsrv, (), agents.ALLEGIANCE_HOSTILE)
        st["agents"][ALLY] = body(authsrv, (), agents.ALLEGIANCE_HOSTILE, health=100.0,
                                  max_health=500.0)
        st["agents"][ALLY2] = body(authsrv, (), agents.ALLEGIANCE_HOSTILE, health=450.0,
                                   max_health=500.0)
        rt = authsrv.removal_target
        check(rt(st, HOSTILE, "other_ally", "condition") is None,
              "nobody carries a condition: None (the slot will be held)")
        st["effects"].apply(ALLY2, BLEEDING, 0, 30.0, T0, type_code=8, caster=99)
        check(rt(st, HOSTILE, "other_ally", "condition") == ALLY2,
              "the lower-id ally is hurt-most (0.2) and CLEAN, the other at 0.9 bleeds: the "
              "AFFLICTED one is named -- no health floor, no hurt-most rule")
        st["agents"][ALLY2]["health"] = 500.0
        check(rt(st, HOSTILE, "other_ally", "condition") == ALLY2,
              "an afflicted ally at 100 % health IS a target (retail's 275 at 1.000)")
        st["effects"].apply(ALLY, POISON, 0, 30.0, T0, type_code=8, caster=99)
        check(rt(st, HOSTILE, "other_ally", "condition") == ALLY,
              "two carriers: the LOWER health fraction (0.2 over 1.0) -- RECONSTRUCTION")
        st["agents"][ALLY]["health"] = 500.0
        check(rt(st, HOSTILE, "other_ally", "condition") == ALLY,
              "two carriers at the same fraction: the lower id -- RECONSTRUCTION")
        st2 = world(authsrv)
        st2["agents"][HOSTILE] = body(authsrv, (), agents.ALLEGIANCE_HOSTILE)
        st2["effects"].apply(HOSTILE, BLEEDING, 0, 30.0, T0, type_code=8, caster=99)
        check(rt(st2, HOSTILE, "ally", "condition") == HOSTILE
              and rt(st2, HOSTILE, "other_ally", "condition") is None
              and rt(st2, HOSTILE, "self", "condition") == HOSTILE,
              "the CASTER is a candidate for byte 3 (ally) and byte 0 (self), never for byte "
              "4 (other ally) -- retail: 6 self-form 277 / 301, 0 of 92 self 275")
        st2["agents"][ALLY] = body(authsrv, (), agents.ALLEGIANCE_HOSTILE, dead=True)
        st2["effects"].apply(ALLY, POISON, 0, 30.0, T0, type_code=8, caster=99)
        check(rt(st2, HOSTILE, "other_ally", "condition") is None,
              "a DEAD carrier is no target (allies_of drops it)")
        st3 = world(authsrv)
        st3["agents"][HERO] = body(authsrv, (), agents.ALLEGIANCE_PLAYER)
        st3["effects"].apply(P, EMPATHY, 12, 30.0, T0, type_code=4, caster=99)
        check(rt(st3, HERO, "ally", "hex") == P and rt(st3, HERO, "ally", "condition") is None,
              "a hero's hex removal names the hexed PLAYER (the player is read off `state`)")


def section_rm_driven():
    print("== 7. (c) the driven loops: a clean hurt ally gets no cure, an afflicted one does ==")
    bar = ((RESTORE, 0.75, 2.0), (ORISON, 1.0, 2.0))
    # (c) the HOSTILE loop, [276, 281], the ally hurt (100 of 500) and clean
    rec = rm_run(bar, HOSTILE, secs=3.0)
    fired = [s for _i, a, s in rec["casts"] if a == HOSTILE]
    hold = [ln for ln in rec["log"].splitlines() if "[CASTAI-RM]" in ln]
    per_tick = {}
    for t, a, _k, _c, _o in rec["seen"]:
        per_tick[round(t, 6)] = per_tick.get(round(t, 6), 0) + 1
    check(RESTORE not in fired and fired.count(ORISON) >= 1
          and rec["st"]["agents"][HOSTILE]["skill_ready"][0] == 0.0,
          "a hostile with [276, 281] and a HURT CLEAN ally casts only 281 -- 276 held, its "
          "recharge never charged", f"casts {fired} ready "
          f"{rec['st']['agents'][HOSTILE]['skill_ready']}")
    check((INT_T, [60, HOSTILE, ALLY, ORISON]) in rec["ann"],
          "  and 281 goes at the hurt ally (the heal rule, unchanged)", f"{rec['ann'][:3]}")
    check(rec["overrun"] is None and per_tick and max(per_tick.values()) == 1
          and len(per_tick) >= 30,
          "  276 is consulted ONCE a tick -- the search ends on the held slot (no spin: "
          "pick_skill ran under its len(bar) + 1 bound and never overran it)",
          f"overrun {rec['overrun']}; {len(per_tick)} ticks, "
          f"max {max(per_tick.values()) if per_tick else None}")
    check(hold and all("holds skill 276" in ln and "nobody carries a condition" in ln
                       for ln in hold) and len(hold) == 1,
          "  its line names the skill and 'nobody carries a condition', once per 5 s",
          f"{hold}")
    # (c') the PARTY loop, the hero's [276, 281], the PLAYER hurt and clean
    ph = float(agents.PLAYER_HEALTH)
    rec = rm_run(bar, HERO, secs=3.0, player_health=0.4 * ph)
    fired = [s for _i, a, s in rec["casts"] if a == HERO]
    check(rec["overrun"] is None and RESTORE not in fired and fired.count(ORISON) >= 1
          and (INT_T, [60, HERO, P, ORISON]) in rec["ann"]
          and rec["st"]["agents"][HERO]["skill_ready"][0] == 0.0,
          "a HERO with [276, 281] and the hurt clean player casts only 281 at the player -- "
          "276 held, uncharged, inside the pick bound",
          f"overrun {rec['overrun']}; casts {fired} ann {rec['ann'][:2]}")
    check(any("party agent 200 holds skill 276" in ln and "[CASTAI-RM]" in ln
              for ln in rec["log"].splitlines()),
          "  its line names the party agent")

    print("== 7. (d) Bleeding planted: 276 lands, removes it, heals per condition ==")
    rec = rm_run(bar, HOSTILE, secs=1.0, setup=_bleed(ALLY))
    ally = rec["st"]["agents"][ALLY]
    want = rec["want_heal"][RESTORE]
    check(rec["ann"][:1] == [(INT_T, [60, HOSTILE, ALLY, RESTORE])]
          and not _conds(rec["st"], ALLY)
          and abs(float(ally["health"]) - (100.0 + float(want))) < 1e-6,
          f"276 is announced at the bleeding ally, lands, the Bleeding is gone and the ally "
          f"is healed once ({want:g}: one condition removed)",
          f"ann {rec['ann'][:1]} conds {_conds(rec['st'], ALLY)} health {ally['health']}")
    rec = rm_run(bar, HOSTILE, secs=1.0, setup=_bleed(ALLY), ally_health=500.0)
    check(rec["ann"][:1] == [(INT_T, [60, HOSTILE, ALLY, RESTORE])]
          and not _conds(rec["st"], ALLY),
          "an afflicted ally at 100 % health IS cured (no health floor; the heal rule would "
          "have held it -- nobody under 90 %)", f"{rec['ann'][:1]}")

    print("== 7. (e) two allies: the lower id clean, the other afflicted ==")

    def two(st):
        st["agents"][ALLY]["health"] = 50.0
        st["agents"][ALLY2] = body(authsrv, (), agents.ALLEGIANCE_HOSTILE, pos=(110.0, -40.0),
                                   health=450.0, max_health=500.0, attacks_back=False)
        st["effects"].apply(ALLY2, BLEEDING, 0, 30.0, T0, type_code=8, caster=99)
    rec = rm_run(bar, HOSTILE, secs=1.0, setup=two)
    check(rec["ann"][:1] == [(INT_T, [60, HOSTILE, ALLY2, RESTORE])]
          and not _conds(rec["st"], ALLY2),
          "276 names agent 12 (bleeding, 90 %), not agent 11 (clean, 10 %) -- the heal "
          "rule's pick", f"{rec['ann'][:1]}")
    off = rm_run(bar, HOSTILE, secs=1.0, setup=two, gate=False)
    check(off["ann"][:1] == [(INT_T, [60, HOSTILE, ALLY, RESTORE])] and _conds(off["st"], ALLY2),
          "  KNOWN-BAD, --no-removal-needs-affliction: 276 goes at the hurt-most CLEAN ally "
          "11 and the bleeding one keeps its Bleeding", f"{off['ann'][:1]}")

    print("== 7. (f) the caster: byte 3 (277, 301) may cure itself -- a hostile and a hero "
          "-- byte 4 (276) may not ==")
    rec = rm_run(((MEND_AIL, 0.75, 5.0),), HOSTILE, secs=1.0, setup=_bleed(HOSTILE))
    check(rec["ann"][:1] == [(INT, [60, HOSTILE, MEND_AIL])] and not _conds(rec["st"], HOSTILE),
          "277 with only the CASTER bleeding lands on the caster: 0x009F [60, 10, 277] and the "
          "Bleeding gone", f"{rec['ann'][:1]} {_conds(rec['st'], HOSTILE)}")
    rec = rm_run(((RESTORE, 0.75, 2.0),), HOSTILE, secs=1.0, setup=_bleed(HOSTILE))
    check(not rec["ann"] and _conds(rec["st"], HOSTILE) == [BLEEDING],
          "276 with only the CASTER bleeding is HELD -- byte 4 never self-targets",
          f"{rec['ann']}")
    # ... and the PARTY loop's own byte-3 candidacy (the review's CD-6: only the hostile
    # loop's was driven, and a party loop passing "other_ally" to removal_target stayed
    # green). The player is whole and clean, so the hero itself is the only carrier.
    rec = rm_run(((MEND_AIL, 0.75, 5.0),), HERO, secs=1.0, player_health=ph,
                 setup=_bleed(HERO))
    check(rec["ann"][:1] == [(INT, [60, HERO, MEND_AIL])] and not _conds(rec["st"], HERO),
          "a HERO's 277 with only ITSELF bleeding (the player whole) cures itself through "
          "ally_cast_tick: 0x009F [60, 200, 277] and the Bleeding gone",
          f"{rec['ann'][:1]} {_conds(rec['st'], HERO)}")

    def hexed_hero(st):
        st["effects"].apply(HERO, EMPATHY, 12, 30.0, T0 - 1.0, type_code=4, caster=HOSTILE)
    rec = rm_run(((REMOVE_HEX, 1.0, 8.0),), HERO, secs=1.5, player_health=ph,
                 setup=hexed_hero)
    check(rec["ann"][:1] == [(INT, [60, HERO, REMOVE_HEX])]
          and not rec["st"]["effects"].on_agent(HERO),
          "a HERO's 301 with only ITSELF hexed removes its own hex through ally_cast_tick: "
          "0x009F [60, 200, 301] and the Empathy gone",
          f"{rec['ann'][:1]} left {[ep['skill'] for ep in rec['st']['effects'].on_agent(HERO)]}")

    print("== 7. (g) a hero cures the bleeding player at full health ==")
    rec = rm_run(bar, HERO, secs=1.0, player_health=ph, setup=_bleed(P))
    check(rec["ann"][:1] == [(INT_T, [60, HERO, P, RESTORE])] and not _conds(rec["st"], P)
          and any(op == authsrv.GAME_SMSG_EFFECT_REMOVE and v[0] == P
                  for _i, op, v in rec["sends"]),
          "the hero's 276 goes at the bleeding player at 100 %, the 0x0044 closes the "
          "player's Bleeding (the runsheet's B arm)", f"{rec['ann'][:1]}")
    off = rm_run(bar, HERO, secs=1.0, player_health=ph, setup=_bleed(P), gate=False)
    check(not off["ann"] and _conds(off["st"], P) == [BLEEDING],
          "  KNOWN-BAD: today's hero holds 276 at a bleeding player at full health -- "
          "nobody is under 90 %", f"{off['ann']}")


def _two_bonds(st, A=authsrv):
    """Two Incendiary Bonds (179) on hostile 10, cast by the hero 0.5 s apart through the
    real apply_effect (so the aura words and the end-burst arm are the server's own)."""
    sent = []
    snd = (lambda op, vals, why="", quiet=False: sent.append((op, list(vals))))
    eps = []
    for k in range(2):
        A.time.t = T0 + 0.5 * k
        eps.append(A.apply_effect(snd, st, HERO, INC_BONDS, 12, HOSTILE, 0))
    A.push_status(snd, st, HOSTILE, 0)
    return eps, sent


def section_rm_hex():
    print("== 7. (h) Remove Hex 301: held with no hex, the newest goes, the [7]s on the last ==")
    bar = ((REMOVE_HEX, 1.0, 8.0),)
    rec = rm_run(bar, HOSTILE, secs=3.0)
    check(not rec["ann"] and rec["st"]["agents"][HOSTILE]["skill_ready"] == [0.0],
          "a hostile's 301 with nobody hexed is HELD (before: cast at itself, removing "
          "nothing, every 8 s)", f"{rec['ann']}")
    off = rm_run(bar, HOSTILE, secs=1.5, gate=False)
    check(off["ann"][:1] == [(INT, [60, HOSTILE, REMOVE_HEX])],
          "  KNOWN-BAD: --no-removal-needs-affliction casts it at itself, 0x009F [60, 10, 301]",
          f"{off['ann'][:1]}")

    def hexed(st):
        st["effects"].apply(ALLY, EMPATHY, 12, 30.0, T0 - 1.0, type_code=4, caster=HERO)
        st["effects"].apply(ALLY, INC_BONDS, 12, 30.0, T0 - 0.5, type_code=4, caster=HERO)
    rec = rm_run(bar, HOSTILE, secs=1.5, setup=hexed)
    left = [ep["skill"] for ep in rec["st"]["effects"].on_agent(ALLY)]
    check(rec["ann"][:1] == [(INT_T, [60, HOSTILE, ALLY, REMOVE_HEX])] and left == [EMPATHY],
          "with the ally hexed twice, 301 goes at it and removes exactly ONE -- the NEWEST "
          "(179, GWW 'Cover'), leaving Empathy", f"{rec['ann'][:1]} left {left}")

    with rm_carried(), arm(clock=Clock(T0), REMOVAL_NEEDS_AFFLICTION=True):
        st = world(authsrv)
        st["agents"][HOSTILE] = body(authsrv, (), agents.ALLEGIANCE_HOSTILE)
        st["agents"][ALLY] = body(authsrv, (), agents.ALLEGIANCE_HOSTILE, pos=(120.0, 40.0))
        st["agents"][HERO] = body(authsrv, (), agents.ALLEGIANCE_PLAYER, pos=(150.0, 0.0))
        bursts = []
        real_burst = authsrv.hex_end_burst

        def spy(send, state, conn_id, ep, why):
            bursts.append((ep["skill"], ep["agent"], why, bool(ep.get("end_burst"))))
            return []
        authsrv.hex_end_burst = spy
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                eps, _applied = _two_bonds(st)
                armed = [bool(ep and ep.get("end_burst")) for ep in eps]
                out = []
                rounds = []
                left = []
                for _k in range(2):
                    sent = []
                    snd = (lambda op, vals, why="", quiet=False, s=sent: s.append((op, list(vals))))
                    out.append(authsrv.resolve_heal(snd, st, REMOVE_HEX, 0, ALLY, HOSTILE, 0))
                    rounds.append(sent)
                    left.append([ep["buff"] for ep in st["effects"].on_agent(HOSTILE)])
                bursts_removed = list(bursts)
                # CONTROL: a third Bonds left to RUN OUT goes through effect_tick, which does
                # call the end burst -- so the spy sees the path a removal must not take
                authsrv.time.t = T0 + 1.0
                ctl = authsrv.apply_effect(lambda *a, **k: None, st, HERO, INC_BONDS, 12,
                                           HOSTILE, 0)
                authsrv.time.t = T0 + 10.0
                authsrv.effect_tick(lambda *a, **k: None, st, 0)
        finally:
            authsrv.hex_end_burst = real_burst
    sevens = [[v for op, v in r if op == INT and v[0] == agents.PROP_AURA_OFF and v[1] == HOSTILE]
              for r in rounds]
    words = [[v for op, v in r if op == authsrv.GAME_SMSG_AGENT_UPDATE_STATUS and v[0] == HOSTILE]
             for r in rounds]
    check(armed == [True, False] and [o and o.get("hexes_removed") for o in out] == [1, 1]
          and left == [[eps[0]["buff"]], []],
          "two Incendiary Bonds on one body -- the FIRST armed to burst, the second arming "
          "none (hex_end_arm: one payoff per wearer) -- and each 301 removes one, the NEWEST "
          "first, so the second removal takes the ARMED one",
          f"armed {armed} out {out} left after each {left}")
    check(sevens[0] == [] and words[0] == [],
          "  the FIRST removal (one Bonds left) sends no [7] and no 0x00F1 -- the hex words "
          "and 0x800 stay up while a hex holds them", f"{sevens[0]} {words[0]}")
    check(sorted(v[2] for v in sevens[1]) == [1, 12] and len(words[1]) == 1
          and not (words[1][0][1] & effects.STATUS_HEXED),
          "  the LAST removal sends [7, 10, 1] [7, 10, 12] and an 0x00F1 with 0x800 clear "
          "(CASTAI-RM2: 11 of 11 last-hex removals on tape)", f"{sevens[1]} {words[1]}")
    check(bursts_removed == [],
          "  and a REMOVED Bonds fires NOTHING -- no end burst on either removal, the armed "
          "one included (OBSERVED 0 payoff 4 of 4, studies/skills 61.1)", f"{bursts_removed}")
    check(bursts[len(bursts_removed):] == [(INC_BONDS, HOSTILE, "it ran out", True)]
          and ctl is not None,
          "  CONTROL: the same hex left to expire DOES reach the end burst (the spy sees the "
          "path)", f"{bursts}")
    # A hex WITH PIPS removed (the review's CD-6): remove_hexes' push_speed / push_attributes
    # / push_regen after the close had no check that could fail -- deleting all three left
    # section 7 green. Suffering 108 (skill_effect.108: health degeneration 0..3) put on the
    # hostile through the real apply_effect moves its [44] below zero; the 301 that removes
    # it must send the [44] back to 0 (REGEN_ZERO_POSITIVE's +0.0).
    regen = authsrv.agents.GV_CHANGE_HEALTH_REGEN
    with rm_carried(), arm(clock=Clock(T0), REMOVAL_NEEDS_AFFLICTION=True):
        st = world(authsrv)
        st["agents"][HOSTILE] = body(authsrv, (), agents.ALLEGIANCE_HOSTILE)
        st["agents"][ALLY] = body(authsrv, (), agents.ALLEGIANCE_HOSTILE, pos=(120.0, 40.0))
        st["agents"][HERO] = body(authsrv, (), agents.ALLEGIANCE_PLAYER, pos=(150.0, 0.0))
        put, took = [], []
        with contextlib.redirect_stdout(io.StringIO()):
            authsrv.apply_effect(lambda op, vals, why="", quiet=False: put.append((op, list(vals))),
                                 st, HERO, SUFFERING, 12, HOSTILE, 0)
            authsrv.push_regen(lambda op, vals, why="", quiet=False: put.append((op, list(vals))),
                               st, HOSTILE, 0)
            hexed_now = [ep["skill"] for ep in st["effects"].on_agent(HOSTILE)]
            got = authsrv.resolve_heal(lambda op, vals, why="", quiet=False:
                                       took.append((op, list(vals))),
                                       st, REMOVE_HEX, 0, ALLY, HOSTILE, 0)
    # the word carries the rate as f32 BITS (authsrv._fraction): decoded here
    f32 = (lambda bits: struct.unpack("<f", struct.pack("<I", int(bits)))[0])
    rate_on = [f32(v[2]) for op, v in put if op == FLT and v[:2] == [regen, HOSTILE]]
    rate_off = [v[2] for op, v in took if op == FLT and v[:2] == [regen, HOSTILE]]
    check(hexed_now == [SUFFERING] and rate_on and rate_on[-1] < 0
          and got and got.get("hexes_removed") == 1 and rate_off == [0]
          and not st["effects"].on_agent(HOSTILE),
          "a removed Suffering (108, a hex with pips) sends the wearer's [44] back to 0 -- "
          "remove_hexes re-sends the regen word after the close, as remove_conditions does",
          f"hexed {hexed_now} [44] at the apply {rate_on} at the removal (bits) {rate_off} "
          f"out {got}")
    # A hex WITH A SNARE removed (round 2 of the review, VF-1): after the Suffering check
    # above, deleting push_speed ALONE from remove_hexes still left section 7 green, since
    # no hex the section planted moved the 0x0027 base. Deep Freeze 234 (skill_effect.234:
    # "Movement speed decrease" in the bonus slot, the flat 66; a type-4 hex) is planted on
    # the hostile and its snared base declared; the 301 that removes it must declare the
    # base back. Only "below the base, then exactly the base" is asserted -- not the x0.34 --
    # so the snare arithmetic (move_speed_factor) is not this check's subject. (push_attributes
    # after a hex removal stays unchecked on purpose: it reacts only to Weakness 486, a
    # CONDITION remove_hexes never closes, so deleting it changes no byte today.)
    speed_op = authsrv.GAME_SMSG_AGENT_UPDATE_SPEED_BASE
    with rm_carried(), arm(clock=Clock(T0), REMOVAL_NEEDS_AFFLICTION=True):
        st = world(authsrv)
        st["agents"][HOSTILE] = body(authsrv, (), agents.ALLEGIANCE_HOSTILE)
        st["agents"][ALLY] = body(authsrv, (), agents.ALLEGIANCE_HOSTILE, pos=(120.0, 40.0))
        st["agents"][HERO] = body(authsrv, (), agents.ALLEGIANCE_PLAYER, pos=(150.0, 0.0))
        put, took = [], []
        with contextlib.redirect_stdout(io.StringIO()):
            st["effects"].apply(HOSTILE, DEEP_FREEZE, 12, 10.0, T0, type_code=4, caster=HERO)
            authsrv.push_speed(lambda op, vals, why="", quiet=False: put.append((op, list(vals))),
                               st, HOSTILE, 0)
            base_speed = authsrv.agent_speed_base(st, HOSTILE)
            got = authsrv.resolve_heal(lambda op, vals, why="", quiet=False:
                                       took.append((op, list(vals))),
                                       st, REMOVE_HEX, 0, ALLY, HOSTILE, 0)
    snared = [v[1] for op, v in put if op == speed_op and v[0] == HOSTILE]
    freed = [v[1] for op, v in took if op == speed_op and v[0] == HOSTILE]
    check(authsrv.MOVE_SPEED_EFFECTS and len(snared) == 1 and 0 < snared[0] < base_speed
          and got and got.get("hexes_removed") == 1 and len(freed) == 1
          and abs(freed[0] - base_speed) < 1e-6 and not st["effects"].on_agent(HOSTILE),
          "a removed Deep Freeze (234, a hex with a snare) declares the wearer's 0x0027 base "
          "back -- remove_hexes re-sends the speed word after the close, as remove_conditions "
          "does for a cured Crippled",
          f"snared {snared} base {base_speed} at the removal {freed} out {got}")
    with arm(REMOVAL_NEEDS_AFFLICTION=True, CONDITION_HEAL_RULE=False):
        with rm_carried():
            st = world(authsrv)
            st["agents"][HOSTILE] = body(authsrv, (), agents.ALLEGIANCE_HOSTILE)
            st["agents"][ALLY] = body(authsrv, (), agents.ALLEGIANCE_HOSTILE)
            st["effects"].apply(HOSTILE, EMPATHY, 12, 30.0, T0, type_code=4, caster=HERO)
            with contextlib.redirect_stdout(io.StringIO()):
                got = authsrv.resolve_heal(lambda *a, **k: None, st, REMOVE_HEX, 0, ALLY,
                                           HOSTILE, 0)
            kept = len(st["effects"].on_agent(HOSTILE))
    check(got is None and kept == 1,
          "under --no-condition-heal-rule 301 removes nothing, as before (the removal rides "
          "the cure rule's flag)", f"{got} {kept}")


def section_rm_known_bad():
    print("== 7. (i) KNOWN-BAD ARM: --no-removal-needs-affliction is 642d8957's bytes ==")
    bar = ((RESTORE, 0.75, 2.0), (ORISON, 1.0, 2.0))
    ph = float(agents.PLAYER_HEALTH)
    # 642d8957 predates NPC_AFTERCAST as well (SKILLS-AC, merged in the same pass): its
    # hold delays the second cast by its aftercast, so the byte comparison turns it off.
    got = {"hostile": rm_run(bar, HOSTILE, secs=2.0, gate=False, aftercast=False)["sends"],
           "hero": rm_run(bar, HERO, secs=2.0, gate=False, aftercast=False,
                          player_health=0.4 * ph)["sends"]}
    on = {"hostile": rm_run(bar, HOSTILE, secs=2.0)["sends"],
          "hero": rm_run(bar, HERO, secs=2.0, player_health=0.4 * ph)["sends"]}
    for k in ("hostile", "hero"):
        want = RM_HEAD[k]
        check(got[k] == want,
              f"the {k}'s [276, 281] fight with a clean hurt ally, 2 s, gate OFF: every send "
              f"equals 642d8957's own ({len(want)} sends, 276 first at the clean ally)",
              f"first diff at {next((i for i, (a, b) in enumerate(zip(got[k], want)) if a != b), min(len(got[k]), len(want)))}"
              f" of {len(got[k])} / {len(want)}")
        check(on[k] != want and not any(v[:1] == [60] and v[-1] == RESTORE
                                         for _i, _op, v in on[k]),
              f"  and the gate ON sends no 276 announce at all ({k})")
    # REMOVE HEX UNDER THE REVERT (the review's EV-2). The flag is the lane's whole revert,
    # so a 301 must remove NOTHING under it -- at 642d8957 it had no effect row. The first
    # cut read `removes_hexes` under the cure rule's flag alone, so the revert aimed a
    # hero's 301 the old way (the hurt-most, here the hexed player) AND removed the hex,
    # and a self-hexed hostile's 301 at itself removed its own: a world no build ran.
    bar = ((REMOVE_HEX, 1.0, 8.0),)
    arms = {"hero": dict(who=HERO, wearer=P, player_health=0.4 * ph,
                         setup=lambda st: st["effects"].apply(
                             P, EMPATHY, 12, 30.0, T0 - 1.0, type_code=4, caster=HOSTILE)),
            "hostile": dict(who=HOSTILE, wearer=HOSTILE, player_health=1e9,
                            setup=lambda st: st["effects"].apply(
                                HOSTILE, EMPATHY, 12, 30.0, T0 - 1.0, type_code=4,
                                caster=HERO))}
    for k, a in arms.items():
        res = {}
        for gate in (False, True):
            r = rm_run(bar, a["who"], secs=1.5, gate=gate, setup=a["setup"],
                       player_health=a["player_health"])
            res[gate] = (r["sends"],
                         [ep["skill"] for ep in r["st"]["effects"].on_agent(a["wearer"])])
        want = RM_HEAD_301[k]
        check(res[False][0] == want and res[False][1] == [EMPATHY],
              f"the {k}'s 301 at a hexed {'player' if k == 'hero' else 'self'}, gate OFF: "
              f"every send equals 642d8957's own ({len(want)} sends) and the Empathy STAYS -- "
              f"the revert removes nothing, as 642d8957 did",
              f"left {res[False][1]}; first diff at "
              f"{next((i for i, (x, y) in enumerate(zip(res[False][0], want)) if x != y), min(len(res[False][0]), len(want)))}"
              f" of {len(res[False][0])} / {len(want)}")
        check(res[True][1] == [] and (k != "hero" or any(
                  op == authsrv.GAME_SMSG_EFFECT_REMOVE and v[0] == P
                  for _i, op, v in res[True][0])),
              f"  and the gate ON removes it ({k}: the Empathy gone"
              f"{', its 0x0044 shown to the player' if k == 'hero' else ''})",
              f"left {res[True][1]}")


def section_rm_source():
    print("== 7. (j) source checks: the flag, the two loops, never the selector ==")
    src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
    args = open(os.path.join(HERE, "serverargs.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    main_fn = _func(tree, "main")
    check('"--no-removal-needs-affliction"' in args
          and _flips(main_fn, "no_removal_needs_affliction", "REMOVAL_NEEDS_AFFLICTION")
          and authsrv.REMOVAL_NEEDS_AFFLICTION is True,
          "--no-removal-needs-affliction in serverargs, flipped in main() through a global, "
          "the gate ON at import")
    check(any(isinstance(n, ast.Assign) and n.col_offset == 0
              and [getattr(t, "id", None) for t in n.targets] == ["REMOVAL_NEEDS_AFFLICTION"]
              for n in tree.body),
          "REMOVAL_NEEDS_AFFLICTION is a column-0 module assignment")
    eat, act = _func(tree, "enemy_attack_tick"), _func(tree, "ally_cast_tick")
    check(len(_calls(eat, "removal_target")) == 1 and len(_calls(act, "removal_target")) == 1
          and len(_calls(eat, "live_effect_hold")) == 1
          and len(_calls(act, "live_effect_hold")) == 1,
          "removal_target is called once from each loop, and each loop still calls "
          "live_effect_hold exactly once (no second hold)")
    pk = _func(tree, "pick_skill")
    pk_src = ast.get_source_segment(src, pk)
    check(not _calls(pk, "removal_target") and "removal_target" not in pk_src
          and "removal_slot_class" not in pk_src and "REMOVAL_NEEDS" not in pk_src,
          "never from pick_skill: the selector stays the testing fixture")
    seg = ast.get_source_segment(src, eat)
    i_rm = seg.find("removal_target(state, agent_id, _kind, _rm)")
    i_heal = seg.find("hostile_heal_target(state, agent_id, _kind)")
    i_gate = seg.find("live_effect_hold(")
    check(0 <= i_rm < i_heal < i_gate,
          "in the hostile loop the removal step resolves the target AHEAD of the heal rule "
          "and the live-effect hold", f"rm {i_rm} heal {i_heal} gate {i_gate}")
    rh = _func(tree, "remove_hexes")
    check(len(_calls(_func(tree, "resolve_heal"), "remove_hexes")) == 1
          and not _calls(rh, "hex_end_burst") and len(_calls(rh, "effect_list_send")) == 1,
          "resolve_heal calls remove_hexes; remove_hexes closes through effect_list_send and "
          "never calls hex_end_burst")


# ---------------------------------------------------------------------------------
def section_rm_rows():
    """Vault-only: its SUBJECT is the vault's table, so it skips on the vault's content
    DIRECTORY being absent (test_agentlife's HAVE_VAULT_CONTENT rule) -- never on a row
    that will not load, which is a FAIL."""
    print("== 8. (a) the carried rows against the vault's own ==")
    if not os.path.isdir(vaultpath.vault_path("content")):
        LEDGER.skip("section 8 (a) (the carried rows): no vault content directory",
                    f"no directory at {vaultpath.vault_path('content')}")
        return
    bad = []
    for key, vals in RM_RECORD.items():
        try:
            row = agents.WORLD.get("skills", key)
        except content.ContentError as exc:
            bad.append((key, f"{exc}"[:60]))
            continue
        got = tuple(row.get(c) for c in RM_COLUMNS)
        if got != vals:
            bad.append((key, [(c, a, b) for c, a, b in zip(RM_COLUMNS, got, vals) if a != b]))
    check(not bad,
          f"every carried row equals the vault's loaded row, column for column "
          f"({len(RM_RECORD)} rows)", f"{bad}")


ZAISHEN = ("20260928T103123", "20260929T100038")


def section_rm_replay():
    """Vault-only: skips on the vault's live-captures DIRECTORY being absent; a present
    directory missing the two Zaishen tapes reads zero casts and FAILS the counts."""
    print("== 8. (b) the RETAIL removal casts, replayed through the real target step ==")
    if not os.path.isdir(vaultpath.vault_path("captures", "live")):
        LEDGER.skip("section 8 (b) (the retail replay): no vault live captures",
                    f"no directory at {vaultpath.vault_path('captures', 'live')}")
        return
    review = os.path.join(os.path.dirname(PARENT), "studies", "monsterai", "review")
    if review not in sys.path:
        sys.path.insert(0, review)
    import castethogram                                         # noqa: E402
    import capgaps                                              # noqa: E402
    real = castethogram.livewire.live_captures

    def only(root=None):
        return [(p, w) for p, w in real(root) if os.path.basename(p) in ZAISHEN]
    castethogram.livewire.live_captures = only
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            c = castethogram.census()
    finally:
        castethogram.livewire.live_captures = real
    gapped = {(s, conn.split("->")[0].rsplit(":", 1)[-1]) for s, conn in capgaps.KNOWN_GAPPED
              if s in ZAISHEN}
    refused = {(s, p) for s, p, _why in c["refused"]}
    check(refused == gapped,
          "castethogram over the two Zaishen tapes refuses exactly the manifest-declared "
          "gapped connection (capgaps.KNOWN_GAPPED) and nothing else", f"{c['refused']}")
    ai = [r for r in c["casts"] if r["class"] not in ("OBSERVER", "HUMAN")
          and r["skill"] in (MEND_COND, RESTORE, MEND_AIL, REMOVE_HEX)]
    by = {}
    for r in ai:
        by[r["skill"]] = by.get(r["skill"], 0) + 1

    def replay(r, aim="gate"):
        """Who the server would aim this retail cast at: the caster and its target as
        bodies, the target carrying what the TAPE says it carried (cond_bit / hexed_bit),
        its health the reconstruction's; a self-form cast's caster at that health. `aim`
        "gate" asks removal_target (the shipped step: None means the gate would HOLD
        it); "heal" asks hostile_heal_target -- the PRE-GATE rule, 642d8957's own aim for
        275-277 in both AI loops and for a party body's 301 (a hostile's 301 went at
        itself, which would miss every retail cast at another body)."""
        sid, caster, tgt = r["skill"], r["caster"], r["target"]
        kind = authsrv.skill_target_kind(sid)
        klass = episodemods.removal_class(authsrv.skill_effect_row(sid))
        h = float(r["h_target"])
        st = world(authsrv)
        st["agents"][caster] = body(authsrv, (), agents.ALLEGIANCE_HOSTILE,
                                    **({"health": 1000.0 * h, "max_health": 1000.0}
                                       if tgt == caster else {}))
        if tgt != caster:
            st["agents"][tgt] = body(authsrv, (), agents.ALLEGIANCE_HOSTILE,
                                     health=1000.0 * h, max_health=1000.0)
        bit = r.get("cond_bit") if klass == "condition" else r.get("hexed_bit")
        if bit:
            if klass == "condition":
                st["effects"].apply(tgt, BLEEDING, 0, 30.0, T0, type_code=8, caster=99)
            else:
                st["effects"].apply(tgt, EMPATHY, 12, 30.0, T0, type_code=4, caster=99)
        if aim == "heal":
            return authsrv.hostile_heal_target(st, caster, kind)
        return authsrv.removal_target(st, caster, kind, authsrv.removal_slot_class(sid))

    with arm(REMOVAL_NEEDS_AFFLICTION=True):
        held = [r for r in ai if replay(r) != r["target"]]
    # RE-AIMED 2026-10-07 (the review's EV-8): the known-bad arm used to be a 0.9 floor
    # the TEST applied before calling removal_target -- a recount of the tape's health
    # column that no server code could redden. It now asks the server's own pre-gate
    # rule, with the gate off.
    with arm(REMOVAL_NEEDS_AFFLICTION=False):
        missed = [r for r in ai if replay(r, aim="heal") != r["target"]]
    n_cure = by.get(MEND_COND, 0) + by.get(MEND_AIL, 0)
    check(by.get(MEND_COND, 0) >= 92 and by.get(MEND_AIL, 0) >= 14
          and by.get(REMOVE_HEX, 0) >= 10 and by.get(RESTORE, 0) == 0,
          "the retail AI removal casts are all there: 275 >= 92 (the Smiting Monks), 277 >= 14 "
          "and 301 >= 10 (the Elementalists and the henchman Healer; the 11th is on the gapped "
          "prefix), 276 none", f"{by}")
    n_self = sum(1 for r in ai if r["target"] == r["caster"])
    check(not held,
          f"the gate HOLDS 0 of the {len(ai)} retail removal casts and names retail's own "
          f"target every time ({n_cure} cures, {by.get(REMOVE_HEX, 0)} Remove Hex; {n_self} "
          f"of them self-form, all byte 3)", f"{[(r['capture'], r['t'], r['skill'], r['caster'], r['target']) for r in held][:5]}")
    by_bad = {}
    for r in missed:
        by_bad[r["skill"]] = by_bad.get(r["skill"], 0) + 1
    high = {}
    for r in ai:
        if float(r["h_target"]) >= authsrv.HERO_HEAL_AT:
            high[r["skill"]] = high.get(r["skill"], 0) + 1
    check(by_bad.get(MEND_COND, 0) == 2 and by_bad.get(REMOVE_HEX, 0) == 5
          and by_bad.get(MEND_AIL, 0) == 0 and by_bad == high,
          "KNOWN-BAD ARM, the pre-gate heal rule (hostile_heal_target, gate OFF -- server "
          "code): it misses exactly the retail casts at a target at or above HERO_HEAL_AT, "
          "2 of the 92 275s and 5 of the 10 Remove Hexes (the henchman Healer's 3 among "
          "them), 0 of 14 277s -- the replay can go red",
          f"missed {by_bad} at >= {authsrv.HERO_HEAL_AT}: {high}")


HEAD_SEQUENCE = [
    # (tick index, skill) -- 19213513, fight(Hatcher bar), gate absent. See the banner.
    (0, 276), (16, 253), (37, 312), (53, 289), (69, 276), (109, 289), (125, 276),
    (141, 253), (164, 289), (180, 276), (220, 312), (236, 289), (252, 276), (268, 253),
    (291, 289), (307, 276), (347, 289), (363, 276), (388, 253), (409, 312), (425, 289),
    (441, 276), (481, 289), (497, 276),
]
ON_SEQUENCE = [
    # (tick index, skill) -- fight(Hatcher bar), the live-effect gate, NPC_AFTERCAST AND
    # REMOVAL_NEEDS_AFFLICTION on. RE-RECORDED 2026-10-08 at the pass-9 landing on the
    # merged tree (the lane's record_on_sequence.py, LANE_ROOT = desk-pass9; two runs
    # identical, 57 casts in 120 s): desk-removal's gate holds the Hatcher's 276 at its
    # CLEAN hurt ally, so 276 leaves the cadence (the lane's own literal, recorded before
    # the gate merged, opened (0, 276), (30, 253) ...). Gaps stay activation + 0.75 s:
    # 35 ticks after 253, 30 after a 0.75 s spell; 289's longer waits are its recharge.
    (0, 253), (35, 312), (65, 289), (120, 289), (175, 289), (218, 312), (248, 289),
    (303, 289), (358, 289), (388, 253), (423, 312), (453, 289), (508, 289), (563, 289),
    (606, 312), (636, 289), (691, 289), (746, 289), (776, 253), (811, 312), (841, 289),
    (896, 289), (951, 289), (994, 312),
]


# THE REMOVAL GATE'S KNOWN-BAD LITERAL (section 7 (i)): every send of rm_run's [276, 281]
# fights, 2 s, gate OFF, recorded 2026-10-07 by driving THIS file's rm_run through
# `git show 642d8957:toolkit/authsrv/authsrv.py` (the scratch driver
# impl-desk-removal/rm_head_literal.py; the worktree's code with the gate off gave the
# same bytes). Tick 0: 276 announced at the CLEAN hurt ally (the hostile's 11, the hero's
# player 1); tick 15 its 58 and visual -- and no heal: it removed nothing.
# Remove Hex under the revert (section 7 (i), the review's EV-2): rm_run's [301] fights,
# 1.5 s, gate OFF -- a hero with the player at 0.4 carrying Empathy, and a hostile carrying
# Empathy itself -- recorded 2026-10-07 through `git show 642d8957:toolkit/authsrv/
# authsrv.py` (the scratch driver impl-desk-removal/fix/fx_head301.py). 642d8957 had no
# skill_effect.301 row, so neither cast removed anything.
RM_HEAD_301 = {
    'hero': [            # the hero's 301 at the hurt, hexed player: announced, completed, nothing
        (0, 0x002E, [200, 0, 1074137746]),
        (0, 0x00A0, [60, 200, 1, 301]),
        (20, 0x009F, [58, 200, 0]),
    ],
    'hostile': [         # a self-hexed hostile's 301 at itself (CASTAI-R2's byte-3 rule)
        (0, 0x002E, [10, 0, 1074137746]),
        (0, 0x009F, [60, 10, 301]),
        (20, 0x009F, [58, 10, 0]),
    ],
}

RM_HEAD = {
    'hostile': [
        (0, 0x002E, [10, 0, 1074137746]),
        (0, 0x00A0, [60, 10, 11, 276]),
        (15, 0x009F, [58, 10, 0]),
        (15, 0x00A0, [20, 11, 10, 491]),
        (16, 0x00A0, [60, 10, 11, 281]),
        (36, 0x009F, [58, 10, 0]),
        (36, 0x00A3, [55, 11, 10, 1041194025]),
    ],
    'hero': [
        (0, 0x002E, [200, 0, 1074137746]),
        (0, 0x00A0, [60, 200, 1, 276]),
        (15, 0x009F, [58, 200, 0]),
        (15, 0x00A0, [20, 1, 200, 491]),
        (16, 0x00A0, [60, 200, 1, 281]),
        (36, 0x009F, [58, 200, 0]),
        (36, 0x00A3, [55, 1, 200, 1060320051]),
    ],
}


def main():
    section_predicate()
    if section_hatcher():
        section_known_bad()
        section_classes()
    section_self_form()
    section_source()
    section_rm_predicate()
    section_rm_target()
    section_rm_driven()
    section_rm_hex()
    section_rm_known_bad()
    section_rm_source()
    section_rm_rows()
    section_rm_replay()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
