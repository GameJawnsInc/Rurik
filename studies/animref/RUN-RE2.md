# ANIMREF-RE run 2 — the gate at the ACTUAL quarterstep window

**Written 2026-08-31, BEFORE the run, after the owner's catch on run 1.** Run 1
measured *move-at-start* (press skill, walk immediately). That is not the
quarterstep. The quarterstep is a move timed to the **animation completing**, and
it is the window the *"unreliable, doesn't feel like stock"* verdict is actually
about. This run reads the gate at that window instead.

Loopback, caged, synthetic credential. PowerShell, from `C:\gd\rurik`.

---

## THE QUESTION

> **At the instant you try to quarterstep — attack, let the swing resolve, tap
> movement to slide — is the walk gate `[char+0x64] bit 0` SET or CLEAR?**

Run 1 proved that *when the gate is set, a move press is eaten*. What it did not
show is whether the gate is set at the quarterstep window. Three things can be
true and they need different fixes:

* **the gate is SET there** → our server holds property 8 across the slide, and
  the quarterstep is blocked by the same mechanism run 1 found;
* **the gate is CLEAR there** → the gate is not the quarterstep's problem; the
  freeze you feel is downstream (the path query, a zero speed product, or the
  client not re-dispatching), and §21.1's pair is the wrong tree for *this*;
* **it is SOMETIMES set** → "unreliable" is literally the 0.3 s hold window: your
  slide sometimes lands inside it and is eaten, sometimes outside it and works.

## Why the harness does NOT drive this — you do

Quarterstepping is a feel thing ([[quarterstep-is-a-feel-thing]]) and this run
honours that completely: **the instrument is read-only and passive.** It records
the gate word every time the client begins a move, whoever pressed the key. So
**you play, by feel, the way you would try to quarterstep in stock** — I script
nothing about the timing. The tap simply records what the gate was at the moment
*you* decided to slide. This is the one design where the instrument and the feel
can meet without the harness pretending to judge the feel.

## Registered predictions — do not edit after the run

| # | Prediction | What it would mean |
|---|---|---|
| **C** (control) | your idle walks read the gate CLEAR (`0x2`) | instrument sound; a SET elsewhere is real |
| **P1** | the quarterstep attempts that **stood still** read the gate SET (`0x3`) | the gate blocks the slide — run 1's mechanism extends to the quarterstep |
| **P2** | the attempts that **slid** read the gate CLEAR (`0x2`) | the gate state, not something else, decides whether the slide fires |
| **P3** | roughly `(felt failures) ≈ (gate-SET presses)` during the attack windows | the felt "unreliable" IS the hold window, quantified |

**Refuted if:** every quarterstep attempt reads CLEAR regardless of whether it
slid — then the gate is *not* what blocks the quarterstep, and the next suspect
is the re-dispatch latch `0x005355C0` or the path query, not property 8.

## The run

**One session, ~5 minutes.** I will say when it starts. Bounded by the capture
timer and by you closing the client.

**1 — launch** (identical to run 1):

```powershell
python toolkit/harness/session.py --enemy --keep-open --hold 420 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 322,105,0,0"
```

**2 — get into open ground**, not against a wall, and target the Hatcher.

**3 — attach the tap** (second PowerShell window, once you are in the world):

```powershell
python toolkit/clientscan/movehook/attach.py --minutes 4
```

**4 — do these, in order:**

* **Control, ×3:** just walk around a little, no attacking. (This is prediction C.)
* **Quarterstep, a batch of ~8–10:** attack the Hatcher — auto-attack by clicking
  it, or press slot 1 (322) — **let the swing play**, and tap movement right as it
  resolves, the way you would to slide in stock. Do it your way; the timing is the
  whole point and it is yours. **Keep a rough count of how many actually slid vs
  how many you just stood still.**

**5 — stop and read:**

```powershell
python toolkit/clientscan/movehook/attach.py --stop
```

```powershell
python toolkit/clientscan/movehook/readhook.py
```

**6 — tell me two things:** paste the `ANIMREF-RE  the two WALK GATES` section,
and say roughly *"about N of M slid."* That second number is what turns the gate
distribution from a byte into an answer about the feel — and it is yours to give,
not the instrument's to guess.

## What each outcome sends us to next, decided in advance

* **stood-still = SET, slid = CLEAR** → the gate is the quarterstep's blocker.
  The fix is a server question about *when* we hold property 8 — and §22.6's
  warning stands: retail holds it *longer* than we do, so the answer is likely
  "match retail's re-arm/re-dispatch shape", not "hold it less".
* **all CLEAR, including the ones that stood still** → property 8 is exonerated
  for the quarterstep; the freeze is downstream and RUN-RE3 taps the path query
  (`agapi_setdest` already fires) and the re-dispatch latch `0x005355C0`.
* **all SET, including the ones that slid** → the gate does not decide the slide
  after all, and the SET reading is incidental; that would refute P2 and send us
  back to the wire timing.

## Provenance and safety

Same read-only int3 tap as run 1, `ours` build → loopback, cage verified. No
live service, no `C:\gw`. Output to `vault/research/movecode` (gitignored).
Nothing about the server changed from the shipped default; this is a passive
instrument on an ordinary session.
