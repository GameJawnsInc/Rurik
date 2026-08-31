# ANIMREF-RE run 1 — which early-out does the applier take?

**Written 2026-08-31, BEFORE the run.** One question, one case, one capture,
with its own positive control inside it. Loopback, caged, synthetic credential.
PowerShell, from `C:\gd\Rurik`.

---

## THE QUESTION, in one line

> **When you press an attack skill and then immediately try to walk and the body
> does not move — is the client refusing at the walk gate, or is it never getting
> a path?**

Those are different bugs with different fixes and the wire cannot tell them
apart (§22.2: all seven exits send the same `0x003D`). This run reads the two
words the client itself branches on, at the instant it branches.

## What is being measured, and what is NOT

**Measured:** `[char+0x64]` and `[char+0x10C]` at every `chcli_dir` /
`chcli_point` entry, from which the branch is decoded — `E3-walk-gate`,
`E2-status-bit8`, `E4-dead`, or `passed-flag-gates`.

**NOT measured: anything about how it feels.** This run cannot and will not
produce a quarterstep verdict — that stays yours, and this is not the run for
it ([[quarterstep-is-a-feel-thing]]). Do not judge the fix here; there is no fix
in this build. **Nothing about the server changed.** This is the shipped default
with a read-only instrument attached.

## Registered predictions — write nothing after the fact

| # | Prediction | Refuted if |
|---|---|---|
| **P1** | The presses that do not move report **`E3-walk-gate`** — `gate_flags & 1` SET | they report `passed-flag-gates` (the gate is clear and the freeze is downstream — §22.6's option 2, and the model is wrong) |
| **P2** | The **idle** walks report `passed-flag-gates` with the gate CLEAR | they report `E3` too — then the reading is a constant and the instrument is measuring nothing |
| **P3** | No entry reports `E4-dead` | any does — you died and that leg is void ([[rurik-harness-walk-numberkey-trap]]) |

**P2 IS THE POSITIVE CONTROL AND THE RUN IS VOID WITHOUT IT.** `readhook`
refuses to score a capture in which nothing ever passed the flag gates, and says
so in those words. That is why step 4 below is not optional padding.

## The run

**One client session, ~6 minutes.** I will say when it is starting; the window is
bounded by the capture timer and by you closing it.

**1 — start the stack and the client** (this is the ordinary loopback launch):

```powershell
python toolkit/harness/session.py --enemy --keep-open --hold 420 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 322,105,0,0"
```

**2 — get into position.** Walk somewhere with open ground around you. **Not
against a wall** — a `W:2` opener against a wall voided a whole run on
2026-08-31. Target the Hatcher.

**3 — attach the instrument** (a second PowerShell window, while the client
sits in the world):

```powershell
python toolkit/clientscan/movehook/attach.py --minutes 4
```

It prints the sites it armed. Injection is instant; there is no window to miss
for these sites, which is why this attaches after you are in position rather
than at launch.

**4 — do these two things, in this order.**

*The treatment, ×5:* target the Hatcher, press slot 1 (322), and **immediately**
try to walk. Whether you move or not is not the measurement — press the key
either way, five times, with a couple of seconds between.

*The control, ×3 — DO NOT SKIP:* stop attacking, let everything settle for about
five seconds, then just walk normally three times. **This is P2. Without it the
capture cannot be scored at all.**

**5 — stop and read:**

```powershell
python toolkit/clientscan/movehook/attach.py --stop
```

```powershell
python toolkit/clientscan/movehook/readhook.py
```

The section headed `ANIMREF-RE  the two WALK GATES` is the answer. Paste it back
and I will score it against the table above.

## What each outcome means, decided in advance

* **E3 on the frozen presses, passed on the idle walks** → §22's mechanism is
  confirmed dynamically. The gate is property 8 and the fix is a server-side
  question about *when* we hold it — which §22.6 showed is subtler than "stop
  re-arming", because retail re-arms constantly.
* **passed-flag-gates on the frozen presses** → the flag gates are not the
  freeze. §21.1's pair is the wrong tree, §22.3 dies, and the next suspect is
  the path query (`E5`–`E7`) or the speed product `m_moveSpeedBase ×
  m_moveSpeedFactor == 0`, which looks successful and does not move.
* **E2 anywhere** → we are setting `m_status` bit 8 somewhere I did not find,
  and §21.4's elimination is wrong.
* **Mixed E3 and passed on the same gesture** → the re-arm cadence is the
  variable, which is exactly §22.3's story and would make the timing the thing
  to chase.

## Provenance and safety

Read-only instrument: a persistent int3 tap that re-emulates the one displaced
instruction and restores every byte on disarm. `ours` build → loopback, cage
verified by `cage.assert_launch_safe`. No live service, no `C:\gw`. The DLL
writes to `vault/research/movecode` (gitignored). `attach.py` refuses a second
attach, because a double load arms each site twice and restores once — a live
`0xCC` left in the client is a crash with our name on it.
