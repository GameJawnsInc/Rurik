# RUN-1zDB — the movement cancel's displacement gate, A/B against a wall

**REGISTERED 2026-09-10, before any launch.** `main` at `a2f4ecaa`. Hand-driven: the
operator quartersteps, because that is the arm under test and no script can produce it.
Scores MOVECODE-1z-db (`MOVE_CANCEL_NEEDS_DISPLACEMENT`), whose predicted effect is a
RECONSTRUCTION until a session measures it.

## 1. The question, in the operator's own words

> **When I press into a wall and keep attacking, do my swings land?**

That is the whole run. One question, one regime, two arms.

## 2. Why this regime and not session 8's route

**Session 8 could not have answered it, and that was checked rather than assumed.** Its 21
swings carry **zero** moved-windup exposure and only **2** still-cancels — the class 1z-db
suppresses. Scoring the fix against it would have been a null with no trials in it.

The corpus says which regime does expose it. Per capture, still-cancels against swings:

| capture | still-cancels | swings |
|---|---|---|
| `20260823T102742` | **10** | 10 |
| `20260901T125928` | 9 | 52 |
| `20260823T101329` | 5 | 23 |
| *(session 8, `20260909T221342`)* | *2* | *21* |

and the mechanism in the maximal exposer is unambiguous: **every one of its windups carries
a `0x003D` whose reported position moved `0.00 u`** — 60 accepted reports over 34 distinct
positions, a client reporting a held heading from a body that is not moving (§1z-cp.3's
corner hold). So the regime is: **body against geometry it cannot walk into, movement key
held or tapped, attacking throughout.**

## 3. The two arms

Both legs are the SAME corner, the SAME action, minutes apart — so route, weapon and skill
differences cancel, which is what a hand-driven A/B usually cannot claim.

* **Arm A — SHIPPED (HEAD default).** `MOVE_CANCEL_NEEDS_DISPLACEMENT = True`.
* **Arm B — KNOWN-BAD.** `--no-move-cancel-displacement`: a keyboard report cancels the
  chain whether or not the body moved. This is the pre-1z-db server.

**Exactly one behavioural default separates them.** Everything else shipped since session 8
is telemetry (`swing_verdict`, `chain_pause`) or tests; SKILLS-FA's armour term is
unreachable here because the run passes `--no-enemy-skills`. One run, one verdict.

## 4. Predictions, fixed BEFORE the run

* **P1 — the headline.** Arm B: still-cancels ≥ **50 %** of swings. Arm A: still-cancels
  **0**. (Arm B's floor comes from the exposers above, 10/10 and 9/52; 50 % is deliberately
  below the best of them.)
* **P2 — the landed fraction separates.** Arm A ≥ **80 %** of swings land damage or a
  critical; arm B ≤ **50 %**. The corpus's still-player baseline is 90.3 % landed against
  retail's 99.0 %, so arm A failing this bar is a real result and not a thin-n wobble.
* **P3 — no silent drop, either arm.** Every swing that does not land carries a
  `swing_verdict` row naming its branch (§1z-cx's instrument, its first live exercise). A
  drop with no row reddens this clause whichever arm it is in.
* **P4 — the operator's own verdict, recorded verbatim.** Answer AFTER both legs, not
  between them: *"In which leg could you actually hit the Hatcher while pressed into the
  wall?"* A shape difference, not a timing one — arm B should be visibly unable to land.
* **P5 — a free read, not a criterion.** The `chain_pause` rows (§1z-dc) name which branch
  a moving tick returned through. §1z-dc tested three candidate suppressors and refuted all
  three; this is the first session that can answer it by reading a row. **It scores
  nothing here** — recorded, and picked up by its own derivation.

## 5. The exposure floor, and the abort

**Pre-registered, because zero exposure is not a null.** Per leg: **≥ 12 player swings**,
and in arm B **≥ 8 windups containing a `0x003D` whose displacement is < 1 u**.

**ABORT:** if arm B is below that floor the regime did not expose the class, and
**neither arm is readable** — report the shortfall and re-run; do not score arm A's zero
as a success. (Arm B is the exposure witness, not a control over arm A's positive: if arm
B makes the floor and arm A shows the predicted zero, P1 stands on its own.)

## 6. The run

**Terminal 1 first, and leave it running** — it waits up to 300 s for the client, so it
must be armed BEFORE the launch.

### Leg A — the shipped default

```powershell
python toolkit/clientscan/agenttap.py --agents 1,10 --seconds 140 --wait 300 --out vault/research/movecode/1zdb1-agenttap.jsonl
```

```powershell
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --enemy --hold 110 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0"
```

HANDS OFF THE KEYBOARD until "body is in the map" (~25 s) — the harness types the login and
the map entry. Then, for the ~110 s it holds: **walk to the corner at the foot of the
stairs, get the Hatcher onto you, press INTO the wall and keep attacking.** Keep the
movement key held or tapping the whole time. It tears itself down; nothing is left parked.

### Leg B — the known-bad arm

```powershell
python toolkit/clientscan/agenttap.py --agents 1,10 --seconds 140 --wait 300 --out vault/research/movecode/1zdb2-agenttap.jsonl
```

```powershell
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --enemy --hold 110 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0 --no-move-cancel-displacement"
```

Same corner, same action, same duration. **Do not answer P4 until both legs are done.**

## 7. Scoring

```powershell
python studies/movecode/review/swingcensus.py
```

```powershell
python studies/movecode/review/sessionscore.py
```

`swingcensus` reads the two new captures directly and — for captures written from
2026-09-09 on — attributes each silent swing from its `swing_verdict` row rather than by
elimination, which is what makes P3 checkable at all.

## 8. What this run cannot settle

* **The exposure divergence.** Our player moves during 10.0 % of windups against retail's
  1.2 % — a REGIME difference (the operator quartersteps; retail's corpus stands and
  auto-attacks), not a rule, and 1z-db changed nothing about it. This run does not address
  it and its numbers must not be quoted as if it had.
* **The moved-windup cancel rate**, ours 77.1 % against retail's 63.6 % on n = 11. Too thin
  to act on, unchanged by 1z-db, and out of scope here.
* **The cast half of `cancel_on_move`**, which still fires on the report on both arms. The
  bar is empty by design (`--skills 0,...`) so no cast happens; that is scoping, not
  evidence about casts.

## 9. RESULT — ran 2026-09-10, both legs, owner-driven (MOVECODE-1z-dd)

Captures `20260910T141412` (A) and `20260910T141651` (B); the owner ended each leg after killing
the Hatcher (52 s and 43 s). Full record: [FINDINGS §1z-dd](FINDINGS.md).

| clause | verdict | reading |
|---|---|---|
| swing floor (≥ 12 per leg) | **met** | 15 + 15 |
| arm B exposure (≥ 8 sub-1 u windups) | **NOT MET — 0** | 19 still reports in B, every one BETWEEN swings, none inside a windup |
| **P1** still-cancels B ≥ 50 %, A 0 | **ABORT** | unreadable: B's 2 of 15 are the two reports that did land in a windup; A's 0 is not scored |
| **P2** landed A ≥ 80 %, B ≤ 50 % | **ABORT** | 86.7 % both arms — no exposure, no separation |
| **P3** every silent swing has a `swing_verdict` | **GREEN, 4 of 4** | A: `move-ended-order`, `reach` 146.9 u; B: `cancel:movement` ×2 |
| **P4** the owner's verbatim answer | **pending** | not yet asked in those words |
| **P5** `chain_pause` free read | **NAMED** | every mid-chain moving tick left through `no-target` — the target-forget on the move |

**What the run found instead**, on the one still-report-in-windup it did produce (A, t=30.36):
the gate suppressed the wire stop and the same report forgot the target through an ungated door,
so the swing dropped as `move-ended-order` 62 ms before landing — silently. Shipped under the
same flag (§1z-dd.3). And the ghost the owner described is §1z-cp.3's corner at 520 u drift, with
the Hatcher walking to the phantom and landing a hit from there (§1z-dd.5), plus a CONTESTED
correction: the Hatcher's own body is one of the two blockers in the corner (§1z-dd.6).

**Re-run under HEAD** with the regime that exposes — hold the key INTO THE WALL (not toward the
Hatcher) and keep attacking — same two legs, same floors.
