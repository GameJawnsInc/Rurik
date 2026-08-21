# What we actually know about the character

Nine research tracks over the 21 vault mirrors, our own captures, and the wire
schema — each track adversarially re-verified citation by citation, then swept
by a completeness critic. This document records only what survived, and labels
everything. It covers the five invented values called out in
`toolkit/authsrv/authsrv.py` (appearance, 0x00B7, the attribute constants,
WORLD_CREATE_AGENT's unknown fields, the 0x008A reply) and the three forward
questions (level, armor, character creation).

## Labels used throughout

| Label | Meaning |
|---|---|
| **OBSERVED** | We saw it ourselves, against the real client, in our own logs. |
| **UPSTREAM** | OpenTyria's code says this, and a verifier confirmed the line. Not a fact about ArenaNet's server. |
| **RECONSTRUCTION** | The source itself signals it is guessing — offset-named field, placeholder magic, stale annotation. |
| **CORROBORATED** | Genuinely independent lineages agree; each use names which ones. |
| **CONTESTED** | Sources disagree. Both sides are recorded; nobody picks a winner. |
| **UNVERIFIED** | Claimed somewhere, and the verifier could not confirm it. Do not build on this. |
| **NOT FOUND** | We looked, and recorded where; there is no answer in the sources we have. |

As in the movement pass: **no claim below is a sourced fact about retail Guild
Wars.** The only ground truth we possess is our own client's behaviour. What
changed since that pass is that we now know two of our "witnesses" were not
what we thought — the one-page answer is next, and the source-map section after
it explains why several corroboration counts moved.

---

## The answer in one page

**The appearance bitfield is real, and it is the best-corroborated fact this
project now owns.** Three lineages that share no author implement the identical
32-bit packing — OpenTyria's C bitfield, gw-preservation's Go shifts, GWLP-R's
Java byte arithmetic — and GWCA reads the profession nibble out of the live
client at exactly bit 20. `APPEARANCE = PROF_WARRIOR << 20` stops being an
invention; it becomes a corroborated layout carrying our chosen values.
(Section a.)

**Two discoveries about our sources outrank any single field.** First,
`schema/messages.json` is not a second lineage: its own provenance block says
it was imported from OpenTyria's `msgdefs.c`. Every past "the schema agrees
with OpenTyria" was one witness counted twice — including several places in
this repo's comments. Second, the arbiter artifact this project keeps saying it
lacks — the client's own packet-template tables — has been on disk all along:
`gw-preservation__network-log-explorer/src/lib/Constants.ts` holds
client-dumped field tables for build 38771 (26 builds before ours), and
GWLP-R-Utils holds a second, older dump plus a 769-packet named catalog. Where
those tables speak, they outrank every reimplementation. (Source map, below.)

The five invented values, resolved:

- **a. Appearance** — layout CORROBORATED; the value ranges (how many faces,
  hair styles…) are NOT FOUND anywhere, and nothing yet proves the profession
  nibble drives the visuals, because we send profession twice in one burst.
- **b. 0x00B7's three bytes** — `primary_profession, secondary_profession,
  is_pvp` by name in two lineages, AgentId + three Uint8s in the client's own
  38771 table. Our `[agent_id, 1, 0, 0]` is what every readable implementation
  sends for a PvE Warrior. The third byte's name is convention; nothing
  consumes it. (Section b.)
- **c. 42 and 50** — both OpenTyria's. 42 is the implicit terminator of its
  attribute enum, found nowhere else; 50 is an uncited literal at
  `GmPlayer.c:125-126` that two other lineages replace with 0/0. Worse: whether
  our 42-zero array is even well-formed is open — one lineage's client parses
  the array as (id, base, bonus) triplets, under which our payload is 14 bogus
  Fast Casting entries. And attribute *ids* diverge +3 between OpenTyria and
  everyone else from Dagger Mastery on — a silent off-by-three trap. (Section c.)
- **d. 0x0020's unknown fields** — the widths are now settled by the client's
  own template table; the *names* are mostly NOT FOUND, honestly. Two fields
  gained real meaning: `h000B` is an agent-kind byte (0 item, 5 player, 9 NPC),
  and field 12 is an allegiance FourCC — `0x706c6179`, ASCII `'play'`, in three
  lineages — which OpenTyria's `0xBAADF00D` merely fills. The 12.0f reading of
  `h0027` is contradicted by the client template (it deserializes as DWORD, not
  float). Nothing in this message carries level, profession, appearance, or
  equipment. (Section d.)
- **e. 0x008A** — our reply matches OpenTyria's handler almost verbatim, so the
  *content* is as good as upstream knows how to make it. But upstream also
  volunteers the same burst unprompted on the 0x0090 path, no source documents
  what the client actually wants here, and our own comment claiming the
  unanswered request caused the 44 s stall is confounded four ways. Verdict:
  right content, unproven placement. (Section e.)

The three forward questions:

- **1. Level** — the character shows level 0 because we never send any
  level-carrying message. The one that matters is agent int-property **36** on
  `0x009F` (159); one packet after WORLD_CREATE_AGENT should do it. Do not
  import `0x9E` — that is older-build numbering. (Section 1.)
- **2. Armor** — item-in-bag and worn-on-body are different messages, and only
  the worn one is disputed: the per-slot visual-equip message (our 111/0x006F)
  is the probe that settles both the opcode mapping and the slot order.
  Appearance comes from `file_id & 0x7fffffff`, not `model_id`. The armour
  *rating* lives in item modifier words — **decoded 2026-08-20, identifier 572's
  argument, and read off the client's own tooltip; see §2** — once the largest hole
  this pass leaves. (Section 2.)
- **3. Creation** — runs entirely on the game channel behind a
  `REQUEST_GAME_INSTANCE` flagged `map_type 11` and/or `map_id 0`; the flow is
  mapped end to end with per-step provenance. The blocker is four bytes: nobody
  on disk knows what bytes 4-7 of the client's 8-byte creation config carry.
  (Section 3.)

One cross-cutting caveat, flagged once: every `declared_unpack_size` in the
imported schema assumes u32 string-length prefixes, while our own codec writes
u16 and the client accepts it, and one GWLP-R template says int16. The
convention is load-bearing for several size arguments and has never been
verified against a capture.

---

## The source map changed: read this before trusting any citation

Three discoveries in this pass re-weight every cross-source argument, including
some in the movement study.

### 1. `schema/messages.json` is OpenTyria. It corroborates nothing.

The file's own provenance block says it: `"imported_from": "ldufr/OpenTyria
code/msgdefs.c"`, `"authority": "imported"`, `validated_against_build: null` —
and its `source_commit` (`c60a8c4`) matches `MANIFEST.json`'s recorded HEAD for
the OpenTyria mirror exactly. Its 0x0059 field list is byte-identical to
`msgdefs.c`. OBSERVED, checked by two tracks independently.

The consequence: every place this pass or a previous one counted "the schema
agrees with OpenTyria" as cross-lineage corroboration was counting one witness
twice. This document's corroboration counts have all been rebuilt without it.
The schema's declared arbiter, `schema/overrides.json` ("Every entry here
CONTRADICTS the imported OpenTyria tables"), currently holds exactly one
measured override — GAME_CMSG 144, 19 bytes, from our own capture — so no
character-cluster shape is presently known-wrong, but the schema is a
convenience index of ldufr, not evidence.

### 2. gw-preservation is a second real lineage — and it holds client dumps

All four `gw-preservation__*` repos have one sole author, "Energy"
(locked-chest) — OBSERVED via `git log` on each. That makes them ONE witness,
but a witness **independent of ldufr**: zero authorship overlap with Laurent
Dufresne, no credits to OpenTyria anywhere in the tree, its own codegen, its
own (older) opcode numbering. The movement study's lineage table placed
`network-log-explorer` inside the ldufr group; that was half right and needs
splitting **per artifact**:

- Its opcode **name** tables are verbatim ldufr — still no independent voice.
- Its **field-type** tables (`src/lib/Constants.ts`: `FieldsGS_StoC_38771`,
  `FieldsGS_CtoS_38771`, with the decoder in `FieldParser.ts:6-50`) are
  **packet-template tables dumped from the client itself, build 38771** — the
  exact artifact `schema/messages.json`'s provenance note calls "the arbiter
  ... not yet dumped". It was on our disk the whole time.

Build 38771 is 26 builds before our 38797, so it is still not our client's
table — but it is the only non-derived witness we have for wire shapes, and
where it is cited below it outranks every reimplementation.

### 3. Three more sources nobody had opened

- **`Fournux__Tyria-Extractor`** — a 21st mirror, its own lineage (solo Rust
  author, live packet sniffer). Its `doc/ITEM_EXTRACTION.md` settles three item
  questions by itself (section 2).
- **`GameRevision__GWLP-R-Utils`** — GWLP-R lineage (shared committers), but it
  carries a second client template dump and a 769-packet named catalog
  (`Templates/PacketTemplates.xml`) that names the whole character-creation
  cluster (`CharacterCreateHead/Acknowledge/Error`, `UpdateAppearance`,
  `AppearanceAndProfession`).
- **`th0br0__sgwlpr`** — GWLP-R lineage, but with artifacts GWLP-R proper
  lacks: a third appearance packer AND the only decoder
  (`db/.../Character.scala` — note its hairstyle mask is 0x1F where 6 bits
  need 0x3F; do not import it), and `MapData.scala:734`'s
  `MapInfo(730, 0, 0, "CharCreation")`.

### The corrected lineage table

| Lineage | Members | Nature |
|---|---|---|
| **ldufr** | OpenTyria, Headquarter, **schema/messages.json**, network-log-explorer's *name* tables | Server + headless-client reconstruction; the wire-format layer machine-extracted from one unknown `Gw.exe` build |
| **gw-preservation** ("Energy") | server, network-logger, network-log-explorer, fileserver-utils | Independent Go server + capture tooling; *field* tables are client dumps @38771; server code uses older opcode numbering (clientVersion 37600 era) |
| **GWCA** | GregLando113, JaborGW, GWToolboxpp-bundled copy | Client-memory structs; opcodes drift (−1 SMSG in places, −2 CMSG); the *bundled* (newer) copy realigns with our build around 0x0059 |
| **GWLP-R** | GameRevision GWLP-R, GWLP-R-Utils, th0br0 sgwlpr | Java/Scala servers + a client template dump; CMSG creation block at −7; item SMSG range at +10/+12 |
| **Py4GW** | apoguita Py4GW, Reforged, Reforged_Native | Live-client scripting. Its packet tables are verbatim copies (of ldufr's tracer and of GWCA's opcodes header) — **almost never a fourth voice**. Its client-derived artifacts (ECHARATTRIB tables, creation-UI frame tree, a working creation routine) are real evidence. |
| **Fournux** | Tyria-Extractor | Independent Rust live sniffer; items/NPCs |
| (no character content) | MapBrowser pair, web players (shiburito → gwnative; toboshii), fileserver-utils | Checked and clean — nothing on appearance, professions, attributes, items, or creation |

Rule that emerged twice this pass: **name tables and field tables inside one
repo can have different provenance.** Check the artifact, not the repo.

---

## a. The appearance dword

**The bit layout is the best-corroborated fact in this study.** Three
independent lineages implement the identical 32-bit packing, a fourth reads one
field of it out of live client memory, and our own capture shows the dword
sitting in the slot every server puts it in.

| Bits | Width | Field | Notes |
|---|---|---|---|
| 0 | 1 | sex | 0 = male, 1 = female |
| 1-4 | 4 | height | |
| 5-9 | 5 | skin color | |
| 10-14 | 5 | hair color | |
| 15-19 | 5 | face style | |
| 20-23 | 4 | primary profession | Warrior = 1 |
| 24-29 | 6 | hair style | |
| 30-31 | 2 | campaign (OpenTyria's `GmChar.h` alone says "race") | 0 = Prophecies/core |

The witnesses, one per lineage:

- **ldufr** — a C bitfield struct with `STATIC_ASSERT(sizeof == 4)`
  (`ldufr__OpenTyria/code/GmChar.h:95-105`, widths at `:81-86`). Within this
  lineage the bit *positions* are declaration-only: no shift arithmetic exists
  anywhere in OpenTyria (grep-verified), so the positions rest on C bitfield
  allocation order. Headquarter re-declares the same struct twice
  (`ldufr__Headquarter/include/client/constants.h:165-174`,
  `code/client/character.h:6-33`) — same author, so reinforcement, not
  corroboration.
- **gw-preservation** — explicit shifts and masks, both directions
  (`gw-preservation__server/gameservice/appearance.go:52-58` encode, `:23-30`
  decode): sex@0, height@1, skin@5, hair@10, face@15, profession@20,
  hairstyle@24, campaign@30. Identical. One warning: this file's trailing
  comments are wrong ("Bits 16-23" beside a `>>15`); trust its arithmetic,
  never its comments. Its three seeded characters cross-check the profession
  nibble — `0x0744943b`, `0x042094e6`, `0x045171b5` all satisfy
  `(bits>>20)&0xF == ProfessionPrimary` (`db/schema.go:178-181, :200-225`;
  `gameservice/appearance_test.go:180-190`) — with the caveat that seeds and
  encoder share a repo, so this is self-consistency, not independent data.
- **GWLP-R** — hand-rolled little-endian byte packing whose arithmetic
  re-derives to the same bit map exactly
  (`GameRevision__GWLP-R/mapshard/.../CharacterFactory.java:88-92`);
  `th0br0__sgwlpr/db/.../Character.scala:27-30` carries byte-identical
  expressions plus the only *decoder* on disk (`:57-67`) — same lineage, and
  its hairstyle mask is `0x1F` where six bits need `0x3F`; do not import it.
- **GWCA** — the client's pre-game context, read from live memory:
  `GetPrimaryProfession() { return (props[2] >> 20) & 0xF; }`
  (`gwdevhub__GWToolboxpp/Dependencies/GWCA/include/GWCA/Context/PreGameContext.h:25`).
  One field, but it is bit 20 read out of the real client.

**CORROBORATED** across ldufr + gw-preservation + GWLP-R for the full layout,
plus GWCA on the profession nibble. Profession numbering None=0, Warrior=1 …
Dervish=10 is corroborated across four lineages (`GmChar.h:14-27`;
`GregLando113__GWCA/Include/GWCA/Constants/Constants.h:17-20`;
`apoguita__Py4GW/Py4GWCoreLib/enums_src/GameData_enums.py:60-72`;
`GameRevision__GWLP-R/mapshard/.../enums/Profession.java:13-25` — cite the Java
enum, not the SQL seed, which has no None row). So `APPEARANCE = 1 << 20` at
`authsrv.py:128-132` graduates from invented to **corroborated layout** — the
*choice* of an all-zero body with only the profession nibble set remains ours.

**OBSERVED, on our own wire.** The capture
(`vault/captures/authsrv/authsrv-20260805T132932-c2.jsonl:55`) shows
PLAYER_CREATE leaving as `5900 | 01000000 | 01000000 | 00001000 | 00 | 00000000
| 00000000 | 0c00 + "Test Warrior"` — the dword `0x00100000` in the third
payload slot, byte-verified. The client accepted it and produced a movable
agent. What we have *not* observed is the client rendering a Warrior *because*
of this dword — we send AGENT_PROFESSIONS (0x00B7) with profession 1 in
the same burst, 0.4 ms later, which confounds any visual attribution. GWCA
models the client's Player with `appearance_bitmap` *separate* from
primary/secondary profession dwords (`.../GameEntities/Player.h:8-18`), so the
client has more than one profession channel and our traffic cannot say which
one dresses the body.

### Where the dword travels

Two places, both now pinned:

1. **PLAYER_CREATE (0x0059), third payload field.** The shape — dword,
   agent_id, dword, byte, dword, dword, string16(32) — is corroborated by
   ldufr (`GameMsg.h:414-424`), GWLP-R (`P077_UpdateAppearance.java:15-21`,
   aligned by shape and its own −11 packet numbering, reinforced by
   `GWLP-R-Utils/Templates/PacketTemplates.xml:1254-1279` "UpdateAppearance"),
   gw-preservation (`StoC.go:284-293`, at its older 0x58), **and by the
   client's own template table**:
   `gw-preservation__network-log-explorer/src/lib/Constants.ts:1562`,
   `FieldsGS_StoC_38771[0x0059]` = Uint32, AgentId, Uint32, Uint8, Uint32,
   Uint32, String16(32) under that repo's own `FieldParser.ts:6-50`. The same
   client table settles the opcode non-circularly: at build 38771, 0x0058
   carries a different shape entirely (one dword + string), so the old GWCA
   headers' 0x0058 is build drift, and our 0x0059 — already proven by our
   capture — is the client's own number.
2. **The character-select settings blob**, bytes 8-11, after version:u16,
   last_outpost:u16, last_time_played:u32 (`GmChar.h:110-115`;
   `AuthMsg.h:156-165`) — corroborated by gw-preservation's independent
   encoder writing the same slot (`authservice/handlers.go:177-182`). Our
   `authsrv.py:266` comment is correct.

### The contests, kept as contests

- **What the third field of 0x0059 *is*.** ldufr, GWLP-R and gw-preservation
  all call it the appearance dword. All three GWCA copies name that slot
  `file_id1` and the following byte `secondary_profession`
  (`GregLando113__GWCA/Include/GWCA/Packets/StoC.h:239-247`, identical in the
  bundled copy). **CONTESTED** — three lineages to one, and the GWCA naming
  looks like stale annotation (the field is declared `uint32_t` with a `// byte`
  comment, no code anywhere reads `file_id1`, and GWCA models real appearance
  elsewhere as `appearance_bitmap`) — but GWCA's struct layouts are its
  acknowledged strength, so the contest stands. The client's own 38771 table
  cannot adjudicate: it carries types, not names (it calls the whole message
  `PLAYER_UPDATE_AGENT_INFO`). Practical consequence today: none. Under either
  reading our `[.., APPEARANCE, 0, ..]` is valid — 0 in the following byte is
  Profession_None if GWCA is right and harmless if not. Testable: send a
  nonzero byte in field 4 and look for a secondary profession.
- **"race" vs "campaign" for bits 30-31.** After verification this is nearly
  one-sided: Headquarter — ldufr's own client — names it `campaign : 2` with
  the identical "0=prof, 1=faction, 2=nightfall" comment
  (`include/client/constants.h:173`, `code/client/character.h:25`), so `race`
  is a one-file naming slip by an author who calls it campaign everywhere
  else. Three lineages say campaign; the comment on the `race` line describes
  campaigns anyway. Not to be confused with the *4-bit* `campaign_type` field
  in CharacterSettings ("0=pvp, 1=prod, 2=faction, 3=nightfall") —
  Headquarter disambiguates the two by name (`character.h:25` vs `:27`).
- **The sixth payload field (second trailing dword).** Three sources fill it
  three ways: 0 (ldufr), `0xCCCCCCCC` (gw-preservation — an uninitialized-stack
  marker, almost certainly copied from a capture of a real server leaking
  padding), `0x3CBFA094` (GWLP-R — a different captured-looking value). The
  client's 38771 table types it a plain unnamed Uint32. Best reading: unread.
  We send 0; the client accepts it. **CONTESTED** on meaning, moot in effect.

### The settings word, and our [medium] annotations

The packed u16 after the appearance dword and guild-hall uuid —
`campaign:4 | level:5 | is_pvp:1 | secondary_profession:4 | helm_status:2`
(`GmChar.h:116-123`) — is corroborated by gw-preservation's encoder building
the same word with shifts, including the tell: it skips bit 9 entirely
(level at `<<4` for 5 bits, secondary at `<<10`,
`authservice/handlers.go:184-189`), leaving a hole exactly where OpenTyria
declares `is_pvp:1`. GWCA's pre-game context reads the same dword from client
memory: `IsPvP()` at bit 9, `GetSecondaryProfession()` at bits 10-13
(`PreGameContext.h:26-29`). Our `"1140"` decodes as campaign=1, level=1,
is_pvp=0, secondary=0, helm=1 (Show) — internally consistent with a Prophecies
level-1 Warrior.

Two `[medium]` annotations in `authsrv.py:262-271` can be upgraded: the
`number_of_pieces` u8 and the trailing junk dword are both **CORROBORATED** —
gw-preservation writes the same u8 count and a literal `0xDDDDDDDD` tail
(`handlers.go:212-215`), sgwlpr writes the same `0xDD`-patterned tail
(`Character.scala:31-37`), matching OpenTyria's note that the blob leaks the
client's uninitialized heap fill. One mild counter-signal: Headquarter declares
`h001E`/`h0021` as real fields rather than padding (`character.h:32-33`), so
"believed unread" should stay "believed", not become "known".

### NOT FOUND, after real searching

- **Value ranges.** How many heights, skins, hair colors, faces, hair styles
  the client actually offers: nowhere on disk. OpenTyria's `*_MAX` macros are
  restatements of the bit widths with zero usage sites (`GmChar.h:88-93`);
  gw-preservation masks to the width and validates nothing. The closest
  artifact is Py4GW_Reforged's character-creation UI frame tree
  (`Py4GWCoreLib/FrameTree/frame_names.py:38, :48, :140`, `frame_aliases.py:1073`
  — HairStylePicker, FacePicker, SkinColorPicker), which names the pickers and
  carries no cardinality. The safe statement: every reimplementation accepts
  any value that fits the width, and none claims the client does.
- **An independent decode of the dword in GWCA/Py4GW beyond bit 20 and bit 0.**
  Everything else is declarations, a hex print, and one Asura-only
  gender read (`TextToSpeechModule.cpp:350-353` — guarded by a race check and
  reading `npc->appearance`, so it is one race-specific path, not a general
  decode).
- **Bytes 4-7 of the client's 8-byte creation config.** OpenTyria memcpy's
  only the first 4 into an `Appearance` (`GameSrv.c:1699-1701`); GWLP-R
  declares the same 8 bytes opaque; the 38771 client table confirms the size
  (`FieldsGS_CtoS_38771[0x008b]` = String16(20), FixedBytes(8), Uint32) and
  nothing else. This is section 3's blocker, recorded once there and once here.

One trap for future porters: Py4GW's `Gender` enum (Unknown=0, Female=1,
Male=2, `GameData_enums.py:53-56`) is a different namespace from the appearance
sex bit and silently breaks male characters if imported.

### Open items

- **Does the profession nibble drive anything client-side?** Vary the nibble
  while holding 0x00B7 fixed, and vice versa. The cheapest high-value probe in
  this section — today the two are perfectly confounded.
- **Field 4 of 0x0059:** send a nonzero byte and look for a secondary
  profession. Settles GWCA's naming one way or the other.
- **Does the client-*sent* creation dword use the same layout?** Every witness
  describes server→client; OpenTyria's creation unpack assumes symmetry and
  nothing corroborates the assumption. Answered for free the first time real
  creation runs (section 3).

---

## b. AGENT_PROFESSIONS (0x00B7): the three trailing bytes

*(Named PLAYER_UPDATE_PROFESSION when this section was written; renamed
2026-08-19 to the catalog's `AGENT_PROFESSIONS` — see "Opcode numbering —
do not import `0x9E`" below and `schema/overrides.json`. The old name was
ldufr's/OpenTyria's, UPSTREAM.)*

Nine bytes total: a 2-byte header, a 4-byte agent id, then three single bytes.
Every source on disk agrees on that shape. Only the third byte's *meaning* is
disputed, and no source anywhere describes what the client does with it. What we
already send — `[agent_id, 1, 0, 0]` at `authsrv.py:908-910`, on the wire as
`b70001000000010000` — is what every implementation we can read sends for a PvE
Warrior. The practical answer is settled; the semantics are not.

### What each source calls the three bytes

| Lineage | Artifact | byte 1 | byte 2 | byte 3 | Opcode |
|---|---|---|---|---|---|
| ldufr | `ldufr__OpenTyria/code/GameMsg.h:111-117` | `primary_profession` | `secondary_profession` | `is_pvp` | 0x00B7 |
| ldufr | `ldufr__Headquarter/code/client/agent.c:988-997` (bound at `game.c:595`) | `prof1` | `prof2` | `is_pvp` — declared, **never read** | 0x00B7 |
| ldufr | `ldufr__OpenTyria/tools/trace-packets.py:241-247` | primary | secondary | is_pvp | 0x00B7 |
| ldufr, restated | `schema/messages.json` #183 | `byte` | `byte` | `byte`, size 9 | 183 |
| GWLP-R | `GameRevision__GWLP-R-Utils/Templates/PacketTemplates.xml:2469-2493` | `PrimaryProf` | `SecondaryProf` | `isPvP` | header 171 |
| GWLP-R | `th0br0__sgwlpr/codegen/PacketTemplates.xml:1932-1942` | `firstProfession` | `secondProfession` | `isPvp` | header 171 |
| GWLP-R | `GameRevision__GWLP-R/.../outbound/P171_UpdatePrivProfessions.java:15-18` | `primaryProf` | `secondaryProf` | `isPvP` | 171 |
| gw-preservation | `gw-preservation__network-log-explorer/src/lib/Constants.ts:2042-2047` | `Uint8` | `Uint8` | `Uint8` — unnamed | 0x00B7 |
| gw-preservation | `gw-preservation__server/gameservice/StoC.go:485-491` | `primaryProfessionId` | `secondaryProfessionId` | `unk1`, `val:0` | 0x00b6 |
| GWCA | — | **no struct exists** | | | opcode define only |

**Our schema is not a witness.** `schema/messages.json`'s own provenance block
reads `imported_from: "ldufr/OpenTyria code/msgdefs.c"`, `authority: "imported"`,
`validated_against_build: null`. The originating rows are literally there:
`msgdefs.c:2990-2996` (`GAME_SMSG_0183`, five fields) and the size table at
`:5531` (`{183, 5, GAME_SMSG_0183, 9}`). Counting our schema beside OpenTyria
counts ldufr twice; so does counting Headquarter, same author. The byte
arithmetic checks either way — 2 + 4 + 1 + 1 + 1 = 9.

So the honest count on the shape is **three lineages: ldufr, GWLP-R,
gw-preservation.** GWCA contributes nothing to the payload — a mirrors-wide grep
binds no `Packet<T>::STATIC_HEADER` to this opcode in any GWCA repo, GWToolbox
registers no StoC handler for it, and Py4GW's packet-level knowledge here is a
bundled copy of ldufr's `trace-packets.py`/`msgs.py`. **NOT FOUND**, checked
twice by different methods. Note also that GWLP-R's number is 171, not 183 — it
is a **shape** match across builds, not a number match.

Provenance splits *inside* gw-preservation and must be tracked per artifact. Its
opcode **name** table (`Constants.ts:239-246`) reproduces OpenTyria's names and
gaps line for line — ldufr, restated. Its **field** table (`FieldsGS_StoC_38771`,
entry at `Constants.ts:2042-2047`) is a client template dump from build 38771:
`[0x0010, 0x0104, 0x0104, 0x0104]`, decoded by `FieldParser.ts` as
`(definition >> 0) & 0xf` — `0x0010` → type 0 → `AgentId`; `0x0104` → type 4,
count 1 → `Uint8` (`FieldParser.ts:19-23`). That table is the best
client-derived witness we have for this message: a real client, at build 38771,
placing AgentId + three Uint8s at opcode 0x00B7. It carries no field names — the
names come from ldufr and GWLP-R only.

### The opcode number

`0x00B7` = 183 is ldufr's (`ldufr__OpenTyria/code/opcodes.h:248`), and our
`authsrv.py:125` plus our schema both descend from it. Outside ldufr, support
for 183 **on our build rests on a single GWCA header**:
`gwdevhub__GWToolboxpp/Dependencies/GWCA/include/GWCA/Packets/Opcodes.h:91`.
`apoguita__Py4GW_Reforged_Native/include/GW/common/opcodes.h:93` is not a second
witness — the two files diff to nine lines (one `#include`, one trailing
newline), and `Py4GW/Py4GWCoreLib/PacketSniffer.py:114` follows the same table
while Py4GW's own bundled `msgs.py:235,240` still uses the old 0x00B6.

Standalone GWCA (`JaborGW__GWCA/.../Opcodes.h:90-91`,
`GregLando113__GWCA/.../Opcodes.h:188-189`) and gw-preservation's Go server
(`StoC.go:485`) put this packet at 0x00B6. That is **systematic -1 drift across
the whole neighbourhood**, not a disagreement about our build:
`JaborGW__GWCA/.../Opcodes.h:86` has AGENT_UPDATE_PROFESSION at 0x00A5 vs 0x00A6,
`:52` has AGENT_CREATE_PLAYER at 0x0058 vs 0x0059, and gw-preservation's
`StoC.go:319` / `:284` mirror both. **Trap:** 0x00B6 is
PLAYER_UPDATE_UNLOCKED_PROFESSIONS in our numbering, so aligning by opcode number
against those sources silently targets the wrong message. The same author's two
repos even contradict each other — NLE's name table says 0x00B7, his server
sends 0x00b6, because the names came from ldufr and the numbers from old GWCA.

**OBSERVED, and thin:** the only build-38797 evidence for any of this is that our
client accepts the 9-byte message at 183 once attribute points precede it
(`authsrv.py:897-904`). **NOT FOUND:** no capture holds a 0x00B7 payload from
anyone. The five build-38797 sessions in `vault/captures/gamesrv/` stop at
MANIFEST_PHASE and contain none, and there is no real-server capture in existence
here.

### The third byte: CONTESTED on the name, unanimous on the value

ldufr and GWLP-R name it `is_pvp`; gw-preservation names it `unk1` and its
`MarshalPlayerUpdateProfession` takes only three arguments, so no caller *can*
set it — `resp.Uint8(0)` at `StoC_gen.go:598` is unconditional. Nobody who names
it can be shown to mean it, either:

- Upstream hardcodes it and says so: `GmPlayer.c:137` is
  `msg->is_pvp = false; // @Cleanup: use the character settings to fill this value`.
  Those settings are identifiable on disk — `ldufr__OpenTyria/code/GmChar.h:118`
  has `unsigned int is_pvp : 1;` and `GmChar.c:20` is the assignment upstream
  would have used. Its intended meaning, from the path it never wired up, is
  "created with no campaign" (`GameSrv.c:1718`, a DB column) — a PvP-only
  character. A PvE Warrior is therefore 0. **UPSTREAM.**
- GWLP-R contradicts itself: `EntityUpdatePrivateProfessionsView.java:27` hardcodes
  `true` on instance load, `CharacterCreation.java:88` passes `false` on creation.
  **Do not read GWLP-R as evidence for 1.**
- sgwlpr's derivation is incoherent and its author flagged it: `XXX` at
  `CharacterHandler.scala:34`, with `isPvp = 1` when `campaign == 1`, which its
  own comment two lines up labels *prophecies*, while campaign 0 is labelled *pvp*.

The best non-ldufr support for the name is not in the packet at all. GWCA's
`gwdevhub__GWToolboxpp/Dependencies/GWCA/include/GWCA/Context/PreGameContext.h:26-29`
reads `IsPvP() { return ((props[7] >> 9) & 0x1) == 0x1; }` and
`GetSecondaryProfession() { return (props[7] >> 10) & 0xF; }` — and ldufr's
`GmChar.h:116-119` lays out `campaign:4, level:5, is_pvp:1, secondary_profession:4`,
putting is_pvp at bit 9 and secondary at 10-13 of the same dword.
`th0br0__sgwlpr/db/.../Character.scala:32-38` comments the identical byte the same
way. **CORROBORATED across ldufr, GWCA and GWLP-R** that the client carries a real
is_pvp flag sitting immediately before secondary profession in the character blob.
That does not prove the third *packet* byte is that flag — but it is far better
than "two projects use the same variable name."

**NOT FOUND:** no source on disk consumes the byte on receipt. Headquarter
declares it and never reads it (`agent.c:1009-1025`), and Headquarter is a
reimplemented client anyway.

### What a level-1 Warrior with no secondary should send

`[agent_id, 1, 0, 0]` — **high confidence**, from three lineages that do not
share a parent:

| Source | Evidence |
|---|---|
| ldufr | `GmPlayer.c:131-139` assigns only agent_id, primary and `is_pvp = false`; `secondary_profession` is never assigned anywhere, and `GameSrv.c:140-145` memsets the buffer first. Warrior comes from `GameSrv.c:1540`. |
| gw-preservation | `player.go:391-392` sends the literal `(p.agentId, 1, 0)`, third byte forced 0. |
| GWLP-R | `CharacterCreation.java:88` sends `(channel, 1, profession, 0, false)` — literally `[1, prof, 0, 0]`. |

Profession numbering None=0, Warrior=1 … Dervish=10 is **CORROBORATED across
ldufr, GWCA and GWLP-R** (`GmChar.h:14-26`;
`JaborGW__GWCA/Include/GWCA/Constants/Constants.h:21-24` and
`.../GameEntities/Agent.h:191-192`; `.../models/enums/Profession.java:13-26`).
Our `PROF_WARRIOR = 1` is right. Our own code is *not* a witness to correctness
here, only to current behaviour.

### The ordering constraint: attribute points first

**OBSERVED, and ours.** Sending 0x00B7 before attribute points killed the client
with `Assertion: attribState ChCliAttrib.cpp(435)` (`authsrv.py:897-904`). This
is the one hard fact in this section that no mirror gave us.

Every reference server orders it the same way — `GmPlayer.c:169-173`
(points at :171, profession at :172), `InstanceLoadView.java:188-189`,
`sgwlpr/registration/.../CharacterHandler.scala:17` before `:40-42`, and
`player.go:391-392`. Three lineages besides ldufr. Our ordering is not a
workaround; it is what everyone does.

The **mechanism is UNVERIFIED.** The closest artifact is GWCA's — not Py4GW's,
which merely copies it — `WorldContext.h` `GWArray<ProfessionState>
party_profession_states` at `+h06BC`, size `0x14`, commented "aka attribStates",
byte-identical at `gwdevhub__GWToolboxpp/Dependencies/GWCA/include/GWCA/Context/WorldContext.h:67-78`
and `:254`, `JaborGW__GWCA/Include/GWCA/Context/WorldContext.h:254`, and
`GregLando113__GWCA/Include/GWCA/Context/WorldContext.h:177`. Its struct is
`{agent_id, primary, secondary, unlocked_professions, unk}` — the same fields
0x00B7 and 0x00B6 carry between them.
`Py4GW_Reforged_Native/src/GW/skillbar/skillbar_methods.cpp:419` notes the same
assert firing for a *different* trigger (agent_id 0 handed to a template loader),
which is consistent with "the assert fires when the state entry cannot be
resolved by agent id" — consistent, not proof. **No source ties that array to
opcode 0x00B7.** The causal story is our inference.

### Adjacent, and a correction worth carrying

`APPEARANCE = PROF_WARRIOR << 20` (`authsrv.py:131-132`) is **CORROBORATED**, not
unverified. `ldufr__OpenTyria/code/GmChar.h:95-104` packs `sex:1 + height:4 +
skin:5 + hair:5 + face:5 = 20 bits` before `primary_profession:4`;
`th0br0__sgwlpr/db/.../Character.scala:26-30` emits `byte2 = profession<<4 |
face>>1`, and byte 2 bit 4 *is* dword bit 20; and GWCA's
`PreGameContext.h:25` reads `GetPrimaryProfession() { return (props[2] >> 20) &
0xF; }`. Three lineages, same bits. The byte we send after APPEARANCE in
PLAYER_CREATE (0x0059) is **CONTESTED in name only** — `secondary_profession` per
`gwdevhub__GWToolboxpp/.../Packets/StoC.h:243`, `unk0` per `GameMsg.h:419`. Our 0
is Profession_None under the first reading and harmless under the second.

### Open items

- **What does the client do with the third byte?** Nothing on disk consumes it,
  and no implementation ever sends a non-zero value, so the name rests on
  convention plus a same-named bit elsewhere in the character blob. A local probe
  sending 1 and watching the skills/attributes window would settle it — a
  live-client experiment, not a reading task.
- **What actually allocates the attribState entry?** We know empirically that
  0x0037 before 0x00B7 avoids the crash, but no source says which message creates
  the `ProfessionState` slot. `WORLD_CREATE_AGENT` is an equally plausible
  candidate. Our ordering works; we do not know why.
- **Should we also send 0x00B6 and 0x00A6?** The shapes are known and cheap:
  schema #182 is agent_id + dword, size 10, matching NLE's 38771 client dump
  `0x00b6 = [0x0010, 0x0404]` (AgentId + Uint32); 0x00A6 is agent_id + two bytes,
  size 8, the *public* other-agents variant with no third byte
  (`P154_UpdatePublicProfessions.java:15-17`, `instance.go:670`). Upstream sends
  0x00B6 immediately after 0x00B7 inside `SendSkillsAndAttributes`, carrying
  `player->character.unlocked_professions` (`GmPlayer.c:146`), set once at creation
  to `1 << primary` (`GameSrv.c:1722`). We send neither. Likely belongs to the
  skills/attributes track.
- **Why does upstream send 0x00B7 twice on instance load?** `GameSrv.c:1469` via
  `SendSkillsAndAttributes`, then again at `:1476` after `BroadcastPlayerCreate`,
  both inside `GameSrv_HandleInstanceLoadRequestPlayers` (1436-1495). Is the
  second load-bearing — does agent creation reset the client's profession state? —
  or is it redundancy? Nothing in the code explains it. We send it once.

---

## c. Attributes: where 42 and 50 come from

Both numbers in `authsrv.py:154-161` come from the same place, and it is not the
client. `ATTRIBUTE_COUNT = 42` and `ATTRIBUTE_POINTS = 50` are OpenTyria's, and
nothing else on disk produces either one. That is the headline, and it survived
verification intact. What did *not* survive is the researcher's follow-on story
about what the 42-element array means; that is now a single-lineage hypothesis
with an experiment attached, and it is flagged as such below.

### 42 is an enum terminator, not a constant

**UPSTREAM.** `Attribute_Count` is not declared anywhere. It is the implicit
last member of a 42-entry enum whose last *named* member is
`Attribute_Mysticism = 41` (`ldufr__OpenTyria/code/GmAttributes.h:3-4, :45-47` —
the whole file is 49 lines: one enum, ids 0..41 assigned explicitly, terminator,
no `#define`, no comment). OpenTyria then writes `msg->data_len =
Attribute_Count` into 0x003A (`GmPlayer.c:267`) and leaves the array itself
untouched, relying on `GameSrv_BuildMsg`'s `memset` (`GameSrv.c:140-144`). Our
`[0]*42` reproduces upstream byte for byte — `toolkit/schema/codec.py:12, :196`
puts a u16 count of 42 on the wire followed by 168 zero bytes.

**Nothing else on disk declares 42.** The verifier re-ran this negative
independently across all 21 mirrors with different terms: the only
`attribute…42` hit anywhere is `ldufr__Headquarter/include/client/constants.h:93`,
`ATTRIBUTE_WIND_PRAYERS = 42` — a coincidence of value. Every attribute-shaped
fixed array on disk is 12, 16, 48 or 54. The only other 42-member list is
GWLP-R's Java enum (`mapshard/…/models/enums/Attribute.java:12-56`), and its own
repo's SQL seed contradicts it. **42 is upstream-only, with one
self-contradicted echo.**

Two adjacent numbers are better sourced than 42 and should not be confused with
it: **48** is the wire *capacity* of the 0x003A array, and **44** is
Headquarter's declared maximum attribute id (`ldufr__Headquarter/code/client/skill.c:578`
— though note it is a function-local `const` inside `template_decode()`, not a
protocol-wide constant, corroborated in-repo by `constants.h:95`).

### The numbering trap: +3 from Dagger Mastery onward

**CORROBORATED, and this is the most dangerous thing in the section.** OpenTyria
numbers attributes contiguously 0..41. Everyone else leaves 26/27/28 unused and
ends at 44. From Dagger Mastery on, the two schemes differ by a constant +3.

| Attribute | OpenTyria (`GmAttributes.h`) | Everyone else |
|---|---|---|
| Marksmanship | 25 | 25 |
| *(reserved / unnamed)* | — | 26, 27, 28 |
| Dagger Mastery | **26** | **29** |
| Mysticism | **41** | **44** |
| Ceiling | `Attribute_Count` = 42 (terminator) | `ATTRIBUTE_MAX = 44`; client table runs to **50** |

Witnesses for the gapped form, across three lineages outside ldufr plus ldufr's
own *client* project: `ldufr__Headquarter/include/client/constants.h:79-80, :95`;
`GregLando113__GWCA/Include/GWCA/Constants/Constants.h:66-71` (one voice, three
copies); `apoguita__Py4GW/Py4GWCoreLib/enums_src/GameData_enums.py:326-329, :344`
(names the holes `Unknown1..3`); `GameRevision__GWLP-R/database/src/main/sql/default_data.sql:102`
(names them `'Reserved'` — different vocabulary for the same three holes, which
argues against transcription). Contiguous form: OpenTyria, plus GWLP-R's Java
enum, which its own SQL contradicts. **CONTESTED within GWLP-R; corroborated
against OpenTyria.**

The strongest witness is client-*data*-derived rather than hand-written: the
`ECHARATTRIB` table at
`apoguita__Py4GW_Reforged/docs/item_mods/tools/game_mod_tables_resolved.txt:5-56`,
resolved against the client's own text-id table — 0..25 named, 26/27/28 present
but resolving to garbage strings, 29 Dagger Mastery … 44 Mysticism. **And ids
45-50 are also present, also garbage.** So the id *space* does not stop at 44.
"45 ids" is our framing, not the client's; treat the size of the space as OPEN.

Concretely: any code of ours that indexes attributes by a GWCA/Py4GW/Headquarter
id against OpenTyria-derived data is **silently off by three from Dagger Mastery
onward**. Warrior and ranger attributes are safe; assassin, ritualist,
dervish and paragon are not. Nothing has bitten us yet only because we rank
nothing.

### 50, and the two bytes of 0x0037

**UPSTREAM, uncited.** `msg->unused_points = 50; msg->used_points = 50;` at
`ldufr__OpenTyria/code/GmPlayer.c:125-126` — a bare literal written to both
bytes, with no comment, no table, and no points-per-level logic anywhere in the
tree to derive it from. The verifier re-searched documentation and data-dump
directories the researcher's code-only globs would have skipped and found
nothing that derives 50.

Against it:

- `gw-preservation__server/gameservice/player.go:391-392, :507-508` — an
  independent lineage (sole author "Energy", verified by git authorship) sends
  **0, 0** on a live path that reaches `InstanceLoadFinish`. RECONSTRUCTION: the
  same file names the fields `points1`/`points2` rather than committing, and is
  littered with `// REVERSE THIS MORE:`.
- `GameRevision__GWLP-R/database/src/main/sql/default_data.sql:437` — the only
  level-to-points table on disk. L1=0, L10=45, L11=55, L20=170. **50 is skipped
  between 45 and 55, and there is no level-0 row at all.** GWLP-R's runtime
  defaults are 0/0 and its character-creation path never overrides them
  (`Components.java:120-124`; verified by exhaustive grep, nothing assigns them).
- CONTESTED, weakly: a deprecated Py4GW leveler comments "50 attribute points
  available" at levels 7-8 (`Nightfall_leveler.py:65, :67`), against GWLP-R's
  30 and 35. Nightfall grants points by quest on top of the level table, which
  explains the divergence. Either way, nothing puts 50 at level 0, and our
  character is level 0.

**The two bytes' shape is settled; their meaning is not.** `agent_id` then two
`uint8`s, agreed by OpenTyria (`GameMsg.h:368-373`), GWLP-R
(`P044_AgentAttributeCreate.java:16-17`), gw-preservation (`StoC.go:228-232`,
which carries its own `// opcode: 0x0037` annotation — our build's numbering),
and confirmed client-side by a binary dump
(`GameRevision__GWLP-R-Utils/deprecated/PacketTemplate Dumper/…/[StoC] Game server Table.txt`,
Packet 0x002C = `ID; BYTE; BYTE`). Field 1 is the spendable pool in all three
namings. Field 2 is `used` (OpenTyria) vs `max` (GWLP-R) vs unnamed
(gw-preservation). **CONTESTED, and materially so**: with 50/50, "used" means
100 points total; "max" means a 50-point pool entirely free.

Ordering is better established than the values. Upstream sends points before
profession (`GmPlayer.c:169-174`), gw-preservation does the same
(`player.go:391-392`), and GWLP-R names the 0x0037-equivalent a **CREATE**
message with a matching `P236_AgentAttributeDestroy` — which is exactly the
shape our own crash implies.

**OBSERVED (ours).** Sending profession without prior attribute state killed the
client on `Assertion: attribState`, `ChCliAttrib.cpp(435)` (`authsrv.py:897-902`).
This is the only attribute observation we own. It establishes that *something*
must precede profession. It does not establish that the something is 0x0037
rather than 0x003A, nor that 50/50 or 42 zeros are right.

### 0x003A: the array shape is settled, the array *unit* is not

**Shape — CORROBORATED across two lineages** (not four; see the caveat).
`uint16` count, then count × `uint32`, capacity 48, declared unpack size 202
(= 2+4+4+48×4): `ldufr__OpenTyria/code/msgdefs.c:2109-2113, :5406`,
`ldufr__Headquarter/code/client/skill.c:502-507`, and
`GameRevision__GWLP-R/protocol/…/P047_SetAttributes.java:19-20`
(`@IsArray(size = 48, prefixLength = 2)`). The 48 is a *capacity*: OpenTyria's
packer writes only `data_len` elements and errors above 48
(`msgpack.c:363, :370-372, :374, :383`).

Two caveats on that "corroborated". First, `schema/messages.json` is **not** a
witness — its own provenance block reads `"imported_from": "ldufr/OpenTyria
code/msgdefs.c"`, `"authority": "imported"`, with a mechanical importer at
`toolkit/schema/import_msgdefs.py` and `"validated_against_build": null`. It is
OpenTyria. Second, GWLP-R's headers are 44/47, not 55/58 — a different client
build. Its own binary dump makes this concrete: in that build the 48-max DWORD
array is Packet **0x002F**, and 0x003A is an unrelated 3-field message. GWLP-R
corroborates the *shape*, not our opcode.

**Unit — UNVERIFIED, single-lineage hypothesis. Do not build on this.**
Headquarter parses the array as three parallel sub-arrays — `attribute_id`,
`rank_base`, `rank_bonus` — requiring the element count divisible by 3
(`ldufr__Headquarter/code/client/skill.c:533-544`, verified line for line).
Under that reading, our 42 zeros are not 42 empty slots; they are 14 copies of
Fast Casting at rank 0, parsing only because 42 happens to divide by 3 — and
the comment at `authsrv.py:157-159` claiming the array's *length* declares how
many slots exist is supported by no source at all.

That is a genuinely alarming reading, and it rests on **one witness in one
lineage**, with two structural problems:

- Headquarter is a *reimplementation*. `skill.c:511` asserts against its own
  202-byte unpacked struct. This is ldufr's reading of the client, not the
  client's behaviour — and ldufr's server contradicts it.
- The claimed independent corroboration is **REFUTED**. Py4GW's 3-field
  `AttributesStruct` (Id/Value/BaseValue) is not a wire unit: the client's real
  in-memory attribute record is **five** `uint32`s — id, level_base, level,
  decrement_points, increment_points, `sizeof == 0x14` — identically in
  `GregLando113__GWCA/Include/GWCA/GameEntities/Attribute.h:11-17` and
  `apoguita__Py4GW_Reforged_Native/include/GW/context/attribute.h:12-19`.
  Py4GW's struct is an author-chosen 3-of-5 projection of a cache.

The companion arithmetic — "48 = 16 × 3, sixteen triplets" — is **inference, not
corroboration**. The three 16s are real (`skill.c:356-358, :372, :623-625`;
`GregLando113__GWCA/Source/SkillbarMgr.cpp:598-599`), but Headquarter's CMSG is
two *separately* length-prefixed 16-arrays and does not factor as 16×3, GWCA's
`[16]` are unchecked caller-local stack buffers, and the newer bundled GWCA uses
`[12]` (`gwdevhub__GWToolboxpp/Dependencies/GWCA/include/GWCA/Managers/SkillbarMgr.h:33-34`).
The multiplication is ours.

**The experiment that settles it.** Send 0x003A with count 0, then 3, then 42,
and watch the client. Upstream's packer handles `array_size == 0` cleanly, so
count 0 is a legal frame. Two confounds to control first: Headquarter's handler
*bails before parsing* if no skillbar exists for the agent
(`skill.c:518-528`), so the run may need a skillbar update sent first; and
gw-preservation reaches the world **never sending 0x003A at all**
(zero hits for the opcode in `gameservice/`), so a null result may mean the
message is optional rather than that our payload is fine.

### Open items

- **Send 0x003A with count 0, then 3, then 42.** The one high-information
  experiment here. It decides between "42 zeros are a well-formed empty array"
  and "our array is 14 bogus Fast Casting entries." Send a skillbar update first
  to clear Headquarter's precondition, and treat "no visible difference" as
  inconclusive, not as vindication.
- **Adopt the gapped numbering (26/27/28 reserved) before ranking anything.**
  Three outside lineages plus a client-derived text-id table agree; only
  OpenTyria and one self-contradicted Java enum do not. The +3 offset is silent
  and will not announce itself. Also stop assuming the id space ends at 44 — the
  client table runs to 50 with the tail unresolved.
- **Decide 50/50 versus 0/0, and find out what the second byte means.** Two
  servers send two different constants for the same message. The only level
  table on disk gives level 1 zero points and has no level-0 row. Probing the
  client's attribute panel distinguishes `used` (50 spent + 50 free = 100 total)
  from `max` (a 50-point pool, all free) directly.
- **Test whether 0x003A is load-bearing at all.** An independent server reaches
  `InstanceLoadFinish` sending only 0x0037. Our `attribState` crash proves
  *something* must precede profession; it does not prove which message, and we
  have never tested dropping 0x003A.

---

## d. WORLD_CREATE_AGENT (0x0020): naming the unknown fields

The movement pass established the shape of this message and stopped there: 23 fields
after the header, 97 payload bytes, 99 = 0x63 total, and **15 of 24 fields named only
by their byte offset** — the worst ratio of any struct in OpenTyria. Seven of those
fifteen are assigned a placeholder value; eight are never assigned at all. This section
asks the next question — *does anyone, anywhere, know what they are?* — and the answer
is mostly no, but the "mostly" is where the useful part lives.

**The layout itself is now settled by a client-authored witness, not by consensus among
emulators.** `gw-preservation__network-log-explorer/src/lib/Constants.ts:1262-1285`
carries the client's own 23-entry packet-template descriptor array for 0x0020, dumped
from build 38771 (ours is 38797). A second, byte-identical copy exists in
`GameRevision__GWLP-R-Utils/deprecated/PacketTemplate Dumper/Predumped/Packet Templates/[StoC] Game server Table.txt:363-405`
— but that one is GWLP-R lineage (same GameRevision committers as GWLP-R itself), so it
is one lineage, not two. Per-artifact provenance matters here: network-log-explorer's
*name* tables are verbatim ldufr and are never corroboration, while its *field* tables
are client dumps and are the strongest evidence on disk. The descriptors decode to
`[0x404, 0x404, 0x104, 0x104, 0x012, 0x204, 0x002, 0x104, 0x021, 0x001, 0x404 ×7, 0x002, 0x012, 0x204, 0x404, 0x012, 0x204]`
— 23 slots matching our `schema/messages.json` GAME_SMSG 32 field-for-field. Summing
by the client's own descriptor-size rule (`Fournux__Tyria-Extractor/crates/tyria_sniffer/src/win32_dll/hooks.rs:436-450`)
gives 112 + 4 = 0x74, which is exactly the size Fournux's live sniffer records for this
opcode (`src/capture.rs:36-41`, `header: 0x0020, name: "AGENT_SPAWNED", size: 0x74`).

Our server sends this message as a verbatim copy of OpenTyria's
(`toolkit/authsrv/authsrv.py:877-896`). OpenTyria's unassigned fields go out as zero
provably, not by assumption: `ldufr__OpenTyria/code/GameSrv.c:140-144` memsets the whole
message buffer before setting the header.

### The seven assigned placeholders

| Field (offset, client-typed width) | Our value | Candidate name(s) — lineage + citation | Verdict |
|---|---|---|---|
| `h000B` @0x000B, BYTE (0x0104) | `5` | No name in any lineage. GWCA `unk3` (`GregLando113__GWCA/Include/GWCA/Packets/StoC.h:132`); GWLP-R `unknown2` (`GameRevision__GWLP-R/.../P021_SpawnAgent.java:15`) | **NOT FOUND** (name). **CORROBORATED** (values): 0 = item, 5 = player, 9 = NPC — three lineages, and one *reader*: `gwdevhub__GWToolboxpp/GWToolboxdll/Modules/ItemDrops.cpp:95-98` rejects any agent with `unk3 != 0` |
| `h001E` @0x001E, BYTE (0x0104) | `1` | Unnamed everywhere. GWCA `unk6; // word` (`StoC.h:134`) | **CORROBORATED** value = 1 (ldufr `GmAgent.c:148`, gw-preservation `StoC_gen.go:149`, GWLP-R `EntitySpawningView.java:76`). Width **settled as BYTE** — see below |
| `h0023` @0x0023, FLOAT (0x0001) | `1.0` | Unnamed. GWCA `unk7; // default 1.0` (`StoC.h:136`) | **CORROBORATED** value (four lineages). Name **NOT FOUND** |
| `h0027` @0x0027, **DWORD (0x0404)** | `0x41400000` | GWCA `unknown_bitwise_1` (`StoC.h:137`) — the only label anyone gives it | **CORROBORATED** bytes (three lineages write the raw magic). The 12.0f reading is **CONTRADICTED** — see below |
| `h003B` @0x003B, DWORD (0x0404) | `0` | Unnamed. Folded into GWCA's `unk8[5]` (`StoC.h:139`); GWLP-R `unknown9` | **CORROBORATED** value 0. Name **NOT FOUND** |
| `h004B` @0x004B, VEC2 (0x0012) | `(+INF, +INF)` | Unnamed. GWCA `unk10; // inf, inf` (`StoC.h:141`) | **CORROBORATED** value (four lineages). Name **NOT FOUND** |
| `h0059` @0x0059, VEC2 (0x0012) | `(+INF, +INF)` | Unnamed. GWCA `unk12; // inf, inf` (`StoC.h:143`) | **CORROBORATED** value (four lineages). Name **NOT FOUND** |

**`h001E` is a BYTE.** The movement doc's cross-check table logs GWCA's `// word` as an
unexplained outlier against four byte-witnesses (`studies/movement/FINDINGS.md`, row
"0x0020 field #8 type"). The client template closes it: slot 8 carries descriptor
`0x0104`, byte-identical to slots 3 and 4 (`agent_type`, `h000B`), both of which every
source reads as BYTE. GWCA's annotation is wrong, and its offset comments in this struct
are independently known to drift by 4 bytes from `unk6` onward.

**`h0027` is not a float.** Three servers write `0x41400000` and it *is* the IEEE-754
bit pattern for 12.0f, which made "12.0f" a tempting reading — the movement doc records
it that way, as "bytes known, meaning not". The client template settles the type question
against it: slot 11 carries `0x0404`, the same descriptor as `agent_id` and `model_id`,
while `speed_base` and `h0023` (slots 9, 10) carry the *distinct* float descriptors
`0x0021` / `0x0001`. The client does not deserialize this slot as a float. Even upstream
declares it `uint32_t` beside a `float` neighbour (`ldufr__OpenTyria/code/GameMsg.h:398-399`).
The 12.0f interpretation should be dropped, not carried as an open option. What the
bits *mean* remains unknown; GWCA's `unknown_bitwise_1` is the only guess on record.

### The eight never-assigned fields

| Field (offset, client-typed width) | Our value | Candidate name(s) — lineage + citation | Verdict |
|---|---|---|---|
| `h002F` @0x002F, DWORD | `0` | GWCA `unk8[5]` member; GWLP-R `unknown6`; gw-preservation `unk6 //wire:uint32,val:0` | **NOT FOUND** — confirmed absent |
| `h0033` @0x0033, DWORD | `0` | same three, positional only | **NOT FOUND** — confirmed absent |
| `h0037` @0x0037, DWORD | `0` | same three, positional only | **NOT FOUND** — confirmed absent |
| `h003F` @0x003F, DWORD | `0` | same three, positional only | **NOT FOUND** — confirmed absent |
| `h0043` @0x0043, VEC2 (0x0002) | `(0.0, 0.0)` | GWCA `unk9`, no default comment (`StoC.h:140`); GWLP-R `unknown11` | **NOT FOUND** (name). Value **CONTESTED** — see below |
| `h0053` @0x0053, WORD (0x0204) | `0` | GWCA collapses to `unk11[2]`; GWLP-R `unknown13`; gw-preservation `unk13 //wire:uint16,val:0` | **NOT FOUND** — confirmed absent |
| `h0055` @0x0055, DWORD (0x0404) | `0` | same three, positional only | **NOT FOUND** — confirmed absent |
| `h0061` @0x0061, WORD (0x0204) | `0` | GWCA `unk13`; GWLP-R `unknown16`; gw-preservation `unk15 //wire:uint16,val:0` | **NOT FOUND** — confirmed absent |

The "confirmed absent" verdicts are load-bearing: the verifier re-swept eight repositories
the first pass never opened — `Fournux__Tyria-Extractor`, `gw-preservation__network-log-explorer`,
`gw-preservation__network-logger`, `th0br0__sgwlpr`, `apoguita__Py4GW_Reforged`,
`GuildWarsMapBrowser`, `gw-preservation__fileserver-utils`, `jean-humann__gwnative` — and
found no name for any of these eight anywhere. It did find a missed *layout* copy
(`th0br0__sgwlpr/codegen/PacketTemplates.xml:568-594`, our exact 23-field sequence under a
bare `<Packet header="21">` with no `<Name>`), which is GWLP-R lineage and adds no names.
That template table is the reason the widths in the table above are firm even where the
names are empty.

**On `h0043`:** OpenTyria leaves it zero and gw-preservation writes `(0.0, 0.0)`
(`gameservice/StoC_gen.go:159-160`); GWLP-R writes `(+INF, +INF)`
(`EntitySpawningView.java:81`). Do not resolve this by counting emulators — two
reimplementations agreeing is not evidence about the client, and GWLP-R sets *all three*
Vec2f slots to INF, so it may simply be blanket-filling. This stays **CONTESTED** until
our own client tells us otherwise.

### Which names to trust, and why almost none of them

The distinction that matters here is not client-memory versus reimplementation — it is
sharper than that. **The only client-authored artifact on disk is a type table, and type
tables have no name column.** The descriptor arrays give us widths with near-certainty
and names with certainty zero. Every name in the two tables above was written by a
reverse-engineer.

Among those, one filter separates the useful from the decorative: *does any code read
the field, or only write it?* A name attached to a field nobody reads is a label, not a
finding. By that test, exactly two of this packet's unknown fields have behavioural
backing — `h000B`, via GWToolbox's item filter, and field 12 @0x002B (below), via
`gwdevhub__GWToolboxpp/GWToolboxdll/Modules/PartyWindowModule.cpp:952`, which reads
`pak->allegiance_bits` directly off an `AgentAdd` callback to decide party-window
membership. Nothing in the GWCA lineage ever reads `unk4`..`unk13`. Headquarter — the
one source that parses a real server's stream — consumes six fields (`agent_id`,
`model_id`, `type`, `position`, `speed_base`, `direction`) and reads none of the rest,
so its offset names, including `model_type`, carry no weight. Headquarter also declares
26 payload fields rather than 23, splitting each Vec2f into scalar pairs, so it is not a
straight mirror of the server struct and should not be used for offset alignment.

One discipline carried over from the movement doc: **GWCA's `// default 1.0`,
`// inf, inf` and `// default 288.0` comments are annotations of unknown provenance, not
measurements.** The movement doc grades 288.0 as "two reconstructions agree; neither
measured" (`studies/movement/FINDINGS.md`, Speed section) and that grading is right. The
same applies to `h0023` and to both INF pairs: a second lineage agreeing is the best
corroboration available and it is still not an observation. Nothing in this section
upgrades a header comment to a fact.

Py4GW adds nothing to any of this: its `trace-packets.py` is a byte-identical copy of
OpenTyria's and its `stoc.h` `AgentAdd` is a verbatim copy of GWCA's. All three apoguita
repositories collapse into ldufr + GWCA for this packet.

### What this packet does *not* carry — and it is all of the character

For the character brief, the negative result is the finding: **no field of 0x0020
carries level, profession, attributes, appearance, or equipment.** The only
identity-bearing field is `model_id` @0x0006, whose high nibble selects the kind
(3 = player, 2 = NPC) with the player number in the low bits — our
`CHAR_CLASS_PLAYER_BASE | PLAYER_NUMBER` is correct. One caveat worth carrying: the
lineages disagree on the mask width. Headquarter uses `& 0xffffff` with `>> 28`
(`ldufr__Headquarter/code/client/agent.c:232-234`), while GWCA/GWToolbox use
`^ 0x30000000` and `Fournux__Tyria-Extractor/src/npcs.rs:287-299` uses
`& 0x0fff_ffff` — 24 bits of id versus 28. Harmless for player number 1; wrong the
moment a model id exceeds 0xFFFFFF.

So the fifteen unknown fields are, for our level-0 naked test character, *not the
problem*. Level arrives separately as agent int-property 36 on opcode **0x009F (159)** —
not 0x9E, which is gw-preservation's older numbering and is a 323-byte string message in
our schema; see section "## 1." for the detail. Visible equipment is likewise a separate
message; both this track and track g agree the nine-dword
`UPDATE_AGENT_VISUAL_EQUIPMENT` is **0x006E** (our schema "110" = `agent_id` + 9 dwords,
`ldufr__Headquarter/code/client/opcodes.h:217`), with a per-slot message adjacent. The
identity of 0x006D is contested between the tracks — defer to "## 2.", which covers it in
depth. Appearance lives in `PLAYER_CREATE`, not here.

### Field 12 @0x002B: the one field this pass actually named

OpenTyria calls it `player_team_token` and fills it with `0xBAADF00D`
(`ldufr__OpenTyria/code/GameSrv.c:1233`) — a self-evident debug filler, and the only such
constant in a protocol field anywhere in that repo. Three independent lineages converge
on a real value instead: GWCA names it `allegiance_bits` and GWToolbox hardcodes
`1886151033` (`PartyWindowModule.cpp:409`); GWLP-R defines
`SpawnType.Player (1886151033) // "play"` alongside `"nonc"`, `"ally"`, `"mob"`
(`GameRevision__GWLP-R/.../enums/SpawnType.java:15-18`); gw-preservation writes
`allegianceFlags := 0x706c6179` (`gameservice/player.go:305`). Same constant, three
lineages, and it is the ASCII FourCC `'p','l','a','y'`. Within ldufr the naming is
self-contradictory — the server header says `player_team_token`, the client handler
(`agent.c:198`) and the tracer (`tools/trace-packets.py:181`) say `model_type` — and
neither ldufr copy ever reads the field, so `model_type` is an unused guess.
**CORROBORATED: this is an allegiance / spawn-type FourCC, not an opaque token.**

**Recommendation (not adopted):** change `PLAYER_TEAM_TOKEN` from `0xBAADF00D` to
`0x706c6179`. It must change in **both** send sites — `toolkit/authsrv/authsrv.py:865`
(INSTANCE_LOADED) and `:889` (WORLD_CREATE_AGENT) — because every lineage keeps the same
token in both messages, and gw-preservation independently puts the real `'play'` constant
in both. Changing one and not the other breaks an invariant all four servers maintain.
Whether the client parses the token or merely compares the two is a hypothesis; nothing
on disk decides it. (Note also that gw-preservation's INSTANCE_LOADED opcode is 0x00F1 in
its numbering against our 0x00F2 — its *shape* argument transfers, its opcode numbers do
not.)

### Open items

- **`h000B` is a latent bug the moment we spawn anything but the player.** OpenTyria
  sends `5` unconditionally, including for NPCs, and we inherited that. The corroborated
  table is 0 = item, 5 = player, 9 = NPC. Correct today; blocking as soon as NPCs or
  drops exist.
- **`h0043`: (0,0) or (+INF,+INF)?** Two reimplementations against one, which is not
  evidence. Since `h004B` and `h0059` are unanimously INF, GWLP-R may be right. A live
  A/B against our own client is the only thing that can settle it, and it only matters
  if the field turns out to govern clamping or pathing bounds.
- **We have captures and never looked at them.** `vault/captures/` holds dozens of paired
  `.jsonl`/`.raw` files recording our own sent packets with decoded opcode and values.
  They are server-side, so they cannot show what the client *does* with a placeholder —
  but they can confirm our 0x0020 leaves at 99 bytes and that the client does not
  disconnect on it, which is the cheapest OBSERVED datum available for this message.
- **The one experiment that would replace this whole section:** dump our own client's
  deserializer table for build 38797. Both copies of the descriptor array on disk are
  build 38771. The layout has been stable from 0x0015/21 through 0x0020/32, so drift is
  unlikely — but "unlikely" is what this document is written to avoid saying.

---

## e. 0x008A during map load: right answer or lucky unblock?

Our client sends CMSG `0x008A` (wire opcode 138) twice during an ordinary map
load — a map load, not character creation, which we never drive. We answer it
with a four-message burst copied from OpenTyria. **The content is probably
right; the placement is likely-but-unproven.** Everything that makes this
uncomfortable is in the second half of that sentence.

### What upstream's handler actually does, and how our burst compares

OpenTyria dispatches `0x008A` from one case in `GameSrv_ProcessPlayerMessage`
(`GameSrv.c:1870-1871`, switch at `:1845`) into
`GameSrv_HandleCharCreationRequestArmors` (`GameSrv.c:1557-1575`). The body is
lookups plus exactly four sends and `return ERR_OK`. UPSTREAM, read in full by
the verifier.

| Upstream send (`GameSrv.c:1570-1573`) | Ours (`authsrv.py:842-852`) | Match |
|---|---|---|
| `SendUpdatePvpUnlockedSkills` → SMSG 0x001D (29) | `[[0] * 128]` | **Shape only.** The all-zero body is ours ("nothing unlocked at level 1", `authsrv.py:840-841`); upstream's content was not verified. |
| `SendUnlockedPvpHeroes` → 0x0018 (24), every word `0xFFFFFFFF` (`GameSrv.c:238-240`) | `[[0xFFFFFFFF] * 8]` | **Verbatim.** |
| `SendPvpItems` → **387** × `PVP_ITEM_STREAM_ADD` 0x001A (table `GameSrv.c:249-642`, ADD built at `:644`) then `PVP_ITEM_STREAM_END` 0x001B (`:652`) | bare `END`, no ADDs (`authsrv.py:848-849`) | **No.** This is the one real divergence in content. |
| `SendAccountFeatures` → nine 0x000F triples (`GameSrv.c:658-667`) | `ACCOUNT_FEATURES` (`authsrv.py:213-215`) | **Verbatim, byte for byte.** |

Send order is identical. Opcode arithmetic cross-checks against `opcodes.h:161-165`
(15/24/26/27/29) and against our own schema shapes for SMSG 29, 24, 27, 15.

**The name is a red herring and upstream proves it.** `GmDefaultArmors` is live
code, but `GetDefaultEquipments` has exactly one consumer outside its own file —
`GameSrv.c:1641`, inside the `CHAR_CREATION_CHANGE_PROF` (0x0060) handler, which
replies with `SendBagItems` (`GameSrv.c:1677-1679`). No armour, item, bag or
equipment call appears anywhere in the 0x008A handler. The comment at
`authsrv.py:204-206` saying so is correct.

**And upstream does not treat this as the delivery path at all.** The same four
sends fire *unprompted* at the top of OpenTyria's `INSTANCE_LOAD_REQUEST_PLAYERS`
(0x0090) handler (`GameSrv.c:1460-1464`, plus `SendUnlockedMaps`, before
`SendInstanceLoaded` at `:1466`). Upstream's client gets this data on the PLAYERS
path whether or not 0x008A ever arrives. **We relocated it to be 0x008A-only** —
our 0x0090 branch (`authsrv.py:853+`) sends none of the four, confirmed
behaviourally in the capture. UPSTREAM + OBSERVED.

### What each lineage calls it, and when our client actually sends it

| Lineage | Its number for our 0x008A | Name | Reply implemented |
|---|---|---|---|
| **ldufr** (`opcodes.h:123`; Headquarter `client/opcodes.h:122`; Py4GW `Packet_enums.py:82`; network-log-explorer `Constants.ts:119`) | 0x008A | `CHAR_CREATION_REQUEST_ARMORS` — ldufr's own coinage, 2024-08-11, flowing server → client library | the four sends above |
| **Py4GW legacy** (`Legacy code and tests/Packet-UI-Listener/msgs.py:113-115`) | 0x0089 (−1) | same ldufr names, shifted | none (listener) |
| **GWLP-R** (−7) | P131 | `P131_Unknown` — no fields, nothing subscribes, while P130/P132/P088 *are* handled | none |
| **gw-preservation** (Energy, −1, `CtoS.go:139`) | 0x8089 | `CreateCharRequestItems` | default warrior equipment, `handlers.go:217-236` |
| **GWCA** (GregLando113 `Packets/Opcodes.h:3-99`, −2) | 0x0088 | **unnamed** — the table jumps 0x0086 SPAWN → 0x008E PLAYERS, leaving 0x0087-0x008D, exactly the char-creation block, blank | — |

CONTESTED, and it is a real contest: two independent lineages give incompatible
replies to the same message, neither citing the other. Do not pick a winner from
code alone. Partly reconcilable, though: gw-preservation registers it *only* in
`preGameHandlers` (`handlers.go:45`), never in `inGameHandlers` — their model
says the client never sends this during a map load. Our client contradicts that.

**The strongest evidence for the placement is structural, not onomastic** —
two client-dumped tables, from different builds, agreeing on shape:

- network-log-explorer's FIELD table (a client dump, build 38771, at *our*
  numbering): `Constants.ts:952-981` gives `0x0088 []`, `0x0089 []`, `0x008a []`,
  `0x008b [0x1417, 0x0805, 0x0404]`, `0x0091 [0x0104, 0x0104]`.
- GWLP-R-Utils' predumped template table (older build, −7):
  `[CtoS] Game server Table.txt:1581-1661` gives `0x0083` header-only,
  `0x0084 = 0x1417 0x0805`, `0x0089 = 0x1005`, `0x008A = 0x0104 0x0104`.

Same template words, offset by exactly seven. Our 0x008A is a bare header sitting
between two bare headers and immediately before the name+appearance confirm.
CORROBORATED across two lineages by field shape. Note the split inside
network-log-explorer: its *name* table is ldufr's verbatim and casts no vote;
only its *field* table is the client dump.

**OBSERVED, from our own capture** (`authsrv-20260805T133648-c2.jsonl`): the
client sends 138 at t=0.231 (before `REQUEST_ITEMS`) and again at t=0.788 —
63 ms after `INSTANCE_LOAD_FINISH`, i.e. in the same phase where upstream pushes
the burst unprompted. Answering with our burst is **sufficient**: the session
runs 189 s fully in-game with no third 138. Suggestive, not conclusive — we
answered the first ask identically, so we cannot tell from this capture whether
the re-ask is triggered by missing content or is unconditional.

### Correction 1: Py4GW never settled our alignment

`authsrv.py:225-227` records that our numbering was "settled against Py4GW's
CTO_OPCODES." That reasoning is **circular, and worse than circular.** Py4GW's
table is a verbatim copy of OpenTyria's — 101 of 101 name/value pairs identical,
three additions, dated after. And the "second mirror off by one" that same
comment says it discarded is *inside Py4GW itself*
(`Legacy code and tests/Packet-UI-Listener/msgs.py:113-115`). Py4GW holds both
sides of the disagreement and cannot adjudicate either.

What actually supports the alignment: GWLP-R (−7) and gw-preservation (−1)
independently agreeing on the block's internal order, plus the two client-dumped
field tables above. The conclusion stands; the stated justification does not.

### Correction 2: our own comment overclaims the 44-second stall

`authsrv.py:835-839` reads the 44 s stall and dropped connection as the
consequence of an unanswered 0x008A. **Not established.** Exactly one capture in
26 has 138 unanswered (`authsrv-20260805T100836-c2.jsonl`, 29 lines, 138 at
line 14 t=0.234, `ConnectionResetError` at t=44.705), and that run differs from
the healthy ones in at least three further uncontrolled ways: it sent
`MANIFEST_PHASE` (408) twice with **no** `MANIFEST_DONE` — the exact defect the
same commit blamed for the client's "Invalid manifest phase" assertion — and it
emitted **zero** `WORLD_SIMULATION_TICK` (0x001E) messages, while every healthy
run ticks every ~50 ms from t=0.07. Commit `afedab6` shipped four fixes together
(manifest phase, map_file_id, `PLAYER_DATA_DONE`, 0x008A) with no isolated
revert and no A/B run recorded anywhere in the project. The client stopped
requesting anything immediately after the two bad manifest messages — the
signature of an assertion crash, not of a wait on unlock data. (The
`PLAYER_DATA` bug *is* excluded in that run: 390 START at line 7, 394 DONE at
line 9, balanced.) We did not identify the blocker; we changed four things and
the client lived.

### Verdict

**Right content, wrong-or-unproven placement.** Three of our four message kinds
match OpenTyria's handler exactly and the fourth is a truncated stream that the
client demonstrably tolerates. What we cannot justify is the *placement*: no
source anywhere documents when the client emits 0x008A or what reply satisfies
it (CONFIRMED_ABSENT across every mirror in the vault), two lineages file it as
character-creation-only, ldufr's own bot client never sends it during map load —
and ours sends it twice. Account-features may simply be what upstream happened
to hang there.

### Open items

- **Is the placement wrong-but-compensating?** Move the four sends to the 0x0090
  handler exactly as upstream does (`GameSrv.c:1460-1463`), leave 0x008A
  unanswered, and count 138s. If the second 138 disappears, we are answering in
  the wrong place and getting away with it.
- **Is 0x008A blocking at all?** Revert *only* the 0x008A branch, leaving the
  manifest, map_file_id and PLAYER_DATA fixes in place, and run once. Right now
  we have one confounded capture and no evidence whatsoever that dropping it
  costs anything.
- **Inspect the control group.** Seven captures contain exactly one 138
  (100836, 101807, 102351, 102603, 102903, 103206, 111035); nineteen contain two;
  all but 102903 of the singles ended in an error at 40-76 s. These are the
  natural test of "does a satisfied client re-ask?" and none has been read.
- **The naked character will not be fixed here.** Even on Energy's reading,
  `onCreateCharRequestItems` emits only `ItemGeneralInfo` + `ItemMovedToLocation`;
  what makes armour *visible* is `AgentUpdateVisualEquipment` (`StoC.go:86`,
  0x006d / `:100`, 0x006e), sent at agent spawn (`player.go:325-336`), never from
  that handler. By field shape those are our GAME_SMSG 110 and 111 (+1 drift).
  That spawn-time pair is the experiment the brief actually wants.

---

## 1. Level and experience

**No opcode is named for level, experience, morale or skill points.** Level is
always a *value inside* a generic property message; experience only ever travels
inside the player-attribute set. Confirmed absent by two searches: OpenTyria's
`opcodes.h` (all 390 lines) and GWCA's `Opcodes.h`, and re-confirmed against
`apoguita__Py4GW/Py4GWCoreLib/PacketSniffer.py:13-260`, a full StoC opcode→name
table for a current client. **NOT FOUND**, and this is a settled negative.

Two channels carry the player's own level, and they are unrelated:

- **Per-agent**, as int property 36 on opcode `0x009F` — the one every reference
  server actually uses to make a level appear.
- **Per-player**, as field 9 of the 15-dword attribute set on `0x00E9`, whose
  field 0 is experience.

### Every message on disk that carries a level or experience

Opcode numbers are **our build's** (38797). `declared_unpack_size` is the wire
size: 2-byte header, `string16(n)` = 4 + 2n.

| Opcode | Message | Carries | Scope | Evidence | Label |
|---|---|---|---|---|---|
| `0x009F` / 159, prop 36 | `AGENT_PROPERTY_UPDATE_INT` = `{prop_id, agent_id, value}`, 14 bytes | level | any agent | `ldufr__OpenTyria/code/GmAgent.c:106-113`, `GmAgentProperties.h:40-41`, `opcodes.h:234`; `ldufr__Headquarter/code/client/agent.c:12, :730-732`; `gw-preservation__server/gameservice/player.go:270` | **CORROBORATED** — ldufr and gw-preservation |
| `0x009F` / 159, prop 37 | `LevelUp` — client does `level += 1` | +1 delta | any agent | `ldufr__Headquarter/code/client/agent.c:734-736` | **UPSTREAM.** No server on disk ever sends it (negative re-run across 21 mirrors) |
| `0x00E9` / 233 | `CHARACTER_UPDATE_FACTIONS` / `PlayerAttrSet`, 15 dwords. OBSERVED 2026-08-05 against our own client: **0 XP**, **9 level**, **11 balthazar (numerator)**, **13 skill points** all confirmed. **Field 12 is NOT the balthazar denominator** — sent 2000, the bar read `1000/0`, so the study's "11-12 balthazar" is half right. **Field 10 sent as 0 left the top-left indicator at -100%**, which is not a legal GW morale (range -60% to +10%) and looks like a display of `0 - 100`; the baseline-100 hypothesis is untested. 1-8 and 14 remain unmapped | XP, level, morale, SP | logged-in player | `ldufr__OpenTyria/code/GameMsg.h:217-234`; `ldufr__Headquarter/code/client/player.c:24-70`; `GameRevision__GWLP-R/…/P221_UpdateFaction.java:15-29`; `GregLando113__GWCA/…/WorldContext.h:186, :204-207`; `gw-preservation__server/gameservice/StoC.go:467-483` | Shape **CORROBORATED** — ldufr, GWCA, GWLP-R, gw-preservation. Field 9's *effect* **OBSERVED 2026-08-05**: sending this with field 9 = 5 then 15 moved the Hero window to Level 5 then Level 15 and it held. No longer contested — settled by our own client, which is the only source that could. Probe: `toolkit/authsrv/probes.py` `player_attrs` |
| `0x00EE` / 238 | `PLAYER_ATTR_UPDATE` = `{attr_id, value}`, applied as `+=` over the same 15 slots; `attr_id 0` = experience | XP delta | player | `ldufr__Headquarter/code/client/player.c:150-155, :167-168`; `opcodes.h:276` | Shape **CORROBORATED** — ldufr, GWCA, GWLP-R. Level via `attr_id 9` is **UNVERIFIED**: the one client reimplementation on disk leaves cases 7/8/9 commented out and ignores case 10 |
| `0x0056` / 86 | `NPC_UPDATE_PROPERTIES`, `uint8 profession` + `uint8 level` | level | an NPC | `gw-preservation__server/gameservice/StoC.go:106-118`; `Fournux__Tyria-Extractor/crates/tyria_sniffer/src/packet.rs:149-163` | **CORROBORATED**, not the player's. OpenTyria declares the opcode and never sends it |
| `0x01C2` / 450 | `PARTY_HERO_ADD`, `uint8 level` | level | a hero | `ldufr__OpenTyria/code/GameMsg.h:466-473` | ~~**UPSTREAM**~~ — **SHAPE OBSERVED 2026-08-15, and the upstream reading is CORRECTED.** The client's own descriptor (table `0x00bcb788`, handler `0x00856b80`) is `[u16, u16, u16, u8, u8]`, 10 bytes — three words and two bytes, not "a `uint8` level". Which `u16` is the agent id and which the hero index is **UNVERIFIED**; the two trailing `u8`s are unnamed by any assert. [studies/heroes/FINDINGS.md](../heroes/FINDINGS.md) §1.2 |
| `0x01BF` / 447 | `PARTY_HENCHMAN_ADD`, trailing `profession` + `level` bytes | level | a henchman | `GregLando113__GWCA/…/StoC.h:857-863`; `schema/messages.json` "447" = `{word, word, string16(20), byte, byte}` | ~~**UNVERIFIED**~~ — **SHAPE CORROBORATED 2026-08-15 by the client itself** (table `0x00bcb788`, handler `0x00856b00` → worker `0x00858cb0`, 50 bytes), an independent witness to GWCA. Field 1 indexes the party record, field 2 is the dedupe key, the name is a real wire string16(20). **The two trailing bytes stay NOT FOUND** — stored to entry `+0x2c`/`+0x30` with no naming assert anywhere, so `profession`+`level` remains one lineage's word. [studies/heroes/FINDINGS.md](../heroes/FINDINGS.md) §1.1 |
| `0x0074` / 116 | `MERCENARY_INFO` = `{hero_id, level, primary, secondary}` | level | a mercenary hero | `GregLando113__GWCA/…/StoC.h:315-321`; `ldufr__OpenTyria/code/opcodes.h:220` | ~~**UNVERIFIED**~~ — **the four-field shape is REFUTED 2026-08-15.** The client's own decoder (table `0x00bc8f68`, handler `0x0091e2f0`) reads **20 fields, 127 bytes**: `[u16, u8,u8,u8, u32,u32, u8,u8, u32, u32×10, string16(32)]`. What survives is that field 1 is an id and three `u8`s follow it (stored to record `+8`/`+0xc`/`+0x10`) — consistent with level/primary/secondary but **not confirmed**, no consumer traced to a profession bound-check. [studies/heroes/FINDINGS.md](../heroes/FINDINGS.md) §1.3 |
| headers 66 / 96 | `QuestTapestry` / `DungeonReward`: `experienceEarned`, `goldEarned`, `skillPointsEarned` | XP award | player | `GameRevision__GWLP-R/…/P066_QuestTapestry.java:14-16`, `P096_DungeonReward.java:14-16` | **UNVERIFIED** — single lineage, and no GWLP-R runtime ever fills them |
| char-select settings blob | 5 bits at bit offset 4 of the dword after `last_guild_hall_id`: `campaign(4) \| level(5) \| is_pvp(1) \| secondary(4) \| helm(2)`; max level 31 | level | roster screen only | `ldufr__OpenTyria/code/GmChar.h:86, :93, :116-121`; `gw-preservation__server/authservice/handlers.go:184-189`; `th0br0__sgwlpr/db/…/Character.scala:27-38` | **CORROBORATED** — three lineages |

### The 15 fields of `0x00E9`, mapped against our own client

MEASURED 2026-08-05 with `toolkit/authsrv/probes.py --probe attr_legend`: one
packet, every field set to `1000 + index` so each number names its own field.

| Field | Drives | Label |
|---|---|---|
| 0 | experience (`424,242 xp`) | **OBSERVED** |
| 1 | Kurzick faction, current | **OBSERVED** |
| 2 | Kurzick maximum — sent 1002, bar reads `/ 0` | **NOT THIS MESSAGE** |
| 3 | Luxon faction, current | **OBSERVED** |
| 4 | Luxon maximum — reads `/ 0` | **NOT THIS MESSAGE** |
| 5 | Imperial faction, current | **OBSERVED** |
| 6 | Imperial maximum — reads `/ 0` | **NOT THIS MESSAGE** |
| 7, 8 | nothing visible anywhere in the Hero window | **NO VISIBLE EFFECT** |
| 9 | level | **OBSERVED** |
| 10 | nothing visible. Specifically NOT the `-100%` top-left indicator: 0, 40, 100 and 110 all left it unchanged | ~~**REFUTED as morale**~~ — **the field IS morale; the DISPLAY is what was refuted.** See the 2026-08-20 update below |
| 11 | Balthazar faction, current | **OBSERVED** |
| 12 | Balthazar maximum — sent 1012 and 2000 on separate runs, bar reads `/ 0` both times | **NOT THIS MESSAGE** |
| 13 | skill points | **OBSERVED** |
| 14 | nothing visible | **NO VISIBLE EFFECT** |

> **UPDATE 2026-08-20 — field 10 is morale after all, and this row's verdict was
> too wide.** ArenaNet's own wire settles it: the live corpus's single player
> death (`20260817T183756`, agent 27, t=78.813) carries `0x00EE [attr 10, -15]`
> on the same tick as `0x009C [27, 85]`, and the character's maximum health and
> energy move 120 → 102 and 25 → 22 — exactly 100 − 15 percent of BASE, on both
> pools. GWCA names the same slot `Morale_Percent` and annotates its range as
> 40 to 110. So the sweep above refuted the **top-left indicator being driven by
> this message**, which stands and is worth knowing; it did not refute the field.
> What draws the indicator is still open (`0x009C` is the candidate) and is
> MORALE-Q1 in [studies/morale/FINDINGS.md](../morale/FINDINGS.md), which carries
> the whole mechanic. Fields 7, 8 and 14 are untouched by this.

**The strongest result here is the negative one.** All four faction maxima ignore
this message. A single instance (field 12) was dismissible; four independent
bars behaving identically is a rule. A server that fills 2/4/6/12 expecting to
set the denominators will ship faction bars that render as empty, and the study's
"11-12 balthazar" reading invites exactly that mistake. Where the maxima do come
from is **NOT FOUND** — plausibly a title-track or account-state message we have
never sent.

> **UPDATE 2026-08-16 — answered at the reading level.** The denominators have
> four dedicated one-dword messages of their own: `0x00EA`–`0x00ED`
> (`CHARACTER_FACTION_MAX_KURZICK/LUXON/BALTHAZAR/IMPERIAL`). Shapes are
> confirmed by the client's own 38797 tables (via `schema/messages.json`, no
> override in range); semantics are CORROBORATED across ldufr (Headquarter's
> handler stores the dword into `player_hero.*.max`), GWLP-R (`P222`–`P225`)
> and the GWCA/Py4GW client-memory sink (`WorldContext` `max_*` fields,
> outside the dupe-paired block this message's fields fill). Fields 2/4/6/12
> are `total_earned_*` — *lifetime* faction, a different stat — which is why
> the bars ignore them. Not yet OBSERVED against our client; the one-packet
> probe and the full record are in [STORAGE.md](STORAGE.md) §2, along with
> the title cluster `0x00F3`–`0x00F6` this note's old "plausibly a
> title-track message" guess was half-pointing at.
>
> **OBSERVED 2026-08-18, both directions.** Retail sends all four (132
> sightings over six live captures, 10000/10000/10000/20000 — STORAGE.md
> §2), and the probe ran agent-piloted against our own client (harness
> `20260818T112259`, [RUNS.md](RUNS.md) §Run 1): all four bars filled with
> our distinct values, mapping EA=Kurzick / EB=Luxon / EC=Balthazar /
> ED=Imperial exactly as named, and a re-sent cap took effect mid-session.
> This section's NOT FOUND is closed end to end.

**Practical note for anyone probing this panel:** the Hero window does not
live-refresh. It has to be closed and reopened after a packet lands, which made
an earlier run read as self-contradictory until the owner noticed.

Not on this list, deliberately: `CHARACTER_UPDATE_INFO` `0x0030` / 48. Its seven
fields upstream are `n_charname` + `charname[32]` + six *offset-named* dwords
(`ldufr__OpenTyria/code/GameMsg.h:303-313`, values assigned at
`GameSrv.c:680-694`). **RECONSTRUCTION** — six of seven have no semantic at all.
None is level. Our `["", 0, 0, 1000, 0, 0, 0]` (`toolkit/authsrv/authsrv.py:700-701`)
is a faithful copy of the assigned set, and it cannot be where a level comes from.

**Lineage rule applied throughout, and it costs us witnesses.**
`schema/messages.json`'s own provenance block reads
`"imported_from": "ldufr/OpenTyria code/msgdefs.c" … "authority": "imported"`,
`"validated_against_build": null`. Our schema **is** ldufr. Where it agrees with
`msgdefs.c` or `GameMsg.h` that is one witness quoted twice, not corroboration.
Every shape above is stated with the schema already discounted.

### Opcode numbering — do not import `0x9E`

For our build the int-property message is **`0x009F` / decimal 159**:
`ldufr__OpenTyria/code/opcodes.h:234`, `ldufr__Headquarter/code/opcodes.h:233`,
and `schema/messages.json` "159" = `{msg_header, dword, agent_id, dword}`,
`declared_unpack_size` 14. A sibling track's `0x9e` is **gw-preservation's older
numbering** (`gameservice/StoC.go:452-457`), matching GWCA
(`Opcodes.h:177 … (0x009E) // 158`). Do not carry it in.

The independent tiebreak is Py4GW, which is not in either lineage on this point
and disagrees with GWCA: `PacketSniffer.py:99-101` maps `0x009E` →
`AGENT_DISPLAY_DIALOG` and `0x009F` → `AGENT_PROPERTY_UPDATE_INT`, and
`:500-502` decodes `0x009F` live as `value_id@+4 / agent_id@+8 / value@+12` —
our number *and* our field order, `prop_id` before `agent_id`.

The same −1 shift recurs at `PLAYER_ATTR_SET` (GWCA `0x00E8` vs our `0x00E9`),
`PLAYER_ATTR_UPDATE` (GWCA `0x00ED` vs our `0x00EE`) and
`PLAYER_UPDATE_PROFESSION` (gw-preservation `0x00B6` vs the `0x00B7` our client
demonstrably accepts, `toolkit/authsrv/authsrv.py:899-910`). **Match by shape,
never by number.** Calling this "the documented GWCA build drift" is our own
inference — no drift documentation exists on disk. **RECONSTRUCTION.**

**Resolved 2026-08-19 for the profession pair, and it was not a shift.**
The pvpui static pass read the per-agent PROFESSION table at
`charCtx[+0x2C]+0x6BC` and found `0x00B6` and `0x00B7` are two *different*
writers into it — `AGENT_PROFESSION_BITS` (a profession bitmask) and
`AGENT_PROFESSIONS` (the two profession ids) — both named from the client's
own strings ([../pvpui/FINDINGS.md](../pvpui/FINDINGS.md) §30,
`schema/overrides.json`). So gw-preservation's `0x00B6` is not our `0x00B7`
off by one; it is the neighbour, and the server dropped the upstream name
the same day. Whether the other two rows above are shifts or neighbours is
**UNVERIFIED** — nothing here read them.

### Why our character shows level 0

**OBSERVED:** in-map level reads 0; the character-select roster says level 1
(`toolkit/authsrv/authsrv.py:262-271`, whose `"11400000"` decodes correctly as
campaign=1, level=1, is_pvp=0, secondary=0, helm=1). Those two facts are not in
conflict — the blob only drives the login screen, and nothing reads it in-map.

**OBSERVED:** we send **none** of the level-carrying messages. A grep of
`toolkit/authsrv/authsrv.py` for `0x009F`, `0x00E9`, `0x00EE` and for `PROPERTY`
finds no constant and no send site, independently reproduced by the verifier.
The client is displaying an unset field, not a wrong value.

OpenTyria reaches the same symptom by a different route: `GameSrv_CreateAgent`
memsets the struct (`GmAgent.c:11-18`), `CreatePlayerAgent` sets eight other
fields and not level (`GameSrv.c:993-1007`), and `agent->level` has exactly one
reference in the whole tree — the *read* at `GmAgent.c:110`. It broadcasts
`PublicLevel = 0` forever, even though the `DbCharacter` it loaded has
`level = 1` (`GameSrv.c:1717`). **UPSTREAM**, and a latent bug worth not copying.

**Which client field the nameplate actually draws from: NOT FOUND.** Six places
were searched — GWCA `Agent.h`, `WorldContext.h`, GWToolboxpp's Modules/Windows/
Widgets, Py4GW's sniffer, `Fournux__Tyria-Extractor/…/packet.rs`,
`gw-preservation__network-log-explorer`'s field walker. Nothing on disk connects
opcode 159 prop 36 to a UI element. The claim rests on four servers' *behaviour*,
not on a read of the client's deserializer.

**The experiment that settles it** (one packet, no other change): send `0x009F`
`{prop_id=36, agent_id=PLAYER_AGENT_ID, value=20}` once after
`WORLD_CREATE_AGENT` and read the display. Read **both** level surfaces — GWCA's
`Agent.h` carries `TagInfo.level` at `+0x0004` (uint16) and a separate agent
`level` at `+0x010C` (uint8), so nameplate and agent record are plausibly
different storage. This converts the best-corroborated claim in the pass into an
OBSERVED fact.

### The XP curve — downgraded, and one worked line corrected

`XpReqForLevel(L) = ((L−1)·300 + 1700)·(L−1)` while `L−1 < 22`, else
`(L−1)·15000 − 147400`. `0x6a4` = 1700, `0x23fc8` = 147400.
Source: `gwdevhub__GWToolboxpp/GWToolboxdll/Modules/GameSettings.cpp:1107-1116`
(GWCA lineage — GWToolboxpp bundles GWCA).

| L | 2 | 3 | 4 | 5 | 20 | 22 | 23 |
|---|---|---|---|---|---|---|---|
| XP required | 2000 | 4600 | 7800 | 11600 | 140600 | 168000 | **182600 (cap)** |

The earlier worked example was **mislabelled by level index** — 182600 is L23,
not L22. Corrected above.

**Provenance, downgraded from "the strongest corroboration in this pass":**
Py4GW's `EXPERIENCE_PROGRESSION` (`Py4GWCoreLib/enums_src/GameData_enums.py:459-483`)
matches the formula at every point checked, but it is not an independent
measurement — the function that builds it cites the public wiki
(`Py4GWCoreLib/py4gwcorelib_src/Utils.py:224`,
`https://wiki.guildwars.com/wiki/Experience`), and Py4GW demonstrably copies
tables elsewhere (its `GENERIC_VALUE_IDS` is a verbatim name-for-name subset of
GWCA's `GenericValueID`). So this is **one wiki-derived table agreeing with one
client-derived reimplementation**, not two independent lineages. **CORROBORATED,
with that caveat** — and neither side is a measurement against our build.

Beyond the cap, `Utils.py:234-245` encodes level 23 + `overflow // 15000`. That
is the same single lineage. **UNVERIFIED**, and it is the only thing on disk
that speaks to levels above 20 at all — with the counter-hint that GWToolboxpp's
own fallback label writes `min(current_level, 20)` (`GameSettings.cpp:1149`).

**NOT FOUND:** no server on disk computes level from experience or awards XP.
OpenTyria, GWLP-R and gw-preservation all treat level and XP as static loaded
state. Every XP↔level arithmetic in the mirrors is client-side.

### Attribute points per level — one dead table and a bot's comments

The message itself is settled. `AGENT_UPDATE_ATTRIBUTE_POINTS` `0x0037` / 55 =
`{agent_id, byte, byte}` — **CORROBORATED** across ldufr
(`GameMsg.h:368-373`), GWLP-R (`P044_AgentAttributeCreate.java:15-17`) and
gw-preservation (`StoC.go:228-233`), and this opcode is **not** drifted.

What the two bytes mean is **CONTESTED**, and so is what to put in them:

| Lineage | Names | Value sent |
|---|---|---|
| ldufr | `unused_points` / `used_points` | hardcoded **50 / 50**, no comment (`GmPlayer.c:120-129`) |
| GWLP-R | `freePts` / **`maxPts`** — a different second field entirely | always **0 / 0** (`Components.java:123-124`, never assigned) |
| gw-preservation | `points1` / `points2` | **0 / 0** (`player.go:507-508`) |

No source explains the pair. Our `ATTRIBUTE_POINTS = 50`
(`toolkit/authsrv/authsrv.py:161`) copies ldufr and says so.

**The per-level table has one source and it is dead data.**
`GameRevision__GWLP-R/database/src/main/sql/default_data.sql:437` gives L1=0 …
L20=170 (step 5 to L10, 10 to L15, 15 to L20). `getAttributePoints()` has **no
caller** anywhere in GWLP-R, and `attributeMaxPts` is never assigned from it.
**UNVERIFIED**, single lineage. A re-search across all 21 mirrors found no
second source for 170 and **nothing at all above level 20**.

The apparent second source is not one. `apoguita__Py4GW/Legacy code and tests/…/Nightfall_leveler.py:55-71`
agrees only to L5 (5/10/15/20) then diverges hard (L6=40 vs GWLP-R's 25) — its
own L6 comment attributes the jump to a campaign event, so those are
level-plus-quest-rewards. Its trailing `else` branch says "20 attribute points
available" for level > 10, contradicting the ladder above it. These are skill-bar
annotations, not a table. **Do not lean on them above L5. CONTESTED.**

The attribute-rank cost ladder — cumulative points to reach rank 0..12 =
`0,1,3,6,10,15,21,28,37,48,61,77,97` — is `gwdevhub__GWToolboxpp/GWToolboxdll/Utils/TeamBuildEncoder.h:152-153`,
**UNVERIFIED**, single lineage, and a literal-sequence grep across all mirrors
returns that one hit.

### Minimal message set for a level-N character

In the order the client's own assertion behaviour already forces
(`ldufr__OpenTyria/code/GameSrv.c:1469-1482`; `gw-preservation__server/gameservice/player.go:268-272`).

1. **`0x009F` `{36, PLAYER_AGENT_ID, N}` after `WORLD_CREATE_AGENT`.**
   **CORROBORATED** — two firm lineages: ldufr (server *and* Headquarter's
   client-side decoder, written against real traffic) and gw-preservation, whose
   author shares nothing with the others and wrote his own `// level` comment.
   GWLP-R sends `PublicLevel` too, but its `GenericValue` enum is
   character-identical to OpenTyria's `AgentProperty` enum, so it may be one
   witness copied forward — **do not count it as a third**. This is the
   load-bearing element and the one we are missing entirely.
2. **`0x00E9`, 15 dwords: field 0 = `XpReqForLevel(N)`, field 9 = N, field 10 =
   100, fields 13/14 = skill points.** Shape **CORROBORATED** (four lineages);
   morale's 100 default corroborated by three. Whether field 9 *does* anything
   is **CONTESTED**: OpenTyria writes a literal 0 there (`GmPlayer.c:98-101`)
   while GWLP-R and gw-preservation fill it for real — but Headquarter's client
   decoder consumes it (`code/client/player.c:55`,
   `client->player_hero.level = pack->level;`), so it is a level channel at
   least one client implementation reads.
3. **`0x0037` — already sent, as 50/50.** Changing it to a level-derived figure
   is **CONTESTED** and unsourced above L5. Both fields are `uint8`, so even
   L20's 170 fits.
4. **`0x003A` (58) — already sent, length 42, array zeroed**
   (`toolkit/authsrv/authsrv.py:160`). Whether an all-zero 42-entry payload is
   *well-formed* is **OPEN**, not settled: see section `## c.`, where a
   single-lineage "triplet" reading holds that an unranked character should send
   count 0. Treat "no change needed" as unproven until that resolves. Three
   counts are in play and are different things — 42 (OpenTyria's enum size,
   what we send), 48 (the wire array capacity, the only protocol fact), 54
   (GWCA's in-memory array).
5. **The char-select settings blob's level bits** should say N for consistency.
   **CORROBORATED** layout, three lineages — but login screen only.

Nothing else. Prop 37 is an increment for a live level-up event, not initial
state, and no server on disk sends it.

### Open items

- **Does `0x009F {36, agent_id, N}` alone change the displayed level on 38797?**
  One packet, nothing else changed, read both the nameplate and the agent
  record. This is the cheapest experiment in the pass and it converts our
  best-corroborated claim into an OBSERVED one.
- **Does `0x00E9` field 9 do anything here, or is OpenTyria right to zero it?**
  Send `0x009F` with level 1 and `0x00E9` with level 20, then the reverse, and
  see which the UI follows. This is the one genuine contest in the section.
- **What are the correct two bytes of `0x0037` for a level-20 character —
  (170,170), (170,0) or (0,170)?** Nothing on disk answers it; all three
  lineages disagree on both the names and the values. Send combinations and
  watch how many points the attribute panel offers.
- **Does the client accept a level above 20 via prop 36?** The settings blob
  caps at 31 (5 bits), the packet field is a full `uint32`, GWToolboxpp's
  fallback label clamps its glyph to 20, and Py4GW's post-cap rule implies 23+.
  Nothing reconciles those four.

---

## 2. Armor: inventory versus what is worn

Our server sends `ITEM_STREAM_CREATE` 0x0144 `[1, 0]`, `SET_ACTIVE_WEAPON_SET` 0x0148, four
empty `WEAPON_SET` 0x0147 and `UPDATE_GOLD_STORAGE` 0x0141 (`authsrv.py:691-699`). No item
exists, no bag exists, and the character is naked. The comment already there — *"Skipped:
inventory"* — is the whole gap.

The finding that organises this section: **placing an item in a bag and putting it on a
body are two different messages, and only one of them is disputed.** Everything from the
item's bytes through its bag slot is settled across four to six independent lineages. The
single unsettled thing is the order of nine dwords inside one message.

**A standing caveat for every claim below.** `schema/messages.json` is imported from
OpenTyria's `msgdefs.c` (`toolkit/schema/import_msgdefs.py`). Where it "agrees" with
OpenTyria it is agreeing with itself, and this track's first pass repeatedly counted it as
a second witness. It is not one. The independent width check for build-era numbering is
`gw-preservation__network-log-explorer/src/lib/Constants.ts`, whose `FieldsGS_StoC_38771`
table (line 1148+, 673 opcodes) is a client-binary extraction. Its *name* table
(`Constants.ts:147-380`) is verbatim ldufr naming and is not independent.

### What is actually in OpenTyria's default-armour table

`GmDefaultArmors.c` is a hand-written table of complete `GmItem` literals — not a
generator, not a database import. UPSTREAM throughout.

| Element | Value | Where |
|---|---|---|
| `GmItem` arrays | **32**, not 38 | `grep -c "^GmItem g_Def"` = 32; 6+8+8+10 = 32 |
| Dispatch slices | Prophecies PvE 6 professions, Factions PvE 8, Nightfall PvE 8, PvP 10 | `GmDefaultArmors.c:562, :1195, :1830, :2816` |
| Prophecies items | 36 = exactly 6 per profession (5 armour + 1 weapon; the warrior's is `ItemType_Hammer`) | per-array counts at `:3-94, :96-187, :189-281, :283-374, :376-467, :469-560` |
| Uniformity | **none** — Factions warrior has 5 (`:571-647`), Nightfall warrior 5 (`:1206-1282`), PvP warrior 7 (`:1841-1947`) | verified per array |
| Per-sex data | **absent** | `GmItem` (`GmItem.h:134-157`) has no sex field; all four slices key on `Profession` only; `GmChar.h:10-12` defines `Sex_Male`/`Sex_Female` and nothing in the item path reads it |
| Per-level data | absent | no level field anywhere in `GmItem` |

Each entry carries `file_id`, `item_type`, `dye_tint`, `dye_colors`, `materials`, `unk1`,
`flags`, `value`, `model_id`, `quantity`, `profession`, a `{count, words[]}` encoded name
and a `{count, words[]}` modifier list. The Prophecies warrior chest, first entry in the
file (`GmDefaultArmors.c:4-18`):

    .file_id = 0x8000005B, .item_type = ItemType_Body, .dye_tint = 19,
    .dye_colors = DyeColor_Gray, .flags = 0x20001006, .model_id = 823,
    .quantity = 1, .profession = Profession_Warrior,
    .name = {4, {0x22A3, 0xFB75, 0xA867, 0x466D}},
    .modifiers = {3, {0xA3C81900, 0x80400000, 0xA0F81400}},

Names are pre-encoded GW string ids, not text. The five Prophecies warrior pieces are
`file_id` 0x5B/0x5E/0x5A/0x5C/0x5D and `model_id` 823/2440/355/1598/6136 in
Body/Legs/Boots/Gloves/Head order — **CORROBORATED across three lineages** (ldufr
`GmDefaultArmors.c:5-16`; gw-preservation `item/item.go:239-243`, with the encoded name
`"22a3 fb75 a867 466d"` matching word for word; GWCA via GWToolbox's armory,
`ArmoryWindow_Constants.h:94-98`, same five ids at 0x05A-0x05E and the same `dye_tint` 19).

**A claim this track first published and the verifier refuted: there is no clean
"campaign signature" in the field values.** The cited Nightfall example was actually a
Dervish *PvP* entry (`:2739-2753`, inside `g_DefDervishPvpEquipments` at `:2723-2814`).
Corrected: Nightfall PvE names are **5 words** beginning 0x8101 with flags 0x20001406
(38×) and 0x20001602 (2×); the 2-word / 0x30001506 pairing is PvP-only. And Prophecies'
0x20001006 is not distinctive at all — Factions PvE uses the same value 39 times.

Two source-quality signals, not wire facts. `GmDefaultArmors.h` declares **44** arrays
including 24 campaign-qualified PvP names the `.c` never defines, spells "Profecies"
throughout while the `.c` spells "Prophecies", and carries a duplicated `#pragma once` at
`:1` and `:3`. And `GetDefaultEquipments` has exactly one call site in the tree —
`GameSrv.c:1641`, inside `GameSrv_HandleCharCreationChangeProf`. Nothing re-derives armour
at login; it is materialised once, at character creation, and persisted.

**Trap if we ever port that loop.** `GmBag_TryAddToBag` (`GmInventory.c:57-66`) writes into
slots where `bag->items[idx] != 0` — it overwrites occupied slots rather than finding a
free one — and the caller's `else if (!GmBag_TryAddToBag(...))` logs success on failure.

### Two different questions: where the item is, and what the agent wears

`GameSrv_SendBagItems` (`GmInventory.c:121-152`) is the inventory primitive: per occupied
slot it sends `CREATE_NAMED_ITEM`, then `ITEM_SET_PROFESSION` if the item is bound, then
`ITEM_MOVED_TO_LOCATION`. `GameSrv_SendInventory` (`:157-186`) wraps it, walking all 22 bag
slots (`BagModelId_Count = 22`) and emitting each bag's container item and
`INVENTORY_CREATE_BAG` first.

| Opcode | Name | Size | What it does | Label |
|---|---|---|---|---|
| 353 / 0x0161 | `CREATE_NAMED_ITEM` | 425 | Declares the item's bytes. Nothing is placed, nothing is visible. | **CORROBORATED** — ldufr (`GameMsg.h:236-253`), GWLP-R (`P343_ItemGeneral.java:18-30`), gw-preservation (`StoC.go:409-424`), GWCA (`GregLando113__GWCA/.../Packets/StoC.h:731-747`), Fournux (`doc/ITEM_EXTRACTION.md:19-38`), explorer 38771 field table |
| 354 / 0x0162 | `ITEM_REUSE_ID` | 425 | **Same layout, re-issued against an `item_id` the client has already seen.** | **CORROBORATED** — Fournux `doc/ITEM_EXTRACTION.md:19-21` ("item general information with a reused `item_id`") + GWCA `StoC.h:972-991` `struct ItemGeneral_ReuseID : ItemGeneral_FirstID {}` |
| 351 / 0x015F | `CREATE_UNNAMED_ITEM` | 25 | The 353 prefix with the name/modifier/model/quantity tail cut off. Used **only** for other players' items (`GmItem.c:96-112` → `BroadcastPlayerEquippedItems`). | **CORROBORATED** — ldufr, GWLP-R, explorer |
| 319 / 0x013F | `INVENTORY_CREATE_BAG` | 13 | Declares the container. | **CORROBORATED** — ldufr `GameMsg.h:131-139`, gw-preservation `itemmgr.go:94-97` |
| 318 / 0x013E | `ITEM_MOVED_TO_LOCATION` | 11 | Puts item into `bag_id`, `slot`. | **CORROBORATED** — ldufr `GmInventory.c:145-152`, gw-preservation `itemmgr.go:138` |
| 346 / 0x015A | `ITEM_SET_PROFESSION` | 7 | `item_id` + profession byte (Warrior = 1). | **CORROBORATED** — ldufr, GWLP-R `P336` |
| 110 / 0x006E | `UPDATE_AGENT_VISUAL_EQUIPMENT` | 42 | `agent_id` + **nine** item ids. The message that makes armour appear on a body. | shape **CORROBORATED** — ldufr, GWLP-R `P098`, gw-preservation, explorer 38771 |
| 111 / 0x006F | (unnamed upstream) | 14 | `agent_id` + slot + item_id — per-slot variant. | **CORROBORATED** — GWLP-R `P099`, gw-preservation `StoC.go:99-104`, explorer 38771 |

**None of 353/319/318 renders anything.** That distinction is the point of this section.

The equipped bag is `bag_model_id` 21, `bag_type` 2, 9 slots, in the order Weapon 0,
OffHand 1, Body 2, Legs 3, Head 4, Boots 5, Gloves 6, CostumeBody 7, CostumeHead 8. That
is **two** lineages, not the three this track first claimed: ldufr (`GmInventory.h:117-129`,
plus `ldufr__Headquarter/include/client/object/bag.h:29-39`, same lineage) and
gw-preservation (`item/item.go:139-152`). The GWCA citation offered as a third was
`Bag *equipped_items;` (`GregLando113__GWCA/.../GameEntities/Item.h:163`) — a pointer that
says nothing about ordering. GWCA's array that *does* carry an order is `NPCEquipment` in
`Agent.h`, which is the **agent's** equipment, not the bag. Conflating those two is exactly
the error the open question turns on, and this track committed it while citing it.

**Opcode mapping, stated plainly and contested.** Our reading: 0x006D = 109
`NPC_UPDATE_WEAPONS` (agent + lead hand + off hand), 0x006E = 110
`UPDATE_AGENT_VISUAL_EQUIPMENT` (agent + 9 dwords), 0x006F = 111 per-slot (agent + slot +
item). Support: OpenTyria `opcodes.h:217-218`; GWLP-R `P097` (agentID/leadhand/offhand) vs
`P099` (agentID/slot/item); the explorer's 38771 field table giving `0x006f` = agentid + 2
dwords. **A sibling track's verify pass disagreed with this mapping**; the arbitration went
our way on evidence weight, not on proof. The per-slot probe below is aimed at 111 and it
settles both this and the slot order at once — if 111 does nothing, the mapping is wrong.

**Where every source is silent: which of the nine positions in message 110 is which, for
build 38797.** CONTESTED, and it is the one thing that decides whether the armour looks
right rather than merely exists.

- **Permuted** (Boots 3, Legs 4, Gloves 5, Head 6): GWLP-R alone, by field name —
  `P098_UpdateFullAgentEquipment.java:18-27` and `GWLP-R-Utils/Templates/PacketTemplates.xml:1485-1538`.
- **Bag order** (Legs 3, Head 4, Boots 5, Gloves 6): OpenTyria's builder — `GmAgent.c:210-218`
  assigns bag index *i* into wire position *i* in all nine cases, its struct field *names*
  notwithstanding (`GameMsg.h:509-517` names them in GWLP-R's order; the names are
  decoration, the bytes are bag order) — and GWCA's `NPCEquipment items[9]`
  (`gwdevhub__GWToolboxpp/Dependencies/GWCA/include/GWCA/GameEntities/Agent.h:60-68`).
- **Not a witness: gw-preservation.** Its nine-dword marshaller (`StoC_gen.go:92-105`)
  writes nine literal zeros — it is a reset. Its `EquipVisualSlot` enum (`item/item.go:154-165`)
  only ever feeds the *per-slot* message (`player.go:121, :196, :335`). It testifies about
  111's slot argument and about message 110 not at all.

So: **1 lineage permuted, 2 bag order**, and the two permuted-adjacent readings do not even
agree with each other on the hands (GWLP-R has leadhand at 0; gw-preservation has
RightHand 1 / LeftHand 0). NOT FOUND for 38797 specifically, after sweeping fifteen mirrors.

> **RUN 2026-08-17, and the question DISSOLVES for pixels** (harness `20260817T150232`,
> probe `armor_slots`; full record `studies/unitsetup/FINDINGS.md` §8 Q6). The per-slot
> probe this section asked for happened: `0x006F` **wears** — the mapping above is
> vindicated against the sibling track's doubt — but the same LEGS piece rendered on the
> legs from position 3 and from position 5, with a nine-zero `0x006E` reset proven clean
> in between. **The item drives its own placement; the position does not choose the body
> part**, so bag order vs permutation cannot be told apart by looking, and the array arm
> (legs@3 + boots@5) drawing both correctly confirms only that bag order WORKS, not that
> it is what 38797 believes. The contest stands, demoted to protocol bookkeeping that no
> screenshot will ever settle; the routes that could are a memory read of the equipped
> bag or a behavior keyed to position (costume slots 7/8 are the candidates).

> **SETTLED THE SAME DAY, BY RETAIL'S OWN WIRE — and the ONE lineage beat the TWO.**
> The note above listed the routes that could decide this and missed the one that did:
> ArenaNet sending the message itself. The Shing Jea capture
> (`vault/captures/live/20260817T183756`) carries seven `0x006F` per-slot writes for one
> player, agent 356, each immediately preceded by the `0x015E` that declares its item —
> so the item TYPE is on the wire beside the slot number, and the mapping is read rather
> than inferred (OBSERVED; reproduced first-party by the orchestrator after the decode
> pass proposed it):
>
> | slot | item id | declared item type |
> |---|---|---|
> | 2 | 5059, 5472 | 7 = Body |
> | 3 | 3680 | 4 = **Boots** |
> | 4 | 3787 | 19 = **Legs** |
> | 5 | 4729 | 13 = **Gloves** |
> | 6 | 3263 | 16 = **Head** |
>
> The bulk message for the same agent closes it: `0x006E [356, 0,0, 5059, 3680, 3787,
> 4729, 3263, 0,0]` — the nine-dword array uses the SAME numbering, so `0x006E` and
> `0x006F` index one array and the per-slot form is the readable window onto it. Thirty
> other players in the same town show the identical `0,0,X,X,X,X,X,0,0` shape.
>
> **That is GWLP-R's PERMUTED reading exactly (Boots 3, Legs 4, Gloves 5, Head 6), and it
> REFUTES bag order (Legs 3, Head 4, Boots 5, Gloves 6).** The section above counted "2
> lineages against 1" and leaned on the majority; the majority is wrong. ldufr's builder
> assigns bag index *i* into wire position *i* and GWCA's array is named in the same
> order, so the two agree because they make the same assumption — which is one witness
> counted twice, the exact defect this repo names for `schema/messages.json` and
> OpenTyria. **Counting lineages is not counting witnesses.**
>
> Consequence for us: the `0x006E` position comments in `toolkit/authsrv/authsrv.py` say
> "position order is bag order, which is 2 lineages against 1" and are now wrong in their
> reasoning though harmless in effect — we send zeros in 1..8 and only position 0 (the
> weapon) is exercised, which both readings agree on. Anything that dresses a body must
> use the measured order above. Full record: [../newopcodes/FINDINGS.md](../newopcodes/FINDINGS.md) `0x006F`.

### How the client knows what an item looks like

**Appearance comes from `file_id`, which the client calls `model_file_id` — never from
`model_id`.** CORROBORATED across GWCA (`Item.h:50-56` `ItemData`; the wire struct at
`Packets/StoC.h:731-747` names the field `model_file_id` directly), Fournux
(`doc/ITEM_EXTRACTION.md:17`, "DAT resource key for the item's visual resource") and GWLP-R
(`PacketTemplates.xml:4656-4661`, "Can also be armor ID if the armor flag is set"). The
client resolves it through an 11-entry `CompositeModelInfo` table (`Item.h:208-211`) which
picks the mesh itself; GWToolbox's armory writes a raw `model_file_id` into `ItemData` and
the character redraws (`ArmoryWindow.cpp:119`).

Three consequences, all now settled:

- **The 0x80000000 high bit is a non-issue.** Fournux `doc/ITEM_EXTRACTION.md:17` and `:26`
  give `model_file_id = raw & 0x7fffffff` in an explicit offset table for 0x0161 — the
  client masks the top bit off. OpenTyria's `0x8000005B` and gw-preservation's / GWToolbox's
  `0x5B` are the same resource; so are the two backpack encodings (0x8001B536 vs 0x1b536).
  This track had this filed CONTESTED with an A/B probe planned. **That probe is cancelled.**
- **Gender is resolved client-side**, which is why the table has no per-sex data.
  **CORROBORATED across two lineages**: Py4GW (`Py4GWCoreLib/Item.py:146-165`) and GWCA via
  GWToolbox (`GWToolboxdll/Modules/Resources.cpp:1370-1379`, `slots_to_try[] = {10u, is_female ? 5u : 0u}`,
  naming the client function it mirrors, `CICompositePlayer::GetCompositeGeometry`). Slot 10
  is a shared geometry slot tried first; 5 female, 0 male.
- **The composite lookup is gated on `interaction & 4`** — the same bit OpenTyria sets in
  `0x20001006` and gw-preservation computes as `flags |= 1 << 2` (`item/item.go:364-369`).
  GWToolbox reads it to decide an item has an armour model at all (`Resources.cpp:1374`).

`model_id` is the item's **catalogue identifier**, corroborated as a *meaning* by Fournux
(`ITEM_EXTRACTION.md:16`, "gameplay identity... not a DAT file number") and GWLP-R (names
the field `ItemID`). **Downgraded from what this track first published:** the headline
evidence was "OpenTyria's 823 *is* gw-preservation's `ItemRingmailHauberk = 823`". That is
two *data tables* agreeing, not two wire implementations — gw-preservation's own marshaller
passes the runtime **local id** into that wire position (`itemmgr.go:124-137`), never 823.
Only its hardcoded backpack path (`itemmgr.go:79-92`) puts a catalogue number there.

### The corrected minimal sequence to dress our warrior

Not CORROBORATED as a whole. Per step:

| # | Message | Payload | Label |
|---|---|---|---|
| 1 | 324 `ITEM_STREAM_CREATE` | `[1, 0]` | **CORROBORATED** (ldufr, GWLP-R, explorer). Already sent, `authsrv.py:691`. |
| 2 | 319 `INVENTORY_CREATE_BAG` | `[1, bag_type=2, bag_model_id=21, bag_id=N, slot_count=9, assoc_item_id=0]` | **CORROBORATED** (ldufr, gw-preservation) for the *shape and values*. That it must precede step 5 is **UNVERIFIED** — it is upstream's emission order, not a stated requirement. |
| 3 | 353 `CREATE_NAMED_ITEM` ×5 | `file_id`/`item_type`/`dye_tint`/`dye_colors`/`flags`/`model_id`/`quantity`/name from `GmDefaultArmors.c:3-94`; **send 0x8000005B as-is** | **CORROBORATED** across 6 witnesses for the field layout; the *values* are **UPSTREAM** (OpenTyria's table, agreeing with gw-preservation's and GWToolbox's). |
| 4 | 346 `ITEM_SET_PROFESSION` | `[item_id, 1]` | **CORROBORATED** (ldufr, GWLP-R). Our server already sends `AGENT_PROFESSIONS` (0x00B7) Warrior=1, so this should be consistent. |
| 5 | 318 `ITEM_MOVED_TO_LOCATION` ×5 | `[1, item_id, bag_id, slot]`, slot = Body 2, Legs 3, Head 4, Boots 5, Gloves 6 | **CORROBORATED** (ldufr, gw-preservation) — **two** lineages on the slot order, not three. |
| 6 | 110 `UPDATE_AGENT_VISUAL_EQUIPMENT` | `[agent_id, 9 item ids]` | shape **CORROBORATED** (4 witnesses); **the order of positions 3-6 is CONTESTED**, 1 lineage against 2, with gw-preservation abstaining. |

Insertion points are already identified and map cleanly onto upstream: steps 1-5 into the
`REQUEST_ITEMS` block at `authsrv.py:688-699`, step 6 into the `REQUEST_PLAYERS` block
between `WORLD_CREATE_AGENT` (`authsrv.py:877`) and `WORLD_UPDATE_CONTROLLED_AGENT`
(`:914`) — which is exactly where `GameSrv.c:1485` sits, after the effects block and before
`SendUpdateControlledAgent` at `:1487`. Note upstream sends inventory *before* the weapon
slots; we currently send `SET_ACTIVE_WEAPON_SET` and four `WEAPON_SET` with nothing between.

### The modifier words: NOT DONE

**DECODED 2026-08-20 -- see [studies/itemmods/FINDINGS.md](../itemmods/FINDINGS.md).**
The format is `{identifier: bits 29-20, arg: bits 17-8, arg2: bits 7-0}`, read out of
the client's own parser and checked against all 5,266 modifier words in the live
corpus (100% dispatch to identifiers the client handles). Armour rating is identifier
**572**'s argument; the `+N vs. damage type` line is **527**. The sentence below stood
for two weeks and is kept as written.

**Nobody on this pass decoded a single item modifier word, and this is the largest
remaining hole in the armour picture.** `GmDefaultArmors` ships literal lists —
`{0xA3C81900, 0x80400000, 0xA0F81400}` for the warrior chest, `{0x24481400}` for the
backpack — and `CREATE_NAMED_ITEM` reserves 64 dwords for them. **Armour rating lives in
those words.** Sending an empty modifier list produces armour that renders and protects
nothing, which is a legitimate first milestone but is not the finished job.

#### THE RATING IS ON SCREEN, 2026-08-20 — and the job was two jobs

The paragraph above is kept as written because both halves of it were right, and
because the second half is why the first one stayed open for a fortnight. The words
were opaque *and* **this server was not sending the armour at all**: the character
stood in every capture bare-chested with five empty slots on the paper doll, so the
experiment this section proposed — *"read the rating out of the client's own item
tooltip"* — had nothing to hover. Decoding the words would not have finished it.

Both are fixed. `authsrv.STARTER_ARMOUR` declares the five pieces, places each in the
equipped bag at the slot retail's own `0x006F` writes name, and one `0x006E` with five
nonzero positions dresses the body. Hovering the chest (`20260820T125155`):

```
Ringmail Hauberk
Armor: 25
Armor +20 (vs. physical damage)
```

> **Armour rating is identifier 572's argument, read off ArenaNet's own renderer.**
> OBSERVED. `0xA3C81900` → 572 arg **25** → `Armor: 25`, through string 2438
> `%str1%: %num1%` with 2372 `Armor`. The second line is two words together:
> `0xA0F81400` → 527 arg **20**, and `0x80400000` → identifier **4**, whose only
> string is 2480 `vs. physical damage`. The leggings read the same, so it is per item
> and not a panel total.

**The character is dressed, which was the milestone this section wanted.** Predictions
were written first and all three held: the body renders wearing the set, the tooltip
carries the rating, and five nonzero `0x006E` positions did not trip an assert. The
item NAMES resolve too — `Ringmail Hauberk`, `Ringmail Leggings` — so
`GmDefaultArmors`' encoded-name dwords are good.

**AND THESE FIVE ROWS ARE NO LONGER UPSTREAM.** `content/items.toml` said of them:
*"one lineage's hand-written table, no capture of ours carries these bytes."* That is
refutable and our own vault refutes it. ArenaNet's server sent us `0x0161` declarations
for **all five of these exact model ids** — 823, 2440, 355, 1598, 6136 — **nine
sightings each across three captures**, and every fixed field agrees: `file_id`,
`item_type`, `dye_tint`, `materials`, `unk1`, `flags`, `value`, `model_id`, `quantity`,
**and all three modifier words**. The one field that differs is `dye_colors`, which is
*meant* to: it is what a player dyed that instance, and retail shows four values for one
model with ours among them. The rows move to CORROBORATED against a first-party capture
— which is a stronger witness than a second lineage, and it was luck rather than design
that the vault's character wore the same starter set. `test_armour.py` §3 replays it.

**What this does NOT show.** That the client *renders* a rating is not that anything
*applies* it: nothing in this server reduces incoming damage by armour, and the tooltip
is a display surface exactly as `studies/pvpui` §34.6's attribute panel is. Armour as a
damage term is `studies/combat`'s, unstarted.

Two specific things this pass should have done and did not: **GWCA's `ItemModifier` struct
was never quoted**, and **Py4GW's item modules and its `PacketSniffer.py` item entries were
never surveyed** — Py4GW was only ever opened for `Item.py`'s composite-model helper. Both
are on disk. Neither was read.

What *is* settled about the field: the **count precedes the array**. Fournux
(`ITEM_EXTRACTION.md:36-38`) puts the modifier count at `+0xb0` and the words at `+0xb4`,
matching OpenTyria's `uint32_t n_modifiers; uint32_t modifiers[64];` (`GameMsg.h:251-252`),
with a total size of `0xb4 + count * 4` up to `0x1b4`. GWLP-R's 2-byte `prefixLength`
(`PacketTemplates.xml:4727-4729`) is the outlier. The schema's trailing-dword field listing
is an import artifact, not a wire ordering.

### Open items

| Question | What would answer it |
|---|---|
| Which slot ordering does build 38797 use inside message 110? | **The one probe worth running.** Send message **111** per-slot — chest first (index 2, agreed by everyone) to prove the pipeline, then the legs piece alone and look at whether it lands on legs or feet. 111 is also where gw-preservation's `EquipVisualSlot` is a *sourced* prediction, so a wrong answer there falsifies something specific. If 111 does nothing at all, our 0x006D/0x006E/0x006F mapping is wrong and that is the real finding. |
| ~~What does a modifier word encode, and where is armour rating?~~ **ANSWERED 2026-08-20** | The format is decoded from the client's own parser ([studies/itemmods](../itemmods/FINDINGS.md)) and **armour rating is identifier 572's argument**, read off the tooltip on a caged client exactly as this row proposed: `Armor: 25`. The row said to read GWCA's `ItemModifier` struct and Py4GW's item modules first; neither was needed and neither was opened — the client's own dispatch table was the shorter route and the better witness. |
| Does the client require `INVENTORY_CREATE_BAG` before `ITEM_MOVED_TO_LOCATION`, or is message 110 alone enough to render? | Untested and unstated by any source — upstream and gw-preservation both happen to emit the bag first. Try 353 + 110 with no bag, then add 319 and 318, and see which is the minimum that draws. |
| What are flag bits 0x1000 and 0x2 in `0x20001006`? | Unknown in every source. gw-preservation *computes* only `0x20000004` for the same armour class, yet hardcodes OpenTyria's exact anomalous values as name-keyed exceptions (`item/item.go:370-375`: `0x20001202` for Third Eye, `0x22001000` for Starter Truncheon, both verbatim in `GmDefaultArmors.c`). That is strong evidence the two share an upstream data extraction — and no evidence at all about what the bits mean. |

---

## 3. Character creation end to end

**Creation never touches the auth channel.** The auth server's entire role is
routing: it takes a `REQUEST_GAME_INSTANCE`, decides this is a creation
instance, and hands the client a game server address exactly as it would for a
map load. Everything that actually builds a character happens on the game
channel, after the normal version/DH/ARC4 handshake.

- **UPSTREAM.** OpenTyria's auth dispatch (`OpenTyria AuthSrv.c:1341-1394`) has
  handlers for login, status, change-play-character, request-game-instance,
  heartbeat, disconnect, EULA, access key, computer info/hash, delete-character
  and update-character-settings — and nothing that creates anything. It does not
  even handle `AUTH_CMSG_ACCOUNT_CREATE` (0x0003).
- **CORROBORATED (ldufr + gw-preservation).** gw-preservation reaches the same
  arrangement independently in Go: its auth service only tags the instance
  (`gw-preservation authservice/handlers.go:297-299`) and all creation handlers
  live in its game service.
- Our own `AUTH_CMSG` name table (`toolkit/authsrv/authsrv.py:273-283`) is a
  verbatim subset of OpenTyria's `opcodes.h`. It is not a second witness to any
  of this, and is not cited as one below.

A standing caveat for every size in this section: **`schema/messages.json` is
imported from OpenTyria's `msgdefs.c`** and is therefore ldufr, never
corroboration. The declared arbiter is `schema/overrides.json`, whose own header
says every entry in it *contradicts* the imported tables; today it overrides
exactly one message (`GAME_CMSG` 144, 19 bytes not 18). Any argument that
reconciles an outside table against an un-overridden imported size is worth
nothing until the same measurement is made from a capture.

### The ordered flow

**Auth channel**

1. Client sends `AUTH_CMSG_REQUEST_GAME_INSTANCE` (0x0029) — header plus six
   dwords: `req_id, map_type, map_id, region, district, language`.
   **CORROBORATED** (`OpenTyria AuthMsg.h:65-73`; `gw-preservation
   authservice/CtoS.go:13-21`, whose `mapId` sits in the same slot), and
   **OBSERVED** — we already parse exactly this at `authsrv.py:366`.
2. Which field means "creation" is **CONTESTED**, and probably a false
   dichotomy. ldufr keys on `map_type == 11` (`OpenTyria GmMap.h:29`,
   `GameSrv.c:1242-1246`; the client side of the same lineage comments
   `// 11 = character creation` at `Headquarter code/client/auth.c:282`).
   GWLP-R and gw-preservation both key on `map_id == 0`
   (`GWLP-R WorldBean.java:35`; `gw-preservation authservice/handlers.go:297`).
   These are different fields of the same message, and
   `sgwlpr db/.../MapData.scala:734` — `MapInfo(730, 0, 0, "CharCreation")` —
   **reconciles them**: the creation scene has map id 730 with gameId 0 and
   fileId 0. A client that sends map_type 11 *and* map_id 0 satisfies both
   tests. Correspondingly, "creation is not a map" is too strong: it has an id
   and a name in one source, and no map *file* in any.
3. Server replies `AUTH_SMSG_GAME_SERVER_INFO` (0x0009) then
   `REQUEST_RESPONSE(0)` (0x0003). **OBSERVED** — already implemented and
   working (`authsrv.py:366-386`), though it ignores `map_type` entirely today.

**Game channel**

4. Server volunteers `INSTANCE_LOAD_HEAD` (0x017C) then `CHAR_CREATION_START`
   (0x0189), unprompted. This, not anything on auth, is what puts the client in
   creation mode. **CORROBORATED** (`OpenTyria GameSrv.c:1244-1245`;
   `gw-preservation gameservice/handlers.go:455-457`).
5. `CHAR_CREATION_START` is a bare header, no payload. **UPSTREAM +
   gw-preservation** (`OpenTyria GameSrv.c:222-226` sends only
   `sizeof(header)`; `gw-preservation StoC_gen.go:65-68`). Two witnesses, not
   three — our schema is ldufr.
6. Client sends `CHAR_CREATION_REQUEST_PLAYER` (0x0089), empty. Server answers
   with a bracketed block: `INSTANCE_PLAYER_DATA_START` (0x0186), item stream,
   inventory, weapon sets, gold, factions, skills+attributes, health+energy,
   then `INSTANCE_PLAYER_DATA_DONE` (0x018A). **CORROBORATED**
   (`OpenTyria GameSrv.c:1542-1552`; `gw-preservation player.go:382-395`).
   A live player agent already exists in the scene at this point — three
   lineages agree (`GameSrv.c:1236-1237` creates it *before* the map-type
   switch; `GWLP-R CharacterCreation.java:72-73`; `gw-preservation
   player.go:391-392`).
7. Client sends `CHAR_CREATION_REQUEST_ARMORS` (0x008A), empty. **CONTESTED
   content**: ldufr answers with account-wide unlock state and no armour at all
   (`GameSrv.c:1570-1573` — PvP skills, PvP heroes, PvP items, account
   features); gw-preservation answers the same wire position with default
   warrior equipment (`gameservice/handlers.go:216-226`). The name is a red
   herring either way.
8. Client sends `CHAR_CREATION_CHANGE_PROF` (0x0060) on every campaign or
   profession change: header + `campaign` u8 + `profession` u8, campaign first,
   4 bytes total. **CORROBORATED on order and semantics** (`OpenTyria
   GameMsg.h:84-88`; `GWLP-R P088:15-16` — but GWLP-R declares both as Java
   `short` and its own header is 88 decimal, so it corroborates order, not
   width and not the opcode). Server response is **UPSTREAM only**: free the
   equipped bag, look up default equipment for (campaign, profession), then send
   unlocked skills, profession, and bag contents (`GameSrv.c:1641-1643`,
   `:1677-1679`).
9. Client sends `CHAR_CREATION_CONFIRM` (0x008B): `string16(20)` name +
   8 opaque bytes + dword flags. **CORROBORATED** (`OpenTyria GameMsg.h:96-102`;
   `GWLP-R P132:17-19`), and — importantly — confirmed by an actual client dump:
   `network-log-explorer Constants.ts` `FieldsGS_CtoS_38771[0x008b]` is
   `[0x1417, 0x0805, 0x0404]`, i.e. String16(20), 8 fixed bytes, Uint32, from
   build 38771. That same table lists `0x0089` and `0x008a` as empty arrays,
   which is genuine client-side confirmation that both are bare headers.
10. Server replies `CHAR_CREATION_SUCCESS` (0x0188) or `CHAR_CREATION_ERROR`
    (0x018B, one dword). **CORROBORATED** on shapes (`OpenTyria
    GameMsg.h:293-301`; `gw-preservation StoC.go:55-59`; `sgwlpr
    codegen/PacketTemplates.xml` header 378).
11. Server drops the player — the creation connection is one-shot
    (`GameSrv.c:1798-1801`). **UPSTREAM.**
12. Client returns to select. Whether it needs a fresh roster is **open**; see
    below.

**Opcode numbering for this cluster is UPSTREAM, not corroborated.** CMSG
0x0060/0x0089/0x008A/0x008B and SMSG 0x0188/0x0189/0x018B come from
`OpenTyria opcodes.h:104, :121-124, :343-346`, echoed by `Headquarter
code/client/opcodes.h` (same lineage), by our schema (imported from the same
file), and by Py4GW's table, which matches ldufr everywhere and may be derived
from it. The numbers are almost certainly right for 38797 — the 38771 client
field dump above independently fixes the *shapes* at those numbers, and our own
server already uses 0x018A as `PLAYER_DATA_DONE` against the real client — but
the label is UPSTREAM. gw-preservation and legacy Py4GW number the whole cluster
one lower; that is a systematically older build, not a competing reading.

**A convention nobody has verified.** Every `declared_unpack_size` argument in
this section (0x008B = 58, 0x0188 = 1092, `CHARACTER_INFO` = 138) assumes u32
length prefixes on `string16`/`array8`, because that is what OpenTyria's C
structs declare. Our own codec writes **u16** on the wire and the client accepts
it, and `sgwlpr` template 132 declares `prefixType int16` for the very same
confirm-message name field. The two conventions differ by two bytes per string
and nothing on disk settles which the client's deserializer wants. Flagging it
once here: a port that copies OpenTyria's struct literally will be wrong.

### Where 0x008A fits

**OBSERVED, and it contradicts the name.** `CHAR_CREATION_REQUEST_ARMORS` is not
creation-scoped on our build. Build 38797 sends it 45 times across the whole
capture vault during *ordinary map loads* — header 0x808A, empty payload — and
it is the **first** content request the client makes on the game channel, ahead
of 0x0088 and 0x0090. Sequence in one session: 0x000A, 0x000B, **0x008A**,
0x0091, 0x000D, 0x0088, 0x0090, 0x0092, 0x008A again. Opcodes 0x0089 and 0x008B
appear **zero** times, consistent with creation never being entered. Answering
0x008A with OpenTyria's unlock burst is what got us past a stall
(`authsrv.py:204-206`, `:224-228`, `:835-839`). So this opcode is already load
bearing for us outside creation, and any creation work must not repurpose it.

### Name validation, and the contested error code

**CORROBORATED (three lineages): there is no name-check round trip.** Validation
is a side effect of the insert. OpenTyria attempts `Db_CreateCharacter` against
a unique index (`GameSrv.c:1767-1778`, `db/seed.sql:105`), gw-preservation maps
`ErrCharacterNameTaken`, GWLP-R does a `findByName` first. Searches across ten
mirrors for a name-availability message found nothing; Py4GW's four
`Character_Name_Check1..4` frames are UI widgets with no packet attached.

**CONTESTED — and the conflict is inside ldufr.** The commonly cited value is
**29** (`OpenTyria GmErrors.h:9`; `GWLP-R ErrorCode.java:20`;
`gw-preservation handlers.go:189-190`). But ldufr's own *client* error-string
table has **no case 29 at all**: `Headquarter code/client/error.c` maps **39** to
"The character name `<text>` is already in use by another player", **31** to
forbidden words, and **41** to "You have attempted to create too many characters
recently" — a creation failure mode absent from every other source. Since the
error code exists only to select a client string, the client-side table is the
one that decides what a user sees. Do not implement 29 as settled. (GWLP-R's own
`CCInvalidName` constant is written `031` in Java, which is octal 25 — its
author hit the trap and left it.)

### What finally writes the character, and what the roster must then say

**UPSTREAM.** On confirm, OpenTyria fills a DB record from the appearance bits
plus the campaign/profession it remembered from `CHANGE_PROF`: level 1, helm
shown, a starting outpost, `is_pvp = (campaign == None)`,
`unlocked_professions = 1 << primary_profession`, then copies equipped armour
file ids and dye colours in (`GameSrv.c:1708-1722`, `:1738-1741`). Secondary
profession is never set at creation in any source.

Only the **first 4** of the 8 config bytes are read — the appearance dword
(**CORROBORATED**: `GameSrv.c:1700-1701` memcpy's 4; `gw-preservation
CtoS.go:11-15` names the second dword literally `ignore`). Its bit layout is the
best-evidenced thing in this whole track, **CORROBORATED across three
lineages**: sex:1@0, height:4@1, skin:5@5, hair_color:5@10, face:5@15,
primary_profession:4@20, hair_style:6@24, 2 bits@30 (ldufr calls the top field
`race`, the other two call it `campaign`, and ldufr's own comment
"0=prof, 1=faction, 2=nightfall" describes campaigns). Do not copy GWLP-R's
*writer* — it drops hair colour entirely (`CharacterCreationView.java:95-98`).

For the new character to appear at select, `AUTH_SMSG_CHARACTER_INFO` (0x0007)
must carry `req_id`, 16-byte uuid, an unused dword, the name as `string16(20)`,
and a settings blob as `array8` capped at 64. **UPSTREAM + OBSERVED** — one
witness (`OpenTyria msgdefs.c:384-391, :5114`, the client-RVA-extracted layer)
plus the fact that our server ships it and the client accepts it
(`authsrv.py:419-421`). The blob is `CharacterSettings`: 37 bytes with no
armour, +5 per piece, so 62 with a full five-piece set against a 64-byte cap —
two bytes of headroom and no room for a sixth piece. Our hardcoded 37-byte blob
is at `authsrv.py:262-271`.

**The SUCCESS-message settings argument does not survive.** It is often said
that `CHAR_CREATION_SUCCESS` carries the same `CharacterSettings` as
`CHARACTER_INFO`, built by the same helper — the helper name does match. But
`GameSrv.c:1794` passes `&player->character`, **not** the `DbCharacter` local
that lines 1705-1757 just populated from the confirm message. OpenTyria
therefore ships a stale or zeroed blob on this message and works anyway. So the
inference "the client rebuilds its roster entry from SUCCESS, which is why
CHARACTER_INFO is never re-sent" **does not follow** — it is an artefact of a
bug. gw-preservation sends an explicitly empty blob here and also appears to
work. **The roster-refresh question is open.**

The u16 between the name and the blob on 0x0188 is **CONTESTED but leaning**:
OpenTyria writes `0x2211` and comments "what is that?"; gw-preservation calls it
`mapId` and sends 148; `sgwlpr` template 378 independently names the field
`mapId`; GWLP-R sends 81. Two lineages name it a map id, one fills it with
noise, and 148 is exactly the `last_outpost` our own test character carries.

### The 8-byte config hole

**NOT FOUND, and this is the blocker.** Nothing on disk explains bytes 4-7 of
the confirm message's config blob. OpenTyria consumes only the first four;
gw-preservation names its second dword `ignore`; GWLP-R's `P132` treats all
eight as one opaque array; `sgwlpr` template 132 types it as an undifferentiated
`int8 occurs=8`; the 38771 client field table confirms the *size* (8 fixed
bytes) and says nothing about contents. Five sources, no answer. Real creation
means accepting a client-authored blob half of which we cannot interpret — and
the same applies to the trailing `flags` dword, which OpenTyria declares as
`CharModeFlags` (DhuumCovenant=1, ReforgedMode=2) and then never reads.

### What Rurik would minimally need

Today we do not create anything: `handle_request_game_instance` never branches on
`map_type` (`authsrv.py:366-386`), and the roster is one hardcoded character
(`authsrv.py:419-421`, `:260-271`). Every `game_instance_request` in the vault —
44 of them — is `map_type 3, map_id 148`. The minimum is:

1. A character store. Everything else is downstream of not having one.
2. Branch the instance request on `map_type == 11` **or** `map_id == 0` (accept
   either; the sources disagree about which the client sets).
3. A creation bring-up on the game channel: `INSTANCE_LOAD_HEAD` then
   `CHAR_CREATION_START`, instead of the outpost bring-up.
4. Handlers for 0x0089 (reuse our existing player-data bracket) and 0x0060.
   0x008A we already answer.
5. A 0x008B handler: unpack name + 8 bytes + dword, decode the appearance dword,
   persist, then reply 0x0188 or 0x018B and drop the player.
6. A roster path that reflects the new character next time the client asks — the
   safe assumption until measured is that the client re-selects and we must have
   the character ready for `CHARACTER_INFO`.

The UI order the client walks, for anyone scripting a live test: Character
Type → Campaign → Profession → Gender → Appearance → Body → Name. Sourced from
`Py4GW Py4GWCoreLib/routines_src/Yield.py:548-581`, a working live-client
creation routine — note Character Type comes **before** Campaign, which is the
reverse of the intuitive reading of the frame list.

### Open items

| Question | What would answer it |
|---|---|
| Does 38797 signal creation with `map_type == 11`, `map_id == 0`, or both? | One click on "Create Character" against the auth server we already run. `handle_request_game_instance` logs both fields for every request; this costs one session and no code change. It also answers whether the client ever sends 0x0089, which it has never done in 44 captured sessions. |
| What are bytes 4-7 of the confirm config blob? | Nothing on disk. Only a capture of a real confirm — which we can produce ourselves once creation is reachable — will say. Until then any creation implementation is storing four bytes it cannot name. |
| Must the auth server re-send `CHARACTER_INFO` after creation, or does the client build the roster entry itself? | Previously argued from OpenTyria's SUCCESS blob; that argument is void (`GameSrv.c:1794` sends the wrong struct). Test directly: create, then watch whether the client re-queries or renders the new slot from the SUCCESS message alone. Sending an empty blob, as gw-preservation does, is the same experiment from the other side. |
| Is the name-taken error 29 or 39? | Send each and read the string the client renders. `Headquarter error.c` says 39 and has no 29; three server reconstructions say 29. One session settles it, and also tells us whether 31 (forbidden words) and 41 (too many characters recently) exist on our build. |

---

## What is still ours, and what changed grade

Every character-cluster value in `toolkit/authsrv/authsrv.py`, re-graded by
this pass. Line numbers are the worktree snapshot this study read.

| Thing | Where | Was | Now |
|---|---|---|---|
| `APPEARANCE = PROF_WARRIOR << 20` | `:132` | invented | **Layout CORROBORATED** (ldufr, gw-preservation, GWLP-R; GWCA on bit 20). The all-zero rest of the dword is our choice; any value fitting the widths is accepted by every reimplementation, none vouches for the client. |
| `PROF_WARRIOR = 1` | `:131` | assumed | **CORROBORATED**, four lineages, same full enum ordering. |
| 0x00B7 payload `[agent_id, 1, 0, 0]` | `:908-910` | three unsourced bytes | **Named** (primary, secondary, is_pvp — ldufr + GWLP-R names, client-dump shape) and the values match every readable implementation for a PvE Warrior. Third byte's meaning UNVERIFIED — nothing consumes it. |
| Points-before-profession ordering | `:897-907` | our empirical workaround | **OBSERVED (ours) + universal** — every reference server orders it the same way. Mechanism still unexplained. |
| `ATTRIBUTE_COUNT = 42` | `:160` | "GmAttributes.h: Attribute_Count" | **UPSTREAM-only.** The comment is accurate about the source; the source is alone. Whether a 42-zero array is well-formed is OPEN (triplet hypothesis, single lineage). |
| `ATTRIBUTE_POINTS = 50` | `:161` | "from GmPlayer.c:125" | **UPSTREAM, uncited literal.** Two other lineages send 0/0. The two bytes' meaning is CONTESTED (used vs max). |
| The comment "its LENGTH is what tells the client how many attribute slots exist" | `:157-159` | stated as fact | **Supported by no source.** Remove or hedge when next editing. |
| WORLD_CREATE_AGENT payload incl. h-fields | `:877-896` | faithful copy | Still a faithful copy; **widths now client-settled** (38771 template), names mostly NOT FOUND. `h0027` "12.0f" reading is CONTRADICTED — it deserializes as DWORD. |
| `PLAYER_TEAM_TOKEN = 0xBAADF00D` | `:165`, sent at `:865` and `:889` | upstream's eye-catcher, kept verbatim | **Superseded by evidence:** three lineages put `0x706c6179` (`'play'`) there. Recommendation: change it — in BOTH send sites at once, since every lineage keeps the two sites equal. |
| 0x008A reply burst | `:834-852` | "what the client is really asking for" | **Content matches upstream verbatim** (minus the 387 PvP item ADDs). Placement unproven; see next row. |
| The stall-causality comment | `:835-839` | "unanswered request caused the 44s drop" | **Overclaims.** The one unanswered capture is confounded by the manifest-phase bug and zero simulation ticks; four fixes shipped together. Downgrade to "answering it is sufficient; necessity untested". |
| The Py4GW-alignment comment | `:225-228` | "identified from the client's own numbering: Py4GW" | **Circular** — Py4GW's table is OpenTyria's verbatim, and Py4GW also ships the −1 table. Real support: GWLP-R and gw-preservation agreeing on internal order, plus the client dumps. |
| `TEST_CHAR_SETTINGS` `[medium]` marks | `:262-271` | number_of_pieces and trailing dword "medium" | **Upgrade both to corroborated** — gw-preservation and sgwlpr write the same count byte and the same `0xDD`-fill tail. Blob layout corroborated end to end. |
| `CHARACTER_UPDATE_INFO ["", 0, 0, 1000, 0, 0, 0]` | `:700-701` | copied burst member | **RECONSTRUCTION** — six of upstream's seven fields are offset-named. Not a level, not appearance; carries nothing we understand. |
| Character-select "level 1" vs in-map level 0 | `:262-271` | puzzling mismatch | **Explained.** The blob drives only the roster screen; in-map level is agent property 36 on 0x009F, which we never send. |

## The probe queue

All read-only research on these questions is exhausted; only the client can
move the needle now. In value order, from the tracks' independent convergence.
(Per the standing rule: driving our patched client is authorized; nothing ever
points at ArenaNet.)

1. **Level:** send `0x009F {36, agent_id, N}` once after WORLD_CREATE_AGENT and
   read the nameplate. One packet; converts the pass's best-corroborated claim
   into an observation, and answers why the character is level 0.
2. **Attributes:** send 0x003A with count 0, then 3, then 42 — settles the
   triplet hypothesis and gives us a sourced attribute payload. May need a
   skillbar update first (Headquarter's parser bails without one), and a null
   result is inconclusive (one lineage never sends 0x003A at all).
3. **Armor:** one piece at a time through the per-slot visual-equip message
   (our 111) — chest first, then legs alone. Settles the 0x006D/6E/6F mapping
   and the slot order in one session, and dresses the character.
4. **Appearance:** vary the profession nibble while holding 0x00B7 fixed, and
   vice versa. Un-confounds the one thing sections a and b both flag.
5. **Creation:** click Create Character once against the running auth server
   and read `map_type`/`map_id` from the log we already write. Zero code.

## What this pass did not do

Recorded so the next pass doesn't re-discover the gaps the hard way.

- **Nobody decoded an item modifier word.** Armour rating lives there;
  GWCA's `ItemModifier` struct and Py4GW's item modules are on disk and were
  never read. The armour plan ("send an empty modifier list") sidesteps it.
- **No name→index alignment table for the attribute enums** across
  GWCA / Py4GW / GWLP-R-SQL / Headquarter / OpenTyria — the +3 offset is
  established, but a full table would make it unmissable. The client-derived
  ECHARATTRIB table runs past 44 to 50; the size of the id space is open.
- **GWToolbox's level-up / XP-award handlers were never searched** — only its
  XP-bar label. It is the one codebase that reacts to real server traffic.
- **`schema/overrides.json` was found only by the critic.** It is the repo's
  declared arbiter over the imported tables and no track opened it. Nothing
  character-shaped is currently overridden, so no conclusion changes — but the
  method should have started there.
- **The u16-vs-u32 string-prefix convention** (flagged in the one-page answer)
  was never measured against a capture.

## Relation to the movement study

Nothing here contradicts `studies/movement/FINDINGS.md` on movement. Two of its
source-audit rows are refined by this pass: network-log-explorer's *name*
tables are ldufr's (as it said), but its *field* tables are client dumps and
independent — the repo's placement in the ldufr lineage row should be read
per-artifact; and the gw-preservation group is a genuinely separate witness
(sole author "Energy"), not part of any previously known lineage. Its
grading of 288.0 ("two reconstructions agree; neither measured") stands and is
deliberately not upgraded here. Its WORLD_CREATE_AGENT field table gains two
refinements: h001E settled as BYTE by the client template, and h0027's "bit
pattern of 12.0f" reading now contradicted by the same template.

The closing sentence of that document applies here word for word: none of these
mirrors is the client's own deserializer table — but this pass found the
closest thing to it, one build early, already sitting in the vault.
