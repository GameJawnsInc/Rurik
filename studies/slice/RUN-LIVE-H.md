# RUN-LIVE-H — one live capture for the hero ladder's unwitnessed shapes

**REGISTERED 2026-09-13, before any launch.** `main` at `d5d4624c` (H13 merged). The owner:
*"i could grab a capture, we can plan a bigger one to grab a couple different features."* This
is that plan: **one human-driven session on the secondary account** (`RUNBOOK.md` §"Capturing a
live session"; the plan is sealed by `livesession.py --plan` before the client launches), legs
ordered so that the cheapest and most certain come first and a leg the character cannot do is
skipped without spoiling the rest.

The rungs H10–H13 each shipped a wire shape the corpus could not witness and the docs labelled
RECONSTRUCTION. This run is what turns each of those labels into OBSERVED or REFUTED. Every leg
below names the label it retires, its exposure floor, and its prediction — fixed here, now.

## 0. Questions for the owner, BEFORE the run

Answers change which legs exist. Do not launch until these are answered in chat:

1. **Which character on the secondary account, what level, where?** The one low-level session
   on file (20260819T132414) was a level-3 Warrior in pre-Searing (the observer at 140 health,
   Sever Artery on the bar, three level-3 henchmen). Pre-Searing has no heroes, no Bonetti's
   Defense, no Final Thrust and no Desperation Blow; it does have **Frenzy** (*Warrior Test*),
   **Hammer Bash** (*Warrior's Challenge*), **Sever Artery + Gash** (*Grawl Invasion*), Healing
   Signet and Power Attack (`studies/presearing/MANIFEST.md`'s Warrior table).
2. **Which of these does the character actually know: Frenzy, Hammer Bash, Gash?** And is there
   **a hammer** in the inventory (Hammer Bash needs one in hand; the starter hammer is a
   Warmaster Grast reward)?
3. **`--mode base` or `--mode reforged`?** Required by the driver since 2026-08-11; the
   Reforged toggle scales enemy health and armour and leaves no mark on the stream.
4. If the account also has a **post-Searing character with a hero**, say so: a second session
   could witness the commander clicks (H5's three opcodes have no retail witness) and Bonetti's
   Defense / Final Thrust. Not this run.

## 1. Preconditions (the runbook's, restated as a checklist)

* `python toolkit/clientpatch/dhbuild.py` says `stock` + `key_tapped` for the `run-live` build.
* The loopback dry-run is green today: `python toolkit/harness/dryrun_keycapture.py` (elevated).
* The plan file below is written to `C:\gd\Rurik\vault\plans\slice_hero_legs.txt` and
  `python toolkit/harness/marks.py --check-plan C:\gd\Rurik\vault\plans\slice_hero_legs.txt`
  parses it. **Then leave the file alone.**
* Human cadence, human hours, one client, never in a competitive context (`PLAN.md` §6.2).

## 2. The legs

Each leg is a paragraph the operator can read at the keyboard. Floors are the minimum exposure
that makes the leg a trial rather than a null; a leg under its floor is reported as ABORTED, never
as "no effect".

### Leg A — Frenzy's attack speed on the wire (retires H13's RECONSTRUCTION; animref §8's item)

Frenzy on the bar, a sword or axe in hand (1.33 s base). Select one foe that will stand and take
it (a Grawl, a River Skale). **Auto-attack for four swings, press Frenzy, keep auto-attacking until
the icon goes (8 s), then four more swings.** Do it twice, on two foes. Do NOT press any other
skill while Frenzy is up — a skill strike's timing rides a different law.

* Floor: ≥ 5 swing STARTs inside each Frenzy episode, ≥ 4 outside, on each of two episodes.
* **P-A1 (the resend).** Within 0.2 s of Frenzy's `0x0042` apply on the observer, a `0x0035
  [me, 1.33, 0.67]`; within 0.2 s of its `0x0044`, a `0x0035 [me, 1.33, 1.0]`. **The
  alternative is equally decisive:** no `0x0035` at all inside the episode means the client
  applies the stance itself and H13's resend is redundant traffic to remove. Either way the
  label goes.
* **P-A2 (the cadence).** START-to-START p50 inside the episode 0.89 s (1.33 × 0.67, the wiki's
  exact 0.8911), outside 1.33 s.
* **P-A3 (the windup under a modifier — animref §8's REFUTED-BY-METHOD item).** Landed-swing
  windup inside the episode fits ONE of `m×base/2 − 0.1`, `m×(base/2 − 0.1)`, `(m×base − 0.2)/2`
  — 0.545, 0.379 or 0.345 s. The first swing under the modifier decides it; five make it a claim.

### Leg B — Frenzy's double damage taken (retires nothing labelled; CORROBORATES the row's WIKI-only multiplier)

Same foes, same episodes: **let the foe hit you at least twice while Frenzy is up and at least
twice while it is not.** The Grawl obliges if you stand still.

* Floor: ≥ 2 hits taken inside and ≥ 2 outside, same foe.
* **P-B.** The inside hits' `0x00A3 [16, me, foe, fraction]` × 140 are ≈ 2× the outside ones
  (Frenzy's "take 175 % damage" at Strength 0 — the wiki's variable is 175→125, so the exact
  factor at this character's Strength is what the leg reads; `damage_taken_multiplier = 2.0` is
  what we ship and the page says it should be 1.75 at rank 0).

### Leg C — Healing Signet's −40 armour (retires H7's "not modelled" with a number)

**Cast Healing Signet with a foe on you, twice.** Stand still; the 2 s cast must take at least
one hit.

* Floor: ≥ 2 hits taken inside a signet cast (across both casts), ≥ 2 outside from the same foe.
* **P-C.** Inside hits ≈ 2^(40/40) = 2× the outside hits (armour 45 → 5 for the cast's length).

### Leg D — Gash on a bleeding foe (retires H10's Deep Wound-on-a-foe wire shape)

**Sever Artery, then Gash, on the same foe, twice.** Watch the foe's health bar for the right
fifth going dark.

* Floor: 2 Gash strikes that land on a foe carrying a live Bleeding.
* **P-D1.** The foe gets `0x0042 [foe, 482, rank, buff, seconds]` in Gash's strike batch, and
  **the foe's `0x009F 42` maximum drop** rides the same batch (deepwoundjoin measured
  `[0x0042, 0x00F1, 0x009F 42]` on the PLAYER, 2 of 2; whether a foe's maximum is sent is the
  open half).
* **P-D2.** A Gash on a foe that is NOT bleeding (do one on purpose, third foe) carries no 482
  and no bonus: its damage equals a plain swing's.

### Leg E — Hammer Bash (CONDITIONAL: the character knows it and holds a hammer; retires H12's attack-skill knock-down RECONSTRUCTION)

Swap to the hammer, **Hammer Bash a foe three times** (it needs 6 adrenaline strikes: swing
first). If the character has neither the skill nor a hammer, skip — say so in chat, the plan's
step is marked and the report says ABORTED.

* Floor: 3 landed Hammer Bash strikes.
* **P-E1.** The strike batch is `[50, me, foe, 331]` at the press, then a windup later `[46, me,
  0]`, the damage, **then `0x00A2 [63, foe, 2.0]`** — the corpus's knock-down message after an
  attack skill's close, which no tape holds.
* **P-E2.** A `0x00D0 [me]` (adrenaline lost) in that same batch, and the foe opens no swing
  for 2.0 s.

### Leg F — the dark bar (already sealed as `vault/plans/adren_gate.txt`, 2026-08-22, never run; folded in)

**Remove EVERY adrenal skill from the bar** — energy skills and signets only, check it twice —
re-enter, **land fifteen weapon hits.** Then put ONE adrenal skill back, re-enter, land three.

* Floor: 15 landed hits on the dark bar, 3 on the armed one.
* **P-F.** Gate A (the bar): zero `0x00CF` / `0x00D0` / `0x00D2` on the dark-bar connection.
  Gate B (the profession): 25 units per completed attack regardless. `test_adrenwire` 12 pins
  the numbers each answer moves.

### Not in this run, said so

A **block** seen from either side (no pre-Searing stance blocks; no pre-Searing foe blocks), a
**knock-down taken** (no pre-Searing foe knocks down), **Final Thrust**, **Desperation Blow**,
**Bonetti's Defense**, the **commander clicks**. All wait on question 4.

## 3. The plan file — write it to `C:\gd\Rurik\vault\plans\slice_hero_legs.txt` VERBATIM

```
# RUN-LIVE-H (studies/slice/RUN-LIVE-H.md) -- sealed by livesession.py before launch.
# Legs A-F; a leg the character cannot do is SKIPPED in chat and reported ABORTED.
enter	the explorable, sword/axe in hand, Frenzy / Sever Artery / Gash / Healing Signet on the bar
frenzy	leg A: four plain swings, Frenzy, swing until it ends, four more -- first foe
frenzy	leg A: the same on a second foe; leg B: stand and take hits inside and outside Frenzy
signet	leg C: Healing Signet with a foe on me, twice, standing still through the cast
gash	leg D: Sever Artery then Gash on one foe; again on a second; a Gash alone on a third
hammer	leg E (if known + a hammer): Hammer Bash three times, swinging first for the adrenaline
strip	leg F: EVERY adrenal skill off the bar, checked twice, re-enter
fight	leg F: fifteen weapon hits on the dark bar
rezone	leg F: one adrenal skill back, re-enter, three hits
logout	done
```

## 4. The commands (PowerShell; every line runs as written)

```
python toolkit/clientpatch/dhbuild.py
python toolkit/harness/marks.py --check-plan C:\gd\Rurik\vault\plans\slice_hero_legs.txt
python toolkit/harness/livesession.py --account capture --exe C:\gd\Rurik\vault\run-live\<build>\Gw.exe --confirm --mode base --plan C:\gd\Rurik\vault\plans\slice_hero_legs.txt
```

The third line is elevated and is the owner's; the driver sends nothing and clicks nothing.

## 5. What gets scored afterwards, and by what

* Leg A: `ias_census.py` / `ias_cadence.py` (this session's scratch; promote to
  `toolkit/authsrv/iasjoin.py` on the capture) — the `0x0035` census per agent and the
  START-to-START cadence inside/outside every episode; animref's windup fitter for P-A3.
* Leg B/C: the damage-fraction join already in `henchjoin.py --hostile` (hits on the observer by
  window).
* Leg D: `deepwoundjoin.py` aimed at the FOE's agent.
* Leg E: `kd_census.py` (this session's scratch) — every prop 63 with its batch.
* Leg F: `test_adrenwire` 12's numbers, on the new connection.

Each leg's verdict goes into `FINDINGS.md` as SLICE-F38 with the label it retires named, and
the H10/H12/H13 rows flip from RECONSTRUCTION to OBSERVED or are reverted — the row's own flag
(`--no-attack-speed-sync`, `--no-knock-down`) is the revert if a prediction fails.
