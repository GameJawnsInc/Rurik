# Where persistent character data lives

2026-08-16. The question: how and where is persistent character data stored —
titles, XP, profession, roleplaying-vs-PvP, faction, and the rest of the
character sheet? Method: three recon sweeps run this session (our server's
character surface; the four reference servers' persistence layers; a
title/faction wire-message hunt across all mirror lineages), joined to the
existing passes in [FINDINGS.md](FINDINGS.md), `studies/reconstruction`,
`studies/recon` and `studies/divergence`, plus two GWW pages fetched fresh.
Labels are FINDINGS.md's vocabulary; WIKI is `browse-gw-wiki`'s addition to it.

## The answer in one page

**Retail stores everything persistent server-side, in two scopes.** The client
persists no character state locally: `Gw.dat` is a content archive, and the
character roster arrives from the auth server on every login (OBSERVED — the
live capture's four `AUTH_SMSG 0x0007` roster rows, `studies/divergence` §1.2).
What the client holds is *vocabulary* — compiled tables such as the 48-entry
title catalog `s_titleClientData` and the 4-entry `s_charFaction`
(`studies/reconstruction` §2.8 row 20) — and it receives *state* over the wire
at three moments: the char-select roster blob (auth channel), the
instance-load burst (game channel), and incremental updates while playing.

**The two scopes are account and character**, and they are load-bearing:

- **Account-scoped:** faction reputation (Kurzick/Luxon/Imperial/Balthazar,
  including the maxima), skill/item/profession unlocks, and the account-based
  title tracks. WIKI (GWW "Title" §Basics, accessed 2026-08-16): account
  titles are Champion, Codex, Gamer, Gladiator, Hero, Lucky, Unlucky,
  Treasure Hunter, Wisdom, Zaishen, **Kurzick/Luxon allegiance**, Commander;
  progress is shared across all characters. Both reference servers that model
  faction at all put it on the **account** row: OpenTyria's `DbAccount` carries
  `kurzick/luxon/imperial/balthazar_points_{max,amount,total}`
  (`DbSchema.h:36-47`) and its send path reads `player->account.*`
  (`GmPlayer.c:87-107`); GWLP-R's `factionstats` table keys on `AccountID`
  (`default_data.sql:235-255`). UPSTREAM ×2, agreeing with WIKI.
- **Character-scoped:** XP, level, primary/secondary profession, appearance,
  attributes, equipped skill bar, the `is_pvp` flag, last outpost, played
  time, and the character-based title tracks (Survivor, Drunkard, LDoA,
  Sunspear, the EotN reputations, …).

**Roleplaying vs PvP is a character-creation-time flag, not a mode.** WIKI
(GWW "PvP-only character", accessed 2026-08-16): the two character types are
*roleplaying* and *PvP-only*; PvP-only characters start at level 20 in the
Great Temple of Balthazar, can enter only PvP outposts, and draw equipment and
skills from the **account's** unlocks. On the wire the flag is bit 9 of the
char-select settings word (CORROBORATED — FINDINGS.md §a) and the third byte
of `0x00B7` (name CONTESTED — §b); in OpenTyria's persistence it is one
`is_pvp` uint8 column on the character row (`DbSchema.h:84`), beside a
`campaign` column whose value 0 means "PvP" (`GmChar.h:116`).

**Two long-standing gaps closed this pass, at the reading level:** the faction
bar *denominators* have a home — four dedicated one-dword messages
`0x00EA`–`0x00ED` — and titles have a full message cluster `0x00F3`–`0x00F6`
that no capture has ever contained. Details and labels below; neither is yet
OBSERVED against our client, and both have cheap probes.

**Every reference server is load-only.** All four persist a character at
creation and serve it at login; none has a working write-back path for
in-game progression (XP gain, level-up, faction, titles). **Rurik persists
nothing at all** — every character value is a literal, a CLI flag, or one of
two `content/world.toml` rows, and the per-connection state dict dies with the
socket. So "how does the real thing store it" has no full answer anywhere on
disk; what we have is the schema shapes, the wire surfaces, and the retail
semantics from GWW.

---

## 1. The wire map: how stored state reaches the client

Persistent state is invisible except when serialized. Three serialization
moments, all already mapped in this repo except the two new clusters:

| Moment | Channel / message | Carries | Status |
|---|---|---|---|
| Login roster | `AUTH_SMSG 0x0007 CHARACTER_INFO`, one per character | name, uuid, settings blob: version, last outpost, played time, appearance dword, guild hall, `campaign(4)|level(5)|is_pvp(1)|secondary(4)|helm(2)` word, equipment pieces | CORROBORATED ×3 lineages (FINDINGS.md §a); OBSERVED on live wire (4 roster rows, `studies/divergence` §1.2) |
| Instance-load burst | `0x0037` attribute points → `0x003A` attribute array → `0x00B7` professions → `0x00E9` 15-dword set → skillbar `0x00DA` … | attributes, professions, XP, level, faction currents, skill points | Shapes CORROBORATED; `0x00E9` fields 0/9/11/13 OBSERVED against our client (FINDINGS.md §1) |
| Incremental | `0x00EE` `{attr_id, value}` deltas; `0x009F` prop 36 (per-agent level); `0x00EA`–`0x00ED` (faction maxima); `0x00F3`–`0x00F6` (titles) | XP awards, level, caps, title state | `0x00EE` OBSERVED in ArenaNet traffic (XP deltas 26/100/126/250/500, `studies/reconstruction` §2.8 row 21); the rest see below |

## 2. Faction maxima: `0x00EA`–`0x00ED` (new)

FINDINGS.md §1 measured that the client ignores fields 2/4/6/12 of `0x00E9`
for the bar denominators and left "where the maxima come from" NOT FOUND.
Answered at the reading level:

- **Shape — MEASURED at our build.** `schema/messages.json` (validated
  field-for-field against the client's own 38797 message-format tables,
  `studies/msgtable`; no override touches this range) has GAME_SMSG
  234/235/236/237 as header + **one dword**, size 6 — verified directly this
  session. `0x00E9` = 15 dwords and `0x00EE` = 2 dwords bracket the block.
- **Semantics — CORROBORATED, not yet observed.** ldufr names them
  `CHARACTER_FACTION_MAX_KURZICK/LUXON/BALTHAZAR/IMPERIAL`
  (`ldufr__OpenTyria/code/opcodes.h:271-276`, structs `GameMsg.h:173-191`);
  Headquarter's handlers store the dword straight into
  `client->player_hero.{kurzick,luxon,balthazar,imperial}.max` behind
  `sizeof == psize` asserts (`ldufr__Headquarter/code/client/player.c:72-146`
  — verified this session); GWLP-R carries the same four as `P222`–`P225`
  `UpdateMax*Faction` (own numbering, shape identical,
  `GWLP-R-Utils/Templates/PacketTemplates.xml:2893-3018`); GWCA and Py4GW and
  gw-preservation's NLE name the same four opcodes at our numbers (names
  only, no decoders — one of those name tables is ldufr-derived, so count
  the *naming* as roughly two independent voices plus ldufr).
- **The client-memory sink corroborates from the other side.** GWCA's
  `WorldContext` holds `max_kurzick/max_luxon/max_balth/max_imperial` at
  `+0x7B8`–`+0x7C4` as standalone fields, *outside* the dupe-paired
  current/total block that `0x00E9`/`0x00EE` fill (`WorldContext.h:280-304`;
  Py4GW's independently-declared ctypes struct agrees). A field with no
  delta path is consistent with a cap set by its own message.
- **Why `0x00E9` fields 2/4/6/12 are ignored:** every reimplementation names
  them `total_earned_*` — *lifetime* faction, a different stat from the cap.
  The probe's "sent 1002, bar reads / 0" is what you'd expect.
- **Also settled by the same sweep:** `0x00E9` fields 7/8 — the two that
  showed NO VISIBLE EFFECT — are `unk_faction4/unk_faction5` in every lineage
  that names them; nobody knows. Field 10 is `morale` by name everywhere
  (UPSTREAM; our probe REFUTED the obvious display reading, so the name is
  still unproven against the client).
- **Not observed anywhere:** no capture in the vault contains 234–237 (the
  live sessions are Pre-Searing; faction UI is Factions/Nightfall content).

**Probe** (extends `probes.py attr_legend`, one packet each): send
`0x00EA`–`0x00ED` with four distinct values and re-open the faction panel.
Four bars with our denominators = OBSERVED; also decides whether the maxima
messages alone suffice or the numerators must arrive first.

## 3. Titles: the `0x00F3`–`0x00F6` cluster (new)

Titles were this repo's blank: 0 of 22,524 captured server messages, no
crash-proven title module (`studies/recon` §5.3), and nothing sent by us.
The mirrors know a four-message SMSG cluster and two CMSGs:

| Opcode (ours) | Name (ldufr) | Shape (schema, client-validated at 38797) |
|---|---|---|
| `0x00F3` / 243 | `TITLE_RANK_DATA` | 3 dwords + string16(8): `rank_id, unk, rank, name` |
| `0x00F4` / 244 | `TITLE_RANK_DISPLAY` | word + dword: `player_id, rank_id` |
| `0x00F5` / 245 | `TITLE_UPDATE` | 2 dwords: `title_id, new_value` |
| `0x00F6` / 246 | `TITLE_TRACK_INFO` | 10 dwords + 2× string16(8): `track_id, group_id, current_points, current_rank, points_to_current, flags, next_rank_id, points_to_next, max_rank, max_rank_id, point_name, description` |
| CMSG `0x0035` / 53 | `DEPOSIT_FACTION` | dword + byte(0=Kurzick,1=Luxon) + dword |
| CMSG `0x0058` / 88 | `TITLE_DISPLAY` | one dword `title_id` |
| CMSG `0x0059` / 89 | `TITLE_HIDE` | header only |

- **Shapes MEASURED at our build** (same argument as §2: `schema/messages.json`
  241–246 validated against the client's own tables, verified this session).
  Field *names* are ldufr's + GWLP-R's (`P231`–`P234` in its numbering,
  `PacketTemplates.xml:3076-3180`); Headquarter's `title.c` handlers carry
  the same structs behind size asserts but never consume the fields.
  GWCA binds structs only to `0x00F5`/`0x00F6` (`StoC.h:1040-1059` —
  `UpdateTitle`, `TitleInfo`), nothing to `0x00F3`/`0x00F4`. UPSTREAM on
  names throughout; no observation anywhere.
- **The dynamic sink:** GWCA `WorldContext` `titles` array at `+0x81C` and
  `title_tiers` at `+0x82C`; per-title record is 0x2C bytes
  (`current_points, tier indices, points_needed_*, two enc-string
  pointers` — `GameEntities/Title.h`, `static_assert` 0x2c; the header's
  "0x28" comment is stale). Py4GW's shared-memory mirror caps at **48
  titles** — the same 48 as the client's `s_titleClientData` and OpenTyria's
  48-member `TitleId` enum (`GmTitles.h`). Three independent 48s.
- **Two different "max" concepts — do not conflate.** `TITLE_TRACK_INFO`'s
  `max_rank`/`max_rank_id` are small per-track tier counts for the Hero-panel
  UI. The faction bar denominators are §2's four messages. A server that
  tries to set Kurzick's cap through a title message has confused the two.
- **Persistence-side:** OpenTyria is the only server that even scaffolds
  titles — a 48-title enum with rank thresholds (`GmTitles.h`,
  `GmTitleConstData.c`), an orphaned `titles` SQL table
  (`seed.sql:159-170`: `account_id, char_id, title_id, current_rank,
  current_points` — note it carries *both* scope keys) and a **commented-out**
  send site (`GameSrv.c:1472` `// GameSrv_SendPlayerTitles`). GWLP-R has the
  three protocol shells and no table. Nobody persists a title anywhere.

**Probes**, cheapest first: (1) send one `0x00F6` with a synthetic track and
open the Hero panel's Titles tab — if a track row renders, the message and
the tab are both settled in one packet; (2) `0x00F5` afterwards to see
whether an update alone can *create* a track entry or only modify one;
(3) `0x00F4` against our own agent id with a rank from (1), looking for the
under-name title. The client's title UI is data-driven from a 48-row compiled
table, so id-space errors should assert loudly rather than silently render
(`GmCtlSkList:3294 title < TITLES`).

## 4. What the reference servers actually persist

Full per-lineage detail is in this session's recon (summarized here; every
cell was cited file:line in the sweep). All four are **real databases** and
all four are **write-once at creation, load-only afterwards**:

| | OpenTyria (SQLite/C) | gw-preservation (SQLite/Go) | GWLP-R (MySQL/Java) | sgwlpr (MongoDB/Scala) |
|---|---|---|---|---|
| XP / level | char row ✔ | char row ✔ | char row ✔ (level → `levels` lookup: L→attr points) | level only |
| Professions | char ✔ both | char ✔ both | char ✔ both, FK | primary only; secondary hardcoded on the wire |
| `is_pvp` | char ✔ + `campaign` 0=pvp | ✘ | ✘ | char ✔ (but wire path hardcodes 0) |
| Appearance | char, decomposed columns | char, packed dword | char, decomposed | char, decomposed |
| Attributes | ✘ (enum only) | ✘ (stub sends) | **char, normalized** (`attributepoints`) | ✘ |
| Skills / unlocks | char: 8-slot bar + `Bitmap1024` unlocks + maps/missions/professions bitmaps | ✘ (sends all-unlocked) | **char, normalized** (`skillaccess`, `skillsequipped`, `professionaccess`) | ✘ |
| Faction | **account** ✔ incl. `_max` | ✘ | **account** ✔ (`factionstats`) | ✘ |
| Titles | dead schema only | ✘ | protocol shells only | ✘ |
| Write-back of progression | none (`Db.c` has no `UPDATE characters` at all) | only `last_outpost` + bags on map transfer | creation path persists the wrong object (`CharacterCreation.java:148` saves `chara`, the null lookup, not the populated `dbChar`) | `Character.update()` defined, never called |

Two shapes worth stealing when Rurik grows a store: OpenTyria's **account/
character split with faction (incl. maxima) on the account row**, and
GWLP-R's **`levels` lookup table** (level → cumulative attribute points,
L20 = 170 — the only level-to-points table on disk, FINDINGS.md §c).
UPSTREAM both; neither is evidence about retail's internal schema, only about
what suffices to drive the client.

## 5. What Rurik stores today: nothing

Verified this session over the whole toolkit:

- Every character value the server sends is a **Python literal** in
  `authsrv.py` (name, uuid, settings blob, `START_LEVEL = 1`, professions),
  a **CLI flag** (`--spawn-profession`, `--skills`, `--unlocks`,
  `--secondary-bits`), or one of exactly **two `content/world.toml` rows**
  (`[player.attributes]` ranks — provenance `invented`; `[player.defaults]`
  energy/health — sourced gw-preservation). The `0x00E9` array goes out with
  field 9 = 1 and **all other fourteen fields deliberately zero**.
- The per-connection `state` dict (quests held, objectives, selected
  character, map) is created per socket and dies with it. Nothing is written
  back.
- `vault/state/` is **login-session tokens only** (`sessionstore.py` — the
  portal↔authsrv handoff). Keyed by token, knows emails, holds nothing
  character-shaped. It is the only vault/state reader/writer in the toolkit.
- The client already *sends* a write: `AUTH_CMSG 0x0009
  UPDATE_CHARACTER_SETTINGS` is received, buffered, logged to the capture,
  acked OK — and dropped (`authsrv.py:7076-7088`). A persistence layer's
  first write path already has traffic waiting for it.
- Explicitly unmodelled, by its own comment (`authsrv.py:5631-5633`):
  inventory, max factions, hard mode. Titles: zero mentions in the file.

## 6. If/when Rurik grows a character store

Not scheduled anywhere; recorded so the shape is not re-derived. The minimum
honest design, given everything above:

1. **Two records, keyed the way retail scopes them**: an account record
   (unlocks, faction currents *and maxima*, account titles) and a character
   record (uuid, name, appearance dword, campaign, level, XP, professions,
   `is_pvp`, attributes, skill bar, last outpost, played time, char titles).
   OpenTyria's `DbCharacter` column list is the best single crib.
2. **Serve the roster from the store** — `char_settings_for()` already
   assembles the blob; it needs rows instead of the `TEST_CHAR_*` literals.
3. **Serve the instance-load burst from the store** — the send sites all
   exist; today they read module globals.
4. **Consume `UPDATE_CHARACTER_SETTINGS`** instead of dropping it, and pick
   the write-back moments (map transfer and logout are what
   gw-preservation's one working save path uses).
5. **A flat file is enough.** One JSON/TOML per account under `vault/` (it is
   personal data; it stays out of git per the vault rule). Nothing here needs
   SQL, and the server path must stay stdlib-only.

## 7. Open items

- Run the two probes (§2, §3). Both are one-packet `probes.py` additions with
  stated predictions; both convert reading-level claims into OBSERVED.
- `0x00E9` fields 7/8 stay unnamed in every lineage; field 10 "morale" is a
  name our own probe already refuted as a display. Park them.
- Whether the account/character title scope split is visible on the wire
  (WIKI says progress is shared account-wide for some tracks; the messages
  carry `title_id`/`track_id` with no scope marker) — answerable only with
  real title traffic, i.e. a live capture outside Pre-Searing, or a probe.
- `is_pvp`'s two open probes from FINDINGS.md §b stand unchanged.
