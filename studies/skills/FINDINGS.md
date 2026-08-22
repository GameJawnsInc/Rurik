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
| Rank-0/rank-15 scaling shown in the tooltip | PE row `0x44`-`0x68` | **Yes, 2026-08-14** — `skilltable.py`, whole window bar `+0x50` (§4 of the 2026-08-05 block) |
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

> **This block RESTARTS the section count at 1, so §1–§8 exist twice in this
> document — once above, once below.** Nothing else collides: §9 onward is a single
> run that never resets. **The resolver, and it is what the citations already do:
> a bare §1–§8 means the DESK pass above.** Every one of the nineteen citations
> from outside this document — `studies/profession` ×8, `studies/skillcast` ×4,
> `studies/combat/PLAN.md` ×3, `studies/profession/MODDABLE.md`,
> `WORKAROUNDS.md`, `studies/review` ×2 — resolves that way, and not one of them
> means a section of this block. **This block's own §1–§8 are cited as "§N of the
> 2026-08-05 block"** (or "of this section", which §10 already uses), and the four
> places that needed it now say so.
>
> The numbers themselves are NOT being migrated. `studies/idents/HANDOFF.md`'s
> ★ box rules on exactly this — *"a mass rename of existing tokens is out of scope
> and should be refused... the deliverable is a convention for NEW identifiers plus
> a resolver, not a migration"* — and section numbers here are load-bearing in
> commit messages (`Skills 32.8`, `Isle 8.6`, `§27.4` are all commit subjects).
> A renumber buys a cold reader a few seconds and costs everyone else their index.
>
> **Two bare references in this document are NOT covered by the rule, because the
> sweep could not settle them and guessing is worse than saying so.** §25's
> *"the answer to §8's question"* has three live candidates — this document's desk
> §8, `PLAN.md` §8's old heal-spam item, and `studies/isle` rung 8 — and the
> paragraph cites isle three lines earlier. §36's *"a scope error of exactly the
> kind [§4](#) warns about elsewhere"* was committed with an EMPTY href (`12ce246`)
> and names no document; neither §4 in this file is about scope. Whoever wrote
> them can close them in a line; nobody else should.

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
observed in §5 of this block, because they diverge only on exact multiples of
25 and none of those three was one. A bar was built from four Warrior skills
whose raw values *are* exact multiples, so the two rules predict different
numbers in every slot:

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
§4 of the 2026-08-05 block answered which values *render green*; this is about
which values are *real*, which turns out not to be the same question. Three
findings and one corroboration, all from the 1,333-skill player corpus plus
the 102 `0x0042` applies in the live captures.

## 12. `skill_arguments` bit 1 means the duration SCALES, not that the slot is meaningful

§4 of the 2026-08-05 block established that a value renders green when its
`args` bit is set **and** its endpoints differ, and that reading endpoints
without the bit invents a progression the game never draws — Rush's scale slot
holds a constant 25 with its bit clear. `authsrv.skill_scale_value` therefore
**raises** on a disabled set, which is right for the scale.

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
the adrenal icon from observed combat.** (EXPLAINED in §26 and INVERTED
in §27: nothing was filling `adrenaline_b` because no `0x00CF` had ever been
sent. With one, the same rig fills the same slots and the controls stay at
zero. The refutation stands exactly as written — it was a true statement
about a client nobody had sent the message to.) At a server-side pool of 100 —
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

**A FIFTH AND A SIXTH writer exist, and neither is one of these four.**
*(Corrected 2026-08-21: this said FIFTH. Opcode **229** `0x00E5`
SKILL_RECHARGE is a sixth — worker `0x00822B90`, reached via stub
`0x0091F690` and thunk `0x00814920`, whose matched-slot body zeroes both
halves at `0x00822C00`/`0x00822C06` in a sequence **byte-identical** to
231's before writing the recharge timestamp at `0x00822C41`. It was missed
here because this section's bounded search asked which sites COMPUTE a
value into `+0x00`, and a constant zero computes nothing. The bound was
stated honestly and still hid a writer — worth keeping as the example.)*

**And the fifth:** Opcode **231**
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

1. ~~**The recharge gate has never been seen live.**~~ — **SEEN 2026-08-21,
   §32, and it holds.** Two witnesses now stand behind it where there was one
   line of disassembly: the measurement (a 120-cost skill on a 12 s recharge
   ends at 40.4% against a predicted 41.7% for "4 gains skipped, 2 landed",
   versus 100% had none been skipped) and GWW's own *"recharging skills cannot
   rebuild adrenaline"*. Note the run's designed readout was confounded — the
   recharge SWEEP draws in the same rectangle as the fill — and the answer came
   from the residue after the sweep cleared. §32.2.
2. ~~**Are the sub-25 gains the health-loss rule?**~~ — **RUN 2026-08-21, and
   it CORRECTED the rule.** They are the health-loss rule: 31 of the 32 carry a
   same-batch `0x00A3` naming the gaining agent as its target, so each joins to
   the exact damage that produced it. **But the wiki's "floored" is wrong —
   the wire rounds.** floor fits 14/31, ceil 17/31, `floor(pct)+1` 17/31,
   **round 31/31**. The discriminating rows are |pct| 2.500, 2.708, 2.917 and
   3.542 granting 3, 3, 3 and 4 where flooring grants 2, 2, 2 and 3.
   `pools.damage_units` shipped the wiki's rule and was corrected; the reading
   is now OBSERVED rather than INFERRED. Two caveats kept: the sign is
   negative on the wire and the magnitude is what the rule reads (flooring the
   negative rounds away from zero and fits nothing — an arithmetic slip that
   made a correct hypothesis look 0-for-31), and the no-grant BOUNDARY moving
   from 1% to 0.5% is an extrapolation, since the corpus's smallest sample is
   2.5%.
3. ~~**What is 209 for?**~~ — **ANSWERED 2026-08-21: "nothing on retail" is
   now EARNED rather than assumed, and both named candidates died.** Verified
   CONFIRMED by an adversarial pass.
   **The hero/henchman push is REFUTED twice over.** Structurally: the worker
   has no hero-specific machinery its siblings lack — the record lookup
   `0x00820F10` is a plain binary search keyed on agent id with no comparison
   against the local player, so 207/208/210 would already serve a hero
   unchanged. And empirically: **heroes are absent from the corpus**
   (`0x01C2` PARTY_HERO_ADD = 0 of 114,985) — with a green positive control,
   since the identical scan finds `0x01BF` PARTY_HENCHMAN_ADD **21 times over 7
   connections**. Better still, those henchmen are the decisive datum:
   **companions demonstrably existed and retail pushed them no skill state at
   all** — zero 218/207/208/209/210/229/230/231 naming any of them.
   **The resync-after-drift story lost its mechanism.** It rested on 207's
   recharge skip (`0x008219C0`) being a client-side quirk the server might not
   share. It is not a quirk: GWW states *"recharging skills cannot rebuild
   adrenaline"*, so it is a GAME rule both sides implement and no drift arises
   from it.
   **What survives is narrower and unfalsified**: an absolute restore into a
   session whose state the server cannot derive from deltas — a reconnect or
   mid-instance resume. **And the corpus is silent on it for a MEASURED reason
   rather than a hopeful one:** all 48 skillbar pushes arrive 0.22–0.90 s into
   their connection, so every one of the 49 connections is a fresh instance
   entry and the corpus **contains no reconnect at all**. The one experiment
   that would settle it is named in §26.12.
   **Method note worth more than the answer**: "is this agent the observer" was
   checked with two independent routes — `0x017D` INSTANCE_LOAD_PLAYER_NAME and
   `0x0199` INSTANCE_LOAD_INFO's player number, each mapped through `0x0059`'s
   `(player_number, agent_id)` — agreeing on 40 of 40 resolvable connections
   and disagreeing on 0. The obvious shortcut fails hard: taking the FIRST
   `0x0059` as self is wrong on 20 of 44 connections, because `0x0059` is
   broadcast for every player in the instance. `toolkit/authsrv/moralescan.py`
   shipped that shortcut and was corrected the same day (§26.13).
4. ~~**Opcode 231 needs its own pass**~~ — **DONE 2026-08-21, §26.12.**
5. ~~**The `u16`/`u32` width disagreement at `+0x38`**~~ — **MEASURED on both
   builds 2026-08-21: still latent.** The high word is zero in **all 3,443
   rows on 38797 AND on 38833**, which also carry the same 151 nonzero costs
   over the same distinct set {20, 25, 50, 60, 75, 80, 100, 120, 125, 130, 140,
   150, 160, 175, 200, 220, 240, 250} — note 20, 60, 130, 140, 160, 175 and 220
   are not multiples of 25, which is §26.8's raw-units point from a second
   build. `skilltable.py` reading a dword where the client reads a word remains
   harmless, and is now harmless *across a build bump* rather than on one
   image. Worth aligning the widths anyway; no longer worth blocking on.
6. ~~**Nothing here has been sent to a client yet.**~~ — **DONE the same day,
   §27.** The run was made, the prediction it registered (`units/cost`, not a
   count of quarters) was CONFIRMED, and §26's central claim is no longer static
   plus wire: a client has now been made to draw this family. The two halves
   §27 did *not* reach — 210's on-screen reset and 208's wipe — are restated as
   open there rather than closed here.

## 27. E5 — the flames, on screen

**2026-08-21, run `20260821T125215`, loopback, build 38797, server at
`98806c0`.** The fifth run of the series §25 opened, and the one that closes
§25's P7. Predictions were registered before the client launched
(session scratchpad, `e5-predictions.md`) and before the build workflow that
produced the sender had reported.

### 27.1 Why this run could be short

E5 is E4 **with one thing changed** — the server now sends `0x00CF` — so E4 is
its own control and was already collected. That is the whole design: §25 had
already established that at a server-side pool of 100 the icon rendered
pixel-identical to its 0-unit state, so any movement here is attributable to
the message rather than to the fight.

**The instrument is the DEFAULT bar**, which turned out to be better than the
single-skill rig §26.11 imagined. `[316, 317, 318, 319, 320, 321, 322, 323]`
carries three adrenal skills whose costs are *not* multiples of 25, and five
non-adrenal ones:

| slot | id | `adrenaline_units` |
|---|---|---|
| 1 | 316 | — (non-adrenal) |
| **2** | **317** | **80** |
| **3** | **318** | **120** |
| **4** | **319** | **80** |
| 5–8 | 320–323 | — (non-adrenal) |

So slots 1 and 5–8 are an **in-frame null control**: they sit in the same
screenshot, under the same lighting, through the same fight. This matters more
than it sounds — `studies/review`'s aggregate-diff lesson is that a
changed-pixel spike over a whole HUD finds tooltips and toasts, not findings.

### 27.2 What the server sent

Twelve gains, each `0x00CF, 10 B`, each emitted **before** its damage message —
retail's batch position, fixed the same morning after the skeptic pass caught
the sender shipping it last:

```
[c1] attacking agent 10 (Hatcher [Collector])
[c1] s2c adrenaline +25 (weapon hit on agent 10) (0x00cf, 10B)
[c1] hit agent 10: 93/100
[c1] s2c adrenaline +25 (weapon hit on agent 10) (0x00cf, 10B)
[c1] hit agent 10: 88/100
      … twelve in all
```

The first `0x00CF` any client has ever been sent by this server, or by any
server we have written.

### 27.3 P10 — the flames move. CONFIRMED

Fraction of each slot's pixels differing from the pre-attack baseline
(`walk2-shot.png`, every pool at 0), threshold 24/765:

| frame | slot 1 | **slot 2** | **slot 3** | **slot 4** | slot 5 | slot 6 | slot 7 | slot 8 |
|---|---|---|---|---|---|---|---|---|
| walk4 | 0.0% | **49.2%** | **23.8%** | **40.3%** | 0.0% | 0.0% | 0.0% | 0.0% |
| walk6 | 0.0% | **89.8%** | **89.0%** | **89.2%** | 0.0% | 0.0% | 0.0% | 0.0% |
| walk8 … walk16 | 0.0% | **89.8%** | **89.0%** | **89.2%** | 0.0% | 0.0% | 0.0% | 0.0% |

**The five control slots are at exactly 0.0% in all seven frames.** Not "close
to zero" — zero changed pixels, which is the same pixel-identity standard that
made §25's negative trustworthy, now producing a positive on the three slots
next to them. §25's P7 is not merely explained, it is inverted under the
identical rig.

### 27.4 P11 — a continuous fraction, not quarters. CONFIRMED

The whole-slot percentages above are **not comparable across slots** — they
depend on the icon art underneath. So the fill was measured the way the client
draws it: per row, bottom-up, counting rows that moved. On `walk4`, the one
frame that caught the bar mid-charge:

```
slot 1 (316, non-adrenal)   0/54 rows =  0.0%   ..................................
slot 2 (317,  80 units)    30/54 rows = 55.6%   ..##############################++
slot 3 (318, 120 units)    17/54 rows = 31.5%   ..#################+++............
slot 4 (319,  80 units)    26/54 rows = 48.1%   ..##########################++++++
slot 5 (320, non-adrenal)   0/54 rows =  0.0%   ..................................
```

**The fill rises from the bottom and stops at arbitrary heights.** Quarter-strike
quantisation on an 80-unit skill could only ever land on 31.25%, 62.5% or
93.75%; 55.6% and 48.1% are neither. This is the `fdiv` at `0x008C6188`
rendering — `adrenaline_b ÷ skillData.adrenaline` — and §26.11's registered
prediction, confirmed.

**And the denominator is the skill's own raw cost, visibly.** Slot 3 costs 120
where slots 2 and 4 cost 80. All three received identical grants, and slot 3
sits *lower* than both. A display keyed to strikes rather than to raw units
could not produce that, and it is the on-screen counterpart of §26.8's census
finding that 151 skills carry costs that are not multiples of 25.

**HONEST LIMIT — and it was mostly the METRIC, not the client. Re-measured
2026-08-21 after §29.4.** As first written this paragraph read: *"Slots 2 and 4
have the same cost and should therefore show the same fill; they read 55.6% and
48.1%. The likeliest reading is animation phase… until [a denser sample] exists
'the two 80-unit skills agree' is UNVERIFIED rather than confirmed."*

That 7.5-point gap came from the rows-over-30%-of-width statistic, which §29.4
showed is sensitive to the icon art *underneath* the fill. Re-measured with the
art-independent boundary criterion the whole series settled on, the same eight
frames give:

| frame | slot 2 (80) | slot 3 (120) | slot 4 (80) |
|---|---|---|---|
| w001 | 0.0% | 0.0% | 0.0% |
| **w002** | **21.2%** | 15.4% | **25.0%** |
| w003–w008 | 100.0% | 100.0% | 100.0% |

**The two 80-unit skills agree exactly in seven of the eight frames**, and in
the single mid-charge frame they differ by 3.8 points — about two rows of 52,
down from 7.5. **And the ORDER FLIPS**: the old statistic put slot 2 above slot
4, this one puts slot 4 above slot 2. A difference whose *sign* depends on the
statistic is a property of the measurement, not of the client.

What honestly remains is much smaller than the original caveat: a ~2-row
difference in one frame, which animation phase would explain and which the
metric's own boundary sensitivity would also explain, with nothing here able to
separate them. The claim "the two 80-unit skills agree" is CONFIRMED in seven
frames and unresolved at the two-row level in one — not the open question this
paragraph used to describe.

### 27.5 What E5 did NOT reach

Stated plainly, because a run that answers two of four questions and reports
four is how §25's own P7 nearly went unnoticed:

- ~~**P12, the spend's on-screen reset (`0x00D2`), is UNTESTED.**~~ — **DONE,
  §28: CONFIRMED**, the spent ring empties to 0.0%.
- ~~**P13, the cross-pool tax, is UNTESTED.**~~ — **DONE, §28: CONFIRMED**, and
  it settled the unit question — equal strikes, unequal rings. This is the half
  of GWW's on-use rule that no screen has ever shown, and the default bar's
  three adrenal skills at 80/120/80 are an unusually good instrument for it: one
  press should drop the other two by exactly one strike each, which at those
  costs is a *different* fraction of each ring.
- **P14, the outpost map-gate control, was not run.** §26.6's
  `MissionCliGetMap() == 1` gate therefore still rests on the disassembly alone.
- The **25 s wipe (`0x00D0`)** was not observed on screen either.

### 27.6 Two process notes worth keeping

**The first attempt failed for a reason the log stated in its second line.**
`--no-enemy` is the *harness's* default and the hostile needs `session.py
--enemy`; the run ordered an attack into an empty world, and `begin_attack`
returned silently because agent 10 did not exist. The server log said `NO ENEMY:
the world will contain the player and nothing else.` at line 2 and it was read
past. The harness's own verdict caught it (`RUN VERDICT RETRACTED`) rather than
letting eight screenshots of an unchanged bar be scored as a null result — which
is exactly what that retraction machinery is for, and the second time it has
paid for itself.

**`git add -A` in a shared worktree swept up another session's work.** Commit
`98806c0` carries a peer session's `test_spawn_burst.py` repair and ~32 lines of
`TESTS.md` alongside the adrenaline arc, under a message describing only the
latter. Nothing was lost and nothing conflicted, but the commit is wrong about
its own contents. It was left un-split deliberately: `git rebase -i` is
unavailable in this environment, and by the time it was noticed the peer had
committed on top, so a rewrite would have rewritten their work too. Recorded
here and in the following commit's message instead — `git status` before
`git add -A` is the habit that prevents it.

## 28. E6 — the spend, and the tax that proves the unit

**2026-08-21, run `20260821T134216`, loopback, build 38797, server at
`9916de8`.** Closes the first two items §27.5 left open. Predictions registered
before the client launched (`e6-predictions.md`), including the numbers.

### 28.1 The rig, and why the default bar is the instrument

Nine landed hits capped every pool, then **`attack:0` broke off the swing** so
no further gain could reach the readout, then slot 2 was pressed. The server
log is the proof that the window is clean: nine `0x00CF`s, the `0x00D2`, and
**zero `0x00CF` after it**.

The bar makes the run discriminating for free. Slots 2 and 4 cost **80**, slot
3 costs **120**, and slots 1 and 5–8 are non-adrenal controls in the same
frame. So one press taxes two rings by the same 25 units against different
denominators — and if the display taxed by a *fraction* instead, both would
drop by the same visible amount.

### 28.2 Our own wire, in ArenaNet's order

```
c2s USE_SKILL
s2c SKILL_ACTIVATED_BROADCAST(skill 317 via USE_SKILL)   0x00E4
s2c adrenaline spend: skill 317 (copy 0)                 0x00D2   <-- between
s2c cast animation: player casts 317                     0x00A0
```

Which is the measured retail shape from §26: `0x00E4` precedes the spend 38 of
38, and the property naming the skill follows it 39 of 39. The sender was
built to that census rather than to symmetry with the energy debit, and this
is the first time it has been seen going out.

### 28.3 P12 — the spent ring empties. CONFIRMED

Slot 2 goes from a full ring to **0.0%** — every row indistinguishable from the
pre-charge empty icon. `0x00821C00` writes both halves of the matched slot to
zero and the screen agrees.

### 28.4 P13 — the tax is 25 UNITS, not a share of the ring. CONFIRMED

Fill measured as the first row from the top carrying any changed pixel against
the empty baseline — E5's own null standard, no tuned threshold:

| slot | skill | cost | charged | after the press | predicted |
|---|---|---|---|---|---|
| 2 | 317 | 80 | 100.0% | **0.0%** | 0.0% |
| 3 | 318 | **120** | 100.0% | **80.8%** | 79.2% |
| 4 | 319 | **80** | 100.0% | **67.3%** | 68.8% |

**CORRECTED 2026-08-21, an hour after this section was written — the point
estimates above are NOT good to 1.6 points, and this paragraph originally said
they were.** They depend on a free parameter I never swept: how many changed
pixels make a row "filled". At the setting used above (any single pixel) the
agreement is 1.6 points; swept from 1 to 40 pixels, slot 3 ranges 65.4–80.8%
and slot 4 ranges 42.3–67.3%. E7 then showed that the ≥1 setting is positively
UNSAFE — it reported a fully empty ring as 100% full off three stray pixels in
one row (§29.4). So the precision claim is withdrawn. **What survives the sweep
is the entire finding**, and it survives at every single threshold:

| minpx | 1 | 5 | 10 | 20 | 30 | 40 |
|---|---|---|---|---|---|---|
| slot 3 (cost 120) drop | 19.2 | 19.2 | 19.2 | 21.2 | 25.0 | 34.6 |
| slot 4 (cost 80) drop | **32.7** | **36.5** | **36.5** | **42.3** | **44.2** | **57.7** |
| slot 2 (spent) | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |

Slot 4 loses more ring than slot 3 at every setting, and the spent ring reads
exactly zero at every setting. Those two statements have no free parameter in
them, and they are what the run is for. The discriminator:

```
slot 3 (cost 120):  ring dropped 19.2 points   (25/120 = 20.8%)
slot 4 (cost  80):  ring dropped 32.7 points   (25/ 80 = 31.2%)
```

**Both slots lost exactly one strike; they lost visibly different amounts of
ring — at every threshold, so the statement is parameter-free.** A proportional tax — a quarter off each, say — would have dropped them
by the same number of points, and it did not. This is `cmp esi,0x19 /
add esi,-0x19` at `0x00821C71` reaching the screen: the pool is carried in raw
units, 25 is the size of a strike, and the ring is `adrenaline_b ÷
skillData.adrenaline` with the skill's own raw cost underneath. §26.8's census
finding that 151 skills carry non-multiples of 25 is now visible rather than
tabular.

### 28.5 P14 — the controls hold. CONFIRMED

Slots 1 and 5–8 sit at **0 changed pixels** across the press, as they did
through all seven frames of E5. The tax reaches exactly the occupied adrenal
slots and nothing else, which is `0x00821C4C`'s `(skillId, skillCopy)` join
behaving.

### 28.6 The wipe is still unseen, and a near-miss worth recording

The 25 s timeout **did** fire on the wire — `adrenaline cleared: 25s out of
combat (0x00d0, 6B)` — about a second after the last scripted frame. The
teardown frame `final.png` is *not* evidence for it: measured against the empty
baseline it reads ~100% changed **on every slot including the two non-adrenal
controls**, so the whole frame is a different screen state and any adrenaline
reading taken from it would be an artifact. That is the aggregate-diff lesson
catching a false positive in the act, and the in-frame controls are what caught
it. ~~**`0x00D0` on screen remains open**, and wants a run that simply waits.~~ —
**DONE, §29.** The run that simply waited is below, and the artifact this
paragraph caught turned out to be the same class of error as the metric defect
§28.4 now carries.

### 28.7 Two measurement notes

**The first attempt (`20260821T133856`) was contaminated and the log said so.**
`S:0.5` does not break off an attack — the swing continued and two more gains
landed after the spend, which would have refilled the taxed pools and hidden
the very effect the run was for. `attack:0` is the clean stop: `begin_attack`
finds no agent 0 and clears `state["attacking"]`. The contamination was
detectable only because the server log lists every `0x00CF` in order; a
screenshot-only run would have shown two plausible rings and no way to know.

**Pixel-identity is too strict a null here, and E5's phrasing invited the
error.** The client re-renders with sub-threshold variation everywhere, so
"identical to the baseline" finds nothing empty even on a ring that is visibly
empty. E5's controls read 0.0% under a *threshold* of 24, not under equality;
this section uses the same threshold and says so. The intermediate attempt —
counting rows over a 30%-of-width threshold — is what produced §27.4's
unresolved discrepancy between two equal-cost skills, because that statistic is
sensitive to the icon art underneath the fill. **The boundary criterion (first
row carrying any change) is art-independent, and under it §27.4's anomaly does
not appear**: here the two 80-unit skills behave identically, one emptied to
0.0% and one taxed to 67.3% against a predicted 68.8%. §27.4's caveat should be
read as a defect of that metric rather than of the client.

## 29. E7 — the wipe, and a metric that lied

**2026-08-21, run `20260821T135905`, loopback, build 38797, server at
`fa601a0`.** The last screen-side item on this channel. Predictions in
`e7-predictions.md`, registered before launch.

The design is the whole point: charge every pool, break off with `attack:0`,
then **do nothing for thirty seconds**. The practice target never attacks, so
no damage re-anchors the clock — the only clock running is the one the last
`0x00CF` started.

### 29.1 The wire

Nine gains, then **exactly one** `0x00D0` and nothing after it:

```
[c1] s2c adrenaline cleared: 25s out of combat (0x00d0, 6B)
[c1] the player's adrenaline is gone: 25s out of combat
```

P18 CONFIRMED — `tick` drops the clock either way, so a wiped bar cannot
re-wipe, and one quiet period produced one message rather than a stream.

### 29.2 P15 and P16 — all three at once, and not early. CONFIRMED

Frames anchored by timestamp, never by filename. `attack:0` ran at 17:59:55, so
the last gain is at or just before it and the wipe is due ~18:00:20:

| frame | time | slot 2 (80) | slot 3 (120) | slot 4 (80) | controls |
|---|---|---|---|---|---|
| w003 | 18:00:08 | 100% | 100% | 100% | 0 |
| w004 | 18:00:16 | 100% | 100% | 100% | 0 |
| **w005** | **18:00:21** | **0.0%** | **0.0%** | **0.0%** | **0** |
| w006–w010 | 18:00:25–44 | 0.0% | 0.0% | 0.0% | 0 |

**The three rings empty together, in one frame step, with no intermediate
state anywhere in the run** — which is `0x00821B00` walking all eight slots and
firing the repaint once. Nothing drains gradually; there is no decay.

And the timing brackets the prediction from both sides: full at 18:00:16, empty
at 18:00:21, due at ~18:00:20. **No frame is empty before the 25 s mark**, which
is the half that matters — an early wipe would have meant the clock is anchored
somewhere other than the last gain.

### 29.3 P17 — the controls hold. CONFIRMED

Slots 1 and 5–8: **0 changed pixels in every one of the ten frames.** This is
the control §28.6 argued for after `final.png` read ~100% changed on every slot
including the non-adrenal ones. Here the wipe frame moves the three adrenal
rings and nothing else, so it is the wipe rather than a screen-state change.

### 29.4 The metric lied, and the controls are what caught it

The first pass over these frames reported **slot 2 back at 100% in the last
frame** — after a wipe, with nothing on the wire that could refill it. It was
not real. Slot 2's mean colour in that frame is the EMPTY value (110,80,35
against an empty baseline of 105,79,34; charged is 218,163,72). Three stray
pixels in the topmost row crossed the difference threshold, and the fill rule
in use — *the first row from the top carrying **any** changed pixel* — turned
three pixels into a full ring.

**That rule produced §28's numbers**, which is why §28.4 now carries a
correction rather than its original precision claim. Swept across sensible
settings the point estimates move by up to 25 points; the *findings* — a spent
ring at exactly zero, and unequal drops for equal strikes — hold at every
setting. E7 itself is immune because it contains no intermediate fill to
measure: 100% and 0% are threshold-independent, and the table above is
identical at minpx 10 and 25.

The general lesson is the one already in this repo's notes and freshly earned:
**a point estimate with an unswept free parameter gets over-read.** The check
worth running is the one with no free parameter in it, and where that is not
available, sweep the parameter and report what survives. Three runs in a row
have now had their headline numbers moved by a threshold choice — §27.4's
"anomaly" (a metric artifact), §28.4's precision (withdrawn), and this frame
(a false positive) — while every *qualitative* claim has survived untouched.

## 30. E8 — the outpost gate, and the overlay that is torn down

**2026-08-21, runs `20260821T140826` (outpost) and `20260821T141108`
(explorable), loopback, build 38797, server at `12ef6b1`.** The last
screen-side item on this channel, and the only NEGATIVE in the series.
Predictions in `e8-predictions.md`.

### 30.1 The confound, named first and defeated

§26.6's claim is read off `0x00542E43` alone: the fill is drawn only when
`MissionCliGetMap() == MISSION_MAP_GAME`. Testing it means sending a correct
`0x00CF` to a client standing in a town — and there is a specific, known reason
the run could produce a worthless null: **an outpost forbids attacking**
(§25/E5). No attack, no hit, no gain, and "the ring did not fill" would be a
statement about the attack rule rather than the display gate.

**It did not fire, and the reason is structural.** The harness's `attack:10`
does not click — it calls `begin_attack` SERVER-side, the same entry the
`ATTACK_AGENT` arm uses, and our server does not consult the map type. So the
outpost arm put **9 gains on the wire, exactly as the explorable arm did**, and
that precondition was checked before a single pixel was measured.

### 30.2 The A/B

Same map (148), same bar, same walk, same nine gains. One flag differs:

| arm | slot | fill@10 | fill@25 | mean RGB before | mean RGB after |
|---|---|---|---|---|---|
| **A outpost** | 2 (317) | **0.0%** | **0.0%** | (197,122,48) | **(197,122,48)** |
| **A outpost** | 3 (318) | **0.0%** | **0.0%** | (154,111,52) | **(154,111,52)** |
| **A outpost** | 4 (319) | **0.0%** | **0.0%** | (137,85,33) | **(137,85,33)** |
| B explorable | 2 (317) | 100.0% | 100.0% | (103,64,27) | (220,143,58) |
| B explorable | 3 (318) | 100.0% | 100.0% | (82,59,29) | (177,134,63) |
| B explorable | 4 (319) | 100.0% | 100.0% | (72,46,20) | (158,102,40) |

**P19 CONFIRMED.** In the outpost the three rings do not move — and not merely
"below threshold": the mean colour of every adrenal slot is **byte-identical
before and after nine gains**. **P20 CONFIRMED**: the same rig, one flag
changed, fills all three. Non-adrenal controls sit at 0.0% in both arms.

### 30.3 The overlay is torn down, not merely unfilled — and the colours say so

The result is better than the null it was designed to produce. Compare the two
arms' *starting* states: an uncharged adrenal icon in an EXPLORABLE is **dark**
(103,64,27), while the same icon in an OUTPOST is **bright** (197,122,48) —
brighter than the explorable's fully-charged state is dark. So the outpost is
not showing an empty ring; it is showing **no ring at all**.

That is exactly what `0x00542E43`'s `jne` path does, and this is its first
confirmation from outside the disassembly: the branch sends msg `0x59` with a
NULL payload, `GmCtlSkImage` substitutes `{0,0}` and **destroys the overlay**
(`call 0x631220`). Three distinct on-screen states, all now observed:

| state | slot 2 mean RGB | what it is |
|---|---|---|
| outpost, any adrenaline | (197,122,48) | no overlay — the plain icon |
| explorable, 0 units | (103,64,27) | overlay present, ring empty |
| explorable, full | (220,143,58) | overlay present, ring full |

The darkening a player reads as "not ready yet" is therefore **part of the
adrenaline overlay**, not a property of the icon — which also retires, from the
other direction, §25's early guess that slot darkening might be an
affordability grey. It is neither affordability nor the selection border: it is
the empty state of a ring that only exists where the ring is drawn.

### 30.4 What this closes, and the one thing it does not

Every screen-side claim about this channel is now observed: the charge (§27),
the spend and the cross-pool tax (§28), the wipe (§29), and the map gate here.
**What is still static-only** is the *reason* for the gate — nothing observed
says why ArenaNet tears the overlay down in towns rather than leaving a stale
ring, and the disassembly does not say either. Not worth a probe; worth not
claiming.

## 31. E9 — the blink warning, and we were already producing it

**2026-08-21, run `20260821T141806`, loopback, build 38797, server at
`dc1bbc8`.** Raised by the owner from GWW's Adrenaline page — *"A visual
warning appears, with partially filled skills will begin blinking"* — a
behaviour §§25–30 never tested and never mentioned. Predictions in
`e9-predictions.md`.

### 31.1 Why §29 was silent on it rather than negative

Two independent reasons, either sufficient. **E7 capped every pool**, and the
wiki's warning is for PARTIALLY filled skills, so nothing was eligible to
blink. And **E7's frames were 5–8 s apart** through the warning window, where a
blink is sub-second and aliases to nothing. A run can be clean, pass every
prediction, and still be blind to a whole behaviour — which is the argument for
reading the wiki against a finished result, not only before it.

### 31.2 The mechanism was already in §26, unrecognised

`0x00CF`'s handler fires UI event **`0x10000058`** carrying `{agent, f32}`,
the float loaded from `.rdata` `0x009495B4` — **MEASURED bytes `0000c841` =
25.0**, the timeout itself. `GmSkSlot` forwards it as msg `0x5A` to
`GmCtlSkImage`, whose own assert names it:

> `GmCtlSkImage:1483` — *"Clearing the adrenaline timer on a skill image is
> currently not supported. Bug Austin about this."*

The handler stores the float (`fstp [edx+0x10]`, `fstp [edx+0x14]`,
`mov [edx+0x18],0`) and never accumulates. **So the countdown is CLIENT-side
and armed by a message this server already sends.** §26 recorded that event as
"the strike flash" with the 25.0 noted only as a fixed constant; it is the
warning timer, and the constant is the timeout.

### 31.3 The measurement

Four gains left slot 3 **partial** (100/120) while slots 2 and 4 capped —
so one frame holds all three categories. Mean luminance, 26 frames ~1 s apart;
the wipe lands at `hold019`:

| slot | state | range | direction changes | verdict |
|---|---|---|---|---|
| 1 | non-adrenal | **0** | 0 | flat |
| 2 | **capped** | 87 | **1** (the wipe step) | flat |
| **3** | **PARTIAL** | **20** | **9** | **OSCILLATES** |
| 4 | **capped** | 61 | **1** (the wipe step) | flat |
| 5 | non-adrenal | **0** | 0 | flat |

**P21 CONFIRMED, P22 CONFIRMED** — the controls are flat to a range of *zero*,
so the oscillation is not a global flicker.

**And the blink goes fully OFF, not dim.** Slot 3's post-wipe luminance — ring
gone — is 62. During the warning window slot 3 hits exactly 62 at `hold015` and
`hold017` and returns to 74–75 between them. The warning hides the fill
entirely and restores it, a square wave aliased at 1 s sampling.

**A finding the wiki implies and this shows: capped skills do NOT blink.**
Slots 2 and 4 sit rock-flat at 156 and 111 through the entire warning window,
changing exactly once — at the wipe. Only the partially filled ring warns,
which is GWW's sentence read strictly.

### 31.4 Corroborated by the owner, watching

**OBSERVED, owner, live during this run: "i watched it blink, seemed good."**
That is worth more than it looks. Three times in this series a headline number
came from a pixel metric that turned out to be wrong (§27.4's phantom anomaly,
§28.4's withdrawn precision, §29.4's false 100%), and a human eye on the actual
screen is the one witness that shares none of those failure modes.

### 31.5 The answer to the question that prompted it

**Yes — we capture it, and we were capturing it before anyone asked.** No
server change was made for this section. The server sends nothing at all
between the last `0x00CF` and the `0x00D0` 25 s later; the blink is the
client's own timer, armed by the gain message, and it appeared the first time
anyone sampled fast enough to see it. **P23 CONFIRMED.**

Worth stating plainly because the opposite was equally possible: had the
warning ridden its own opcode, this channel would have been incomplete and
nothing in §§25–30 would have revealed it.

## 26.12 Opcode 231 — the recharge family's *indefinite* case

**Settled 2026-08-21** (§26.11 item 4), static plus corpus, verified CONFIRMED
by an adversarial re-derivation. §26.3 declined to name it on one handler read;
this is the evidence it asked for.

**The chain, each link with exactly one way in** (`codescan --xrefs`): RECV
table `0x00BC8F68` → stub `0x0091F6E0` (0 direct calls, 1 data word at
`0x00BC97E0`) → thunk `0x00814980` → worker `0x00822D10`. So the only path into
this worker is opcode 231 arriving off the wire; no client-side code disables a
skill through this door. Shape `[agent_id, u16 skillId, u32 skillCopy]`, 12 B,
from `msgshape.py` — **CORROBORATED by a lineage with no shared ancestry**,
gw-preservation's `network-log-explorer` typing `0x00e7` as the identical triple.

**What it does**, MEASURED with bytes:

```
00822D79  8b4604              mov eax,[esi+4]      ; SAVE the old adrenaline_b
00822D7C  c70600000000        mov [esi],0          ; adrenaline_a = 0
00822D82  c7460400000000      mov [esi+4],0        ; adrenaline_b = 0
00822D89  85c0 / 7419         test eax,eax / je    ; repaint only if there WAS any
00822D99  push 0x10000059     ;  the adrenaline repaint, payload {agent}
00822DA9  fld  [0x948654]     ;  +INFINITY (bytes 00 00 80 7f)
00822DC3  c74608ffffffff      mov [esi+8],0xFFFFFFFF   ; recharge = NEVER
00822DBB  push 0x1000005d     ;  {agent, skillId, skillCopy, +inf, +inf}
```

**CORRECTION to [studies/skillcast](../skillcast/FINDINGS.md) §5**, which reads
*"adrenaline_a = 0; if (adrenaline_b) fire 0x10000059; adrenaline_b = 0"*. The
image saves the old `adrenaline_b` **first** and zeroes **both** halves before
testing the saved value. The guard is on the previous adrenaline, and that
detail is what makes the next paragraph decidable.

### The zeroing is PURPOSEFUL — and NOT special to 231

The four recharge-family workers read side by side settle §26.3's question:

| opcode | what it means | touches adrenaline? |
|---|---|---|
| **229** `0x00E5` SKILL_RECHARGE | unavailability BEGINS, timed | **zeroes both halves** — `0x00822C00`/`0x00822C06`, a sequence **byte-identical** to 231's |
| **230** `0x00E6` SKILL_RECHARGED | unavailability ENDS | **no** — its entire matched body is `mov [ecx+8],0` |
| **231** `0x00E7` | unavailability BEGINS, indefinite | **zeroes both halves** |
| **232** `0x00E8` | describes a partial recharge | **no** |

**The rule is "when unavailability begins, the pool is dropped"**, and it is
229's rule as much as 231's — so any model treating adrenaline-clearing as a
property of *disabling* is wrong. **WIKI corroborates from outside the binary**:
GWW's Adrenaline page says *"Disabled skills also lose all their adrenaline
while recharging skills cannot rebuild adrenaline"* — both halves, matching both
workers.

### The name is NOT being promoted, and that is the finding

`studies/skillcast` §5 proposed **SKILL_DISABLED** (explicitly INFERRED). It is
defensible in meaning and **collides with a physically different channel**: the
client keeps a per-slot *disabled* bitmask at `HotKeyState+0xA4` (GWCA's
`Skillbar.disabled`), written by opcodes **100/101** (`bts`/`btr` at
`0x00822085`/`0x0082208A`; GWCA names them HERO_SKILL_STATUS /
HERO_SKILL_STATUS_BITMAP) and read by accessor `0x00816F40` — and **231 never
touches it**. "Disabled" also fails to separate 231 from 229, since GWW uses the
word for Dervish avatars being *"disabled for 45 seconds"*, which is a TIMED
disable and therefore 229's job.

`SKILL_RECHARGE_INDEFINITE` is proposed instead — it sits in the existing
register beside SKILL_RECHARGE/SKILL_RECHARGED, names the field 231 actually
writes, and carries the discriminating fact. **It stays INFERRED and out of
`schema/overrides.json`**: witness 1 (the handler) is strong, witness 2 (the
wire) is n=1, and that is below `studies/smsgnames`' two-witness bar. **No
ArenaNet string names this message** — the worker contains zero asserts and
pushes zero string pointers, and the positive control is green (the identical
grep finds `adrenalin`, `hotKeyState` and ChCliSkill's own asserts). No upstream
names it either: absent from the maintained GWCA, Headquarter, OpenTyria and
the network-log-explorer name map.

### The single wire witness

**Exactly one `0x00E7` in 114,985 live messages** — capture `20260817T231139`,
t=105.145, naming **skill 2**, which `textrec.py` resolves through the client's
own string table to **"Resurrection Signet"**. After it, skill 2 appears in no
message of any kind for the remaining **116 seconds** of the tape. That is
retail's one-use-per-morale-boost rule, and a signet that cannot come back until
a condition the server controls is exactly what an *indefinite* recharge is for.

**One honest wrinkle, flagged rather than smoothed:** the cast began
(`0x00E4`) at t=99.646 and the `0x00E7` landed at t=105.145 — 5.499 s, against
skill 2's own table activation of 3.0 s. A co-firing `0x00E3` supports "at cast
end", but the interval does not match the table and nothing here explains the
difference.

### Open

- **Does 231 make a skill uncastable, or only paint the slot?** The DISPLAY path
  is proved end to end — `GmSkSlot 0x00543181` calls the recharge accessor,
  recognises `INT_MAX`, and loads the same `+inf` constant, skipping the sweep
  arithmetic. The INPUT gate is untraced.
- **What re-enables it.** WIKI says a morale boost; which opcode carries that is
  unknown, and the observed connection never re-armed skill 2.
- **Opcode 232 has ZERO occurrences too** — a second fully-implemented,
  never-observed handler in this same family, alongside 209 and energy property
  33. Three now, which starts to look like a pattern rather than three accidents.

## 26.13 A tool defect found sideways: "which agent is me"

Recorded here because the adrenaline pass found it and in
[studies/morale](../morale/FINDINGS.md) because that is whose tool it is.

Establishing that no adrenaline message ever names a non-observer needed a
sound answer to *which agent is the observer*. The obvious shortcut —
**take the first `0x0059` and call its agent id ours** — is wrong, because
`0x0059` is `AGENT_CREATE_PLAYER` and the server broadcasts one for **every**
player in the instance: 16 to 56 of them in a busy outpost. The first is
whoever the server happened to send first.

`toolkit/authsrv/moralescan.py` shipped exactly that shortcut, with a comment
asserting *"field 2 is the receiving player's own agent id"*. **MEASURED against
the self-scoped anchor: the two rules agree on 24 connections and DISAGREE on
20 of 44** — 45% wrong — e.g. naming agent 16 where the observer is 767.

**The sound anchor is property 41 (MAX ENERGY)**, which §23 measured as
self-scoped across 97 sightings; an independent route (`0x0199`'s player number
mapped through `0x0059`'s pairs) agrees with it wherever both resolve, 40 of 40.
`moralescan.py` now uses property 41 and **does not fall back** to the old rule
— a connection with no property 41 leaves the flag unset, which is the honest
answer, where guessing would restore the 45%.

**Nothing published was wrong**, and that is worth stating precisely rather than
implying either more or less: `studies/morale`'s census claims count VALUES
across all agents ("the only non-zero `0x00EE` is −15", "the only `0x009C` that
is not 100 is 85") and never consult the flag. Re-running the census after the
fix reproduces both numbers exactly — 40 sightings, 83 sightings, same two
departures. So this is a **latent** defect corrected before it was relied on,
not a result being withdrawn.

The general shape is one this repo keeps meeting: a fixture that silently
resolves to the wrong thing turns every assertion behind it into a no-op, and
the defence is an anchor the artifact can refute rather than a plausible-looking
first element.

## 36. The client runs its OWN expiry timer — but it does not forget the effect (`--probe effect_silent_extend`, 2026-08-21)

> **Numbering note, 2026-08-21 — this section was written as §32, and so was
> §32 below.** Two `## 32.` headings collide as one markdown anchor, which made
> every cross-reference to "§32" ambiguous, including `PLAN.md` §8's adrenaline
> entry. **This** one moved, because §32 below is E10 and `§27`–`§32` = E5–E10 is
> a run `PLAN.md` cites by position. Old references resolve here: `studies/isle`
> §32/§32.7/§32.8 and `effects.EffectTable.apply`'s docstring now say §36. The
> section keeps its place in the file rather than moving to the end — this
> document is already non-monotonic (§26.12/§26.13 sit after §31) and a 248-line
> move is a worse diff than an out-of-order number.

**Answers the question `effects.EffectTable.apply` had left open** — its docstring
ended *"how retail refreshes one is NOT FOUND"*, and
[studies/isle §8.6](../isle/FINDINGS.md) had just answered the WIRE half: retail
refreshes by sending nothing and delaying the `0x0044`. A capture cannot see a
screen, so this probe read the other half. Run `20260821T173954`, verdict PASS,
all seven steps confirmed on the wire in `gamesrv.log` before any frame was
opened (`0x0042` 20 B, `0x0044` 10 B, three declared refusals silent).

**Design.** CONTROL: skill 478 for 10.0 s, removed at exactly `apply + duration`
— the shape our server emits today, which proves a removal removes. TREATMENT:
skill 480 for 10.0 s, then **25 seconds of server silence**, then a late
`0x0044`. Screenshots every ~2.35 s throughout.

### 36.1 The prediction was half right, and the half it got wrong is the finding

Pre-registered: *"the icon is STILL DRAWN at +13 s and +20 s with the timer bar
drained to empty, and it goes only when the late `0x0044` lands."* What happened:

- **The live icon vanished on the client's own timer, with no packet.** The
  Burning icon was gone roughly 15 seconds before the late `0x0044` was sent. The
  visible window was ~9 s against a 10.0 s stated duration, not the ~25 s the
  "waits to be told" reading requires. **The client owns the expiry.**
- **But the slot did not go empty.** Between self-expiry and the removal the
  client holds a **static, heavily faded ghost of the same icon** — an amplified
  diff reproduces the flame sprite's exact shape — and clears it the moment the
  `0x0044` arrives.

**Neither naive reading would have got this.** "Is the icon there?" answers *no*;
a pixel diff answers *yes*. The state is a third thing: **presented as expired,
still slotted.**

### 36.2 Why the ghost is a measurement and not my eye

| comparison | slot region | control region elsewhere on the same HUD row |
|---|---|---|
| consecutive frames, same state (6 pairs) | **0.000** | 0.000 |
| across the late removal (4 pairs) | **6.829** | **0.000** |

The noise floor is *exactly* zero — the camera is static, so same-state frames
are byte-identical. The change is **6.829 in the slot and 0.000 in a same-sized
control patch beside it**, which is what rules out lighting, animation and any
global render change. And the seven state-B frames spanning **+25.8 s to +39.9 s
are byte-identical to each other**, so this is a held static state, not a fade
still in progress.

### 36.3 What this decides for our own substrate

**`REMOVE-then-APPLY` is NOT required, and silence is NOT free.** The late
removal landed correctly on an effect the client had already expired visually —
no refusal, no desync — so the pair this table emits is not load-bearing for
correctness. But an effect held open by silence **stops being visible to the
player at its stated duration**. So:

- for anything the player must SEE for time T, the duration we send must cover T
  (or the effect must be re-applied); silence extends the server's bookkeeping,
  not the player's experience;
- `effects.py` is still not changed behaviourally on the strength of this — what
  changed is that the cost of each option is now measured rather than assumed.

### 36.4 The question this opens, and it is cheap

**Do retail players see the ghost too?** §8.6's Isle episodes ran +1.25 s to
+55.0 s past their stated durations on ONE apply each, so by this client's rule
the operator spent most of that time looking at a faded icon while the condition
still cost health — the Disease that killed them outlasted its 10.0 s duration
many times over. That is either a real quirk players live with, or retail sends
something we have not identified for environmental sources. **One screenshot of
a Student's ring taken 20 s after entry settles it**, and it costs nothing on the
next Isle trip. Until then, this section describes OUR client's response to OUR
messages, which is exactly what it was built to measure — and no further.

### 36.5 Does this apply to RETAIL? The message shapes are identical, and the only gap left is the build

§36.4 asked whether retail players see the ghost too, and said one live screenshot
would settle it. That overstated the cost: **most of it settles offline**, because
the client is the referee and the question is whether it can tell the two servers
apart.

Decoded with `bufflog` rather than by hand — a first pass scanning raw bytes for
`0x0044` found matches inside float payloads (`00803f` is `1.0f`) and was thrown
away:

| source | message |
|---|---|
| **retail**, Isle Students | `0x0042 [target 25, skill 482, field3 0, buff 117, duration 10.0]` |
| **retail**, Isle Students | `0x0042 [target 25, skill 2077, field3 0, buff 117, duration 10.0]` |
| **ours**, the probe | `0x0042 [25, 478, 0, 1, 10.0]` |
| **ours**, the probe | `0x0042 [25, 480, 0, 2, 10.0]` |

**Field for field the same shape** — same target slot, `field3 = 0` on both sides,
the same `10.0` f32 duration, and condition skill ids (type_code 8) in both. The
client has nothing in the message to distinguish our application from ArenaNet's,
so it should take the same path.

**THE ONE GAP IS THE BUILD, and it is worth naming rather than waving past.** The
retail capture is **38849**; the probe above ran on the loopback client, which was
**38797** — 52 builds apart. Effect rendering is unlikely to have moved, but
"unlikely" is not a measurement, and this repo has been wrong about a version
assumption before. **CLOSED in §36.7 by rebuilding the loopback client at 38849
and re-running: identical to three decimals.**

### 36.6 Closing the build gap meant building a 38849 loopback client, and a guard stopped the first attempt

**The gap was closeable offline** — the retail build is on disk, since the
operator's own install auto-updated to 38849 (`RUNBOOK` §"the build gate's
'service' is a proxy"). The loopback client was two builds behind the service
anyway, so rebuilding it is maintenance the runbook already prescribes after
every ArenaNet update rather than work invented for this question.

`dump_dh_params.py` on the 38849 install first, because that is the runbook's own
go/no-go: **`GO.`** — `g = 4`, 512-bit prime, struct at VA `0x00a910d8`, so the
crypto scheme did not move. Then `make_custom_client.py` + `make_run_dir.py`:
`B == g^b mod p -> True`, classified `ours`, updater killed, filed at
`vault/run/2026-08-20_21511009c460/`. `dhbuild.py` audits the whole vault clean.

**THE FIRST LAUNCH WAS REFUSED, AND THE GUARD WAS RIGHT.** `contentids`:

> `map 146 0x1B97D: the two archives bind this id to DIFFERENT FILES` — server
> row 7982 is 1,300,036 B crc `0xA0AE500A`, client row 177262 is 1,300,044 B crc
> `0x33F1A289`.

So **build 38849 changed map 146's geometry** — 8 bytes longer, different CRC —
and the server's study archive still holds the old one. Its own words for why
that matters: *"the server would path against geometry the client is not drawing,
and the run would look like it worked."* That is a silent-wrong-answer class of
failure caught before a single packet, and it is the second guard this week to
pay for itself.

**Resolved without touching anything shared.** `vault/dat_study/Gw.dat` is used by
other arcs and other sessions, so re-cutting it to 38849 is not a call this arc
makes alone. `RURIK_DAT` pointed at the 38849 client's OWN archive makes the pair
the same generation by construction — `test_contentids.py` §1 calls that *"the
only pairing in this vault that is coherent today"* and it is what the
2026-08-14 compass run used. **Recorded as owed maintenance:** the server's study
archive is now a build behind the client's, and every default-paired run inherits
that.

With that pairing the guard went green — **"content file ids: 12 of 12 map row(s)
agree across both archives"** — and the launch was then refused a SECOND time, by
a different guard and equally correctly:

> `REFUSING to launch ...6-08-20_21511009c460\Gw.exe` — *"no firewall cage
> names this binary at all. This client carries OUR Diffie-Hellman parameters."*

A newly built ours-DH binary is not in any cage rule, and `PLAN.md` §6.2 is
absolute that such a client must never reach the real service — it does not fail
cleanly, because Stage A completes first with whatever credential the client
autofills. Caging is an **elevated** step by design (`isolate_client.ps1`, no
arguments, which enumerates every client under `vault/run` rather than the single
hardcoded path that once left one uncaged for a day). **So the 38849 re-run is
staged and blocked on one elevated command, and the build gap in §36.5 stands
until it runs.** Everything else about the rebuild is done and verified.

### 36.7 The gap is CLOSED: 38849 behaves identically, so retail players see the ghost

Same probe, same plan, the **38849** loopback client — the exact build the Isle
capture came from. Run `20260821T180010`, verdict PASS, all seven steps confirmed
on the wire first.

| measurement | 38797 | **38849** |
|---|---|---|
| live-icon windows | 2 | 2 |
| treatment window | +16.5 .. +23.5 s | **+16.4 .. +23.4 s** |
| same-state frame noise floor | 0.000 | **0.000** |
| slot change across the late removal | 6.829 | **6.829** |
| control patch across the same removal | 0.000 | **0.000** |

**Identical to three decimal places on a different build.** In both, the live icon
dies ~16 s before the late `0x0044` is sent, and the faded ghost holds until it
arrives.

**So the chain closes without a live run**, and each link is measured rather than
assumed: retail's Student application and our probe's are field-for-field the same
`0x0042` (§36.5); the client cannot tell them apart; and the client's behaviour is
now measured on retail's own build. **A retail player standing in a Student's ring
sees a live condition icon for its stated ~10 s and a dead-looking faded one for
the rest of the stay, while the condition keeps costing health the whole time.**
The Disease that killed the operator in `20260821T152147` did most of its damage
behind an icon that had already visually expired.

*Label: OBSERVED for the client behaviour on both builds and for the message-shape
identity; RECONSTRUCTION for the retail player's experience, since we render our
own messages and not ArenaNet's.* **The one thing not excluded** is an unidentified
opcode that refreshes the client's timer — §8.6 found nothing on the effect channel
in those windows, and no other message is known to touch it, but "we did not find
one" is weaker than "there is none". A single retail screenshot 20 s into a ring
would convert the last link from inference to observation, and it is now worth
exactly that one frame and no more.

### 36.8 SCOPE CORRECTION: the silent extension is ENVIRONMENTAL-ONLY, and §36.3 overreached

**Raised by the owner, 2026-08-21: "any credence to thinking these condition
circles are some sort of hard-coded exception that combat doesn't follow?"**
There is, and checking it found an overreach in this arc's own handoff.

Every effect episode in the vault carrying a duration, scored by close residual
and partitioned by how it was applied:

| applied by | n | residual |
|---|---|---|
| **environmental** — the Isle's torches (984/998/999) and Students (479-486, 2077) | **15** | **LATE, +1.25 s to +55.0 s** |
| cast or attack — 160, 364, 348, 814, 179 | 78 | **never late.** Exact, or early (a cure) |

**All 15 late closures come from the two rung-8 runs** — the only sessions where
the operator deliberately stood in range. Not one cast- or attack-applied effect
has EVER closed late, across six captures and five skills.

**And the same environmental skills close exactly when nobody loiters**, which is
what rules out "those skill ids are special": skill 480 at `-0.00` and `+0.00`,
984 at `+0.00`, 998 at `-0.00` in the rung-6 roster run, and 998/999 at `-0.04`
in the rung-8 run itself once the operator had stepped away. **The variable is
standing in the source's radius, not the skill.**

**SO §36.3's HANDOFF WAS WRONG IN SCOPE.** It said this table "emits a shape
retail does not", reasoning from the silent extension to how our server should
refresh a cast effect. Those are two different mechanisms and the corpus separates
them cleanly. Worse, the cast side does not say what §36.3 implied either:
`effects.EffectTable.apply` already records that retail's 15 overlapping
re-applications are **all under 0.5 s — same-instant doubles, not re-casts** —
each carrying a NEW buff id while the first episode still closes on its own
duration. So retail **stacks** those; it does not extend them.

**The honest state, per mechanism:**

- **Environmental / persistent-area:** retail refreshes silently and delays the
  `0x0044`. OBSERVED, 15 episodes. Our server has no analogue of this source type,
  so there is nothing here to copy or to fix.
- **Cast or attack:** retail has **no witnessed case of a live effect being
  deliberately extended at all.** Not silently, not by REMOVE-then-APPLY, not by a
  refreshing re-apply. The 15 overlaps are simultaneity, not extension. **Our
  REMOVE-then-APPLY is therefore unwitnessed either way — it is neither confirmed
  nor refuted**, and §36.3 should not have leaned on the Isle to judge it.

**And the Isle is a training area**, which is the general form of the owner's
point and worth carrying beyond this section: its torches and Students are
pedagogical props built to apply one condition on contact. Generalising from them
to combat is a scope error of exactly the kind [§4](#) warns about elsewhere, and
this section exists because it was made here.

**What survives unchanged.** §36.1-36.2's client behaviour (self-expiry at the
stated duration, then a held faded ghost until the removal) is a fact about the
CLIENT, which receives one `0x0042` and a late `0x0044` and cannot know what
applied them. §36.7's conclusion that a retail player in a Student's ring watches
a ghost also stands — that is the environmental case, measured on its own build.
Only the generalisation to combat is withdrawn.

### 36.9 The re-cast run ABORTED on a bad skill pick, and the pick was a scope error

Run `20260821T184758`, plan `isle_rung8d_recast.txt` (sha256 `beb5ba72...`), seals
AGREE, 3 keys, 2 connections. **Aborted by the operator at the tooltip step, and
correctly.** The plan named skill **348** as "a Warrior SHOUT, recharge 4 s against
a duration observed at 10.0 s ... already on the operator's bar". The bar skill is
**364 = `"Charge!"`**, and the operator read its tooltip: **5 energy, 20 s
recharge** against a 10-12 s duration. Recharge exceeds duration, so it can never
overlap itself and the block cannot run.

**THE ERROR IS WORTH MORE THAN THE RUN, and it is a scope error of the same family
as §36.8's.** The plan's basis for "already on the operator's bar" was that 348
appears three times in capture `20260819T132414`. **That capture is a TOWN
DISTRICT (map 238)**, where other players are casting constantly — an effect
landing in a capture means somebody nearby cast it, not that it is ours. The
capture cannot distinguish the two, and the plan treated an ambient observation as
a fact about our own character. *Appearing in a capture is not the same as being
on our bar*, and nothing in the effect channel carries a source agent to say
otherwise (§8.6's own premise, used here against itself).

**What the aborted run still banked.** Six `skill 160` episodes (Windborne Speed,
the Master of Winds control) and one `skill 364` at `field3 10 / dur 10.0`, all
closing exact — and the operator's tooltip read is the **first operator-confirmed
check of the `364 = "Charge!"` binding**, which [studies/isle §"Rung 8 prep"] had
from GWW alone. The energy column agrees at 5. The rank-13 damage block never ran.

**The requirement, stated mechanically so no one has to guess a name again.** The
block needs a **self-targeted effect whose RECHARGE is shorter than its DURATION**
— both numbers readable off the tooltip by the operator. Measured from the
client's own `s_skill` table via `toolkit/clientscan/skilltable.py`, **build
38849**, filtered to self-target (`target == 0`), profession common-or-Warrior,
playable:

| recharge | duration r0 → r15 | id | type | cost |
|---|---|---|---|---|
| 10 | 10 → 20 | **316** | **Shout** | 5 energy |
| 4 | 10 (flat) | **348** | **Shout** | 4 adrenaline |
| 4 | 1 → 15 | 366 | Shout | 4 adrenaline |
| 4 | 8 (flat) | 346 | Stance | 5 energy |
| 4 | 10 (flat) | 1701 | Stance | 5 energy |
| 2 | 8 (flat) | 1142 | Stance | 1 adrenaline |

**Prefer a SHOUT over a stance, and the reason is not aesthetic.** WIKI (GWW,
"Stance"): *"Only one Stance can be active at any time … using a new Stance will
replace the previous one."* Re-casting a stance is therefore governed by stance
exclusivity and would answer *"how does a stance replace itself"*, which is not
the question §36.8 left open. Shouts carry no such rule. **316** is the cleanest
candidate — energy cost, and at the operator's Tactics ~10 its duration is ~16-17 s
against a 10 s recharge. An adrenaline shout (348, 366) is also fine and has one
advantage: adrenaline charges by hitting, so the block can ride on top of the
rank-13 bench swings instead of needing its own setup.

**348 HAS A NAME as of the same day, from a different arc: it is
`"Watch Yourself!"`** (§33.6, reported by the operator after another run and
agreeing with the client's table on profession, attribute and every checkable
field). That makes it the strongest starting suggestion here — a core Warrior
Tactics shout, 10 s flat against a 4 s recharge, and its adrenaline cost is an
ADVANTAGE rather than a nuisance because the rank-13 bench block already has the
operator swinging: adrenaline charges by hitting, so the re-cast test can ride on
top of the swings instead of needing its own setup.

**But confirm it on the bar before sealing a plan around it** — that is the whole
point of this section, and 348 being named does not make it owned. **Which of
these the operator actually owns is not knowable from a capture.** The next plan
must be built around a skill the operator reads off their own bar, with the
tooltip's recharge and duration quoted back.

## 32. E10 — the recharge gate, read from the residue

**2026-08-21, run `20260821T190847`, loopback, build 38797, server at
`26ea691`.** §26.11 item 1, the last loopback-testable item on this channel.
Predictions in `e10-predictions.md`. **The run's designed readout failed and the
run still answers**, which is the part worth reading.

### 32.1 The rig

Bar `[316, **373**, 318, 319, 320, 321, 322, 323]`. Skill **373** costs 120
units and recharges **12 s**; **318** costs the identical 120 and recharges 0.
So treatment and matched control differ *only* in the recharge, and any
divergence cannot be a denominator artefact — the thing §28 showed matters.

The wire did exactly what the test needs: 9 gains capped everything, the spend
of 373, `SKILL_RECHARGE(skill 373, 12s)`, then **4 gains inside the window**,
`SKILL_RECHARGED`, then **2 gains after**. P26 met — the client was sent the
gains and does the per-slot application itself, so the gate under test is its own.

### 32.2 The designed readout is CONFOUNDED, and the data says so itself

| frame | time | s2 (373) | s3 (318) | s4 (319) |
|---|---|---|---|---|
| charged | 23:09:46 | 100.0% | 100.0% | 100.0% |
| post-spend | 23:09:52 | **100.0%** | 80.8% | 63.5% |
| in-window | 23:09:59 | **100.0%** | 100.0% | 100.0% |
| after expiry | 23:10:05 → 23:10:23 | **40.4%** | 100.0% | 100.0% |

**Slot 2 reads 100% immediately after being spent to zero** — and then *drops*
to 40.4% with no spend and no clear on the wire. Adrenaline cannot fall on its
own, so the 100% is not adrenaline: it is the **recharge sweep**, the overlay
`GmSkSlot` draws from the same accessor §26.12 traced, in the same rectangle as
the fill. The internal contradiction is the proof, and no external assumption is
needed for it.

**This is a design error, not a client behaviour.** Testing a *recharge* gate
required a skill with a recharge, which necessarily puts a recharge sweep on the
one slot being measured. E6 never hit it because 317 recharges in 0 s. The two
signals are confounded by construction, and any P24 verdict read off the
in-window frames — either way — would have been the sweep.

### 32.3 The residue answers it anyway

Once `SKILL_RECHARGED` clears the sweep, slot 2's pixels are the fill alone, and
the two hypotheses predict numbers three-fold apart:

| | 373's units | fill | measured |
|---|---|---|---|
| **gate HELD** — 4 skipped, 2 land | 0 + 50 | **41.7%** | **40.4%** ✓ |
| gate FAILED — all 6 land | 150 → capped 120 | 100.0% | — |

**40.4% is 21 of 52 rows; 41.7% is 21.7.** Within one row, and the same
1–2 point agreement E5–E9 produced. **P24 CONFIRMED** — the client skips a
recharging slot, so `0x008219C0`'s single line reaches the display. **P25
CONFIRMED**: the matched 120-cost control refilled 80.8% → 100% from those same
messages, so the skip is specific to the recharging slot and not a dead wire.
**P27 CONFIRMED**: the slot became eligible the moment the recharge expired.

Two independent witnesses now stand behind this rule — this measurement and
GWW's *"recharging skills cannot rebuild adrenaline"* (§26.11 item 3) — where
before there was one line of disassembly.

### 32.4 The lesson, which is the fourth of its kind here

E5 mis-measured on icon art, E6 on a too-strict null, E7 on a whole-frame state
change, and E10 on an overlay sharing the fill's rectangle. **Every one was
caught by an in-frame control or an internal contradiction, and none by
re-reading the code.** The rule this series keeps re-learning: when a readout is
visual, the thing that saves you is another region of the same frame that must
not move — and when a value moves in a direction the mechanic forbids, believe
the contradiction over the metric.

**Still open on this channel, and NOT loopback-testable:** whether a spend
restarts retail's 25 s clock (§26.11's divergence). Our server says no and the
corpus cannot arbitrate — no spend sits inside any of the 15 sampled clear
windows. That needs a **live** capture of a spend followed by 25 quiet seconds,
which is a human-driven run under `PLAN.md` §6.2, not a loopback one.

## 33. The timeout anchors on the last GAIN — a live capture, by 7 ms

**2026-08-21, capture `20260821T205552`, LIVE against the real service**, plan
`adren_spend_clock.txt` sealed before launch (sha `0e73d3ae…`, `plan_sealed:
true`, 3 keys tapped). The last question on this channel, and the only one a
loopback run could not answer.

### 33.1 The question, and why only a live run could settle it

Our server drops a charged bar 25 s after the last GAIN, and `AdrenalinePool.use`
deliberately does not restart that clock. GWW says adrenaline is lost after 25 s
"out of combat" and casting is plainly combat, so the rival reading was at least
as intuitive. **The corpus could not arbitrate**: not one of the 15 isolated
`0x00D0` clears had a `0x00D2` spend anywhere in its window. Only a session that
*creates* that case could decide it, and only retail's own server could be the
witness.

### 33.2 The design, and the one thing it had to avoid

The discriminator is a **gap between the last hit and the spend** — without it
both hypotheses predict the same instant and the run measures nothing. And the
trap: **the spend had to land no hit**, because a landed hit is +25 adrenaline
and would restart the very clock being timed. The plan called for a
self-targeted adrenal skill; the operator spent **skill 348** (type_code 15,
target 0, 80 units), and the wire confirms it worked — **zero `0x00CF` after the
spend**, so the interval is clean.

### 33.3 The measurement

```
last GAIN   t = 18.939
SPEND       t = 36.746      (17.807 s after the last gain)
CLEAR       t = 43.932
```

| anchor | predicts | Δ from measured |
|---|---|---|
| **the last GAIN** (our rule) | 43.939 | **−0.007 s** |
| the SPEND (the rival) | 61.746 | −17.814 s |

**Retail anchors on the last gain, by 7 milliseconds against an alternative
17.8 seconds away.** `AdrenalinePool.use` is correct as written and the
divergence is closed in our favour. n=1 — one episode — but the discrimination
is three orders of magnitude wider than the residual.

### 33.4 What the operator's experience says about the plan

The run worked; the *instructions* were poor, and the operator said so. Two real
defects, recorded because live sessions are expensive and the next plan should
not repeat them:

- **The plan never said the 25 s clock is already running during the pause.**
  From the operator's seat "wait 10 s, spend, now wait 40 more" reads as nonsense
  when the bar is visibly about to drop in 7. The 40 s instruction was
  *experimentally* right — it is what makes a clear at 43.9 meaningful, since a
  spend-anchored clock would not have fired until 61.7 — but an unexplained
  correct instruction is indistinguishable from a wrong one.
- **The pause eats the window, and the plan never bounded it.** The gap came out
  at 17.8 s of a 25 s budget. Eight seconds slower and the bar would have dropped
  *before* the spend and the run would have measured nothing. The plan should
  have said: keep the pause short enough that the spend lands with at least 5 s
  to spare, and if the bar drops first that is a failed attempt, not a result.

The irony worth keeping: the operator's "too slow" execution produced **better**
data than the plan asked for. 17.8 s of separation put the hypotheses nearly
18 s apart instead of 10.

### 33.5 What the same capture cost and gave elsewhere

**Gave, unasked:** the corpus grew 14 → 20 captures, and the energy oracle in
`test_pools` went red on it — correctly. A new property-43 rate,
`0.038823530077934265`, joins to **(2 pips, 17 max)**, and **17 = 20 × 0.85**: a
Warrior's base pool under a −15 death penalty, carrying its 2 pips unchanged.
That is a **second** death-penalty witness for the `f32(0.33)·pips ÷ max`
quantum, from a different capture and a different base than §23's original
(25 → 22), and it arrived *as a test failure* because the armour table had no
17-energy row. The table was too narrow and the model was right.

**Also gave:** a second property-52 resurrect witness, both exactly 1.0.

**And refuted one of our own claims.** `test_adrenwire` §7 asserted the spend's
follower is "always property 50, never 48 or 60", at delta exactly +1 — true of
every spend it had, all of them sword attack skills. Skill 348 follows with
**property 48** (`instant_skill_activated`) at delta **+2**. What survives, 40 of
40, is the half the sender actually needs: **the spend comes first**. The
follower's identity depends on the kind of skill and must not be keyed on.

**Cost, honestly:** the plan asked for light hits TAKEN as a free harvest, to put
a sample under 1% of maximum health and settle the boundary
`pools.damage_units` extrapolates. All 255 new gains carry exactly 25 — they are
landed hits, not damage taken. **The sub-1% boundary is still extrapolated**, and
it is now the cheapest open item on this channel.

### 33.6 Skill 348 is "Watch Yourself!" — and it checks our own `ceil`

**Reported by the operator after the run** (GWW, `"Watch Yourself!"`), and the
client's own table agrees on every field that can be checked:

| | client's record | GWW |
|---|---|---|
| profession | 1 (Warrior) | Warrior |
| attribute | 21 = **Tactics** (`test_attribspend.py:50`) | Tactics |
| displayed adrenaline | **4** | **4 Adrenaline** |
| activation / target | 0.0, target 0 | instant, non-targeted |

**And the displayed 4 is OURS, not the client's.** The record stores only the raw
**80** at `+0x38`; `skilltable.displayed_adrenaline` computes the 4 as
`ceil(80 / 25)`, a RECONSTRUCTION from "a strike is a flat 25, so the displayed
cost is the number of hits needed". GWW saying **4** is therefore an independent
check of that rule — **and on the case that discriminates**, since 80 is not a
multiple of 25 (80/25 = 3.2, where floor gives 3 and ceil gives 4). §26.8's
census found 151 adrenal skills and many of their costs are not multiples of 25;
this is the first time one of them has had its displayed value confirmed from
outside our own decode.

It also explains §33.5's refutation rather than leaving it as an oddity: a
**shout** (`type_code` 15, target 0, instant) is exactly the kind of skill whose
activation would be announced by property **48**, `instant_skill_activated`,
rather than 50, `attack_skill_activated`. The thing that broke the old claim and
the thing that made the run safe are the same property of the same skill —
picking a shout meant no hit could land, and a shout is not an attack skill.

## 34. SKILLS-B1 — the boundary the corpus cannot answer, and the gate it hid

**2026-08-21, no client launched.** `studies/skills` mints `SKILLS-` per
[studies/idents/CONVENTION.md](../idents/CONVENTION.md) §1 — the arc's own
`FINDINGS.md` takes the arc name. Predictions **P28–P31** were sealed before
any scan ran (session scratchpad, sha256 `0b3d6ee7…`); the extractor is
`toolkit/authsrv/adrenjoin.py` and the pins are `test_adrenwire.py` §12–§13.

### 34.1 The question, and why the evidence in hand could not answer it

§33 closed the adrenaline channel except for one line, which `PLAN.md` §8 called
the cheapest thing left: **where does the damage-taken rule stop granting?**
`pools.damage_units` grants `round(pct)` units for `pct` percent of maximum
health lost, and the rounding is measured — 32 sub-25 `0x00CF`s in the live
corpus, 31 joinable to their damage, round fits **31 of 31** where floor fits 14.
But the docstring's own last paragraph names the hole: "A hit for under 0.5% now
grants nothing (it rounds to zero) where the floored reading put that boundary
at 1%. Nothing in the corpus sits in that band."

**That population is selected on the outcome.** It starts from the gains and
looks back at the damage, so every row in it is a damage event that DID grant.
It cannot contain the band where the rule stops. The repair is obvious: run the
join the other way, from every `0x00A3` naming the observer as target, and the
no-gain rows arrive by construction.

### 34.2 The naive answer, and it is spectacularly wrong

Run that inverse census with no other thought and it is clean, large and
completely misleading:

```
damage-to-self events, unambiguous batches   64
  granted something                          32
  granted NOTHING                            32
  largest percentage that granted nothing   7.5000
  smallest percentage that granted           2.5000
```

Read at face value that says retail grants no adrenaline for a hit taking 7.5%
of maximum health — an order of magnitude above the wiki's 1% and above every
granting row in the same table. It also puts **2.5000% granting 3 units in one
row and nothing in another**, which is not a threshold at all: it means the
grant is not a function of the damage.

### 34.3 SKILLS-B1 — the split, and it is total. OBSERVED

The variable is one nobody had stratified on, and it has nothing to do with
adrenaline traffic: **does the observer's own `SKILLBAR_UPDATE` ever name a
skill with a non-zero `adrenaline_units`?**

| | connections | messages | `0x00CF` | `0x00D0` | `0x00D2` |
|---|---|---|---|---|---|
| **ARMED** — ≥1 adrenal skill on the bar | 36 | 98,338 | **918** | **27** | **40** |
| **DARK** — no adrenal skill, ever | 22 | 44,982 | **0** | **0** | **0** |

Not "few" — none. Across 44,982 messages the entire family is absent, spends
and clears included, which is self-consistent in a way that matters: no gain
means no 25-second clock means nothing to clear, and §33 measured that clock at
25.00 s after the last gain.

**The armed column reproduces §4's census exactly** — 918/27/40, and the 886/32
strike split too. That census counts opcodes over the whole corpus; this one
counts them per connection after a skillbar join. Two unrelated queries landing
on the same six numbers is the cross-check that says the stratifier did not
quietly drop traffic.

**Every one of §34.2's 32 no-gain rows is DARK.** Restrict to ARMED and there is
no no-gain row at all: 32 damage events, 32 grants.

### 34.4 The control, because a negative needs a positive

A filtered search that finds nothing proves nothing until it has found something
it should, and here the positive lives inside the negative population. **The
dark connections fought:**

```
DARK   hits landed (damage where the observer is the SOURCE)   45
       completed melee attacks (int property 1, self)          13
       damage taken                                            32
       0x00CF received                                          0
```

GWW's rule is 25 units per successful weapon hit. Thirteen completed melee
attacks earned **zero** messages. Compare the armed side, where the match is
one-for-one: capture `20260818T132739` carries 280 completed attacks and
**280** gains, `20260821T163511` 251 and **251**.

So the silence is a **gate**, not a quiet capture. That distinction is the whole
check — without §34.4 the claim in §34.3 is unfalsifiable.

### 34.5 The gate's variable is CONFOUNDED, and saying so is the finding's other half

Two rules fit all 58 connections identically:

- **Gate A** — the server sends `0x00CF` only when the observer's bar carries an
  adrenal skill.
- **Gate B** — the server sends `0x00CF` only for professions that use
  adrenaline.

Every dark connection is *also* a non-Warrior: bars of profession-7 skills
(814/783/858), profession-4 (153/105), profession-2 (394/446), and two empty
bars. Every armed connection is the *same* Warrior bar (382/384/385 + 364/1/2,
and 348 in the live run). The corpus holds one adrenaline-using character and
three that are not, so it cannot separate A from B and neither may be promoted.

**What separates them is one capture**: the Warrior, in an explorable, with
every adrenal skill taken off the bar, landing hits. Gate A predicts silence;
Gate B predicts 25s. It is a live run and it is cheap, but it is a run — this is
recorded as the experiment, not performed.

### 34.6 Why nobody saw this from the screen. OBSERVED, from the bytes

The charge worker gates its own repaint on whether any slot actually moved, and
that is arithmetic on three addresses rather than a reading:

```
0x008219B3   33 ff                  xor edi,edi          ; before the loop
0x008219C0   ...                    loop top
0x008219EA   89 0e                  mov [esi],ecx        ; the only slot store
0x008219EC   bf 01 00 00 00         mov edi,1            ; INSIDE the loop
0x008219F6   75 c8                  jne 0x008219C0       ; back-edge
0x008219F8   85 ff                  test edi,edi
0x008219FA   0f 84 ed 00 00 00      je  0x00821AED       ; the shared exit
0x00821A03   d9 05 b4 95 94 00      fld dword [0x009495B4]   ; 25.0f
0x00821A12   68 58 00 00 10         push 0x10000058          ; the UI event
```

The flag starts clear, is set only where a slot is written, and is tested
**after** the loop — and the `je` lands past both the 25.0 and the UI event
push. So a `0x00CF` that no slot accepted repaints nothing, fires no
`0x10000058`, and arms no 25-second timer. §31's blink warning never starts.

It cuts both ways. It is why our own extra traffic is harmless on screen, and it
is why six captures of retail sending nothing at all sat unread for a day.

### 34.7 What this does to the sender: a divergence, deliberately not fixed

`authsrv.player_gains_adrenaline` decided this exact case, in writing:

> A GAIN THAT EVERY SLOT REFUSED STILL GOES OUT, though — full pools, **a bar
> with no adrenal skill on it**, everything recharging.

The argument for it is sound and is about our own clock. The **empirical
premise** underneath it is now measured false: retail does not send one. And
retail's silence is deeper than the gain — it sends no `0x00D0` either, so there
is no clock to keep honest, which is the half the docstring's reasoning could not
have known.

**The sender is NOT changed, and that is a ruling rather than an omission.**
Implementing Gate A means picking one side of §34.5's confound on zero evidence,
and the two errors are symmetric and both invisible: §34.6 shows the client
no-ops on an unaccepted 207, and §30 shows an unarmed bar has no overlay to
repaint. What lands is the record — the docstring now names the divergence, and
`test_adrenwire` §12 pins the measurement so the capture that separates A from B
goes red on the number it changes.

### 34.8 P28–P31, scored

- **P28 — "there exist damage-to-self events with no gain." CONFIRMED, wrong
  reason.** 32 of them, and not one is sub-threshold.
- **P29 — "a single threshold, `max(pct | no gain) < 0.5`." VOID.** The
  prediction assumed the population was homogeneous. It is two populations, and
  the "boundary" it would have reported is 7.5%. Worse for the prediction than
  that: §34.C shows the corpus does not pin the rule's FAMILY either, so 0.5
  was never the only candidate it was being scored against.
- **P30 — "`units == round(pct)` on every joined pair." CONFIRMED**, re-fitted
  on the armed rows alone: **round 32/32**, ceil 17, floor 15. The floor→round
  correction survives the stratification that destroyed the boundary claim, and
  the ledger closes: 886 strikes beside damage DEALT plus 32 grants beside
  damage TAKEN accounts for all 918 gains with no residue.
- **P31 — "1- and 2-unit gains exist if the corpus holds damage in
  [0.5, 2.5)." VACUOUS.** No armed row sits below 2.5000%. The armed range is
  2.50–11.04%.

**The sub-1% boundary therefore stays UNVERIFIED**, and now for a known reason
rather than an absence. It was called the cheapest open item on this channel; it
is not one — but it is now the best-specified one, because §34.C reduces it to
a single light hit with two named rules predicting opposite outcomes.

### 34.A The blind replication, and the two rows it recovered

Run as `studies/review`'s pattern: two agents over the same corpus, each handed
one rival hypothesis and told to **refute it**, neither shown the other's answer
or mine. One got `round`, cutoff 0.5%; one got `floor`, cutoff 1.0% — GWW's own
rule. The floor agent returned `hypothesis_survives: false` and reached the bar
gate independently, by its own route and with its own scanner: *"the split is
exact: 11/11 connections with an adrenal bar carry 207; 0/4 without one do, and
those 4 are where all 32 nulls sit."* Two derivations, no shared code.

It also found **two rows my scan lost**, and both are corrections to this
document rather than footnotes:

1. **Damage arrives on `0x00A2` as well as `0x00A3`.** The sourceless
   three-field float channel carries exactly ONE damage event at the observer in
   the whole corpus — a 6.25% hit granting 6 units. My scan read only `0x00A3`,
   which left that gain as an orphan with no damage anywhere near it. **My scan
   printed the orphan and I moved on.** The replication chased it instead, and
   that is the difference between 31 joined and 32.
2. **Two batches carry two identical hits and two identical gains.** I excluded
   them as ambiguous; identical values make every assignment the same pair, so
   they attribute by symmetry and excluding them was over-caution.

**The ledger closing is what says nothing else is left**: 886 + 32 = 918, every
gain in the corpus explained by exactly one partner, no residue.

One thing in its report is wrong and is worth naming rather than quietly
dropping: it proposed reading the rounding constant out of the client's charge
worker to promote the boundary from INFERRED to OBSERVED. There is no such
constant to read. `0x00CF` carries the units already computed, and the worker
does `add eax,[ebp+0xc]` — the message's own field (§26.2, `test_adrenwire` §9).
The damage→units conversion happens on ArenaNet's server, which we cannot
disassemble, and that is precisely why this question needs a capture.

### 34.B The check with no free parameter, which the replication supplied

Every one of the eleven distinct armed percentages is an exact integer over 480:

```
 2.500000037%  = 12/480      6.041666493%  = 29/480
 2.708333358%  = 13/480      6.250000000%  = 30/480
 2.916666679%  = 14/480      7.083333284%  = 34/480
 3.125000000%  = 15/480      8.124999702%  = 39/480
 3.541666642%  = 17/480     11.041666567%  = 53/480
 5.000000075%  = 24/480
```

**480 is the smallest denominator that does it** — searched 1..2000, and the
only others are 960, 1440 and 1920. And the observer's **int property 42**, its
maximum health, reads **480** on the same wire, from a message none of that
arithmetic touched. Two independent witnesses to the same number; a wrong
denominator has no reason to produce eleven integers.

**What it also bounds, honestly:** every granting row in the corpus is that one
character at 480 health. So the corpus cannot separate "one unit per 1% of
maximum health" from "one unit per 4.8 raw damage points" — the wire sends the
fraction, which makes the percentage reading natural, but that is an argument
and not a measurement. **Any second maximum health in a granting connection
settles it**, and that is a cheaper capture than the boundary one.

### 34.C The error bar, and the rival family that changes the experiment

Both agents fitted the rule as a FAMILY rather than testing two candidates,
which is the shape this repo asks for — and the second one found a survivor
neither I nor the first had considered. Re-derived here from the bytes rather
than taken on report, all three over the same 32 armed rows:

```
floor(pct.k) == units     k in [1.200000, 1.086792)     EMPTY
round(pct.k) == units     k in [1.000000, 1.040000)     survives
ceil (pct.k) == units     k in (0.905660, 0.960000]     survives
```

**The floor family is empty under EVERY rescale**, which is a much stronger
statement than "floor fits 15 of 32": no charging rule of the form
`floor(k x damage-fraction)` can produce this wire, whatever `k` is — so
"retail charges on pre-mitigation damage and then floors" is refuted too, not
just the plain reading. GWW is explicit and is outside it: *"rounded down, so
taking less than 1% of your maximum health causes you to gain no adrenaline"*
— **and the threshold in that sentence is a consequence of the rounding, so
with the rounding refuted the threshold cannot be imported either.**

**The two survivors disagree about exactly the thing we went looking for.**
`round` grants nothing below ~0.5%; `ceil` grants **one unit for any damage at
all**. Same 32 rows, opposite answers at the low end. Also surviving, and worth
naming because they read like the same rule and are not: `max(1, round(pct))`
and `max(3, round(pct))`.

**So the experiment is now one observation wide.** One point of damage on the
480-health character in the corpus is 0.208%:

| damage taken | `ceil` predicts | `round` predicts |
|---|---|---|
| 1 point (0.208%) | **1 unit** | **0 — no message at all** |
| 2 points (0.417%) | 1 unit | 0 |
| 4 points (0.833%) | 1 unit | 1 unit |

One light hit taken by a character carrying an adrenal skill separates them, and
a `0x00CF` either arrives or it does not. That is a far better-specified probe
than the one §33's live plan asked for — it said only "light hits taken", and
got 255 gains of exactly 25 — and it is what belongs in the next live plan.
`pools.damage_units` implements `round`; if `ceil` is right, our server is
silent where retail sends a unit.

### 34.D The skeptic pass, and the row the corpus nearly answered with

A third agent was given both derivations and told to break them, not to
summarise them. It re-ran the whole corpus itself. Both headline sets survived
— the census, the gate, the 32/32 fit, the self-identification — and it
corrected both agents on something neither had checked, then found the row that
matters most in this whole section.

**THE NEAR MISS.** The two surviving families disagree only below about 1%.
**Exactly one damage event in the entire corpus lands in that band** — capture
`20260810T235916`, connection `…:49163`, observer 31, one hit for 1 point of
100 maximum health — **and that observer's bar carries no adrenal skill**, so
there was nothing to charge. Every other damage-taken event anywhere in twenty
captures is at or above 2.5%. The corpus came within one connection of settling
the question and did not.

**And its value is 0.999999978%, not 1%.** The wire bits are `0xBC23D70A`,
which is `-0.009999999776482582`. At four decimal places it prints as
`1.0000` — *exactly the value where round and ceil agree*. From the bytes it
sits just below, where they do not. **Three independent readers printed it
rounded and all three read past it**: both replication agents, and my own
scanner, whose `%7.4f` did the hiding. `adrenjoin.py` now prints nine decimals
and calls the band out by name, and `test_adrenwire` §12 pins the row.

**A CORRECTION TO BOTH AGENTS, and it is a method note rather than a number.**
Both read the observer's maximum health as a *set* of the property-42 values in
the connection. Property 42 is re-sent **on change**, so the value in force at a
damage event is not the last one in the stream: connection `…:52294` fights its
whole session at **120** and receives 102 some 1,197 messages later, and
`…:52606` fights at 120 and receives 140 three thousand messages later. The
in-force set across the eight damage connections is **{100, 120, 480}**, not
the {100, 102, 120, 140, 480} one agent published — and that agent's own
integrality control is arithmetically impossible as stated (2.5% × 140 = 3.5
points). Re-run with the temporally correct denominator the control *holds*,
64 rows of 64. **Its conclusion survived; its stated evidence did not**, which
is a distinction worth keeping. Nothing in §34 moves: those rows are excluded
anyway, and all four ARMED connections carry only 480. `adrenjoin.whose_max_health`
now reads it temporally.

**THE SHARPEST THING IT SAID ABOUT §34.3's OWN LOGIC.** The bar split is
justified by an outcome-independent variable, and it is still true that *of the
64 damage rows the gate removes 32, and all 32 removed rows are nulls while 0
of the 32 kept rows are nulls.* A gate whose removals are 100% single-valued in
the outcome can only ever delete nulls and never grants — so **any boundary
read off the gated population is void by construction**, not merely
under-powered. §34 does not read one off it. That is the difference between a
declared limit and a concealed defect, and it is why the boundary line in
§34.8 says UNVERIFIED rather than a number.

**Two things it got wrong, checked from the bytes rather than taken on report.**
Its closing recommendation — and the first agent's too — was to read the
rounding constant out of the client's charge worker and promote the boundary to
OBSERVED without a capture. **There is no such constant.** `0x00CF` carries the
units already computed; the worker does `add eax,[ebp+0xc]`, the message's own
field (§26.2, `test_adrenwire` §9). The conversion happens on ArenaNet's server.
Two agents proposed it independently, which makes it worth writing down as a
dead end rather than leaving for a third to rediscover. And one agent's ceil
interval had both endpoints inverted, `[0.905660, 0.960000)` for
`(0.905660, 0.960000]`; the skeptic caught it and §34.C already has it right.

**One denominator worth stating so §34.3 is not over-read.** Of the 36 ARMED
connections, **25 saw no combat at all** — no damage dealt, none taken. The 918
gains come from 11. The split in §34.3 is a *bar* split over every usable
connection; the control in §34.4 is scoped to the 17 connections that fought,
where it is 11 armed with gains and 6 dark without, 17 of 17.

### 34.9 The lesson, which is the series' fourth of the same shape

§27, §28, §29 and §32 each caught a metric that lied, every time by an in-frame
control rather than by re-reading code. This is the fifth, and the first with no
pixels in it: **the stratifier was a variable the question never mentioned.**
The reading that survived was not the careful one — a careful reader gets 7.5%
and a clean-looking table of 59 rows — it was the one that noticed 2.5000%
appearing twice with two different answers and refused to average them.

Worth naming for the next session: the defence that worked here was **checking
whether the population could contain the answer at all** before believing what
it reported. `adrenjoin.whose_agent` carries the same rule one level down, and
the comment there is load-bearing: identifying the observer by "the agent a
`0x00CF` names" is right on every connection that has one, and would have
deleted the entire dark population from the denominator — hiding the finding
rather than producing a wrong number, which is worse.

**And a second lesson, which is mine to wear twice.** My scan printed an
unexplained row — one gain with no damage in its batch — and I read past it
because the finding I was chasing was already large. Then my scan printed the
single most decisive row in the corpus as `1.0000%`, at a precision that landed
it exactly on the value where the rival rules agree, and I read past that too.
**Neither was a reasoning error; both were display and scope choices made
before there was anything to see.** A scanner's output format is part of its
evidence. The blind replication chased it and
found a whole message channel. An orphan in a ledger is a lead, and the ledger
closing at 918 of 918 is the only thing that says there are no more.

## 35. SKILLS-T1 — the client names its own skill types

**2026-08-21, no client launched, no wiki consulted.** Closes `PLAN.md` §8
item 5 and `studies/presearing/MANIFEST.md` §8's eleven-code follow-up.
Tool: `toolkit/clientscan/typenames.py`; pins: `test_typenames.py` (16 checks).

### 35.1 The question, and the method that was not needed

`MANIFEST.md` §8 named ten of the client's skill `type_code` values by **Rosetta
stone**: take skills whose type is independently known, read their `+0x0C`, take
the majority. It left **eleven UNKNOWN** — 9, 11, 16, 20, 21, 22, 24, 25, 26,
27, 28 — and called naming them "a bounded follow-up using the same method, two
or three known-name skills per code". `PLAN.md` §8 item 5 singled out **16**,
because it is on this server's own default bar and named nowhere.

That method would have worked, and it would have needed an outside source for
every code. It was not necessary. **The client names its own types**, in one
switch, and the whole derivation is arithmetic on its bytes.

```
0x004F9BF0   the namer     mov eax,[edi+0x0C]     <- the type_code field
                           cmp eax,0x0E           <- type 14 leaves here
                           ...                    <- 17, 18, 22 leave here
                           push eax ; call 0x004F9DD0
0x004F9DD0   the switch    mov eax,[ebp+8] ; dec eax ; cmp eax,0x1C
                           ja  0x004FA7A0         <- the default arm
                           jmp [eax*4+0x004FA7BC] <- 29 entries
```

Every case body computes a **string id**. And the default arm carries the single
strongest piece of evidence that this is the *type* namer rather than some other
switch on some other field — ArenaNet's own sentence, at `.rdata 0x0094E614`:

> "There is no string to describe skill %u's type."

### 35.2 The control, which is the whole argument

The jump-table index is `type_code - 1`, and **the bias is the only free
parameter in the entire derivation**. At that bias, all ten codes `MANIFEST.md`
named years earlier — by a completely different method, against outside sources
— resolve through the owner's archive to exactly the ten words it used:

```
 3 Stance      4 Hex Spell   5 Spell     6 Enchantment Spell   7 Signet
 8 Condition  10 Skill      12 Glyph    15 Shout             19 Preparation
```

**Ten of ten.** Then the same check is re-run at bias 0 and bias 2 and scores
**zero and zero**. That second half is what makes the first mean anything: one
step either way breaks every known code at once, so the agreements cannot be a
table of plausible words meeting plausible guesses.

**The exactness in that check is load-bearing, and it was learned by breaking
it.** The first cut asked `expected in got` — and "Spell" is a substring of
"Hex Spell", so the shifted control scored 1 instead of 0 and went red on its
own leak. A weaker comparison leaves the headline check looking fine while
quietly poisoning the control meant to falsify it.

### 35.3 The table. OBSERVED

Ids, with the case body that computes each. **The ids are what the repo commits;
the words are resolved at run time from the owner's own archive**, per
CLAUDE.md's rule for authored text.

| code | case body | base | elite | word | previously |
|---|---|---|---|---|---|
| 1 | `0x004F9E37` | 34036 | — | Blessing | not in our mirror |
| 2 | `0x004F9F3C` | 931 | — | Party Bonus | not in our mirror |
| 9 | `0x004FA74E` | 32224 | 32225 | **Well Spell** | UNKNOWN |
| 11 | `0x004FA6FC` | 32222 | 32223 | **Ward Spell** | UNKNOWN |
| 13 | `0x004FA59B` | 52243 | — | Title | not in our mirror |
| **16** | `0x004FA30B` | **942** | 943 | **Skill** | **UNKNOWN — item 5** |
| 20 | `0x004FA2B9` | 938 | 939 | **Pet Attack** | UNKNOWN |
| 21 | `0x004FA602` | 958 | 959 | **Trap** | UNKNOWN |
| 23 | `0x004FA100` | 32219 | — | Environment Effect | not in our mirror |
| 24 | `0x004F9FA3` | 32220 | 32221 | **Item Spell** | UNKNOWN |
| 25 | `0x004FA549` | 954 | 955 | **Weapon Spell** | UNKNOWN |
| 26 | `0x004FA167` | 38863 | **39729** | **Form** | UNKNOWN |
| 27 | `0x004F9FF5` | 36382 | 36383 | **Chant** | UNKNOWN |
| 28 | `0x004FA0AE` | 18450 | 18451 | **Echo** | UNKNOWN |
| 29 | `0x004FA047` | 51773 | — | Disguise | not in our mirror |

Type 26's elite is **not** base+1 — its body is `and eax,0x362; add eax,0x97CF`
rather than the usual `or imm; shr 2` — and the test pins that as the one
documented exception, so a later reader does not "fix" 39729 to 38864.

### 35.4 Item 5's answer is a genuine oddity

**`type_code` 16 is displayed as "Skill" — and so is `type_code` 10, from a
DIFFERENT string record.** 942 and 960 are two rows of the archive carrying the
same English word (and the same word in French, German and Italian). Two enum
values ArenaNet chose to label identically: not an alias, and not a collision in
our decode. The test asserts **both** halves, because either alone reads wrong.

The bodies differ, and that is where the distinction lives:

- **10** branches on the touch and half-range flags and has variant names for
  each.
- **16** has no variants and instead **asserts both flags are clear** — two
  `GmSkHelpers.cpp:139` sites at `0x004FA30B..0x004FA34B`.

**Why the engine needs two enum values for one word is NOT ANSWERED.** Nothing
here read the code that *consumes* the distinction, only the code that names it.
That is the honest residue of item 5, and it is a different and much smaller
question than the one that was open this morning.

It also explains the structural profile that made 16 puzzling before the switch
turned up. Its 21 rows are **100% instant, 100% self-targeted, 100% carrying a
duration** — perfectly homogeneous, which is not what a catch-all looks like;
type 10's 55 rows are 13% / 31% / 38%, which is. Two "Skill" codes, one of them
the untargeted-self-buff case, fits both shapes.

### 35.5 What the client refuses to name, on purpose

Three refusals, each read from the bytes, and each recorded as a **fact** rather
than a gap in our work:

- **17 and 18** short-circuit in the namer (`sub ecx,0x11; je` then
  `sub ecx,1; je`) to string id 1, the null record. The client has **no word**
  for them. They are also the two largest populations in the full 3,443-row
  client table, so this is the largest thing still unnamed — and it is unnamed
  *by ArenaNet*, not by us.
- **14** never reaches the switch: `cmp eax,0x0E` intercepts it and tail-calls
  `0x004FAE60` with the weapon and combo fields, because an attack's displayed
  name depends on the weapon and the chain slot ("Sword Attack", "Off-Hand
  Attack"). Its jump-table slot is the default arm.
- **22**'s name is not a constant either. It is resolved in the namer from title
  track `+0x2A` and profession `+0x28`: `0x28` gives one string, else profession
  2 gives another and 8 a third, and anything else logs a failure at
  `0x0094E728` naming the family. ArenaNet's own internal word for it is
  **"global skill"**.

### 35.6 What is NOT promoted, and why

- **Type 2, "Party Bonus".** The image says it plainly and the constant is
  verified, but its members are not in our mirror and no second witness exists.
  The tool carries the id; nothing calls it settled.
- **The flag-conditioned variants** — "Touch Hex Spell", "Flash Enchantment
  Spell", "Half Range Spell". Those strings are reachable from the case bodies
  (OBSERVED) but **which flag bit selects which was not verified**, so
  `TYPE_STRING_ID` deliberately holds only the unflagged name. A mapping nobody
  checked is the thing this repo keeps getting burned by.
- **Type 14's weapon sub-table.** A second switch at `0x004FAE60` that nobody
  walked to the end. Treat any list of its returns as a floor.
- **`effects.py`'s `EFFECT_TYPES`.** Several newly-named codes — Well Spell,
  Ward Spell, Item Spell, Weapon Spell, Form, Chant, Echo — are plainly timed
  effects, and adding them is a *behaviour* change that needs its own evidence
  and its own run. Named here as a follow-on, not done.

### 35.7 How it was found, which is the transferable part

Three agents, three routes, none seeing the others: the image, the skill table's
structure calibrated on the ten known codes, and the live wire corpus. **The
image route won outright** — it went at the code rather than hunting for arrays,
found the accessor by cross-reference, and scanned for MSVC compressed switches
whose bound sits in 20..36. The structural route independently derived the
two-name split for type 22 from nothing but the corpus composition, which is the
strongest cross-route agreement in the set; the wire route contributed a witness
for 16 and a partition of the activation properties.

**And the judge caught the image route citing the wrong address for its own
correct conclusion** — `0x004FA2F9` where the arithmetic is at `0x004FA34B`;
the earlier address is the tail of the *type-20* case and holds `or esi,0x0EA8`
→ 938. The number was right, the citation was one case body early. That is
worth more than it looks: a wrong citation makes a later reader's audit fail and
look like the claim failed. Everything published here was re-read from the image
before it was written down, and the test pins `0x004FA34B` specifically.

## 38. SKILLS-R1 — what answers a refused press, on the wire and on screen

> **Numbering note, 2026-08-22 — this section was written as §36, and so was
> §36 above.** Two `## 36.` headings collide as one markdown anchor, which is
> the append collision `toolkit/seclint.py` was written for a day earlier — and
> it caught this one, red on `test_seclint.py`. **This** one moved, because §36
> above is the `effect_silent_extend` probe, which had ALREADY been renumbered
> once (out of its own `## 32.` collision) and is cited from `studies/isle`
> §36/§36.7/§36.8, `effects.EffectTable.apply`'s docstring and this file's
> own positive control. §38 is the next free number; §37 below is SKILLS-R2
> and keeps its number, so the R1/R2 pair reads 38 then 37 in file order — this
> document is already non-monotonic (§26.12/§26.13 and §36 all sit before
> §32) and renumbering a section that does NOT collide is churn with no gate
> behind it. Old references resolve here: `PLAN.md` §8 item 2 now says §38.

**2026-08-22.** Closes `PLAN.md` §8 item 2, which had been open since E2 on
2026-08-20. Three blind recon routes (image / corpus / our own catalog), a
judge, then a build and a loopback run: `20260822T105929`.

### 38.1 Retail's answer is three messages, not one

```
0x005D CHAT_MESSAGE_CORE    [coded string = the reason's string id]
0x005E CHAT_MESSAGE_SERVER  [playerId, channel 7]
0x00E2                      [agent, skill, copy]     <- releases the slot
```

**OBSERVED.** Of 143 skill presses in the 20-capture corpus, **43 are declined
and 43 are answered** — none is met with silence. 40 of 40 carry the full
batch in exactly that order with those exact neighbours; the other 3 send the
bare `0x00E2` with no sentence, so **the sentence and the release are
separable**.

I reproduced every number independently before writing any code: the `0x005E`
channel census `{6: 1, 7: 40, 10: 96}`, the 40/40 adjacency, `0x00E2` at 53
occurrences with third field 0 in **53/53**, and `codedstr.encode_id(1960)` =
`0x8A8`, matching the observed wire word bit for bit.

**Channel 7 is the warning panel, from two sides.** The image: GmView frame
`0x1000007F` dispatches to `0x004E4EFC`, whose first instruction is
`cmp dword ptr [edi],7` — channel 7 is the only value that body accepts, and
the panel is named `TxtError`. The wire: all 40 channel-7 tags sit in refusal
batches, while 96 channel-10 and 1 channel-6 tag in the same captures never do.
That contrast is the discriminating negative; a channel byte appearing in both
populations would have proved nothing.

**`0x00E2` cannot carry the reason, and that is measured.** It shares dispatch
stub `0x0091F650` with `0x00E3`, and the stub forwards three payload dwords and
**not the opcode** — the worker literally cannot tell them apart. So the reason
rides the chat line and the opcode only releases the slot. (`0x00E4` and
`0x00E5` have distinct stubs in the same table, which is the contrast proving
the sharing is real rather than an artifact of how we read the table.) Retail
answers a refusal with `0x00E2` **43 times** and with `0x00E3` **zero**.

`0x00E2` is unnamed in `messages.json`, in `overrides.json` and in GWCA's
`Opcodes.h`. It is named here as `GAME_SMSG_SKILL_REFUSED`.

### 38.2 The run. P19 and P20 CONFIRMED

Bar `317,863,318,319,320,321,322,323`. Skill 863 was chosen for one property:
**recharge 0**, which removes the recharge confound entirely.

| frame | press | server | on screen | orb |
|---|---|---|---|---|
| `2-key` | 317, adrenal, 0 units | REFUSED, #1960 | **"Not enough Adrenaline."** | 25 |
| `3-key` | 863, 25 energy, have 25 | **ACCEPTED** | "Order of Apostasy" cast bar, glyph, sparkles | **0** |
| `4-key` | 863, have 7.83 | REFUSED, #1961 | **"Not enough Energy."** | 8 |

**The middle row is the in-frame control and it is what makes the other two
interpretable** — it separates "presses are being seen" from "the refusal did
something", and it fired unambiguously.

**P20 is the one that mattered. 1961 was a RECONSTRUCTION and is now OBSERVED.**
The corpus contains **zero** energy refusals — all 43 declines are `0x0027`
attack-skill presses and 0 of 49 `0x0046` casts was ever refused, because the
operator never ran out of energy. So 1961 rested on the archive text plus its
position one record after 1960's. A different sentence on screen would have
refuted it. The right one appeared.

### 38.3 P21 REFUTED, and it is a real refinement

I predicted the sentence would appear **both** as a panel and as a chat-log
line. It does not. **The chat log is empty in all three frames** — the
channel-7 line renders only as the floating red text above the character and
never enters the log. So channel 7 is not "a chat channel that also draws a
panel"; it is a panel channel that the log ignores.

### 38.4 THE INSTRUMENT WOULD HAVE MISSED THIS ENTIRELY

The pre-registration named this as the trap most likely to kill the run, and it
was right. The refusal text renders at roughly **(880–1060, 520–540)** — and
the harness screenshot scorer masks the player-body rect
`~(850,300)-(1120,760)` to suppress idle animation. **The sentence lands dead
centre of the mask.**

Measured 2026-08-18 against the `0x00B9` callout, that mask ate 53% of a known
UI element's changed pixels and would have scored a lone banner at 95 scattered
anti-aliased pixels — noise under any threshold. Had this run been scored the
usual way it would have reported a null, and the null would have been read as
"the message does nothing."

**This is the fifth metric trap in this series and the first one caught in
advance** — §§27, 29, 30 and 32 each caught theirs with an in-frame control
*after* the fact. What caught this one was declining the instrument before the
run, on the strength of a measurement someone had already written down.

### 38.4b THE HARNESS RETRACTED THIS RUN'S VERDICT, and it is recorded here

`RUN VERDICT RETRACTED: the run passed its checkpoints, then the client died
during the hold.` The same machinery that voided E5 fired again, and a run whose
verdict was retracted must say so in its own write-up rather than in a summary
somewhere else.

**It does not touch the readings, and the timestamps are why:**

| | time |
|---|---|
| adrenaline refusal frame `2-key` | 11:00:26 |
| control frame `3-key` | 11:00:35 |
| energy refusal frame `4-key` | 11:00:43 |
| **94 further hold frames** | 11:00:44 → **11:04:19** |
| client exits, code **0**, no error dialog | ~11:04:20 |

The three measured frames precede the exit by about **three and a half
minutes**, the gamesrv log carries all three complete press/answer exchanges
before them, and the harness's own crash check says it plainly: *"no error
dialog within 12 s — the client exited WITHOUT one, which is a clean exit
rather than a silent crash."* The last frames before the exit are logged
`skipped: client not foreground`, so the window lost focus first.

**And it is worth stating what this rules out, because it is the obvious
worry:** the new messages did not destabilise the client. A client killed by a
malformed `0x00E2` or a bad coded string dies AT the press, with a dialog or a
nonzero code; this one drew both sentences correctly, kept running for 94 more
frames with normal effect traffic (`effect 863 on agent 1 expired, 5.03s of
5.0s`), and then exited cleanly.

**AND THE EXIT IS EXPLAINED — THE OPERATOR CLOSED IT, because I gave them no
reason not to.** This was written as "unexplained" for about ten minutes until
the owner said so: *"i exited since you left it on my screen without a timeout
or indication when it would finish."*

That is a defect in how the run was invoked, not in the client. `--keep-open`
**without `--hold`** means exactly this, and `session.py` says so in the flag's
own help — *"Without `--hold` it holds until you close the client."* So the run
parked a live game window on the owner's screen with no end condition and no
progress indication, and then the harness logged their reasonable response to
it as a client death. The retraction is real, its cause is a badly chosen flag,
and the lesson is that **an agent-driven run must bound its own hold**:
`--keep-open --hold N`, with N sized to the action script plus a margin.

This is the same failure as the live-capture plan of 2026-08-21 (§33.4), from a
different direction: **a wait that is not bounded and not announced.** Twice in
two days, once in prose and once in a flag.

**AND THERE WAS A FOURTH PRESS, THE OPERATOR'S — it is accounted for and it is
a free witness.** While the window sat open the owner pressed slot 2 once. The
log carries four `0x8046 USE_SKILL`, not three, and the extra one is at line
**214**, after every measured event (lines 141–169) and after frame `4-key`.
So the readings above are clean; this is stated because a run with unlogged
operator input is a run whose readings cannot be trusted, and the check is
cheap.

What it adds is worth more than the tidiness. That press was **ACCEPTED** —
energy had regenerated to 25 and the cast drained it to 0 again — and it came
**after two refusals on that same bar**. So a slot that has just been refused
still takes a fresh press: the `0x00E2` release does not leave the slot
unusable, and it is a HUMAN-driven confirmation rather than another
harness-scripted one. That is a small piece of evidence on §38.8's open
question about the ~10 s re-animation, and it arrived by accident.

### 38.5 Two corrections the routes needed

**The judge corrected the corpus route on the single anomalous line.** It had
filed the one non-1960 channel-7 message as a recharge refusal. Resolving the
text settles it the other way: that press is **the only one in the corpus with
target == 0** — 1 of 1 against 0 of 42 — and 1934 is *"Invalid attack target."*
The genuine recharge refusal is a **different** press 0.66 s earlier, and it is
**silent**; 1964 ("That skill is still recharging.") never appears on any wire
we hold. Neither route could have caught this alone — the corpus route
deliberately refused to resolve text, the image route had no wire.

**And the schema route had the right fact with the wrong conclusion.** It found
that 226 and 227 share a dispatch and concluded `0x00E2` was therefore
disqualified as a carrier of "refused". That sharing is exactly *why* the
design works, and its own standing warning — "a survey keyed on a name cannot
find a thing nobody named" — predicted the miss, because `0x00E2` is unnamed.

### 38.6 The code's own comment was wrong about itself

`authsrv.py`'s resource gate carried this, and both halves are now refuted:

> *"What retail's server does when a client presses an unaffordable skill is
> UNOBSERVED on our corpus: the client may well swallow the press itself and
> never send `0x0046` at all, in which case this branch is unreachable in a
> real session."*

It is observed, 43 times. And the branch is the hot path rather than a dead
one: E2 watched our client send a 25-energy press with 7.70 energy, and
retail's own clients send 43 declined presses — including one **inside a live
recharge window**, which also means `ChCliApiUseSkill`'s recharge bail does not
cover the attack-skill send path.

### 38.7 A third test that had grown up around our silence

Two `test_pools` checks asserted `sent == []` on a refusal. That was right about
the cast cycle and wrong about the wire. **This is the third time in this arc a
test defended a shape retail never produces** — the energy debit order and the
adrenaline gain order were the first two.

The intent survives and is sharper: not "nothing was sent" but "exactly the
refusal batch, and nothing from the cast cycle", with `cast_cycle_ops()` naming
what a refusal may never emit. Same argument as the other two: pin a shape
against a census, not against whatever the sender happened to do first.

### 38.8 What is still open

- **What ends the ~10 s slot re-animation E2 saw**, and whether ~10 s is real
  at all. The only release in the image is the `0x00E2` refcount decrement.
  Either there is an unread client-side timeout or 10 s is simply how long the
  operator watched. **NOT FOUND**; all three routes left it open.
- **The reason ids for the rest of the 1934–1993 block.** They live server-side
  and are not derivable from a client that only renders what it is handed.
- **Two silent skill-384 declines** (pool exactly == cost, no recharge window)
  may be a fourth refusal class. Recorded, not fitted.
- **String ids 1928–1933** are RC4-encrypted archive records and unreadable.

## 37. SKILLS-R2 — the "~10 second" re-animation is a 1-second loop that never stops

**2026-08-22.** §38.8's first open bullet, and the last thing `PLAN.md` §8
item 2 was waiting on. Two routes that share no method: an A/B loopback pair
(`20260822T114025` released, `20260822T114206` silent) and a static hunt through
the pinned image. **Both answer the same way, and the answer is a negative.**

### 37.1 The question, and why it was only answerable today

E2 (2026-08-20) watched a refused press re-animate its slot for *"about 10
seconds"* against a server that answered with nothing. Two candidates: **(a)** a
client-side timeout expires the pending-cast entry, or **(b)** nothing does, and
the ~10 s is something else.

Until 2026-08-22 our server *was* the silent case, so (b) had no contrast to be
measured against. §38 put `0x00E2` on the wire, and `--refusal-silent`
reproduces the old server exactly — **one flag, one difference**, which is the
arm the recon judge asked for and the only reason this is a measurement rather
than an argument.

### 37.2 The run. P22 and P23 CONFIRMED

One press per arm, identical scripts, 1.27 s frames, 39.2 s hold. Slot 1
changed-pixel count against the previous frame; slot 8 is an in-frame control
that was never pressed.

| | arm A, released | arm B, silent |
|---|---|---|
| slot 1, every frame after the press | **0** | **still animating at 39.2 s** |
| slot 8 control, all 32 frames | 0 | **0** |
| `0x8046` presses vs a 1-action script | 1 | 1 |

**Arm B was still changing in its final frame — the hold ended before the
animation did.** Nothing was observed to stop it.

**The cross-arm control is what makes this attributable.** Same slot, same
skill, same map, same script; the only difference is whether the release went
out. An idle shimmer in the icon art would have moved in arm A too, and arm A
is flat zero in all 32 frames. And `0x00E2` stopping it within a single frame is
an independent confirmation that the release does what §38 says.

### 37.3 The static route: (b), with a positive control that could have refuted it

Three structural facts, each re-read from the image by me before publication:

1. **The removal path has exactly one root.** Every link in the release chain
   has a single caller and zero data words holding its VA, closing to the RECV
   table: `0x00823090` ← `0x00822B70` ← `0x008148C0` ← stub `0x0091F650`, which
   both `0x00E2` and `0x00E3` resolve to. **Only a received message reaches the
   decrement.**
2. **The entry has nowhere to keep a deadline.** It is 8 bytes and both dwords
   are spoken for — `mov [eax+edi*8],ebx` writes the key
   `(skillId<<16)|copy` at +0, `mov [eax+edi*8+4],1` writes the refcount at +4.
   ArenaNet names the second itself: **`ChCliSkill:955  pending->refCount`**.
   No timestamp, no float, so a per-entry expiry is structurally impossible
   without a parallel store — and only three code sites in the whole image
   compute `&pendingSkills` (insert, release, and an `rtl::Array` destructor),
   none of them time-driven.
3. **The overlay loop has no terminating condition.** The casting overlay is
   created and destroyed solely by GmCtlSkImage msg `0x62`, whose value is the
   entry's existence copied verbatim through UI event `0x1000005B`. Its tick
   accumulates dt, advances a counter every **0.0625 s**
   (`.rdata 0x00951030 = 00 00 80 3d`) and **wraps at 16**
   (`0x008CF93B cmp eax,0x10`). No countdown, no self-destruction.

**THE POSITIVE CONTROL IS WHAT MAKES THE NEGATIVE WORTH ANYTHING.** A search
that has never found a timeout cannot be trusted to report their absence, so
the same method was pointed at a timer we already knew existed — and it
recovered the adrenaline blink end to end: the arm (`fld dword [0x009495B4]`,
raw `0000c841` = **25.0**, broadcast `0x10000058`), the route through
GmSkSlot to GmCtlSkImage msg `0x5A`, and the store's **per-frame float
subtraction** `fsub dword [edi]` with its latch at zero. That idiom is not a
wall-clock read at all, so it would have been invisible to a clock-xref sweep —
the method found it anyway, and applied to the pending array it returns nothing.

**A free correction to §31 came with it:** the blink window is the last
**4.0 seconds** (`.rdata 0x00941B98 = 00 00 80 40`), which is why §31.3 saw the
oscillation only near the end of the 25 s and never earlier.

### 37.4 The answer, and where the operator's number came from

**There is no client-side timeout. The "~10 seconds" is not a duration the
client enforces** — against a silent server the entry persists and the overlay
loops indefinitely. E2's number was how long the operator watched.

And both routes independently landed on the same explanation for *why ten*:
**the overlay loop is exactly 1.000 s** (16 × 0.0625). "About ten seconds" is
about ten cycles of a loop that looks the same every time — which is precisely
what a repeating animation with no endpoint looks like to someone deciding when
to stop watching. **Labelled RECONSTRUCTION**, because nobody asked the operator
to count cycles and the run cannot distinguish "watched ten loops" from "watched
for ten seconds".

### 37.5 MY MEASUREMENT WAS GARBAGE FIRST, AND ITS OUTPUT SAID SO

`png.read` returns `(pixels, width, height, COLOUR TYPE)` — the fourth value is
the PNG colour type, **not** the channel count. I used it as a stride, so a
truecolour image (type 2, three bytes a pixel) was read three bytes at a stride
of **two**: every index wrong, every comparison a comparison of overlapping
garbage.

**The tell was in the first output and I did not act on it.** Two *separate
runs* produced byte-identical numbers — 2906 and 3079, twice. Two independent
runs of a live game agreeing to the byte is not a result, it is a diagnostic,
and I read past it and went looking at the crop geometry instead. `png._CHANNELS`
is the real mapping.

**Its second effect was worse than the first**, and is the reason this is
written up rather than quietly fixed: with the wrong stride, *both arms read
zero for every frame*. That is a NULL — and it is the exact null the
pre-registration had named as "the rig is wrong, neither arm is interpretable."
The plan's own stopping rule caught it. Had the plan not named that null in
advance, "no change in either arm" is a perfectly publishable-looking finding
that would have said the opposite of the truth.

**A period claim was declined at the right moment, for the wrong reason.** After
the fix I measured the cycle at lag 11 (14.0 s) or lag 16 (20.3 s), both weak,
and refused to publish a period from 32 aliased samples. The static route then
gave the true period: **1.000 s.** I sampled a 1 s signal at 1.27 s — far past
Nyquist — so both candidates were aliasing artifacts. The refusal was correct;
the reason I gave for it ("the sampling cannot resolve it") happened to be
exactly right, which is luckier than it should have been.

### 37.6 What is still not established

- **The character's own cast animation in AgentView.** Property 60 queues action
  event kind `0x19` with two payload dwords and **no duration argument**; where
  its length comes from, and whether AvChar retires it independently, is
  **NOT FOUND**. If anything ends *visibly* on its own, this is where it lives.
- **A second path that could clear the overlay while the entry lives**, flagged
  and explicitly not settled: GmSkSlot's full refresh at `0x00543020` sends msg
  `0x62` with a hard-coded false when its cached slot pointer is null, without
  consulting `IsSlotCasting`. What would put a slot in that state is unknown.
  **UNVERIFIED**, and it is the one candidate that could still make a slot
  appear to stop on its own.

