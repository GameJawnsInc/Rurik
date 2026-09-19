# WEAPONS — the live capture runsheet

Four runs, each ≤ 8 steps, each answering questions the corpus cannot. Written
2026-09-18, after every owner-free rung of the arc had landed and the remaining
open items were all capture-gated. The plan rows are in
[PLAN.md](PLAN.md) §6; this file is what you execute.

**The short version.** One PvP character on the **Isle of the Nameless**, with
weapons from the PvP equipment panel, covers RUN-1A, RUN-1B and RUN-2 in two
sittings. Nobody needs to meet a requirement for any of it: timing, launch,
flight, projectile and range do not depend on one. RUN-3 is the exception and
wants the right attributes, so it is last.

---

## 0. Before anything launches

**The house rules are the control that matters**, and no tool substitutes for
them ([CLAUDE.md](../../CLAUDE.md)): the **secondary account**, human cadence,
human hours, **one client**, never in a competitive context. The driver sends no
keystrokes and no clicks by design — you play, it watches.

**Checked on 2026-09-18, so you do not have to re-derive it:**

| | |
|---|---|
| live build to use | `vault/run-live/2026-09-01_44fbd68767a8/Gw.exe` |
| its build id | **38888** |
| your own install `C:\gw` | **38888** — they match, so the updater has nothing to do |
| its DH | `stock` (ArenaNet's — correct, and the only kind that may point live) |
| its key-tap | **present** |
| its updater | LIVE — correct for a live build, and the reason it can rewrite itself |

Re-check the moment anything smells stale, because the updater can rewrite that
exe **in place mid-run** and take the key-tap cave with it (this happened on
2026-08-21 and cost 336 KiB of undecryptable ciphertext):

```bash
python toolkit/clientpatch/dhbuild.py
```

**Then the loopback dry-run, once per sitting.** It runs the whole pipeline —
key-tap, off-wire capture, keytap read, assemble, decrypt — against our own
server, where every byte has an oracle, and it cleans up after itself. From an
**elevated** shell:

```bash
python toolkit/harness/dryrun_keycapture.py
```

If that is not green, stop. Nothing below is worth doing with a broken pipeline.

**Free F9, F10 and F11 before you start.** The marker registers them globally and
swallows them, so they never reach Guild Wars. If something else already holds
them it refuses rather than silently polling.

---

## 1. How each run is driven

Same shape every time. Two shells, both elevated.

**Shell A — the driver.** It hashes the plan *before* the client launches, prints
the sha256 into `manifest.json`, and prints the exact marker command for shell B.

```bash
The four commands, ready to paste, one per run and in this order.

RUN-WEAPONS-1A, the martial clocks, the scythe's extra targets and the spear:

```bash
python toolkit/harness/livesession.py --account capture --exe C:\gd\Rurik\vault\run-live\2026-09-01_44fbd68767a8\Gw.exe --confirm --mode base --minutes 30 --plan C:\gd\Rurik\vault\plans\weapons_1a.txt
```

RUN-WEAPONS-1B, the bow classes and the caster clocks:

```bash
python toolkit/harness/livesession.py --account capture --exe C:\gd\Rurik\vault\run-live\2026-09-01_44fbd68767a8\Gw.exe --confirm --mode base --minutes 30 --plan C:\gd\Rurik\vault\plans\weapons_1b.txt
```

RUN-WEAPONS-2, range per weapon type:

```bash
python toolkit/harness/livesession.py --account capture --exe C:\gd\Rurik\vault\run-live\2026-09-01_44fbd68767a8\Gw.exe --confirm --mode base --minutes 25 --plan C:\gd\Rurik\vault\plans\weapons_2.txt
```

RUN-WEAPONS-3, the damage terms:

```bash
python toolkit/harness/livesession.py --account capture --exe C:\gd\Rurik\vault\run-live\2026-09-01_44fbd68767a8\Gw.exe --confirm --mode base --minutes 35 --plan C:\gd\Rurik\vault\plans\weapons_3.txt
```

**`--mode base` is settled by evidence rather than copied.** The flag is REQUIRED
and deliberately has no default: Reforged changes enemy health and armour by about
20 %, and a capture that did not stamp its mode can never be graded afterwards. All
**26** stamped live captures in the vault record `mode=base`, so that is this
account's mode. If the account has changed since, fix the flag before you run,
because nothing downstream can repair it.

**`--minutes` is a CEILING, not a duration.** Ctrl-C ends the run at any point and
still assembles and scrubs in full, so a generous ceiling costs nothing while a
tight one can truncate the last block.

**Shell B — the marker.** Copy the command the driver printed. Do not retype it:
a different file with the same name seals nothing and the mismatch is only
reported after the run.

While you play: **F9** advances to the next plan step, **F10** says you repeated
the one you are on, **F11** stamps an instant with no text. F11 means exactly one
thing per run and each run below says what.

**Afterwards** the manifest's `plan_seals` field reports AGREE / DISAGREE /
UNCHECKED. AGREE is the only one that means the plan you sealed is the plan the
marker read.

---

## 2. RUN-WEAPONS-1A — the martial clocks, the scythe's extra targets, the spear

**Answers** WEAPONS-Q5 (scythe: duration, how extra targets appear on the wire,
the critical's size) and WEAPONS-Q6 (spear: duration, projectile id, arrow flag,
with and without a shield).

**Where.** Isle of the Nameless, the Master of Damage suits. Pick one spot, stand
on it for every block, and do not drift — the flight and distance questions in
RUN-1B depend on the same habit and it is worth building here.

**F11 means: "I am on the mark and this block starts now."** Nothing else.

**The eight steps** (`vault/plans/weapons_1a.txt`):

1. axe, no off-hand — 20 plain swings on one suit
2. scythe — 20 plain swings on **one** suit
3. scythe — 20 plain swings positioned so **three** suits are adjacent to the target
4. spear, no off-hand — 20 plain swings
5. spear **+ shield** — 20 plain swings
6. axe again, 10 swings — the repeat that catches a drifting clock
7. idle 30 s, weapon drawn, no swings — the silence that dates the chain
8. done

**Sealed predictions.** Scythe and spear `start → start` **1.500 s**; the word or
launch at **0.650 s** after the start; the spear's `0x00A4` field 7 = **1**; the
scythe's extra targets arrive as additional damage words in the same instant as
the target's, not as separate swings; the scythe's critical is **×2^0.125**, not
the ×2^0.5 every other weapon takes (WIKI, and the reason this run exists).

**Exposure floor.** At least **15 landed swings in every block** and a `0x0035`
for each equip. Below that the block is a null, not a measurement.

**Abort** if a suit dies or despawns, if anything else attacks you, or if you
cannot tell which suit you are targeting. Say so in the notes and redo the block.

---

## 3. RUN-WEAPONS-1B — the bow classes and the caster clocks

**Answers** WEAPONS-Q2 (which `609` value is which bow class) and WEAPONS-Q3
(projectile speed per class — the same distance, so five flights are directly
comparable).

**Where.** The same Isle spot, and **the same spot for all seven weapons** — this
is the whole run. Q3 is distance ÷ flight, so a step sideways between blocks is
the free parameter that ruins it.

**F11 means: "I am on the mark."** Tap it at the start of every block.

**The seven steps** (`vault/plans/weapons_1b.txt`): shortbow, flatbow, longbow,
recurve, hornbow, staff, wand — 20 plain swings each, from the mark, at the same
suit.

**Sealed predictions.** `start → launch` at **0.9125 / 1.1375 / 1.250 / 0.775 s**
for the 2.025 / 2.475 / 2.7 / 1.75 s clocks; flight-time ratios across the five
bows of **0.59 : 0.88 : 0.59 : 0.40 : 0.59**; the `609` argument differing between
the classes, with 1 and 3 already known to be the two 2.475 s ones. The corpus's
three measured speeds are 1200, 1600 and 2800 u/s, so a class landing on a fourth
number is the interesting result.

**Exposure floor.** At least **5 launches per weapon** from the mark. Fewer than 3
in any block and that class is unmeasured.

**Abort** on the same conditions as 1A, plus: if you move between blocks, mark it
and treat the run as two runs rather than pretending the spot held.

---

## 4. RUN-WEAPONS-2 — range per weapon type

**Answers** WEAPONS-Q4 (range per type in units, and what height does to it).

**Q16 is no longer part of this run.** It asked what parks retail's client at
range on an attack-follow, and §22 answered it from the client's own code: the
park threshold has no weapon term, so a follow walks a body to the melee disc
whatever it holds. Do not spend steps on it.

**The method, which has no free parameter.** Stand well beyond range, press attack
**once**, and let the character walk in. The distance from the shooter to the aim
point at the **first launch** is the range. Repeat uphill and downhill if the Isle
gives you the slope.

**F11 means: "I pressed attack from this spot."**

**The eight steps** (`vault/plans/weapons_2.txt`): shortbow, flatbow, longbow,
recurve, hornbow, staff, wand, spear — one press each, from as far as the ground
allows.

**Sealed predictions.** **1004** shortbow, **1498** flatbow and longbow, **1273**
recurve and hornbow, **1248** staff and wand, **1004** spear.

**Exposure floor.** Every weapon must produce a press, a follow, and a first
launch. A weapon that shot before you finished walking was not out of range —
back up and redo it.

**Abort** if anything interrupts the walk-in, and redo that weapon.

---

## 5. RUN-WEAPONS-3 — the damage terms (last, and it wants the right attributes)

**Answers** WEAPONS-Q10 (the unmet-requirement term for weapon, shield and focus),
the scythe's critical size from a second direction, WEAPONS-Q12 (whether
customisation's ×1.2 is already inside the isle study's numbers), and W4's
remaining half — `587` damage type against armour's `+N vs type` words.

**Why it is last.** Every other run works with any attributes. This one needs a
requirement **met** and then deliberately **unmet** on the same weapon, which
means spending and respeccing.

**F11 means: "the requirement is now UNMET."**

**The steps** (`vault/plans/weapons_3.txt`): one weapon at a met requirement, 20
swings; the same weapon unmet, 20 swings; a shield met then unmet; a focus met
then unmet; hornbow against the 100-armour suit; longbow against the same suit.

**Sealed predictions.** An unmet weapon requirement deals **one third** of base
damage (WIKI, and [studies/isle](../isle/FINDINGS.md) measured against that and
refused to pin a term — so this run is what settles it); an unmet **shield** gives
armour 8, an unmet **focus** energy 6; the hornbow penetrates **10 %** more armour
than the longbow against the same suit.

**Exposure floor.** 20 landed swings in each of the met and unmet blocks on the
same weapon. Anything less and the pair does not discriminate.

**Abort** if you cannot confirm from the character panel which state the
requirement is in. The whole run is that one bit.

---

## 6. After each run

Score against the corpus with the tools that already exist. The capture stamp is
the directory name the driver printed.

```bash
python toolkit/authsrv/weaponcensus.py --capture <stamp> --shooters
```

```bash
python toolkit/authsrv/timingjoin.py --capture <stamp> --swings
```

`weaponcensus` gives the per-weapon wire shape — the item type, the `609` and
`617` arguments, the launch fields and the arrival kinds. `timingjoin` gives the
clocks beside our own server's, which is the comparison that found three timing
defects nobody had seen from one side alone.

**Write the answers into [PLAN.md](PLAN.md) §7's question rows**, one row per
question, and move whatever ships into a rung. A run that measured something and
was never written up is a run nobody can use.

---

## 7. What this runsheet refuses

- **No wiki number becomes a pin.** Every prediction above is a prior to test.
  GWW contradicting itself on bow durations and ranges is the standing reminder.
- **No weapon clock is calibrated on a hostile.** Ranged NPCs repeat at 1.75 /
  1.90 / 1.985 / 2.125 s, which is AI pacing and not a weapon's duration
  (WEAPONS-C5).
- **No plan written after the client launched.** That is a label, not a
  prediction, and the driver deliberately offers no marker command without one.
