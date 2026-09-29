#!/usr/bin/env python3
r"""CASTAI-Z1 / Z2 / Z3 scored off the live Zaishen Challenge captures (monsterai FINDINGS 18).

    python studies/monsterai/review/zaishenrun.py                  # Z1 tape; match 2 refused (gapped)
    python studies/monsterai/review/zaishenrun.py --prefix         # match 2's prefix scored too
    python studies/monsterai/review/zaishenrun.py --prefix --rows  # plus one line per cast
    python studies/monsterai/review/zaishenrun.py --capture 20260928T103123
    python studies/monsterai/review/zaishenrun.py --capture 20260929T100038 --rows   # Z2 tape

WHAT THIS SCORES. One capture (default 20260928T103123, the owner's run of 2026-09-28 on
the secondary account, build 38888, plan castai_z1_degeneration.txt; the Z2 tape is
20260929T100038, the same account and build, plan castai_z2_monks.txt): every game
connection whose map is a Zaishen arena (castethogram.ZAISHEN_MAPS, MEASURED on these
tapes) and which creates 0x01BF henchman adds. Matches are numbered by start time. The
opponent TEAM is read off the wire, not the plan: the professions in the 0x0056
definitions of the four ZAISHEN bodies -- {Warrior, Ranger, Necromancer, Mesmer} is the
Degeneration Team (Z1), four Elementalists the Obsidian Spike Elementalists (Z3; match 3
was picked BY ACCIDENT, the owner's words, so Z3 here is ONE match: PARTIAL), four Monks
the Smiting Monks (Z2). Party names come from the 0x01BF profession byte: 3 Healer,
6 Mage, 2 Archer, 1 Fighter (WIKI, the henchman pages revs 2675993 / 2675996 / 2675995 /
2709116). A section whose team has no match on the capture says so and prints no
verdict lines (a "[NULL] n=0" over no match would read as a measurement).

THE GAPPED CONNECTION (`--prefix`, opt-in). Match 2's s2c has two capture gaps (the
sniffer dropped 38 bytes at stream offset 38045 and 20 at 38548), so
`livewire.decode_conn` refuses it -- correctly, for every other consumer: a partially
timed stream would date one message with another's clock. `prefix_decode` walks
`tape._segments` in seq order from the stream's first byte, STOPS at the first seq
discontinuity, and decodes exactly the plaintext bytes those segments carry (the
orchestrator's method, scratch orch-z1-prefix.py). It prints the cut byte and time, and
refuses unless the prefix frames whole and the c2s direction decodes whole. Every match-2
number is labelled "prefix": the last ~21 s of that match are not in it.

READERS REUSED: castethogram (Conn, build_casts, completion, the health RECONSTRUCTION,
applies_live, the ZAISHEN / HENCHMAN classes), rechargeprobe (activation / recharge read
out of the 38888 exe -- it carries the PvP ids the pinned table lacks), agents.WORLD
skills rows (type, target byte, duration0 / duration15), aotjoin.rows_of (the Fire Storm
join: completion, ticks, words per tick), weaponcensus (who holds what), shoutjoin
(the observer), henchjoin (0x01BF adds).

SKILL IDS ARE THE WIRE'S AND THE TABLE'S. Names where the repo already has one
CORROBORATED (effects.py / hexjoin / authsrv comments): 197 Fire Storm, 277 Mend Ailment,
281 Orison of Healing, 282 Word of Healing, 286 Heal Other, 288 Healing Breeze,
301 Remove Hex; and, read off GWW's own infobox `id` field on 2026-09-28 (WIKI, the
revisions at ARCANE_CONUNDRUM below) and matching the table row's cost / activation /
recharge: 36 Arcane Conundrum, 53 Migraine, 31 Conjure Phantasm, 44 Phantom Pain,
179 Incendiary Bonds, 313 Healing Touch, 280 Heal Area, 169 Earth Attunement,
176 Ward Against Melee, 2809 Obsidian Flame (PvP). The first draft of this docstring
named the Z3 ids by elimination; the wiki's ids agree with every one. The Z2 ids (the
Monks' bar, the Mage's Aura of Restoration, the Archer's Poison Arrow, the Fighter's
Hamstring) were read off GWW's infobox on 2026-09-29 and are named ONLY after
`corroborate_ids` has matched each one's energy / activation / recharge against the
served build's own exe row at run time (WIKI_TRIPLES below; a mismatch withholds the
name and prints the id by number). Every other id on the Z2 tape is printed by number.

THE PREDICTIONS are FINDINGS 18's, registered 2026-09-28 before the run; the operational
choices this reader makes where the registration is silent are marked SCORER'S RULE and
were written before the reader first ran over the capture.

  Z1.P1  no opponent hex onto a body carrying a live episode of the same hex. LIVE:
         the observer -- EXACT, a 0x0042 [obs, S, .., buff] with no 0x0044 [obs, buff]
         yet; any other body -- RECONSTRUCTION: the latest completed (58) cast of S on T,
         live for D after the completion, where D is the duration the SAME skill showed
         on the observer's 0x0042 in this capture (median, OBSERVED) or else the table's
         duration0 ("certain") -- the table is the build's exe row at the caster's
         observed rank since fix 4 below; cut short by T's death / re-create, a hex removal
         completing on T (301 by anyone), T's 0x00F1 hexed bit (0x800) clearing, or the
         [7] of the skill's class marker on T (added after the first run: class_markers).
         INFORMATIVE (the floor's unit): S was live on T at some instant between the
         caster's slot for S becoming READY (its previous completion + the exe
         recharge) and the announce. A counterexample FAILS it whatever the floor
         (FINDINGS: "one counterexample is enough"); else < 10 informative is NULL.
  Z1.P2  the Healer's 301 only onto a hexed target (hexed bit at the announce, or a
         live 0x0042 hex on the observer); latency from the bit's last rise. Floor 5.
  Z1.P3  the Healer's heals on ANOTHER ally (a completed cast of a HEAL_SKILLS id at
         T != healer -- CORRECTED after the first run, which took "a completion batch
         carrying [55, T, healer]" and so counted two Remove Hexes whose batch carried a
         Healing Breeze tick; the verdict was NULL either way): every one on a hurt T (health
         < 0.99 or damage on T in the 10 s before), the lowest health fraction among
         the living party in >= 80 % of casts where >= 2 are hurt; 281 only when T's
         deficit >= the heal it lands. Floor 20.
  Z1.P4  a Necromancer-body hex completing on a non-observer T carries [6, T, 1] and
         [6, T, X], X not 12 and not 4. One clean instance names X.
  Z1.P5  every property-61 word naming the observer (0x00A3 [61, obs, target, s] or
         0x00A2 [61, obs, s]) anywhere in the capture, and every observer SPELL (type
         4 / 5 / 6) announced with Arcane Conundrum (36) or Migraine (53) live on it
         (0x0042). HELD if such a cast carries a 61 word naming the observer in its
         batch; FAILED if there are such casts and none does; NULL if there are none.
         POST-HOC -- NOT PRE-REGISTERED IN EVERY DETAIL. Two of the rules just stated
         were set AFTER this reader first ran over the capture: (1) the scored set was
         NARROWED to observer spells under 36 / 53, which is what FINDINGS 18's text
         registers ("a spell of yours cast under Arcane Conundrum or Migraine") -- the
         first run scored every observer cast under ANY Mesmer-body hex; (2) the word
         window was WIDENED to the announce's whole batch (castethogram.Conn.batch_ops,
         +/- BATCH), CHOSEN AFTER SEEING THE DATA -- under the older window the first run
         printed FAILED, 0 of 8. The HELD rests on ONE cast (match 4 622.94, skill 153
         under 31 + 36) whose word the older window missed, so the verdict turns on
         change (2). Read it as a lead with one witness, not as a registered pass.
  Z1.P6  a ZAISHEN definition with >= 30 casts and an announce where >= 2 of its slots
         were READY at once (the bar), and a slot re-fired while another READY slot
         waited: SCORER'S RULE -- S2 an energy (not adrenaline) foe-target slot the body
         already fired in this incarnation, ready at S's previous announce and not fired
         between S's two announces. Energy is not on the wire: a waiting slot the body
         could not pay for would look the same (printed as the caveat).
  Z1.P7  Fire Storms (197, the Mage) whose ticks strike >= 2 opponents (floor 3): the
         opponents struck in the first 3 damaging ticks are struck by no later tick while
         alive (the instrument is the tick's damage words, OBSERVED; positions on these
         tapes are leads, aotjoin's note).
  Z3.P1  Obsidian Flame (2809: the only foe-target skill the four Elementalists cast;
         not in the pinned table, exe act 1.5 / rech 5; WIKI id, the PvP split) groups on
         one target inside 1.5 s; SCORER'S RULE: HELD if >= 50 % of the casts sit in a
         group of >= 3.
  Z3.P2  Ward Against Melee within 3 s of a melee attack start on an Elementalist.
  Z3.P3  277 / 301 by an Elementalist only onto an Elementalist carrying a condition
         (0x02) / a hex (0x800). Floor 5 Mend Ailment.
  Z3.P4  Heal Area (280: the Elementalists' Healing Prayers self-form spell --
         WIKI id): the caster's health at each cast; >= 2 inside 2 s.
  Z3.P5  Earth Attunement (169: Earth Magic enchantment, self, 36-60 s --
         WIKI id) never re-cast while its [6] lives; each re-cast >= 0.228 s
         after the [7].
  OWNER  opponent offensive casts (a hex, or any foe-target spell / attack skill) and
         attack starts (0x00A0 [4]) by TARGET, per match, with the observer's weapon.
         On a match without a Healer every party body's share is printed instead.

CASTAI-Z2 -- THE SMITING MONKS (20260929T100038; registered in FINDINGS 18 on 2026-09-28,
before the run). Scored over EVERY match whose four ZAISHEN bodies are Monks (MONKS).
The operational rules below are SCORER'S RULES: written 2026-09-29 after an INSTRUMENT
probe over the tape (scratch z2s-probe / z2s-probe2: what the wire carries, never a
verdict) and BEFORE this section first ran. Anything changed after a Z2 verdict was seen
is marked POST-HOC at its site with the verdict it replaced.

THE INSTRUMENTS, as measured on this tape (OBSERVED unless labelled):
  * HEALTH. No 0x00A2 [34] setter on any body of any match: every body is anchored
    'create-full' -- created at full health when the match instance loads -- and
    integrated from there (16 / 17 / 55 deltas, the 44 regen rate; Conn.health_at). A
    revive is a +1.0 delta at the dead-bit clear (Resurrection Signet's 100 %), so a
    revived body is re-anchored at 1.0 by the wire itself. The L2 check (the
    reconstruction <= 0.10 just after the killing batch) is printed over the MONK
    bodies' deaths -- the instrument the P2 threshold rests on -- and over the party's.
    A match END marks every surviving party body dead at ONE instant with health > 0
    (the defeat mark; RECONSTRUCTION); those are printed and not counted.
  * THE CONDITION BIT 0x02 (effects.STATUS_CONDITION) rides the monks' 0x00F1 words: it
    rises in the batch of the Fighter's Hamstring [46]. The 275 target's state is read
    off it; the observer is never a 275 target (the byte says other ALLY).
  * THE ENCHANTED BIT 0x80 (effects.STATUS_ENCHANTED) and the class visual pair
    [6, T, 13] + [6, T, 18] (a monk) / [6, T, 13] + [6, T, 11] (the Mage) rise together
    at the FIRST live enchantment on a body and fall together ([7]) when the LAST one
    ends -- every 0x80 transition on this tape coincides with a [6, T, 13] / [7, T, 13],
    except a body's FIRST 0x00F1 word: the status word is sent on change only, and a
    body created already enchanted carries its live [6] ids in its create batch and no
    0x80 word until its status next changes (Z-Monk#5, match 2: [6, 13] + [6, 18] at its
    create 215.62, first word 263.71). So the VISUAL is the primary instrument and the
    bit a control, None (no word yet) meaning unknown, never clean. 13 is SHARED: 271,
    272, 307, 180 and 184 completions all carry it when the body had no live 13 before,
    so it is a CLASS marker (bounds every enchantment episode on T from above), never a
    skill's own. No Monk enchantment has a skill-specific [6].
  * ATTACKS. 0x00A0 [4] (attack started) is sent per SWING: a monk's [4] at T, then
    [1] (GV_MELEE_ATTACK_FINISHED) or [3] (GV_ATTACK_STOPPED) ~0.5 s later, then the
    next [4]; a monk STOPS ([3]) to cast and resumes with a new [4]. No monk sends a
    [50] attack skill (none on the bar).
  * NO cast-time word: 0 of the Monks' 349 cast announces carries a 0x00A3 / 0x00A2
    [61] (the henchman Mage's and Fighter's casts do, at 0.67 x, as on the Z1 tape).
  * The team: the c2s 0x00A6 [map, team, 0] ENTER (CASTAI-ZF4) carries team 57 on every
    outpost connection of this tape, and every match is four 38888:124 Monks.

  Z2.P1  every 275 (Mend Condition) by a Monk body -> the target's condition bit at the
         announce (Conn.status_at), OR rising inside the announce's own batch (t <= ta +
         BATCH: a word's order inside one batch is not a time order; counted as carrying
         and printed apart as 'same batch'). Counterexample: the bit clear through
         ta + BATCH -> FAILED; none, with n >= 5 -> HELD; n < 5 -> NULL. 275's exe target
         byte is 4 (other ally, effects.OTHER_ALLY_TARGET): a Monk CANNOT Mend itself; a
         9F self form or an A0 naming the caster is printed as an anomaly and counted as
         a counterexample of the table, not of P1.
         Z2.P1b (a companion line, not a registered id -- the registration expected NO hex
         on a monk and called Smite Hex a named null): the Mage's Incendiary Bonds (179,
         an Elementalist hex) DOES hex the monks (their 0x800 bit rises), so 302 (Smite
         Hex) is scored by the same rule against the hexed bit, the 9F self form included
         (target byte 3, the caster is legal), floor 5 (SCORER'S RULE: Mend Condition's).
  Z2.P2  every 307 (Reversal of Fortune) by a Monk, both forms (the 9F form's target is
         the caster, L1): the target's reconstructed health JUST BEFORE the announce
         (Conn.health_at -- the same h_target column Z1.P3 and Z3.P4 read). At-or-below
         = round(h, 3) <= 0.700. One cast above the line -> FAILED (the registration says
         "every"); none, with n >= 10 -> HELD; n < 10 -> NULL. A second column prints the
         MINIMUM reconstruction inside the 1 s before the announce (the AI decides on a
         tick; a lead, never the verdict). A target dead at the announce, or with no
         reconstruction, is listed and not counted. The 9F form's caster-health reading
         is the same instrument.
  Z2.P3  the share of Z2.P2's casts whose target is NOT the caster: >= 0.25 -> HELD,
         else FAILED; under P2's floor of 10 -> NULL (SCORER'S RULE: the same casts, so
         the same floor).
  Z2.P4  272 (Balthazar's Aura) and 271 (Zealot's Fire) re-cast onto a body still carrying
         them -- RECONSTRUCTION: the previous COMPLETED cast of the same skill on T by any
         Monk, live for the exe's duration (272: 8 s, 271: 60 s; duration0 = duration15
         for both, so 'certain'), cut by T's death / re-create and by the class marker's
         [7, T, 13] (the last enchantment on T ended: an upper bound). Nothing on our
         side removes an enchantment (the party's bars carry no removal; the observer's
         casts are 1 / 2 / 153 / 364 / 2858 / 3443, none a removal). A counterexample is
         an announce of S at T while such an episode of S on T is live -> FAILED; none
         -> HELD, with the number of casts that HAD a live previous episode to overlap
         at all ('informative') printed: 272 recharges in 20 s and lives 8, 271 in 30 s
         and lives 60, so only a 271 re-cast, or a 272 onto ANOTHER monk, can overlap.
         251 (Scourge Healing): an announce at T with T's hexed bit 0x800 set at the
         announce (the Monks' only hex is 251, so on our bodies hexed = 251 live,
         RECONSTRUCTION), or on the observer a live 0x0042 [obs, 251] (EXACT) -> FAILED;
         none -> HELD; no 251 -> NULL. A second 251 announced at T while another Monk's
         251 on T is IN FLIGHT (announced, not yet completed) is printed apart and does
         not refute: T carried nothing yet.
  Z2.P5  every 68 (Drain Enchantment) by a Monk -> was the target enchanted at the
         announce? Observer: a live 0x0042 of an exe type-6 skill (EXACT). Henchman: the
         class visual [6, T, 13] live (Conn.live6) -- the PRIMARY instrument, OBSERVED
         rising with the Mage's 180 / 184 completions and falling with a 68's -- with the
         0x80 bit and a RECONSTRUCTION (the type-6 self-casts completed on T and still
         inside the exe's duration0, minus one per 68 completed on T since the oldest of
         them) printed beside it as controls; a visual / bit disagreement marks the row
         CONTESTED. Unenchanted = no live 13 (henchman) / no live type-6 0x0042
         (observer). One 68 at an unenchanted target -> FAILED; none, n >= 1 -> HELD.
         Every cast prints the seconds since the last [7, T, 13] and the other Monks'
         68s at the same T inside the 2 s before (a burst that stripped the target
         before this announce): the AI's decision may predate the strip -- a lead the
         reader can weigh, never the verdict.
  Z2.P6  per MONKS match, 1-s windows over the match span (the state read at each
         window's start instant), kept while >= 2 Monks are alive (the dead bit). A
         Monk's CURRENT TARGET at t is the target of its latest 0x00A0 [4] at or before t,
         held until its next [4]; it ENDS at the target's death, the Monk's own death /
         re-create, or 30 s without a [4] (castethogram.ATTACK_WINDOW). A [3] attack
         stopped does NOT end it (a Monk stops to cast and resumes on the same body). A
         window AGREES when every Monk holding a current target holds the same one; the
         HEADLINE denominator is windows with >= 2 alive AND >= 2 holders (one holder is
         vacuous); the counts over 1-holder and 0-holder windows are printed beside it.
         >= 80 % -> HELD, else FAILED; no window with >= 2 holders -> NULL. Every SWITCH
         -- a [4] naming a different target from the Monk's still-current one -- is
         listed (t, monk, from, to); a [4] after the current target ended (death /
         expiry) is a fresh pick and is counted apart.

CHANGES AFTER THE JUDGE (2026-09-28: a judge reconciled this scorer against three blind
replicators over 20260928T103123 and listed five fixes; each is applied here and dated
at its site, and none was chosen to move a verdict):
  1  castethogram.completion() skips an instant 0x009F [48] when it looks for the
     announce that supersedes a cast (a stance mid-cast is not a new cast). Z1.P4 21 ->
     22 (match 2 342.94's 109 -> Archer now completes); Z1.P6 38888:119 overlap 35 ->
     34. The old corpus's AI tables are unchanged: 3 of its end words moved, all
     OBSERVER casts, which are never scored.
  2  Z1.P3: for a skill whose target byte is 4 (other ally -- 286 Heal Other, the byte
     read off agents.WORLD) the caster is not a lowest-health candidate. 4/5 -> 5/5;
     the verdict stays NULL (n=5 < floor 20).
  3  Z1.P7 prints two verdicts (score_p7): (a) as registered and (b) with the early
     group required to hold >= 2 bodies; in both a body dead at the storm's next tick
     after its last strike did NOT leave (the first run's death flag was unused).
  4  Z1.P1's reconstructed durations: observed on the observer, else the 38888 exe's
     own row at the caster's attribute rank OBSERVED in 0x0042 field3 (observed_ranks,
     with its interpolation control printed), else the exe's duration0 labelled "rank
     unknown". The pinned agents.WORLD row is the last resort and says so. (The exe
     recharge was already in use: build_casts reads rechargeprobe.table_for.)
  5  Z3.P1 prints Obsidian Flame CASTS per target beside GROUPS per target (the first
     line's "targets" counted groups); castethogram's ALL-CASTS line labels arena casts
     '@zaishen' so the old corpus's HENCHMAN and the arena's never print as one sum.

Refuses (exit 2) when the capture is missing or holds no Zaishen arena connection.
Standard library only. Read-only: writes nothing.
"""
import argparse
import bisect
import collections
import json
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

import aotjoin          # noqa: E402  (rows_of: the Fire Storm join)
import castethogram as ce   # noqa: E402
import livewire         # noqa: E402
import rechargeprobe    # noqa: E402
import shoutjoin        # noqa: E402
import tape             # noqa: E402
import vaultpath        # noqa: E402
import weaponcensus as wc   # noqa: E402

DEFAULT_CAPTURE = "20260928T103123"
HENCH_NAME = {3: "Healer", 6: "Mage", 2: "Archer", 1: "Fighter"}
PROF = {1: "Warrior", 2: "Ranger", 3: "Monk", 4: "Necromancer", 5: "Mesmer", 6: "Elementalist"}
DEGENERATION = (1, 2, 4, 5)
OBSIDIAN = (6, 6, 6, 6)
MONKS = (3, 3, 3, 3)
WEAPON_TYPE = {2: "axe", 5: "bow", 12: "focus", 15: "hammer", 22: "wand", 24: "shield",
               26: "staff", 27: "sword", 32: "daggers", 35: "scythe", 36: "spear", 0: "empty"}
MELEE_TYPES = {2, 15, 27, 32, 35}          # axe, hammer, sword, daggers, scythe
# ids with a CORROBORATED name in the repo (effects.py, hexjoin, authsrv comments)
FIRE_STORM, MEND_AILMENT, ORISON, REMOVE_HEX = 197, 277, 281, 301
# WIKI (GWW infobox `id`, read 2026-09-28 through the browser, the revision in brackets):
# Arcane Conundrum 36 [2733017], Migraine 53 [2661567], Conjure Phantasm 31 [2731216],
# Phantom Pain 44 [2738389], Incendiary Bonds 179 [2733032], Healing Touch 313
# [2738562], Heal Area 280 [2692843], Earth Attunement 169 [2718873], Ward Against
# Melee 176 [2686635], Obsidian Flame (PvP) 2809 [2629756] (the PvE Obsidian Flame is
# 219 [2717091]; the Zaishen cast the PvP one). Each matches the table / exe row the
# tape carries (energy, activation, recharge) -- WIKI + client table, CORROBORATED.
ARCANE_CONUNDRUM, MIGRAINE = 36, 53
SKILL_NAME = {36: "Arcane Conundrum", 53: "Migraine", 31: "Conjure Phantasm", 44: "Phantom Pain",
              179: "Incendiary Bonds", 313: "Healing Touch", 280: "Heal Area",
              169: "Earth Attunement", 176: "Ward Against Melee", 2809: "Obsidian Flame (PvP)",
              197: "Fire Storm", 277: "Mend Ailment", 281: "Orison of Healing",
              282: "Word of Healing", 286: "Heal Other", 288: "Healing Breeze", 301: "Remove Hex"}
OBSIDIAN_FLAME, HEAL_AREA, EARTH_ATTUNEMENT, WARD_AGAINST_MELEE = 2809, 280, 169, 176
# CASTAI-Z2 -- WIKI (GWW infobox `id`, read 2026-09-29 through the app's browser, the
# revision in brackets), each NAMED ONLY AFTER `corroborate_ids` matches the id's
# energy / activation / recharge against the served build's exe row at run time (the
# triple the wiki page states, WIKI_TRIPLES): Balthazar's Aura 272 [2741459] (15 / 1.0 /
# 20), Mend Condition 275 [2683544] (5 / 0.75 / 2; target 'other allies'), Reversal of
# Fortune 307 [2741457] (5 / 0.25 / 2; already CORROBORATED in effects.py), Scourge
# Healing 251 [2683533] (10 / 2.0 / 5), Smite Hex 302 [2683750] (5 / 1.0 / 12), Zealot's
# Fire 271 [2695805] (10 / 0.25 / 30; self), Drain Enchantment 68 [2683731] (5 / 2.0 /
# 20; target foe); the Zaishen Mage's Aura of Restoration 180 [2732814] (5 / 0.25 / 20;
# self -- the PvE version, the page's own bug note); the Archer's Poison Arrow 404
# [2678681] (5 / 0 / 1); the Fighter's Hamstring 320 [2731374] (5 / 0 / 10). The team
# page is Smiting Monks [2647764]; Resurrection Signet 2 is effects.py's. Every other id
# on the Z2 tape (the Mage's 184 / 185 / 186, the Archer's 394 / 396 / 402 / 433 / 446,
# the Fighter's 1 / 322 / 327 / 383, the observer's 153 / 2858 / 3443) prints by number
# unless the repo already names it (364 "Charge!", effects.py; 197 Fire Storm;
# 179 Incendiary Bonds and 185 Mind Burn, hexjoin; 186 Fireball, aotjoin).
BALTHAZARS_AURA, MEND_CONDITION, REVERSAL_OF_FORTUNE, SCOURGE_HEALING = 272, 275, 307, 251
SMITE_HEX, ZEALOTS_FIRE, DRAIN_ENCHANTMENT, RESURRECTION_SIGNET = 302, 271, 68, 2
AURA_OF_RESTORATION, POISON_ARROW, HAMSTRING = 180, 404, 320
WIKI_TRIPLES = {                 # id: (energy, activation s, recharge s) as the wiki page states
    272: (15, 1.0, 20), 275: (5, 0.75, 2), 307: (5, 0.25, 2), 251: (10, 2.0, 5),
    302: (5, 1.0, 12), 271: (10, 0.25, 30), 68: (5, 2.0, 20), 180: (5, 0.25, 20),
    404: (5, 0.0, 1), 320: (5, 0.0, 10),
}
Z2_NAMES = {272: "Balthazar's Aura", 275: "Mend Condition", 307: "Reversal of Fortune",
            251: "Scourge Healing", 302: "Smite Hex", 271: "Zealot's Fire",
            68: "Drain Enchantment", 180: "Aura of Restoration", 404: "Poison Arrow",
            320: "Hamstring"}
MONK_BAR = {272, 275, 307, 251, 302, 271, 68, 2}      # the WIKI bar + Resurrection Signet
ENCHANTED_BIT = 0x80             # effects.STATUS_ENCHANTED; on the Z2 tape it rises / falls
                                 # with the class visual 13 (the docstring's instruments)
ENCH_CLASS_VISUAL = 13           # [6, T, 13]: the shared 'enchanted' class marker, MEASURED
                                 # on 20260929T100038 (271 / 272 / 307 / 180 / 184 add it on a
                                 # clean body; a 68's completion removes it)
ATTACK_HOLD = ce.ATTACK_WINDOW   # 30 s: a [4] older than this no longer names a current target
ENCH_DURATION = {272: 8.0, 271: 60.0}   # exe 38888 duration0 = duration15 (checked at run time)
HEX_REMOVERS = {REMOVE_HEX}
# The Healer's heal skills, as cast on this tape: 281 / 282 / 286 / 288 (names
# CORROBORATED in the repo) and 313 (Healing Touch, WIKI id above). Its 301 / 2 / 314
# are not heals.
HEAL_SKILLS = {281, 282, 286, 288, 313}
HEX_BIT, COND_BIT, DEAD_BIT = 0x800, 0x02, 0x10
OTHER_ALLY_BYTE = 4            # effects.TARGET_KINDS[4] 'other_ally': never the caster
PROP_CAST_TIME = 61
FLOORS = {"Z1.P1": 10, "Z1.P2": 5, "Z1.P3": 20, "Z1.P7": 3, "Z3.P3": 5,
          "Z2.P1": 5, "Z2.P1b": 5, "Z2.P2": 10, "Z2.P3": 10}
ROF_LINE = 0.70                  # Z2.P2: "at or below 70 %" (WIKI rev 2741457, the hero rule)
P3_SHARE, P6_SHARE = 0.25, 0.80
WINDOW_S, LEAD_S, BURST_S = 1.0, 1.0, 2.0
BATCH = 0.05
OBSIDIAN_WINDOW, HEALAREA_WINDOW, WARD_WINDOW = 1.5, 2.0, 3.0
ATTUNE_MIN_GAP = 0.228


def f32(bits):
    return struct.unpack("<f", struct.pack("<I", int(bits) & 0xFFFFFFFF))[0]


def med(xs):
    return round(statistics.median(xs), 3) if xs else None


# ------------------------------------------------------------------ decoding
def prefix_decode(capdir, conn_file):
    """(conn, merged, cut) for a connection whose s2c the sniffer left GAPPED: the s2c
    PREFIX before the first seq discontinuity, decoded whole, plus the c2s decoded whole.
    cut = {plain_bytes, plain_total, gap_seq_expected, gap_seq_got, gap_bytes, t_last,
    t_gap, messages}. Raises ValueError when the prefix does not frame whole, when the
    c2s does not, or when there is no gap (decode_conn is the reader then)."""
    conn, plain = None, b""
    for line in open(os.path.join(capdir, conn_file), encoding="utf-8", errors="replace"):
        try:
            r = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if r.get("kind") == "version" and r.get("connection"):
            conn = r["connection"]
        elif r.get("kind") == "frame" and r.get("direction") == "s2c":
            plain += bytes.fromhex(r.get("plain") or "")
    if not conn or not plain:
        raise ValueError("no s2c plaintext")
    left, right = conn.split("->")
    segs = tape._segments(os.path.join(capdir, "wire.jsonl"), (left, right), "s2c")
    events, off, skip, prev_end, gap = [], 0, livewire.HANDSHAKE_S2C, None, None
    t_last = None
    for seq, t, payload in segs:
        if prev_end is not None and seq != prev_end:
            gap = (prev_end, seq, (seq - prev_end) & 0xFFFFFFFF, t)
            break
        prev_end = (seq + len(payload)) & 0xFFFFFFFF
        if skip:
            take = min(skip, len(payload))
            payload, skip = payload[take:], skip - take
            if not payload:
                continue
        events.append((t, plain[off:off + len(payload)]))
        off += len(payload)
        t_last = t
    if gap is None:
        raise ValueError("no seq discontinuity: not a gapped connection")
    cod = livewire._get_codec()
    msgs, rc = tape.decode_all(events, cod, channel="GAME_SMSG", mask=0, strict=False)
    if rc.err is not None or rc.consumed != rc.total:
        raise ValueError(f"the prefix does not frame whole: {rc.consumed}/{rc.total} {rc.err}")
    _c, c2s_ev, c2s_err = livewire.build_events(capdir, conn_file, "c2s")
    if c2s_err is not None or not c2s_ev:
        raise ValueError(f"c2s refused: {c2s_err}")
    cm, rc2 = tape.decode_all(c2s_ev, cod, channel="GAME_CMSG", mask=livewire.CMSG_MASK,
                              strict=False)
    if rc2.err is not None or rc2.consumed != rc2.total:
        raise ValueError(f"c2s does not frame whole: {rc2.consumed}/{rc2.total}")
    merged = [(t, "s2c", op, v) for t, op, v in msgs] + [(t, "c2s", op, v) for t, op, v in cm]
    merged.sort(key=lambda r: (r[0], 0 if r[1] == "c2s" else 1))
    cut = {"plain_bytes": off, "plain_total": len(plain), "gap_seq_expected": gap[0],
           "gap_seq_got": gap[1], "gap_bytes": gap[2], "t_last": t_last, "t_gap": gap[3],
           "messages": len(msgs), "c2s_messages": len(cm)}
    return conn, merged, cut


# ------------------------------------------------------------------ one match
class Match:
    def __init__(self, n, stamp, port, conn, rows, cut, merged):
        self.n, self.stamp, self.port, self.conn, self.rows, self.cut = n, stamp, port, conn, rows, cut
        self.merged = merged
        self.s2c = conn.s2c
        self.obs = conn.observer
        t0 = min(t for t, _d, _o, _v in merged)
        t1 = max(t for t, _d, _o, _v in merged)
        self.span = (t0, t1)
        self.opp = sorted(a for a in conn.creates if conn.klass(a, t1) == "ZAISHEN")
        self.hench = {a: HENCH_NAME.get(conn.party[a][0], f"prof{conn.party[a][0]}")
                      for a in sorted(conn.hench)}
        self.opp_prof = {}
        for a in self.opp:
            d = conn.definition(a, t1)
            info = conn.defs.get(d)
            self.opp_prof[a] = info[1] if info else None
        profs = tuple(sorted(p for p in self.opp_prof.values() if p is not None))
        self.team = ("DEGENERATION" if profs == DEGENERATION else
                     "OBSIDIAN" if profs == OBSIDIAN else
                     "MONKS" if profs == MONKS else f"UNKNOWN{profs}")
        self.tag = f"match {n}" + (" (prefix)" if cut else "")

    def name(self, agent):
        if agent is None:
            return "none"
        if agent == self.obs:
            return "observer"
        if agent in self.hench:
            return self.hench[agent]
        if agent in self.opp_prof:
            p = PROF.get(self.opp_prof[agent], "?")
            same = [a for a, q in self.opp_prof.items() if q == self.opp_prof[agent]]
            return f"Z-{p}" + (f"#{agent}" if len(same) > 1 else "")
        return f"agent{agent}"

    def party(self):
        return [self.obs] + sorted(self.hench)

    def by_prof(self, prof):
        return [a for a, p in self.opp_prof.items() if p == prof]

    def healer(self):
        return next((a for a, nm in self.hench.items() if nm == "Healer"), None)

    def mage(self):
        return next((a for a, nm in self.hench.items() if nm == "Mage"), None)

    def dead_at(self, agent, t):
        st = self.conn.status_at(agent, t)
        return bool(st is not None and st & DEAD_BIT)

    def bit_rises(self, agent, bit):
        out, prev = [], 0
        for (t, w) in self.conn.status.get(agent, ()):
            if (w & bit) and not (prev & bit):
                out.append(t)
            prev = w
        return out

    def bit_clears_after(self, agent, bit, t0):
        """First time after t0 + BATCH the agent's status word lacks `bit`, or None."""
        for (t, w) in self.conn.status.get(agent, ()):
            if t > t0 + BATCH and not (w & bit):
                return t
        return None


def load(capdir, stamp, use_prefix):
    table = ce.skill_rows()
    exe = rechargeprobe._exe_tables()
    matches, refused, others = [], [], []
    chans = sorted(tape.channel_files(capdir),
                   key=lambda ch: ch["connection"].split("->")[0].rsplit(":", 1)[-1])
    vers, starts = {}, {}
    for ch in chans:
        try:
            vers[ch["file"]] = tape.client_version(capdir, ch["connection"])
        except Exception as exc:                                        # noqa: BLE001
            vers[ch["file"]] = exc
            continue
        # a match's NUMBER is its start among ALL arena connections, refused ones too
        # (the client's first c2s segment), so a refusal never renumbers the others
        if vers[ch["file"]]["map_id"] in ce.ZAISHEN_MAPS:
            left, right = ch["connection"].split("->")
            segs = tape._segments(os.path.join(capdir, "wire.jsonl"), (left, right), "c2s")
            starts[ch["file"]] = min(t for _s, t, _p in segs) if segs else float("inf")
    number = {f: i + 1 for i, f in enumerate(sorted(starts, key=starts.get))}
    for ch in chans:
        port = ch["connection"].split("->")[0].rsplit(":", 1)[-1]
        ver = vers[ch["file"]]
        if isinstance(ver, Exception):
            refused.append((port, None, f"no VERSION: {str(ver)[:60]}"))
            continue
        if ch["file"] in number:
            port = f"{port} (match {number[ch['file']]})"
        cut = None
        _c, merged, ok = livewire.decode_conn(capdir, ch["file"])
        if not ok:
            if not use_prefix:
                refused.append((port, ver["map_id"], "byte accounting open (gapped); --prefix scores its prefix"))
                continue
            try:
                _c, merged, cut = prefix_decode(capdir, ch["file"])
            except ValueError as exc:
                refused.append((port, ver["map_id"], f"prefix refused: {exc}"))
                continue
        observer, _p, why = shoutjoin.observer_of(merged)
        if observer is None:
            refused.append((port, ver["map_id"], f"no observer: {(why or '')[:60]}"))
            continue
        others.append((port, ver["map_id"], merged, observer, cut))
        if ver["map_id"] not in ce.ZAISHEN_MAPS:
            continue
        bare = port.split(" ")[0]
        conn = ce.Conn(stamp, bare, merged, observer, ver["build"], ver["map_id"])
        if not conn.zaishen:
            refused.append((port, ver["map_id"], "arena map without 0x01BF henchman adds"))
            continue
        rows = ce.build_casts(conn, table, rechargeprobe.table_for(ver["build"], exe), None)
        matches.append((number[ch["file"]], bare, conn, rows, cut, merged))
    matches.sort(key=lambda x: x[0])
    out = [Match(n, stamp, port, conn, rows, cut, merged)
           for (n, port, conn, rows, cut, merged) in matches]
    return out, refused, others, table


# ------------------------------------------------------------------ helpers
def completed(r):
    return r.get("end_prop") == ce.PROP_FINISHED and r.get("end_t") is not None


def observed_durations(matches):
    """{skill: [seconds]} from every 0x0042 on an observer (OBSERVED)."""
    d = collections.defaultdict(list)
    for m in matches:
        for (t, s, buff, dur, ia) in m.conn.applies.get(m.obs, ()):
            d[s].append(round(dur, 3))
    return d


# ------------------------------------------------------------------ durations (FIX 4)
# FIX 4 (2026-09-28, the judge): a hex never seen on the observer used to take the PINNED
# agents.WORLD row's duration0, and that pin is stale against the 38888 exe this tape
# was played on (135: WORLD 3..16, exe 4..18; 44's recharge WORLD 15, exe 10). The rows
# now come out of the exe OF THE CONNECTION'S BUILD, through the same exe map
# (rechargeprobe._exe_tables) and the same reader (skilltable.locate_table /
# parse_record) that rechargeprobe.table_for uses for activation / recharge -- kept
# whole here because table_for keeps only those two.
_EXE = {"map": None, "rows": {}}


def exe_skill_rows(build):
    """{skill: skilltable.parse_record row} out of the exe of `build`, or None."""
    if build in _EXE["rows"]:
        return _EXE["rows"][build]
    if _EXE["map"] is None:
        _EXE["map"] = rechargeprobe._exe_tables()
    exe = _EXE["map"].get(build)
    if exe is None:
        _EXE["rows"][build] = None
        return None
    import skilltable       # noqa: E402  (clientscan, stdlib-only; on sys.path above)
    with open(exe, "rb") as f:
        data = f.read()
    base, count, _score = skilltable.locate_table(data)
    rows = {sid: skilltable.parse_record(data, base, sid) for sid in range(count)}
    _EXE["rows"][build] = rows
    return rows


def observed_ranks(z1):
    """The caster's ATTRIBUTE RANK, OBSERVED: a 0x0042 [obs, S, field3, buff, f32] of a
    HEX S (exe type 4) whose completion (58) by exactly one ZAISHEN definition sits in
    the same batch carries that caster's rank in field3. Keyed (def_key, the exe row's
    attribute) -- a definition is one template, and npcdefs' rule keeps it inside its
    build. Two observations that disagree make the key CONTESTED (None, unusable).
    Scoped to hexes on purpose: on an attribute-less condition (attribute 51 -- 480..484)
    field3 carries the duration in seconds, not a rank (13 / 14 / 19 / 20 beside f32s of
    the same value on this tape).
    Returns (ranks {(def_key, attr): rank|None}, evidence {key: [...]}, control [...]):
    the control is the interpolation d0 + (d15 - d0) * rank / 15 against the f32 the
    same 0x0042 carries -- a check the formula can fail."""
    ev, control, unattributed = collections.defaultdict(list), [], []
    for m in z1:
        ex = exe_skill_rows(m.conn.build)
        if not ex:
            continue
        for (t, op, v) in m.s2c:
            if op != ce.OP_APPLY or len(v) <= 5 or v[1] != m.obs:
                continue
            sk = v[2]
            row = ex.get(sk)
            if not row or row["type_code"] != 4:
                continue
            casts = [r for r in m.rows if r["skill"] == sk and r["target"] == m.obs
                     and r["class"] == "ZAISHEN" and completed(r) and abs(r["end_t"] - t) <= BATCH]
            defs = {r["def_key"] for r in casts}
            if len(defs) != 1:
                unattributed.append((m.tag, round(t, 3), sk))
                continue
            dk = defs.pop()
            rank = int(v[3])
            ev[(dk, row["attribute"])].append((m.tag, round(t, 3), sk, rank))
            d0, d15 = float(row["duration0"]), float(row["duration15"])
            control.append((m.tag, round(t, 3), sk, dk, row["attribute"], rank, d0, d15,
                            round(d0 + (d15 - d0) * rank / 15.0, 3), round(f32(v[5]), 3)))
    ranks = {}
    for k, lst in ev.items():
        rs = {x[3] for x in lst}
        ranks[k] = rs.pop() if len(rs) == 1 else None
    return ranks, dict(ev), control, unattributed


def cast_duration(skill, def_key, build, obs_dur, ranks, table):
    """(certain, possible, how) for a hex `skill` cast by `def_key` on a non-observer.
    Order: OBSERVED on the observer -> the build's exe row at the caster's OBSERVED rank
    -> the exe row's duration0, rank unknown (possible to duration15) -> only without an
    exe for the build, the pinned agents.WORLD row, labelled so."""
    if obs_dur.get(skill):
        d = statistics.median(obs_dur[skill])
        return d, d, "duration as observed on the observer"
    ex = exe_skill_rows(build)
    row = ex.get(skill) if ex else None
    if row is not None:
        d0, d15 = float(row["duration0"]), float(row["duration15"])
        rk = ranks.get((def_key, row["attribute"]))
        if rk is not None:
            d = d0 + (d15 - d0) * rk / 15.0
            return d, d, (f"exe {build} {d0:g}..{d15:g} at rank {rk} (attribute "
                          f"{row['attribute']}, OBSERVED in 0x0042 field3) = {d:g}")
        return d0, max(d0, d15), f"exe {build} duration0 {d0:g} (rank unknown; possible to {d15:g})"
    row = table.get(skill, {})
    d0, d15 = float(row.get("duration0") or 0), float(row.get("duration15") or 0)
    return d0, max(d0, d15), f"PINNED agents.WORLD duration0 {d0:g} (no exe for {build}; rank unknown)"


def class_markers(z1):
    """{skill: marker id} -- the [6] id OTHER than 1 that a hex's completion batch adds on
    a non-observer target, most common per skill over the Z1 matches (OBSERVED; Z1.P4
    reads the Necromancer's). A marker's [7] on T says the LAST hex of that class on T has
    ended, so it bounds every episode of the class from above (added after the first run,
    which printed two 'possible' re-hexes of 109 that the Necromancer marker's [7] shows
    had ended 6 s before the re-cast)."""
    c = collections.defaultdict(collections.Counter)
    for m in z1:
        for r in m.rows:
            if r["type"] == 4 and completed(r) and r["target"] not in (None, m.obs, r["caster"]):
                for x in set(r["adds_on_target"]) - {1}:
                    c[r["skill"]][x] += 1
    return {s: cc.most_common(1)[0][0] for s, cc in c.items() if cc}


def hex_intervals(m, target, skill, rows, obs_dur, table, markers, ranks):
    """[(start, certain_end, possible_end, how)] of `skill` live on `target`.
    Observer: EXACT (0x0042/0x0044; both ends equal). Other: RECONSTRUCTION (the
    docstring), certain / possible per cast_duration (FIX 4: observed on the observer,
    else the build's exe row at the caster's observed rank, else its duration0 with the
    rank unknown), both cut by death / re-create / a hex removal / the hexed bit clearing
    / the skill's class marker's [7]."""
    conn = m.conn
    out = []
    if target == m.obs:
        for (t, s, buff, dur, ia) in conn.applies.get(target, ()):
            if s != skill:
                continue
            ends = [u for (u, b, iu) in conn.unapplies.get(target, ()) if b == buff and iu > ia]
            e = min(ends) if ends else float("inf")
            out.append((t, e, e, "observed 0x0042"))
        return out
    deaths = [t for (t, w) in conn.status.get(target, ()) if w & DEAD_BIT]
    creates = conn.create_t.get(target, [])
    removals = [r["end_t"] for r in rows if r["skill"] in HEX_REMOVERS and r["target"] == target
                and completed(r)]
    mk = markers.get(skill)
    mk_ends = [t for (t, sgn, eid) in conn.effects6.get(target, ()) if sgn < 0 and eid == mk]
    for r in rows:
        if r["skill"] != skill or r["target"] != target or not completed(r):
            continue
        if r["class"] != "ZAISHEN":
            continue
        dur, d15, how = cast_duration(skill, r["def_key"], conn.build, obs_dur, ranks, table)
        if dur <= 0:
            continue
        te = r["end_t"]
        st = conn.status_at(target, te + BATCH)
        if st is None or not (st & HEX_BIT):
            continue                      # the hex never showed on the target's status
        cuts = [x for x in deaths + creates + removals if x > te]
        cuts += [x for x in mk_ends if x > te + BATCH]
        clr = m.bit_clears_after(target, HEX_BIT, te)
        if clr is not None:
            cuts.append(clr)
        cut = min(cuts) if cuts else float("inf")
        out.append((te, min(te + dur, cut), min(te + max(d15, dur), cut), how))
    return out


def ready_time(m, r, rows):
    """When the caster's slot for r's skill was last READY before r's announce: the
    previous completion (or announce, if it never completed) + the exe recharge; the
    caster's create for a first cast."""
    prev = [x for x in rows if x["caster"] == r["caster"] and x["inc"] == r["inc"]
            and x["skill"] == r["skill"] and x["t"] < r["t"]]
    if not prev:
        ct = [c for c in m.conn.create_t.get(r["caster"], ()) if c <= r["t"]]
        return (ct[-1] if ct else m.span[0]), "first cast (from the create)"
    p = prev[-1]
    base = p["end_t"] if p["end_t"] is not None else p["t"]
    return base + float(r["recharge"] or 0), "previous completion + recharge"


def verdict_line(pid, verdict, text, would_fail):
    return f"[{verdict}] {pid}: {text}\n      would have gone the other way: {would_fail}"


# ------------------------------------------------------------------ Z1
def score_p1(z1, table, obs_dur, ranks):
    per, cx, inf_rows, possible = collections.Counter(), [], [], []
    n_all = collections.Counter()
    markers = class_markers(z1)
    dur_src = collections.defaultdict(set)
    for m in z1:
        for r in m.rows:
            if r["class"] != "ZAISHEN" or r["type"] != 4 or r["target"] in (None, r["caster"]):
                continue
            n_all[m.tag] += 1
            if r["target"] != m.obs:
                dur_src[r["skill"]].add(cast_duration(r["skill"], r["def_key"], m.conn.build,
                                                      obs_dur, ranks, table)[2])
            ivs = hex_intervals(m, r["target"], r["skill"], m.rows, obs_dur, table, markers, ranks)
            ta = r["t"]
            live = [iv for iv in ivs if iv[0] < ta - 1e-6 and iv[1] > ta]
            poss = [iv for iv in ivs if iv[0] < ta - 1e-6 and iv[1] <= ta < iv[2]]
            rt, _how = ready_time(m, r, m.rows)
            informative = bool(live) or any(iv[0] < ta and iv[1] > rt for iv in ivs)
            if poss and not live:
                possible.append((m.tag, round(ta, 2), m.name(r["caster"]), r["skill"],
                                 m.name(r["target"]), [(round(a, 2), round(b, 2), round(c, 2))
                                                       for a, b, c, _h in poss]))
            if informative:
                per[m.tag] += 1
                inf_rows.append((m.tag, round(ta, 2), m.name(r["caster"]), r["skill"],
                                 m.name(r["target"]), round(rt, 2), bool(live)))
            if live:
                cx.append((m.tag, round(ta, 2), m.name(r["caster"]), r["skill"],
                           m.name(r["target"]), [(round(a, 2), round(b, 2), h) for a, b, _c, h in live]))
    n_inf = sum(per.values())
    if cx:
        v = "FAILED"
    elif n_inf < FLOORS["Z1.P1"]:
        v = "NULL"
    else:
        v = "HELD"
    text = (f"opponent hex casts at another body n={sum(n_all.values())} {dict(n_all)}; "
            f"INFORMATIVE (the hex live on the chosen target while the slot was ready) "
            f"n={n_inf} {dict(per)} (floor {FLOORS['Z1.P1']}); counterexamples (live at the "
            f"announce) {len(cx)}; duration15-only 'possible' overlaps {len(possible)} (do not "
            f"refute); class markers used {markers}")
    wf = ("any one opponent hex announced onto a body whose same hex was live (observer: an open "
          "0x0042; henchman: inside the observed duration with the hexed bit set) -> FAILED; "
          f"with none, >= {FLOORS['Z1.P1']} informative casts were needed for HELD")
    return v, text, wf, {"cx": cx, "informative": inf_rows, "possible": possible,
                         "dur_src": {k: sorted(v_) for k, v_ in sorted(dur_src.items())}}


def score_p2(z1):
    rows, per = [], collections.Counter()
    for m in z1:
        h = m.healer()
        for r in m.rows:
            if r["caster"] != h or r["skill"] != REMOVE_HEX:
                continue
            per[m.tag] += 1
            T, ta = r["target"], r["t"]
            st = m.conn.status_at(T, ta)
            hexed_bit = bool(st is not None and st & HEX_BIT)
            obs_hex = []
            if T == m.obs:
                obs_hex = [(s, a) for (s, a) in ce.applies_live(m.conn, T, ta)
                           if (ce.skill_rows().get(s, {}).get("type_code") == 4)]
            rises = [t for t in m.bit_rises(T, HEX_BIT) if t <= ta]
            lat = round(ta - rises[-1], 3) if rises and hexed_bit else None
            rows.append((m.tag, round(ta, 2), m.name(T), r["form"], hexed_bit, obs_hex, lat,
                         r["end_prop"]))
    n = len(rows)
    clean = [x for x in rows if not x[4] and not x[5]]
    v = "NULL" if n < FLOORS["Z1.P2"] else ("FAILED" if clean else "HELD")
    text = (f"the Healer's Remove Hex (301) n={n} {dict(per)} (floor {FLOORS['Z1.P2']}); onto a "
            f"hexed target {n - len(clean)}, onto a clean one {len(clean)}; latency from the hexed "
            f"bit's rise (s) {[x[6] for x in rows]}")
    wf = (f"with >= {FLOORS['Z1.P2']} casts, any one at a target whose hexed bit was clear (and, "
          "on the observer, no live 0x0042 hex) -> FAILED")
    return v, text, wf, rows


def heal_rows(m, healer):
    """The Healer's HEALS: a completed cast of a heal skill (HEAL_SKILLS -- the ids whose
    heal IS the effect; 301 Remove Hex is not one, and its completion batch can carry a
    Healing Breeze tick's 55, which the first run counted as a heal)."""
    out = []
    for r in m.rows:
        if r["caster"] != healer or r["skill"] not in HEAL_SKILLS or not completed(r):
            continue
        out.append(r)
    return out


def score_p3(z1, table):
    other, lowest_ok, lowest_n, notes, orison = [], 0, 0, [], []
    per = collections.Counter()
    self_n = collections.Counter()
    unhurt = []
    excl = collections.Counter()
    for m in z1:
        h = m.healer()
        for r in heal_rows(m, h):
            if r["target"] == h:
                self_n[m.tag] += 1
                continue
            per[m.tag] += 1
            ta = r["t"]
            hp = {}
            for a in m.party():
                if m.dead_at(a, ta):
                    continue
                hp[a] = m.conn.health_at(a, ta)[0]
            # FIX 2 (2026-09-28, the judge): a skill whose target byte is 4 (OTHER ally --
            # 286 Heal Other; the byte read off agents.WORLD's skills row) cannot land on
            # its caster, so the caster is not a candidate for "the lowest-health ally". The
            # first run compared 286 at match 1 189.87 against the Healer's own 0.13.
            tbyte = table.get(r["skill"], {}).get("target")
            cand = dict(hp)
            if tbyte == OTHER_ALLY_BYTE and h in cand:
                del cand[h]
                excl[r["skill"]] += 1
            hurt = {a: x for a, x in cand.items() if x is not None and x < 0.99}
            t_h = r.get("h_target")
            is_hurt = (t_h is not None and t_h < 0.99) or (r.get("dmg_on_target_10s") or 0) > 0
            if not is_hurt:
                unhurt.append((m.tag, round(ta, 2), r["skill"], m.name(r["target"]), t_h))
            chosen_low = None
            if len(hurt) >= 2:
                lowest_n += 1
                low = min(hurt.values())
                chosen_low = t_h is not None and t_h <= low + 1e-3
                lowest_ok += bool(chosen_low)
            other.append((m.tag, round(ta, 2), r["skill"], m.name(r["target"]), t_h,
                          {m.name(a): x for a, x in sorted(hp.items())}, chosen_low,
                          f"target byte {tbyte}" + (" (caster not a candidate)"
                                                    if tbyte == OTHER_ALLY_BYTE else "")))
    for m in z1:
        h = m.healer()
        for r in heal_rows(m, h):
            if r["skill"] != ORISON:
                continue
            t_h = r.get("h_target")
            deficit = None if t_h is None else round(1 - t_h, 4)
            heal = r.get("heal_on_target")
            orison.append((m.tag, round(r["t"], 2), m.name(r["target"]), deficit, heal,
                           None if deficit is None or heal is None
                           else deficit + 1e-3 >= heal))
    n = len(other)
    share = None if not lowest_n else round(lowest_ok / lowest_n, 3)
    bad_orison = [x for x in orison if x[5] is False]
    if n < FLOORS["Z1.P3"]:
        v = "NULL"
    else:
        v = "HELD" if (not unhurt and (share is None or share >= 0.8) and not bad_orison) else "FAILED"
    text = (f"the Healer's heals landing on ANOTHER ally n={n} {dict(per)} (floor "
            f"{FLOORS['Z1.P3']}); on itself {sum(self_n.values())} {dict(self_n)}; on an unhurt "
            f"ally {len(unhurt)}; lowest-health chosen where >= 2 hurt {lowest_ok} of {lowest_n}"
            f" ({share}; the caster left out of the candidates for a target-byte-4 skill "
            f"{dict(excl)}); Orison of Healing (281) n={len(orison)}, landed with deficit < heal "
            f"{len(bad_orison)}")
    wf = (f"with >= {FLOORS['Z1.P3']} heals on another ally: any heal on an unhurt ally, the "
          "lowest-health ally chosen in < 80 % of the >= 2-hurt casts, or an Orison landing "
          "more than the target's deficit -> FAILED")
    return v, text, wf, {"other": other, "orison": orison, "unhurt": unhurt}


def score_p4(z1):
    inst = []
    for m in z1:
        necro = m.by_prof(4)
        for r in m.rows:
            if r["caster"] not in necro or r["type"] != 4 or not completed(r):
                continue
            if r["target"] in (None, m.obs, r["caster"]):
                continue
            ids = list(r["adds_on_target"])
            others = sorted(set(ids) - {1})
            clean = 1 in ids and len(others) == 1
            inst.append((m.tag, round(r["t"], 2), r["skill"], m.name(r["target"]), ids, clean,
                         others[0] if clean else None))
    clean = [x for x in inst if x[5]]
    xs = collections.Counter(x[6] for x in clean)
    good = [x for x in clean if x[6] not in (12, 4)]
    if not inst:
        v = "NULL"
    elif good:
        v = "HELD"
    else:
        v = "FAILED" if clean else "NULL"
    text = (f"Necromancer-body hexes completing on a non-observer n={len(inst)}; clean "
            f"([6,T,1] + exactly one other id) {len(clean)}; the other id {dict(xs)}")
    wf = ("every clean instance carrying 12 or 4 as its other id (an Elementalist / Mesmer "
          "marker), or no [6,T,1] at all -> FAILED; no clean instance -> NULL")
    return v, text, wf, inst


def score_p5(z1, others, table):
    words = []
    for port, map_id, merged, obs, cut in others:
        for t, d, op, v in merged:
            if d != "s2c" or len(v) < 3 or v[1] != PROP_CAST_TIME:
                continue
            if op == ce.OP_FLOAT_T and len(v) > 4 and v[2] == obs:
                words.append((port, map_id, round(t, 3), "0x00A3", v[3], round(f32(v[4]), 3)))
            elif op == ce.OP_FLOAT and len(v) > 3 and v[2] == obs:
                words.append((port, map_id, round(t, 3), "0x00A2", None, round(f32(v[3]), 3)))
    casts = []
    for m in z1:
        mes = set(m.by_prof(5))
        mes_hexes = {r["skill"] for r in m.rows if r["caster"] in mes and r["type"] == 4}
        for r in m.rows:
            if r["caster"] != m.obs or r["form"] not in ("A0[60]", "9F[60]"):
                continue
            ta = r["t"]
            live = [(s, a) for (s, a) in ce.applies_live(m.conn, m.obs, ta) if s in mes_hexes]
            # the word rides the announce's own batch (r["t"] is rounded to the ms, so the
            # batch window, not "t <= ta", decides -- the first run's cut missed it)
            w61 = [(round(t, 3), op, v) for t, op, v in m.conn.batch_ops(ta)
                   if op in (ce.OP_FLOAT, ce.OP_FLOAT_T) and len(v) > 2 and v[1] == PROP_CAST_TIME
                   and v[2] == m.obs]
            casts.append((m.tag, round(ta, 2), r["skill"], table.get(r["skill"], {}).get("type_code"),
                          r["activation"], live, [(t, round(f32(v[-1]), 3)) for t, op, v in w61]))
    under = [c for c in casts if c[5]]
    per_hexset = collections.defaultdict(lambda: [0, 0])
    for c in under:
        k = tuple(sorted(s for s, _a in c[5]))
        per_hexset[k][0] += 1
        per_hexset[k][1] += bool(c[6])
    reg = [c for c in under if c[3] in (4, 5, 6)
           and any(s in (ARCANE_CONUNDRUM, MIGRAINE) for s, _a in c[5])]
    with_word = [c for c in reg if c[6]]
    if with_word:
        v = "HELD"
    elif reg:
        v = "FAILED"
    else:
        v = "NULL"
    text = (f"property-61 words naming the observer, whole capture n={len(words)} {words}; "
            f"observer spells announced under Arcane Conundrum (36) or Migraine (53) n={len(reg)}"
            f", carrying a 61 word naming the observer {len(with_word)}; every observer cast "
            f"under any Mesmer-body hex n={len(under)} of {len(casts)} announced, per live-hex "
            f"set (casts, with a word) "
            f"{ {k: tuple(v_) for k, v_ in sorted(per_hexset.items())} }")
    wf = ("an observer spell announced under a live 36 / 53 with no property-61 word naming the "
          "observer in its batch -> FAILED")
    return v, text, wf, {"words": words, "casts": casts}


def energy_foe_slot(table, rec_skill, sk):
    row = table.get(sk, {})
    return row.get("target") == 5 and not row.get("adrenaline") and sk != 2


def score_p6(z1, table):
    per_def = collections.defaultdict(list)
    for m in z1:
        for r in m.rows:
            if r["class"] == "ZAISHEN" and r["def_key"] and r["form"] in ("A0[60]", "9F[60]", "A0[50]", "9F[48]"):
                per_def[r["def_key"]].append((m, r))
    out = {}
    for dk, lst in per_def.items():
        n = len(lst)
        skills = collections.Counter(r["skill"] for _m, r in lst)
        overlap, violations = 0, []
        for m, r in lst:
            body = [x for x in m.rows if x["caster"] == r["caster"] and x["inc"] == r["inc"]]
            seen = {}
            for x in body:
                if x["t"] < r["t"]:
                    seen[x["skill"]] = x
            ready_now = []
            for sk, last in seen.items():
                if not energy_foe_slot(table, None, sk):
                    continue
                base = last["end_t"] if last["end_t"] is not None else last["t"]
                if base + float(last["recharge"] or 0) <= r["t"]:
                    ready_now.append(sk)
            if len(ready_now) >= 2:
                overlap += 1
            prev_same = seen.get(r["skill"])
            if prev_same is None or not energy_foe_slot(table, None, r["skill"]):
                continue
            between = {x["skill"] for x in body if prev_same["t"] < x["t"] < r["t"]}
            for sk, last in seen.items():
                if sk == r["skill"] or not energy_foe_slot(table, None, sk) or sk in between:
                    continue
                if last["t"] >= prev_same["t"]:
                    continue
                base = last["end_t"] if last["end_t"] is not None else last["t"]
                ready = base + float(last["recharge"] or 0)
                if ready <= prev_same["t"]:
                    violations.append((m.tag, round(prev_same["t"], 2), round(r["t"], 2),
                                       m.name(r["caster"]), r["skill"], sk, round(ready, 2)))
        out[dk] = {"n": n, "skills": dict(skills), "overlap": overlap, "violations": violations,
                   "bar": n >= 30 and overlap > 0 and len(skills) >= 2}
    at_bar = [dk for dk, x in out.items() if x["bar"]]
    viol = [dk for dk in at_bar if out[dk]["violations"]]
    v = "NULL" if not at_bar else ("HELD" if viol else "FAILED")
    text = (f"ZAISHEN definitions at the bar (>= 30 casts, >= 2 skills, an announce with >= 2 "
            f"energy foe slots ready) {at_bar}; of those with a slot re-fired while another ready "
            f"slot waited {viol}; per definition (n, overlap announces, violations): "
            + ", ".join(f"{dk}=({x['n']}, {x['overlap']}, {len(x['violations'])})"
                        for dk, x in sorted(out.items())))
    wf = ("a definition at the bar whose every re-fire came only after every other ready "
          "energy foe slot had fired since its previous cast (round robin's order) -> FAILED")
    return v, text, wf, out


def fire_storms(m, caster):
    seq = [(i, t, op, list(v)) for i, (t, op, v) in enumerate(m.s2c)]
    return [r for r in aotjoin.rows_of(seq, FIRE_STORM) if r["caster"] == caster]


def score_p7(z1):
    """FIX 3 (2026-09-28, the judge): two verdicts, both printed.
    (a) AS REGISTERED (FINDINGS 18: "leaves the circle together ... within its first 3
        damaging ticks"; "Floor: 3 Fire Storms landing on >= 2 opponents"): the unit is a
        storm whose ticks strike >= 2 opponents anywhere; its EARLY group is the opponents
        struck in damaging ticks 1-3; it LEFT when every early body left -- struck by no
        damaging tick after the 3rd, AND alive at the storm's next tick after its last
        strike (completion + that tick's k + 1 s). A body dead by then did not leave: its
        absence is its death. (The first run's `died_in_window` flagged any death inside
        10 s and did not use it. Match 1 197.05's early Z-Mesmer is still LEFT under this
        rule: last struck at damaging tick 1 (+1.0 s), alive and unstruck at +2 s, its
        dead bit at +5.08 s, after the storm's +3.0 s ground visual -- it left, then died
        to other damage; the fate string prints the later death.)
    (b) THE EARLY GROUP REQUIRED TO HOLD >= 2 BODIES: the unit is a storm whose ticks 1-3
        strike >= 2 opponents -- "an opponent GROUP inside the storm" -- same LEFT rule,
        same floor 3, applied to that unit.
    Neither counts a death as leaving."""
    storms, qual = [], []
    for m in z1:
        mage = m.mage()
        opp = set(m.opp)
        for r in fire_storms(m, mage):
            if r.get("completion_t") is None:
                storms.append((m.tag, round(r["announce_t"], 2), "no completion", None))
                continue
            ticks = r.get("ticks", [])
            struck = collections.defaultdict(list)
            for i, x in enumerate(ticks):
                for w in x["fs_words"]:
                    if w[0] in opp:
                        struck[w[0]].append(i + 1)
            row = {"tag": m.tag, "t": round(r["announce_t"], 2), "tick_ks": r.get("tick_ks"),
                   "struck": {m.name(a): v for a, v in struck.items()}}
            storms.append((m.tag, row["t"], row, None))
            if len(struck) >= 2:
                tc = r["completion_t"]
                grp = [a for a, v in struck.items() if min(v) <= 3]
                fate, stayed, died = {}, [], []
                for a in grp:
                    later = [k for k in struck[a] if k > 3]
                    if later:
                        fate[m.name(a)] = f"stayed (struck again at damaging tick {later})"
                        stayed.append((m.name(a), later))
                        continue
                    last = max(struck[a])
                    t_next = tc + ticks[last - 1]["k"] + 1 + BATCH
                    if m.dead_at(a, t_next):
                        dt = [t for (t, w) in m.conn.status.get(a, ()) if w & DEAD_BIT and t <= t_next]
                        fate[m.name(a)] = (f"DIED (dead at the next tick, completion+"
                                           f"{t_next - tc - BATCH:.0f} s; dead bit at +"
                                           f"{(dt[-1] - tc) if dt else float('nan'):.2f} s) -- not leaving")
                        died.append(m.name(a))
                    else:
                        later_d = [t for (t, w) in m.conn.status.get(a, ())
                                   if w & DEAD_BIT and t_next < t <= tc + 11.0]
                        fate[m.name(a)] = (f"left (last struck at damaging tick {last}, alive and "
                                           f"unstruck at completion+{t_next - tc - BATCH:.0f} s"
                                           + (f"; died LATER, dead bit at +{later_d[0] - tc:.2f} s"
                                              if later_d else "") + ")")
                row["group"] = [m.name(a) for a in grp]
                row["stayed_past_tick3"] = stayed
                row["died_not_left"] = died
                row["fate"] = fate
                row["left"] = bool(grp) and not stayed and not died
                qual.append(row)

    def verdict(unit):
        n_, left_ = len(unit), sum(1 for q in unit if q["left"])
        if n_ < FLOORS["Z1.P7"]:
            return "NULL", n_, left_
        return ("HELD" if left_ == n_ else "FAILED"), n_, left_

    va, na, la = verdict(qual)
    vb, nb, lb = verdict([q for q in qual if len(q["group"]) >= 2])
    text = (f"Fire Storms by the Mage n={len(storms)}. (a) AS REGISTERED: storms striking >= 2 "
            f"opponents n={na} (floor {FLOORS['Z1.P7']}); whose early (ticks 1-3) group all left "
            f"inside the first 3 damaging ticks {la} -> {va}. (b) EARLY GROUP >= 2 BODIES: storms "
            f"whose ticks 1-3 strike >= 2 opponents n={nb} (floor {FLOORS['Z1.P7']}); all left "
            f"{lb} -> {vb}. A death is never counted as leaving (bodies that died instead: "
            f"{[(q['tag'], q['t'], q['died_not_left']) for q in qual if q['died_not_left']]})")
    wf = (f"(a) with >= {FLOORS['Z1.P7']} storms on >= 2 opponents: any storm with an early-struck "
          "opponent struck again after the third damaging tick, or dead instead of gone -> FAILED; "
          f"(b) the same over storms whose early group holds >= 2 bodies, NULL below "
          f"{FLOORS['Z1.P7']} of them. The headline verdict is (a), the registered one")
    return va, text, wf, {"storms": storms, "qualifying": qual, "b": (vb, nb, lb)}


# ------------------------------------------------------------------ Z3
def score_z3(m3):
    res = {}
    opp = set(m3.opp)
    rows = m3.rows
    # P1 Obsidian Flame groups
    of = sorted([r for r in rows if r["caster"] in opp and r["skill"] == OBSIDIAN_FLAME],
                key=lambda r: r["t"])
    used, groups = set(), []
    for i, r in enumerate(of):
        if i in used:
            continue
        g = [i]
        for j in range(i + 1, len(of)):
            if of[j]["t"] - r["t"] > OBSIDIAN_WINDOW:
                break
            if j not in used and of[j]["target"] == r["target"]:
                g.append(j)
        used.update(g)
        casters = {of[k]["caster"] for k in g}
        groups.append((round(r["t"], 2), m3.name(r["target"]), len(g), len(casters),
                       r.get("h_target")))
    in3 = sum(g[2] for g in groups if g[2] >= 3)
    share = None if not of else round(in3 / len(of), 3)
    v = "NULL" if not of else ("HELD" if share >= 0.5 else "FAILED")
    # FIX 5 (2026-09-28, the judge): the first line printed only the GROUP count per
    # target, which reads as casts; both are printed now, every party body named (a
    # zero is a finding: the Archer drew none).
    per_cast = collections.Counter({m3.name(a): 0 for a in m3.party()})
    per_cast.update(m3.name(r["target"]) for r in of)
    per_group = collections.Counter({m3.name(a): 0 for a in m3.party()})
    per_group.update(g[1] for g in groups)
    res["Z3.P1"] = (v, f"Obsidian Flame (2809) casts n={len(of)}; groups on one target inside "
                    f"{OBSIDIAN_WINDOW} s: sizes {collections.Counter(g[2] for g in groups)}; casts "
                    f"in a group of >= 3: {in3} ({share}); CASTS per target {dict(per_cast)} of "
                    f"{len(of)}; GROUPS per target {dict(per_group)} of {len(groups)}",
                    "fewer than half of the Obsidian Flames in a >= 3 group (SCORER'S RULE) -> FAILED",
                    groups)
    # P2 Ward Against Melee after a melee attack start on an Elementalist
    items = wc.items_of(m3.s2c)
    hands = wc.hands_timeline(m3.s2c)
    melee = []
    for a, lst in m3.conn.attack_starts.items():
        if a in opp:
            continue
        for (t, tgt) in lst:
            if tgt not in opp:
                continue
            held = wc.held_at(hands, a, t)
            typ = wc.held_type(items, held[0]) if held else None
            if typ in MELEE_TYPES:
                melee.append((round(t, 2), m3.name(a), m3.name(tgt), WEAPON_TYPE.get(typ, typ)))
    all_att = [(m3.name(a), m3.name(tg)) for a, lst in m3.conn.attack_starts.items() if a not in opp
               for (t, tg) in lst if tg in opp]
    bar_ids = collections.Counter(r["skill"] for r in rows if r["caster"] in opp)
    res["Z3.P2"] = ("UNTESTED" if not melee else "NULL",
                    f"melee attack starts on an Elementalist n={len(melee)} (every attack start "
                    f"on one n={len(all_att)}, by {collections.Counter(a for a, _ in all_att)}); "
                    f"the Elementalists' cast ids {dict(bar_ids)}; Ward Against Melee (176) "
                    f"n={bar_ids.get(WARD_AGAINST_MELEE, 0)}",
                    "a melee attack start on an Elementalist with no ward within 3 s -> FAILED; "
                    "none of our party held a melee weapon in match 3, so the trigger never occurred",
                    melee)
    # P3 Mend Ailment / Remove Hex
    rm = []
    for r in rows:
        if r["caster"] not in opp or r["skill"] not in (MEND_AILMENT, REMOVE_HEX):
            continue
        T = r["target"]
        st = m3.conn.status_at(T, r["t"])
        bit = COND_BIT if r["skill"] == MEND_AILMENT else HEX_BIT
        rm.append((round(r["t"], 2), r["skill"], m3.name(r["caster"]), m3.name(T), r["form"],
                   None if st is None else bool(st & bit)))
    nma = sum(1 for x in rm if x[1] == MEND_AILMENT)
    clean = [x for x in rm if x[5] is False]
    v = "NULL" if nma < FLOORS["Z3.P3"] else ("FAILED" if clean else "HELD")
    res["Z3.P3"] = (v, f"Mend Ailment (277) n={nma} (floor {FLOORS['Z3.P3']}), Remove Hex (301) "
                    f"n={len(rm) - nma}; onto a target without the matching status bit {len(clean)} "
                    f"({collections.Counter(x[1] for x in clean)}); self-form (9F) casts "
                    f"{sum(1 for x in rm if x[4] == '9F[60]')}",
                    f"with >= {FLOORS['Z3.P3']} Mend Ailments, any 277 at a body with no condition "
                    "bit or 301 at one with no hexed bit -> FAILED", rm)
    # P4 Heal Area
    ha = sorted([r for r in rows if r["caster"] in opp and r["skill"] == HEAL_AREA], key=lambda r: r["t"])
    trig = [(round(r["t"], 2), m3.name(r["caster"]), r.get("h_caster")) for r in ha]
    pairs = [(round(a["t"], 2), round(b["t"], 2)) for i, a in enumerate(ha) for b in ha[i + 1:]
             if b["t"] - a["t"] <= HEALAREA_WINDOW and b["caster"] != a["caster"]]
    hs = [x[2] for x in trig if x[2] is not None]
    res["Z3.P4"] = ("NULL" if not ha else ("HELD" if pairs else "FAILED"),
                    f"Heal Area (280) n={len(ha)}; the caster's reconstructed health at the "
                    f"announce min/median/max {min(hs) if hs else None}/{med(hs)}/"
                    f"{max(hs) if hs else None}; pairs by different casters inside "
                    f"{HEALAREA_WINDOW} s {len(pairs)}",
                    "no two Heal Areas by different Elementalists inside 2 s -> FAILED", trig)
    # P5 Earth Attunement
    ea = collections.defaultdict(list)
    for r in rows:
        if r["caster"] in opp and r["skill"] == EARTH_ATTUNEMENT:
            ea[(r["caster"], r["inc"])].append(r)
    recasts = []
    for (c, inc), lst in ea.items():
        for a, b in zip(lst, lst[1:]):
            ids = set(a["adds_on_target"])
            rem = [t for (t, sgn, eid) in m3.conn.effects6.get(c, ())
                   if sgn < 0 and eid in ids and (a["end_t"] or a["t"]) < t < b["t"]]
            gap = round(b["t"] - rem[0], 3) if rem else None
            recasts.append((m3.name(c), round(a["t"], 2), round(b["t"], 2), gap))
    bad = [x for x in recasts if x[3] is None or x[3] < ATTUNE_MIN_GAP]
    res["Z3.P5"] = ("NULL" if not recasts else ("FAILED" if bad else "HELD"),
                    f"Earth Attunement (169) casts n={sum(len(v) for v in ea.values())} over "
                    f"{len(ea)} bodies; re-casts n={len(recasts)}",
                    "a re-cast with no [7] of its [6] since, or < 0.228 s after it -> FAILED",
                    recasts)
    return res


# ------------------------------------------------------------------ Z2
def corroborate_ids(build):
    """(named {id: name}, mismatches [(id, wiki triple, exe triple)]): a Z2 id is named
    only when the exe of `build` carries the wiki page's energy / activation / recharge
    (WIKI_TRIPLES). A check the exe can fail: a mismatch prints the id by number."""
    ex = exe_skill_rows(build) or {}
    named, bad = {}, []
    for sid, (e, a, r) in sorted(WIKI_TRIPLES.items()):
        row = ex.get(sid)
        got = None if row is None else (int(row["energy"]), float(row["activation"]),
                                        float(row["recharge"]))
        if got is not None and got[0] == e and abs(got[1] - a) < 1e-6 and abs(got[2] - r) < 1e-6:
            named[sid] = Z2_NAMES[sid]
        else:
            bad.append((sid, (e, a, r), got))
    durs = {}
    for sid, d in ENCH_DURATION.items():
        row = ex.get(sid)
        durs[sid] = (None if row is None else
                     (float(row["duration0"]), float(row["duration15"])), d)
    return named, bad, durs


def z2n(sid, named):
    return f"{sid} {named[sid]}" if sid in named else f"{sid}"


def monk_rows(z2, skill):
    for m in z2:
        for r in m.rows:
            if r["class"] == "ZAISHEN" and r["skill"] == skill:
                yield m, r


def bit_state(m, agent, bit, ta):
    """(carrying, how): the status bit at the announce (words strictly before), or a
    word carrying it inside the announce's own batch (ta .. ta + BATCH)."""
    st = m.conn.status_at(agent, ta)
    if st is not None and st & bit:
        return True, "at the announce"
    for (t, w) in m.conn.status.get(agent, ()):
        if ta - 1e-9 <= t <= ta + BATCH and (w & bit):
            return True, "same batch"
    return False, ("clear" if st is not None else "clear (no status word yet)")


def bit_context(m, agent, bit, ta):
    """(seconds since the bit last CLEARED before ta, seconds until it next RISES after
    ta) -- printed on every P1 / P1b clean-target row after the first run, as context
    (a decision made on a state that had just ended, or a cast that preceded the
    condition); the verdict does not read it."""
    prev_w, last_clear, next_rise = 0, None, None
    for (t, w) in m.conn.status.get(agent, ()):
        if t < ta - 1e-9:
            if (prev_w & bit) and not (w & bit):
                last_clear = t
        elif next_rise is None and (w & bit) and not (prev_w & bit):
            next_rise = t
        prev_w = w
    return (None if last_clear is None else round(ta - last_clear, 3),
            None if next_rise is None else round(next_rise - ta, 3))


def score_z2_p1(z2, named):
    out = {}
    for pid, skill, bit, bname in (("Z2.P1", MEND_CONDITION, COND_BIT, "condition bit 0x02"),
                                   ("Z2.P1b", SMITE_HEX, HEX_BIT, "hexed bit 0x800")):
        rows, per, anomalies = [], collections.Counter(), []
        for m, r in monk_rows(z2, skill):
            T, ta = r["target"], r["t"]
            per[m.tag] += 1
            carrying, how = bit_state(m, T, bit, ta)
            if skill == MEND_CONDITION and (r["form"] == "9F[60]" or T == r["caster"]):
                anomalies.append((m.tag, round(ta, 2), m.name(r["caster"]), r["form"]))
            rows.append((m.tag, round(ta, 2), m.name(r["caster"]), r["form"], m.name(T),
                         carrying, how, r["end_prop"],
                         None if carrying else bit_context(m, T, bit, ta)))
        n = len(rows)
        clean = [x for x in rows if not x[5]]
        same_batch = sum(1 for x in rows if x[6] == "same batch")
        v = "NULL" if n < FLOORS[pid] else ("FAILED" if clean else "HELD")
        # POST-HOC (after the first run printed [FAILED] 2 of 92 for P1 and 2 of 29 for
        # P1b): the registered rule counts a bit RISING inside the announce's batch as
        # carrying but not a bit that CLEARED inside it -- and both P1 counterexamples
        # carry a clear word < 1 ms before the announce (the same batch: the condition
        # ended in the tick the Monk announced in). The symmetric reading -- the bit set
        # at any instant inside ta +/- BATCH -- was NOT pre-registered; its verdict is
        # printed as a lead beside the registered one, which stands.
        sym_clean = [x for x in clean if x[8] is None or x[8][0] is None or x[8][0] > BATCH]
        v_sym = "NULL" if n < FLOORS[pid] else ("FAILED" if sym_clean else "HELD")
        forms = collections.Counter(x[3] for x in rows)
        extra = ""
        if skill == SMITE_HEX:
            rises = {m.tag: sum(len(m.bit_rises(a, HEX_BIT)) for a in m.opp) for m in z2}
            extra = (f"; hexed-bit rises on the Monks per match {rises} (the Mage's 179, an "
                     f"Elementalist hex -- the registration expected none)")
        text = (f"{z2n(skill, named)} by a Monk n={n} {dict(per)} (floor {FLOORS[pid]}); forms "
                f"{dict(forms)}; onto a target carrying the {bname} {n - len(clean)} (of which "
                f"'same batch' {same_batch}), onto a clean one {len(clean)}; self-target "
                f"anomalies (table byte 4 says other ally) {len(anomalies)}{extra}")
        wf = (f"with >= {FLOORS[pid]} casts, any one at a target whose {bname} was clear through "
              f"the announce's batch -> FAILED")
        out[pid] = (v, text, wf, {"rows": rows, "clean": clean, "anomalies": anomalies,
                                  "sym": (v_sym, len(sym_clean), len(clean) - len(sym_clean))})
    return out


def score_z2_p2(z2, named):
    rows, per, skipped = [], collections.Counter(), []
    for m, r in monk_rows(z2, REVERSAL_OF_FORTUNE):
        T, ta = r["target"], r["t"]
        if m.dead_at(T, ta):
            skipped.append((m.tag, round(ta, 2), m.name(r["caster"]), m.name(T),
                            "target dead at the announce"))
            continue
        h, how = m.conn.health_at(T, ta)
        if h is None:
            skipped.append((m.tag, round(ta, 2), m.name(r["caster"]), m.name(T),
                            f"no reconstruction: {how}"))
            continue
        # the minimum inside the LEAD_S before the announce: the reading just after every
        # health event in the window, and at the window's start (a lead, not the verdict)
        pts = [ta - LEAD_S] + [te + 1e-6 for (te, k, v) in m.conn.health_ev.get(T, ())
                               if ta - LEAD_S < te < ta]
        vals = [m.conn.health_at(T, x)[0] for x in pts]
        lead = min([h] + [x for x in vals if x is not None])
        per[m.tag] += 1
        rows.append((m.tag, round(ta, 2), m.name(r["caster"]), r["form"], m.name(T),
                     round(h, 3), round(lead, 3), how, r["end_prop"]))
    n = len(rows)
    above = [x for x in rows if x[5] > ROF_LINE + 1e-9]
    near = [x for x in rows if ROF_LINE < x[5] <= ROF_LINE + 0.05]
    hs = [x[5] for x in rows]
    v = "NULL" if n < FLOORS["Z2.P2"] else ("FAILED" if above else "HELD")
    forms = collections.Counter(x[3] for x in rows)
    text = (f"{z2n(REVERSAL_OF_FORTUNE, named)} by a Monk n={n} {dict(per)} (floor "
            f"{FLOORS['Z2.P2']}); forms {dict(forms)}; target health (RECONSTRUCTION, just "
            f"before the announce) at or below {ROF_LINE:.2f}: {n - len(above)}, above: "
            f"{len(above)} (of which inside (0.70, 0.75]: {len(near)}); min/median/max "
            f"{min(hs) if hs else None}/{med(hs)}/{max(hs) if hs else None}; skipped "
            f"{len(skipped)}; with the minimum over the 1 s before the announce instead "
            f"(a lead): above {sum(1 for x in rows if x[6] > ROF_LINE + 1e-9)}")
    wf = (f"with >= {FLOORS['Z2.P2']} casts, any one whose target's reconstructed health "
          f"just before the announce was above {ROF_LINE:.2f} -> FAILED (the registration "
          f"says every cast)")
    return v, text, wf, {"rows": rows, "above": above, "skipped": skipped}


def score_z2_p3(p2rows, named):
    n = len(p2rows)
    other = [x for x in p2rows if x[4] != x[2]]
    share_ = None if not n else round(len(other) / n, 3)
    v = "NULL" if n < FLOORS["Z2.P3"] else ("HELD" if share_ >= P3_SHARE else "FAILED")
    by_target = collections.Counter("self" if x[4] == x[2] else "another Monk" for x in p2rows)
    text = (f"{z2n(REVERSAL_OF_FORTUNE, named)} casts n={n} (P2's floor {FLOORS['Z2.P3']}); "
            f"on another Monk {len(other)} ({share_}), on itself {n - len(other)}; "
            f"{dict(by_target)}")
    wf = f"with >= {FLOORS['Z2.P3']} casts, fewer than {P3_SHARE:.0%} on another Monk -> FAILED"
    return v, text, wf, other


def ench_episodes(m, T, skill):
    """[(start, end, how, caster)]: RECONSTRUCTION -- every completed ZAISHEN cast of
    `skill` on T, live for ENCH_DURATION, cut by T's death / re-create and by the class
    marker's [7, T, 13] (the last enchantment on T ended)."""
    conn = m.conn
    dur = ENCH_DURATION[skill]
    deaths = m.bit_rises(T, DEAD_BIT)
    creates = list(conn.create_t.get(T, []))
    marker_ends = [t for (t, sgn, eid) in conn.effects6.get(T, ())
                   if sgn < 0 and eid == ENCH_CLASS_VISUAL]
    out = []
    for r in m.rows:
        if r["class"] != "ZAISHEN" or r["skill"] != skill or r["target"] != T or not completed(r):
            continue
        te = r["end_t"]
        c1 = [x for x in deaths + creates if x > te]
        c2 = [x for x in marker_ends if x > te + BATCH]
        cut1 = min(c1) if c1 else float("inf")
        cut2 = min(c2) if c2 else float("inf")
        end = min(te + dur, cut1, cut2)
        how = ("natural" if end == te + dur else
               ("death / re-create" if end == cut1 else "[7, T, 13]"))
        out.append((te, end, how, r["caster"]))
    return out


def score_z2_p4(z2, named):
    res = {}
    for skill in (BALTHAZARS_AURA, ZEALOTS_FIRE):
        rows, cx, inf = [], [], []
        per = collections.Counter()
        forms = collections.Counter()
        for m, r in monk_rows(z2, skill):
            T, ta = r["target"], r["t"]
            per[m.tag] += 1
            forms[r["form"]] += 1
            eps = ench_episodes(m, T, skill)
            live = [e for e in eps if e[0] < ta - 1e-6 and e[1] > ta]
            would = [e for e in eps if e[0] < ta - 1e-6 and e[0] + ENCH_DURATION[skill] > ta]
            st = m.conn.status_at(T, ta)
            bit = None if st is None else bool(st & ENCHANTED_BIT)
            row = (m.tag, round(ta, 2), m.name(r["caster"]), r["form"], m.name(T),
                   [(round(a, 2), round(b, 2), h, m.name(c)) for a, b, h, c in live],
                   [(round(a, 2), round(b, 2), h, m.name(c)) for a, b, h, c in would],
                   bit)
            rows.append(row)
            if would:
                inf.append(row)
            if live:
                cx.append(row)
        n = len(rows)
        v = "NULL" if n == 0 else ("FAILED" if cx else "HELD")
        res[skill] = (v, rows, cx, inf, per, forms)
    # 251
    rows, cx, flight = [], [], []
    per = collections.Counter()
    for m, r in monk_rows(z2, SCOURGE_HEALING):
        T, ta = r["target"], r["t"]
        per[m.tag] += 1
        st = m.conn.status_at(T, ta)
        hexed_bit = bool(st is not None and st & HEX_BIT)
        obs_live = []
        if T == m.obs:
            obs_live = [(s, a) for (s, a) in ce.applies_live(m.conn, T, ta) if s == SCOURGE_HEALING]
        hexed = bool(obs_live) if T == m.obs else hexed_bit
        others_ = [x for _m, x in monk_rows([m], SCOURGE_HEALING)
                   if x["target"] == T and x["caster"] != r["caster"] and x["t"] < ta
                   and ((x["end_t"] is not None and x["end_t"] > ta - 1e-9)
                        or (x["end_t"] is None and ta - x["t"] <= float(x["activation"] or 2.0) + 0.5))]
        row = (m.tag, round(ta, 2), m.name(r["caster"]), r["form"], m.name(T), hexed,
               "observer 0x0042 (EXACT)" if T == m.obs else "hexed bit (RECONSTRUCTION: 251 is the Monks' only hex)",
               hexed_bit, [(round(x["t"], 2), m.name(x["caster"])) for x in others_], r["end_prop"])
        rows.append(row)
        if hexed:
            cx.append(row)
        elif others_:
            flight.append(row)
    n = len(rows)
    v = "NULL" if n == 0 else ("FAILED" if cx else "HELD")
    res[SCOURGE_HEALING] = (v, rows, cx, flight, per)
    parts, wf = [], []
    for skill in (BALTHAZARS_AURA, ZEALOTS_FIRE):
        v_, rows_, cx_, inf_, per_, forms_ = res[skill]
        parts.append(f"{z2n(skill, named)} n={len(rows_)} {dict(per_)} forms {dict(forms_)}: "
                     f"re-cast inside a live episode (RECONSTRUCTION {ENCH_DURATION[skill]:g} s, "
                     f"cut by death / re-create / [7, T, 13]) {len(cx_)} -> {v_}; informative "
                     f"(a previous episode would still have been live uncut) {len(inf_)}")
    v_, rows_, cx_, flight_, per_ = res[SCOURGE_HEALING]
    parts.append(f"{z2n(SCOURGE_HEALING, named)} n={len(rows_)} {dict(per_)}: onto a target "
                 f"already hexed at the announce {len(cx_)} -> {v_} (on the observer "
                 f"{sum(1 for x in rows_ if x[6].startswith('observer'))} casts, EXACT); "
                 f"another Monk's 251 in flight at the same target {len(flight_)} (not a "
                 f"counterexample)")
    vs = [res[BALTHAZARS_AURA][0], res[ZEALOTS_FIRE][0], res[SCOURGE_HEALING][0]]
    v = "FAILED" if "FAILED" in vs else ("HELD" if "HELD" in vs else "NULL")
    text = "; ".join(parts) + (f"; the three parts {vs}: any FAILED fails, else any HELD holds")
    wf = ("a 272 / 271 announced at a body inside the reconstructed episode of the same skill "
          "(uncut), or a 251 announced at a body whose hexed bit was set (observer: a live "
          "0x0042 251) -> FAILED")
    return v, text, wf, res


def recon_ench_count(m, T, ta, ex):
    """RECONSTRUCTION: type-6 casts completed on T (by anyone) still inside the exe's
    duration0, not across a death of T, minus one per ZAISHEN 68 completed on T since the
    oldest of them started; floored at 0."""
    deaths = m.bit_rises(T, DEAD_BIT)
    live = []
    for r2 in m.rows:
        if r2["target"] != T or not completed(r2) or r2["end_t"] >= ta:
            continue
        row = ex.get(r2["skill"])
        if not row or row["type_code"] != 6:
            continue
        te = r2["end_t"]
        if any(te < d <= ta for d in deaths):
            continue
        if te + float(row["duration0"]) > ta:
            live.append(te)
    if not live:
        return 0, 0, 0
    t0 = min(live)
    rem = sum(1 for _m, x in monk_rows([m], DRAIN_ENCHANTMENT)
              if x["target"] == T and completed(x) and t0 < x["end_t"] < ta)
    return max(0, len(live) - rem), len(live), rem


def score_z2_p5(z2, named):
    rows, un, contested = [], [], []
    per = collections.Counter()
    tgt = collections.Counter()
    for m, r in monk_rows(z2, DRAIN_ENCHANTMENT):
        ex = exe_skill_rows(m.conn.build) or {}
        T, ta = r["target"], r["t"]
        per[m.tag] += 1
        tgt[m.name(T)] += 1
        st = m.conn.status_at(T, ta)
        bit = None if st is None else bool(st & ENCHANTED_BIT)
        if T == m.obs:
            live = [(s, a) for (s, a) in ce.applies_live(m.conn, T, ta)
                    if ex.get(s, {}).get("type_code") == 6]
            ench, how = bool(live), f"observer 0x0042 type-6 live {live} (EXACT)"
            recon = None
            cont = False
        else:
            l6 = m.conn.live6(T, ta)
            vis = ENCH_CLASS_VISUAL in l6
            recon = recon_ench_count(m, T, ta, ex)
            ench, how = vis, f"[6, T, 13] live: {vis} (live6 {l6})"
            cont = bit is not None and bit != vis
        strips = [t for (t, sgn, eid) in m.conn.effects6.get(T, ())
                  if sgn < 0 and eid == ENCH_CLASS_VISUAL and t < ta]
        since_strip = round(ta - strips[-1], 3) if strips else None
        burst = [(round(x["t"], 2), m.name(x["caster"])) for _m, x in monk_rows([m], DRAIN_ENCHANTMENT)
                 if x["target"] == T and x["caster"] != r["caster"] and ta - BURST_S <= x["t"] < ta]
        row = (m.tag, round(ta, 2), m.name(r["caster"]), m.name(T), ench, how, bit, recon,
               since_strip, burst, r["end_prop"])
        rows.append(row)
        if not ench:
            un.append(row)
        if cont:
            contested.append(row)
    n = len(rows)
    v = "NULL" if n == 0 else ("FAILED" if un else "HELD")
    text = (f"{z2n(DRAIN_ENCHANTMENT, named)} by a Monk n={n} {dict(per)}; targets {dict(tgt)}; at "
            f"an enchanted target {n - len(un)}, at an UNENCHANTED one {len(un)} (henchman: no "
            f"live [6, T, 13]; observer: no live type-6 0x0042); visual / 0x80 disagreements "
            f"(CONTESTED rows) {len(contested)}; unenchanted casts' seconds since the last "
            f"[7, T, 13] and the burst before them: "
            f"{[(x[0], x[1], x[2], x[8], x[9]) for x in un]}")
    wf = ("any one 68 announced at a body carrying no live enchantment (the class visual 13 "
          "on a henchman; a type-6 0x0042 on the observer) -> FAILED")
    return v, text, wf, {"rows": rows, "un": un, "contested": contested}


def current_target(m, a, starts, rises, t, hold=ATTACK_HOLD):
    """(target, how) -- the Monk's current attack target at t (the docstring's P6 rule)."""
    prior = [(t4, tg) for (t4, tg) in starts if t4 <= t]
    if not prior:
        return None, "no [4] yet"
    t4, tg = prior[-1]
    if t - t4 > hold:
        return None, "expired"
    if any(t4 < d <= t for d in rises.get(a, ())) or any(t4 < c <= t for c in m.conn.create_t.get(a, ())):
        return None, "monk died"
    if any(t4 < d <= t for d in rises.get(tg, ())):
        return None, "target died"
    return tg, "held"


def p6_windows(m, monks, starts, rises, hold):
    c = collections.Counter()
    t = m.span[0]
    while t <= m.span[1]:
        alive = [a for a in monks if not m.dead_at(a, t)]
        if len(alive) >= 2:
            c["windows >= 2 alive"] += 1
            holders = {}
            for a in alive:
                cur, _how = current_target(m, a, starts[a], rises, t, hold)
                if cur is not None:
                    holders[a] = cur
            if len(holders) >= 2:
                c["holders >= 2"] += 1
                if len(set(holders.values())) == 1:
                    c["agree (>= 2 holders)"] += 1
            elif len(holders) == 1:
                c["holders == 1"] += 1
            else:
                c["holders == 0"] += 1
        t += WINDOW_S
    return c


def score_z2_p6(z2):
    per, switches, fresh = {}, [], []
    tot = collections.Counter()
    # POST-HOC (added after the first run printed [FAILED] 93 of 117 = 0.795 under the
    # registered rule): the same count under other holds and with 1-holder windows counted
    # as agreeing -- a SENSITIVITY line, printed as a lead; the verdict stays the
    # registered 30 s / >= 2 holders.
    sens = collections.defaultdict(collections.Counter)
    for m in z2:
        monks = list(m.opp)
        starts = {a: [(t, v[3]) for t, op, v in m.s2c
                      if op == ce.OP_INT_T and len(v) > 4 and v[1] == ce.PROP_ATTACK_STARTED and v[2] == a]
                  for a in monks}
        rises = {a: m.bit_rises(a, DEAD_BIT) for a in monks + m.party()}
        c = p6_windows(m, monks, starts, rises, ATTACK_HOLD)
        for hold in (5.0, 10.0, 20.0, ATTACK_HOLD, 60.0):
            sens[hold].update(p6_windows(m, monks, starts, rises, hold))
        for a in monks:
            st = starts[a]
            for (tp, tgp), (t4, tg) in zip(st, st[1:]):
                cur, how = current_target(m, a, st, rises, t4 - 1e-6)
                if cur is None:
                    fresh.append((m.tag, round(t4, 2), m.name(a), m.name(tgp), m.name(tg), how))
                elif tg != cur:
                    switches.append((m.tag, round(t4, 2), m.name(a), m.name(cur), m.name(tg)))
        per[m.tag] = dict(c)
        tot.update(c)
    n2, a2 = tot["holders >= 2"], tot["agree (>= 2 holders)"]
    share_ = None if not n2 else round(a2 / n2, 3)
    v = "NULL" if not n2 else ("HELD" if share_ >= P6_SHARE else "FAILED")
    sens_txt = {}
    for hold, c in sorted(sens.items()):
        k2, g2, k1 = c["holders >= 2"], c["agree (>= 2 holders)"], c["holders == 1"]
        sens_txt[f"hold {hold:g} s"] = (f">= 2 holders {g2}/{k2} ({round(g2 / k2, 3) if k2 else None}); "
                                        f"1-holder windows counted as agreeing {g2 + k1}/{k2 + k1} "
                                        f"({round((g2 + k1) / (k2 + k1), 3) if k2 + k1 else None})")
    text = (f"1-s windows with >= 2 Monks alive n={tot['windows >= 2 alive']}; with >= 2 "
            f"holding a current target n={n2}, of which all holders agree {a2} ({share_}); "
            f"1-holder windows {tot['holders == 1']}, 0-holder {tot['holders == 0']}; per match "
            f"{per}; SWITCHES (a [4] naming a different target from a still-current one) "
            f"{len(switches)}; fresh picks after the current target ended {len(fresh)} "
            f"{dict(collections.Counter(x[5] for x in fresh))}")
    wf = (f"fewer than {P6_SHARE:.0%} of the >= 2-holder windows with every holder on one "
          f"target -> FAILED")
    return v, text, wf, {"switches": switches, "fresh": fresh, "per": per, "sens": sens_txt}


def z2_instruments(z2):
    """The health instrument on the Z2 tape: anchoring, L2 at the Monks' deaths, the
    party's deaths with the match-end defeat marks named, the revives' +1.0 delta."""
    out = {"set34": {}, "anchor": collections.Counter(), "l2_monks": [], "l2_party": [],
           "revives": [], "end_marks": []}
    for m in z2:
        out["set34"][m.tag] = len(m.conn.set34)
        for a in m.opp:
            out["anchor"][m.conn.health_at(a, m.span[1])[1]] += 1
        party = set(m.party())
        deaths = ce.death_checks(m.conn)
        for d in deaths:
            row = (m.tag, d["agent"], m.name(d["agent"]), d["t"], d["h_before"], d["h_after_batch"], d["how"])
            if d["agent"] in m.opp:
                out["l2_monks"].append(row)
            elif d["agent"] in party:
                out["l2_party"].append(row)
        # the defeat mark: >= 2 party bodies marked dead at ONE instant with health > 0.10
        # (presentation fix after the first run, which looked only inside the span's last
        # 2 s and found none: the marks sit ~10 s before the connection's last message,
        # 572.686 on a span ending 582.5 and 670.166 on one ending 680.0; no verdict reads
        # this list -- the L2 headline is over the Monks' deaths)
        by_t = collections.defaultdict(list)
        for d in deaths:
            if d["agent"] in party:
                by_t[d["t"]].append(d)
        for t, lst in by_t.items():
            if len(lst) >= 2 and any((d["h_after_batch"] or 0) > 0.10 for d in lst):
                out["end_marks"].append((m.tag, t, [(m.name(d["agent"]), d["h_after_batch"]) for d in lst]))
        for a in list(m.opp) + m.party():
            prev = 0
            for (t, w) in m.conn.status.get(a, ()):
                if (prev & DEAD_BIT) and not (w & DEAD_BIT):
                    plus = [round(v, 3) for (te, k, v) in m.conn.health_ev.get(a, ())
                            if k == "delta" and abs(te - t) <= 0.1 and v is not None and v > 0.99]
                    out["revives"].append((m.tag, m.name(a), round(t, 2), plus,
                                           m.conn.health_at(a, t + 0.3)[0]))
                prev = w
    return out


def z2_facts(z2, others, named):
    """Facts beyond the predictions, for the record (not verdicts)."""
    f = {}
    f["definitions"] = {}
    for m in z2:
        for a in m.opp:
            d = m.conn.definition(a, m.span[1])
            f["definitions"][f"{m.conn.build}:{d}"] = m.conn.defs.get(d)
    f["enter"] = []
    for port, map_id, merged, obs, cut in others:
        for t, d, op, v in merged:
            if d == "c2s" and op == 0x00A6 and len(v) > 2:
                f["enter"].append((port, round(t, 2), list(v[1:])))
    forms = collections.defaultdict(collections.Counter)
    hench = collections.defaultdict(collections.Counter)
    obs = collections.Counter()
    for m in z2:
        for r in m.rows:
            if r["class"] == "ZAISHEN":
                forms[r["skill"]][r["form"]] += 1
            elif r["class"] == "HENCHMAN":
                hench[m.name(r["caster"])][r["skill"]] += 1
            elif r["class"] == "OBSERVER":
                obs[r["skill"]] += 1
    f["monk_forms"] = {z2n(s, named): dict(c) for s, c in sorted(forms.items())}
    f["off_bar"] = sorted(set(forms) - MONK_BAR)
    f["hench"] = {k: dict(sorted(c.items())) for k, c in sorted(hench.items())}
    f["observer"] = dict(sorted(obs.items()))
    # [61] words by class / skill over the Z2 matches, with the factor vs the table activation
    w61 = collections.defaultdict(list)
    n_ann = collections.Counter()
    for m in z2:
        for r in m.rows:
            if r["form"] not in ("A0[60]", "9F[60]"):
                continue
            n_ann[r["class"]] += 1
            ws = [round(f32(v[-1]), 3) for t, op, v in m.conn.batch_ops(r["t"])
                  if op in (ce.OP_FLOAT, ce.OP_FLOAT_T) and len(v) > 2 and v[1] == PROP_CAST_TIME
                  and v[2] == r["caster"]]
            for s in ws:
                w61[(r["class"], r["skill"])].append((s, r["activation"],
                                                      round(s / r["activation"], 3) if r["activation"] else None))
    f["w61"] = {k: (len(v), sorted({x[2] for x in v})) for k, v in sorted(w61.items())}
    f["announces_by_class"] = dict(n_ann)
    # class visuals: a type-6 completion on a body carrying no live 13 just before it (the
    # VISUAL decides 'clean': after the first run keyed this on the 0x80 bit and counted a
    # body with no 0x00F1 word yet as clean -- Z-Monk#5 in match 2 was created at 215.62
    # already carrying [6, 13] + [6, 18] in its create batch and got its first status word
    # at 263.71 -- four completions on it read as 'clean, adds nothing')
    adds = collections.defaultdict(collections.Counter)
    adds_bit = collections.defaultdict(collections.Counter)
    hex_adds = collections.Counter()
    for m in z2:
        for r in m.rows:
            if not completed(r) or r["target"] is None or r["class"] not in ("ZAISHEN", "HENCHMAN"):
                continue
            if r["type"] == 6:
                if ENCH_CLASS_VISUAL not in m.conn.live6(r["target"], r["end_t"] - 1e-6):
                    adds[(r["class"], r["skill"])][tuple(sorted(r["adds_on_target"]))] += 1
                st = m.conn.status_at(r["target"], r["end_t"])
                adds_bit[(r["class"], r["skill"])][
                    ("bit set" if st is not None and st & ENCHANTED_BIT else
                     "bit clear" if st is not None else "no status word yet",
                     tuple(sorted(r["adds_on_target"])))] += 1
            if r["skill"] == SCOURGE_HEALING and r["target"] != m.obs:
                hex_adds[tuple(sorted(r["adds_on_target"]))] += 1
    f["ench_adds_on_clean"] = {k: dict(v) for k, v in sorted(adds.items())}
    f["ench_adds_by_bit"] = {k: dict(v) for k, v in sorted(adds_bit.items())}
    f["scourge_adds"] = dict(hex_adds)
    # 0x80 transitions vs [6, 13] / [7, 13]
    tr = collections.Counter()
    for m in z2:
        for a in list(m.opp) + m.party():
            prev = 0
            for (t, w) in m.conn.status.get(a, ()):
                rose = (w & ENCHANTED_BIT) and not (prev & ENCHANTED_BIT)
                fell = (prev & ENCHANTED_BIT) and not (w & ENCHANTED_BIT)
                prev = w
                if not (rose or fell):
                    continue
                e = {(v[1], v[3]) for tt, op, v in m.conn.batch_ops(t)
                     if op == ce.OP_INT and len(v) > 3 and v[1] in (6, 7) and v[2] == a}
                if rose:
                    tr["rises"] += 1
                    tr["rises with [6, 13]"] += (6, ENCH_CLASS_VISUAL) in e
                else:
                    tr["falls"] += 1
                    tr["falls with [7, 13]"] += (7, ENCH_CLASS_VISUAL) in e
    f["bit80"] = dict(tr)
    # what follows a Monk's [4]
    after = collections.Counter()
    for m in z2:
        for a in m.opp:
            evs = [(t, v[1]) for (t, op, v) in m.s2c if op in (ce.OP_INT, ce.OP_INT_T)
                   and len(v) > 2 and v[2] == a and v[1] not in (6, 7, 20, 21)]
            for i, (t, p) in enumerate(evs):
                if p == ce.PROP_ATTACK_STARTED and i + 1 < len(evs):
                    after[evs[i + 1][1]] += 1
    f["after_4"] = dict(after.most_common())
    # the condition visuals 25 / 27 on Monks (by number; which condition is UNVERIFIED)
    cv = collections.Counter()
    for m in z2:
        for a in m.opp:
            for (t, sgn, eid) in m.conn.effects6.get(a, ()):
                if sgn > 0 and eid in (25, 27):
                    comps = {r["skill"] for r in m.rows if completed(r) and r["target"] == a
                             and abs(r["end_t"] - t) <= BATCH}
                    cv[(eid, "with a completion of " + str(sorted(comps)) if comps else "no completion in the batch")] += 1
    f["cond_visuals"] = {f"{k[0]} {k[1]}": v for k, v in sorted(cv.items(), key=str)}
    return f


# ------------------------------------------------------------------ the owner's question
def weapon_of(m):
    items = wc.items_of(m.s2c)
    hands = wc.hands_timeline(m.s2c)
    held = wc.held_at(hands, m.obs, m.span[1])
    tl = hands.get(m.obs, [])
    typ = wc.held_type(items, held[0]) if held else None
    speeds = sorted({(round(f32(v[2]), 3)) for t, op, v in m.s2c if op == 0x0035 and v[1] == m.obs})
    return {"lead_type": typ, "name": WEAPON_TYPE.get(typ, str(typ)), "changes": len(tl),
            "attack_base_0x0035": speeds}


def targeting(matches, table):
    out = []
    for m in matches:
        opp = set(m.opp)
        names = [m.name(a) for a in m.party()]
        off = collections.Counter()
        hexes = collections.Counter()
        att = collections.Counter()
        per_body = collections.defaultdict(collections.Counter)
        for r in m.rows:
            if r["caster"] not in opp or r["target"] in (None, r["caster"]):
                continue
            if r["target"] in opp:
                continue
            row = table.get(r["skill"], {})
            if row.get("target") not in (5, None) and r["skill"] != OBSIDIAN_FLAME:
                continue
            nm = m.name(r["target"])
            off[nm] += 1
            per_body[m.name(r["caster"])][nm] += 1
            if r["type"] == 4:
                hexes[nm] += 1
        # 0x00A0 [4] only -- an attack SKILL's [50] is already an offensive cast above
        att_body = collections.defaultdict(collections.Counter)
        for t, op, v in m.s2c:
            if op == ce.OP_INT_T and len(v) > 4 and v[1] == ce.PROP_ATTACK_STARTED and v[2] in opp \
                    and v[3] not in opp:
                att[m.name(v[3])] += 1
                att_body[m.name(v[2])][m.name(v[3])] += 1
        # EXPOSURE: a target can only be chosen while it is alive. The same tallies over
        # the instants when all four party bodies were alive (the 0x00F1 dead bit), and
        # each party body's seconds dead inside the match.
        full = collections.Counter()
        for r in m.rows:
            if r["caster"] in opp and r["target"] not in (None, r["caster"]) and r["target"] not in opp \
                    and (table.get(r["skill"], {}).get("target") in (5, None) or r["skill"] == OBSIDIAN_FLAME) \
                    and not any(m.dead_at(a, r["t"]) for a in m.party()):
                full["cast:" + m.name(r["target"])] += 1
        for t, op, v in m.s2c:
            if op == ce.OP_INT_T and len(v) > 4 and v[1] == ce.PROP_ATTACK_STARTED and v[2] in opp \
                    and v[3] not in opp and not any(m.dead_at(a, t) for a in m.party()):
                full["attack:" + m.name(v[3])] += 1
        dead_s = {}
        for a in m.party():
            s, since = 0.0, None
            for (t, w) in m.conn.status.get(a, ()):
                if (w & DEAD_BIT) and since is None:
                    since = t
                elif not (w & DEAD_BIT) and since is not None:
                    s += t - since
                    since = None
            if since is not None:
                s += m.span[1] - since
            dead_s[m.name(a)] = round(s, 1)
        out.append({"tag": m.tag, "team": m.team, "weapon": weapon_of(m), "party": names,
                    "offensive": dict(off), "hexes": dict(hexes), "attack_starts": dict(att),
                    "per_body": {k: dict(v) for k, v in per_body.items()},
                    "attack_body": {k: dict(v) for k, v in att_body.items()},
                    "all_alive": dict(full), "dead_s": dead_s})
    return out


def share(c, key):
    n = sum(c.values())
    return f"{c.get(key, 0)}/{n}" + (f" ({100.0 * c.get(key, 0) / n:.0f} %)" if n else "")


# ------------------------------------------------------------------ extras for CASTAI
def mesmer_targets(z1):
    out = []
    for m in z1:
        mes = set(m.by_prof(5))
        c = collections.defaultdict(collections.Counter)
        for r in m.rows:
            if r["caster"] in mes and r["target"] not in (None, r["caster"]):
                c[r["skill"]][m.name(r["target"])] += 1
        out.append((m.tag, {f"{k} {SKILL_NAME.get(k, '')}".strip(): dict(v) for k, v in sorted(c.items())}))
    return out


def hex_recast_pattern(z1, obs_dur):
    """Per (body, hex): the re-cast onto the SAME target -- age since the previous
    completion, against the duration observed on the observer."""
    out = collections.defaultdict(list)
    for m in z1:
        for r in m.rows:
            if r["class"] != "ZAISHEN" or r["type"] != 4 or r["target"] in (None, r["caster"]):
                continue
            prev = [x for x in m.rows if x["caster"] == r["caster"] and x["skill"] == r["skill"]
                    and x["t"] < r["t"] and completed(x)]
            if prev and prev[-1]["target"] == r["target"]:
                out[(m.name(r["caster"]), r["skill"])].append(
                    (m.tag, round(r["t"] - prev[-1]["end_t"], 2), m.name(r["target"])))
    return out


def cast_time_words(z1):
    """Every property-61 word in the Z1 matches, with the hexes live on its caster
    (observer: 0x0042; others: the RECONSTRUCTED Mesmer-body hexes) -- which hex stretches
    a cast (RECONSTRUCTION)."""
    table = ce.skill_rows()
    out = []
    for m in z1:
        mes = set(m.by_prof(5)) | set(m.by_prof(4))
        for i, (t, op, v) in enumerate(m.s2c):
            if op not in (ce.OP_FLOAT, ce.OP_FLOAT_T) or len(v) < 4 or v[1] != PROP_CAST_TIME:
                continue
            ag = v[2]
            secs = round(f32(v[-1]), 3)
            nxt = next(((vv[4] if oo == ce.OP_INT_T else vv[3]) for tt, oo, vv in m.s2c[i + 1:i + 6]
                        if oo in (ce.OP_INT, ce.OP_INT_T) and len(vv) > 3 and vv[1] == 60 and vv[2] == ag),
                       None)
            act = table.get(nxt, {}).get("activation") if nxt else None
            recent = sorted({(x["skill"]) for x in m.rows if x["caster"] in mes and x["type"] == 4
                             and x["target"] == ag and completed(x) and 0 < t - x["end_t"] < 20})
            out.append((m.tag, round(t, 2), m.name(ag), nxt, act, secs, recent))
    return out


# ------------------------------------------------------------------ main
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--capture", default=DEFAULT_CAPTURE)
    ap.add_argument("--prefix", action="store_true",
                    help="opt in: score a GAPPED connection's s2c prefix (match 2)")
    ap.add_argument("--rows", action="store_true")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass
    capdir = vaultpath.vault_path("captures", "live", args.capture)
    if not os.path.isdir(capdir) or not os.path.exists(os.path.join(capdir, "wire.jsonl")):
        print(f"zaishenrun: REFUSED -- capture {capdir} is missing (no wire.jsonl)")
        return 2
    who, why = livewire.capture_origin(capdir)
    if who != "live":
        print(f"zaishenrun: REFUSED -- {args.capture} origin {who!r} ({why}); live only")
        return 2
    matches, refused, others, table = load(capdir, args.capture, args.prefix)
    if not matches:
        print(f"zaishenrun: REFUSED -- no Zaishen arena connection scored in {args.capture}; "
              f"refused {refused}")
        return 2
    P = print
    P(f"zaishenrun -- capture {args.capture} (origin live); arena maps {sorted(ce.ZAISHEN_MAPS)}; "
      f"prefix decode {'ON (--prefix)' if args.prefix else 'OFF'}")
    for x in refused:
        P(f"   refused: port {x[0]} map {x[1]}: {x[2]}")
    for m in matches:
        cut = ""
        if m.cut:
            c = m.cut
            cut = (f"; PREFIX cut at plaintext byte {c['plain_bytes']} of {c['plain_total']} "
                   f"(first gap: expected seq {c['gap_seq_expected']}, got {c['gap_seq_got']}, "
                   f"{c['gap_bytes']} bytes missing, at t={c['t_gap']:.2f}; last prefix segment "
                   f"t={c['t_last']:.2f}; {c['messages']} s2c messages framed whole, "
                   f"{c['c2s_messages']} c2s) -- every number below for this match is the "
                   f"prefix to the capture gap (the rest of the match lost)")
        P(f"   {m.tag}: port {m.port} map {m.conn.map_id} build {m.conn.build} t "
          f"{m.span[0]:.1f}-{m.span[1]:.1f}; team {m.team}; opponents "
          f"{[(a, m.name(a)) for a in m.opp]}; party {[(a, m.name(a)) for a in m.party()]}{cut}")
    z1 = [m for m in matches if m.team == "DEGENERATION"]
    z3 = [m for m in matches if m.team == "OBSIDIAN"]
    z2 = [m for m in matches if m.team == "MONKS"]
    obs_dur = observed_durations(z1)
    if z1:
        ranks, rank_ev, rank_ctl, rank_unatt = observed_ranks(z1)
        P("")
        P(f"hex durations OBSERVED on the observer (0x0042 f32, s), Z1 matches: "
          f"{ {k: sorted(v) for k, v in sorted(obs_dur.items())} }")
        P(f"caster attribute ranks OBSERVED (0x0042 field3 of a ZAISHEN hex on the observer; "
          f"None = CONTESTED): {ranks}; evidence {rank_ev}; 0x0042 hexes with no single "
          f"ZAISHEN completion in their batch {rank_unatt}")
        for x in rank_ctl:
            P(f"   rank control (tag, t, skill, def, attribute, rank, exe d0, exe d15, "
              f"d0 + (d15 - d0) * rank / 15, the 0x0042's own f32): {x}")
        P("")
        P(f"Z1 (the Degeneration Team) over {[m.tag for m in z1]}")
        res = {}
        res["Z1.P1"] = score_p1(z1, table, obs_dur, ranks)
        res["Z1.P2"] = score_p2(z1)
        res["Z1.P3"] = score_p3(z1, table)
        res["Z1.P4"] = score_p4(z1)
        res["Z1.P5"] = score_p5(z1, others, table)
        res["Z1.P6"] = score_p6(z1, table)
        res["Z1.P7"] = score_p7(z1)
        for pid in ("Z1.P1", "Z1.P2", "Z1.P3", "Z1.P4", "Z1.P5", "Z1.P6", "Z1.P7"):
            v, text, wf, _d = res[pid]
            P(verdict_line(pid, v, text, wf))
        vb, nb, lb = res["Z1.P7"][3]["b"]
        P(f"[{vb}] Z1.P7(b): the same storms with the early group required to hold >= 2 bodies: "
          f"n={nb} (floor {FLOORS['Z1.P7']}), all early bodies left {lb} (a death not counted as "
          f"leaving) -- NOT the registered form; Z1.P7 above is")
        d = res["Z1.P1"][3]
        for k, v in d["dur_src"].items():
            P(f"      P1 duration used for hex {k} on a non-observer: {v}")
        for x in d["cx"]:
            P(f"      P1 cx: {x}")
        for x in d["informative"]:
            P(f"      P1 informative: {x}")
        for x in d["possible"]:
            P(f"      P1 possible-only: {x}")
        for x in res["Z1.P2"][3]:
            P(f"      P2: {x}")
        for x in res["Z1.P3"][3]["other"]:
            P(f"      P3 other-ally heal: {x}")
        for x in res["Z1.P3"][3]["orison"]:
            P(f"      P3 orison (tag, t, target, deficit, heal, deficit>=heal): {x}")
        for x in res["Z1.P4"][3]:
            P(f"      P4: {x}")
        for x in res["Z1.P5"][3]["casts"]:
            if x[5] or x[6]:
                P(f"      P5 observer cast (tag, t, skill, type, activation, Mesmer hexes live (skill, age), 61 words): {x}")
        for dk, x in sorted(res["Z1.P6"][3].items()):
            P(f"      P6 {dk}: n={x['n']} skills {x['skills']} overlap {x['overlap']}")
            for vv in x["violations"][:12]:
                P(f"         re-fire (tag, prev t, t, body, skill, waiting slot, ready since): {vv}")
        for x in res["Z1.P7"][3]["storms"]:
            P(f"      P7 storm: {x[:3]}")
    else:
        P("")
        P("Z1 (the Degeneration Team): no Degeneration match on this capture -- Z1 is not "
          "scored here (its verdicts stand on 20260928T103123, FINDINGS 18.1)")
    if z2:
        P("")
        P(f"Z2 (the Smiting Monks) over {[m.tag for m in z2]} -- the SCORER'S RULES are the "
          f"module docstring's, written before this section first ran")
        build = z2[0].conn.build
        named, bad, durs = corroborate_ids(build)
        P(f"   Z2 ids named after matching the WIKI triple (energy, activation, recharge) "
          f"against exe {build}: {sorted(named)}; MISMATCH (printed by number) {bad}; the "
          f"reconstructed enchantment durations (exe d0/d15, used) {durs}")
        ins = z2_instruments(z2)
        lm = ins["l2_monks"]
        low = [x for x in lm if x[5] is not None and x[5] <= 0.10]
        P(f"   health instrument: 0x00A2 [34] setters per match {ins['set34']}; every Monk body's "
          f"anchoring {dict(ins['anchor'])}; L2 at the MONKS' deaths (reconstruction <= 0.10 "
          f"just after the killing batch) {len(low)} of {len(lm)}"
          f"{' -- the instrument holds' if lm and len(low) >= 0.8 * len(lm) else ' -- UNVERIFIED: every health column below is suspect'}")
        for x in lm:
            if x[5] is None or x[5] > 0.10:
                P(f"      L2 Monk death NOT <= 0.10: {x}")
        lp = ins["l2_party"]
        lowp = [x for x in lp if x[5] is not None and x[5] <= 0.10]
        P(f"   L2 at the party's deaths {len(lowp)} of {len(lp)}; the match-END defeat marks "
          f"(>= 2 party bodies marked dead at one instant with health > 0.10, RECONSTRUCTION) "
          f"{ins['end_marks']}")
        for x in lp:
            if (x[5] is None or x[5] > 0.10) and not any(x[3] == e[1] for e in ins["end_marks"]):
                P(f"      L2 party death NOT <= 0.10 and not an END mark: {x}")
        rv = ins["revives"]
        P(f"   revives (dead bit clearing) n={len(rv)}; with a +1.0 delta inside 0.1 s "
          f"{sum(1 for x in rv if x[3])}; reconstruction 0.3 s after: "
          f"{collections.Counter(x[4] for x in rv)}")
        r2 = {}
        r2.update(score_z2_p1(z2, named))
        r2["Z2.P2"] = score_z2_p2(z2, named)
        r2["Z2.P3"] = score_z2_p3(r2["Z2.P2"][3]["rows"], named)
        r2["Z2.P4"] = score_z2_p4(z2, named)
        r2["Z2.P5"] = score_z2_p5(z2, named)
        r2["Z2.P6"] = score_z2_p6(z2)
        for pid in ("Z2.P1", "Z2.P1b", "Z2.P2", "Z2.P3", "Z2.P4", "Z2.P5", "Z2.P6"):
            v, text, wf, _d = r2[pid]
            P(verdict_line(pid, v, text, wf))
        for pid in ("Z2.P1", "Z2.P1b"):
            d = r2[pid][3]
            vs, ns, nb = d["sym"]
            P(f"      {pid[3:]} POST-HOC (not the verdict): with the bit's CLEAR inside the "
              f"announce's batch (< {BATCH} s before) also counted as carrying -- the mirror of "
              f"the registered same-batch rise -- clean targets {ns} (same-batch clears set "
              f"aside {nb}) -> would read {vs}; the registered verdict above stands")
            for x in d["clean"]:
                P(f"      {pid[3:]} onto a CLEAN target (tag, t, caster, form, target, carrying, how, "
                  f"end, (s since the bit last cleared, s until it next rises)): {x}")
            for x in d["anomalies"]:
                P(f"      {pid[3:]} self-target anomaly: {x}")
            if args.rows:
                for x in d["rows"]:
                    P(f"      {pid[3:]} (tag, t, caster, form, target, carrying, how, end, context): {x}")
        d = r2["Z2.P2"][3]
        for x in d["above"]:
            P(f"      P2 ABOVE the line (tag, t, caster, form, target, h, min 1 s before, how, end): {x}")
        for x in d["skipped"]:
            P(f"      P2 skipped: {x}")
        for x in d["rows"]:
            P(f"      P2 cast (tag, t, caster, form, target, h, min 1 s before, how, end): {x}")
        d = r2["Z2.P4"][3]
        # POST-HOC (after the first run): the rule as written gave 272 / 271 HELD on 0
        # counterexamples with NO informative cast (272: 0, 271: 4, all four cut by the
        # caster's death before the re-cast) -- a check that could not fail. By Z1.P1's
        # convention (the informative cast is the floor's unit) those two parts read NULL;
        # the 251 part is the only one tested. The registered line above stands as written.
        P(f"      P4 POST-HOC (not the verdict): informative casts (a previous episode would "
          f"have been live uncut) 272: {len(d[BALTHAZARS_AURA][3])}, of them still live at the "
          f"announce {sum(1 for x in d[BALTHAZARS_AURA][3] if x[5])}; 271: "
          f"{len(d[ZEALOTS_FIRE][3])}, still live {sum(1 for x in d[ZEALOTS_FIRE][3] if x[5])} "
          f"(the rest cut by the caster's death) -- a re-cast could only have overlapped a "
          f"live episode {sum(1 for x in d[ZEALOTS_FIRE][3] + d[BALTHAZARS_AURA][3] if x[5])} "
          f"times, so the 272 / 271 parts are VACUOUS and read NULL by Z1.P1's "
          f"informative-floor convention; the 251 part ({len(d[SCOURGE_HEALING][1])} casts) is "
          f"the tested one")
        for skill in (BALTHAZARS_AURA, ZEALOTS_FIRE):
            v_, rows_, cx_, inf_, per_, forms_ = d[skill]
            for x in cx_:
                P(f"      P4 {z2n(skill, named)} RE-CAST INSIDE A LIVE EPISODE (tag, t, caster, form, target, live, would-be-live, 0x80): {x}")
            for x in inf_:
                if x not in cx_:
                    P(f"      P4 {z2n(skill, named)} informative, cut before the announce: {x}")
        v_, rows_, cx_, flight_, per_ = d[SCOURGE_HEALING]
        for x in cx_:
            P(f"      P4 {z2n(SCOURGE_HEALING, named)} ONTO A HEXED TARGET: {x}")
        for x in flight_:
            P(f"      P4 {z2n(SCOURGE_HEALING, named)} in flight (tag, t, caster, form, target, hexed, how, bit, others in flight, end): {x}")
        if args.rows:
            for x in rows_:
                P(f"      P4 251 (tag, t, caster, form, target, hexed, how, bit, others in flight, end): {x}")
        d = r2["Z2.P5"][3]
        for x in d["un"]:
            P(f"      P5 at an UNENCHANTED target (tag, t, caster, target, enchanted, how, 0x80, recon (count, live, removed), s since [7,T,13], burst, end): {x}")
        for x in d["contested"]:
            P(f"      P5 CONTESTED (visual vs 0x80): {x}")
        for x in d["rows"]:
            P(f"      P5 cast (tag, t, caster, target, enchanted, how, 0x80, recon, s since strip, burst, end): {x}")
        d = r2["Z2.P6"][3]
        P(f"      P6 POST-HOC sensitivity (a lead, not the verdict; the registered rule is hold "
          f"{ATTACK_HOLD:g} s over >= 2-holder windows): {d['sens']}")
        for x in d["switches"]:
            P(f"      P6 switch (tag, t, monk, from, to): {x}")
        for x in d["fresh"]:
            P(f"      P6 fresh pick (tag, t, monk, previous [4] target, new, why the previous ended): {x}")
    if z3:
        P("")
        P(f"Z3 (the Obsidian Spike Elementalists) over {[m.tag for m in z3]} -- PARTIAL (one "
          f"match, picked by accident)")
        z = score_z3(z3[0]) if len(z3) == 1 else None
        if z is None:
            P("   more than one Obsidian match: this reader scores one")
        else:
            for pid in ("Z3.P1", "Z3.P2", "Z3.P3", "Z3.P4", "Z3.P5"):
                v, text, wf, rows = z[pid]
                P(verdict_line(pid, v, text, wf))
                for x in rows[:40]:
                    P(f"      {pid[3:]}: {x}")
    P("")
    P("THE OWNER'S QUESTION: opponent offensive casts (foe-target skills, hexes counted apart) "
      "and 0x00A0 [4] attack starts by TARGET, per match, with the observer's weapon read off "
      "the wire (0x006E lead hand -> 0x0161 item type; 0x0035 attack base)")
    for x in targeting(matches, table):
        w = x["weapon"]
        P(f"   {x['tag']} [{x['team']}] observer wields {w['name']} (item type {w['lead_type']}, "
          f"0x0035 base {w['attack_base_0x0035']}, {w['changes']} hand record(s))")
        P(f"      offensive casts {x['offensive']} n={sum(x['offensive'].values())}; hexes "
          f"{x['hexes']}; attack starts {x['attack_starts']} n={sum(x['attack_starts'].values())}")
        if "Healer" in x["party"]:
            P(f"      on the Healer: casts {share(x['offensive'], 'Healer')}, hexes "
              f"{share(x['hexes'], 'Healer')}, attack starts {share(x['attack_starts'], 'Healer')}; "
              f"on the observer: casts {share(x['offensive'], 'observer')}, hexes "
              f"{share(x['hexes'], 'observer')}, attack starts {share(x['attack_starts'], 'observer')}")
        else:
            for nm in x["party"]:
                P(f"      on the {nm}: casts {share(x['offensive'], nm)}, hexes "
                  f"{share(x['hexes'], nm)}, attack starts {share(x['attack_starts'], nm)}")
        for b, c in sorted(x["per_body"].items()):
            P(f"         casts by {b}: {c}")
        for b, c in sorted(x["attack_body"].items()):
            P(f"         attack starts by {b}: {c}")
        P(f"      exposure: seconds dead in the match {x['dead_s']}; with ALL FOUR alive: "
          f"{dict(sorted(x['all_alive'].items()))}")
    P("")
    P("FOR CASTAI (not predictions)")
    for tag, c in mesmer_targets(z1):
        P(f"   Mesmer-body targets per skill, {tag}: {c}")
    for k, v in sorted(hex_recast_pattern(z1, obs_dur).items()):
        P(f"   hex re-cast onto the SAME target, age since the previous completion (s) {k}: {v}")
    for x in cast_time_words(z1):
        P(f"   61 word (tag, t, caster, next skill, table act, seconds, Mesmer/Necro hexes "
          f"completed on it in the 20 s before): {x}")
    if z2:
        named, _bad, _durs = corroborate_ids(z2[0].conn.build)
        f = z2_facts(z2, others, named)
        P(f"   Z2 the Monks' 0x0056 definitions (build:definition -> (file, profession, level)): "
          f"{f['definitions']}")
        P(f"   Z2 c2s 0x00A6 ENTER sends on the outpost connections (port, t, [map, team, 0]): "
          f"{f['enter']}")
        P(f"   Z2 Monk casts by skill and form: {f['monk_forms']}; ids cast that are NOT on the "
          f"WIKI bar (+ Resurrection Signet): {f['off_bar']}")
        P(f"   Z2 henchman casts by skill (by number unless named above): {f['hench']}; the "
          f"observer's: {f['observer']}")
        P(f"   Z2 [61] cast-time words in the announce batch, by (class, skill): n and the "
          f"factors vs the table activation {f['w61']}; announces by class {f['announces_by_class']}")
        P(f"   Z2 [6] adds in the completion batch of an ENCHANTMENT landing on a body with no "
          f"live 13 before it (class, skill) -> ids: {f['ench_adds_on_clean']}; the same by the "
          f"0x80 bit instead (None = no 0x00F1 word yet, which is NOT clean): "
          f"{f['ench_adds_by_bit']}; Scourge Healing's adds on a non-observer target: "
          f"{f['scourge_adds']}")
        P(f"   Z2 0x80 transitions vs the class visual: {f['bit80']}")
        P(f"   Z2 the prop that follows a Monk's [4] (1 = GV_MELEE_ATTACK_FINISHED, 3 = "
          f"GV_ATTACK_STOPPED, agents.py UPSTREAM names): {f['after_4']}")
        P(f"   Z2 [6] condition visuals on Monks by number (which condition: UNVERIFIED): "
          f"{f['cond_visuals']}")
    if args.rows:
        for m in matches:
            for r in m.rows:
                P(f"   ROW {m.tag} t={r['t']:.2f} {r['class']:8s} {m.name(r['caster']):12s} "
                  f"{r['form']:7s} sk {r['skill']:4d} type {r['type']} -> {m.name(r['target'])} "
                  f"end {r['end_prop']}@{r['end_t']} h_t {r.get('h_target')} heal "
                  f"{r.get('heal_on_target')} adds {r.get('adds_on_target')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
