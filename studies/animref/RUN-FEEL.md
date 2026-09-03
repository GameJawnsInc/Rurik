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

## RESULT

*(to be filled in from the operator's own words plus the paired agenttap
capture — the subjective answer is the verdict, the capture is the corroboration
and never the other way round)*
