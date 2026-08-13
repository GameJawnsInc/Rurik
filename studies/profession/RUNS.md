# Runs: what the client actually did

Fifth document in the profession arc, and **the first one made of observations rather than
readings.** [`FINDINGS.md`](FINDINGS.md) measured the limits, [`WORKAROUNDS.md`](WORKAROUNDS.md)
found the routes, [`MODDABLE.md`](MODDABLE.md) designed for arbitrary N and
[`ATTRIBUTES.md`](ATTRIBUTES.md) costed the hardest dimension. Between them: ~50 agents, four
documents, and **not one packet sent**. This is the packet.

Four sessions, 2026-08-12, loopback only, ours-DH build, verified cage, synthetic
credential. Runs 1 and 2 are §2–§3; the two `profession_skillbar` sessions are §8, and
§8 corrects §6's first row.

## Labels

Same vocabulary as the rest of the arc. **OBSERVED** carries its full weight here for the
first time: watched happening in a running client, by this repo, on a dated run.

---

## 1. The result

> **Profession 12 — an id the client does not ship — rides `0x00A6` and the client keeps
> playing. It dies only when a profession-keyed UI surface reads it, and the first such
> surface is the SKILLS PANEL.** Same key, same panel, one byte different: it opens at
> profession 3 and asserts at profession 12.
>
> The assert is **`*skill` at `ChCliSkill.cpp:1022`** — a **NULL POINTER**, not a bound
> check. That distinction is the most consequential thing in this document (§4).

**MODDABLE.md's central premise survived contact.** Its claim was that 256 professions are
reachable because the appearance nibble and the live profession byte are *different storage*,
so the byte carriers accept an id the nibble could not hold. The setter at `0x007F7330` has no
comparison instruction in its whole body, and it behaved exactly as that predicted.

---

## 2. Run 1 — `profession_custom`

Capture: `vault/captures/gamesrv/authsrv-20260812T200932-c1.jsonl` ·
harness report `vault/captures/harness/20260812T200921/`

| t | event |
|---|---|
| +3.64 s | `0x00B7` from the spawn burst (the server's own, profession 1) |
| +5.65 s | **step 1 — control, profession 3** |
| +15.66 s | **step 2 — profession 12** |
| +16→20.78 s | client sends `MOVE_SET_HEADING` ×7, `MOVE_CANCEL_REPORT_POSITION`; server answers `AGENT_MOVE_DIRECTION` |
| +20.78 s | last c2s from the client |
| +25.63 s | connection gone; steps 3 and 4 could not send |

**The headline is the 5.1 seconds.** The client received an out-of-band profession and went on
talking — its own c2s traffic, which is the proof-of-life standard the smsgsweep pass had to
learn the hard way (a socket says nothing; an assert leaves it open). **The packet is not what
kills it.**

**What run 1 could not do was attribute the death.** The operator opened the skills menu and
the session ended, but nobody had opened that panel while the profession was legal — so "the
skills panel reads a profession-keyed table out of bounds" and "that panel was never going to
open in our thin loopback world" both fit. Our world has no party, no roster and no unlocks;
a panel refusing to open proves nothing on its own. n=1, no control.

*(The operator also pressed `P` for the party window and it did not open. Unattributed and
probably mundane — the server sends no party state at all. Recorded, not relied on.)*

---

## 3. Run 2 — `profession_ab`, the missing control

Same operator action twice, either side of one changed byte: open the skills panel at
profession 3, close it, send profession 12, open the **same** panel again.

- **Arm A, profession 3 — the panel OPENS.** Normal.
- **Arm B, profession 12 — the client asserts.**

**That is clean attribution.** One byte differs between the arms; everything else — the key,
the panel, the session, the map, the operator — is held constant.

### What the crash log gives, and it is more than the attribution

**OBSERVED**, build 38797, image ASLR'd to base `0x00F20000` (delta `0xB20000`):

**The assert:** `*skill`, `ChCliSkill.cpp:1022`. A null-pointer assertion on a skill.

**The faulting instruction resolves into the routine this arc has been reading statically for
three passes.** `eip = 0x00FA7BDB` → static **`0x00487BDB`**, which is the
`pop dword ptr [ebp-0x10]` of the `call $+5` stack-snapshot idiom inside `0x00487BC0`. The
log's own Code bytes (`8f45f054 8f45f455 8f45f88b 45088945`) match this repo's disassembly of
that address byte for byte. **The assert routine pass 1 identified is the one that ran.**

**And it confirms the calling convention R1's patch depends on.** The trace's first argument
is `0x000003FE` = **1022** — the line number in `ChCliSkill.cpp`. So `[ebp+8]` is the line,
one stack argument, with the expression and file pointers arriving in `edx`/`ecx` (`ebx`
points at the file string). **That is exactly the ABI measured statically, and it is why
`ret 4` is correct for all 20,131 call sites.** R1's five-byte patch is now corroborated by a
live crash rather than by reading alone.

### The call chain, resolved

Every frame rebased by `0xB20000` and named with `asserts.py --at`:

| Static VA | Module | Role |
|---|---|---|
| `0x00487BDB` | the shared assert routine | `*skill` |
| `0x008217EB` | `ChCliSkill.cpp` | the lookup that returned null |
| `0x00816E6F` | `ChCliApi.cpp` | character/skill API |
| `0x0050277E`, `0x0050106F` | **`GmDeckBuilder.cpp`** | **the skills-and-attributes panel** |
| `0x0064CA24` | `FrMsg.cpp` | UI frame messaging |
| `0x00633C7C`, `0x00630DB4` | `FrApi.cpp` | UI frame API |
| `0x004E1F7D`, `0x004E2C08` | `GmView.cpp` | the view layer |

`GmDeckBuilder` is where pass 1 already located the client's own
`agentPrimaryProf != agentSecondaryProf` invariant. It is now in the crash path, from the
other direction.

---

## 4. The mechanism is a null lookup, not a bound check — and that changes the plan

Four documents modelled the failure as **29 bound checks, each of which ends the session.**
What actually fired is a **null-pointer assert on a skill**, several frames below the panel.

The difference matters for what a fix looks like:

- A **bound check** says *"12 is not a valid profession"* — the answer is to widen the bound,
  which is `ATTRIBUTES.md`-style patching across many sites.
- A **null skill pointer** says *"nothing is registered for profession 12"* — the answer may
  be to **populate** a per-profession skill list rather than to patch anything. The client did
  not object to the id; it objected to finding nothing behind it.

**This is a materially more encouraging mechanism**, and it was not predicted by any of the
four prior documents. It is also a lead, not a conclusion: one assert on one panel. Whether
the other twelve profession-keyed surfaces fail the same way is **UNMEASURED**.

**What is NOT established:** that the 29 bound checks are irrelevant. This run never reached
one — the skills panel died first, at a different kind of check. The ordering the probe set
out to get is now: **the skills panel is first.** What is second is unknown.

---

## 5. Corrections to the arc

**5.1 — The predicted failure signature was wrong in run 1, and right in run 2.** The arc's
model is that an assert leaves the process *alive* behind a modal dialog with its socket
*open*. Run 1 showed the opposite: no dialog within 12 s, client exited code 1, final
screenshot a "Connecting" screen. Run 2 produced a real assert with a real dialog. The most
likely reading is that run 1's dialog was dismissed inside the harness's 12-second window,
but that is **INFERRED** — run 1's signature is recorded as it was seen, not reconciled.

**5.2 — `CHAR_PROFESSIONS_MAX = 6` was a live bug, not only a blocker.** Fixed as L0 before
these runs. It refused professions 7–10 — which ship, and which reach
`agent_set_profession` straight from content via `authsrv.py`'s NPC loop.

**5.3 — `probes.check_encodable()` was never run by the suite.** The guard against wasting a
client run was itself unguarded, reachable only from `probes.py`'s `__main__`. Now covered.

**5.4 — the dump file is still not findable.** The crash log names `DumpFile: Crash.dmp`;
no such file exists in the run directory. `CLAUDE.md`'s standing note survives — the log
*names* a dump it does not appear to write.

**5.5 — ASLR is on, delta `0xB20000` this run.** Any runtime work (`WORKAROUNDS.md` R3) must
rebase; `keytap.py` already resolves module bases correctly and is the precedent.

---

## 6. Open, and the next rung

| Question | Status | Next |
|---|---|---|
| Does populating a skill list for profession 12 clear the assert? | **STILL UNANSWERED — the probe ran and its CONTROL arm reddened (§8)** | The re-send instrument is poisoned; spawn-time delivery or R1 (§8) |
| Which surface fails *second*? | **UNMEASURED** — the skills panel died first | Neuter the assert (R1, 5 bytes) and re-run: fall-through turns one answer per run into many |
| Do the other twelve profession-keyed surfaces fail by null or by bound? | **UNMEASURED** | Same |
| Is profession 11 (the sentinel) different from 12? | **UNMEASURED** | `profession_sentinel`, already registered |
| Does 255 mask to 15 rather than failing? | **UNMEASURED** — the silent-failure check | `profession_max`, already registered |
| Did run 1's control (profession 3) render visibly? | **NOT CONFIRMED** by the operator | Any future run should confirm arm A explicitly |

**The cheapest next rung is R1**, and this run is what makes it worth doing: with the assert
neutered, a session survives its first out-of-band read and keeps going, so one client run
yields the *ordering* of many surfaces instead of the first one only. Five bytes, one site,
and the ABI it depends on is now confirmed by a live crash.

---

## 7. Reproduce

```
python toolkit/authsrv/authsrv.py --list-probes    # profession_custom | _ab | _skillbar | _spawn | _sentinel | _max
python toolkit/harness/session.py --keep-open --shots 10 \
    --game-args '--probe profession_ab'
```

Loopback only. The cage is enforced from the bytes (`cage.assert_launch_safe`), the build is
selected by whose DH it carries, and the account is synthetic. Arm A must open the panel; if
it does not, the run has already answered a different question and arm B means nothing.

To rebase a crash address to a static VA: `static = runtime − (BaseAddr − 0x00400000)`.

---

## 8. Run 3 — `profession_skillbar` (2026-08-12): the control arm reddened

Two sessions the same evening, both loopback, driving the probe built for §6's first
row: run 2's A/B plus the same eight-skill bar re-delivered mid-session in BOTH arms, so
the arms still differ by one byte.

**3a — unattended.** Harness `20260812T213205`, capture
`authsrv-20260812T213215-c1.jsonl`. The harness echoed the gamesrv's stdout only for
`--labelrun`, so the probe's prompts went to `gamesrv.log` alone and the operator sat at
a silent terminal; all seven steps fired with nobody at the keys (fixed the same
evening, `test_harness` §8). The burned run is still evidence: **the client outlived
every packet** — steps ended at +64.9 s, last c2s at +227.7 s — so the mid-session
re-send is not lethal at profession 3 (step 2) or at 12 (step 5), and profession 12 →
recovery, unopened, replicates run 1's headline.

**3b — operated.** Harness `20260812T213758`, capture
`authsrv-20260812T213806-c1.jsonl`.

| t | event |
|---|---|
| +4.73 s | step 1 — profession 3, the control |
| +8.74 s | step 2 — bar re-send, still profession 3 |
| +12.24 s | **last c2s from the client** |
| +12.75 s | step 3 — "NOW open the skills menu (K)"; the operator pressed K (reported; the c2s window brackets it) |
| ~+15 s | the assert — dialog `When:` 21:38:21 against capture start 21:38:06 |
| +32.8→64.8 s | steps 4–7 fired into a dead client; 10 pings unanswered |

**The client died in ARM A, at profession 3 — a shipping value — before the experiment
ever ran.** The dialog, captured by the harness on the Ctrl-C teardown path (the
capture-on-EVERY-run change earned its keep), is the SAME assert as run 2: `*skill`,
`ChCliSkill.cpp(1022)`, base `0x00F20000` again.

### What this measures

One variable separates 3b's arm A from run 2's arm A, which opened: **the mid-session
re-send.** The worlds are otherwise identical — same unlocks-all burst, same bar,
checked line-for-line in both gamesrv logs. So, n=1 with run 2's arm A as its control:

> **OBSERVED: a mid-session `SKILLBAR_UPDATE` followed by opening the skills panel
> asserts the client at a LEGAL profession.** Same null, no out-of-band byte anywhere
> in the session.

Three consequences:

- **The probe cannot answer its question with this instrument.** The re-send poisons
  the panel on its own, so §6 row 1 — population vs bounds — is **UNANSWERED**, not
  answered in the negative. Do not re-run `profession_skillbar` expecting its stated
  fork; its arm-A control did exactly what a control is for.
- **Run 2's attribution stands.** It contained no re-send in either arm; its one-byte
  difference is untouched by this.
- **INFERRED, leaning toward the population theory rather than against it:** the same
  null is now reachable with the profession held legal, by an action that plausibly
  rebuilds skill state. A profession bound check cannot fire at 3; whatever `*skill`
  dereferences was left null by the REBUILD. Consistent with §4's "nothing registered
  behind the id" — but it is one crash, and the client's re-send handler is unread.

### A frame for the null, from the game's own mechanics

**WIKI (GWW, "Skills and Attributes Panel" and "Profession changer"):** the panel
carries a drop-down for changing SECONDARY profession — roleplaying characters list
the secondaries unlocked on that character, PvP characters any profession unlocked on
the account, and a character who cannot change secondary cannot select the box. So the
panel **enumerates professions and builds per-profession state**, and a per-profession
walk that dereferences skill data is a plausible frame for both crashes: profession 12
in the walk (run 2), and a walk re-entered after a skill-state rebuild (run 3b).
Operator's suggestion, 2026-08-12. The wiki is strong for this player-visible
mechanic and weak for internals — the frame is **INFERRED**; the handler is unread.

### The routes from here

- **Spawn-time delivery — BUILT 2026-08-12.** `authsrv.py --spawn-profession N`
  rebinds what the burst's `0x00B7` carries, built through
  `agents.agent_set_profession` (custom derived from the value, 0 refused at startup,
  out-of-band announced loudly); the appearance nibble deliberately stays put —
  different storage, bound-checked `< 0xB` at load, and the mismatch is run 2's
  measured-survivable condition. Bar, unlocks and attributes all arrive AFTER it in
  the same burst, nothing is re-sent, and K is the session's first provocation.
  Paired observation-only probe: `profession_spawn` (warns if run without the flag).
  TWO sessions, control first — spawn-time delivery of a non-default profession is
  itself new:

  ```
  python toolkit/harness/session.py --keep-open --shots 10 \
      --game-args '--probe profession_spawn --spawn-profession 3'
  python toolkit/harness/session.py --keep-open --shots 10 \
      --game-args '--probe profession_spawn --spawn-profession 12'
  ```
- **R1, the five-byte neuter — now MORE attractive.** Two distinct provocations reach
  the same noreturn assert; with it neutered, one run yields the ordering for both.
