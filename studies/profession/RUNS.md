# Runs: what the client actually did

Fifth document in the profession arc, and **the first one made of observations rather than
readings.** [`FINDINGS.md`](FINDINGS.md) measured the limits, [`WORKAROUNDS.md`](WORKAROUNDS.md)
found the routes, [`MODDABLE.md`](MODDABLE.md) designed for arbitrary N and
[`ATTRIBUTES.md`](ATTRIBUTES.md) costed the hardest dimension. Between them: ~50 agents, four
documents, and **not one packet sent**. This is the packet.

> **READ §10 FIRST.** The static dive of 2026-08-12 refutes this document's headline
> (§1), its attribution (§3) and its mechanism (§4). **The crash was our own server
> setting bit 0 of the unlock bitmap**; the client's skills panel enumerates that bitmap
> and asserts on a zero id, and **the walk never reads a profession at all.** §§1–9 are
> kept verbatim, with retraction notes in place, because how seven sessions produced a
> profession explanation for a bug with no profession in it is worth more than a clean
> document.

Seven sessions, 2026-08-12, loopback only, ours-DH build, verified cage, synthetic
credential. Runs 1 and 2 are §2–§3; the two `profession_skillbar` sessions are §8; the
two `profession_spawn` sessions and the two discriminators are §9; `profession_trigger`
is §9's T1. **§10 is the static dive that explains all of them at once.**

## Labels

Same vocabulary as the rest of the arc. **OBSERVED** carries its full weight here for the
first time: watched happening in a running client, by this repo, on a dated run.

---

## 1. The result

> **RETRACTED 2026-08-12 by §10.** Both sentences below are wrong. The panel does not
> "open at 3 and assert at 12" — it asserted at every profession, because **our own
> server set bit 0 of the unlock bitmap** and the panel's skill walk asserts on a zero
> id. And `*skill` is **not a null pointer**: it is a zero VALUE test. The one thing
> that survives is the first clause — profession 12 rides `0x00A6` and the client keeps
> playing. Read §10 first; §§1–9 are kept verbatim as the record of how six sessions
> were spent on a crash with no profession in it.

> ~~**Profession 12 — an id the client does not ship — rides `0x00A6` and the client keeps
> playing. It dies only when a profession-keyed UI surface reads it, and the first such
> surface is the SKILLS PANEL.** Same key, same panel, one byte different: it opens at
> profession 3 and asserts at profession 12.~~
>
> ~~The assert is **`*skill` at `ChCliSkill.cpp:1022`** — a **NULL POINTER**, not a bound
> check. That distinction is the most consequential thing in this document (§4).~~

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

- ~~**Arm A, profession 3 — the panel OPENS.** Normal.~~
- ~~**Arm B, profession 12 — the client asserts.**~~

> **RETRACTED by §10 — and this retraction is the most useful thing in the arc.**
> **Arm A CRASHED.** Measured from this run's own capture
> (`authsrv-20260812T201439-c1.jsonl`) and harness dir: the arm-A K prompt fired at
> t=11.30 s, the client's **last c2s is a ping reply at t=17.81 s**, `ping_summary`
> records **4 missed pings**, `hold002.png` (t≈14 s) shows a live client with no panel
> open, and `hold003.png` (t≈24 s) shows the fatal-error dialog **already on screen**.
> Arm B's one changed byte was not sent until **t=31.30 s** — seven-plus seconds into a
> client that was already dead behind a modal dialog — and its "open the panel AGAIN"
> prompt at t=39.31 s went to a corpse.
>
> So the crash belongs to **arm A, at profession 3**, and the "one byte differs"
> attribution was an artifact of the exact failure `test_smsgsweep.py` already fixed for
> the opcode sweep: **an assert leaves the socket open and the process alive**, so
> anything short of a proof-of-life fence scores a dead client as healthy. The probe
> driver never inherited that fence. §10's fix list carries it.

~~**That is clean attribution.** One byte differs between the arms; everything else — the key,
the panel, the session, the map, the operator — is held constant.~~

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

## 4. ~~The mechanism is a null lookup, not a bound check~~ — REFUTED by §10

> **RETRACTED 2026-08-12.** It is neither. `*skill` at `ChCliSkill.cpp:1022` is a
> **zero-VALUE test** on an enumerated skill id (`test eax,eax` on `(word << 5) + bit`),
> and the id is 0 because **our own unlock bitmap set bit 0**. Nothing is null, nothing
> is out of bounds, and no profession is involved. Everything below reasons from the
> word "null" and is wrong in the same direction — the section is kept because the
> *shape* of the error matters: a plausible mechanism, stated in a heading, that four
> documents then built on. §10 has the disassembly.

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
| Does populating a skill list for profession 12 clear the assert? | **STILL UNANSWERED — both instruments reddened their controls (§8, §9)** | Settle the bar-mismatch story first (§9's three discriminators); 12 cannot even reach K via `0x00B7` (load gate, §9) |
| Which surface fails *second*? | **PARTIALLY ANSWERED (§9)** — for `0x00B7`-delivered 12 the FIRST surface is the load gate `ConstChar.cpp:1296`, before any panel | R1 still turns one run into many for what sits past it |
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

---

## 9. Run 4 — `profession_spawn` (2026-08-12): two crashes, two different asserts

Two sessions, spawn-time delivery via `--spawn-profession`, zero mid-session sends.
Both crashed; **neither is the crash §8's route predicted, and each one is a finding.**

**4a — `--spawn-profession 3` (control): the panel dies at a SHIPPING profession.**
Harness `20260812T215649`, capture `authsrv-20260812T215658-c1.jsonl`. `0x00B7(prof 3)`
in the burst at +2.89 s, the client plays normally for ~19 s (c2s until +22.42 s), the
operator presses K, and the dialog (+23 s) is the SAME assert as runs 2 and 3: `*skill`,
`ChCliSkill.cpp(1022)`. **The trace's rebased frames are IDENTICAL to run 2's chain** —
`0x008217EB` (ChCliSkill) → `0x00816E6F` (ChCliApi) → `0x0050277E`/`0x0050106F`
(GmDeckBuilder) → `0x0064CA24` (FrMsg) → `0x00633C7C` (FrApi) — same panel, same
lookup, same line argument `0x3FE` = 1022.

**4b — `--spawn-profession 12`: dead on arrival, at a BOUND CHECK.** Harness
`20260812T215753`, capture `authsrv-20260812T215801-c1.jsonl`. The client's **last c2s
is at +3.42 s — the same instant `0x00B7(prof 12)` was sent.** The operator saw the
loading screen freeze at 0%. The dialog (+4 s):

> **`Assertion: profession < arrsize(s_profChapter)` —
> `P:\Code\Gw\Const\Programmer\ConstChar.cpp(1296)`**

**The first bound check of FINDINGS.md's 29-family ever observed firing live.** The
trace resolves through the message-dispatch layer — MsgConn-range frames with `0x00B7`
sitting in the frame args — into ChCli-range frames and a ConstChar per-profession
accessor whose sibling asserts are `chapter < 3`, `profession`, and
`profession < CHAR_PROFESSIONS` (`ConstChar:844–846`, via `asserts.py --at
0x005AB830`). A frame at `0x0091F0C7` sits in the same region as the appearance packer
`0x0091D430`; noted, not claimed.

### Correction 1 — the byte carriers are NOT equivalent

`0x00A6(12)` lands silently and the client plays on (runs 1 and 2). **`0x00B7(12)` is
lethal ON ARRIVAL**: its handler path validates the profession against the compiled
chapter table. And run 1's step 3 — "the player-specific carrier, also 12" — **was
never actually survived**: run 1's client was dead before that step fired (last c2s
+20.78 s, step ~+27.7 s), so the packet went to a corpse and the run could not have
said otherwise. MODDABLE.md treats the two byte carriers as one storage class; that is
now **CONTESTED** — a custom id must stay off `0x00B7` unless `ConstChar.cpp:1296` is
widened or neutered.

### Correction 2 — the skillbar's own profession was an uncontrolled variable

Operator's hypothesis, mid-report: *"i have a warrior skillbar, maybe that's
illegal?"* **OBSERVED (client table, build 38797, `skilltable.py`): skills 316–323 —
the test bar every session sends — are ALL profession 1, Warrior.** (The enemy's elite
276 is profession 3, matching its declared profession.) Now every K observation in the
arc fits one story:

| Session | Prof when skill data was DELIVERED | Bar prof | Prof at K | K result |
|---|---|---|---|---|
| run 2 arm A | 1 (burst) | 1 — match | 3 | **OPENS** |
| run 2 arm B | 1 (burst) | 1 — match | 12 | `*skill` |
| run 3b | bar REDELIVERED at 3 | 1 — mismatch | 3 | `*skill` |
| run 4a | 3 (burst) | 1 — mismatch | 3 | `*skill` |

**INFERRED:** the panel dereferences skill state built when the skill data arrived,
keyed by the profession in effect at that moment; a bar whose skills do not belong to
that profession leaves the pointer null. The one configuration that ever opened is the
one where bar and delivery profession matched. Run 2 arm B still needs a second
trigger (the current-profession walk at 12) — the story does not replace run 2's
attribution, it sits beside it.

### The discriminators — one session each, all in-band, no new tooling

| # | Session | Prediction under the story | A crash refutes |
|---|---|---|---|
| 1 | default spawn (prof 1, Warrior bar), press K | OPENS | the pure-default control — never run in the arc's history; a crash here means our world breaks the panel regardless |
| 2 | `--spawn-profession 3 --skills ""` (empty bar), press K | OPENS | delivery-time profession alone breaks the panel |
| 3 | `--spawn-profession 3 --skills 276` (a profession-3 skill), press K | OPENS | the mismatch story itself — a matching bar should be safe |

```
python toolkit/harness/session.py --keep-open --shots 10 \
    --game-args '--probe profession_spawn'
python toolkit/harness/session.py --keep-open --shots 10 \
    --game-args '--probe profession_spawn --spawn-profession 3 --skills ""'
python toolkit/harness/session.py --keep-open --shots 10 \
    --game-args '--probe profession_spawn --spawn-profession 3 --skills 276'
```

(Run 1's command will WARN about the missing flag — for that session the default IS
the experiment; say so in the report.)

### Where the population question stands

Reframed, not dead. For profession 12 the panel is no longer even reachable by
`0x00B7` spawn delivery — the load gate fires first. Reaching K at 12 with populated
skill state now means **agent-carrier delivery inside the burst**: `0x00A6(12)` sent
BEFORE the skill block, which no tooling does yet and which is worth building only
after the bar-mismatch story is settled — if a matching bar is what makes the panel
safe, "populated" may simply mean "a bar of skills the profession owns", and no
profession-12 bar can exist in the compiled table.

### Discriminator results (same evening) — the mismatch story is REFUTED

Discriminators 1 and 3 ran; both CRASHED on the same `*skill` assert (dialogs
captured: harness `20260812T220906` and `20260812T221006`; worlds verified from the
captures — prof 1 + Warrior bar, and prof 3 + bar `[276, 0×7]`). Both were MATCHED
configurations and both predicted OPENS, so **the bar-mismatch story is dead by its
own stated predictions**. Discriminator 2 never ran: PowerShell 5.1 collapses the
trailing `""` into a lone `"` and the harness died on an unterminated quote —
`split_args` now refuses that cleanly naming the trap, and an empty bar is
`--skills 0`. (Under the new story below, #2 is no longer load-bearing.)

**The real finding is discriminator 1: the PURE DEFAULT world cannot open the skills
panel.** Six sessions have now pressed K without a prior `0x00A6` and all six died on
the same null; the ONE session that ever opened (run 2 arm A) is the one where
`0x00A6` arrived first. This was never about custom professions.

**And the missing piece was already measured, in another study.** `studies/smsg`
§`0x00A6`: retail sends AGENT_SET_PROFESSION **136 times across 4 tapes**, field 3
cross-matches the player-create profession byte 130/130, and the handler chain
(`0x0091ee70 → … → 0x007f7330`) writes the pair and **notifies exactly the attributes
panel, the party roster and the hero commander** (event `0x1000001d`). Its "for our
server" list — bullet 10 — already recommended sending `0x00A6` per agent. Our burst
sends only `0x00B7` for the player. **INFERRED, one step from SOURCED: the skills
panel dereferences state that only the `0x00A6` handler builds, and our server never
sends the message.** Run 2's arm A opened because the probe happened to deliver it.

**Next: `profession_trigger`** — run 2A replayed with the one change that removes the
change: `0x00A6(1)`, the value the burst already declared, then K. OPENS → the
arrival is the trigger, and the fix is to send the player's `0x00A6` in the burst,
which is what retail does. CRASHES → the trigger is the CHANGE (run 2A's value was
3), and the next probe sends `0x00A6(3)`. Either way, one session:

```
python toolkit/harness/session.py --keep-open --shots 10 \
    --game-args '--probe profession_trigger'
```

### T1 result — CRASHED, and the third refuted story ends the run-and-guess loop

Harness `20260812T221706`, capture `authsrv-20260812T221714-c1.jsonl`. Both
`0x00A6(1)` sends landed (+4.8 s, +10.8 s), K at ~+12 s, same `*skill` at
`ChCliSkill.cpp:1022` (dialog 22:17:27). **The arrival-trigger story is refuted.**
That is three stated predictions dead in one evening — bar-mismatch, arrival-trigger,
and (below) compare-before-notify — so per the house rule the next rung is READING,
not another run.

**Two readings already done (OBSERVED, disassembly of build 38797):**

- **The setter `0x007F7330` has no comparison and notifies unconditionally**: it
  writes the pair to `[AvChar+0x108]+2/+3`, caches at `+0x10E/+0x10F`, and fires
  event `0x1000001d` on EVERY call — confirming MODDABLE's original reading. A
  compare-before-notify cannot explain T1; the event fired in every session, so the
  event was never the discriminating variable. (A by-agent-id variant sits at
  `0x007F73A0` firing the same event.)
- **The `*skill` assert lives inside a bitmap iterator.** The function at
  `0x00821790` is find-next-set-bit over a word bitmap (words at `+0x10`, word count
  at `+0x18`); it converts the found bit to an id, fetches a per-id skill object,
  and line 1022 asserts that object non-null. **The skills panel WALKS A SKILL
  BITMAP and asserts on each id it visits.** Sibling asserts in the same region:
  `*copies` (1036), `skill` (442/463). And this repo has met the family before from
  the unlock direction: `unlock_all_words()`'s clamp comment records that an
  UNCLAMPED unlock bitmap asserted ChCliSkill the moment the panel opened, which is
  why "all" means all 3,443 real rows and not all 4,096 bits.

**What survives eight K observations:** the current primary at K is the only
variable left standing — `0x00A6`-delivered **3 opened; 1, 12, and never-set all
crashed** — and no story yet explains that shape. Which bitmap instance the walk
reads (unlocks? per-profession learned list?), what it filters by, and which per-id
object is null are all READABLE from the callers: GmDeckBuilder's open path
(`0x0050277E`, `0x0050106F`) → ChCliApi (`0x00816E6F`) → the iterator's call sites.

**The next rung is that static dive, and NO client run until it is done.** Three
refuted predictions is past the study-before-iterating threshold; the dive names the
walked object and the filter, and then ONE run confirms it.

---

## 10. The dive (2026-08-12): it was our bit, and there was never a profession in it

Eight agents — four parallel reads of the call chain, one synthesis, three adversarial
verifiers that re-ran every disassembly independently. Two verdicts held; **the third
refuted part of the proposed fix**, which is recorded below because it was right.

### 10.1 The mechanism, end to end

All static VAs, build 38797, OBSERVED — re-derived by at least two agents independently.

| Step | What happens |
|---|---|
| `0x00502580` | panel refresh. Four gates (`0x005025CE`, `0x005025D9`, `0x0050263D`, `0x0050264F`) — **none reads a profession**. Enumeration cursor zeroed at `0x00502646` |
| `0x00502779` | `call 0x816E50` (crash frame `0x0050277E`), three out-pointers, no profession argument |
| `0x00816E50` | TLS context → `this = ctx[0x2c]+0x700` → `call 0x821790` (crash frame `0x00816E6F`) |
| `0x00821790` | find-next-set-bit over words at `[this+0x10]`, count at `[this+0x18]` |
| `0x008217CB` | `lea eax,[esi+ebx]` — **id = (word << 5) + bit** |
| `0x008217D3` | `test eax,eax` → if ZERO, push `0x3FE` (=1022), `call 0x00487BC0` at `0x008217E6`; next instruction `0x008217EB` is the crash frame |

> **`*skill` is a ZERO-VALUE test on the enumerated skill id. Nothing is null.**
> The assert fires **iff the walked bitmap has bit 0 set**, because id 0 is not a skill.

Four crash-stack frames land on four instructions that were disassembled — a chain our
own decoder cannot force. Two supporting reads that could have killed it and did not:
`0x0046E110` is literally `bsr eax,ecx; ret` — **zero-based**, so bit 0 really does
enumerate as id 0 (1-based would have made this reading impossible); and the not-found
exit (`mov esi,0x7fffffe` at `0x008217C3`, rejected by `cmp eax,0x7fffffff`) is clean,
so an empty or bit-0-clear bitmap **ends the loop and opens the panel**.

### 10.2 Which bitmap — a correction the reads got wrong and the synthesis caught

Two read agents assigned the walked container to opcode `0x00D3`. Wrong, and the
difference is one instruction: the shared bitmap setter `0x00473550` keeps words at
container `+0`, capacity `+4`, count `+8`. The iterator reads `+0x10`/`+0x18` off base
`+0x700` — i.e. a container embedded at **`+0x710`**. `0x00DB`'s writer `0x00822910`
does `add ecx,0x10` at `0x00822916`; `0x00D3`'s writer `0x00821CC0` does not.
`--xrefs` closes it: the `+0x710` container has **exactly one writer and one reader** in
the whole image.

**`0x00DB` is `GAME_SMSG_UPDATE_UNLOCKED_SKILLS` — the message this server sends.** The
panel was doing the obvious thing: listing the skills we told it we own.

### 10.3 The defect is ours, and it is one character

`unlock_all_words()` iterated `range(SKILL_TABLE_ROWS)` — **from 0**. Every `0x00DB` this
server ever sent carried bit 0: **242 of 242 sends across every capture in the vault**,
all beginning `db 00 80 00 ff ff ff ff`. `build_unlock_bitmap`'s explicit-list arm has
had `if sid <= 0: continue` since it was written; only the "all" arm was wrong.

Fixed to `range(1, SKILL_TABLE_ROWS)`, with the pre-fix version rebuilt inline as a
negative control (`test_agentlife.py`, unlock-bitmap section) — the two must differ in
exactly bit 0, so a revert reddens.

### 10.4 Why the "profession 3 opens" premise was false

**The deductive argument is the strong one, and it needs no capture:** there is **no
profession-dependent branch anywhere** between the panel's entry and the assert — zero
conditional instructions between the profession getters' return at `0x00502768` and the
call at `0x00502779`, none inside `0x00816E50`, none inside `0x00821790`. With an
identical bitmap, a profession-dependent outcome is **not merely unobserved, it is
unavailable.** And the one profession-indexed table in the story could not have helped:
`s_profChapter` at `0x00A384F0` reads `[0,0,0,0,0,0,0,2,2,3,3]` — **entry[1] == entry[3]
== 0**, Warrior and Monk identical.

The evidential half agrees (§3's retraction). Scope it honestly, per the verifier: **no
session shows the panel open**, and every session where the client demonstrably died
after a K prompt died with bit 0 set — but a K press leaves no c2s trace, so most
sessions cannot confirm one happened. Run 2 carries the refutation alone.

*(The verifier flagged session `20260812T213215` as alive 215 s past a K prompt. That is
run 3a — the unattended session where the echo defect sent the prompts to `gamesrv.log`
and nobody was at the keyboard. Explained, not anomalous.)*

### 10.5 What the verifier refuted, and it inverts the advice

The synthesis proposed sending `0x00A6` for the player to fix what the panel *displays*.
**Measured and refuted:** `0x00A6`'s setter `0x007F7330` writes only the agent object
(`+0x10E`/`+0x10F`) and fires event `0x1000001D`, which only GmAgentCommander and
AttribFrame listen to. The panel's profession getters read a 20-byte-record array at
**`ctx[0x2c]+0x6BC`**, whose **only writer is `0x0081FD60`, reached only from `0x00B7`'s
handler** — and that writer fires `0x1000004E`, the event GmDeckBuilder's own listener
arm waits for (`0x00500659` → `0x0050067D`). `--field 0x6bc` finds no other route.

> **So the panel's display is fixed by `0x00B7`, not `0x00A6` — and `0x00B7`'s handler
> `0x00813AE0` makes a SECOND call, `call 0x819e60` at `0x00813B12`, which reaches the
> attribute rebuild and feeds the primary to `s_profChapter`'s bound
> (`ConstChar.cpp:1296`).** The sole writer of the panel's profession record and the
> message that asserts on a profession ≥ 11 are **the same message, one call apart.**

**No server-side message can make the panel display a custom profession.** That is not
an unverified next wall — it is a measured dead end, and it is sharper than what the
synthesis claimed. Widening the 11-entry table or R1's assert neuter is the only route,
and both are client-side.

Confirmed from our own wire: the `ConstChar:1296` session sent **zero** `0x00A6` and one
`0x00B7(prof 12)`, last c2s at the same instant. The 1296 route is `0x00B7`'s alone.

Two label corrections the verifiers forced, both worth keeping: "no profession is read"
is **false** (two getters *are* called, at `0x00502758`/`0x00502763`) — the defensible
claim is that **no profession value BRANCHES anything**; and those getters are read
*before* the walk and used only after it.

### 10.6 Where the arc stands

| Claim | Now |
|---|---|
| `*skill` is a null lookup | **REFUTED** — a zero-value test on an enumerated id |
| Profession 3 opens the panel, 12 asserts | **REFUTED** — the walk is profession-blind; arm A crashed |
| The 29 bound checks are the profession wall | **One is REAL and OBSERVED**: `ConstChar.cpp:1296`, on `0x00B7` arrival |
| `0x00A6(12)` lands and the client plays on | **STANDS** (runs 1, 2) — the one original finding that survives |
| The byte carriers are not equivalent | **STANDS and is sharpened** — `0x00B7` validates, `0x00A6` does not |
| A custom profession can be DISPLAYED by a server message | **REFUTED** — measured dead end (§10.5) |

**Falsifiable prediction, stated before the run:** with bit 0 cleared and nothing else
changed, the **pure default world** — primary 1, Warrior bar, no `0x00A6` — opens the
Skills-and-Attributes panel on K, and the client keeps answering pings for the rest of
the session. If it still asserts at `ChCliSkill.cpp:1022`, this whole reading is wrong.
**Score it on c2s traffic after the K press, never on the socket.**

**STATUS: UNTESTED.** The first attempt (harness `20260813T000725`) crashed and did
**not** test it — the run was served by **another worktree**. `session.py` spawns
`authsrv.py` from *its own* directory (`TOOLKIT` derives from `__file__`), so launching
a different tree's `session.py` runs that tree's server: this one printed
`all (3443 real skills)` and `MAP OVERRIDE: 143`, and its `0x00DB` still carried
`word0 = 0xffffffff`. Bit 0 was set on the wire, so the client did exactly what §10.1
says it must. **A pre-fix server cannot falsify a post-fix prediction.** Run it by
ABSOLUTE PATH:

```
python C:\gd\Rurik\.claude\worktrees\sweet-euler-697883\toolkit\harness\session.py \
    --keep-open --shots 10 --game-args '--probe profession_spawn'
```

**Two tells now make this self-diagnosing from `gamesrv.log` alone**, both added
2026-08-13: the banner prints `source: <dir>` naming the tree that served the run, and
`unlocks:` must read **3442**, not 3443. And the bitmap is now a **hard refusal** —
`refuse_skill_zero()` raises at startup naming `ChCliSkill.cpp:1022`, so a tree carrying
the old loop dies before the socket opens instead of twelve seconds into a client
session. It refuses rather than repairing: a server that quietly fixed its own payload
would hide the next bad producer.

### 10.7 Carried forward

0. **A parallel session is working this same arc** in worktree
   `friendly-kilby-fcaf57` (branch `claude/custom-profession-exploration-dead6c`), and
   its tree still carries the bit-0 loop. Anything it measures about the skills panel
   before it takes `main` is measuring the old defect. Whoever reads this first should
   say so in that session rather than letting it spend more client runs.
1. **The probe driver needs the proof-of-life fence** `test_smsgsweep.py` already has —
   run 2's misattribution is that same defect, and it cost six sessions. A K press
   leaves no c2s trace, so a probe prompt should also require the operator to
   acknowledge that they acted.
2. **`asserts.py --at` is a proximity window, not enclosing-function bounds** — querying
   a RETURN address can omit the very assert that produced it. `--grep` on the
   expression text is the reliable pin. (This is what let §4's "null lookup" stand.)
3. **The 15-map whitelist is a landmine on other maps.** Where `[edi+8] & 0x10`,
   GmDeckBuilder builds the secondary-profession dropdown (the WIKI mechanic of §8) and
   carries `GmDeckBuilder:2321 agentPrimaryProf != agentSecondaryProf` and
   `GmDeckBuilder:2334 entryIndex`, with its loop bounded `cmp edi,0xb`. With no `0x00B7`
   both getters return 11, so primary == secondary and **2321 fires**; and 11 can never
   have an entry, so **2334 fires**. Our map reaches the assert only because
   `[edi+8] == 0`, so this does not affect the prediction above — but it will bite the
   first time the arc changes map.
4. **Unmeasured:** with bit 0 cleared the walk posts up to ~3,442 UI rows through msg
   `0x57`; no bound on that list was established.
