# MOVECODE-B2 — the runsheet for the first movehook capture

**Status: everything below is prepared and nothing is armed.** The DLL builds, its
test is green end to end against a throwaway 32-bit process, and the addresses are
verified against the pinned client. What has not happened is the run, because it
needs the owner's go-ahead and a player walking around.

**Prediction first, per the standard that got the router arc four honest results.**
The prediction is MOVECODE-P1, registered in
[FINDINGS.md](FINDINGS.md) §3 *before* this instrument existed. Do not read the
capture until §1 below is re-read.

---

## 1. What is predicted, and what refutes it

**MOVECODE-P1a.** Some server-granted destinations will be re-baked with
`isWaypoint = 1` before their arrival tick — i.e. the client re-plans our grants.
Concretely: `readhook.py` will report a **non-zero glide fraction**, and the return
addresses of the gliding bakes will be `0x00600B0F` (obstacle avoidance) and/or
`0x0060193B` (the priority-queue path solve).

**MOVECODE-P1b.** Every teleport will be preceded by a bit-18-CLEAR agent, and the
body-to-target distance at the teleport will be **small when the client's own last leg
agreed with our copy and large exactly when it did not**.

**What refutes P1a — and this is a real possible outcome, not a formality.** If the
glide fraction is **zero** — every bake in the session carrying `isWaypoint = 0` — then
the client does *not* re-plan server-granted destinations, FINDINGS §1.6's reframing is
wrong, and `PLAN.md` §2.1's original reading ("every `0x0029` we send arms a scheduled
hard arrival") stands unmodified. B1 established that the setter *calls* both re-bakers
on straight-line code and that each is guarded by an ordinary point inequality; it did
**not** establish that either is ever reached under the setter's arguments. That is
precisely what this run decides.

**What refutes P1b.** A teleport whose agent had bit 18 **SET** at entry. FINDINGS §1.3
says the only reader of the bit routes SET to a re-bake and CLEAR to the teleport, so a
SET-at-teleport record is a refutation of the decoded branch, not noise. `readhook.py`
prints that case in those words rather than burying it.

**A third outcome that is not a refutation and must not be read as one.** Zero bakes at
all, with control A green, means the client baked no movement while the hook was armed —
a fact about the run, not about the client. Re-run; do not conclude.

---

## 2. Preconditions

1. **The owner's go-ahead.** The client is not launched without it, even on loopback.
2. **The harness is free.** Other sessions share it. Ask before taking it.
3. **The launch binding, from the bytes and never from a filename:**
   ```bash
   python toolkit/clientpatch/dhbuild.py
   ```
   Hook development uses the **`ours`-DH loopback build under `vault/run/`**. Never
   `run-live/`, never pointed at ArenaNet. `sorted(exes)[-1]` has picked the wrong
   build three times in this repo's history.
4. **The addresses still match the build:**
   ```bash
   python toolkit/clientscan/movehook/gensites.py --check
   ```
   Must print `OK` for all four sites. Every address is build 38797; a client update
   invalidates all of them and this refuses rather than arming a breakpoint
   mid-instruction.
5. **The DLL is built and current:**
   ```bash
   cd toolkit/clientscan/movehook && powershell -ExecutionPolicy Bypass -File ./build.ps1 movehook.c
   ```
   Expect `machine=014C (x86)`. `Gw.exe` is 32-bit; a 64-bit DLL cannot be injected.
6. **The test is green:**
   ```bash
   python toolkit/clientscan/movehook/test_movehook.py
   ```
   36 checks on a machine with the client, a compiler and `SysWOW64\cmd.exe`.

---

## 3. DO NOT use `autoinject.py` for this hook

`autoinject.py` exists because **terrain builds once at map load** — a ~7 second window,
after which a correct breakpoint sees `hits 0`
([[project-rurik-trnhook-injection-window]]). **Movement is not like that.** The bake,
the setter and the teleport fire continuously for as long as anything moves, so there is
no window to miss.

Worse, autoinject would *hurt*: the DLL's run timer starts at injection, so arming at
launch spends the first minutes of a ten-minute capture sitting on the login screen.

**Inject mid-session instead, once the character is in the world and standing where the
run is meant to start.**

---

## 4. The run

Two shells. Announce the launch to the owner first — the client fights for input focus
and the machine is shared.

**Shell 1 — the stack and the client.** `--hold` bounds it; `--keep-open` alone parks a
window on the owner's screen forever.

```bash
python toolkit/harness/session.py --keep-open --hold 900
```

**Shell 2 — attach once the character is in the world and standing where the run
starts.** One command; it finds the pid, writes the config, and injects.

```bash
python toolkit/clientscan/movehook/attach.py --minutes 10
```

Expect `LoadLibraryA returned 0x…  (loaded)` and `armed for 10 minute(s)`. It
**refuses a second attach** into the same client: the DLL patches bytes and restores
them on disarm, so a double load arms each site twice and restores once, leaving a live
`0xCC` in the client's code. If it refuses, restart the client rather than forcing.

The config goes in `movehook.cfg` beside the DLL and **not** in the environment —
`GetEnvironmentVariableA` inside an injected DLL reads the *client's* environment,
inherited from whatever launched `Gw.exe`, so an exported variable would be silently
ignored while you believed the run was bounded. `test_movehook.py` §8 pins that
precedence by setting the two to different values and checking which the DLL honoured.

**Then play.** The operator walks — this is world-anchored input and stays with the
owner. Do a mix of:

- click-to-move across open ground (the common case),
- click-to-move where something is in the way (a wall corner, an NPC) — **this is the
  case P1a is about**, because it is what should provoke the avoidance re-bake,
- keyboard walking, to get grants that the player then declines to follow,
- standing still for a stretch, so the capture has a baseline.

The DLL disarms itself and writes when its timer elapses or the ring fills.

---

## 5. Reading it

```bash
python toolkit/clientscan/movehook/readhook.py
```

**Read the control lines first, before any number below them.** `readhook.py` refuses to
score a capture whose control A did not fire, and says so — but a `control B: DID NOT
FIRE` is *not* a refusal and still matters: it means patch-and-delivery on real client
code is unproven, so a zero in any row is not evidence of absence.

Then, in order:

1. **`hits` per site.** Zero across all four with control A green means the client did
   not move. Re-run.
2. **`RING FULL`** in `movehook.txt` means the run was truncated and the tail is
   missing, so any rate is biased toward what happened early. Re-run shorter or raise
   `NCAP`.
3. **P1a's glide fraction and its return addresses.** Score against §1.
4. **Any return address that is none of the five known callers.** That is a caller
   `--xrefs` could not see — MOVECODE-Q4 answering itself, and a finding in its own
   right. The known set:
   `0x00602AD8` setter(0), `0x006002BA` tick(0), `0x00600B0F` avoid(1),
   `0x0060193B` solve(1), `0x005FEC83` follower(forwards its own arg2).
5. **P1b's teleport distances.**

Copy the capture out of `vault/research/movecode/` before the next run — the DLL
overwrites both files.

---

## 6. Known failure modes

| Symptom | What it means |
|---|---|
| `control A: DID NOT FIRE` | the vectored handler never ran. Nothing else in the file means anything. |
| `control B: COULD NOT ARM` | no thread was sampled executing in `.text`. Honest, not a failure — but B proved nothing this run. |
| `hits 0` on every site, control A green | the client moved nothing while armed, **or** the addresses are stale. Re-run `gensites.py --check` first. |
| `LoadLibraryA returned 0x00000000` | injection failed. The client may be elevated — run the injector elevated too. |
| the client dies on injection | stop, and do not re-run. Capture the crash and treat it as a defect in `movehook.c`, not a flaky run. |
| no output file at all | the run never completed its timer. The DLL writes only on disarm. |
