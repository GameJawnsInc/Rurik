# Monster AI — what can be recovered, and what cannot

**Study arc:** `studies/monsterai/` · **Date:** 2026-08-11 · **Method:** five parallel angles (client binary, ArenaNet's own captured traffic in two passes, GWW, our own repo), each hostilely refuted by an independent skeptic, then a capture-campaign design and a completeness critic over the whole dossier.

---

**The result.** Monster AI as a *mechanism* — the decision function, its inputs, its internal state, its tick — cannot be recovered from the client binary, cannot be recovered from the wire, and cannot be recovered by any capture campaign of any length, because it is never shipped and never transmitted. That is a firm negative and it holds up: zero of 937 embedded source paths in the shipped client lie under any `\Srv\` directory, from a detector proven able to catch 6 of 6 planted ones, and 33 AI-adjacent keyword searches across two structurally independent routes (the compiled-assert corpus and a raw-string scan of every section including `.rsrc`) return zero. What *can* be recovered is the observable **envelope** — what a monster does, when, at what range, at what speed, per creature model — and a surprising amount of it was already sitting in the vault, mis-measured. The single largest finding of this dive is negative and self-inflicted: `SWING_WINDUP = 0.899` was adopted as a fixed constant on n=6 swings from one agent, and the second live capture, already in the vault when that constant was written, refutes it (n=42 across four attackers at two declared speeds, two non-overlapping clusters 86 ms apart). The second largest is that **twelve of fourteen combat constants in `authsrv.py` can be changed to a wrong value and all 125 checks in the suite stay green** — so the honest comment at each call site is currently the only thing standing between an invented number and a claim. Confidence: high on the binary negative, high on the per-model spread of reach and windup, **low to nil on aggro range, leash and skill-selection policy**, none of which this corpus can answer. **UPDATE 2026-08-11, after the study's own cheapest follow-up ran: the binary negative is now TOTAL.** `CHAR_AI_MODES` — the one named server-shaped AI concept anywhere in the shipped image, and the one lead §2.2 explicitly declined to call refuted — reads **3**, and its three modes resolve through the client's own text system to **Fight / Guard / Avoid Combat**. It is the player's hero-and-pet stance widget. Nothing about monster decision-making survives in the client. §2.2.1.

**Notation.** Captures are named by timestamp stamp only: **capture A** = `20260807T143055`, **capture B** = `20260810T235916`. Connections are `A/2`, `B/4` etc. — capture stamp plus connection index in chain order. No ports, accounts, characters or session ids appear here or should appear in anything derived from this. Agent ids are per-connection wire ids and are not identifying.

---

## 1. The question, and why it was asked now

Our server gives its one enemy a bar of four skills and cycles them round-robin. The bar's four ids were picked by us out of the client's own skill table; the selection policy is ours; the four constants that decide when a monster notices, closes, reaches and swings are ours. When the round-robin selector landed, the owner ruled:

> *"I don't want to invent mechanics like that, I thought we were just testing. we'll need to do a deeper dive into AI before we decide casting AI, but this is a good testing function still."*

and, opening this dive:

> *"if we can't reconstruct it easily via diasm/binaries/packets then consider creative alternative solutions that we could use to best approach the stock game experience."*

This document is what decides what replaces the invented layer — or decides, with evidence, that nothing can yet, and says exactly what would. The answer is the second, with a large caveat: the *envelope* is measurable and several parts of it are already measured, so "nothing can" applies to policy, not to the numbers policy operates on.

`pick_skill`'s own docstring already says the honest thing and this dive does not improve on it: *"STILL NOT MEASURED … Round robin, least-recently-used and priority order are all inventions."*

---

## 2. What the client binary knows

**Result: no monster-AI decision code is shipped, and the negative is wide — but it is a floor, not a census, and it has one named crack.**

### 2.1 The negative, and why it is trustworthy

| Search | Scope | Result |
|---|---|---|
| Server-side translation units | 937 distinct `P:\Code` source paths, 6 naming patterns (`\Srv\`, `SrvXxx`, `Server`, `SvXxx`, `GameSrv*`, `HostXxx`/`SimXxx`) | **0** for every pattern |
| Assert expressions, 19 AI terms | 19,758 readable assert sites, case-insensitive | **0** each |
| Assert expressions, 14 further terms (`follow`, `chase`, `avoid`, `steer`, `pursue`, `flee`, `wander`, `seek`, `engage`, `notice`, `alert`, `awake`, `sense`, `target`) | same corpus | 7 hits, **every one a false positive** (a spectator-camera flag, a shop constant, `s_avoidCount`, `s_refCountAlert`, a file seek) |
| Raw strings, 9 terms | 30,941 distinct printable ASCII + UTF-16LE strings ≥4 chars across `.text`/`.rdata`/`.data` | **0** each |
| Same, extended | +12,891 strings in `.rsrc`/`.reloc`, plus `danger`, `aggress`, `hostile`, `monster`, `AI_`, `aiMode`, `flee`, `guard` | **0** each |
| `1012.0f` / `1248.0f` (the wiki's aggro and cast ranges) | f32 aligned and unaligned, f64, int32, squared forms, half-range — all sections | no genuine constant; 3 raw `1012.0` byte runs in `.text` are mid-instruction coincidences and `.rdata` (where float constants live) holds zero |

**Label: SOURCE-CODE. n:** two builds for the source-path census; one pinned build (`vault/client/2026-07-29_221c13772c7a/Gw.exe`, build 38797) for the rest. Every figure above was independently reproduced by a second party — the 30,941 string count reproduced *to the string* from a scanner written from scratch.

The srctree zero is worth more than the others because its detector is proven able to fire: `test_srctree.py` plants six fabricated `Srv`-style paths and requires all six caught, with a no-false-positive control. The keyword zeros are worth less, and their own tool says so — `asserts.py` prints a coverage shortfall of 370 unreadable call sites on every invocation, so **every keyword zero is a floor short by up to that many sites**, and `CompassAIControl.cpp` — the one file in the whole image whose name is literally "AI Control" — contains **zero asserts** and is structurally invisible to the tool that produced them.

Two scope corrections that were missed and matter. "No `Srv` translation unit" is **not** "no server code in the image": `srctree.py`'s own output ends with *"shared trees: no Cli/Srv split, so the server built these too — Base 79, Engine 297, Net 18, Gw\Const 37"*, i.e. **431 shipped files the server also compiled**. Among them is an eleven-file `Engine\Map\Path` subsystem — `PathFind`, `PathFlood`, `PathObstacle`, `PathDir`, `PathBsp`, `PathBuild`, `PathApi`, `PathData` and more. Six of those were read in full for this dive: their asserts are trapezoids, portals, barriers, `SINK_NODE`/`X_NODE`, edge tables, `blockMap`/`mapDims`. **Pure geometry, zero AI vocabulary.** One positive fell out that nobody had: `PathObstacle:176` asserts `radius >= 0` — the shipped pathing library models **dynamic obstacles with a radius**, which is the mechanism behind the wiki's body-blocking and melee-surround behaviour, and `toolkit/mapdata/pathmap.py` has no dynamic obstacle at all.

### 2.2 The one crack: `CHAR_AI_MODES` — **CLOSED 2026-08-11, as UI**

**READ THE RESOLUTION IN §2.2.1 FIRST.** What follows is the lead as this study first
reported it, kept because the *reasoning* about it was sound and the outcome was not
foregone. The immediate has now been read. It is 3, the three modes are **Fight**,
**Guard** and **Avoid Combat**, and the rival this section declined to refute is the
one that survived.

**Label: SOURCE-CODE. n:** 9 `AI_MODE` assert sites + 10 `aiMode` sites, run against the pinned build.

```
0x0080dfae  ChCliApi:4331        mode < CHAR_AI_MODES
0x0050db1e  GmPetCommander:127   m_aiMode == CHAR_AI_MODE_AGGRESSIVE
0x0050d810  GmPetCommander:161   petAiMode != CHAR_AI_MODES
0x0050d83d  GmPetCommander:166   m_aiMode < AI_MODE_ICONS
0x004fba74  GmAgentCommander:328 aiMode < CHAR_AI_MODES
0x004fca1a  GmAgentCommander:150 No valid case for switch variable 'm_aiMode'
0x004e4b4a  GmView:6743          No valid case for switch variable 'hero.aiMode'
```

`srctree.py` reports `Gw\Char  14 files, 11 Cli, 0 Srv  <- Cli/Srv split`. So this is a **per-character AI-mode enum, in the same `CHAR_` namespace as `CHAR_CLASS_MONSTER_BASE`, inside a subsystem whose server half was not shipped.** Two format strings in the same binary carry it across a wire-shaped boundary: `HeroActivate (hero %d, agent %d, inventoryId %d, aiMode %d)` — whose only `.text` xref resolves into `Gw\Char\Cli\ChCliHero.cpp` — and `NAPetAdd (agent %d, aiMode %d)`. An aiMode alongside an agent id.

None of the 19 original keywords would have caught any of this; it surfaced from a one-letter change (`aggro` → `aggress`). **That is the shape of every confident zero in this section.**

**The rival is not refuted and I am not claiming it is:** `CHAR_AI_MODES` may be a pure UI enum for the compass Guard/Fight/Avoid-Combat stance. **Refuted if** its cardinality — readable as the immediate operand of the comparison at `0x0080dfae` — is exactly 3 and matches the three stances. That immediate has not been read. **It is the single cheapest open question in this whole study: one capstone pass, no capture, no client launch.**

### 2.2.1 The read, 2026-08-11 — and it closes

**The prediction was stated before the disassembler ran and it is confirmed on every
axis: `CHAR_AI_MODES = 3`, and the three modes are `Fight`, `Guard`, `Avoid Combat`.**
This is the player's own hero/pet/henchman stance control. It is not a monster-AI
concept, and with it the binary negative of §2.1 becomes **total**: there is now no
named server-shaped AI concept anywhere in the shipped image.

**Label: SOURCE-CODE. n:** 9 bound sites + 2 switch statements + 1 string triple, all
on the pinned build (38797).

**The bound, five times.** Every `CHAR_AI_MODES` comparison in the image reads 3:

```
0x0080DFA3  cmp dword ptr [ebp + 0xc], 3   ChCliApi:4331          mode < CHAR_AI_MODES
0x004FBA6A  cmp edi, 3                     GmAgentCommander:328   aiMode < CHAR_AI_MODES
0x0050D806  cmp ecx, 3                     GmPetCommander:161     petAiMode != CHAR_AI_MODES
0x0050D94E  cmp eax, 3                     GmPetCommander:254     m_aiMode < CHAR_AI_MODES
0x0050E0CA  cmp edi, 3                     GmPetCommander:368     petAiMode != CHAR_AI_MODES
```

The three `AI_MODE_ICONS` sites read 3 as well, and the AGGRESSIVE site reads 0:

```
0x0050D833  cmp edx, 3                     GmPetCommander:166     m_aiMode < AI_MODE_ICONS
0x0050E590  cmp eax, 3                     GmPetCommander:515     m_aiMode < AI_MODE_ICONS
0x0050E744  cmp dword ptr [edi + 0x20], 3  GmPetCommander:515     m_aiMode < AI_MODE_ICONS
0x0050DB16  cmp dword ptr [edi + 0x20], 0  GmPetCommander:127     m_aiMode == CHAR_AI_MODE_AGGRESSIVE
```

**And the read validates itself, which is why it is worth more than a pattern match.**
An MSVC assert compiles to `cmp` / `j<cc>` / `push <LINE>` / `mov edx,<expr>` /
`mov ecx,<file>` / `call`. So the instruction stream carries the **source line number**
as an immediate, and it must equal the line `asserts.py` reports for that address from
an entirely different mechanism. **All nine sites agree** — `push 0x10eb` = 4331 at
`ChCliApi:4331`, and so on down. A window that had landed on a lookalike site would
have produced a mismatched line and been thrown out.

**Two independent switches, three arms each.** `GmAgentCommander:150` and `GmView:6743`
are both `No valid case for switch variable` defaults, and both switches compile to a
`sub`/`je` chain rather than a jump table — so the arm count is readable directly and
owes nothing to any `cmp`:

```
GmAgentCommander @ 0x004FCA00          GmView @ 0x004E4B33
  mov eax, [edi + 8]                     mov eax, [edi + 0xc]
  sub eax, 0 ; je -> case 0              sub eax, 0 ; je -> case 0
  sub eax, 1 ; je -> case 1              sub eax, 1 ; je -> case 1
  sub eax, 1 ; je -> case 2              sub eax, 1 ; je -> case 2
  push 0x96   (= 150)  -> default        push 0x1a57 (= 6743) -> default
```

**And the switch names them.** `GmAgentCommander`'s three arms are a mode → string-id
map to three consecutive ids, resolved through the client's own text system by
`toolkit/clientscan/textrec.py`:

| mode | id | `textrec.py` | file:record |
|---|---|---|---|
| 0 | 44156 (`0xAC7C`) | **Fight** | 43:124 |
| 1 | 44157 (`0xAC7D`) | **Guard** | 43:125 |
| 2 | 44158 (`0xAC7E`) | **Avoid Combat** | 43:126 |

`CHAR_AI_MODE_AGGRESSIVE` reads **0** (`cmp dword ptr [edi + 0x20], 0` at
`GmPetCommander:127`), i.e. the mode labelled *Fight* — internally consistent, and a
fact nobody arranged. `m_aiMode` lives at struct offset **+0x20**, agreed by two sites.

**`AI_MODE_ICONS` is also 3.** A second symbol, a parallel array, sized to the mode
count. An icon per stance is a UI structure and nothing else — this is corroboration
*for* the surviving rival rather than merely consistency with it.

**What this does and does not say.** It says the client's only AI-mode concept is the
three-button stance widget the player sets on their own party. It says nothing about
whether ArenaNet's *server* has a richer notion — it cannot, because §2.1 is exactly
the finding that the server's code is not here. The `HeroActivate (hero %d, agent %d,
inventoryId %d, aiMode %d)` format string still shows an aiMode crossing a wire-shaped
boundary; it now reads as the client *telling the server which stance the player
picked*, which is the direction that was always more likely and is now the only one
left standing.

**No test was added, and the reason is proportionality rather than laziness.** Every
address above is build-specific — `pinned.py` exists because addresses are not part of
any file format and must not be carried between builds — and nothing in this repo
depends on this finding; it closed a lead rather than opening a code path. A check here
would go red on ArenaNet's next update for a reason unrelated to anything of ours, which
is the failure mode that trains people to ignore red runs. The reproduction is the four
commands in §2.2.2, and the string ids are the stable part if it ever needs re-running.

### 2.2.2 Reproducing it

```bash
python toolkit/clientscan/asserts.py --grep "(?i)ai.?mode|AI_MODE"
python toolkit/clientscan/codescan.py --dis 0x0080dfa0 --count 8
python toolkit/clientscan/codescan.py --dis 0x004fca00 --count 12
python toolkit/clientscan/textrec.py 0xAC7C 0xAC7D 0xAC7E
```

A methodological note worth keeping, because it is the same shape as three other
defects in this study. The scratch reader that swept all nine bound sites first took
the **first** backward alignment that landed on the assert address, and reported
`<none in window>` for `ChCliApi:4331` — the one site whose listing had already been
read by hand and demonstrably has a `cmp` 11 bytes up. A shallow start decodes a few
bytes of garbage that happen to land on the target and carries no `cmp`. Taking the
**deepest** consistent alignment fixed all four false negatives at once. A confident
zero from a reader that knew one alignment of many: §6 has three more of those, and
this one was caught only because a hand-read listing contradicted it.

### 2.3 What else the binary was asked and answered

- **`GAME_SMSG 38` (AGENT_UPDATE_FLAGS)** — the setter at `0x006028a6-0x006028b7` is exactly `((old ^ new) & 0x3f0000) ^ new`, VERIFIED by disassembly. Bits **16–21 keep their old value**; the server can only deliver the other 26. Of those 26, exactly **one** is named by any assert this project has read (`AGENT_FLAG_INVISIBLE`, bit 1). Whether an aggro or alert bit rides here is **NOT FOUND, over 25 unlabelled deliverable bits**. (The dossier's original claim listed `DESTROYING`, `IN_WORLD` and `MOVEMENT_STALE` as flags this message "carries"; they are bits 16, 17 and 19 — inside the mask — so they are precisely what it cannot set. See §6.)
- **The 67-id generic-value enum** — structurally extracted from the client's 7 real dispatch switches (int main at `0x008128f0` handling 47 ids, float main at `0x00813040` handling 14, ids 5/8/40/51 with no main case body, id 40 acted on by no switch at all). The *structure* is SOURCE-CODE and sound. The claim that none of the 67 is an AI decision input is a reading of **reconstruction names** over a channel that is a render/notify path by construction, with 13 ids carrying no name at all — **UNVERIFIED as evidence about AI**, not a measured negative.
- **`schema/overrides.json`** — a reported "zero hits for AI/MONSTER/NPC/… in the full catalog" was a check that could not fail: `schema/messages.json`'s 777 entries carry **no `name` field at all**. The 37 names in the project live in `overrides.json`, and grepping those returns three: **GAME_SMSG 86 `NPC_UPDATE_PROPERTIES`**, GAME_SMSG 87 `MONSTER_COMPOSITE`, GAME_CMSG 59 `NPC_SERVICE_SELECT`. The first is the most on-topic opcode in the catalogue for this study and was reported as absent. See §3.7 for what it turned out to carry.

---

## 3. What ArenaNet's own traffic shows

**Result: the corpus is exhausted, it is thin, and its most useful findings are per-creature-model rather than global. It settles reach, windup, speed vocabulary and the shape of a fight. It cannot settle aggro range, leash, target switching, group pulls, respawn or skill-selection policy — and it never could, because none of those events occur in it.**

### 3.1 The corpus, measured

Two mined live captures, 8 connections, **21,543 GAME_SMSG messages, carry=0 on every connection** — reproduced independently twice and matching `test_smsgnames.py`'s own count. (The capture-campaign angle quotes 22,137, which is the figure in `test_tape.py`'s docstring; the two were not reconciled and 21,543 is the number two parties re-derived here.) Client-to-server: **500 game-channel messages over 25 distinct opcodes** in capture B — the direction nobody had opened at the start of this dive, and the one that answered by measurement what the first pass answered by reconstruction.

The other four live sessions are now accounted for, which closes "only two of six were mined" as a real zero: one decodes cleanly to 387 messages over 2 connections with **zero `WORLD_CREATE_AGENT`** — no agents, therefore no monsters — and three have no decrypted game channel at all. `aiload.py` hardcodes the two mined stamps, which is why nobody had looked.

Population (OBSERVED, whole corpus): 1,068 creates, kind byte taking `{0:23, 1:94, 5:366, 8:25, 9:560}`; 76 distinct `mon1` hostiles across the four explorable connections; **9 distinct kind=9 agents appear in any combat generic-value event, ever**; 151 distinct NPCs issue at least one movement message (976 `AGENT_MOVE_TO_POINT` + 130 `AGENT_UPDATE_SPEED` + 99 `UPDATE_ROTATION`). So ambient locomotion is common and combat is rare.

### 3.2 Fights: five, four of them started by the player

**OBSERVED, n=5 of 76 distinct hostiles.** Agents 38 (A/2), 40 (A/4), 43 (B/2), 41 and 278 (B/4) trade an attack with the player. In **four of the five** the client's own `GAME_CMSG 38 ATTACK_AGENT` or `39` attack-skill precedes the server's `attack_started` echo by **2.0–11.5 s** — witnessed in the client stream, not inferred. Only agent 41 has no player-side event in either direction, and that survives a test it was never given: the client half of that connection contains attack clicks on two other agents and never on 41.

**What this refutes:** our server's model, in which a hostile notices an approaching non-attacking player inside `AGGRO_RANGE` and initiates. That model is refuted for 4 of 5 and left open for the 5th.

**What it does not establish:** any distance. The reported "935–2077 units away" band is not a range — the 2077 figure reproduces exactly as the *length of the leg the player walked* to reach that monster. See §6.

Time from the player's first hostile act to the hostile's first `attack_started` is **3.534–8.178 s over n=3**, and it is dominated by travel. Which number you get depends on whether you date the player's act from the click, the skill activation, the damage, or the value-4 `attack_started` — and those differ by up to 11.5 s. **n is too small and the definition too unstable to characterise a reaction latency; do not quote a mean.**

### 3.3 Reach is a per-model property, and a global constant is refuted in both directions

**OBSERVED. n = 1 measured melee case, 2 measured ranged cases, 1 unresolved.**

| Model | Declared attack base (`0x0035`) | Separation at its own `attack_started` | Behaviour |
|---|---|---|---|
| 536872258 (agents 40, 41, 48) | 2.00 s | **~65 units** (agent 40, over a 13 s exchange) | closes, then strikes |
| 536872346 (agents 38, 43) | 1.75 s | **~599 units** | strikes without closing |
| 536872354 (agent 278) | 1.75 s | **~706 units** | never moves at all (0 move messages) |

The ~65 figure rests on two oracles the first pass did not open: the client's own self-position (`GAME_CMSG 61`, whose first vec2 is bit-identical to the server's create position on the first message of all four connections) and **`GAME_SMSG 0x00A4`, whose vec2 is the *target's* world position — the only direct positional oracle for a non-player agent anywhere in the server-to-client stream, and there are thirteen of them in 21,543 messages.** That oracle is self-validating: on agent-40 rows it lands on that agent's patrol leg at **79.34 u/s against the 80.0 u/s its own speed fraction predicts** — a check that could have failed and did not.

`ENEMY_MELEE_RANGE = 150.0` is therefore refuted from both sides at once: one model reaches from well *inside* it, two from four to five times *outside* it. **Never pool across model ids.** The original 269–1594 unit "range band" is exactly what pooling three creature types produces.

Agent 278 deserves its own line because the whole surviving >150 refutation rested on it and nobody said so: it is the corpus's **burrowing worm** — three creates at one identical position, `EFFECT_TRANSITION` (0x1000) set and cleared, two removes, create speed field 12.0. It cannot walk.

### 3.4 Movement vocabulary

**OBSERVED, corpus-wide.**

- **`0x0025 AGENT_MOVE_DIRECTION` is a player-body channel only** — 593 of 593 instances name a kind=5 agent, naming up to 10 distinct players in one outpost, and **zero** name any kind=9 NPC.
- NPC movement rides **`0x0029 AGENT_MOVE_TO_POINT`** (1,997 corpus-wide) and **`0x002A AGENT_UPDATE_DESTINATION`** (23 corpus-wide, 4 of them for kind=9). `0x002A`'s fifth field names the *followed agent* and its destination equals that agent's exact position — proved bit-for-bit against the client's own self-report. This is a **follow/pursue primitive**, and the client disassembly already says more about it than the wire can: `studies/movement/FINDINGS.md` records that `0x002A`'s handler is byte-identical to `0x0029`'s except for one extra push, that the argument lands in `agent+0x98`, and that **the client's internal move re-issuers deliberately preserve it** — a mechanism claim no packet count can make. (Both study docs — `studies/movement/` and `studies/cmsg/` — went uncited by every angle and each independently re-derived their contents from scratch.)
- **Speed fractions**, `AGENT_UPDATE_SPEED`, 22 hostile agents / 26 messages: `{0.2778: 7, 0.3333: 9, 0.3472: 6, 1.0: 4}` — i.e. **80 / 96 / 100 u/s against a 288 u/s reference**, with the 80 independently measured at 79.34 u/s. `ENEMY_MOVE_RATE = 0.75` (216 u/s) is **never sent to a hostile**, though it is sent three times to the player's own agent, so it is a real retail value that these hostiles never take.
- **The jump to 1.0 is not an aggro signal.** Of the four hostile jumps to full speed, two close on the player, **one closes on other NPCs**, and one moves away from a player 4,300 units distant. The reading "1.0 means it noticed you" is refuted by its own corpus.
- **Turn rate is per-creature and quantised.** 111 rotation messages across both captures give exactly three distinct rates — `{0.24892, 0.8901179, 2.0943952}` — and the largest is **bit-identical to float32(2π/3)**. Our server sends that maximum to everything.

### 3.5 The swing, and the constant it kills

**OBSERVED. n=42 clean windups from 4 attackers at 2 declared speeds, both captures, paired conservatively (a start pairs only with a landing preceding that attacker's next start, so a truncated swing is dropped rather than mis-paired). RE-MEASURED FROM SCRATCH by the orchestrator — see §10 — because this is the finding that changes code.**

| Declared base (`0x0035`) | n | Agents | Token | Windup range | Ratio to declared |
|---|---|---|---|---|---|
| 2.00 s | 18 | 40, 48 | `mon1` | **0.880 – 0.920 s** | 0.4401 – 0.4600 |
| 1.75 s | 24 | 46, 47 | `band` | **0.746 – 0.794 s** | 0.4263 – 0.4538 |

Pooled: **mean ratio 0.4458, sd 0.0073, range [0.4263, 0.4600], n=42.**

The two windup clusters **do not overlap** — the gap is **+86 ms**, roughly twice either cluster's own width — while the two *ratio* bands do overlap. That is the whole argument in one line: express the windup in seconds and the creatures disagree; express it as a fraction of the creature's own declared attack base and they agree.

**Our own pairing is worse than "not a constant" — it is outside everything ever observed.** `authsrv.py` ships `SWING_WINDUP = 0.899` against a declared `ENEMY_ATTACK_SPEED = 1.33`, an implied ratio of **0.6759 — 47% above the largest ratio in the corpus.** The proportional model predicts **0.593 s** for our Hatcher. Neither surviving model supports the number we ship, so this is not a choice between two readings; the shipped value loses to both.

**Two confounds stay open and must be stated.**

1. Two declared speeds across two creature pairs do not separate "scales with declared speed" from "is per-creature and happens to track speed." A third declared speed would. **What is dead is "fixed for everything."**
2. The 1.75 group's attackers carry the **`band`** token, not `mon1` — they are the NPC-vs-NPC skirmish of §3.9, not hostiles fighting the player. So the two clusters differ in allegiance as well as in declared speed. This does not rescue the fixed model (the `mon1` cluster alone spans 0.880–0.920 and still refutes a single number paired with 1.33), but it does mean the *proportional* model rests on a comparison across allegiance classes, and a third sample within one class is what would close it.

**A third declared speed already exists in the corpus and yields nothing.** One agent in capture B declares **2.475 s** and never produces a paired windup — the melee-finish channel carries landings for exactly 4 agents corpus-wide. So the third data point has to come from a capture, as §7 says; it is not sitting unread in the vault the way the second one was.

The related two-phase figure — `attack_started` → `melee_attack_finished` at 42/42 within 0.746–0.920 s, mean 0.828 s — is the **same measurement pooled across both declared speeds**, and the mean should not be quoted. Separately, **definition 1442 never sends a melee finish at all** (0 for 2 of 2 swings, and no agent of that definition anywhere in the corpus does), which explains two "unpaired swings" more simply than the interruption-by-death story that was offered for them.

### 3.6 Skill casting: n=1, and the caster is not a monster

**OBSERVED. n = 1 NPC skill activation in 21,543 messages, against 49 NPC `attack_started`.**

The one cast (A/2) is corroborated by a prediction that could have failed. Skill 83 resolves in the client's own tables to *Animate Bone Horror*; the client's table gives its activation as 1.0 s; **the observed activation-to-finish gap is 1.000 s**, and across all five casts in the corpus (one NPC, four player) the gap matches the table to **≤8 ms over two distinct durations** (1.000 vs 1.0; 2.000 and 1.992 vs 2.0). And the minion exists: at the exact millisecond of `skill_finished`, a **kind=9** agent is created with `EFFECT 0x1000` in the same instant, near the corpse; it walks 18 legs and is removed 0.196 s after its caster. A summon skill predicted a summon and one arrived.

Three properties of that finding matter more than the finding:

1. **The caster carries the `nonc` allegiance token.** Corpus-wide, no `nonc` agent ever appears as an attacker, as a target, or in any damage event — **0 in 21,543 messages.** For a study about monster AI, the one NPC cast in the corpus was performed by an agent class that never fights.
2. **The NPC's activation rides `0x009F` (int, no target); all four player activations ride `0x00A0` (int, with target).** Same value id, different message shape by actor. For anyone writing an NPC casting path, that is the most actionable byte in the finding.
3. **Nothing can be said about order, cadence or recharge.** No NPC casts twice. There is no second event to sequence against.

`GV_ADD_EFFECT` and `GV_REMOVE_EFFECT` (ids 6, 7) do not occur anywhere. A correlation scan for NPC-applied conditions on the player returns zero, but it is **uninformative**: every one of the 17 player-kind status events in the whole corpus carries the same value, `0x100`. The dependent variable is a constant, so the scan could not have found anything.

### 3.7 What a monster *is* — the definition record nobody read

**OBSERVED. n = 126 `NPC_UPDATE_PROPERTIES` (opcode 86) messages, 92 distinct (capture, definition) rows, 54 distinct definition ids; stability checked on 7 definitions × 4 connections × 2 captures = 20 rows, zero disagreement.**

The wire already carries a per-creature record: definition id, file id, **flags**, the byte `agents.py` calls profession, a **level** byte, an EncString name, scale and speed. The rows are **byte-stable across sessions three days apart and across different maps** — a per-instance record had every opportunity to drift and did not, which is what makes pooling them legitimate.

And the flags field partitions perfectly against the create's allegiance token:

| Token | Definition `flags` values seen | Creates |
|---|---|---|
| `mon1` (hostile) | 8, 13 | 233 |
| `band` | 12 | 37 |
| `anim` | 9 | 32 |
| `nonc` | 256, 521, 524, 525, 66048, 98816, 98820 | 244 |
| `play` | 524 | 39 |

Masking with `0x300`: **0 of 585 creates cross.** Every fighting token has bits `0x100`/`0x200` clear; every non-combatant token has one set. And `content/npcs.toml`'s hatcher — **the server's one and only enemy** — carries `flags = 0x20C = 524`, the most common non-combatant value and one no `mon1` definition ever takes. The rival (flags is a nameplate bitfield, the partition incidental) is not fully closed, but a single `mon1` create carrying `0x100` or `0x200` would have refuted it and there are none in 302 of them. **CLOSED 2026-08-11 — see §3.7.1. Every use the client makes of this field is a RENDERER or a UI PANEL, so the partition is real and its combat reading is not something the client can support.**

**The `profession` byte is not established as a profession.** It reads **11** on five definitions, against `agents.py`'s own `CHAR_PROFESSIONS_MAX = 6` (from 387 live samples) and GW's ten professions. It reads 2 ("Ranger") on the one model measured closing to ~65 units to melee, and 1 ("Warrior") on the burrowing worm that has no legs. And it cannot be cross-checked here: `AGENT_SET_PROFESSION` names **only kind=5 player bodies** — 234 of 234 targets with a create in the same connection, zero NPCs. The field name is ours, taken from an upstream as a lead.

**The level byte cannot be validated either, and there is a trap waiting.** Generic-value id 36 ("PublicLevel") takes the value **1 and only 1 on every NPC agent in the corpus** (kind 9: 9 events; kind 8: 18 events); all variation 2..20 is on player bodies. Pairing it against the definition's level byte yields 27 pairs, 8 "agreeing" and 19 "disagreeing" — **but both outcomes are forced, because every NPC sample is 1.** This is recorded here specifically so the next dive does not run that cross-check, see 8-for-8 on the non-zero subset, and promote the level byte. `content/npcs.toml`'s own caveat stands: *"a worm whose level reads 0 is at least as likely to mean the field is not a level as it is to mean the worm has none."*


### 3.7.1 The `flags` read, 2026-08-11 — every consumer is a renderer or a panel

**PREDICTION, stated before the disassembler ran:** the handler would store `flags` and
the bits would be tested elsewhere, for **display** reasons — nameplate, targetability,
minimap — and bits 8/9 would *not* branch into anything combat-named. The partition would
turn out to be a consequence of a display rule rather than a combat rule. **Refuted if** a
bit-8 or bit-9 test reached a combat-named branch, or an assert named the field with a
combat term.

**CONFIRMED, and more cleanly than predicted.** Nine sites read the field. Every one is
the renderer or a UI panel. Not one is combat, and not one is gameplay.

**The handler interprets nothing.** `0x0091dd80` copies seven message dwords into a
32-byte stack struct and calls `0x0080fa30`, which writes them into
`base[+0x7fc] + def_id * 48` under `Array.h:587 index < m_count`. Both are pure
marshallers. Whatever `flags` *means* is decided by the readers.

**Two parallel definition tables, dispatched on the id's top nibble** (`0x0080DEF0`,
ChCliApi):

```
and eax, 0xf0000000
cmp eax, 0x20000000   je -> monster table at +0x7fc, 48-byte rows  (lea edi,[ecx-0x20000000])
cmp eax, 0x30000000   je -> player  table at +0x80c, 80-byte rows
                      else -> assert ChCliApi:4325
```

**And the wire agrees, which is the cross-check that could have failed.** The create's
model field carries exactly those class bases: **585 of 585** joined creates are
`0x20000000`-based, the player's own create is `0x30000001`, and **48 of 54** definition
ids join under `- 0x20000000` against **0 of 54** under the identity. The neighbouring
assert `baseClass == CHAR_CLASS_PLAYER_BASE` names the other constant outright.

**`flags` is message field[6], so row offset +0x10.** Cross-confirmed by a source this
study did not write: `content/npcs.toml`'s worm provenance already records the mapping as
`[definition, file_id, 0, scale, 0, flags, profession, level, enc_name]`, read back
against the wire when that row landed.

**The readers, each attributed by its own asserts:**

| bits | site | module | what that module is |
|---|---|---|---|
| **9** | `0x007FD5B5` `test [+0x10], 0x200` | `AvChar` | `Gw\AgentView\AvChar.cpp` — the renderer. The branch ends in `AvChar:8212 seqIndex != SEQ_INDEX_UNDEFINED`: an **animation sequence** |
| **4, 5, 13** | `0x007FD7D5` `test [+0x10], 0x2030` | `AvChar` | on a hit, substitutes **row+0x14** into an appearance call |
| **8** | `0x00561E1F` `test [+0x10], 0x100` | `PtMinionRoster` | the minion-roster **panel** (`CtlFrameListGetItemFrameId`, `listFrame`) |
| **10** | `0x00570B62` `test [esi], 0x400` | `PtRoster` | the party-roster **panel** (`FrameTestStyles(ThisFrame(), ROSTER_STYLE_…)`) |
| **14** | `0x0056198F`, `0x00561E19` | `PtMinionRoster`, `CtlInstance` | panel plus UI control |
| **4, 5, 12** | `0x0081B372` | `ChCliBase` | decomposes the word and ORs three bits into `[esi+0x64]`; its calls land in **`AvApi`** — AgentView again |

`Av*` is AgentView, the render layer. `Pt*` are party-window panel frames. `Ctl*` is the
UI control library. **There is no seventh category.**

**The partition is really bit 9, not the `0x300` mask.** Re-counted from the corpus — 585
creates joined to a definition, **0 crossing**, reproducing §3.7 exactly:

| token | creates | flags values |
|---|---|---|
| `nonc` | 244 | 256(1), 521(13), 524(200), 525(2), 66048(4), 98816(16), 98820(8) |
| `mon1` | 233 | 8(226), 13(7) |
| `play` | 39 | 524(39) |
| `band` | 37 | 12(37) |
| `anim` | 32 | 9(32) |

Per bit, combatant tokens against the rest: **bit 9 is 0/302 against 282/283** — nearly a
perfect separator on its own — and **bit 8 is 0/302 against 1/283**, covering the single
remaining definition. So the `0x300` mask is bit 9 plus one straggler, and bit 9 is the
AvChar animation gate.

**What this settles, and what it does not.** It settles that *the client* uses this word
for display. It does **not** settle that the server means nothing else by it — the server
is what sends the field, and §2.1 is precisely the finding that the server's code is not
in this image. So the honest statement is: **the wire partition is a fact (585/585), and
the client's own use does not corroborate a combat reading of it.** §3.7's framing that
this read would "settle what the definition `flags` bits mean" was too strong; the client
can only answer for its own half.

**A correction to §3.7, and it is one of ours.** §3.7 noted that our hatcher carries
`flags = 0x20C`, "the most common non-combatant value and one no `mon1` definition ever
takes," with the implication that the row is wrong. **The row is right.** A Hatcher *is* a
Collector — a non-combatant — and `0x20C` is what ArenaNet declares for one. What the
observation actually shows is that **our test hostile is a non-combatant creature wearing
a fight**, which `content/world.toml` already says out loud ("A Hatcher is standing in for
a worm… this row exercises the CYCLE, not the creature"). Under this read it also means
our enemy renders in the townsfolk animation class, bit 9 set — a fixture consequence, not
a data defect. Nothing in `content/` needs changing.

**One thing this strengthens elsewhere.** §3.7 doubts that the byte we call `profession`
is a profession. The AvChar branch above consumes **row+0x14 — that byte — as a parameter
to an appearance call**, gated on flags bits. That is the client using the field for how a
character *looks*, which is evidence against the gameplay reading and was not available
when §3.7 was written.

**SCOPE, and the result contains its own proof that the scope is a floor.** `--xrefs`
finds direct `call rel32`/`jmp rel32` only, and caller windows were walked to the next
`call`/`ret`. **`ChCliBase`'s consumer at `0x0081B220` has no direct caller at all** — it
is installed as a callback (`mov dword ptr [ecx], 0x81b220` at `0x00824606`) — so the xref
method demonstrably under-reports, here, inside this very result. "Every reader is a
renderer or a panel" is therefore a statement about every reader **reachable by this
method**; an indirect or vtable path reaches none of it.

**Reproducing it**

```bash
python toolkit/clientscan/msghandler.py 0x0056 --follow --depth 1 --annotate
python toolkit/clientscan/codescan.py --field 0x7fc
python toolkit/clientscan/codescan.py --xrefs 0x0080DEF0
python toolkit/clientscan/asserts.py --at 0x00561DF0 --span 0x600
```


### 3.8 Death, corpses and loot — a whole system nobody asked about

**OBSERVED. n = 4 monster deaths; opcode 309 occurs exactly twice in 21,543 messages.**

Two of the four deaths produce a complete four-message loot burst *at the exact millisecond of the death flag*: an item record, **opcode 309 (item model, the killing player's agent, float32 600.0) — bit-identical both times and occurring nowhere else in the corpus** — an opcode 360 linking a new agent to the dying one, and a `WORLD_CREATE_AGENT` with **kind=0**, 25 units from the corpse. A single 309 away from a death would have refuted the reading; there is none. Drop *rate* is n=4 and uncharacterised (the two that dropped nothing are agent 40 and the worm).

Corpse persistence: 45.0 s in the one clean case (death flag to remove). The corpse is not inert — an agent re-created at t=79.186 in B/2, which the first pass called *"an unrelated fresh hostile spawn"* and its skeptic corrected to *"whatever it is, the bytes point at the same entity,"* is settled by a message both skipped: **`AGENT_INITIAL_STATUS` (opcode 240) carrying the DEAD bit, sent in the same instant — the only such message in the corpus.** It is a **visibility re-announce of a corpse and its loot** (the drop agent from that same kill is re-created 0.193 s later with a byte-identical payload at the identical position), not a respawn and not a resurrection. A respawn cannot announce an agent as already dead.

### 3.9 What the corpus does not contain, and therefore cannot answer

Each of these is a real zero over 21,543 messages, stated with what was searched:

- **No unprovoked-aggro measurement.** Four of five fights are player-initiated. The fifth (agent 41) bounds only to **1,197–3,634 units**, because its last commanded waypoint was issued 9.9 s earlier at patrol speed. An integration of its track at the measured 80 u/s puts it ~1,180–1,280 units out — that is three chained integrations with no anchoring waypoint, it is a **RECONSTRUCTION**, and the fact that it lands on our invented `AGGRO_RANGE = 1200` must not be quoted as narrowing the bound.
- **No disengagement**, ever. In the three engagements traced to a conclusion nothing is sent for the dying agent between its last attack and its death flag. The player always won decisively; there is no losing-monster and no player-walks-away case.
- **No two hostiles fighting the player at once.** The only connection with two player-facing hostiles has disjoint windows, 23.2 s apart. No group pull exists to observe.
- **No target switch, no respawn, no player death, no morale event.** `AGENT_UPDATE_ALLEGIANCE` (`0x002F`) is sent **0 times** — allegiance is never changed by that message (it can still change by re-create, which is common).
- **NPC-vs-NPC combat exists but is one skirmish**: 38 `attack_started` over 25 s, three participants — a `mon1` agent attacking a `band` agent twelve times while two `band` agents attack it thirteen times each. **No `band` agent ever shares a combat message with the player anywhere in the corpus.** That establishes a monster will target a non-player agent. It does **not** establish two hostile factions, and a scripted ally-NPC-vs-monster set piece is not excluded. The `band` and `anim` tokens are absent from `agents.py`, which carries `ALLEGIANCE_HOSTILE = 0x6D6F6E73` (`'mons'`) while every hostile here carries `'mon1'`.

### 3.10 Gw.dat carries none of this

**OBSERVED, and opened here for the first time in this arc. n = 698 MFT rows (349 map heads + 349 partners), every chunk in every row.**

No chunk in any of 349 maps carries spawn, patrol or behaviour data. The two candidate slots are empty or trivial: **Locations is a constant 9 bytes (Bloated) / 13 bytes (Stripped) in 349 of 349 maps**, and **Mission is 56–1,226 bytes (median 221)** of short ASCII name and link tokens (`next` in 88 maps, `town` 53, `prev` 17). Every large per-map chunk is geometry or render: Terrain, Props, Path, Zones, Shore, Sight, VisData.

**One slot of 23 remains inferred rather than measured:** Props (12–97 KB Bloated, 51–657 KB Stripped) is carried opaquely. If placements live in the archive they live there. Cheapest close: `mapexport` already reads prop positions for its orientation oracle — extend that read to histogram prop model ids for one map and check whether any lands in the `0x20000000` creature-class range the corpus uses. Separately, the **Sight** chunk (median ~60 KB per map, up to 478 KB, carried opaquely) is a candidate precomputed line-of-sight structure, and every discussion of LOS in this dossier went through `pathmap.clip()` without mentioning it.

---

## 4. What the wiki documents, and how load-bearing it is

**Result: GWW is the only source in this dive that supplies a numeric aggro radius, the only one that treats that radius as a per-creature field, and the only one with implementable rules for scatter, leash and formation. It is also community synthesis, mostly five to nine years unrevised, and it contradicts itself in two places. Treat it as a hypothesis generator with numbers attached, never as a fact about retail.**

**Label for everything in this section: WIKI (the project's slot for GWW; not UPSTREAM, and explicitly weak for internals). Revision ids given because currency is the failure mode.**

### 4.1 The number this dive was told did not exist

> **Earshot: 1012 gwinches, exactly the size of the aggro bubble, and the largest standard area of effect.** — GWW *Area of effect* §Earshot, rev2685457 (2023-03-31)

The identity chain closes across two further pages the first pass *did* fetch: *Danger Zone* (rev2647572) — *"The Danger Zone is more commonly known as the 'aggro bubble'"* — and *Range* (rev2720855) — *"Earshot … has the same radius as the Danger Zone."*

So **Danger Zone = aggro bubble = earshot = 1012 gwinches**, stated outright. It survives a check that could have failed: six independent relative statements on the *Range* page (1004 "very slightly smaller"; 1248 "just over 1.2×"; 1273 "approximately 1.25×"; 1498 "about 1.5×"; 2512 "roughly 2.5×"; half-range 624 at "0.6×") all land within about 1% of 1012, and three ratio statements on *Area of effect* (166 ≈ 1/6, 252 ≈ 1/4, 322 ≈ 1/3) agree.

The full range table, corrected: touch/melee **144**; half range for skills **624** (= half of spell range, which the wiki equivalently gives as 0.6 × the Danger Zone — *not* 0.6 × spell range); shortbow/spear **1004**; casting **1248**; hornbow/recurve **1273**; flatbow/longbow **1498**; spirit/binding ritual **2512**; some Nature Rituals **3500**; Soul Reaping gather **2508**; compass/party **5020**. AoE radii: adjacent **166**, nearby **252** (240 for a named anomaly set), in the area **322**, shout anomaly **1000**.

### 4.2 Aggro and leash are per-creature fields, said three times

- *"Some foes (Siege Wurms, Siege Turtles, Kournan Spotters) have a larger aggro bubble than the one displayed on the compass."* — *Aggro* rev2655578
- *"Very low level foes in starter zones have no aggro bubble at all."* — same
- *"Creating a large gap (the required distance depends on the foe)."* — same, §Breaking aggro

**For a server that has to store these as fields rather than constants, that is the most actionable statement in the angle.** Our `AGGRO_RANGE = 1200.0` is one number for every creature; the wiki says the default is 1012 and that named creatures differ in both directions.

Leash, same page: foes *"will only follow a certain distance **from where they took aggro**"* — the anchor is the aggro point, **not the spawn** — *"This distance is longer if the group was patrolling; if they were standing still or balling up, they can only be pulled a short distance."* And the return behaviour: foes *"break off and return to what they were doing before entering aggro."* No gwinch figure for either case. A second break condition exists with no distance threshold at all: *"Moving faster in relation to a foe until the foe breaks off,"* with a specific note that stacked speed boosts hitting the 34% cap break aggro faster than a single +33% effect even though the resulting speed is nearly identical — a rule keyed to boost magnitude rather than speed, and directly testable.

Aggro-gain rules: a miss, a block or a dodge still aggros; **an obstructed attack does not**. Damaging a minion or spirit aggros its controller. Corpses keep an aggro bubble. Same-type groups within *"slightly less than aggro range"* chain-aggro together. Pre-cast damage (e.g. Retribution) does not aggro, and instant-cast skills do not take aggro. Aggro is per-party: *"Until the entire team breaks aggro, everyone who took aggro will retain it, unless they die."*

### 4.3 Skill usage and targeting

> *"They each have a set of skills to which they are limited. The way they use these skills is embedded into the skill itself, so monsters with the same skills use them the same way."* — *Foe* rev2674584 (2021-08-29)

Three conditional **eligibility** gates are documented (spell-trigger skills only on targets wielding a caster weapon; Blind skills restricted by target weapon and further by game mode; condition-only skills used on condition-immune spirits). Corroborating the per-skill reading: *"Some monsters (such as Chromatic Drakes and Graven Monoliths) can change their set of skills. When that happens, their behavior also changes to match the skills."*

**This does not establish selection order.** A monster that filters by these gates and then picks in bar order, or uniformly at random among the survivors, satisfies every sentence on the page. The page also flags itself: *"Most monsters obey the same AI. A few of the principles are:"*

Targeting: *"two priorities of who to target: weakest foes (by health and armor rating) and closest foes … they only overpower each other at extremes; for example, they will target the characters with lowest armor rating but a tank can draw focus by body blocking them."* This is **n=1 page and uncorroborated** — the *Body block* page contains **zero occurrences of "aggro"** and never says a foe retargets onto the blocker; obstruction and target selection are different mechanisms. And the same wiki contradicts itself two pages over: *Aggro* §Shared aggro says the focus factors *"are not known,"* then lists seven as player inference. **CONTESTED within one source.** *Hard mode* adds a third factor the two-factor model does not contain: HM foes *"are less likely to ball around a single target if more targets are available."*

### 4.4 Scatter — the mechanic our server does not have, stated precisely

The trigger is **area damage over time**, not AoE generally:

> *"As a rule of thumb, all AoE skills that cause damage over time also cause scatter … AoE skills with a single packet of damage do not cause scatter … AoE skills that lack damage over time do not cause scatter, even if the effect could be reduced or avoided by scattering. Panic and Spiteful Spirit are prominent examples of this."* — *Scatter* rev2735452 (2026-07-23)

Implementable detail from the same page: **the whole group scatters simultaneously, cancelling current actions**; targets run **from the epicenter**, unless that path enters another scatter-causing skill; foes **cease all actions until they reach a safe location**; the rate is higher in Hard mode; and heroes/henchmen have the **same** scatter rate in both modes while foes do not.

### 4.5 Formation, patrol, bosses, mode

- **Formation** (*Body block*, rev2735440, 2026-07-23 — the most recently edited page in the set and a featured article): *"Melee enemies will attempt to surround a player and form a body block when initially engaging,"* counterable by strafing as they converge; and a *"protective semi-circle around their monk"* for two named factions. A convergence routine computed against the target's position at engage time is not producible by independent per-unit pathing.
- **Patrol** (rev2620395, 2017-07-13, Category:Unofficial terms): enemies on patrol *"stop moving if there is no player within roughly a compass range and a half"* when arriving at their next waypoint — i.e. roughly **7,530 gwinches** given compass range 5,020. The same page distinguishes three idle modes: patrolling, wandering in a small radius, standing still.
- **Bosses** (rev2692235): in Factions, Nightfall and EotN — **not Prophecies** — bosses deal double damage and have halved skill activation and recharge, plus +3 regeneration and (in Prophecies/EotN) *most* have Natural Resistance. Note halved activation and reduced recharge are **not boss-exclusive**: Hard mode gives them to all foes.
- **Hard mode movement speed is CONTESTED, n=2 pages disagreeing.** *Speed boost* (rev2658010, 2020-05-09) says foes *"move 33-50% faster than normal"*; *Hard mode* (rev2733192, 2026-07-05) says *"Move about 33% faster."* No source attributes the spread to foe type — that gloss was invented. **Pre-Searing has no Hard Mode**, so this does not bear on the campaign map, but it does bear on anyone borrowing the figure.
- **Non-standard AI**, explicitly *"specifically-coded exceptions"*: some Monk and Ritualist monsters kite; Siege Wurms are fully stationary; sprout Plants, Brooding Thorns and some Scarab Nest Builders are stationary but move under area damage over time; burrowing Wurms move only while burrowed and re-burrow after prolonged surface time or when no targets are in range; Glint, Kuunavang, Shiro Tagachi and the Undead Lich have unique AI. **Kiting is not Monk/Ritualist-exclusive** — *Hard mode* says foes generally kite more, and ball less, in HM.
- **Hero AI is a sibling, not a proxy.** Heroes have documented conditional, health-aware triggering, a target-lock hierarchy, and *"no reaction time; their interrupts are never late."* One patch note (2019-02-05) names *"Heroes, Henchmen, and monsters"* together; the 2026-06-24 one names *"martial heroes and pets"* only. **n=1 patch, not 2.** Both citations are `{{Outdated info}}` banners flagging the very section the healing rules are quoted from. And two mechanics are documented as diverging: scatter rate is mode-dependent for foes and not for heroes, and *"Heroes do not coordinate their actions with each other"* against the foe semi-circle. **A shared-engine inference is CONTESTED.**

### 4.6 How load-bearing is any of it

Three of the four core pages carry `Category:Unofficial terms`. *Foe* has not been revised since **2021-08-29**, across at least one AI patch; *Patrol* since **2017**; *Movement* since **2020**; *Area damage over time* since **2013**. Where a stale page and a fresh one disagree — *Movement* 2020 vs *Scatter* 2026, *Speed boost* 2020 vs *Hard mode* 2026 — the stale one gives the looser, wronger statement both times.

**Verdict on load-bearing:** the gwinch table is a set of *values* and can seed content rows with `source = "wiki"`. The scatter, leash, targeting and formation descriptions are *algorithms*, and under this project's own rule (`CLAUDE.md`; `PLAN.md` §6.1) **a derivation-register row must exist before any module takes an algorithm or a table from an upstream**. The register was read in full for this dive: thirteen rows, **none touching combat AI, aggro, targeting or skill selection.** That row has to be written first, and the repo angle's framing of the wiki output as "bare values" understated what would actually be borrowed.

---

## 5. What our server currently invents

**Result: every constant and policy is already honestly self-labelled at its call site — I found no comment that overclaims its evidence. That is the good news and it is also the whole defence, because twelve of fourteen of these values can be silently changed to something wrong and the entire 125-check suite stays green.**

The coverage figures below were produced by **sabotage**: patching the module global one at a time (equivalent to editing the literal, since both the server function and the test read it at call time) and re-running `test_agentlife.py`.

| Constant | Site | Value | Provenance | Sabotage result |
|---|---|---|---|---|
| `ATTACK_RANGE` | `authsrv.py:1100` (one call site, `:1296`) | 1500.0 | Ours | → 10.0 **green** |
| `AGGRO_RANGE` | `authsrv.py:1119` | 1200.0 | Ours | → 1100.0 **green** |
| `ENEMY_MELEE_RANGE` | `authsrv.py:1147` | 150.0 | Ours | → 400.0 **green** |
| `ENEMY_HIT_FRACTION` | `authsrv.py:1120` | 0.10 | Ours | → 0.20 **green** |
| `HIT_FRACTION` | `authsrv.py:982` | 0.15 | Ours, legibility | → 0.5 **green** |
| `REVIVE_AFTER` | `authsrv.py:983` | 8.0 | Ours, legibility | → 900.0 **green** |
| `PLAYER_REVIVE_AFTER` | `authsrv.py:1121` | 10.0 | Ours; mechanism UNVERIFIED, n=0 player deaths | → 60.0 **green** |
| `SWING_WINDUP` | `authsrv.py:1136` | 0.899 | OBSERVED — **and refuted as a constant**, §3.5 | → 0.2 **green** |
| `ENEMY_MOVE_RATE` | `authsrv.py:1148` | 0.75 | Ours; never sent to a hostile in the corpus | → 0.4 **green** |
| `ENEMY_DEST_RESEND` | `authsrv.py:1150` | 120.0 | Ours | → 300.0 **green** |
| `ENEMY_FACING_EPSILON` | `authsrv.py:1175` | 0.15 rad | Ours, bandwidth throttle | → 0.01 **green**, → 1.0 **green** |
| `ENEMY_SKILL_FRACTION` | `authsrv.py:1240` | 0.25 | Ours, flat on purpose | → 0.5 **green**; only bound is `> ENEMY_HIT_FRACTION` |
| `ENEMY_MAX_HEALTH` | `content/world.toml:13` | 100 | Ours, placeholder | → 555.0 **green** |
| `ENEMY_ATTACK_SPEED` | `authsrv.py:960` | 1.33 | Arbitrary non-zero placeholder | → 2.7 **green** |
| `ENEMY_SKILL_BAR` | `authsrv.py:1236-1239` | ids 276/253/312/289 | Fields SOURCE-CODE; **selection invented**; testing fixture per owner's ruling | typo'd activation **and** recharge **green** |
| **`ENEMY_TURN_RATE`** | `authsrv.py:1174` | 2π/3 | **CORROBORATED** — ArenaNet's own quantised maximum, bit-identical | → 1.0 **RED**. The only one. |

`ATTACK_INTERVAL = agents.ATTACK_SPEED['hammer'] = 1.75` (`authsrv.py:208`, `:1099`) deserves its own line: the base × modifier **formula** is CORROBORATED (the client's own `fmul` at `0x007F837E` reproduces GWW's IAS table 6 for 6 to four decimal places), but **no value 1.75 is read out of the binary anywhere** — the rate table is `source = "wiki"`, and the second lineage cited for it (GWCA) corroborates only the axe/sword/dagger 1.33, which this constant does not use. **Formula CORROBORATED; value UPSTREAM, n=1 source.**

Policy and structural gaps, all explicitly documented at their sites except the last:

- **`pick_skill` round-robin** (`:1760-1799`) — invented; owner's ruling makes it a fixture. The *defect it replaced* is a real measured fact: first-ready-in-bar-order left slot 4 unreachable, measured `{276:6, 253:3, 312:3, 289:0}` pre-fix against `{3,3,3,3}` post-fix, n=1 loopback run each.
- **"A cast in flight beats everything"** (`:1499-1506`) — a scheduling-safety invariant about our own tick granularity, not a transcription of ArenaNet's priority rule, and the corpus cannot arbitrate (one NPC cast, in a different connection from any NPC melee).
- **Recharge from cast start** (`:1521-1525`) — **RECONSTRUCTION** from the client's static table semantics. No live NPC recharge cycle exists to distinguish start-triggered from completion-triggered.
- **No leash home** (`:1638-1651`) — and it is worse than documented: `spawn_enemy` (`:2249-2270`) stores no spawn anchor at all, so a leash is **uncomputable from the state the server keeps**. Adding one is a state change, not a branch.
- **No pathfinding** — `pathmap.route()` (a working A* with string-pulling) exists and is called from nowhere; `clip()` is used only on the per-tick step segment.
- **No line of sight** — the reach gate (`:1477`) and the chase gate (`:1639`) are pure `math.hypot`. `clip()` could serve as an *approximate* LOS test (`clip(a,b) == b`) with two error modes its own docstring names: it answers walkability, not visibility, and at 16-unit sampling it sees through any obstacle thinner than the step.
- **No energy, no interrupt, no aftercast.** `skilltable.py` already decodes energy (`+0x35`), adrenaline (`+0x38`), aftercast (`+0x40`), activation (`+0x3C`) and recharge (`+0x4C`) for all 3,443 rows. **Interrupt and aftercast are wirable today with no new capture. Energy is not** — the cost is client-readable but the pool it is spent from is one of `PLAN.md` §1.7's four genuinely server-only categories.
- **Enemy skills are single-target only** (`land_skill`, `:1802-1841`, hardcodes the player's agent id) — **and this is the one simplification in the file that carries no flag.** A case-insensitive search of all 4,626 lines for `aoe` / `single target` / `area of effect` / `splash` returns zero. Every other equally-implied simplification in the same functions does get a callout.

### 5.1 Errors found in the repo, to be fixed

1. **Skill 276 is ELITE.** Its flags word has `FLAG_ELITE` (0x4) set. `authsrv.py:1226-1228` and `studies/enemy/PLAN.md:2795-2796` both assert all four bar skills are "campaign 1, non-elite," and the repo angle repeated it as evidence. The "21 qualifying candidates" census reproduces exactly under profession 3 + campaign 1 + non-elite + recharge > 0 — **and skill 276 is not a member of it.** (Decode sanity-checked first: 307 elites in 1,333 corpus rows, spread 36/36/36/37/35/36 across the six core professions.) This is precisely the defect the missing cross-check predicts, and it had already happened.
2. **A stale, overclaiming comment at the selection call site.** `authsrv.py:1518-1522` still reads *"FIRST READY IN BAR ORDER, which makes the bar a priority list — roughly what a Guild Wars monster does."* The selector became round-robin, and `pick_skill`'s own docstring twenty lines below says nothing in this project knows how a Guild Wars monster chooses.
3. **A citation naming the wrong capture.** `authsrv.py:1189` places the single NPC skill activation in capture B. It is in **capture A**, connection 2. The connection identifier in the same sentence is correct; only the stamp is wrong. (`test_agentlife.py`'s sibling docstring cites no stamp, so only the one site needs correcting.)
4. **Stale burrow counts.** The instrument prints emerge n=**137** in [1.976, 2.021] and submerge n=**132** in [1.973, 2.037], over **140** worm creates across 13 worm ids. `content/world.toml:52` says "n=132 each way," `authsrv.py:2079` says "151 worm re-creations," `CLAUDE.md` says 140. The 2.00 s transition constant itself is genuinely pinned against a literal in `test_burrow.py` with a mutate-and-restore control — the strongest pinning in the whole combat surface.

---

## 6. What was REFUTED — do not rebuild these

The refutations are the valuable half of this dive. Each entry names the killed claim, why it died, and what would have had to be observed for it to live.

**From the client binary**

1. **"The client's real AI vocabulary is 8 identifiers and they all name hero/henchman control, proved by co-location with `hero`."** REFUTED. `GmPetCommander` returns 12 assert sites and **not one mentions `hero`**; `ChCliApi:4331`'s `mode < CHAR_AI_MODES` sits between a `baseClass` check and a hotkey bound check, a generic character-API neighbourhood. The shared-enum rival the claim declared beaten is exactly what the naming argues *for*. See §2.2.
2. **"`GAME_SMSG 38` carries `DESTROYING`, `IN_WORLD`, `MOVEMENT_STALE` and `INVISIBLE`."** REFUTED by the claim's own citations: those bits are 16, 17, 19 and 1, and the setter keeps bits 16–21 at their old value. Three of the four named flags are precisely what that message **cannot** set.
3. **"Zero AI/monster hits in the message catalog."** REFUTED — a check that could not fail (`messages.json` has no `name` fields at all). Three hits exist in `overrides.json`, one of them `NPC_UPDATE_PROPERTIES`.
4. **"The fixed compass circle is what you'd expect if the aggro rule lives server-side."** UNVERIFIED as an inference — affirming the consequent. A client that holds the number and draws a constant produces the same observation. The string negative (no `aggro`/`danger` anywhere, now including `.rsrc`) is real; the inference is not.

**From ArenaNet's traffic**

5. **"Distance at the player's opening attack is 935–2077 units."** REFUTED. The 2077 figure reproduces exactly as the length of the leg the player walked to reach that monster; the player then abandoned that waypoint for a follow. Distances measured from the client's own self-position stream are ~1,166 u and ~1,700 u for two cases — and they measure *where the player clicked*, which is not a range at all.
6. **"Monsters strike from 269–1594 units, every case ≥1.8× our 150."** REFUTED. All four numbers reproduce exactly with the stated method — the failure is in the model, not the arithmetic. It pooled three creature models and used zero-order-hold position estimates while two direct oracles sat unread. Corrected in §3.3: ~65 / ~599 / ~706 by model.
7. **"Two independent methods (hold and interpolation) agree EXACTLY."** REFUTED as a check. For an agent that has reached its waypoint the two methods are identical by construction. **A check that cannot fail is not a check** — and the case cited as the strongest agreement is exactly that case.
8. **"`0x0025` is never sent for a non-player and 260 of 260 target the player's own agent."** REFUTED as stated: 593 corpus-wide, and in the outpost connections they name up to 10 distinct *other* player bodies. The restriction to explorable connections was carried into a corpus-wide claim. The *inference* also fails: NPC movement rides `0x002A` as well as `0x0029`, and `0x002A` was never scanned.
9. **"The jump to speed 1.0 coincides with closing on the player."** REFUTED — one of four such jumps closes on other NPCs, one moves away from a distant player. Also, the 23-agent histogram merges two entities on one re-used agent id; strict count is 22 agents / 26 messages.
10. **"Patrol destinations sit far from the player while chase destinations converge."** REFUTED for its own example: under the stated method, one of agent 41's *patrol* destinations is 4% **closer** to the player than its chase destination. The quoted 1200–4400 band only appears if follow messages the report says it did not scan are folded in. Also contaminated: the "never engaged" list includes the fifth player fight, whose small distance is a *chase*, inverting the argument it is used for.
11. **"Agent 43's reappearance is an unrelated fresh spawn (kind 9→8 proves a different entity)."** REFUTED by its own bytes — same model, same allegiance, the exact death coordinates. And settled in §3.8: an `AGENT_INITIAL_STATUS` carrying the DEAD bit in the same instant makes it a **corpse-and-loot visibility re-announce**.
12. **"Reaction latency is 3.534–5.695 s, mean 4.71."** REFUTED. A value-4-only scan systematically misdates any fight opened with a skill; that opening is a value-50 activation 2.5 s earlier in one case. Corrected range 3.534–8.178 s, n=3, and the definition is unstable by up to 11.5 s.
13. **"A marker sequence (GV 11/12) is a notice/engage signal preceding a hostile's first attack."** REFUTED three ways: the agent traced carries the **`nonc`** token, it **never attacks anything ever** (so "before any attack" is vacuous), the event count is 12 not 18, and the dispatch-table support does not discriminate because nearly every id 0..66 has a case body including ids that never appear on the wire. The corpus-wide half survives: ids 11/12 are NPC-exclusive (89 and 38 events, 0 on any player), values `{3,4,5}` and `{0}`. The **meaning is UNVERIFIED.**
14. **"Two unpaired swings are explained by interruption-by-death."** REFUTED by a simpler rival that explains both plus a third: **definition 1442 never sends a melee finish at all**, 0 for 2 of 2, and no agent of that definition anywhere does.
15. **"No NPC applies a condition to the player."** REFUTED as a *check* — the dependent variable is a constant (all 17 player status events carry `0x100`). NOT FOUND, and the corpus cannot answer either way.
16. **"Two hostile factions fight each other."** WEAKENED to: one `mon1` agent attacks non-player agents. Three participants, not four or six; agent 41's only attack in the entire corpus targets the player; and `band` is never hostile to anything but `mon1` in any observation. A scripted ally-NPC encounter is not excluded.
17. **"kind=8 is the summoned minion."** The kind=8 census is right and the minion conclusion is wrong in effect — **the minion is kind=9 and is in the corpus**, created at the exact millisecond of `skill_finished`. Searching only kind=8 and reporting the question closed is the same failure shape as every confident zero above.
18. **"GV 36 corroborates the definition's level byte, 8 of 8 on the non-zero subset."** Recorded here **pre-emptively as refuted**: every NPC sample of GV 36 is 1, so both outcomes are forced and the comparison carries no information.

**From the wiki**

19. **"GWW gives no aggro-bubble radius; the binary and packet corpus must carry that weight alone."** REFUTED. 1012 gwinches, stated outright on a page that was never fetched, found with one search. The derived 1005–1040 bracket that stood in for it is also unsound: it used 2 of 6 available relative statements, and the flatbow figure implies 998.7, **below its own stated floor**.
20. **"Foes move away when they are the target of an AoE skill."** REFUTED by GWW's own dedicated article: **damage over time** is the trigger; single-packet AoE does not scatter, and Panic and Spiteful Spirit are named counterexamples. The corroboration the claim cited (Plants moving under area damage over time) is a *link to the DoT-specific mechanism* and works against it.
21. **"Body block corroborates the weakest+closest targeting rule."** REFUTED — that page contains zero mentions of aggro and never says a foe retargets onto a blocker. n=1 page, not 2, and the same wiki says elsewhere the factors are not known.
22. **"Two patches changed AI for Heroes, Henchmen and monsters together, implying a shared engine."** REFUTED — only the 2019 banner names monsters; the 2026 one names martial heroes and pets. n=1 patch note. And two mechanics are documented as *diverging* between heroes and foes.
23. **"Foes move 33–50% faster in Hard mode, varying by foe type."** CONTESTED — a newer page says "about 33%", and no source attributes the spread to foe type.
24. **"Kiting is a Monk/Ritualist-only carve-out."** WEAKENED — HM foes generally kite more.

**From the repo**

25. **"`ENEMY_MELEE_RANGE`, `ENEMY_HIT_FRACTION`, `AGGRO_RANGE` and `ENEMY_SKILL_FRACTION` are pinned."** REFUTED by running the sabotage rather than reasoning about it: all four pass at wrong values. A symbol appearing in a test file is not a check when the expectation is computed *from* that symbol.
26. **"All four `ENEMY_SKILL_BAR` skills are non-elite."** REFUTED — skill 276 carries `FLAG_ELITE`. See §5.1.
27. **"`SWING_WINDUP` cannot be settled; neither vaulted capture has a second declared speed."** REFUTED — the second capture is a four-NPC brawl at two declared speeds and it was already in the vault when the constant was adopted. See §3.5.
28. **"`begin_attack` performs a range check."** REFUTED — it does not; `ATTACK_RANGE` has exactly one call site.

---

## 7. The route: how to settle what is unsettled

### 7.1 Build the clock binding first, or the whole campaign is un-analysable

**OBSERVED, and it is a blocker.** `wirecapture.open_capture` stamps every segment `perf_counter() - t0`, with `t0` taken **inside the sniffer subprocess** after WinDivert opens; the `wire_meta` line carries client, server, pid and ports and **no time**. The only other clock in the artifact is `manifest.json`'s `stamp`, a `strftime` taken in the parent **before that subprocess is spawned**. So a narrated live session can today be aligned only post-hoc, to within seconds, off server anchors — which is exactly the gap-inference failure `labelrun.py` was written to end.

The fix is **dual**, because either channel alone is unchecked:

- **In-band:** the operator types short chat lines (`GAME_CMSG 100 CHAT_SEND`), which land on the same stream at the same clock and carry their own recognisable plaintext — the idiom `labelrun.py`'s `chat_say` step already uses. **n=0 live evidence**: `CHAT_SEND` appears **zero times** in capture B's 500 client messages. That is why it is **step 0 with a stated prediction**, not an assumption. If zero chat messages reach ArenaNet's game channel, the in-band channel does not exist and the analyser must **say so** rather than proceed on an unchecked binding.
- **Out-of-band:** a new `marks.jsonl` written by the driver, each mark recording both `perf_counter()` and the `t` of the last record then present in `wire.jsonl`.

The analyser requires the two to agree **in order** and reports the measured per-mark skew. The rival — "`perf_counter()` is QPC-derived so one file is enough" — loses on CPython's own contract (the reference point is undefined; only differences within one call site are valid) and on this project's rule that a fixture silently resolving to the wrong thing turns every assertion behind it into a no-op.

Two independent clocks already exist to *check* such a binding: the client's own self-position at median 0.501 s, and `0x001E`, whose payload summed across a tape reconstructs that tape's own wall clock to **+18 ms worst case over 13–185 s**.

### 7.2 The operator script — blocks, with free play between them

The session must read as ordinary play. Two or three blocks, 25–40 minutes total. **Every step is a sentence printed to a terminal that a human reads and acts on. The driver sends no keystrokes and no clicks — that is the rule that matters and no guard substitutes for it.**

| # | Step | Duration | Why this shape |
|---|---|---|---|
| 0 | `mark_smoke` — type two short chat lines | 30 s | settles whether the in-band mark channel exists at all |
| 1 | `idle_a` **CONTROL** — stand still in sight of a creature, hands off | 45 s | ambient-patrol measurement; the only thing that can answer whether monster movement correlates with the player at all |
| 2 | `approach` — pick an untouched creature, close in **bursts of ~1 s running then ~3 s standing**, stop the instant it reacts | 90 s | forced by measurement: self-position arrives at median 0.501 s / p90 1.769 s, i.e. **144 u median and 509 u p90 of travel between fixes**. A 50% error band cannot discriminate a per-creature radius from a global one. A monster that reacts while the player is **standing** gives a point measurement; one that reacts mid-burst gives a bracket the operator sized. |
| 3 | `retreat` — do not fight it; run straight past where you started until it stops following; stand 10 s | 60 s | the disengage question, which the entire existing corpus cannot speak to |
| 4 | `idle_b` **CONTROL** | 30 s | second ambient sample |
| 5 | `kill` — a third creature, fought to death while standing still | 120 s | windup at a third declared speed; drops; corpse timing |
| 6 | `narrate` — one chat line per unexplained thing seen | 30 s | settles `band`/`anim` in one session |
| 7 | `play` — unconstrained, **not used for attribution** | 3 min | makes the session a session |

**The control predicate must be redefined for live, and getting it wrong voids a run in the opposite direction from `labelrun`'s original bug.** On our own server a control window predicts *no traffic*. Against ArenaNet the world keeps talking — `0x001E` alone is **6,928 messages**, roughly a third of the server stream — so a "no traffic" predicate would redden in every control window and a check that always reddens is as useless as one that never does. The live control is a predicate on the **client half only**: zero player-action opcodes (38, 39, 57, 61, 62, 70, 193) in the window, with 9 and 146 permitted and counted.

### 7.3 The analyser: `toolkit/authsrv/behaviourrun.py`

Sibling to `labelrun.py`. Consumes a live capture stamp plus its `marks.jsonl`. **Reuses** `tape.load_tape` + `tape.decode_all` (whole-stream, byte-accounted), `cmsgstream.timed(stamp, 'c2s')` (masked and timed), `origin.origin_of`, `agents.py`'s vocabulary and `checks.Ledger`. **Emits** per-step windows over both directions and an encounter table keyed by **(connection, model_id, agent_id)** — every row carrying its model id, because pooling across models is what produced the refuted range band.

Nine checks that can go red:

1. `origin != live` is a refusal.
2. `decode_all`'s `receipt.consumed == receipt.total` per connection.
3. The tick clock and the wire clock agree — `0x001E` integral vs wire span, within the 50 ms bound `test_smsgnames.py` already uses. **Run this against the two existing captures before a single new session**: if it reddens there, the wire-clock-to-plaintext mapping everything already relies on is broken and every timed claim in the repo is suspect.
4. In-band chat marks and `marks.jsonl` agree in order; per-mark skew reported.
5. Every CONTROL window carries zero player-action client opcodes.
6. **An encounter whose subject moved and has no direct positional sample is UNRESOLVED, never estimated.** Qualification rule: a subject is measurable iff it sent **zero** `0x0029`, **zero** `0x002A` and **zero** `0x002B` between its create and its first reaction, in which case its position is exactly its create coordinate. This refusal exists because estimation produced four numbers, two of them wrong by 481 and 1,594 units.
7. No number printed pooled across model ids.
8. Reforged flag present, or stat rows withheld (see below).
9. A `Ledger` floor set from a real green run.

`toolkit/authsrv/test_behaviourrun.py` lands **in the same commit** and is added to `CLAUDE.md`'s suite list in that commit. It builds its fixture synthetically (no vault), and the defect it must be able to catch is `labelrun`'s own: a mark written *after* the prompt steals the first message of a step and hands it to the previous one.

### 7.4 Map choice is split

- **Aggro, leash, movement, reach, windup, corpse persistence, drops:** Lakeside County and Green Hills County. Solo, low density, low risk, and this project's content is already there.
- **Skill-selection policy: NOT the Catacombs.** Its nine permanent residents have **zero base skill bars between them** — a session there would yield zero monster casts and read as "monsters do not cast," which is false. The ambient base-mode creatures with a bar of ≥2 are **16 region-wide** (of 91 hostile types: 49 with no bar, 11 with exactly one, 31 with ≥2 of which 13 are Vanguard-quest-only and 2 Reforged-gated) and are concentrated elsewhere — Carrion Devourer (6 skills), Grawl Shaman (3), Bandit Firestarter (4), Charr Hunter (3), River Drake (3), Charr Blade Storm (3), Vatlaaw Doomtooth (3). **UPSTREAM**, via `studies/presearing/MANIFEST.md`'s re-read of the pages.
- **The single best subject for separating a casting policy from an attack policy is the Aloe Husk / Aloe Seed pair:** documented non-combatants that never attack even in retaliation, and that nevertheless carry Healing Breeze and Shielding Hands.

**Record the Reforged Mode flag in `marks.jsonl` and refuse to emit stat rows without it — and prefer running with it OFF.** It reduces enemy health by 20% and armor by roughly 20%, **changes the AI** (faction-conditional hostility), and adds creatures. It is toggleable after character creation, so it is a per-session property. A capture taken in Reforged Mode yields numbers 20% off base and perfectly self-consistent — the exact failure shape this repo keeps paying for. `origin.py` cannot disambiguate it. **This is a check the artifact can fail:** a computed max health landing within 1% of 0.8× GWW's published figure means the flag was recorded wrong.

### 7.5 One instrument worth naming: absolute monster max health from the wire

**RECONSTRUCTION, and it contradicts `PLAN.md` §1.7's placement of monster HP among the four genuinely server-only things.** Damage on the wire is a fraction of the **damaged** agent's own maximum (13/13 against 0/13 for the rival slot). **Life stealing ignores armor and damage reduction entirely and steals a fixed published amount.** So one life-stealing skill cast at a **full-health** monster gives `monster_max = steal / f`.

What makes it a measurement rather than an arithmetic trick: **two different life-stealing skills of different published amounts, on the same creature type, must agree.** A third witness exists — GWW publishes Pre-Searing creature health. Two constraints: the damage channel **floors at 1 and cannot kill**, so a steal exceeding remaining health is clamped and must be discarded; and the character must actually carry such a skill. **Refuted if** two skills disagree beyond float precision — then either the fraction reading or the published steal figure is wrong and the instrument is dead.

§1.7's statement is about what the **client exposes** and it is correct. It says nothing about what a fraction on the wire, divided into a known absolute, recovers.

### 7.6 The ranking

| Tier | Question | What it costs |
|---|---|---|
| **Cheap** (1–3 sessions, high confidence) | Whether unprovoked proximity aggro happens at all, and its per-creature bracket; the leash outcome class; patrol vs player-correlation of ambient movement (**free by-product of every control window**); the speed-fraction vocabulary and what actually triggers 1.0; windup vs declared speed at a third speed; reach per model; corpse persistence and drop rate; the identity of `band` and `anim`; absolute max health for creatures GWW publishes | one clean encounter per creature ≈ 90 s |
| **Many sessions** (5–10, yield not guaranteed) | Skill-selection policy; target selection among several friendly bodies (**needs a pet or an escort NPC — a solo character has exactly one body**); scatter (needs a character carrying an area damage-over-time skill); interrupt and aftercast behaviour | each needs a rare creature property, a second friendly body, or a specific build |
| **Cannot be settled by any capture** | **AI as a mechanism** — the decision function, its inputs, its tick, its internal state; monster **energy** (cost is client-readable, the pool is not); anything about **Hard Mode** (Pre-Searing has none); **armor** (inferred from damage, never sent) | — |

The impossible tier's floor should be stated as a floor: the srctree zero is a real negative from a detector proven able to fire, but 431 shared-tree files the server also compiled remain, and six of the eleven `Engine\Map\Path` modules have now been read (pure geometry, and a dynamic-obstacle radius). **Refuted if** a disassembly pass over the remaining five finds steering or pursuit code, which would move movement policy out of that tier.

**The leash step is worth a whole step because all three outcomes are findings:** (a) the subject sends a move whose destination lies back toward its create position — leash-home is real and our documented gap is genuine; (b) it stops where it stands — our behaviour is **correct** and the documented gap is not one; (c) it never stops — there is no leash. The subject must be aggroed by **approach**, not by being attacked, so the anchor is its create position rather than a fight location. (GWW anchors leash at *where aggro was taken*, so outcome (a) has two sub-shapes and the analyser must report which.) If the subject follows to the zone edge, that is **UNRESOLVED**, not outcome (c).

**Skill policy: state the stopping rule before the first session, because the cheap way to get n is exactly the behaviour that closes accounts.** Discriminating round-robin from priority order from least-recently-used needs roughly 30 casts per creature type spanning ≥2 skills with overlapping readiness; a 4-skill bar yields perhaps 3–8 casts per fight. That is 5–10 fights per type, **spread across sessions, on different individuals in different parts of the map**. The observable is the cast histogram across slots plus inter-cast interval against each skill's own recharge. **Grinding one spawn point is REFUSED, not refuted** — no analyser result is worth the account. A finding falls out on the way: a creature casting the same skill twice **inside** that skill's published recharge would mean monsters do not obey the player recharge table, and the whole policy question changes shape before any histogram is worth building.

### 7.7 Sessions and stopping rules

Six to ten sessions of 25–40 minutes, **at most one per day, at human hours, over two to three weeks, secondary account, one client**. `livesession.py` already enforces the cheap structural half (one live client, a `--minutes` ceiling, `--confirm`). Per-question stopping rules, fixed in advance so nothing is rationalised into agreeing afterwards:

- **Aggro range** — 10 clean point measurements (subject stationary since create, player stationary at trigger) across ≥3 creature types, or 6 sessions, whichever first.
- **Leash** — 6 disengagements across ≥2 creature types.
- **Windup** — as soon as a third declared attack speed is sampled with n≥8.
- **Health** — two life-stealing skills agreeing on 3 creature types GWW publishes.
- **Skill policy** — 30 casts on one creature type, or 8 sessions; then **report the shortfall rather than a histogram over n=6**.
- **Hard behavioural cap, overriding all of the above:** no more than 3 approaches on the same creature type per session, no repeated visits to one spawn point.

### 7.8 Refused outright

Scripted keystrokes or clicks against ArenaNet in any form, including a "gentle" movement-key-only version — the loopback harness's three-Enters-and-a-Play-click is precisely the pattern the rule exists about. A second client or second account for the two-friendly-bodies test (a charmed pet or an escort NPC is the legitimate substitute and is ordinary play). A MITM proxy — the channel is DH-keyed end to end and a proxy holds neither exponent. Spawn grinding. Reforged Mode. And **zero-order-hold or interpolated position estimates for a moved hostile** — that is what produced the four refuted range numbers.

### 7.9 Four desk follow-ups that need no capture at all

1. ~~**Read the immediate at `0x0080dfae`** — the cardinality of `CHAR_AI_MODES`.~~ **DONE 2026-08-11, and it closed as UI.** 3, across five bound sites; two independent three-arm switches; `AI_MODE_ICONS` also 3; `CHAR_AI_MODE_AGGRESSIVE` = 0; and the modes resolve to **Fight / Guard / Avoid Combat**. Every step could have refuted the prediction and none did. §2.2.1.
2. **Read the remaining `Engine\Map\Path` modules** — could move movement policy out of the impossible tier.
3. **Histogram Props-chunk model ids for one map** — closes the last of Gw.dat's 23 slots.
4. **Run `msghandler.py` on opcode `0x0056`** — settles what the definition `flags` bits mean, from the client's own use.

---

## 8. What to do in the meantime

**The approximation must be visibly one, and today it is only visible in comments. Make it structural.**

### 8.1 AI policy belongs in `content/ai.toml`, not in `authsrv.py`

`content.py`'s own rule places a fact about the *world* in content and a fact about the *client* in `agents.py`. AI policy is a fact about the world and is exactly the thing you want to author per creature. Moving it does three things at once:

1. Every number carries a **load-enforced** provenance label instead of a comment.
2. Values become **per-creature**, which is the substantive correction — one global reach constant is refuted by a corpus showing ~65 and ~600 for different models, and no annotation can fix that.
3. An approximation becomes visibly swappable.

Proposed row per creature: `aggro_radius`, `leash` (`none` | `stop` | `home`), `move_rate_patrol`, `move_rate_chase`, `reach`, `windup_ratio`, `skill_policy`, `max_health` — each with `provenance = {source, verified, note}` drawn from the existing `SOURCES` vocabulary, which already contains exactly the four rungs needed:

> **`capture`** (observed on ArenaNet's wire, per model id) > **`client-table`** (activation, recharge, energy, adrenaline, aftercast — already decoded) > **`wiki`** (GWW's published bars, health, armor, and the 1012 default) > **`invented`** (*"ours, chosen rather than observed. Says so out loud."*)

**An `invented` AI row must name, in its `note`, the observation that would replace it.** `world.toml`'s existing spawn provenance block is the working precedent and already does the harder half in prose — separating the measured 2.00 s burrow transition from the invented out/hidden durations, and explaining why the measured pair deliberately did *not* come to the content file.

**Refuted if** a value turns out not to be authorable per creature — i.e. if the campaign shows reach and aggro radius are properties of the **server's tick** rather than of the creature, in which case they are protocol vocabulary and belong in `agents.py` instead.

### 8.2 Separate capability from policy

Derive what a monster **can** do from the client's own table plus GWW's published bars, and keep it in a layer separate from **when** it does it. `skilltable.py` already gives activation, recharge, energy, adrenaline and aftercast for 3,443 rows of build 38797; GWW publishes bars for 31 of 91 Pre-Searing hostile types. That is a capability model with **no live capture at all**, and it makes the campaign's job strictly smaller: the only thing left to observe is *when*.

The prediction that makes it a measurement rather than a transcription: **an observed monster cast's activation duration must equal the client table's activation for that skill.** The existing corpus already gives 5 of 5 to ≤8 ms across two distinct durations. The one carve-out remains energy.

### 8.3 What tests would actually pin this

Three, and each catches a defect that has already occurred:

1. **Assert against literals, not symbols.** `test_burrow.py` is the model — `TRANSITION_SECONDS = 2.00` in the test file, compared to the constants, with a mutate-and-restore control. Twelve of fourteen combat constants currently derive their expectation *from* the value under test. A section that names each constant's intended value as a literal turns twelve silent changes into twelve red checks.
2. **Cross-check `ENEMY_SKILL_BAR` against `skilltable.py`'s live read of build 38797.** Nothing does. It would have caught the elite error, and it catches a typo'd activation or recharge, both of which currently pass.
3. **A content-provenance check:** every `ai.toml` row carries a `source` from `SOURCES`, and every `invented` row's `note` is non-empty and names a refuting observation. `content.py` already refuses unlicensed-upstream rows without a `verified` string; this is the same shape one rung further.

And set the `Ledger` floor from a real green run of the new sections, never from a guess.

### 8.4 Corrections to land alongside

Fix the four errors in §5.1 (the elite skill, the stale call-site comment, the wrong capture stamp, the stale burrow counts). Add the AoE/single-target flag to `land_skill` — it is the one simplification in the file with no callout. Either make `SWING_WINDUP` proportional to the declared speed, or leave it and **state the refutation at the call site**, because the current pairing of 0.899 with a declared 1.33 is a combination no observation supports under either surviving model (proportional predicts ~0.59 s).

**Keep round-robin.** It is the owner's ruling, it is a fixture, and the only property it claims — that every slot is reachable — is a mechanism property that was measured. Just stop the code from saying it is *"roughly what a Guild Wars monster does."*

### 8.5 The compliance gate, before any of this lands

`CLAUDE.md` and `PLAN.md` §6.1: **before a module takes a layout, an algorithm or a table from any upstream, add its register row first.** The register was read in full — thirteen rows, none touching combat AI, aggro, targeting or skill selection. The gwinch set is a **table**; the scatter, leash, targeting and formation rules are **algorithms**. One row naming GWW, its licence, and which findings are values (fine as content rows with `source = "wiki"`) versus policies (need the row) has to be written **before the first aggro or scatter rule lands**. This is the rule the `gwdat.py` incident was written about: a rule nothing checks is a wish.

### 8.6 One acceptance instrument, and it is not a measurement

Play the R1.5 tape of ArenaNet's own recorded monster behaviour into our client on loopback, run our own server on the same map, and have the **owner watch both**. This is the only instrument that can answer *"does it feel like Guild Wars,"* and this project already has the precedent: the `0x002E` facing convention needed an owner-observed +π offset that no wire-side check could have produced, because *"the wire cannot tell a facing from its opposite"* — and `test_rotate.py`'s own scoring called the un-offset derivation *"correct by every derivation available"* while the agent faced backwards on screen.

**Its scope is bounded by the tape's own docstring:** *"It is not a world … A tape can show a load and a populated, animated map; it cannot show control."* So the A/B is over ambient behaviour and combat animation, not responsiveness. **And it is refused as evidence:** diffing our emitted stream against the tape compares our reconstruction against a recording of a different session on a different map at a different moment, so any difference is uninterpretable and any similarity is our own decoder on both sides.

---

## 9. Open questions, ranked by what they cost to answer

| # | Question | Cost | What settles it |
|---|---|---|---|
| 1 | ~~Is `CHAR_AI_MODES` a UI enum or a server-side AI concept?~~ **ANSWERED 2026-08-11: UI.** | *was:* one capstone read | 3 at five sites, two three-arm switches, `AI_MODE_ICONS` = 3, `AGGRESSIVE` = 0, and the labels are **Fight / Guard / Avoid Combat**. The lead closed and the binary negative is total. §2.2.1. |
| 2 | ~~What do the definition `flags` bits mean?~~ **ANSWERED 2026-08-11: to the client, they are display.** | *was:* one `msghandler.py` run | Nine readers, every one `AvChar`/`AvApi` (the renderer) or `PtRoster`/`PtMinionRoster`/`CtlInstance` (UI panels). Bit 9 — the near-perfect combatant separator, 0/302 vs 282/283 — is an **animation gate**. The partition is real; the client cannot support a combat reading of it. §3.7.1. |
| 3 | Does `Engine\Map\Path` contain steering or pursuit? | **Reading five more modules' asserts.** | Six of eleven are read and are pure geometry; `PathObstacle`'s `radius >= 0` says dynamic obstacles are modelled. |
| 4 | Do monster spawn placements live in the Props chunk? | **One prop model-id histogram** for one map, off code `mapexport` already has. | Whether any id lands in the `0x20000000` creature-class range. Closes Gw.dat's last unmeasured slot. |
| 5 | Does the tick clock agree with the wire clock on the **existing** captures? | **One analyser run**, no new session. | The `0x001E` integral against the wire span, ≤50 ms. If red, every timed claim in the repo is suspect. |
| 6 | Does windup scale with declared speed, or is it per-creature? | **One session** targeting a third declared speed, n≥8. | A creature at 1.33 or 2.475. Predicts windup in [0.43, 0.46] × its own declared base. |
| 7 | Does unprovoked proximity aggro happen at all, and at what radius per creature? | **1–3 sessions**, the `approach` step, subjects that have not moved since create. | 10 point measurements across ≥3 types. **Refuted if** two creature types' brackets do not overlap — then it is a field, not a constant, as GWW says. **Also refuted if** a subject never reacts down to contact, in which case `AGGRO_RANGE` dies as a concept rather than being retuned. |
| 8 | Leash: home, stop, or none — and anchored where? | **1–3 sessions**, the `retreat` step, aggroed by approach not by attack. | 6 disengagements across ≥2 types. All three outcomes are findings. |
| 9 | Is ambient movement correlated with the player at all? | **Free** — a by-product of every control window. | Patrol destinations vs contemporaneous player position, clustered rather than merely catalogued. |
| 10 | Absolute monster max health | **1–3 sessions**, if the character carries life-stealing skills. | Two skills of different published steal agreeing on 3 types GWW publishes. Would move HP off `PLAN.md` §1.7's server-only list. |
| 11 | What are `band` and `anim`? | **One session**, the `narrate` step. | The operator saying in chat what they were looking at. |
| 12 | Does a hostile ever switch targets? | **Needs a pet or escort NPC** — a solo character has one body. | Not searched in the existing corpus either; one connection with three simultaneous hostiles could support the analysis. |
| 13 | Skill-selection policy | **5–10 sessions**, and the yield is not guaranteed. | 30 casts per type across sessions on different individuals. Report the shortfall rather than a histogram over n=6. |
| 14 | Scatter | **Needs a character with an area damage-over-time skill.** | GWW's four rules are specific enough to falsify: group-synchronised, cancels current actions, runs from epicenter, ceases actions until safe. |
| 15 | Respawn, group pulls, boss identification, morale, target-switch | **Unknown** — none of these events occurs in the corpus, and none is guaranteed to occur in a campaign session either. | Longer dwell in one area after a kill (respawn); a denser pull (group aggro); a boss encounter (the unexplained 4-bit that separates `mon1` flags 8 and 13). |
| 16 | AI as a mechanism | **Cannot be settled.** | Nothing. It is not shipped and it is not transmitted. |

---

## 10. What the orchestrator re-ran, and what changed

Everything above came from thirteen agents. Four of its claims would change code in this
repo, so those four were re-measured from scratch before any of them landed. **All four
reproduce. One of them reproduces with different numbers, and the discrepancy is
recorded rather than smoothed over.**

| Claim | Verdict | What the re-run got |
|---|---|---|
| `SWING_WINDUP` is not a constant | **CONFIRMED, numbers differ** | n=**42** from **4** attackers, not n=40 from 5. The melee-finish channel carries landings for exactly four agents corpus-wide, so five attackers *cannot* have paired windups; the 5 is likely an attacker counted with none. The 86 ms cluster gap reproduces exactly. |
| Skill 276 is elite | **CONFIRMED** | `elite=True`, `flags=4` (bit 2), read from the client's own table on the pinned build. Bit 2 is set on 391 of 3,443 rows, so it is a real field and not a one-row artifact. Activations and recharges of all four bar skills match. |
| The NPC cast is cited to the wrong capture | **CONFIRMED** | The single `0x009F [60, agent, skill]` is in **capture A**, connection `:62994`. The comment names capture B. |
| Twelve of fourteen constants are unpinned | **CONFIRMED** | Sabotaged four: `SWING_WINDUP → 0.2`, `ENEMY_MELEE_RANGE → 400.0`, `AGGRO_RANGE → 1100.0` all **pass 125/125**. `ENEMY_TURN_RATE → 1.0` is the only one that reddens — and it is the only CORROBORATED constant in the set. |

**One thing the re-run found that the dive did not**, and it is the most actionable byte
in §3.6: the NPC's cast and the player's casts are **different message shapes**, not the
same message with a different actor.

| | opcode | payload |
|---|---|---|
| NPC, ×1 | `0x009F` | `[60, agent, skill]` — **no target slot** |
| player, ×4 | `0x00A0` | `[60, caster, target, skill]` |

Our server already sends the `0x009F` form, so it is right — but it was right without
this being written down anywhere, which is the same as being right by luck.

**And a method note that belongs here rather than in a commit message.** The first
version of the windup re-measurement scored **zero paired swings** and, had it not been
obviously zero, would have read as "the corpus contains no landings." The cause was the
decoder trap this repo keeps paying for: `0x00A0`'s value field is at index **1**, and
the script read index 3 — which is a constant `0` on all 63 instances. A vacuous zero
from a field that is always zero is exactly the failure `checks.py` exists to catch, and
nothing but the implausibility of the result caught it here. The layout in the table
above was *measured* out of the corpus before the second attempt, not assumed.

---

*Written 2026-08-11 from a five-angle fan-out with independent hostile review of every angle, a capture-campaign design and a completeness critic, then a verification pass by the orchestrator over every code-driving claim (§10). Nothing in this document was produced by launching a client or by pointing anything at ArenaNet. Every corpus figure quoted here was reproduced by at least two parties except where n and provenance are stated otherwise, and every claim that did not survive review is in §6 rather than deleted.*