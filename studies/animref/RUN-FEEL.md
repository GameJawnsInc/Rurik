# RUN-FEEL — do the SYMPTOMS go away? (ANIMREF-RE §40.13)

**Registered before the run.** The operator plays normally; the instrument is
the operator. Everything below is written down first so the answers cannot be
rationalised into agreeing with the fix afterwards.

Behaviour under test: `MOVECODE-1z-t` / `KBD_SYNC`, default ON, merged `671c45d`.
Its *mechanism* is already closed — RUN-1zT measured the client's world-0 copy
going from p50 237 u to 0.0 u from the body it draws. **This run asks a
different question, and no amount of memory-scoring answers it:** does the
player SEE the difference?

> The harness can prove the body travelled N units. That is not the claim.
> Set up the arms, hand over the keys, ask one question.

---

## 1. The primary question — ONE

> **Does the Hatcher still swing at you from a distance it should not reach?**

That is §40.7's first symptom and the one §40.13 predicts should vanish **with
no enemy-side change at all**. Everything else below is secondary and must not
be allowed to blur it.

## 2. The full symptom checklist, with a PREDICTED SPLIT

This is the part that can fail informatively: the fix is predicted to remove two
symptoms and **leave a third untouched**. A run where all three vanish is
*suspicious* — it would mean something changed that this session did not change.

| # | §40.7 symptom | prediction | why |
|---|---|---|---|
| 1 | the enemy swings from long range | **GONE** | the collision disc parks the enemy relative to the player's world-0 copy; that copy now tracks the drawn body |
| 2 | the enemy warps into your body | **GONE** | same cause, other tail of the same distribution (rendered enemy landed 2–587 u away) |
| 3 | **you warp when you issue a move command right beside the enemy** | **STILL THERE** | agent-vs-agent collision is **unmodelled server-side** (§40.7 symptom 3, §40.12 item 2, the `0x006011F0` dig). Nothing in 1z-t touches it |
| 4 | your own body warping during ordinary keyboard walking | **GONE / much rarer** | this is the world-0 drift itself |

## 3. Confounds named in advance, so they are not read as refutations

- **CLICK-to-move is only partly covered, and that is by design.** The lead and
  the family-rate ride the keyboard arm (`0x003D`); a click walk's *transit* is
  unchanged. The stop echo fires on any `0x0047`, so a click walk's *arrival*
  does get re-pinned. **So: warps during a long click-walk are NOT a refutation
  of 1z-t** — that is the click path, which has its own graveyard and its own
  open work. Keyboard-walk warps ARE in scope.
- **The first moment of a walk is the fix's weakest point.** RUN-1zT measured
  the whole residual as an acquisition transient on the opening leg (198.9 u,
  against ~6 u on every later leg). A small jolt at the *instant* you start
  moving is expected and already recorded; a warp mid-walk is not.
- **Our navmesh has coverage debt.** On the scored run the clip's
  `origin-unwalkable` door opened on 3 of 12 grants. Near geometry we model
  badly the lead falls back to a zero-distance grant — safe, but it means the
  fix is weakest exactly where the map is worst. Walking into a wall and
  feeling something odd is worth reporting but is a *different* defect.
- **Zero exposure is not a null.** If the Hatcher never actually engages, symptoms
  1 and 2 have run no trials and the run cannot speak to them. Get hit a few
  times on purpose.

## 4. What REFUTES the fix

- Symptom 1 or 2 still present at anything like their old frequency.
- A **new** class of visible warp that the shipped default did not have. This
  outranks every number: the arm is additive on the wire, so a new warp class
  would mean the lead is ordering walks our mesh should have refused.
- Your own body warping during plain keyboard movement on open ground.

## 5. Setup

Enemy on and survivable (`--enemy-hit 0.02` — the default kills in ~7.5 s).
`agenttap.py` records both world copies for the player and the Hatcher
throughout, read-only, so the subjective report can be joined to the objective
track afterwards — §40.9 cost three runs by steering around a body nobody had
measured, and this is the cheap insurance against repeating that.

**No `--walk`. The operator drives.** This is the run where that is correct:
the question is about experience, and there is no scripted substitute for it.

## 6. The four questions, to be answered in the operator's own words

Asked verbatim after the session, not during:

1. **Did the Hatcher swing at you from further away than it should have?**
   (yes / no / sometimes — and roughly how often)
2. **Did the Hatcher ever appear to warp into or through your body?**
3. **Did YOU warp when issuing a move command right next to it?**
   (this one is predicted to still happen)
4. **Did your own movement feel right — any warping, rubber-banding or
   sticking while walking on the keyboard?**

Free-form after that: anything that felt wrong that these four did not ask
about. The operator's unprompted reports have been a reliable instrument in this
arc twice; the questions are a floor, not a ceiling.

---

## RESULT — RAN 2026-09-03 08:46. **REFUTED on the primary question, and the
## capture says the fix never applied to how the operator actually plays.**

**The operator, verbatim:** *"still seeing desync, enemy at long range, and
couldn't resume attacking after some point. bad run."*

That is symptom 1 present. §2 predicted it GONE. **Registered outcome: REFUTED.**

### Why — the operator plays with the MOUSE, and 1z-t is a keyboard fix

Capture `authsrv-20260903T084616-c1.jsonl`, 24.3 s of live play:

| | count |
|---|---|
| `click_verdict` rows | **40** |
| of those, **fired** | **0** |
| refusal reason | **`geo-stale`, 40 of 40** |
| client position reports (`0x003D`, keyboard) | 5 |
| `KBD LEAD` sends | **2** |
| `KBD STOP-ECHO` sends | **0** (no `0x0047` arrived at all) |

`geo-stale` is the 1.0 s freshness gate (`authsrv.py:16373`). During click-to-move
the client goes quiet, so **every** click fails it: the server grants nothing, the
client paths itself, and world-0 stands where it was until the client's own
desync test drags the body back. **None of 1z-t's three terms engage on the click
path** — the lead and the family rate ride the `0x003D` arm, and the stop echo
needs an `0x0047` that never came.

The tap shows the same split as a number (220 samples, `agenttap-20260903T084632`):

| | RUN-1zT (scripted keyboard) | this session (clicking) |
|---|---|---|
| player world-0 vs drawn body p50 | 0.0 | 0.0 |
| **p90** | **17.7** | **223.1** |
| max | 198.9 | 494.9 |
| rendered enemy vs rendered player p50 / p90 | — | 78.3 / **336.8** |
| enemy's own two copies p50 | 5.2 | 4.6 |

**The fix holds at the median and collapses in the tail**, and the tail is where
the symptom lives. The enemy remains faithful (4.6 u between its own copies), so
§40.11's reading survives: this is still the player's world-0 desync, just on a
path 1z-t does not cover.

### What this settles

- **MOVECODE-1z-t is correct, confirmed, and scoped to a regime the operator does
  not use.** Nothing about RUN-1zT is retracted; its claim was always about the
  keyboard arm and it holds there.
- **§40.13's question is NOT answered.** The symptoms were never given a chance to
  respond, because the mechanism under test never ran. This is a **zero-exposure
  result for the treatment**, not evidence against the mechanism — the same trap
  §2 named for the enemy and missed for the fix itself.
- **The next step is already in the tree, measured and costed.** `PLAN.md` §7 Q13,
  2026-08-27, decomposing the same refusals: *"Widen or bypass the freshness
  window (13 of 17). ... This is the cheapest thing on the list and the largest
  single contributor."* It also records that this can be asked **on its own,
  without the D1_LEAD bundle.** This run reproduces it at **40 of 40**.

### The scope error, named so it is not repeated

The instrument run (RUN-1zT) used scripted keyboard input because that is what
`--walk` can drive. The fix was then aimed at the keyboard arm and assumed to
transfer. **Nobody checked which movement path the operator actually uses before
choosing which path to fix** — and 24 s of ordinary play answered it decisively
(40 clicks against 5 keyboard reports). A regime census is cheap, and it belongs
BEFORE the fix, not after it.

### This run's own limits, stated rather than smoothed

- **~24 s of play.** The client exited cleanly (code 0, no error dialog) 31 s into
  a 720 s hold; the tap recorded 220 samples and stopped there. Thin — but the
  40/40 refusal signal is unambiguous and does not need length.
- Two process failures cost operator time and are recorded in the session log: a
  **relative `--exe`** made `Popen` resolve the client against the working
  directory it sets, so the first launch never spawned one; and the tap then timed
  out on its 120 s wait and had to be restarted, losing the session's first ~40 s.
- **Symptoms 2, 3 and 4 are UNREAD**, not negative. With the treatment inert and
  the run 24 s long, the predicted split (3 staying while 1 and 2 go) never got a
  fair test.

### Carried forward — "couldn't resume attacking": DIAGNOSED to a mechanism, not fixed

A symptom §6's four questions did not ask about, and the same capture explains
it. **Ten attack presses; only the first two produced a player swing.** Joined to
the tap, every press's `0x002C` re-pin lands within 0.2–24 u of the DRAWN body, so
the first hypothesis — that the re-pin was teleporting the body backwards — is
**REFUTED**. What the join shows instead:

| press (t) | body→Hatcher | what followed |
|---|---|---|
| 16.42 / 19.42 / 22.51 | 77 / 73 / 86 u | swing ✓ |
| 21.06 | 44 u | swing, then `attack_stopped: the player moves before the swing landed` |
| **21.86 / 31.77 / 33.17 / 37.64** | **85 / 84 / 21 / 39 u — all inside 144 u reach** | **nothing: no swing, no approach, no row, no console line** |
| 29.73 / 36.27 | 203 / 113 u | APPROACH (correct — out of reach) |

**The mechanism, from source (RECONSTRUCTION, load-bearing links verified):**

1. The click arm abandons the approach and re-stamps `click_moving_at` at its
   **top** (`authsrv.py:19049-19051`), *before* the freshness verdict at `:19168`
   — so a click the server then REFUSES `geo-stale` still counts as a move.
2. `_player_body_moving` (`:10365`) reads that latch, and its own comment says it
   is "armed on EVERY 0x003E".
3. `attack_tick` defers the swing clock while the body is "moving"
   (`player_last_swing += now - since`) and cancels an in-flight swing on a move
   (`MOVE_ENDS_CHAIN`, §39 — the 21.06 row above is exactly that).
4. The press's `0x002C` clears the latch; the next click re-arms it ~200 ms later
   — 40 clicks in 20 s — before the tick can open a swing.

So **click-spam starves the swing, and the clicks doing it are ones the server
refused to act on.** The server believes a body is moving that it declined to
move. This is the SAME root as the gate refusal seen from the attack side, and it
means answering clicks (the gate fix) changes this too — but it is a separate
defect with its own fix (a refused click must not arm the moving latch, or the
latch must expire), and it is **not** built here.

**Instrument gap, recorded:** a press that reaches `attack_tick` and is refused
by the interval / moving / target branches leaves **no row and no console line**.
Two of the four silent presses have literally nothing within 0.7 s of them in the
capture. The R11 lesson ("a suppressed grant is PRINTED, never silent") has not
been applied to the swing.
