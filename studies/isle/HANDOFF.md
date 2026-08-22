# Isle of the Nameless — handoff to a cold session

**Written 2026-08-18.** **This is NOT a status document.** `PLAN.md` §3's *R-ISLE* row is
the status authority and it is current as of `89bcf68`; this file deliberately does not
restate it, for the reason `CLAUDE.md` opens with. What is here is what the code and the
commits cannot tell you: the traps, and the things a cold session predictably gets wrong.

**Read in this order.** `PLAN.md` §3 *R-ISLE* (where it is) → `studies/isle/PLAN.md` §8
(the eleven-rung ladder, per-rung status) → `studies/isle/FINDINGS.md` §"Rung 7, LIVE #2"
(the damage formula, and the three claims review overturned) and §"Rung 6b" (the east).
`studies/isle/PLAN.md` is ~1,000 lines; do not read it front to back to start work.

---

## 1. The one-paragraph state

**Rungs 1–8 are done.** The Isle is mapped: two live captures (`20260817T231139` west and
centre, `20260818T094648` east) give an agent-id ↔ definition-slot ↔ model ↔ `enc_name` ↔
coordinate table for ~110 stations, the range ladder is closed to ±12.4 u, and the east
holds the skill-bar foe Masters with their pets and spirits. **Rung 7 landed 2026-08-18**
(`20260818T132739`, 495 damage events): the whole outbound damage formula is measured and
adversarially verified, `GV_CRITICAL = 17` is CONFIRMED after months CONTESTED, and gate
1's attribute channel came free with it. Read `FINDINGS.md` "Rung 7, LIVE #2" — especially
its corrections, because three of that pass's own claims were overturned by review. ~~What
is **not** done: no body on the island has a *name* we can prove.~~ **That fell 2026-08-21:
an operator screenshot of the Students' line renders ten nameplates, each Student named for
the condition it applies, which is the `enc_name` route working — see FINDINGS §7.2. Bodies
on this island now have provable names.**

**Rung 8 landed 2026-08-21 across THREE short runs**, and the reason it was three is the
lesson: the 27-step design was unfollowable mid-session and the operator read F9 as "go to
the next condition" rather than "advance one step" (FINDINGS §7.8). Skill **999** observed,
the **condition map is complete** (all ten, 482 = Deep Wound by elimination, 2077 = Cracked
Armor corroborated by GWW's own `<!--id:2077-->`), and the rank ladder closed rung 7's
unmet-requirement defect: **the penalty SCALES with rank**, PINNED refuted at `5.5e-10` by
the distributions rather than a fit. Next is **rung 8d's re-run** — the re-cast shape plus
the unrun rank-13 bench block; the first attempt (2026-08-21) aborted on a skill pick
inferred from an ambient capture, and the re-staged plan
(`vault/plans/isle_rung8d_recast_v2.txt`) is built on a wire readback of the operator's own
bar instead (`studies/skills` §36.9–§36.10, PLAN §3's ladder addendum). After that,
**rung 9, the scripted pass — its respawn analyser is BUILT (2026-08-22)**:
`toolkit/authsrv/respawn.py`, keyed on (definition slot, spawn position) with the
preceding-death bit, proved on the corpus (`test_respawn.py`, 46 checks). Read FINDINGS §10
before designing the run — retail revives IN PLACE (never re-creates), the 30 s
practice-target respawn is already measured n=15 from the rung-7 capture, and the sparring
pit revives in waves that must not be pooled with timer bodies.

## 2. What will bite you, in the order it will bite

**You cannot name a body from a capture, and you will be tempted to.** `enc_name` arrives
for every definition (246/246 — it is free, no targeting needed), but it is a set of string
**ids**, and the only route to a string is rendering it on a client we control. A previous
pass identified a body by combining geometry with the operator's memory, published "agent 28
= Master of Combat", and had it withdrawn under review: the plan's own labels put that agent
at the *Suits*, its profession (Warrior) contradicts GWW's Elementalist Master of Damage, and
there was no health datum to break the tie. **Structure is evidence; a name is not, until
it is rendered.** The one time a multi-axis structural claim survived (§"Rung 6b": profession
+ level + allegiance + summon shape agreeing at once, across three bodies) it is still
labelled RECONSTRUCTION. Rung 7's Master of Damage is the same shape and the same label,
even though it now agrees on **five** axes — profession 6, level 20, health 590, position
between two target stations, and its own announced damage total matching our summed
points. Five agreeing axes is still not a rendered name.

**CHECK THE VAULT BEFORE YOU DESIGN THE SESSION. It has happened three times now.**
Rung 6's 70-step targeting plan became 18 steps of walking once someone measured that
names arrive unprompted. Rung 7's analyzer found its whole proving corpus in a *detour*
nobody planned. Rung 8's central question — does effect application ride `0x0042`, with
the design expecting a refutation — was answered by **97 applies already sitting in
`vault/captures/live/`**, along with the hex and enchantment the same document called
"the largest single miss across all four families". In all three cases the incidental
traffic outvalued the deliberate traffic, and in all three the cost of checking first
was under an hour. **Point the reader at the corpus before the client.**

**And a number is not a result until you have asked what its error bar is.** The rung-7
first pass reported `D = 38.16 and 39.88` against a predicted 40 and read it as a near
miss; the interval is [37.30, 42.00] and contains 40 at −0.8σ. It also reported a rank
"kink ratio" of 2.23 against 2.4 — whose 95% interval turns out to be [−17, 24], a
statistic that cannot tell 2.4 from 1.0. Both survived a whole analysis pass and died to
a bootstrap that needed no new data. **The strongest evidence in that run — a band test
with no free parameters — was available from the first minute and nobody made it until an
adversary asked what pinned the number.**

**Targeting buys you almost nothing, and a plan full of it wastes the run.** Measured: the
four spot-check steps produced **0 new stations out of 95 creates**. Names, slots, models,
positions and allegiance all arrive unprompted. What delivery *is* gated on is **distance** —
so coverage is the operator's job and clicking is not. The first plan was 70 steps of
targeting; it became 18 steps of walking once it was measured, and the walking is what found
seven missing definition indices.

**A level-0, model-less body co-located with a level-20 one is a SUMMON, not a station.**
It is re-created under fresh agent ids at one spot (observed: agent 118 → 123 → 158 at a
single position). `agentroster.stations()` keys on position, so a spirit that respawns three
times looks like three bodies and inflates any census you build on it.

**Do not write a plan in compass words.** Walking "east" from the Isle spawn lands you at
the **north-east corner** — world +x and +y are both involved — so "east, then along the
eastern edge north and south" describes a rectangle the island does not have, and it sent
the operator back and forth along one line. Write legs as landmarks, or as "until X sits at
the compass edge". Related: the island is **much bigger than it looks**. A leg budgeted at
~10,000 u actually ran 13,325.

**The manifest can lie to you if it is old.** `reassemble()` used to recompute the
per-connection report, print it, and drop it — so a re-assembled capture kept advertising
its original refusals forever. Fixed 2026-08-18; a manifest now carries `report_from`, and
**absent means `run()` wrote it and it was never re-assembled**. If a capture's manifest and
its directory disagree, believe the directory and re-run `--assemble`.

## 3. The instruments that are ready, and what they cost

- **`toolkit/authsrv/agentroster.py`** — reads any capture into cross-session-stable
  stations. Refuses to pool mixed origins. This is the reader; you do not need a new one.
- **`vault/plans/isle_rung6_roster.txt`** and **`isle_rung6_east.txt`** — the two sealed
  plans, as worked examples of the format (`kind<TAB>text`, `#` comments free).
- **The live procedure** is `RUNBOOK.md` §"Capturing a live session". The build is chosen
  **for you** now: `livesession.preflight()` refuses an exe whose build does not match the
  owner's install, before the login. Ask directly with `buildid.py --exe <path>`.
- **`--mode base`** for a PvP-only character. Well founded (Reforged is opted into at
  character creation and the PvP flow does not offer it) but **UNVERIFIED** — nothing here
  has measured it, and it is `operator-declared` with no wire mark.

## 4. Open, and worth taking in this order

1. **Rung 8 — the effects pass. PREPPED, and its exit criterion was met OFFLINE** (see
   FINDINGS "Rung 8 prep"). The corpus already held **97 `0x0042` applies**, the
   apply/remove lifecycle is exact to the millisecond, **field 3 is the applier's
   attribute rank**, and hexes and enchantments — the design's "largest single miss …
   no instrument at all" — were **already captured and merely unidentified** (skill 984
   = Torch Enchantment, 998 = Torch Hex). The session is staged at
   `vault/plans/isle_rung8_effects.txt` for the four things the vault cannot give:
   skill **999** (the degeneration torch), the five foe Students' condition ids,
   degeneration in pips, and rung 7's rank ladder. **The torches are not clicked** —
   they re-apply every ~2 s to anyone adjacent.
2. **The rung-7 residual is the highest-value single measurement left on the island**, and
   it is small: **one block at rank 7 or 6, or one weapon with a different requirement.**
   Three separate rung-7 results (the formula's unmet-requirement term, the rank-8
   critical, and the 0.29 ratio) all fail at the same term, and the data cannot say which
   of {divisor, strike-level drop, crit rule} carries it. Anything that touches the Isle
   again should carry this block.
3. **Rung 7 is DONE and its analyzer is the model for the next one** — build the consumer
   BEFORE the session, because it is what turns a run into a result. But note the two
   traps it hit: `tape.load_tape` times are connection-local while marks are
   capture-global (add `info["t0"]`, or blocks come back silently MISLABELLED, not
   unlabelled), and a point estimate without an interval will be over-read every time.
3. **Three definition indices — 130, 139, 146 — have never appeared in any capture we
   hold.** Seven of their ten siblings turned up in the east exactly as predicted. If a
   future pass does not produce these three, they belong to another map and the Isle roster
   is closed at 27 types, which is a result worth stating rather than a gap.
4. **`0x0195` is written up — [studies/mapload/FINDINGS.md](../mapload/FINDINGS.md)**, all
   seven fields, and it took two fixtures with it: `studies/tape` §1.2's open question is
   settled (field 1 is a **terrain-file id**, and 165811 carries both the Isle and the Great
   Temple of Balthazar) and `content/maps.toml [map.280]` now carries **retail's arrival
   position** instead of our mesh-centre probe. What is left open there is field 5's meaning
   and a live conflict about whether `0x0020` field 7 is a unit vector or a world position —
   the repo currently holds both readings.
5. **Loopback residuals**, cheap, any harness window: the multi-word varint send, the `0x5F`
   overhead channel (never bare-sid — it crashes the client; but note rung 7 observed 18
   healthy `0x5F` lines paired with `0x5D`, so the hazard is the BARE sid, not the opcode),
   skill 2077's render, and the energy drain-pool probe, which has never been run.

## 5. What NOT to redo

The range ladder (10 rungs, byte-identical across visits, ±12.4 u — closed). The island's
west and centre (walked at a median 255 u; empty ground there is real absence). The spot
checks (which agent was clicked is settled for all four; only the name is open). And do not
re-walk the east for coverage — it is *bounded*, not merely visited: the track encloses every
body found on every side.
