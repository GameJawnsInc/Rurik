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
- **The 38797 pin cannot currently run.** Its run-dir archive has map 146/148 mid-replacement
  (row 7982 renamed `0x8001B97D`); on 38833 those maps bind to *different files* than
  `dat_study`. Clean explorable maps on the 38833 pair are **90, 474, 558** — Lakeside County
  is not one. `contentids.py` refuses correctly; this is archive state, not a bug, and it was
  not repaired here.
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
> so it is definitively NOT the hero index.**)*

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
