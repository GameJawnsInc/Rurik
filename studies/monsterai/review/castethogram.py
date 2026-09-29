#!/usr/bin/env python3
r"""The retail cast ethogram: every skill an AI body casts on retail's wire, with what it
was cast AT and what that target already carried. (DESKWORK-D8 step 2(c); monsterai FINDINGS section 9 row 13 -- NOT PLAN.md section 7 Q13, which is D1_LEAD)

    python studies/monsterai/review/castethogram.py            # tables + predictions
    python studies/monsterai/review/castethogram.py --rows     # plus one line per AI cast
    python studies/monsterai/review/castethogram.py --json     # the event list on stdout
    python studies/monsterai/review/castethogram.py --no-save  # do not write the vault files

WHY THIS EXISTS. The server's hostile and hero skill choice is `pick_skill` in
`toolkit/authsrv/authsrv.py`, a declared TESTING function (round robin; owner's ruling
2026-08-11) that re-casts a hex the target already carries (studies/skills 16.1). GWW
("Foe", rev 2674584, last edited 2021-08-29) says a monster's use of a skill "is embedded into the skill
itself", and heroes and henchmen share the AI (heroes 5.6) -- so a policy would be
per-SKILL data. Before one is written, this reads what retail's AI casters actually do.

READ-ONLY, LIVE ONLY. Captures come from `livewire.live_captures()` (origin LIVE via
`toolkit/origin.py`, so a loopback / our-server capture never pools with a live one);
every non-live directory is counted and printed as excluded. A connection whose byte
accounting does not close (`livewire.decode_conn` ok=False) or whose observer the two
rules do not agree on (`shoutjoin.observer_of`) is refused and counted. Exit 2 when
nothing observed is left to report.

DECODERS REUSED, NOT RE-DERIVED: `livewire.decode_conn` (framing), `shoutjoin.observer_of`
(property 41 x answered presses), `tape.client_version` (the connection's own BUILD and
map from its VERSION frame), `rechargeprobe.table_for` (activation / recharge read out
of the exe OF THAT BUILD), `agents.WORLD` skills rows (type, target byte, durations --
the pinned build's content table), `noticeradius.creates_of` / `HostileTrack` /
`player_reports` (positions), `henchjoin.party_of` (0x01BF henchman / 0x01C2 hero adds
created in the connection), `effects.TARGET_KINDS` (the target byte's CORROBORATED
codes). Definition identity is (BUILD, definition index) -- npcdefs' --build rule: a
definition index is never pooled across builds.

WIRE SHAPES, MEASURED OUT OF THIS CORPUS BEFORE THE READER WAS WRITTEN (decoded values
carry the header at v[0]; the monsterai 10 trap was reading 0x00A0 at the wrong index):
  0x00A0 [160, 60, caster, target, skill]   a targeted cast       373 in the corpus
  0x00A0 [160, 50, caster, target, skill]   an attack skill       333
  0x009F [159, 60, caster, skill]           an UNTARGETED cast    715 (NOT one NPC's
            oddity: monsterai 10's "NPC form" is the SELF / NO-TARGET form, used by
            every class incl. the observer (57). Recon, 2026-09-27: its skills' target
            byte is 0 (none/self) or 3 (ally, caster legal) or 1 (unresolved) -- never
            4 other-ally or 5 foe -- and 0x00A0 [60] names caster == target 0 of 373.
            So a 0x009F cast's target is the CASTER (RECONSTRUCTION, locked in L1).)
  0x009F [159, 48, caster, skill]           an instant (stance / shout), no target
  0x009F [159, 58|46|59|45|35, caster, 0]   finished / attack-finished / stopped / ...
  0x009F [159, 6|7, agent, id]              GV_ADD_EFFECT / GV_REMOVE_EFFECT on ANY body
            (id is an effect VISUAL, not the skill: 179 and 1097 both add 12 -- hexjoin L1)
  0x0042 [66, target, skill, field3, buff, f32] / 0x0044 [68, target, buff]
            effects BY SKILL ID, but only on the observer (and a hero) -- hexjoin G1
  0x00A0 [160, 4, attacker, target, 0]      attack started (noticeradius GV_ATTACK_STARTED)
  0x00A3 [163, 16|17|55, target, source, f32]  damage (negative) / heal (positive), in
            max-health fractions (agents.py 55 note: 16/17 negative 1,494 of 1,494)
  0x00A2 [162, 34, agent, f32]  the health SETTER -- 45 in the corpus, EVERY one on a
            create tick (recon); 0x00A2 [162, 44, agent, f32] the net regen rate
  0x00F1 [241, agent, status]   0x10 dead, 0x800 hexed, 0x02 a condition (hexjoin)
  0x0020 create: v[1] agent, v[2] tag<<28 | definition, v[4] kind, v[5] pos, v[12] token
  0x0056 [86, definition, file_id, 0, scale, 0, flags, profession, level, name]

THE CASTER'S CLASS (the order is the rule):
  OBSERVER    the connection's own player -- a human; counted, never scored.
  HUMAN       any other player: a class-tag-3 / kind-5 create, OR any caster on a PvP
              connection (the observer's own allegiance token is an arena team token
              'att*'). CAVEAT: on the Random Arenas tape 20260817T231139 the seven other
              players are class-tag-2 kind-9 creates with 0x0056 definitions, and the
              observer's three team-mates are even named by 0x01BF -- the wire does NOT
              separate them from AI bodies. They are HUMAN on the map's word and the
              repo's label (skills 56: "the observer's four-player team against
              another"), not on a byte.
  ZAISHEN     (2026-09-28, CASTAI-Z1; checked BEFORE the PvP rule above it would otherwise
              meet) on a ZAISHEN ARENA connection -- its map is one of ZAISHEN_MAPS AND
              the connection creates 0x01BF henchman adds -- a class-tag-2 body carrying an
              arena token ('att*') that is NOT the observer's: the four level-20 Zaishen
              opponents. AI (WIKI "Zaishen Challenge" rev 2707130: a PvE challenge mission,
              4 against 4 AI), but PvP-simulation AI of unknown tier (monsterai 18,
              CASTAI-W2), so it is its OWN population: never in AI_CLASSES, never pooled
              with MONSTER or the Isle. The map ids are the five MEASURED on
              20260928T103123 (tape.client_version of its four match connections: 320,
              318, 322, 318) and on 20260929T100038 (its five: 318, 321, 322, 319, 321);
              no other arena id is guessed, so an arena map not on either tape reads as
              the old PvP rule (HUMAN) until a tape measures it.
              On the same connection the observer's 0x01BF adds are HENCHMAN (AI: the
              outpost's Zaishen henchmen, WIKI "Zaishen Challenge (outpost)" rev 2724880).
              EVERY cast on a Zaishen arena connection carries `arena` = "zaishen" and is
              kept OUT of the pooled AI tables below (the headline stays the old corpus's);
              `studies/monsterai/review/zaishenrun.py` scores them.
  HERO        0x01C2 add created in this connection (henchjoin.party_of)
  HENCHMAN    0x01BF add created in this connection, on a non-PvP connection
  ALLY_NPC    the observer's allegiance token, no party add in this connection: an
              allied NPC, a minion or spirit, or a henchman whose add went out on an
              earlier connection -- NOT separable here; kept apart, never pooled.
  FRIENDLY    the 'nonc' (noncombatant) token -- which still FIGHTS: the MANTID tutorial's
              level-1 allies (38888:3116 / 3117, map 212) hex and nuke 'mon1' bodies,
              and the Isle's 38x:108 enchants the player with 160. A token mismatch
              with 'nonc' says nothing, so its target class is read off the skill's
              target byte and labelled "(byte)". (FRIENDLY joined the AI tables after
              the first run, which scored the other four classes only.)
  MONSTER     any other token ('mon1' on every hostile caster in the corpus)
  UNKNOWN     no create seen
The AI tables are MONSTER, HENCHMAN, HERO, ALLY_NPC and FRIENDLY, each on its own row,
over every connection that is NOT a Zaishen arena (`pooled_ai`).

PER CAST (all times on the capture clock): capture, conn, build, map, t, caster, its
incarnation (0x0020 count -- ids are RECYCLED, rechargeprobe), definition (build-scoped,
with file id / profession / level from 0x0056), class, form, skill, type, target byte,
TARGET (from the announce; the caster for a 0x009F form -- `target_how` says which), the
target's class (self / ally / foe by allegiance token), the target's and the caster's
health fraction (RECONSTRUCTION: a create with no 34 setter taken as full, then every
16/17/55 delta and the 44 regen integrated -- `h_how` says anchored or not; checked
against deaths in L2), whether the target already carried a LIVE EPISODE OF THE SAME
SKILL at the announce (below), any live [6] effect / the hexed bit / the condition bit,
the distance (both ends wire-parked = "wire"; otherwise dead-reckoned by HostileTrack =
"reckoned"; the observer's own end is its c2s self-report), the time since the caster's
previous cast (any skill), and the time since THIS SLOT was last ready (previous
completion + the build's recharge -- recharge from COMPLETION, D5 step 4), plus that gap
net of the caster's own busy time (its other casts' completion + the table aftercast).

A LIVE EPISODE of skill S on target T at time t:
  * OBSERVED-SKILL: a 0x0042 [T, S, ..., buff] with no 0x0044 [T, buff] yet (observer /
    hero only);
  * OBSERVED-VISUAL: a completed cast of S on T whose completion batch carried
    [6, T, x] for an x that is SKILL-SPECIFIC -- added by the completion batches of
    exactly one skill anywhere in the corpus -- and no [7, T, x] yet;
  * RECONSTRUCTED: a completed cast of an effect-type skill (stance 3, hex 4, enchantment
    6, preparation 19 -- effects.EFFECT_TYPES) with no skill-specific [6]: live while
    t < completion + duration0 ("certain" -- the shortest the rank allows) and
    "possible" up to completion + duration15.
  THE FIRST RUN GOT THIS WRONG, recorded rather than smoothed: it took every [6] id in a
  completion batch as that skill's own, and scored 5 P1 "counterexamples" that were one
  monster (38888:129) re-casting enchantment 164 at 61-62 s -- past its duration15 of 60
  -- behind [6] ids 11 and 13 that its THREE enchantments (164, 225, 180) all add and
  that stay up while any one of them lives. A shared id marks a class of effect, not a
  skill; `specific_ids()` now separates them and the table prints both sets.
  An episode also closes at T's next create (a re-create re-sends what is live) and at
  T's death.

THE PREDICTIONS, registered here BEFORE the first run of this reader (the orchestrator's
five, then this lane's own):

  P1  Retail AI never casts a hex or an enchantment on a target that already carries a
      live episode of the SAME skill (round robin's defect, skills 16.1) -- except a
      same-instant double (the prior episode opened < 0.5 s before the announce).
      Refuted by ONE observed-evidence counterexample; "possible" (duration15-only)
      overlaps are printed apart and do not refute.
  P2  An AI heal (a cast whose completion batch carries 0x00A3 [55, T, caster, f > 0] on
      its own target) lands on a HURT ally: reconstructed health < 0.99 OR a 16/17 on T
      inside the 10 s before the announce -- never on one at full health by both tests.
  P3  An AI caster re-casts a skill at the first opportunity: over re-casts whose previous
      cast completed, the median of (announce - (previous completion + recharge)) is
      <= 1.0 s. (The alternative is a deliberately held slot.)
  P4  A condition-removal (275, 276, 277, 278, 311) or hex-removal (301, 303) skill is cast
      only on a target carrying one ([6] live, or the 0x02 / 0x800 status bit). The ids
      are the content rows' and effects.py's WIKI-cited ones.
  P5  An offensive spell (type 4 or 5, target byte 5 foe) targets the caster's CURRENT
      attack target -- its latest 0x00A0 [4 | 50, caster, T] inside the 30 s before --
      where the caster has one.
  P6  (this lane) P3's gap is LONGER for hexes / enchantments than for type-5 spells:
      the median gap-from-ready of type 4/6 re-casts exceeds type 5's by >= 2 s -- the
      slot held while its episode lives.
  P7  (this lane) monsterai 9 row 13's bar is NOT met: no single AI definition reaches 30 casts of one
      skill across >= 2 sessions -- i.e. the corpus cannot yet support a per-skill
      policy histogram, only per-type rules.
  P8  (this lane) Monster hexes: the target is the caster's attack target or the
      observer in >= 90 % of casts (a hostile hexes whoever it is fighting).

LOCKED AFTER RECON, NOT PREDICTIONS (they were seen before this docstring was written):
  L1  every 0x009F [60] cast's skill carries target byte 0, 1 or 3; no 0x00A0 [60] names
      its caster as its target.
  L2  THE HEALTH INSTRUMENT: at every death (0x00F1 dead bit rising) of a body whose
      health is anchored, the reconstruction reads <= 0.10 in >= 80 % of them. If this
      fails, every health column is printed as UNVERIFIED and P2 falls back to its
      damage-inside-10-s half alone.

Standard library only. Reads the vault through `vaultpath`; writes only under
vault/research/castai-2026-09-27/ (gitignored). Never pools across origins or builds.
"""
import argparse
import bisect
import collections
import json
import math
import os
import statistics
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
for _sub in ("toolkit", "toolkit/authsrv", "toolkit/clientscan", "toolkit/schema"):
    _p = os.path.join(ROOT, _sub)
    if _p not in sys.path:
        sys.path.insert(0, _p)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import agents           # noqa: E402  (the client's skill rows, via content)
import effects          # noqa: E402  (TARGET_KINDS, EFFECT_TYPES)
import henchjoin        # noqa: E402  (party_of)
import livewire         # noqa: E402  (live_captures, decode_conn, capture_origin)
import noticeradius     # noqa: E402  (creates_of, HostileTrack, player_reports, report_at)
import rechargeprobe    # noqa: E402  (per-build activation / recharge from the exe)
import shoutjoin        # noqa: E402  (observer_of)
import tape             # noqa: E402  (channel_files, client_version)
import vaultpath        # noqa: E402

OP_CREATE, OP_REMOVE_AGENT = 0x0020, 0x0021
OP_FOLLOW = 0x002A
OP_APPLY, OP_UNAPPLY = 0x0042, 0x0044
OP_DEF = 0x0056
OP_INT, OP_INT_T, OP_FLOAT, OP_FLOAT_T = 0x009F, 0x00A0, 0x00A2, 0x00A3
OP_STATUS = 0x00F1
PROP_ATTACK_STARTED = 4
PROP_ADD_EFFECT, PROP_REMOVE_EFFECT = 6, 7
PROP_DMG = (16, 17)
PROP_HEALTH_SET = 34
PROP_REGEN = 44
PROP_HEAL = 55
PROP_INSTANT, PROP_ATTACK_SKILL, PROP_CAST = 48, 50, 60
END_PROPS = (58, 46, 59, 45, 35)
PROP_FINISHED, PROP_ATTACK_FINISHED = 58, 46
DEAD_BIT, HEX_BIT, COND_BIT = 0x10, 0x800, 0x02
BATCH = 0.05
DOUBLE_S = 0.5
HURT_WINDOW = 10.0
ATTACK_WINDOW = 30.0
HELD_S = 3.0
Q13_BAR = 30
EFFECT_TYPES = set(effects.EFFECT_TYPES) | {19}
TYPE_NAMES = {3: "Stance", 4: "Hex", 5: "Spell", 6: "Enchant", 7: "Signet", 8: "Cond",
              10: "Skill", 12: "Glyph", 14: "Attack", 15: "Shout", 19: "Prep"}
COND_REMOVAL = {275, 276, 277, 278, 311}
HEX_REMOVAL = {301, 303}
AI_CLASSES = ("MONSTER", "HENCHMAN", "HERO", "ALLY_NPC", "FRIENDLY")
# The Zaishen Challenge arena maps -- MEASURED (the client's own VERSION frame on each
# match connection, tape.client_version), and only those: on 20260928T103123 (CASTAI-Z1)
# 320 (match 1), 318 (matches 2 and 4), 322 (match 3); on 20260929T100038 (CASTAI-Z2)
# 318 (match 1, :57580), 321 (matches 2 and 5, :62925 / :64557), 322 (match 3, :51090)
# and 319 (match 4, :51199). Five ids over two tapes, each read off a match connection.
# The outpost's own 0x01D7 menu lists [321, 318, 320, 319, 322] (CASTAI-ZF3) -- the same
# five -- but the menu is not the source of this set: an id joins it when a match
# connection's VERSION frame carries it, and none has been taken from the menu.
ZAISHEN_MAPS = frozenset({318, 319, 320, 321, 322})
ARENA_CLASSES = ("ZAISHEN", "HENCHMAN")      # what an arena connection's AI is labelled
OUT_DIR_PARTS = ("research", "castai-2026-09-27")


def f32(bits):
    return struct.unpack("<f", struct.pack("<I", int(bits) & 0xFFFFFFFF))[0]


def fourcc(v):
    return noticeradius.fourcc(v)


def med(xs):
    return round(statistics.median(xs), 3) if xs else None


def pooled_ai(casts):
    """The AI casts the pooled tables score: an AI class, and NOT on a Zaishen arena
    connection (those are their own population -- zaishenrun.py)."""
    return [r for r in casts if r["class"] in AI_CLASSES and not r.get("arena")]


def arena_ai(casts):
    """The Zaishen arena connections' AI casts (ZAISHEN opponents, HENCHMAN adds)."""
    return [r for r in casts if r.get("arena") and r["class"] in ARENA_CLASSES]


def class_label(r):
    """The caster class as the ALL-CASTS census prints it: a cast on a Zaishen arena
    connection carries '@zaishen', so the old corpus's HENCHMAN (henchjoin adds on PvE
    connections) and the arena's HENCHMAN (the outpost's Zaishen henchmen) never print
    as one sum (fix 5, 2026-09-28: the first line read HENCHMAN 241 = 46 + 195)."""
    return r["class"] + ("@zaishen" if r.get("arena") else "")


# ------------------------------------------------------------------ the tables
def skill_rows():
    out = {}
    for k, r in agents.WORLD.rows("skills").items():
        try:
            out[int(k)] = r
        except (TypeError, ValueError):
            continue
    return out


# ------------------------------------------------------------------ one connection
class Conn:
    """One decoded game connection, indexed for the cast join."""

    def __init__(self, stamp, port, merged, observer, build, map_id):
        self.stamp, self.port, self.observer = stamp, port, observer
        self.build, self.map_id = build, map_id
        self.merged = merged
        self.s2c = [(t, op, v) for t, d, op, v in merged if d == "s2c"]
        self.times = [t for t, _o, _v in self.s2c]
        self.creates = noticeradius.creates_of(merged)       # agent -> [(t,pos,kind,tok,def,base,mult)]
        self.tag = {}
        self.defs = {}                                       # definition -> (file, prof, level)
        for t, op, v in self.s2c:
            if op == OP_CREATE and len(v) > 12:
                self.tag.setdefault(v[1], []).append((t, int(v[2]) >> 28))
            elif op == OP_DEF and len(v) > 8:
                self.defs[v[1]] = (v[2], v[7], v[8])
        self.party = henchjoin.party_of(merged)              # agent -> (prof, level)
        self.heroes = {int(v[3]) for _t, d, op, v in merged
                       if d == "s2c" and op == 0x01C2 and len(v) > 5}
        obs_c = self.creates.get(observer)
        self.obs_token = obs_c[0][3] if obs_c else None
        self.pvp = bool(self.obs_token and self.obs_token.startswith("att"))
        # a Zaishen arena: one of the MEASURED maps AND 0x01BF henchman adds (not heroes)
        self.hench = set(self.party) - self.heroes
        self.zaishen = self.map_id in ZAISHEN_MAPS and bool(self.hench)
        self.reports = noticeradius.player_reports(merged)
        self._tracks = {}
        self._build_timelines()

    # -- timelines ------------------------------------------------------------
    def _build_timelines(self):
        self.health_ev = collections.defaultdict(list)   # agent -> [(t, kind, val)]
        self.effects6 = collections.defaultdict(list)    # agent -> [(t, +1|-1, id)]
        self.applies = collections.defaultdict(list)     # target -> [(t, skill, buff, dur, s2c index)]
        self.unapplies = collections.defaultdict(list)   # target -> [(t, buff, s2c index)]
        self.status = collections.defaultdict(list)      # agent -> [(t, word)]
        self.attack_starts = collections.defaultdict(list)  # attacker -> [(t, target)]
        self.follows = collections.defaultdict(list)     # agent -> [(t, target)]
        self.announces = []                              # (t, idx, caster, target|None, skill, prop, form)
        self.ends = collections.defaultdict(list)        # caster -> [(t, idx, prop)]
        self.damage_on = collections.defaultdict(list)   # target -> [(t, source, f)]
        self.heals = collections.defaultdict(list)       # target -> [(t, source, f)]
        self.create_t = collections.defaultdict(list)
        self.set34 = []
        for i, (t, op, v) in enumerate(self.s2c):
            if op == OP_CREATE and len(v) > 12:
                self.create_t[v[1]].append(t)
                self.health_ev[v[1]].append((t, "create", None))
            elif op == OP_FLOAT and len(v) > 3:
                if v[1] == PROP_HEALTH_SET:
                    self.health_ev[v[2]].append((t, "set", f32(v[3])))
                    self.set34.append(f32(v[3]))
                elif v[1] == PROP_REGEN:
                    self.health_ev[v[2]].append((t, "regen", f32(v[3])))
                elif v[1] in PROP_DMG + (PROP_HEAL,):
                    self.health_ev[v[2]].append((t, "delta", f32(v[3])))
            elif op == OP_FLOAT_T and len(v) > 4:
                if v[1] in PROP_DMG + (PROP_HEAL,):
                    x = f32(v[4])
                    self.health_ev[v[2]].append((t, "delta", x))
                    if v[1] in PROP_DMG:
                        self.damage_on[v[2]].append((t, v[3], x))
                    else:
                        self.heals[v[2]].append((t, v[3], x))
                elif v[1] == PROP_HEALTH_SET:
                    self.health_ev[v[2]].append((t, "set", f32(v[4])))
            elif op == OP_STATUS and len(v) > 2:
                self.status[v[1]].append((t, int(v[2])))
                if int(v[2]) & DEAD_BIT:
                    self.health_ev[v[1]].append((t, "dead", None))
            elif op == OP_APPLY and len(v) > 5:
                self.applies[v[1]].append((t, v[2], v[4], f32(v[5]), i))
            elif op == OP_UNAPPLY and len(v) > 2:
                self.unapplies[v[1]].append((t, v[2], i))
            elif op == OP_INT and len(v) > 3:
                if v[1] in (PROP_ADD_EFFECT, PROP_REMOVE_EFFECT):
                    self.effects6[v[2]].append((t, 1 if v[1] == PROP_ADD_EFFECT else -1, v[3]))
                elif v[1] in (PROP_CAST, PROP_INSTANT):
                    self.announces.append((t, i, v[2], None, v[3], v[1], f"9F[{v[1]}]"))
                elif v[1] in END_PROPS:
                    self.ends[v[2]].append((t, i, v[1]))
            elif op == OP_INT_T and len(v) > 4:
                if v[1] in (PROP_CAST, PROP_ATTACK_SKILL):
                    self.announces.append((t, i, v[2], v[3], v[4], v[1], f"A0[{v[1]}]"))
                if v[1] in (PROP_ATTACK_STARTED, PROP_ATTACK_SKILL):
                    self.attack_starts[v[2]].append((t, v[3]))
            elif op == OP_FOLLOW and len(v) > 5:
                self.follows[v[1]].append((t, v[5]))
        self.by_caster = collections.defaultdict(list)
        for a in self.announces:
            self.by_caster[a[2]].append(a)

    # -- identity -------------------------------------------------------------
    def create_at(self, agent, t):
        rows = [c for c in self.creates.get(agent, ()) if c[0] <= t]
        return rows[-1] if rows else None

    def incarnation(self, agent, t):
        return sum(1 for ct in self.create_t.get(agent, ()) if ct <= t)

    def tag_at(self, agent, t):
        rows = [g for ct, g in self.tag.get(agent, ()) if ct <= t]
        return rows[-1] if rows else None

    def token(self, agent, t):
        c = self.create_at(agent, t)
        return c[3] if c else None

    def klass(self, agent, t):
        if agent == self.observer:
            return "OBSERVER"
        c = self.create_at(agent, t)
        if c is None:
            return "UNKNOWN"
        if self.tag_at(agent, t) == 3 or c[2] == 5:
            return "HUMAN"
        if self.zaishen:
            if agent in self.hench:
                return "HENCHMAN"
            if c[3].startswith("att") and c[3] != self.obs_token and self.tag_at(agent, t) == 2:
                return "ZAISHEN"
        if self.pvp and c[3].startswith("att"):
            return "HUMAN"
        if agent in self.heroes:
            return "HERO"
        if agent in self.party:
            return "HENCHMAN"
        if c[3] == self.obs_token:
            return "ALLY_NPC"
        if c[3] == "nonc":
            return "FRIENDLY"
        return "MONSTER"

    def definition(self, agent, t):
        c = self.create_at(agent, t)
        if c is None or self.tag_at(agent, t) != 2:
            return None
        return c[4]

    # -- health ---------------------------------------------------------------
    def health_at(self, agent, t, use_dead=True):
        """(fraction, how) just before t, or (None, why). RECONSTRUCTION. With
        use_dead=False the dead bit does not zero it (L2 must not be forced true)."""
        evs = self.health_ev.get(agent)
        if not evs:
            return None, "no create"
        h, how, rate, last = None, None, 0.0, None
        for (te, kind, val) in evs:
            if te >= t - 1e-9:
                break
            if h is not None and last is not None and rate:
                h = min(1.0, max(0.0, h + rate * (te - last)))
            last = te
            if kind == "create":
                h, how, rate = 1.0, "create-full (no 34)", 0.0
            elif kind == "set":
                h, how = max(0.0, min(1.0, val)), "anchored (34)"
            elif kind == "regen":
                rate = val
            elif kind == "delta" and h is not None:
                h = max(0.0, min(1.0, h + val))
            elif kind == "dead" and use_dead:
                h = 0.0
        if h is None:
            return None, "no create before"
        if last is not None and rate:
            h = min(1.0, max(0.0, h + rate * (t - last)))
        return round(h, 4), how

    # -- effects ----------------------------------------------------------------
    def live6(self, agent, t):
        """Ids of [6, agent, id] live just before t (reset at each create)."""
        live = collections.Counter()
        ct = [c for c in self.create_t.get(agent, ()) if c < t - 1e-9]
        since = ct[-1] if ct else -1e18
        for (te, sgn, eid) in self.effects6.get(agent, ()):
            if te >= t - 1e-9:
                break
            if te < since:
                continue
            if sgn > 0:
                live[eid] += 1
            elif live[eid] > 0:
                live[eid] = 0
        return sorted(k for k, n in live.items() if n > 0)

    def status_at(self, agent, t):
        w = None
        for (te, word) in self.status.get(agent, ()):
            if te >= t - 1e-9:
                break
            w = word
        return w

    def batch_ops(self, t):
        lo = bisect.bisect_left(self.times, t - BATCH)
        hi = bisect.bisect_right(self.times, t + BATCH)
        return self.s2c[lo:hi]

    # -- positions --------------------------------------------------------------
    def pos(self, agent, t):
        """((x, y), 'wire'|'reckoned'|'self-report', age) or (None, why, None)."""
        if agent == self.observer:
            r = noticeradius.report_at(self.reports, t)
            if r is None:
                return None, "no self-report", None
            return r[1], "self-report", round(t - r[0], 2)
        c = self.create_at(agent, t)
        if c is None:
            return None, "no create", None
        key = (agent, c[0])
        tr = self._tracks.get(key)
        if tr is None:
            stream = [(tt, op, v) for (tt, op, v) in self.s2c
                      if len(v) >= 2 and v[1] == agent and tt >= c[0]]
            tr = noticeradius.HostileTrack(stream, c)
            self._tracks[key] = tr
        p, observed, _moving, _n = tr.pos_at(t)
        return p, ("wire" if observed else "reckoned"), None


# ------------------------------------------------------------------ the join
def completion(conn, caster, ta, idx, act):
    """(t_end, prop) of the caster's end word for the announce at (ta, idx), or
    (None, 'superseded'|'no end'). The end belongs to the caster's most recent
    announce; for act > 0 an end earlier than ta + act/2 is the PREVIOUS cast's.

    The announce that SUPERSEDES this one is the caster's next announce that has an end
    word of its own -- never an instant 0x009F [48] (a stance / shout: no end word,
    build_casts). FIXED 2026-09-28 (CASTAI-Z1 judge, fix 1): `nxt` used to be the next
    announce of ANY form, so a stance fired mid-cast (the Zaishen Necromancer's skill 11)
    marked the in-flight cast 'superseded' although its 58 followed on time -- on
    20260928T103123 match 1 159.98 skill 133, match 2 313.19 135 -> observer (its 0x0042
    at 314.195) and 342.94 109 -> Archer (its [58] at 343.936)."""
    nxt = None
    for a in conn.by_caster.get(caster, ()):
        if a[5] == PROP_INSTANT:
            continue
        if (a[0], a[1]) > (ta, idx):
            nxt = (a[0], a[1])
            break
    lo = ta + (0.5 * act if act else 0.0)
    for (te, i, prop) in conn.ends.get(caster, ()):
        if (te, i) <= (ta, idx) or te < lo - 1e-9:
            continue
        if te > ta + act + 5.0:
            break
        if nxt is not None and (te, i) > nxt:
            return None, "superseded"
        return te, prop
    return None, ("superseded" if nxt is not None else "no end")


def build_casts(conn, table, rec_table, stats):
    """Every announce on the connection, joined."""
    out = []
    last_any = {}                   # (caster, inc) -> (t, t_end_eff)
    last_slot = {}                  # (caster, inc, skill) -> (ta, t_end, prop)
    busy = collections.defaultdict(list)   # (caster, inc) -> [(ta, t_free)]
    for (ta, idx, caster, target, skill, prop, form) in conn.announces:
        row = table.get(skill, {})
        typ = row.get("type_code")
        tbyte = row.get("target")
        if rec_table is not None and skill in rec_table:
            act, rech = rec_table[skill]
            table_src = f"exe {conn.build}"
        else:
            act = float(row.get("activation") or 0.0)
            rech = float(row.get("recharge") or 0.0)
            table_src = "content (pinned)"
        aftercast = float(row.get("aftercast") or 0.0)
        if prop == PROP_INSTANT:
            # an instant has no end word of its own; the first end word after it is
            # the caster's PREVIOUS attack skill finishing (fixed after the first run,
            # which read the JARIN hero's stance 346 as re-cast 1 s before ready)
            te, eprop = ta, "instant"
        else:
            te, eprop = completion(conn, caster, ta, idx, act)
        inc = conn.incarnation(caster, ta)
        klass = conn.klass(caster, ta)
        if target is None and prop == PROP_CAST:
            tgt, target_how = caster, "caster (0x009F self form)"
        elif target is None and typ == 3:
            tgt, target_how = caster, "caster (a stance: effects.py, the wearer is the caster)"
        elif target is None:
            tgt, target_how = None, "none (instant; a shout's recipients are not named)"
        else:
            tgt, target_how = target, "announce"
        # target class by token
        if tgt is None:
            tclass = None
        elif tgt == caster:
            tclass = "self"
        else:
            a, b = conn.token(caster, ta), conn.token(tgt, ta)
            if a is None or b is None:
                tclass = None
            elif a == b:
                tclass = "ally"
            elif "nonc" in (a, b):
                # a noncombatant token differs from everyone's, so a token mismatch says
                # nothing (the Isle's 108 enchants the PLAYER with 160); the skill's own
                # target byte decides, and the label says so
                tclass = {5: "foe", 3: "ally", 4: "ally", 6: "ally"}.get(tbyte, "other") + "(byte)"
            else:
                tclass = "foe"
        rec = {
            "capture": conn.stamp, "port": conn.port, "build": conn.build,
            "map": conn.map_id, "t": round(ta, 3), "caster": caster, "inc": inc,
            "arena": "zaishen" if getattr(conn, "zaishen", False) else None,
            "class": klass, "form": form, "skill": skill, "type": typ,
            "type_name": TYPE_NAMES.get(typ, str(typ)), "target_byte": tbyte,
            "target_byte_kind": effects.TARGET_KINDS.get(tbyte, "unresolved"),
            "activation": act, "recharge": rech, "table_src": table_src,
            "end_t": None if te is None else round(te, 3), "end_prop": eprop,
            "target": tgt, "target_how": target_how, "target_class": tclass,
            "target_klass": None if tgt is None else conn.klass(tgt, ta),
        }
        d = conn.definition(caster, ta)
        rec["definition"] = d
        rec["def_key"] = None if d is None else f"{conn.build}:{d}"
        rec["def_info"] = conn.defs.get(d) if d is not None else None   # (file, prof, level)
        # health
        rec["h_caster"], rec["h_caster_how"] = conn.health_at(caster, ta)
        if tgt is not None:
            rec["h_target"], rec["h_target_how"] = conn.health_at(tgt, ta)
            dmg = [x for x in conn.damage_on.get(tgt, ()) if ta - HURT_WINDOW <= x[0] < ta]
            rec["dmg_on_target_10s"] = len(dmg)
            rec["live6_target"] = conn.live6(tgt, ta)
            st = conn.status_at(tgt, ta)
            rec["status_target"] = st
            rec["hexed_bit"] = None if st is None else bool(st & HEX_BIT)
            rec["cond_bit"] = None if st is None else bool(st & COND_BIT)
        # distance
        if tgt is not None and tgt != caster:
            pc, hc, _ = conn.pos(caster, ta)
            pt, ht, age = conn.pos(tgt, ta)
            if pc is not None and pt is not None:
                rec["dist"] = round(math.hypot(pc[0] - pt[0], pc[1] - pt[1]), 1)
                rec["dist_how"] = f"{hc}/{ht}" + (f" ({age}s)" if age is not None else "")
            else:
                rec["dist"], rec["dist_how"] = None, f"{hc}/{ht}"
        # the caster's attack target
        prior_att = [x for x in conn.attack_starts.get(caster, ()) if ta - ATTACK_WINDOW <= x[0] < ta]
        rec["attack_target"] = prior_att[-1][1] if prior_att else None
        prior_fol = [x for x in conn.follows.get(caster, ()) if ta - ATTACK_WINDOW <= x[0] < ta]
        rec["follow_target"] = prior_fol[-1][1] if prior_fol else None
        # timing
        ck = (caster, inc)
        pa = last_any.get(ck)
        rec["since_prev_cast"] = None if pa is None else round(ta - pa[0], 3)
        ps = last_slot.get((caster, inc, skill))
        if ps is None:
            rec["since_ready"] = None
            rec["since_ready_how"] = "first cast seen"
        else:
            pta, pte, pprop, _ptg = ps
            if pte is None:
                rec["since_ready"] = round(ta - (pta + rech), 3)
                rec["since_ready_how"] = "previous uncompleted (announce + recharge)"
            else:
                rec["since_ready"] = round(ta - (pte + rech), 3)
                rec["since_ready_how"] = "completion + recharge"
            ready = (pte if pte is not None else pta) + rech
            frees = [f for (s, f) in busy[ck] if s < ta and f > ready]
            free_at = max([ready] + frees)
            # NOTE (after the first run): for a caster that is never idle this is the
            # time since its LAST cast of anything ended, not a property of this slot;
            # `passed_over` is the slot's own measure.
            rec["since_free"] = round(ta - free_at, 3)
            # the caster's announces of OTHER skills after this slot was ready: 0 means
            # this was the first thing it cast once the slot came back
            rec["passed_over"] = sum(1 for a in conn.by_caster.get(caster, ())
                                     if ready < a[0] < ta and a[4] != skill
                                     and conn.incarnation(caster, a[0]) == inc)
            rec["prev_same_target"] = _ptg
            rec["prev_completion_age"] = None if pte is None else round(ta - pte, 3)
            d0_, d15_ = float(row.get("duration0") or 0), float(row.get("duration15") or 0)
            # was the slot ready while the previous episode was still certainly live?
            rec["ready_inside_d0"] = (pte is not None and typ in EFFECT_TYPES
                                      and 0 < d0_ < 100000 and rech < d0_)
            rec["age_minus_d15"] = (round(ta - pte - d15_, 3) if pte is not None
                                    and typ in EFFECT_TYPES and 0 < d15_ < 100000 else None)
        # effects this cast put on its target (the episode store is built in pass 2)
        rec["adds_on_target"], rec["heal_on_target"] = [], None
        rec["damage_by_caster_on_target"] = None
        if te is not None and tgt is not None:
            for (tb, op, v) in conn.batch_ops(te):
                if op == OP_INT and len(v) > 3 and v[1] == PROP_ADD_EFFECT and v[2] == tgt:
                    rec["adds_on_target"].append(v[3])
                if op == OP_FLOAT_T and len(v) > 4 and v[1] == PROP_HEAL and v[2] == tgt \
                        and v[3] == caster:
                    rec["heal_on_target"] = round((rec["heal_on_target"] or 0.0) + f32(v[4]), 5)
            rec["damage_by_caster_on_target"] = any(
                op == OP_FLOAT_T and len(v) > 4 and v[1] in PROP_DMG and v[2] == tgt and v[3] == caster
                for (tb, op, v) in conn.batch_ops(te))
        rec["_ta"], rec["_te"], rec["_d0"], rec["_d15"] = ta, te, \
            float(row.get("duration0") or 0), float(row.get("duration15") or 0)
        # bookkeeping
        last_any[ck] = (ta,)
        last_slot[(caster, inc, skill)] = (ta, te, eprop, tgt)
        busy[ck].append((ta, (te if te is not None else ta + act) + aftercast))
        out.append(rec)
    return out


def specific_ids(casts):
    """{visual id: skill} for the [6] ids that exactly ONE skill's completion batches
    ever add across the corpus. A shared id (hexjoin L1's 1 on every hex; 11 / 13 on
    every enchantment of 38888:129) marks a CLASS of effect, not a skill, and closes
    only when the last effect of that class ends -- so it cannot date an episode."""
    by_id = collections.defaultdict(set)
    for r in casts:
        for x in r["adds_on_target"]:
            by_id[x].add(r["skill"])
    return ({x: next(iter(sk)) for x, sk in by_id.items() if len(sk) == 1},
            {x: sorted(sk) for x, sk in by_id.items() if len(sk) > 1})


def episodes_pass(conn, rows, specific):
    """Pass 2 on one connection: the live-episode columns, in announce order."""
    eps = collections.defaultdict(list)      # target -> [episode]
    for r in rows:
        ta, tgt, skill = r["_ta"], r["target"], r["skill"]
        if tgt is not None:
            r.update(episode_state(conn, eps, tgt, skill, ta))
            others = {e["skill"] for e in eps.get(tgt, ())}
            r["any_episode"] = any(
                episode_state(conn, eps, tgt, s2, ta)["same_live"] in ("observed", "certain")
                for s2 in others) or bool(applies_live(conn, tgt, ta))
        if r["_te"] is not None and tgt is not None:
            ids = {x for x in r["adds_on_target"] if specific.get(x) == skill}
            if ids:
                eps[tgt].append({"skill": skill, "t0": r["_te"], "ids": ids, "how": "visual"})
            elif r["type"] in EFFECT_TYPES and 0 < r["_d0"] < 100000:
                eps[tgt].append({"skill": skill, "t0": r["_te"], "d0": r["_d0"],
                                 "d15": r["_d15"], "how": "duration"})


def applies_live(conn, tgt, ta):
    """[(skill, age)] of 0x0042 applies on tgt live at ta (observer / hero only)."""
    out = []
    for (t, s, buff, dur, ia) in conn.applies.get(tgt, ()):
        if t >= ta - 1e-9:
            continue
        gone = [u for (u, b, iu) in conn.unapplies.get(tgt, ()) if b == buff and iu > ia and u < ta]
        if not gone:
            out.append((s, round(ta - t, 3)))
    return out


def episode_state(conn, eps, tgt, skill, ta):
    """{'same_live': 'observed'|'certain'|'possible'|None, 'same_age', 'same_how'}."""
    for (s, age) in applies_live(conn, tgt, ta):
        if s == skill:
            return {"same_live": "observed", "same_age": age, "same_how": "0x0042"}
    creates = [c for c in conn.create_t.get(tgt, ()) if c < ta]
    last_create = creates[-1] if creates else -1e18
    deaths = [t for (t, w) in conn.status.get(tgt, ()) if (w & DEAD_BIT) and t < ta]
    floor = max(last_create, deaths[-1] if deaths else -1e18)
    best = None
    rank = {"observed": 3, "certain": 2, "possible": 1}
    for ep in eps.get(tgt, ()):
        if ep["skill"] != skill or ep["t0"] >= ta or ep["t0"] < floor:
            continue
        age = ta - ep["t0"]
        if ep["how"] == "visual":
            ended = any(ep["t0"] + BATCH < te_ < ta and sgn < 0 and eid in ep["ids"]
                        for (te_, sgn, eid) in conn.effects6.get(tgt, ()))
            cand = None if ended else {"same_live": "observed", "same_age": round(age, 3),
                                       "same_how": "[6] skill-specific visual"}
        elif age < ep["d0"]:
            cand = {"same_live": "certain", "same_age": round(age, 3), "same_how": "< duration0"}
        elif age < ep["d15"]:
            cand = {"same_live": "possible", "same_age": round(age, 3), "same_how": "< duration15"}
        else:
            cand = None
        if cand and (best is None or rank[cand["same_live"]] > rank[best["same_live"]]):
            best = cand
    out = best or {"same_live": None, "same_age": None, "same_how": None}
    out["same_ended_ago"] = None if best else ended_ago(conn, eps, tgt, skill, ta, floor)
    return out


def ended_ago(conn, eps, tgt, skill, ta, floor):
    """Seconds since the target's last OBSERVED end of a same-skill episode (a 0x0044 of
    its 0x0042 buff, or the [7] of a skill-specific visual), or None. POST-HOC: the
    reaction latency of a re-cast that waited for the expiry."""
    ends = []
    for (t, s2, buff, dur, ia) in conn.applies.get(tgt, ()):
        if s2 != skill or t >= ta:
            continue
        us = [u for (u, b, iu) in conn.unapplies.get(tgt, ()) if b == buff and iu > ia and u < ta]
        if us:
            ends.append(min(us))
    for ep in eps.get(tgt, ()):
        if ep["skill"] != skill or ep["how"] != "visual" or ep["t0"] >= ta:
            continue
        us = [te_ for (te_, sgn, eid) in conn.effects6.get(tgt, ())
              if ep["t0"] + BATCH < te_ < ta and sgn < 0 and eid in ep["ids"]]
        if us:
            ends.append(min(us))
    ends = [e for e in ends if e >= floor]
    return round(ta - max(ends), 3) if ends else None


# ------------------------------------------------------------------ the census
def census():
    root = vaultpath.require_dir("captures", "live", why="castethogram reads live captures")
    all_dirs = sorted(d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d)))
    live = livewire.live_captures(root)
    live_names = {os.path.basename(p) for p, _w in live}
    excluded_origin = []
    for d in all_dirs:
        if d not in live_names:
            who, why = livewire.capture_origin(os.path.join(root, d))
            excluded_origin.append((d, who, (why or "")[:60]))
    table = skill_rows()
    exe_by_build = rechargeprobe._exe_tables()
    refused, conns_ok, casts = [], 0, []
    set34 = []
    deaths = []
    per_conn = []
    for capdir, _who in live:
        stamp = os.path.basename(capdir)
        for ch in tape.channel_files(capdir):
            port = ch["connection"].split("->")[0].rsplit(":", 1)[-1]
            try:
                _c, merged, ok = livewire.decode_conn(capdir, ch["file"])
            except Exception as exc:                              # noqa: BLE001
                refused.append((stamp, port, f"decode: {str(exc)[:60]}"))
                continue
            if not ok:
                refused.append((stamp, port, "byte accounting open"))
                continue
            observer, _p, why = shoutjoin.observer_of(merged)
            if observer is None:
                refused.append((stamp, port, (why or "")[:70]))
                continue
            try:
                ver = tape.client_version(capdir, ch["connection"])
                build, map_id = ver["build"], ver["map_id"]
            except Exception as exc:                              # noqa: BLE001
                refused.append((stamp, port, f"no VERSION: {str(exc)[:50]}"))
                continue
            conns_ok += 1
            conn = Conn(stamp, port, merged, observer, build, map_id)
            set34.extend(conn.set34)
            rec_table = rechargeprobe.table_for(build, exe_by_build)
            rows = build_casts(conn, table, rec_table, None)
            casts.extend(rows)
            per_conn.append((conn, rows))
            deaths.extend(death_checks(conn))
    specific, shared = specific_ids(casts)
    for conn, rows in per_conn:
        episodes_pass(conn, rows, specific)
    for r in casts:
        for k in ("_ta", "_te", "_d0", "_d15"):
            r.pop(k, None)
    return {"casts": casts, "refused": refused, "connections": conns_ok,
            "specific_ids": specific, "shared_ids": shared,
            "captures": len(live), "excluded_origin": excluded_origin,
            "set34": set34, "deaths": deaths, "exe_builds": sorted(exe_by_build)}


def death_checks(conn):
    """L2: the reconstruction at every dead-bit rising edge of a non-observer."""
    out = []
    for agent, ws in conn.status.items():
        if agent == conn.observer:
            continue
        prev = 0
        for (t, w) in ws:
            if (w & DEAD_BIT) and not (prev & DEAD_BIT):
                h, how = conn.health_at(agent, t, use_dead=False)
                # the killing batch's own deltas are applied: read just after the batch,
                # and the dead bit itself is NOT allowed to zero the reading
                h2, _ = conn.health_at(agent, t + BATCH, use_dead=False)
                out.append({"capture": conn.stamp, "port": conn.port, "agent": agent,
                            "t": round(t, 3), "h_before": h, "h_after_batch": h2, "how": how})
            prev = w
    return out


# ------------------------------------------------------------------ scoring
def score(c):
    casts = c["casts"]
    ai = pooled_ai(casts)
    s = {"n_all": len(casts), "by_class": collections.Counter(class_label(r) for r in casts),
         "n_ai": len(ai), "n_arena": sum(1 for r in casts if r.get("arena"))}
    # L1
    l1_9f = [r for r in casts if r["form"] == "9F[60]"]
    s["l1_9f_bytes"] = collections.Counter(r["target_byte"] for r in l1_9f)
    s["l1_a0_self"] = sum(1 for r in casts if r["form"] == "A0[60]" and r["target"] == r["caster"])
    s["l1"] = all(b in (0, 1, 3) for b in s["l1_9f_bytes"] if b is not None) and s["l1_a0_self"] == 0
    # 9F self-form corroboration: completion batch effect on the caster
    self_ev = [r for r in l1_9f if r["end_t"] is not None and r["class"] != "OBSERVER"]
    s["l1_self_evidence"] = (sum(1 for r in self_ev if r["adds_on_target"] or r["heal_on_target"]),
                             len(self_ev))
    # L2
    dd = [d for d in c["deaths"] if d["h_after_batch"] is not None]
    low = [d for d in dd if d["h_after_batch"] <= 0.10]
    s["l2"] = (len(low), len(dd))
    s["l2_ok"] = bool(dd) and len(low) >= 0.8 * len(dd)
    s["set34_values"] = sorted(round(x, 3) for x in c["set34"])
    # P1
    eff = [r for r in ai if r["type"] in (4, 6) and r.get("target") is not None]
    p1_obs = [r for r in eff if r.get("same_live") in ("observed", "certain")]
    p1_double = [r for r in p1_obs if (r.get("same_age") or 99) < DOUBLE_S]
    p1_cx = [r for r in p1_obs if (r.get("same_age") or 99) >= DOUBLE_S]
    p1_poss = [r for r in eff if r.get("same_live") == "possible"]
    s["p1"] = {"n": len(eff), "n_completed_prior_known": len(eff),
               "overlap_observed_or_certain": len(p1_obs), "doubles": len(p1_double),
               "counterexamples": len(p1_cx), "possible_only": len(p1_poss),
               "holds": len(p1_cx) == 0 and len(eff) > 0,
               "cx_rows": [short(r) for r in p1_cx][:40],
               "by_class": collections.Counter((r["class"], r.get("same_live")) for r in eff)}
    # P2
    heals = [r for r in ai if r.get("heal_on_target") is not None and r["heal_on_target"] > 0]
    def hurt(r):
        h = r.get("h_target")
        return (h is not None and h < 0.99) or (r.get("dmg_on_target_10s") or 0) > 0
    full = [r for r in heals if not hurt(r)]
    s["p2"] = {"n": len(heals), "full_by_both": len(full), "holds": bool(heals) and not full,
               "full_rows": [short(r) for r in full][:40],
               "h_target": [r.get("h_target") for r in heals],
               "by_class": collections.Counter((r["class"], r["target_class"]) for r in heals),
               "damage_half_only_full": sum(1 for r in heals if not r.get("dmg_on_target_10s"))}
    # P3 / P6
    rc = [r for r in ai if r.get("since_ready_how") == "completion + recharge"]
    gaps = [r["since_ready"] for r in rc]
    s["p3"] = {"n": len(rc), "median": med(gaps), "p_le_1": sum(1 for g in gaps if g <= 1.0),
               "p_gt_held": sum(1 for g in gaps if g > HELD_S),
               "negative": sum(1 for g in gaps if g < -0.35),
               "median_free": med([r["since_free"] for r in rc]),
               "holds": bool(gaps) and med(gaps) <= 1.0,
               "by_class": {k: (len(v), med(v)) for k, v in group(rc, "class", "since_ready").items()}}
    g46 = [r["since_ready"] for r in rc if r["type"] in (4, 6)]
    g5 = [r["since_ready"] for r in rc if r["type"] == 5]
    s["p6"] = {"n46": len(g46), "med46": med(g46), "n5": len(g5), "med5": med(g5),
               "holds": bool(g46) and bool(g5) and med(g46) - med(g5) >= 2.0}
    # P4
    rem = [r for r in ai if r["skill"] in COND_REMOVAL | HEX_REMOVAL]
    def carries(r):
        return bool(r.get("live6_target")) or bool(r.get("hexed_bit")) or bool(r.get("cond_bit"))
    s["p4"] = {"n": len(rem), "on_clean": sum(1 for r in rem if not carries(r)),
               "holds": bool(rem) and all(carries(r) for r in rem),
               "rows": [short(r) for r in rem][:40]}
    # P5
    off = [r for r in ai if r["type"] in (4, 5) and r["target_byte"] == 5 and r["form"] == "A0[60]"]
    with_att = [r for r in off if r.get("attack_target") is not None]
    match = [r for r in with_att if r["attack_target"] == r["target"]]
    s["p5"] = {"n": len(off), "with_attack_target": len(with_att), "match": len(match),
               "holds": bool(with_att) and len(match) == len(with_att),
               "miss_rows": [short(r) for r in with_att if r["attack_target"] != r["target"]][:40],
               "no_attack_target_on_observer": sum(1 for r in off if r.get("attack_target") is None
                                                   and r["target_klass"] == "OBSERVER"),
               "no_attack_target": len(off) - len(with_att)}
    # P8
    mh = [r for r in ai if r["class"] == "MONSTER" and r["type"] == 4]
    ok8 = [r for r in mh if r["target"] == r.get("attack_target") or r["target_klass"] == "OBSERVER"]
    s["p8"] = {"n": len(mh), "ok": len(ok8), "holds": bool(mh) and len(ok8) >= 0.9 * len(mh)}
    # POST-HOC, NOT PREDICTIONS (written after the first run, printed as such):
    # (a) P2 restricted to the skills whose heal IS the effect (Spell 5 / Signet 7): the
    #     registered P2 also caught enchantments (164 / 225) whose completion batch
    #     carries a heal word as a side effect;
    heals57 = [r for r in heals if r["type"] in (5, 7)]
    full57 = [r for r in heals57 if not hurt(r)]
    s["p2b"] = {"n": len(heals57), "full_by_both": len(full57),
                "full_rows": [short(r) for r in full57][:20]}
    # (b) the heal THRESHOLD per definition: the reconstructed health of the target at
    #     the announce of each heal (RECONSTRUCTION; L2 is the instrument's check)
    thr = collections.defaultdict(list)
    for r in heals57:
        if r.get("h_target") is not None:
            thr[(r["class"], r["def_key"], r["skill"], r["target_class"])].append(r["h_target"])
    s["heal_threshold"] = {k: (len(v), round(min(v), 3), med(v), round(max(v), 3))
                           for k, v in sorted(thr.items(), key=lambda kv: -len(kv[1]))}
    # (c) the ENGAGING population: casts by a definition that ever targets a non-self
    #     body in the corpus. A self-only definition (the Isle of the Nameless practice
    #     bodies that heal themselves under environmental Burning) is a different animal.
    engaging_defs = {r["def_key"] for r in ai if r["target"] not in (None, r["caster"])}
    for r in casts:
        r["population"] = ("engaging" if r["def_key"] in engaging_defs else "self-only") \
            if r["class"] in AI_CLASSES and not r.get("arena") else None
    eng = [r for r in rc if r["population"] == "engaging"]
    s["p3_engaging"] = {"n": len(eng), "median": med([r["since_ready"] for r in eng]),
                        "median_free": med([r["since_free"] for r in eng]),
                        "le_1": sum(1 for r in eng if r["since_ready"] <= 1.0),
                        "by_type": {TYPE_NAMES.get(k, k): (len(v), med(v)) for k, v in
                                    group(eng, "type", "since_ready").items()},
                        "free_by_type": {TYPE_NAMES.get(k, k): (len(v), med(v)) for k, v in
                                         group(eng, "type", "since_free").items()}}
    s["passed_over"] = {
        "all": (len(rc), sum(1 for r in rc if r.get("passed_over") == 0)),
        "engaging_by_type": {TYPE_NAMES.get(k, k): (len(v), sum(1 for x in v if x == 0), med(v))
                             for k, v in group(eng, "type", "passed_over").items()},
        "by_class": {k: (len(v), sum(1 for x in v if x == 0))
                     for k, v in group(rc, "class", "passed_over").items()}}
    # (d) P1's STRENGTH: the re-casts of an effect skill onto the same target whose slot
    #     came back while the previous episode was still certainly live (recharge <
    #     duration0) -- the only casts where the AI HAD the round-robin choice.
    inf = [r for r in ai if r.get("ready_inside_d0") and r.get("prev_same_target") == r["target"]]
    s["p1_strength"] = {"n": len(inf),
                        "rows": sorted((r["def_key"], r["skill"], r["recharge"], r["prev_completion_age"],
                                        r["age_minus_d15"], r["passed_over"]) for r in inf)}
    # (e) P5 for the casters with no attack word: the latest 0x002A follow target, and the
    #     previous offensive cast's target
    prev_off = {}
    p5b = collections.Counter()
    for r in sorted(off, key=lambda r: (r["capture"], r["port"], r["caster"], r["inc"], r["t"])):
        k = (r["capture"], r["port"], r["caster"], r["inc"])
        if r.get("attack_target") is None:
            p5b["n"] += 1
            if r.get("follow_target") is not None:
                p5b["with_follow"] += 1
                p5b["follow_match"] += r["follow_target"] == r["target"]
            if k in prev_off:
                p5b["with_prev_offensive"] += 1
                p5b["prev_offensive_match"] += prev_off[k] == r["target"]
        prev_off[k] = r["target"]
    s["p5b"] = dict(p5b)
    # (f) every effect type (stance and preparation too, outside P1's registration):
    #     re-casts onto a live same-skill episode, per (class, skill, type)
    alleff = [r for r in ai if r["type"] in EFFECT_TYPES and r.get("target") is not None]
    tally = collections.defaultdict(lambda: [0, 0, 0, []])
    for r in alleff:
        k = (r["class"], r["def_key"], r["skill"], r["type_name"])
        tally[k][0] += 1
        if r.get("same_live") in ("observed", "certain"):
            tally[k][1] += 1
            tally[k][3].append(r.get("same_age"))
        elif r.get("same_live") == "possible":
            tally[k][2] += 1
    s["same_live_all_types"] = {k: (v[0], v[1], v[2], v[3][:12]) for k, v in tally.items()}
    # (g) reaction latency: an effect re-cast onto a target whose same-skill episode
    #     was OBSERVED to end (0x0044 / a skill-specific [7]) before the announce
    lat = collections.defaultdict(list)
    for r in ai:
        if r.get("same_ended_ago") is not None and r["type"] in EFFECT_TYPES:
            lat[(r["class"], r["def_key"], r["skill"], r["type_name"])].append(r["same_ended_ago"])
    s["latency"] = {k: (len(v), round(min(v), 3), med(v), round(max(v), 3))
                    for k, v in sorted(lat.items(), key=lambda kv: -len(kv[1]))}
    s["pop"] = collections.Counter((r["class"], r["population"], r["map"]) for r in ai)
    s["specific_ids"] = c.get("specific_ids")
    s["shared_ids"] = c.get("shared_ids")
    # P7 / Q13
    per_def_skill = collections.defaultdict(lambda: {"n": 0, "caps": set(), "bodies": set()})
    for r in ai:
        k = (r["class"], r["def_key"], r["skill"])
        per_def_skill[k]["n"] += 1
        per_def_skill[k]["caps"].add(r["capture"])
        per_def_skill[k]["bodies"].add((r["capture"], r["port"], r["caster"], r["inc"]))
    at_bar = [k for k, v in per_def_skill.items() if v["n"] >= Q13_BAR and len(v["caps"]) >= 2]
    s["p7"] = {"at_bar": at_bar, "holds": not at_bar,
               "at_bar_engaging": [k for k in at_bar if k[1] in engaging_defs],
               "best": sorted(((v["n"], len(v["caps"]), len(v["bodies"]), k)
                               for k, v in per_def_skill.items()), reverse=True)[:10],
               "best_engaging": sorted(((v["n"], len(v["caps"]), len(v["bodies"]), k)
                                        for k, v in per_def_skill.items()
                                        if k[1] in engaging_defs), reverse=True)[:10]}
    return s


def group(rows, key, val):
    g = collections.defaultdict(list)
    for r in rows:
        if r.get(val) is not None:
            g[r[key]].append(r[val])
    return g


def short(r):
    return (f"{r['capture']}/{r['port']} t={r['t']:.2f} {r['class']} c{r['caster']} "
            f"def {r['def_key']} skill {r['skill']}({r['type_name']}) -> {r['target']} "
            f"[{r['target_klass']}] same={r.get('same_live')}@{r.get('same_age')} "
            f"h_t={r.get('h_target')} dmg10={r.get('dmg_on_target_10s')} att={r.get('attack_target')} "
            f"live6={r.get('live6_target')} hex={r.get('hexed_bit')} cond={r.get('cond_bit')}")


# ------------------------------------------------------------------ printing
def tables(c, s):
    L = []
    P = L.append
    casts = c["casts"]
    ai = pooled_ai(casts)
    P(f"castethogram -- live captures {c['captures']}, connections scored {c['connections']}, "
      f"refused {len(c['refused'])}, non-live directories excluded {len(c['excluded_origin'])}; "
      f"exe tables for builds {c['exe_builds']}")
    for e in c["excluded_origin"]:
        P(f"   excluded (origin): {e}")
    for e in c["refused"]:
        P(f"   refused: {e}")
    P("")
    P(f"ALL CASTS n={s['n_all']} ({s['n_all'] - s['n_arena']} off the Zaishen arenas, "
      f"{s['n_arena']} on them -- '@zaishen') by caster class: {dict(s['by_class'])}")
    P(f"   (HUMAN + OBSERVER are counted and never scored; AI = {AI_CLASSES} off the Zaishen "
      f"arenas: n={s['n_ai']})")
    bc = collections.Counter((class_label(r), r["form"]) for r in casts)
    for k in sorted(bc):
        P(f"   {k[0]:17s} {k[1]:7s} {bc[k]:5d}")
    ar = arena_ai(casts)
    arc = sorted({(r["capture"], r["port"], r["map"]) for r in casts if r.get("arena")})
    P(f"ZAISHEN ARENAS (own population, NEVER pooled into the tables below; scored by "
      f"zaishenrun.py): connections {len(arc)} {arc}; AI casts n={len(ar)} by class "
      f"{dict(collections.Counter(r['class'] for r in ar))}; on those connections every "
      f"class {dict(collections.Counter(r['class'] for r in casts if r.get('arena')))}")
    P("")
    P(f"L1 (locked after recon): 0x009F[60] target bytes {dict(s['l1_9f_bytes'])}; 0x00A0[60] "
      f"caster==target {s['l1_a0_self']} -> {'HOLDS' if s['l1'] else 'FAILS'}; a non-observer "
      f"0x009F[60] whose completion batch put an effect or a heal on the CASTER: "
      f"{s['l1_self_evidence'][0]} of {s['l1_self_evidence'][1]}")
    P(f"L2 (health instrument): deaths reading <= 0.10 just after the killing batch "
      f"{s['l2'][0]} of {s['l2'][1]} -> {'HOLDS' if s['l2_ok'] else 'FAILS: health columns UNVERIFIED'}; "
      f"the corpus's 34 setters ({len(s['set34_values'])}): {s['set34_values']}")
    P("")
    # per class x type
    P("AI CASTS by class x skill type (n)")
    ct = collections.Counter((r["class"], r["type_name"]) for r in ai)
    types = sorted({r["type_name"] for r in ai})
    P("   " + " " * 10 + "".join(f"{t:>9s}" for t in types))
    for k in AI_CLASSES:
        P(f"   {k:10s}" + "".join(f"{ct.get((k, t), 0):9d}" for t in types))
    P("")
    P("AI CASTS by (class, population, map)  -- population: 'engaging' = the definition casts at a "
      "non-self body somewhere in the corpus; 'self-only' never does")
    for k, n in sorted(s["pop"].items(), key=lambda kv: -kv[1]):
        P(f"   {str(k):40s} {n:5d}")
    P("")
    P(f"[6] visual ids: SKILL-SPECIFIC (one skill's completions add it) {s['specific_ids']}; "
      f"SHARED (a class of effect) {s['shared_ids']}")
    P("")
    P("AI CASTS by class x target class")
    tc = collections.Counter((r["class"], r["target_class"]) for r in ai)
    for k in AI_CLASSES:
        P(f"   {k:10s} " + ", ".join(f"{t}={n}" for (kk, t), n in sorted(tc.items(), key=str) if kk == k))
    P("")
    # per definition
    P(f"PER DEFINITION (build:definition; file, profession, level from 0x0056) -- monsterai 9 row-13 bar "
      f"{Q13_BAR} casts per type across sessions")
    pd = collections.defaultdict(list)
    for r in ai:
        pd[(r["class"], r["def_key"])].append(r)
    P(f"   {'class':9s} {'def':>12s} {'file/prof/lvl':>22s} {'pop':>9s} {'maps':>9s} {'n':>4s} "
      f"{'sess':>4s} {'bodies':>6s} {'short':>6s}  skills")
    for (k, dk), rs in sorted(pd.items(), key=lambda kv: -len(kv[1])):
        caps = {r["capture"] for r in rs}
        bodies = {(r["capture"], r["port"], r["caster"], r["inc"]) for r in rs}
        sk = collections.Counter(r["skill"] for r in rs)
        info = rs[0]["def_info"]
        maps = ",".join(str(m) for m in sorted({r["map"] for r in rs}))
        P(f"   {k:9s} {str(dk):>12s} {str(tuple(info) if info else None):>22s} "
          f"{rs[0]['population']:>9s} {maps:>9s} {len(rs):4d} "
          f"{len(caps):4d} {len(bodies):6d} {max(0, Q13_BAR - len(rs)):6d}  "
          + " ".join(f"{s_}x{n}" for s_, n in sk.most_common()))
    P("")
    P("PER SKILL (AI casters, pooled across definitions only within one build)")
    ps = collections.defaultdict(list)
    for r in ai:
        ps[(r["build"], r["skill"])].append(r)
    P(f"   {'build':>6s} {'skill':>5s} {'type':>8s} {'tb':>3s} {'n':>4s} {'defs':>4s} {'sess':>4s} "
      f"{'self':>4s} {'ally':>4s} {'foe':>4s} {'same-live':>9s} {'med gap-ready':>13s} "
      f"{'med free':>8s} {'med dist':>8s} {'short':>5s}")
    for (b, sk), rs in sorted(ps.items(), key=lambda kv: -len(kv[1])):
        tcc = collections.Counter((r["target_class"] or "").split("(")[0] for r in rs)
        sl = sum(1 for r in rs if r.get("same_live") in ("observed", "certain"))
        g = [r["since_ready"] for r in rs if r.get("since_ready_how") == "completion + recharge"]
        dists = [r["dist"] for r in rs if r.get("dist") is not None]
        P(f"   {b:>6} {sk:>5} {rs[0]['type_name']:>8s} {str(rs[0]['target_byte']):>3s} {len(rs):4d} "
          f"{len({r['def_key'] for r in rs}):4d} {len({r['capture'] for r in rs}):4d} "
          f"{tcc.get('self', 0):4d} {tcc.get('ally', 0):4d} {tcc.get('foe', 0):4d} {sl:9d} "
          f"{str(med(g)) + ' n=' + str(len(g)):>13s} "
          f"{str(med([r['since_free'] for r in rs if r.get('since_ready_how') == 'completion + recharge'])):>8s} "
          f"{str(med(dists)):>8s} {max(0, Q13_BAR - len(rs)):5d}")
    P("")
    P("PREDICTIONS (registered in the docstring before the first run)")
    p = s["p1"]
    P(f"P1 hex/enchantment re-cast onto a live episode of the same skill: n={p['n']} AI hex/ench "
      f"casts; overlapping (observed or certain) {p['overlap_observed_or_certain']}, of which "
      f"same-instant doubles {p['doubles']} and COUNTEREXAMPLES {p['counterexamples']}; "
      f"duration15-only 'possible' {p['possible_only']} -> {'HOLDS' if p['holds'] else 'FAILS'}")
    P(f"   by (class, same_live): {dict(p['by_class'])}")
    for x in p["cx_rows"]:
        P(f"   cx: {x}")
    p = s["p2"]
    P(f"P2 AI heal on a full-health ally: n={p['n']} heals landing on their target; full by both "
      f"tests {p['full_by_both']} -> {'HOLDS' if p['holds'] else 'FAILS'}; heals with no damage "
      f"on T in the 10 s before: {p['damage_half_only_full']}; by (class, target) {dict(p['by_class'])}")
    for x in p["full_rows"]:
        P(f"   full: {x}")
    p = s["p3"]
    P(f"P3 re-cast at the first opportunity: n={p['n']} re-casts after a completed cast; median "
      f"gap from ready {p['median']} s (<= 1.0 s: {p['p_le_1']}, > {HELD_S} s held: {p['p_gt_held']}, "
      f"< -0.35 s i.e. before the table says ready: {p['negative']}); median net of the caster's "
      f"own busy time {p['median_free']} s -> {'HOLDS' if p['holds'] else 'FAILS'}; by class "
      f"{p['by_class']}")
    p = s["p6"]
    P(f"P6 hex/enchantment slots held longer than type-5 spells: med {p['med46']} (n={p['n46']}) vs "
      f"{p['med5']} (n={p['n5']}) -> {'HOLDS' if p['holds'] else 'FAILS'}")
    p = s["p4"]
    P(f"P4 removal skills only on a carrying target: n={p['n']}; on a clean target {p['on_clean']} -> "
      f"{'HOLDS' if p['holds'] else ('UNTESTED (n=0)' if not p['n'] else 'FAILS')}")
    for x in p["rows"]:
        P(f"   rm: {x}")
    p = s["p5"]
    P(f"P5 offensive spell on the caster's current attack target: n={p['n']}; with an attack target "
      f"{p['with_attack_target']}; match {p['match']} -> {'HOLDS' if p['holds'] else 'FAILS'}; "
      f"no attack target {p['no_attack_target']} ({p['no_attack_target_on_observer']} of them on the observer)")
    for x in p["miss_rows"]:
        P(f"   miss: {x}")
    p = s["p8"]
    P(f"P8 monster hexes on its attack target or the observer: {p['ok']} of {p['n']} -> "
      f"{'HOLDS' if p['holds'] else 'FAILS'}")
    p = s["p7"]
    P(f"P7 monsterai 9 row-13 bar unmet (no AI (definition, skill) with >= {Q13_BAR} casts over >= 2 sessions): "
      f"{'HOLDS' if p['holds'] else 'FAILS'}; at the bar {p['at_bar']}")
    P("   best (n, sessions, bodies, (class, def, skill)):")
    for b in p["best"]:
        P(f"      {b}")
    P(f"   ENGAGING definitions only -- at the bar {p['at_bar_engaging']}; best:")
    for b in p["best_engaging"]:
        P(f"      {b}")
    P("")
    P("POST-HOC (written after the first run; NOT predictions)")
    p = s["p2b"]
    P(f"P2 restricted to heal-IS-the-effect types (Spell 5, Signet 7): n={p['n']}; full by both "
      f"tests {p['full_by_both']}")
    for x in p["full_rows"]:
        P(f"   full: {x}")
    P("heal threshold: the target's reconstructed health at each heal's announce, per "
      "(class, def, skill, target): (n, min, median, max)")
    for k, v in s["heal_threshold"].items():
        P(f"   {str(k):52s} {v}")
    p = s["p3_engaging"]
    P(f"P3 over ENGAGING definitions only: n={p['n']}; median gap from ready {p['median']} s "
      f"(<= 1.0 s: {p['le_1']}); median net of own busy time {p['median_free']} s")
    P(f"   gap from ready by type {p['by_type']}")
    P(f"   net of busy by type    {p['free_by_type']}  (for a never-idle caster this is its "
      f"idle time since its last cast of ANYTHING, not a slot property)")
    p = s["passed_over"]
    P(f"passed over: re-casts where the caster cast NOTHING else between the slot's ready time and "
      f"the re-cast -- all {p['all'][1]} of {p['all'][0]}; by class (n, zero) {p['by_class']}")
    P(f"   engaging, by type (n, zero, median other casts) {p['engaging_by_type']}")
    p = s["p1_strength"]
    P(f"P1's strength: re-casts onto the SAME target where the slot was ready while the previous "
      f"episode was certainly live (recharge < duration0): n={p['n']}")
    P("   (def, skill, recharge, age since previous completion, age - duration15, other casts passed over)")
    for x in p["rows"]:
        P(f"   {x}")
    P(f"P5 for offensive casts with no attack word: {s['p5b']}")
    P("reaction latency: effect re-casts onto a target whose same-skill episode was OBSERVED to "
      "end before the announce, seconds since that end: (class, def, skill, type): (n, min, median, max)")
    for k, v in s["latency"].items():
        P(f"   {str(k):48s} {v}")
    P("same-skill live episode at the announce, EVERY effect type (stance / prep outside P1): "
      "(class, def, skill, type): (n, observed-or-certain, possible-only, ages)")
    for k, v in sorted(s["same_live_all_types"].items(), key=lambda kv: -kv[1][0]):
        P(f"   {str(k):48s} {v}")
    return "\n".join(L)


def rows_text(c):
    out = []
    for r in c["casts"]:
        if r["class"] not in AI_CLASSES or r.get("arena"):
            continue
        out.append(f"{r['capture']}/{r['port']} t={r['t']:9.3f} {r['class']:8s} c{r['caster']:<4} "
                   f"i{r['inc']} def {str(r['def_key']):>11s} {r['form']:7s} sk {r['skill']:4d} "
                   f"{r['type_name']:7s} -> {str(r['target']):>4s} {str(r['target_class']):5s} "
                   f"end {r['end_prop']} h_t {r.get('h_target')} h_c {r.get('h_caster')} "
                   f"same {r.get('same_live')}@{r.get('same_age')} live6 {r.get('live6_target')} "
                   f"d {r.get('dist')} {r.get('dist_how', '')} prev {r.get('since_prev_cast')} "
                   f"ready {r.get('since_ready')} free {r.get('since_free')} att {r.get('attack_target')} "
                   f"heal {r.get('heal_on_target')}")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rows", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-save", action="store_true")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass
    c = census()
    ai = pooled_ai(c["casts"])
    if not ai:
        print(f"castethogram: REFUSED -- no AI cast observed over {c['connections']} live "
              f"connections ({len(c['casts'])} casts of any class). Nothing to report.")
        return 2
    s = score(c)
    text = tables(c, s)
    if args.json:
        print(json.dumps({"casts": c["casts"]}, default=str))
    else:
        print(text)
        if args.rows:
            print(rows_text(c))
    if not args.no_save:
        out_dir = vaultpath.vault_path(*OUT_DIR_PARTS)
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, "castethogram-events.json"), "w", encoding="utf-8") as fh:
            json.dump({"produced_by": "studies/monsterai/review/castethogram.py", "origin": "live",
                       "captures": c["captures"], "connections": c["connections"],
                       "refused": c["refused"], "casts": c["casts"]}, fh, default=str, indent=0)
        with open(os.path.join(out_dir, "castethogram-tables.txt"), "w", encoding="utf-8") as fh:
            fh.write(text + "\n\n" + rows_text(c) + "\n")
        if not args.json:
            print(f"\nwrote {out_dir}\\castethogram-events.json and castethogram-tables.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
