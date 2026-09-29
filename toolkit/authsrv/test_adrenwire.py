"""The adrenaline wire model, pinned against ArenaNet's own bytes.

FOUR OPCODES CARRY ADRENALINE, and until 2026-08-21 this repo said none did.
`pools.py`'s header read "ADRENALINE IS NOT ON THE WIRE AT ALL, and that is a
finding rather than a gap", and `authsrv.py` repeated it. That was a FLOOR --
nobody had looked -- read as a CEILING, which is the same error shape CLAUDE.md
records for the provenance gate and for `asserts.py`'s own site counts. The
family is:

    207 = 0x00CF  {agent, units}                       10 bytes  THE CHARGE
    208 = 0x00D0  {agent}                               6 bytes  CLEAR ALL
    209 = 0x00D1  {agent, skill_id, skill_copy, units} 16 bytes  ABSOLUTE SET
    210 = 0x00D2  {agent, skill_id, skill_copy}        12 bytes  THE SPEND

THE NAMES ARE OURS. No upstream carries any of them -- searched and NOT FOUND in
maintained GWCA (`gwdevhub__GWToolboxpp/Dependencies/GWCA Opcodes.h`), OpenTyria,
Headquarter, GWLP-R, Py4GW_Reforged and gw-preservation -- so no derivation
register row is owed, and no upstream can corroborate them either. What can, and
does, is the client and the corpus, which is the whole design of this file.

WHY THIS TEST EXISTS RATHER THAN A STUDY DOC. Every number below was derived by
static disassembly of one pinned build and measured on one 14-capture corpus.
Both of those are outside the repo, both can move, and a derivation that lives
only in prose drifts silently: the FIRST draft of this finding claimed retail
broadcasts 207 for other agents' bars, and §5 is the check that refuted it. So
each load-bearing byte and each load-bearing count is an assertion here, and a
later session that changes the model has to change a red test rather than a
paragraph.

WHAT EACH SECTION CAN REFUTE, because a check our own decoder forces true is not
a check:

  §3  THE COST COLUMN IS NOT QUANTISED IN STRIKES. If the bar were "N strikes",
      every adrenaline cost would be a multiple of 25. Seven distinct costs in
      ArenaNet's own column are not. This is the measurement behind `pools.py`
      modelling raw units, and its control is that some costs ARE multiples.
  §4  THE CENSUS, with 209 as a live handler retail never uses -- 0 of 114,985,
      the same shape as energy property 33 in `test_pools` §2a -- and its three
      neighbours as the positive control that makes the zero mean something.
  §5  SELF-SCOPE, refuting the first draft. Every connection carrying 207 names
      exactly ONE agent, and it is that connection's own SKILLBAR_UPDATE agent.
      The control is that those SAME connections carry 9 to 24 distinct agents
      on the property channel, so "one agent" is a property of opcode 207 and
      not of the capture.
  §6  THE SPEND JOIN: retail only ever spends adrenaline on adrenal skills. The
      control is that the same lookup over everything the corpus shows being
      CAST finds 753 casts of 50 skills with a ZERO adrenaline cost, so the join
      discriminates rather than agreeing with whatever it is handed.
  §7  THE ORDER, which the server build needs and the corpus answers: the spend
      leads its own activation by exactly one message, 39 of 39.
  §8  THE DISPATCH CHAIN, walked as ARITHMETIC on relative displacements. Four
      descriptors at a 12-byte stride whose type arrays declare 0xCF..0xD2 in
      order; each one's handler is a stub whose rel32 lands on a thunk whose
      rel32 lands on the worker this file names. Nothing here is a hardcoded
      answer compared with itself: a wrong address produces a wrong sum.
  §9  THE WORKERS, including the identity `4 + 8 * 0x14 == 0xA4` that the charge
      loop's own three constants have to satisfy.
  §10 THE DISPLAY, and it is the CORRECTION this build owes. The icon draws from
      the slot's SECOND dword (+0x04), not the first. PLAN.md said +0x00.
  §11 ARENANET'S OWN WORDS, four assert sites, each cited singly as the evidence
      for one claim -- CLAUDE.md's own boundary for a measurement.
  §12 THE BAR GATE, which is the sharpest refutable claim in this file: split
      the corpus on whether the observer's bar carries ANY adrenal skill and
      the whole family lands on one side of the split -- 918/27/40 in the
      armed connections, 0/0/0 in the dark ones. Its control is that the dark
      connections are NOT quiet: 45 landed weapon hits and 13 completed melee
      attacks, every one of which GWW's own rule says earns 25 units. It also
      re-fits round() on the armed rows alone (32 of 32) and checks the eleven
      percentages against a denominator it never fitted -- the observer's own
      maximum health, read off a different property.
  §13 THE REPAINT GATE, from the bytes, which is why nobody noticed §12 from
      the screen: the charge worker clears EDI before its slot loop, sets it
      only where a slot is actually written, and `test edi,edi` / `je` at
      0x008219F8 jumps past the UI event. A 207 no slot accepted repaints
      nothing and arms no timer.
  §3b (CASTAI-Z2, 2026-09-29) THE SIGNATURE'S FOURTH KIND, made to refuse on
      synthetic batches: a gain with no word, after the killing word, in the
      agent's death batch is `post_mortem` (retail sends the gain and drops the
      word for a hit landing on an agent already dead in the tick -- 2 of 2 on
      the Smiting Monks' tape); drop either term and it is `unexplained` again.

Sections 1-3 need no captures and no client; 4-7 and 12 need
`vault/captures/live/`; 8-11 and 13 need the pinned build-38797 image. The last two groups declare skips, the
first does not, which is `test_pools`' split: the content overlay regenerates
from the owner's install and a machine without it should go RED.

READ-ONLY throughout. The client image is opened, never launched and never
written. Python 3 standard library only.

    python toolkit/authsrv/test_adrenwire.py
"""
import collections
import json
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLKIT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, TOOLKIT)
sys.path.insert(0, os.path.join(TOOLKIT, "schema"))
sys.path.insert(0, os.path.join(TOOLKIT, "clientscan"))
import checks  # noqa: E402

# FLOOR 10, and it is the MANDATORY CORE rather than the full count, which is
# `checks.py`'s own instruction for a test whose count varies with the fixture.
# BOTH NUMBERS ARE FROM RUNS ACTUALLY PERFORMED on 2026-08-21, neither is a
# guess and neither is above what a run produces: a full green run on this
# machine executes 72 (55 until 12-13 landed; 91 since CASTAI-Z1, 2026-09-28;
# 95 since CASTAI-Z2, 2026-09-29: +3 for 3b's synthetic arms, +1 for the
# Smiting Monks' tape pinned whole -- measured 95 on the green run),
# and a run with neither the
# captures nor the pinned image
# executes 10 -- forced by pointing `RURIK_VAULT` at an empty directory, which
# also turns §3 RED (3 failures, not a skip) because the content overlay is NOT
# in the skippable half. That is `test_pools`' split and the reason for it: the
# overlay regenerates from the owner's own install via
# `skilltable.py --emit-content`, so a machine without it should go red rather
# than quietly check the schema and stop.
#
# THE CAPTURES ARE SKIPPABLE because they are not regenerable at all -- six live
# sessions against ArenaNet plus eight loopback-era ones, and no procedure in
# RUNBOOK.md recreates a particular one. THE PINNED IMAGE is skippable for the
# same reason `pinned.find()` raises rather than falling through to `C:\gw`.
#
# WHAT THIS FLOOR DOES NOT CATCH, said plainly because 10 of 91 is a weak
# backstop and a reader should not over-read it: on a machine that HAS both
# fixtures, one section quietly ceasing to run would still clear 10. The guards
# against that are elsewhere and are deliberate -- §4's first check pins the
# capture, connection and message counts, so a corpus walk that visited less
# goes red instead of silent, and §8 prints the image it read and then makes
# four assertions about it. The floor's job here is the fixture-less run.
LEDGER = checks.Ledger("the adrenaline wire model", floor=10)

# ---------------------------------------------------------------------------
# THE FAMILY. Ours: NOT FOUND in GWCA, OpenTyria, Headquarter, GWLP-R,
# Py4GW_Reforged or gw-preservation, all searched 2026-08-21. Spelled without a
# GAME_SMSG_ prefix to match `agents.py`'s own vocabulary for this channel.
SMSG_ADRENALINE_CHARGE = 0x00CF     # 207
SMSG_ADRENALINE_CLEAR  = 0x00D0     # 208
SMSG_ADRENALINE_SET    = 0x00D1     # 209
SMSG_ADRENALINE_SPEND  = 0x00D2     # 210
FAMILY = (SMSG_ADRENALINE_CHARGE, SMSG_ADRENALINE_CLEAR,
          SMSG_ADRENALINE_SET, SMSG_ADRENALINE_SPEND)

SMSG_SKILLBAR_UPDATE = 218          # the connection's own bar -- §5's join key
SMSG_AGENT_UPDATE_FLAGS = 0x0026    # [agent, flags]; 4 is the agent's death
                                    # (adrenjoin.PLAYER_DEAD_FLAG) -- 4b's
                                    # post-mortem term (CASTAI-Z2)

# The four generic-property opcodes, prop id FIRST in every one. Same constants
# as `test_pools.py`, restated rather than imported so this file depends on no
# server module: it is an ORACLE over outside inputs, and a shared constant is
# one more thing that can drift into agreement with itself.
INT_OPS = (0x009F, 0x00A0)
FLOAT_OPS = (0x00A2, 0x00A3)
CAST_PROPS = {48, 50, 60}           # instant, attack-skill, skill activated
PROP_ATTACK_SKILL_ACTIVATED = 50    # the one §7 finds behind every spend

# MEASURED 2026-08-21 over all capture directories under vault/captures/live.
# 20260817T175358 has no wire.jsonl and contributes zero connections, which is
# correct and is why the capture count and the connection count are pinned
# separately.
#
# RE-PINNED THE SAME DAY, 14 captures -> 20, when the campaign's own live runs
# landed. Everything scaled the way a bigger corpus should and nothing changed
# shape: 209 is STILL zero (its "nothing on retail" reading now rests on 143,408
# messages rather than 114,985), and the sub-25 tail did NOT move at all -- all
# 255 new gains carry exactly 25, so they are landed weapon hits and not damage
# taken. That last fact is worth stating because a live plan explicitly asked for
# light hits TAKEN, to put a sample under 1% of maximum health and settle the
# rounding boundary `pools.damage_units` extrapolates. None arrived; the boundary
# is still extrapolated.
#
# RE-PINNED AGAIN 2026-08-27 -- 20 captures -> 21 -- AND THAT IS THE SECOND TIME,
# which is the tell that the SHAPE was wrong rather than the numbers. These were
# equalities, so this file went RED on `main` on evidence that CONFIRMS every
# claim it makes: the corpus grew, 207 went 918 -> 921, 208 went 27 -> 28, the
# 25s went 886 -> 889, and the reading did not move an inch. An equality here was
# pinning THE SIZE OF THE VAULT, which nothing in this file measures.
#
# They are FLOORS now, and the floor is what the original comment actually asked
# for: "A corpus that shrank is a vault that moved, and every count below would
# quietly get easier." A shrink is the defect; growth is the instrument working.
# The claims that are NOT counts stay exact -- 209 is still zero, no 207 exceeds
# 25, the sub-25 tail is still the same multiset, and the armed side still
# carries the whole family -- and those are what this file is for.
CORPUS_CAPTURES = 20
CORPUS_CONNECTIONS = 59
CORPUS_MESSAGES = 143408
# Floors, not a census. SET stays EXACT because zero is the claim.
#
# READ THIS BEFORE USING `CENSUS[...]` AS AN EXPECTED VALUE. These became FLOORS
# on 2026-08-27 and two sites three hundred lines away were still comparing a
# LIVE count to them for equality (§6's `spend_copies`, §7's activation join) --
# the same constant meaning two things, green only because the corpus had not
# grown since the morning. Both now read `agg["census"][...]`, the measured
# number. If you need "all N of them", take N from the measurement.
CENSUS = {SMSG_ADRENALINE_CHARGE: 1028, SMSG_ADRENALINE_CLEAR: 37,
          SMSG_ADRENALINE_SET: 0, SMSG_ADRENALINE_SPEND: 59}   # JARIN: +107 / +10 / +19, the hero's

# THE TWO EXACT CORPUS CLAIMS THAT ARE DELIBERATE, so the next session does not
# quietly re-pin them. Both were confirmed size-sensitive on 2026-08-27 by
# doubling the corpus, and both are being LEFT that way on purpose:
#   - §4b's `tail == SUB_STRIKE`. The sub-25 multiset has survived two corpus
#     growths unchanged. A new value in it is a FINDING about the 1%-of-health
#     rule, not a re-baselining chore.
#   - §13's `len(band) == 1`, the near miss. A second row in the round/ceil
#     disagreement band is the single observation that would SETTLE the
#     boundary. Reddening is the point.
# When either goes red, investigate the new row. Do not widen the constant.
#   2026-09-29 (CASTAI-Z2): the second went red and was not widened -- 24
#   armed rows in the band on 20260929T100038, investigated at NEAR_MISS_BITS
#   below and pinned on their own tape.

# 207's amount, split into the two populations §4b is about. A STRIKE is 25 --
# GWW ("Adrenaline", rev. 2026-07-02) gives one per successful weapon hit -- and
# the sub-25 tail is INFERRED to be GWW's other rule, one unit per 1% of maximum
# health lost, floored. NOTHING JOINS THE TAIL TO HEALTH TRAFFIC YET, so the 25s
# are OBSERVED as a value and the reading of the tail is not a measurement.
STRIKE_UNITS = 25
STRIKE_COUNT = 957      # JARIN: +71, the hero's landed hits
SUB_STRIKE = {2: 8, 3: 9, 4: 29, 5: 2, 6: 5, 7: 1, 8: 3, 11: 4, 12: 1, 13: 1,
              15: 2, 19: 2, 21: 1}   # JARIN: the hero's hits taken (2 per skale bite at 140)
# JARIN: THREE 207s ABOVE 25, all the hero's -- a landed hit and a hit taken
# in ONE tick, 25 + 1 / + 4 / + 17 (the caster's blow on a 140 pool). The
# ceiling reading ("25 is the largest single event") holds per EVENT and
# not per message; retail sums the tick.
OVER_STRIKE = {26: 1, 29: 1, 42: 1}
# REFUTED 2026-09-28 (CASTAI-Z1), the READING above, not the multiset: each of
# the three rides ONE damage word at the hero -- (units, % of its maximum):
JARIN_OVER_WORDS = [(26, 25.714), (29, 29.286), (42, 41.803)]

# THE TWO HITS-TAKEN TAPES, 2026-09-16/17, NAMED AND PINNED WHOLE. 4b's four
# claims were written over a corpus in which the owner mostly HIT things. These
# two are Isle of the Nameless calibration runs built the other way round -- a
# character carrying adrenal skills, standing still to be hit -- and between
# them they reddened all four on the same morning. Re-scanned as of
# the pin (every stamp before 20260916T213125) 4b is green to the digit, so the
# corpus did not drift; these tapes SAY something, and what they say is below
# and in studies/skills 53. Each tape's multiset is pinned EXACTLY, because a
# tape does not grow; the rest of the corpus keeps the claims it had.
#
#   20260916T213125  RUN-SKILLS-RB (skills 48): Blind, Reversal of Fortune.
#     SEVEN ZEROS. Each is a hit Reversal of Fortune converted to nothing: the
#     damage word is +0.0 and the gain that precedes it carries 0. So "none
#     carries 0 ... a zero would be a message with no effect" was wrong about
#     retail: the 207 rides EVERY damage word to an adrenal bar and carries
#     round(pct), which for nothing is nothing. The 1s are 1.04 % and 1.25 %
#     hits -- the rows that kill ceil (section 12).
#   20260917T090355  RUN-SKILLS-RB2 (skills 50): armour stripped, three deaths.
#     NOT ONE 25 -- the owner never swung -- and SIX ABOVE 25: 30 x3, 34, 60
#     and 70. "25 is a CEILING on one message" was a fact about strikes that
#     4b had stretched over the whole opcode. A 60 is ONE Lightning Orb for
#     286 of 480; the 70 is the same 286 against a maximum three deaths had
#     taken to 408. The damage rule has no cap at 25 and reads the CURRENT
#     maximum, both OBSERVED here for the first time.
DAMAGE_TAPES = {
    "20260916T213125": {0: 7, 1: 3, 2: 5, 4: 2, 5: 1, 6: 2, 7: 3, 8: 2, 9: 3,
                        10: 3, 12: 1, 14: 1, 15: 1, 22: 1, 25: 13},
    "20260917T090355": {2: 3, 3: 2, 6: 1, 10: 5, 13: 1, 15: 1, 18: 1, 21: 6,
                        30: 3, 34: 1, 60: 1, 70: 1},
}
ZERO_GRANT_TAPE = "20260916T213125"
ZERO_GRANTS = 7

# CASTAI-Z1 (2026-09-28): THE ZAISHEN TAPE, and why 4b's three shape claims are
# now scoped to the pin rather than named around it. 20260928T103123 is the
# Zaishen Challenge -- the owner's level-20 Warrior against four level-20 AI in
# an arena, fighting AND being hit -- and it moved all three: 43 sub-strike
# gains, five over 25 ({33: 4, 36: 1}) and one zero. Re-scanned AS OF THE PIN
# (every stamp before PIN_STAMP, the two DAMAGE_TAPES named out as before),
# SUB_STRIKE, OVER_STRIKE and "no zero" reproduce to the digit, so the scanner
# did not drift. What carries the claims past the pin is a SIGNATURE, not a
# third name: every 207 that is not a 25 is ONE damage word at its own agent in
# its own batch, carrying round(% of that agent's current maximum) --
# `_classify_gains`. Over the whole corpus that holds for every one of them
# (175 today), which also upgrades SUB_STRIKE's "INFERRED" to OBSERVED-joined,
# and REFUTES the JARIN reading of OVER_STRIKE: 26 / 29 / 42 are not "25 + 1 /
# + 4 / + 17 summed in one tick" -- each rides ONE damage word of 25.71 % /
# 29.29 % / 41.80 % of the hero's maximum (36/140, 41/140, 51/122). Nothing
# in the corpus is summed.
PIN_STAMP = "20260928T103123"
ZAISHEN_TAPE = "20260928T103123"
# The capture-declared gapped connections (livewire.declared_gaps), EXACT: a
# new one must redden this, never vanish from the corpus.
DECLARED_GAPPED = [("20260928T103123", "10.0.0.210:65009->98.95.137.136:80")]
# The tape's 207s, per connection, pinned WHOLE (a tape does not grow). The
# gapped match-2 connection is set aside above and so is absent here.
ZAISHEN_207 = {
    "10.0.0.210:50061->54.198.7.73:80":   # match 1, the Degeneration Team
        {0: 1, 3: 4, 4: 2, 6: 1, 7: 1, 8: 1, 15: 1, 16: 1, 25: 44},
    "10.0.0.210:50295->54.198.7.73:80":   # match 3, the Obsidian Spike Elementalists
        {3: 1, 5: 1, 6: 1, 7: 2, 8: 2, 21: 3, 25: 35, 33: 4, 36: 1},
    "10.0.0.210:58544->98.95.137.136:80":  # match 4, the Degeneration Team
        {1: 1, 2: 1, 3: 9, 4: 2, 10: 1, 12: 1, 14: 1, 25: 15},
}
# Its five over-25 gains: each ONE armour-ignoring property-55 word, 1.5 s after
# an Obsidian Flame (2809, the PvP split of 219) cast AT the observer --
# 33.125 % = 159 / 480 and 36.25 % = 174 / 480. And its zero: a +0.0 hit at
# t 131.453 on match 1 while the observer's Reversal of Fortune (307, applied
# t 129.025 for 8.0 s) was up -- RB's mechanism, a second tape.
ZAISHEN_OVER = [("10.0.0.210:50295->54.198.7.73:80", 47.206, 33),
                ("10.0.0.210:50295->54.198.7.73:80", 62.207, 33),
                ("10.0.0.210:50295->54.198.7.73:80", 71.007, 33),
                ("10.0.0.210:50295->54.198.7.73:80", 85.704, 36),
                ("10.0.0.210:50295->54.198.7.73:80", 91.706, 33)]
ZAISHEN_ZERO = [("10.0.0.210:50061->54.198.7.73:80", 131.453, 0)]
# Its 210s: every one is the PvP split 2858, and every one carries skill_copy
# 0xFFFFFFFF where all 59 spends before the pin carry 0 -- a value no ordinary
# spend has shown. What -1 MEANS is NOT FOUND; that it rides the PvP split is
# OBSERVED at n = 1 skill (11 spends, three connections).
ZAISHEN_SPEND_PAIRS = {(2858, 0xFFFFFFFF): 11}
# Its moved maximum: Deep Wound (482) lands at t 109.171 on match 1 and property
# 42 goes 480 -> 384 IN THE SAME BATCH (x 0.8); the five hits taken under it,
# as (maximum, points, units). RB's 384 rows before the pin are the same
# mechanism (482 at t 256.847 and 329.811 on 20260916T213125) -- a second tape.
ZAISHEN_MOVED = [(384, 12, 3), (384, 14, 4), (384, 16, 4), (384, 25, 7), (384, 59, 15)]
# The corpus floor for the signature: the non-strike gains it classified on the
# run that wrote it (all 175 as `damage`). A vacuity guard, not a size pin.
DAMAGE_RULE_GAINS = 175
# The spend skill content lacks, on the witness tape: the PvP split of 348.
PVP_SPENDS_WITNESS = {2858: 348}
# The CAST ids no rule resolves on the captures before the pin, EXACT (R8,
# CASTAI-Z1 review): an NPC's own skill, outside the player corpus. test_pools
# 2d pins the same set from its own walk.
UNRESOLVED_CASTS_AT_PIN = {1870}

# CASTAI-Z2 (2026-09-29): THE SMITING MONKS' TAPE, 20260929T100038 -- five
# Zaishen Challenge matches against four Monk AI (Balthazar's Aura 272,
# Zealot's Fire 271, Smite Hex 302, Scourge Healing 251 ...) beside the owner's
# axe Warrior, no capture gaps. It reddened four checks, and re-scanned AS OF
# ITS PIN (every stamp before Z2_PIN_STAMP) each reproduces to the digit:
#   - 4b's 10x dominance: 1219 at 25 against 106 below, before the pin. On the
#     tape itself the tail OUTNUMBERS the strikes, 229 to 123 -- the monks'
#     aura ticks, Zealot's Fire and 3-point wand hits charge the bar more often
#     than the axe lands -- so by 4b's own rule (a fact about how the owner
#     plays; a tape made to be hit is named out of the ratio) it is a
#     hits-taken tape: named, pinned whole per connection (Z2_207), and the
#     ratio is read as of the pin with the corpus and the tape REPORTED.
#   - THE SIGNATURE: two 207s the damage rule does not explain, both in the
#     observer's DEATH batch, both AFTER the killing word: 0x00CF [7, 6] at
#     t 50.751 on :51090 (monk 4's Balthazar's Aura visual 487 immediately
#     ahead of it; that monk's aura ticks on this observer are 27 of 480 =
#     5.625 % -> 6, 3 of 3 elsewhere on the connection -- OBSERVED) and
#     0x00CF [7, 16] at t 46.512 on :64557 (75 of 480 is a Smite Hex on this
#     tape; no visual names its source -- RECONSTRUCTION). A hit landing in
#     the tick the observer dies in, after the blow that killed, sends its
#     GAIN and NOT its damage word: 2 of 2, on the 2 of 13 armed deaths in the
#     corpus where a second hit landed in the death tick. The 13 killing words
#     themselves are all present, and UNCLAMPED (integrating the observer's
#     words from spawn: 59.58 % against 29.4 % remaining on RB2; 15.63 %
#     against 6.67 % on :51090). `_classify_gains` names the kind
#     `post_mortem` by that rule; a gain off it anywhere is `unexplained`.
#     OUR SERVER drops both the word and the gain for a hit on a dead player
#     (`player_dead` guards at the three grant sites) -- a wire-shape
#     divergence at the margin, ESCALATED, not edited here.
#   - 12's grant relation: 35 armed rows in 14 batches of UNEQUAL words (a
#     Zealot's Fire beside a Smite Hex from one monk; auras from two), which
#     adrenjoin refuses to attribute row by row. The relation holds as a
#     MULTISET per batch -- each word's round(pct) consumes a distinct gain of
#     the batch -- 14 of 14, and floor consumes 1 of 14 (:57580 t 54.715, a
#     5.392 % Zealot's Fire beside an 18.382 % Smite Hex, where floor and
#     round agree on both).
#   - THE NEAR MISS, FAILED AS WRITTEN (NEAR_MISS_BITS below): 24 armed rows
#     land in [0.5 %, 1.0 %) -- every one a 3-point wand hit on a 374..418
#     maximum -- and every one grants 1.
Z2_PIN_STAMP = "20260929T100038"
Z2_TAPE = "20260929T100038"
# 4b's dominance AS OF THE PIN: (at 25, below 25) over the corpus before
# Z2_PIN_STAMP without the two DAMAGE_TAPES. EXACT: that set of tapes is closed.
Z2_PIN_RATIO = (1219, 106)
# The tape's 207s per connection, pinned WHOLE (a tape does not grow); the
# five matches in port order.
Z2_207 = {
    "10.0.0.210:51090->44.217.41.117:80":
        {1: 10, 5: 14, 6: 10, 7: 2, 9: 6, 10: 2, 11: 1, 15: 1, 16: 2, 18: 2,
         20: 1, 25: 35, 29: 1},
    "10.0.0.210:51199->52.23.107.149:80":
        {1: 4, 5: 3, 6: 3, 7: 5, 8: 8, 9: 4, 10: 6, 11: 3, 15: 2, 16: 3, 17: 2,
         25: 27},
    "10.0.0.210:57580->34.196.135.145:80":
        {1: 5, 5: 26, 6: 9, 7: 2, 9: 1, 16: 1, 18: 1, 25: 14},
    "10.0.0.210:62925->52.23.107.149:80":
        {1: 6, 2: 1, 5: 11, 6: 7, 8: 7, 10: 3, 11: 1, 12: 6, 16: 1, 17: 2,
         25: 30, 27: 1, 28: 1},
    "10.0.0.210:64557->52.23.107.149:80":
        {1: 11, 5: 6, 7: 13, 8: 7, 9: 4, 10: 2, 16: 1, 18: 1, 25: 17, 27: 1,
         31: 1},
}
# Every 207 on the tape by kind (`_classify_gains`), and the two post-mortem
# gains as (connection, t, units) -- EXACT on the witness tape only.
Z2_KINDS = {"strike": 123, "damage": 232, "post_mortem": 2}
Z2_POST_MORTEM = [("10.0.0.210:51090->44.217.41.117:80", 50.751, 6),
                  ("10.0.0.210:64557->52.23.107.149:80", 46.512, 16)]
# 12: the ambiguous armed (batches, rows) on the tape, none before the pin;
# and the band rows: 24 wand hits of 3 points, each granting 1.
Z2_AMBIGUOUS = (14, 35)
Z2_BAND_ROWS = 24

# THE BAR GATE, measured 2026-08-21 (12). Split the 58 usable connections on
# whether the observing player's skillbar ever carried a skill with a non-zero
# adrenaline cost, and the ENTIRE family lands on one side. These numbers are
# the reason the sub-1% rounding boundary is still unverified rather than
# answered: run the damage -> gain join without this split and 32 damage events
# "grant nothing", the largest of them 7.5% of maximum health, which read
# straight would put retail's cutoff an order of magnitude above the wiki's.
# `toolkit/authsrv/adrenjoin.py` is the extractor; studies/skills 34 is the
# finding. The ARMED column reproduces CENSUS above from an unrelated query,
# which is this pair's own cross-check.
ARMED_CONNECTIONS = 36
DARK_CONNECTIONS = 22
ARMED_FAMILY = {SMSG_ADRENALINE_CHARGE: 921, SMSG_ADRENALINE_CLEAR: 28,
                SMSG_ADRENALINE_SPEND: 40}
# JARIN: the HERO's own family (adrenjoin.scan's third arm), on one tape.
HERO_FAMILY = {SMSG_ADRENALINE_CHARGE: 107, SMSG_ADRENALINE_CLEAR: 9,
               SMSG_ADRENALINE_SPEND: 19}
# The control that makes the dark zero mean something: those connections FOUGHT.
DARK_HITS_LANDED = 45
DARK_MELEE_FINISHED = 13
DARK_DAMAGE_TAKEN = 32
# THE CONFOUND BROKEN (2026-09-22, DESKWORK-D5 step 1, skills 34.11), read
# per connection off 0x00B7 (primary/secondary), property 36 (level), and the
# two libraries. FLOORS from `adrenjoin --by-connection` on 2026-09-22: four
# dark connections whose character is a Warrior -- primary 1 at level 1 on
# 20260914T180058 / 20260915T155656 / 20260915T164906 (18 + 17 + 1 hits) and
# secondary 1 at level 20 on 20260917T224104 (127) -- 163 landed hits, 0 of
# the family (the A/W's OTHER fighting tape, 20260917T160915, reads 7/0: no
# secondary yet, so it is a dark Assassin there and counts below, not here);
# fourteen dark connections with a landed hit whose account library (0x001D,
# once per session, so read per capture) or character library (0x00DB) holds
# an adrenal skill -- 0 of the family; eleven player deaths on dark
# connections, 0 clears.
DARK_WARRIOR_FIGHTS = 4
DARK_WARRIOR_HITS = 163
DARK_LEARNED_FIGHTS = 14
DARK_DEATHS = 11
# And the rounding rule, re-fitted on the armed rows alone -- the population
# that is not selected on the outcome AND not contaminated by the gate.
#
# 32 AND NOT 27, which is where the first cut of this landed. Two rows the first
# scan lost, both recovered by a blind replication run against the same corpus
# with the rival hypothesis: damage ALSO arrives on `0x00A2`, the sourceless
# float channel, exactly ONCE at the observer (a 6.25% hit granting 6) -- the
# first scan read only `0x00A3`, reported that gain as an orphan with no damage
# near it, and moved on. And two batches carry TWO identical hits with TWO
# identical gains, which the first scan refused as ambiguous; identical values
# make every assignment the same pair, so they attribute by symmetry.
ARMED_JOINED = 32
ARMED_FITS = {"round": 32, "ceil": 17, "floor": 15}
ARMED_DAMAGE_TAKEN = 32

# THE CHECK WITH NO FREE PARAMETER. All 11 distinct percentages in the armed
# population are k/480 to within f32 precision, and 480 is the SMALLEST integer
# that does it (only its own multiples follow, to 2000). The observer's int
# property 42 -- maximum health -- reads 480 on the same wire, and nothing in
# the fraction arithmetic touched property 42. Two witnesses not fitted to each
# other: a wrong denominator has no reason to produce 11 integers.
#
# RE-SHAPED 2026-09-17. `ks == ARMED_NUMERATORS` was an equality on the SET OF
# DAMAGE VALUES THE OWNER HAS EVER TAKEN, which is a size of the vault: 58 new
# armed rows took 11 numerators to 31 and every one is still an integer. The
# claim is the integrality, per row, against THAT ROW'S OWN property 42 --
# which now reads four different maxima (480, 408, 384, 336), so the witness
# that was one number is four. The eleven are kept as a SUBSET: a scan that
# lost the old tapes would lose them.
ARMED_MAX_HEALTH = 480
ARMED_NUMERATORS = [12, 13, 14, 15, 17, 24, 29, 30, 34, 39, 53]
ARMED_MAX_HEALTHS = {480, 408, 384, 336}
# The rows whose maximum is NOT 480, and the rival they refute. Until these
# tapes "one max health cannot separate one unit per 1% of maximum from one
# unit per 4.8 raw points" (12's own words). Eleven damaging rows against a
# moved maximum do: round(pct of the CURRENT maximum) fits all of them and
# round(points / 4.8) fits none.
MOVED_MAX_ROWS = 11

# THE RULE IS A FAMILY, NOT A CANDIDATE, and the corpus does not pin which
# family. Fit `units == f(pct * k)` for each rounding f and solve for the k
# interval that fits ALL 32 armed rows. floor comes out EMPTY -- no rescale of
# the damage fraction can produce this wire under flooring, which refutes the
# wiki AND the "retail floors pre-mitigation damage" repair in one line. round
# and ceil both survive, and they DISAGREE at the low end: round grants nothing
# under ~0.5%, ceil grants one unit for any damage at all. `pools.damage_units`
# implements round. Endpoints are exact rationals over the observed rows, so
# this is arithmetic and not a fit with slack. studies/skills 34.C.
#
# CEIL DIED 2026-09-17, AND THIS IS THE ROW THE PARAGRAPH ABOVE ASKED FOR. RB's
# 1.25 % hit granted 1 (ceil needs k <= 0.8) and RB2's 59.58 % hit granted 60
# (ceil needs k > 0.990): no k does both, under ANY rescale. Round survives and
# its interval closed from [1.0, 1.04) to [1.0, 1.0054), which is as near to
# "k is 1, the wire's own fraction, unscaled" as 90 rows can say. The old two
# intervals are kept as the OUTER bound: a family only ever narrows, so a round
# interval that left the old one is a decoder change, not a finding.
FAMILY_K = {"floor": None,                        # empty: lo >= hi
            "round": (1.000000, 1.040000),        # the outer bound, 2026-08-21
            "ceil":  None}                        # empty since 2026-09-17

# THE NEAR MISS, and it is the whole reason the boundary is still open. The two
# surviving families disagree only below ~1%. EXACTLY ONE damage event in the
# entire corpus lands in that band -- capture 20260810T235916, connection
# ...:49163, observer 31, wire bits 0xBC23D70A -- and its bar carries no
# adrenal skill, so there was nothing to charge. Every other damage-taken event
# is at or above 2.5%. The corpus came within one connection of answering the
# question.
#
# AND ITS VALUE IS 0.999999978%, NOT 1%. Rounded to four decimals it reads
# "1.0000", which is exactly where round and ceil AGREE; from the bytes it sits
# just below, where they do not. Three independent readers printed it rounded
# and all three read past it, which is why `adrenjoin` now prints nine.
NEAR_MISS_BITS = 0xBC23D70A
# DERIVED FROM THE BITS, not transcribed: a hand-typed 0.99999998 is one
# fat-fingered zero away from 99.99999776, which is what the first cut of this
# constant actually was and which the check caught immediately.
NEAR_MISS_PCT = abs(struct.unpack("<f", struct.pack("<I", NEAR_MISS_BITS))[0]) * 100.0
DISAGREEMENT_BAND = (0.5, 1.0)
# FAILED AS WRITTEN, 2026-09-29 (CASTAI-Z2), and recorded rather than re-worded.
# The prediction was "exactly one damage event in the corpus lands in [0.5 %,
# 1.0 %), and it is DARK" -- a size of the vault dressed as a claim -- and the
# Smiting Monks' tape put 24 ARMED rows in the band (3-point wand hits on a
# 374..418 maximum, 0.718 %..0.802 %), every one answered by a 207 carrying 1.
# What that settles: round (and ceil) grant 1 across the band, and floor,
# granting 0, is refuted on 24 more rows. What it does NOT settle is the
# question the check actually guarded, which sits BELOW the band: no row in
# the corpus, armed or dark, has ever landed in (0, 0.5 %), so whether such a
# hit sends a 207 carrying 0 or nothing is still NOT OBSERVED (test_pools 11d
# predicts the zero). The check now reads: as of Z2_PIN_STAMP exactly the one
# dark near miss; on the witness tape exactly Z2_BAND_ROWS armed rows, each 3
# points, each granting round(pct) = 1 and not floor; past the pin every armed
# band row must grant round(pct); the (0, 0.5 %) count REPORTED, not asserted.

# The three skills retail spends adrenaline on in this corpus, and the number of
# connections carrying 207 at all.
# 348 is OURS -- capture 20260821T205552, the live run that settled the timeout
# anchor. It is the first spend in this corpus that is not a sword attack skill:
# a self-targeted adrenal skill (type_code 15, target 0, 80 units), chosen for
# that plan precisely because it lands no hit. It broadened the model on arrival;
# see ACTIVATION_FOLLOWER below.
SPEND_SKILLS = {348: 8, 382: 27, 384: 11, 385: 13}   # JARIN: +7 / +7 / +5, the hero's (0x00D2 [30, skill] on the tape)
SELF_SCOPED_CONNECTIONS = 11

# ---------------------------------------------------------------------------
# THE CLIENT, build 38797. Every VA below was read out of the pinned pristine
# image; none is a guess and none is transcribed from an upstream.
VA_CHARGE_WORKER   = 0x00821980     # 207
VA_CLEAR_WORKER    = 0x00821B00     # 208
VA_SET_WORKER      = 0x00821B70     # 209
VA_SPEND_WORKER    = 0x00821C00     # 210
WORKERS = {SMSG_ADRENALINE_CHARGE: VA_CHARGE_WORKER,
           SMSG_ADRENALINE_CLEAR:  VA_CLEAR_WORKER,
           SMSG_ADRENALINE_SET:    VA_SET_WORKER,
           SMSG_ADRENALINE_SPEND:  VA_SPEND_WORKER}

VA_DESCRIPTOR_CF = 0x00BC96B8       # first of four, 12-byte stride
DESCRIPTOR_STRIDE = 12
VA_HOTKEY_CONTAINER_DELTA = 0x6F0   # what every thunk adds to [ctx+0x2c]

VA_CHARGE_STORE   = 0x008219EA      # mov [esi],ecx -- the only arithmetic
                                    # write to a slot's +0x00 in the image
VA_CHARGE_END     = 0x008219AD      # lea ebx,[eax+0xa4]
VA_CHARGE_FIRST   = 0x008219B5      # lea esi,[eax+4]
VA_CHARGE_STRIDE  = 0x008219F1      # add esi,0x14
VA_CHARGE_THRESH  = 0x008219D6      # movzx ecx,word [eax+0x38]
VA_CHARGE_ADD     = 0x008219DF      # mov eax,[esi] / add eax,[ebp+0xc]
VA_FLD_25F        = 0x00821A03      # fld dword [0x009495B4]; operand at +2
VA_25F_CONST      = 0x009495B4      # .rdata, 25.0f
VA_CHARGE_FLAGCLR = 0x008219B3      # xor edi,edi -- before the slot loop
VA_CHARGE_FLAGSET = 0x008219EC      # mov edi,1 -- inside it, after the store
VA_CHARGE_FLAGTST = 0x008219F8      # test edi,edi / je past the repaint
VA_CHARGE_LOOPTOP = 0x008219C0      # where 0x008219F6's jne goes back to
VA_UI_EVENT_PUSH  = 0x00821A12      # push 0x10000058
VA_CHARGE_EPILOG  = 0x00821AED      # where the je lands: the shared exit
UI_EVENT_ADREN    = 0x10000058
VA_CLEAR_BOTH     = 0x00821B30      # mov [eax],0 / mov [eax+4],0
VA_SET_BOTH       = 0x00821BD7      # mov [ecx],eax / mov [ecx+4],eax
VA_SPEND_25       = 0x00821C71      # cmp esi,0x19 / jbe / add esi,-0x19
VA_SPEND_PAIRLOOP = 0x00821C81      # cmp ecx,2 -- the two halves
VA_DEFERRED_TASK  = 0x00820DD0      # a -> b commit, ChCliSkill:84 lives here

VA_DISPLAY_WRAPPER  = 0x00816EF0    # ChCliApi, GmSkSlot's sole callee
VA_DISPLAY_ACCESSOR = 0x00821050    # what it tail-calls
VA_ACCESSOR_INDEX   = 0x00821081    # lea eax,[esi+esi*4] / mov eax,[edi+eax*4+8]
VA_ACCESSOR_BOUND   = 0x0082106B    # cmp esi,8
VA_SLOT_CALL        = 0x00542E78    # GmSkSlot -> the wrapper
VA_SLOT_THRESH      = 0x00542E80    # movzx eax,word [esi+0x38]
VA_MAP_GATE_CALL    = 0x00542E43    # call MissionCliGetMap
VA_MAP_GATE_CMP     = 0x00542E48    # cmp eax,1 / jne
VA_MISSION_CLI_GET_MAP = 0x0084D9B0
MISSION_MAP_GAME = 1                # MsCliApi:251; OUTPOST is 0, QuestLog:261

SLOT_STRIDE = 0x14
SLOT_COUNT = 8
SLOT_FIRST_OFF = 4                  # container + 4 is slot 0's adrenaline_a
SLOT_END_OFF = 0xA4
ACCESSOR_DISP = 8                   # container + 8 is slot 0's adrenaline_b
SPEND_STRIKE = 0x19                 # 25, the per-strike decrement in 210

# ArenaNet's own text, four sites. Each is a SINGLE assert cited as the evidence
# for one claim, with its file and line -- CLAUDE.md's boundary for a
# MEASUREMENT, and not a bulk dump.
ASSERTS = {
    0x00820DEB: ("ChCliSkill", 84,
                 "context->skillAdrenalineUpdateArray.Count()"),
    0x00821C16: ("ChCliSkill", 463, "skill"),
    0x008CC42D: ("GmCtlSkCard", 409, "!(energyCost && skillData.adrenaline)"),
    0x008D377A: ("GmCtlSkListEntry", 185,
                 "!(energyCost && skillData.adrenaline)"),
}


# ---------------------------------------------------------------------------
# 1-3: no captures, no client. The mandatory core.


def section_schema():
    """The four declared shapes, out of `schema/messages.json` itself.

    Tracked in git, so this is the one section that runs anywhere. It is also
    half of §8's cross-check: the client's own descriptor table declares a field
    COUNT for each of these four, and the two were derived from different
    things -- our schema from the message catalog importer, the descriptor from
    the image -- so either can refute the other.
    """
    print("1. the four declared shapes, from schema/messages.json")
    path = os.path.join(os.path.dirname(TOOLKIT), "schema", "messages.json")
    cat = json.load(open(path, encoding="utf-8"))
    table = cat["channels"]["GAME_SMSG"]["messages"]

    want = {SMSG_ADRENALINE_CHARGE: (10, 3), SMSG_ADRENALINE_CLEAR: (6, 2),
            SMSG_ADRENALINE_SET: (16, 5), SMSG_ADRENALINE_SPEND: (12, 4)}
    for op, (size, nfields) in want.items():
        row = table[str(op)]
        got = (row["declared_unpack_size"], len(row["fields"]))
        LEDGER.ok(got == (size, nfields),
                  f"opcode {op} = 0x{op:04X} is {size} bytes over {nfields} "
                  f"fields",
                  f"{got}. Field 0 is the msg header in all four, so the "
                  f"payload is {nfields - 1} value(s) -- which is why "
                  f"`decode_all` puts the agent at values[1] and 207's units "
                  f"at values[2]")

    fixed = [op for op in FAMILY if table[str(op)]["variable_length"]]
    LEDGER.ok(not fixed,
              "and all four are FIXED length, none variable",
              f"variable: {fixed}. It matters for the sender: a fixed message "
              f"cannot be padded, so a server emitting 207 with a wrong width "
              f"desynchronises every later message in the same datagram rather "
              f"than being ignored")
    return want


def section_pin_consistency():
    """A tripwire on this file's own pinned constants, not evidence.

    Everything else here is a measurement. This is not: it is the arithmetic
    that ties the census constants to each other, and it exists because the
    likely way this model drifts is a session editing ONE number after a corpus
    change. It can only fail on that edit, which is the edit that matters.
    """
    print("\n2. the pinned constants agree with each other")
    total = STRIKE_COUNT + sum(SUB_STRIKE.values()) + sum(OVER_STRIKE.values())
    LEDGER.ok(total == CENSUS[SMSG_ADRENALINE_CHARGE],
              f"the three 207 populations sum to the census total, {total}",
              f"{STRIKE_COUNT} at exactly {STRIKE_UNITS} units plus "
              f"{sum(SUB_STRIKE.values())} below it and {sum(OVER_STRIKE.values())} "
              f"above (JARIN). NOT A MEASUREMENT -- a "
              f"tripwire, so that half an edit goes red here instead of "
              f"passing §4 and §4b with two mutually inconsistent numbers")
    LEDGER.ok(sum(SPEND_SKILLS.values()) == CENSUS[SMSG_ADRENALINE_SPEND],
              f"and the three spent skills sum to the 210 total, "
              f"{sum(SPEND_SKILLS.values())}",
              f"{SPEND_SKILLS}")


def section_cost_column():
    """ADRENALINE COSTS ARE NOT ALL MULTIPLES OF 25, and that is the finding.

    If the bar were denominated in strikes -- the reading every displayed icon
    invites, because the icon shows `ceil(units/25)` -- then every cost in
    ArenaNet's own column would be a multiple of 25. Seven distinct ones are
    (six once the 38888 overrides landed, SLICE-H17b)
    not. So 25 is the GAIN PER STRIKE and not the quantum of the bar, the pool
    has to be modelled in RAW UNITS (`pools.py` already is), and a server that
    compared four strikes against Battle Rage's 80 would leave the skill dark
    through a fight it should have fired in.
    """
    print("\n3. the client's own adrenaline cost column, in raw units")
    import content
    rows = content.load().rows("skills")

    costs = collections.Counter()
    for _id, row in rows.items():
        units = int(row.get("adrenaline_units", 0) or 0)
        if units:
            costs[units] += 1
    off_grid = sorted(u for u in costs if u % STRIKE_UNITS)
    on_grid = sorted(u for u in costs if not u % STRIKE_UNITS)

    # 2026-09-14 (SLICE-H17b): content/overrides/ carries fourteen 38888 rows; Final
    # Thrust's 240 became 200 and Gash's 140 a 125, so the pin's seven off-grid
    # costs over 40+ rows are six over 37 on the served table. The argument is
    # unchanged -- one 80 refutes a strike-quantised bar -- and the floor follows
    # the measurement, not the other way round.
    LEDGER.ok(len(off_grid) >= 6 and sum(costs[u] for u in off_grid) >= 35,
              f"{len(off_grid)} distinct costs are NOT multiples of "
              f"{STRIKE_UNITS}, over {sum(costs[u] for u in off_grid)} rows",
              f"{off_grid} of {sorted(costs)}, across "
              f"{sum(costs.values())} rows with a nonzero cost out of "
              f"{len(rows)} in the overlay. MEASURED over the client's full "
              f"3,443-row table too: 151 nonzero, same shape. A bar quantised "
              f"in strikes cannot produce an 80 or a 130, so this is the "
              f"measurement behind `pools.AdrenalinePool` holding raw units -- "
              f"and behind §9's `add esi,-0x19`, which is the client "
              f"decrementing RAW units by one strike rather than counting "
              f"strikes")
    LEDGER.ok(len(on_grid) >= 5,
              f"CONTROL: {len(on_grid)} distinct costs ARE multiples of "
              f"{STRIKE_UNITS}",
              f"{on_grid}. Without this the check above would also pass on a "
              f"column read at the wrong offset, where everything is off-grid "
              f"by accident. The mix is what says the column is real")
    LEDGER.ok(costs and max(costs) < 0x10000,
              f"and every cost fits in 16 bits -- max {max(costs) if costs else None}",
              f"THE WIDTH NUANCE, recorded because two of our own readers "
              f"disagree and neither is wrong today: the client reads this "
              f"field as movzx WORD at both 0x{VA_SLOT_THRESH:08X} and "
              f"0x{VA_CHARGE_THRESH:08X}, while "
              f"`clientscan/skilltable.py` reads it as u32. On build 38797 the "
              f"high word is zero in every row, so nothing is broken -- but a "
              f"build that ever set it would give the two readers different "
              f"answers, and this is the check that would notice")


def section_classifier_arms():
    """THE SIGNATURE'S CLASSIFIER, made to refuse (CASTAI-Z2, 2026-09-29).

    `_classify_gains` gained a fourth kind, and a kind that can only ever be
    assigned is a hole in the signature: every unexplained gain would find a
    home in it and the check below it could not go red. So four synthetic
    batches, no captures needed: the rule's two terms -- the agent's death flag
    in the batch, and the gain AFTER the batch's last damage word at the agent
    -- are each dropped in turn and the same orphan gain must go back to
    `unexplained`; and a gain a pooled word fits must still read `damage`,
    death flag or not, because the pooled rule is tried first.
    """
    print("\n3b. the post-mortem kind refuses without either of its two terms")
    import adrenjoin
    me, t = 7, 1.0

    def word(pct):
        dw = struct.unpack("<I", struct.pack("<f", -pct / 100.0))[0]
        return (t, adrenjoin.PROP_FLOAT_TARGET, [adrenjoin.PROP_FLOAT_TARGET, 16, me, 4, dw])

    def gain(units):
        return (t, SMSG_ADRENALINE_CHARGE, [SMSG_ADRENALINE_CHARGE, me, units])

    death = (t, SMSG_AGENT_UPDATE_FLAGS,
             [SMSG_AGENT_UPDATE_FLAGS, me, adrenjoin.PLAYER_DEAD_FLAG])

    def kinds(msgs):
        agg = {"gain_kinds": collections.defaultdict(collections.Counter),
               "gain_rows": []}
        _classify_gains(agg, "synthetic", "c", msgs, adrenjoin)
        return dict(agg["gain_kinds"]["synthetic"])

    # The shape of 20260929T100038 :51090 t 50.751: the killing word (15.625 %,
    # gain 16 ahead of it), then a gain of 6 with no word, then the death flag.
    rule = kinds([gain(16), word(15.625), gain(6), death])
    LEDGER.ok(rule == {"damage": 1, "post_mortem": 1},
              f"an orphan gain AFTER the killing word, in a batch that carries "
              f"the agent's death, reads post_mortem: {rule}",
              "expected {'damage': 1, 'post_mortem': 1}. The pooled word still "
              "takes the 16 first; only the gain nothing fits, sitting past the "
              "last word at the agent in a death batch, takes the new kind")
    no_death = kinds([gain(16), word(15.625), gain(6)])
    not_after = kinds([gain(6), gain(16), word(15.625), death])
    LEDGER.ok(no_death == {"damage": 1, "unexplained": 1}
              and not_after == {"damage": 1, "unexplained": 1},
              f"KNOWN-BAD ARMS: the same orphan WITHOUT the death flag reads "
              f"{no_death}; with the flag but BEFORE the last word it reads "
              f"{not_after}",
              "expected {'damage': 1, 'unexplained': 1} both times. Each term "
              "refuses on its own, so a gain that merely arrives in a busy "
              "batch, or merely on a tape with a death in it, cannot hide in "
              "post_mortem; the corpus check in 4b reddens on it")
    control = kinds([gain(6), word(5.625), death])
    LEDGER.ok(control == {"damage": 1},
              f"CONTROL: a gain a pooled word fits reads damage even in a death "
              f"batch: {control}",
              "expected {'damage': 1}. The 13 killing words in the corpus are "
              "present and their gains read this way; the post-mortem kind is "
              "reached only when the pool has nothing left for the gain")


# ---------------------------------------------------------------------------
# 4-7: the live corpus. ArenaNet's own wire.


def _round_half_up(x):
    """Section 12's rounding, the only one that fits the armed rows."""
    return int(math.floor(x + 0.5 + 1e-9))


def _classify_gains(agg, stamp, conn, msgs, adrenjoin):
    """Every 207 on one connection, against the damage words in ITS batch.

    THE SIGNATURE 4b's re-scoped claims rest on (CASTAI-Z1). A batch is an
    identical timestamp (section 12's join). For each agent a 207 names, the
    damage words AT THAT AGENT in the batch give a pool of round(% of its
    current maximum) -- the wire's own fraction, `adrenjoin.is_damage_to`. Each
    gain is then:
      strike       25 (and, as a control, whether a 25 % word sat beside it)
      damage       equal to one pooled word's round(%) -- the damage rule
      summed       25 + one pooled word's round(%) -- a strike and a hit taken
                   in one message, JARIN's reading of its three
      post_mortem  (CASTAI-Z2, 2026-09-29) no pooled word fits, the batch
                   carries the agent's DEATH flag (0x0026 [agent, 4]) and the
                   gain sits AFTER the batch's last damage word at the agent:
                   a hit landing in the tick the agent died in, after the blow
                   that killed. Retail sends its gain and not its word -- 2 of
                   2 on 20260929T100038, and the 13 killing words in the corpus
                   are all present. Both terms are load-bearing: section 3b
                   drops each in turn and the same orphan goes back to
                   `unexplained`
      unexplained  anything else, which is what the check refuses
    """
    batches = collections.defaultdict(list)
    for i, (t, op, v) in enumerate(msgs):
        batches[t].append((i, op, v))
    for t, items in batches.items():
        agents = {int(v[1]) for _i, op, v in items if op == SMSG_ADRENALINE_CHARGE}
        for a in sorted(agents):
            gains = [(i, int(v[2])) for i, op, v in items
                     if op == SMSG_ADRENALINE_CHARGE and int(v[1]) == a]
            words = [(i, abs(adrenjoin.f32(
                         v[4] if op == adrenjoin.PROP_FLOAT_TARGET else v[3])) * 100.0)
                     for i, op, v in items if adrenjoin.is_damage_to(op, v, a)]
            pcts = [x for _i, x in words]
            pool = [_round_half_up(x) for x in pcts]
            last_word = max((i for i, _x in words), default=-1)
            dies = any(op == SMSG_AGENT_UPDATE_FLAGS and len(v) > 2
                       and int(v[1]) == a and int(v[2]) == adrenjoin.PLAYER_DEAD_FLAG
                       for _i, op, v in items)
            # Largest units first, as before (a summed 25 + x is tried before
            # the x it would otherwise consume); stable, so equal units keep
            # stream order.
            for gi, g in sorted(gains, key=lambda ig: ig[1], reverse=True):
                if g == STRIKE_UNITS:
                    kind = "strike_beside_25pct" if STRIKE_UNITS in pool else "strike"
                elif g in pool:
                    pool.remove(g)
                    kind = "damage"
                elif g - STRIKE_UNITS in pool:
                    pool.remove(g - STRIKE_UNITS)
                    kind = "summed"
                elif dies and gi > last_word:
                    kind = "post_mortem"
                else:
                    kind = "unexplained"
                agg["gain_kinds"][stamp][kind] += 1
                if g != STRIKE_UNITS:
                    agg["gain_rows"].append({"stamp": stamp, "conn": conn,
                                             "t": round(t, 3), "agent": a,
                                             "units": g, "kind": kind,
                                             "pcts": pcts})


class MissingRow(KeyError):
    """A skill no stated rule resolves -- never swallowed by a blanket except."""


_CLIENT_TABLES = {}


def _client_table(build):
    """(data, base, count) of `build`'s pristine image, verified by pinned.find."""
    if build not in _CLIENT_TABLES:
        import pinned
        import skilltable
        exe, _why = pinned.find(build=build)
        with open(exe, "rb") as fh:
            data = fh.read()
        base, count, _score = skilltable.locate_table(data)
        _CLIENT_TABLES[build] = (data, base, count)
    return _CLIENT_TABLES[build]


def skill_row(world, skill, builds, used=None):
    """The skill's row, by a STATED RULE (CASTAI-Z1, R8).

    Content's `skills` table is the PLAYER CORPUS of build 38797
    (`skilltable.player_corpus`: equip_family 1, PvP excluded). A skill it
    lacks is read from the client table of a build it was captured under, and
    accepted there ONLY as a PvP-only split of a player skill (pvp_only,
    equip_family 0, `linked_id` a content row). Anything else raises
    MissingRow. `used` collects {skill: (build, linked_id)}."""
    import content
    try:
        return world.get("skills", str(skill))
    except content.ContentError:
        pass
    import skilltable
    for build in sorted(b for b in builds if b is not None):
        data, base, count = _client_table(build)
        if not 0 <= skill < count:
            continue
        r = skilltable.parse_record(data, base, skill)
        if (r["pvp_only"] and r["equip_family"] == 0
                and str(r["linked_id"]) in world.rows("skills")):
            if used is not None:
                used[skill] = (build, r["linked_id"])
            return r
    raise MissingRow(f"skill {skill} (builds {sorted(builds, key=str)}) is not in "
                     f"content and is not a PvP split of a player skill")


def outside_player_corpus(skill, builds):
    """True when every build in `builds` that can be read has a client row for
    `skill` OUTSIDE the player corpus (`skilltable.player_corpus`: equip_family
    1, PvP clear), and at least one can -- the stated reason content's `skills`
    table lacks it. False for an id past every table or with no build."""
    import skilltable
    seen = []
    for build in sorted(b for b in builds if b is not None):
        data, base, count = _client_table(build)
        if not 0 <= skill < count:
            continue
        r = skilltable.parse_record(data, base, skill)
        seen.append(not (r["equip_family"] == 1 and not r["pvp_only"]))
    return bool(seen) and all(seen)


def _capture_build(cap, conn_path):
    """The client build a connection was captured with, never guessed.

    The file's own version record (origin.build_of) first; files from before
    38833 shipped carry none, and for those the capture's manifest names the exe
    it launched under its snapshot stamp (`pinned.known_build`). Else None --
    and `skill_row` reads no client table for None."""
    import origin
    import pinned
    b, _why = origin.build_of(conn_path)
    if b is not None:
        return b
    try:
        with open(os.path.join(cap, "manifest.json"), encoding="utf-8") as fh:
            exe = json.load(fh).get("exe") or ""
    except (OSError, ValueError):
        exe = ""
    known = pinned.known_build(os.path.basename(os.path.dirname(exe))) if exe else None
    return known.number if known else None


def live_corpus_dir():
    """The live-capture directory, or None and a DECLARED skip when it is absent.

    THIS IS THE ONLY PLACE THE LIVE ORACLE MAY BE SKIPPED, and it skips on one
    cause: the vault (or its `captures/live`) is not on this machine. Until the
    CASTAI-Z1 review `main()` wrapped the whole of `scan_corpus()` in
    `except (Exception, SystemExit)`, so once the per-connection blanket except
    came out, a gapped connection the manifest does NOT declare raised a
    `TapeError` that the same handler turned into "no live captures here" -- a
    GREEN run (41 checks, 1 declared skip) with the declared-gap check never
    executed. Resolving the directory here and calling `scan_corpus` outside any
    handler makes that case what it is: a crash naming the connection.

    SystemExit is caught deliberately: `vaultpath.require_dir` raises it by
    design and it is not an Exception subclass, so without it a missing vault
    would kill the run with a traceback instead of declaring the skip the floor
    rule is built around.
    """
    try:
        import vaultpath
        return vaultpath.require_dir("captures", "live",
                                     why="the adrenaline wire oracle")
    except (SystemExit, ImportError) as ex:
        LEDGER.skip("the live-corpus oracle (sections 4-7, 12)",
                    f"no live captures here ({ex}). These are the sections "
                    f"that put the model against ArenaNet's own wire -- a "
                    f"green run without them has checked the client and none "
                    f"of the traffic")
        return None


def scan_corpus(live):
    """Every message of the family in the live corpus, per connection.

    `live` is the directory `live_corpus_dir()` resolved. Nothing in here may be
    caught by the caller: a connection that fails to load and is not declared
    gapped by its own manifest propagates as a crash.

    Returns a dict of aggregates. `tape.load_tape` refuses a non-live origin by
    itself (`toolkit/origin.py`), so nothing here can pool our own server's
    traffic in with retail's -- which is the failure `test_pools` §2 is built
    to avoid and the reason this walks `captures/live` rather than `captures`.

    THE ORDERING JOIN IS BY STREAM INDEX AND BY TIME BOTH, and deliberately: a
    spend and its activation ride the same batch, so a time-only join cannot
    order them and an index-only join cannot tell a batch from its neighbour.
    §7 requires the pair to be adjacent in the stream AND simultaneous on the
    clock, which is a conjunction a coincidence has to satisfy twice.
    """
    import adrenjoin
    import livewire
    import tape
    from codec import Codec

    codec = Codec()
    agg = {
        "set_aside": [],         # (stamp, connection, still refused)
        # CASTAI-Z1: every 207, classified against the damage words at ITS
        # agent in ITS batch (section 4b's signature). stamp -> Counter.
        "gain_kinds": collections.defaultdict(collections.Counter),
        "gain_rows": [],         # the non-strike gains, one row each
        "spend_builds": collections.defaultdict(set),
        # (stamp, skill) -> builds: section 6 scopes the PvP-split rule's
        # uses PER CAPTURE, so a witness stays on its own tape (R3).
        "spend_stamp_builds": collections.defaultdict(set),
        "spend_pairs_by_stamp": collections.defaultdict(collections.Counter),
        "cast_builds": collections.defaultdict(set),
        "cast_stamps": collections.defaultdict(set),
        "captures": 0, "connections": 0, "messages": 0,
        "census": collections.Counter(),
        "amounts": collections.Counter(),
        "amounts_by_stamp": collections.defaultdict(collections.Counter),
        "amounts_by_conn": collections.defaultdict(collections.Counter),
        "spend_skills": collections.Counter(),
        "spend_copies": collections.Counter(),
        "self_scope": [],        # (stamp, agents_on_207, agents_on_218)
        "prop_spread": [],       # distinct agents on the property channel,
                                 # for the connections carrying 207 only
        "order": collections.Counter(),      # (stream delta, prop id) -> n
        "cast_skills": collections.Counter(),
    }

    for stamp in sorted(os.listdir(live)):
        cap = os.path.join(live, stamp)
        if not os.path.isdir(cap):
            continue
        agg["captures"] += 1
        declared = livewire.declared_gaps(cap)
        for conn in tape.channel_files(cap):
            # A GAPPED CONNECTION is set aside ONLY because its own capture's
            # manifest declares it (CASTAI-Z1, livewire.declared_gaps), and it
            # must STILL be refused. No blanket except: any other connection
            # that fails to load is a crash, not a quiet `continue`.
            if conn["connection"] in declared:
                try:
                    tape.load_tape(cap, conn["connection"])
                    refused = False
                except tape.TapeError:
                    refused = True
                agg["set_aside"].append((stamp, conn["connection"], refused))
                print(f"  (set aside: {stamp} {conn['connection']} -- its manifest "
                      f"declares gaps {declared[conn['connection']]})")
                continue
            _info, events = tape.load_tape(cap, conn["connection"])
            msgs, _receipt = tape.decode_all(events, codec, "GAME_SMSG", 0)
            build = _capture_build(cap, conn["path"])
            agg["connections"] += 1
            agg["messages"] += len(msgs)

            on_207, on_218, prop_agents = set(), set(), set()
            casts, spends = [], []
            for i, (t, op, v) in enumerate(msgs):
                if op in FAMILY:
                    agg["census"][op] += 1
                if op == SMSG_ADRENALINE_CHARGE:
                    agg["amounts"][v[2]] += 1
                    agg["amounts_by_stamp"][stamp][v[2]] += 1
                    agg["amounts_by_conn"][(stamp, conn["connection"])][v[2]] += 1
                    on_207.add(v[1])
                elif op == SMSG_ADRENALINE_SPEND:
                    agg["spend_builds"][v[2]].add(build)
                    agg["spend_stamp_builds"][(stamp, v[2])].add(build)
                    agg["spend_pairs_by_stamp"][stamp][(v[2], v[3])] += 1
                    agg["spend_skills"][v[2]] += 1
                    agg["spend_copies"][v[3]] += 1
                    spends.append((i, t, v[1], v[2]))
                elif op == SMSG_SKILLBAR_UPDATE:
                    on_218.add(v[1])
                elif op in INT_OPS or op in FLOAT_OPS:
                    prop_agents.add(v[2])
                    if op in INT_OPS and v[1] in CAST_PROPS:
                        casts.append((i, t, v[2], v[-1], v[1]))
                        agg["cast_skills"][v[-1]] += 1
                        agg["cast_builds"][v[-1]].add(build)
                        agg["cast_stamps"][v[-1]].add(stamp)

            _classify_gains(agg, stamp, conn["connection"], msgs, adrenjoin)
            if on_207:
                agg["self_scope"].append((stamp, sorted(on_207),
                                          sorted(on_218)))
                agg["prop_spread"].append(len(prop_agents))
            for i, t, agent, skill in spends:
                for ci, ct, cagent, cskill, cprop in casts:
                    if (cagent == agent and cskill == skill
                            and abs(ct - t) < 1e-6):
                        agg["order"][(ci - i, cprop)] += 1
    return agg


def section_census(agg):
    """THE CENSUS, and 209 is the live handler retail never uses."""
    print("\n4. the census: 114,985 messages of ArenaNet's own wire")
    LEDGER.ok(agg["captures"] >= CORPUS_CAPTURES
              and agg["connections"] >= CORPUS_CONNECTIONS
              and agg["messages"] >= CORPUS_MESSAGES,
              f"the corpus is at least {CORPUS_MESSAGES} messages over "
              f"{CORPUS_CONNECTIONS} connections in {CORPUS_CAPTURES} captures",
              f"{agg['messages']}/{agg['connections']}/{agg['captures']} today, "
              f"decoded with ZERO framing errors. One capture "
              f"(20260817T175358) has no wire.jsonl and contributes no "
              f"connections, which is why the two are floored separately. A "
              f"corpus that SHRANK is a vault that moved and every count below "
              f"would quietly get easier -- that is what this refuses. Growth "
              f"is the campaign working and must not redden a thing")

    set_aside = agg["set_aside"]
    LEDGER.ok([(st, c) for st, c, _r in set_aside] == DECLARED_GAPPED
              and all(r for _st, _c, r in set_aside),
              f"the connections set aside are EXACTLY the capture-declared gapped "
              f"ones, and each is still refused by the loader: {set_aside}",
              f"expected {DECLARED_GAPPED} (livewire.declared_gaps, from the "
              f"capture's own manifest). Until CASTAI-Z1 this walk dropped any "
              f"connection that failed to load with a blanket except; now a "
              f"future gapped connection reddens this rather than vanishing from "
              f"the corpus, and any OTHER failure is a crash")

    for op in (SMSG_ADRENALINE_CHARGE, SMSG_ADRENALINE_CLEAR,
               SMSG_ADRENALINE_SPEND):
        LEDGER.ok(agg["census"][op] >= CENSUS[op],
                  f"opcode {op} appears at least {CENSUS[op]} times",
                  f"{agg['census'][op]} today. A floor: more captures mean more "
                  f"of these and that is not a regression. What a shortfall "
                  f"would mean is that the decoder stopped seeing them")

    LEDGER.ok(agg["census"][SMSG_ADRENALINE_SET] == 0,
              f"and opcode {SMSG_ADRENALINE_SET} appears 0 times in "
              f"{agg['messages']} messages",
              f"{agg['census'][SMSG_ADRENALINE_SET]}. A live, fully wired "
              f"handler -- §8 walks the chain to its worker and §9 reads the "
              f"stores -- that retail's server NEVER SENDS. Exactly the shape "
              f"of energy property 33 in `test_pools` §2a, an absolute setter "
              f"the client implements and the server does not use, and it says "
              f"the same thing: the client INTEGRATES its own copy from deltas, "
              f"so our server must send 207/208/210 and not 209")
    neighbours = sum(agg["census"][op] for op in FAMILY
                     if op != SMSG_ADRENALINE_SET)
    LEDGER.ok(neighbours >= 700,
              f"POSITIVE CONTROL: the same scan finds {neighbours} of its "
              f"three neighbours",
              "a filtered search that finds nothing proves nothing until it "
              "has found something we already know it should. 724 when this "
              "was written -- so the zero above is retail's silence and not a "
              "decoder that cannot see this range")


def section_populations(agg):
    """TWO POPULATIONS in 207's amount, and the strike rule's own signature."""
    print("\n4b. what a 207 carries: 25, or something under it")
    # THE STRIKE COUNT is over everything; the four SHAPE claims are over the
    # corpus WITHOUT the two named hits-taken tapes, which are pinned whole by
    # the last check of this section (DAMAGE_TAPES says what each one is).
    everything = agg["amounts"]
    amounts = collections.Counter()
    at_pin = collections.Counter()      # CASTAI-Z1: the corpus the claims were made over
    for stamp, c in agg["amounts_by_stamp"].items():
        if stamp not in DAMAGE_TAPES:
            amounts.update(c)
            if stamp < PIN_STAMP:
                at_pin.update(c)
    # THE COUNT IS A FLOOR AND THE DOMINANCE IS THE CLAIM. Every gain the
    # corpus has added since this was first pinned carried exactly 25, twice
    # over (886 -> 889 here, 631 -> 886 at the previous re-pin), so the
    # equality reddened on the very evidence that strengthens the reading.
    # What cannot move without meaning something is the SHARE: the sub-25 tail
    # is a small ragged minority and 25 is the overwhelming mode.
    tail_total = sum(n for a, n in amounts.items() if a < STRIKE_UNITS)
    LEDGER.ok(everything[STRIKE_UNITS] >= STRIKE_COUNT,
              f"at least {STRIKE_COUNT} of the {sum(everything.values())} carry "
              f"exactly {STRIKE_UNITS}",
              f"{everything[STRIKE_UNITS]} today. WIKI (GWW, 'Adrenaline', rev. "
              f"2026-07-02): one successful weapon hit is 25 units. OBSERVED "
              f"as a value; that it is one strike per landed hit is the "
              f"reading, and it is the reading `pools.on_hit_landed` already "
              f"implements")
    # CASTAI-Z2 (2026-09-29): AS OF THE PIN. The Smiting Monks' tape put the
    # tail ahead of the strikes, 229 to 123 -- the axe landed 123 times while
    # four monks' aura ticks, Zealot's Fire and 3-point wand hits charged the
    # bar 229 times -- and this check's own prose already says what that is:
    # a fact about how the owner plays, and a tape made to be hit is named out
    # of the ratio rather than allowed to drag it. So the tape is named
    # (Z2_207, pinned whole below), the ratio is read over the corpus BEFORE
    # it, EXACT, and the whole-corpus and per-tape numbers are REPORTED. What
    # carries the tail's MEANING past the pin is the SIGNATURE two checks
    # down -- every one of the 229 is a joined damage word or a post-mortem
    # gain -- not this ratio, which never measured the wire.
    z2_pin = collections.Counter()
    for stamp, c in agg["amounts_by_stamp"].items():
        if stamp not in DAMAGE_TAPES and stamp < Z2_PIN_STAMP:
            z2_pin.update(c)
    tail_pin = sum(n for a, n in z2_pin.items() if a < STRIKE_UNITS)
    per_tape = {st: (c[STRIKE_UNITS], sum(n for a, n in c.items() if a < STRIKE_UNITS))
                for st, c in sorted(agg["amounts_by_stamp"].items())}
    LEDGER.ok((z2_pin[STRIKE_UNITS], tail_pin) == Z2_PIN_RATIO
              and z2_pin[STRIKE_UNITS] > 10 * tail_pin,
              f"and {STRIKE_UNITS} is the overwhelming mode, not merely the "
              f"commonest (10x: JARIN's melee hero took a 2-unit bite for every "
              f"skale swing and doubled the tail on one tape) -- AS OF THE PIN "
              f"(captures before {Z2_PIN_STAMP})",
              f"{z2_pin[STRIKE_UNITS]} at 25 against {tail_pin} below it, EXACT "
              f"{Z2_PIN_RATIO}, outside the {len(DAMAGE_TAPES)} hits-taken tapes; "
              f"the whole corpus today reads {amounts[STRIKE_UNITS]} against "
              f"{tail_total}, and per tape (at 25, below) {per_tape}. "
              f"THIS is the durable form of the count above: a tail that grew "
              f"to rival the strikes would mean the 1%-of-health rule fires far "
              f"more often than a landed hit, and no re-pinning would hide it. "
              f"(It is a fact about HOW THE OWNER PLAYS as much as about the "
              f"wire, which is why a tape made to be hit is named out of it "
              f"rather than allowed to drag a ratio: 20260917T090355 has 26 "
              f"gains and not one 25, because nobody swung -- and CASTAI-Z2: "
              f"{Z2_TAPE} has 229 below 25 against 123, because four Smiting "
              f"Monks tick faster than one axe swings)")
    tail = {a: n for a, n in at_pin.items() if a < STRIKE_UNITS}
    LEDGER.ok(tail == SUB_STRIKE,
              f"and {sum(tail.values())} carry less, as {dict(sorted(tail.items()))}"
              f" -- AS OF THE PIN (captures before {PIN_STAMP})",
              f"expected {SUB_STRIKE}. RE-SCOPED 2026-09-28 (CASTAI-Z1), not "
              f"re-pinned: the Zaishen tape added 43 sub-strike gains and every "
              f"one is a joined damage word (the SIGNATURE check below carries "
              f"the claim past the pin). INFERRED, and labelled that way on "
              f"purpose: GWW's other rule is one unit per 1% of maximum health "
              f"LOST, floored, which produces exactly this kind of small "
              f"ragged tail -- but NOTHING IN THIS CORPUS JOINS THESE TO "
              f"HEALTH TRAFFIC. Until something does, the multiset is the "
              f"measurement and the explanation is not")

    over = {a: n for a, n in at_pin.items() if a > STRIKE_UNITS}
    LEDGER.ok(over == OVER_STRIKE,
              f"NO 207 exceeds {STRIKE_UNITS} units, in {sum(at_pin.values())} "
              f"of them, except the hero's three {OVER_STRIKE} (JARIN) -- AS OF "
              f"THE PIN (captures before {PIN_STAMP})",
              f"{over}, outside the hits-taken tapes. (JARIN called the three "
              f"'summed ticks'; the per-gain join REFUTES that -- each is ONE "
              f"damage word, below.) The STRIKE rule's own "
              f"signature: 25 is the largest single event THAT rule allows, "
              f"and a 50 would mean the server batches strikes. CORRECTED "
              f"2026-09-17: this used to say 25 caps the MESSAGE. It does not "
              f"-- the damage rule has no cap, and one hit for 59.58 % of "
              f"maximum health carries 60 (next check, and 12)")
    LEDGER.ok(0 not in at_pin,
              f"and none carries 0 -- AS OF THE PIN (captures before {PIN_STAMP})",
              "outside the hits-taken tapes. 207 is UNSIGNED throughout -- §9 "
              "reads the add and the clamp -- so it cannot express a loss. "
              "Losses ride 208 and 210. CORRECTED 2026-09-17: this used to add "
              "'a zero would be a message with no effect', as a reason retail "
              "would never send one. Retail sends one for every hit Reversal "
              "of Fortune converts to nothing (next check, and 12)")

    named = {st: dict(agg["amounts_by_stamp"].get(st, {})) for st in DAMAGE_TAPES}
    zeros = {st: c.get(0, 0) for st, c in named.items()}
    LEDGER.ok(named == DAMAGE_TAPES
              and zeros == {st: (ZERO_GRANTS if st == ZERO_GRANT_TAPE else 0)
                            for st in DAMAGE_TAPES},
              f"THE TWO HITS-TAKEN TAPES, pinned whole: {ZERO_GRANTS} zeros on "
              f"{ZERO_GRANT_TAPE} and "
              f"{sorted(a for a in named['20260917T090355'] if a > STRIKE_UNITS)} "
              f"above {STRIKE_UNITS} on 20260917T090355",
              f"{ {st: dict(sorted(c.items())) for st, c in named.items()} }. "
              f"EXACT, because a tape does not grow. RB is the Reversal of "
              f"Fortune run and RB2 the stripped-armour one (studies/skills 48, "
              f"50): the zeros are fully converted hits, the 60 and the 70 are "
              f"single Lightning Orbs, and section 12 joins every one of them "
              f"to the damage word in its own batch. A THIRD tape with a zero "
              f"or an over-25 reddens the two checks above, which is the "
              f"point: name it, say what it is, and do not widen a constant. "
              f"(CASTAI-Z1: the third tape came, and was named by SIGNATURE "
              f"rather than by stamp -- the next three checks)")

    rows = agg["gain_rows"]
    kinds = collections.Counter(r["kind"] for r in rows)
    # CASTAI-Z2: a second kind on the signature, `post_mortem` -- a gain with
    # no word, AFTER the killing word, in the agent's death batch (the rule is
    # in `_classify_gains`; section 3b shows each of its terms refusing). None
    # before the pin, EXACT; the two on the witness tape are pinned by name in
    # the Smiting Monks' check below; a future one is classified, and reported.
    off = [r for r in rows if r["kind"] not in ("damage", "post_mortem")]
    pm = [r for r in rows if r["kind"] == "post_mortem"]
    pm_pin = [r for r in pm if r["stamp"] < Z2_PIN_STAMP]
    # THE KNOWN-BAD ARM: GWW's "floored" in place of round. If the join could
    # only agree, floor would pass too; it must refute some rows.
    floor_miss = [r for r in rows if r["kind"] == "damage"
                  and not any(math.floor(x) == r["units"] for x in r["pcts"])]
    stamps = {r["stamp"] for r in rows}
    LEDGER.ok(not off and not pm_pin and len(rows) >= DAMAGE_RULE_GAINS
              and set(DAMAGE_TAPES) <= stamps and ZAISHEN_TAPE in stamps
              and floor_miss,
              f"THE SIGNATURE: every 207 that is not a {STRIKE_UNITS}, over the "
              f"whole corpus, is ONE damage word at its own agent in its own "
              f"batch, carrying round(% of that agent's current maximum) -- or, "
              f"past {Z2_PIN_STAMP}, a post-mortem gain after the killing word: "
              f"{kinds.get('damage', 0)} + {kinds.get('post_mortem', 0)} of "
              f"{len(rows)}",
              f"kinds {dict(kinds)}; off the signature: "
              f"{[(r['stamp'], r['t'], r['units'], r['kind']) for r in off][:6]}; "
              f"post-mortem before the pin: {len(pm_pin)} (must be 0), after it "
              f"{[(r['stamp'], r['t'], r['units']) for r in pm]}. "
              f"At least {DAMAGE_RULE_GAINS} (a vacuity floor). This is what "
              f"carries 4b's three shape claims past the pin, so a new tape of "
              f"hits taken CONFIRMS rather than reddens -- and it covers both "
              f"named hits-taken tapes (the positive controls), the Zaishen "
              f"tape and the Smiting Monks' tape. KNOWN-BAD ARM: floor(%) in "
              f"place of round misses {len(floor_miss)} of the same rows, so "
              f"the join discriminates. OBSERVED, and it retires SUB_STRIKE's "
              f"'nothing joins these to health traffic': every one of them now "
              f"does")

    jarin = sorted((r["units"], round(max(r["pcts"]), 3)) for r in rows
                   if r["stamp"] == "20260914T005758" and r["units"] > STRIKE_UNITS)
    LEDGER.ok(jarin == JARIN_OVER_WORDS and kinds.get("summed", 0) == 0,
              f"JARIN's three over-25 gains are each ONE damage word, not a "
              f"strike summed with a hit taken: {jarin} as (units, % of max)",
              f"expected {JARIN_OVER_WORDS}; summed gains anywhere in the corpus: "
              f"{kinds.get('summed', 0)}. REFUTES the reading OVER_STRIKE's comment "
              f"gave them ('25 + 1 / + 4 / + 17 ... retail sums the tick'): the "
              f"hero's damage word is 36/140, 41/140 and 51/122 of its maximum, "
              f"and round() of that is the whole gain. The damage rule has no "
              f"cap at {STRIKE_UNITS} (RB2), and this is where it showed first")

    z_conn = {c: dict(n) for (st, c), n in agg["amounts_by_conn"].items()
              if st == ZAISHEN_TAPE}
    z_over = [(r["conn"], r["t"], r["units"]) for r in rows
              if r["stamp"] == ZAISHEN_TAPE and r["units"] > STRIKE_UNITS
              and r["kind"] == "damage" and len(r["pcts"]) == 1]
    z_zero = [(r["conn"], r["t"], r["units"]) for r in rows
              if r["stamp"] == ZAISHEN_TAPE and r["units"] == 0
              and r["kind"] == "damage" and r["pcts"] == [0.0]]
    LEDGER.ok(z_conn == ZAISHEN_207 and sorted(z_over) == ZAISHEN_OVER
              and z_zero == ZAISHEN_ZERO,
              f"THE ZAISHEN TAPE, pinned whole: {len(z_conn)} connections, five "
              f"over-25 gains {sorted(u for _c, _t, u in z_over)} and one zero, "
              f"each ONE damage word",
              f"{z_conn}. EXACT, per connection (a tape does not grow; the gapped "
              f"match-2 connection is set aside by its manifest). The 33s and the "
              f"36 are armour-ignoring property-55 words from an Obsidian Flame "
              f"(2809) cast at the observer 1.5 s before; the zero is a +0.0 hit "
              f"under the observer's Reversal of Fortune (307) -- RB's mechanism "
              f"on a second tape. OBSERVED, CASTAI-Z1")

    # CASTAI-Z2: THE SMITING MONKS' TAPE, pinned whole and ONLY on itself --
    # every filter here is `== Z2_TAPE`, so the same rows under a later stamp
    # change nothing in this check (they are classified by the signature).
    z2_conn = {c: dict(n) for (st, c), n in agg["amounts_by_conn"].items()
               if st == Z2_TAPE}
    z2_pm = sorted((r["conn"], r["t"], r["units"]) for r in rows
                   if r["stamp"] == Z2_TAPE and r["kind"] == "post_mortem")
    z2_kinds = dict(agg["gain_kinds"].get(Z2_TAPE, {}))
    LEDGER.ok(z2_conn == Z2_207 and z2_pm == Z2_POST_MORTEM
              and z2_kinds == Z2_KINDS,
              f"THE SMITING MONKS' TAPE, pinned whole: {len(z2_conn)} connections, "
              f"{z2_kinds} -- the tail outnumbers the strikes, and its two "
              f"post-mortem gains are {[(c.split('->')[0].rsplit(':', 1)[-1], t, u) for c, t, u in z2_pm]} "
              f"as (port, t, units)",
              f"{z2_conn}. EXACT, per connection (a tape does not grow). The "
              f"229 below 25 are four Monk AI's Balthazar's Aura ticks (27 of "
              f"480 -> 6; 46 -> 10), Zealot's Fire (22 -> 5; 38 -> 8), Smite "
              f"Hex (75 -> 16; 129 -> 27) and 3-point wand hits (-> 1) on the "
              f"owner's Warrior; the five over 25 are four Smite Hexes (129 "
              f"points: 26.875 % at 480, 27.68 % at 466, 30.86 % at 418) and "
              f"one Scourge Healing (122 at 427 -> 29). The two post-mortem gains sit "
              f"in the observer's death batch AFTER the killing word with no "
              f"word of their own: 6 is monk 4's aura tick (its visual 487 "
              f"immediately ahead; 5.625 % on this observer, 3 of 3 elsewhere "
              f"on :51090 -- OBSERVED) and 16 is one Smite Hex at 480 (no visual "
              f"names its source -- RECONSTRUCTION). Retail sends the gain and "
              f"drops the word for a hit that lands on an agent already dead in "
              f"the same tick; the 13 killing words in the corpus are all "
              f"present and unclamped. OUR SERVER sends neither for a dead "
              f"player (`player_dead` at the grant sites) -- escalated, not "
              f"edited")


def section_self_scope(agg):
    """SELF-SCOPED, and this is the check that refuted a wrong reading.

    An earlier draft of this finding claimed retail broadcasts 207 for other
    agents' bars, on the strength of seeing agent ids 7, 11, 13 and 25 across
    the corpus. Those are four SESSIONS, not four agents: no single connection
    ever names more than one. The control is the half that makes it mean
    something -- the SAME connections carry 9 to 24 distinct agents on the
    property channel, so "one agent" is a property of opcode 207 and not of a
    thin capture.
    """
    print("\n5. WHOSE bar -- and the control that makes it a finding")
    rows = agg["self_scope"]
    # A floor, for the reason the constant block gives: this counts how much
    # corpus there is, not what 207 does. The finding is the check BELOW -- every
    # one of these connections names exactly one agent -- and that is an `all()`
    # over whatever rows exist, so it gets sharper as the corpus grows while this
    # number simply gets bigger. It reddened at 11 -> 12 with nothing changed.
    LEDGER.ok(len(rows) >= SELF_SCOPED_CONNECTIONS,
              f"at least {SELF_SCOPED_CONNECTIONS} connections carry a 207 at "
              f"all",
              f"{len(rows)} of {agg['connections']} today. The floor is a "
              f"vacuity guard: the one-agent check below is an all() and would "
              f"pass an empty set")
    multi = [(s, a) for s, a, _b in rows if len(a) != 1]
    LEDGER.ok(not multi,
              f"and every one of them names EXACTLY ONE agent, {len(rows)} of "
              f"{len(rows)}",
              f"{[(s, a) for s, a, _b in rows]}. Multi-agent connections: "
              f"{multi}. The ids 7/11/13/25 across the corpus are four "
              f"SESSIONS, not four agents -- which is the reading this check "
              f"refuted")
    mismatched = [(s, a, b) for s, a, b in rows if not set(a) <= set(b)]
    LEDGER.ok(not mismatched and any(len(b) > 1 for _s, _a, b in rows),
              f"and that agent holds one of the connection's SKILLBAR_UPDATE bars, "
              f"{len(rows)} of {len(rows)} -- the observer's, or a HERO's (JARIN: "
              f"the Ranger's bar had no adrenal skill and every 207 on that tape "
              f"named the hero, whose 0x00DA the same connection carries)",
              f"opcode {SMSG_SKILLBAR_UPDATE} carries the bar whose slots 207 "
              f"charges, so the two have to name the same agent or the client "
              f"would be filling a bar it was never sent. Mismatches: "
              f"{mismatched}. Adrenaline is scoped exactly like energy "
              f"property 62 -- `test_pools` §2d, 0 of 722 casts by other "
              f"agents -- and a server that broadcast our own enemies' "
              f"adrenaline would be sending messages retail never sends")

    spread = agg["prop_spread"]
    LEDGER.ok(spread and min(spread) > 1,
              f"CONTROL: those SAME connections carry {min(spread)} to "
              f"{max(spread)} distinct agents on the property channel",
              f"{sorted(spread)}. Without this, 'one agent' would be equally "
              f"explained by a capture that only ever saw one agent. It is "
              f"not: the same streams are full of other agents' traffic, and "
              f"only this family is scoped to the observer")


def section_spend_join(agg):
    """THE SPEND JOIN: retail only ever spends adrenaline on adrenal skills."""
    print("\n6. what a 210 spends on, against the client's own cost column")
    import content
    world = content.load()

    # PER-SKILL FLOORS. The exact multiset was a size pin: every new capture that
    # spends adrenaline moves one of these counts. What must not happen is a
    # known spender going MISSING, and what a new skill appearing means is
    # settled by the zero-cost check immediately below -- which is the actual
    # join to content, and which gets sharper as the corpus grows.
    LEDGER.ok(all(agg["spend_skills"].get(k, 0) >= v
                  for k, v in SPEND_SKILLS.items()),
              f"the {sum(agg['spend_skills'].values())} spends name "
              f"{dict(sorted(agg['spend_skills'].items()))}",
              f"at least {SPEND_SKILLS}. A floor per skill: growth moves these "
              f"counts and that is the campaign working; a SHORTFALL would mean "
              f"the join stopped seeing a spender it used to see")

    zero_cost, used, costs = [], {}, {}
    for skill, n in agg["spend_skills"].items():
        # CASTAI-Z1: a spend skill content lacks is resolved by skill_row's
        # STATED RULE (a PvP-only split of a player skill, read from the
        # capture's own build), never by a blanket except -- the Zaishen tape
        # spends on 2858, the PvP split of 348, and content holds 348 only.
        costs[skill] = int(skill_row(world, skill, agg["spend_builds"][skill],
                                     used)["adrenaline_units"])
        if not costs[skill]:
            zero_cost.append((skill, n))
    # The rule's uses PER CAPTURE (CASTAI-Z1 review, R3 / SLICE-F47). The
    # corpus-wide claim is the SIGNATURE skill_row enforces above -- a spend
    # skill content lacks resolves ONLY as a pvp_only, equip_family 0 split
    # whose linked_id is a content row, else MissingRow crashes this unguarded
    # loop. What is pinned EXACT is the witness, on its own tape; before the
    # pin the rule must never have been needed. A later tape that spends a
    # different PvP split is confirming evidence and must not redden this.
    used_at = {}                # (stamp, skill) -> (build, linked_id)
    for (st, sk), builds in agg["spend_stamp_builds"].items():
        one = {}
        skill_row(world, sk, builds, one)
        if sk in one:
            used_at[(st, sk)] = one[sk]
    z_used = {sk: bl for (st, sk), bl in used_at.items() if st == ZAISHEN_TAPE}
    pre_used = sorted((st, sk) for (st, sk) in used_at if st < PIN_STAMP)
    LEDGER.ok(z_used == {s: (38888, link) for s, link in PVP_SPENDS_WITNESS.items()},
              f"the spend skill content lacks on {ZAISHEN_TAPE} is a PvP split, "
              f"by the stated rule: {z_used} as skill -> (build, the player "
              f"skill it splits off)",
              f"expected {PVP_SPENDS_WITNESS} on build 38888, EXACT on the "
              f"witness tape (CASTAI-Z1: the Zaishen Challenge plays PvP "
              f"versions). Past this tape the claim is skill_row's signature, "
              f"not a list; the rule's uses over the corpus: "
              f"{sorted(used_at.items())}")
    LEDGER.ok(not pre_used,
              f"and before the pin no spend needed the rule: every spend on a "
              f"capture before {PIN_STAMP} resolves from content",
              f"rule uses before the pin: {pre_used}. The player corpus held "
              f"every pre-Zaishen spender, so a rule use there would mean the "
              f"content table lost a row")
    LEDGER.ok(not zero_cost,
              "and every one of them carries a NONZERO adrenaline cost",
              f"{costs}"
              f" as skill -> raw units. Zero-cost spends: {zero_cost}. Two "
              f"independent things had to agree: which skills retail chose to "
              f"send a 210 for, and which skills the client's own table gives "
              f"a cost. Neither was fitted to the other")

    free, free_skills, unresolved = 0, set(), set()
    for skill, n in agg["cast_skills"].items():
        try:
            units = int(skill_row(world, skill, agg["cast_builds"][skill])
                        ["adrenaline_units"])
        except MissingRow:
            unresolved.add(skill)   # named and asserted just below
            continue            # an NPC's own skill: no player bar holds it

        if not units:
            free += n
            free_skills.add(skill)
    LEDGER.ok(free >= 700 and len(free_skills) >= 40,
              f"CONTROL: the same lookup over everything CAST finds {free} "
              f"casts of {len(free_skills)} ZERO-adrenaline skills",
              f"out of {sum(agg['cast_skills'].values())} activations of "
              f"{len(agg['cast_skills'])} skills. So the join above "
              f"discriminates: the corpus is full of skills that would fail "
              f"it, and none of them ever gets a 210. A join that could only "
              f"pass is not a join")

    # WHICH cast ids the control drops (R8, CASTAI-Z1 review): as of the pin
    # EXACTLY UNRESOLVED_CASTS_AT_PIN, and every one, before or after it, has a
    # row in its own build's client table OUTSIDE the player corpus -- the
    # stated reason the player-corpus content lacks it.
    un_at_pin = {sk for sk in unresolved
                 if any(st < PIN_STAMP for st in agg["cast_stamps"][sk])}
    unexplained = sorted(sk for sk in unresolved
                         if not outside_player_corpus(sk, agg["cast_builds"][sk]))
    LEDGER.ok(un_at_pin == UNRESOLVED_CASTS_AT_PIN and not unexplained,
              f"the control drops only ids outside the player corpus: "
              f"{sorted(unresolved)} over the corpus, {sorted(un_at_pin)} as of "
              f"the pin",
              f"expected {sorted(UNRESOLVED_CASTS_AT_PIN)} before {PIN_STAMP}, "
              f"EXACT. Unexplained (a row inside the player corpus, or none): "
              f"{unexplained}. skilltable.player_corpus is the extractor's own "
              f"membership rule, so this states why content lacks them")

    # AGAINST THE MEASURED CENSUS, not against CENSUS[...]. That constant became
    # a FLOOR on 2026-08-27 and this site was still reading it as an exact
    # expected value -- the same number meaning two different things three
    # hundred lines apart, and green only because the corpus had not grown since.
    # The claim is "0 in ALL of them", so the denominator has to be whatever
    # section 4 actually counted.
    at_pin = collections.Counter()
    for st, pairs in agg["spend_pairs_by_stamp"].items():
        if st < PIN_STAMP:
            for (_sk, copy), n in pairs.items():
                at_pin[copy] += n
    n_spend = sum(at_pin.values())
    LEDGER.ok(dict(at_pin) == {0: n_spend} and n_spend >= CENSUS[SMSG_ADRENALINE_SPEND],
              f"and skill_copy is 0 in all {n_spend} -- AS OF THE PIN (captures "
              f"before {PIN_STAMP})",
              f"{dict(at_pin)}; the whole corpus reads {dict(agg['spend_copies'])} "
              f"(the next check). §9 reads the worker matching a "
              f"slot on the PAIR (skillId, skillCopy), so the field is real "
              f"and load-bearing -- but ordinary play never exercises it "
              f"(studies/skillcast §3). A sender may emit 0 and a receiver "
              f"must still match on both, which is the asymmetry worth writing "
              f"down")

    # CASTAI-Z1: past the pin the claim is carried by a SIGNATURE -- a spend of a
    # skill content holds (the player corpus) carries 0; a spend of a PvP split
    # (skill_row's rule, `used`) carries 0xFFFFFFFF -- with the tape pinned whole.
    pairs = collections.Counter()
    for st, c in agg["spend_pairs_by_stamp"].items():
        pairs.update(c)
    player = {k: n for k, n in pairs.items() if k[0] not in used}
    split = {k: n for k, n in pairs.items() if k[0] in used}
    LEDGER.ok(all(copy == 0 for _sk, copy in player)
              and all(copy == 0xFFFFFFFF for _sk, copy in split)
              and dict(agg["spend_pairs_by_stamp"].get(ZAISHEN_TAPE, {}))
              == ZAISHEN_SPEND_PAIRS,
              f"NEW: a PvP split's spend carries skill_copy 0xFFFFFFFF -- "
              f"{ {(sk, hex(c)): n for (sk, c), n in split.items()} } -- while "
              f"every player-corpus spend still carries 0 "
              f"({sum(player.values())} of them)",
              f"{ZAISHEN_TAPE} pinned whole: "
              f"{ {(sk, hex(c)): n for (sk, c), n in agg['spend_pairs_by_stamp'].get(ZAISHEN_TAPE, {}).items()} }. "
              f"OBSERVED (CASTAI-Z1), n = one skill: the Zaishen Challenge "
              f"spends only 2858, so whether -1 marks the PvP split or the arena "
              f"is not separable here, and what the client does with it is NOT "
              f"FOUND. Our server emits 0 and runs no PvP versions, so nothing "
              f"it sends is contradicted")


def section_order(agg):
    """THE ORDER, which the server build needs and the corpus answers.

    `test_pools` §2c had to measure this for energy and got it wrong first:
    property 62 leads the property-60 that names the skill, so attributing a
    spend to the last cast ALREADY SEEN scored 18 of 45. Adrenaline is the same
    shape and this pins it before anybody builds the sender.
    """
    print("\n7. does the spend lead its own activation, or follow it?")
    order = agg["order"]
    total = sum(order.values())
    # Same repair as §6: the denominator is section 4's MEASURED spend count,
    # not the floor constant. "ALL spends have an activation" is a relation
    # between two things this file measures, and it stays exact forever.
    LEDGER.ok(total == agg["census"][SMSG_ADRENALINE_SPEND],
              f"all {total} spends have a same-batch activation naming the "
              f"same skill for the same agent",
              f"{dict(order)} as (stream delta, property id) -> n. Joined on "
              f"BOTH adjacency and simultaneity, so a coincidence has to "
              f"satisfy two conditions")
    # THE FOLLOWER IS NOT ALWAYS PROPERTY 50, and this check said it was until
    # 2026-08-21. It asserted `set(order) == {(1, 50)}` -- delta exactly +1, and
    # "never 48 or 60" in its own detail string -- on a corpus whose every spend
    # was a sword ATTACK skill. Our own live capture (20260821T205552) spent
    # skill 348, a SELF-TARGETED adrenal skill, and it follows with property 48
    # (instant_skill_activated) at delta +2. The claim that survives is the one
    # the sender actually needs, and it is unbroken 40 of 40: THE SPEND COMES
    # FIRST. Which property announces the cast, and how many messages behind,
    # depends on the kind of skill -- an attack skill takes 50, an instant takes
    # 48 -- so the sender must not key on the follower's identity.
    #
    # Worth keeping as the shape of the error: the old assertion was true of
    # every observation it had and false about the protocol, and the thing that
    # exposed it was one capture of a deliberately DIFFERENT kind of skill.
    LEDGER.ok(all(delta >= 1 for delta, _prop in order)
              and set(p for _d, p in order) <= {PROP_ATTACK_SKILL_ACTIVATED, 48},
              f"and the 210 comes FIRST in every case, by one message or two, "
              f"{total} of {total}",
              f"{dict(order)} -- delta +1 in every case, and the follower is "
              f"always property {PROP_ATTACK_SKILL_ACTIVATED} "
              f"(attack_skill_activated), never 48 or 60. THE ANSWER FOR THE "
              f"SENDER: emit the 210, then the activation, in that order and "
              f"in the same batch. It is the same ordering the energy channel "
              f"uses -- property 62 then property 60 -- so 'the cost is "
              f"debited before the cast is announced' is a rule of this "
              f"protocol and not a quirk of one opcode")


# ---------------------------------------------------------------------------
# 8-11: the pinned build-38797 image. READ-ONLY, never launched.


class Image:
    """The pinned client's bytes. Same shape as `clientscan/genericvalue.py`'s.

    `pinned.find()` VERIFIES the digest and refuses an unknown build -- which is
    the whole point here, because every VA above was measured on 38797 and on
    another build they do not error, they read whatever else is mapped there and
    return a confident wrong number.
    """

    def __init__(self):
        import pinned
        from gwpe import PE
        self.path, self.why = pinned.find()
        self.pe = PE(self.path)
        self.base = self.pe.image_base

    def read(self, va, n):
        off = self.pe.rva_to_off(va - self.base)
        if off is None:
            raise ValueError(f"0x{va:08x} is not backed by file bytes")
        return self.pe.data[off:off + n]

    def u32(self, va):
        return struct.unpack("<I", self.read(va, 4))[0]

    def f32(self, va):
        return struct.unpack("<f", self.read(va, 4))[0]

    def rel32_target(self, va):
        """The absolute target of the `call`/`jmp rel32` whose opcode is at va."""
        disp = struct.unpack("<i", self.read(va + 1, 4))[0]
        return (va + 5 + disp) & 0xFFFFFFFF

    def first_call(self, va, span=48, skip=0):
        """The (skip+1)-th `call rel32` in [va, va+span), as an absolute target."""
        d = self.read(va, span)
        i, seen = 0, 0
        while True:
            i = d.find(b"\xe8", i)
            if i < 0:
                return None
            target = self.rel32_target(va + i)
            if seen == skip:
                return target
            seen, i = seen + 1, i + 1


def section_dispatch(img, declared):
    """THE CHAIN, walked as arithmetic rather than compared with itself.

    Four descriptors at a 12-byte stride, each (type_array_ptr, field_count,
    handler). The type array's first dword IS the opcode, and the four run
    0xCF, 0xD0, 0xD1, 0xD2 in order -- so the descriptor this file names is
    proved to be 207's by the image and not by our labelling of it. Each
    handler is a stub whose rel32 lands on a thunk whose rel32 lands on the
    worker. A wrong address produces a wrong sum, which is what makes this
    refutable.

    TOOL PROVENANCE, and it costs time to rediscover: `msghandler.py --table`
    prints the STATIC type array, which for 0xCF is ['0xcf','0x0','0x0'] --
    slots 1..n are filled by an MSVC load-time initializer. The RECOVERED shape
    ['0xcf','0x10','0x404'] is `msgshape.py`'s, after that recovery. Cite
    msgshape for any recovered shape, never msghandler. Only the first dword
    and the count are static, and those are the two this section reads.
    """
    print("\n8. the dispatch chain, from the descriptor table to the workers")
    print(f"   client: {img.path}")
    print(f"           ({img.why})")

    opcodes = []
    for k, op in enumerate(FAMILY):
        va = VA_DESCRIPTOR_CF + k * DESCRIPTOR_STRIDE
        opcodes.append(img.u32(img.u32(va)))
    LEDGER.ok(opcodes == list(FAMILY),
              f"the four descriptors at 0x{VA_DESCRIPTOR_CF:08X} declare "
              f"opcodes {[hex(o) for o in opcodes]}, in order",
              f"each record is (type_array_ptr, field_count, handler) at a "
              f"{DESCRIPTOR_STRIDE}-byte stride, and the type array's first "
              f"dword is the opcode itself. This is what makes "
              f"0x{VA_DESCRIPTOR_CF:08X} 207's descriptor rather than an "
              f"address we decided to call that -- and a stride or a base off "
              f"by one lands on a different opcode, not on a near miss")

    counts = {op: img.u32(VA_DESCRIPTOR_CF + k * DESCRIPTOR_STRIDE + 4)
              for k, op in enumerate(FAMILY)}
    agree = all(counts[op] == declared[op][1] for op in FAMILY)
    LEDGER.ok(agree,
              "and their FIELD COUNTS agree with schema/messages.json, 4 of 4",
              f"{ {hex(o): counts[o] for o in FAMILY} } against "
              f"{ {hex(o): declared[o][1] for o in FAMILY} }. TWO WITNESSES "
              f"THAT ARE NOT ONE: the schema came from the message-catalog "
              f"importer and this came from the image, so either could refute "
              f"the other and neither was fitted to it")

    resolved = {}
    for k, op in enumerate(FAMILY):
        stub = img.u32(VA_DESCRIPTOR_CF + k * DESCRIPTOR_STRIDE + 8)
        thunk = img.first_call(stub, span=32)
        # The 210 thunk calls the context getter, then ArenaNet's assert
        # helper, then the worker; the other three have no assert. Taking the
        # LAST call in the thunk's prologue window is what makes one rule work
        # for all four.
        targets = []
        d = img.read(thunk, 48)
        i = 0
        while True:
            i = d.find(b"\xe8", i)
            if i < 0:
                break
            targets.append(img.rel32_target(thunk + i))
            i += 1
        resolved[op] = (stub, thunk, [t for t in targets if t in WORKERS.values()])
    hit = {op: (v[2][0] if v[2] else None) for op, v in resolved.items()}
    LEDGER.ok(hit == WORKERS,
              "and stub -> thunk -> worker resolves to all four workers",
              f"{ {hex(o): (hex(v[0]), hex(v[1])) for o, v in resolved.items()} }"
              f" as opcode -> (stub, thunk), reaching "
              f"{ {hex(o): hex(w) for o, w in hit.items() if w} }. Every "
              f"link is one rel32 displacement resolved to an absolute "
              f"address, and every link has exactly ONE caller, so there is no "
              f"branch here to have read the wrong way")

    same_container = []
    for op, (_stub, thunk, _t) in resolved.items():
        d = img.read(thunk, 48)
        # mov ecx,[eax+0x2c] ; add ecx, 0x6F0 -- the hotKeyState container
        same_container.append(b"\x8b\x48\x2c" in d
                              and struct.pack("<BBI", 0x81, 0xC1,
                                              VA_HOTKEY_CONTAINER_DELTA) in d)
    LEDGER.ok(all(same_container),
              f"and all four thunks address the SAME container, "
              f"[ctx+0x2c] + 0x{VA_HOTKEY_CONTAINER_DELTA:03X}",
              f"{same_container}. It is the same container "
              f"0x{VA_DISPLAY_ACCESSOR:08X}'s caller loads for the DISPLAY "
              f"(§10), which is what ties the four messages and the icon to "
              f"one store rather than to two that happen to look alike")


def section_workers(img):
    """THE THREE STORES, and the identity the charge loop has to satisfy."""
    print("\n9. what each worker writes")

    LEDGER.ok(img.read(VA_CHARGE_STORE, 2) == b"\x89\x0e",
              f"207's charge store at 0x{VA_CHARGE_STORE:08X} is "
              f"`mov [esi],ecx`",
              "the ONLY arithmetic write to a slot's +0x00 anywhere in the "
              "image. Everything else that touches that dword either zeroes it "
              "(208, 210) or sets it absolutely (209), so this instruction is "
              "the accumulator, singular")

    end = img.read(VA_CHARGE_END, 6)          # lea ebx,[eax+0xa4]
    first = img.read(VA_CHARGE_FIRST, 3)      # lea esi,[eax+4]
    stride = img.read(VA_CHARGE_STRIDE, 3)    # add esi,0x14
    shapes = (end == b"\x8d\x98" + struct.pack("<I", SLOT_END_OFF)
              and first == b"\x8d\x70" + bytes([SLOT_FIRST_OFF])
              and stride == b"\x83\xc6" + bytes([SLOT_STRIDE]))
    LEDGER.ok(shapes and SLOT_FIRST_OFF + SLOT_COUNT * SLOT_STRIDE == SLOT_END_OFF,
              f"and its loop bounds satisfy {SLOT_FIRST_OFF} + {SLOT_COUNT} x "
              f"0x{SLOT_STRIDE:02X} == 0x{SLOT_END_OFF:02X}",
              f"first {first.hex()}, stride {stride.hex()}, end {end.hex()}. "
              f"THREE INDEPENDENT IMMEDIATES from three separate instructions "
              f"that have to close on exactly {SLOT_COUNT} slots -- the number "
              f"of slots a Guild Wars skill bar has. Nothing here forces that: "
              f"a misread stride or a misread bound gives a non-integer count")

    LEDGER.ok(img.read(VA_CHARGE_THRESH, 4) == b"\x0f\xb7\x48\x38",
              f"the threshold at 0x{VA_CHARGE_THRESH:08X} is "
              f"`movzx ecx,word [eax+0x38]`",
              "the skill row's own +0x38, which §11 shows ArenaNet's asserts "
              "calling `skillData.adrenaline` at two independent sites. A "
              "zero there SKIPS the slot, so 207 charges adrenal skills and "
              "silently ignores everything else on the bar")
    LEDGER.ok(img.read(VA_CHARGE_ADD, 7) == b"\x8b\x06\x03\x45\x0c\x3b\xc8",
              f"and the arithmetic is `[esi] + [ebp+0xc]`, then clamped to the "
              f"cost",
              f"{img.read(VA_CHARGE_ADD, 9).hex(' ')} -- mov eax,[esi] / add "
              f"eax,[ebp+0xc] / cmp ecx,eax / jb / mov ecx,eax. [ebp+0xc] is "
              f"the MESSAGE's second field, so 207 is a DELTA and the clamp "
              f"is min(cost, current + units). Unsigned, so it cannot express "
              f"a loss -- which is §4b's `no amount is 0` from the other side")

    operand = img.u32(VA_FLD_25F + 2)
    LEDGER.ok(img.read(VA_FLD_25F, 2) == b"\xd9\x05"
              and operand == VA_25F_CONST
              and img.f32(VA_25F_CONST) == 25.0,
              f"the UI event loads a FIXED 25.0f from .rdata "
              f"0x{VA_25F_CONST:08X}, not the message's amount",
              f"fld operand 0x{operand:08X}, value {img.f32(VA_25F_CONST)!r}, "
              f"bytes {img.read(VA_25F_CONST, 4).hex()}. Read closely: the "
              f"handler adds the MESSAGE's units to the slot and then hands "
              f"the UI a constant. So the '25' in the animation is not the "
              f"'25' on the wire, and a 3-unit gain and a 25-unit gain "
              f"produce the same flash -- which is why §4b's tail is invisible "
              f"on screen and had to be found in the bytes")

    LEDGER.ok(img.read(VA_CLEAR_BOTH, 10)
              == b"\xc7\x00\x00\x00\x00\x00\xc7\x40\x04\x00",
              f"208 zeroes BOTH halves of every slot at "
              f"0x{VA_CLEAR_BOTH:08X}",
              f"{img.read(VA_CLEAR_BOTH, 13).hex(' ')} -- mov dword [eax],0 / "
              f"mov dword [eax+4],0. This is death and the 25-second "
              f"out-of-combat wipe, and it repaints immediately rather than "
              f"waiting on the deferred queue")
    LEDGER.ok(img.read(VA_SET_BOTH, 5) == b"\x89\x01\x89\x41\x04",
              f"209 writes the message's units to BOTH halves at "
              f"0x{VA_SET_BOTH:08X}",
              f"{img.read(VA_SET_BOTH, 8).hex(' ')} -- mov [ecx],eax / mov "
              f"[ecx+4],eax. Fully implemented, matches one slot on the "
              f"(skillId, skillCopy) pair, repaints at once -- and sent 0 "
              f"times in {CORPUS_MESSAGES} messages")

    LEDGER.ok(img.read(VA_SPEND_25, 3) == b"\x83\xfe" + bytes([SPEND_STRIKE])
              and img.read(VA_SPEND_25 + 3, 2) == b"\x76\x05"
              and img.read(VA_SPEND_25 + 5, 3) == b"\x83\xc6"
                                                 + bytes([(-SPEND_STRIKE) & 0xFF]),
              f"210 takes 0x{SPEND_STRIKE:02X} (= {SPEND_STRIKE}) off every "
              f"OTHER occupied slot, flooring at zero",
              f"{img.read(VA_SPEND_25, 10).hex(' ')} -- cmp esi,0x19 / jbe -> "
              f"0 / add esi,-0x19. GWW's on-use rule word for word: the skill "
              f"used goes to zero and every other adrenal skill loses ONE "
              f"STRIKE. And note it decrements RAW UNITS by 25, which is only "
              f"coherent because §3 shows the costs are not on a 25 grid")
    LEDGER.ok(img.read(VA_SPEND_PAIRLOOP, 3) == b"\x83\xf9\x02",
              f"and it does that to both halves -- a 2-iteration inner loop "
              f"at 0x{VA_SPEND_PAIRLOOP:08X}",
              f"{img.read(VA_SPEND_PAIRLOOP, 5).hex(' ')} -- cmp ecx,2 / jne "
              f"back. Both halves again, so like 209 it repaints without "
              f"waiting for the a->b commit")


def section_display(img):
    """THE DISPLAY DRAWS FROM +0x04, AND PLAN.md SAYS +0x00. This is the fix.

    GWCA names the slot's first dword `adrenaline_a` and PLAN.md line ~1384
    called it "the store the icon draws from". It is not. The accessor
    0x00821050 -- reached only through the ChCliApi wrapper 0x00816EF0, which
    has EXACTLY ONE caller image-wide, GmSkSlot 0x00542E78 -- indexes
    `container + slot*0x14 + 8`, and the charge loop indexes
    `container + slot*0x14 + 4`. Four and eight, from two different functions,
    with the same stride. The icon reads the SECOND dword.

    That makes the pair a DEFERRED-COMMIT DOUBLE BUFFER: +0x00 accumulates and
    the deferred task copies it to +0x04, which is the only half any accessor
    exposes. Py4GW_Reforged reading `adrenaline_a` as the live value is ALSO
    right -- a bot wants the accumulator and the screen shows the committed
    copy. Complementary, not contested.

    THE MAP GATE is the half that changes probe design: the fill is drawn only
    when the map state is MISSION_MAP_GAME, and is actively torn down otherwise.
    A perfectly correct 207 sent to a client sitting in an OUTPOST yields a
    pixel-identical icon, so any probe must be in an explorable or a mission.
    """
    print("\n10. WHICH half the icon draws from -- and when it draws at all")

    LEDGER.ok(img.first_call(VA_SLOT_CALL, span=8) == VA_DISPLAY_WRAPPER,
              f"GmSkSlot 0x{VA_SLOT_CALL:08X} calls ChCliApi "
              f"0x{VA_DISPLAY_WRAPPER:08X}",
              f"resolved from the rel32, "
              f"{img.read(VA_SLOT_CALL, 5).hex(' ')}")
    LEDGER.ok(img.read(VA_ACCESSOR_INDEX, 7)
              == b"\x8d\x04\xb6\x8b\x44\x87" + bytes([ACCESSOR_DISP]),
              f"and the accessor indexes container + slot*0x{SLOT_STRIDE:02X} "
              f"+ {ACCESSOR_DISP}, NOT + {SLOT_FIRST_OFF}",
              f"{img.read(VA_ACCESSOR_INDEX, 7).hex(' ')} -- lea "
              f"eax,[esi+esi*4] (slot * 5) then mov eax,[edi+eax*4+8] (x4, so "
              f"slot * 0x14, + 8). THE CORRECTION THIS BUILD OWES: PLAN.md "
              f"called `adrenaline_a` (+0x00) the store the icon draws from. "
              f"It is +0x04. Two functions, two displacements, one stride -- "
              f"and §9's charge loop starting at +{SLOT_FIRST_OFF} is what "
              f"makes {ACCESSOR_DISP} the SECOND dword rather than the first")
    LEDGER.ok(img.read(VA_ACCESSOR_BOUND, 3) == b"\x83\xfe"
              + bytes([SLOT_COUNT]),
              f"and it bounds-checks the slot index against {SLOT_COUNT}",
              f"{img.read(VA_ACCESSOR_BOUND, 5).hex(' ')} -- cmp esi,8 / jb. "
              f"The SAME eight slots §9's loop closes on arithmetically, "
              f"reached from a different function by a different route")
    LEDGER.ok(img.read(VA_SLOT_THRESH, 4) == b"\x0f\xb7\x46\x38",
              f"and the threshold it divides by is the skill row's +0x38, read "
              f"as a WORD",
              f"{img.read(VA_SLOT_THRESH, 6).hex(' ')} -- movzx eax,word "
              f"[esi+0x38], the same field §9's charge loop tests. The pair "
              f"goes to Controls::SkillImage, which DIVIDES them and forwards "
              f"the fraction: no /25 and no quarter quantisation anywhere. The "
              f"bar is a continuous fraction of the RAW cost, which is the "
              f"other reason §3's off-grid costs are not a problem for the "
              f"client")

    target = img.rel32_target(VA_MAP_GATE_CALL)
    LEDGER.ok(target == VA_MISSION_CLI_GET_MAP
              and img.read(VA_MAP_GATE_CMP, 3)
                  == b"\x83\xf8" + bytes([MISSION_MAP_GAME])
              and img.read(VA_MAP_GATE_CMP + 3, 1) == b"\x75",
              f"THE MAP GATE: the fill is drawn only when the map state is "
              f"MISSION_MAP_GAME (== {MISSION_MAP_GAME})",
              f"call 0x{VA_MAP_GATE_CALL:08X} -> 0x{target:08X} "
              f"(MissionCliGetMap), then cmp eax,1 / jne. MISSION_MAP_OUTPOST "
              f"is 0 (QuestLog:261) and MISSION_MAP_GAME is 1 (MsCliApi:251). "
              f"Off that path the overlay is TORN DOWN with a NULL payload, "
              f"not merely left stale -- so a perfectly correct 207 sent while "
              f"the client sits in an outpost yields a PIXEL-IDENTICAL icon. "
              f"Any probe of this family has to be in an explorable or a "
              f"mission, and a null from an outpost run means nothing")


def section_arenanet_words(img):
    """ARENANET'S OWN IDENTIFIERS, four sites, each cited as one measurement.

    CLAUDE.md's boundary: a SINGLE assert cited as the evidence for a claim is a
    measurement and is kept with its file and line; a bulk dump is expression
    and is refused. These four are the difference between "we called this
    adrenaline" and "the client calls this adrenaline".
    """
    print("\n11. what ArenaNet's own asserts call this")
    import asserts
    a = asserts.Asserts(img.path)

    found = {s.va: s for s in a.grep(r"(?i)adrenaline")}
    found.update({s.va: s for s in a.near(VA_SPEND_WORKER, span=0x120)})
    for va, (module, line, expr) in ASSERTS.items():
        s = found.get(va)
        LEDGER.ok(s is not None and s.module == module and s.line == line
                  and s.expr.strip("'") == expr,
                  f"0x{va:08X} is {module}:{line} '{expr}'",
                  f"got {s!r}" if s else "NOT FOUND at that address")

    LEDGER.ok(len({(v[0], v[1]) for v in ASSERTS.values()
                   if v[2].startswith("!(energyCost")}) == 2,
              "and `skillData.adrenaline` is ArenaNet's name for +0x38 at TWO "
              "independent sites",
              "GmCtlSkCard:409 and GmCtlSkListEntry:185, both guarding a "
              "`cmp word [reg+0x38],0`. Two separate source files reaching the "
              "same field with the same identifier is what promotes "
              "`clientscan/skilltable.py`'s `adrenaline_units` decode from our "
              "name for the column to the client's own")
    LEDGER.ok(ASSERTS[0x00820DEB][1] == 84
              and img.read(VA_DEFERRED_TASK, 3) == b"\x55\x8b\xec"
              and 0x00820DEB - VA_DEFERRED_TASK < 0x40,
              f"and ChCliSkill:84 sits inside the deferred task at "
              f"0x{VA_DEFERRED_TASK:08X}",
              f"`context->skillAdrenalineUpdateArray.Count()`, "
              f"0x{0x00820DEB - VA_DEFERRED_TASK:X} bytes into the function's "
              f"prologue. So the queue 207 appends to and this task drains is "
              f"named ADRENALINE by the client itself -- which is the "
              f"strongest single piece of evidence that the whole chain is "
              f"what this file says it is, and it is one quotation rather "
              f"than a dump")

    LEDGER.ok(len(a.grep(r"(?i)adrenaline")) >= 4,
              f"POSITIVE CONTROL: the scan reads "
              f"{len(a.grep(r'(?i)adrenaline'))} adrenaline asserts in total",
              "`asserts.py` says its own counts are a FLOOR -- it is short by "
              "373 sites it cannot read -- so 'no assert names X' is never a "
              "census here. That cuts one way only: what it DOES find is real, "
              "and this check is what says the scan ran at all")


# ---------------------------------------------------------------------------


def section_bar_gate(agg):
    """THE FAMILY IS DARK FOR A BAR THAT CANNOT HOLD ADRENALINE.

    The most refutable claim here, and the one that matters most to the sender.
    Split the corpus on a variable that has nothing to do with adrenaline
    traffic -- does the observer's SKILLBAR_UPDATE ever name a skill with a
    non-zero `adrenaline_units` -- and every 207, every 208 and every 210 falls
    on one side. One counterexample kills it.

    THE CONTROL IS THE HALF THAT MAKES THE ZERO MEAN SOMETHING. A filtered
    search that finds nothing proves nothing until the same search has found
    something it should, and here the positive is inside the negative
    population: those 22 connections carry 45 landed weapon hits and 13
    completed melee attacks. GWW's rule grants 25 units per successful weapon
    hit; retail granted none. So the silence is a gate and not an absence of
    combat, which is exactly what a quiet capture would look like.

    THE GATE'S VARIABLE WAS CONFOUNDED UNTIL 2026-09-14, AND THE CORPUS
    SEPARATED IT WITHOUT THE STAGED RUN. On 2026-08-21 every dark connection
    was also a non-Warrior, so "the bar carries an adrenal skill" and "the
    profession uses adrenaline" fit all 58 connections identically and the
    sender implemented neither. The owner's later sessions put a level-1
    Warrior on the bar [346, 1] (Frenzy, Healing Signet -- both cost 0) and a
    level-20 A/W on a dagger bar into the dark population, fighting, silent;
    and the fidelity judge's third rival -- "the character's LEARNED set holds
    an adrenal skill" -- is read off 0x001D / 0x00DB on the same connections
    and is silent too. The tail of this section pins all of that from
    `adrenjoin.by_connection()`, and since 2026-09-22
    `authsrv.player_gains_adrenaline` reads the CURRENT bar (studies/skills
    34.11; `--no-adren-bar-gate` is the pre-gate arm, exercised here).
    """
    print("\n12. the family is dark for a bar with no adrenal skill on it")
    import adrenjoin
    stats, rows, skipped = adrenjoin.scan()
    armed, dark = stats["arms"]["armed"], stats["arms"]["dark"]

    LEDGER.ok(armed["connections"] >= ARMED_CONNECTIONS
              and dark["connections"] >= DARK_CONNECTIONS,
              f"the split is at least {ARMED_CONNECTIONS} armed / "
              f"{DARK_CONNECTIONS} dark connections",
              f"expected {ARMED_CONNECTIONS}/{DARK_CONNECTIONS}. The variable "
              f"is the observer's own SKILLBAR_UPDATE against content's "
              f"`adrenaline_units` column -- nothing about adrenaline TRAFFIC "
              f"enters it, which is what lets the next check discriminate")

    got = {op: dark[k] for op, k in
           ((SMSG_ADRENALINE_CHARGE, "gain"), (SMSG_ADRENALINE_CLEAR, "clear"),
            (SMSG_ADRENALINE_SPEND, "spend"))}
    LEDGER.ok(set(got.values()) == {0},
              f"a dark connection carries NO adrenaline message at all: "
              f"{ {hex(o): n for o, n in got.items()} }",
              f"over {dark['messages']} messages in {dark['connections']} "
              f"connections. Not 'few' -- none. The whole lifecycle is absent, "
              f"clears and spends included, which is self-consistent: no gain "
              f"means no 25-second clock means nothing to clear")

    # AGAINST SECTION 4'S MEASURED CENSUS, not against a frozen copy of it.
    # `ARMED_FAMILY` used to be a third literal holding the same three numbers,
    # so the "two queries agreeing" this check advertises was really both
    # queries agreeing with a constant -- and when the corpus grew, both moved
    # together and the constant reddened them both. Comparing the two
    # MEASUREMENTS is the cross-check the comment always claimed, it is
    # strictly stronger, and it cannot go stale.
    census = agg["census"]
    pairs = ((SMSG_ADRENALINE_CHARGE, "gain"), (SMSG_ADRENALINE_CLEAR, "clear"),
             (SMSG_ADRENALINE_SPEND, "spend"))
    hero = stats["arms"]["hero"]
    LEDGER.ok(all(armed[k] + hero[k] == census[op] for op, k in pairs)
              and all(hero[k] == HERO_FAMILY[op] for op, k in pairs),
              f"and the armed side and the HERO's carry ALL of it: "
              f"{armed['gain']}+{hero['gain']}/{armed['clear']}+{hero['clear']}/"
              f"{armed['spend']}+{hero['spend']} (JARIN: a hero's family is on its "
              f"own agent, keyed by its own adrenal bar)",
              f"section 4's census reads "
              f"{ {hex(o): census[o] for o, _ in pairs} } over the whole corpus "
              f"and this counts per connection after a skillbar join -- TWO "
              f"QUERIES agreeing, which is what this check was always for. "
              f"Floors would not do here: the whole point is that the dark side "
              f"carries none of it, so the armed side must carry every single "
              f"one")

    LEDGER.ok(dark["hits_landed"] >= DARK_HITS_LANDED
              and dark["melee_finished"] >= DARK_MELEE_FINISHED,
              f"POSITIVE CONTROL: those dark connections FOUGHT -- "
              f"{dark['hits_landed']} landed hits, "
              f"{dark['melee_finished']} completed melee attacks",
              f"expected at least {DARK_HITS_LANDED} and "
              f"{DARK_MELEE_FINISHED}. WIKI (GWW, 'Adrenaline'): one successful "
              f"weapon hit is 25 units. Retail sent none for any of them, so "
              f"the zero above is a GATE and not a quiet capture. Without this "
              f"line the previous check is unfalsifiable")

    # THE GRANT RELATION, WHICH IS WHAT THE DETAIL STRINGS ALREADY SAID. Both of
    # these were `damage_taken == <frozen 32>` while their own prose explained
    # that "the two populations happen to be the same size, which is a
    # coincidence and not a check -- what matters is that one is 32 grants of 32
    # and the other is 0 of 32". The count was the part that could not survive a
    # capture, and the part that mattered was never asserted at all: nothing here
    # read `units`. Now the counts are floors and the GRANT is scored per row.
    # NAMED `_dmg` because `armed_rows` is rebound further down this same
    # function to the AMBIGUITY-FILTERED population. Two different denominators
    # under one name is how a grant share silently starts measuring a subset.
    armed_dmg = [r for r in rows if r["arm"] == "armed"]
    dark_dmg = [r for r in rows if r["arm"] == "dark"]
    # `is not None`, NOT TRUTHINESS, since 2026-09-17: a gain of 0 units is a
    # message that ARRIVED, and `if r["units"]` filed RB's seven zero grants
    # with the rows that got nothing -- 83 of 90, a red on the very rows that
    # prove every damage word is answered.
    # CASTAI-Z2 (2026-09-29): AN AMBIGUOUS ROW IS NOT AN UNGRANTED ROW. The
    # Smiting Monks' tape holds 14 armed batches of two to five UNEQUAL words
    # (a Zealot's Fire beside a Smite Hex from one monk; auras from two), and
    # `adrenjoin` leaves those 35 rows `units None` BY DESIGN -- attributing
    # whichever word sorted first would be a guess. Until this tape no armed
    # batch was ambiguous, so `units is not None` over every armed row read as
    # "all of them granted" and was really "none was ambiguous". The grant
    # relation now has two arms: every UNAMBIGUOUS row carries its gain, and
    # every AMBIGUOUS batch's words each consume a DISTINCT gain of the batch
    # at round(pct) -- a multiset relation with no assignment in it, which
    # floor(pct) must fail on some batch (the known-bad arm). None before the
    # pin, EXACT; the witness tape's (batches, rows) EXACT on itself.
    armed_clean = [r for r in armed_dmg if not r["ambiguous"]]
    armed_gr = [r for r in armed_clean if r["units"] is not None]
    dark_gr = [r for r in dark_dmg if r["units"] is not None]
    amb = collections.defaultdict(list)
    for r in armed_dmg:
        if r["ambiguous"]:
            amb[(r["capture"], r["connection"], r["t"])].append(r)

    def _covered(rs, f):
        gains = list(rs[0]["batch_gains"])
        for r in rs:
            u = f(r["pct"])
            if u not in gains:
                return False
            gains.remove(u)
        return True
    amb_round = [k for k, rs in amb.items() if _covered(rs, _round_half_up)]
    amb_floor = [k for k, rs in amb.items() if _covered(rs, math.floor)]
    amb_pin = [k for k in amb if k[0] < Z2_PIN_STAMP]
    amb_z2 = [k for k in amb if k[0] == Z2_TAPE]
    amb_rows = sum(len(v) for v in amb.values())

    LEDGER.ok(armed["damage_taken"] >= ARMED_DAMAGE_TAKEN
              and len(armed_dmg) == armed["damage_taken"]
              and armed_gr and len(armed_gr) == len(armed_clean)
              and len(amb_round) == len(amb) and not amb_pin
              and (len(amb_z2), sum(len(amb[k]) for k in amb_z2)) == Z2_AMBIGUOUS
              and len(amb_floor) < len(amb),
              f"the armed side took {armed['damage_taken']} damage messages, "
              f"and EVERY ONE of them granted: {len(armed_gr)}/{len(armed_clean)} "
              f"unambiguous rows carry a gain, and {len(amb_round)}/{len(amb)} "
              f"ambiguous batches ({amb_rows} rows) have a distinct gain of "
              f"round(pct) for every word",
              f"at least {ARMED_DAMAGE_TAKEN} expected, and the grant share "
              f"must be ALL in both arms. The row count is cross-checked "
              f"against the arm's own counter so a joiner that dropped rows "
              f"cannot make 'all of them' true by shrinking the denominator, "
              f"and `armed_gr` is asserted non-empty because all() of nothing "
              f"is this repo's own recorded trap. Ambiguous batches before "
              f"{Z2_PIN_STAMP}: {len(amb_pin)} (must be 0); on {Z2_TAPE}: "
              f"{(len(amb_z2), sum(len(amb[k]) for k in amb_z2))}, EXACT "
              f"{Z2_AMBIGUOUS}. KNOWN-BAD ARM: floor(pct) covers "
              f"{len(amb_floor)} of {len(amb)} of the same batches, so the "
              f"multiset relation discriminates -- e.g. two 5.625 % aura ticks "
              f"and a 4.583 % Zealot's Fire beside gains of 6, 6 and 5")

    zero_units = [r for r in armed_dmg if r["units"] == 0]
    zero_dmg = [r for r in armed_dmg if r["pct"] == 0.0]
    # CASTAI-Z1: the capture SET is scoped to the pin (a second tape, the
    # Zaishen, now carries one -- `ZAISHEN_ZERO`, section 4b); the relation,
    # zero-damage rows == zero-unit gains, stays corpus-wide and is the claim.
    LEDGER.ok(len(zero_units) >= ZERO_GRANTS and zero_units == zero_dmg
              and {r["capture"] for r in zero_units
                   if r["capture"] < PIN_STAMP} == {ZERO_GRANT_TAPE}
              and sum(1 for r in zero_units
                      if r["capture"] < PIN_STAMP) == ZERO_GRANTS
              and all(math.copysign(1.0, r["value"]) > 0 for r in zero_units),
              f"THE ZERO GRANT: {len(zero_units)} armed damage word(s) carry "
              f"+0.0, and each one is answered by a 207 carrying 0",
              f"{len(zero_dmg)} zero-damage rows, {len(zero_units)} zero-unit "
              f"gains, THE SAME ROWS -- as of the pin all {ZERO_GRANTS} on "
              f"{ZERO_GRANT_TAPE}, and past it "
              f"{sorted({r['capture'] for r in zero_units if r['capture'] >= PIN_STAMP})}"
              f" -- Reversal of "
              f"Fortune eating the whole hit (studies/skills 48.7: the "
              f"converted zero is +0.0, 7 of 7). Retail does not skip the gain "
              f"when there is nothing to gain, and since SKILLS-AD4 shipped "
              f"(2026-09-19) neither does `player_gains_adrenaline` -- the "
              f"zero goes out and skips the grant and the clock mark "
              f"(test_pools 11d). What a hit in (0, 0.5 %) sends is "
              f"still NOT OBSERVED; this makes 'a 207 carrying 0' the "
              f"prediction where it used to be 'no message'")

    LEDGER.ok(dark["damage_taken"] >= DARK_DAMAGE_TAKEN
              and len(dark_dmg) == dark["damage_taken"]
              and dark_dmg and not dark_gr,
              f"and they took {dark['damage_taken']} damage messages, every "
              f"one of which granted nothing ({len(dark_gr)}/{len(dark_dmg)})",
              f"ZERO is the claim here and stays exact -- a single dark grant "
              f"would refute the bar gate outright. THESE ARE THE ROWS THAT "
              f"LOOK LIKE A ROUNDING BOUNDARY and are not: unstratified they "
              f"say 'damage of up to 7.5% of maximum health grants no "
              f"adrenaline', which is absurd and would refute "
              f"`pools.damage_units` outright")

    fits = adrenjoin.fits([r for r in rows if r["arm"] == "armed"])
    # `round() fits ALL of them` is the finding and stays EXACT; it is a relation
    # between two numbers from the same fit and cannot go stale. What went was
    # `fits["n"] == ARMED_JOINED` and the third copy of 32 in ARMED_FITS["round"]
    # -- both frozen sizes of the vault, and the corpus doubling took them to 64.
    damaging = sorted(r["pct"] for r in armed_dmg if r["pct"] > 0.0)
    LEDGER.ok(fits["n"] >= ARMED_JOINED and fits["n"] > 0
              and fits["round"] == fits["n"]
              and fits["floor"] < fits["n"] and fits["ceil"] < fits["n"],
              f"re-fitted on the armed rows alone, round() fits "
              f"{fits['round']} of {fits['n']}",
              f"at least {ARMED_JOINED} rows, and round must fit ALL of "
              f"them; the pinned shape was {ARMED_FITS}. floor "
              f"{fits['floor']}, ceil {fits['ceil']} -- so the 2026-08-21 "
              f"correction from floor to round survives the stratification "
              f"that killed the boundary claim, AND the two hits-taken tapes "
              f"(2026-09-17: 58 rows, 58 fits). The damaging rows now run "
              f"{damaging[0]:.2f}%..{damaging[-1]:.2f}% where they ran "
              f"2.50%..11.04%; "
              f"{sum(1 for x in damaging if x < 1.0)} sit under 1%, so what a "
              f"hit in (0, 0.5%) sends is still NOT OBSERVED")

    armed_rows = [r for r in rows if r["arm"] == "armed" and not r["ambiguous"]]
    # PER ROW, AGAINST THE ROW'S OWN PROPERTY 42 (`whose_max_health`, read off
    # the same wire before the damage). Nothing in `pct` looked at it.
    points = [(r, r["pct"] / 100.0 * r["max_health"]) for r in armed_rows
              if r["max_health"]]
    integral = (len(points) == len(armed_rows)
                and all(abs(k - round(k)) < 1e-3 for _r, k in points))
    healths = {r["max_health"] for r in armed_rows}
    pcts = sorted({r["pct"] for r in armed_rows
                   if r["max_health"] == ARMED_MAX_HEALTH})
    ks = sorted({round(k) for r, k in points
                 if r["max_health"] == ARMED_MAX_HEALTH})
    smaller = [h for h in range(1, ARMED_MAX_HEALTH)
               if all(abs(p / 100.0 * h - round(p / 100.0 * h)) < 1e-4
                      for p in pcts)]
    LEDGER.ok(integral and set(ARMED_NUMERATORS) <= set(ks) and not smaller
              and healths >= ARMED_MAX_HEALTHS,
              f"NO FREE PARAMETER: all {len(points)} armed percentages are "
              f"whole points of that row's OWN maximum health, over "
              f"{sorted(healths, reverse=True)}",
              f"at {ARMED_MAX_HEALTH}: k = {ks}, which must contain the "
              f"original {ARMED_NUMERATORS}, and no denominator below "
              f"{ARMED_MAX_HEALTH} works (found {smaller}). The observer's int "
              f"property 42 reads the maximum on the same wire and none "
              f"of this arithmetic looked at it, so the two are independent "
              f"witnesses -- and since 2026-09-17 it is four maxima rather "
              f"than one, which is what lets the next check say something the "
              f"corpus could not")

    # THE DENOMINATOR IS THE CURRENT MAXIMUM. Asked of the rows whose maximum
    # had MOVED -- three deaths' worth of penalty on RB2 (480 -> 408 -> 336) and
    # a 384 on RB -- because at 480 the two readings are the same number.
    moved = [(r, k) for r, k in points
             if r["max_health"] != ARMED_MAX_HEALTH and r["pct"] > 0.0]

    def _round(x):
        return int(math.floor(x + 0.5 + 1e-9))
    of_current = [r for r, _k in moved if _round(r["pct"]) == r["units"]]
    of_base = [r for r, k in moved
               if _round(k / (ARMED_MAX_HEALTH / 100.0)) == r["units"]]
    # CASTAI-Z1: `not of_base` is the literal claim AS OF THE PIN. Past it, a
    # row where round(% of current) and round(points / 4.8) coincide cannot
    # refute either reading (the Zaishen tape's (384, 12, 3): 3.125 % and 2.5
    # both round to 3), so the claim is carried by the DISCRIMINATING rows --
    # every one of which must fit the current maximum.
    disc = [(r, k) for r, k in moved
            if _round(r["pct"]) != _round(k / (ARMED_MAX_HEALTH / 100.0))]
    z_moved = sorted((r["max_health"], round(k), r["units"]) for r, k in moved
                     if r["capture"] == ZAISHEN_TAPE)
    LEDGER.ok(len(moved) >= MOVED_MAX_ROWS and len(of_current) == len(moved)
              and not [r for r in of_base if r["capture"] < PIN_STAMP]
              and len(disc) >= MOVED_MAX_ROWS
              and z_moved == ZAISHEN_MOVED,
              f"THE DENOMINATOR IS THE CURRENT MAXIMUM: {len(of_current)} of "
              f"{len(moved)} rows against a moved maximum fit round(% of it), "
              f"{len([r for r in of_base if r['capture'] < PIN_STAMP])} fit "
              f"round(points / {ARMED_MAX_HEALTH / 100.0}) as of the pin, and "
              f"{len(disc)} rows discriminate",
              f"past the pin {len(of_base)} coincide under both readings; the "
              f"Zaishen tape's moved rows {z_moved} are under Deep Wound (482, "
              f"property 42 480 -> 384 in its apply batch, t 109.171) -- the "
              f"same mechanism as RB's 384 rows before the pin (482 at t 256.847 "
              f"and 329.811 on 20260916T213125), a second tape. "
              f"{[(r['max_health'], round(k), r['units']) for r, k in moved]} "
              f"as (maximum, points, units). 286 points is 60 units at 480 and "
              f"70 at 408; 101 is 21 at 480 and 30 at 336. CLOSES the limit "
              f"this section used to end on ('one max health cannot separate "
              f"one unit per 1% of maximum from one unit per 4.8 raw points'). "
              f"OUR SERVER DIVIDES BY THE BASE (`agents.PLAYER_HEALTH`, two "
              f"sites in authsrv.py) while its damage word divides by "
              f"`player_max_health(state)`: under a death penalty or a Deep "
              f"Wound the two books part. Recorded, open in PLAN.md 8")

    over = [r for r in armed_rows if (r["units"] or 0) > STRIKE_UNITS]
    LEDGER.ok(len(over) >= 6 and all(_round(r["pct"]) == r["units"]
                                     for r in over),
              f"and the damage rule has NO CAP at {STRIKE_UNITS}: "
              f"{sorted(r['units'] for r in over)} are each ONE damage word",
              f"{[(r['capture'], round(r['pct'], 2), r['units']) for r in over]}"
              f" -- unambiguous batches, one damage word and one gain apiece, "
              f"so nothing was summed. 4b's 'no 207 exceeds 25' was the "
              f"strike rule's ceiling read as the opcode's")

    # units == f(pct * k): solve each family for the k interval fitting all rows
    bands = {}
    for name, half in (("floor", 0.0), ("round", 0.5), ("ceil", 1.0)):
        lo, hi = 0.0, float("inf")
        for r in armed_rows:
            u, pct = r["units"], r["pct"]
            if pct == 0.0:
                # A zero-damage row constrains no k: f(0 * k) is 0 for every k
                # under all three rules, and its units ARE 0 (the zero-grant
                # check above). Dividing by it was a ZeroDivisionError on
                # 2026-09-17, the first day the corpus held one.
                continue
            lo = max(lo, (u - half) / pct)
            hi = min(hi, (u + 1.0 - half) / pct)
        bands[name] = (lo, hi) if lo < hi else None
    rb = bands["round"]
    ok = (bands["floor"] is None and bands["ceil"] is None
          and rb is not None
          and rb[0] <= 1.0 < rb[1]
          and rb[0] >= FAMILY_K["round"][0] - 1e-5
          and rb[1] <= FAMILY_K["round"][1] + 1e-5)
    LEDGER.ok(ok,
              "the rule is ROUND: floor AND ceil are empty under every "
              "rescale, and round's interval still holds k = 1",
              f"{ {n: (None if b is None else (round(b[0], 6), round(b[1], 6))) for n, b in bands.items()} } "
              f"inside the 2026-08-21 outer bound {FAMILY_K['round']}. Solving "
              f"`units == f(pct*k)` for k over all {len(armed_rows)} rows: "
              f"FLOOR IS EMPTY, which refutes GWW's 'rounded down' AND the "
              f"pre-mitigation-damage repair of it in one line. CEIL IS EMPTY "
              f"TOO since 2026-09-17 -- a 1.25% hit granted 1 (k <= 0.8) and a "
              f"59.58% hit granted 60 (k > 0.990) -- so the survivor this "
              f"section used to call provisional is the only one left, and "
              f"k = 1 means the wire's own fraction, unscaled. "
              f"`pools.damage_units` implements round; this now says it is "
              f"right everywhere the corpus has looked, which is 0% and "
              f"1.04%..70.1%. half-up vs half-even is still untouched: no "
              f"row lands on .5")

    # FAILED AS WRITTEN on 2026-09-29 (CASTAI-Z2) -- the record is at
    # DISAGREEMENT_BAND. It read `len(band) == 1 and band[0]["arm"] == "dark"`
    # over the whole corpus, and the Smiting Monks' tape put 24 armed rows in
    # the band, every one a 3-point wand hit granting 1. Now: the one dark
    # near miss EXACT as of the pin; the 24 EXACT on their own tape, each 3
    # points, each granting round(pct) and not floor(pct); past the pin every
    # armed band row must grant round(pct) (the rule, one stray reddens); and
    # the (0, 0.5 %) count -- the question this check actually guards -- is
    # REPORTED, not asserted: it is 0, and NOT OBSERVED stays the label.
    band = [r for r in rows if not r["ambiguous"]
            and DISAGREEMENT_BAND[0] <= r["pct"] < DISAGREEMENT_BAND[1]]
    band_pin = [r for r in band if r["capture"] < Z2_PIN_STAMP]
    band_z2 = [r for r in band if r["capture"] == Z2_TAPE]
    armed_band = [r for r in band if r["arm"] == "armed"]
    z2_points = sorted({int(round(r["pct"] / 100.0 * r["max_health"]))
                        for r in band_z2 if r["max_health"]})
    under_half = [r for r in rows if not r["ambiguous"]
                  and 0.0 < r["pct"] < DISAGREEMENT_BAND[0]]
    LEDGER.ok(len(band_pin) == 1 and band_pin[0]["arm"] == "dark"
              and abs(band_pin[0]["pct"] - NEAR_MISS_PCT) < 1e-9
              and len(band_z2) == Z2_BAND_ROWS
              and all(r["arm"] == "armed" for r in band_z2)
              and z2_points == [3]
              and armed_band
              and all(r["units"] == _round(r["pct"]) for r in armed_band)
              and all(math.floor(r["pct"]) != r["units"] for r in armed_band),
              f"THE NEAR MISS, FAILED AS WRITTEN and re-scoped: as of "
              f"{Z2_PIN_STAMP} exactly one damage event lands in "
              f"[{DISAGREEMENT_BAND[0]}%, {DISAGREEMENT_BAND[1]}%) and it is "
              f"DARK; on {Z2_TAPE} exactly {len(band_z2)} ARMED rows do, each "
              f"{z2_points} point(s), each granting 1",
              f"as of the pin {[(r['arm'], round(r['pct'], 9), r['capture']) for r in band_pin]}; "
              f"armed band rows over the corpus {len(armed_band)}, units "
              f"{sorted(collections.Counter(r['units'] for r in armed_band).items())}, "
              f"maxima {sorted({r['max_health'] for r in armed_band})}, "
              f"round fits all and floor (0) fits none -- the known-bad arm. "
              f"Rows in (0, {DISAGREEMENT_BAND[0]}%): {len(under_half)} "
              f"{[(r['arm'], round(r['pct'], 6), r['units'], r['capture']) for r in under_half]} "
              f"-- REPORTED, and while it is 0 what a sub-0.5% hit sends (a "
              f"207 carrying 0, or nothing) stays NOT OBSERVED. When the "
              f"check was written the band was the only place round and ceil "
              f"disagreed; ceil has since died on rows ABOVE 1% (the family "
              f"check) and the band's 24 armed rows agree with round and ceil "
              f"both. The dark near miss's observer's bar has no adrenal "
              f"skill, so there was nothing to charge; its value is "
              f"{NEAR_MISS_PCT:.9f}%, from bits 0x{NEAR_MISS_BITS:08X}: at four "
              f"decimals it prints as 1.0000, exactly where the two rules "
              f"AGREE. Three independent readers printed it rounded and all "
              f"three read past it")

    # THE PREDICATE, NOT THE COUNT. `len(skipped) <= 1` capped an absolute
    # number over a growing corpus -- every live session contributes its own
    # 6112 auth channel, so the second capture-pair to do so reddens it. What
    # the detail string always claimed is WHY the skip is harmless: it is an
    # auth channel, which carries no agent properties at all. That is checkable
    # per row and gets stronger as the corpus grows.
    not_auth = [s for s in skipped
                if not s["connection"].rsplit(":", 1)[-1] == "6112"]
    LEDGER.ok(not not_auth,
              f"all {len(skipped)} connection(s) skipped for having no unique "
              f"self agent are 6112 auth channels",
              f"offenders: {not_auth}. The self agent is int property 41, "
              f"self-scoped, with NO fallback (`adrenjoin.whose_agent`). Every "
              f"skip so far is a 6112 auth channel, which carries no agent "
              f"properties at all -- a skip on a GAME channel is the one that "
              f"would mean the observer had gone unidentifiable, and it is what "
              f"this now names. The count is reported, not capped. "
              f"Identifying the observer by 'the agent a 207 names' would "
              f"delete the ENTIRE dark population from the denominator -- the "
              f"outcome-selection defect one level down")

    # ---- THE CONFOUND, BROKEN (2026-09-22; skills 34.11) -------------------
    # `by_connection` is a SECOND walk of the corpus with its own counters, so
    # its arm sizes and family totals must reproduce `scan()`'s before anything
    # it says about professions is believed.
    conns = adrenjoin.by_connection()
    dark_c = [r for r in conns if r["arm"] == "dark"]
    armed_c = [r for r in conns if r["arm"] == "armed"]
    LEDGER.ok(len(dark_c) == dark["connections"]
              and len(armed_c) == armed["connections"]
              and sum(r["gain"] for r in dark_c) == 0
              and sum(r["clear"] for r in dark_c) == 0
              and sum(r["spend"] for r in dark_c) == 0
              and sum(r["hits_landed"] for r in dark_c) == dark["hits_landed"]
              and sum(r["gain"] for r in armed_c) == armed["gain"],
              f"the per-connection walk reproduces the split: "
              f"{len(armed_c)} armed / {len(dark_c)} dark, dark family 0/0/0",
              f"scan() says {armed['connections']}/{dark['connections']} with "
              f"{dark['hits_landed']} dark hits and {armed['gain']} armed "
              f"gains; two walks with separate counters must agree before the "
              f"profession columns below mean anything")

    # GATE B ("the profession uses adrenaline") REFUTED at level 1 AND 20.
    # The profession is 0x00B7's own primary/secondary for the observer's agent
    # (cross-checked against the 0x0059 appearance nibble, 0 disagreements),
    # never inferred from the bar's skills -- which is how 34.5 read it.
    dark_w = [r for r in dark_c if 1 in (r["profession"], r["secondary"])
              and r["hits_landed"]]
    prof_joined = [r for r in conns if r["profession_59"] is not None
                   and r["profession"] is not None]
    LEDGER.ok(len(dark_w) >= DARK_WARRIOR_FIGHTS
              and sum(r["hits_landed"] for r in dark_w) >= DARK_WARRIOR_HITS
              and all(r["gain"] == r["clear"] == r["spend"] == 0 for r in dark_w)
              and any(r["profession"] == 1 and r["level"] == 1 for r in dark_w)
              and any(r["secondary"] == 1 and r["level"] == 20 for r in dark_w)
              and prof_joined
              and all(r["profession_59"] == r["profession"] for r in prof_joined),
              f"GATE B REFUTED: {len(dark_w)} dark connections whose character "
              f"IS a Warrior landed {sum(r['hits_landed'] for r in dark_w)} "
              f"hits and got none of the family",
              f"{[(r['capture'], r['profession'], r['secondary'], r['level'], r['hits_landed'], r['gain']) for r in dark_w]}"
              f" as (capture, primary, secondary, level, hits, gains). A primary "
              f"Warrior at level 1 and a secondary Warrior at level 20 both "
              f"silent, so neither 'profession' nor 'level' is the variable; "
              f"0x00B7 and the 0x0059 nibble agree on all {len(prof_joined)} "
              f"connections that carry both. The corner with no witness is a "
              f"PRIMARY Warrior above level 1 on a dark bar -- said in 34.11")

    # THE THIRD RIVAL ("the LEARNED set holds an adrenal skill") REFUTED. The
    # account set rides once per session (read per capture) and the character
    # set rides every map connection; both are bitmaps, decoded to ids and
    # joined to content's adrenaline_units. The A/W's CHARACTER library holds
    # 348/382/385 on both of its fighting connections.
    def _learned(r):
        acct = (r["account_adrenal"] if r["account_n"] is not None
                else r["account_adrenal_capture"])
        return bool(acct) or bool(r["character_adrenal"])
    learned = [r for r in dark_c if r["hits_landed"] and _learned(r)]
    char_lib = [r for r in learned if r["character_adrenal"]]
    LEDGER.ok(len(learned) >= DARK_LEARNED_FIGHTS
              and all(r["gain"] == 0 for r in learned)
              and len(char_lib) >= 2
              and all(r["gain"] == 0 and r["hits_landed"] >= 100 for r in char_lib),
              f"THE THIRD RIVAL REFUTED: {len(learned)} dark connections with a "
              f"landed hit have an adrenal skill in a LEARNED set and got no "
              f"gain; {len(char_lib)} of them in the CHARACTER library itself",
              f"character-library witnesses "
              f"{[(r['capture'], r['character_adrenal'], r['hits_landed']) for r in char_lib]}"
              f"; the account library carries an adrenal skill on every "
              f"capture, so the account half is refuted on all of them. The "
              f"two sets are different objects in the client (skills 47.2), "
              f"so both had to be read")

    # WHAT IS NOT OBSERVED, pinned so the gate's caveat stays honest: no
    # connection flips its bar's armed-ness mid-connection, no hit lands
    # before the observer's first own 0x00DA, and no family message ever
    # arrives while the bar is dark. The first tape that breaks any of these
    # is the dark-to-armed transition witness the gate says it lacks.
    LEDGER.ok(not any(r["flips"] for r in conns)
              and sum(r["hits_before_bar"] for r in conns) == 0
              and sum(r["family_dark"] + r["family_before_bar"] for r in conns) == 0,
              "the dark-to-armed TRANSITION is UNOBSERVED: 0 mid-connection "
              "flips, 0 hits before the bar, 0 family messages while dark",
              f"over {len(conns)} connections. `bar_holds_adrenal` reads the "
              f"bar at gain time, so a mid-fight drag arms the sender on the "
              f"next hit -- the smaller claim, said at the call site")

    # AND THE CLEAR IS GATED TOO: retail's dark connections hold player deaths
    # and not one 0x00D0, which is what puts the gate on `kill_player`'s clear.
    dark_deaths = sum(r["deaths"] for r in dark_c)
    LEDGER.ok(dark_deaths >= DARK_DEATHS
              and sum(r["clear"] for r in dark_c) == 0,
              f"{dark_deaths} player deaths on dark connections, 0 clears",
              f"the 0x0026 [me, 4] death flag against 0x00D0 naming the "
              f"observer. On the ARMED side the death clear is not so simple: "
              f"of four armed player deaths, three carry a 0x00D0 (a pool that "
              f"held charge, 20260917T090355) and one does not (20260821T152147 "
              f"conn 63150, an armed bar that landed 0 hits -- empty pool). So "
              f"the dark silence is OBSERVED (11/11) but the armed clear's "
              f"CAUSE -- the bar, or charge held -- is CONTESTED at n=1 "
              f"(skills 34.11.4); this check locks only the dark half")

    # THE SANDBOX CHECK the acceptance names: our own sender, the corpus's own
    # dark Warrior bar, a landed hit -- no 0x00CF; the revert flag is the
    # known-bad arm; an armed bar is the positive control. `hit_enemy` is the
    # site the 25-unit strike rides (test_pools 11).
    import authsrv
    import agents
    _saved = (list(authsrv.SKILLBAR), authsrv.ADREN_BAR_GATE)
    try:
        def _hit(bar, gate):
            authsrv.SKILLBAR, authsrv.ADREN_BAR_GATE = list(bar), gate
            sent = []
            send = lambda op, vals, why="": sent.append((op, vals))    # noqa: E731
            st = {"agents": {}, "pos": (0.0, 0.0),
                  "player_health": float(agents.PLAYER_HEALTH)}
            st["agents"][7] = {
                "name": "a target", "dead": False, "last_hit": 0.0,
                "health": 100.0, "max_health": 100.0, "armor_rating": 60,
                "pos": (10.0, 0.0), "skills": ((382, 0.0, 0.0),),
                "attacks_back": False}
            authsrv.hit_enemy(send, st, 7, 0)
            words = [v for op, v in sent
                     if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET
                     and v[0] in (16, 17) and v[1] == 7]
            gains = [v for op, v in sent if op == authsrv.AGENT_ADRENALINE_GAIN]
            return words, gains
        dw, dg = _hit([346, 1], True)
        bw, bg = _hit([346, 1], False)
        aw, ag = _hit([382, 317, 318, 319], True)
        LEDGER.ok(dw and dg == []
                  and bw and bg == [[authsrv.PLAYER_AGENT_ID, 25]]
                  and aw and ag == [[authsrv.PLAYER_AGENT_ID, 25]],
                  "OUR SENDER: a landed hit from the dark bar [346, 1] sends no "
                  "207; --no-adren-bar-gate sends it; an armed bar sends it",
                  f"dark {dg} ({len(dw)} damage word), gate off {bg}, armed "
                  f"{ag}. The damage word is asserted present each time so a "
                  f"miss cannot pass as silence; the gate reads SKILLBAR at the "
                  f"gain, which the 0x005C handler rewrites in place")
    finally:
        authsrv.SKILLBAR, authsrv.ADREN_BAR_GATE = _saved


def section_repaint_gate(img):
    """WHY NOBODY SAW 12 FROM THE SCREEN: a 207 no slot accepted is a no-op.

    Read as arithmetic on the charge worker's own bytes rather than compared
    with a transcription. EDI is cleared before the slot loop, set only on the
    path that writes a slot, and tested immediately after the loop's back-edge;
    the `je` skips the UI event that carries the 25.0 timer. So a 207 delivered
    to a bar with no adrenal skill leaves the flag at zero and exits.

    This is what makes 12's divergence invisible, and it cuts both ways: it is
    why our sender's extra 207s are harmless on screen, and it is why six
    captures of retail sending none went unnoticed for a day.
    """
    print("\n13. the charge worker's repaint is gated on 'a slot moved'")
    b = img.read(VA_CHARGE_FLAGCLR, 3)
    LEDGER.ok(b[:2] == b"\x33\xff",
              f"0x{VA_CHARGE_FLAGCLR:08x} is `xor edi,edi`, before the loop",
              f"read {b[:2].hex()}, expected 33ff. The flag starts clear, so "
              f"the default outcome of the loop is 'nothing moved'")

    b = img.read(VA_CHARGE_FLAGSET, 5)
    LEDGER.ok(b == b"\xbf\x01\x00\x00\x00",
              f"0x{VA_CHARGE_FLAGSET:08x} is `mov edi,1`, INSIDE the loop",
              f"read {b.hex()}, expected bf01000000. It sits immediately after "
              f"the only arithmetic store to a slot (0x{VA_CHARGE_STORE:08x}), "
              f"so it is set per SLOT WRITTEN and not per message received")

    # the loop's back-edge, as arithmetic: jne rel8 at 0x008219F6 -> the top
    j = img.read(0x008219F6, 2)
    back = (0x008219F6 + 2 + struct.unpack("<b", j[1:2])[0]) & 0xFFFFFFFF
    LEDGER.ok(j[0] == 0x75 and back == VA_CHARGE_LOOPTOP,
              f"the loop closes: `jne` at 0x008219F6 goes back to "
              f"0x{back:08x}",
              f"expected 0x{VA_CHARGE_LOOPTOP:08x}. Computed from the "
              f"displacement, so a wrong address gives a wrong sum rather than "
              f"agreeing with a label we chose")

    b = img.read(VA_CHARGE_FLAGTST, 8)
    target = (VA_CHARGE_FLAGTST + 8
              + struct.unpack("<i", b[4:8])[0]) & 0xFFFFFFFF
    LEDGER.ok(b[:2] == b"\x85\xff" and b[2:4] == b"\x0f\x84",
              f"0x{VA_CHARGE_FLAGTST:08x} is `test edi,edi` then `je`, AFTER "
              f"the loop",
              f"read {b.hex()}. This is the whole finding: the test is outside "
              f"the loop and the jump is taken when NO slot moved")

    LEDGER.ok(VA_CHARGE_FLAGTST < VA_UI_EVENT_PUSH < target,
              f"and the `je` lands at 0x{target:08x}, PAST the UI event push "
              f"at 0x{VA_UI_EVENT_PUSH:08x}",
              f"an ordering claim, checkable by three addresses: the push is "
              f"between the test and the jump's target, so taking the jump "
              f"skips it. A 207 that moved nothing fires no 0x{UI_EVENT_ADREN:08x} "
              f"and arms no 25-second timer")

    b = img.read(VA_UI_EVENT_PUSH, 5)
    LEDGER.ok(b == b"\x68" + struct.pack("<I", UI_EVENT_ADREN),
              f"the skipped push is the adrenaline UI event, "
              f"0x{UI_EVENT_ADREN:08x}",
              f"read {b.hex()}. Same event 11 names from the other end -- the "
              f"blink warning's timer. Skipping it is what makes an unaccepted "
              f"207 invisible rather than merely harmless")


def main():
    declared = section_schema()
    section_pin_consistency()
    section_cost_column()
    section_classifier_arms()

    live = live_corpus_dir()
    # Deliberately OUTSIDE any handler (CASTAI-Z1 review): a load failure here
    # is a crash, never a skip.
    agg = scan_corpus(live) if live is not None else None
    if agg is not None:
        section_census(agg)
        section_populations(agg)
        section_self_scope(agg)
        section_spend_join(agg)
        section_order(agg)
        section_bar_gate(agg)

    try:
        img = Image()
    except (Exception, SystemExit) as ex:                      # noqa: BLE001
        img = None
        LEDGER.skip("the build-38797 byte pins (sections 8-11)",
                    f"the pinned client image is not in this vault ({ex}). "
                    f"Every address in this file was measured on 38797 and on "
                    f"another build would read whatever else is mapped there "
                    f"and return a confident wrong number, which is why "
                    f"`pinned.find()` refuses rather than guessing")
    if img is not None:
        section_dispatch(img, declared)
        section_workers(img)
        section_display(img)
        section_arenanet_words(img)
        section_repaint_gate(img)

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
