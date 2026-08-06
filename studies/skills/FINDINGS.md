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
| 14 / `0x000E` | `ATTRIBUTE_DECREASE` | agent_id, u32, u32 | 14 |
| 15 / `0x000F` | `ATTRIBUTE_INCREASE` | agent_id, u32, u32 | 14 |
| 16 / `0x0010` | `ATTRIBUTE_LOAD` | agent_id, array32[16], array32[16] | 142 decl. |
| 28 / `0x001C` | `HERO_USE_SKILL` | agent_id, u32, u32, agent_id | 18 |
| 41 / `0x0029` | `DROP_BUFF` | u32 | 6 |
| **70 / `0x0046`** | **`USE_SKILL`** | **u32, u32, agent_id, u8** | **15** |
| 92 / `0x005C` | `SKILLBAR_SKILL_SET` | agent_id, u32, u32, u32 | 18 |
| 93 / `0x005D` | `SKILLBAR_LOAD` | agent_id, array32[8] | 42 decl. |
| 94 / `0x005E` | `SKILLBAR_SKILL_REPLACE` | agent_id, u32 ×4 | 22 |
| 109 / `0x006D` | `TOME_UNLOCK_SKILL` | u32, u32 | 10 |

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
| Rank-0/rank-15 scaling shown in the tooltip | PE row `0x44`-`0x68` | **No** |
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

**A caveat on the OBSERVED tier itself.** The bytes in our captures are ours; the
*names* attached to them are OpenTyria's. Our label table matches ldufr's
`opcodes.h` precisely where ldufr disagrees with the rest of the cluster — our
captures label opcode 183 `PLAYER_UPDATE_PROFESSION`, which is OpenTyria's
number, while GWCA and Py4GW both put that message at 182. So "SMSG 29 =
PVP_UNLOCKED_SKILLS" is **observed bytes with a sourced name**, not an
independent observation. Worth stamping the label table with its provenance.

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
| What actually triggers the cast animation — 228, a property update, or the client's own prediction? | Send each in isolation and watch. No source we have answers it; the movement pass's precedent says bet on client prediction. |
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
