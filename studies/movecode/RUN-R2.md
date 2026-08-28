# MOVECODE-R2 — the runsheet for the gate/fence run

**Built 2026-08-28. UNRUN.** One owner-driven loopback run answers four questions
that have each been open across several passes. The instrument changed since the
last run — **two new sites, two new agent offsets, and record v6** — so this
needs a DLL rebuild, which the last three arms did not.

Scored against `FINDINGS.md` §1s.9's ask. Predictions are §1 and were written
**before** the instrument existed, per the standard that got this arc its honest
results.

---

## 0. READ THIS FIRST — §1s.9 named five addresses and four are not sites

`FINDINGS.md` §1s.9 asked for four hook sites and listed five addresses. **Four
of the five are not function entries**, re-read from the pinned 38797 image:

| §1s.9 address | first byte | what it is | verdict |
|---|---|---|---|
| `0x00606009` | `0f` | the AgTrack fence branch, a `je` | **REFUSED** |
| `0x00605634` | `83` | the facing-9 compare, a `cmp` | **REFUSED** |
| `0x00605683` | `5e` | the facing-9 return-1 tail, a `pop esi` | **REFUSED** |
| `0x005FCAA0` | `e8` | the ResyncAllAsync **thunk**, a `call` | **REFUSED** |
| `0x005FEF70` | `55` | gate 3 | OK |

`gensites.py` refuses any row whose first byte is not `0x55`, because the handler
re-emulates exactly one instruction shape (`PLAN.md` §7 Q12(d)). **That ruling is
a constraint on the handler, not a typo in the row** — `test_movehook.py` §14 now
proves the refusal fires on all four of these real addresses, and fires *again*
when the row's `first_byte` is "fixed" to match the byte actually there.

**What replaced them is not a relaxed rule.** Three of the four wanted a VALUE
the existing entry hooks already reach:

* **the facing-9 early-out** — both its operands sit on `snaptest`'s **arg2**,
  the agent that row already dereferences, and one of them
  (`m_timeStopMovement`) was already captured. **One new offset finished it.**
* **the AgTrack fence** — the operand of `agtrack`'s own branch, computable at
  its entry from `ecx` and arg1.
* **ResyncAllAsync** — `0x00605E40`, the body the thunk jumps to.

**So this run arms 2 new sites, not 4.** NSITES 11 → 13.

---

## 1. What is predicted, and what refutes it

### R2-P1 — the fence is read, not sampled

**Prediction.** `agtrack` records will carry `have_fence = 1` on the large
majority of hits, and the fence will be observed **both open and shut** within
one run.

**Refuted by** `have_fence = 0` on most hits — the deref failed and the run
measures nothing — **or** by the fence never being observed shut, which would
mean §1s.8 item 1's whole contrast was an artifact of `movetap`'s sampler and
there is no fence-shut state to attribute anything to.

**Why it matters.** §1s.8 item 1 KILLED the previous "suppression buys ~3×"
finding: the classifier was `movetap` sampling fence *state* at 11.4 Hz against a
median shut run of 13 samples, and `agtrack` **zeroes the whole roster's
`clientControlled` on snap**, so "shut" was partly the post-snap state. Reading
the operand at the decision is the only thing that separates them.

### R2-P2 — the two routes to the fence count agree

**Prediction.** Two independent constructions give the same fence-shut count:

1. **direct** — `agtrack` hits with `have_fence = 1 and fence == 0`;
2. **derived** — `agtrack` hits whose agent has `src_world != 1` and which are
   **not** followed by a `snaptest` record.

The flow is `fence` → `world == 1 diverts` → `snaptest`, so with the world field
now captured every invocation partitions into diverted / fence-shut / tested.

**Refuted by** the two disagreeing by more than the pairing tolerance. That is a
real possible outcome and it is informative either way: a disagreement means
either the fence deref is reading the wrong record, or `snaptest` is reachable by
a path the disassembly does not show.

### R2-P3 — the facing-9 early-out is now evaluable, and fires

**Prediction.** Some `snaptest` records will carry `src_stop != 0` **and**
`src_facing == 9`, which is a NO-SNAP returned *before any gate runs*
(`0x00605634` → `0x00605641` → `0x00605683 mov eax, 1`).

**Refuted by** zero such records, which would make `facing == 9` a state this
client does not enter under loopback play, and would retire the lead.

**Not a refutation:** the early-out firing but never on a record that would
otherwise have snapped. That is worth its own row.

### R2-P4 — `resync` (`ResyncAllAsync`) fires, and the question is whether it fires COLD

**Prediction.** `resync` will appear, and its reseeds will be the ones returning
to `0x00605EF6`.

**THE ACTUAL QUESTION, and it is the residual risk to "the nine candidates were
aimed at the right gate":** §1s.1 found that all 21 gateless firings in the
corpus followed closely on a *gated* snap that had just glued the two copies, so
**that corpus cannot see the route fire cold.** This site is the only instrument
that can.

**The interesting outcome is a `resync` with a LARGE separation between the two
copies at the moment it fires.** If that happens, a route with no gates at all is
moving the player, and no separation-managing policy can reach it.

**Refuted by** `resync` firing only within a short window of a gated snap, every
time — which leaves §1s.1's no-op reading intact.

### R2-P5 — gate 3 discriminates the undiscriminated snaps

**Prediction.** `stepclear` hits **filtered on `retaddr == 0x0060581E`** will
appear on some snaps, and their presence discriminates gate 2 from gate 3 on the
3 snaps §1s.3 leaves undiscriminated.

**THE FILTER IS NOT OPTIONAL.** `0x005FEF70` has **two** direct callers —
`0x00605819` (gate 3, inside `snaptest`) and `0x006007A9` (inside the
obstacle-sidestep `0x00600500`). A draft called the second a phantom; it is not.
An unfiltered hit count is not a gate-3 count.

**Ring-fill caveat:** `main:3333` says the avoidance retry path retries up to 6
times per collision event, so `stepclear` may fire **far** more often than gate 3
does. Watch `stored` against `NCAP = 32768`; a full ring is a truncated run.

---

## 2. THE EXPOSURE FLOORS, pre-registered

An arm that does not meet its floor **measures nothing and must be re-run, not
concluded from.** This is the mistake K1 arm A made (2 fires in 1,773 verdicts)
and that §1l reported through anyway.

| quantity | floor | why |
|---|---|---|
| `agtrack` hits with `have_fence = 1` | **≥ 50** | below this the fence deref is not established |
| `agtrack` hits with `fence == 0` | **≥ 3** | zero means no fence-shut state to attribute |
| `snaptest` hits | **≥ 20** | §1s.3 scored 28 across ten captures |
| `resync` hits | **≥ 1** | it fired in 5 of 7 snap-capable captures |
| `stepclear` hits with `retaddr == 0x0060581E` | **≥ 1** | zero leaves gate 3 unobserved, as it has been all arc |

**A floor of 0 met is still 0.** If `resync` and `stepclear` both come back
empty, the run is a NULL on P4/P5 and says so; it does not become a null on P1–P3.

---

## 3. Preconditions

```bash
python toolkit/clientscan/movehook/test_movehook.py
```

Expect **108** (62 on a bare machine). **This is a new number** — it was 81 before
the v6 fields and §14 landed.

```bash
python toolkit/test_content.py
```

Expect **45**.

```bash
python toolkit/clientscan/movehook/gensites.py --exe vault/client/2026-07-29_221c13772c7a/Gw.exe
```

Expect **13 hook site(s), 12 agent offset(s)** and every row `OK`.

### THE DLL MUST BE REBUILT — the last three arms did not need this

Record v6 and two new sites mean the shipped `movehook.dll` is stale. **Close the
client first** — the hook DLL does not unload, and `LNK1104` leaves the old site
set on disk, which would arm 11 sites and write a v5 record while everything
downstream expects 13 and v6.

```bash
powershell -ExecutionPolicy Bypass -File toolkit/clientscan/movehook/build.ps1 movehook.c
```

Expect `machine=014C (x86)`.

---

## 4. THE RUN

**Announce the launch.** The client fights for input focus and the machine is
shared.

**Shell 1 — the whole stack AND the client, one command.** `session.py` brings up
both servers itself, so there is no separate `authsrv.py` shell; server flags ride
on `--game-args`. `--click-echo` is the best measured configuration and is what
this run should carry, because the question is about the CLIENT's reconcile
machinery and the server should be in its best-known state rather than its
default one.

`--exe` is not optional: `session.py` defaults to the **newest** build and every
movehook address is **38797**. `--hold` bounds the window; without it the client
parks on the owner's screen indefinitely.

```bash
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --keep-open --hold 600 --game-args="--click-echo --map 280"
```

**Shell 2 — attach the hook ONCE THE CHARACTER IS IN THE WORLD AND IN POSITION.**

**Do NOT use `autoinject.py` here.** That is the obvious tool and it is the wrong
one — `attach.py`'s own docstring says so in terms. `autoinject` exists for
*terrain*, which builds once at map load inside a measured ~7 second window.
Movement is the opposite: the bake, the setter and the teleport fire continuously
for as long as anything moves, so there is no window to miss — **and the DLL's run
timer starts at INJECTION**, so arming at launch spends the first minutes of a
bounded capture sitting on the login screen.

```bash
python toolkit/clientscan/movehook/attach.py --minutes 6 --out vault/research/movecode/r2
```

The 6-minute capture sits inside the 10-minute hold with room for login and
positioning at the front.

> ### ⚠ BRIEF THE OPERATOR BEFORE THE WALK — copy this WITH the command
>
> **The walk this run needs is different from the last three.** Those were about
> what the *server* grants. This one is about the *client's* reconcile, so the
> walk should provoke **snaps**, not clicks.
>
> **1. Walk long routes and interrupt them.** Click somewhere far, let the
> character get moving, then press a direction key mid-walk. That is the shape
> that produced snaps in runs 3–5. Repeat it a dozen times or more — the floors
> above want ≥ 20 `snaptest` hits.
>
> **2. Walk into geometry.** Corners, railings, props, doorways. Gate 3 is the
> obstacle/crowding test and **has never been observed in this arc**; walking
> into things is the only way to provoke it.
>
> **3. Stand still sometimes.** The facing-9 early-out needs
> `m_timeStopMovement != 0`, which is a *stopped* agent. A run that never stops
> may never enter the state.
>
> **4. NO-CLIP — still no instrument but your eyes.** Did the character walk
> *through* props, railings, rocks, or along bare ground it should not reach?
> The offline detector built for this on 2026-08-28 **failed its positive
> control** and cannot substitute (§1r.6). This row has now been deferred to
> human attention **four times**; if it is not reported it comes back UNSCORED
> again. **"I watched for it and saw none" is a result, not a blank.**
>
> **5. Say what you saw warp, and roughly when.** The operator's report has
> disagreed with a metric twice in this arc and been right both times.

Stop the capture cleanly when the walk is done:

```bash
python toolkit/clientscan/movehook/attach.py --stop
```

---

## 5. Reading it back

```bash
python toolkit/clientscan/movehook/readhook.py --bin vault/research/movecode/r2/movehook.bin
```

**Both controls must say FIRED.** Control A is the DLL's own `int3`; if it did
not fire the handler was dead and every count is a fact about nothing. A zero
from a dead hook and a zero from a client that never did it are the same zero.

```bash
python toolkit/clientscan/movehook/pathdiff.py --map 0x287B3 --bin vault/research/movecode/r2/movehook.bin
```

**`--map auto` refuses on these captures** (two meshes tie); pass `0x287B3`. The
server log's `map_id 148` is the client's connect parameter, not where the
session ran — the spawn coordinate `(−6036, −2519)` is the tell.

**Two traps that have each cost this arc a published number:**

* **Never filter a trajectory on `id == 1`.** One agent id names two objects and
  they sit hundreds of units apart. Group on the `ecx` address. `readhook` does,
  and raises when an id is ambiguous.
* **`readhook`'s world-copy census does not print the two copies in a stable
  order**, and run 5 prints a *third* entry it flags `NOT AN AGENT`. Key on the
  `WORLD_SYNC` / `other world` label, never on position.

**And one new to this run:** `readhook.py` with no `--bin` reads
`vault/research/movecode/movehook.bin`, which is byte-identical to the K1 arm's
capture. Always pass `--bin`.

---

## 6. If a prediction is refuted

Write it up as a refutation with its number, the way §1q and §1r did. **A refuted
prediction with its measurement attached is worth more than a deleted one**, and
this arc's nine epitaphs in `authsrv.py` are the reason anyone can tell what has
already been tried.

The one thing that would **reprice the arc** is P4 coming back with a `resync`
firing cold at a large separation. That would mean the reconcile has a route with
no gates that no server-side policy can reach — and every candidate measured so
far has been aimed at the gated one.
