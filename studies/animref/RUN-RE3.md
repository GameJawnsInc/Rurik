# ANIMREF-RE run 3 — HOLD the key, don't tap it

**Written before the run, after §25.** One question, one session, loopback,
nothing changed on the server. This is the cheap run that must happen before the
expensive one (a live-service capture).

---

## THE QUESTION

> **When you hold the movement key through the damage instead of tapping it, does
> the slide fire — and does it feel like stock?**

## Why this run exists

Run 2 said your presses were refused 14/14. The nine-agent follow-up found that in
**12 of those 14 the gate went clear within 10 ms** of the refusal and stayed
clear — and nothing re-dispatched for the next 1.8–2.2 s. During a real walk the
client re-issues at frame rate (p50 16 ms), so a key that was still down would
have gone through immediately. **It went through on exactly the two attempts where
it was down: 7 and 8, at 59 ms and 165 ms.** Those are your "quarterstep-ish" ones.

So the reading is that the press ended before the round trip did. Your own words
for stock are *"I can **hold** W right as the damage hits"* — a hold, not a tap.
This run gives that reading its fair test.

**This is not me telling you that you pressed it wrong.** The instrument cannot
see your fingers; it sees dispatches, and the inference above is exactly the kind
this arc has already gotten wrong twice. That is what the run is for.

## Registered predictions — do not edit after the run

| # | Prediction | Refuted if |
|---|---|---|
| **P1** | with the key HELD through the damage, most attempts slide | they still stand still with the key demonstrably down |
| **P2** | the slides start **50–200 ms** after the gate clears | they start much later, or at no consistent lag |
| **P3** | the gate still reads SET (`0x3`) at the press | it reads clear — then the refusal was never the mechanism |

**P3 is the control.** It must still refuse; what changes is whether the *second*
dispatch happens. If the gate stops reading SET, something else changed and the
comparison with run 2 is void.

## The run

Same launch as run 2 — nothing about the server has changed:

```powershell
python toolkit/harness/session.py --enemy --keep-open --hold 420 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 322,105,0,0"
```

Get into open ground, target the Hatcher, then in a second window:

```powershell
python toolkit/clientscan/movehook/attach.py --minutes 4
```

**Do, in order:**

* **Control, ×3:** walk around normally, no attacking.
* **Batch A — HOLD, ~8 attempts:** auto-attack the Hatcher, and **press and KEEP
  HOLDING** the movement key from just before the damage until you have clearly
  either moved or not. Hold it a good half-second. Count roughly how many slid.
* **Batch B — TAP, ~4 attempts:** the same thing but tapping, as in run 2. This is
  the paired comparison, in the same session and the same server state.

Stop and read:

```powershell
python toolkit/clientscan/movehook/attach.py --stop
```

```powershell
python toolkit/clientscan/movehook/readhook.py
```

**Report:** the `ANIMREF-RE the two WALK GATES` section, plus one line —
*"held: about N of M slid; tapped: about N of M"* — and, if you are willing to say
it, whether any of the held ones **felt** like a stock slide. That last part is
the only thing no instrument here can produce.

## What each outcome means, decided in advance

* **Held slides, tapped does not** → §25.2's reading is confirmed end to end. Our
  server's wire is then not distinguishable from retail's on this mechanism, and
  anything left is feel or the §25.4 thread (what ends the other 75% of retail's
  holds).
* **Neither slides** → §25.2 item 1 is wrong, the client is not re-dispatching
  when it should, and the live-build movehook session becomes justified.
* **Both slide** → run 2's failures were something transient, and run 2's 14/14
  needs re-examining before anything is built on it.
* **Held slides but feels wrong** → the mechanism is right and the residual is
  timing/latency, which is a different investigation (retail's clear costs 34 ms
  of round trip; ours costs ≈0 server-side plus 59–165 ms of client apply).

## Provenance and safety

Read-only int3 tap, `ours` build → loopback, cage verified. No live service, no
`C:\gw`. Output to `vault/research/movecode` (gitignored). Score **per file, never
pooled** (§25.5).
