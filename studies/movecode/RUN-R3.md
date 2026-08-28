# MOVECODE-R3 — the click-shape run

**Written 2026-08-28, after R2 ([FINDINGS.md](FINDINGS.md) §1t). One new site, one
question.** Predictions and floors are registered here **before** the run, per the
standard that got this arc its honest results.

---

## 0. READ THIS FIRST — this is NOT another interrupted-walk run

R2's walk was *long routes interrupted with a directional key*, and it was the right
walk: it answered the fence (1,914 reads), the gateless route, gate 3, and exonerated
the teleport a third time. **Do not repeat it.** Those questions are closed.

**What R2 could not answer is the operator's own first claim**, and it failed on `n`:

> *"getting yanked out of my **cornered** click to move"*

§1t.3 scored that **CONTESTED**. The de-circularised instrument gave warped p50 444 u
against control p50 243 u — **overlapping**, with the control's max exceeding 5 of 9
warped rows. The reason is the denominator: **14 clicks in the whole run, 10 warped
against 4 controls.** That is not a comparison, it is an anecdote with arithmetic.

**So R3 is a CLICK-VOLUME run.** The walk is ordinary; what changes is how much of it
is clicking, and that both kinds of click actually occur.

**You do not have to label anything.** The arms are classified **offline**, from the
capture, by whether a straight line from the click's own origin to its destination is
clear on our mesh — `mapfindpath` records both ends (`pt_a`, `pt_b`), and §1t.3 verified
`pt_a` equals the body's position at the click to **0.0 u on 14 of 14**. The classifier
is geometry, not memory.

---

## 1. What is predicted, and what refutes it

### R3-P1 — the two unnamed `SetPosition` callers are named

`setposition` (`0x00602B20`) is hooked as of 2026-08-28. It has **7 direct callers** and
the record carries the return address, so whichever fires names itself.

**Prediction.** At least one `setposition` record carries a return address that is
**not** `0x00602369` (reseed). R2's own census found **2 such writes** in 187 s through
the `agtrack`-return proxy, so the exposure is expected rather than hoped for.

**What it buys.** `0x00604A50` sits in a function called from **AgApi** (`0x005FC110`,
`0x005FC24A`), and `0x00606394` in one called from the **AgTrack** region (`0x006040BA`,
`0x0060413A`). Neither carries a naming assert — only `Array:587` bounds checks — so
**static analysis has not named them and this run is how they get named.** Four further
callers (`0x005FDAE5`, `0x005FDB49`, `0x005FF74B`, `0x006028FF`) have never been observed
at all.

**REFUTED IF** every `setposition` record returns to `0x00602369` — in which case the two
writes R2 counted came through a path this site cannot see, and the site is inert.

### R3-P2 — displacements concentrate on the BLOCKED-line clicks

**The operator's claim, turned into a number with a control arm.**

Classify every click by whether `pathmap.clip(pt_a → pt_b)` reaches the destination:
**CLEAR** (a straight line suffices — an open-ground click) or **BLOCKED** (the route
must bend — a cornered click).

**Prediction.** Displacements fall disproportionately on **BLOCKED** clicks. Stated so it
can fail: the displacement rate per BLOCKED click **exceeds** the rate per CLEAR click,
with a Fisher exact **p ≤ 0.05** on the 2×2.

**REFUTED IF** the two rates are within noise, **or** if CLEAR clicks warp at least as
often. Either would mean the corner is not the trigger, and §1t.3's CONTESTED becomes a
NOT FOUND — a real result that closes a line of enquiry rather than opening one.

**A third outcome that is NOT a refutation:** the floors below are missed. Then the run
measures nothing and must be re-run, not concluded from.

### R3-P3 — the landing is captured at the write, not inferred

`deref_arg_a = 1` captures the point `SetPosition` is asked to install.

**Prediction.** For every displacement, the captured `pt_a` equals the position seen in
the next record carrying that object, to **< 1 u**.

**Why it matters.** §1t.2 had to reconstruct the landing from the following record, and
§1t.3's operand substitution happened inside exactly that reconstruction. If this holds,
the landing stops being an inference for good.

**REFUTED IF** they disagree — which would mean the branch at `0x00602B57` sends the
write somewhere other than the argument. The row's `limits` field already warns of it.

---

## 2. THE EXPOSURE FLOORS, pre-registered

**A run below these floors measures nothing and must be re-run, not reported through.**
That is the mistake K1 arm A made — 2 fires in 1,773 verdicts, reported anyway.

| quantity | floor | R2 got |
|---|---|---|
| clicks (`chcli_point`) | **≥ 30** | 14 |
| `mapfindpath` queries from the planner (`0x0081AF56`) | **≥ 25** | 14 |
| clicks classified **CLEAR** (the control arm) | **≥ 10** | ~4 |
| clicks classified **BLOCKED** (the treatment arm) | **≥ 10** | ~10 |
| displacements | **≥ 8** | 11 |
| `setposition` records | **≥ 10** | n/a (new site) |

**The CLEAR floor is the one that will be missed if the walk is careless**, because a
player naturally clicks *toward* things and things are what block lines. Deliberately
spend a third of the run clicking across open ground with a path you can already see.
**A control arm that never happens wastes the whole run** — `zero exposure is not a
null`, and this arc has paid that twice.

---

## 3. Preconditions

Already true as of 2026-08-28, and cheap to confirm:

```bash
python toolkit/clientscan/movehook/test_movehook.py
```

Expect **120** (floor 73). It was 113 before the `setposition` row.

```bash
python toolkit/clientscan/movehook/gensites.py --exe vault/client/2026-07-29_221c13772c7a/Gw.exe
```

Expect **14 hook site(s), 12 agent offset(s)**, every row `OK`, including
`setposition 0x00602B20`.

**The DLL is already rebuilt** against the 14-site table and is newer than `sites.h`, so
`attach.py` will not refuse. Only rebuild if you touch the rows — and **close the client
first**, because the hook does not unload.

---

## 4. THE RUN

Announce it. The client fights for input focus and the machine is shared.

**Shell 1 — the stack and the client:**

```bash
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --keep-open --hold 900 --game-args="--click-echo --map 280"
```

`--exe` is not optional: `session.py` defaults to the newest build and every movehook
address is **38797**. The hold ends it after 15 minutes.

**Shell 2 — once the character is in the world and standing still:**

```bash
python toolkit/clientscan/movehook/attach.py --minutes 8 --out vault/research/movecode/r3
```

Not before. The DLL's timer starts at injection, so attaching at launch spends the
capture on the login screen.

### The walk

**Click a lot. Roughly half cornered, half open.** Aim for 30+ clicks in 8 minutes —
about one every 15 seconds, which is more clicking than feels natural. That is the point.

1. **CORNERED clicks (~half).** Click a destination whose straight line is obstructed:
   round a building, past a rock formation, through a doorway, across a railing. Let each
   run far enough to see whether it warps.
2. **OPEN clicks (~half). THIS IS THE CONTROL AND IT IS THE ONE AT RISK.** Click a
   destination with a clear straight path. Long is fine — length is not what is being
   tested, obstruction is. **Without these the run cannot be scored.**
3. **Let each click finish**, or nearly. A click abandoned two steps in produces a query
   and no exposure.
4. **Keep some keyboard walking**, but it is no longer the point — a few interrupted
   walks keep the reseed path alive.
5. **Say what warped, and roughly when.** The operator's report has disagreed with a
   metric twice in this arc and been right both times (§1n.2, §1l.2).
6. **Watch for clipping** — walking through props, or on ground the body should not
   reach. Still no instrument but your eyes, and *"I watched and saw none"* is a result.

---

## 5. Reading it back

```bash
python toolkit/clientscan/movehook/attach.py --stop
```

```bash
python toolkit/clientscan/movehook/readhook.py --bin vault/research/movecode/r3/movehook.bin
```

**Both controls must say FIRED.** Check `setposition` appears in the per-site table with
a non-zero count, and read the **SetPosition CENSUS** line against the **DISPLACEMENTS**
count — if the census is higher, the difference is warps the stamp comparison cannot see
(§1t.4 measured 15 against 11).

```bash
python toolkit/clientscan/movehook/pathdiff.py --map 0x287B3 --bin vault/research/movecode/r3/movehook.bin
```

`--map auto` refuses on these captures (two meshes tie); pass `0x287B3`.

**The CLEAR/BLOCKED classification is not yet a tool.** It is one script over
`mapfindpath`'s `pt_a`/`pt_b` and `pathmap.clip`, written when the capture exists — and if
it earns its keep it belongs in `readhook` beside the census, not in a scratchpad.

---

## 6. If a prediction is refuted

Write it up as refuted. §1q, §1r, and §1t's P2 and P3 are all refutations, and each is
worth more than the confirmation would have been. **P2 refuting is the most informative
single outcome available here**: it would retire the cornered-click hypothesis, which is
currently the last unexplained half of the operator's own description of the defect.
