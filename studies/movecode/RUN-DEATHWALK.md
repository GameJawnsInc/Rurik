# DEATHWALK — death, rise and re-approach: the follow hop's leftovers, as one batch

> **DRAFT, 2026-10-06. NOT REGISTERED, NOT RUN.** This plan becomes a registration only
> when its desk steps (D0–D3) have run and their numbers are written into the H rows
> below. Until then every number marked *(pending D-n)* is a placeholder, and nothing
> here may be quoted as a prediction. A launch needs the owner's go-ahead (parallel
> sessions share the harness), announced as **HANDS OFF THE KEYBOARD**.

**Identifiers.** `DEATHWALK-D<n>` = desk steps, no client. `DEATHWALK-E<n>` = scripted
experiments, one flag each. `DEATHWALK-H<n>` = registered predictions. Convention:
[studies/idents/CONVENTION.md](../idents/CONVENTION.md).

**Tree.** Written at `2faed55d` (branch `desk-residue`, off `main` at `cdf15970`).
Re-check `git rev-parse --show-toplevel` before any step.

## 1. What this batch closes

Five open items, from `PLAN.md` §8.1 and the sections that own them. They share one
rig, because three of them need the player to DIE, and the other two need a follow or a
swing that the same fight already produces.

| Item | What is open | Kind | Source |
|---|---|---|---|
| **a1** re-path same-tick swings | a player `[4]` within 25 ms of an `APPROACH re-path` `0x002A`. Retail 0 of 458 own follows. Ours 1–4 per launch (KILLFAR), 0–6 per launch on both TRAILPIN arms (T 7, N 10) | **known defect, mechanism UNKNOWN** | FINDINGS §1z-ds.45 (H6), §1z-ds.48, §1z-ds.36 |
| **a2** W: the re-approach rides the landing | `WINDUP_HOLDS_APPROACH` shipped; never met on the client | shipped, **unexercised** | §1z-ds.28; §1z-ds.34/.35 ("not exercised") |
| **a3** the death stop | `DEATH_STOPS_WINDUP` shipped: `[3, me, 0]` behind the KILL status. Retail 30 of 30 open-windup deaths, 0 of 155 without | shipped, **unexercised** | §1z-ds.27 |
| **a4** a target's death releases the hold | retail releases at the chain's next scheduled event with `[3]` for a swing in flight (20 of 20, §1z-ds.31); ours releases next tick and drops the swing **silently**, citing one live close (`authsrv.py` attack_tick's target-gone branch: "n=1, castmech 3c") | **CONTESTED** — two witnesses disagree | §1z-ds.31 "Recorded, not changed" |
| **b** SHRINEWARP 1z-dp.4 | a death mid-leg, raised IN PLACE (a hero's signet, or the 10 s timer), keeps the stale click latch; the first press re-pins at the leg's lerped point — up to the leg's remainder | **known defect**, derived from the code, never exercised | §1z-dp.4; `revive_player` clears no latch |

**Out of scope:** RANGERLOOP-F9 (the pre-Searing Ranger's late halt). It is the ranged
approach's mirror problem and needs a Ranger rig; it is a different arc.

## 2. Desk steps first — no client

The order matters: **a run is the last instrument, not the first.** Two of the five
items (a1, a4) are not ready to be predicted, and one (b) can be fixed and locked
offline.

- **DEATHWALK-D0 — bring the scorers into the tree.** Every scorer of record for the
  1z-ds batches (`kf_sametick.py`, `tp_score.py`, `score_ds3.py`'s windup-follow and
  death-stop counts, `h_retail_death.py` / `h_ours_deaths.py`, `r_windup_follow.py`,
  `r_death_any.py`) lives only in a prior session's scratchpad. Copy what this batch
  uses into `studies/movecode/review/`, re-run each against its own published number
  (TRAILPIN's T 7 / N 10, §1z-ds.27's 30 of 30, §1z-ds.28's 0 of 1,654) and refuse to
  use one that does not reproduce. A run scored by a file nobody can open is not
  reproducible.
- **DEATHWALK-D1 — a1's mechanism, from the tapes already on disk.** `follow_order_at`
  is written on re-paths too (`_approach_send`), so §1z-ds.36's re-read SHOULD fire for
  them, and yet the swings happen. Read the operand at each occurrence (KILLFAR,
  TRAILPIN and LEADRETIRE tapes; 17+ events): did `follow_order_at` change in that tick?
  what were the re-path leg's length and eta? what did `_player_body_moving` return after
  the re-read? Two rivals, neither favoured: **(i)** a re-path whose stop point is
  already within reach makes a near-zero leg whose latch expires at once, so "moving" is
  honestly false; **(ii)** the re-path is sent from a site other than attack_tick's own
  `approach_tick` call (the landing's same-tick re-approach, or the zero-run follow after
  a re-pin, K2 91.502). The fix is designed only after the operand is read, and ships
  behind its own revert flag.
- **DEATHWALK-D2 — a4's contest, settled at the desk.** The "no hostile died" behind
  §1z-ds.31's zero exposure is about the seven OWNER tapes. The harness corpus should
  hold many target deaths (the slice, daggers and weapons runs kill Hatchers), and
  counting them is this step's first job, UNVERIFIED until it is done. Census
  ours: on a target's death with the player's swing in flight, what do we send and
  when. Census retail again, with the swing-in-flight split explicit: does the `[3]`
  depend on the swing being in flight, and does castmech 3c's n = 1 close fall in the
  other cell? If the two witnesses are one rule seen from two cells, write the rule;
  if they truly disagree, the contest gets its own section and a run of its own, not
  this one.
- **DEATHWALK-D3 — fix b offline.** `revive_player` clears the click latch and leg and
  calls `_forget_client_position`, as the wipe already does (§1z-dp.3), behind its own
  revert flag. One change per test: a `test_shrinewarp` section drives a real mid-leg
  death, an in-place rise by each route (the hero signet, the timer) and a real press;
  the fixed arm sends no `0x002C`, the known-bad arm re-pins at the leg's lerped point.
  Per "don't ask to ship", this ships ON once derived, flagged and tested; E2 below
  confirms it on the client.

## 3. The scripted experiments

**Driver.** Agent-driven, `toolkit/harness/session.py` on the loopback build under
`vault/run/slice/`, `agenttap.py` beside it at 30 Hz (the rendered position is the
warp instrument; `movetap` cannot certify under the harness). Interleaved arms
(A1 B1 A2 B2 …), cap 8 launches per experiment, +2 per arm if a floor misses, then stop.
**An arm under its floor is UNEXPOSED, not a null.**

**Rig.** `vault/sandbox/revheal3` as it stands: player 140 hp, two Monk heroes with
Resurrection Signet (skill 2), a raider with 3,000 hp hitting 40–60 every 1.75 s. The
player dies often, the heroes raise in place, and a full wipe sends everyone to the
shrine (the case SHRINEWARP already fixed). A heroless copy of it gives the 10 s timer
route. Server flags go inside `--game-args`.

| Experiment | Arms (one flag) | Exposure, and how it is made | Floor per arm |
|---|---|---|---|
| **DEATHWALK-E1** a3 death stop | default vs `--death-keeps-windup` | the player's own windup open at the killing blow. A phase lottery (the windup is 0.4458 of the swing), so the plan re-presses `attack:` after every rise | 5 open-windup deaths *(launch count pending the pilot)* |
| **DEATHWALK-E2** b in-place rise | D3's flag on vs off | a death DURING an unfinished click-walk (long `click:x,y` legs into the raider's reach), an in-place rise, then an attack press | 3 such deaths with remainder > 100 u |
| **DEATHWALK-E3** a2 W | default vs `--approach-in-windup` | a target that leaves reach INSIDE the player's windup. **The source is unsolved**: the candidates are the raider switching to a hero, a hero's hit pulling it, or a follow of a moving hero. Pilot first, one launch, floor check only | 5 left-reach-in-windup events |
| **DEATHWALK-E4** a1 re-path | D1's flag on vs off | none needed: `followpin-g` + TRAILPIN's plan already makes 0–6 per launch | 5 re-paths per launch |

E4 runs on `followpin-g`, not `revheal3`: it is the rig whose control rate is known.
a4 has no experiment until D2 says whether it needs one.

## 4. Predictions — to be filled by the desk steps

| | Prediction | Retail | Known-bad arm |
|---|---|---|---|
| **DEATHWALK-H1** (E1) | every open-windup player death carries `[3, me, 0]` after the KILL status, at index 1 of the dier-named messages | 30 of 30; index 1 on 27 of 30 | 0 |
| **DEATHWALK-H2** (E1) | 0 `[3, me, 0]` on deaths with no windup open | 0 of 155 | 0 |
| **DEATHWALK-H3** (E2) | after an in-place rise, the first press sends no `0x002C` at the stale leg and the drawn body does not jump > 25 u (agenttap agent 1) | indirect only *(pending D3: a rise-then-press witness)* | a re-pin at the leg's point; jump = the leg's remainder |
| **DEATHWALK-H4** (E3) | 0 own `0x002A` inside an own windup; every re-approach at or after the landing, most in the landing's batch (`[1]`, `[8, 0]`, `0x002A`) | 0 of 1,654; 18 of 18; 13 of 18 in the batch | a follow inside the windup |
| **DEATHWALK-H5** (E4) | 0 swings within 25 ms of a re-path on the fixed arm | 0 of 458 | 1–6 per launch *(pending D1's mechanism)* |

**Aborts, checked between launches:** a client assert or crash dialog (stop the
sequence and read the dump statically first); the player face-down more than 60 s
(a wipe loop); an agenttap file with no agent-1 rows (the instrument died, so the
launch scores nothing).

**Owner questions.** None: every item here is wire- or tape-scored, and none is a feel
question. If D3's fix is confirmed, the owner's next ordinary session is the witness
that it is unnoticeable. That is a feel question, asked afterwards, not a gate.

## 5. Cost

D0–D3 are desk work, about a session. E1–E4 are 32 launches at the base cap plus E3's
one-launch pilot (up to 8 more if floors miss), around 7–8 minutes each: roughly four
hours of machine time with nobody at the keyboard, less if the floors are met early. E3's pilot comes first, because it is the only
experiment whose exposure might not exist.
