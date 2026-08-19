# Heroes and henchmen — what the client knows, and what we can author

**Arc opened 2026-08-15.** Read-only client analysis (build 38797, the pinned pristine
`Gw.exe`), the vault's whole capture corpus, and the official wiki. No client was launched
and nothing was patched. Labels are the repo vocabulary defined in
[studies/character/FINDINGS.md](../character/FINDINGS.md): OBSERVED, UPSTREAM,
CORROBORATED, RECONSTRUCTION, CONTESTED, UNVERIFIED, NOT FOUND.

---

## 0. The result in one paragraph

**Heroes and henchmen are recoverable, and they are recoverable from the BINARY, not from
the wire.** This is the same shape as [studies/monsterai](../monsterai/FINDINGS.md) — and
the same reason: every session in the vault is a solo operator, so the party-add family has
**zero live occurrences in 22,524 decoded live `GAME_SMSG` messages** (OBSERVED, §5). But
where monster AI died on a *total* binary negative — the server half was never shipped —
heroes are the opposite case: the client is **dense** with hero structure, because the hero
is a thing the *client* renders, commands and stores. Two party-add messages are now shaped
from the client's own descriptor tables and their handler bodies traced store-by-store
(§1); the static hero catalogue is located, bounded and closed (§2); the command surface is
bounded at seven slots and three stances (§3). The honest negatives are equally sharp: a
hero's **skill bar has no known delivery mechanism on the wire** (NOT FOUND, §4), and the
**c2s** direction — stance changes, flag placement, hiring — is NOT FOUND at every point we
looked (§3.3). An authorship route exists and the henchman half is buildable now (§7).

**The single most useful fact for anyone continuing:** a henchman carries its **name on the
wire** and needs no client-side table lookup at all, while a hero carries **no name** and
must resolve its identity through `s_heroClientData`. That asymmetry is why the henchman is
strictly the easier target, and it is measured, not assumed (§6).

---

## 1. The party-add wire family — OBSERVED from the client's own tables

Two dispatch tables are in play and they are **not** the same subsystem. Conflating them is
the first available mistake:

| Table | Family | Opcodes |
|---|---|---|
| `0x00bcb788` | **party roster** | `0x01BF` henchman-add, `0x01C2` hero-add, `0x01D2` build-begin, `0x01CB` add-member, `0x01B2` set-mine |
| `0x00bc8f68` | **hero data cache** | `0x0072` hero-data gate, `0x0074` mercenary/hero info |

CONFIRMED by an adversarial re-derivation from fresh disassembly: the two families even use
structurally different `this`-resolution idioms (the `0x00bcb788` handlers open
`call 0x47f660; mov ecx,[eax+0x4c]; add ecx,4`).

### 1.1 `0x01BF` / 447 — PARTY_HENCHMAN_ADD

**OBSERVED.** Descriptor `[u16, u16, string16(20), u8, u8]`, **50 bytes on the wire**, table
`0x00bcb788`, handler `0x00856b00` → worker `0x00858cb0`. Field-by-field, traced to the
store and independently reproduced by a second agent from raw disassembly:

| Wire | Use | Stored |
|---|---|---|
| `msg+4` u16 | bound-checked against `[this+0x44]`, indexes the pointer array at `[this+0x3c]` — **the party record**, so party 1 must have been BUILT first | — |
| `msg+8` u16 | **dedupe key** — scanned against existing entries before append (loop `0x858D06`–`0x858D3C`) | entry`+0x0` |
| `msg+0xc` | name, copied by helper `0x46bf70` | entry`+0x4`…`+0x2b` |
| `msg+0x34` u8 | — | entry`+0x2c` |
| `msg+0x38` u8 | — | entry`+0x30` |

Entry size **0x34 bytes**. This **CORROBORATES** GWCA's published
`{word, word, string16(20), byte, byte}` from an independent witness (the client's own
descriptor), promoting the *shape* from UNVERIFIED — see
[studies/character/FINDINGS.md](../character/FINDINGS.md) line 1157.

**But the two trailing `u8`s are NOT FOUND, and that is the correct label.** GWCA and
OpenTyria call them `profession` and `level`. The client stores them to `entry+0x2c` and
`entry+0x30` **with no naming assert anywhere** — `asserts.py --grep henchman` returns four
sites (`PtHenchman:98`, `PtPartyEntry:146`, `PtRoster:248`, `PtRoster:602`), none naming a
level or profession field. Their meaning stays UPSTREAM. It is also *cheap to settle*: send
distinguishable values and read the rendered row.

### 1.2 `0x01C2` / 450 — PARTY_HERO_ADD

**OBSERVED.** Descriptor `[u16, u16, u16, u8, u8]`, **10 bytes**, same table `0x00bcb788`,
handler `0x00856b80` → worker `0x00858f50`. The first field uses the **identical** party
lookup mechanism as `0x01BF`.

**This CORRECTS OpenTyria.** `ldufr__OpenTyria/code/GameMsg.h:466-473` gives
`PARTY_HERO_ADD` a `uint8 level` and nothing to distinguish it; the client's own descriptor
carries **three** `u16`s and **two** `u8`s. The row in
[studies/character/FINDINGS.md](../character/FINDINGS.md):1156 marked UPSTREAM should now
read: shape OBSERVED, field meaning still open.

Storage: `msg+8`→entry`+0x4`, `msg+0xc`→entry`+0x0`, `msg+0x10` u8→entry`+0x8`, two
**client-hardcoded zero dwords** (not wire fields) →entry`+0xc`/`+0x10`, `msg+0x14`
u8→entry`+0x14`. Entry size **0x18 bytes**.

> **A RECONSTRUCTION was REFUTED here, and it is worth recording.** The first pass argued
> "entry`+0x0` is the primary-key position, by analogy with `0x01BF`". The analogy does not
> hold: **`0x01C2`'s worker has no dedupe scan at all** — it goes straight from the slot
> lookup to an unconditional append (capacity-grow via `0x4739c0`, store), unlike
> `0x01BF`'s worker which explicitly loops over existing entries. So there is no functional
> evidence that entry`+0x0` is a key rather than entry`+0x4`.

**Which of the two `u16`s is `agentId` and which is a hero index is UNVERIFIED**, and the
cross-reference that looked like it would settle it points the wrong way: `GmHeroCommander`'s
`heroData->agentId` resolves through `ctx+0x2c+0x584` — the **`0x0074` data-cache record**,
not the `0x01C2` party-roster entry. One caged probe with distinct values in both arms
settles it.

### 1.3 `0x0074` / 116 — the upstream shape is REFUTED

**OBSERVED.** Handler `0x0091e2f0` → `0x00811560` → `0x0081db20`. The client's own decoder
reads **20 fields, 127 bytes**:
`[u16, u8,u8,u8, u32,u32, u8,u8, u32, u32×10, string16(32)]`.

That is **not** GWCA/OpenTyria's `{hero_id, level, primary, secondary}`
([character FINDINGS](../character/FINDINGS.md):1158). The four-field claim is REFUTED as a
description of the wire; what survives is that the *first* field is an id and three `u8`s
follow it (stored to record `+8`, `+0xc`, `+0x10`) — consistent with
`{level, primary, secondary}` but **not confirmed**, since no consumer of `+0xc`/`+0x10` was
traced to a profession bound-check. RECONSTRUCTION, low confidence.

The worker looks up **or creates** a per-hero record in the local player's own context at
`ctx+0x2c+0x584`, keyed by the u16 id. The ten trailing dwords are split into **two clean
5-dword (20-byte) chunks** stored at record `+0x4c` and `+0x60`, with a conditional third
copy to `+0x74`. Two parallel 20-byte groups; meaning NOT FOUND.

### 1.4 `0x0072` / 114 — a CLIENT-STATE gate

Handler `0x0091e240` → `0x00811530` → `0x0081da40`. `msgshape.py`'s own field-typer types
field 2 as `agent_id` independently of any hero naming. The worker looks the agent up and,
**on a miss**, calls out through `0x0046ed40` with a tag pointer `0xa95888` — which is the
`HeroActivate (hero %d, agent %d, inventoryId %d, aiMode %d)` format string
(cross-referenced with [monsterai](../monsterai/FINDINGS.md) §2.2). That string fires from
inside the handling of an **incoming** message, not a player-initiated send (OBSERVED) —
which is a small but real correction to any reading of `HeroActivate` as a c2s verb.

---

## 2. The static hero catalogue — `s_heroClientData`, settled

**OBSERVED, and I verified this one personally because two agents disagreed and the answer
is load-bearing.**

```
0x005A9380  cmp esi, 0x28          ; 40
            push 0x96              ; line 150
            -> P:\Code\Gw\Const\ConstHero.cpp / "index < arrsize(s_heroClientData)"
            lea eax,[esi+esi*2] ; lea eax,[eax*8 + 0xa35e08]   =>  24*index + 0xA35E08
```

**`s_heroClientData` is 40 rows × 24 bytes at VA `0x00A35E08`.** The accessor is
`0x005A9380`; the `ConstHero.cpp:150` assert sits inside it at `0x005a9391`.

> **The rival reading was a misattribution to the NEIGHBOURING table, and reading the
> client's own assert strings settles it cold.** The accessor at `0x005A9350` —
> `cmp esi,0x30` (48), stride 12, base `0xA35B80` — asserts
> `P:\Code\Gw\Const\ConstTitle.cpp` / `index < arrsize(s_titleClientData)`. It is the
> **title** table. Two adjacent `Const*` accessors, six instructions apart, and the
> 48×12 geometry belongs to the other one. *A structural locator that closes on the wrong
> anchor still closes.*

**Bounds, corroborated across independent sites:**

- **`HEROES` = 40.** `ChCliApi:4446` `hero < HEROES` at `0x0080E257` is `cmp esi,0x28`
  (line `0x115e` = 4446), and `:4459` uses the same bound. Equals `arrsize(s_heroClientData)`
  — two independently-compiled constants agreeing.
- **`HERO_UNUSED` = 0.** `ChCliApi:4447` (line `0x115f`) fires on `test esi,esi; jne` — it
  asserts only when the value is 0. Row 0 is the reserved placeholder, and its name field
  resolves to the empty string, distinct from all 39 others (CORROBORATED).
- **Per-player active-hero cap = 7**, from three independent sites: `PtPlayer:332`
  `heroIndex < arrsize(m_heroAgentId)` (`cmp esi,7` at `0x00574C99`, line `0x14c` = 332),
  `GmHeroCommander:214` `heroIndexPlayer != arrsize(activeHeroes)` (`cmp ebx,7`), and
  `GmView:4330`'s keybind enum naming exactly `CONST_KEY_COMMAND_HERO1..HERO7`.

**Row layout (6 dwords).** `+0x00` row index (self-referential, verified by `consttable.py`'s
index-column check); `+0x04` a per-hero **unlock cost/threshold** compared against a balance
fetched via `0x00815E20(0xB)` inside the `VnUnlockHero` eligibility check (RECONSTRUCTION,
medium); `+0x08` a constant `157942` across rows 1–39 that resolves structurally but yields
no text — **NOT FOUND**; `+0x0C` **name** string-id; `+0x10` **epithet** string-id; `+0x14`
**biography** string-id.

**No `model_id` and no profession field in this table** — so a hero body's model must come
from a content row, and a hero's professions are *not* here.

### 2.1 Provenance ruling — this table is extractable

**CONFIRMED under the MEASUREMENT branch of the provenance gate.** The row is six numeric
dwords: an index, a cost threshold, an unresolved id and three **string ids** — precisely the
nouns `CLAUDE.md` permits ("levels, bounds, counts, strides, ids, offsets, addresses,
layouts"). A `heroes_table.py` emitting
`{index, unlock_cost, unk8, name_string_id, epithet_string_id, bio_string_id}` per row is
permitted, on the standing conditions: **the extractor lives in this repo, the row names it,
the row records the build, provenance is per row.**

Two boundaries hold. **Emit ids, never a committed 40-row column of resolved English** —
that is the "commit the id, resolve the string at run time" rule, and it is exactly what the
client itself does. The handful of single resolutions used above as evidence for the
field-offset hypothesis (row 1 → a name, row 0 → empty) are legitimate measurements; a bulk
name dump would not be. And the extractor must anchor on `0x005A9380` / base `0xA35E08` —
the title-table trap above is the reason to say so out loud.

---

## 3. The command surface

### 3.1 Seven slots, and an eight-way flag dispatch

**OBSERVED.** `GmHeroCommander` bounds a per-player array of exactly **7** commander slots
(`heroCommanderSlot`, `(0x4c-0x30)/4 = 7`, asserts at `:81`, `:108`, `:246`). Binding a slot
resolves an agent id to a `heroData` pointer (`call 0x0080e370`), then asserts the pointer
non-null (`:120`) and `heroData->agentId` non-zero (`:121`) — **so a hero needs a live world
body before its commander slot will bind.** A second 7-element array, `activeHeroes`, is
built by scanning the party's agents.

`GmView:4330`'s assert enumerates ten key symbols and the switch maps ten physical key codes
through a jump table to **8** distinct command indices. Independently, `AV_FLAGS = 8`
(`AvFlag:86`) and `AI_COMMAND_FLAGS = 8` (`Compass:222`, `CompassInt:49`) are two separately
bounded 8-element enumerations. The natural reading — henchmen-as-a-group at index 0 plus 7
individually-flaggable hero slots — is **RECONSTRUCTION**; no single site names index 0
"henchmen". *(The wiki independently describes four compass flag controls: three individual
plus one all — see §6.)*

### 3.2 The stance enum, corroborated from a second direction

**`CHAR_AI_MODES = 3` = Fight / Guard / Avoid Combat.** Established in
[monsterai §2.2.1](../monsterai/FINDINGS.md) from five bound sites and text ids 44156–44158;
**independently CORROBORATED this session by the wiki**, which documents exactly three hero
Combat modes under those three names (GWW *Hero*, rev 2026-06-21). A code-derived enum and a
player-facing document agreeing is a genuine two-witness result.

This also confirms monsterai's framing from the other side: the enum is the *player's*
hero/henchman/pet stance widget, not a monster-AI concept.

### 3.3 The c2s direction is NOT FOUND, three times

- **Stance change: NOT FOUND.** `GmAgentCommander`'s aiMode setter bound-checks the value
  (`:328`), stores it to `[esi+8]`, and calls a generic UI-invalidate routine with 256
  callers — **no network send**. Whether stance is server-authoritative at all, or purely
  client-local, is unanswerable from this evidence and both readings fit.
- **Flag placement: NOT FOUND.** `AvFlag`'s place/create path and `GmView`'s keybind
  dispatch both bottom out in generic vector/UI calls with no opcode-constant push.
  (`GAME_CMSG 0x2B` is **COMPASS_DRAW**, already settled in
  [minimap §4.1](../minimap/FINDINGS.md), and is *not* hero flags — a rival that arc took
  seriously and refuted.)
- **Hiring: NOT FOUND.** No c2s "hire henchman" opcode was located. Irrelevant to
  server-push authoring, but it means we cannot make the client *request* a hero.

All three are **floors, not censuses** — `asserts.py` itself warns that every "no assert
names X" answer is short by the ~370 sites its fixed patterns cannot read.

**CORRECTED 2026-08-19, and the first bullet is the one that fell — by clicking, not by
reading.** Once the commander panel opened (pvpui §28.3), the stance buttons became
clickable for the first time ever, and each of the three emitted exactly one
`GAME_CMSG 0x0015` — `[agent_id, mode]`, agent 200, mode tracking the click order
Guard=1/Avoid=2/Fight=0, the same enum `0x0072`'s own format string names `aiMode`.
Full record: [pvpui §28.5](../pvpui/FINDINGS.md); named `HERO_AI_MODE` in
`schema/overrides.json`. Two refinements, not a contradiction: the send lives on the
**button path**, not the `GmAgentCommander` setter this section traced (that dead end
was a wrong-place answer, and the floors-not-censuses caveat above was doing exactly
its job), and the client does **not** move its own stance ring on click — it waits for
the server, so stance is server-authoritative and the setter presumably runs on the
`0x0072` echo. Flag placement stayed unemitted in the outpost run, but not as a null:
the client refused it on its own — "Norgu cannot have a target while in an outpost" —
so that bullet's verdict now lives with the explorable-map run in pvpui §28.5. Hiring
remains NOT FOUND.

---

## 4. Hero skill bars — the sharpest negative

**NOT FOUND: no message anywhere carries a hero's 8-slot skill bar.**

The party-add messages have no room for one — `0x01BF` is 50 bytes and 20 of them are the
name; `0x01C2` is 10 bytes total. A scan of every declared SEND-direction message shape
found no skill-bar-shaped field (8 discrete skill ids in sequence) in any of `0x0074`,
`0x01BF`, `0x01C2`, or the SEND table.

`GmDeckBuilder` (a "deck" is a skill bar) has an explicit `heroData` concept: three asserts
at `:2301`/`:2321`/`:2334` inside one function iterating 11 attribute slots, gated by
`test byte ptr [edi+8], 0x10`. But the attribute getters it uses resolve **unconditionally**
to the *local player's* record (`ctx+0x2c+0x6bc` — the same array
[profession RUNS.md](../profession/RUNS.md) found is written only by `PLAYER_UPDATE_PROFESSION`).
Whether the deck builder ever repoints that singleton at a hero's own record while editing a
hero build is **NOT FOUND**.

So a hero's build is either a packed template blob in a message not yet scanned, or it is
client-table-resolved. `ChCliHero` holds **two** distinct hero-indexed structures — a
156-byte-stride array (setter `0x0081D830`, assert `charHeroData` at `:103`) and a 36-byte
record list (`0x0081D880`) — and **neither was traced to any message**. That is the gap.

---

## 5. Can the wire teach us this? No — and here is the number

**OBSERVED, and this is the arc's framing fact.** Decoding every `GAME_SMSG` frame from all
six live-session directories (12 live connections, `origin.py`-classified LIVE) via
`tape.decode_all` yields **22,524 messages, of which ZERO carry opcode 114, 116, 447 or
450.** Every live session is one solo operator; no party was ever formed.

The only appearances of these four opcodes anywhere in the vault are **92 sent-events across
50 files, every one labelled `PROBE[smsgsweep]`** — our own synthetic sweep. No ordinary
server operation has ever sent them.

**What the sweep already measured** (2026-08-12, all-zero payloads):

| Opcode | Result | Reading |
|---|---|---|
| `0x0072` | **ASSERTED** | a **client-state gate**: `charHeroData` wants a hero record and a level-1 character has none. No payload opens it. |
| `0x0074`, `0x01BF`, `0x01C2` | **SILENT**, then **QUIET** on the screen pass (0.08–0.19% vs noise floors 0.07–0.18%) | absorbed with no reply and no detectable screen change |

The SILENT results are explained: the all-zero `0x01BF` took the `party_id == 0` branch,
which resolves the "current party" slot from `[this+0x50]` — and nothing had been built, so
it found NULL and dropped silently. **Our server has since learned to build a party**
(`party_build()`, [RESKIN §17](../profession/RESKIN.md)), so this is precisely the condition
that has changed. Whether QUIET means "inert opcode" or "nothing was listening" is the first
thing a caged run should answer.

Also worth recording: these three were **never retried under the `--encstring` regime**, only
all-zero — and a real encoded string is what flipped six other opcodes from ASSERTED to a
named visible effect.

---

## 6. The player-facing layer (WIKI)

Every fact here is WIKI with page and revision; it is what the mechanism has to reproduce.

- **Henchmen** (*Henchman*, rev 2026-04-07): hired from the Party Search panel's Henchmen
  tab; **leader-only**; **builds are FIXED** (heroes are described as "an enhanced, fully
  customizable version of henchmen"); **level depends on the outpost** — map-travelling
  re-levels them. So henchman level is a per-(unit, outpost) fact, not a global one.
- **The first roster we can actually reach** (*Ascalon City*, rev 2026-01-30): post-Searing
  Ascalon City, party size 4, henchmen all **level 3** — **Stefan** (Warrior), **Reyna**
  (Ranger), **Alesia** (Monk), **Orion** (Elementalist). **Pre-Searing has none**,
  confirming [presearing MANIFEST](../presearing/MANIFEST.md) #35. *(Note for anyone
  planning a capture: Lakeside County is pre-Searing — the tape run's map has no henchmen to
  observe.)*
- **Heroes** (*Hero*, rev 2026-06-21): Nightfall/EotN; **31 heroes**; fully customizable
  skills, attributes and equipment; fixed primary profession (except Razah). Three combat
  modes as in §3.2. Four compass flag controls — three individual plus one "all heroes and
  henchmen"; heroes 4+ use keybinds, matching the 8-way dispatch in §3.1.
- **Hero cap, corrected**: "up to seven heroes", and **"prior to the March 3, 2011 update,
  each character was limited to adding three"**. The 7-hero limit is a **2011 game update
  gated on party size**, *not* an EotN feature — a correction to the premise this arc
  started from. Heroes are per-controlling-player; henchmen are leader-only.
- **Mercenary Hero** (*Mercenary Hero*, rev 2026-07-15): a **registered level-20 character
  template** — profession primary/secondary, name and appearance copied; account-wide, max 8.
  This grounds the *semantics* behind `0x0074`'s first fields even though it REFUTES the
  4-field wire shape (§1.3).
- **Hero AI** (*Hero behavior*, rev 2026-08-10): "no reaction time; their interrupts are
  never late" — this is the verbatim source for the phrase quoted in
  [monsterai §4.5](../monsterai/FINDINGS.md), now cited with a revision. And
  (*Henchman*, See also) **"heroes and henchmen share the same AI"** — which *sharpens*
  monsterai's finding rather than contradicting it: hero↔henchman is a shared engine,
  hero↔monster is not.

---

## 7. The authorship route

### 7.1 Henchman — buildable now

Every step below already exists in `authsrv.py` except one. **The new message is `0x01BF`.**

```
0x0059 PLAYER_INFO            (existing)
0x00B0 PLAYER_PARTY_SIZE      size 1 -> 2
0x00B1 PLAYER_SET_PARTY       (existing, size-then-leader is the measured order)
0x01D2 PARTY_BUILD_BEGIN      party 1        (existing)
0x01CB PARTY_ADD_MEMBER       the player     (existing)
0x01BF PARTY_HENCHMAN_ADD  <-- NEW: [party 1, agent_id, enc_name, u8, u8]
0x01D3 PARTY_BUILD_COMMIT     party 1        (existing)
0x01B2 PARTY_SET_MINE         party 1        (existing)
0x0056 / 0x0057 / 0x0020      the body, via the existing create_agent_world path
```

**Gates**, all mirrored from client asserts rather than taste: `PyCliParty.cpp:1228` (a
second `0x01D2` with a build open), `:1238` (commit id must equal begin id), the **silent**
`[this+0x44]` bound (party must be built first — the sweep's SILENT is the observation of
this failing), `Base\rtl\Array.h index<m_count` (an agent whose `0x0056` definition was never
sent **kills the client**), and our own codec cap — `enc_name` must be a pre-encoded
string-id list within **20 code units**.

Two useful asymmetries found while verifying: `0x01CB`'s worker **asserts** on a missing
party record (`PyCliParty.cpp:1036`) while `0x01BF`'s worker **silently returns** — so the
absence of the 1036 assert in a run proves the party record exists, and a silent `0x01BF`
failure then points at the UI/render layer rather than the party gate. And the `0x01BF`
worker never *reads* the `[record+0x78]` build flag — it **sets** it, exactly as `0x01CB`
does, which leans toward "post-commit placement also works" without closing it
(OBSERVED-partial, ~90 instructions).

**Smallest demo:** one new line behind a flag (the pattern `PLAYER_FLAGS` already uses) —
send `0x01BF` with a real `EncString` name and bump `0x00B0` to 2, **with no world body at
all**. That deliberately isolates the roster question from the agent question. If the row
does not draw, add the body with a matching agent id and re-run; `PtRoster:602`'s frame
lookup by `agentId` predicts that it will matter.

### 7.2 Hero — one genuine unknown in the middle

Same spine, plus `0x0074` first (to create the data-cache record), `0x01C2` in the build
window, the world body (**mandatory** — `GmHeroCommander:120/121` demand a resolvable
`heroData` with a non-zero `agentId`), and a **trailing `0x0072` as a diagnostic**: it
ASSERTED on 2026-08-12 under identical client state minus our messages, so if it now
completes silently, *something we sent created the record* — a refutable experiment with the
prediction stated first, which is the house pattern.

Hero index must be **1..39** (`hero < HEROES`=40, `hero != HERO_UNUSED`=0).

**Blockers, honestly:** which `0x01C2` `u16` is the agent id (UNVERIFIED); **what creates
the `charHeroData` record** `0x0072` gates on (NOT FOUND — and the world body may be
*necessary but not sufficient*, since nothing shows `0x0020` creating a `ChCliHero` record);
hero skill-bar delivery (NOT FOUND, §4); and the timing of commander-slot binding, which
means the hero demo **could assert before its diagnostic sends** — in which case the assert
dialog *is* the readout, naming the binding trigger.

### 7.3 Acceptance criteria, in ladder style

> **R4c-H (henchman).** In one caged loopback harness run in an explorable, with the
> instance-load sequence extended by exactly one `0x01BF` (party 1, a real `EncString` name
> from a content row, agent id matching a `0x0020`-created body ~150 units from spawn) and
> `0x00B0` raised to 2, pressing **P** shows the Party Members roster with **two** member
> rows, the second bearing the archive-resolved name — while the control arm, identical but
> omitting the `0x01BF`, shows **one**.

> **R4c-He (hero, stretch).** The same construction with `0x0074` + `0x01C2` + body, passing
> when a second roster row renders **and** the trailing `0x0072` completes without the
> assert dialog.

**Two strengthenings the verifier added, both adopted.** First, `shotlabel.py` "does not name
anything" — its number proves *change against a noise floor*; the "two rows, named" content
is an **operator read** of the labelled frame, and the criterion must state that split
rather than implying the tool reads text. Second, add a **name-swap arm**: two treatment
runs differing only in which name id is sent. A pixel-diff can be faked by any change; a
*specific different name in the same row* cannot. Note also that **no echo is possible** —
with 0 of 22,524 live messages carrying `0x01BF`, there exists no retail byte stream to
replay, so any `0x01BF` we send is necessarily authored.

---

## 8. Open questions, ranked by cost

1. **Does `0x01BF` render a roster row now that `party_build()` exists?** The whole route
   hangs on this and it is one caged run. The QUIET-because-no-party reading is
   RECONSTRUCTION until then.
2. **Do the add messages have to sit inside the `0x01D2`..`0x01D3` window?** Probe both
   arms; retail's own placement is unknowable from our corpus (0 live hits).
3. ~~**What creates the `charHeroData` record?**~~ **ANSWERED §11.3: `0x0074`.** The
   trailing diagnostic did answer it cheapest — one message's presence flips the assert
   between `charHeroData` and `attribState`.
4. ~~**Does the roster row require a matching live world agent?**~~ **ANSWERED §10.1: no.**
   The row draws standalone; it is its CONTENT that needs the agent. **And §11.1 settles
   `0x01C2`'s word order: msg+0xc is the agent id, msg+8 the hero index.**
5. ~~**What do `0x01BF`'s two trailing `u8`s mean?**~~ **PARTIALLY ANSWERED §10.2** — not
   what the roster row renders, which is the reading upstream's names invite. Purpose still
   NOT FOUND; the untested candidate is the outpost hiring UI.
6. **Where do hero skill bars and ATTRIBUTES come from?** Still NOT FOUND — but §11.4
   renames it: the client now asserts `attribState` (`ChCliAttrib.cpp:156`) as the next
   gate, so the question is "what writes a hero's attribute record", and `0x0074`'s two
   unexplained 5-dword groups are the shaped hypothesis to test first.
7. **Retry the family under `--encstring`** — never done; it flipped six other opcodes.
8. **A live capture at a henchman outpost** is the only source of OBSERVED ground truth for
   retail's send order and field values. Post-Searing Ascalon City, four level-3 henchmen
   (§6) — that is the shopping list.

---

## 10. THE CAGED RUN — R4c-H passes, and the roster row is a POINTER

**Run 2026-08-16, caged loopback, four arms, build 38833 (`2026-08-13_64fae3b1369b`),
map 90 Lornar's Pass, explorable.** Owner's go-ahead. Every arm reached "body is in the
map"; the readout is the client's own screen with the operator reading the row, exactly as
§7.3 requires.

| arm | `0x01BF` | body at agent 30 | rows | second row reads |
|---|---|---|---|---|
| control | — | — | **1** | — |
| roster-only | ✔ | — | **2** | `Lvl 255  ...` |
| body | ✔ | ✔ | **2** | `Mo1 Hatcher [Collector]` |
| **discriminator** | ✔ *(worm name, prof 6, lvl 20)* | ✔ *(Hatcher, prof 3, lvl 1)* | **2** | `Mo1 Hatcher [Collector]` |

**R4c-H PASSES.** Two roster rows against the control's one, the difference being exactly
one `0x01BF`, the second row bearing the archive-resolved name `Hatcher [Collector]`
prefixed `Mo1` — Monk, level 1. The name never rode the wire as text: the server sent four
string ids and the client resolved them against the owner's own archive.

### 10.1 The row draws with NO body — but it draws EMPTY

Staging the roster-only arm first paid. The row **rendered with no world agent at all**, so
`PtRoster:602`'s frame lookup by `agentId` is **not a precondition for the row existing** —
that closes §8's question 4. But its content was `Lvl 255  ...`: no name, and level `255`
= `0xFF`, a sentinel. The row is a container the client fills from somewhere else.

### 10.2 The discriminator — it overturns the natural reading

The body arm alone **could not settle anything**, and saying so is the point: its `0x0056`
carried the *same* name, profession and level as the `0x01BF`, so the rendered row could not
name its source. A confound, not a result.

A fourth arm made the two disagree — wire carrying the **worm's** name ids, profession **6**,
level **20**; body keeping Hatcher/Monk/1. Proven from the captured plaintext, not a log line:

```
bf01 0100 1e00 0400 | 410f 66be 2af2 d404 | 06 | 14
 447   p1  ag30 len4|  = lakeside_worm, NOT hatcher |  6 | 20
```

**The row rendered `Mo1 Hatcher [Collector]` — the BODY's values, every field.**

> **`0x01BF`'s name string and its two trailing bytes do not drive the roster row.** The
> row's name, profession and level all come from the AGENT the row points at. `0x01BF` binds
> a roster SLOT to an `agent_id`; the client reads what it displays from that agent.

**CORROBORATED from a prior session, independently and from the other direction.**
`test_agentlife.py`'s `section_party_of_one` already records that `0x00A6` is "the SOLE
write path to the agent's profession bytes, which is what the **party/roster label builder**
reads — so the profession ABBREVIATION had nothing to draw from and has never appeared in
any session." That was measured about the **player's own** row via `0x00A6`; this arm
measures the same thing about a **henchman's** row via `0x01BF`, and extends it from
profession to name and level. Two sessions, two different messages, one conclusion: **the
roster label builder reads the AGENT.** It also explains the control arm's `W0 Test Warrior`
— the `W` is the player agent's own profession byte, not anything the party messages carried.

This **refines the upstream claim rather than confirming it.** GWCA and OpenTyria name the
trailing bytes `profession` and `level`; the body arm *looked* like a confirmation and was
not. The client stores them to entry `+0x2c`/`+0x30` (§1.1) and **renders neither**. Their
purpose stays **NOT FOUND**, now with a measured negative attached rather than only a missing
assert. Same for the wire name: a real `string16(20)` the roster ignores. The obvious
untested candidate for both is the **hiring UI**, where a henchman is listed *before* it has
a body — which is an OUTPOST, and the party window will not open in one (RESKIN §18.1's
explorable gate). That is the next experiment and it needs the gate solved first.

### 10.3 An unpredicted second readout: the compass flag widget

The control arm's compass has **no flag strip at all**; both henchman arms grow one — a
**green "all" flag** (drawn with three dots), **three greyed numbered flags 1/2/3**, and a
**clear (X)**.

Four controls, one group plus three individual, from **one `0x01BF`** — and present in the
**roster-only** arm too, so the widget is driven by the roster entry, not the agent. It
independently corroborates two readings that were previously inference: the wiki's "three
individual plus one all heroes and henchmen" (§6), and §3.1's RECONSTRUCTION that the 8-way
`AI_COMMAND_FLAGS` dispatch keeps henchmen-as-a-group off the numbered slots. The numbered
flags are greyed because there are no heroes.

### 10.4 What it cost, so the next session does not re-pay it

- **`Code=007` is usually OUR crash, not the client's refusal.** The first body arm died with
  the client showing "connection lost"; the cause was `KeyError: 'attack_speed'` in
  `create_agent_world`, which killed the world-tick thread. Read `gamesrv.log` for a
  traceback before believing the dialog.
- ~~**The 38797 pin cannot currently run.**~~ **RETRACTED — see §24.** The pin runs; the
  cause was the crossbuild key bug, not the archive. The map-row half below is real and
  unchanged, but it is about maps 146/148 and was wrongly carried onto a map-90 run.
  ~~ Its run-dir archive has map 146/148 mid-replacement
  (row 7982 renamed `0x8001B97D`); on 38833 those maps bind to *different files* than
  `dat_study`. Clean explorable maps on the 38833 pair are **90, 474, 558** — Lakeside County
  is not one. `contentids.py` refuses correctly; this is archive state, not a bug, and it was
  not repaired here.
~~
- **`0x01BF` holds its shape on 38833**: same table `0x00bcb788`, same
  `[u16,u16,string16(20),u8,u8]`, same 50 bytes; only the handler moves
  (`0x00856b00` → `0x00856bc0`). A two-build corroboration of §1.1.
- **`--exe` needs an absolute path**, and `--game-args` needs the `=` form
  (`--game-args="--map 90"`) or argparse eats the leading `--`.
- **`reskin-roster/` is still armed** with 125 rewritten icon rows and it **sorts last**, so
  any "newest/last wins" exe pick grabs the one build whose archive is deliberately modified.

### 10.5 Buildable now, and still not

Authoring a henchman is **done as a mechanism**: `agents.party_henchman_add()` +
`party_build(inside_window=...)` + the body, flag-gated (`--henchman`, `--henchman-body`,
and the three `--henchman-wire-*` discriminator flags). Unchanged by this run: **follow AI**
(movement messages exist, so it is work rather than an unknown), the **c2s** direction
(§3.3), and the whole **hero** route, whose blockers are in §7.2.

## 11. THE HERO ARM — the word order is settled, and `0x0074` opens the gate

**Run 2026-08-16, same cage, same build 38833, map 90, five arms.** The hero route was the
one §7.2 called UNCERTAIN, with three named blockers. Two of them are now closed by
measurement and the third has moved to a new, named place.

| arm | `0x01C2` words | body | `0x0074` | roster | trailing `0x0072` |
|---|---|---|---|---|---|
| H1 | wordA=200 wordB=1 | ✔ | ✔ | **1 row** — no hero | — |
| H2 | **wordA=1 wordB=200** | ✔ | ✔ | **2 rows**, `Mo1 Hatcher [Collecto…]` + slot button `1` | — |
| H3 | as H2 | ✔ | ✔ | — | **`attribState`**, `ChCliAttrib.cpp(156)` |
| H4 | as H2 | ✔ | **✗** | — | **`charHeroData`**, `ChCliHero.cpp(199)` |

### 11.1 Which `u16` is the agent id — settled, and the design is why

The blocker was that `0x01C2` carries two `u16` identity words and *nothing in the client
says which is which* — the storage-order analogy was refuted (no dedupe scan) and
`GmHeroCommander`'s `heroData->agentId` turned out to resolve through the `0x0074` data
cache, not this entry.

The arm settles it by construction: the body was created at **agent 200**, deliberately
**outside the 1..39 hero-index range** (`ChCliApi:4446` `hero < HEROES`, HEROES==40). A word
carrying 200 *cannot* be a legal hero index, so whichever position it must occupy for the row
to render is the agent id. An id inside 1..39 would have let both readings fit — the same
confound the henchman arm nearly shipped with.

**H1 renders nothing; H2 renders the hero.** Therefore:

> **`0x01C2` msg+0xc (→ entry+0x0) is the AGENT ID.** *(The second half of this claim —
> "msg+8 is the HERO INDEX" — is **CORRECTED in §17.3**: the arm could not distinguish hero
> index from owner player number from owner agent id, because all three are 1 in this rig.
> `msg+8` is UNVERIFIED; the agent-id half stands. **§18 then settled the negative by
> experiment: `msg+8` carried 1 while the hero was 2 and the row still rendered as hero 2,
> so it is definitively NOT the hero index. **§21 then identified it positively: it is the
> OWNER PLAYER NUMBER.**)*

And that yields a tidy structural fact across both messages: **entry+0x0 holds the agent id
in `0x01BF` *and* `0x01C2`** — consistent storage, different wire order. The refuted
"entry+0 is the key by analogy" reasoning (§1.2) reached the right offset for the wrong
reason; the offset is now measured rather than argued.

### 11.2 The hero row is a henchman row plus a commander slot

H2's row reads `Mo1 Hatcher [Collecto…]` — **the body's** name, profession and level again,
exactly as §10.2 measured for the henchman. The roster label builder reads the agent, and
that now holds across both message families and three separate arms.

What the hero row has that the henchman's does not is a **numbered commander-slot button
`1`** drawn to its left — the `GmHeroCommander` per-slot UI (§3.1's 7-slot array), bound
here because the row named a hero index and a live agent with a non-zero id, which is what
`GmHeroCommander:120/121` assert.

### 11.3 `0x0074` creates the `charHeroData` record — a single-variable proof

§7.2's blocker "what creates the `charHeroData` record that `0x0072` gates on" was **NOT
FOUND by any static route**: `ChCliHero` has two hero-indexed structures and no message could
be traced into either. The trailing-`0x0072` diagnostic was designed for exactly this, with
its prediction on record — the sweep had it ASSERT on `charHeroData`.

H3 and H4 differ by **one message**. With `0x0074`, the client clears the hero-record gate and
dies deeper. Without it, it dies on the original gate:

```
H3 (0x0074 sent):   Assertion: attribState     P:\Code\Gw\Char\Cli\ChCliAttrib.cpp(156)
H4 (0x0074 dropped): Assertion: charHeroData   P:\Code\Gw\Char\Cli\ChCliHero.cpp(199)
```

> **`0x0074` MERCENARY_INFO is what creates the hero data record.** Its worker's "look up OR
> CREATE keyed by the first field at `ctx+0x2c+0x584`" (§1.3) is not just a plausible reading
> of the disassembly — it is the observed effect.

*(Both asserts are quoted as the single-assert evidence for a specific claim, which the
provenance gate permits; and a crash dialog is text the retail client shows any player who
crashes, which CLAUDE.md names explicitly as not extraction. Nothing was sent to ArenaNet —
the reporter's send button was never pressed.)*

### 11.4 The gate did not vanish, it MOVED — and where it moved to is the point

`attribState` in **`ChCliAttrib.cpp`** is the hero's **attribute state**, and the client is
now asking for it *by name*. That lands precisely on §4, the arc's sharpest negative: hero
skill bars and attributes have **no known delivery mechanism** on the wire, and
`GmDeckBuilder`'s attribute getters resolve unconditionally to the *local player's* record at
`ctx+0x2c+0x6bc`.

So §4 is no longer only an absence in our scans. The client has told us what the next message
must carry, and the next question is concrete rather than open-ended: **what writes a HERO's
attribute record?** The `0x0074` chunk was the first place to look — ten unexplained dwords
the client splits into two 5-dword groups at record `+0x4c` and `+0x60` (§1.3), and 20 bytes
is exactly one attribute entry.

> **That hypothesis was tested the same day and is REFUTED — §12.** The chunk is 40 bytes
> written into the wrong structure: `attribState` is a separate `0x43c`-stride record,
> binary-searched by a key, holding `attrib[51]` of 20 bytes each. The live lead is now the
> **template system** (§12.3), which has `attribCount` + `attrib[]` + `attribValue[]` and
> named asserts to find it by.

### 11.5 What is now closed, and what is not

**Closed by this arm:** `0x01C2`'s word order (§8 q4 for heroes); what creates
`charHeroData` (§8 q3); that a hero row renders at all and that it, too, reads the agent.
**Still open and unchanged:** hero **skill-bar** delivery (§4) — now with a named next gate;
the **c2s** direction (§3.3); `0x0074`'s remaining 17 fields; and whether a hero needs
anything beyond attributes before it is a working party member.

## 12. The attribute-chunk hypothesis — REFUTED, with the prediction on record

§11.4 proposed that `0x0074`'s two unexplained 5-dword groups (record `+0x4c`/`+0x60`) are
the hero's attribute block, on the strength of a size coincidence. **It is wrong, and the
static read said so before the run.**

### 12.1 What `attribState` actually is

Reading `ChCliAttrib.cpp:156` (`0x00818c77`, build 38833) rather than guessing at it:

- The asserting function `0x00818C60` calls a resolver `0x00819430`, asserts the result
  non-null, then returns `[esi+0x434]`.
- The resolver is a **binary search** over an array of **stride `0x43c` (1084 B)**, keyed by
  a dword at record `+0x0`. It is a pure lookup — all four of its callers are ChCliAttrib's
  own getters (lines 133/146/156/166), so nothing here creates a record.
- The `attrib[]` bound is `cmp ebx, 0x33` = **51** (`ChCliAttrib:177`,
  `attrib < arrsize(attribState->attrib)`), and the caller's index math
  `lea eax,[eax+eax*4]; lea eax,[eax+1]; lea eax,[esi+eax*4]` = `20*i + 4` gives
  **20 bytes per attribute entry, array starting at record+4**. 51 × 20 = 1020, and
  `1084 − 1024 = 60` bytes of tail — which is where `+0x434` lives.

The structure's own field names come from its asserts:
`attribState->attrib[attrib].baseValue >= 0` (`:42`) and `attribState->attribPointsAvail >= 0`
(`:43`).

### 12.2 The prediction, and the arm that could have refuted it

> **Stated before the run:** the assert will stay `attribState`, because attribState is a
> separate `0x43c`-stride keyed record holding 1020 bytes of attribute array, while
> `0x0074`'s chunk is **40 bytes written into a different structure**. If the assert moves,
> the prediction is wrong and the chunk is load-bearing.

The arm loaded every byte the hypothesis could want: chunk = ten dwords of `12` (the
attribute rank cap named by `AcctTemplate:441`), the **flag set non-zero** so the client
takes its *conditional third copy* of the second group to record `+0x74` — a branch no
previous run had exercised at all — and the three leading `u8`s at 20/3/6.

**Result: `Assertion: attribState  ChCliAttrib.cpp(156)`, unchanged.** Byte-identical
outcome to the all-zero arm. The chunk is not the attribute block, and the third-copy branch
does not reach attribState either.

### 12.3 What the refutation bought

Three new measurements and a better lead, which is why a stated-and-failed prediction is
worth more than an unstated one:

- **`attribState` geometry** (§12.1) — stride, key, 51-entry array, 20-byte entries. This is
  the shape any future "author a hero build" work has to fill.
- **The attribute count is 51** and the **rank cap is 12** (`AcctTemplate:441`
  `data.attribValue[index] <= 12`), both OBSERVED.
- **The next candidate is the TEMPLATE system, and it now has named asserts.**
  `AcctTemplate:422/423` bound a `data.attribCount` against `arrsize(data.attrib)` and
  against **16**; `:440` bounds `data.attrib[index] < CHAR_ATTRIBS`; and
  `TemplatesCode:168` / `TemplatesHelpers:368` both bound
  `m_skillTemplateData.attribCount` against `marrsize(AccountTemplateDataSkill, attrib)`.
  A struct carrying `attribCount` + `attrib[]` + `attribValue[]` **is** a build — which is
  exactly §4's "packed template blob" candidate, no longer a guess about where to look.

### 12.4 `s_attribPoints` — a clean two-witness corroboration

Chased from `CharData:202` (`level < arrsize(s_attribPoints)`), which bounds at
`cmp esi,0xd` = **13**, and the access `mov eax,[esi*4 + 0xbc8b24]` gives a dword table at
**`0x00BC8B24`**. It **closes**: index 13 is `0xFFFFFFFF`, a sentinel sitting exactly where
the assert's bound stops — a check the artifact could have refuted and did not.

| rank | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **client** `s_attribPoints[rank]` | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 9 | 11 | 13 | 16 | 20 |
| **WIKI** cost to reach rank | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 9 | 11 | 13 | 16 | 20 |

WIKI (GWW, *Attribute point* §Points required to increase rank, read 2026-08-16): the same
twelve numbers, totalling **97** to reach rank 12. **CORROBORATED** — a table read out of the
binary and twenty years of player observation agreeing exactly, and the two share no author,
code or ancestry, which is the kind of agreement the `ldufr`/GWCA cluster cannot give.

Index `[0]` is `5`, which does **not** fit the cost curve; the dword before the table is also
`5`, so `[0]` is most likely a neighbour's tail or unused. Flagged rather than explained —
**NOT FOUND**.

Two more WIKI facts that pin the frame: attribute rank **12 is the maximum obtainable by
spending points** (corroborating `AcctTemplate:441` `attribValue[index] <= 12` from the
player-visible side), and a character has at most **200 attribute points** at level 20 with
both attribute quests — which is what `attribState->attribPointsAvail` (`ChCliAttrib:43`)
counts down from. The profession table also sums to ~42 attributes plus 8 PvE title tracks,
consistent with `CHAR_ATTRIBS` = **51**.

**What is still NOT FOUND:** what creates an `attribState` entry. The only stride-`0x43c`
site outside ChCliAttrib resolves to generic `Array.cpp` growth code, so the insert path is a
vector push with no message traced into it — the same wall §4 hit, now one structure closer
and with the array's exact shape known.

## 13. The template system is a RED HERRING — and the real mechanism was already in our tree

The lead from §12.3 was the template system. **It is the wrong door, and that is now
CONFIRMED rather than suspected.** `AccountTemplateDataSkill` is **140 bytes (`0x8c`)** —
`profPrimary`, `profSecondary`, `attribCount`, `attrib[12]`, `attribValue[12]`, `skill[8]` —
and it is **account-local**: the in-memory form of the base64 build-code / saved-template
feature. A reachability closure from its functions contains **zero message handlers**. It is
the player's "save my build" UI, not a delivery mechanism, and it never was.

### 13.1 The real pair: `0x0037` creates, `0x003A` fills

**OBSERVED, and verified from both ends.**

| | shape | role |
|---|---|---|
| `0x0037` / 55 | `[agent_id, u8, u8]`, 8 B, handler `0x0091d8c0` | **CREATES** the attribState record |
| `0x003A` / 58 | `[agent_id, array32[48]]`, 8–200 B, handler `0x0091d920` | **FILLS** `attrib[]` |

The create chain is `0x0091D8C0` → thunk `0x0080EAA0` → ChCliAttrib creator `0x008199C0` →
array insert `0x00819540`, and the creator's own guard is `ChCliAttrib:313` **`!attribState`**
— the mirror image of the `:156` null check that started this. Both messages live in table
`0x00bc8f68`, the same table as `0x0072` and `0x0074`. Every link has exactly one caller and
appears in no data word, so it is in no vtable.

**Both are keyed by AGENT id — which is precisely why a hero can have attributes at all.**

> **And we already had them.** `authsrv.py` has carried
> `GAME_SMSG_AGENT_UPDATE_ATTRIBUTE_POINTS = 0x0037` and
> `GAME_SMSG_AGENT_UPDATE_ATTRIBUTES = 0x003A` since the combat/profession arc, with a
> measured column-major builder. The arc spent two refuted hypotheses hunting for a message
> that was already in the tree, sent to the player's agent every session. This is the
> `PLAN.md`-§3 failure in miniature: the thing was known, in a neighbouring study, and not
> connected.

The record layout is now fully mapped: `+0x000` key (agent id), `+0x004..+0x3FF` `attrib[51]`
× 20 B, three `Array` headers at `+0x400`/`+0x410`/`+0x424`, `+0x434` `attribPointsAvail`,
`+0x438` the third `0x0037` field. `ChCliAttrib:42`'s own text
(`attribState->attrib[attrib].baseValue >= 0`) lands on `record + i*20 + 8`, and `:43`
(`attribPointsAvail`) on `+0x434` — the source's own field names landing on our offsets,
which is a check the artifact could have refuted.

### 13.2 The gate moved a third time, and then bit

Sending the pair for the hero's agent **does clear the attribState gate** — measured, the
assert moves:

```
charHeroData   ChCliHero.cpp(199)     -> fixed by 0x0074          (§11.3)
attribState    ChCliAttrib.cpp(156)   -> fixed by 0x0037 + 0x003A (this section)
profession < arrsize(s_profChapter)   ConstChar.cpp(1296)          <- now here
```

The new bound is `cmp esi,0xb` = **11** (getter `0x005AB800`, table `0x00A384F0`), so a
profession must be 0..10. **Two fixes were tried and both are REFUTED:**

1. **`0x0074`'s `b2`/`b3` are not it.** Setting them to 1/2 — the fields upstream names
   `primary`/`secondary` — changed nothing. That is a measured negative against the upstream
   naming on this path, and it is the second time this arc has failed to confirm those names.
2. **Nor is a profession/attribute mismatch.** The hero's agent was `AGENT_SET_PROFESSION
   (200, 3)` (Monk, from the body's content row) while the attributes we send are 17–21
   (Warrior, copied from the player). Matching them — a Warrior body, profession 1 — produced
   the **identical** assert.

**And it regresses a working hero.** The crash fires with *or without* the trailing `0x0072`,
so it is the attribute pair itself. A hero that renders perfectly well without attributes
(§11.2) dies with them. `--hero-attribs` is therefore **OFF by default**: a default-on flag
that crashes is worse than no flag.

**Two failed fixes is the repo's own stop-and-study line, so this stops here.** The next
session's first move is static, not another run: the profession getter `0x005AB800` has 12
callers, and three of them — `0x00819FF2`, `0x0081A092`, `0x0081A261` — sit in the attribute
code the pair activates. Read those three and find where the out-of-range `profession` is
loaded from. That is a desk task needing no client.

## 14. THE HERO IS AUTHORED — every gate cleared, and the row draws `Norgu`

Reading the three callers named at the end of §13 answered it, and the answer was one
message plus one ordering. **The full chain now completes and the client survives it.**

### 14.1 Where the bad profession came from

The three callers of the profession getter `0x005AB800` all sit in one function,
**`0x00819EF0`**, whose prologue is the whole answer:

```
0x00819EF8  mov esi,[ebp+8]        ; the attribState record
0x00819F17  call 0x47f660          ; GetLocalPlayerContext()
0x00819F1E  mov ebx,[eax+0x2c]
0x00819F21  add ebx,0x6bc          ; <-- ctx[0x2c]+0x6BC
0x00819F2C  call 0x81fad0          ; (array, [esi] = agent id) -> primary   -> [ebp-8]
0x00819F3F  mov [ebp-0x1c],eax     ;                          -> secondary -> [ebp-0x1c]
```

It takes the attribState record, reads **its agent id**, and looks that agent's **primary and
secondary professions** up in the array at `ctx[0x2c]+0x6BC`. Callers 2 and 3
(`0x0081A092`, `0x0081A261`) then hand each straight to `s_profChapter` **guarded only
against 0, never against the bound**. Caller 1 (`0x00819FF2`) is a different shape — it maps
an *attribute* to its profession via `s_attrib` first.

**`ctx[0x2c]+0x6BC` is the array `studies/profession/RUNS.md` already identified as written
only by `0x00B7` — and we had only ever sent `0x00B7` for the player.** An agent absent from
it yields an out-of-range profession, and `ConstChar:1296` fires.

> **THERE ARE TWO PROFESSION STORES, and conflating them cost this arc an afternoon.**
> `0x00A6` writes the **agent's** profession bytes — what the roster label builder reads,
> which is why the hero row already said `Mo1`. `0x00B7` writes the **`+0x6BC` array** — what
> the **attribute** code reads. Setting one does nothing for the other. That is why matching
> the body's profession (§13.2) changed nothing: it was `0x00A6`'s store all along.

### 14.2 `s_attrib`, read in passing

51 rows × 20 B at **`0x00A35740`**: `+0x00` profession, `+0x04` a **self-referential index**
(row *i* holds *i* — a closure the artifact could have refuted), `+0x08`/`+0x0C` string ids,
`+0x10` an **is-primary** flag set on **exactly ten rows, one per profession 1..10**.
Attribute **17 is Strength** (profession 1), matching the player ranks this server sends.

**Attributes 26–28 and 45–50 carry profession `11`** — out of range for `s_profChapter`.
Those are the PvE title tracks, which belong to no profession, and they are why the guard at
caller 1 exists at all.

### 14.3 The last gate was ORDER, and this repo already knew it

With `0x00B7` sent for the hero, `ConstChar:1296` cleared and the assert moved to
**`attribState`, `ChCliAttrib.cpp(435)`** — a *different line* from the `:156` that opened
§12. The fix was not new information: `authsrv.py`'s own comment above the player's pair
records that exact assert with `0xb7` named in the stack trace, and the remedy —
**points first, profession second**. Sending `0x00B7` before `0x0037` reproduced it exactly.

**The complete chain, all four gates, each cleared by a measured change:**

| gate | assert | cleared by |
|---|---|---|
| 1 | `charHeroData` `ChCliHero.cpp(199)` | `0x0074` |
| 2 | `attribState` `ChCliAttrib.cpp(156)` | `0x0037` |
| 3 | `profession < arrsize(s_profChapter)` `ConstChar.cpp(1296)` | `0x00B7` **for the hero's agent** |
| 4 | `attribState` `ChCliAttrib.cpp(435)` | **order**: `0x0037` → `0x00B7` → `0x003A` |

And the `0x0072` diagnostic — which **ASSERTED** on 2026-08-12 under this same client state
minus our messages — now **completes silently**. That was the refutable experiment this arc
opened with, and it has flipped.

### 14.4 The payoff: the row stops saying "Hatcher" and starts saying "Norgu"

The measurement that makes this more than "no crash". With the hero record incomplete, the
row read `Mo1 Hatcher [Collector]` — the **body's** name, per §10.2's rule that the roster
label builder reads the agent. With the record **complete**, the same run's row reads:

**`Mo1 Norgu`**

Norgu is `s_heroClientData` row 1. **The client switched name sources.** Once the hero data
record is satisfied, the roster stops labelling from the agent and resolves the hero's own
identity from the static table — which is exactly §0's claim, *"a hero carries no name and
must resolve its identity through `s_heroClientData`"*, now measured rather than argued. It
also independently confirms the recon's row-1 resolution, from the screen instead of from
`textrec.py`.

`--hero-attribs` is **ON** by default again; `--no-hero-attribs` is the control arm, and it
is a real one — it produces a hero row labelled from the body instead of the hero table.

### 14.5 What a hero now needs, end to end

```
0x0074  MERCENARY_INFO          hero index 1..39      -> creates charHeroData
0x01D2/0x01CB                   party build window
0x01C2  PARTY_HERO_ADD          msg+8 = hero index, msg+0xc = AGENT ID
0x01D3/0x01B2                   commit + set mine
0x0056/0x0057/0x0020            the body, at that agent id
0x00A6  AGENT_SET_PROFESSION    the agent's own profession bytes
0x0037  AGENT_ATTRIBUTE_POINTS  creates attribState        <-- order
0x00B7  PLAYER_UPDATE_PROFESSION  ctx+0x6BC, for the HERO   <-- is
0x003A  AGENT_UPDATE_ATTRIBUTES   fills attrib[]            <-- load-bearing
```

**Still open:** the hero's **skill bar** (§4 — the attribute half is now solved, the eight
skill slots are not), the **c2s** direction (§3.3), `0x0074`'s remaining 17 fields, and
follow AI.

### 14.6 A guard this arc strengthened

Adding the hero's `0x00B7` turned `test_agentlife`'s syntax-tree check red, correctly: it
requires every `0x00B7` send site to build through `spawn_profession_values()` rather than a
literal list, and the hero's site did not. Fixed by giving the builder an `agent_id`
parameter (defaulting to the player, so no existing caller moved).

The check itself had a latent hole — it **reassigned** its verdict per match, so with two
send sites it graded only whichever came **last** in the file. It is now `all()` over a
counted list. Proven both ways: sabotaging the hero's site (last) fails as before, and
sabotaging the **player's** site (first) now fails too, where the old logic would have passed
it. The arc got lucky in the safe direction — the new site happened to be last, so the hole
announced itself instead of hiding.

## 15. The skill bar — §4's negative was a SCOPING ERROR, and `0x0072` is HeroActivate

### 15.1 `0x00DA` was in our tree the whole time

**§4 is CORRECTED.** It recorded "no skill-bar-shaped field (8 discrete skill ids) anywhere"
after scanning `0x0074`, `0x01BF`, `0x01C2` and every declared **SEND**-direction shape. That
search space excluded the answer:

**`0x00DA` SKILLBAR_UPDATE — `[agent_id, array32[8], array32[8], u8]`, RECV, agent-keyed,
eight slots.**

It is a server→client message this repo has been sending **for the player every session**.
The negative was never about the wire; it was about where we looked. **That is the fourth
time in this arc that the mechanism was already in the tree** — after `0x0037`, `0x003A` and
`0x00B7`. The recurring shape is worth naming: *every* piece of a hero turned out to be an
existing **agent-keyed** message we only ever addressed to the player.

Sent to the hero's agent it is accepted — 75 bytes, eight skill ids, no assert.

> **Honest limit: this is delivery, not display.** The hero's bar is accepted and the client
> survives, but **I have not seen it rendered.** The hero panel is opened by clicking the
> commander-slot button, and that click **crashes the client** (§15.3). So "the hero has a
> skill bar" is supported by the message's shape and its acceptance, not by a screenshot of
> eight icons. Do not upgrade this to OBSERVED-on-screen until someone sees the bar.

### 15.2 `0x0072` is HeroActivate, not a diagnostic

The arc opened this message as a refutable probe. It is the **activation**, and the client
names its own fields: the worker's miss path calls out with the format string at `0xa95888`,

`HeroActivate (hero %d, agent %d, inventoryId %d, aiMode %d)`

— four fields, in that order, matching the descriptor `[word, agent_id, dword, dword]`
exactly. Renamed `agents.hero_activate(hero_id, agent_id, inventory_id, ai_mode)`.

**Measured, and this is the readout that settles it.** Two runs identical but for `0x0072`:

| `0x0072` | roster row | commander flag 1 |
|---|---|---|
| not sent | `Mo1 Hatcher [Collector]` — the **body's** name | greyed |
| **sent** | **`Mo1 Norgu`** — `s_heroClientData` row 1 | **green, enabled** |

So `0x0072` is what promotes a labelled body into a **hero**: the client switches the roster
label from the agent to the static hero table, and `GmHeroCommander` binds the slot (which
needs non-null `heroData` and non-zero `agentId`, asserts `:120`/`:121`). §14.4 credited the
name switch to "the record being complete"; **that was half right and is now sharpened** —
completeness is necessary, and `0x0072` is the trigger.

**And `aiMode` is field 4.** The Fight/Guard/Avoid-Combat stance (`CHAR_AI_MODES == 3`, §3.2)
is therefore **server-settable**, a partial answer to §3.3: we still cannot see the client
*change* stance c2s, but we can *set* it. That is one of the arc's oldest open questions
moving, from the wrong direction to the useful one.

### 15.3 The commander-slot click crashes — a new, bounded unknown

Clicking the hero's commander-slot button (the enabled `1`) takes the client down. It is a
**UI path we have never fed**, and the obvious suspect is named in the very format string
above: **`inventoryId`**, which we send as 0. A hero panel wants equipment. Bounded, cheap to
attack next, and it is the reason §15.1's limit stands.

### 15.4 The complete hero, as it now stands

```
0x0074  MERCENARY_INFO           hero index 1..39        creates charHeroData
0x01D2/0x01CB                    party build window
0x01C2  PARTY_HERO_ADD           msg+8 hero index, msg+0xc AGENT ID
0x01D3/0x01B2                    commit + set mine
0x0056/0x0057/0x0020             the body, at that agent id
0x00A6  AGENT_SET_PROFESSION     the agent's own profession bytes
0x0037  AGENT_ATTRIBUTE_POINTS   creates attribState          0x00B7  PLAYER_UPDATE_PROFESSION ctx+0x6BC, for the HERO       > order matters
0x003A  AGENT_UPDATE_ATTRIBUTES  fills attrib[]               /
0x00DA  SKILLBAR_UPDATE          the eight slots
0x0072  HERO_ACTIVATE            hero, agent, inventoryId, aiMode
```

**Still open:** the commander-panel click (§15.3), `inventoryId`/equipment, `0x0074`'s other
17 fields, the **c2s** direction proper (§3.3 — placing a flag, changing stance from the
client), and follow AI.

## 16. `inventoryId` — REFUTED as the cause, twice, and the real one is named

§15.3 nominated `inventoryId` (HeroActivate field 3, sent as 0) as the suspect behind the
commander-panel click crash. **It is not, and the suspicion was mine to retract.**

### 16.1 The click crash is `commander`, not inventory

Naming the assert should have come first. It is:

```
Assertion: commander        P:\Code\Gw\Ui\Game\GmView.cpp(5890)
```

Not one of the eight inventory asserts — `ItCliApi:1194`
`context->inventoryTable.Get(inventoryId)` was the plausible one. `asserts.py` does not read
line 5890; it is one of the 371 sites its fixed patterns miss, a live reminder that its
answers are floors. The site is `0x004E38EB`, `push 0x1702` = 5890.

### 16.2 And a non-zero `inventoryId` changes nothing

Two runs with `inventoryId = 1`:

- **On the activation path:** accepted, no assert. It does **not** trip `ItCliApi:1194`, so
  the field is not validated anywhere this arc can reach.
- **With the commander click:** the **identical** `commander` / `GmView.cpp(5890)` assert.

So `inventoryId` is **inert on every reachable path** and is **not** what the click wants.
Both outcomes the experiment allowed came back negative — the field's meaning stays NOT
FOUND, but the crash is no longer mis-attributed to it.

### 16.3 What the click actually wants

Read statically this time, rather than guessed:

- Commander objects live in a **container at `ctx+0x20`**. `heroCommanderSlot[7]` at
  `ctx+0x30..+0x4c` holds **keys into it**, not the objects: the slot version
  (`0x00524DD0`) bound-checks `cmp ecx,7`, reads `[eax + ecx*4 + 0x30]`, and looks *that* up
  in `ctx+0x20`.
- **`0x00524C40` is a GET-OR-CREATE** — it looks up `ctx+0x20` and, on a miss, walks the
  7-slot array to make one. `GmHeroCommander:81`'s `slotIndex < arrsize(...)` lives inside it.
- **`0x00524DB0`, the one the click uses, does NOT create.** It looks up and asserts. That
  asymmetry is the whole bug: our hero has no entry in `ctx+0x20`, and the click takes the
  non-creating path.
- The creator's second caller, `0x00524FA4`, sits in a **loop over 12-byte entries at
  `ebp-0x58`** — the `activeHeroes` stack buffer built by scanning the party's agents
  (`GmHeroCommander:214`, `cmp ebx,7`).

**So the next question is precise:** the party-agent scan that fills `activeHeroes` and
creates a commander per entry either never runs for our hero, or registers it under a key
different from the one `GmView:5890` looks up. Deciding which is desk work on `0x00524F80`'s
scan filter and its key — no client needed.

*(One tension worth carrying: commander **flag 1 is enabled on screen**, so part of this
machinery did bind, while the container lookup still misses. A key mismatch fits that better
than "the scan never ran".)*

### 16.4 Also wired, and NOT tested

`--hero-ai-mode` now sets HeroActivate's field 4, the Fight/Guard/Avoid-Combat stance. It is
**untested**: no run has varied it, and nothing here is evidence that the stance takes
effect. It exists so the next session can ask.

## 17. The desk work: the commander mechanism mapped, the prediction refuted

Asked to do desk work rather than more runs, so: the whole commander path is now read out of
the binary. It produced one prediction, the prediction was **wrong**, and what it eliminated
is worth more than what it proposed.

### 17.1 The mechanism, end to end

**The iterator `0x008563B0(partyId, index)`** — read in full rather than guessed at:

```
esi = ctx[0x4c]                      ; the party manager
partyId == 0 -> esi = esi[0x54]      ; "my party" (RESKIN §17's PyCliGetMyPartyId pointer)
index >= esi[0x2c] -> return 0       ; count
return esi[0x24] + index*24          ; base + index * 0x18
```

**Stride `0x18` is exactly `0x01C2`'s entry size**, so this walks the hero entries our
`PARTY_HERO_ADD` appends. That much is structural and solid.

**The scan `0x00524E00`** iterates it and, per entry:

| it reads | `0x01C2` wrote there |
|---|---|
| `cmp [edi+4], ctx[0x44][0x2ac]` — the filter | `msg+8` |
| `mov eax,[edi+8]` — the **commander key** | `msg+0x10` |

and writes `activeHeroes[n] = {slot, -1, key}` (12-byte entries at `ebp-0x58`), bounded by
`GmHeroCommander:214`'s `cmp ebx,7`. Then `0x00524FA4` calls the **get-or-create**
`0x00524C40` with that key.

**The asymmetry that is the bug:** `0x00524C40` creates on a miss; `0x00524DB0` — the
resolver `GmView:5890`'s click uses — only looks up, and asserts. Our hero has no entry in
the `ctx+0x20` container, so the click dies.

### 17.2 The prediction, and its refutation

We had been leaving `msg+0x10` at **0**, so the reading was: the commander gets registered
under key 0 while the click looks up a real hero id. Prediction: put the hero id in
`msg+0x10` and the click stops asserting.

**Refuted.** With `0x01C2` carrying `(1, 200, 1, 0)` the click produces the **identical**
`commander` / `GmView.cpp(5890)`. No regression either — the roster still reads `Mo1 Norgu`
with slot 1 bound and flag 1 green — so the change is kept as the better-founded value
(`entry+8` *is* what the scan reads as the key) but it is **RECONSTRUCTION, not a fix**.

**What that eliminates is the useful part.** The scan `0x00524E00` has **exactly one caller**,
`0x004E5D85`, inside a GmView **event** handler. If putting the right key in the right field
changes nothing, the leading explanation is no longer "wrong key" but **"the scan never
runs"** — the commander container is populated by a client-side UI event we do not trigger,
not by anything on the wire. That would make the commander panel not server-reachable at all,
which is a different and more useful shape of answer than another field to guess at.

### 17.3 A correction to §11.1, and the confound behind it

§11.1 concluded `0x01C2`'s `msg+8` is the **hero index**. **That is not established, and I
overstated it.**

What H1/H2 actually proved is narrower: `msg+0xc` is the **agent id** — solid, because 200
lies outside every other candidate range and the row only rendered when 200 sat there. But
`msg+8` was only ever shown to accept `1` and reject `200`, and in this test rig
**`PLAYER_NUMBER`, `PLAYER_AGENT_ID` and the hero index are all 1**. Hero index, owner player
number and owner agent id are therefore indistinguishable, and §17.1's filter
(`[edi+4]` vs a widely-used "my id" accessor with 45 call sites) actively suggests *owner*
rather than *hero index*.

**`msg+8` is UNVERIFIED**, and separating it needs a rig where those three values differ —
a different player number, or a hero index ≥ 2. That is the confound this arc warned about
when designing the agent-200 arm, and then walked into one field over.

### 17.4 Where this leaves the click

Three failed fixes now (`inventoryId` twice, the commander key once), which is well past the
stop-and-study line. The study says: **stop treating it as a missing message.** The next move
is to identify which GmView event calls `0x004E5D85`, and whether anything server-side can
provoke it. If nothing can, the commander panel is simply outside what a server authors, and
the hero — which renders, is named from `s_heroClientData`, carries attributes and a skill
bar, and has its commander flag lit — is already complete for every purpose the wire controls.

## 18. Hero index 2 — the confound is broken, and `msg+8` is not the hero index

§17.3 said separating `0x01C2`'s `msg+8` needed a rig where player number, player agent id
and hero index are not all 1. Hero index **2** is that rig.

The wire, with all three finally distinct:

```
0x0074  MERCENARY_INFO (hero 2, ...)
0x01C2  PARTY_HERO_ADD (party 1, wordA 1, wordB 200, 2, 0)
        msg+8 = 1 (player number)   msg+0xc = 200 (agent)   msg+0x10 = 2 (hero id)
0x0072  HERO_ACTIVATE (hero 2, agent 200, inventory 0, aiMode 0)
```

**The row renders, and it reads `Mo1 Goren`.**

Two results, one negative and one positive:

- **`msg+8` is NOT the hero index — OBSERVED.** It carried **1** while the hero was **2**,
  and the row rendered anyway with hero 2's identity. §11.1's original reading is now
  refuted by experiment rather than merely doubted (§17.3 doubted it; this settles it).
  What `msg+8` *is* remains **UNVERIFIED**: it accepts 1 and rejects 200, and the scan's
  filter (§17.1) compares `entry+4` against a widely-used "my id" accessor, which points at
  **owner**. Our `PLAYER_NUMBER` and `PLAYER_AGENT_ID` are both 1, so owner-player-number
  and owner-agent-id are still indistinguishable — a narrower confound than before, and the
  rig to break it is a player number that differs from the player's agent id.
- **`s_heroClientData` row 2 is `Goren`, confirmed from the screen.** The recon resolved rows
  1 and 2 as Norgu and Goren via `textrec.py` against the archive; both are now independently
  confirmed by the client rendering them, from a different direction entirely. The hero
  catalogue reading is solid.

**Still confounded, and worth naming:** three fields carried the value 2 in this run —
`0x0074`'s hero id, `0x01C2`'s `msg+0x10`, and `0x0072`'s hero id. So "the identity comes
from the hero id" is established, but *which message* supplies it is not. The discriminator
is one run: give `0x01C2`'s `msg+0x10` a different value (say 3) while `0x0074`/`0x0072`
keep 2, and read which name appears.

The commander slot stayed bound and flag 1 stayed green throughout, so nothing here
regressed the working hero.

## 19. Splitting `msg+0x10` — `0x01C2` carries no hero identity at all

The last confound from §18: three fields carried the value 2, so "identity comes from the
hero id" was established while *which message* supplies it was not. One run splits them.

Prediction on record before the run, with the target named: `s_heroClientData` row 3's name
id is 36274, which `textrec.py` resolves to **Tahlkora**. So — **Tahlkora** means the
identity comes from `0x01C2`'s `msg+0x10`; **Goren** means it comes from `0x0074`/`0x0072`.

```
0x0074  MERCENARY_INFO (hero 2)
0x01C2  PARTY_HERO_ADD (party 1, wordA 1, wordB 200, 3, 0)   <- msg+0x10 = 3
0x0072  HERO_ACTIVATE  (hero 2, agent 200, 0, 0)
```

**The row reads `Mo1 Goren`.**

### 19.1 The result

**The hero's identity comes from `0x0074`/`0x0072`, not from `0x01C2`.** The party-add
message carried a *different* hero id and the client ignored it completely — no crash, no
change, no Tahlkora.

That sharpens §0's framing further than it was stated. The original claim was "a hero carries
**no name** on the wire and must resolve through `s_heroClientData`". The stronger, measured
version is: **`0x01C2` carries no hero IDENTITY at all.** Its five fields are a party id, an
owner-ish word (§18: not the hero index, still UNVERIFIED between owner-player and
owner-agent), the agent id, and two bytes. The hero's *whole* identity arrives on the
data-cache family.

### 19.2 `msg+0x10` is inert on everything observable

Worth stating plainly because it is now doubly unconfirmed:

- §17.1 read it as the **commander key**, from `GmHeroCommander`'s scan taking `[edi+8]`.
- §17.2 put the hero id there and the panel click asserted **identically** — no fix.
- §19 puts a *wrong* value there and **nothing changes** — no name change, no crash.

So `msg+0x10` does not drive the roster label, does not repair the commander click, and does
not complain when wrong. The scan genuinely reads `entry+8` — that disassembly stands — but
every consequence we can observe is indifferent to it, which is consistent with §17.2's
leading explanation that **the scan never runs** in our session. Its role stays
**RECONSTRUCTION**, and the value we send (the hero id) is a best guess, not a measurement.

### 19.3 What is left

One confound survives: `0x0074` and `0x0072` both carried hero 2, so which of the two
supplies the identity is undetermined. The same trick splits them — give `0x0072` a different
hero id from `0x0074`'s — with the caveat that `0x0072` is the activation and may simply
assert rather than render, which would itself be an answer.

## 20. Splitting `0x0074` and `0x0072` — they are two halves of one keyed record

The last confound. Three outcomes were named before the run: the name follows `0x0074`
(Goren), the name follows `0x0072` (Tahlkora), or `0x0072` asserts `charHeroData` because its
field 1 *selects* the record `0x0074` made.

```
0x0074  MERCENARY_INFO (hero 2)      <- creates a record for 2
0x01C2  PARTY_HERO_ADD (..., 2, 0)
0x0072  HERO_ACTIVATE  (hero 3, ...) <- activates 3, for which no record exists
```

**Outcome C.** `Assertion: charHeroData  P:\Code\Gw\Char\Cli\ChCliHero.cpp(199)` — the
**identical** assert §11.3 got by omitting `0x0074` entirely.

### 20.1 The result, and why it is better than an A/B answer

**`0x0074`'s field 1 is the record KEY; `0x0072`'s field 1 is a SELECTOR into the same
namespace, and the two must agree.** A mismatched selector is indistinguishable — same
assert, same line — from the record never having been created at all.

So the question "which message supplies the hero's identity" was subtly malformed, and the
run says so rather than picking a side. Neither supplies it independently: **`0x0074` creates
a keyed record that carries the identity, and `0x0072` activates the record under that key.**
The name the roster renders is the *record's*, reached through a key both messages must name
identically. That is a cleaner mechanism than either branch of the A/B would have described.

It also **re-confirms §11.3 from a new direction**: that section established `0x0074` creates
the `charHeroData` record by removing it. This reproduces the same assert by *keeping* the
message and mismatching its key — a different manipulation reaching the same gate, which is
the kind of agreement worth more than a repeat of the same arm.

### 20.2 The hero family, as a whole, now reads

| message | field 1 | role |
|---|---|---|
| `0x0074` MERCENARY_INFO | hero id | **creates** the `charHeroData` record (the identity lives here) |
| `0x01C2` PARTY_HERO_ADD | owner-ish word (UNVERIFIED) | roster slot → agent id at `msg+0xc`; **carries no identity** (§19) |
| `0x0072` HERO_ACTIVATE | hero id | **selects** that record and activates it; also `agentId`, `inventoryId`, `aiMode` |

Three arcs of confound-splitting, each one field at a time, and the shape that emerges is:
**identity is the data-cache record's, the party message only binds a slot to an agent.**

### 20.3 Still open

`0x01C2`'s `msg+8` (owner-player vs owner-agent — both 1 in this rig), its `msg+0x14`,
`0x0074`'s other 17 fields, `msg+0x10`'s real role (§19.2 — inert on everything observable),
the commander-panel click (§17.4 — probably a client-side UI event, not a message), the
untested `aiMode`, and follow AI.

## 21. `msg+8` is the OWNER PLAYER NUMBER — and the arm exposed two "my id" notions

The rig §18 asked for: `--player-number 2` makes `PLAYER_NUMBER` (2) differ from
`PLAYER_AGENT_ID` (1), so the two candidate readings of `0x01C2`'s `msg+8` finally separate.
`--hero-owner` overrides `msg+8` alone. Two arms differing in nothing else:

| arm | `msg+8` | roster row | commander slot / flag 1 |
|---|---|---|---|
| **A** | **2** (the player number) | **`Mo1 Goren` renders** | **absent / greyed** |
| **B** | **1** (the agent id) | **no hero row** | **bound / green** |

### 21.1 The answer

**`msg+8` is the owner PLAYER NUMBER — OBSERVED.** The roster row renders exactly when
`msg+8` equals the player number this server declared, and not when it equals the agent id.
That is consistent across all three rigs now: the original (`PLAYER_NUMBER` 1, `msg+8` 1 →
renders), H1 (`msg+8` 200 → no row), and arms A/B here. §11.1's "hero index" reading was
withdrawn in §17.3, refuted in §18, and the field is now positively identified rather than
merely narrowed.

### 21.2 The unexpected half: the two filters disagree

Arms A and B are **exact mirrors** — whichever value makes the roster row appear makes the
commander binding vanish, and vice versa. Both consumers read the same `entry+4`, so they
must be comparing it against **different** "my id" values:

- the **roster UI** compares against the player number we declared (2),
- the **`GmHeroCommander` scan** (§17.1) compares `entry+4` against `ctx[0x44][0x2ac]`, which
  evidently stayed **1**.

**RECONSTRUCTION, and the honest reading:** `--player-number` changes only what *we send*, not
what the client believes about itself. `ctx[0x44][0x2ac]` is computed from something our
override never touched, so forcing `PLAYER_NUMBER` to 2 **desynchronised** the client's own
notion of "me" from ours. In the default rig both are 1 and everything agrees, which is why
the hero worked all along.

**What is still not settled:** whether `ctx[0x44][0x2ac]` is the player's *agent id* or a
client-side *player number* derived elsewhere — because in this rig it is 1, and so is
`PLAYER_AGENT_ID`. Breaking that needs the client's own value moved, not ours, which means
finding what writes it rather than another flag on our side.

### 21.3 The practical consequence

Do not use `--player-number` for anything but this experiment. It puts the server's claimed
player number out of step with the client's internal one, and the visible symptom is
narrow and misleading: the roster row and the commander binding become mutually exclusive.
The default (1) is the value that satisfies both, and it is the default for that reason.

## 22. What writes `ctx[0x44][0x2ac]`: `0x0199` INSTANCE_LOAD_INFO, field 1

§21.2 left the client's own "my id" unnamed. Desk work, no client:

- **`ctx[0x44]` is the MISSION subsystem.** The accessor `0x0084DD70` sits in **MsCliApi**
  (its neighbours assert `MsCliApi:387/396/406/821`).
- **`codescan.py --field 0x2AC --writes`** finds eleven stores image-wide; three are in the
  MsCliApi range, and two of those are real writes rather than an init-zero:
  `0x0084EF13` and `0x0084F24F`. Both take a message struct as `[ebp+8]` and copy **`[msg+4]`
  — field 1** — into `mission_ctx[0x2ac]`; the second bulk-copies a dozen more fields
  alongside it, which is what a message handler looks like.
- Neither has a `call` xref: each VA sits in **one aligned `.rdata` word** (`0x00BCB2B4`,
  `0x00BCB368`) — dispatch-table entries. `msgshape.py --all` matches them to opcodes:

| opcode | handler | shape |
|---|---|---|
| **`0x0199` INSTANCE_LOAD_INFO** | `0x0084EF00` | `[agent_id, u16, u8, u32, u8, u8]`, 15 B |
| `0x01A4` | `0x0084F230` | `[agent_id, u16, u8, u32, u8, u8, u32, vec2, u16, u8, u8, string16(20), blob(8)]`, 81 B |

**`ctx[0x44][0x2ac]` is `0x0199`'s field 1** — the message this server has sent at every
instance load since the beginning, whose field 1 the client's own descriptor types
`agent_id` and which we fill with the player's agent id. `0x01A4` writes the same slot from
its own field 1 and we never send it.

> **CORRECTED 2026-08-17 BY RETAIL'S OWN WIRE: field 1 is the PLAYER NUMBER, not the
> agent id.** The paragraph above reads the client's descriptor — which types field 1
> `agent_id` — and concludes we are right to fill it with the player's agent id. The
> Factions captures separate the two for the first time, and they disagree with the type
> name. Measured across all four game channels of
> `vault/captures/live/20260817T183756` (OBSERVED):
>
> | channel | `0x0199` field 1 | local player's `0x0059` | `0x0022` controlled agent |
> |---|---|---|---|
> | 52294 | **1** | player_number 1, agent **27** | 27 |
> | 58378 | **1** | player_number 1, agent **27** | 27 |
> | 58389 | **1** | player_number 1, agent **395** | 395 |
> | 60966 | **1** | player_number 1, agent **311** | 311 |
>
> Field 1 tracks the player NUMBER (constant 1) and never the agent id (27, 395, 311).
> **A descriptor's field TYPE is what the client parses it as, not what the server puts
> in it** — the same distinction §1.2 already drew when OpenTyria's field names turned out
> to be decoration over a positional layout.
>
> Two consequences. **§21.2's split filter is explained**: the roster UI and the
> `GmHeroCommander` scan compare `entry+0x4` against different "my id" values because
> `ctx[0x44][0x2ac]` holds the player NUMBER, so a `0x01C2` carrying the player number
> renders the row while one carrying the agent id satisfies neither. That is exactly the
> mirror-image result §21.2 measured and could not explain. **And our server has never
> been bitten**: we fill field 1 with `PLAYER_AGENT_ID`, which is 1, and our
> `PLAYER_NUMBER` is also 1 — divergence D7's confound again, the two id spaces collapsed
> by a solo instance. A multi-player instance would separate them and we would be wrong.
>
> Also OBSERVED here and worth its own line: **player_number is not a stable identity**.
> The local player is player 1 from their own client's view, while agents 91 and 337 both
> carry number 4, and 379/309/349 all carry 18 — the numbers are recycled slots, not
> identities. Anything keyed on player_number across time needs to know that.
>
> **Send site fixed 2026-08-18**: `authsrv.py`'s `0x0199` now fills field 1 with
> `PLAYER_NUMBER`, retiring the "we would be wrong" sentence above. Consequence for the
> experimental flag: `--player-number` now moves the roster filter and the commander
> scan's `ctx[0x44][0x2ac]` together, so §21's mirror (row and binding mutually
> exclusive) is a historical rig, not a reproducible one. §22.1 and §25.3 below carried
> the pre-correction "agent id" reading for a day after this block landed; both are
> corrected in place.

### 22.1 This explains §21's mirror exactly

The two filters read the same `entry+4` and compare it against different things:

- the **roster UI** against the value we used as `PLAYER_NUMBER` (which also feeds `0x0059`,
  `0x00B0`/`0x00B1`, `0x01CB`'s party member and the player's `model_id`, so "player number"
  is the coherent label but not fully isolated),
- the **`GmHeroCommander` scan** against `ctx[0x44][0x2ac]` = **`0x0199` field 1** — which
  in that rig held **1** because our server filled it with `PLAYER_AGENT_ID`. (This line
  originally read "= the player's agent id", written from what we SENT; retail fills the
  field with the player **number** — §22's CORRECTED block — and the send site now does
  too, 2026-08-18.)

`--player-number 2` moved the first and left the second at 1, so exactly one of the two could
match at a time. In the default rig `PLAYER_NUMBER` and `PLAYER_AGENT_ID` are both 1, both
filters see 1, and the hero binds — which is why every earlier run worked and why the
mirror only appeared once the two were forced apart.

### 22.2 A trap removed

`0x0199`'s field 1 was a **literal `1`** at the send site, not `PLAYER_AGENT_ID`. Harmless
today because the constant is also 1 — and exactly the kind of thing this repo keeps
recording after it bites: the value now demonstrably feeds a filter three subsystems away,
so a literal that silently stops tracking the constant is worth closing before it matters.
Now `PLAYER_AGENT_ID`, with the reason attached.

### 22.3 The confirming experiment, and why it was not run

The prediction is clean: set `0x0199` field 1 **and** `msg+8` to the same value and both
consumers agree again. It was not run because that field is the player's own agent id — the
body is created at `PLAYER_AGENT_ID`, so moving one without the other desynchronises the
player rather than the hero, and the run would measure our own inconsistency. The honest
version of the test is to move `PLAYER_AGENT_ID` itself, which touches the spawn path and
deserves its own arm rather than a footnote to this one.

## 23. A FULL AUTHORED PARTY — three heroes and a henchman, in one roster

The capability step. `--hero` now takes a list, and every hero gets its own agent id and
definition from one place (`hero_slots()`), because an agent id reused for a second body
leaves the client holding one agent's state under another's name.

```
0x01BF PARTY_HENCHMAN_ADD (party 1, agent 30,  ...)
0x01C2 PARTY_HERO_ADD     (party 1, owner 1, agent 200, hero 1)
0x01C2 PARTY_HERO_ADD     (party 1, owner 1, agent 201, hero 2)
0x01C2 PARTY_HERO_ADD     (party 1, owner 1, agent 202, hero 3)
... bodies, attribute trios, skill bars, then one HERO_ACTIVATE each
```

**The Party Members window:**

```
    W0 Test Warrior
[1] Mo1 Norgu
[2] Mo1 Goren
[3] Mo1 Tahlkora
    Mo1 Hatcher [Collector]
```

### 23.1 What this measures that a single hero could not

- **The commander slot array assigns sequentially and independently.** Slots 1, 2, 3 appear
  as separate numbered buttons, one per hero — the `heroCommanderSlot[7]` array of §3.1
  filling up, not a single slot being reused.
- **Each hero resolves its OWN identity.** Three different `s_heroClientData` rows render
  three different names from three `0x0074` records keyed by three hero ids. The keyed-record
  model of §20 holds at n=3, which is the first time it has been tested past one.
- **Heroes and henchmen coexist in one roster, and the client distinguishes them visually.**
  The henchman row has **no numbered button**; the heroes do. That is §3.1's reconstruction
  (individually-flaggable hero slots vs henchmen-as-a-group) and the wiki's "three individual
  flags plus one all-heroes-and-henchmen" (§6), both now visible on screen rather than
  inferred from an 8-way dispatch.
- **`s_heroClientData` row 3 = `Tahlkora`, confirmed from the screen.** Predicted in §19 from
  `textrec.py` before the run that would show it; the row never rendered in that arm because
  the client ignored `msg+0x10`. It renders here. Rows **1, 2 and 3** are now each confirmed
  from two unrelated directions — archive resolution and the client's own rendering.

### 23.2 Guards, mirroring the client's own bounds

`--hero` refuses more than **7** (`PtPlayer:332` and `GmHeroCommander:214` both `cmp 7`,
`GmView:4330` names exactly HERO1..HERO7), refuses a **duplicate** hero id (each `0x0074`
record is keyed by that id, so two agents would select one record), and each id still
traverses the 1..39 bound. All four refusals verified.

The single-hero experiment flags (`--hero-owner`, `--hero-swap`, `--hero-roster-id`,
`--hero-activate-id`) apply to the **first** hero only, so a probe arm can never silently
rewrite a whole roster.

### 23.3 Bodies are fanned out

120 units apart along y, because bodies sharing a spot read as one body and "nothing
appeared" is a failure this repo has already paid for once.

## 23. The scan trigger, named — and it is a PARTY event, so the server can reach it

§17.3 left the question "what event runs the `activeHeroes` scan, and can anything
server-side provoke it". Desk work, no client.

### 23.1 The GmView event dispatch

The commander branches are not a function each — they are cases of one switch:

```
004E366A  sub  eax, 0x10000007          ; event id, biased
004E366F  cmp  eax, 0x1c7               ; 456 events
004E3674  ja   <default>
004E367A  movzx eax, byte [eax+0x4E66C4] ; event -> case, a BYTE map
004E3681  jmp  dword [eax*4+0x4E6480]    ; 145 case targets
```

Resolving the two indirections gives the events by name-number:

| event | case | body |
|---|---|---|
| **`0x10000114`** | 90 | the **`activeHeroes` scan** (`0x004E5D20`), which creates the commanders |
| `0x100001A3` | 124 | `GmView:5875` commander |
| **`0x100001A4`** | 125 | `GmView:5890` commander — **the branch that crashes** |

### 23.2 Who raises them

- **`0x10000114` is raised from the PARTY MANAGER**, at `0x008588AD`:
  `push 0x10000114; call 0x633d70`, immediately after setting a flag bit
  (`[esi+0x10] |= 0x80`) and with `[ebp+8] = edi` as the payload. That address is in the
  same `0x0085xxxx` region as `0x01BF`'s worker (`0x00858cb0`) and `0x01CB`'s
  (`0x00859800`).
  **So the answer to §17.3's question is YES — the scan's trigger is a party event, and the
  party is exactly what our messages drive.** The panel is not obviously outside what a
  server can author, which is the opposite of the leading hypothesis §17.3 recorded.
- **`0x100001A4` has two raisers**, and that is the interesting part: `0x00524FD1`, **inside
  the scan itself**, right after the get-or-create loop — and `0x00577E34`, in the **PtHero**
  region (`PtHero:156` `commanderBtnFrame` is at `0x00578123`), i.e. the party-window hero
  button. The same event is fired both by the code that *creates* commanders and by the
  button that *consumes* them.

### 23.3 What this makes of the crash

The intended order is: party changes → `0x10000114` → the scan builds `activeHeroes` →
get-or-create a commander per entry → `0x100001A4` per commander. The party-window button
raises `0x100001A4` **directly**, so pressing it when the scan never created anything takes
the non-creating resolver (`0x00524DB0`, §17.3) straight into the assert.

That is consistent with everything measured, including §19's finding that `msg+0x10` is inert
on every observable: if the scan never ran, the key it would have used cannot matter.

### 23.4 The precise next step

The scan's filter is `[edi+4] == ctx[0x44][0x2ac]`, which §22 identified as `0x0199`'s field
1 = 1, and our `msg+8` is 1 by default — so the filter *should* pass. Two candidates remain
and they are separable by reading, not running:

1. **The iterator.** `0x008563B0` resolves `[ctx+0x4c]` (the party manager) and branches on
   its argument; §17.1 read its loop shape but not what it actually enumerates. If it walks
   party PLAYERS rather than hero entries, `[edi+4]`/`[edi+8]` are not the `0x01C2` fields
   this arc has been assuming, and every key inference above it is unfounded.
2. **The raiser's reachability.** `0x008588AD` sits on one path through the party code; which
   of `0x01D2`/`0x01CB`/`0x01C2`/`0x01D3` reaches it is unread. If none does, the server can
   build a party the client never announces, and *that* is the gap.

Item 1 first: it is cheap and it can invalidate a chain of inferences, which is the better
kind of check to run early.

## 24. CORRECTION — the 38797 pin runs, and my archive diagnosis was wrong

§10.4 recorded, as an environment fact worth not re-paying for, that **"the 38797 pin cannot
currently run"**, blaming its archive. **That is wrong and is retracted.**

The real cause was a server bug that another arc found and fixed the next day: the
2026-08-14 crossbuild key fix lived **inline in the auth branch** and the game branch never
got it, so a 38797 client authenticated fine and was then handed **38833's key** on the game
channel. The handshake "completed", the ARC4 stream was noise, and the client died right
after `INSTANCE_LOAD_INFO` with `Code=007` and zero c2s. Fixed as one shared
`bind_key_to_build()` with an AST regression check that both channels reach it
(`test_handshake.py` §0). Full record: `studies/unitmodels/U7-RUN.md`.

**The evidence was in my own log the whole time.** That first run printed
`keys: 2 key files present; starting with the newest, rurik_dh_2026-08-13…` and, two lines
later, `GAME version: build=38797`. I read the map-row preflight refusal — which was real,
and about maps 146/148 — and carried it over onto a **map 90** run that failed for an
entirely different reason.

**Re-tested 2026-08-17 with the fix in:** the 38797 pin reaches `body is in the map`, the log
now reads `keys: re-selected 2026-07-29_221c13772c7a to match the client's build 38797 (had
2026-08-13_64fae3b1369b)`, and the hero renders **identically** — `Mo1 Goren`, commander slot
1 bound, flag green.

**So the whole hero arc reproduces on the PIN**, not only on 38833. That is worth more than
the retraction: every §10–§23 result was measured on 38833, and the repo's canonical build
now shows the same behaviour.

### 24.1 The same mistake, twice in two days, in both directions

Worth stating plainly because it is a pattern and not bad luck. Yesterday I recorded that a
server-side `NameError` and a bad map row **present identically from the client's side**, and
that another session had spent its first attempt on the archive because of it. I had already
made that exact error myself, one day earlier, and written it into a findings doc as a
measured environment fact.

The correct instinct is in `RUNBOOK.md`'s own advice and worth repeating here: **`Code=007`
means read `gamesrv.log` first.** A preflight refusal about map A is not evidence about a run
that serves map B, and a diagnosis that survives only because nobody re-tested it is not a
measurement.

### 24.2 Collision hazards carried over from U7-RUN.md

That record's other three failures are about experiments fighting themselves, and two apply
directly to this arc:

- **Do not combine a measurement arm with `--probe` or the standing enemy.** U7's run 3 had a
  burrow cycle, combat AI and a probe all driving one creature while it tried to measure an
  animation rate; `probes.py`'s burrow step deliberately re-creates the body at a **fresh
  agent id**, which is a second body. Every hero arm here ran without probes, which was luck
  as much as design — say it out loud in the next one.
- **`--game-args` needs the `=` form.** Independently hit here (§10.4) and recorded there with
  the reason: argparse only accepts a `--`-leading value if it contains a space, which is why
  `'--probe burrow'` works and `'--practice-target'` does not.

## 25. The iterator confirmed, and `0x01C2` drives a DIFFERENT path than the scan

§23.4 named two candidates and said to take the first because it could invalidate a chain of
inferences rather than add to one. It did not invalidate it — it confirmed it, and then the
second candidate turned up the real asymmetry.

### 25.1 The iterator walks the hero array — confirmed against the writer, same build

`0x008563B0` resolves to `party->container[0x24][index]`, bound `[party+0x2c]`, **stride 24**.
Read `0x01C2`'s worker on the SAME build to check that against the writer rather than accept
a size coincidence — and note the worker is **`0x00859010` on 38833**, not the 38797 address
this arc had been quoting; reading a pinned-build address in the other binary is exactly the
cross-build error the verifiers warned about, and I nearly made it here.

Decoding the handler's push order (`push [eax+4]` last = first arg), every §1.2 offset
reproduces:

| stack | wire | store |
|---|---|---|
| `[ebp+0xc]` | `msg+8` | **entry+4** |
| `[ebp+0x10]` | `msg+0xc` | **entry+0** |
| `[ebp+0x14]` | `msg+0x10` | **entry+8** |
| `[ebp+0x18]`, `[ebp+0x1c]` | *client-hardcoded 0* | entry+0xc, +0x10 |
| `[ebp+0x20]` | `msg+0x14` | entry+0x14 |

and the append is `lea ecx,[edi+0x24]` … `base + (count-1)*24`. **Same base, same bound, same
stride as the iterator.** So `[edi+4]`/`[edi+8]` in the scan really are `msg+8` and
`msg+0x10`, and §1.2's layout — read on 38797 — holds on 38833 too.

### 25.2 But `0x01C2` raises a DIFFERENT event than the scan

The worker's tail raises **`0x1000011E`**, not `0x10000114`:

```
008590CA  push 0x1000011e ; call 0x633d70
```

Resolving both through §23.1's dispatch: `0x1000011E` → **case 93** (`0x004E5DE1`),
`0x10000114` → **case 90** (`0x004E5D20`, the bulk `activeHeroes` scan). They are different
handlers.

And `0x10000114`'s raiser — function `0x00858850`, reached through `0x00856920` — has **eight
callers and all of them are UI** (GmView, `Pt*`), none a message worker. **So the bulk scan is
UI-triggered and no message we send provokes it.**

### 25.3 What our message DOES drive

Case 93 is the incremental counterpart, and it uses the same machinery:

```
004E5DED  call 0x84dd70      ; ctx[0x44][0x2ac] -- 0x0199 field 1 (22)
004E5DF2  cmp  [esi+4], eax  ; the SAME my-id filter
004E5DFB  push [esi+8]       ; the key
004E5DFE  call 0x524cc0
```

and `0x00524CC0` walks the party hero array **through the same iterator**, comparing
`entry+4` against the my-id and `entry+8` against the key, incrementing a counter only for
entries that pass the my-id test — i.e. deriving the **slot index** as the position among
*my* heroes.

**This revises §17.2 and §23.3.** "The scan never runs" is right about the BULK scan and
wrong as a whole story: there are two paths, and `0x01C2` drives the incremental one. It also
confirms §21/§22's mirror from a third code path — the commander side compares `msg+8`
against `ctx[0x44][0x2ac]` (= `0x0199` field 1 — `PLAYER_AGENT_ID` as our server filled it
then; retail puts the player **number** there, §22's CORRECTED block, and our send site
follows since 2026-08-18) while the roster row wants the **player number**, and the default
rig satisfies both only because both are 1.

### 25.4 One loose end, flagged rather than papered over

Case 93 reads `[esi+4]` and `[esi+8]` where `esi` is the dispatcher's first argument (the
event payload pointer, `0x004E27E5`). The payload `0x01C2`'s worker builds looks like an
8-byte buffer (`[ebp-8]` and `[ebp-4]`), so `payload+8` would read past it. Either the
payload is larger than it appears, or `esi` in case 93 is not the payload. **I have not
resolved which**, and the field semantics of case 93 above are therefore RECONSTRUCTION, not
OBSERVED — the surrounding structure (same filter, same iterator, slot-index-by-counting) is
solid, the exact payload offsets are not.

## 26. The loose end resolved, a conditional raise found — and my fix refuted twice

### 26.1 §25.4's loose end is closed

The event payload `0x01C2`'s worker builds is a two-dword buffer, and the second dword is
**the entry pointer**: `ecx` is set to the new entry at `0x00859089`
(`lea ecx,[eax+ecx*8]`) and is **never reassigned** through all six field stores or the
branch that follows, so at `mov [ebp-4],ecx` it still holds it. Payload =
`{party_id_or_0, entryPtr}`.

So case 93 reaching entry fields is mechanically possible — it dereferences the pointer the
payload carries. The semantics are independently CORROBORATED by §21's arms, which are
behavioural and need no plumbing read: `msg+8` = 1 (matching `ctx[0x44][0x2ac]`) bound the
commander, `msg+8` = 2 did not. That is exactly "filter the entry's +4 against the my-id".

### 26.2 A conditional raise, OBSERVED

Reading that tail turned up something the arc had not seen:

```
008590AF  cmp edi, [ebx+0x4c]    ; the party appended to vs the manager's cache
008590B2  je  0x8590e2           ; EQUAL -> epilogue, the raise is SKIPPED
...
008590CA  push 0x1000011e ; call 0x633d70
```

**`0x01C2` raises its commander event only on a party-cache MISS.** `[mgr+0x4c]` is the same
cache the worker's own fast path consults at the top (`cmp [edi],esi; je <append>`). That is
a real, previously unrecorded gate.

### 26.3 Two arms, and the honest scoring of each

It made an obvious hypothesis: our `0x01C2` rides straight after `0x01CB` on party 1, warming
that cache, so the raise never fires.

- **Arm A, `--hero-post-commit`** (send `0x01C2` after `0x01B2`): still asserts. **This arm
  proves nothing** and I nearly scored it as a refutation. Post-commit the party is *still
  party 1*, so the cache still holds it and the condition under test never changed — the same
  confound shape as §10.2's body arm.
- **Arm B, `--hero-bust-cache`** (open a build on party **2** immediately before the
  `0x01C2` to party 1, so the manager caches a different party and the hero-add must take the
  slow lookup): **still asserts, identically.**

Arm B genuinely changes the condition, so the hypothesis is **REFUTED**: the cache-hit gate is
real but is **not** why the commander fails to bind.

### 26.4 Where that leaves it

`0x00524CC0` (case 93's callee) does reach the get-or-create — its tail runs on to the
`0x00524C40` call at `0x00524D1B`, so the incremental path *can* create a commander. Two
possibilities survive and they are not separable from the outside:

1. the event still is not firing, for a reason other than the cache; or
2. it fires, and `0x00524CC0`'s search finds no entry matching the key it is handed —
   which loops back to `msg+0x10`, the field §19 measured as inert on every observable.

**What would separate them is runtime observation, not more static reading** — a breakpoint
or a code-cave trace on `0x008590CA`, which is a native-tooling job (`CLAUDE.md` carve-out 3
permits it explicitly and it is the first thing in this arc that has genuinely warranted it).
Three static hypotheses have now been refuted here by experiment; a fourth guess is worth
less than one measurement of whether the event fires at all.

## 27. MEASURED, not guessed: no commander is ever created

§26.4 said the next step was runtime observation rather than a fourth guess. It did not need
a debugger — the question can be answered by reading the **result** instead of trapping the
event, and the commander context turns out to be a plain static global.

`toolkit/clientscan/commanderpeek.py` (new, pure `ctypes` through `keytap`'s reader — the
same `OpenProcess`/`ReadProcessMemory` path the live key capture uses, read-only, no
breakpoint, no injection). The chain is OBSERVED end to end: `0x004E0B90` is
`mov eax,[0xC07850]` plus a non-null assert, so the GmHeroCommander context is a **static
global at `0x00C07850`**; `ctx+0x20` is the container `0x00524DB0` searches; `ctx+0x30..0x4c`
is `heroCommanderSlot[7]`.

Read from a live client with the hero authored, the roster row drawn and the flag lit:

```
ctx                 0x01636760
container ctx+0x20  ptr=0x06C4D4B0  cap=7  count=0  alloc=21
heroCommanderSlot   0 0 0 0 0 0 0
```

**`count = 0`, all seven slots empty.** The context is live and the container is allocated —
`cap=7`, matching `GmHeroCommander`'s own bound, a small corroboration of §3.1 from live
memory rather than from an assert.

### 27.1 What it settles

§26.4 left two possibilities and this cuts them:

1. ~~the event fires and `0x00524CC0`'s search finds no entry matching its key~~ — **REFUTED.**
   A key mismatch would still have *created* nothing only if the search failed **and** the
   create path were never reached; but the container being empty with the party entry
   present means nothing was created under **any** key. There is no commander filed under the
   wrong key either.
2. **the creation path never runs for our hero — CONFIRMED as the live reading.**

And the party entry demonstrably *is* present: the roster row renders with the hero's
archive-resolved name, and that text is drawn from the same `party+0x24` array §25.1
identified. So the data is there and the consumer never consumes it.

### 27.2 What it does not settle, and the honest next step

Empty tells us nothing was created; it does not distinguish **the event never being raised**
from **case 93 running and rejecting the entry at its `my-id` filter**. Both leave the
container at zero.

Separating them needs the one thing still not measured: whether `0x008590CA` executes. That
is a trace — a breakpoint or code cave — and `CLAUDE.md` carve-out 3 permits native tooling
explicitly. The difference from §26.4 is that the case for spending it is now made of a
measurement instead of a fourth hypothesis.

*(The other half — reading `ctx[0x44][0x2ac]` live to check the filter's own value — is not
available the same cheap way: `0x0047F660` resolves the root context through **TLS**
(`mov ecx,[0xc0f300]; mov eax,fs:[0x2c]; mov eax,[eax+ecx*4]`), so it needs the target
thread's TEB rather than a global read. Worth knowing before someone plans it as a five-minute
job.)*

### 27.3 The method note, because it is the reusable part

Three static hypotheses were refuted by client runs on this one question, at roughly seven
minutes each, and the thing that actually moved it was **reading four dwords out of the live
process**. The commander context was a plain global the whole time. When a question is "what
is the client's state", prefer measuring the state over predicting it — the same lesson
`CLAUDE.md`'s "capture the client and read it" states, arrived at the expensive way.

## 28. A subscriber-map reading that was WRONG, and the control that caught it

Having measured the container empty (§27), the obvious next cheap read was the UI event
**subscriber map**: `0x0064CA30` does `mov ecx, 0xc11bc4` — the address *is* the map object —
and looks the event id up through `0x00491F20` before calling any handler. An event with no
entry would be raised into nothing, which would explain the empty container with no debugger
at all.

The lookup's own arithmetic gives the shape: buckets at map`+0x10`, bucket count `+0x18`,
mask `+0x1c`, **12-byte entries** (`lea ecx,[edi+edi*2]; lea edx,[eax+ecx*4]`) whose `+8` is a
state word. Read live, the header agreed exactly: `buckets=0x1D1A6A38, n=512, mask=0x1FF`.

**And the answer it produced was dramatic and false.** It reported **NO SUBSCRIBER** for
`0x1000011E`, `0x10000114` *and* `0x100001A4`.

### 28.1 Why that is refuted, from evidence already in hand

`0x100001A4` is **known live**: the party-window button raises it, and the client asserts
**inside its handler** — that is the whole `GmView.cpp(5890)` crash this arc has been chasing.
An event whose handler demonstrably runs cannot be unsubscribed. So the reader was broken,
not the client surprising.

Dumping the bucket array settled it: **512 of 512 slots non-empty, and no event-id-shaped
value at ANY of the three offsets.** The map does not hold raw ids in its buckets — the
lookup hashes through `0x004920B0` first, so the keys are hashed or held indirectly and a
plain walk cannot find them without replicating that hash.

### 28.2 The control is now the tool's gate

`commanderpeek.py --events` no longer answers unless it finds `0x100001A4` first. If the
control is absent the reader declares itself broken and gives **no** subscriber verdict.
Both branches verified offline against a synthetic map (absent → refuses; present → answers,
`0x1000011E`=1, `0x10000114`=0).

This is the house rule doing its job in the direction that matters: *"a fixture that silently
resolves to the wrong thing turns every assertion behind it into a no-op."* Without the
control, "the commander event has no subscriber" would have been a clean, memorable,
completely wrong finding — and it fits the arc's story so neatly that it would probably have
survived review.

### 28.3 What still stands, and what is now off the table

- **§27's container measurement stands.** It is a separate, simple header read
  (`ctx+0x20`: `cap=7 count=0`, seven zero slots) and it is *consistent* with the assert
  rather than in tension with it.
- **The subscriber question is unanswered**, and cheaply answering it is off the table: it
  needs `0x004920B0` replicated, which is a second thing to get wrong, or a trace — which is
  where §26.4 already pointed.

**Loose end, named rather than left implicit:** the control gate is verified offline but has
no committed test, and a new test file needs its `TESTS.md` entry in the same commit
(`test_srclint` §7 enforces both directions). That is the next small piece of work here.

## 29. `heroes_table.py` — the extraction §2.1 ruled permitted, built

Outstanding since §2.1 ruled it inside the provenance gate's MEASUREMENT branch. Built as a
thin emitter over `consttable`'s structural locator rather than a second copy of the location
logic, so there is one place that can be wrong about where the table is.

**It carries no address.** §2's contested reading was lost to `s_titleClientData` sitting six
instructions from `s_heroClientData`, so the module locates by the `ConstHero.cpp` anchor and
then **refuses** any geometry that is not 40 × 24 — naming the trap in the refusal.

Run against the pin:

```
s_heroClientData: 40 x 24 B at file 0x634E08, anchor 0x6351C8 (ConstHero.cpp)
  closure: base + 40*24 == 0x6351C8        <- ends exactly where its anchor begins
  index column agrees with the row number on every row
```

That closure is the check the artifact could refute and did not: an off-by-one-row base or
stride does not land on the anchor byte.

**Ids only, and that is the gate rather than a style choice.** The name, epithet and biography
ship as **string ids**; the client resolves them from the owner's own archive at render time —
the same "commit the id, resolve at run time" pattern `mapbuild.py` proves and `0x01BF` proves
on the wire (§10.2). `--resolve` takes explicit rows for analysis and **refuses** a whole
column, because that is the bulk expression the gate refuses.

`vault/content/heroes.toml` written (373 lines, gitignored — the vault is where bulk
extraction goes). **All 40 rows pass `content.py`'s real `_check_provenance`**, and stripping
`extractor` from one makes it refuse, so the 40/40 is a result rather than a tautology.

`test_heroes_table.py` (floor 10) pins all of it, including the title-table sabotage with a
positive control after it. Catalogued in `TESTS.md` in the same commit.

## 30. The hero row's label MIXES sources, and `0x0074`'s name is inert

Two things here, one free from data already collected and one from a run.

### 30.1 The free observation, and it sharpens §19

The henchman row reads `Mo1 Hatcher [Collector]`, and §10.2 proved all three parts come from
the **agent** — the wire's own name was ignored.

The hero row reads `Mo1 Goren`. But **the hero's body IS a hatcher** (`--hero-body-npc`
defaults to it, and the `0x0056` says so). So the hero row's label is **assembled from two
places**:

| part | henchman | hero |
|---|---|---|
| profession (`Mo`) | agent | **agent** |
| level (`1`) | agent | **agent** |
| name | agent | **`s_heroClientData`, via the hero id** |

That was visible in screenshots from §18 onward and went unstated. It is the concrete form of
§19's "identity arrives on the data-cache family": a hero's *identity* is the table's, while
its *displayed profession and level* are still the agent's — which is why a Monk-bodied
"Goren" renders without complaint even though the real Goren is a Warrior.

### 30.2 `0x0074`'s name field is inert for the roster — the last encstring case

`0x0074` carries a `string16(32)`, and **every run in this arc had sent it empty** — the one
encstring case the family never tested. (`0x01BF`'s was tested from §10 onward and is what
made the henchman row render a real name, so the standing "retry under `--encstring`" item was
already superseded there.)

Sent with a real EncString — the worm's, deliberately different from both the body and the
hero id — the message goes out at 71 bytes with `4 name ids`, and the row still reads
**`Mo1 Goren`**.

So `0x0074`'s name field **does not override the `s_heroClientData` lookup** for the roster
label. Whether it feeds some other surface (the hero panel, a tooltip) is untested and now
has a flag to test it with; for the roster it is inert.

That closes the arc's "retry under `--encstring`" item: both name-bearing messages in this
family have now carried a real one, and the outcomes are opposite — `0x01BF`'s rides to the
agent-fed label and is ignored (§10.2), `0x0074`'s rides to a table-fed label and is ignored
too. In neither case does a name on the wire reach the party roster.

## 31. `msg+0x14` and `aiMode` — inert, with one of them uninformative

Both were named leftovers: `0x01C2`'s second trailing `u8` (stored to entry+0x14) had never
been varied, and `--hero-ai-mode` was wired but untested. Run together, with the confound
stated up front — if anything had changed I would have had to split them, and nothing did.

Wire: `PARTY_HERO_ADD(party 1, wordA 1, wordB 200, 2, 200)` and
`HERO_ACTIVATE(hero 2, agent 200, inventory 0, aiMode 2)`. The row is **byte-identical**:
`Mo1 Goren`, slot 1 bound, flag green.

- **`msg+0x14` is inert on every observable**, exactly as its sibling `msg+0x10` (§19). Both
  trailing bytes of `0x01C2` now have a measured negative rather than an absent assert.
- **`aiMode` is inert too — and that result is UNINFORMATIVE**, which matters more than the
  observation. Our server has no follow AI and no hero combat behaviour, so there is nothing
  for a Fight/Guard/Avoid-Combat stance to act on. What the run shows is that the stance does
  not change the ROSTER or the compass; it says nothing about whether the client acts on it,
  and it must not be read as "stance does nothing". `CHAR_AI_MODES = 3` stays CORROBORATED
  from the binary and the wiki (§3.2) and untested behaviourally.

## 32. Where this arc stops

The research is at its wall, and the remaining work is of three kinds — none of it more
reading.

**~~Needs native tooling.~~ SPENT, and it answered — see §33.** This section read: *"What is
left is a single question — does `0x008590CA` execute — and it needs a breakpoint or code
cave."* It was built (`commandertrap.py`, hardware breakpoints, nothing written into the
client) and the question is answered: **the raise executes once the party-cache gate opens,
and the handler never runs.** The event is raised into nothing. `0x00524C40` never executes
either, which confirms §27's `count=0` from a second, independent instrument.

The wall has therefore **moved rather than fallen flat**: it is no longer "does the event
fire" but **"what registers a subscriber for `0x1000011E`, and why is it not registered
here"**. And the practical answer this arc needed is settled — no wire field binds a
commander, so the hero is complete for everything the server governs.

**Needs another arc first.** `0x01BF`'s trailing bytes and its wire name (§10.2's measured
negatives) have one untested candidate left, the **outpost hiring UI** — and the party window
does not open in an outpost until RESKIN §18.1's explorable gate is solved. That is not this
arc's to do.

**Ordinary server building, not research.** Follow AI: the movement messages exist and the
hero stands still because nothing drives it. Unbuilt work with no unknown in it.

**What this arc delivered:** a henchman and a hero authored end to end from our own server,
both rendering named roster rows on the pinned build; the wire shapes of four messages read
from the client's own tables, three of which correct or refute their published upstream
descriptions; `s_heroClientData` located, closed and extracted under the provenance gate; and
the attribute pair (`0x0037`/`0x003A`) plus `0x00B7` identified as what a hero needs — all of
which were already in the tree, addressed to the wrong agent.

## 33. THE WALL COMES DOWN: the commander event is raised into nothing

§26.4, §27.2 and §32 all stop at the same sentence — *what would separate the remaining
possibilities is runtime observation, and that is a native-tooling job.* Built it. The answer
is **not** the one the arc had been circling, and it moves the question rather than closing it
where everyone expected.

### 33.1 The instrument, and what it deliberately is not

`toolkit/clientscan/commandertrap.py`: a debugger in pure `ctypes`. Execute breakpoints live
in **DR0..DR3**, which are per-thread processor state, so **nothing is written into the
client** — no `int3` patched over an instruction, no code cave, no injected DLL, no thread
created in the target. `CLAUDE.md` carve-out 3 permits a compiler and this did not need one,
which is the cheap end of that permission. It matters beyond tidiness: an `int3` patch mutates
the very bytes every address in this file was measured against.

Each site's **instruction bytes are re-verified against the RUNNING process** before anything
arms. The pin is 38797, these addresses are 38833, and §24 already read one build's address in
the other's binary once in this arc. A hardware breakpoint on the wrong build does not error —
it arms on whatever is mapped there and reports it as the chain. Live, the client came up at
base `0x00610000`, slide `0x210000`, and all sites matched.

### 33.2 Three arms

| arm | `worker` | `raise` | `case93` | `filter` | | `bulkraise` | `bulk` | `create` |
|---|---|---|---|---|---|---|---|---|
| default (party cache **hit**) | 1 | **0** | 0 | 0 | | — | — | — |
| `--hero-bust-cache` (cache **miss**) | 1 | **1** | **0** | 0 | | — | — | — |
| bulk path | 1 | — | — | — | | **1** | **0** | **0** |

Every arm: `arm failures / resume failures 0 / 0`, one swallowed `int3` (the attach break-in,
none of the client's), zero foreign single-steps.

`worker` is the **control** and it fired in all three, so `0x01C2` demonstrably reached
`0x00859010` and a silent trap cannot be confused with a real negative — which is the whole
shape of §28's failure. All four slots are written in one `SetThreadContext` per thread, so
the silent sites were armed **on the very thread the control fired on**; "armed but blind" is
not available as an explanation.

### 33.3 The stack and the entry, from the frozen client

At `worker` (`push ebp`, args still at `[esp+4..]`):

```
party_id 1   msg+8 owner 1   msg+0xc agent 200   msg+0x10 heroId 2   msg+0x14 0
```

and at `raise`, dereferencing `ecx`:

```
entry+0 agent 200   entry+4 owner 1   entry+8 heroId 2   entry+0xc/0x10/0x14 0
```

**§25.1's decode of the push order is confirmed against the live stack**, and §26.1's claim
that `ecx` still holds the entry pointer at `0x008590CA` is confirmed by that row decoding
sensibly at all. `esi = 0` there, so the event payload is `{0, entryPtr}`.

### 33.4 What it settles, and it is three separate things

**1. §26.2's cache gate is real, and now OBSERVED rather than read.** The default rig takes
the fast path at `0x00859027`, so `edi == [ebx+0x4c]` at `0x008590AF` and `je 0x8590e2` skips
the raise: `raise = 0`. Bust the cache and the same site fires: `raise = 1`. The gate does
exactly what the disassembly said. This was **predicted in writing before the runs**.

**2. The event is raised INTO NOTHING.** In the bust-cache arm `0x008590CA` executes,
`0x00633D70` is called with `0x1000011E`, and `0x004E5DE1` **never runs**. The static routing
makes that mean what it looks like — resolved out of the image's own byte map and jump table:

```
0x1000011E  case  93 -> 0x004E5DE1      and it is the ONLY event routing to case 93
0x10000114  case  90 -> 0x004E5D20      the bulk activeHeroes scan
0x100001A4  case 125 -> 0x004E38DA      GmView:5890 -- the click that crashes
```

One event, one case, one target. So there is no "it dispatched to a different case" escape:
the switch was simply never entered with `0x1000011E`.

**3. Nothing ever creates a commander, confirmed by a second, independent instrument.**
`0x00524C40` (get-or-create, `GmHeroCommander:81`) **never executes**. §27 reached the same
conclusion by reading the container header out of live memory (`cap=7 count=0`); this reaches
it by tracing the code that would have filled it. Two unrelated methods, same answer — which
is worth more than either alone, because §27's reading depended on the container offset being
right and this one does not.

### 33.5 The corrected shape of the problem

§17.4 guessed the commander container is "populated by a client-side UI event we do not
trigger". The measured version is **different and stronger**:

> The event **is** raised. Nothing consumes it. What is missing is a **SUBSCRIPTION**, not a
> trigger.

That distinction is the whole result. Every fix this arc attempted — `inventoryId` (§16),
`msg+0x10` (§19), the cache gate (§26) — was aimed at *getting the client to raise the event*.
Three of them were refuted by experiment and the fourth (§26) turns out to have succeeded at
its stated goal: the bust-cache arm **does** make the raise fire, and the panel still asserts.
§26.3 scored that arm "the cache-hit gate is real but is NOT why the commander fails to bind",
and that verdict was exactly right — this names the mechanism behind it.

**So `0x01C2` cannot bind a commander, and no wire field will change that.** The hero as
authored — roster row, name, level, profession, attributes, skill bar, lit commander flag — is
complete for everything the wire governs, which is §17.4's conclusion arrived at by
measurement instead of by exhaustion.

### 33.6 The bulk path is dead the same way

`0x00858850`, the function §25.2 identified as raising `0x10000114`, **does run** in our
session — and case 90 (`0x004E5D20`) never does. So both commander events fail in the same
place: raised, unconsumed.

**Stated carefully, because it is easy to overclaim here:** the trap measured that
`0x00858850` *executes*. It did not measure its caller, and it did not measure whether that
particular execution reached its raise. §25.2's "all eight callers are UI" is neither
confirmed nor refuted by this — the client runs UI and message handling on one thread
(everything above fired on the same tid), so the thread identity says nothing either way.

### 33.7 What is left, and it is one bounded question

Not "does the event fire" — that is answered. **What registers a subscriber for `0x1000011E`
and `0x10000114`, and why is it not registered in our session?** The commander module is
demonstrably alive (§27: context non-null, container allocated at `cap=7`), so this is not
an uninitialised UI. That is a real question with a real instrument now pointed at it, and it
is the honest successor to §32's wall. **§34 answers the first half and re-shapes the
second.**

### 33.8 Four defects in the instrument, three of them caught by its own control

The reusable part, and it is not about heroes.

- **A 64-bit debugger does not receive `0x80000004` from a 32-bit target.** It receives
  `STATUS_WX86_SINGLE_STEP` (`0x4000001E`) and `STATUS_WX86_BREAKPOINT` (`0x4000001F`). The
  first version passed every hit back to the client as somebody else's exception and reported
  **no hits**. Against the client that would have published "the commander event is never
  raised" as a measurement — the right headline, reached by a broken instrument, which is
  §28's failure exactly.
- **`EFLAGS.RF` does not survive `ContinueDebugEvent`.** A hardware execute breakpoint is a
  *fault*, delivered before the instruction runs; the processor sets RF in the saved flags so
  the resume does not re-trap, and that does not make it back through the debug loop. The
  first live run trapped one instruction **32 times in 4ms**, identical `ESP` each time, until
  the runaway guard disarmed the slot — and reported it as "this site executed 32 times". The
  debugger has to set RF itself.
- **State captured after the read handle closed.** Decoding happened at report time, by which
  point `main`'s `finally` had closed the handle and the client had exited, so every captured
  field read `None`. State belongs to the instant the thread is frozen; anything later is
  reading a different process. This is why run 2 was discarded rather than published — its
  `raise=0` was probably right, and a run whose capture returned nothing has no business
  supplying a headline.
- **The module list is not ready the instant a process exists.** `--wait` grabs the pid
  microseconds after `CreateProcess` on purpose, and the toolhelp snapshot fails with
  `ERROR_PARTIAL_COPY`. Retried, with a timeout so it cannot become a silent hang.

**And the control had its own blind spot, which is the lesson worth keeping.** §3 of the test
originally stopped at the first hit. That proves a breakpoint **fires** and says nothing about
whether the target **resumes** — two separate claims, one of them untested, and the untested
one was the broken one. It now runs to process exit and requires *exactly one* hit on an entry
point that executes once. A control that only checks the half you thought of is a control with
a hole in it.

## 34. NO SUBSCRIBER, measured — and the control nearly let a second §28 through

§33 showed the commander event is raised and its handler never runs, and inferred "raised
into nothing". §28 had said the subscriber question itself was off the table: the map's keys
hash through `0x004920B0`, so a bucket walk cannot find them, and answering it "needs that
replicated, which is a second thing to get wrong, or a trace."

**It needed neither.** The raise is four instructions of ordinary code:

```
0064CA42  call 0x491f20      ; the map lookup
0064CA47  test eax, eax      ; <- EAX IS THE SUBSCRIBER LIST for the event in [ebp+8]
0064CA49  je   0x64ca58      ; NULL -> return, having called nothing
0064CA53  call 0x64c7d0      ; else dispatch to the list
```

So let the client hash its own key and read the answer out of `eax` one instruction later.
No replication, nothing to get wrong.

### 34.1 The result

```
worker  party 1, owner 1, agent 200, hero 2
raise   entry+0 agent 200   entry+4 owner 1   entry+8 heroId 2
lookup  event(ebp+8)      0x1000011E
        subscribers(eax)  0x00000000
        NO SUBSCRIBER -- takes `je 0x64ca58`, the raise returns having called nothing
```

Three sites, one thread, in order, 3 ms apart, `arm/resume failures 0/0`. **`0x1000011E` has
no subscriber at the moment it is raised.** The captured `event(ebp+8)` is the point of that
capture and not decoration: it proves the hit was *ours* rather than some other event that
interleaved.

`0x0064CA47` is inside the raise **every** UI event in the client passes through, so arming
it for a session would trap thousands of times. It is armed only when our own raise fires and
taken down after one hit (`arm_after`/`oneshot`), so it was live for ~3 ms.

### 34.2 THE CONTROL FAILED FIRST, and this is the part worth keeping

A reader whose only output is NO SUBSCRIBER is §28 wearing a different hat. So: arm the same
address with no trigger and census what the client raises on its own.

**The first control run said NO SUBSCRIBER to everything** — every sampled lookup, including
unrelated events `0x10000141` and `0x0000004B`. Had that been the last word, §34.1 was dead.

It was not the reader; it was the **sample**. All 32 hits landed inside one 4 ms burst, ~30 of
them the same event, because `max_hits` capped the slot instantly. A hot site's default
ceiling is not a sample of anything. Re-run with the ceiling at 4000:

```
CENSUS: 54 distinct events, 4000 hits
  23 ALWAYS subscribed        e.g. 0x00000045 -> 0x1AEFBEE8, 0x10000114 -> 0x1C4D0AA0
  23 never subscribed
   8 BOTH -- their subscriber state CHANGED during the session
```

**The reader is bidirectional, so §34.1 stands.** And a near-miss is recorded rather than
quietly fixed: a control that samples badly does not fail loudly, it agrees with whatever you
were about to conclude.

### 34.3 Two things the census gives away for free

**`0x10000114` IS subscribed** (`-> 0x1C4D0AA0`), so §28's reader was wrong about that one
too — exactly as its own control implied. That leaves a real tension with §33.6, which
measured `bulkraise=1, bulk=0`: the bulk event has a live subscriber, yet case 90
(`0x004E5D20`) never executed. Either `0x00858850` ran without reaching its raise in that
session, or the subscriber for `0x10000114` is **not** the switch that holds case 90. Two
different sessions, so they are not strictly comparable. **UNRESOLVED, and named rather than
smoothed over.**

**Subscriptions change during a session.** Eight events appear with a null subscriber at one
moment and a real one at another — `0x00000054`, `0x10000001`, `0x10000007`, `0x1000001D`,
`0x10000030`, `0x1000005E`, `0x10000142`, `0x10000176`. The map is populated as the client's
UI modules come up, not once at startup.

### 34.4 The successor question, now sharp enough to test

§33.7 asked *why* there is no subscriber and could only gesture. §34.3 turns it into a
hypothesis with a mechanism:

> **TIMING.** Our `0x01C2` rides inside the instance load. If the commander UI subscribes
> later than that, the event is raised into an empty slot and the same wire bytes would work
> if they arrived after the subscription.

**UNVERIFIED**, and stated with what would refute it: census `0x1000011E` across a whole
session and find it *never* subscribed at any moment — that kills timing and puts the fault
back on the subscription itself. The current census cannot answer it, because the lookup only
happens when the event is raised and our rig raises it exactly once. What it needs is either
the registration site trapped, or a hero-add deliberately sent long after
`INSTANCE_LOAD_FINISH` — and no flag sends one that late today (`--hero-bust-cache` already
moves it after the party build, which is as late as the current rig goes).

**None of this changes §33.5's practical conclusion**: at the moment our server can send it,
`0x01C2` cannot bind a commander, and the authored hero is complete for everything the wire
governs.

## 35. The timing hypothesis: CORROBORATED, NOT REPRODUCIBLE -- and a retraction

34.4 proposed TIMING as the reason the commander event is raised into nothing, with a
refutation stated. `--hero-late N` was built for it (`hero_late_tick`, polled from the world
tick): hold the whole party/roster sequence until N seconds after `INSTANCE_LOAD_FINISH`
instead of sending it inside the load. The precedent was already in the same handler --
`UI_OVERLAY_FLAGS` is sent late because "a byte that arrives before the UI exists sets a bit
nothing is left to read."

### 35.1 The A/B, and it is a real difference

| when `0x01C2` is sent | `raise` | `subscribers(eax)` | `case93` |
|---|---|---|---|
| inside the instance load (33, 34) | 1 | **`0x00000000`** | **0** |
| 20 s after `INSTANCE_LOAD_FINISH` | 1 | **`0x26151EA0`** | **1** |

Same rig otherwise, and the late run's `case93` capture cross-checks itself: `payload+4` =
`0x2736DD90` = the `entry(ecx)` captured at the raise in the same run, which is 26.1's
`{0, entryPtr}` payload confirmed from a third direction.

**So the commander UI does subscribe, and later than our hero-add had been arriving.** That
is a genuine measurement and the subscriber reading behind it is control-verified (34.2).

### 35.2 SUPERSEDED BY 35.5 -- it reproduces 4 of 5. Read on before using this section.

*The three subsections below are kept exactly as written at n=2, because the correction they
carry is about my own labelling and deleting it would hide it. The measurement they report is
real: one late run did stall. What changed is the DENOMINATOR.*

### 35.2 IT DOES NOT REPRODUCE, and that governs (at n=2)

A second run on the **identical** rig -- `--hero-late 20 --hero-bust-cache`, same map, same
hero -- reached the worker and stopped:

```
chain: worker=1 -> filter=0 -> create=0 -> notfound=0
```

and a third late session, sampled every 8 s for 14 samples, held the commander container at
`cap=7 count=0` throughout. **No commander is created in any run, early or late.**

**Correction on the record: this was called CONFIRMED mid-session and it is not.** At n=2 the
late path is **CORROBORATED and NOT REPRODUCIBLE**. One run reached case 93; one did not.

### 35.3 The confound, named

`--hero-late` changes **two** things, not one. It moves the send later, *and* it moves it to a
moment when the party-manager cache state is far less controlled. The raise is gated on a
cache MISS (26.2), and `--hero-bust-cache` opens a build on party 2 immediately before -- but
20 s into a live instance the client has had time to re-cache party 1 in between, which would
make the hero-add a HIT again and skip the raise entirely.

That predicts run 10's shape exactly: **`raise = 0`**, therefore no case 93, no filter, no
create. It was not trapped in that run, so it is a hypothesis and not a reading -- but it is
the same confound shape as 10.2's body arm and 26.3's arm A, both of which this arc has
already paid for once.

### 35.4 What would settle it

Trap `worker, raise, lookup, case93` on the late rig across several runs. If `raise = 0`
whenever the chain stalls, the confound is the cache and 35.1's subscriber reading stands
intact -- and what the rig then needs is a **deterministic** cache miss at a late moment,
which `--hero-bust-cache` does not guarantee once the instance is live.

**Unchanged either way:** no commander is created in any run measured, so 33.5's practical
conclusion holds -- at the moment our server can reliably send it, `0x01C2` does not bind a
commander, and the authored hero is complete for everything the wire governs.

## 35.5 The series 35.4 asked for: it reproduces 4 of 5

Three more late runs with `worker,raise,lookup,case93` armed, exactly the shape 35.4
specified. **All three ran the full chain**, each with its own live subscriber pointer:

| run | worker | raise | lookup | case93 | `subscribers(eax)` |
|---|---|---|---|---|---|
| 9 | 1 | 1 | 1 | 1 | `0x26151EA0` |
| series 1 | 1 | 1 | 1 | 1 | `0x272BA958` |
| series 2 | 1 | 1 | 1 | 1 | `0x25EE9D78` |
| series 3 | 1 | 1 | 1 | 1 | `0x25BF7AA8` |
| 10 | 1 | -- | -- | **0** | *(not armed)* |

**So the late rig reaches case 93 in 4 of 5 runs**, and 35.2's "NOT REPRODUCIBLE" was drawn
from a single stall. The honest label is now **REPRODUCIBLE WITH ONE OUTLIER**: sending the
roster sequence after `INSTANCE_LOAD_FINISH` reliably finds a subscriber for `0x1000011E`
where sending it inside the load reliably does not.

**Run 10 stays unattributed and is not swept up.** It did not arm `raise` or `lookup`, so
whether it stalled at the cache gate (35.3's confound) or at an absent subscriber cannot be
recovered from it. One in five is a real rate and it is recorded as one.

**The distinct subscriber pointer in every run is worth noting**: four different addresses, so
this is a list allocated per session rather than a static that might have been misread.

### 35.6 THE LATE RIG MAKES THE CLIENT ASSERT -- 4 of 4, and it confounds everything above

Reading the session logs rather than only the trap reports:

```
ERROR DIALOG captured
>>> Assertion: SkillListContext::SKILL_LIST_USERS != skillListUser
```

**Every late run produced it -- 4 of 4, identical string.** `--hero-late` does not merely move
the roster sequence, it puts the client into an assert it never hits on the inline rig. The
likely cause is the hero's skill bar (`0x00DA`) arriving 20 s after the load, but that is not
measured and is a guess.

**This is a confound over 35.1 and 35.5, and it is mine.** Every late measurement in this
section was taken from a client that asserts during the run. "The subscriber appears later"
may be a fact about normal UI initialisation, or it may be a fact about a client in a degraded
state -- these runs cannot tell those apart. The subscriber pointer being **different in every
run** (four distinct addresses) is mild evidence for a genuine per-session list rather than an
artifact, but it is not decisive.

**Downgraded:** 35.1 and 35.5 are **CONTESTED**, not CORROBORATED. What survives unconditionally
is the *contrast* -- inline runs read `subscribers = 0` and late runs read non-zero -- because
that difference is large, repeated, and control-verified (34.2). What does NOT survive is any
claim about *why*, because the rig changed two things and then broke a third.

**What it would take:** find and fix the assert first. A rig that asserts is not a rig.

**35.6a -- the inline half of that claim, VERIFIED (it had not been).** 35.6 asserted the
dialog appears "in every late run and in no inline run" while only ever having checked the
late half. Checked properly against `vault/captures/harness/`:

| rig | runs | asserted |
|---|---|---|
| inline (`0x01C2` inside the load) | 3 | **0** |
| late (`--hero-late 20`) | 9 | **9** |

So the claim holds, and it now rests on both halves instead of one. Writing a two-sided
statement having tested one side is the same defect as 28's reader, in prose rather than code.

**35.6b -- the obvious fix was tried and FAILED.** `0x0074` was moved back to the inline
schedule, on the reasoning that deferring it put `0x0072` HeroActivate, the attribute pair and
the skill bar 20 s *before* the `charHeroData` record they need -- inverting the order 13/14
established. The chain still ran (`worker/raise/lookup/case93` all 1) and **the client still
asserted, 2 of 2.** So that inversion was real but is not the cause.

**35.6c -- THE WHOLE PIPELINE WAS DEFERRED AS ONE UNIT, AND IT STILL ASSERTS.** The third and
last ordering was tried: `hsend()` now routes the entire hero pipeline through a single
deferral point -- `0x0074`, the party build with `0x01C2`, the world body, the attribute trio
(`0x00B7`/`0x0037`/`0x003A`), the skill bar `0x00DA` and `0x0072` HeroActivate -- preserving
their relative order exactly and changing only the absolute time. **The chain ran
(`worker/raise/lookup/case93` all 1) and the client asserted anyway.**

Three orderings, three asserts:

| rig | relative order | assert |
|---|---|---|
| `0x0074` deferred, rest inline | inverted | yes |
| `0x0074` inline, rest inline | partly split | yes |
| **whole pipeline deferred** | **identical to inline** | **yes** |

**So the assert is not about relative ordering at all -- it is about LATENESS ITSELF.** The
client will not accept a party roster and hero delivered after `INSTANCE_LOAD_FINISH`,
however internally well-ordered. The regression control holds throughout: the same code on the
inline schedule is clean (`RUN VERDICT: PASS`, send order unchanged), so `hsend` did not break
the default path.

**What this closes.** "Send it later" is **not a viable authoring route**, and the timing
experiment cannot be run cleanly by this method -- any late delivery asserts, so every late
measurement is taken from a client that is failing. §35.1/§35.5 stay **CONTESTED** and there is
now no cheap way to lift that. The subscriber genuinely is present later (measured four times,
control-verified), but we cannot exploit it, which leaves §33.5's practical conclusion exactly
where it was and better understood: **the commander panel is not reachable from the server.**

## 36. The subscribe site, built -- and a BYTE ANCHOR MUST NOT CONTAIN A RELOCATED ADDRESS

35.6c's successor route is the map INSERT rather than the lookup: `0x0064CDA4` looks an event
up and, when absent, allocates a list and stores the id (`mov [ebx],esi`). At that point `esi`
is the event id and `[ebp+4]` is the caller's return address -- so a census names **who
registers what**, which is what 34 and 35 could not reach by watching the raise.

### 36.1 The guard refused, and it was right for the wrong reason

Armed at `0x0064CDA4` the verification REFUSED:

```
expected b9c41bc100      (mov ecx, 0x00C11BC4)
got      b9c41be200      (mov ecx, 0x00E21BC4)
```

`0xE21BC4 - 0xC11BC4 = 0x210000`, **exactly the run's ASLR slide.** That instruction embeds an
absolute DATA address, the loader relocates it, and the bytes in memory therefore differ from
the bytes in the file *by design*. The site was correct and the guard rejected it.

**The rule, and it is general:** a byte anchor must contain no relocated absolute address.
The four sites this arc has been using survived only by luck of encoding -- two function
prologues, a `push imm32` whose immediate is a CONSTANT (not relocated), and a `call rel32`,
which is PC-relative and identical in file and memory. Re-anchored five bytes on to
`0x0064CDA9`, the `call rel32` into the lookup, where `esi` and `[ebp+4]` still hold the same
values. It verifies and arms.

*(This is the second time the byte guard has produced a REFUSAL rather than a wrong number,
and both times the refusal was the useful output: once for a genuine cross-build hazard, once
for this. A guard that only ever says yes is 28's reader again.)*

### 36.2 The instrument works; the run that used it did not

Armed, it captures exactly what was wanted -- `event(esi)` with `caller(retaddr)`, e.g.
`0x10000013` registered from `0x00843C07`.

**But the census is worthless and the reason is an orchestration error, not the tool.** The
trap attached to pid 24896 -- the PREVIOUS run's client, still alive, already fully loaded --
so it sampled 3 late subscriptions instead of the startup burst where the interesting
registrations happen. The earlier series scripts serialised on `while tasklist | grep Gw.exe`
for exactly this reason and this run was launched without it. **`0x1000011E` is absent from
those 3, which means nothing**: a 3-event sample taken after the UI is built cannot show a
registration that happens during construction.

### 36.3 THE CLEAN CENSUS: `0x1000011E` IS SUBSCRIBED, on the INLINE rig, twice

Re-run properly serialised (wait for the field to clear, then start the client), so the
startup burst is captured instead of a post-construction tail: **277 distinct
(event, caller) pairs**, and among them

```
x2   event(esi)=0x1000011E   caller(retaddr)=0x00843C07
```

**On the ordinary inline rig -- the one that does NOT assert.** So the commander event does
acquire a subscriber in a perfectly normal session; §34 measured `subscribers = 0` only
because the raise happens *during the instance load*, before that registration.

**This lifts §35's CONTESTED status without touching the broken rig.** The timing story no
longer rests on late runs that assert -- it is now visible on the clean inline rig from a
completely different instrument: the registration exists, and our `0x01C2` simply precedes it.
§35.1/§35.5's *contrast* was right and its late-rig *mechanism* was never needed.

**A repeat of 36.1's own lesson, one section later.** The captured `0x00843C07` is a RUNTIME
address; resolving it against the image gave misaligned garbage until the slide came off:
`0x00843C07 - 0x210000 = 0x00633C07`, which sits beside the raise wrapper at `0x00633D70`.
Un-sliding a captured pointer is the mirror of not baking a relocated address into an anchor,
and both cost a wrong reading before being noticed.

The caller resolves to a thin subscribe wrapper:

```
00633BF0  push eax
00633BF1  call 0x64ca60          ; resolve the target object
00633BF9  lea  ecx,[eax+0xa8]    ; its own map, NOT the global 0xC11BC4
00633BFF  push [ebp+0xc]         ; the event id, from the wrapper's arg
00633C02  call 0x64cd60          ; subscribe
```

so every registration in the census funnels through one site and the wrapper's **callers** are
what name the UI construction. That is the next read, and it is static: enumerate callers of
`0x00633BF0` and find which passes `0x1000011E`.

### 36.4 EIGHT subscribers and ONE raiser, enumerated from the image

The wrapper's callers, found by scanning `.text` for the immediate itself
(`68 1E 01 00 10`, `push 0x1000011E`) and decoding the following `call rel32`:

```
0x004ED055 -> 0x00633BD0      0x0056ABC9 -> 0x00633BD0
0x00539380 -> 0x00633BD0      0x0056DEB6 -> 0x00633BD0
0x00562D94 -> 0x00633BD0      0x005749BB -> 0x00633BD0
0x00567AB8 -> 0x00633BD0      0x008BB6B0 -> 0x00633BD0
0x008590CA -> 0x00633D70   <- OURS: the RAISE, 0x01C2's worker
```

**Eight SUBSCRIBE sites and exactly one RAISE site, and the one raiser is the instruction this
whole arc has been chasing since 26.4.** The asymmetry is the answer to "who registers it":
eight different UI constructions each subscribe to the commander event, and the party
hero-add is the only thing in the image that raises it.

**And the census counted TWO registrations in our session, not eight** -- so six of those
eight sites belong to UI that our session never constructs. That is now a bounded, purely
static question: name the eight, and the two that DO run tell us what must exist before a
hero-add can bind a commander. No further client runs are needed to enumerate them.

### 36.5 The eight subscribers, NAMED

Each site attributed by the asserts in its enclosing function (`asserts.py --at <va> --span`):

| site | module | what it is |
|---|---|---|
| `0x00539380` | **GmPosseRoster** | the party roster window -- the hero row's own UI |
| `0x008BB6B0` | **Compass** | the compass, which draws the hero flag widget |
| `0x005749BB` | **PtPlayer** / PtSearchParty | party player rows (`PtPlayer:332` is 23.2's 7-hero cap) |
| `0x004ED055` | **GmView** | the main game view |
| `0x00562D94` | **PtSearch** | party search |
| `0x00567AB8` | CtlInstance / **PtSearchDescription** | party search description |
| `0x0056ABC9` | **PtInvite** / CtlInstance | party invite |
| `0x0056DEB6` | CtlInstance / **PtButtons** | party window buttons |

**The split is exactly the one this arc already knows.** The two UIs our session demonstrably
builds are the roster (23: the hero row renders) and the compass (10.2: the flag widget
appears, unpredicted at the time) -- and both subscribe here. The six that do not run are
**party search, invite, description, buttons** -- the outpost party-formation UI, which is the
same surface 32 recorded as blocked behind RESKIN 18.1's explorable gate. So the commander
event is registered by the party-formation UI as a family, and an explorable-map session
constructs only the two members that draw the party once it exists.

**RECONSTRUCTION, and flagged because the census cannot confirm it -- see 36.6.**

### 36.6 A capture defect: `caller(retaddr)` names the WRAPPER, not the subscriber

The census captured `caller(retaddr)` at `0x0064CDA4` from `[ebp+4]`, intending "who
subscribed". Every row came back with the SAME value, `0x00843C07`, which un-slides
(-0x210000) to **`0x00633C07` -- inside the subscribe wrapper `0x00633BD0` itself**. The
trapped function is the wrapper's callee, so `[ebp+4]` is the wrapper's return address and is
constant by construction. It identifies nothing.

**The enumeration in 36.4/36.5 does not depend on it** -- that came from scanning `.text` for
the immediate `push 0x1000011E` and decoding the following `call`, which is independent of the
census. What is NOT established is **which two of the eight ran in our session**: that needs
one frame further up (`[[ebp]+4]`), and 36.5's roster+compass attribution is RECONSTRUCTION
from which UI our session visibly builds, not a measurement.

Third address-arithmetic slip in this arc, all the same shape: 24 read a 38797 address in a
38833 image, 36.1 anchored on relocated bytes, and this un-slid a pointer whose frame was the
wrong one. The lesson is narrower than "be careful with addresses" -- it is that a captured
pointer needs its FRAME justified, not just its base.

### 36.7 MEASURED: the two are GmView and Compass -- and 36.5's guess was HALF WRONG

The frame walk fixed (`[[ebp]+4]`), one clean census, 399 distinct registrations. Exactly two
carry `0x1000011E`, and un-sliding by this run's `0x9A0000`:

```
SUBSCRIBER 0x0125B6BD -> 0x008BB6BD    Compass
SUBSCRIBER 0x00E8D060 -> 0x004ED060    GmView
inner      0x00FD3C07 -> 0x00633C07    constant, as 36.6 predicted
```

**The cross-check is exact in both directions.** The static scan found `push 0x1000011E` at
`0x008BB6B0` with its `call` 8 bytes later, so the return address must be `0x008BB6BD` -- and
that is what the live capture holds. Same for `0x004ED055` +6 -> `0x004ED060`. A static
enumeration and a live frame walk, agreeing to the byte, neither derived from the other.
`inner` stayed constant across all 399, which is the control 36.6 built in: had it varied, the
frame reasoning was wrong and `outer` would have been worthless.

**And it REFUTES 36.5.** That section reconstructed the two live subscribers as
**GmPosseRoster + Compass**, reasoning from which UI our session visibly builds -- the roster
renders the hero row, so surely the roster subscribes. Measured, they are **GmView + Compass**:
the Compass half was right and **the roster half is wrong**. `GmPosseRoster` subscribes at
`0x00539380` and that site does NOT run in our session, even though the roster window is on
screen with a hero row in it.

That is worth more than the correction. The roster **drawing** a hero and the roster
**registering for commander events** are separate things, and only the second is what a
commander binding needs. It also sharpens 33.5: the missing subscription is not "some UI we do
not build" in the abstract -- it is specifically `GmPosseRoster`'s, from a window that is
demonstrably present. Why that window's registration does not run is the next question, and it
is a fresh one.

**Method note, because this is the third time it has paid.** 36.5 was labelled RECONSTRUCTION
rather than measured, and the label is the only reason the refutation is a correction to a
guess instead of a retraction of a finding. The same discipline caught 28's subscriber map and
35's premature CONFIRMED.

### 36.8 Chasing GmPosseRoster's absence: the chain read, the gate REFUTED

36.7 left one question: why does `GmPosseRoster` not subscribe when its window is on screen?
Read statically, the chain is:

- `0x005392A0` is GmPosseRoster's message handler -- a switch on `[esi+4]`, confirmed by its
  own asserts (`sm_instanceCount`, `sm_staticSelectedAgentId`, `GmPosseRoster:115/124/137`).
- Its jump table (base 9, `0x00539794`/`0x0053977C`) routes **message `0x09`** to `0x005392D8`,
  which falls through to the subscribe block -- and that block registers **four** events
  together: `0x10000114` (the bulk scan), **`0x1000011E`**, `0x1000011F`, `0x100001C5`.
  So message 9 is instance-create, and it is the only path to the roster's subscription.
- The handler is installed from exactly three sites (`push 0x539980`): `0x0050145C`
  (**GmDeckBuilder**), `0x00578C0C` (**UiCtlInstance/PvpItemList**, next door to §11's
  `PtHero:156`), and `0x008E3264` (**UiCtlInstance**).
- `0x00578C0C` sits behind a guard: `call 0x00815E90; test eax,eax; je <skip>`. That function
  resolves the root context, takes `ctx[0x2c]` -- the same character context §14 read `+0x6BC`
  from -- and returns 0 when **`[ctx[0x2c]+0x67C]` is zero**. Its only two real writers are at
  `0x005E42CF` and `0x0081B8FC`, the latter in **ChCliBase** (asserts 480-515,
  `playerTeamToken` / `AgentGetTeamToken`).

**Hypothesis: the field is zero on our synthetic character, so the install is skipped.**
Prediction stated before the run: `posseGate` fires with `esi == 0`.

**REFUTED.** Trapped at `0x00815EA0`, where `esi` IS that field: four hits, **non-zero every
time** -- `gate passes, the roster handler installs`. The field is populated on our character.

### 36.9 What that leaves, stated precisely

The measurement kills the hypothesis and does **not** answer the question, and the difference
matters. What it establishes is only that `[ctx[0x2c]+0x67C]` is non-zero. It does **not**
establish that `0x00578BF0` (the guarded install site) ever ran -- `0x00815E90` has other
callers and the trap cannot tell which one produced a given hit without a frame walk, the same
distinction §36.6 already paid for once.

So three possibilities survive, and separating them is the next arc's work, not a quick run:

1. the install site runs, the handler is installed, and **message 9 is never delivered** to it;
2. a **different** one of the three install sites is the roster's real path, and it is gated
   elsewhere;
3. the handler is installed and message 9 delivered, but the subscribe block is reached by a
   route the census would have seen -- which §36.7 rules out, so this is the weakest.

**Standing regardless:** `GmPosseRoster` does not subscribe to `0x1000011E` in our session
(§36.7, measured), the commander event's only live subscribers are GmView and Compass, and
`0x01C2` cannot bind a commander from the server. Four hypotheses have now been refuted on
this question (`inventoryId`, `msg+0x10`, the party-cache gate, and this one), which is the
arc's established pattern: the static reading is sound and the guess about *which* branch is
cold has been wrong every time.

### 36.10 MEASURED: the roster handler never runs at all, and the gate is not why

Both sites armed together for a whole session:

```
posseMsg  0        <- GmPosseRoster's handler, NEVER ENTERED
posseGate 5        <- field ctx[0x2c]+0x67C = 1 every time, non-zero
```

**`GmPosseRoster`'s message handler is never entered once** in 115 seconds, with the party
window open and a hero row rendering in it. Not message 9, not any message. So §36.9's
possibility (1) -- "installed but message 9 never delivered" -- is **REFUTED**: a component
with an installed handler would take *some* message across a whole session, and this takes
none.

And the gate is not the reason. `[ctx[0x2c]+0x67C]` is **1**, so `0x00815E90` returns non-zero
and its `je` is not taken. Which forces the conclusion:

> **`0x00578BF0` -- the guarded install site -- never runs in our session.** Its gate would
> have passed had it been reached. The five `posseGate` hits therefore come from the
> function's *other* callers, exactly as §36.9 warned they might.

That is §36.9's possibility (2), confirmed by elimination, and it moves the blocker **one
level up**: not the gate, not the handler, but whatever constructs the thing at `0x00578BF0`
in the first place. The two remaining install sites are `0x0050145C` (**GmDeckBuilder**, the
PvP build UI) and `0x008E3264` (**UiCtlInstance**) -- neither of which an explorable PvE
session has any reason to build either.

**Which closes the shape of the answer even though it does not name the caller.** Every route
to `GmPosseRoster` runs through UI our session does not construct -- a PvP deck builder, a
PvP item list, a generic control instance -- and the roster window we *do* see on screen is a
different component that draws party rows without ever registering for commander events. That
is the concrete form of §36.7's finding, and it is why no amount of wire traffic will bind a
commander: the subscriber is not merely unregistered, its entire construction path is absent.

**Fifth refuted hypothesis on this question** (`inventoryId`, `msg+0x10`, the party-cache gate,
the `+0x67C` gate, and now "installed but unmessaged"). The static reading has been right every
time; the guess about which branch is cold has been wrong every time. That asymmetry is the
arc's most reusable lesson, and it is why each of these cost one cheap measurement instead of a
redesign.

**Next, and it is one clean run:** the same site, on a client this run started, with the
wait-for-exit guard restored. Then resolve the caller addresses statically -- `codescan
--xrefs` on each -- to name the UI construction that registers `0x1000011E`.

**The remaining route, and it is not more of this:** find what the client itself does between
the load and the subscription -- i.e. trap the map INSERT rather than the lookup, and learn
which UI construction registers `0x1000011E`. That is a different instrument (the registration
site) and a fresh arc's worth of work.

**Superseded, kept for the record -- the reasoning that led to 35.6c:** the hero's **body,
attributes (`0x0037`/`0x003A`), skill bar (`0x00DA`) and `0x0072` HeroActivate are still sent
inline** while the roster binding arrives 20 s later, so now those are too EARLY relative to
`0x01C2` rather than too late. `SkillListContext::SKILL_LIST_USERS != skillListUser` naming a
skill-list *user* fits a skill bar addressed to an agent the party does not yet hold. The
correct rig defers the **whole hero pipeline as one unit**, preserving relative order and
moving only the absolute time -- which is what "change one thing" required from the start and
what this flag did not do.

### 35.7 A site-set asymmetry, recorded and NOT explained

The two trap configurations disagreed systematically:

| sites armed | runs | reached case 93 |
|---|---|---|
| `worker,raise,lookup,case93` | 4 | **4** |
| `worker,filter,create,notfound` | 3 | **0** |

Same rig, same session arguments, same map, same hero -- only the armed addresses differ. The
assert above is constant across BOTH sets, so it is not the discriminator. Three readings fit
and this arc has no evidence to choose between them: run-to-run variance that happened to
land 4-0 then 0-3; an observer effect where trapping `0x008590CA` delays the raise into a
window that works; or something about the later sites being armed. **UNRESOLVED, and it is
recorded because it means the numbers in 35.5 are not yet safe to build on.**

### 35.8 What is STILL not explained, and it is the whole remaining question

Case 93 runs. And **no commander is created** -- the container held `cap=7 count=0` across all
14 samples of a late session. Since `0x00524CC0` reaches the get-or-create on BOTH of its
exits (33's reading, unchanged), the break must sit between case 93's entry and that call:
either the my-id filter at `0x004E5DF2` rejects, or `0x00524CC0` behaves differently from the
static read. That is one run shape -- `worker, filter, create, notfound` on the late rig,
repeated to beat the 1-in-5 stall -- and the filter site captures both operands, so it answers
itself.

## 9. Defects and corrections this arc produced

- **`msgshape.py` printed `string16(0)` for every wide-string field — FIXED `c81d6d1`,
  REGRESSION-CHECKED 2026-08-19.** `Field.__repr__` shows `self.cap`, but the `wstring`
  branch never passed `cap=` to the constructor — only `wire=`. The true capacity was
  recoverable only by back-solving from the wire total, which is why §1.1 said
  `string16(20)` where the tool said `(0)`. The tool now prints the declared capacity
  (`0x01BF` → `string16(20)`, `0x0074` → `string16(32)`), and `test_msgshape.py` §4 pins it
  over all **141** wide-string fields in the image, on all three vaulted builds, with the
  capacity histogram identical across them — the protocol did not move, only the tables did.
  **The fix sat for four days with nothing checking it**, which is the defect this entry
  really records: §9 and `PLAN.md` both went on describing an open bug that was already
  closed, because a fix nobody pinned reads exactly like a fix nobody made. §4's negative
  control constructs a `Field` the old way and asserts it still prints `string16(0)`, so a
  future edit that drops `cap=` reddens 14 checks instead of silently returning.
  **It also unblocked a claim in another arc:** `0x0049`'s three `string16(8)` fields are now
  legible, which moves `studies/quests/FINDINGS.md`'s cap-of-8 row off OpenTyria's annotation
  and onto the client's own descriptor.
- **A 48×12 table at `0xA35B80` is `s_titleClientData`, not `s_heroClientData`** (§2). Two
  adjacent `Const*` accessors; the structural locator closed on the wrong anchor.
- **`0x0074` is not `{hero_id, level, primary, secondary}`** (§1.3) — 20 fields, 127 bytes.
- **`PARTY_HERO_ADD` is not "a `uint8` level"** (§1.2) — three `u16`s and two `u8`s.
- **The 7-hero cap is a 2011-03-03 update gated on party size, not an EotN feature** (§6).
- **`0x01C2` has no dedupe scan**, so the "entry+0 is the primary key" analogy is refuted
  (§1.2).
