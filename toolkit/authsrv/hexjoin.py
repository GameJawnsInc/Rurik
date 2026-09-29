r"""Hexes on retail's wire: Incendiary Bonds 179, Mind Burn 185, how ANY hex lands, and the conditions.

    python toolkit/authsrv/hexjoin.py              # every live capture: the predictions, PASS/FAIL per line
    python toolkit/authsrv/hexjoin.py --rows       # plus one block per 179 / 185 cast (batches in wire order)
    python toolkit/authsrv/hexjoin.py --json
    python toolkit/authsrv/hexjoin.py --stamp 20260817T231139   # one capture

WHY THIS EXISTS. DESKWORK-D6 step 3 (studies/deskwork/PLAN.md): the plan's text read
Incendiary Bonds as "a hex plus area damage" and Mind Burn's energy clause as one
comparison against the target. Before a server line was written the tape lane
(2026-09-27) re-derived both from the bytes, and both readings were CORRECTED: 179's
damage is the hex's END effect (+3 s, the target's death, never a removal), and Mind
Burn's second packet is decided PER FOE. This is the committed port of that lane's
scratch join (`d6U-tape-join.py`), and `test_skilldamage.py` section 12c locks what it
prints. studies/skills/FINDINGS.md 61 carries the reading.

METHOD. Captures come from `livewire.live_captures()` -- origin LIVE only (origin.py's
refuse-to-mix rule at the loader), behind `vaultpath.require_dir` so a missing vault
raises instead of scanning nothing. Each game connection is decoded by
`deepwoundjoin.sequence`, which REFUSES a connection that does not frame whole
(refusals are counted and printed). The observer is `spellhitjoin.observer_of`
(property 41 cross-checked against the answered c2s presses), computed on every
connection that carries an 0x0042 or an announce of a skill this reader follows -- the
c2s decode is most of the cost.

WIRE SHAPES (decoded values carry the header at v[0]):
  0x0042 [66, target, skill, field3, buff, f32]   an effect apply (NO source field)
  0x0044 [68, target, buff]                       its removal
  0x00A0 [160, prop, a, b, value]   prop 60 announce [60, caster, target, skill];
                                    prop 20 [20, target, caster, visual]
  0x009F [159, prop, agent, value]  prop 58 finished; prop 59 stopped; prop 10 skill damage
                                    naming the skill; prop 6 / 7 GV_ADD_EFFECT / GV_REMOVE_EFFECT
                                    [6, agent, id] -- how the client draws an effect on ANY body
  0x00A3 [163, prop, target, cause, f32]   16 / 17 damage (a negative fraction)
  0x00F1 [241, agent, status word]         bit 0x10 dead, 0x800 hexed, 0x400 (snared,
                                           RECONSTRUCTION), 0x02 a condition
  0x0027 [39, agent, speed]                the declared movement speed (a float)
  0x0020 create: v[1] agent, v[4] kind, v[12] allegiance token
  0x001E the world simulation tick -- skipped when reading batch order

THE COMPLETION. The first `[58, caster, 0]` at least max(0.3 s, half the activation)
after the announce whose caster's latest announce is this one (a 58 closer belongs to a
previous skill sharing the announce's batch -- aotjoin's lesson); a 59 / 45 / 35 there is
a STOPPED cast, and an announce superseded by a newer one before any end is
"superseded".

THE PREDICTIONS, exactly as the tape lane REGISTERED them on 2026-09-27 before its
first run (the priors: spellhitjoin 43.3-43.5's 39 Mind Burn twins and 179's payoff at
hex end, bufflog's "179 -> (13, 3.0)", the skills-FINDINGS status-word table). Three
of them FAILED as registered -- I4, M2, C2 -- and this reader prints each one FAILED
with the corrected reading (I4c, M2c, C2c) beside it. They are not rewritten: a
prediction that is edited to fit the tape after the run is a prediction nothing could
have refuted. Two things beside them are NOT the lane's registrations and say so: the
per-port announce counts EXPECT_179_PER_PORT / EXPECT_185_PER_PORT are the lane's
FIRST-RUN OUTPUT (registered after it, printed as such), and M4's second clause is
UNTESTABLE on this corpus (below).

 179 Incendiary Bonds (record: type 4, target 5, act 1.0, dur 3/3, scale 20..80, bonus 1..3, aoe 240)
  I1  every announce is 0x00A0 [60, caster, target, 179]; completion [58, caster, 0] at +1.0 +- 0.05 s.
      (The per-port counts the reader also holds it to -- 19 / 4 / 4 / 3 on the witness tape --
      were registered AFTER the first run, from its output; a floor on the corpus, exact per tape.)
  I2  the completion batch carries a [20, target, caster, 348] and NO damage word from the
      caster onto the target.
  I3  when the target is the observer, the completion batch carries 0x0042 [obs, 179, rank, buff, 3.0]
      -- the f32 IS the duration -- and a 0x00F1 with bit 0x800 set.
  I4  THE TRIGGER is at completion + 3.00 +- 0.05 s on EVERY cast whose target lived (no early
      trigger in the corpus); it carries the caster's damage words onto the target and 0..3 more
      foes, no 58 and no [20]; when the target is the observer the 0x0044 of the hex's buff lands
      in the same batch.
      FAILED AS REGISTERED. The timing half holds (20 scheduled ends at +2.986..+3.022). The
      "every cast whose target lived" half fails three ways: 4 hexes REMOVED by the target's own
      Remove Hex (301) fired NOTHING; 3 ended EARLY on the target's death, 2 of them striking an
      adjacent foe; 1 ended early in the batch where the CASTER died (n = 1, not in the wiki).
      I4c the corrected reading: a hex's end is scheduled (+3.0 +- 0.05) or early; an early end by
      a removal carries no payoff; an early end on the target's death carries the payoff on the
      foes still standing; and no payoff batch carries a 58 of 179 (a 58 / [20] of the caster's
      OTHER skill completing in the same instant is a mixed batch, aotjoin's word; two of them).
      WIKI (GWW "Incendiary Bonds" rev 2733032) names the target's death and the removal.
      A word in the end batch whose (caster, value) ALREADY landed on that foe in the completion
      batch is the caster's periodic TICK (Fire Storm's, repeating one value a second), not the
      payoff's -- 690.819's only "payoff" word is one (the D6 review's EV-6); such an end is
      counted as mixed (`i_payoff_tick`), never as a payoff.
  I5  every trigger word's taker is a foe of the caster (allegiance token), 1..4 takers.
  I6  a Burning 0x0042 [obs, 480, n, buff, n.0] lands on the observer whenever the observer takes
      a trigger word, duration 3.0, removed by 0x0044 at + duration.

 185 Mind Burn (record: type 5, target 5, act 1.0, scale 15..60, bonus 1..10, aoe 156)
  M1  every announce 0x00A0 [60, c, t, 185]; [58, c, 0] at +1.0 +- 0.05.
      (The per-port counts -- 17 / 4 / 3 / 3 on the witness tape -- registered after the first
      run, as I1's.)
  M2  the completion batch carries [20, target, caster, 331] and one or two IDENTICAL 16 words onto
      the target (two = the energy clause, P4's twin); on a twin cast the adjacent foes ALSO take a
      word -- a non-twin cast strikes the target alone.
      FAILED AS REGISTERED. In 4 of 25 casts the foes of ONE cast mix twins and singles, and at
      54071 647.300 the TARGET got one word while the adjacent foe 14 got two.
      M2c the corrected reading: the second word and its Burning are decided PER FOE -- a foe with
      two words carries a new [6, foe, 25] or was already burning; a single-word foe carries no
      Burning signal (one exception, 780.235, printed). CONTESTED against the wiki's wording
      ("if you have more Energy than target foe"), n = 1 decisive cast; the wiki's own anomaly
      note ("checks the energy condition independently for each target hit") agrees.
  M3  Burning 0x0042 on the target when it is the observer, duration an integer in 1..10.
      UNTESTABLE AS REGISTERED: no Mind Burn was ever cast ONTO the observer. The observer was
      struck as an ADJACENT foe (twice), with twins: 0x0042 [obs, 480, 9, buff, 9.0] -- printed as
      M3c, the same claim on the foe the tape does hold.
  M4  DECIDABILITY: the caster's energy is never on the wire (casters are not the observer); on a
      cast onto the observer the observer's energy IS, so a twin gives only "caster energy > the
      observer's energy then" -- the comparison is undecidable from the tape, only bounded.
      The first clause holds (scored). The second is UNTESTABLE AS REGISTERED: no Mind Burn was
      cast onto the observer (M3's own null), and the observer's CURRENT energy is never on the
      wire either -- its maximum (prop 41), its regen (43) and its spends (62) are, a current
      value is not -- so the "bound" the clause promised cannot be taken from any tape here.
      Printed so beside M4 (the D6 review's EV-5); an earlier port dropped the clause.

 generic hex apply (every type-4 skill announced anywhere in the live corpus)
  G1  the 0x0042 is visible ONLY on the observer (or a hero): 0 hex applies on any other agent.
  G2  on the observer, a hex's 0x0042 is in the caster's completion batch, and in wire order the 58
      comes FIRST, then the 0x0042, then the 0x00F1.
  G3  f32 == interp(duration0, duration15, field3) on every hex apply (bufflog's rule).
  G4  the removal is 0x0044 [obs, buff] at apply + f32 within 0.05 s unless stripped.

 conditions
  C1  >= 1 apply of Dazed 485 and >= 2 of Cracked Armor 2077 in the LIVE corpus, all on
      Pre-Searing (Isle) connections, none inside a cast's 58 batch (environmental).
      The Isle clause is UNSCORED: this reader does not read the map id; the applies are on
      20260821T152147 / 20260821T155022, the Isle captures by their stamps (skills 61.3), and
      that is a reading of the vault's filing, not of the bytes (the D6 review's EV-5).
  C2  Burning (480) and Bleeding (478) applies: field3 == the f32 (integer seconds) on every one,
      removal at + f32.
      FAILED AS REGISTERED: field3 equals the duration only on CAST-applied conditions (Burning
      from 179 / 185, 5 of 5); the environmental ones -- the Isle's Bleeding, Poison, Dazed,
      Cracked Armor -- carry field3 0.
      C2c the corrected reading: a condition a SKILL applied (a [10, target, skill] in its
      batch -- 179's payoff has no 58 -- or a 58 whose caster's announce named this target)
      carries field3 == its f32; an environmental one (neither) carries field3 0.

REGISTERED AFTER THE LANE'S FIRST RUN, from what that run showed, and locked on its second
(`--part2` there); NOT predictions, and said so:
  L1  a hex landing on ANY body is `[6, T, 1]` + `[6, T, class]` in the completion batch and
      `[7, T, ..]` at the end: 179 [1, 12] on every cast, Teinai's Prison 1097 [1, 12] (the `1`
      withheld once, 651.779, when the target already carried Empathy's live 1), Empathy 26
      [1, 4] on every cast; Lightning
      Strike 222 (type 4 in the table; hexes only when Overcast, WIKI rev 2738740) lands NO [6].
  L2  when one batch strikes several foes the words go out in ASCENDING agent id (the target
      first only when it has the lowest id).
  L3  Teinai's Prison 1097 (the -66 % snare hex) carries 0x0027 [T, 288 x 0.34 = 97.92] in its
      apply batch and 0x0027 [T, 288.0] in its end batch, and 0x00F1 bit 0x400 set with it and
      cleared at its end.
  L4  the [6] effect ids on the observer beside a condition's 0x0042: Burning 25, Dazed 28,
      Cracked Armor 29.

THE ZAISHEN CAPTURE (2026-09-28, CASTAI-Z1, 20260928T103123 -- after the registration; the
predictions above are NOT re-worded; every tape is scored on its OWN build's table, read
from the vault's pristine image of that build -- `build_table`, since 2026-09-28). Its casts
break six registered predictions and one
corrected reading. Each is scored AS REGISTERED on the corpus as it stood before that stamp
(the test cuts the census there, where the reading holds exactly as on the day it was
registered), AS REGISTERED on the whole corpus (FAILED, printed so), and -- where a
re-statement with no free parameter exists -- RE-STATED on the whole corpus (`RESTATED`):
  I1 / M1  the Zaishen Mage (agent 9) casts 179 and 185 behind a `0x00A3 [61 GV_CASTTIME,
           caster, target, 0.67]` word and completes them at +0.651..+0.693 (commit 974f8748's
           word). I1r / M1r: the completion at the [61] seconds when sent, else the activation,
           +- COMPLETION_TOL.
  I2       on :50295 457.840 the caster's 179 completion batch carries one word from the caster
           onto the target: its own Fire Storm's k = 2 tick (all three foes take the same value;
           the 197 completed at 456.823 -- aotjoin's mixed instant). I2r: no damage word from the
           caster onto the target except one riding a tick of the caster's own Fire Storm
           (completion + k s, k = 1..10, within aotjoin's TICK_TOL).
  I3 / G2  a hex landing on an observer ALREADY hexed carries no 0x00F1 (the status word does
           not change): agent 3's 179 onto the observer at 194.673 (field3 0 -- the caster's own
           Fire Magic), and four G2 applies (44, 179, 31, 36). I3r / G2r: the 58 ahead of the
           0x0042 on every apply, and an 0x00F1 with the hex bit after it UNLESS the target's
           last status word before the batch already carried the hex bit.
  G3       agent 4's 135 lands on the observer twice (:50061 164.735, 187.725) at field3 11 with
           f32 14.0, where interp(3, 16, 11) = 12.533 -- the first hex in the corpus whose
           duration is NOT constant across ranks (every earlier G3 row, 179's 3 / 3, could not
           fail). No re-statement: FAILED, its witness exact; the cause is UNMEASURED.
           RE-STATED 2026-09-28 (the regenerate-from-38888 arc), in two parts of UNEQUAL
           standing, neither fitted: (a) MEASURED -- the row was the wrong BUILD's: this
           reader took every tape's rows from the vault's one bulk table (38797), and the
           Zaishen tape is build 38888 (its VERSION frame), where 135 is 4..18 (CASTAI-ZF7's
           re-balance; 3..16 on 38797 / 38833 / 38849, each read from its pristine image);
           every tape is now scored on its own build's table (`build_table`); and (b)
           INTEGERIZATION, CORROBORATED by ONE witness (two applies, one rank, one tape): G3
           as registered is UNROUNDED, interp(4, 18, 11) = 14.267, and the wire carries 14.0
           -- the duration sent is an INTEGER. WHICH integer rule is UNDISCRIMINATED: 14.267
           goes to 14 under round-half-up, floor and truncation alike, so this tape cannot
           tell them apart, and `effects.interp`'s half-up (the scaler at 0x005A8920 as that
           docstring states it, its tie-break never settled) is the rule G3r uses, not a
           rule this witness measured.
           G3 AS REGISTERED still FAILS on this tape (14.267 != 14.0, printed so).
           G3r: f32 == effects.interp(duration0, duration15, field3) on the tape's own
           build's row, on every hex apply. Each part is needed: on the 38797 row (the
           known-bad arm, `with_table`) G3r predicts 13 and FAILS too (12 under floor; either
           way not the wire's 14).
  C2c      one skill-applied condition carries field3 0 (Crippled 15 s under a [10, obs, 334]
           at :50061 219.517), and three conditions this reader calls environmental carry field3
           == f32 -- a Deep Wound in the batch where the observer's hex 44 ends (203.938) and two
           Poisons riding an attack's 0x00A7 + [20, obs, 6, 743] (:58544 611.458, 620.553): the
           classifier sees neither a hex's END nor an attack's landing. No re-statement: FAILED.

THE SECOND ZAISHEN CAPTURE (2026-09-29, CASTAI-Z2, 20260929T100038 -- the Smiting Monks; the
predictions above are NOT re-worded). Scourge Healing 251, a 30 s hex, lands on the observer
seven times, and its 0x0044 comes early on three of them for a reason the registration never
saw and on one for a reason the READER got wrong:
  G4       "the removal at apply + f32 within 0.05 s unless stripped" -- the reader's `stripped`
           was the target's DEATH in the removal's batch. On this tape the ARENA ROUND'S END
           strips it: :51090's 251 at 442.802 is removed at +12.250 in the batch that carries
           0x0181 (the mission clock set directly -- studies/newopcodes, 0x0180's family --
           beside 0x0180 re-armed and 0x01AF), the observer's other effects, the Fighter's and
           the monks' [7]s all in the same instant, no death bit on anybody: the round is over
           and every body is wiped. Z1's three rounds ended the same way (0x0181 at :50061
           229.495, :50295 523.439, :58544 626.139) with no hex live on the observer, so G4
           could not see it there. G4r: the removal at apply + f32 within REMOVAL_TOL unless
           the batch it sits in carries the target's death bit OR 0x0181 (`round_end`).
           G4 AS REGISTERED FAILS on this tape (printed so); G4r holds on the whole corpus.
           And the reader: `removal` took the first 0x0044 [target, buff] at or after the
           apply's TIME, and at :64557 667.396 a 0x0044 [7, 61] sits in the SAME batch AHEAD
           of the 0x0042 that hands buff 61 out again (the id is reused the instant it is
           freed) -- the reader read the old instance's end as the new one's, residual -30.0.
           `removal` now takes the first 0x0044 AFTER the apply in WIRE ORDER
           (`REMOVAL_BY_ORDER`, the module flag; False is the known-bad arm, and
           test_skilldamage 12c shows it reproduce the -30.0). On the corpus before the
           tape the change moves exactly ONE number, and it is not one any prediction
           reads: the Isle tape's Burning on the observer at 20260821T152147 :63150
           741.941 (C2's residual column), re-applied in the batch where its previous
           instance ends under the same buff id 125 -- the reader's "-3.0" was that
           earlier instance's 0x0044, its "+6.021" now the id's next end at +9.021.
           Every hex apply's residual at the pin is byte-identical (asserted).
The DAMAGE the monks deal is spellhitjoin's business (its docstring: Zealot's Fire's payoff
riding the batch of the skill that triggered it, and the holy words on property 55).
`m_rank_fits` ("the caster's 13 predicts both Burnings") is scored on the WITNESS's hex applies
-- its own claim's scope (EV-3); the corpus's ranks are printed (`m_ranks_corpus`).
A connection the capture's OWN manifest declares gapped (`livewire.declared_gaps`) is set
aside BY NAME, printed, and decoded once to show it still refuses (`set_aside`); `refused`
counts every OTHER connection that does not frame whole.

Corpus totals are FLOORS (a later capture is confirming evidence); the witness tape's own
counts (20260817T231139: 30 announces of 179, 27 of 185) are exact, per tape. score() keeps
the two apart: every exact number (completions, ends, takers, twins, the [6] ids, the order
census) is computed on the WITNESS capture alone, the invariants (every hex 0x0042 on the
observer, every G3 residual, every cast-applied condition's field3) and the floors on the
whole corpus -- so a later capture holding the same casts again reddens nothing
(test_skilldamage 12c appends one and checks; the D6 review's EV-3 found the first port
pinning corpus totals as per-tape exacts).

Standard library only; reads the vault through `vaultpath`, and each tape's own build's skill
table out of the vault's pristine image of that build (`clientscan/pinned.py` + `skilltable.py`).
"""
import argparse
import bisect
import collections
import json
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
PARENT = os.path.dirname(HERE)
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)
CLIENTSCAN = os.path.join(PARENT, "clientscan")      # pinned / skilltable: the per-build table
if CLIENTSCAN not in sys.path:
    sys.path.insert(0, CLIENTSCAN)

import bufflog          # noqa: E402
import deepwoundjoin    # noqa: E402  (sequence: refuses a connection that does not frame whole)
import effects          # noqa: E402  (interp: the client's own ROUNDED scaler, G3r)
import livewire         # noqa: E402  (live_captures: origin LIVE only)
import spellhitjoin     # noqa: E402  (observer_of / c2s_of)
import tape             # noqa: E402
import vaultpath        # noqa: E402

OP_CREATE = 0x0020
OP_SIM_TICK = 0x001E
OP_SPEED = 0x0027
OP_EFFECT_APPLY = 0x0042
OP_EFFECT_REMOVE = 0x0044
OP_INT = 0x009F
OP_FLOAT = 0x00A2
OP_INT_TARGET = 0x00A0
OP_POINT_EFFECT = 0x00A1
OP_FLOAT_TARGET = 0x00A3
OP_ADRENALINE = 0x00CF
OP_STATUS = 0x00F1
OP_ROUND_END = 0x0181       # the mission clock set directly (studies/newopcodes, 0x0180's family):
                            # on both Zaishen tapes the batch that closes an arena round and
                            # strips every effect on every body -- G4r's second strip
REMOVAL_BY_ORDER = True     # `Conn.removal`: the first 0x0044 AFTER the apply in wire order;
                            # False = by time (the reader before 2026-09-29, the known-bad arm)
OWN_OPS = (0x00E2, 0x00E3, 0x00E4, 0x00E5)
PROP_ADD_EFFECT = 6
PROP_REMOVE_EFFECT = 7
PROP_SKILL_DAMAGE = 10
PROP_EFFECT_ON_TARGET = 20
PROP_DAMAGE = (16, 17)
PROP_HEALTH_GAIN = 55
PROP_FINISHED = 58
PROP_ANNOUNCE = 60
PROP_CAST_TIME = 61          # agents.GV_CASTTIME: a modified cast's seconds, ahead of its [60]
ANNOUNCE_PROPS = (60, 50, 48)
END_PROPS = (58, 59, 45, 35)
DEAD_BIT = 0x10
HEX_BIT = 0x800
SNARE_BIT = 0x400
TYPE_HEX = 4

INCENDIARY, MIND_BURN = 179, 185
FIRE_STORM = 197            # I2r: a word riding the caster's own Fire Storm tick
TICK_TOL = 0.05             # s; aotjoin.TICK_TOL, the tick gate
TEINAIS_PRISON, EMPATHY, LIGHTNING_STRIKE = 1097, 26, 222
REMOVE_HEX = 301            # the target's own 58 in a hex's end batch (WIKI: Remove Hex)
BURNING, BLEEDING, DAZED, CRACKED_ARMOR = 480, 478, 485, 2077
CONDS = {478: "Bleeding", 479: "Blind", 480: "Burning", 481: "Crippled", 482: "Deep Wound",
         483: "Disease", 484: "Poison", 485: "Dazed", 486: "Weakness", 2077: "Cracked Armor"}
BURNING_EFFECT_ID, DAZED_EFFECT_ID, CRACKED_EFFECT_ID = 25, 28, 29     # L4

BATCH = 0.05                # s; one batch's shoulder
COMPLETION_TOL = 0.05       # s; I1 / M1
PAYOFF_AT = 3.0             # s; 179's record duration (3 / 3)
PAYOFF_TOL = 0.05           # s; I4
END_WINDOW = 40.0           # s after the completion a hex's [7] is looked for
REMOVAL_TOL = 0.05          # s; G4 / I6
SNARE_BASE = 288.0          # u/s; the declared base every 0x0027 restores (slice 48)
SNARE_FACTOR = 0.34         # 1 - 0.66; L3

EXPECT_CAPTURE = "20260817T231139"
# the captures the post-hoc L1 facts were read on (179 / Teinai's Prison + Empathy /
# Lightning Strike x2): their [6] counts are exact PER TAPE; any other stamp is a floor
L1_WITNESSES = (EXPECT_CAPTURE, "20260913T210901", "20260914T005758", "20260916T150306")
EXPECT_179_PER_PORT = {"54071": 19, "50527": 4, "50513": 4, "50286": 3}
EXPECT_185_PER_PORT = {"54071": 17, "50527": 4, "50513": 3, "50286": 3}


def _f32(bits):
    return struct.unpack("<f", struct.pack("<I", int(bits) & 0xFFFFFFFF))[0]


def interp(lo, hi, rank):
    return lo + (hi - lo) * rank / 15.0


def _int(x, default=0):
    try:
        return int(x) if x is not None else default
    except (TypeError, ValueError):
        return default


_BUILD_TABLES = {}          # build -> (rows, types) | LookupError


def build_table(build):
    """(rows, types) of `build`: {skill_id: row} over that build's player corpus, read out
    of the vault's PRISTINE image of that build (`pinned.find(build=...)`, verified) with
    `skilltable.parse_record` -- the rows `skilltable.py --emit-content` writes for that
    build (equip_family 1, PvP-only excluded) -- and {skill_id: type_code}.

    WHY PER BUILD (2026-09-28, the regenerate-from-38888 arc). This reader used to take
    every tape's rows from `agents.WORLD` -- the vault's ONE bulk table, whichever build it
    was generated from -- so a prediction for a tape recorded on build B was scored against
    another build's row, and the verdict moved when the vault did: Faintheartedness 135 is
    3..16 on 38797 / 38833 / 38849 and 4..18 on 38888 (the re-balance, CASTAI-ZF7), and the
    Zaishen tape (build 38888) lands it at field3 11. A tape is now scored against ITS OWN
    build's table (the client's VERSION frame names the build, `tape.client_version`), as
    rechargeprobe.table_for and test_effects section 2 already do, so the result depends
    on the tapes and the pinned images and on nothing the vault's content overlay says.
    Raises LookupError (cached) when the vault holds no pristine image of `build`: a
    connection is never scored against another build's table."""
    got = _BUILD_TABLES.get(build)
    if isinstance(got, LookupError):
        raise got
    if got is not None:
        return got
    import pinned           # noqa: E402  (clientscan, stdlib-only)
    import skilltable       # noqa: E402
    try:
        exe, _why = pinned.find(build=build)
    except SystemExit as exc:
        err = LookupError(f"no pristine image of build {build} in the vault: {str(exc)[:80]}")
        _BUILD_TABLES[build] = err
        raise err from None
    with open(exe, "rb") as fh:
        data = fh.read()
    if skilltable.build_of(data) != build:
        err = LookupError(f"{exe} is not the pristine image of build {build}")
        _BUILD_TABLES[build] = err
        raise err
    base, count, _score = skilltable.locate_table(data)
    every = [skilltable.parse_record(data, base, i) for i in range(count)]
    rows = {i: every[i] for i in skilltable.player_corpus(every)}
    types = {k: _int(r.get("type_code"), -1) for k, r in rows.items()}
    _BUILD_TABLES[build] = (rows, types)
    return rows, types


def with_table(c, build):
    """THE KNOWN-BAD ARM: the census `c` with EVERY connection scored against `build`'s
    table instead of its own -- what this reader did before 2026-09-28 when the vault's
    bulk table was `build`. Nothing is re-decoded; each Conn is a shallow copy."""
    import copy
    rows, types = build_table(build)
    conns = []
    for cc in c["conns"]:
        d = copy.copy(cc)
        d.table, d.types, d.table_build = rows, types, build
        conns.append(d)
    return dict(c, conns=conns)


def _fmt(op, v):
    if op == OP_FLOAT_TARGET and len(v) > 4:
        return f"0x{op:04X} {[v[1], v[2], v[3], round(_f32(v[4]), 5)]}"
    if op == OP_EFFECT_APPLY and len(v) > 5:
        return f"0x0042 [tgt {v[1]}, skill {v[2]}, f3 {v[3]}, buff {v[4]}, {round(_f32(v[5]), 3)}]"
    if op == OP_STATUS and len(v) > 2:
        return f"0x00F1 [{v[1]}, 0x{int(v[2]):X}]"
    if op == OP_SPEED and len(v) > 2:
        try:
            return f"0x0027 [{v[1]}, {float(v[2]):.2f}]"
        except (TypeError, ValueError):
            pass
    s = repr(list(v[1:]))
    return f"0x{op:04X} {s if len(s) < 90 else s[:87] + '...'}"


class Conn:
    """One decoded game connection, indexed for the joins below."""

    def __init__(self, stamp, port, seq, observer, build, table, types):
        self.stamp, self.port, self.seq, self.observer = stamp, port, seq, observer
        # the connection's own build (its VERSION frame) and that build's table
        # (build_table); `table_build` is the build the rows were read from --
        # `build` except under with_table's known-bad arm
        self.build, self.table, self.types, self.table_build = build, table, types, build
        self.times = [t for _i, t, _o, _v in seq]
        self.announces = collections.defaultdict(list)   # caster -> [(t, skill, target, form)]
        self.alleg, self.kind = {}, {}
        self.status = collections.defaultdict(list)       # agent -> [(t, word)]
        self.applies, self.removes = [], []
        self.cast_time = {}                              # (caster, announce t) -> [61] seconds
        last61 = {}
        for _i, t, op, v in seq:
            if op == OP_FLOAT_TARGET and len(v) > 4 and v[1] == PROP_CAST_TIME:
                last61[v[2]] = (t, round(_f32(v[4]), 4))
            elif op == OP_FLOAT and len(v) > 3 and v[1] == PROP_CAST_TIME:
                last61[v[2]] = (t, round(_f32(v[3]), 4))
            if op in (OP_INT_TARGET, OP_INT) and len(v) > 3 and v[1] in ANNOUNCE_PROPS:
                w = last61.pop(v[2], None)
                if w is not None and abs(w[0] - t) < 1e-6:     # the same instant, ahead of it
                    self.cast_time[(v[2], t)] = w[1]
            if op == OP_CREATE and len(v) > 12:
                self.alleg[int(v[1])] = int(v[12])
                self.kind[int(v[1])] = int(v[4])
            elif op == OP_INT_TARGET and len(v) > 4 and v[1] in ANNOUNCE_PROPS:
                self.announces[v[2]].append((t, v[4], v[3], f"0x00A0[{v[1]}]"))
            elif op == OP_INT and len(v) > 3 and v[1] in ANNOUNCE_PROPS:
                self.announces[v[2]].append((t, v[3], None, f"0x009F[{v[1]}]"))
            elif op == OP_STATUS and len(v) > 2:
                self.status[v[1]].append((t, int(v[2])))
            elif op == OP_EFFECT_APPLY and len(v) > 5:
                self.applies.append({"t": t, "target": v[1], "skill": v[2], "field3": v[3],
                                     "buff": v[4], "dur": round(_f32(v[5]), 4), "i": _i})
            elif op == OP_EFFECT_REMOVE and len(v) > 2:
                self.removes.append({"t": t, "target": v[1], "buff": v[2], "i": _i})

    def span(self, a, b):
        return self.seq[bisect.bisect_left(self.times, a):bisect.bisect_right(self.times, b)]

    def batch(self, t):
        return [x for x in self.span(t - BATCH, t + BATCH) if x[2] != OP_SIM_TICK]

    def latest_announce(self, caster, t):
        best = None
        for a in self.announces.get(caster, ()):
            if a[0] <= t:
                best = a
        return best

    def completion(self, caster, ta, activation):
        """(t of the 58, None) or (None, why)."""
        lo = ta + max(0.3, 0.5 * activation)
        for _i, t, op, v in self.span(ta, ta + activation + 3.0):
            if op == OP_INT and len(v) > 3 and v[2] == caster and v[1] in END_PROPS:
                if t < lo:
                    continue
                a = self.latest_announce(caster, t)
                if a is None or a[0] != ta:
                    return None, ("superseded", round(t - ta, 3))
                if v[1] == PROP_FINISHED:
                    return t, None
                return None, (v[1], round(t - ta, 3))
        return None, ("no end",)

    def on_own_tick(self, caster, t):
        """Is `t` a tick instant of one of the caster's own Fire Storms -- its completion
        + k s, k = 1..10, within TICK_TOL (aotjoin's gate)?"""
        for ta, sk, _tg, _f in self.announces.get(caster, ()):
            if sk != FIRE_STORM or not (0.0 < t - ta <= 14.0):
                continue
            tc, _why = self.completion(caster, ta, 2.0)
            if tc is None:
                continue
            k = round(t - tc)
            if 1 <= k <= 10 and abs(t - tc - k) <= TICK_TOL:
                return True
        return False

    def foe(self, a, b):
        if a not in self.alleg or b not in self.alleg:
            return None
        return self.alleg[a] != self.alleg[b]

    def removal(self, target, buff, t, i=None):
        """The 0x0044 [target, buff] that ends the apply at `t` (wire index `i`): the
        first one AFTER the apply in wire order (REMOVAL_BY_ORDER) -- a buff id is
        reused the instant it is freed, and at 20260929T100038 :64557 667.396 the old
        instance's 0x0044 sits in the same batch ahead of the new 0x0042 -- or, on the
        known-bad arm (or with no `i`), the first at or after `t`."""
        for r in self.removes:
            if r["target"] != target or r["buff"] != buff:
                continue
            if REMOVAL_BY_ORDER and i is not None:
                if r["i"] > i:
                    return r["t"]
            elif r["t"] >= t - 1e-6:
                return r["t"]
        return None

    def round_end_in(self, batch):
        """Does this batch close the arena round (0x0181, docstring G4r)?"""
        return any(op == OP_ROUND_END for _i, _t, op, _v in batch)

    def status_before(self, agent, t):
        """The agent's last 0x00F1 word before the batch at `t`, or None."""
        last = None
        for tt, word in self.status.get(agent, ()):
            if tt >= t - BATCH:
                break
            last = word
        return last

    def dead_in(self, agent, batch):
        return any(op == OP_STATUS and len(v) > 2 and v[1] == agent and (int(v[2]) & DEAD_BIT)
                   for _i, _t, op, v in batch)

    def effect_live(self, agent, effect_id, t):
        """Is [6, agent, effect_id] live just before `t` (no [7] since)?"""
        live = False
        for _i, tt, op, v in self.seq:
            if tt >= t - BATCH:
                break
            if op == OP_INT and len(v) > 3 and v[1] in (PROP_ADD_EFFECT, PROP_REMOVE_EFFECT) \
                    and v[2] == agent and _int(v[3]) == effect_id:
                live = v[1] == PROP_ADD_EFFECT
        return live


def casts_of(conns, skills):
    """Every announce of a skill in `skills` (a set, or a function of the connection
    naming the set on its build's table), with its completion; the activation is the
    connection's own build's."""
    out = []
    for c in conns:
        want = skills(c) if callable(skills) else skills
        for caster, lst in c.announces.items():
            for (ta, sk, target, form) in lst:
                if sk not in want:
                    continue
                act = float(c.table.get(sk, {}).get("activation") or 1.0)
                tc, stop = c.completion(caster, ta, act)
                out.append({"c": c, "capture": c.stamp, "port": c.port, "observer": c.observer,
                            "caster": caster, "target": target, "skill": sk, "ta": ta,
                            "form": form, "tc": tc, "stop": stop, "act": act,
                            "ct": c.cast_time.get((caster, ta)),
                            "dt": None if tc is None else round(tc - ta, 3)})
    out.sort(key=lambda r: (r["capture"], r["port"], r["ta"]))
    return out


def completion_tokens(r):
    """The completion batch reduced to the cast's own tokens, in wire order."""
    c, cst, tg = r["c"], r["caster"], r["target"]
    toks = []
    for _i, t, op, v in c.batch(r["tc"]):
        if op == OP_INT and v[1] == PROP_FINISHED and v[2] == cst:
            toks.append("58")
        elif op == OP_INT_TARGET and v[1] == PROP_EFFECT_ON_TARGET and v[3] == cst:
            toks.append(f"[20 {'T' if v[2] == tg else v[2]} {v[4]}]")
        elif op == OP_INT and v[1] == PROP_ADD_EFFECT and v[2] == tg:
            toks.append(f"[6 T {v[3]}]")
        elif op == OP_EFFECT_APPLY and v[2] == r["skill"]:
            toks.append(f"42{'T' if v[1] == tg else '?'}")
        elif op == OP_EFFECT_APPLY:
            toks.append(f"42({v[2]})")
        elif op == OP_EFFECT_REMOVE:
            toks.append("44")
        elif op == OP_STATUS and v[1] == tg:
            toks.append(f"F1T(0x{int(v[2]):X})")
        elif op == OP_FLOAT_TARGET and v[1] in PROP_DAMAGE and v[3] == cst:
            toks.append(f"W{'T' if v[2] == tg else v[2]}")
        elif op == OP_FLOAT_TARGET and v[1] == PROP_HEALTH_GAIN and v[2] == cst:
            toks.append("55self")
        elif op == OP_ADRENALINE and len(v) > 1 and v[1] == tg:
            toks.append("CF")
        elif op == OP_INT and v[1] == PROP_SKILL_DAMAGE and v[2] == tg:
            toks.append(f"[10 {v[3]}]")
    return toks


def _words_by_foe(c, caster, batch):
    words = collections.defaultdict(list)
    for _i, _t, op, v in batch:
        if op == OP_FLOAT_TARGET and v[1] in PROP_DAMAGE and v[3] == caster:
            words[v[2]].append(round(_f32(v[4]), 5))
    return words


def _order_of(c, caster, batch):
    seq = []
    for _i, _t, op, v in batch:
        if op == OP_FLOAT_TARGET and v[1] in PROP_DAMAGE and v[3] == caster \
                and (not seq or seq[-1] != v[2]):
            seq.append(v[2])
    return seq


# ---------------------------------------------------------------- 179
def incendiary_rows(conns):
    """One row per 179 cast: the completion, the hex's lifecycle ([6] -> [7]), how it
    ended and the payoff batch."""
    rows = []
    for r in casts_of(conns, {INCENDIARY}):
        c, cst, tg, tc = r["c"], r["caster"], r["target"], r["tc"]
        if tc is None:
            rows.append(r)
            continue
        bb = c.batch(tc)
        r["tokens"] = completion_tokens(r)
        r["batch"] = [(round(t - tc, 3), _fmt(op, v)) for _i, t, op, v in bb]
        r["words_on_target"] = len(_words_by_foe(c, cst, bb).get(tg, ()))
        # I2r: a word onto the target that rides the caster's own Fire Storm tick
        r["words_on_target_tick"] = (r["words_on_target"] if r["words_on_target"]
                                     and c.on_own_tick(cst, tc) else 0)
        r["fx20"] = [(v[2], v[4]) for _i, _t, op, v in bb
                     if op == OP_INT_TARGET and v[1] == PROP_EFFECT_ON_TARGET and v[3] == cst]
        r["adds"] = [_int(v[3]) for _i, _t, op, v in bb
                     if op == OP_INT and v[1] == PROP_ADD_EFFECT and v[2] == tg]
        r["status_hex"] = [int(v[2]) & HEX_BIT for _i, _t, op, v in bb
                           if op == OP_STATUS and v[1] == tg]
        # the hex's 0x0042 (the target is the observer), its slot and its removal
        hx = [a for a in c.applies if a["skill"] == INCENDIARY and abs(a["t"] - tc) <= BATCH
              and a["target"] == tg]
        r["hex_apply"] = None
        if hx:
            a = hx[0]
            ops = [(op, v) for _i, _t, op, v in bb]
            i58 = next((n for n, (op, v) in enumerate(ops)
                        if op == OP_INT and v[1] == PROP_FINISHED and v[2] == cst), None)
            i42 = next((n for n, (op, v) in enumerate(ops)
                        if op == OP_EFFECT_APPLY and v[4] == a["buff"]), None)
            if1 = next((n for n, (op, v) in enumerate(ops)
                        if op == OP_STATUS and v[1] == tg), None)
            i20 = next((n for n, (op, v) in enumerate(ops)
                        if op == OP_INT_TARGET and v[1] == PROP_EFFECT_ON_TARGET and v[2] == tg), None)
            i6 = next((n for n, (op, v) in enumerate(ops)
                       if op == OP_INT and v[1] == PROP_ADD_EFFECT and v[2] == tg), None)
            rt = c.removal(tg, a["buff"], a["t"], a["i"])
            prior = c.status_before(tg, a["t"])
            r["hex_apply"] = {"field3": a["field3"], "dur": a["dur"], "buff": a["buff"],
                              "order_58_42_f1": None not in (i58, i42, if1) and i58 < i42 < if1,
                              # I3r: the 58 ahead of the 0x0042, then an 0x00F1 with the hex
                              # bit -- unless the target's status already carried it
                              "order_58_42": None not in (i58, i42) and i58 < i42,
                              "f1_hex_after": (None not in (i42, if1) and if1 > i42
                                               and bool(int(ops[if1][1][2]) & HEX_BIT)),
                              "already_hexed": prior is not None and bool(prior & HEX_BIT),
                              "between_20_and_6": None not in (i20, i42, i6) and i20 < i42 < i6,
                              "removal_at": None if rt is None else round(rt - tc, 3),
                              "residual": None if rt is None else round(rt - a["t"] - a["dur"], 3)}
        # the end: the first [7, T, id in adds] after the completion batch
        r["end"] = r["end_dt"] = None
        r["end_why"], r["payoff"], r["end_batch"] = [], {}, []
        r["payoff_takers_foe"], r["payoff_own58"], r["payoff_fx20"] = [], [], []
        r["payoff_burning"] = {}
        if r["adds"]:
            for _i, t, op, v in c.span(tc + BATCH + 0.001, tc + END_WINDOW):
                if op == OP_INT and v[1] == PROP_REMOVE_EFFECT and v[2] == tg and _int(v[3]) in r["adds"]:
                    r["end"] = t
                    break
        if r["end"] is not None:
            te = r["end"]
            eb = c.batch(te)
            r["end_dt"] = round(te - tc, 3)
            r["end_batch"] = [(round(t - tc, 3), _fmt(op, v)) for _i, t, op, v in eb]
            why = []
            if c.dead_in(tg, eb):
                why.append("target died")
            if c.dead_in(cst, eb):
                why.append("caster died")
            own = [(v[2], (c.latest_announce(v[2], t) or (None, None))[1])
                   for _i, t, op, v in eb if op == OP_INT and v[1] == PROP_FINISHED and v[2] != cst]
            if any(who == tg and sk == REMOVE_HEX for who, sk in own):
                why.append("removed (the target's Remove Hex)")
            elif own:
                why.append(f"another 58 in the batch {own}")
            r["end_why"] = why
            # a removal is a removal whatever its offset (one Remove Hex landed at +2.967)
            r["scheduled"] = (abs(r["end_dt"] - PAYOFF_AT) <= PAYOFF_TOL
                              and not any(w.startswith("removed") for w in why))
            words = _words_by_foe(c, cst, eb)
            # a foe whose end-batch words ALL already landed on it from this caster in
            # the COMPLETION batch is taking the caster's periodic tick (Fire Storm's,
            # one value a second), not the payoff (690.819: EV-6) -- set aside, printed
            at_completion = _words_by_foe(c, cst, bb)
            r["payoff_tick"] = {foe: ws for foe, ws in words.items()
                                if ws and all(w in at_completion.get(foe, ()) for w in ws)}
            words = {foe: ws for foe, ws in words.items() if foe not in r["payoff_tick"]}
            r["payoff"] = dict(words)
            r["payoff_takers_foe"] = [c.foe(cst, foe) for foe in words]
            r["payoff_own58"] = [(v[2], (c.latest_announce(v[2], t) or (None, None))[1])
                                 for _i, t, op, v in eb
                                 if op == OP_INT and v[1] == PROP_FINISHED and v[2] == cst]
            r["payoff_fx20"] = [(v[2], v[4]) for _i, _t, op, v in eb
                                if op == OP_INT_TARGET and v[1] == PROP_EFFECT_ON_TARGET and v[3] == cst]
            r["payoff_a1"] = sum(1 for _i, _t, op, _v in eb if op == OP_POINT_EFFECT)
            r["payoff_order"] = _order_of(c, cst, eb)
            # Burning per struck foe: a new [6, foe, 25] in the batch, or already burning
            for foe in words:
                new6 = any(op == OP_INT and v[1] == PROP_ADD_EFFECT and v[2] == foe
                           and _int(v[3]) == BURNING_EFFECT_ID for _i, _t, op, v in eb)
                r["payoff_burning"][foe] = ("new" if new6 else
                                            "already" if c.effect_live(foe, BURNING_EFFECT_ID, te)
                                            else "none")
            # the observer struck: the 0x00CF -> [10, obs, 179] -> word prefix, and its Burning
            obs = c.observer
            r["observer_struck"] = obs in words
            if obs in words:
                ops = [(op, v) for _i, _t, op, v in eb]
                i_cf = next((n for n, (op, v) in enumerate(ops)
                             if op == OP_ADRENALINE and len(v) > 1 and v[1] == obs), None)
                i_10 = next((n for n, (op, v) in enumerate(ops)
                             if op == OP_INT and v[1] == PROP_SKILL_DAMAGE and v[2] == obs
                             and v[3] == INCENDIARY), None)
                i_w = next((n for n, (op, v) in enumerate(ops)
                            if op == OP_FLOAT_TARGET and v[1] in PROP_DAMAGE and v[2] == obs), None)
                r["observer_prefix_ok"] = None not in (i_cf, i_10, i_w) and i_cf < i_10 < i_w
                burn = [a for a in c.applies if a["skill"] == BURNING and a["target"] == obs
                        and abs(a["t"] - te) <= BATCH]
                r["observer_burning"] = [(a["field3"], a["dur"],
                                          None if c.removal(obs, a["buff"], a["t"], a["i"]) is None
                                          else round(c.removal(obs, a["buff"], a["t"], a["i"]) - a["t"], 3))
                                         for a in burn]
        rows.append(r)
    return rows


# ---------------------------------------------------------------- 185
def mind_burn_rows(conns):
    rows = []
    for r in casts_of(conns, {MIND_BURN}):
        c, cst, tg, tc = r["c"], r["caster"], r["target"], r["tc"]
        if tc is None:
            rows.append(r)
            continue
        bb = c.batch(tc)
        r["tokens"] = completion_tokens(r)
        r["batch"] = [(round(t - tc, 3), _fmt(op, v)) for _i, t, op, v in bb]
        words = _words_by_foe(c, cst, bb)
        r["words"] = dict(words)
        r["on_target"] = list(words.get(tg, ()))
        r["others"] = {foe: ws for foe, ws in words.items() if foe != tg}
        r["fx20"] = [(v[2], v[4]) for _i, _t, op, v in bb
                     if op == OP_INT_TARGET and v[1] == PROP_EFFECT_ON_TARGET and v[3] == cst]
        r["order"] = _order_of(c, cst, bb)
        r["foe_signal"] = {}
        for foe, ws in words.items():
            new6 = any(op == OP_INT and v[1] == PROP_ADD_EFFECT and v[2] == foe
                       and _int(v[3]) == BURNING_EFFECT_ID for _i, _t, op, v in bb)
            r["foe_signal"][foe] = (len(ws), "new" if new6 else
                                    "already" if c.effect_live(foe, BURNING_EFFECT_ID, tc) else "none")
        r["observer_burning"] = [(a["field3"], a["dur"],
                                  None if c.removal(a["target"], a["buff"], a["t"], a["i"]) is None
                                  else round(c.removal(a["target"], a["buff"], a["t"], a["i"]) - a["t"], 3))
                                 for a in c.applies if a["skill"] == BURNING
                                 and a["target"] == c.observer and abs(a["t"] - tc) <= BATCH]
        rows.append(r)
    return rows


# ---------------------------------------------------------------- generic hex
def hex_rows(conns):
    """Every type-4 cast that completed: its [6]s and how it ended (L1); every hex 0x0042
    (G1-G4); the snare words (L3)."""
    casts = []
    for r in casts_of(conns, lambda c: {k for k, t in c.types.items() if t == TYPE_HEX}):
        c, cst, tg, tc = r["c"], r["caster"], r["target"], r["tc"]
        if tc is None:
            casts.append(r)
            continue
        bb = c.batch(tc)
        r["tokens"] = completion_tokens(r)
        r["adds"] = [_int(v[3]) for _i, _t, op, v in bb
                     if op == OP_INT and v[1] == PROP_ADD_EFFECT and v[2] == tg]
        r["status_at_apply"] = [int(v[2]) for _i, _t, op, v in bb if op == OP_STATUS and v[1] == tg]
        r["speed_at_apply"] = [round(float(v[2]), 2) for _i, _t, op, v in bb
                               if op == OP_SPEED and v[1] == tg]
        r["end_dt"], r["speed_at_end"], r["status_at_end"], r["removes"] = None, [], [], []
        if r["adds"]:
            for _i, t, op, v in c.span(tc + BATCH + 0.001, tc + END_WINDOW):
                if op == OP_INT and v[1] == PROP_REMOVE_EFFECT and v[2] == tg and _int(v[3]) in r["adds"]:
                    r["end_dt"] = round(t - tc, 3)
                    eb = c.batch(t)
                    r["speed_at_end"] = [round(float(w[2]), 2) for _j, _u, o2, w in eb
                                         if o2 == OP_SPEED and w[1] == tg]
                    r["status_at_end"] = [int(w[2]) for _j, _u, o2, w in eb
                                          if o2 == OP_STATUS and w[1] == tg]
                    r["removes"] = [_int(w[3]) for _j, _u, o2, w in eb
                                    if o2 == OP_INT and w[1] == PROP_REMOVE_EFFECT and w[2] == tg]
                    break
        casts.append(r)
    applies = []
    for c in conns:
        for a in c.applies:
            if c.types.get(a["skill"]) != TYPE_HEX:
                continue
            row = c.table.get(a["skill"], {})
            d0, d15 = float(row.get("duration0") or 0), float(row.get("duration15") or 0)
            pred = interp(d0, d15, a["field3"])
            # G3r: the client's own two-point scaler (0x005A8920), which ROUNDS
            pred_r = effects.interp(d0, d15, a["field3"])
            rt = c.removal(a["target"], a["buff"], a["t"], a["i"])
            # G4r: stripped by the target's death, or by the arena round's end (0x0181)
            dead_at_end = rt is not None and c.dead_in(a["target"], c.batch(rt))
            round_end = rt is not None and c.round_end_in(c.batch(rt))
            bb = c.batch(a["t"])
            ops = [(op, v) for _i, _t, op, v in bb]
            i42 = next((n for n, (op, v) in enumerate(ops)
                        if op == OP_EFFECT_APPLY and v[4] == a["buff"] and v[1] == a["target"]), None)
            i58 = next((n for n, (op, v) in enumerate(ops)
                        if op == OP_INT and v[1] == PROP_FINISHED), None)
            if1 = next((n for n, (op, v) in enumerate(ops)
                        if op == OP_STATUS and v[1] == a["target"]), None)
            prior = c.status_before(a["target"], a["t"])
            applies.append({"capture": c.stamp, "port": c.port, "skill": a["skill"],
                            "target": a["target"], "on_observer": a["target"] == c.observer,
                            "t": round(a["t"], 3),
                            "field3": a["field3"], "dur": a["dur"], "pred": round(pred, 3),
                            "g3_ok": abs(pred - a["dur"]) < 0.01,
                            "pred_r": pred_r, "g3r_ok": abs(pred_r - a["dur"]) < 0.01,
                            "build": c.build, "table_build": c.table_build,
                            "d0d15": (d0, d15),
                            "order_58_42_f1": None not in (i58, i42, if1) and i58 < i42 < if1,
                            # G2r: the 58 ahead of the 0x0042, then an 0x00F1 with the hex
                            # bit -- unless the target's status already carried it
                            "order_58_42": None not in (i58, i42) and i58 < i42,
                            "f1_hex_after": (None not in (i42, if1) and if1 > i42
                                             and bool(int(ops[if1][1][2]) & HEX_BIT)),
                            "already_hexed": prior is not None and bool(prior & HEX_BIT),
                            "removal_at": None if rt is None else round(rt - a["t"], 3),
                            "residual": None if rt is None else round(rt - a["t"] - a["dur"], 3),
                            "stripped": rt is None or dead_at_end,
                            "round_end": round_end,
                            "end_why": ("none" if rt is None else "death" if dead_at_end
                                        else "round end" if round_end
                                        else "scheduled" if abs(rt - a["t"] - a["dur"]) <= REMOVAL_TOL
                                        else "early")})
    return casts, applies


def all_applies(conns):
    """Every 0x0042 corpus-wide: on the observer or not, and who the others are."""
    out = []
    for c in conns:
        for a in c.applies:
            out.append({"capture": c.stamp, "port": c.port, "skill": a["skill"],
                        "target": a["target"], "on_observer": a["target"] == c.observer,
                        "kind": c.kind.get(a["target"])})
    return out


def multi_foe_batches(conns):
    """179 payoff batches and 185 completion batches striking >= 2 foes: the order (L2)."""
    out = []
    for r in incendiary_rows(conns):
        if r.get("end") is not None and len(set(r["payoff"])) >= 2:
            seq = r["payoff_order"]
            out.append((INCENDIARY, r["port"], round(r["ta"], 3), r["target"], seq,
                        seq == sorted(seq), seq[0] == r["target"]))
    for r in mind_burn_rows(conns):
        if r.get("tc") is not None and len(set(r["words"])) >= 2:
            seq = r["order"]
            out.append((MIND_BURN, r["port"], round(r["ta"], 3), r["target"], seq,
                        seq == sorted(seq), seq[0] == r["target"]))
    return out


# ---------------------------------------------------------------- conditions
def condition_rows(conns):
    out = []
    for c in conns:
        for a in c.applies:
            if a["skill"] not in CONDS:
                continue
            bb = c.batch(a["t"])
            rt = c.removal(a["target"], a["buff"], a["t"], a["i"])
            f58 = sorted({v[2] for _i, _t, op, v in bb if op == OP_INT and v[1] == PROP_FINISHED})
            # a 58 in the batch attributes the condition only when that caster's latest
            # announce NAMES this target (an environmental apply can share any agent's instant)
            at_me = [v[2] for _i, t, op, v in bb if op == OP_INT and v[1] == PROP_FINISHED
                     and (c.latest_announce(v[2], t) or (None, None, None))[2] == a["target"]]
            p10 = [v[3] for _i, _t, op, v in bb
                   if op == OP_INT and v[1] == PROP_SKILL_DAMAGE and v[2] == a["target"]]
            ids = [_int(v[3]) for _i, _t, op, v in bb
                   if op == OP_INT and v[1] == PROP_ADD_EFFECT and v[2] == a["target"]]
            out.append({"capture": c.stamp, "port": c.port, "skill": a["skill"],
                        "name": CONDS[a["skill"]], "target": a["target"],
                        "on_observer": a["target"] == c.observer, "field3": a["field3"],
                        "dur": a["dur"], "cast_applied": bool(f58), "skill_applied": bool(at_me or p10),
                        "effect_ids": ids,
                        "residual": None if rt is None else round(rt - a["t"] - a["dur"], 3)})
    return out


# ---------------------------------------------------------------- the census
def census(stamps=None, codec=None):
    """Every live capture (or those named), every game connection that frames whole, each
    with its own build (the client's VERSION frame) and that build's table (build_table).
    A connection whose build cannot be read, or whose build has no pristine image in the
    vault, is REFUSED with the reason -- never scored against another build's table."""
    codec = codec or bufflog.Codec()
    root = vaultpath.require_dir("captures", "live", why="hexjoin reads live captures")
    conns, refused = [], []
    set_aside, declared_not_refused = [], []
    captures = 0
    for capdir, _who in livewire.live_captures(root):
        stamp = os.path.basename(capdir)
        if stamps and stamp not in stamps:
            continue
        captures += 1
        declared = livewire.declared_gaps(capdir)
        for ch in tape.channel_files(capdir):
            if ch["connection"] in declared:
                # the capture's OWN manifest declares this connection gapped: set it aside
                # BY NAME, and decode it once to show it still refuses
                try:
                    deepwoundjoin.sequence(capdir, ch["connection"], codec)
                except (bufflog.BuffLogError, tape.TapeError) as exc:
                    set_aside.append((stamp, ch["connection"], str(exc)[:100]))
                    print(f"   SET ASIDE {stamp} {ch['connection']}: its manifest declares it "
                          f"gapped {declared[ch['connection']]} -- still refused")
                else:
                    declared_not_refused.append((stamp, ch["connection"]))
                continue
            try:
                seq = deepwoundjoin.sequence(capdir, ch["connection"], codec)
                build = tape.client_version(capdir, ch["connection"])["build"]
            except (bufflog.BuffLogError, tape.TapeError) as exc:
                refused.append((stamp, ch["connection"], str(exc)[:100]))
                continue
            try:
                table, types = build_table(build)
            except LookupError as exc:
                refused.append((stamp, ch["connection"], f"no table for build {build}: "
                                                         f"{str(exc)[:80]}"))
                continue
            follow = {k for k, t in types.items() if t == TYPE_HEX} | {MIND_BURN}
            port = ch["connection"].split("->")[0].rsplit(":", 1)[-1]
            wants_observer = any(op == OP_EFFECT_APPLY for _i, _t, op, _v in seq) or any(
                (op == OP_INT_TARGET and len(v) > 4 and v[1] in ANNOUNCE_PROPS and v[4] in follow)
                or (op == OP_INT and len(v) > 3 and v[1] in ANNOUNCE_PROPS and v[3] in follow)
                for _i, _t, op, v in seq)
            observer = None
            if wants_observer:
                c2s = spellhitjoin.c2s_of(capdir, ch["file"])
                observer, _press, _why = spellhitjoin.observer_of(seq, c2s)
            conns.append(Conn(stamp, port, seq, observer, build, table, types))
    return {"captures": captures, "connections": len(conns), "refused": refused,
            "set_aside": set_aside, "declared_not_refused": declared_not_refused,
            "conns": conns, "stamps": stamps,
            "builds": dict(collections.Counter(c.build for c in conns)),
            "observer_named": sum(1 for c in conns if c.observer is not None)}


def upto(c, stamp):
    """The census `c` cut to the captures BEFORE `stamp` -- the corpus the predictions were
    registered on (connections, refusals and set-asides cut with it)."""
    conns = [cc for cc in c["conns"] if cc.stamp < stamp]
    return dict(c, conns=conns, connections=len(conns),
                refused=[r for r in c["refused"] if r[0] < stamp],
                set_aside=[r for r in c.get("set_aside", ()) if r[0] < stamp],
                captures=len({cc.stamp for cc in conns}),
                observer_named=sum(1 for cc in conns if cc.observer is not None))


def narrow(c, stamp):
    """The census `c` cut to ONE capture."""
    conns = [cc for cc in c["conns"] if cc.stamp == stamp]
    return dict(c, conns=conns, connections=len(conns),
                refused=[r for r in c["refused"] if r[0] == stamp],
                set_aside=[r for r in c.get("set_aside", ()) if r[0] == stamp],
                captures=len({cc.stamp for cc in conns}),
                observer_named=sum(1 for cc in conns if cc.observer is not None))


def score(c):
    """The numbers the predictions are judged on -- and the verdicts."""
    conns = c["conns"]
    inc = incendiary_rows(conns)
    mb = mind_burn_rows(conns)
    hcasts, happlies = hex_rows(conns)
    every42 = all_applies(conns)
    conds = condition_rows(conns)
    # THE WITNESS AND THE CORPUS ARE KEPT APART (EV-3): every EXACT number below is the
    # witness capture's (EXPECT_CAPTURE, the tape the predictions were registered on);
    # a `*_corpus` key is the whole corpus's and a FLOOR. A confirming later capture
    # (the same casts again) moves the floors and nothing else.
    wcon = [cc for cc in conns if cc.stamp == EXPECT_CAPTURE]
    order = multi_foe_batches(wcon)                  # exact, per tape
    s = {"captures": c["captures"], "connections": c["connections"], "refused": len(c["refused"]),
         "observer_named": c["observer_named"], "witness": EXPECT_CAPTURE}

    # ---- 179
    wit = [r for r in inc if r["capture"] == EXPECT_CAPTURE]
    done_c = [r for r in inc if r["tc"] is not None]        # corpus
    done = [r for r in wit if r["tc"] is not None]          # witness: exact
    stopped = [(r["port"], round(r["ta"], 3), r["stop"]) for r in inc if r["tc"] is None]
    s["i_announces"], s["i_announces_corpus"] = len(wit), len(inc)
    s["i_per_port"] = dict(collections.Counter(r["port"] for r in wit))
    s["i_forms"] = dict(collections.Counter(r["form"] for r in inc))
    s["i_by_observer"] = sum(1 for r in inc if r["caster"] == r["observer"])
    s["i_completed"], s["i_completed_corpus"], s["i_stopped"] = len(done), len(done_c), stopped
    dts = [r["dt"] for r in done_c]
    s["i_dt"] = (min(dts), max(dts)) if dts else None
    s["i1"] = (s["i_per_port"] == EXPECT_179_PER_PORT and s["i_by_observer"] == 0
               and set(s["i_forms"]) == {"0x00A0[60]"} and bool(done)
               and all(abs(dt - 1.0) <= COMPLETION_TOL for dt in dts))
    # I1r (2026-09-28): the completion at the [61] seconds when sent, else the activation
    s["i_ct_casts"] = [(r["capture"], r["port"], round(r["ta"], 3), r["ct"], r["dt"])
                       for r in done_c if r.get("ct") is not None]
    s["i1r_off"] = [(r["capture"], r["port"], round(r["ta"], 3), r.get("ct"), r["dt"]) for r in done_c
                    if abs(r["dt"] - (r["ct"] if r.get("ct") is not None else 1.0)) > COMPLETION_TOL]
    s["i1r"] = (s["i_per_port"] == EXPECT_179_PER_PORT and s["i_by_observer"] == 0
                and set(s["i_forms"]) == {"0x00A0[60]"} and bool(done) and not s["i1r_off"])
    s["i_fx20_348"] = sum(1 for r in done_c if (r["target"], 348) in r["fx20"])
    s["i_words_on_target"] = sum(r["words_on_target"] for r in done_c)
    s["i2"] = bool(done) and s["i_fx20_348"] == len(done_c) and s["i_words_on_target"] == 0
    # I2r: no word from the caster onto the target but one riding its own Fire Storm tick
    s["i_words_on_target_tick"] = [(r["capture"], r["port"], round(r["ta"], 3), r["words_on_target"])
                                   for r in done_c if r["words_on_target_tick"]]
    s["i2r"] = (bool(done) and s["i_fx20_348"] == len(done_c)
                and sum(r["words_on_target"] - r["words_on_target_tick"] for r in done_c) == 0)
    hx = [r["hex_apply"] for r in done_c if r["hex_apply"]]
    s["i_hex_applies"] = hx
    s["i3"] = (len(hx) >= 1 and all(h["dur"] == 3.0 and h["order_58_42_f1"] for h in hx)
               and all(any(b & HEX_BIT for b in r["status_hex"]) for r in done_c if r["hex_apply"]))
    # I3r: the 58 ahead of the 0x0042; an 0x00F1 with the hex bit after it unless the
    # observer's status already carried the bit (a status word that does not change)
    s["i_hex_already"] = [(r["capture"], r["port"], round(r["ta"], 3), r["caster"], r["hex_apply"]["field3"])
                          for r in done_c if r["hex_apply"] and r["hex_apply"]["already_hexed"]
                          and not r["hex_apply"]["f1_hex_after"]]
    s["i3r"] = (len(hx) >= 1 and all(h["dur"] == 3.0 and h["order_58_42"]
                                     and (h["f1_hex_after"] or h["already_hexed"]) for h in hx))
    ends = [r for r in done if r["end"] is not None]
    sched = [r for r in ends if r["scheduled"]]
    early = [r for r in ends if not r["scheduled"]]
    removed = [r for r in early if any(w.startswith("removed") for w in r["end_why"])]
    # (a scheduled end whose batch also carries another agent's 58 is still scheduled: the
    # target's own other casts share the instant on 4 of them; only its Remove Hex removes)
    tdied = [r for r in early if "target died" in r["end_why"] and r not in removed]
    cdied = [r for r in early if "caster died" in r["end_why"] and r not in removed and r not in tdied]
    s["i_ends"] = len(ends)
    s["i_end_offsets"] = sorted(r["end_dt"] for r in ends)
    s["i_scheduled"] = len(sched)
    s["i_scheduled_with_words"] = sum(1 for r in sched if r["payoff"])
    s["i_scheduled_range"] = ((min(r["end_dt"] for r in sched), max(r["end_dt"] for r in sched))
                              if sched else None)
    s["i_removed"] = [(r["port"], round(r["ta"], 3), r["end_dt"], len(r["payoff"])) for r in removed]
    s["i_target_died"] = [(r["port"], round(r["ta"], 3), r["end_dt"], sorted(r["payoff"]))
                          for r in tdied]
    s["i_caster_died"] = [(r["port"], round(r["ta"], 3), r["end_dt"], sorted(r["payoff"]))
                          for r in cdied]
    s["i_unexplained_early"] = [(r["port"], round(r["ta"], 3), r["end_dt"], r["end_why"])
                                for r in early if r not in removed and r not in tdied and r not in cdied]
    # I4 AS REGISTERED: the payoff at +3.0 on every cast whose target lived, with the caster's words
    lived = [r for r in ends if "target died" not in r["end_why"]]
    s["i4"] = (bool(lived) and all(r["scheduled"] and r["payoff"] for r in lived)
               and not any(r["payoff_own58"] or r["payoff_fx20"] for r in lived))
    # I4c
    with_words = [r for r in ends if r["payoff"]]
    s["i_payoff_58_of_179"] = sum(1 for r in with_words for _w, sk in r["payoff_own58"] if sk == INCENDIARY)
    s["i_payoff_mixed"] = [(r["port"], round(r["ta"], 3), r["payoff_own58"], r["payoff_fx20"])
                           for r in with_words if r["payoff_own58"] or r["payoff_fx20"]]
    # EV-6: a scheduled end whose only word is the caster's periodic tick (set aside in
    # incendiary_rows) is a mixed instant, not a payoff -- 690.819, printed
    s["i_payoff_tick"] = [(r["port"], round(r["ta"], 3), r["end_dt"], r["payoff_tick"])
                          for r in ends if r.get("payoff_tick")]
    s["i4c"] = (len(sched) >= 18 and s["i_scheduled_with_words"] >= 18
                and len(removed) >= 4 and all(n == 0 for _p, _t, _d, n in s["i_removed"])
                and sum(1 for r in tdied if r["payoff"]) >= 2
                and not s["i_unexplained_early"]
                and s["i_payoff_58_of_179"] == 0 and len(s["i_payoff_mixed"]) <= 2)
    s["i_payoff_a1"] = sum(r.get("payoff_a1", 0) for r in ends if r["payoff"])
    takers = collections.Counter(len(r["payoff"]) for r in ends if r["payoff"])
    s["i_takers_hist"] = dict(sorted(takers.items()))
    s["i_takers_not_foe"] = sum(1 for r in ends for f in r["payoff_takers_foe"] if f is not True)
    s["i_target_struck"] = sum(1 for r in ends if r["payoff"] and r["target"] in r["payoff"])
    s["i_target_struck_of"] = sum(1 for r in ends if r["payoff"] and "target died" not in r["end_why"])
    s["i5"] = (bool(takers) and set(takers) <= {1, 2, 3, 4} and s["i_takers_not_foe"] == 0)
    burning = collections.Counter(v for r in ends for v in r["payoff_burning"].values())
    s["i_payoff_burning"] = dict(burning)
    obs_hits = [r for r in ends if r.get("observer_struck")]
    s["i_observer_struck"] = len(obs_hits)
    s["i_observer_prefix_ok"] = sum(1 for r in obs_hits if r.get("observer_prefix_ok"))
    s["i_observer_burning"] = [b for r in obs_hits for b in r.get("observer_burning", ())]
    s["i6"] = (len(obs_hits) >= 1 and len(s["i_observer_burning"]) == len(obs_hits)
               and all(f3 == 3 and dur == 3.0 and rem is not None and abs(rem - 3.0) <= REMOVAL_TOL
                       for f3, dur, rem in s["i_observer_burning"]))

    # ---- 185
    mwit = [r for r in mb if r["capture"] == EXPECT_CAPTURE]
    mdone_c = [r for r in mb if r["tc"] is not None]        # corpus
    mdone = [r for r in mwit if r["tc"] is not None]        # witness: exact
    s["m_announces"], s["m_announces_corpus"] = len(mwit), len(mb)
    s["m_per_port"] = dict(collections.Counter(r["port"] for r in mwit))
    s["m_by_observer"] = sum(1 for r in mb if r["caster"] == r["observer"])
    s["m_completed"], s["m_completed_corpus"] = len(mdone), len(mdone_c)
    s["m_stopped"] = [(r["port"], round(r["ta"], 3), r["stop"]) for r in mb if r["tc"] is None]
    mdts = [r["dt"] for r in mdone_c]
    s["m_dt"] = (min(mdts), max(mdts)) if mdts else None
    s["m1"] = (s["m_per_port"] == EXPECT_185_PER_PORT and bool(mdone)
               and all(abs(dt - 1.0) <= COMPLETION_TOL for dt in mdts)
               and set(collections.Counter(r["form"] for r in mb)) == {"0x00A0[60]"})
    # M1r: the completion at the [61] seconds when sent, else the activation
    s["m_ct_casts"] = [(r["capture"], r["port"], round(r["ta"], 3), r["ct"], r["dt"])
                       for r in mdone_c if r.get("ct") is not None]
    s["m1r_off"] = [(r["capture"], r["port"], round(r["ta"], 3), r.get("ct"), r["dt"]) for r in mdone_c
                    if abs(r["dt"] - (r["ct"] if r.get("ct") is not None else 1.0)) > COMPLETION_TOL]
    s["m1r"] = (s["m_per_port"] == EXPECT_185_PER_PORT and bool(mdone) and not s["m1r_off"]
                and set(collections.Counter(r["form"] for r in mb)) == {"0x00A0[60]"})
    twin = [r for r in mdone if len(r["on_target"]) >= 2]
    single = [r for r in mdone if len(r["on_target"]) == 1]
    none_ = [r for r in mdone_c if not r["on_target"]]      # an invariant: none anywhere
    s["m_twin"], s["m_single"], s["m_none"] = len(twin), len(single), len(none_)
    s["m_twin_identical"] = sum(1 for r in twin if len(set(r["on_target"])) == 1)
    s["m_fx20_331"] = sum(1 for r in mdone_c if (r["target"], 331) in r["fx20"])
    mixed = [r for r in mdone if r["others"]
             and any(len(ws) != len(r["on_target"]) for ws in r["others"].values())]
    s["m_mixed"] = [(r["port"], round(r["ta"], 3), r["target"], len(r["on_target"]),
                     {f: len(w) for f, w in r["others"].items()}) for r in mixed]
    s["m_target_single_adjacent_twin"] = [(r["port"], round(r["ta"], 3)) for r in mixed
                                          if len(r["on_target"]) == 1
                                          and any(len(w) >= 2 for w in r["others"].values())]
    # M2 AS REGISTERED: a twin cast strikes the adjacent too, a single strikes the target alone
    s["m2"] = (bool(mdone) and s["m_fx20_331"] == len(mdone_c) and not none_
               and all(len(set(r["on_target"])) == 1 for r in twin)
               and not any(r["others"] for r in single) and not mixed)
    sig = collections.Counter((n, kind, "target" if foe == r["target"] else "adjacent")
                              for r in mdone for foe, (n, kind) in r["foe_signal"].items())
    s["m_foe_signal"] = {f"{n} word(s), {kind}, {who}": v for (n, kind, who), v in sorted(sig.items())}
    twin_no_signal = sum(v for (n, kind, _w), v in sig.items() if n >= 2 and kind == "none")
    single_signal = sum(v for (n, kind, _w), v in sig.items() if n == 1 and kind == "new")
    s["m_twin_no_burning"], s["m_single_with_burning"] = twin_no_signal, single_signal
    # M2c
    s["m2c"] = (len(s["m_target_single_adjacent_twin"]) >= 1 and len(mixed) >= 4
                and twin_no_signal == 0 and single_signal <= 1
                and sum(v for (n, _k, _w), v in sig.items() if n >= 2) >= 30)
    s["m_onto_observer"] = sum(1 for r in mdone if r["target"] == r["observer"])
    s["m3"] = None                       # untestable as registered (0 casts onto the observer)
    ob = [b for r in mdone for b in r["observer_burning"]]
    s["m_observer_burning"] = ob
    s["m3c"] = (len(ob) >= 2 and all(1 <= f3 <= 10 and float(f3) == dur and rem is not None
                                     and abs(rem - dur) <= REMOVAL_TOL for f3, dur, rem in ob))
    s["m4"] = bool(mb) and s["m_by_observer"] == 0
    s["m4_second_clause"] = None            # UNTESTABLE: no cast onto the observer, no current energy
    # the rank CORROBORATION: 179's hex field3 (the caster's Fire Magic) predicts both Burnings
    # scored on the WITNESS's hex applies -- the claim is its caster's rank (EV-3's scope);
    # the corpus's ranks are printed (20260928T103123 adds agent 3's 179 at field3 0)
    ranks = {r["hex_apply"]["field3"] for r in done if r["hex_apply"]}
    s["m_ranks_corpus"] = sorted({h["field3"] for h in hx})
    s["m_rank_fits"] = (len(ranks) == 1 and all(
        int(math.floor(interp(1, 3, r) + 0.5)) == 3 and int(math.floor(interp(1, 10, r) + 0.5)) == 9
        for r in ranks))

    # ---- generic hex
    s["h_announces"] = dict(collections.Counter(r["skill"] for r in hcasts))
    s["h_where"] = {f"{k[0]}/{k[1]} {k[2]}": n for k, n in sorted(collections.Counter(
        (r["capture"], r["port"], r["skill"]) for r in hcasts).items())}
    s["h_42_per_skill"] = dict(collections.Counter(a["skill"] for a in happlies))
    s["h_42_on_observer"] = sum(1 for a in happlies if a["on_observer"])
    s["h_42_elsewhere"] = sum(1 for a in happlies if not a["on_observer"])
    s["all_42"] = len(every42)
    s["all_42_on_observer"] = sum(1 for a in every42 if a["on_observer"])
    others = [a for a in every42 if not a["on_observer"]]
    s["all_42_elsewhere"] = {f"{k[0]}/{k[1]} agent {k[2]} kind {k[3]}": n for k, n in
                             collections.Counter((a["capture"], a["port"], a["target"], a["kind"])
                                                 for a in others).items()}
    s["g1"] = len(happlies) >= 1 and s["h_42_elsewhere"] == 0
    s["g2"] = len(happlies) >= 1 and all(a["order_58_42_f1"] for a in happlies)
    s["g2_already_hexed"] = [(a["capture"], a["port"], a["t"], a["skill"]) for a in happlies
                             if not a["order_58_42_f1"] and a["already_hexed"]]
    s["g2r"] = len(happlies) >= 1 and all(a["order_58_42"] and (a["f1_hex_after"] or a["already_hexed"])
                                          for a in happlies)
    s["g3_misses"] = sum(1 for a in happlies if not a["g3_ok"])
    s["g3_miss_rows"] = [(a["capture"], a["port"], a["t"], a["skill"], a["field3"], a["dur"], a["pred"])
                         for a in happlies if not a["g3_ok"]]
    s["g3"] = len(happlies) >= 1 and s["g3_misses"] == 0
    # G3r (docstring): the client's own ROUNDED scaler on the tape's own build's row
    s["g3r_miss_rows"] = [(a["capture"], a["port"], a["t"], a["skill"], a["field3"], a["dur"],
                           a["pred_r"]) for a in happlies if not a["g3r_ok"]]
    s["g3r"] = len(happlies) >= 1 and not s["g3r_miss_rows"]
    # every hex apply's (capture, port, t, skill, field3, f32, the row's endpoints, the
    # tape's build, the build the row was read from) -- what G3 / G3r were scored on
    s["g3_rows"] = [(a["capture"], a["port"], a["t"], a["skill"], a["field3"], a["dur"],
                     a["d0d15"], a["build"], a["table_build"]) for a in happlies]
    s["h_residuals"] = [(a["skill"], a["residual"]) for a in happlies]
    s["g4"] = len(happlies) >= 1 and all(
        a["stripped"] or (a["residual"] is not None and abs(a["residual"]) <= REMOVAL_TOL)
        for a in happlies)
    # G4r (docstring, 2026-09-29): stripped by the target's death OR the round's end
    s["g4_rows"] = [(a["capture"], a["port"], a["t"], a["skill"], a["removal_at"], a["end_why"])
                    for a in happlies]
    s["g4_off"] = [x for x, a in zip(s["g4_rows"], happlies)
                   if not (a["stripped"] or (a["residual"] is not None and abs(a["residual"]) <= REMOVAL_TOL))]
    s["g4r_off"] = [x for x, a in zip(s["g4_rows"], happlies) if a["end_why"] in ("early", "none")]
    s["g4r"] = len(happlies) >= 1 and not s["g4r_off"]
    hdone_c = [r for r in hcasts if r["tc"] is not None]                              # corpus
    hdone = [r for r in hdone_c if r["capture"] in L1_WITNESSES]                      # witnesses
    s["l_adds_corpus"] = {f"{k[0]} {list(k[1])}": n for k, n in sorted(collections.Counter(
        (r["skill"], tuple(r["adds"])) for r in hdone_c).items())}
    adds = collections.Counter((r["skill"], tuple(r["adds"])) for r in hdone)
    s["l_adds"] = {f"{k[0]} {list(k[1])}": n for k, n in sorted(adds.items())}
    ended = [r for r in hdone if r["end_dt"] is not None]
    s["l_ended"] = dict(collections.Counter(r["skill"] for r in ended))
    s["l_end_ranges"] = {sk: (min(r["end_dt"] for r in ended if r["skill"] == sk),
                              max(r["end_dt"] for r in ended if r["skill"] == sk))
                         for sk in sorted({r["skill"] for r in ended})}

    def _all(sk, pred):
        rows = [r for r in hdone if r["skill"] == sk]
        return bool(rows) and all(pred(r) for r in rows)
    emp = [r for r in hdone if r["skill"] == EMPATHY]
    tp_ = [r for r in hdone if r["skill"] == TEINAIS_PRISON]
    s["l1"] = (_all(INCENDIARY, lambda r: r["adds"] == [1, 12])
               and bool(tp_) and all(r["adds"] in ([1, 12], [12]) for r in tp_)
               and sum(1 for r in tp_ if r["adds"] == [12]) <= 1
               and _all(EMPATHY, lambda r: r["adds"] == [1, 4])
               and _all(LIGHTNING_STRIKE, lambda r: r["adds"] == []
                        and not any(w & HEX_BIT for w in r["status_at_apply"]))
               and all(w & HEX_BIT for r in hdone if r["skill"] != LIGHTNING_STRIKE
                       for w in r["status_at_apply"][-1:]))
    s["l_order"] = dict(collections.Counter(
        (sk, "ascending" if asc else "NOT ascending", "target first" if tf else "target not first")
        for sk, _p, _t, _tg, _seq, asc, tf in order))
    s["l_order"] = {f"{k[0]} {k[1]}, {k[2]}": n for k, n in sorted(s["l_order"].items())}
    s["l_not_ascending"] = [(sk, p, t, tg, seq) for sk, p, t, tg, seq, asc, _tf in order if not asc]
    s["l2"] = (sum(1 for x in order if x[5]) >= 23 and len(s["l_not_ascending"]) <= 2
               and all(len(seq) > len(set(seq)) for _s, _p, _t, _tg, seq in s["l_not_ascending"]))
    s["l_ascending"] = sum(1 for x in order if x[5])       # 24 of 25 on the witness (EV-12)
    tp = [r for r in hdone if r["skill"] == TEINAIS_PRISON]
    s["l_snare"] = [(r["speed_at_apply"], r["speed_at_end"],
                     [hex(w) for w in r["status_at_apply"]], [hex(w) for w in r["status_at_end"]])
                    for r in tp]
    snared = round(SNARE_BASE * SNARE_FACTOR, 2)
    s["l3"] = (len(tp) >= 6 and all(
        r["speed_at_apply"] == [snared] and r["speed_at_end"] == [SNARE_BASE]
        and r["status_at_apply"] and (r["status_at_apply"][-1] & (HEX_BIT | SNARE_BIT)) == (HEX_BIT | SNARE_BIT)
        and r["status_at_end"] and not (r["status_at_end"][-1] & SNARE_BIT)
        for r in tp))

    # ---- conditions
    s["c_applies"] = dict(collections.Counter(x["name"] for x in conds))
    s["c_total_42"], s["c_total_44"] = len(every42), sum(len(cc.removes) for cc in conns)
    dz = [x for x in conds if x["skill"] == DAZED]
    ca = [x for x in conds if x["skill"] == CRACKED_ARMOR]
    s["c_dazed"] = [(x["capture"], x["port"], x["target"], x["field3"], x["dur"]) for x in dz]
    s["c_cracked"] = [(x["capture"], x["port"], x["target"], x["field3"], x["dur"]) for x in ca]
    s["c1"] = (len(dz) >= 1 and len(ca) >= 2
               and not any(x["cast_applied"] for x in dz + ca)
               and all(x["field3"] == 0 for x in dz + ca))
    bb_ = [x for x in conds if x["skill"] in (BURNING, BLEEDING)]
    s["c_burn_bleed"] = [(x["name"], x["field3"], x["dur"], x["cast_applied"], x["residual"]) for x in bb_]
    s["c2"] = bool(bb_) and all(x["field3"] == round(x["dur"]) for x in bb_)
    cast_applied = [x for x in conds if x["skill_applied"]]
    environmental = [x for x in conds if not x["skill_applied"]]
    s["c_cast_applied"] = len(cast_applied)
    s["c_environmental"] = len(environmental)
    s["c_cast_applied_off"] = [(x["name"], x["field3"], x["dur"]) for x in cast_applied
                               if x["field3"] != round(x["dur"])]
    s["c_environmental_off"] = [(x["name"], x["field3"], x["dur"]) for x in environmental
                                if x["field3"] != 0]
    s["c2c"] = (len(cast_applied) >= 20 and not s["c_cast_applied_off"]
                and len(environmental) >= 30 and not s["c_environmental_off"])
    ids = collections.defaultdict(collections.Counter)
    for x in conds:
        if x["on_observer"]:
            for i in x["effect_ids"]:
                ids[x["name"]][i] += 1
    s["c_effect_ids"] = {k: dict(v) for k, v in sorted(ids.items())}       # corpus: a floor
    wids = collections.defaultdict(collections.Counter)
    for x in conds:
        if x["on_observer"] and x["capture"] == EXPECT_CAPTURE:
            for i in x["effect_ids"]:
                wids[x["name"]][i] += 1
    s["c_effect_ids_witness"] = {k: dict(v) for k, v in sorted(wids.items())}   # exact
    # an observer condition with NO [6] id in its batch at all (Mind Burn's two Burnings
    # on the observer, 20260817T231139) -- counted, so the ids above are not read as n/n
    s["c_observer_no_id"] = dict(collections.Counter(               # the witness tape: exact
        x["name"] for x in conds if x["on_observer"] and not x["effect_ids"]
        and x["capture"] == EXPECT_CAPTURE))
    s["c_observer_no_id_corpus"] = dict(collections.Counter(        # corpus: a floor
        x["name"] for x in conds if x["on_observer"] and not x["effect_ids"]))
    s["l4"] = (ids["Burning"].get(BURNING_EFFECT_ID, 0) >= 1
               and ids["Dazed"].get(DAZED_EFFECT_ID, 0) >= 1
               and ids["Cracked Armor"].get(CRACKED_EFFECT_ID, 0) >= 1)
    return s


REGISTERED = ("i1", "i2", "i3", "i4", "i5", "i6", "m1", "m2", "m3", "m4",
              "g1", "g2", "g3", "g4", "c1", "c2")
FAILED_AS_REGISTERED = ("i4", "m2", "c2")
UNTESTABLE = ("m3",)
CORRECTED = ("i4c", "m2c", "m3c", "c2c")
LOCKED_LATER = ("l1", "l2", "l3", "l4")
# THE ZAISHEN CAPTURE (2026-09-28, docstring): the registered predictions it FAILS, and the
# re-statement (no free parameter) each one's verdict rests on beside it. The corrected C2c
# has none -- it stands FAILED on that tape, its witness exact in test_skilldamage. G3 had none
# until 2026-09-28 (the regenerate-from-38888 arc): G3r, the client's own rounded scaler on the
# tape's OWN build's row, is its re-statement (docstring), and G3 as registered stays FAILED.
FAILED_ON_ZAISHEN = ("i1", "i2", "i3", "m1", "g2", "g3")
# THE SECOND ZAISHEN CAPTURE (2026-09-29, docstring): G4 as registered fails on the round's
# end; G4r is its re-statement (the death OR the round's end strips)
FAILED_ON_ZAISHEN2 = ("g4",)
RESTATED = {"i1": "i1r", "i2": "i2r", "i3": "i3r", "m1": "m1r", "g2": "g2r", "g3": "g3r",
            "g4": "g4r"}
CORRECTED_FAILED_ON_ZAISHEN = ("c2c",)


def verdicts(s):
    """The reader's own verdict: every prediction holds as registered except the three
    that FAILED (their corrected readings hold), M3 is untestable (its M3c holds), and
    the four post-hoc facts hold."""
    return {
        "registered_hold": all(s[k] for k in REGISTERED if k not in FAILED_AS_REGISTERED + UNTESTABLE),
        "failed_as_registered": all(not s[k] for k in FAILED_AS_REGISTERED),
        "corrected_hold": all(s[k] for k in CORRECTED),
        "later_hold": all(s[k] for k in LOCKED_LATER),
    }


def restated_verdicts(s):
    """The whole corpus's verdict since the Zaishen capture: every registered prediction
    holds as registered or through its re-statement, except the three FAILED at
    registration (I4 / M2 / C2) -- G3 included since 2026-09-28, through G3r, and G4
    since 2026-09-29, through G4r; M3 untestable; the corrected readings but C2c hold;
    the post-hoc facts hold."""
    skip = FAILED_AS_REGISTERED + UNTESTABLE
    return {
        "registered_or_restated_hold": all(s[k] or (k in RESTATED and s[RESTATED[k]])
                                           for k in REGISTERED if k not in skip),
        "restatements_hold": all(s[v] for v in RESTATED.values()),
        "failed_as_registered": all(not s[k] for k in FAILED_AS_REGISTERED),
        "corrected_hold": all(s[k] for k in CORRECTED if k not in CORRECTED_FAILED_ON_ZAISHEN),
        "later_hold": all(s[k] for k in LOCKED_LATER),
    }


def _say(text):
    try:
        print(text)
    except UnicodeEncodeError:
        enc = sys.stdout.encoding or "ascii"
        print(text.encode(enc, "backslashreplace").decode(enc, "replace"))


def _v(ok):
    return "PASS" if ok else "FAIL"


def print_rows(c):
    n = 0
    for r in incendiary_rows(c["conns"]) + mind_burn_rows(c["conns"]):
        n += 1
        print(f"\n#{n} skill {r['skill']} {r['capture']} {r['port']} observer={r['observer']} "
              f"caster={r['caster']} -> target={r['target']} announce t={r['ta']:.3f} "
              f"completion +{r['dt']} stopped={r['stop']}")
        if r["tc"] is None:
            continue
        print(f"   tokens {' '.join(r['tokens'])}")
        if r["skill"] == INCENDIARY:
            print(f"   adds={r['adds']} end=+{r['end_dt']} why={r['end_why']} payoff={r['payoff']} "
                  f"burning={r['payoff_burning']} hex42={r['hex_apply']}")
        else:
            print(f"   words={r['words']} signals={r['foe_signal']} order={r['order']}")
        print("   completion batch, wire order:")
        for off, s_ in r["batch"]:
            _say(f"       {off:+.3f} {s_}")
        if r.get("end_batch"):
            print("   end batch, wire order:")
            for off, s_ in r["end_batch"]:
                _say(f"       {off:+.3f} {s_}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--rows", action="store_true", help="one block per 179 / 185 cast")
    ap.add_argument("--stamp", action="append", default=None, help="only this capture (repeatable)")
    a = ap.parse_args()
    c = census(stamps=a.stamp)
    s = score(c)
    v = verdicts(s)
    if a.json:
        print(json.dumps({"score": s, "verdicts": v, "refused": c["refused"]}, indent=1, default=str))
        return 0
    print(f"hexjoin: {s['captures']} live captures, {s['connections']} connections framed whole, "
          f"{s['refused']} refused; the observer named on {s['observer_named']}")
    for r in c["refused"]:
        print(f"   refused {r}")
    print(f"   set aside by their capture's own manifest (gapped, still refused): "
          f"{c['set_aside'] or 'none'}; declared but decoding whole: "
          f"{c['declared_not_refused'] or 'none'}")
    if a.rows:
        print_rows(c)
        print()
    print("---- 179 Incendiary Bonds")
    print(f"[{_v(s['i1'])}] I1 announces on {EXPECT_CAPTURE} per port {s['i_per_port']} (registered "
          f"AFTER the first run, from its output: {EXPECT_179_PER_PORT}), corpus {s['i_announces_corpus']} "
          f"(a floor), forms {s['i_forms']}, by the observer {s['i_by_observer']}; completed "
          f"{s['i_completed']} on the witness / {s['i_completed_corpus']} corpus at +{s['i_dt']}; "
          f"stopped {s['i_stopped']}")
    print(f"[{_v(s['i2'])}] I2 [20, T, 348] in {s['i_fx20_348']}/{s['i_completed']} completion batches; "
          f"damage words on the target there {s['i_words_on_target']}")
    print(f"[{_v(s['i3'])}] I3 the hex's 0x0042 on the observer: {s['i_hex_applies']} (n = "
          f"{len(s['i_hex_applies'])}; f32 3.0, 58 < 0x0042 < 0x00F1, 0x800 set)")
    print(f"[{_v(s['i4'])}] I4 AS REGISTERED (the payoff at +3.0 on every cast whose target lived): "
          f"{s['i_ends']} hexes traced [6] -> [7]; scheduled {s['i_scheduled']} at "
          f"{s['i_scheduled_range']} ({s['i_scheduled_with_words']} with words); REMOVED "
          f"{len(s['i_removed'])} (port, t, end, words) {s['i_removed']}; the target died "
          f"{s['i_target_died']}; the caster died {s['i_caster_died']}; unexplained early "
          f"{s['i_unexplained_early']}")
    print(f"[{_v(s['i4c'])}] I4c the corrected reading: a removal fires nothing ({len(s['i_removed'])}/"
          f"{len(s['i_removed'])}), the target's death fires early on the foes standing "
          f"({sum(1 for x in s['i_target_died'] if x[3])}/{len(s['i_target_died'])}), no payoff batch "
          f"carries a 58 of 179 ({s['i_payoff_58_of_179']}); MIXED instants (the caster's OTHER "
          f"skill completing there, its 58 / [20]) {s['i_payoff_mixed']}; ends whose only word is "
          f"the caster's periodic TICK, not a payoff (port, t, end, foe: values) {s['i_payoff_tick']}")
    print(f"[{_v(s['i5'])}] I5 takers per payoff {s['i_takers_hist']}, not a foe {s['i_takers_not_foe']}; "
          f"the target among them {s['i_target_struck']}/{s['i_target_struck_of']} (alive); Burning on the "
          f"takers {s['i_payoff_burning']}")
    print(f"[{_v(s['i6'])}] I6 the observer struck {s['i_observer_struck']} (0x00CF -> [10, obs, 179] -> "
          f"word {s['i_observer_prefix_ok']}); its Burning (field3, f32, removed after) "
          f"{s['i_observer_burning']}")
    print("---- 185 Mind Burn")
    print(f"[{_v(s['m1'])}] M1 announces per port {s['m_per_port']} (registered AFTER the first run: "
          f"{EXPECT_185_PER_PORT}), corpus {s['m_announces_corpus']} (a floor), by the observer "
          f"{s['m_by_observer']}; completed {s['m_completed']} on the witness / {s['m_completed_corpus']} "
          f"corpus at +{s['m_dt']}; stopped {s['m_stopped']}")
    print(f"[{_v(s['m2'])}] M2 AS REGISTERED (one comparison; a twin cast strikes the adjacent, a single "
          f"the target alone): [20, T, 331] {s['m_fx20_331']}/{s['m_completed']}; on the target twin "
          f"{s['m_twin']} (identical {s['m_twin_identical']}), single {s['m_single']}, none {s['m_none']}; "
          f"casts MIXING twins and singles across their foes {len(s['m_mixed'])}: {s['m_mixed']}")
    print(f"[{_v(s['m2c'])}] M2c per FOE: the target single while an adjacent foe is twin "
          f"{s['m_target_single_adjacent_twin']}; per (words, Burning signal, who) {s['m_foe_signal']}; "
          f"twins with no Burning signal {s['m_twin_no_burning']}, singles with a NEW one "
          f"{s['m_single_with_burning']} (an 'already' on a single is no evidence either way)")
    print(f"[----] M3 UNTESTABLE as registered: Mind Burn casts onto the observer {s['m_onto_observer']}")
    print(f"[{_v(s['m3c'])}] M3c the observer struck as an ADJACENT foe: Burning (field3, f32, removed "
          f"after) {s['m_observer_burning']} -- an integer in 1..10, field3 == f32; the 179 hex's field3 "
          f"{sorted({h['field3'] for h in s['i_hex_applies']})} predicts 3 and 9: {s['m_rank_fits']}")
    print(f"[{_v(s['m4'])}] M4 (first clause) no caster is the observer, so the caster's energy is never "
          f"on the wire: the comparison is not decided")
    print(f"[----] M4 (second clause) UNTESTABLE as registered: 'on a cast onto the observer the "
          f"observer's energy IS on the wire, so a twin gives a bound' -- casts onto the observer "
          f"{s['m_onto_observer']}, and the observer's CURRENT energy is never on the wire (41 / 43 / 62 "
          f"are); no bound can be taken")
    print("---- every hex")
    print(f"[{_v(s['g1'])}] G1 hex 0x0042s {s['h_42_per_skill']}: on the observer {s['h_42_on_observer']}, "
          f"elsewhere {s['h_42_elsewhere']}; ALL 0x0042 {s['all_42']}: on the observer "
          f"{s['all_42_on_observer']}, elsewhere {s['all_42_elsewhere']}")
    print(f"[{_v(s['g2'])}] G2 58 < 0x0042 < 0x00F1 on every hex apply (n = {len(s['h_residuals'])})")
    print(f"[{_v(s['g3'])}] G3 f32 == interp(d0, d15, field3), unrounded as registered, on the tape's "
          f"own build's row: misses {s['g3_misses']}")
    print(f"[{_v(s['g4'])}] G4 removal residuals (skill, s) {s['h_residuals']}")
    print(f"[{_v(s['l1'])}] L1 type-4 announces {s['h_announces']} at {s['h_where']}; [6, T, ids] at the "
          f"landing {s['l_adds']}; ended {s['l_ended']} at {s['l_end_ranges']}")
    print(f"[{_v(s['l2'])}] L2 multi-foe batches (the witness tape) {s['l_order']}: {s['l_ascending']} of "
          f"{len(s['l_not_ascending']) + s['l_ascending']} ascending; not ascending {s['l_not_ascending']} "
          f"(each a repeated agent: two groups in one window)")
    print(f"[{_v(s['l3'])}] L3 Teinai's Prison (speed at apply, at end, status at apply, at end) {s['l_snare']}")
    print("---- conditions")
    print(f"[{_v(s['c1'])}] C1 0x0042 {s['c_total_42']} / 0x0044 {s['c_total_44']} corpus-wide; conditions "
          f"{s['c_applies']}; Dazed {s['c_dazed']}; Cracked Armor {s['c_cracked']} (no 58 in the batch, "
          f"field3 0; the 'all on Isle connections' clause is UNSCORED -- the map id is not read here, "
          f"the stamps are the Isle's by the vault's filing)")
    print(f"[{_v(s['c2'])}] C2 AS REGISTERED (Burning and Bleeding: field3 == f32): "
          f"(name, field3, f32, cast-applied, residual) {s['c_burn_bleed']}")
    print(f"[{_v(s['c2c'])}] C2c skill-applied conditions (a [10, me, skill], or a 58 whose announce named me) "
          f"{s['c_cast_applied']}, field3 != f32 on {s['c_cast_applied_off']}; environmental "
          f"{s['c_environmental']}, field3 != 0 on {s['c_environmental_off']}")
    print(f"[{_v(s['l4'])}] L4 [6] ids beside the observer's condition 0x0042s {s['c_effect_ids']} "
          f"(the witness tape's: {s['c_effect_ids_witness']}; observer conditions carrying NO [6] id "
          f"{s['c_observer_no_id']} on the witness tape -- Mind Burn's twin Burning on the observer "
          f"sends none, 2/2 -- and {s['c_observer_no_id_corpus']} corpus-wide); NOTE "
          f"id 29 is shared by Weakness and Cracked Armor -- a class, not a per-condition id (the D6 "
          f"review's R34-8)")
    print("---- RE-STATED for the Zaishen capture (docstring; no free parameter)")
    print(f"[{_v(s['i1r'])}] I1r / [{_v(s['m1r'])}] M1r the completion at the [61] seconds when sent: "
          f"179 {s['i_ct_casts']} off {s['i1r_off']}; 185 {s['m_ct_casts']} off {s['m1r_off']}")
    print(f"[{_v(s['i2r'])}] I2r a word on the target only on the caster's own Fire Storm tick: "
          f"{s['i_words_on_target_tick']}")
    print(f"[{_v(s['i3r'])}] I3r / [{_v(s['g2r'])}] G2r no 0x00F1 when already hexed: 179 "
          f"{s['i_hex_already']}; every hex {s['g2_already_hexed']}")
    print(f"[{_v(s['g3r'])}] G3r f32 == the client's ROUNDED scaler on the tape's own build's row: "
          f"G3's misses {s['g3_miss_rows']}, G3r's {s['g3r_miss_rows']}")
    print(f"[{_v(s['g4r'])}] G4r the removal at + f32 unless the target's death or the round's end "
          f"(0x0181) strips it: G4's misses {s['g4_off']}, G4r's {s['g4r_off']}; every hex apply "
          f"(capture, port, t, skill, removal at, why) {s['g4_rows']}")
    print(f"[----] C2c off (no re-statement) "
          f"{s['c_cast_applied_off']} / {s['c_environmental_off']}; the 179 hexes' ranks "
          f"corpus-wide {s['m_ranks_corpus']}")
    rv = restated_verdicts(s)
    print(f"hexjoin (whole corpus, re-stated): {rv}")
    ok = all(v.values())
    print(f"hexjoin: {'THE READING HOLDS' if ok else 'THE READING FAILS'} -- registered "
          f"{_v(v['registered_hold'])}, I4/M2/C2 failed as registered {_v(v['failed_as_registered'])}, "
          f"corrected {_v(v['corrected_hold'])}, post-hoc {_v(v['later_hold'])}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
