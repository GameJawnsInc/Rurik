# Isle of the Nameless — handoff to a cold session

**Written 2026-08-18.** **This is NOT a status document.** `PLAN.md` §3's *R-ISLE* row is
the status authority and it is current as of `89bcf68`; this file deliberately does not
restate it, for the reason `CLAUDE.md` opens with. What is here is what the code and the
commits cannot tell you: the traps, and the things a cold session predictably gets wrong.

**Read in this order.** `PLAN.md` §3 *R-ISLE* (where it is) → `studies/isle/PLAN.md` §8
(the eleven-rung ladder, per-rung status) → `studies/isle/FINDINGS.md` §"Rung 6 prep" and
§"Rung 6b" (what the two live runs settled). `studies/isle/PLAN.md` is ~1,000 lines; do not
read it front to back to start work.

---

## 1. The one-paragraph state

**Rungs 1–6 are done.** The Isle is mapped: two live captures (`20260817T231139` west and
centre, `20260818T094648` east) give an agent-id ↔ definition-slot ↔ model ↔ `enc_name` ↔
coordinate table for ~110 stations, the range ladder is closed to ±12.4 u, and the east
holds the skill-bar foe Masters with their pets and spirits. What is **not** done is
everything downstream of naming and damage: no body on the island has a *name* we can
prove, and no swing has been taken. Next is **rung 7, the damage pass**.

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
labelled RECONSTRUCTION.

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

1. **Rung 7 — the damage pass.** Auto-attack only against the Suits, aggregated on
   **(target, cause, swing-kind)**. Design and confounds in `studies/isle/PLAN.md`. The
   armor bench and the Master of Damage are already located and their coordinates recorded.
2. **Rung 8 — the effects pass.** Its material was found a rung early: the east's foe
   Masters, with pets and spirits, at known coordinates. Order still stands — Torches first,
   because if effect application does not arrive on `0x0042` the channel assumption is
   refuted in two minutes rather than a whole session.
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
   overhead channel (never bare-sid — it crashes the client), skill 2077's render, and the
   energy drain-pool probe, which has never been run.

## 5. What NOT to redo

The range ladder (10 rungs, byte-identical across visits, ±12.4 u — closed). The island's
west and centre (walked at a median 255 u; empty ground there is real absence). The spot
checks (which agent was clicked is settled for all four; only the name is open). And do not
re-walk the east for coverage — it is *bounded*, not merely visited: the track encloses every
body found on every side.
