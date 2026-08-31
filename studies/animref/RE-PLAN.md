# ANIMREF-RE — the movement gate, by reverse engineering rather than guesswork

**Owner's direction, 2026-08-31:** *"let's try to go at this from a true
reverse engineering approach rather than more guesswork."* Written straight
after their verdict on the shipped fix: **"i can do it but it's unreliable
and doesn't feel quite like stock."**

That verdict is the honest state of the arc. Everything R6/R7 shipped is
corpus-derived and correct as far as it goes, and it did not deliver the
thing that was asked for. What follows is the plan that stops proposing
server changes and reads the client instead.

## 0. What we are actually looking for

**One sentence: find the predicate the client tests before it translates the
player's body, and find what our server leaves in the state that predicate
reads.**

## 1. The observation that localises it — do not re-derive this

From the two instrumented runs (FINDINGS §14, captures `20260831T110144`
and `20260831T110743`), in the frozen arm:

* the client **SENT its `0x003D`** at the keydown — so the input path, the
  key delivery, the focus and the wire are all fine;
* the server answered **identically** in the frozen and the moving windows
  (the `0x0025` direction echo, the zero-lead pin, same tags);
* and the body **did not translate** — the client stop-reported its
  *unchanged* coordinates at keyup, server-side drift 767 u.

**Therefore the gate is in the client's LOCAL movement application**, after
input and before position integration. It is not the input path, not the
message, and not something the server failed to answer. That single fact
excludes most of what a fresh session would otherwise re-test.

## 2. What is already decoded (FINDINGS §15) — the starting map

Each animation property enqueues a per-agent animation-state node via
`0x007F2E90(agent, N)` — a linked-list splice at `[agent+0xC4]`, node
`{state N, [agent+0x2c], timestamp}` — plus a global "current local action"
latch at `0x010874AC` (state) / `0x010874B0` (agent), with `0x010874A8`
cleared alongside:

| property | AvChar method | state N | global |
|---|---|---|---|
| 1 melee_finished | `0x007F6BC0` | 0 | AC=0, B0=agent |
| 3 attack_stopped | `0x007F6C00` | 2 | — |
| 4 attack_started | `0x007F6C10` | 3 | cleared |
| 46 attack_skill_finished | `0x007F74F0` | 0x11 | AC=0x11, B0=agent |
| 49 attack_skill_stopped | `0x007F7510` | 0x12 | AC=0x12, B0=agent |
| 50 attack_skill_activated | `0x007F7540` | 0x15 | cleared |

Observed behaviour of OUR client: movable in states 0/2/3, **not** in
0x11/0x15. Retail's client moves in 0x11 (87 of 100 mid-chain corpus moves
carry no property 3). Property 8 is NOT the gate — it is released on
movement in both arms.

Other bytes seen written by the animation dispatcher and unexplained:
`[AvChar+0x1B7]` and `[AvChar+0x1B8]` (written at `0x007F84B3` and
`0x007F8663`/`0x007F866A`), `[+0x158] & 0x20`, `[+0x1BA]`, `[+0x1BB]`
(weapon/animation selectors in `0x007F82C0`). Any of these is a candidate
for what the movement update reads.

## 3. The dig, in order, each step falsifiable

**Step 1 — find the local movement update (static).** The MOVECODE arc has
already decoded much of this client's movement model (sync `+0x60`
moveSpeed, `+0x5C`, the AgTrack history chain,
`studies/movecode/FINDINGS.md`); **start from its addresses rather than
from scratch** — that arc's `0x005FD9D0`/`0x00602990` and the grant-bake
path are the nearest known ground. Target: the per-frame function that
applies velocity to the local player.
*Refutable:* if the function found never reads any animation-state field,
it is the wrong function.

**Step 2 — enumerate the readers of the state (static).**
`codescan.py --field 0xC4`, `--field 0x1B7`, `--field 0x1B8` and
`--xrefs 0x010874AC` / `0x010874B0`. The gate should appear as a READ of
one of these inside (or one call below) the movement update.
*Positive control first:* the same scan must find the known WRITERS listed
in §2 — if it cannot see those, the scan is mis-scoped and its silence
means nothing (`asserts.py` counts are a floor; a negative needs a positive
control).

**Step 3 — confirm dynamically, frozen vs moving.** This is the step that
settles it, and the tooling exists: `toolkit/clientscan/movehook/` is a
persistent int3 tap on function entries (MOVECODE-B2), `commandertrap.py`
is the Windows-debugger reference to copy, and `keytap.py` shows
cross-process `ReadProcessMemory` with ASLR-correct module bases in pure
`ctypes`. Read the candidate field at the instant of a keydown in both
arms — the frozen arm (attack skill pressed) and the moving arm (auto-attack
or idle).
*Prediction to register BEFORE the run:* the candidate differs between arms
at that instant, and its frozen value is one our server put there.
*Refuted if:* the field reads identically in both arms — then the gate is
elsewhere and step 2's candidate list was wrong.

**Step 4 — derive the server-side condition, then ship it.** Only once step
3 names the field: what must the server send (or stop sending) so the field
holds the movable value at the right instant. Default ON with a revert flag,
one change, and the verdict is the owner's **by feel** — see §4.

## 4. Rules this dig inherits

* **The harness does not get a vote on the quarterstep.** Owner's ruling,
  2026-08-31: it is a feel thing. A scripted plan proves the body travelled
  N units, which is a necessary condition dressed as the finding. Use the
  harness for the A/B scaffold and the wire record; the verdict is the
  owner's.
* **No movement leg at the top of a scripted plan** without checking the
  terrain — a `W:2` opener parked the character against a wall and voided a
  whole run on 2026-08-31.
* **Do not ship on n=1**, and do not ship a wire form retail never sends
  (D20 and R7a are both on the record as what that costs).
* Client work is read-only on the pinned build (38797,
  `vault/client/2026-07-29_221c13772c7a/Gw.exe`); `capstone`/`pefile` are
  permitted in `clientscan/msghandler.py` and `codescan.py` only, and a
  native toolchain is a cost rather than a blocker (`PLAN.md` §7 Q6).

## 5. What is NOT in scope for this dig

R6/R8 are shipped and verified — the attack-skill execution batch, and the
on-body effect visuals (owner confirmed 2026-08-31: *"effects render on the
target now too"*). §17's IAS windup needs a live capture, not this dig.
Nothing here reopens the corpus laws; they are the referent this dig is
trying to satisfy.
