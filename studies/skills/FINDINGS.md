# What we actually know about skills

Ten reading tracks over eleven prior-art mirrors, our own capture vault and our own
schema, each then adversarially re-verified by a second reader who re-opened every
cited file and re-ran every generalising grep. This document records only what
survived verification, and labels everything.

No code was written and no client was launched for this pass. It is a study.

## Labels used throughout

| Label | Meaning |
|---|---|
| **OBSERVED** | We saw it ourselves, against our own client, in our own logs. |
| **CLIENT-DATA** | Read out of the shipped client — its PE tables, its `Gw.dat`, or its live memory layout — by a third-party tool whose code we have read. This is the strongest class of evidence in this pass, and it is still somebody else's reading. |
| **UPSTREAM** | A reimplementation's code says this, and a verifier confirmed the line. These are reconstructions; none is a fact about ArenaNet's server. |
| **RECONSTRUCTION** | The source signals it is guessing — offset-named field, placeholder magic, commented-out call, or the author saying so. |
| **CONTESTED** | Sources disagree, and this document does not pick a winner. |
| **UNVERIFIED** | Claimed by a track, and the verifier could not confirm it. Do not build on this. |
| **NOT FOUND** | We looked, and there is no answer in the sources we have. |
| **WIKI** | The official Guild Wars Wiki (`wiki.guildwars.com`) says this — twenty years of players documenting observed retail behaviour, cited by page and section. Its strength is **not uniform**: strong for player-visible values (a skill's displayed cost, recharge, description), because mass observation of the retail client beats any single reimplementation's reading; weak for internals (byte layouts, wire formats), which players inferred from outside. The test is *could a player have seen this from the game window?* It shares no author, code or ancestry with the §6 cluster, so wiki + a code lineage agreeing is real corroboration. |

**The single most important thing this pass learned about its own sources** is in
§6, and it is bad news: the "ldufr" and "GWCA" lineages, which the movement pass
treated as independent, are **not independent**. They share an author. Nine
separate repositories in our vault propagate one misspelling. Read §6 before
treating any two sources here as corroboration.

---

## The answer in one page

**The client already knows everything about every skill, and the server is not
told any of it.** A skill's name, description, icon, attribute, profession,
energy cost, cast time, aftercast, recharge, adrenaline, AoE range, rank-0/rank-15
scaling and animation ids all live in a fixed-width table compiled into the
client, indexed by numeric skill id. Nothing in any protocol message in any
direction carries a single one of those values. Every skill-related message in
the catalogue refers to a skill by a bare number.

This is the load-bearing finding of the pass. It is supported by four sources
using three different methods, two of which are outside the authorship cluster:

- **Fournux/Tyria-Extractor** parses the client PE and reads a `0xa4`-byte
  (164-byte) record per skill, addressed as `table_base + skill_id * 0xa4`
  (`doc/SKILL_EXTRACTION.md:23-30`). Its skill extraction command takes
  **only a `Gw.dat` path** — no packet log, no injected sniffer, no network
  (`src/cli.rs:41-44`). A tool that can produce the complete skill dataset from
  a disk file alone is a proof that no server tells the client any of it.
- **GWCA** declares the same record as a C++ struct, `sizeof == 0xa4`, and gets
  it by scanning the client binary
  (`gwdevhub__GWToolboxpp/Dependencies/GWCA/include/GWCA/GameEntities/Skill.h:14-87`).
- **The client's own assertion string**, recovered by GWCA's scanner, is
  `index < arrsize(s_skill)` (`gwdevhub__GWToolboxpp/tools/gw-update/anchor-index.json:1519-1520`).
  That is ArenaNet's text, naming a file-scope array `s_skill` and bounds-checking
  an index against it. It is the closest thing to a primary source in this pass.
- **GWLP-R**, an unrelated 2013 server lineage, designed a `skills` database table
  whose only columns are `ID`, `Name`, `Attribute` — no cost, no cast time, no
  recharge, no icon — and shipped it with **zero rows**
  (`database/src/main/sql/default_data.sql:86-102` region). A server project that
  got as far as a JPA entity and two join tables never modelled a single skill
  constant, because there was never any reason to.

Two independent measurements of how many skills exist land four apart:
Tyria-Extractor counts **1,333** base rows in a 2026-07-26 `Gw.exe`
(`GWDAT_INVESTIGATION_JOURNAL.md:128`); the Guild Wars wiki totals **1,329**
player skills (`vault/research/2026-08-04/skill-substrate.md:21-36`). Two
unrelated methods, 0.3% apart. That is the best corroboration anywhere in this
document, and it is better than anything the cluster's internal agreement can
offer.

**What this means for the two questions that actually matter:**

**Getting a real skill onto the bar is nearly free.** One message —
`GAME_SMSG_SKILLBAR_UPDATE`, opcode 218 / `0x00DA` — carries eight `uint32` skill
ids, and the client draws the icon, name, tooltip, cost and recharge from its own
table. We already send this message; we send eight zeros. Changing a zero to
`1954` is the whole of Q3. See §3 for the exact caveats, of which the real one is
that our opcode numbering has never been validated against our own client.

**Creating a genuinely new skill is a client-patching project, not a server
project.** The id *is* the row index into a compiled table whose length is stored
in the table itself. An id the client has never heard of has no row, no name
string, no icon file and no animation. Re-skinning an existing id with new
server-side behaviour, by contrast, requires **no client change at all** — and is
the only one of the two that is available to us today. See §5.

**Third, and unwelcome:** no prior server project in our vault has ever
implemented skill *execution*. Not OpenTyria, not GWLP-R, not the Go server. All
three send a skill bar at map load and stop. There is no reference implementation
of casting anywhere in our sources, and the client-to-server half of the protocol
is materially worse evidenced than the server-to-client half. See §4.

---

## 1. Where skill data lives

### The short version

| Component | Lives in | Addressed by | Label |
|---|---|---|---|
| Stats (costs, timings, attribute, profession, flags, scaling) | A fixed-width array **inside the client PE** | `skill_id` as the zero-based row index | CLIENT-DATA |
| Name, concise description, full description | **`Gw.dat` text resources** | three `uint32` **string ids** stored in the PE row | CLIENT-DATA |
| Icons (standard and high-res) | **`Gw.dat` textures** (ATEX/ATTX) | two-to-three `uint32` **dat file numbers** stored in the PE row | CLIENT-DATA |
| Cast animations | referenced by six `uint32` ids in the PE row | id → asset resolution **NOT FOUND** | CONTESTED (see below) |
| Which skill is in which bar slot | **the server** | `SKILLBAR_UPDATE` | UPSTREAM |
| Which skills are unlocked | **the server** | unlock bitmaps | UPSTREAM |
| Live recharge / cast / interrupt events | **the server**, by skill id | lifecycle messages | UPSTREAM |

The dividing line is clean and it is worth stating as a rule: **the server owns
which and when; the client owns what.**

### The skill record

164 bytes, `0xa4`. Two sources describe it and they were written independently.
Here is the 2026-era GWCA struct in full, because every offset in it is something
a private server does *not* get to choose
(`gwdevhub__GWToolboxpp/Dependencies/GWCA/include/GWCA/GameEntities/Skill.h:14-87`,
verbatim, abridged only of its predicate methods):

```c
struct Skill { // total : 0xA4/164
    /* +h0000 */ GW::Constants::SkillID skill_id;
    /* +h0004 */ uint32_t h0004;
    /* +h0008 */ GW::Constants::Campaign campaign;
    /* +h000C */ GW::Constants::SkillType type;
    /* +h0010 */ uint32_t special;              // flag bitfield
    /* +h0014 */ uint32_t combo_req;
    /* +h0018 */ uint32_t effect1;
    /* +h001C */ uint32_t condition;
    /* +h0020 */ uint32_t effect2;
    /* +h0024 */ uint32_t weapon_req;
    /* +h0028 */ GW::Constants::ProfessionByte profession;
    /* +h0029 */ GW::Constants::AttributeByte attribute;
    /* +h002A */ uint16_t title;
    /* +h002C */ GW::Constants::SkillID skill_id_pvp;
    /* +h0030 */ uint8_t combo;
    /* +h0031 */ uint8_t target;
    /* +h0032 */ uint8_t h0032;
    /* +h0033 */ uint8_t skill_equip_type;
    /* +h0034 */ uint8_t overcast;              // only if special flag has 0x000001 set
    /* +h0035 */ uint8_t energy_cost;
    /* +h0036 */ uint8_t health_cost;
    /* +h0037 */ uint8_t h0037;
    /* +h0038 */ uint32_t adrenaline;
    /* +h003C */ float activation;
    /* +h0040 */ float aftercast;
    /* +h0044 */ uint32_t duration0;
    /* +h0048 */ uint32_t duration15;
    /* +h004C */ uint32_t recharge;
    /* +h0050 */ uint16_t h0050[4];
    /* +h0058 */ uint32_t skill_arguments;      // 1 duration set, 2 scale set, 4 bonus scale set
    /* +h005C */ uint32_t scale0;
    /* +h0060 */ uint32_t scale15;
    /* +h0064 */ uint32_t bonusScale0;
    /* +h0068 */ uint32_t bonusScale15;
    /* +h006C */ float aoe_range;
    /* +h0070 */ float const_effect;
    /* +h0074 */ uint32_t caster_overhead_animation_id; //2077 == max == no animation
    /* +h0078 */ uint32_t caster_body_animation_id;
    /* +h007C */ uint32_t target_body_animation_id;
    /* +h0080 */ uint32_t target_overhead_animation_id;
    /* +h0084 */ uint32_t projectile_animation_1_id;
    /* +h0088 */ uint32_t projectile_animation_2_id;
    /* +h008C */ uint32_t icon_file_id;
    /* +h0090 */ uint32_t icon_file_id_2;
    /* +h0094 */ uint32_t icon_file_id_hi_res;
    /* +h0098 */ uint32_t name;                 // String id
    /* +h009C */ uint32_t concise;              // String id
    /* +h00A0 */ uint32_t description;          // String id
};
static_assert(sizeof(Skill) == 0xa4, "struct Skill has incorrect size");
```

Fournux/Tyria-Extractor documents 31 of those offsets from its own reading of the
PE (`doc/SKILL_EXTRACTION.md:23-76`) and agrees with GWCA on every one it covers,
**including the tail offsets and the total size**. That is a genuine cross-source
agreement: Tyria-Extractor is not in the authorship cluster (§6), and it arrived
at `0x98`/`0x9c`/`0xa0` for the three string ids on its own.

**Three things about that record a server implementer must not get wrong:**

1. **`energy_cost` at `+0x35` is an encoded byte, not an energy number.** Value 11
   means 15 energy; value 12 means 25 energy; everything else is literal. Both
   sources carry the same two special cases — GWCA as a `GetEnergyCost()` helper
   (`Skill.h:89-95` region), Tyria-Extractor as a documented rule
   (`doc/SKILL_EXTRACTION.md:43`). CLIENT-DATA, but see the caveat below.
2. **`adrenaline` at `+0x38` is a total in adrenaline units, and the displayed
   cost is `ceil(raw / 25)`** — not a plain division. **This document, not
   Tyria-Extractor, is what was wrong.** `doc/SKILL_EXTRACTION.md` §2.1 states
   the ceil formula explicitly, with a worked example (Gash stores 140 units,
   displays 6); only the one-line gloss in its offset table reads "25 units
   correspond to one displayed strike", and that gloss is what this document
   copied. Dividing gives 3.2 for Battle Rage and 4.8 for Defy Pain, which are
   not integers and are not what the client shows. Now verified against 115
   skills — see "The adrenaline field, measured and corrected".
3. **62 of the 164 bytes are undocumented by Tyria-Extractor** — `0x04-0x07`,
   `0x14-0x27`, `0x32`, `0x37`, `0x50-0x57`, `0x74-0x8b`, `0x94-0x97`. GWCA names
   some of those bytes (notably the whole animation block and
   `icon_file_id_hi_res`) but three of its own fields are still offset-named:
   `h0004`, `h0032`, `h0037`, `h0050[4]`. Nobody has fully reversed this record.

**Caveat on the energy encoding, and it is the field most likely to bite us.**
The 11→15 / 12→25 mapping has no disassembly address, no journal entry, and no
test in either source. Two special values is a suspiciously small set for a
hand-derived encoding. Mark it **CLIENT-DATA, uncorroborated by measurement** —
if Rurik ever serves energy costs, verify this one first.

### The adrenaline field, measured and corrected

**CORROBORATED — OBSERVED (ours) + WIKI (GWW), and it refutes the rule this
document shipped.** This is the only field in the 164-byte record we have taken
all the way from raw bytes to what the player sees.

We read `+0x38` out of the client's skill row and watched what the client
displayed:

| Skill | id | raw `+0x38` | client shows |
|---|---|---|---|
| Battle Rage | 317 | 80 | 4 |
| Rush | 319 | 80 | 4 |
| Defy Pain | 318 | 120 | 5 |

The inherited rule — raw ÷ 25 — gives 3.2, 3.2 and 4.8. None is an integer and
none matches. Three observations were not enough to choose between the two
obvious repairs, `ceil(raw/25)` and `floor(raw/25)+1`, since both fit all three.

The wiki supplied the mechanism, which decides it:

- **WIKI (GWW, "Adrenaline" §Gaining adrenaline):** "You gain 25 units of
  adrenaline (=one strike) each time you successfully hit an opponent with a
  weapon", plus 1 unit per 1% of maximum health lost, rounded down.
- **WIKI (GWW, "Battle Rage" §Notes; identical text on "Rush" §Notes):** "This
  skill exactly requires **80 units** of adrenaline to be fully charged, so 3
  strikes and 5 units."

Gain is a flat 25 per hit, so a skill's displayed cost is **the number of hits
needed to charge it**:

```
displayed_strikes = ceil(raw_units / 25)
```

Battle Rage's 80 units is three full strikes with 5 units owing; the fourth hit
covers them, so the client shows 4. `floor(raw/25)+1` is **refuted** — it
predicts 2 for a 25-unit skill, 5 for 100, 6 for 125, 7 for 150 and 9 for 200,
where the correct values are 1, 4, 5, 6 and 8. Any cost that is an exact
multiple of 25 separates the two rules.

Two things worth keeping beyond the formula:

- **GWW independently confirms the raw magnitude**, not just the displayed
  value. "80 units" is exactly our `+0x38`. That is a player-visible page
  agreeing with a byte we read out of the binary, from a source with no
  relationship to the §6 authorship cluster — the strongest corroboration in
  this section.
- **GWW skill pages carry ArenaNet's own skill `id`** in their infobox (Battle
  Rage 317, Defy Pain 318, Rush 319 — consecutive). That is a direct join key
  from a wiki page to a row in the client's skill table, and it makes
  wiki-vs-client cross-checking mechanical rather than manual. `Gw.exe` row
  count and wiki skill count already agree to 0.3% (§"The answer in one page");
  the `id` field is how that comparison could be done row by row.

### The row-by-row audit

**OBSERVED (ours), 2026-08-06.** `toolkit/clientscan/skilltable.py` is our own
stdlib-Python reader for `s_skill`. It locates the table structurally — never by
address — and dumps every row. Against `C:\gw\Gw.exe` (10,483,904 bytes) it
finds the table at file offset `5799632`, **3,443 rows**, of which **1,333** are
the player corpus (`equip_family == 1`, PvP flag clear).

**1,333 is exactly Tyria-Extractor's count.** That is a second implementation,
in a different language, written from the spec rather than the code, landing on
the same number — which is what makes the layout claim above CORROBORATED
rather than merely repeated.

The wiki's `id` field makes the join mechanical. Crawling the ten profession
categories plus Common skills via the MediaWiki API yields 1,788 pages, 1,564
carrying an infobox `id`. Joined against the client table:

| Field | Compared | Agree | Disagree |
|---|---|---|---|
| `adrenaline` → `ceil(units/25)` | 115 | **115** | **0** |
| energy encoding `11` → 15 | 104 | **104** | **0** |
| energy encoding `12` → 25 | 30 | **30** | **0** |
| `elite` flag | 307 client-corpus elites | **all** | **0** |

**Nothing disagreed.** Every gap resolved to a set-definition or coverage
difference, checked rather than assumed:

- 49 wiki-elite ids sit outside the client's corpus-elite set. Sampled 15: all
  15 are `pvp_only` rows with `equip_family == 0` whose `linked_id` points back
  at the base skill — precisely the reciprocal PvP relation
  `SKILL_EXTRACTION.md` §4 describes, and excluded from the corpus by design.
  The elite flag itself agrees on them.
- Ids `121` and `229` carry the encoded energy byte but appear nowhere in the
  crawl. They are not a conflict; the eleven categories walked do not cover
  every skill page. **UNVERIFIED** rather than clean.
- The wiki dump spans 1,564 ids against a 1,333-row corpus, so raw distribution
  totals differ. That is the PvP variants, not a discrepancy.

**This settles the energy encoding**, which this document flagged two sections
above as the field "most likely to bite us" — CLIENT-DATA with no disassembly
address, no journal entry and no test. It now has 134 independent confirmations
and zero exceptions: every skill the wiki shows at 15 energy stores `11`, every
skill it shows at 25 stores `12`. Promote it to **CORROBORATED**. The caveat
above is retained deliberately as a record of what the doubt was worth.

Incidental: the wiki lists exactly **1,329** skills carrying an energy cost —
the same 1,329 this document already cites for the wiki skill count, arrived at
by a different route.

**How to re-read the wiki.** `wiki.guildwars.com` gives a scripted client a
small burst of requests and then refuses it for a long while — MEASURED at 5
consecutive successes out of 20, then hard 403s, with a two-minute backoff not
restoring access. No User-Agent, header set or VPN change helps, and retrying
in a loop is what exhausts the allowance. Use the `browse-gw-wiki` skill in
`.claude/skills/`; a browser is unaffected, and the API *is* reachable from
inside a browser page context (`fetch('/api.php?...')` under `javascript_tool`),
which is how 1,788 pages were pulled here — far cheaper than one navigation per
page.

The occasional scripted success is a trap worth naming: it briefly made the
skill's own selftest report GWW as unblocked, because the check was reading a
cache entry written during a lucky window. A network check a cache can satisfy
is not a network check.

**Do not use the Fandom GuildWiki (`guildwars.fandom.com`) for skill values.**
Its skill templates were last edited 2008–2010 while ArenaNet still ships
balance updates. It lists Defy Pain at 130 units / 6 strikes against GWW's 5 and
our measured 120, and gives 20 seconds for out-of-combat adrenaline decay where
GWW gives 25. Neither page flags itself as uncertain. A frozen wiki does not
produce obvious garbage; it produces confidently wrong specifics that survive a
casual cross-check.

### Where the table itself sits

**CLIENT-DATA.** Tyria-Extractor obtains the client PE by reading it out of
`Gw.dat` as archive file id **4102** and parsing it as a PE32 image, falling back
to a `Gw.exe` on disk and then to a second `Gw.dat` in the parent directory
(`src/dat.rs:16`, `:350-399`). It then locates the skill table **structurally**,
not by address: it scans every PE section at 4-byte steps for a candidate where
row 0 has id 0, **the `u32` at row-0 offset `0x2c` equals the record count**, row
1 has id 1, and row 1's description id is row 0's plus one, then scores up to 256
further rows for plausibility (`src/skills/table.rs`).

That row-0 detail matters for §5: **the table stores its own length**, in the
field that is `skill_id_pvp` on every other row.

**Correction to a claim you may meet elsewhere in this repo: "file 4102 is
Gw.exe" is the tool author's naming, not a demonstrated fact.**
`const CLIENT_PE_FILE_ID: u32 = 4102;` is the only occurrence of 4102 in the
entire Tyria-Extractor tree; no comment, journal entry or commit message explains
how it was determined. What is sourced is "a `MZ`/PE32 image lives at dat file
4102 and the skill table is in it". RECONSTRUCTION on the identification.

GWCA's older forks locate the table differently — by scanning `.text` for the
byte pattern `8D 04 B6 C1 E0 05 05` (an `index * 5 * 32` = `index * 160` address
computation) and validating that the resulting pointer lies in the PE section
named `.rdata` (`GregLando113__GWCA/Source/SkillbarMgr.cpp:147`). **That code is
dead.** The stride it encodes is 160, which is the pre-2026 record size, and
GWToolbox's own generated anchor index shows the current GWCA finds the array via
the `index < arrsize(s_skill)` assertion string instead. Cite the `.rdata` gate
only as era-tagged corroboration for "compiled-in static array", never as a
current-build fact.

### Names and descriptions

**CLIENT-DATA.** They are not strings on the record; they are `uint32` string
ids. Two sources describe two halves of the same pipeline:

- **Tyria-Extractor** resolves a string id to a `Gw.dat` text resource by integer
  division: `file_index = string_id / 1024`, `record_index = string_id % 1024`.
  The `file_index` selects a slot in an **11 languages × 99 text files = 1,089
  pointer array that lives in the PE**; changing language changes only which row
  of that array is used, never the `(file_index, record_index)` pair. The array's
  virtual address is build-specific (`0x00BEF1B8` in one client, `0x00BF0210` in
  the 2026-07-26 client), so the tool locates it structurally as the unique run of
  1,089 backed pointers (`GWDAT_INVESTIGATION_JOURNAL.md:41-47`).
- **GWCA/GWToolbox** shows the *runtime* path: the id is converted to an encoded
  wide string (`GW::UI::UInt32ToEncStr`) and resolved through the client's own
  asynchronous, language-aware text decoder (`GW::UI::AsyncDecodeStr`).

**Descriptions are templates, not finished text.** The stored description carries
`%str1%` / `%str2%` / `%str3%` placeholders which the client fills from the
record's own `scale0`/`scale15`, `bonusScale0`/`bonusScale15` and
`duration0`/`duration15` pairs. Tyria-Extractor decoded 1,261 English templates
and found **only** those three placeholders, each with a non-zero corresponding
endpoint pair (`GWDAT_INVESTIGATION_JOURNAL.md:60-64`). GWToolbox independently
builds the same substitution with control codes `0x10A`/`0x10B`/`0x10C`. Two
lineages, same mechanism.

This retires an open question our own repo logged as unresolved:
`vault/research/2026-08-04/client-data-tables.md:300-310` records the encoded
string format as UNRESOLVED. Tyria-Extractor ships a format document and decoded
1,261 records with it.

**The client draws its own tooltips.** GWToolbox hooks a client function found by
the assertion string `GmTipSkill.cpp` / `"No valid case for switch variable
'm_powerType'"`, which takes `{frame_id, skill_id, ...}` and writes a skill
description into a UI frame. The client can render a complete tooltip **from a
skill id alone**. CLIENT-DATA, and directly load-bearing for Q3.

### Icons

**CLIENT-DATA, with an open disagreement.** The record holds raw `uint32` `Gw.dat`
file numbers. GWToolbox's `Resources::GetSkillImage` feeds `skill->icon_file_id`
straight into `GwDatModule::LoadTextureFromFileId`, which memory-maps the
client's own open `Gw.dat` handle, parses the MFT and decodes the ATEX/ATTX
texture. Tyria-Extractor resolves the same numbers through the dat hash lookup and
writes PNGs.

**CONTESTED — which slot is the high-resolution icon.** Tyria-Extractor documents
`0x8c` as standard and **`0x90` as "high-resolution icon file number in the
analyzed client table"**, and documents nothing at `0x94`. GWCA names `0x8c`
`icon_file_id`, `0x90` `icon_file_id_2`, and **`0x94` `icon_file_id_hi_res`**.
GWToolbox is not even self-consistent: its HD export prefers `icon_file_id_2`,
its listing draws `icon_file_id` first, and `Resources` treats
`icon_file_id_hi_res` as the hi-res one. Three readings of three fields. Do not
build on any of them without measuring.

A wiki-scraping path exists in GWToolbox (`Resources::GetSkillImageFromGWW`) and
in Py4GW (a bundled `skill_descriptions.json` of 1,488 entries plus scraped JPGs).
Neither is how the game renders skills — GWToolbox's wiki function has **zero call
sites in the entire mirror**, and Py4GW's bundles are a back-fill for its own
overlay. Mentioned only so nobody mistakes a scraped asset corpus for client data.

### Cast animations — the real gap

**CONTESTED, tending to NOT FOUND.** GWCA names six animation-id fields at
`+0x74`..`+0x88` (caster overhead/body, target body/overhead, two projectile
animations), with the comment `2077 == max == no animation`. Tyria-Extractor
leaves that entire byte range undocumented. So the *existence* of per-skill
animation ids is single-lineage (cluster) evidence.

Worse, **nothing anywhere resolves an animation id to an asset.** No GWCA or
GWToolbox code reads those six fields for any purpose. GuildWarsMapBrowser carries
a `Gw.exe`-derived animation-state table containing `"Skill Cast"`, `"Skill
Channel"`, `"Spell Cast"` and similar — but those are generic per-*model* states
keyed by hash, with no skill linkage, and the table is a poor source in its own
right: it contains six duplicated hash keys, two sentinel values and one entry the
author flags as invented. Treat it as low-confidence reconstruction.

If we ever need to know which animation a specific skill plays, no source we have
answers it.

### What the client holds at runtime, beyond the constants

**CLIENT-DATA**, all from the 2026 vendored GWCA:

```c
struct SkillbarSkill { // total: 0x14/20
    /* +h0000 */ uint32_t adrenaline_a;
    /* +h0004 */ uint32_t adrenaline_b;
    /* +h0008 */ uint32_t recharge;
    /* +h000C */ Constants::SkillID skill_id;
    /* +h0010 */ uint32_t event;
};
struct Skillbar { // total: 0xBC/188
    /* +h0000 */ uint32_t agent_id;
    /* +h0004 */ SkillbarSkill skills[8];
    /* +h00A4 */ uint32_t disabled;
    /* +h00A8 */ SkillbarCastArray cast_array;
    /* +h00B8 */ uint32_t h00B8;
};
```

`recharge` is an **absolute client timestamp**, not a remaining duration:
`GetRecharge()` returns `recharge - MemoryMgr::GetSkillTimer()`, and 0 means
ready (`GregLando113__GWCA/Source/Skill.cpp:9-12`). The cooldown countdown is
computed entirely client-side once the server has supplied the target tick — the
client never polls "is it ready yet".

Skill unlock state is likewise client-resident once delivered: account-level in
`AccountContext.unlocked_account_skills`, character-level in
`WorldContext.unlocked_character_skills`, both `uint32` bitfields indexed
`array[id/32] & (1 << (id%32))`.

**CONTESTED — the `Skillbar` tail.** The two current sources disagree. GWCA
(refreshed 2026-07-14) has `SkillbarCastArray cast_array` at `+0xA8`; apoguita's
Py4GW_Reforged_Native still carries the older `{h00A8[2], casting, h00B4[2]}`
layout, and their `SkillbarCast` element layouts also differ. Anything Rurik
writes about "the client's casting field" must pick a side and say which.

### Attributes

Attribute constant data is a **second** client-resident array — `AttributeInfo
{profession_id, attribute_id, name_id, desc_id, is_pve}`, `0x14` bytes, count
hardcoded `0x33` (51) in GWCA's scan pattern. Same pattern as skills: names are
string ids, the server sends only numbers.

**A settled correction, and one of the more useful results of this pass:
OpenTyria's attribute id space is wrong.** Three sources place Dagger Mastery at
**29**, leaving 26/27/28 unused, and Mysticism at **44**:

| Source | Dagger Mastery | Mysticism | 26/27/28 |
|---|---|---|---|
| ldufr **OpenTyria** `GmAttributes.h:30,45` | **26** | **41** | packed, no gap |
| ldufr **Headquarter** `include/client/constants.h:80,95` | 29 | 44 | unused |
| **GWLP-R** DB, `default_data.sql:102` | 29 | 44 | three `'Reserved'` rows |
| **GWCA** `AttributeByte` enum | 29 | — | explicit jump to 29 |

Headquarter's own template decoder independently hardcodes `ATTRIBUTE_MAX = 44`
(`code/client/skill.c:576-578`). OpenTyria is contradicted by its own author's
other project, by an unrelated 2013 lineage that shipped 45 populated rows, and
by GWCA. **Do not import OpenTyria's attribute enum.** Note also that GWLP-R's
own parallel Java enum omits the three Reserved slots and therefore diverges from
its own database ids above 25 — that enum is dead code and should not be used
either.

---

## 2. What the protocol says

Everything in this section is the ldufr wire catalogue unless marked otherwise.
Two facts about its provenance govern how much weight it can carry.

**First, the server-to-client half is machine-extracted and the client-to-server
half is not.** `msgdefs.info` is `msgdefs.c` plus one `// Handler Rva:` comment
per format table — and those annotations exist on **39/39 AUTH_SMSG and 487/487
GAME_SMSG tables, and on 0/57 AUTH_CMSG and 0/194 GAME_CMSG tables** (verifier's
own census). The SMSG shapes are anchored to real client dispatch addresses. The
CMSG shapes rest on unstated derivation. Weight them differently.

**Second, `schema/messages.json` is a byte-faithful import of this exact file.**
The verifier re-ran the diff across all four channels: **zero mismatches in field
type, length, count or declared size, over 777 tables**. Its agreement with
`msgdefs.c` is a tautology, never corroboration. It also carries
`"validated_against_build": null`, and `schema/overrides.json` holds exactly one
measured override — a GAME_CMSG entry. **No skill-related SMSG in this repo has
ever been checked against a real client.**

A note on a claim that circulated during this pass: it is *not* true that
`messages.json` has no skill entries. Every skill message's **shape** is there,
correctly, keyed by decimal opcode. What is missing is any **semantic name** —
the file has no name field for any opcode at all. You cannot tell from it that
`70` is `USE_SKILL`; that mapping has to come from `opcodes.h` by hand.

### Server → client

Sizes below are **wire** bytes computed from `msgpack.c`'s packer, which writes an
array count as `u16` on the wire while the struct holds it as `u32` — so a
variable message is exactly 2 bytes smaller per array than its declared size.

**The skill bar**

| Opcode | Name | Wire shape | Bytes | Sent by OpenTyria? |
|---|---|---|---|---|
| 217 / `0x00D9` | `SKILLBAR_UPDATE_SKILL` | agent_id, u8 slot, u16 skill_id, u32 | 13 | no |
| 218 / `0x00DA` | `SKILLBAR_UPDATE` | agent_id, array32[8] skills, array32[8] pvp_masks, u8 | 75 at 8/8 (declared 79) | **yes** |

`SKILLBAR_UPDATE` is the full-bar load and the single most important message in
this document. Its sender, verbatim (`ldufr__OpenTyria/code/GmPlayer.c:150-167`):

```c
void GameSrv_SendSkillbarUpdate(GameSrv *srv, GameConnection *conn, GmPlayer *player)
{
    GameSrvMsg *buffer = GameSrv_BuildMsg(srv, GAME_SMSG_SKILLBAR_UPDATE);
    GameSrv_SkillbarUpdate *msg = &buffer->skillbar_update;
    msg->agent_id = player->agent_id;
    msg->n_skills = 8;
    msg->skills[0] = player->character.skill1;
    /* ... skills[1..6] ... */
    msg->skills[7] = player->character.skill8;
    msg->n_pvp_masks = 8;
    msg->unk1 = 1;
    GameConnection_SendMessage(conn, buffer, sizeof(*msg));
}
```

Note what it does *not* do: it declares `n_pvp_masks = 8` and never writes
`pvp_masks[]`, so eight zero dwords go out from `BuildMsg`'s memset. And
`skill1..skill8` are SQLite columns that **default to 0 and are never assigned
anywhere in the codebase** — no `UPDATE` statement touches them, and no CMSG
handler exists to set them. UPSTREAM. The trailing `unk1 = 1` is uncited.

**The cast lifecycle** — all five defined, none ever sent by any reference server:

| Opcode | Name | Wire shape | Bytes |
|---|---|---|---|
| 226 / `0x00E2` | `SKILL_INTERUPTED` *(sic)* | agent_id, u16 skill_id, u32 | 12 |
| 227 / `0x00E3` | `SKILL_CANCEL` **and** `SKILL_ACTIVATED` | agent_id, u16 skill_id, u32 | 12 |
| 228 / `0x00E4` | `SKILL_ACTIVATE` | agent_id, u16 skill_id, u32 | 12 |
| 229 / `0x00E5` | `SKILL_RECHARGE` | agent_id, u16 skill_id, u32, u32 recharge | 16 |
| 230 / `0x00E6` | `SKILL_RECHARGED` | agent_id, u16 skill_id, u32 | 12 |

**Opcode 227 is defined twice, under two names, on consecutive lines of
`opcodes.h:266-267`.** The verifier's duplicate scan confirms it is the *only*
duplicated GAME_SMSG number in the file. This is not obviously a bug: the
extracted client dispatch table gives **226 and 227 the same handler RVA
`004E6610`** while their neighbours (225 → `004E65F0`, 228 → `004E6630`) differ,
and Headquarter's handler for `SKILL_ACTIVATED` declares its payload struct with
the name `SkillCancel` (`code/client/skill.c:133`). The author knew. Whether
cancel and activated are one context-dependent message or a copy-paste error is
**UNVERIFIED** — but anyone importing this table gets a silent collision.

GWCA's independent naming for the same numbers matches, and adds field names the
ldufr side lacks:

```c
struct SkillActivate  { uint32_t agent_id; uint32_t skill_id; uint32_t skill_instance; };
struct SkillRecharge  { uint32_t agent_id; uint32_t skill_id; uint32_t skill_instance; uint32_t recharge; };
struct SkillRecharged { uint32_t agent_id; uint32_t skill_id; uint32_t skill_instance; };
```

That third field, **`skill_instance`**, is the single most useful unknown in this
document for anyone building an execution engine. It appears in all three
lifecycle messages, recurs in GWLP-R's 2013 templates under the same name, and
has no counterpart in OpenTyria's structs. It reads as a cast-correlation handle.
Its semantics are NOT FOUND.

**Effects, conditions, enchantments** — six messages, 63-68, all defined, none
ever sent by any reference server:

| Opcode | Name | Wire shape | Bytes |
|---|---|---|---|
| 63 / `0x003F` | `EFFECT_UPKEEP_ADDED` | agent_id, agent_id, u16, u32, u32 | 20 |
| 64 / `0x0040` | `EFFECT_UPKEEP_REMOVED` | agent_id, u32 | 10 |
| 65 / `0x0041` | `EFFECT_UPKEEP_APPLIED` | agent_id, agent_id, u16, u32, u32 | 20 |
| 66 / `0x0042` | `EFFECT_APPLIED` | agent_id, u16, u32, u32, u32 | 20 |
| 67 / `0x0043` | `EFFECT_RENEWED` | agent_id, u32, u32, u32 | 18 |
| 68 / `0x0044` | `EFFECT_REMOVED` | agent_id, u32 | 10 |

There is **no message named CONDITION, ENCHANT, HEX, AURA or BUFF anywhere in the
GAME_SMSG list.** Conditions and enchantments ride the `EFFECT_*` family, tagged
by a type code. The only source that names the type codes is Headquarter:
`EFFECT_APPLIED` = `{agent_id, u16 skill_id, u32 effect_type, u32 effect_id, u32
duration-as-float}` with **0 = condition/shout, 8 = stance, 11 = maintained
enchantment, 14 = enchantment/nature ritual**. Single-source, uncited.
RECONSTRUCTION. GWCA corroborates only the field *shape*, naming the third field
`attribute_level` rather than `effect_type` — a **CONTESTED** field name in the
one message that would carry a condition.

**Energy, health, regeneration, and most of casting** are not dedicated messages
at all. They ride a generic property channel:

| Opcode | Name | Wire shape |
|---|---|---|
| 159 / `0x009F` | `AGENT_PROPERTY_UPDATE_INT` | **u32 prop_id first**, then agent_id, u32 value |
| 160 / `0x00A0` | `..._INT_TARGET` | prop_id, agent_id, agent_id, value |
| 161 / `0x00A1` | `AGENT_PROPERTY_PLAY_EFFECT` | Vec2, u16, agent_id, u16, u8, u8 |
| 162 / `0x00A2` | `AGENT_PROPERTY_UPDATE_FLOAT` | prop_id, agent_id, float |
| 163 / `0x00A3` | `..._FLOAT_TARGET` | prop_id, agent_id, agent_id, float |
| 164 / `0x00A4` | `AGENT_PROJECTILE_LAUNCHED` | agent_id, Vec2, u16, u32, u32, u32, u8 |

Note the field order: **`prop_id` comes before `agent_id` on the wire.**

The property vocabulary is a 66-entry enum (`GmAgentProperties.h`). The
skill-relevant entries:

```
Energy = 41    Health = 42    EnergyRegen = 43    HealthRegen = 44
CastSkill = 60    InterruptSkill = 59    CastAttackSkill = 50    CastTimeModifier = 61
SkillDamage = 10    ApplyAnimation = 22    ApplyAnimationLoop = 28
ApplyAura = 6    RemoveAura = 7    ApplyEffect1 = 20    ApplyEffect2 = 21
Knockdown1 = 35    Knockdown2 = 63    AttackFail = 38    InterruptAttack = 49
```

**This vocabulary is the one place in the whole pass where three lineages agree
across thirteen years.** GWLP-R's `GenericValue.java` (2013) lists Energy = 41,
Health = 42, EnergyRegen = 43, HealthRegen = 44, SkillDamage = 10, CastSkill = 60,
InterruptSkill = 59, CastAttackSkill = 50, CastTimeModifier = 61 — the same
ordinals, in an unrelated codebase, a decade earlier. GWCA's `GenericValueID`
adds `skill_finished = 58`, `energy_spent = 62`, `instant_skill_activated = 48`,
`attack_skill_activated = 50`, `attack_skill_finished = 46`, `knocked_down = 63`.
Both sources also flag their own ignorance honestly: 14 of GWLP-R's 66 ordinals
carry `// TODO: Generic Value missing!`, and 14 of OpenTyria's 66 are named only
by their number (`AgentPropertyValue_1`, `_Value13`, `_Value18`, …).

If Rurik ever builds a skill-effect oracle, **this enum is its vocabulary**, and
it is the best-corroborated thing in this document after the record layout.

**Account state**

| Opcode | Name | Shape | Wire max |
|---|---|---|---|
| 29 / `0x001D` | `PVP_UPDATE_UNLOCKED_SKILLS` | header + array32[128] | 516 bytes |
| 219 / `0x00DB` | `UPDATE_UNLOCKED_SKILLS` | header + array32[128] | 516 bytes |

Both are sent by OpenTyria, both read the **same** `unlocked_skills` bitmap —
that server draws no PvE/PvP distinction. Neither message carries an agent id.
128 dwords is **4,096 bits**, comfortably covering the ~3,443-entry id space.

**Do not copy OpenTyria's unlock path.** The verifier found five stacked defects:
`bitmap_length` passes a byte count where an element count is expected and reads
`bitmap[127]` out of bounds on a 32-element array; the returned value is a *bit*
index used as an *element* count; `_bitmap_bitlen` returns the index of the lowest
set bit rather than a bit length; `set_bit` assigns instead of OR-ing (destroying
31 bits); `clear_bit` assigns `~(1<<pos)` (setting 31 bits). None of it was ever
noticed because **`bitmap_set_bit` and `bitmap_clear_bit` have zero call sites in
the entire repository** — at the pinned commit, OpenTyria unlocks nothing at all.

**Unmapped protocol sitting inside the skill block.** 249 of the 487 GAME_SMSG
format tables have no name in `opcodes.h`. Ten of the unnamed ones sit inside or
beside the skill block, all with real client handler RVAs. Three are worth
flagging:

- **211** (`0x00D3`): `header + array32[128]`, declared 518 — **byte-identical in
  shape to both unlock-list messages**, three slots before `SKILLBAR_UPDATE_SKILL`.
  A third unlock-list-shaped message nobody has named.
- **231** (`0x00E7`) and **232** (`0x00E8`): sit immediately after
  `SKILL_RECHARGED` and share the lifecycle shape (231 is exactly
  `agent_id, u16, u32`). The best candidates for the "skill done" and "instant
  skill" messages the named catalogue lacks.

### Client → server

Weaker evidence — no RVAs, no C structs, and **not one of these is dispatched by
any reference server**.

| Opcode | Name | Wire shape | Bytes |
|---|---|---|---|
| 14 / `0x000E` | `ATTRIBUTE_DECREASE` **✓ CONFIRMED** | agent_id, **sequence**, **attribute** | 14 |
| 15 / `0x000F` | `ATTRIBUTE_INCREASE` **✓ CONFIRMED** | agent_id, **sequence**, **attribute** | 14 |
| 16 / `0x0010` | `ATTRIBUTE_LOAD` **✓** | agent_id, **ids[]**, **ranks[]** (16 max, not 64) | 142 decl. |
| 28 / `0x001C` | `HERO_USE_SKILL` | agent_id, u32, u32, agent_id | 18 |
| 41 / `0x0029` | `DROP_BUFF` | u32 | 6 |
| **70 / `0x0046`** | **`USE_SKILL`** | **u32, u32, agent_id, u8** | **15** |
| 92 / `0x005C` | `SKILLBAR_SKILL_SET` | agent_id, u32, u32, u32 | 18 |
| 93 / `0x005D` | `SKILLBAR_LOAD` | agent_id, array32[8] | 42 decl. |
| 94 / `0x005E` | `SKILLBAR_SKILL_REPLACE` | agent_id, u32 ×4 | 22 |
| 109 / `0x006D` | `TOME_UNLOCK_SKILL` | u32, u32 | 10 |

**The first three rows stopped being weak evidence on 2026-08-19** — see
[pvpui §32](../pvpui/FINDINGS.md). Both names *and* their direction assignment are
confirmed from the client's own senders (`0x00818A90` decrease, `0x00818CE0` increase,
each reached only from the attribute panel's own minus/plus button handler in
`AttribBtns.cpp`), and the two anonymous dwords are now named: a **sequence** and an
**attribute index**. The sequence is the handle of a client-side PREDICTION the server
retires with `0x0036`. Nine live rank transitions price out exactly against
`s_attribPoints`, in both directions, with no free parameter. `ATTRIBUTE_LOAD`'s declared
142 bytes also hide a client defect: the sender clamps to 64 entries and its buffer holds
16.

`USE_SKILL`'s four fields are **unnamed in every source we have**. Headquarter
emits it as `{i32 skill_id, i32 flags, AgentId target, u8}`; apoguita's packet
sniffer guesses `skill_id, type, target_id, flags`. Neither is corroborated.
The reading "first dword is the skill id" is inference, not a sourced fact.

**The `0x8000` CMSG mask is on the wire.** `GameSrv_GetMessages` masks the raw
header only to index the format array; the unmasked value is what lands in
`msg->header` and is compared against the mask-OR'd constants in the dispatch
switch. This corroborates the movement pass's own capture finding.

**OpenTyria dispatches zero skill-related client messages.** Its switch
(`GameSrv.c:1845-1901`) has exactly 16 cases: disconnect, heartbeat, two pings,
three instance-load requests, four character-creation messages, equipped colour,
chat, move-to-coord, cancel-movement, last-position. Everything else falls to a
`default` that logs a warning and returns `ERR_BAD_USER_DATA` — **a value the
sole call site discards uninspected**. A client can send `USE_SKILL` at this
server all day; nothing happens and nothing breaks.

### What actually reaches a client at map entry

**UPSTREAM**, verified call-chain, from `GameSrv_HandleInstanceLoadRequestPlayers`
(the reply to CMSG 144 / `0x0090`), in send order:

1. `PVP_UPDATE_UNLOCKED_SKILLS` (29) — `GameSrv.c:1460`
2. `AGENT_UPDATE_ATTRIBUTE_POINTS` (55) — hardcoded 50 unused / 50 used
3. `PLAYER_UPDATE_PROFESSION` (183)
4. `PLAYER_UPDATE_UNLOCKED_PROFESSIONS` (182)
5. `SKILLBAR_UPDATE` (218) — eight zeros
6. `UPDATE_UNLOCKED_SKILLS` (219) — empty
   *(2–6 are one function, `GameSrv_SendSkillsAndAttributes`, `GameSrv.c:1469`)*

Those are **upstream's own symbol names**, quoted as it writes them. In this
repo 183 is `AGENT_PROFESSIONS` and 182 is `AGENT_PROFESSION_BITS`, named
from the client instead — see the provenance stamp further down this file.
7. `AGENT_UPDATE_ATTRIBUTES` (58) — `GameSrv.c:1473`
8. two `AGENT_PROPERTY_UPDATE_INT` + one `_FLOAT` — energy, health, regen
9. `AGENT_INITIAL_EFFECTS` (240) — always zero

None of it is in the pre-request initial burst. **Correction to a claim made
during this pass:** the same five-message block *also* fires on the
character-creation path (`GameSrv.c:1549`), in a completely different surrounding
order. If Rurik replays map-entry ordering, note also that
`PLAYER_UPDATE_PROFESSION` is sent **twice** on the map-entry path — once inside
the block and again directly at `GameSrv.c:1476`.

Several of these are stubs, and the study should not mistake them for knowledge:
`AGENT_UPDATE_ATTRIBUTES` sets `data_len = 42` and **never writes `data_buf`**, so
42 zero dwords go out; attribute points are hardcoded 50/50 for a level-0
character; `energy_per_sec` is never assigned, so regen is always 0.0; and the
world tick's regeneration arithmetic integrates permanently-zero rates into
fields that are never transmitted.

`GameSrv.c:1467-1468` preserves a comment from a live packet capture that the
**real** server sends two messages, decimal 123 and 124, between `INSTANCE_LOADED`
and the skill block — messages OpenTyria does not implement. That gap sits exactly
where the skill block begins.

### The cast lifecycle, as the only source that models it describes it

**UPSTREAM, single-source.** Headquarter is a headless *client*, so what it
implements is evidence about what a client expects:

1. client sends CMSG `USE_SKILL` (70) and **optimistically** sets
   `skill->casting = true` and `agent->casting_skill_id`;
2. server sends `SKILL_ACTIVATE` (228) → `skill->casting_confirmed = true`;
3. server sends `SKILL_ACTIVATED`/`SKILL_CANCEL` (227) → both flags cleared,
   `casting_skill_id` reset to 0;
4. server sends `SKILL_RECHARGE` (229) → `recharging = true`;
5. server sends `SKILL_RECHARGED` (230) → `recharging = false`.

Every handler bails with `LogError` if the agent has no skillbar or the skill id
is not on the bar. Note the pattern in step 1: **the client acts first and waits
for confirmation.** It is the same architecture the movement pass found — the
client predicts, the server confirms.

`SKILL_RECHARGE`'s trailing dword is the only trailing dword anywhere in the
lifecycle that gets a name: Headquarter calls it `recharge_sec`
(`code/client/skill.c:187-220`). Single-source, uncited.

---

## 3. The minimum to get one real skill on the bar, drawn correctly

**One message, and we already send it.**

`GAME_SMSG_SKILLBAR_UPDATE`, opcode **218** (`0x00DA`), payload:

| Field | Type | Value |
|---|---|---|
| header | u16 | `218` little-endian |
| agent_id | u32 | the player's agent id |
| n_skills | u16 on the wire | `8` |
| skills[8] | u32 × 8 | the skill ids, `0` for an empty slot |
| n_pvp_masks | u16 on the wire | `8` |
| pvp_masks[8] | u32 × 8 | zeros are what upstream sends |
| unk1 | u8 | `1` (upstream's uncited constant) |

75 bytes at 8/8. That is the whole of Q3 **as far as any source we have can tell
us.** The client resolves the icon, the name, the concise and full descriptions,
the energy cost, the cast time and the recharge from its own table using the id.
Nothing else crosses the wire.

**Two things to send alongside, and why:**

- **An unlock bitmap** — `UPDATE_UNLOCKED_SKILLS` (219) and/or
  `PVP_UPDATE_UNLOCKED_SKILLS` (29), `header + u16 count + count × u32`, bit *n*
  of word *n/32* meaning skill *n* is unlocked. Whether the client *refuses to
  draw* a bar skill that is not unlocked is **NOT FOUND** — no source states it
  either way. The Go server side-steps the question by sending 128 words of
  `0xffffffff`, which is a usable experiment: blanket-unlock everything, see what
  draws.
- **`SKILLBAR_UPDATE_SKILL`** (217), 13 bytes, `{agent_id, u8 slot, u16 skill_id,
  u32}` — the cheap single-slot change once a bar exists. Headquarter's handler
  requires the skillbar to already exist, so send the full bar first.

**The caveats, in the order they are likely to bite:**

1. **Our opcode numbering has never been validated against our own client.**
   `messages.json` carries `validated_against_build: null`; the one measured
   override in the repo is for a different message. And there is a *known,
   dated* renumbering in exactly this range — see §6.
2. **The skill id must exist in the client's table.** Ids run 0..3442 in the
   2026-07-26 client, with 405 unused slots scattered through the range and the
   largest gap being ids 658–762. An id in a hole has a row, but its contents are
   whatever occupies that row.
3. **The client updates its own skillbar display without waiting for the
   server.** GWCA documents this explicitly, as a bug it has to work around, and
   names the responsible UI message `kUpdateSkillbar` (`0x1000005e`). So a
   "the bar drew correctly" observation is not by itself proof the server message
   was understood.
4. **Not every row in the table is a player skill.** GWCA's own header comment:
   *"Guild Wars uses the skill array to build mods for weapons, so stuff like runes
   are skills too"*. Row selection for real skills goes by the equip/use-family
   byte at `0x33` plus the PvP flag. Rows 3418–3421 carry a not-playable flag and
   the localized name `...`.
5. **`pvp_masks[]` is unexplained.** Upstream declares eight and sends zeros.
   Whether the client needs it populated is NOT FOUND.

**A concrete first experiment**, entirely within what this document supports:
pick a Pre-Searing skill id, put it in `skills[0]`, send 219 with a bitmap that
has that bit set, and look at the bar. If the icon and tooltip render, Q1 and Q3
are both confirmed against our own client in one shot, and every claim in §1
about client-side residency graduates from CLIENT-DATA to OBSERVED.

---

## 4. The minimum to cast it and see an animation

**This one is not answerable from our sources, and it is important to say so
plainly.** No reference server in our vault implements casting. OpenTyria: no cast
state, no cast timer, no interrupt, no recharge tracking, no damage — the whole
concept is absent from the agent struct. GWLP-R: defines the wire shapes and never
constructs a single one of them. The Go server: a repo-wide search for "cast"
matches only the word "broadcast".

What the sources *do* support is a **hypothesis with named messages**, which is
worth stating precisely because it is testable in one session:

1. The client sends CMSG `USE_SKILL` (70 / `0x0046`), 15 bytes,
   `{u32, u32, agent_id, u8}` — field meanings unnamed in every source.
   **The client will not send it if its own local state says the skill is still
   recharging or the target type is wrong**; both checks run purely on
   client-resident data before any packet leaves.
2. The server answers `SKILL_ACTIVATE` (228 / `0x00E4`), 12 bytes,
   `{agent_id, u16 skill_id, u32}` — GWCA names that third field `skill_instance`.
   **This is the message most likely to start the animation**, because it is the
   only thing the server sends between the request and the completion, and the
   client already holds the skill's six animation ids locally.
3. The server ends the cast with 227 (`SKILL_ACTIVATED`/`SKILL_CANCEL`), then
   brackets the cooldown with `SKILL_RECHARGE` (229, carrying the recharge value)
   and `SKILL_RECHARGED` (230).
4. Energy expenditure and cast timing ride the property channel, not dedicated
   messages: `energy_spent = 62`, `casttime = 61` ("non-standard cast time, value
   in seconds"), `skill_activated = 60`, `skill_finished = 58`,
   `instant_skill_activated = 48` on opcode 159/162.

**Why "will the animation play" is genuinely open.** The client holds
`caster_body_animation_id` and five siblings for every skill, and it certainly
does not need to be told which animation to use. But nothing in any source
identifies what triggers it. Three candidates, none confirmed:
`SKILL_ACTIVATE` (228) alone; `AgentProperty_ApplyAnimation` (22) or
`CastSkill` (60) over the property channel; or the client self-animating on
sending `USE_SKILL` and merely waiting for confirmation — which is exactly the
architecture the movement pass established for walking, and is therefore the
hypothesis I would test first.

GWToolbox supplies one useful sidelight: it can NOP out client-side skill warm-up
timing with a two-byte patch at a scanned site. **Some cast timing is enforced in
the client**, not only server-side.

**Two named messages that would matter and that nobody sends:** `SCREEN_SHAKE`
(70 / `0x0046` SMSG, distinct from the CMSG of the same number) and
`AGENT_PROPERTY_PLAY_EFFECT` (161), the only named message pairing a world
position with an effect payload; plus `AGENT_PROJECTILE_LAUNCHED` (164), which
GWCA documents as covering "martial weapons and projectile-launching skills".

---

## 5. New skill, or re-skinned id?

**Short answer: re-skin an existing id. It is available today, it needs zero
client changes, and it is a different project by an order of magnitude from adding
a new id.**

### What the server can freely choose

Everything about **behaviour**. Nothing on the server side constrains a skill id
to mean what ArenaNet meant. In OpenTyria, `skill1..skill8` are opaque `u32`
columns copied verbatim into the wire message, and the unlock bitmap is a raw bit
index. When the server decides that using id *N* deals 40 damage and applies
Burning for 3 seconds, no source we have suggests the client checks. The client
draws the id's shipped icon and tooltip, and the mechanical outcome is entirely
whatever the server says it is.

**The consequence worth stating out loud:** a re-skinned skill's tooltip will lie.
The client renders the *shipped* description from its own table, filled in from
the shipped `scale0`/`scale15` numbers. If our Fireball does something else, the
tooltip still describes ArenaNet's Fireball. That is a design constraint on
re-skinning, not a technical obstacle.

### What the server cannot touch

| Property | Where it lives | Can a server change it? |
|---|---|---|
| Name, concise, full description | dat text records, via string ids in the PE row | **No** |
| Icon (standard and hi-res) | dat ATEX/ATTX textures, via file numbers in the PE row | **No** |
| Energy, adrenaline, health cost | PE row `0x34-0x38` | **No** |
| Activation, aftercast, recharge | PE row `0x3c`, `0x40`, `0x4c` | **No** |
| Attribute, profession, type, elite flag | PE row `0x28`, `0x29`, `0x0c`, `0x10` | **No** |
| Rank-0/rank-15 scaling shown in the tooltip | PE row `0x44`-`0x68` | **Yes, 2026-08-14** — `skilltable.py`, whole window bar `+0x50` (§4) |
| Animation ids | PE row `0x74`-`0x88` | **No** |
| Whether the id exists at all | PE table length at row 0 `+0x2c` | **No** |

Nothing in any protocol message in either direction carries any of these. That
negative was checked three ways: the ldufr SMSG catalogue was walked end to end,
GWLP-R's 907-name packet catalogue was searched, and network-log-explorer's
build-38771 name table was enumerated. **NOT FOUND, three lineages deep.**

Two further pieces of evidence that the id space is the client's to define, not
the server's:

- **New ids arrive by the client's table growing.** GWCA's `SkillID` enum gained
  `Reforged_Mode = 0xD6A` and `Dhuums_Covenant_Broken = 0xD6B` in a dated commit
  (2025-12-19), moving `Count` from `0xD6A` to `0xD6C`. Tyria-Extractor
  independently measured **one appended row, id 3442**, in the 2026-07-26
  executable versus the earlier snapshot. When ArenaNet adds a skill, they ship a
  client.
- **GWLP-R's protocol says the same thing in prose.** Its `DialogButton` packet
  documents its `SkillID` field as *"the skill displayed if skill icon is used
  else its value: 0xFFFFFFFF"* — the server sends a bare id as an **icon
  selector**, and the client is expected to already own the art.

### What adding a genuinely new id would actually require

Four separate pieces of work, in dependency order:

1. **Grow the PE skill table.** Append a 164-byte row and update the record count
   stored at row 0's `+0x2c`. The id is the row index, so ids must stay dense.
2. **Add name and description records to a `Gw.dat` text file** at
   `(string_id / 1024, string_id % 1024)`, for as many of the 11 languages as you
   care about — and update the 1,089-pointer language table in the PE if the
   target text file does not already exist.
3. **Add ATEX/ATTX icon textures to `Gw.dat`** and wire their file numbers into
   the row. This means producing the container: 4-byte magic, FourCC, dimensions,
   data-range size, subcode bitfield, then the bitstream and planar tail — ATEX
   stores undecoded block components in separate planes rather than complete DXT
   blocks.
4. **Choose animation ids** from whatever the client already has, since nothing
   we have resolves an animation id to an asset.

> **SUPERSEDED 2026-08-14. Read this before costing anything below.** The blocker
> named in the next paragraph has FALLEN, and the paragraph is left standing only
> because the reasoning around it is still good. It says writing to `Gw.dat` is
> "not a demonstrated capability in our entire evidence base" — true of the
> *mirrors*, and no longer true of this repo:
>
> * **step 2 (text records) is done** — `toolkit/mapdata/textwrite.py` wrote 188
>   authored skill-name records into text file 98 and the retail client read them
>   back off the bar (`studies/profession/RESKIN.md` §24);
> * **step 3 (icon textures) is done** — `toolkit/mapdata/iconset.py` armed 125
>   ATEX rows with generated art, on screen since 2026-08-14;
> * **step 1 (grow the PE table)** this document already calls tractable, and the
>   repo now patches six tables in that image (`toolkit/clientpatch/reskin.py`).
>
> **Only step 4 is still open**, and it is the one this document independently
> flags as the real gap: nothing anywhere resolves an animation id to an asset
> (§"Cast animations"). That is now the binding constraint on a genuinely new
> skill id, not the archive.
>
> The §5 table above should be read the same way: its "Can a server change it?"
> column is about what a server can change **at run time over the wire**, and
> every "No" in it is still correct in that sense. Four of those rows have since
> been changed **out of band** — name, icon, attribute and profession — by
> patching the PE row and writing the archive. Do not read that column as "cannot
> be changed".

**The blocker is step 2 and step 3, and it is concrete: neither mirrored dat tool
can write.** Tyria-Extractor and GuildWarsMapBrowser both open the archive
strictly read-only. There is no repack, no MFT insert and no hash-row insert
anywhere in either codebase. Writing to `Gw.dat` is not a demonstrated capability
in our entire evidence base — it is unexplored territory, not a solved problem
someone else has tooling for.

Step 1 is comparatively tractable and, notably, **is a capability this project
already has**: we patch the client binary today for the DH key
(`toolkit/clientpatch/make_custom_client.py`), and `toolkit/gwpe.py` is a
dependency-free PE reader. Growing a table in a PE we already patch is a smaller
step than it sounds.

One inference, labelled as such: the client almost certainly executes the `Gw.exe`
on disk rather than the copy at dat file 4102 — Tyria-Extractor treats them as
interchangeable and falls back from one to the other — so a PE patch would target
the on-disk executable. **Unverified**; nothing in our sources states the
relationship between the two copies.

### The honest summary

| | Re-skin an existing id | Add a new id |
|---|---|---|
| Client binary changes | none | grow the PE skill table |
| `Gw.dat` changes | none | new text records **and** new ATEX icons |
| Tooling we have | all of it | PE patching only; **no dat writer exists anywhere** |
| Tooltip correctness | wrong (shows shipped text) | correct, if you author it |
| Available today | **yes** | no |

Repurposing is not a compromise, it is the whole of R4b as far as the client
cares: ~1,300 shipped ids, each with correct art and text, waiting for behaviour
that only we can supply. Adding an id is a client-modding project that should be
scoped separately and only if authoring genuinely new content becomes the goal.

---

## 6. How far to trust these sources

**The provenance finding of this pass, and it demotes the movement study's own
lineage table:** the "ldufr" and "GWCA" groups are **not independent**.

GWToolbox's own credits name three people as authors of "the GW API used"
(`gwdevhub__GWToolboxpp/README.md:93-104`): **KAOS** (GregLando113) as original
creator, and **Ziox** (github.com/reduf) and **Jon** (github.com/3vcloud) as
major contributors. The identity chain closes on three separate tokens:

```
git -C gwdevhub__GWToolboxpp log --format='%an <%ae>' | sort -u
  Ziox            <laurent.dufresne@hotmail.com>
  reduf           <laurent.dufresne@hotmail.com>
  Laurent Dufresne <laurent.dufresne@hotmail.com>

git -C ldufr__OpenTyria log --format='%an <%ae>' | sort -u
  Laurent Dufresne <laurent.dufresne@hotmail.com>      (all 180 commits)
```

A third project outside both confirms the handle:
`Jonathan-Greve__GuildWarsMapBrowser/README.md:64` thanks
*"[Laurent Dufresne](https://github.com/ldufr)"*. And Jon Riley plus Leo
Friedrichs appear as committers in **both** Headquarter and GWToolbox —
Headquarter has only eight distinct author identities in its entire history, and
half of them are that overlap.

**GWLP-R is in the cluster too**, as its ancestor. GWCA's own header credits
*"Most low level ground work of API via the GWCA and GWLP:R projects"*
(`GWCA.h:19-20`) and its `StoCMgr.h` points readers at GWLP-R's packet wiki.

**And gw-preservation, which this pass initially nominated as the strongest
independent candidate, is not independent either — for naming.** Its
`network-log-explorer/src/lib/Constants.ts` is a 340-entry opcode→name table that
matches OpenTyria's `opcodes.h` on **337 of 340 entries, on both number and
name** — including OpenTyria's misspelling:

```
Constants.ts:263   0x00E2: "SKILL_INTERUPTED",
opcodes.h:265      #define GAME_SMSG_SKILL_INTERUPTED   (GAME_SMSG_MASK | 0x00E2) // 226
```

One `R`, in both, 337 agreements deep, with OpenTyria's file predating it by ten
months. Convergent independent reverse engineering does not reproduce a typo. That
misspelling propagates through **nine repositories** in our vault: both GWCA
mirrors, the live vendored GWCA, GWToolbox, OpenTyria, Headquarter, all three
apoguita repos, and network-log-explorer. It is the cleanest single proof that
this is one corpus.

The earlier reasoning — "we grepped for citations and found none" — was the wrong
test. Absence of attribution is not absence of derivation; the right test is to
diff the corpus.

### What that leaves

| Claim type | Genuinely independent sources |
|---|---|
| Opcode **numbering and naming** | **None.** One corpus, nine repos. |
| Skill **record layout** | Two: the cluster (GWCA) and **Fournux/Tyria-Extractor** (partial — it cites GWToolbox and Py4GW as "conceptual references", and takes its FFNA file-reference formula from GuildWarsMapBrowser, but it also *corrects* GWCA, which is what real independence looks like). |
| Skill **count** | Two, by unrelated methods: Tyria-Extractor's PE measurement (1,333 base rows) and the Guild Wars wiki (1,329 player skills). |
| **`adrenaline` at `+0x38`** | Two, and one of them is ours: our own reader over `Gw.exe`, and GWW. 115 skills, zero disagreements. The wiki shares no author or code with this cluster. |
| **Energy encoding (`11`→15, `12`→25)** | Two: our own reader and GWW, 134 skills, zero exceptions. Was the weakest CLIENT-DATA claim in this document; now the best-tested one. |
| **Skill corpus size (1,333)** | Two implementations from the spec: Tyria-Extractor (Rust) and `toolkit/clientscan/skilltable.py` (ours, Python), same structural search, identical count. |
| Capture **methodology** | gw-preservation is genuinely independent here — its `annotate.py` decodes the client's *own* runtime field-descriptor bitfield rather than consulting a hand-maintained table, and its RC4 scan signatures appear nowhere else in the vault. |
| Attribute id space | Three against one (see §1). |

### The opcode drift, which is real and dated

The numbering in this document is **post-shift**, and the shift is documented:

- GWCA commit `933975a5` (2025-12-19) renumbered every SMSG at or above `0x003C`
  by **+1**. `SKILLBAR_UPDATE_SKILL` moved `0x00D8` → `0x00D9`; the `EFFECT_*`
  family moved `0x003E..0x0043` → `0x003F..0x0044`.
- apoguita's own files witness the same event from outside: a legacy file
  committed 2026-02-02 numbers every skill opcode exactly **one lower** than its
  current (2026-06-17) tables.
- The **Go server**, which enforces client build **37600**, implements
  structurally identical messages consistently one lower in the `0x9E`–`0xF1`
  neighbourhood (`0xD9` vs `0xDA`, `0xEF` vs `0xF0`, `0x9E` vs `0x9F`, `0xA1` vs
  `0xA2`) — while matching exactly at `0x0037`, proving the shift is **localized,
  not global**.

Since gw-preservation's opcode work is its own measurement even though its *names*
are borrowed, that last row is real corroboration that the shift happened between
build 37600 and build 38771. **Our client is 38797.** ldufr's numbering — which
is what `messages.json` imported — is post-shift and therefore the right side of
the drift. That is reassuring and it is not validation.

The practical consequence of getting this wrong is worse than a missing message:
under build 38771, the slot the Go server uses for energy updates (`0x009E`) is
`AGENT_DISPLAY_DIALOG`, and the slot it uses for floats (`0x00A1`) is
`AGENT_PROPERTY_PLAY_EFFECT`. An off-by-one here does not fail silently; it
delivers an energy value into a dialog box.

### Per-source currency, for skill claims specifically

| Source | Best-evidenced era | Use it for |
|---|---|---|
| **Our own captures** | build **38797**, 2026-08-05 | The only source measured against our client. Skill coverage: three account-disclosure messages, sent by *our* stub. |
| **Fournux/Tyria-Extractor** | **2026-07-26 `Gw.exe`** — three days before our snapshot | The skill record, the string pipeline, the icon pipeline, skill counts. The most build-current skill-data source we have. |
| **GWCA (live, vendored in GWToolbox 4.7.2.3)** | dependency refreshed **2026-07-14** | Struct layouts, StoC payload structs, the UI-message vocabulary. |
| **GWCA (frozen mirrors)** | GregLando 2023-11-14, JaborGW 2024-11-30 | Implementation code the live copy no longer ships. **Both still say the record is `0xA0`/160 — a pre-2026 figure.** |
| **apoguita / Py4GW** | code written 2026, knowledge **inherited from GWCA** | Its one genuinely independent contribution is a Ghidra-sourced doc (2026-06-01) confirming the `+0x98`/`+0x9C`/`+0xA0` string-id offsets. |
| **gw-preservation** | server active past our snapshot; logger tracks build eras | Methodology and the build-37600 comparison point. Not naming. |
| **ldufr (OpenTyria / Headquarter)** | OpenTyria last touched 2026-02-21, cosmetically | The wire catalogue, the map-entry order, the only cast-lifecycle model in existence. |
| **GWLP-R** | **2013 client** | The property-value vocabulary and the attribute table. Not opcode numbers. |

**Housekeeping consequence for our own repo:** `PLAN.md:239` and
`vault/research/2026-08-04/client-data-tables.md:92` both record `GW::Skill` as
160 bytes. That is the 2023 figure. The current client's record is **164**, and
the three string ids sit four bytes later than those documents say.

### One method not to reuse

`git log --reverse -1` does **not** return a repository's first commit — the `-1`
is applied before the reverse. Used on both GWCA mirrors during this pass, it made
each look like a single-day repository; GregLando's actually runs from 2015-10-03
across 1,555 commits. The staleness conclusions survived, the characterisation did
not. Correct form: `git log --reverse --format=... | head -1`.

---

## 7. What we own, and what we have actually seen

**OBSERVED, and it is a thin list.** Across 127 capture files and 603 distinct
message labels, exactly three skill-adjacent opcodes appear, all sent by **our own
stub server** to our patched client (build 38797) during the map-load handshake:

| Opcode | Label | Payload |
|---|---|---|
| 29 | `PVP_UNLOCKED_SKILLS` | 516 bytes: `1d00` `8000` then 128 zero dwords |
| 24 | `PVP_UNLOCKED_HEROES` | 36 bytes: opcode, count 8, then 8 × `0xffffffff` |
| 27 | `PVP_ITEM_STREAM_END` | 2 bytes, bare header |

Canonical instance: `vault/captures/authsrv/authsrv-20260805T104326-c13.jsonl:15-17`,
session 2026-08-05, recurring in 25 of the 127 files.

**A correction that matters, because it was wrong in the brief for this pass and
in our own notes:** opcode 29's payload is **not** "128 bytes of zero" and it is
not a bitmask *on the wire*. It is `u16 opcode` + `u16 count = 128` + **128 zero
`uint32` words** = 516 bytes. The count-then-array shape matches both OpenTyria's
`skills[]` array and the Go server's marshaller exactly. Anyone implementing
against "a 128-byte bitmask" would produce a malformed message.

**No skill-bar content, no skill use, no skill effect, and no cast has ever
crossed the wire in any session we have recorded** — in either direction. Our
character has an empty bar and every session ends during the early handshake. The
client, for its part, sends nothing skill-related either.

> **[Superseded 2026-08-20.** True when written — every session then ended in the
> early handshake. The live corpus has since grown to 14 captures, and it now
> holds **44 `USE_SKILL` (0x0046) episodes across 7 distinct skill ids**, with
> full activate/recharge/property bookkeeping — §16–§24 below are built on
> them. This sentence kept reading as current for ten days; the correction is
> dated so it cannot again.]

**A caveat on the OBSERVED tier itself.** The bytes in our captures are ours; the
*names* attached to them are OpenTyria's. Our label table matches ldufr's
`opcodes.h` precisely where ldufr disagrees with the rest of the cluster — our
captures label opcode 183 `PLAYER_UPDATE_PROFESSION`, which is OpenTyria's
number, while GWCA and Py4GW both put that message at 182. So "SMSG 29 =
PVP_UNLOCKED_SKILLS" is **observed bytes with a sourced name**, not an
independent observation. Worth stamping the label table with its provenance.

**Stamped, and the label lost, 2026-08-19.** `183` is `AGENT_PROFESSIONS` and
`182` is `AGENT_PROFESSION_BITS` in `schema/overrides.json`, both named from
the client's own code rather than from any lineage's header
([../pvpui/FINDINGS.md](../pvpui/FINDINGS.md) §30), and the server renamed
its constants to match. The OpenTyria names listed above are left as
written: they cite upstream's own source, and are not a claim about retail.

**Reusable infrastructure** for a skills experiment, all opcode-family-agnostic
and none of it skill-specific today: the capture and client-driving harness
(`toolkit/harness/drive_client.py`, `admin.py`, `rawlisten.py`, `tcptable.py`),
the patched-client builder (`toolkit/clientpatch/make_custom_client.py`,
`make_run_dir.py`), the schema importer (`toolkit/schema/import_msgdefs.py`), the
PE reader (`toolkit/gwpe.py`), and the binary scanner
(`toolkit/clientscan/protoscan.py`) — which has never been reported against
skill-related symbols and structurally could surface them.

**A provenance single point of failure worth fixing:** the binding between our
client's SHA-256 (`221c13772c7a`) and its numeric build number (38797) exists
only as prose in `studies/handshake/PLAN.md:82-88`. The snapshot `MANIFEST.json`
has no field for the ArenaNet build number at all.

---

## 8. Open questions

Ordered by how much they would change what we do next.

| Question | What would answer it |
|---|---|
| Does our client accept opcode 218 and draw a real skill? | Put one id in `skills[0]` and look. One session. This is the whole pass's headline experiment and it validates §1 and §3 at once. |
| Does the client require a skill to be unlocked before it will draw it on the bar? | Same session, twice: once with the unlock bit set, once without. NOT FOUND in every source. |
| ~~What actually triggers the cast animation — 228, a property update, or the client's own prediction?~~ | **ANSWERED 2026-08-15: AGENT PROPERTY 60.** And it was answered exactly the way this row said to — send each in isolation and watch. Two caged loopback runs on build 38833, identical in every respect (same bar, same map 90, same hold, the message under test firing at t≈10.85 in both) and differing ONLY in which message followed the bar: `cast_228_only` sent `0x00E4` at the local player and the operator saw **nothing**; `cast_prop60_only` sent property 60 with the same skill id and the operator saw **the cast sparkle on the weapon**. Captures `authsrv-20260815T184213-c1.jsonl` and `authsrv-20260815T184317-c1.jsonl`. So **228 is bookkeeping** — which is what its handler said statically (it compares the named agent against the local player and returns before reaching AgentView) and what the LIVE WIRE independently implied: all 7 `0x00E4` in the live corpus name the receiving connection's own player, so ArenaNet broadcasts it uniformly and relies on that discard (`studies/combat/PLAN.md` §6 step 0a, §16). Three witnesses — handler, wire, screen — agreeing. The row's own guess, client prediction, is refuted: the animation needs a message, and property 60 is it. |
| What is `skill_instance`, the third dword in all three lifecycle messages? | NOT FOUND in every lineage. Only a real capture of a real cast would settle it, and there is no real server. |
| Which of `0x90` and `0x94` is the high-resolution icon? | Tyria-Extractor and GWCA disagree. Decode both file numbers for one skill and compare dimensions. |
| Is the energy encoding really just 11→15 and 12→25? | Two sources assert it, neither measured it, neither tests it. Decode the `0x35` byte for a known 5-energy and a known 10-energy skill. |
| Are opcodes 231 and 232 the missing "skill done" / "instant skill" messages? | They sit immediately after `SKILL_RECHARGED` with the lifecycle shape and have real client handler RVAs. Nobody has named them. |
| What is opcode 211 — a third unlock-list-shaped message? | Same shape as both unlock messages, three slots before the skillbar block, unnamed in every source. |
| Do our client's opcode numbers match ldufr's post-shift table at all? | Only dumping the client's own packet-template table settles it. Everything in §2 is provisional until then. |
| What did the real server send at decimal 123 and 124 during map load? | OpenTyria preserves a capture-derived note that they exist and does not implement them. They sit exactly where the skill block begins. |
| Can `Gw.dat` be written at all? | No tool in our evidence base can. This gates the entire "new skill id" project and is unexplored. |
| Is the dat's file 4102 the same image as the `Gw.exe` we run? | Tyria-Extractor treats them as interchangeable and never says why. Compare hashes. |

The shape of this document is that **§1 is well-evidenced and §4 is not**. We know
where skill data lives with four sources and three methods behind us. We know what
the messages look like from one corpus wearing nine hats. We know how casting works
from a single headless client that models it and a single reference server that
does not implement it at all.

And the one thing we could check cheaply — whether our own client draws a real
skill when we send it opcode 218 — has never been tried.

**Four of these were answered on 2026-08-06 by reading the client's handlers.
See [studies/skillcast/FINDINGS.md](../skillcast/FINDINGS.md).** In short:
`skill_instance` is the bar slot's **copy index** and ArenaNet calls it `copy`
in a log string; **218's second array is not `pvp_masks`**, it fills that copy
field; **231 is "skill disabled" and 232 is a fractional recharge**, neither is
"skill done"; the **cast animation comes from agent property 60**, not opcode
228, whose handler does nothing at all when it names the local player; and
opcode 211 writes a bitmap nothing in the image reads. All of it is static —
SOURCED at best, never OBSERVED — and that study ends with six committed probes
that would settle it against a real client.

---

# OBSERVED, 2026-08-05: the first results measured against our own client

Everything above this line was written without launching a client. This section
was produced by running §3's "concrete first experiment" and then a follow-up,
against build 38797 on our own server. It is the only part of this document
labelled **OBSERVED** — we watched it happen — and where it contradicts what is
above, the observation wins and the earlier text is left in place for the record.

Method: `toolkit/authsrv/authsrv.py` gained a skill block (opcodes 29, 219, 218)
sending eight real Warrior ids read out of this build's own table;
`toolkit/clientpatch/repoint_skill.py` rewrote individual fields of individual
skill rows in a copy of `Gw.exe`. Two launches, three screenshots each. The four
skills used, identified BY the experiment rather than assumed: **316 "To the
Limit!", 317 Battle Rage, 318 Defy Pain, 319 Rush.**

## 1. §3 was right, and its caveats did not bite

**One message put eight real skills on the bar, drawn correctly.** The client
rendered eight distinct icons with correct names, energy costs, adrenaline costs,
recharge times, skill types and attributes — from nothing but eight bare `uint32`
ids in a 75-byte message.

- **`GAME_SMSG_SKILLBAR_UPDATE` = 218 / `0x00DA` is correct for build 38797.**
  So are `UPDATE_UNLOCKED_SKILLS` = 219 and `PVP_UPDATE_UNLOCKED_SKILLS` = 29.
  §3's first caveat — "our opcode numbering has never been validated against our
  own client", `messages.json` carrying `"validated_against_build": null` — is
  now discharged for these three. It remains true for every other opcode.
- **The wire shape is exactly as computed**: 75 bytes at 8/8 against a declared
  79, the two-byte difference per array being the `u16` count the packer writes.
  516 bytes each for 29 and 219.
- **Unlock state was not a gate, or was satisfied.** We blanket-set 128 words of
  `0xFFFFFFFF` precisely so it could not be a confounder, so §3's open question —
  whether the client refuses to draw a locked skill — is still **NOT FOUND**. It
  is now cheap to answer: send the bar with an empty bitmap and look.
- **Ordering:** we sent the unlock lists BEFORE the bar, where upstream sends the
  bar first. It worked. Whether upstream's order also works is untested.

## 2. The icon question is settled, and every source we have is wrong

§1 recorded this as **CONTESTED**: Tyria-Extractor documents `+0x8c` as the
standard icon and `+0x90` as high-resolution; GWCA names `+0x8c` `icon_file_id`
and `+0x94` `icon_file_id_hi_res`; GWToolbox is not self-consistent across its
own three call sites.

**MEASURED: the skillbar draws `+0x90`.**

Three skills were repointed at Rush's art, one variable each, with real Rush in
the adjacent slot as the reference:

| Slot | Skill | Field changed | Result |
|---|---|---|---|
| 1 | 316 | `+0x8c` only | **unchanged** |
| 2 | 317 | `+0x90` only | **became Rush's icon** |
| 3 | 318 | both | became Rush's icon |
| 4 | 319 | none | reference |

The field every source calls the standard or primary icon has no effect on the
bar. An earlier, messier run agreed once the result is known: a slot with only
`+0x8c` changed did not move, and a slot with both changed did.

**What this does not say.** `+0x8c` is populated in 3,439 of 3,443 rows and pairs
one-to-one with `+0x90`, so it is certainly *something* — plausibly the icon used
somewhere we did not look (skill list, hero panel, a different UI scale). All
that is established is the bar, at this resolution. `+0x94` remains untested and
is populated in only 86 rows.

**Consequence for re-skinning: a borrowed icon needs `+0x90`, and repointing
`+0x8c` alone does nothing visible.**

## 3. Descriptions are templates, and the numbers come from the target row

§1 states this from two lineages; it is now watched. Skill 322 was given 318's
name/concise/description string ids and nothing else:

| | real Defy Pain (318) | 322 wearing Defy Pain's text |
|---|---|---|
| tooltip | Elite Skill. **(20 seconds.)** You have **+90** maximum Health, +20 armor, and take **-1** less damage. (Attrib: Strength) | Melee Attack. **(0 seconds.)** You have **+10** maximum Health, +20 armor, and take **-0** less damage. (Attrib: Strength) |

Same template, different numbers — the placeholders were filled from **322's own**
`duration`/`scale`/`bonusScale` fields, not the donor's. `+20 armor` is literal
text in the template and is identical in both, which is the control.

The same held for Rush: id 323 wearing Rush's text printed *(2 seconds)* from its
own `duration0 = 2`, where real Rush prints *(8 seconds)* from its own `8`. Its
attribute line read Tactics — 323's own `+0x29` — against Rush's Strength.

**So text and numbers are completely independent.** The skill type word ("Melee
Attack" vs "Elite Stance"), energy, adrenaline, recharge, attribute and every
scaling endpoint stayed with the target row while the prose came from the donor.

## 4. Which numbers render green, and why

The owner noticed that a cloned Defy Pain showed **one** attribute-scaled (green)
value where the real one shows **two**, and asked whether "number of raisable
values" is a skill property. It is, and it is `skill_arguments` at **`+0x58`** —
GWCA's comment reads "1 duration set, 2 scale set, 4 bonus scale set", and it is
a bitfield.

But the bit alone is not the rule. MEASURED:

| id | `args` | sets enabled | rank-0 → rank-15 | green |
|---|---|---|---|---|
| 318 Defy Pain | 7 | duration, scale, bonusScale | 20→20, 90→300, 1→10 | **2** |
| 322 clone | 2 | scale | 10→40 | **1** |
| 316 "To the Limit!" | 7 | duration, scale, bonusScale | 10→20, 10→60, 1→6 | **3** |
| 319 Rush | 1 | duration | 8→20 | **1** |

**A value renders green when its set is enabled AND its two endpoints differ.**
Defy Pain's duration is enabled but constant at 20→20, so it prints without being
green — which is exactly the missing second green number.

**[OBSERVED/CORROBORATED] 2026-08-14 — this table is now reproducible by a
script, and a third witness agrees with all of it.** For two days these four rows
were the only reading of `+0x44`..`+0x68` in the repo and **nothing here could
regenerate them**; `skilltable.py` decoded exactly one field inside the window
(recharge, `+0x4C`). It now decodes the whole window as u32 — `duration0/15`
(`+0x44`/`+0x48`), `skill_arguments` (`+0x58`), `scale0/15` (`+0x5C`/`+0x60`),
`bonus_scale0/15` (`+0x64`/`+0x68`) — and reproduces every number above
byte-exact (`test_skilltable.py` §7, which also asserts the green rule rather
than leaving it as prose). `+0x50` stays **NOT FOUND**: neither upstream source
names it and nothing here resolves it.

The third witness is GWW, crawled 2026-08-14, which shares no author, code or
ancestry with either the client binary or Tyria-Extractor's spec. Every endpoint
its `{{Skill progression}}` templates list matches (§8):
WIKI (GWW, "Defy Pain", rev. 2026-08-14) `+ Maximum health` 90→300 and
`Damage reduction` 1→10, with duration absent from the progression because the
description says a flat "For 20 seconds";
WIKI (GWW, `"To the Limit!"`) `Max foes` 1→6, `Duration` 10→20,
`+ Max health` 10→60; WIKI (GWW, "Power Attack") `+ Damage` 10→40;
WIKI (GWW, "Rush") `Duration` 8→20.

**Rush is the row that proves the bitfield is load-bearing.** Its scale slot
holds **25** — the constant in "move 25% faster" — with its scale bit CLEAR, and
the wiki lists no scale progression for it. A decode that read endpoints and
skipped `skill_arguments` would invent a green the game does not draw, so the
test checks both directions: every listed endpoint must match, and no unlisted
set may render.

## 5. Two corrections to §1

**The adrenaline conversion is not a division.** *(Superseded by §10 below, which
settles it as `ceil(raw/25)` and walks back the overstatement in this
paragraph's original heading — the 25-unit figure is correct and is corroborated
by an independent source; only the division was wrong. Left in place because the
reasoning here is what motivated the probe.)* §1 records, from
Tyria-Extractor and with a unit test behind it, that `adrenaline` at `+0x38` is in
internal units of 25 per displayed strike. Three observations refute the division:

| skill | raw `+0x38` | client displayed | raw/25 |
|---|---|---|---|
| Battle Rage (317) | 80 | **4** | 3.2 |
| Rush (319) | 80 | **4** | 3.2 |
| Defy Pain (318) | 120 | **5** | 4.8 |

Both `ceil(raw/25)` and `floor(raw/25)+1` fit all three; they diverge only on
exact multiples of 25 and none of these is one. The table holds 18 distinct
non-zero values (20, 25, 50, 60, 75, 80, 100, 120, 125, 130, 140, 150, 160, 175,
200, 220, 240, 250) and they are not all multiples of 25, so the clean-division
model was never going to hold. **One observation of a skill whose raw value is an
exact multiple of 25 would discriminate.** §1's own warning that this field is
"CLIENT-DATA, uncorroborated by measurement" was well placed.

**The elite border is `special` (+0x10) bit `0x4`, not part of the icon.** When
two elite skills had their icons repointed to a non-elite skill's, they kept
their golden borders. MEASURED: `special == 0x00000004` for Battle Rage and Defy
Pain, `0x00000000` for "To the Limit!" and Rush.

## 6. What this means for §5, "New skill, or re-skinned id?"

§5's honest summary says a re-skinned skill's tooltip "will lie, because the
client renders the shipped text", and lists name, description and icon under
"what the server cannot touch" with **No** in every row.

That is still true **of the server**. It is not true of the project, because we
already patch the client binary for the Diffie-Hellman key, and the same patcher
can repoint a skill row's string ids and icon file ids at any other skill's:

| Property | Server can change? | PE repoint can borrow? |
|---|---|---|
| Name | No | **Yes** — observed |
| Concise / full description | No | **Yes** — observed |
| Skillbar icon | No | **Yes**, via `+0x90` — observed |
| Energy, adrenaline, recharge, activation | No | yes, though untested here |
| Attribute, profession, type, elite flag | No | yes, though untested here |
| Numbers filling the description | No | they follow the row, not the text |

**A re-skinned skill's tooltip no longer has to lie.** Its name, its prose and its
bar icon can all be borrowed from any of the ~1,300 shipped skills, with no
`Gw.dat` write, no injected DLL and no new content — only the client patching this
project already performs. What cannot be borrowed is text that no shipped skill
contains, and that is where `studies/datwrite/FINDINGS.md` picks the story up.

## 7. Where this leaves the caveats §3 raised

| §3 caveat | Status |
|---|---|
| Opcode numbering never validated | **discharged** for 218/219/29 on build 38797 |
| Skill id must exist in the client's table | held; ids were read from the table itself |
| Client updates its own skillbar without waiting for the server | not contradicted, and not separable here — but the bar was empty until we sent 218, so the server message is doing the work |
| Not every row is a player skill | avoided by filtering on profession and icons |
| `pvp_masks[]` unexplained | still **NOT FOUND**; eight zeros worked |

## 8. Reproducing this

```bash
python toolkit/authsrv/authsrv.py --skills 316,317,318,319,320,321,322,323
python toolkit/clientpatch/repoint_skill.py --show 318
python toolkit/clientpatch/repoint_skill.py --target 316 --donor 319 --fields icon2
```

`repoint_skill.py` never writes in place by default, refuses anything under
`C:\gw`, locates the table structurally rather than by address, and cross-checks
the result against ArenaNet's own `ConstSkill.cpp` / `arrsize(s_skill)` strings
sitting immediately after the table. The run dir keeps `Gw.exe.pre-repoint` as
the pristine patched binary; the firewall cage is scoped to the literal path
`…\Gw.exe`, so a repointed build must be swapped over that name rather than run
under its own, or it runs uncaged.

## 9. The unlock bitmap gates the skill picker, not the skillbar

§3 left this **NOT FOUND**: *"Whether the client refuses to draw a bar skill that
is not unlocked is NOT FOUND — no source states it either way."* The first pass
side-stepped it by blanket-setting all 4,096 bits, exactly so it could not be a
confounder.

**Probe.** Same eight skills on the bar; unlock bitmap with **four** bits set —
316, 318, 320, 322, which are slots 1, 3, 5, 7. An alternating pattern was chosen
because it is unmistakable at a glance and cannot be confused with "the bar failed
to load".

**OBSERVED: all eight icons drew.** The unlock state did not suppress a single
one. What it did control was the **Skills and Attributes panel** (`K`), which
listed exactly the four unlocked skills and nothing else, grouped by attribute:

| Panel entry | shown cost | id | matches the row |
|---|---|---|---|
| Defy Pain (Strength) | 5 adrenaline | 318 | attr 17, adren 120 |
| Power Attack (Strength) | 5 energy / 3 recharge | 322 | attr 17, energy 5, recharge 3 |
| Hamstring (Swordsmanship) | 5 energy / 10 recharge | 320 | attr 20, energy 5, recharge 10 |
| "To the Limit!" (Tactics) | 5 energy / 10 recharge | 316 | attr 21, energy 5, recharge 10 |

**The division is clean and it is the useful one: bar contents are the server's,
the unlock list is the player's.** A server can place any skill on any bar
regardless of unlock state; the bitmap decides only what the player may pick for
themselves. For a private server this means the unlock list is optional
scaffolding, not a gate to be fought.

One inconsistency worth recording: the panel's own eight-slot strip along its top
rendered **empty** while the action bar below it was full. That widget filters by
unlock state and disagrees with the bar it is supposed to mirror.

**A free side effect: unlocking a skill names it.** The panel prints the resolved
name, cost and attribute for every unlocked id, which is a way to identify skills
without decoding a single text record. Four ids were named this way, and the
tooltips named three more: **316 "To the Limit!", 317 Battle Rage, 318 Defy Pain,
319 Rush, 320 Hamstring, 322 Power Attack.**

**Attribute bytes, MEASURED** from those four against `+0x29`: **17 = Strength,
20 = Swordsmanship, 21 = Tactics.** §1's warning against importing OpenTyria's
attribute enum stands; these three are ours.

---

## 10. The adrenaline field is a threshold, not a strike count

§1 records, from Tyria-Extractor and with a unit test behind it, that `adrenaline`
at `+0x38` is "in internal units, 25 per displayed strike". §5 of this section
earlier called that refuted. **That was an over-correction, and this is the
settled version.**

The **unit is right**. The Guild Wars Wiki's *Adrenaline* page states the mechanic
directly: *"You gain 25 units of adrenaline (=one strike) each time you
successfully hit an opponent with a weapon"*, and *"all other skills lose one
strike (25 units) of adrenaline"*.

What was wrong is treating it as division. **`+0x38` holds a threshold in units,
and the displayed cost is the number of strikes needed to reach it:**

```
displayed adrenaline cost = ceil(raw / 25)
```

That is why the field is not always a multiple of 25 — 11 of the 18 distinct
non-zero values in the table are not (20, 60, 75, 130, 140, 160, 220, 240 among
them). A threshold can sit anywhere; the strike count rounds up.

**The probe.** Both `ceil(raw/25)` and `floor(raw/25)+1` fit the three skills
observed in §5, because they diverge only on exact multiples of 25 and none of
those three was one. A bar was built from four Warrior skills whose raw values
*are* exact multiples, so the two rules predict different numbers in every slot:

| Slot | id | raw `+0x38` | `ceil` predicts | `floor+1` predicts | **OBSERVED** |
|---|---|---|---|---|---|
| 1 | 1142 | 25 | 1 | 2 | **1** |
| 2 | 357 | 100 | 4 | 5 | **4** |
| 3 | 329 | 150 | 6 | 7 | **6** |
| 4 | 336 | 200 | 8 | 9 | **8** |
| 5 | 317 Battle Rage | 80 | 4 | 4 | 4 |
| 6 | 318 Defy Pain | 120 | 5 | 5 | 5 |
| 7 | 319 Rush | 80 | 4 | 4 | 4 |

Four for four for `ceil`, and the three controls — where both rules agree —
reported unchanged, so nothing else moved between runs. `floor(raw/25)+1` is
dead.

**A note on the wiki as a source.** It does not fit this document's existing
labels. It is community documentation of observed retail behaviour, which for a
*player-visible* mechanic is strong evidence and is genuinely **a separate lineage
from every code source in `vault/mirrors/`** — unlike the ldufr/GWCA cluster,
which shares an author and counts once. For *internal* representation it is weak:
it says nothing about `+0x38` being a threshold, and it could not have. Here the
two halves are complementary rather than redundant — the wiki supplied the game
mechanic, the client supplied the encoding, and neither alone would have produced
`ceil(raw/25)`.

---

## 11. Everything §3 left open, as of this pass

| Question | Status |
|---|---|
| Are opcodes 218 / 219 / 29 right for our build? | **Answered** — yes, build 38797 |
| Does the client refuse to draw a locked skill? | **Answered** — no; unlocks gate the picker |
| Which of `+0x8c` / `+0x90` / `+0x94` does the bar draw? | **Answered** — `+0x90` |
| How does raw adrenaline map to the displayed cost? | **Answered** — `ceil(raw/25)` |
| Are descriptions templates filled from the row's own numbers? | **Answered** — yes |
| What decides how many values render green? | **Answered** — `args` (+0x58) ∩ endpoints differing |
| Where does the elite border come from? | **Answered** — `special` (+0x10) bit `0x4` |
| What is `pvp_masks[]` for? | still **NOT FOUND**; eight zeros worked throughout |
| What is `+0x94` for? | still **NOT FOUND**; 86 rows carry it, none tested |
| Does upstream's message ordering also work? | untested — we sent unlocks before the bar |

---

# OBSERVED, 2026-08-20: the DURATION slot, read because the server had to send one

The effect substrate (`toolkit/authsrv/effects.py`, R4b) needed one number the
table does not hand over cleanly: **how long does this skill's effect last?**
§4 answered which values *render green*; this is about which values are *real*,
which turns out not to be the same question. Three findings and one
corroboration, all from the
1,333-skill player corpus plus the 102 `0x0042` applies in the live captures.

## 12. `skill_arguments` bit 1 means the duration SCALES, not that the slot is meaningful

§4 established that a value renders green when its `args` bit is set **and** its
endpoints differ, and that reading endpoints without the bit invents a
progression the game never draws — Rush's scale slot holds a constant 25 with
its bit clear. `authsrv.skill_scale_value` therefore **raises** on a disabled
set, which is right for the scale.

**It is too strong for the duration, and retail says so.** Skills **984 (Torch
Enchantment)** and **998 (Torch Hex)** have `skill_arguments = 0` — the duration
bit CLEAR — endpoints 30/30, and **ArenaNet sent `0x0042` with duration 30.0 for
both**. A server that honours the bit the strict way cannot reproduce two of
retail's own applies.

So the bit is about the **progression**, and the slot is about the **value**.
The two coincide for the scale (a scale with no progression has no meaning of
its own) and come apart for the duration (a fixed-duration skill still has a
duration). `effects.resolve_duration` splits them, and every branch it permits
names a retail witness while every branch it refuses names its zero:

| shape | n (of 1,333) | rule | witness |
|---|---|---|---|
| bit SET | 618 | interpolate `lo..hi` at the rank | 160, 364, 348, 814 |
| bit CLEAR, `lo == hi == 0` | 488 | no duration → `None` | — (nothing to send) |
| bit CLEAR, `lo == hi`, below the sentinel floor | 148 | the flat value | **984, 998 at 30.0** |
| bit CLEAR, `lo == hi`, at or above it | 30 | **REFUSE** | none — see §13 |
| bit CLEAR, `lo != hi` | 49 | **REFUSE** | **none, in 102 applies** |

The last row is the honest one. Forty-nine skills carry two differing endpoints
with the bit clear and **not one of them appears anywhere in the corpus**, so
there is no evidence for *either* reading — interpolate anyway, or take one
endpoint? The module raises rather than returning a plausible number.

## 13. The duration slot carries SENTINELS, and they are an enum in the high word

Of the 666 bit-clear skills with equal endpoints, **30 hold a value that is not a
second count**:

| value | hex | n | what they mostly are |
|---|---|---|---|
| 131,072 | `0x20000` | 22 | Enchantment |
| 196,608 | `0x30000` | 7 | Enchantment / Signet |
| 999,999 | — | 1 | Spell |

**24 of the 30 are Enchantments**, which is exactly where a *"maintained until
removed"* marker belongs — a maintained enchantment has no duration, so its slot
is free to carry something else. `0x20000` and `0x30000` are 2 and 3 in the high
word, i.e. an enum, not a magnitude; 999,999 is the other spelling of forever.

**Vital Blessing (289) is one of them, and it is on our own enemy's bar**, so
this refusal fires in every session this server runs. That is deliberate: the
alternative is putting **36 hours** on the wire as a duration. What the enum
*means* is **NOT FOUND** — no source in this repo names it, and the module keys
on the SHAPE (high word set, floor `0x10000`) rather than on the three observed
values, because it is the shape that is established.

**A follow-up with a clean answer available:** the client draws "Enchantment
Spell" and a maintained-enchantment tooltip from *somewhere*. Whatever reads
`0x20000` is the same kind of anchor `s_attrib`'s accessors were for the item
modifiers (`studies/itemmods` §2), and it would name the enum rather than leave
it as a floor.

## 14. `target` (+0x31) is a target-TYPE enum, and the type column corroborates two of its codes

The substrate needs to know whether a stance lands on the caster or on what the
caster is aiming at. `target` answers it, and the answer is checkable without
trusting any single skill, because `type_code` is an independent column:

| type | n | target distribution |
|---|---|---|
| Attack (14) | 199 | **5 → 199/199** |
| Stance (3) | 76 | **0 → 75/76** |
| Glyph (12), Preparation (19), type 16, 20, 21, 24, 26, 27 | 117 | **0 → 117/117** |
| Hex (4) | 151 | 5 → 140, then 0/1/16 |
| Enchantment (6) | 227 | 0 → 151, 3 → 52, then 1/4/5/6/14 |

An attack necessarily aims at a foe and a stance necessarily lands on the
caster, so **0 = self and 5 = the cast's target** is read off the type column
rather than asserted about any one skill. The one Stance at 5 and the three
Hexes at 0 are not explained here and are not needed.

**Codes 1, 3, 4, 6, 14 and 16 are UNRESOLVED.** 3 is plainly ally-shaped (52
Enchantments and Reversal of Fortune 307 carry it) and 4 is *also* ally-shaped
(Restore Condition 276), which is one distinction too many to guess at — so
`effects.effect_recipient` reads only 0 and lets everything else fall through to
what the caster aimed at. Known-wrong-but-bounded, rather than an invented enum.

## 15. And a corroboration of somebody else's finding, at corpus scale

`studies/isle/FINDINGS.md` rung-8 prep §2 settled **`0x0042`'s field 3 = the
applying skill's attribute RANK** on 2026-08-18, CORROBORATED against GWW across
five values and four skills. Running the same prediction over the **whole**
corpus with the client's table on the other side of the join:

> `interp(duration0, duration15, field3)` == the f32 duration on the wire, for
> **96 of 96 non-condition applies, 0 misses**.

No free parameter — the endpoints are ArenaNet's, the formula was measured at
`0x005A8920` for the *damage* scale, and field3 and the duration are retail's
bytes. This is not a new finding; it is that finding mechanised, in
`test_effects.py` §2, guarding a rule the server now depends on.

**Worth recording because of what it says about the repo rather than the game:**
`bufflog.field3_report`'s docstring still read *"the answer is one session away"*
for two days after the answer was written down in another study. That is the
fourth time in one week a measured number sat unread beside code using an
invented one — property 17, the rung-7 damage formula, the item modifiers, and
this — and all four failed the same way round: measured, written down, not
wired.

## 16. The client DRAWS them — run `20260820T174731`, and it types them itself

Everything above is offline. This is the client.

**The run.** Loopback, `--enemy --explorable`, the bar's slot 1 swapped to
**Frenzy 346** with the existing `--skills` flag (no code edit), one scripted
keypress on slot 1, 18 s of walk plan and a 60 s hold at a frame every 4 s.
`vault/captures/harness/20260820T174731`, contact sheets `hud-walk-frenzy.png`
and `hud-hold-hex.png`. **13 applies, 13 removals, zero client asserts, run
verdict PASS.**

**Both directions worked, and the whole chain is on record for the player's:**

```
key "1" -> c2s 0x8046 USE_SKILL -> 0x00E4 -> 0x00E5 (cast end)
        -> 0x0042 EFFECT_APPLY(stance 346 on agent 1, buff 3, 8.0s at rank 0)
        -> ... 8s ... -> 0x0044 EFFECT_REMOVE(buff 3, expired after 8.0s)
```

and the enemy's, needing no input at all:
`0x0042 EFFECT_APPLY(hex 253 on agent 1, buff 1, 18.0s at rank 12)`.

**THE CLIENT TYPES THE EFFECT ITSELF, FROM THE SKILL ID.** We send no colour,
no category and no art — `0x0042` carries `[target, skill, rank, buff,
duration]` and nothing else. The client drew Frenzy's own icon under a **GREEN**
border and Scourge Sacrifice's under a **MAGENTA** one, which are GW's stance
and hex colours. So the whole `type_code` taxonomy §14 reads out of the table is
something the client already knows per skill id, and a server that gets the id
right gets the category, the art and the tooltip for free.

**The timer bar is real and it drains on OUR number.** Frenzy is the row §12 is
about — `skill_arguments = 0`, endpoints 8/8, the duration bit CLEAR — so the
strict reading of the bitfield would have refused to send anything. Frames
`w002` (21:48:04) and `w003` (21:48:08) show its green bar shortening, and by
`w004` (21:48:11) **the icon is gone**: applied ~21:48:03, an 8-second
progression bar, gone at 8 seconds. The flat branch is right and the client
agrees with it on screen.

**Expiry lands inside retail's own band.** Our residuals were **+0.03, +0.05 and
+0.03 s** against the stated duration, on a world tick. The corpus's shoulder is
83 of 88 closes within 50 ms (`bufflog.EXPIRY_TOLERANCE`), so our lateness is
inside the spread retail itself produces.

**The death strip is visible.** `hold001` and `hold006` are the two death
frames: no icons at all, while `hold002`-`hold005` carry the hex with its bar
draining. Three episodes came off in one `stripped 3 effect(s)` and the client
took all three without complaint.

### 16.1 The run found a gap, the fix was wrong, and the corpus said so

**What the run showed.** The server opened **four concurrent episodes of skill
253 on the same agent** — the Hatcher re-casts every ~5 s and nothing stopped it
— and **the client never drew more than ONE hex icon.** A second run
(`20260820T175507`, frames every 2 s) pinned the client's side precisely: its
timer bar drains **monotonically** across three re-applications, from ~85% to
~28% over 8 seconds of an 18-second duration. **A repeat `0x0042` for a live
(agent, skill) is DISCARDED — no second icon, no reset.**

**The obvious fix was made and is now reverted.** Collapsing to one episode per
(agent, skill), refreshing in place, looked well-supported: the client's single
icon, plus `buff_id_report`'s peak of 2 concurrent episodes. A prediction was
stated before the run that tested it — *re-sending `0x0042` with the EXISTING
buff id resets the bar* — and it was **REFUTED**: the bar drained straight
through three same-id refreshes.

**Then the corpus refuted the collapse itself.** Asked directly whether retail
ever re-applies a live effect:

> **15 overlapping re-applications** across the live captures — a second
> `0x0042` for the same (target, skill) while the first is still live — and
> **every one carries a NEW buff id**: 120→121 at a 0.43 s gap, 110→114 at
> 0.50 s, 121→120 at 0.09 s. The first episode still closes `expired` against
> its own duration. Same-id repeats occur **only** after the previous one
> closed (51→51 at 14.98 s against a 13.0 s duration, five times over).

So ArenaNet's allocator is the plain one we already had, and collapsing would
have made our stream a shape retail never produces. `test_effects.py` §4b now
pins retail's rule instead of our fix.

**Which relocates the actual defect, and it is more interesting than a channel
bug.** Retail's fifteen overlaps are all **under 0.5 s** apart — same-instant
doubles, an AoE or a party-wide effect touching one target twice — and **not one
is a re-cast of a live effect.** Ours were five seconds apart. The thing no
monster in the corpus does is what *our* monster does:

> **our placeholder AI re-casts a hex the target already has.** `pick_skill`
> asks only whether a slot has recharged.

That is an **AI rule**, not a wire rule, and `pick_skill`'s own docstring
already says it is "a testing function, not a decision about AI" that "gets
replaced rather than extended". So it is recorded there and left alone. It also
lands exactly where `studies/heroes` §5.6 said this arc would end up: *"do not
use this skill if the target is already affected"* is precisely the sort of
condition GWW publishes **per skill**, which is R4c's open design question, not
a line to add to a round-robin selector.

**Left standing, and named:** how retail refreshes an effect at all is **NOT
FOUND**. Re-sending the apply does nothing (measured, both id choices).
`0x0044`-then-`0x0042` would certainly work and there is no evidence retail does
it. The question only becomes live when something in this server needs to extend
a running effect, and nothing does yet.

**NOT ANSWERED by this run, and named so it is not read as answered:**

1. **Whether an ADRENALINE skill can be pressed at all.** The default bar's two
   stances (Battle Rage 317, Rush 319) cost 4 adrenaline and nothing tells the
   client the player has any, so slot 1 was swapped to the 5-energy Frenzy to
   sidestep it. Whether the client greys an uncharged adrenaline skill and
   swallows the keypress is untested, and it is the cheapest reason to model
   adrenaline.
2. **What the enchantment sentinel means** (§13). Vital Blessing refused on
   every cycle of this run, loudly, exactly as designed — thirteen log lines
   naming the gap.
3. **Whether the effect does anything.** Frenzy's icon appeared; Frenzy's
   *+33% attack speed and double damage taken* are not modelled, and neither is
   Scourge Sacrifice's. The channel is the substrate; the per-skill mechanics
   are the `scale_means` pattern again, one wiki-sourced row at a time.

---

# OBSERVED, 2026-08-20 (later): five more families, and three rules the wiki had all along

§16 left the substrate carrying icons with no consequences and five of the nine
R4b families unreached. This pass closed most of that. Everything below was
measured before it was built, and three of the five were then watched at a
client.

## 17. The type list is corroborated by the table, and Glyph joins it

Adding a `type_code` to the effect list is a claim about ArenaNet's taxonomy, so
it wants a check the table can refuse. Across the **478** corpus skills in the
five effect types:

| type | n | duration resolves | refuses (sentinel/unwitnessed) | **no duration** |
|---|---|---|---|---|
| Stance (3) | 76 | 74 | 2 | **0** |
| Glyph (12) | 10 | 9 | 1 | **0** |
| Preparation (19) | 14 | 13 | 1 | **0** |
| Hex (4) | 151 | 142 | 9 | **0** |
| Enchantment (6) | 227 | 194 | 33 | **0** |

**Not one of the 478 has nothing to time.** Meanwhile **488** corpus skills DO
carry 0/0 endpoints — attacks, signets, most spells — and **none** of them is in
these five types. If "this type IS a timed effect" were the wrong mapping, the
giveaway would be a type full of skills with no duration, and there is none.

## 18. THREE of the five types are ONE-AT-A-TIME, and two say so in the game's own words

This is the answer to §16.1's open question — *how does an effect get replaced* —
and it was sitting on GWW the whole time:

> **Stance** (rev. 2020-10-23), quoting **Isokeh, Expert Ranger**, in game:
> *"Only one Stance can be active at any time, so if you are under the effects
> of a Stance, using a new Stance will replace the previous one."*
> **Preparation** (rev. 2020-06-18): *"Only one preparation can be active at a
> time. Activating another preparation will override the previous one."*
> **Glyph** (rev. 2024): *"If a glyph is cast while another glyph is already
> active, the new one replaces the old one."*

The rule is per **TYPE** and per **AGENT** — any stance replaces any stance —
and hexes and enchantments carry no such rule, which is why they are not in it.

**On the wire a replacement is `0x0044` then `0x0042`.** That is forced rather
than chosen: §16.1 measured that re-sending the apply alone is discarded by the
client under either buff id, so a replacement the client can see has to close
and reopen. **WATCHED** (`20260820T190616`, `hud-stance-swap.png`): Rush's icon
became Frenzy's **in the same slot, under the same green stance border**, with a
fresh timer, and there was never a third icon.

## 19. Property 55 is the HEALING channel, and the client's own arithmetic agrees

The server had no way to make health go up that drew anything — `GV_HEALTH` is a
silent setter. Asked directly, the corpus answers in one pass over 2,007
property events on `0x00A3`:

| property | negative | positive | self-directed (`target == cause`) |
|---|---|---|---|
| 16 (damage) | **1251** | 0 | **0 of 1251** |
| 17 (critical) | **243** | 0 | **0 of 243** |
| 55 | 4 | **502** | **454 of 506** |

Damage always has a distinct attacker and victim and is always a negative
delta — `_damage_fraction` already sent `-frac`, which turns out to be retail's
convention 1,251 times over. **A positive, overwhelmingly self-inflicted health
delta on the damage channel is a heal.** GWCA's name `armor_ignoring` therefore
describes the *mechanism* (a health change armour has no say in) and not the
*direction*; the four negatives are consistent with a sacrifice and that reading
is UNVERIFIED.

**CONFIRMED AT THE CLIENT** (`20260820T190917`, `hud-heal-54-to-100.png`). The
client's own health readout reads **54 → 100 → 54 → 100** across three Healing
Signet casts, moving by exactly the **46** the server sent each time. The client
applies property 55 as a health gain and its arithmetic matches ours.

**And it draws no number for it** — a green-text scan over twenty frames
spanning three heals finds **0–8 saturated green pixels**, the 8 being frames
taken at the keypress instant before the cast completed. Damage on 16/17 *is*
drawn. So either retail annotates a heal through some other value id, or the
client simply does not, and this repo cannot yet say which. **OPEN**, and named
rather than assumed away.

## 20. A spell is not a swing, and a label does not say *when*

Two defects the tests could not have caught, both found by running it:

- **Casting a HEX made the player swing a hammer.** `cast_tick` dispatched on
  *"is there a target"*, so Faintheartedness produced
  `attack_started: player swings at 10` and five points of hammer damage.
- **Flare dealt that same five** instead of its own 20 fire damage, because
  only the `additive` mode was ever read and `standalone` fell on the floor.

Both are fixed by dispatching on `type_code`: **only type 14 rides a weapon
swing** (WIKI, GWW "Attack skill" — attack skills *are* attacks and use the
equipped weapon; all 199 in the corpus carry target byte 5). A spell deals its
own number with no roll, no armour exponent and no critical, and sends **one**
message — no `attack_started`, no `melee_attack_finished`, because it never
began a swing.

**And the label trap that would have shipped without the type column:** GWW
gives `Ignite Arrows` the variable **`Fire damage` 3..18** — the same label as
Flare's. It is a Preparation, and its fire damage rides the *next arrows*.
Nothing in the client's table separates them. So a skill that opens an episode
resolves no damage and no heal at cast: its scale describes what the effect does
while it is up.

## 21. Conditions: the join, and the rule that they never stack

`studies/isle` established that a condition's duration comes from the
**inflicting** skill (Burning's own endpoints are 3/3 and retail sends it at
9.0). The missing half was *which* condition and *from where*, and both are
per-skill data already carried:

> **GWW's progression variable NAMES it** — `Sever Artery` has exactly one
> variable and it is called `Bleeding` — and **the client's bonus slot carries
> the seconds**, 5..25, in the slot `skill_arguments = 4` names. **The bitfield
> picked the slot before the wiki was read.**

Sever Artery at Swordsmanship 3 resolves to **Bleeding (478) for 9 s**, and the
apply names the *condition's* id rather than the skill's — which is what retail
carries, since the corpus's six condition applies name 480 and 481 and never the
skill that caused them.

**Then a run put five Bleedings on the player at once.** With the enemy's Sever
Artery on a 0 s recharge (`20260820T191725`) the pips went 3 → 6 → 9 → **10, the
cap** — twenty health a second, and visibly absurd. The rule was on GWW:

> **WIKI (GWW, "Condition" §Notes):** *"Reapplied conditions will last the
> original time period, unless the reapplied duration is greater than the
> remaining amount of time."*

So one instance per (agent, condition), and a re-application is a **comparison**,
not an addition. A shorter one is a no-op on the wire as well as in the table —
nothing about the target changed. A longer one **extends** it, as `0x0044` then
`0x0042`, which is the one replacement shape the client honours.

## 22. What a condition DOES — property 44, and one clause of B4 closed

`studies/isle` B4 CONFIRMED property 44 as the net health-regeneration rate in
max-health fractions per second, quantised at 2/H, riding **`0x00A2`** — itself a
correction to `PLAN.md` §3.3, which had it on `0x009F` (*"the value census
matches §3.3 exactly; the opcode did not"*). It left exactly one clause open:

> *"Still UNVERIFIED: that one 2 hp/s step equals one HUD pip (needs a screen,
> not the wire)."*

The pips are GWW's — *"each pip represents a loss of two health per second"*,
**Bleeding 3, Burning 7, Disease 4, Poison 4**, capped at 10 — and the other six
conditions degenerate nothing, which is a fact rather than a gap. So Bleeding on
a 100-health player must be **exactly** `-3 × 2 / 100 = -0.06` per second, with
no free parameter on either side.

**CONFIRMED AT THE CLIENT** (`20260820T192221`, `hud-degen-three-pips.png`),
and it closes B4's clause. The client drew **exactly three `‹` arrows** on the
health bar, and its own displayed health fell **100 → 86 → 72 → 58 → 44** across
frames **2.32 s** apart — an implied **6.03 health/s against the 6.00 the server
sent**, three times over. Three pips asked for, three pips drawn; 0.5%
agreement on a rate neither side was tuned to.

**Health stays server-authoritative and the ticks are silent**, which is B4's
own conclusion: *"passive ticks are never streamed"*. The server sends the RATE
once, on change, and spends the health without a single property-16 message —
a tick that also sent damage would draw a stream of red numbers retail never
draws. The client's 6.03 is that animation, done by the client from one number.
The expiry sends the rate back to zero, which is the half a server is most
likely to forget: the icon goes and the arrows stay.

---

# OBSERVED, 2026-08-20 (third pass): ENERGY has a complete wire model — and ADRENALINE has no wire at all

The energy recon ran as five parallel read-only censuses over the 14-capture
live corpus (13,378 property-channel messages, 49 connections, every one
decoding to its final byte), the pinned build-38797 client table, and the
2026-08-20 harness frames. Everything below is theirs plus two checks run by
the orchestrator; scratch scripts are named in the session log.

## 23. Energy rides four properties, and its quantum is f32(0.33) — not one third

Energy has **no dedicated opcode**. It rides the same generic property channel
as health, on the **no-target** variants only (0x009F int, 0x00A2 float —
never once on 0x00A0/0x00A3, whose only populated float properties remain
{16, 17, 55}; energy bookkeeping has no victim field because it is always
self-directed):

| property | channel | n (live corpus) | what it is |
|---|---|---|---|
| **41** | 0x009F int | 97, values {20, 22, 25, 30} | **MAX energy**, sent as the same (1, real) on-create pair as health’s 42 |
| **43** | 0x00A2 float | 52 | **regen RATE**, fraction of max per second, sent once on change — never periodic |
| **62** | 0x00A2 float | 45, all negative | **discrete SPEND**: −(energy_cost / max), once per completed cast |
| **52** | 0x00A2 float | 1 | **discrete GAIN**: the one witness is a resurrect, value exactly 1.0 |
| 33 | any | **0** | the candidate absolute setter: **NOT FOUND**, positive control green (34/44/52/55/62 all found by the identical scan) |

**The rate’s quantum, settled bit-exactly.** The corpus carries exactly five
nonzero prop-43 values. Three candidate formulas were tested against the raw
f32 bit patterns; only one reproduces all five:

| observed f32 | = f32(f32(0.33)·pips/max) | GWW armor row |
|---|---|---|
| 0.032999999821186066 | 2 pips / 20 **or** 3 / 30 (degenerate) | Warrior base — or caster before armor |
| 0.03959999978542328 | 3 / 25 | Ranger (+1 pip, +5e) |
| 0.04400000348687172 | 4 / 30 | caster basic armor (+2, +10) |
| 0.052800003439188004 | 4 / 25 | Dervish/Assassin (+2, +5) |
| 0.06000000238418579 | 4 / 22 | 4 pips over a death-penalty max |

The nominal rule — WIKI (GWW, "Energy" §Regeneration, rev 2026-03-15): *"Each
pip of Energy regeneration generates 1 Energy every 3 seconds"* — predicts
p/(3m), which matches **zero of the five** bit patterns. The wire’s constant is
**0.33 held in single precision**, not one third: `f32(0.33) × pips ÷ max`,
rounded once more to f32. Same class of result as health’s 2/H quantum
(isle B4), and the (pips, max) pairs are **exactly GWW’s basic-armor table
rows** — an independent join nobody tuned.

**The denominator is the CURRENT max, and one agent proves it by dying.**
Capture `20260817T183756`, agent 27: max 25, rate 0.0528 (= 4 pips/25). At
t=353.299 one batch carries the death bit (0x00F1 effects=16), prop 41 re-sent
**22**, prop 42 re-sent **102** — 102 is 120 × 0.85 exactly, a death-penalty
hit to the maxima — and **prop 43 driven to 0.0**: regen stops at death. At
t=363.343, 10.044 s later: death bit clears, **prop 43 = 0.06 = the same 4 pips
over the NEW max 22**, **prop 52 = 1.0** and prop 55 = 1.0 — a resurrect
refilling both pools in one instant. Four properties, one mechanism, retail
bytes. (One recon agent initially read the 25→22 as a *current*-energy spend;
the 42=102 co-occurrence in the same death batch settles it as the maxima.)

**Prop 62 is −cost/max, validated against the client’s own table with zero
exceptions.** All **45** spends in the corpus, **8 distinct skills** (105, 153,
364, 394, 780, 783, 814, 858) over three pool sizes, every one predicted
exactly from `skills.toml`’s own energy column — skill 364 ("Charge!") alone
22 times across 6 connections, always −0.25 = 5e over max 20 (the control: a
fixed denominator of 20 misses 18 of 45 across the other pools). It fires
**once** per cast, 0.03–0.7 s after `USE_SKILL` (mostly ~0.05 s), and **the
spend precedes the property-60 that names the skill in the same batch, 45 of
45** — measured because a stream-order join first scored 18 of 45 by hanging
each spend on the previous cast. **Zero-cost casts send nothing** — 0 of the
observing agent’s 44 free casts carry one. **And prop 62 is scoped to the
agent whose orb is on screen**: a 2×2 with two empty cells — the observing
player’s agent spends on 45 of 45 paid casts and 0 of 44 free ones, while
**722 casts by OTHER agents (579 of them paid) carry not one spend** — so a
server must not emit 62 for its NPCs, and ours does not. The client sends
nothing energy-shaped in the other direction: `USE_SKILL`’s four payload
fields never carry a quantity. (An earlier count in this section read 44
episodes over five skills — that was the c2s `USE_SKILL` join, which sees only
connections whose client half decodes; the s2c activation join above is the
wider net and the shipped oracle enforces its numbers.)

**The client does not predict a deduction.** Two 2026-08-20 harness runs
(`20260820T190210`, `20260820T190917`): eight presses including Flare — 5e in
retail — and the energy bar sat at 25 in every frame while health visibly
re-rendered 54→100→54 in the same frames. Our server has never had a prop-62
call site (`GV_ENERGY_SPENT` defined, zero uses), so the flat bar is the
measurement: **energy display waits for the server**. The client does zero the
orb at death client-side — and leaves it 0 after revive, because our revive
path sends no energy property where retail sends 52=1.0 + 43=rate. That is a
falsifiable prediction for the next run: emit the resurrect pair and the orb
should refill.

**Closed in passing:** `studies/isle` §9 item 6’s "skill 364… no measurable
effect" — it had one, −0.25 max-energy on prop 62 at the exact flagged
timestamp (t=1008.125, capture `20260818T132739`), a channel damagepass.py
never reads. And `content/world.toml`’s `float_43 = 0.0396` — gw-preservation’s
"REVERSE THIS MORE" constant — is now **measured**: it is f32(0.33)·3/25, the
Ranger armor row, and the identical bit pattern appears in capture
`20260810T235916` on four connections. `studies/profession/RESKIN.md` §24.1’s
counts (52: never observed; 62: n=6) were true against its twelve-capture
corpus and are superseded by this one — addendum written there.

## 24. Adrenaline: the table carries the threshold, the wiki carries the rules, and the wire carries nothing anyone has named

**The client table’s +0x38 is raw units and it is the USE threshold.** §10
measured the field (80/120/80 for Battle Rage/Defy Pain/Rush, displayed
strikes = ceil(units/25)); GWW’s own "Battle Rage" Notes: *"exactly requires
80 units… 3 strikes and 5 units"*. `skills.toml` now carries it per row as
`adrenaline_units` (extractor extended this arc).

**The rules — WIKI (GWW, "Adrenaline", rev 2026-07-02), player-visible tier:**

- Gain **25 units (= one strike) per successful weapon hit** on an opponent —
  weapon hits, not spell damage. Multi-hit attack skills grant one per hit.
- Gain **1 unit per 1% of maximum health lost** to damage, **floored** (sub-1%
  grants nothing), counted before damage reduction.
- **Each adrenal skill has its own pool; all pools grow simultaneously.**
- On USE: the used skill’s pool resets to zero and **every other skill loses
  one strike (25 units)** — *"whether or not the skill is interrupted or it
  fails"*.
- **All adrenaline is lost on death, or after 25 seconds of non-combat** (no
  attack landed, no damage taken — zero damage does not count as combat).

~~**And the wire is silent.**~~ — **SUPERSEDED 2026-08-21 by §26: the wire was
never silent, it was UNNAMED.** Four GAME_SMSG opcodes carry adrenaline — 207,
208, 209, 210 (`0x00CF`–`0x00D2`) — and 724 of them are sitting in this same
live corpus. The paragraph below is kept verbatim because every sentence in it
is *true as written*, and the shape of the miss is the lesson: this section
searched the sources for the WORD, and no source anywhere has it, so a source
survey could not have found the channel and a corpus scan with no name to look
for did not either. The second horn of the disjunction below is the right one,
and what settled it was the client's own receive table, not any source.

**And the wire is silent.** `schema/messages.json` names no adrenaline message.
GWCA’s `Opcodes.h` names none. GWCA reads `adrenaline_a/b` out of **client
memory** (`SkillbarSkill`, +0x00/+0x04), not out of a packet it maps. The
warrior melee sessions in the live corpus surface no adrenaline-shaped
property. So either the client animates its own icons from combat it can
already see — it watches its hits land and its health drop, and it holds the
unit costs in its own table — or the channel hides in an unmapped opcode.
~~UNRESOLVED~~ — **answered the same evening, §25**: the harness put Sever
Artery on the bar, landed nine hits, and the icon never moved. The client
does not self-animate adrenaline; the display waits for a message nobody has
mapped. The server tracks the pools authoritatively regardless.

## 25. The client consumes all of it — four runs, 2026-08-20 evening

The substrate landed at `68d9850` (gate, debit, regen, adrenaline pools,
death/revive emissions) and four loopback runs measured what the client does
with each message. Predictions were written before the first launch
(session scratchpad, `run-predictions.md`); every P below names its verdict.

**E1 (`20260820T230059`) — the debit and the climb.** The first property-62
any client has ever received from this server. Fifteen frames, every one
reconciled against the server's own logged pool plus 0.99 e/s times the gap:
**the client displays floor(its own integration of max + rate + debits)** —
including the two frames that discriminate floor from round (server 22.56 →
client **22**; 23.5 → **23**) — and the climb between messages runs at
exactly the prop-43 rate. Fourteen frames sit on exact press-time anchors;
the fifteenth (24 at ~+2 s) is consistent within the one press whose time is
estimated. P1 CONFIRMED, P2 CONFIRMED (the client animates the rate, as it
does for health). **And the energy bar draws THREE `›››` arrows — the 3-pip
rate, rendered** — with a control: at death (E3) the rate goes to 0.0 and the
orb empties outright. One pip-quantum, one arrow, the energy twin of isle
B4's health-pip result.

**E2 (`20260820T230849`) — the refusals, and the answer to §8's question.**
A 25-energy skill (863) drained the pool 25 → 0.00 in one cast, and the
recovery staircase came back **5 → 11 → 17 → 22 → 25** across ~6 s frames —
~1 e/s, the sent rate, from near-empty. Then the two refusals: with 7.70
energy the client **SENT** the 25-energy `USE_SKILL` anyway, and with 0
adrenaline it **SENT** the `0x8027` attack-skill press —

> **The client does not swallow an unaffordable press, and it does not grey
> the slot for affordability** (the darkening our first read saw was the
> SELECTED-SKILL gold border moving between slots). Against our server, the
> gate is the SERVER's, both halves. P3/P5 answered: no client-side gate
> fired. What retail's server answers a refused press with — ours answers
> with silence, and the client visibly re-animates the pressed slot for
> ~10 s afterwards — is a new open question; retail players see a "Not
> enough Energy" feedback that has to come from somewhere.

Also observed: the practice target died to THREE Power Attacks (they hit
for ~41, not the ~19 the walk plan assumed), which is why this run's Sever
charge stopped at 75 units — the fourth swing hit a corpse. And the
**25-second non-combat wipe fired live**: `the player's adrenaline is gone`.

**E3 (`20260820T231700`) — death and the resurrect pair.** The enemy killed
the player; the kill batch carried `energy regeneration stops` (43 = 0.0,
the retail death shape) and the client emptied the orb with the health. Ten
seconds later the revive sent the retail resurrect pair — **52 = 1.0 then
43 = rate** — and **the orb refilled on screen** (frame 23:17:44 empty,
23:17:50 full). Yesterday's runs left that orb at 0 forever; this was
property 52's first render on any client, ours or theirs. P8, P9 CONFIRMED.
Bonus: the post-revive Sever press was refused at **46 units accumulated
purely from taking hits** — the 1-unit-per-1%-health-lost rule visibly at
work with zero swings landed.

**E4 (`20260820T232138`) — the full adrenaline cycle.** Nine landed
auto-attack swings (each +25, pool capped at its 100-unit cost), then:
`skill 382 spends 100 adrenaline; every other pool loses a strike` →
`EFFECT_APPLY(Bleeding on agent 10, buff 1, 9.0s, inflicted by skill 382 at
rank 3)` — charge, spend, cross-pool tax and the condition landing through
the effect substrate, one unbroken chain. The immediate re-press proved the
reset: `needs 100, has 75` — exactly three post-spend swings' worth. P6
CONFIRMED.

**P7 REFUTED, and the negative is the finding: the client does NOT charge
the adrenal icon from observed combat.** At a server-side pool of 100 —
charged, accepted, spent — Sever's slot rendered pixel-identical to its
0-unit state (E4 frames w001 vs w002/w003; the gold ring in w004 is press
feedback, present for refused and accepted presses alike). The dark icon at
zero units matches GWW's description, but the flames-creeping-up display is
fed by the client's own adrenaline store (GWCA's `SkillbarSkill.adrenaline_a`,
+0x00) — and **no source anywhere maps the message that fills it**: not
schema/messages.json, not GWCA's `Opcodes.h` (GWCA reads it from client
MEMORY). Finding that opcode is now a named clientscan target: what writes
`SkillbarSkill.adrenaline_a`, and which RECV handler reaches it.

**ANSWERED 2026-08-21, §26 — and the refutation STANDS, now with a mechanism.**
Four RECV handlers write that store and nothing else does; our server sent none
of them, so there was nothing for the icon to draw. The target question was also
better than it knew: `adrenaline_a` (+0x00) is an ACCUMULATOR, and the icon does
not draw from it at all — it draws from `adrenaline_b` (+0x04), a deferred
commit of the first. Two things this run could not have known are now on record
for whoever re-runs it: the fill is drawn only while the map state is
`MISSION_MAP_GAME`, and the bar is a continuous fraction of the skill's RAW
cost, not a count of strikes.

# OBSERVED, 2026-08-21 (fourth pass): adrenaline HAS a wire — four opcodes

§25 ended with a named target: *what writes `SkillbarSkill.adrenaline_a`, and
which RECV handler reaches it.* This is the answer. It took the route every hard
question in this repo has taken — read the client's own receive table, then
check the reading against ArenaNet's own traffic — and it went to the binary
first precisely because §24 had already proved the sources were exhausted.

**What §24 got wrong, and it is worth naming before the evidence.** §24 searched
for the *word* and concluded the wire was silent. The word is not there: no
reimplementation in the vault names an adrenaline message, and the client itself
never names one either. But the channel was in `schema/messages.json` the whole
time, as four unnamed layouts. A survey keyed on a name cannot find a thing
nobody named. §24's second horn — *"or the channel hides in an unmapped
opcode"* — was the right one.

Static work is on the **pinned pristine build 38797**. No client was launched
for this pass, nothing was patched, and the live corpus was read and not written.

## 26. The adrenaline family: `0x00CF` gains, `0x00D0` clears, `0x00D1` sets, `0x00D2` spends

### 26.1 The four messages

MEASURED. Shapes are `msgshape.py`'s **recovered** descriptors, not
`msghandler.py --table`'s — the cmd slots in the static image read
`['0xcf', '0x0', '0x0']` because a load-time initializer fills them, and citing
the static view for a shape is how a reader gets a confidently wrong answer.
Every one of the four agrees byte-for-byte with the layout `schema/messages.json`
already carried, so naming them changed no field list; that is proved rather
than asserted in §26.10.

| opcode | hex | recovered shape | wire | worker | what the handler does | live |
|---|---|---|---|---|---|---|
| **207** | `0x00CF` | `[agent_id, u32]` | 10 B | `0x00821980` | adds `units` to every eligible slot, capped at that skill's cost | **663** |
| **208** | `0x00D0` | `[agent_id]` | 6 B | `0x00821B00` | zeroes both halves of all 8 slots | **22** |
| **209** | `0x00D1` | `[agent_id, u16, u32, u32]` | 16 B | `0x00821B70` | writes `units` to one slot, both halves | **0** |
| **210** | `0x00D2` | `[agent_id, u16, u32]` | 12 B | `0x00821C00` | used skill → 0, every other occupied slot −25 | **39** |

Names are in `schema/overrides.json` as `AGENT_ADRENALINE_GAIN` / `_CLEAR` /
`_SET` / `_SPEND`. **Every one of those names is INFERRED** — no ArenaNet string
names any of these four messages. What is SOURCED is the *store* they write
(§26.7); the verbs are our summary of what each handler does.

**The dispatch chains, and why they cannot be mis-read.** MEASURED, one link at
a time, `codescan.py --xrefs` on each:

```
  RECV table 0x00BC8F68
    207  stub 0x0091F3F0 -> thunk 0x00814500 -> worker 0x00821980
    208  stub 0x0091F410 -> thunk 0x00814520 -> worker 0x00821B00
    209  stub 0x0091F430 -> thunk 0x00814540 -> worker 0x00821B70
    210  stub 0x0091F460 -> thunk 0x00814570 -> worker 0x00821C00
```

Each of the eight downstream functions has **exactly one direct caller in the
image**, so there is no branch anywhere in the chain to have taken wrongly.
Every thunk does the same two things: `mov ecx,[eax+0x2C]` then `add ecx,0x6F0`
— the per-agent skill-bar container that ArenaNet's own assert calls
`hotKeyState` (`ChCliSkill.cpp:718`, the same container opcode 100's override
row already named). A record is 0xA4 bytes: eight slots of stride 0x14 starting
at record+4, ending at record+0xA4. The bound is SOURCED too —
`ChCliSkill.cpp:124` asserts `hotKey < arrsize(hotKeyState->hotKey)` on the
accessor's slot index.

Slot layout, as the four handlers use it:

| offset | field | who touches it |
|---|---|---|
| +0x00 | `adrenaline_a` — the accumulator | 207 adds, 210 decrements, the deferred commit reads |
| +0x04 | `adrenaline_b` — the display copy | 208/209/210 write; the commit writes; **the only half any accessor exposes** |
| +0x08 | recharge | 207 reads it as a gate |
| +0x0C | skill id | matched by 209 and 210 |
| +0x10 | skill copy | matched by 209 and 210 |

### 26.2 The charging loop, read instruction by instruction

MEASURED at `0x00821980`. Five rules, and each one is a single instruction pair
rather than an inference:

1. **Walk exactly eight slots.** `0x008219AD lea ebx,[eax+0xA4]` (the end) and
   `0x008219B5 lea esi,[eax+4]` (the first), stepped `0x008219F1 add esi,0x14`.
2. **Skip a RECHARGING slot.** `0x008219C0 cmp dword [esi+8],0 / jne` — a skill
   whose recharge is nonzero takes no adrenaline at all. This is a rule the wiki summary
   in §24 does not carry, and the client enforces it.
3. **Skip an EMPTY slot.** `0x008219C6 mov eax,[esi+0xC] / test eax,eax / je`.
4. **Skip a NON-ADRENAL skill.** `0x008219CE call 0x005A88B0` resolves the skill
   row (`imul eax,esi,0xA4` + base `0x00988ED0`, bound `0xD73` = 3443 rows), then
   `0x008219D6 movzx ecx,word [eax+0x38] / test cx,cx / je`. Zero cost, no charge.
5. **Add, then CAP at the skill's own cost.** `0x008219DF mov eax,[esi]` /
   `0x008219E1 add eax,[ebp+0xC]` / `0x008219E4 cmp ecx,eax / jb / mov ecx,eax` /
   `0x008219EA mov [esi],ecx`. That is `slot = min(cost, slot + units)`.

`0x008219EC mov edi,1` sets a *something-gained* flag, and **if no slot took the
units the handler returns having done nothing** — no event, no queue entry, no
repaint. Everything is UNSIGNED: `0x00CF` cannot express a loss, and a server
that wants one has to send `0x00D0` or `0x00D2`.

**The 25.0f is a constant, not the amount.** On any gain the handler posts UI
event `0x10000058` carrying `fld dword [0x009495B4]` — MEASURED as raw bytes
`0000c841` in `.rdata`, i.e. `25.0f`, a fixed literal. It is **not** the
message's `units` field. Anyone reading that `fld` as "the amount gained" would
get 25 for a 3-unit gain; the amount reaches the store through `[ebp+0xC]` and
nowhere else.

### 26.3 The deferred `a`→`b` commit, and why the split exists

MEASURED. After the loop, 207 appends the agent to the array at `ctx+0x6E0` and
schedules deferred task `0x00820DD0`. That task pops the front entry, re-finds
the record, and runs `0x00820E84 mov ecx,[eax]` / `0x00820E86 mov [eax+4],ecx`
across all eight slots — `adrenaline_a` → `adrenaline_b` — then posts
`0x10000059`, the repaint.

**This is a deferred-commit double buffer, and the asymmetry is the evidence.**
`+0x00` is written by the arithmetic and read by almost nothing; `+0x04` is
written by every handler that wants an immediate repaint and is the only half
the accessor exposes (§26.4). `0x00CF` alone routes through the queue — 208, 209
and 210 write **both** halves inline and repaint on the spot, which is exactly
what you do when the value is already final and you are not batching.

**How hard that claim was checked.** `codescan.py --xrefs 0x00820F10` says the
record lookup — the only direct path to a slot in the image — has **25 direct
call sites**, and every one falls inside a single contiguous stretch of `.text`,
`0x00820E6E`–`0x008230AB`, whose asserts are `ChCliSkill`'s. All 25 were
disassembled. Within that bound, a slot's `+0x00` is:

- **computed** at exactly four sites — `0x008219EA` (207's capped add),
  `0x00821B30` (208's zero), `0x00821BD7` (209's set), `0x00821C7E` (210's
  decrement);
- **cleared wholesale** by the skill-bar load path, which memsets the whole
  0x14-byte slot (`call 0x0046DBF0`, `ecx` = slot base, `edx` = 0x14) — so
  loading a bar drops adrenaline as a side effect;
- **moved wholesale** by two five-dword slot copies (`0x008224A4`,
  `0x00822861`), which relocate a slot without computing anything;
- and **read to compute with** at three sites only: 207's own `add`, the
  deferred commit, and 210's decrement.

That is a bounded search, not a census, and the bound is what makes it
refutable: anything reaching a slot without going through `0x00820F10` is
outside it. Naming the bound is deliberate — `studies/enemy/PLAN.md` §6o once reported a
scope-limited search as a global absence and closed a question for a session
with a false sentence.

**A FIFTH writer exists, and it is not one of these four.** Opcode **231**
(`0x00E7`, `[agent_id, u16, u32]`, 12 B — the same shape as 210) reaches worker
`0x00822D10` via stub `0x0091F6E0` and thunk `0x00814980`, matches one slot, and
zeroes **both** adrenaline halves (`0x00822D7C`, `0x00822D82`) before setting the
recharge field to `0xFFFFFFFF` and posting a second event. It is almost
certainly a *skill disabled* message and this pass is **not naming it** — one
handler read is not enough, and 231 has its own evidence to gather. It is
recorded here because any model of this store that lists four writers is already
wrong.

### 26.4 The display path ends at an `fdiv` — and it is the RAW cost, with no quarters

MEASURED, and this is the correction §25 could not make.

`ChCliApi 0x00816EF0` is the adrenaline accessor. It returns
`[record + 0x14*slot + 8]` — computed as `lea eax,[esi+esi*4]` /
`mov eax,[edi+eax*4+8]` at `0x00821081`, which is slot base **+0x04**, the
display copy. It has **exactly one direct caller in the entire image**
(`codescan --xrefs`, zero aligned words holding the VA): `GmSkSlot 0x00542E78`.

That caller fetches the display half, fetches the cost beside it, and posts both
to one control:

```
00542E78  call 0x816EF0                  ; adrenaline_b for this slot
00542E7D  mov  [ebp-8], eax
00542E80  movzx eax, word ptr [esi+0x38] ; the skill row's adrenaline cost
00542E84  mov  [ebp-4], eax
00542E8D  push 0x59                      ; -> Controls::SkillImage, payload {b, cost}
```

`GmCtlSkImage 0x008C6112` receives message `0x59`, and its arithmetic is the
whole answer:

- `0x008C6140 cmp eax,ecx / jb` — if `adrenaline_b >= cost`, the fraction is
  never computed and a different, fully-charged visual is used;
- otherwise both values are converted as **unsigned** (`fild` plus the
  `fadd [0x93c1d8]` = `4294967296.0` fixup for a set sign bit) and
  `0x008C6188 fdiv` divides them;
- the quotient is forwarded as message `0x56`.

**So the fill is a continuous fraction of the RAW unit cost.** There is no
division by 25 anywhere on this path and no quantisation to quarters. A 3-unit
gain on a 100-unit skill sends the control `0.03`, not zero — what the control
then *draws* with that number is one hop further than this pass traced, and the
run in §26.11 item 6 is what would settle it. §10's `ceil(units/25)` is still
right for the *number printed on the skill card*; it has nothing to do with the
fraction on this path.

**And it corrects a claim of ours.** `PLAN.md` (~line 1384) says the display
store is `SkillbarSkill.adrenaline_a (+0x00)`. **That is wrong** — the display
store is `+0x04`. Note what is *not* being corrected: `Py4GW_Reforged` reads
`adrenaline_a` as the live value and that is also right, for a different
consumer. A bot wants the accumulator, which is current the instant the message
lands; the screen shows the committed copy, which lags by one deferred task.
The two readings are complementary, not contested.

### 26.5 What retail actually sends — the census

MEASURED by this session over the live corpus: `vault/captures/live` holds **14**
capture directories, **10** of which carry a decrypted game channel; those ten
hold **49 GAME_SMSG connections** and **114,985 messages**, every connection
decoding to its final byte with zero framing errors (`tape.decode_all` refuses a
partial decode, and the pooling rule refuses any connection whose `origin` is
not `live`).

| opcode | n | payload distribution |
|---|---|---|
| 207 | **663** | `25` ×631; sub-25 gains ×32: `{3:6, 4:12, 5:1, 6:5, 7:1, 8:3, 11:4}` |
| 208 | **22** | — |
| 209 | **0** | — |
| 210 | **39** | skill ids `{382: 20, 384: 11, 385: 8}` |

**Self-scoped, 9 of 9.** Every connection that carries a 207 names **exactly one
agent id**, and that id equals the same connection's own opcode-218
`SKILLBAR_UPDATE` agent. Zero mismatches, zero multi-agent connections. The nine
connections sit in three captures and show only four distinct ids —
`{7, 11, 13, 25}`, with two connections in one capture both naming `11` — which
is what a per-instance agent handle looks like, not four agents being tracked.

**This REFUTED an earlier draft of this same pass**, which read the four
distinct ids as evidence that retail broadcasts adrenaline for other agents'
bars. It does not. Adrenaline is scoped exactly like energy property 62
(§23): a server emits it only for the agent whose own UI shows the value, and
ours must not emit it for NPCs.

**Two amount populations, and only one of them has a reading with evidence.**
The `25`s are OBSERVED as a value, and 25 units per landed weapon hit is exactly
the first of the two WIKI gain rules §24 already records. The 32 sub-25 gains
are also OBSERVED as values, and the obvious reading is §24's second rule — one
unit per 1% of maximum health lost, floored — which would make
`{3,4,5,6,7,8,11}` percentages of a health bar.
**That reading is INFERRED and nothing joins it to health traffic yet.** The
join is cheap and specific and has not been run: for each sub-25 gain, find the
health property on the same agent within the same batch and test
`units == floor(100 · damage / max_health)`. Until somebody does that, the
population is a set of small integers that is *consistent with* a rule, which is
what coincidence also looks like.

**209's zero is a result, not a gap.** A fully implemented live handler that
retail never used in anything this repo has captured — the same shape of finding
as energy property 33 (§23), also implemented, also never sent. It is why 209 is
filed at `medium` while its three siblings are `high`.

### 26.6 The map-state gate, and what it does to probe design

MEASURED, and this changes how the next run must be set up.

`GmSkSlot 0x00542E43` calls `MissionCliGetMap` (`0x0084D9B0`, which returns
`missionCtx[+0x238]`), then `0x00542E48 cmp eax,1` / `0x00542E4B jne`. On the
`jne` path the control is sent message `0x59` with a **NULL payload**
(`0x00542E9F push 0 / push 0`) — the overlay is not merely left stale, it is
torn down.

The enum values are SOURCED from ArenaNet's own asserts and the branches they
guard, not guessed:

- `MsCliApi.cpp:251` asserts `context->map == MISSION_MAP_GAME` guarding
  `cmp dword [esi+0x238],1` → **`MISSION_MAP_GAME == 1`**;
- `QuestLog.cpp:261` asserts `MISSION_MAP_OUTPOST == MissionCliGetMap()`
  guarding `test eax,eax / je` → **`MISSION_MAP_OUTPOST == 0`**.

**So a perfectly correct 207 sent while the client sits in an OUTPOST produces a
pixel-identical icon.** Any probe of this family has to be in an explorable or a
mission, and a null from an outpost run means nothing at all — it is a check
that cannot fail, which is not a check. (This does **not** explain §25's P7:
that run's icon stayed dark because nothing had written the store at all, our
server having sent none of these four. The map gate is a *second* requirement
the next run has to satisfy, not a re-reading of the last one.)

### 26.7 ArenaNet's own words

SOURCED. Four assert sites carry the word, and two of them do real work:

| site | expression | what it settles |
|---|---|---|
| `ChCliSkill.cpp:84` @ `0x00820DEB` | `context->skillAdrenalineUpdateArray.Count()` | names the whole deferred chain **adrenaline** |
| `GmCtlSkCard.cpp:409` @ `0x008CC42D` | `!(energyCost && skillData.adrenaline)` | guards `cmp word [esi+0x38],0` |
| `GmCtlSkListEntry.cpp:185` @ `0x008D377A` | `!(energyCost && skillData.adrenaline)` | guards `cmp word [edi+0x38],0` |
| `GmCtlSkImage.cpp:1483` @ `0x008C61F4` | *"Clearing the adrenaline timer on a skill image is currently not supported. Bug Austin about this."* | the control drawing `0x59` is the adrenaline control, in ArenaNet's own words |

The middle two are the load-bearing pair. **`word[skillRow+0x38]` IS
`skillData.adrenaline`, at two independent sites in two different source
files** — which promotes `toolkit/clientscan/skilltable.py`'s `adrenaline_units`
from our name for the field to *the client's own*. §10 measured that field and
called it a threshold; ArenaNet calls it `adrenaline`, and both are true.

Two more entry-guard asserts pin field 2 of the two matching handlers as
`skill`: `ChCliSkill.cpp:442` at `0x00821B85` (209) and `ChCliSkill.cpp:463` at
`0x00821C16` (210), each guarding a `test` on that argument. The row lookup's
own bound assert is at `ConstSkill.cpp:3833`, and it names the table `s_skill`.

A caution the tooling itself prints: `asserts.py` reads 19,758 sites and knows
it is short by at least 373 more it cannot pattern-match, so **"no assert names
X" from that tool is a floor, not a census.** Nothing above depends on an
absence.

### 26.8 Adrenaline costs are NOT all multiples of 25

MEASURED over all **3,443** rows of build 38797's skill table (base VA
`0x00988ED0`, stride 0xA4). **151 rows carry a nonzero cost:**

```
20:1   25:2   50:6   60:1   75:10   80:20  100:24  120:20  125:2
130:5  140:5  150:20  160:5  175:5  200:21  220:1  240:2   250:1
```

Nine of the eighteen distinct values are **not** multiples of 25. So **the pool
must be modelled in raw units** — 25 is the gain per weapon strike, not the
quantum of the bar — which is what `pools.py` already does and what §26.4's
`fdiv` independently requires.

**A latent width disagreement, recorded before it bites.** The client reads
`+0x38` as `movzx WORD` at both `0x00542E80` and `0x008219D6` — 16 bits.
`skilltable.py` (~line 198) reads it as `u32`. On build 38797 the high word is
**0 on every one of the 3,443 rows** (measured), so nothing is wrong today and
nothing needs changing today. But the widths disagree, and if a future build
ever parks a flag in that high word, our decode silently inflates a cost by
65,536× while the client ignores it.

### 26.9 No upstream names any of this — with positive controls

**NOT FOUND**, and searched with a control green in every file so the negative
means something (`feedback: a negative needs a positive control`). Six opcode
tables across five lineages:

| lineage | file | `adrenalin` | `0x00CF`–`0x00D2` | control |
|---|---|---|---|---|
| GWCA (maintained, gwdevhub) | `Dependencies/GWCA/.../Opcodes.h` | 0 | none | `0x00D9` found |
| GWCA (GregLando113) | `Include/GWCA/Packets/Opcodes.h` | 0 | none | `0x00D9` found |
| GWCA (JaborGW) | `Include/GWCA/Packets/Opcodes.h` | 0 | none | `0x00D9` found |
| Headquarter | `code/client/opcodes.h` | 0 | none | `0x00D9` found |
| OpenTyria | `code/opcodes.h` | 0 | none | `0x00D9` found |
| Py4GW_Reforged_Native | `include/GW/common/opcodes.h` | 0 | none | `0x00D9` found |

The control matters: all six tables share build 38797's numbering (`0x00D9` /
`0x00DA` are the skillbar pair in every one, and our own census joined 207
against opcode 218 successfully), so their silence is silence about *these*
messages and not about some other build's.

**Three lineages DO carry the four shapes, and every one of them leaves the
messages unnamed.** This is the strongest corroboration in the section and it is
worth spelling out, because none of it was taken from anybody — the shapes were
derived from the client's own recovered descriptors and *then* compared:

- `gw-preservation/network-log-explorer` (`Constants.ts`) lists cmd arrays for
  `0x00cf`–`0x00d2` that match ours **cmd for cmd**: `[0x0010, 0x0404]`,
  `[0x0010]`, `[0x0010, 0x0204, 0x0404, 0x0404]`, `[0x0010, 0x0204, 0x0404]`.
  Its *name* map, in the same file, skips straight from `0x00CD` to `0x00D9`.
- **`sgwlpr` and `GWLP-R` predate this numbering, and finding them required
  correcting for the shift.** Their skill block sits **12 lower** than ours —
  GWLP-R has `P206_UpdateSkillBar` where we have 218, `P215_SkillActivated`
  where we have 227, `P217_SkillRecharge` / `P218_SkillRecharged` where we have
  229 / 230. At 207 − 12 = **195**, `sgwlpr`'s `PacketTemplates.xml` carries four
  consecutive packets whose fields are exactly ours:
  `195 = [agentid, int32]`, `196 = [agentid]`,
  `197 = [agentid, int16, int32, int32]`, `198 = [agentid, int16, int32]`.
  GWLP-R's `P195`–`P198` are the same four, and all four class names are
  `_Unknown`.

Four consecutive layouts matching across a build gap of a decade or more is
not something a coincidence produces, and it is a shape check with no free
parameter: the offset was fixed by three *other* messages before 195 was looked
at. Use of `gw-preservation` is confined to exactly this — verifying a value we
derived ourselves, the only thing that upstream's terms permit (`CLAUDE.md`,
second gate) — and nothing here takes a layout, an algorithm or a constant from
any of the three, so no derivation-register row is owed.

**So the four names are OURS** — and, worth saying plainly, the reason nobody
named them is not that they are obscure. They are four consecutive opcodes in
the middle of the skill block, 724 of them in this corpus. They went unnamed
because everyone who wanted adrenaline read it out of client memory instead,
where it is one `ReadProcessMemory` away.

### 26.10 What did not change, proved rather than argued

The codec reads only `fields`; the four override rows add none, so decoding
*cannot* change. That is exactly the sort of claim our own decoder can be made to
agree with, so it was checked the other way round: the **entire** live corpus was
decoded twice — once against the committed `overrides.json`, once against the
working tree's — and hashed.

```
committed overrides:    b11aba5b…  114,985 messages
working-tree overrides: b11aba5b…  114,985 messages
```

Identical SHA-256 over every decoded field of every message. The four
schema-reading tests were also re-run before and after and returned the same
counts: `test_codec.py` 29, `test_catalog.py` 13, `schema/test_smsgnames.py` 15,
`authsrv/test_smsgnames.py` 26 — all green, 83 checks.

### 26.11 Open

1. **The recharge gate has never been seen live.** Rule 2 of §26.2 is read off
   `cmp dword [esi+8],0 / jne` and nothing in the corpus isolates it. The probe:
   charge a bar, put one adrenal skill on recharge, send a 207, and watch whether
   that slot's fill moves. Cheap, and it is the only one of the five rules with a
   single line of evidence.
2. **Are the sub-25 gains the health-loss rule?** §26.5's join is unrun. Until
   it is, that reading is INFERRED and the 32 values are just small integers.
3. **What is 209 for?** Zero live witnesses. A resynchronisation after a
   reconnect and a hero/henchman bar push are both plausible and neither is
   evidenced. If the answer is "nothing on retail", say so — energy property 33
   is the precedent for an implemented-and-unused handler.
4. **Opcode 231 needs its own pass** (§26.3). It is the fifth writer of this
   store, its shape matches 210's, and this section deliberately did not name it.
5. **The `u16`/`u32` width disagreement at `+0x38`** (§26.8) is latent on 38797
   and should be re-measured on 38833 before anyone relies on it staying latent.
6. **Nothing here has been sent to a client yet.** Every claim in §26 is static
   plus retail's wire. The confirming run is: explorable map (§26.6), a bar with
   an adrenal skill, 207 for a partial fill, 210 for the reset-and-tax, 208 for
   the wipe — with the prediction that the fill is `units/cost` of the ring and
   not a count of quarters.
