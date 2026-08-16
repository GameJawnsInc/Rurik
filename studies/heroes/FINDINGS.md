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
3. **What creates the `charHeroData` record?** The trailing `0x0072` diagnostic answers it
   cheapest.
4. **Which `0x01C2` `u16` is the agent id?** Two arms with distinct values.
5. **What do `0x01BF`'s two trailing `u8`s mean?** Distinguishable values, read the row.
6. **Where do hero skill bars come from?** Needs either a targeted search of blob-shaped
   message shapes or a live capture that recruits a hero.
7. **Retry the family under `--encstring`** — never done; it flipped six other opcodes.
8. **A live capture at a henchman outpost** is the only source of OBSERVED ground truth for
   retail's send order and field values. Post-Searing Ascalon City, four level-3 henchmen
   (§6) — that is the shopping list.

---

## 9. Defects and corrections this arc produced

- **`msgshape.py` prints `string16(0)` for every wide-string field.** `Field.__repr__` shows
  `self.cap`, but the `wstring` branch never passes `cap=` to the constructor — only `wire=`.
  The true capacity is recoverable only by back-solving from the wire total. A real,
  reproducible display bug that will mislead anyone who trusts the printed capacity, and the
  reason §1.1 says `string16(20)` where the tool says `(0)`.
- **A 48×12 table at `0xA35B80` is `s_titleClientData`, not `s_heroClientData`** (§2). Two
  adjacent `Const*` accessors; the structural locator closed on the wrong anchor.
- **`0x0074` is not `{hero_id, level, primary, secondary}`** (§1.3) — 20 fields, 127 bytes.
- **`PARTY_HERO_ADD` is not "a `uint8` level"** (§1.2) — three `u16`s and two `u8`s.
- **The 7-hero cap is a 2011-03-03 update gated on party size, not an EotN feature** (§6).
- **`0x01C2` has no dedupe scan**, so the "entry+0 is the primary key" analogy is refuted
  (§1.2).
