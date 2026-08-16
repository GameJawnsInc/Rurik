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

> **`0x01C2` msg+0xc (→ entry+0x0) is the AGENT ID; msg+8 (→ entry+0x4) is the HERO INDEX.**

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
