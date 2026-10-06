# DEATHWALK — death, rise and re-approach: the follow hop's leftovers, as one batch

> **DRAFT, 2026-10-06. NOT REGISTERED, NOT RUN.** This plan becomes a registration only
> when its desk steps have run and their numbers are written into the H rows below.
> **D0–D4 RAN the same day** (§2a): every desk step is done and four fixes ship ON,
> none of them run on a client yet. What is left is registration: the E3 pilot must find
> its exposure, and E5 needs its rig. A launch needs the owner's go-ahead (parallel sessions
> share the harness), announced as **HANDS OFF THE KEYBOARD**.

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

## 2a. What the desk steps found (2026-10-06)

- **DEATHWALK-D0 — done.** Eight scorers of record, plus their support files, are in
  `studies/movecode/review/` (17 files). **Every one reproduces its published number**:
  0 of 458; 1,654 windups / 18 of 18; 30 of 30 / 0 of 155; 20 of 20; KILLFAR H6's 1-4 per
  launch; TRAILPIN's H1-H7 and its T 7 / N 10; DSBATCH3's wire counts. One attribution
  corrected: TRAILPIN's T 7 / N 10 came from `tp_controls.py`, not `tp_score.py`. Both are
  ported.
- **DEATHWALK-D1 — done, fix SHIPPED** (FINDINGS §1z-ds.51). 47 of 49 same-tick swings are
  a re-path due on the tick the body crossed inside its 80 u stop. That re-path makes a
  zero leg that replaces a live latch, and 1z-ds.36's re-read then lets the swing through.
  `STOP_DISC_ENDS_FOLLOW` makes arrival win inside the disc (`--repath-inside-stop`
  reverts). The other two are C2 (a sub-tick re-path) and C3 (a zero-run new follow), one
  each, both leftovers.
- **DEATHWALK-D2 — done, the contest RESOLVED** (FINDINGS §1z-ds.50). It was one rule seen
  from two cells. Retail holds the hold to the chain's next scheduled event: `[8, me, 0]`
  `[3, me, 0]` at the due landing for a swing in flight (20 of 20), `[8, me, 0]` alone at
  the next due start otherwise (34 of 34). castmech 3c's n = 1 close is the second cell.
  Ours diverges in both cells, and has ZERO exposure under today's code. The code
  comments now say so; the behaviour is D4.
- **DEATHWALK-D3 — done, fix SHIPPED** (FINDINGS §1z-dp.5). `RISE_ENDS_LEGS` retires the
  latch, leg and pre-walk report at an in-place rise, through the wipe's own helper
  (`--rise-keeps-legs` reverts). The wipe's own rise is not in place, so each revert arm
  reproduces its defect alone; the test caught that masking.
- **DEATHWALK-D4 — done, fix SHIPPED (2026-10-06, FINDINGS §1z-ds.52).** At the target's
  death the release is scheduled instead of sent: at the swing's `lands_at` with `[3]` if
  it is in flight, else at the next due start. A new order or any hold release cancels
  it. The swing stays armed but unlandable, so a move in the window still carries its
  `[3]`. `TARGET_DEATH_HOLDS`, with `--target-death-releases-now` as the revert;
  `test_playerswing` §26. Its client run, E5, needs a hostile that can die to someone
  else's damage inside the player's windup; revheal3's 3,000 hp raider cannot.

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
**DEATHWALK-E5** (a4; arms: `--target-death-releases-now` vs the default, D4 shipped) runs
on its own rig, built 2026-10-06 (§3a). E2's arms are now `--rise-keeps-legs` vs the
default (D3 shipped), and E4's are `--repath-inside-stop` vs the default (D1 shipped).

### 3a. The E5 rig: `deathwalk-e5`

**What it must do:** make the player's attack TARGET die to someone else's damage, at a
phase of the player's own swing the rig does not choose. That exposes both of D4's cells:
the death inside the windup and the death in the gap after a landing.

**The spec** is `vault/sandbox/deathwalk-e5.toml` (the house place for specs, gitignored).
It compiles with `python toolkit/harness/sandbox.py --spec vault/sandbox/deathwalk-e5.toml --write`
to `vault/sandbox/deathwalk-e5/world.toml`. Its numbers, so it can be rebuilt from here:
- **The player:** a level-3 Warrior with an empty bar and no ranks, holding the starter
  sword (2..3). Health 2,000.
- **The heroes:** 7 and 8, both `academy_monk` bodies at level 20 with an empty bar,
  `[[13, 12]]`, a staff with `damage = [10, 15]` and health 2,000. Not hero 3: the character
  store holds a bar for hero 3, and the store wins over the spec (`sandbox.store_warnings`),
  so it would cast heals and damage spells.
- **The hostiles:** sixteen `bandit_raider`s in four groups of four. Each is level 20 with
  70 health, damage `[1, 1]`, no skills, `[[19, 1]]` and the starter hammer at 1.75. The
  last group's first member is the boss (glow 5), as the compiler requires. Agents
  110–125, in groups along the corridor from y ≈ 3,650 to 10,680.

**The tuning**, computed with the server's own `creature_armor_rating` and
`combatmath.swing_damage`, not assumed:
- A level-20 raider rates 80, of which 20 meets physical damage only.
- The player's sword does **~1 a hit**: mean 0.5 at the spec's rank 0, and 1.0 at the
  store's actual Swordsmanship 5 / level 5. Under `--persist` the store wins there too, and
  the tuning holds either way.
- A hero's staff, at strike level 3 x 20 = 60 against 60, does **12.5 a hit** (10..15).
- A Monte Carlo of the fight (player 1.33 s with a 0.565 s windup; two staves at 1.75 s
  with 0.2–0.6 s of flight; 70 health; RECONSTRUCTION, not a run) gives a median kill at
  5.5 s, and kills split **41.8 % inside the player's windup, 54.1 % in the gap, 4.2 % by
  the player's own landing**. So all 16 dying gives ~7 in-flight and ~9 next-start deaths
  per launch, against E5's floor of 5 per arm.

**Checked offline:** with `RURIK_CONTENT_EXTRA` at the overlay, the server's
`area_population("errand,sandbox")` accepts all 16 rows (ids 110–125, 70 / 20 / `[1, 1]`),
and `[party.sandbox]` carries heroes 8 and 7 at `[10, 15]` and player health 2,000, every
row `source = "invented"`. **Not checked:** that the heroes engage the player's target at
the predicted rate, the staff's real interval and flight, and the 16 actually dying in one
launch. Those need a client, so E5's first launch is a one-launch pilot with a floor check,
like E3's.

**The launch, drafted** (PowerShell; agent-driven, HANDS OFF THE KEYBOARD, on the owner's
go-ahead):

```
$env:RURIK_DAT='C:/gd/Rurik/vault/run/slice/Gw.dat'; $env:RURIK_CONTENT_EXTRA='C:/gd/Rurik/vault/sandbox/deathwalk-e5'
python -u toolkit/harness/session.py --replace --warn 5 --settle 0 --hold 30 --shots 0 --exe C:/gd/Rurik/vault/run/slice/Gw.exe --game-args "--ping-seconds 0.5 --map 168 --party sandbox --area sandbox --spawn-profession 1 --unlocks <the list sandbox.py prints> [--target-death-releases-now]" --actions "0:play" --walk "wait:3 attack:110 wait:16 attack:111 wait:9 attack:112 wait:9 attack:113 wait:9 attack:114 wait:16 attack:115 wait:9 attack:116 wait:9 attack:117 wait:9 attack:118 wait:16 attack:119 wait:9 attack:120 wait:9 attack:121 wait:9 attack:122 wait:16 attack:123 wait:9 attack:124 wait:9 attack:125 wait:12"
```

The flags are TRAILPIN's (proven on this corridor): `--map 168` starts in the corridor, and there is no
`--persist`, so the spec's ranks apply. With `--persist` the store's would, and the tuning holds either
way. `attack:N` is the server's mailbox: the server walks the body in and swings. The first
target of each group gets 16 s for the ~2,100 u walk plus the kill. An `attack:` on a target
the heroes already killed is refused as `dead-target`, which loses nothing.

**The scorer is built (2026-10-06): `studies/movecode/review/e5_score.py`.**
- **Cells from the wire:** it reads each death of the chain target and places it by cell
  from the wire alone: in flight when the chain's last start has no landing and no stop
  before the death.
- **Expected instant, from the wire:** the start plus this chain's own previous windup,
  or the last start plus this chain's own start-to-start gap. The tape's medians are the
  fallback; our own rows are a cross-check only.
- **Arm from the tape:** `flags.TARGET_DEATH_HOLDS`.
- **Verdicts:**
  - `PASS` / `FAIL` on the D4 arm: the batch (`[8, 0]` `[3]` in flight, `[8, 0]` alone
    otherwise), no landing after the death, and within 0.06 s of the expected instant;
  - `old-shape` / `UNEXPECTED` on the known-bad and pre-D4 arms;
  - `input-first`, `hold-down` and `NO-RELEASE`, reported and not judged.
- **Floors:** 5 judged deaths per cell per arm; below that the arm is UNEXPOSED.
- **Abort:** `--check STAMP` exits 3 when a launch has no chain-target death at all, which
  means the rig failed.

Its `--selftest` (about 5 s) has four layers:
- the opcodes and props are the server's;
- 13 synthetic cases, every verdict reachable;
- three tapes written live by the REAL server code: D4 in flight, D4 next start and the
  known-bad arm score `PASS`, `PASS` and `old-shape`, the D4 releases 2–3 ms from the
  wire-derived instant;
- the real pre-D4 vault tape (`20261001T160802` 111.051, D2's specimen) scores
  `old-shape` off real bytes.

**Baseline over September's 570 tapes:** 91 chain-target deaths, 0 `UNEXPECTED`, 0
`NO-RELEASE`. In flight there are 7 (4 `old-shape`, 3 `hold-down`); next start 84 (29
`old-shape`, 2 `input-first`, 53 `hold-down`). That reproduces D2's independent census of
the same tapes.

### 3b. The E5 pilot RAN (2026-10-06): the rig works, and D4 scores 11 of 11

**What ran:** one launch on the D4 (default) arm, on the owner's go-ahead, agent-driven, with
HANDS OFF announced. Launched from `main` at `36230914` with §3a's command; the slice
client's cage cleared it for loopback only. Harness `20261006T193947`; tape
`authsrv-20261006T194028-c1`. RUN VERDICT PASS: 33 plan steps all ran, no assert, and the
client closed cleanly after the hold.

**Pre-registered before launch:**
- the abort: zero chain-target deaths (`--check` exit 3);
- the model's guess: 16 deaths, ~7 in flight, ~9 next start, ~1 by the player's own hit;
- every judged death on this arm `PASS`, within 0.06 s;
- the rig undercut if the heroes did not engage, or if either cell judged fewer than 5.

**What it showed** (`e5_score.py --check 20261006T194028`, exit 0; OBSERVED):
- **All 16 raiders died.** 11 died as the player's chain target and were judged; 5 (112,
  113, 117, 121, 125) died to the heroes before the plan's order named them, so they were
  never the chain's target and are not scored.
- **The heroes landed every judged killing blow:** agents 200 / 201 for 11–15, the tuned
  10–15 band, with 96 hero hits spread evenly over 10..15. The player's own hit size is
  not separately read off this tape.
- **In flight: 5 judged, 5 `PASS`.** `[8, 0]` then `[3]` in one batch at the due landing,
  no landing after the death. Deaths 0.10–0.56 s into the windup; releases 0.008–0.46 s
  after the death.
- **Next start: 6 judged, 6 `PASS`.** `[8, 0]` alone at the next due start, 0.10–0.57 s
  after the death.
- **On time:** every release is within 1 ms of its wire-derived instant. The server's own
  rows agree: `held_to` names the right cell, and `target_death_release` was at most
  0.9 ms late.
- **Against the prediction:** both cells met their floor of 5 in ONE launch; the model
  guessed ~7 / ~9 / ~1, and the run gave 5 / 6 / 0 judged.

**What it does NOT show:**
- that retail's client draws these batches as retail's does (D4 is retail's rule
  replayed on our wire);
- anything about the known-bad arm on this rig. The pre-D4 old shape is already OBSERVED
  on September's tapes (29 + 4 `old-shape`, §3a's baseline), so a `--target-death-releases-now`
  launch would add a same-rig control, not a new fact.

**To finish E5 as registered:** interleave one or more `--target-death-releases-now`
launches (the same command with the flag) until that arm's cells reach 5. The cap of 8
launches is not needed: one launch per arm meets the floor.

## 4. Predictions — to be filled by the desk steps

| | Prediction | Retail | Known-bad arm |
|---|---|---|---|
| **DEATHWALK-H1** (E1) | every open-windup player death carries `[3, me, 0]` after the KILL status, at index 1 of the dier-named messages | 30 of 30; index 1 on 27 of 30 | 0 |
| **DEATHWALK-H2** (E1) | 0 `[3, me, 0]` on deaths with no windup open | 0 of 155 | 0 |
| **DEATHWALK-H3** (E2) | after an in-place rise, the first press sends no `0x002C` at the stale leg and the drawn body does not jump > 25 u (agenttap agent 1) | indirect only *(pending D3: a rise-then-press witness)* | a re-pin at the leg's point; jump = the leg's remainder |
| **DEATHWALK-H4** (E3) | 0 own `0x002A` inside an own windup; every re-approach at or after the landing, most in the landing's batch (`[1]`, `[8, 0]`, `0x002A`) | 0 of 1,654; 18 of 18; 13 of 18 in the batch | a follow inside the windup |
| **DEATHWALK-H5** (E4) | 0 swings of the C1 class (a `[4]` within 25 ms of a re-path with run ≤ 0.4 u inside the stop) on the fixed arm; C2 / C3 counted and reported, not held to 0 | 0 of 458 (193 re-paths, nearest 43.5 ms) | 1–6 per launch, C1 (TRAILPIN T 7, N 10; KILLFAR 1–4) |
| **DEATHWALK-H6** (E5; scored by `review/e5_score.py`, 5 judged per cell per arm) | a chain target's death releases at the due landing with `[8, me, 0]` `[3, me, 0]` for a swing in flight, and at the next due start with `[8, me, 0]` alone otherwise | 20 of 20; 34 of 34 | `[8, me, 0]` on the next tick, no `[3]` |

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
